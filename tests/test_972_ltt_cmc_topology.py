"""Chot topology va ho so khoi dong LTT-CMC."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ltt_cmc_co_quyet_dinh_va_hang_muc_dang_mo():
    decisions = (ROOT / "docs/QUYET_DINH_NEN_TANG.md").read_text(
        encoding="utf-8")
    plan = (ROOT / "docs/KE_HOACH_TRIEN_KHAI.md").read_text(
        encoding="utf-8")
    assert "### Q123 — LTT-CMC" in decisions
    assert "`main` là nhánh chuẩn" in decisions
    assert "## H45 — LTT-CMC" in plan
    assert "H45.0" in plan and "[ ]" in plan


def test_ltt_cmc_state_ghi_sha_nguon_day_du():
    state = (ROOT / "docs/LTT_CMC/STATE.md").read_text(encoding="utf-8")
    assert "34b4626e24e5dda419adf5b407e46f5fb744c454" in state
    assert "SESSION_PROTECTED" in state
    assert "CANONICAL_CANDIDATE" in state
