"""test_1534 — máy B im quá hạn đọc (`httpx.ReadTimeout`) ở mọi cửa `/api/v1`. C0-34.

## Sự việc (log production 19/09/2026 16:53:18 UTC)

    STREAM LOI rid=5d73ccda dur=135.4s ttfb=- khoi=6 token_ra=0
    khong do duoc usage — hoan du va KHONG thu            (tiền: đúng)
    unhandled public api error POST /api/v1/messages -> ReadTimeout

Bốn agent con + agent chính cùng gọi `ltt-3.8`; máy B không trả byte dữ liệu nào
sau vài nhịp `: ping`. `httpx.ReadTimeout` thoát khỏi thân phản hồi stream — 200
đã gửi nên khách (LTTCODE) chỉ thấy luồng đứt không `message_stop`, và `_phat`
còn `mo.hong()` ⇒ `api_pool.danh_dau_loi` (năm lần = khoá DUY NHẤT của
`ltt_llm` sang ERROR — sự cố khoá pool 19/09).

## Bất biến

1. Stream (`/messages`, `/responses`): hết giờ đọc ⇒ MỘT khối lỗi đúng khuôn
   giao thức, mã `overloaded` (client tự thử lại), không ngoại lệ thoát.
2. Hết giờ đọc KHÔNG phạt khoá — cả giữa luồng lẫn lúc chờ header.
3. Tiền hoàn đủ.
4. Đồng bộ (`/chat/completions`): hết giờ ⇒ 503 có thân lỗi, hoàn đủ — `test_1535`.

⛔ Đối chứng âm: `ConnectError` lúc mở (máy B không với tới) VẪN phạt khoá.
"""
from __future__ import annotations

import importlib
import json

import httpx
import pytest

_t272 = importlib.import_module("tests.test_272_cua_streaming")

MSG = _t272.MSG
RSP = _t272.RSP
api = _t272.api                      # noqa: F811 — dùng lại fixture đã có
_account = _t272._account
_so_du = _t272._so_du
_than = _t272._than
_h = _t272._h


class _LuongTreo:
    """`LuongMo` giả: vài nhịp `: ping` rồi im ⇒ `httpx.ReadTimeout` như httpx thật."""

    def __init__(self, nem: BaseException):
        self.ma = 200
        self.content_type = "text/event-stream"
        self.bao: list = []
        self._nem = nem
        self.luong = self._di()

    def _di(self):
        yield b": ping\n\n"
        yield b": ping\n\n"
        raise self._nem

    def xong(self, tokens=0):
        self.bao.append("xong")

    def hong(self, exc):
        self.bao.append(("hong", type(exc).__name__))


def _dat_treo(monkeypatch, nem=None):
    from platform_core.llm import luong_vlm
    tao: list = []

    def gia(db, *, duong, than, timeout_s=900.0, **_meta):
        m = _LuongTreo(nem or httpx.ReadTimeout("timed out"))
        tao.append(m)
        return m

    monkeypatch.setattr(luong_vlm, "mo", gia)
    return tao


def _su_kien(r) -> list:
    ds = []
    for dong in r.text.splitlines():
        if dong.startswith("data:"):
            ds.append(json.loads(dong[5:].strip()))
    return ds


@pytest.mark.parametrize("duong", [MSG, RSP])
def test_stream_het_gio_doc_tra_khoi_loi_overloaded_khong_phat_khoa_hoan_tien(
        api, monkeypatch, duong):
    tao = _dat_treo(monkeypatch)
    user_id, token = _account()
    truoc = _so_du(user_id)

    r = api.post(duong, json=_than(), headers=_h(token))

    assert tao, "chua cham 'may B' — phep kiem khong do dung thu no noi"
    assert r.status_code == 200, r.text
    ds = _su_kien(r)
    assert ds, f"khach khong nhan khoi loi nao: {r.text[-300:]!r}"
    cuoi = ds[-1]
    if duong == MSG:
        assert cuoi["type"] == "error", cuoi
        assert cuoi["error"]["type"] == "overloaded_error", cuoi
    else:
        assert cuoi["type"] == "response.failed", cuoi
        assert cuoi["response"]["error"]["code"] == "server_is_overloaded", cuoi
    assert ("hong", "ReadTimeout") not in tao[0].bao, (
        "het gio doc bi tinh la loi khoa — nam lan la ltt_llm sang ERROR")
    assert _so_du(user_id) == truoc, "het gio ma van thu tien"


