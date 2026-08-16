"""Xoá nội dung job trên R2 — kho lưu trữ mà production thật sự dùng.

`test_218` chứng minh file bị xoá thật, nhưng trên `LocalStorage`. Production
chạy `LTT_STORAGE=r2`, nên lời hứa "file hết hạn sau 30 ngày" **chưa được chứng
minh ở nơi nó phải đúng** — và nếu `R2Storage.delete` hỏng im lặng thì CSDL vẫn
ghi "đã hết hạn" trong khi file còn nguyên, tức đúng kiểu sai mà cả đợt việc này
sinh ra để đóng.

Có một lý do **cấu trúc** khiến đường này chưa bao giờ được kiểm: `boto3` chỉ nằm
trong venv của máy chủ, không có ở Python chạy bộ test. Một đường code mà bộ test
không import nổi thì không phải "chưa ai viết test" — nó là *không thể* có test,
cho tới khi ai đó nhận ra.

Nên ở đây có hai tầng, và tầng nào chứng minh được gì thì nói rõ tầng đó:

* **Luôn chạy** — nối dây: `R2Storage.delete` gọi `delete_object` đúng bucket,
  đúng key, và `expire_content` coi khoá đã biến mất là đã xoá (R2 **không** báo
  lỗi khi xoá key không tồn tại, khác `LocalStorage`).
* **Chạy khi có `LTT_TEST_R2_BUCKET`** — thật: ghi lên R2 thật rồi xoá, và hỏi
  lại chính R2 xem còn không.

Tầng hai **cố ý không tự chạy với bucket production**: token R2 của triển khai
này chỉ có quyền trên đúng một bucket, và tên bucket cho thấy nó có thể dùng
chung với hệ thống khác đang phục vụ người thật. Ghi vào đó — dù chỉ vài byte
dưới một tiền tố riêng — là quyết định của chủ sản phẩm, không phải của test.
"""
from __future__ import annotations

import io
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest


# ── Tầng 1: nối dây, luôn chạy ───────────────────────────────────────────────

class _S3Gia:
    """Client S3 giả, ghi lại đúng những lời gọi đã phát ra."""

    def __init__(self):
        self.da_xoa: list = []
        self.da_ghi: list = []

    def delete_object(self, Bucket, Key):       # noqa: N803 - chữ ký boto3
        self.da_xoa.append((Bucket, Key))
        return {}

    def put_object(self, **kw):
        self.da_ghi.append(kw.get("Key"))
        return {}


@pytest.fixture()
def r2_gia(monkeypatch):
    from platform_core import storage as storage_mod

    kho = storage_mod.R2Storage.__new__(storage_mod.R2Storage)
    kho.bucket = "bucket-gia"
    gia = _S3Gia()
    monkeypatch.setattr(type(kho), "_c", lambda self: gia, raising=False)
    return kho, gia


def test_r2_xoa_dung_bucket_va_dung_key(r2_gia):
    """Sai bucket hoặc sai key thì file không bao giờ biến mất, và không ai báo."""
    kho, gia = r2_gia
    kho.delete("thumbnail/u-1/job-9/0.png")

    assert gia.da_xoa == [("bucket-gia", "thumbnail/u-1/job-9/0.png")]


def test_r2_khong_bao_loi_khi_key_da_bien_mat(r2_gia):
    """Khác `LocalStorage`: S3 coi xoá một key không tồn tại là thành công.

    `expire_content` dựa vào điều đó — nó đếm "đã xoá" cho cả trường hợp file
    vốn đã không còn, vì kết quả mong muốn đã đạt. Nếu R2 ném lỗi ở đây thì mỗi
    lượt quét lại sẽ log một vệt lỗi cho những file đã dọn từ lần trước.
    """
    kho, _gia = r2_gia
    kho.delete("khong/ton/tai.png")         # không được ném


def test_het_han_noi_dung_goi_dung_cac_khoa_cua_job_len_r2(tmp_path, r2_gia,
                                                           monkeypatch):
    """Ghép hai phần: chọn khoá (neo theo id job) và xoá (qua R2)."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'r2.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core import job_content
    from platform_core.db import Base, get_engine, get_session
    from platform_core.models import JOB_DONE, Job

    Base.metadata.create_all(get_engine())
    kho, gia = r2_gia

    gen = get_session()
    db = next(gen)
    try:
        job_id = str(uuid.uuid4())
        xong = datetime.now(timezone.utc) - timedelta(days=60)
        khoa = [f"thumbnail/u-1/{job_id}/{i}.png" for i in range(3)]
        db.add(Job(id=job_id, user_id="u-1", app_slug="thumbnail",
                   job_type="thumbnail.generate",
                   params={"topic": "bí mật"},
                   result={"image_keys": khoa},
                   status=JOB_DONE, finished_at=xong, created_at=xong,
                   next_run_at=xong))
        db.commit()

        bao_cao = job_content.purge_expired(db, kho)
        db.commit()

        assert bao_cao == {"jobs": 1, "files": 3}
        assert [k for _b, k in gia.da_xoa] == khoa
        assert db.get(Job, job_id).content_expired_at is not None
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


# ── Tầng 2: R2 thật, chỉ chạy khi được chỉ định bucket ───────────────────────

BUCKET = (os.environ.get("LTT_TEST_R2_BUCKET") or "").strip()
r2_that = pytest.mark.skipif(
    not BUCKET,
    reason=("Đặt LTT_TEST_R2_BUCKET (bucket VỨT ĐI, không phải bucket "
            "production) để chạy phần này. Xem docstring: bucket của triển "
            "khai này có thể dùng chung với hệ thống khác."))


@r2_that
def test_ghi_len_r2_that_roi_xoa_va_hoi_lai(tmp_path, monkeypatch):
    """Phép đo duy nhất chứng minh được lời hứa 30 ngày trên kho thật.

    Hỏi lại chính R2 chứ không tin giá trị trả về: một `delete_object` trả 200
    mà vẫn để file lại là đúng kiểu hỏng im lặng cần loại trừ ở đây.
    """
    monkeypatch.setenv("LTT_R2_BUCKET", BUCKET)
    monkeypatch.setenv("LTT_STORAGE", "r2")

    from platform_core import storage as storage_mod

    storage_mod.set_storage(None)
    kho = storage_mod.get_storage()
    assert isinstance(kho, storage_mod.R2Storage), (
        f"mong đợi R2Storage, nhận {type(kho).__name__}")

    key = f"h36-selftest/{uuid.uuid4().hex}/anh.png"
    kho.put(key, io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 64),
            content_type="image/png")

    kho.open(key).close()                   # có thật trước khi xoá
    kho.delete(key)

    with pytest.raises(Exception):          # noqa: B017 - đã biến mất thật
        kho.open(key).close()

    storage_mod.set_storage(None)
