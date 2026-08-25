"""Bản khai của app VPS. Nền tảng chỉ đọc file này.

Ba điều đáng nói, vì cả ba đều khác với app AI thông thường:

**1. `credit_cost` trả 0, không phải None.** Điểm thu của VPS là *máy còn sống hay
không*, thu mỗi 30 ngày (khuôn Q98), chứ không phải *lượt job*. Xem `cost.py`.

**2. `enabled` đọc cờ lúc nạp.** Cờ `LTT_VPS` tắt → app không xuất hiện trong
catalog. `routes.py` chặn thêm một lớp nữa để URL gõ thẳng cũng không trả lời.

**3. `gpu_vram_mb` để trống nhưng `max_runtime_s` thì không.** Tạo một máy Windows
là clone + sysprep + boot lần đầu: vài phút, đôi khi hơn mười. Không khai trần thì
job treo giữ slot vô hạn, và với đội hình vài tiến trình worker thì vài job như
vậy là dừng cả nền tảng — im lặng, không ai được báo.
"""
from __future__ import annotations

import apps.vps as vps_app
from apps.vps import bao_tri
from apps.vps.cost import credit_cost
from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry

MANIFEST = AppManifest(
    slug="vps",
    display_name=N_('LTT VPS — máy chủ ảo Windows'),
    route_prefix="/vps",
    summary=N_('Thuê máy chủ ảo Windows, tạo xong trong vài phút, trả bằng '
               'credit. Bạn tự chọn cấu hình và vùng đặt máy.'),
    icon="🖥️",
    accent="#0B7285",

    nav=(NavEntry("LTT VPS", "/vps", "🖥️", "vps"),),

    job_types=("vps.provision", "vps.rebuild", "vps.destroy"),
    # Chỉ gọi HTTP tới Proxmox trong LAN — không cần GPU, không cần ffmpeg.
    requires=("api",),
    credit_cost=credit_cost,

    # Trần thời gian cho MỘT job. Con số theo việc thật, không theo cảm tính:
    # clone một template Windows rồi sysprep + boot lần đầu mất 5–15 phút trên
    # ảo hoá lồng. 30 phút là trần để job treo bị cắt, không phải thời gian kỳ vọng.
    max_runtime_s={
        "vps.provision": 1800,
        "vps.rebuild": 1800,
        "vps.destroy": 600,
    },

    # Việc nền định kỳ: thu tiền, treo máy hết tiền, xoá máy quá hạn ân hạn.
    # Nền tảng gọi nó DƯỚI lease `bao_tri`, nên nó chạy đúng một lần trên toàn
    # cụm dù có bao nhiêu tiến trình worker. Xem `bao_tri.py` để biết vì sao đây
    # là hợp đồng chứ không phải vòng lặp tự dựng.
    bao_tri=bao_tri.chay,
    bao_tri_moi_giay=3600,

    table_prefix="vps",

    surface="customer",
    # `development`: hạ tầng mới dựng, chưa có máy khách nào chạy thật. Q73 cấm
    # dùng nhãn marketing để giả trạng thái — đổi sang `released` khi P1 xanh.
    lifecycle="development",
    capabilities=("Utilities",),
    # Nhóm RIÊNG trên thanh tiêu đề, ngang hàng với "Ứng dụng" — chốt của chủ
    # sản phẩm 25/08: *"VPS là menu riêng; Ứng dụng là các tiện ích sau này tôi
    # xây dựng."*
    #
    # Tên nhóm để nguyên "VPS", không dịch và không bọc `N_()`: nó giống nhau ở
    # cả hai ngôn ngữ, và một msgid không có gì để dịch chỉ làm bánh cóc i18n
    # phải đếm thêm một dòng vô ích.
    #
    # ⚠️ Nhóm này có ĐÚNG MỘT app. Bốn nhóm kia gom nhiều app; thêm một nhóm
    # một-app làm thanh tiêu đề dài ra cho MỌI trang và MỌI người dùng, kể cả
    # người không mua VPS. Đó là cái giá, và chủ sản phẩm đã biết khi chốt.
    group="VPS",

    # Fail-closed. Cờ tắt = không có trong catalog, không ai thấy.
    enabled=vps_app.enabled(),
    # Hiện thẻ app cho cả khách CHƯA đăng nhập. `/vps` phục vụ hai thứ tuỳ
    # người xem: ẩn danh thấy bảng giá, đã đăng nhập thấy máy của mình — nên
    # thẻ này không dẫn tới ngõ cụt.
    #
    # Vẫn an toàn khi chưa mở bán: `enabled` đọc cờ `LTT_VPS`, và cờ tắt thì app
    # KHÔNG xuất hiện trong catalog dù `public=True`.
    public=True,

    notes="Proxmox chạy LỒNG trong VMware trên máy B. Trần công suất là ĐĨA và "
          "RAM — xem docs/VPS/PHAN_TICH_VPS_PROXMOX.md muc 2 truoc khi doi gia.",
)
