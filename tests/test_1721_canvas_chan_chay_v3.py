"""wf-chan Defect A — chặn "Chạy" trên Canvas v2 khi workflow đã có `WorkflowDraft`.

## Vì sao cần bộ kiểm riêng

`c0db75dd` để Canvas lưu qua `/agent/api/v3/workflows` (bảng `workflow` /
`workflow_draft`, xem `apps/agent/routes/drafts_v3.py`), nhưng nút "Chạy" trên
giao diện vẫn gọi hai route v2 cũ — `POST /agent/api/workflows/{id}/validate`
("Kiểm tra chi phí", `apps/agent/routes/library.py`) và
`POST /agent/api/workflows/{id}/runs` (`apps/agent/routes/runs.py`) — và cả hai
đọc bảng v2 `agent_workflows` qua `platform_core.agent.workflows.get_owned`.

Hai hình dạng lỗi khác nhau tuỳ `workflow_id` có mặt ở đâu:

    chỉ có ở v3 (workflow mới dựng
    trên Canvas hôm nay)          -> `get_owned` 404 "Không tìm thấy workflow."
                                      dù workflow đó CÓ THẬT
    có ở CẢ HAI bảng (đã di trú
    qua `di_tru_m1.py`, CÙNG id)  -> `get_owned` tìm thấy hàng v2 và CHẠY
                                      ĐƯỢC — nhưng nội dung v2 đó có thể đã CŨ
                                      so với draft v3 người dùng đang sửa

Chốt của chủ dự án (22/09): chặn gọn ở đường v2 bằng một 503 rõ ràng, chờ
Workflow V2 engine (`phien/wf-v2`) thay cả hai đường. `_chan_neu_dang_nang_cap_v3`
(`apps/agent/routes/_shared.py`) là nơi DUY NHẤT canh việc đó, dùng chung bởi cả
`validate` lẫn `runs` — thiếu vế "dùng chung" thì một trong hai đường có thể
lệch khỏi đường kia.

## Ba mệnh đề tệp này canh, và một vế đối chứng bắt buộc

1. Workflow **chỉ tồn tại ở v3** ⇒ 503 rõ ràng, không phải 404 "không tìm thấy"
   như thể nó chưa từng có, trên cả `validate` lẫn `runs`.
2. Workflow **đã di trú** (có hàng ở CẢ `agent_workflows` lẫn `workflow_draft`,
   cùng `id`) ⇒ vẫn 503 trên cả hai — không được chạy nội dung v2 có thể đã cũ.
3. Workflow **v2 thuần, không có draft** ⇒ hành vi KHÔNG ĐỔI (vế đối chứng bắt
   buộc theo bài học Đợt 4–5: không có nó, một bản vá chặn *mọi* workflow cũng
   làm hai bài trên xanh).
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from platform_core.agent.workflows import plan_to_canvas


def _plan():
    # `text.prompt_package` la mot tool VAN CON, dung nhu `test_97` da doi sau
    # khi `text.script` bi go (Q109). Y dinh khong doi: mot buoc, sinh van ban.
    return {"version": 1, "goal": "Kiểm thử chặn chạy v3", "budget_max_credit": 50,
            "steps": [{"id": "s1", "tool": "text.prompt_package", "after": [],
                       "fanout": 1, "max_retry": 0, "on_fail": "retry_same",
                       "verify": None,
                       "params": {"title": "Một tiêu đề", "story": "Một câu chuyện."}}]}


def _csrf(html: str) -> str:
    match = re.search(r'data-csrf-token="([^"]+)"', html)
    assert match
    return match.group(1)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    for email in ("chan-v3-a@example.com", "chan-v3-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123", is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "chan-v3-test-session", "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver", follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={"username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/agent/canvas"}).status_code == 200
        canvas = client.get("/agent/canvas")
        return client, _csrf(canvas.text)

    a, token_a = login("chan-v3-a@example.com")
    b, token_b = login("chan-v3-b@example.com")
    yield a, token_a, b, token_b
    a.close(); b.close(); dbmod.reset_engine()


def _user_id(email: str) -> str:
    import platform_core.db as dbmod
    from platform_core.models import User
    db = next(dbmod.get_session())
    try:
        return db.query(User).filter_by(email=email).one().id
    finally:
        db.close()


def _create_v2(client, token, *, name="Workflow v2"):
    return client.post("/agent/api/workflows", headers={"X-CSRF-Token": token},
                       json={"name": name, "canvas": plan_to_canvas(_plan())})


def _v3_do_thi(n: int = 1) -> dict:
    return {"version": 3, "goal": "g", "budget_max_credit": 0,
            "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "", "edges": [],
                       "nodes": [{"id": f"n{i}", "type": "tool"}
                                 for i in range(n)]}]}


def _make_v3_only(owner_id: str) -> str:
    """Workflow chỉ tồn tại ở v3: có `Workflow` + `WorkflowDraft`, KHÔNG có
    `AgentWorkflow` — hệt một workflow người dùng mới dựng trên Canvas hôm nay,
    chưa từng chạm đường v2."""
    import platform_core.db as dbmod
    from platform_core.workflow import dinh_nghia
    db = next(dbmod.get_session())
    try:
        wf = dinh_nghia.tao_workflow(db, owner_id=owner_id, name="v3 only")
        dinh_nghia.luu_draft(db, wf.id, document=_v3_do_thi(), revision=0)
        db.commit()
        return wf.id
    finally:
        db.close()


def _them_draft_v3_cung_id(workflow_id: str, owner_id: str) -> None:
    """Mô phỏng kết quả của `di_tru_m1.chuyen()`: một `Workflow` + một
    `WorkflowDraft` mang CÙNG `id` với một `AgentWorkflow` đã có sẵn — đúng hình
    dạng của một workflow **đã di trú**."""
    import platform_core.db as dbmod
    from platform_core.models import Workflow, WorkflowDraft
    db = next(dbmod.get_session())
    try:
        db.add(Workflow(id=workflow_id, owner_id=owner_id, name="đã di trú"))
        db.add(WorkflowDraft(workflow_id=workflow_id, document=_v3_do_thi(),
                             revision=1))
        db.commit()
    finally:
        db.close()


_THONG_DIEP = ("Chạy workflow trên Canvas đang được nâng cấp sang runtime mới. "
              "Bản nháp của bạn vẫn được lưu an toàn.")


# ── 1. Workflow chỉ tồn tại ở v3 ─────────────────────────────────────────────

def _so_agent_run() -> int:
    import platform_core.db as dbmod
    from platform_core.models import AgentRun
    db = next(dbmod.get_session())
    try:
        return db.query(AgentRun).count()
    finally:
        db.close()


def test_v3_only_bi_chan_tren_ca_validate_va_runs(api):
    a, token_a, *_ = api
    owner_id = _user_id("chan-v3-a@example.com")
    wid = _make_v3_only(owner_id)

    validated = a.post(f"/agent/api/workflows/{wid}/validate",
                       headers={"X-CSRF-Token": token_a}, json={})
    assert validated.status_code == 503, validated.text
    assert validated.json()["detail"] == _THONG_DIEP

    run = a.post(f"/agent/api/workflows/{wid}/runs",
                 headers={"X-CSRF-Token": token_a}, json={})
    assert run.status_code == 503, run.text
    assert run.json()["detail"] == _THONG_DIEP
    # 🔴 Không chỉ mã lỗi đúng: một `AgentRun` mồ côi được tạo ra dù bị chặn
    #    sẽ nằm đó chờ điều phối nhặt lên và chạy — đúng thứ Defect A phải
    #    ngăn. `_chan_neu_dang_nang_cap_v3` raise TRƯỚC `_prepare_run`, nên
    #    không có gì ghi vào CSDL để nhặt.
    assert _so_agent_run() == 0


def test_v3_only_cua_NGUOI_KHAC_van_404_khong_lo_su_ton_tai(api):
    """⛔ `_chan_neu_dang_nang_cap_v3` lọc theo chủ NGAY TẠI CHỖ nó tra
    `WorkflowDraft` — không hoãn việc đó cho `get_owned` phía sau. Không có bài
    này, một bản vá tra thẳng `WorkflowDraft` theo `workflow_id` (bỏ qua chủ sở
    hữu) vẫn làm bài trên xanh, nhưng nó biến 503 thành một cách để một người lạ
    dò xem `workflow_id` của người khác có tồn tại hay không. Cả hai đường —
    `validate` LẪN `runs` — phải giữ đúng 404, không chỉ một trong hai."""
    a, token_a, b, token_b = api
    owner_id = _user_id("chan-v3-a@example.com")
    wid = _make_v3_only(owner_id)

    foreign_validate = b.post(f"/agent/api/workflows/{wid}/validate",
                              headers={"X-CSRF-Token": token_b}, json={})
    assert foreign_validate.status_code == 404
    assert foreign_validate.json()["detail"] != _THONG_DIEP

    foreign_runs = b.post(f"/agent/api/workflows/{wid}/runs",
                          headers={"X-CSRF-Token": token_b}, json={})
    assert foreign_runs.status_code == 404
    assert foreign_runs.json()["detail"] != _THONG_DIEP


# ── 2. Workflow đã di trú: có mặt ở CẢ HAI bảng ─────────────────────────────

def test_da_di_tru_bi_chan_tren_ca_validate_va_runs(api):
    a, token_a, *_ = api
    owner_id = _user_id("chan-v3-a@example.com")
    created = _create_v2(a, token_a, name="đã di trú").json()
    wid = created["id"]
    _them_draft_v3_cung_id(wid, owner_id)

    validated = a.post(f"/agent/api/workflows/{wid}/validate", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'}, json={})
    assert validated.status_code == 503, validated.text
    assert validated.json()["detail"] == _THONG_DIEP

    run = a.post(f"/agent/api/workflows/{wid}/runs", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'}, json={})
    assert run.status_code == 503, run.text
    assert run.json()["detail"] == _THONG_DIEP
    assert _so_agent_run() == 0


# ── 3. Đối chứng: workflow v2 thuần, KHÔNG có draft ─────────────────────────

def test_v2_THUAN_khong_co_draft_thi_hanh_vi_KHONG_DOI(api):
    """Vế đối chứng bắt buộc. Không có bài này, một bản vá chặn *mọi* workflow
    (kể cả những cái chưa từng chạm Canvas v3) cũng làm hai bài trên xanh — và
    không ai chạy được workflow nào nữa."""
    a, token_a, *_ = api
    created = _create_v2(a, token_a, name="v2 thuần").json()
    wid = created["id"]

    validated = a.post(f"/agent/api/workflows/{wid}/validate", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'}, json={})
    assert validated.status_code == 200, validated.text
    revision = validated.json()["revision"]

    run = a.post(f"/agent/api/workflows/{wid}/runs", headers={
        "X-CSRF-Token": token_a, "If-Match": f'"{revision}"'}, json={})
    assert run.status_code == 201, run.text
    assert run.json()["status"] == "awaiting_approval"
