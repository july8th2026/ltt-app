"""Ký tự Unicode VÔ HÌNH phải bị bỏ trước khi văn bản tới model.

## Vì sao tệp này tồn tại — và nguồn của nó

Upstream `pnnbao97/VieNeu-TTS` **issue #177** (đã đóng). Người dùng báo *"xuất
hiện các tiếng nước ngoài chèn giữa giọng đọc tiếng Việt"*. Tác giả trả lời,
nguyên văn:

  *"khả năng cao lỗi này KHÔNG phải do model mà xuất phát từ ký tự Unicode ẩn
   hoặc định dạng văn bản đầu vào. Các văn bản dạng hành chính sao chép từ Word
   hoặc trang tin thường chứa các ký tự không hiển thị (zero-width characters).
   Khi đi qua bộ tokenizer, chúng tạo ra các token lạ (OOV), khiến mô hình sinh
   ra tiếng lạ trước khi đọc tiếp câu sau."*

Người báo lỗi xác nhận sửa được sau khi đổi hàm chia đoạn.

⛔ VÌ SAO NÓ LÀ LỖI **TIỀN**: job vẫn `done`, và `credit_cost` tính theo giây
   **thật sự sinh ra**. Khách trả tiền cho một bản thu có tiếng lạ chen vào, và
   **không lỗi nào báo**. Trước bản vá này, sáu ký tự lọt thẳng qua
   `chuan_hoa`: ZWSP · ZWNJ · ZWJ · BOM · soft hyphen · line separator.

## ⭐ Ký tự ẩn gây BA loại lỗi, và hai loại im lặng hoàn toàn

  1. model đọc ra tiếng lạ        — nghe thấy được
  2. **phá khớp từ điển phát âm** — im lặng
  3. **phá regex ngày/giờ/số thứ tự** — im lặng

Đó là lý do phép xoá phải chạy **trước** `tu_dien.ap_dung` và trước các regex,
chứ không phải chỉ "ở đâu đó trong `chuan_hoa`".
"""
from __future__ import annotations

import unicodedata

import pytest

from apps.ltt_voice import text_pipeline as tp

#: Sáu thủ phạm đã đo được là lọt qua, cộng vài họ hàng cùng category `Cf`.
VO_HINH = {
    "U+200B ZWSP": "​",
    "U+200C ZWNJ": "‌",
    "U+200D ZWJ": "‍",
    "U+FEFF BOM": "﻿",
    "U+00AD SOFT HYPHEN": "­",
    "U+2060 WORD JOINER": "⁠",
    "U+202A LRE": "‪",
    "U+202C PDF": "‬",
    "U+200E LRM": "‎",
}


@pytest.mark.parametrize("ten,ky_tu", list(VO_HINH.items()))
def test_ky_tu_vo_hinh_bi_bo(ten, ky_tu):
    ra = tp.chuan_hoa(f"Công ty{ky_tu}Green Travel")
    assert ky_tu not in ra, f"{ten} van lot qua: {ra!r}"
    # ⛔ XOÁ, không thay bằng khoảng trắng. ZWSP là **gợi ý chỗ ngắt dòng**,
    #    không phải dấu phân cách: "Xin<ZWSP>chào" nghĩa là "Xinchào" có thể
    #    xuống dòng ở giữa. Thay bằng khoảng trắng là tự tạo ra một từ mới.
    assert ra == "Công tyGreen Travel", (
        f"{ten} bi THAY bang khoang trang thay vi bi xoa: {ra!r}")


@pytest.mark.parametrize("ky_tu", [" ", " "])
def test_ngat_dong_la_thanh_xuong_dong_that(ky_tu):
    """`U+2028`/`U+2029` là `Zl`/`Zp` — chúng **là** ngắt dòng, nên đổi chứ
    không xoá. Xoá chúng là dính hai câu vào nhau."""
    ra = tp.chuan_hoa(f"Câu một.{ky_tu}Câu hai.")
    assert ky_tu not in ra
    assert "Câu một." in ra and "Câu hai." in ra
    assert "một.Câu" not in ra, f"hai cau bi dinh vao nhau: {ra!r}"


def test_ky_tu_HIEN_DUOC_thi_GIU_LAI():
    """Dấu nháy cong và gạch ngang **hiển thị được** — chúng là dấu câu thật và
    model đọc chúng thành ngắt nghỉ. Xoá chúng là làm mất ngữ điệu.

    ⭐ Đây là phép kiểm giữ cho bản vá **không nở ra**: "bỏ ký tự lạ" rất dễ
       trượt thành "bỏ mọi thứ không phải a-z".
    """
    ra = tp.chuan_hoa("Anh ấy nói “xin chào” — rồi đi.")
    assert "“" in ra and "”" in ra and "—" in ra


