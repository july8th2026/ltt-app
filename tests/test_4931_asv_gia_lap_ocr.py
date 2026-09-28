"""B13 việc C3 — `rao_chan_nang.gia_lap_ocr` phải chặn ĐÚNG ở `co_san()`, ⛔
không nạp RapidOCR thật, và ⛔ không đụng vào `_hop_cua_khung`/`_may()`.

Phép kiểm ở đây CHẠY NHANH, ⛔ không dùng ffmpeg/video thật — chỉ kiểm điểm
chặn, đúng khuôn các bài `test_BB4_*` của
`tests/test_4895_asv_do_vung_tang_ocr.py`.
"""
from __future__ import annotations

from apps.auto_scan_video import do_vung, do_vung_ocr
from tests.rao_chan_nang import gia_lap_ocr


def test_gia_lap_ocr_tat_co_san(monkeypatch):
    monkeypatch.setattr(do_vung_ocr, "co_san", lambda: True)  # gia bo da cai
    gia_lap_ocr(monkeypatch)
    assert do_vung_ocr.co_san() is False


def test_gia_lap_lam_dai_chu_nhieu_tang_LUI_ve_do_dai_chu_KHONG_goi_OCR_that(
        monkeypatch):
    """Bài CHÍNH: chứng minh sau khi giả lập, một lượt gọi `_dai_chu_nhieu_tang`
    (đúng đường `de_xuat` đi qua) ⛔ không bao giờ chạm `do_vung_ocr.
    do_dai_chu_ocr` thật — nếu chạm, test tự nổ ngay tại chỗ."""
    goi: list[int] = []
    gia_lap_ocr(monkeypatch)

    def no_neu_goi(*a, **k):
        raise AssertionError(
            "OCR that KHONG duoc goi khi da gia lap co_san()=False")

    monkeypatch.setattr(do_vung_ocr, "do_dai_chu_ocr", no_neu_goi)
    monkeypatch.setattr(
        do_vung, "do_dai_chu",
        lambda *a, **k: goi.append(1) or do_vung.KetQua((), 4))

    kq = do_vung._dai_chu_nhieu_tang("x.mp4")

    assert goi == [1], "lui tang KHONG xay ra — de_xuat se nap OCR that"
    assert kq.so_khung == 4


def test_gia_lap_ocr_TON_TRONG_ket_qua_tang_lui_that(monkeypatch):
    """Vế đối chứng: tầng lùi (`do_dai_chu`, biến thiên điểm ảnh — 0 model)
    vẫn CHẠY THẬT và trả kết quả CỦA NÓ, ⛔ bị fixture ghi đè bằng một giá trị
    giả tuỳ tiện — `gia_lap_ocr` chỉ tắt MỘT nhánh (`co_san`), không thay thế
    `do_dai_chu`."""
    import pytest

    gia_lap_ocr(monkeypatch)
    # `do_dai_chu` that se NEM DoVungLoi vi khong mo duoc video gia — dung
    # hanh vi that cua ham that, ⛔ khong phai mot gia tri fixture bia ra.
    # (Kiem qua ham that, khong qua monkeypatch, nen day la mot phep do THAT.)
    with pytest.raises(do_vung.DoVungLoi):
        do_vung._dai_chu_nhieu_tang("khong_ton_tai_cho_nao.mp4")
