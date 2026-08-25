"""Dung lai cong vao sau khi no chet — phan di qua API (H39/G9b).

    python tools\\vps_dung_lai_cong_vao.py --xem
    python tools\\vps_dung_lai_cong_vao.py --cong sgp-1 --may-moi <instance_id_vultr> \\
        --ip-moi 45.32.x.y

## Viec nay chia lam hai nua, va day la nua THU HAI

Nua thu nhat chay tren chinh con VPS moi:
`tools/vps_gateway/dung-lai-cong-vao.sh` + `cai-dat-cong-vao.sh` — WireGuard,
nftables, chuyen tiep goi, unit phat lai duong.

Nua thu hai la tep nay, va no lam ba viec **khong lam bang shell duoc**:

1. **Gan lai Reserved IP** sang may moi. Day la ly do ca ke hoach nay kha thi:
   Reserved IP cua Vultr **khong chet theo may**. Go khoi may cu, gan vao may
   moi, dia chi giu nguyen -- khach khong phai doi gi.
2. **Mo lai duong NAT** cho tung khach, doc tu `vps_ip` trong CSDL. Bo luat tren
   cong vao moi la bang rong; khong buoc nay thi IP da gan nhung khong dan ve
   dau ca.
3. **Cap nhat `vps_gateway`** — `ip_cong_khai`, `nha_cung_cap_id`, `wg_endpoint`.
   Bo qua buoc nay thi lan mua IP tiep theo gan vao con may DA CHET.

## Vi sao KHONG tu tao instance Vultr

Tao may la thao tac tieu tien va khong hoan tac duoc phan da tinh. Tao nham mot
con la mot dong tien nho nhung deu, va no chay am tham. Nen buoc do de nguoi lam
-- mot cu bam tren bang dieu khien Vultr, hoac mot lenh `curl` -- roi dua id vao
day. `services/vultr.py` co y **khong** co ham tao/xoa instance.
"""
from __future__ import annotations

import argparse
import io
import os
import pathlib
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)


