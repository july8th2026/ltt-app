"""V4c — LOGO DI CHUYỂN: chốt kế hoạch "C — không lấy", và đo XEM NÓ CÓ THẬT AN TOÀN.

## Vì sao bài này tồn tại dù V4c ⛔ KHÔNG được dựng

`docs/superpowers/plans/2026-09-25-asv-hai-giai-doan.md` chốt V4c ở phương án
**C** (không lấy) vì hai lý do độc lập: chi phí 5–10× so với V4a/V4b, và nó
⛔ không phải một bộ TỰ DÒ — thuật toán tham chiếu của Viral đòi khách khoanh ô
trước rồi mới bám theo, và chính Viral tự thử hướng đó rồi tự loại.

⭐ Nhưng "không dựng" phải được ĐÓNG bằng một phép đo, ⛔ không phải một câu nói.
Câu hỏi thật: `do_logo_tinh` (V4a) ⛔ có ÂM THẦM trả một hộp TĨNH sai cho một
logo ĐANG DI CHUYỂN không? Nếu có, đó là một lỗ hổng thật — khách trả tiền cho
một lượt render che NHẦM chỗ, đúng cảnh báo trong kế hoạch. Nếu không, cơ chế
đã tự an toàn và bài này CHỐT lại bằng số, không bằng lập luận suông.

## ⚠️ Và một phép kiểm "rỗng" một mình thì ⛔ không chứng minh được gì

Một bài chỉ khẳng định *"logo động -> `vung` rỗng"* sẽ xanh cả khi ai đó xoá
luôn `do_logo_tinh` (đo vắng mặt — sổ `co-hoan-la-phep-do-hay-chi-la-mot-cau-
noi.md`). ⇒ Bài dưới có ĐỐI CHỨNG: **cùng khuôn ảnh động hệt nhau**, chỉ khác
một chỗ — logo TĨNH — phải trả về MỘT hộp. Thiếu đối chứng thì phép kiểm chính
vô nghĩa.
"""
from __future__ import annotations

import subprocess

import pytest

from apps.auto_scan_video import do_vung as dv

#: Nen SINH DONG dung khuon `test_4301` — moi diem anh doi qua thoi gian, de
#: mot phep do "rong" o day khong the la hau qua cua mot nen TINH.
_NEN = ("color=c=gray:s=640x360:r=10:d=6,format=rgb24,"
        "geq=r='128+110*sin(X/23+T*3)':g='128+110*sin(Y/19+T*2)':"
        "b='128+110*sin((X+Y)/29+T*4)'[bg];")


def _dung(loc: str, ra: str) -> None:
    kq = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "nullsrc",
         "-filter_complex", loc, "-map", "[v]", "-pix_fmt", "yuv420p",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", ra],
        capture_output=True, text=True, timeout=180, errors="replace")
    assert kq.returncode == 0, (kq.stderr or "")[-1500:]


@pytest.fixture(scope="module")
def clip_logo_tinh(tmp_path_factory) -> str:
    """ĐỐI CHỨNG: logo đục, ĐỨNG YÊN ở góc trên-phải suốt clip."""
    ra = str(tmp_path_factory.mktemp("v4c") / "tinh.mp4")
    _dung(_NEN
          + "[bg]drawbox=x=560:y=18:w=56:h=28:color=white@1.0:t=fill,"
            "drawbox=x=566:y=24:w=44:h=16:color=black@1.0:t=fill[v]", ra)
    return ra


@pytest.fixture(scope="module")
def clip_logo_dong(tmp_path_factory) -> str:
    """Logo đục HỆT cỡ ĐỐI CHỨNG, nhưng TRƯỢT ngang liên tục qua cả clip."""
    ra = str(tmp_path_factory.mktemp("v4c") / "dong.mp4")
    _dung(_NEN
          + "[bg]drawbox=x='40+80*t':y=18:w=56:h=28:color=white@1.0:t=fill,"
            "drawbox=x='46+80*t':y=24:w=44:h=16:color=black@1.0:t=fill[v]", ra)
    return ra


def test_DOI_CHUNG_logo_TINH_van_ra_mot_hop(clip_logo_tinh):
    """Nếu đối chứng này đỏ thì toàn bộ khuôn clip sai, và bài rỗng bên dưới
    ⛔ không chứng minh được điều gì — đây PHẢI xanh trước."""
    kq = dv.do_logo_tinh(clip_logo_tinh)
    assert kq.so_khung > 0
    assert len(kq.vung) == 1, f"doi chung phai ra DUNG mot hop, duoc {kq.vung!r}"
    assert kq.vung[0]["goc"] == "tr"


def test_logo_DI_CHUYEN_KHONG_ra_mot_hop_TINH_SAI(clip_logo_dong):
    """🔴 Bài chính. `do_logo_tinh` PHẢI tự loại logo di chuyển — ⛔ không được
    báo một hộp tĩnh cho một vị trí chỉ đúng trong một phần thời gian.

    Đo được (xem `do_vung.py` mục "V4c — LOGO DI CHUYỂN"): cơ chế tự an toàn
    là hệ quả TRỰC TIẾP của `NGUONG_STD` — logo di chuyển làm `std` theo trục
    thời gian ở MỖI ô lưới TĂNG VỌT (mỗi ô chỉ "thấy" logo một phần thời gian),
    vượt hẳn `NGUONG_STD=8.0` mà logo TĨNH giữ dưới. ⛔ Đây KHÔNG phải một
    ngoại lệ code viết riêng cho ca này — không có nhánh nào trong
    `do_logo_tinh` biết "logo" là gì ngoài công thức `std` đó.
    """
    kq = dv.do_logo_tinh(clip_logo_dong)
    assert kq.so_khung > 0, "phai DOC duoc khung — rong vi khong doc duoc la ca KHAC"
    assert kq.vung == (), (
        f"LO HONG THAT: logo di chuyen bi bao thanh {kq.vung!r} — mot hop TINH "
        "cho mot vi tri chi dung mot phan thoi gian. Xem canh bao trong "
        "docs/superpowers/plans/2026-09-25-asv-hai-giai-doan.md muc V4c.")


def test_de_xuat_cung_rong_cho_logo_di_chuyen_KHONG_phai_khong_do_duoc(
        clip_logo_dong):
    """Qua `de_xuat()`: rỗng ở đây phải đi đường `khong_co` (BẤT BIẾN 1 —
    "đã quét thật, không thấy gì"), ⛔ KHÔNG phải `khong_do_duoc` (lỗi kỹ
    thuật). Logo động không phải một lỗi đọc video — bộ dò đọc video BÌNH
    THƯỜNG, nó chỉ đúng đắn không nhận ra một vị trí không đứng yên."""
    ra = dv.de_xuat(clip_logo_dong)
    assert ra["so_khung"][dv.NGUON_LOGO] > 0
    assert not any(h["nguon"] == dv.NGUON_LOGO for h in ra["vung"])
    assert ra["trang_thai"] != dv.TRANG_THAI_KHONG_DO_DUOC
