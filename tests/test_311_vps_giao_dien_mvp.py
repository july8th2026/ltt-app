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


def test_khach_AN_DANH_chi_thay_MOT_bang_gia():
    """🔴 Hai bảng giá trên một trang là hai nguồn cho cùng một con số.

    Từ Đợt 2, nhánh ẩn danh có bảng giá riêng. Thẻ "Tạo máy mới / Bảng giá" cũ
    phải **chỉ dựng cho người đã đăng nhập** — nếu không, khách ẩn danh thấy giá
    hai lần, và bản đứng dưới là bản có tiếng nói cuối cùng dù nó chỉ tình cờ ở
    đó.

    ⚠️ Cả hai vỏ gọi **cùng macro** `the_goi`, nên con số vẫn là một nguồn. Phép
       kiểm này chốt *không hiện hai lần*, không chốt *không có hai bản dữ liệu* —
       việc đó `test_304::test_moi_goi_co_mo_ta_va_mot_loi_ra` đã canh.
    """
    t = _vps_html()
    i = t.index('_("Tạo máy mới") if ban_duoc')
    truoc = t[:i]
    assert truoc.rstrip().endswith("{% if da_dang_nhap %}") or \
        "{% if da_dang_nhap %}" in truoc[-400:], (
        "the 'Tao may moi / Bang gia' khong con duoc bao boi `da_dang_nhap` — "
        "khach an danh se thay bang gia HAI lan")


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
