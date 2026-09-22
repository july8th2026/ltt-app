"""video_crawler — UX (PLAN_MVP W2-L7, spec parity A20/A21).

- Tốc độ + ETA thật trong thông điệp tiến độ lúc tải (`adapters/_ytdlp.py` hook — phần LTT thêm).
- "Tải lại các mục lỗi" của một job tải đã xong: job mới CHỈ chứa các mục có trong `job.result.loi`.
- Lọc lịch sử theo nền (`?nen=`) trong bảng hàng đợi.
- Hướng dẫn xuất cookies.txt theo trình duyệt + cảnh báo rủi ro tài khoản (N7).
- Placeholder ô nhập theo (nền, chế độ).
"""
from __future__ import annotations

import re
import socket

import pytest

from apps.video_crawler.adapters import _ytdlp

# ---------------------------------------------------------------- tốc độ + ETA (đơn vị, không mạng)


def test_dinh_dang_toc_do_don_vi_theo_nguong():
    assert _ytdlp._dinh_dang_toc_do(512) == "512 B/s"
    assert _ytdlp._dinh_dang_toc_do(2.3 * 1024 ** 2) == "2,3 MB/s"
    assert _ytdlp._dinh_dang_toc_do(1.5 * 1024 ** 3) == "1,5 GB/s"


def test_dinh_dang_eta_giay_phut_gio():
    assert _ytdlp._dinh_dang_eta(12) == "12 s"
    assert _ytdlp._dinh_dang_eta(90) == "1:30"
    assert _ytdlp._dinh_dang_eta(3700) == "1:01:40"


def test_toc_do_eta_ghep_ca_hai():
    assert _ytdlp.toc_do_eta({"speed": 2.3 * 1024 ** 2, "eta": 12}) == "2,3 MB/s · còn 12 s"


def test_toc_do_eta_rong_khi_chua_co_mau():
    assert _ytdlp.toc_do_eta({"speed": None, "eta": None}) == ""
    assert _ytdlp.toc_do_eta({}) == ""


def test_toc_do_eta_mot_phan_thieu():
    assert _ytdlp.toc_do_eta({"speed": 1024, "eta": None}) == "1,0 KB/s"
    assert _ytdlp.toc_do_eta({"speed": None, "eta": 5}) == "còn 5 s"


# ---------------------------------------------------------------- hook thật của YtdlpAdapter.tai


class _FakeYDL:
    def __init__(self, opts, *, kich_ban=None):
        self.params = opts
        self.kich_ban = kich_ban

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def download(self, urls):
        if self.kich_ban:
            self.kich_ban(self)
        return 0

    def hook(self, d):
        for h in self.params.get("progress_hooks", []):
            h(d)


def test_hook_tai_dua_toc_do_eta_vao_thong_diep(tmp_path):
    from apps.video_crawler.adapters._ytdlp import YtdlpAdapter
    from apps.video_crawler.adapters.base import CrawlItem

    class NenGia(YtdlpAdapter):
        nen_tang = "gia"

        def url_video(self, id):
            return f"https://gia.test/v/{id}"

        def id_hop_le(self, id):
            return id == "12345"

        def url_kham_pha(self, che_do, dau_vao, n):
            return dau_vao

    def kich_ban(y):
        y.hook({"status": "downloading", "downloaded_bytes": 40, "total_bytes": 100,
                "speed": 2.3 * 1024 ** 2, "eta": 12})
        (tmp_path / "12345.mp4").write_bytes(b"x" * 10)

    def nha(opts):
        return _FakeYDL(opts, kich_ban=kich_ban)

    msgs = []
    NenGia(nha).tai(CrawlItem("gia", "12345", "https://gia.test/v/12345"), tmp_path,
                    bao_tien_do=lambda p, m: msgs.append(m))
    assert any("2,3 MB/s" in m and "còn 12 s" in m for m in msgs)


# ---------------------------------------------------------------- web (route + template)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'w.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vc-ux")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("LTT_VIDEO_CRAWLER", "1")
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.250.66.78", 443))])

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
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


