"""Mot ban /developers CO DU LIEU, chay tren cong rieng, KHONG cham production.

Vi sao ton tai: kiem giao dien can trang O TRANG THAI THAT — co khoa, co nhat
ky, co webhook hong, co ngan sach — chu khong phai trang rong. Va lam viec do
tren CSDL that la mot viec khong duoc phep.

    python tools/dev_portal_harness.py [--port 8101]

In ra dia chi + email/mat khau de dang nhap. Ctrl-C de dung.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EMAIL = "dev-ui-qa@example.com"
MATKHAU = "a-good-password-12"
PEPPER = "harness-pepper-" + "t" * 40


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8101)
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="devui-"))
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(tmp / 'devui.db').as_posix()}"
    os.environ["LTT_DATA_DIR"] = str(tmp / "data")

    from platform_core.public_api import keys as devkeys, limits, projects
    os.environ[devkeys.PEPPER_ENV] = PEPPER
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    Base.metadata.create_all(get_engine())

    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=EMAIL, password=MATKHAU)
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 4820, by="harness")
        db.commit()
        _seed(db, user)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "development",
        "LTT_SESSION_SECRET": "harness-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp / "config.json"),
        "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": "text.chat,image.ltt,image.thumbnail",
        # `development` chu khong phai `local-server-test`: o hai ho so kia
        # cookie phien mang co `secure`, va qua http://127.0.0.1 trinh duyet
        # bo cookie do => moi trang bat ve /login va khong soi duoc gi.
    })

    print(f"\n  http://127.0.0.1:{args.port}/developers")
    print(f"  {EMAIL} / {MATKHAU}\n  tmp: {tmp}\n", flush=True)

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


def _seed(db, user) -> None:
    """Trang thai DA DUNG: hai project, bon khoa, nhat ky, webhook hong."""
    import uuid

    from platform_core import secretbox
    from platform_core.public_api import keys as devkeys, projects, webhooks
    from platform_core.public_api.tables import (
        WEBHOOK_DEAD, WEBHOOK_DELIVERED, WEBHOOK_FAILED, ApiBudget,
        ApiRequestLog, WebhookDelivery, WebhookSubscription)

    now = datetime.now(timezone.utc)
    p1 = projects.create(db, user_id=user.id, name="May chu san xuat")
    p2 = projects.create(db, user_id=user.id, name="Thu nghiem noi bo")
    db.flush()

    devkeys.issue(db, user_id=user.id, name="production-web",
                  project_id=p1.id, scopes=["tools:read", "jobs:create", "jobs:read",
                          "artifacts:read"],
                  allowed_tools=["text.chat"],
                  allowed_ips=["203.0.113.4", "198.51.100.0/24"],
                  expires_at=now + timedelta(days=90))
    devkeys.issue(db, user_id=user.id, name="worker-batch", project_id=p1.id,
                  scopes=["tools:read", "jobs:create", "jobs:read",
                          "usage:read", "credits:read", "webhooks:manage"])
    devkeys.issue(db, user_id=user.id, name="ban thu cuc bo", project_id=p2.id,
                  scopes=["tools:read"], mode="test")
    k4, _ = devkeys.issue(db, user_id=user.id, name="khoa cu da thu hoi",
                          project_id=p2.id, scopes=["tools:read"])
    db.flush()
    devkeys.revoke(db, k4)

    kid = devkeys.list_for_user(db, user.id)[0].key_id
    mau = [
        ("POST", "/api/v1/jobs", 200, "", "text.chat", 812, 12),
        ("GET", "/api/v1/tools", 200, "", "", 41, 0),
        ("POST", "/api/v1/jobs", 402, "insufficient_credit", "image.ltt", 96, 0),
        ("POST", "/api/v1/quotes", 200, "", "image.ltt", 154, 0),
        ("POST", "/api/v1/jobs", 429, "rate_limited", "text.chat", 12, 0),
        ("GET", "/api/v1/jobs/{job_id}", 404, "not_found", "", 28, 0),
        ("POST", "/api/v1/jobs", 422, "invalid_input", "image.ltt", 61, 0),
        ("POST", "/api/v1/jobs", 200, "", "image.ltt", 21044, 9),
        ("GET", "/api/v1/usage", 200, "", "", 73, 0),
        ("POST", "/api/v1/jobs", 500, "internal_error", "text.chat", 3120, 0),
    ]
    for i, (method, route, status, code, tool, ms, cre) in enumerate(mau):
        db.add(ApiRequestLog(
            id=str(uuid.uuid4()),
            request_id=f"req_{i:02d}9f4c2ab7e1d6350a8c",
            user_id=user.id, key_id=kid, project_id=p1.id, method=method,
            route=route, status=status, code=code, tool=tool,
            latency_ms=ms, credit_delta=cre,
            created_at=now - timedelta(minutes=7 * i)))

    # A handful of billed API jobs so Usage lines, the tool-breakdown donut and
    # the "jobs via API" count show real data — not just request-log rows.
    from platform_core.models import CREDIT_HOLD, CreditEntry, Job
    from platform_core.public_api.invocation import API_META_KEY
    jobs_mau = [("image.ltt", 296, 6), ("image.ltt", 0, 5), ("text.chat", 187, 4),
                ("vision.ltt", 99, 8), ("audio.ltt", 46, 12), ("text.chat", 0, 1)]
    for i, (tool, credit_net, days_ago) in enumerate(jobs_mau):
        jid = str(uuid.uuid4())
        job = Job(id=jid, user_id=user.id, app_slug="anhnoibo", job_type="api",
                  status="succeeded",
                  params={API_META_KEY: {"tool": tool, "mode": "live",
                                         "key_id": kid}},
                  created_at=now - timedelta(days=days_ago, minutes=i))
        db.add(job)
        if credit_net:
            db.add(CreditEntry(user_id=user.id, job_id=jid, kind=CREDIT_HOLD,
                               delta=-credit_net,
                               created_at=now - timedelta(days=days_ago)))

    db.add(ApiBudget(id=str(uuid.uuid4()), user_id=user.id, scope="account",
                     period="month", amount=2000, thresholds=[50, 80, 100],
                     hard_cap=False, created_at=now))

    sub = WebhookSubscription(
        id=str(uuid.uuid4()), user_id=user.id, key_id=kid,
        url="https://example.com/ltt/hook",
        secret_enc=secretbox.ma_hoa(webhooks.new_secret()),
        events=list(webhooks.TERMINAL_EVENTS), enabled=True, created_at=now)
    db.add(sub)
    db.flush()
    for i, st in enumerate((WEBHOOK_DELIVERED, WEBHOOK_FAILED, WEBHOOK_FAILED,
                            WEBHOOK_DEAD, WEBHOOK_DELIVERED)):
        db.add(WebhookDelivery(
            id=str(uuid.uuid4()), user_id=user.id, subscription_id=sub.id,
            event_id=webhooks.new_event_id(), event_type="job.succeeded",
            status=st, attempts=1 if st == WEBHOOK_DELIVERED else 4,
            last_status_code=200 if st == WEBHOOK_DELIVERED else 503,
            last_error="" if st == WEBHOOK_DELIVERED else "503 Service Unavailable",
            next_attempt_at=now, created_at=now - timedelta(hours=i),
            delivered_at=now if st == WEBHOOK_DELIVERED else None))

    # A couple of notifications so the bell, the overview panel and the
    # notifications page show a real list rather than only an empty state.
    from platform_core.public_api import notifications
    notifications.raise_alert(
        db, user_id=user.id, kind=notifications.WEBHOOK_FAILING,
        subject=sub.id, title="Webhook đang giao hỏng",
        body="Điểm nhận https://example.com/ltt/hook có lần giao bỏ cuộc.",
        now=now - timedelta(hours=2))
    notifications.raise_alert(
        db, user_id=user.id, kind=notifications.KEY_EXPIRING,
        subject=kid, title="Một khóa sắp hết hạn",
        body="Khóa production-web hết hạn trong 90 ngày.",
        now=now - timedelta(days=1))


if __name__ == "__main__":
    raise SystemExit(main())
