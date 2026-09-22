"""Chuan hoa van ban truoc khi cham WER/CER — CUNG MOT ham cho CA HAI ve.

## Luat: mot ham, hai ve

WER do "may doc co doc dung kich ban khong". Kich ban viet `23`, may doc
"hai muoi ba", ASR chep lai `23` hoac "hai mươi ba" tuy tam trang. Neu hai ve
di qua hai phep chuan hoa khac nhau, WER do SU KHAC NHAU CUA HAI PHEP CHUAN HOA,
khong phai loi doc. Nen `chuan_hoa(chu, ngon_ngu, tu_dien)` duoc goi dung nhu
nhau cho kich ban (tham chieu) va cho ban ASR (gia thuyet).

## Tieng Viet — be mat da khai cua LTT Voice

    text_pipeline.chuan_hoa(chu, doc_so_tran=True, tu_dien_rieng=tu_dien)
      -> chu thuong, bo dau cau/ky hieu (loai Unicode P*, S*), gon khoang trang

⭐ `text_pipeline.chuan_hoa` la CHINH ham ASV goi truoc khi dua chu cho may doc
   (`giong_noi.chuan_hoa_van_ban`, be mat lien-app da khai). `doc_so_tran=True`
   (may doc dung `False`) doc NOT ca so nho thanh chu — tuc sau buoc nay ca hai
   ve deu "hai mươi ba", bat ke ve nao viet so. Tu dien ten rieng cua khach di
   qua ca hai ve, nen "CPU"/"xi pi diu" khong thanh loi.
⭐ Buoc sau la loi cua `BasicTextNormalizer` (Whisper, OpenAI — chuan cham ASR
   da dung o bang Open ASR Leaderboard): NFKC, chu thuong, thay loai Unicode
   M/S/P bang khoang trang. Khac DUY NHAT, co y: KHONG xoa noi dung trong ngoac
   `(...)`/`[...]`. Whisper xoa de bo nhan "[Music]" cua chinh no; o day kich ban
   co the co "(Hà Nội)" va may doc DOC no, nen xoa o ve tham chieu ma ASR van
   chep lai la sinh loi chen gia. Va giu dau thanh (khong `remove_diacritics`):
   dau thanh la nghia trong tieng Viet.
   Token sau buoc nay la **am tiet** (chinh ta tieng Viet cach tung am tiet) —
   WER tieng Viet o day la WER tren am tiet.

## Tieng Anh — `EnglishTextNormalizer` cua Whisper

Chuan cham WER tieng Anh cua Whisper (so -> chu so, viet tat, "Mr" -> "mister",
dau cau). Bang doi chinh ta Anh-My de RONG: kich ban va ASR deu mot phia.

⛔ Ham nay KHONG goi model, KHONG doc mang. Chay duoc o venv san pham (phan
   tieng Viet) va trong `qc-venv` (runner goi no).
"""
from __future__ import annotations

import re
import unicodedata

#: Doi khi doi bat cu phep nao o duoi. Vao phien ban bo do `giong`.
PHIEN_BAN_CHUAN_HOA = 1

_KHOANG = re.compile(r"\s+")


def _bo_dau_cau(s: str) -> str:
    """Loi `BasicTextNormalizer.remove_symbols` (Whisper), giu dau thanh."""
    s = unicodedata.normalize("NFKC", s)
    return "".join(" " if unicodedata.category(c)[0] in "MSP" else c for c in s)


def chuan_hoa(chu: str, ngon_ngu: str, tu_dien: dict | None = None) -> str:
    """Van ban -> chuoi token cach nhau MOT khoang trang. Rong neu khong con gi."""
    chu = str(chu or "")
    nn = str(ngon_ngu or "").lower()
    if nn == "en":
        from transformers.models.whisper.english_normalizer import (
            EnglishTextNormalizer)
        return _KHOANG.sub(" ", EnglishTextNormalizer({})(chu)).strip()
    if nn == "vi":
        from apps.ltt_voice import text_pipeline
        chu = text_pipeline.chuan_hoa(chu, doc_so_tran=True,
                                      tu_dien_rieng=tu_dien or None)
    return _KHOANG.sub(" ", _bo_dau_cau(chu.casefold())).strip()


def cham(tham_chieu: str, gia_thuyet: str, ngon_ngu: str) -> dict:
    """WER (+ CER cho tieng Viet) tren hai chuoi DA chuan hoa. Can `jiwer`.

    Tham chieu rong ⇒ `{"bo_qua": ...}`: WER khong xac dinh (chia cho 0), va mot
    doan khong co chu thi khong co gi de doc sai.
    """
    import jiwer

    if not tham_chieu:
        return {"bo_qua": "tham chieu rong sau chuan hoa"}
    gt = gia_thuyet or ""
    w = jiwer.process_words(tham_chieu, gt) if gt else None
    so_tu = len(tham_chieu.split())
    ra = {
        "wer": round(float(w.wer) if w else 1.0, 4),
        "so_tu": so_tu,
        "thay": int(w.substitutions) if w else 0,
        "xoa": int(w.deletions) if w else so_tu,
        "chen": int(w.insertions) if w else 0,
    }
    if str(ngon_ngu or "").lower() == "vi":
        ra["cer"] = round(float(jiwer.cer(tham_chieu, gt)) if gt else 1.0, 4)
    return ra
