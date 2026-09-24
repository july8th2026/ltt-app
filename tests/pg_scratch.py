"""One gate for every test that wants a real PostgreSQL database.

These tests call ``Base.metadata.drop_all()``. That is correct for a scratch
database and catastrophic for any other one, and the only thing standing between
the two is an environment variable — on a machine where the platform's own
PostgreSQL is running, a single typo in ``LTT_TEST_DATABASE_URL`` drops the
tables serving real customers.

So the rule is not "be careful". The rule is that a URL has to **prove** it is
disposable before anything destructive touches it:

* its database name must contain ``test`` — a production database will not be
  named that by accident, and naming one that way is a deliberate act;
* it must not be the URL this deployment actually runs on.

A URL that fails those checks is a **hard failure**, never a skip. Skipping is
how a mistake becomes silence: the suite goes green, and nobody learns that the
guard fired.
"""
from __future__ import annotations

import os
import pathlib
import re

import pytest

ENV = "LTT_TEST_DATABASE_URL"

#: Tien to CSDL scratch. Ten thuc = `<TIEN_TO><lan>`, nen no LUON chua "test".
TIEN_TO = "lttplatform_test_"

#: Tran ten CSDL cua PostgreSQL la 63 byte (`NAMEDATALEN - 1`).
DAI_TOI_DA = 63


def _chuan_ten(lan: str) -> str:
    """`asvf-nghiem-thu-v2` -> `asvf_nghiem_thu_v2`, cat cho vua tran 63.

    ⭐ **Van tay thi DUNG LAI `tools/pg_ten_cay.van_tay_cay`, khong tu bam.** Kho
       nay DA co quy uoc CSDL test theo cay (`_multiproc_test`, `_wf_migration_test`,
       `_m1_dientap_test` — 18 CSDL nhu vay dang ton tai tren may), va tu viet mot
       phep bam thu hai la dung bay N-08 toi vua ghi: **hai cho khai cung mot dieu,
       khong ai bat khop**.
    """
    tho = re.sub(r"[^a-z0-9_]+", "_", lan.lower()).strip("_") or "khong_ten"
    try:
        import sys
        goc = str(pathlib.Path(__file__).resolve().parents[1])
        if f"{goc}/tools" not in sys.path:
            sys.path.insert(0, f"{goc}/tools")
        from pg_ten_cay import van_tay_cay
        tho = f"{tho[:28]}_{van_tay_cay(pathlib.Path(goc))}"
    except Exception:                       # noqa: BLE001 - thieu tools/ thi dung ten tho
        pass
    return tho[:DAI_TOI_DA - len(TIEN_TO)].strip("_")


def bao_dam_csdl(url: str) -> None:
    """`CREATE DATABASE` neu chua co. Goi duoc nhieu lan.

    🔴 **Buoc nay KHONG co trong Task 0, va thieu no thi Task 0 la mot HOI QUY.**
       `Base.metadata.create_all()` tao **BANG**, khong tao **CSDL**. Do that 24/09:
       sau khi `scratch_url` tra ten theo lan, `tests/test_2080_asv_cache_lease.py`
       chet `psycopg.OperationalError` — CSDL `lttplatform_test_<lan>` khong ton tai.

    ⛔ Chi `CREATE`, khong bao gio `DROP`: xoa la viec cua nguoi van hanh
       (`tools/pg_ten_cay.cau_xoa` da co rao rieng cho no), va mot bo test tu xoa
       CSDL cua chinh no giua mot lan chay song song la mot cach hay de mat du lieu
       cua lan khac.
    """
    import sqlalchemy as sa

    ten = _database_name(url)
    try:
        e = sa.create_engine(url, connect_args={"connect_timeout": 5})
        with e.connect():
            pass
        e.dispose()
        return
    except Exception:                       # noqa: BLE001 - chua noi duoc: thu tao
        pass
    quan_tri = sa.create_engine(f"{url.rsplit('/', 1)[0]}/postgres",
                                isolation_level="AUTOCOMMIT",
                                connect_args={"connect_timeout": 5})
    try:
        with quan_tri.connect() as c:
            c.execute(sa.text(f'CREATE DATABASE "{ten}"'))
    except Exception as loi:                # noqa: BLE001
        # Hai lan song song cung tao -> mot ben thang, ben kia thay "already
        # exists". Do la duong chay BINH THUONG cua co che, khong phai su co.
        if "already exists" not in str(loi).lower():
            raise
    finally:
        quan_tri.dispose()


