"""P2: ToolSpec public phải bám handler, giá và output đang chạy."""
from __future__ import annotations

import pytest

from platform_core.agent.tools import (ToolParamsError, discover_tools,
                                       resolve_params_schema,
                                       validate_tool_params)
from platform_core.registry import credit_for, discover


EXPECTED = {
    "text.script", "image.generate", "image.thumbnail", "video.generate",
    "video.subtitle", "video.upscale", "video.short_clips",
    "text.generate", "image.batch_generate",
    "asset.image", "asset.images", "asset.video", "asset.audio", "video.extract_frames",
    "media.merge_image", "media.merge_video",
    "audio.generate", "video.social_import", "image.upscale",
    "text.prompt_package", "story.storyboard",
    # Model anh NOI BO (H37/Q102). No vao bang nay vi `discover_tools()` lay MOI
    # ToolSpec job-based — khong phai vi ai do quyet dinh mo no cho Agent. Ba cong
    # fail-closed cua Q92 va cong `is_active` cua H37 khong bi anh huong.
    "image.ltt",
    # Model NGON NGU noi bo (H38/Q106). Cung ly do: `discover_tools()` lay MOI
    # ToolSpec job-based.
    #
    # 🔴 NHUNG HE QUA O DAY KHAC, va phai noi ra: `planner.py` goi thang
    #    `discover_tools()`, KHONG co allowlist rieng. Nen tu luc nay Agent noi
    #    bo CO THE tu chon `text.chat` — tuc la mot luot chay Agent (von da chay
    #    tren mot LLM) co the tao them mot job LLM nua va tinh tien khach lan hai.
    #
    #    Do khong hien nhien la sai: model nha re hon `text.generate` (Gemini),
    #    nen Agent chon no co the la lua chon dung. Nhung no la mot HANH VI MOI,
    #    khong phai mot dong trong bang test.
    #
    # ⛔ Neu sau nay muon giu Agent tranh xa tool nay thi CHO SUA la mot allowlist
    #    o phia Agent, KHONG phai bang nay. Bang nay chi chep lai `discover_tools()`
    #    tra ve gi; sua no de "chan" Agent la sua cai nhiet ke.
    "text.chat",
}


def test_dung_toan_bo_tool_job_based_duoc_discover():
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
    "text.generate": {"prompt": "Viết một đoạn giới thiệu", "model": "gemini-2.5-flash",
                      "format": "markdown"},
    "image.generate": {
        "prompt": "Một thành phố tương lai", "model": "gemini-2.5-flash-image",
        "aspect_ratio": "16:9", "count": 4,
    },
    "image.batch_generate": {
        "prompt": "Bốn góc máy của một sản phẩm", "model": "gemini-2.5-flash-image",
        "aspect_ratio": "1:1", "count": 4,
    },
    "asset.image": {"image_key": "$input.image"},
    "asset.images": {"image_keys": ["agent-assets/u/1.png", "agent-assets/u/2.png"]},
    "asset.video": {"video_key": "$input.video"},
    "asset.audio": {"audio_key": "$input.audio"},
    "video.extract_frames": {"video_key": "$input.video", "interval_sec": 2,
                             "max_frames": 12},
    "media.merge_image": {"images": ["$s1.image_key", "$s2.image_key"], "layout": "grid"},
    "media.merge_video": {"videos": ["$s1.video_key", "$s2.video_key"], "transition": "cut"},
    "audio.generate": {"text": "Xin chào", "model": "gemini-2.5-flash-preview-tts",
                       "voice": "Kore", "style": "Natural"},
    "video.social_import": {"url": "https://cdn.example.com/owned.mp4", "confirm_rights": True},
    "image.upscale": {"image_key": "$s1.image_key", "preset": "fast"},
    "image.thumbnail": {
        "topic": "Du lịch Việt Nam", "model": "gemini-2.5-flash-image",
        "aspect_ratio": "16:9", "count": 1,
    },
    "text.prompt_package": {
        "operation": "director", "title": "Chiến dịch", "story": "Một câu chuyện đủ dài",
        "scene_count": 6, "duration_seconds": 30, "aspect_ratio": "16:9",
        "style": "cinematic", "audience": "general", "language": "vi",
        "resources": [], "model": "gemini-2.5-flash",
    },
    "story.storyboard": {
        "operation": "storyboard", "title": "Chiến dịch",
        "story": "Một câu chuyện đủ dài", "scene_count": 6,
        "aspect_ratio": "16:9", "style": "cinematic", "resources": [],
        "model": "gemini-2.5-flash",
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
    "text.generate": {"text": "Nội dung"},
    "image.generate": {"image_keys": ["image/u/1.png"], "prompt": "p"},
    "image.batch_generate": {"image_keys": ["image/u/1.png", "image/u/2.png"], "prompt": "p"},
    "asset.image": {"image_key": "agent-assets/u/1.png"},
    "asset.images": {"image_keys": ["agent-assets/u/1.png", "agent-assets/u/2.png"]},
    "asset.video": {"video_key": "agent-assets/u/1.mp4"},
    "asset.audio": {"audio_key": "agent-assets/u/1.wav"},
    "video.extract_frames": {"image_keys": ["mediatools/u/1/1.jpg"]},
    "media.merge_image": {"image_key": "mediatools/u/1/merged.jpg"},
    "media.merge_video": {"video_key": "mediatools/u/1/merged.mp4"},
    "audio.generate": {"audio_key": "mediatools/u/1/speech.wav"},
    "video.social_import": {"video_key": "mediatools/u/1/imported.mp4"},
    "image.upscale": {"image_key": "upscalevideo/u/1/image-x4.png"},
    "image.thumbnail": {"image_keys": ["thumbnail/u/1.png"], "prompt": "p"},
    "video.generate": {"video_key": "taovideo/u/1.mp4"},
    "video.subtitle": {"video_key": "autosubvideo/u/1.mp4", "srt_key": "s", "ass_key": "a"},
    "video.upscale": {"video_key": "upscalevideo/u/1.mp4"},
    "video.short_clips": {"clips": [{"video_key": "taoclipngan/u/1.mp4"}]},
    "text.prompt_package": {"prompt_package": {"scenes": []}, "master_prompt": "p"},
    "story.storyboard": {"storyboard": {"scenes": []}, "master_prompt": "p"},
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
