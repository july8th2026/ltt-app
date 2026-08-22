"""LTT Nexus — bề mặt KHÁCH HÀNG (Q93).

App này **không phải** là Nexus. Nó là cái khách nhìn thấy: danh sách máy, nút
ghép máy mới, nút thu hồi, và nhật ký "ai đã vào máy tôi". Toàn bộ danh tính
thiết bị, vé phiên và kiểm toán sống ở `platform_core/nexus/` — vì danh tính
thiết bị thuộc về **tài khoản**, không thuộc app, và app không được cấp phát
credential toàn hệ thống (`AGENTS.md` 8.4).

Không có `job_types` và không có `credit_cost`: app này không nộp việc gì cho
worker. Mô hình tiền của Nexus (Q98) là **trừ credit theo số máy đã ghép, mỗi
tháng** — không phải credit theo *lượt job*, nên `credit_cost` (giá mỗi lượt
job) vẫn là `None`. Điểm thu là **quyền mở phiên** (`cap_ve` từ chối khi hết
credit), không phải một lượt worker. Nạp thêm credit **chỉ trong trình duyệt**
(PayOS H9); app không xử lý thanh toán.

`enabled` đọc từ cờ `LTT_NEXUS` lúc nạp: cờ tắt thì app **không xuất hiện trong
catalog**. Route còn một lớp chặn nữa; hai lớp vì một lớp là chỗ để quên.
"""
from __future__ import annotations

from platform_core import nexus
from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry

MANIFEST = AppManifest(
    slug="nexus",
    display_name=N_('LTT Nexus — điều khiển máy từ xa'),
    route_prefix="/nexus",
    summary=N_('Điều khiển máy tính của bạn từ xa — không mở cổng, không cần '
               'IP tĩnh. Cài ứng dụng, đăng nhập cùng tài khoản, máy hiện ra là '
               'bấm vào dùng.'),
    icon="🖥️",
    accent="#3B5BDB",

    nav=(NavEntry("LTT Nexus", "/nexus", "🖥️", "nexus"),),

    # Không có job: app này chỉ quản lý thiết bị và phiên.
    job_types=(),
    requires=(),
    credit_cost=None,

    # Q73/Q74: hai trục riêng. `lifecycle` trả lời "chín tới đâu",
    # `capabilities` trả lời "thuộc thể loại nào" — trộn chúng làm bộ lọc
    # Marketplace khó hiểu.
    #
    # `development` chứ không `released`: phần điều khiển thật (engine, relay)
    # chưa có, nên gắn nhãn "Đã phát hành" là nói quá. Q73 cấm dùng chữ "Đã
    # hoàn thiện" chính vì loại nhầm lẫn này.
    surface="customer",
    # `released`: từ Q101/Model B, thứ khách thật sự dùng là app native + relay
    # LTT — cả hai đã chạy trên production và đã thu credit. Trang `/nexus` này
    # là cửa giới thiệu của nó, không còn là bản demo web-broker chưa có engine.
    lifecycle="released",
    capabilities=("Utilities",),
    group=N_("Ứng dụng"),

    # Fail-closed (Q93). Cờ tắt = không có trong catalog, không ai thấy.
    enabled=nexus.enabled(),
)
