"""
registry.py — hợp đồng giữa nền tảng và từng app. Đây là file quan trọng nhất.

Nền tảng KHÔNG được biết tên app nào tồn tại. Nó quét `apps/*/manifest.py`,
đọc `MANIFEST`, rồi tự dựng trang chủ, gắn route, và phân job cho worker.

Vì sao phải làm vậy: nếu tên app nằm rải rác trong code nền tảng (trang chủ,
sidebar, bảng giá, phân job) thì thêm app thứ 10 là sửa 10 chỗ và chắc chắn
quên một chỗ. Với registry, thêm app = thêm một folder.

Thêm app mới cần đúng 3 việc:
    1. tạo `apps/<slug>/manifest.py` có biến MANIFEST
    2. tạo `apps/<slug>/routes.py` có biến `router` (APIRouter)
    3. xong. Không sửa file nào của nền tảng.

Xem `apps/demo/` làm mẫu tối thiểu và `docs/03_THEM_APP_MOI.md` để làm theo.
"""
from __future__ import annotations

import importlib
import pathlib
from dataclasses import dataclass, field
from typing import Callable, Optional

APPS_DIR = pathlib.Path(__file__).resolve().parent.parent / "apps"


@dataclass(frozen=True)
class NavEntry:
    """Một dòng trong sidebar của app."""
    label: str
    path: str
    icon: str = ""
    nav_key: str = ""          # để template biết dòng nào đang active
    built: bool = True         # False -> hiện nhãn "đang xây", không ẩn đi


@dataclass(frozen=True)
class AppManifest:
    """Bản khai của một app. Nền tảng chỉ đọc, không sửa.

    `slug` là khoá duy nhất và cũng là tên folder. `route_prefix` là đường dẫn
    dưới app.lttstudios.com — mỗi app một prefix riêng để không bao giờ đụng
    nhau.
    """

    slug: str
    display_name: str
    route_prefix: str
    summary: str = ""
    icon: str = "📦"
    accent: str = "#1565C0"

    # Sidebar. App đơn giản để trống, nền tảng tự tạo 1 dòng từ route_prefix.
    nav: tuple = ()

    # Loại job app này sinh ra, ví dụ ("seedance.t2v", "seedance.i2v").
    # Worker khai báo mình làm được loại nào; hàng đợi khớp theo đây.
    job_types: tuple = ()

    # Worker cần năng lực gì để chạy job của app này:
    #   "api"     - chỉ gọi API bên ngoài, chạy ở đâu cũng được
    #   "ffmpeg"  - cần ffmpeg cục bộ
    #   "gpu"     - cần VRAM
    #   "browser" - cần trình duyệt + IP dân dụng (bot đăng bài)
    # Phải có annotation kiểu, nếu không dataclass coi đây là biến lớp chứ
    # không phải field và constructor sẽ từ chối tham số `requires=`.
    requires: tuple = ("api",)

    # Hàm tính credit. Là HÀM chứ không phải số, vì giá phụ thuộc tham số
    # (Seedance tính theo giây video × độ phân giải, không tính theo lần gọi).
    # Nhận dict tham số job, trả về số credit. None = app chưa thu phí.
    credit_cost: Optional[Callable[[dict], int]] = None

    # True khi app đã chạy được thật. False -> trang chủ hiện nhãn "đang xây"
    # thay vì để người dùng bấm vào rồi gặp lỗi.
    enabled: bool = True

    # Ghi chú nội bộ, hiện trên trang chủ cho admin.
    notes: str = ""

    def nav_entries(self) -> list:
        """Sidebar của app. Không khai gì thì tạo mặc định 1 dòng."""
        if self.nav:
            return list(self.nav)
        return [NavEntry(label=self.display_name, path=self.route_prefix,
                         icon=self.icon, nav_key=self.slug)]


@dataclass
class LoadedApp:
    """Manifest + router đã import xong."""
    manifest: AppManifest
    router: object = None
    error: str = ""

    @property
    def slug(self) -> str:
        return self.manifest.slug


class RegistryError(Exception):
    pass


