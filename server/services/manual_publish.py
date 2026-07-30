"""
manual_publish.py — the web equivalent of the desktop Manual FB / Manual
TikTok tabs (gui/operation_tab.py).

Two things had to change from the desktop design, both forced by the move to
a remote server:

  1. **The video arrives as an upload, not a local path.** The desktop used
     `filedialog.askopenfilename` and passed a path straight into the
     engine. Here the browser streams the file to `temp_video_dir` first and
     the job is given that server-side path.

  2. **Publishing runs as a background job, not inline.** The desktop kept
     the Tk main loop responsive with a worker thread and callbacks. An HTTP
     request cannot wait out a multi-minute upload+publish, so a job id is
     returned immediately and the page polls for status.

Validation, limits and error wording are ported from
`gui/operation_tab.py::_validate` / `_validate_tiktok` so the web rejects
exactly what the desktop rejected, with the same messages.
"""
from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, field

from server.services import ui_constants as UI


# ── Validation (ported verbatim from operation_tab) ───────────────────────────

def validate_facebook(*, account: str, page: str, video_path: str, title: str,
                      description: str, thumbnail: str, schedule: str) -> str | None:
    """Returns the first error message, or None. Order matches the desktop."""
    if not account.strip():
        return "Vui lòng chọn tài khoản (vào tab 🔐 Tài khoản FB để kết nối)"
    if not page.strip() or "Chưa có page" in page:
        return "Vui lòng chọn Page đăng (vào tab 🔐 Tài khoản FB để tick chọn page)"

    err = _validate_video(video_path, UI.VIDEO_EXTS_FB, UI.FB_MAX_VIDEO_BYTES,
                          "Facebook Graph API giới hạn 10 GB.")
    if err:
        return err

    if not title.strip():
        return "Vui lòng nhập tiêu đề video"
    if len(title) > UI.FB_TITLE_LIMIT:
        return (f"Tiêu đề quá dài ({len(title)} ký tự).\n"
                f"Giới hạn: {UI.FB_TITLE_LIMIT} ký tự.")
    if len(description) > UI.FB_DESC_LIMIT:
        return (f"Mô tả quá dài ({len(description)} ký tự).\n"
                f"Giới hạn: {UI.FB_DESC_LIMIT} ký tự.")

    if thumbnail.strip():
        if not os.path.exists(thumbnail):
            return f"File thumbnail không tồn tại:\n{thumbnail}"
        if os.path.isdir(thumbnail):
            return f"Thumbnail là thư mục, không phải ảnh:\n{thumbnail}"
        ext = os.path.splitext(thumbnail)[1].lower()
        if ext not in UI.IMAGE_EXTS:
            return (f"Thumbnail không phải ảnh hợp lệ ({ext}).\n"
                    f"Hỗ trợ: {', '.join(sorted(UI.IMAGE_EXTS))}")

    if schedule.strip():
        from datetime import datetime
        try:
            when = datetime.strptime(schedule.strip(), "%d/%m/%Y %H:%M")
        except ValueError:
            return "Định dạng lịch sai — cần: DD/MM/YYYY HH:MM"
        if when < datetime.now():
            return (f"Lịch đăng đang ở quá khứ:\n{schedule}\n\n"
                    "Để đăng ngay, để trống ô lịch.\n"
                    "Để lên lịch, chọn thời gian tương lai.")
    return None


def validate_tiktok(*, account: str, video_path: str, title: str,
                    description: str) -> str | None:
    if not account.strip() or "Chưa kết nối" in account:
        return ("Chưa có tài khoản TikTok.\n"
                "Vào tab 🎵 Tài khoản TikTok → Kết nối tài khoản trước.")

    err = _validate_video(video_path, UI.VIDEO_EXTS_TT, UI.TT_MAX_VIDEO_BYTES,
                          "TikTok giới hạn 4 GB.")
    if err:
        return err

    # Duration is best-effort: only checked when ffprobe exists, exactly as
    # the desktop did — a missing ffprobe must not block a publish.
    try:
        from core.tiktok.video_validator import is_ffprobe_available, validate_video
        if is_ffprobe_available():
            report = validate_video(video_path)
            dur = getattr(report, "duration_s", 0) or 0
            if dur > UI.TT_MAX_DURATION_S:
                return (f"Video dài {dur:.0f}s, vượt giới hạn TikTok mặc định "
                        f"({UI.TT_MAX_DURATION_S}s = 10 phút).\n"
                        "Nếu app của bạn đã được TikTok unlock 30 phút, "
                        "có thể bỏ qua check này.")
    except Exception:
        pass

    if not title.strip():
        return "Vui lòng nhập tiêu đề (phần 📝 Nội dung phía trên)."
    if len(title) > UI.TT_CAPTION_LIMIT:
        return (f"Tiêu đề quá dài ({len(title)} ký tự).\n"
                f"TikTok giới hạn {UI.TT_CAPTION_LIMIT} ký tự.")
    total = len(title) + len(description)
    if total > UI.TT_CAPTION_LIMIT:
        return (f"Tiêu đề + mô tả tổng cộng {total} ký tự, vượt giới hạn "
                f"caption TikTok ({UI.TT_CAPTION_LIMIT}).")
    return None


