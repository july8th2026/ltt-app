"""Treo khan cap mot may khach — dung khi co bao cao lam dung.

    python tools\\vps_treo_khan.py --xem
    python tools\\vps_treo_khan.py --may <instance_id|ip|vmid> --ly-do "spam mail"
    python tools\\vps_treo_khan.py --may <...> --bo-treo

## Vi sao la CONG CU dong lenh, khong phai mot nut trong trang admin

Them mot `ModelView` cho bang cua app vao `server/admin.py` la viet cung ten app
vao nen tang -- dung thu hop dong app cam. Duong dung la mo rong hop dong (khai
admin view trong manifest), va do la mot thay doi lon hon thu viec nay dang can.

Nen no o day, cung cho voi `vps_doctor.py` va `vps_them_cong_vao.py`.

## Treo o day lam DU BA viec, khong chi doi mot cot

1. **Tat may** tren Proxmox -- treo ma may van chay thi "treo" chi la mot nhan;
2. **Ham toc** dia chi tren router -- neu may khong tat duoc (Proxmox khong tra
   loi) thi it nhat luu luong cua no bi cat xuong con 1 MB/s;
3. **Ghi so** trang thai + han xoa + su kien -- de con dau vet tra lai duoc.

Thu tu do la co y: viec cang chac chan thanh cong thi lam cang som.
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

# Console Windows mac dinh la cp1252, va `nhan.trang_thai()` tra tieng Viet co
# dau. Khong doi ma ra UTF-8 thi cong cu VO NGAY o dong `print` dau tien --
# `UnicodeEncodeError`, khong in duoc gi, va nguoi dang xu ly su co khong biet
# may da bi treo hay chua. Cung khuon voi `tools/check_i18n.py`.
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


def _tim(db, khoa: str):
    """Tim may theo instance_id, IP noi bo, IP cong khai, hoac vmid.

    Nhan ca bon vi nguoi dung cong cu nay dang xu ly su co, va thu ho cam trong
    tay co the la bat ky cai nao trong bon -- thuong la mot dia chi IP lay tu
    bao cao lam dung."""
    from sqlalchemy import select

    from apps.vps.tables import VpsInstance, VpsIp

    khoa = str(khoa or "").strip()
    m = db.get(VpsInstance, khoa)
    if m is not None:
        return m
    if khoa.isdigit():
        m = db.execute(select(VpsInstance).where(
            VpsInstance.vmid == int(khoa))).scalars().first()
        if m is not None:
            return m
    m = db.execute(select(VpsInstance).where(
        VpsInstance.ip_noi_bo == khoa)).scalars().first()
    if m is not None:
        return m
    ip = db.execute(select(VpsIp).where(VpsIp.dia_chi == khoa)).scalars().first()
    return db.get(VpsInstance, ip.instance_id) if ip is not None else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xem", action="store_true", help="liet ke may dang song")
    ap.add_argument("--may", help="instance_id, IP noi bo, IP cong khai, hoac vmid")
    ap.add_argument("--ly-do", default="", help="ghi vao nhat ky va hien cho khach")
    ap.add_argument("--bo-treo", action="store_true", help="bo ham toc, KHONG tu bat may")
    args = ap.parse_args()

    _nap_env()
    from sqlalchemy import select

    from apps.vps import nhan
    from apps.vps.services import billing, dieu_khien, provisioning
    from apps.vps.services import router as bo_dinh_tuyen
    from apps.vps.services.proxmox import ProxmoxError, client_tu_moi_truong
    from apps.vps.tables import VpsInstance, VpsIp
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        if args.xem or not args.may:
            ip_theo_may = {x.instance_id: x.dia_chi for x in
                           db.execute(select(VpsIp)).scalars()}
            dong = list(db.execute(select(VpsInstance).where(
                VpsInstance.trang_thai != "da_xoa")).scalars())
            if not dong:
                print("Khong co may nao dang song.")
                return 0
            for m in dong:
                print(f"  {m.id}  vmid={m.vmid}  {str(m.ip_noi_bo or '-'):<12} "
                      f"{ip_theo_may.get(m.id, '-'):<16} "
                      f"{nhan.trang_thai(m.trang_thai):<12} "
                      f"{'GIAM TOC' if m.bi_giam_toc else ''}")
            return 0

        may = _tim(db, args.may)
        if may is None:
            print(f"Khong tim thay may {args.may!r}")
            return 2

        if args.bo_treo:
            # KHONG tu bat may lai: neu no bi treo vi lam dung thi nguoi quyet
            # dinh bat lai phai la mot con nguoi, khong phai mot lenh don.
            if may.ip_noi_bo:
                bo_dinh_tuyen.client_tu_moi_truong().dat_giam_toc(
                    str(may.ip_noi_bo), False)
                may.bi_giam_toc = False
            provisioning.ghi_su_kien(db, may.id, "bo_treo_khan", boi="admin")
            db.commit()
            print(f"Da bo ham toc cho {may.id}. May VAN dang tat — bat lai bang tay.")
            return 0

        ly_do = args.ly_do or "Treo khan cap boi quan tri"

        # 1) Ham toc TRUOC: no gan nhu chac chan thanh cong, va no cat ngay luu
        #    luong cua may ke ca khi Proxmox khong tra loi o buoc sau.
        if may.ip_noi_bo:
            try:
                bo_dinh_tuyen.client_tu_moi_truong().dat_giam_toc(
                    str(may.ip_noi_bo), True)
                may.bi_giam_toc = True
                print(f"  da ham toc {may.ip_noi_bo}")
            except bo_dinh_tuyen.SshLenhError as exc:
                print(f"  KHONG ham toc duoc: {str(exc)[:90]}")

        # 2) Tat may + ghi so. `dieu_khien.treo` van ghi so ke ca khi Proxmox
        #    khong tat duoc — treo la quyet dinh cua nguoi, khong phai cua Proxmox.
        try:
            client = client_tu_moi_truong()
            dieu_khien.treo(db, may, client, ly_do=ly_do)
            print(f"  da tat may {may.vmid} va ghi so")
        except ProxmoxError as exc:
            billing.treo(db, may, ly_do)
            print(f"  Proxmox khong tra loi ({str(exc)[:60]}) — VAN da ghi so treo")

        provisioning.ghi_su_kien(db, may.id, "treo_khan", boi="admin", ly_do=ly_do)
        db.commit()
        print(f"XONG. {may.id} -> {nhan.trang_thai(may.trang_thai)}; "
              f"han xoa {may.xoa_sau}")
        return 0
    finally:
        gen.close()


if __name__ == "__main__":
    raise SystemExit(main())
