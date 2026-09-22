"""ASV final — chuan hoa hai ve truoc WER/CER (`apps/asv_gpu/do_luong/chuan_hoa_loi`).

Luat duoc chot: MOT ham cho ca kich ban va ban ASR. Moi cach viet cung mot loi
doc (so/chu, hoa/thuong, dau cau, tu dien ten rieng) phai ra CUNG mot chuoi —
neu khong WER do su khac nhau cua cach viet chu khong do loi doc.
"""
from __future__ import annotations

import importlib.util

import pytest

from apps.asv_gpu.do_luong import chuan_hoa_loi as ch


@pytest.mark.parametrize("a,b", [
    ("Năm 2024 có 23 người.", "năm hai nghìn không trăm hai mươi tư có hai mươi ba người"),
    ("Xin chào, CÁC BẠN!", "xin chào các bạn"),
    ("Giá 15%", "giá mười lăm phần trăm"),
    ("  nhiều   khoảng   trắng ", "nhiều khoảng trắng"),
])
def test_vi_hai_cach_viet_CUNG_mot_loi_doc_ra_cung_chuoi(a, b):
    assert ch.chuan_hoa(a, "vi") == ch.chuan_hoa(b, "vi")


def test_vi_GIU_dau_thanh_vi_dau_thanh_la_nghia():
    assert ch.chuan_hoa("ma", "vi") != ch.chuan_hoa("mà", "vi")
    assert "mà" in ch.chuan_hoa("Mà!", "vi")


def test_vi_KHONG_xoa_noi_dung_trong_ngoac_vi_may_doc_DOC_no():
    """Whisper BasicTextNormalizer xoa `(...)`; o day kich ban co "(Hà Nội)" va
    may doc doc no — xoa o ve tham chieu la sinh loi chen gia."""
    assert ch.chuan_hoa("Thủ đô (Hà Nội)", "vi") == "thủ đô hà nội"


def test_vi_tu_dien_ten_rieng_ap_CA_HAI_ve():
    tu = {"LTT": "eo tê tê"}
    assert ch.chuan_hoa("LTT xin chào", "vi", tu) == ch.chuan_hoa("eo tê tê xin chào", "vi", tu)


def test_vi_token_la_AM_TIET():
    assert ch.chuan_hoa("Hôm nay trời đẹp", "vi").split() == ["hôm", "nay", "trời", "đẹp"]


@pytest.mark.skipif(importlib.util.find_spec("transformers") is None,
                    reason="EnglishTextNormalizer can transformers")
def test_en_dung_EnglishTextNormalizer_cua_whisper():
    assert (ch.chuan_hoa("It's 23 dollars, Mr. Smith!", "en")
            == ch.chuan_hoa("it is twenty three dollars mister smith", "en"))


@pytest.mark.skipif(importlib.util.find_spec("jiwer") is None,
                    reason="jiwer chi co trong qc-venv")
def test_cham_wer_cer_va_tham_chieu_rong():
    r = ch.cham("mot hai ba bon", "mot hai bon", "vi")
    assert r["wer"] == 0.25 and r["xoa"] == 1 and "cer" in r
    assert ch.cham("", "gi do", "vi") == {"bo_qua": "tham chieu rong sau chuan hoa"}
    assert ch.cham("a b", "", "en")["wer"] == 1.0
