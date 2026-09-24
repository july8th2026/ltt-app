"""`core.call_workflow` — run con, và **MỘT khoản giữ chỗ cho cả cây**.

## 🔴 Bất biến về tiền, và vì sao nó là bất biến

`tien.py` viết thẳng ra:

    "Mỗi node của một workflow rồi sẽ sinh một job, và **đường job đã thu tiền**.
     Nếu run cũng giữ và node cũng giữ thì khách trả **hai lần** cho cùng một việc."

Run con là đúng cái bẫy ấy ở một tầng khác: nếu `tao_run` chạy nguyên cho run
con thì mỗi lần gọi subworkflow là **một khoản giữ nữa**, và một cây gọi sâu 5
tầng giam số dư của khách 5 lần cho một lượt chạy.

⇒ Luật: **run con KHÔNG giữ chỗ.** Trần của nó đã nằm trong trần của cha (§7.2
  *"subworkflow: `estimated_max` của version con"*), và chi phí thật của nó
  **cộng lên** `actual_cost` của cha khi nó kết thúc. Một cây = một khoản giữ,
  một lần quyết toán.

## Phép này KHÔNG phủ cái gì

Không phủ `wait = false` (bắn rồi quên) — spec §5.10 mặc định `wait = true` và
bản này chỉ làm `true`. Không phủ huỷ run cha khi con đang chạy. Không chạy trên
PostgreSQL thật (Task 8).
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import pytest

from platform_core.workflow.cong_cu import CongCu
from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 3,
                          returns={"text": "text"})}


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _canh(a: str, b: str) -> dict:
    return {"id": f"{a}-{b}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": "DATA",
            "condition": ""}


@pytest.fixture()
def xuong(db, monkeypatch):
    """Xưởng: `publish(nodes, edges) -> Workflow` và `chay(workflow) -> run`."""
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    credit.nap(db, "u1", 10000, note="test")
    dem = {"n": 0}

    class _X:
        def publish(self, nodes, edges=()):
            dem["n"] += 1
            w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"t{dem['n']}")
            dinh_nghia.luu_draft(db, w.id, revision=0, document={
                "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                         "edges": list(edges)}]})
            v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1",
                                          cong_cu=CC)
            w.published_version_id = v.id
            db.flush()
            return w

        def chay(self, w):
            dem["n"] += 1
            run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                                     trigger_kind="manual",
                                     idempotency_key=f"k{dem['n']}")
            return run
    return _X()


def _vong(db, run, lan=6):
    """Quay động cơ vài lượt — run con xong mới đánh thức được run cha."""
    from platform_core.workflow import dong_co
    tt = ""
    for _ in range(lan):
        tt = dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        for con in _con_cua(db, run):
            dong_co.xu_ly_run(db, con.id, cong_cu=CC)
    return tt


def _con_cua(db, run):
    from platform_core.models import WorkflowRun
    return db.query(WorkflowRun).filter_by(parent_run_id=run.id).all()


def _tt(db, run, nid):
    from platform_core.workflow import may_trang_thai as mtt
    return mtt.trang_thai_node(db, run.id, nid)


# ── ĐỐI CHỨNG: run KHÔNG có cha vẫn giữ chỗ y như cũ ────────────────────────

def test_doi_chung_run_goc_van_giu_cho_mot_lan(db, xuong):
    from platform_core import credit
    # Một node app (giá 3) — đồ thị toàn node lõi có trần 0, và `giu_cho_run`
    # cố ý KHÔNG đặt `hold_id` cho một khoản không tồn tại (`tien.py`).
    w = xuong.publish([{"id": "a", "type": "tool",
                        "position": {"x": 0, "y": 0},
                        "data": {"tool": "text.chat", "params": {}}}])
    run = xuong.chay(w)
    assert run.hold_id == run.id
    assert credit.so_da_giu(db, run.id) == run.estimated_max


# ── Tiền: MỘT khoản giữ cho cả cây ──────────────────────────────────────────

def test_run_con_KHONG_giu_khoan_thu_hai(db, xuong):
    from platform_core import credit
    con = xuong.publish([{"id": "a", "type": "tool",
                          "position": {"x": 0, "y": 0},
                          "data": {"tool": "text.chat", "params": {}}}])
    cha = xuong.publish([_core("g", "call_workflow", workflow_id=con.id,
                               version_id="latest", inputs={})])
    run = xuong.chay(cha)
    _vong(db, run, lan=1)
    [rc] = _con_cua(db, run)
    assert rc.hold_id == "", "run con giu khoan thu hai"
    assert credit.so_da_giu(db, rc.id) == 0
    assert rc.parent_node_id == "g" and rc.do_sau == 1


def test_tran_cua_CHA_da_bao_gom_tran_cua_CON(db, xuong):
    """§7.2: *"subworkflow: `estimated_max` của version con"*."""
    from platform_core.models import WorkflowVersion
    con = xuong.publish([{"id": "a", "type": "tool",
                          "position": {"x": 0, "y": 0},
                          "data": {"tool": "text.chat", "params": {}}}])
    v_con = db.get(WorkflowVersion, con.published_version_id)
    assert v_con.estimated_max == 3
    cha = xuong.publish([_core("g", "call_workflow", workflow_id=con.id,
                               version_id="latest", inputs={})])
    assert db.get(WorkflowVersion,
                  cha.published_version_id).estimated_max == 3


def test_chi_phi_that_cua_CON_cong_len_CHA(db, xuong):
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import thi_hanh
    con = xuong.publish([{"id": "a", "type": "tool",
                          "position": {"x": 0, "y": 0},
                          "data": {"tool": "text.chat", "params": {}}}])
    cha = xuong.publish([_core("g", "call_workflow", workflow_id=con.id,
                               version_id="latest", inputs={}),
                         _core("sau", "transform", gia_tri='"xong"')],
                        [_canh("g", "sau")])
    run = xuong.chay(cha)
    _vong(db, run, lan=1)
    [rc] = _con_cua(db, run)
    assert _tt(db, run, "g") == "WAITING"           # wait = true
    job = db.get(Job, thi_hanh.anh_chup_hien_tai(db, rc.id, "a").job_id)
    jobs.complete(db, job, {"text": "chao"})
    assert _vong(db, run) == "SUCCEEDED"
    assert rc.actual_cost == 3
    assert run.actual_cost == 3                      # cong len, khong nhan doi
    assert _tt(db, run, "sau") == "SUCCEEDED"


def test_con_FAILED_thi_node_CHA_FAILED(db, xuong):
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import thi_hanh
    con = xuong.publish([{"id": "a", "type": "tool",
                          "position": {"x": 0, "y": 0},
                          "data": {"tool": "text.chat", "params": {}}}])
    cha = xuong.publish([_core("g", "call_workflow", workflow_id=con.id,
                               version_id="latest", inputs={})])
    run = xuong.chay(cha)
    _vong(db, run, lan=1)
    [rc] = _con_cua(db, run)
    job = db.get(Job, thi_hanh.anh_chup_hien_tai(db, rc.id, "a").job_id)
    jobs.fail(db, job, "hong", retry=False)
    assert _vong(db, run) == "FAILED"
    assert _tt(db, run, "g") == "FAILED"


def test_ket_qua_run_con_doc_duoc_tu_node_CHA(db, xuong):
    con = xuong.publish([_core("t", "transform", gia_tri='"xin chao"'),
                         _core("o", "output", ten="loi", gia_tri="nodes.t.output.gia_tri")],
                        [_canh("t", "o")])
    cha = xuong.publish([_core("g", "call_workflow", workflow_id=con.id,
                               version_id="latest", inputs={})])
    run = xuong.chay(cha)
    assert _vong(db, run) == "SUCCEEDED"
    from platform_core.workflow import thi_hanh
    ra = thi_hanh.anh_chup_hien_tai(db, run.id, "g").output_ref
    assert ra["outputs"] == {"loi": "xin chao"}


# ── GHIM version, và chặn ở PUBLISH ─────────────────────────────────────────

def test_version_id_duoc_GHIM_luc_publish_cha(db, xuong):
    """§5.10: *"ghim lúc **publish cha**: compiler thay `"latest"` bằng id
    version publish hiện tại, ghi vào graph cha"*."""
    from platform_core.models import WorkflowVersion
    con = xuong.publish([_core("t", "transform", gia_tri="1")])
    cha = xuong.publish([_core("g", "call_workflow", workflow_id=con.id,
                               version_id="latest", inputs={})])
    g = db.get(WorkflowVersion, cha.published_version_id).graph
    assert g["nodes"][0]["params"]["version_id"] == con.published_version_id


