"""
Linter hop dong app (audit) — chot khong app nao vi pham hop dong CO HOC. Chay lai
moi lan them app: manifest/slug, job_types<->handle/credit_cost, CSRF+auth, guard co-lap.
"""
from __future__ import annotations


def test_khong_co_ERROR_hop_dong():
    from tools.lint_app_contract import lint
    errs = [f for f in lint() if f.level == "ERROR"]
    assert errs == [], "vi pham hop dong app: " + "; ".join(str(e) for e in errs)


def test_moi_app_co_job_types_deu_co_handle():
    """Khong app nao khai job_types ma thieu handle (chan job khong chay duoc)."""
    from tools.lint_app_contract import lint
    bad = [f for f in lint() if "job_types" in f.msg and f.level == "ERROR"]
    assert bad == [], str(bad)


# ── Tang nghiep vu trong hop dong app (audit control-plane 2026-08-06) ───────

def test_linter_flags_a_route_file_that_grew_too_large():
    """Nguong nay la thu duy nhat chan `routes.py` bien thanh noi chua tat ca.

    Khong co no thi khong ai biet luc nao file da qua lon: khong co canh bao,
    va mot file 1.800 dong chi lo ra khi co nguoi phai debug trong do.
    """
    import tools.lint_app_contract as lint

    assert lint.MAX_ROUTES_LINES <= 900
    assert lint.MAX_ROUTES_HANDLERS <= 30


def test_linter_actually_reports_the_oversized_route_files(tmp_path, monkeypatch):
    import tools.lint_app_contract as lint

    fake = tmp_path / "apps" / "phinhto"
    fake.mkdir(parents=True)
    (fake / "manifest.py").write_text(
        'MANIFEST = 1\nslug = "phinhto"\n', encoding="utf-8")
    body = "\n".join(f"@router.get('/r{i}')\ndef h{i}(): pass" for i in range(40))
    (fake / "routes.py").write_text(
        "require_login\nverify_csrf_token\n" + body + "\n" * 950, encoding="utf-8")
    monkeypatch.setattr(lint, "APPS", tmp_path / "apps")

    messages = [f.msg for f in lint.lint() if f.app == "phinhto"]
    assert any("vuot nguong" in m for m in messages), messages


def test_linter_warns_when_a_busy_app_has_no_business_layer(tmp_path, monkeypatch):
    """Nhieu handler ma khong co services/ hay features.py = logic dang nam
    trong route, chi la chua du lon de vuot nguong dong."""
    import tools.lint_app_contract as lint

    fake = tmp_path / "apps" / "khongtang"
    fake.mkdir(parents=True)
    (fake / "manifest.py").write_text(
        'MANIFEST = 1\nslug = "khongtang"\n', encoding="utf-8")
    body = "\n".join(f"@router.get('/r{i}')\ndef h{i}(): pass" for i in range(15))
    (fake / "routes.py").write_text(
        "require_login\nverify_csrf_token\n" + body, encoding="utf-8")
    monkeypatch.setattr(lint, "APPS", tmp_path / "apps")

    messages = [f.msg for f in lint.lint() if f.app == "khongtang"]
    assert any("khong co services/" in m for m in messages), messages

    # Them features.py thi het canh bao — day la loi thoat duoc ghi ro.
    (fake / "features.py").write_text("# quy tac nghiep vu\n", encoding="utf-8")
    messages = [f.msg for f in lint.lint() if f.app == "khongtang"]
    assert not any("khong co services/" in m for m in messages), messages


def test_the_contract_documents_where_business_logic_goes():
    """Linter canh bao, nhung nguoi doc phai biet dat vao dau moi sua duoc."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    text = (root / "platform_core" / "registry.py").read_text(encoding="utf-8")
    assert "services/" in text
    assert "features.py" in text
    assert "CHỈ lo HTTP" in text


def test_linter_kiem_ca_app_da_tach_routes_thanh_package(tmp_path, monkeypatch):
    """Bỏ sót dạng `routes/` thì linter im lặng đúng với hai app LỚN NHẤT ngay
    sau khi chúng được tách — mọi kiểm CSRF/auth/cô-lập biến mất mà không ai
    biết. Đây là cách hỏng do chính việc tách sinh ra.

    Ngưỡng kích thước tính theo TỪNG FILE: tách đúng thì tổng còn to hơn ban
    đầu (mỗi module thêm docstring + import), nên đo tổng sẽ phạt đúng thứ
    mình muốn khuyến khích.
    """
    import tools.lint_app_contract as lint

    app = tmp_path / "apps" / "demo_pkg"
    (app / "routes").mkdir(parents=True)
    (app / "manifest.py").write_text(
        'MANIFEST = App(slug="demo_pkg")\n', encoding="utf-8")
    (app / "routes" / "__init__.py").write_text("from .a import router\n", encoding="utf-8")
    # Một miền hợp lệ: có require_login + CSRF.
    (app / "routes" / "a.py").write_text(
        "from server.auth.session import require_login\n"
        "from server.auth.csrf import verify_csrf_token\n"
        "@router.post('/x')\ndef x(): ...\n", encoding="utf-8")
    monkeypatch.setattr(lint, "APPS", tmp_path / "apps")
    assert [f.msg for f in lint.lint()] == [], "app tách đúng không được báo lỗi"

    # Giờ gỡ require_login khỏi module duy nhất -> linter PHẢI thấy.
    (app / "routes" / "a.py").write_text(
        "from server.auth.csrf import verify_csrf_token\n"
        "@router.post('/x')\ndef x(): ...\n", encoding="utf-8")
    msgs = [f.msg for f in lint.lint()]
    assert any("require_login" in m for m in msgs), (
        f"linter bỏ qua package `routes/` — kiểm an toàn không chạy: {msgs}")


def test_nguong_kich_thuoc_tinh_theo_tung_file_khong_theo_tong(tmp_path, monkeypatch):
    """Chốt riêng vì đây là chỗ dễ viết ngược nhất."""
    import tools.lint_app_contract as lint

    app = tmp_path / "apps" / "demo_pkg2"
    (app / "routes").mkdir(parents=True)
    (app / "manifest.py").write_text('MANIFEST = App(slug="demo_pkg2")\n', encoding="utf-8")
    head = ("from server.auth.session import require_login\n"
            "from server.auth.csrf import verify_csrf_token\n")
    # 4 file × 400 dòng = 1.600 dòng tổng, vượt xa 900 — nhưng mỗi file đều nhỏ.
    for name in "abcd":
        (app / "routes" / f"{name}.py").write_text(
            head + "@router.post('/x')\ndef x(): ...\n" + "# dòng\n" * 400,
            encoding="utf-8")
    monkeypatch.setattr(lint, "APPS", tmp_path / "apps")
    msgs = [f.msg for f in lint.lint()]
    assert not any("vuot nguong" in m for m in msgs), (
        f"đo tổng thay vì đo từng file — phạt đúng thứ nên khuyến khích: {msgs}")
