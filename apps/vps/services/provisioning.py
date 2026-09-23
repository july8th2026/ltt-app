"""Cấp phát: chọn cổng vào, cấp VMID, cấp cổng NAT, cấp IP.

## Luật duy nhất đáng nhớ ở file này

**Không đọc-rồi-ghi. Cứ ghi, và coi `IntegrityError` là đường chạy bình thường.**

Nền tảng chạy nhiều tiến trình worker. Mẫu "tìm số trống rồi lưu" có một khoảng
trống giữa hai bước, và với hai job cùng lúc thì hai máy sẽ nhận cùng một cổng —
máy sau ghi đè NAT của máy trước, khách đầu tiên mất kết nối **im lặng**, không có
lỗi nào để ai nhận ra. Đó là loại hỏng tệ nhất.

Cách đúng đã được `platform_core/gpu_lease.py` chứng minh trong production: ràng
buộc duy nhất ở tầng CSDL là trọng tài, `IntegrityError` nghĩa là *người khác vừa
giành trước*, và ta thử số kế tiếp. Không phải sự cố, không log ERROR.

## Vì sao mỗi lần thử nằm trong một savepoint

Một `IntegrityError` làm hỏng cả transaction đang mở: mọi câu lệnh sau đó đều bị
từ chối cho tới khi rollback. `begin_nested()` giới hạn thiệt hại vào đúng lần thử
đó, nên vòng lặp chạy tiếp được mà không mất những gì đã làm trước.
"""
from __future__ import annotations

from platform_core.i18n import N_

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from apps.vps.cost import dia_tong_gb, lay_plan
from apps.vps.services import capacity, mang
from apps.vps.tables import (VpsEvent, VpsGateway, VpsInstance, VpsIp,
                             )

log = logging.getLogger(__name__)

#: Trạng thái mà máy KHÔNG còn chiếm tài nguyên. Mọi trạng thái khác đều tính
#: vào phần "đã hứa" — kể cả `bi_treo`: máy treo vẫn giữ nguyên đĩa (V8 chỉ xoá
#: sau 7 ngày), nên chỗ đó chưa bán lại được.
KHONG_CHIEM_CHO = ("da_xoa",)

#: VMID Proxmox dành cho máy khách. Dưới 200 để cho template và máy nội bộ;
#: trên 899 không thuộc phạm vi V4 (quyết định D07: guard VMID 200–899).
VMID_DAU = 200
VMID_CUOI = 899

#: Cổng trong máy khách. RDP là mặc định vì catalog toàn Windows (V9).
CONG_SSH = 22


class HetChoError(RuntimeError):
    """Không còn cổng / VMID / IP để cấp. Thông điệp viết cho người đọc."""


class KhongCoGatewayError(RuntimeError):
    """Không có cổng vào nào đang nhận máy mới ở vùng khách chọn."""


# ── phần đã hứa với khách ────────────────────────────────────────────────────

def da_hua(db: DbSession, *, chi_chua_tao: bool = False) -> tuple[int, int]:
    """Tổng RAM (MB) và đĩa (GB) app đã cam kết với khách. Trả `(ram, dia)`.

    `chi_chua_tao=True` chỉ đếm những máy **chưa có VMID** — tức job provision
    chưa tạo VM trên Proxmox. Dùng khi ghép với `capacity.cam_ket_tu_vm()`: máy
    đã có VMID thì Proxmox đã đếm rồi, cộng lần nữa là đếm đúp và app sẽ từ chối
    bán trong khi vẫn còn chỗ.
    """
    dieu_kien = [VpsInstance.trang_thai.not_in(KHONG_CHIEM_CHO)]
    if chi_chua_tao:
        dieu_kien.append(VpsInstance.vmid.is_(None))
    rows = db.execute(
        select(VpsInstance.plan_id, VpsInstance.dia_them_gb, func.count())
        .where(*dieu_kien)
        .group_by(VpsInstance.plan_id, VpsInstance.dia_them_gb)
    ).all()

    ram_mb = 0
    dia_gb = 0
    for plan_id, them, so_luong in rows:
        plan = lay_plan(plan_id)
        if plan is None:
            # Gói đã gỡ khỏi bảng giá nhưng máy cũ vẫn chạy. Không được bỏ qua —
            # nó vẫn ăn chỗ thật. Đếm theo cấu hình lớn nhất để nghiêng về an toàn.
            log.warning("vps: goi %r khong con trong bang gia, dem theo goi lon nhat",
                        plan_id)
            from apps.vps.cost import PLANS
            plan = max(PLANS, key=lambda p: p.ram_mb)
            can_dia = plan.disk_gb + int(them or 0)
        else:
            can_dia = dia_tong_gb(plan_id, int(them or 0))
        ram_mb += plan.ram_mb * int(so_luong)
        dia_gb += can_dia * int(so_luong)
    return ram_mb, dia_gb


