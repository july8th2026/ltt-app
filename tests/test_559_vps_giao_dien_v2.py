"""VPS V2 Pha 09 — giao diện nói đúng thứ đang xảy ra.

Từ ADR-03, bấm một nút điều khiển **không** đổi `trang_thai` ngay: nó mở một thao
tác và nộp một job. Đó là bản sửa đúng cho ba lỗi P0 — nhưng nó dịch một vấn đề
sang giao diện: nếu trang im lặng, khách thấy y nguyên trạng thái cũ, kết luận
nút hỏng, và bấm lại.

Nên bộ này chốt ba câu mà trang **phải** trả lời được:

1. *"tôi vừa bấm — nó có ăn không?"* → nhánh "đang có việc chạy";
2. *"trạng thái này mới hay cũ?"* → độ tươi của phép đo;
3. *"vì sao máy tôi không ra Internet được?"* → cách ly, và nó khác "tạm dừng".

Và một câu **không** trả lời: RAM/đĩa bên trong máy khách. Không đo được thì
không có ô cho nó.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
CHI_TIET = GOC / "server" / "templates" / "vps_chi_tiet.html"
DANH_SACH = GOC / "server" / "templates" / "vps.html"
ROUTES = GOC / "apps" / "vps" / "routes.py"


def _chi_tiet() -> str:
    return CHI_TIET.read_text(encoding="utf-8")


# ── 1. "Tôi vừa bấm — nó có ăn không?" ──────────────────────────────────────

def test_trang_may_co_nhanh_DANG_CO_VIEC_CHAY():
    t = _chi_tiet()
    assert "{% if viec %}" in t


def test_dang_ban_thi_KHONG_bay_nut_dieu_khien_nao():
    """Một nút sẽ bị máy chủ từ chối tệ hơn không có nút.

    `thao_tac.mo` từ chối khi máy đang bận — nhưng khách chỉ biết điều đó **sau**
    khi bấm, và với ba nút trong khối Nguy hiểm thì họ còn phải gõ đúng tên máy
    trước rồi mới nghe "đang bận".
    """
    t = _chi_tiet()
    khoi = t[t.index("{% if viec %}"):t.index('{% elif may.trang_thai == "bi_treo" %}')]
    for nut in ("/bat", "/tat", "/khoi-dong-lai"):
        assert f'action="{{{{ app.route_prefix }}}}/{{{{ may.id }}}}{nut}"' \
            not in khoi, f"con bay nut {nut} khi may dang ban"
    # Console thì VẪN để: nó không đụng vào máy, và nó là đường khách nhìn thấy
    # việc đang xảy ra.
    assert "/console" in khoi


def test_khoi_NGUY_HIEM_cung_bi_an_khi_may_dang_ban():
    t = _chi_tiet()
    assert 'may.trang_thai != "da_xoa" and not viec' in t, (
        "ba nut khong hoan tac duoc van bay ra khi may dang ban")


def test_trang_DANH_SACH_cung_hien_viec_dang_chay():
    """Khách thường bấm ở trang danh sách rồi quay lại đúng trang đó.

    Chỉ sửa trang chi tiết là để nguyên câu hỏi ở đúng nơi nó hay được hỏi nhất.
    """
    t = DANH_SACH.read_text(encoding="utf-8")
    assert "{% if m.viec %}" in t


def test_route_cap_VIEC_cho_ca_hai_trang():
    src = ROUTES.read_text(encoding="utf-8")
    assert '"viec": _viec_dang_chay(db, m)' in src, "trang danh sach thieu"
    assert '"viec": _viec_dang_chay(db, may)' in src, "trang chi tiet thieu"


def test_nhan_tac_vu_dich_o_ROUTE_khong_o_TEMPLATE():
    """Một bảng tra chép tay trong Jinja là bản sao thứ hai của `nhan.TAC_VU`.

    Bản sao sẽ lệch, và trang sẽ nói một câu khác về cùng một việc.
    """
    t = _chi_tiet() + DANH_SACH.read_text(encoding="utf-8")
    for ma in ("dang_kd_lai", "dang_khoi_phuc", "dang_cap_phat"):
        assert f'"{ma}"' not in t, f"template tu tra ma tac vu {ma!r}"
    assert "nhan.tac_vu(" in ROUTES.read_text(encoding="utf-8")


# ── 2. "Trạng thái này mới hay cũ?" ─────────────────────────────────────────

def test_trang_may_phan_biet_CHUA_HOI_DUOC_voi_CHUA_HOI_LAI():
    """Hai câu khác nhau, hai nguyên nhân, hai chỗ đi sửa.

    `mat_lien_lac` = đã hỏi máy chủ và **không có trả lời** — sự cố hạ tầng.
    `quan_sat_cu` = **chưa hỏi lại** đủ gần đây — có thể vòng đối chiếu chưa tới
    lượt, hoặc nó đã chết.

    Gộp làm một câu là lấy mất của khách đúng thông tin họ cần để biết nên chờ
    hay nên gọi hỗ trợ.
    """
    t = _chi_tiet()
    assert "{% if mat_lien_lac %}" in t
    assert "{% elif quan_sat_cu %}" in t
    i, j = t.index("mat_lien_lac"), t.index("quan_sat_cu")
    assert i < j, "nhanh 'khong hoi duoc' phai dung truoc nhanh 'co the da cu'"


def test_route_cap_do_tuoi_tu_MO_HINH_chu_khong_tu_tinh_lai():
    src = ROUTES.read_text(encoding="utf-8")
    assert "trang_thai_may.qua_cu(may)" in src
    assert "trang_thai_may.MAT_LIEN_LAC" in src


# ── 3. Cách ly ≠ tạm dừng ───────────────────────────────────────────────────

def test_trang_may_noi_ro_CACH_LY_khac_TAM_DUNG():
    """Ba điều khách sắp hỏi hỗ trợ, và cả ba phải nằm trên trang.

    Đĩa còn không, máy còn chạy không, vào bằng đường nào.
    """
    t = _chi_tiet()
    assert "{% if bi_cach_ly %}" in t
    khoi = t[t.index("{% if bi_cach_ly %}"):t.index("{% if mat_lien_lac %}")]
    assert "Console" in khoi, "khong noi duong vao con lai"
    assert "còn nguyên" in khoi, "khong noi du lieu con nguyen"


def test_ly_do_cach_ly_hien_ra_cho_khach():
    """Một trạng thái phạt không có lý do là một trạng thái khách không cãi được."""
    assert "may.cach_ly_ly_do" in _chi_tiet()


# ── 4. Không hứa thứ không đo được ─────────────────────────────────────────

def test_trang_may_KHONG_co_o_RAM_hay_CPU_dang_dung():
    """Máy khách không có guest agent (virtio treo trên cụm này).

    Một ô "RAM đang dùng: —" là một lời hứa rằng ta sẽ điền nó, và nó không bao
    giờ được điền. `plan.ram_mb` thì khác — đó là **cấu hình đã bán**, một con
    số ta biết chắc.
    """
    # Bỏ chú thích trước khi soi: đầu tệp có một khối liệt kê **những thứ ảnh
    # tham chiếu có mà backend KHÔNG có** ("Uptime SLA 99.95%…"), tức chính chỗ
    # ghi lại quyết định không hứa. Soi cả chú thích là bắt đúng lời giải thích
    # của mình — cùng lớp lỗi với bộ dò văn bản trừng phạt việc giải thích.
    t = re.sub(r"(?s)\{#.*?#\}", " ", _chi_tiet())
    for cam in ("RAM đang dùng", "CPU đang dùng", "Đĩa còn trống", "Uptime"):
        assert cam not in t, f"hua thu khong do duoc: {cam}"


def test_trang_may_KHONG_hua_sao_luu_doc_lap():
    """Trang nói "Ảnh chụp", không nói "Sao lưu" — và khác biệt ấy là thật.

    Ảnh nằm cùng pool với đĩa gốc; hỏng đĩa là mất cả hai. Hứa "sao lưu" rồi
    giao một ảnh chụp là loại lời hứa người ta chỉ phát hiện sai đúng vào lúc
    mất dữ liệu.
    """
    t = _chi_tiet()
    xau = [d for d in t.splitlines()
           if re.search(r'_\("[^"]*[Ss]ao l[ưu]u', d) and "Ảnh chụp" not in d]
    assert xau == [], f"trang may dung tu 'sao luu': {xau}"


# ── 5. API công khai: một quyết định, không phải một khoảng trống ───────────

def test_VPS_van_dong_o_api_v1_va_ly_do_duoc_ghi_lai():
    """Không mở `/api/v1` cho VPS là một **quyết định**, và nó phải đọc được.

    Hợp đồng của `/api/v1` là *quote → giữ chỗ → quyết toán* cho **một lượt
    chạy**. Một máy ảo là một **hợp đồng thuê có thời hạn**: không có "một lượt"
    nào để báo giá, và tiền đã đi qua `paid_until` mỗi 30 ngày.

    Ép nó vào khuôn đó là dựng một hợp đồng nói sai về thứ nó bán — đắt hơn hẳn
    việc chưa có API. Xem `docs/vps_v2/ADR_INDEX.md` ADR-06.
    """
    adr = (GOC / "docs" / "vps_v2" / "ADR_INDEX.md").read_text(encoding="utf-8")
    assert "ADR-06" in adr
    assert "api/v1" in adr or "API công khai" in adr


def test_manifest_van_KHONG_khai_ToolSpec_nao():
    """Trạng thái thật, và nó khớp `docs/PUBLIC_API/APP_API_COVERAGE_FINAL.md`."""
    from apps.vps.manifest import MANIFEST
    assert not getattr(MANIFEST, "tools", ())


# ── 6. Render thật: trang phải mở được với mô hình mới ─────────────────────

@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'vps-ui2.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vps-ui2")
    monkeypatch.setenv("LTT_VPS", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models   # noqa: F401
    import apps.vps.tables        # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield dbmod
    dbmod.reset_engine()


def test_trang_chi_tiet_RENDER_duoc_khi_may_dang_ban(moi_truong):
    """Kiểm bằng render thật, không chỉ đọc template.

    Một biến thiếu trong ngữ cảnh làm Jinja ném ở **runtime**, không ở lượt đọc
    tệp — và trang trắng chỉ lộ ra khi có người mở nó.
    """
    from fastapi.testclient import TestClient

    from apps.vps import trang_thai_may as tt
    from apps.vps.services import thao_tac
    from apps.vps.tables import VpsGateway, VpsInstance
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    from server.app import create_app

    gen = moi_truong.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="vps-ui2@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 100_000)
        g = VpsGateway(ten="cong-ui2", vung="sgp", ip_cong_khai="203.0.113.10")
        db.add(g)
        db.flush()
        m = VpsInstance(user_id=u.id, plan_id="vps-vua",
                        os_id="winsrv2022-gui", gateway_id=g.id,
                        trang_thai="dang_chay", vmid=555)
        db.add(m)
        db.flush()
        thao_tac.mo(db, m, tt.DANG_KD_LAI, boi=u.id)
        db.commit()
        may_id, email = m.id, u.email
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    client = TestClient(create_app())
    try:
        # Biểu mẫu đăng nhập đòi CSRF và dùng trường `username`. Bỏ qua hai
        # điều đó thì nhận 422 — một lỗi của đồ gá đội lốt một lỗi của sản phẩm.
        login = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"',
                          login.text).group(1)
        client.post("/login", data={"username": email,
                                    "password": "matkhau-tot-12",
                                    "csrf_token": token})
        r = client.get(f"/vps/{may_id}")
        assert r.status_code == 200, r.status_code
        # Nhãn tác vụ phải hiện ra — đây là toàn bộ điểm của pha này.
        assert "Đang khởi động lại" in r.text
        # Và KHÔNG được có nút phá huỷ nào trên một máy đang bận.
        assert "/khoi-phuc" not in r.text and "/cai-lai" not in r.text
    finally:
        client.close()


# ── 7. Trang bán hàng KHÔNG được rò hình dạng hạ tầng ───────────────────────

def test_trang_ban_hang_KHONG_ro_ten_bien_moi_truong_hay_ten_Proxmox(moi_truong):
    """🔴 Đo được trên PRODUCTION 09/09/2026, ngay sau lượt deploy VPS V2.

    Trang `/vps` **công khai** — khách chưa đăng nhập cũng thấy — in nguyên văn:

        Hiện chưa nhận máy mới. (chua cau hinh Proxmox: production ma khong co
        LTT_VPS_PROXMOX_CA: tu choi noi toi Proxmox khi khong xac minh duoc
        chung chi. Ghim CA that, hoac chay o moi truong khac.)

    Ba thứ sai cùng lúc: tiếng Việt-không-dấu trộn thuật ngữ trên một trang bán
    hàng; **tên biến môi trường** nội bộ; và chữ `Proxmox` — thứ mà chính
    `services/proxmox.py` viết rằng khách *"không bao giờ nhìn thấy"*.

    ⚠️ Rò rỉ này **có sẵn từ trước** bản sửa TLS (`_suc_chua` luôn trả
       `f"chua cau hinh Proxmox: {exc}"`). Bản sửa chỉ làm `exc` dài ra, và nhờ
       dài ra mà nó lộ. Một lỗi ẩn sau một chuỗi ngắn vẫn là một lỗi.

    Ca này chốt **hành vi qua đường render thật**, không đọc mã: môi trường test
    vốn không có cấu hình Proxmox, nên đường `ChuaCauHinh` là đường mặc định ở
    đây — đúng đường mà production vừa đi.
    """
    from fastapi.testclient import TestClient

    from server.app import create_app

    client = TestClient(create_app())
    try:
        r = client.get("/vps")
        assert r.status_code == 200, r.status_code
        # Tiền đề: phải THẬT SỰ đang ở nhánh không đọc được sức chứa, nếu không
        # ca này xanh rỗng vì trang chưa bao giờ hiện dải cảnh báo nào.
        assert "alert-err" in r.text, "trang khong o nhanh 'chua nhan may moi'"
        for cam in ("Proxmox", "LTT_VPS_PROXMOX", "chua cau hinh",
                    "ChuaCauHinh", "127.0.0.1", "8006"):
            assert cam not in r.text, f"trang ban hang ro {cam!r}"
    finally:
        client.close()


def test_ly_do_ky_thuat_van_di_vao_LOG(caplog):
    """Không rò ra trang **không** có nghĩa là vứt đi.

    Người vận hành cần đúng chuỗi ấy để biết phải đặt biến nào. Bỏ hẳn nó là
    đổi một lỗi lộ liễu lấy một lỗi im lặng — và im lặng thì tốn nhiều giờ hơn.
    """
    import logging

    from apps.vps import routes

    with caplog.at_level(logging.WARNING, logger="apps.vps.routes"):
        suc_chua, ly_do = routes._suc_chua(None)

    assert suc_chua is None
    assert "Proxmox" not in ly_do, "cau cho khach khong duoc nhac Proxmox"
    ghi = " ".join(x.getMessage() for x in caplog.records)
    assert "suc chua" in ghi, "khong ghi log ly do ky thuat"


# ── 8. Trang MÁY cũng không được rò — cùng hạng lỗi, khác trang ────────────

#: Thứ không bao giờ được có mặt trong một câu viết cho khách.
#:
#: Chốt **tập hợp**, không chốt số lượng: thêm một mã lỗi mới vào `nhan.MA_LOI`
#: thì ca dưới tự soi nó, không cần ai nhớ sửa test.
CAM = ("Proxmox", "LTT_VPS_", "8006", "Error", "Traceback", "upid", "UPID",
       "qemu", "vmid")


def test_moi_cau_trong_MA_LOI_deu_sach(moi_truong):
    """Quét cả bảng, không quét một dòng ví dụ."""
    from apps.vps import nhan

    assert nhan.MA_LOI, "bang rong thi ca nay xanh rong"
    for ma, cau in list(nhan.MA_LOI.items()) + [("<la>", nhan.MA_LOI_KHONG_RO)]:
        for cam in CAM:
            assert cam not in cau, f"cau cua ma {ma!r} co {cam!r}"


def test_ma_loi_LA_khong_duoc_tra_ve_chinh_no(moi_truong):
    """Điểm lệch có chủ ý so với `trang_thai()` và `su_kien()`.

    Chỗ gọi `nhan.ma_loi` từng chứa **chuỗi lỗi thô**. Nếu hàm này giữ quy ước
    "mã lạ trả về chính nó" thì một chuỗi thô đi vào sẽ đi thẳng ra trang — tức
    bản vá tự vô hiệu hoá mình mà vẫn xanh.
    """
    from apps.vps import nhan

    tho = "VpsJobError: Proxmox tu choi lenh: 500 tai /nodes/pve1/qemu/555"
    ra = nhan.ma_loi(tho)
    assert ra != tho
    assert "Proxmox" not in ra


def test_trang_may_KHONG_ro_loi_tho_khi_mot_thao_tac_hong(moi_truong):
    """🔴 Đo được trên PRODUCTION 09/09/2026, cùng ngày với lần rò ở `/vps`.

    `jobs._danh_dau_loi` ghi `f"{type(exc).__name__}: {exc}"` vào `may.ly_do`,
    rồi đẩy **chính chuỗi đó** vào nhật ký. Cả hai đều là trang của khách, nên
    một lệnh Proxmox hỏng hiện ra nguyên văn:

        VpsJobError: Proxmox tu choi lenh: <lỗi thô, kèm đường /nodes/…/qemu/…>

    Ca này đi qua **render thật** và phủ cả hai bề mặt trong một lượt, vì sửa
    một chỗ mà quên chỗ kia là kết cục mặc định của một rò rỉ có hai lối ra.
    """
    from fastapi.testclient import TestClient

    from apps.vps import jobs
    from apps.vps.services.proxmox import ProxmoxError
    from apps.vps.tables import VpsGateway, VpsInstance
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    from server.app import create_app

    # Chuỗi mồi mang đúng hình dạng thứ Proxmox trả về thật.
    THO = "500 loi tai https://10.10.0.2:8006/api2/json/nodes/pve1/qemu/555/status"

    gen = moi_truong.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="vps-ro@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 100_000)
        g = VpsGateway(ten="cong-ro", vung="sgp", ip_cong_khai="203.0.113.11")
        db.add(g)
        db.flush()
        m = VpsInstance(user_id=u.id, plan_id="vps-vua", os_id="winsrv2022-gui",
                        gateway_id=g.id, trang_thai="dang_chay", vmid=555)
        db.add(m)
        db.flush()
        db.commit()
        may_id, email = m.id, u.email

        # Đúng đường mà production đi: một lệnh Proxmox hỏng giữa chừng.
        jobs._danh_dau_loi(db, may_id, ProxmoxError(THO))

        may = db.get(VpsInstance, may_id)
        assert may.ly_do, "khong ghi ly do thi ca nay xanh rong"
        assert THO not in may.ly_do
        assert "Proxmox" not in may.ly_do
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    client = TestClient(create_app())
    try:
        login = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"',
                          login.text).group(1)
        client.post("/login", data={"username": email,
                                    "password": "matkhau-tot-12",
                                    "csrf_token": token})
        r = client.get(f"/vps/{may_id}")
        assert r.status_code == 200, r.status_code
        # Tiền đề: trang phải THẬT SỰ đang hiện khối lý do, nếu không mọi
        # khẳng định "không có chuỗi cấm" ở dưới đều đúng một cách rỗng.
        assert "Lý do" in r.text, "trang khong hien khoi ly do"
        for cam in (THO, "10.10.0.2", "8006", "ProxmoxError", "qemu"):
            assert cam not in r.text, f"trang may ro {cam!r}"
    finally:
        client.close()


def test_chi_tiet_ky_thuat_van_di_vao_LOG_va_giu_duoc_MA(moi_truong, caplog):
    """Cạnh chiếu ngược: sửa rò rỉ bằng cách **xoá** thông tin.

    Người vận hành cần chuỗi thô để chẩn đoán, và cần **mã** để nối dòng này
    với `vps_thao_tac.ma_loi`. Mất một trong hai là đổi một lỗi lộ liễu lấy một
    lỗi im lặng.
    """
    import logging

    from apps.vps import jobs
    from apps.vps.services.proxmox import ProxmoxError
    from apps.vps.tables import VpsEvent, VpsGateway, VpsInstance
    from platform_core.users import tao_nguoi_dung

    THO = "500 loi tai https://10.10.0.2:8006/api2/json/nodes/pve1"
    gen = moi_truong.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="vps-log@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        g = VpsGateway(ten="cong-log", vung="sgp", ip_cong_khai="203.0.113.12")
        db.add(g)
        db.flush()
        m = VpsInstance(user_id=u.id, plan_id="vps-vua", os_id="winsrv2022-gui",
                        gateway_id=g.id, trang_thai="dang_chay", vmid=556)
        db.add(m)
        db.flush()
        db.commit()

        with caplog.at_level(logging.WARNING, logger="apps.vps.jobs"):
            jobs._danh_dau_loi(db, m.id, ProxmoxError(THO))

        ghi = " ".join(x.getMessage() for x in caplog.records)
        assert THO in ghi, "chi tiet ky thuat bi vut mat"
        assert "proxmox_tu_choi" in ghi, "log khong mang MA de noi voi thao tac"

        from sqlalchemy import select
        e = db.execute(select(VpsEvent).where(VpsEvent.instance_id == m.id)
                       .where(VpsEvent.loai == "loi")).scalars().first()
        assert e is not None, "khong ghi su kien"
        assert e.chi_tiet.get("ma_loi") == "proxmox_tu_choi"
        assert THO not in str(e.chi_tiet), "su kien van mang chuoi tho"
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
