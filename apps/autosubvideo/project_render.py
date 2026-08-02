"""Build immutable Studio project subtitle artifacts for a render job."""
from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

from apps.autosubvideo.ass_builder import (
    _apply_animation, _apply_highlight, _build_header, _build_styles_section,
    _format_ass_time, build_srt,
)
from apps.autosubvideo.schemas import StudioProjectV1
from apps.autosubvideo.segmenter import SubtitleEvent


def _events(track: dict) -> list[SubtitleEvent]:
    return [SubtitleEvent(start=float(cue["start"]), end=float(cue["end"]),
                          text=str(cue["text"]), display_text=str(cue["text"]),
                          index=index)
            for index, cue in enumerate(track.get("cues") or []) if str(cue.get("text", "")).strip()]


def _vtt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def build_project_artifacts(snapshot: dict, output_dir: str, *, width: int,
                            height: int) -> dict:
    """Build combined ASS, optional per-track SRT and a metadata bundle."""
    project = StudioProjectV1.model_validate(snapshot)
    selected = set(project.output.track_ids)
    tracks = [track for track in project.tracks
              if track.visible and (not selected or track.id in selected) and track.cues]
    if not tracks:
        raise ValueError("Không có track phụ đề được chọn để render.")

    root = Path(output_dir); root.mkdir(parents=True, exist_ok=True)
    style = project.style
    lines = ["[Events]",
             "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    srt_paths: dict[str, str] = {}
    vtt_paths: dict[str, str] = {}
    json_paths: dict[str, str] = {}
    for position, track in enumerate(sorted(tracks, key=lambda item: item.z_index)):
        events = _events(track.model_dump(mode="json"))
        if project.output.export_srt:
            safe = "".join(c for c in track.id if c.isalnum() or c in "_-")[:64]
            path = root / f"sub-{safe}.srt"; build_srt(events, str(path)); srt_paths[track.id] = str(path)
        else:
            safe = "".join(c for c in track.id if c.isalnum() or c in "_-")[:64]
        if project.output.export_vtt:
            path = root / f"sub-{safe}.vtt"
            body = ["WEBVTT", ""]
            for event in events:
                body.extend([f"{_vtt_time(event.start)} --> {_vtt_time(event.end)}",
                             event.text.replace("\n", " "), ""])
            path.write_text("\n".join(body), encoding="utf-8")
            vtt_paths[track.id] = str(path)
        if project.output.export_json:
            path = root / f"sub-{safe}.json"
            path.write_text(json.dumps({"schema_version": 1,
                "track": track.model_dump(mode="json")}, ensure_ascii=False, indent=2),
                encoding="utf-8")
            json_paths[track.id] = str(path)
        for event in events:
            text = _apply_highlight(event, style.highlight_mode, style.highlight_color,
                keyword_highlights=style.keyword_highlights,
                keyword_highlight_color=style.keyword_highlight_color)
            text = _apply_animation(text, style, width, height)
            # Additional tracks are placed at the top by default; source stays
            # at the selected style position. Layer preserves deterministic z-order.
            if position:
                text = "{\\an8}" + text
            lines.append(f"Dialogue: {track.z_index},{_format_ass_time(event.start)},"
                         f"{_format_ass_time(event.end)},Default,,0,0,0,,{text}")
    ass_path = root / "sub-combined.ass"
    ass_path.write_text(
        _build_header("Auto Sub Studio", width, height) + "\n" +
        _build_styles_section(style, width, height, style.highlight_color) + "\n" +
        "\n".join(lines) + "\n", encoding="utf-8-sig")

    manifest_path = root / "render-manifest.json"
    manifest_path.write_text(json.dumps({"schema_version": 1,
        "resolution": project.output.resolution, "format": project.output.format,
        "quality": project.output.quality, "track_ids": [track.id for track in tracks]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    bundle_path = None
    if project.output.bundle_zip:
        bundle_path = root / "subtitle-bundle.zip"
        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(ass_path, ass_path.name); archive.write(manifest_path, manifest_path.name)
            for path in srt_paths.values(): archive.write(path, os.path.basename(path))
            for path in vtt_paths.values(): archive.write(path, os.path.basename(path))
            for path in json_paths.values(): archive.write(path, os.path.basename(path))
    return {"ass_path": str(ass_path), "srt_paths": srt_paths,
            "vtt_paths": vtt_paths, "json_paths": json_paths,
            "bundle_path": str(bundle_path) if bundle_path else "",
            "track_ids": [track.id for track in tracks]}
