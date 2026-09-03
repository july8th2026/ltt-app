"""Auto Scan Video V4 — a normal test run must not start a real model.

## The thing this prevents

`tools/test_nhanh.py` runs `pytest -n auto` = 20 workers on this machine, and **this
machine is production** (`C:\\LTTPlatform` exists; LTTStudioWeb, Worker, Voice and Codex
are all serving). On 2026-09-02 the owner had to **hard-reset the machine twice**. Session
`lttstudiosapp-a1` traced it: load did not *add*, it *multiplied*, because a heavy model ran
inside one worker of an already-parallel suite.

`pipeline.CHUOI` declares `tai_nguyen="tach_nguon_cuc_bo"` so the platform throttles it —
but that governs the **job queue**. pytest does not go through the queue.

Phase 04 put three real-model calls behind `tests/rao_chan_nang` (2 × demucs, 1 ×
faster-whisper). This file is what stops the fourth from arriving unnoticed.

## Why a ratchet and not a review habit

The three calls it found were written across two phases by an author who knew the rule and
had written it down. Nobody adds a heavy call on purpose; it arrives as one more line in a
test that already passes locally, on a machine where it takes four seconds.

## Design notes — both of these cost me a wrong first draft

**`assign_speakers` is not heavy.** My first forbidden-function list included it because it
lives in `ai_workflows` next to `diarize_file`. It is 12 lines of interval arithmetic
(`ai_workflows.py:77`) and loads nothing. Proximity is not evidence.

**Three call sites reach a heavy function without ever touching an engine.** `doc_mot_doan`
raises `GiongError` on an empty or over-long segment *before* it calls `goi_cong`. So the
detector cannot simply flag every mention; the exemptions are declared as a **set**, with a
reason each, and adding one is a visible diff — the same shape as
`test_421::TIEN_TRINH_CON_CHO_PHEP`.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
TESTS = GOC / "tests"

#: Ham NAP TRONG SO MODEL hoac goi mot dich vu sinh noi dung that.
#:
#: ⛔ `ffmpeg`/`ffprobe` khong nam day: chung la cong cu, chay vai tram mili giay,
#:    va moi giai doan media deu can — rao chung lai la lam ca bo test vo nghia.
HAM_NANG = {
    "tach_nguon":     "demucs — 4 stem, nap checkpoint torch hub",
    "transcribe_file": "faster-whisper / whisperx — nap model ASR",
    "diarize_file":   "pyannote — nap model phan biet nguoi noi",
    "goi_cong":       "goi may sinh tieng that qua loopback :8120",
    "doc_mot_doan":   "duong sinh tieng cua ASV, ket thuc o `goi_cong`",
}

#: Hai cach hop le de goi mot ham nang trong mot phep kiem:
#:   `monkeypatch` trong tham so  -> phep kiem tu thay engine bang mot ban gia
#:   `CHI_KHI_BAT` tren decorator -> phep kiem NANG, mac dinh bo qua
DAU_HIEU_AN_TOAN = ("monkeypatch", "CHI_KHI_BAT")

#: Ngoai le, khai theo TAP HOP. Moi dong la mot lan doc ma va ket luan rang loi
#: goi khong bao gio toi duoc engine. Them mot dong la mot QUYET DINH, va no
#: hien trong diff.
NGOAI_LE: dict[tuple[str, str], str] = {
    ("test_409_asv_giong_noi.py",
     "test_doan_QUA_DAI_bi_tu_choi_chu_KHONG_tu_chia_nho"):
        "`doc_mot_doan` nem GiongError o phep do do dai, TRUOC `vf.goi_cong` "
        "(giong_noi.py:160-166). Khong engine nao duoc cham.",
    ("test_409_asv_giong_noi.py", "test_doan_RONG_bi_tu_choi"):
        "`doc_mot_doan` nem GiongError ngay dong dau khi chuoi rong "
        "(giong_noi.py:152). Khong engine nao duoc cham.",
}


def _ten_duoc_goi(nut: ast.AST) -> set[str]:
    ra: set[str] = set()
    for n in ast.walk(nut):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                ra.add(f.attr)
            elif isinstance(f, ast.Name):
                ra.add(f.id)
    return ra


def _ten_trong_decorator(ham: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    ra: set[str] = set()
    for d in ham.decorator_list:
        for n in ast.walk(d):
            if isinstance(n, ast.Attribute):
                ra.add(n.attr)
            elif isinstance(n, ast.Name):
                ra.add(n.id)
    return ra


def _quet(nguon: str, ten_tep: str) -> list[tuple[str, str, list[str]]]:
    """`(tep, ten_test, ham_nang_bi_goi)` cho moi phep kiem KHONG co rao chan."""
    import warnings

    try:
        with warnings.catch_warnings():
            # ⚠️ `ast.parse` phat lai SyntaxWarning cua tep no doc (vd `\d` trong
            #    mot docstring regex). Do la canh bao cua TEP KIA; de no noi len
            #    o day chi lam ban ket qua va khien nguoi doc tuong phep kiem nay
            #    hong.
            warnings.simplefilter("ignore", SyntaxWarning)
            cay = ast.parse(nguon)
    except SyntaxError:
        return []
    vi_pham = []
    for ham in ast.walk(cay):
        if not isinstance(ham, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not ham.name.startswith("test_"):
            continue
        nang = sorted(_ten_duoc_goi(ham) & set(HAM_NANG))
        if not nang:
            continue
        an_toan = ({a.arg for a in ham.args.args} | _ten_trong_decorator(ham))
        if an_toan & set(DAU_HIEU_AN_TOAN):
            continue
        if (ten_tep, ham.name) in NGOAI_LE:
            continue
        vi_pham.append((ten_tep, ham.name, nang))
    return vi_pham


# ══════════════════════════════════════════════════════════════════════════════
#  Banh coc
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_phep_kiem_nao_goi_engine_nang_ma_khong_co_rao_chan():
    """G7 — mot lan chay thuong khong duoc khoi dong demucs/whisper/pyannote/TTS."""
    vi_pham = []
    for tep in sorted(TESTS.glob("test_*.py")):
        vi_pham += _quet(tep.read_text(encoding="utf-8"), tep.name)

    assert vi_pham == [], (
        "phep kiem goi engine NANG ma khong stub va khong rao:\n" +
        "\n".join(f"  {t}::{h} -> {n}" for t, h, n in vi_pham) +
        "\n\nSua bang MOT trong ba cach:\n"
        "  1. nhan `monkeypatch` va thay engine bang ban gia (cach thuong dung);\n"
        "  2. dat @rao_chan_nang.NANG + @rao_chan_nang.CHI_KHI_BAT neu that su "
        "can engine that, roi chay `python tools/check_bo_qua.py --accept`;\n"
        "  3. neu loi goi KHONG BAO GIO toi duoc engine, khai vao `NGOAI_LE` "
        "kem ly do doc duoc tu ma nguon.")


def test_bo_do_THAT_SU_bat_duoc():
    """Chung minh bo do khong phai mot den xanh noi vao khong.

    ⛔ Khong co phep kiem nay thi `_quet` co the tra `[]` mai mai va banh coc o
       tren van xanh — dung kieu "guard tren tap rong" ma `test_401` canh bao.
    """
    xau = ("def test_x(tmp_path):\n"
           "    tach_tieng.tach_nguon('a.wav', 'out')\n")
    assert _quet(xau, "t.py") == [("t.py", "test_x", ["tach_nguon"])]

    # Ba duong thoat, ca ba deu phai lam bo do IM.
    assert _quet("def test_x(monkeypatch):\n    tach_nguon('a','b')\n", "t.py") == []
    assert _quet("@rao_chan_nang.CHI_KHI_BAT\n"
                 "def test_x():\n    tach_nguon('a','b')\n", "t.py") == []
    ngoai_le_tep, ngoai_le_ham = next(iter(NGOAI_LE))
    assert _quet(f"def {ngoai_le_ham}():\n    doc_mot_doan('x')\n",
                 ngoai_le_tep) == []

    # Va mot phep kiem KHONG cham engine phai khong bao gio bi bao.
    assert _quet("def test_x():\n    assert 1 == 1\n", "t.py") == []


def test_ba_phep_kiem_nang_da_biet_deu_dang_duoc_rao():
    """Chot dich danh ba cho pha 04 vua rao. Doi tuong, khong phai so luong.

    ⭐ `test_401` da hoc bai nay: chot mot con so thi con so do dung ngay ca khi
       ai do rao nham cai khac. Chot dung ba cai TEN thi khong.
    """
    mong_doi = {
        ("test_406_asv_tach_tieng.py", "test_tach_nguon_ra_du_BON_stem"),
        ("test_406_asv_tach_tieng.py", "test_tron_nen_ra_dung_dinh_dang_va_am_luong"),
        ("test_407_asv_chep_loi.py", "test_engine_ASR_that_chay_duoc"),
    }
    for ten_tep, ten_ham in mong_doi:
        cay = ast.parse((TESTS / ten_tep).read_text(encoding="utf-8"))
        ham = next((f for f in ast.walk(cay)
                    if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and f.name == ten_ham), None)
        assert ham is not None, f"{ten_tep}::{ten_ham} bien mat"
        assert "CHI_KHI_BAT" in _ten_trong_decorator(ham), (
            f"{ten_tep}::{ten_ham} mat rao chan — no goi engine that")


def test_rao_chan_MAC_DINH_la_bo_qua():
    """Bien moi truong chu khong phai co `-m`: mac dinh phai an toan.

    🔴 Mot marker chi loc khi co nguoi go `-m "not nang"`. Ai quen go la model
       that chay lai, va "ai do quen" chinh la kich ban da lam sap may hai lan.
    """
    import os

    from tests import rao_chan_nang

    assert rao_chan_nang.BIEN == "LTT_TEST_NANG"
    assert rao_chan_nang.bat() == bool(os.environ.get("LTT_TEST_NANG", "").strip())
    # Marker van co, de CHON (`-m nang`) — nhung no khong phai thu dang chan.
    assert rao_chan_nang.NANG.name == "nang"


def test_marker_nang_da_duoc_khai_trong_pytest_ini():
    """Marker chua khai sinh `PytestUnknownMarkWarning`, va canh bao thi bi bo qua."""
    ini = (GOC / "pytest.ini").read_text(encoding="utf-8")
    assert "nang:" in ini
    # ⛔ `addopts` an trong ini se doi hanh vi cua `gate.py` va `test_nhanh.py`
    #    ma khong ai thay trong lenh. Khong duoc co.
    #
    # 🔴 Doc theo DONG, khong quet chuoi con. Ban dau day la `"addopts" not in ini`
    #    va no do — vi chinh dong comment ngay tren chua tu do. Lan thu ba trong
    #    mot phien mot bo do bat duoc loi van giai thich chinh no; xem pha 02.
    khai = [d.split("=")[0].strip() for d in ini.splitlines()
            if d.strip() and not d.lstrip().startswith("#") and "=" in d]
    assert "addopts" not in khai, f"pytest.ini dat addopts an: {khai}"


@pytest.mark.parametrize("ten,ly_do", sorted(HAM_NANG.items()))
def test_moi_ham_trong_danh_sach_nang_deu_co_ly_do(ten, ly_do):
    """Mot danh sach cam khong ly do la mot danh sach khong ai dam sua.

    ⚠️ `assign_speakers` da tung nam trong danh sach nay o ban dau, chi vi no o
       cung tep voi `diarize_file`. No la 12 dong so hoc khoang thoi gian
       (`ai_workflows.py:77`) va khong nap gi ca. **Gan nhau khong phai bang
       chung.** Yeu cau mot ly do la thu bat duoc dieu do.
    """
    assert len(ly_do) > 20, f"{ten} thieu ly do doc duoc"


# ══════════════════════════════════════════════════════════════════════════════
#  Bo bat bien V4 (tang 2 cua V4_TEST_REVIEW_PROTOCOL)
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_bat_bien_tang_2_deu_co_MOT_TEP_chung_minh():
    """Ban do bat-bien -> tep phai tro toi tep co that.

    ⛔ Mot ban do tro toi mot tep da bi xoa la mot bat bien khong ai chung minh
       nua, va no im lang: bo test van xanh, chi la no khong con kiem thu do.
    """
    from tests import bo_bat_bien_v4 as bo

    thieu = sorted({t for t in bo.BAT_BIEN.values() if not (GOC / t).exists()})
    assert thieu == [], f"bat bien tro toi tep khong ton tai: {thieu}"

    # `V4_TEST_REVIEW_PROTOCOL` liet ke 12 bat bien bat buoc.
    assert len(bo.BAT_BIEN) >= 12


def test_hai_vong_deu_ton_tai_va_vong_DU_bao_trum_vong_NHANH():
    """Vong nhanh la mot TAP CON, khong phai mot danh sach khac.

    ⭐ Neu hai vong troi ra khoi nhau, "chay vong nhanh" khong con la mot buoc
       trung gian tren duong toi vong du — no thanh mot phep do khac han, va hai
       phep do khac nhau cung goi la "bat bien" la cach chac chan de doc nham
       mot ket qua xanh.
    """
    from tests import bo_bat_bien_v4 as bo

    assert set(bo.VONG_NHANH) < set(bo.VONG_DU)
    for t in bo.VONG_DU:
        assert (GOC / t).exists(), f"vong du tro toi tep khong ton tai: {t}"


def test_moi_tep_trong_ban_do_deu_nam_trong_vong_DU():
    """Khai mot bat bien roi khong chay no la mot loi hua, khong phai mot phep kiem."""
    from tests import bo_bat_bien_v4 as bo

    ngoai = sorted(set(bo.BAT_BIEN.values()) - set(bo.VONG_DU))
    assert ngoai == [], (
        f"bat bien duoc khai nhung khong tep nao trong VONG_DU chay chung: {ngoai}")
