"""
video_crawler — bề mặt web (spec §9, §21, §22, §26).

Mệnh đề chốt:
- Cờ `LTT_VIDEO_CRAWLER` tắt ⇒ 404, kể cả chưa đăng nhập (không thừa nhận là có app, tiền lệ ASV `_cong_co`).
- Trang sinh từ registry: nền đã bật mới hiện, chế độ đúng theo nền.
- POST thiếu CSRF ⇒ 400, không tạo job.
- Job nộp luôn thuộc người đang đăng nhập (owner lấy từ phiên, không từ form).
- Người khác không xem được kết quả xem trước của mình.
"""
from __future__ import annotations

import re
import socket

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'w.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vc")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("LTT_VIDEO_CRAWLER", "1")
    # DNS giả: test không đọc mạng; mọi tên miền phân giải ra một IP công khai.
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.250.66.78", 443))])

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()                                   # bảng vc_phien của app
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); s = next(gen)
    ua = tao_nguoi_dung(s, email="a@x.com", password="matkhau-tot", is_verified=True)
    ub = tao_nguoi_dung(s, email="b@x.com", password="matkhau-tot", is_verified=True)
    credit.nap(s, ua.id, 100); credit.nap(s, ub.id, 100)
    s.commit()
    ids = (ua.id, ub.id)
    s.close()

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    yield client, ids
    dbmod.reset_engine()


def _login(client, email):
    client.post("/logout", follow_redirects=False)
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text).group(1)
    r = client.post("/login", data={"username": email, "password": "matkhau-tot", "csrf_token": tok},
                    follow_redirects=False)
    assert r.status_code == 303


def _csrf(client):
    return re.search(r'name="csrf_token" value="([^"]+)"', client.get("/video-crawler").text).group(1)


def _jobs(uid):
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); s = next(gen)
    try:
        return [(j.job_type, j.params) for j in s.query(Job).filter(Job.user_id == uid).all()]
    finally:
        s.close()


def test_co_tat_thi_404_ca_khi_chua_dang_nhap(env, monkeypatch):
    client, _ = env
    monkeypatch.setenv("LTT_VIDEO_CRAWLER", "0")
    assert client.get("/video-crawler", follow_redirects=False).status_code == 404


def test_trang_sinh_tu_registry(env):
    client, _ = env
    _login(client, "a@x.com")
    r = client.get("/video-crawler")
    assert r.status_code == 200
    assert 'data-nen="youtube"' in r.text
    assert 'data-nen="kuaishou"' not in r.text          # nền chưa bật không hiện
    for che_do in ("tu_khoa", "link", "kenh", "bo"):
        assert f'value="{che_do}"' in r.text


def test_post_thieu_csrf_bi_tu_choi(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/kham-pha", data={"nen_tang": "youtube", "che_do": "tu_khoa",
                                                     "dau_vao": "meo", "so_luong": "3"})
    assert r.status_code == 400
    assert _jobs(ua) == []


def test_kham_pha_tao_job_cua_chinh_nguoi_dang_nhap(env):
    client, (ua, ub) = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/kham-pha",
                    data={"nen_tang": "youtube", "che_do": "tu_khoa", "dau_vao": "meo", "so_luong": "3",
                          "owner_id": ub, "csrf_token": _csrf(client)})
    assert r.status_code == 200
    jobs = _jobs(ua)
    assert [t for t, _ in jobs] == ["video_crawler.kham_pha"]
    assert jobs[0][1]["owner_id"] == ua                   # form gửi owner_id của B cũng không ăn
    assert _jobs(ub) == []


def test_dau_vao_sai_bao_loi_co_ten_khong_tao_job(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/kham-pha",
                    data={"nen_tang": "youtube", "che_do": "link", "dau_vao": "https://evil.example/x",
                          "so_luong": "1", "csrf_token": _csrf(client)})
    assert r.status_code == 400
    assert "Link không hợp lệ" in r.text
    assert _jobs(ua) == []


def _xem_truoc_xong(client, uid, ids):
    """Nộp một xem trước qua route thật rồi đánh dấu xong với kết quả giả (web test không có worker)."""
    client.post("/video-crawler/kham-pha",
                data={"nen_tang": "youtube", "che_do": "tu_khoa", "dau_vao": "meo", "so_luong": "3",
                      "csrf_token": _csrf(client)})
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, Job
    gen = get_session(); s = next(gen)
    try:
        j = s.query(Job).filter(Job.user_id == uid, Job.job_type == "video_crawler.kham_pha").one()
        j.status = JOB_DONE
        j.result = {"muc": [{"nen_tang": "youtube", "id": i, "url": f"https://www.youtube.com/watch?v={i}",
                             "tieu_de": f"T {i}"} for i in ids], "bo_qua_trung": 0}
        s.commit()
        return j.id
    finally:
        s.close()


def test_tai_muc_da_chon_lay_tu_xem_truoc_bo_url_cua_form(env):
    """Review BLOCKER: `url_<id>` do form gửi bị BỎ; mục lấy từ kết quả xem trước của chính người dùng."""
    client, (ua, _) = env
    _login(client, "a@x.com")
    a1, b2 = "a1aaaaaaaaa", "b2bbbbbbbbb"
    kp = _xem_truoc_xong(client, ua, [a1, b2])
    r = client.post("/video-crawler/tai",
                    data={"nen_tang": "youtube", "xem_truoc": kp, "muc": [a1, b2],
                          f"url_{a1}": "https://www.youtube.com/playlist?list=PLtan_cong",
                          "csrf_token": _csrf(client)},
                    follow_redirects=False)
    assert r.status_code in (204, 303)
    tai = [p for t, p in _jobs(ua) if t == "video_crawler.tai"]
    assert [m["id"] for m in tai[0]["muc"]] == [a1, b2]
    assert tai[0]["muc"][0]["url"] == f"https://www.youtube.com/watch?v={a1}"