def _nap_env() -> None:
    goc = pathlib.Path(__file__).resolve().parents[1]
    for tep in (r"C:\LTTPlatform\secrets\app.env", str(goc / "secrets" / "app.env")):
        p = pathlib.Path(tep)
        if not p.exists():
            continue
        for d in p.read_text(encoding="utf-8-sig").splitlines():
            if "=" in d and not d.strip().startswith("#"):
                k, v = d.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xem", action="store_true",
                    help="liet ke cong vao, IP va duong dang co — khong sua gi")
    ap.add_argument("--cong", help="ten cong vao trong bang vps_gateway")
    ap.add_argument("--may-moi", help="instance_id ben Vultr cua con VPS MOI")
    ap.add_argument("--ip-moi", help="IP chinh cua con VPS moi")
    args = ap.parse_args()

    _nap_env()
    from sqlalchemy import select

    from apps.vps.services import gateway as cong_vao
    from apps.vps.services import vultr as nha_cung_cap
    from apps.vps.tables import VpsGateway, VpsInstance, VpsIp
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        khach = nha_cung_cap.client_tu_moi_truong()

        if args.xem or not args.cong:
            print("== Cong vao trong CSDL ==")
            for g in db.execute(select(VpsGateway)).scalars():
                print(f"  {g.ten:<10} {g.ip_cong_khai:<16} "
                      f"nha_cung_cap_id={g.nha_cung_cap_id or '(trong)'}")
            print("\n== Reserved IP ben Vultr ==")
            for r in khach.danh_sach_ip():
                print(f"  {r.get('subnet'):<16} id={r.get('id')} "
                      f"nhan={r.get('label')!r} gan_vao={r.get('instance_id') or '(trong)'}")
            print("\n== Duong phai mo lai (tu CSDL) ==")
            n = 0
            for ip in db.execute(select(VpsIp)).scalars():
                may = db.get(VpsInstance, ip.instance_id) if ip.instance_id else None
                print(f"  {ip.dia_chi:<16} -> {may.ip_noi_bo if may else '(khong chu)'}")
                n += 1
            if not n:
                print("  (khong co) — chua ban may nao")
            return 0

        if not args.may_moi or not args.ip_moi:
            print("Thieu --may-moi hoac --ip-moi.")
            return 2

        g = db.execute(select(VpsGateway)
                       .where(VpsGateway.ten == args.cong)).scalars().first()
        if g is None:
            print(f"Khong co cong vao {args.cong!r}")
            return 2

        print(f"== 1. Gan lai Reserved IP sang may moi {args.may_moi} ==")
        da_gan = 0
        for ip in db.execute(select(VpsIp)
                             .where(VpsIp.gateway_id == g.id)).scalars():
            if not ip.vultr_id:
                print(f"  {ip.dia_chi}: chua co vultr_id, bo qua")
                continue
            try:
                # Go truoc: mot Reserved IP chi gan duoc vao MOT instance. May cu
                # co the da chet nhung Vultr van coi la dang gan.
                khach.go_ip(ip.vultr_id)
            except nha_cung_cap.VultrError:
                pass                      # chua gan vao dau — khong phai loi
            khach.gan_ip(ip.vultr_id, args.may_moi)
            print(f"  {ip.dia_chi}: da gan")
            da_gan += 1
        print(f"  --> {da_gan} dia chi")

        print("\n== 2. Cap nhat cong vao trong CSDL ==")
        # Lam TRUOC khi mo duong: `gateway.client_tu_moi_truong()` doc
        # LTT_VPS_GATEWAY_HOST tu moi truong, nen nguoi chay phai sua bien do
        # roi moi chay tiep. Ghi vao CSDL o day de lan mua IP sau khong gan vao
        # con may da chet.
        g.ip_cong_khai = args.ip_moi
        g.nha_cung_cap_id = args.may_moi
        g.wg_endpoint = f"{args.ip_moi}:51820"
        db.commit()
        print(f"  {g.ten}: ip_cong_khai={g.ip_cong_khai} "
              f"nha_cung_cap_id={g.nha_cung_cap_id}")

        moi_truong = os.environ.get("LTT_VPS_GATEWAY_HOST", "")
        if moi_truong != args.ip_moi:
            print(f"\n  ⚠️  LTT_VPS_GATEWAY_HOST dang la {moi_truong!r}, khong phai "
                  f"{args.ip_moi!r}.")
            print("      Sua no trong secrets/app.env ROI chay lai buoc 3 duoi day,")
            print("      neu khong cac lenh nftables se di toi con may CU.")
            return 1

        print("\n== 3. Mo lai duong NAT cho tung khach ==")
        rt = cong_vao.client_tu_moi_truong()
        da_mo = 0
        for ip in db.execute(select(VpsIp)
                             .where(VpsIp.gateway_id == g.id)).scalars():
            may = db.get(VpsInstance, ip.instance_id) if ip.instance_id else None
            if may is None or not may.ip_noi_bo:
                print(f"  {ip.dia_chi}: khong co may nao dung, bo qua")
                continue
            rt.mo_duong(ip.dia_chi, str(may.ip_noi_bo))
            print(f"  {ip.dia_chi} -> {may.ip_noi_bo}")
            da_mo += 1
        print(f"  --> {da_mo} duong")

        print("\n== 4. Doi chieu voi bo luat THAT tren cong vao ==")
        that = rt.danh_sach_duong()
        print(f"  map `vao` tren cong vao: {that or '(rong)'}")
        thieu = [ip.dia_chi for ip in db.execute(
            select(VpsIp).where(VpsIp.gateway_id == g.id)).scalars()
            if ip.instance_id and ip.dia_chi not in that]
        if thieu:
            print(f"  ⚠️  CON THIEU: {thieu}")
            return 1
        print("  khop.")
        return 0
    finally:
        gen.close()


if __name__ == "__main__":
    raise SystemExit(main())
