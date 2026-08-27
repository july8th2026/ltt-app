"""Chay bo bat bien da tien trinh (`test_214`) — hoac noi to rang no khong chay.

Ba loi P0 cua ban audit 2026-08-15 lot qua hon ba nghin test vi CHUA TUNG co gi
chay hai tien trinh worker cung luc tren mot CSDL. `test_214` la phep do con
thieu do — nhung no can PostgreSQL, va `pytest` chi in mot chu `s` khi bo qua.
Mot chu `s` giua ba nghin dau cham thi khong ai thay.

Cong cu nay bien viec bo qua thanh MOT DONG RIENG trong gate. No khong lam gate
do khi may khong co PostgreSQL — mot may phat trien khong co PostgreSQL van phai
lam viec duoc — nhung no khong bao gio de viec bo qua tro nen VO HINH.

Tim CSDL test theo thu tu:
  1. `LTT_TEST_DATABASE_URL` neu da dat;
  2. tu dung tu `LTT_DATABASE_URL` cua chinh trien khai nay, doi ten CSDL thanh
     `<ten>_multiproc_test` va TAO neu chua co (can quyen tao CSDL, hoac mat
     khau superuser o `secrets/postgres-superuser.txt` nhu bo cai dung).

Ten CSDL luon chua chu `test` — rao o `tests/pg_scratch.py` tu choi bat cu URL
nao khong chung minh duoc no la CSDL vut di, vi cac test nay goi `drop_all()`.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HAU_TO = "_multiproc_test"
SUPER = (pathlib.Path(r"C:\LTTPlatform\secrets\postgres-superuser.txt"),
         ROOT / "secrets" / "postgres-superuser.txt")


def _doc_neu_duoc(path: pathlib.Path) -> str:
    """Noi dung tep, hoac chuoi rong neu khong co HOAC khong du quyen.

    🔴 `PermissionError` o day KHONG phai loi — no la dau hieu `secrets\\` da
       duoc siet dung (chi SYSTEM + Administrators), va cong cu nay chay bang
       tai khoan thuong.

    ⚠️ Truoc 2026-08-27 ham goi no chi bat `path.exists()`, va `exists()` **nem**
       `PermissionError` chu khong tra `False`. Nen ngay sau khi siet ACL, buoc
       gate nay do bang mot stack trace — trong khi no von co san duong du phong
       (tu dung CSDL test). Mot cong cu doc mot cau hinh TUY CHON phai coi
       "khong doc duoc" giong "khong co", nhat la khi "khong doc duoc" la trang
       thai MONG DOI.
    """
    try:
        return path.read_text(encoding="utf-8-sig")
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def _doc_env(ten: str) -> str:
    """Doc mot bien tu app.env da cai hoac trong kho. Khong in ra gia tri."""
    for path in (pathlib.Path(r"C:\LTTPlatform\secrets\app.env"),
                 ROOT / "secrets" / "app.env"):
        for line in _doc_neu_duoc(path).splitlines():
            if line.strip().startswith(f"{ten}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _superuser_pw() -> str:
    for path in SUPER:
        noi_dung = _doc_neu_duoc(path)
        if noi_dung:
            return noi_dung.strip()
    return ""


def _tim_url() -> tuple[str, str]:
    """Tra (url, ly_do_bo_qua). Mot trong hai luon rong."""
    dat = (os.environ.get("LTT_TEST_DATABASE_URL") or "").strip()
    if dat:
        return dat, ""

    live = (os.environ.get("LTT_DATABASE_URL") or "").strip() or _doc_env("LTT_DATABASE_URL")
    if not live.startswith(("postgresql", "postgres")):
        return "", "khong tim thay PostgreSQL (LTT_DATABASE_URL khong phai postgres)"

    base, _, ten = live.rpartition("/")
    ten = ten.split("?", 1)[0]
    scratch_ten = f"{ten}{HAU_TO}"
    scratch = f"{base}/{scratch_ten}"

    try:
        import sqlalchemy as sa
    except ImportError:
        return "", "khong co sqlalchemy"

    # Da co san thi dung luon.
    try:
        e = sa.create_engine(scratch, future=True,
                             connect_args={"connect_timeout": 5})
        with e.connect():
            pass
        e.dispose()
        return scratch, ""
    except Exception as exc:                # noqa: BLE001
        # Khong noi duoc = chua tao, hoac PostgreSQL khong chay. Giu lai ly do
        # de neu buoc duoi cung that bai thi nguoi doc biet vi sao, thay vi chi
        # thay "khong tao duoc" ma khong ro tai buoc nao.
        vi_sao_khong_noi_duoc = f"{type(exc).__name__}"

    pw = _superuser_pw()
    if not pw:
        return "", (f"chua co CSDL {scratch_ten} ({vi_sao_khong_noi_duoc}) va "
                    f"khong co mat khau superuser de tao")
    try:
        thong_tin, _, dia_chi = base.partition("://")[2].partition("@")
        # CSDL phai thuoc ve tai khoan cua NEN TANG, khong phai superuser: neu
        # khong, `ltt_app` khong tao duoc bang trong do va moi test do voi
        # "permission denied for schema public". Chi lay TEN dang nhap, khong
        # cham toi mat khau.
        chu = thong_tin.split(":", 1)[0]
        admin_url = f"postgresql+psycopg://postgres:{pw}@{dia_chi}/postgres"
        e = sa.create_engine(admin_url, future=True,
                             isolation_level="AUTOCOMMIT",
                             connect_args={"connect_timeout": 5})
        with e.connect() as c:
            c.execute(sa.text(f'CREATE DATABASE "{scratch_ten}" OWNER "{chu}"'))
        e.dispose()
        print(f"[i] da tao CSDL test {scratch_ten}")
        return scratch, ""
    except Exception as exc:                # noqa: BLE001
        return "", (f"khong tao duoc CSDL test: {type(exc).__name__} "
                    f"(khong noi duoc truoc do: {vi_sao_khong_noi_duoc})")


def main() -> int:
    url, ly_do = _tim_url()
    if not url:
        # KHONG phai loi: mot may khong co PostgreSQL van phai lam viec duoc.
        # Nhung phai noi to, vi day la bang chung cho ba loi P0 da dong.
        print("BO QUA bo bat bien da tien trinh — " + ly_do)
        print("  test_214 la thu duy nhat chung minh webhook khong gui trung,")
        print("  canh bao khong nhan doi, va so credit khop khi nhieu tien")
        print("  trinh worker chay cung luc.")
        # Tu 2026-08-27, nguyen nhan HAY GAP NHAT tren may chu khong con la
        # "khong co PostgreSQL" ma la "khong doc duoc secrets\": thu muc do da
        # duoc siet ve SYSTEM + Administrators, nen mot shell thuong khong lay
        # duoc `LTT_DATABASE_URL` lan mat khau superuser. Noi thang ra, vi hai
        # nguyen nhan do doi hai cach xu ly khac han nhau.
        if not _doc_neu_duoc(pathlib.Path(r"C:\LTTPlatform\secrets\app.env")):
            # !! THUAN ASCII o day. Gate goi cong cu nay KHONG dat
            #    PYTHONIOENCODING, nen stdout la cp1252 va mot ky tu ngoai bang
            #    ma do nem `UnicodeEncodeError` -> buoc gate DO, voi mot stack
            #    trace khong lien quan gi toi thu no dang kiem.
            #    Da dinh dung the ngay 27/08 khi them mot emoji vao dong duoi.
            print()
            print("  !! Tren may CHU: gan nhu chac chan vi khong doc duoc")
            print("      C:\\LTTPlatform\\secrets\\ (da siet ve SYSTEM +")
            print("      Administrators tu 27/08). Do KHONG phai loi.")
            print("      Chay lai gate bang PowerShell Administrator, hoac dat")
            print("      LTT_TEST_DATABASE_URL truoc khi chay.")
        print()
        print("  Chay tay:")
        print("    set LTT_TEST_DATABASE_URL=postgresql+psycopg://.../..._test")
        print("    python -m pytest tests/test_214_multi_process_runtime.py")
        return 0

    env = dict(os.environ)
    env["LTT_TEST_DATABASE_URL"] = url
    env.pop("LTT_DATABASE_URL", None)       # test tu tro CSDL cua no
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_214_multi_process_runtime.py"],
        cwd=str(ROOT), env=env, capture_output=True, text=True)
    if done.returncode != 0:
        print(done.stdout[-3000:])
        print(done.stderr[-1500:])
        return done.returncode
    print(done.stdout.strip().splitlines()[-1] if done.stdout.strip() else "OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