def test_DOI_CHUNG_luong_vo_that_van_phat_khoa_va_tra_upstream(api, monkeypatch):
    """Lỗi đọc KHÁC hết giờ (máy B cắt) vẫn là lỗi thượng nguồn — phạt như cũ."""
    tao = _dat_treo(monkeypatch, nem=httpx.ReadError("may B cat"))
    _u, token = _account()
    r = api.post(MSG, json=_than(), headers=_h(token))
    assert r.status_code == 200
    cuoi = _su_kien(r)[-1]
    assert cuoi["type"] == "error" and cuoi["error"]["type"] == "api_error", cuoi
    assert tao[0].bao == [("hong", "ReadError")], tao[0].bao


# ── Lúc chờ header (luong_vlm.mo) ────────────────────────────────────────────

def _mo_voi_client_nem(monkeypatch, nem):
    from platform_core import api_keys, api_pool, providers
    from platform_core.llm import luong_vlm

    phat: list = []
    monkeypatch.setattr(api_pool, "chon_key",
                        lambda db, **k: type("K", (), {"base_url": "http://b"})())
    monkeypatch.setattr(api_pool, "danh_dau_loi",
                        lambda db, key, **k: phat.append(k.get("message")))
    monkeypatch.setattr(api_keys, "lay_credential", lambda db, key: "x")
    monkeypatch.setattr(providers, "get", lambda pid: None)

    class _Ctx:
        def __enter__(self):
            raise nem

        def __exit__(self, *a):
            return False

    class _Client:
        def __init__(self, *a, **k):
            pass

        def stream(self, *a, **k):
            return _Ctx()

        def close(self):
            pass

    monkeypatch.setattr(httpx, "Client", _Client)
    with pytest.raises(luong_vlm.KhongMoDuocLuong) as loi:
        luong_vlm.mo(None, duong="/v1/messages", than={"model": "m"})
    return loi.value, phat


def test_mo_het_gio_doc_header_KHONG_phat_khoa_va_danh_dau_het_gio(monkeypatch):
    loi, phat = _mo_voi_client_nem(monkeypatch, httpx.ReadTimeout("timed out"))
    assert phat == [], "cho header qua han bi phat khoa"
    assert loi.failure.is_timeout and not loi.failure.is_busy


def test_DOI_CHUNG_mo_ConnectError_VAN_phat_khoa(monkeypatch):
    loi, phat = _mo_voi_client_nem(monkeypatch, httpx.ConnectError("refused"))
    assert phat == ["ConnectError"]
    assert not loi.failure.is_timeout


def test_dieu_phoi_ReadTimeout_thanh_AmbiguousProviderError(monkeypatch):
    """Nguồn của ca đồng bộ: ReadTimeout ⇒ `AmbiguousProviderError` (không phạt khoá)."""
    from platform_core.llm import dieu_phoi
    from platform_core.llm.cong_vlm import AmbiguousProviderError

    class _Client:
        def __init__(self, *a, **k):
            pass

        def request(self, *a, **k):
            raise httpx.ReadTimeout("timed out")

        def close(self):
            pass

    monkeypatch.setattr(httpx, "Client", _Client)
    with pytest.raises(AmbiguousProviderError):
        dieu_phoi._goi_openai("http://b", "x", {"model": "m", "messages": []}, 1.0)
