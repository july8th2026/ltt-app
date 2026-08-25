"""Script cài đặt — chốt những thứ chỉ vỡ trên máy đích, không vỡ ở đây.

Đây là loại lỗi đắt nhất: bạn chỉ biết khi đã ngồi trước máy chủ mới, và
thông báo lỗi thường chẳng liên quan gì tới nguyên nhân thật.
"""
from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SETUP = ROOT / "setup"

SCRIPTS = ["1-kiem-tra-may.ps1", "2-cai-dat.ps1", "3-cloudflare.ps1",
           "4-nghiem-thu.ps1"]


@pytest.mark.parametrize("name", SCRIPTS)
def test_script_exists(name):
    assert (SETUP / name).exists()


@pytest.mark.parametrize("name", SCRIPTS)
def test_script_is_pure_ascii(name):
    """PowerShell 5.1 đọc .ps1 không BOM theo bảng mã ANSI của hệ thống. Một
    dấu tiếng Việt trong chuỗi sẽ bị đọc sai và làm hỏng cả câu lệnh — lỗi báo
    ra ở một dòng chẳng liên quan."""
    raw = (SETUP / name).read_bytes()
    bad = [(i, b) for i, b in enumerate(raw) if b > 127]
    assert bad == [], (
        f"{name} có byte không phải ASCII ở vị trí {[i for i, _ in bad[:5]]}"
    )


@pytest.mark.parametrize("name", SCRIPTS)
def test_script_has_no_bom(name):
    raw = (SETUP / name).read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf", f"{name} có BOM"


def _code_only(name: str) -> str:
    """Bỏ dòng bình luận và khối trợ giúp `<# ... #>`.

    Cần thiết vì các script *có* bình luận dặn "không được dùng Out-File" —
    tìm chuỗi thô sẽ báo nhầm chính lời dặn đó.
    """
    lines = []
    in_block = False
    for line in (SETUP / name).read_text(encoding="ascii").splitlines():
        stripped = line.strip()
        if stripped.startswith("<#"):
            in_block = True
        if in_block:
            if "#>" in stripped:
                in_block = False
            continue
        if stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


@pytest.mark.parametrize("name", SCRIPTS)
def test_script_never_writes_files_with_bom(name):
    """`Out-File -Encoding utf8` và `Set-Content -Encoding utf8` ở PowerShell
    5.1 chèn BOM. BOM trong config.json làm json.load() vỡ và /health/ready trả
    503 trong khi dịch vụ vẫn chạy — chuyện này đã thực sự xảy ra."""
    code = _code_only(name)
    for banned in ("Out-File", "Set-Content"):
        assert banned not in code, (
            f"{name} dùng {banned} — ghi file phải dùng "
            f"[IO.File]::WriteAllText(..., UTF8Encoding($false))"
        )


def test_install_script_writes_without_bom():
    text = (SETUP / "2-cai-dat.ps1").read_text(encoding="ascii")
    assert "UTF8Encoding($false)" in text


def test_cloudflare_script_writes_config_without_bom():
    """cloudflared không đọc được YAML có BOM ở dòng đầu."""
    text = (SETUP / "3-cloudflare.ps1").read_text(encoding="ascii")
    assert "UTF8Encoding($false)" in text


def test_services_rotate_logs_by_size():
    """W2.3: log phai xoay theo KICH THUOC (AppRotateBytes), khong chi khi restart
    (AppRotateFiles mot minh de log phong to vo han giua hai lan restart)."""
    inst = (SETUP / "2-cai-dat.ps1").read_text(encoding="ascii")
    assert inst.count("AppRotateBytes") >= 2      # web + worker
    assert "AppRotateOnline" in inst
    cf = (SETUP / "3-cloudflare.ps1").read_text(encoding="ascii")
    assert "AppRotateBytes" in cf


# ── những thứ script bắt buộc phải làm ─────────────────────────────────────

