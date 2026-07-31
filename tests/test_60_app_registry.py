"""Hợp đồng app registry — thứ quyết định chi phí thêm app thứ 10.

Nếu hợp đồng này lỏng thì mỗi app mới lại phải sửa nền tảng một chút, và
đến app thứ năm thì không ai nhớ phải sửa những đâu. Các test dưới đây chốt
đúng những chỗ dễ trượt nhất.
"""
from __future__ import annotations

import pathlib

import pytest

from platform_core.registry import (
    AppManifest,
    NavEntry,
    RegistryError,
    credit_for,
    discover,
    job_type_owners,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent


# ── quét app ───────────────────────────────────────────────────────────────

def test_discovers_every_app_folder():
    slugs = {a.slug for a in discover()}
    assert "demo" in slugs
    assert "socialbot" in slugs


def test_no_app_fails_to_load():
    broken = {a.slug: a.error for a in discover() if a.error}
    assert broken == {}, f"app nạp lỗi: {broken}"


def test_every_apps_subfolder_has_a_manifest():
    """Một folder trong apps/ mà thiếu manifest.py sẽ bị bỏ qua HOÀN TOÀN im
    lặng — code có đó, route không bao giờ chạy, và rất khó nhận ra."""
    missing = [
        d.name for d in (ROOT / "apps").iterdir()
        if d.is_dir() and not d.name.startswith(("_", "."))
        and not (d / "manifest.py").exists()
    ]
    assert missing == [], f"thiếu manifest.py: {missing}"


# ── những va chạm im lặng ──────────────────────────────────────────────────

def test_route_prefixes_are_unique():
    """Hai app cùng prefix thì app nạp sau bị che mất và FastAPI không báo gì."""
    prefixes = [a.manifest.route_prefix.rstrip("/") for a in discover()]
    dupes = {p for p in prefixes if prefixes.count(p) > 1}
    assert not dupes, f"route_prefix trùng: {dupes}"


def test_slugs_are_unique():
    slugs = [a.slug for a in discover()]
    assert len(slugs) == len(set(slugs))


def test_job_types_are_unique_across_apps():
    """Hai app cùng nhận một job_type thì job chạy bằng handler nào là ngẫu
    nhiên theo thứ tự quét thư mục."""
    owners: dict = {}
    for a in discover():
        for jt in a.manifest.job_types:
            assert jt not in owners, \
                f"job_type {jt!r} bị cả {owners[jt]} và {a.slug} nhận"
            owners[jt] = a.slug
    assert job_type_owners() == owners


def test_registry_rejects_duplicate_prefix():
    from platform_core.registry import _validate
    m = AppManifest(slug="x", display_name="X", route_prefix="/demo")
    with pytest.raises(RegistryError, match="route_prefix trùng"):
        _validate(m, seen_slugs=set(), seen_prefixes={"/demo"})


def test_registry_rejects_relative_prefix():
    from platform_core.registry import _validate
    m = AppManifest(slug="x", display_name="X", route_prefix="demo")
    with pytest.raises(RegistryError, match="phải bắt đầu bằng"):
        _validate(m, seen_slugs=set(), seen_prefixes=set())


def test_validate_tu_choi_job_types_thieu_credit_cost():
    """W1.6: app sinh job mà thiếu credit_cost bị chặn NGAY lúc discover (fail
    som), không đợi tới lúc submit mới vỡ."""
    from platform_core.registry import _validate
    m = AppManifest(slug="x", display_name="X", route_prefix="/x",
                    job_types=("x.do",), credit_cost=None)
    with pytest.raises(RegistryError, match="credit_cost"):
        _validate(m, seen_slugs=set(), seen_prefixes=set(), seen_job_types=set())


def test_validate_tu_choi_job_type_trung():
    """W1.6: job_type trùng giữa hai app bị chặn ngay (worker phân job theo
    job_type — trùng thì quyết toán nhầm giá)."""
    from platform_core.registry import _validate
    m = AppManifest(slug="x", display_name="X", route_prefix="/x",
                    job_types=("dup.jt",), credit_cost=lambda p: 1)
    with pytest.raises(RegistryError, match="job_type trùng"):
        _validate(m, seen_slugs=set(), seen_prefixes=set(),
                  seen_job_types={"dup.jt"})


# ── credit: chỗ mất tiền ───────────────────────────────────────────────────

def test_credit_is_computed_from_params_not_fixed():
    """Giá phải là hàm của tham số. Seedance tính theo giây video × độ phân
    giải; một hằng số sẽ tính sai ngay từ job đầu tiên."""
    small = credit_for("demo.reverse", {"text": "x" * 50})
    big = credit_for("demo.reverse", {"text": "x" * 5000})
    assert big > small


def test_unknown_job_type_is_refused_not_free():
    """Job không tra được giá phải bị TỪ CHỐI. Trả 0 nghĩa là chạy miễn phí
    ngoài ý muốn — với API tính theo giây thì đó là mất tiền thật."""
    with pytest.raises(RegistryError, match="không app nào nhận"):
        credit_for("khong.ton.tai", {})


def test_job_type_without_price_is_refused():
    """App khai job_types nhưng quên credit_cost cũng phải bị chặn."""
    apps = [type("L", (), {
        "manifest": AppManifest(slug="p", display_name="P", route_prefix="/p",
                                job_types=("p.run",), credit_cost=None),
        "slug": "p", "router": None, "error": "",
    })()]
    with pytest.raises(RegistryError, match="chưa khai credit_cost"):
        credit_for("p.run", {}, apps=apps)


# ── điều hướng ─────────────────────────────────────────────────────────────

def test_every_enabled_app_is_reachable_from_the_sidebar():
    for a in discover():
        if not a.manifest.enabled:
            continue
        entries = a.manifest.nav_entries()
        assert entries, f"{a.slug} không có mục nav -> không ai vào được"
        for e in entries:
            assert e.path.startswith("/"), f"{a.slug}: {e.path} không tuyệt đối"


def test_manifest_without_nav_gets_a_default_entry():
    m = AppManifest(slug="x", display_name="App X", route_prefix="/x")
    entries = m.nav_entries()
    assert len(entries) == 1
    assert entries[0].path == "/x"


def test_declared_nav_is_used_as_is():
    m = AppManifest(slug="x", display_name="X", route_prefix="/x",
                    nav=(NavEntry("A", "/x/a"), NavEntry("B", "/x/b")))
    assert [e.path for e in m.nav_entries()] == ["/x/a", "/x/b"]


# ── app hỏng không được làm sập nền tảng ───────────────────────────────────

def test_a_broken_app_does_not_break_discovery(tmp_path):
    """Nếu một app lỗi làm sập cả nền tảng thì bạn không vào được để xem app
    nào lỗi. Nó phải được ghi lại kèm lý do."""
    apps = tmp_path / "apps"
    (apps / "bad").mkdir(parents=True)
    (apps / "bad" / "__init__.py").write_text("", encoding="utf-8")
    (apps / "bad" / "manifest.py").write_text(
        "raise RuntimeError('hỏng có chủ ý')", encoding="utf-8")

    import sys
    sys.path.insert(0, str(tmp_path))
    try:
        result = discover(apps_dir=apps)
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("apps.bad.manifest", None)

    assert len(result) == 1
    assert result[0].error
    assert result[0].manifest.enabled is False


# ── nền tảng không được biết app nào tồn tại ───────────────────────────────

def test_platform_never_imports_an_app():
    """Chiều phụ thuộc chỉ đi một hướng. Nền tảng import app là quay lại đúng
    thứ registry sinh ra để tránh."""
    import ast

    offenders = []
    for path in (ROOT / "platform_core").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                if n == "apps" or n.startswith("apps."):
                    offenders.append(f"{path.name}:{node.lineno} -> {n}")
    assert offenders == [], f"platform_core import app: {offenders}"


def test_no_app_slug_is_hardcoded_in_the_platform():
    """Tên app xuất hiện trong code nền tảng là dấu hiệu registry bị đi vòng."""
    slugs = [a.slug for a in discover() if a.slug != "demo"]
    offenders = []
    for path in (ROOT / "platform_core").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for slug in slugs:
            if slug in text:
                offenders.append(f"{path.name}: {slug!r}")
    assert offenders == [], f"tên app bị viết cứng: {offenders}"


# ── app demo phải luôn chạy được ───────────────────────────────────────────

def test_demo_job_handler_works():
    from apps.demo import jobs
    out = jobs.handle({"text": "abc def"})
    assert out["output"] == "fed cba"
    assert out["words"] == 2


def test_demo_job_rejects_empty_input():
    """Handler phải NÉM lỗi khi thất bại. Trả về êm ru nghĩa là job 'thành
    công' và credit đã giữ vẫn bị trừ."""
    from apps.demo import jobs
    with pytest.raises(ValueError):
        jobs.handle({"text": "   "})
