"""Nội dung của job hết hạn; bằng chứng thì không.

Bản kiểm kê ở `governance.py` khai 42 store và có test bắt mỗi store phải nêu
một hàm dọn **có thật và được worker gọi**. Nhưng nó chỉ nhìn **bảng CSDL**. File
sinh ra không có store nào, không sweep nào, không cửa sổ tải về nào được công
bố — một API bán ảnh giữ mọi đầu ra vĩnh viễn. Bánh cóc tự tin vì nó đầy đủ trên
đúng nửa nó nhìn thấy.

Nên phép kiểm ở đây là **hành vi**, không phải danh sách: chạy thật, ghi file
thật, già hoá, quét, rồi hỏi kho lưu trữ xem còn gì không. Một danh sách khai
báo sẽ đúng cho tới khi ai đó thêm một chỗ ghi file mới; câu hỏi "kho còn gì
không" thì không lách được.
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'content.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session

    Base.metadata.create_all(get_engine())
    gen = get_session()
    session = next(gen)
    try:
        yield session, storage_mod.get_storage()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        storage_mod.set_storage(None)
        dbmod.reset_engine()


def _job_co_file(db, storage, *, so_file: int = 3, xong_cach_day_ngay: int = 60):
    """Một job đã xong, có file trong kho, theo đúng quy ước khoá của app."""
    from platform_core.models import JOB_DONE, Job

    job_id = str(uuid.uuid4())
    owner = "u-1"
    khoa = []
    for i in range(so_file):
        key = f"thumbnail/{owner}/{job_id}/{i}.png"
        storage.put(key, io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 100),
                    content_type="image/png")
        khoa.append(key)

    xong = datetime.now(timezone.utc) - timedelta(days=xong_cach_day_ngay)
    job = Job(id=job_id, user_id=owner, app_slug="thumbnail",
              job_type="thumbnail.generate",
              params={"topic": "bí mật của khách", "count": so_file},
              result={"image_keys": khoa, "prompt": "prompt đầy đủ của khách"},
              status=JOB_DONE, finished_at=xong, created_at=xong,
              next_run_at=xong)
    db.add(job)
    db.commit()
    return job, khoa


def _con_lai(storage, khoa) -> list:
    con = []
    for key in khoa:
        try:
            storage.open(key).close()
            con.append(key)
        except Exception:                   # noqa: BLE001
            pass
    return con


# ── Nhận diện khoá: sai theo hướng bỏ sót, không phải xoá nhầm ───────────────

def test_chi_nhan_khoa_co_id_cua_chinh_job(moi_truong):
    """Với một thao tác không hoàn tác được, chỉ có một hướng sai chấp nhận được.

    Nếu phép nhận dạng lỡ sai, cái tệ nhất được phép xảy ra là bỏ sót một file —
    không bao giờ là xoá file của job khác.
    """
    from platform_core import job_content
    from platform_core.models import Job

    job = Job(id="job-cua-toi", user_id="u", app_slug="thumbnail",
              job_type="t", params={},
              result={"cua_toi": "thumbnail/u/job-cua-toi/0.png",
                      "cua_nguoi_khac": "thumbnail/u/job-khac/0.png",
                      "khong_phai_khoa": "một câu mô tả bình thường"},
              status="done")
    khoa = job_content.content_keys(job)

    assert khoa == ["thumbnail/u/job-cua-toi/0.png"]


def test_khong_nhan_nham_url(moi_truong):
    """Một URL presigned trong `result` không phải khoá lưu trữ để xoá."""
    from platform_core import job_content
    from platform_core.models import Job

    job = Job(id="j1", user_id="u", app_slug="x", job_type="t", params={},
              result={"link": "https://cdn.example.com/x/u/j1/a.png"},
              status="done")
    assert job_content.content_keys(job) == []


def test_khoa_lap_lai_chi_dem_mot_lan(moi_truong):
    from platform_core import job_content
    from platform_core.models import Job

    job = Job(id="j1", user_id="u", app_slug="x", job_type="t",
              params={"nguon": "x/u/j1/a.png"},
              result={"ket_qua": "x/u/j1/a.png"}, status="done")
    assert job_content.content_keys(job) == ["x/u/j1/a.png"]


# ── Hành vi thật trên kho lưu trữ ────────────────────────────────────────────

def test_file_that_su_bien_mat(moi_truong):
    """Câu hỏi mà một danh sách khai báo không trả lời được."""
    from platform_core import job_content

    db, storage = moi_truong
    job, khoa = _job_co_file(db, storage)

    assert _con_lai(storage, khoa) == khoa, "dựng test hỏng: file chưa tồn tại"

    bao_cao = job_content.purge_expired(db, storage)
    db.commit()

    assert bao_cao == {"jobs": 1, "files": 3}
    assert _con_lai(storage, khoa) == [], "file vẫn còn sau khi hết hạn"


def test_bang_chung_o_lai_khi_noi_dung_ra_di(moi_truong):
    """Hàng job phải sống sót: bút toán credit trỏ về nó.

    Xoá hàng là làm một tranh chấp hoá đơn sáu tháng sau không trả lời được.
    """
    from platform_core import job_content
    from platform_core.models import Job

    db, storage = moi_truong
    job, _ = _job_co_file(db, storage)
    job_id = job.id

    job_content.purge_expired(db, storage)
    db.commit()

    con = db.get(Job, job_id)
    assert con is not None, "hàng job bị xoá mất"
    assert con.user_id == "u-1"
    assert con.job_type == "thumbnail.generate"
    assert con.status == "done"
    assert con.finished_at is not None


def test_noi_dung_cua_khach_khong_con_trong_hang(moi_truong):
    """Prompt là thứ khách viết ra; giữ mãi là một khoản nợ riêng tư."""
    from platform_core import job_content
    from platform_core.models import Job

    db, storage = moi_truong
    job, _ = _job_co_file(db, storage)
    job_id = job.id

    job_content.purge_expired(db, storage)
    db.commit()

    con = db.get(Job, job_id)
    assert con.params == {}
    assert con.result == {}
    assert "bí mật của khách" not in str(con.params)


def test_co_moc_de_phan_biet_het_han_voi_mat_du_lieu(moi_truong):
    """Một `result` rỗng không có lời giải thích sẽ bị đọc là mất dữ liệu."""
    from platform_core import job_content
    from platform_core.models import Job

    db, storage = moi_truong
    job, _ = _job_co_file(db, storage)
    job_id = job.id

    job_content.purge_expired(db, storage)
    db.commit()

    assert db.get(Job, job_id).content_expired_at is not None


def test_job_con_han_khong_bi_dung_toi(moi_truong):
    from platform_core import job_content

    db, storage = moi_truong
    job, khoa = _job_co_file(db, storage, xong_cach_day_ngay=3)

    bao_cao = job_content.purge_expired(db, storage)
    db.commit()

    assert bao_cao["jobs"] == 0
    assert _con_lai(storage, khoa) == khoa


def test_job_dang_chay_khong_bi_dung_toi(moi_truong):
    """Job chưa kết thúc còn cần chính `params` của nó để chạy được."""
    from platform_core import job_content
    from platform_core.models import JOB_QUEUED, Job

    db, storage = moi_truong
    cu = datetime.now(timezone.utc) - timedelta(days=90)
    job = Job(id=str(uuid.uuid4()), user_id="u-1", app_slug="thumbnail",
              job_type="thumbnail.generate", params={"topic": "vẫn cần"},
              status=JOB_QUEUED, created_at=cu, next_run_at=cu)
    db.add(job)
    db.commit()

    assert job_content.purge_expired(db, storage)["jobs"] == 0
    assert db.get(Job, job.id).params == {"topic": "vẫn cần"}


def test_quet_hai_lan_cho_ket_qua_giong_het(moi_truong):
    """Lượt thứ hai không được tính lại những job đã hết hạn."""
    from platform_core import job_content

    db, storage = moi_truong
    _job_co_file(db, storage)

    dau = job_content.purge_expired(db, storage)
    db.commit()
    sau = job_content.purge_expired(db, storage)
    db.commit()

    assert dau["jobs"] == 1
    assert sau["jobs"] == 0


def test_mot_file_khong_xoa_duoc_khong_chan_nhung_file_con_lai(moi_truong):
    """Và job vẫn phải được đánh dấu, nếu không lượt sau thử lại mãi."""
    from platform_core import job_content
    from platform_core.models import Job

    db, storage = moi_truong
    job, khoa = _job_co_file(db, storage)
    job_id = job.id

    that_bai = khoa[1]
    goc = storage.delete

    def _delete(key):
        if key == that_bai:
            raise OSError("file bi khoa")
        return goc(key)

    storage.delete = _delete
    job_content.purge_expired(db, storage)
    db.commit()
    storage.delete = goc

    assert db.get(Job, job_id).content_expired_at is not None
    assert _con_lai(storage, khoa) == [that_bai]


def test_worker_that_su_goi_vong_don_nay(moi_truong):
    """Một chính sách nêu tên một hàm không ai chạy thì tệ hơn không có chính sách.

    Đúng bài học EXT-19, và lần này là cho kho file.
    """
    import inspect

    from platform_core import job_runner

    nguon = inspect.getsource(job_runner._don_du_lieu_het_han)
    assert "_don_noi_dung_job" in nguon

    cau = inspect.getsource(job_runner._don_noi_dung_job)
    assert "job_content.purge_expired" in cau
