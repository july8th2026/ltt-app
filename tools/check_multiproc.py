"""Chay bo bat bien da tien trinh/da luong tren PostgreSQL that (`TEP_PG`) —
hoac noi to rang no khong chay.

Ba loi P0 cua ban audit 2026-08-15 lot qua hon ba nghin test vi CHUA TUNG co gi
chay hai tien trinh worker cung luc tren mot CSDL. `test_214` la phep do con
thieu do — nhung no can PostgreSQL, va `pytest` chi in mot chu `s` khi bo qua.
Mot chu `s` giua ba nghin dau cham thi khong ai thay.

`TEP_PG` (duoi day) cung gom `test_1720_wf_dong_co_pg.py`: dam bao dong co
Workflow V2 (`platform_core/workflow/dong_co.py`) an toan khi hai luot
`mot_vong` chay song song tren cung CSDL (khoa hang run, khong nop job doi) va
song sot khi mot luot chet giua chung (FLOW H — transaction rollback, khong
job ma). Cung mot ly do bo qua vo hinh: bo qua ca hai chum bao dam nay tren mot
may khong co PostgreSQL cung chi la MOT chu `s`.

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

#: Moi tep test can PostgreSQL that. Them tep moi vao DAY (mot nguon).
TEP_PG = ("tests/test_214_multi_process_runtime.py",
          "tests/test_1720_wf_dong_co_pg.py")


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
    # Moi cay mot CSDL test rieng (su co 17/09, tools/pg_ten_cay.py).
    sys.path.insert(0, str(ROOT / "tools"))
    from pg_ten_cay import ten_csdl_test
    scratch_ten = ten_csdl_test(ten, HAU_TO, ROOT)
    scratch = f"{base}/{scratch_ten}"

    try:
        import sqlalchemy as sa
    except ImportError:
        return "", "khong co sqlalchemy"

    # 🔴 CO MAT KHAU SUPERUSER THI NOI BANG SUPERUSER — khong bang tai khoan ung
    #    dung. Do 19/09/2026 (L3 `91ceccd4`): cay chinh co `secrets\app.env` BAN
    #    DEV (07/09) voi mat khau `ltt_app` DA CU, con mat khau superuser van
    #    dung. Hai buoc PostgreSQL kia (`do_migration_tren_postgres`,
    #    `dien_tap_m1_tren_postgres`) dung superuser nen XANH; buoc nay dung
    #    `ltt_app` nen DO `password authentication failed for user "ltt_app"`
    #    — va "khep" bang chay lai nang quyen (doc `app.env` production) ba lan.
    #    Chay lai lan hai con te hon: CSDL da tao o lan dau ⇒ `CREATE` loi
    #    "already exists" ⇒ tu khai bo qua — do bien thanh bo qua.
    #
    # ⭐ Cung quy uoc voi `do_migration_tren_postgres._url_nhap`: CSDL vut di
    #    (ten chua `test`, rao `tests/pg_scratch.py`) thi superuser AN TOAN hon,
    #    va phep do khong con phu thuoc mot mat khau thu hai co the lech.
    pw = _superuser_pw()
    if pw:
        dia_chi = base.partition("://")[2].partition("@")[2]
        return _dung_bang_superuser(sa, pw, dia_chi, scratch_ten)

    # Khong co superuser: CSDL da co san (va tai khoan ung dung noi duoc) thi dung.
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
        return "", (f"chua co CSDL {scratch_ten} ({type(exc).__name__}) va "
                    f"khong co mat khau superuser de tao")


def _dung_bang_superuser(sa, pw: str, dia_chi: str, scratch_ten: str) -> tuple[str, str]:
    """URL superuser toi CSDL vut di `scratch_ten`; TAO neu chua co. Khong in mat khau."""
    scratch = f"postgresql+psycopg://postgres:{pw}@{dia_chi}/{scratch_ten}"
    try:
        e = sa.create_engine(scratch, future=True,
                             connect_args={"connect_timeout": 5})
        with e.connect():
            pass
        e.dispose()
        return scratch, ""
    except Exception as exc:                # noqa: BLE001
        # Chua tao, hoac PostgreSQL khong chay — buoc duoi se phan xu.
        vi_sao_khong_noi_duoc = type(exc).__name__
    try:
        admin_url = f"postgresql+psycopg://postgres:{pw}@{dia_chi}/postgres"
        e = sa.create_engine(admin_url, future=True,
                             isolation_level="AUTOCOMMIT",
                             connect_args={"connect_timeout": 5})
        with e.connect() as c:
            c.execute(sa.text(f'CREATE DATABASE "{scratch_ten}"'))
        e.dispose()
        print(f"[i] da tao CSDL test {scratch_ten}")
        return scratch, ""
    except Exception as exc:                # noqa: BLE001
        return "", (f"khong tao duoc CSDL test: {type(exc).__name__} "
                    f"(khong noi duoc truoc do: {vi_sao_khong_noi_duoc})")


def _xoa_scratch() -> None:
    """Xoa CSDL test cua CHINH cay nay sau luot chay (su co 23/09: CSDL mo coi).

    Chi xoa khi cong cu TU dung CSDL do bang superuser — tuc lan sau tu tao lai
    duoc. `LTT_TEST_DATABASE_URL` do nguoi goi dat, hoac khong co superuser (CSDL
    co san, tai khoan ung dung noi vao): KHONG phai cua ta, giu nguyen.
    """
    if (os.environ.get("LTT_TEST_DATABASE_URL") or "").strip():
        return
    pw = _superuser_pw()
    if not pw:
        return
    live = (os.environ.get("LTT_DATABASE_URL") or "").strip() or _doc_env("LTT_DATABASE_URL")
    if not live.startswith(("postgresql", "postgres")):
        return
    base, _, ten = live.rpartition("/")
    ten = ten.split("?", 1)[0]
    sys.path.insert(0, str(ROOT / "tools"))
    from pg_ten_cay import cau_xoa_csdl_test
    cau = cau_xoa_csdl_test(ten, HAU_TO, ROOT)
    dia_chi = base.partition("://")[2].partition("@")[2]
    import sqlalchemy as sa
    e = sa.create_engine(f"postgresql+psycopg://postgres:{pw}@{dia_chi}/postgres",
                         future=True, isolation_level="AUTOCOMMIT",
                         connect_args={"connect_timeout": 5})
    try:
        with e.connect() as c:
            c.execute(sa.text(cau))
        print("[i] da xoa CSDL test cua cay nay")
    except Exception as exc:                # noqa: BLE001
        print(f"[!] khong xoa duoc CSDL test ({type(exc).__name__}) - "
              "python tools/don_csdl_test.py se liet ke no")
    finally:
        e.dispose()


def main() -> int:
    url, ly_do = _tim_url()
    if not url:
        # KHONG phai loi: mot may khong co PostgreSQL van phai lam viec duoc.
        # Nhung phai noi to, vi day la bang chung cho ba loi P0 da dong.
        print("BO QUA bo bat bien da tien trinh/da luong — " + ly_do)
        print("  test_214 la thu duy nhat chung minh webhook khong gui trung,")
        print("  canh bao khong nhan doi, va so credit khop khi nhieu tien")
        print("  trinh worker chay cung luc. test_1720 la thu duy nhat chung")
        print("  minh dong co Workflow V2 khong nop job doi khi hai luot")
        print("  `mot_vong` chay song song, va song sot khi mot luot chet")
        print("  giua chung (FLOW H). Bo qua ca hai la bo qua bang chung cho")
        print("  ca hai bao dam nay, khong chi bao dam cua test_214.")
        # Tu 2026-08-27, nguyen nhan HAY GAP NHAT tren may chu khong con la
        # "khong co PostgreSQL" ma la "khong doc duoc secrets\": thu muc do da
        # duoc siet ve SYSTEM + Administrators, nen mot shell thuong khong lay
        # duoc `LTT_DATABASE_URL` lan mat khau superuser. Noi thang ra, vi hai
        # nguyen nhan do doi hai cach xu ly khac han nhau.
        if not _doc_neu_duoc(pathlib.Path(r"C:\LTTPlatform\secrets\app.env")):
            # !! THUAN ASCII: gate khong dat PYTHONIOENCODING (stdout cp1252),
            #    ky tu ngoai bang ma se nem UnicodeEncodeError. Da dinh 27/08.
            print()
            print("  !! Tren may CHU: gan nhu chac chan vi khong doc duoc")
            print("      C:\\LTTPlatform\\secrets\\ (da siet ve SYSTEM +")
            print("      Administrators tu 27/08). Do KHONG phai loi.")
            print("      Chay lai gate bang PowerShell Administrator, hoac dat")
            print("      LTT_TEST_DATABASE_URL truoc khi chay.")
        print()
        print("  Chay tay:")
        print("    set LTT_TEST_DATABASE_URL=postgresql+psycopg://.../..._test")
        print("    python -m pytest " + " ".join(TEP_PG))
        return 0

    try:
        return _chay_test_214(url)
    finally:
        _xoa_scratch()


def _chay_test_214(url: str) -> int:
    env = dict(os.environ)
    env["LTT_TEST_DATABASE_URL"] = url
    env.pop("LTT_DATABASE_URL", None)       # test tu tro CSDL cua no
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *TEP_PG],
        # 🔴 `encoding=` + `errors=`, KHONG chi `text=True`.
        #
        #    `text=True` giai ma bang bang ma MAC DINH cua he — tren Windows la
        #    cp1252 — va bo test nay in tieng Viet khi mot phep kiem hong. Ket
        #    qua: cong cu chet o `UnicodeDecodeError` **trong khi dang doc thong
        #    bao loi**, roi `done.stdout` la None va dong ke tiep nem
        #    `TypeError: 'NoneType' object is not subscriptable`.
        #
        # ⛔ Tuc mot lan hong THAT bien thanh mot crash cua chinh cong cu chan
        #    doan, va nguoi doc khong bao gio thay duoc phep kiem nao do. Da
        #    xay ra that: `bat bien da tien trinh` bao FAIL ma khong mot dong
        #    nao noi vi sao.
        cwd=str(ROOT), env=env, capture_output=True,
        text=True, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        print((done.stdout or "")[-3000:])
        print((done.stderr or "")[-1500:])
        return done.returncode
    ra = (done.stdout or "").strip()
    print(ra.splitlines()[-1] if ra else "OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
