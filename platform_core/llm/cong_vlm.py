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

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

#: Không biết còn bao lâu thì coi như LÂU. Không bao giờ lạc quan.
ETA_KHONG_BIET = None


class CongVlmError(Exception):
    """Cổng VLM hỏng thật. Bên gọi ĐƯỢC quyền tính đây là lỗi provider.

    ⭐ `ma` — **mã HTTP thượng nguồn**, thêm 13/09 (L-09). Không có nó thì
       `dieu_phoi` gọi `api_pool.danh_dau_loi(db, key)` mà không nói được lỗi
       thuộc loại nào, và `danh_dau_loi` đọc `http_status=None` thành *"5xx hoặc
       lỗi mạng"* ⇒ `error_count += 1`. Năm lần là `APIKEY_ERROR`, thứ **không
       tự hồi**.

    🔴 Hậu quả đo được: một khách gửi **năm ảnh hỏng** là tắt model nhà cho tới
       khi có người sửa tay. Chính `danh_dau_loi` đã có nhánh đúng —
       *"400 ≤ s < 500: Bad request CỦA TA — KHÔNG phạt"* — nhưng nhánh ấy chỉ
       chạy khi ai đó **truyền mã vào**.
    """

    def __init__(self, thong_diep: str = "", *, ma: Optional[int] = None):
        super().__init__(thong_diep)
        #: Mã HTTP thượng nguồn, `None` khi lỗi không đến từ một phản hồi HTTP.
        self.ma = ma


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

    def __init__(self, ly_do: str, retry_after_s: Optional[float] = None,
                 chi_tiet: Optional[dict] = None):
        super().__init__(ly_do or "may B dang ban")
        self.ly_do = ly_do
        self.retry_after_s = retry_after_s
        self.chi_tiet = chi_tiet or {}


#: Cổng trả mã này khi lượt bị **hủy theo yêu cầu**. Quy ước của nginx cho
#: *"client đã đóng"*; cả hai đầu là mã của ta nên dùng nó là đúng nghĩa.
MA_HUY = 499


class HuyError(Exception):
    """Lượt bị HỦY theo yêu cầu. **KHÔNG PHẢI LỖI** — của ai cả.

    🔴 VÌ SAO KHÔNG PHẢI `CongVlmError`, VÀ ĐÂY LÀ LUẬT THỨ NĂM CỦA TỆP NÀY.
       `CongVlmError` là giấy phép cho bên gọi `api_pool.danh_dau_loi()`; năm lần
       là `key.status = APIKEY_ERROR`, thứ **không tự hồi** (`_ung_vien` bỏ mọi
       khoá `status != ACTIVE`, chỉ `COOLDOWN` tự về). Tức **năm lần khách bấm
       "dừng" là model nhà tắt vĩnh viễn** — đúng thảm hoạ D-005 mà luật 1 đã bịt
       ở cửa 429 và luật 504 đã bịt ở cửa hết giờ. Đây là cửa thứ ba.

    🔴 VÀ VÌ SAO KHÔNG DÙNG LẠI `BanError` cho gọn. `dieu_phoi` đọc `BanError` là
       *"đi tiếp provider sau"*. Với model nội bộ, `canonical.THU_TU_PROVIDER` có
       **một** phần tử — nên "đi tiếp" là cạn danh sách ⇒ `KhongCoProviderNao`,
       một thông điệp nói "không provider nào phục vụ được" cho một lượt mà chính
       khách vừa hủy. Nguyên nhân thật bị che, và người đọc log sẽ đi tìm máy B.

    ⇒ Một lớp riêng, không họ hàng với `CongVlmError`: **không** cascade, **không**
      đánh dấu lỗi khoá, và bên gọi nhìn tên là biết chuyện gì.
    """

    def __init__(self, ly_do: str = "", chi_tiet: Optional[dict] = None):
        super().__init__(ly_do or "luot bi huy theo yeu cau")
        self.ly_do = ly_do
        self.chi_tiet = chi_tiet or {}


