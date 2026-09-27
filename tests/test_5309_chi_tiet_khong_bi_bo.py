"""Sec 6.2b -- chi tiet camera/lighting/mood PHAI vao prompt, khong bi bo.

Con bo nay dang o `routes/handoff.py:44`: ghi de cung `motion="cinematic"`
roi bo `scene.camera`. Sua N-1 bang cach chi khop enum roi bo chu goc la VUT
TRUONG IM LANG LAN THU HAI.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services.briefs import prompt_day_du
from apps.prompt_ai_ommi.tables import OmmiCanh

CHI_TIET = "medium shot, 35mm, slow push in"


def test_camera_chu_tu_do_nam_NGUYEN_VAN_trong_prompt():
    c = OmmiCanh(owner_id="u_1", brief_id="b", prompt="Nhan vat buoc vao phong",
                 camera=CHI_TIET, lighting="golden hour, rim light",
                 mood="tram lang")
    ra = prompt_day_du(c)
    assert CHI_TIET in ra
    assert "golden hour, rim light" in ra
    assert "tram lang" in ra
    assert "Nhan vat buoc vao phong" in ra


def test_truong_rong_thi_khong_them_nhan_trong():
    c = OmmiCanh(owner_id="u_1", brief_id="b", prompt="P", camera="", lighting="", mood="")
    assert prompt_day_du(c).strip() == "P"


def test_chi_mot_truong_co_thi_chi_them_nhan_do():
    c = OmmiCanh(owner_id="u_1", brief_id="b", prompt="P", camera=CHI_TIET, lighting="", mood="")
    ra = prompt_day_du(c)
    assert "Camera:" in ra and "Lighting:" not in ra and "Mood:" not in ra


def test_tat_dinh_goi_hai_lan_ra_cung_mot_chuoi():
    """`camera` nam trong `idempotency.key_fields` cua taovideo.

    Khong tat dinh thi hai lan giao bai cung mot canh tach doi job dedupe.
    """
    c = OmmiCanh(owner_id="u_1", brief_id="b", prompt="P", camera=CHI_TIET,
                 lighting="L", mood="M")
    assert prompt_day_du(c) == prompt_day_du(c)
