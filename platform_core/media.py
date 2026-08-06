"""
media.py — dịch vụ nền tảng cho công cụ ffmpeg (P4 + P5).

Vì sao ở platform_core: nhiều app video (auto_sub, upscale, concat…) đều cần
định vị ffmpeg/ffprobe, đọc metadata video, dò encoder GPU. Gom về một nơi để
app KHÔNG gọi thẳng binary — đổi đường dẫn/encoder chỉ sửa một file.

Khác BOT GEMINI: bản gốc dùng asyncio; worker nền tảng chạy handler ĐỒNG BỘ
(một tiến trình một job) nên ở đây dùng `subprocess` đồng bộ cho đơn giản, đúng
mô hình. Song song nhiều job = chạy nhiều tiến trình worker (P3), không phải
async trong một tiến trình.

Cấu hình đường dẫn (theo thứ tự ưu tiên):
  LTT_FFMPEG / LTT_FFPROBE  (đường dẫn tuyệt đối) → PATH → thư mục cài phổ biến.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from typing import Callable, Optional

log = logging.getLogger(__name__)


class MediaError(Exception):
    pass


# Nơi WinGet/BtbN hay đặt ffmpeg trên Windows (khi không có trên PATH của dịch vụ).
_WIN_HINTS = (
    r"C:\ffmpeg\bin",
    r"C:\Program Files\ffmpeg\bin",
)


def _locate(name: str, env_key: str) -> Optional[str]:
    override = os.environ.get(env_key, "").strip()
    if override:
        return override if os.path.isfile(override) else None
    found = shutil.which(name)
    if found:
        return found
    exe = name + (".exe" if os.name == "nt" else "")
    for d in _WIN_HINTS:
        cand = os.path.join(d, exe)
        if os.path.isfile(cand):
            return cand
    # WinGet Links shim / PATH mở rộng của user không lên tới dịch vụ NSSM.
    links = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links")
    cand = os.path.join(links, exe)
    return cand if os.path.isfile(cand) else None


def ffmpeg_bin() -> str:
    p = _locate("ffmpeg", "LTT_FFMPEG")
    if not p:
        raise MediaError("Không tìm thấy ffmpeg (đặt LTT_FFMPEG hoặc thêm vào PATH).")
    return p


def ffprobe_bin() -> str:
    p = _locate("ffprobe", "LTT_FFPROBE")
    if not p:
        raise MediaError("Không tìm thấy ffprobe (đặt LTT_FFPROBE hoặc thêm vào PATH).")
    return p


def has_ffmpeg() -> bool:
    try:
        return bool(_locate("ffmpeg", "LTT_FFMPEG"))
    except OSError:
        return False


# ── P5: đọc metadata video (đo duration để GIỮ CHỖ credit) ────────────────────

def probe(path: str) -> dict:
    """Metadata video qua ffprobe (đồng bộ).
    Trả {duration, width, height, codec, fps, audio_codec, file_size_mb, bitrate_kbps}."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Không có file video: {path}")
    cmd = [ffprobe_bin(), "-v", "quiet", "-print_format", "json",
           "-show_format", "-show_streams", path]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired as e:
        raise MediaError("ffprobe quá thời gian.") from e
    if out.returncode != 0:
        raise MediaError(f"ffprobe lỗi (code {out.returncode}): "
                         f"{out.stderr.decode(errors='replace')[:300]}")
    try:
        data = json.loads(out.stdout.decode(errors="replace"))
    except json.JSONDecodeError as e:
        raise MediaError("ffprobe trả về không phải JSON.") from e

    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0) or 0)
    file_size = int(fmt.get("size", 0) or 0)
    width = height = 0
    fps = 0.0
    vcodec = acodec = ""
    for st in data.get("streams", []):
        if st.get("codec_type") == "video" and not vcodec:
            width = int(st.get("width", 0) or 0)
            height = int(st.get("height", 0) or 0)
            vcodec = st.get("codec_name", "") or ""
            rfr = st.get("r_frame_rate", "0/1") or "0/1"
            if "/" in rfr:
                num, den = rfr.split("/")
                fps = float(num) / float(den) if float(den) else 0.0
            else:
                fps = float(rfr or 0)
        elif st.get("codec_type") == "audio" and not acodec:
            acodec = st.get("codec_name", "") or ""
    bitrate_kbps = int((file_size * 8) / max(duration, 0.1) / 1000) if duration > 0 else 0
    return {"duration": round(duration, 3), "width": width, "height": height,
            "codec": vcodec, "fps": round(fps, 2), "audio_codec": acodec,
            "file_size_mb": round(file_size / (1024 * 1024), 1),
            "bitrate_kbps": bitrate_kbps}


