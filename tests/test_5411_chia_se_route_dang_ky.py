"""Rao cung S4 (brief lan F, pha 4): cot `share_level` phai co MOT duong HTTP
dat duoc, va duong do phai THAT SU duoc dang ky vao `router` cua app - khong
chi ton tai trong tep `routes/chia_se.py`.

⚠️ Phep kiem dang ky duoi day se DO cho toi khi dieu phoi (Lan M) them
`chia_se` vao danh sach import cua `apps/prompt_ai_ommi/routes/__init__.py`
(Task 9 cua plan pha 4) - dung nhu rao cung da chot, Lan F KHONG tu dang ky
tep do. Day la ban ghi TAM THOI cho biet "cot chet" hay chua, khong phai loi
o `routes/chia_se.py`.

Phep kiem dang ky chay o TIEN TRINH RIENG (subprocess), khong dung chung
process voi cac test khac trong file/goi nay: neu chay chung process, mot
test khac (vi du test truc tiep import `routes.chia_se`) co the da gan cac
duong nay vao `router` singleton TRUOC no, lam phep kiem PASS gia tao du
`routes/__init__.py` chua he dang ky gi. `router` (khai o routes/_shared.py)
la MOT APIRouter dung chung cho ca app.
"""
from __future__ import annotations

import subprocess
import sys


#: `router` la mot APIRouter DUNG CHUNG cho ca app (khai o routes/_shared.py),
#: chua co tien to "/prompt-ai-ommi" o muc nay - tien to do chi duoc them luc
#: nen tang goi `app.include_router(router, prefix=...)`. Do do kiem tren
#: `router.routes` phai dung duong CHUA co tien to.
_EXPECTED_PATHS = {
    "/api/share",
    "/api/share/{code}",
    "/api/share/{code}/nhan",
    "/api/library/{kind}/{item_id}/share-level",
}

_CHECK_SCRIPT = (
    "from apps.prompt_ai_ommi.routes import router\n"
    "paths = {getattr(r, 'path', None) for r in router.routes}\n"
    "print('|'.join(sorted(paths)))\n"
)


def test_share_routes_are_defined_in_the_chia_se_module():
    """Phep kiem NOI DUNG tep: routes/chia_se.py tu dinh nghia dung 4 duong
    mong doi, doc lap voi viec __init__.py co import no hay khong."""
    import importlib
    module = importlib.import_module("apps.prompt_ai_ommi.routes.chia_se")
    paths_in_module = {
        route.path for route in module.router.routes
        if getattr(route, "path", None) in _EXPECTED_PATHS}
    assert paths_in_module == _EXPECTED_PATHS, (
        f"routes/chia_se.py thieu duong: {_EXPECTED_PATHS - paths_in_module}")


def test_share_routes_are_registered_on_the_apps_public_router():
    """Phep kiem DANG KY THAT: `routes/__init__.py` phai import module
    chia_se de cac duong tren duoc dang ky vao `router` dung nhu app that su
    mount. Neu __init__.py chua import chia_se (Task 9, Lan M chua chay), tap
    duong nay RONG so voi mong doi - cot `share_level` la CHET, dung lop loi
    D-2 (`ommi_binding.scene_id IS NULL` do khong ai sinh/doc)."""
    result = subprocess.run(
        [sys.executable, "-c", _CHECK_SCRIPT],
        cwd=None, capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, (
        f"loi chay phep kiem dang ky:\nSTDOUT={result.stdout}\nSTDERR={result.stderr}")
    known_paths = set(result.stdout.strip().split("|")) if result.stdout.strip() else set()
    missing = _EXPECTED_PATHS - known_paths
    assert not missing, (
        "duong chia se CHUA duoc dang ky vao apps.prompt_ai_ommi.routes.router "
        f"(thieu: {missing}). Cho Task 9 (Lan M) sua "
        "apps/prompt_ai_ommi/routes/__init__.py them 'chia_se' vao danh sach "
        "import - Lan F khong tu sua tep do.")