def _validate_video(path: str, exts: tuple, max_bytes: int, limit_note: str) -> str | None:
    if not path.strip():
        return "Vui lòng chọn file video"
    if not os.path.exists(path):
        return f"File video không tồn tại:\n{path}"
    if os.path.isdir(path):
        return (f"Đường dẫn là thư mục, không phải file video:\n{path}\n\n"
                f"Hãy chọn file {' / '.join(exts[:3])}")
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        return f"Không đọc được file video:\n{exc}"
    if size == 0:
        return f"File video rỗng (0 byte):\n{path}"
    if size > max_bytes:
        return f"File video quá lớn ({size / 1024 ** 3:.1f} GB).\n{limit_note}"
    ext = os.path.splitext(path)[1].lower()
    if ext not in exts:
        return (f"File không có đuôi video hợp lệ ({ext}).\n"
                f"Hỗ trợ: {', '.join(sorted(exts))}")
    return None


# ── Background publish jobs ───────────────────────────────────────────────────

@dataclass
class PublishJob:
    id: str
    platform: str
    state: str = "queued"          # queued | running | done | error
    status: str = ""
    result_link: str = ""
    error: str = ""
    log: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "platform": self.platform, "state": self.state,
                "status": self.status, "result_link": self.result_link,
                "error": self.error, "log": self.log[-60:]}


class PublishRegistry:
    """Process-wide job table. One orchestrator per process (ADR-005), so a
    plain dict under a lock is sufficient and avoids adding infrastructure."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict = {}

    def create(self, platform: str) -> PublishJob:
        job = PublishJob(id=uuid.uuid4().hex[:12], platform=platform)
        with self._lock:
            self._jobs[job.id] = job
            # Keep the table bounded; manual publishing is low volume.
            if len(self._jobs) > 50:
                for stale in list(self._jobs)[:-50]:
                    self._jobs.pop(stale, None)
        return job

    def get(self, job_id: str) -> PublishJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def latest(self, platform: str) -> PublishJob | None:
        with self._lock:
            jobs = [j for j in self._jobs.values() if j.platform == platform]
        return jobs[-1] if jobs else None


_registry = PublishRegistry()


def registry() -> PublishRegistry:
    return _registry


def _record(job: PublishJob, message: str, level: str = "info") -> None:
    job.log.append({"level": level, "message": str(message)[:400]})


def start_facebook_publish(config: dict, task: dict) -> PublishJob:
    """Hand the task to the same UploadEngine the desktop used."""
    job = _registry.create("facebook")
    stop_event = threading.Event()

    def run() -> None:
        job.state = "running"
        try:
            from core.upload_engine import UploadEngine
            engine = UploadEngine(
                config, stop_event,
                on_log=lambda m, l="info": _record(job, m, l),
                on_status=lambda m: setattr(job, "status", str(m)[:200]),
                on_result=lambda t, status, link: _finish(job, status, link),
                on_done=lambda: None,
                on_error=lambda m: None,   # on_result already carries it
            )
            engine.run(task)
        except Exception as exc:
            job.state, job.error = "error", str(exc)
            _record(job, f"Lỗi: {exc}", "error")
        finally:
            if job.state == "running":
                job.state = "done"

    threading.Thread(target=run, daemon=True, name=f"ManualFB-{job.id}").start()
    return job


def _finish(job: PublishJob, status: str, link: str) -> None:
    if status == "success":
        job.state, job.result_link = "done", link
        _record(job, f"✅ Đăng thành công: {link}", "success")
    else:
        job.state, job.error = "error", link
        _record(job, f"❌ {link}", "error")


def start_tiktok_publish(config: dict, task: dict) -> PublishJob:
    """Hand the task to TikTokPublisher. The compliance guard inside it runs
    server-side, so a tampered form cannot bypass the checks."""
    job = _registry.create("tiktok")
    stop_event = threading.Event()

    def run() -> None:
        job.state = "running"
        try:
            from core.tiktok.publisher_service import TikTokPublisher
            pub = TikTokPublisher(
                config, stop_event,
                on_log=lambda m, l="info": _record(job, m, l),
                on_status=lambda m: setattr(job, "status", str(m)[:200]),
            )
            result = pub.publish(task)
            pid = getattr(result, "external_post_id", "") or "—"
            st = getattr(result, "status", "") or "ok"
            job.state = "done"
            job.status = f"✅ Đăng thành công! publish_id={pid} ({st})"
            _record(job, job.status, "success")
        except Exception as exc:
            job.state = "error"
            job.error = _friendly_tiktok_error(exc)
            _record(job, f"❌ {job.error}", "error")

    threading.Thread(target=run, daemon=True, name=f"ManualTT-{job.id}").start()
    return job


def _friendly_tiktok_error(exc: Exception) -> str:
    """Same mapping as gui/operation_tab.py::_friendly_tiktok_error."""
    try:
        from core.tiktok.compliance_guard import TikTokComplianceError
        if isinstance(exc, TikTokComplianceError):
            return f"{exc.message}\n(Mã: {exc.error_code})"
    except Exception:
        pass
    try:
        from core.tiktok.error_codes import get_friendly_message
        code = getattr(exc, "error_code", "")
        if code:
            return get_friendly_message(code, fallback=str(exc))
    except Exception:
        pass
    return str(exc)


# ── Uploaded video storage ────────────────────────────────────────────────────

def temp_video_dir(config: dict) -> str:
    from core.runtime_paths import resolve_runtime_paths
    configured = str(config.get("temp_video_dir", "") or "").strip()
    target = configured or os.path.join(resolve_runtime_paths().data_dir, "temp_videos")
    os.makedirs(target, exist_ok=True)
    return target


def safe_upload_name(filename: str) -> str:
    """Keep the extension (validation depends on it) but never trust the
    client-supplied path or name."""
    base = os.path.basename(filename or "upload")
    ext = os.path.splitext(base)[1].lower()[:10]
    stem = "".join(c for c in os.path.splitext(base)[0] if c.isalnum() or c in "-_")[:60]
    return f"{stem or 'upload'}_{uuid.uuid4().hex[:8]}{ext}"
