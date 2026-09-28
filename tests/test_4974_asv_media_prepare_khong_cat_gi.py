"""P0-c — `media_prepare` ⛔ KHONG cat gi: ⛔ khong cua so khach, ⛔ khong cat canh.

## Hai phan quyet, va bai nay ghim CA HAI

    25/09  `ke_cat.py:1-20`  — CAT CANH o GIAI DOAN 2, tren MP4 DA XONG
    28/09  chu du an          — "cat dau duoi ho lam dau la dung neu chi 1 lan render"

Phan quyet 28/09 noi ve **so lan encode**, va §1 cua
`B17_PLAN_TRIEN_KHAI_THEO_VIRAL.md` da do: ta **da** chi encode hinh MOT lan
(`che_do_render.py:133-143`). ⇒ Dieu 28/09 doi hoi **da co**, va no ⛔ khong doi
hoi cat som.

Bai nay do ba bat bien ma mot lan doi "cat som" se pha, tung cai mot:

    1. ban goc ⛔ khong bi cham        — bam tep nguon truoc/sau `chay()`
    2. `audio_full.wav` DUNG la FULL   — do dai = do dai nguon
    3. `media_prepare` ⛔ khong goi duong cat — AST, ⛔ khong grep chuoi
    4. DUNG MOT artifact `.wav`        — xem `test_4976` ve vi sao con so 1 la luat
"""
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import giai_doan_media, nhap_media  # noqa: E402
from platform_core.storage import LocalStorage  # noqa: E402
from tests.fixtures import asv_media as fx  # noqa: E402

GOC = Path(__file__).resolve().parents[1]
TEP_MEDIA = GOC / "apps" / "auto_scan_video" / "giai_doan_media.py"

#: Ten cac cho CAT — ⛔ khong mot cai nao duoc xuat hien trong `giai_doan_media`.
MODULE_CAT = ("cat_dau_cuoi", "ke_cat", "ban_do_thoi_gian")

#: Ham thi hanh phep cat canh (`che_do_render`). Neu `media_prepare` goi mot
#: trong so nay thi phan quyet 25/09 da bi pha ma ⛔ khong ai phai sua mot tep
#: tai lieu nao.
HAM_CAT_CANH = ("loc_cat_hai_dong", "loc_cat_noi", "chon", "giao")


class _RunGia:
    """Toi thieu dung nhung truong `giai_doan_media.chay` doc."""

    def __init__(self, khoa: str):
        self.id = "run-p0c-4974"
        self.owner_id = "uA"
        self.source_key = khoa
        self.contract_version = "v4"


# ══════════════════════════════════════════════════════════════════════════════
#  1 + 2 + 4 — mot luot `chay()` THAT
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def luot(tmp_path):
    fx.require_ffmpeg()
    kho = LocalStorage(str(tmp_path / "kho"))
    khoa = fx.nap_nguon_vao_kho(kho, tmp_path, duration_s=4.0)
    run = _RunGia(khoa)
    duong_nguon = kho.local_path(khoa)
    assert duong_nguon, "LocalStorage phai cho duong that"
    bam_truoc = hashlib.sha256(Path(duong_nguon).read_bytes()).hexdigest()
    ket = giai_doan_media.chay(None, kho, run=run, ctx=None)
    return kho, khoa, duong_nguon, bam_truoc, ket


def test_ban_goc_KHONG_bi_cham__bam_tep_nguon_khong_doi(luot):
    """⭐ Docstring `giai_doan_media.py:13-14` la mot loi hua; bai nay la phep do.

    Mat ban goc la mat kha nang tinh lai moi thu ha nguon — nen ke ca mot lan
    doi "cat som" duoc chap thuan, no van ⛔ khong duoc ghi len khoa nguon.
    """
    _kho, _khoa, duong_nguon, bam_truoc, _ket = luot
    bam_sau = hashlib.sha256(Path(duong_nguon).read_bytes()).hexdigest()
    assert bam_sau == bam_truoc


