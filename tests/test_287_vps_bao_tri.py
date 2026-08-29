"""H39/G4 — việc nền định kỳ: thu tiền, treo, xoá.

Bộ test này tồn tại vì một lý do cụ thể: `services/billing.py` đã có đủ hàm kèm
test từ 23/08, nhưng cho tới 24/08 **không nơi nào gọi chúng**. Test đơn vị chứng
minh hàm đúng; nó không chứng minh có ai chạy hàm.

Nên ở đây kiểm ba tầng, và tầng thứ ba là tầng đã để lọt:

1. một lượt bảo trì làm đúng ba việc (thu → treo → nộp job xoá);
2. treo **thật sự tắt máy**, không chỉ đổi một cột trong CSDL;
3. **hợp đồng có khai, và nền tảng có gọi** — nối dây, không phải logic.
"""
from __future__ import annotations

import pathlib
from datetime import datetime, timedelta, timezone

import pytest

from apps.vps import bao_tri

GOC = pathlib.Path(__file__).resolve().parents[1]


class _ClientGia:
    def __init__(self, hong: bool = False):
        self.hong = hong
        self.da_tat: list[int] = []

    def tat_cung(self, vmid):
        if self.hong:
            from apps.vps.services.proxmox import ProxmoxError
            raise ProxmoxError("Proxmox tra 500", status=500)
        self.da_tat.append(int(vmid))
        return "UPID:pve:tat"


class _May:
    def __init__(self, id="may-1", trang_thai="dang_chay", vmid=200,
                 paid_until=None, xoa_sau=None, user_id="u1"):
        self.id = id
        self.user_id = user_id
        self.trang_thai = trang_thai
        self.vmid = vmid
        self.paid_until = paid_until
        self.xoa_sau = xoa_sau
        self.ly_do = ""
        self.plan_id = "vps-nho"
        self.dia_them_gb = 0


class _DbGia:
    """CSDL giả. `execute` trả danh sách rỗng: test ở đây kiểm ĐIỀU PHỐI, còn
    phần đo băng thông có bộ test riêng (`test_288`)."""

    def __init__(self, may=()):
        self.da_commit = 0
        self._may = list(may)

    def execute(self, *a, **kw):
        class _Kq:
            """Đóng vai kết quả của SQLAlchemy cho cả `select` lẫn `delete`."""

            rowcount = 0

            def __init__(self, x):
                self._x = x

            def scalars(self):
                return self

            def __iter__(self):
                return iter(self._x)

        return _Kq(self._may)

    def add(self, x):
        pass

    def flush(self):
        pass

    def commit(self):
        self.da_commit += 1

    def delete(self, x):
        pass


