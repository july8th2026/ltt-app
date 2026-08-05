"""
frontend_bundle.py — tra đường dẫn bundle React đã build, dùng chung cho mọi app.

App nào có giao diện React đều cần đúng ba việc: tìm gốc repo, đọc manifest của
Vite, đổi tên file băm thành URL `/static/...`. Trước 2026-08-06 ba app chép
nguyên đoạn đó, và cả ba đều neo gốc repo bằng `Path(__file__).parents[2]`.

Đếm cấp thư mục là sai ngay khi file đổi chỗ. Lúc tách `routes.py` của một app
thành package, file sâu thêm một cấp nên `parents[2]` trỏ vào `apps/`; manifest
không đọc được, `_workspace_assets()` trả rỗng, và trang **vẫn trả 200** với
một vỏ trống. Hỏng lặng lẽ, không log, không exception.

Nên ở đây neo gốc repo bằng TÊN thư mục (`server/static` tồn tại), và app chỉ
khai tên thư mục bundle của mình. Đây là hạ tầng, không phải nghiệp vụ của app
nào — nền tảng không cần biết app tên gì.
"""
from __future__ import annotations

import json
from pathlib import Path

# Đi ngược lên tới thư mục đầu tiên có `server/static`. Không phụ thuộc độ sâu
# của file gọi, nên di chuyển module không làm gãy đường dẫn.
REPO_ROOT = next(p for p in Path(__file__).resolve().parents
                 if (p / "server" / "static").is_dir())

# Vite luôn khai entry theo đường dẫn nguồn; mọi bundle của nền tảng dùng chung
# một quy ước để không phải truyền thêm tham số.
ENTRY = "src/main.tsx"


def manifest_path(bundle: str) -> Path:
    """Đường dẫn manifest của Vite cho `bundle` (tên thư mục dưới static/)."""
    return REPO_ROOT / "server" / "static" / bundle / ".vite" / "manifest.json"


def bundle_assets(bundle: str) -> tuple[list[str], list[str]]:
    """Trả (danh sách JS, danh sách CSS) đã có tiền tố `/static/<bundle>/`.

    Thiếu hoặc hỏng manifest thì trả hai list rỗng — caller quyết định hiển thị
    gì. KHÔNG tự dựng giao diện tạm: template nói rõ là chưa có bundle và trỏ
    người dùng về trang chạy được, thay vì hiện vỏ trống trông như hỏng.
    """
    try:
        manifest = json.loads(manifest_path(bundle).read_text(encoding="utf-8"))
        entry = manifest[ENTRY]
        return ([f"/static/{bundle}/{entry['file']}"],
                [f"/static/{bundle}/{item}" for item in entry.get("css", [])])
    except (OSError, KeyError, ValueError):
        return [], []
