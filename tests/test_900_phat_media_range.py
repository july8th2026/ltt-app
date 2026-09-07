"""700 — hop dong HTTP Range cua `platform_core.phat_media`.

Bo kiem nay chot DUNG bon khiem khuyet ma nam ban chep tu viet trong `apps/`
dang mang (do 2026-09-05, `docs/MOBILE/02_BASELINE.md` muc 1b):

  1. khong bao gio tra 416
  2. suffix `bytes=-500` tra 501 byte DAU thay vi 500 byte CUOI
  3. `bytes=0-` doc toan tep vao RAM
  4. `start > end` xu ly moi noi mot kieu

Moi phep kiem duoi day se DO neu ai do thay `phat_media` bang mot ban theo kieu
cu. Do la muc dich: mot chu thich noi "dung chuan RFC" khong ngan duoc gi, mot
phep kiem thi co.

Khong cham CSDL, khong cham kho that, khong doc trang thai may.
"""
from __future__ import annotations

import io

import pytest

from platform_core import phat_media


class KhoGia:
    """Kho toi thieu: chi `open` + `size`, dung nhu `Storage` that."""

    def __init__(self, du_lieu: bytes, tua_duoc: bool = True):
        self.du_lieu = du_lieu
        self.tua_duoc = tua_duoc
        self.so_lan_mo = 0
        self.luong_da_dong: list[bool] = []

    def size(self, khoa: str) -> int:
        return len(self.du_lieu)

    def open(self, khoa: str):
        self.so_lan_mo += 1
        if self.tua_duoc:
            return _LuongDem(self.du_lieu, self)
        return _LuongKhongTua(self.du_lieu, self)


class _LuongDem(io.BytesIO):
    """Tep cuc bo: tua duoc."""

    def __init__(self, du_lieu: bytes, kho: KhoGia):
        super().__init__(du_lieu)
        self._kho = kho

    def close(self):
        self._kho.luong_da_dong.append(True)
        super().close()


class _LuongKhongTua:
    """`StreamingBody` cua R2: KHONG tua duoc — `seek` nem `AttributeError`."""

    def __init__(self, du_lieu: bytes, kho: KhoGia):
        self._d = du_lieu
        self._i = 0
        self._kho = kho

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            n = len(self._d) - self._i
        m = self._d[self._i:self._i + n]
        self._i += len(m)
        return m

    def seek(self, *a):
        raise AttributeError("StreamingBody khong tua duoc")

    def close(self):
        self._kho.luong_da_dong.append(True)


def than(resp) -> bytes:
    """Gom body cua `Response`/`StreamingResponse` thanh bytes."""
    if hasattr(resp, "body_iterator"):
        import asyncio

        async def gom():
            ra = b""
            async for m in resp.body_iterator:
                ra += m
            return ra

        return asyncio.run(gom())
    return resp.body


NOI_DUNG = bytes(range(256)) * 8          # 2048 byte, moi byte doan duoc vi tri


# ── 1. Khong co Range -> 200 ─────────────────────────────────────────────────

def test_khong_range_tra_200_va_khai_accept_ranges():
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="audio/wav")
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-length"] == str(len(NOI_DUNG))
    assert "content-range" not in r.headers
    assert than(r) == NOI_DUNG


def test_accept_ranges_co_MAT_ngay_ca_khi_khong_co_range():
    """Safari quyet dinh co seek duoc hay khong TU luot 200 dau tien.

    Day chinh la cho `ltt_voice` va `chatltt` dang thieu: luot dau khong khai
    `Accept-Ranges`, nen WebKit ket luan may chu khong tua duoc va bo phat —
    trong khi tai xuong van chay. Do la trieu chung nguoi dung bao.
    """
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="audio/wav")
    assert r.headers.get("accept-ranges") == "bytes"


# ── 2. Dai hop le -> 206 ────────────────────────────────────────────────────

def test_dai_dong_tra_206_dung_byte():
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=100-199")
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 100-199/{len(NOI_DUNG)}"
    assert r.headers["content-length"] == "100"
    assert than(r) == NOI_DUNG[100:200]


