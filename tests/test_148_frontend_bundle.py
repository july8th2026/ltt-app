"""
test_148 - bundle React: mot cho tra duong dan, khong app nao dem cap thu muc.

Vi sao co file nay: 2026-08-06, luc tach `apps/prompt_ai_ommi/routes.py` thanh
package, file tinh goc repo bang `Path(__file__).parents[2]` sau them mot cap.
`parents[2]` tro vao `apps/`, manifest khong doc duoc, va trang **van tra 200**
voi mot vo trong. Khong log, khong exception - chi nguoi dung thay trang trang.

Ba app deu chep doan do. Gio ca ba goi `platform_core.frontend_bundle`.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

from platform_core.frontend_bundle import REPO_ROOT, bundle_assets, manifest_path

ROOT = pathlib.Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"

# Bundle nao dang duoc app dung. Them bundle moi thi them vao day - test se doi
# hoi no that su da build, giong `tools/gate.py`.
BUNDLES = ["agent-canvas", "autosub-studio", "prompt-ai-ommi"]


def test_repo_root_khong_phu_thuoc_do_sau_cua_file():
    """Goc repo phai la goc repo that, du module nam o dau."""
    assert REPO_ROOT == ROOT, f"goc repo sai: {REPO_ROOT} != {ROOT}"
    assert (REPO_ROOT / "server" / "static").is_dir()
    assert (REPO_ROOT / "apps").is_dir()


@pytest.mark.parametrize("bundle", BUNDLES)
def test_moi_bundle_dang_dung_deu_giai_duoc_ra_file_that(bundle):
    """Tra ve URL rong = trang se hong lang le. Bat o day, khong bat o production."""
    scripts, styles = bundle_assets(bundle)
    assert scripts, (
        f"bundle {bundle!r} khong giai duoc ra JS nao. Manifest: "
        f"{manifest_path(bundle)} (ton tai: {manifest_path(bundle).is_file()})")
    for url in scripts + styles:
        assert url.startswith(f"/static/{bundle}/")
        served = ROOT / "server" / "static" / url[len("/static/"):]
        assert served.is_file(), f"{url} tro toi file khong ton tai: {served}"


def test_bundle_thieu_thi_tra_rong_chu_khong_no():
    """Caller quyet dinh hien gi; helper khong duoc nem giua luc render trang."""
    assert bundle_assets("khong-he-ton-tai") == ([], [])


def test_manifest_hong_cung_tra_rong(tmp_path, monkeypatch):
    """Manifest co that nhung sai cau truc cung phai tra rong, khong nem KeyError."""
    import platform_core.frontend_bundle as fb
    broken = tmp_path / "server" / "static" / "xx" / ".vite"
    broken.mkdir(parents=True)
    (broken / "manifest.json").write_text(json.dumps({"sai/entry.tsx": {}}),
                                          encoding="utf-8")
    monkeypatch.setattr(fb, "REPO_ROOT", tmp_path)
    assert fb.bundle_assets("xx") == ([], [])


def test_khong_app_nao_tu_neo_goc_repo_bang_cach_dem_cap():
    """`parents[n]` trong app = dem cap thu muc = gay ngay khi file doi cho.

    Chua doan lai `.vite/manifest.json` trong app: da co mot cho lam viec do.
    """
    dem_cap, tu_doc_manifest = [], []
    for path in sorted(APPS.rglob("*.py")):
        if "__pycache__" in path.parts or "vendor" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Bo dong chu thich - file frontend_bundle va cac ghi chu noi ve bay nay.
        code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
        rel = path.relative_to(ROOT).as_posix()
        if re.search(r"parents\[\s*[2-9]\s*\]", code):
            dem_cap.append(rel)
        if ".vite" in code and "manifest.json" in code:
            tu_doc_manifest.append(rel)

    # taoclipngan chen sys.path cho engine vendor - khac han viec tim static.
    dem_cap = [f for f in dem_cap if not f.startswith("apps/taoclipngan/")]

    assert not dem_cap, (
        "app dang neo duong dan bang cach dem cap thu muc: " + ", ".join(dem_cap) +
        " - dung platform_core.frontend_bundle hoac neo bang ten thu muc")
    assert not tu_doc_manifest, (
        "app dang tu doc manifest cua Vite: " + ", ".join(tu_doc_manifest) +
        " - dung platform_core.frontend_bundle.bundle_assets()")


def test_nen_tang_khong_biet_ten_app_nao():
    """Hop dong app: `platform_core` khong duoc nhac ten app cu the."""
    source = (ROOT / "platform_core" / "frontend_bundle.py").read_text(encoding="utf-8")
    for slug in [d.name for d in APPS.iterdir() if d.is_dir()] + BUNDLES:
        assert slug not in source, f"frontend_bundle.py nhac ten {slug!r}"
