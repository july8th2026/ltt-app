"""Cửa v3 chạy run — `POST /agent/api/v3/workflows/{id}/runs`, `GET …/runs/{id}`.

## Ba mệnh đề tệp này canh

1. **Tạo run đi qua `tao_run`**, không có đường tắt: run sinh ra phải có
   `hold_id` (đã giữ tiền) và `status == "QUEUED"`. Một cửa tạo `WorkflowRun`
   thẳng bằng `db.add()` trông y hệt ở mức HTTP nhưng KHÔNG giữ tiền — và
   không ai phát hiện cho tới khi hoá đơn về.
2. **Ranh giới chủ sở hữu là 404**, cả lúc tạo lẫn lúc đọc — `403` xác nhận id
   đó có thật.
3. **Node chưa có ảnh chụp nào ⇒ `PENDING`**, không phải vắng mặt khỏi danh
   sách: giao diện vẽ đủ node của đồ thị ngay từ giây đầu, nếu không người dùng
   thấy các node "mọc dần" và tưởng đồ thị bị cắt.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from platform_core.workflow.cong_cu import CongCu

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 3)}


def _csrf(html: str) -> str:
    match = re.search(r'data-csrf-token="([^"]+)"', html)
    assert match
    return match.group(1)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'v3run.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    for email in ("v3run-a@example.com", "v3run-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                       is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "v3run-test-session",
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver",
                            follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"',
                          page.text).group(1)
        assert client.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/agent/canvas"}).status_code == 200
        return client, _csrf(client.get("/agent/canvas").text)

    a, token_a = login("v3run-a@example.com")
    b, token_b = login("v3run-b@example.com")
    yield a, token_a, b, token_b
    a.close(); b.close(); dbmod.reset_engine()


def _uid(email: str) -> str:
    import platform_core.db as dbmod
    from platform_core.models import User
    db = next(dbmod.get_session())
    try:
        return db.query(User).filter_by(email=email).one().id
    finally:
        db.close()


def _publish(owner_id: str, *, credit_cap: int = 500) -> str:
    """Một workflow ĐÃ PUBLISH của `owner_id`, và chủ có đủ tiền."""
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.workflow import dinh_nghia
    db = next(dbmod.get_session())
    try:
        wf = dinh_nghia.tao_workflow(db, owner_id=owner_id, name="w")
        doc = {"version": 3, "goal": "", "budget_max_credit": 0,
               "active_page_id": "p1",
               "pages": [{"id": "p1", "name": "", "edges": [], "nodes": [
                   {"id": "a", "type": "tool", "position": {"x": 0, "y": 0},
                    "data": {"tool": "text.chat", "params": {}}}]}]}
        dinh_nghia.luu_draft(db, wf.id, document=doc, revision=0)
        ver = dinh_nghia.xuat_ban_draft(db, wf.id, created_by=owner_id,
                                        cong_cu=CC)
        wf.published_version_id = ver.id
        # `credit_cap == 0` ⇒ KHÔNG nạp: `nap(…, 0)` là một bút toán rỗng và
        # một số đường từ chối nó. Tài khoản chưa nạp = số dư 0, đúng thứ
        # `test_thieu_credit_tra_402_chu_khong_500` cần.
        if credit_cap:
            credit.nap(db, owner_id, credit_cap, note="test")
        db.commit()
        return wf.id
    finally:
        db.close()


def test_tao_run_di_qua_tao_run_nen_CO_giu_tien(api):
    import platform_core.db as dbmod
    from platform_core.models import WorkflowRun
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))

    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token_a}, json={})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "QUEUED" and body["credit_max"] == 3
    assert [n["node_id"] for n in body["nodes"]] == ["a"]
    assert body["nodes"][0]["status"] == "PENDING"
    assert body["seq_cuoi"] >= 1

    db = next(dbmod.get_session())
    try:
        run = db.get(WorkflowRun, body["id"])
        assert run.hold_id, "run khong giu tien => cua nay khong qua tao_run"
    finally:
        db.close()


def test_workflow_cua_nguoi_khac_tra_404_chu_khong_403(api):
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-b@example.com"))
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token_a}, json={})
    assert r.status_code == 404


def test_workflow_chua_publish_tra_422_co_ma(api):
    import platform_core.db as dbmod
    from platform_core.workflow import dinh_nghia
    a, token_a, _, _ = api
    db = next(dbmod.get_session())
    try:
        wf = dinh_nghia.tao_workflow(db, owner_id=_uid("v3run-a@example.com"),
                                     name="chua publish")
        db.commit(); wf_id = wf.id
    finally:
        db.close()
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token_a}, json={})
    assert r.status_code == 422
    assert r.json()["detail"]["ma"] == "chua_publish"


def test_thieu_credit_tra_402_chu_khong_500(api):
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"), credit_cap=0)
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token_a}, json={})
    assert r.status_code == 402
    assert r.json()["detail"]["ma"] == "thieu_credit"


def test_doc_run_tra_node_va_su_kien_tang_dan(api):
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    run_id = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
                    headers={"X-CSRF-Token": token_a}, json={}).json()["id"]

    full = a.get(f"/agent/api/v3/runs/{run_id}").json()
    assert full["su_kien"] and full["su_kien"][0]["loai"] == "WorkflowStarted"
    assert full["seq_cuoi"] == full["su_kien"][-1]["seq"]

    # `sau=` là một BỘ LỌC, không phải một trang: xin sau seq cuối ⇒ rỗng,
    # nhưng `seq_cuoi` vẫn phải nói đúng vị trí hiện tại.
    tiep = a.get(f"/agent/api/v3/runs/{run_id}",
                 params={"sau": full["seq_cuoi"]}).json()
    assert tiep["su_kien"] == []
    assert tiep["seq_cuoi"] == full["seq_cuoi"]
    assert tiep["nodes"] == full["nodes"]


def test_doc_run_cua_nguoi_khac_tra_404(api):
    a, token_a, b, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    run_id = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
                    headers={"X-CSRF-Token": token_a}, json={}).json()["id"]
    assert b.get(f"/agent/api/v3/runs/{run_id}").status_code == 404


# ── Fix round 1 (task-2-review.md) ──────────────────────────────────────────

def test_inputs_khong_phai_object_tra_422_khong_phai_500(api):
    """`{"inputs": [1, 2]}` — `dict(raw or {})` trên một list ném `TypeError`
    trước khi `tao_run` kịp chạy (Important #2). Đây là cửa tiêu tiền, một
    kiểu sai không được rơi xuống 500."""
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token_a}, json={"inputs": [1, 2]})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["ma"] == "inputs_khong_hop_le"


def test_inputs_la_chuoi_cung_tra_422_khong_phai_500(api):
    """`{"inputs": "abc"}` — `dict("abc")` ném `ValueError`, vế đối chứng
    của ca trên (một kiểu sai KHÁC vẫn phải qua cùng một cửa 422)."""
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token_a}, json={"inputs": "abc"})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["ma"] == "inputs_khong_hop_le"


def test_inputs_qua_lon_tra_422_co_ma(api):
    """`inputs` hợp lệ VỀ KIỂU nhưng vượt trần vẫn không được đi vào
    `WorkflowStarted.du_lieu` (sống 90 ngày) — Important #2, vế thứ hai.

    100_000 byte: dưới trần CHUNG của `AgentBodyLimitMiddleware` (128 KiB —
    nếu không request chết ở tầng middleware với 413, không phải 422 của
    route này) nhưng vượt trần RIÊNG của `inputs` (`_GIOI_HAN_INPUTS`, 64 KiB)."""
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token_a},
               json={"inputs": {"x": "a" * 100_000}})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["ma"] == "inputs_qua_lon"


def test_tran_inputs_dem_BYTE_chu_khong_dem_ky_tu_thoat(api):
    """Trần là BYTE, đúng như thông điệp lỗi hứa — không phải ký tự `\\uXXXX`.

    15_000 chữ "ă" = 30_010 byte UTF-8 (LỌT trần 64 KiB) nhưng
    `json.dumps(..., ensure_ascii=True)` nở thành 90_010 ký tự (VƯỢT trần).
    Đếm ký tự ⇒ khách viết tiếng Việt bị siết gắt gấp ~3 lần so với khách
    viết tiếng Anh, trên cùng một con số được quảng cáo.
    """
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    payload = {"x": "ă" * 15_000}
    assert len(json.dumps(payload).encode()) > 64 * 1024
    assert len(json.dumps(payload, ensure_ascii=False).encode()) < 64 * 1024
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token_a}, json={"inputs": payload})
    assert r.status_code == 201, r.text


def test_dong_co_chua_dang_ky_tra_503_co_ma_khong_phai_500(api, monkeypatch):
    """`chu_dong_co()` ném `RegistryError` khi không app nào khai
    `job_type workflow.dong_co` — sự cố cấu hình thật (`2d3e3c41`), phải là
    503 có mã, không phải 500 trơ (Minor #4, mục cuối)."""
    from platform_core.registry import RegistryError
    from platform_core.workflow import tao_run

    def _vo() -> str:
        raise RegistryError("khong app nao khai job_type workflow.dong_co")

    monkeypatch.setattr(tao_run, "chu_dong_co", _vo)
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    r = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
               headers={"X-CSRF-Token": token_a}, json={})
    assert r.status_code == 503, r.text
    assert r.json()["detail"]["ma"] == "dong_co_chua_san_sang"


def test_node_chua_co_anh_chup_bao_attempt_0_khong_phai_1(api):
    """`attempt: 1` trên một node CHƯA TỪNG chạy nói dối rằng nó đã thử một
    lượt (Minor #5) — `0` mới đúng."""
    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    run_id = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
                    headers={"X-CSRF-Token": token_a}, json={}).json()["id"]
    node = a.get(f"/agent/api/v3/runs/{run_id}").json()["nodes"][0]
    assert node["status"] == "PENDING"
    assert node["attempt"] == 0


