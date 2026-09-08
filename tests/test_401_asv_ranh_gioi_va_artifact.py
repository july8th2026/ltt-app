"""Auto Scan Video — source-level boundaries and the artifact completion protocol.

Two kinds of guard live here.

**§1 source boundaries** bind code that does not exist yet (Phase 05+ creates
`apps/auto_scan_video/`, `apps/asv_media/`, `apps/asv_gpu/`). A guard over an empty set
of paths passes for the wrong reason, so each one is paired with a **self-test proving
the detector actually fires** on a synthetic violation. Without that pairing these would
be four green lights wired to nothing.

**§2 artifact protocol** pins the storage behaviour ADR-001 D7 depends on. That is real
today and testable today.
"""
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent

#: Every path Auto Scan will own. Empty entries are normal before Phase 05 — the guards
#: below start biting the moment a directory appears, with no edit needed here.
DUONG_AUTO_SCAN = (
    "apps/auto_scan_video",
    "apps/asv_media",
    "apps/asv_gpu",
    "apps/asv_voice",
)


def _tep_python(duong: str) -> list[Path]:
    goc = GOC / duong
    if not goc.exists():
        return []
    return [p for p in goc.rglob("*.py") if "__pycache__" not in p.parts]


def _tep_auto_scan() -> list[Path]:
    out: list[Path] = []
    for duong in DUONG_AUTO_SCAN:
        out.extend(_tep_python(duong))
    return out


def _docstring_ids(cay: ast.AST) -> set[int]:
    """`id()` of every docstring Constant node, so prose can be skipped."""
    ra: set[int] = set()
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Module, ast.ClassDef, ast.FunctionDef,
                            ast.AsyncFunctionDef)):
            than = getattr(nut, "body", None) or []
            if (than and isinstance(than[0], ast.Expr)
                    and isinstance(than[0].value, ast.Constant)
                    and isinstance(than[0].value.value, str)):
                ra.add(id(than[0].value))
    return ra


def _vi_pham(text: str, cam: tuple[str, ...]) -> list[str]:
    """Forbidden markers reachable as CODE. Docstrings and comments are exempt.

    🔴 **This started as a substring scan, and that was wrong in a way worth
       recording.** Every file it guards carries a comment explaining the rule —
       `apps/asv_gpu/jobs.py` names `gpu_arbiter` four times precisely to warn
       against it. A substring scan flagged those warnings as violations.

       A guard that fails on the text explaining the guard teaches the next
       author to delete the explanation. That is worse than no guard: it trades
       a real defence for a green light and removes the reason anyone knew about
       it.

    ⭐ So the unit is the **AST**, not the file. Comments never reach the tree at
       all, and docstrings are identified and skipped. String literals that are
       *not* docstrings still count — `os.environ["CUDA_VISIBLE_DEVICES"]` is a
       real violation and lives in a plain string.
    """
    try:
        cay = ast.parse(text)
    except SyntaxError:
        # Unparseable file is a different failure; let the compile step own it.
        return []

    bo_qua = _docstring_ids(cay)
    thay: set[str] = set()

    for nut in ast.walk(cay):
        if isinstance(nut, ast.Import):
            for ten in nut.names:
                thay.add(ten.name)
        elif isinstance(nut, ast.ImportFrom):
            if nut.module:
                thay.add(nut.module)
            for ten in nut.names:
                thay.add(ten.name)
        elif isinstance(nut, ast.Name):
            thay.add(nut.id)
        elif isinstance(nut, ast.Attribute):
            thay.add(nut.attr)
        elif isinstance(nut, ast.keyword) and nut.arg:
            # 🔴 THIEU DONG NAY THI GUARD `shell=True` KHONG BAO GIO NO DUOC.
            #    `shell=True` la mot `ast.keyword`, khong phai `Name` hay
            #    `Attribute`. Phep kiem cua pha 08 da xanh mot luot voi bo do
            #    khong the bat duoc no — tuc mot den xanh noi voi mot cai day
            #    khong noi vao dau ca, dung thu ma `test_may_do_...` sinh ra de
            #    chan. Bat duoc vi self-test do CA HAI CHIEU chu khong chi chieu
            #    "khong bao dong gia".
            thay.add(nut.arg)
        elif isinstance(nut, ast.Constant) and isinstance(nut.value, str):
            if id(nut) not in bo_qua:
                thay.add(nut.value)

    goi = "\n".join(thay)
    return [dau for dau in cam if dau in goi]


# ══════════════════════════════════════════════════════════════════════════════
#  §1 — source boundaries
# ══════════════════════════════════════════════════════════════════════════════

_CAM_GPU = ("gpu_arbiter", "gpu_claims", "CUDA_VISIBLE_DEVICES", "nvidia-smi")


