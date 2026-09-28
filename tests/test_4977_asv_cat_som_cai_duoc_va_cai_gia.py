"""P0-c — CAI DUOC va CAI GIA cua "cat dau o `media_prepare`", do bang so.

⛔ Tep nay ⛔ **khong** thi hanh phep cat o `media_prepare` (xem `test_4974`). No
do hai dai luong de ket luan cua lan P0-c dung tren SO, ⛔ khong tren loi:

    CAI DUOC  phan vat lieu ASR ⛔ khong phai nghe = `1 - (den - tu)` cua do dai
              (voi bo moc that `[0,05 ; 0,95]`: **10 %**)
    CAI GIA   so cho ha nguon phai doi truc, do o `test_4975` (**5** module doc
              ban goc) + so lan ap cua so phai bo (**2**, `test_4973`)

⭐ Va bai o duoi chung minh phan **CO HOC** cua phep cat la **tam thuong**:
   `-ss`/`-to` cho ra dung do dai cua so, ⛔ khong cham ban goc. ⇒ Cai chan lan
   P0-c ⛔ **khong** phai "cat kho", ma la **day dien truc**.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import cat_dau_cuoi, nhap_media  # noqa: E402
from tests.fixtures import asv_media as fx  # noqa: E402

CUA_SO = (0.05, 0.95)
DAI_S = 20.0


def _wav_16k(ff: str, nguon: Path, dich: Path, *, ss=None, to=None) -> Path:
    """Dung CHINH bo tham so `nhap_media.tach_tieng_cho_asr` dung, cong `-ss`/`-to`.

    ⚠️ `-ss`/`-to` dat SAU `-i` (loc thay vi tim): mot `-ss` truoc `-i` nhay ve
       khung khoa gan nhat, nen do dai ra lech vai chuc mili-giay theo NGUON —
       tuc dung bien the "nhanh" o day se lam bai nay do mot dai luong khac.
    """
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(nguon)]
    if ss is not None:
        cmd += ["-ss", f"{ss:.6f}"]
    if to is not None:
        cmd += ["-to", f"{to:.6f}"]
    cmd += ["-vn", "-ac", str(nhap_media.SO_KENH_ASR),
            "-ar", str(nhap_media.TAN_SO_ASR), "-c:a", "pcm_s16le", str(dich)]
    subprocess.run(cmd, check=True, capture_output=True)
    return dich


@pytest.fixture()
def nguon(tmp_path):
    fx.require_ffmpeg()
    return fx.tiny_mp4(tmp_path / "nguon.mp4", duration_s=DAI_S)


def test_co_hoc_cua_phep_cat_la_tam_thuong__do_dai_ra_DUNG_bang_cua_so(nguon, tmp_path):
    """Cat ra dung do dai cua so — nen ket luan "⛔ khong nen lam" ⛔ khong duoc
    dua tren "cat kho"."""
    ff = fx.require_ffmpeg()
    tt = nhap_media.soi(str(nguon))
    T = float(tt["thoi_luong"])

    cua = cat_dau_cuoi.chuan_hoa(CUA_SO)
    tu, den = cua[0] * T, cua[1] * T

    full = _wav_16k(ff, nguon, tmp_path / "full.wav")
    cat = _wav_16k(ff, nguon, tmp_path / "cat.wav", ss=tu, to=den)

    dai_full = float(nhap_media.soi(str(full))["thoi_luong"])
    dai_cat = float(nhap_media.soi(str(cat))["thoi_luong"])

    # 1 khung PCM 16 kHz = 0,0000625 s; 0,02 s la bien cho bien khung AAC nguon.
    assert dai_cat == pytest.approx(den - tu, abs=0.02)
    assert dai_cat / dai_full == pytest.approx(CUA_SO[1] - CUA_SO[0], abs=0.01)


def test_cai_duoc__vat_liet_ASR_giam_DUNG_10_phan_tram(nguon, tmp_path):
    """⭐ Cai duoc la **tuyen tinh theo cua so**, ⛔ khong hon: PCM 16 kHz mot kenh
    la 32 kB/s deu, nen so byte ti le dung voi thoi gian ASR phai nghe.
    """
    ff = fx.require_ffmpeg()
    full = _wav_16k(ff, nguon, tmp_path / "full.wav")
    tt = nhap_media.soi(str(nguon))
    T = float(tt["thoi_luong"])
    cua = cat_dau_cuoi.chuan_hoa(CUA_SO)
    cat = _wav_16k(ff, nguon, tmp_path / "cat.wav",
                   ss=cua[0] * T, to=cua[1] * T)

    ti_le = cat.stat().st_size / full.stat().st_size
    assert ti_le == pytest.approx(CUA_SO[1] - CUA_SO[0], abs=0.01)
    # ⇒ Tiet kiem 10 %, va ⛔ KHONG hon: mot lan ASR ngan hon 10 % la 10 % cua
    #    mot buoc, ⛔ khong phai 10 % cua ca chuoi 13 giai doan.
    assert 1.0 - ti_le == pytest.approx(0.10, abs=0.01)


def test_cat_KHONG_cham_ban_goc__bam_tep_nguon_khong_doi(nguon, tmp_path):
    """Dieu (1) cua brief — de, va bai nay chot no du phep cat co duoc lam hay
    khong: `-ss`/`-to` ghi ra tep MOI."""
    ff = fx.require_ffmpeg()
    truoc = hashlib.sha256(nguon.read_bytes()).hexdigest()
    tt = nhap_media.soi(str(nguon))
    T = float(tt["thoi_luong"])
    cua = cat_dau_cuoi.chuan_hoa(CUA_SO)
    _wav_16k(ff, nguon, tmp_path / "cat.wav", ss=cua[0] * T, to=cua[1] * T)
    assert hashlib.sha256(nguon.read_bytes()).hexdigest() == truoc


def test_ten_audio_full_se_NOI_DOI__nen_phuong_an_la_(nguon, tmp_path):
    """🔑 Ghim tieu chi chon (a)/(b) cua brief: *dai luong ha nguon doc duoc co
    con tu mo ta dung ⛔ khong*.

    Mot tep ten `audio_full.wav` ma do dai chi bang 90 % nguon la mot **ten noi
    doi**, va ha nguon ⛔ khong co cach nao biet: `nhap_media.soi` tra do dai
    THAT cua no, ⛔ khong tra "toi da bi cat 13,75 s".
    """
    ff = fx.require_ffmpeg()
    tt = nhap_media.soi(str(nguon))
    T = float(tt["thoi_luong"])
    cua = cat_dau_cuoi.chuan_hoa(CUA_SO)
    noi_doi = _wav_16k(ff, nguon, tmp_path / "audio_full.wav",
                       ss=cua[0] * T, to=cua[1] * T)
    ho_so = nhap_media.soi(str(noi_doi))
    assert noi_doi.name == "audio_full.wav"
    assert float(ho_so["thoi_luong"]) < T - 1.0
    # ⛔ Va ⛔ khong mot truong nao trong ho so soi ke ra `dau_cat`.
    assert not [k for k in ho_so if "cat" in k or "offset" in k]