def test_client_khong_tu_khai_duoc_gia_con(db, xuong):
    """⛔ *"một trường trong body của người gọi không thể là nguồn của một con
    số nền tảng dùng để giữ tiền của chính người gọi ấy"* (`bao_gia.py`)."""
    from platform_core.workflow.bien_dich import LoiBienDich
    con = xuong.publish([_core("t", "transform", gia_tri="1")])
    with pytest.raises(LoiBienDich) as e:
        xuong.publish([_core("g", "call_workflow", workflow_id=con.id,
                             version_id="latest", inputs={}, gia_con=0)])
    assert e.value.ma == "tham_so_la"


def test_goi_chinh_minh_bi_tu_choi(db, xuong):
    from platform_core.workflow import dinh_nghia
    from platform_core.workflow.bien_dich import LoiBienDich
    w = dinh_nghia.tao_workflow(db, owner_id="u1", name="tu goi")
    dinh_nghia.luu_draft(db, w.id, revision=0, document={
        "version": 3, "pages": [{"id": "p1", "nodes": [
            _core("g", "call_workflow", workflow_id=w.id,
                  version_id="latest", inputs={})], "edges": []}]})
    with pytest.raises(LoiBienDich) as e:
        dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    assert e.value.ma == "goi_de_quy"


def test_workflow_con_chua_publish_bi_tu_choi(db, xuong):
    from platform_core.workflow import dinh_nghia
    from platform_core.workflow.bien_dich import LoiBienDich
    chua = dinh_nghia.tao_workflow(db, owner_id="u1", name="chua publish")
    with pytest.raises(LoiBienDich) as e:
        xuong.publish([_core("g", "call_workflow", workflow_id=chua.id,
                             version_id="latest", inputs={})])
    assert e.value.ma == "workflow_con_chua_publish"