def test_loi_htmx_tra_200_de_hien_duoc(env):
    """Review MAJOR 7: htmx 2 không swap phản hồi 4xx ⇒ khách không thấy lỗi (CSRF hết hạn, thiếu credit)."""
    client, _ = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/kham-pha", headers={"HX-Request": "true"},
                    data={"nen_tang": "youtube", "che_do": "tu_khoa", "dau_vao": "meo", "so_luong": "3",
                          "csrf_token": "sai"})
    assert r.status_code == 200
    assert "Phiên đã hết hạn" in r.text


def test_cao_het_theo_nguon(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/tai",
                    data={"nen_tang": "youtube", "che_do": "kenh", "dau_vao": "@abc", "so_luong": "4",
                          "khong_trung": "1", "csrf_token": _csrf(client)},
                    follow_redirects=False)
    assert r.status_code in (204, 303)
    ((_, params),) = _jobs(ua)
    assert params["nguon"] == {"che_do": "kenh", "dau_vao": "@abc", "so_luong": 4, "khong_trung": True}


def test_nguoi_khac_khong_xem_duoc_ket_qua_xem_truoc(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    client.post("/video-crawler/kham-pha",
                data={"nen_tang": "youtube", "che_do": "tu_khoa", "dau_vao": "meo", "so_luong": "3",
                      "csrf_token": _csrf(client)})
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); s = next(gen)
    jid = s.query(Job).filter(Job.user_id == ua).one().id
    s.close()
    assert client.get(f"/video-crawler/kham-pha/{jid}").status_code == 200
    _login(client, "b@x.com")
    assert client.get(f"/video-crawler/kham-pha/{jid}").status_code == 404


# ── Phiên đăng nhập (B1) ──────────────────────────────────────────────────────

_BI_MAT_WEB = "SAPISID-bi-mat-web-0123456789"
_COOKIES_WEB = ("# Netscape HTTP Cookie File\n"
                f".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\t{_BI_MAT_WEB}\n")


def test_nhap_phien_hien_trang_thai_khong_lo_gia_tri(env, monkeypatch):
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-web")
    client, _ = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/phien", data={"nen_tang": "youtube", "cookies_txt": _COOKIES_WEB,
                                                  "csrf_token": _csrf(client)}, follow_redirects=False)
    assert r.status_code in (204, 303)
    trang = client.get("/video-crawler").text
    assert 'data-phien="youtube"' in trang
    assert _BI_MAT_WEB not in trang
    _login(client, "b@x.com")
    assert 'data-phien="youtube"' not in client.get("/video-crawler").text     # user khác không thấy


def test_xoa_phien_can_csrf(env, monkeypatch):
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-web")
    client, _ = env
    _login(client, "a@x.com")
    client.post("/video-crawler/phien", data={"nen_tang": "youtube", "cookies_txt": _COOKIES_WEB,
                                              "csrf_token": _csrf(client)})
    assert client.post("/video-crawler/phien/xoa", data={"nen_tang": "youtube"}).status_code == 400
    assert 'data-phien="youtube"' in client.get("/video-crawler").text
    client.post("/video-crawler/phien/xoa", data={"nen_tang": "youtube", "csrf_token": _csrf(client)})
    assert 'data-phien="youtube"' not in client.get("/video-crawler").text


def test_cookie_khong_hop_le_bao_loi_co_ten(env, monkeypatch):
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-web")
    client, _ = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/phien", data={"nen_tang": "youtube", "cookies_txt": "xin chao",
                                                  "csrf_token": _csrf(client)})
    assert r.status_code == 400
    assert "cookie" in r.text.lower()


# ── Ảnh bìa + poll (SO_LOI L10, L14) ────────────────────────────────────────

def test_anh_bia_chi_chu_xem_duoc(env, monkeypatch):
    from apps.video_crawler import anh_bia
    monkeypatch.setattr(anh_bia, "_lay_mac_dinh", lambda url, *, toi_da: (b"\xff\xd8\xffJPEG", "image/jpeg"))
    client, (ua, _) = env
    _login(client, "a@x.com")
    vid = "a1aaaaaaaaa"
    kp = _xem_truoc_xong(client, ua, [vid])
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); s = next(gen)
    j = s.get(Job, kp)
    j.result = {"muc": [{"id": vid, "anh_bia": "https://i.ytimg.com/vi/x/hq.jpg"}]}
    s.commit(); s.close()
    r = client.get(f"/video-crawler/anh-bia/{kp}/0")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert "public" not in r.headers.get("cache-control", "")          # nền tảng ép no-store cho trang cần đăng nhập
    _login(client, "b@x.com")
    assert client.get(f"/video-crawler/anh-bia/{kp}/0").status_code == 404


def test_hang_doi_chi_poll_khi_con_job_chay(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    assert "every 4s" not in client.get("/video-crawler/hang-doi").text     # chưa có job
    client.post("/video-crawler/kham-pha", data={"nen_tang": "youtube", "che_do": "tu_khoa", "dau_vao": "meo",
                                                 "so_luong": "3", "csrf_token": _csrf(client)})
    assert "every 4s" in client.get("/video-crawler/hang-doi").text          # job đang chờ
