"""Node `ai.agent` trên **run con** (spec §12.3) — plan wf-v2 P8 Task 2.

## Nguồn (⛔ không tự suy)

- **Activepieces** `packages/core/shared/src/lib/ee/agent/agent.ts`:

      maxSteps: z.number().int().positive().max(MAX_AGENT_STEP_BUDGET)
                 .default(DEFAULT_AGENT_MAX_STEPS),
      tools: z.array(AgentTool).max(MAX_AGENT_TOOLS).default([]),

  Trần **nằm trong lược đồ**, không trong một `if` lúc chạy — nên một cấu hình
  vượt trần không bao giờ được LƯU. Ta làm đúng thế: `maximum`/`maxItems` của
  `NodeDefinition.tham_so` bị cưỡng chế ở **cổng publish**
  (`bien_dich._kiem_tham_so_loi`), không phải lúc agent đang tiêu tiền.
- **LangGraph** `libs/langgraph/langgraph/pregel/main.py` — hết số bước thì
  `raise GraphRecursionError`, chứ không im lặng dừng. Ở đây: FAILED có mã
  `vuot_so_buoc`, không phải "trả về kết quả dở".

## 🔴 Bất biến tiền

`run_con.py`: *"MỘT khoản giữ cho cả cây"*. Agent mở **nhiều** run con; không
run con nào giữ chỗ, và chi phí thật của chúng cộng lên cha qua
`tong_chi_phi_con`. Hai phép dưới đây có **đối chứng** (một run không agent).
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import json

import pytest

from platform_core.workflow.cong_cu import CongCu
# ⚠️ Import ĐỂ ĐĂNG KÝ: `nut_loi/__init__.py` (làn p5c sở hữu) chưa import
#    `ai_agent`, nên node chỉ tồn tại khi có người nạp mô-đun. Xem báo cáo
#    Task 2, mục "chưa làm được".
from platform_core.workflow.nut_loi import ai_agent  # noqa: F401
from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _cc(ten, gia, returns):
    return CongCu(ten=ten, app_slug="ltt_llm", job_type=ten + ".job",
                  type_version=1, params_schema={}, side_effect="external",
                  idempotency_fields=("x",), resource={"class": "api"},
                  tinh_gia=lambda p, g=gia: g, returns=dict(returns))


CC = {"text.chat": _cc("text.chat", 3, {"content": "text"}),
      "image.generate": _cc("image.generate", 5, {"image_keys": "image[]"})}


def _agent(nid="ag", **params):
    p = {"muc_tieu": "ve mot con meo",
         "cong_cu_cho_phep": ["app.image.generate"],
         "so_buoc_toi_da": 3, "ngan_sach_credit": 50}
    p.update(params)
    return {"id": nid, "type": "ai.agent", "position": {"x": 0, "y": 0},
            "params": p}


@pytest.fixture()
def xuong(db, monkeypatch):
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


def _vong(db, run, lan=3):
    """Quay động cơ CHA và mọi CON vài lượt, kết bằng một lượt CHA.

    ⭐ Một bước agent cần **ba** lượt để lộ ra: cha mở run con → con nộp job →
       (job xong ở ngoài) → con chốt → cha đi bước kế. Trong production
       `danh_thuc`/`tao_run.danh_thuc_dong_co` nối chúng lại; ở đây phải quay
       tay, và quay thiếu thì phép kiểm đo **số lượt quay** chứ không đo agent.
    """
    from platform_core.workflow import dong_co
    for _ in range(lan):
        dong_co.xu_ly_run(db, run.id, cong_cu=CC)
        for con in _con_cua(db, run):
            dong_co.xu_ly_run(db, con.id, cong_cu=CC)
    return dong_co.xu_ly_run(db, run.id, cong_cu=CC)


def _con_cua(db, run):
    from platform_core.models import WorkflowRun
    return db.query(WorkflowRun).filter_by(parent_run_id=run.id).all()


def _tt(db, run, nid):
    from platform_core.workflow import may_trang_thai as mtt
    return mtt.trang_thai_node(db, run.id, nid)


def _tra_loi_buoc(db, run, noi_dung):
    """Hoàn tất job của run con ĐANG chạy bằng `noi_dung`. Trả số job đã đóng."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import may_trang_thai as mtt, thi_hanh
    dem = 0
    for con in _con_cua(db, run):
        if con.status in mtt.RUN_KET_THUC:
            continue
        anh = thi_hanh.anh_chup_hien_tai(db, con.id, ai_agent.NUT_BUOC)
        if anh is None or not anh.job_id:
            continue
        job = db.get(Job, anh.job_id)
        if job is None or job.status != "queued":
            continue
        jobs.complete(db, job, dict(noi_dung))
        dem += 1
    return dem


