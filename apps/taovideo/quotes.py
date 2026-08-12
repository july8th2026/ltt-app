"""Báo giá ký và submit một-lần cho Seedance.

Quote khóa đúng cấu hình ảnh hưởng giá trước khi app lưu asset hay tạo job.
``intent`` là idempotency key của cả batch: gửi lại cùng form sau double-click,
retry mạng hoặc refresh không tạo thêm job/hold, kể cả job cũ đã terminal.
"""
from __future__ import annotations

import os
import uuid

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select, text

from apps.taovideo import cost
from platform_core.i18n import _ as _t


QUOTE_TTL_S = 15 * 60
_SALT = "ltt-taovideo-quote-v1"
_VERSION = 1


def _serializer() -> URLSafeTimedSerializer:
    secret = (os.environ.get("LTT_SESSION_SECRET") or "").strip()
    if not secret:
        raise RuntimeError(_t("Chưa cấu hình khóa ký báo giá."))
    return URLSafeTimedSerializer(secret)


def _configuration(params: dict, count: int, has_video_input: bool) -> dict:
    priced = dict(params)
    if has_video_input:
        priced["refs"] = [{"kind": "video"}]
    else:
        priced["refs"] = []
    return {
        "model": str(params.get("model") or ""),
        "resolution": str(params.get("resolution") or ""),
        "duration": int(params.get("duration") or 0),
        "aspect_ratio": str(params.get("aspect_ratio") or ""),
        "count": max(1, min(int(count), 2)),
        "has_video_input": bool(has_video_input),
        "unit_hold": cost.customer_charge_cap(priced),
    }


def issue(user_id: str, params: dict, count: int,
          has_video_input: bool) -> tuple[str, dict]:
    payload = {
        "v": _VERSION,
        "user_id": str(user_id),
        "intent": uuid.uuid4().hex,
        **_configuration(params, count, has_video_input),
    }
    return _serializer().dumps(payload, salt=_SALT), payload


def verify(token: str, user_id: str, params: dict, count: int,
           has_video_input: bool, *, max_age: int = QUOTE_TTL_S) -> dict | None:
    if not token:
        return None
    try:
        payload = _serializer().loads(token, salt=_SALT, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    expected = _configuration(params, count, has_video_input)
    if payload.get("v") != _VERSION or payload.get("user_id") != str(user_id):
        return None
    if any(payload.get(key) != value for key, value in expected.items()):
        return None
    intent = str(payload.get("intent") or "")
    if len(intent) != 32:
        return None
    return payload


def _dedupe_key(user_id: str, intent: str, variant: int) -> str:
    from platform_core.job_submit import dedupe_key_for
    return dedupe_key_for("taovideo.generate", {
        "user_id": user_id, "quote_intent": intent, "variant": int(variant),
    })


def _lock_intent(db, user_id: str, intent: str) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {
            "k": f"taovideo-quote:{user_id}:{intent}",
        })


def existing_jobs(db, user_id: str, intent: str, count: int) -> list:
    """Trả đủ batch cũ (mọi status), hoặc danh sách rỗng nếu chưa submit."""
    from platform_core.models import Job
    keys = [_dedupe_key(user_id, intent, k) for k in range(count)]
    rows = db.execute(select(Job).where(
        Job.user_id == user_id,
        Job.app_slug == "taovideo",
        Job.job_type == "taovideo.generate",
        Job.dedupe_key.in_(keys),
    )).scalars().all()
    by_key = {job.dedupe_key: job for job in rows}
    return [by_key[key] for key in keys] if all(key in by_key for key in keys) else []


def submit_batch(db, *, user_id: str, quote: dict, base_params: dict,
                 fixed_seed: int | None = None,
                 variant_refs: list[list[dict]] | None = None) -> list:
    """Tạo/reuse nguyên batch dưới khóa quote, giữ credit đúng một lần."""
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import Job

    intent = str(quote["intent"])
    count = int(quote["count"])
    if variant_refs is not None and len(variant_refs) != count:
        raise ValueError(_t("Số bộ tham chiếu không khớp batch."))
    _lock_intent(db, user_id, intent)
    prior = existing_jobs(db, user_id, intent, count)
    if prior:
        return prior

    jobs = []
    for variant in range(count):
        key = _dedupe_key(user_id, intent, variant)
        old = db.execute(select(Job).where(
            Job.user_id == user_id, Job.app_slug == "taovideo",
            Job.job_type == "taovideo.generate", Job.dedupe_key == key,
        )).scalar_one_or_none()
        if old is not None:
            jobs.append(old)
            continue
        params = dict(base_params, _n=variant,
                      _quote_intent=intent, _quote_version=_VERSION)
        if variant_refs is not None:
            params["refs"] = list(variant_refs[variant])
        if fixed_seed is not None:
            params["seed"] = (fixed_seed + variant) % 2_147_483_648
        jobs.append(submit_with_credit(
            db, user_id=user_id, app_slug="taovideo",
            job_type="taovideo.generate", params=params, dedupe_key=key,
        ))
    return jobs