def test_audio_full_DUNG_la_full__do_dai_bang_do_dai_nguon(luot):
    """🔴 Neu mot ngay nao do bai nay do, mot trong hai dieu da xay ra:

       · phep cat da duoc doi vao `media_prepare` **ma ten tep van la `full`**
         ⇒ ten NOI DOI, va do la lop loi kho nay bi nhieu nhat;
       · hoac phep tach tieng da doi hanh vi.

    ⇒ Sua bai nay thi phai doi **ten artifact**, ⛔ khong phai noi con so.
    """
    kho, khoa, duong_nguon, _bam, ket = luot
    tt_nguon = nhap_media.soi(duong_nguon)
    khoa_wav = [p["staging_key"] for p in ket["phan"] if p["duoi"] == "wav"]
    assert len(khoa_wav) == 1
    duong_wav = kho.local_path(khoa_wav[0])
    tt_wav = nhap_media.soi(duong_wav)
    # 0,10 s: AAC ket thuc o bien khung, nen container nguon va WAV PCM lech
    # duoi mot khung tieng. Mot phep cat 5 % cua bo moc that la 13,75 s.
    assert tt_wav["thoi_luong"] == pytest.approx(tt_nguon["thoi_luong"], abs=0.10)


def test_ho_so_soi_khai_do_dai_NGUON__khong_do_dai_da_cat(luot):
    """`tom_tat["thoi_luong"]` la thu `giai_doan_thoi_gian.py:314-318` doc lam
    `tong_giay` cho CA ke hoach thoi gian. Mot con so da cat o day dich truc
    cua moi giai doan sau no."""
    _kho, _khoa, duong_nguon, _bam, ket = luot
    tt_nguon = nhap_media.soi(duong_nguon)
    assert ket["tom_tat"]["thoi_luong"] == pytest.approx(tt_nguon["thoi_luong"])


# ══════════════════════════════════════════════════════════════════════════════
#  3 — AST: ⛔ khong mot duong cat nao di qua `media_prepare`
# ══════════════════════════════════════════════════════════════════════════════

def _cay():
    return ast.parse(TEP_MEDIA.read_text(encoding="utf-8"))


def _ten_duoc_import(cay) -> set[str]:
    ra: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom):
            ra.update(a.asname or a.name for a in n.names)
        elif isinstance(n, ast.Import):
            ra.update((a.asname or a.name).split(".")[0] for a in n.names)
    return ra


def _ten_ham_duoc_goi(cay) -> set[str]:
    ra: set[str] = set()
    for n in ast.walk(cay):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Attribute):
            ra.add(f.attr)
        elif isinstance(f, ast.Name):
            ra.add(f.id)
    return ra


def test_media_prepare_KHONG_import_mot_module_cat_nao():
    """⛔ AST chu ⛔ khong grep: mot chuoi `"ke_cat"` trong mot chu thich (nhu
    chinh tep nay co) ⛔ khong phai mot phep goi."""
    da_import = _ten_duoc_import(_cay())
    assert not (da_import & set(MODULE_CAT)), sorted(da_import & set(MODULE_CAT))


def test_media_prepare_KHONG_goi_duong_cat_canh():
    """Chot phan quyet 25/09 bang MAY: cat canh o GD2, ⛔ khong o day."""
    da_goi = _ten_ham_duoc_goi(_cay())
    assert not (da_goi & set(HAM_CAT_CANH)), sorted(da_goi & set(HAM_CAT_CANH))


def test_media_prepare_KHONG_doc_cai_dat_cua_khach():
    """⭐ Cua so khach den tu `cai_dat.doc(run).cat`
    (`giai_doan_hinh_anh.py:258-260`). `media_prepare` ⛔ khong doc `cai_dat` —
    nen bai nay la **cua vao** cua moi lan doi "cat som", va no do su VANG MAT
    cua mot phep doc, ⛔ khong do mot phep tinh co the sai.
    """
    assert "cai_dat" not in _ten_duoc_import(_cay())
    assert "doc" not in _ten_ham_duoc_goi(_cay())
