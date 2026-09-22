"""
video_crawler — lớp pháp lý của MỌI lượt tải (PLAN_MVP §C làn L1; DANH_GIA_MVP N1–N3, N7).

Mệnh đề chốt:
- Lượt tải (cào hết HOẶC tải mục đã chọn) thiếu ô cam kết quyền ⇒ lỗi có tên, KHÔNG tạo job, không giữ credit.
  Xem trước không cần cam kết.
- Có cam kết ⇒ params mang `cam_ket={"phien_ban": PHIEN_BAN_CAM_KET, "luc": <ISO UTC>}`.
- Khoá dedupe bỏ `luc`: bấm đúp cách nhau một giây vẫn là MỘT job (chống trừ tiền hai lần), đổi phiên bản văn bản
  cam kết thì khác khoá.
- Trần tải theo tài khoản: ≤ 60 video/giờ, ≤ 300 video/ngày — đếm số MỤC của job tải của CHÍNH user trong cửa sổ;
  job xong đếm số video thật đã tải, job huỷ trước khi chạy đếm 0; vượt ⇒ lỗi rõ ràng, không tạo job.
- Trang hiện khối điều khoản + liên kết chính sách + kênh báo vi phạm (lấy từ hằng trong app).
"""
from __future__ import annotations

import re
import socket
from datetime import datetime, timedelta, timezone

import pytest

from apps.video_crawler import features


# ── Đơn vị: cam kết + dedupe ─────────────────────────────────────────────────

def test_thieu_cam_ket_thi_loi_co_ten():
    with pytest.raises(features.ChuaCamKet) as e:
        features.gan_cam_ket({"owner_id": "u1"}, dong_y=False)
    assert isinstance(e.value, features.LoiDauVao)
    assert "cam kết" in str(e.value).lower()


def test_co_cam_ket_thi_params_mang_phien_ban_va_luc_utc():
    luc = datetime(2026, 9, 22, 3, 4, 5, tzinfo=timezone.utc)
    p = features.gan_cam_ket({"owner_id": "u1", "muc": []}, dong_y=True, bay_gio=luc)
    assert p["cam_ket"] == {"phien_ban": features.PHIEN_BAN_CAM_KET, "luc": "2026-09-22T03:04:05+00:00"}
    assert p["owner_id"] == "u1" and p["muc"] == []


def test_khoa_dedupe_bo_luc_nhung_giu_phien_ban():
    goc = {"owner_id": "u1", "nen_tang": "youtube", "muc": [{"id": "a" * 11}]}
    p1 = features.gan_cam_ket(goc, dong_y=True, bay_gio=datetime(2026, 9, 22, 1, 0, 0, tzinfo=timezone.utc))
    p2 = features.gan_cam_ket(goc, dong_y=True, bay_gio=datetime(2026, 9, 22, 1, 0, 1, tzinfo=timezone.utc))
    assert p1 != p2
    assert features.khoa_dedupe(features.JOB_TAI, p1) == features.khoa_dedupe(features.JOB_TAI, p2)
    p3 = {**p1, "cam_ket": {**p1["cam_ket"], "phien_ban": "khac"}}
    assert features.khoa_dedupe(features.JOB_TAI, p3) != features.khoa_dedupe(features.JOB_TAI, p1)


# ── Đơn vị: trần tải theo tài khoản ──────────────────────────────────────────

@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'p.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


_BAY_GIO = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


def _job(db, *, owner="u1", so_muc=20, nguon=False, status="queued", truoc=timedelta(minutes=5),
         video_keys=None, started=True, job_type=features.JOB_TAI, app="video_crawler"):
    from platform_core.models import Job
    params = ({"owner_id": owner, "nen_tang": "youtube",
               "nguon": {"che_do": "kenh", "dau_vao": "@a", "so_luong": so_muc, "khong_trung": False}}
              if nguon else
              {"owner_id": owner, "nen_tang": "youtube", "muc": [{"id": f"{i:011d}"} for i in range(so_muc)]})
    j = Job(user_id=owner, app_slug=app, job_type=job_type, params=params, status=status,
            created_at=_BAY_GIO - truoc, started_at=(_BAY_GIO - truoc) if started else None,
            result={"muc": [], "video_keys": list(video_keys)} if video_keys is not None else None)
    db.add(j); db.commit()
    return j


