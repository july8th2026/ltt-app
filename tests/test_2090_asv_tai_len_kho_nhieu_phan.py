"""asv-final L_TAI_LEN — API tai len NHIEU PHAN cua `platform_core.storage`.

Hai backend PHAI cung ngu nghia: dev/test chay `LocalStorage`, production chay
`R2Storage`. Ca hai duoc chot o day — Local bang dia that, R2 bang `moto` (gia
lap S3 trong tien trinh, khong cham mang, khong cham bucket that).
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
from datetime import datetime, timedelta, timezone

import pytest

from platform_core.storage import (LocalStorage, R2Storage, RoutedStorage,
                                   StorageError)


def _md5(b: bytes) -> str:
    return base64.b64encode(hashlib.md5(b).digest()).decode()


KHOA = "staging/u1/auto_scan_video/s1/payload.mp4"


# ══════════════════════════════════════════════════════════════════════════════
#  LocalStorage
# ══════════════════════════════════════════════════════════════════════════════

def test_local_dut_giua_chung_roi_TIEP_TUC_ghep_dung_tung_byte(tmp_path):
    kho = LocalStorage(str(tmp_path))
    ds = [os.urandom(1000), os.urandom(1000), os.urandom(1000), os.urandom(123)]
    kho.multipart_create(KHOA, "video/mp4")
    for i in (1, 2):
        kho.multipart_put_part(KHOA, i, io.BytesIO(ds[i - 1]), _md5(ds[i - 1]), 1000)

    # "Mat mang" = mot doi tuong kho MOI (tien trinh khac / khoi dong lai).
    kho2 = LocalStorage(str(tmp_path))
    da = kho2.multipart_list_parts(KHOA)
    assert [p.part_number for p in da] == [1, 2]
    assert [p.size for p in da] == [1000, 1000]
    assert da[0].etag == hashlib.md5(ds[0]).hexdigest()

    for i in (3, 4):
        kho2.multipart_put_part(KHOA, i, io.BytesIO(ds[i - 1]), _md5(ds[i - 1]), 1000)
    ra = kho2.multipart_complete(KHOA, 4)
    goc = b"".join(ds)
    assert ra.size == len(goc)
    with kho2.open(KHOA) as fh:
        assert hashlib.sha256(fh.read()).hexdigest() == hashlib.sha256(goc).hexdigest()
    # Ghep xong thi phan tam bien mat.
    assert not kho2._mp_dir(KHOA).exists()


def test_local_MD5_sai_bi_tu_choi_va_phan_KHONG_duoc_ghi(tmp_path):
    kho = LocalStorage(str(tmp_path))
    kho.multipart_create(KHOA)
    b = os.urandom(500)
    with pytest.raises(StorageError):
        kho.multipart_put_part(KHOA, 1, io.BytesIO(b), _md5(b"khac"), 1000)
    assert kho.multipart_list_parts(KHOA) == []
    # Doi chung: dung MD5 thi nhan.
    kho.multipart_put_part(KHOA, 1, io.BytesIO(b), _md5(b), 1000)
    assert [p.part_number for p in kho.multipart_list_parts(KHOA)] == [1]


@pytest.mark.parametrize("md5", ["", "khong-phai-base64!", base64.b64encode(b"ngan").decode()])
def test_local_MD5_thieu_hoac_sai_dinh_dang_bi_tu_choi(tmp_path, md5):
    kho = LocalStorage(str(tmp_path))
    kho.multipart_create(KHOA)
    with pytest.raises(StorageError):
        kho.multipart_put_part(KHOA, 1, io.BytesIO(b"abc"), md5, 1000)


def test_local_phan_VUOT_tran_bi_tu_choi(tmp_path):
    kho = LocalStorage(str(tmp_path))
    kho.multipart_create(KHOA)
    b = os.urandom(1001)
    with pytest.raises(StorageError):
        kho.multipart_put_part(KHOA, 1, io.BytesIO(b), _md5(b), 1000)
    assert kho.multipart_list_parts(KHOA) == []


def test_local_ghep_khi_THIEU_phan_bi_tu_choi(tmp_path):
    kho = LocalStorage(str(tmp_path))
    kho.multipart_create(KHOA)
    for i in (1, 3):
        kho.multipart_put_part(KHOA, i, io.BytesIO(b"x" * 10), _md5(b"x" * 10), 10)
    with pytest.raises(StorageError):
        kho.multipart_complete(KHOA, 3)
    assert not kho.exists(KHOA)


def test_local_huy_xoa_phan_va_luot_khong_ton_tai_nua(tmp_path):
    kho = LocalStorage(str(tmp_path))
    kho.multipart_create(KHOA)
    kho.multipart_put_part(KHOA, 1, io.BytesIO(b"x"), _md5(b"x"), 10)
    assert kho.multipart_abort(KHOA) is True
    assert kho.multipart_abort(KHOA) is False
    with pytest.raises(StorageError):
        kho.multipart_list_parts(KHOA)
    with pytest.raises(StorageError):
        kho.multipart_put_part(KHOA, 1, io.BytesIO(b"x"), _md5(b"x"), 10)


def test_local_khong_cap_ve_truc_tiep(tmp_path):
    """Local tra None -> app nhan phan qua route cua no (hop dong nhu `put_url`)."""
    kho = LocalStorage(str(tmp_path))
    kho.multipart_create(KHOA)
    assert kho.multipart_part_url(KHOA, 1, _md5(b"x")) is None


# ══════════════════════════════════════════════════════════════════════════════
#  R2Storage (moto)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def r2(monkeypatch):
    moto = pytest.importorskip("moto")
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    with moto.mock_aws():
        kho = R2Storage(bucket="asv-thu", endpoint_url="https://s3.amazonaws.com",
                        access_key_id="a", secret_access_key="b", region="us-east-1")
        kho._c().create_bucket(Bucket="asv-thu")
        yield kho


MIB5 = 5 * 1024 * 1024


def test_r2_dut_roi_tiep_tuc_theo_KHOA_va_ghep_dung_byte(r2):
    ds = [os.urandom(MIB5), os.urandom(MIB5), os.urandom(777)]
    r2.multipart_create(KHOA, "video/mp4")
    r2.multipart_create(KHOA, "video/mp4")      # goi lai: TAI DUNG luot cu
    assert len(r2._c().list_multipart_uploads(Bucket="asv-thu")["Uploads"]) == 1
    r2.multipart_put_part(KHOA, 1, io.BytesIO(ds[0]), _md5(ds[0]), MIB5)

    # Tien trinh khac: khong co gi trong RAM, van tim ra luot bang khoa.
    kho2 = R2Storage(bucket="asv-thu", endpoint_url="https://s3.amazonaws.com",
                     access_key_id="a", secret_access_key="b", region="us-east-1")
    assert [(p.part_number, p.size) for p in kho2.multipart_list_parts(KHOA)] == [(1, MIB5)]
    for i in (2, 3):
        kho2.multipart_put_part(KHOA, i, io.BytesIO(ds[i - 1]), _md5(ds[i - 1]), MIB5)
    kho2.multipart_complete(KHOA, 3)
    body = r2._c().get_object(Bucket="asv-thu", Key=KHOA)["Body"].read()
    assert hashlib.sha256(body).hexdigest() == hashlib.sha256(b"".join(ds)).hexdigest()


def test_r2_ve_phan_KY_content_md5(r2):
    """Toan ven o production: `content-md5` nam trong chu ky, nen trinh duyet
    phai gui dung header va R2 tu kiem than phan."""
    r2.multipart_create(KHOA, "video/mp4")
    ve = r2.multipart_part_url(KHOA, 2, _md5(b"abc"), ttl_s=600)
    assert ve is not None and ve.method == "PUT"
    assert ve.headers == {"Content-MD5": _md5(b"abc")}
    assert "partNumber=2" in ve.url and "uploadId=" in ve.url
    assert "content-md5" in ve.url.split("X-Amz-SignedHeaders=")[1].split("&")[0]
    # Khong bao gio mang token CSRF hay gi khac sang kho.
    assert "csrf" not in ve.url.lower()


def test_r2_kho_TU_CHOI_phan_co_MD5_khong_khop(r2):
    """Cung phep kiem ma R2 lam voi ve da ky: than khac MD5 khai -> BadDigest."""
    b = os.urandom(MIB5)
    r2.multipart_create(KHOA)
    with pytest.raises(StorageError):
        r2.multipart_put_part(KHOA, 1, io.BytesIO(b), _md5(b"khac"), MIB5)
    assert r2.multipart_list_parts(KHOA) == []


def test_r2_ve_phan_tu_choi_md5_sai_dinh_dang(r2):
    r2.multipart_create(KHOA)
    with pytest.raises(StorageError):
        r2.multipart_part_url(KHOA, 1, "khong-hop-le")


def test_r2_ghep_thieu_phan_bi_tu_choi_va_huy_don_sach(r2):
    b = os.urandom(MIB5)
    r2.multipart_create(KHOA)
    r2.multipart_put_part(KHOA, 1, io.BytesIO(b), _md5(b), MIB5)
    with pytest.raises(StorageError):
        r2.multipart_complete(KHOA, 2)
    assert r2.multipart_abort(KHOA) is True
    assert r2.multipart_abort(KHOA) is False
    assert r2._c().list_multipart_uploads(Bucket="asv-thu").get("Uploads", []) == []
    with pytest.raises(StorageError):
        r2.multipart_list_parts(KHOA)


# ══════════════════════════════════════════════════════════════════════════════
#  RoutedStorage + bo don cua nen tang
# ══════════════════════════════════════════════════════════════════════════════

def test_routed_uy_quyen_nhieu_phan_theo_tien_to(tmp_path):
    chinh = LocalStorage(str(tmp_path / "chinh"))
    cuc_bo = LocalStorage(str(tmp_path / "cuc_bo"))
    kho = RoutedStorage(chinh=chinh, cuc_bo=cuc_bo, tien_to=("voice/",))
    kho.multipart_create(KHOA)
    kho.multipart_put_part(KHOA, 1, io.BytesIO(b"ab"), _md5(b"ab"), 10)
    assert [p.part_number for p in chinh.multipart_list_parts(KHOA)] == [1]
    kho.multipart_complete(KHOA, 1)
    assert chinh.exists(KHOA) and not cuc_bo.exists(KHOA)


def test_sweep_HUY_luot_nhieu_phan_bo_do(tmp_path, monkeypatch):
    """Bo don cua nen tang (`upload_sessions.sweep`) phai huy phan dang do —
    `delete(key)` khong cham toi chung, va tren R2 chung bi tinh tien."""
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'd.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core import upload_sessions
    from platform_core.models import UPLOAD_DELETED
    from platform_core.users import tao_nguoi_dung
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    try:
        u = tao_nguoi_dung(db, email="sweep@example.com", password="Strong-pass-123",
                           is_verified=True)
        kho = LocalStorage(str(tmp_path / "f"))
        s = upload_sessions.create(
            db, user_id=u.id, app_slug="auto_scan_video", filename="a.mp4",
            content_type="video/mp4", expected_size=100, max_size=1000,
            allowed_types=("video/mp4",), ttl_s=60)
        kho.multipart_create(s.staging_key)
        kho.multipart_put_part(s.staging_key, 1, io.BytesIO(b"x"), _md5(b"x"), 10)
        bao = upload_sessions.sweep(
            db, kho, now=datetime.now(timezone.utc) + timedelta(hours=1), dry_run=False)
        assert bao["deleted"] == 1 and bao["errors"] == 0
        assert s.status == UPLOAD_DELETED
        assert not kho._mp_dir(s.staging_key).exists()
    finally:
        db.close()
        dbmod.reset_engine()