def test_install_sets_app_directory():
    """AppDirectory sai thì dịch vụ vẫn chạy nhưng mọi trang trả 500, vì một
    số đường dẫn tính theo thư mục làm việc."""
    text = (SETUP / "2-cai-dat.ps1").read_text(encoding="ascii")
    assert "AppDirectory" in text


def test_install_never_overwrites_real_config_or_secrets():
    """Chạy lại script cài mà xoá mất bí mật đang dùng là mất dữ liệu không
    khôi phục được.

    Vế `data/config.json` bỏ đi 2026-08-25 (Q108): tệp đó là cấu hình của app
    socialbot, và bộ cài không còn tạo hay đụng tới nó. Vế `secrets/app.env`
    thì giữ nguyên — đó mới là chỗ chứa khoá phiên và khoá mã hoá token, và
    ghi đè nó là **mất vĩnh viễn** mọi token đã lưu của khách.
    """
    text = (SETUP / "2-cai-dat.ps1").read_text(encoding="ascii")
    assert "if (Test-Path $envFile)" in text


def test_install_copy_fails_fast_instead_of_hanging():
    """Robocopy mặc định là `/R:1000000 /W:30`. Script dừng dịch vụ TRƯỚC khi
    copy, nên một file bị khoá hoặc ACL hỏng sẽ treo vô hạn với production đang
    tắt. Đã thật sự xảy ra ngày 2026-08-05: deploy treo giữa `node_modules`,
    site ngưng 20 phút cho tới khi khôi phục tay từ `app.previous`."""
    code = _code_only("2-cai-dat.ps1")
    assert "robocopy" in code
    assert "/R:2" in code, "thiếu giới hạn retry — treo là mất production vô hạn"
    assert "/W:2" in code, "thiếu giới hạn thời gian chờ giữa các lần retry"


def test_install_does_not_copy_developer_artifacts():
    """Production không chạy Node/Vite/Playwright/pytest. Copy thêm chúng chỉ
    kéo dài cửa sổ downtime (~700 MB) và tăng số file có thể bị khoá."""
    code = _code_only("2-cai-dat.ps1")
    for folder in ("node_modules", ".playwright-cli", ".playwright-mcp",
                   "test-results", "tmp"):
        assert folder in code, f"{folder} phải nằm trong /XD"


def test_install_binds_loopback_only():
    """Nghe 0.0.0.0 là ai cũng gọi thẳng vào app được, bỏ qua Cloudflare."""
    code = _code_only("2-cai-dat.ps1")
    assert "--host 127.0.0.1" in code
    assert "0.0.0.0" not in code


def test_verify_checks_loopback_binding():
    text = (SETUP / "4-nghiem-thu.ps1").read_text(encoding="ascii")
    assert "0.0.0.0" in text, "nghiệm thu phải bắt được trường hợp nghe ra ngoài"


def test_verify_checks_docs_are_closed():
    """/docs liệt kê toàn bộ route và tham số — đồ ăn sẵn cho kẻ tấn công."""
    text = (SETUP / "4-nghiem-thu.ps1").read_text(encoding="ascii")
    assert "/docs" in text


def test_cloudflare_script_documents_the_hard_limits():
    """Ba giới hạn này quyết định cách viết app. Ai chạy script phải đọc được
    ngay, không phải đi tìm trong tài liệu."""
    text = (SETUP / "3-cloudflare.ps1").read_text(encoding="ascii")
    assert "100 MB" in text
    assert "100 giay" in text
    assert "413" in text and "524" in text


def test_cloudflare_script_pauses_for_the_human():
    """Đăng nhập Cloudflare cần trình duyệt — script phải dừng và nói rõ, chứ
    không im lặng treo."""
    text = (SETUP / "3-cloudflare.ps1").read_text(encoding="ascii")
    assert "CAN BAN LAM" in text
    assert "tunnel login" in text


def test_preflight_changes_nothing():
    """Bước kiểm tra máy phải chỉ đọc. Nếu nó sửa gì thì không còn là kiểm tra
    trước khi cài nữa."""
    text = _code_only("1-kiem-tra-may.ps1")
    for banned in ("New-Item", "Remove-Item", "Start-Service", "Stop-Service",
                   "Copy-Item", "Move-Item", "icacls"):
        assert banned not in text, f"bước kiểm tra máy không được gọi {banned}"