class VuotNganSachError(Exception):
    """Yêu cầu vượt trần của cổng (413). Thử lại y hệt sẽ hỏng y hệt.

    Tách khỏi `CongVlmError` vì lý do vận hành: đây **không** phải lỗi của máy B,
    và `api_pool` không được đánh dấu lỗi cho key vì nó.
    """

    def __init__(self, ly_do: str, chi_tiet: Optional[dict] = None):
        super().__init__(ly_do or "vuot ngan sach")
        self.ly_do = ly_do
        self.chi_tiet = chi_tiet or {}


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
    return SuDung(token_vao=vao, token_ra=ra,
                  token_vao_cache=min(cache, vao), dang_tin=True)


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
        ma, than = self._goi("GET", "/health")
        if ma != 200:
            raise CongVlmError(f"health tra {ma}")
        return than or {}

    def models(self) -> list:
        ma, than = self._goi("GET", "/v1/models")
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
    def chat(self, *, model: str, messages: list, tools: Optional[list] = None,
             max_tokens: Optional[int] = None, temperature: Optional[float] = None,
             reasoning_effort: Optional[str] = None,
             them: Optional[dict] = None) -> KetQuaChat:
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

        ma, than = self._goi("POST", "/v1/chat/completions", json=than_gui)

        if ma == 429:
            # ⛔ ĐÂY là chỗ luật 1 sống. Không nâng thành lỗi, không đổi provider.
            ct = than if isinstance(than, dict) else {}
            raise BanError(str((ct.get("detail") or {}).get("chi_tiet")
                               or ct.get("ly_do") or "may B dang ban"),
                           chi_tiet=ct)
        if ma == MA_HUY:
            # ⛔ ĐỨNG Ở ĐÂY, TRƯỚC nhánh `ma != 200` cuối hàm. Rơi xuống đó là
            #    `CongVlmError`, tức giấy phép đánh dấu lỗi khoá — xem `HuyError`.
            ct = than if isinstance(than, dict) else {}
            raise HuyError(str(ct.get("ly_do") or "huy theo yeu cau"), chi_tiet=ct)
        if ma == 413:
            ct = than if isinstance(than, dict) else {}
            raise VuotNganSachError("yeu cau vuot tran cua cong", chi_tiet=ct)
        if ma == 404:
            raise CongVlmError(f"model '{model}' khong co hoac chua duoc mo")
        if ma == 504:
            # 🔴 HẾT GIỜ Ở THƯỢNG NGUỒN **KHÔNG PHẢI** LỖI CỦA KHOÁ.
            #
            #    Cổng trả 504 khi `llama-swap`/`llama-server` không trả lời kịp.
            #    Trước 09/09 nó nằm chung cửa 502, và 502 rơi vào nhánh cuối
            #    (`CongVlmError`) ⇒ `api_pool.danh_dau_loi()` ⇒ sau **5** lần
            #    `key.status = APIKEY_ERROR`.
            #
            # ⛔ Và `APIKEY_ERROR` **KHÔNG TỰ HỒI**: `api_pool._ung_vien` bỏ mọi
            #    khoá `status != ACTIVE`, còn tự hồi thì chỉ có `COOLDOWN`. Tức
            #    năm lần hết giờ là model nhà tắt và **ở lại tắt** tới khi có
            #    người vào sửa tay.
            #
            # ⭐ Đó đúng là D-005 — thảm hoạ mà luật 1 ở đầu tệp này đã bịt rất
            #    kỹ ở cửa **429** — chỉ là nó vào bằng cửa **hết giờ**, cửa chưa
            #    ai bịt. Một prompt 200K prefill hàng phút là hành vi **bình
            #    thường** của hệ này, không phải dấu hiệu máy B hỏng.
            #
            # ⚠️ Dùng `AmbiguousProviderError` chứ **không** đẻ lớp mới, và đó là
            #    lựa chọn có lý do: ngữ nghĩa của nó đã đúng y hệt — *"đã gửi đi
            #    nhưng không biết kết quả"*. `dieu_phoi.goi()` sẵn có nhánh
            #    `except (AmbiguousProviderError, ProviderOomError): raise` nên
            #    lượt này **không cascade** (thượng nguồn có thể đã bắt đầu sinh
            #    chữ, thử lại nơi khác là trả tiền hai lần) và **không**
            #    `danh_dau_loi`. Thêm một lớp mới sẽ phải chép lại đúng hai hành
            #    vi ấy, và bản chép sẽ lệch vào một ngày nào đó.
            raise AmbiguousProviderError(
                "thuong nguon khong tra loi kip (504) — khong danh dau loi cho khoa")
        noi_dung_loi = str(than or "").lower()
        if ma in (500, 502, 503, 507) and any(
                marker in noi_dung_loi for marker in
                ("out of memory", "cuda oom", "cuda_error_out_of_memory", "oom")):
            raise ProviderOomError("provider khong du bo nho cho request")
        if ma in (400, 422):
            # ⛔ ĐỨNG TRƯỚC nhánh cuối. Rơi xuống đó là `CongVlmError` trần, tức
            #    giấy phép phạt key cho một lỗi của khách — xem `YeuCauSaiError`.
            than_sai = than if isinstance(than, dict) else {}
            _e = than_sai.get("error")
            loi_sai = _e if isinstance(_e, dict) else {}
            raise YeuCauSaiError(
                str(loi_sai.get("message") or than_sai.get("detail")
                    or f"thuong nguon tra {ma}"), ma=ma)
        if ma != 200:
            raise CongVlmError(f"/v1/chat/completions tra {ma}", ma=ma)

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
        except Exception as e:                       # pragma: no cover
            if str(method).upper() == "POST":
                raise AmbiguousProviderError(
                    f"mat ket noi sau khi bat dau gui: {type(e).__name__}") from None
            raise CongVlmError(f"loi mang: {type(e).__name__}") from None


def _boc(than: dict) -> KetQuaChat:
    lua = (than.get("choices") or [{}])[0] or {}
    tin = lua.get("message") or {}
    goi_tool = tin.get("tool_calls") or []
    return KetQuaChat(
        noi_dung=str(tin.get("content") or ""),
        # `--reasoning-format deepseek` tách khối <think> ra đây.
        suy_nghi=str(tin.get("reasoning_content") or ""),
        tool_calls=tuple(goi_tool),
        finish_reason=str(lua.get("finish_reason") or ""),
        model=str(than.get("model") or ""),
        su_dung=doc_su_dung(than),
        tho=than,
    )
