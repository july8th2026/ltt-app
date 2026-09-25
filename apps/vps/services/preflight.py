"""Independent, fail-closed health preflight for one infrastructure profile."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os

from apps.vps import bang_thong, profiles
from apps.vps.cost import PLANS
from apps.vps.services import backend_factory, nguon_luc, provisioning
from apps.vps.services.sellable_capacity import (
    available_gateway_slots,
    effective_ipv4_slots,
    promised_without_ip,
)
from apps.vps.services.machine_b_runtime import (
    MachineBRuntimeEvidence,
    read_machine_b_runtime,
)
from apps.vps.tables import VpsInfrastructureProfile, VpsProfileHealth


@dataclass(frozen=True)
class PreflightResult:
    ready: bool
    components: dict[str, str]
    summaries: dict[str, str]
    sellable: dict[str, int] = field(default_factory=dict)


def _status(value: object) -> str:
    candidate = str(value or "UNKNOWN").upper()
    return candidate if candidate in profiles.HEALTH_STATES else "UNKNOWN"


def _probe(callable_):
    try:
        return callable_()
    except Exception as exc:  # probe boundary: report class, never provider text
        return type("FailedHealth", (), {
            "status": "CRITICAL",
            "summary": f"probe failed ({type(exc).__name__})",
            "details": {},
        })()


def run_profile_preflight(
    db,
    profile: VpsInfrastructureProfile,
    *,
    compute,
    public_ip,
    gateway,
    runtime: MachineBRuntimeEvidence,
    demote_on_failure: bool = True,
) -> PreflightResult:
    """Measure all activation prerequisites and persist independent evidence.

    Operator preflight demotes a failing profile. The periodic refresh passes
    `demote_on_failure=False`: its red health rows already close selection, and
    demoting on one transient probe would need a human to re-activate sales.
    """
    compute_health = _probe(compute.health)
    ip_health = _probe(public_ip.health)
    gateway_health = _probe(gateway.health)
    capacity_probe = _probe(compute.capacity)

    compute_status = _status(compute_health.status)
    ip_status = _status(ip_health.status)
    gateway_status = _status(gateway_health.status)
    runtime_status = _status(runtime.status)
    network_status = (
        _status(runtime.domains.get("network"))
        if runtime_status == "HEALTHY" else runtime_status)
    storage_status = (
        _status(runtime.domains.get("storage"))
        if runtime_status == "HEALTHY" else runtime_status)

    capacity_status, capacity_summary = "CRITICAL", "sellable capacity unavailable"
    sellable = {}
    try:
        ip_details = dict(getattr(ip_health, "details", None) or {})
        gateway_details = dict(getattr(gateway_health, "details", None) or {})
        gateway_limit = gateway_details.get("available_slots")
        if gateway_limit is None:
            gateway_limit = available_gateway_slots(db, profile.id)
        measured = provisioning.suc_chua_hien_tai(
            db, capacity_probe["node"], capacity_probe["storage"], capacity_probe["vms"])
        # 🔴 Bản cũ gọi `effective_ipv4_slots(ip_details)` **không** trừ
        #    `promised_without_ip`, trong khi trang bán và luồng tạo máy thì
        #    có. Hai phép tính cho cùng một câu hỏi, và chúng lệch nhau thật:
        #    `capacity` báo xanh trong khi trang hiện 0 chỗ. Nay cả ba đi qua
        #    `nguon_luc`, nên "lệch" không còn là một trạng thái biểu diễn được.
        do = nguon_luc.DoDuoc(
            suc_chua=measured,
            free_ipv4=effective_ipv4_slots(
                ip_details,
                promised_without_ip=promised_without_ip(db, profile.id)),
            gateway_slots=gateway_limit,
            da_hua_bang_thong_gb=nguon_luc.bang_thong_da_hua_gb(db, profile.id),
            ngan_sach_bang_thong_gb=bang_thong.ngan_sach_hua_gb(),
        )
        ket = {plan.id: nguon_luc.danh_gia(do, plan.id) for plan in PLANS}
        sellable = {plan_id: kq.so_cho for plan_id, kq in ket.items()}
        if any(kq.ban_duoc for kq in ket.values()):
            capacity_status = "HEALTHY"
            capacity_summary = "compute, IPv4, gateway and bandwidth have slots"
        else:
            # Nói ĐÚNG ràng buộc đang chặn, không nói "no sellable slots" cho
            # cả bốn nguyên nhân: người vận hành đọc dòng này để biết đi sửa gì.
            capacity_summary = "khong con cho: " + "; ".join(
                kq.cau_cho_van_hanh for kq in ket.values())[:280]
    except (TypeError, ValueError, KeyError, AttributeError):
        # Malformed provider payloads must not turn the whole health page into
        # an exception, or unknown capacity into a green activation gate.
        pass
    if storage_status != "HEALTHY":
        capacity_status = storage_status
        capacity_summary = "Machine B storage evidence is not healthy"

    components = {
        "compute": compute_status,
        "ip": ip_status,
        "gateway": gateway_status,
        "network": network_status,
        "capacity": capacity_status,
        "runtime": runtime_status,
    }
    summaries = {
        "compute": str(getattr(compute_health, "summary", ""))[:300],
        "ip": str(getattr(ip_health, "summary", ""))[:300],
        "gateway": str(getattr(gateway_health, "summary", ""))[:300],
        "network": "Machine B network evidence",
        "capacity": capacity_summary,
        "runtime": str(runtime.reason or "coherent fresh Machine B generation")[:300],
    }
    observed = datetime.now(timezone.utc)
    for component in profiles.REQUIRED_HEALTH_COMPONENTS:
        db.add(VpsProfileHealth(
            infrastructure_profile_id=profile.id,
            component=component,
            status=components[component],
            summary=summaries[component],
            provenance={**dict(runtime.provenance or {}), **(
                {"sellable_slots": sellable} if component == "capacity" else {})},
            generated_at=runtime.generated_at,
            observed_at=observed,
        ))
    ready = all(value == "HEALTHY" for value in components.values())
    # ⚠️ Hạ profile CHỈ khi tầng `CHAN_BAN` đỏ. Hạ vì `network` đỏ thì việc tách
    #    hai tầng thành vô nghĩa: `select_profile` bỏ qua `network` được, nhưng
    #    một profile đã bị đặt `accept_new = False` thì không con đường nào chọn
    #    nó nữa — và phải có NGƯỜI bật lại. Đúng vòng luẩn quẩn mà một bộ đếm
    #    gói rơi từng tạo ra ngày 23/09.
    giao_duoc = all(components[ten] == "HEALTHY" for ten in profiles.CHAN_BAN)
    if not giao_duoc and demote_on_failure:
        profile.accept_new = False
        profile.is_default = False
    profile.last_health_at = observed
    db.flush()
    return PreflightResult(ready, components, summaries, sellable)


def run_configured_profile_preflight(
    db, profile: VpsInfrastructureProfile, *, runtime_dir: str | None = None,
    demote_on_failure: bool = True,
) -> PreflightResult:
    """Construct configured adapters and consume Machine B artifacts read-only."""
    runtime_ref = str(profile.compute_config.get("runtime_ref") or "")
    if runtime_ref and not runtime_ref.startswith("LTT_"):
        directory = ""
    else:
        directory = (runtime_dir or (os.environ.get(runtime_ref, "") if runtime_ref else "")
                     or os.environ.get("LTT_VPS_MACHINE_B_RUNTIME", ""))
    runtime = read_machine_b_runtime(directory) if directory else MachineBRuntimeEvidence(
        "UNKNOWN", "Machine B runtime directory is not configured")
    if profile.public_ip_backend_type == "ovh_static_pool":
        provider = backend_factory.ovh_inventory_client(profile)
        if not provider.health():
            raise RuntimeError("OVH service ownership check failed")
    return run_profile_preflight(
        db, profile,
        compute=backend_factory.compute_backend(profile),
        public_ip=backend_factory.public_ip_backend(db, profile),
        gateway=backend_factory.gateway_backend(profile),
        runtime=runtime,
        demote_on_failure=demote_on_failure,
    )


def nguyen_nhan_ngan(exc: BaseException) -> str:
    """Mot cau ngan, KHONG bi mat, du de biet phai lam gi.

    🔴 Do 25/09/2026: khoa OVH bi thu hoi, va bang suc khoe ho so in
       `periodic preflight unavailable (OvhError)` cho CA BON thanh phan chan ban.
       Dong do khong dan tới bat cu hanh dong nao: no khong noi la khoa, khong noi
       ma so, va khai ca `compute` (Proxmox, hoan toan khoe) la CRITICAL. Chu du an
       chi thay "He thong dang bao tri" o cua hang; tim ra goc mat 6 phep do.

    ⛔ Khong ghep `message` cua nha cung cap vao day: no co khi vong lai chinh yeu
       cau. Chi lay ma HTTP + ma loi dinh danh (`INVALID_CREDENTIAL`, ...).
    """
    ten = type(exc).__name__
    ma = getattr(exc, "status", None)
    ma_loi = str(getattr(exc, "ma_loi", "") or "")
    phan = [ten]
    if isinstance(ma, int):
        phan.append(str(ma))
    if ma_loi:
        phan.append(ma_loi)
    return " ".join(phan)[:100]


def refresh_active_profiles(db, *, run=None) -> dict[str, bool]:
    """Periodic health refresh for every ACTIVE profile; never demotes.

    Each profile is isolated: a constructor/transport failure records CRITICAL
    rows for that profile only (selection closes) and the loop continues.
    """
    from sqlalchemy import select

    run = run or run_configured_profile_preflight
    ids = db.execute(select(VpsInfrastructureProfile.id).where(
        VpsInfrastructureProfile.status == "ACTIVE")).scalars().all()
    ket_qua: dict[str, bool] = {}
    for profile_id in ids:
        row = db.get(VpsInfrastructureProfile, profile_id)
        try:
            ket_qua[profile_id] = run(db, row, demote_on_failure=False).ready
            db.commit()
        except Exception as exc:  # boundary: report class, never provider text
            db.rollback()
            row = db.get(VpsInfrastructureProfile, profile_id)
            now = datetime.now(timezone.utc)
            for component in profiles.REQUIRED_HEALTH_COMPONENTS:
                db.add(VpsProfileHealth(
                    infrastructure_profile_id=row.id, component=component,
                    # ⭐ `UNKNOWN`, khong phai `CRITICAL`. Hai dieu khac nhau:
                    #    `CRITICAL` = da do va no hong; `UNKNOWN` = chua do duoc.
                    #    Khong mot thanh phan nao trong vong nay duoc do — preflight
                    #    no TRUOC do (khoa OVH chet 25/09 lam `provider.health()`
                    #    nem), nen khai `compute` (Proxmox hoan toan khoe) la
                    #    CRITICAL la noi mot dieu ta chua he biet.
                    #
                    # ⛔ Va no KHONG noi cua ban them mot milimet:
                    #    `profiles._danh_gia` doi `row.status != "HEALTHY"` la chan
                    #    (profiles.py:150) — no khong doi `CRITICAL`. Nen day la
                    #    mot thay doi ve SU THAT, khong phai ve CHINH SACH.
                    status="UNKNOWN", observed_at=now, generated_at=now,
                    summary=("khong do duoc thanh phan nay; preflight dung som: "
                             + nguyen_nhan_ngan(exc))))
            row.last_health_at = now
            db.commit()
            ket_qua[profile_id] = False
    return ket_qua
