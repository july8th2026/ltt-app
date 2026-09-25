"""Keo cac may VPS DA CO ve chuan danh tinh 25/09/2026.

Ba hang muc, do that khi so voi Vultr:

1. `cpu host` — bo `kvm64` generic (giong het nhau tren moi may, va cham hon).
   ⚠️ Chi co hieu luc sau MOT chu ky tat/bat. ⛔ Cong cu nay **khong tu tat may
   khach**: chon thoi diem dung may la viec cua chu may, khong phai cua ta.
2. `ipfilter`/`macfilter` — chong mot khach ARP/IP spoof khach khac tren cung
   `vmbr1`. Co hieu luc **ngay**, khong can tat may.
3. rDNS — A record tren Cloudflare roi PTR o OVH. Thu tu la bat buoc (OVH doi
   forward-confirm).

Chay lai duoc nhieu lan: moi buoc kiem truoc khi ghi.

    python tools/vps_chuan_hoa.py            # chi BAO CAO, khong doi gi
    python tools/vps_chuan_hoa.py --ap       # ap that
"""
from __future__ import annotations

import argparse
import sys


def _may_va_ip(db):
    from sqlalchemy import select

    from apps.vps.tables import VpsInstance, VpsIp

    may = db.execute(select(VpsInstance).where(
        VpsInstance.trang_thai != "da_xoa")).scalars().all()
    ip = {r.instance_id: r.dia_chi for r in db.execute(
        select(VpsIp).where(VpsIp.state == "BOUND")).scalars() if r.instance_id}
    return may, ip


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Chuan hoa danh tinh VPS da co.")
    ap.add_argument("--ap", action="store_true", help="ap that (mac dinh chi bao cao)")
    a = ap.parse_args(argv)

    from sqlalchemy import select

    from platform_core.db import get_session
    from apps.vps import jobs
    from apps.vps.tables import VpsInfrastructureProfile
    from apps.vps.services import backend_factory, dns_cloudflare, rdns

    for db in get_session():
        profile = db.execute(select(VpsInfrastructureProfile).where(
            VpsInfrastructureProfile.status == "ACTIVE",
            VpsInfrastructureProfile.is_default.is_(True))).scalars().first()
        if profile is None:
            print("khong co profile ACTIVE mac dinh")
            return 1
        cli = backend_factory.compute_backend(profile).client
        may, ip_theo_may = _may_va_ip(db)

        print(f"{'vmid':>6}  {'ten':<16} {'cpu':<10} {'firewall':<10} "
              f"{'ip':<16} {'ptr'}")
        cho_tat_bat, da_sua = [], 0
        for m in sorted(may, key=lambda x: x.vmid or 0):
            if not m.vmid:
                continue
            node = cli.config.node
            cfg = cli._goi("GET", f"/nodes/{node}/qemu/{int(m.vmid)}/config")
            d = cfg.get("data", cfg) if isinstance(cfg, dict) else cfg
            cpu = str(d.get("cpu") or "kvm64(mac dinh)")
            fw = cli.doc_firewall(int(m.vmid))
            fw_ok = all(str(fw.get(k, "")).lower() in ("1", "true")
                        for k in ("enable", "ipfilter", "macfilter"))
            ip = ip_theo_may.get(m.id, "")
            # ⛔ Ba trang thai, khong phai `bool`: "OVH da luu" va "the gioi thay
            #    duoc" la hai su that khac nhau — do that 25/09, OVH luu xong ma
            #    `nslookup` van khong tra gi sau mot gio.
            ptr = "-"
            if ip:
                tt, _ = rdns.trang_thai_ptr(
                    backend_factory.ovh_inventory_client(profile), ip)
                ptr = {rdns.DA_THAY: "da thay",
                       rdns.DANG_LAN: "dang lan truyen",
                       rdns.CHUA_DAT: "CHUA dat"}[tt]
            print(f"{m.vmid:>6}  {str(m.ten)[:16]:<16} {cpu:<10} "
                  f"{'dat' if fw_ok else 'CHUA':<10} {ip or '-':<16} {ptr}")

            if not a.ap:
                continue
            if cpu.startswith("kvm64"):
                cli.dat_cau_hinh(int(m.vmid), cpu="host")
                cho_tat_bat.append(m.vmid)
                da_sua += 1
            if not fw_ok:
                jobs._dat_firewall_may_khach(cli, int(m.vmid))
                da_sua += 1
            if ip:
                rdns.dat_rdns(dns_cloudflare.client_tu_moi_truong(),
                              backend_factory.ovh_inventory_client(profile), ip)

        if a.ap:
            print(f"\nda sua {da_sua} muc")
            if cho_tat_bat:
                print("⚠️ CPU chi doi sau mot chu ky TAT/BAT — may dang cho: "
                      + ", ".join(str(v) for v in cho_tat_bat))
                print("   (cong cu KHONG tu tat may khach)")
        else:
            print("\n(chi bao cao — them `--ap` de ap that)")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