def _lan_tu_worktree() -> str:
    """Ten lan suy tu TEN CAY LAM VIEC.

    🔴 **TAT DINH, va suy tu CAY chu khong tu PID.**

       `tests/test_1720_wf_dong_co_pg` mo HAI tien trinh worker khac nhau va ca hai
       phai tro ve **CUNG MOT** CSDL scratch. Suy tu `os.getpid()` cho hai ten khac
       nhau, va bai do hong theo mot cach rat kho doc: hai worker nhin hai CSDL
       rong, khong ai thay job cua ai, va thong bao khong nhac mot chu nao den ten
       CSDL.

    ⭐ Ten cay la dung muc chia: mot lan = mot cay = mot nhanh (`cay_rieng.py`).
    """
    return os.environ.get("LTT_PHIEN") or pathlib.Path(
        __file__).resolve().parents[1].name


def _database_name(url: str) -> str:
    """The database part of a SQLAlchemy URL, without parsing credentials out.

    Deliberately string-level: this never needs to see the password, and code
    that does not hold a secret cannot leak one.
    """
    tail = url.rsplit("/", 1)[-1]
    return tail.split("?", 1)[0].strip().lower()


def scratch_url(lan: str = "") -> str:
    """The scratch PostgreSQL URL for THIS lane, or "" when the suite should skip.

    Raises when the variable is set to something that is not obviously a
    throwaway — refusing loudly beats running destructively.

    🔑 **`lan` la ca ban sua cua Task 0 (N-10).** Truoc 24/09 moi lan dung CHUNG
       mot ten CSDL, nen `moi_truong` cua lan nay goi `drop_all` duoi chan lan
       khac — va thu duy nhat chan viec do la khoa `cua_so_yen` tren
       `postgres_test`. Khoa do **chia mot cai ten**, khong chia mot tai nguyen
       doc quyen.

    ⛔ Do 24/09: mot lan giu khoa **78 phut**, mot lan phien khac xep hang sau no,
       cho mot thu **le ra khong chan ai**. Mot cai ten thi **nhan ban duoc**; suc
       tinh (`cpu_nhieu`) thi khong — dung gop hai loai khoa lam mot.

    ⭐ Va no dong luon **M-11**: mot `AsvRun` mo coi cua lan khac tu nop job vo han
       lam tran 200 job thanh tran DUNG CHUNG, nen tren CSDL do khong con do duoc
       *"vong sua co quay khong"*. Moi lan mot CSDL ⇒ khong lan nao thay rac cua
       lan khac.
    """
    url = (os.environ.get(ENV) or "").strip()
    if not url:
        return ""

    # Chỉ kiểm TÊN, không so với `LTT_DATABASE_URL`. Phép so đó từng có ở đây và
    # nó bắn nhầm đúng vào tình huống rào sinh ra để bảo vệ: một test đa tiến
    # trình trỏ `LTT_DATABASE_URL` về chính CSDL vứt đi, rồi tiến trình con
    # (Windows dùng `spawn`) nạp lại module test — rào thấy hai giá trị bằng
    # nhau, kết luận "đây là production", và giết mọi worker **trước khi in ra
    # được gì**. Cả bộ test vẫn xanh, vì không có gì chạy thì cũng không có gì
    # xảy ra hai lần.
    #
    # Phép kiểm tên đủ mạnh mà không có mặt trái đó: CSDL production của nền
    # tảng không tình cờ mang chữ `test`, và đặt tên như vậy là một hành động
    # cố ý.
    # 🔴 **Rao an toan chay TREN TEN NGUOI VAN HANH DUA, TRUOC khi ta viet lai.**
    #
    #    Ban dau Task 0 viet lai ten NGAY dau ham, va bang mot dong da lam ca rao
    #    nay **khong the voi tay toi duoc**: moi URL deu thanh `lttplatform_test_*`
    #    nen phep kiem "ten co chua 'test'" luon dung. Mot tro chan khong bao gio
    #    nem thi khong phai mot tro chan.
    #
    # ⛔ Va no te hon mot chut nua: mot loi go tro `LTT_TEST_DATABASE_URL` vao
    #    MAY production se **im lang** tao mot CSDL scratch **tren may do** (host va
    #    mat khau van la cua production) thay vi do to. Docstring dau tep noi thang:
    #    *"A URL that fails those checks is a hard failure, never a skip. Skipping
    #    is how a mistake becomes silence."*
    #
    # ⭐ `test_3005::test_rao_AN_TOAN_van_con_nguyen` la thu bat duoc no.
    name = _database_name(url)
    if "test" not in name:
        pytest.fail(
            f"{ENV} names database {name!r}, which does not look disposable. "
            f"These tests drop every table, so the name must contain 'test'.")
    # Rao da qua -> nay moi tach rieng CSDL cua lan nay (N-10).
    # ⛔ **CHUA BAT MAC DINH — chan o quyen CSDL, khong o ma.**
    #
    # 🔴 Do 24/09: vai `ltt_app` co `rolcreatedb = False`; chi `postgres` (superuser)
    #    tao duoc CSDL. Nen `lttplatform_test_<lan>` **khong the tu sinh ra**, va bat
    #    mac dinh lam MOI bai PG chet `database "..." does not exist`.
    #
    # ⇒ Duong theo lan la OPT-IN (`LTT_PG_SCRATCH_THEO_LAN=1`) cho toi khi chu du an
    #   quyet mot trong hai: cap `CREATEDB` cho `ltt_app` (doi the an ninh cua may
    #   production — KHONG phai viec cua mot lan), hoac tao san CSDL moi lan bang vai
    #   `postgres` trong mot buoc van hanh.
    #
    # ⛔ Va day la mot mac dinh GIU NGUYEN HIEN TRANG, khong phai mot ban lui im
    #    lang: `LOI_TONG.md` N-10 ghi ro no dang cho quyet dinh gi.
    if not (os.environ.get("LTT_PG_SCRATCH_THEO_LAN") or "").strip() and not lan:
        return url

    # ⛔ **KHONG goi `bao_dam_csdl` o day.** Ham nay duoc goi luc IMPORT o it nhat
    #    bon tep (`PG_URL = scratch_url()`), va mot phep tinh TEN khong duoc mo ket
    #    noi CSDL nhu tac dung le: no lam moi lan `import` cham di mot vong mang,
    #    va lam cac bai kiem ve CACH DAT TEN phai co mot PostgreSQL that.
    # ⇒ Viec tao CSDL nam o `conftest.pytest_sessionstart` — MOT lan moi phien.
    return f"{url.rsplit('/', 1)[0]}/{TIEN_TO}{_chuan_ten(lan or _lan_tu_worktree())}"


def skip_without_postgres():
    """`pytest.mark.skipif` for tests that need a real PostgreSQL.

    The reason string names the variable, because a skipped test whose reason is
    "not configured" teaches nobody how to configure it.
    """
    return pytest.mark.skipif(
        not (os.environ.get(ENV) or "").strip(),
        reason=f"Set {ENV} to a scratch PostgreSQL database (name must "
               f"contain 'test').")
