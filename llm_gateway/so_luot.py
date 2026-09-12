"""so_luot.py — sổ các lượt ĐANG BAY của cổng: hủy được, và ghi được một dòng.

Hai việc trong một vật thể, và đó là chủ ý: cả hai đều là *"thứ ta biết về một
lượt đang bay"*. Tách thành hai sổ nghĩa là hai chỗ phải cùng biết một
`request_id` còn sống hay đã chết, và hai chỗ ấy sẽ lệch nhau vào một ngày nào đó.

## Vì sao KHÔNG import `platform_core/llm/ngat.py`

`ngat.py` đã giải đúng bài này cho **máy A**: một sổ đóng nằm trong `ContextVar`,
vì không thêm được tham số vào `executor.run` (một hợp đồng app).

Cổng này **không thể** dùng lại chính mã ấy, và lý do là cấu trúc chứ không phải
thẩm mỹ: `llm_gateway` chạy trên **máy B**, nơi cây `platform_core` **không được
deploy** — `llm_gateway/deploy/kiem_import.py` chốt đúng điều đó ("`gia_token`
nam o platform_core tren MAY A, KHONG deploy sang may B: may B khong biet gia,
khong biet credit, khong biet nguoi dung", Q102). Một `import platform_core` ở
đây là một `ImportError` **lúc khởi động dịch vụ**, tức cổng chết chứ không phải
một tính năng thiếu.

⇒ Nên **khuôn** được dùng lại, không phải mã:

  * cùng `ContextVar` giữ một **danh sách thay đổi tại chỗ** (bản sao ngữ cảnh
    chép con trỏ, nên luồng khác đóng được thứ luồng này đang dùng);
  * cùng lý do *"không thêm được tham số"* — ở đây là `Upstream.json/stream`.
    `upstream.py` ghi rõ hình dạng hai hàm ấy **là điều kiện** để bộ test chạy
    được trên máy A bằng một bản giả, và `FakeUpstream` trong `test_250` cài đúng
    hai chữ ký đó. Thêm một tham số `dong-khi-huy` vào là bắt mọi bản giả khai
    lại chữ ký cho một việc chỉ `api.py` làm được.
  * cùng cảnh báo: ⛔ đừng đổi vật thể trong `SO_LUOT` thành một giá trị bất biến.

## Khác `ngat.py` MỘT điểm — và điểm đó là lý do tệp này tồn tại

`ngat` hủy từ **cùng một cây gọi** (cửa đang giữ request của khách). Ở đây người
hủy là **một request HTTP khác** (`POST /v1/huy`), nên hai bên không chia sẻ ngữ
cảnh nào cả — chỉ chia sẻ một cái tên. Vậy cần hai phép tra, không phải một:

    ContextVar  ->  "lượt CỦA TÔI là lượt nào"   (upstream ghi hàm đóng vào đây)
    SoLuot      ->  "lượt tên X đang ở đâu"      (`/v1/huy` tìm bằng đây)

## Dòng sổ: một lượt một dòng, và nó là một SỔ SÁCH

⛔ Một dòng thiếu số còn tệ hơn không có dòng nào — nó trông như một phép đo và
   trả lời sai. Nên khi thượng nguồn chết **trước khi `usage` về** (khách hủy,
   hết giờ, llama-server rơi), dòng vẫn được ghi nhưng mọi số token là `null` và
   `so_dang_tin: false`. Không bao giờ ghi `0`: `0 token` là một câu **khẳng
   định** ("lượt này rỗng"), còn `null` là một câu **thú nhận** ("không đo được").
   Hai câu ấy khác nhau đúng ở chỗ ai đọc sổ để tính tiền.

⛔ VÀ LUỒNG SSE KHÔNG BAO GIỜ CÓ `usage` Ở ĐÂY. Cổng chuyển tiếp SSE **nguyên
   xi** và tuyệt đối không phân tích lại (`upstream.stream` ghi lý do: một
   harness cộng đồng cắt delta bằng regex đã làm mất chữ giữa dòng). Nên với
   `stream=true` dòng sổ mang `so_dang_tin: false` và chỉ có thứ **cổng tự đo
   được**: TTFT và mã kết thúc. Ai cần token của lượt stream thì đọc `usage` ở
   máy A (`dem_token_luong.py`) hoặc `/metrics` của engine — không đọc ở đây.

⛔ KHÔNG NỘI DUNG. Không prompt, không phản hồi, không tên khách — cùng luật với
   `dem.py`. Một con số không rò rỉ được gì; một prompt thì rò rỉ tất cả.
"""
from __future__ import annotations

import contextvars
import json
import logging
import threading
from typing import Any, Callable, Optional

log = logging.getLogger("llm_gateway.so_luot")

#: Sổ riêng, KHÔNG dùng `llm_gateway.api`. Người trực grep một dòng sổ theo
#: `request_id` và không muốn 400 dòng `INFO` khác chen vào; và `gateway.log` có
#: thể lọc theo tên logger này để tách sổ khỏi log vận hành.
log_so = logging.getLogger("llm_gateway.so")

