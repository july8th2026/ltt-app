"""Doi soat CONG cua cong vao VPS voi thu that — tu ben ngoai va tu ben trong.

🔴 Vi sao co tep nay (24/09/2026): ngay sau khi may khach that dau tien len,
   mot phep do tay phat hien `ssh` cua **cong vao** tra loi tren CA 11 dia chi
   IPv4, gom ca dia chi vua ban cho khach. Goc: `/etc/nftables.conf` viet
   `tcp dport 22 accept` — mot dieu kien **khong neu pham vi**, va pham vi mac
   dinh cua no la MOI dia chi may nay so huu.

   Khong phep kiem nao trong kho do duoc dieu do, vi no khong nam trong ma:
   no nam trong mot tep cau hinh tren mot may khac. Nen bai hoc khong phai
   "them mot test", ma la "viec do phai TU CHAY duoc" — day la cong cu do.

## No tra loi ba cau

1. **Cong 22 co dong tren moi IP da ban khong?** (do TU BEN NGOAI, khong tin
   cau hinh — cau hinh la y dinh, ket noi la su that)
2. **Luat chan co con dung dia chi quan tri hien tai khong?** — luat viet
   `ip daddr != <IP>`; neu OVH doi IP chinh cua cong vao thi con so do thanh
   mot con so go tay khong con y nghia, va cua mo lai trong im lang.
3. **RDP 3389 co con thong toi may khach khong?** — mot ban va an ninh lam hong
   duong ban hang la mot ban va se bi go, nen phai do ca chieu nguoc lai.

⛔ Khong sua gi. Chi do va noi.
"""
from __future__ import annotations

import argparse
import socket
import sys

CONG_QUAN_TRI = 22
CONG_RDP = 3389
CHO_GIAY = 6


def _cong_mo(ip: str, cong: int, cho: float = CHO_GIAY) -> bool:
    """Ket noi TCP that. `True` = bat tay duoc; timeout/refused = dong."""
    s = socket.socket()
    s.settimeout(cho)
    try:
        s.connect((ip, cong))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _doc_so_sach():
    """Tra (ip_quan_tri, [ip da ban], [ip duoc bao ve]) tu CSDL + profile."""
    from sqlalchemy import select

    from platform_core.db import get_session
    from apps.vps.tables import VpsGateway, VpsInfrastructureProfile, VpsIp

    for db in get_session():
        profile = db.execute(select(VpsInfrastructureProfile).where(
            VpsInfrastructureProfile.status == "ACTIVE",
            VpsInfrastructureProfile.is_default.is_(True))).scalars().first()
        if profile is None:
            raise SystemExit("khong co profile ACTIVE mac dinh")
        gw = db.execute(select(VpsGateway).where(
            VpsGateway.infrastructure_profile_id == profile.id)).scalars().first()
        if gw is None:
            raise SystemExit("profile khong co gateway")
        ban = [r.dia_chi for r in db.execute(select(VpsIp).where(
            VpsIp.state == "BOUND")).scalars()]
        giu = [r.dia_chi for r in db.execute(select(VpsIp).where(
            VpsIp.state == "QUARANTINED")).scalars()]
        return str(gw.ip_cong_khai), sorted(ban), sorted(giu)
    raise SystemExit("khong mo duoc CSDL")


def _luat_chan_tren_gateway(ip_quan_tri: str) -> tuple[bool, str]:
    """Luat chan co ton tai VA co neu dung dia chi quan tri hien tai khong."""
    from sqlalchemy import select

    from platform_core.db import get_session
    from apps.vps.tables import VpsInfrastructureProfile
    from apps.vps.services import backend_factory

    for db in get_session():
        profile = db.execute(select(VpsInfrastructureProfile).where(
            VpsInfrastructureProfile.status == "ACTIVE",
            VpsInfrastructureProfile.is_default.is_(True))).scalars().first()
        cli = backend_factory.gateway_backend(profile).client
        ra = str(cli._bash("nft list chain inet gw input"))
        break
    else:
        return False, "khong mo duoc CSDL"
    return luat_khop(ra, ip_quan_tri)


def luat_khop(chain_input: str, ip_quan_tri: str) -> tuple[bool, str]:
    """THUAN. Chain `input` co luat chan 22 dung dia chi quan tri hien tai khong.

    Tach khoi phan doc SSH de do duoc bang test: cai dang hong o day khong phai
    viec mo ket noi, ma la viec **so mot con so trong luat voi mot con so trong
    so sach** — dung cho ma mot lan doi IP se lam sai trong im lang.
    """
    for dong in chain_input.splitlines():
        d = dong.strip()
        if "dport 22 drop" in d and "daddr" in d:
            # `ip daddr != 51.79.166.36 tcp dport 22 drop ...`
            if f"!= {ip_quan_tri}" in d:
                return True, d
            return False, f"luat co, nhung neu dia chi KHAC voi gateway hien tai: {d}"
    return False, "KHONG co luat chan cong 22 nao trong chain input"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Doi soat cong cua cong vao VPS.")
    ap.add_argument("--khong-hoi-gateway", action="store_true",
                    help="bo qua phep doc luat qua SSH (chi do tu ben ngoai)")
    a = ap.parse_args(argv)

    ip_quan_tri, da_ban, duoc_giu = _doc_so_sach()
    loi: list[str] = []

    print(f"IP quan tri cong vao : {ip_quan_tri}")
    print(f"IP da ban cho may    : {len(da_ban)}")
    print(f"IP giu (VM noi bo)   : {len(duoc_giu)}")

    print("\n== 1. Cong 22 tren tung dia chi (do TU BEN NGOAI) ==")
    for ip in da_ban + duoc_giu:
        mo = _cong_mo(ip, CONG_QUAN_TRI)
        print(f"  {ip:18s} 22 {'MO  <-- LO CONG QUAN TRI' if mo else 'dong'}")
        if mo:
            loi.append(f"cong 22 MO tren {ip} — cong quan tri lo ra dia chi khong phai cua no")
    mo_qt = _cong_mo(ip_quan_tri, CONG_QUAN_TRI)
    print(f"  {ip_quan_tri:18s} 22 {'mo (dung)' if mo_qt else 'DONG <-- mat duong quan tri'}")
    if not mo_qt:
        loi.append(f"cong 22 DONG tren chinh IP quan tri {ip_quan_tri} — khong con duong vao")

    if not a.khong_hoi_gateway:
        print("\n== 2. Luat chan co neu dung dia chi quan tri hien tai ==")
        dat, chi_tiet = _luat_chan_tren_gateway(ip_quan_tri)
        print(f"  {'OK  ' if dat else 'LOI '} {chi_tiet}")
        if not dat:
            loi.append(f"luat chan cong 22 khong khop gateway hien tai: {chi_tiet}")

    print("\n== 3. RDP van thong toi may khach ==")
    for ip in da_ban:
        mo = _cong_mo(ip, CONG_RDP)
        # Chua cai Windows thi 3389 dong la DUNG — nen day la thong tin, khong phai loi.
        print(f"  {ip:18s} 3389 {'mo' if mo else 'dong (dung neu Windows chua cai)'}")

    print()
    if loi:
        for x in loi:
            print(f"LOI: {x}")
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
