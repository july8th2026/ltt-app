"""H39 — danh tính phần cứng của máy khách: khác nhau, và KHÔNG đổi.

Hai tính chất ở đây kéo về hai phía ngược nhau, và cả hai đều là lỗi thật nếu
mất:

* **khác nhau giữa các máy** — máy trùng danh tính thì bản sao lưu, giấy phép và
  mọi thứ nhận diện theo phần cứng lẫn lộn giữa hai khách, và một máy bị chặn thì
  máy kia chịu chung mà không tự gỡ được;
* **không đổi qua các lần chạy lại** — job tạo máy chạy lại được; MAC đổi giữa
  chừng thì Windows đã cài xong thấy card "mới", đặt hồ sơ mạng về *Public*, và
  tường lửa chặn RDP. Khách mất đường vào máy của chính họ.

Test ở đây kiểm cả hai, vì sửa một tính chất rất dễ làm hỏng tính chất kia.
"""
from __future__ import annotations

import re
import uuid as _uuid

import pytest

from apps.vps.services import dinh_danh, mang
from apps.vps.tables import VpsGateway

MAU = [f"550e8400-e29b-41d4-a716-{i:012d}" for i in range(500)]


# ── 1. Khác nhau ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("lay,ten", [
    (dinh_danh.mac, "MAC"),
    (dinh_danh.uuid_smbios, "UUID"),
    (dinh_danh.so_hieu_dia, "so hieu dia"),
    (dinh_danh.so_hieu_may, "so hieu may"),
])
def test_500_may_khong_trung_nhau(lay, ten):
    gia_tri = [lay(x) for x in MAU]
    assert len(set(gia_tri)) == len(MAU), f"{ten} bi trung"


def test_bon_muc_doc_lap_nhau():
    """Mỗi mục băm từ một chuỗi riêng. Nếu chúng dùng chung một nguồn byte thì
    đổi cách sinh một mục sẽ lặng lẽ kéo mục khác đổi theo."""
    m = MAU[0]
    b = {dinh_danh.mac(m), dinh_danh.uuid_smbios(m),
         dinh_danh.so_hieu_dia(m), dinh_danh.so_hieu_may(m)}
    assert len(b) == 4


# ── 2. Không đổi ────────────────────────────────────────────────────────────

def test_goi_lai_cho_ket_qua_Y_HET():
    """Đây là tính chất khiến ta SUY RA thay vì bốc ngẫu nhiên."""
    for _ in range(3):
        assert dinh_danh.danh_tinh(MAU[7]) == dinh_danh.danh_tinh(MAU[7])


def test_khong_dung_ngau_nhien_that(monkeypatch):
    """Chốt cứng: nếu ai đó thay bằng `secrets`/`random` thì test này đỏ."""
    import random
    import secrets

    def cam(*a, **kw):
        raise AssertionError("danh tinh khong duoc dung nguon ngau nhien")

    for mod, ten in ((random, "randbytes"), (random, "random"),
                     (secrets, "token_bytes"), (secrets, "token_hex")):
        if hasattr(mod, ten):
            monkeypatch.setattr(mod, ten, cam)
    dinh_danh.danh_tinh(MAU[3])


# ── 3. Đúng khuôn để Proxmox và máy khách nhận ──────────────────────────────

def test_mac_dung_khuon_va_giu_OUI_proxmox():
    """Giữ OUI của Proxmox là **cố ý**: máy này là máy ảo, ta không giả nó thành
    máy của một hãng phần cứng nào."""
    for x in MAU[:50]:
        m = dinh_danh.mac(x)
        assert re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", m), m
        assert m.startswith(dinh_danh.OUI + ":")


def test_mac_la_unicast_khong_phai_multicast():
    """Bit thấp nhất của octet đầu bật = địa chỉ multicast; card mang địa chỉ đó
    thì gói tin không tới nơi. `BC` chẵn nên an toàn — nhưng chốt lại phòng khi
    ai đó đổi `OUI`."""
    dau = int(dinh_danh.OUI.split(":")[0], 16)
    assert dau & 1 == 0


def test_uuid_hop_le_va_dung_phien_ban_4():
    for x in MAU[:50]:
        u = _uuid.UUID(dinh_danh.uuid_smbios(x))
        assert u.version == 4 and u.variant == _uuid.RFC_4122


def test_so_hieu_dia_khong_vuot_gioi_han_ATA():
    """Dài quá 20 ký tự bị cắt cụt LẶNG LẼ — và cắt cụt là con đường về lại chỗ
    trùng nhau."""
    for x in MAU[:50]:
        s = dinh_danh.so_hieu_dia(x)
        assert 0 < len(s) <= 20 and re.fullmatch(r"[0-9A-Z]+", s), s


