"""Sổ nguồn lực VPS — MỘT phép tính trả lời "bán được gói này không, vì sao không".

## Vì sao tệp này tồn tại

🔴 Đo trên production 23/09/2026: trang `/vps` in *"Hết chỗ cho cấu hình này"*
   cho **cả ba gói**, trong khi compute còn 14/9/6 chỗ và cổng vào còn 150.
   Không tài nguyên nào hết. Câu đó là một lỗi sức khoẻ bị dịch sai thành một
   lời từ chối bán hàng, và khách là người đọc nó.

   Đường đi của lỗi: `profiles.select_profile` ném `ProfileNotReady` (một bộ
   đếm gói rơi của Máy B làm `network` đỏ) → `routes._gioi_han_ban` bắt rồi
   trả `None` → `trang_chinh` đọc `None` thành `con_cho = False` cho mọi gói →
   thẻ gói in "Hết chỗ".

⭐ Nguyên nhân sâu hơn là **ba nơi cùng tự tính một câu trả lời**: trang bán,
   luồng tạo máy, và `preflight`. Và chúng **đã lệch nhau thật** — `preflight`
   gọi `effective_ipv4_slots(ip_details)` còn `routes` gọi cùng hàm đó **có**
   trừ `promised_without_ip`, nên thành phần `capacity` báo xanh trong khi
   trang hiện 0 chỗ.

Nên ở đây làm một chỗ duy nhất, và ba nơi kia gọi nó.

## Hai lớp, cố ý

`danh_gia()` là hàm **thuần**: nhận số đo, trả phán quyết. Không CSDL, không
mạng, nên luật bán hàng kiểm được bằng test rẻ và không có cửa giả.

`con_ban_duoc()` đi đọc thế giới thật rồi gọi `danh_gia()`. Mọi thứ đọc không
được đều thành `None` — và `None` là **`suc_khoe`**, không phải "hết chỗ".
Không biết còn bao nhiêu thì không bán; nhưng phải nói đúng rằng ta không biết.

## Hai câu, cố ý

⛔ `cau_cho_khach` không bao giờ chứa tên hệ thống nội bộ. Bản cũ của
   `_suc_chua` in nguyên văn `chua cau hinh Proxmox: production ma khong co
   LTT_VPS_PROXMOX_CA` **ra trang bán hàng công khai** (đo 09/09/2026): một
   câu tiếng Việt-không-dấu trộn thuật ngữ, tên biến môi trường, và cái tên
   `Proxmox` mà chính `services/proxmox.py` nói khách không bao giờ được thấy.

`cau_cho_van_hanh` giữ số liệu, viết không dấu, đi vào log và trang admin.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from apps.vps import bang_thong
from apps.vps.cost import lay_plan
from apps.vps.services import capacity
from apps.vps.services.sellable_capacity import sellable_slots
from platform_core.i18n import N_
from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

RANG_BUOC_COMPUTE = "compute"
RANG_BUOC_IPV4 = "ipv4"
RANG_BUOC_GATEWAY = "gateway"
RANG_BUOC_BANG_THONG = "bang_thong"
RANG_BUOC_SUC_KHOE = "suc_khoe"

#: Một câu mỗi ràng buộc. Thêm ràng buộc mà quên câu ⇒ `test_2500` đỏ.
#:
#: `compute` là ràng buộc DUY NHẤT khách tự xử lý được (chọn gói nhỏ hơn), nên
#: nó là ràng buộc duy nhất được phép nói "hết chỗ" — và trang gắn thêm danh
#: sách gói còn bán được ngay cạnh câu này.
CAU_CHO_KHACH = {
    RANG_BUOC_COMPUTE: N_("Gói này tạm hết chỗ."),
    RANG_BUOC_IPV4: N_("Tạm hết địa chỉ IP. Chúng tôi đang bổ sung."),
    RANG_BUOC_GATEWAY: N_("Tạm ngưng nhận máy mới."),
    RANG_BUOC_BANG_THONG: N_("Tạm ngưng nhận máy mới trong tháng này."),
    RANG_BUOC_SUC_KHOE: N_("Hệ thống đang bảo trì, tạm chưa nhận máy mới."),
}

#: Thứ tự phá hoà khi hai ràng buộc cùng chặt nhất. Đặt `compute` trước vì nó
#: là ràng buộc duy nhất khách còn làm được gì đó; `suc_khoe` sau cùng vì nó
#: chỉ xuất hiện khi không có số nào để so.
_UU_TIEN = (RANG_BUOC_COMPUTE, RANG_BUOC_BANG_THONG, RANG_BUOC_IPV4,
            RANG_BUOC_GATEWAY)


@dataclass(frozen=True)
class DoDuoc:
    """Mọi số đo cần để trả lời câu hỏi bán hàng. `None` = **không đọc được**.

    Phân biệt `None` với `0` là cả điểm của lớp này: `0` là "đã đo, và hết";
    `None` là "chưa đo được". Gộp hai cái thành một con số là cách trang bán
    hàng nói dối mà không ai cố ý.
    """

    suc_chua: capacity.SucChua | None
    free_ipv4: int | None
    gateway_slots: int | None
    da_hua_bang_thong_gb: int = 0
    ngan_sach_bang_thong_gb: int = 0


@dataclass(frozen=True)
class KetQua:
    ban_duoc: bool
    so_cho: int
    rang_buoc: str
    cau_cho_khach: str
    cau_cho_van_hanh: str


def _cho_bang_thong(do: DoDuoc, plan) -> int:
    """Còn hứa thêm được mấy máy gói này trước khi cạn ngân sách cổng vào.

    Gói không khai hạn mức (`bang_thong_gb = 0`) thì băng thông không chặn nó —
    cùng khuôn với `bang_thong.han_muc_byte`, nơi 0 nghĩa là không hãm.
    """
    if int(getattr(plan, "bang_thong_gb", 0) or 0) <= 0:
        return _KHONG_CHAN
    con = int(do.ngan_sach_bang_thong_gb) - int(do.da_hua_bang_thong_gb)
    return max(0, con) // int(plan.bang_thong_gb)


#: Lớn hơn mọi số chỗ thật, nhưng vẫn là một `int` để `min()` không phải biết
#: về trường hợp riêng. Không dùng `sys.maxsize`: một số vô nghĩa lọt ra giao
#: diện thì ít nhất nó phải trông như một con số người đọc được.
_KHONG_CHAN = 1_000_000


def danh_gia(do: DoDuoc, plan_id: str, *, dia_them_gb: int = 0) -> KetQua:
    """Phán quyết bán hàng từ số đo. **Thuần** — không CSDL, không mạng."""
    plan = lay_plan(plan_id)
    if plan is None:
        # Một gói không có trong bảng giá không phải chuyện của khách: hoặc
        # link cũ, hoặc form bị sửa. Không bán, và không đổ lỗi cho hạ tầng.
        return KetQua(False, 0, RANG_BUOC_SUC_KHOE,
                      _t(CAU_CHO_KHACH[RANG_BUOC_SUC_KHOE]),
                      f"goi {plan_id!r} khong co trong bang gia")

    if (do.suc_chua is None or do.free_ipv4 is None
            or do.gateway_slots is None):
        thieu = [ten for ten, gt in (("compute", do.suc_chua),
                                     ("ipv4", do.free_ipv4),
                                     ("gateway", do.gateway_slots))
                 if gt is None]
        return KetQua(False, 0, RANG_BUOC_SUC_KHOE,
                      _t(CAU_CHO_KHACH[RANG_BUOC_SUC_KHOE]),
                      "khong doc duoc: " + ", ".join(thieu))

    ban = sellable_slots(do.suc_chua, plan_id, extra_disk_gb=dia_them_gb,
                         free_ipv4=do.free_ipv4,
                         gateway_slots=do.gateway_slots)
    cho = {
        RANG_BUOC_COMPUTE: ban.compute_slots,
        RANG_BUOC_IPV4: ban.ipv4_slots,
        RANG_BUOC_GATEWAY: ban.gateway_slots,
        RANG_BUOC_BANG_THONG: _cho_bang_thong(do, plan),
    }
    so_cho = min(cho.values())
    rang_buoc = next(ten for ten in _UU_TIEN if cho[ten] == so_cho)
    return KetQua(
        ban_duoc=so_cho >= 1,
        so_cho=so_cho,
        rang_buoc=rang_buoc,
        cau_cho_khach=_t(CAU_CHO_KHACH[rang_buoc]),
        cau_cho_van_hanh=(
            f"{plan_id}: compute={cho[RANG_BUOC_COMPUTE]} "
            f"ipv4={cho[RANG_BUOC_IPV4]} "
            f"gateway={cho[RANG_BUOC_GATEWAY]} "
            f"bang_thong={cho[RANG_BUOC_BANG_THONG]} "
            f"-> {so_cho} ({rang_buoc})"),
    )


# ── lớp đọc thế giới thật ────────────────────────────────────────────────────

def _suc_chua(db, profile) -> capacity.SucChua | None:
    """Sức chứa compute, hoặc `None` khi không đọc được.

    ⛔ Lý do kỹ thuật đi vào log, **không** đi ra trang. Đo trên production
       09/09/2026: trang bán hàng công khai in nguyên văn tên biến môi trường
       và cái tên `Proxmox`. `KetQua.cau_cho_khach` tồn tại để chuyện đó không
       lặp lại được — nhưng chỉ khi chỗ này chịu im.
    """
    from apps.vps.services import backend_factory, provisioning
    from apps.vps.services.proxmox import ChuaCauHinh, ProxmoxError

    try:
        client = backend_factory.compute_backend(profile).client
        return provisioning.suc_chua_hien_tai(
            db, client.trang_thai_node(), client.kho_luu_tru(),
            client.danh_sach_vm())
    except (ChuaCauHinh, ProxmoxError) as exc:
        log.warning("vps nguon luc: khong doc duoc suc chua: %s",
                    type(exc).__name__)
        return None


def _gioi_han_ip_va_cong(db, profile) -> tuple[int | None, int | None]:
    """`(IPv4 bán được, chỗ cổng vào)`. `None` ở vị trí nào = chưa đo được chỗ đó.

    Một nguồn cho cả trang bán và luồng tạo máy (R24). Trước đây `preflight`
    tính IPv4 **không** trừ `promised_without_ip` còn `routes` thì có, nên
    thành phần `capacity` báo xanh trong khi trang hiện 0 chỗ.
    """
    from apps.vps.services import backend_factory
    from apps.vps.services.sellable_capacity import (
        available_gateway_slots, effective_ipv4_slots, promised_without_ip)

    try:
        chi_tiet = backend_factory.public_ip_backend(db, profile).health().details
        free = effective_ipv4_slots(
            chi_tiet, promised_without_ip=promised_without_ip(db, profile.id))
    except backend_factory.operation_error_types() as exc:
        log.warning("vps nguon luc: khong doc duoc kho IP: %s",
                    type(exc).__name__)
        return None, None
    try:
        return free, available_gateway_slots(db, profile.id)
    except backend_factory.operation_error_types() as exc:
        log.warning("vps nguon luc: khong doc duoc cho cong vao: %s",
                    type(exc).__name__)
        return free, None


def bang_thong_da_hua_gb(db, profile_id: str | None) -> int:
    """Tổng hạn mức đã hứa cho các máy còn sống — số để so với ngân sách."""
    from sqlalchemy import select

    from apps.vps.tables import VpsInstance

    q = select(VpsInstance).where(VpsInstance.trang_thai != "da_xoa")
    if profile_id:
        q = q.where(VpsInstance.infrastructure_profile_id == profile_id)
    return bang_thong.tong_da_hua_gb(list(db.execute(q).scalars()))


def do_nguon_luc(db, profile=None) -> DoDuoc:
    """Đọc cả sáu tài nguyên một lượt. Không ném — đọc hỏng thành `None`."""
    from apps.vps import profiles
    from apps.vps.services import provisioning

    if profile is None:
        vung = provisioning.vung_dang_mo(db)
        if not vung:
            log.warning("vps nguon luc: khong co vung nao dang mo")
            return DoDuoc(None, None, None)
        try:
            profile = profiles.select_profile(db, region=vung[0][0])
        except profiles.ProfileNotReady as exc:
            # 🔴 Đây CHÍNH LÀ chỗ sinh ra "Hết chỗ" giả ngày 23/09: bản cũ trả
            #    `None` rồi để `trang_chinh` đọc nó thành `con_cho = False`.
            #    Nay nó vẫn trả `None`, nhưng `danh_gia` gọi đúng tên ràng buộc
            #    là `suc_khoe` và in đúng câu bảo trì.
            log.warning("vps nguon luc: khong co profile nhan may moi: %s", exc)
            return DoDuoc(None, None, None)

    free_ipv4, cong = _gioi_han_ip_va_cong(db, profile)
    return DoDuoc(
        suc_chua=_suc_chua(db, profile),
        free_ipv4=free_ipv4,
        gateway_slots=cong,
        da_hua_bang_thong_gb=bang_thong_da_hua_gb(db, profile.id),
        ngan_sach_bang_thong_gb=bang_thong.ngan_sach_hua_gb(),
    )


def con_ban_duoc(db, plan_id: str, *, dia_them_gb: int = 0,
                 do: DoDuoc | None = None) -> KetQua:
    """Bán được gói này ngay bây giờ không, và nếu không thì vì sao.

    `do` cho phép người gọi đo **một lần** rồi hỏi nhiều gói — trang bán hỏi cả
    ba gói, và ba lượt gọi Proxmox cho một lần dựng trang là ba lần chờ mạng.
    """
    return danh_gia(do if do is not None else do_nguon_luc(db), plan_id,
                    dia_them_gb=dia_them_gb)
