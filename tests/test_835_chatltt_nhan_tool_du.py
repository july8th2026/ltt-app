"""
test_835 — mọi tool NỘI BỘ đều phải có nhãn tiếng Việt ở giao diện. (H44 P09 bước 5)

## Vì sao một bánh cóc Python soi một tệp TypeScript

`KhoiTool.tsx` chỉ hiện những khoá đối số **có nhãn**; khoá lạ thì **ẩn**. Đó là
lựa chọn đúng cho tool ngoài chưa ai làm nhãn — nhưng nó cũng là một **đường
trốn**: thêm một tool nội bộ mới, quên nhãn, và đối số của nó **im lặng biến
mất** khỏi màn hình. Không lỗi, không cảnh báo, chỉ là một khối tool trống rỗng.

⇒ Bánh cóc này đóng đường ấy cho **tool của chính mình**, và cố ý **không** đòi
  gì ở tool ngoài (`image.ltt`, `speech.ltt`) — hợp đồng của chúng nằm ở app
  khác và có thể đổi mà không ai ở đây biết.

## ⚠️ Bộ trích đọc bằng regex, nên nó phải TỰ KIỂM

Không có bộ phân tích TypeScript ở đây, nên hai bảng nhãn được đọc bằng biểu
thức chính quy — tức đang **đọc thứ đại diện**. Một regex hỏng trả về tập rỗng,
và mọi phép kiểm `⊆` sẽ **xanh sạch** trên một tập rỗng.

⇒ `test_bo_trich_TU_KIEM` chốt rằng bộ trích thật sự tìm được vài khoá đã biết.
  Đúng bài học *"bộ dò quét văn bản"*: kèm self-test, đừng tin phép trích.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
TSX = GOC / "frontend" / "chatltt" / "src" / "KhoiTool.tsx"


def _khoa_cua_bang(ten_bang: str) -> set:
    """Khoá của một `const <ten_bang>: Record<string, string> = { ... }`."""
    van = TSX.read_bytes().decode("utf-8")
    m = re.search(rf"const {ten_bang}[^=]*=\s*\{{(.*?)\n\}}", van, re.S)
    if not m:
        return set()
    return set(re.findall(r"^\s*'?([A-Za-z_][\w.]*)'?\s*:", m.group(1), re.M))


def test_bo_trich_TU_KIEM():
    """⛔ Không có dòng này thì mọi phép kiểm dưới xanh trên một tập rỗng."""
    assert "noi_bo.tinh" in _khoa_cua_bang("NHAN_TOOL")
    assert "bieu_thuc" in _khoa_cua_bang("NHAN_DOI_SO")


def test_moi_tool_NOI_BO_deu_co_nhan_ten():
    from apps.chatltt.services import tool_noi_bo as T

    ten = {t["function"]["name"] for t in T.KHOI}
    thieu = ten - _khoa_cua_bang("NHAN_TOOL")
    assert thieu == set(), f"tool noi bo thieu nhan ten: {sorted(thieu)}"


def test_moi_DOI_SO_cua_tool_noi_bo_deu_co_nhan():
    """🔴 Đây là phép kiểm thật sự của tệp này.

    Khoá không có nhãn thì **ẩn**, nên quên nhãn không hỏng gì — nó chỉ làm
    người dùng không bao giờ thấy tool ấy đã được gọi với tham số gì.
    """
    from apps.chatltt.services import tool_noi_bo as T

    khoa = set()
    for t in T.KHOI:
        khoa |= set((t["function"]["parameters"].get("properties") or {}))
    thieu = khoa - _khoa_cua_bang("NHAN_DOI_SO")
    assert thieu == set(), f"doi so thieu nhan: {sorted(thieu)}"


def test_khong_khai_nhan_cho_thu_KHONG_ton_tai():
    """Chiều ngược lại: một nhãn cho một tool đã gỡ là một dòng chết.

    ⛔ Trừ tool ngoài (`image.*`, `speech.*`) — chúng có thật, chỉ là hợp đồng
       nằm ở app khác nên `tool_noi_bo.KHOI` không biết.
    """
    from apps.chatltt.services import tool_noi_bo as T

    ten = {t["function"]["name"] for t in T.KHOI}
    thua = {k for k in _khoa_cua_bang("NHAN_TOOL")
            if k.startswith("noi_bo.") and k not in ten}
    assert thua == set(), f"nhan cho tool khong ton tai: {sorted(thua)}"


@pytest.mark.parametrize("bang", ["NHAN_TOOL", "NHAN_DOI_SO", "NHAN_TRANG_THAI"])
def test_moi_nhan_deu_la_NHAN_chu_khong_phai_MA(bang):
    """Nhãn không được là chính cái khoá, và không được mang hình dạng định danh.

    ⚠️ Bản đầu của phép kiểm này đòi *"phải có dấu tiếng Việt"* và **đỏ trên một
       nhãn ĐÚNG**: `'Xong'` là tiếng Việt, chỉ là không có dấu.

    ⭐ Đúng cái bẫy tệp này cảnh báo ở đầu, lần này ở phía tôi: tôi đo **hình
       thức** (có dấu) thay cho **tính chất** (là nhãn, không phải mã). Tính
       chất ấy đo trực tiếp được, và rẻ hơn: một mã mang `_` hoặc `.`, và một
       nhãn thì khác cái khoá của nó.
    """
    van = TSX.read_bytes().decode("utf-8")
    m = re.search(rf"const {bang}[^=]*=\s*\{{(.*?)\n\}}", van, re.S)
    assert m, bang
    cap = re.findall(r"^\s*'?([A-Za-z_][\w.]*)'?\s*:\s*'([^']+)'", m.group(1), re.M)
    assert cap, bang
    xau = [(k, v) for k, v in cap
           if v == k or "_" in v or "." in v]
    assert xau == [], f"{bang}: nhan mang hinh dang MA: {xau}"


def test_moi_TRANG_THAI_backend_deu_co_nhan_o_giao_dien():
    """Bánh cóc nối hai phía: thêm một trạng thái ở `tables.py` mà quên nhãn ⇒ đỏ."""
    from apps.chatltt.tables import TRANG_THAI_KHOI_TOOL

    thieu = set(TRANG_THAI_KHOI_TOOL) - _khoa_cua_bang("NHAN_TRANG_THAI")
    assert thieu == set(), f"trang thai thieu nhan: {sorted(thieu)}"