def _quyet(**kw):
    return {"content": json.dumps(kw, ensure_ascii=False)}


# ── 1. Mỗi lần gọi công cụ = MỘT run con ────────────────────────────────────

def test_moi_buoc_cua_agent_la_mot_run_con_mot_nut(db, xuong):
    w = xuong.publish([_agent()])
    run = xuong.chay(w)
    _vong(db, run)
    assert _tt(db, run, "ag") == "WAITING"
    con = _con_cua(db, run)
    assert len(con) == 1 and con[0].do_sau == 1      # buoc NGHI dau tien

    _tra_loi_buoc(db, run, _quyet(cong_cu="app.image.generate",
                                  params={"prompt": "meo"}))
    _vong(db, run)
    assert len(_con_cua(db, run)) == 2               # + run con GOI CONG CU
    assert _tt(db, run, "ag") == "WAITING"


def test_agent_ket_thuc_SUCCEEDED_voi_ket_qua_cua_model(db, xuong):
    w = xuong.publish([_agent(so_buoc_toi_da=1)])
    run = xuong.chay(w)
    _vong(db, run)
    _tra_loi_buoc(db, run, _quyet(xong=True, ket_qua={"loi": "xong roi"}))
    assert _vong(db, run) == "SUCCEEDED"
    from platform_core.workflow import thi_hanh
    ra = thi_hanh.anh_chup_hien_tai(db, run.id, "ag").output_ref
    assert ra["ket_qua"] == {"loi": "xong roi"}


# ── 2. 🔴 MỘT khoản giữ cho cả cây ──────────────────────────────────────────

def test_banh_coc_MOT_khoan_giu_du_agent_mo_NHIEU_run_con(db, xuong):
    w = xuong.publish([_agent()])
    run = xuong.chay(w)
    _vong(db, run)
    _tra_loi_buoc(db, run, _quyet(cong_cu="app.image.generate",
                                  params={"prompt": "meo"}))
    _vong(db, run)
    _tra_loi_buoc(db, run, {"image_keys": ["k1"]})
    _vong(db, run)
    con = _con_cua(db, run)
    assert len(con) >= 2
    # Một cây = MỘT khoản giữ, dù có bao nhiêu run con. `hold_id` rỗng nghĩa
    # là run ấy KHÔNG giữ gì (`tien.giu_cho_run`: *"hold_id nghĩa là có một
    # khoản đang bị giam"*).
    assert run.hold_id
    assert [c.hold_id for c in con] == ["" for _ in con]
    assert all(int(c.estimated_max or 0) == 0 for c in con)


def test_chi_phi_that_cua_moi_run_con_agent_cong_len_CHA(db, xuong):
    w = xuong.publish([_agent()])
    run = xuong.chay(w)
    _vong(db, run)
    _tra_loi_buoc(db, run, _quyet(cong_cu="app.image.generate",
                                  params={"prompt": "meo"}))
    _vong(db, run)
    _tra_loi_buoc(db, run, {"image_keys": ["k1"]})       # cong cu: 5
    _vong(db, run)
    _tra_loi_buoc(db, run, _quyet(xong=True, ket_qua={"ok": 1}))  # nghi: 3
    assert _vong(db, run) == "SUCCEEDED"
    # 3 (nghi) + 5 (cong cu) + 3 (nghi) = 11 — KHONG phai 0.
    assert run.actual_cost == 11


# ── 3. Hành động bị chặn, mỗi cái một mã ────────────────────────────────────

def test_cong_cu_NGOAI_danh_sach_cho_phep_bi_tu_choi(db, xuong):
    w = xuong.publish([_agent()])
    run = xuong.chay(w)
    _vong(db, run)
    _tra_loi_buoc(db, run, _quyet(cong_cu="app.text.chat", params={}))
    assert _vong(db, run) == "FAILED"
    from platform_core.workflow import thi_hanh
    assert "cong_cu_khong_duoc_phep" in (
        thi_hanh.anh_chup_hien_tai(db, run.id, "ag").error or "")
    # ⭐ ĐỐI CHỨNG: không có run con nào được mở cho công cụ bị cấm.
    assert len(_con_cua(db, run)) == 1


def test_vuot_so_buoc_toi_da_thi_FAILED_khong_lang_le_dung(db, xuong):
    w = xuong.publish([_agent(so_buoc_toi_da=1)])
    run = xuong.chay(w)
    _vong(db, run)
    _tra_loi_buoc(db, run, _quyet(cong_cu="app.image.generate", params={}))
    _vong(db, run)
    _tra_loi_buoc(db, run, {"image_keys": ["k1"]})
    _vong(db, run)
    _tra_loi_buoc(db, run, _quyet(cong_cu="app.image.generate", params={}))
    assert _vong(db, run) == "FAILED"
    from platform_core.workflow import thi_hanh
    assert "vuot_so_buoc" in (
        thi_hanh.anh_chup_hien_tai(db, run.id, "ag").error or "")


