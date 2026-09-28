"""Đo migration trên PostgreSQL THẬT — lấp phần còn nợ của rủi ro `R4`.

🔴 **VÌ SAO CÔNG CỤ NÀY TỒN TẠI.** Đo 08/09/2026: **không phép kiểm nào trong
   kho thi hành `alembic upgrade` trên PostgreSQL.**

    moi tep goi `command.upgrade`:  test_103 · test_451 · test_45 · test_505
                                    · test_616
    -> postgres = 0  o TAT CA (chung deu tro `sqlite:///`)

   Bước gate `bat bien da tien trinh` cũng không lấp được: nó dựng lược đồ bằng
   `drop_all()`/metadata — tức đi đường **SQLAlchemy model**, không đi đường
   **migration**. Hai đường khác nhau, và **chỉ đường thứ hai là đường
   production đi**.

⇒ Hệ quả đo được: `BOOLEAN DEFAULT 1` (PostgreSQL từ chối, SQLite nhận) sống
  sót qua **ba** commit, mỗi commit đều kèm câu *"thi hành thật từ `base` tới
  `head`"* — câu ấy đúng, và nó đúng **trên SQLite**.

## ⛔ RÀO AN TOÀN — vì sao chúng ở đây và không được nới

CSDL production của nền tảng tên `lttplatform`, và nó đang giữ **sổ credit
thật**. Công cụ này gọi `DROP`/`CREATE` nên nó phải **CHỨNG MINH** cái nó chạm
là CSDL vứt đi trước khi chạm, chứ không phải "cẩn thận":

    1. ten CSDL PHAI chua "test"       — production khong tinh co mang chu do
    2. ten CSDL PHAI KHAC ten dang chay — kiem theo TEN, khong theo chuoi URL
    3. chi DROP DATABASE qua `pg_ten_cay.cau_xoa_csdl_test` — ten TINH LAI tu
       (ten dang chay, HAU_TO, cay nay), khong nhan tu ngoai; khong FORCE

⚠️ Rào 2 kiểm **tên**, không so cả URL: `tests/pg_scratch.py` ghi rõ phép so URL
   từng bắn nhầm đúng vào tình huống nó sinh ra để bảo vệ.

🔴 Rào 3 cũ là *"không bao giờ DROP DATABASE"*. Đo 23/09/2026: mỗi worktree để
   lại CSDL nháp, worktree bị gỡ thì CSDL mồ côi — 132 CSDL, 44.651 tệp, và
   PostgreSQL fsync từng tệp sau mỗi lần máy sập (~4,5 phút, `pg_ctl` quá hạn,
   dịch vụ báo Stopped). Giờ công cụ xoá CSDL nháp của CHÍNH cây nó ở cuối lượt
   (`--giu` thì giữ); còn sót thì `tools/don_csdl_test.py`.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
HAU_TO = "_wf_migration_test"

# Chay duoc tu bat ky thu muc nao: `tools/` khong nam tren sys.path khi
# script duoc goi bang duong dan tuyet doi.
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))


def _doc_env(ten: str) -> str:
    """Đọc một biến từ `app.env`. **Không in giá trị ra.**"""
    for path in (pathlib.Path(r"C:\LTTPlatform\secrets\app.env"),
                 GOC / "secrets" / "app.env"):
        try:
            noi_dung = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as loi:                            # noqa: BLE001
            # ⛔ KHONG duoc nuot: "ACL chan" va "tep khong ton tai" phai la HAI
            #    cau tra loi khac nhau. Gop chung thanh mot su im lang chinh la
            #    thu da lam ba phien chan doan sai ba vong lien tiep 08/09.
            print(f"  (bo qua {path}: {type(loi).__name__})")
            continue
        for line in noi_dung.splitlines():
            if line.strip().startswith(f"{ten}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _superuser_pw() -> str:
    for path in (pathlib.Path(r"C:\LTTPlatform\secrets\postgres-superuser.txt"),
                 GOC / "secrets" / "postgres-superuser.txt"):
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception as loi:                            # noqa: BLE001
            # Cung ly do nhu tren. `PermissionError` o `C:\LTTPlatform\secrets`
            # KHONG phai loi — no la dau hieu ACL dang lam dung viec (W1.5) —
            # nhung no phai NOI RA, vi no doi cau tra loi cua ca cong cu.
            print(f"  (bo qua {path}: {type(loi).__name__})")
            continue
    return ""


def _ten_csdl(url: str) -> str:
    return url.rsplit("/", 1)[-1].split("?", 1)[0].strip().lower()


def _dung_url(url: str, ten_that: str, ten_dang_chay: str) -> None:
    """Ba rào. Vi phạm bất kỳ rào nào ⇒ **dừng**, không phải bỏ qua.

    ⛔ Bỏ qua là cách một sai lầm trở thành im lặng: bộ kiểm xanh, và không ai
       học được rằng cái rào đã nổ.
    """
    if "test" not in ten_that:
        raise SystemExit(
            f"⛔ TU CHOI: ten CSDL {ten_that!r} khong chua 'test'. Cong cu nay "
            "goi DROP/CREATE nen no chi chay tren mot CSDL VUT DI.")
    if ten_that == ten_dang_chay:
        raise SystemExit(
            f"⛔ TU CHOI: {ten_that!r} chinh la CSDL dang chay. Do la so credit "
            "that.")
    if not url.startswith(("postgresql", "postgres")):
        raise SystemExit(f"⛔ TU CHOI: {url.split('://')[0]} khong phai postgres.")


def _url_nhap(live: str, ten: str) -> str:
    """URL CSDL nháp — dựng từ **superuser**, không từ tài khoản ứng dụng.

    ⚠️ Đo 08/09: `CREATE DATABASE` chạy bằng `postgres` nên CSDL mới thuộc
       `postgres`, và tài khoản ứng dụng **không nối được vào nó**. Dùng lại
       URL của ứng dụng ở đây sẽ thất bại theo một cách trông y hệt "chưa tạo",
       và vòng lặp sẽ thử tạo lại mãi.

    ⛔ Dùng superuser ở đây **an toàn hơn**, không phải lỏng hơn: ba rào ở
       `_dung_url` đã chứng minh CSDL này là thứ vứt đi trước khi bất cứ gì
       chạm tới nó.
    """
    pw = _superuser_pw()
    if not pw:
        raise SystemExit(
            "⛔ khong doc duoc mat khau superuser "
            "(`secrets/postgres-superuser.txt`).")
    dia_chi = live.partition("://")[2].partition("@")[2].rsplit("/", 1)[0]
    return f"postgresql+psycopg://postgres:{pw}@{dia_chi}/{ten}"


def _tao_neu_thieu(url: str, ten: str, live: str) -> None:
    import sqlalchemy as sa

    try:
        e = sa.create_engine(url, connect_args={"connect_timeout": 5})
        with e.connect():
            pass
        e.dispose()
        print(f"  CSDL {ten} da co.")
        return
    except Exception as loi:                                # noqa: BLE001
        # ⚠️ Do 08/09: "xac thuc truot" va "CSDL chua tao" den day TRONG Y HET
        #    nhau, va vong lap se thu tao lai MAI. Neu ra thi lan sau doc duoc
        #    ngay thay vi doan.
        print(f"  (chua noi duoc toi {ten}: {type(loi).__name__})")

    quan_tri = _url_nhap(live, "postgres")
    e = sa.create_engine(quan_tri, isolation_level="AUTOCOMMIT",
                         connect_args={"connect_timeout": 5})
    try:
        with e.connect() as c:
            c.execute(sa.text(f'CREATE DATABASE "{ten}"'))
        print(f"  DA TAO CSDL {ten}.")
    except Exception as loi:                                # noqa: BLE001
        if "already exists" not in str(loi):
            raise
        print(f"  CSDL {ten} da co (tao boi mot luot truoc).")
    finally:
        e.dispose()


def _xoa_csdl_nhap(live: str, ten_dang_chay: str) -> None:
    """Xoá CSDL nháp của CHÍNH cây này. Hỏng thì nói, không làm đổi kết luận."""
    import sqlalchemy as sa
    from pg_ten_cay import cau_xoa_csdl_test

    cau = cau_xoa_csdl_test(ten_dang_chay, HAU_TO, GOC)
    e = sa.create_engine(_url_nhap(live, "postgres"), isolation_level="AUTOCOMMIT",
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


def _ep_utf8() -> None:
    """Cho phep tieng Viet + emoji trong bao cao ngay ca khi stdout bi HUNG.

    🔴 SU CO 28/09/2026. Buoc gate `migration tren postgres` do voi mot
       `UnicodeEncodeError` o `cp1252` — **trong chinh dong `print` bao ket qua**:

           print(f"    ⚠️ MIGRATION TAO ma MODEL KHONG KHAI: {thua}")
           UnicodeEncodeError: 'charmap' codec can't encode characters in
           position 4-5: character maps to <undefined>

    ⭐ Va day moi la phan dat. `thua` chi la mot CANH BAO (`xau = bool(thieu)`),
       nen lo ra dung phai bien thanh PASS kem mot dong canh bao. Cu chet trong
       luc **bao cao** da bien mot canh bao thanh mot **buoc do**, va dong thoi
       **giau mat noi dung** canh bao ay — nguoi doc thay mot traceback ve
       encoding va ⛔ khong he biet co bang nao lech luoc do.

       Mot cong cu do luong chet trong luc noi ket qua thi te hon mot cong cu
       khong chay: no bao dong SAI va giu lai dung thong tin can de biet la sai.
    """
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _ep_utf8()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--giu", action="store_true",
                    help="giu lai CSDL nhap sau khi chay (mac dinh: xoa)")
    args = ap.parse_args()

    live = (os.environ.get("LTT_DATABASE_URL") or "").strip() or _doc_env(
        "LTT_DATABASE_URL")
    if not live:
        print("BO QUA: khong tim thay LTT_DATABASE_URL.")
        return 0
    if not live.startswith(("postgresql", "postgres")):
        print("BO QUA: LTT_DATABASE_URL khong tro toi PostgreSQL.")
        return 0

    ten_dang_chay = _ten_csdl(live)
    # Moi cay mot CSDL test rieng (su co 17/09, tools/pg_ten_cay.py).
    sys.path.insert(0, str(GOC / "tools"))
    from pg_ten_cay import ten_csdl_test
    ten = ten_csdl_test(ten_dang_chay, HAU_TO, GOC)
    url = _url_nhap(live, ten)
    _dung_url(url, ten, ten_dang_chay)

    print(f"CSDL dang chay : {ten_dang_chay}   (KHONG cham toi)")
    print(f"CSDL nhap      : {ten}")
    _tao_neu_thieu(url, ten, live)

    try:
        return _do(url)
    finally:
        if not args.giu:
            _xoa_csdl_nhap(live, ten_dang_chay)


def _do(url: str) -> int:
    """Than phep do. Engine dong truoc khi `main` xoa CSDL nhap (DROP khong FORCE)."""
    import sqlalchemy as sa

    e = sa.create_engine(url)
    try:
        return _do_tren(e, url)
    finally:
        e.dispose()


def _do_tren(e, url: str) -> int:
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config

    import platform_core.db as dbmod                        # noqa: E402
    import platform_core.models                             # noqa: F401,E402
    # Don sach truoc khi chay: mot luot cu con sot bang se lam
    # `alembic upgrade` do vi "da ton tai", va do la mot cai do KHONG noi gi ve
    # migration.
    dbmod.Base.metadata.drop_all(e)
    with e.connect() as c:
        c.execute(sa.text("DROP TABLE IF EXISTS alembic_version"))
        c.commit()

    os.environ["LTT_DATABASE_URL"] = url
    cfg = Config(str(GOC / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)

    print("\n[1] alembic upgrade base -> head TREN POSTGRES THAT")
    command.upgrade(cfg, "head")
    print("    OK")

    print("\n[2] so luoc do SINH RA voi `Base.metadata`")
    ins = sa.inspect(e)
    that = set(ins.get_table_names())
    khai = set(dbmod.Base.metadata.tables)
    thieu = sorted(khai - that - {"alembic_version"})
    thua = sorted(that - khai - {"alembic_version"})
    print(f"    bang tren CSDL: {len(that)} | bang khai o model: {len(khai)}")
    if thieu:
        print(f"    ⛔ MODEL CO ma MIGRATION KHONG TAO: {thieu}")
    if thua:
        print(f"    ⚠️ MIGRATION TAO ma MODEL KHONG KHAI: {thua}")

    print("\n[3] chi muc BO PHAN co that su duoc tao khong")
    bo_phan = 0
    with e.connect() as c:
        rows = c.execute(sa.text(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname='public' AND indexdef LIKE '%WHERE%' "
            "ORDER BY indexname")).all()
    for ten_idx, _ in rows:
        bo_phan += 1
        print(f"    {ten_idx}")
    print(f"    tong: {bo_phan} chi muc bo phan")

    xau = bool(thieu)
    print("\nRESULT: " + ("FAIL" if xau else "PASS"))
    return 1 if xau else 0


if __name__ == "__main__":
    sys.exit(main())
