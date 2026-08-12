"""
H6 — cốt lõi vận hành: catalog công khai + SSO UX + login return-to.

Khoá hành vi (Q30):
- trang chủ `/` CÔNG KHAI: khách chưa đăng nhập vẫn xem được, chỉ hiện app
  `public=True`, KHÔNG hiện app nội bộ (demo/socialbot) và KHÔNG có sidebar;
- route app yêu cầu đăng nhập → 303 `/login?next=<path>`;
- `safe_next` chống open-redirect;
- đăng nhập xong quay lại đúng `next`;
- vỏ đã-đăng-nhập hiện số dư credit.
"""
from __future__ import annotations

import re
import io
import json

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    url = f"sqlite:///{(tmp_path / 'vh.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-h6")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver", follow_redirects=False)
    try:
        yield c
    finally:
        dbmod.reset_engine()


def _csrf(client, path):
    m = re.search(r'name="csrf_token" value="([^"]+)"', client.get(path).text)
    assert m
    return m.group(1)


# ── safe_next (chống open-redirect) ─────────────────────────────────────────────

def test_safe_next_chan_open_redirect():
    from server.auth.session import safe_next
    assert safe_next("/thumbnail") == "/thumbnail"
    assert safe_next("") == "/"
    assert safe_next("//evil.com") == "/"
    assert safe_next("https://evil.com") == "/"
    assert safe_next("http://evil") == "/"
    assert safe_next("/a\nb") == "/"
    assert safe_next("evil.com") == "/"          # không bắt đầu bằng /


def test_progress_bao_terminal_de_trang_tu_nap_action_va_artifact(client):
    import platform_core.db as dbmod
    from platform_core.models import JOB_DONE, JOB_RUNNING, Job
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        user = tao_nguoi_dung(db, email="job-progress@example.com",
                              password="matkhau-tot-12", is_verified=True)
        running = Job(user_id=user.id, app_slug="demo", job_type="demo.reverse",
                      status=JOB_RUNNING)
        done = Job(user_id=user.id, app_slug="demo", job_type="demo.reverse",
                   status=JOB_DONE, result={"text_key": "demo/result.txt"})
        db.add_all([running, done]); db.commit()
        running_id, done_id = running.id, done.id
    finally:
        try: next(gen)
        except StopIteration: pass

    token = _csrf(client, "/login")
    assert client.post("/login", data={"username": "job-progress@example.com",
                                        "password": "matkhau-tot-12",
                                        "csrf_token": token}).status_code == 303
    active = client.get(f"/jobs/{running_id}/progress")
    terminal = client.get(f"/jobs/{done_id}/progress")
    assert active.status_code == 200
    assert "X-LTT-Job-Terminal" not in active.headers
    assert terminal.status_code == 200
    assert terminal.headers["X-LTT-Job-Terminal"] == "1"


# ── Catalog công khai ───────────────────────────────────────────────────────────

def test_trang_chu_cong_khai_cho_khach(client):
    r = client.get("/")
    assert r.status_code == 200                    # KHÔNG đá về /login
    body = r.text
    assert "Tạo ảnh AI" in body                    # một entry point ảnh hiện
    assert "Tạo Thumbnail YouTube" not in body     # mode con không lặp card
    assert "Đăng nhập" in body and "Đăng ký" in body
    # App nội bộ (public=False) KHÔNG hiện cho khách:
    assert "Demo — kiểm tra" not in body
    assert "Đăng bài Facebook" not in body
    # Không có vỏ nội bộ (sidebar) cho khách:
    assert "Việc của tôi" not in body


def test_click_app_khi_chua_dang_nhap_deep_link_login(client):
    # Catalog trỏ vào shell Tạo ảnh AI; route Thumbnail cũ vẫn được test riêng.
    body = client.get("/").text
    assert "/login?next=/taoanh" in body
    assert "/login?next=/thumbnail" not in body


# ── require_login mang next ─────────────────────────────────────────────────────

def test_route_app_chua_dang_nhap_303_kem_next(client):
    r = client.get("/thumbnail")
    assert r.status_code == 303
    assert r.headers["location"] == "/login?next=/thumbnail"


# ── Đăng nhập quay lại đúng app + số dư credit ở vỏ ─────────────────────────────

