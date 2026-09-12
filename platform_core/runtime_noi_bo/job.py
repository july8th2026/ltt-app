"""
job.py — báo giá và nộp job **có giữ chỗ** cho một client nội bộ.

⛔ KHÔNG PHẢI ĐƯỜNG NỘP THỨ HAI. Cả hai hàm ở đây chỉ gói lại thứ đã có:

    bao_gia()  = agent.tools.validate_tool_params + ToolSpec.lane_for + registry.credit_for
    nop_job()  = job_submit.submit_with_credit (validate/giá/giữ chỗ/queue một giao dịch)

Phần "quote ký HMAC có hạn" của `/api/v1` cố ý **không** ở đây: nó tồn tại vì
khách API ở ngoài phiên đăng nhập và có thể gửi một báo giá cũ. Client web
gọi `bao_gia` rồi `nop_job` trong cùng một phiên; số đã báo đi thẳng vào
`quoted_credit`, và `credit.quyet_toan` kẹp số thu **không bao giờ vượt** phần
đã giữ (Q84).

⭐ `owner_id` được **ép** bằng `user_id` — handler của app ảnh/tiếng kiểm sở
   hữu theo nó, và `invocation.submit` của `/api/v1` cũng ép đúng như vậy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from platform_core.job_submit import dedupe_key_for, submit_with_credit
from platform_core.registry import credit_for
from platform_core.runtime_noi_bo.tim import KhongCoNangLuc, tim_tool  # noqa: F401

log = logging.getLogger("platform_core.runtime_noi_bo.job")


class ThamSoSai(ValueError):
    """Tham số không theo `ToolSpec` — lỗi của bên gọi, chưa chạm sổ tiền."""


@dataclass(frozen=True)
class BaoGia:
    """Giá đã tính cho MỘT bộ tham số đã chuẩn hoá. Đưa nguyên cái này vào `nop_job`."""

    tool_name: str
    lane: str                 # job_type thật (theo `ToolSpec.lane_for`)
    credit: int               # số sẽ giữ chỗ
    phien_ban_gia: str        # từ `bang_gia()` của app, "" nếu app không khai
    tham_so_sach: dict        # tham số đã validate + điền mặc định


def bao_gia(tool_name: str, params: dict, *, db=None, user_id: str = "") -> BaoGia:
    """Validate theo ToolSpec (kể cả tuỳ chọn động theo người dùng) rồi tính giá."""
    from platform_core.agent.tools import ToolParamsError, validate_tool_params

    manifest, tool = tim_tool(tool_name)
    try:
        sach = validate_tool_params(tool_name, dict(params or {}),
                                    db=db, user_id=user_id)
    except ToolParamsError as e:
        raise ThamSoSai(str(e)) from None
    lane = tool.lane_for(sach)
    so = int(credit_for(lane, sach))
    return BaoGia(tool_name=tool_name, lane=lane, credit=so,
                  phien_ban_gia=_phien_ban_gia(manifest), tham_so_sach=sach)


def _phien_ban_gia(manifest) -> str:
    """`phien_ban_gia` từ `bang_gia()` của app; app hỏng bảng giá thì "" **và ồn ào**.

    Cùng luật với `bao_tri`/`bang_gia_cong_khai`: một app hỏng không được làm
    hỏng báo giá của app khác — nhưng phải ghi log, vì nhãn phiên bản giá rỗng
    trên một báo giá là thứ chỉ lộ ra khi khách đối soát.
    """
    if manifest.bang_gia is None:
        return ""
    try:
        return str((manifest.bang_gia() or {}).get("phien_ban_gia") or "")
    except Exception:                                           # noqa: BLE001
        log.exception("bang_gia cua %s nem khi bao gia", manifest.slug)
        return ""


def nop_job(db, *, user_id: str, bao_gia: BaoGia, correlation_id: str = "",
            idempotency_key: str = ""):
    """Nộp job và giữ chỗ đúng số đã báo. KHÔNG commit — caller commit.

    Ném `credit.ThieuCreditError` (rollback cùng), `registry.RegistryError`.
    `idempotency_key` rỗng ⇒ khoá dedupe suy từ `(lane, tham số)` như mọi route.
    """
    from platform_core.public_api.limits import resource_class
    from platform_core.registry import admission_luc_nop

    manifest, tool = tim_tool(bao_gia.tool_name)
    params = dict(bao_gia.tham_so_sach)
    params["owner_id"] = user_id
    dedupe = idempotency_key or dedupe_key_for(bao_gia.lane, params)
    # 🔴 THEO MODEL, không phải bộ ba tĩnh (multijob 2.3, R20). Xem
    #    `registry.admission_luc_nop` để biết vì sao đọc `tool.admission_resource`
    #    ở đây làm hỏng `jobs.claim` + fairness + scheduler envelope.
    tai_nguyen, so_suat = admission_luc_nop(
        tool, bao_gia.tham_so_sach, mac_dinh=resource_class(manifest))
    return submit_with_credit(
        db, user_id=user_id, app_slug=manifest.slug, job_type=bao_gia.lane,
        params=params, dedupe_key=dedupe,
        max_attempts=manifest.so_lan_thu_for(bao_gia.lane),
        correlation_id=correlation_id,
        quoted_credit=int(bao_gia.credit),
        admission_resource=tai_nguyen,
        admission_slots=so_suat,
        origin="internal_runtime", priority_class="internal",
    )
