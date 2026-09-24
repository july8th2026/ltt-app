"""P10 HTTP API: CSRF, ownership, ETag, palette and import/export."""
from __future__ import annotations

import json
import io
import re

import pytest
from fastapi.testclient import TestClient

from platform_core.agent.plan_v1 import plan_to_canvas


def _plan():
    # `text.script` (tool cua `kichban`) DA GO o Q109. Thay bang mot tool VAN
    # CON va cung sinh van ban. Y dinh cua bo test khong doi.
    return {"version": 1, "goal": "Kiểm thử quy trình", "budget_max_credit": 50,
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
    for email in ("canvas-a@example.com", "canvas-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123", is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "workflow-api-test-session", "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver", follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={"username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/agent/canvas"}).status_code == 200
        canvas = client.get("/agent/canvas")
        return client, _csrf(canvas.text)

    a, token_a = login("canvas-a@example.com")
    b, token_b = login("canvas-b@example.com")
    yield a, token_a, b, token_b
    a.close(); b.close(); dbmod.reset_engine()


def _create(client, token, *, name="Workflow A"):
    return client.post("/agent/api/workflows", headers={"X-CSRF-Token": token},
                       json={"name": name, "canvas": plan_to_canvas(_plan())})


def test_crud_etag_stale_conflict_and_csrf(api):
    a, token, *_ = api
    assert a.post("/agent/api/workflows", json={}).status_code == 400
    created = _create(a, token)
    assert created.status_code == 201 and created.headers["etag"] == '"1"'
    workflow = created.json(); wid = workflow["id"]
    assert a.get("/agent/api/workflows").json()["items"][0]["id"] == wid
    assert a.get(f"/agent/api/workflows/{wid}").json()["canvas"] == workflow["canvas"]
    canvas = workflow["canvas"]; canvas["goal"] = "Mục tiêu đã sửa"
    saved = a.put(f"/agent/api/workflows/{wid}", headers={
        "X-CSRF-Token": token, "If-Match": '"1"'}, json={"name": "Mới", "canvas": canvas})
    assert saved.status_code == 200 and saved.json()["revision"] == 2
    stale = a.put(f"/agent/api/workflows/{wid}", headers={
        "X-CSRF-Token": token, "If-Match": '"1"'}, json={"name": "Cũ", "canvas": canvas})
    assert stale.status_code == 409


# 🗑️ ĐÓNG CỬA 24/09/2026 — plan wf-v2 P8 Task 5 (nợ §5) gỡ cả cụm v2
#    assistant / snapshots / shares / clone / export-import: chúng tra
#    `AgentWorkflow` id trong khi giao diện v3 cầm id bảng khác ⇒ 404 ngay
#    lần bấm đầu; production đo `shares` 0 bản ghi mọi thời đại, clone 0,
#    restore 0 (đối chứng `save` = 78). Sự vắng mặt được ghim bằng
#    `test_2934_dong_cua_cum_v2.py`, không bằng im lặng.
#    Bài đã gỡ: ownership_clone_archive_import_export (phần sở hữu chuyển
#    xuống `test_so_huu_tren_cua_CON_LAI`) · import_pathological ·
#    prompt_creates_editable_canvas · assistant_preview · snapshot_share.


def test_so_huu_tren_cua_CON_LAI(api):
    """Phần CÒN SỐNG của bài cũ: đọc/ghi workflow của người khác ⇒ 404,
    và `DELETE` không có cửa."""
    a, token_a, b, token_b = api
    row = _create(a, token_a).json(); wid = row["id"]
    assert b.get(f"/agent/api/workflows/{wid}").status_code == 404
    assert b.put(f"/agent/api/workflows/{wid}",
                 headers={"X-CSRF-Token": token_b},
                 json={"revision": 1, "name": "chiem",
                       "canvas": row["canvas"]}).status_code == 404
    assert a.delete(f"/agent/api/workflows/{wid}").status_code == 405


def test_validate_server_price_and_palette_are_authoritative(api):
    """Gia do MAY CHU chot, khong do trinh duyet gui len.

    ⛔ 23/09 (spec §17.4): `POST /agent/api/workflows/{id}/validate` da bi go
       cung luong chay v1. Menh de con lai — `/palette` khong duoc lech
       `discover_tools()`, va `/tools/{ten}/quote` la nguon gia duy nhat — VAN
       nguyen gia tri va VAN co duong that di qua (`workspace.py`), nen bai nay
       o lai; chi ba dong goi `/validate` bi cat.
    """
    a, token, *_ = api
    _create(a, token)
    palette = a.get("/agent/api/palette").json()
    # ⭐ Chốt "palette phơi ĐÚNG bộ tool discover được", không chốt bằng một con số
    #    cứng. Con số cứng ở đây từng là 21 và ngày 23/08/2026 nó đỏ vì HAI phiên
    #    làm việc song song, mỗi phiên thêm một tool (`image.ltt`, `text.chat`).
    #    Một số đếm mà nhiều phiên cùng tăng thì không phải bánh cóc: nó chỉ đỏ
    #    lặp lại vì cùng một lý do, và lần nào người sửa cũng chỉ gõ số mới —
    #    không ai phải nhìn xem tool mới là tool gì.
    #    Bánh cóc THẬT nằm ở `tests/test_88`: danh sách THEO TÊN, thêm tool mà
    #    quên khai là đỏ ở đó. Test này lo phần khác — palette và bộ discover
    #    không được lệch nhau — và đó là bất biến mạnh hơn một con số.
    from platform_core.agent.tools import discover_tools

    assert palette["version"] == 2
    assert {tool["name"] for tool in palette["tools"]} == set(discover_tools())
    assert palette["routing"]["mode"] == "platform_auto"
    # ⭐ Bản cũ: `len(model["providers"]) == 2` cho `seedance-2.0` — đúng khi có
    #    `byteplus` + `plenx`. AI CLEAN REBUILD V2 cho PLENX nghỉ (10/09/2026)
    #    nên con số thành 1; nhưng đổi `2` thành `1` chỉ dời điểm gãy sang lần
    #    sau, và mâu thuẫn với chính chú thích ba dòng trên đây — *"bất biến
    #    mạnh hơn một con số"*.
    #
    #    Bất biến thật: palette **không được lệch với registry**, và nó không
    #    được chào một nhà cung cấp đã nghỉ. Suy ra từ registry nên nó không trôi.
    from platform_core import providers as _pv

    # `providers` trong palette là **list dict** `{"id", "label"}` — nên phải
    # rút `id` ra trước khi so. Bản nháp viết `set(sd["providers"]) == mong or
    # {…} == mong` và nó **tự chặn mình**: `set()` trên dict ném `TypeError`
    # trước khi kịp tới `or`. Một cách viết "thử hai kiểu cho chắc" mà kiểu thứ
    # nhất nổ thì kiểu thứ hai không bao giờ được chạy.
    def _ids(ds):
        return {p["id"] if isinstance(p, dict) else p for p in ds}

    sd = next(m for m in palette["models"] if m["id"] == "seedance-2.0")
    mong = {p.id for p in _pv.REGISTRY.values()
            if p.is_active and any(x.id == "seedance-2.0" for x in p.models)}
    assert mong, "khong con nha cung cap song nao phuc vu seedance-2.0"
    assert _ids(sd["providers"]) == mong, (
        f"palette lech registry: {sd['providers']} vs {mong}")
    for m in palette["models"]:
        for pid in _ids(m["providers"]):
            assert not _pv.da_ngung(pid), (
                f"palette van chao {pid} cho {m['id']} - nha cung cap da nghi")
    assert all("price" not in tool and "params_schema" in tool for tool in palette["tools"])
    # ⛔ SUA 26/08 — bang nay khoa PALETTE CUA THOI TRUOC Q109.
    #
    #    Khang dinh cu doi BON tool chinh, trong do `text.generate` va
    #    `audio.generate` di cung `mediatools`/`kichban`. Va no doi
    #    `text.script` co `customer_visible is False` — tool do khong con.
    #
    # ⭐ Nay palette con HAI tool chinh, va do khong phai mot con so tuy tien:
    #    `apps/agent/routes/_shared.py` co mot bang `presentation` khai ro tool
    #    nao la `primary`. Phep kiem nay chot bang do, nen doi bang ma quen doi
    #    day se lam gate do — dung nhu no nen the.
    assert {tool["name"]: tool["label"] for tool in palette["tools"] if tool["primary"]} == {
        "image.generate": "Tạo hình ảnh", "video.generate": "Tạo video"}
    quote = a.post("/agent/api/tools/text.prompt_package/quote",
        headers={"X-CSRF-Token": token}, json={"params": {"title": "Tiêu đề hợp lệ", "story": "Nội dung."},
        "fanout": 2, "max_retry": 1})
    assert quote.status_code == 200
    assert quote.json()["maximum"] == quote.json()["unit"] * 4
    assert quote.json()["authoritative"] is True
    bad = a.post("/agent/api/tools/text.prompt_package/quote",
        headers={"X-CSRF-Token": token}, json={"params": {}})
    assert bad.status_code == 200 and bad.json()["valid"] is False
    assert bad.json()["maximum"] is None and bad.json()["authoritative"] is True


def test_canvas_preferences_are_validated_and_owned_per_user(api):
    a, token_a, b, _ = api
    assert a.get("/agent/api/preferences").json() == {
        "theme": "dark", "catalog_mode": "simple",
        "presentation_version": "creative-v1", "revision": 0}
    assert a.put("/agent/api/preferences", json={
        "theme": "dark", "catalog_mode": "advanced"}).status_code == 400
    saved = a.put("/agent/api/preferences", headers={"X-CSRF-Token": token_a}, json={
        "theme": "dark", "catalog_mode": "advanced"})
    assert saved.status_code == 200
    assert saved.json() == {"theme": "dark", "catalog_mode": "advanced",
                            "presentation_version": "creative-v1", "revision": 1}
    assert a.get("/agent/api/preferences").json()["theme"] == "dark"
    assert b.get("/agent/api/preferences").json()["theme"] == "dark"
    assert a.put("/agent/api/preferences", headers={"X-CSRF-Token": token_a}, json={
        "theme": "blue", "catalog_mode": "simple"}).status_code == 422


def test_canvas_uploaded_asset_has_owner_scoped_browser_preview(api):
    from PIL import Image
    a, token_a, b, _ = api
    output = io.BytesIO(); Image.new("RGB", (4, 3), "red").save(output, format="PNG")
    uploaded = a.post("/agent/api/assets", headers={"X-CSRF-Token": token_a},
        files={"file": ("owned.png", output.getvalue(), "image/png")})
    assert uploaded.status_code == 200
    payload = uploaded.json()
    assert payload["url"].startswith("/agent/api/assets/")
    preview = a.get(payload["url"])
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/png")
    assert "no-store" in preview.headers["cache-control"]
    assert preview.headers["accept-ranges"] == "bytes"
    partial = a.get(payload["url"], headers={"Range": "bytes=0-9"})
    assert partial.status_code == 206 and len(partial.content) == 10
    assert partial.headers["content-range"].startswith("bytes 0-9/")
    assert b.get(payload["url"]).status_code == 404


def test_api_round_trips_canvas_v2_without_losing_non_execution_content(api):
    a, token, *_ = api
    legacy = plan_to_canvas(_plan())
    canvas = {"version": 2, "goal": legacy["goal"],
              "budget_max_credit": legacy["budget_max_credit"],
              "active_page_id": "p1", "pages": [{"id": "p1", "name": "Trang chính",
                  "nodes": legacy["nodes"], "edges": legacy["edges"],
                  "viewport": legacy["viewport"],
                  "frames": [{"id": "f1", "name": "Nhóm 1", "node_ids": ["s1"]}],
                  "notes": [{"id": "n1", "text": "Ghi chú"}], "comments": []}]}
    canvas["pages"][0]["nodes"][0]["label"] = "Lời dẫn mở đầu"
    created = a.post("/agent/api/workflows", headers={"X-CSRF-Token": token},
                     json={"name": "Workflow v2", "canvas": canvas})
    assert created.status_code == 201 and created.json()["canvas"] == canvas
    wid = created.json()["id"]
    # ⛔ 23/09: buoc `/validate` o giua da bi go (§17.4). ⛔ 24/09: buoc
    #    `/export` cung bi go (P8 Task 5). Menh de cua bai KHONG doi — VONG
    #    TRON tao -> doc lai khong lam mat noi dung phi thi hanh — chi la ve
    #    "doc lai" nay di qua cua CON SONG.
    doc_lai = a.get(f"/agent/api/workflows/{wid}").json()
    assert doc_lai["canvas"] == canvas


def test_cua_quan_tri_chi_admin_vao_duoc_va_khong_lo_noi_dung_nguoi_dung(api):
    """Phan CON LAI cua bai kiem toan quan tri sau khi `AgentRun` bi go.

    🗑️ 23/09 (plan 01b Task 9): `_tao_agent_run()` + hai cua `/api/admin/runs*`
       da chet cung bang `agent_runs` — chung khong do gi khac ngoai bang do.

    ⭐ Hai menh de KHONG chet cung no, nen chung o lai day:
       1. cua quan tri la cua QUAN TRI — nguoi dung thuong phai nhan 404 (404
          chu khong phai 403: khong xac nhan su ton tai cua cua);
       2. no khong lo noi dung nguoi dung — khong `goal`, khong `plan`, khong
          email, khong id nguoi dung.
       Menh de 2 hom nay de dat hon truoc (phan hoi khong con doc bang nao cua
       nguoi dung), nhung no van la menh de that va van phai co nguoi canh.
    """
    a, _token_a, b, _token_b = api
    assert a.get("/agent/api/admin/metrics").status_code == 404

    import platform_core.db as dbmod
    from platform_core.models import User
    db = next(dbmod.get_session())
    db.query(User).filter_by(email="canvas-b@example.com").one().role = "admin"
    db.commit(); db.close()

    tra_loi = b.get("/agent/api/admin/metrics")
    assert tra_loi.status_code == 200
    so_lieu = tra_loi.json()
    assert "worker_wait_by_capability" in so_lieu
    assert so_lieu["live"]["planning_attempts"] >= 0
    # ⚠️ So theo KHOA JSON (`"goal":`), khong theo chuoi tran: `"plan"` tran
    #    khop ca `planning_attempts` — mot bo do bat nham chinh bo dem noi bo
    #    cua `planner`, va bai se do mai du khong co ro ri nao.
    for cam in ('"goal"', '"plan"', '"user_id"',
                "canvas-a@example.com", "canvas-b@example.com"):
        assert cam not in tra_loi.text, f"phan hoi quan tri lo `{cam}`"