def test_dang_nhap_quay_lai_app_va_hien_credit(client):
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="kh@example.com", password="matkhau-tot-12",
                           is_verified=True)
        credit.cap_tay(db, u.id, 30, by="admin"); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    tok = _csrf(client, "/login?next=/thumbnail")
    r = client.post("/login", data={"username": "kh@example.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": tok, "next": "/thumbnail"})
    assert r.status_code == 303
    assert r.headers["location"] == "/thumbnail"          # quay lại đúng app

    # Vỏ đã-đăng-nhập hiện số dư credit.
    home = client.get("/")
    assert home.status_code == 200
    assert "30 credit" in home.text
    assert "Việc của tôi" in home.text                    # user thấy sidebar


def _tao_va_dang_nhap(client, email, role="user"):
    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email=email, password="matkhau-tot-12",
                       is_verified=True, role=role); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    tok = _csrf(client, "/login")
    r = client.post("/login", data={"username": email,
                                    "password": "matkhau-tot-12",
                                    "csrf_token": tok})
    assert r.status_code == 303


# ── Vỏ hai tầng (H6.6): launcher + trang con theo ngữ cảnh ───────────────────────

def test_sidebar_launcher_mot_dong_moi_app(client):
    """Ở trang chủ: mỗi app MỘT dòng; trang con của app KHÔNG tràn ra sidebar."""
    _tao_va_dang_nhap(client, "u1@example.com")
    body = client.get("/").text
    assert "Đăng bài Facebook + TikTok" in body      # dòng app (tầng 1) hiện
    assert "Sheet TikTok" not in body                # trang con (tầng 2) ẩn
    assert "Manual TikTok" not in body


def test_sidebar_bung_trang_con_khi_trong_app(client):
    """Khi đang Ở TRONG một app nhiều trang, trang con của nó mới bung ra."""
    _tao_va_dang_nhap(client, "u2@example.com")
    r = client.get("/facebook", follow_redirects=False)
    assert r.status_code == 200
    assert "Sheet TikTok" in r.text                  # trang con bung ra
    assert "Manual TikTok" in r.text


def test_link_quan_tri_chi_hien_cho_admin(client):
    """Link '/admin/' chỉ hiện cho admin CSDL, ẩn với user thường."""
    _tao_va_dang_nhap(client, "normal@example.com")           # user thường
    home = client.get("/").text
    assert "/admin/" not in home
    _lt = re.search(r'name="csrf_token" value="([^"]+)"', home).group(1)
    client.post("/logout", data={"csrf_token": _lt})
    _tao_va_dang_nhap(client, "boss@example.com", role="admin")  # admin
    assert "/admin/" in client.get("/").text


def test_home_workspace_chi_hien_activity_va_running_job_cua_chu_so_huu(client):
    """H13: rail trang chu không được lộ hoạt động/job của người dùng khác."""
    import platform_core.db as dbmod
    from platform_core.models import JOB_QUEUED, Job
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        mine = tao_nguoi_dung(db, email="mine-home@example.com",
                              password="matkhau-tot-12", is_verified=True)
        other = tao_nguoi_dung(db, email="other-home@example.com",
                               password="matkhau-tot-12", is_verified=True)
        db.add(Job(user_id=mine.id, app_slug="thumbnail", job_type="thumbnail.generate",
                   status=JOB_QUEUED, progress=42, progress_msg="MINE_HOME_ACTIVITY"))
        db.add(Job(user_id=other.id, app_slug="thumbnail", job_type="thumbnail.generate",
                   status=JOB_QUEUED, progress=77, progress_msg="OTHER_PRIVATE_ACTIVITY"))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    _tao_va_dang_nhap(client, "workspace-view@example.com")
    # Đổi sang user có job trong phiên mới để kiểm owner-scope đúng người xem.
    _lt = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/").text).group(1)
    client.post("/logout", data={"csrf_token": _lt})
    tok = _csrf(client, "/login")
    client.post("/login", data={"username": "mine-home@example.com",
                                 "password": "matkhau-tot-12", "csrf_token": tok})
    body = client.get("/").text
    # H24: nhan tieng Anh lan giua trang tieng Viet la LOI da sua, khong phai
    # hop dong. Gio la chuoi tieng Viet, dich sang EN qua catalog.
    assert "Kho ứng dụng" in body and "Ứng dụng của tôi" in body
    assert "MINE_HOME_ACTIVITY" in body
    assert "OTHER_PRIVATE_ACTIVITY" not in body
    assert 'data-popular=' in body


