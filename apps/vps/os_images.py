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

Yêu cầu của Microsoft là con số cứng: **Windows 11 cần 64 GB đĩa và 4 GB RAM**,
Server 2022 cần 32 GB. Một tổ hợp (gói × OS) không đạt ngưỡng thì máy **không cài
được** — và nó chỉ lộ ra sau khi khách đã trả tiền và đang nhìn một thông báo lỗi
của trình cài đặt. Kiểm ở đây là kiểm trước khi thu tiền.

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
    #: Máy cài bản này có cần UEFI + vTPM + Secure Boot không. Windows 11 thì có,
    #: và thiếu nó thì trình cài đặt dừng ở "This PC can't run Windows 11".
    can_uefi_tpm: bool = False
    ghi_chu: str = ""


OS_IMAGES: tuple[OsImage, ...] = (
    OsImage(
        id="debian-12", ten="Debian 12 (noi bo)", ho="linux",
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
        # 32 GB là yêu cầu của Microsoft. Trước 24/08 số này là 80 vì máy nhân
        # bản từ template 80 GB và Proxmox không thu đĩa được; khách tự cài thì
        # ràng buộc đó biến mất.
        ram_mb_toi_thieu=4096, disk_gb_toi_thieu=32, cong_quen=3389,
        khach_thay=True,
    ),
    OsImage(
        id="win11", ten="Windows 11", ho="windows",
        # Microsoft: 4 GB RAM va 64 GB dia la SAN, khong phai khuyen nghi.
        ram_mb_toi_thieu=4096, disk_gb_toi_thieu=64, cong_quen=3389,
        khach_thay=True, can_uefi_tpm=True,
        ghi_chu="Trinh cai dat dung o 'This PC can't run Windows 11' neu thieu "
                "UEFI/OVMF + vTPM + Secure Boot.",
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

