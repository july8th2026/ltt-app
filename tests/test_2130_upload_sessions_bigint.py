"""asv-final L_NO_KY_THUAT F-08 — `upload_sessions.expected_size`/`actual_size`
phải sống qua BigInteger, không còn kẹp ở 2 GiB-1 (giới hạn `int4`).

Không dùng dữ liệu > 2 GiB thật trên đĩa — chỉ cần cột CSDL giữ đúng số byte
khai báo qua một vòng ghi/đọc lại (round trip), đúng như `platform_core.models.
UploadSession.expected_size` khai bây giờ (BigInteger, xem migration
`d7bc2f8fbf0f`).
"""
from __future__ import annotations

import pytest

from tests.conftest import APP_THU_SLUG, bao_dam_user

#: 3 GiB — vượt trần `int4` (2 147 483 647) mà một cột Integer thường sẽ kẹp
#: hoặc tràn số khi ghi xuống PostgreSQL thật.
QUA_2GIB = 3 * 1024 * 1024 * 1024
assert QUA_2GIB > 2 ** 31 - 1


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'uploads_bigint.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    from platform_core.storage import LocalStorage, set_storage
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    storage = LocalStorage(str(tmp_path / "files")); set_storage(storage)
    gen = dbmod.get_session(); db = next(gen)
    try:
        bao_dam_user(db, "u1"); db.commit()
        yield db
    finally:
        db.close(); dbmod.reset_engine(); set_storage(None)


def test_expected_size_qua_2gib_song_qua_vong_ghi_doc_lai(env, monkeypatch):
    """create() voi expected_size > 2 GiB -> commit -> doc lai bang id moi:
    gia tri phai nguyen ven, khong bi kep/tran o bien int4.

    `MAX_ACTIVE_BYTES` (2 GiB/khach dang cho) la mot han muc NGHIEP VU rieng,
    khong lien quan F-08 (gioi han cot CSDL) - nang no len o day de phep nay
    chi do dung mot dieu: cot co giu nguyen gia tri hay khong."""
    from platform_core import upload_sessions
    from platform_core.models import UploadSession
    monkeypatch.setattr(upload_sessions, "MAX_ACTIVE_BYTES", QUA_2GIB * 2)
    db = env

    session = upload_sessions.create(
        db, user_id="u1", app_slug=APP_THU_SLUG, filename="phim-lon.mp4",
        content_type="video/mp4", expected_size=QUA_2GIB, max_size=QUA_2GIB,
        allowed_types=("video/mp4",),
    )
    db.commit()
    session_id = session.id
    db.expire_all()

    doc_lai = db.get(UploadSession, session_id)
    assert doc_lai is not None
    assert doc_lai.expected_size == QUA_2GIB


def test_actual_size_qua_2gib_song_qua_vong_ghi_doc_lai(env):
    """actual_size (dem byte da nhan) cung phai chiu duoc gia tri > 2 GiB —
    cung mot loai kep se xay ra khi mot phien tai len lon thuc su hoan tat."""
    from platform_core.models import UploadSession
    import uuid
    from datetime import datetime, timedelta, timezone
    db = env

    session = UploadSession(
        id=str(uuid.uuid4()), user_id="u1", app_slug=APP_THU_SLUG,
        staging_key=f"staging/u1/{APP_THU_SLUG}/x/payload.mp4",
        content_type="video/mp4", expected_size=QUA_2GIB, actual_size=QUA_2GIB,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(session); db.commit()
    session_id = session.id
    db.expire_all()

    doc_lai = db.get(UploadSession, session_id)
    assert doc_lai.actual_size == QUA_2GIB
