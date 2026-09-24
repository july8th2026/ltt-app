"""Webhook subscriptions, transactional outbox, signing and SSRF defence.

Three properties, in the order they matter:

**A webhook must never be able to affect a job.** Delivery is a separate row
written in the same transaction as the job's terminal state (a transactional
outbox), then sent by the worker. A receiver that is down, slow or hostile can
therefore delay nothing and settle nothing differently — the money side has
already committed.

**A webhook must not become an SSRF channel.** The customer chooses the URL, so
the platform is being asked to make an outbound request to an address an
untrusted party picked. Every hop is validated — scheme, host, resolved IP,
and again after each redirect — against loopback, private, link-local and
cloud-metadata ranges. No platform credential is ever attached.

**A receiver must be able to prove the call came from us.** Each delivery is
signed ``HMAC-SHA256(secret, "<timestamp>.<event_id>.<raw body>")``, which binds
the signature to a moment, to one immutable event and to the exact bytes — so a
replayed body, a resent old event or a modified payload all fail verification.

The subscription secret is **encrypted at rest**, not hashed: the server has to
reproduce it to sign with it. That is the opposite requirement to a developer
API key, and mixing the two would break one of them.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import platform_core.an_toan_mang as an_toan_mang
from platform_core.public_api.errors import invalid_request

EVENT_JOB_SUCCEEDED = "job.succeeded"
EVENT_JOB_FAILED = "job.failed"
EVENT_JOB_CANCELLED = "job.cancelled"
# Terminal states only. A "job.running" event would be a second, weaker copy of
# information the caller can already poll for, and every extra event is another
# request the platform makes to an address a customer controls.
TERMINAL_EVENTS = (EVENT_JOB_SUCCEEDED, EVENT_JOB_FAILED, EVENT_JOB_CANCELLED)

SIGNATURE_HEADER = "X-LTT-Signature"
TIMESTAMP_HEADER = "X-LTT-Timestamp"
EVENT_HEADER = "X-LTT-Event-Id"

#: The shape a receiver parses. Immutable within a version: a receiver written
#: against `1` must keep working, so a field may be **added** to the payload but
#: never removed or renamed without moving this number — and moving it is a
#: breaking change the contract checker refuses (EXT-17).
PAYLOAD_VERSION = 1

#: The fields inside `data`. Listed rather than inferred from a sample, because
#: the checker has to compare against something that says what was *promised*,
#: not what one example happened to contain.
PAYLOAD_FIELDS = ("job_id", "tool", "status", "mode")
SIGNATURE_VERSION = "v1"

MAX_ATTEMPTS = 6
BASE_BACKOFF_S = 30
MAX_BACKOFF_S = 6 * 3600
DELIVERY_TIMEOUT_S = 10
MAX_RESPONSE_BYTES = 8 * 1024
MAX_REDIRECTS = 3
SECRET_BYTES = 32

# ⭐ RUT RA 24/09/2026 (plan wf-v2 P7/T1): phep kiem SSRF gio song o
#    `platform_core/an_toan_mang.py` va node `core.http` dung CHUNG no. Ten nay
#    giu lai de nguoi doc `webhooks.py` khong phai doan tap dia chi nam o dau.
METADATA_ADDRESSES = an_toan_mang.METADATA_ADDRESSES

#: Mã lỗi của bộ gác chung → **đúng câu** `/api/v1` vẫn trả trước khi rút ra.
#: Một bảng tra, không phải khớp chuỗi: mô-đun chung không biết gì về webhook,
#: và không được biết.
_THONG_BAO = {
    an_toan_mang.MA_RONG: "A webhook URL is required.",
    an_toan_mang.MA_QUA_DAI: "This webhook URL is too long.",
    an_toan_mang.MA_SO_DO: "Webhook URLs must use https.",
    an_toan_mang.MA_THONG_TIN_DANG_NHAP:
        "Webhook URLs must not contain credentials.",
    an_toan_mang.MA_KHONG_CO_HOST: "This webhook URL has no host.",
    an_toan_mang.MA_KHONG_PHAN_GIAI_DUOC:
        "This webhook host could not be resolved.",
    # Một câu cho **mọi** lớp bị chặn: người gọi không được dùng văn bản lỗi
    # để vẽ bản đồ mạng nội bộ của nền tảng.
    an_toan_mang.MA_KHONG_CHO_PHEP: "This webhook URL is not allowed.",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WebhookError(Exception):
    """A delivery could not be attempted at all (bad target, bad config)."""


# ── Target validation (SSRF) ──────────────────────────────────────────────────

#: Bộ phân giải DNS mặc định **của webhook**. Giữ tên ở đây sau khi phép kiểm
#: được rút ra `an_toan_mang`, vì `tests/test_202_webhook_console.py:42` thay
#: chính tên này để cả cụm test không đi ra DNS thật.
_system_resolver = an_toan_mang._phan_giai_he_thong


def validate_target(url: str, *, require_https: bool = True,
                    resolver=None) -> str:
    """Check a customer-supplied URL, or raise.

    Called both when a subscription is created **and** before every delivery,
    including after each redirect: DNS can change between those moments, and a
    name that resolved to a public address yesterday can point at 127.0.0.1
    today (DNS rebinding).

    ⛔ Không còn giữ phép kiểm ở đây. Hàm này chỉ còn làm **hai** việc
    `an_toan_mang` không được biết: dịch cờ `require_https` của webhook
    thành một `ChinhSach`, và dịch mã lỗi thành đúng câu `/api/v1` trả.
    """
    chinh_sach = an_toan_mang.ChinhSach(
        so_do_cho_phep=frozenset({"https"} if require_https
                                 else {"https", "http"}))
    try:
        # ⚠️ `resolver or _system_resolver` — KHÔNG để `an_toan_mang` tự chọn
        #    bộ phân giải mặc định. Bộ test của webhook thay DNS bằng
        #    `monkeypatch.setattr(webhooks, "_system_resolver", ...)`; nếu
        #    hàm này truyền `None` xuống thì lần thay đó thành **vô hiệu
        #    trong im lặng** và cả cụm test sẽ đi ra mạng thật.
        return an_toan_mang.kiem_url(url, chinh_sach=chinh_sach,
                                     resolver=resolver or _system_resolver)
    except an_toan_mang.LoiChanSSRF as exc:
        raise invalid_request(
            _THONG_BAO.get(exc.ma, _THONG_BAO[an_toan_mang.MA_KHONG_CHO_PHEP])
        ) from exc


# ── Signing ───────────────────────────────────────────────────────────────────

def new_secret() -> str:
    import secrets

    return secrets.token_urlsafe(SECRET_BYTES)


def signature_payload(timestamp: int, event_id: str, body: bytes) -> bytes:
    return b".".join([str(int(timestamp)).encode("ascii"),
                      str(event_id).encode("ascii"), body])


def sign(secret: str, *, timestamp: int, event_id: str, body: bytes) -> str:
    digest = hmac.new(str(secret).encode("utf-8"),
                      signature_payload(timestamp, event_id, body),
                      hashlib.sha256).hexdigest()
    return f"{SIGNATURE_VERSION}={digest}"


def verify(secret: str, *, timestamp: int, event_id: str, body: bytes,
           signature: str, tolerance_s: int = 300) -> bool:
    """True when `signature` was produced by `secret` for this exact event.

    The header may carry several comma-separated signatures — during a secret
    rotation the platform signs with both the new and the old secret — so a
    receiver checking with one of them must accept if **any** entry matches.
    """
    if abs(int(time.time()) - int(timestamp)) > tolerance_s:
        return False
    expected = sign(secret, timestamp=timestamp, event_id=event_id, body=body)
    for candidate in str(signature or "").split(","):
        if hmac.compare_digest(expected, candidate.strip()):
            return True
    return False


def job_event_type(status: str) -> str:
    from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR

    return {JOB_DONE: EVENT_JOB_SUCCEEDED, JOB_ERROR: EVENT_JOB_FAILED,
            JOB_CANCELLED: EVENT_JOB_CANCELLED}.get(str(status), "")


def build_payload(*, event_id: str, event_type: str, job_id: str,
                  tool: str, status: str, mode: str = "live",
                  created_at: datetime | None = None) -> dict:
    """Deliberately thin: identifiers and status, never results or params.

    A webhook goes to an address the platform cannot vouch for, and a
    misconfigured one is a data leak. The receiver fetches what it needs through
    the authenticated API using the ids in here.
    """
    return {
        "id": str(event_id),
        "type": str(event_type),
        "created_at": (created_at or _now()).isoformat(),
        # ``mode`` lets one receiver serve both worlds: a test delivery is
        # signed and shaped exactly like a live one, so the only way to tell
        # them apart is if the payload says so (EXT-12).
        "data": {"job_id": str(job_id), "tool": str(tool or ""),
                 "status": str(status), "mode": str(mode or "live")},
    }


def canonical_body(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


# ── Retry schedule ────────────────────────────────────────────────────────────

def next_attempt_at(attempt: int, *, now: datetime | None = None,
                    jitter: float = 0.0) -> datetime:
    """Exponential backoff with jitter, capped.

    Jitter is passed in rather than drawn here so the schedule is deterministic
    in tests; the worker supplies a random value. Without it, a receiver that
    goes down takes every pending delivery with it and then gets all of them
    back in one synchronised wave when it returns.
    """
    delay = min(MAX_BACKOFF_S, BASE_BACKOFF_S * (2 ** max(0, int(attempt) - 1)))
    spread = delay * 0.2 * max(0.0, min(1.0, float(jitter)))
    return (now or _now()) + timedelta(seconds=delay + spread)


def new_event_id() -> str:
    return uuid.uuid4().hex
