"""T-2 (spec Sec 10.2) -- bo kiem placeholder chay tren CA 12 mau cua ban goc.

Khong test mau dai dien. Bai hoc `vi-du-trong-loi-nhac-la-menh-lenh-ngam`:
sua theo vai vi du lam tut mot cai von dung.

Pham vi phep do nay: no do BO PLACEHOLDER (do duoc tu CSDL ban goc 26/09),
chua do NOI DUNG that cua 12 mau -- noi dung duoc nhap o pha 4, va pha 4 PHAI
chay lai phep nay tren noi dung that.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from apps.prompt_ai_ommi.services.placeholders import (
    NGUON_GIA_TRI, kiem_placeholder)

MAU = json.loads(
    (pathlib.Path(__file__).parent / "fixtures"
     / "ommi_mau_goc_placeholders.json").read_text(encoding="utf-8"))

#: 4 bien TU DO cua mau `Ong Ngoai` -- khong co nguon he thong, khach tu nhap.
BIEN_TU_DO = {"FACTION_A", "FACTION_B", "MIN_COMBAT_DISTANCE", "NEUTRAL_LIST"}


def test_fixture_dung_12_mau():
    """Dem cung la mot phep kiem: 12 la so do duoc, khong phai so uoc."""
    assert len(MAU) == 12


def _gia_tri_day_du(placeholders: list[str]) -> dict:
    return {ten: f"<{ten}>" for ten in placeholders}


@pytest.mark.parametrize("mau", MAU, ids=[m["ten"] for m in MAU])
def test_moi_mau_render_duoc_khi_du_gia_tri(mau):
    body = " ".join("{%s}" % ten for ten in mau["placeholders"])
    thieu = kiem_placeholder(body, mau["placeholders"],
                             _gia_tri_day_du(mau["placeholders"]))
    assert thieu == [], f"{mau['ten']} con thieu: {thieu}"


@pytest.mark.parametrize("mau", MAU, ids=[m["ten"] for m in MAU])
def test_moi_placeholder_he_thong_deu_co_nguon(mau):
    """Bien khong phai bien tu do thi PHAI co trong bang nguon gia tri."""
    khong_nguon = [t for t in mau["placeholders"]
                   if t not in NGUON_GIA_TRI and t not in BIEN_TU_DO]
    assert khong_nguon == [], (
        f"{mau['ten']}: bien khong co nguon va khong phai bien tu do: "
        f"{khong_nguon}")


@pytest.mark.parametrize("mau", MAU, ids=[m["ten"] for m in MAU])
def test_thieu_mot_gia_tri_thi_PHAI_bao_thieu(mau):
    """Doi chung: bo mot gia tri di, bo kiem phai bat duoc.

    Khong co phep nay thi `thieu == []` o tren co the chi vi ham luon tra rong
    -- bai hoc `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`.
    """
    body = " ".join("{%s}" % ten for ten in mau["placeholders"])
    gia_tri = _gia_tri_day_du(mau["placeholders"])
    bo = mau["placeholders"][0]
    gia_tri.pop(bo)
    assert bo in kiem_placeholder(body, mau["placeholders"], gia_tri)