def test_node_co_anh_chup_tra_dung_cost_attempt_job_error(api):
    """Important #3 — không phép kiểm nào trước đây đưa một node qua khỏi
    `PENDING`, nên nhánh `anh is not None` của `_nodes_json` (cost_credit,
    attempt, job_id, error) chưa hề được xác nhận. Đi qua đường THẬT
    (`may_trang_thai.chuyen_node`), không ghi tay `NodeRunSnapshot`."""
    import platform_core.db as dbmod
    from platform_core.workflow import may_trang_thai

    a, token_a, _, _ = api
    wf_id = _publish(_uid("v3run-a@example.com"))
    run_id = a.post(f"/agent/api/v3/workflows/{wf_id}/runs",
                    headers={"X-CSRF-Token": token_a}, json={}).json()["id"]

    db = next(dbmod.get_session())
    try:
        assert may_trang_thai.chuyen_node(db, run_id, "a", sang="READY",
                                          mo_ta="scheduler nhac node")
        assert may_trang_thai.chuyen_node(db, run_id, "a", sang="RUNNING",
                                          mo_ta="worker nhan job",
                                          job_id="job-abc", attempt_number=2)
        assert may_trang_thai.chuyen_node(
            db, run_id, "a", sang="FAILED", mo_ta="worker bao loi",
            error="vuot_tran_bao_gia", job_id="job-abc", attempt_number=2,
            cost_credit=7)
        db.commit()
    finally:
        db.close()

    nodes = a.get(f"/agent/api/v3/runs/{run_id}").json()["nodes"]
    node = next(n for n in nodes if n["node_id"] == "a")
    assert node["status"] == "FAILED"
    assert node["attempt"] == 2
    assert node["cost_credit"] == 7
    assert node["job_id"] == "job-abc"
    assert node["error"] == "vuot_tran_bao_gia"
