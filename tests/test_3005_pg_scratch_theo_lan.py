"""Mỗi làn một CSDL scratch riêng — bỏ khoá `postgres_test` (N-10, Task 0).

## Khoá này bảo vệ MỘT CÁI TÊN, không bảo vệ một tài nguyên độc quyền

Đo 24/09: một làn giữ `postgres_test` **78 phút**, và một làn phiên khác xếp hàng
sau nó — **cho một thứ lẽ ra không chặn ai**. Lý do khoá tồn tại: mọi làn dùng chung
**một** tên CSDL (`lttplatform_test`), và `test_423.moi_truong` gọi `drop_all` trên
nó. Cho mỗi làn một tên riêng thì hết xung đột và không cần khoá nào.

⚠️ **Khác `cpu_nhieu`, và đừng gộp hai thứ:** khoá CPU chia **sức tính** nên không bỏ
   được — nhả ra rồi giành lại chỉ **chậm hơn**. `postgres_test` chia một **cái tên**;
   nhả ra rồi giành lại có thể **sai kết quả**, nhưng cái tên thì **nhân bản được**.

⭐ Nó đóng luôn **M-11**: một `AsvRun` `running` mồ côi của làn khác tự nộp job vô
   hạn (`jobs` phình 1.274 dòng) làm trần 200 job thành trần **dùng chung**, nên trên
   CSDL đó không còn đo được *"vòng sửa có quay không"*. Mỗi làn một CSDL ⇒ không làn
   nào thấy rác của làn khác.

## ⛔ Tên phải suy từ WORKTREE, không từ PID

`test_1720_wf_dong_co_pg` mở **hai tiến trình** worker khác nhau và cả hai phải trở
về **CÙNG MỘT** CSDL scratch. Suy tên từ `os.getpid()` sẽ cho hai tên khác nhau và
làm bài đó hỏng theo một cách rất khó đọc. Nên phép suy phải **tất định theo cây**.
"""
from __future__ import annotations

import pathlib

import pytest
from _pytest.outcomes import Failed

from tests import pg_scratch

#: Tên định danh PostgreSQL: tối đa 63 byte (`NAMEDATALEN - 1`).
DAI_TOI_DA = 63

#: Gốc kho — tiến trình con phải chạy ở đây để `from tests import …` giải được.
_GOC = pathlib.Path(__file__).resolve().parents[1]

#: Thân bài của tiến trình con (làn B) dùng ở đối chứng cô lập. Để ở cấp
#: module vì người đọc cần thấy làn B làm GÌ mà không phải lần vào hàm.
THAN_LAN_B = """def test_drop_all_cua_lan_B():
    import os, sqlalchemy as sa
    from tests import pg_scratch
    import platform_core.models  # noqa: F401
    import platform_core.db as dbmod
    os.environ['LTT_DATABASE_URL'] = os.environ[pg_scratch.ENV]
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    dbmod.Base.metadata.drop_all(dbmod.get_engine())
"""

# 🔴 **Sáu phép kiểm về ĐẶT TÊN CSDL đã bị XOÁ khỏi tệp này, có chủ ý.**
#
#    Chúng chốt đường "một CSDL mỗi làn" — đường đã bỏ vì vai `ltt_app` không có
#    `CREATEDB`. Sau khi `scratch_url` thôi đổi tên CSDL, bốn trong sáu bài đó
#    **vẫn XANH** nhưng không còn chốt gì: chúng hỏi về một tên mà nay là hằng số.
#
# ⛔ Và một phép kiểm rỗng nghĩa mà vẫn xanh thì **tệ hơn một phép kiểm đỏ**: nó
#    trông y hệt độ phủ. Nên xoá, không để lại. Đường schema có bộ chốt riêng ở dưới.
def test_rao_AN_TOAN_van_con_nguyen(monkeypatch):
    """⛔ Bỏ khoá KHÔNG được kéo theo nới rào an toàn.

    `scratch_url` phải vẫn **hard-fail** khi tên CSDL không chứa `test` — rào đó là
    thứ duy nhất đứng giữa `drop_all` và CSDL đang phục vụ khách.
    """
    # ⛔ `monkeypatch`, khong `os.environ[...]` tho: dat thang se RO RI sang cac bai
    #    sau trong cung tep, va mot bai do vi bai truoc lam ban moi truong la mot
    #    gio dong ho bi mat.
    monkeypatch.setenv(pg_scratch.ENV,
                       "postgresql+psycopg://u:p@127.0.0.1:5432/lttplatform")
    # ⛔ `Failed`, khong `BaseException`: ruff B017 dung o day — mot `raises` qua
    #    rong se XANH ca khi ham nem `TypeError` vi mot loi go, tuc no khong con
    #    chung minh rang RAO da ban.
    with pytest.raises(Failed):
        pg_scratch.scratch_url("asvf-b1")


