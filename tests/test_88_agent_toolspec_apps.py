"""P2: ToolSpec của 7 app phải bám handler, giá và output đang chạy."""
from __future__ import annotations

import pytest

from platform_core.agent.tools import (ToolParamsError, discover_tools,
                                       resolve_params_schema,
                                       validate_tool_params)
from platform_core.registry import credit_for, discover


EXPECTED = {
    "text.script", "image.generate", "image.thumbnail", "video.generate",
    "video.subtitle", "video.upscale", "video.short_clips",
}


def test_dung_7_tool_job_based_duoc_discover():
    assert set(discover_tools()) == EXPECTED


def test_app_khong_phu_hop_khong_bi_ep_toolspec():
    manifests = {item.slug: item.manifest for item in discover()}
    assert manifests["demo"].tools == ()
    assert manifests["socialbot"].tools == ()
    assert manifests["chataistudio"].tools == ()


VALID_CASES = {
    "text.script": {
        "topic": "Cách làm phim ngắn",
        "duration": "3-5_phut", "tone": "educational",
        "audience": "general", "language": "vi",
    },
    "image.generate": {
        "prompt": "Một thành phố tương lai", "model": "gemini-2.5-flash-image",
        "aspect_ratio": "16:9", "count": 4,
    },
    "image.thumbnail": {
        "topic": "Du lịch Việt Nam", "model": "gemini-2.5-flash-image",
        "aspect_ratio": "16:9", "count": 1,
    },
    "video.generate": {
        "prompt": "Máy quay tiến qua khu rừng", "model": "seedance-2.0-mini",
        "resolution": "720p", "duration": 5, "aspect_ratio": "16:9",
        "generate_audio": True,
    },
    "video.subtitle": {
        "video_key": "$s1.video_key",
        "transcript": [{"start": 0, "end": 1, "text": "Xin chào"}],
        "style_id": "default", "quality": "standard",
    },
    "video.upscale": {
        "video_key": "$s1.video_key", "preset": "quality",
        "target_height": 2160, "codec": "hevc", "preview": False,
    },
    "video.short_clips": {
        "video_key": "$input.video", "tier": "high_quality",
        "genre": "talking_head", "aspect_ratio": "9:16", "language": "vi",
        "target_clip_count": 10, "min_clip_duration_sec": 15,
        "max_clip_duration_sec": 60,
    },
}


@pytest.mark.parametrize("tool_name", sorted(VALID_CASES))
def test_params_that_toi_thieu_toi_da_hop_le(tool_name):
    params = VALID_CASES[tool_name]
    validated = validate_tool_params(tool_name, params)
    assert all(validated[key] == value for key, value in params.items())


@pytest.mark.parametrize(("tool_name", "params"), [
    ("text.script", {"topic": "x", "duration": "khong-co"}),
    ("image.generate", {"prompt": "x", "model": "model-khong-co", "count": 1}),
    ("image.thumbnail", {"topic": "x", "model": "gemini-2.5-flash-image", "count": 5}),
    ("video.generate", {"prompt": "x", "model": "seedance-2.0-mini", "resolution": "4k"}),
    ("video.subtitle", {"video_key": "v", "transcript": [], "quality": "ultra"}),
    ("video.upscale", {"video_key": "v", "target_height": 9999}),
    ("video.short_clips", {"video_key": "v", "target_clip_count": 11}),
])
def test_enum_range_model_sai_bi_chan_truoc_submit(tool_name, params):
    with pytest.raises(ToolParamsError):
        validate_tool_params(tool_name, params)


@pytest.mark.parametrize("tool_name", sorted(VALID_CASES))
def test_gia_toolspec_dung_nguon_credit_hien_hanh(tool_name):
    tools = discover_tools()
    params = validate_tool_params(tool_name, VALID_CASES[tool_name])
    apps = discover()
    owner = next(a for a in apps if tools[tool_name] in a.manifest.tools)
    assert credit_for(tools[tool_name].job_type, params, apps) == owner.manifest.credit_cost(params)


RESULT_FIXTURES = {
    "text.script": {"script": {"title": "T", "hook": "H"}},
    "image.generate": {"image_keys": ["image/u/1.png"], "prompt": "p"},
    "image.thumbnail": {"image_keys": ["thumbnail/u/1.png"], "prompt": "p"},
    "video.generate": {"video_key": "taovideo/u/1.mp4"},
    "video.subtitle": {"video_key": "autosubvideo/u/1.mp4", "srt_key": "s", "ass_key": "a"},
    "video.upscale": {"video_key": "upscalevideo/u/1.mp4"},
    "video.short_clips": {"clips": [{"video_key": "taoclipngan/u/1.mp4"}]},
}


def _matches_port(value, port):
    if port in ("text", "image", "video", "audio", "model_ref"):
        return isinstance(value, str)
    if port in ("image[]", "video[]"):
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    return isinstance(value, (dict, list)) if port == "json" else False


@pytest.mark.parametrize("tool_name", sorted(RESULT_FIXTURES))
def test_result_fixture_khop_returns_handler(tool_name):
    spec = discover_tools()[tool_name]
    result = RESULT_FIXTURES[tool_name]
    assert all(name in result and _matches_port(result[name], port)
               for name, port in spec.returns.items())


def test_resolve_video_capability_theo_model():
    mini = resolve_params_schema("video.generate", {"model": "seedance-2.0-mini"})
    full = resolve_params_schema("video.generate", {"model": "seedance-2.0"})
    assert "4k" not in mini["resolution"]["values"]
    assert "4k" in full["resolution"]["values"]
