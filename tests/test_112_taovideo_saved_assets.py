"""H15.S4 TV-FEAT-001 — asset lịch sử owner-scoped và validation."""

import asyncio
import io
from pathlib import Path

import pytest
from starlette.datastructures import Headers, UploadFile


ROOT = Path(__file__).resolve().parents[1]


class _Storage:
    def __init__(self):
        self.files = {}

    def put(self, key, stream, content_type="application/octet-stream"):
        self.files[key] = (stream.read(), content_type)

    def exists(self, key):
        return key in self.files

    def size(self, key):
        return len(self.files[key][0])

    def open(self, key):
        return io.BytesIO(self.files[key][0])

    def delete(self, key):
        self.files.pop(key, None)


def _upload(name: str, content_type: str,
            data: bytes = b"\x00\x00\x00\x18ftypisommedia") -> UploadFile:
    return UploadFile(io.BytesIO(data), filename=name,
                      headers=Headers({"content-type": content_type}))


def test_upload_ref_luu_metadata_va_chuan_hoa_role(tmp_path, monkeypatch):
    from apps.taovideo.routes import _luu_refs
    import platform_core.db as dbmod
    # ⛔ PHAI import TRUOC `create_all`. `Base.metadata` rong cho toi khi module
    #    nay duoc nap; `create_all` tren mot metadata rong tao ZERO bang va
    #    khong ne mot tieng nao. Phep kiem nay tung xanh chi vi mot tep test
    #    KHAC chay truoc no trong cung tien trinh da nap ho — nen no do ngay
    #    khi chay mot minh, hoac khi xdist xep no len dau mot worker.
    import platform_core.models  # noqa: F401
    import platform_core.storage as storage_module
    from tests.conftest import bao_dam_user
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'stage-ref.db').as_posix()}")
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    bao_dam_user(db, "u1"); db.commit(); db.close()
    storage = _Storage()
    monkeypatch.setattr(storage_module, "get_storage", lambda: storage)
    try:
        refs = asyncio.run(_luu_refs(
            "u1", [_upload(r"C:\fake\clip.mp4", "video/mp4")],
            ["first_frame"], ["hero"],
        ))

        assert len(refs) == 1
        assert refs[0]["kind"] == "video"
        assert refs[0]["role"] == "reference_video"
        assert refs[0]["name"] == "clip.mp4"
        assert refs[0]["content_type"] == "video/mp4"
        assert refs[0]["size"] == 17
        assert refs[0]["storage_key"].startswith("staging/u1/taovideo/")
        assert refs[0]["upload_id"]
    finally:
        dbmod.reset_engine()


def test_upload_ref_tu_choi_mime_va_qua_bon_file(monkeypatch):
    from apps.taovideo.routes import _luu_refs
    import platform_core.storage as storage_module
    monkeypatch.setattr(storage_module, "get_storage", lambda: _Storage())

    with pytest.raises(ValueError, match="không hỗ trợ"):
        asyncio.run(_luu_refs("u1", [_upload("x.exe", "application/octet-stream")], []))
    with pytest.raises(ValueError, match="Tối đa 4"):
        asyncio.run(_luu_refs("u1", [_upload(f"{i}.png", "image/png") for i in range(5)], []))


def test_batch_invalid_khong_de_lai_file_da_luu(monkeypatch):
    from apps.taovideo.routes import _luu_refs
    import platform_core.storage as storage_module
    storage = _Storage()
    monkeypatch.setattr(storage_module, "get_storage", lambda: storage)

    with pytest.raises(ValueError, match="không hỗ trợ"):
        asyncio.run(_luu_refs("u1", [
            _upload("good.png", "image/png"),
            _upload("bad.exe", "application/octet-stream"),
        ], []))
    assert storage.files == {}


def test_saved_asset_chi_resolve_tu_lich_su_dung_owner(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'assets.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.storage as storage_module
    from apps.taovideo.routes import _saved_refs_for_user
    from platform_core.models import Job
    from platform_core.users import tao_nguoi_dung

    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    storage = _Storage()
    try:
        mine = tao_nguoi_dung(db, email="asset-mine@example.com",
                              password="matkhau-tot-12", is_verified=True)
        other = tao_nguoi_dung(db, email="asset-other@example.com",
                               password="matkhau-tot-12", is_verified=True)
        mine_key = f"taovideo/{mine.id}/refs/mine"
        other_key = f"taovideo/{other.id}/refs/other"
        storage.files[mine_key] = (b"mine", "image/png")
        storage.files[other_key] = (b"other", "image/png")
        db.add_all([
            Job(user_id=mine.id, app_slug="taovideo", job_type="taovideo.generate",
                params={"refs": [{"storage_key": mine_key, "kind": "image",
                                  "role": "first_frame", "handle": "hero"}]}),
            Job(user_id=other.id, app_slug="taovideo", job_type="taovideo.generate",
                params={"refs": [{"storage_key": other_key, "kind": "image"}]}),
        ])
        db.commit(); monkeypatch.setattr(storage_module, "get_storage", lambda: storage)

        assert _saved_refs_for_user(mine.id, [mine_key])[0]["role"] == "first_frame"
        with pytest.raises(ValueError, match="không hợp lệ"):
            _saved_refs_for_user(mine.id, [other_key])
    finally:
        try: next(gen)
        except StopIteration: pass
        dbmod.reset_engine()


def test_ui_co_asset_library_va_gioi_han_tong_bon():
    page = (ROOT / "apps/taovideo/templates/taovideo.html").read_text(encoding="utf-8")
    assert 'href="#tv-assets"' in page
    assert 'name="saved_ref_keys"' in page
    assert "function syncRefLimit()" in page
    assert "total>4" in page
    assert "Chưa có tài sản đã lưu" in page
