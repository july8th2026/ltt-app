"""Banh coc: `bindings._ROLE_ALIAS_CU` phai KHOP `taovideo.refs._ROLE_REMAP`.

`services/bindings.py` khai literal mot bang alias ten role cu (khong doc
thuoc tinh rieng tu `_ROLE_REMAP` cua taovideo — xem docstring dau tep do).
Khai literal thi co nguy co LECH khi taovideo doi bang that: bai test nay la
luoi bat lech do, dat trong `tests/` vi day la noi DUY NHAT duoc phep import
ca hai app (`.importlinter` cai quan goi `apps/`, khong cai quan `tests/`).
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services.bindings import _ROLE_ALIAS_CU, BindingError, _clean_role
from apps.taovideo.refs import VALID_IMAGE_ROLES, _ROLE_REMAP


def test_role_alias_cu_khop_dung_bang_that_cua_taovideo():
    assert _ROLE_ALIAS_CU == _ROLE_REMAP, (
        "bindings._ROLE_ALIAS_CU da lech voi taovideo.refs._ROLE_REMAP — "
        "sua _ROLE_ALIAS_CU trong apps/prompt_ai_ommi/services/bindings.py "
        "cho khop lai (khong doc thang thuoc tinh rieng tu cua taovideo).")


def test_moi_dich_cua_alias_deu_la_role_hop_le():
    for ten_cu, dich in _ROLE_ALIAS_CU.items():
        assert dich in VALID_IMAGE_ROLES, (
            f"alias {ten_cu!r} -> {dich!r} khong nam trong VALID_IMAGE_ROLES")


def test_ten_rac_van_bi_tu_choi_khong_duoc_khoan_dung_ngam():
    """Doi chung: neu _clean_role tro nen khoan dung voi MOI chuoi (khong
    con nem BindingError) thi hai phep so o tren van co the xanh gia tao."""
    with pytest.raises(BindingError):
        _clean_role("image", "khong_ton_tai")
