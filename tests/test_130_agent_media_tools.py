from __future__ import annotations

import io

import pytest
from PIL import Image

from apps.mediatools.jobs import _safe_remote_url, handle
from platform_core.storage import LocalStorage, set_storage


class Ctx:
    job_id = "job-1"
    def progress(self, *_args):
        pass


@pytest.fixture()
def storage(tmp_path):
    value = LocalStorage(str(tmp_path / "files")); set_storage(value)
    yield value
    set_storage(None)


def _png(color: str) -> io.BytesIO:
    result = io.BytesIO(); Image.new("RGB", (24, 16), color).save(result, "PNG"); result.seek(0)
    return result


def test_asset_passthrough_chot_owner(storage):
    storage.put("agent-assets/u1/a.png", _png("red"), "image/png")
    result = handle({"owner_id": "u1", "image_key": "agent-assets/u1/a.png"}, Ctx())
    assert result["image_key"] == "agent-assets/u1/a.png"
    with pytest.raises(ValueError, match="không thuộc"):
        handle({"owner_id": "u2", "image_key": "agent-assets/u1/a.png"}, Ctx())


def test_merge_image_tao_artifact_that(storage):
    storage.put("agent-assets/u1/a.png", _png("red"), "image/png")
    storage.put("agent-assets/u1/b.png", _png("blue"), "image/png")
    result = handle({"owner_id": "u1", "images": ["agent-assets/u1/a.png",
                    "agent-assets/u1/b.png"], "layout": "horizontal"}, Ctx())
    assert storage.exists(result["image_key"])
    with storage.open(result["image_key"]) as stream:
        image = Image.open(stream)
        assert image.size == (48, 16)


def test_social_import_chan_ssrf(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *_args, **_kwargs:
                        [(None, None, None, None, ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="mạng nội bộ"):
        _safe_remote_url("https://example.com/video.mp4")