def test_taovideo_studio_history_filter_va_owner_scope(client):
    """H13.taovideo: gallery/history chỉ đọc job của chủ sở hữu."""
    import platform_core.db as dbmod
    from platform_core.models import JOB_DONE, JOB_ERROR, Job
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        mine = tao_nguoi_dung(db, email="tv-mine@example.com", password="matkhau-tot-12", is_verified=True)
        other = tao_nguoi_dung(db, email="tv-other@example.com", password="matkhau-tot-12", is_verified=True)
        db.add(Job(user_id=mine.id, app_slug="taovideo", job_type="taovideo.generate", status=JOB_DONE,
                   params={"prompt":"PROMPT_CUA_TOI", "resolution":"720p", "duration":5, "aspect_ratio":"16:9"}))
        db.add(Job(user_id=other.id, app_slug="taovideo", job_type="taovideo.generate", status=JOB_ERROR,
                   params={"prompt":"PROMPT_NGUOI_KHAC"}))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    _tao_va_dang_nhap(client, "tv-view@example.com")
    token = _csrf(client, "/")
    client.post("/logout", data={"csrf_token": token})
    token = _csrf(client, "/login")
    client.post("/login", data={"username":"tv-mine@example.com", "password":"matkhau-tot-12", "csrf_token":token})
    body = client.get("/taovideo?status=done").text
    assert "PROMPT_CUA_TOI" in body and "PROMPT_NGUOI_KHAC" not in body
    assert "Lịch sử prompt" in body and "Tất cả" in body


def test_seedance_upscale_quote_va_confirm_chi_cho_video_cua_chu_so_huu(client):
    """H13.upscale: Seedance chỉ tạo Upscale job qua quote/confirm server-side.

    Giá, source key và ownership đều do server quyết định; browser không thể gửi
    một storage key của người khác hoặc tự hạ giá.
    """
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import JOB_DONE, Job
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        mine = tao_nguoi_dung(db, email="seed-up@example.com",
                              password="matkhau-tot-12", is_verified=True)
        other = tao_nguoi_dung(db, email="seed-other@example.com",
                               password="matkhau-tot-12", is_verified=True)
        credit.cap_tay(db, mine.id, 100, by="test")
        source = Job(user_id=mine.id, app_slug="taovideo", job_type="taovideo.generate",
                     status=JOB_DONE, params={"duration": 5},
                     result={"video_key": f"taovideo/{mine.id}/out.mp4", "duration": 5})
        foreign = Job(user_id=other.id, app_slug="taovideo", job_type="taovideo.generate",
                      status=JOB_DONE,
                      result={"video_key": f"taovideo/{other.id}/out.mp4", "duration": 5})
        db.add_all([source, foreign]); db.commit(); source_id, foreign_id = source.id, foreign.id
    finally:
        try: next(gen)
        except StopIteration: pass

    token = _csrf(client, "/login")
    logged = client.post("/login", data={"username": "seed-up@example.com",
                                         "password": "matkhau-tot-12", "csrf_token": token})
    assert logged.status_code == 303
    quote = client.post("/taovideo/upscale-quote",
                        data={"job_id": source_id, "target_height": "2160"})
    assert quote.status_code == 200 and quote.json()["ok"] is True
    assert quote.json()["target_height"] == 2160 and quote.json()["credit"] > 0
    assert client.post("/taovideo/upscale-quote", data={"job_id": foreign_id}).status_code == 404

    page_token = _csrf(client, "/taovideo")
    confirmed = client.post("/taovideo/upscale-confirm", data={
        "csrf_token": page_token, "job_id": source_id, "target_height": "2160",
        "preset": "quality", "codec": "hevc",
    })
    assert confirmed.status_code == 200 and confirmed.json()["ok"] is True
    gen = dbmod.get_session(); db = next(gen)
    try:
        child = db.get(Job, confirmed.json()["upscale_job_id"])
        assert child.user_id == mine.id and child.app_slug == "upscalevideo"
        assert child.job_type == "upscalevideo.render.quality"
        assert child.params["video_key"] == f"taovideo/{mine.id}/out.mp4"
        assert child.params["target_height"] == 2160 and child.params["preset"] == "quality"
    finally:
        try: next(gen)
        except StopIteration: pass


