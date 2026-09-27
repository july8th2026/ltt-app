"""Loi nhac khoa nhan vat -- chuyen tu `prompt_canh`, dung bo placeholder cua ta.

⛔ Ban goc dung ten bien rieng cua no. Giu ten cu nghia la co HAI bo placeholder
   trong mot app -- dung bay `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`.
"""
from __future__ import annotations

import pathlib

from apps.prompt_ai_ommi.services.placeholders import tim_placeholder

TEP = pathlib.Path("apps/prompt_ai_ommi/prompts/khoa_nhan_vat.txt")

#: Bien loi nhac nay dung. Them bien moi ⇒ them vao day VA vao
#: `services/nhan_vat.py::_gia_tri_khoa`.
BIEN_CHO_PHEP = {"NAME", "GENDER", "AGE_RANGE", "FACE", "BODY", "HAIR",
                 "OUTFIT", "PERSONALITY", "EXPRESSION", "MOVEMENT",
                 "NEGATIVE_NOTES"}


def test_tep_ton_tai_va_khong_rong():
    assert TEP.exists() and TEP.read_text(encoding="utf-8").strip()


def test_khong_dung_bien_ngoai_danh_sach_cho_phep():
    dung = set(tim_placeholder(TEP.read_text(encoding="utf-8")))
    la = dung - BIEN_CHO_PHEP
    assert not la, f"bien khong khai: {sorted(la)}"


def test_tep_khong_co_BOM():
    """BOM trong tep cau hinh da lam sap production (AGENTS.md Sec 5)."""
    assert not TEP.read_bytes().startswith(b"\xef\xbb\xbf")
