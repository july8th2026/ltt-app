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

import json
import pathlib
from dataclasses import dataclass

from platform_core.i18n import N_

NHAN_GIOI = {"nam": N_('Nam'), "nu": N_('Nữ')}
NHAN_VUNG = {"bac": N_('Miền Bắc'), "trung": N_('Miền Trung'), "nam": N_('Miền Nam')}
NHAN_PHONG_CACH = {
    "tin_tuc": N_('Tin tức'),
    "tu_nhien": N_('Tự nhiên'),
    "doc_truyen": N_('Kể chuyện'),
}

#: Thứ tự ƯU TIÊN của phong cách khi xếp giọng. Số nhỏ đứng trước.
#:
#: 🔴 XẾP BẰNG DỮ LIỆU, KHÔNG BẰNG NHÃN. `NHAN_PHONG_CACH` ở trên đã qua `_()`,
#:    nên so sánh chuỗi nhãn sẽ **trượt theo ngôn ngữ giao diện** — hỏng lặng
#:    lẽ, và chỉ hỏng với khách xem bản dịch.
#:
#: ⭐ Và thứ tự này là một QUYẾT ĐỊNH SẢN PHẨM, không phải một chi tiết: bên
#:    tiêu thụ lấy phần tử **đầu** làm mặc định, nên để `tu_nhien` đứng đầu
#:    nghĩa là mọi khách chưa chọn gì đều được đọc bằng giọng tự nhiên.
#:
#: ⛔ Hằng số này từng có **hai** bản — một ở `tham_chieu.py`, một ở nơi khác.
#:    Hai bảng thứ tự cho cùng một kho giọng là hai màn hình mời cùng một khách
#:    hai giọng mặc định khác nhau. Đây là bản DUY NHẤT.
UU_TIEN_PHONG_CACH = {"tu_nhien": 0, "doc_truyen": 1, "tin_tuc": 2}


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


#: Ảnh chụp danh sách preset của engine, nằm trong git.
#: Sinh bằng `tools/sinh_giong_mau_engine.py`; **đừng sửa tay**.
ANH_CHUP = pathlib.Path(__file__).with_name("giong_mau_engine.json")

_DOI_GIOI = {"male": "nam", "female": "nu"}


def _nap() -> tuple:
    """Dựng `DANH_SACH` từ ảnh chụp, một lần lúc nạp module.

    🔴 VÌ SAO ĐỌC TỆP CHỨ KHÔNG GÕ TAY HAI MƯƠI DÒNG.

       Bản đầu khai thẳng hai mươi `GiongMau("Minh Đức", "nam", …)` trong mã.
       `tools/check_i18n.py` đỏ ngay: **17 chuỗi chưa bọc `_()`**.

       Và nó đúng theo luật của nó — nhưng bọc `_()` ở đây sẽ **sai một cách
       nguy hiểm**: tên preset là thứ đi thẳng vào `infer(voice=...)`. Một cái
       tên "đã dịch" là một cái tên engine không nhận ra, và lỗi chỉ hiện ở
       worker sau khi khách đã bị giữ credit.

    ⭐ Lối ra không phải là cãi với bánh cóc, mà là **bỏ bản chép**. Tên giọng
       vốn là dữ liệu của engine, không phải hằng số của ta. Đọc từ ảnh chụp thì:
         · không còn chuỗi tiếng Việt nào trong tệp `.py` này;
         · không còn hai chỗ phải khớp nhau bằng tay;
         · và ngày nâng engine, `sinh_giong_mau_engine.py` là chỗ **duy nhất**
           phải chạy.

    ⚠️ Đọc tệp lúc import: 2,5 KB, một lần cho cả tiến trình. Không chạm mạng,
       không nạp model — đó vẫn là toàn bộ lý do tệp này không hỏi `/v1/voices`.
    """
    d = json.loads(ANH_CHUP.read_text(encoding="utf-8"))
    ra = []
    for ten, v in d.get("presets", {}).items():
        ra.append(GiongMau(
            ma=ten,
            gioi=_DOI_GIOI.get(str(v.get("gender") or ""), ""),
            vung=str(v.get("vung") or ""),
            phong_cach=str(v.get("style") or ""),
        ))
    # Sắp cho người đọc: nam trước nữ, rồi Bắc → Trung → Nam, rồi theo tên.
    # Thứ tự trong JSON là thứ tự của engine và không có nghĩa gì với ai.
    thu_tu_vung = {"bac": 0, "trung": 1, "nam": 2}
    ra.sort(key=lambda g: (g.gioi != "nam", thu_tu_vung.get(g.vung, 9), g.ma))
    return tuple(ra)


DANH_SACH: tuple[GiongMau, ...] = _nap()

#: Giọng engine dùng khi khách không chọn gì. Lấy từ ảnh chụp, không gõ tay —
#: gõ tay thì ngày engine đổi mặc định, ta vẫn nói cái cũ.
MAC_DINH: str = str(
    json.loads(ANH_CHUP.read_text(encoding="utf-8")).get("default_voice") or "")

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
