"""P9b task 4 (nốt) — `POST /agent/api/v3/runs/{id}/chay-lai-tu/{node}` (§14).

Spec §14: *"tạo run **mới** cùng version, sao output các node **không phải hậu
duệ** của node chọn từ run cũ (tham chiếu artifact, không chép byte), chạy từ
node đó. `workflow_run.chay_lai_tu_run_id` ghi nguồn gốc."*

## 🔴 BA MỆNH ĐỀ VỀ TIỀN — tệp này canh bằng SỐ, không bằng lời

1. **Run mới là run ĐỘC LẬP ⇒ khoản giữ RIÊNG.** ⛔ Không dùng lại `hold_id`
   của run cũ (nó đã hoặc sẽ được quyết toán cho run cũ), ⛔ không mượn
   `parent_run_id` — run con **không** có hold riêng (`run_con.py`,
   `ket_so.ket_so` cộng chi phí con lên cha). Mượn quan hệ ấy là lặng lẽ biến
   một lượt chạy lại thành một run **không trả tiền**, và mọi phép kiểm về
   hold vẫn xanh.
2. **Node TÁI DỤNG không được tính tiền lần hai.** Ảnh chụp sao sang run mới
   mang `cost_credit = 0`: khách đã trả cho chính công việc ấy ở run cũ.
3. ⭐ **ĐỐI CHỨNG — phép đo phải PHÂN BIỆT được.** Một lượt chạy lại mà
   **không** node nào tái dụng được phải tốn **đúng bằng** một run mới tinh.
   Thiếu phép này, một cài đặt "ghi `cost_credit = 0` cho MỌI node" vẫn xanh ở
   mệnh đề 2 — và nó cho không toàn bộ lượt chạy.
"""
from __future__ import annotations

import uuid

from tests.test_1723_v3_tao_va_doc_run import (CC, _chay, _publish,  # noqa: F401
                                               _uid, api)

EMAIL = "v3run-a@example.com"


def _publish2(owner_id: str, *, credit_cap: int = 500) -> str:
    """Workflow HAI node `a -> b`, mỗi node 3 credit ⇒ trần run = 6."""
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.workflow import dinh_nghia
    db = next(dbmod.get_session())
    try:
        wf = dinh_nghia.tao_workflow(db, owner_id=owner_id, name="w2")
        dinh_nghia.luu_draft(db, wf.id, document={
            "version": 3, "goal": "", "budget_max_credit": 0,
            "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "", "nodes": [
                {"id": n, "type": "tool", "position": {"x": i * 200, "y": 0},
                 "data": {"tool": "text.chat", "params": {}}}
                for i, n in enumerate(("a", "b"))],
                "edges": [{"id": "e1", "source": "a", "target": "b",
                           "sourceHandle": "content", "targetHandle": "prompt"}]}]},
            revision=0)
        ver = dinh_nghia.xuat_ban_draft(db, wf.id, created_by=owner_id,
                                        cong_cu=CC)
        wf.published_version_id = ver.id
        credit.nap(db, owner_id, credit_cap, note="test")
        db.commit()
        return wf.id
    finally:
        db.close()


def _chay_lai(client, token, run_id: str, node_id: str, *, khoa=None):
    return client.post(
        f"/agent/api/v3/runs/{run_id}/chay-lai-tu/{node_id}",
        headers={"X-CSRF-Token": token,
                 "Idempotency-Key": khoa or f"t3454-{uuid.uuid4().hex}"},
        json={})


def _xong(run_id: str, node_id: str, *, gia: int, ra: dict | None = None):
    """Cho một node CHẠY XONG thật sự (qua máy trạng thái), tốn `gia` credit."""
    import platform_core.db as dbmod
    from platform_core.workflow import may_trang_thai
    db = next(dbmod.get_session())
    try:
        assert may_trang_thai.chuyen_node(db, run_id, node_id, sang="READY",
                                          mo_ta="t3454")
        assert may_trang_thai.chuyen_node(
            db, run_id, node_id, sang="SUCCEEDED", mo_ta="t3454",
            cost_credit=gia, output_ref=ra or {"content": f"ra-{node_id}"})
        db.commit()
    finally:
        db.close()


def _ket_thuc(run_id: str) -> int:
    """Đưa run về SUCCEEDED (kích `ket_so`) và trả `actual_cost` đã chốt."""
    import platform_core.db as dbmod
    from platform_core.models import WorkflowRun
    from platform_core.workflow import may_trang_thai
    db = next(dbmod.get_session())
    try:
        may_trang_thai.chuyen_run(db, run_id, sang="RUNNING")
        may_trang_thai.chuyen_run(db, run_id, sang="SUCCEEDED")
        db.commit()
        return int(db.get(WorkflowRun, run_id).actual_cost or 0)
    finally:
        db.close()


def _run(run_id: str):
    import platform_core.db as dbmod
    from platform_core.models import WorkflowRun
    db = next(dbmod.get_session())
    try:
        r = db.get(WorkflowRun, run_id)
        return {"hold_id": r.hold_id, "parent_run_id": r.parent_run_id,
                "chay_lai_tu_run_id": r.chay_lai_tu_run_id,
                "version_id": r.version_id,
                "estimated_max": int(r.estimated_max or 0)}
    finally:
        db.close()


