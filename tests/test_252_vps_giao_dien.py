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
        if _cong_co not in deps:
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

        # Ba câu này là điều kiện của Q103 (V1/V2/V3), không phải trang trí.
        assert "best effort" in r.text
        assert "không phải một địa chỉ IP riêng" in r.text
        assert "Sao lưu hằng tuần" in r.text

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
            return {"memory": {"total": ram_gb * 1024 ** 3}}

        def kho_luu_tru(self):
            return [{"storage": "local-lvm", "content": "images,rootdir",
                     "total": dia_gb * 1024 ** 3,
                     "used": dia_dung_gb * 1024 ** 3}]

        def danh_sach_vm(self):
            return list(vms or [])

    import apps.vps.routes as routes
    monkeypatch.setattr(routes, "client_tu_moi_truong", lambda *a, **k: _Client())


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
        assert "hết chỗ" in r.text
        assert r.text.count('action="/vps/tao"') == 1
    finally:
        client.close()


def test_to_hop_khong_boot_duoc_bi_tu_choi_TRUOC_khi_thu_tien(moi_truong,
                                                              monkeypatch):
    """Windows 11 trên gói 60 GB không boot. Không được thu tiền rồi mới biết."""
    monkeypatch.setenv("LTT_VPS", "1")
    _gia_lap_proxmox(monkeypatch)
    user_id = _tao_khach(moi_truong)

    client = _client()
    try:
        _dang_nhap(client)
        page = client.get("/vps")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        r = client.post("/vps/tao", data={
            "csrf_token": token, "plan_id": "vps-vua", "os_id": "win11",
            "vung": "port", "dia_them_gb": 0})
        assert r.status_code == 303
        assert "64" in r.headers["location"]
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

    from apps.vps.tables import VpsGateway
    gen = moi_truong.get_session()
    db = next(gen)
    try:
        db.add(VpsGateway(ten="cong-chinh", vung="port",
                          ip_cong_khai="203.0.113.10",
                          ten_mien="vps.example.com",
                          cong_dau=31000, cong_cuoi=31100))
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
            "os_id": "winsrv2022-gui", "vung": "port", "dia_them_gb": 0})
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
        assert credit.so_du(db, user_id) == 10_000 - 1790

        job = db.query(Job).filter_by(job_type="vps.provision").one()
        assert job.params["instance_id"] == may.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