#: Lượt đang chạy trong ngữ cảnh này. `None` = không ai mở sổ (một lời gọi
#: `upstream.json` ngoài đường request, ví dụ `/running` lúc khởi động).
SO_LUOT: contextvars.ContextVar[Optional["Luot"]] = contextvars.ContextVar(
    "ltt_gw_luot", default=None)


class Luot:
    """Một lượt đang bay: các cửa ra mạng của nó, cờ hủy, và dòng sổ của nó.

    ⚠️ Vật thể này bị **hai luồng** chạm: luồng phục vụ request (ghi số đo) và
       luồng phục vụ `/v1/huy` (bật cờ, đóng cửa). Khoá bảo vệ danh sách cửa và
       cờ hủy — hai thứ mà một lần đọc-rồi-ghi hỏng sẽ để lại một socket mở.
       Các trường số đo chỉ luồng phục vụ ghi, nên chúng không cần khoá.
    """

    __slots__ = ("ma", "model", "giao_thuc", "gpu", "t0", "bam_gio",
                 "_khoa", "_cua", "da_huy", "stream",
                 "ma_http", "ket_thuc", "ttft_s",
                 "token_vao", "token_cache", "token_ra",
                 "prefill_tps", "decode_tps", "so_dang_tin")

    def __init__(self, *, ma: str = "", model: str = "", giao_thuc: str = "",
                 gpu: str = "", t0: float = 0.0, bam_gio=None):
        self.ma = ma
        self.model = model
        self.giao_thuc = giao_thuc
        self.gpu = gpu
        self.t0 = t0
        self.bam_gio = bam_gio
        self._khoa = threading.Lock()
        self._cua: list[Callable[[], None]] = []
        self.da_huy = False
        self.stream = False
        self.ma_http: Optional[int] = None
        self.ket_thuc = ""
        self.ttft_s: Optional[float] = None
        # ⛔ `None`, KHÔNG phải 0 — xem docstring module. `0` là một khẳng định.
        self.token_vao: Optional[int] = None
        self.token_cache: Optional[int] = None
        self.token_ra: Optional[int] = None
        self.prefill_tps: Optional[float] = None
        self.decode_tps: Optional[float] = None
        self.so_dang_tin = False

    # ── đường hủy ────────────────────────────────────────────────────────────
    def ghi_nhan(self, dong: Callable[[], None]) -> None:
        """Ghi một cửa ra mạng của lượt này.

        ⚠️ Đã hủy rồi mới ghi ⇒ đóng NGAY. Không có nhánh này thì một lượt bị hủy
           đúng lúc `httpx.Client` vừa dựng xong sẽ để lại một socket mở mà không
           ai đóng: `/v1/huy` đã chạy xong danh sách rỗng và không quay lại nữa.
        """
        with self._khoa:
            self._cua.append(dong)
            da = self.da_huy
        if da:
            _dong_mot(dong)

    def huy(self) -> int:
        """Bật cờ hủy rồi đóng mọi cửa. Trả số cửa đã đóng. Idempotent."""
        with self._khoa:
            self.da_huy = True
            cua = list(self._cua)
        n = 0
        for dong in cua:
            if _dong_mot(dong):
                n += 1
        return n

    # ── dòng sổ ──────────────────────────────────────────────────────────────
    def doc_than(self, than: bytes) -> None:
        """Bóc `usage` + `timings` từ thân phản hồi **không stream**.

        ⛔ Thân không đọc được / không có `usage` ⇒ để nguyên `None` và
           `so_dang_tin=False`. Đây là đúng trường hợp *"thượng nguồn chết trước
           khi `usage` về"*: dòng sổ vẫn ra, nhưng nó nói thật là nó không đo được.
        """
        try:
            d = json.loads(than or b"{}")
        except (ValueError, TypeError):
            return
        if not isinstance(d, dict):
            return
        usage = d.get("usage")
        timings = d.get("timings")
        if isinstance(timings, dict):
            self.prefill_tps = _so(timings.get("prompt_per_second"))
            self.decode_tps = _so(timings.get("predicted_per_second"))
            cache = _nguyen(timings.get("cache_n"))
            if cache is not None:
                self.token_cache = cache
        if isinstance(usage, dict):
            self.token_vao = _nguyen(usage.get("prompt_tokens"))
            self.token_ra = _nguyen(usage.get("completion_tokens"))
            if self.token_cache is None:
                ct = usage.get("prompt_tokens_details")
                if isinstance(ct, dict):
                    self.token_cache = _nguyen(ct.get("cached_tokens"))
            # `dang_tin` chỉ khi `usage` CÓ và đọc được — cùng luật `cong_vlm`
            # luật 3: không bao giờ để `usage` là số đoán.
            self.so_dang_tin = self.token_vao is not None
        lua = (d.get("choices") or [{}])
        if isinstance(lua, list) and lua and isinstance(lua[0], dict):
            self.ket_thuc = str(lua[0].get("finish_reason") or "") or self.ket_thuc

    def ghi_ttft(self, giay: float) -> None:
        if giay >= 0:
            self.ttft_s = round(float(giay), 3)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ma": self.ma or None,
            "model": self.model or None,
            "gpu": self.gpu or None,
            "giao_thuc": self.giao_thuc or None,
            "stream": self.stream,
            "ma_http": self.ma_http,
            "ket_thuc": self.ket_thuc or None,
            "huy": self.da_huy,
            "ttft_s": self.ttft_s,
            "token_vao": self.token_vao,
            "token_cache": self.token_cache,
            "token_ra": self.token_ra,
            "prefill_tps": self.prefill_tps,
            "decode_tps": self.decode_tps,
            "so_dang_tin": self.so_dang_tin,
        }