def _anh(run_id: str, node_id: str):
    import platform_core.db as dbmod
    from platform_core.workflow import thi_hanh
    db = next(dbmod.get_session())
    try:
        a = thi_hanh.anh_chup_hien_tai(db, run_id, node_id)
        return None if a is None else {
            "status": a.execution_status, "cost": int(a.cost_credit),
            "output_ref": dict(a.output_ref or {})}
    finally:
        db.close()


def _dem_hold() -> int:
    import platform_core.db as dbmod
    from platform_core.models import CREDIT_HOLD, CreditEntry
    db = next(dbmod.get_session())
    try:
        return db.query(CreditEntry).filter_by(
            user_id=_uid(EMAIL), kind=CREDIT_HOLD).count()
    finally:
        db.close()


# ── 1. Khoản giữ RIÊNG, và đúng loại quan hệ ─────────────────────────────────

def test_run_chay_lai_co_khoan_giu_RIENG_va_khong_phai_run_con(api):  # noqa: F811
    a, token_a, _, _ = api
    cu = _chay(a, token_a, _publish2(_uid(EMAIL))).json()["id"]
    _xong(cu, "a", gia=3)
    truoc = _dem_hold()

    r = _chay_lai(a, token_a, cu, "b")
    assert r.status_code == 201, r.text
    moi = r.json()["id"]

    # ĐÚNG MỘT khoản giữ mới — không hai, không không.
    assert _dem_hold() == truoc + 1
    t_moi, t_cu = _run(moi), _run(cu)
    assert t_moi["hold_id"] == moi != t_cu["hold_id"]     # ⛔ khong dung lai
    assert t_moi["chay_lai_tu_run_id"] == cu
    # ⛔ KHONG phai quan he cha-con: run con khong co hold rieng.
    assert t_moi["parent_run_id"] == ""
    # Cùng version (spec §14 "cùng version"), nên cùng trần.
    assert t_moi["version_id"] == t_cu["version_id"]
    assert t_moi["estimated_max"] == t_cu["estimated_max"] == 6


def test_ghim_version_CU_chu_khong_phai_ban_publish_moi_nhat(api):  # noqa: F811
    """Publish bản mới rồi mới bấm chạy lại ⇒ vẫn chạy ĐỒ THỊ CŨ.

    Chạy lại trên một đồ thị khác là sao output của những node **có thể không
    còn tồn tại** sang một đồ thị **có thể không có chúng** — và không ai báo.
    """
    import platform_core.db as dbmod
    from platform_core.models import Workflow
    from platform_core.workflow import dinh_nghia
    a, token_a, _, _ = api
    uid = _uid(EMAIL)
    wf_id = _publish2(uid)
    cu = _chay(a, token_a, wf_id).json()
    _xong(cu["id"], "a", gia=3)

    db = next(dbmod.get_session())
    try:
        dinh_nghia.luu_draft(db, wf_id, document={
            "version": 3, "goal": "", "budget_max_credit": 0,
            "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "", "edges": [], "nodes": [
                {"id": "z", "type": "tool", "position": {"x": 0, "y": 0},
                 "data": {"tool": "text.chat", "params": {}}}]}]}, revision=1)
        ver2 = dinh_nghia.xuat_ban_draft(db, wf_id, created_by=uid, cong_cu=CC)
        db.get(Workflow, wf_id).published_version_id = ver2.id
        db.commit(); ver2_id = ver2.id
    finally:
        db.close()

    moi = _chay_lai(a, token_a, cu["id"], "b").json()
    assert moi["version_id"] == cu["version_id"] != ver2_id
    assert sorted(n["node_id"] for n in moi["nodes"]) == ["a", "b"]


# ── 2. Tái dụng KHÔNG tính tiền lần hai ──────────────────────────────────────

def test_node_tai_dung_giu_NGUYEN_output_ref_va_cost_credit_0(api):  # noqa: F811
    a, token_a, _, _ = api
    cu = _chay(a, token_a, _publish2(_uid(EMAIL))).json()["id"]
    _xong(cu, "a", gia=3, ra={"content": "artifact://abc"})
    _xong(cu, "b", gia=3)

    moi = _chay_lai(a, token_a, cu, "b").json()["id"]
    sao = _anh(moi, "a")
    assert sao["status"] == "SUCCEEDED"
    # Tham chiếu artifact giữ NGUYÊN — ⛔ không chép byte, không sinh id mới.
    assert sao["output_ref"]["content"] == "artifact://abc"
    # 🔴 ⛔ KHÔNG tính tiền lần hai.
    assert sao["cost"] == 0
    # Node được chọn (và hậu duệ) KHÔNG được sao — nó phải chạy lại thật.
    assert _anh(moi, "b") is None


