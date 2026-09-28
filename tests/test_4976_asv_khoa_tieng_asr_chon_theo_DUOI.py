"""P0-c — `_khoa_tieng_asr` chon ban tieng **theo DUOI `.wav`**, ⛔ khong theo truc.

## Vi sao bai nay quyet dinh ca lan P0-c

Cach "nhe" nhat de dat cua so khach vao `media_prepare` la **them** mot artifact
(`audio_asr.wav` = cua so) va **giu** `audio_full.wav` dung nghia *full* —
phuong an (a) trong brief. Bai nay do rang phuong an ay ⛔ **khong the lam mot
minh o `giai_doan_media.py`**:

    giai_doan_chep_loi.py:104-107
        for khoa in (truoc.outputs or {}).get("khoa_asset") or []:
            if khoa.endswith(".wav"):
                return khoa

⇒ Nguoi chon ban tieng cho ASR chon **tep `.wav` DAU TIEN trong danh sach**. Hai
  artifact `.wav` ⇒ mot **xo so ve TRUC**: ASR co the nhan ban da cat (moc lech
  `dau_cat`) hay ban full, tuy thu tu `khoa_asset` — va ⛔ khong mot phep kiem nao
  do duoc su khac biet ay, vi **ca hai deu la mot tep WAV hop le**.

⭐ Do la mot bien ⛔ khong duoc gac (`nen-tang-nghia-vu-ngam-va-be-mat-an`). Nen
   phuong an (a) buoc phai sua `giai_doan_chep_loi.py` — mot tep lan P0-c ⛔
   KHONG so huu.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import features, giai_doan_chep_loi, pipeline  # noqa: E402


class _GiaiDoanGia:
    def __init__(self, khoa_asset):
        self.outputs = {"khoa_asset": list(khoa_asset)}


class _RunGia:
    id = "run-p0c-4976"


@pytest.fixture()
def gieo(monkeypatch):
    """Thay `features.giai_doan_theo_ten` de khai `khoa_asset` tuy y."""
    def dat(khoa_asset):
        def gia(db, run_id, ten):
            assert ten == pipeline.MEDIA_PREPARE
            return _GiaiDoanGia(khoa_asset)
        monkeypatch.setattr(features, "giai_doan_theo_ten", gia)
    return dat


# ══════════════════════════════════════════════════════════════════════════════
#  Hom nay: DUNG mot `.wav` ⇒ phep chon la tat dinh
# ══════════════════════════════════════════════════════════════════════════════

def test_mot_wav_duy_nhat__chon_dung_no(gieo):
    gieo(["a/ho_so.json", "a/audio_full.wav"])
    assert giai_doan_chep_loi._khoa_tieng_asr(None, _RunGia()) == "a/audio_full.wav"


def test_khong_co_wav__NEM_chu_khong_im_lang(gieo):
    gieo(["a/ho_so.json"])
    with pytest.raises(giai_doan_chep_loi.ThieuBanTieng):
        giai_doan_chep_loi._khoa_tieng_asr(None, _RunGia())


# ══════════════════════════════════════════════════════════════════════════════
#  PHEP TIEM NGHICH — them mot `.wav` thu hai (phuong an (a) lam mot minh)
# ══════════════════════════════════════════════════════════════════════════════

def test_tiem_nghich__HAI_wav_thi_ASR_nhan_cai_DAU_TIEN_chu_khong_biet_truc(gieo):
    """🔴 Hai thu tu khac nhau ⇒ hai TRUC khac nhau, cung mot ma, ⛔ khong loi.

    Bai nay ⛔ **khong** doi hoi mot phep chon "dung"; no chot rang phep chon
    hien tai ⛔ khong he hoi ve truc. Do la ly do phuong an (a) ⛔ khong an toan
    khi lam mot minh trong `giai_doan_media.py`.
    """
    gieo(["a/audio_full.wav", "a/audio_asr_cat.wav"])
    assert giai_doan_chep_loi._khoa_tieng_asr(None, _RunGia()) == "a/audio_full.wav"

    # ⭐ Dao thu tu — **cung ma, cung du lieu, khac ket qua**.
    gieo(["a/audio_asr_cat.wav", "a/audio_full.wav"])
    assert giai_doan_chep_loi._khoa_tieng_asr(None, _RunGia()) == "a/audio_asr_cat.wav"


def test_phep_chon_KHONG_doc_ten_tep__nen_doi_ten_mot_minh_khong_cuu_duoc(gieo):
    """⛔ Doi ten `audio_full.wav` thanh `audio_cua_so.wav` ⛔ khong sua gi: dieu
    kien duy nhat la `.endswith(".wav")`.

    ⇒ Phuong an (b) — *giu ten, ghi offset vao `source_probe.json`* — cung ⛔
      khong cuu duoc: **⛔ khong mot ai** trong duong ASR doc `source_probe.json`
      de biet offset. Mot can gat dat duoc, doc lai duoc, ma ⛔ khong ai doc
      (`can-gat-dat-duoc-doc-lai-duoc-nhung-khong-ai-doc`).
    """
    gieo(["a/audio_cua_so.wav"])
    assert giai_doan_chep_loi._khoa_tieng_asr(None, _RunGia()) == "a/audio_cua_so.wav"