def test_bien_CHUA_DAT_thi_tra_RONG_chu_khong_nem(monkeypatch):
    """Hành vi cũ phải giữ: chưa đặt biến ⇒ `""` ⇒ bộ test dùng SQLite và skip."""
    monkeypatch.delenv(pg_scratch.ENV, raising=False)
    assert pg_scratch.scratch_url("asvf-b1") == ""
    assert pg_scratch.scratch_url() == ""


# ══════════════════════════════════════════════════════════════════════════════
#  Đường SCHEMA — không cần `CREATEDB`, và dọn được (Task 0 bản 2)
# ══════════════════════════════════════════════════════════════════════════════
#
# ⭐ **Vì sao đổi từ CSDL-mỗi-làn sang SCHEMA-mỗi-làn.** Vai `ltt_app` có
#    `rolcreatedb = False` nên không tạo được CSDL, nhưng **tạo và xoá được
#    SCHEMA** (điều phối đo 24/09). Ba cái được:
#
#      1. ⛔ không phải cấp `CREATEDB` cho vai app — không đổi thế an ninh
#         production, và cấp quyền cũng không gỡ được vì `pg_hba` là
#         `scram-sha-256` nên chỉ chủ dự án có mật khẩu `postgres`;
#      2. ⭐ `DROP SCHEMA ... CASCADE` dọn sạch ⇒ trả lời **N-11** (tích tụ CSDL
#         mồ côi) — phản biện mạnh nhất với bản đầu của Task 0;
#      3. không trần số làn.
#
# ⭐ Và bề mặt đã KIỂM, không đoán: `grep` thấy 13 tệp có `public.`, nhưng liệt kê
#    thật thì **0 bảng/cột** nào bị gán schema (`__table_args__ schema=` rỗng toàn
#    kho), `public.name`/`deprecated`/`execution_mode` là **biến Python**
#    (`public = project_tool(...)`), và `func.public.f_unaccent` là **hàm cấp
#    CSDL** — đã qualify tường minh nên nó đúng bất kể `search_path`.

def test_hai_lan_khac_nhau_cho_hai_SCHEMA_khac_nhau():
    a = pg_scratch.schema_lan("asvf-b1")
    b = pg_scratch.schema_lan("asvf-dich")
    assert a != b, (a, b)


def test_ten_schema_hop_le_voi_postgres():
    ten = pg_scratch.schema_lan("asvf-nghiem-thu-v2")
    assert len(ten) <= DAI_TOI_DA, f"{len(ten)} ky tu: {ten}"
    assert ten == ten.lower() and "-" not in ten, ten
    assert ten.replace("_", "").isalnum(), ten
    # ⛔ KHONG duoc tra `public`: xoa `public` bang CASCADE la xoa ca CSDL.
    assert ten != "public"


def test_schema_lan_TAT_DINH():
    assert pg_scratch.schema_lan("x1") == pg_scratch.schema_lan("x1")
    assert pg_scratch.schema_lan() == pg_scratch.schema_lan()


def test_search_path_LUON_co_public_o_sau():
    """⚠️ `public` phải còn trong `search_path`, và phải ở SAU schema của làn.

    🔑 `apps/chatltt/services/tim_doan.py` gọi `func.public.f_unaccent(...)` — một
       **hàm cấp CSDL**. Nó đã qualify tường minh nên nó sống sót; nhưng bỏ `public`
       khỏi `search_path` vẫn làm mọi thứ *khác* ở `public` biến mất khỏi tầm nhìn,
       nên giữ nó ở sau là rẻ và đúng.
    ⛔ Và phải ở SAU: nếu `public` đứng trước, `create_all` sẽ tạo bảng vào `public`
       và hai làn lại đụng nhau — tức bản sửa này thành vô hiệu mà vẫn xanh.
    """
    sp = pg_scratch.search_path("asvf-b1")
    assert sp.split(",") == ["asv_asvf_b1", "public"], sp


