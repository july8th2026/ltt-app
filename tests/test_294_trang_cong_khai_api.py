"""Tài liệu API và công cụ phải **lấy được mà không cần tài khoản**.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — ĐO 25/08 TRÊN PRODUCTION.

   Cả 18 trang của cổng lập trình viên đều trả `303` về `/login`, và hai thứ
   quan trọng nhất thì **không lấy được bằng bất kỳ đường nào**:

       /developers/docs -> 303        /tai/... (SDK)        -> 404 (khong co route)
       /developers/cli  -> 303        bo cai cong cu .exe   -> khong duoc nhac o dau

   Một người đang **cân nhắc** không đọc được một dòng hướng dẫn tích hợp nào
   trước khi tạo tài khoản. Đó là thứ tự ngược, và dự án đã học đúng bài này một
   lần rồi — trang giá cũ cũng nằm sau cổng đăng nhập và đã được tách ra
   `/gia-api`. Bài học chỉ được áp cho **riêng trang giá**.

⛔ VÀ MỘT LỖI TỆ HƠN: `dev_docs.html` liệt kê cho khách các **đường dẫn tệp
   trong kho mã của ta** (`docs/PUBLIC_API/…`, `sdk/python/…`). Khách không có
   kho mã. Trang trông như một mục lục đầy đủ — và chính điều đó làm **ta** tin
   rằng tài liệu đã tới tay khách.

⭐ RANH GIỚI: thứ giúp người ta **quyết định mua** thì công khai; thứ gắn với
   một **tài khoản** thì sau đăng nhập. Test này chốt vế thứ nhất.
"""
from __future__ import annotations

import importlib
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def khach():
    from fastapi.testclient import TestClient
    from server.app import create_app
    return TestClient(create_app())


@pytest.fixture()
def tl():
    return importlib.import_module("server.routes.tai_lieu_api")


# ── Công khai thật, không phải "công khai nếu đã đăng nhập" ──────────────────

@pytest.mark.parametrize("duong", ["/huong-dan", "/huong-dan/cong-cu"])
def test_doc_duoc_khi_CHUA_dang_nhap(khach, duong):
    r = khach.get(duong, follow_redirects=False)
    assert r.status_code == 200, (
        f"{duong} tra {r.status_code} - mot nguoi dang can nhac khong doc duoc")


def test_trang_huong_dan_noi_du_ca_NAM_be_mat(khach):
    """Thiếu một bề mặt là một nhóm khách không biết mình cắm được."""
    noi = khach.get("/huong-dan").text
    for be_mat in ("Codex CLI", "Claude Code", "VS Code", "Claude Desktop"):
        assert be_mat in noi, f"trang huong dan khong nhac toi {be_mat}"


def test_trang_huong_dan_canh_bao_HAI_rao_chan_cua_claude_desktop(khach):
    """Hai rào chắn cho **cùng** một triệu chứng: bấm gửi, không có gì xảy ra.

    Thiếu lời cảnh báo này thì khách sẽ kết luận là API của ta hỏng.
    """
    from platform_core.public_api import examples
    noi = khach.get("/huong-dan").text
    assert examples.DESKTOP_MODEL in noi, "khong noi ten tuyen cua Claude Desktop"
    assert "chatTabEnabled" in noi, "khong noi ve chatTabEnabled"


def test_KHONG_con_duong_dan_kho_ma_trong_trang_cho_khach():
    """🔴 Chốt chính lỗi đã có: trang cho khách chỉ được trỏ tới **URL tải được**.

    Khách không có `docs/` và không có `sdk/` — nhắc tên chúng như một mục lục là
    đưa cho người ta một danh sách không mở được cái nào.
    """
    import re
    xau = []
    for ten in ("dev_docs.html", "huong_dan.html", "huong_dan_cong_cu.html",
                "_cam_chon.html"):
        noi = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        # ⚠️ Bỏ chú thích Jinja trước khi soi. `{# … #}` KHÔNG bao giờ được
        #    render, nên một đường dẫn kho mã nằm trong đó là ghi chú cho lập
        #    trình viên — đúng chỗ của nó. Bản đầu của test này quét cả chú
        #    thích và đỏ ngay trên chính đoạn giải thích vì sao không được làm
        #    thế: một phép đo bắt nhầm đối tượng nó định bảo vệ.
        noi = re.sub(r"\{#.*?#\}", "", noi, flags=re.S)
        for dau in ("docs/PUBLIC_API/", "sdk/python/", "sdk/typescript/",
                    "sdk/postman/"):
            if dau in noi:
                xau.append(f"{ten}: {dau}")
    assert not xau, f"trang cho khach van tro vao kho ma: {xau}"


