"""Bảng giá VPS và quy đổi sang credit (Q103 V6, Q104 V11).

Giá **neo vào đối thủ Việt Nam**, không neo vào Vultr (V5). Vultr chỉ còn để đối
chiếu: gói 2 vCPU/4 GB của họ là $20 ≈ 520.000đ, còn AZDIGI bán 1 vCPU/1 GB từ
79.000đ **kèm RAID-10, backup tuần và SLA 99,9%** — thứ hạ tầng của ta không có.
Vì thế giá ở đây phải rẻ hơn họ rõ rệt, và trang bán phải nói thật về SLA.

## Vì sao cấu hình đĩa lớn hơn cảm giác

Catalog chỉ có Windows (V9). Yêu cầu tối thiểu của Microsoft là **32 GB đĩa**
(Server 2016 và 2022 đều là **32 GB**), nên không có gói nào dưới 40 GB. Bản nháp đầu từng ghi
25 GB cho gói rẻ nhất — con số đó **không cài nổi Windows**, và nó là loại lỗi
chỉ lộ ra khi khách đã trả tiền.

## `credit_cost` trả 0 — cố ý, không phải quên

Nền tảng tính tiền theo **lượt job**. VPS thì không: điểm thu là **máy còn sống
hay không**, thu mỗi 30 ngày, đúng khuôn Q98 (`NexusDevice.paid_until`). Một lượt
`vps.provision` tự nó không đáng giá gì — tiền đã thu ở chỗ khác. Trả 0 chứ không
để `None` vì hợp đồng app (`tools/lint_app_contract.py`) bắt buộc app có khai
`job_types` thì phải có `credit_cost`; `None` sẽ thành "app chưa thu phí", sai
hẳn về nghĩa.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.billing_math import credits_base_tu_vnd
from platform_core.i18n import N_

#: Đĩa bán thêm: bán theo lô 10 GB.
DIA_THEM_MOI_LO_GB = 10
GIA_MOI_LO_DIA_VND = 25_000

#: Một chu kỳ thuê bao. 30 ngày, giống Nexus (Q98) — cùng khuôn, cùng cách nghĩ.
CHU_KY_NGAY = 30


@dataclass(frozen=True)
class Plan:
    """Một gói bán. Bất biến: đổi giá là thêm gói mới, không sửa gói đang bán.

    Việc "gói này chạy được bản nào" **không** khai ở đây. Nó suy ra từ số thật
    trong `os_images.hop_le()`: so `plan.ram_mb` với `img.ram_mb_toi_thieu`, và
    đĩa với `img.disk_gb_toi_thieu`.

    Trước 24/08 ở đây còn một trường `os_toi_thieu` khai tay điều đó. **Không nơi
    nào đọc nó** — nó là nguồn chân lý thứ hai cho một câu hỏi đã có nguồn thứ
    nhất, và nó đã kịp lệch: nó trỏ vào `win11`, một bản không còn trong danh mục.
    """

    id: str
    ten: str
    vcpu: int
    #: RAM là tài nguyên CỨNG — giữ chỗ thật, không dùng chung (V14).
    ram_mb: int
    #: Đĩa là **HẠN MỨC**, không phải chỗ đã giữ (V14). Kho là LVM-thin nên máy
    #: chỉ chiếm phần nó ghi thật; khách khai 60 GB có thể chỉ đang dùng 12 GB.
    #: Giữ chỗ cứng cho từng máy là lãng phí 3/4 kho và làm sản phẩm không bán
    #: được. Đổi lại: phải có phanh — xem `services/capacity.py`.
    disk_gb: int
    #: Hạn mức băng thông mỗi chu kỳ, tính bằng GB. Vượt thì **hãm tốc**, không
    #: cắt và không tính thêm tiền — đúng như trang bán viết. 0 = không hãm.
    #:
    #: Tổng đã hứa vượt 2 TB của cổng vào Vultr là **có chủ ý** (bán chồng, cùng
    #: khuôn với đĩa thin ở V14), nhưng nó là rủi ro cần nhìn thấy chứ không phải
    #: mẹo — xem `bang_thong.tong_da_hua_gb`.
    bang_thong_gb: int
    gia_thang_vnd: int
    mo_ta: str
    #: Gói **khuyến nghị**. Đúng MỘT gói được đặt cờ này.
    #:
    #: Có nó vì trang bán cần đánh dấu một gói, và hai cách còn lại đều trôi:
    #: đọc văn xuôi trong `mo_ta` thì trượt khi đổi câu chữ; viết cứng id gói
    #: trong template thì trượt khi đổi id. Cả hai trôi **lặng lẽ** — trang vẫn
    #: render, chỉ là không còn dấu nào.
    nen_chon: bool = False

    @property
    def credit_thang(self) -> int:
        """Giá quy ra credit. Một chỗ duy nhất, dùng toán của nền tảng (Q31)."""
        return credits_base_tu_vnd(self.gia_thang_vnd)


PLANS: tuple[Plan, ...] = (
    Plan(
        id="vps-nho",
        ten=N_("VPS Nhỏ"),
        vcpu=1,
        ram_mb=2048,
        disk_gb=40,
        bang_thong_gb=300,
        gia_thang_vnd=149_000,
        mo_ta=N_("Chạy được Windows Server 2016 hoặc 2022 bản Core (không có giao "
                 "diện đồ hoạ). Hợp khi bạn chỉ cần một máy chạy phần mềm hoặc "
                 "script nền."),
    ),
    Plan(
        id="vps-vua",
        ten=N_("VPS Vừa"),
        vcpu=2,
        ram_mb=4096,
        disk_gb=60,
        bang_thong_gb=600,
        gia_thang_vnd=179_000,
        mo_ta=N_("Chạy được mọi bản trong danh mục: Server 2016 và 2022 có giao "
                 "diện, hoặc Windows 10 LTSC. Đây là gói phần lớn người dùng nên "
                 "chọn."),
        nen_chon=True,
    ),
    Plan(
        id="vps-lon",
        ten=N_("VPS Lớn"),
        vcpu=4,
        ram_mb=8192,
        disk_gb=80,
        bang_thong_gb=1000,
        gia_thang_vnd=329_000,
        # Gói này KHÔNG mở thêm bản Windows nào — mọi bản trong danh mục đã chạy
        # được ở gói Vừa. Nó bán CPU, RAM và đĩa, và mô tả phải nói đúng thế;
        # câu cũ ("đủ đĩa cho Windows 11") nay vừa sai vừa mời một thứ không bán.
        mo_ta=N_("Gấp đôi CPU và RAM của gói Vừa, đĩa 80 GB. Hợp khi bạn chạy "
                 "phần mềm nặng hoặc nhiều việc cùng lúc — không phải để cài "
                 "thêm bản Windows nào khác."),
    ),
)

_THEO_ID = {p.id: p for p in PLANS}


def lay_plan(plan_id: str) -> Plan | None:
    """Tra một gói theo id. Trả None nếu không có — người gọi tự quyết cách báo."""
    return _THEO_ID.get(str(plan_id or "").strip())


def gia_thang_vnd(plan_id: str, dia_them_gb: int = 0) -> int:
    """Tiền một chu kỳ, đã cộng đĩa mua thêm. Đơn vị VNĐ.

    `dia_them_gb` phải là bội của 10 — bán theo lô để không phải quản lý những
    con số lẻ mà chính ta cũng không cấp phát được gọn trên LVM/ZFS.
    """
    plan = lay_plan(plan_id)
    if plan is None:
        raise ValueError(f"khong co goi {plan_id!r}")
    them = int(dia_them_gb or 0)
    if them < 0:
        raise ValueError("dia_them_gb am")
    if them % DIA_THEM_MOI_LO_GB:
        raise ValueError(
            f"dia_them_gb phai la boi cua {DIA_THEM_MOI_LO_GB}")
    so_lo = them // DIA_THEM_MOI_LO_GB
    return plan.gia_thang_vnd + so_lo * GIA_MOI_LO_DIA_VND


def credit_thang(plan_id: str, dia_them_gb: int = 0) -> int:
    """Tiền một chu kỳ, quy ra credit. Đây là con số thực sự bị trừ khỏi số dư."""
    return credits_base_tu_vnd(gia_thang_vnd(plan_id, dia_them_gb))


def dia_tong_gb(plan_id: str, dia_them_gb: int = 0) -> int:
    """Tổng đĩa cấp cho một máy = đĩa của gói + đĩa mua thêm."""
    plan = lay_plan(plan_id)
    if plan is None:
        raise ValueError(f"khong co goi {plan_id!r}")
    return plan.disk_gb + int(dia_them_gb or 0)


def credit_cost(params: dict) -> int:
    """Giá credit của một LƯỢT JOB. Luôn 0 — xem docstring đầu file."""
    return 0
