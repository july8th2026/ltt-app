"""State machine and selection authority for VPS infrastructure profiles."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.vps.tables import (VpsInfrastructureProfile, VpsInstance,
                             VpsProfileHealth)

PROFILE_STATES = ("ACTIVE", "DRAINING", "STANDBY", "DISABLED")
HEALTH_STATES = ("UNKNOWN", "STALE", "HEALTHY", "DEGRADED", "CRITICAL")
REQUIRED_HEALTH_COMPONENTS = (
    "compute", "ip", "gateway", "network", "capacity", "runtime")

#: Hai tầng, và `REQUIRED_HEALTH_COMPONENTS` là hợp của chúng (`test_2501`
#: chốt rằng chúng phủ kín và không chồng lấn — thêm một thành phần mà quên
#: xếp tầng là thêm một thành phần không ai gác).
#:
#: ## Vì sao tách
#:
#: 🔴 Đo 23/09/2026: `select_profile` đòi cả sáu xanh, nên **một** bộ đếm gói
#:    rơi của Máy B (`wireguard.gateway.tx_dropped`) đóng cả cửa hàng. 12/13
#:    phép kiểm mạng còn lại đều PASS. Trên `vps_profile_health` từ 16/09:
#:    HEALTHY 608 · CRITICAL 136 · DEGRADED 94 · STALE 173 — cửa hàng bật tắt
#:    theo cửa sổ 10 phút, và khách bán được hay không là chuyện may rủi.
#:
#: `CHAN_BAN` trả lời **"giao được máy không"**: bốn thứ này hỏng thì một máy
#: mới không thể ra đời hoặc không thể giao đúng. `CANH_BAO` trả lời **"chạy
#: mượt không"**: gói rơi trong đường hầm không ngăn `qm clone` chạy.
#:
#: ⚠️ `capacity` ở lại `CHAN_BAN` **có chủ ý**, và nó kéo theo `runtime` gián
#:    tiếp: `preflight` hạ `capacity` xuống theo `storage` của Máy B. Bằng
#:    chứng đĩa cũ nghĩa là không biết còn bao nhiêu đĩa — và bán chồng đĩa mù
#:    thì không phải là bán chậm, là bán một thứ không có.
CHAN_BAN = ("compute", "ip", "gateway", "capacity")
CANH_BAO = ("network", "runtime")

#: Thành phần cảnh báo do **vòng bảo trì** đo, không phải `preflight`.
#:
#: ⚠️ Phải NẰM NGOÀI `REQUIRED_HEALTH_COMPONENTS`: `preflight` duyệt tập đó và
#:    đòi một trạng thái cho **từng** thành phần (`components[component]`), nên
#:    thêm vào đấy một thứ nó không đo được là một `KeyError` giữa đường đo sức
#:    khoẻ. `test_2600` chốt rằng hai tập rời nhau.
#:
#: Vì sao cần một tầng riêng: lớp canh băng thông theo TỔNG
#: (`bao_tri._can_ham_theo_tong`) đọc bộ đếm cổng vào qua SSH. Đọc hỏng thì nó
#: bỏ lượt — cố ý, để một lần hỏng thoáng qua không kéo theo lớp riêng. Nhưng
#: bỏ lượt **trong im lặng** thì một tuần SSH chết trông y hệt một tuần bình
#: thường, và thứ đầu tiên phát hiện ra sẽ là hoá đơn OVH.
CANH_BAO_BAO_TRI = ("bang_thong_tong", "cong_quan_tri", "chuan_hoa_may")

# Stable IDs make migration/backfill and operator tooling agree without looking
# profiles up by a mutable display name.
VULTR_PROFILE_ID = "00000000-0000-4000-8000-000000000401"
OVH_PROFILE_ID = "00000000-0000-4000-8000-000000000402"

# Freshness windows are derived from the cadences that actually refresh each
# timestamp, never from a wish. A window tighter than its producer's cadence
# rejects every create between two refreshes (measured 16/09: the old 300 s
# window against a 30-minute collector blocked sales structurally).
#
#   observed_at  — written by the app's own preflight, refreshed by the VPS
#                  maintenance hook every HEALTH_REFRESH_SECONDS.
#   generated_at — Machine B collector generation: Scheduled Task every 30 min
#                  (LTT-VM-Promox-v4 06-HIEN-TRANG/CHANGE-JOURNAL.md 2026-09-10),
#                  mirrored to this host every RUNTIME_SYNC_SECONDS.
#
# Two missed cycles plus one transport/sync lag is still stale; one late run is
# not an outage. Operator activation keeps its own strict window.
HEALTH_REFRESH_SECONDS = 600
HEALTH_MAX_AGE_SECONDS = 2 * HEALTH_REFRESH_SECONDS + 300
RUNTIME_COLLECTOR_SECONDS = 1800
RUNTIME_SYNC_SECONDS = 600
RUNTIME_MAX_AGE_SECONDS = 2 * RUNTIME_COLLECTOR_SECONDS + RUNTIME_SYNC_SECONDS
ACTIVATION_MAX_AGE_SECONDS = 300

#: Tuổi tối đa của **bản sinh từ máy B** khi người vận hành bật bán lại.
#:
#: 🔴 Đo 25/09/2026: `activate_profile` truyền `ACTIVATION_MAX_AGE_SECONDS` (300 s)
#:    cho CẢ HAI cửa sổ — tuổi quan sát của ta VÀ tuổi bản sinh của máy B. Nhưng
#:    máy B sinh mỗi `RUNTIME_COLLECTOR_SECONDS` = 1800 s, nên bản mới nhất trung
#:    bình đã **900 s** tuổi. ⇒ Điều kiện **không thể thoả**, trừ khi bấm đúng
#:    trong 300 s sau một lần sinh.
#:
#:    Và `admin_profiles._configured_preflight` hạ hồ sơ khi **bất kỳ** ngoại lệ
#:    nào xảy ra — kể cả một khoá API hết hạn, thứ đã xảy ra thật sáng 25/09. Đường
#:    về duy nhất là `activate_profile`. ⇒ Một khoá hết hạn **đóng cửa hàng vĩnh
#:    viễn**, và người vận hành bấm "bật lại" chỉ nhận `stale health component:
#:    runtime` mãi mãi.
#:
#: ⭐ Hai cửa sổ cho hai thứ khác nhau. Cửa sổ chặt nói *"bằng chứng phải vừa được
#:    đo xong"* — điều đó nói về **phép đo của ta**, thứ chạy được ngay trước khi
#:    bấm. Nó ⛔ không có quyền đòi máy B chạy nhanh hơn thiết kế của nó.
#: ⚠️ `RUNTIME_COLLECTOR_SECONDS + RUNTIME_SYNC_SECONDS`, ⛔ KHONG phai
#:    `RUNTIME_MAX_AGE_SECONDS`. Ban dau toi dat bang `RUNTIME_MAX_AGE_SECONDS`
#:    (4200 s) va no lam do `test_1010::test_fresh_observation_of_old_generation
#:    _does_not_unlock_profile` — mot bat bien CO Y: mot quan sat tuoi ve mot ban
#:    sinh CU thi khong duoc mo khoa ho so.
#:
#: 🔴 Toi da sua mot cua bat kha thi thanh mot cua qua rong. 4200 s la nguong
#:    **binh thuong**, va no tha cho **HAI** chu ky bi nho (`2*1800 + 600`) — dung
#:    cho vận hanh lien tuc, sai cho mot quyet dinh bat ban.
#:
#: ⇒ Bat ban tha **KHONG** chu ky nao: `1800 + 600 = 2400 s` la tuoi te nhat cua
#:   ban sinh MOI NHAT (mot chu ky sinh cong thoi gian guong ve). Luon thoa duoc,
#:   va chat hon nguong binh thuong. Mot ban sinh cu hon the la may B **da nho it
#:   nhat mot luot**, va luc do khong phai luc bat ban.
ACTIVATION_GENERATED_MAX_AGE_SECONDS = (RUNTIME_COLLECTOR_SECONDS
                                        + RUNTIME_SYNC_SECONDS)


class ProfileNotReady(RuntimeError):
    """Profile cannot safely accept a new external mutation."""


def pinned_profile(db: Session, instance: VpsInstance) -> VpsInfrastructureProfile:
    """Resolve only the durable pin; never fall back to default/global credentials."""
    db.refresh(instance)
    if instance.profile_resolution_state != "PINNED" or not instance.infrastructure_profile_id:
        raise ProfileNotReady("NEEDS_REVIEW: instance has no verified profile pin")
    row = db.get(VpsInfrastructureProfile, instance.infrastructure_profile_id)
    if row is None:
        raise ProfileNotReady("NEEDS_REVIEW: pinned profile is missing")
    db.refresh(row)
    if row.status == "DISABLED":
        raise ProfileNotReady("DISABLED: pinned profile blocks normal operations")
    if instance.vmid is not None and int(instance.vmid) in range(100, 108):
        raise ProfileNotReady("PROTECTED: VM100–107 cannot be operated by VPS")
    return row


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def health_prerequisites(
    db: Session,
    profile_id: str,
    *,
    now: datetime | None = None,
    max_age_seconds: int = HEALTH_MAX_AGE_SECONDS,
    generated_max_age_seconds: int = RUNTIME_MAX_AGE_SECONDS,
    thanh_phan: tuple[str, ...] = CHAN_BAN,
) -> tuple[bool, str, datetime | None]:
    """Check latest independent component observations; missing/stale fails closed.

    `max_age_seconds` bounds our own observation; `generated_max_age_seconds`
    bounds the upstream Machine B generation it was derived from.

    `thanh_phan` chọn tầng phải xanh. Mặc định `CHAN_BAN` — giữ cửa hàng mở
    chỉ đòi "giao được máy không". Người vận hành bật bán lần đầu
    (`activate_profile`) truyền `REQUIRED_HEALTH_COMPONENTS` để đòi cả sáu.
    """
    current = _utc(now or datetime.now(timezone.utc))
    newest: datetime | None = None
    for component in thanh_phan:
        row = db.execute(
            select(VpsProfileHealth)
            .where(
                VpsProfileHealth.infrastructure_profile_id == profile_id,
                VpsProfileHealth.component == component,
            )
            .order_by(VpsProfileHealth.observed_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            return False, f"missing health component: {component}", newest
        observed = _utc(row.observed_at)
        if newest is None or observed > newest:
            newest = observed
        timestamps = [(observed, max_age_seconds)]
        if row.generated_at is not None:
            timestamps.append((_utc(row.generated_at), generated_max_age_seconds))
        for timestamp, limit in timestamps:
            age = (current - timestamp).total_seconds()
            if age < -60:
                return False, f"future health component: {component}", newest
            if age > limit:
                return False, f"stale health component: {component}", newest
        if row.status != "HEALTHY":
            return False, f"unhealthy component: {component}={row.status}", newest
    return True, "", newest


def activate_profile(
    db: Session,
    profile_id: str,
    *,
    make_default: bool = False,
    max_age_seconds: int = ACTIVATION_MAX_AGE_SECONDS,
    generated_max_age_seconds: int = ACTIVATION_GENERATED_MAX_AGE_SECONDS,
) -> VpsInfrastructureProfile:
    """Activate only after fresh health; serialize default changes in the DB."""
    profile = db.execute(
        select(VpsInfrastructureProfile)
        .where(VpsInfrastructureProfile.id == profile_id)
        .with_for_update()
    ).scalar_one_or_none()
    if profile is None:
        raise ProfileNotReady("profile not found")

    # Bật bán là một quyết định CÓ NGƯỜI: nó đòi **cả sáu** thành phần xanh và
    # một cửa sổ tươi chặt hơn. Giữ cửa hàng mở (`select_profile`) mới là chỗ
    # chỉ đòi tầng `CHAN_BAN`.
    # ⛔ HAI cửa sổ, ⛔ không phải một số dùng cho cả hai. Xem
    #    `ACTIVATION_GENERATED_MAX_AGE_SECONDS`: bản cũ đòi bản sinh của máy B
    #    tươi hơn 300 s trong khi máy B sinh mỗi 1800 s ⇒ đường bật lại là bất
    #    khả thi, và một khoá API hết hạn đóng cửa hàng vĩnh viễn.
    ready, reason, observed = health_prerequisites(
        db, profile.id, max_age_seconds=max_age_seconds,
        generated_max_age_seconds=generated_max_age_seconds,
        thanh_phan=REQUIRED_HEALTH_COMPONENTS)
    if not ready:
        raise ProfileNotReady(reason)

    if make_default:
        defaults = db.execute(
            select(VpsInfrastructureProfile)
            .where(VpsInfrastructureProfile.is_default.is_(True))
            .with_for_update()
        ).scalars().all()
        for old in defaults:
            old.is_default = False
        db.flush()

    profile.status = "ACTIVE"
    profile.accept_new = True
    # Re-activating the current default must not silently drop it; only an
    # explicit default change (above) clears the previous holder.
    profile.is_default = bool(make_default) or bool(profile.is_default)
    profile.last_health_at = observed
    db.flush()
    return profile


def canh_bao(db: Session, profile_id: str, *,
             thanh_phan: tuple[str, ...] | None = None) -> list[tuple[str, str]]:
    """Thành phần tầng `CANH_BAO` đang không xanh: `[(tên, trạng_thái)]`.

    ⚠️ Hàm này là **nửa còn lại** của việc gỡ `network` khỏi cổng bán. Gỡ một
       tín hiệu ra khỏi chỗ chặn mà không đưa nó vào chỗ nhìn là bỏ nó thật —
       đúng số phận `bang_thong.tong_da_hua_gb` đã gặp: một hàm viết ra để
       canh bán chồng, không dòng nào gọi, suốt từ khi có nó.

    Thiếu bản ghi cũng là một cảnh báo (`UNKNOWN`): ở tầng này "không đo được"
    không đóng cửa hàng, nhưng nó vẫn phải hiện ra cho người vận hành.
    """
    # Mặc định gồm CẢ thành phần do vòng bảo trì ghi: một tín hiệu chỉ có giá
    # trị khi có chỗ nhìn nó, và trang admin đọc thẳng hàm này.
    #
    # Người gọi hướng KHÁCH truyền `thanh_phan=CANH_BAO`: `bang_thong_tong` là
    # tín hiệu VẬN HÀNH ("ta có đang canh không"), không phải chất lượng dịch
    # vụ khách đang nhận. Nói với khách rằng một bộ đếm nội bộ đọc không được
    # là đổ lo lắng sang người không làm gì được với nó.
    ra: list[tuple[str, str]] = []
    for component in (CANH_BAO + CANH_BAO_BAO_TRI if thanh_phan is None
                      else thanh_phan):
        row = db.execute(
            select(VpsProfileHealth)
            .where(
                VpsProfileHealth.infrastructure_profile_id == profile_id,
                VpsProfileHealth.component == component,
            )
            .order_by(VpsProfileHealth.observed_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            # Thiếu bản ghi cũng là một cảnh báo: "chưa bao giờ đo" là đúng thứ
            # mục này sinh ra để không giấu nữa.
            ra.append((component, "UNKNOWN"))
        elif row.status != "HEALTHY":
            ra.append((component, str(row.status)))
    return ra


def select_profile(db: Session, *, region: str) -> VpsInfrastructureProfile:
    """Select by customer-visible region only; provider/profile are not inputs."""
    rows = db.execute(
        select(VpsInfrastructureProfile)
        .where(
            VpsInfrastructureProfile.region == region,
            VpsInfrastructureProfile.status == "ACTIVE",
            VpsInfrastructureProfile.accept_new.is_(True),
        )
        .order_by(VpsInfrastructureProfile.is_default.desc())
        .with_for_update()
    ).scalars().all()
    rows = [row for row in rows if health_prerequisites(db, row.id)[0]]
    if not rows:
        raise ProfileNotReady(f"no healthy ACTIVE profile for region {region!r}")
    defaults = [row for row in rows if row.is_default]
    if len(defaults) == 1:
        return defaults[0]
    if len(rows) == 1:
        return rows[0]
    raise ProfileNotReady(f"ambiguous ACTIVE profiles for region {region!r}")


def pin_instance(
    instance: VpsInstance,
    profile: VpsInfrastructureProfile,
) -> None:
    """Pin once. An already-pinned instance can never follow a changed default."""
    if profile.status != "ACTIVE" or not profile.accept_new:
        raise ProfileNotReady("profile does not accept new VPS")
    existing = instance.infrastructure_profile_id
    if existing and existing != profile.id:
        raise ProfileNotReady("instance profile is immutable")
    instance.infrastructure_profile_id = profile.id
    instance.profile_resolution_state = "PINNED"
