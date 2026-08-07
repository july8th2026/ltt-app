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

from platform_core.i18n import _ as _t
import logging
import os
import tempfile
import copy
import io
import json
import hashlib

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
        raise ValueError(_t('Thiếu project/source/revision cho transcription.'))
    if not video_key.startswith(f"autosubvideo/{owner_id}/"):
        raise ValueError(_t('Video source không thuộc project owner.'))
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
            raise ValueError(_t('Video không có audio/thời lượng hợp lệ.'))
        if duration > 7200:
            raise ValueError(_t('Mỗi lượt chép lời tối đa 120 phút.'))

        def progress(percent, message):
            if ctx is not None:
                ctx.progress(max(5, min(90, int(percent))), message)

        result = transcribe_file(
            local, language=str(params.get("language", "")),
            model_name=str(params.get("model", "large-v3")), on_progress=progress,
            is_cancelled=(ctx.is_cancelled if ctx is not None else None),
            gpu_uuid=getattr(ctx, "gpu_uuid", ""))
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
            raise ValueError(_t('Không nhận được lời nói trong video.'))
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
    if operation == "diarize":
        return _handle_diarize(params, ctx)
    if operation == "translate":
        return _handle_translate(params, ctx)
    if operation == "render_project":
        return _handle_project_render(params, ctx)
    if operation != "render":
        raise ValueError(f"Operation Auto Sub không hỗ trợ: {operation}")
    return _handle_render(params, ctx)


def _handle_project_render(params: dict, ctx=None) -> dict:
    from platform_core import media
    from platform_core.storage import get_storage
    from apps.autosubvideo.schemas import StudioProjectV1
    from apps.autosubvideo.project_render import build_project_artifacts

    owner_id = str(params.get("owner_id", "")); video_key = str(params.get("video_key", ""))
    snapshot = params.get("project_snapshot") or {}
    canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != str(params.get("snapshot_sha256", "")):
        raise ValueError(_t('Snapshot project không còn toàn vẹn.'))
    project = StudioProjectV1.model_validate(snapshot)
    if not owner_id or not video_key.startswith(f"autosubvideo/{owner_id}/"):
        raise ValueError(_t('Source video không thuộc project owner.'))
    storage = get_storage(); job_id = getattr(ctx, "job_id", "") or "adhoc"
    ext = _EXT[project.output.format]
    prefix = f"autosubvideo/{owner_id}/{job_id}"
    out_key = f"{prefix}/output{ext}"
    tmpdir = tempfile.mkdtemp(prefix="ltt_autosub_project_")
    local = os.path.join(tmpdir, "source" + (os.path.splitext(video_key)[1] or ".mp4"))
    try:
        if ctx: ctx.progress(4, "tải snapshot và source")
        with storage.open(video_key) as src, open(local, "wb") as dst:
            import shutil; shutil.copyfileobj(src, dst, length=1024 * 1024)
        meta = media.probe(local); duration = float(meta.get("duration") or 0)
        if duration <= 0: raise ValueError(_t('Video không có thời lượng hợp lệ.'))
        true_cost = cost.uoc_luong_credit(duration, project.output.quality)
        _dam_bao_giu_cho(job_id, owner_id, true_cost)
        target_height = {"720p": 720, "1080p": 1080, "4k": 2160}.get(project.output.resolution, 0)
        source_w = int(meta.get("width") or project.source.width or 1920)
        source_h = int(meta.get("height") or project.source.height or 1080)
        render_h = target_height or source_h
        render_w = max(2, int(round(source_w * render_h / max(1, source_h) / 2) * 2))
        artifacts = build_project_artifacts(snapshot, tmpdir, width=render_w, height=render_h)
        if not storage.exists(out_key):
            def progress(value):
                if ctx: ctx.progress(min(95, 22 + int(value * .72)), "render video")
            local_out = os.path.join(tmpdir, "output" + ext)
            burn.burn(video_path=local, ass_path=artifacts["ass_path"], output_path=local_out,
                output_format=project.output.format, quality=project.output.quality,
                source_bitrate_kbps=int(meta.get("bitrate_kbps") or 0),
                total_duration=duration, target_height=target_height, on_progress=progress)
            with open(local_out, "rb") as stream:
                storage.put(out_key, stream, f"video/{project.output.format}")
        result = {"video_key": out_key, "credit_cost": true_cost,
            "duration_s": round(duration, 2), "quality": project.output.quality,
            "resolution": project.output.resolution, "output_format": project.output.format,
            "snapshot_sha256": digest, "project_revision": params.get("project_revision"),
            "track_ids": artifacts["track_ids"], "mode": "full",
            "source": {"width": source_w, "height": source_h,
                       "fps": meta.get("fps", 0),
                       "has_audio": bool(meta.get("has_audio", True))},
            "output": {"width": render_w, "height": render_h}}
        if project.output.export_ass:
            key=f"{prefix}/sub-combined.ass"
            with open(artifacts["ass_path"],"rb") as stream: storage.put(key,stream,"text/plain; charset=utf-8")
            result["ass_key"]=key
        if project.output.export_srt:
            result["srt_keys"]={}
            for track_id,path in artifacts["srt_paths"].items():
                key=f"{prefix}/{os.path.basename(path)}"
                with open(path,"rb") as stream: storage.put(key,stream,"application/x-subrip")
                result["srt_keys"][track_id]=key
        if project.output.export_vtt:
            result["vtt_keys"]={}
            for track_id,path in artifacts["vtt_paths"].items():
                key=f"{prefix}/{os.path.basename(path)}"
                with open(path,"rb") as stream: storage.put(key,stream,"text/vtt")
                result["vtt_keys"][track_id]=key
        if project.output.export_json:
            result["json_keys"]={}
            for track_id,path in artifacts["json_paths"].items():
                key=f"{prefix}/{os.path.basename(path)}"
                with open(path,"rb") as stream: storage.put(key,stream,"application/json")
                result["json_keys"][track_id]=key
        if artifacts["bundle_path"]:
            key=f"{prefix}/subtitle-bundle.zip"
            with open(artifacts["bundle_path"],"rb") as stream: storage.put(key,stream,"application/zip")
            result["bundle_key"]=key
        if ctx: ctx.progress(100,"render hoàn tất")
        return result
    finally:
        import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