def test_cau_xoa_schema_TU_CHOI_public_va_ten_la():
    """⛔ `DROP SCHEMA public CASCADE` là xoá cả CSDL. Phải từ chối ở cửa."""
    for xau in ("public", "", "pg_catalog", 'a"; drop schema public; --'):
        with pytest.raises(ValueError):
            pg_scratch.cau_xoa_schema(xau)
    assert pg_scratch.cau_xoa_schema("asv_asvf_b1") == (
        'DROP SCHEMA IF EXISTS "asv_asvf_b1" CASCADE')


# ══════════════════════════════════════════════════════════════════════════════
#  Dọn THẬT, và CÔ LẬP thật — hai bước không được khai suông
# ══════════════════════════════════════════════════════════════════════════════

def _co_pg() -> str:
    """URL PostgreSQL scratch, hoặc `""`. ⛔ Không đọc `app.env` ở đây."""
    import os
    return (os.environ.get(pg_scratch.ENV) or "").strip()


PG = pytest.mark.skipif(not _co_pg(), reason=f"can {pg_scratch.ENV}")


def _chay_pytest_con(tmp_path, lan: str, than: str) -> tuple[int, str]:
    """Chạy MỘT tệp pytest trong tiến trình CON, với `LTT_PHIEN=<lan>`.

    🔑 Tiến trình con là điều kiện, không phải sự cầu kỳ: `pytest_sessionstart` và
       `pytest_sessionfinish` **chỉ chạy một lần mỗi phiên**, nên không cách nào quan
       sát chúng từ bên trong phiên đang chạy. Muốn chứng minh *"bước dọn thật sự
       chạy"* thì phải có một phiên khác để xem.
    """
    import os
    import subprocess
    import sys

    tep = tmp_path / f"test_con_{lan.replace('-', '_')}.py"
    tep.write_text(than, encoding="utf-8")
    moi = dict(os.environ)
    moi["LTT_PHIEN"] = lan
    moi[pg_scratch.BIEN_THEO_LAN] = "1"
    moi["PYTHONIOENCODING"] = "utf-8"
    moi.pop("PGOPTIONS", None)
    # 🔴 **`-p tests.conftest` la dieu kien, khong phai trang tri.**
    #
    #    pytest tim `conftest.py` theo thu muc cua TEP TEST, khong theo `cwd`. Tep con
    #    nam trong `tmp_path` (ngoai `tests/`), nen `tests/conftest.py` **khong duoc
    #    nap** va `pytest_sessionstart` khong chay ⇒ schema khong duoc tao, va phep
    #    kiem do voi mot thong bao khong nhac gi den conftest.
    #
    # ⛔ Cach khac la ghi tep con VAO `tests/` — bo, vi no de rac trong cay lam viec
    #    va dam voi mot luot gate dang chay. Nap conftest nhu mot PLUGIN thi khong.
    r = subprocess.run([sys.executable, "-m", "pytest", str(tep), "-q",
                        "-p", "tests.conftest",
                        "-p", "no:randomly", "-p", "no:cacheprovider"],
                       cwd=str(_GOC), env=moi, capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _schema_dang_co(url: str) -> set:
    import sqlalchemy as sa
    e = sa.create_engine(url)
    try:
        with e.connect() as c:
            return {r[0] for r in c.execute(sa.text(
                "select nspname from pg_namespace where nspname like 'asv_%'"))}
    finally:
        e.dispose()


@PG
def test_DON_that_su_chay_o_cuoi_phien(tmp_path):
    """⛔ Không khai *"có dọn"* — chứng minh schema BIẾN MẤT sau khi phiên con xong.

    🔴 Đây là bước trả lời **N-11**: bản đầu của Task 0 tạo một CSDL mỗi làn và
       **không có đường dọn**, nên nó đổi *một khoá chặn 78 phút* thành *N CSDL mồ
       côi tích tụ* — đúng cái `tests/test_2300` canh.
    """
    url = _co_pg()
    lan = "asvf-thu-don"
    ten = pg_scratch.schema_lan(lan)

    # 🔴 **DON TRUOC, dung `assert` rang no vang.**
    #
    #    Ban dau dong nay la `assert ten not in _schema_dang_co(url)`. Do that: chay
    #    hai lan lien tiep cho **do roi xanh** — vi mot luot bi ngat (hoac buoc don
    #    cua phien con hong) de lai schema, lam lan chay SAU do o ngay dong dau, roi
    #    chinh lan do don sach nen lan THU BA lai xanh.
    #
    # ⛔ Tuc phep kiem phu thuoc vao **ket qua cua lan truoc** — dung cai no ton tai
    #    de chan. Va no lat do/xanh ma khong ai doi mot dong ma, tuc no se bi cho la
    #    "nhieu" va bi chay lai cho den khi xanh.
    #
    # ⭐ Mot phep kiem phai tu dua minh ve trang thai dau, khong doi moi truong sach.
    pg_scratch.xoa_schema(url, lan)
    assert ten not in _schema_dang_co(url), "khong don duoc schema truoc khi thu"

    ma, ra = _chay_pytest_con(tmp_path, lan, (
        "def test_co_schema():\n"
        "    import os, sqlalchemy as sa\n"
        "    from tests import pg_scratch\n"
        "    ten = pg_scratch.schema_lan()\n"
        "    e = sa.create_engine(os.environ[pg_scratch.ENV])\n"
        "    with e.connect() as c:\n"
        "        co = list(c.execute(sa.text(\n"
        "            \"select 1 from pg_namespace where nspname = :t\"), {'t': ten}))\n"
        "    assert co, f'phien con khong tao schema {ten}'\n"))
    try:
        assert ma == 0, ra[-1500:]
        assert ten not in _schema_dang_co(url), (
            f"schema {ten} CON LAI sau khi phien con xong — buoc don khong chay")
    finally:
        # ⛔ Do la bai ve DON, nen no khong duoc la bai de lai rac.
        pg_scratch.xoa_schema(url, lan)


@PG
def test_DOI_CHUNG_CO_LAP_mot_ben_drop_all_ben_kia_khong_bi_anh_huong(tmp_path):
    """⛔ **BƯỚC KHÔNG ĐƯỢC BỎ.** Đây là điều DUY NHẤT chứng minh **cô lập**.

    Mọi bài ở trên chỉ chứng minh **tên khác nhau** — mà tên khác nhau không phải
    thứ khoá `postgres_test` đang bảo vệ. Nó bảo vệ việc `drop_all` của làn này
    **không kéo bàn ra từ dưới chân** làn khác.

    🔑 Cách dựng: làn A tạo một bảng trong schema của nó và ghi một dòng. Rồi một
       tiến trình CON của làn B gọi `create_all` + `drop_all` trên schema của **nó**.
       Sau đó dòng của làn A **phải còn**.

    ⚠️ `drop_all` chỉ xoá bảng nó thấy qua `search_path`. Nên nếu `search_path` bị
       đặt sai — ví dụ `public` đứng TRƯỚC schema của làn — thì làn B sẽ xoá bảng của
       làn A. Đó đúng là hỏng hóc bài này đi tìm, và cũng là lý do
       `test_search_path_LUON_co_public_o_sau` tồn tại.
    """
    import sqlalchemy as sa

    url = _co_pg()
    lan_a, lan_b = "asvf-colap-a", "asvf-colap-b"
    ten_a = pg_scratch.schema_lan(lan_a)
    # Tu dua ve trang thai dau (xem ghi chu o bai tren).
    pg_scratch.xoa_schema(url, lan_a)
    pg_scratch.xoa_schema(url, lan_b)
    pg_scratch.bao_dam_schema(url, lan_a)
    try:
        e = sa.create_engine(
            url, isolation_level="AUTOCOMMIT",
            connect_args={"options": f"-c search_path={ten_a},public"})
        try:
            with e.connect() as c:
                c.execute(sa.text("create table if not exists thu_co_lap "
                                  "(id int primary key)"))
                c.execute(sa.text("insert into thu_co_lap values (1) "
                                  "on conflict do nothing"))
        finally:
            e.dispose()

        ma, ra = _chay_pytest_con(tmp_path, lan_b, THAN_LAN_B)
        assert ma == 0, ra[-1500:]

        e = sa.create_engine(
            url, connect_args={"options": f"-c search_path={ten_a},public"})
        try:
            with e.connect() as c:
                con = list(c.execute(sa.text("select id from thu_co_lap")))
        finally:
            e.dispose()
        assert con == [(1,)], (
            f"lan B `drop_all` da cham vao schema cua lan A: {con!r}. "
            f"CO LAP KHONG DAT — khoa `postgres_test` van can thiet.")
    finally:
        pg_scratch.xoa_schema(url, lan_a)
        pg_scratch.xoa_schema(url, lan_b)
