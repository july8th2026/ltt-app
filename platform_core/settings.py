"""
settings.py — hồ sơ môi trường của tiến trình. Một câu hỏi, một câu trả lời.

Đây là phần **duy nhất** của `core/settings.py` cũ còn sống sót sau khi app
socialbot bị gỡ (2026-08-25). Phần còn lại — `load_settings`, `AppSettings`,
`MissingConfigError`, `CONFIG_SCHEMA_VERSION` và cả `core.config_validator` —
đi theo app đó, vì chúng chỉ phục vụ **một** tệp: `data/config.json`, và tệp
đó là cấu hình của socialbot (Meta App ID, Sheet ID, tên cột, chống spam).

## ⭐ Điều đáng ghi lại, vì nó xoá một lớp lỗi chứ không chỉ xoá mã

`/health/ready` trước đây trả **503 khi không đọc được `data/config.json`**.
Nghĩa là một tệp cấu hình **của một app đã đóng băng** quyết định nền tảng có
được coi là sẵn sàng hay không — và trình quản lý dịch vụ khởi động lại tiến
trình theo đúng câu trả lời đó.

Đó không phải chuyện lý thuyết: `CLAUDE.md` mục 1 và `AGENTS.md` mục 5 đều ghi
sự cố thật *"BOM trong config.json → `json.load()` vỡ → `/health/ready` trả 503
trong khi dịch vụ vẫn chạy bình thường"*. Nền tảng nay **không đọc tệp nào cả**
lúc khởi động; hồ sơ môi trường suy ra từ một biến môi trường.

⚠️ Nhưng ĐỪNG đọc điều đó thành *"quy tắc không-BOM đã hết hiệu lực"*. Quy tắc
   vẫn nguyên: `cloudflare/config.yml`, `secrets/app.env` và mọi tệp cấu hình
   khác vẫn phải ghi không BOM, và `tests/test_61_setup_scripts.py` vẫn chốt
   điều đó. Thứ biến mất là **một** đường dính lỗi, không phải cả lớp quy tắc.

## Vì sao nằm ở `platform_core` chứ không ở `server`

`tools/doctor.py` và bộ cài cũng cần biết hồ sơ môi trường, và cả hai đều không
được phép import `server`. Hồ sơ môi trường là chuyện của **nền tảng**, không
phải của tầng HTTP.
"""
from __future__ import annotations

import os
from enum import Enum


class Environment(Enum):
    DEVELOPMENT       = "development"
    LOCAL_SERVER_TEST = "local-server-test"
    PRODUCTION        = "production"


class UnknownEnvironmentError(ValueError):
    """`LTT_ENV` được đặt thành một giá trị không phải hồ sơ nào đã định nghĩa."""


def resolve_environment(env: dict | None = None) -> Environment:
    """Hồ sơ môi trường của tiến trình này.

    Ném khi `LTT_ENV` lạ, thay vì lặng lẽ lùi về `development`. Lùi về
    `development` là chỗ nguy hiểm nhất có thể lùi tới: nó bật tài liệu API
    tương tác, tắt cookie an toàn, và cho phép bịa khoá phiên tạm — cả ba đều
    là thứ không bao giờ được xảy ra vì một lỗi gõ phím trong biến môi trường.
    """
    e = os.environ if env is None else env
    raw = (e.get("LTT_ENV") or "development").strip().lower()
    for member in Environment:
        if member.value == raw:
            return member
    raise UnknownEnvironmentError(
        f"LTT_ENV khong hop le: '{raw}'. Phai la mot trong: "
        f"{', '.join(m.value for m in Environment)}"
    )


__all__ = ["Environment", "UnknownEnvironmentError", "resolve_environment"]
