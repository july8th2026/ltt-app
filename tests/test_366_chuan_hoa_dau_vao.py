"""Hai lỗi hình dạng đầu vào, tìm ra bằng cách đọc hộp thư lỗi của upstream.

## Vì sao cả hai đều là lỗi TIỀN

Không cái nào làm job hỏng. Job `done`, tệp có thật, thời lượng đúng, và
`credit_cost` tính theo **số giây thật sự sinh ra** — nên khách trả tiền đầy đủ
cho một bản thu đọc sai. Không dòng log nào được ghi.

  · **#119** — `"CHƯƠNG I"` bị engine đọc thành *"xê hát u ơ en giê"*. Tác giả
    upstream xác nhận: engine hiểu nhầm chữ viết hoa toàn bộ là từ viết tắt.
  · **#112** — `…` (U+2026) không được chuẩn hoá nên không có chỗ ngắt hơi.
    Upstream đã sửa `...` ở sea-g2p 0.6.8 nhưng `…` thì **chưa**.

## Vì sao bộ test cũ không thấy

Mọi phép kiểm chuẩn hoá trước đây gửi **văn bản sạch do chính ta viết**. Không ai
dán một quyết định hành chính hay một đoạn copy từ Word vào một test. Ba lỗi tìm
được hôm nay (#177, #119, #112) đều thuộc lớp đó — và không lỗi nào bị bắt bởi
test, cả ba đều bắt bằng cách đọc xem **người khác đưa gì vào cùng model này**.
"""
from __future__ import annotations

import pytest


def _ch(s: str) -> str:
    from apps.ltt_voice.text_pipeline import chuan_hoa
    return chuan_hoa(s)


# ═══════════════════════════════════ #112 · dấu ba chấm ═════════════════════

@pytest.mark.parametrize("vao", ["Anh ấy nói… rồi im lặng.",
                                 "Anh ấy nói... rồi im lặng.",
                                 "Anh ấy nói.... rồi im lặng."])
def test_dau_ba_cham_thanh_mot_dau_cham(vao):
    """`…` và `...` phải cùng về một dấu chấm — đó là chỗ engine ngắt hơi."""
    ra = _ch(vao)
    assert "…" not in ra, f"con ky tu U+2026 trong {ra!r}"
    assert "..." not in ra, f"con ba dau cham trong {ra!r}"
    assert ra.count(".") == 2, (
        f"{ra!r} — mong doi dung hai dau cham (mot thay cho dau ba cham, mot "
        f"ket cau)")


def test_nhieu_dau_ba_cham_lien_tiep_gop_lam_mot():
    """Hai dấu chấm cách nhau một khoảng trắng là hai câu rỗng, không phải một
    quãng nghỉ dài."""
    assert _ch("Chờ đã…… thế à?") == "Chờ đã. thế à?"


def test_dau_ba_cham_khong_dung_vao_dau_cham_thuong():
    assert _ch("Không có gì.") == "Không có gì."


# ═══════════════════════════════════ #119 · VIẾT HOA ════════════════════════

def test_viet_hoa_co_dau_bi_ha_xuong():
    """🔴 Ca chính: văn bản hành chính tiếng Việt.

    Tác giả upstream: *"nếu viết hoa toàn bộ như CHƯƠNG thì hệ thống đang hiểu
    nhầm là từ viết tắt nên mới đọc từng chữ cái."*
    """
    assert _ch("CHƯƠNG I. QUY ĐỊNH CHUNG") == "chương I. quy định chung"
    assert _ch("Điều 5. QUYẾT ĐỊNH này có hiệu lực") \
        == "Điều 5. quyết định này có hiệu lực"


def test_viet_tat_khong_dau_duoc_giu_nguyen():
    """⛔ Ngược lại: `RAM` viết hoa đang được đánh vần **đúng**.

    Hạ nó thành "ram" là sửa một lỗi bằng cách tạo ra lỗi ngược lại.
    """
    assert "RAM" in _ch("Xem mục CPU và RAM")
    assert _ch("Theo ISO 9001 và TCVN") == "Theo ISO 9001 và TCVN"


def test_tu_dien_viet_tat_van_khop_sau_khi_them_luat():
    """Phép hạ đặt SAU `tu_dien.ap_dung` — nếu đảo thứ tự thì `CPU` rơi khỏi
    từ điển và luật này lặng lẽ phá một tính năng khác."""
    assert "xi pi diu" in _ch("Xem mục CPU và RAM")


@pytest.mark.parametrize("vao,phai_giu", [
    ("HĐND TỈNH ban hành", "HĐND"),
    ("TRƯỜNG ĐH BÁCH KHOA", "ĐH"),
    ("CÔNG TY TNHH ABC thông báo", "TNHH"),
])
def test_viet_tat_khong_co_nguyen_am_song_sot_trong_chuoi_co_dau(vao, phai_giu):
    """🔴 Chuỗi trộn viết tắt với chữ viết hoa có dấu — ca THẬT, không dựng ra.

    Mọi âm tiết tiếng Việt đều có nguyên âm làm âm chính. Nên một chữ không có
    nguyên âm nào **không thể** là từ tiếng Việt — nó chỉ có thể là viết tắt.
    Đó là một sự thật ngôn ngữ, và đó là lý do nó được phép quyết định.
    """
    ra = _ch(vao)
    assert phai_giu in ra, (
        f"{vao!r} -> {ra!r}: {phai_giu!r} khong co nguyen am nen no la viet "
        f"tat, khong duoc ha xuong")


