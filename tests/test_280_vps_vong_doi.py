"""H39/G3 — vòng đời máy: bật, tắt, khởi động lại, cài lại, xoá.

Phần lớn test ở đây kiểm **luật tiền**, không kiểm kỹ thuật:

* máy bị treo vì nợ mà khách tự bật lại được thì "treo" chỉ là một cái nút, tức
  là không treo gì cả — và khách dùng miễn phí cho tới khi ai đó để ý;
* máy của người này mà người kia điều khiển được thì không cần nói thêm;
* hai nút không hoàn tác được mà bấm nhầm được thì sớm muộn có người mất dữ liệu.
"""
from __future__ import annotations

import pytest

from apps.vps.services import dieu_khien
from apps.vps.services.proxmox import ProxmoxError


class _ClientGia:
    """Proxmox giả: ghi lại lệnh đã gọi, hoặc hỏng theo yêu cầu."""

    def __init__(self, hong: bool = False):
        self.hong = hong
        self.da_goi: list[tuple[str, int]] = []

    def _ghi(self, ten, vmid):
        if self.hong:
            raise ProxmoxError("Proxmox tra 500", status=500)
        self.da_goi.append((ten, int(vmid)))
        return f"UPID:pve:{ten}"

    def bat(self, vmid):
        return self._ghi("bat", vmid)

    def tat_mem(self, vmid):
        return self._ghi("tat_mem", vmid)

    def tat_cung(self, vmid):
        return self._ghi("tat_cung", vmid)


class _DbGia:
    """Đủ để `ghi_su_kien` và `commit` chạy mà không cần CSDL thật."""

    def __init__(self):
        self.su_kien: list[str] = []
        self.da_commit = 0

    def add(self, x):
        pass

    def flush(self):
        pass

    def commit(self):
        self.da_commit += 1


class _May:
    def __init__(self, trang_thai="dang_chay", vmid=200):
        self.id = "may-1"
        self.trang_thai = trang_thai
        self.vmid = vmid
        self.ly_do = ""
        self.paid_until = None
        self.xoa_sau = None


@pytest.fixture(autouse=True)
def _bat_su_kien(monkeypatch):
    """Chặn `ghi_su_kien` để không cần CSDL — nhưng vẫn ghi lại nó ĐƯỢC GỌI."""
    from apps.vps.services import provisioning
    ghi: list[str] = []

    def gia(db, instance_id, loai, **kw):
        ghi.append(loai)

    monkeypatch.setattr(provisioning, "ghi_su_kien", gia)
    monkeypatch.setattr(dieu_khien.provisioning, "ghi_su_kien", gia)
    return ghi


# ── 1. Luật tiền: máy bị treo thì khách KHÔNG tự bật lại ────────────────────

def test_may_bi_treo_thi_khach_KHONG_tu_bat_lai_duoc():
    """Nếu bật lại được thì 'treo' chỉ là một cái nút — tức không treo gì cả."""
    c = _ClientGia()
    with pytest.raises(dieu_khien.KhongDuocPhepError) as e:
        dieu_khien.bat(_DbGia(), _May(trang_thai="bi_treo"), c, boi="khach")
    assert "treo" in str(e.value).lower()
    assert c.da_goi == [], "khong duoc goi Proxmox"


def test_loi_treo_noi_ro_phai_lam_gi_de_dung_lai():
    """Câu này khách đọc, nên nó phải chỉ được đường ra chứ không chỉ báo lỗi."""
    with pytest.raises(dieu_khien.KhongDuocPhepError) as e:
        dieu_khien.kiem_dieu_khien_duoc(_May(trang_thai="bi_treo"))
    assert "credit" in str(e.value).lower()


def test_may_dang_tao_thi_khong_ai_duoc_dung_vao():
    """Bật/tắt giữa lúc job đang clone là cách chắc chắn để có máy hỏng nửa chừng."""
    c = _ClientGia()
    for tt in ("dang_tao", "da_xoa"):
        with pytest.raises(dieu_khien.KhongDuocPhepError):
            dieu_khien.tat(_DbGia(), _May(trang_thai=tt), c, boi="khach")
    assert c.da_goi == []


def test_may_chua_co_vmid_thi_tu_choi():
    with pytest.raises(dieu_khien.KhongDuocPhepError):
        dieu_khien.bat(_DbGia(), _May(vmid=None), _ClientGia(), boi="khach")


# ── 2. Ba thao tác thường ───────────────────────────────────────────────────