def test_upscale_cancel_owner_only_hoan_credit_dung_mot_lan(client):
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import CREDIT_REFUND, JOB_CANCELLED, CreditEntry, Job
    from platform_core.users import tao_nguoi_dung
    from apps.upscalevideo.service import submit_upscale_job
    from sqlalchemy import func, select

    gen = dbmod.get_session(); db = next(gen)
    try:
        mine = tao_nguoi_dung(db, email="up-cancel@example.com",
                              password="matkhau-tot-12", is_verified=True)
        other = tao_nguoi_dung(db, email="up-cancel-other@example.com",
                               password="matkhau-tot-12", is_verified=True)
        credit.cap_tay(db, mine.id, 100, by="test")
        credit.cap_tay(db, other.id, 100, by="test")
        own_job = submit_upscale_job(
            db, user_id=mine.id, video_key=f"upscalevideo/{mine.id}/in.mp4",
            duration_s=60, target_height=1080)
        foreign_job = submit_upscale_job(
            db, user_id=other.id, video_key=f"upscalevideo/{other.id}/in.mp4",
            duration_s=60, target_height=1080)
        assert own_job.job_type == "upscalevideo.render.fast"
        assert foreign_job.job_type == "upscalevideo.render.fast"
        db.commit(); own_id, foreign_id, mine_id = own_job.id, foreign_job.id, mine.id
        assert credit.so_du(db, mine_id) == 70
    finally:
        try: next(gen)
        except StopIteration: pass

    token = _csrf(client, "/login")
    assert client.post("/login", data={"username": "up-cancel@example.com",
                                        "password": "matkhau-tot-12",
                                        "csrf_token": token}).status_code == 303
    token = _csrf(client, "/upscalevideo")
    denied = client.post(f"/upscalevideo/jobs/{foreign_id}/cancel",
                         data={"csrf_token": token})
    assert denied.status_code == 404

    first = client.post(f"/upscalevideo/jobs/{own_id}/cancel",
                        data={"csrf_token": token})
    assert first.status_code == 303
    second = client.post(f"/upscalevideo/jobs/{own_id}/cancel",
                         data={"csrf_token": token})
    assert second.status_code == 303

    gen = dbmod.get_session(); db = next(gen)
    try:
        job = db.get(Job, own_id)
        refunds = db.execute(select(func.count()).select_from(CreditEntry).where(
            CreditEntry.job_id == own_id, CreditEntry.kind == CREDIT_REFUND)).scalar_one()
        assert job.status == JOB_CANCELLED
        assert credit.so_du(db, mine_id) == 100 and refunds == 1
    finally:
        try: next(gen)
        except StopIteration: pass


def test_upscale_compare_source_owner_range_va_missing(client, tmp_path):
    """UP3: source được chọn từ job đã kiểm owner, không nhận key từ URL."""
    import platform_core.db as dbmod
    from platform_core.models import JOB_DONE, Job
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung

    storage = LocalStorage(str(tmp_path / "upscale-source-store"))
    set_storage(storage)
    try:
        gen = dbmod.get_session(); db = next(gen)
        try:
            mine = tao_nguoi_dung(db, email="up-source@example.com",
                                  password="matkhau-tot-12", is_verified=True)
            other = tao_nguoi_dung(db, email="up-source-other@example.com",
                                   password="matkhau-tot-12", is_verified=True)
            direct_key = f"upscalevideo/{mine.id}/direct/input.mp4"
            seedance_key = f"taovideo/{mine.id}/seedance/output.mp4"
            storage.put(direct_key, io.BytesIO(b"DIRECT-VIDEO"), content_type="video/mp4")
            storage.put(seedance_key, io.BytesIO(b"SEEDANCE-VIDEO"), content_type="video/mp4")
            direct = Job(user_id=mine.id, app_slug="upscalevideo",
                         job_type="upscalevideo.upscale", status=JOB_DONE,
                         params={"video_key": direct_key})
            seedance = Job(user_id=mine.id, app_slug="upscalevideo",
                           job_type="upscalevideo.upscale", status=JOB_DONE,
                           params={"video_key": seedance_key})
            missing = Job(user_id=mine.id, app_slug="upscalevideo",
                          job_type="upscalevideo.upscale", status=JOB_DONE,
                          params={"video_key": f"taovideo/{mine.id}/missing.mp4"})
            foreign = Job(user_id=other.id, app_slug="upscalevideo",
                          job_type="upscalevideo.upscale", status=JOB_DONE,
                          params={"video_key": f"upscalevideo/{other.id}/private.mp4"})
            db.add_all([direct, seedance, missing, foreign]); db.commit()
            ids = direct.id, seedance.id, missing.id, foreign.id
        finally:
            try: next(gen)
            except StopIteration: pass

        token = _csrf(client, "/login")
        assert client.post("/login", data={"username": "up-source@example.com",
                                            "password": "matkhau-tot-12",
                                            "csrf_token": token}).status_code == 303
        direct_id, seedance_id, missing_id, foreign_id = ids
        ranged = client.get(f"/upscalevideo/jobs/{direct_id}/source",
                            headers={"Range": "bytes=0-5"})
        assert ranged.status_code == 206 and ranged.content == b"DIRECT"
        assert ranged.headers["content-range"] == "bytes 0-5/12"
        seedance_response = client.get(f"/upscalevideo/jobs/{seedance_id}/source")
        assert seedance_response.status_code == 200
        assert seedance_response.content == b"SEEDANCE-VIDEO"
        assert client.get(f"/upscalevideo/jobs/{foreign_id}/source").status_code == 404
        assert client.get(f"/upscalevideo/jobs/{missing_id}/source").status_code == 404
    finally:
        set_storage(None)


