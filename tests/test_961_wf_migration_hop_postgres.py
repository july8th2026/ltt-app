"""LTT WORKFLOW V2 · `R4` — migration phải hợp PostgreSQL, không chỉ hợp SQLite.

🔴 Rủi ro `R4` (`27_29 §29`) nói thẳng, và tôi **đã mắc đúng nó**:

    "`31+N` do tren SQLite; ke hoach truy van Postgres khac.
     Do lai tren Postgres TRUOC dot 2."

Tôi đo cả năm đợt trên SQLite tạm. Lượt kiểm nào cũng xanh. Rồi khi compile DDL
cho dialect PostgreSQL:

    BOOLEAN DEFAULT 1     <- PostgreSQL TU CHOI
    BOOLEAN DEFAULT 0        "column is of type boolean but default expression
                              is of type integer"

**Sáu cột, ba migration của tôi.** SQLite nhận `DEFAULT 1` nên mọi phép kiểm của
tôi xanh; production chạy PostgreSQL nên nó sẽ chết ở `alembic upgrade head` —
tức **sau `Stop-Service`**, chỗ tệ nhất.

⭐ Vì sao bộ kiểm cũ không thể bắt: nó chạy migration trên **sqlite tạm**, và câu
   hỏi nó trả lời là *"migration chạy được không"* — trên SQLite. Câu cần hỏi là
   *"migration chạy được trên **CSDL mà production dùng** không"*. Một trục thiếu.

⇒ Phép kiểm dưới đây **không cần một PostgreSQL sống**: nó compile DDL cho
  dialect PostgreSQL và soi chuỗi sinh ra. Rẻ, tất định, chạy ở mọi máy.

⚠️ Nó **không** thay được một lượt chạy thật trên Postgres — nó bắt lỗi **cú
   pháp/kiểu**, không bắt lỗi **kế hoạch truy vấn**. Phần còn lại của `R4` (đo
   `M1`/`M2` trên Postgres thật) vẫn còn nợ, và nó cần một CSDL vứt đi mà
   `secrets/` đang chặn **cố ý**.
"""
from __future__ import annotations

import pathlib
import re

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

BANG_V2 = (
    "workflow", "workflow_draft", "workflow_version", "workflow_version_node",
    "workflow_version_edge", "workflow_run", "node_run", "node_run_snapshot",
    "waitpoint", "waitpoint_signal", "node_run_waitpoint", "wakeup",
    "foreach_vong", "foreach_muc", "artifact", "workflow_trigger",
)

_THU_MUC = pathlib.Path(__file__).resolve().parent.parent / "alembic" / "versions"

#: Chuỗi số nguyên làm mặc định cho một cột BOOLEAN. Đây là **chính** lỗi đã mắc.
_BOOL_SO = re.compile(r"sa\.Boolean\(\)[^)]*?server_default=sa\.text\(\s*[\"'](\d+)[\"']",
                      re.S)


def _bang(ten: str):
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401

    return dbmod.Base.metadata.tables[ten]


# ── Lỗi đã mắc: BOOLEAN DEFAULT <số> ─────────────────────────────────────────

def test_KHONG_migration_nao_dat_BOOLEAN_mac_dinh_bang_SO():
    """🔴 `BOOLEAN DEFAULT 1` chạy trên SQLite, **chết** trên PostgreSQL.

    Quét **mọi** migration của kho, không riêng của Workflow V2: lớp lỗi này
    không thuộc về một chương trình nào, nó thuộc về *thói quen viết migration
    rồi kiểm trên SQLite*.
    """
    pham = []
    for f in sorted(_THU_MUC.glob("*.py")):
        noi_dung = f.read_text(encoding="utf-8")
        for m in _BOOL_SO.finditer(noi_dung):
            dong = noi_dung[:m.start()].count("\n") + 1
            pham.append(f"{f.name}:{dong} server_default=sa.text({m.group(1)!r})")

    assert pham == [], (
        "BOOLEAN mac dinh bang so — PostgreSQL tu choi:\n  "
        + "\n  ".join(pham)
        + "\nDung sa.text('true') / sa.text('false') — chay duoc CA HAI dialect.")


def test_doi_chung_bo_do_BAT_duoc_mau_xau():
    """Đối chứng cho bài trên: mẫu regex phải thật sự khớp.

    Không có bài này, `test_...KHONG_migration_nao...` xanh **cả khi** mẫu sai
    và không khớp gì — một phép kiểm quét-rồi-không-thấy-gì luôn xanh, và nó
    xanh giống hệt nhau dù bộ quét hỏng hay kho sạch.
    """
    xau = '''sa.Column("x", sa.Boolean(), nullable=False,
                  server_default=sa.text("1")),'''
    tot = '''sa.Column("x", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),'''
    assert _BOOL_SO.search(xau) is not None, "bo do KHONG bat duoc mau xau"
    assert _BOOL_SO.search(tot) is None, "bo do bat NHAM mau tot"


