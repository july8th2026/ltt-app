"""Máy quét bí mật thu hẹp theo HÌNH DẠNG, ⛔ không bằng cách miễn trừ thư mục.

🔴 **Vì sao tệp này tồn tại.** `scan_source_secrets` chặn bản dựng vì `bare_32_char_hex`
   bắt **bằng chứng đo được**: mã băm md5/sha, mã định danh công khai của clip giọng,
   và một bản băm đã bị cắt để hiển thị. Không cái nào là bí mật.

⛔ **Cách sửa SAI, và nó đã được dùng hai lần rồi:** thêm thư mục vào danh sách miễn
   trừ. Mỗi lần gặp báo động giả lại thêm một thư mục, và **mỗi thư mục thêm vào là một
   vùng không còn được quét**. Nếu một khoá thật lọt vào `.superpowers/` hay `docs/` thì
   không cửa nào kêu. Danh sách đó nay đã có `.claude`, `.codex`, `.superpowers`,
   `cutclipshort`…

⭐ **Cách ở đây:** mọi tệp **vẫn được quét**; chỉ **ba hình dạng** cụ thể được thả, và
   cả ba đều đòi **ngữ cảnh**, không chỉ đòi hình chuỗi hex:

     `vc_<32 hex>`                      mã định danh CÔNG KHAI của clip giọng
     `"…md5|sha|checksum…": "<32 hex>"` giá trị của một khoá tên là bằng chứng
     `<hex>…<hex>`                      một bản băm ĐÃ BỊ CẮT để hiển thị

   cộng một luật cho văn xuôi/bảng: có chữ báo *"đây là băm"* **trước** chuỗi hex **và
   không** chữ nào báo *"đây là thông tin đăng nhập"* trên cùng dòng.

⭐ **Vì sao hình dạng „bị cắt" an toàn hơn cả:** một bí mật viết có `...` ở giữa thì
   **không dùng được nữa** — nó đã mất một phần. Nên cả khi thả nhầm, thứ thả ra không
   phải một thông tin dùng được.

⛔ Và nửa quan trọng nhất của tệp này là **nửa ĐỐI CHỨNG NGƯỢC**: bí mật thật vẫn phải
   bị bắt. Một phép kiểm chỉ chứng minh "báo động giả đã hết" thì cũng xanh khi ai đó
   tắt hẳn máy quét.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]

#: 32 ky tu hex, GHEP LUC CHAY.
#:
#: 🔴 Viet thang mot chuoi 32 hex vao tep nay thi **chinh may quet bat tep
#:    kiem cua no** — da xay ra 24/09. Do la may quet lam DUNG viec; loi
#:    nam o du lieu thu. Ghep luc chay thi khong dong nao chua hinh dang do.
#: ⛔ Dung them tep nay vao danh sach mien tru — do chinh la cach sua ma
#:    ca tep nay ton tai de chan.
HEX32 = "0123456789abcdef" * 2


@pytest.fixture()
def sc():
    spec = importlib.util.spec_from_file_location(
        "_scan_bm", GOC / "tools" / "scan_source_secrets.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["_scan_bm"] = m
    spec.loader.exec_module(m)
    return m


def _bat(sc, dong: str) -> bool:
    return bool(sc._scan_line(pathlib.Path("x"), 1, dong))


# ══════════════════════════════════════════════════════════════════════════
# 1. BÍ MẬT THẬT VẪN PHẢI BỊ BẮT — nửa đối chứng ngược
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("dong", [
    'api_key = "' + 'deadbeef' * 4 + '"',
    'token: "' + HEX32 + '"',
    'LTT_SECRET=' + HEX32,
    '  "gia_tri": "' + HEX32 + '"',
])
def test_bi_mat_that_VAN_bi_bat(sc, dong):
    """⛔ Nếu bài này đỏ thì việc thu hẹp đã đi quá và máy quét hết kiểm gì."""
    assert _bat(sc, dong), f"LOT LUOI: {dong}"


def test_co_CA_HAI_chu_thi_van_bat(sc):
    """Dòng vừa có chữ „băm" vừa có chữ „khoá" ⇒ **bắt**.

    ⭐ Lúc đó chữ „sha" không còn nói lên được điều gì: nó có thể là tên một biến
       chứa khoá thật. Nghi ngờ thắng.
    """
    assert _bat(sc, "api_key sha  " + "deadbeef" * 4)


def test_hex_tran_KHONG_ngu_canh_thi_bat(sc):
    """Ba hình dạng được thả đều đòi NGỮ CẢNH. Một chuỗi hex trần vẫn bị bắt."""
    assert _bat(sc, "    " + HEX32)


# ══════════════════════════════════════════════════════════════════════════
# 2. BA HÌNH DẠNG ĐƯỢC THẢ
# ══════════════════════════════════════════════════════════════════════════

def test_ma_clip_giong_CONG_KHAI_duoc_tha(sc):
    """`vc_<32 hex>` đi tới trình duyệt của khách ⇒ nó không thể là bí mật."""
    assert not _bat(sc, '    "vc_526cb3ffb0d14558aadf199db27c0507",  # Owen')


def test_gia_tri_cua_khoa_bang_chung_duoc_tha(sc):
    assert not _bat(sc, '  "md5_render": "ee6ccffc88decb050ae6bd1afc7e2e61"')


def test_bam_DA_BI_CAT_duoc_tha(sc):
    """⭐ An toàn nhất trong ba: một bí mật có `...` ở giữa thì đã hỏng, không dùng được."""
    assert not _bat(
        sc, '  "khoa_chung": "ed3599b93552...af7860f5e19e7dffa2102a1c023a21f4"')


def test_bam_trong_BANG_van_xuoi_duoc_tha(sc):
    """Bảng markdown không có cú pháp `"khoá": "giá trị"` — cần luật cho văn xuôi."""
    assert not _bat(sc, "bam remux toi gian   acd497e1825e6fd978901482afa0e899   3205 goi")


# ══════════════════════════════════════════════════════════════════════════
# 3. CHỐT CƠ HỌC: ⛔ đừng chữa báo động giả bằng cách thêm thư mục miễn trừ
# ══════════════════════════════════════════════════════════════════════════

def test_KHONG_them_thu_muc_mien_tru_cho_bang_chung_ASV(sc):
    """⛔ `docs/` và thư mục bằng chứng ASV phải VẪN được quét.

    🔴 Đây là bất biến quan trọng nhất của tệp. Cách sửa dễ nhất cho một báo động
       giả là thêm thư mục vào `EXCLUDED_DIR_NAMES` — và nó đã được dùng hai lần
       (`.codex`, rồi `.superpowers` ngày 23/09). Mỗi lần như vậy đổi một báo động
       giả lấy một **vùng mù**.
    """
    cam = {"docs", "auto_scan_video_final", "bang_chung", "apps", "tools", "tests"}
    trung = cam & set(sc.EXCLUDED_DIR_NAMES)
    assert not trung, f"da mien tru ca thu muc — tao vung mu: {sorted(trung)}"


def test_moi_hinh_dang_tha_deu_doi_NGU_CANH(sc):
    """Chốt rằng không mẫu nào chỉ đòi „32 ký tự hex" rồi thả.

    ⛔ Một mẫu như vậy sẽ thả **mọi** chuỗi hex, tức tắt hẳn luật.
    """
    for mau in sc.KHONG_PHAI_BI_MAT:
        assert not mau.fullmatch(HEX32), (
            f"mau nay tha MOI chuoi hex: {mau.pattern}")
