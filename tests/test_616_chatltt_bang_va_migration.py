"""
test_616 — Phase 07: bảng `chatltt_*` + migration Alembic lên/xuống sạch, một head.

⚠️ CẬP NHẬT 2026-09-05 (H44 P03), CÓ CHỦ ĐÍCH — không phải nới lỏng.

Phép kiểm này ghim "đúng BA bảng `chatltt_*`" và "head là `7d2c1e9f4a03`". H44
thêm ba bảng điều phối tool (`run`/`step`/`approval`) và một revision mới, nên
hai mệnh đề đó **hết đúng**. Chúng đã làm đúng việc của mình: bắt tôi phải quay
lại đây và nói ra thay đổi, thay vì để nó trôi qua.

⛔ Cách sai là đổi `==` thành `<=` cho xong. Làm vậy là gỡ chính thứ vừa bắt
   được thay đổi — lần sau ai thêm một bảng `chatltt_*` bừa sẽ không ai biết.
   Nên danh sách vẫn **chốt cứng**, chỉ là chốt sáu tên thay vì ba, và migration
   xuống một bước vẫn phải xoá **đúng** phần H44 chứ không phải mọi thứ.
"""
from __future__ import annotations

import pytest


#: Ba bảng V1 (H43) + ba bảng điều phối tool (H44). CHỐT CỨNG — thêm bảng
#: `chatltt_*` mà không sửa dòng này thì phép kiểm đỏ, và đó là chủ ý.
BANG_V1 = {"chatltt_conversation", "chatltt_message", "chatltt_execution"}
BANG_V3 = {"chatltt_run", "chatltt_step", "chatltt_approval"}


def test_ba_bang_mang_dung_tien_to_va_registry_nap_duoc():
    from platform_core.db import Base
    from platform_core.registry import load_app_tables

    da_nap = load_app_tables()
    assert "chatltt" in da_nap
    ten = {t for t in Base.metadata.tables if t.startswith("chatltt_")}
    assert ten == BANG_V1 | BANG_V3


def test_alembic_mot_head_va_migration_chatltt_noi_dung_chuoi():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = scripts.get_heads()
    assert len(heads) == 1, heads
    rev = scripts.get_revision(heads[0])
    assert "chatltt" in (rev.doc or "").lower()
    # Head nay la migration H44; no phai noi TIEP migration H43, khong thay the.
    assert rev.revision == "4b8e21c6d907"
    assert rev.down_revision == "7d2c1e9f4a03"


@pytest.mark.timeout(240)
def test_upgrade_head_roi_downgrade_mot_buoc_sach(tmp_path, monkeypatch):
    """Lên head tạo đủ sáu bảng; xuống một bước xoá ĐÚNG phần H44, giữ nguyên V1.

    ⭐ Mệnh đề cuối là điều kiện của đường lùi (`02_ADR_ORCHESTRATION.md` §7):
       hạ migration H44 phải làm mất `run`/`step`/`approval` mà **hội thoại cũ
       không đổi một byte**. Nếu nó cũng xoá `chatltt_message` thì "lùi được"
       chỉ là một câu trong tài liệu.
    """
    from sqlalchemy import create_engine, inspect

    url = "sqlite:///" + (tmp_path / "mig.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    insp = inspect(create_engine(url))
    bang = set(insp.get_table_names())
    assert (BANG_V1 | BANG_V3) <= bang
    idx = {i["name"] for i in insp.get_indexes("chatltt_message")}
    assert {"ix_chatltt_msg_conv_parent", "ix_chatltt_msg_conv_created"} <= idx
    # Hai rang buoc DUY NHAT la cong chong duyet hai lan (02_HOP_DONG.md §2).
    idx_ap = {i["name"] for i in insp.get_indexes("chatltt_approval")}
    assert {"ux_chatltt_approval_step", "ux_chatltt_approval_idem"} <= idx_ap
    assert all(i["unique"] for i in insp.get_indexes("chatltt_approval")
               if i["name"] in ("ux_chatltt_approval_step", "ux_chatltt_approval_idem"))
    # Hai cot noi len run/step phai NULLABLE — moi hang V1 van hop le, khong backfill.
    cot = {c["name"]: c for c in insp.get_columns("chatltt_execution")}
    assert cot["run_id"]["nullable"] and cot["step_id"]["nullable"]

    # Xuong MOT buoc: mat dung phan H44, giu nguyen V1.
    command.downgrade(cfg, "-1")
    insp = inspect(create_engine(url))
    bang2 = set(insp.get_table_names())
    assert (bang - bang2) == BANG_V3, "xuong mot buoc phai xoa DUNG ba bang H44"
    assert BANG_V1 <= bang2, "hoi thoai cu KHONG duoc mat khi lui H44"
    cot2 = {c["name"] for c in insp.get_columns("chatltt_execution")}
    assert "run_id" not in cot2 and "step_id" not in cot2

    # Xuong tiep mot buoc nua: het sach chatltt_*  (menh de goc cua H43).
    command.downgrade(cfg, "-1")
    insp = inspect(create_engine(url))
    assert not {t for t in set(insp.get_table_names()) if t.startswith("chatltt_")}
