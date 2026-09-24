"""P9b task 1 — `POST /agent/api/v3/runs/{id}/nodes/{node}/thu-lai` (spec §14
*"Thử lại node: tạo attempt mới (cần hold còn đủ; không thì 402)"*).

## 🔴 Cửa này CHẠM SỔ CREDIT — ba mệnh đề về tiền, đo được

1. **⛔ KHÔNG khoản giữ thứ hai.** `tien.giu_cho_run` là **một lần/run**
   (`tien.py`, `test_965`). Một lượt thử lại là một **job mới**, nhưng job của
   động cơ workflow không tự giữ tiền — nó nằm dưới khoản giữ của run. Phép
   kiểm đếm bút toán `CREDIT_HOLD` **trước và sau** và đòi con số KHÔNG ĐỔI.
2. **Run đã KẾT SỔ thì từ chối.** Đây là chỗ đặc tả tự mâu thuẫn: §14 viết
   *"run đang FAILED ⇒ thử lại"*, nhưng `FAILED ∈ may_trang_thai.RUN_KET_THUC`
   và `may_trang_thai.chuyen_run` gọi thẳng `ket_so.ket_so()` khi vào trạng
   thái kết thúc ⇒ khoản giữ **đã nhả**, `hold_id` đã xoá, sổ của khách đã
   chốt. Chạy tiếp một node dưới một khoản giữ không còn là nền tảng làm không
   công. `platform_core/agent/supervisor.py` đã thu hẹp đúng chỗ này cho §12.4
   (mã `run_da_ket_so`, đã gộp `main`) — cửa này **dùng lại đúng luật đó**,
   không phát minh luật thứ hai.
3. **Hold còn đủ cho trần của chính node ấy.** `estimated_max` trừ chi phí
   thật đã ghi phải còn ≥ `gia_tran` của node. Đây là chữ "cần hold còn đủ"
   của §14, tính từ số đã có — ⛔ không cột mới.

## Vì sao `retry.max` KHÔNG gác cửa này

`retry.max` (§5.6, mặc định **0**) là chính sách retry **TỰ ĐỘNG**: bao nhiêu
lần động cơ được tự gõ lại cửa provider mà không hỏi ai. §12.4 gắn nó cho
supervisor (*"trong `retry.max` còn lại"*) vì supervisor cũng là **máy**. §14
gắn cho cửa NGƯỜI BẤM đúng một điều kiện, và điều kiện ấy là **tiền**, không
phải `retry.max`. Gác thêm `retry.max` ở đây làm nút "Thử lại" **chết theo mặc
định** (`max = 0` ⇒ mọi lần bấm 409) — một nút không bao giờ chạy.

⛔ Cái KHÔNG được nới: `thu_lai.KHONG_THU_LAI` (`ABANDONED`/`CANCELLED`/
`SUCCEEDED`/`SKIPPED`). `ABANDONED` = provider **có thể đã nhận**; một lượt
thử lại là một side effect thứ hai không đảo được, và ý muốn của người bấm
không đảo được nó.
"""
from __future__ import annotations

import json
import uuid

import pytest

from tests.test_1723_v3_tao_va_doc_run import (CC, _chay, _publish,  # noqa: F401
                                               _uid, api)


def _thu_lai(client, token, run_id: str, node_id: str):
    return client.post(
        f"/agent/api/v3/runs/{run_id}/nodes/{node_id}/thu-lai",
        headers={"X-CSRF-Token": token,
                 "Idempotency-Key": f"t3451-{uuid.uuid4().hex}"}, json={})


def _dem_hold(email: str) -> int:
    import platform_core.db as dbmod
    from platform_core.models import CREDIT_HOLD, CreditEntry
    db = next(dbmod.get_session())
    try:
        return db.query(CreditEntry).filter_by(
            user_id=_uid(email), kind=CREDIT_HOLD).count()
    finally:
        db.close()


def _chuyen(run_id: str, node_id: str, *, sang: str, **kw) -> bool:
    import platform_core.db as dbmod
    from platform_core.workflow import may_trang_thai
    db = next(dbmod.get_session())
    try:
        ok = may_trang_thai.chuyen_node(db, run_id, node_id, sang=sang,
                                        mo_ta="test 3451", **kw)
        db.commit()
        return ok
    finally:
        db.close()


