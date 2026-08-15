"""Lease có tên, và outbox nhận việc đúng cách.

`test_214` chứng minh những tính chất này dưới **tranh chấp thật** và chỉ chạy
trên PostgreSQL. File này kiểm chính cơ chế, tuần tự, nên nó chạy ở mọi nơi và
chỉ ra *cái gì* hỏng khi `test_214` đỏ.

Hai file cần cả hai: một cái nói cơ chế có đúng không, cái kia nói cơ chế có
được dùng đúng chỗ không.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'lease.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session

    Base.metadata.create_all(get_engine())
    gen = get_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


# ── Lease ────────────────────────────────────────────────────────────────────

def test_chi_mot_nguoi_giu_duoc_lease(db):
    from platform_core import leases

    dau = leases.acquire(db, name=leases.MAINTENANCE, holder="tien-trinh-A")
    sau = leases.acquire(db, name=leases.MAINTENANCE, holder="tien-trinh-B")

    assert dau is not None
    assert sau is None, "hai tiến trình cùng tưởng mình được chạy việc nền"
    assert leases.current_holder(db, name=leases.MAINTENANCE) == "tien-trinh-A"


def test_khong_giu_duoc_khong_phai_loi(db):
    """`None` là câu trả lời bình thường cho "tôi có phải người chạy không".

    Nếu nó là ngoại lệ thì mọi tiến trình không giành được lease sẽ ghi một vệt
    lỗi mỗi chu kỳ, và log của người vận hành đầy thứ không phải sự cố.
    """
    from platform_core import leases

    leases.acquire(db, name=leases.MAINTENANCE, holder="A")
    assert leases.acquire(db, name=leases.MAINTENANCE, holder="B") is None


def test_hai_lease_khac_ten_khong_dam_nhau(db):
    from platform_core import leases

    assert leases.acquire(db, name=leases.MAINTENANCE, holder="A") is not None
    assert leases.acquire(db, name=leases.WEB, holder="A") is not None


def test_chu_chet_thi_lease_het_han_va_nguoi_khac_nhan_duoc(db):
    """Tự lành mới là tính chất quan trọng nhất.

    Lease không hết hạn nghĩa là một tiến trình bị kill sẽ làm việc nền **dừng
    vĩnh viễn và im lặng** — không job nào hỏng để ai nhận ra, chỉ là webhook
    không còn được gửi nữa.
    """
    from platform_core import leases
    from platform_core.models import SingletonLease

    chet = leases.acquire(db, name=leases.MAINTENANCE, holder="da-chet")
    assert chet is not None

    # Giả lập: chủ ngừng đập nhịp từ lâu.
    row = db.get(SingletonLease, chet.id)
    row.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    db.commit()

    moi = leases.acquire(db, name=leases.MAINTENANCE, holder="con-song")
    assert moi is not None, "lease của tiến trình đã chết không bao giờ nhả"
    assert leases.current_holder(db, name=leases.MAINTENANCE) == "con-song"


def test_dap_nhip_giu_duoc_lease_va_chan_nguoi_khac(db):
    from platform_core import leases
    from platform_core.models import SingletonLease

    lease = leases.acquire(db, name=leases.MAINTENANCE, holder="A")
    row = db.get(SingletonLease, lease.id)
    row.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    db.commit()

    assert leases.heartbeat(db, lease) is True
    assert leases.acquire(db, name=leases.MAINTENANCE, holder="B") is None


def test_mat_lease_thi_dap_nhip_bao_that_bai(db):
    """Người giữ phải biết mình mất quyền, để dừng ngay.

    Tiếp tục làm việc nền sau khi lease đã sang tay là đúng cái mà lease sinh ra
    để ngăn.
    """
    from platform_core import leases

    lease = leases.acquire(db, name=leases.MAINTENANCE, holder="A")
    leases.release(db, lease)
    leases.acquire(db, name=leases.MAINTENANCE, holder="B")

    assert leases.heartbeat(db, lease) is False


def test_nha_som_thi_nguoi_khac_nhan_ngay(db):
    from platform_core import leases

    lease = leases.acquire(db, name=leases.MAINTENANCE, holder="A")
    leases.release(db, lease)
    assert leases.acquire(db, name=leases.MAINTENANCE, holder="B") is not None


# ── Outbox ───────────────────────────────────────────────────────────────────

def _delivery(db, *, count: int = 1) -> list:
    from platform_core.public_api import outbox
    from platform_core.public_api.tables import (WebhookDelivery,
                                                 WebhookSubscription)

    now = datetime.now(timezone.utc)
    sub = WebhookSubscription(
        id=uuid.uuid4().hex, user_id="u-1", url="https://example.com/hook",
        events=["job.succeeded"], enabled=True, secret_enc="enc:" + "s" * 40)
    db.add(sub)
    db.flush()
    ids = []
    for _ in range(count):
        row = WebhookDelivery(
            id=uuid.uuid4().hex, subscription_id=sub.id, user_id="u-1",
            event_id=uuid.uuid4().hex, event_type="job.succeeded", job_id="",
            payload={"job_id": "", "tool": "image.thumbnail",
                     "status": "succeeded", "mode": "live"},
            status=outbox.WEBHOOK_PENDING, attempts=0,
            next_attempt_at=now, created_at=now)
        db.add(row)
        ids.append(row.id)
    db.commit()
    return ids


def test_nhan_viec_roi_thi_nguoi_sau_khong_thay_no_den_han(db):
    """Đây là lỗi gốc: trước đây `claim_due` chỉ SELECT, nên ai đọc cũng thấy.

    Hai worker cùng thấy một delivery là "đến hạn" và cả hai đều gửi — khách
    nhận hai callback, còn bảng vẫn hiện `attempts=1` vì cả hai ghi đè cùng một
    giá trị. Sau khi nhận thật, lượt đọc thứ hai phải **không thấy gì**.
    """
    from platform_core.public_api import outbox
    from platform_core.public_api.tables import WEBHOOK_SENDING

    _delivery(db, count=3)

    dau = outbox.claim_due(db, holder="worker-A")
    assert len(dau) == 3
    assert all(row.status == WEBHOOK_SENDING for row in dau)

    sau = outbox.claim_due(db, holder="worker-B")
    assert sau == [], f"worker thứ hai vẫn nhận được {len(sau)} delivery"


def test_nhan_viec_ben_vung_truoc_khi_goi_http(db):
    """Trạng thái phải đã ghi xuống CSDL **trước** lời gọi mạng đầu tiên.

    Nếu commit sau khi gửi thì một tiến trình chết giữa chừng để lại hàng ở
    trạng thái cũ, và lượt quét sau gửi lại — đúng cái double-send cần chặn.
    """
    from platform_core.public_api import outbox
    from platform_core.public_api.tables import WEBHOOK_SENDING, WebhookDelivery

    ids = _delivery(db, count=1)
    outbox.claim_due(db, holder="worker-A")

    db.expire_all()
    row = db.get(WebhookDelivery, ids[0])
    assert row.status == WEBHOOK_SENDING
    assert row.attempts == 1, "lượt thử phải được tính lúc nhận, không phải lúc ghi kết quả"


def test_worker_chet_giua_luc_gui_thi_delivery_duoc_nhan_lai(db):
    """Nhận việc phải có hạn, nếu không một tiến trình chết giam nó vĩnh viễn."""
    from platform_core.public_api import outbox
    from platform_core.public_api.tables import WebhookDelivery

    ids = _delivery(db, count=1)
    outbox.claim_due(db, holder="worker-chet")

    row = db.get(WebhookDelivery, ids[0])
    row.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    lai = outbox.claim_due(db, holder="worker-khac")
    assert [r.id for r in lai] == ids


def test_luot_thu_khong_bi_dem_hai_lan(db):
    """`attempts` tăng ở lúc nhận, nên chỗ ghi kết quả không được tăng nữa.

    Đếm hai chỗ nghĩa là delivery chết sau ba lần thử thay vì sáu — nửa số lần
    thử biến mất mà không ai thấy.
    """
    from platform_core.public_api import outbox, webhooks
    from platform_core.public_api.tables import WebhookDelivery

    ids = _delivery(db, count=1)
    goi = {"n": 0}

    def _hong(subscription, row):
        goi["n"] += 1
        raise RuntimeError("receiver down")

    for _ in range(webhooks.MAX_ATTEMPTS):
        row = db.get(WebhookDelivery, ids[0])
        row.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        outbox.deliver_due(db, sender=_hong)
        db.commit()

    row = db.get(WebhookDelivery, ids[0])
    assert row.attempts == webhooks.MAX_ATTEMPTS, row.attempts
    assert goi["n"] == webhooks.MAX_ATTEMPTS, (
        f"gửi {goi['n']} lần cho {webhooks.MAX_ATTEMPTS} lượt thử")
    assert row.status == outbox.WEBHOOK_DEAD


def test_gui_thanh_cong_van_ket_thuc_dung_trang_thai(db):
    from platform_core.public_api import outbox
    from platform_core.public_api.tables import WEBHOOK_DELIVERED, WebhookDelivery

    ids = _delivery(db, count=2)
    bao_cao = outbox.deliver_due(db, sender=lambda sub, row: 200)
    db.commit()

    assert bao_cao["delivered"] == 2, bao_cao
    for delivery_id in ids:
        row = db.get(WebhookDelivery, delivery_id)
        assert row.status == WEBHOOK_DELIVERED
        assert row.attempts == 1


# ── Cảnh báo ─────────────────────────────────────────────────────────────────

def test_cung_mot_canh_bao_chi_ghi_duoc_mot_lan(db):
    """Cooldown giờ do CSDL cưỡng chế, không phải do đọc-rồi-ghi trong Python."""
    from platform_core.public_api import notifications

    dau = notifications.raise_alert(
        db, user_id="u-1", kind="budget.threshold", subject="account:80",
        title="80%", body="…")
    db.commit()
    sau = notifications.raise_alert(
        db, user_id="u-1", kind="budget.threshold", subject="account:80",
        title="80%", body="…")
    db.commit()

    assert dau is not None
    assert sau is None, "cảnh báo trùng vẫn ghi được"


def test_khoa_chong_trung_song_sot_khi_lan_doc_truoc_khong_thay_gi(db):
    """Mô phỏng đúng cuộc đua: hai tiến trình đều đọc thấy "chưa có gì".

    Lần đọc chỉ là lối tắt cho trường hợp thường; ràng buộc UNIQUE mới là thứ
    thi hành. Test này bỏ qua lối tắt để chỉ còn ràng buộc chịu trách nhiệm.
    """
    from platform_core.public_api import notifications
    from platform_core.public_api.tables import ApiNotification

    khoa = notifications.cooldown_key("budget.threshold", "account:50")
    for _ in range(2):
        row = ApiNotification(
            id=str(uuid.uuid4()), user_id="u-1", kind="budget.threshold",
            subject="account:50", title="50%", body="…",
            created_at=datetime.now(timezone.utc), event_key=khoa)
        db.add(row)
        try:
            db.commit()
        except Exception:
            db.rollback()

    from sqlalchemy import func, select

    dem = db.execute(select(func.count(ApiNotification.id)).where(
        ApiNotification.event_key == khoa)).scalar_one()
    assert dem == 1, f"{dem} bản ghi cho một khoá cảnh báo"


def test_canh_bao_khac_chu_de_van_ghi_duoc(db):
    """Chống trùng không được biến thành chống-mọi-thứ."""
    from platform_core.public_api import notifications

    a = notifications.raise_alert(db, user_id="u-1", kind="budget.threshold",
                                  subject="account:50", title="50%", body="…")
    db.commit()
    b = notifications.raise_alert(db, user_id="u-1", kind="budget.threshold",
                                  subject="account:80", title="80%", body="…")
    db.commit()
    assert a is not None and b is not None


def test_mot_canh_bao_trung_khong_lam_mat_nhung_cai_hop_le_cung_luot(db):
    """Một lượt quét dựng nhiều cảnh báo; một cái trùng không được kéo đổ cả lượt.

    Chống trùng bằng `rollback()` sẽ huỷ luôn những cảnh báo hợp lệ đã ghi trước
    nó trong cùng transaction — khách mất cảnh báo thật vì một cảnh báo lặp.
    """
    from sqlalchemy import func, select

    from platform_core.public_api import notifications
    from platform_core.public_api.tables import ApiNotification

    notifications.raise_alert(db, user_id="u-1", kind="budget.threshold",
                              subject="account:50", title="50%", body="…")
    db.commit()

    # Một lượt: cái mới, cái trùng, rồi cái mới nữa.
    notifications.raise_alert(db, user_id="u-1", kind="budget.threshold",
                              subject="account:80", title="80%", body="…")
    notifications.raise_alert(db, user_id="u-1", kind="budget.threshold",
                              subject="account:50", title="50%", body="…")
    notifications.raise_alert(db, user_id="u-1", kind="budget.threshold",
                              subject="account:95", title="95%", body="…")
    db.commit()

    chu_de = {row.subject for row in db.execute(
        select(ApiNotification)).scalars().all()}
    assert chu_de == {"account:50", "account:80", "account:95"}, chu_de
    assert db.execute(select(func.count(ApiNotification.id))).scalar_one() == 3
