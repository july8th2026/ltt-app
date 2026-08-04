from __future__ import annotations

import io

import pytest
from PIL import Image

from apps.taovideo.jobs import _reference_specs
from apps.taovideo.manifest import MANIFEST, _cost
from platform_core.storage import LocalStorage, set_storage


@pytest.fixture()
def storage(tmp_path):
    value = LocalStorage(str(tmp_path / "files")); set_storage(value)
    yield value
    set_storage(None)


def _png() -> io.BytesIO:
    output = io.BytesIO(); Image.new("RGB", (8, 6), "red").save(output, "PNG"); output.seek(0)
    return output


def test_video_tool_exposes_typed_media_inputs_and_prices_video_reference():
    spec = next(tool for tool in MANIFEST.tools if tool.name == "video.generate")
    assert spec.params_schema["image_key"]["type"] == "image"
    assert spec.params_schema["image_keys"]["type"] == "image[]"
    assert spec.params_schema["video_key"]["type"] == "video"
    assert spec.params_schema["audio_key"]["type"] == "audio"
    base = {"model": "seedance-2.0-mini", "resolution": "720p", "duration": 5}
    assert _cost({**base, "video_key": "$source.video_key"}) > 0
    assert _cost({**base, "video_key": "$source.video_key"}) != _cost(base)


def test_typed_and_legacy_references_share_owner_gate_dedupe_and_cap(storage):
    storage.put("agent-assets/u1/source.png", _png(), "image/png")
    storage.put("agent-assets/u1/clip.mp4", io.BytesIO(b"video"), "video/mp4")
    specs = _reference_specs({
        "image_key": "agent-assets/u1/source.png",
        "image_keys": ["agent-assets/u1/source.png"],
        "video_key": "agent-assets/u1/clip.mp4",
    }, "u1", storage)
    assert [(item["kind"], item["storage_key"]) for item in specs] == [
        ("image", "agent-assets/u1/source.png"),
        ("video", "agent-assets/u1/clip.mp4"),
    ]
    with pytest.raises(ValueError, match="không thuộc"):
        _reference_specs({"image_key": "agent-assets/u2/foreign.png"}, "u1", storage)
    with pytest.raises(ValueError, match="không còn"):
        _reference_specs({"image_key": "agent-assets/u1/missing.png"}, "u1", storage)


def test_video_reference_cap_is_enforced_after_dedupe(storage):
    keys = []
    for index in range(5):
        key = f"agent-assets/u1/{index}.png"; storage.put(key, _png(), "image/png"); keys.append(key)
    with pytest.raises(ValueError, match="tối đa 4"):
        _reference_specs({"image_keys": keys}, "u1", storage)
