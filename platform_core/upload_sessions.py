"""Upload staging lifecycle dùng chung cho app file/media.

File mới luôn vào ``staging/``. Paid input chỉ promote sau khi job giữ credit.
Editor có project bền vững được attach source vào project với TTL riêng; đây
không phải paid input và không được đi vòng qua ``promote(job)``. Session hết
hạn/failure có sweeper idempotent để browser bỏ dở không thành rác vĩnh viễn.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import PurePath
import io
import logging
import re
import uuid

from sqlalchemy import func, select

from platform_core.i18n import _ as _t
from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR, Job,
                                  UPLOAD_ATTACHED, UPLOAD_DELETED, UPLOAD_PENDING,
                                  UPLOAD_PROMOTED, UPLOAD_READY, UploadSession)


DEFAULT_TTL_S = 60 * 60
PROMOTED_RETENTION_DAYS = 30
DRAFT_RETENTION_DAYS = 30
MAX_ACTIVE_SESSIONS = 20
MAX_ACTIVE_BYTES = 2 * 1024 * 1024 * 1024
MAX_CREATED_PER_MINUTE = 12
#: Slug app hop le cho mot khoa staging.
#:
#: 🔴 **DAU GACH DUOI DUOC THEM 2026-09-03, va truoc do no la mot loi that.**
#:
#:    Ban cu la `^[a-z0-9][a-z0-9-]{0,63}$` — khong co `_`. Ket qua: **7 trong 19
#:    app** cua kho bi `create()` tu choi thang, trong do co `ltt_voice`
#:    (`lifecycle="released"`, dang ban) va `ltt_llm`:
#:
#:        bi tu choi: asv_gpu, asv_media, asv_voice, auto_scan_video,
#:                    ltt_llm, ltt_voice, prompt_ai_ommi
#:
#:    Va no khong lo ra suot mot thoi gian dai vi hai ly do cong lai: app duy
#:    nhat dang goi `upload_sessions` la `autosubvideo` — mot trong so it slug
#:    khong co gach duoi — con `tests/conftest.py:71` dat `APP_THU_SLUG="appthu"`,
#:    nen ca bo test chua bao gio di qua nhanh nay voi mot slug that.
#:
#: ⭐ Day khong phai mot han che co chu y: `AppManifest` khong cam gach duoi o
#:    dau ca, va bay app dang dung no. Trong mot duong dan luu tru, `_` an toan
#:    ngang `-`, va `storage._safe_key` van la lop chan cuoi.
#:
#: ⛔ Doi nay CHI NOI RONG: moi slug hop le truoc day van hop le. Khong nguoi goi
#:    nao doi hanh vi. Xem `tests/test_429_asv_v4_dau_vao_lon.py` muc 3.
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
log = logging.getLogger(__name__)


class UploadSessionError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _matches_type(content_type: str, allowed: tuple[str, ...]) -> bool:
    return any(content_type == item or
               (item.endswith("/*") and content_type.startswith(item[:-1]))
               for item in allowed)


def create(db, *, user_id: str, app_slug: str, filename: str,
           content_type: str, expected_size: int, max_size: int,
           allowed_types: tuple[str, ...], ttl_s: int = DEFAULT_TTL_S,
           now: datetime | None = None) -> UploadSession:
    current = now or _now()
    if not _SLUG.fullmatch(str(app_slug or "")):
        raise UploadSessionError(_t("Ứng dụng upload không hợp lệ."))
    name = PurePath(str(filename or "").replace("\\", "/")).name[:255]
    if not name:
        raise UploadSessionError(_t("Tên file không hợp lệ."))
    ct = str(content_type or "application/octet-stream").split(";", 1)[0].strip().lower()
    if not _matches_type(ct, allowed_types):
        raise UploadSessionError(_t("Loại file không được hỗ trợ."))
    try:
        size = int(expected_size)
    except (TypeError, ValueError) as exc:
        raise UploadSessionError(_t("Kích thước file không hợp lệ.")) from exc
    if size <= 0 or size > int(max_size):
        raise UploadSessionError(_t("Kích thước file vượt giới hạn."))

    active = (UPLOAD_PENDING, UPLOAD_READY)
    active_count, active_bytes = db.execute(select(
        func.count(UploadSession.id),
        func.coalesce(func.sum(UploadSession.expected_size), 0),
    ).where(
        UploadSession.user_id == user_id,
        UploadSession.status.in_(active),
        UploadSession.expires_at > current,
    )).one()
    recent = db.execute(select(func.count(UploadSession.id)).where(
        UploadSession.user_id == user_id,
        UploadSession.created_at >= current - timedelta(minutes=1),
    )).scalar_one()
    if int(active_count or 0) >= MAX_ACTIVE_SESSIONS or \
            int(active_bytes or 0) + size > MAX_ACTIVE_BYTES:
        raise UploadSessionError(_t("Đã đạt giới hạn upload đang chờ."))
    if int(recent or 0) >= MAX_CREATED_PER_MINUTE:
        raise UploadSessionError(_t("Tạo quá nhiều lượt upload. Vui lòng thử lại sau."))

    session_id = str(uuid.uuid4())
    ext = PurePath(name).suffix.lower()[:12]
    session = UploadSession(
        id=session_id,
        user_id=user_id, app_slug=app_slug, filename=name, content_type=ct,
        expected_size=size, expires_at=current + timedelta(seconds=max(60, int(ttl_s))),
        staging_key=f"staging/{user_id}/{app_slug}/{session_id}/payload{ext}",
    )
    db.add(session); db.flush()
    return session


def owned(db, *, session_id: str = "", staging_key: str = "",
          user_id: str, app_slug: str) -> UploadSession | None:
    stmt = select(UploadSession).where(
        UploadSession.user_id == user_id, UploadSession.app_slug == app_slug)
    if session_id:
        stmt = stmt.where(UploadSession.id == session_id)
    elif staging_key:
        stmt = stmt.where(UploadSession.staging_key == staging_key)
    else:
        return None
    return db.execute(stmt).scalar_one_or_none()


def upload_target(storage, session: UploadSession):
    return storage.try_put_url(
        session.staging_key,
        ttl_s=max(60, int((_utc(session.expires_at) - _now()).total_seconds())),
        content_type=session.content_type,
    )


def _signature_ok(content_type: str, head: bytes) -> bool:
    ct = content_type.lower()
    if ct in {"application/octet-stream"}:
        return bool(head)
    if ct in {"image/jpeg", "image/jpg"}:
        return head.startswith(b"\xff\xd8\xff")
    if ct == "image/png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ct == "image/webp":
        return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    if ct in {"video/mp4", "video/quicktime", "video/x-m4v"}:
        return len(head) >= 12 and head[4:8] == b"ftyp"
    if ct in {"video/webm", "video/x-matroska"}:
        return head.startswith(b"\x1aE\xdf\xa3")
    if ct == "video/x-msvideo":
        return head.startswith(b"RIFF") and head[8:12] == b"AVI "
    if ct in {"audio/wav", "audio/x-wav"}:
        return head.startswith(b"RIFF") and head[8:12] == b"WAVE"
    if ct in {"audio/mpeg", "audio/mp3"}:
        return head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF)
    if ct in {"audio/mp4", "audio/x-m4a"}:
        return len(head) >= 12 and head[4:8] == b"ftyp"

    # ── TAI LIEU (H44 B1, 06/09) ─────────────────────────────────────────────
    #
    # 🔴 Truoc hom nay ham nay tra `False` cho MOI kieu tai lieu, nen duong
    #    upload cua nen tang KHONG NHAN DUOC mot tai lieu nao. Do la mot khoang
    #    thieu cua hop dong, khong phai mot chinh sach — `chatltt` la app dau
    #    tien can no (P06 doc PDF/txt/md/csv/json).
    if ct == "application/pdf":
        # PDF co magic THAT. Kiem no la mot cai loi bao mat that: mot tep `.exe`
        # doi ten thanh `.pdf` bi chan o DAY, truoc khi cham bo trich.
        return head.startswith(b"%PDF-")
    if ct in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }:
        # ⭐ `.docx`/`.pptx` la ZIP (OOXML) — magic `PK\x03\x04`. Kiem duoc, va
        #    no chan mot `.exe` doi ten y het truong hop PDF.
        #
        # ⚠️ Nhung no KHONG phan biet duoc docx voi mot zip bat ky. Do la gioi
        #    han THAT cua tang nay, va no chap nhan duoc: bo trich phia sau se
        #    tu choi mot zip khong phai OOXML, va no tu choi bang `KhongDocDuoc`
        #    — dung loai loi, dung ai co loi.
        return head.startswith(b"PK\x03\x04")
    if ct in {"text/plain", "text/markdown", "text/csv", "application/json",
              "text/html"}:
        # ⛔ Chu thuan KHONG co magic — nen dieu kien phai la mot TINH CHAT,
        #    khong phai mot tien to: khong byte NUL, va giai duoc UTF-8. Mot tep
        #    nhi phan gan nhu luon co NUL trong 512 byte dau; mot tep chu thi
        #    khong bao gio.
        if b"\x00" in head:
            return False
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            # ⭐ Cat giua mot ky tu nhieu byte cung nem — nen chi tu choi khi loi
            #    KHONG nam o duoi cung cua doan da doc.
            try:
                head[:-4].decode("utf-8")
            except UnicodeDecodeError:
                return False
        return bool(head)
    return False


def confirm(db, storage, session: UploadSession,
            *, now: datetime | None = None) -> UploadSession:
    current = now or _now()
    if session.status == UPLOAD_READY:
        return session
    if session.status != UPLOAD_PENDING or _utc(session.expires_at) <= current:
        raise UploadSessionError(_t("Vé upload đã hết hạn hoặc đã được dùng."))
    if not storage.exists(session.staging_key):
        raise UploadSessionError(_t("File chưa upload xong."))
    actual = int(storage.size(session.staging_key))
    if actual != int(session.expected_size):
        raise UploadSessionError(_t("Kích thước file thực tế không khớp khai báo."))
    stream = storage.open(session.staging_key)
    try:
        head = stream.read(32)
    finally:
        stream.close()
    if not _signature_ok(session.content_type, head):
        raise UploadSessionError(_t("Nội dung file không khớp định dạng khai báo."))
    session.actual_size = actual
    session.status = UPLOAD_READY
    session.updated_at = current
    db.flush()
    return session


def stage_bytes(db, storage, *, user_id: str, app_slug: str, filename: str,
                content_type: str, data: bytes, max_size: int,
                allowed_types: tuple[str, ...],
                ttl_s: int = DEFAULT_TTL_S) -> UploadSession:
    """Stage multipart nhỏ bằng cùng contract với direct upload."""
    session = create(
        db, user_id=user_id, app_slug=app_slug, filename=filename,
        content_type=content_type, expected_size=len(data), max_size=max_size,
        allowed_types=allowed_types, ttl_s=ttl_s,
    )
    storage.put(session.staging_key, io.BytesIO(data), content_type=session.content_type)
    return confirm(db, storage, session)


def _la_job_thu(job: Job) -> bool:
    """Job này có phải job chế độ thử (khoá `ltt_tk_`) hay không.

    Cửa "phải giữ credit mới được lưu file" tồn tại để không ai biến input của
    job thành kho lưu trữ miễn phí. Một job chế độ thử **không bao giờ** giữ
    credit — đó chính là lời hứa của khoá thử — nên với nó cửa đó không phải một
    hàng rào mà là một bức tường: mọi tool nhận file trở thành không thử được,
    và đúng cái mà chế độ thử sinh ra để cho phép lại là cái nó chặn.

    Trần chống lạm dụng của chế độ thử nằm ở chỗ khác và vẫn nguyên: giới hạn
    kích thước, giới hạn nhịp gọi, và hạn lưu trữ của upload đã promote.
    """
    from platform_core.public_api import sandbox

    return sandbox.is_test(sandbox.mode_of_job(job))


def promote(db, storage, session: UploadSession, *, job: Job,
            final_key: str, now: datetime | None = None) -> str:
    from platform_core import credit, job_events
    current = now or _now()
    if session.user_id != job.user_id or session.app_slug != job.app_slug:
        raise UploadSessionError(_t("Upload không thuộc job này."))
    if session.status == UPLOAD_PROMOTED:
        if session.job_id != job.id or session.final_key != final_key:
            raise UploadSessionError(_t("Upload đã được dùng cho job khác."))
        return session.final_key
    confirm(db, storage, session, now=current)
    if credit.so_da_giu(db, job.id) <= 0 and not _la_job_thu(job):
        raise UploadSessionError(_t("Chưa giữ credit nên không thể lưu file."))
    try:
        stored = storage.promote(
            session.staging_key, final_key, content_type=session.content_type)
        if stored.size != session.actual_size:
            raise UploadSessionError(_t("Promote file không toàn vẹn."))
        session.status = UPLOAD_PROMOTED
        session.final_key = stored.key
        session.job_id = job.id
        session.expires_at = current + timedelta(days=PROMOTED_RETENTION_DAYS)
        session.updated_at = current
        job_events.append(
            db, job, "input_promoted", visibility=job_events.INTERNAL,
            details={"upload_id": session.id, "bytes": session.actual_size,
                     "content_type": session.content_type},
            event_key=f"input-promoted:{session.id}",
        )
        db.flush()
    except Exception:
        # Object storage không tham gia transaction CSDL. Nếu validation/flush
        # sau lệnh move lỗi, trả file về staging để retry/sweeper còn nhìn thấy.
        compensate(storage, [(session.staging_key, final_key,
                              session.content_type)])
        raise
    return stored.key


def attach_to_project(db, storage, session: UploadSession, *, project_id: str,
                      final_key: str, now: datetime | None = None) -> str:
    """Attach a validated source to an owner-scoped editor project.

    This transition is deliberately separate from ``promote``: a draft source
    is needed before a paid Job exists, while paid inputs must still prove a
    credit hold. The caller owns the AppProject ownership/revision check and
    must compensate the object move if its database commit fails.
    """
    current = now or _now()
    pid = str(project_id or "").strip()
    prefix = f"{session.app_slug}/{session.user_id}/"
    if not pid or not str(final_key).startswith(prefix):
        raise UploadSessionError(_t("Đích project upload không hợp lệ."))
    if session.status == UPLOAD_ATTACHED:
        if session.project_id != pid or session.final_key != final_key:
            raise UploadSessionError(_t("Upload đã gắn vào project khác."))
        session.expires_at = current + timedelta(days=DRAFT_RETENTION_DAYS)
        session.updated_at = current
        db.flush()
        return session.final_key
    if session.status == UPLOAD_PROMOTED:
        raise UploadSessionError(_t("Upload đã được dùng cho job."))
    confirm(db, storage, session, now=current)
    try:
        stored = storage.promote(
            session.staging_key, final_key, content_type=session.content_type)
        if stored.size != session.actual_size:
            raise UploadSessionError(_t("Attach file không toàn vẹn."))
        session.status = UPLOAD_ATTACHED
        session.final_key = stored.key
        session.project_id = pid
        session.expires_at = current + timedelta(days=DRAFT_RETENTION_DAYS)
        session.updated_at = current
        db.flush()
    except Exception:
        compensate(storage, [(session.staging_key, final_key,
                              session.content_type)])
        raise
    return stored.key


def project_attachment(db, *, user_id: str, app_slug: str,
                       project_id: str, final_key: str) -> UploadSession | None:
    return db.execute(select(UploadSession).where(
        UploadSession.user_id == user_id,
        UploadSession.app_slug == app_slug,
        UploadSession.project_id == project_id,
        UploadSession.final_key == final_key,
    )).scalar_one_or_none()


def touch_project_attachment(db, session: UploadSession,
                             *, now: datetime | None = None) -> bool:
    if session.status != UPLOAD_ATTACHED:
        return False
    current = now or _now()
    session.expires_at = current + timedelta(days=DRAFT_RETENTION_DAYS)
    session.updated_at = current
    db.flush()
    return True


def compensate(storage, promotions: list[tuple[str, str, str]]) -> int:
    """Đảo các move chưa commit, theo thứ tự ngược; best-effort và idempotent.

    Route gọi hàm này sau ``db.rollback()`` nếu commit chứa job/hold/session lỗi.
    Nhờ key đích xác định trước, file không thành orphan vô danh ngoài CSDL.
    """
    restored = 0
    for staging_key, final_key, content_type in reversed(promotions):
        try:
            if storage.exists(final_key) and not storage.exists(staging_key):
                storage.promote(final_key, staging_key, content_type=content_type)
                restored += 1
        except Exception:  # noqa: BLE001 - keep reverting the remaining files
            log.exception("khong the tra artifact ve staging: %s", final_key)
    return restored


def _stored_key(session: UploadSession) -> str:
    return (session.final_key if session.status in (UPLOAD_ATTACHED, UPLOAD_PROMOTED)
            else session.staging_key)


def sweep(db, storage, *, now: datetime | None = None,
          dry_run: bool = True, limit: int = 500) -> dict:
    current = now or _now()
    rows = list(db.execute(select(UploadSession).where(
        UploadSession.status.in_((UPLOAD_PENDING, UPLOAD_READY, UPLOAD_ATTACHED,
                                  UPLOAD_PROMOTED)),
        UploadSession.expires_at <= current,
    ).order_by(UploadSession.expires_at).limit(max(1, min(int(limit), 5000)))).scalars())
    due = []; skipped_active = 0; errors = 0; deleted = 0
    for session in rows:
        if session.job_id:
            job = db.get(Job, session.job_id)
            if job is not None and job.status not in (JOB_DONE, JOB_ERROR, JOB_CANCELLED):
                skipped_active += 1
                continue
        key = _stored_key(session)
        due.append({"upload_id": session.id, "status": session.status,
                    "bytes": session.actual_size or session.expected_size})
        if dry_run:
            continue
        try:
            storage.delete(key)
            session.status = UPLOAD_DELETED
            session.updated_at = current
            deleted += 1
        except Exception:  # noqa: BLE001 - report keeps sweeper progressing
            log.exception("cleanup upload session %s that bai", session.id)
            errors += 1
    if not dry_run:
        db.flush()
    return {"due": len(due), "deleted": deleted, "errors": errors,
            "skipped_active": skipped_active, "items": due}


def cleanup_failed_job(db, storage, job: Job) -> int:
    """Xóa input promoted của job terminal lỗi/hủy; gọi lại không đổi kết quả."""
    if job.status not in (JOB_ERROR, JOB_CANCELLED):
        return 0
    rows = list(db.execute(select(UploadSession).where(
        UploadSession.job_id == job.id,
        UploadSession.status == UPLOAD_PROMOTED,
    )).scalars())
    removed = 0
    for session in rows:
        storage.delete(session.final_key)
        session.status = UPLOAD_DELETED
        session.updated_at = _now()
        removed += 1
    if removed:
        from platform_core import job_events
        job_events.append(
            db, job, "input_cleaned", visibility=job_events.INTERNAL,
            details={"uploads": removed}, event_key="failed-input-cleanup",
        )
    db.flush()
    return removed


def reconcile(db, storage, *, limit: int = 1000) -> dict:
    rows = list(db.execute(select(UploadSession).where(
        UploadSession.status.in_((UPLOAD_PENDING, UPLOAD_READY, UPLOAD_ATTACHED,
                                  UPLOAD_PROMOTED)),
    ).limit(max(1, min(int(limit), 5000)))).scalars())
    missing = []
    for session in rows:
        key = _stored_key(session)
        if not storage.exists(key):
            missing.append({"upload_id": session.id, "status": session.status,
                            "job_id": session.job_id})
    return {"checked": len(rows), "missing": len(missing), "items": missing}
