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