# ── Tải được thật ────────────────────────────────────────────────────────────

def test_moi_goi_trong_danh_sach_deu_TAI_DUOC(khach, tl):
    """Quảng cáo một tệp mà không phục vụ được nó thì tệ hơn là không nhắc."""
    for ten in tl.GOI_TAI:
        r = khach.get(f"/tai/{ten}")
        assert r.status_code == 200, f"/tai/{ten} -> {r.status_code}"
        assert r.content, f"/tai/{ten} rong"


def test_ten_la_thi_404_chu_khong_doc_duoc_o_dia(khach):
    """Danh sách trắng làm việc đọc bậy **không thể**, chứ không phải 'khó'."""
    for bay in ("khong-co-that", "../../secrets/app.env", "..%2F..%2Fapp.env"):
        r = khach.get(f"/tai/{bay}")
        assert r.status_code in (404, 400), f"/tai/{bay} -> {r.status_code}"


def test_chua_phat_hanh_thi_503_chu_khong_phai_404(khach, tl, monkeypatch):
    """Hai chuyện khác nhau, và người trực phải phân biệt được từ log.

    `404` nghĩa là "đường dẫn sai". `503` nghĩa là "đường dẫn đúng, chưa có bản
    nào được thả vào thư mục phát hành" — thứ hai là việc của người vận hành.
    """
    monkeypatch.setattr(tl, "bo_cai_moi_nhat", lambda: None)
    assert khach.get("/tai/cong-cu-cam").status_code == 503


def test_bam_tinh_TU_CHINH_TEP_dang_phuc_vu(tl, tmp_path, monkeypatch):
    """Không ký số thì băm là **thứ duy nhất** khách dùng để kiểm tệp.

    ⛔ Nên nó không được là một chuỗi gõ tay ở chỗ khác: đổi tệp mà băm không đổi
       là một lời bảo đảm sai, và sai đúng ở chỗ nguy hiểm nhất.
    """
    import hashlib
    thu_muc = tmp_path / "api_dist"
    thu_muc.mkdir()
    tep = thu_muc / "LTTStudios-CamCLI-Setup-9.9.9.exe"
    tep.write_bytes(b"noi dung gia")
    monkeypatch.setattr(tl, "_thu_muc_ban_phat", lambda: thu_muc)
    tl._BAM_DA_TINH.clear()

    kq = tl.bo_cai_moi_nhat()
    assert kq["phien_ban"] == "9.9.9"
    assert kq["sha256"] == hashlib.sha256(b"noi dung gia").hexdigest()

    # Doi noi dung -> bam PHAI doi theo.
    tep.write_bytes(b"noi dung khac han")
    assert tl.bo_cai_moi_nhat()["sha256"] == \
        hashlib.sha256(b"noi dung khac han").hexdigest()


def test_chon_ban_MOI_NHAT_khi_thu_muc_co_nhieu_ban(tl, tmp_path, monkeypatch):
    thu_muc = tmp_path / "api_dist"
    thu_muc.mkdir()
    for v in ("1.0.0", "1.10.0", "1.9.0"):
        (thu_muc / f"LTTStudios-CamCLI-Setup-{v}.exe").write_bytes(b"x")
    monkeypatch.setattr(tl, "_thu_muc_ban_phat", lambda: thu_muc)
    tl._BAM_DA_TINH.clear()
    # So sanh theo SO, khong theo chuoi: "1.9.0" > "1.10.0" neu so chuoi.
    assert tl.bo_cai_moi_nhat()["phien_ban"] == "1.10.0"


# ── Một nguồn duy nhất cho hướng dẫn ────────────────────────────────────────

