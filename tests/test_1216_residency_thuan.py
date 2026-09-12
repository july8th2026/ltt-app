"""Residency 3090 (D01 B) — bảng `gpu_residency` (5.1) + máy trạng thái THUẦN (5.2).

Hai phần trong một tệp, đúng như plan Pha 5 xếp: phần **mô hình** chốt ba nghĩa vụ
của một bảng mới ở nền tảng (xếp loại lưu trữ · dọn hay lý do không cần · UNIQUE
vào drill khôi phục) cộng migration lên/xuống sạch; phần **thuần** chốt máy trạng
thái — không CSDL, không HTTP, không đồng hồ, nên nó kiểm được **không cần GPU**.
"""
from __future__ import annotations

import pathlib

import pytest

REV = "c7a3f1e5b904"
GOC = pathlib.Path(__file__).resolve().parents[1]
COT = {"nhom", "trang_thai", "tu_luc", "cua_so_bat_dau", "lan_nap_loi", "phien_ban"}


# ══════════════════════════════════════════════════════════════════════════════
# Phần A — bảng `gpu_residency` (Task 5.1)
# ══════════════════════════════════════════════════════════════════════════════

def test_migration_noi_dung_chuoi_va_mot_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config(str(GOC / "alembic.ini")))
    assert len(scripts.get_heads()) == 1, scripts.get_heads()
    rev = scripts.get_revision(REV)
    assert rev.down_revision == "b4d7f2c19e30"


@pytest.mark.timeout(240)
def test_len_roi_xuong_mot_buoc_sach_va_khop_mo_hinh(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    from platform_core.models import GpuResidency

    url = "sqlite:///" + (tmp_path / "mig.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.chdir(GOC)
    cfg = Config("alembic.ini")
    command.upgrade(cfg, REV)
    insp = inspect(create_engine(url))

    # Mô hình và migration phải nói CÙNG một tập cột — lệch là `create_all`
    # (test) và `alembic upgrade` (production) dựng hai lược đồ khác nhau.
    cot = {c["name"] for c in insp.get_columns("gpu_residency")}
    assert cot == COT
    assert {c.name for c in GpuResidency.__table__.columns} == cot
    uq = {u["name"] for u in insp.get_unique_constraints("gpu_residency")}
    assert "uq_gpu_residency_nhom" in uq

    command.downgrade(cfg, "-1")
    insp = inspect(create_engine(url))
    assert "gpu_residency" not in insp.get_table_names()


def test_governance_xep_loai_gpu_residency():
    """Không phải dữ liệu của khách (như `gpu_leases`): nó nói model nào đang cư
    trú trên một nhóm GPU — không có `user_id`, không có nội dung nào của khách.

    ⚠️ Lệch với chữ của plan (*"Store OPERATIONAL, dọn: không cần"*) và lệch có
    lý do **cơ học**: `test_211::test_operational_stores_all_declare_who_removes_them`
    đòi mọi Store OPERATIONAL phải khai một hàm dọn THẬT. Bảng này có đúng một
    dòng mỗi nhóm, ghi đè tại chỗ ⇒ không có gì để dọn, nên lời khai
    OPERATIONAL sẽ là một lời khai sai.
    """
    from platform_core.public_api import governance

    assert governance.unclassified(["gpu_residency"]) == []
    assert "gpu_residency" in governance.NOT_CUSTOMER_DATA
    assert governance.store_for("gpu_residency") is None


def test_drill_khoi_phuc_biet_uq_moi():
    """Lấy tên UNIQUE **từ chính mô hình**, không gõ lại chuỗi: đổi tên ràng buộc
    mà quên drill thì phép kiểm này đỏ, chứ không xanh vì đang so hai hằng số
    nhau. Và `assert ten` chặn kiểu xanh rỗng khi tập hợp co về rỗng.
    """
    from platform_core.models import GpuResidency

    van = (GOC / "tools" / "restore_drill_schema.py").read_text(encoding="utf-8")
    ten = {c.name for c in GpuResidency.__table__.constraints
           if (getattr(c, "name", "") or "").startswith("uq_")}
    assert ten, "bang gpu_residency khong con rang buoc UNIQUE nao"
    assert all(f'"{t}"' in van for t in ten), ten
