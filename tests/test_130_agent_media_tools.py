from __future__ import annotations

import io
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest
from PIL import Image

from apps.mediatools.jobs import _safe_remote_url, _social_host, handle
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


def _mp4(path: Path, color: str) -> None:
    from platform_core.media import ffmpeg_bin
    result = subprocess.run([ffmpeg_bin(), "-y", "-f", "lavfi", "-i",
                             f"color=c={color}:s=160x96:d=0.7:r=12",
                             "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                             "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                             "-c:a", "aac", str(path)], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")


def test_asset_passthrough_chot_owner(storage):
    storage.put("agent-assets/u1/a.png", _png("red"), "image/png")
    result = handle({"owner_id": "u1", "image_key": "agent-assets/u1/a.png"}, Ctx())
    assert result["image_key"] == "agent-assets/u1/a.png"
    with pytest.raises(ValueError, match="không thuộc"):
        handle({"owner_id": "u2", "image_key": "agent-assets/u1/a.png"}, Ctx())


def test_asset_image_collection_preserves_order_owner_and_uniqueness(storage):
    storage.put("agent-assets/u1/a.png", _png("red"), "image/png")
    storage.put("agent-assets/u1/b.png", _png("blue"), "image/png")
    result = handle({"owner_id": "u1", "image_keys": [
        "agent-assets/u1/b.png", "agent-assets/u1/a.png"]}, Ctx())
    assert result["image_keys"] == ["agent-assets/u1/b.png", "agent-assets/u1/a.png"]
    with pytest.raises(ValueError, match="trùng"):
        handle({"owner_id": "u1", "image_keys": [
            "agent-assets/u1/a.png", "agent-assets/u1/a.png"]}, Ctx())


def test_merge_image_tao_artifact_that(storage):
    storage.put("agent-assets/u1/a.png", _png("red"), "image/png")
    storage.put("agent-assets/u1/b.png", _png("blue"), "image/png")
    result = handle({"owner_id": "u1", "images": ["agent-assets/u1/a.png",
                    "agent-assets/u1/b.png"], "layout": "horizontal"}, Ctx())
    assert storage.exists(result["image_key"])
    with storage.open(result["image_key"]) as stream:
        image = Image.open(stream)
        assert image.size == (48, 16)


def test_merge_video_va_extract_frames_tao_artifact_that(storage, tmp_path):
    from platform_core.media import duration_seconds
    first = tmp_path / "first.mp4"; second = tmp_path / "second.mp4"
    _mp4(first, "red"); _mp4(second, "blue")
    with first.open("rb") as stream:
        storage.put("agent-assets/u1/first.mp4", stream, "video/mp4")
    with second.open("rb") as stream:
        storage.put("agent-assets/u1/second.mp4", stream, "video/mp4")
    merged = handle({"owner_id": "u1", "videos": ["agent-assets/u1/first.mp4",
                     "agent-assets/u1/second.mp4"], "transition": "cut"}, Ctx())
    assert merged["source_count"] == 2 and storage.exists(merged["video_key"])
    exported = tmp_path / "merged.mp4"
    with storage.open(merged["video_key"]) as source, exported.open("wb") as target:
        target.write(source.read())
    assert duration_seconds(str(exported)) >= 1.2
    frames = handle({"owner_id": "u1", "video_key": merged["video_key"],
                     "interval_sec": 0.25, "max_frames": 3}, Ctx())
    assert frames["count"] == 3
    assert all(storage.exists(key) for key in frames["image_keys"])


def test_social_import_chan_ssrf(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *_args, **_kwargs:
                        [(None, None, None, None, ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="mạng nội bộ"):
        _safe_remote_url("https://example.com/video.mp4")


def test_social_platform_only_accepts_https_known_hosts():
    assert _social_host("https://www.youtube.com/shorts/abc") == "youtube.com"
    assert _social_host("https://vm.tiktok.com/abc") == "vm.tiktok.com"
    assert _social_host("https://instagram.com/reel/abc") == "instagram.com"
    assert _social_host("http://youtube.com/watch?v=x") == ""
    assert _social_host("https://youtube.com.evil.example/watch?v=x") == ""


def test_social_platform_download_is_bounded_owned_and_has_no_shell(monkeypatch, storage, tmp_path):
    captured = {}
    class FakeYDL:
        def __init__(self, options): captured.update(options); self.options = options
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def extract_info(self, _url, download=True):
            assert download is True
            output = Path(self.options["outtmpl"].replace("%(ext)s", "mp4"))
            output.write_bytes(b"fake-video")
            return {"duration": 8}
    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FakeYDL))
    monkeypatch.setattr("platform_core.media.duration_seconds", lambda _path: 8.0)
    result = handle({"owner_id": "u1", "url": "https://youtube.com/shorts/abc",
                     "confirm_rights": True}, Ctx())
    assert result["credit_cost"] == 2 and result["source"] == "social_platform"
    assert result["video_key"].startswith("mediatools/u1/")
    assert storage.exists(result["video_key"])
    assert captured["noplaylist"] is True and captured["max_downloads"] == 1
    assert "exec_cmd" not in captured and "netrc_cmd" not in captured