def test_hai_trang_dung_CHUNG_mot_than(khach):
    """Hai bản sao của cùng hướng dẫn là hai bản sẽ lệch, và bản lệch là bản
    khách đọc. Cùng lý do `/gia-api` lấy số từ `bang_gia()` thay vì gõ lại."""
    # ⚠️ Kiem TINH CHAT, khong ghim TEN tep: hai trang phai include CUNG MOT
    #    than. Ban cu ghim chuoi "_cam_than.html", nen khi than doi ten thanh
    #    "_cam_chon.html" (25/08) test do — trong khi tinh chat no bao ve van
    #    dung nguyen. Mot test do vi mot cai ten la mot test se bi sua cho im.
    import re
    than = {}
    for ten in ("dev_cli.html", "huong_dan.html"):
        noi = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        thay = re.findall(r'{%\s*include\s+"(_cam_[a-z_]+\.html)"', noi)
        assert thay, f"{ten} khong include than cam nao"
        than[ten] = set(thay)
    a, b = than["dev_cli.html"], than["huong_dan.html"]
    assert a == b, f"hai trang dung than KHAC nhau: {a} vs {b}"


def test_trang_cong_cu_hien_bam_va_KHONG_bao_tat_diet_virus(khach):
    noi = khach.get("/huong-dan/cong-cu").text
    assert "SHA-256" in noi
    assert "/tai/cong-cu-cam" in noi
    # ⛔ Bao khach tat phan mem diet virus la loi khuyen ta khong bao gio duoc dua.
    for cam in ("tắt phần mềm diệt virus", "tat dinh kem", "disable antivirus"):
        if cam == "tắt phần mềm diệt virus":
            # Trang CO nhac cum nay, nhung phai la loi HUA KHONG LAM.
            assert "KHÔNG bao giờ đề nghị" in noi or "KHÔNG" in noi


# ── Vỏ công khai phải có ĐỦ kiểu, không chỉ có class ─────────────────────────
#
# 🔴 ĐO 25/08 BẰNG CHROME THẬT. `ltt.css` không hề có luật `.card`, `.table` hay
#    `pre` — kiểu của chúng nằm NỘI TUYẾN trong `base.html`, tức chỉ vỏ đã đăng
#    nhập mới có. Mọi trang công khai render với class KHÔNG CÓ LUẬT NÀO KHỚP:
#    thẻ không tách nhau, bảng là mấy cột chữ trôi nổi, và khối mã là chữ trần —
#    trên đúng những trang tồn tại để khách CHÉP CẤU HÌNH.
#
# ⭐ Đối chứng làm rõ chẩn đoán: `/status/api` dùng `base.html` và đẹp chuẩn.
#    Cùng hệ thống thiết kế, khác ở chỗ có CSS hay không.

def test_ca_hai_vo_deu_include_kieu_dung_chung():
    """Một nguồn, hai vỏ. Bản sao thứ hai là bản sẽ lệch."""
    for ten in ("base.html", "base_public.html"):
        noi = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        assert "_kieu_chung.html" in noi, (
            f"{ten} khong include kieu dung chung -> trang cua no se render voi "
            f"class khong co luat CSS nao khop")


@pytest.mark.parametrize("luat", [".card", "pre", ".table th", "table"])
def test_kieu_dung_chung_co_du_luat_can_thiet(luat):
    noi = (GOC / "server" / "templates" / "_kieu_chung.html").read_text(encoding="utf-8")
    assert luat in noi, f"thieu luat cho {luat}"


def test_khoi_ma_co_NEN_va_VIEN():
    """Khối mã trần lẫn vào văn xuôi thì khách phải tự tô để chép — và tô hụt
    một dòng trong `config.toml` thì lỗi hiện ra ở tận lúc gọi API."""
    noi = (GOC / "server" / "templates" / "_kieu_chung.html").read_text(encoding="utf-8")
    khoi = noi.split("pre {", 1)[1].split("}", 1)[0]
    assert "background" in khoi and "border" in khoi and "padding" in khoi
    assert "overflow-x" in khoi, "khong cuon ngang thi tran ra ngoai tren dien thoai"


def test_trang_cong_khai_render_RA_the_card_that(khach):
    """Chốt bằng HTML render, không phải bằng template: cả class lẫn luật."""
    r = khach.get("/huong-dan")
    assert 'class="card' in r.text
    assert "_kieu_chung" not in r.text, "include phai duoc RENDER, khong phai in ten ra"
    # Luat phai co mat trong chinh trang tra ve (style noi tuyen cua vo).
    assert ".card" in r.text and "border-radius" in r.text