def suc_chua_hien_tai(db: DbSession, trang_thai_node: dict, kho: list,
                      vms: list | None = None) -> capacity.SucChua:
    """Sức chứa thật của node, ghép từ HAI nguồn — và cần cả hai.

    * **Proxmox** biết node đang cam kết bao nhiêu cho *mọi* VM, kể cả những máy
      không thuộc app này. Đây là con số nền, và bỏ nó đi là bán chỗ của chính
      chủ nhà (xem `capacity.cam_ket_tu_vm`).
    * **CSDL của app** biết những máy vừa bán mà job provision **chưa kịp tạo
      VM** — Proxmox chưa thấy chúng, nhưng chỗ thì đã hứa rồi.

    Cộng đúng một lần mỗi máy: máy đã có VMID nằm ở nguồn thứ nhất, máy chưa có
    nằm ở nguồn thứ hai.
    """
    goc = capacity.suc_chua_tu_proxmox(trang_thai_node, kho)
    ram_vm, dia_vm, vcpu_vm = capacity.cam_ket_tu_vm(vms or [])
    ram_cho, dia_cho = da_hua(db, chi_chua_tao=True)
    lon = capacity.kho_lon_nhat(kho)
    return capacity.SucChua(
        cpu_tong=goc.cpu_tong,
        # Chỉ đếm vCPU của VM ĐANG CÓ trên Proxmox. Máy app đã hứa mà chưa tạo
        # thì phần vCPU của nó nhỏ (1–4) và sẽ vào ngay ở lượt sau — không đáng
        # thêm một truy vấn nữa vào đường bán hàng.
        vcpu_da_hua=vcpu_vm,
        ram_mb_tong=goc.ram_mb_tong,
        dia_gb_tong=goc.dia_gb_tong,
        ram_mb_da_hua=ram_vm + ram_cho,
        dia_gb_da_hua=dia_vm + dia_cho,
        # Chỗ THỰC đã ghi trên kho. Với LVM-thin nó nhỏ hơn nhiều so với đã hứa,
        # và chính khoảng lệch đó là thứ V14 cho phép bán (xem `capacity`).
        dia_gb_dang_dung=int(lon.get("used") or 0) // (1024 ** 3))


# ── chọn cổng vào ────────────────────────────────────────────────────────────

#: Nhãn người đọc cho từng vùng. Thiếu nhãn thì hiện mã vùng — xấu nhưng đúng,
#: còn hơn giấu một vùng đang mở khỏi trang bán.
NHAN_VUNG = {
    "sgp": "Singapore",
    "vn": N_("Việt Nam"),
}


def vung_dang_mo(db: DbSession) -> list[tuple[str, str]]:
    """Các vùng **thật sự có cổng vào đang nhận máy**, dạng `[(mã, nhãn)]`.

    Trang bán phải dựng bộ chọn vùng từ đây, không được viết cứng danh sách.

    Đã trả giá cho việc viết cứng: sau khi bỏ mô hình chia cổng, trang vẫn còn
    ba lựa chọn cũ và **mặc định là `port`** — một vùng không còn tồn tại. Khách
    bấm "Thuê máy này" thì gặp `khong co cong vao nao dang mo o vung 'port'`,
    một câu không nói được gì với họ. Bộ test không thấy vì nó gọi thẳng hàm với
    vùng đúng.
    """
    ma = sorted({str(g.vung) for g in db.execute(
        select(VpsGateway).where(VpsGateway.dang_nhan_may_moi.is_(True))
    ).scalars() if str(g.vung or "").strip()})
    return [(x, NHAN_VUNG.get(x, x)) for x in ma]


def chon_gateway(db: DbSession, vung: str, *,
                 infrastructure_profile_id: str | None = None) -> VpsGateway:
    """Cổng vào đang nhận máy mới ở một vùng. Không có → lỗi rõ ràng.

    Chọn cái **còn nhiều địa chỉ trống nhất** để các cổng đầy đều nhau, thay vì
    nhồi một cái tới cạn rồi mới sang cái sau.
    """
    dieu_kien = [VpsGateway.vung == str(vung),
                 VpsGateway.dang_nhan_may_moi.is_(True)]
    if infrastructure_profile_id is not None:
        dieu_kien.append(
            VpsGateway.infrastructure_profile_id == infrastructure_profile_id)
    ung_vien = list(db.execute(
        select(VpsGateway).where(*dieu_kien)
    ).scalars())
    if not ung_vien:
        raise KhongCoGatewayError(f"khong co cong vao nao dang mo o vung {vung!r}")

    def con_trong(g: VpsGateway) -> int:
        da_dung = db.execute(
            select(func.count()).select_from(VpsInstance)
            .where(VpsInstance.gateway_id == g.id,
                   VpsInstance.ip_noi_bo.is_not(None))
        ).scalar_one()
        return mang.so_dia_chi(g) - int(da_dung)

    return max(ung_vien, key=con_trong)


# ── cấp phát nguyên tử ───────────────────────────────────────────────────────

def _thu_ghi(db: DbSession, doi_tuong) -> bool:
    """Ghi một bản ghi trong savepoint. False = người khác vừa giành trước."""
    try:
        with db.begin_nested():
            db.add(doi_tuong)
            db.flush()
        return True
    except IntegrityError:
        return False


def cap_vmid(db: DbSession, instance: VpsInstance, *, goi_y: int = 0,
             da_co_tren_may_chu: Iterable[int] = ()) -> int:
    """Cấp VMID cho một máy. `goi_y` là số Proxmox đề nghị (`/cluster/nextid`).

    Số của Proxmox chỉ là gợi ý: hai job hỏi cùng lúc nhận cùng một số. Trọng tài
    là ràng buộc duy nhất trên `vps_instance.vmid`.

    **`da_co_tren_may_chu` không phải tối ưu hoá — nó là hàng rào an toàn.** Hỏi
    một mình CSDL là chưa đủ: máy nào tồn tại trên Proxmox mà CSDL không biết
    (dựng bằng tay, CSDL khôi phục từ backup, hai môi trường dùng chung cụm) sẽ
    được cấp lại số của nó — và `jobs.py` thấy VM đã tồn tại nên **bỏ qua bước
    nhân bản rồi cấu hình lại chính máy đó**, tức giao máy của người này cho
    người khác. Không lỗi nào được ghi ra.

    Đã dính thật ngày 24/08 khi chạy thử với CSDL rỗng: job chiếm đúng VM 200
    đang chạy và đổi tên nó.
    """
    dang_dung = {int(v) for v in db.execute(
        select(VpsInstance.vmid).where(VpsInstance.vmid.is_not(None))
    ).scalars() if v is not None}
    dang_dung |= {int(v) for v in da_co_tren_may_chu}

    bat_dau = max(VMID_DAU, int(goi_y or 0))
    for vmid in _dai_so(bat_dau, VMID_DAU, VMID_CUOI):
        if vmid in dang_dung:
            continue
        try:
            with db.begin_nested():
                instance.vmid = vmid
                db.flush()
            return vmid
        except IntegrityError:
            instance.vmid = None
            dang_dung.add(vmid)
    raise HetChoError(f"het VMID trong dai {VMID_DAU}-{VMID_CUOI}")


def cap_ip_noi_bo(db: DbSession, instance: VpsInstance,
                  gateway: VpsGateway) -> str:
    """Cấp cho máy một địa chỉ trong mạng riêng. Nguyên tử theo luật đầu file.

    Khác `cap_vmid`: ở đây không INSERT bản ghi mới mà **UPDATE chính máy**, nên
    trọng tài là ràng buộc duy nhất `(gateway_id, ip_noi_bo)` trên `vps_instance`.
    Cứ ghi, `IntegrityError` nghĩa là worker khác vừa giành trước địa chỉ đó.
    """
    if instance.ip_noi_bo:
        return str(instance.ip_noi_bo)

    da_dung = {str(x) for x in db.execute(
        select(VpsInstance.ip_noi_bo).where(
            VpsInstance.gateway_id == gateway.id,
            VpsInstance.ip_noi_bo.is_not(None))
    ).scalars()}

    for dia_chi in mang.dai_dia_chi(gateway):
        if dia_chi in da_dung:
            continue
        instance.ip_noi_bo = dia_chi
        instance.gateway_id = gateway.id
        if _thu_ghi(db, instance):
            return dia_chi
        instance.ip_noi_bo = None
        da_dung.add(dia_chi)
    raise HetChoError(
        f"het dia chi tren cong vao {gateway.ten!r} "
        f"(dai octet {gateway.octet_dau}-{gateway.octet_cuoi})")


def cap_ip(db: DbSession, instance: VpsInstance, gateway: VpsGateway) -> VpsIp:
    """Gán một IP công cộng còn trống cho máy.

    Không INSERT mà UPDATE: IP là tài nguyên **đã mua sẵn**, có sẵn trong bảng.
    Ràng buộc duy nhất trên `instance_id` vẫn là trọng tài khi hai job tranh nhau.
    """
    if not gateway.cho_phep_ip_rieng:
        raise HetChoError(f"cong vao {gateway.ten!r} khong ban IP rieng")

    trong = list(db.execute(
        select(VpsIp).where(VpsIp.gateway_id == gateway.id,
                            VpsIp.instance_id.is_(None))
    ).scalars())
    for ip in trong:
        try:
            with db.begin_nested():
                ip.instance_id = instance.id
                db.flush()
            return ip
        except IntegrityError:
            ip.instance_id = None
    raise HetChoError(f"het IP trong tren cong vao {gateway.ten!r}")


def _dai_so(bat_dau: int, thap_nhat: int, cao_nhat: int) -> Iterable[int]:
    """Đếm từ `bat_dau` tới hết dải rồi vòng lại từ đầu — mỗi số đúng một lần."""
    bat_dau = min(max(int(bat_dau), thap_nhat), cao_nhat)
    yield from range(bat_dau, cao_nhat + 1)
    yield from range(thap_nhat, bat_dau)


# ── nhật ký vòng đời ─────────────────────────────────────────────────────────

def ghi_su_kien(db: DbSession, instance_id: str, loai: str, *,
                boi: str = "he_thong", **chi_tiet) -> VpsEvent:
    """Ghi một mốc vào nhật ký của máy. Đây là thứ trả lời khách, không phải log."""
    su_kien = VpsEvent(instance_id=instance_id, loai=str(loai),
                       boi=str(boi), chi_tiet=dict(chi_tiet))
    db.add(su_kien)
    db.flush()
    return su_kien


@dataclass(frozen=True)
class ThoiGianSanSang:
    """Bao lâu từ lúc khách bấm "Tạo máy" tới lúc máy dùng được."""

    p50_giay: int
    p90_giay: int
    so_mau: int


#: Dưới ngần này lần tạo thành công thì **không hứa gì**. Một lần đo không phải
#: một phân bố, và một lời hứa dựng từ nó là một lời hứa dựng từ may rủi.
TOI_THIEU_MAU = 3


def thoi_gian_san_sang(db, *, toi_da_mau: int = 20) -> "ThoiGianSanSang | None":
    """Thời gian tới lúc sẵn sàng, **đo từ chính các máy đã tạo xong**.

    ## Vì sao không viết cứng một con số

    Chủ dự án chốt 23/09/2026: giữ cách mua IP OVH theo yêu cầu, nhưng **nói
    trước** với khách rằng họ sẽ chờ. Đường tạo máy có một bước đặt mua địa chỉ
    IP ở OVH với `order_delivery_timeout_seconds = 3600`, nên "vài giây" là sai
    và khách bấm xong sẽ ngồi nhìn một trang không nói gì.

    Một con số viết cứng thì không ai kiểm lại: hạ tầng chậm đi, trang vẫn nói
    "3 phút" mãi mãi. Nên số này đo từ khoảng `tao_moi` → `tao_xong` của các
    máy **thật sự** đã lên, lấy `toi_da_mau` lần gần nhất.

    `None` = chưa đủ mẫu để nói gì. Im lặng đúng hơn là đoán.

    ⚠️ Máy hỏng không có `tao_xong`, nên nó không đóng góp số nào — cố ý. Đếm
       nó bằng "bây giờ trừ lúc bắt đầu" sẽ biến mỗi máy hỏng thành một con số
       khổng lồ, và lời hứa cho khách trôi ra vô tận.
    """
    bat_dau: dict[str, datetime] = {}
    ket_thuc: dict[str, datetime] = {}
    for e in db.execute(
        select(VpsEvent)
        .where(VpsEvent.loai.in_(("tao_moi", "tao_xong")))
        .order_by(VpsEvent.created_at.desc())
        .limit(toi_da_mau * 8)
    ).scalars():
        (bat_dau if e.loai == "tao_moi" else ket_thuc)[e.instance_id] = e.created_at

    cap: list[tuple[datetime, int]] = []
    for instance_id, xong in ket_thuc.items():
        moi = bat_dau.get(instance_id)
        if moi is None:
            continue
        giay = int((_utc(xong) - _utc(moi)).total_seconds())
        if giay < 0:
            # Đồng hồ lệch hoặc sự kiện ghi lại sau: một khoảng âm là bằng
            # chứng hỏng, không phải một mẫu nhanh kỷ lục.
            continue
        cap.append((xong, giay))

    if len(cap) < TOI_THIEU_MAU:
        return None
    cap.sort(key=lambda x: x[0], reverse=True)
    giay = sorted(g for _x, g in cap[:toi_da_mau])
    return ThoiGianSanSang(
        p50_giay=giay[(len(giay) - 1) // 2 + (len(giay) % 2 == 0)],
        p90_giay=giay[min(len(giay) - 1, int(len(giay) * 0.9))],
        so_mau=len(giay),
    )


def _utc(gt: datetime) -> datetime:
    return gt if gt.tzinfo else gt.replace(tzinfo=timezone.utc)
