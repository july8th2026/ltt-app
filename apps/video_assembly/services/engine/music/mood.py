import os
import random
from typing import Optional

import yaml

from ...tuong_thich.log import info
from ...tuong_thich.ffmpeg import probe_duration, run

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


def _load_keywords(path: str) -> dict:
    if not path or not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = {}
    for mood, kws in data.items():
        if kws is None:
            out[mood] = []
        elif isinstance(kws, (list, tuple)):
            out[mood] = [str(x) for x in kws]
        else:
            out[mood] = [str(kws)]
    return out


def _pick_mood(keyword_map: dict, text: str) -> str:
    if not keyword_map:
        return "Calm"
    t = (text or "").lower()
    for mood, kws in keyword_map.items():
        for kw in kws:
            if kw and kw.lower() in t:
                return str(mood)
    return "Calm"


def _pick_track(music_root: str, mood: str) -> Optional[str]:
    folder = os.path.join(music_root, mood)
    if not os.path.isdir(folder):
        return None
    tracks = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(AUDIO_EXTS)
    ]
    return random.choice(tracks) if tracks else None


def _ffmpeg_list_path(p: str) -> str:
    ap = os.path.abspath(p).replace("\\", "/")
    return ap.replace("'", "\\'")


def _extract_window(track: str, out_wav: str, take_s: float, avoid_start: float, avoid_end: float) -> float:
    dur = max(0.0, probe_duration(track))
    take = max(3.0, float(take_s))

    if dur > (avoid_start + avoid_end + take + 0.5):
        st_min = avoid_start
        st_max = max(avoid_start, dur - avoid_end - take)
        st = random.uniform(st_min, st_max)
    else:
        st = 0.0

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{st:.3f}",
        "-i", track,
        "-t", f"{take:.3f}",
        "-vn",
        "-ar", "48000",
        "-ac", "2",
        "-c:a", "pcm_s16le",
        out_wav
    ]
    run(cmd, capture_output=True)
    return take


def _majority_mood(moods: list[str]) -> str:
    if not moods:
        return "Calm"
    freq = {}
    for m in moods:
        freq[m] = freq.get(m, 0) + 1
    return max(freq.items(), key=lambda x: x[1])[0]


def _build_music_blocks(cfg: dict, segments: list[dict], keyword_map: dict, total_len: float) -> list[dict]:
    """
    Convert many short segments (3–5s) into longer music blocks (60–90s or config range).
    Each block chooses a single mood for stability.
    """
    mcfg = cfg.get("music", {})
    seg_min, seg_max = mcfg.get("segment_len_s", [60.0, 90.0])
    seg_min = float(seg_min)
    seg_max = float(seg_max)

    blocks = []
    i = 0
    n = len(segments)
    t = 0.0

    while t < total_len and i < n:
        # choose target block length (e.g. 60–90s)
        target = random.uniform(seg_min, seg_max)
        block_start = t
        block_end = min(total_len, block_start + target)

        moods_in_block = []
        # collect segments whose time overlaps this block window
        while i < n:
            s = segments[i]
            s_start = float(s.get("start", 0.0))
            s_end = float(s.get("end", 0.0))

            # if segment starts after block end → stop collecting
            if s_start >= block_end:
                break

            # pick mood from this segment text
            mood = _pick_mood(keyword_map, s.get("text", "")) if keyword_map else "Calm"
            moods_in_block.append(mood)
            i += 1

        mood_final = _majority_mood(moods_in_block)
        blocks.append({
            "start": block_start,
            "end": block_end,
            "mood": mood_final,
            "dur": max(3.0, block_end - block_start),
        })

        t = block_end

    return blocks


