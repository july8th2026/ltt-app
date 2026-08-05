"""Phân tầng: `platform_core` không được phụ thuộc vào `server`.

`platform_core` là nền tảng — worker, script CLI và test đều dùng nó mà không
dựng web. Cho nó import `server` biến sơ đồ tầng thành hình tròn và làm
`platform_core` không dùng được nếu thiếu tầng web.

Audit control-plane 2026-08-06 tìm thấy đúng một vi phạm:
`platform_core/users.py` import `server.auth.password_hashing`. Module đó thuần
stdlib nên đã chuyển hẳn xuống `platform_core/password_hashing.py`. Test này
canh để không có cái thứ hai.
"""
from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMPORT = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][\w.]*)", re.M)


def _modules_imported_by(folder: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in (ROOT / folder).rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        # Bỏ import trong hàm/thử-bắt-lỗi? KHÔNG — import muộn vẫn là phụ thuộc.
        hit = {m.split(".")[0] for m in IMPORT.findall(text)}
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        out[rel] = hit
    return out


def test_platform_core_never_imports_server():
    offenders = {
        name: sorted(mods & {"server"})
        for name, mods in _modules_imported_by("platform_core").items()
        if "server" in mods
    }
    assert offenders == {}, (
        f"platform_core phụ thuộc ngược lên server: {offenders}")


def test_platform_core_never_imports_apps():
    """Nền tảng không được biết app nào tồn tại — registry là đường duy nhất."""
    offenders = {
        name: sorted(mods & {"apps"})
        for name, mods in _modules_imported_by("platform_core").items()
        if "apps" in mods
    }
    assert offenders == {}, f"platform_core biết tới apps: {offenders}"


#: Ngoại lệ ĐƯỢC GHI RÕ, không phải chỗ im lặng cho qua.
#:
#: `taovideo` gọi `upscalevideo.service.submit_upscale_job` cho nút "Nâng cấp
#: 4K" trên video Seedance. Đây là dạng phụ thuộc chéo ít hại nhất: hàm đó tự
#: nộp job qua `submit_with_credit` với `job_type` của chính upscalevideo, nên
#: tiền và hàng đợi vẫn đi đúng đường nền tảng; nó chỉ tránh nhân đôi
#: `build_params`.
#:
#: Vẫn là nợ: gỡ hay đổi tên `upscalevideo` sẽ làm gãy `taovideo`. Đường đúng là
#: ToolSpec handoff như `prompt_ai_ommi` đang dùng. Chưa đổi vì đây là luồng
#: TRẢ TIỀN đang chạy, và đổi nó cần một cổng kiểm riêng chứ không kèm vào một
#: đợt sửa mười hạng mục.
CROSS_APP_ALLOWED = {("taovideo", "upscalevideo")}


def test_apps_never_import_another_app():
    """App gọi thẳng app khác thì gỡ một app là gãy app kia. Trao đổi giữa app
    phải đi qua ToolSpec/job của nền tảng."""
    offenders = {}
    for path in (ROOT / "apps").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        owner = path.relative_to(ROOT / "apps").parts[0]
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"(?:from|import)\s+apps\.([a-z_０-９\w]+)", text):
            other = match.group(1)
            if other != owner and (owner, other) not in CROSS_APP_ALLOWED:
                offenders.setdefault(
                    str(path.relative_to(ROOT)).replace("\\", "/"), set()).add(other)
    assert offenders == {}, f"app import chéo: { {k: sorted(v) for k, v in offenders.items()} }"


def test_apps_do_not_import_private_server_helpers():
    """Dấu gạch dưới nghĩa là 'không phải API công khai'. App phải hỏi qua hợp
    đồng (`server.deps`), không thò tay vào ruột module khác.

    Khớp theo câu IMPORT chứ không theo chuỗi con: `user_is_admin` là biến hợp
    lệ của một app và chứa `_is_admin` bên trong — bản đầu của test này báo đỏ
    giả vì điều đó.
    """
    private_import = re.compile(r"from\s+server[\w.]*\s+import\s+(.+)")
    offenders = {}
    for path in (ROOT / "apps").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for match in private_import.finditer(path.read_text(encoding="utf-8")):
            names = [n.strip() for n in match.group(1).split(",")]
            hidden = [n for n in names if n.startswith("_")]
            if hidden:
                offenders[str(path.relative_to(ROOT)).replace("\\", "/")] = hidden
    assert offenders == {}, f"app import hàm private của server: {offenders}"


def test_moi_module_mien_deu_duoc_import_trong_routes_init():
    """Tách `routes.py` thành package tạo một cách hỏng mới: thêm module miền
    mà quên import vào `__init__` thì handler KHÔNG đăng ký, route biến mất
    lặng lẽ — server vẫn khởi động, chỉ là app thiếu tính năng.

    Không kiểm bằng cách đếm route (số sẽ đổi mỗi lần thêm tính năng), mà kiểm
    đúng điều dễ quên: mọi file `.py` trong package đều được `__init__` nhắc tới.
    """
    packages = [p for p in (ROOT / "apps").glob("*/routes") if p.is_dir()]
    assert packages, "chưa app nào tách routes thành package — test này thành vô nghĩa"
    for pkg in packages:
        init = (pkg / "__init__.py").read_text(encoding="utf-8")
        app = pkg.parent.name
        for module in sorted(pkg.glob("*.py")):
            if module.name == "__init__.py":
                continue
            assert re.search(rf"\b{re.escape(module.stem)}\b", init), (
                f"{app}: {module.name} không được import trong routes/__init__.py — "
                f"handler trong đó sẽ không đăng ký và route sẽ biến mất lặng lẽ")


def test_routes_package_van_xuat_ra_router():
    """Nền tảng chỉ biết một thứ: biến `router`. Tách file không được đổi điều đó."""
    import importlib
    for pkg in [p for p in (ROOT / "apps").glob("*/routes") if p.is_dir()]:
        app = pkg.parent.name
        module = importlib.import_module(f"apps.{app}.routes")
        assert hasattr(module, "router"), f"apps/{app}/routes/ không xuất ra `router`"
        assert module.router.routes, f"apps/{app}/routes/ có router nhưng rỗng route"
