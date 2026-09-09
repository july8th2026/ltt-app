"""Do TOKEN VAO / TOKEN RA / THOI GIAN cua model nha (may B) — CHI DOC.

Doc `asv_usage` tren CSDL production: mot dong = MOT luot goi nang luc, do duoc.
Khong doc bang gia, khong doc `ngan_sach.py` — nhung con so o day la thu da
**xay ra**, khong phai thu duoc **khai**.

## ⛔ Vi sao khong lay tu tep chung cu

`ai.py:415` ghi `token_vao`/`token_ra` vao SO SU DUNG, khong vao bao cao nghiem
thu. Va CSDL cua bo test la SQLite dung-mot-lan, nen so cua mot luot test bien
mat cung thu muc tam. Chi production giu duoc chuoi dai.

## ⛔ Rao an toan

`_chi_doc` import tu `tools/dem_d2_agent_production.py` — SELECT-only, mot cau,
khong tu khoa ghi o bat cu dau. Khong chep lai rao: mot ban sao cua rao la mot
ban sao co the troi khoi ban goc.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import statistics
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))


def _nap_d2():
    s = importlib.util.spec_from_file_location(
        "d2_chi_doc", GOC / "tools" / "dem_d2_agent_production.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _tom(ten: str, ds: list) -> None:
    if not ds:
        print(f"  {ten:22s} (khong co so)")
        return
    ds = sorted(ds)
    n = len(ds)

    def pct(p: float) -> float:
        return ds[min(n - 1, int(n * p))]

    print(f"  {ten:22s} n={n:<6d} min={ds[0]:<8.0f} p50={statistics.median(ds):<9.0f} "
          f"p90={pct(0.90):<9.0f} p99={pct(0.99):<9.0f} max={ds[-1]:<9.0f} "
          f"tb={statistics.fmean(ds):.0f}")


def main() -> int:
    # ⛔ **KHONG co `--ngay`, va viec khong co no la co y.**
    #
    #    Ban dau co `--ngay` (mac dinh 30) va cau `SELECT` ben duoi **khong
    #    loc theo ngay** mot chut nao. Mot co khai ra ma khong noi gi toi ket
    #    qua la mot cua gia: no hua mot cua so 30 ngay, nguoi doc tin, roi
    #    doc con so cua **ca lich su**.
    #
    # ⚠️ Mo lai duoc, nhung phai kem mot cot thoi gian DA XAC MINH la co that
    #    trong `asv_usage` — dung them lai co roi de cau SELECT nguyen si.
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args()

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
        co = {r[0] for r in c.execute(sa.text(d2._chi_doc(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public'")))}
        if "asv_usage" not in co:
            print("BO QUA: khong co bang `asv_usage` tren production.")
            e.dispose()
            return 0
        cot = {r[0] for r in c.execute(sa.text(d2._chi_doc(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='asv_usage'")))}
        print(f"CSDL: {ten}   (CHI DOC)")
        print(f"cot cua `asv_usage`: {sorted(cot)}\n")

        tong = int(c.execute(sa.text(d2._chi_doc(
            "SELECT COUNT(*) FROM asv_usage"))).scalar() or 0)
        print(f"tong dong asv_usage: {tong}")
        if not tong:
            e.dispose()
            return 0

        # `ghi_chu` la JSON chua `token_vao`/`token_ra` (xem `ai.py:415`).
        hang = c.execute(sa.text(d2._chi_doc(
            "SELECT nang_luc, don_vi, so_luong, ghi_chu, trang_thai "
            "FROM asv_usage"))).mappings().all()
    e.dispose()

    import collections
    import json

    vao: dict[str, list] = collections.defaultdict(list)
    ra: dict[str, list] = collections.defaultdict(list)
    giay: dict[str, list] = collections.defaultdict(list)
    trang = collections.Counter()
    for h in hang:
        trang[h["trang_thai"]] += 1
        g = h["ghi_chu"]
        if isinstance(g, str):
            try:
                g = json.loads(g)
            except Exception:                                # noqa: BLE001
                g = {}
        g = g or {}
        nl = str(h["nang_luc"] or "?")
        if g.get("token_vao"):
            vao[nl].append(float(g["token_vao"]))
        if g.get("token_ra"):
            ra[nl].append(float(g["token_ra"]))
        if str(h["don_vi"] or "") in ("giay", "s") and h["so_luong"]:
            giay[nl].append(float(h["so_luong"]))

    print(f"trang thai: {dict(trang)}\n")
    print("TOKEN VAO theo nang luc:")
    for k in sorted(vao):
        _tom(k, vao[k])
    print("\nTOKEN RA theo nang luc:")
    for k in sorted(ra):
        _tom(k, ra[k])
    if giay:
        print("\nTHOI GIAN (giay) theo nang luc:")
        for k in sorted(giay):
            _tom(k, giay[k])

    tv = [x for v in vao.values() for x in v]
    tr = [x for v in ra.values() for x in v]
    if tv or tr:
        print("\nGOP:")
        _tom("token vao", tv)
        _tom("token ra", tr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