def test_upscale_batch_ba_job_atomic_dedupe_va_owner(client, tmp_path):
    """UP4: tối đa 3, hold nguyên tử, retry không trừ hai lần, key đúng owner."""
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import Job
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    from sqlalchemy import func, select

    storage = LocalStorage(str(tmp_path / "upscale-batch-store"))
    set_storage(storage)
    try:
        gen = dbmod.get_session(); db = next(gen)
        try:
            mine = tao_nguoi_dung(db, email="up-batch@example.com",
                                  password="matkhau-tot-12", is_verified=True)
            other = tao_nguoi_dung(db, email="up-batch-other@example.com",
                                   password="matkhau-tot-12", is_verified=True)
            credit.cap_tay(db, mine.id, 20, by="test")
            for i in range(6):
                storage.put(f"upscalevideo/{mine.id}/uploads/{i}.mp4",
                            io.BytesIO(f"video-{i}".encode()), content_type="video/mp4")
            foreign_key = f"upscalevideo/{other.id}/uploads/private.mp4"
            storage.put(foreign_key, io.BytesIO(b"private"), content_type="video/mp4")
            db.commit(); mine_id = mine.id
        finally:
            try: next(gen)
            except StopIteration: pass

        token = _csrf(client, "/login")
        assert client.post("/login", data={"username": "up-batch@example.com",
                                            "password": "matkhau-tot-12",
                                            "csrf_token": token}).status_code == 303
        token = _csrf(client, "/upscalevideo")
        items = [{"video_key": f"upscalevideo/{mine_id}/uploads/{i}.mp4",
                  "duration_s": 10, "request_id": f"batch-a-{i}"}
                 for i in range(3)]
        data = {"csrf_token": token, "manifest": json.dumps(items),
                "preset": "fast", "target_height": "1080", "codec": "h264"}
        first = client.post("/upscalevideo/batch", data=data)
        assert first.status_code == 200 and first.json()["ok"] is True
        first_ids = [x["job_id"] for x in first.json()["jobs"]]
        assert len(first_ids) == 3 and len(set(first_ids)) == 3

        second = client.post("/upscalevideo/batch", data=data)
        assert second.status_code == 200
        assert [x["job_id"] for x in second.json()["jobs"]] == first_ids

        too_many = items + [{"video_key": f"upscalevideo/{mine_id}/uploads/3.mp4",
                             "duration_s": 10, "request_id": "batch-a-3"}]
        assert client.post("/upscalevideo/batch", data={
            "csrf_token": token, "manifest": json.dumps(too_many)}).status_code == 400
        foreign = [{"video_key": foreign_key, "duration_s": 1,
                    "request_id": "foreign-0"}]
        assert client.post("/upscalevideo/batch", data={
            "csrf_token": token, "manifest": json.dumps(foreign)}).status_code == 400

        insufficient = [{"video_key": f"upscalevideo/{mine_id}/uploads/{i+3}.mp4",
                         "duration_s": 60, "request_id": f"batch-b-{i}"}
                        for i in range(3)]
        failed = client.post("/upscalevideo/batch", data={
            "csrf_token": token, "manifest": json.dumps(insufficient),
            "preset": "fast", "target_height": "1080"})
        assert failed.status_code == 400 and failed.json()["ok"] is False
        assert all(x["status"] == "not_submitted" for x in failed.json()["items"])

        gen = dbmod.get_session(); db = next(gen)
        try:
            count = db.execute(select(func.count()).select_from(Job).where(
                Job.user_id == mine_id, Job.app_slug == "upscalevideo")).scalar_one()
            assert count == 3
            assert credit.so_du(db, mine_id) == 5  # 3 × ceil(10/60×30)
        finally:
            try: next(gen)
            except StopIteration: pass
    finally:
        set_storage(None)


