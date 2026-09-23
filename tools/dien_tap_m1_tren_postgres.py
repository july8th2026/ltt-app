"""Dien tap `M-1` tren PostgreSQL THAT, voi du lieu that cua production.

🔴 **VI SAO CONG CU NAY TON TAI.** `tools/do_migration_tren_postgres.py` dong
   duoc mot truc: *migration* co chay tren PostgreSQL khong. No **khong** dong
   truc thu hai: *ma chay luc runtime* co chay tren PostgreSQL khong.

   Do 08/09/2026 — `M-1` danh dau ban da di tru bang

       published_version_id = "m1:" + id       # 3 + 36 = 39 ky tu
       platform_core.models.Workflow.published_version_id = String(36)

   SQLite **khong cuong che** do dai `VARCHAR`; PostgreSQL co:

       value too long for type character varying(36)

   Nen phep dien tap tren mot ban sao SQLite cua **chinh du lieu production**
   van XANH, va `M-1` chi chet o lan chay that. Cung ho voi `BOOLEAN DEFAULT 1`
   da song sot qua ba commit — khac o cho ca do la DDL, con ca nay la DML.

## ⛔ RAO AN TOAN — giong `do_migration_tren_postgres.py`, va vi cung ly do

CSDL production ten `lttplatform`, dang giu **so credit that**. Cong cu nay goi
`CREATE`/`INSERT` nen no phai CHUNG MINH cai no cham la CSDL vut di:

    1. ten CSDL PHAI chua "test"        — production khong tinh co mang chu do
    2. ten CSDL PHAI KHAC ten dang chay — kiem theo TEN, khong theo chuoi URL
    3. doc production CHI qua `_chi_doc` — SELECT-only, mot cau, khong tu khoa ghi

⇒ Duong ghi va duong doc la HAI ket noi khac nhau toi HAI CSDL khac nhau.
  Production khong bao gio nam tren duong ghi.

🔴 23/09/2026: CSDL nhap cua moi cay tung KHONG bao gio bi xoa -> worktree go
   di la CSDL mo coi (132 CSDL, PostgreSQL fsync 44.651 tep sau moi lan sap).
   Gio cuoi luot xoa CSDL nhap cua CHINH cay nay qua
   `pg_ten_cay.cau_xoa_csdl_test` (ten tinh lai, khong FORCE); `--giu` thi giu.
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

HAU_TO = "_m1_dientap_test"

#: Cot doc tu `agent_workflows`. Khai tuong minh chu khong `SELECT *`: mot cot
#: them vao sau nay se lam `AgentWorkflow(**hang)` no, va no ra mot loi noi ro
#: thay vi mot hang thieu du lieu.
COT = ("id", "user_id", "name", "goal", "plan_version", "nodes", "edges",
       "document", "status", "budget_max", "revision")


def _nap_d2():
    s = importlib.util.spec_from_file_location(
        "d2_chi_doc", GOC / "tools" / "dem_d2_agent_production.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _doc_production(d2) -> list[dict]:
    """Doc `agent_workflows` tu production — CHI DOC, qua rao `_chi_doc`."""
    import sqlalchemy as sa

    live = d2._live_url()
    if not live.startswith(("postgresql", "postgres")):
        return []
    pw = d2._doc_bi_mat("postgres-superuser.txt").strip()
    if not pw:
        return []
    ten = live.rsplit("/", 1)[-1].split("?", 1)[0]
    dia_chi = live.partition("://")[2].partition("@")[2].rsplit("/", 1)[0]
    e = sa.create_engine(f"postgresql+psycopg://postgres:{pw}@{dia_chi}/{ten}",
                         connect_args={"connect_timeout": 5})
    try:
        with e.connect() as c:
            hang = c.execute(sa.text(d2._chi_doc(
                f"SELECT {', '.join(COT)} FROM agent_workflows"))).mappings().all()
    finally:
        e.dispose()
    return [dict(h) for h in hang]


def _url_nhap(d2, ten: str) -> str:
    live = d2._live_url()
    pw = d2._doc_bi_mat("postgres-superuser.txt").strip()
    dia_chi = live.partition("://")[2].partition("@")[2].rsplit("/", 1)[0]
    return f"postgresql+psycopg://postgres:{pw}@{dia_chi}/{ten}"


def _dung_url(ten_that: str, ten_dang_chay: str) -> None:
    if "test" not in ten_that:
        raise SystemExit(f"⛔ TU CHOI: {ten_that!r} khong chua 'test'.")
    if ten_that == ten_dang_chay:
        raise SystemExit(f"⛔ TU CHOI: {ten_that!r} la CSDL dang chay.")


def _tao_neu_thieu(d2, url: str, ten: str) -> None:
    import sqlalchemy as sa

    try:
        e = sa.create_engine(url, connect_args={"connect_timeout": 5})
        with e.connect():
            pass
        e.dispose()
        return
    except Exception as loi:                                # noqa: BLE001
        print(f"  (chua noi duoc toi {ten}: {type(loi).__name__})")

    e = sa.create_engine(_url_nhap(d2, "postgres"), isolation_level="AUTOCOMMIT",
                         connect_args={"connect_timeout": 5})
    try:
        with e.connect() as c:
            c.execute(sa.text(f'CREATE DATABASE "{ten}"'))
        print(f"  DA TAO CSDL {ten}.")
    except Exception as loi:                                # noqa: BLE001
        if "already exists" not in str(loi):
            raise
    finally:
        e.dispose()


def _xoa_csdl_nhap(d2, ten_dang_chay: str) -> None:
    """Xoa CSDL nhap cua CHINH cay nay. Hong thi noi, khong doi ket luan."""
    import sqlalchemy as sa
    from pg_ten_cay import cau_xoa_csdl_test

    cau = cau_xoa_csdl_test(ten_dang_chay, HAU_TO, GOC)
    e = sa.create_engine(_url_nhap(d2, "postgres"), isolation_level="AUTOCOMMIT",
                         connect_args={"connect_timeout": 5})
    try:
        with e.connect() as c:
            c.execute(sa.text(cau))
        print("  (da xoa CSDL nhap - dung `--giu` neu muon giu lai)")
    except Exception as loi:                                # noqa: BLE001
        print(f"  !! khong xoa duoc CSDL nhap ({type(loi).__name__}) - "
              "`python tools/don_csdl_test.py` se liet ke no")
    finally:
        e.dispose()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--giu", action="store_true", help="giu lai CSDL nhap sau khi chay")
    args = ap.parse_args()

    d2 = _nap_d2()
    live = d2._live_url()
    if not live.startswith(("postgresql", "postgres")):
        print("BO QUA: khong tim thay LTT_DATABASE_URL kieu postgres.")
        return 0

    ban_ghi = _doc_production(d2)
    print(f"doc tu production (CHI DOC): {len(ban_ghi)} hang `agent_workflows`")
    if not ban_ghi:
        print("BO QUA: khong doc duoc du lieu nguon.")
        return 0

    ten_dang_chay = live.rsplit("/", 1)[-1].split("?", 1)[0]
    # Moi cay mot CSDL test rieng (su co 17/09, tools/pg_ten_cay.py).
    sys.path.insert(0, str(GOC / "tools"))
    from pg_ten_cay import ten_csdl_test
    ten = ten_csdl_test(ten_dang_chay, HAU_TO, GOC)
    _dung_url(ten, ten_dang_chay)
    url = _url_nhap(d2, ten)
    print(f"CSDL dang chay : {ten_dang_chay}   (KHONG cham toi)")
    print(f"CSDL nhap      : {ten}")
    _tao_neu_thieu(d2, url, ten)

    try:
        return _dien_tap(url, ban_ghi)
    finally:
        if not args.giu:
            _xoa_csdl_nhap(d2, ten_dang_chay)


def _dien_tap(url: str, ban_ghi: list[dict]) -> int:
    """Than dien tap. Engine dong (`reset_engine`) truoc khi `main` xoa CSDL nhap."""
    os.environ["LTT_DATABASE_URL"] = url
    import platform_core.db as dbmod
    dbmod.reset_engine()
    try:
        return _dien_tap_tren(dbmod, ban_ghi)
    finally:
        dbmod.reset_engine()


def _dien_tap_tren(dbmod, ban_ghi: list[dict]) -> int:
    import platform_core.models as M

    e = dbmod.get_engine()
    dbmod.Base.metadata.drop_all(e)
    dbmod.Base.metadata.create_all(e)
    db = next(dbmod.get_session())

    for h in ban_ghi:
        db.add(M.AgentWorkflow(**h))
    db.commit()
    print(f"  da nap {db.query(M.AgentWorkflow).count()} hang vao CSDL nhap\n")

    from platform_core.workflow import di_tru_m1

    thu = di_tru_m1.chuyen(db)
    db.commit()
    tao_sau_chay_thu = db.query(M.Workflow).count()
    print(f"[chay thu ] se_chuyen={thu['se_chuyen']} rong={thu['rong']} "
          f"tong={thu['tong']}  |  Workflow tao ra={tao_sau_chay_thu}")

    that = di_tru_m1.chuyen(db, chay_that=True)
    db.commit()
    cong = that["da_chuyen"] + that["rong"] + that["da_co"]
    print(f"[chay that] da_chuyen={that['da_chuyen']} rong={that['rong']} "
          f"da_co={that['da_co']} tong={that['tong']}  |  cong={cong}")

    lai = di_tru_m1.chuyen(db, chay_that=True)
    db.commit()
    tong_wf = db.query(M.Workflow).count()
    print(f"[luy dang ] lan hai: da_chuyen={lai['da_chuyen']} "
          f"da_co={lai['da_co']}  |  Workflow tong={tong_wf}")

    # Thu duoc CUU: cong ma `canvas_to_plan()` dang vut di.
    giu = 0
    for d in db.query(M.WorkflowDraft).all():
        for t in d.document.get("pages", []):
            for c in t.get("edges", []):
                if (c.get("source_port") not in ("", "out")
                        or c.get("target_port") not in ("", "in")):
                    giu += 1
    print(f"[gia tri  ] canh mang cong KHONG mac dinh duoc giu: {giu}")

    db.close()

    xau = (tao_sau_chay_thu != 0
           or cong != that["tong"]
           or lai["da_chuyen"] != 0
           or tong_wf != that["da_chuyen"])
    print("\nRESULT: " + ("FAIL" if xau else "PASS"))
    return 1 if xau else 0


if __name__ == "__main__":
    sys.exit(main())