def _handle_diarize(params: dict, ctx=None) -> dict:
    from platform_core import app_projects
    from platform_core.db import get_session
    from platform_core.storage import get_storage
    from apps.autosubvideo.ai_workflows import assign_speakers, diarize_file
    from apps.autosubvideo.schemas import StudioProjectV1
    owner_id=str(params.get("owner_id",""));project_id=str(params.get("project_id",""))
    revision=int(params.get("project_revision",0) or 0);video_key=str(params.get("video_key",""))
    if not owner_id or not project_id or revision<1 or not video_key.startswith(f"autosubvideo/{owner_id}/"):
        raise ValueError(_t('Thiếu project/source/revision cho diarization.'))
    tmpdir=tempfile.mkdtemp(prefix="ltt_autosub_diarize_")
    local=os.path.join(tmpdir,"source"+(os.path.splitext(video_key)[1] or ".mp4"))
    try:
        if ctx:ctx.progress(3,"tải source")
        with get_storage().open(video_key) as src,open(local,"wb") as dst:
            import shutil;shutil.copyfileobj(src,dst,length=1024*1024)
        turns=diarize_file(local,min_speakers=int(params.get("min_speakers",0) or 0),
            max_speakers=int(params.get("max_speakers",0) or 0),
            on_progress=(lambda p,m:ctx.progress(p,m)) if ctx else None,
            is_cancelled=ctx.is_cancelled if ctx else None)
        gen=get_session();db=next(gen)
        try:
            row=app_projects.get_owned(db,project_id,owner_id,"autosubvideo")
            payload=copy.deepcopy(row.payload);cue_count=0
            speakers=dict(payload.get("speakers") or {})
            for track in payload.get("tracks") or []:
                if track.get("kind")!="source":continue
                updated,names=assign_speakers(track.get("cues") or [],turns)
                track["cues"]=updated;cue_count+=sum(bool(cue.get("speaker")) for cue in updated)
                for key,value in names.items():speakers.setdefault(key,value)
            payload["speakers"]=speakers
            validated=StudioProjectV1.model_validate(payload).model_dump(mode="json")
            conflict=False;applied=0
            try:
                saved=app_projects.save(db,project_id=project_id,user_id=owner_id,
                    app_slug="autosubvideo",revision=revision,name=row.name,schema_version=1,payload=validated)
                db.commit();applied=saved.revision
            except app_projects.ProjectConflict:db.rollback();conflict=True
        finally:
            try:next(gen)
            except StopIteration:pass
        artifact_key=f"autosubvideo/{owner_id}/{getattr(ctx,'job_id','adhoc')}/diarization.json"
        get_storage().put(artifact_key,io.BytesIO(json.dumps({"schema_version":1,"turns":turns},
            ensure_ascii=False,allow_nan=False).encode("utf-8")),"application/json")
        if ctx:ctx.progress(100,"phân vai hoàn tất")
        return {"project_id":project_id,"project_revision":applied,"project_conflict":conflict,
                "diarization_key":artifact_key,"speaker_count":len({t['speaker'] for t in turns}),
                "assigned_cues":cue_count}
    finally:
        import shutil;shutil.rmtree(tmpdir,ignore_errors=True)