def _tao_job_tai_co_loi(uid, *, xong_ids, loi_ids, nen_tang="youtube"):
    """Job `video_crawler.tai` đã DONE với vài mục xong + vài mục lỗi tạm thời (giống `_tai_voi` trả về)."""
    from platform_core.db import get_session
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import JOB_DONE

    gen = get_session(); s = next(gen)
    try:
        muc = [{"id": i} for i in xong_ids + loi_ids]
        job = submit_with_credit(s, user_id=uid, app_slug="video_crawler", job_type="video_crawler.tai",
                                 params={"owner_id": uid, "nen_tang": nen_tang, "muc": muc},
                                 dedupe_key=f"k-{xong_ids}-{loi_ids}", max_attempts=2)
        job.status = JOB_DONE
        job.result = {
            "muc": [{"nen_tang": nen_tang, "id": i, "url": f"https://www.youtube.com/watch?v={i}",
                    "tieu_de": f"T {i}", "tep": f"video_crawler/{uid}/{job.id}/{i}.mp4"} for i in xong_ids],
            "video_keys": [f"video_crawler/{uid}/{job.id}/{i}.mp4" for i in xong_ids],
            "loi": [{"id": i, "ma": "mang", "thong_diep": "Lỗi mạng khi kết nối tới nền tảng."} for i in loi_ids],
            "bo_qua_trung": 0, "credit_cost": len(xong_ids),
        }
        s.commit()
        return job.id
    finally:
        s.close()


def _jobs_tai(uid):
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); s = next(gen)
    try:
        return [(j.job_type, j.params) for j in
                s.query(Job).filter(Job.user_id == uid, Job.job_type == "video_crawler.tai").all()]
    finally:
        s.close()


# -- Tải lại các mục lỗi ------------------------------------------------------

