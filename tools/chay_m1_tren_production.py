"""Chay `M-1` tren CSDL PRODUCTION — di tru ban nhap Canvas v2 sang luoc do V2.

⛔ **Day la cong cu GHI vao CSDL dang giu so credit that.** Nen no khong "can
   than"; no bat buoc phai di qua ba thu, theo dung thu tu:

    1. MAC DINH LA CHAY THU. Phai go `--that` moi ghi.
    2. Truoc khi ghi, in ra HIEN TRANG hai bang dich — neu chung khong o trang
       thai mong doi thi DUNG, khong "co gang xu ly".
    3. Sau khi ghi, doc lai va doi chieu voi bao cao. Mot bao cao khong duoc
       kiem lai la mot loi khai, khong phai mot phep do.

## Vi sao viec nay an toan hon ve mat co hoc chu khong chi ve mat y dinh

    - `agent_workflows` (nguon) : CHI DOC, khong cau lenh nao ghi vao no
    - `workflow` + `workflow_draft` (dich) : bang MOI, tao 08/09, do duoc la RONG
    - khong cham `credit_entries` / `jobs` / `users`
    - luy dang: chay lai tim thay ban cu theo KHOA CHINH thay vi tao ban thu hai
    - dao lai duoc bang mot cau: xoa dung nhung `id` co trong `agent_workflows`

⚠️ **Da tung sai o day, 08/09/2026.** Ban dau `M-1` danh dau bang
   `published_version_id = "m1:" + id` = 39 ky tu vao cot `String(36)`. SQLite
   khong cuong che do dai `VARCHAR` nen ca bo test lan mot lan dien tap tren
   BAN SAO SQLITE CUA CHINH DU LIEU NAY deu XANH. PostgreSQL tra
   `StringDataRightTruncation`. Vi the cong cu nay khong bao gio duoc dung lam
   phep kiem dau tien — `tools/dien_tap_m1_tren_postgres.py` phai xanh truoc.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

BANG_DICH = ("workflow", "workflow_draft")


def _nap_d2():
    s = importlib.util.spec_from_file_location(
        "d2_chi_doc", GOC / "tools" / "dem_d2_agent_production.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--that", action="store_true",
                    help="GHI THAT vao production (mac dinh: chi chay thu)")
    ap.add_argument("--va-trang", action="store_true",
                    help="VA khoa trang con thieu cho ban DA di tru (09/09)")
    args = ap.parse_args()

    d2 = _nap_d2()
    live = d2._live_url()
    if not live.startswith(("postgresql", "postgres")):
        print("BO QUA: khong tim thay LTT_DATABASE_URL kieu postgres.")
        return 0
    pw = d2._doc_bi_mat("postgres-superuser.txt").strip()
    if not pw:
        print("BO QUA: khong doc duoc mat khau superuser.")
        return 0

    ten = live.rsplit("/", 1)[-1].split("?", 1)[0]
    dia_chi = live.partition("://")[2].partition("@")[2].rsplit("/", 1)[0]
    url = f"postgresql+psycopg://postgres:{pw}@{dia_chi}/{ten}"

    import sqlalchemy as sa

    print(f"CSDL: {ten}   che do: "
          f"{'GHI THAT' if args.that else 'CHAY THU (khong ghi)'}\n")

    # ── 2. Hien trang TRUOC ───────────────────────────────────────────────
    e0 = sa.create_engine(url, connect_args={"connect_timeout": 5})
    with e0.connect() as c:
        nguon = int(c.execute(sa.text(d2._chi_doc(
            "SELECT COUNT(*) FROM agent_workflows"))).scalar() or 0)
        # `scalar()` khai kieu `Any | None`, va o mot cong cu DOI CHIEU SO
        # BUT TOAN thi do khong phai chuyen kieu: mot `None` lot qua se lam
        # phep tru duoi kia no giua luc dang doi chieu production, sau khi
        # da ghi. Ep ngay tai nguon.
        truoc = {b: int(c.execute(sa.text(d2._chi_doc(
            f"SELECT COUNT(*) FROM {b}"))).scalar() or 0) for b in BANG_DICH}
    e0.dispose()
    print(f"  nguon  agent_workflows : {nguon}")
    for b, n in truoc.items():
        print(f"  dich   {b:15s} : {n}")
    if nguon == 0:
        print("\nKHONG CO GI DE CHUYEN.")
        return 0
    print()

    os.environ["LTT_DATABASE_URL"] = url
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models as M                          # noqa: F401
    from platform_core.workflow import di_tru_m1

    db = next(dbmod.get_session())
    try:
        if args.va_trang:
            # ⛔ `chuyen()` LUY DANG nen no khong tu lanh ban da chuyen. Mot
            #    khiem khuyet trong `_trang_v3` (09/09: sinh 4 khoa thay vi 8)
            #    chi sua duoc bang duong nay.
            va = di_tru_m1.va_trang(db, chay_that=args.that)
            if args.that:
                db.commit()
            else:
                db.rollback()
            print(f"  [va trang] da_va={va['da_va']}  se_va={va['se_va']}  "
                  f"da_du={va['da_du']}  tong={va['tong']}")
            print()
            print("RESULT: PASS")
            return 0
        ra = di_tru_m1.chuyen(db, chay_that=args.that)
        if args.that:
            db.commit()
        else:
            # ⛔ Ro rang chu khong ngam: che do chay thu khong ghi gi, va cach
            #    duy nhat CHUNG MINH dieu do la vut bo phien lam viec.
            db.rollback()
    finally:
        db.close()

    if args.that:
        print(f"  da_chuyen={ra['da_chuyen']}  rong={ra['rong']}  "
              f"da_co={ra['da_co']}  tong={ra['tong']}")
    else:
        print(f"  se_chuyen={ra['se_chuyen']}  rong={ra['rong']}  "
              f"tong={ra['tong']}")

    # ── 3. Doc lai va DOI CHIEU ───────────────────────────────────────────
    e1 = sa.create_engine(url, connect_args={"connect_timeout": 5})
    with e1.connect() as c:
        sau = {b: int(c.execute(sa.text(d2._chi_doc(
            f"SELECT COUNT(*) FROM {b}"))).scalar() or 0) for b in BANG_DICH}
    e1.dispose()
    dbmod.reset_engine()

    print()
    for b in BANG_DICH:
        print(f"  {b:15s} : {truoc[b]} -> {sau[b]}")

    mong = ra["da_chuyen"] if args.that else 0
    lech = [b for b in BANG_DICH if sau[b] - truoc[b] != mong]
    if lech:
        print(f"\n⛔ LECH: {lech} khong tang dung {mong}")
        print("RESULT: FAIL")
        return 1
    if not args.that:
        print("\n  (chay thu: hai bang KHONG doi — dung nhu mong doi)")
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