def _handle_translate(params: dict, ctx=None) -> dict:
    from platform_core import app_projects
    from platform_core.db import get_session
    from platform_core.storage import get_storage
    from apps.autosubvideo.ai_workflows import translate_cues
    from apps.autosubvideo.schemas import StudioProjectV1
    owner_id=str(params.get("owner_id",""));project_id=str(params.get("project_id",""))
    revision=int(params.get("project_revision",0) or 0);track_id=str(params.get("track_id",""))
    language=str(params.get("target_language",""))[:24]
    if not owner_id or not project_id or revision<1 or not track_id or not language:
        raise ValueError(_t('Thiếu project/track/ngôn ngữ cho translation.'))
    gen=get_session();db=next(gen)
    try:
        row=app_projects.get_owned(db,project_id,owner_id,"autosubvideo")
        payload=copy.deepcopy(row.payload);source=next((t for t in payload.get("tracks",[]) if t.get("id")==track_id),None)
        if not source or not source.get("cues"):raise ValueError(_t('Track nguồn không có cue để dịch.'))
        translated=translate_cues(db,source["cues"],language,
            on_progress=(lambda p,m:ctx.progress(p,m)) if ctx else None,
            is_cancelled=ctx.is_cancelled if ctx else None)
        target_id=f"track-{language}";existing=next((t for t in payload.get("tracks",[]) if t.get("id")==target_id),None)
        z=max([-1,*[int(t.get("z_index",0)) for t in payload.get("tracks",[])]])+1
        track={"id":target_id,"kind":"translation","language":language,
               "name":f"Bản dịch {language}","visible":False,"z_index":z,
               "style_id":source.get("style_id","default"),"cues":translated}
        if existing:
            track["visible"]=bool(existing.get("visible",False));track["z_index"]=int(existing.get("z_index",z))
            payload["tracks"]=[track if t.get("id")==target_id else t for t in payload["tracks"]]
        else:payload["tracks"].append(track)
        validated=StudioProjectV1.model_validate(payload).model_dump(mode="json")
        conflict=False;applied=0
        artifact_key=f"autosubvideo/{owner_id}/{getattr(ctx,'job_id','adhoc')}/translation-{language}.json"
        get_storage().put(artifact_key,io.BytesIO(json.dumps({"schema_version":1,"track":track},
            ensure_ascii=False,allow_nan=False).encode("utf-8")),"application/json")
        try:
            saved=app_projects.save(db,project_id=project_id,user_id=owner_id,
                app_slug="autosubvideo",revision=revision,name=row.name,schema_version=1,payload=validated)
            db.commit();applied=saved.revision
        except app_projects.ProjectConflict:db.rollback();conflict=True
        if ctx:ctx.progress(100,"dịch hoàn tất")
        return {"project_id":project_id,"project_revision":applied,"project_conflict":conflict,
                "translation_key":artifact_key,"track_id":target_id,"cue_count":len(translated),
                "target_language":language}
    finally:
        try:next(gen)
        except StopIteration:pass


def _handle_render(params: dict, ctx=None) -> dict:
    from platform_core import media
    from platform_core.storage import get_storage

    video_key = str(params.get("video_key", "")).strip()
    if not video_key:
        raise ValueError(_t('Thiếu video (video_key).'))
    transcript = params.get("transcript") or []
    if not transcript:
        raise ValueError(_t('Thiếu transcript (chưa nạp phụ đề).'))
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
            raise RuntimeError(_t('Không dựng được file phụ đề ASS.'))

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
