"""Tốc độ HẬU KỲ: điều khiển thật, và ba ràng buộc quanh nó.

## Vì sao nó KHÔNG vi phạm Q119

Chú thích cũ ở `ltt_voice_studio.html` viết *"DELIVERY STYLE (tốc độ + phong
cách) — ⛔ Q119 CẤM phơi ra"*. Đọc lại Q119 thì đó là một **trích dẫn sai**:
Q119 ① nêu đích danh năm tham số — `temperature`, `top_k`, `top_p`,
`repetition_penalty`, `repetition_window` — và không có "tốc độ". Cả hai lý do
của nó (cache CUDA graph khoá theo `(B, temperature, top_k, top_p)`; tông lệch
do `temperature`, upstream #173) đều chỉ nói về đường LẤY MẪU.

⇒ Bộ chốt này giữ ranh giới ấy: tốc độ được phơi ra, năm tham số kia thì không.
"""
from __future__ import annotations

import pytest

from apps.ltt_voice import features, toc_do


def test_hop_le_ep_ve_khoang_va_KHONG_nem():
    """Một tham số hỏng không được làm hỏng cả job."""
    assert toc_do.hop_le(99) == toc_do.TOC_DO_MAX
    assert toc_do.hop_le(0.01) == toc_do.TOC_DO_MIN
    for xau in ("abc", None, "", [], float("nan"), float("inf")):
        assert toc_do.hop_le(xau) == 1.0, xau


def test_KHONG_goi_ffmpeg_khi_khong_can_doi():
    """1.00× vẫn giải mã + mã hoá lại toàn bộ sóng âm nếu không chặn."""
    assert not toc_do.can_doi(1.0)
    assert not toc_do.can_doi("abc")
    assert toc_do.can_doi(1.25)
    goc = b"RIFF____WAVE_gia_lap"
    assert toc_do.ap_dung(goc, 1.0) is goc


def test_hong_thi_TRA_NGUYEN_BAN_chu_khong_nem():
    """Tới đây tiếng ĐÃ SINH và khách ĐÃ BỊ TÍNH TIỀN.

    Biến một lỗi hậu kỳ thành một job hỏng là thu tiền cho một việc rồi vứt kết
    quả của nó đi.
    """
    rac = b"khong phai wav"
    assert toc_do.ap_dung(rac, 1.5) == rac


def test_cac_nac_deu_nam_trong_khoang():
    for n in toc_do.CAC_NAC:
        assert toc_do.hop_le(n) == n, f"nac {n} bi `hop_le` ep sang gia tri khac"
    assert 1.0 in toc_do.CAC_NAC, "phai co nac 'khong doi'"


def test_yeu_cau_doc_toc_do_va_KHONG_tin_dau_vao():
    yc = features.chuan_hoa({"text": "xin chao", "preset": "Adam",
                             "toc_do": "1.25"})
    assert yc.toc_do == 1.25
    for xau in ("abc", None, 99, -3):
        yc = features.chuan_hoa({"text": "xin chao", "preset": "Adam",
                                 "toc_do": xau})
        assert toc_do.TOC_DO_MIN <= yc.toc_do <= toc_do.TOC_DO_MAX, xau


def test_KHONG_doi_toc_do_thi_KHONG_them_truong_vao_lich_su():
    """Thêm hai trường luôn-luôn-có để phục vụ một ca hiếm là làm nặng tất cả."""
    yc = features.chuan_hoa({"text": "xin chao", "preset": "Adam"})
    r = features.KetQua(yeu_cau=yc, audio_key="k", giay=10.0,
                        text_da_chuan_hoa="xin chao").as_result()
    assert "toc_do" not in r and "duration_played_s" not in r


def test_TIEN_tinh_theo_ban_GOC_khong_theo_ban_da_tang_toc():
    """🔴 Ràng buộc TIỀN, và nó là một lỗ khai thác được nếu làm sai.

    Ở 1,5× tệp ngắn đi một phần ba. Tính tiền theo thời lượng tệp là để khách
    chọn tốc độ nhanh trả ít hơn cho **cùng một lượng việc GPU**.
    """
    yc_thuong = features.chuan_hoa({"text": "xin chao", "preset": "Adam"})
    yc_nhanh = features.chuan_hoa({"text": "xin chao", "preset": "Adam",
                                   "toc_do": "1.5"})
    thuong = features.KetQua(yeu_cau=yc_thuong, audio_key="k", giay=30.0,
                             text_da_chuan_hoa="x").as_result()
    nhanh = features.KetQua(yeu_cau=yc_nhanh, audio_key="k", giay=30.0,
                            giay_phat=20.0, text_da_chuan_hoa="x").as_result()
    assert nhanh["credit_cost"] == thuong["credit_cost"], (
        "tang toc lam RE tien di — day la mot lo khai thac, khong phai uu dai")
    assert nhanh["duration_s"] == 30.0, "duration_s la co so TINH TIEN"
    assert nhanh["duration_played_s"] == 20.0, "do dai TEP khach nhan"


def test_NAM_THAM_SO_LAY_MAU_van_khong_ra_hop_dong():
    """Ranh giới Q119 vẫn nguyên: tốc độ ra, năm tham số kia thì không."""
    yc = features.chuan_hoa({
        "text": "xin chao", "preset": "Adam",
        "temperature": 1.4, "top_k": 99, "top_p": 0.1,
        "repetition_penalty": 2.0, "repetition_window": 8})
    for cam in ("temperature", "top_k", "top_p",
                "repetition_penalty", "repetition_window"):
        assert not hasattr(yc, cam), (
            f"`{cam}` lot vao YeuCau — Q119 khoa nam tham so lay mau nay")
