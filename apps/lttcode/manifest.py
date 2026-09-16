"""LTTCODE — kênh phát hành của ứng dụng desktop (spec updater, LTTCODEAPP).

App này không bán công cụ nào và không nộp job: nó chỉ trả lời ứng dụng LTTCODE
trên máy người dùng "có bản mới không" và phục vụ bộ cài đã ký. Vì vậy nó là
`surface="runtime"` (không có thẻ catalog, không có mục điều hướng) và mọi route
đều công khai — xem `routes.py`.

Dữ liệu vận hành nằm trong thư mục dữ liệu (cập nhật nền tảng không đụng tới):
`lttcode_releases.json` và `lttcode_dist/`. Phát hành = `tools/release.ps1` ở kho
LTTCODEAPP ghi hai thứ đó; không cần deploy lại nền tảng.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest

MANIFEST = AppManifest(
    slug="lttcode",
    display_name=N_("LTTCODE — tải về và cập nhật"),
    route_prefix="/lttcode",
    summary=N_("Trang tải và kênh cập nhật của ứng dụng LTTCODE cho Windows."),
    job_types=(),
    requires=(),
    credit_cost=None,
    surface="runtime",
    public=False,
    lifecycle="internal",
)
