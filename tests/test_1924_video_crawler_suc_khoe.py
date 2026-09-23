"""
video_crawler — sức khoẻ vận hành (PLAN_MVP §C dòng L4, brief lane vcm-suckhoe).

Ba mảnh, một hợp đồng:
- `suc_khoe.thong_ke`: đọc `jobs` (KHÔNG bảng mới), gộp theo nền × (mục tải xong / mục lỗi theo mã /
  job lỗi toàn phần), tính tỉ lệ thành công + khuyến nghị tắt (< 80%, ≥ 10 mục).
- `nen_tang.CO_TAT_NEN` (`LTT_VIDEO_CRAWLER_TAT`): tắt mềm theo nền, đọc env MỖI LẦN GỌI (không cache).
- `routes_van_hanh`: trang `/van-hanh` operator-only, cùng cổng cờ `LTT_VIDEO_CRAWLER` với `routes.py`.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest

from apps.video_crawler import nen_tang, suc_khoe
from apps.video_crawler.jobs import JOB_TAI
from apps.video_crawler.manifest import MANIFEST


# ═══════════════════════════════════════════════════════════════════════════
# A. suc_khoe.thong_ke — đọc thẳng bảng jobs, không bảng mới
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'sk.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _job(*, nen_tang: str | None, status: str, result: dict | None = None,
         job_type: str = JOB_TAI, app_slug: str = MANIFEST.slug,
         created_at: datetime | None = None):
    from platform_core.models import Job
    params = {} if nen_tang is None else {"nen_tang": nen_tang}
    j = Job(user_id="u1", app_slug=app_slug, job_type=job_type, params=params,
            status=status, result=result)
    if created_at is not None:
        j.created_at = created_at
    return j


def test_muc_tai_xong_va_loi_theo_ma_gop_theo_nen(db):
    from platform_core.models import JOB_DONE
    db.add_all([
        _job(nen_tang="youtube", status=JOB_DONE, result={"muc": [{"id": "a"}, {"id": "b"}], "loi": []}),
        _job(nen_tang="youtube", status=JOB_DONE,
             result={"muc": [{"id": "c"}], "loi": [{"id": "d", "ma": "yt_403"}]}),
        _job(nen_tang="youtube", status=JOB_DONE,
             result={"muc": [], "loi": [{"id": "e", "ma": "yt_403"}, {"id": "f", "ma": "yt_bot"}]}),
    ])
    db.commit()
    kq = suc_khoe.thong_ke(db)
    yt = kq["youtube"]
    assert yt["muc_tai_xong"] == 3
    assert yt["muc_loi"] == 3
    assert yt["muc_loi_theo_ma"] == {"yt_403": 2, "yt_bot": 1}
    assert yt["job_loi_toan_phan"] == 0
    assert yt["tong_job"] == 3


def test_job_loi_toan_phan_dem_o_muc_job_khong_co_ma():
    """Job lỗi TOÀN PHẦN (`jobs.py:_tai_voi` ném trước khi trả result) mất chi tiết theo mục —
    chỉ đếm được ở mức job, không có `loi_theo_ma` (đúng mô tả trong docstring `suc_khoe.py`)."""
    from platform_core.models import JOB_ERROR
    from platform_core import db as dbmod
    import platform_core.models  # noqa: F401
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        dbmod.reset_engine()
        import os
        os.environ["LTT_DATABASE_URL"] = f"sqlite:///{tmp}/e.db"
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        gen = dbmod.get_session(); s = next(gen)
        try:
            s.add(_job(nen_tang="facebook", status=JOB_ERROR, result=None))
            s.commit()
            kq = suc_khoe.thong_ke(s)
            fb = kq["facebook"]
            assert fb["job_loi_toan_phan"] == 1
            assert fb["muc_loi_theo_ma"] == {}
            assert fb["muc_tai_xong"] == 0
            assert fb["ty_le_thanh_cong"] == 0.0
        finally:
            s.close(); dbmod.reset_engine()
            os.environ.pop("LTT_DATABASE_URL", None)


def test_ty_le_thanh_cong_va_khuyen_nghi_tat_can_du_10_muc(db):
    from platform_core.models import JOB_DONE
    # 3 xong, 1 lỗi -> 75% nhưng chỉ 4 mục: chưa đủ mẫu, KHÔNG khuyến nghị tắt.
    db.add(_job(nen_tang="weibo", status=JOB_DONE,
                result={"muc": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                        "loi": [{"id": "4", "ma": "mang"}]}))
    db.commit()
    weibo = suc_khoe.thong_ke(db)["weibo"]
    assert weibo["ty_le_thanh_cong"] == pytest.approx(0.75)
    assert weibo["khuyen_nghi_tat"] is False


def test_khuyen_nghi_tat_khi_du_10_muc_va_duoi_80_phan_tram(db):
    from platform_core.models import JOB_DONE
    # 7 xong, 3 lỗi = 10 mục, 70% < 80% -> khuyến nghị tắt.
    db.add(_job(nen_tang="douyin", status=JOB_DONE,
                result={"muc": [{"id": str(i)} for i in range(7)],
                        "loi": [{"id": f"e{i}", "ma": "mang"} for i in range(3)]}))
    db.commit()
    douyin = suc_khoe.thong_ke(db)["douyin"]
    assert douyin["tong_muc"] == 10
    assert douyin["ty_le_thanh_cong"] == pytest.approx(0.7)
    assert douyin["khuyen_nghi_tat"] is True


def test_khong_khuyen_nghi_tat_khi_tren_80_phan_tram_du_mau(db):
    from platform_core.models import JOB_DONE
    db.add(_job(nen_tang="tiktok", status=JOB_DONE,
                result={"muc": [{"id": str(i)} for i in range(9)],
                        "loi": [{"id": "e0", "ma": "mang"}]}))
    db.commit()
    tt = suc_khoe.thong_ke(db)["tiktok"]
    assert tt["tong_muc"] == 10
    assert tt["ty_le_thanh_cong"] == pytest.approx(0.9)
    assert tt["khuyen_nghi_tat"] is False


def test_chi_tinh_job_tai_khong_tinh_kham_pha_hay_app_khac(db):
    from apps.video_crawler.jobs import JOB_KHAM_PHA
    from platform_core.models import JOB_DONE
    db.add_all([
        _job(nen_tang="youtube", status=JOB_DONE, job_type=JOB_KHAM_PHA,
             result={"muc": [{"id": "1"}, {"id": "2"}]}),        # khám phá: miễn phí, KHÔNG tính
        _job(nen_tang="youtube", status=JOB_DONE, app_slug="autosubvideo",
             result={"muc": [{"id": "1"}]}),                     # app khác cùng tên job_type: KHÔNG tính
    ])
    db.commit()
    assert suc_khoe.thong_ke(db) == {}


def test_bo_qua_trung_khong_phai_thanh_cong_khong_phai_loi(db):
    """`_tai_voi`: mọi mục đều đã tải trước ⇒ `muc=[]`, `loi=[]`, `credit_cost=0` — không tính tiền,
    không phải lỗi. `thong_ke` không được biến ca này thành lỗi hay thành công."""
    from platform_core.models import JOB_DONE
    db.add(_job(nen_tang="instagram", status=JOB_DONE,
                result={"muc": [], "loi": [], "bo_qua_trung": 3, "credit_cost": 0}))
    db.commit()
    ig = suc_khoe.thong_ke(db)["instagram"]
    assert ig["muc_tai_xong"] == 0
    assert ig["muc_loi"] == 0
    assert ig["tong_muc"] == 0
    assert ig["ty_le_thanh_cong"] is None
    assert ig["khuyen_nghi_tat"] is False


def test_thieu_nen_tang_trong_params_roi_vao_khong_ro(db):
    from platform_core.models import JOB_DONE
    db.add(_job(nen_tang=None, status=JOB_DONE, result={"muc": [{"id": "1"}], "loi": []}))
    db.commit()
    assert "khong_ro" in suc_khoe.thong_ke(db)


def test_cua_so_gio_loc_theo_thoi_gian(db):
    from platform_core.models import JOB_DONE
    bay_gio = datetime.now(timezone.utc)
    db.add_all([
        _job(nen_tang="youtube", status=JOB_DONE, result={"muc": [{"id": "moi"}], "loi": []},
             created_at=bay_gio - timedelta(hours=1)),
        _job(nen_tang="youtube", status=JOB_DONE, result={"muc": [{"id": "cu"}], "loi": []},
             created_at=bay_gio - timedelta(hours=48)),
    ])
    db.commit()
    kq = suc_khoe.thong_ke(db, gio=24, bay_gio=bay_gio)
    assert kq["youtube"]["muc_tai_xong"] == 1


def test_nen_khong_co_job_tai_khong_xuat_hien(db):
    assert suc_khoe.thong_ke(db) == {}


# ═══════════════════════════════════════════════════════════════════════════
# B. nen_tang — tắt mềm theo nền qua LTT_VIDEO_CRAWLER_TAT (đọc env mỗi lần gọi)
# ═══════════════════════════════════════════════════════════════════════════

def test_mac_dinh_khong_tat_nen_nao():
    ids = [n.id for n in nen_tang.cac_nen_bat()]
    assert "youtube" in ids and "facebook" in ids


def test_tat_mem_an_nen_khoi_cac_nen_bat(monkeypatch):
    monkeypatch.setenv(nen_tang.CO_TAT_NEN, "youtube,facebook")
    ids = [n.id for n in nen_tang.cac_nen_bat()]
    assert "youtube" not in ids
    assert "facebook" not in ids
    assert "twitter" in ids            # nền khác không bị ảnh hưởng


def test_lay_nen_bat_nem_loi_khi_nen_dang_tat_mem(monkeypatch):
    assert nen_tang.lay_nen_bat("youtube").id == "youtube"      # bình thường: không lỗi
    monkeypatch.setenv(nen_tang.CO_TAT_NEN, "youtube")
    with pytest.raises(nen_tang.NenKhongHopLe):
        nen_tang.lay_nen_bat("youtube")


def test_doc_env_moi_lan_goi_khong_cache(monkeypatch):
    """Đổi env giữa hai lượt gọi liên tiếp (không import lại module) phải có hiệu lực ngay."""
    assert "youtube" in [n.id for n in nen_tang.cac_nen_bat()]
    monkeypatch.setenv(nen_tang.CO_TAT_NEN, "youtube")
    assert "youtube" not in [n.id for n in nen_tang.cac_nen_bat()]
    monkeypatch.delenv(nen_tang.CO_TAT_NEN)
    assert "youtube" in [n.id for n in nen_tang.cac_nen_bat()]


def test_khoang_trang_va_phan_tu_rong_trong_danh_sach_tat_bi_bo_qua(monkeypatch):
    monkeypatch.setenv(nen_tang.CO_TAT_NEN, " youtube , , facebook ")
    ids = [n.id for n in nen_tang.cac_nen_bat()]
    assert "youtube" not in ids and "facebook" not in ids


# ═══════════════════════════════════════════════════════════════════════════
# C. routes_van_hanh — trang operator-only, cùng cổng cờ với routes.py
# ═══════════════════════════════════════════════════════════════════════════

def test_hai_hang_co_mo_phai_bang_nhau():
    """`routes_van_hanh.CO_MO` là bản sao của `routes.py:CO_MO` (không import ngược) — lệch là bug."""
    from apps.video_crawler import routes as vc_routes
    from apps.video_crawler import routes_van_hanh
    assert routes_van_hanh.CO_MO == vc_routes.CO_MO == "LTT_VIDEO_CRAWLER"


@pytest.fixture()
def van_hanh_client(tmp_path, monkeypatch):
    """App đầy đủ (như `test_1906`) + gắn tạm `routes_van_hanh.router` — điều phối sẽ gắn thật khi gộp
    `routes.py` (lane L1); ở đây chỉ để kiểm chính router/template/quyền của lane này hoạt động đúng."""
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'vh.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vc-vh")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("LTT_VIDEO_CRAWLER", "1")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); s = next(gen)
    ops = tao_nguoi_dung(s, email="op@x.com", password="matkhau-tot", role="admin", is_verified=True)
    kh = tao_nguoi_dung(s, email="kh@x.com", password="matkhau-tot", role="user", is_verified=True)
    s.commit()
    ids = (ops.id, kh.id)
    s.close()

    from apps.video_crawler import routes_van_hanh
    from server.app import create_app
    app = create_app()
    app.include_router(routes_van_hanh.router, prefix="/video-crawler")
    client = TestClient(app, base_url="https://testserver")
    yield client, ids
    dbmod.reset_engine()


def _login(client, email):
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text).group(1)
    r = client.post("/login", data={"username": email, "password": "matkhau-tot", "csrf_token": tok},
                    follow_redirects=False)
    assert r.status_code == 303


def test_co_tat_thi_404_ca_khi_da_dang_nhap_operator(van_hanh_client, monkeypatch):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    monkeypatch.setenv("LTT_VIDEO_CRAWLER", "0")
    assert client.get("/video-crawler/van-hanh").status_code == 404


def test_khach_thuong_bi_chan_403(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "kh@x.com")
    assert client.get("/video-crawler/van-hanh").status_code == 403


def test_operator_thay_dung_so_tren_du_lieu_gia(van_hanh_client):
    client, (op_id, _) = van_hanh_client
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, JOB_ERROR, Job
    gen = get_session(); s = next(gen)
    s.add_all([
        # 1 xong + 8 lỗi (loi theo mã) + 1 job lỗi toàn phần = 10 mục, 10% thành công -> đủ mẫu, dưới 80%.
        Job(user_id=op_id, app_slug=MANIFEST.slug, job_type=JOB_TAI, params={"nen_tang": "youtube"},
            status=JOB_DONE, result={"muc": [{"id": "1"}],
                                     "loi": [{"id": str(i), "ma": "yt_403"} for i in range(8)]}),
        Job(user_id=op_id, app_slug=MANIFEST.slug, job_type=JOB_TAI, params={"nen_tang": "youtube"},
            status=JOB_ERROR, result=None),
    ])
    s.commit(); s.close()

    _login(client, "op@x.com")
    r = client.get("/video-crawler/van-hanh")
    assert r.status_code == 200
    assert "youtube" in r.text
    assert "yt_403 × 8" in r.text
    assert "Nên tắt" in r.text          # 1/10 = 10% < 80%, đủ 10 mục -> khuyến nghị tắt


def test_nen_bi_tat_mem_bien_khoi_trang_chinh(van_hanh_client, monkeypatch):
    """Tích hợp với `routes.py` (đã tồn tại, không sửa): nền tắt mềm không còn là chip chọn được."""
    client, _ = van_hanh_client
    monkeypatch.setenv("LTT_VIDEO_CRAWLER_TAT", "youtube")
    _login(client, "kh@x.com")
    r = client.get("/video-crawler")
    assert r.status_code == 200
    assert 'data-nen="youtube"' not in r.text
    assert 'data-nen="facebook"' in r.text
