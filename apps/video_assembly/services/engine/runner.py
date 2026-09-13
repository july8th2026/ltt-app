"""
engine/runner.py - PATCH FOR PHASE 1 + MUSIC FORMAT FIX

Changes:
1. Add input validation before processing
2. Add error context tracking for each file operation
3. Add stage progress tracking
4. Better error messages with file context
5. ✅ Support both MP3 and WAV for music track (auto-detect)

Usage:
  Thay thế hàm run_local_job() trong engine/runner.py hiện tại
"""

import os
import shutil
import uuid
import json
from pathlib import Path

from ..tuong_thich.log import info, warn, exc, error
from ..tuong_thich.paths import ensure_dir, safe_name

# Import validation và error tracking
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from .error_context import (
    FileErrorContext,
    StageValidator,
    ProcessingTracker,
    validate_input_structure
)

# Engine modules
from .stt import transcribe_whisper
from .segment import make_segments
from .clip_sampling import sample_clip_frames
from .video_sanitize import sanitize_folder
from .clip_embed import ClipEmbedder
from .matcher import match_timeline
from .sequential_timeline import build_sequential_timeline
from .filters.duplicates import filter_duplicates
from .filters.motion import filter_by_motion
from .filters.yolo_quality import filter_by_yolo
from .music.mood import build_music_track
from .assemble import build_video_from_timeline
from .audio.mix import mix_audio_layers
from .audio.demucs_post import make_base_video_novocals


def _signal_gpu_phase_done(workdir: str, reason: str = ""):
    """[Phase A2] Signal to parent process that GPU-heavy phases are done.

    Writes a marker file `{workdir}/.gpu_phase_done`. Parent process (bot/job.py:run_engine)
    polls for this file and releases the GpuSlot file lock as soon as it appears, so other
    bots can use the GPU while this engine continues with CPU/NVENC work (assembly, music
    mix, subtitle burn).

    Idempotent — safe to call multiple times. Parent uses a flag to fire callback once only.

    Non-fatal on failure: parent always releases lock at subprocess exit anyway, so a
    missing marker just means we lose the early-release optimization for this job.
    """
    try:
        import time as _t
        from pathlib import Path as _P
        marker = _P(workdir) / ".gpu_phase_done"
        marker.write_text(f"{_t.time():.0f}\n{reason}\n", encoding="utf-8")
        info("gpu_phase_done_signal", reason=reason, path=str(marker))
    except Exception as _e:
        info("gpu_phase_done_signal_failed", error=str(_e))


def _detect_music_format(music_dir: str) -> str:
    """
    Auto-detect music format từ files có sẵn trong music_dir.
    
    Priority order: wav > mp3 > m4a > aac > flac > ogg
    
    Args:
        music_dir: Đường dẫn đến thư mục chứa music (có thể có subfolders theo mood)
    
    Returns:
        Extension string (không có dấu chấm): "wav", "mp3", etc.
        Default: "mp3" nếu không tìm thấy file nào
    
    Examples:
        >>> _detect_music_format("MUSIC/Calm")
        "wav"  # nếu tìm thấy file .wav
        
        >>> _detect_music_format("MUSIC/Empty")  
        "mp3"  # fallback default
    """
    if not os.path.exists(music_dir) or not os.path.isdir(music_dir):
        return "mp3"
    
    # Priority format order (WAV first vì lossless)
    format_priority = ['.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg']
    
    # Scan all files in directory và subdirectories (mood folders)
    for root, dirs, files in os.walk(music_dir):
        for format_ext in format_priority:
            for f in files:
                if f.lower().endswith(format_ext):
                    return format_ext[1:]  # Bỏ dấu chấm: ".wav" -> "wav"
    
    # Fallback default
    return "mp3"


