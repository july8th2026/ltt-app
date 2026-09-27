"""Loi vao mac dinh la 2-pane Studio Kich ban (Q-3), va `/classic` con song."""
from __future__ import annotations

import pathlib

SRC = pathlib.Path("frontend/prompt-ai-ommi/src")


def test_co_studio_shell_va_brief_pane():
    assert (SRC / "StudioShell.tsx").exists()
    assert (SRC / "BriefPane.tsx").exists()


def test_ommi_shell_lay_studio_lam_man_mac_dinh():
    nguon = (SRC / "OmmiShell.tsx").read_text(encoding="utf-8")
    assert "StudioShell" in nguon


def test_duong_classic_khong_bi_xoa():
    """`/classic` la duong lui khi Studio moi co van de tren production."""
    nguon = pathlib.Path("apps/prompt_ai_ommi/routes/pages.py").read_text(
        encoding="utf-8")
    assert "classic" in nguon
