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

🔑 "ĐÃ PUBLISH" Ở CÂY NÀY = `Workflow.published_version_id`, KHÔNG phải "có mặt
   trong bảng `workflow_version`". Bản v1 của Task 9 lọc thiếu điều đó nên báo
   cả những version CŨ — mà `WorkflowVersion` bất biến, nên một cảnh báo trên
   bản cũ là cảnh báo không ai tắt được. Hai bài cuối tệp này chốt đúng ranh
   giới ấy theo cả hai chiều.
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


def _version(db, wf, *, nodes, seq: int = 1, publish: bool = True):
    """Thêm một version cho `wf`. `publish=True` ⇒ trỏ `published_version_id`
    vào nó, tức đây là bản ĐANG publish — đúng thứ `tao_run` đọc."""
    from platform_core.models import WorkflowVersion, WorkflowVersionNode

    graph = {"schema": "ltt.workflow/3", "nodes": nodes, "edges": [],
             "thu_tu": [n["id"] for n in nodes]}
    v = WorkflowVersion(workflow_id=wf.id, seq=seq, graph=graph,
                        graph_hash=f"hash-{wf.id}-{seq}",
                        created_by="u1", estimated_max=0)
    db.add(v)
    db.flush()
    for n in nodes:
        db.add(WorkflowVersionNode(version_id=v.id, node_id=n["id"],
                                   node_type=n["type"],
                                   type_version=int(n["type_version"])))
    if publish:
        wf.published_version_id = v.id
    db.flush()
    return v


def test_khong_thieu_gi_khi_registry_con_dung_type_version(db):
    from platform_core.workflow import nut
    ten = sorted(t for t in nut.tat_ca() if t.startswith("app."))[0]
    tv = nut.tat_ca()[ten].type_version
    wf = _workflow(db)
    _version(db, wf, nodes=[{"id": "a", "type": ten, "type_version": tv,
                                "thi_hanh": "job"}])
    assert nut.type_version_thieu(db) == []


def test_bat_duoc_version_tro_toi_type_version_khong_con(db):
    from platform_core.workflow import nut
    ten = sorted(t for t in nut.tat_ca() if t.startswith("app."))[0]
    wf = _workflow(db)
    v = _version(db, wf, nodes=[{"id": "a", "type": ten,
                                    "type_version": 99, "thi_hanh": "job"}])
    thieu = nut.type_version_thieu(db)
    assert thieu == [{"version_id": v.id, "node_id": "a", "node_type": ten,
                      "type_version": 99}]


def test_bat_duoc_tool_da_bi_go_khoi_registry(db):
    from platform_core.workflow import nut
    wf = _workflow(db)
    v = _version(db, wf, nodes=[{"id": "a", "type": "app.da.go",
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
    _version(db, wf, nodes=[{"id": "a", "type": "app.da.go",
                                "type_version": 1, "thi_hanh": "job"}])
    assert nut.type_version_thieu(db) == []


def test_bo_qua_VERSION_CU_khong_con_la_ban_dang_publish(db):
    """🔑 RANH GIỚI của `type_version_thieu`, và là chỗ nó từng lệch.

    `WorkflowVersion` BẤT BIẾN, nên một version cũ trỏ tới tool đã gỡ thì
    KHÔNG BAO GIỜ sửa được — báo nó là dựng đúng cái "báo động không ai tắt
    được" mà chính hàm ấy lấy làm lý do loại workflow đã lưu trữ. Cổng thật
    (`tao_run`) chỉ chạy `workflow.published_version_id`, nên chỉ bản ĐANG
    publish mới là rủi ro đang sống.
    """
    from platform_core.workflow import nut
    ten = sorted(t for t in nut.tat_ca() if t.startswith("app."))[0]
    tv = nut.tat_ca()[ten].type_version
    wf = _workflow(db)
    # seq 1: bản CŨ, trỏ tới một tool đã gỡ. seq 2: bản ĐANG publish, lành.
    _version(db, wf, seq=1, publish=False,
             nodes=[{"id": "a", "type": "app.da.go", "type_version": 1,
                     "thi_hanh": "job"}])
    _version(db, wf, seq=2, publish=True,
             nodes=[{"id": "a", "type": ten, "type_version": tv,
                     "thi_hanh": "job"}])
    assert nut.type_version_thieu(db) == []


def test_VAN_bat_duoc_khi_ban_dang_publish_la_ban_hong(db):
    """Đối chứng của bài ngay trên: lọc `published_version_id` KHÔNG được lọc
    quá tay. Cùng hình dạng hai version, chỉ đổi bản nào đang publish."""
    from platform_core.workflow import nut
    ten = sorted(t for t in nut.tat_ca() if t.startswith("app."))[0]
    tv = nut.tat_ca()[ten].type_version
    wf = _workflow(db)
    _version(db, wf, seq=1, publish=False,
             nodes=[{"id": "a", "type": ten, "type_version": tv,
                     "thi_hanh": "job"}])
    v2 = _version(db, wf, seq=2, publish=True,
                  nodes=[{"id": "a", "type": "app.da.go", "type_version": 1,
                          "thi_hanh": "job"}])
    assert nut.type_version_thieu(db) == [
        {"version_id": v2.id, "node_id": "a", "node_type": "app.da.go",
         "type_version": 1}]