def test_bat_va_tat_goi_dung_lenh_va_doi_trang_thai():
    c, m, db = _ClientGia(), _May(trang_thai="da_tat"), _DbGia()
    dieu_khien.bat(db, m, c, boi="khach")
    assert c.da_goi == [("bat", 200)] and m.trang_thai == "dang_chay"

    dieu_khien.tat(db, m, c, boi="khach")
    assert c.da_goi[-1] == ("tat_mem", 200) and m.trang_thai == "da_tat"


def test_tat_MAC_DINH_la_tat_mem_chu_khong_rut_dien():
    """Rút điện giữa lúc Windows đang ghi đĩa là cách làm hỏng hệ tệp của khách."""
    c = _ClientGia()
    dieu_khien.tat(_DbGia(), _May(), c, boi="khach")
    assert c.da_goi == [("tat_mem", 200)]
    c2 = _ClientGia()
    dieu_khien.tat(_DbGia(), _May(), c2, boi="khach", cung=True)
    assert c2.da_goi == [("tat_cung", 200)]


def test_khoi_dong_lai_KHONG_dung_endpoint_reboot_cua_proxmox():
    """`reboot` của Proxmox chờ guest tự tắt và treo vô hạn nếu Windows đang hiện
    hộp thoại "có muốn lưu không". Ta tắt mềm, khách tự bật lại."""
    c = _ClientGia()
    dieu_khien.khoi_dong_lai(_DbGia(), _May(), c, boi="khach")
    assert c.da_goi == [("tat_mem", 200)]


# ── 3. Thất bại cũng phải để lại dấu ────────────────────────────────────────

def test_thao_tac_that_bai_van_duoc_ghi_nhat_ky(_bat_su_kien):
    """Khách hỏi "sao bấm mãi không được" thì phải có thứ để đọc."""
    m = _May()
    with pytest.raises(ProxmoxError):
        dieu_khien.bat(_DbGia(), m, _ClientGia(hong=True), boi="khach")
    assert any("that_bai" in x for x in _bat_su_kien)
    assert m.trang_thai == "dang_chay", "khong duoc doi trang thai khi lenh hong"


# ── 4. Treo: uỷ quyền phần ghi sổ cho `billing` ─────────────────────────────

def test_treo_UY_QUYEN_cho_billing_chu_khong_tu_ghi_so(monkeypatch):
    """Hai chỗ cùng quyết một việc thì sớm muộn lệch nhau: chỗ này đặt `xoa_sau`,
    chỗ kia quên, và máy của khách nằm lại vĩnh viễn hoặc bị xoá sớm bảy ngày."""
    from apps.vps.services import billing
    da_goi = []
    monkeypatch.setattr(billing, "treo",
                        lambda db, may, ly_do: da_goi.append(ly_do))
    monkeypatch.setattr(dieu_khien.billing, "treo",
                        lambda db, may, ly_do: da_goi.append(ly_do))
    c = _ClientGia()
    dieu_khien.treo(_DbGia(), _May(), c, ly_do="No tien")
    assert c.da_goi == [("tat_cung", 200)], "treo phai tat CUNG"
    assert da_goi == ["No tien"], "phan ghi so phai do billing lam"


def test_treo_van_ghi_so_ke_ca_khi_proxmox_khong_tat_duoc(monkeypatch):
    """Treo là quyết định về TIỀN. Proxmox hỏng không được phép cứu máy khỏi bị treo."""
    from apps.vps.services import billing
    da_goi = []
    monkeypatch.setattr(dieu_khien.billing, "treo",
                        lambda db, may, ly_do: da_goi.append(ly_do))
    dieu_khien.treo(_DbGia(), _May(), _ClientGia(hong=True), ly_do="No tien")
    assert da_goi == ["No tien"]


# ── 5. Đếm ngày còn hạn ─────────────────────────────────────────────────────

def test_con_bao_nhieu_ngay_khong_bao_gio_tra_so_am():
    """"Còn −2 ngày" không nói được gì cho người đọc."""
    from datetime import datetime, timedelta, timezone

    from apps.vps.services import billing

    now = datetime(2026, 8, 24, tzinfo=timezone.utc)
    m = _May()
    m.paid_until = now - timedelta(days=5)
    assert billing.con_bao_nhieu_ngay(m, now=now) == 0
    m.paid_until = now + timedelta(days=3, hours=12)
    assert billing.con_bao_nhieu_ngay(m, now=now) == 3
    m.paid_until = None
    assert billing.con_bao_nhieu_ngay(m, now=now) is None