def test_may_do_bat_duoc_MA_that_va_tha_cho_van_ban_giai_thich():
    """Proves the detector is both live and correctly scoped.

    ⭐ This is the test that gives the other four their meaning, in two directions:

       **Sensitivity** — a real import must be caught, or the guards are decoration.
       **Specificity** — prose must not be, or the guards punish documentation and
       the next author deletes the warning to get a green light.

    The second half is not hypothetical: this file's first version was a substring
    scan, and it failed on `apps/asv_gpu/jobs.py` — a file whose docstring names
    `gpu_arbiter` four times *for the purpose of forbidding it*.
    """
    # Sensitivity: real code, in each of the forms a violation can take.
    assert _vi_pham("from gpu_arbiter import current_gpu\n", _CAM_GPU) == ["gpu_arbiter"]
    assert _vi_pham("import gpu_arbiter\n", _CAM_GPU) == ["gpu_arbiter"]
    assert _vi_pham('os.environ["CUDA_VISIBLE_DEVICES"] = "0"\n',
                    _CAM_GPU) == ["CUDA_VISIBLE_DEVICES"]
    assert _vi_pham("from platform_core.job_submit import submit_with_credit\n",
                    ("submit_with_credit",)) == ["submit_with_credit"]
    # Tham so TU KHOA. Thieu nhanh nay thi guard `shell=True` cua pha 08 xanh
    # vinh vien — no da xanh mot luot truoc khi phep kiem nay bat duoc.
    assert _vi_pham("subprocess.run(cmd, shell=True)\n", ("shell",)) == ["shell"]

    # Specificity: the same names, as prose that explains the rule.
    assert _vi_pham('"""Never import gpu_arbiter; use ctx.gpu_env()."""\n',
                    _CAM_GPU) == []
    assert _vi_pham("# do not call submit_with_credit here\nx = 1\n",
                    ("submit_with_credit",)) == []

    # And the compliant form stays clean.
    assert _vi_pham("env = ctx.gpu_env(base=os.environ)\n", _CAM_GPU) == []


def test_auto_scan_KHONG_duoc_tu_chon_card_GPU():
    """I11 / O6 / ADR-001 D6 — handlers never choose hardware.

    🔴 This is not hypothetical. Five live call sites in the legacy trees select a card
       themselves and would come along on a copy-paste migration:
         FULL AUTO VIDEO/BOT_TRANSCRIPT/.../engine/stt.py:274
         FULL AUTO VIDEO/BOT_TRANSCRIPT/.../engine/whisper_integration.py:207
         FULL AUTO VIDEO/Bot_PausePipeline/engine/stt.py:82-89
         FULL AUTO VIDEO/DUNGVIDEO-FULL/engine/runner.py:697
       The platform assigns the card via `gpu_lease` and hands it over through
       `JobContext.gpu_env()`; anything else races the lease and OOMs a shared 3090.
    """
    xau = []
    for tep in _tep_auto_scan():
        con = _vi_pham(tep.read_text(encoding="utf-8", errors="replace"), _CAM_GPU)
        if con:
            xau.append(f"{tep.relative_to(GOC).as_posix()}: {con}")
    assert not xau, (
        "Auto Scan tu chon GPU — phai dung ctx.gpu_env() cua nen tang:\n"
        + "\n".join(xau))


def test_auto_scan_KHONG_duoc_phu_thuoc_core_legacy():
    """O9 — `core/` is the frozen socialbot legacy and must not gain a new caller."""
    xau = []
    for tep in _tep_auto_scan():
        text = tep.read_text(encoding="utf-8", errors="replace")
        if _vi_pham(text, ("from core.", "import core.")):
            xau.append(tep.relative_to(GOC).as_posix())
    assert not xau, f"Auto Scan import `core/` (di san dong bang): {xau}"


def test_job_giai_doan_KHONG_duoc_tu_giu_credit():
    """I3 / ADR-001 D4 — the one-line mistake that would double-charge every run.

    Stage jobs must be submitted with `jobs.submit`. Using `submit_with_credit` would
    give each of the nine stages its own hold **on top of** the run's, and the ledger
    would still balance — so nothing would look broken except the customer's balance.

    Only the customer-facing app may hold, and it holds for the *run*, not a stage.
    """
    xau = []
    for tep in _tep_auto_scan():
        if tep.parts[-2] == "auto_scan_video" and tep.name in ("routes.py", "billing.py"):
            continue  # the run-level hold lives here by design
        text = tep.read_text(encoding="utf-8", errors="replace")
        if _vi_pham(text, ("submit_with_credit",)):
            xau.append(tep.relative_to(GOC).as_posix())
    assert not xau, (
        "job giai doan dung submit_with_credit -> giu cho ca run LAN stage: " + str(xau))


def test_danh_sach_duong_auto_scan_khop_thuc_te():
    """Keeps §1 honest as the app is built.

    Once Phase 05 creates the app directories, this asserts the guard list actually
    covers them — the failure mode being a new `apps/asv_*` directory that no guard
    watches, which is how a boundary quietly stops existing.
    """
    thuc_te = sorted(p.name for p in (GOC / "apps").iterdir()
                     if p.is_dir() and (p.name.startswith("asv_")
                                        or p.name == "auto_scan_video"))
    khai = sorted(Path(d).name for d in DUONG_AUTO_SCAN)
    assert thuc_te == [] or thuc_te == khai, (
        f"apps/ co {thuc_te} nhung guard chi canh {khai} — them vao DUONG_AUTO_SCAN")


