"""
Handler job app `taoclipngan`. Chạy engine `cutclipshort` trong WORKER GPU (job dài:
chép lời + phân tích + render nhiều clip). Bọc 3 hàm lõi (theo blueprint
`test_local_run.py`): run_full_analysis → run_editorial → render_segment.

Hợp đồng: idempotent (resume: bỏ qua nếu đã có manifest kết quả) · báo tiến độ ·
NÉM khi lỗi (nền tảng hoàn credit). Giữ chỗ theo phút client khai → worker đo phút
THẬT + đếm clip THẬT → nâng giữ chỗ nếu thiếu → quyết toán.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

from apps.taoclipngan import cost

log = logging.getLogger(__name__)

_ASPECT = {
    "9:16": ("PORTRAIT_9_16", 1080, 1920),
    "1:1": ("SQUARE_1_1", 1080, 1080),
    "16:9": ("LANDSCAPE_16_9", 1920, 1080),
    "4:5": ("PORTRAIT_4_5", 1080, 1350),
}
_TIERS = ("fast", "balanced", "high_quality")


def _dam_bao_giu_cho(job_id: str, user_id: str, need: int) -> None:
    if not user_id or need <= 0:
        return
    from platform_core import credit
    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        held = credit.so_da_giu(db, job_id)
        if held >= need:
            return
        try:
            credit.giu_cho(db, user_id, need - held, job_id)
            db.commit()
        except credit.ThieuCreditError as e:
            db.rollback()
            raise RuntimeError(f"Không đủ credit cho video dài thật ({need} credit): {e}") from e
    finally:
        try: next(gen)
        except StopIteration: pass


def handle(params: dict, ctx=None) -> dict:
    import sys
    if str(Path(__file__).resolve().parents[2]) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from platform_core import media
    from platform_core.storage import get_storage

    # Engine cutclipshort tự dò ffmpeg/ffprobe qua PATH (nhiều adapter gọi
    # FFmpegAdapter() không truyền path). Worker (LocalSystem) KHÔNG có ffmpeg trên
    # PATH → prepend thư mục ffmpeg của nền tảng (LTT_FFMPEG) vào PATH tiến trình.
    try:
        for _bin in (media.ffmpeg_bin, media.ffprobe_bin):   # ffprobe co the o dir khac
            d = os.path.dirname(_bin())
            if d and d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
    except Exception:  # noqa: BLE001
        pass

    video_key = str(params.get("video_key", "")).strip()
    if not video_key:
        raise ValueError(_t('Thiếu video (video_key).'))
    tier = str(params.get("tier", "high_quality"))
    if tier not in _TIERS:
        tier = "high_quality"
    genre = str(params.get("genre", "talking_head")) or "talking_head"
    aspect = str(params.get("aspect_ratio", "9:16"))
    if aspect not in _ASPECT:
        aspect = "9:16"
    language = (params.get("language") or "").strip() or None    # None = auto detect
    try:
        min_dur = float(params.get("min_clip_duration_sec", 15) or 15)
        max_dur = float(params.get("max_clip_duration_sec", 60) or 60)
        target_n = int(params.get("target_clip_count", 3) or 3)
    except (TypeError, ValueError):
        min_dur, max_dur, target_n = 15.0, 60.0, 3
    target_n = max(1, min(target_n, 10))
    from apps.taoclipngan.features import (AnalysisProgressTracker,
                                           apply_quality_gate,
                                           brand_overrides, clean_brand,
                                           clean_platforms, platform_copy,
                                           score_rationale)
    brand_preset = clean_brand(str(params.get("brand_preset") or "auto"))
    platforms = clean_platforms(params.get("platforms") or [])
    owner_id = str(params.get("owner_id", "")) or "unknown"
    job_id = getattr(ctx, "job_id", "") or "adhoc"

    storage = get_storage()
    out_prefix = f"taoclipngan/{owner_id}/{job_id}"
    manifest_key = f"{out_prefix}/clips.json"

    tmp = tempfile.mkdtemp(prefix="ltt_clip_")
    project_dir = Path(tmp) / "project"
    render_dir = Path(tmp) / "clips"
    project_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)
    src = Path(tmp) / ("src" + (os.path.splitext(video_key)[1] or ".mp4"))
    try:
        if ctx is not None:
            ctx.progress(2, "tải video")
        with storage.open(video_key) as fsrc, open(src, "wb") as fdst:
            shutil.copyfileobj(fsrc, fdst, length=1024 * 1024)

        true_dur = media.duration_seconds(str(src))
        if true_dur <= 0:
            raise ValueError(_t("Không đọc được thời lượng video nguồn."))
        _dam_bao_giu_cho(job_id, params.get("owner_id", ""),
                         cost.uoc_luong_credit(true_dur, tier, target_n))

        # Resume: đã có manifest kết quả → không chạy lại.
        if storage.exists(manifest_key):
            data = json.loads(storage.open(manifest_key).read().decode("utf-8"))
            return {"clips": data.get("clips", []), "credit_cost": data.get("credit_cost")
                    or cost.uoc_luong_credit(true_dur, tier, len(data.get("clips", []))),
                    "brand_preset": data.get("brand_preset", brand_preset),
                    "platforms": data.get("platforms", platforms),
                    "qa": data.get("qa") or {}}

        # ── 1. PHÂN TÍCH (whisper + scene + yolo + audio…) ────────────────────
        # Cache cross-job (T6): phân tích là hàm của (file nguồn, tier, version
        # engine) — KHÔNG của job/user. Để cache/ sống ngoài tempdir (bị rmtree
        # cuối job) theo source_hash bền, job kế cùng video + tier ăn cache hit.
        # project_dir vẫn ở tempdir: candidates/plans/logs là của TỪNG job.
        from cutclipshort.core.analysis_runner import run_full_analysis
        from cutclipshort.core.config import AppConfig
        from cutclipshort.storage.media_index import compute_source_hash
        from platform_core.runtime_paths import data_path

        config = AppConfig()
        config.set_quality_tier(tier)
        config.set("analysis", "whisper_language", language)
        _shared_cache = Path(data_path("tcn_cache",
                                      compute_source_hash(src)[:24]))

        analysis_progress = AnalysisProgressTracker()

        def _acb(engine_name, pct):
            update = analysis_progress.update(engine_name, pct)
            if ctx is not None and update is not None:
                ctx.progress(*update)

        if ctx is not None:
            ctx.progress(5, "phân tích video (chép lời…)")
        analysis = run_full_analysis(video_path=src, project_dir=project_dir,
                                     genre=genre, config=config,
                                     progress_callback=_acb,
                                     cache_dir=_shared_cache)

        # ── 2. EDITORIAL (chọn highlight) ─────────────────────────────────────
        if ctx is not None:
            ctx.progress(62, "chọn đoạn hay")
        from cutclipshort.editorial.brain import run_editorial
        from cutclipshort.types import EditConstraints
        from cutclipshort.types.base import AspectRatio
        aspect_enum, tw, th = _ASPECT[aspect]
        constraints = EditConstraints(
            min_clip_duration_sec=min_dur, max_clip_duration_sec=max_dur,
            target_clip_count=max(target_n, 5), platform="tiktok",
            aspect_ratio=AspectRatio[aspect_enum], target_width=tw, target_height=th)
        candidates, edit_plan = run_editorial(
            analysis=analysis, constraints=constraints, genre=genre,
            user_overrides=brand_overrides(brand_preset), tier_name=tier)

        # ── 2.5 QUALITY GATE (veto clip kém trước render) ─────────────────────
        # lifecycle="released" → block (loại clip bị veto, bổ sung từ hạng kế
        # tiếp); "development" → warn (chỉ ghi lý do vào manifest, render nguyên
        # vẹn). `apply_quality_gate` là hàm thuần trong features.py — test được
        # mà không cần worker/GPU.
        from apps.taoclipngan.manifest import MANIFEST as _TCN_MANIFEST
        _gate_mode = "block" if _TCN_MANIFEST.lifecycle == "released" else "warn"
        kept_candidates, qa = apply_quality_gate(candidates, _gate_mode)
        if _gate_mode == "block":
            # plan.clips có spec của TẤT CẢ candidate theo thứ tự hạng (build
            # edit_plan.py dựng cho từng candidate) → lọc bỏ clip bị veto là
            # đủ: top-N lấy lại từ hạng kế tiếp tự động. Không thể rỗng:
            # apply_quality_gate luôn giữ ≥1 (fallback top-1).
            _kept_ids = {str(getattr(c, "candidate_id", "")) for c in kept_candidates}
            edit_plan.clips = [s for s in edit_plan.clips if s.clip_id in _kept_ids]
        if ctx is not None:
            ctx.progress(64, f"gate: {len(qa['vetoed'])} veto / {len(candidates)} {_t('ứng viên')}")
        log.info("[taoclipngan] quality gate mode=%s: %d/%d veto, fallback=%s",
                 _gate_mode, len(qa["vetoed"]), len(candidates), qa["fallback"])

        # ── 3. RENDER N clip ──────────────────────────────────────────────────
        # Huỷ hợp tác (Phase 0.3): worker đọc trạng thái job mỗi 0.5s trong
        # vòng poll của ffmpeg; job bị HUỶ → adapter giết cây ffmpeg.exe và
        # ném PipelineCancelledError → dịch thành JobCancelled (nền tảng hoàn
        # credit, không fail job).
        from cutclipshort.render.segment_renderer import render_segment
        from cutclipshort.errors import PipelineCancelledError
        from platform_core.job_runner import JobCancelled
        _cancel = (getattr(ctx, "is_cancelled", None) if ctx is not None else None)
        from cutclipshort.types import RenderSettings
        rs = RenderSettings(prefer_nvenc=True, nvenc_preset="p5", crf="18",
                            pixel_format="yuv420p", audio_codec="aac",
                            audio_bitrate="192k", audio_sample_rate=44100, audio_channels=2)
        selected = edit_plan.clips[:target_n]
        # Key theo candidate_id (CandidateClip KHONG co clip_id); ClipSpec.clip_id ==
        # candidate.candidate_id → join dung, title/score moi khong bi trong.
        cand_by = {getattr(c, "candidate_id", None): c for c in candidates}
        clips_out: list[dict] = []
        for i, clip_spec in enumerate(selected, 1):
            if ctx is not None:
                ctx.progress(min(97, 68 + int(i * 29 / max(len(selected), 1))),
                             f"dựng clip {i}/{len(selected)}")
            local = render_dir / f"clip_{i:02d}.mp4"
            try:
                out_path = render_segment(clip=clip_spec, source_path=src,
                                          output_path=local, render_settings=rs,
                                          cancel_check=_cancel)
            except PipelineCancelledError:
                # Job đã bị HUỶ: ffmpeg tree đã bị giết ở adapter. Dịch thành
                # JobCancelled để job_runner xử lý huỷ (hoàn credit, không fail).
                raise JobCancelled() from None
            except Exception as e:  # noqa: BLE001
                log.warning("[taoclipngan] render clip %d lỗi: %s", i, e)
                continue
            ckey = f"{out_prefix}/clip_{i:02d}.mp4"
            with open(out_path, "rb") as f:
                storage.put(ckey, f, content_type="video/mp4")
            cand = cand_by.get(getattr(clip_spec, "clip_id", None))
            title = (getattr(cand, "display_title", "") or "") if cand else ""
            score = round(float(getattr(getattr(cand, "score", None), "overall", 0) or 0), 3) if cand else 0
            rng = getattr(clip_spec, "source_range", None)
            dur = round(float(getattr(rng, "end", 0) - getattr(rng, "start", 0)), 1) if rng else 0
            _cap_segs = list(getattr(clip_spec, "caption_segments", None) or [])
            captions = [{"start": round(float(getattr(seg, "start", 0)), 3),
                         "end": round(float(getattr(seg, "end", 0)), 3),
                         "text": str(getattr(seg, "text", ""))[:1000],
                         "speaker": str(getattr(seg, "speaker", "") or "")[:80],
                         "words": [{"word": str(getattr(w, "word", ""))[:120],
                                    "confidence": round(float(getattr(w, "confidence", 0.0) or 0.0), 3)}
                                   for w in (getattr(seg, "words", None) or [])]}
                        for seg in _cap_segs]
            description = (getattr(cand, "seo_description", "") or "") if cand else ""
            hashtags = list(getattr(cand, "suggested_hashtags", []) or []) if cand else []
            clips_out.append({"video_key": ckey, "title": title[:120], "score": score,
                              "duration_s": dur,
                              "source_start": round(float(getattr(rng, "start", 0)), 3) if rng else 0,
                              "source_end": round(float(getattr(rng, "end", 0)), 3) if rng else 0,
                              "transcript": captions,
                              "score_rationale": score_rationale(cand) if cand else {},
                              "seo_description": str(description)[:2000],
                              "hashtags": [str(x)[:60] for x in hashtags[:12]],
                              "platform_copy": platform_copy(title, description,
                                                               hashtags, platforms)})

        if not clips_out:
            raise RuntimeError(_t('Không dựng được clip nào từ video (thử video khác/tier khác).'))

        # Độ tin cậy ghi lời theo clip (whisper word-level; không phải WER —
        # chưa có corpus tham chiếu). Clip nào không có từ confidence → None,
        # UI tự ẩn.
        from apps.taoclipngan.features import tin_cay_ghi_loi
        total_words = 0
        for _c in clips_out:
            for _seg in _c["transcript"]:
                _words = _seg.get("words") if isinstance(_seg, dict) \
                    else getattr(_seg, "words", None)
                if isinstance(_words, (list, tuple)):
                    total_words += len(_words)
        for clip in clips_out:
            clip["transcript_confidence"] = tin_cay_ghi_loi(clip["transcript"], total_words)

        credit_cost = cost.uoc_luong_credit(true_dur, tier, len(clips_out))
        # Lưu manifest kết quả (idempotent resume).
        import io as _io
        storage.put(manifest_key,
                    _io.BytesIO(json.dumps({"clips": clips_out, "credit_cost": credit_cost,
                                           "brand_preset": brand_preset,
                                           "platforms": platforms,
                                           "qa": qa},
                                           ensure_ascii=False).encode("utf-8")),
                    content_type="application/json")
        if ctx is not None:
            ctx.progress(100, f"xong — {len(clips_out)} clip")
        return {"clips": clips_out, "credit_cost": credit_cost, "tier": tier,
                "genre": genre, "aspect_ratio": aspect, "n_clips": len(clips_out),
                "brand_preset": brand_preset, "platforms": platforms, "qa": qa}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
