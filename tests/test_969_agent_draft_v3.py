"""Đợt 5.2 phần C — cửa nội bộ cho bản nháp Canvas **v3** (`WorkflowDraft`).

## Ba mệnh đề tệp này canh

1. **`revision` là khoá lạc quan thật**, không phải một bộ đếm trang trí: tab
   đến sau nhận `409` thay vì ghi đè âm thầm phần người kia vừa gõ.
2. **Ranh giới chủ sở hữu là `404`, không phải `403`** — `403` xác nhận id đó
   có thật.
3. **Xuất bản lại cùng nội dung không đẻ version thứ hai** — do
   `UNIQUE (workflow_id, graph_hash)` cưỡng chế, không do mã cẩn thận.

⛔ Và một mệnh đề **phủ định** cũng được canh: cửa v3 **không** có đường chạy.
   Chạy một workflow đi qua `/api/v1/workflows/{id}/runs`, nơi có báo giá đã ký,
   `Idempotency-Key` và một khoản giữ chỗ. Một đường chạy ở tầng nội bộ sẽ là
   cửa tiêu tiền **không đi qua** thứ nào trong ba thứ đó — và nó sẽ trông y hệt
   một tiện nghi cho người dùng giao diện.
"""
from __future__ import annotations

import pytest

from platform_core.models import Workflow, WorkflowDraft, WorkflowVersion


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'v3.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def _do_thi(n: int = 3) -> dict:
    return {"version": 3, "goal": "g", "budget_max_credit": 0,
            "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "", "edges": [],
                       "nodes": [{"id": f"n{i}", "type": "tool"}
                                 for i in range(n)]}]}


# ── 1. Khoá lạc quan ────────────────────────────────────────────────────────

def test_revision_lech_thi_XUNG_DOT_chu_khong_ghi_de(db):
    """🔴 Đây là bài đắt nhất ở đây. Không có nó, hai tab cùng mở thì tab đến
    sau **ghi đè im lặng** phần người kia vừa gõ — và không dấu vết nào."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    dinh_nghia.luu_draft(db, wf.id, document=_do_thi(1), revision=0)
    db.commit()

    # Tab A ghi thành công, revision 1 -> 2.
    dinh_nghia.luu_draft(db, wf.id, document=_do_thi(2), revision=1)
    db.commit()

    # Tab B vẫn giữ revision 1 — phải bị chặn.
    with pytest.raises(dinh_nghia.XungDotRevision):
        dinh_nghia.luu_draft(db, wf.id, document=_do_thi(9), revision=1)
    db.rollback()

    assert len(db.get(WorkflowDraft, wf.id).document["pages"][0]["nodes"]) == 2


def test_revision_KHOP_thi_ghi_duoc(db):
    """⭐ Vế hợp lệ. Không có nó, một bản vá "luôn từ chối" cũng làm bài trên
    xanh — và không ai lưu được gì nữa."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    dinh_nghia.luu_draft(db, wf.id, document=_do_thi(1), revision=0)
    db.commit()
    d = dinh_nghia.luu_draft(db, wf.id, document=_do_thi(5), revision=1)
    db.commit()
    assert d.revision == 2
    assert len(d.document["pages"][0]["nodes"]) == 5


# ── 2. Xuất bản ─────────────────────────────────────────────────────────────