NOW = datetime(2026, 8, 24, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _chan_ghi_su_kien(monkeypatch):
    from apps.vps.services import provisioning
    monkeypatch.setattr(provisioning, "ghi_su_kien",
                        lambda db, iid, loai, **kw: None)
    from apps.vps.services import billing, dieu_khien
    monkeypatch.setattr(billing, "ghi_su_kien", lambda db, iid, loai, **kw: None)
    monkeypatch.setattr(dieu_khien.provisioning, "ghi_su_kien",
                        lambda db, iid, loai, **kw: None)


def _dung_billing(monkeypatch, *, den_han_thu=(), den_han_xoa=(), thieu_tien=False):
    """Thay hai truy vấn CSDL bằng danh sách cho sẵn — test này kiểm ĐIỀU PHỐI,
    không kiểm SQL (đã có `test_251` cho phần đó)."""
    from apps.vps.services import billing

    monkeypatch.setattr(billing, "den_han_thu",
                        lambda db, now=None: list(den_han_thu))
    monkeypatch.setattr(billing, "den_han_xoa",
                        lambda db, now=None: list(den_han_xoa))

    def thu(db, may, now=None):
        if thieu_tien:
            raise billing.ThieuCreditError("Khong du credit")
        may.paid_until = (now or NOW) + timedelta(days=30)

    monkeypatch.setattr(billing, "thu_mot_chu_ky", thu)


# ── 1. Một lượt làm đúng ba việc ────────────────────────────────────────────

def test_thu_duoc_thi_khong_treo_va_khong_xoa(monkeypatch):
    _dung_billing(monkeypatch, den_han_thu=[_May()])
    monkeypatch.setattr(bao_tri, "_client_hoac_none", lambda: _ClientGia())
    kq = bao_tri.mot_luot(_DbGia(), now=NOW)
    # So theo TAP KHOA thay vi so bang nhau: mot lượt bảo trì làm nhiều việc, và
    # thêm một việc mới không phải lý do để test về "thu tiền" báo đỏ.
    assert kq["da_thu"] == 1
    assert all(kq[k] == 0 for k in kq if k != "da_thu"), kq


def test_thieu_credit_thi_TREO_chu_khong_bo_qua(monkeypatch):
    """Bỏ qua một máy không trả được tiền nghĩa là cho dùng miễn phí vô hạn."""
    _dung_billing(monkeypatch, den_han_thu=[_May()], thieu_tien=True)
    monkeypatch.setattr(bao_tri, "_client_hoac_none", lambda: _ClientGia())
    m = _May()
    _dung_billing(monkeypatch, den_han_thu=[m], thieu_tien=True)
    kq = bao_tri.mot_luot(_DbGia(), now=NOW)
    assert kq["da_treo"] == 1
    assert m.trang_thai == "bi_treo"
    assert m.xoa_sau is not None, "phai dat han xoa, neu khong may nam lai mai"


# ── 2. Treo phải TẮT MÁY, không chỉ đổi một cột ─────────────────────────────

def test_treo_that_su_TAT_may(monkeypatch):
    """Đây là lỗ hổng của bản đầu: `billing.treo` chỉ ghi sổ, máy vẫn chạy trên
    Proxmox suốt 7 ngày ân hạn — khách hết tiền vẫn dùng bình thường, và RAM vẫn
    bị giữ."""
    m = _May(vmid=207)
    _dung_billing(monkeypatch, den_han_thu=[m], thieu_tien=True)
    c = _ClientGia()
    monkeypatch.setattr(bao_tri, "_client_hoac_none", lambda: c)
    bao_tri.mot_luot(_DbGia(), now=NOW)
    assert c.da_tat == [207], "treo ma khong tat may thi 'treo' chi la mot nhan"


def test_proxmox_hong_van_TREO_trong_so(monkeypatch):
    """Treo là quyết định về TIỀN. Proxmox hỏng không được cứu máy khỏi bị treo."""
    m = _May()
    _dung_billing(monkeypatch, den_han_thu=[m], thieu_tien=True)
    monkeypatch.setattr(bao_tri, "_client_hoac_none", lambda: _ClientGia(hong=True))
    kq = bao_tri.mot_luot(_DbGia(), now=NOW)
    assert kq["da_treo"] == 1 and m.trang_thai == "bi_treo"


def test_chua_cau_hinh_proxmox_van_thu_tien_binh_thuong(monkeypatch):
    """Không nối được Proxmox thì vẫn thu — nếu không, một cấu hình thiếu biến
    môi trường sẽ lặng lẽ biến mọi máy thành miễn phí."""
    m = _May()
    _dung_billing(monkeypatch, den_han_thu=[m], thieu_tien=True)
    monkeypatch.setattr(bao_tri, "_client_hoac_none", lambda: None)
    kq = bao_tri.mot_luot(_DbGia(), now=NOW)
    assert kq["da_treo"] == 1 and m.trang_thai == "bi_treo"


# ── 3. Xoá đi qua HÀNG ĐỢI, và không nộp trùng ──────────────────────────────

def test_may_qua_han_an_han_duoc_nop_job_xoa(monkeypatch):
    da_nop = []
    m = _May(trang_thai="bi_treo", xoa_sau=NOW - timedelta(days=1))
    _dung_billing(monkeypatch, den_han_xoa=[m])
    monkeypatch.setattr(bao_tri, "_client_hoac_none", lambda: _ClientGia())
    monkeypatch.setattr(bao_tri, "_nop_job_xoa",
                        lambda db, may: da_nop.append(may.id) or True)
    kq = bao_tri.mot_luot(_DbGia(), now=NOW)
    assert kq["da_nop_xoa"] == 1 and da_nop == [m.id]


def test_job_xoa_dung_dedupe_key_theo_MAY(monkeypatch):
    """Vòng chạy mỗi giờ. Không có `dedupe_key` thì một máy chờ xoá tích 24 job
    mỗi ngày, tất cả làm cùng một việc."""
    ghi = {}

    class _Q:
        @staticmethod
        def submit(db, **kw):
            ghi.update(kw)
            return object()

    # Vá **thuộc tính trên gói**, không phải `sys.modules`: `from platform_core
    # import jobs` đọc thuộc tính khi gói đã nạp, nên vá `sys.modules` chỉ ăn khi
    # test này chạy MỘT MÌNH — và xanh-khi-chạy-riêng, đỏ-khi-chạy-cả-bộ là loại
    # test tệ hơn không có.
    import platform_core

    monkeypatch.setattr(platform_core, "jobs", _Q, raising=False)
    bao_tri._nop_job_xoa(_DbGia(), _May(id="may-9", user_id="u7"))
    assert ghi["dedupe_key"] == "vps-destroy-may-9"
    assert ghi["job_type"] == "vps.destroy"
    assert ghi["user_id"] == "u7"
    assert ghi["params"]["instance_id"] == "may-9"


def test_KHONG_xoa_thang_trong_vong_bao_tri():
    """Xoá gọi ra Vultr và chờ tác vụ Proxmox. Làm thẳng ở đây thì một Vultr chậm
    giữ lease bảo trì của CẢ nền tảng, chặn luôn dọn job, quét cảnh báo, webhook."""
    import inspect

    nguon = inspect.getsource(bao_tri)
    assert "vps.destroy" in nguon
    for cam in ("client.xoa(", "_xoa_may", "tra_ip_cong_khai"):
        assert cam not in nguon, f"vong bao tri khong duoc goi {cam}"


# ── 4. Nối dây: hợp đồng khai, và nền tảng gọi ──────────────────────────────

def test_manifest_CO_khai_viec_dinh_ky():
    """Tầng đã để lọt: hàm đúng, test xanh, nhưng không ai gọi suốt một ngày."""
    from apps.vps.manifest import MANIFEST

    assert MANIFEST.bao_tri is bao_tri.chay
    assert 60 <= MANIFEST.bao_tri_moi_giay <= 24 * 3600


def test_app_tat_co_thi_KHONG_co_viec_bao_tri_nao(tmp_path):
    """Nua thu nhat: `apps/vps` co that su tat theo co `LTT_VPS` khong.

    🔴 CHAY TRONG TIEN TRINH RIENG, va do la ca noi dung cua phep kiem nay.

    `AppManifest.enabled` doc bien moi truong luc **NAP MODULE**. Ban truoc goi
    `monkeypatch.delenv("LTT_VPS")` roi goi thang `registry.viec_bao_tri()` —
    nhung neu mot test khac trong cung worker xdist da nap `apps/vps/manifest.py`
    khi co con dat, thi `MANIFEST.enabled` **da chot la True** va `delenv` khong
    thao duoc gi.

    Hau qua do duoc 29/08: gate do dung phep kiem nay mot luot, xanh luot sau,
    va khong tai hien duoc khi chay rieng hay chay cung sau tep VPS khac. No
    chan mot lan deploy. Cung lop loi voi hai lan khac cung ngay —
    `__pycache__` va mat phang claim GPU toan may (xem `BAY_TRONG_CONG_CHAT_LUONG.md`
    Bay 16): **trang thai NGOAI phep kiem ro VAO phep kiem**.

    ⛔ Dung sua bang `importlib.reload`: no de lai mot module da doi cho moi test
       chay sau, tuc doi mot ro ri lay mot ro ri khac.
    """
    import json
    import os
    import subprocess
    import sys

    # Mot dong, noi bang dau cham phay — de khong phai nhung ky tu xuong dong
    # vao mot chuoi Python nam trong mot tep Python.
    ma = ("import json; from platform_core import registry; "
          "print(json.dumps([s for s, _, _ in registry.viec_bao_tri()]))")
    moi_truong = {k: v for k, v in os.environ.items() if k != "LTT_VPS"}
    r = subprocess.run([sys.executable, "-c", ma], capture_output=True,
                       text=True, cwd=str(GOC), env=moi_truong, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "vps" not in json.loads(r.stdout.strip().splitlines()[-1]), r.stdout


def test_nen_tang_CHI_chay_viec_cua_app_DANG_BAT(monkeypatch):
    """Nua thu hai: nen tang co LOC theo `enabled` khong.

    Kiem thang ham loc bang manifest gia — khong phu thuoc thu tu import cua ca
    bo test. Nua thu nhat o phep kiem tren.
    """
    from platform_core import registry

    # `enabled` đọc cờ lúc NẠP module, nên ở đây kiểm thẳng hàm lọc thay vì
    # nạp lại toàn bộ app — cái sau phụ thuộc thứ tự import của cả bộ test.
    from platform_core.registry import AppManifest

    class _Item:
        def __init__(self, m):
            self.manifest = m

    tat = AppManifest(slug="x", display_name="x", route_prefix="/x",
                      bao_tri=lambda: None, enabled=False)
    bat = AppManifest(slug="y", display_name="y", route_prefix="/y",
                      bao_tri=lambda: None, enabled=True)
    ra = registry.viec_bao_tri([_Item(tat), _Item(bat)])
    assert [s for s, _, _ in ra] == ["y"]


def test_vong_bao_tri_cua_nen_tang_CO_goi_viec_cua_app():
    import inspect

    from platform_core import job_runner

    assert "_bao_tri_cac_app(moc)" in inspect.getsource(job_runner._mot_luot_bao_tri)


def test_mot_app_nem_KHONG_chan_app_khac(monkeypatch):
    """Vòng bảo trì là vòng gốc — không có ai ở trên để xử lý. Một app hỏng làm
    dừng cả vòng nghĩa là dọn job, cảnh báo và webhook cũng dừng theo."""
    from platform_core import job_runner, registry

    da_chay = []

    def no():
        raise RuntimeError("app nay hong")

    monkeypatch.setattr(registry, "viec_bao_tri",
                        lambda: [("hong", no, 3600),
                                 ("lanh", lambda: da_chay.append(1), 3600)])
    job_runner._bao_tri_cac_app({})
    assert da_chay == [1]


def test_app_nem_thi_van_phai_CHO_du_gian_cach(monkeypatch):
    """Đặt mốc trước khi chạy. Không thế thì một app ném sẽ bị gọi lại mỗi vòng
    poll, và log đầy cùng một stack trace."""
    from platform_core import job_runner, registry

    dem = []

    def no():
        dem.append(1)
        raise RuntimeError("hong")

    monkeypatch.setattr(registry, "viec_bao_tri", lambda: [("x", no, 3600)])
    moc: dict = {}
    job_runner._bao_tri_cac_app(moc)
    job_runner._bao_tri_cac_app(moc)
    assert dem == [1], "lan hai phai bi hoan lai vi chua den han"
