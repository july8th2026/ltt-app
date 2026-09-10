"""Khu VPS lên MVP giao diện — chốt **nền dùng chung** (Đợt 1).

Kế hoạch: `docs/VPS/UI_MVP_V2/00_KE_HOACH_GIAO_DIEN.md`.
Quyết định D-01…D-04: `docs/VPS/UI_MVP_V2/01_QUYET_DINH_D01_D04.md`.

## Vì sao một tệp nữa, khi đã có `test_252` và `test_304`

Ba tệp chốt ba loại tính chất khác nhau, và trộn chúng làm cả ba khó đọc:

* `test_252` — **hợp đồng** của trang (cổng cờ, fail-closed, không lộ máy người khác).
* `test_304` — **trình bày trang bán**: thứ tự kể chuyện, thẻ chọn, bảng giá.
* tệp này — **nền dùng chung của cả năm màn hình**: một ngôn ngữ trạng thái,
  một nguồn nhãn, và những gì phải tồn tại **trước** khi năm trang tách ra.

## ⚠️ Điều tệp này KHÔNG chốt được

Nó đọc mã, nên nó chốt **nguyên nhân** chứ không chốt kết quả — cùng giới hạn mà
`test_304` đã ghi. Ba lỗi nặng nhất của đợt 25/08 (bố cục vỡ, chữ hoa kế thừa,
nút màu đỏ) đều có HTML **đúng** và cây trợ năng **đúng**. Kết quả phải kiểm bằng
trình duyệt thật.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

from apps.vps import nav, nhan

GOC = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = GOC / "server" / "templates"
LTT_CSS = GOC / "server" / "static" / "ltt.css"
BILLING = GOC / "apps" / "vps" / "services" / "billing.py"


# ── 1 · Một ngôn ngữ trạng thái cho cả năm trang ──────────────────────────

def test_moi_ma_trang_thai_deu_co_NHAN_va_BADGE_va_BUOC_TIEP():
    """Thêm một trạng thái vào CSDL mà quên khai ở `nhan.py` ⇒ đỏ.

    🔴 **Vì sao chốt tập hợp, không chốt số lượng.** Một phép kiểm đếm
       `len(BADGE) == 6` vẫn xanh khi ai đó đổi tên một mã và khai một mã khác —
       bộ đếm đúng, nội dung sai.

    ⚠️ **Nguồn là MÃ ĐANG CHẠY, không phải lược đồ.** Cột `trang_thai` là
       `String(16)` trần, không có `CheckConstraint` nào — xem `_ma_trang_thai_
       trong_bang()` để biết vì sao bản đầu của phép kiểm này đọc lược đồ và
       xanh giả.

    ⚠️ Trạng thái thiếu **màu** thì `nhan.badge()` trả xám (fail-closed, không
       nói dối), nhưng trạng thái thiếu **câu "giờ làm gì"** thì khách nhìn thấy
       một nhãn mà không biết phải làm gì tiếp — đó là lý do `BUOC_TIEP` cũng
       phải đủ, kể cả khi câu đó cố ý rỗng.
    """
    ma = _ma_trang_thai_trong_bang()
    assert len(ma) >= 6, f"chi doc duoc {len(ma)} ma tu bang — bo doc hong"

    assert set(nhan.TRANG_THAI) == ma, (
        f"thieu nhan: {sorted(ma - set(nhan.TRANG_THAI))} · "
        f"thua nhan: {sorted(set(nhan.TRANG_THAI) - ma)}")
    assert set(nhan.BADGE) == ma, (
        f"thieu mau: {sorted(ma - set(nhan.BADGE))} · "
        f"thua mau: {sorted(set(nhan.BADGE) - ma)}")
    assert set(nhan.BUOC_TIEP) == ma, (
        f"thieu buoc tiep: {sorted(ma - set(nhan.BUOC_TIEP))} · "
        f"thua: {sorted(set(nhan.BUOC_TIEP) - ma)}")


def test_badge_chi_dung_class_co_that_trong_ltt_css():
    """Một class badge gõ sai thành một badge **không có kiểu nào** — chữ trần
    trên nền trần, và không phép kiểm nào khác thấy.
    """
    css = LTT_CSS.read_text(encoding="utf-8")
    for ma, cls in nhan.BADGE.items():
        assert re.search(rf"\.{re.escape(cls)}\b", css), (
            f"trang thai {ma!r} dung class {cls!r} — khong co trong ltt.css")


def test_ma_la_KHONG_bao_gio_hien_mau_KHOE():
    """Fail-closed về phía thận trọng.

    Một trạng thái ta chưa biết mà hiện màu xanh "đang chạy" là nói một điều ta
    không kiểm được — và nó nói điều đó đúng vào lúc hệ thống đang ở một trạng
    thái không ai lường trước.
    """
    assert nhan.badge("mot_ma_chua_tung_co") == "b-grey"
    assert nhan.badge("") == "b-grey"
    assert nhan.badge(None) == "b-grey"


def test_ma_la_tra_ve_CHINH_NO_chu_khong_tra_chuoi_rong():
    """Một ô trống làm khách tưởng máy không có trạng thái. Một mã lạ hiện ra ít
    nhất cho ta thứ để tra khi họ chụp màn hình gửi tới."""
    assert nhan.trang_thai("ma_la") == "ma_la"
    assert nhan.su_kien("viec_la") == "viec_la"


# ── 2 · Nhật ký: mã máy đọc → câu người đọc ───────────────────────────────

def test_moi_loai_su_kien_duoc_GHI_deu_co_nhan_nguoi_doc():
    """Nhật ký tồn tại để trả lời khách *"vì sao máy tôi bị tắt"* sau ba tháng.

    Nó chỉ làm được việc đó nếu mọi loại sự kiện **thật sự được ghi** đều có một
    câu người đọc. Danh sách loại đọc từ **mã đang chạy** (mọi lời gọi
    `ghi_su_kien`), không gõ tay — gõ tay thì thêm một `ghi_su_kien` mới là quên
    một nhãn mới, và trang sẽ hiện `treo_khong_tat_duoc` cho khách xem.
    """
    loai = _loai_su_kien_duoc_ghi()
    assert len(loai) >= 12, f"chi tim duoc {len(loai)} loai — bo doc hong"
    thieu = sorted(x for x in loai if nhan.su_kien(x) == x)
    assert thieu == [], f"{len(thieu)} loai su kien chua co nhan: {thieu}"


def test_hau_to_that_bai_KHONG_can_khai_rieng_tung_dong():
    """`dieu_khien._lam` sinh động `f"{ten_thao_tac}_that_bai"`.

    Nếu `nhan.py` phải khai riêng từng cặp thì mỗi thao tác cần **hai** dòng, và
    một trong hai sẽ bị quên — lặng lẽ, vì nhánh thất bại là nhánh hiếm chạy.
    """
    assert nhan.su_kien("bat_that_bai") == nhan.su_kien("bat")
    assert nhan.su_kien_that_bai("bat_that_bai") is True
    assert nhan.su_kien_that_bai("bat") is False
    assert nhan.su_kien_xau("bat_that_bai") is True
    assert nhan.su_kien_xau("bat") is False
    assert nhan.su_kien_xau("bi_treo") is True


def test_nhan_su_kien_KHONG_ghep_chuoi_de_dich():
    """Ghép `nhan + " thất bại"` tạo một msgid **không có trong catalog**.

    Nó sẽ luôn ra tiếng Việt trên bản EN, và không phép kiểm `.po` nào bắt được
    vì chuỗi ghép đó không tồn tại ở đâu để mà trích. `su_kien()` trả về msgid
    gốc và để template ghép — cùng bài học với `{{ app.display_name }}`.
    """
    nguon = (GOC / "apps" / "vps" / "nhan.py").read_text(encoding="utf-8")
    than = re.sub(r'(?s)""".*?"""', " ", nguon)
    than = re.sub(r"(?m)^\s*#.*$", " ", than)
    assert "N_(" not in than.split("def su_kien")[1].split("def ")[0], (
        "`su_kien()` dang tu dung `N_()` — nhan phai lay tu bang, khong sinh moi")


# ── 3 · D-04 · Lịch sử băng thông: chụp TRƯỚC khi bị xoá ──────────────────

def test_thu_mot_chu_ky_CHUP_bang_thong_TRUOC_khi_dat_lai():
    """🔴 Mỗi chu kỳ trôi qua mà không chụp là một chu kỳ **mất vĩnh viễn**.

    Không có bảng lịch sử băng thông. `_dat_lai_bang_thong` đưa bộ đếm về 0, và
    không có bản sao nào ở đâu để dựng lại — ngày ta muốn có trang băng thông,
    lịch sử của mọi khách sẽ bắt đầu từ con số 0 của hôm đó.

    Phép kiểm chốt **thứ tự**, vì đó là chỗ duy nhất có thể sai: đọc **sau** khi
    đặt lại thì hàm vẫn chạy, sự kiện vẫn có trường đó, và giá trị luôn là `0`.
    Một lỗi im lặng hoàn hảo — không ngoại lệ, không log, chỉ toàn số 0.
    """
    src = BILLING.read_text(encoding="utf-8")
    than = re.sub(r'(?s)""".*?"""', " ", src)
    than = re.sub(r"(?m)^\s*#.*$", " ", than)
    khoi = than[than.index("def thu_mot_chu_ky"):]
    khoi = khoi[: khoi.index("def _dat_lai_bang_thong")]
    # ⚠️ Cắt từ `credit.tru(` — tức **nhánh CÓ THU TIỀN**. Hàm có một nhánh ra
    #    sớm cho máy giá 0 (máy nội bộ), và nhánh đó cũng gọi
    #    `_dat_lai_bang_thong` nhưng KHÔNG ghi sự kiện. Đo thứ tự trên cả hàm sẽ
    #    so lần đọc của nhánh thu tiền với lần đặt lại của nhánh miễn phí — hai
    #    thứ không liên quan, và phép kiểm đỏ dù mã đúng. Đã dính đúng thế.
    khoi = khoi[khoi.index("credit.tru("):]

    i_doc = khoi.find("may.bang_thong_byte")
    i_dat = khoi.find("_dat_lai_bang_thong(may)")
    i_ghi = khoi.find("bang_thong_byte=")
    assert i_doc >= 0, "khong con doc `may.bang_thong_byte` truoc khi dat lai"
    assert i_dat >= 0, "khong con dat lai bang thong o nhanh thu tien"
    assert i_ghi >= 0, "su kien `thu_phi` khong con mang `bang_thong_byte=`"
    assert i_doc < i_dat < i_ghi, (
        "Thu tu phai la DOC -> DAT LAI -> GHI. Doc sau khi dat lai thi ham van "
        "chay, su kien van co truong do, va gia tri luon la 0 — mot loi im lang "
        "hoan hao.")


def test_su_kien_thu_phi_mang_du_ba_truong():
    """Sao kê thanh toán đọc `credit` và `den`; lịch sử băng thông đọc trường
    thứ ba. Thiếu một trường là hỏng một trong hai, ở hai thời điểm khác nhau."""
    src = BILLING.read_text(encoding="utf-8")
    khoi = src[src.index('ghi_su_kien(db, may.id, "thu_phi"'):][:400]
    for truong in ("credit=", "den=", "bang_thong_byte="):
        assert truong in khoi, f"su kien thu_phi thieu {truong}"


# ── 4 · D-04 · Menu chỉ hứa những trang có lý do tồn tại ──────────────────

def test_KHONG_hua_trang_anh_chup():
    """Ta chụp **đúng một** bản, **tự động** hằng tuần, khách không tự chụp được.

    Một "trang ảnh chụp" sẽ hiện một hàng, với một nút đã có sẵn trong khối Nguy
    hiểm của trang máy. `nav.py` tự đặt luật cho mình: mục "sắp có" phải *"có
    thật trong kế hoạch, không phải chỗ giữ chỗ cho vui"* — và mục này không.
    """
    from apps.vps.services import sao_luu

    assert sao_luu.GIU == 1, (
        "GIU da doi — neu nay giu NHIEU ban thi mot trang anh chup CO ly do "
        "ton tai, va quyet dinh D-04 phai duoc doc lai")
    khoa = {k for k, _ in nav.SAP_CO_MAY}
    assert "anh_chup" not in khoa


def test_muc_sap_co_KHONG_bao_gio_la_mot_lien_ket():
    """Hiện tên một mục chưa làm là **thông tin**; một liên kết 404 thì không."""
    ds = nav.menu("tong_quan", may=_may_gia())
    khoa_sap_co = {k for k, _ in nav.SAP_CO_MAY}
    for m in ds:
        if m["khoa"] in khoa_sap_co:
            assert m["href"] is None, f"muc sap co {m['khoa']!r} lai co href"


# ── 5 · Nền kiểu: một nguồn, không quay về template ───────────────────────

def test_lop_kieu_khu_VPS_ton_tai_va_khai_token_rieng():
    """Nếu lớp này biến mất thì fixture `kieu` của `test_304` trả rỗng và mọi
    phép kiểm trình bày ở đó đỏ. Chốt ở đây thêm một lần để câu lỗi nói đúng
    nguyên nhân thay vì nói "không tìm thấy `.vps-the`".
    """
    css = LTT_CSS.read_text(encoding="utf-8")
    assert "LỚP NGỮ NGHĨA CỦA KHU VPS" in css
    for token in ("--vps-teal:", "--vps-teal-hover:"):
        assert token in css, f"thieu token {token}"


def test_luat_nut_cua_khu_du_DAC_HIEU_de_thang_kieu_chung():
    """🔴 `_kieu_chung.html` là một khối `<style>` **nội tuyến trong `<head>`,
       đứng SAU thẻ `<link>` tới `ltt.css`** — và nó khai:

           button, .btn { background: var(--accent); … }

       Cùng độ đặc hiệu (0,1,0) nhưng **đến sau** ⇒ nó thắng mọi luật `.btn-*`
       một-class viết trong `ltt.css`. Không có cảnh báo nào; nút chỉ đơn giản
       là **màu đỏ** — tức màu của hành động không hoàn tác được, trên một cái
       nút tên là "Chọn gói này".

    ⚠️ Đây là lý do bản cũ đặt `.btn-goi` trong `<style>` của template. Chuyển
       nó sang `ltt.css` mà giữ nguyên độ đặc hiệu là **làm sống lại đúng lỗi
       đó** — và đã sống lại thật, đo bằng Chrome 26/08:
       `backgroundColor == rgb(239,55,49)`.

    Phép kiểm chốt **nguyên nhân** (hai class), vì kết quả chỉ thấy được bằng
    `getComputedStyle` trên trang render — `tools\\vps_dung_mau.py` làm việc đó.
    """
    css = LTT_CSS.read_text(encoding="utf-8")
    css = re.sub(r"(?s)/\*.*?\*/", " ", css)

    # Luật của _kieu_chung.html vẫn còn ⇒ cái bẫy vẫn còn ⇒ phép kiểm còn ý nghĩa.
    chung = (TEMPLATES / "_kieu_chung.html").read_text(encoding="utf-8")
    assert re.search(r"button,\s*\.btn\s*\{[^}]*background:var\(--accent\)"
                     r"|button,\s*\.btn\s*\{[^}]*background:\s*var\(--accent\)",
                     chung.replace("\n", " ")), (
        "`_kieu_chung.html` khong con dat background cho .btn — doc lai phep "
        "kiem nay truoc khi xoa no")

    for nut in ("btn-goi", "btn-may"):
        assert f".btn.{nut}" in css, (
            f"`.{nut}` phai viet la `.btn.{nut}` (do dac hieu 0,2,0). Mot class "
            f"thoi (0,1,0) se thua `button, .btn` cua _kieu_chung.html, va nut "
            f"van hanh se ra MAU DO.")
        assert not re.search(rf"(?<![.\w]){re.escape('.' + nut)}\s*[,{{]", css), (
            f"con mot luat `.{nut}` mot-class trong ltt.css — no se thua "
            f"_kieu_chung.html va lam nguoi doc tuong da sua xong")


def test_luat_gioi_han_be_ngang_CO_pham_vi():
    """`.app-main` là primitive **dùng chung** với khu API.

    Một luật `.app-main > .card{max-width:940px}` không phạm vi ở `ltt.css` sẽ
    lặng lẽ bóp cả cổng lập trình viên — và nó bóp bằng cách trang vẫn render,
    chỉ là hẹp lại, tức không ai báo lỗi.
    """
    css = LTT_CSS.read_text(encoding="utf-8")
    css = re.sub(r"(?s)/\*.*?\*/", " ", css)
    for m in re.finditer(r"([^\n{}]*\.app-main\s*>\s*\.card[^\n{]*)\{", css):
        chon = m.group(1).strip()
        assert ".vps-" in chon or ".dev-" in chon, (
            f"luat `{chon}` khong co pham vi — no cham moi khu dung .app-main")

    goc = TEMPLATES / "vps_chi_tiet.html"
    assert "vps-may" in goc.read_text(encoding="utf-8"), (
        "trang may khong con dat moc pham vi `vps-may`")


# ── 6 · Đợt 2 · Storefront công khai ──────────────────────────────────────

def _vps_html() -> str:
    """Template trang bán, **đã bóc chú thích** — cùng lý do với `test_304`."""
    t = (TEMPLATES / "vps.html").read_text(encoding="utf-8")
    return re.sub(r"(?s)\{#.*?#\}", " ", t)


@pytest.fixture(scope="module")
def trang_an_danh(tmp_path_factory) -> str:
    """HTML **thật** của `/vps` cho khách ẩn danh.

    Vài tính chất chỉ trả lời được bằng cái hiện ra, không bằng hình dạng của mã
    sinh ra nó — xem `test_khach_AN_DANH_chi_thay_MOT_bang_gia` để biết bản đọc
    template đã sai thế nào.
    """
    import os

    from fastapi.testclient import TestClient

    cu = {k: os.environ.get(k) for k in
          ("LTT_DATABASE_URL", "LTT_ENV", "LTT_SESSION_SECRET", "LTT_VPS")}
    thu_muc = tmp_path_factory.mktemp("vps311")
    os.environ.update({
        "LTT_DATABASE_URL": f"sqlite:///{(thu_muc / 'x.db').as_posix()}",
        "LTT_ENV": "development",
        "LTT_SESSION_SECRET": "test-vps-311",
        "LTT_VPS": "1",
    })
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models   # noqa: F401
    import apps.vps.tables        # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    try:
        r = client.get("/vps")
        assert r.status_code == 200, f"/vps an danh tra {r.status_code}"
        return r.text
    finally:
        client.close()
        dbmod.reset_engine()
        for k, v in cu.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

        # 🔴 Tra lai bien moi truong la CHUA DU.
        #
        # `apps/vps/manifest.py` khai `enabled=vps_app.enabled()` — doc co
        # **luc NAP module**. Fixture nay dat `LTT_VPS=1` roi import
        # `server.app`, nen manifest bi dong bang voi `enabled=True` cho **ca
        # tien trinh**. Tra bien moi truong ve khong go duoc cai da dong bang.
        #
        # Hau qua do duoc 27/08: `test_287::test_nen_tang_CHI_chay_viec_cua_
        # app_DANG_BAT` do — no `delenv("LTT_VPS")` roi khang dinh viec bao tri
        # cua vps khong chay, nhung manifest van bao "dang bat". Phep kiem do
        # xanh khi chay mot minh, do khi chay sau fixture nay. Tuc **fixture cua
        # toi lam mot phep kiem an ninh cua nguoi khac thoi do duoc gi**.
        #
        # ⚠️ Don sau lung minh. Mot fixture de lai trang thai toan cuc la mot
        #    fixture bien thu tu chay thanh mot bien an cua ca bo test.
        import importlib

        import apps.vps
        import apps.vps.manifest
        importlib.reload(apps.vps)
        importlib.reload(apps.vps.manifest)


def test_khach_AN_DANH_chi_thay_MOT_bang_gia(trang_an_danh):
    """🔴 Hai bảng giá trên một trang là hai nguồn cho cùng một con số.

    Từ Đợt 2, nhánh ẩn danh có bảng giá riêng. Thẻ "Tạo máy mới / Bảng giá" cũ
    phải **chỉ dựng cho người đã đăng nhập** — nếu không, khách ẩn danh thấy giá
    hai lần, và bản đứng dưới là bản có tiếng nói cuối cùng dù nó chỉ tình cờ ở
    đó.

    ⚠️ **Đo trên HTML ĐÃ RENDER, không đọc template.** Bản đầu của phép kiểm này
       tìm chuỗi `{% if da_dang_nhap %}` ngay trước thẻ tạo máy, và nó đỏ ngay ở
       Đợt 3 khi khối đó chuyển vào một nhánh `da_dang_nhap` mở **xa hơn ở trên**
       — mã đúng, phép kiểm sai. Một câu hỏi về *cái gì hiện ra* phải được trả
       lời bằng *cái hiện ra*, không bằng hình dạng của mã sinh ra nó.

    Cả hai vỏ gọi **cùng macro** `the_goi`, nên con số vẫn là một nguồn; phép
    kiểm này chốt *không hiện hai lần*, còn *không có hai bản dữ liệu* thì
    `test_304::test_moi_goi_co_mo_ta_va_mot_loi_ra` đã canh.
    """
    assert trang_an_danh.count('class="goi-luoi"') == 1, (
        "khach an danh thay nhieu hon MOT luoi bang gia")
    assert 'action="/vps/tao"' not in trang_an_danh, (
        "khach an danh thay bieu mau — no se POST va an 401")


def test_hinh_trang_tri_KHONG_day_gia_xuong_duoi_man_hinh_dau():
    """🔴 Đây là một luật, không phải một sở thích.

    Đo 25/08 trên 390×844: giá đầu tiên nằm ở **y=1121**, tức dưới màn hình đầu
    277px. Đợt đó kéo nó lên y=524, và Đợt 2 kéo tiếp xuống y=323. Một hình
    trang trí đặt **trên** giá ở màn hẹp sẽ đẩy nó xuống lại — tức tự tay làm
    hỏng đúng thứ vừa sửa xong, và làm hỏng theo cách không ai để ý vì trang vẫn
    render bình thường.
    """
    t = _vps_html()
    assert 'class="vps-hero-art" aria-hidden="true"' in t, (
        "hinh trang tri phai `aria-hidden` — no khong mang thong tin nao")

    css = LTT_CSS.read_text(encoding="utf-8")
    css = re.sub(r"(?s)/\*.*?\*/", " ", css)
    m = re.search(r"@media\(max-width:(\d+)px\)\{[^@]*?\.vps-hero-art\{display:none\}",
                  css.replace("\n", ""))
    assert m, "khong con luat an hinh trang tri o man hep"
    assert int(m.group(1)) >= 700, (
        f"nguong an hinh la {m.group(1)}px — qua hep, hinh se van day gia xuong "
        f"o may tinh bang")


def test_dai_loi_ich_noi_thu_KHACH_NHAN_DUOC_chu_khong_hua_them():
    """Cột phải nói thứ khách **nhận được**; khối "Đọc trước khi thuê" nói thứ
    dịch vụ **không** hứa. Trộn hai loại đó thì một trong hai bị đọc lướt.

    ⚠️ Và cột này tuyệt đối không được trượt thành trục bán hàng của đối thủ —
       cùng danh sách cấm với `test_304::test_dai_bon_o_noi_thu_KIEM_CHUNG_DUOC`.
    """
    t = _vps_html()
    i = t.index('class="vps-loi-ich"')
    khoi = t[i:t.index("</ul>", i)]
    for cam in ("99,9", "99.9", "uptime", "Uptime", "24/7", "SLA",
                "không giới hạn", "unlimited", "Enterprise", "cloud"):
        assert cam not in khoi, f"cot loi ich hua mot thu ta khong co: {cam!r}"
    so_muc = khoi.count("<li>")
    assert so_muc >= 4, f"chi co {so_muc} muc loi ich"


def test_CTA_cuoi_co_CA_HAI_loi_ra():
    """Người đọc hết sáu dòng hạn chế mà vẫn còn ở đây là người sẵn sàng nhất
    trên trang — và trước Đợt 2 họ phải cuộn ngược lên đầu để tìm một cái nút.

    Hai lối ra, không một: phần lớn người đọc trang này **chưa** có tài khoản,
    nhưng người đã có thì không được rơi vào đường tạo tài khoản mới.
    """
    t = _vps_html()
    i = t.index('class="vps-cta"')
    khoi = t[i:t.index("</div>", t.index('class="nut"', i))]
    assert 'href="/register"' in khoi, "CTA cuoi thieu duong tao tai khoan"
    assert "/login?next=" in khoi, "CTA cuoi thieu duong dang nhap"


def test_sau_dong_DOC_TRUOC_van_du_sau():
    """Đợt 2 đổi khối cảnh báo từ một cột dọc sang lưới ba cột. Đổi **cách bày**,
    không được đổi **nội dung** — `test_298` đối chiếu từng con số, nhưng nó
    không đếm số mục, nên một dòng bị đánh rơi khi tái cấu trúc sẽ lọt.
    """
    t = _vps_html()
    i = t.index('class="vps-doc-truoc"')
    khoi = t[i:t.index("</ul>", i)]
    assert khoi.count("<li>") == 6, (
        f"khoi 'Doc truoc khi thue' con {khoi.count('<li>')} muc, phai co 6 — "
        f"day la dieu kien cua Q103, khong phai van ban trang tri")


# ── 7 · Đợt 3 · Nhà của khách + tạo máy ───────────────────────────────────

def test_bon_o_chi_so_dem_o_ROUTE_chu_khong_trong_template():
    """Một vòng lặp đếm trong Jinja là logic không test được — và bốn con số này
    là thứ khách quét mắt đầu tiên.

    Chốt **hành vi của hàm đếm**, không chốt hình dạng template: đó là chỗ duy
    nhất có thể sai.
    """
    from apps.vps.routes import _thong_ke

    class _May:
        def __init__(self, tt):
            self.trang_thai = tt

    ds = [
        {"may": _May("dang_chay"), "con_ngay": 24},
        {"may": _May("dang_chay"), "con_ngay": 2},     # vừa chạy vừa sắp hết hạn
        {"may": _May("da_tat"), "con_ngay": 0},
        {"may": _May("dang_tao"), "con_ngay": None},   # chưa thu chu kỳ nào
        {"may": _May("loi"), "con_ngay": 30},
    ]
    tk = _thong_ke(ds)
    assert tk == {"tong": 5, "dang_chay": 2, "da_tat": 1, "sap_het_han": 2}, tk

    # `con_ngay is None` KHÔNG được tính là sắp hết hạn: `None` nghĩa là chưa thu
    # chu kỳ nào, không nghĩa là hết hạn. `None <= 3` ném TypeError ở Python 3,
    # nên lỗi này không im lặng — nhưng nó nổ TRÊN TRANG của khách.
    assert _thong_ke([{"may": _May("dang_tao"), "con_ngay": None}])["sap_het_han"] == 0


def test_nguong_SAP_HET_HAN_khop_giua_o_chi_so_va_the_may():
    """Ô chỉ số và nhãn đỏ trong danh sách phải nói **cùng một câu** về cùng một
    máy. Hai ngưỡng khác nhau ở hai chỗ là thứ chỉ lộ ra khi có đúng một máy rơi
    vào khe giữa chúng — tức muộn, và với một khách thật.
    """
    src = (GOC / "apps" / "vps" / "routes.py").read_text(encoding="utf-8")
    mac = (TEMPLATES / "_vps_mac.html").read_text(encoding="utf-8")
    assert "n <= 3" in src, "nguong o chi so doi roi"
    assert "con_ngay <= 3" in mac, "nguong tren the may doi roi"


def test_console_KHONG_mo_khi_may_khong_dieu_khien_duoc():
    """Một nút mở ra rồi báo lỗi tệ hơn một nút mờ có lý do.

    `dieu_khien.kiem_dieu_khien_duoc` là nguồn chân lý; template chỉ được hỏi
    lại nó, không tự phát minh một danh sách trạng thái thứ hai.
    """
    from apps.vps.services import dieu_khien

    t = _vps_html()
    i = t.index('class="vps-may-nut"')
    khoi = t[i:t.index("</div>", t.index("aria-disabled", i))]
    assert "aria-disabled" in khoi, "khong con nhanh vo hieu hoa cho Console"

    # Tập trạng thái mà template cho mở console phải là TẬP CON của tập mà
    # service thật sự cho phép — nếu không, nút mở ra rồi máy chủ từ chối.
    class _May:
        # `kiem_dieu_khien_duoc` đọc cả `vmid` — máy chưa có vmid là máy chưa
        # dựng xong, và nó từ chối vì lý do đó chứ không vì trạng thái.
        def __init__(self, tt):
            self.trang_thai = tt
            self.vmid = 9001

    cho_mo = set(re.findall(r'trang_thai in \("([a-z_]+)", "([a-z_]+)"\)', khoi))
    assert cho_mo, "khong doc duoc danh sach trang thai trong template"
    for bo in cho_mo:
        for tt in bo:
            dieu_khien.kiem_dieu_khien_duoc(_May(tt))   # không được ném


def test_DANH_SACH_may_khong_con_la_bang_bay_cot():
    """Bảng bắt mắt quét ngang cả màn hình để nối một máy với sáu thuộc tính của
    nó, và ở 390px thì bảy cột không còn là một bảng nữa.
    """
    t = _vps_html()
    # ⚠️ Cắt đúng danh sách máy. Bản đầu cắt từ `_("Máy của tôi")` tới hết và
    #    đỏ vì **bảng so sánh ba gói** trong biểu mẫu tạo máy bên dưới — một cái
    #    bảng hoàn toàn hợp lệ, và là thứ bảng làm tốt nhất (so cột với cột).
    #    "Đừng dùng bảng" chưa bao giờ là luật; luật là *đừng dùng bảng cho một
    #    đối tượng có sáu thuộc tính*.
    i = t.index('class="vps-may-ds"')
    khoi = t[i:t.index("{% endfor %}", i)]
    assert "<table" not in khoi, "danh sach may van la mot bang"
    assert 'class="vps-may-the' in khoi, "khong dung the may"
    assert "badge_trang_thai" in khoi and "do_bang_thong" in khoi, (
        "the may khong dung macro chung — hai trang se lech ngon ngu trang thai")


def test_DOC_TRUOC_hien_MOT_lan_cho_moi_nguoi_xem(trang_an_danh):
    """Khách ẩn danh: mở sẵn, ngay dưới bảng giá — họ đang **quyết định**.
    Chủ máy: gấp lại ở cuối trang — họ đã đồng ý một lần rồi, lúc bấm "Tạo máy".

    Một macro, một bản văn: `test_298` đối chiếu từng con số trong đó với hằng
    số thật, và hai bản sao thì lần sửa sau chỉ sửa một bản.
    """
    t = _vps_html()
    assert t.count("{% macro doc_truoc()") == 1, "khoi canh bao khong con la MOT macro"
    assert t.count("{{ doc_truoc() }}") == 2, (
        "phai goi dung hai lan — mot cho khach an danh, mot cho chu may")

    assert trang_an_danh.count('_("Đọc trước khi thuê")') == 0     # đã render
    assert trang_an_danh.count("Đọc trước khi thuê") == 1, (
        "khach an danh thay khoi canh bao nhieu hon mot lan")
    assert "<details" not in trang_an_danh[
        trang_an_danh.index("Đọc trước khi thuê") - 400:
        trang_an_danh.index("Đọc trước khi thuê")], (
        "khoi canh bao bi gap lai cho khach AN DANH — ho dang quyet dinh, "
        "khong duoc giau sau mot cu bam")


# ── 8 · D-01 · Tên máy ────────────────────────────────────────────────────

def test_ten_may_la_NHAN_khong_phai_hostname():
    """Khách tự cài Windows từ ISO — không cloud-init, không sysprep. Nền tảng
    **không có cách nào** đặt tên bên trong máy.

    Chốt bằng tài liệu vì đây là thứ một phiên sau sẽ đoán sai: cái tên `ten`
    không tự nói ra rằng nó không phải hostname.
    """
    from apps.vps import ten_may

    assert "hostname" in (ten_may.__doc__ or "").lower(), (
        "docstring khong noi ro `ten` KHONG phai hostname")


def test_ten_may_chuan_hoa_truoc_khi_so_sanh():
    """`"may  A "` và `"may A"` phải là **một** tên.

    Thiếu bước này thì khách gõ tên vào ô xác nhận phá huỷ sẽ bị từ chối một
    chuỗi **trông giống hệt** cái đang hiện trên màn hình — và không có cách nào
    để họ tự thấy khoảng trắng thừa.
    """
    from apps.vps import ten_may

    assert ten_may.chuan_hoa("  may  A  ") == "may A"
    assert ten_may.chuan_hoa(None) == ""
    assert ten_may.kiem("  vps 01 ") == "vps 01"


def test_ten_may_tu_chi_dung_ky_tu_an_toan():
    from apps.vps import ten_may

    for xau in ("", "a", "x" * 41, "<script>", "a/b", "a\\b", "a;b"):
        try:
            ten_may.kiem(xau)
        except ten_may.TenKhongHopLeError:
            continue
        raise AssertionError(f"nhan mot ten khong nen nhan: {xau!r}")

    # Dấu tiếng Việt PHẢI qua được: tên là dữ liệu của khách.
    assert ten_may.kiem("Máy bán hàng") == "Máy bán hàng"


def test_ten_tu_sinh_KHONG_dung_phep_cong_de_dem():
    """Khách có `vps-01` và `vps-03` (đã xoá `vps-02`) thì `len(may) + 1` cho ra
    `vps-03` — một tên **đã tồn tại**. Lỗi đó chỉ lộ ra ở bước kiểm trùng, dưới
    dạng một câu lỗi khó hiểu cho một tên mà khách không hề gõ.
    """
    src = (GOC / "apps" / "vps" / "ten_may.py").read_text(encoding="utf-8")
    than = re.sub(r'(?s)""".*?"""', " ", src)
    khoi = than[than.index("def tu_sinh"):]
    assert "for i in range" in khoi, "tu_sinh khong con quet tim so con trong"
    assert "len(" not in khoi.split("return")[0], (
        "tu_sinh dang dem bang do dai danh sach — se sinh ra ten da ton tai")


def test_doi_ten_KHONG_doi_go_xac_nhan():
    """Đổi nhãn là việc **đảo được**. Đặt rào chắn ở việc đảo được thì rào chắn ở
    việc KHÔNG đảo được bị nhờn — và đó là lúc nó thôi bảo vệ được ai.
    """
    src = (GOC / "apps" / "vps" / "routes.py").read_text(encoding="utf-8")
    khoi = src[src.index("def doi_ten_may"):]
    khoi = khoi[: khoi.index("\n@router")]
    assert "verify_csrf_token" in khoi, "doi ten khong kiem CSRF"
    assert "_may_cua_khach" in khoi, "doi ten khong kiem chu so huu"
    assert "xac_nhan" not in khoi, (
        "doi ten dang doi go xac nhan — day la viec dao duoc")


def test_o_TEN_MAY_khong_bat_buoc_va_co_goi_y():
    """Một trường bắt buộc ở bước cuối của luồng mua là một chỗ để khách bỏ dở."""
    t = _vps_html()
    i = t.index('id="vps-ten"')
    the = t[t.rindex("<input", 0, i):t.index(">", i)]
    assert "required" not in the, "o ten dang bat buoc"
    assert "ten_goi_y" in the, "o ten khong co goi y"
    assert 'maxlength="40"' in the, "thieu tran do dai o phia trinh duyet"


# ── 9 · Đợt 4 · Trung tâm điều khiển một máy ──────────────────────────────

def _chi_tiet_html() -> str:
    t = (TEMPLATES / "vps_chi_tiet.html").read_text(encoding="utf-8")
    return re.sub(r"(?s)\{#.*?#\}", " ", t)


def test_trang_may_KHONG_co_o_mat_khau():
    """🔴 Chốt quan trọng nhất của trang này.

    Ảnh tham chiếu vẽ một ô `Password ••••••` có nút hiện và nút chép. Nền tảng
    **không giữ mật khẩu nào** — khách tự cài Windows và tự đặt tài khoản. Vẽ ô
    đó ra là hứa một thứ không tồn tại, đúng lúc khách đang cần nó nhất, và cách
    duy nhất họ phát hiện ra là bấm vào rồi thấy trống.

    Trang **có** một hàng "Mật khẩu" — nhưng nó nói ra sự thật, không nhận là
    giữ được gì.
    """
    t = _chi_tiet_html()
    assert 'type="password"' not in t, "co mot o nhap mat khau tren trang may"
    for cam in ("••", "&bull;", "reveal", "hien-mat-khau", "show-password"):
        assert cam not in t, f"co dau hieu mot o mat khau bi che: {cam!r}"
    i = t.index('_("Mật khẩu")')
    assert "không giữ bản nào" in t[i:i + 400], (
        "hang 'Mat khau' khong noi ro nen tang KHONG giu mat khau")


def test_trang_may_KHONG_hua_thu_khong_co():
    """Cùng danh sách cấm với trang bán — mở rộng ra trang một máy.

    Ảnh tham chiếu có cột trái "Uptime SLA 99.95% · Hỗ trợ 24/7 · NVMe
    Enterprise" và một nút "Gia hạn ngay" không dẫn tới đâu.
    """
    t = _chi_tiet_html()
    for cam in ("99,9", "99.9", "uptime", "Uptime", "SLA", "24/7",
                "Enterprise", "Gia hạn ngay", "hàng ngày", "Tạo ticket"):
        assert cam not in t, f"trang may hua mot thu ta khong co: {cam!r}"


def test_nhip_anh_chup_va_chu_ky_DOC_TU_MA():
    """Đổi `sao_luu.GIU` hay `CHU_KY_NGAY` mà quên sửa trang là nói sai với
    người đang trả tiền — và nó sai **lặng lẽ**, vì trang vẫn render.
    """
    t = _chi_tiet_html()
    for bien in ("so_anh_giu", "chu_ky_ngay", "an_han_ngay"):
        assert bien in t, f"trang may viet cung thay vi doc `{bien}`"

    src = (GOC / "apps" / "vps" / "routes.py").read_text(encoding="utf-8")
    assert "sao_luu.GIU" in src and "CHU_KY_NGAY" in src, (
        "route khong con lay ba hang so do tu ma")
    assert "AN_HAN_TRUOC_KHI_XOA_NGAY" in src


def test_dai_hanh_dong_THEO_TRANG_THAI():
    """Không bày mọi nút ngang hàng. Máy đã tắt thì "Bật" là việc duy nhất đáng
    làm; máy đang tạo thì không việc nào — và một nút bị máy chủ từ chối tệ hơn
    không có nút.
    """
    t = _chi_tiet_html()
    # ⚠️ Neo vào dải nút CHÍNH (dải chứa "Cài Windows"), không vào `vps-hd` đầu
    #    tiên. Từ VPS V2 có một dải `vps-hd` **trước** nó: nhánh "đang có việc
    #    chạy", chỉ hiện Console. Neo vào cái đầu tiên là đo nhầm khối.
    i = t.rindex('class="vps-hd"', 0, t.index("Cài Windows"))

    # `dang_tao` và `bi_treo` ra nhánh CHỈ THÔNG TIN — tức trước cả dải nút.
    for tt in ("bi_treo", "dang_tao"):
        assert f'may.trang_thai == "{tt}"' in t[:i], (
            f"trang thai {tt!r} khong co nhanh rieng truoc dai hanh dong")

    # Và nhánh "đang có việc chạy" phải đứng TRƯỚC mọi nhánh trạng thái.
    #
    # Vì sao đây là mệnh đề mạnh nhất trong ba mệnh đề ở đây: từ ADR-03, bấm một
    # nút điều khiển **không** đổi `trang_thai` ngay. Nên một máy `dang_chay` mà
    # đang tắt dở vẫn khớp nhánh `dang_chay` và vẫn bày đủ nút — khách bấm tiếp
    # vào một máy đang bận. Nhánh `viec` là thứ duy nhất chặn được điều đó.
    assert t.index("{% if viec %}") < t.index('may.trang_thai == "bi_treo"'), (
        "nhanh 'dang co viec chay' phai dung TRUOC moi nhanh trang thai")

    # Trong dải nút, `da_tat` đổi NÚT CHÍNH: "Bật" thay cho "Khởi động lại /
    # Tắt máy". Không phải hai dải khác nhau — cùng một dải, khác nút.
    dai = t[i:t.index("{% endif %}", t.index("Cài Windows", i))]
    assert 'may.trang_thai == "da_tat"' in dai, (
        "dai hanh dong khong re nhanh theo trang thai")
    assert dai.index('_("Bật")') < dai.index('_("Khởi động lại")'), (
        "voi may da tat, 'Bat' phai la nhanh dau — no la viec duy nhat dang lam")


def test_nhat_ky_KHONG_do_JSON_tho_va_KHONG_lo_chi_tiet_cum():
    """`upid` của Proxmox và `vmid` không giúp khách việc gì, và chúng nói ra
    hình dạng của cụm."""
    from apps.vps.routes import _chi_tiet_doc_duoc

    ra = _chi_tiet_doc_duoc({"upid": "UPID:pve:0000A1B2", "vmid": 9001,
                             "ip_noi_bo": "10.51.0.51",
                             "credit": 1790, "den": "2026-09-19T00:00:00"})
    assert "UPID" not in ra and "9001" not in ra, f"lo chi tiet noi bo: {ra}"
    # 🔴 `ip_noi_bo` lot qua CA vong kiem bang canh dung san, va chi hien ra o
    #    luot nghiem thu dau tien voi MAY THAT (27/08): nhat ky in
    #    `ip_noi_bo: 10.51.0.51` — dia chi trong LAN cua cum.
    #
    # ⚠️ Bai hoc chung: mot danh sach CAM chi chan duoc thu no biet ten, va du
    #    lieu gia chi chua nhung khoa nguoi viet nghi ra. Do la ly do mot luot
    #    chay that khong the thay the bang mot bo canh dung san.
    assert "10.51.0.51" not in ra, f"lo dia chi trong LAN cua cum: {ra}"
    assert "1790" in ra, "mat mot chi tiet co nghia voi khach"
    assert "19/09/2026" in ra, (
        "ngay van o dang ISO — dung cho may doc, sai cho mot dong nhat ky")
    assert _chi_tiet_doc_duoc(None) == ""
    assert _chi_tiet_doc_duoc("mot chuoi") == ""


def test_khoi_NGUY_HIEM_giu_o_go_ten_o_CA_BA_viec():
    """Ảnh tham chiếu bỏ mất ô gõ tên và chỉ để lại ba cái nút. Ảnh sai.

    Khuôn "gõ đúng tên" của GitHub tồn tại vì ba việc này **không hoàn tác
    được** — chúng phải khó bấm nhầm hơn một cú click.
    """
    t = _chi_tiet_html()
    i = t.index('class="vps-nguy"')
    khoi = t[i:]
    assert khoi.count('name="xac_nhan"') == 3, (
        f"chi con {khoi.count('name=\"xac_nhan\"')} o go xac nhan, phai co 3")
    assert khoi.count("required") >= 3, "o xac nhan khong con bat buoc"
    # Thứ tự: ít thiệt hại trước.
    assert (khoi.index("khoi-phuc") < khoi.index("cai-lai")
            < khoi.index('/xoa"')), (
        "thu tu khoi Nguy hiem phai la khoi phuc -> cai lai -> xoa")


def test_ba_trang_trong_mot_may_dung_CHUNG_macro_danh_tinh():
    """Ba trang cùng hiện **một** danh tính máy. Ba bản sao sẽ lệch, và cái lệch
    sẽ là cái nói sai địa chỉ — tức nói sai đúng thứ khách tới đây để lấy.

    ⚠️ Ở Đợt 4 mới có **một** trang dùng; Đợt 5 và 6 nối tiếp. Phép kiểm chốt
       rằng macro tồn tại và không ai dựng bản thứ hai bằng tay.
    """
    mac = (TEMPLATES / "_vps_mac.html").read_text(encoding="utf-8")
    assert "{% macro dinh_may(" in mac
    assert "may.id" in mac and "may.vmid" not in mac, (
        "dai danh tinh dang hien `vmid` — do la so hieu ben trong Proxmox, "
        "khach khong dung duoc vao viec gi con ta thi lo hinh dang cua cum")
    # CẢ BA trang trong một máy, không phải một.
    for ten in ("vps_chi_tiet.html", "vps_cai_dat.html", "vps_console.html"):
        noi_dung = (TEMPLATES / ten).read_text(encoding="utf-8")
        assert "mac.dinh_may(" in noi_dung, f"{ten} khong dung macro danh tinh"
        assert 'import "_vps_mac.html" as mac with context' in noi_dung, (
            f"{ten} import macro thieu `with context` — moi chuoi ben trong "
            f"macro se ra tieng Viet tren ban EN, va khong phep kiem `.po` nao "
            f"bat duoc vi chuoi CO trong catalog va DA dich")


# ── 12 · Đợt 7 · Cổng liên trang ──────────────────────────────────────────

def test_NAM_trang_VPS_dung_CHUNG_mot_ngon_ngu_trang_thai():
    """Không template nào được tự viết chữ trạng thái hay tự chọn màu.

    Năm trang cùng nói về cùng những cái máy. Một trang tự dịch `bi_treo` thành
    một câu khác là một trang nói một điều khác về máy của khách — và không ai
    phát hiện ra cho tới khi họ mở hai tab cạnh nhau.
    """
    tep = sorted(TEMPLATES.glob("vps*.html"))
    assert len(tep) >= 5

    # ⚠️ **Không** cấm chuỗi `_("Đang chạy")` xuất hiện trong template. Bản đầu
    #    của phép kiểm này làm thế và đỏ ngay: bốn ô chỉ số ở màn B dùng đúng
    #    những chữ đó làm **nhãn cột** — cùng từ, khác việc. Một phép kiểm không
    #    phân biệt được "nhãn của một cái ô" với "trạng thái của một cái máy" là
    #    một phép kiểm bắt người ta viết vòng vo để né nó.
    #
    # 🔑 Tính chất đo được là: **class badge không bao giờ do template tự gán**.
    #    Badge chỉ dựng qua macro, và macro lấy class từ `nhan.badge()`.
    for p in tep:
        t = re.sub(r"(?s)\{#.*?#\}", " ", p.read_text(encoding="utf-8"))
        for cls in sorted(set(nhan.BADGE.values())):
            assert f'"badge {cls}' not in t, (
                f"{p.name} tu gan class badge {cls!r} — dung "
                f"`mac.badge_trang_thai()` de bon trang noi cung mot ngon ngu")

    # Và bốn trang hiện trạng thái máy đều phải đi qua macro đó — trực tiếp,
    # hoặc gián tiếp qua `dinh_may()` (chính nó gọi `badge_trang_thai`).
    for ten in ("vps.html", "vps_chi_tiet.html", "vps_cai_dat.html",
                "vps_console.html"):
        t = (TEMPLATES / ten).read_text(encoding="utf-8")
        assert "badge_trang_thai(" in t or "mac.dinh_may(" in t, (
            f"{ten} khong dung badge chung")


def test_KHONG_trang_VPS_nao_hua_thu_KHONG_CO():
    """Danh sách cấm áp cho **cả năm trang**, không chỉ trang bán.

    ⚠️ Bóc chú thích trước khi khẳng định. Đây là lớp lỗi đã lặp **năm lần**
       trong dự án: khối giải thích *"ảnh tham chiếu có 99.9% uptime"* làm chính
       phép kiểm cấm-uptime đỏ.
    """
    cam = ("99,9", "99.9", "uptime", "Uptime", "SLA", "24/7", "Enterprise",
           "AES-256", "unlimited", "không giới hạn")
    for p in sorted(TEMPLATES.glob("vps*.html")):
        t = re.sub(r"(?s)\{#.*?#\}", " ", p.read_text(encoding="utf-8"))
        for x in cam:
            assert x not in t, f"{p.name} hua mot thu ta khong co: {x!r}"


def test_KHONG_nut_nao_tro_toi_mot_route_KHONG_TON_TAI():
    """Một nút dẫn tới 404 là một nút tệ hơn không có nút.

    Quét mọi `action=` và `href=` trỏ vào `route_prefix` trong năm template, so
    với **bảng route thật** của router — không so với một danh sách gõ tay.
    """
    from apps.vps.routes import router

    that = {tuple(re.sub(r"\{[a-z_]+\}", "*", str(getattr(r, "path", "")))
                  .strip("/").split("/"))
            for r in router.routes}
    that.discard(("",))

    # ⚠️ Một đoạn đường là **biểu thức Jinja** thì coi như ký tự đại diện: trang
    #    máy lặp `[("bat", …), ("tat", …), ("khoi-dong-lai", …)]` và dựng
    #    `{{ hanh_dong }}` — giá trị chỉ biết được lúc chạy. Điều còn kiểm được,
    #    và là rủi ro thật, là **một đoạn viết tay gõ sai**.
    mau = re.compile(r'(?:action|href)="\{\{ app\.route_prefix \}\}([^"]*)"')
    for p in sorted(TEMPLATES.glob("vps*.html")):
        t = re.sub(r"(?s)\{#.*?#\}", " ", p.read_text(encoding="utf-8"))
        for duong in mau.findall(t):
            doan = tuple("*" if "{{" in x else x
                         for x in duong.split("#")[0].strip("/").split("/") if x)
            if not doan:
                continue        # `route_prefix` tran = trang goc cua khu, luon co
            khop = [d for d in that
                    if len(d) == len(doan)
                    and all(a == "*" or b == "*" or a == b for a, b in zip(d, doan))]
            assert khop, (
                f"{p.name}: `route_prefix/{'/'.join(doan)}` khong khop route nao. "
                f"Route co that: {sorted('/'.join(d) for d in that)}")


# ── 10 · Đợt 5 · Hướng dẫn cài Windows ────────────────────────────────────

def _cai_dat_html() -> str:
    t = (TEMPLATES / "vps_cai_dat.html").read_text(encoding="utf-8")
    return re.sub(r"(?s)\{#.*?#\}", " ", t)


def test_cot_buoc_la_MUC_LUC_khong_phai_TIEN_DO():
    """🔴 Không có tiến độ nào lưu ở máy chủ, và Prompt 04 cấm dựng một cái.

    Ảnh tham chiếu có "3 / 8", dấu tích, và nút "Tôi đã hoàn tất bước này". Cả
    ba đều hứa rằng hệ thống **biết khách đang ở đâu** — mà nó thì không biết.
    Một dấu tích không lưu được còn tệ hơn không có: nó biến mất khi tải lại
    trang, và khách sẽ tưởng mình mất tiến độ.
    """
    t = _cai_dat_html()
    for cam in ("hoàn tất bước này", "Bỏ qua hướng dẫn", "checked", "progress",
                "Tạo ticket", "24/7"):
        assert cam not in t, f"trang cai dat co dau hieu tien do/ho tro gia: {cam!r}"
    assert not re.search(r"\d\s*/\s*8", t), "co mot bo dem tien do kieu `3 / 8`"
    assert 'href="#buoc-' in t, "cot buoc khong phai muc luc co mo neo"


def test_tam_buoc_doc_tu_MOT_nguon():
    """Cột bên trái và các mục bên phải phải cùng một danh sách. Hai danh sách
    chép tay thì lần thêm bước sau chỉ sửa một bên, và mục lục trỏ vào hư không.
    """
    from apps.vps.routes import BUOC_CAI_DAT

    assert len(BUOC_CAI_DAT) == 8, f"co {len(BUOC_CAI_DAT)} buoc, cho doi 8"
    t = _cai_dat_html()
    assert "buoc_muc_luc" in t, "cot buoc khong doc tu route"
    for so, _nhan in BUOC_CAI_DAT:
        assert f'id="buoc-{so}"' in t, f"khong co muc tuong ung buoc {so}"


def test_canh_bao_PRESS_ANY_KEY_giu_NGUYEN_VAN():
    """Đây là chỗ tốn công nhất trong cả quá trình cài, và nó không tự hiện ra.

    Bấm một phím ở màn hình đó là quay lại **đầu** trình cài đặt — tức mất 15–25
    phút vừa chờ.
    """
    t = _cai_dat_html()
    assert "Press any key to boot from CD or DVD" in t
    assert "đừng bấm gì cả" in t
    assert "quay lại đầu trình cài đặt" in t, (
        "mat cau giai thich HAU QUA — canh bao khong noi vi sao thi khong ai nghe")
    i = t.index("Press any key")
    assert "vps-canh-to" in t[max(0, i - 700):i], (
        "canh bao khong con nam trong khoi noi bat")


def test_so_do_o_dia_DUNG_SO_THAT_cua_khach():
    """🔴 D-03 · Sơ đồ, KHÔNG phải ảnh chụp.

    Một ảnh bitmap mang số liệu **cứng** (`80.0 GB`) sẽ hiện `80.0 GB` cho khách
    gói Nhỏ — sai đúng ở con số họ cần đối chiếu, và sai ở bước mà chọn nhầm thì
    phải cài lại từ đầu.
    """
    t = _cai_dat_html()
    assert "Drive 0 Unallocated Space" in t, (
        "mat chuoi khach phai NHAN RA tren man hinh")
    assert "{{ dia_gb }}" in t, "so do dang viet cung dung luong dia"
    assert "<img" not in t, "trang dang dung mot anh — xem quyet dinh D-03"

    from apps.vps.routes import huong_dan_cai_dat   # noqa: F401
    src = (GOC / "apps" / "vps" / "routes.py").read_text(encoding="utf-8")
    assert "dia_tong_gb(may.plan_id, may.dia_them_gb)" in src, (
        "dia_gb phai gom ca dia mua them, khong chi dia cua goi")


# ── 11 · Đợt 6 · Console ──────────────────────────────────────────────────

def _console_html() -> str:
    t = (TEMPLATES / "vps_console.html").read_text(encoding="utf-8")
    return re.sub(r"(?s)\{#.*?#\}", " ", t)


def test_console_KHONG_hua_thuat_toan_ma_hoa_va_KHONG_dem_nguoc():
    """🔴 Hai lời hứa bịa trong ảnh tham chiếu.

    ① "AES-256" — không nơi nào trong mã khẳng định thuật toán.
    ② "Phiên sẽ hết hạn sau 14:47" — vé tiêu **ngay lúc mở WebSocket**, nên sau
      khi nối xong **không còn hạn nào để đếm**. Một đồng hồ ở đây đếm một thứ
      không có, và nó sẽ chạy hết rồi… không có gì xảy ra.
    """
    t = _console_html()
    for cam in ("AES", "Encrypted", "setInterval", "countdown", "dem_nguoc",
                "Chrome", "navigator.userAgent"):
        assert cam not in t, f"console hua/hien mot thu khong co nguon: {cam!r}"
    # Tính chất "một lần" thì GIỮ — nó có thật và đáng nói ra.
    assert "một lần" in t, "mat tinh chat 've dung mot lan', mot thu CO that"


def test_console_GIU_NGUYEN_giao_thuc():
    """⛔ Đợt 6 chỉ đổi trình bày. Bốn thứ này là giao thức, không phải giao diện.

    Mất một trong bốn là mất một tính chất bảo mật hoặc một hành vi mà khách
    dựa vào — và mất **lặng lẽ**, vì trang vẫn hiện ra một khung đen.
    """
    t = _console_html()
    assert "rfb.scaleViewport = true" in t
    assert "rfb.resizeSession = false" in t, (
        "dang doi do phan giai may cua khach theo cua so trinh duyet")
    assert 'tabindex="0"' in t, (
        "khung mat `tabindex` — chuot chay ma ban phim khong, va trieu chung la "
        "'go khong len chu'")
    assert "location.reload()" in t and "rfb.connect" not in t, (
        "dang tu noi lai bang ve DA TIEU — mot vong lap that bai im lang")


def test_console_anh_xa_DUNG_BA_su_kien_RFB_dang_co():
    """Không phát minh sự kiện thứ tư. noVNC phát `connect`, `disconnect`
    (clean hoặc không) và `securityfailure` — bốn trạng thái, ba sự kiện.
    """
    t = _console_html()
    for sk in ("connect", "disconnect", "securityfailure"):
        assert f'addEventListener("{sk}"' in t, f"mat nhanh su kien {sk!r}"
    assert "e.detail.clean" in t, (
        "khong con phan biet ngat SACH voi MAT ket noi — hai thu khac nhau voi "
        "nguoi dang dung")


def test_console_trang_thai_la_BADGE_co_cham_VA_chu():
    """Màu không bao giờ đứng một mình — luật của cả khu, và console là chỗ dễ
    quên nhất vì nó gần như không có chữ nào khác."""
    t = _console_html()
    assert 'tt.className = "tt badge "' in t, "trang thai console khong dung badge"
    for lop in ("b-ok", "b-err", "b-warn", "b-grey"):
        assert lop in t, f"thieu mau trang thai {lop!r}"
    assert 'innerHTML = \'<span class="dot"></span>\'' in t, "badge khong co cham"


# ── phụ trợ ───────────────────────────────────────────────────────────────

def _ma_trang_thai_trong_bang() -> set[str]:
    """Mọi mã trạng thái mà **mã đang chạy** ghi vào hoặc so sánh với.

    ⚠️ Cột `trang_thai` là `String(16)` trần — **không có `CheckConstraint`**,
       nên không có danh sách hợp lệ nào để đọc từ lược đồ. Bản đầu của phép
       kiểm này đọc ràng buộc, không tìm thấy gì, và trả về **tập rỗng** — tức
       một phép kiểm xanh không kiểm gì cả. Câu `assert len(ma) >= 6` ở nơi gọi
       là thứ duy nhất phát hiện ra.

    ⇒ Nguồn thật là chính mã: một trạng thái mà `provisioning`/`billing`/`jobs`
      **ghi được** thì khách **thấy được**, nên nó phải có nhãn. Đọc cả phép gán
      lẫn phép so sánh — máy vào một trạng thái ở tệp này và bị đọc ở tệp kia.
    """
    ra: set[str] = set()
    mau = re.compile(r"""trang_thai\s*(?:=|==|!=|\bin\b)\s*
                         \(?\s*((?:"[a-z_]+"\s*,?\s*)+)\)?""", re.X)
    for p in (GOC / "apps" / "vps").rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        src = re.sub(r'(?s)""".*?"""', " ", src)
        src = re.sub(r"(?m)^\s*#.*$", " ", src)
        for m in mau.finditer(src):
            ra |= set(re.findall(r'"([a-z_]+)"', m.group(1)))
    return ra


def _loai_su_kien_duoc_ghi() -> set[str]:
    """Mọi loại sự kiện được truyền cho `ghi_su_kien` trong khu VPS.

    Đọc bằng AST chứ không regex: đối số thứ ba có thể là hằng chuỗi hoặc một
    f-string (`f"{ten_thao_tac}_that_bai"`). Với f-string ta lấy **phần hằng**
    và bỏ qua, vì hậu tố đã có phép kiểm riêng.
    """
    ra: set[str] = set()
    for p in (GOC / "apps" / "vps").rglob("*.py"):
        cay = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            ten = getattr(nut.func, "attr", None) or getattr(nut.func, "id", None)
            if ten != "ghi_su_kien" or len(nut.args) < 3:
                continue
            d = nut.args[2]
            if isinstance(d, ast.Constant) and isinstance(d.value, str):
                ra.add(d.value)
    return ra


class _MayGia:
    id = "0123456789abcdef"
    ten = "vps-01"


def _may_gia():
    return _MayGia()
