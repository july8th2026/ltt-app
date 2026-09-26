"""`handoff_stage.py` chi duoc dua vao DUNG 5 ten cua `apps.taovideo.refs` (G-3b).

Doc bang AST, khong import — mot import them ten thu sau la mot QUYET DINH
KIEN TRUC phai khai lai o ca hai dau (`tools/lint_app_contract.py` +
`apps/taovideo/__init__.py::BE_MAT_CONG_KHAI`) va o `.importlinter`, khong phai
mot tien nghi lam tro trong mot tep.

⭐ Bo cho phep o day la DUNG 5 ten cua `BE_MAT_CONG_KHAI`, ⛔ khong co
`RefError`: `RefError` la mot ten cua `refs.py` nhung KHONG nam trong ban khai,
nen dua no vao la mo mot canh khong cong cu nao kiem. `handoff_stage` do nguong
bang `normalize_image` + `MAX_INLINE_BYTES` va bat `RuntimeError` (lop cha cua
`RefError`) thay vi import ten do.
"""
from __future__ import annotations

import ast
import pathlib

NGUON = pathlib.Path("apps/prompt_ai_ommi/services/handoff_stage.py")


def _cay() -> ast.Module:
    return ast.parse(NGUON.read_text(encoding="utf-8"))


def _be_mat_da_khai() -> set[str]:
    """Doc `BE_MAT_CONG_KHAI` cua taovideo bang AST tu NGUON, khong import.

    ⭐ Lay tu ban khai THAT chu khong chep literal vao day: chep la hai cho
    khai cung mot dieu, va cai bay `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`
    khong tu tha cho mot tep test.
    """
    src = pathlib.Path("apps/taovideo/__init__.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Assign)
                and any(getattr(t, "id", "") == "BE_MAT_CONG_KHAI"
                        for t in node.targets)):
            return {ten for _module, ten in ast.literal_eval(node.value)}
    raise AssertionError("apps/taovideo/__init__.py khong khai BE_MAT_CONG_KHAI")


def test_chi_dua_vao_ten_da_khai_o_be_mat_cong_khai():
    dua_vao = set()
    for node in ast.walk(_cay()):
        if (isinstance(node, ast.ImportFrom)
                and node.module == "apps.taovideo.refs"):
            dua_vao |= {alias.name for alias in node.names}
    assert dua_vao, "handoff_stage.py phai import tu apps.taovideo.refs"
    ngoai_bang = dua_vao - _be_mat_da_khai()
    assert not ngoai_bang, f"import ngoai ban khai (G-3b): {sorted(ngoai_bang)}"


def test_khong_import_module_taovideo_nao_khac():
    for node in ast.walk(_cay()):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
        elif isinstance(node, ast.Import):
            module = ",".join(alias.name for alias in node.names)
        else:
            continue
        if "taovideo" not in module:
            continue
        assert module == "apps.taovideo.refs", (
            f"chi duoc dua vao apps.taovideo.refs, thay: {module!r}")


def test_routes_handoff_khong_con_import_taovideo():
    """Phep chuyen cua Pha 2: route thoi import `refs`, service nhan viec do.

    Day cung la dong doi chieu voi `.importlinter`: import-linter TU CHOI mien
    tru CHET, nen neu route import lai `refs` ma khong ai khai lai dong do thi
    hang rao se do — va nguoc lai.
    """
    src = pathlib.Path("apps/prompt_ai_ommi/routes/handoff.py").read_text(
        encoding="utf-8")
    for node in ast.walk(ast.parse(src)):
        module = ""
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
        elif isinstance(node, ast.Import):
            module = ",".join(alias.name for alias in node.names)
        assert "taovideo" not in module, (
            f"routes/handoff.py khong duoc import taovideo nua: {module!r}")


def test_prefill_khong_import_nguoc_sang_ommi():
    """Canh app->app la MOT CHIEU — chieu nguoc lai phai rong o CA HAI tep
    cua `taovideo` ma Pha 2 cham vao."""
    for ten in ("apps/taovideo/prefill.py", "apps/taovideo/routes.py"):
        src = pathlib.Path(ten).read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(src)):
            module = ""
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
            elif isinstance(node, ast.Import):
                module = ",".join(alias.name for alias in node.names)
            assert "prompt_ai_ommi" not in module, (
                f"{ten} khong duoc import prompt_ai_ommi: {module!r}")