def test_upscale_watch_token_scoped_submit_revoke(client, tmp_path):
    """UP5: bearer domain-separated, batch max 3 và revoke có hiệu lực ngay."""
    import hashlib
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import Session
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung

    storage = LocalStorage(str(tmp_path / "watch-api-store")); set_storage(storage)
    try:
        gen = dbmod.get_session(); db = next(gen)
        try:
            user = tao_nguoi_dung(db, email="watch-api@example.com",
                                  password="matkhau-tot-12", is_verified=True)
            credit.cap_tay(db, user.id, 100, by="test"); db.commit(); user_id = user.id
        finally:
            try: next(gen)
            except StopIteration: pass
        token = _csrf(client, "/login")
        assert client.post("/login", data={"username": "watch-api@example.com",
                                            "password": "matkhau-tot-12",
                                            "csrf_token": token}).status_code == 303
        csrf = _csrf(client, "/upscalevideo")
        issued = client.post("/upscalevideo/watch/token", data={"csrf_token": csrf})
        raw = issued.json()["token"]; headers = {"Authorization": f"Bearer {raw}"}
        assert issued.status_code == 200 and len(raw) >= 32
        assert client.get("/upscalevideo/watch/status").status_code == 401
        assert client.get("/upscalevideo/watch/status", headers=headers).json()["max_batch"] == 3

        gen = dbmod.get_session(); db = next(gen)
        try:
            rows = db.query(Session).filter(Session.user_id == user_id).all()
            assert raw not in {row.id for row in rows}
            assert hashlib.sha256(raw.encode()).hexdigest() not in {row.id for row in rows}
        finally:
            try: next(gen)
            except StopIteration: pass

        manifest = [{"filename": "a.mp4", "duration_s": 5,
                     "request_id": "watch-a"},
                    {"filename": "b.mp4", "duration_s": 5,
                     "request_id": "watch-b"}]
        files = [("videos", ("a.mp4", b"video-a", "video/mp4")),
                 ("videos", ("b.mp4", b"video-b", "video/mp4"))]
        submitted = client.post("/upscalevideo/watch/batch", headers=headers,
                                data={"manifest": json.dumps(manifest)}, files=files)
        assert submitted.status_code == 200 and len(submitted.json()["jobs"]) == 2
        repeated = client.post("/upscalevideo/watch/batch", headers=headers,
                               data={"manifest": json.dumps(manifest)}, files=files)
        assert repeated.status_code == 200
        assert [x["job_id"] for x in repeated.json()["jobs"]] == [
            x["job_id"] for x in submitted.json()["jobs"]]

        assert client.post("/upscalevideo/watch/revoke",
                           data={"csrf_token": csrf}).status_code == 200
        assert client.get("/upscalevideo/watch/status", headers=headers).status_code == 401
    finally:
        set_storage(None)


def test_upscale_telemetry_chi_admin_va_eta_can_du_ba_mau(client, monkeypatch):
    import platform_core.db as dbmod
    from datetime import datetime, timedelta, timezone
    from platform_core.models import JOB_DONE, JOB_RUNNING, Job
    from platform_core.users import tao_nguoi_dung
    from apps.upscalevideo import telemetry

    monkeypatch.setattr(telemetry, "gpu_snapshot", lambda: {
        "available": True, "model": "TEST GPU", "util_percent": 10,
        "temp_c": 50, "vram_total_mb": 100, "vram_used_mb": 20})
    gen = dbmod.get_session(); db = next(gen)
    try:
        normal = tao_nguoi_dung(db, email="tele-user@example.com",
                                password="matkhau-tot-12", is_verified=True)
        admin = tao_nguoi_dung(db, email="tele-admin@example.com",
                               password="matkhau-tot-12", is_verified=True)
        admin.role = "admin"
        for index in range(3):
            db.add(Job(user_id=normal.id, app_slug="upscalevideo",
                       job_type="upscalevideo.render", status=JOB_DONE,
                       params={"video_key": f"upscalevideo/{normal.id}/{index}.mp4",
                               "duration_s": 10, "preset": "fast", "target_height": 1080},
                       result={"duration_s": 10, "processing_seconds": 60}))
        db.add(Job(user_id=normal.id, app_slug="upscalevideo",
                   job_type="upscalevideo.render", status=JOB_RUNNING,
                   started_at=datetime.now(timezone.utc) - timedelta(seconds=10),
                   params={"video_key": f"upscalevideo/{normal.id}/run.mp4",
                           "duration_s": 10, "preset": "fast", "target_height": 1080}))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    token = _csrf(client, "/login")
    client.post("/login", data={"username": "tele-user@example.com",
                                 "password": "matkhau-tot-12", "csrf_token": token})
    assert client.get("/upscalevideo/admin-telemetry").status_code == 403
    assert "Còn khoảng" in client.get("/upscalevideo").text
    token = _csrf(client, "/upscalevideo")
    client.post("/logout", data={"csrf_token": token})
    token = _csrf(client, "/login")
    client.post("/login", data={"username": "tele-admin@example.com",
                                 "password": "matkhau-tot-12", "csrf_token": token})
    response = client.get("/upscalevideo/admin-telemetry")
    assert response.status_code == 200 and response.json()["gpu"]["model"] == "TEST GPU"
    assert "video_key" not in response.text and "filename" not in response.text

