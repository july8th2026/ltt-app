"""Canh app->app moi (prompt_ai_ommi -> taovideo) phai duoc khai HAI CHIEU (G-3b).

`apps/taovideo/__init__.py` dang RONG HOAN TOAN truoc task nay, nen bai nay
la RED: linter se bao ERROR "duoc app khac goi sang nhung KHONG tu khai be
mat" ngay khi canh duoc them vao APP_DUOC_DUNG_APP ma khong sua ben kia.
"""
from __future__ import annotations

import subprocess
import sys
import pathlib

GOC = pathlib.Path(__file__).resolve().parent.parent


def test_canh_duoc_khai_trong_allowlist():
    from tools.lint_app_contract import APP_DUOC_DUNG_APP
    canh = APP_DUOC_DUNG_APP.get(("prompt_ai_ommi", "taovideo"))
    assert canh == {
        ("apps.taovideo.refs", "normalize_image"),
        ("apps.taovideo.refs", "image_to_inline"),
        ("apps.taovideo.refs", "image_role"),
        ("apps.taovideo.refs", "VALID_IMAGE_ROLES"),
        ("apps.taovideo.refs", "MAX_INLINE_BYTES"),
    }


def test_taovideo_tu_khai_be_mat_khop_allowlist():
    import ast
    from tools.lint_app_contract import APP_DUOC_DUNG_APP
    source = (GOC / "apps" / "taovideo" / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    khai = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "BE_MAT_CONG_KHAI" for t in node.targets):
            khai = ast.literal_eval(node.value)
    assert khai is not None, "apps/taovideo/__init__.py thieu BE_MAT_CONG_KHAI"
    assert set(khai) == APP_DUOC_DUNG_APP[("prompt_ai_ommi", "taovideo")]


def test_lint_app_contract_khong_co_ERROR_ve_taovideo():
    ra = subprocess.run([sys.executable, "tools/lint_app_contract.py"],
                        cwd=str(GOC), capture_output=True, text=True)
    assert "taovideo" not in "\n".join(
        line for line in ra.stdout.splitlines() if "ERROR" in line), ra.stdout


def test_lint_app_contract_thoat_ma_0():
    ra = subprocess.run([sys.executable, "tools/lint_app_contract.py"],
                        cwd=str(GOC), capture_output=True, text=True)
    assert ra.returncode == 0, ra.stdout