def _cho_FAILED(run_id: str, node_id: str = "a"):
    assert _chuyen(run_id, node_id, sang="READY")
    assert _chuyen(run_id, node_id, sang="FAILED", error="provider_loi: 500",
                   attempt_number=1)


def _anh(run_id: str, node_id: str = "a"):
    import platform_core.db as dbmod
    from platform_core.workflow import thi_hanh
    db = next(dbmod.get_session())
    try:
        a = thi_hanh.anh_chup_hien_tai(db, run_id, node_id)
        return (a.execution_status, int(a.attempt_number),
                dict(a.output_ref or {})) if a else None
    finally:
        db.close()


def _publish2(owner_id: str, *, credit_cap: int = 500) -> str:
    """Workflow HAI node — cần cho phép kiểm "hold không còn đủ"."""
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.workflow import dinh_nghia
    db = next(dbmod.get_session())
    try:
        wf = dinh_nghia.tao_workflow(db, owner_id=owner_id, name="w2")
        nut = [{"id": n, "type": "tool", "position": {"x": i * 100, "y": 0},
                "data": {"tool": "text.chat", "params": {}}}
               for i, n in enumerate(("a", "b"))]
        dinh_nghia.luu_draft(db, wf.id, document={
            "version": 3, "goal": "", "budget_max_credit": 0,
            "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "", "edges": [], "nodes": nut}]},
            revision=0)
        ver = dinh_nghia.xuat_ban_draft(db, wf.id, created_by=owner_id,
                                        cong_cu=CC)
        wf.published_version_id = ver.id
        credit.nap(db, owner_id, credit_cap, note="test")
        db.commit()
        return wf.id
    finally:
        db.close()


# ── 1. Tiền ──────────────────────────────────────────────────────────────────

def test_thu_lai_KHONG_giu_them_mot_khoan_nao(api):  # noqa: F811
    """🔴 Mệnh đề đắt nhất: một lượt thử lại KHÔNG sinh bút toán `hold` thứ hai."""
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    _cho_FAILED(run_id)
    truoc = _dem_hold("v3run-a@example.com")

    r = _thu_lai(a, token_a, run_id, "a")
    assert r.status_code == 200, r.text
    assert _dem_hold("v3run-a@example.com") == truoc

    # Node đã được hẹn chạy lại, và `attempt` TĂNG — `attempt` đứng yên là
    # màn hình nói dối (lượt 2 hiện là lượt 1) VÀ là khoá khử trùng
    # (`cau_noi._khoa_idem` với `side_effect="none"` băm theo `lan`) dùng lại.
    tt, lan, out = _anh(run_id)
    assert (tt, lan) == ("RETRY_SCHEDULED", 2)
    from platform_core.workflow import thu_lai
    assert thu_lai.KHOA_HAN in out          # có hạn ⇒ `den_han` nhặt được


def test_co_wakeup_retry_de_dong_co_thuc_su_quay_lai(api):  # noqa: F811
    """Đối chứng cho phép trên: đổi trạng thái mà KHÔNG hẹn đánh thức thì node
    nằm `RETRY_SCHEDULED` tới khi `TRAN_RUN` (20 giờ) hết hạn — vẫn "xanh" ở
    mọi phép chỉ đọc ảnh chụp."""
    import platform_core.db as dbmod
    from platform_core.models import Wakeup
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    _cho_FAILED(run_id)
    assert _thu_lai(a, token_a, run_id, "a").status_code == 200

    db = next(dbmod.get_session())
    try:
        assert db.query(Wakeup).filter_by(run_id=run_id, kind="retry").count() == 1
    finally:
        db.close()


def test_run_da_ket_so_tra_402(api):  # noqa: F811
    import platform_core.db as dbmod
    from platform_core.workflow import may_trang_thai
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    _cho_FAILED(run_id)
    db = next(dbmod.get_session())
    try:
        assert may_trang_thai.chuyen_run(db, run_id, sang="RUNNING")
        assert may_trang_thai.chuyen_run(db, run_id, sang="FAILED")
        db.commit()
    finally:
        db.close()

    r = _thu_lai(a, token_a, run_id, "a")
    assert r.status_code == 402, r.text
    assert r.json()["detail"]["ma"] == "run_da_ket_so"


def test_hold_khong_con_du_tra_402(api):  # noqa: F811
    """`estimated_max` trừ chi phí thật đã ghi < `gia_tran` của node ⇒ 402.

    Chi phí 5 credit ghi cho node `b` là **dựng tay** (không có đường thật nào
    ghi quá trần của một node) — đúng ý đồ: phép kiểm này đo NHÁNH SỐ HỌC của
    cửa, và một nhánh không có đối chứng số học là một nhánh không ai biết nó
    còn đúng hay không.
    """
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish2(_uid("v3run-a@example.com"))).json()["id"]
    _cho_FAILED(run_id, "a")
    assert _chuyen(run_id, "b", sang="READY")
    assert _chuyen(run_id, "b", sang="SUCCEEDED", cost_credit=5)   # trần run = 6

    r = _thu_lai(a, token_a, run_id, "a")
    assert r.status_code == 402, r.text
    assert r.json()["detail"]["ma"] == "hold_khong_du"


