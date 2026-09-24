"""P9b task 5 — DIỄN TẬP LỖI §18.7 trên **bề mặt quan sát** (điều kiện ra P9b).

§18.7 liệt kê 17 tình huống phải diễn tập *"trước khi mở cho khách"*. Tệp này
**không** diễn tập cả 17 — phần lớn thuộc động cơ, worker, connector, trigger,
tức làn khác. Nó diễn tập đúng **tập con mà làn này chạm**, và bảng độ phủ đầy
đủ (đã đo / chưa đo / không thuộc làn) nằm ở
`docs/superpowers/reports/p9b-quan-sat-2/task-5-report.md`.

⚠️ Một phép diễn tập chỉ có giá khi nó hỏi *"màn hình NÓI GÌ trong lúc hỏng"*.
   Phép kiểm chức năng hỏi "kết quả đúng không"; phép diễn tập hỏi **"người
   vận hành nhìn thấy gì, và có tin nhầm được không"**. Đó là lý do mỗi bài
   dưới đây khẳng định về **thứ cửa quan sát trả ra**, không chỉ về CSDL.
"""
from __future__ import annotations

import json
import uuid

from tests.test_1723_v3_tao_va_doc_run import (CC, _chay, _publish,  # noqa: F401
                                               _uid, api)


def _chuyen(run_id: str, node_id: str, *, sang: str, **kw) -> bool:
    import platform_core.db as dbmod
    from platform_core.workflow import may_trang_thai
    db = next(dbmod.get_session())
    try:
        ok = may_trang_thai.chuyen_node(db, run_id, node_id, sang=sang,
                                        mo_ta="dien tap 3453", **kw)
        db.commit()
        return ok
    finally:
        db.close()


def _thu_lai(client, token, run_id, node_id):
    return client.post(
        f"/agent/api/v3/runs/{run_id}/nodes/{node_id}/thu-lai",
        headers={"X-CSRF-Token": token,
                 "Idempotency-Key": f"t3453-{uuid.uuid4().hex}"}, json={})


def _hold(email: str) -> int:
    import platform_core.db as dbmod
    from platform_core.models import CREDIT_HOLD, CreditEntry
    db = next(dbmod.get_session())
    try:
        return db.query(CreditEntry).filter_by(
            user_id=_uid(email), kind=CREDIT_HOLD).count()
    finally:
        db.close()


# ── §18.7 "huỷ" ──────────────────────────────────────────────────────────────

def test_huy__luong_SSE_dong_NGAY_chu_khong_treo_toi_moc_90s(api):  # noqa: F811
    """Huỷ một run đang chạy ⇒ luồng trực tiếp phải **đóng**, có khung `dong`.

    Nếu luồng treo tới mốc 90 s, mỗi lần huỷ để lại một kết nối chết trên máy
    chủ và một màn hình không biết mình đã hết việc để nghe.
    """
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    a.post(f"/agent/api/v3/runs/{run_id}/cancel",
           headers={"X-CSRF-Token": token_a}, json={})

    with a.stream("GET", f"/agent/api/v3/runs/{run_id}/su-kien") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        tho = "".join(r.iter_text())
    assert "event: dong" in tho
    # ⭐ Và khung cuối phải NÓI RA trạng thái thật — một luồng đóng im lặng để
    #    màn hình đứng ở ảnh chụp cũ.
    cuoi = [d for d in tho.splitlines() if d.startswith("data: ")][-2]
    assert json.loads(cuoi[6:])["status"] == "CANCELLED"


# ── §18.7 "retry" ────────────────────────────────────────────────────────────

def test_retry_thu_cong__khong_sinh_khoan_giu_thu_hai(api):  # noqa: F811
    """🔴 Diễn tập đắt nhất: một lượt thử lại KHÔNG được chạm sổ lần hai."""
    a, token_a, _, _ = api
    run_id = _chay(a, token_a, _publish(_uid("v3run-a@example.com"))).json()["id"]
    assert _chuyen(run_id, "a", sang="READY")
    assert _chuyen(run_id, "a", sang="FAILED", error="provider_loi: 500")
    truoc = _hold("v3run-a@example.com")

    r = _thu_lai(a, token_a, run_id, "a")
    assert r.status_code == 200, r.text
    assert _hold("v3run-a@example.com") == truoc
    # Cửa quan sát phải nói ra ngay: node đã sang lượt 2.
    nut = {n["node_id"]: n for n in r.json()["nodes"]}["a"]
    assert (nut["status"], nut["attempt"]) == ("RETRY_SCHEDULED", 2)


