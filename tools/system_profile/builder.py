"""Build the deterministic ``ho_so_he_thong.txt`` repository dossier.

The dossier is a navigation and behavior map, not a copy of source code and
not a live-production status report. It intentionally reads only repository
sources selected by ``tools/system_profile_config.json``. Runtime data,
credentials, browser profiles, logs and temporary artifacts are excluded.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "tools" / "system_profile_config.json"
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "options", "head"})
ENV_RE = re.compile(r"\bLTT_[A-Z][A-Z0-9_]+\b")


def _config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def profile_path() -> Path:
    return ROOT / _config()["output"]


def _excluded(path: Path, config: dict) -> bool:
    relative = path.relative_to(ROOT)
    excluded = set(config["exclude_parts"])
    return any(part in excluded or part.startswith(".backup_")
               for part in relative.parts)


def source_files() -> list[Path]:
    """Return the exact repository files that define dossier freshness."""
    config = _config()
    extensions = set(config["include_extensions"])
    paths: set[Path] = {CONFIG_PATH}
    for relative in (*config["root_sources"], *config["authoritative_docs"]):
        path = ROOT / relative
        if path.is_file():
            paths.add(path)
    for relative in config["source_roots"]:
        base = ROOT / relative
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if (path.is_file() and path.suffix.lower() in extensions
                    and not _excluded(path, config)):
                paths.add(path)
    paths.discard(profile_path())
    return sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix())


def _fingerprint(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _literal(node, default=""):
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return default
    return value


def _parse(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None


def _router_prefix(tree: ast.AST) -> str:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        name = value.func.id if isinstance(value.func, ast.Name) else ""
        if name != "APIRouter":
            continue
        for keyword in value.keywords:
            if keyword.arg == "prefix":
                return str(_literal(keyword.value, ""))
    return ""


def _auth_hint(node: ast.AST) -> str:
    names = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
    attrs = {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)}
    tokens = names | attrs
    if tokens & {"require_admin", "require_operator", "admin_required"}:
        return "admin"
    if tokens & {"require_login", "user_hien_tai", "current_user", "_api_user"}:
        return "login"
    if tokens & {"current_identity_optional", "mo_db_optional"}:
        return "optional"
    return "unspecified"


def _join_route(prefix: str, route: str) -> str:
    if not route:
        return prefix or "/"
    if not prefix:
        return route
    return prefix.rstrip("/") + "/" + route.lstrip("/")


def _app_prefixes() -> dict[str, str]:
    from platform_core.registry import discover

    return {app.slug: app.manifest.route_prefix for app in discover()}


def routes() -> list[dict]:
    """Static HTTP route inventory with an explicitly approximate auth hint."""
    result: list[dict] = []
    prefixes = _app_prefixes()
    candidates = [ROOT / "server" / "app.py"]
    candidates.extend((ROOT / "server" / "routes").rglob("*.py"))
    for slug in prefixes:
        app_dir = ROOT / "apps" / slug
        # App contract usually names routes.py/routes/, but Prompt AI keeps
        # public API handlers in api.py. Scan all Python modules and select by
        # decorators so the dossier reflects behavior, not a naming guess.
        candidates.extend(app_dir.rglob("*.py"))
    for path in sorted(set(candidates)):
        tree = _parse(path)
        if tree is None:
            continue
        relative = path.relative_to(ROOT)
        prefix = _router_prefix(tree)
        owner = "platform"
        if relative.parts[0] == "apps" and len(relative.parts) > 1:
            owner = relative.parts[1]
            prefix = _join_route(prefixes.get(owner, ""), prefix)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(
                        decorator.func, ast.Attribute):
                    continue
                method = decorator.func.attr.lower()
                if method not in HTTP_METHODS:
                    continue
                route = str(_literal(decorator.args[0], "<dynamic>")) if decorator.args else ""
                result.append({
                    "owner": owner,
                    "method": method.upper(),
                    "path": _join_route(prefix, route),
                    "handler": node.name,
                    "auth": _auth_hint(node),
                    "source": f"{relative.as_posix()}:{node.lineno}",
                })
    return sorted(result, key=lambda row: (row["owner"], row["path"], row["method"]))


def database_tables() -> list[dict]:
    result = []
    for base in (ROOT / "platform_core", ROOT / "apps"):
        for path in base.rglob("*.py"):
            tree = _parse(path)
            if tree is None:
                continue
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                for item in node.body:
                    if (isinstance(item, (ast.Assign, ast.AnnAssign))
                            and ((isinstance(item, ast.Assign)
                                  and any(isinstance(target, ast.Name)
                                          and target.id == "__tablename__"
                                          for target in item.targets))
                                 or (isinstance(item, ast.AnnAssign)
                                     and isinstance(item.target, ast.Name)
                                     and item.target.id == "__tablename__"))):
                        table = _literal(item.value, "<dynamic>")
                        result.append({
                            "table": str(table),
                            "model": node.name,
                            "source": f"{path.relative_to(ROOT).as_posix()}:{node.lineno}",
                        })
    return sorted(result, key=lambda row: row["table"])


def migrations() -> list[dict]:
    result = []
    for path in sorted((ROOT / "alembic" / "versions").glob("*.py")):
        tree = _parse(path)
        if tree is None:
            continue
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {
                            "revision", "down_revision"}:
                        values[target.id] = _literal(node.value, "<dynamic>")
        result.append({
            "revision": str(values.get("revision", "?")),
            "down": str(values.get("down_revision", "None")),
            "title": (ast.get_docstring(tree) or "").splitlines()[0] if ast.get_docstring(tree) else "",
            "source": path.relative_to(ROOT).as_posix(),
        })
    return result


def _code_inventory(paths: list[Path]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        groups[relative.split("/", 1)[0]].append(relative)
    return dict(sorted(groups.items()))


def _environment_names(paths: Iterable[Path]) -> list[str]:
    names = set()
    for path in paths:
        if path.suffix.lower() not in {".py", ".ps1", ".md", ".json", ".txt"}:
            continue
        try:
            names.update(ENV_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return sorted(names)


def _frontend_rows() -> list[dict]:
    rows = []
    for package in sorted((ROOT / "frontend").glob("*/package.json")):
        data = json.loads(package.read_text(encoding="utf-8"))
        folder = package.parent
        manifest_path = ROOT / "server" / "static" / folder.name / ".vite" / "manifest.json"
        entry = "missing"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry = str((manifest.get("src/main.tsx") or {}).get("file", "missing"))
        rows.append({
            "name": folder.name,
            "package": data.get("name", folder.name),
            "version": data.get("version", "?"),
            "node": (data.get("engines") or {}).get("node", "?"),
            "src": len(list((folder / "src").rglob("*.*"))),
            "tests": len(list((folder / "tests").rglob("*.test.ts*"))),
            "entry": entry,
        })
    return rows


def _app_rows() -> list[dict]:
    from platform_core.registry import discover

    route_counts = Counter(row["owner"] for row in routes())
    rows = []
    for loaded in discover():
        manifest = loaded.manifest
        folder = ROOT / "apps" / manifest.slug
        files = [path.relative_to(ROOT).as_posix() for path in folder.rglob("*")
                 if path.is_file() and "__pycache__" not in path.parts]
        tools = []
        for tool in manifest.tools:
            inputs = ", ".join(f"{key}:{value.get('type', '?')}"
                               for key, value in tool.params_schema.items())
            outputs = ", ".join(f"{key}:{value}" for key, value in tool.returns.items())
            tools.append({
                "name": tool.name,
                "job": tool.job_type,
                "visible": bool(tool.customer_visible),
                "inputs": inputs,
                "outputs": outputs,
            })
        credit_owner = "none"
        if manifest.credit_cost is not None:
            credit_owner = f"{manifest.credit_cost.__module__}.{manifest.credit_cost.__name__}"
        rows.append({
            "slug": manifest.slug,
            "name": manifest.display_name,
            "prefix": manifest.route_prefix,
            "surface": manifest.surface,
            "lifecycle": manifest.lifecycle,
            "enabled": manifest.enabled,
            "public": manifest.public,
            "parent": manifest.catalog_parent or "-",
            "capabilities": tuple(manifest.capabilities),
            "requires": tuple(manifest.requires),
            "jobs": tuple(manifest.job_types),
            "vram": dict(manifest.gpu_vram_mb or {}),
            "credit": credit_owner,
            "table_prefix": manifest.table_prefix or "-",
            "routes": route_counts[manifest.slug],
            "tools": tools,
            "files": sorted(files),
            "error": loaded.error or "-",
        })
    return rows


def _line(lines: list[str], value: str = "") -> None:
    lines.append(value.rstrip())


def build_profile() -> str:
    config = _config()
    paths = source_files()
    route_rows = routes()
    table_rows = database_tables()
    migration_rows = migrations()
    app_rows = _app_rows()
    inventory = _code_inventory(paths)
    suffix_counts = Counter(path.suffix.lower() or "<none>" for path in paths)
    lines: list[str] = []

    _line(lines, "HỒ SƠ HỆ THỐNG LTTSTUDIOSAPP")
    _line(lines, "=" * 78)
    _line(lines, f"Schema hồ sơ : {config['schema']}")
    _line(lines, f"Phiên bản app : {_app_version()}")
    _line(lines, f"Fingerprint   : sha256:{_fingerprint(paths)}")
    _line(lines, f"Nguồn đã quét : {len(paths)} file repository; không đọc runtime/secrets/log")
    _line(lines)
    _line(lines, "MỤC ĐÍCH VÀ CÁCH DÙNG")
    _line(lines, "- Đây là bản đồ điều hướng và hành vi được sinh từ code để AI/người mới")
    _line(lines, "  hiểu hệ thống nhanh; KHÔNG phải bản sao source và KHÔNG phải health live.")
    _line(lines, "- Khi cần sửa, phải mở file nguồn được chỉ ra; không suy diễn từ hồ sơ.")
    _line(lines, "- Thứ tự chân lý: QUYET_DINH_NEN_TANG.md → code/test → kế hoạch → hồ sơ.")
    _line(lines, "- Tạo lại: python tools/build_system_profile.py")
    _line(lines, "- Kiểm tra: python tools/build_system_profile.py --check")
    _line(lines)

    _line(lines, "1. NHẬN DIỆN VÀ BẤT BIẾN")
    _line(lines, "- Sản phẩm: SaaS đa người dùng bán công cụ AI theo credit.")
    _line(lines, "- Control plane: app.lttstudios.com; app dùng route path /<slug>.")
    _line(lines, "- Web/worker là tiến trình riêng; PostgreSQL là nguồn chân lý job/credit.")
    _line(lines, "- Job trả phí: quote → approve → hold → queue → settle/refund.")
    _line(lines, "- Job dài chạy trong worker; không chạy đồng bộ trong HTTP request.")
    _line(lines, "- D:\\BOT GEMINI chỉ đọc; không truy cập cây đó trong runtime.")
    _line(lines, "- Hai cây mã nguồn độc lập; cấm phụ thuộc/import chéo.")
    _line(lines, "- Production code C:\\LTTPlatform\\app; data/secrets nằm ngoài release.")
    _line(lines, "- Cổng nền tảng 8100; cổng 8000 thuộc hệ thống khác.")
    _line(lines, "- Secret chỉ qua biến môi trường/thư mục bảo vệ; hồ sơ chỉ ghi TÊN biến.")
    _line(lines)

    _line(lines, "2. LUỒNG VẬN HÀNH CỐT LÕI")
    _line(lines, "Browser → Cloudflare Tunnel → FastAPI/Jinja/React → PostgreSQL")
    _line(lines, "                                     ↓")
    _line(lines, "                              Job queue + credit hold")
    _line(lines, "                                     ↓")
    _line(lines, "                         Worker → API/FFmpeg/GPU/storage")
    _line(lines, "                                     ↓")
    _line(lines, "                       Job event/artifact → UI → settle/refund")
    _line(lines, "Các lớp chính:")
    _line(lines, "- platform_core/: auth-domain, registry, DB, jobs, credit, GPU, storage,")
    _line(lines, "  provider, upload lifecycle, observability và Agent runtime dùng chung.")
    _line(lines, "- server/: HTTP/control plane, middleware, auth, template và admin.")
    _line(lines, "- apps/<slug>/: manifest, HTTP adapter, service/features, jobs và bảng riêng.")
    _line(lines, "- core/: social publishing legacy/frozen và worker compatibility còn được dùng.")
    _line(lines, "- frontend/: ba workspace React/Vite; production chỉ phục vụ bundle đã build.")
    _line(lines)

    _line(lines, f"3. DANH MỤC APP ({len(app_rows)})")
    for app in app_rows:
        _line(lines, f"[{app['slug']}] {app['name']}")
        _line(lines, f"  URL={app['prefix']} | surface={app['surface']} | lifecycle={app['lifecycle']}")
        _line(lines, f"  enabled={app['enabled']} | public={app['public']} | parent={app['parent']}")
        _line(lines, f"  requires={','.join(app['requires']) or '-'} | capabilities={','.join(app['capabilities']) or '-'}")
        _line(lines, f"  HTTP routes={app['routes']} | table_prefix={app['table_prefix']} | manifest_error={app['error']}")
        _line(lines, f"  credit_cost={app['credit']}")
        _line(lines, f"  job_types={', '.join(app['jobs']) or '-'}")
        if app["vram"]:
            _line(lines, "  gpu_vram_mb=" + ", ".join(
                f"{key}:{value}" for key, value in sorted(app["vram"].items())))
        _line(lines, f"  Agent tools ({len(app['tools'])}):")
        if app["tools"]:
            for tool in app["tools"]:
                _line(lines, f"    - {tool['name']} → {tool['job']} | customer_visible={tool['visible']}")
                _line(lines, f"      inputs: {tool['inputs'] or '-'}")
                _line(lines, f"      outputs: {tool['outputs'] or '-'}")
        else:
            _line(lines, "    - none")
        _line(lines, "  File map:")
        for file in app["files"]:
            _line(lines, f"    - {file}")
        _line(lines)

    _line(lines, f"4. HTTP ROUTE INVENTORY ({len(route_rows)})")
    _line(lines, "Auth là gợi ý AST, không thay security review hay browser test.")
    for row in route_rows:
        _line(lines, f"- [{row['owner']}] {row['method']:<6} {row['path']} → "
                     f"{row['handler']} | auth~{row['auth']} | {row['source']}")
    _line(lines)

    _line(lines, f"5. DATA MODEL ({len(table_rows)} bảng)")
    for row in table_rows:
        _line(lines, f"- {row['table']} → {row['model']} | {row['source']}")
    _line(lines)
    _line(lines, f"6. ALEMBIC MIGRATIONS ({len(migration_rows)})")
    for row in migration_rows:
        _line(lines, f"- {row['revision']} ← {row['down']} | {row['title']} | {row['source']}")
    _line(lines)

    frontends = _frontend_rows()
    _line(lines, f"7. FRONTEND WORKSPACES ({len(frontends)})")
    for row in frontends:
        _line(lines, f"- {row['name']}: package={row['package']}@{row['version']}, "
                     f"Node={row['node']}, src={row['src']}, tests={row['tests']}, bundle={row['entry']}")
    _line(lines, "- Sau mọi thay đổi GUI: Playwright render thật + console + failed network + mobile.")
    _line(lines)

    _line(lines, "8. STORAGE, LOG, RETENTION VÀ BẢO MẬT")
    _line(lines, "- Upload trả phí: staging owner/app, TTL 1h, promote sau hold, cleanup terminal.")
    _line(lines, "- Editor draft: attachment owner/app/project, TTL 30 ngày, touch khi mở.")
    _line(lines, "- Job metadata/timeline customer: 365 ngày; debug event nội bộ: 30 ngày.")
    _line(lines, "- CreditEntry append-only; không purge theo vòng đời Job.")
    _line(lines, "- Customer chỉ xem log đã làm sạch; raw kỹ thuật chỉ admin/support.")
    _line(lines, "- Local/R2 storage qua platform_core.storage; data path qua runtime_paths.")
    _line(lines, "- Tài liệu chi tiết: docs/DATA_RETENTION_POLICY.md và SECURITY_CHECKLIST.md.")
    _line(lines)

    env_names = _environment_names(paths)
    _line(lines, f"9. BIẾN MÔI TRƯỜNG ĐƯỢC THAM CHIẾU ({len(env_names)} tên; KHÔNG có giá trị)")
    for name in env_names:
        _line(lines, f"- {name}")
    _line(lines)

    tests = sorted(path.relative_to(ROOT).as_posix()
                   for path in (ROOT / "tests").glob("test_*.py"))
    _line(lines, f"10. QUALITY GATES ({len(tests)} file pytest + {len(frontends)} frontend)")
    _line(lines, "- Lệnh duy nhất trước khi báo xong: python tools/gate.py")
    _line(lines, "- Quick loop: python tools/gate.py --quick")
    _line(lines, "- Gate: secret scan, app contract, undefined names, silent-except,")
    _line(lines, "  i18n growth, system-profile freshness, frontend tests và pytest.")
    _line(lines, "- GUI không được coi là PASS nếu chưa kiểm Playwright trên render thật.")
    _line(lines, "Test inventory:")
    for test in tests:
        _line(lines, f"- {test}")
    _line(lines)

    _line(lines, "11. DEPLOY / ROLLBACK")
    _line(lines, "- Build: python tools/build_release.py --output <folder>")
    _line(lines, "- Update: deploy/windows/update.ps1 -SourceZip <release.zip>")
    _line(lines, "- Update bắt buộc backup → stop → rotate → extract → deps → migration → health.")
    _line(lines, "- Rollback code: deploy/windows/rollback.ps1; data không tự downgrade.")
    _line(lines, "- Health: /health/live và /health/ready; production phải database=ok.")
    _line(lines, "- Source of truth vận hành: docs/01_COPY_LEN_SERVER.md.")
    _line(lines)

    _line(lines, "12. TÀI LIỆU PHẢI ĐỌC")
    for doc in config["authoritative_docs"]:
        _line(lines, f"- {doc}")
    _line(lines, "- docs/NHAT_KY.md (hai mục mới nhất; lịch sử thực thi, không phải kiến trúc)")
    _line(lines)

    _line(lines, f"13. CHỈ MỤC SOURCE ({len(paths)} file)")
    _line(lines, "Phân bố extension: " + ", ".join(
        f"{suffix}:{count}" for suffix, count in sorted(suffix_counts.items())))
    for group, files in inventory.items():
        _line(lines, f"[{group}] ({len(files)})")
        for file in files:
            _line(lines, f"- {file}")
        _line(lines)

    _line(lines, "14. GIỚI HẠN CỦA HỒ SƠ")
    _line(lines, "- Không chứa giá trị secret, user data, job payload, log hay browser state.")
    _line(lines, "- Không xác nhận provider/GPU/Cloudflare đang live; dùng doctor/health/browser.")
    _line(lines, "- Auth hint của route là phép đọc tĩnh; middleware/dependency runtime mới quyết định.")
    _line(lines, "- Fingerprint đổi nghĩa là phải tạo lại hồ sơ và review diff.")
    _line(lines)
    return "\n".join(lines).rstrip() + "\n"


def _app_version() -> str:
    try:
        tree = _parse(ROOT / "version.py")
        if tree is not None:
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                            return str(_literal(node.value, "unknown"))
    except OSError:
        pass
    return "unknown"