def _validate(manifest: AppManifest, seen_slugs: set, seen_prefixes: set) -> None:
    """Chặn sớm những sai sót âm thầm gây khó hiểu về sau."""
    if not manifest.slug or not manifest.slug.replace("_", "").isalnum():
        raise RegistryError(
            f"slug không hợp lệ: {manifest.slug!r} — chỉ chữ, số và gạch dưới")
    if manifest.slug in seen_slugs:
        raise RegistryError(f"slug trùng: {manifest.slug!r}")
    if not manifest.route_prefix.startswith("/"):
        raise RegistryError(
            f"[{manifest.slug}] route_prefix phải bắt đầu bằng '/': "
            f"{manifest.route_prefix!r}")
    if manifest.route_prefix.rstrip("/") in seen_prefixes:
        # Hai app cùng prefix thì app nạp sau bị app trước che mất, và
        # FastAPI không báo gì cả — rất khó truy.
        raise RegistryError(
            f"[{manifest.slug}] route_prefix trùng: {manifest.route_prefix!r}")
    if manifest.job_types and manifest.credit_cost is None:
        # Không phải lỗi chặn, nhưng app sinh job mà không tính tiền thì
        # thường là quên, và với giá API thật thì quên là mất tiền.
        pass


def discover(apps_dir: pathlib.Path = APPS_DIR) -> list:
    """Quét apps/*/manifest.py. Trả về danh sách LoadedApp đã sắp xếp.

    Một app lỗi KHÔNG làm sập nền tảng — nó được ghi lại kèm lý do và hiện
    trên trang chủ. Đó là điểm khác biệt quan trọng: bạn vẫn vào được hệ thống
    để xem app nào lỗi, thay vì cả site 500.
    """
    if not apps_dir.exists():
        return []

    loaded: list = []
    seen_slugs: set = set()
    seen_prefixes: set = set()

    for entry in sorted(apps_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith(("_", ".")):
            continue
        if not (entry / "manifest.py").exists():
            continue

        try:
            mod = importlib.import_module(f"apps.{entry.name}.manifest")
            manifest = getattr(mod, "MANIFEST")
            if not isinstance(manifest, AppManifest):
                raise RegistryError("MANIFEST không phải AppManifest")
            _validate(manifest, seen_slugs, seen_prefixes)
        except Exception as exc:
            loaded.append(LoadedApp(
                manifest=AppManifest(
                    slug=entry.name, display_name=entry.name,
                    route_prefix=f"/{entry.name}", enabled=False,
                ),
                error=f"{type(exc).__name__}: {exc}",
            ))
            continue

        seen_slugs.add(manifest.slug)
        seen_prefixes.add(manifest.route_prefix.rstrip("/"))

        router = None
        router_error = ""
        try:
            rmod = importlib.import_module(f"apps.{entry.name}.routes")
            router = getattr(rmod, "router", None)
            if router is None:
                router_error = "routes.py không có biến `router`"
        except ModuleNotFoundError:
            # App chỉ có job, không có UI riêng — hợp lệ.
            pass
        except Exception as exc:
            router_error = f"{type(exc).__name__}: {exc}"

        loaded.append(LoadedApp(manifest=manifest, router=router,
                                error=router_error))

    return loaded


def mount_all(app, apps: Optional[list] = None) -> list:
    """Gắn router của mọi app vào FastAPI. Trả về danh sách đã nạp."""
    apps = discover() if apps is None else apps
    for item in apps:
        if item.router is not None and not item.error:
            app.include_router(item.router, prefix=item.manifest.route_prefix)
    return apps


def job_type_owners(apps: Optional[list] = None) -> dict:
    """job_type -> slug. Dùng để phân job và tra giá credit."""
    apps = discover() if apps is None else apps
    out: dict = {}
    for item in apps:
        for jt in item.manifest.job_types:
            out[jt] = item.manifest.slug
    return out


def credit_for(job_type: str, params: dict, apps: Optional[list] = None) -> int:
    """Credit cần cho một job. Raise nếu job_type không ai nhận.

    Cố tình raise thay vì trả 0: một job không tính được giá mà vẫn chạy là
    một job miễn phí ngoài ý muốn, và với $0,68/giây thì đó là mất tiền thật.
    """
    apps = discover() if apps is None else apps
    for item in apps:
        if job_type in item.manifest.job_types:
            fn = item.manifest.credit_cost
            if fn is None:
                raise RegistryError(
                    f"[{item.slug}] job_type {job_type!r} chưa khai credit_cost "
                    f"— từ chối chạy để không phát sinh chi phí không kiểm soát")
            return int(fn(params))
    raise RegistryError(f"không app nào nhận job_type {job_type!r}")
