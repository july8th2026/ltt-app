"""
Handler job app `autosubvideo`. Khắc phụ đề vào video trong WORKER (không dính
trần 100s Cloudflare). Luồng:

    tải video (R2/Local) → ĐO thời lượng thật → ĐẢM BẢO giữ chỗ đủ (chống khai
    gian) → dựng ASS từ transcript → burn ffmpeg (báo tiến độ) → lưu output →
    quyết toán theo giá thật.

Hợp đồng: idempotent (resume: output đã có thì bỏ qua) · báo tiến độ (ctx.progress
đập nhịp) · NÉM khi lỗi (nền tảng hoàn credit). Giá quyết toán = credit theo
thời lượng THẬT (không phải theo số client khai).
"""
from __future__ import annotations

import logging
import os
import tempfile
import copy
import io
import json

from apps.autosubvideo import burn, cost

log = logging.getLogger(__name__)

_EXT = {"mp4": ".mp4", "mkv": ".mkv", "webm": ".webm"}


def _dam_bao_giu_cho(job_id: str, user_id: str, need: int) -> None:
    """Đảm bảo phần giữ chỗ của job ≥ `need`. Thiếu thì giữ thêm phần chênh.
    Ném RuntimeError nếu số dư không đủ (worker sẽ fail job + hoàn phần đã giữ) —
    chặn TRƯỚC khi encode nên không tốn tài nguyên cho job không trả nổi tiền."""
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
            raise RuntimeError(
                f"Không đủ credit cho video dài thật ({need} credit): {e}") from e
    finally:
        try: next(gen)
        except StopIteration: pass


