"""Chot authority branch va van hanh sau Q123."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import cay_rieng, do_phu_diff


ROOT = Path(__file__).resolve().parents[1]


def test_cong_cu_dung_main_lam_trunk():
    assert cay_rieng.NHANH_TRUNK == "main"
    assert do_phu_diff.NHANH_GOC_MAC_DINH == ("origin/main", "main")


def test_tao_cay_that_su_phan_nhanh_tu_main(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    calls = []

    monkeypatch.setattr(cay_rieng, "GOC", root)
    monkeypatch.setattr(cay_rieng, "la_cay_chinh", lambda: True)
    monkeypatch.setattr(cay_rieng, "_dang_do", lambda: [])
    monkeypatch.setattr(cay_rieng, "_chep_thu_khong_o_trong_git", lambda _p: None)
    monkeypatch.setattr(cay_rieng, "_cap_dai_so_test", lambda _p: None)
    monkeypatch.setattr(
        cay_rieng.shutil, "disk_usage",
        lambda _p: SimpleNamespace(free=100 * 1024 ** 3))

    def fake_git(*args, **_kwargs):
        calls.append(args)
        return ""

    monkeypatch.setattr(cay_rieng, "_git", fake_git)

    assert cay_rieng._tao("cmc-contract") == 0
    assert ("worktree", "add", str(tmp_path / "repo-cmc-contract"),
            "-b", "phien/cmc-contract", "main") in calls


def test_thieu_main_thi_do_phu_fail_closed(monkeypatch):
    monkeypatch.setattr(
        do_phu_diff.subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1))
    with pytest.raises(SystemExit, match="main"):
        do_phu_diff._nhanh_goc_mac_dinh()


def test_ci_bao_ve_main_trong_giai_doan_chuyen_tiep():
    workflow = (ROOT / ".github/workflows/gate-quick.yml").read_text(
        encoding="utf-8")
    assert "branches: [main, admin-mvp-v3, master]" in workflow


def test_tai_lieu_song_tro_ve_hop_dong_van_hanh():
    deploy = (ROOT / "docs/16_CAP_NHAT_VA_DEPLOY.md").read_text(
        encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "docs/00_LTT_OPERATING_CONTRACT.md" in deploy
    assert "sau mỗi lần sửa" not in deploy
    assert "docs/NHAT_KY.md" in claude
    assert "_luutru/PROJECT_MEMORY.md` | nhật ký" not in claude
