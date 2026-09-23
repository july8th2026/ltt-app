"""Khoa LTTCODE phai doc duoc so du - N-04."""
from apps.lttcode.dang_nhap import SCOPES_KHOA
from platform_core.public_api.scopes import (SCOPE_CREDITS_READ, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ)


def test_khoa_lttcode_doc_duoc_so_du():
    assert SCOPE_CREDITS_READ in SCOPES_KHOA


def test_khong_no_them_quyen_ngoai_bon_quyen_da_chot():
    assert set(SCOPES_KHOA) == {SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE,
                                SCOPE_JOBS_READ, SCOPE_CREDITS_READ}