def test_smbios1_dat_uuid_va_serial_nhung_KHONG_gia_nha_san_xuat():
    s = dinh_danh.smbios1(MAU[0])
    assert s.startswith("uuid=") and "serial=" in s and s.endswith("base64=1")
    for cam in ("manufacturer=", "product=", "family=", "sku="):
        assert cam not in s, f"khong gia {cam}"


def test_instance_id_rong_thi_NEM_chu_khong_tra_bua():
    """Trả về một danh tính mặc định thì mọi máy lỗi sẽ dùng CHUNG danh tính đó."""
    for xau in ("", "   ", None):
        with pytest.raises(ValueError):
            dinh_danh.danh_tinh(xau)


# ── 4. MAC phải thực sự tới được `net0` ─────────────────────────────────────

def _gw():
    return VpsGateway(ten="gw", bridge="vmbr1", subnet_cidr="10.51.0.0/24",
                      subnet_gw="10.51.0.1", dns="1.1.1.1", mtu=1420)


def test_mac_duoc_ghim_vao_net0():
    m = mang.mang_cho_may(_gw(), "10.51.0.50")
    net = mang.cau_hinh_qemu(m, co_cloud_init=False,
                             mac="bc:24:11:aa:bb:cc")["net0"]
    assert net.startswith(f"{mang.MO_HINH_CARD}=BC:24:11:AA:BB:CC,")
    assert "bridge=vmbr1" in net and "mtu=1420" in net


def test_khong_truyen_mac_thi_van_chay_duoc():
    """Đường nội bộ (Linux, nhân bản) không cần MAC ghim."""
    m = mang.mang_cho_may(_gw(), "10.51.0.50")
    assert mang.cau_hinh_qemu(m, co_cloud_init=False)["net0"].startswith(
        f"{mang.MO_HINH_CARD},")


def test_job_tao_may_THAT_SU_ghim_ba_thu_vao_cau_hinh():
    """Test đơn vị ở trên không chứng minh job có GỌI chúng không. Đây mới là
    chỗ từng để lọt: hàm đúng, nhưng không ai gọi."""
    from apps.vps import cost, jobs, os_images

    class _May:
        id = "550e8400-e29b-41d4-a716-000000000042"
        plan_id = "vps-nho"
        dia_them_gb = 0

    may = _May()
    plan = cost.lay_plan("vps-nho")
    img = os_images.lay_os("winsrv2022-core")
    ch = jobs._cau_hinh_may_trong(may, plan, img, "vmdata:iso/x.iso")

    assert dinh_danh.so_hieu_dia(may.id) in ch["sata0"]
    assert ch["smbios1"] == dinh_danh.smbios1(may.id)
    assert dinh_danh.uuid_smbios(may.id) in ch["smbios1"]


# ── 5. Mô hình template đã bỏ — và không được lặng lẽ quay lại ──────────────

def test_khong_con_ham_template_vmid():
    assert not hasattr(os_module(), "template_vmid"), (
        "mo hinh template da bo 2026-08-24")


def os_module():
    from apps.vps import os_images
    return os_images


def test_KHONG_con_duong_nhan_ban_template():
    """Ba template cuối bị xoá khỏi cụm 24/08 (chủ sản phẩm chốt: "sài qua cài
    đặt thì xoá các template"), nên nhánh `clone` không còn đối tượng nào để
    nhân bản.

    Giữ lại một nhánh không ai đi qua **trong đường tạo máy** là giữ mã không
    lần chạy nào thử tới — và nó sẽ được ai đó "sửa lại cho chạy" vào một ngày
    không ai nhớ vì sao nó ở đó."""
    import inspect

    from apps.vps import jobs

    assert not hasattr(jobs, "_template_noi_bo")
    nguon = inspect.getsource(jobs._tao_may)
    assert "clone(" not in nguon, "van con nhanh nhan ban"
    assert "tao_may(" in nguon, "chi con mot duong: may trong + dia cai"


def test_khong_con_bien_moi_truong_template():
    """`LTT_VPS_TEMPLATE_*` không còn ai đọc. Để lại trong `app.env` thì lần sau
    có người đặt nó và tưởng nó có tác dụng."""
    from pathlib import Path

    tep = Path("secrets/app.env")
    if not tep.exists():
        return
    noi_dung = tep.read_text(encoding="utf-8-sig")
    assert "LTT_VPS_TEMPLATE_" not in noi_dung