# ── Hai lỗi IM LẶNG mà ký tự ẩn gây ra ───────────────────────────────────────

def test_ky_tu_an_KHONG_pha_khop_tu_dien():
    """🔴 Từ điển phát âm khớp theo **biên từ**. Một ZWSP giữa từ làm phép khớp
    trượt — và không có triệu chứng nào ngoài một chữ bị đọc sai."""
    sach = tp.chuan_hoa("chưởng môn")
    ban = tp.chuan_hoa("chưởng​ môn")
    assert ban == sach, (
        f"ZWSP lam lech ket qua tu dien:\n  sach: {sach!r}\n  ban : {ban!r}")


def test_ky_tu_an_KHONG_pha_regex_ngay():
    """🔴 Cùng một ký tự ẩn cũng phá `_NGAY`. Ngày không được đọc thành chữ thì
    model đọc `12/08/2026` theo cách của nó — thường là sai."""
    sach = tp.chuan_hoa("12/08/2026")
    ban = tp.chuan_hoa("12/08​/2026")
    assert "ngày" in sach, f"tien de sai, `_NGAY` khong chay: {sach!r}"
    assert ban == sach, (
        f"ZWSP lam `_NGAY` truot:\n  sach: {sach!r}\n  ban : {ban!r}")


# ── Thứ tự với NFC ───────────────────────────────────────────────────────────

def test_xoa_TRUOC_nfc_de_dau_to_hop_van_ghep_duoc():
    """🔴 Phép kiểm tinh tế nhất tệp này, và nó chốt một THỨ TỰ.

    Ca khó: `'a'` + `U+200B` + dấu sắc tổ hợp `U+0301`.

        xoá SAU  NFC  ->  U+0061 U+0301   (rời)   — KHÔNG phải NFC
        xoá TRƯỚC NFC ->  U+00E1          (ghép)  — đúng NFC

    NFC không ghép được qua một ký tự chen giữa, nên xoá sau thì phép ghép đã lỡ
    mất chuyến. Hai chuỗi **in ra giống hệt nhau** — `'á'` và `'á'`.

    ⛔ Và nó không phải chuyện thẩm mỹ: với tokenizer đó là hai chuỗi khác nhau,
       tức đúng loại token lạ mà cả phép xoá này sinh ra để tránh. Sửa một nửa
       lỗi rồi để lại nửa kia ở dạng khó thấy hơn thì tệ hơn không sửa.
    """
    ra = tp.chuan_hoa("a​́")
    assert ra == unicodedata.normalize("NFC", ra), (
        f"ket qua KHONG o dang NFC: {[f'U+{ord(c):04X}' for c in ra]} — "
        "phep xoa dang chay SAU `normalize('NFC')`, phai chay TRUOC")
    assert ra == "á" and len(ra) == 1


def test_van_ban_sach_khong_bi_doi():
    """Bản vá không được đụng vào văn bản vốn đã sạch."""
    for cau in ("Xin chào các bạn.", "Doanh thu tăng 15%.",
                "Hello, this is English."):
        assert tp.chuan_hoa(cau) == tp.chuan_hoa(tp.chuan_hoa(cau))


def test_chuoi_rong_va_none_khong_no():
    assert tp.chuan_hoa("") == ""
    assert tp.chuan_hoa(None) == ""  # type: ignore[arg-type]


# ── Đi qua cả ống, không chỉ một hàm ─────────────────────────────────────────

def test_ky_tu_an_khong_lot_qua_chia_doan():
    """`chuan_bi` là thứ ba cửa thực sự gọi. Bọc `chuan_hoa` mà `chuan_bi` đi
    đường khác thì bản vá không tới đâu cả."""
    kq = tp.chuan_bi("Câu một.​ Câu hai.​", tran_moi_doan=1500)
    assert "​" not in kq.da_chuan_hoa
    for d in kq.doan:
        assert "​" not in d


def test_bao_gia_giam_chu_khong_tang():
    """⭐ Ký tự ẩn bị bỏ ⇒ ít ký tự hơn ⇒ báo giá **giảm**.

    Đúng hướng: khách trả cho thứ được đọc, không trả cho thứ vô hình. Và vì
    `manifest._gia()` đếm **sau** chuẩn hoá, nó tự khớp — không phải sửa gì.
    """
    from apps.ltt_voice.manifest import MANIFEST

    ban = "Công ty" + "​" * 200 + " Green Travel"
    sach = "Công ty Green Travel"
    assert MANIFEST.credit_cost({"text": ban}) == MANIFEST.credit_cost({"text": sach})
