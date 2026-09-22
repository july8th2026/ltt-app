"""
cong_vlm.py — client phía MÁY A gọi cổng VLM trên máy B. (H38)

⭐ Đây là phía đối diện của `llm_gateway/api.py`. Nó **không** biết gì về
   llama.cpp, GGUF, VRAM hay ComfyUI — chỉ biết một HTTP API tương thích OpenAI,
   và biết bốn luật mà dự án đã trả giá để học.

⛔ LUẬT 1 — **429 LÀ BẬN, KHÔNG PHẢI HỎNG.** Máy B dùng chung GPU với việc ảnh và
   dự án video. Nếu coi 429 là lỗi provider thì `api_pool.danh_dau_loi()` sẽ
   cooldown rồi **`disable` key sau 5 lần** — và model nhà tự tắt vĩnh viễn chỉ vì
   hàng xóm đang bận.
   ⇒ `BanError` là một lớp NGOẠI LỆ RIÊNG, không phải `CongVlmError`.

⛔ LUẬT 2 — **KHÔNG TỰ CHUYỂN SANG MODEL KHÁC.** D-010: đổi model sau lưng khách
   là đánh tráo sản phẩm. Với một API **bán ra ngoài** thì nặng hơn nữa: khách trả
   tiền cho Qwen3.8-27B mà nhận về Gemini thì đó là bán sai hàng.
   ⇒ Bận thì báo bận. Muốn có đường lui thì bên gọi **tự khai**, và khi đó **tính
   tiền theo giá của model lui**.

⛔ LUẬT 3 — **KHÔNG BAO GIỜ ĐỂ `usage` LÀ SỐ ĐOÁN.** Tiền của khách tính từ đây.
   Thượng nguồn không trả `usage` thì `SuDung.dang_tin = False`, và bên gọi phải
   xử lý trường hợp đó **một cách rõ ràng** thay vì lặng lẽ tính bừa.

⛔ LUẬT 4 — **TOKEN LẤY TỪ CACHE PHẢI ĐẾM RIÊNG.** llama.cpp báo
   `timings.cache_n` = số token prompt **không phải prefill lại**. Bot gọi lặp
   cùng system prompt; tính đủ giá cho phần đó là **tính tiền khách hai lần cho
   cùng một thứ**.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from platform_core.llm.the_suy_nghi import tach_the_lot
from platform_core.llm.model_failure import ModelFailure, decode_gateway_failure

log = logging.getLogger(__name__)

#: Không biết còn bao lâu thì coi như LÂU. Không bao giờ lạc quan.
ETA_KHONG_BIET = None


class CongVlmError(Exception):
    """Cổng VLM hỏng thật. Bên gọi ĐƯỢC quyền tính đây là lỗi provider.

    ⭐ `ma` — **mã HTTP thượng nguồn**, thêm 13/09 (L-09). Không có nó thì
       `dieu_phoi` gọi `api_pool.danh_dau_loi(db, key)` mà không nói được lỗi
       thuộc loại nào, và `danh_dau_loi` đọc `http_status=None` thành *"5xx hoặc
       lỗi mạng"* ⇒ `error_count += 1`. Năm lần là `APIKEY_ERROR` — từ 19/09
       có hạn `ERROR_COOLDOWN_S` rồi thử lại (nửa mở), nhưng `error_count` giữ
       nguyên nên lỗi kế là ERROR ngay; trước 19/09 thì **không tự hồi**.

    🔴 Hậu quả đo được: một khách gửi **năm ảnh hỏng** là tắt model nhà cho tới
       khi có người sửa tay. Chính `danh_dau_loi` đã có nhánh đúng —
       *"400 ≤ s < 500: Bad request CỦA TA — KHÔNG phạt"* — nhưng nhánh ấy chỉ
       chạy khi ai đó **truyền mã vào**.
    """

    def __init__(
        self,
        thong_diep: str = "",
        *,
        ma: Optional[int] = None,
        failure: Optional[ModelFailure] = None,
    ):
        super().__init__(thong_diep)
        #: Mã HTTP thượng nguồn, `None` khi lỗi không đến từ một phản hồi HTTP.
        self.ma = ma
        self.failure = failure


class AmbiguousProviderError(CongVlmError):
    """Outbound POST đã bắt đầu nhưng không nhận được kết quả xác định."""


class ProviderOomError(CongVlmError):
    """Provider xác định không đủ bộ nhớ; retry nguyên request sẽ hỏng lại."""


class YeuCauSaiError(CongVlmError):
    """Thượng nguồn nói **yêu cầu sai** (400/422) — lỗi của KHÁCH, không của ta.

    🔴 VÌ SAO PHẢI CÓ LỚP RIÊNG, đo được 13/09 (L-09, cổng N §22):

       Máy B trả đúng chuẩn cho một ảnh hỏng:

           400 {"error": {"code": 400, "type": "invalid_request_error",
                          "message": "Failed to load image or audio file"}}

       Máy A làm phẳng nó thành `CongVlmError` ⇒ **503** cho khách, và
       `danh_dau_loi` không có mã nên phạt key như một lỗi 5xx.

       Hai cái sai, mỗi cái một hướng:
         · khách nhận `503 retry_after` cho một yêu cầu **không bao giờ** thành
           công dù thử lại bao nhiêu lần;
         · và năm lượt như thế **tắt model nhà**.

    ⛔ KHÔNG cascade sang provider khác — cùng lý do với `ProviderOomError`:
       gửi lại y hệt một yêu cầu sai thì nó sai y hệt. Cascade ở đây chỉ tiêu
       thêm một provider và một lượt chờ của khách.

    ⭐ Đây là **cửa thứ ba** của cùng một thảm hoạ D-005. Luật 1 ở đầu tệp bịt
       cửa **429**; bản vá 09/09 bịt cửa **504**; cửa **400** đứng mở tới hôm nay.
    """


class BanError(Exception):
    """Máy B đang bận. **KHÔNG PHẢI LỖI** — đừng đánh dấu lỗi cho key."""

    def __init__(
        self,
        ly_do: str,
        retry_after_s: Optional[float] = None,
        chi_tiet: Optional[dict] = None,
        failure: Optional[ModelFailure] = None,
    ):
        super().__init__(ly_do or "may B dang ban")
        self.ly_do = ly_do
        self.retry_after_s = retry_after_s
        self.chi_tiet = chi_tiet or {}
        self.failure = failure


#: Cổng trả mã này khi lượt bị **hủy theo yêu cầu**. Quy ước của nginx cho
#: *"client đã đóng"*; cả hai đầu là mã của ta nên dùng nó là đúng nghĩa.
MA_HUY = 499


class HuyError(Exception):
    """Lượt bị HỦY theo yêu cầu. **KHÔNG PHẢI LỖI** — của ai cả.

    🔴 VÌ SAO KHÔNG PHẢI `CongVlmError`, VÀ ĐÂY LÀ LUẬT THỨ NĂM CỦA TỆP NÀY.
       `CongVlmError` là giấy phép cho bên gọi `api_pool.danh_dau_loi()`; năm lần
       là `key.status = APIKEY_ERROR`. Trước 19/09 trạng thái đó **không tự
       hồi**; nay nó có hạn (`api_pool.ERROR_COOLDOWN_S`) rồi thử lại, còn ERROR
       không hạn (đặt tay/bản cũ) vẫn chờ admin. Dù vậy **năm lần khách bấm
       "dừng" vẫn là model nhà tắt** (từng hạn một, mỗi lỗi kế lại tắt ngay) —
       đúng thảm hoạ D-005 mà luật 1 đã bịt
       ở cửa 429 và luật 504 đã bịt ở cửa hết giờ. Đây là cửa thứ ba.

    🔴 VÀ VÌ SAO KHÔNG DÙNG LẠI `BanError` cho gọn. `dieu_phoi` đọc `BanError` là
       *"đi tiếp provider sau"*. Với model nội bộ, `canonical.THU_TU_PROVIDER` có
       **một** phần tử — nên "đi tiếp" là cạn danh sách ⇒ `KhongCoProviderNao`,
       một thông điệp nói "không provider nào phục vụ được" cho một lượt mà chính
       khách vừa hủy. Nguyên nhân thật bị che, và người đọc log sẽ đi tìm máy B.

    ⇒ Một lớp riêng, không họ hàng với `CongVlmError`: **không** cascade, **không**
      đánh dấu lỗi khoá, và bên gọi nhìn tên là biết chuyện gì.
    """

    def __init__(
        self,
        ly_do: str = "",
        chi_tiet: Optional[dict] = None,
        failure: Optional[ModelFailure] = None,
    ):
        super().__init__(ly_do or "luot bi huy theo yeu cau")
        self.ly_do = ly_do
        self.chi_tiet = chi_tiet or {}
        self.failure = failure


class VuotNganSachError(Exception):
    """Yêu cầu vượt trần của cổng (413). Thử lại y hệt sẽ hỏng y hệt.

    Tách khỏi `CongVlmError` vì lý do vận hành: đây **không** phải lỗi của máy B,
    và `api_pool` không được đánh dấu lỗi cho key vì nó.
    """

    def __init__(
        self, ly_do: str, chi_tiet: Optional[dict] = None, failure: Optional[ModelFailure] = None
    ):
        super().__init__(ly_do or "vuot ngan sach")
        self.ly_do = ly_do
        self.chi_tiet = chi_tiet or {}
        self.failure = failure


@dataclass(frozen=True)
class SuDung:
    """Số token của một lượt gọi. **Đây là căn cứ tính tiền.**"""

    token_vao: int = 0
    token_ra: int = 0
    #: Token prompt lấy lại từ cache (`timings.cache_n`). Đã NẰM TRONG `token_vao`.
    token_vao_cache: int = 0
    #: `False` khi thượng nguồn không trả `usage`. Bên gọi **phải** xử lý riêng —
    #: xem luật 3. Đừng coi 0 token là "miễn phí".
    dang_tin: bool = False

    @property
    def token_vao_moi(self) -> int:
        """Phần prompt thật sự phải prefill — phần tính giá đầy đủ."""
        return max(0, self.token_vao - self.token_vao_cache)


@dataclass(frozen=True)
class KetQuaChat:
    noi_dung: str = ""
    #: Khối suy nghĩ, khi cổng chạy `--reasoning-format deepseek`. Tách khỏi
    #: `noi_dung` để token suy nghĩ không chen vào giữa một tool call.
    suy_nghi: str = ""
    tool_calls: tuple = ()
    finish_reason: str = ""
    model: str = ""
    su_dung: SuDung = field(default_factory=SuDung)
    #: Thân JSON gốc, cho bên gọi cần thứ ta chưa bóc.
    tho: dict = field(default_factory=dict)

    @property
    def co_tool_call(self) -> bool:
        return bool(self.tool_calls)


def _int(gt: Any) -> int:
    try:
        return max(0, int(gt))
    except (TypeError, ValueError):
        return 0


def _phan_hoi(value: tuple) -> tuple[int, Any, dict[str, str]]:
    """Nhận cả transport cũ `(status, body)` và mới có thêm headers."""
    if len(value) >= 3:
        ma, than, headers = value[:3]
        return int(ma), than, dict(headers or {})
    ma, than = value
    return int(ma), than, {}


def _failure_body(than: Any) -> bytes:
    if isinstance(than, bytes):
        return than
    if isinstance(than, str):
        return than.encode("utf-8", "replace")
    try:
        return json.dumps(than, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError):
        return b""


def doc_su_dung(than: dict) -> SuDung:
    """Bóc `usage` + `timings.cache_n` từ thân phản hồi của llama-server.

    Tách thành hàm riêng vì **đây là hàm tính tiền**, và một hàm tính tiền phải
    test được mà không cần dựng cả một client.
    """
    than = than or {}
    usage = than.get("usage")
    if not isinstance(usage, dict):
        # ⛔ Luật 3: không đoán. `dang_tin=False` để bên gọi biết mà xử lý.
        return SuDung(dang_tin=False)

    vao = _int(usage.get("prompt_tokens"))
    ra = _int(usage.get("completion_tokens"))

    # `cache_n` là của llama.cpp, nằm ngoài `usage`. Một số bản cũng đặt
    # `cached_tokens` trong `prompt_tokens_details` theo kiểu OpenAI — nhận cả hai.
    cache = 0
    timings = than.get("timings")
    if isinstance(timings, dict):
        cache = _int(timings.get("cache_n"))
    if not cache:
        chi_tiet = usage.get("prompt_tokens_details")
        if isinstance(chi_tiet, dict):
            cache = _int(chi_tiet.get("cached_tokens"))

    # Cache không thể nhiều hơn tổng prompt. Nếu thượng nguồn báo thế thì nó sai,
    # và ta kẹp lại thay vì để nó thành một khoản giảm giá không có thật.
    return SuDung(token_vao=vao, token_ra=ra, token_vao_cache=min(cache, vao), dang_tin=True)


@dataclass
class CongVlm:
    """`goi` là hàm HTTP tiêm được: `goi(method, path, json=None) -> (status, body)`.

    Tiêm thay vì gọi thẳng `httpx` để test chạy được trên máy A **không cần máy B**
    — cùng cách `cong_render.py` tự test chính nó.
    """

    goi: Callable[..., tuple]
    #: Trần một lượt HTTP. Rộng có chủ ý: ở ngữ cảnh dài, prefill mất hàng chục
    #: giây trước token đầu tiên.
    timeout_s: float = 120.0

    # ── đọc trạng thái ───────────────────────────────────────────────────────
    def health(self) -> dict:
        ma, than, _headers = _phan_hoi(self._goi("GET", "/health"))
        if ma != 200:
            raise CongVlmError(f"health tra {ma}")
        return than or {}

    def models(self) -> list:
        ma, than, _headers = _phan_hoi(self._goi("GET", "/v1/models"))
        if ma != 200:
            raise CongVlmError(f"/v1/models tra {ma}")
        return list((than or {}).get("data") or [])

    def dang_ban(self) -> tuple:
        """`(ban, ly_do)` — hỏi trước khi gửi, để giao diện nói được với khách.

        Không thay thế việc bắt `BanError`: giữa lúc hỏi và lúc gửi, việc ảnh hoặc
        dự án video có thể vừa bắt đầu một lượt.
        """
        try:
            h = self.health()
        except CongVlmError:
            return True, "khong lien lac duoc voi may B"
        tt = h.get("trong_tai") or {}
        return bool(tt.get("ban")), str(tt.get("ly_do") or "")

    # ── gọi model ────────────────────────────────────────────────────────────
    def chat(
        self,
        *,
        model: str,
        messages: list,
        tools: Optional[list] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
        them: Optional[dict] = None,
    ) -> KetQuaChat:
        """Một lượt chat. Ném `BanError` khi bận, `VuotNganSachError` khi quá trần.

        ⛔ Không có tham số `fallback` ở đây, và đó là **có chủ ý** (luật 2). Việc
           chọn model lui là quyết định của tầng trên, và nó phải kèm theo việc
           **tính tiền theo model lui**.
        """
        if not model:
            raise CongVlmError("thieu ten model")

        than_gui: dict[str, Any] = {"model": model, "messages": list(messages)}
        if tools:
            than_gui["tools"] = list(tools)
        if max_tokens is not None:
            than_gui["max_tokens"] = int(max_tokens)
        if temperature is not None:
            than_gui["temperature"] = float(temperature)
        if reasoning_effort:
            than_gui["reasoning_effort"] = str(reasoning_effort)
        if them:
            than_gui.update(them)
        # Streaming đi đường khác — bóc `usage` từ SSE là việc riêng, và trộn hai
        # đường vào một hàm là cách chắc chắn nhất để tính tiền sai một trong hai.
        than_gui["stream"] = False

        ma, than, headers = _phan_hoi(self._goi("POST", "/v1/chat/completions", json=than_gui))

        if ma != 200:
            failure = decode_gateway_failure(ma, headers, _failure_body(than))
            detail = failure.as_detail()
            code = failure.canonical_code
            budget_codes = {
                "unsupported_modality",
                "image_count_exceeded",
                "image_too_large",
                "image_url_not_allowed",
                "image_decode_failed",
                "input_tokens_exceeded",
                "max_output_tokens_exceeded",
                "context_window_exceeded",
            }
            # Chỉ mã có cấu trúc quyết định NGỮ NGHĨA (Task 13): status HTTP
            # không sinh `canonical_code` — mã lạ fail-closed `upstream_unknown`.
            #
            # ⛔ NHƯNG status 4xx vẫn quyết định CHÍNH SÁCH, và đó là hai việc
            #    khác nhau (L-09, `tests/test_1244`): một phản hồi 4xx chứng minh
            #    YÊU CẦU sai, nó không chứng minh khoá/endpoint hỏng. Thiếu nhánh
            #    dưới thì mã lạ + 400 rơi vào `upstream_unknown`, mà mã ấy nằm
            #    trong `penalizes_key` ⇒ `danh_dau_loi` đếm lỗi khoá ⇒ năm ảnh
            #    hỏng của một khách tắt model nhà (thảm hoạ D-005, cửa thứ tư).
            #    Ngữ nghĩa vẫn là `upstream_unknown`; chỉ LỚP lỗi đổi.
            if failure.is_busy:
                raise BanError(failure.message, failure.retry_after_s, detail, failure=failure)
            if failure.is_cancelled:
                raise HuyError(failure.message, detail, failure=failure)
            if failure.is_timeout:
                raise AmbiguousProviderError(failure.message, ma=ma, failure=failure)
            if code == "provider_oom":
                raise ProviderOomError(failure.message, ma=ma, failure=failure)
            if code in budget_codes:
                raise VuotNganSachError(failure.message, detail, failure=failure)
            if code in {"invalid_request", "unsupported_parameter"}:
                raise YeuCauSaiError(failure.message, ma=ma, failure=failure)
            if 400 <= int(ma) < 500 and code not in {"unauthorized", "forbidden"}:
                raise YeuCauSaiError(failure.message, ma=ma, failure=failure)
            raise CongVlmError(failure.message, ma=ma, failure=failure)

        return _boc(than if isinstance(than, dict) else {})

    # ── nội bộ ───────────────────────────────────────────────────────────────
    def _goi(self, method: str, path: str, *, json: Any = None) -> tuple:
        try:
            return self.goi(method, path, json=json, timeout=self.timeout_s)
        except (BanError, HuyError):
            # ⛔ `HuyError` PHẢI đi cùng `BanError` ở đây. Hàm `goi` tiêm vào có
            #    thể tự nhận ra việc hủy trước ta (nó là bên cầm `httpx.Client`,
            #    nên nó là bên duy nhất phân biệt được "ta tự đóng" với "mạng
            #    chập" — xem `dieu_phoi._goi_openai`). Không có dòng này thì nhánh
            #    `except Exception` dưới sẽ bọc nó thành `AmbiguousProviderError`,
            #    và một lượt hủy lại trở thành một lượt "không rõ kết quả".
            raise
        except Exception as e:  # pragma: no cover
            if str(method).upper() == "POST":
                raise AmbiguousProviderError(
                    f"mat ket noi sau khi bat dau gui: {type(e).__name__}"
                ) from None
            raise CongVlmError(f"loi mang: {type(e).__name__}") from None


def _boc(than: dict) -> KetQuaChat:
    lua = (than.get("choices") or [{}])[0] or {}
    tin = lua.get("message") or {}
    goi_tool = tin.get("tool_calls") or []
    # `--reasoning-format deepseek` tách khối <think> ra `reasoning_content` —
    # nhưng chỉ ở `</think>` ĐẦU TIÊN. Budget cắt ngang ⇒ thẻ thứ hai lọt vào
    # `content` (llama.cpp#28182, T1b): trả phần lọt về suy nghĩ tại MỘT chỗ bóc
    # này, nên mọi cửa đồng bộ (`/chat/completions`, `/messages`, `/responses`
    # không stream, job) cùng sạch.
    noi_dung, suy_nghi = tach_the_lot(
        str(tin.get("content") or ""), str(tin.get("reasoning_content") or "")
    )
    return KetQuaChat(
        noi_dung=noi_dung,
        suy_nghi=suy_nghi,
        tool_calls=tuple(goi_tool),
        finish_reason=str(lua.get("finish_reason") or ""),
        model=str(than.get("model") or ""),
        su_dung=doc_su_dung(than),
        tho=than,
    )
