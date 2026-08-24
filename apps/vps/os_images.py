"""Catalog hệ điều hành, và ràng buộc tối thiểu của từng bản.

## Vì sao ràng buộc tối thiểu nằm trong dữ liệu chứ không trong đầu người bán

Yêu cầu của Microsoft là con số cứng: **Windows 11 cần 64 GB đĩa và 4 GB RAM**,
Server 2022 cần 32 GB. Một tổ hợp (gói × OS) không đạt ngưỡng thì máy **không boot**
— và nó chỉ lộ ra sau khi khách đã trả tiền, đã chờ mười phút clone, và đang nhìn
một màn hình đen. Kiểm ở đây là kiểm trước khi thu tiền.

## `khach_thay`

Linux **không nằm trong catalog bán** (V9: chỉ Windows). Nó có mặt ở đây vì lý do
kỹ thuật thuần tuý: dựng chuỗi *web → job → clone → cấp cổng → khách vào được* bằng
`cloud-init` mất ~40 giây mỗi lượt và tất định; bằng Windows + sysprep mất 10–20
phút và có bốn cái bẫy đã biết. Chứng minh đường ống bằng Linux rồi mới cắm Windows
vào tách được "lỗi đường ống" khỏi "lỗi template Windows".

Và nó đã trả công ngay: chính template nội bộ này phát hiện ra **virtio không chạy
trên cụm** — một lỗi của *hạ tầng*, không của app, mà template Windows (vốn dùng
`sata0` sẵn) sẽ không bao giờ để lộ ra.

## VMID của template đọc từ môi trường

Template là thứ **của một cụm cụ thể**, không phải của mã nguồn. Ghim số vào code
nghĩa là dựng lại cụm là sửa code. Đọc từ `LTT_VPS_TEMPLATE_<ID>` — vd
`LTT_VPS_TEMPLATE_WINSRV2022_GUI=9002`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from apps.vps.cost import dia_tong_gb, lay_plan


@dataclass(frozen=True)
class OsImage:
    """Một bản hệ điều hành cài sẵn thành template."""

    id: str
    ten: str
    #: `windows` hoặc `linux` — quyết định dùng Cloudbase-Init hay cloud-init.
    ho: str
    ram_mb_toi_thieu: int
    disk_gb_toi_thieu: int
    #: Cổng khách thường dùng để vào — chỉ để **hiển thị hướng dẫn**, không còn
    #: dùng để cấu hình gì. NAT 1:1 mở toàn bộ cổng của IP riêng cho máy đó.
    cong_quen: int
    #: Hiện trong catalog bán không. False = template kỹ thuật, khách không thấy.
    khach_thay: bool
    ghi_chu: str = ""


OS_IMAGES: tuple[OsImage, ...] = (
    OsImage(
        id="debian-12", ten="Debian 12 (noi bo)", ho="linux",
        ram_mb_toi_thieu=1024, disk_gb_toi_thieu=10, cong_quen=22,
        khach_thay=False,
        ghi_chu="Template NOI BO de chung minh duong ong, khong ban (V9). "
                "PHAI la ban `generic`, KHONG phai `genericcloud`: genericcloud "
                "co y bo driver phan cung that (ke ca AHCI), ma dia cua ta la "
                "sata0 vi virtio treo tren cum nay — xem NHAT_KY 2026-08-23.",
    ),
    OsImage(
        id="ubuntu-24-04", ten="Ubuntu 24.04 LTS", ho="linux",
        ram_mb_toi_thieu=1024, disk_gb_toi_thieu=10, cong_quen=22,
        khach_thay=False,
        ghi_chu="Template NOI BO, KHONG dung nua. No chet vi virtio: cum nay "
                "chay long trong VMware va guest ghi vao thanh ghi notify cua "
                "virtio-pci thi khong bao gio quay ra. Dung `debian-12`.",
    ),
    OsImage(
        id="winsrv2022-core", ten="Windows Server 2022 (Core)", ho="windows",
        ram_mb_toi_thieu=2048, disk_gb_toi_thieu=32, cong_quen=3389,
        khach_thay=True,
        ghi_chu="Khong co giao dien do hoa. Nhe nhat trong cac ban Windows.",
    ),
    OsImage(
        id="winsrv2022-gui", ten="Windows Server 2022 (co giao dien)", ho="windows",
        ram_mb_toi_thieu=4096, disk_gb_toi_thieu=32, cong_quen=3389,
        khach_thay=True,
    ),
    OsImage(
        id="win10", ten="Windows 10", ho="windows",
        ram_mb_toi_thieu=4096, disk_gb_toi_thieu=32, cong_quen=3389,
        khach_thay=True,
    ),
    OsImage(
        id="win11", ten="Windows 11", ho="windows",
        # Microsoft: 4 GB RAM va 64 GB dia la SAN, khong phai khuyen nghi.
        ram_mb_toi_thieu=4096, disk_gb_toi_thieu=64, cong_quen=3389,
        khach_thay=True,
        ghi_chu="Can UEFI/OVMF + vTPM + Secure Boot trong cau hinh VM.",
    ),
)

_THEO_ID = {o.id: o for o in OS_IMAGES}


def lay_os(os_id: str) -> OsImage | None:
    return _THEO_ID.get(str(os_id or "").strip())


def os_ban_duoc() -> tuple[OsImage, ...]:
    """Những bản khách được chọn. Ubuntu không nằm ở đây (V9)."""
    return tuple(o for o in OS_IMAGES if o.khach_thay)


def hop_le(plan_id: str, os_id: str, dia_them_gb: int = 0) -> tuple[bool, str]:
    """Gói này có chạy nổi bản OS này không? Trả `(được, lý_do)`.

    `lý_do` viết cho khách đọc trên trang bán, không phải cho log.
    """
    plan = lay_plan(plan_id)
    if plan is None:
        return False, f"khong co goi {plan_id!r}"
    img = lay_os(os_id)
    if img is None:
        return False, f"khong co he dieu hanh {os_id!r}"

    if plan.ram_mb < img.ram_mb_toi_thieu:
        return False, (f"{img.ten} can toi thieu {img.ram_mb_toi_thieu // 1024} GB RAM, "
                       f"goi {plan.ten} chi co {plan.ram_mb // 1024} GB")
    dia = dia_tong_gb(plan_id, dia_them_gb)
    if dia < img.disk_gb_toi_thieu:
        return False, (f"{img.ten} can toi thieu {img.disk_gb_toi_thieu} GB dia, "
                       f"cau hinh nay chi co {dia} GB")
    return True, ""


def template_vmid(os_id: str, env: dict | None = None) -> int:
    """VMID của template cho một bản OS. 0 = chưa khai trong môi trường."""
    src = os.environ if env is None else env
    khoa = "LTT_VPS_TEMPLATE_" + str(os_id or "").upper().replace("-", "_")
    try:
        return int(str(src.get(khoa, "")).strip() or 0)
    except ValueError:
        return 0


def khoa_moi_truong(os_id: str) -> str:
    """Tên biến môi trường cần đặt cho một bản OS — để thông báo lỗi nói được
    chính xác phải làm gì, thay vì bắt người đọc đi tra tài liệu."""
    return "LTT_VPS_TEMPLATE_" + str(os_id or "").upper().replace("-", "_")