# ── DDL compile được cho PostgreSQL ──────────────────────────────────────────

@pytest.mark.parametrize("ten", BANG_V2)
def test_moi_bang_V2_compile_duoc_cho_POSTGRES(ten):
    ddl = str(CreateTable(_bang(ten)).compile(dialect=postgresql.dialect()))
    assert ddl.strip().upper().startswith("CREATE TABLE")
    assert not re.search(r"BOOLEAN DEFAULT \d", ddl), (
        f"{ten}: BOOLEAN DEFAULT <so> — PostgreSQL tu choi\n{ddl}")


@pytest.mark.parametrize("ten", BANG_V2)
def test_moi_bang_V2_compile_duoc_cho_SQLITE(ten):
    """Cùng lược đồ phải chạy trên **cả hai** — test dùng SQLite, production Postgres."""
    ddl = str(CreateTable(_bang(ten)).compile(dialect=sqlite.dialect()))
    assert ddl.strip().upper().startswith("CREATE TABLE")


# ── Chỉ mục bộ phận — thứ khác nhau nhiều nhất giữa hai dialect ──────────────

def test_BAY_chi_muc_bo_phan_deu_giu_menh_de_WHERE_tren_POSTGRES():
    """⭐ Chỉ mục bộ phận là chỗ hai dialect khác nhau nhiều nhất.

    Mất mệnh đề `WHERE` thì chỉ mục **vẫn tạo được** và truy vấn **vẫn chạy** —
    chỉ là nó phình theo mọi hàng đã chết, và không ai thấy cho tới khi bảng
    lớn. Một khiếm khuyết im lặng, nên phải ghim bằng con số.
    """
    pg = postgresql.dialect()
    thay = {}
    for ten in BANG_V2:
        for idx in _bang(ten).indexes:
            s = str(CreateIndex(idx).compile(dialect=pg))
            if " WHERE " in s:
                thay[idx.name] = s

    mong = {
        "ux_workflow_run_idem", "ix_waitpoint_due", "ux_waitpoint_idem",
        "ix_wakeup_due", "ix_foreach_muc_chua_xong", "ix_artifact_expiry",
        "ix_trigger_due",
        # P3 — con cua `core.call_workflow` (`20260924_1500_wf_run_con`).
        "ix_workflow_run_parent",
        # P4 — bo quet HET HAN di bang keyset cursor, nen chi muc phai mang
        # `(het_han_luc, id)` theo dung thu tu (`cho_doi.quet_het_han`).
        "ix_waitpoint_het_han",
    }
    assert set(thay) == mong, f"thieu/thua chi muc bo phan: {set(thay) ^ mong}"


def test_chi_muc_bo_phan_dung_BOOLEAN_kieu_POSTGRES():
    """`WHERE xong = 0` chạy trên SQLite; PostgreSQL cần `xong = false`."""
    pg = postgresql.dialect()
    for ten in BANG_V2:
        for idx in _bang(ten).indexes:
            s = str(CreateIndex(idx).compile(dialect=pg))
            assert not re.search(r"WHERE\s+\w+\s*=\s*[01]\b", s), (
                f"{idx.name}: menh de WHERE dung so cho boolean tren PG\n{s}")


# ── Bất biến: model và migration phải khai CÙNG một tập bảng ────────────────

def test_16_bang_V2_deu_co_trong_model():
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401

    thieu = [t for t in BANG_V2 if t not in dbmod.Base.metadata.tables]
    assert thieu == [], f"bang khai trong test ma khong co model: {thieu}"


def test_moi_bang_V2_deu_duoc_MOT_migration_tao_ra():
    """Bảng có model mà không migration nào tạo ⇒ chạy được ở test, chết ở production.

    Test dùng `Base.metadata.create_all()`, production dùng `alembic`. Hai đường
    khác nhau, và chỉ đường thứ hai là thật.
    """
    noi_dung = "\n".join(f.read_text(encoding="utf-8")
                         for f in _THU_MUC.glob("*.py"))
    thieu = [t for t in BANG_V2
             if f'create_table(\n        "{t}"' not in noi_dung
             and f'create_table("{t}"' not in noi_dung]
    assert thieu == [], f"co model nhung KHONG migration nao tao: {thieu}"


def test_khong_bang_V2_nao_dung_JSONB_rieng_cua_postgres():
    """Lược đồ phải chạy trên cả hai. `sa.JSON()` portable; `JSONB` thì không.

    Ghim vì `JSONB` là thứ rất dễ bị thêm vào sau — nó nhanh hơn trên Postgres,
    và nó làm mọi phép kiểm chạy SQLite **không chạy nữa**.
    """
    for ten in BANG_V2:
        for cot in _bang(ten).columns:
            assert not isinstance(cot.type, postgresql.JSONB), (
                f"{ten}.{cot.name} dung JSONB — bo test chay SQLite se vo")
            if isinstance(cot.type, sa.JSON):
                assert str(cot.type.compile(dialect=sqlite.dialect())) == "JSON"