def test_so_muc_du_kien_cua_hai_kieu_tai():
    assert features.so_muc_du_kien({"muc": [{"id": "a"}, {"id": "b"}]}) == 2
    assert features.so_muc_du_kien({"nguon": {"so_luong": 7}}) == 7


def test_duoi_tran_gio_thi_qua(db):
    _job(db, so_muc=20); _job(db, so_muc=20)
    features.kiem_tran_tai(db, "u1", 20, bay_gio=_BAY_GIO)          # 40 + 20 = 60 — đúng trần, được


def test_vuot_tran_gio_thi_loi_ro_rang(db):
    _job(db, so_muc=20); _job(db, so_muc=20); _job(db, so_muc=15, nguon=True)
    with pytest.raises(features.QuaTranTai) as e:
        features.kiem_tran_tai(db, "u1", 10, bay_gio=_BAY_GIO)      # 55 + 10 > 60
    assert isinstance(e.value, features.LoiDauVao)
    assert str(features.TAI_MOI_GIO) in str(e.value)


def test_job_ngoai_cua_so_gio_khong_tinh_vao_tran_gio(db):
    _job(db, so_muc=20, truoc=timedelta(minutes=61))
    _job(db, so_muc=20, truoc=timedelta(minutes=61))
    _job(db, so_muc=20, truoc=timedelta(minutes=61))
    features.kiem_tran_tai(db, "u1", 20, bay_gio=_BAY_GIO)


def test_vuot_tran_ngay_thi_loi_ro_rang(db):
    for h in range(15):                                             # 15 × 20 = 300 trong 24 h, không cái nào trong 1 h
        _job(db, so_muc=20, truoc=timedelta(hours=1, minutes=5 + h * 60))
    with pytest.raises(features.QuaTranTai) as e:
        features.kiem_tran_tai(db, "u1", 1, bay_gio=_BAY_GIO)
    assert str(features.TAI_MOI_NGAY) in str(e.value)


def test_job_hon_24h_khong_tinh(db):
    for _ in range(15):
        _job(db, so_muc=20, truoc=timedelta(hours=25))
    features.kiem_tran_tai(db, "u1", 20, bay_gio=_BAY_GIO)


def test_job_xong_dem_video_that_huy_truoc_khi_chay_dem_khong(db):
    _job(db, so_muc=20, status="done", video_keys=["k1"])           # tải được 1 ⇒ tính 1
    _job(db, so_muc=20, status="cancelled", started=False)          # huỷ khi còn chờ ⇒ 0
    _job(db, so_muc=20, status="error")                             # lỗi không có kết quả ⇒ tính đủ (thận trọng)
    features.kiem_tran_tai(db, "u1", 39, bay_gio=_BAY_GIO)          # 1 + 0 + 20 + 39 = 60
    with pytest.raises(features.QuaTranTai):
        features.kiem_tran_tai(db, "u1", 40, bay_gio=_BAY_GIO)


def test_tran_chi_dem_job_tai_cua_chinh_user(db):
    for _ in range(3):
        _job(db, owner="u2", so_muc=20)                             # người khác
        _job(db, so_muc=20, job_type=features.JOB_KHAM_PHA)         # xem trước không tính
        _job(db, so_muc=20, app="app_khac")                         # app khác
    features.kiem_tran_tai(db, "u1", 60, bay_gio=_BAY_GIO)


# ── Web: form, route, trang ──────────────────────────────────────────────────

@pytest.fixture()
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'w.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vc-pl")
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
    credit.nap(s, ua.id, 1000)
    s.commit()
    uid = ua.id
    s.close()
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    client.post("/logout", follow_redirects=False)
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text).group(1)
    assert client.post("/login", data={"username": "a@x.com", "password": "matkhau-tot", "csrf_token": tok},
                       follow_redirects=False).status_code == 303
    yield client, uid
    dbmod.reset_engine()


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


def _cao_het(client, **them):
    data = {"nen_tang": "youtube", "che_do": "kenh", "dau_vao": "@abc", "so_luong": "4",
            "csrf_token": _csrf(client), **them}
    return client.post("/video-crawler/tai", data=data, follow_redirects=False)