def test_vuot_ngan_sach_thi_KHONG_mo_them_run_con(db, xuong):
    w = xuong.publish([_agent(ngan_sach_credit=4)])   # < 3 (nghi) + 5 (cong cu)
    run = xuong.chay(w)
    _vong(db, run)
    truoc = len(_con_cua(db, run))
    _tra_loi_buoc(db, run, _quyet(cong_cu="app.image.generate", params={}))
    assert _vong(db, run) == "FAILED"
    from platform_core.workflow import thi_hanh
    assert "vuot_ngan_sach" in (
        thi_hanh.anh_chup_hien_tai(db, run.id, "ag").error or "")
    assert len(_con_cua(db, run)) == truoc


def test_dau_ra_khong_khop_luoc_do_thi_FAILED(db, xuong):
    w = xuong.publish([_agent(luoc_do_dau_ra={
        "type": "object", "properties": {"n": {"type": "integer"}},
        "required": ["n"]})])
    run = xuong.chay(w)
    _vong(db, run)
    _tra_loi_buoc(db, run, _quyet(xong=True, ket_qua={"n": "khong phai so"}))
    assert _vong(db, run) == "FAILED"
    from platform_core.workflow import thi_hanh
    assert "dau_ra_sai_luoc_do" in (
        thi_hanh.anh_chup_hien_tai(db, run.id, "ag").error or "")


def test_model_tra_ve_khong_doc_duoc_thi_FAILED_co_ma(db, xuong):
    w = xuong.publish([_agent()])
    run = xuong.chay(w)
    _vong(db, run)
    _tra_loi_buoc(db, run, {"content": "toi khong biet"})
    assert _vong(db, run) == "FAILED"
    from platform_core.workflow import thi_hanh
    assert "quyet_dinh_khong_doc_duoc" in (
        thi_hanh.anh_chup_hien_tai(db, run.id, "ag").error or "")


# ── 4. Trần trong LƯỢC ĐỒ, cưỡng chế ở cổng publish (nguồn Activepieces) ────

@pytest.mark.parametrize("params,ma", [
    ({"so_buoc_toi_da": 9}, "tham_so_vuot_tran"),
    ({"cong_cu_cho_phep": [f"app.t{i}" for i in range(11)]},
     "tham_so_vuot_tran"),
    ({"ngan_sach_credit": 0}, "tham_so_vuot_tran"),
])
def test_cong_publish_tu_choi_cau_hinh_vuot_tran(db, xuong, params, ma):
    from platform_core.workflow import bien_dich
    with pytest.raises(bien_dich.LoiBienDich) as e:
        xuong.publish([_agent(**params)])
    assert e.value.ma == ma


def test_thieu_ngan_sach_credit_bi_tu_choi_luc_publish(db, xuong):
    from platform_core.workflow import bien_dich
    p = {"muc_tieu": "x", "cong_cu_cho_phep": [], "so_buoc_toi_da": 2}
    with pytest.raises(bien_dich.LoiBienDich) as e:
        xuong.publish([{"id": "ag", "type": "ai.agent",
                        "position": {"x": 0, "y": 0}, "params": p}])
    assert e.value.ma == "thieu_tham_so"


def test_tran_bao_gia_cua_node_BANG_ngan_sach_credit(db, xuong):
    from platform_core.models import WorkflowVersion
    w = xuong.publish([_agent(ngan_sach_credit=42)])
    ver = db.get(WorkflowVersion, w.published_version_id)
    assert ver.graph["bang_gia"]["ag"] == 42
    assert int(ver.estimated_max) == 42


# ── 5. Nhật ký quyết định (spec §12.3) ──────────────────────────────────────

def test_ghi_AgentStep_vao_workflow_event(db, xuong):
    from platform_core.models import WorkflowEvent
    w = xuong.publish([_agent()])
    run = xuong.chay(w)
    _vong(db, run)
    _tra_loi_buoc(db, run, _quyet(cong_cu="app.image.generate", params={}))
    _vong(db, run)
    buoc = db.query(WorkflowEvent).filter_by(run_id=run.id,
                                             loai="AgentStep").all()
    assert buoc, "khong ghi AgentStep nao"
    assert any((e.du_lieu or {}).get("cong_cu") == "app.image.generate"
               for e in buoc)
