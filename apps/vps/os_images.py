"""Catalog hệ điều hành: **đĩa cài đặt**, và ràng buộc tối thiểu của từng bản.

## Khách tự cài, nền tảng không dựng sẵn

Từ 2026-08-24 mỗi máy bán ra là một **máy trống + đĩa cài Windows**; khách tự chạy
trình cài đặt qua console và **tự đặt tài khoản, mật khẩu của chính họ**.

Điều đó đổi ba thứ ở file này:

* mỗi bản OS trỏ tới một **file ISO** (`LTT_VPS_ISO_<ID>`), không phải một template;
* `disk_gb_toi_thieu` quay về đúng **yêu cầu của Microsoft**, vì không còn thừa
  hưởng đĩa của template nào;
* nền tảng **không bao giờ biết mật khẩu của khách** — không giữ thì không làm lộ.

## Vì sao ràng buộc tối thiểu nằm trong dữ liệu chứ không trong đầu người bán

Yêu cầu của Microsoft là con số cứng: **Server 2016 và 2022 đều cần 32 GB đĩa**;
bản Core sống được với 2 GB RAM, bản có giao diện cần 4 GB. Một tổ hợp (gói × OS)
không đạt ngưỡng thì máy **không cài được** — và nó chỉ lộ ra sau khi khách đã trả
tiền và đang nhìn một thông báo lỗi của trình cài đặt. Kiểm ở đây là kiểm trước khi
thu tiền.

## Phạm vi: KHÔNG bán Windows 11 (chốt 2026-08-24)

Danh mục dừng ở **Server 2016, Server 2022 và Windows 10 LTSC**. Windows 11 đòi
UEFI/OVMF + vTPM + Secure Boot, tức một nhánh cấu hình máy **riêng** mà không bản
nào khác đi qua — nhánh chỉ một thứ dùng là nhánh không ai thử, và nó hỏng lặng lẽ.
Nhánh đó đã được gỡ khỏi `jobs.py`; muốn mở lại thì đọc `docs/VPS/PHAN_TICH_VPS_PROXMOX.md`
mục 11 để dựng lại, đừng đoán.

## `khach_thay`

Bản Linux nội bộ **không nằm trong catalog bán** (V9: chỉ Windows). Nó ở đây vì lý
do kỹ thuật thuần tuý: dựng chuỗi *web → job → máy → cấp IP → khách vào được* bằng
`cloud-init` mất ~40 giây mỗi lượt và tất định; bằng Windows thì mất 20–40 phút vì
có một con người ngồi bấm. Giữ một đường nhanh để tách "lỗi đường ống" khỏi "lỗi
trong lúc cài Windows".

## Đường dẫn ISO đọc từ môi trường

ISO là thứ **của một cụm cụ thể**, không phải của mã nguồn. Ghim tên file vào code
nghĩa là dựng lại cụm là sửa code. Đọc từ `LTT_VPS_ISO_<ID>` — vd
`LTT_VPS_ISO_WINSRV2022_GUI=local:iso/windows-server-2022-eval-en-us.iso`.
"""
from __future__ import annotations

from platform_core.i18n import N_

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
    #: Yêu cầu đĩa của chính hệ điều hành. Khách tự cài nên không còn thừa hưởng
    #: đĩa của template nào — số này là số của Microsoft, không hơn.
    disk_gb_toi_thieu: int
    #: Cổng khách thường dùng để vào — chỉ để **hiển thị hướng dẫn**, không còn
    #: dùng để cấu hình gì. NAT 1:1 mở toàn bộ cổng của IP riêng cho máy đó.
    cong_quen: int
    #: Hiện trong catalog bán không. False = bản kỹ thuật, khách không thấy.
    khach_thay: bool
    ghi_chu: str = ""


