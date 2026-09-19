"""test_1523 — khach ngat giua luong KHONG duoc phat khoa provider. Su co 19/09/2026.

## Su viec (log production, gio UTC)

    23:54:30-23:54:46  5 dong `STREAM LOI` lien nhau (ttfb 0,2-11 s, token_ra 60-204)
    23:54:47 ->        moi lan mo luong: `khong cap duoc khoa cho ltt_llm (ThieuKeyError)`

Khoa DUY NHAT cua `ltt_llm` sang `status=error, error_count=5,
last_error='ReadError'` — va `APIKEY_ERROR` khong tu hoi. May B khoe suot luc do.

## Chuoi nhan qua (moi mat xich co bang chung)

1. `cloudflared.log`: dung 5 dong `stream N canceled by remote with error code 0`
   cung GIAY voi 5 dong `STREAM LOI` — phia KHACH (canh Cloudflare) huy luong,
   khong phai may B.
2. `bat_dong_bo_hoa` (vá L-08, 13/09) nhan huy -> `dong_nguon()` dong thang
   `httpx.Client` trong khi luong threadpool dang chan o `r.iter_raw()`.
3. Dong client tu luong khac giua luc doc => `httpx.ReadError` (tai hien 5/5 lan,
   httpx 0.28.1) — dung `last_error` tren production.
4. `ReadError` khong phai `GeneratorExit`, nen `_phat` ghi `vo = e` ->
   `STREAM LOI` -> `mo.hong(vo)` -> `api_pool.danh_dau_loi` nhanh "5xx/mang".
   Nam lan khong xen thanh cong nao -> `APIKEY_ERROR`.
5. Doi chung trong log: `STREAM KHACH_NGAT` co 26 dong, dong CUOI la 13/09 18:33
   (truoc vá L-08). Tu do KHONG con dong nao; `STREAM LOI` tang 6 -> 8 -> 12 -> 27
   -> 59/ngay. Vá L-08 da doi "khach ngat" thanh "loi thuong nguon".

⇒ Bat bien: khi CHINH PHIA A dong cua ra may B (vi khach di), ngoai le doc ma
  lan dong ay gay ra la HE QUA cua khach di, khong phai loi cua khoa.

⛔ Doi chung am o day la bat buoc: may B THAT SU cat luong thi van phai phat khoa.
"""
from __future__ import annotations

import inspect
import threading
from types import SimpleNamespace

import anyio
import httpx
import pytest

from platform_core.runtime_noi_bo import luong as cua_luong


class _MoGia:
    """Bản giả `LuongMo`: nguồn chặn như httpx thật, `dong_nguon` làm vỡ lượt đọc.

    ⚠️ `dong_nguon` làm vỡ lượt đọc bằng `httpx.ReadError` — đó KHÔNG phải nguồn
       tự mở trói cho mình (bẫy đã ghi ở `test_1246`), mà là hành vi đo được của
       httpx khi `Client.close()` chạy ở luồng khác (xem docstring tệp).
    """

    def __init__(self, *, b_tu_cat: bool = False):
        self.da_vao = threading.Event()
        self._dong = threading.Event()
        self.b_tu_cat = b_tu_cat
        self.bao: list = []
        self.luong = self._di()

    def _di(self):
        yield b"data: {\"type\":\"message_start\"}\n\n"
        self.da_vao.set()
        if self.b_tu_cat:
            raise httpx.ReadError("may B cat ket noi")
        self._dong.wait(10)
        raise httpx.ReadError("client da dong tu luong khac")

    def dong_nguon(self) -> None:
        self._dong.set()

    def xong(self, tokens: int = 0) -> None:
        self.bao.append(("xong", tokens))

    def hong(self, exc: BaseException) -> None:
        self.bao.append(("hong", type(exc).__name__))


def _luot(monkeypatch, mo) -> "cua_luong.LuotLuong":
    monkeypatch.setattr(cua_luong, "quyet_toan", lambda *a, **k: None)
    cb = SimpleNamespace(request_id="req-1523-aaaaaaaa", user_id="u1523xxxx",
                         da_giu=0, model_alias="ltt-3.8", lease_id="",
                         waiter_id="")
    luot = cua_luong.LuotLuong(chuan_bi=cb, content_type="text/event-stream")
    cua_luong.gan_luong(mo, luot)
    return luot


def test_khach_ngat_giua_luong_KHONG_phat_khoa(monkeypatch):
    """🔴 Mệnh đề trung tâm: hủy phía A -> ReadError -> KHÔNG `hong()`."""
    mo = _MoGia()
    luot = _luot(monkeypatch, mo)

    async def _chay():
        with anyio.move_on_after(1.0):
            async for _ in cua_luong.bat_dong_bo_hoa(luot.luong, luot.dong_nguon):
                pass

    anyio.run(_chay)
    # Luồng bị bỏ rơi cần một nhịp để bung ra và chạy `finally` của `_phat`.
    for _ in range(50):
        if mo.bao:
            break
        threading.Event().wait(0.05)

    assert mo.da_vao.is_set(), "chua toi luot doc bi chan — phep do khong cham dich"
    assert ("hong", "ReadError") not in mo.bao, (
        "khach ngat bi tinh la loi cua khoa: nam lan nhu the la APIKEY_ERROR "
        "va ltt_llm chet cho toi khi admin reset (su co 19/09)")
    assert mo.bao and mo.bao[0][0] == "xong", mo.bao
    assert luot.ket_thuc == "khach_ngat", luot.ket_thuc


def test_DOI_CHUNG_AM_may_B_that_su_cat_thi_VAN_phat_khoa(monkeypatch):
    """Không ai hủy phía A mà luồng vỡ -> đó là thượng nguồn -> phạt như cũ."""
    mo = _MoGia(b_tu_cat=True)
    luot = _luot(monkeypatch, mo)

    async def _chay():
        async for _ in cua_luong.bat_dong_bo_hoa(luot.luong, luot.dong_nguon):
            pass

    with pytest.raises(httpx.ReadError):
        anyio.run(_chay)
    assert mo.bao == [("hong", "ReadError")], mo.bao
    assert luot.ket_thuc == "loi"


def test_dong_nguon_sau_khi_luong_da_ket_thuc_khong_doi_phan_quyet(monkeypatch):
    """`bat_dong_bo_hoa` gọi `dong_nguon` ở MỌI đường ra, kể cả sau lỗi thật.

    Cờ "A đã đóng" dựng muộn lúc đó không được sửa lại phán quyết đã ghi.
    """
    mo = _MoGia(b_tu_cat=True)
    luot = _luot(monkeypatch, mo)
    with pytest.raises(httpx.ReadError):
        for _ in luot.luong:
            pass
    luot.dong_nguon()
    assert mo.bao == [("hong", "ReadError")]
    assert luot.ket_thuc == "loi"


def test_mo_thuong_nguon_di_qua_gan_luong():
    """Cửa thật phải dùng đúng hàm đã được kiểm ở trên, không tự gán lại."""
    src = inspect.getsource(cua_luong.mo_thuong_nguon)
    assert "gan_luong(" in src, (
        "`mo_thuong_nguon` khong con goi `gan_luong` — co huy phia A se khong "
        "duoc dung, va khach ngat lai phat khoa")
