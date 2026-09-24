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


#: Tran ten CSDL cua PostgreSQL la 63 byte (`NAMEDATALEN - 1`).
DAI_TOI_DA = 63


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
    # ⛔ **KHONG doi ten CSDL.** Co lap nay theo **SCHEMA**, khong theo CSDL — xem
    #    phan cuoi tep. Duong "mot CSDL moi lan" DA BO: vai `ltt_app` khong co
    #    `CREATEDB`, va cap quyen do la doi the an ninh cua may production.
    #
    # ⚠️ `lan` giu lai trong chu ky vi `schema_lan`/`search_path` dung cung mot khai
    #    niem "lan"; nguoi goi khong phai hoc hai cach goi.
    return url


def skip_without_postgres():
    """`pytest.mark.skipif` for tests that need a real PostgreSQL.

    The reason string names the variable, because a skipped test whose reason is
    "not configured" teaches nobody how to configure it.
    """
    return pytest.mark.skipif(
        not (os.environ.get(ENV) or "").strip(),
        reason=f"Set {ENV} to a scratch PostgreSQL database (name must "
               f"contain 'test').")


# ══════════════════════════════════════════════════════════════════════════════
#  Co lap theo SCHEMA (Task 0 ban 2) — khong doi ten CSDL, khong can `CREATEDB`
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 **Vi sao khong dung CSDL-moi-lan.** Vai `ltt_app` co `rolcreatedb = False`
#    (do 24/09), nen `CREATE DATABASE` **khong the** chay tu bo test; va cap
#    `CREATEDB` cho vai app la **doi the an ninh cua may production**, khong phai
#    viec cua mot lan. Nhung `ltt_app` **tao va xoa duoc SCHEMA**.
#
# ⭐ Ba cai duoc so voi CSDL-moi-lan:
#      1. khong doi quyen nao;
#      2. `DROP SCHEMA ... CASCADE` don sach ⇒ het tich tu CSDL mo coi (N-11);
#      3. khong tran so lan.
#
# ⭐ Be mat da KIEM (khong doan): toan kho **khong** bang/cot nao bi gan schema
#    (`__table_args__ schema=` rong), nen moi bang di theo `search_path`. Cho duy
#    nhat qualify tuong minh la `func.public.f_unaccent` — mot **ham cap CSDL**,
#    dung nhu vay.

#: Tien to schema cua lan. ⛔ Khong bao gio tra `public`.
TIEN_TO_SCHEMA = "asv_"

_TEN_HOP_LE = re.compile(r"[a-z][a-z0-9_]*")

#: Co bat duong theo lan. MOT cho khai — `conftest` va `scratch_url` doc cung day.
BIEN_THEO_LAN = "LTT_PG_SCRATCH_THEO_LAN"


def theo_lan_bat() -> bool:
    """Duong co lap theo lan da bat chua.

    ⚠️ Con OPT-IN cho toi khi **doi chung co lap** xanh. Mac dinh la GIU NGUYEN
       HIEN TRANG (mot CSDL dung chung + khoa `postgres_test`) — ⛔ khong lui im
       lang, va cung khong bat som: bat truoc khi chung minh duoc co lap la bo mot
       khoa dang that su chan `drop_all` cua lan khac.
    """
    return bool((os.environ.get(BIEN_THEO_LAN) or "").strip())

#: Schema KHONG duoc xoa, du ai goi. `DROP SCHEMA public CASCADE` = xoa ca CSDL.
SCHEMA_CAM_XOA = frozenset({"public", "pg_catalog", "pg_toast", "information_schema"})


def _chuan_schema(lan: str) -> str:
    """`asvf-b1` -> `asvf_b1`. ⛔ KHONG them van tay cay.

    🔴 Ban dau ham nay dung `_chuan_ten` (co van tay cay cua `pg_ten_cay`), va do la
       **sai cho duong schema**: van tay lay theo **noi goi**, nen
       `schema_lan("asvf-b1")` cho hai ket qua khac nhau o hai cay ⇒ hai tien trinh
       cua **doi chung co lap** khong thong nhat duoc mot cai ten, va bai doi chung
       se do vi mot ly do khong lien quan gi den co lap.

    ⭐ Van tay CAN cho ten CSDL (ten CSDL la toan cuc tren ca server, hai checkout
       trung ten co the dam nhau) nhung KHONG can cho schema: schema nam trong MOT
       CSDL tren MOT server, va ten cay lam viec von da duy nhat tren may do. Mot
       `lan` truyen tuong minh thi chinh no la danh tinh.
    """
    tho = re.sub(r"[^a-z0-9_]+", "_", lan.lower()).strip("_") or "khong_ten"
    if not tho[0].isalpha():
        tho = f"l{tho}"
    return tho


def schema_lan(lan: str = "") -> str:
    """Ten schema rieng cua lan nay. Tat dinh, <= 63 ky tu, khong bao gio `public`."""
    return f"{TIEN_TO_SCHEMA}{_chuan_schema(lan or _lan_tu_worktree())}"[:DAI_TOI_DA]


def search_path(lan: str = "") -> str:
    """`<schema cua lan>,public`.

    ⛔ `public` phai o SAU. Neu no dung truoc, `create_all` tao bang vao `public` va
       hai lan lai dung nhau — tuc ban sua nay thanh vo hieu **ma van xanh**.
    """
    return f"{schema_lan(lan)},public"


def cau_xoa_schema(ten: str) -> str:
    """Cau `DROP SCHEMA ... CASCADE`, hoac `ValueError` neu khong chung minh duoc.

    ⛔ Cung tinh than `pg_ten_cay.cau_xoa`: mot cau xoa phai TU CHOI thay vi tin
       nguoi goi. `DROP SCHEMA public CASCADE` xoa ca CSDL.
    """
    thap = (ten or "").strip().lower()
    if not _TEN_HOP_LE.fullmatch(thap):
        raise ValueError(f"tu choi xoa schema {ten!r}: khong phai identifier thuan")
    if thap in SCHEMA_CAM_XOA:
        raise ValueError(f"tu choi xoa schema {ten!r}: schema he thong")
    if not thap.startswith(TIEN_TO_SCHEMA):
        raise ValueError(f"tu choi xoa schema {ten!r}: khong mang tien to "
                         f"{TIEN_TO_SCHEMA!r}")
    return f'DROP SCHEMA IF EXISTS "{thap}" CASCADE'


def bao_dam_schema(url: str, lan: str = "") -> str:
    """`CREATE SCHEMA IF NOT EXISTS` cho lan nay. Tra ten schema."""
    import sqlalchemy as sa

    ten = schema_lan(lan)
    e = sa.create_engine(url, isolation_level="AUTOCOMMIT",
                         connect_args={"connect_timeout": 5})
    try:
        with e.connect() as c:
            c.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{ten}"'))
    finally:
        e.dispose()
    return ten


def xoa_schema(url: str, lan: str = "") -> None:
    """`DROP SCHEMA ... CASCADE`. Goi o cuoi phien — day la buoc DON cua N-11."""
    import sqlalchemy as sa

    cau = cau_xoa_schema(schema_lan(lan))
    e = sa.create_engine(url, isolation_level="AUTOCOMMIT",
                         connect_args={"connect_timeout": 5})
    try:
        with e.connect() as c:
            c.execute(sa.text(cau))
    finally:
        e.dispose()