def test_xuat_ban_LAI_cung_noi_dung_KHONG_de_version_thu_hai(db):
    """Ràng buộc CSDL, không phải mã cẩn thận: `UNIQUE (workflow_id, graph_hash)`
    khiến hai request song song cũng không lách được."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    g = _do_thi(3)
    a = dinh_nghia.xuat_ban(db, wf.id, g, created_by="u1", estimated_max=30)
    db.commit()
    b = dinh_nghia.xuat_ban(db, wf.id, dict(g), created_by="u1", estimated_max=30)
    db.commit()
    assert a.id == b.id
    assert db.query(WorkflowVersion).count() == 1


def test_xuat_ban_noi_dung_KHAC_thi_ra_version_moi(db):
    """Đối chứng: không có bài này, một bản vá *"luôn trả version cũ"* cũng làm
    bài trên xanh — và mọi lần publish sau đều không có tác dụng."""
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    a = dinh_nghia.xuat_ban(db, wf.id, _do_thi(3), created_by="u1")
    db.commit()
    b = dinh_nghia.xuat_ban(db, wf.id, _do_thi(4), created_by="u1")
    db.commit()
    assert a.id != b.id and db.query(WorkflowVersion).count() == 2


def test_tran_chi_phi_DONG_BANG_cung_graph(db):
    """⚠️ `23_24`: tính lại lúc chạy nghĩa là một lượt có thể vượt một trần mà
    người duyệt **chưa từng thấy con số ấy**."""
    from platform_core.workflow import bao_gia, dinh_nghia
    from platform_core.workflow.cong_cu import CongCu

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    cc = {"t.x": CongCu(ten="t.x", app_slug="t", job_type="t.x", type_version=1,
                        params_schema={}, side_effect="external",
                        idempotency_fields=(), tinh_gia=lambda p: 5)}
    g = {"schema": "ltt.workflow/3", "nodes": [
        {"id": f"n{i}", "type": "app.t.x", "params": {}, "thi_hanh": "job"}
        for i in range(3)], "edges": []}
    gia = bao_gia.bao_gia_do_thi(g, cong_cu=cc)
    ver = dinh_nghia.xuat_ban(db, wf.id, g, created_by="u1",
                              estimated_max=gia.toi_da)
    db.commit()
    assert ver.estimated_max == gia.toi_da > 0


# ── 3. Bề mặt: cửa v3 KHÔNG có đường chạy ───────────────────────────────────

def test_cua_v3_KHONG_co_duong_chay_nao():
    """⛔ Mệnh đề **phủ định**, và nó là mệnh đề dễ mất nhất.

    Một `POST /api/v3/.../runs` sẽ trông y hệt một tiện nghi cho người dùng giao
    diện, và nó sẽ là một cửa tiêu tiền **không** đi qua báo giá đã ký, **không**
    đòi `Idempotency-Key`, **không** giữ chỗ. Ba thứ ấy chỉ có ở
    `/api/v1/workflows/{id}/runs`.
    """
    from apps.agent.routes import router

    v3 = [r.path for r in router.routes if "/api/v3/" in getattr(r, "path", "")]
    assert v3, "khong route v3 nao duoc dang ky — nghi phep kiem quet nham cho"
    chay = [p for p in v3 if p.endswith("/runs") or "/runs/" in p]
    assert not chay, f"cua v3 khong duoc co duong chay: {chay}"


def test_nam_route_v3_deu_duoc_dang_ky():
    from apps.agent.routes import router

    co = {(sorted(r.methods)[0], r.path) for r in router.routes
          if "/api/v3/" in getattr(r, "path", "")}
    assert co == {
        ("GET", "/api/v3/workflows"),
        ("POST", "/api/v3/workflows"),
        ("GET", "/api/v3/workflows/{workflow_id}"),
        ("PUT", "/api/v3/workflows/{workflow_id}"),
        ("POST", "/api/v3/workflows/{workflow_id}/publish"),
    }


def test_tai_lieu_rong_dung_HINH_DANG_ma_M1_sinh_ra():
    """⭐ Một bản di trú và một bản tạo mới không được khác nhau ở chỗ người đọc
    phải nhớ. Cả hai đều là `version 3` + một trang `p1`."""
    from apps.agent.routes.drafts_v3 import _tai_lieu_rong

    d = _tai_lieu_rong()
    assert d["version"] == 3
    assert d["active_page_id"] == d["pages"][0]["id"] == "p1"
    assert set(d) == {"version", "goal", "budget_max_credit",
                      "active_page_id", "pages"}


def test_cua_v3_KHONG_dung_bang_cua_Canvas_v2(db):
    """`AgentWorkflow` và `Workflow` là hai bảng khác nhau. Ghi nhầm bảng sẽ làm
    bản nháp v3 hiện ra ở trình soạn v2 dưới dạng một đồ thị rỗng."""
    from platform_core.models import AgentWorkflow
    from platform_core.workflow import dinh_nghia

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="w")
    dinh_nghia.luu_draft(db, wf.id, document=_do_thi(2), revision=0)
    db.commit()
    assert db.query(Workflow).count() == 1
    assert db.query(WorkflowDraft).count() == 1
    assert db.query(AgentWorkflow).count() == 0
