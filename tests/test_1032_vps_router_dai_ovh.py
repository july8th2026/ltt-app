"""R25 (17/09/2026): router DHCP phai cap ca dai OVH 10.50.0.0/24.

Do tren production: VPS ban dau tien (VM 204) cai xong Windows nhung khong co mang.
Router `ltt-router-sgp` nhan DHCPDISCOVER cua MAC may khach va tra
"no address available", vi dnsmasq chi co dai 10.51.0.0/24 va eth1 khong co dia
chi nao trong 10.50.0.0/24 (dnsmasq chi cap cho mang noi truc tiep). Sua live:
dia chi phu 10.50.0.2/24 tren eth1 + dhcp-range co tag cho tung dai; ngay sau do
DHCPACK 10.50.0.50 va RDP 51.79.202.1:3389 mo tu Internet.

Tep nay ghim ban sua vao script dung router, de dung lai router khong mat no.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import textwrap

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = GOC / "tools" / "vps_gateway" / "cai-dat-router.sh"


def _script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _dnsmasq_conf() -> str:
    m = re.search(r"cat > /etc/dnsmasq\.d/ltt-vps\.conf <<EOF\n(.*?)\nEOF\n", _script(), re.S)
    assert m, "khong tim thay khoi cau hinh dnsmasq trong script"
    return m.group(1)


def test_moi_dai_mot_dhcp_range_co_tag_rieng():
    conf = _dnsmasq_conf()
    assert "dhcp-range=set:vultr,10.51.0.0,static,255.255.255.0,1h" in conf
    assert "dhcp-range=set:ovh,$MANG_OVH,static,255.255.255.0,1h" in conf
    assert 'MANG_OVH="10.50.0.0"' in _script()
    # Mot dhcp-range khong tag se lam option router bi ap nham dai.
    assert not re.search(r"^dhcp-range=(?!set:)", conf, re.M)


def test_gateway_cua_dai_OVH_la_host_proxmox_khong_phai_router():
    conf = _dnsmasq_conf()
    assert "dhcp-option=tag:ovh,option:router,$CUA_OVH" in conf
    assert "dhcp-option=tag:vultr,option:router,$CUA_KHACH" in conf
    assert 'CUA_OVH="10.50.0.1"' in _script()
    # Option router khong tag = gui 10.51.0.1 cho may OVH => co IP ma khong ra mang.
    assert not re.search(r"^dhcp-option=option:router", conf, re.M)


def test_eth1_duoc_gan_dia_chi_phu_OVH_va_ghi_vao_netplan_khong_apply():
    s = _script()
    assert 'DIA_CHI_OVH="10.50.0.2/24"' in s
    assert 'ip addr add "$DIA_CHI_OVH" dev "$NIC_KHACH"' in s
    assert "for np in /etc/netplan/*.yaml" in s
    assert not re.search(r"^\s*netplan apply", s, re.M), (
        "netplan apply dung lai card va cat SSH quan tri")


def test_ban_sao_luu_khong_nam_trong_dnsmasq_d():
    """dnsmasq doc MOI tep trong /etc/dnsmasq.d; do that 17/09: ban .bak lam no chet."""
    s = _script()
    assert not re.search(r"cp [^\n]*/etc/dnsmasq\.d/[^\n]*\.bak", s)
    assert '"/root/$(basename "$np").bak-r25"' in s


def test_dia_chi_phu_router_nam_ngoai_dai_cap_cho_may_khach():
    """Dai cap cho may khach OVH la octet 50-200 (vps_gateway ovh-sgp-1)."""
    octet = int('10.50.0.2/24'.split("/")[0].rsplit(".", 1)[1])
    assert not 50 <= octet <= 200


def test_doan_sua_netplan_them_dung_mot_dong_giu_thut_le(tmp_path):
    m = re.search(r"<<'PY'\n(.*?)\nPY\n", _script(), re.S)
    assert m, "khong tim thay doan python sua netplan"
    (tmp_path / "edit.py").write_text(m.group(1), encoding="utf-8")
    np = tmp_path / "50-cloud-init.yaml"
    np.write_text(textwrap.dedent("""\
        network:
            ethernets:
                eth1:
                    addresses:
                    - 10.51.0.1/24
                    match:
        """), encoding="utf-8")
    subprocess.run(["python", str(tmp_path / "edit.py"), str(np), "10.51.0.1/24",
                    "10.50.0.2/24"], check=True)
    lines = np.read_text(encoding="utf-8").splitlines()
    i = lines.index("            - 10.51.0.1/24")
    assert lines[i + 1] == "            - 10.50.0.2/24"
    assert sum("10.50.0.2/24" in line for line in lines) == 1


@pytest.mark.parametrize("bien", ["MANG_OVH", "CUA_OVH", "DIA_CHI_OVH"])
def test_bien_moi_duoc_khai_truoc_khi_dung(bien):
    s = _script()
    assert s.index(f'{bien}="') < s.index(f"${bien}")


def test_cloud_init_khong_duoc_sinh_lai_netplan_xoa_dia_chi_OVH():
    """Router co cloud-init: khong tat thi reboot sinh lai 50-cloud-init.yaml (do 17/09)."""
    s = _script()
    assert ("echo 'network: {config: disabled}' > "
            "/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg") in s
    assert s.index("99-disable-network-config.cfg") < s.index("for np in /etc/netplan/*.yaml")
