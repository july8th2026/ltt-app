"""
ngan_sach.py — chặn cấu hình VƯỢT VÙNG ĐÃ ĐO trước khi nó chạm vào GPU. (H37)

⭐ VÌ SAO CÓ TỆP NÀY — SỰ CỐ THẬT 22/08/2026 (D-024): máy B **khởi động lại đột
   ngột** giữa một lô ảnh. Cấu hình đang chạy chiếm **23,9 / 24,6 GB = 97,5 % VRAM**
   và **ở lì đó giữa các job**. Không còn chỗ cho hệ điều hành lẫn dự án video dùng
   chung. Và lượt sắp chạy ngay sau đó là chế độ `subject` với **hai ảnh tham chiếu
   4 MP** — một cấu hình **chưa từng được đo VRAM lần nào**, xếp trong một chuỗi tự
   động không người canh.

⛔ NGUYÊN TẮC: **chưa đo thì không chạy.** Không phải "ước lượng rồi thử" — máy B
   là máy dùng chung, và cái giá của một lần đoán sai là chủ dự án mất máy.

   Đây đúng tinh thần fail-closed của Q92 ở Public API: bật cờ **không** tự mở tool
   nào. Ở đây: model chạy được ở một độ phân giải **không** có nghĩa là nó chạy được
   khi thêm ảnh tham chiếu.

⭐ TOKEN LÀ THƯỚC ĐO, KHÔNG PHẢI ĐIỂM ẢNH. HiDream-O1 có `PATCH_SIZE = 32` (đọc
   trong `comfy_extras/nodes_hidream_o1.py`), nên một khung W×H tốn `(W/32)·(H/32)`
   token, và **ảnh tham chiếu nối thêm token vào cùng chuỗi đó** — chúng đi vào
   `reference_latents` của conditioning, tức là vào chính chuỗi mà attention phải
   xử lý. D-019 đã đo: **thời gian tỉ lệ thuận với token**. Bộ nhớ attention thì tệ
   hơn tuyến tính.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Cạnh ô vá của HiDream-O1. Không đặt số khác — nó là hằng của model.
PATCH = 32

#: ⭐ TRẦN LÀ SỐ ĐÃ ĐO THẬT, không phải số tính ra.
#:
#:   2048×2048  → 4.096 token   (G3, VRAM đỉnh 16,8 GB — lượt đơn lẻ)
#:   2560×1440  → 3.600 token   (G4, `--reserve-vram 3`: 17,6 GB · 57,8 s)
#:   edit 1 ảnh @2 MP  → 5.553 token   (G5: **19,8 GB** · 190,6 s)
#:   edit 1 ảnh @4 MP  → **7.506 token** (G5: **19,8 GB** · 190,1 s)
#:   subject 2 ảnh @2 MP → **7.506 token** (G5: **20,0 GB** · 210,8 s)
#:
#: 7.506 là cấu hình lớn nhất **từng chạy xong và có số đo** (G5, 22/08). Trần đã
#: nâng từ 4.096 lên bằng SỐ ĐO, không bằng suy đoán — xem D-032.
#:
#: ⭐ Hai điều số đo G5 dạy, đều trái trực giác:
#:   · Token tham chiếu **KHÔNG nhân thời gian theo attention**: 5.553 và 7.506
#:     token đều mất ~190 s. Chi phí ảnh tham chiếu là **một lần**, không theo bậc.
#:   · Nhưng chế độ tham chiếu vẫn **đắt gấp 3,3 lần** ảnh thường cùng số bước
#:     (190 s so với 57,8 s). Đó là con số phải nói với khách, không phải giấu.
TOKEN_DA_DO_TOI_DA = 7506

#: Biên VRAM phải chừa cho hệ điều hành + dự án video. `--reserve-vram` của ComfyUI
#: nhận GB; con số ở đây phải khớp với cờ dùng khi khởi động ComfyUI trên máy B.
VRAM_CHUA_LAI_GB = 3.0


class NgoaiVungDaDo(Exception):
    """Cấu hình vượt vùng đã đo. Đây là **từ chối có chủ ý**, không phải lỗi."""


@dataclass(frozen=True)
class Uoc:
    token_khung: int
    token_tham_chieu: int
    so_anh_tham_chieu: int

    @property
    def tong(self) -> int:
        return self.token_khung + self.token_tham_chieu

    def as_dict(self) -> dict:
        return {"token_khung": self.token_khung,
                "token_tham_chieu": self.token_tham_chieu,
                "so_anh_tham_chieu": self.so_anh_tham_chieu,
                "tong_token": self.tong,
                "tran_da_do": TOKEN_DA_DO_TOI_DA}


def token_khung(width: int, height: int) -> int:
    """Token của khung sinh ra. Làm tròn LÊN: một hàng ô vá lẻ vẫn tốn cả hàng."""
    if width <= 0 or height <= 0:
        raise ValueError("width/height phai duong")
    return -(-width // PATCH) * (-(-height // PATCH))


def token_tham_chieu(megapixel: float, so_anh: int) -> int:
    """Token do ảnh tham chiếu nối thêm.

    `ImageScaleToTotalPixels` trong bản mẫu đưa mỗi ảnh về `megapixel` MP với
    `resolution_steps=32`, nên mỗi ảnh tốn ≈ `MP·10⁶ / 32²` token.
    """
    if so_anh < 0 or megapixel < 0:
        raise ValueError("so_anh/megapixel khong duoc am")
    return int(so_anh * round(megapixel * 1_000_000 / (PATCH * PATCH)))


def uoc_tinh(width: int, height: int, *, ref_mp: float = 0.0, so_ref: int = 0) -> Uoc:
    return Uoc(token_khung(width, height), token_tham_chieu(ref_mp, so_ref), so_ref)


def kiem(width: int, height: int, *, ref_mp: float = 0.0, so_ref: int = 0,
         tran: int = TOKEN_DA_DO_TOI_DA) -> Uoc:
    """Ném `NgoaiVungDaDo` nếu cấu hình vượt vùng đã đo. Trả ước tính nếu qua.

    ⛔ Thông điệp lỗi phải nói ra **con số** và **cách đi tiếp**. Một lời từ chối
    không kèm lối ra sẽ bị người sau vòng qua bằng cách sửa hằng số.
    """
    u = uoc_tinh(width, height, ref_mp=ref_mp, so_ref=so_ref)
    if u.tong > tran:
        raise NgoaiVungDaDo(
            f"cau hinh nay can {u.tong} token ({u.token_khung} khung"
            f" + {u.token_tham_chieu} tu {so_ref} anh tham chieu @ {ref_mp} MP),"
            f" vuot tran DA DO {tran}."
            " Do that o cau hinh nay truoc (tang dan, co nguoi canh), ghi so vao"
            " DECISIONS.md, roi moi nang TOKEN_DA_DO_TOI_DA. Xem D-024.")
    return u


# ── đọc thẳng từ workflow đã dựng ────────────────────────────────────────────
#
# ⛔ VÌ SAO KHÔNG TIN THAM SỐ CỦA BÊN GỌI: bản đầu của chốt này đếm `req.refs` —
#    và `chay_baseline.py` (đường ĐO ĐẠC, đúng cái đường đã làm sập máy B) truyền
#    ảnh tham chiếu qua **giá trị thẻ** `ref1`/`ref2`, không qua `req.refs`. Chốt
#    sẽ đếm 0 ảnh và cho cấu hình nguy hiểm đi lọt. Một test bắt được điều này
#    trước khi nó chạy thật.
#
#    Workflow đã dựng là **sự thật cuối cùng** — nó chính là thứ gửi cho ComfyUI.
#    Đếm ở đó thì không đường nào vòng qua được.

NODE_KHUNG = "EmptyHiDreamO1LatentImage"
NODE_ANH_VAO = "LoadImage"
NODE_CO_LAI = "ImageScaleToTotalPixels"


def doc_tu_workflow(wf: dict) -> tuple[int, int, float, int]:
    """Trả `(width, height, ref_mp, so_ref)` đọc từ workflow. Thiếu thì trả 0."""
    w = h = 0
    mp = 0.0
    so_ref = 0
    for nut in wf.values():
        if not isinstance(nut, dict):
            continue
        loai = nut.get("class_type")
        vao = nut.get("inputs") or {}
        if loai == NODE_KHUNG:
            w = int(vao.get("width") or 0)
            h = int(vao.get("height") or 0)
        elif loai == NODE_ANH_VAO:
            so_ref += 1
        elif loai == NODE_CO_LAI:
            try:
                mp = max(mp, float(vao.get("megapixels") or 0.0))
            except (TypeError, ValueError):
                pass
    return w, h, mp, so_ref


def kiem_workflow(wf: dict, *, tran: int = TOKEN_DA_DO_TOI_DA) -> Uoc:
    """Chốt ngân sách đọc từ chính workflow sắp gửi đi. Ném `NgoaiVungDaDo`."""
    w, h, mp, so_ref = doc_tu_workflow(wf)
    if w <= 0 or h <= 0:
        # Không tìm thấy nút khung ⇒ không biết cấu hình ⇒ KHÔNG đoán, KHÔNG chặn.
        # Chặn ở đây sẽ khoá mọi workflow tương lai không dùng nút này.
        return Uoc(0, 0, so_ref)
    return kiem(w, h, ref_mp=mp, so_ref=so_ref, tran=tran)