def test_cao_het_thieu_cam_ket_thi_khong_tao_job(env):
    client, uid = env
    r = _cao_het(client)
    assert r.status_code == 400
    assert "cam kết" in r.text.lower()
    assert _jobs(uid) == []


def test_cao_het_co_cam_ket_thi_params_mang_cam_ket(env):
    client, uid = env
    r = _cao_het(client, cam_ket="1")
    assert r.status_code in (204, 303)
    ((_, params),) = _jobs(uid)
    assert params["cam_ket"]["phien_ban"] == features.PHIEN_BAN_CAM_KET
    assert datetime.fromisoformat(params["cam_ket"]["luc"]).utcoffset() == timedelta(0)


def test_bam_dup_cach_mot_giay_van_mot_job(env, monkeypatch):
    client, uid = env
    lan = iter([datetime(2026, 9, 22, 1, 0, 0, tzinfo=timezone.utc), datetime(2026, 9, 22, 1, 0, 1, tzinfo=timezone.utc)])
    goc = features.gan_cam_ket
    monkeypatch.setattr(features, "gan_cam_ket", lambda p, *, dong_y, bay_gio=None: goc(p, dong_y=dong_y, bay_gio=next(lan)))
    _cao_het(client, cam_ket="1"); _cao_het(client, cam_ket="1")
    assert len(_jobs(uid)) == 1


def _xem_truoc_xong(client, uid, ids):
    client.post("/video-crawler/kham-pha",
                data={"nen_tang": "youtube", "che_do": "tu_khoa", "dau_vao": "meo", "so_luong": "3",
                      "csrf_token": _csrf(client)})
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, Job
    gen = get_session(); s = next(gen)
    try:
        j = s.query(Job).filter(Job.user_id == uid, Job.job_type == features.JOB_KHAM_PHA).one()
        j.status = JOB_DONE
        j.result = {"muc": [{"nen_tang": "youtube", "id": i, "url": f"https://www.youtube.com/watch?v={i}",
                             "tieu_de": f"T {i}"} for i in ids], "bo_qua_trung": 0}
        s.commit()
        return j.id
    finally:
        s.close()


def test_xem_truoc_khong_can_cam_ket_con_tai_da_chon_thi_can(env):
    client, uid = env
    a1 = "a1aaaaaaaaa"
    kp = _xem_truoc_xong(client, uid, [a1])                     # xem trước đi qua KHÔNG có cam_ket
    trang = client.get(f"/video-crawler/kham-pha/{kp}").text
    assert 'name="cam_ket"' in trang                            # form "Tải các video đã chọn" có ô cam kết
    r = client.post("/video-crawler/tai", data={"nen_tang": "youtube", "xem_truoc": kp, "muc": [a1],
                                                "csrf_token": _csrf(client)}, follow_redirects=False)
    assert r.status_code == 400 and "cam kết" in r.text.lower()
    assert [t for t, _ in _jobs(uid)] == [features.JOB_KHAM_PHA]
    r = client.post("/video-crawler/tai", data={"nen_tang": "youtube", "xem_truoc": kp, "muc": [a1],
                                                "cam_ket": "1", "csrf_token": _csrf(client)},
                    follow_redirects=False)
    assert r.status_code in (204, 303)
    tai = [p for t, p in _jobs(uid) if t == features.JOB_TAI]
    assert tai[0]["cam_ket"]["phien_ban"] == features.PHIEN_BAN_CAM_KET


def test_vuot_tran_qua_route_thi_bao_ro_khong_tao_job(env, monkeypatch):
    client, uid = env
    monkeypatch.setattr(features, "TAI_MOI_GIO", 5)
    r = _cao_het(client, cam_ket="1", so_luong="4")
    assert r.status_code in (204, 303)
    r = _cao_het(client, cam_ket="1", so_luong="2", dau_vao="@khac")
    assert r.status_code == 429
    assert "5 video" in r.text
    assert len(_jobs(uid)) == 1


def test_trang_co_o_cam_ket_dieu_khoan_va_kenh_bao_vi_pham(env):
    client, _ = env
    html = client.get("/video-crawler").text
    assert re.search(r'<input[^>]+name="cam_ket"[^>]*required', html)
    assert features.URL_DIEU_KHOAN in html
    assert features.URL_BAO_VI_PHAM in html
    assert features.EMAIL_HO_TRO in html