# ══════════════════════════════════════════════════════════════════════════════
#  §2 — artifact completion protocol (ADR-001 D7)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def kho(tmp_path):
    from platform_core.storage import LocalStorage
    return LocalStorage(str(tmp_path / "kho"))


def test_promote_di_chuyen_va_XOA_ban_staging(kho):
    """D7 step 3. A promoted artifact must leave no staging twin behind.

    If staging survived, `upload_sessions.sweep` would later delete a file that is now
    referenced — or bill storage twice for the same bytes.
    """
    kho.put("staging/a.bin", io.BytesIO(b"noi dung"), content_type="application/octet-stream")
    assert kho.exists("staging/a.bin")

    kho.promote("staging/a.bin", "asv/uA/run1/media/deadbeef.bin")
    assert kho.exists("asv/uA/run1/media/deadbeef.bin")
    assert not kho.exists("staging/a.bin"), "ban staging con lai sau khi promote"


def test_promote_khong_co_staging_thi_NEM_chu_khong_tao_tep_rong(kho):
    """D7 crash gap 2→3. The failure must be loud.

    A crash between validate and promote leaves no staging object. If `promote` then
    invented an empty file, the stage would record a durable ref to zero bytes and mark
    itself DONE — I8 violated, and the customer receives an empty video.
    """
    from platform_core.storage import StorageError

    with pytest.raises(StorageError):
        kho.promote("staging/khong-ton-tai.bin", "asv/uA/run1/media/x.bin")
    assert not kho.exists("asv/uA/run1/media/x.bin"), (
        "promote that bai nhung van tao tep dich -> stage se DONE voi tep rong")


def test_ghi_lai_cung_mot_van_tay_la_idempotent(kho):
    """D7 crash gap 3→4, and why keys are derived from the fingerprint.

    A stage that promoted successfully but died before persisting its refs re-runs and
    promotes again to the **same** key. Because the key comes from the fingerprint and
    not from a timestamp or a counter, the second write overwrites the first instead of
    orphaning it — so the crash costs compute, never correctness.
    """
    dich = "asv/uA/run1/media/vantay123.bin"
    kho.put("staging/1.bin", io.BytesIO(b"lan mot"))
    kho.promote("staging/1.bin", dich)

    kho.put("staging/2.bin", io.BytesIO(b"lan hai"))
    kho.promote("staging/2.bin", dich)

    assert kho.exists(dich)
    with kho.open(dich) as f:
        assert f.read() == b"lan hai"
    assert not kho.exists("staging/1.bin") and not kho.exists("staging/2.bin")


def test_khoa_artifact_tach_theo_chu_so_huu_va_run(kho):
    """I6 / I19 — the key layout itself carries the isolation.

    `asv/{owner}/{run}/{stage}/{fingerprint}` means two owners with an identical
    fingerprint still land on different keys. Isolation that depends only on a database
    filter is one forgotten `WHERE` away from leaking; putting the owner in the key
    makes the leak require a deliberate path construction.
    """
    kho.put("staging/a.bin", io.BytesIO(b"cua A"))
    kho.put("staging/b.bin", io.BytesIO(b"cua B"))
    kho.promote("staging/a.bin", "asv/uA/run1/media/vantay-giong-nhau.bin")
    kho.promote("staging/b.bin", "asv/uB/run9/media/vantay-giong-nhau.bin")

    with kho.open("asv/uA/run1/media/vantay-giong-nhau.bin") as f:
        assert f.read() == b"cua A"
    with kho.open("asv/uB/run9/media/vantay-giong-nhau.bin") as f:
        assert f.read() == b"cua B"


# ══════════════════════════════════════════════════════════════════════════════
#  §3 — media fixtures usable by Phases 08+
# ══════════════════════════════════════════════════════════════════════════════

def test_fixture_media_co_du_hai_luong(tmp_path):
    """MEDIA_PREPARE and AUDIO_PREPARE both need something to chew on."""
    from platform_core import media
    from tests.fixtures.asv_media import tiny_mp4

    duong = tiny_mp4(tmp_path / "tiny.mp4")
    thong_tin = media.probe(str(duong))
    assert thong_tin["duration"] == pytest.approx(3.0, abs=0.2)
    assert thong_tin["width"] == 320 and thong_tin["height"] == 240
    assert thong_tin["audio_codec"], "fixture phai co luong tieng"


def test_fixture_video_cam_khong_co_luong_tieng(tmp_path):
    """The input `MVP_CONTRACT.md` §2 rejects at submit — needs a fixture to test with."""
    from platform_core import media
    from tests.fixtures.asv_media import tiny_mp4_silent

    duong = tiny_mp4_silent(tmp_path / "cam.mp4")
    assert not media.probe(str(duong)).get("audio_codec"), (
        "fixture 'khong tieng' lai co tieng")