def test_dai_mo_duoi_chay_toi_het_tep():
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=2000-")
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 2000-2047/{len(NOI_DUNG)}"
    assert than(r) == NOI_DUNG[2000:]


def test_cuoi_vuot_qua_tep_thi_kep_ve_byte_cuoi():
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=2040-999999")
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 2040-2047/{len(NOI_DUNG)}"


# ── 3. Suffix range — khiem khuyet so 2 ─────────────────────────────────────

def test_suffix_tra_byte_CUOI_khong_phai_byte_dau():
    """`bytes=-500` = 500 byte CUOI.

    Ban cu doc `s=""` -> start=0 va `e="500"` -> end=500, tra 501 byte DAU. Sai
    du lieu, va sai trong im lang: client nhan du 501 byte va tin la dung.
    """
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=-500")
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 1548-2047/{len(NOI_DUNG)}"
    assert than(r) == NOI_DUNG[-500:]
    assert than(r) != NOI_DUNG[:501], "day dung la loi cua ban cu"


def test_suffix_lon_hon_tep_thi_tra_ca_tep():
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=-999999")
    assert r.status_code == 206
    assert than(r) == NOI_DUNG


def test_suffix_khong_tra_206_rong():
    """`bytes=-0` = "khong byte nao cuoi" -> khong thoa man noi -> 416."""
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=-0")
    assert r.status_code == 416


# ── 4. Khong thoa man noi -> 416 — khiem khuyet so 1 va so 4 ────────────────

@pytest.mark.parametrize("dai", ["bytes=2048-", "bytes=5000-6000", "bytes=-0"])
def test_dai_khong_thoa_man_tra_416(dai):
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range=dai)
    assert r.status_code == 416, f"{dai} phai la 416, khong duoc nan thanh 206"


def test_416_kem_content_range_sao_tren_tong():
    """Thieu `bytes */N` thi 416 la mot nga cut: client khong biet hoi lai gi."""
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=9999-")
    assert r.status_code == 416
    assert r.headers["content-range"] == f"bytes */{len(NOI_DUNG)}"


def test_dau_lon_hon_cuoi_tra_416_khong_phai_206_lech():
    """Bon app nan `start=0` nhung GIU `end`; `agent` nan ca hai. Ca hai deu sai."""
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=500-100")
    assert r.status_code == 416


# ── 5. Cu phap la -> bo qua, tra 200 (RFC 9110 §14.2) ──────────────────────

@pytest.mark.parametrize("dai", [
    "", "   ", "items=0-10", "bytes=abc-def", "bytes=", "bytes=-",
    "bytes=1.5-2", "khong-phai-range",
])
def test_cu_phap_la_thi_tra_toan_tep_chu_khong_phai_416(dai):
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range=dai)
    assert r.status_code == 200
    assert than(r) == NOI_DUNG


def test_nhieu_dai_tra_toan_tep():
    """Multipart/byteranges hop le nhung khong trinh phat nao o day can."""
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=0-9,20-29")
    assert r.status_code == 200
    assert than(r) == NOI_DUNG


# ── 6. Tep rong ─────────────────────────────────────────────────────────────

def test_tep_rong_tra_200_khong_phai_416():
    kho = KhoGia(b"")
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="audio/wav",
                               dai_range="bytes=0-")
    assert r.status_code == 200
    assert r.headers["content-length"] == "0"
    assert than(r) == b""


# ── 7. Khong doc toan tep vao RAM — khiem khuyet so 3 ──────────────────────

def test_bytes_0_gach_khong_gom_toan_tep_thanh_mot_khoi():
    """`bytes=0-` la dang Chrome gui thuong xuyen nhat.

    Ban cu goi `f.read(total)` — mot video 400 MB thanh 400 MB RSS moi luot.
    Ban nay phai phat theo khoi, nen than phai la mot BO SINH chu khong phai
    mot khoi bytes dung san.
    """
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=0-")
    assert r.status_code == 206
    assert hasattr(r, "body_iterator"), "phai la StreamingResponse"
    assert than(r) == NOI_DUNG