def test_chu_hoa_dau_cau_khong_bi_dung_toi():
    """Chỉ chuỗi VIẾT HOA TOÀN BỘ mới bị đụng, không phải chữ hoa đầu từ."""
    assert _ch("Tôi Đi Học") == "Tôi Đi Học"
    assert _ch("Xin chào các bạn") == "Xin chào các bạn"
    assert _ch("Hà Nội và TP HCM") == "Hà Nội và TP HCM"


def test_xuong_dong_tach_hai_chuoi_khac_nhau():
    """Xuống dòng là ranh giới: tiêu đề và nội dung là hai chuỗi, không phải một."""
    ra = _ch("TIÊU ĐỀ\nNỘI DUNG ở đây")
    assert "tiêu đề" in ra and "nội dung" in ra


def test_phan_du_da_biet_va_da_ghi():
    """⚠️ Luật này KHÔNG che được viết tắt CÓ nguyên âm nằm trong chuỗi có dấu.

    `"CÔNG TY TNHH ABC"` → `ABC` bị hạ thành `abc`. Ghi lại thành phép kiểm để
    nó là một **giới hạn đã biết**, không phải một lỗi chờ ai đó phát hiện —
    và để ngày ai đó sửa được nó thì phép kiểm này đỏ và bắt họ xoá dòng này.

    Cửa `/xem-truoc` tồn tại đúng cho phần dư này.
    """
    ra = _ch("CÔNG TY TNHH ABC thông báo")
    assert "TNHH" in ra, "phan giu duoc thi phai giu"
    assert "abc" in ra, (
        "neu ca nay da sua duoc thi xoa phep kiem nay va cap nhat chu thich "
        "trong `_ha_chuoi_viet_hoa`")


# ═══════════════════════════════════ không phá thứ đã có ════════════════════

def test_khong_pha_phep_bo_ky_tu_vo_hinh():
    """#177 vẫn phải hoạt động sau khi thêm hai luật mới."""
    assert _ch("Xin​chào﻿ bạn") == "Xinchào bạn"


def test_khong_pha_doc_so_va_ngay():
    ra = _ch("Ngày 5/9/2026 có 30%")
    assert "phần trăm" in ra
    assert "/" not in ra, f"ngay chua duoc doc thanh chu: {ra!r}"


# ═══════════════════════ phân cách hàng nghìn dính hậu tố tiền ══════════════
#
# Tìm ra 01/09/2026 bằng cách MỞ BẢNG "MÁY SẼ ĐỌC THÀNH" trên production và đọc
# nó, chứ không bằng test — vì không phép kiểm nào ở đây từng chạm tới phân cách
# hàng nghìn. Chuỗi thử là một câu quảng cáo bình thường, và bảng xem trước hiện
# ra `1250.000 đồng`.
#
# ⛔ Lỗi nằm ở đúng cách viết giá THÔNG DỤNG NHẤT ở Việt Nam. `_NGAN` dùng
#    `(?=\d{3}\b)`, mà `đ` là ký tự chữ trong Unicode nên `\b` không khớp giữa
#    `0` và `đ`:
#
#        990.000đ    -> 990.000 đồng    (dau cham song sot NGUYEN VEN)
#        1.250.000đ  -> 1250.000 đồng   (bo cai dau, giu cai sau)
#
#    Còn `1.250.000 đồng` — có dấu cách — thì ĐÚNG. Nên một phép kiểm viết bằng
#    văn bản sạch sẽ xanh, và đó chính là lý do lỗi sống sót: dạng hỏng là dạng
#    khách gõ, dạng đúng là dạng ta gõ khi viết test.

def test_hang_nghin_dinh_hau_to_tien():
    """Ba dạng viết giá phải ra cùng một con số."""
    for vao in ("990.000\u0111", "990.000 \u0111\u1ed3ng", "990.000VN\u0110"):
        ra = _ch(vao)
        assert "990000" in ra, f"{vao!r} -> {ra!r}: dau cham hang nghin con lai"
        assert "\u0111\u1ed3ng" in ra, f"{vao!r} -> {ra!r}: mat don vi tien"


def test_hang_nghin_NHIEU_nhom_dinh_hau_to():
    """`1.250.000đ` từng chỉ bỏ dấu chấm ĐẦU rồi giữ dấu chấm sau."""
    ra = _ch("1.250.000\u0111")
    assert "1250000" in ra, f"-> {ra!r}"
    assert "1250.000" not in ra, (
        f"-> {ra!r}: bo dau cham dau ma giu dau cham sau — te hon ca khong sua, "
        "vi no ra mot chuoi khong phai so cung khong phai chu")


def test_hang_nghin_KHONG_an_dau_cau_va_thap_phan():
    """Nới `\b` thành `(?!\d)` không được nuốt thêm gì.

    Ba ca này phải GIỮ NGUYÊN dấu chấm — nếu một lượt sửa sau làm chúng đỏ thì
    luật đã nới quá tay.
    """
    assert _ch("3.14") == "3.14", "thap phan hai chu so: khong phai hang nghin"
    assert "2020. 300" in _ch("nam 2020. 300 nguoi"), "dau cham CAU co dau cach"
