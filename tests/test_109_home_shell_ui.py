"""H15.S3 HOME-001 — khóa shell marketplace, mobile và accessibility."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_home_mobile_navigation_co_hanh_vi_va_aria_contract():
    home = _read("server/templates/home.html")

    assert 'id="market-side"' in home
    assert 'aria-controls="market-side"' in home
    assert 'aria-expanded="false"' in home
    assert 'class="market-scrim"' in home
    assert "market-nav-open" in home
    assert "function closeNav()" in home
    assert "function openNav()" in home
    assert "if(e.key==='Escape')" in home


def test_home_filter_va_progress_co_accessible_state():
    home = _read("server/templates/home.html")

    # H24: nhan gio di qua catalog dich. Van chot rang bo loc CO ten doc duoc
    # cho trinh doc man hinh — do moi la dieu test nay canh.
    assert "aria-label=" in home
    assert "Lọc theo nhóm" in home
    assert 'data-category="all" aria-pressed="true"' in home
    assert "setAttribute('aria-pressed',String(on))" in home
    assert 'id="market-count" aria-live="polite"' in home
    # Golden UI: role/aria-valuemin/max/label nam trong macro `ui.thanh_tien_do`
    # (`_ui.html`, chot tai test_1270); home phai DUNG macro do.
    assert "ui.thanh_tien_do(progress," in home
    assert "{% set progress = [[job.progress or 0, 0]|max, 100]|min %}" in home
    assert "Jobs đang chạy" not in home


def test_home_shell_dung_semantic_token_va_mobile_account():
    css = _read("server/static/ltt.css")
    marker = css.index("H15.S3 HOME-001")
    home_css = css[marker:]

    for token in (
        "var(--surface-base)",
        "var(--surface-raised)",
        "var(--border-subtle)",
        "var(--text-primary)",
        "var(--brand-primary)",
        "var(--status-warning)",
        "var(--motion-normal)",
    ):
        assert token in home_css
    assert ".market-nav-open .market-side" in home_css
    assert ".market-account{display:block" in home_css

