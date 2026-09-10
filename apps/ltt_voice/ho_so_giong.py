r"""
ho_so_giong.py — TỐC ĐỘ ĐỌC ĐO ĐƯỢC của từng giọng, và phép ước dựng trên nó.

## Vấn đề nó giải

`gia.py` ước thời lượng bằng **một** cặp hằng số cho **cả kho giọng**:

    GIAY_KHOI_DONG_UOC = 1.5
    KY_TU_MOI_GIAY_UOC = 18

Số ấy đo thật (30/08, RTX 5060 Ti) nhưng đo trên **một** bộ giọng. Chính chú
thích của nó nói ra giới hạn: *"Số đo là của MỘT bộ giọng trên MỘT card; một
giọng đọc chậm hơn là hoàn toàn bình thường."*

⇒ Hệ quả đo được ở một hệ khác: `D:\Viral` giữ bảng `TOC_DOC` cho 61 giọng, và
  chênh lệch giữa hai giọng cùng ngôn ngữ lên tới **43 %** (`Nhỏ Ngọt Ngào`
  2,93 s so với `Review Phim new` 4,20 s cho cùng một câu). Một hằng số phẳng
  bắt **mọi** bài trả giá cho giọng chậm nhất, hoặc giữ thiếu ở giọng ấy.

## 🔴 VÌ SAO LÀ MỘT ẢNH CHỤP JSON, KHÔNG PHẢI MỘT BẢNG CSDL

`manifest._gia()` chạy ở **mọi lượt báo giá**, và chú thích của chính nó cấm:
*"nó chạy ở mọi lượt báo giá nên không được chạm mạng hay CSDL."*

Một bảng `voice_runtime_profile` sẽ buộc đường báo giá phải mở một phiên CSDL —
tức phá đúng ràng buộc ấy. Kho này đã có khuôn đúng cho cùng bài toán:
`giong_mau_engine.json` — dữ liệu **đo được**, sinh bằng công cụ, commit vào
kho, đọc **một lần** lúc import.

⭐ Và nó khả thi vì `_gia(params)` **đã có `params`**: tên preset nằm ngay trong
   đó, nên tra hồ sơ không cần biết gì thêm.

## ⛔ ƯỚC PHẢI THỪA, LUÔN LUÔN — và đây là chỗ dễ làm hỏng sổ sách nhất

Con số này dùng để **giữ chỗ credit**. Giữ thiếu thì khách tiêu quá số dư, và
đó là một lỗi **sổ sách**, không phải một lỗi hiển thị (`gia.py` ghi rõ).

Nên hồ sơ không dùng `ky_tu_moi_giay` trung bình mà dùng **cận dưới**:

    ky_tu_moi_giay_uoc = trung_binh - 2*do_lech_chuan

Chậm hơn ⇒ ước nhiều giây hơn ⇒ giữ nhiều credit hơn ⇒ hoàn lại phần dư khi
job xong. Sai về phía **giữ thừa** là sai an toàn; sai về phía giữ thiếu thì
không.

## ⚠️ Thiếu hồ sơ KHÔNG phải lỗi

Giọng nhân bản của khách không bao giờ có trong ảnh chụp — chúng sinh ra sau
lượt đo. `tra()` trả `None` và mọi thứ lùi về đúng hằng số cũ. Đó là hành vi
đúng, không phải một khoảng trống chờ lấp.
"""
from __future__ import annotations

import json
import pathlib

#: Ảnh chụp. Sinh bằng `tools/do_ho_so_giong.py`; **đừng sửa tay**.
ANH_CHUP = pathlib.Path(__file__).with_name("ho_so_giong.json")

#: Số lượt đo tối thiểu để một hồ sơ được TIN.
#:
#: 🔴 BA, KHÔNG PHẢI MỘT. Một lượt đo cho một con số, không cho một **dải** —
#:    và không có dải thì không rút được `do_lech_chuan`, tức không biết phải
#:    ước thừa bao nhiêu. `tham_so_cong_khai.py` đã ghi đúng lời cảnh báo này
#:    cho một phép đo khác: *"một vòng đo, không phải nhiều vòng như
#:    `cong_chat_luong_voice.py` đòi để rút dung sai từ chính số đo"*.
SO_LUOT_TOI_THIEU = 3

#: Bao nhiêu độ lệch chuẩn trừ đi để ra cận dưới an toàn.
#:
#: 2σ phủ ~97,7 % một phía nếu phân bố xấp xỉ chuẩn. Không cần chính xác hơn:
#: đây là một biên an toàn, không phải một khoảng tin cậy công bố.
SO_SIGMA = 2.0


def _nap() -> dict:
    """Đọc ảnh chụp một lần lúc import. Thiếu tệp ⇒ dict rỗng, không ném.

    ⛔ KHÔNG ném khi thiếu tệp: một kho chưa từng chạy phép đo vẫn phải bán
       được hàng. Thiếu hồ sơ chỉ có nghĩa *"chưa đo"*, và đường lùi đã có.
    """
    try:
        d = json.loads(ANH_CHUP.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d.get("giong") or {}


DANH_SACH = _nap()


def phien_ban() -> str:
    """Phiên bản của lượt đo. `""` khi chưa có ảnh chụp."""
    try:
        return str(json.loads(ANH_CHUP.read_text(encoding="utf-8"))
                   .get("phien_ban") or "")
    except (OSError, ValueError):
        return ""


def tra(ten: str):
    """Hồ sơ của một giọng, hoặc `None` khi chưa đo / không đủ tin.

    ⛔ `None` là một câu trả lời ĐẦY ĐỦ — cùng quy ước với
       `lan_ngon_ngu.doan_ngon_ngu` và `lui_giong.chon`. Nơi gọi lùi về hằng số
       cũ chứ không đoán.
    """
    ho_so = DANH_SACH.get(str(ten or "").strip())
    if not isinstance(ho_so, dict):
        return None
    if int(ho_so.get("so_luot") or 0) < SO_LUOT_TOI_THIEU:
        return None
    if not ho_so.get("ky_tu_moi_giay"):
        return None
    return ho_so


def ky_tu_moi_giay_an_toan(ten: str):
    """Cận DƯỚI của tốc độ đọc, hoặc `None`. Dùng để **giữ chỗ**, nên cố ý thấp.

    ⚠️ Trả cận dưới chứ không trả trung bình: xem khối *"ƯỚC PHẢI THỪA"* ở đầu
       tệp. Một giọng đo được 20,8 với σ = 0,9 thì ở đây ra 19,0 — ước thừa
       khoảng 9 %, và phần thừa được hoàn ngay khi job xong.
    """
    ho_so = tra(ten)
    if ho_so is None:
        return None
    tb = float(ho_so["ky_tu_moi_giay"])
    sd = float(ho_so.get("do_lech_chuan") or 0.0)
    can_duoi = tb - SO_SIGMA * sd
    # ⛔ Không bao giờ trả một con số phi lý: một σ lớn bất thường (đo trên máy
    #    đang tải nặng) có thể đẩy cận dưới xuống 0 hoặc âm, và khi đó phép chia
    #    ở `giay_uoc` sẽ nổ hoặc cho một con số khổng lồ.
    return can_duoi if can_duoi >= 1.0 else None


def giay_khoi_dong(ten: str):
    """Phí khởi động ĐO ĐƯỢC của một giọng, hoặc `None`."""
    ho_so = tra(ten)
    if ho_so is None:
        return None
    g = ho_so.get("giay_khoi_dong")
    return float(g) if g is not None else None