def test_phien_thu_hoi_khong_gay_vong_lap_redirect(client):
    """Phiên có sid nhưng đã bị THU HỒI (đổi mật khẩu/hết hạn) không được gây
    vòng lặp /login ⇄ route: login_form phải xác thực sid ĐỒNG NHẤT với
    require_login, không chỉ kiểm sid có mặt hay không (ERR_TOO_MANY_REDIRECTS)."""
    import platform_core.db as dbmod
    from platform_core.models import Session as SessionRow
    from platform_core.users import tao_nguoi_dung
    from sqlalchemy import select

    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="stale@example.com",
                       password="matkhau-tot-12", is_verified=True); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    tok = _csrf(client, "/login")
    r = client.post("/login", data={"username": "stale@example.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": tok})
    assert r.status_code == 303                      # đăng nhập được, cookie có sid

    gen = dbmod.get_session(); db = next(gen)         # thu hồi phiên trong DB
    try:
        # DB lưu HASH của token (P0-5), không lưu token thô — xoá thẳng dòng
        # phiên để mô phỏng "đổi mật khẩu/hết hạn" mà không cần token thô.
        row = db.execute(select(SessionRow)).scalars().first()
        assert row is not None
        db.delete(row); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    # /login KHÔNG redirect nữa (không còn phiên hợp lệ) → hiện form 200.
    lf = client.get("/login", follow_redirects=False)
    assert lf.status_code == 200
    # Route bảo vệ → 303 về /login, KHÔNG lặp.
    j = client.get("/jobs", follow_redirects=False)
    assert j.status_code == 303 and j.headers["location"].startswith("/login")


def test_open_redirect_qua_next_bi_chan(client):
    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="k2@example.com", password="matkhau-tot-12",
                       is_verified=True); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    tok = _csrf(client, "/login")
    r = client.post("/login", data={"username": "k2@example.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": tok, "next": "https://evil.com"})
    assert r.status_code == 303
    assert r.headers["location"] == "/"                   # KHÔNG cho ra ngoài


# ── W0.2: dedupe chống double-submit ─────────────────────────────────────────────

def test_double_submit_khong_tao_2_job(client):
    """P0-2: F5 / double-click cùng nội dung → 1 job, trừ credit 1 lần (dedupe_key
    đã đấu ở route submit). Trước khi sửa: 2 job, 2 hold."""
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="dup@example.com",
                           password="matkhau-tot-12", is_verified=True,
                           role="admin")
        credit.cap_tay(db, u.id, 50, by="test"); db.commit(); uid = u.id
    finally:
        try: next(gen)
        except StopIteration: pass

    tok = _csrf(client, "/login")
    client.post("/login", data={"username": "dup@example.com",
                                "password": "matkhau-tot-12", "csrf_token": tok})

    # Endpoint hàng đợi (đi qua submit_with_credit + dedupe) là POST /demo/queue.
    r1 = client.post("/demo/queue", data={"text": "xin chao",
                                          "csrf_token": _csrf(client, "/demo")},
                     follow_redirects=False)
    r2 = client.post("/demo/queue", data={"text": "xin chao",
                                          "csrf_token": _csrf(client, "/demo")},
                     follow_redirects=False)
    assert r1.status_code == 303 and r2.status_code == 303

    gen = dbmod.get_session(); db = next(gen)
    try:
        from sqlalchemy import func, select
        from platform_core.models import Job
        n = db.execute(select(func.count()).select_from(Job)
                       .where(Job.user_id == uid)).scalar_one()
        assert n == 1, f"dedupe hong: co {n} job thay vi 1"
    finally:
        try: next(gen)
        except StopIteration: pass


# ── W0.3: IP thật sau Cloudflare Tunnel ──────────────────────────────────────────