def test_thu_lai_loi_tao_job_moi_chi_voi_muc_loi(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    id_xong, id_loi = "a1aaaaaaaaa", "b2bbbbbbbbb"
    jid = _tao_job_tai_co_loi(ua, xong_ids=[id_xong], loi_ids=[id_loi])
    r = client.post(f"/video-crawler/tai/{jid}/thu-lai-loi",
                    data={"cam_ket": "1", "csrf_token": _csrf(client)}, follow_redirects=False)
    assert r.status_code in (204, 303)
    tai = _jobs_tai(ua)
    assert len(tai) == 2                                    # job gốc + job thử lại
    moi = [p for _, p in tai if p.get("muc") and [m["id"] for m in p["muc"]] == [id_loi]]
    assert len(moi) == 1
    assert moi[0]["muc"][0]["url"] == f"https://www.youtube.com/watch?v={id_loi}"   # dựng lại từ id, không tin gì cũ


def test_thu_lai_loi_thieu_cam_ket_bao_loi_khong_tao_job(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    jid = _tao_job_tai_co_loi(ua, xong_ids=["a1aaaaaaaaa"], loi_ids=["b2bbbbbbbbb"])
    truoc = len(_jobs_tai(ua))
    r = client.post(f"/video-crawler/tai/{jid}/thu-lai-loi", data={"csrf_token": _csrf(client)})
    assert r.status_code == 400
    assert "cam kết" in r.text.lower()
    assert len(_jobs_tai(ua)) == truoc


def test_thu_lai_loi_khong_co_muc_loi_bao_loi(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    jid = _tao_job_tai_co_loi(ua, xong_ids=["a1aaaaaaaaa"], loi_ids=[])
    r = client.post(f"/video-crawler/tai/{jid}/thu-lai-loi",
                    data={"cam_ket": "1", "csrf_token": _csrf(client)})
    assert r.status_code == 400
    assert "không có mục lỗi" in r.text.lower()


def test_thu_lai_loi_khong_phai_chu_thi_404(env):
    client, (ua, ub) = env
    _login(client, "a@x.com")
    jid = _tao_job_tai_co_loi(ua, xong_ids=["a1aaaaaaaaa"], loi_ids=["b2bbbbbbbbb"])
    _login(client, "b@x.com")
    r = client.post(f"/video-crawler/tai/{jid}/thu-lai-loi",
                    data={"cam_ket": "1", "csrf_token": _csrf(client)})
    assert r.status_code == 404
    assert _jobs_tai(ub) == []


def test_thu_lai_loi_thieu_csrf_bi_tu_choi(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    jid = _tao_job_tai_co_loi(ua, xong_ids=["a1aaaaaaaaa"], loi_ids=["b2bbbbbbbbb"])
    r = client.post(f"/video-crawler/tai/{jid}/thu-lai-loi", data={"cam_ket": "1"})
    assert r.status_code == 400
    assert len(_jobs_tai(ua)) == 1


def test_nut_thu_lai_loi_hien_khi_job_co_muc_loi(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    jid = _tao_job_tai_co_loi(ua, xong_ids=["a1aaaaaaaaa"], loi_ids=["b2bbbbbbbbb"])
    trang = client.get("/video-crawler/hang-doi").text
    assert f"/video-crawler/tai/{jid}/thu-lai-loi" in trang
    assert "Tải lại 1 mục lỗi" in trang


# -- Lọc lịch sử theo nền -----------------------------------------------------

def test_loc_lich_su_theo_nen(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    _tao_job_tai_co_loi(ua, xong_ids=["a1aaaaaaaaa"], loi_ids=[], nen_tang="youtube")
    _tao_job_tai_co_loi(ua, xong_ids=["c3ccccccccc"], loi_ids=[], nen_tang="weibo")

    tat_ca = client.get("/video-crawler/hang-doi").text
    assert tat_ca.count("<tr>") == 3               # 1 dòng đầu bảng (thead) + 2 job

    chi_yt = client.get("/video-crawler/hang-doi?nen=youtube").text
    assert chi_yt.count("<tr>") == 2                # thead + đúng 1 job (youtube)

    chi_douyin = client.get("/video-crawler/hang-doi?nen=douyin").text
    assert "Không có lượt cào nào cho nền này" in chi_douyin


def test_bo_loc_nen_co_trong_trang_chinh(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    trang = client.get("/video-crawler").text
    assert '<select name="nen">' in trang
    assert "Tất cả nền" in trang


# -- Placeholder theo (nền, chế độ) ------------------------------------------

def test_placeholder_theo_nen_che_do_trong_html(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    trang = client.get("/video-crawler").text
    m = re.search(r'data-nen="youtube"[^>]*data-goi-y=\'([^\']*)\'', trang)
    assert m, trang[:2000]
    import json
    goi_y = json.loads(m.group(1))
    assert goi_y["link"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert goi_y["bo"].startswith("https://www.youtube.com/playlist?list=")


def test_placeholder_khong_co_che_do_nen_khong_ho_tro(env):
    """bilibili_tv chỉ hỗ trợ 'link' — bảng goi_y không được lọt che_do khác vào (registry là nguồn chân lý)."""
    client, (ua, _) = env
    _login(client, "a@x.com")
    trang = client.get("/video-crawler").text
    m = re.search(r'data-nen="bilibili_tv"[^>]*data-goi-y=\'([^\']*)\'', trang)
    assert m
    import json
    goi_y = json.loads(m.group(1))
    assert set(goi_y.keys()) == {"link"}


# -- Hướng dẫn xuất cookies.txt + cảnh báo rủi ro tài khoản -------------------

def test_huong_dan_xuat_cookies_va_canh_bao_tai_khoan(env):
    client, (ua, _) = env
    _login(client, "a@x.com")
    trang = client.get("/video-crawler").text
    assert "Get cookies.txt LOCALLY" in trang
    assert "LOCALLY" in trang and "gửi cookie của bạn ra máy chủ ngoài" in trang
    assert "Rủi ro tài khoản" in trang and "tài khoản phụ" in trang
