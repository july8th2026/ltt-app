"""X-5 -- khoi chu khoa nhan vat PHAI di vao prompt gui LLM.

⚠️ Day la ca "tinh nang co ma khong lam gi": `fixed_prompt_block` VAN duoc luu,
   VAN hien tren giao dien, chi khong di vao prompt. Khong phep kiem nao khac
   bat duoc -- dung dang loi `pham-vi-phep-do-hep-hon-loi-tuyen-bo`.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services.composer import director_prompt

KHOI = "an elderly Vietnamese man, silver beard, brown ao dai"


def test_khoi_chu_khoa_nam_nguyen_van_trong_prompt_gui_LLM():
    _system, prompt = director_prompt({
        "story": "x" * 40, "scene_count": 3, "duration": 15,
        "character_block": KHOI})
    assert KHOI in prompt


def test_khong_co_khoi_thi_prompt_van_dung_duoc():
    _system, prompt = director_prompt({
        "story": "x" * 40, "scene_count": 3, "duration": 15})
    assert "x" * 40 in prompt


def test_khoi_boi_canh_cung_vao_prompt():
    _system, prompt = director_prompt({
        "story": "x" * 40, "scene_count": 3, "duration": 15,
        "background_block": "a warm living room at dusk"})
    assert "a warm living room at dusk" in prompt
