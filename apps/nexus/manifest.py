"""LTT Nexus — bề mặt KHÁCH HÀNG (Q93).

App này **không phải** là Nexus. Nó là cái khách nhìn thấy: danh sách máy, nút
ghép máy mới, nút thu hồi, và nhật ký "ai đã vào máy tôi". Toàn bộ danh tính
thiết bị, vé phiên và kiểm toán sống ở `platform_core/nexus/` — vì danh tính
thiết bị thuộc về **tài khoản**, không thuộc app, và app không được cấp phát
credential toàn hệ thống (`AGENTS.md` 8.4).

Không có `job_types` và không có `credit_cost`: app này không nộp việc gì cho
worker. Mô hình tiền của Nexus là **thuê bao tháng theo số máy** (Q93/D3), không
phải credit theo lượt — nên không có gì để tính giá ở đây.

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
    summary=N_('Ghép máy tính của bạn vào tài khoản, rồi điều khiển nó từ xa. '
               'Mọi phiên đều được ghi lại và bạn xem được ai đã vào máy nào.'),
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
    lifecycle="development",
    capabilities=("Utilities",),
    group=N_("Ứng dụng"),

    # Fail-closed (Q93). Cờ tắt = không có trong catalog, không ai thấy.
    enabled=nexus.enabled(),
)