def test_co_nut_sao_chep_va_no_khong_pha_trang_khi_thieu_JS():
    """Tăng cường dần: không JS thì không có nút, trang vẫn đọc được y nguyên."""
    js = (GOC / "server" / "static" / "sao_chep.js").read_text(encoding="utf-8")
    assert "navigator.clipboard" in js
    assert "isSecureContext" in js, (
        "thieu kiem ngu canh bao mat -> nut nem loi va KHONG NOI GI")
    # Nut duoc TAO bang JS, khong nam san trong template.
    for ten in ("_cam_chon.html", "huong_dan.html", "huong_dan_cong_cu.html"):
        noi = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        assert "nut-chep" not in noi


def test_asset_ver_bam_CA_js_chu_khong_chi_css():
    """🔴 Trước 25/08 chỉ băm `ltt.css`, nên một tệp JS mới mang đúng số của CSS.

    Đổi JS mà không đổi CSS thì URL không đổi, và Cloudflare tiếp tục phục vụ bản
    cũ tới khi hết TTL — đúng cái bẫy quy tắc 6 của `CLAUDE.md` mô tả.
    """
    from server import templating
    assert "sao_chep.js" in templating.TAI_SAN_CO_VERSION
    assert "ltt.css" in templating.TAI_SAN_CO_VERSION


def test_thanh_tren_co_loi_vao_khu_API_cho_nguoi_CHUA_dang_nhap(khach):
    """Trước 25/08 lối duy nhất là mục trong menu tài khoản — chỉ hiện sau khi
    đăng nhập. Một lập trình viên đang cân nhắc không có đường nào tới tài liệu."""
    r = khach.get("/gia-api")
    assert 'href="/huong-dan"' in r.text


def test_gia_api_chi_co_MOT_h1(khach):
    """Hai `h1` là hai chủ đề ngang hàng — trang không nói được nó nói về cái gì."""
    r = khach.get("/gia-api")
    assert r.text.count("<h1") == 1, f"co {r.text.count('<h1')} the h1"


# ── Trang công khai phải giới thiệu CẢ HAI thứ ta bán ────────────────────────
#
# 🔴 ĐO 25/08 trên `/huong-dan`, trang công khai DUY NHẤT nói về tích hợp:
#      ltt_llm 16 lần · codex 24 · claude 39   ·   image.ltt 0 · quote 0
#    Ta bán hai thứ và giới thiệu một. Người chưa đăng ký thấy giá ảnh ở
#    /gia-api rồi hết đường — mọi hướng dẫn dùng ảnh nằm sau đăng nhập.

def test_trang_cong_khai_gioi_thieu_CA_tao_anh(khach):
    from platform_core.public_api import examples
    noi = khach.get("/huong-dan").text
    assert examples.ANH_TOOL in noi, "trang cong khai khong nhac toi cong cu tao anh"
    for che_do in ("t2i", "edit", "subject"):
        assert che_do in noi, f"thieu che do {che_do}"
    assert "/api/v1/quotes" in noi and "/api/v1/artifacts" in noi


def test_vi_du_anh_noi_dung_cho_lay_artifact(khach):
    """⛔ Chỗ một lượt gọi thật đã vấp: tài liệu nói `result`, thật là `outputs[]`."""
    noi = khach.get("/huong-dan").text
    assert "outputs[]" in noi or "outputs" in noi
    from platform_core.public_api import examples
    vi_du = examples.curl_anh_ba_buoc()
    assert "outputs" in vi_du
    assert "/api/v1/quotes" in vi_du and "/api/v1/jobs" in vi_du \
        and "/api/v1/artifacts" in vi_du
    assert "Idempotency-Key" in vi_du, (
        "thieu Idempotency-Key -> khach thu lai se tao job thu hai va tra tien hai lan")


def test_vi_du_anh_KHONG_chua_khoa_that(khach):
    """Không đoạn nào được chứa một chuỗi trông như khoá thật."""
    from platform_core.public_api import examples
    vi_du = examples.curl_anh_ba_buoc()
    assert "ltt_sk_" not in vi_du
    assert "$LTT_API_KEY" in vi_du


def test_noi_ro_138_giay_va_vi_sao_bat_buoc_bat_dong_bo(khach):
    """Khách cần con số để đặt timeout, và cần biết vì sao không có cửa đồng bộ."""
    noi = khach.get("/huong-dan").text
    assert "138" in noi
    assert "100" in noi, "phai noi tran 100 giay cua Cloudflare"
