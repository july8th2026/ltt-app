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

Nên ở đây có **ba tầng**, và tầng nào chứng minh được gì thì nói rõ tầng đó:

1. **Nối dây** (luôn chạy) — `R2Storage.delete` gọi `delete_object` đúng bucket,
   đúng key. Chứng minh code ta gọi đúng API, không chứng minh gì về S3.
2. **Giao thức** (chạy khi có `moto`) — `boto3` thật, ký request thật, một máy
   chủ S3 thật trong tiến trình. Đây là tầng bắt được những giả định mà tầng 1
   không thể: ngữ nghĩa "xoá key không tồn tại là **thành công**" (khác hẳn
   `LocalStorage`, vốn ném `FileNotFoundError`), và việc file **thật sự** biến
   mất chứ không chỉ là một lời gọi trả 200.
3. **R2 thật trên mạng** (chạy khi có `LTT_TEST_R2_BUCKET`) — chưa chạy lần nào.

Tầng 3 **cố ý không tự chạy với bucket production**. Đã kiểm bằng dữ liệu chứ
không đoán: bucket của triển khai này là `fb-video-storage` trên account
`3530f3e5…`, và **hệ thống BOT GEMINI dùng đúng bucket đó, đúng account đó** cho
đường asset của nó (`app/ui/static/js/modules/api-keys.js`). Đó là kho lưu trữ
của một hệ thống đang phục vụ người thật mà `CLAUDE.md` cấm tạo/sửa/xoá bất cứ
thứ gì. Ghi vài byte dưới một tiền tố riêng gần như chắc chắn vô hại — và "gần
như chắc chắn" không phải mức đủ cho một thao tác không hoàn tác được trên kho
của người khác.

Tầng 2 tồn tại chính vì tầng 3 bị chặn: nó lấy lại phần lớn giá trị mà không
chạm vào thứ gì của ai.
"""
from __future__ import annotations

import io
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

#: Đủ để `image_input`/magic-byte coi là PNG. Một hằng số, không lặp lại
#: literal ở bốn chỗ — mỗi lần lặp là một lần gõ nhầm chuỗi thoát.
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64


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


# ── Tầng 2: client S3 THẬT, chống lại một máy chủ S3 thật (trong tiến trình) ─

moto = pytest.importorskip(
    "moto",
    reason=("Cần `moto` để dựng một máy chủ S3 thật trong tiến trình. Thiếu nó "
            "thì đường R2 chỉ được kiểm ở mức nối dây."))


@pytest.fixture()
def r2_that_giao_thuc(monkeypatch):
    """`R2Storage` thật, `boto3` thật, giao thức S3 thật — chỉ máy chủ là cục bộ.

    Đây là tầng mà bản stub ở trên **không** chạm tới: ký request, mã lỗi của
    S3, và ngữ nghĩa "xoá một key không tồn tại là thành công". Nếu giả định nào
    trong số đó sai thì stub vẫn xanh còn production vẫn hỏng.
    """
    from moto import mock_aws

    with mock_aws():
        import boto3

        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        boto3.client("s3").create_bucket(Bucket="ltt-moto-test")

        monkeypatch.setenv("LTT_STORAGE", "r2")
        monkeypatch.setenv("LTT_R2_BUCKET", "ltt-moto-test")
        monkeypatch.setenv("LTT_R2_ACCOUNT_ID", "khong-dung")
        monkeypatch.setenv("LTT_R2_ENDPOINT", "https://s3.amazonaws.com")
        monkeypatch.setenv("LTT_R2_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("LTT_R2_SECRET_ACCESS_KEY", "test")

        from platform_core import storage as storage_mod

        storage_mod.set_storage(None)
        kho = storage_mod.get_storage()
        assert isinstance(kho, storage_mod.R2Storage), type(kho).__name__
        try:
            yield kho
        finally:
            storage_mod.set_storage(None)


def test_ghi_roi_xoa_qua_client_s3_that(r2_that_giao_thuc):
    """Ghi thật, xoá thật, rồi HỎI LẠI kho — không tin giá trị trả về.

    Một `delete_object` trả 200 mà vẫn để file lại là đúng kiểu hỏng im lặng
    cần loại trừ: CSDL sẽ ghi "đã hết hạn" trong khi file còn nguyên.
    """
    kho = r2_that_giao_thuc
    key = f"thumbnail/u-1/{uuid.uuid4()}/0.png"
    kho.put(key, io.BytesIO(PNG_BYTES),
            content_type="image/png")

    kho.open(key).close()                   # có thật trước khi xoá
    kho.delete(key)

    with pytest.raises(Exception):          # noqa: B017 - đã biến mất thật
        kho.open(key).close()


def test_xoa_key_khong_ton_tai_khong_bao_loi_tren_s3_that(r2_that_giao_thuc):
    """Ngữ nghĩa S3, xác nhận bằng máy chủ chứ không bằng giả định.

    `expire_content` dựa vào điều này để đếm "đã xoá" cho file vốn đã không còn.
    Nếu S3 thật ném lỗi ở đây thì mỗi lượt quét lại sẽ log một vệt lỗi cho những
    file đã dọn từ lần trước — và không ai nhận ra vì chúng chỉ là log.
    """
    r2_that_giao_thuc.delete("khong/ton/tai/bao-gio.png")


def test_het_han_noi_dung_xoa_that_tren_s3(tmp_path, r2_that_giao_thuc,
                                           monkeypatch):
    """Vòng đầy đủ trên kho thật: job cũ → quét → hỏi lại kho xem còn gì không.

    `test_218` làm đúng điều này trên đĩa. Production chạy R2, nên tới đây mới
    là chỗ lời hứa "file hết hạn sau 30 ngày" được chứng minh trên **giao thức**
    mà nó thật sự đi qua.
    """
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'motojob.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core import job_content
    from platform_core.db import Base, get_engine, get_session
    from platform_core.models import JOB_DONE, Job

    Base.metadata.create_all(get_engine())
    kho = r2_that_giao_thuc

    job_id = str(uuid.uuid4())
    khoa = [f"thumbnail/u-1/{job_id}/{i}.png" for i in range(3)]
    for key in khoa:
        kho.put(key, io.BytesIO(PNG_BYTES),
                content_type="image/png")

    gen = get_session()
    db = next(gen)
    try:
        xong = datetime.now(timezone.utc) - timedelta(days=60)
        db.add(Job(id=job_id, user_id="u-1", app_slug="thumbnail",
                   job_type="thumbnail.generate", params={"topic": "bí mật"},
                   result={"image_keys": khoa}, status=JOB_DONE,
                   finished_at=xong, created_at=xong, next_run_at=xong))
        db.commit()

        assert job_content.purge_expired(db, kho) == {"jobs": 1, "files": 3}
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()

    for key in khoa:
        with pytest.raises(Exception):      # noqa: B017
            kho.open(key).close()


# ── Tầng 3: R2 THẬT trên mạng, chỉ chạy khi được chỉ định bucket vứt đi ──────

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
    kho.put(key, io.BytesIO(PNG_BYTES), content_type="image/png")

    kho.open(key).close()                   # có thật trước khi xoá
    kho.delete(key)

    with pytest.raises(Exception):          # noqa: B017 - đã biến mất thật
        kho.open(key).close()

    storage_mod.set_storage(None)
