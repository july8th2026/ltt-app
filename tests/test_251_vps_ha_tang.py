"""Hạ tầng app VPS (H39 P0, Q103 + Q104).

Bộ test này bám vào những chỗ mà sai sẽ **hỏng im lặng** — tức là loại hỏng không
làm test nào khác đỏ và không làm log nào đỏ, chỉ làm khách mất máy:

* **Fail-closed.** Cờ tắt mà app vẫn hiện là mở một bề mặt tạo máy ảo cho người lạ.
* **Cấu hình × hệ điều hành.** Bản Windows có giao diện trên gói 2 GB RAM **không
  cài nổi**. Nếu không chặn trước khi thu tiền thì khách phát hiện sau khi đã trả
  và đang nhìn một thông báo lỗi của trình cài đặt.
* **Cấp phát nguyên tử.** Hai job song song nhận cùng một cổng NAT thì máy sau ghi
  đè NAT của máy trước, và khách đầu tiên mất kết nối mà **không có lỗi nào**.
* **Xếp chỗ fail-closed.** Không đọc được dung lượng kho thì phải NGỪNG bán, không
  phải bán tiếp — kho đầy làm mọi VM hỏng một lượt, không chỉ máy gây đầy.
* **Tiền.** Trừ thiếu thì mất doanh thu; trừ thừa thì mất khách. `paid_until` phải
  cộng dồn từ mốc cũ, không phải từ hôm nay.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import apps.vps as vps_app
from apps.vps import cost, os_images
from apps.vps.services import capacity, proxmox


# ── fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'vps.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models   # noqa: F401
    import apps.vps.tables        # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def _gateway(db, *, octet_dau=10, octet_cuoi=12, vung="sgp",
             ip_rieng=True, ten="cong-vn"):
    from apps.vps.tables import VpsGateway
    g = VpsGateway(ten=ten, vung=vung, ip_cong_khai="203.0.113.10",
                   ten_mien="vps.example.com",
                   bridge="vmbr1", subnet_cidr="10.51.0.0/24",
                   subnet_gw="10.51.0.1", dns="1.1.1.1", mtu=1420,
                   octet_dau=octet_dau, octet_cuoi=octet_cuoi,
                   cho_phep_ip_rieng=ip_rieng)
    db.add(g)
    db.flush()
    return g


def _may(db, gateway, *, plan_id="vps-vua", os_id="winsrv2022-gui",
         user_id="u1", trang_thai="dang_tao", dia_them_gb=0):
    from apps.vps.tables import VpsInstance
    m = VpsInstance(user_id=user_id, plan_id=plan_id, os_id=os_id,
                    dia_them_gb=dia_them_gb, gateway_id=gateway.id,
                    trang_thai=trang_thai)
    db.add(m)
    db.flush()
    return m


# ── 1. Fail-closed ───────────────────────────────────────────────────────────

def test_co_tat_thi_app_tat():
    assert vps_app.enabled({}) is False
    assert vps_app.enabled({"LTT_VPS": ""}) is False
    assert vps_app.enabled({"LTT_VPS": "may"}) is False


def test_co_bat_bang_gia_tri_ro_rang():
    for gt in ("1", "true", "TRUE", "yes", "on"):
        assert vps_app.enabled({"LTT_VPS": gt}) is True


def test_manifest_khong_thu_theo_luot_job():
    """`credit_cost` phải trả 0, không phải None — xem `cost.py`.

    None nghĩa là "app chưa thu phí", sai hẳn: VPS thu theo chu kỳ 30 ngày. Và
    `tools/lint_app_contract.py` bắt buộc app khai `job_types` thì phải có
    `credit_cost`, nên None cũng làm gate đỏ.
    """
    from apps.vps.manifest import MANIFEST
    assert MANIFEST.credit_cost is not None
    assert MANIFEST.credit_cost({}) == 0
    assert MANIFEST.table_prefix == "vps"
    assert set(MANIFEST.job_types) == {"vps.provision", "vps.rebuild", "vps.destroy"}
    # Trần thời gian phải có: job treo mà vẫn đập nhịp sẽ giữ slot vô hạn.
    for jt in MANIFEST.job_types:
        assert MANIFEST.runtime_limit_for(jt) > 0


def test_moi_bang_deu_mang_tien_to_vps():
    import apps.vps.tables as t
    for cls in (t.VpsGateway, t.VpsInstance, t.VpsIp, t.VpsEvent):
        assert cls.__tablename__.startswith("vps_")


# ── 2. Bảng giá ──────────────────────────────────────────────────────────────

def test_khong_goi_nao_duoi_nguong_dia_cua_windows():
    """Bản nháp đầu từng có gói 25 GB. Windows tối thiểu 32 GB — không cài nổi."""
    for p in cost.PLANS:
        assert p.disk_gb >= 32, f"goi {p.id} khong cai noi Windows"


def test_gia_quy_ra_credit_theo_ti_gia_nen_tang():
    assert cost.credit_thang("vps-nho") == 1490       # 149.000d / 100
    assert cost.credit_thang("vps-vua") == 1790
    assert cost.credit_thang("vps-lon") == 3290


def test_goi_re_nhat_phai_tra_noi_tien_IP_rieng():
    """Mỗi máy nay kèm MỘT IP công khai riêng, giá vốn $3/tháng ≈ 78.000đ.

    Gói 89k cũ chỉ còn 11k sau tiền IP — không sống được. Test này là cái chốt
    để không ai hạ giá gói vào cửa xuống dưới mức trả nổi cái IP mà quên mất
    điều đó (V6 chốt 89k khi mô hình còn CHIA CỔNG, không còn đúng nữa).
    """
    GIA_VON_IP_VND = 78_000
    re_nhat = min(p.gia_thang_vnd for p in cost.PLANS)
    assert re_nhat >= GIA_VON_IP_VND * 1.8, (
        f"goi re nhat {re_nhat}d khong du bien tren gia von IP {GIA_VON_IP_VND}d")


def test_dia_mua_them_cong_dung_va_chi_nhan_boi_cua_10():
    assert cost.gia_thang_vnd("vps-vua", 20) == 179_000 + 2 * 25_000
    assert cost.dia_tong_gb("vps-vua", 20) == 60 + 20
    with pytest.raises(ValueError):
        cost.gia_thang_vnd("vps-vua", 7)
    with pytest.raises(ValueError):
        cost.gia_thang_vnd("vps-vua", -10)


# ── 3. Hệ điều hành × cấu hình ───────────────────────────────────────────────

def test_KHONG_ban_windows_11():
    """Chốt 2026-08-24: danh mục dừng ở Server 2016/2022 và Windows 10 LTSC.

    Windows 11 đòi UEFI/OVMF + vTPM + Secure Boot, tức một nhánh cấu hình máy
    **riêng** mà không bản nào khác đi qua — nhánh chỉ một thứ dùng là nhánh
    không lần chạy nào thử tới, và nó hỏng lặng lẽ. Nhánh đó đã gỡ khỏi
    `jobs.py`, nên thêm lại `win11` vào catalog mà quên dựng lại nhánh sẽ tạo ra
    máy BIOS thường, và khách ngồi nhìn "This PC can't run Windows 11".
    """
    assert os_images.lay_os("win11") is None
    assert "win11" not in {o.id for o in os_images.OS_IMAGES}


def test_phep_kiem_DIA_that_su_chay(monkeypatch):
    """`vps-nho` thiếu cả RAM lẫn đĩa, nên nó không chứng minh được phép kiểm đĩa
    có chạy hay không. Dựng một bản giả chỉ vượt ngưỡng ĐĨA để tách hai phép kiểm.
    """
    from apps.vps.os_images import OsImage

    to = OsImage(id="thu-dia-to", ten="Ban gia dia to", ho="windows",
                 ram_mb_toi_thieu=2048, disk_gb_toi_thieu=200,
                 cong_quen=3389, khach_thay=False)
    monkeypatch.setitem(os_images._THEO_ID, to.id, to)
    duoc, ly_do = os_images.hop_le("vps-vua", to.id)          # 4 GB RAM, 60 GB
    assert duoc is False
    assert "200" in ly_do and "dia" in ly_do
    # Mua thêm đĩa thì qua — chứng minh `dia_them_gb` thật sự vào phép tính.
    assert os_images.hop_le("vps-vua", to.id, 140)[0] is True


def test_moi_ban_ban_cho_khach_deu_chay_duoc_o_it_nhat_MOT_goi():
    """Một bản không gói nào chạy nổi thì nó chỉ là một dòng chết trong catalog —
    hiện ra ở đâu đó rồi bị từ chối ở đúng lúc khách bấm mua."""
    from apps.vps.cost import PLANS

    for img in os_images.os_ban_duoc():
        assert any(os_images.hop_le(p.id, img.id)[0] for p in PLANS),             f"{img.id} khong goi nao chay duoc"


def test_goi_nho_khong_chay_ban_co_giao_dien():
    duoc, ly_do = os_images.hop_le("vps-nho", "winsrv2022-gui")   # 2 GB RAM
    assert duoc is False
    assert "RAM" in ly_do


def test_catalog_CHI_con_Windows():
    """V9 chốt catalog chỉ Windows. Hai bản Linux nội bộ (`debian-12`,
    `ubuntu-24-04`) từng nằm đây để phục vụ đường nhân bản template — đường đó
    đã bị gỡ 24/08 sau khi ba template cuối bị xoá khỏi cụm, nên hai bản đó
    không còn cách nào tạo được máy.

    Một mục trong catalog mà mọi lần tạo đều ném lỗi là một cái bẫy, không phải
    một tuỳ chọn."""
    for cu_ky in ("ubuntu-24-04", "debian-12"):
        assert os_images.lay_os(cu_ky) is None, f"{cu_ky} van con trong catalog"
    assert {o.ho for o in os_images.OS_IMAGES} == {"windows"}
    assert all(o.khach_thay for o in os_images.OS_IMAGES)


def test_ten_bien_dia_cai_dat_doc_duoc_tu_ma_os():
    assert os_images.khoa_moi_truong("winsrv2022-gui") ==         "LTT_VPS_ISO_WINSRV2022_GUI"
    assert os_images.khoa_moi_truong("winsrv2016-core") == "LTT_VPS_ISO_WINSRV2016_CORE"
    assert os_images.dia_cai_dat("winsrv2016-gui", {}) == ""
    assert os_images.dia_cai_dat(
        "winsrv2016-gui",
        {"LTT_VPS_ISO_WINSRV2016_GUI": "local:iso/x.iso"}) == "local:iso/x.iso"


def test_chua_khai_dia_cai_dat_thi_KHONG_doan_bua():
    """Fail-closed: chua khai thi job tu choi tao may, thay vi tao mot may trong
    khong boot duoc roi de khach nhin man hinh den ma khong hieu vi sao."""
    assert os_images.dia_cai_dat("winsrv2022-gui", {}) == ""


def test_may_khach_chi_co_MOT_duong_BIOS():
    """Không còn nhánh `ovmf` + `efidisk0` + `tpmstate0`. Nhánh đó chỉ phục vụ
    Windows 11; giữ lại một nhánh không bản nào đi qua là nuôi mã không ai thử."""
    from apps.vps import cost, jobs

    ch = jobs._cau_hinh_may_trong(
        type("M", (), {"id": "550e8400-e29b-41d4-a716-000000000001",
                       "plan_id": "vps-vua", "dia_them_gb": 0})(),
        cost.lay_plan("vps-vua"), os_images.lay_os("winsrv2016-gui"),
        "local:iso/x.iso")
    assert ch["bios"] == "seabios"
    assert "efidisk0" not in ch and "tpmstate0" not in ch


def test_hai_ban_cua_cung_mot_doi_Server_dung_CHUNG_mot_dia_cai(monkeypatch):
    """Core và bản có giao diện là **một màn hình trong trình cài đặt**, không
    phải hai bộ cài. Tách thành hai mục trong catalog chỉ vì sàn RAM khác nhau."""
    monkeypatch.setenv("LTT_VPS_ISO_WINSRV2016_CORE", "local:iso/2016.iso")
    monkeypatch.setenv("LTT_VPS_ISO_WINSRV2016_GUI", "local:iso/2016.iso")
    assert (os_images.dia_cai_dat("winsrv2016-core")
            == os_images.dia_cai_dat("winsrv2016-gui") != "")
    assert (os_images.lay_os("winsrv2016-core").ram_mb_toi_thieu
            < os_images.lay_os("winsrv2016-gui").ram_mb_toi_thieu)


# ── 4. Xếp chỗ ───────────────────────────────────────────────────────────────

def test_het_ram_thi_khong_ban_nua():
    sc = capacity.SucChua(ram_mb_tong=64 * 1024, dia_gb_tong=600,
                          ram_mb_da_hua=64 * 1024 - capacity.RAM_DU_PHONG_MB,
                          dia_gb_da_hua=0)
    kq = capacity.cho_phep_ban(sc, "vps-vua")
    assert kq.cho_phep is False
    assert "RAM" in kq.ly_do


def test_dia_la_tai_nguyen_CHIA_SE_khong_giu_cho_cung(capsys=None):
    """V14: đã hứa vượt kho **không** phải lý do từ chối, miễn kho còn trống thật.

    Node đo được 640 GB hứa trên 475 GB kho mà mới dùng 173 GB. Nếu giữ chỗ cứng
    thì lãng phí 3/4 kho và sản phẩm không bán được máy nào.
    """
    sc = capacity.SucChua(ram_mb_tong=64 * 1024, dia_gb_tong=600,
                          dia_gb_da_hua=700,        # da hua VUOT kho
                          dia_gb_dang_dung=100)     # nhung moi dung 100 GB
    assert capacity.cho_phep_ban(sc, "vps-nho").cho_phep is True


def test_phanh_1_kho_thuc_dung_cham_80_phan_tram():
    """Máy đầy dần theo thời gian mà không ai bán thêm gì — chỉ phanh này thấy."""
    ban_duoc = 600 - capacity.DIA_TEMPLATE_GB
    sc = capacity.SucChua(ram_mb_tong=64 * 1024, dia_gb_tong=600,
                          dia_gb_da_hua=100,
                          dia_gb_dang_dung=int(ban_duoc * 0.80))
    kq = capacity.cho_phep_ban(sc, "vps-nho")
    assert kq.cho_phep is False
    assert "nguong" in kq.ly_do


def test_phanh_2_khong_cho_ban_vo_han_khi_kho_con_rong():
    """Kho mới dùng 5 % nhưng đã hứa gấp 10 lần thì ngày mai là thảm hoạ."""
    sc = capacity.SucChua(ram_mb_tong=64 * 1024, dia_gb_tong=600,
                          dia_gb_da_hua=int((600 - 45) * 3.0),
                          dia_gb_dang_dung=30)
    kq = capacity.cho_phep_ban(sc, "vps-nho")
    assert kq.cho_phep is False
    assert "ban chong" in kq.ly_do
    assert capacity.TRAN_BAN_CHONG == 3.0


def test_khong_doc_duoc_kho_thi_KHONG_ban(capsys=None):
    """Fail-closed, cả ở đường `cho_phep_ban` chứ không chỉ ở `kho_qua_tai`."""
    sc = capacity.SucChua(ram_mb_tong=64 * 1024, dia_gb_tong=0)
    assert capacity.cho_phep_ban(sc, "vps-nho").cho_phep is False


def test_sau_V14_RAM_la_thu_quyet_dinh_so_may_ban_duoc():
    """Đĩa chia sẻ ⇒ trần thật là RAM, không phải đĩa.

    Với node thật sau khi nới RAM lên 64 GB và trừ 35 GB của 8 máy chủ nhà:
    còn ~23 GB ⇒ 5 máy `vps-vua`. Test này giữ cho tài liệu và code khỏi trôi
    khỏi nhau.
    """
    ram_con = 64 * 1024 - capacity.RAM_DU_PHONG_MB - 36 * 1024
    assert ram_con // 4096 == 5         # vps-vua (4 GB)
    assert ram_con // 2048 == 11        # vps-nho (2 GB)


def test_dem_ca_VM_KHONG_thuoc_app_nay():
    """Lỗi thật, chỉ lộ ra khi đo cụm thật ngày 2026-08-22.

    Node có sẵn **8 máy của chủ nhà chiếm 35,9 GB / 43,2 GB RAM**. Bản đầu của
    `capacity` chỉ cộng phần app tự bán (0 máy) nên vẫn báo "còn 38 GB, bán tiếp
    đi" — bán tiếp ở đó là bán chỗ của chính chủ nhà.
    """
    vms = [
        {"vmid": 100, "maxmem": 8 * 1024 ** 3, "maxdisk": 80 * 1024 ** 3},
        {"vmid": 101, "maxmem": 4 * 1024 ** 3, "maxdisk": 80 * 1024 ** 3},
        # Template không tính: nó không chạy, và đĩa của nó đã trừ ở DIA_TEMPLATE_GB.
        {"vmid": 9000, "maxmem": 5 * 1024 ** 3, "maxdisk": 80 * 1024 ** 3,
         "template": 1},
    ]
    ram, dia, _vcpu = capacity.cam_ket_tu_vm(vms)
    assert ram == 12 * 1024
    assert dia == 160


def test_suc_chua_ghep_proxmox_voi_may_app_CHUA_kip_tao(db):
    """Máy đã có VMID thì Proxmox đếm rồi — cộng lần nữa là đếm đúp."""
    from apps.vps.services import provisioning
    g = _gateway(db)
    da_tao = _may(db, g, plan_id="vps-vua")          # 4 GB / 60 GB
    da_tao.vmid = 200
    _may(db, g, plan_id="vps-nho")                    # 2 GB / 40 GB, chưa có vmid
    db.flush()

    sc = provisioning.suc_chua_hien_tai(
        db,
        {"memory": {"total": 64 * 1024 ** 3}},
        [{"storage": "vmdata", "content": "images,rootdir",
          "total": 475 * 1024 ** 3}],
        [{"vmid": 200, "maxmem": 4 * 1024 ** 3, "maxdisk": 60 * 1024 ** 3}],
    )
    # 4 GB (Proxmox, may da tao) + 2 GB (CSDL, may chua tao) = 6 GB
    assert sc.ram_mb_da_hua == 6 * 1024
    assert sc.dia_gb_da_hua == 100


def test_node_da_day_thi_TU_CHOI_ban_them(db):
    """Trạng thái thật của cụm 2026-08-22: 35,9 GB cam kết / 43,2 GB tổng.

    Hết RAM — và sau V14 thì **RAM** mới là thứ chặn, không phải đĩa.
    """
    from apps.vps.services import provisioning
    vms = [{"vmid": 100 + i, "maxmem": 4 * 1024 ** 3, "maxdisk": 80 * 1024 ** 3}
           for i in range(8)]
    vms[0]["maxmem"] = 8 * 1024 ** 3            # VM100 that su 7,9 GB
    sc = provisioning.suc_chua_hien_tai(
        db,
        {"memory": {"total": 43 * 1024 ** 3}},
        [{"storage": "vmdata", "content": "images,rootdir",
          "total": 475 * 1024 ** 3, "used": 174 * 1024 ** 3}],
        vms)
    assert sc.dia_gb_dang_dung == 174
    kq = capacity.cho_phep_ban(sc, "vps-vua")
    assert kq.cho_phep is False, "node da day ma van cho ban -> ban cho cua chu nha"
    assert "RAM" in kq.ly_do


def test_khong_doc_duoc_dung_luong_thi_NGUNG_ban():
    """Fail-closed: bán khi không biết còn bao nhiêu chỗ là đúng thứ phải phòng."""
    assert capacity.kho_qua_tai(0, 0).cho_phep is False


def test_nguong_80_phan_tram():
    tong = 1000
    assert capacity.kho_qua_tai(799, tong).cho_phep is True
    assert capacity.kho_qua_tai(800, tong).cho_phep is False


def test_doc_suc_chua_tu_phan_hoi_proxmox():
    sc = capacity.suc_chua_tu_proxmox(
        {"memory": {"total": 64 * 1024 ** 3}},
        [{"storage": "local", "content": "iso,vztmpl", "total": 50 * 1024 ** 3},
         {"storage": "local-lvm", "content": "images,rootdir",
          "total": 600 * 1024 ** 3}])
    assert sc.ram_mb_tong == 65536
    assert sc.dia_gb_tong == 600        # bỏ qua kho `iso`, chỉ lấy kho `images`


# ── 5. Driver Proxmox ────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload if payload is not None else {"data": None}

    def json(self):
        return self._payload


class _Session:
    """Session giả — nhờ nó toàn bộ tầng trên kiểm được mà không cần cụm thật."""

    def __init__(self, *phan_hoi):
        self.phan_hoi = list(phan_hoi)
        self.calls = []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        return self.phan_hoi.pop(0) if self.phan_hoi else _Resp(200)


def _cau_hinh():
    return proxmox.doc_cau_hinh({
        "LTT_VPS_PROXMOX_URL": "https://192.168.2.168:8006",
        "LTT_VPS_PROXMOX_TOKEN_ID": "vpsapp@pve!ltt",
        "LTT_VPS_PROXMOX_TOKEN_SECRET": "bi-mat",
        "LTT_VPS_PROXMOX_NODE": "pve",
    })


def test_thieu_bien_moi_truong_thi_bao_ro_thieu_cai_nao():
    with pytest.raises(proxmox.ChuaCauHinh) as e:
        proxmox.doc_cau_hinh({})
    assert "LTT_VPS_PROXMOX_URL" in str(e.value)


def test_token_id_sai_dang_bi_bat_ngay():
    """Sai dạng thì Proxmox trả 401 chung chung — bắt sớm để khỏi mất một giờ dò."""
    with pytest.raises(proxmox.ChuaCauHinh) as e:
        proxmox.doc_cau_hinh({
            "LTT_VPS_PROXMOX_URL": "https://x:8006",
            "LTT_VPS_PROXMOX_TOKEN_ID": "vpsapp@pve",     # thiếu `!ten`
            "LTT_VPS_PROXMOX_TOKEN_SECRET": "s",
        })
    assert "user@realm!tenToken" in str(e.value)


def test_header_uy_quyen_dung_dinh_dang_proxmox():
    ss = _Session(_Resp(200, {"data": {"version": "9.2"}}))
    c = proxmox.ProxmoxClient(_cau_hinh(), session=ss)
    assert c.phien_ban() == {"version": "9.2"}
    _m, url, kw = ss.calls[0]
    assert url.endswith("/api2/json/version")
    assert kw["headers"]["Authorization"] == "PVEAPIToken=vpsapp@pve!ltt=bi-mat"
    assert kw["timeout"] == proxmox.TIMEOUT_MAC_DINH


def test_401_va_403_co_thong_diep_khac_nhau():
    c = proxmox.ProxmoxClient(_cau_hinh(), session=_Session(_Resp(401)))
    with pytest.raises(proxmox.ProxmoxError) as e:
        c.phien_ban()
    assert e.value.status == 401

    c = proxmox.ProxmoxClient(_cau_hinh(), session=_Session(_Resp(403)))
    with pytest.raises(proxmox.ProxmoxError) as e:
        c.phien_ban()
    assert e.value.status == 403


def test_khong_bao_gio_tu_thu_lai():
    """Thử lại một POST clone đã tới nơi sẽ tạo MÁY THỨ HAI, mồ côi, ăn đĩa."""
    ss = _Session(_Resp(500))
    c = proxmox.ProxmoxClient(_cau_hinh(), session=ss)
    with pytest.raises(proxmox.ProxmoxError):
        c.clone(9001, 250, ten="vps-test")
    assert len(ss.calls) == 1


def test_clone_mac_dinh_la_linked_clone():
    """Linked clone là khác biệt giữa bán được vài máy và bán được vài chục."""
    ss = _Session(_Resp(200, {"data": "UPID:pve:1"}))
    c = proxmox.ProxmoxClient(_cau_hinh(), session=ss)
    assert c.clone(9001, 250, ten="vps-test") == "UPID:pve:1"
    assert ss.calls[0][2]["data"]["full"] == 0


def test_DELETE_dua_tham_so_vao_QUERY_STRING_khong_phai_than():
    """Proxmox tra **501 Not Implemented** khi tham so cua DELETE nam trong than.

    Thong bao 501 khong noi gi ve nguyen nhan — no nghe nhu endpoint khong ton
    tai. Da ton mot lan xoa that de tim ra. Test nay giu cho no khong quay lai.
    """
    ss = _Session(_Resp(200, {"data": "UPID:pve:xoa"}))
    c = proxmox.ProxmoxClient(_cau_hinh(), session=ss)
    c.xoa(9000)
    _m, url, kw = ss.calls[0]
    assert "purge=1" in url, "tham so DELETE phai o query string"
    assert "destroy-unreferenced-disks=1" in url
    assert kw.get("data") is None, "DELETE khong duoc gui than request"


def test_loi_mang_thanh_ProxmoxError_chu_khong_thoat_ra_ngoai():
    class _No:
        def request(self, *a, **k):
            raise OSError("khong noi duoc")

    c = proxmox.ProxmoxClient(_cau_hinh(), session=_No())
    with pytest.raises(proxmox.ProxmoxError):
        c.phien_ban()


# ── 5b. Mạng riêng của khách ────────────────────────────────────────────────

def _gw_mang(**doi):
    """Cổng vào giống hạ tầng thật đang chạy: 10.51.0.0/24, router ở .1."""
    from apps.vps.tables import VpsGateway
    tham = dict(ten="cong-sgp", vung="sgp", ip_cong_khai="45.32.114.249",
                ten_mien="", bridge="vmbr1", subnet_cidr="10.51.0.0/24",
                subnet_gw="10.51.0.1", dns="1.1.1.1 8.8.8.8",
                mtu=1420, octet_dau=10, octet_cuoi=250)
    tham.update(doi)
    return VpsGateway(**tham)


def test_dai_dia_chi_bo_qua_dia_chi_cua_router():
    """10.51.0.1 là VM router, không phải chỗ trống — cấp nó là mất cả mạng."""
    from apps.vps.services import mang
    ds = list(mang.dai_dia_chi(_gw_mang(octet_dau=1, octet_cuoi=4)))
    assert ds == ["10.51.0.2", "10.51.0.3", "10.51.0.4"]
    assert "10.51.0.1" not in ds


def test_so_dia_chi_dung_de_do_suc_chua():
    from apps.vps.services import mang
    assert mang.so_dia_chi(_gw_mang(octet_dau=10, octet_cuoi=19)) == 10


def test_cau_hinh_qemu_cam_MOT_card_vao_bridge_co_lap():
    """Máy khách không được có card ra LAN nhà — chỉ một đường, qua vmbr1."""
    from apps.vps.services import mang
    c = mang.cau_hinh_qemu(mang.mang_cho_may(_gw_mang(), "10.51.0.50"))
    assert c["net0"] == f"{mang.MO_HINH_CARD},bridge=vmbr1,firewall=0,mtu=1420"
    assert mang.MO_HINH_CARD != "virtio", (
        "virtio treo tren cum long trong VMware — xem chu thich MO_HINH_CARD")
    assert c["ipconfig0"] == "ip=10.51.0.50/24,gw=10.51.0.1"
    assert c["nameserver"] == "1.1.1.1 8.8.8.8"
    assert "net1" not in c, "khach chi duoc mot card"


def test_MTU_phai_duoc_ghim_vao_cau_hinh():
    """1420 là số ĐO THẬT qua đường hầm. Để mặc định 1500 thì gói lớn rơi im lặng,
    triệu chứng là 'web nào cũng vào được trừ vài trang' — mất hàng giờ mới lần ra."""
    from apps.vps.services import mang
    c = mang.cau_hinh_qemu(mang.mang_cho_may(_gw_mang(), "10.51.0.50"))
    assert "mtu=1420" in c["net0"]


def test_cong_vao_khai_thieu_thi_TU_CHOI_chu_khong_doan():
    from apps.vps.services import mang
    for thieu in ("bridge", "subnet_cidr", "subnet_gw"):
        with pytest.raises(mang.CauHinhMangError) as e:
            mang.mang_cho_may(_gw_mang(**{thieu: ""}), "10.51.0.50")
        assert thieu in str(e.value)


def test_dia_chi_ngoai_mang_hoac_trung_router_thi_TU_CHOI():
    from apps.vps.services import mang
    with pytest.raises(mang.CauHinhMangError) as e:
        mang.mang_cho_may(_gw_mang(), "10.99.0.50")
    assert "khong thuoc mang" in str(e.value)
    with pytest.raises(mang.CauHinhMangError) as e:
        mang.mang_cho_may(_gw_mang(), "10.51.0.1")
    assert "cong vao" in str(e.value)
    with pytest.raises(mang.CauHinhMangError):
        mang.mang_cho_may(_gw_mang(), "")


def test_chi_nhan_mask_24_chu_khong_doan_gan_dung():
    """Nhận /16 rồi tính sai một octet là cấp TRÙNG địa chỉ cho hai khách."""
    from apps.vps.services import mang
    with pytest.raises(mang.CauHinhMangError) as e:
        mang.mang_cho_may(_gw_mang(subnet_cidr="10.51.0.0/16"), "10.51.0.50")
    assert "/24" in str(e.value)


# ── 6. Cấp phát nguyên tử ────────────────────────────────────────────────────

def test_hai_may_khong_bao_gio_nhan_cung_mot_dia_chi(db):
    from apps.vps.services import provisioning
    g = _gateway(db, octet_dau=10, octet_cuoi=11)
    m1, m2 = _may(db, g), _may(db, g)
    a1 = provisioning.cap_ip_noi_bo(db, m1, g)
    a2 = provisioning.cap_ip_noi_bo(db, m2, g)
    assert {a1, a2} == {"10.51.0.10", "10.51.0.11"}


def test_het_dia_chi_thi_bao_loi_ro_rang_chu_khong_ghi_de(db):
    from apps.vps.services import provisioning
    g = _gateway(db, octet_dau=10, octet_cuoi=10)
    provisioning.cap_ip_noi_bo(db, _may(db, g), g)
    with pytest.raises(provisioning.HetChoError) as e:
        provisioning.cap_ip_noi_bo(db, _may(db, g), g)
    assert "het dia chi" in str(e.value)


def test_cap_lai_cho_cung_mot_may_tra_ve_dung_dia_chi_cu(db):
    """Job chạy lại không được cấp thêm địa chỉ thứ hai cho cùng một máy."""
    from apps.vps.services import provisioning
    g = _gateway(db)
    m = _may(db, g)
    a1 = provisioning.cap_ip_noi_bo(db, m, g)
    db.commit()
    assert provisioning.cap_ip_noi_bo(db, m, g) == a1


def test_dia_chi_da_cap_van_giu_duoc_sau_khi_mot_lan_dung_do(db):
    """Sau một `IntegrityError`, transaction phải còn dùng được (savepoint)."""
    from apps.vps.services import provisioning
    g = _gateway(db, octet_dau=10, octet_cuoi=15)
    provisioning.cap_ip_noi_bo(db, _may(db, g), g)
    db.commit()
    a2 = provisioning.cap_ip_noi_bo(db, _may(db, g), g)
    db.commit()
    assert a2 == "10.51.0.11"


def test_vmid_TRANH_may_da_co_tren_may_chu(db):
    """Máy tồn tại trên Proxmox mà CSDL không biết thì KHÔNG được cấp lại số đó.

    Nếu cấp lại, `jobs.py` thấy VM đã tồn tại nên bỏ qua bước nhân bản rồi cấu
    hình lại chính máy đó — tức **giao máy của người này cho người khác**, không
    một lỗi nào được ghi ra. Đã dính thật 24/08 với CSDL rỗng.
    """
    from apps.vps.services import provisioning
    g = _gateway(db)
    m = _may(db, g)
    vmid = provisioning.cap_vmid(db, m, da_co_tren_may_chu={200, 201, 202})
    assert vmid not in (200, 201, 202)
    assert vmid == 203


def test_vmid_khong_trung_va_ton_trong_goi_y(db):
    from apps.vps.services import provisioning
    g = _gateway(db)
    a = provisioning.cap_vmid(db, _may(db, g), goi_y=250)
    b = provisioning.cap_vmid(db, _may(db, g), goi_y=250)
    assert a == 250 and b == 251


def test_ip_rieng_chi_cap_tren_cong_cho_phep(db):
    from apps.vps.services import provisioning
    from apps.vps.tables import VpsIp
    g = _gateway(db, ip_rieng=False)
    with pytest.raises(provisioning.HetChoError):
        provisioning.cap_ip(db, _may(db, g), g)

    g2 = _gateway(db, ten="cong-sgp", vung="sgp", ip_rieng=True)
    db.add(VpsIp(gateway_id=g2.id, dia_chi="198.51.100.7"))
    db.flush()
    m = _may(db, g2)
    assert provisioning.cap_ip(db, m, g2).dia_chi == "198.51.100.7"
    with pytest.raises(provisioning.HetChoError):
        provisioning.cap_ip(db, _may(db, g2), g2)


def test_chon_cong_vao_theo_vung_va_bo_qua_cong_dang_dong(db):
    from apps.vps.services import provisioning
    g = _gateway(db, vung="vn", ten="vn-1")
    g.dang_nhan_may_moi = False
    db.flush()
    with pytest.raises(provisioning.KhongCoGatewayError):
        provisioning.chon_gateway(db, "vn")
    g.dang_nhan_may_moi = True
    db.flush()
    assert provisioning.chon_gateway(db, "vn").id == g.id


def test_may_bi_treo_van_tinh_la_dang_chiem_cho(db):
    """V8 chỉ xoá sau 7 ngày, nên máy treo vẫn giữ đĩa — chưa bán lại được."""
    from apps.vps.services import provisioning
    g = _gateway(db)
    _may(db, g, plan_id="vps-vua", trang_thai="bi_treo")
    ram, dia = provisioning.da_hua(db)
    assert (ram, dia) == (4096, 60)

    _may(db, g, plan_id="vps-nho", trang_thai="da_xoa")
    ram2, dia2 = provisioning.da_hua(db)
    assert (ram2, dia2) == (ram, dia)      # máy đã xoá thì không tính


# ── 7. Tiền ──────────────────────────────────────────────────────────────────

def _khach(db, credit_ban_dau=0):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email="vps@ex.com", password="mat-khau-dai-123456",
                       is_verified=True)
    db.flush()
    if credit_ban_dau:
        credit.nap(db, u.id, credit_ban_dau)
    return u


def test_thu_dung_so_credit_va_dat_han_30_ngay(db):
    from apps.vps.services import billing
    from platform_core import credit
    u = _khach(db, 5000)
    g = _gateway(db)
    m = _may(db, g, user_id=u.id, plan_id="vps-vua")

    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    assert billing.thu_mot_chu_ky(db, m, now=now) == 1790
    assert credit.so_du(db, u.id) == 5000 - 1790
    assert m.paid_until == now + timedelta(days=30)


def test_han_cong_don_tu_moc_cu_chu_khong_tu_hom_nay(db):
    """Khách trả muộn hai ngày thì hai ngày đó vẫn thuộc chu kỳ đã trả."""
    from apps.vps.services import billing
    u = _khach(db, 5000)
    g = _gateway(db)
    m = _may(db, g, user_id=u.id, plan_id="vps-nho")

    m.paid_until = datetime(2026, 8, 20, tzinfo=timezone.utc)
    tre = datetime(2026, 8, 22, tzinfo=timezone.utc)
    billing.thu_mot_chu_ky(db, m, now=tre)
    assert m.paid_until == datetime(2026, 9, 19, tzinfo=timezone.utc)


def test_tre_hon_mot_chu_ky_thi_bat_dau_lai_tu_hom_nay(db):
    """Chống lỗi NUỐT TIỀN, không phải lỗi lệch ngày.

    Máy bị treo hai tháng rồi khách nạp lại. Nếu cộng dồn từ mốc cũ thì mốc mới
    vẫn nằm trong quá khứ — máy vừa thu xong đã hết hạn ngay, và vòng thu sẽ trừ
    tiếp mỗi lượt cho tới khi cạn sạch số dư.
    """
    from apps.vps.services import billing
    from platform_core import credit
    u = _khach(db, 5000)
    g = _gateway(db)
    m = _may(db, g, user_id=u.id, plan_id="vps-nho")

    m.paid_until = datetime(2026, 6, 1, tzinfo=timezone.utc)
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    billing.thu_mot_chu_ky(db, m, now=now)
    assert m.paid_until == now + timedelta(days=30)
    assert billing.con_han(m, now=now) is True
    # Và lượt quét kế tiếp KHÔNG được trừ thêm lần nữa.
    con_lai = credit.so_du(db, u.id)
    assert billing.thu_phi_dinh_ky(db, now=now) == {"da_thu": 0, "da_treo": 0}
    assert credit.so_du(db, u.id) == con_lai


def test_thieu_credit_thi_khong_tru_nua_vong(db):
    from apps.vps.services import billing
    from platform_core import credit
    u = _khach(db, 100)
    g = _gateway(db)
    m = _may(db, g, user_id=u.id, plan_id="vps-lon")
    with pytest.raises(billing.ThieuCreditError):
        billing.thu_mot_chu_ky(db, m)
    assert credit.so_du(db, u.id) == 100
    assert m.paid_until is None


def test_het_credit_thi_treo_ngay_va_dat_moc_xoa_bay_ngay(db):
    from apps.vps.services import billing
    u = _khach(db, 0)
    g = _gateway(db)
    m = _may(db, g, user_id=u.id, plan_id="vps-vua", trang_thai="dang_chay")
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)

    ket_qua = billing.thu_phi_dinh_ky(db, now=now)
    assert ket_qua == {"da_thu": 0, "da_treo": 1}
    assert m.trang_thai == "bi_treo"
    assert m.xoa_sau == now + timedelta(days=7)

    # Chưa tới hạn thì chưa xoá; tới hạn thì có trong danh sách.
    assert billing.den_han_xoa(db, now=now + timedelta(days=6)) == []
    assert [x.id for x in billing.den_han_xoa(db, now=now + timedelta(days=7))] \
        == [m.id]


def test_may_con_han_thi_khong_bi_thu_lai(db):
    from apps.vps.services import billing
    u = _khach(db, 5000)
    g = _gateway(db)
    m = _may(db, g, user_id=u.id, plan_id="vps-nho", trang_thai="dang_chay")
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    m.paid_until = now + timedelta(days=10)
    db.flush()
    assert billing.thu_phi_dinh_ky(db, now=now) == {"da_thu": 0, "da_treo": 0}


def test_su_kien_duoc_ghi_lai_de_tra_loi_khach(db):
    """Nhật ký vòng đời là thứ trả lời "vì sao máy tôi bị tắt", không phải log."""
    from apps.vps.services import billing
    from apps.vps.tables import VpsEvent
    u = _khach(db, 5000)
    g = _gateway(db)
    m = _may(db, g, user_id=u.id, plan_id="vps-nho")
    billing.thu_mot_chu_ky(db, m)
    db.flush()
    loai = [e.loai for e in db.query(VpsEvent).filter_by(instance_id=m.id)]
    assert "thu_phi" in loai


# ── 9. Bán chồng CPU ─────────────────────────────────────────────────────────
#
# Trước 24/08 `cho_phep_ban` gác RAM và đĩa nhưng **không gác CPU chút nào**, nên
# mức bán chồng CPU là một hệ quả tình cờ chứ không phải một lựa chọn. Node đo
# được: **32 luồng**, mà riêng 8 máy của chủ nhà đã cam kết **41 vCPU** — tức nó
# đã ở 1,28× trước khi bán cho ai một máy nào.

def _suc_chua_rong(**kw):
    """Sức chứa dư dả về RAM và đĩa, để chỉ còn CPU là thứ quyết định."""
    mac_dinh = dict(ram_mb_tong=200_000, dia_gb_tong=2000, dia_gb_dang_dung=10)
    mac_dinh.update(kw)
    return capacity.SucChua(**mac_dinh)


def test_cam_ket_tu_vm_dem_ca_vCPU():
    vms = [{"maxmem": 4 * 1024 ** 3, "maxdisk": 40 * 1024 ** 3, "cpus": 2},
           {"maxmem": 8 * 1024 ** 3, "maxdisk": 80 * 1024 ** 3, "cpus": 6},
           {"maxmem": 1 * 1024 ** 3, "maxdisk": 10 * 1024 ** 3, "cpus": 4,
            "template": 1}]
    _ram, _dia, vcpu = capacity.cam_ket_tu_vm(vms)
    assert vcpu == 8, "template khong tinh, dung nhu RAM va dia"


def test_ty_le_ban_chong_cpu():
    sc = _suc_chua_rong(cpu_tong=32, vcpu_da_hua=41)
    assert round(sc.ty_le_ban_chong_cpu, 2) == 1.28


def test_chua_do_duoc_cpu_thi_KHONG_chan():
    """CPU khác RAM và đĩa: thiếu nó máy vẫn chạy, chỉ chậm. Nên "không đọc được"
    ở đây không đáng để dừng bán hàng — khác hẳn với đĩa, nơi không đọc được thì
    phải NGỪNG bán."""
    sc = _suc_chua_rong(cpu_tong=0, vcpu_da_hua=999)
    assert capacity.cho_phep_ban(sc, "vps-lon").cho_phep is True
    assert sc.ty_le_ban_chong_cpu == 0.0


def test_vuot_tran_ban_chong_cpu_thi_CHAN():
    tran = capacity.TRAN_BAN_CHONG_CPU
    sc = _suc_chua_rong(cpu_tong=32, vcpu_da_hua=int(32 * tran))
    kq = capacity.cho_phep_ban(sc, "vps-lon")
    assert kq.cho_phep is False
    assert "CPU" in kq.ly_do and "vCPU" in kq.ly_do, kq.ly_do


def test_ngay_duoi_tran_thi_van_ban_duoc():
    sc = _suc_chua_rong(cpu_tong=32, vcpu_da_hua=90)     # 90+1 = 91/32 = 2.84x
    assert capacity.cho_phep_ban(sc, "vps-nho").cho_phep is True


def test_RAM_van_hoi_TRUOC_cpu():
    """Thiếu RAM thì máy **không khởi động nổi**; thiếu CPU thì nó chỉ chậm. Lý
    do từ chối phải nói đúng thứ chặn thật, nếu không người đọc đi sửa nhầm chỗ."""
    sc = capacity.SucChua(ram_mb_tong=1024, dia_gb_tong=2000,
                          cpu_tong=1, vcpu_da_hua=500)
    assert "RAM" in capacity.cho_phep_ban(sc, "vps-lon").ly_do