def test_provider_mo_ho__ABANDONED_thi_TU_CHOI_thu_lai(api):  # noqa: F811
    """§18.7 "provider mơ hồ". `ABANDONED` = provider **có thể đã nhận**.

    Đây là ca mà một nút bấm dễ chịu sẽ tạo một side effect thứ hai không đảo
    được. Đối chứng ngay dưới: cùng cửa, node `FAILED` thì **đi qua** — nên
    409 ở đây là một LUẬT, không phải một cửa hỏng.
    """
    a, token_a, _, _ = api
    wf = _publish(_uid("v3run-a@example.com"))
    mo_ho = _chay(a, token_a, wf).json()["id"]
    assert _chuyen(mo_ho, "a", sang="READY")
    assert _chuyen(mo_ho, "a", sang="QUEUED")
    assert _chuyen(mo_ho, "a", sang="ABANDONED", error="ket_qua_mo_ho: timeout")
    r = _thu_lai(a, token_a, mo_ho, "a")
    assert r.status_code == 409
    assert r.json()["detail"]["ma"] == "khong_thu_lai_duoc"

    hong = _chay(a, token_a, wf).json()["id"]
    assert _chuyen(hong, "a", sang="READY")
    assert _chuyen(hong, "a", sang="FAILED", error="provider_loi: 500")
    assert _thu_lai(a, token_a, hong, "a").status_code == 200


# ── §18.7 "publish version mới khi run đang chạy" ────────────────────────────

def test_publish_ban_moi_giua_chung__run_cu_GHIM_va_diff_NOI_RA(api):  # noqa: F811
    """Publish một version mới trong lúc một run đang chạy.

    Hai điều phải đúng cùng lúc, và điều thứ hai là phần của làn này:
    1. Run cũ **ghim** `version_id` cũ — không bị kéo sang đồ thị mới giữa chừng.
    2. Cửa so sánh **nói ra** rằng hai lượt chạy không cùng một bản
       (`khac_version`). Không nói ra thì người đọc diff sẽ quy mọi khác biệt
       cho dữ liệu, trong khi thứ đổi là **đồ thị**.
    """
    import platform_core.db as dbmod
    from platform_core.models import Workflow
    from platform_core.workflow import dinh_nghia
    a, token_a, _, _ = api
    uid = _uid("v3run-a@example.com")
    wf_id = _publish(uid)
    cu = _chay(a, token_a, wf_id).json()
    assert _chuyen(cu["id"], "a", sang="READY")

    # Publish bản MỚI trong lúc run cũ còn sống.
    db = next(dbmod.get_session())
    try:
        dinh_nghia.luu_draft(db, wf_id, document={
            "version": 3, "goal": "", "budget_max_credit": 0,
            "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "", "edges": [], "nodes": [
                {"id": "a", "type": "tool", "position": {"x": 0, "y": 0},
                 "data": {"tool": "text.chat", "params": {}}},
                {"id": "b", "type": "tool", "position": {"x": 200, "y": 0},
                 "data": {"tool": "text.chat", "params": {}}}]}]}, revision=1)
        ver2 = dinh_nghia.xuat_ban_draft(db, wf_id, created_by=uid, cong_cu=CC)
        db.get(Workflow, wf_id).published_version_id = ver2.id
        db.commit(); ver2_id = ver2.id
    finally:
        db.close()
    moi = _chay(a, token_a, wf_id).json()

    # 1. Run cũ KHÔNG bị kéo sang đồ thị mới.
    van_cu = a.get(f"/agent/api/v3/runs/{cu['id']}").json()
    assert van_cu["version_id"] == cu["version_id"] != ver2_id
    assert [n["node_id"] for n in van_cu["nodes"]] == ["a"]
    assert moi["version_id"] == ver2_id

    # 2. Cửa so sánh NÓI RA điều đó.
    body = a.get(f"/agent/api/v3/runs/{cu['id']}/so-sanh",
                 params={"voi": moi["id"]}).json()
    assert body["khac_version"] is True
    # `b` chỉ có ở một bên ⇒ phải nằm trong `khac`, không được lặng lẽ biến mất.
    assert "b" in body["khac"]
