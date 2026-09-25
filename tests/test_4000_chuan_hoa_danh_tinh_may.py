"""Máy khách mới phải tự đúng chuẩn: CPU thật, và chống giả mạo IP/MAC.

🔴 Đo 25/09/2026 trên hai máy khách thật (VM 204, 208) khi so với Vultr:

  - `cpu` **không được khai** ⇒ QEMU dùng `kvm64`, một CPU giả lập generic,
    **giống hệt nhau trên mọi máy** và chậm hơn CPU thật;
  - `net0 … firewall=0` ⇒ `ipfilter`/`macfilter` của Proxmox **không chạy**, nên
    một khách có thể ARP/IP spoof khách khác trên cùng `vmbr1`.

⚠️ Và cái bẫy của bản vá này: **bật firewall mà để policy mặc định là DROP là
   cắt mạng của khách.** Mục tiêu ở đây CHỈ là chống giả mạo, không phải lọc gói.
   Nên hai policy phải ACCEPT **tường minh**, và phép kiểm phải chốt đúng điều đó
   — nếu không, bản sửa an ninh này thành một sự cố mất mạng.
"""
import pytest


@pytest.fixture()
def cau_hinh():
    from types import SimpleNamespace

    from apps.vps import jobs

    may = SimpleNamespace(id="3ca8c925-5859-4b02-9d1a-6ba708943245", plan_id="vps-nho",
                          dia_them_gb=0)
    plan = SimpleNamespace(vcpu=1, ram_mb=2048, disk_gb=40)
    img = SimpleNamespace(ho="windows")
    return jobs._cau_hinh_may_trong(may, plan, img, "local:iso/x.iso")


def test_CPU_khong_con_la_kvm64_generic(cau_hinh):
    """`kvm64` giống nhau trên mọi máy, và chậm hơn CPU thật."""
    assert cau_hinh.get("cpu") == "host"


def test_van_giu_nhung_thu_phan_biet_hai_may(cau_hinh):
    """Bánh cóc: đừng đánh đổi cái đang đúng lấy cái mới."""
    assert "serial=" in cau_hinh["sata0"]
    assert cau_hinh["smbios1"].startswith("uuid=")


def test_firewall_bat_de_CHONG_GIA_MAO(cau_hinh):
    from apps.vps import jobs

    fw = jobs._firewall_may_khach()
    assert fw["enable"] == 1
    assert fw["ipfilter"] == 1
    assert fw["macfilter"] == 1


@pytest.mark.parametrize("chieu", ["policy_in", "policy_out"])
def test_policy_phai_ACCEPT_tuong_minh(chieu):
    """⛔ Đây là phép kiểm quan trọng nhất tệp này. Proxmox mặc định policy DROP
    khi bật firewall; để nguyên mặc định là **cắt mạng của mọi khách** bằng một
    bản vá an ninh."""
    from apps.vps import jobs

    assert jobs._firewall_may_khach()[chieu] == "ACCEPT"


def test_net0_bat_co_firewall():
    """`ipfilter` chỉ áp khi chính NIC bật cờ firewall — cấu hình VM 204/208 đo
    được hôm nay là `firewall=0`, tức mọi luật ở trên đều không tới nơi.

    ⚠️ `net0` do `mang.cau_hinh_qemu` dựng, KHÔNG nằm trong `_cau_hinh_may_trong`
       — bản đầu của phép kiểm này hỏi nhầm chỗ và đỏ vì `KeyError`, tức nó đo
       một thứ không tồn tại ở đó thay vì đo cái cần đo.
    """
    from types import SimpleNamespace

    from apps.vps.services import mang

    m = SimpleNamespace(bridge="vmbr1", mtu=1420, cidr="10.50.0.52/24",
                        gateway="10.50.0.1", dns="")
    net = mang.cau_hinh_qemu(m, co_cloud_init=False, mac="BC:24:11:48:D8:66")["net0"]
    assert "firewall=1" in net
    assert "bridge=vmbr1" in net
