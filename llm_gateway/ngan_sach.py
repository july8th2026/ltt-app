"""
ngan_sach.py — chặn yêu cầu VƯỢT VÙNG ĐÃ ĐO **trước khi** nó chạm vào GPU. (H38)

⭐ VÌ SAO CÓ TỆP NÀY — cùng một bài học với `render_gateway/ngan_sach.py`. Ở đó là
   sự cố 22/08: một cấu hình **chưa từng được đo VRAM lần nào** được xếp vào chuỗi
   tự động không người canh. Ở đây rủi ro giống hệt, chỉ đổi đơn vị: **token thay
   cho điểm ảnh**.

   Một yêu cầu **rộng hơn cửa sổ của hồ sơ nó đi vào** sẽ không "chậm hơn một chút" —
   nó làm llama-server cắt ngữ cảnh hoặc chết lúc cấp phát, và trong cả hai trường
   hợp người dùng nhận về thứ sai mà không biết là sai.

   ⛔ Câu trên **từng ghi** một con số thật — `-c 204800`, **đã gỡ** — và đó là cửa sổ của
      thời **một** hồ sơ — **đã gỡ** từ khi máy B chạy hai model với hai cửa sổ
      khác nhau (L-14). Một ví dụ minh hoạ **không cần** con số thật: nó chỉ cần
      bất đẳng thức. `tests/test_981` bắt chính dòng này **ngay lần đầu nó collect
      được trở lại** — trước đó nó chết ở cấp module nên bộ dò nằm im suốt mấy
      ngày, và hai chỗ trôi đã ẩn được đúng trong cửa sổ đó.

⛔ NGUYÊN TẮC: **chưa đo thì không chạy.** Trần ở đây đọc từ `Config`, và số trong
   `Config` chỉ được nâng sau khi P5 đo thật và ghi vào `DECISIONS.md`.

⭐ ƯỚC LƯỢNG TOKEN Ở ĐÂY LÀ CỐ Ý THÔ VÀ CỐ Ý BẢO THỦ.

   llama-server **có** endpoint đếm chính xác (`/v1/chat/completions/input_tokens`),
   nhưng gọi nó **đánh thức model** — tức là đã chạm GPU, đúng thứ tệp này sinh ra
   để tránh. Nên ta chặn bằng ước lượng rẻ tiền ở tầng ngoài, và để llama-server tự
   lo phần chính xác ở tầng trong.

   Hệ quả phải chấp nhận: ước lượng **cao hơn thật**, nên đôi khi từ chối một yêu
   cầu lẽ ra vừa. Đó là chiều sai an toàn. Chiều ngược lại — cho lọt một yêu cầu
   vượt trần — mới là chiều nguy hiểm.

================================================================================
🔴 ĐO 03/09: "CAO HƠN THẬT" HOÁ RA LÀ TỚI **HAI LẦN**, VÀ ĐÓ LÀ MỘT LỖI THẬT

Đoạn trên đúng về *chiều* và sai về *độ lớn*. Đo bằng `/tokenize` của chính
model đang nạp, năm loại nội dung:

    JSON kieu Codex gui     1,42x     3,55 ky tu/token that
    ma Python (kho nay)     1,27x     3,17
    tieng Anh van xuoi      2,00x     5,00
    tieng Viet co dau       1,26x     3,14
    tron - phien agent      1,55x     3,87

⛔ VÀ ĐÂY LÀ CHỖ NÓ THÀNH LỖI, KHÔNG CHỈ THÀNH LÃNG PHÍ. Cổng này cưỡng chế
   bằng token **ƯỚC**; client (Codex, Claude Code) đếm token **THẬT**. Nên con
   số ta công bố cho client — và ngưỡng nén nó tính ra từ con số đó — **nằm ở
   một đơn vị khác** với thứ ta từ chối. Với hỗn hợp 1,55×, ta từ chối ở khoảng
   110.000 token thật trong khi nói với client rằng nó có 156.385 và hãy nén ở
   123.617.

   Không ngưỡng nén nào ở phía client ngăn được `413` khi hai bên đếm bằng hai
   đơn vị khác nhau. Đó là cơ chế thật của sự cố `413` ở 101.938/96.256, và
   **một ngưỡng nén đúng không sửa được nó**.

⭐ VÀ `/tokenize` KHÔNG PHẢI `/v1/chat/completions/input_tokens`. Đoạn ba dòng ở
   trên gộp hai endpoint làm một, và sự nhập nhằng đó là lý do phép đếm chính xác
   bị loại từ đầu. `/tokenize` **không chạy inference** — nó chỉ cần từ vựng của
   model đang nạp. Gọi hàng chục lần trong lô đo 03/09: không sinh một token nào.

⇒ Nên `kiem_tra` nay có **ba nhánh**, và nhánh nhanh không đổi:

       uoc <= tran                    -> NHAN ngay
       uoc >  tran, model DA NAP      -> /tokenize, quyet theo so THAT
       uoc >  tran, model CHUA NAP    -> tu choi theo uoc (khong danh thuc GPU)

   Nhánh một an toàn **vì** ước là số cao: ước vừa thì thật chắc chắn vừa.
   Nhánh ba giữ nguyên tính chất "413 trước khi chạm GPU" (đo 03/09: ≤0,02 s).
   Chỉ nhánh hai là mới, và nó chỉ **nới**, không bao giờ nới quá `tran`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any

from . import uoc_token as UT
from .error_contract import make_error

#: ⭐ PHÉP ƯỚC TOKEN là `llm_gateway/uoc_token.py` — CẬN TRÊN có chứng minh (docstring
#:    tệp ấy), bản giống hệt từng byte của `platform_core/llm/uoc_token.py` máy A
#:    (test_1470). A giữ chỗ bằng đúng hàm B đếm ⇒ "A nhận ⇒ B nhận" (A ⊆ B).
#:
#: 🔴 ĐÃ GỠ `KY_TU_MOI_TOKEN = 2.5` (Task 7, 18/09/2026). Đoạn cũ ở đây cãi rằng
#:    2,5 "bảo thủ quá cho mọi thứ" — đúng với văn xuôi Anh (2,25×), SAI với code
#:    (0,74×), chữ Trung (0,42×), hex (0,45×), emoji (0,16×): ước THIẾU ⇒ đường
#:    nhanh "ước vừa trần ⇒ nhận ngay" cho lọt yêu cầu tràn KV.

#: Token quy cho MỘT ảnh khi chưa biết độ phân giải thật.
#:
#: Qwen3.8 lấy mẫu ảnh theo ô vá; một ảnh chụp màn hình cỡ 1080p rơi vào khoảng
#: 1.000–1.600 token. Lấy **2.048** cho chắc — nếu ước cao thì chỉ mất một chỗ
#: trong ngân sách, còn ước thấp thì tràn ngữ cảnh.
#:
#: Tên `TOKEN_GIU_MOI_ANH` (Task 11, 18/09) — khớp `apps/ltt_llm/ngan_sach.HO_SO[m]
#: .token_giu_moi_anh` (test `test_1201`), và KHÔNG trùng tên `TOKEN_MOI_ANH = 770`
#: (số ĐO dùng cho hoá đơn ở máy A).
TOKEN_GIU_MOI_ANH = 2048

_DATA_URL = re.compile(r"^data:(?P<mime>[\w.+-]+/[\w.+-]+)?;base64,", re.I)


class VuotNganSach(ValueError):
    """Yêu cầu vượt trần đã đo. Mang theo lý do đọc được cho người dùng."""

    def __init__(self, code: str, ly_do: str, *, truong: str = "", tran: int = 0,
                 thay: int = 0):
        super().__init__(ly_do)
        self.code = code
        self.ly_do = ly_do
        self.truong = truong
        self.tran = tran
        self.thay = thay

    def as_dict(self, *, request_id: str) -> dict[str, Any]:
        """Phong bì v1, kèm đúng hình dạng cũ trong một chu kỳ chuyển tiếp."""
        legacy = {"ly_do": self.ly_do, "truong": self.truong,
                  "tran": self.tran, "thay": self.thay}
        envelope = make_error(
            self.code,
            request_id=request_id,
            field=self.truong or None,
            limit=self.tran,
            actual=self.thay,
        )
        # Các khóa legacy ở cả tầng ngoài và `legacy`: máy A hiện hành vẫn đọc
        # tầng ngoài; máy A mới đọc phong bì v1. Nhờ vậy B có thể đi trước và A
        # vẫn lùi phiên bản độc lập trong cửa sổ chuyển tiếp.
        return {**envelope, **legacy, "legacy": legacy}


@dataclass(frozen=True)
class KetQuaDo:
    """Kết quả đo một yêu cầu, để ghi log và trả trong header."""

    token_van_ban: int
    so_anh: int
    token_anh: int
    byte_anh_lon_nhat: int
    #: URL ảnh KHÔNG phải `data:` — mỗi cái là một đường SSRF tiềm năng.
    url_tu_xa: tuple = ()
    #: Mọi đoạn văn bản đã gom, để `kiem_tra` đếm **thật** khi cần.
    #:
    #: ⛔ Giữ tham chiếu chứ không chép: chúng đã nằm trong `body` trong bộ nhớ,
    #:    nên đây không phải một bản sao thứ hai của một hội thoại 400 KB.
    van_ban: tuple = ()
    #: Số token **thật** do `/tokenize` trả về, khi đã hỏi. `None` = chưa hỏi.
    #:
    #: ⭐ `None` KHÁC 0. Không phân biệt được hai thứ đó thì một lần "không hỏi
    #:    được" trông y hệt một yêu cầu rỗng — và một yêu cầu rỗng thì vừa mọi
    #:    trần, tức lỗi sẽ nghiêng về chiều nguy hiểm.
    token_that: "int | None" = None
    #: Token KHUÔN CHAT (đã nằm trong `token_van_ban`). `/tokenize` chỉ đếm các đoạn
    #: văn bản, không đếm khuôn — nên số THẬT phải cộng lại phần này.
    token_khuon: int = 0

    @property
    def token_vao(self) -> int:
        """Token vào **dùng để phán xử**: số thật nếu đã đếm, không thì số ước."""
        if self.token_that is not None:
            return self.token_that + self.token_khuon + self.token_anh
        return self.token_van_ban + self.token_anh

    @property
    def token_vao_uoc(self) -> int:
        """Số ƯỚC, luôn có. Dùng cho log và header — để đọc log biết được ta
        phán xử bằng số nào."""
        return self.token_van_ban + self.token_anh


def _do_anh(url: str) -> int:
    """Byte thật của một ảnh `data:` URL. Trả 0 nếu là URL thường (không tải về).

    ⛔ KHÔNG tải ảnh từ URL ngoài ở đây. Cổng này không được đi ra Internet —
       một yêu cầu chứa `image_url` trỏ ra ngoài là một đường SSRF, và Q102 nói
       máy B không giữ bí mật nào, nên nó cũng không được làm proxy ra ngoài.
    """
    m = _DATA_URL.match(url or "")
    if not m:
        return 0
    phan = (url or "").split(",", 1)
    if len(phan) != 2:
        return 0
    # len(base64) * 3/4 là kích thước sau giải mã, không cần giải mã thật.
    return (len(phan[1]) * 3) // 4


def do_yeu_cau(body: dict[str, Any]) -> KetQuaDo:
    """Đo một body của bất kỳ giao thức nào trong ba giao thức cổng phục vụ.

    ⭐ Gom văn bản bằng `uoc_token.gom_than` — CÙNG hàm máy A dùng (qua bản sao
       `platform_core/llm/uoc_token.py`): đi mọi chuỗi của mọi tin nhắn (cả
       `tool_calls`, `tool_use.input`, `function_call.arguments`), khối tool đếm
       nguyên JSON gọn, ảnh tách riêng. `token_van_ban` = văn bản + khuôn chat.
    """
    van_ban: list[str] = []
    anh: list[str] = []
    so_tin, so_tool = UT.gom_than(body, van_ban, anh)
    khuon = UT.khuon(so_tin, so_tool)

    byte_lon_nhat = max((_do_anh(u) for u in anh), default=0)
    # Ảnh nào KHÔNG mở đầu bằng `data:...;base64,` thì là một địa chỉ để ai đó đi
    # tải — và bên đi tải sẽ là máy B. Gom lại để `kiem_tra` từ chối.
    tu_xa = tuple(u for u in anh if u and not _DATA_URL.match(u))
    return KetQuaDo(
        token_van_ban=UT.uoc_doan(van_ban) + khuon,
        so_anh=len(anh),
        token_anh=len(anh) * TOKEN_GIU_MOI_ANH,
        byte_anh_lon_nhat=byte_lon_nhat,
        url_tu_xa=tu_xa,
        van_ban=tuple(van_ban),
        token_khuon=khuon,
    )


def kiem_tra(body: dict[str, Any], *, max_input_tokens: int, max_output_tokens: int,
             max_images: int, max_image_bytes: int, max_context: int,
             co_vision: bool, dem_that=None) -> KetQuaDo:
    """Ném `VuotNganSach` nếu yêu cầu vượt bất kỳ trần nào. Không chạm GPU.

    `dem_that` — tuỳ chọn — là một hàm `(list[str]) -> int | None` đếm token
    **thật** của các đoạn văn bản, hoặc trả `None` khi không đếm được lúc này
    (model chưa nạp, thượng nguồn không trả lời). Xem ba nhánh ở docstring đầu
    tệp.

    ⛔ `dem_that` chỉ được gọi khi phép **ước** đã vượt trần. Đường nhanh —
       tuyệt đại đa số yêu cầu — không thêm một round-trip nào, và đó là điều
       kiện để thay đổi này không phải một cái giá trả mỗi lượt.
    """
    do = do_yeu_cau(body)

    if do.so_anh and not co_vision:
        raise VuotNganSach(
            "unsupported_modality",
            "Ho so model nay khong nap vision. Goi model co vision thay vi model nay.",
            truong="images", tran=0, thay=do.so_anh)

    if do.so_anh > max_images:
        raise VuotNganSach("image_count_exceeded",
                           "Qua nhieu anh trong mot yeu cau.",
                           truong="images", tran=max_images, thay=do.so_anh)

    # 🔒 CHỈ NHẬN ẢNH `data:` — TỪ CHỐI MỌI URL TỪ XA.
    #
    #    Nếu ta chuyển tiếp một `image_url` trỏ ra ngoài, **máy B** sẽ là bên đi
    #    tải nó. Khách gửi `http://127.0.0.1:8188/...` là bắt máy B gọi vào chính
    #    mạng nội bộ của nó — đó là SSRF, và ComfyUI ở cổng 8188 **không có xác
    #    thực**.
    #
    #    Đo thật 22/08: llama-server hiện **từ chối** URL http (trả 400). Nhưng đó
    #    là một bảo đảm ĐI MƯỢN — nó phụ thuộc hành vi của thượng nguồn và có thể
    #    đổi ở một bản nâng cấp. Chốt ở đây làm nó thành bảo đảm CỦA TA.
    if do.url_tu_xa:
        raise VuotNganSach(
            "image_url_not_allowed",
            "Chi nhan anh dang data: URL (base64). URL tu xa bi tu choi.",
            truong="image_url", tran=0, thay=len(do.url_tu_xa))

    if do.byte_anh_lon_nhat > max_image_bytes:
        raise VuotNganSach("image_too_large", "Anh qua lon.", truong="image_bytes",
                           tran=max_image_bytes, thay=do.byte_anh_lon_nhat)

    # `max_tokens` (Chat/Anthropic) và `max_output_tokens` (Responses) là cùng một thứ.
    xin_ra = body.get("max_tokens")
    if xin_ra is None:
        xin_ra = body.get("max_output_tokens")
    xin_ra = int(xin_ra) if isinstance(xin_ra, (int, float)) else max_output_tokens
    if xin_ra > max_output_tokens:
        raise VuotNganSach("max_output_tokens_exceeded",
                           "Xin sinh ra qua nhieu token.", truong="max_tokens",
                           tran=max_output_tokens, thay=xin_ra)

    # ── NHÁNH HAI: ước đã vượt trần, hỏi số THẬT trước khi từ chối ──────────
    #
    # ⭐ Chỉ vào đây khi **ước** đã vượt. Ước là số CAO, nên ước vừa ⇒ thật chắc
    #    chắn vừa, và ta không tốn một round-trip nào cho đường nhanh.
    #
    # ⛔ `dem_that` trả `None` = "không đếm được lúc này" (model chưa nạp, hoặc
    #    thượng nguồn không trả lời). Khi đó ta **giữ nguyên** phán xử theo ước.
    #    Đó là chiều sai an toàn, và nó giữ đúng tính chất đã đo 03/09: một
    #    yêu cầu quá to bị chặn trong ≤0,02 s mà không đánh thức GPU.
    if do.token_vao > max_input_tokens and dem_that is not None and do.van_ban:
        that = None
        try:
            that = dem_that(list(do.van_ban))
        except Exception:                                     # noqa: BLE001
            # Một đường ĐẾM mà ném thì không được phép làm vỡ đường phục vụ.
            # Không đếm được thì lùi về ước, y như `None`.
            that = None
        if isinstance(that, int) and that >= 0:
            do = replace(do, token_that=that)

    if do.token_vao > max_input_tokens:
        raise VuotNganSach("input_tokens_exceeded",
                           "Dau vao vuot tran token.", truong="input_tokens",
                           tran=max_input_tokens, thay=do.token_vao)

    # Vào + ra phải cùng nằm trong cửa sổ ngữ cảnh của hồ sơ. Đây là chốt bắt được
    # trường hợp mà hai chốt trên bỏ lọt: mỗi cái vừa trần của nó, cộng lại thì tràn.
    if do.token_vao + xin_ra > max_context:
        raise VuotNganSach(
            "context_window_exceeded",
            "Dau vao cong dau ra vuot cua so ngu canh cua ho so model.",
            truong="context", tran=max_context, thay=do.token_vao + xin_ra)

    return do
