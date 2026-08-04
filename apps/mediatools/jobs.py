from __future__ import annotations

import io
import math
import os
import shutil
import subprocess
import tempfile
import base64
import wave
import ipaddress
import socket
from urllib.parse import urljoin, urlparse
from pathlib import Path


def _owned(key: str, owner_id: str) -> str:
    normalized = str(key or "").replace("\\", "/").strip("/")
    parts = normalized.split("/")
    if not owner_id or len(parts) < 3 or parts[1] != owner_id:
        raise ValueError("Asset không thuộc tài khoản đang chạy workflow.")
    return normalized


def _copy_local(storage, key: str, target: str) -> None:
    with storage.open(key) as src, open(target, "wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def _asset(params: dict, owner_id: str, storage) -> dict | None:
    if "image_keys" in params:
        keys = [_owned(str(key), owner_id) for key in list(params.get("image_keys") or [])]
        if not 1 <= len(keys) <= 12:
            raise ValueError("Cần 1–12 ảnh cho bộ ảnh đầu vào.")
        if len(set(keys)) != len(keys) or any(not storage.exists(key) for key in keys):
            raise ValueError("Bộ ảnh có asset trùng hoặc không còn tồn tại.")
        return {"image_keys": keys, "provenance": {"kind": "owned_uploads",
                                                     "owner": owner_id}}
    for field in ("image_key", "video_key", "audio_key"):
        if field in params:
            key = _owned(str(params[field]), owner_id)
            if not storage.exists(key):
                raise ValueError("Asset không còn tồn tại.")
            return {field: key, "provenance": {"kind": "owned_upload", "owner": owner_id}}
    return None


def _extract(params: dict, owner_id: str, storage, ctx) -> dict:
    from platform_core.media import ffmpeg_bin
    source = _owned(str(params.get("video_key", "")), owner_id)
    interval = max(.25, min(float(params.get("interval_sec", 2)), 60))
    maximum = max(1, min(int(params.get("max_frames", 12)), 60))
    job_id = getattr(ctx, "job_id", "adhoc")
    prefix = f"mediatools/{owner_id}/{job_id}/frames"
    tmp = tempfile.mkdtemp(prefix="ltt_frames_")
    try:
        local = os.path.join(tmp, "source" + (Path(source).suffix or ".mp4"))
        _copy_local(storage, source, local)
        pattern = os.path.join(tmp, "frame_%04d.jpg")
        cmd = [ffmpeg_bin(), "-y", "-i", local, "-vf", f"fps=1/{interval}",
               "-frames:v", str(maximum), "-q:v", "2", pattern]
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError("FFmpeg không tách được frame từ video.")
        keys = []
        files = sorted(Path(tmp).glob("frame_*.jpg"))
        if not files:
            raise RuntimeError("Video không tạo được frame hợp lệ.")
        for index, path in enumerate(files, 1):
            if ctx is not None:
                ctx.progress(int(index * 90 / len(files)), "đang lưu frame")
            key = f"{prefix}/{index:04d}.jpg"
            with open(path, "rb") as stream:
                storage.put(key, stream, content_type="image/jpeg")
            keys.append(key)
        return {"image_keys": keys, "count": len(keys), "interval_sec": interval}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _merge_images(params: dict, owner_id: str, storage, ctx) -> dict:
    from PIL import Image, ImageOps
    keys = [_owned(str(key), owner_id) for key in list(params.get("images") or [])]
    if not 2 <= len(keys) <= 12:
        raise ValueError("Cần 2–12 ảnh để ghép.")
    images = []
    for key in keys:
        with storage.open(key) as stream:
            image = Image.open(io.BytesIO(stream.read())).convert("RGB")
            image.thumbnail((1600, 1600))
            images.append(image.copy())
    layout = str(params.get("layout") or "grid")
    cols = len(images) if layout == "horizontal" else 1 if layout == "vertical" else math.ceil(math.sqrt(len(images)))
    rows = math.ceil(len(images) / cols)
    width = max(image.width for image in images); height = max(image.height for image in images)
    sheet = Image.new("RGB", (cols * width, rows * height), "#111111")
    for index, image in enumerate(images):
        fitted = ImageOps.contain(image, (width, height))
        x = (index % cols) * width + (width - fitted.width) // 2
        y = (index // cols) * height + (height - fitted.height) // 2
        sheet.paste(fitted, (x, y))
    output = io.BytesIO(); sheet.save(output, "JPEG", quality=92, optimize=True); output.seek(0)
    key = f"mediatools/{owner_id}/{getattr(ctx, 'job_id', 'adhoc')}/merged.jpg"
    storage.put(key, output, content_type="image/jpeg")
    return {"image_key": key, "source_count": len(keys), "layout": layout}


def _merge_videos(params: dict, owner_id: str, storage, ctx) -> dict:
    from platform_core.media import ffmpeg_bin
    keys = [_owned(str(key), owner_id) for key in list(params.get("videos") or [])]
    if not 2 <= len(keys) <= 12:
        raise ValueError("Cần 2–12 video để nối.")
    tmp = tempfile.mkdtemp(prefix="ltt_merge_video_")
    try:
        local = []
        for index, key in enumerate(keys):
            path = os.path.join(tmp, f"source_{index:03d}{Path(key).suffix or '.mp4'}")
            _copy_local(storage, key, path); local.append(path)
        concat = os.path.join(tmp, "concat.txt")
        with open(concat, "w", encoding="utf-8", newline="\n") as stream:
            for path in local:
                stream.write("file '" + path.replace("'", "'\\''") + "'\n")
        output = os.path.join(tmp, "merged.mp4")
        cmd = [ffmpeg_bin(), "-y", "-f", "concat", "-safe", "0", "-i", concat,
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-movflags", "+faststart", output]
        result = subprocess.run(cmd, capture_output=True, timeout=1800)
        if result.returncode != 0:
            raise RuntimeError("FFmpeg không nối được các video; hãy dùng nguồn cùng kích thước/FPS.")
        key = f"mediatools/{owner_id}/{getattr(ctx, 'job_id', 'adhoc')}/merged.mp4"
        with open(output, "rb") as stream:
            storage.put(key, stream, content_type="video/mp4")
        return {"video_key": key, "source_count": len(keys), "transition": "cut"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _tts(params: dict, owner_id: str, storage, ctx) -> dict:
    import httpx
    model = str(params.get("model") or "gemini-2.5-flash-preview-tts")
    text = str(params.get("text") or "").strip()
    if not text:
        raise ValueError("Thiếu văn bản cần đọc.")
    voice = str(params.get("voice") or "Kore")
    style = str(params.get("style") or "Natural, clear studio narration")
    try:
        from platform_core import api_keys, api_pool
        from platform_core.db import get_session
        from platform_core.models import APIKEY_CAT_CHAT
        gen = get_session(); db = next(gen)
        try:
            key_row = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_CHAT, model=model)
            credential = api_keys.lay_credential(db, key_row); key_id = key_row.id
            db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        credential = os.environ.get("GEMINI_API_KEY", "").strip(); key_id = ""
    if not credential:
        raise RuntimeError("Chưa có API key Gemini cho TTS.")
    body = {
        "contents": [{"parts": [{"text": f"{style}\n\nRead exactly this transcript:\n{text}"}]}],
        "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {
            "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    if ctx is not None: ctx.progress(30, "đang tổng hợp giọng đọc")
    try:
        response = httpx.post(url, headers={"x-goog-api-key": credential}, json=body, timeout=180)
        if response.status_code != 200:
            raise RuntimeError(f"Dịch vụ TTS tạm lỗi (mã {response.status_code}).")
        parts = ((response.json().get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        inline = next((part.get("inlineData") or part.get("inline_data") for part in parts
                       if part.get("inlineData") or part.get("inline_data")), None)
        if not inline or not inline.get("data"):
            raise RuntimeError("Gemini TTS không trả audio.")
        pcm = base64.b64decode(inline["data"])
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(pcm)
        output.seek(0)
        key = f"mediatools/{owner_id}/{getattr(ctx, 'job_id', 'adhoc')}/speech.wav"
        storage.put(key, output, content_type="audio/wav")
        if key_id:
            gen = get_session(); db = next(gen)
            try:
                row = api_keys.lay_key_theo_id(db, key_id)
                if row: api_pool.danh_dau_thanh_cong(db, row); db.commit()
            finally:
                try: next(gen)
                except StopIteration: pass
        if ctx is not None: ctx.progress(100, "xong")
        return {"audio_key": key, "voice": voice, "sample_rate": 24000,
                "credit_cost": max(1, (len(text) + 999) // 1000 * 2)}
    except Exception:
        raise


def _safe_remote_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Chỉ nhận URL HTTPS công khai, không chứa thông tin đăng nhập.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443,
                                                               type=socket.SOCK_STREAM)}
    except OSError:
        raise ValueError("Không phân giải được máy chủ video.") from None
    if not addresses:
        raise ValueError("Máy chủ video không có địa chỉ hợp lệ.")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise ValueError("URL trỏ tới mạng nội bộ hoặc địa chỉ bị chặn.")
    return value


_SOCIAL_DOMAINS = ("youtube.com", "youtu.be", "tiktok.com", "instagram.com",
                   "facebook.com", "fb.watch")


def _social_host(value: str) -> str:
    parsed = urlparse(value)
    host = str(parsed.hostname or "").lower().removeprefix("www.")
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return ""
    return host if any(host == domain or host.endswith(f".{domain}")
                       for domain in _SOCIAL_DOMAINS) else ""


def _download_social(url: str, owner_id: str, storage, ctx) -> dict:
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("Máy chủ chưa cài bộ nhập video mạng xã hội.") from None
    maximum = 250 * 1024 * 1024
    temp_dir = tempfile.mkdtemp(prefix="ltt_social_")

    def match_filter(info, *, incomplete=False):
        if info.get("is_live"):
            return "Không hỗ trợ livestream."
        duration = float(info.get("duration") or 0)
        if duration > 15 * 60:
            return "Video mạng xã hội không được dài quá 15 phút."
        return None

    def progress(event: dict) -> None:
        if ctx is None or event.get("status") != "downloading":
            return
        total = int(event.get("total_bytes") or event.get("total_bytes_estimate") or maximum)
        done = int(event.get("downloaded_bytes") or 0)
        ctx.progress(min(85, max(2, int(done * 85 / max(total, 1)))),
                     "đang nhập video mạng xã hội")

    try:
        options = {
            "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "merge_output_format": "mp4", "outtmpl": os.path.join(temp_dir, "source.%(ext)s"),
            "noplaylist": True, "max_downloads": 1, "max_filesize": maximum,
            "match_filter": match_filter, "progress_hooks": [progress],
            "quiet": True, "no_warnings": True, "cachedir": False,
            "socket_timeout": 20, "retries": 2, "fragment_retries": 2,
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.extract_info(url, download=True)
        except Exception:
            raise RuntimeError("Không tải được video công khai; hãy kiểm tra liên kết và quyền truy cập.") from None
        files = sorted((path for path in Path(temp_dir).iterdir() if path.is_file()),
                       key=lambda path: path.stat().st_mtime, reverse=True)
        if not files:
            raise RuntimeError("Không tìm thấy video sau khi tải.")
        source = files[0]
        if source.stat().st_size <= 0 or source.stat().st_size > maximum:
            raise ValueError("Video mạng xã hội vượt giới hạn 250 MB.")
        from platform_core.media import duration_seconds
        duration = duration_seconds(str(source))
        if duration <= 0 or duration > 15 * 60:
            raise ValueError("Video mạng xã hội không hợp lệ hoặc dài quá 15 phút.")
        key = f"mediatools/{owner_id}/{getattr(ctx, 'job_id', 'adhoc')}/social.mp4"
        with open(source, "rb") as stream:
            storage.put(key, stream, content_type="video/mp4")
        if ctx is not None:
            ctx.progress(100, "xong")
        return {"video_key": key, "source": "social_platform",
                "source_host": _social_host(url), "duration_s": duration, "credit_cost": 2}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _social_import(params: dict, owner_id: str, storage, ctx) -> dict:
    import httpx
    if params.get("confirm_rights") is not True:
        raise ValueError("Bạn phải xác nhận có quyền sử dụng video.")
    requested = str(params.get("url") or "").strip()
    if _social_host(requested):
        return _download_social(requested, owner_id, storage, ctx)
    current = _safe_remote_url(requested)
    maximum = 90 * 1024 * 1024
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp:
            temp_path = temp.name
            with httpx.Client(follow_redirects=False, timeout=60) as client:
                for _redirect in range(4):
                    with client.stream("GET", current, headers={"Accept": "video/*"}) as response:
                        if response.status_code in (301, 302, 303, 307, 308):
                            location = response.headers.get("location", "")
                            if not location:
                                raise RuntimeError("Redirect video thiếu Location.")
                            current = _safe_remote_url(urljoin(current, location)); continue
                        if response.status_code != 200:
                            raise RuntimeError(f"Máy chủ video trả mã {response.status_code}.")
                        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                        if not content_type.startswith("video/"):
                            raise ValueError("URL phải trỏ trực tiếp tới file video, không phải trang web.")
                        declared = int(response.headers.get("content-length") or 0)
                        if declared > maximum:
                            raise ValueError("Video URL vượt giới hạn 90 MB.")
                        total = 0
                        for block in response.iter_bytes(1024 * 1024):
                            total += len(block)
                            if total > maximum:
                                raise ValueError("Video URL vượt giới hạn 90 MB.")
                            temp.write(block)
                            if ctx is not None: ctx.progress(min(80, int(total * 80 / max(declared, maximum))), "đang nhập video")
                        break
                else:
                    raise ValueError("URL chuyển hướng quá nhiều lần.")
        from platform_core.media import duration_seconds
        if duration_seconds(temp_path) <= 0:
            raise ValueError("Nội dung tải về không phải video hợp lệ.")
        key = f"mediatools/{owner_id}/{getattr(ctx, 'job_id', 'adhoc')}/imported.mp4"
        with open(temp_path, "rb") as stream:
            storage.put(key, stream, content_type="video/mp4")
        return {"video_key": key, "source": "owned_https_url", "credit_cost": 2}
    finally:
        if temp_path:
            try: os.unlink(temp_path)
            except OSError: pass


def handle(params: dict, ctx=None) -> dict:
    from platform_core.storage import get_storage
    owner_id = str(params.get("owner_id", ""))
    storage = get_storage()
    if "text" in params:
        return _tts(params, owner_id, storage, ctx)
    if "url" in params:
        return _social_import(params, owner_id, storage, ctx)
    if "interval_sec" in params:
        return _extract(params, owner_id, storage, ctx)
    if "images" in params:
        return _merge_images(params, owner_id, storage, ctx)
    if "videos" in params:
        return _merge_videos(params, owner_id, storage, ctx)
    passthrough = _asset(params, owner_id, storage)
    if passthrough is not None:
        return passthrough
    raise ValueError("Tác vụ media không hợp lệ.")