def test_con_han_va_con_bao_nhieu_ngay_la_HAI_thu_khac_nhau():
    """`con_han` trả `bool`. Dùng nó cho cảnh báo "còn N ngày" thì `True <= 3`
    luôn đúng trong Python, và cảnh báo hiện cho MỌI máy — đã suýt dính 24/08."""
    from datetime import datetime, timedelta, timezone

    from apps.vps.services import billing

    now = datetime(2026, 8, 24, tzinfo=timezone.utc)
    m = _May()
    m.paid_until = now + timedelta(days=20)
    assert billing.con_han(m, now=now) is True
    assert billing.con_bao_nhieu_ngay(m, now=now) == 20


# ── 6. Máy khách chỉ được có MỘT card ───────────────────────────────────────

def test_go_het_card_thua_cua_template():
    """Template có sẵn `net1` thì máy khách thừa hưởng nó. Nếu card đó cắm
    `vmbr0` thì **máy bán cho khách có một chân trong LAN nhà**.

    Không lý thuyết: `WIN10-LTSC-GOLD` có `net1`, và máy thử 24/08 hiện ra hai
    card trong Windows ("Ethernet" và "Ethernet 2")."""
    from apps.vps import jobs

    class _C:
        class config:
            node = "pve"

        def _goi(self, method, duong_dan, **kw):
            return {"net0": "e1000,bridge=vmbr1", "net1": "e1000,bridge=vmbr0",
                    "net3": "e1000,bridge=vmbr0", "sata0": "x", "name": "y"}

    assert jobs._go_card_thua(_C(), 200) == {"delete": "net1,net3"}


def test_template_chi_co_mot_card_thi_khong_xoa_gi():
    from apps.vps import jobs

    class _C:
        class config:
            node = "pve"

        def _goi(self, method, duong_dan, **kw):
            return {"net0": "e1000,bridge=vmbr1", "sata0": "x"}

    assert jobs._go_card_thua(_C(), 200) == {}


# ── 7. Gỡ đĩa cài sau khi khách tự cài xong ─────────────────────────────────

class _ClientDia(_ClientGia):
    def __init__(self, hong: bool = False):
        super().__init__(hong)
        self.cau_hinh: dict = {}

    def dat_cau_hinh(self, vmid, **kw):
        if self.hong:
            raise ProxmoxError("Proxmox tra 500", status=500)
        self.da_goi.append(("dat_cau_hinh", int(vmid)))
        self.cau_hinh = kw


def test_go_dia_cai_thao_ide0_VA_doi_thu_tu_boot():
    """Thiếu vế nào cũng hỏng, và hỏng theo hai kiểu khác nhau:

    * chỉ `delete=ide0` mà giữ `boot=order=ide0;sata0` → máy còn nhớ một thiết bị
      không còn tồn tại, và BIOS mất thêm thời gian mỗi lần khởi động;
    * chỉ đổi `boot` mà giữ đĩa → vẫn hiện "Press any key to boot from CD", tức
      là chưa giải quyết đúng thứ nút này sinh ra để giải quyết.
    """
    c, m, db = _ClientDia(), _May(), _DbGia()
    dieu_khien.go_dia_cai(db, m, c, boi="khach")
    assert c.cau_hinh == {"delete": "ide0", "boot": "order=sata0"}
    assert db.da_commit == 1


def test_go_dia_cai_chay_lai_duoc():
    """Khách bấm hai lần là chuyện thường. Lần hai không được thành lỗi."""
    c, m, db = _ClientDia(), _May(), _DbGia()
    for _ in range(2):
        dieu_khien.go_dia_cai(db, m, c, boi="khach")
    assert c.cau_hinh == {"delete": "ide0", "boot": "order=sata0"}


def test_may_bi_treo_thi_khong_go_dia_duoc():
    """Cùng cổng quyền với bật/tắt: máy đang nợ tiền thì khách không đụng vào."""
    c = _ClientDia()
    with pytest.raises(dieu_khien.KhongDuocPhepError):
        dieu_khien.go_dia_cai(_DbGia(), _May(trang_thai="bi_treo"), c, boi="khach")
    assert c.da_goi == []


def test_may_dang_tao_thi_khong_go_dia_duoc():
    """Gỡ đĩa giữa lúc job đang dựng máy là rút nền dưới chân nó."""
    c = _ClientDia()
    with pytest.raises(dieu_khien.KhongDuocPhepError):
        dieu_khien.go_dia_cai(_DbGia(), _May(trang_thai="dang_tao"), c, boi="khach")
    assert c.da_goi == []
