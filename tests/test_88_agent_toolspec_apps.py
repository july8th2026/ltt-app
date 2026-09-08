"""P2: ToolSpec public phải bám handler, giá và output đang chạy."""
from __future__ import annotations

import pathlib

import pytest

from platform_core.agent.tools import (ToolParamsError, discover_tools,
                                       resolve_params_schema,
                                       validate_tool_params)
from platform_core.registry import credit_for, discover


@pytest.fixture(autouse=True)
def _moi_provider_deu_song(monkeypatch):
    """Tệp này chốt **HỢP ĐỒNG TOOLSPEC** (tham số min/max, giá, output), không
    chốt provider nào đang sống. Mệnh đề ấy phải **bất biến với tập hợp
    provider** — nếu không, mỗi lần nền tảng retire một provider thì một phép
    kiểm về toolspec lại đỏ, và người ta sẽ hạ kỳ vọng, tức mất luôn thứ nó canh.

    ⚠️ Từ pha 04 (AI CLEAN REBUILD V2) `gemini` đã ngừng, mà
    `taoanh/manifest.py:64,149` và `thumbnail/manifest.py:85` khai
    `"providers": ["gemini"]` ⇒ enum `model_ref` của 5 tool thành **rỗng**, và
    `validate_tool_params` nay fail-closed nên nó **từ chối mọi model**. Đó là
    trạng thái ĐÚNG của pha 04; chốt trạng thái ấy nằm ở
    `tests/test_1000_chan_provider_da_ngung.py`.

    ⏭️ Pha 06 sẽ trỏ hai manifest ấy sang `ltt_image`. Lúc đó fixture này thành
    **thừa và phải gỡ** — nó đang che một sự thật tạm thời, không phải một sự
    thật lâu dài.
    """
    import dataclasses

    from platform_core import providers

    monkeypatch.setattr(
        providers, "REGISTRY",
        {pid: dataclasses.replace(p, is_active=True)
         for pid, p in providers.REGISTRY.items()},
        raising=False)


# 🗑️ Bo 11 tool ngay 2026-08-25 cung ba app `kichban`, `mediatools`, `demo`:
#    text.script · text.generate · asset.image · asset.images · asset.video ·
#    asset.audio · video.extract_frames · media.merge_image · media.merge_video ·
#    audio.generate · video.social_import.
#
# ⚠️ Bon tool `asset.*` la node DAU VAO cua workflow Agent. Go chung la go duong
#    dua tep cua khach vao mot chuoi Agent — chu san pham da biet va van quyet.
EXPECTED = {
    "image.generate", "image.thumbnail", "video.generate",
    "video.subtitle", "video.upscale", "video.short_clips",
    "image.batch_generate", "image.upscale",
    "text.prompt_package", "story.storyboard",
    # Model anh NOI BO (H37/Q102). No vao bang nay vi `discover_tools()` lay MOI
    # ToolSpec job-based — khong phai vi ai do quyet dinh mo no cho Agent. Ba cong
    # fail-closed cua Q92 va cong `is_active` cua H37 khong bi anh huong.
    "image.ltt",
    # Model GIONG NOI noi bo (LTT VOICE, Q117/Q118). Cung ly do voi hai dong tren:
    # `discover_tools()` lay MOI ToolSpec job-based, khong phai vi ai do quyet dinh
    # mo no cho Agent.
    #
    # Khac `text.chat` o mot diem dang ghi: mot luot Agent chay tren mot LLM co the
    # tu chon `speech.ltt` de doc ket qua thanh tieng — do la mot nang luc MOI cho
    # Agent, va no ton tien khach. Neu dieu do khong mong muon thi cho dung khong
    # phai o day ma o allowlist cua `planner.py`.
    "speech.ltt",
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
    # ⚠️ CAP NHAT 06/09 (H44 B1). `chatltt.trich_tep` — trich van ban tu tai
    #    lieu khach dinh vao hoi thoai. No vao bang nay vi `discover_tools()`
    #    lay MOI ToolSpec, khong phai vi ai do mo no cho Agent.
    #
    # 🔴 VA DAY LA TOOL DAU TIEN TRONG KHO dat `customer_visible=False`.
    #    Cong thu nhat ton tai tu lau nhung CHUA TUNG CHIU LUC — 13 tool con
    #    lai deu `True`. Do 06/09 truoc khi dua vao:
    #      frontend/agent-canvas/src/presentationAdapter.ts:65 va :75
    #      palette.filter(tool => tool.customer_visible !== false)
    #    ⇒ giao dien CO ton trong no, nen tool nay khong hien trong palette.
    "chatltt.trich_tep",
    # ⚠️ CAP NHAT 07/09 (H44 B6 buoc 3). `chatltt.nghien_cuu` — vong nghien
    #    cuu tren tai lieu khach da dinh. Cung ly do nhu dong tren: no vao bang
    #    nay vi `discover_tools()` lay MOI ToolSpec.
    "chatltt.nghien_cuu",
}


def test_dung_toan_bo_tool_job_based_duoc_discover():
    assert set(discover_tools()) == EXPECTED


def test_cong_THU_NHAT_that_su_chan_chu_khong_chi_ton_tai():
    """🔴 Them 06/09 — banh coc tren chi chot TEN, khong chot HANH VI.

    `chatltt.trich_tep` la tool DAU TIEN dat `customer_visible=False`. Truoc
    no, cong thu nhat la mot truong khong ai dung — no co the da hong tu lau
    ma khong ai biet, vi khong co gi de no chan.

    ⚠️ 07/09: tap nay len HAI voi `chatltt.nghien_cuu` (B6 buoc 3). Sua mot
       con so o day la mot QUYET DINH ve palette Agent, nen no phai di kem mot
       dong noi ro tool nao vua an di va vi sao — dung nhu dong tren da lam.

    ⛔ Va `discover_tools()` KHONG loc theo no (do: no tra ve ca 14 tool).
       Cua that nam o giao dien. Nen phep kiem nay chot rang truong ay den
       duoc CHO LOC — thieu no thi mot tool "an" se hien trong palette Agent,
       mot san pham DANG CONG KHAI.
    """
    tools = discover_tools()
    an = {n for n, s in tools.items() if not s.customer_visible}
    assert an == {"chatltt.trich_tep", "chatltt.nghien_cuu"}, (
        f"tap tool AN da doi: {an} — moi thay doi o day la mot quyet dinh "
        "ve thu khach nhin thay trong palette Agent")

    goc = pathlib.Path(__file__).resolve().parents[1]
    ma = (goc / "frontend" / "agent-canvas" / "src"
          / "presentationAdapter.ts").read_text(encoding="utf-8")
    assert "customer_visible!==false" in ma.replace(" ", ""), (
        "giao dien thoi loc `customer_visible` — tool AN se hien trong palette")


def test_app_khong_phu_hop_khong_bi_ep_toolspec():
    manifests = {item.slug: item.manifest for item in discover()}
    assert manifests["chataistudio"].tools == ()
    assert manifests["nexus"].tools == ()


VALID_CASES = {
    "image.generate": {
        "prompt": "Một thành phố tương lai", "model": "gemini-2.5-flash-image",
        "aspect_ratio": "16:9", "count": 4,
    },
    "image.batch_generate": {
        "prompt": "Bốn góc máy của một sản phẩm", "model": "gemini-2.5-flash-image",
        "aspect_ratio": "1:1", "count": 4,
    },
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
    "image.generate": {"image_keys": ["image/u/1.png"], "prompt": "p"},
    "image.batch_generate": {"image_keys": ["image/u/1.png", "image/u/2.png"], "prompt": "p"},
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
