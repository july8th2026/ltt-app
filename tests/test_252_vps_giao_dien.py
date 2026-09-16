"""Bề mặt HTTP của app VPS: cái cờ phải thật sự đóng cửa, và trang phải nói thật.

Hai lớp test, và lớp đầu quan trọng hơn:

**1. Cấu trúc.** `registry.mount_all()` gắn router của mọi app **bất kể**
`manifest.enabled` (`test_226` đã chốt sự thật đó). Nên với app này, lớp chặn ở
route là **lớp duy nhất** thật sự đóng cửa. Một test gọi thử chỉ phủ những route
đã biết; cái nguy hiểm là route **sẽ được thêm sau**. Vì thế phải chốt bằng cấu
trúc: mọi handler đều có cổng cờ, và cổng cờ đứng **trước** `require_login`.

Thứ tự đó không phải chuyện thẩm mỹ. `Depends` chạy theo thứ tự khai báo: đặt
cổng cờ sau `require_login` thì một route "đã đóng" vẫn chuyển hướng về `/login`
— tức là vẫn xác nhận nó tồn tại, và vẫn bắt khách đăng nhập vào một thứ không mở.

**2. Trang nói thật.** Q103 chốt bán trên hạ tầng best-effort, không IP riêng.
Ba câu cảnh báo trên trang là **điều kiện của quyết định đó**, không phải trang
trí — khách phải đọc được trước khi trả tiền. Test giữ chúng khỏi bị ai dọn đi.
"""
from __future__ import annotations

import inspect
import re

import pytest


# ── 1. Cấu trúc: cờ đóng được cửa, và đóng đúng chỗ ─────────────────────────

def _handlers():
    from apps.vps import routes
    return [obj for ten, obj in vars(routes).items()
            if inspect.isfunction(obj) and not ten.startswith("_")
            and obj.__module__ == routes.__name__]


def test_moi_handler_deu_co_cong_co():
    from apps.vps.routes import _cong_co

    hs = _handlers()
    assert hs, "khong tim thay handler nao — test nay da mat tac dung"

    thieu = []
    for fn in hs:
        deps = [p.default.dependency for p in inspect.signature(fn).parameters.values()
                if hasattr(p.default, "dependency")]
        if _cong_co in deps:
            continue
        # Handler WebSocket không dùng được `Depends(_cong_co)`: chuỗi phụ thuộc
        # của FastAPI cho WebSocket không chạy giống HTTP, và `HTTPException`
        # ném trong ngữ cảnh đó không thành 404 mà thành một lỗi khác. Chúng
        # kiểm cờ TƯỜNG MINH trong thân hàm — nên test đo đúng cái đó, thay vì
        # đo hình thức chữ ký rồi bỏ sót ý định.
        nguon = inspect.getsource(fn)
        if inspect.iscoroutinefunction(fn) and "vps_app.enabled()" in nguon:
            assert "close(code=1008)" in nguon, (
                f"{fn.__name__}: co kiem co nhung khong dong ket noi")
            continue
        thieu.append(fn.__name__)
    assert thieu == [], f"handler khong co cong co: {thieu}"


def test_cong_co_dung_TRUOC_require_login():
    """Đặt sau thì route 'đã đóng' vẫn 303 về /login — vẫn xác nhận nó tồn tại."""
    from apps.vps.routes import _cong_co
    from server.auth.session import require_login

    sai = []
    for fn in _handlers():
        thu_tu = [p.default.dependency
                  for p in inspect.signature(fn).parameters.values()
                  if hasattr(p.default, "dependency")]
        if _cong_co in thu_tu and require_login in thu_tu:
            if thu_tu.index(_cong_co) > thu_tu.index(require_login):
                sai.append(fn.__name__)
    assert sai == [], f"cong co dat SAU require_login: {sai}"


def test_mount_all_van_khong_nhin_manifest_enabled():
    """Nếu nền tảng đổi hành vi, test này đỏ và ta xem lại — chứ không tự tin nhầm."""
    from platform_core import registry
    assert "item.manifest.enabled" not in inspect.getsource(registry.mount_all)


# ── 2. Bề mặt thật ──────────────────────────────────────────────────────────

@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'vps-ui.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vps-ui")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models   # noqa: F401
    import apps.vps.tables        # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield dbmod
    dbmod.reset_engine()


