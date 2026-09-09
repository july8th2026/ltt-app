"""HM-6 — ô chọn tác vụ trên giao diện: sinh từ danh mục, không gõ tay.

## Vì sao chỉ có ô chọn tác vụ, chưa có gallery kéo-thả

Kế hoạch HM-6 dự tính một gallery **kéo-thả có thứ tự** cho nhiều ảnh tham
chiếu. Nhưng mọi tác vụ cần nhiều ảnh (`nhieu_anh_tham_chieu`,
`boi_canh_va_nhan_vat`) đang `mo=False` — chúng thiếu bản ghi
`mac_dinh__vace_14B.json`, và bản ghi ấy phải rút từ máy thật (HM-7).

⛔ Dựng một ô chọn nhiều ảnh trong khi mọi tác vụ nhiều ảnh đều đóng là **mở
   một cánh cửa vào một căn phòng khoá** — đúng cái bất biến mà chính app này
   đã trả giá một lần để học:

       chon MP4 -> nen tang GIU CREDIT -> job hong -> hoan credit

   Tiền trả lại, thời gian và niềm tin thì không.

⇒ Gallery đi cùng HM-7/HM-8, khi VACE thật sự chạy được. Ghi ở đây để lần sau
  không ai tưởng nó bị bỏ sót.
"""
from __future__ import annotations

import inspect
import pathlib
import re

from apps.lttvideo import routes, tac_vu


def _template() -> str:
    goc = pathlib.Path(inspect.getsourcefile(routes)).parent / "templates"
    return chr(10).join(f.read_text(encoding="utf-8")
                        for f in sorted(goc.glob("*.html")))


# ══════════════════════════════════════════════════════════════════════════
#  1. Sinh tu danh muc, khong go tay
# ══════════════════════════════════════════════════════════════════════════

def test_template_LAP_qua_danh_muc_chu_khong_go_tung_tac_vu():
    """Gõ tay từng tác vụ trong template nghĩa là thêm một tác vụ phải sửa hai
    chỗ, và chỗ thứ hai là chỗ sẽ bị quên."""
    html = _template()
    assert "{% for t in tac_vu %}" in html
    for tv in tac_vu.TAC_VU.values():
        # Nhan hien thi phai den tu `t.nhan`, khong duoc go nguyen van.
        assert str(tv.nhan) not in html, (
            f"nhan {str(tv.nhan)!r} go tay trong template")


def test_route_dua_dung_TAC_VU_DANG_MO_vao_template():
    ma = inspect.getsource(routes)
    assert "tac_vu.dang_mo()" in ma, (
        "route dua ca TAC_VU vao — tac vu chua mo se hien roi hong luc chay")


def test_moi_tac_vu_hien_ra_deu_CHAY_DUOC():
    """🔑 Cửa trước khớp cửa sau. Một tác vụ hiện trên giao diện mà thiếu bản
    ghi mặc định của model sẽ nhận credit rồi hỏng."""
    goc = pathlib.Path(tac_vu.__file__).parent / "ban_ghi"
    for tv in tac_vu.dang_mo():
        assert (goc / f"mac_dinh__{tv.model}.json").is_file(), tv.ma


# ══════════════════════════════════════════════════════════════════════════
#  2. Server KHONG tin trinh duyet
# ══════════════════════════════════════════════════════════════════════════

def test_ma_tac_vu_LA_bi_tu_choi_o_CUA_TRUOC():
    """⛔ Trình duyệt gửi gì cũng phải đối chiếu lại với `dang_mo()`.

    Một mã lạ — hoặc một tác vụ `mo=False` gõ tay vào request — phải bị chặn
    **trước khi** nền tảng giữ credit, chứ không đi tới job rồi hỏng sau hai
    mươi phút.
    """
    ma = inspect.getsource(routes.tao_video)
    assert "dang_mo()" in ma, "route khong doi chieu ma tac vu voi danh muc mo"


def test_o_chon_tep_van_chi_moi_ANH():
    """Bất biến giữ từ trước: mọi MIME ô chọn tệp mời phải có một tác vụ đang
    mở nhận được nó. Hai tác vụ đang mở đều chỉ nhận ảnh."""
    m = re.search(r'accept="([^"]+)"', _template())
    assert m
    for mime in m.group(1).split(","):
        assert mime.strip().startswith("image/"), mime


# ══════════════════════════════════════════════════════════════════════════
#  3. Gallery keo-tha CHUA lam — va do la mot quyet dinh
# ══════════════════════════════════════════════════════════════════════════

def test_o_chon_tep_cho_chon_NHIEU_khi_va_CHI_KHI_co_tac_vu_nhieu_anh_mo():
    """⛔ Đối chứng cho quyết định hoãn gallery — viết dưới dạng **tương đương**,
    không dưới dạng "chưa có tính năng X".

    🔴 Bản đầu dùng `pytest.skip` khi có tác vụ nhiều ảnh mở ra, và bánh cóc
       `bo qua im lang` bắt đúng: **một test bị bỏ qua là một test không canh
       gì cả**. Một phép kiểm tự tắt khi thế giới đổi thì đúng lúc cần nó nhất
       lại là lúc nó im lặng.

    ⭐ Mệnh đề thật không phải *"không được có `multiple`"* mà là *"hai cửa phải
      KHỚP nhau"*:

          o chon tep cho chon nhieu  ⟺  co tac vu dang mo nhan >1 tep

      Viết thế thì nó đúng ở **cả hai** thế giới, và nó bắt được **cả hai**
      chiều lệch: mời 5 ảnh khi mọi tác vụ nhiều ảnh đều đóng (người dùng mất
      credit), lẫn mở VACE mà quên mở ô chọn tệp (tính năng câm lặng).
    """
    co_tac_vu_nhieu_anh = any(t.so_tep_toi_da > 1 for t in tac_vu.dang_mo())
    html = _template()
    the_file = html.split('type="file"', 1)[1].split(">", 1)[0]
    cho_chon_nhieu = "multiple" in the_file

    assert cho_chon_nhieu == co_tac_vu_nhieu_anh, (
        f"o chon tep cho chon nhieu={cho_chon_nhieu} nhung tac vu nhieu anh "
        f"dang mo={co_tac_vu_nhieu_anh} — hai cua LECH nhau")


def test_tac_vu_dong_KHONG_lot_ra_giao_dien():
    """Danh mục là bản đồ: nó vẽ cả chỗ chưa tới. Nhưng giao diện chỉ được mời
    chỗ đã tới."""
    dong = [t for t in tac_vu.TAC_VU.values() if not t.mo]
    assert dong, "khong con tac vu dong nao — cap nhat phep kiem nay"
    assert all(t not in tac_vu.dang_mo() for t in dong)
