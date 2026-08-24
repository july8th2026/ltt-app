"""
ngan_sach.py — chặn yêu cầu VƯỢT VÙNG ĐÃ ĐO **trước khi** nó chạm vào GPU. (H38)

⭐ VÌ SAO CÓ TỆP NÀY — cùng một bài học với `render_gateway/ngan_sach.py`. Ở đó là
   sự cố 22/08: một cấu hình **chưa từng được đo VRAM lần nào** được xếp vào chuỗi
   tự động không người canh. Ở đây rủi ro giống hệt, chỉ đổi đơn vị: **token thay
   cho điểm ảnh**.

   Một yêu cầu 300K token gửi vào hồ sơ `-c 204800` sẽ không "chậm hơn một chút" —
   nó làm llama-server cắt ngữ cảnh hoặc chết lúc cấp phát, và trong cả hai trường
   hợp người dùng nhận về thứ sai mà không biết là sai.

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
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any

#: Số ký tự trên một token, dùng để ƯỚC LƯỢNG.
#:
#: Tokenizer của Qwen nuốt khoảng 3,5–4 ký tự tiếng Anh cho một token, và **ít hơn
#: hẳn với tiếng Việt có dấu** (dấu tiếng Việt tốn thêm byte UTF-8, và tokenizer
#: cắt nhỏ hơn). Lấy **2,5** để nghiêng về phía ước lượng CAO.
#:
#: ⚠️ Đây không phải hằng của model. Nó là một mốc an toàn. Đừng nâng nó lên cho
#:    "lọt được nhiều yêu cầu hơn" — đó là chọn một con số khác cũng chưa ai đo.
KY_TU_MOI_TOKEN = 2.5

#: Token quy cho MỘT ảnh khi chưa biết độ phân giải thật.
#:
#: Qwen3.8 lấy mẫu ảnh theo ô vá; một ảnh chụp màn hình cỡ 1080p rơi vào khoảng
#: 1.000–1.600 token. Lấy **2.048** cho chắc — nếu ước cao thì chỉ mất một chỗ
#: trong ngân sách, còn ước thấp thì tràn ngữ cảnh.
TOKEN_MOI_ANH = 2048

_DATA_URL = re.compile(r"^data:(?P<mime>[\w.+-]+/[\w.+-]+)?;base64,", re.I)


class VuotNganSach(ValueError):
    """Yêu cầu vượt trần đã đo. Mang theo lý do đọc được cho người dùng."""

    def __init__(self, ly_do: str, *, truong: str = "", tran: int = 0, thay: int = 0):
        super().__init__(ly_do)
        self.ly_do = ly_do
        self.truong = truong
        self.tran = tran
        self.thay = thay

    def as_dict(self) -> dict[str, Any]:
        return {"ly_do": self.ly_do, "truong": self.truong,
                "tran": self.tran, "thay": self.thay}


@dataclass(frozen=True)
class KetQuaDo:
    """Kết quả đo một yêu cầu, để ghi log và trả trong header."""

    token_van_ban: int
    so_anh: int
    token_anh: int
    byte_anh_lon_nhat: int
    #: URL ảnh KHÔNG phải `data:` — mỗi cái là một đường SSRF tiềm năng.
    url_tu_xa: tuple = ()

    @property
    def token_vao(self) -> int:
        return self.token_van_ban + self.token_anh


def _uoc_token(s: str) -> int:
    if not s:
        return 0
    return int(len(s) / KY_TU_MOI_TOKEN) + 1


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


def _duyet_noi_dung(noi_dung: Any, ra: list[str], anh: list[str]) -> None:
    """Gom mọi chuỗi văn bản và mọi ảnh trong một `content` bất kỳ.

    Nhận cả ba hình dạng đang lưu hành, vì cổng phục vụ ba giao thức:
    OpenAI Chat (`{"type": "image_url", "image_url": {"url": ...}}`),
    OpenAI Responses (`{"type": "input_image", "image_url": ...}`),
    Anthropic Messages (`{"type": "image", "source": {"data": ...}}`).
    """
    if noi_dung is None:
        return
    if isinstance(noi_dung, str):
        ra.append(noi_dung)
        return
    if isinstance(noi_dung, list):
        for phan in noi_dung:
            _duyet_noi_dung(phan, ra, anh)
        return
    if not isinstance(noi_dung, dict):
        return

    loai = str(noi_dung.get("type") or "")

    if loai in ("text", "input_text", "output_text"):
        ra.append(str(noi_dung.get("text") or ""))
        return

    if loai == "image_url":                       # OpenAI Chat
        gt = noi_dung.get("image_url")
        anh.append(str(gt.get("url") if isinstance(gt, dict) else gt or ""))
        return

    if loai == "input_image":                     # OpenAI Responses
        anh.append(str(noi_dung.get("image_url") or ""))
        return

    if loai == "image":                           # Anthropic Messages
        nguon = noi_dung.get("source") or {}
        if isinstance(nguon, dict):
            du_lieu = nguon.get("data")
            if du_lieu:
                # Anthropic gửi base64 trần, không có tiền tố `data:`.
                anh.append("data:;base64," + str(du_lieu))
            else:
                anh.append(str(nguon.get("url") or ""))
        return

    # Kiểu lạ: vẫn gom mọi chuỗi bên trong để không đếm thiếu.
    for gt in noi_dung.values():
        if isinstance(gt, (str, list, dict)):
            _duyet_noi_dung(gt, ra, anh)


def do_yeu_cau(body: dict[str, Any]) -> KetQuaDo:
    """Đo một body của bất kỳ giao thức nào trong ba giao thức cổng phục vụ."""
    van_ban: list[str] = []
    anh: list[str] = []

    # `system` của Anthropic nằm ngoài `messages`.
    _duyet_noi_dung(body.get("system"), van_ban, anh)
    # `instructions` của Responses API cũng vậy.
    _duyet_noi_dung(body.get("instructions"), van_ban, anh)

    for khoa in ("messages", "input"):
        gt = body.get(khoa)
        if isinstance(gt, str):
            van_ban.append(gt)
        elif isinstance(gt, list):
            for tin in gt:
                if isinstance(tin, dict):
                    _duyet_noi_dung(tin.get("content", tin), van_ban, anh)
                else:
                    _duyet_noi_dung(tin, van_ban, anh)

    # Mô tả tool cũng chiếm ngữ cảnh, và với Codex thì chúng **không nhỏ**.
    for khoa in ("tools", "functions"):
        gt = body.get(khoa)
        if isinstance(gt, list):
            for t in gt:
                _duyet_noi_dung(t, van_ban, anh)

    byte_lon_nhat = max((_do_anh(u) for u in anh), default=0)
    # Ảnh nào KHÔNG mở đầu bằng `data:...;base64,` thì là một địa chỉ để ai đó đi
    # tải — và bên đi tải sẽ là máy B. Gom lại để `kiem_tra` từ chối.
    tu_xa = tuple(u for u in anh if u and not _DATA_URL.match(u))
    return KetQuaDo(
        token_van_ban=sum(_uoc_token(s) for s in van_ban),
        so_anh=len(anh),
        token_anh=len(anh) * TOKEN_MOI_ANH,
        byte_anh_lon_nhat=byte_lon_nhat,
        url_tu_xa=tu_xa,
    )


def kiem_tra(body: dict[str, Any], *, max_input_tokens: int, max_output_tokens: int,
             max_images: int, max_image_bytes: int, max_context: int,
             co_vision: bool) -> KetQuaDo:
    """Ném `VuotNganSach` nếu yêu cầu vượt bất kỳ trần nào. Không chạm GPU."""
    do = do_yeu_cau(body)

    if do.so_anh and not co_vision:
        raise VuotNganSach(
            "Ho so model nay khong nap vision. Goi model co vision thay vi model nay.",
            truong="images", tran=0, thay=do.so_anh)

    if do.so_anh > max_images:
        raise VuotNganSach("Qua nhieu anh trong mot yeu cau.",
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
            "Chi nhan anh dang data: URL (base64). URL tu xa bi tu choi.",
            truong="image_url", tran=0, thay=len(do.url_tu_xa))

    if do.byte_anh_lon_nhat > max_image_bytes:
        raise VuotNganSach("Anh qua lon.", truong="image_bytes",
                           tran=max_image_bytes, thay=do.byte_anh_lon_nhat)

    # `max_tokens` (Chat/Anthropic) và `max_output_tokens` (Responses) là cùng một thứ.
    xin_ra = body.get("max_tokens")
    if xin_ra is None:
        xin_ra = body.get("max_output_tokens")
    xin_ra = int(xin_ra) if isinstance(xin_ra, (int, float)) else max_output_tokens
    if xin_ra > max_output_tokens:
        raise VuotNganSach("Xin sinh ra qua nhieu token.", truong="max_tokens",
                           tran=max_output_tokens, thay=xin_ra)

    if do.token_vao > max_input_tokens:
        raise VuotNganSach("Dau vao vuot tran token.", truong="input_tokens",
                           tran=max_input_tokens, thay=do.token_vao)

    # Vào + ra phải cùng nằm trong cửa sổ ngữ cảnh của hồ sơ. Đây là chốt bắt được
    # trường hợp mà hai chốt trên bỏ lọt: mỗi cái vừa trần của nó, cộng lại thì tràn.
    if do.token_vao + xin_ra > max_context:
        raise VuotNganSach(
            "Dau vao cong dau ra vuot cua so ngu canh cua ho so model.",
            truong="context", tran=max_context, thay=do.token_vao + xin_ra)

    return do