def _tao_khach(dbmod, credit_ban_dau=10_000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="vps-ui@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, credit_ban_dau)
        db.commit()
        return u.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _client():
    from fastapi.testclient import TestClient
    from server.app import create_app
    return TestClient(create_app(), base_url="https://testserver",
                      follow_redirects=False)


def _dang_nhap(client):
    login = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
    client.post("/login", data={"username": "vps-ui@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": token})


def test_co_tat_thi_URL_go_thang_tra_404(moi_truong, monkeypatch):
    """404 chứ không 403: 403 xác nhận bề mặt này có thật."""
    monkeypatch.delenv("LTT_VPS", raising=False)
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        assert client.get("/vps").status_code == 404
        assert client.post("/vps/tao", data={}).status_code == 404
    finally:
        client.close()


def test_co_bat_thi_trang_mo_va_NOI_THAT_ve_han_che(moi_truong, monkeypatch):
    monkeypatch.setenv("LTT_VPS", "1")
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        r = client.get("/vps")
        assert r.status_code == 200

        # Bốn câu này là điều kiện của Q103, không phải trang trí. Câu về IP
        # đã ĐỔI ngày 24/08: từ khi mỗi máy có một IP công khai riêng, câu cũ
        # ("bạn nhận cổng, không nhận IP") thành SAI — và một dòng cảnh báo sai
        # còn tệ hơn không có, vì khách tin nó.
        assert "best effort" in r.text
        assert "địa chỉ IP riêng" in r.text
        assert "Băng thông có hạn mức" in r.text, (
            "phai cong bo han muc bang thong: 2.048 GB/thang chia cho TAT CA "
            "khach, mot nguoi tai phim ca thang an het quota cua 15 nguoi kia")
        assert "hạn mức trên kho lưu trữ dùng chung" in r.text
        # 24/08: câu này cũng ĐỔI. Bản cũ hứa "sao lưu", nhưng thứ hạ tầng làm
        # được là **ảnh chụp**, và nó nằm trên cùng kho với đĩa gốc — pool hỏng
        # là mất cả hai. Hứa "sao lưu" rồi giao một ảnh chụp là loại lời hứa
        # người ta chỉ phát hiện sai đúng vào lúc mất dữ liệu.
        assert "Ảnh chụp hằng tuần" in r.text
        assert "KHÔNG thay thế bản sao lưu" in r.text, (
            "phai noi ro anh chup khong phai ban sao luu")

        # Bảng giá phải khớp `cost.py`, không phải một con số gõ tay trong template.
        from apps.vps.cost import PLANS
        for p in PLANS:
            assert p.ten in r.text
    finally:
        client.close()


def test_khong_doc_duoc_suc_chua_thi_KHONG_cho_tao_may(moi_truong, monkeypatch):
    """Fail-closed: chưa cấu hình Proxmox thì không được bán, và phải nói vì sao."""
    monkeypatch.setenv("LTT_VPS", "1")
    for k in ("LTT_VPS_PROXMOX_URL", "LTT_VPS_PROXMOX_TOKEN_ID",
              "LTT_VPS_PROXMOX_TOKEN_SECRET"):
        monkeypatch.delenv(k, raising=False)
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        r = client.get("/vps")
        assert "Hiện chưa nhận máy mới" in r.text
        assert 'action="/vps/tao"' not in r.text
    finally:
        client.close()


def _gia_lap_proxmox(monkeypatch, *, ram_gb=64, dia_gb=600, vms=None,
                     dia_dung_gb=0):
    """Giả một cụm Proxmox rảnh, để kiểm luồng tạo máy mà không cần cụm thật.

    `vms` mặc định rỗng = node chưa có máy nào. Cụm thật thì **không** như vậy —
    node đo ngày 2026-08-22 đã có 8 máy của chủ nhà — nên phép kiểm xếp chỗ phải
    đọc danh sách VM của Proxmox, không chỉ đọc CSDL của app.
    """
    class _Client:
        def trang_thai_node(self):
            return {"memory": {"total": ram_gb * 1024 ** 3}, "cpuinfo": {"cpus": 20}}

        def kho_luu_tru(self):
            return [{"storage": "local-lvm", "content": "images,rootdir",
                     "total": dia_gb * 1024 ** 3,
                     "used": dia_dung_gb * 1024 ** 3}]

        def danh_sach_vm(self):
            return list(vms or [])

    import apps.vps.routes as routes
    monkeypatch.setattr(routes, "client_tu_moi_truong", lambda *a, **k: _Client())
    from types import SimpleNamespace
    monkeypatch.setattr(routes.backend_factory, "compute_backend", lambda profile:
                        SimpleNamespace(client=_Client()))


def _tao_profile_healthy(db):
    from datetime import datetime, timezone
    from apps.vps.profiles import OVH_PROFILE_ID, REQUIRED_HEALTH_COMPONENTS
    from apps.vps.tables import VpsInfrastructureProfile, VpsProfileHealth

    profile = VpsInfrastructureProfile(
        id=OVH_PROFILE_ID, slug="ovh-sgp-prod", name="OVH-SGP-PROD",
        region="port", environment="production", status="ACTIVE",
        accept_new=True, is_default=True, compute_backend_type="proxmox",
        public_ip_backend_type="ovh_static_pool", gateway_backend_type="nft",
        credential_ref="LTT_OVH",
    )
    db.add(profile)
    now = datetime.now(timezone.utc)
    for component in REQUIRED_HEALTH_COMPONENTS:
        db.add(VpsProfileHealth(
            infrastructure_profile_id=profile.id, component=component,
            status="HEALTHY", observed_at=now, generated_at=now))
    db.flush()
    return profile


def test_node_da_day_vi_MAY_CUA_CHU_NHA_thi_khong_moi_khach_tao(moi_truong,
                                                                monkeypatch):
    """Node thật có sẵn 8 máy của chủ nhà chiếm gần hết RAM.

    Trang phải nói "hết chỗ" chứ không mời khách bấm Thuê — bán ở đó là bán chỗ
    của chính mình, và khách trả tiền cho một máy không bao giờ khởi động nổi.
    """
    monkeypatch.setenv("LTT_VPS", "1")
    # Đúng trạng thái node ngày 2026-08-22: 8 máy, VM100 chiếm 7,9 GB.
    day = [{"vmid": 100 + i, "maxmem": 4 * 1024 ** 3, "maxdisk": 80 * 1024 ** 3}
           for i in range(8)]
    day[0]["maxmem"] = 8 * 1024 ** 3
    _gia_lap_proxmox(monkeypatch, ram_gb=43, dia_gb=475, vms=day,
                     dia_dung_gb=174)
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        r = client.get("/vps")
        assert r.status_code == 200
        # RAM còn ~2 GB: chỉ gói nhỏ nhất còn chỗ, hai gói lớn phải báo hết.
        #
        # Kiểm TÍNH CHẤT, không kiểm nguyên văn: câu chữ đã đổi một lần
        # ("hết chỗ" -> "Hết chỗ cho cấu hình này.") và sẽ còn đổi.
        assert "Hết chỗ" in r.text, "trang khong bao goi nao het cho"
        # W1 (25/08): hết chỗ thì phải NÓI ĐI ĐÂU. Trước đó trang dừng ở hai
        # chữ "hết chỗ" và bỏ khách giữa luồng mua — ở đây gói nhỏ VẪN còn
        # chỗ, nên thẻ hết chỗ bắt buộc phải chỉ sang nó.
        assert "Còn chỗ:" in r.text, (
            "the 'het cho' khong chi sang goi con lai")
        assert r.text.count('action="/vps/tao"') == 1
    finally:
        client.close()


def test_to_hop_khong_boot_duoc_bi_tu_choi_TRUOC_khi_thu_tien(moi_truong,
                                                              monkeypatch):
    """Bản có giao diện trên gói 2 GB RAM không cài nổi. Không được thu tiền rồi
    mới biết.

    Trước 24/08 test này dùng Windows 11 trên gói 60 GB. Bỏ Windows 11 khỏi danh
    mục làm nó vẫn ĐỎ-hoá-xanh nhầm chỗ: lỗi trả về thành "khong co he dieu hanh
    'win11'" — vẫn là một lời từ chối, nhưng từ chối vì **mã OS không tồn tại**,
    không phải vì phép kiểm cấu hình. Nó sẽ xanh kể cả khi `hop_le()` bị gỡ hẳn.
    Nên nay dùng một tổ hợp CÓ THẬT nhưng không đủ RAM."""
    monkeypatch.setenv("LTT_VPS", "1")
    _gia_lap_proxmox(monkeypatch)
    user_id = _tao_khach(moi_truong)

    client = _client()
    try:
        _dang_nhap(client)
        page = client.get("/vps")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        r = client.post("/vps/tao", data={
            "csrf_token": token, "plan_id": "vps-nho",
            "os_id": "winsrv2022-gui", "vung": "sgp", "dia_them_gb": 0})
        assert r.status_code == 303
        assert "RAM" in r.headers["location"]
    finally:
        client.close()

    # Không có máy nào được tạo, và không mất credit nào.
    from platform_core import credit
    from apps.vps.tables import VpsInstance
    gen = moi_truong.get_session()
    db = next(gen)
    try:
        assert db.query(VpsInstance).count() == 0
        assert credit.so_du(db, user_id) == 10_000
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_khong_co_cong_vao_thi_tu_choi_chu_khong_tao_may_mo_coi(moi_truong,
                                                                monkeypatch):
    """Chưa nạp `vps_gateway` thì không có đường nào cho khách vào — phải từ chối.

    Tạo máy rồi mới phát hiện không có cổng nghĩa là một VM chạy trên đĩa mà
    không ai vào được: tốn chỗ trong cái kho vốn là nút thắt, và khách trả tiền
    cho một thứ không dùng được.
    """
    monkeypatch.setenv("LTT_VPS", "1")
    _gia_lap_proxmox(monkeypatch)
    user_id = _tao_khach(moi_truong)

    client = _client()
    try:
        _dang_nhap(client)
        page = client.get("/vps")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        r = client.post("/vps/tao", data={
            "csrf_token": token, "plan_id": "vps-vua",
            "os_id": "winsrv2022-gui", "vung": "port", "dia_them_gb": 0})
        assert r.status_code == 303
        assert "loi=" in r.headers["location"]
    finally:
        client.close()

    from platform_core import credit
    from apps.vps.tables import VpsInstance
    gen = moi_truong.get_session()
    db = next(gen)
    try:
        assert db.query(VpsInstance).count() == 0
        assert credit.so_du(db, user_id) == 10_000
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_tao_may_thanh_cong_thu_tien_va_NOP_JOB_chu_khong_cham_proxmox(
        moi_truong, monkeypatch):
    """Cloudflare cắt request ở 100 giây; clone + sysprep mất vài phút tới hơn mười.

    Làm đồng bộ thì khách nhận 524 trong khi một máy vẫn đang được tạo phía sau,
    và không ai biết nó tồn tại. Nên request này chỉ được ghi CSDL + nộp job.
    """
    monkeypatch.setenv("LTT_VPS", "1")
    _gia_lap_proxmox(monkeypatch)
    user_id = _tao_khach(moi_truong)

    from apps.vps.tables import VpsGateway, VpsIp
    gen = moi_truong.get_session()
    db = next(gen)
    try:
        profile = _tao_profile_healthy(db)
        gateway = VpsGateway(ten="cong-chinh", vung="port",
                          infrastructure_profile_id=profile.id,
                          ip_cong_khai="203.0.113.10",
                          ten_mien="vps.example.com",
                          bridge="vmbr1", subnet_cidr="10.51.0.0/24",
                          subnet_gw="10.51.0.1", dns="1.1.1.1", mtu=1420,
                          octet_dau=10, octet_cuoi=100,
                          cho_phep_ip_rieng=True)
        db.add(gateway)
        db.flush()
        db.add(VpsIp(gateway_id=gateway.id, infrastructure_profile_id=profile.id,
                     dia_chi="192.0.2.60", state="FREE"))
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    client = _client()
    try:
        _dang_nhap(client)
        page = client.get("/vps")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        r = client.post("/vps/tao", data={
            "csrf_token": token, "plan_id": "vps-vua",
            "os_id": "winsrv2022-gui", "vung": "port", "dia_them_gb": 0,
            # Extra form fields are attacker-controlled and must never override
            # the server-side selector.
            "profile_id": "attacker-profile", "provider": "vultr"})
        assert r.status_code == 303
        assert r.headers["location"] == "/vps"
    finally:
        client.close()

    from platform_core import credit
    from platform_core.models import Job
    from apps.vps.tables import VpsInstance
    gen = moi_truong.get_session()
    db = next(gen)
    try:
        may = db.query(VpsInstance).one()
        assert may.trang_thai == "dang_tao"
        assert may.paid_until is not None
        assert may.vmid is None            # chưa chạm Proxmox trong request
        assert may.infrastructure_profile_id == profile.id
        assert may.profile_resolution_state == "PINNED"
        assert credit.so_du(db, user_id) == 10_000 - 1790

        job = db.query(Job).filter_by(job_type="vps.provision").one()
        assert job.params["instance_id"] == may.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Thuộc tính template phải CÓ THẬT ────────────────────────────────────────
#
# Jinja in một thuộc tính không tồn tại thành **chuỗi rỗng**, không báo lỗi. Nên
# lỗi loại này không hiện ra dưới dạng lỗi mà dưới dạng một câu cụt trên trang —
# và nó sống tới khi có người đọc kỹ. Đã dính thật 24/08: template gọi
# `suc_chua.dia_gb_con` (không có) nên khách thấy "44.5 GB RAM · GB đĩa".
#
# Test này không render trang; nó đọc template như văn bản và đối chiếu từng
# `<biến>.<thuộc tính>` với lớp thật. Rẻ, và bắt được cả những nhánh mà một lần
# render không đi qua.

import re as _re
from pathlib import Path as _Path


def _thuoc_tinh_trong(tep: str, bien: str) -> set[str]:
    van_ban = _Path("server/templates") / tep
    return set(_re.findall(rf"\b{bien}\.([a-zA-Z_][a-zA-Z0-9_]*)",
                           van_ban.read_text(encoding="utf-8")))


def test_moi_thuoc_tinh_suc_chua_trong_template_deu_co_that():
    from apps.vps.services.capacity import SucChua

    dung = _thuoc_tinh_trong("vps.html", "suc_chua")
    thieu = sorted(x for x in dung if not hasattr(SucChua, x))
    assert not thieu, f"vps.html goi thuoc tinh khong co tren SucChua: {thieu}"
    assert dung, "test nay chi co nghia khi template that su dung suc_chua"


def test_moi_thuoc_tinh_may_trong_template_deu_co_that():
    from apps.vps.tables import VpsInstance

    for tep in ("vps_chi_tiet.html", "vps_console.html"):
        dung = _thuoc_tinh_trong(tep, "may")
        thieu = sorted(x for x in dung if not hasattr(VpsInstance, x))
        assert not thieu, f"{tep} goi thuoc tinh khong co tren VpsInstance: {thieu}"


def test_moi_thuoc_tinh_plan_va_os_trong_template_deu_co_that():
    from apps.vps.cost import Plan
    from apps.vps.os_images import OsImage

    for tep in ("vps.html", "vps_chi_tiet.html"):
        for bien, lop in (("plan", Plan), ("os", OsImage)):
            dung = _thuoc_tinh_trong(tep, bien)
            thieu = sorted(x for x in dung
                           if not hasattr(lop, x) and x not in lop.__annotations__)
            assert not thieu, f"{tep}: {bien}.{thieu} khong co tren {lop.__name__}"


# ─────────────────────────────────────────────────────────────────────────────
# Trang bán công khai (25/08)
#
# Q124/D01 + D09 thay quyết định storefront cũ: VPS là web-only owner MVP,
# authenticated-only. Catalog công khai không còn dẫn người lạ vào bề mặt này.
# ─────────────────────────────────────────────────────────────────────────────

def test_khach_AN_DANH_bi_chuyen_toi_dang_nhap(moi_truong, monkeypatch):
    monkeypatch.setenv("LTT_VPS", "1")
    client = _client()
    try:
        r = client.get("/vps")          # KHÔNG đăng nhập
        assert r.status_code == 303
        assert r.headers["location"].startswith("/login?next=")
        assert "149.000" not in r.text
    finally:
        client.close()


def test_khach_AN_DANH_khong_thay_bieu_mau_va_khong_thay_may_cua_ai(
        moi_truong, monkeypatch):
    """Biểu mẫu cho khách ẩn danh = một cái nút dẫn tới lỗi 401.

    Và `_may_cua_toi(db, "")` sẽ quét cả bảng — nên nhánh ẩn danh phải KHÔNG gọi
    nó, chứ không phải gọi rồi lọc.
    """
    monkeypatch.setenv("LTT_VPS", "1")
    _tao_khach(moi_truong)
    client = _client()
    try:
        r = client.get("/vps")
        assert r.status_code == 303
        assert 'action="/vps/tao"' not in r.text
        assert "Máy của tôi" not in r.text
        # Cổng cờ vẫn đứng trước cổng đăng nhập.
        monkeypatch.delenv("LTT_VPS", raising=False)
        assert client.get("/vps").status_code == 404
    finally:
        client.close()


def test_khach_DA_DANG_NHAP_thay_bieu_mau_chu_khong_thay_loi_moi_dang_nhap(
        moi_truong, monkeypatch):
    monkeypatch.setenv("LTT_VPS", "1")
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        r = client.get("/vps")
        assert r.status_code == 200
        assert "Đăng nhập để thuê máy" not in r.text, (
            "moi nguoi da dang nhap di dang nhap lan nua")
        assert "Tạo tài khoản" not in r.text
        # KHÔNG chốt sự tồn tại của biểu mẫu ở đây: môi trường test không nối
        # được tới Proxmox nên `suc_chua` là None, và fail-closed đúng nghĩa là
        # không dựng biểu mẫu. `test_khong_doc_duoc_suc_chua_thi_KHONG_cho_tao_may`
        # mới là chỗ chốt điều đó. Ở đây chỉ chốt: bảng giá vẫn hiện.
        assert "149.000" in r.text
    finally:
        client.close()


def test_app_TAT_khong_lot_vao_trang_chu_cua_nguoi_da_dang_nhap(moi_truong,
                                                                monkeypatch):
    """Ba nơi liệt kê app phải nói GIỐNG NHAU.

    `server/templating.py` (thanh bên + header) lọc `manifest.enabled`; nhánh ẩn
    danh của `dashboard.py` cũng lọc. Nhánh **đã đăng nhập** thì không — nên một
    app đang tắt cờ vẫn hiện thẻ, và route của nó trả 404. Bấm vào là ngõ cụt.

    Đo được ngày 25/08 với chính app `vps`. Lỗi có sẵn từ trước, không phải do
    `public=True`: nhánh đó trả `authenticated or public`, nên `public=False`
    cũng lọt y hệt.

    🔴 **Vì sao ép thẳng `MANIFEST.enabled` chứ không chỉ xoá biến môi trường.**

    `MANIFEST.enabled` được tính **một lần lúc nạp module** (`manifest.py` gọi
    `vps_app.enabled()` ở mức module). Nên xoá biến môi trường chỉ có tác dụng
    khi `apps.vps.manifest` **chưa** từng được nạp trong tiến trình này. Dưới
    `pytest -n`, một test khác trong cùng worker đặt `LTT_VPS=1` rồi nạp manifest
    là ca này đỏ — và nó đỏ vì **thứ tự nạp**, không vì sản phẩm sai.

    Đo được 09/09: ca này xanh khi chạy riêng và khi chạy cùng vài tệp, nhưng đỏ
    trong một lượt rộng hơn — cùng một mã sản phẩm, khác mỗi cách chia việc cho
    worker. Một phép kiểm đổi kết quả theo thứ tự nạp thì nó **không đo** thứ nó
    khai là đo.

    ⇒ Xoá biến môi trường (cho tiền đề 404, vì route đọc cờ **sống**) VÀ ép cờ
      trong manifest (cho mệnh đề thật: nhánh đã-đăng-nhập có lọc `enabled`
      không). Hai lớp, hai câu hỏi khác nhau.
    """
    from apps.vps.manifest import MANIFEST

    monkeypatch.delenv("LTT_VPS", raising=False)
    # `AppManifest` là `frozen=True`, nên `setattr` trên **thể hiện** bị chặn.
    # Đặt một `property` trên LỚP thì đi qua được (property là data descriptor,
    # ưu tiên hơn `__dict__` của thể hiện), và chỉ chạm đúng app `vps` — các app
    # khác vẫn khai đúng cờ của chúng, để ca này không vô tình tắt cả catalog.
    monkeypatch.setattr(
        type(MANIFEST), "enabled",
        # App khác đọc thẳng giá trị đã lưu trong `__dict__` — `frozen=True` cất
        # ở đó — nên chúng vẫn khai đúng cờ của chính mình.
        property(lambda self: False if self.slug == "vps"
                 else self.__dict__.get("enabled", True)),
        raising=False)
    _tao_khach(moi_truong)
    client = _client()
    try:
        assert client.get("/vps").status_code == 404, "tien de: route phai 404"
        assert "LTT VPS" not in client.get("/").text, "the app lot khi chua dang nhap"
        _dang_nhap(client)
        assert "LTT VPS" not in client.get("/").text, (
            "app tat van hien the cho nguoi da dang nhap -> bam vao la 404")
    finally:
        client.close()
