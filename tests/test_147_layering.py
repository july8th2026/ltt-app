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
#: ── Auto Scan Video ────────────────────────────────────────────────────────
#:
#: Sáu cạnh, nhưng **hai loại khác hẳn nhau**. Gộp chúng làm một dòng ngoại lệ
#: sẽ giấu mất điều đáng biết: ba cạnh đầu không phải nợ, ba cạnh sau thì có.
#:
#: ⭐ LOẠI A — `asv_media` · `asv_gpu` · `asv_voice` → `auto_scan_video`
#:
#:    Ba cái này **không phải app độc lập**. Chúng khai `surface="runtime"` +
#:    `catalog_parent="auto_scan_video"`, không có thẻ catalog, không có mục
#:    nav, không bán riêng. Chúng tồn tại vì một lý do kỹ thuật duy nhất: quyền
#:    nhặt job lọc theo **APP** chứ không theo `job_type`
#:    (`platform_core/jobs.py:158-164`), nên một app khai đủ cả bốn năng lực sẽ
#:    chỉ chạy được trên worker có đủ cả bốn — tức là không bao giờ.
#:
#:    ⇒ Câu "gỡ một app là gãy app kia" **không áp dụng**: gỡ `auto_scan_video`
#:      không làm gãy một sản phẩm khác, nó gỡ chính sản phẩm này. Đây là import
#:      TRONG một sản phẩm, chỉ trông giống import chéo vì hợp đồng app buộc mỗi
#:      làn worker phải là một thư mục riêng.
#:
#: ⚠️ LOẠI B — `auto_scan_video` → `ltt_llm` · `autosubvideo` · `ltt_voice`
#:
#:    Đây MỚI là nợ, và đúng cùng loại với `taovideo → upscalevideo` ở trên:
#:    đổi tên hay gỡ một trong ba app kia sẽ làm gãy Auto Scan Video.
#:
#:      dich_thuat.py        -> ltt_llm       điều phối model dịch
#:      giai_doan_chep_loi.py-> autosubvideo  bộ chạy ASR
#:      giong_noi.py         -> ltt_voice     chuẩn hoá văn bản + TTS
#:
#:    Nhưng nó **khác** `taovideo → upscalevideo` ở một điểm quyết định đường
#:    sửa: ba lời gọi này phần lớn là **hàm thuần**, không phải nộp job. Ví dụ
#:    `ltt_voice.text_pipeline.chuan_hoa` là chuẩn hoá tiếng Việt — một mối lo
#:    dùng chung đã bị đặt nhầm chỗ, nó thuộc `platform_core` chứ không thuộc
#:    một app. Nên đường ra đúng ở đây **không phải** ToolSpec handoff (handoff
#:    một hàm thuần chỉ thêm một vòng hàng đợi cho một phép biến đổi chuỗi) mà
#:    là **nâng phần dùng chung lên `platform_core`**.
#:
#:    Chưa làm trong pha 14 vì việc đó sửa `platform_core/` VÀ ba app **đang
#:    phục vụ khách trả tiền** của lane khác — đúng thứ `CLAUDE.md` bảo dừng
#:    lại và nói rõ thay vì kèm vào một đợt mười hạng mục. Ghi ở RISK-14-01.
CROSS_APP_ALLOWED = {
    ("taovideo", "upscalevideo"),
    # loại A — cùng một sản phẩm, tách vì quyền nhặt job lọc theo app
    ("asv_media", "auto_scan_video"),
    ("asv_gpu", "auto_scan_video"),
    ("asv_voice", "auto_scan_video"),
    # loại B — nợ thật, đường ra là nâng phần dùng chung lên platform_core
    ("auto_scan_video", "ltt_llm"),
    ("auto_scan_video", "autosubvideo"),
    ("auto_scan_video", "ltt_voice"),
}


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


def test_nen_tang_va_app_khong_phu_thuoc_core_legacy():
    """`core/` **đã bị xoá hẳn 2026-08-25** (Q108). Đừng dựng lại nó.

    Lịch sử, vì nó giải thích vì sao phép kiểm này vẫn còn giá trị sau khi thứ
    nó canh đã biến mất: `core/` là 15.046 dòng thừa kế từ thời sản phẩm còn là
    bot FB/TikTok. Trước 2026-08-06 **mọi** app đều dính nó — không phải vì
    chúng cần, mà vì `platform_core/storage.py` gọi `core.runtime_paths`, kéo cả
    cây theo. Một sợi dây duy nhất khiến bản đồ phụ thuộc nói dối: nhìn vào
    tưởng `core/` là hạ tầng chung, thực ra 99,4% của nó không phục vụ app nào
    đang bán (xem docs/APP_AUDIT/control-plane/2026-08-06/04_BAN_DO_CORE.md).

    H22 cắt sợi dây đó; Q108 xoá luôn phần còn lại. Phép kiểm giữ nguyên vì nó
    nay canh một điều khác và vẫn đáng canh: **thứ nhiều nơi cần là hạ tầng, và
    hạ tầng thuộc về `platform_core/`** — đừng tạo một `core/` thứ hai dưới tên
    khác.
    """
    offenders = {}
    for area in ("apps", "platform_core"):
        for path in (ROOT / area).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            hits = re.findall(r"^\s*(?:from|import)\s+(core(?:\.[\w.]+)?)", text, re.M)
            if hits:
                offenders[path.relative_to(ROOT).as_posix()] = sorted(set(hits))
    assert offenders == {}, (
        f"nền tảng/app đang phụ thuộc core/ legacy: {offenders} — "
        f"thứ dùng chung thì đặt ở platform_core/")
