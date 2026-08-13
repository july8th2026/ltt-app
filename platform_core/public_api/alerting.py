"""Detecting the conditions worth telling a developer about.

Kept apart from :mod:`notifications`, which only stores and deduplicates: this
module decides *when* something is true. The split matters because the scan runs
on a schedule and will re-detect the same condition every pass — the storage
layer is what makes that harmless, so the detection layer is free to be simple
and stateless.

Every condition here is one the customer can act on. "Your balance is low" is
actionable; "your job took 4 seconds" is not, and an alert nobody can act on
teaches people to ignore the channel.
Alert text is translated **when it is raised**, not when it is read: the row
stores what a customer will see, and the scan runs in the worker where there is
no request locale. That freezes an alert in the platform's default language,
which is the honest trade for not building a message-catalogue layer for eight
sentences.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from platform_core.i18n import _ as _t
from platform_core.public_api import budgets, notifications

#: Warn when the balance would not cover a handful of average calls. Not a
#: percentage of anything: an account that tops up in small amounts would be
#: permanently "low", and one that tops up in large amounts would be warned too
#: late.
LOW_CREDIT_THRESHOLD = 20

#: Warn this far ahead of a key's expiry. Long enough to rotate calmly during a
#: working week.
KEY_EXPIRY_WARNING = timedelta(days=7)

#: A webhook endpoint that produced this many dead deliveries in a day is not
#: having a bad moment; it is broken.
DEAD_DELIVERY_THRESHOLD = 3

QUOTA_NEAR_PERCENT = 80


def _now() -> datetime:
    return datetime.now(timezone.utc)


def scan_account(db, *, user_id: str, config=None,
                 now: datetime | None = None) -> list:
    """Raise whatever is true for this account. Returns the new alerts.

    Suppressed duplicates are simply absent from the result, so a caller can
    log "3 new alerts" honestly.
    """
    current = now or _now()
    raised = []
    for finding in (_low_credit(db, user_id, current),
                    *_budget_alerts(db, user_id, current),
                    *_quota_alerts(db, user_id, config, current),
                    *_expiring_keys(db, user_id, current),
                    *_failing_webhooks(db, user_id, current)):
        if finding is None:
            continue
        row = notifications.raise_alert(db, user_id=user_id, now=current,
                                        **finding)
        if row is not None:
            raised.append(row)
    return raised


def _low_credit(db, user_id: str, now: datetime):
    from platform_core import credit

    balance = credit.so_du(db, user_id)
    if balance > LOW_CREDIT_THRESHOLD:
        return None
    return {
        "kind": notifications.LOW_CREDIT,
        # The subject is the balance bucket, not the exact number: otherwise
        # every credit spent would be a "new" subject and the cooldown would
        # never apply.
        "subject": "balance",
        "title": _t("Số dư còn %(n)s credit") % {"n": balance},
        "body": _t("Lời gọi API sẽ bị từ chối khi không đủ credit cho báo "
                   "giá. Nạp thêm ở /nap."),
    }


def _budget_alerts(db, user_id: str, now: datetime) -> list:
    found = []
    for budget in budgets.list_for(db, user_id=user_id):
        state = budgets.status(db, budget, now=now)
        for threshold in state["crossed"]:
            exceeded = int(threshold) >= 100
            found.append({
                "kind": (notifications.BUDGET_EXCEEDED if exceeded
                         else notifications.BUDGET_THRESHOLD),
                # One subject per budget *and* threshold: crossing 80% and then
                # 100% are two different pieces of news.
                "subject": f"{budget.id}:{threshold}",
                "title": _t("Đã dùng %(percent)s%% ngân sách %(period)s") % {
                    "percent": state["percent"], "period": budget.period},
                "body": (
                    _t("%(spent)s/%(amount)s credit trong kỳ này.") % {
                        "spent": state["spent"], "amount": state["amount"]}
                    + (" " + _t("Ngân sách cứng: lời gọi mới bị từ chối.")
                       if budget.hard_cap and exceeded else "")),
            })
    return found


def _quota_alerts(db, user_id: str, config, now: datetime) -> list:
    ceiling = int(getattr(config, "daily_credit_limit", 0) or 0)
    if ceiling <= 0:
        return []
    spent = budgets.api_spend_since(
        db, user_id=user_id, since=budgets.window_start(budgets.PERIOD_DAY,
                                                        now=now))
    percent = int(spent * 100 / max(1, ceiling))
    if percent < QUOTA_NEAR_PERCENT:
        return []
    exceeded = percent >= 100
    return [{
        "kind": (notifications.QUOTA_EXCEEDED if exceeded
                 else notifications.QUOTA_NEAR),
        "subject": f"daily:{now:%Y-%m-%d}",
        "title": _t("Đã dùng %(percent)s%% hạn mức credit ngày của máy chủ")
        % {"percent": percent},
        "body": _t("%(spent)s/%(ceiling)s credit hôm nay. Hạn mức này do quản "
                   "trị viên đặt và không nới được từ phía tài khoản.") % {
                       "spent": spent, "ceiling": ceiling},
    }]


def _expiring_keys(db, user_id: str, now: datetime) -> list:
    from platform_core.public_api.tables import DeveloperApiKey

    rows = db.execute(select(DeveloperApiKey).where(
        DeveloperApiKey.user_id == str(user_id),
        DeveloperApiKey.revoked_at.is_(None),
        DeveloperApiKey.expires_at.is_not(None))).scalars().all()
    found = []
    for key in rows:
        expires = key.expires_at
        if expires is None:
            continue
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if not now < expires <= now + KEY_EXPIRY_WARNING:
            continue
        days = max(0, (expires - now).days)
        found.append({
            "kind": notifications.KEY_EXPIRING,
            "subject": key.key_id,
            "title": _t("Khóa API hết hạn sau %(days)s ngày") % {"days": days},
            "body": _t("Khóa %(key)s (%(name)s) hết hạn %(date)s. Tạo khóa "
                       "mới, chuyển ứng dụng sang, rồi thu hồi khóa cũ.") % {
                           "key": key.key_id,
                           "name": key.name or _t("không tên"),
                           "date": f"{expires:%Y-%m-%d}"},
        })
    return found


def _failing_webhooks(db, user_id: str, now: datetime) -> list:
    from platform_core.public_api.tables import (WEBHOOK_DEAD, WebhookDelivery,
                                                 WebhookSubscription)

    since = now - timedelta(days=1)
    rows = db.execute(
        select(WebhookDelivery.subscription_id, func.count(WebhookDelivery.id))
        .where(WebhookDelivery.user_id == str(user_id),
               WebhookDelivery.status == WEBHOOK_DEAD,
               WebhookDelivery.created_at >= since)
        .group_by(WebhookDelivery.subscription_id)).all()
    found = []
    for subscription_id, total in rows:
        if int(total) < DEAD_DELIVERY_THRESHOLD:
            continue
        subscription = db.get(WebhookSubscription, subscription_id)
        url = subscription.url if subscription is not None else subscription_id
        found.append({
            "kind": notifications.WEBHOOK_FAILING,
            "subject": str(subscription_id),
            "title": _t("%(n)s sự kiện webhook không giao được") % {
                "n": int(total)},
            "body": _t("Điểm nhận %(url)s đã bỏ cuộc sau đủ số lần thử. Job "
                       "và credit không bị ảnh hưởng; gửi lại từ khu Webhook "
                       "sau khi sửa xong.") % {"url": url},
        })
    return found


def scan_all(db, *, config=None, now: datetime | None = None) -> int:
    """Scan every account that has touched the API. Returns alerts raised.

    Scoped to API users rather than every account on the platform: somebody who
    has never made an API call cannot have an API budget, an expiring key or a
    failing webhook, and scanning them would grow this job with the user table
    instead of with the API.
    """
    from platform_core.public_api.tables import DeveloperApiKey

    owners = [row[0] for row in db.execute(
        select(DeveloperApiKey.user_id).distinct()).all()]
    total = 0
    for user_id in owners:
        for row in scan_account(db, user_id=user_id, config=config, now=now):
            notifications.send_email_for(db, row)
            total += 1
    return total
