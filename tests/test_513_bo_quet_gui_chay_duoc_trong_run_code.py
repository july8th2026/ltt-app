r"""Hai bộ quét GUI phải chạy được trong sandbox `playwright-cli run-code`.

## 🔴 Vì sao tệp này tồn tại — một lỗi KHÔNG BAO GIỜ NỔ

`tools/a11y_quet.js:39` gọi `new URL(CAU_HINH.goc)`. **`URL` không tồn tại**
trong ngữ cảnh `run-code`. Nhưng nó nằm **bên trong** nhánh
`if (CAU_HINH.cookie)`, và `check_a11y.ROUTE_MAC_DINH` chỉ có bốn route **công
khai** — không route nào cần đăng nhập.

⇒ Nhánh ấy **chưa bao giờ chạy**, dù docstring của `check_a11y.py` khai
  `--cookie` là cách quét route cần đăng nhập. Một đường có đủ khớp nối mà chưa
  bao giờ có nước (`DECISIONS.md::DV-010`).

Nó nổ đúng lần đầu tiên ai đó quét một route cần đăng nhập — 08/09/2026, khi
soát màn Dự án và thẻ giọng cho U-17.

## ⭐ Và bản vá đã nằm sẵn ở tệp anh em

`tools/mobile_quet.js` có **đúng** đoạn mã ấy, đã sửa, kèm nguyên chú thích:

    ⚠️ `URL` khong ton tai trong ngu canh `run-code`. Tach ten may bang chuoi.

Ai đó gặp lỗi, sửa ở **một** tệp, ghi lại lý do — và tệp anh em có cùng đoạn mã
thì không ai sửa. **Chép lại bộ đo mà không chép bài học là cách một lớp lỗi
sống sót qua chính bản vá của nó.**

## ⛔ Phép kiểm này chốt CÁI ĐÃ HỎNG, không chốt "đường cookie chạy đúng"

Chốt câu thứ hai đòi một máy chủ sống + `playwright-cli` + một phiên đang mở —
tức một phép kiểm tích hợp không chạy được ở mọi lượt gate, nên nó sẽ bị `skip`,
và **một phép kiểm bị bỏ qua thì không canh gì cả**.

⇒ Ở đây chốt đúng thứ đã hỏng, bằng một phép đọc tĩnh chạy trong nửa giây. Nó
  không chứng minh đường `--cookie` đúng; nó chứng minh **lớp lỗi này không quay
  lại**, ở **cả hai** tệp, kể cả khi ai đó chép thêm bản thứ ba.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]

#: Mọi tệp `.js` được `playwright-cli run-code` thực thi.
#:
#: ⛔ DÒ BẰNG NỘI DUNG, không gõ tay danh sách. Một danh sách chép tay không có
#:    cách nào tự biết nó đã cũ — và bản thứ ba chính là ca tệp này sinh ra để
#:    bắt. Dấu hiệu: tệp khai `const CAU_HINH = {...}` (khuôn mà cả
#:    `check_a11y.py` lẫn `mobile_qa.py` thay-rồi-gọi).
def _bo_quet() -> list[pathlib.Path]:
    ra = []
    for p in sorted((GOC / "tools").glob("*.js")):
        if "const CAU_HINH" in p.read_text(encoding="utf-8"):
            ra.append(p)
    return ra


def test_tim_duoc_it_nhat_HAI_bo_quet():
    """⭐ ĐỐI CHỨNG cho `_bo_quet()`. Một bộ dò trả về danh sách rỗng làm **mọi**
    phép kiểm dưới đây xanh vĩnh viễn — và chúng sẽ xanh rất thuyết phục."""
    ten = {p.name for p in _bo_quet()}
    assert {"a11y_quet.js", "mobile_quet.js"} <= ten, (
        f"khong tim thay du hai bo quet (thay: {sorted(ten)})")


#: Phép tách hostname mà CẢ HAI bộ quét phải dùng.
#:
#: ⚠️ `URL` không có trong sandbox `run-code`, nên tách bằng chuỗi là bắt
#:    buộc. Nhưng "tách bằng chuỗi" có nhiều cách, và hai cách khác nhau là
#:    hai chỗ có thể sai khác nhau — nên chốt ĐÚNG MỘT biểu thức.
MAU_TACH_HOSTNAME = "replace(/^https?:\\/\\//, '')"


def _ma_that(s: str) -> str:
    """Bỏ chú thích `/* */` và `//`.

    🔴 BẮT BUỘC: cả hai tệp **trích dẫn** `new URL` trong chú thích để giải
       thích vì sao không dùng nó. Khớp chuỗi thô sẽ báo động trên chính lời
       giải thích — lỗi đã mắc nhiều lần trong kho này.
    """
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return re.sub(r"//[^\n]*", " ", s)


def test_bo_loc_chu_thich_THAT_SU_cat():
    """⛔ SELF-TEST. `_ma_that` hỏng thì phép kiểm chính xanh vĩnh viễn."""
    assert "new URL" not in _ma_that("/* dung new URL o day */ var a = 1;")
    assert "new URL" not in _ma_that("// dung new URL o day\nvar a = 1;")
    assert "new URL" in _ma_that("var u = new URL(x);"), "bo loc cat ca MA THAT"


@pytest.mark.parametrize("tep", [p.name for p in _bo_quet()])
def test_KHONG_bo_quet_nao_dung_new_URL(tep):
    """🔴 `URL` không tồn tại trong sandbox `run-code`.

    ⚠️ Và lỗi này **im lặng gấp đôi**: nó nằm trong nhánh chỉ chạy khi có
       cookie, mà mốc mặc định không có route nào cần đăng nhập. Một lỗi không
       bao giờ nổ vẫn là một lỗi — nó chỉ đợi đúng người đầu tiên cần tới nó.
    """
    ma = _ma_that((GOC / "tools" / tep).read_text(encoding="utf-8"))
    assert "new URL" not in ma, (
        f"`tools/{tep}` dung `new URL(...)` — `URL` KHONG ton tai trong ngu "
        f"canh `playwright-cli run-code`. Tach ten may bang chuoi, xem "
        f"`tools/mobile_quet.js`.")


@pytest.mark.parametrize("tep", [p.name for p in _bo_quet()])
def test_moi_bo_quet_tach_hostname_CUNG_MOT_KIEU(tep):
    """⭐ Vế thứ hai, và nó là vế chặn bản sao thứ ba.

    Không đủ khi chỉ cấm `new URL`: một tệp mới có thể tách hostname bằng
    một phép khác — đúng hôm nay và sai ở một dạng URL nào đó. Chốt rằng cả
    hai dùng **cùng** phép: một phép, một chỗ để sửa nếu nó sai.

    ⛔ SO CHUỖI NGUYÊN VĂN, không dựng một regex để dò một regex. Bản đầu
       viết `re.search(r"replace\\(/\\^https\\?...")` và **đỏ oan ở cả hai
       tệp** — tôi bận thoát dấu cho lớp regex thứ hai và làm sai chính thứ
       mình đang dò. Một phép so chuỗi thẳng không có lớp thứ hai để làm sai.
    """
    # 🔴 ĐỌC MÃ THÔ, KHÔNG QUA `_ma_that`. Biểu thức cần tìm CHỨA `//`
    #    (`replace(/^https?:\/\//, '')`), nên bộ cắt chú thích `//` xoá nốt
    #    phần sau nó — bộ lọc ăn mất chính thứ nó đang dò.
    #
    # ⭐ `test_506::_ma_js` đã ghi đúng giới hạn này (*"một `//` bên trong chuỗi
    #    ký tự cũng bị cắt"*) và tôi vẫn vấp lại ở đây. Một giới hạn được ghi ra
    #    không tự áp dụng cho người viết ra nó.
    #
    # ⚠️ Bỏ `_ma_that` ở đây AN TOÀN vì chú thích của hai tệp trích dẫn
    #    `new URL`, không trích dẫn biểu thức này — nên không có nguy cơ khớp
    #    vào lời giải thích.
    ma = (GOC / "tools" / tep).read_text(encoding="utf-8")
    assert "addCookies" in ma, (
        f"tools/{tep} khong con dat cookie — neu do la co y thi go phep "
        f"kiem nay, dung noi rong danh sach `_bo_quet()`")
    assert MAU_TACH_HOSTNAME in ma, (
        f"`tools/{tep}` tach hostname bang mot phep KHAC. Dung dung mot "
        f"phep o ca hai tep: {MAU_TACH_HOSTNAME!r}")


def test_ca_hai_deu_dat_cookie_theo_CUNG_hinh_dang():
    """⛔ Cookie sai `domain` thì trình duyệt **im lặng bỏ qua** nó, và trang trả
    về bản CHƯA ĐĂNG NHẬP — báo cáo khi ấy là báo cáo của trang login, không
    phải của trang cần đo.

    `check_a11y.py` có gắn cờ `CHUA_DANG_NHAP` cho ca ấy, nhưng một phép kiểm
    tĩnh rẻ hơn một lượt quét 15 phút rồi đọc cờ.
    """
    for p in _bo_quet():
        ma = _ma_that(p.read_text(encoding="utf-8"))
        if "addCookies" not in ma:
            continue
        assert "domain:" in ma, f"tools/{p.name}: addCookies thieu `domain`"
        assert "path:" in ma, f"tools/{p.name}: addCookies thieu `path`"
