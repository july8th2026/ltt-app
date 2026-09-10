"""LTT WORKFLOW V2 · Đợt 5.3 — `M-1`: chuyển bản nháp Canvas v2 sang lược đồ V2.

🔴 **Hạng mục này từng được ghi là "gần như KHÔNG TỒN TẠI"** (`27_29 §27.1`), dựa
   trên một phép đo **đúng**:

       0 job `agent.advance` / 28 ngay log production   (`01 §A.1`)

   Và kết luận rút ra là *"không có khách đứng trên đường cũ ⇒ thay thẳng, gỡ
   bản cũ"*.

⚠️ Đo `D2` ngày 08/09/2026 trên chính CSDL production:

       agent_workflows 10 · agent_runs 4 · agent_workflow_snapshots 83
       doi chung: users 27 · jobs 1770 · credit_entries 5500

⇒ Con số `0 run` **đúng**, nhưng nó nói **KHÔNG AI CHẠY** — không nói **KHÔNG AI
  ĐÃ DỰNG**. Xoá lớp ấy là xoá việc của 10 người.

## ⭐ Nhưng hình dạng THẬT của 10 bản ghi ấy mới là thứ quyết cách làm

Đo tiếp (chỉ đọc):

    10/10 mang ten mac dinh "Workflow moi"   -> khong ai doi ten
    toi da 3 node, toi da 2 canh             -> khong co do thi nao that su
    4/10 co `document` RONG                  -> khong co Canvas v2 de chuyen
    6/10 co `document` 5 khoa: active_page_id · budget_max_credit · goal
                                · pages · version
    3 `validated` · 7 `draft` · tat ca `plan_version = 1`

⇒ Nên `M-1` **có thật** nhưng **nhỏ**, và nó phải xử đúng ba lớp: bản có
  `document`, bản chỉ có `nodes/edges` cũ, và bản rỗng hoàn toàn.

⛔ Và nó phải **LUỸ ĐẲNG**: một script di trú chạy hai lần mà nhân đôi dữ liệu
   là cách một lần chạy lại vì hoảng biến thành một sự cố thật.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'm1.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


def _cu(db, *, ten="Workflow mới", document=None, nodes=None, edges=None,
        status="draft", user_id="u1"):
    """Một `AgentWorkflow` đúng hình dạng production đã đo."""
    from platform_core.models import AgentWorkflow

    w = AgentWorkflow(user_id=user_id, name=ten, document=document or {},
                      nodes=nodes or [], edges=edges or [], status=status)
    db.add(w)
    db.flush()
    return w


def _doc_v2(so_node=3, so_canh=1):
    """Canvas v2 đúng 5 khoá đo được trên production."""
    return {
        "version": 2,
        "goal": "thu",
        "budget_max_credit": 120,
        "active_page_id": "p1",
        "pages": [{
            "id": "p1", "name": "Trang 1",
            "nodes": [{"id": f"n{i}", "type": "tool",
                       "position": {"x": i * 90, "y": 40}, "dragging": False,
                       "data": {"tool": "ltt_llm.chat"}}
                      for i in range(so_node)],
            # ⚠️ CO Y dung gia tri KHAC mac dinh (`out`/`in`). Ban dau bai
            #    kiem dung dung "out"/"in", va phep tiem "vut sourceHandle di,
            #    hard-code out/in" VAN XANH — vi hai duong cho ra cung ket qua.
            #    Mot bo du lieu thu trung voi gia tri du phong thi KHONG PHAN
            #    BIET DUOC hai nhanh, va bai kiem tro thanh trang tri.
            "edges": [{"id": f"e{i}", "source": f"n{i}", "target": f"n{i+1}",
                       "sourceHandle": "anh_ra", "targetHandle": "van_ban_vao"}
                      for i in range(so_canh)],
        }],
    }


# ── Ba lớp dữ liệu thật ──────────────────────────────────────────────────────

def test_ban_co_document_v2_chuyen_duoc(db):
    from platform_core.models import WorkflowDraft
    from platform_core.workflow import di_tru_m1

    cu = _cu(db, document=_doc_v2())
    db.commit()

    ra = di_tru_m1.chuyen(db, chay_that=True)
    db.commit()

    assert ra["da_chuyen"] == 1
    draft = db.get(WorkflowDraft, ra["anh_xa"][cu.id])
    assert draft is not None and draft.document["version"] == 3


def test_ban_CHI_co_nodes_edges_cu_van_chuyen_duoc(db):
    """⭐ 4/10 bản ghi production có `document` RỖNG — chỉ còn `nodes`/`edges`.

    Bỏ qua chúng là bỏ mất **40 %** thứ cần chuyển, và bỏ theo cách im lặng:
    script báo "đã chuyển 6" và không ai hỏi 6 trên mấy.
    """
    from platform_core.models import WorkflowDraft
    from platform_core.workflow import di_tru_m1

    cu = _cu(db, document={}, nodes=[{"id": "n0", "type": "tool", "data": {}}],
             edges=[])
    db.commit()

    ra = di_tru_m1.chuyen(db, chay_that=True)
    db.commit()

    draft = db.get(WorkflowDraft, ra["anh_xa"][cu.id])
    assert draft is not None
    assert len(draft.document["pages"][0]["nodes"]) == 1


def test_ban_RONG_HOAN_TOAN_van_tao_workflow_nhung_KHAI_ra(db):
    """Rỗng hoàn toàn: vẫn giữ danh tính, nhưng phải **đếm riêng**.

    ⛔ Gộp nó vào `da_chuyen` là nói dối một cách dễ chịu: con số đẹp hơn, và
       người đọc tưởng có 10 đồ thị được cứu.
    """
    from platform_core.workflow import di_tru_m1

    _cu(db, document={}, nodes=[], edges=[])
    db.commit()

    ra = di_tru_m1.chuyen(db, chay_that=True)
    db.commit()

    assert ra["rong"] == 1
    assert ra["da_chuyen"] == 0


# ── Luỹ đẳng ─────────────────────────────────────────────────────────────────

def test_chay_HAI_LAN_khong_nhan_doi(db):
    """⛔ Một script di trú chạy lại vì hoảng không được biến thành sự cố."""
    from platform_core.models import Workflow, WorkflowDraft
    from platform_core.workflow import di_tru_m1

    _cu(db, document=_doc_v2())
    _cu(db, document=_doc_v2(so_node=2, so_canh=1))
    db.commit()

    di_tru_m1.chuyen(db, chay_that=True)
    db.commit()
    lan_hai = di_tru_m1.chuyen(db, chay_that=True)
    db.commit()

    assert db.query(Workflow).count() == 2
    assert db.query(WorkflowDraft).count() == 2
    assert lan_hai["da_chuyen"] == 0 and lan_hai["da_co"] == 2


# ── Chạy thử là MẶC ĐỊNH ────────────────────────────────────────────────────

def test_MAC_DINH_la_chay_thu_khong_ghi_gi(db):
    """⛔ Một script di trú mặc định GHI là một script chỉ cần gõ nhầm một lần.

    Mặc định chạy thử biến "lỡ tay" thành một báo cáo thay vì một lần ghi.
    """
    from platform_core.models import Workflow
    from platform_core.workflow import di_tru_m1

    _cu(db, document=_doc_v2())
    db.commit()

    ra = di_tru_m1.chuyen(db)
    db.commit()

    assert ra["chay_that"] is False
    assert ra["se_chuyen"] == 1
    assert db.query(Workflow).count() == 0, "chay thu ma van ghi la sai"


# ── Thứ Plan v1 đang VỨT ĐI, script phải GIỮ LẠI ────────────────────────────

def test_GIU_sourceHandle_targetHandle_ma_canvas_to_plan_dang_vut(db):
    """⭐ `27_29 §27.2`: *"dữ liệu để dựng cạnh có kiểu ĐÃ CÓ SẴN — hôm nay
    `canvas_to_plan()` vứt nó đi. Script chuyển GIỮ LẠI thứ đang bị vứt."*

    Đây là toàn bộ giá trị của `M-1`: không phải chép dữ liệu sang chỗ mới, mà
    **cứu phần thông tin mà đường cũ đang đánh rơi**.
    """
    from platform_core.models import WorkflowDraft
    from platform_core.workflow import di_tru_m1

    cu = _cu(db, document=_doc_v2(so_node=2, so_canh=1))
    db.commit()

    ra = di_tru_m1.chuyen(db, chay_that=True)
    db.commit()

    canh = db.get(WorkflowDraft, ra["anh_xa"][cu.id]).document["pages"][0]["edges"][0]
    assert canh["source_port"] == "anh_ra"
    assert canh["target_port"] == "van_ban_vao"


def test_giu_budget_va_goal(db):
    """`budget_max_credit` là một con số về TIỀN — mất nó là mất trần chi phí."""
    from platform_core.models import WorkflowDraft
    from platform_core.workflow import di_tru_m1

    cu = _cu(db, document=_doc_v2())
    db.commit()
    ra = di_tru_m1.chuyen(db, chay_that=True)
    db.commit()

    d = db.get(WorkflowDraft, ra["anh_xa"][cu.id]).document
    assert d["budget_max_credit"] == 120 and d["goal"] == "thu"


def test_giu_CHU_SO_HUU(db):
    """⛔ Chuyển nhầm chủ là cho người này thấy workflow của người kia."""
    from platform_core.models import Workflow
    from platform_core.workflow import di_tru_m1

    _cu(db, document=_doc_v2(), user_id="u_a")
    _cu(db, document=_doc_v2(so_node=2), user_id="u_b")
    db.commit()
    di_tru_m1.chuyen(db, chay_that=True)
    db.commit()

    assert {w.owner_id for w in db.query(Workflow).all()} == {"u_a", "u_b"}


def test_ten_mac_dinh_duoc_giu_nguyen_khong_bia_ten_moi(db):
    """10/10 bản ghi production mang tên mặc định. Đổi tên chúng là **bịa**."""
    from platform_core.models import Workflow
    from platform_core.workflow import di_tru_m1

    _cu(db, ten="Workflow mới", document=_doc_v2())
    db.commit()
    di_tru_m1.chuyen(db, chay_that=True)
    db.commit()

    assert db.query(Workflow).one().name == "Workflow mới"


# ── Báo cáo phải nói ĐỦ, không chỉ nói ĐẸP ──────────────────────────────────

# ── Thứ SQLite không cưỡng chế mà PostgreSQL CÓ ─────────────────────────────

def test_moi_chuoi_M1_ghi_ra_deu_VUA_do_dai_cot(db):
    """🔴 Bộ test chạy SQLite. Production chạy PostgreSQL. `VARCHAR(n)` là một
    trong những chỗ hai bên **không** đồng ý:

        SQLite      : do dai VARCHAR la trang tri, nhan moi chuoi
        PostgreSQL  : "value too long for type character varying(36)"

    Bản đầu của `M-1` đánh dấu bằng `published_version_id = "m1:" + id`, tức
    **39** ký tự vào một cột `String(36)`. Nó xanh trên SQLite, xanh cả khi
    diễn tập trên **bản sao chính dữ liệu production** — và sẽ chết ở lượt chạy
    thật.

    ⭐ Nên phép kiểm này **không** hỏi *"cái dấu ấy có ngắn không"*. Nó hỏi
       *"có chuỗi nào M-1 ghi ra mà dài hơn cột của nó không"* — mệnh đề bất
       biến với mọi trường thêm về sau. Một phép kiểm chỉ ghim đúng ca đã biết
       thì lần sau lại phải phát hiện lại từ đầu.

    Cùng họ với `BOOLEAN DEFAULT 1` ở các migration, nhưng khác trục:
    `tools/do_migration_tren_postgres.py` kiểm **migration**, còn đây là
    **đường chạy lúc runtime** — nó không đỡ được ca này.
    """
    from sqlalchemy import String

    from platform_core.models import Workflow, WorkflowDraft
    from platform_core.workflow import di_tru_m1

    _cu(db, document=_doc_v2())
    _cu(db, document={}, nodes=[{"id": "n0", "type": "t", "data": {}}])
    db.commit()

    di_tru_m1.chuyen(db, chay_that=True)
    db.commit()

    qua_dai = []
    for lop in (Workflow, WorkflowDraft):
        for hang in db.query(lop).all():
            for cot in lop.__table__.columns:
                gioi_han = getattr(cot.type, "length", None)
                if not isinstance(cot.type, String) or not gioi_han:
                    continue
                gia_tri = getattr(hang, cot.name, None)
                if isinstance(gia_tri, str) and len(gia_tri) > gioi_han:
                    qua_dai.append(
                        f"{lop.__tablename__}.{cot.name}: "
                        f"{len(gia_tri)} ky tu > {gioi_han}")

    assert not qua_dai, (
        "PostgreSQL se TU CHOI nhung gia tri nay: " + "; ".join(qua_dai))


def test_bao_cao_cong_lai_dung_bang_TONG_SO_ban_ghi(db):
    """⭐ Bất biến kiểm được: `đã_chuyển + rỗng + đã_có = tổng`.

    Không có nó, một nhánh `continue` bị bỏ quên sẽ làm vài bản ghi biến mất
    khỏi mọi con số — và một báo cáo không cộng lại được là một báo cáo không
    ai kiểm được.
    """
    from platform_core.models import AgentWorkflow
    from platform_core.workflow import di_tru_m1

    _cu(db, document=_doc_v2())
    _cu(db, document={}, nodes=[{"id": "n0", "type": "t", "data": {}}])
    _cu(db, document={}, nodes=[], edges=[])
    db.commit()

    ra = di_tru_m1.chuyen(db, chay_that=True)
    db.commit()
    tong = db.query(AgentWorkflow).count()
    assert ra["da_chuyen"] + ra["rong"] + ra["da_co"] == tong == 3


# ── Vá trang cho bản ĐÃ di trú (09/09/2026) ─────────────────────────────────

def _draft_thieu_khoa(db, wf_id: str):
    """Đúng hình dạng `_trang_v3` bản đầu sinh ra: 4 khoá thay vì 8."""
    from platform_core.models import WorkflowDraft

    d = WorkflowDraft(workflow_id=wf_id, revision=1, document={
        "version": 3, "goal": "g", "budget_max_credit": 10,
        "active_page_id": "p1",
        "pages": [{"id": "p1", "name": "", "nodes": [], "edges": []}]})
    db.add(d)
    db.flush()
    return d


def test_va_trang_dien_du_khoa_cho_ban_DA_di_tru(db):
    """🔴 `chuyen()` luỹ đẳng nên nó **không tự lành** bản đã chuyển.

    Ngày 09/09 đúng tình huống ấy: 9 workflow production đã ở dạng thiếu bốn
    khoá, và Canvas trắng màn khi mở chúng.
    """
    from platform_core.workflow import di_tru_m1

    d = _draft_thieu_khoa(db, "w1")
    db.commit()

    ra = di_tru_m1.va_trang(db, chay_that=True)
    db.commit()

    assert ra["da_va"] == 1 and ra["da_du"] == 0
    trang = d.document["pages"][0]
    for khoa in ("viewport", "frames", "notes", "comments", "view"):
        assert khoa in trang, khoa


def test_va_trang_KHONG_dung_toi_ban_da_du(db):
    """⭐ Đối chứng. Không có bài này, một bản vá *"ghi đè mọi trang"* cũng làm
    bài trên xanh — và nó sẽ **xoá** `viewport` người dùng đã kéo."""
    from platform_core.workflow import di_tru_m1

    d = _draft_thieu_khoa(db, "w1")
    db.commit()
    di_tru_m1.va_trang(db, chay_that=True)
    db.commit()
    rev_sau_lan_dau = d.revision

    lai = di_tru_m1.va_trang(db, chay_that=True)
    db.commit()
    assert lai["da_va"] == 0 and lai["da_du"] == 1
    assert d.revision == rev_sau_lan_dau, "ban da du khong duoc tang revision"


def test_va_trang_GIU_viewport_va_node_dang_co(db):
    """⛔ Chỉ THÊM. Một `viewport` người dùng đã kéo là thông tin thật."""
    from platform_core.models import WorkflowDraft
    from platform_core.workflow import di_tru_m1

    vp = {"x": 88, "y": -12, "zoom": 2.0}
    d = WorkflowDraft(workflow_id="w1", revision=1, document={
        "version": 3, "goal": "g", "budget_max_credit": 10,
        "active_page_id": "p1",
        "pages": [{"id": "p1", "name": "T", "viewport": vp,
                   "nodes": [{"id": "n0", "type": "tool", "data": {"tool": "x"}}],
                   "edges": [{"id": "e", "source_node": "n0",
                              "target_node": "n0", "source_port": "anh_ra",
                              "target_port": "van_ban_vao", "kind": "DATA"}]}]})
    db.add(d)
    db.commit()

    di_tru_m1.va_trang(db, chay_that=True)
    db.commit()
    t = d.document["pages"][0]
    assert t["viewport"] == vp
    assert t["nodes"][0]["data"]["tool"] == "x"
    assert t["edges"][0]["source_port"] == "anh_ra"


def test_va_trang_MAC_DINH_la_chay_thu(db):
    from platform_core.workflow import di_tru_m1

    d = _draft_thieu_khoa(db, "w1")
    db.commit()
    ra = di_tru_m1.va_trang(db)
    db.commit()
    assert ra["chay_that"] is False and ra["se_va"] == 1
    assert "viewport" not in d.document["pages"][0]
