"""Khai mot cong vao (gateway) vao CSDL — viec bat buoc truoc khi ban duoc may.

Khong co dong `vps_gateway` nao thi app tu choi tao may, va tu choi la DUNG: mot
VM chay tren dia ma khong ai vao duoc thi khong phai san pham. Nhung tu choi do
hien ra la mot loi kho hieu neu khong biet phai khai o dau -- nen co tep nay.

Chay lai duoc: khai lai cung `--ten` thi CAP NHAT dong cu chu khong tao dong hai.

    python tools\vps_them_cong_vao.py --xem
    python tools\vps_them_cong_vao.py --ten sgp-1 --ip 45.32.114.249 \
        --vung sgp --bridge vmbr1 --subnet 10.51.0.0/24 --gw-noi-bo 10.51.0.1

`--nha-cung-cap-id` la id cua chinh cong vao ben Vultr. Thieu no thi moi lan gan
Reserved IP phai tra theo nhan, va doi ten tren bang dieu khien la app khong tim
thay nua. Khong khai thi tep nay TU TRA -- xem `--tim-id`.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")


def _nap_env() -> None:
    for tep in (r"C:\LTTPlatform\secrets\app.env",
                str(pathlib.Path(__file__).resolve().parents[1] / "secrets" / "app.env")):
        p = pathlib.Path(tep)
        if not p.exists():
            continue
        for d in p.read_text(encoding="utf-8-sig").splitlines():
            if "=" in d and not d.strip().startswith("#"):
                k, v = d.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xem", action="store_true", help="chi liet ke, khong sua")
    ap.add_argument("--ten")
    ap.add_argument("--vung", default="sgp")
    ap.add_argument("--ip", help="IP cong khai cua chinh cong vao")
    ap.add_argument("--ten-mien", default="")
    ap.add_argument("--bridge", default="vmbr1")
    ap.add_argument("--subnet", default="10.51.0.0/24")
    ap.add_argument("--gw-noi-bo", default="10.51.0.1")
    ap.add_argument("--dns", default="1.1.1.1 8.8.8.8")
    ap.add_argument("--mtu", type=int, default=1420)
    ap.add_argument("--octet-dau", type=int, default=50)
    ap.add_argument("--octet-cuoi", type=int, default=200)
    ap.add_argument("--nha-cung-cap-id", default="")
    ap.add_argument("--tim-id", action="store_true",
                    help="tra id ben Vultr theo --ten roi dien vao")
    ap.add_argument("--khong-ban-ip-rieng", action="store_true")
    args = ap.parse_args()

    _nap_env()
    from sqlalchemy import select

    from apps.vps.services import mang
    from apps.vps.tables import VpsGateway
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        if args.xem or not args.ten:
            dong = list(db.execute(select(VpsGateway)).scalars())
            if not dong:
                print("CHUA CO CONG VAO NAO — app se tu choi tao may.")
                return 1
            for g in dong:
                print(f"  {g.ten:<10} {g.ip_cong_khai:<16} {g.bridge} "
                      f"{g.subnet_cidr} gw={g.subnet_gw} mtu={g.mtu} "
                      f"octet {g.octet_dau}-{g.octet_cuoi} "
                      f"({mang.so_dia_chi(g)} dia chi) "
                      f"nha_cung_cap_id={g.nha_cung_cap_id or '(trong)'} "
                      f"{'nhan may moi' if g.dang_nhan_may_moi else 'DANG RUT'}")
            return 0

        if not args.ip:
            print("thieu --ip"); return 2

        ncc_id = args.nha_cung_cap_id
        if args.tim_id and not ncc_id:
            from apps.vps.services import vultr
            ncc_id = str(vultr.client_tu_moi_truong()
                         .instance_theo_nhan(args.ten)["id"])
            print(f"  tim thay id ben Vultr: {ncc_id}")

        g = db.execute(select(VpsGateway)
                       .where(VpsGateway.ten == args.ten)).scalars().first()
        moi = g is None
        if moi:
            g = VpsGateway(ten=args.ten)
            db.add(g)
        g.vung = args.vung
        g.ip_cong_khai = args.ip
        g.ten_mien = args.ten_mien
        g.wg_endpoint = f"{args.ip}:51820"
        g.bridge = args.bridge
        g.subnet_cidr = args.subnet
        g.subnet_gw = args.gw_noi_bo
        g.dns = args.dns
        g.mtu = args.mtu
        g.octet_dau = args.octet_dau
        g.octet_cuoi = args.octet_cuoi
        g.cho_phep_ip_rieng = not args.khong_ban_ip_rieng
        if ncc_id:
            g.nha_cung_cap_id = ncc_id

        # Kiem TRUOC khi commit: mot cong vao khai sai chi lo ra luc mot khach
        # bam mua, va luc do loi hien ra tren mat ho.
        mang.mang_cho_may(g, _dia_chi_thu(g))
        db.commit()
        print(("DA THEM " if moi else "DA CAP NHAT ") + g.ten +
              f"  ({mang.so_dia_chi(g)} dia chi cap duoc)")
        return 0
    finally:
        gen.close()


def _dia_chi_thu(g) -> str:
    from apps.vps.services import mang
    return next(iter(mang.dai_dia_chi(g)))


if __name__ == "__main__":
    raise SystemExit(main())
