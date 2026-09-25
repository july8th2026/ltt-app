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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _nap_env(duong: str) -> None:
    """Nap `secrets\app.env` vao os.environ neu env chua co san.

    Cong cu van hanh duoc goi bang tay tren may chu, noi bi mat CHI nam trong
    app.env (dich vu duoc nssm nuong env luc cai). Khong nap thi nguoi chay
    nhan mot traceback `DatabaseNotConfigured` thay vi mot cau bao ro rang.
    """
    import os

    tep = Path(duong)
    if os.environ.get("LTT_DATABASE_URL") or not tep.exists():
        return
    for dong in tep.read_text(encoding="utf-8-sig").splitlines():
        dong = dong.strip()
        if dong and not dong.startswith("#") and "=" in dong:
            ten, gia = dong.split("=", 1)
            os.environ.setdefault(ten.strip(), gia.strip())

# ⭐ MOT nguon cho ca cong cu nay lan vong bao tri (`bao_tri._kiem_cong_quan_tri`).
#    Hai ban do se lech, va chung se lech o cho quyet dinh "co bi lo khong".
from apps.vps.services.kiem_cong import (CONG_QUAN_TRI, CONG_RDP,
                                         cong_mo as _cong_mo, luat_khop)


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Doi soat cong cua cong vao VPS.")
    ap.add_argument("--khong-hoi-gateway", action="store_true",
                    help="bo qua phep doc luat qua SSH (chi do tu ben ngoai)")
    ap.add_argument("--env", default=r"C:\LTTPlatform\secrets\app.env",

                      help="tep bi mat de nap khi env chua co san")
    a = ap.parse_args(argv)

    _nap_env(a.env)

    ip_quan_tri, da_ban, duoc_giu = _doc_so_sach()
    loi: list[str] = []

    print(f"IP quan tri cong vao : {ip_quan_tri}")
    print(f"IP da ban cho may    : {len(da_ban)}")
    print(f"IP giu (VM noi bo)   : {len(duoc_giu)}")

    print("\n== 1. Cong 22 tren tung dia chi (do TU BEN NGOAI) ==")
    for ip in da_ban + duoc_giu:
        mo, vi_sao = _cong_mo(ip, CONG_QUAN_TRI)
        print(f"  {ip:18s} 22 {'MO  <-- LO CONG QUAN TRI' if mo else f'dong ({vi_sao})'}")
        if mo:
            loi.append(f"cong 22 MO tren {ip} — cong quan tri lo ra dia chi khong phai cua no")
    mo_qt, vi_sao_qt = _cong_mo(ip_quan_tri, CONG_QUAN_TRI)
    print(f"  {ip_quan_tri:18s} 22 "
          f"{'mo (dung)' if mo_qt else f'DONG <-- mat duong quan tri ({vi_sao_qt})'}")
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
        mo, vi_sao = _cong_mo(ip, CONG_RDP)
        # Chua cai Windows thi 3389 dong la DUNG — nen day la thong tin, khong phai loi.
        print(f"  {ip:18s} 3389 "
              f"{'mo' if mo else f'dong ({vi_sao}) — dung neu Windows chua cai'}")

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
