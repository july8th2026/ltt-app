"""Trần thời gian chạy một job, và tiến trình con được thay thế khi chết.

Nhặt job mồ côi chỉ bắt worker **chết** — mất đập nhịp. Một job **treo** mà vẫn
đập nhịp thì giữ slot vô hạn, và với đội hình vài tiến trình thì vài job như vậy
là dừng cả nền tảng: im lặng, không job nào hỏng, không ai được báo.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'runtime.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session

    Base.metadata.create_all(get_engine())
    gen = get_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


# ── Trần đến từ đâu ──────────────────────────────────────────────────────────

def test_app_khong_khai_thi_van_co_tran():
    """Không có trần mới là mặc định nguy hiểm.

    Nó im lặng cho tới đúng ngày một job treo thật, và ngày đó thì không ai
    đang ngồi đọc code để nhận ra thiếu sót.
    """
    from platform_core.job_runner import _tran_thoi_gian

    assert _tran_thoi_gian("thumbnail", "thumbnail.generate") > 0


def test_app_khai_thi_lay_cua_app():
    from platform_core.registry import AppManifest

    m = AppManifest(slug="x", display_name="X", route_prefix="/x",
                    max_runtime_s={"x.slow": 7200})
    assert m.runtime_limit_for("x.slow", default=60) == 7200
    assert m.runtime_limit_for("x.khac", default=60) == 60


def test_job_gpu_duoc_tran_rong_hon_job_goi_mang():
    """Trần là chốt chặn cho job treo, không phải hạn mức hiệu năng.

    Một job GPU dựng video dài thật sự chạy lâu; một lời gọi nhà cung cấp thì
    không. Cùng một con số cho cả hai nghĩa là hoặc giết oan cái đầu, hoặc thả
    lỏng cái sau.
    """
    from platform_core.job_runner import (RUNTIME_LIMIT_S,
                                          _tran_thoi_gian)

    assert RUNTIME_LIMIT_S["gpu"] > RUNTIME_LIMIT_S["api"]
    assert (_tran_thoi_gian("upscalevideo", "upscalevideo.render")
            > _tran_thoi_gian("thumbnail", "thumbnail.generate"))


# ── Đồng hồ ──────────────────────────────────────────────────────────────────

def test_job_xong_som_thi_dong_ho_bi_tat(monkeypatch):
    """Quên tắt đồng hồ = đồng hồ canh giờ thành đồng hồ hẹn giờ tự sát.

    Một job chạy xong trong năm giây vẫn sẽ giết tiến trình khi tới hạn, và
    triệu chứng (worker tự khởi động lại lúc rảnh) trông chẳng liên quan gì tới
    nguyên nhân.
    """
    import platform_core.job_runner as jr

    no = {"n": 0}
    monkeypatch.setattr(jr, "_het_gio",
                        lambda *a, **k: no.__setitem__("n", no["n"] + 1))
    monkeypatch.setattr(jr, "_tran_thoi_gian", lambda *a, **k: 0.05)

    import time
    with jr._canh_gio("job-1", "thumbnail", "thumbnail.generate"):
        pass
    time.sleep(0.2)

    assert no["n"] == 0, "đồng hồ vẫn nổ sau khi job đã xong"


def test_job_qua_han_thi_dong_ho_no(monkeypatch):
    import platform_core.job_runner as jr

    no = {"n": 0}
    monkeypatch.setattr(jr, "_het_gio",
                        lambda *a, **k: no.__setitem__("n", no["n"] + 1))
    monkeypatch.setattr(jr, "_tran_thoi_gian", lambda *a, **k: 0.05)

    import time
    with jr._canh_gio("job-1", "thumbnail", "thumbnail.generate"):
        time.sleep(0.3)

    assert no["n"] == 1


def test_tran_bang_khong_thi_khong_dat_dong_ho(monkeypatch):
    """Tắt hẳn phải là một lựa chọn tường minh, không phải một tai nạn."""
    import platform_core.job_runner as jr

    monkeypatch.setattr(jr, "_tran_thoi_gian", lambda *a, **k: 0)
    with jr._canh_gio("job-1", "thumbnail", "thumbnail.generate") as tran:
        assert tran == 0


# ── Không thử lại một job treo ───────────────────────────────────────────────

def test_job_vuot_tran_khong_duoc_thu_lai(db):
    """Thử lại một job treo chỉ tiêu thêm một slot rồi treo tiếp, ba lần."""
    import uuid
    from datetime import datetime, timezone

    from platform_core import jobs as jobq
    from platform_core.models import JOB_ERROR, JOB_RUNNING, Job

    job = Job(id=str(uuid.uuid4()), user_id="u-1", app_slug="thumbnail",
              job_type="thumbnail.generate", params={}, status=JOB_RUNNING,
              max_attempts=3, attempts=0,
              next_run_at=datetime.now(timezone.utc),
              created_at=datetime.now(timezone.utc))
    db.add(job)
    db.commit()

    jobq.fail(db, job, "Job vuot tran thoi gian chay (60s).", retry=False)
    db.commit()

    assert job.status == JOB_ERROR, "job treo vẫn được xếp chạy lại"


def test_that_bai_thuong_van_duoc_thu_lai(db):
    """Không được biến mọi thất bại thành vĩnh viễn khi thêm `retry=False`."""
    import uuid
    from datetime import datetime, timezone

    from platform_core import jobs as jobq
    from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job

    job = Job(id=str(uuid.uuid4()), user_id="u-1", app_slug="thumbnail",
              job_type="thumbnail.generate", params={}, status=JOB_RUNNING,
              max_attempts=3, attempts=0,
              next_run_at=datetime.now(timezone.utc),
              created_at=datetime.now(timezone.utc))
    db.add(job)
    db.commit()

    jobq.fail(db, job, "mang chap chon")
    db.commit()

    assert job.status == JOB_QUEUED


# ── Cha thay thế con ─────────────────────────────────────────────────────────

def test_cha_biet_nang_luc_cua_tung_vi_tri_de_thay_dung_lop(monkeypatch):
    """Thay một con GPU bằng worker đa năng là lặng lẽ đổi đội hình.

    Đội hình là thứ người vận hành khai; nền tảng không được tự sửa nó khi đang
    chữa một sự cố khác.
    """
    import job_worker

    monkeypatch.setenv("LTT_WORKER_POOLS", "api:2, gpu:1")
    doi_hinh = job_worker._doi_hinh()

    nhan = []
    for nang_luc, so in doi_hinh:
        for _ in range(so):
            nhan.append(nang_luc)

    assert len(nhan) == 3
    assert nhan[0] == nhan[1] == {"api"}
    assert "gpu" in nhan[2]