def duration_seconds(path: str) -> float:
    """Chỉ lấy thời lượng (giây). Lỗi → 0.0 (caller quyết định)."""
    try:
        return float(probe(path).get("duration", 0.0))
    except Exception:  # noqa: BLE001
        # PHẢI ghi log: con số này dùng để GIỮ CHỖ credit. Trả 0.0 lặng lẽ
        # nghĩa là giữ chỗ 0 credit — khách được làm miễn phí, hoặc job bị
        # định giá sai, và không dòng nào chỉ ra vì sao.
        log.exception("Không đo được thời lượng %s — trả 0.0, credit sẽ sai", path)
        return 0.0


# ── Dò encoder GPU (dùng chung; auto_sub có fallback CPU, upscale bắt buộc GPU) ──

_gpu_cache: Optional[str] = None


def detect_gpu_encoder() -> str:
    """encoder phần cứng tốt nhất (h264_nvenc>h264_qsv>h264_amf) hoặc "" (CPU).
    Cache theo vòng đời tiến trình."""
    global _gpu_cache
    if _gpu_cache is not None:
        return _gpu_cache
    if not has_ffmpeg():
        _gpu_cache = ""
        return ""
    for enc in ("h264_nvenc", "h264_qsv", "h264_amf"):
        if _test_encoder(enc):
            log.info("[media] GPU encoder: %s", enc)
            _gpu_cache = enc
            return enc
    log.info("[media] không có GPU encoder, dùng libx264")
    _gpu_cache = ""
    return ""


def _test_encoder(encoder: str) -> bool:
    # 256x256 testsrc (KHÔNG dùng nullsrc 64x64): NVENC có kích thước TỐI THIỂU và
    # từ chối frame quá nhỏ ("Frame Dimension less than the minimum") → test cũ báo
    # nhầm "không có GPU" dù NVENC sẵn sàng, khiến encode 4K lùi về CPU rất chậm.
    try:
        r = subprocess.run(
            [ffmpeg_bin(), "-y", "-f", "lavfi",
             "-i", "testsrc=size=256x256:rate=1:duration=1", "-pix_fmt", "yuv420p",
             "-c:v", encoder, "-frames:v", "1", "-f", "null", "-"],
            capture_output=True, timeout=15)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def reset_gpu_cache() -> None:
    """Cho test."""
    global _gpu_cache
    _gpu_cache = None


# ── Chạy ffmpeg đồng bộ có báo tiến độ (dùng chung auto_sub + upscale) ─────────

_OUT_TIME_US = re.compile(r"^out_time_(?:ms|us)=(\d+)")
_OUT_TIME = re.compile(r"^out_time=(\d+):(\d+):([\d.]+)")


def run_with_progress(cmd: list, *, total_duration: float = 0.0,
                      on_progress: Optional[Callable[[float], None]] = None,
                      timeout: int = 1800, cwd: Optional[str] = None) -> None:
    """Chạy một lệnh ffmpeg có `-progress pipe:1 -nostats`, đọc stdout để báo
    phần trăm (0..100) qua `on_progress`. Ném MediaError nếu returncode != 0.

    Lưu ý: caller phải tự thêm `-progress pipe:1 -nostats` vào cmd. Hàm này chỉ
    đọc và phân tích, không tự chèn cờ (để caller kiểm soát toàn bộ lệnh).

    `cwd` đặt thư mục làm việc — dùng để tránh phải escape đường dẫn Windows trong
    filter (vd `-vf ass=`): chạy trong thư mục chứa file rồi truyền tên file trần."""
    import collections
    import threading

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            bufsize=1, universal_newlines=True, cwd=cwd)
    # PHẢI rút stderr song song: ffmpeg ghi nhiều vào stderr; nếu để đầy buffer
    # đường ống (64KB) trong khi ta chỉ đọc stdout thì ffmpeg treo → deadlock với
    # video dài. Thread này giữ giữ 12 dòng cuối để báo lỗi.
    tail: "collections.deque" = collections.deque(maxlen=12)

    def _drain_err():
        try:
            for ln in proc.stderr:                     # type: ignore[union-attr]
                s = ln.strip()
                if s:
                    tail.append(s)
        except (OSError, ValueError):
            pass          # ống đã đóng: bình thường khi tiến trình kết thúc

    t = threading.Thread(target=_drain_err, daemon=True)
    t.start()
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            if on_progress and total_duration > 0:
                m = _OUT_TIME_US.match(line)
                cur = None
                if m:
                    cur = int(m.group(1)) / 1_000_000
                else:
                    m2 = _OUT_TIME.match(line)
                    if m2:
                        cur = int(m2.group(1)) * 3600 + int(m2.group(2)) * 60 + float(m2.group(3))
                if cur is not None:
                    pct = min(99.0, cur / total_duration * 100)
                    if pct > 0:
                        on_progress(round(pct, 1))
            if line == "progress=end":
                if on_progress:
                    on_progress(100.0)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired as e:
        proc.kill()
        proc.wait()
        raise MediaError(f"ffmpeg quá thời gian ({timeout}s).") from e
    finally:
        t.join(timeout=5)
    if proc.returncode != 0:
        raise MediaError(f"ffmpeg lỗi (code {proc.returncode}): " + " | ".join(tail))
