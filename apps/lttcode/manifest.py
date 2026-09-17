"""LTTCODE — trang công khai + kênh phát hành của ứng dụng desktop (LTTCODEAPP).

App này không bán công cụ nào và không nộp job. Nó làm hai việc:

1. `/lttcode` — trang GIỚI THIỆU công khai (giới thiệu, hướng dẫn, nút tải bản
   `stable`), cùng khuôn với `/nexus` (spec "Trang công khai LTTCODE", 17/09).
   Vì vậy `surface="customer"` + `public=True`: có thẻ catalog và mục điều hướng,
   người chưa đăng nhập cũng đọc được.
2. Trả lời ứng dụng LTTCODE trên máy người dùng "có bản mới không", phục vụ bộ cài
   đã ký, đăng nhập thiết bị và tìm web — xem `routes.py`.

Không `ToolSpec`, không Job ⇒ về **API** app này vẫn `INTERNAL_ONLY`
(`docs/PUBLIC_API/APP_DISPOSITION_V1.md`); "công khai" ở đây là trang web.

Dữ liệu vận hành nằm trong thư mục dữ liệu (cập nhật nền tảng không đụng tới):
`lttcode_releases.json` và `lttcode_dist/`. Phát hành = `tools/release.ps1` ở kho
LTTCODEAPP ghi hai thứ đó; không cần deploy lại nền tảng.
"""
from __future__ import annotations

from apps.lttcode import bao_tri
from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry

MANIFEST = AppManifest(
    slug="lttcode",
    display_name=N_("LTTCODE — trợ lý lập trình AI"),
    route_prefix="/lttcode",
    summary=N_("Ứng dụng Windows giúp đọc, sửa mã và chạy lệnh trong thư mục dự án "
               "của bạn, dùng model của LTT Studios và trả bằng credit."),
    icon="⌨️",
    accent="#ef3731",

    nav=(NavEntry("LTTCODE", "/lttcode", "⌨️", "lttcode"),),

    job_types=(),
    requires=(),
    credit_cost=None,

    surface="customer",
    public=True,
    # `released`: bộ cài Windows phát qua kênh cập nhật. Trang chỉ hiện nút tải
    # khi kênh `stable` có bản; chưa có thì ghi "Sắp phát hành".
    lifecycle="released",
    capabilities=("Utilities",),
    group=N_("Ứng dụng"),

    # Bảng `lttcode_auth_codes` (mã một lần của "Đăng nhập LTT Studios").
    table_prefix="lttcode",
    # Dọn mã đăng nhập hết hạn (governance.STORES: `lttcode_auth_codes`).
    bao_tri=bao_tri.chay,
    bao_tri_moi_giay=3600,
)