def test_client_ip_uu_tien_cf_connecting_ip():
    from server.auth.session import client_ip

    class _Req:
        def __init__(self, headers, host):
            self.headers = headers
            self.client = type("C", (), {"host": host})()

    assert client_ip(_Req({"cf-connecting-ip": "9.9.9.9"}, "127.0.0.1")) == "9.9.9.9"
    assert client_ip(_Req({}, "127.0.0.1")) == "127.0.0.1"     # fallback khi khong co header


# ── W1.4: auth hardening ─────────────────────────────────────────────────────────

def test_login_chua_xac_thuc_bi_chan(client):
    """Mật khẩu đúng nhưng chưa xác thực email → 403, KHÔNG tạo phiên."""
    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="unv@example.com", password="matkhau-tot-12",
                       is_verified=False); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    tok = _csrf(client, "/login")
    r = client.post("/login", data={"username": "unv@example.com",
                                    "password": "matkhau-tot-12", "csrf_token": tok})
    assert r.status_code == 403
    assert "chưa xác thực" in r.text
    assert "Việc của tôi" not in client.get("/").text     # không vào được


def test_khoa_theo_tai_khoan_du_khac_ip(client):
    """Khoá theo TÀI KHOẢN: 5 lần sai cùng email từ 5 IP khác nhau → lần 6 vẫn
    429 (credential-stuffing từ nhiều IP mà per-IP không chặn được)."""
    for i in range(5):
        tok = _csrf(client, "/login")
        r = client.post("/login", data={"username": "target@x.com",
                                        "password": "sai", "csrf_token": tok},
                        headers={"CF-Connecting-IP": f"10.0.0.{i}"})
        assert r.status_code == 401
    tok = _csrf(client, "/login")
    r = client.post("/login", data={"username": "target@x.com",
                                    "password": "sai", "csrf_token": tok},
                    headers={"CF-Connecting-IP": "10.0.0.250"})   # IP hoàn toàn mới
    assert r.status_code == 429                          # vẫn khoá vì theo tài khoản


def test_logout_can_csrf(client):
    """Logout không token → KHÔNG đăng xuất (giữ phiên); có token → đăng xuất."""
    _tao_va_dang_nhap(client, "lo@example.com")
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert "Việc của tôi" in client.get("/").text        # vẫn đăng nhập

    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/").text).group(1)
    r2 = client.post("/logout", data={"csrf_token": tok}, follow_redirects=False)
    assert r2.status_code == 303 and r2.headers["location"] == "/login"
    assert "Việc của tôi" not in client.get("/").text     # đã đăng xuất


def test_forgot_password_rate_limit(client):
    """forgot-password bị rate-limit (chống bơm mail + đốt hạn ngạch Resend)."""
    for _ in range(5):
        tok = _csrf(client, "/forgot-password")
        r = client.post("/forgot-password",
                        data={"email": "nobody@x.com", "csrf_token": tok},
                        headers={"CF-Connecting-IP": "7.7.7.7"})
        assert r.status_code == 200
    tok = _csrf(client, "/forgot-password")
    r = client.post("/forgot-password",
                    data={"email": "nobody@x.com", "csrf_token": tok},
                    headers={"CF-Connecting-IP": "7.7.7.7"})
    assert r.status_code == 429


def test_rate_limit_theo_cf_ip_khong_khoa_lien(client):
    """P0-3: rate-limit key theo CF-Connecting-IP, không phải 127.0.0.1 chung.
    5 lần sai từ IP A khoá IP A; IP B KHÔNG bị vạ lây. (Dùng username KHÁC nhau
    cho A và B để cô lập per-IP, không lẫn với khoá-theo-tài-khoản của W1.4.)"""
    for _ in range(5):
        tok = _csrf(client, "/login")
        r = client.post("/login", data={"username": "a@x.com", "password": "sai",
                                        "csrf_token": tok},
                        headers={"CF-Connecting-IP": "1.1.1.1"})
        assert r.status_code == 401
    tokA = _csrf(client, "/login")
    ra = client.post("/login", data={"username": "a@x.com", "password": "sai",
                                     "csrf_token": tokA},
                     headers={"CF-Connecting-IP": "1.1.1.1"})
    assert ra.status_code == 429                       # IP A đã bị khoá (per-IP)
    tokB = _csrf(client, "/login")
    rb = client.post("/login", data={"username": "b@x.com", "password": "sai",
                                     "csrf_token": tokB},
                     headers={"CF-Connecting-IP": "2.2.2.2"})
    assert rb.status_code == 401                       # IP B + tài khoản khác: KHÔNG vạ lây