def _handle_transcribe(params: dict, ctx=None) -> dict:
    from platform_core import media
    from platform_core.storage import get_storage
    from apps.autosubvideo.schemas import StudioProjectV1
    from apps.autosubvideo.transcription import transcribe_file

    owner_id = str(params.get("owner_id", ""))
    project_id = str(params.get("project_id", ""))
    video_key = str(params.get("video_key", ""))
    expected_revision = int(params.get("project_revision", 0) or 0)
    if not owner_id or not project_id or not video_key or expected_revision < 1:
        raise ValueError("Thiếu project/source/revision cho transcription.")
    if not video_key.startswith(f"autosubvideo/{owner_id}/"):
        raise ValueError("Video source không thuộc project owner.")
    storage = get_storage()
    tmpdir = tempfile.mkdtemp(prefix="ltt_autosub_asr_")
    local = os.path.join(tmpdir, "source" + (os.path.splitext(video_key)[1] or ".mp4"))
    job_id = getattr(ctx, "job_id", "") or "adhoc"
    try:
        if ctx is not None:
            ctx.progress(3, "tải source")
        with storage.open(video_key) as src, open(local, "wb") as dst:
            import shutil
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        duration = media.duration_seconds(local)
        if duration <= 0:
            raise ValueError("Video không có audio/thời lượng hợp lệ.")
        if duration > 7200:
            raise ValueError("Mỗi lượt chép lời tối đa 120 phút.")

        def progress(percent, message):
            if ctx is not None:
                ctx.progress(max(5, min(90, int(percent))), message)

        result = transcribe_file(
            local, language=str(params.get("language", "")),
            model_name=str(params.get("model", "large-v3")), on_progress=progress,
            is_cancelled=(ctx.is_cancelled if ctx is not None else None))
        cues = []
        for index, segment in enumerate(result.get("segments") or [], 1):
            start = max(0.0, float(segment.get("start", 0)))
            end = float(segment.get("end", 0))
            text = str(segment.get("text", "")).strip()
            if end <= start or not text:
                continue
            words = []
            for word in segment.get("words") or []:
                try:
                    ws, we = float(word.get("start")), float(word.get("end"))
                except (TypeError, ValueError):
                    continue
                wt = str(word.get("word", word.get("text", ""))).strip()
                if wt and start <= ws < we <= end:
                    words.append({"start": ws, "end": we, "text": wt})
            cues.append({"id": f"cue-{index:06d}", "start": start, "end": end,
                         "text": text, "speaker": "", "words": words})
        if not cues:
            raise ValueError("Không nhận được lời nói trong video.")
        language = str(result.get("language") or params.get("language") or "und")[:24]
        track = {"id": "track-source", "kind": "source", "language": language,
                 "name": "Bản chép lời", "visible": True, "z_index": 0,
                 "style_id": "default", "cues": cues}
        artifact_key = f"autosubvideo/{owner_id}/{job_id}/transcript.json"
        storage.put(artifact_key, io.BytesIO(json.dumps(
            {"schema_version": 1, "track": track}, ensure_ascii=False,
            allow_nan=False).encode("utf-8")), content_type="application/json")

        applied_revision = 0
        conflict = False
        from platform_core.db import get_session
        from platform_core import app_projects
        gen = get_session(); db = next(gen)
        try:
            row = app_projects.get_owned(db, project_id, owner_id, "autosubvideo")
            payload = copy.deepcopy(row.payload)
            tracks = [item for item in payload.get("tracks", [])
                      if item.get("id") != "track-source"]
            payload["tracks"] = [track, *tracks]
            payload["active_step"] = "transcript"
            validated = StudioProjectV1.model_validate(payload).model_dump(mode="json")
            try:
                saved = app_projects.save(
                    db, project_id=project_id, user_id=owner_id,
                    app_slug="autosubvideo", revision=expected_revision,
                    name=row.name, schema_version=1, payload=validated)
                db.commit(); applied_revision = saved.revision
            except app_projects.ProjectConflict:
                db.rollback(); conflict = True
        finally:
            try: next(gen)
            except StopIteration: pass
        if ctx is not None:
            ctx.progress(100, "chép lời hoàn tất")
        return {"project_id": project_id, "project_revision": applied_revision,
                "project_conflict": conflict, "transcript_key": artifact_key,
                "cue_count": len(cues), "language": language,
                "engine": result.get("engine", ""),
                "alignment_status": result.get("alignment_status", ""),
                "fallback_reason": result.get("fallback_reason", "")}
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def handle(params: dict, ctx=None) -> dict:
    operation = str(params.get("operation", "render"))
    if operation == "transcribe":
        return _handle_transcribe(params, ctx)
    if operation != "render":
        raise ValueError(f"Operation Auto Sub không hỗ trợ: {operation}")
    return _handle_render(params, ctx)


