import os
import subprocess
from ...tuong_thich.log import info


AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


def _pick_first_audio(path_dir: str) -> str:
    files = [f for f in os.listdir(path_dir) if f.lower().endswith(AUDIO_EXTS)]
    if not files:
        raise FileNotFoundError(f"No voice audio found in: {path_dir}")
    files.sort()
    return os.path.join(path_dir, files[0])


def _run(cmd: list[str], capture: bool = True, timeout: float = 900):
    """
    Run ffmpeg command. If fails, show stderr/stdout to debug.
    [Phase 7] timeout=900s (15 phút) — audio mix 1 video tổng < 5 phút thực tế.
    """
    try:
        if capture:
            return subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, check=True, timeout=timeout,
            )
        return subprocess.run(cmd, check=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"Audio mix FFmpeg timeout ({timeout:.0f}s): {' '.join(cmd[:6])}..."
        ) from e


def mix_audio_layers(cfg: dict, base_video: str, voice_dir: str, music_path: str | None, out_video: str):
    """
    Audio mix policy (per your spec):
    - Voice: keep original (no loudnorm), only resample to 48k stereo for stability
    - Music: loudnorm to target LUFS (default -24), then duck by voice (sidechaincompress)
    - Clip audio (base_video audio): keep but reduce gain (default -18dB)
    - Final: AAC 48k stereo
    - Video: copy by default (fast, no quality loss)
    """
    audio_cfg = cfg.get("audio", {})
    out_cfg = cfg.get("output", {})

    # ---- Inputs
    voice_in = _pick_first_audio(voice_dir)

    tmp_dir = os.path.join(os.path.dirname(os.path.abspath(out_video)), "tmp_audio")
    os.makedirs(tmp_dir, exist_ok=True)

    # Convert voice to stable WAV (keep loudness unchanged)
    voice_wav = os.path.join(tmp_dir, "voice_48k.wav")
    _run([
        "ffmpeg", "-y",
        "-i", voice_in,
        "-vn",
        "-ar", "48000",
        "-ac", "2",
        "-c:a", "pcm_s16le",
        voice_wav
    ])

    inputs = ["-i", base_video, "-i", voice_wav]

    # ---- Music handling
    has_music = bool(music_path)
    if has_music:
        inputs += ["-i", music_path]

    # ---- Gains / targets
    # Clip audio should be quiet to not fight voice
    base_gain_db = float(audio_cfg.get("base_clip_audio_gain_db", -18.0))

    # Music target loudness (LUFS)
    music_target_lufs = float(audio_cfg.get("music_target_lufs", -24.0))
    # True Peak and LRA for loudnorm
    music_tp = float(audio_cfg.get("music_true_peak_db", -2.0))
    music_lra = float(audio_cfg.get("music_lra", 7.0))

    duck_cfg = audio_cfg.get("ducking", {})
    duck_enable = bool(duck_cfg.get("enable", True))

    # sidechaincompress parameters
    # Note: threshold can be specified in dB by adding "dB" suffix (as you had)
    thr_db = float(duck_cfg.get("threshold_db", -24.0))  # more negative = more sensitive
    ratio = float(duck_cfg.get("ratio", 12.0))
    attack = int(duck_cfg.get("attack_ms", 15))
    release = int(duck_cfg.get("release_ms", 600))
    makeup_db = float(duck_cfg.get("makeup_db", 0.0))  # usually 0

    # Optional: extra music trim gain after loudnorm (fine-tune)
    # Default is -24dB per your spec (reduce background music while keeping voice unchanged)
    music_post_gain_db = float(audio_cfg.get("music_post_gain_db", -24.0))

    # ---- Build filter_complex
    # Streams:
    #   [0:a] = base clip audio
    #   [1:a] = voice wav
    #   [2:a] = music (optional)
    #
    # Steps:
    #   - base clip: volume down
    #   - music: loudnorm to -24 LUFS, then (optional) post gain, then duck by voice
    #   - mix: amix with voice dominant
    #
    # IMPORTANT: We DO NOT loudnorm voice.
    if has_music:
        # loudnorm music to target LUFS
        # Use single-pass loudnorm (good enough & fast). Two-pass is more accurate but slower/complex.
        fc = (
            f"[0:a]volume={base_gain_db}dB[clip];"
            f"[2:a]loudnorm=I={music_target_lufs}:TP={music_tp}:LRA={music_lra}[mnorm];"
            f"[mnorm]volume={music_post_gain_db}dB[mv];"
        )

        if duck_enable:
            # Duck music by voice
            # sidechaincompress: main input is music [mv], sidechain is voice [1:a]
            fc += (
                f"[mv][1:a]sidechaincompress="
                f"threshold={thr_db}dB:ratio={ratio}:attack={attack}:release={release}:makeup={makeup_db}dB"
                f"[mduck];"
                f"[clip][mduck][1:a]amix=inputs=3:normalize=0:dropout_transition=0[aout]"
            )
        else:
            fc += f"[clip][mv][1:a]amix=inputs=3:normalize=0:dropout_transition=0[aout]"
    else:
        # No music: just clip + voice
        fc = (
            f"[0:a]volume={base_gain_db}dB[clip];"
            f"[clip][1:a]amix=inputs=2:normalize=0:dropout_transition=0[aout]"
        )

    # ---- Video output strategy
    # base_video was already produced at target width/height/fps; mixing should NOT re-encode video by default.
    copy_video = bool(out_cfg.get("copy_video_on_mix", True))
    if copy_video:
        v_args = ["-c:v", "copy"]
    else:
        vcodec = out_cfg.get("video_codec", "libx264")
        # High quality re-encode if needed (same settings as assemble.py)
        v_args = [
            "-c:v", vcodec,
            "-preset", "veryfast",
            "-crf", "18",
            "-b:v", "32M",
            "-maxrate", "40M",
            "-bufsize", "64M"
        ]

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", fc,
        "-map", "0:v",
        "-map", "[aout]",
        *v_args,
        "-c:a", "aac",
        "-ar", "48000",
        "-ac", "2",
        "-movflags", "+faststart",
        out_video
    ]

    # Run and show output if it fails
    try:
        _run(cmd, capture=True)
    except subprocess.CalledProcessError as e:
        # show tail of ffmpeg output for debug
        out = (e.stdout or "")
        raise RuntimeError(f"FFmpeg mix failed.\n\nCMD: {' '.join(cmd)}\n\nOUTPUT (tail):\n{out[-6000:]}") from e

    info("mix_done", out=out_video)
