"""P9 task 3 (mở rộng, yêu cầu điều phối 24/09 khi mở lại `main`/phase 5+6):
`GET /agent/api/v3/runs/{id}` phải phân biệt được một node `WAITING` vì đang
chờ NGƯỜI DUYỆT (`Waitpoint.kind == "HUMAN"`) với `WAITING` vì đang chờ
webhook/event/delay/run con/barrier — "một node WAITING vì đang đợi người
duyệt mà giao diện không phân biệt được với WAITING vì lỗi là đúng hạng lỗi
task 3" (coordinator).

Trường mới: `waiting_kind`, giá trị khớp NGUYÊN `Waitpoint.kind`
(`DELAY|JOB|WEBHOOK|HUMAN|CHILD_RUN|BARRIER`) — rỗng khi node không `WAITING`.
"""
from __future__ import annotations

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401,F811


def _phien_ban(sess, *, workflow_id: str, graph: dict):
    from platform_core.models import WorkflowVersion
    ver = WorkflowVersion(workflow_id=workflow_id, seq=1, graph=graph,
                          graph_hash="y" * 64)
    sess.add(ver); sess.flush()
    return ver


def test_node_waiting_vi_HUMAN_khac_node_waiting_vi_WEBHOOK(db):  # noqa: F811
    from platform_core.models import WorkflowRun
    from platform_core.workflow import cho_doi, may_trang_thai, thi_hanh
    from apps.agent.routes.runs_v3 import _nodes_json

    graph = {
        "nodes": [
            {"id": "duyet", "type": "core.wait_human"},
            {"id": "hook", "type": "core.wait_webhook"},
        ],
        "thu_tu": ["duyet", "hook"],
        "edges": [],
    }
    ver = _phien_ban(db, workflow_id="w1", graph=graph)
    run = WorkflowRun(owner_id="u1", workflow_id="w1", version_id=ver.id)
    db.add(run); db.flush()

    for nid, kind in (("duyet", "HUMAN"), ("hook", "WEBHOOK")):
        wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1", kind=kind)
        cho_doi.chan_node(db, run_id=run.id, node_id=nid, waitpoint_id=wp.id)
        # PENDING -> READY -> WAITING (bảng chuyển `NODE_CHUYEN`; không có
        # đường tắt PENDING -> WAITING).
        assert may_trang_thai.chuyen_node(
            db, run.id, nid, sang="READY", mo_ta="san sang") is True
        assert may_trang_thai.chuyen_node(
            db, run.id, nid, sang="WAITING", mo_ta="cho", job_id="") is True
    db.flush()

    nodes = {n["node_id"]: n for n in _nodes_json(db, run)}
    assert nodes["duyet"]["status"] == "WAITING"
    assert nodes["duyet"]["waiting_kind"] == "HUMAN"
    assert nodes["hook"]["status"] == "WAITING"
    assert nodes["hook"]["waiting_kind"] == "WEBHOOK"
    # Hai node CHỜ VÌ HAI LÝ DO KHÁC NHAU -- day chinh la thu giao dien phai
    # phan biet duoc, khong duoc gop chung ve mot nhan "Dang cho tin hieu".
    assert nodes["duyet"]["waiting_kind"] != nodes["hook"]["waiting_kind"]


def test_node_khong_waiting_thi_waiting_kind_rong(db):  # noqa: F811
    from platform_core.models import WorkflowRun
    from apps.agent.routes.runs_v3 import _nodes_json

    graph = {"nodes": [{"id": "a", "type": "tool"}], "thu_tu": ["a"],
            "edges": []}
    ver = _phien_ban(db, workflow_id="w1", graph=graph)
    run = WorkflowRun(owner_id="u1", workflow_id="w1", version_id=ver.id)
    db.add(run); db.flush()

    nodes = {n["node_id"]: n for n in _nodes_json(db, run)}
    assert nodes["a"]["status"] == "PENDING"
    assert nodes["a"]["waiting_kind"] == ""
