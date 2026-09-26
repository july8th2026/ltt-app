"""`CloudflareError` phải mang mã, và ⛔ không được nuốt nguyên thân lỗi vào thông điệp.

## Hai lỗi trong cùng một tệp, và tôi viết nó hôm qua

Rà soát 26/09 cho `dns_cloudflare` **5/10**, thấp nhất trong bảy lớp nối — vì hai lý
do độc lập:

1. `CloudflareError` là lớp **duy nhất** ⛔ không có `.status`. `OvhError`,
   `ProxmoxError`, `VultrError`, `GatewayError` đều có. Người gọi ⛔ không phân biệt
   được `429` (bị hãm nhịp, nên chờ rồi thử lại) với `403` (token sai, thử lại vô
   nghĩa) — phải **mò chuỗi**.
2. Nó nhét **300 ký tự thân lỗi thô** vào message. Đúng cái tôi đã tránh ở
   `ovh._ma_loi_ovh` — nơi chỉ lấy `errorCode`/`class` và ⛔ không lấy `message`, vì
   thân lỗi của nhà cung cấp có khi **vọng lại chính yêu cầu** (ở đây yêu cầu mang
   tên bản ghi, tức mang IP của khách).

⭐ Cùng một người, cùng một ngày, đã sửa đúng lớp lỗi này ở `ovh.py` rồi lặp lại nó ở
  `dns_cloudflare.py`. **Biết về cái bẫy ⛔ không miễn nhiễm nó** — thứ chặn được là
  một phép kiểm, ⛔ không phải sự cẩn thận.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from apps.vps.services import dns_cloudflare as cf


class _Than:
    """Giả một `HTTPError` có `.read()` như `urllib` trả về."""

    def __init__(self, noi_dung: bytes):
        self._b = noi_dung

    def read(self, n: int = -1) -> bytes:
        return self._b

    def close(self) -> None:
        # `HTTPError.__del__` goi `close()`. Thieu no thi pytest bao
        # `PytestUnraisableExceptionWarning` — mot canh bao bi bo qua se thanh
        # diem mu, nen dong no o day chu khong tat nó ở cấu hình.
        return None


def _loi(ma: int, doc: dict | None, *, tho: bytes | None = None) -> HTTPError:
    than = tho if tho is not None else json.dumps(doc or {}).encode()
    return HTTPError("https://api.cloudflare.com/client/v4/x", ma, "err", {},
                     _Than(than))


def test_mang_status_va_ma_loi():
    e = cf.CloudflareError("x", status=429, ma_loi="81044")
    assert e.status == 429 and e.ma_loi == "81044"


def test_khong_truyen_thi_status_la_None():
    assert cf.CloudflareError("x").status is None


def test_doc_ma_loi_tu_than_JSON_cua_cloudflare():
    doc = {"success": False, "errors": [{"code": 81044, "message": "Record not found"}]}
    assert cf.ma_loi_cloudflare(_loi(400, doc)) == "81044"


def test_than_khong_phai_JSON_thi_ma_loi_RONG_chu_khong_nem():
    assert cf.ma_loi_cloudflare(_loi(502, None, tho=b"<html>bad gateway</html>")) == ""


def test_khong_co_than_thi_ma_loi_RONG():
    class _KhongDoc:
        code = 500

        def read(self, n=-1):
            raise OSError("khong co than")

    assert cf.ma_loi_cloudflare(_KhongDoc()) == ""


def test_thong_diep_KHONG_chua_than_loi_tho(monkeypatch):
    """⛔ Thân lỗi Cloudflare mang **tên bản ghi**, tức mang IP của khách.

    Và một `message` tự do của nhà cung cấp có khi vọng lại nguyên yêu cầu — đó là
    lý do `ovh._ma_loi_ovh` chỉ lấy mã định danh.
    """
    doc = {"success": False,
           "errors": [{"code": 81044,
                       "message": "ip-51-79-215-194.vps.lttstudios.com khong hop le"}]}

    def _nem(*a, **kw):
        raise _loi(400, doc)

    monkeypatch.setattr(cf, "urlopen", _nem)
    dns = cf.CloudflareDns("tok-gia", "lttstudios.com")
    with pytest.raises(cf.CloudflareError) as ex:
        dns._goi_that("GET", "/zones")
    cau = str(ex.value)
    assert "81044" in cau, "phai co ma de phan biet"
    assert "51.79.215.194" not in cau and "lttstudios.com" not in cau, (
        f"than loi tho lot vao thong diep: {cau!r}")
    assert ex.value.status == 400 and ex.value.ma_loi == "81044"


def test_loi_mang_khong_co_status():
    """`OSError` (DNS chết, timeout) ⛔ không có mã HTTP — và `None` nói đúng điều đó."""
    def _nem(*a, **kw):
        raise OSError("timed out")

    dns = cf.CloudflareDns("tok-gia")
    goc = cf.urlopen
    cf.urlopen = _nem
    try:
        with pytest.raises(cf.CloudflareError) as ex:
            dns._goi_that("GET", "/zones")
    finally:
        cf.urlopen = goc
    assert ex.value.status is None and ex.value.ma_loi == ""
    assert "OSError" in str(ex.value)


def test_MOI_lop_noi_deu_co_status_khong_con_lop_nao_khac_biet():
    """⛔ Bánh cóc: một lớp nối thiếu `.status` là người gọi phải mò chuỗi.

    Danh sách này là **tính chất**, ⛔ không phải liệt kê tên: mọi lớp lỗi của mọi
    lớp nối hạ tầng phải trả lời được câu *"nhà cung cấp trả mã gì"*.
    """
    from apps.vps.services.gateway import GatewayError
    from apps.vps.services.ovh import OvhError
    from apps.vps.services.proxmox import ProxmoxError
    from apps.vps.services.vultr import VultrError

    for lop in (cf.CloudflareError, OvhError, ProxmoxError, VultrError,
                GatewayError):
        e = lop("thu")
        assert hasattr(e, "status"), f"{lop.__name__} thieu .status"
