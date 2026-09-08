r"""
lui_giong.py — chọn một giọng THAY THẾ khi giọng được yêu cầu không dùng được.

## 🔴 Luật số một: KHÔNG BAO GIỜ ÂM THẦM ĐỔI NGƯỜI NÓI

Đây không phải một nguyên tắc suy ra từ lý thuyết. Hệ `D:\Viral` đã chạy đường
lùi **không** giữ giới tính, và ngày 26/08/2026 khách báo nguyên văn: *"giọng
nam bị biến thành giọng nữ"*. Chú thích trong `giong_piper.py` của họ ghi lại
đúng cơ chế:

    "TRUOC DAY backend KHONG CO bang nay: gioi chi nam trong NHAN hien thi ...
     He qua: moi duong LUI GIONG o backend khong co cach nao biet khach dang
     chon nam hay nu ⇒ lui ve PIPER_VOICE_MAC_DINH = ngochuyen = giong NU,
     ke ca khi khach chon giong NAM."

⇒ Hai hệ quả cho tệp này, và cả hai là **ràng buộc cứng**:

    ① KHONG NOI GIOI, KHONG NOI LAN.  Het ung vien thi TRA VE None,
       khong ha tieu chuan.  Mot loi "khong doc duoc" thanh that tot hon
       mot ban doc bang giong nguoi khac.
    ② MOI luot lui phai SINH RA MOT CANH BAO cho khach doc.  Lui im lang
       chinh la thu ta dang di sua.

## Nới cái gì, theo thứ tự nào

    1. cung lan + cung gioi + cung phong cach + cung vung     <- khop nhat
    2. noi VUNG        (giu lan + gioi + phong cach)
    3. noi PHONG CACH  (giu lan + gioi)
    4. DUNG

⭐ Vùng nới **trước** phong cách, và thứ tự ấy có lý do: giọng miền Bắc đọc thay
   giọng miền Nam thì người nghe nhận ra ngay nhưng vẫn hiểu; một giọng tin tức
   đọc thay một giọng kể chuyện thì đổi hẳn **nhịp** của cả bài. Cái người nghe
   chịu được dễ hơn thì nới trước.

## ⚠️ Giới hạn ĐÃ BIẾT của bản này — ghi ra để không ai tưởng nó rộng hơn

Ứng viên lùi hiện **chỉ là 20 giọng mẫu của engine**, và cả 20 đều thuộc làn
`vi` (xem `features.giai_giong`). Nghĩa là:

    lan vi + gioi ro   ->  lui duoc
    lan en             ->  KHONG (chua co giong mau lan en)
    gioi = "" khong ro ->  KHONG (khong duoc doan — xem `tables.VoiceProfile.gioi`)

Đây là một giới hạn của **kho giọng**, không phải của thuật toán: `chon()` nhận
một danh sách ứng viên bất kỳ. Ngày kho chung có giọng làn `en` với giới đã
khai, mở rộng bằng cách đưa chúng vào `cac`, không phải bằng cách sửa bậc thang.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.i18n import N_

#: Cảnh báo hiển thị cho khách. Điền nhãn bằng `dien_canh_bao` — cùng lý do
#: `lan_ngon_ngu` tách khuôn khỏi phép điền: `N_()` phải thấy một chuỗi HẰNG
#: thì bộ trích mới lấy được nó vào `.po`, nên đừng nối bằng f-string.
CANH_BAO = N_('Giọng bạn chọn hiện không dùng được, nên bài này được đọc bằng '
              '{giong_thay} ({mo_ta}). Hãy ghi danh lại giọng của bạn để dùng '
              'tiếp.')


@dataclass(frozen=True)
class UngVien:
    """Một giọng có thể đứng thay. `ma` là thứ đi thẳng vào `preset=`."""

    ma: str
    gioi: str
    ngon_ngu: str
    vung: str = ""
    phong_cach: str = ""


def _hop(u: UngVien, *, gioi: str, ngon_ngu: str) -> bool:
    """Hai điều kiện KHÔNG BAO GIỜ được nới. Tách ra để nhìn thấy được."""
    return u.gioi == gioi and u.ngon_ngu == ngon_ngu


def chon(*, gioi: str, ngon_ngu: str, vung: str = "", phong_cach: str = "",
         cac) -> UngVien | None:
    """Giọng thay thế, hoặc `None` khi không có ứng viên nào **đủ tiêu chuẩn**.

    ⛔ `None` là một câu trả lời ĐẦY ĐỦ, không phải một thất bại — cùng quy ước
       với `lan_ngon_ngu.doan_ngon_ngu`. Nơi gọi phải báo lỗi thành thật chứ
       không được hạ tiêu chuẩn để có kết quả.

    ⚠️ Giới hoặc làn không rõ (`""`) ⇒ trả `None` NGAY. Không có nghĩa nào cho
       "cùng giới với một giới không biết", và đoán hộ là đúng cái lỗi mà cả
       tệp này đi sửa.
    """
    if gioi not in ("nam", "nu") or ngon_ngu not in ("vi", "en"):
        return None

    # ⭐ Sắp theo `ma` để phép chọn TẤT ĐỊNH. Cùng đầu vào phải cho cùng giọng
    #    thay — nếu không thì hai lượt đọc lại của cùng một bài ra hai người
    #    nói khác nhau, và không ai tái hiện được lỗi nào ở đây.
    hop = sorted((u for u in cac if _hop(u, gioi=gioi, ngon_ngu=ngon_ngu)),
                 key=lambda u: u.ma)
    if not hop:
        return None

    for loc in (
        lambda u: u.vung == vung and u.phong_cach == phong_cach,   # ① khớp nhất
        lambda u: u.phong_cach == phong_cach,                      # ② nới vùng
        lambda _u: True,                                           # ③ nới phong cách
    ):
        for u in hop:
            if loc(u):
                return u
    return None


def tu_giong_mau() -> tuple:
    """Ứng viên dựng từ 20 giọng mẫu của engine.

    ⛔ Cả 20 đều thuộc làn `vi` — xem chú thích *"Preset là giọng người nói
       TIẾNG VIỆT ba miền"* ở `features.giai_giong`. Gán cứng `"vi"` ở đây là
       nói ra sự thật ấy tại chỗ nó được dùng, chứ không phải một mặc định lười.
    """
    from . import giong_mau
    return tuple(UngVien(ma=g.ma, gioi=g.gioi, ngon_ngu="vi", vung=g.vung,
                         phong_cach=g.phong_cach)
                 for g in giong_mau.DANH_SACH)


def dien_canh_bao(mau: str, u: UngVien) -> str:
    """Điền tên giọng thay + mô tả vào khuôn cảnh báo."""
    from . import giong_mau
    from platform_core.i18n import _ as _t
    mo_ta = " · ".join(str(_t(n)) for n in (
        giong_mau.NHAN_GIOI.get(u.gioi, u.gioi),
        giong_mau.NHAN_VUNG.get(u.vung, u.vung),
    ) if n)
    return str(mau).replace("{giong_thay}", u.ma).replace("{mo_ta}", mo_ta)