def test_doi_chung_hold_con_du_thi_200(api):  # noqa: F811
    """⭐ ĐỐI CHỨNG của phép trên: cùng đồ thị, chi phí NHỎ hơn ⇒ đi qua."""
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish2(_uid("v3run-a@example.com"))).json()["id"]
    _cho_FAILED(run_id, "a")
    assert _chuyen(run_id, "b", sang="READY")
    assert _chuyen(run_id, "b", sang="SUCCEEDED", cost_credit=3)   # còn 3 ≥ 3
    assert _thu_lai(a, token_a, run_id, "a").status_code == 200


# ── 2. Side effect ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("sang", ["ABANDONED", "CANCELLED"])
def test_trang_thai_trong_KHONG_THU_LAI_bi_tu_choi(api, sang):  # noqa: F811
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    assert _chuyen(run_id, "a", sang="READY")
    assert _chuyen(run_id, "a", sang="QUEUED")
    assert _chuyen(run_id, "a", sang=sang)

    r = _thu_lai(a, token_a, run_id, "a")
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["ma"] == "khong_thu_lai_duoc"


def test_node_chua_hong_thi_tu_choi(api):  # noqa: F811
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    r = _thu_lai(a, token_a, run_id, "a")          # còn PENDING
    assert r.status_code == 409
    assert r.json()["detail"]["ma"] == "trang_thai_node_sai"


def test_retry_max_0_van_bam_thu_lai_duoc(api):  # noqa: F811
    """`retry.max` mặc định 0 gác retry TỰ ĐỘNG, ⛔ không gác người bấm.

    Không có phép này, một cài đặt "tiện tay gọi `thu_lai.con_luot`" làm nút
    Thử lại chết theo mặc định — và chết **im lặng đúng luật**, nên không ai
    coi đó là lỗi.
    """
    import platform_core.db as dbmod
    from platform_core.models import WorkflowRun, WorkflowVersion
    from platform_core.workflow import thu_lai
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    _cho_FAILED(run_id)

    db = next(dbmod.get_session())
    try:
        ver = db.get(WorkflowVersion, db.get(WorkflowRun, run_id).version_id)
        nut = next(n for n in ver.graph["nodes"] if n["id"] == "a")
        assert thu_lai.doc_chinh_sach(nut).so_lan == 0      # tiền đề
        assert thu_lai.con_luot(nut, 1) is False            # máy thì HẾT lượt
    finally:
        db.close()
    assert _thu_lai(a, token_a, run_id, "a").status_code == 200   # người thì KHÔNG


# ── 3. Ranh giới ─────────────────────────────────────────────────────────────

def test_node_khong_co_trong_do_thi_tra_404(api):  # noqa: F811
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    r = _thu_lai(a, token_a, run_id, "khong-ton-tai")
    assert r.status_code == 404, r.text
    assert r.json()["detail"]["ma"] == "node_khong_ton_tai"


def test_run_cua_nguoi_khac_tra_404(api):  # noqa: F811
    a, token_a, b, token_b = api
    run_a = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    _cho_FAILED(run_a)
    assert _thu_lai(b, token_b, run_a, "a").status_code == 404
    # Đối chứng: chính chủ vẫn 200 — 404 ở trên là RANH GIỚI, không phải
    # một cửa hỏng cho mọi người.
    assert _thu_lai(a, token_a, run_a, "a").status_code == 200


def test_thieu_csrf_thi_tu_choi(api):  # noqa: F811
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    _cho_FAILED(run_id)
    r = a.post(f"/agent/api/v3/runs/{run_id}/nodes/a/thu-lai",
               content=json.dumps({}),
               headers={"Content-Type": "application/json"})
    assert r.status_code in (400, 403), r.text
