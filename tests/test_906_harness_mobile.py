"""706 — bộ đo mobile phải giữ bốn bài học đã trả giá để có.

`tools/mobile_quet.js` + `tools/mobile_qa.py quet` là thứ dựng lại được mọi con
số trong `docs/MOBILE/`. Nhưng một bộ đo cũng là mã, và mã thì trôi — nên bốn
mệnh đề dưới đây được chốt lại.

⭐ Cả bốn đều đến từ một lần bộ đo **nói dối**, không phải từ lý thuyết:

1. `getBoundingClientRect().right` báo cả phần đã bị một tổ tiên `overflow-x:auto`
   **hấp thụ**. Không lọc theo tổ tiên cuộn thì bộ đo chỉ nhầm thủ phạm — đã xảy
   ra **ba lần** trong một phiên (khối `<pre>`, `nav.apptabs`, và bảng ở `/jobs`).

2. Cỡ chữ ô nhập phải đọc `getComputedStyle`: luật 16px nằm trong
   `@media(pointer:coarse)`, thuộc tính HTML không thấy nó.

3. Vùng chạm **trong** một canvas React Flow phải chia lại cho zoom. Đo 05/09:
   `.react-flow__handle` đo 29px ở zoom 0,648 nhưng CSS là **44px** — đã đạt sàn.
   Không chia thì ta "sửa" một thứ chỉ nhỏ vì người dùng đang thu nhỏ canvas.

4. Dòng `const CAU_HINH = {...};` là **giao diện** giữa Python và JS. `quet()`
   thay đúng dòng ấy; đổi cách viết nó thì lệnh gãy — và gãy ở chỗ thông báo
   lỗi không nói gì về nguyên nhân.

Không mở trình duyệt, không cần máy chủ.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
JS = GOC / "tools" / "mobile_quet.js"
PY = GOC / "tools" / "mobile_qa.py"


def boc_chu_thich(s: str) -> str:
    """Bỏ `/* */` và `//`, giữ độ dài. Tệp này thuần JS nên không cần lọc HTML."""
    ra = list(s)
    i, n = 0, len(s)
    while i < n:
        mo = next((c for c in (("/*", "*/"), ("//", "\n")) if s.startswith(c[0], i)), None)
        if mo:
            j = s.find(mo[1], i + len(mo[0]))
            j = n if j < 0 else j + len(mo[1])
            for k in range(i, j):
                if ra[k] != "\n":
                    ra[k] = " "
            i = j
        else:
            i += 1
    return "".join(ra)


def test_bo_boc_chu_thich_that_su_boc():
    """Chính phần giải thích ở đầu tệp JS nhắc cả bốn từ khoá dưới đây."""
    vao = "a /* coToTienCuon */ b // getComputedStyle\nc"
    ra = boc_chu_thich(vao)
    assert "coToTienCuon" not in ra and "getComputedStyle" not in ra
    assert len(ra) == len(vao)


@pytest.fixture(scope="module")
def js() -> str:
    assert JS.exists(), "tools/mobile_quet.js biến mất"
    return boc_chu_thich(JS.read_text(encoding="utf-8"))


# ── Bốn bài học ────────────────────────────────────────────────────────────

def test_loc_theo_to_tien_cuon_truoc_khi_goi_la_TRAN(js):
    assert "coToTienCuon" in js, (
        "bộ đo không còn lọc theo tổ tiên cuộn — nó sẽ báo mọi phần tử trong một "
        "vùng `overflow-x:auto` là tràn, và chỉ nhầm thủ phạm")
    assert "overflowX" in js
    i_ham = js.find("coToTienCuon")
    i_dung = js.find("coToTienCuon(el)")
    assert i_dung > i_ham, "hàm lọc có mặt nhưng không được gọi"


def test_co_chu_o_nhap_doc_COMPUTED_chu_khong_doc_thuoc_tinh(js):
    assert "getComputedStyle(el).fontSize" in js, (
        "cỡ chữ đọc từ thuộc tính HTML sẽ không bao giờ thấy luật 16px trong "
        "`@media(pointer:coarse)` — phép đo sẽ xanh giả trên mọi trang")


def test_vung_cham_trong_canvas_duoc_chia_lai_cho_zoom(js):
    assert "react-flow__viewport" in js and "zoom" in js, (
        "bộ đo không còn biết canvas đang thu phóng")
    assert re.search(r"b\.height\s*/\s*zoom", js), (
        "chiều cao trong canvas không được chia lại cho zoom — `.react-flow__handle` "
        "đo 29px ở zoom 0,648 nhưng CSS là 44px, tức đã đạt sàn")


def test_dong_CAU_HINH_dung_khuon_ma_python_thay_duoc():
    """Giao diện Python↔JS. Đổi cách viết thì `quet` gãy, và gãy khó hiểu."""
    tho = JS.read_text(encoding="utf-8")
    assert re.search(r"const CAU_HINH = \{.*?\};", tho, re.S), (
        "không còn dòng `const CAU_HINH = {...};` — `mobile_qa.py quet` thay đúng "
        "dòng này bằng cấu hình thật trước khi gọi playwright-cli")
    py = PY.read_text(encoding="utf-8")
    assert "const CAU_HINH = " in py, "phía Python không còn thay dòng ấy"


# ── Hai cái bẫy nền tảng, đã trả giá ──────────────────────────────────────

def test_khong_dung_HEAD_de_do_route_con_song():
    """FastAPI trả **405** cho `HEAD` ở route chỉ khai `GET`.

    Một bộ lọc "bỏ mọi thứ >= 400" khi ấy vứt sạch cả 23 route rồi báo
    *"quét 0 route"* — rất tự tin, và hoàn toàn vô nghĩa. Đã xảy ra ở lượt chạy
    đầu tiên của chính lệnh này.
    """
    py = PY.read_text(encoding="utf-8")
    m = re.search(r"def route_khach.*?(?=\ndef )", py, re.S)
    assert m, "không còn `route_khach`"
    assert 'method="HEAD"' not in m.group(0), (
        "`route_khach` quay lại dùng HEAD — FastAPI trả 405 và bộ lọc sẽ vứt sạch route")


def test_tim_playwright_cli_bang_which_chu_khong_goi_thang():
    """Trên Windows, npm cài `playwright-cli` thành bộ ba tệp (không đuôi, `.cmd`,
    `.ps1`), và `subprocess` **không** tự chọn `.cmd` — nó báo `WinError 2`.
    `shutil.which` thì biết, vì nó đọc `PATHEXT`."""
    py = PY.read_text(encoding="utf-8")
    assert 'shutil.which("playwright-cli")' in py, (
        "gọi thẳng `playwright-cli` trong subprocess sẽ hỏng trên Windows")


# ── 320px phải nằm trong bộ khung mặc định ────────────────────────────────

def test_khung_mac_dinh_co_320px():
    """320px bắt được **hai** lỗi mà 390px bỏ lọt, và một trong hai do chính bản
    vá vùng chạm 44px sinh ra. Một bộ đo chỉ chạy ở khổ "chuẩn" không thấy mép."""
    py = PY.read_text(encoding="utf-8")
    m = re.search(r"KHUNG_MAC_DINH = \(([^)]*)\)", py, re.S)
    assert m, "không còn `KHUNG_MAC_DINH`"
    assert "p320" in m.group(1)
    js = JS.read_text(encoding="utf-8")
    assert re.search(r"p320:\s*\{\s*w:\s*320", js), "`mobile_quet.js` không còn khổ 320"
