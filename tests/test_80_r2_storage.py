"""
H10 — R2 storage backend. Test không cần boto3 (nạp lười) + không cần R2 thật.

Khoá: `url_for` (Local=None, R2=presigned), chọn backend theo env, dựng R2 từ env.
"""
from __future__ import annotations

import pytest


def test_local_url_for_none(tmp_path):
    from platform_core.storage import LocalStorage
    s = LocalStorage(str(tmp_path))
    import io
    s.put("a/b.txt", io.BytesIO(b"x"))
    assert s.url_for("a/b.txt") is None       # Local → app tự serve


def test_r2_from_env_dung_endpoint(monkeypatch):
    from platform_core import storage
    monkeypatch.setenv("LTT_R2_ACCOUNT_ID", "acc123")
    monkeypatch.setenv("LTT_R2_ACCESS_KEY_ID", "akid")
    monkeypatch.setenv("LTT_R2_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("LTT_R2_BUCKET", "ltt")
    monkeypatch.delenv("LTT_R2_ENDPOINT", raising=False)
    r2 = storage._r2_from_env()
    assert r2.bucket == "ltt"
    assert r2._endpoint == "https://acc123.r2.cloudflarestorage.com"


def test_r2_from_env_thieu_thi_nem(monkeypatch):
    from platform_core import storage
    for k in ("LTT_R2_ACCOUNT_ID", "LTT_R2_ENDPOINT", "LTT_R2_ACCESS_KEY_ID",
              "LTT_R2_SECRET_ACCESS_KEY", "LTT_R2_BUCKET"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(storage.StorageError):
        storage._r2_from_env()


def test_r2_url_for_presigned(monkeypatch):
    from platform_core.storage import R2Storage
    r2 = R2Storage(bucket="ltt", endpoint_url="https://x.r2.cloudflarestorage.com",
                   access_key_id="a", secret_access_key="b")

    class _FakeClient:
        def generate_presigned_url(self, op, Params, ExpiresIn):  # noqa: N803
            assert op == "get_object" and Params["Bucket"] == "ltt"
            return f"https://signed/{Params['Key']}?e={ExpiresIn}"
    r2._client = _FakeClient()
    url = r2.url_for("taovideo/u1/j1/video.mp4", ttl_s=600)
    assert url.startswith("https://signed/taovideo/u1/j1/video.mp4?e=600")


def test_get_storage_chon_r2_theo_env(monkeypatch):
    from platform_core import storage
    monkeypatch.setenv("LTT_STORAGE", "r2")
    monkeypatch.setenv("LTT_R2_ACCOUNT_ID", "acc")
    monkeypatch.setenv("LTT_R2_ACCESS_KEY_ID", "akid")
    monkeypatch.setenv("LTT_R2_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("LTT_R2_BUCKET", "ltt")
    storage.set_storage(None)
    try:
        s = storage.get_storage()
        assert isinstance(s, storage.R2Storage)
    finally:
        storage.set_storage(None)