def build_music_track(cfg: dict, music_root: str, segments: list[dict], out_path: str) -> Optional[str]:
    mcfg = cfg.get("music", {})
    if not mcfg.get("enable", True) or not music_root or not os.path.isdir(music_root):
        return None

    total_len = float(segments[-1]["end"]) if segments else 0.0
    if total_len <= 0.0:
        return None

    keyword_map = _load_keywords(mcfg.get("keyword_map_file", "")) if mcfg.get("use_keyword_map", True) else {}

    tmp_dir = os.path.join(os.path.dirname(out_path), "tmp_music")
    os.makedirs(tmp_dir, exist_ok=True)

    avoid_start = float(mcfg.get("avoid_start_s", 10.0))
    avoid_end = float(mcfg.get("avoid_end_s", 10.0))
    crossfade_s = float(mcfg.get("crossfade_s", 0.0))

    # ✅ NEW: build long music blocks (not per 3–5s segment)
    blocks = _build_music_blocks(cfg, segments, keyword_map, total_len)

    chunks = []
    for bi, b in enumerate(blocks):
        mood = b["mood"]
        dur = float(b["dur"])

        track = _pick_track(music_root, mood) or _pick_track(music_root, "Calm")
        if not track:
            continue

        chunk_wav = os.path.join(tmp_dir, f"block_{bi:04d}_{mood}.wav")
        _extract_window(track, chunk_wav, take_s=dur, avoid_start=avoid_start, avoid_end=avoid_end)
        chunks.append(chunk_wav)

    if not chunks:
        return None

    # ✅ If crossfade_s > 0 and we have multiple blocks, do acrossfade chain
    mixed_wav = os.path.join(tmp_dir, "music_mixed.wav")

    if crossfade_s > 0.0 and len(chunks) >= 2:
        inputs = []
        for c in chunks:
            inputs += ["-i", c]

        # chain acrossfade: [0:a][1:a] -> [a01], then [a01][2:a] -> [aout]...
        fc_parts = []
        last = "[0:a]"
        for idx in range(1, len(chunks)):
            cur = f"[{idx}:a]"
            out = f"[a{idx:02d}]"
            fc_parts.append(f"{last}{cur}acrossfade=d={crossfade_s}:c1=tri:c2=tri{out}")
            last = out

        fc = ";".join(fc_parts)

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", fc,
            "-map", last,
            "-vn",
            "-ar", "48000",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            mixed_wav
        ]
        run(cmd, capture_output=True)
    else:
        # fallback: simple concat (no crossfade)
        list_path = os.path.join(tmp_dir, "concat.txt")
        with open(list_path, "w", encoding="utf-8", newline="\n") as f:
            for c in chunks:
                f.write(f"file '{_ffmpeg_list_path(c)}'\n")

        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", _ffmpeg_list_path(list_path),
            "-vn",
            "-c:a", "pcm_s16le",
            "-ar", "48000",
            "-ac", "2",
            mixed_wav
        ]
        run(cmd_concat, capture_output=True)

    # Trim exactly to total video duration
    trimmed_wav = os.path.join(tmp_dir, "music_trim.wav")
    cmd_trim = [
        "ffmpeg", "-y",
        "-i", mixed_wav,
        "-t", f"{total_len:.3f}",
        "-vn",
        "-c:a", "pcm_s16le",
        "-ar", "48000",
        "-ac", "2",
        trimmed_wav
    ]
    run(cmd_trim, capture_output=True)

    out_ext = os.path.splitext(out_path)[1].lower()
    if out_ext in (".wav", ".wave"):
        os.replace(trimmed_wav, out_path)
        info("music_track_done", out=out_path, fmt="wav", seconds=total_len, blocks=len(blocks))
        return out_path

    cmd_mp3 = [
        "ffmpeg", "-y",
        "-i", trimmed_wav,
        "-c:a", "libmp3lame",
        "-b:a", str(mcfg.get("bitrate", "192k")),
        "-ar", "48000",
        "-ac", "2",
        out_path
    ]
    run(cmd_mp3, capture_output=True)
    info("music_track_done", out=out_path, fmt="mp3", seconds=total_len, blocks=len(blocks))
    return out_path
