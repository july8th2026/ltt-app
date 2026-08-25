"""Bản ghi giải thích một lỗi 500 phải **thật sự nói được nó là lỗi gì**.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — 25/08, một lỗi 500 có thật mà không chẩn đoán được.

   Claude Desktop gọi `/api/v1/messages` và ta trả về một `500`. Ta có **hai**
   đường ghi log cho đúng tình huống này, và **cả hai đều câm**:

   * `server.api.errors` gọi `logger.exception(...)`. Nhưng một handler của
     FastAPI **không** chạy trong khối `except` — ngoại lệ tới qua tham số `exc`,
     nên `sys.exc_info()` rỗng và vết ghi ra đúng ba chữ: `NoneType: None`.
   * `server.app` bắt được vết thật, nhưng vết đó dài 108 dòng và bị **cắt** —
     mà kiểu ngoại lệ nằm ở **cuối** một traceback Python, tức đúng phần bị cắt.

⛔ Hệ quả: một dòng log **trông như** đã có vết, mà không mang thông tin nào.
   Đó tệ hơn là không có log — nó làm ta tin là mình đã nhìn.

⭐ BÀI HỌC: thứ quan trọng nhất phải nằm trong **dòng message**, không phải trong
   phần đính kèm. Đính kèm bị cắt; dòng message thì không.

⚠️ Vẫn KHÔNG được rò ra cho khách: thân 500 giữ nguyên cố định. Đây chỉ là thứ
   người vận hành đọc.
"""
from __future__ import annotations

import importlib
import logging

import pytest


@pytest.fixture()
def err():
    return importlib.import_module("server.api.errors")


class _Req:
    """Đủ hình dạng cho handler, không dựng cả app."""

    class _Url:
        path = "/api/v1/messages"

    def __init__(self):
        self.url = self._Url()
        self.method = "POST"
        self.state = type("S", (), {})()
        self.headers = {}


def test_ghi_duoc_KIEU_va_THONG_DIEP_ngoai_le(err, caplog):
    """Chốt chính cái đã hỏng: handler phải nêu được ngoại lệ là gì."""
    with caplog.at_level(logging.ERROR, logger="server.api.errors"):
        err.unhandled_exception_handler(_Req(), KeyError("max_tokens"))

    ban_ghi = [r for r in caplog.records if r.name == "server.api.errors"]
    assert ban_ghi, "khong ghi duoc gi ca"
    dong = ban_ghi[-1].getMessage()
    assert "KeyError" in dong, f"dong log khong neu kieu ngoai le: {dong}"
    assert "max_tokens" in dong, f"dong log khong neu thong diep: {dong}"


def test_KHONG_con_ghi_ra_NoneType_None(err, caplog):
    """Chốt thô, cố ý: triệu chứng cũ không được quay lại."""
    with caplog.at_level(logging.ERROR, logger="server.api.errors"):
        err.unhandled_exception_handler(_Req(), ValueError("hong that"))

    r = [x for x in caplog.records if x.name == "server.api.errors"][-1]
    assert r.exc_info is not None, (
        "exc_info rong -> vet se ghi ra 'NoneType: None' dung nhu loi cu")
    assert r.exc_info[0] is ValueError


def test_ma_nguon_khong_dung_lai_logger_exception(err):
    """`logger.exception()` trong handler của FastAPI **luôn** ghi vết rỗng.

    Đây là chốt bằng mã nguồn vì lỗi kia không nổ — nó chỉ lặng lẽ ghi sai, và
    một lần sửa sau rất dễ "gọn hoá" ngược về `.exception()`.
    """
    import pathlib
    ma = pathlib.Path(err.__file__).read_text(encoding="utf-8")
    than = ma.split("def unhandled_exception_handler", 1)[1].split("\ndef ", 1)[0]
    assert ").exception(" not in than, (
        "quay lai logger.exception() trong handler -> vet lai rong")
    assert "exc_info=exc" in than


def test_than_tra_ve_van_la_500_co_dinh(err):
    """Sửa log KHÔNG được làm rò chi tiết ra cho khách."""
    kq = err.unhandled_exception_handler(_Req(), RuntimeError("bi mat cua ta"))
    assert kq.status_code == 500
    assert b"bi mat cua ta" not in bytes(kq.body)
    assert b"RuntimeError" not in bytes(kq.body)