class SoLuot:
    """Sổ tra lượt theo mã, ở mức **tiến trình cổng**.

    ⚠️ Một sổ cho mỗi `create_app()`, không phải một biến module: bộ test dựng
       nhiều app trong cùng tiến trình, và một sổ dùng chung sẽ để lượt của app
       này hủy được bằng mã của app kia — một phép kiểm xanh vì lý do sai.

    ⚠️ Lượt KHÔNG mang `X-LTT-Request-Id` thì **không vào sổ**, tức không hủy
       được. Đó là hệ quả trực tiếp của việc cổng **dội lại** mã chứ không tự
       sinh (`_dau_ra` ghi lý do): một mã cổng tự đặt thì máy A không có gì để
       gọi `/v1/huy` bằng. Dòng sổ vẫn được ghi — chỉ thiếu `ma`.
    """

    __slots__ = ("_khoa", "_dang")

    def __init__(self) -> None:
        self._khoa = threading.Lock()
        self._dang: dict[str, Luot] = {}

    def dat(self, luot: Luot) -> None:
        if not luot.ma:
            return
        with self._khoa:
            self._dang[luot.ma] = luot

    def xoa(self, ma: str) -> None:
        if not ma:
            return
        with self._khoa:
            self._dang.pop(ma, None)

    def huy(self, ma: str) -> Optional[int]:
        """Đóng mọi cửa của lượt `ma`. `None` khi không có lượt nào tên ấy."""
        with self._khoa:
            luot = self._dang.get(ma)
        if luot is None:
            return None
        return luot.huy()

    def dang_chay(self) -> int:
        with self._khoa:
            return len(self._dang)


# ── hàm mức module: cửa mà `upstream.py` gọi ────────────────────────────────
def luot_nay() -> Optional[Luot]:
    return SO_LUOT.get()


def ghi_nhan(dong: Callable[[], None]) -> None:
    """`upstream` ghi hàm đóng của nó vào lượt của ngữ cảnh. Không có lượt ⇒ bỏ."""
    luot = SO_LUOT.get()
    if luot is not None:
        luot.ghi_nhan(dong)


def da_huy() -> bool:
    """Lượt của ngữ cảnh này đã bị hủy chưa.

    `upstream.json` hỏi câu này khi `httpx` ném: **cùng một ngoại lệ** có thể là
    "mạng chập" (⇒ 502, máy A ĐƯỢC đánh dấu lỗi khoá) hoặc "ta vừa tự đóng vì
    khách hủy" (⇒ 499, **không** được đánh dấu lỗi khoá). Không phân biệt được
    thì một lượt hủy sẽ tính thành năm lần nữa là tắt vĩnh viễn model nhà (D-005).
    """
    luot = SO_LUOT.get()
    return bool(luot is not None and luot.da_huy)


def ghi_so(luot: Luot) -> None:
    """Một dòng JSON cho một lượt. Không bao giờ ném — sổ không được làm hỏng lượt."""
    try:
        log_so.info("%s", json.dumps(luot.as_dict(), ensure_ascii=False,
                                     sort_keys=True))
    except Exception:  # noqa: BLE001 - ghi so khong duoc lam vo mot phan hoi
        log.exception("khong ghi duoc dong so cua luot %s", luot.ma or "?")


def _dong_mot(dong: Callable[[], None]) -> bool:
    """Đóng một cửa, nuốt lỗi.

    ⚠️ Nuốt có chủ ý, cùng lập luận `ngat.dong_het`: ta đang ở đường hủy và một
       `close()` hỏng không được che mất việc đóng những cửa còn lại. Nhưng nuốt
       **lặng lẽ** thì khác — nên nó ra log.
    """
    try:
        dong()
        return True
    except Exception:  # noqa: BLE001 - duong huy khong duoc nem
        log.exception("khong dong duoc cua ra mang khi huy luot")
        return False


def _nguyen(gt: Any) -> Optional[int]:
    try:
        return max(0, int(gt))
    except (TypeError, ValueError):
        return None


def _so(gt: Any) -> Optional[float]:
    try:
        return round(float(gt), 2)
    except (TypeError, ValueError):
        return None
