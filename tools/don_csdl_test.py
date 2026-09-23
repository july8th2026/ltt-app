"""don_csdl_test.py - liet ke CSDL test PostgreSQL MO COI; chi xoa khi co `--xoa`.

    python tools/don_csdl_test.py           # CHAY THU: in bang, khong xoa gi
    python tools/don_csdl_test.py --xoa     # xoa dung nhom XOA (can chu du an duyet)

🔴 VI SAO CO TEP NAY. Den 23/09/2026 may chu co 132 CSDL, 127 tao trong thang 9:
   ba cong cu gate (`check_multiproc`, `do_migration_tren_postgres`,
   `dien_tap_m1_tren_postgres`) tao mot CSDL test cho MOI worktree va khong bao
   gio xoa; `test_1010` tao mot CSDL ngau nhien moi luot. Sau moi lan may sap,
   PostgreSQL fsync tung tep (44.651 tep, ~4,5 phut) -> `pg_ctl` qua han -> dich
   vu bao Stopped trong khi postgres.exe van chay -> lan tat may sau giet no.

   Cac cong cu gio tu xoa CSDL cua chinh cay no. Tep nay don phan con sot: luot
   bi ngat giua chung, worktree da go, ban cu chua va.

⭐ Phan loai hoi QUAN HE, khong hoi nhan (AGENTS.md §4c):
   - CSDL theo cay: van tay trong ten co khop MOT worktree dang ton tai
     (`git worktree list`) khong -> khop thi GIU;
   - dang co ket noi (`pg_stat_activity`) -> GIU, du ten trong the nao;
   - production, CSDL he thong, ten la -> khong bao gio nam trong nhom XOA.
   Moi lenh xoa di qua `pg_ten_cay.cau_xoa` (khong FORCE: CSDL vua co ket noi
   giua luc liet ke va luc xoa thi PostgreSQL tu tu choi).
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))
if str(GOC / "tools") not in sys.path:
    sys.path.insert(0, str(GOC / "tools"))

from pg_ten_cay import (CSDL_HE_THONG, HAU_TO_DA_BIET, KHUON_DIEN_TAP,  # noqa: E402
                        cau_xoa, van_tay_cay)

KHUON_VPS = re.compile(r"ltt_vps_v4_test_[0-9a-f]{32}")


def phan_loai(ten: str, ket_noi: int, ten_goc: str, van_tay_song: set[str],
              co_cay_ma_cu: bool) -> tuple[str, str]:
    """(nhom, ly do). Nhom: XOA | GIU | KHAC. Ham thuan — khong cham CSDL.

    `co_cay_ma_cu`: con worktree nao chay ban cong cu truoc 17/09 (chua co
    `pg_ten_cay.py`, dung ten CO DINH khong van tay) khong.
    """
    thap = ten.lower()
    if thap in CSDL_HE_THONG or thap == ten_goc.lower():
        return "GIU", "production / he thong"
    if ket_noi > 0:
        return "GIU", f"dang co {ket_noi} ket noi"
    goc = re.escape(ten_goc.lower())
    for hau_to in HAU_TO_DA_BIET:
        m = re.fullmatch(rf"{goc}{re.escape(hau_to)}_([0-9a-f]{{8}})", thap)
        if m:
            if m.group(1) in van_tay_song:
                return "GIU", "worktree con song"
            return "XOA", "CSDL test cua worktree da go"
        if re.fullmatch(rf"[a-z0-9_]*{re.escape(hau_to)}", thap):
            if co_cay_ma_cu:
                return "GIU", "ten co dinh truoc 17/09, con cay chay ma cu"
            return "XOA", "ten co dinh truoc 17/09, khong cay nao con dung"
    if KHUON_VPS.fullmatch(thap):
        return "XOA", "test_1010: ten ngau nhien, khong bao gio dung lai"
    if KHUON_DIEN_TAP.fullmatch(thap):
        return "XOA", "restore_drill_schema: luot bi ngat giua chung"
    return "KHAC", "khong khop khuon nao - khong dong toi"


def worktree_song() -> list[pathlib.Path]:
    ra = subprocess.run(["git", "-C", str(GOC), "worktree", "list", "--porcelain"],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", check=True).stdout
    return [pathlib.Path(dong[len("worktree "):].strip())
            for dong in ra.splitlines() if dong.startswith("worktree ")]


def _ket_noi_quan_tri():
    import sqlalchemy as sa
    import do_migration_tren_postgres as dm

    live = dm._doc_env("LTT_DATABASE_URL")
    if not live.startswith(("postgresql", "postgres")):
        raise SystemExit("khong tim thay LTT_DATABASE_URL kieu postgres")
    e = sa.create_engine(dm._url_nhap(live, "postgres"), isolation_level="AUTOCOMMIT",
                         connect_args={"connect_timeout": 5})
    return e, dm._ten_csdl(live)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--xoa", action="store_true",
                    help="XOA that nhom XOA (mac dinh: chi liet ke)")
    args = ap.parse_args()

    import sqlalchemy as sa

    cay = worktree_song()
    van_tay = {van_tay_cay(p) for p in cay}
    co_cay_ma_cu = any((p / "tools" / "check_multiproc.py").exists()
                       and not (p / "tools" / "pg_ten_cay.py").exists() for p in cay)
    e, ten_goc = _ket_noi_quan_tri()
    try:
        with e.connect() as c:
            hang = c.execute(sa.text(
                "SELECT d.datname, pg_database_size(d.oid), "
                "(SELECT count(*) FROM pg_stat_activity a WHERE a.datname = d.datname), "
                "(pg_stat_file('base/' || d.oid)).modification "
                "FROM pg_database d WHERE NOT d.datistemplate ORDER BY d.datname")).all()
        bang = [(ten, round(co / 1048576, 1), int(kn), luc,
                 *phan_loai(ten, int(kn), ten_goc, van_tay, co_cay_ma_cu))
                for ten, co, kn, luc in hang]

        print(f"production: {ten_goc} | worktree con song: {len(cay)} | "
              f"con cay ma cu: {co_cay_ma_cu} | tong CSDL: {len(bang)}")
        for nhom in ("XOA", "GIU", "KHAC"):
            ds = [b for b in bang if b[4] == nhom]
            print(f"\n== {nhom}: {len(ds)} CSDL, {sum(b[1] for b in ds):.1f} MB ==")
            for ten, mb, kn, luc, _, ly_do in ds:
                ngay = luc.strftime("%Y-%m-%d") if luc else "?"
                print(f"  {ten:<55} {mb:>7.1f} MB  kn={kn}  {ngay}  {ly_do}")

        if not args.xoa:
            print("\nCHAY THU - khong xoa gi. Xoa that: --xoa (can chu du an duyet).")
            return 0
        xoa = loi = 0
        for ten, *_, nhom, _ly in bang:
            if nhom != "XOA":
                continue
            try:
                with e.connect() as c:
                    c.execute(sa.text(cau_xoa(ten, ten_goc)))
                xoa += 1
            except Exception as exc:                        # noqa: BLE001
                loi += 1
                print(f"  !! {ten}: {type(exc).__name__}")
        print(f"\nda xoa {xoa}, khong xoa duoc {loi}")
        return 1 if loi else 0
    finally:
        e.dispose()


if __name__ == "__main__":
    sys.exit(main())
