"""SSE cho MỘT run đang chạy — `GET /agent/api/v3/runs/{id}/su-kien` (P9 task 1,
spec §14, plan `2026-09-24-wf-v2-MASTER.md` §4 P9).

## Ba mệnh đề tệp này canh

1. **Giao thức đúng**: `Content-Type: text/event-stream`, mỗi khung có `id:`
   (dùng cho `Last-Event-ID`) và `event: run` mang JSON cùng hình dạng với
   `GET /runs/{id}` (không phải một hợp đồng thứ hai).
2. **Sự kiện MỚI tới, không cần poll lại**: một `workflow_event` ghi giữa lúc
   luồng đang mở phải xuất hiện ở khung KẾ TIẾP mà không cần mở kết nối mới.
3. **`Last-Event-ID` thắng `?sau=`**: nối lại bằng header đó phải tiếp đúng
   chỗ đã dừng, không phát lại từ đầu và không nhảy quá.
4. Run kết thúc ⇒ luồng ĐÓNG (không treo tới mốc 90 s) — phép kiểm này canh
   luồng không bao giờ chạy quá vài giây, tự nó là bằng chứng.
"""
from __future__ import annotations

import json
import re
import threading
import uuid

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
                       f"sqlite:///{(tmp_path / 'v3sse.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email="v3sse-a@example.com", password="Strong-pass-123",
                   is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "v3sse-test-session",
                          "LTT_ADMIN_USERNAME": "",
                          "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "v3sse-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/agent/canvas"}).status_code == 200
    yield client, _csrf(client.get("/agent/canvas").text)
    client.close(); dbmod.reset_engine()


def _uid(email: str) -> str:
    import platform_core.db as dbmod
    from platform_core.models import User
    db = next(dbmod.get_session())
    try:
        return db.query(User).filter_by(email=email).one().id
    finally:
        db.close()


def _publish(owner_id: str) -> str:
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
        credit.nap(db, owner_id, 500, note="test")
        db.commit()
        return wf.id
    finally:
        db.close()


def _doc_khung(text: str) -> list[dict]:
    """Cắt thân `event stream` thành các gói `{event, id, data}`.

    Thứ tự dòng trong MỘT khung không quan trọng ("id:" có thể đứng trước
    hay sau "event:") — hàm này gom mọi dòng cho tới khi gặp dòng RỖNG (ranh
    giới `\\n\\n` của SSE), rồi mới đẩy khung vào kết quả.
    """
    ra: list[dict] = []
    hien: dict = {}
    for line in text.splitlines():
        if line == "":
            if hien:
                ra.append(hien)
            hien = {}
            continue
        if line.startswith("event: "):
            hien["event"] = line[len("event: "):]
        elif line.startswith("id: "):
            hien["id"] = int(line[len("id: "):])
        elif line.startswith("data: "):
            hien["data"] = line[len("data: "):]
    if hien:
        ra.append(hien)
    return ra


#: ⚠️ `starlette.testclient.TestClient` (khuôn `httpx` cũ, cảnh báo deprecated
#: khi chạy) KHÔNG giao từng khung SSE cho client theo thời gian thực: đo bằng
#: một app FastAPI tối giản 3 khung cách nhau 1 s, `client.stream(...).iter_lines()`
#: chỉ trả dòng ĐẦU TIÊN sau ~3,03 s — tức toàn bộ response bị GOM lại tới khi
#: generator phía SERVER chạy xong rồi mới phát một lần cho client. Vì vậy hai
#: phép kiểm dưới đây KHÔNG cố quan sát "khung tới real-time" qua client; chúng
#: dùng một THREAD GHI DB với độ trễ thật để ép generator phía SERVER (chạy
#: thật, `await asyncio.sleep` thật) đi qua nhiều nhịp TRƯỚC khi tự đóng ở
#: trạng thái kết thúc — rồi đọc lại TOÀN BỘ thân response đã gom, và kiểm thứ
#: tự/nội dung từng khung đã được server phát ra dọc theo thời gian đó.
def _ghi_tre(fn, do_tre_s: float) -> threading.Thread:
    def _chay():
        import time
        time.sleep(do_tre_s)
        fn()
    t = threading.Thread(target=_chay, daemon=True)
    t.start()
    return t