def test_do_sau_qua_5_bi_tu_choi_luc_publish(db, xuong):
    """§10: *"độ sâu subworkflow 5"*. Chặn ở publish — độ sâu tính được TĨNH
    vì mọi `version_id` đã ghim và version là bất biến."""
    from platform_core.models import WorkflowVersion
    from platform_core.workflow.bien_dich import LoiBienDich
    from platform_core.workflow.run_con import DO_SAU_TOI_DA

    w = xuong.publish([_core("t", "transform", gia_tri="1")])
    for tang in range(1, DO_SAU_TOI_DA + 1):
        w = xuong.publish([_core("g", "call_workflow", workflow_id=w.id,
                                 version_id="latest", inputs={})])
        assert db.get(WorkflowVersion,
                      w.published_version_id).graph["do_sau_goi"] == tang
    with pytest.raises(LoiBienDich) as e:
        xuong.publish([_core("g", "call_workflow", workflow_id=w.id,
                             version_id="latest", inputs={})])
    assert e.value.ma == "qua_sau_subworkflow"


def test_banh_coc_MOT_khoan_giu_cho_CA_CAY():
    """⛔ Chỉ `tao_run.tao_run` được gọi `tien.giu_cho_run`.

    ⭐ Cắn thật: thêm `tien.giu_cho_run(db, run)` vào `run_con.tao_run_con` là
       đủ để nó đỏ (đã tiêm thử — xem báo cáo Task 7).

    Đối chứng: khẳng định số lượng > 0 trước, để một phép grep hỏng không xanh giả.
    """
    import ast
    import pathlib

    goi: dict[str, list[str]] = {}
    for f in sorted(pathlib.Path("platform_core").rglob("*.py")):
        cay = ast.parse(f.read_text(encoding="utf-8"))
        ten = [ast.unparse(c.func) for c in ast.walk(cay)
               if isinstance(c, ast.Call)]
        cho = [t for t in ten if t.endswith("giu_cho_run")]
        if cho:
            goi[f.as_posix()] = cho
    assert goi, "khong tim thay loi goi nao - phep kiem nay dang do tap rong"
    assert set(goi) == {"platform_core/workflow/tao_run.py"}, goi


def test_huy_CHA_thi_huy_luon_CON(db, xuong):
    """Spec §18.5 FLOW F: *"huỷ cha huỷ con"*.

    🔴 Đây là một lỗ **tiền thật**, không phải một chi tiết cho gọn: một run con
    sống sót sau khi cha bị huỷ vẫn nộp job, vẫn tiêu credit — và `ket_so` của
    cha đã chạy xong nên `tong_chi_phi_con` không bao giờ đọc tới phần ấy.
    """
    from platform_core.models import JOB_CANCELLED, Job
    from platform_core.workflow import dong_co, thi_hanh
    con = xuong.publish([{"id": "a", "type": "tool",
                          "position": {"x": 0, "y": 0},
                          "data": {"tool": "text.chat", "params": {}}}])
    cha = xuong.publish([_core("g", "call_workflow", workflow_id=con.id,
                               version_id="latest", inputs={})])
    run = xuong.chay(cha)
    _vong(db, run, lan=1)
    [rc] = _con_cua(db, run)
    job = db.get(Job, thi_hanh.anh_chup_hien_tai(db, rc.id, "a").job_id)
    assert job.status != JOB_CANCELLED             # doi chung: dang song

    assert dong_co.huy_run(db, run.id, "khach bam Huy") is True
    assert run.status == "CANCELLED" and rc.status == "CANCELLED"
    assert db.get(Job, job.id).status == JOB_CANCELLED


def test_huy_cha_khong_nga_khi_con_da_ket_thuc(db, xuong):
    """Đối chứng: con đã xong thì lượt huỷ cha không đụng vào nó."""
    from platform_core.workflow import dong_co
    con = xuong.publish([_core("t", "transform", gia_tri="1")])
    cha = xuong.publish([_core("g", "call_workflow", workflow_id=con.id,
                               version_id="latest", inputs={}),
                         _core("cho", "transform", gia_tri="2")],
                        [_canh("g", "cho")])
    run = xuong.chay(cha)
    _vong(db, run, lan=2)
    [rc] = _con_cua(db, run)
    assert rc.status == "SUCCEEDED"
    dong_co.huy_run(db, run.id, "khach bam Huy")
    assert rc.status == "SUCCEEDED"                # KHONG bi ghi de