def run_local_job(cfg: dict, input_dir: str, music_dir: str, out_path: str, workdir: str):
    """
    Run local job with Phase 1 improvements:
    - Input validation before processing
    - Error context for file operations
    - Stage progress tracking
    - ✅ Music format auto-detection (MP3 & WAV support)
    """
    
    # Setup paths
    workdir_abs = os.path.abspath(workdir)
    input_dir_abs = os.path.abspath(input_dir)
    job_id = safe_name(os.path.basename(workdir_abs)) or safe_name(os.path.basename(input_dir_abs)) or str(uuid.uuid4())[:8]
    job_dir = ensure_dir(workdir_abs)
    
    # ✅ IMPROVEMENT 1: Initialize progress tracker
    tracker = ProcessingTracker(job_id)
    
    # Enhanced logging
    info("job_start", 
         job_id=job_id, 
         job_dir=job_dir,
         job_dir_abs=workdir_abs,
         input_dir=input_dir,
         input_dir_abs=input_dir_abs,
         music_dir=music_dir,
         out_path=out_path)

    try:
        # ========================================
        # STAGE 0: INPUT VALIDATION
        # ========================================
        tracker.start_stage("INPUT_VALIDATION", "Kiểm tra file đầu vào")
        
        # ✅ IMPROVEMENT 2: Validate input structure
        validator = validate_input_structure(Path(input_dir_abs), job_id)
        
        tracker.complete_stage("INPUT_VALIDATION")

        # ========================================
        # STAGE 1: VIDEO SANITIZE (optional)
        # ========================================
        video_dir = os.path.join(input_dir_abs, "VIDEO")
        vcfg = cfg.get("video_sanitize", {})
        
        if vcfg.get("enable", True):
            tracker.start_stage("VIDEO_SANITIZE", f"Sanitizing videos from {video_dir}")
            
            # Validate VIDEO directory exists
            validator.validate_dir_has_files(
                Path(video_dir),
                stage="VIDEO_SANITIZE",
                extensions=['.mp4', '.avi', '.mov', '.mkv'],
                min_files=1
            )
            
            sanitized_dir = os.path.join(job_dir, "_sanitized_videos")
            info("sanitizing_videos", source=video_dir, destination=sanitized_dir)
            
            try:
                video_dir = sanitize_folder(cfg, video_dir, sanitized_dir)
                info("sanitize_done", video_dir=video_dir)
                tracker.complete_stage("VIDEO_SANITIZE")
            except Exception as e:
                tracker.fail_stage("VIDEO_SANITIZE", str(e))
                raise
        else:
            info("video_sanitize_disabled", using_dir=video_dir)

        # ========================================
        # STAGE 2: TRANSCRIPTION
        # ========================================
        voice_dir = os.path.join(input_dir_abs, "VOICE")
        
        # Validate VOICE directory
        validator.validate_dir_has_files(
            Path(voice_dir),
            stage="TRANSCRIPTION",
            extensions=['.mp3', '.wav', '.m4a', '.aac'],
            min_files=1
        )
        
        input_transcript_path = os.path.join(input_dir_abs, "transcript.json")
        segments_output_path = os.path.join(job_dir, "segments.json")
        transcript_output_path = os.path.join(job_dir, "transcript.json")
        
        if os.path.exists(input_transcript_path):
            # Use existing transcript
            tracker.start_stage("TRANSCRIPTION", "Using existing transcript.json")
            
            # ✅ IMPROVEMENT 3: Validate transcript file
            validator.validate_file_exists(Path(input_transcript_path), "TRANSCRIPTION", required=True)
            
            with FileErrorContext(input_transcript_path, "LOAD_TRANSCRIPT", job_id):
                with open(input_transcript_path, "r", encoding="utf-8") as f:
                    segments = json.load(f)
                
                info("loaded_existing_segments", count=len(segments))
                
                # Save copies
                with open(segments_output_path, "w", encoding="utf-8") as f:
                    json.dump(segments, f, ensure_ascii=False, indent=2)
                
                with open(transcript_output_path, "w", encoding="utf-8") as f:
                    json.dump(segments, f, ensure_ascii=False, indent=2)
            
            tracker.complete_stage("TRANSCRIPTION")
        
        else:
            # Generate new transcript
            tracker.start_stage("TRANSCRIPTION", f"Generating transcript from {voice_dir}")
            
            try:
                info("no_existing_transcript_creating_new")
                
                # Whisper transcription with error tracking
                transcript = transcribe_whisper(cfg, voice_dir, transcript_output_path)
                
                # Segment generation
                segments = make_segments(cfg, transcript, segments_output_path)
                
                tracker.complete_stage("TRANSCRIPTION")
            except Exception as e:
                tracker.fail_stage("TRANSCRIPTION", str(e))
                error("transcription_failed", 
                      voice_dir=voice_dir,
                      error=str(e),
                      suggestion="Check audio files format and Whisper model availability")
                raise

        # Validate segments exist
        validator.validate_file_exists(Path(segments_output_path), "POST_TRANSCRIPTION", required=True)

        # ========================================
        # STAGE 3: CLIP SAMPLING
        # ========================================
        tracker.start_stage("CLIP_SAMPLING", f"Sampling frames from {video_dir}")
        
        clips_dir = os.path.join(job_dir, "clips")
        
        try:
            clip_items = sample_clip_frames(cfg, video_dir, clips_dir)
            info("clip_sampling_done", total_clips=len(clip_items))
            tracker.complete_stage("CLIP_SAMPLING")
        except Exception as e:
            tracker.fail_stage("CLIP_SAMPLING", str(e))
            error("clip_sampling_failed",
                  video_dir=video_dir,
                  clips_dir=clips_dir,
                  error=str(e),
                  suggestion="Check video files are valid and readable")
            raise

        # ========================================
        # STAGE 4: FILTERING
        # ========================================
        tracker.start_stage("FILTERING", "Filtering clips by quality")
        
        try:
            orig_count = len(clip_items)
            min_clips_needed = max(len(segments) * 1.2, 60)

            # FIX#3: Helper đếm số scene_id duy nhất phủ bởi clips còn sống.
            # Dùng cùng PREFIX_PATTERN với sequential_timeline.py:11 để đảm bảo
            # logic mapping đồng nhất giữa filter và timeline matching.
            import re as _re
            _PREFIX_RE = _re.compile(r'^(\d{3,4})-scene', _re.IGNORECASE)
            _SCENE_RE  = _re.compile(r'scene_?id[-_](\d+)', _re.IGNORECASE)
            def _unique_scenes(items):
                s = set()
                for c in items:
                    nm = c.get("name", "") or ""
                    m = _PREFIX_RE.search(nm) or _SCENE_RE.search(nm)
                    if m:
                        s.add(int(m.group(1)))
                return len(s)
            scenes_total = _unique_scenes(clip_items)

            # Apply filters with fallback
            # Quy tắc revert MỚI: revert nếu (a) thiếu clip tổng, HOẶC (b) mất phủ scene_id.
            # Quy tắc cũ chỉ kiểm (a) → motion filter có thể loại sạch các scene B-roll
            # khiến timeline_matching fail dù tổng clip vẫn dư.
            orig = clip_items
            clip_items = filter_by_motion(cfg, clip_items)
            scenes_after = _unique_scenes(clip_items)
            if len(clip_items) < min_clips_needed or scenes_after < scenes_total:
                info("filter_motion_reverted",
                     kept=len(clip_items), needed=min_clips_needed,
                     scenes_before=scenes_total, scenes_after=scenes_after,
                     reason=("scene_coverage_lost" if scenes_after < scenes_total else "low_count"))
                clip_items = orig
            else:
                scenes_total = scenes_after

            orig = clip_items
            clip_items = filter_duplicates(cfg, clip_items)
            scenes_after = _unique_scenes(clip_items)
            if len(clip_items) < min_clips_needed or scenes_after < scenes_total:
                info("filter_duplicates_reverted",
                     kept=len(clip_items), needed=min_clips_needed,
                     scenes_before=scenes_total, scenes_after=scenes_after,
                     reason=("scene_coverage_lost" if scenes_after < scenes_total else "low_count"))
                clip_items = orig
            else:
                scenes_total = scenes_after

            orig = clip_items
            clip_items = filter_by_yolo(cfg, clip_items)
            scenes_after = _unique_scenes(clip_items)
            if len(clip_items) < min_clips_needed or scenes_after < scenes_total:
                info("filter_yolo_reverted",
                     kept=len(clip_items), needed=min_clips_needed,
                     scenes_before=scenes_total, scenes_after=scenes_after,
                     reason=("scene_coverage_lost" if scenes_after < scenes_total else "low_count"))
                clip_items = orig

            info("filtering_done",
                 original=orig_count,
                 after_filter=len(clip_items),
                 unique_scenes=_unique_scenes(clip_items),
                 segments=len(segments))
            
            tracker.complete_stage("FILTERING")
        except Exception as e:
            tracker.fail_stage("FILTERING", str(e))
            # Filtering errors are not critical, continue with original clips
            info("filtering_failed_using_original", error=str(e))

        # ========================================
        # STAGE 5: EMBEDDING
        # ========================================
        tracker.start_stage("EMBEDDING", "Computing CLIP embeddings")
        
        try:
            embedder = ClipEmbedder(cfg)
            embedder.embed_clips(clip_items)
            embedder.embed_texts(segments)
            
            tracker.complete_stage("EMBEDDING")
        except Exception as e:
            tracker.fail_stage("EMBEDDING", str(e))
            error("embedding_failed",
                  error=str(e),
                  suggestion="Check CLIP model availability and GPU/CPU resources")
            raise

        # ========================================
        # STAGE 6: TIMELINE MATCHING
        # ========================================
        tracker.start_stage("TIMELINE_MATCHING", "Matching clips to segments")
        
        timeline_path = os.path.join(job_dir, "timeline.json")
        
        try:
            if cfg.get("timeline", {}).get("mode", "semantic") == "sequential":
                timeline = build_sequential_timeline(cfg, segments, clip_items, timeline_path)
            else:
                timeline = match_timeline(cfg, segments, clip_items, timeline_path)
            
            info("timeline_done", segments=len(timeline))
            tracker.complete_stage("TIMELINE_MATCHING")
        except Exception as e:
            tracker.fail_stage("TIMELINE_MATCHING", str(e))
            error("timeline_matching_failed",
                  error=str(e),
                  segments=len(segments),
                  clips=len(clip_items))
            raise

        # Validate timeline exists
        validator.validate_file_exists(Path(timeline_path), "POST_TIMELINE", required=True)

        # ========================================
        # STAGE 7: VIDEO ASSEMBLY
        # ========================================
        tracker.start_stage("VIDEO_ASSEMBLY", "Assembling base video")
        
        base_video = os.path.join(job_dir, "base_video.mp4")
        
        try:
            build_video_from_timeline(cfg, timeline, base_video)
            
            # Validate output
            validator.validate_file_exists(Path(base_video), "POST_ASSEMBLY", required=True)
            
            tracker.complete_stage("VIDEO_ASSEMBLY")
        except Exception as e:
            tracker.fail_stage("VIDEO_ASSEMBLY", str(e))
            error("video_assembly_failed",
                  timeline=timeline_path,
                  output=base_video,
                  error=str(e),
                  suggestion="Check FFmpeg installation and timeline.json validity")
            raise

        # ========================================
        # STAGE 8: DEMUCS (optional)
        # ========================================
        demucs_cfg = cfg.get("demucs", {})
        # [Audit Fix #1] Track Demucs success — chi signal marker neu thuc su DONE
        # Truoc day: marker duoc ghi LUON neu eval disabled, ke ca khi Demucs crash
        # → bot khac vao trong khi Demucs cleanup van dang chay → potential GPU race.
        # Sau fix: marker chi ghi neu Demucs success HOAC bi disable hoan toan.
        _demucs_ok = True  # Mac dinh True (skipped = OK)
        if demucs_cfg.get("enable", False):
            tracker.start_stage("DEMUCS", "Removing vocals from base video")

            base_nv = os.path.join(job_dir, "base_video_novocals.mp4")

            try:
                make_base_video_novocals(cfg, base_video, base_nv)
                base_video = base_nv

                tracker.complete_stage("DEMUCS")
                _demucs_ok = True
            except Exception as e:
                tracker.fail_stage("DEMUCS", str(e))
                # Demucs is optional, continue without it
                info("demucs_failed_skipping", error=str(e))
                _demucs_ok = False  # ← MARK FAIL: skip early marker

        # [Phase A2 + Audit Fix #1] Sau STAGE 8 (Demucs done or skipped) — neu
        # Eval bi disable VA Demucs khong fail thi day la diem GPU work cuoi cung.
        # Signal parent release GpuSlot ngay.
        # Neu Eval enabled HOAC Demucs crashed thi BO QUA: eval/cleanup can GPU lai;
        # marker se ghi sau eval (line ~726) hoac safety net trong worker finally.
        # [Sua 2026-08-26 — do duoc tu hop den] Truoc day marker CHI fire khi
        # evaluation bi TAT. Evaluation dang BAT nen thuc te lease bi giu den het
        # job: do duoc dungvideo/ENGINE giu GPU 52 phut o 6% utilization -> 48
        # phut khoa card ma khong dung. Tren toan he thong: 89% thoi gian giu
        # GPU la lang phi.
        #
        # Demucs la buoc GPU NANG CUOI CUNG. Sau day la MUSIC / MIX / BURN SUB —
        # toan viec CPU/ffmpeg. Nha lease ngay tai day.
        if _demucs_ok:
            _signal_gpu_phase_done(workdir, reason="post_demucs_gpu_work_done")
        else:
            info("gpu_phase_marker_skipped", reason="demucs_failed_keep_lock_for_safety")

        # ========================================
        # STAGE 9: MUSIC
        # ========================================
        tracker.start_stage("MUSIC", f"Building music track from {music_dir}")
        
        # ✅ FIX: Auto-detect music format thay vì hardcode .mp3
        music_format = _detect_music_format(music_dir)
        music_track = os.path.join(job_dir, f"music.{music_format}")
        
        info("music_format_detected", 
             music_dir=music_dir, 
             format=music_format,
             output_path=music_track)
        
        try:
            # Validate music directory exists
            if not os.path.exists(music_dir):
                info("music_dir_missing_skipping", music_dir=music_dir)
                music_track = None
            else:
                # build_music_track sẽ tự động convert theo extension của out_path
                build_music_track(cfg, music_dir, segments, music_track)
                
                # ✅ Enhanced validation với detailed logging
                if os.path.exists(music_track):
                    size_mb = os.path.getsize(music_track) / 1024 / 1024
                    info("music_created_success", 
                         path=music_track, 
                         format=music_format,
                         size_mb=f"{size_mb:.2f}",
                         exists=True)
                    validator.validate_file_exists(Path(music_track), "POST_MUSIC", required=False)
                else:
                    info("music_not_created_fallback", 
                         expected_path=music_track,
                         exists=False)
                    music_track = None
            
            tracker.complete_stage("MUSIC")
        except Exception as e:
            tracker.fail_stage("MUSIC", str(e))
            # Music is optional
            error("music_failed_skipping", 
                  error=str(e),
                  music_dir=music_dir,
                  expected_format=music_format,
                  suggestion="Check music folder has valid audio files (.wav, .mp3, etc.)")
            music_track = None

        # ========================================
        # STAGE 10: AUDIO MIX
        # ========================================
        tracker.start_stage("AUDIO_MIX", "Mixing audio layers")
        
        try:
            mix_audio_layers(cfg, base_video, voice_dir, music_track, out_path)
            
            # Validate final output
            validator.validate_file_exists(Path(out_path), "FINAL_OUTPUT", required=True)
            
            tracker.complete_stage("AUDIO_MIX")
        except Exception as e:
            tracker.fail_stage("AUDIO_MIX", str(e))
            error("audio_mix_failed",
                  base_video=base_video,
                  voice_dir=voice_dir,
                  music_track=music_track,
                  output=out_path,
                  error=str(e),
                  suggestion="Check FFmpeg and audio file formats. Ensure music track exists if specified.")
            raise

        # ========================================
        # STAGE 11: SUBTITLE (optional)
        # ========================================
        sub_cfg = cfg.get("subtitle", {})
        out_subbed_path = os.path.join(job_dir, "output_subbed.mp4")

        if sub_cfg.get("enable", False):
            tracker.start_stage("SUBTITLE", "Burning subtitles into video")
            info("subtitle_config",
                 style=sub_cfg.get("style_preset", "default"),
                 mode=sub_cfg.get("segment_mode", "sentence"),
                 quality=sub_cfg.get("quality", "standard"))

            try:
                from .subtitle.pipeline import generate_subtitle_files
                from .subtitle.burner import burn_subtitles as burn_sub, probe_video
                from .subtitle.schemas import SubtitleStyleConfig
                from .subtitle.style_registry import get_config

                # Load transcript data
                with open(transcript_output_path, "r", encoding="utf-8") as f:
                    transcript_data = json.load(f)

                # Load segment timing for subtitle alignment (voice → video remap)
                segment_timing_path = os.path.join(job_dir, "segment_timing.json")
                segment_timing = None
                if os.path.exists(segment_timing_path):
                    with open(segment_timing_path, "r", encoding="utf-8") as f:
                        segment_timing = json.load(f)
                    info("subtitle_timing_loaded", segments=len(segment_timing))

                if not transcript_data:
                    info("subtitle_skip", reason="empty transcript")
                    shutil.copy2(out_path, out_subbed_path)
                else:
                    # Probe video for resolution
                    video_info = probe_video(out_path)
                    v_width = video_info.get("width", 1920)
                    v_height = video_info.get("height", 1080)
                    total_dur = video_info.get("duration", 0)
                    info("subtitle_probe",
                         resolution=f"{v_width}x{v_height}",
                         duration=f"{total_dur:.1f}s")

                    # Build custom style overrides from config (if any custom fields provided)
                    custom_style = None
                    _CUSTOM_STYLE_KEYS = (
                        "font_family", "font_size", "font_color", "bold", "italic",
                        "font_fallback", "outline_color", "outline_width",
                        "shadow_color", "shadow_offset",
                        "alignment", "margin_v", "margin_h", "line_spacing",
                        "bg_box", "bg_color", "bg_opacity", "bg_padding",
                        "safe_area_percent", "max_chars_per_line", "max_lines",
                        "highlight_mode", "highlight_color",
                        "keyword_highlights", "keyword_highlight_color",
                    )
                    style_fields = {k: sub_cfg[k] for k in _CUSTOM_STYLE_KEYS if k in sub_cfg}
                    # Filter out "zero/empty = use preset default" values:
                    # GUI spinbox uses 0 as "(preset default)", empty string = not set
                    # Nếu không filter, font_size=0 sẽ override preset font_size=48 → render lỗi
                    # NOTE: outline_width and shadow_offset are intentionally excluded —
                    # 0 is a valid user choice (no outline / no shadow), not "use default".
                    _ZERO_MEANS_DEFAULT = {"font_size",
                                           "margin_v", "margin_h", "line_spacing",
                                           "bg_padding", "safe_area_percent", "max_chars_per_line", "max_lines"}
                    style_fields = {
                        k: v for k, v in style_fields.items()
                        if not (k in _ZERO_MEANS_DEFAULT and (v == 0 or v == ""))
                        and not (isinstance(v, str) and v == "")
                    }
                    if style_fields:
                        # Merge with preset: start from preset, then override with custom fields
                        try:
                            base_style = get_config(sub_cfg.get("style_preset", "default"))
                            custom_style = base_style.copy_with(**style_fields)
                            info("subtitle_custom_style", fields=list(style_fields.keys()))
                        except Exception as e:
                            warn("subtitle_custom_style_error", error=str(e))
                            custom_style = None  # Fall back to preset only

                    # Generate ASS + SRT files
                    info("subtitle_generating_ass")
                    sub_result = generate_subtitle_files(
                        transcript_data=transcript_data,
                        style_id=sub_cfg.get("style_preset", "default"),
                        custom_style=custom_style,
                        segment_mode=sub_cfg.get("segment_mode", "sentence"),
                        output_dir=job_dir,
                        base_name="subtitle",
                        video_width=v_width,
                        video_height=v_height,
                        segment_timing=segment_timing,
                    )

                    ass_path = sub_result.get("ass_path")
                    if not ass_path:
                        raise RuntimeError("ASS subtitle file was not generated")

                    event_count = sub_result.get("event_count", "?")
                    info("subtitle_ass_ready",
                         events=event_count,
                         ass_path=ass_path)

                    if sub_result.get("font_warning"):
                        warn("subtitle_font_fallback", warning=sub_result["font_warning"])

                    # Burn subtitles into video (match source bitrate to preserve quality)
                    source_kbps = video_info.get("bitrate_kbps", 0)
                    info("subtitle_burning", input=out_path, output=out_subbed_path,
                         bitrate_mode="match", source_kbps=source_kbps)
                    burn_sub(
                        video_path=out_path,
                        ass_path=ass_path,
                        output_path=out_subbed_path,
                        quality=sub_cfg.get("quality", "standard"),
                        bitrate_mode="match",
                        source_bitrate_kbps=source_kbps,
                        total_duration=total_dur,
                    )

                    sub_size_mb = os.path.getsize(out_subbed_path) / 1024 / 1024
                    orig_size_mb = os.path.getsize(out_path) / 1024 / 1024
                    info("subtitle_done",
                         output=out_subbed_path,
                         size_mb=f"{sub_size_mb:.1f}",
                         original_mb=f"{orig_size_mb:.1f}")

                tracker.complete_stage("SUBTITLE")

            except Exception as e:
                tracker.fail_stage("SUBTITLE", str(e))
                error("subtitle_failed_using_original",
                      error=str(e),
                      suggestion="Subtitle burn failed, using original video without subtitles")
                # Fail-safe: copy original video
                if not os.path.exists(out_subbed_path):
                    shutil.copy2(out_path, out_subbed_path)
                    info("subtitle_fallback_copy", output=out_subbed_path)
        else:
            info("subtitle_disabled")

        # [Phase A2] Sau buoc GPU cuoi (SUB xong/bo qua) — defensive marker write.
        # Idempotent: neu marker da ghi sau STAGE 8 thi ghi lai la no-op cho cha
        # (callback chi fire mot lan moi subprocess).
        _signal_gpu_phase_done(workdir, reason="post_sub_final")

        # ========================================
        # SUCCESS
        # ========================================
        final_output = out_subbed_path if os.path.isfile(out_subbed_path) else out_path
        info("job_done", job_id=job_id, output=final_output)
        
        # Print summary
        print("\n" + "=" * 80)
        print(tracker.get_progress_summary())
        print(validator.get_summary())
        print("=" * 80 + "\n")
        
    except Exception as e:
        # Print failure summary
        print("\n" + "=" * 80)
        print("❌ JOB FAILED")
        print("=" * 80)
        print(tracker.get_progress_summary())
        print(validator.get_summary())
        print("=" * 80 + "\n")
        
        exc("job_failed", e)
        raise