def test_verify_changes_nothing():
    text = _code_only("4-nghiem-thu.ps1")
    for banned in ("New-Item", "Remove-Item", "Start-Service", "Stop-Service",
                   "Copy-Item", "Move-Item"):
        assert banned not in text, f"bước nghiệm thu không được gọi {banned}"


# ── template không được phụ thuộc thư mục làm việc ─────────────────────────

def test_template_dir_is_absolute():
    """Đường dẫn template tương đối chỉ chạy đúng khi thư mục làm việc là gốc
    dự án. Chạy uvicorn từ chỗ khác là MỌI trang trả 500, mà thông báo lỗi
    không nói gì về thư mục làm việc — bẫy dễ vấp nhất khi sang máy mới."""
    text = (ROOT / "server" / "templating.py").read_text(encoding="utf-8")
    assert 'directory="server/templates"' not in text
    assert "__file__" in text


def test_templates_resolve_from_any_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import importlib

    import server.templating as t
    importlib.reload(t)
    assert pathlib.Path(t._TEMPLATE_DIR).is_dir()
    assert (pathlib.Path(t._TEMPLATE_DIR) / "base.html").exists()


# ── tài liệu ───────────────────────────────────────────────────────────────

DOC_DIR = ROOT / "docs"


@pytest.mark.parametrize("doc", sorted(p.name for p in DOC_DIR.glob("*.md")))
def test_doc_has_no_invisible_control_characters(doc):
    r"""Ký tự điều khiển lọt vào tài liệu là lỗi vô hình.

    Đã xảy ra thật: một chuỗi Python không phải raw-string chứa
    `.\setup\3-cloudflare` — `\3` là escape bát phân nên thành chr(3). Nhìn
    mắt thường không thấy gì, nhưng người đọc copy đường dẫn về sẽ chạy sai.
    """
    text = (DOC_DIR / doc).read_text(encoding="utf-8")
    bad = [(i, hex(ord(c))) for i, c in enumerate(text)
           if ord(c) < 32 and c not in "\n\r\t"]
    assert bad == [], f"{doc} có ký tự điều khiển tại {bad[:5]}"


@pytest.mark.parametrize("doc", ["00_BAT_DAU_TU_DAY.md", "01_COPY_LEN_SERVER.md",
                                 "02_LENH_CHO_CLAUDE.md", "03_THEM_APP_MOI.md",
                                 "04_CLOUDFLARE_TUNNEL.md"])
def test_setup_guide_exists(doc):
    assert (DOC_DIR / doc).exists()


def test_docs_reference_scripts_that_exist():
    """Tài liệu chỉ tới file không tồn tại là chỉ dẫn sai — người dùng gõ vào
    rồi mới biết."""
    import re

    # Bắt "setup\<ten>.ps1" ở bất kỳ đâu trong tài liệu.
    pattern = re.compile(r"setup[\\/]([\w\-.]+\.ps1)")

    missing = []
    for doc in DOC_DIR.glob("*.md"):
        for name in pattern.findall(doc.read_text(encoding="utf-8")):
            if not (ROOT / "setup" / name).exists():
                missing.append(f"{doc.name} -> setup/{name}")
    assert missing == [], f"tài liệu chỉ tới file không có: {missing}"


def test_claude_md_references_only_real_scripts():
    import re

    pattern = re.compile(r"setup[\\/]([\w\-.]+\.ps1)")
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    names = set(pattern.findall(text))
    assert names, "CLAUDE.md phải chỉ rõ chạy script nào"
    for name in names:
        assert (ROOT / "setup" / name).exists(), f"CLAUDE.md chỉ tới setup/{name}"


def test_claude_md_exists_at_root():
    """Claude chạy trên máy đích đọc file này đầu tiên để biết ngữ cảnh."""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "setup" in text
    assert "UTF8Encoding($false)" in text, "phải dặn cách ghi file không BOM"