def _handle_render(params: dict, ctx=None) -> dict:
    from platform_core import media
    from platform_core.storage import get_storage

    video_key = str(params.get("video_key", "")).strip()
    if not video_key:
        raise ValueError("Thiếu video (video_key).")
    transcript = params.get("transcript") or []
    if not transcript:
        raise ValueError("Thiếu transcript (chưa nạp phụ đề).")
    style_id = str(params.get("style_id") or "default")
    segment_mode = str(params.get("segment_mode") or "sentence")
    quality = str(params.get("quality") or "standard")
    output_format = str(params.get("output_format") or "mp4")
    if output_format not in _EXT:
        output_format = "mp4"
    export_srt = bool(params.get("export_srt", True))
    owner_id = str(params.get("owner_id", "")) or "unknown"
    job_id = getattr(ctx, "job_id", "") or "adhoc"

    storage = get_storage()
    ext = _EXT[output_format]
    out_key = f"autosubvideo/{owner_id}/{job_id}/output{ext}"

    tmpdir = tempfile.mkdtemp(prefix="ltt_autosub_")
    tmp_video = os.path.join(tmpdir, "in" + os.path.splitext(video_key)[1] or ".mp4")
    try:
        # 1. Tải video về máy worker (R2 hoặc Local đều qua storage.open).
        if ctx is not None:
            ctx.progress(4, "tải video")
        with storage.open(video_key) as src, open(tmp_video, "wb") as dst:
            import shutil as _sh
            _sh.copyfileobj(src, dst, length=1024 * 1024)

        # 2. Đo thời lượng THẬT → giá thật → đảm bảo giữ chỗ đủ (trước khi encode).
        meta = media.probe(tmp_video)
        true_dur = float(meta.get("duration") or 0.0)
        vw = int(meta.get("width") or 1920) or 1920
        vh = int(meta.get("height") or 1080) or 1080
        src_kbps = int(meta.get("bitrate_kbps") or 0)
        true_cost = cost.uoc_luong_credit(true_dur, quality)
        _dam_bao_giu_cho(job_id, params.get("owner_id", ""), true_cost)

        # Resume (orphan reclaim): output đã có → bỏ qua encode, quyết toán đúng giá.
        if storage.exists(out_key):
            res = {"video_key": out_key, "credit_cost": true_cost,
                   "duration_s": round(true_dur, 1), "quality": quality,
                   "output_format": output_format}
            for kk, ck in (("srt_key", f"autosubvideo/{owner_id}/{job_id}/sub.srt"),
                           ("ass_key", f"autosubvideo/{owner_id}/{job_id}/sub.ass")):
                if storage.exists(ck):
                    res[kk] = ck
            if ctx is not None:
                ctx.progress(100, "xong")
            return res

        # 3. Dựng file ASS (+SRT) từ transcript.
        if ctx is not None:
            ctx.progress(12, "dựng phụ đề")
        from apps.autosubvideo.subtitle_adapter import generate_subtitle_files
        subs = generate_subtitle_files(
            transcript_data=list(transcript), style_id=style_id,
            segment_mode=segment_mode, output_dir=tmpdir, base_name="sub",
            video_width=vw, video_height=vh,
            export_ass=True, export_srt=export_srt)
        ass_path = subs.get("ass_path")
        if not ass_path or not os.path.isfile(ass_path):
            raise RuntimeError("Không dựng được file phụ đề ASS.")

        # 4. Burn ffmpeg (báo tiến độ 30..95).
        tmp_out = os.path.join(tmpdir, "out" + ext)

        def _prog(p):
            if ctx is not None:
                ctx.progress(min(95, 30 + int(p * 0.6)), "khắc phụ đề…")

        burn.burn(video_path=tmp_video, ass_path=ass_path, output_path=tmp_out,
                  output_format=output_format, quality=quality,
                  bitrate_mode="auto", source_bitrate_kbps=src_kbps,
                  total_duration=true_dur, on_progress=_prog)

        # 5. Lưu output (+SRT/ASS) vào storage.
        if ctx is not None:
            ctx.progress(96, "lưu kết quả")
        with open(tmp_out, "rb") as f:
            storage.put(out_key, f, content_type=f"video/{output_format}")
        result = {"video_key": out_key, "credit_cost": true_cost,
                  "duration_s": round(true_dur, 1), "quality": quality,
                  "output_format": output_format}
        if export_srt and subs.get("srt_path") and os.path.isfile(subs["srt_path"]):
            srt_key = f"autosubvideo/{owner_id}/{job_id}/sub.srt"
            with open(subs["srt_path"], "rb") as f:
                storage.put(srt_key, f, content_type="application/x-subrip")
            result["srt_key"] = srt_key
        ass_key = f"autosubvideo/{owner_id}/{job_id}/sub.ass"
        with open(ass_path, "rb") as f:
            storage.put(ass_key, f, content_type="text/plain; charset=utf-8")
        result["ass_key"] = ass_key
        if subs.get("font_warning"):
            result["font_warning"] = subs["font_warning"]

        if ctx is not None:
            ctx.progress(100, "xong")
        return result
    finally:
        import shutil as _sh
        _sh.rmtree(tmpdir, ignore_errors=True)