def test_chay_lai_tu_node_DAU_thi_khong_sao_gi(api):  # noqa: F811
    a, token_a, _, _ = api
    cu = _chay(a, token_a, _publish2(_uid(EMAIL))).json()["id"]
    _xong(cu, "a", gia=3)
    _xong(cu, "b", gia=3)
    moi = _chay_lai(a, token_a, cu, "a").json()["id"]
    assert _anh(moi, "a") is None and _anh(moi, "b") is None


# ── 3. ⭐ ĐỐI CHỨNG: phép đo phân biệt được "tái dụng" với "chạy lại tất" ────

def test_khong_tai_dung_duoc_thi_ton_DUNG_BANG_mot_run_moi(api):  # noqa: F811
    """Ba lượt chạy, ba con số, đo tới lúc KẾT SỔ.

    | lượt | tái dụng | chi phí thật |
    |---|---|---|
    | run mới tinh | - | 6 |
    | chạy lại từ `a` (không tái dụng được gì) | {} | **6** — bằng run mới |
    | chạy lại từ `b` (tái dụng `a`) | {a} | **3** |

    Nếu hai dòng cuối bằng nhau thì phép đo không nói được gì; nếu dòng giữa
    nhỏ hơn 6 thì có việc được cho không.
    """
    a, token_a, _, _ = api
    # Ba lượt chạy × 6 credit ⇒ nạp rộng tay, để không phép nào chết vì hết tiền.
    wf = _publish2(_uid(EMAIL), credit_cap=500)

    # (1) run MỚI TINH chạy hết.
    tuoi = _chay(a, token_a, wf).json()["id"]
    _xong(tuoi, "a", gia=3); _xong(tuoi, "b", gia=3)
    gia_run_moi = _ket_thuc(tuoi)

    # (2) chạy lại từ `a` — hậu duệ của `a` là CẢ đồ thị ⇒ không tái dụng gì.
    goc = _chay(a, token_a, wf).json()["id"]
    _xong(goc, "a", gia=3); _xong(goc, "b", gia=3); _ket_thuc(goc)
    lai_het = _chay_lai(a, token_a, goc, "a").json()["id"]
    _xong(lai_het, "a", gia=3); _xong(lai_het, "b", gia=3)
    gia_lai_het = _ket_thuc(lai_het)

    # (3) chạy lại từ `b` — tái dụng `a`.
    goc2 = _chay(a, token_a, wf).json()["id"]
    _xong(goc2, "a", gia=3); _xong(goc2, "b", gia=3); _ket_thuc(goc2)
    lai_mot = _chay_lai(a, token_a, goc2, "b").json()["id"]
    _xong(lai_mot, "b", gia=3)
    gia_lai_mot = _ket_thuc(lai_mot)

    assert gia_run_moi == 6
    assert gia_lai_het == gia_run_moi       # ⭐ khong tai dung => ton y het
    assert gia_lai_mot == 3                 # tai dung `a` => khong tra lan hai
    assert gia_lai_mot < gia_lai_het        # ... va phep do PHAN BIET duoc


# ── 4. Ranh giới ─────────────────────────────────────────────────────────────

def test_bam_hai_lan_cung_khoa_KHONG_tao_hai_run(api):  # noqa: F811
    """Cửa này tiêu tiền ⇒ cùng luật `Idempotency-Key` với cửa tạo run."""
    a, token_a, _, _ = api
    cu = _chay(a, token_a, _publish2(_uid(EMAIL))).json()["id"]
    _xong(cu, "a", gia=3)
    khoa = f"t3454-{uuid.uuid4().hex}"
    truoc = _dem_hold()
    r1 = _chay_lai(a, token_a, cu, "b", khoa=khoa)
    r2 = _chay_lai(a, token_a, cu, "b", khoa=khoa)
    assert (r1.status_code, r2.status_code) == (201, 200)
    assert r1.json()["id"] == r2.json()["id"]
    assert _dem_hold() == truoc + 1        # ⛔ KHONG giu tien lan hai


def test_thieu_idempotency_key_tra_400(api):  # noqa: F811
    a, token_a, _, _ = api
    cu = _chay(a, token_a, _publish2(_uid(EMAIL))).json()["id"]
    r = a.post(f"/agent/api/v3/runs/{cu}/chay-lai-tu/b",
               headers={"X-CSRF-Token": token_a}, json={})
    assert r.status_code == 400
    assert r.json()["detail"]["ma"] == "thieu_idempotency_key"


def test_node_khong_co_trong_do_thi_tra_404(api):  # noqa: F811
    a, token_a, _, _ = api
    cu = _chay(a, token_a, _publish2(_uid(EMAIL))).json()["id"]
    r = _chay_lai(a, token_a, cu, "khong-ton-tai")
    assert r.status_code == 404
    assert r.json()["detail"]["ma"] == "node_khong_ton_tai"


def test_run_cua_nguoi_khac_tra_404(api):  # noqa: F811
    a, token_a, b, token_b = api
    cu = _chay(a, token_a, _publish2(_uid(EMAIL))).json()["id"]
    assert _chay_lai(b, token_b, cu, "b").status_code == 404
    assert _chay_lai(a, token_a, cu, "b").status_code == 201
