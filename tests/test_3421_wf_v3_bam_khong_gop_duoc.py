"""P9 task 3 (🔴): đường thi hành BỊ BĂM không còn khiến node hiện `PENDING`
giả trên `GET /agent/api/v3/runs/{id}`.

Nợ đã khai (`docs/superpowers/plans/2026-09-24-wf-v2-MASTER.md` §4 Phase 4,
"Còn hở"): `foreach` lồng sâu ⇒ `danh_thuc.duong_thi_hanh` băm khoá khi vượt
64 ký tự (`#<sha256>`, không còn `/`) ⇒ `_gop_than_foreach` (`runs_v3.py`) im
lặng bỏ qua hàng đó ⇒ node thân hiện `PENDING` trên Canvas dù đang chạy/đã
hỏng thật.

## Vì sao phép này KHÔNG kiểm "gộp đúng vào đúng node"

Hash một chiều: một khi khoá đã băm, tầng quan sát (đây, `apps/agent/routes/
runs_v3.py`, thuộc lượt p9-quan-sat) không còn cách nào suy ngược nó thuộc
`(node_id, vong)` nào — brute-force mọi tổ hợp tới `max_items` (spec cho tới
1000 phần tử, lồng nhiều tầng) không có trần chi phí, và việc đó cũng không
được sửa ở tầng ĐỘNG CƠ (`dong_co.py`/`foreach.py`/`vong_lap.py`) hay THÊM CỘT
vào `platform_core/models.py` — cả hai ngoài ranh giới của lượt này (xem báo
cáo task 3). Phép này canh đúng thứ SỬA ĐƯỢC trong ranh giới: **không còn nói
dối `PENDING`** — đổi sang một trạng thái tường minh `KHONG_XAC_DINH`.
"""
from __future__ import annotations

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _graph_foreach_don(nid_than: str) -> dict:
    """Một `foreach` bọc đúng MỘT node thân `nid_than`, khép bằng `foreach_end`."""
    return {
        "nodes": [
            {"id": "f1", "type": "core.foreach", "params": {"max_items": 5}},
            {"id": nid_than, "type": "tool",
             "data": {"tool": "text.chat", "params": {}}},
            {"id": "fend", "type": "core.foreach_end",
             "params": {"foreach": "f1"}},
        ],
        "thu_tu": ["f1", nid_than, "fend"],
        "edges": [{"source_node": "f1", "target_node": nid_than},
                 {"source_node": nid_than, "target_node": "fend"}],
    }


def _phien_ban(sess, *, workflow_id: str, graph: dict):
    """Một `WorkflowVersion` GIẢ đủ để `_nodes_json` đọc `graph` thật —
    `_nodes_json` mở `db.get(WorkflowVersion, run.version_id)`, không nhận
    `graph` trực tiếp."""
    from platform_core.models import WorkflowVersion
    ver = WorkflowVersion(workflow_id=workflow_id, seq=1, graph=graph,
                          graph_hash="x" * 64)
    sess.add(ver); sess.flush()
    return ver


def test_khoa_bam_khong_con_hien_PENDING_gia(db):  # noqa: F811
    from platform_core.models import WorkflowRun
    from platform_core.workflow import danh_thuc, thi_hanh
    from apps.agent.routes.runs_v3 import (TRANG_THAI_KHONG_XAC_DINH,
                                           _gop_than_foreach, _nodes_json)

    # `vong` đủ dài để `duong_thi_hanh` PHẢI băm (>64 ký tự) — đối chứng ngay
    # dưới đây (`test_doi_chung_vong_ngan_khong_bam`) chứng minh phép đo này
    # thật sự phụ thuộc việc CÓ băm hay không, không phải luôn luôn đỏ/xanh.
    vong_dai = [("vong_lap_ten_rat_dai_de_vuot_qua_tran", 3)]
    nid = "node_than_id_cung_kha_dai_de_chac_chan_vuot_64"
    khoa = danh_thuc.duong_thi_hanh(nid, vong=vong_dai)
    assert khoa.startswith("#") and "/" not in khoa, (
       "tien de cua phep kiem: khoa PHAI bi bam, neu khong phep nay khong "
       "do dung thu no noi no do")

    do_thi = _graph_foreach_don(nid)
    ver = _phien_ban(db, workflow_id="w1", graph=do_thi)
    run = WorkflowRun(owner_id="u1", workflow_id="w1", version_id=ver.id)
    db.add(run); db.flush()
    thi_hanh.ghi_chuyen(db, run.id, nid, execution_status="RUNNING",
                        description="dang chay", vong=vong_dai)
    db.flush()

    gop, khong_xac_dinh = _gop_than_foreach(db, run, do_thi)
    assert nid in khong_xac_dinh, (
       "node than voi khoa bam phai roi vao tap KHONG XAC DINH")
    assert nid not in gop  # khong the gop no vao trang thai gi ca — that

    nodes = _nodes_json(db, run)
    theo_id = {n["node_id"]: n for n in nodes}
    assert theo_id[nid]["status"] == TRANG_THAI_KHONG_XAC_DINH
    assert theo_id[nid]["status"] != "PENDING", (
       "day chinh la loi da khai: node dang RUNNING nhung hien PENDING gia")
    assert theo_id[nid]["error"]  # co giai thich, khong phai chuoi rong


def test_doi_chung_vong_ngan_khong_bam_van_gop_dung(db):  # noqa: F811
    """Đối chứng: `vong` NGẮN (không băm) vẫn phải gộp CHÍNH XÁC như trước —
    phép sửa không được làm hỏng đường không-băm."""
    from platform_core.models import WorkflowRun
    from platform_core.workflow import danh_thuc, thi_hanh
    from apps.agent.routes.runs_v3 import _gop_than_foreach, _nodes_json

    nid = "x"
    vong_ngan = [("f1", 0)]
    khoa = danh_thuc.duong_thi_hanh(nid, vong=vong_ngan)
    assert not khoa.startswith("#") and "/" in khoa

    do_thi = _graph_foreach_don(nid)
    ver = _phien_ban(db, workflow_id="w1", graph=do_thi)
    run = WorkflowRun(owner_id="u1", workflow_id="w1", version_id=ver.id)
    db.add(run); db.flush()
    thi_hanh.ghi_chuyen(db, run.id, nid, execution_status="SUCCEEDED",
                        description="xong", vong=vong_ngan)
    db.flush()

    gop, khong_xac_dinh = _gop_than_foreach(db, run, do_thi)
    assert khong_xac_dinh == frozenset()
    assert gop[nid]["status"] == "SUCCEEDED"

    nodes = _nodes_json(db, run)
    theo_id = {n["node_id"]: n for n in nodes}
    assert theo_id[nid]["status"] == "SUCCEEDED"
