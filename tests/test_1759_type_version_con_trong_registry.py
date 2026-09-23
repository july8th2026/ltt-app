"""Spec §4.3/§18.4 — mọi `type_version` mà một version ĐÃ PUBLISH tham chiếu
vẫn phải còn trong registry.

🔴 Lỗ hổng IM LẶNG: đổi `params_schema` của một tool mà quên tăng
   `type_version`, hoặc gỡ một tool, làm mọi `workflow_version` trỏ tới nó
   ĐỔI NGHĨA mà không lỗi nào báo (`registry.py` §type_version, `G05`).

⚠️ LỆCH VỚI PLAN 02 (đọc trước khi sửa lại test này). Plan viết code mẫu giả
   định `WorkflowVersion` có cột `status` (`"PUBLISHED"`/`"ARCHIVED"`) và
   tham số `version=`. Cây này KHÔNG có cột trạng thái trên `WorkflowVersion`:
   `platform_core/models.py` khai nó là *"một bản đã xuất bản — BẤT BIẾN sau
   khi tạo"* (trường `seq`, không phải `version`); mọi hàng của bảng
   `workflow_version` LÀ một bản đã xuất bản — không có `DRAFT` ở tầng này
   (bản đang soạn nằm ở bảng `workflow_draft` riêng, sửa tại chỗ). "Lưu trữ"
   là thuộc tính của `Workflow` CHA (`archived_at`), gate thật ở
   `workflow/tao_run.py::tao_run` (`if not workflow.published_version_id or
   workflow.archived_at is not None: ...`). Test dưới đây dựng một `Workflow`
   cho mỗi version và dùng `archived_at` thay cho `status="ARCHIVED"`.
"""
from __future__ import annotations

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401  (fixture)
# ruff: noqa: F811


def _workflow(db, *, archived: bool = False):
    from datetime import datetime, timezone

    from platform_core.models import Workflow

    wf = Workflow(owner_id="u1",
                 archived_at=(datetime.now(timezone.utc).replace(tzinfo=None)
                              if archived else None))
    db.add(wf)
    db.flush()
    return wf


def _version(db, workflow_id, *, nodes, seq: int = 1):
    from platform_core.models import WorkflowVersion, WorkflowVersionNode

    graph = {"schema": "ltt.workflow/3", "nodes": nodes, "edges": [],
             "thu_tu": [n["id"] for n in nodes]}
    v = WorkflowVersion(workflow_id=workflow_id, seq=seq, graph=graph,
                        graph_hash=f"hash-{workflow_id}-{seq}",
                        created_by="u1", estimated_max=0)
    db.add(v)
    db.flush()
    for n in nodes:
        db.add(WorkflowVersionNode(version_id=v.id, node_id=n["id"],
                                   node_type=n["type"],
                                   type_version=int(n["type_version"])))
    db.flush()
    return v


def test_khong_thieu_gi_khi_registry_con_dung_type_version(db):
    from platform_core.workflow import nut
    ten = sorted(t for t in nut.tat_ca() if t.startswith("app."))[0]
    tv = nut.tat_ca()[ten].type_version
    wf = _workflow(db)
    _version(db, wf.id, nodes=[{"id": "a", "type": ten, "type_version": tv,
                                "thi_hanh": "job"}])
    assert nut.type_version_thieu(db) == []


def test_bat_duoc_version_tro_toi_type_version_khong_con(db):
    from platform_core.workflow import nut
    ten = sorted(t for t in nut.tat_ca() if t.startswith("app."))[0]
    wf = _workflow(db)
    v = _version(db, wf.id, nodes=[{"id": "a", "type": ten,
                                    "type_version": 99, "thi_hanh": "job"}])
    thieu = nut.type_version_thieu(db)
    assert thieu == [{"version_id": v.id, "node_id": "a", "node_type": ten,
                      "type_version": 99}]


def test_bat_duoc_tool_da_bi_go_khoi_registry(db):
    from platform_core.workflow import nut
    wf = _workflow(db)
    v = _version(db, wf.id, nodes=[{"id": "a", "type": "app.da.go",
                                    "type_version": 1, "thi_hanh": "job"}])
    assert nut.type_version_thieu(db) == [
        {"version_id": v.id, "node_id": "a", "node_type": "app.da.go",
         "type_version": 1}]


def test_bo_qua_version_cua_workflow_da_luu_tru(db):
    # 🔑 Thay cho `status = "ARCHIVED"` của plan (không tồn tại trên cây này):
    # đánh dấu WORKFLOW CHA đã lưu trữ (`archived_at`), giống hệt gate thật ở
    # `tao_run.tao_run`.
    #
    # Mot ban da luu tru khong con tao run moi => no khong phai mot rui ro
    # dang song; bao no la bao mot bao dong khong ai tat duoc.
    from platform_core.workflow import nut
    wf = _workflow(db, archived=True)
    _version(db, wf.id, nodes=[{"id": "a", "type": "app.da.go",
                                "type_version": 1, "thi_hanh": "job"}])
    assert nut.type_version_thieu(db) == []
