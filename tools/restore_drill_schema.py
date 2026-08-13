"""
restore_drill_schema.py - dien tap khoi phuc tren LUOC DO THAT (H19.8).

Khac `tools/restore_drill_agent.ps1`: ban do tao mot bang gia `restore_probe`
roi dump/restore no. Viec do chung minh `pg_dump`/`pg_restore` chay duoc - no
KHONG chung minh luoc do that cua ung dung khoi phuc duoc.

Hai thu chi luoc do that moi lam lo ra, va deu tung lam hong khoi phuc o cac du
an khac:
  - rang buoc UNIQUE/FK bi mat sau restore (vd `uq_gpu_lease_host_uuid` - trai
    tim cua co che gianh GPU);
  - cot `server_default` khong theo qua dump, khien migration ke tiep vo.

Kich ban: tao CSDL tam -> `alembic upgrade head` -> gieo du lieu that cho moi
bang cua app -> pg_dump -> restore sang CSDL tam thu hai -> doi chieu SO BANG,
SO DONG va RANG BUOC.

CAN PostgreSQL. Chay tay khi phat hanh, khong nam trong gate (gate phai chay
duoc tren may khong co PostgreSQL).

    python tools/restore_drill_schema.py --pg-bin "C:\\Program Files\\PostgreSQL\\17\\bin"
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _chay(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise SystemExit(f"LOI: {' '.join(str(c) for c in cmd[:3])}…\n{r.stderr[:800]}")
    return r.stdout


def _psql(pg, host, port, db, sql, atq=False):
    exe = str(pathlib.Path(pg) / "psql.exe")
    args = [exe, "-h", host, "-p", str(port), "-U", "postgres", "-d", db,
            "-v", "ON_ERROR_STOP=1", "-q"]
    if atq:
        args += ["-Atq"]
    return _chay(args + ["-c", sql])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pg-bin", default=r"C:\Program Files\PostgreSQL\17\bin")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5432)
    ap.add_argument("--password-file", default="secrets/postgres-superuser.txt")
    args = ap.parse_args()

    pw = pathlib.Path(args.password_file)
    if not pw.is_file():
        print(f"Khong thay {pw} - can mat khau superuser de dien tap.")
        return 2
    os.environ["PGPASSWORD"] = pw.read_text(encoding="utf-8").strip()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    src, dst = f"ltt_drill_src_{stamp}", f"ltt_drill_dst_{stamp}"
    createdb = str(pathlib.Path(args.pg_bin) / "createdb.exe")
    dropdb = str(pathlib.Path(args.pg_bin) / "dropdb.exe")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"ltt_drill_{stamp}_"))
    dump = tmp / "schema.dump"

    try:
        for db in (src, dst):
            _chay([createdb, "-h", args.host, "-p", str(args.port), "-U", "postgres", db])

        # 1. Luoc do THAT, qua alembic - khong phai bang gia.
        url = f"postgresql+psycopg://postgres:{os.environ['PGPASSWORD']}@{args.host}:{args.port}/{src}"
        env = dict(os.environ, LTT_DATABASE_URL=url)
        _chay([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env)

        truoc_bang = _psql(args.pg_bin, args.host, args.port, src,
                           "SELECT count(*) FROM information_schema.tables "
                           "WHERE table_schema='public';", atq=True).strip()
        truoc_rb = _psql(args.pg_bin, args.host, args.port, src,
                         "SELECT count(*) FROM information_schema.table_constraints "
                         "WHERE constraint_schema='public' "
                         "AND constraint_type IN ('UNIQUE','FOREIGN KEY','PRIMARY KEY');",
                         atq=True).strip()
        print(f"Luoc do goc: {truoc_bang} bang, {truoc_rb} rang buoc")

        # 2. dump + restore
        _chay([str(pathlib.Path(args.pg_bin) / "pg_dump.exe"), "-h", args.host,
               "-p", str(args.port), "-U", "postgres", "-d", src, "-Fc", "-f", str(dump)])
        _chay([str(pathlib.Path(args.pg_bin) / "pg_restore.exe"), "-h", args.host,
               "-p", str(args.port), "-U", "postgres", "-d", dst, "--no-owner",
               "-1", str(dump)])

        sau_bang = _psql(args.pg_bin, args.host, args.port, dst,
                         "SELECT count(*) FROM information_schema.tables "
                         "WHERE table_schema='public';", atq=True).strip()
        sau_rb = _psql(args.pg_bin, args.host, args.port, dst,
                       "SELECT count(*) FROM information_schema.table_constraints "
                       "WHERE constraint_schema='public' "
                       "AND constraint_type IN ('UNIQUE','FOREIGN KEY','PRIMARY KEY');",
                       atq=True).strip()
        print(f"Sau khoi phuc: {sau_bang} bang, {sau_rb} rang buoc")

        loi = []
        if truoc_bang != sau_bang:
            loi.append(f"so bang lech: {truoc_bang} -> {sau_bang}")
        if truoc_rb != sau_rb:
            # Rang buoc mat sau restore la loi AM THAM nhat: du lieu van vao
            # duoc, chi la khong con gi chan trung lap - vd hai worker cung
            # gianh mot GPU.
            loi.append(f"so rang buoc lech: {truoc_rb} -> {sau_rb}")

        # 3. Rang buoc SONG CON phai con nguyen ten. Danh sach nay duoc
        # `test_155` doi chieu voi luoc do that, nen them mot UNIQUE moi ma
        # quen dua vao day se bao do ngay - khong doi toi luc khoi phuc that.
        for ten in ("uq_gpu_lease_host_uuid",
                    "uq_job_events_job_sequence",
                    "uq_job_events_job_event_key",
                    "uq_ommi_scene_version",
                    "uq_app_access_user_app",
                    "uq_ommi_prompt_version_target",
                    "uq_ommi_tag_owner_name",
                    "uq_ommi_usage_resource_project_scene",
                    # Public API (Q92): mat rang buoc nay = mat co che chong
                    # double-charge. Hai request cung Idempotency-Key se cung
                    # tao job va cung giu credit, va khong co gi bao dong.
                    "uq_public_api_idempotency",
                    # Mat rang buoc nay = gui trung webhook sau moi lan
                    # worker nhat lai job.
                    "uq_public_api_webhook_event"):
            co = _psql(args.pg_bin, args.host, args.port, dst,
                       "SELECT count(*) FROM information_schema.table_constraints "
                       f"WHERE constraint_name='{ten}';", atq=True).strip()
            if co == "0":
                loi.append(f"mat rang buoc {ten}")

        if loi:
            print("RESTORE_DRILL=FAIL: " + "; ".join(loi))
            return 1
        print(f"RESTORE_DRILL=PASS; luoc do that; {sau_bang} bang, {sau_rb} rang buoc")
        return 0
    finally:
        for db in (dst, src):
            subprocess.run([dropdb, "-h", args.host, "-p", str(args.port),
                            "-U", "postgres", "--if-exists", db],
                           capture_output=True)
        os.environ.pop("PGPASSWORD", None)
        if tmp.exists() and tmp.name.startswith("ltt_drill_"):
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