def test_doc_khoi_khong_bao_gio_xin_hon_mot_khoi_mot_lan():
    ghi: list[int] = []

    class LuongDo(_LuongDem):
        def read(self, n=-1):
            ghi.append(n)
            return super().read(n)

    kho = KhoGia(NOI_DUNG)
    kho.open = lambda khoa: LuongDo(NOI_DUNG, kho)   # noqa: ARG005
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=0-")
    than(r)
    assert ghi, "phai co it nhat mot lan doc"
    assert max(ghi) <= phat_media.KHOI


# ── 8. Kho khong tua duoc (R2) ─────────────────────────────────────────────

def test_luong_khong_tua_duoc_van_ra_dung_byte():
    """`StreamingBody` cua R2 nem `AttributeError` khi `seek` — phai doc bo."""
    kho = KhoGia(NOI_DUNG, tua_duoc=False)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range="bytes=1000-1099")
    assert r.status_code == 206
    assert than(r) == NOI_DUNG[1000:1100]


@pytest.mark.parametrize("dai", [None, "bytes=0-99"])
def test_luong_duoc_dong_sau_khi_phat_xong(dai):
    """Ban cu o `autosubvideo` khong dong luong; mo ta tep treo toi luc GC don.

    Kiem CA duong 200 lan 206 — duong 200 la duong bi bo quen, vi no chi dua
    thang luong cho `StreamingResponse` va khong ai dong no.
    """
    kho = KhoGia(NOI_DUNG)
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                               dai_range=dai)
    than(r)
    assert kho.luong_da_dong == [True]


def test_duong_200_cung_phat_theo_khoi_khong_lap_theo_DONG():
    """Lap tren mot tep nhi phan la lap theo DONG — cat o moi byte 0x0A.

    Nam ban chep cu deu dua thang `storage.open(key)` cho `StreamingResponse`,
    nen mot tep WAV bi bam thanh hang nghin mau dai ngan ngau nhien theo vi tri
    cua byte 0x0A trong du lieu am thanh. No chay duoc, nen khong ai de y.
    """
    ghi: list[int] = []

    class LuongDo(_LuongDem):
        def read(self, n=-1):
            ghi.append(n)
            return super().read(n)

    kho = KhoGia(NOI_DUNG)
    kho.open = lambda khoa: LuongDo(NOI_DUNG, kho)   # noqa: ARG005
    r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="audio/wav")
    assert than(r) == NOI_DUNG
    assert ghi, "duong 200 phai goi read() theo khoi"
    assert max(ghi) <= phat_media.KHOI
    assert -1 not in ghi, "read(-1) nghia la nuot ca tep mot lan"


# ── 9. Tieu de them va tong duoc truyen san ────────────────────────────────

def test_tieu_de_them_di_kem_moi_ma_trang_thai():
    kho = KhoGia(NOI_DUNG)
    them = {"Cache-Control": "private, no-store"}
    for dai, ma in ((None, 200), ("bytes=0-9", 206), ("bytes=9999-", 416)):
        r = phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                                   dai_range=dai, tieu_de_them=them)
        assert r.status_code == ma
        assert r.headers["cache-control"] == "private, no-store"


def test_tong_truyen_san_thi_khong_hoi_kho_nua():
    """Noi goi da biet kich thuoc thi dung bat kho `head_object` lan hai."""

    class KhoDemSize(KhoGia):
        def __init__(self, d):
            super().__init__(d)
            self.so_lan_size = 0

        def size(self, khoa):
            self.so_lan_size += 1
            return super().size(khoa)

    kho = KhoDemSize(NOI_DUNG)
    phat_media.phat_tu_kho(kho, "k", kieu_noi_dung="video/mp4",
                           tong=len(NOI_DUNG))
    assert kho.so_lan_size == 0


# ── 10. Chot rang bo phan tich khong tu y nan dai ─────────────────────────

@pytest.mark.parametrize("dai,mong", [
    ("bytes=0-0", (0, 0)),
    ("bytes=0-2047", (0, 2047)),
    ("bytes=2047-2047", (2047, 2047)),
    ("bytes=-1", (2047, 2047)),
])
def test_phan_tich_range_bien(dai, mong):
    assert phat_media.phan_tich_range(dai, 2048) == mong
