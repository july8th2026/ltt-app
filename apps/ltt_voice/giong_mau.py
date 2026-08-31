"""
giong_mau.py — hai mươi GIỌNG MẪU mà engine dựng sẵn, khai thành hợp đồng.

🔴 VÌ SAO KHAI TĨNH THAY VÌ HỎI CỔNG.

   Cổng có `/v1/voices`, nhưng `voice_sidecar/server.py` gọi `c.nap()` trong đó —
   tức **nạp model**. Đo 30/08 (`docs/LTT_VOICE/do_v1.json`): **19,4 giây khi
   nguội**. Một trang liệt kê giọng gọi thẳng vào đó sẽ treo 19 giây ở lượt đầu
   mỗi sáng, và với người dùng nó trông y hệt một trang chết.

   Danh sách này lại gần như không bao giờ đổi — nó đi kèm bản model. Nên nó
   thuộc về **mã**, và ngày nó đổi thì phép kiểm dưới đây sẽ nói.

⭐ Đây là khuôn đã dùng cho `tham_so_cong_khai.py`: một bản sao ở phía nền tảng,
   một phép kiểm đối chiếu với phía engine. *Hai bản sao không có phép kiểm là
   hai bản sao sẽ lệch; hai bản sao **có** phép kiểm là một hợp đồng.*
   Phép kiểm: `tests/test_345_ltt_voice_giong_mau.py`.

⛔ `ma` PHẢI ĐÚNG TỪNG KÝ TỰ tên preset của engine, dấu và khoảng trắng đầy đủ.
   Nó là thứ đi thẳng vào `infer(voice=...)`, và sai một dấu thì SDK ném
   `ValueError: Voice 'X' not found` — một lỗi chỉ lộ ra ở worker, sau khi khách
   đã bấm và đã bị giữ credit.

⭐ BA MẶT LỌC DƯỚI ĐÂY LÀ THẬT, và chúng thay cho thứ ảnh tham chiếu vẽ.

   Ảnh `02_VOICES.png` lọc theo `VI / EN / Bilingual` và `All Families`. Nền tảng
   **không có** hai khái niệm đó: engine tự xử tiếng Việt lẫn tiếng Anh nên không
   có giọng nào "chỉ EN", và "Voice Family" không tồn tại ở đâu cả.

   Nhưng dữ liệu thật lại cho ba mặt **tốt hơn** — giới tính, vùng miền, phong
   cách — và đó đúng là ba câu người chọn giọng thực sự hỏi. Nên ở đây ảnh không
   bị "cắt bớt", nó được thay bằng thứ đúng hơn.

⚠️ `phong_cach` là **nhãn mô tả giọng, KHÔNG phải nút vặn**. `v3turbo.py` ghi rõ:
   *"Style is deprecated on v3 Turbo: it is implied by the reference … Kept only
   as voice metadata."* Nghĩa là không ai chọn được "đọc giọng tin tức" cho một
   giọng vốn là giọng kể chuyện — phong cách đã nằm sẵn trong chính giọng đó.
   Hiện nó như một tính chất, đừng bao giờ hiện nó như một ô chọn.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.i18n import N_

#: Tên preset mà engine dùng khi khách không chọn gì. Khớp `default_voice` trong
#: `vieneu/assets/voices_v3_turbo.json`.
MAC_DINH = "Adam"

NHAN_GIOI = {"nam": N_('Nam'), "nu": N_('Nữ')}
NHAN_VUNG = {"bac": N_('Miền Bắc'), "trung": N_('Miền Trung'), "nam": N_('Miền Nam')}
NHAN_PHONG_CACH = {
    "tin_tuc": N_('Tin tức'),
    "tu_nhien": N_('Tự nhiên'),
    "doc_truyen": N_('Kể chuyện'),
}


@dataclass(frozen=True)
class GiongMau:
    """Một giọng dựng sẵn. **Không** mang gì của engine ngoài cái tên."""

    ma: str
    gioi: str
    vung: str
    phong_cach: str

    @property
    def public_id(self) -> str:
        """Danh tính công khai của một giọng mẫu **là chính tên nó**.

        Khác giọng nhân bản (`vc_<32 hex>`), và khác một cách có chủ ý: hợp đồng
        API đã khai `preset: "Adam"` chứ không phải một mã sinh ra. Một cái tên
        đọc được là thứ khách dán vào mã nguồn mà không phải tra lại.
        """
        return self.ma

    @property
    def la_mau(self) -> bool:
        return True

    @property
    def trang_thai(self) -> str:
        """Giọng mẫu luôn dùng được — không có bước ghi danh nào để chờ."""
        return "active"

    @property
    def ten_hien_thi(self) -> str:
        return self.ma


#: Hai mươi giọng, đọc từ `vieneu/assets/voices_v3_turbo.json` ngày 31/08/2026.
#: Thứ tự: nam trước nữ, trong mỗi nhóm theo vùng Bắc → Trung → Nam. Không theo
#: thứ tự của tệp JSON — thứ tự đó không có nghĩa gì với người đọc.
DANH_SACH: tuple[GiongMau, ...] = (
    # ── Nam ──
    GiongMau("Minh Đức", "nam", "bac", "tin_tuc"),
    GiongMau("Phạm Tuyên", "nam", "bac", "tu_nhien"),
    GiongMau("Thanh Bình", "nam", "bac", "doc_truyen"),
    GiongMau("Quang Sơn", "nam", "trung", "tu_nhien"),
    GiongMau("Minh Triết", "nam", "nam", "tin_tuc"),
    GiongMau("Xuân Vĩnh", "nam", "nam", "tu_nhien"),
    GiongMau("Adam", "nam", "nam", "tu_nhien"),
    GiongMau("Thái Sơn", "nam", "nam", "doc_truyen"),
    GiongMau("Đức Trí", "nam", "nam", "doc_truyen"),
    # ── Nữ ──
    GiongMau("Mai Anh", "nu", "bac", "tin_tuc"),
    GiongMau("Trúc Ly", "nu", "bac", "tu_nhien"),
    GiongMau("Đoan Trang", "nu", "bac", "tu_nhien"),
    GiongMau("Ngọc Huyền", "nu", "bac", "tu_nhien"),
    GiongMau("Ngọc Linh", "nu", "bac", "doc_truyen"),
    GiongMau("Quỳnh Anh", "nu", "bac", "doc_truyen"),
    GiongMau("Ngọc Trân", "nu", "trung", "tu_nhien"),
    GiongMau("Thùy Dung", "nu", "nam", "tin_tuc"),
    GiongMau("Thục Đoan", "nu", "nam", "doc_truyen"),
    GiongMau("Mỹ Duyên", "nu", "nam", "doc_truyen"),
    GiongMau("Kim Thanh", "nu", "nam", "doc_truyen"),
)

#: Tra nhanh theo mã. Dựng một lần lúc nạp module.
THEO_MA = {g.ma: g for g in DANH_SACH}


def tim(ma: str) -> GiongMau | None:
    return THEO_MA.get((ma or "").strip())


def hop_le(ma: str) -> bool:
    """Mã này có phải một giọng mẫu có thật không.

    ⭐ Dùng ở cửa nộp để chặn sớm. Không có phép kiểm này thì một `preset` gõ sai
       đi hết đường xuống worker rồi mới hỏng — và lúc đó khách đã chờ, đã bị giữ
       credit, và thông điệp lỗi đến từ SDK chứ không từ ta.
    """
    return (ma or "").strip() in THEO_MA


def loc(*, gioi: str = "", vung: str = "", phong_cach: str = "",
        tim_kiem: str = "") -> list[GiongMau]:
    """Lọc theo ba mặt + tìm theo tên. Chuỗi rỗng nghĩa là **không lọc mặt đó**."""
    kq = list(DANH_SACH)
    if gioi:
        kq = [g for g in kq if g.gioi == gioi]
    if vung:
        kq = [g for g in kq if g.vung == vung]
    if phong_cach:
        kq = [g for g in kq if g.phong_cach == phong_cach]
    if tim_kiem:
        q = tim_kiem.strip().lower()
        kq = [g for g in kq if q in g.ma.lower()]
    return kq