def test_sse_giao_thuc_va_nhan_su_kien_moi_giua_luong(api):
    """Đỏ trước 24/09: route chưa tồn tại ⇒ 404. Xanh sau khi thêm route."""
    client, token = api
    owner = _uid("v3sse-a@example.com")
    wf_id = _publish(owner)
    run = client.post(f"/agent/api/v3/workflows/{wf_id}/runs",
                      headers={"X-CSRF-Token": token,
                               "Idempotency-Key": f"sse-{uuid.uuid4().hex}"},
                      json={}).json()
    run_id = run["id"]
    assert run["status"] not in ("SUCCEEDED", "FAILED", "CANCELLED",
                                 "SYSTEM_FAILURE", "TIMED_OUT")

    import platform_core.db as dbmod
    from platform_core.workflow import may_trang_thai, su_kien

    def _ghi_su_kien_moi():
        db2 = next(dbmod.get_session())
        su_kien.ghi(db2, run_id, "NodeResumed", node_id="a",
                   du_lieu={"nhip": 1})
        db2.commit(); db2.close()

    def _ket_thuc_run():
        db3 = next(dbmod.get_session())
        assert may_trang_thai.chuyen_run(db3, run_id, sang="RUNNING",
                                         ly_do="test") is True
        assert may_trang_thai.chuyen_run(db3, run_id, sang="SUCCEEDED",
                                         ly_do="test") is True
        db3.commit(); db3.close()

    # Nhịp quét server là 1 s (`_SSE_NHIP_S`) — hẹn hai việc ở hai nhịp KHÁC
    # nhau để chắc chắn chúng rơi vào hai khung `event: run` riêng biệt.
    _ghi_tre(_ghi_su_kien_moi, 1.3)
    _ghi_tre(_ket_thuc_run, 2.6)

    r = client.get(f"/agent/api/v3/runs/{run_id}/su-kien", timeout=15)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    khung = _doc_khung(r.text)
    assert [k["event"] for k in khung[-1:]] == ["dong"], (
       "luong phai tu dong khi run vao trang thai ket thuc")
    goi_khung = [json.loads(k["data"]) for k in khung if k.get("event") == "run"]
    assert len(goi_khung) >= 3, (
       "can it nhat 3 nhip (truoc su_kien moi, sau su_kien moi, luc ket thuc)")

    goi1 = goi_khung[0]
    assert goi1["id"] == run_id and goi1["seq_cuoi"] == 1
    assert any(n["node_id"] == "a" and n["status"] == "PENDING"
              for n in goi1["nodes"])

    # Một khung SAU lúc _ghi_su_kien_moi() phải mang đúng sự kiện đó, và
    # seq_cuoi của nó phải TĂNG — không phát lại NodeResumed ở các khung sau.
    khung_co_su_kien_moi = [g for g in goi_khung
                            if any(e["loai"] == "NodeResumed"
                                   for e in g["su_kien"])]
    assert len(khung_co_su_kien_moi) == 1, (
       "NodeResumed phai xuat hien DUNG MOT lan, o khung no thuc su xay ra")
    assert khung_co_su_kien_moi[0]["seq_cuoi"] == 2

    goi_cuoi = goi_khung[-1]
    assert goi_cuoi["status"] == "SUCCEEDED"


def test_sse_last_event_id_thang_sau_khi_noi_lai(api):
    """`Last-Event-ID` (client tự gắn khi `EventSource` nối lại) phải THẮNG
    `?sau=` của lần connect đầu — nếu không, mỗi lần máy chủ tự đóng ở mốc 90 s
    sẽ làm trình duyệt phát lại TOÀN BỘ lịch sử từ đầu."""
    client, token = api
    owner = _uid("v3sse-a@example.com")
    wf_id = _publish(owner)
    run = client.post(f"/agent/api/v3/workflows/{wf_id}/runs",
                      headers={"X-CSRF-Token": token,
                               "Idempotency-Key": f"sse2-{uuid.uuid4().hex}"},
                      json={}).json()
    run_id = run["id"]

    import platform_core.db as dbmod
    from platform_core.workflow import may_trang_thai

    def _ket_thuc_run():
        db2 = next(dbmod.get_session())
        assert may_trang_thai.chuyen_run(db2, run_id, sang="RUNNING",
                                         ly_do="test") is True
        assert may_trang_thai.chuyen_run(db2, run_id, sang="SUCCEEDED",
                                         ly_do="test") is True
        db2.commit(); db2.close()

    _ghi_tre(_ket_thuc_run, 1.3)

    # `sau=0` NHƯNG có `Last-Event-ID: 1` ⇒ phải đọc tiếp từ seq 1 (bỏ qua
    # `WorkflowStarted`, seq=1), KHÔNG phát lại từ đầu.
    r = client.get(f"/agent/api/v3/runs/{run_id}/su-kien?sau=0",
                   headers={"Last-Event-ID": "1"}, timeout=15)
    assert r.status_code == 200
    khung = _doc_khung(r.text)
    goi_khung = [json.loads(k["data"]) for k in khung if k.get("event") == "run"]
    assert all(g["su_kien"] == [] or
              all(e["seq"] > 1 for e in g["su_kien"])
              for g in goi_khung), (
       "Last-Event-ID=1 phai bo qua WorkflowStarted (seq=1), khong phat lai no")
    assert khung[-1]["event"] == "dong"
    assert goi_khung[-1]["status"] == "SUCCEEDED"
