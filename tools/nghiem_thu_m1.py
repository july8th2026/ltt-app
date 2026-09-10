"""Nghiem thu `M-1` sau khi da ghi — CHI DOC, doc lai tu production.

⛔ **KHONG doc bao cao cua `chay_m1_tren_production.py`.** Mot cong cu tu bao
   minh lam dung la mot loi khai, khong phai mot phep do. Tep nay noi lai vao
   CSDL, dem lai tu dau, va doi chieu voi mot ANH CHUP LAY TRUOC KHI GHI.

## Sau menh de, va vi sao tung cai

    1. `agent_workflows` KHONG doi   nguon la CHI DOC; doi mot hang la mot loi
    2. `users` KHONG doi             M-1 khong duoc cham nguoi dung
    3. `credit_entries` KHONG GIAM   so chi ghi them; giam la mat but toan
    4. `workflow` +N                 N = so ban that su chuyen duoc
    5. id moi NAM TRON trong id nguon   ban moi GIU NGUYEN `id` cua ban cu, nen
                                        mot id la nghia la ta da BIA ra mot ban
    6. `published_version_id` RONG   ban vua di tru CHUA xuat ban lan nao. Day
                                     la cot tung bi ep lam dau `"m1:"+id` va
                                     lam tran `String(36)` tren PostgreSQL —
                                     kiem no la kiem rang bai hoc do con giu.

⚠️ Menh de 3 dung "KHONG GIAM" chu khong "KHONG DOI": production dang phuc vu
   khach that, nen `credit_entries` va `jobs` **se** tang giua hai lan doc. Mot
   phep kiem doi chung dung yen o day se do vi luu luong that, va nguoi doc se
   hoc cach bo qua no.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

BANG = ("agent_workflows", "workflow", "workflow_draft",
        "credit_entries", "jobs", "users")


def _nap_d2():
    s = importlib.util.spec_from_file_location(
        "d2_chi_doc", GOC / "tools" / "dem_d2_agent_production.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--truoc", required=True,
                    help="tep JSON anh chup LAY TRUOC KHI GHI")
    args = ap.parse_args()

    truoc = json.loads(pathlib.Path(args.truoc).read_text(encoding="utf-8"))
    d2 = _nap_d2()
    live = d2._live_url()
    pw = d2._doc_bi_mat("postgres-superuser.txt").strip()
    if not (live.startswith(("postgresql", "postgres")) and pw):
        print("BO QUA: khong dung duoc URL production.")
        return 0

    ten = live.rsplit("/", 1)[-1].split("?", 1)[0]
    dia_chi = live.partition("://")[2].partition("@")[2].rsplit("/", 1)[0]

    import sqlalchemy as sa

    e = sa.create_engine(f"postgresql+psycopg://postgres:{pw}@{dia_chi}/{ten}",
                         connect_args={"connect_timeout": 5})
    with e.connect() as c:
        sau = {b: int(c.execute(sa.text(d2._chi_doc(
            f"SELECT COUNT(*) FROM {b}"))).scalar() or 0) for b in BANG}
        id_moi = {r[0] for r in c.execute(sa.text(d2._chi_doc(
            "SELECT id FROM workflow")))}
        pvid = sorted({r[0] for r in c.execute(sa.text(d2._chi_doc(
            "SELECT DISTINCT published_version_id FROM workflow")))})
        co_cong = int(c.execute(sa.text(d2._chi_doc(
            "SELECT COUNT(*) FROM workflow_draft "
            "WHERE document::text LIKE '%source_port%'"))).scalar() or 0)
        # ⚠️ MENH DE DUNG khong phai "moi draft deu mang cong". Phan lon
        #    workflow production khong co canh nao (do 08/09: toi da 3 node,
        #    toi da 2 canh). Menh de dung la KHONG MAT: so ban NGUON co canh
        #    phai bang so draft mang cong.
        #
        # ⛔ Ban dau toi chot `co_cong == them`, no DO, va cai bay tiep theo la
        #    "ha phep kiem cho xanh". Thu phai sua la MENH DE — va cach duy
        #    nhat biet duoc la di do CHINH DU LIEU NGUON.
        nguon_co_canh = int(c.execute(sa.text(d2._chi_doc(
            "SELECT COUNT(*) FROM agent_workflows WHERE "
            "(document::text LIKE '%sourceHandle%') OR "
            "(edges::text <> '[]' AND edges IS NOT NULL)"))).scalar() or 0)
    e.dispose()

    t = truoc["dem"]
    id_nguon = {h["id"] for h in truoc["hang"]}
    them = sau["workflow"] - t["workflow"]

    print(f"CSDL: {ten}   (CHI DOC)\n")
    print("BANG                 TRUOC ->   SAU")
    for b in BANG:
        dau = "   <-- doi" if t[b] != sau[b] else ""
        print(f"  {b:18s} {t[b]:6d} -> {sau[b]:6d}{dau}")
    print()
    print(f"  id workflow moi nam tron trong id nguon : "
          f"{id_moi <= id_nguon}  ({len(id_moi)}/{len(id_nguon)})")
    print(f"  published_version_id (chi duoc co '')   : {pvid}")
    print(f"  ban NGUON co canh                       : {nguon_co_canh}")
    print(f"  draft mang `source_port`                : {co_cong}"
          f"   (phai bang so tren, KHONG phai bang {them})")
    print()

    kt = [
        ("agent_workflows KHONG doi (nguon chi doc)",
         t["agent_workflows"] == sau["agent_workflows"]),
        ("users KHONG doi", t["users"] == sau["users"]),
        # KHONG GIAM, khong phai KHONG DOI — xem docstring.
        ("credit_entries KHONG giam", sau["credit_entries"] >= t["credit_entries"]),
        ("jobs KHONG giam", sau["jobs"] >= t["jobs"]),
        ("workflow_draft tang bang workflow",
         sau["workflow_draft"] - t["workflow_draft"] == them),
        ("id moi la id CU (khong bia id nao)", id_moi <= id_nguon),
        ("published_version_id rong", pvid == [""]),
        # KHONG MAT canh: moi ban nguon co canh phai ra mot draft mang cong.
        ("khong mat canh nao", co_cong == nguon_co_canh),
    ]
    for ten_kt, ok in kt:
        print(f"  {'DAT ' if ok else 'HONG'}  {ten_kt}")

    xau = not all(o for _, o in kt)
    print("\nRESULT: " + ("FAIL" if xau else "PASS"))
    return 1 if xau else 0


if __name__ == "__main__":
    sys.exit(main())
