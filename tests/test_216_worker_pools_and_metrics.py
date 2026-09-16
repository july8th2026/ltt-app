"""Đội hình worker theo lớp tài nguyên, và metrics rời khỏi tiến trình.

Hai thay đổi khác nhau nhưng cùng một lý do: nền tảng chạy nhiều tiến trình, và
cả hai chỗ này đều được viết như thể chỉ có một.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'pools.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.public_api import metrics

    Base.metadata.create_all(get_engine())
    metrics.reset()
    gen = get_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        metrics.reset()
        dbmod.reset_engine()


# ── Đội hình worker ──────────────────────────────────────────────────────────

def test_khong_khai_gi_thi_giu_nguyen_hanh_vi_cu(monkeypatch):
    """Đổi ngầm đội hình của một máy chủ đang chạy là thứ không ai muốn gặp."""
    import job_worker

    monkeypatch.delenv("LTT_WORKER_POOLS", raising=False)
    monkeypatch.setenv("LTT_WORKER_PROCESSES", "4")
    assert job_worker._doi_hinh() == [(None, 4)]


def test_khai_pool_thi_moi_pool_co_tap_nang_luc_rieng(monkeypatch):
    import job_worker

    monkeypatch.setenv("LTT_WORKER_POOLS", "api:6, gpu+ffmpeg:2")
    doi_hinh = job_worker._doi_hinh()

    assert [so for _nl, so in doi_hinh] == [6, 2]
    assert doi_hinh[0][0] == {"api"}
    assert doi_hinh[1][0] == {"api", "gpu", "ffmpeg"}


def test_pool_gpu_van_nhat_duoc_job_chi_can_api(monkeypatch):
    """Một worker khai nhiều năng lực hơn phải nhặt được NHIỀU loại hơn.

    Nếu pool `gpu` chỉ nhặt job GPU thì lúc không có job GPU nó nằm không, trong
    khi hàng đợi đầy job chờ mạng — đúng cái lãng phí mà việc chia lớp sinh ra
    để chấm dứt.
    """
    import job_worker

    monkeypatch.setenv("LTT_WORKER_POOLS", "gpu:1")
    nang_luc, _so = job_worker._doi_hinh()[0]
    assert "api" in nang_luc


def test_khai_sai_thi_lui_ve_mac_dinh_chu_khong_sap(monkeypatch):
    import job_worker

    monkeypatch.setenv("LTT_WORKER_POOLS", "khong-phai-so:abc")
    monkeypatch.setenv("LTT_WORKER_PROCESSES", "2")
    assert job_worker._doi_hinh() == [(None, 2)]


def test_worker_chi_nhat_job_nam_trong_nang_luc_cua_no(db):
    """Đây là chỗ việc chia lớp thật sự có hiệu lực.

    `jobs.claim()` lọc theo `manifest.requires`, nên một worker `api` không được
    nhặt job của app đòi GPU — nếu nó nhặt, job sẽ chạy trên máy không có card.
    """
    from platform_core import jobs as jobq
    from platform_core.models import Job

    db.add(Job(id=str(uuid.uuid4()), user_id="u-1", app_slug="upscalevideo",
               job_type="upscalevideo.render", params={},
               status="queued", next_run_at=datetime.now(timezone.utc),
               created_at=datetime.now(timezone.utc)))
    db.commit()

    chi_api = jobq.claim(db, worker_id="w-api", capabilities={"api"})
    assert chi_api is None, "worker không có GPU vẫn nhặt job GPU"

    co_gpu = jobq.claim(db, worker_id="w-gpu",
                        capabilities={"api", "gpu", "ffmpeg"})
    assert co_gpu is not None, "worker đủ năng lực vẫn không nhặt được"


# ── Metrics ──────────────────────────────────────────────────────────────────

def test_xa_roi_thi_bo_dem_cuc_bo_ve_khong(db):
    """Lấy-rồi-xoá phải nguyên tử, nếu không số đếm giữa hai thao tác sẽ mất."""
    from platform_core.public_api import metrics

    metrics.increment("requests", 5)
    metrics.observe("request_ms", 12.0)

    assert metrics.flush(db) == 2
    db.commit()

    assert metrics.snapshot()["counters"] == {}
    assert metrics.snapshot()["latency"] == {}


def test_khong_co_gi_de_xa_thi_khong_ghi_dong_nao(db):
    from platform_core.public_api import metrics

    assert metrics.flush(db) == 0


def test_so_song_sot_qua_khoi_dong_lai(db):
    """Bộ đếm trong tiến trình mất khi khởi động lại — bảng thì không."""
    from platform_core.public_api import metrics

    metrics.increment("jobs_created", 7)
    metrics.flush(db)
    db.commit()

    metrics.reset()          # như thể tiến trình vừa khởi động lại
    assert metrics.snapshot()["counters"] == {}

    gop = metrics.aggregate(db, hours=1)
    assert gop["counters"]["jobs_created"] == 7


def test_nhieu_tien_trinh_duoc_cong_lai(db):
    """Điều mà bộ đếm trong tiến trình không bao giờ làm được."""
    from platform_core.public_api import metrics

    metrics.increment("requests", 10)
    metrics.flush(db, process="may:1001")
    metrics.increment("requests", 5)
    metrics.flush(db, process="may:1002")
    db.commit()

    gop = metrics.aggregate(db, hours=1)
    assert gop["counters"]["requests"] == 15
    assert gop["processes"] == 2


def test_do_tre_cong_dung_cach(db):
    """Trung bình phải tính trên tổng, không phải trung bình của trung bình."""
    from platform_core.public_api import metrics

    metrics.observe("request_ms", 10.0)
    metrics.observe("request_ms", 30.0)
    metrics.flush(db, process="may:1")
    metrics.observe("request_ms", 100.0)
    metrics.flush(db, process="may:2")
    db.commit()

    do_tre = metrics.aggregate(db, hours=1)["latency"]["request_ms"]
    assert do_tre["count"] == 3
    assert do_tre["avg_ms"] == pytest.approx((10 + 30 + 100) / 3, abs=0.01)
    assert do_tre["max_ms"] == 100.0


def test_ngoai_cua_so_thi_khong_tinh(db):
    from platform_core.public_api import metrics
    from platform_core.public_api.tables import ApiMetricSample

    metrics.increment("requests", 3)
    metrics.flush(db)
    db.commit()

    cu = db.execute(__import__("sqlalchemy").select(ApiMetricSample)).scalars().first()
    cu.window_start = datetime.now(timezone.utc) - timedelta(days=3)
    db.commit()

    assert metrics.aggregate(db, hours=24)["counters"] == {}


def test_mau_cu_bi_don(db):
    """Bảng ghi mỗi phút mỗi tiến trình thì không dọn là phình mãi."""
    import sqlalchemy as sa

    from platform_core.public_api import metrics
    from platform_core.public_api.tables import ApiMetricSample

    metrics.increment("requests", 1)
    metrics.flush(db)
    db.commit()

    row = db.execute(sa.select(ApiMetricSample)).scalars().first()
    row.window_start = datetime.now(timezone.utc) - timedelta(days=60)
    db.commit()

    assert metrics.purge_expired(db) == 1
    db.commit()
    assert db.execute(sa.select(sa.func.count(ApiMetricSample.id))).scalar_one() == 0


def test_mau_con_han_khong_bi_don(db):
    import sqlalchemy as sa

    from platform_core.public_api import metrics
    from platform_core.public_api.tables import ApiMetricSample

    metrics.increment("requests", 1)
    metrics.flush(db)
    db.commit()

    assert metrics.purge_expired(db) == 0
    assert db.execute(sa.select(sa.func.count(ApiMetricSample.id))).scalar_one() == 1


def test_mau_metrics_khong_mang_gi_cua_khach(db):
    """Tên bộ đếm là hợp đồng với người vận hành, không phải dữ liệu khách.

    Một bảng đo lường mà lỡ mang id khách hay nội dung là một kho dữ liệu mới
    không ai khai trong bảng kiểm kê riêng tư.
    """
    import sqlalchemy as sa

    from platform_core.public_api import metrics
    from platform_core.public_api.tables import ApiMetricSample

    metrics.increment("requests", 1)
    metrics.flush(db)
    db.commit()

    cot = {c.name for c in ApiMetricSample.__table__.columns}
    assert "user_id" not in cot and "key_id" not in cot and "payload" not in cot

    row = db.execute(sa.select(ApiMetricSample)).scalars().first()
    assert row.name in metrics.snapshot()["counters"] or row.name == "requests"


# ── GUI-D006 (16/09/2026): app nào KHÔNG làn nào nhặt được ──────────────────
#
# 🔴 13–16/09 `LTT_WORKER_POOLS=api:6, gpu:1` thiếu làn `voice` ⇒ job LTT VOICE
#    nằm `queued` ba ngày, không log, không event. Hàm dưới trả lời đúng câu
#    không ai hỏi: "có app đang bật nào mà không worker nào nhặt được không".

_APP = [("ltt_llm", ("api",), True), ("ltt_voice", ("voice",), True),
        ("taoclipngan", ("gpu", "ffmpeg"), True), ("asv_voice", ("voice",), False)]


def _doi_hinh_tu(monkeypatch, chuoi):
    import job_worker
    monkeypatch.setenv("LTT_WORKER_POOLS", chuoi)
    return job_worker._doi_hinh()


def test_D006_cau_hinh_14_09_de_lo_ltt_voice_vo_hinh(monkeypatch):
    import job_worker
    vo_hinh = job_worker.app_khong_lan_nao_nhat(
        _doi_hinh_tu(monkeypatch, "api:6, gpu:1"), _APP)
    assert vo_hinh == ["ltt_voice", "taoclipngan"]


def test_D006_them_lan_voice_thi_voice_het_vo_hinh(monkeypatch):
    import job_worker
    vo_hinh = job_worker.app_khong_lan_nao_nhat(
        _doi_hinh_tu(monkeypatch, "api:6, gpu:1, voice:1"), _APP)
    assert vo_hinh == ["taoclipngan"]
    vo_hinh = job_worker.app_khong_lan_nao_nhat(
        _doi_hinh_tu(monkeypatch, "api:6, gpu+ffmpeg:1, voice:1"), _APP)
    assert vo_hinh == []


def test_D006_worker_da_nang_va_app_tat_khong_bi_bao(monkeypatch):
    import job_worker
    monkeypatch.delenv("LTT_WORKER_POOLS", raising=False)
    assert job_worker.app_khong_lan_nao_nhat(job_worker._doi_hinh(), _APP) == []
    # `asv_voice` tắt ⇒ không báo dù không làn nào có `voice`.
    assert "asv_voice" not in job_worker.app_khong_lan_nao_nhat(
        _doi_hinh_tu(monkeypatch, "api:1"), _APP)