OS_IMAGES: tuple[OsImage, ...] = (
    OsImage(
        id="debian-12", ten=N_("Debian 12 (nội bộ)"), ho="linux",
        ram_mb_toi_thieu=1024, disk_gb_toi_thieu=10, cong_quen=22,
        khach_thay=False,
        ghi_chu="Ban NOI BO de chung minh duong ong, khong ban (V9). Day la anh "
                "cloud co san cloud-init nen may len trong ~40 giay, khac han "
                "Windows phai co nguoi ngoi cai. PHAI la ban `generic`, KHONG "
                "phai `genericcloud`: genericcloud co y bo driver phan cung that "
                "(ke ca AHCI), ma dia cua ta la sata0 vi virtio treo tren cum nay.",
    ),
    OsImage(
        id="ubuntu-24-04", ten="Ubuntu 24.04 LTS", ho="linux",
        ram_mb_toi_thieu=1024, disk_gb_toi_thieu=10, cong_quen=22,
        khach_thay=False,
        ghi_chu="Template NOI BO, KHONG dung nua. No chet vi virtio: cum nay "
                "chay long trong VMware va guest ghi vao thanh ghi notify cua "
                "virtio-pci thi khong bao gio quay ra. Dung `debian-12`.",
    ),
    # Một ISO Server phục vụ CẢ HAI bản Core và có giao diện: chọn bản nào là một
    # màn hình trong trình cài đặt, không phải hai bộ cài khác nhau. Tách thành hai
    # mục ở đây vì **sàn RAM khác nhau** (2 GB với Core, 4 GB với giao diện) — và
    # đó là thứ quyết định gói nào bán được bản nào.
    OsImage(
        id="winsrv2016-core", ten="Windows Server 2016 (Core)", ho="windows",
        ram_mb_toi_thieu=2048, disk_gb_toi_thieu=32, cong_quen=3389,
        khach_thay=True,
        ghi_chu=N_("Bản cũ hơn 2022. Chọn nó khi phần mềm của bạn cần đúng đời này."),
    ),
    OsImage(
        id="winsrv2016-gui", ten=N_("Windows Server 2016 (có giao diện)"), ho="windows",
        ram_mb_toi_thieu=4096, disk_gb_toi_thieu=32, cong_quen=3389,
        khach_thay=True,
    ),
    OsImage(
        id="winsrv2022-core", ten="Windows Server 2022 (Core)", ho="windows",
        ram_mb_toi_thieu=2048, disk_gb_toi_thieu=32, cong_quen=3389,
        khach_thay=True,
        ghi_chu=N_("Không có giao diện đồ hoạ. Nhẹ nhất trong các bản Windows."),
    ),
    OsImage(
        id="winsrv2022-gui", ten=N_("Windows Server 2022 (có giao diện)"), ho="windows",
        ram_mb_toi_thieu=4096, disk_gb_toi_thieu=32, cong_quen=3389,
        khach_thay=True,
    ),
    OsImage(
        # LTSC, không phải bản Home/Pro thường: đĩa cài trên node là
        # `win10-ltsc-2021-x64.iso`. Ghi đúng tên để khách không mua nhầm kỳ vọng
        # về Microsoft Store hay các ứng dụng đi kèm — LTSC không có chúng.
        id="win10", ten="Windows 10 LTSC 2021", ho="windows",
        # 32 GB là yêu cầu của Microsoft. Trước 24/08 số này là 80 vì máy nhân
        # bản từ template 80 GB và Proxmox không thu đĩa được; khách tự cài thì
        # ràng buộc đó biến mất.
        ram_mb_toi_thieu=4096, disk_gb_toi_thieu=32, cong_quen=3389,
        khach_thay=True,
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


def khoa_moi_truong(os_id: str) -> str:
    """Tên biến môi trường cần đặt cho một bản OS — để thông báo lỗi nói được
    chính xác phải làm gì, thay vì bắt người đọc đi tra tài liệu."""
    return "LTT_VPS_ISO_" + str(os_id or "").upper().replace("-", "_")


def dia_cai_dat(os_id: str, env: dict | None = None) -> str:
    """Volid của đĩa cài đặt, vd `local:iso/windows-server-2022-eval.iso`.

    Chuỗi rỗng = chưa khai trong môi trường. **Fail-closed**: chưa khai thì job
    từ chối tạo máy, thay vì tạo một máy trống không boot được rồi để khách nhìn
    màn hình đen mà không hiểu vì sao.
    """
    src = os.environ if env is None else env
    return str(src.get(khoa_moi_truong(os_id), "")).strip()

