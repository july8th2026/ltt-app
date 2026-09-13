"""test_1246 — luong stream phai HUY DUOC khi khach cat. Su co L-08, 13/09/2026.

## Su co that

Khach cat giua mot luot stream ⇒ lease `mode=stream` van song **>=643 s** trong
khi may B da ranh (`requests_processing = 0`). Mot suat GPU bi giu cho mot nguoi
da dong cua so.

## ⛔ MOT BAN VA "HIEN NHIEN" DA DUOC DEPLOY VA DA HONG — bo nay thay the no

Ban dau (sang 13/09) toi boc luong bang mot ham tham `request.receive()` theo
nhip 1 s. No da len production, va do tren may that:

    chay TRON luot, khong cat        21,5 s (849 manh)
    cat o manh 5, qua Cloudflare     lease nha sau 99,0 s
    cat o manh 5, qua LOOPBACK       lease CHUA nha sau 150 s
    log "khach cat giua luong"       KHONG MOT DONG NAO

Vi tu chua bao gio tra `True`. Ly do: o cua DONG BO khong ai tranh `receive` nen
cach ay chay (L-06: 16,54 -> 1,43 s); o cua STREAM thi Starlette DA DO SAN tren
`receive` qua `listen_for_disconnect`, nen `http.disconnect` toi tay NO. Va thu
no lam khi nhan duoc la huy cancel scope — dung cai KHONG cat duoc threadpool.
**Ben thang cuoc dua la ben khong lam gi duoc.**

## Vi sao ban NAY khac ve BAN CHAT

    generator DONG BO bi bo roi   -> khong ai nem gi vao  -> `finally` treo
    generator BAT DONG BO bi huy  -> `CancelledError` nem VAO diem `await`
                                     -> `finally` chay NGAY

Khong tranh `receive` voi ai. Doi chieu cong dong: `fastapi#7572` (async
generator la cach duoc khuyen nghi) va `Kludex/starlette#2866` (maintainer xac
nhan huy CO lan vao async generator; giai doan khong lan duoc la hoi quy theo
phien ban, da sua — ta dang o starlette 1.3.1 + uvicorn 0.52.0).

## Bon menh de

| # | menh de | no chan dieu gi |
|---|---|---|
| 1 | khach doc het ⇒ khong mat manh nao | ban va khong duoc lam hong duong thuong |
| 2 | huy ⇒ nguon duoc DONG | khong dong thi httpx van mo, may B van giu slot |
| 3 | huy KHONG dung cho luong dang chan | ban le `abandon_on_cancel=True` |
| 4 | nguon khong co `close` thi khong vo | iterator thuong van dung duoc |
"""
import threading
import time

import anyio

from platform_core.runtime_noi_bo import luong as cua_luong


def test_doc_het_thi_khong_mat_manh_nao():
    nk: list = []

    def _nguon():
        try:
            for i in range(5):
                yield f"manh-{i}".encode()
        finally:
            nk.append("dong")

    async def _chay():
        ra = []
        async for khoi in cua_luong.bat_dong_bo_hoa(_nguon()):
            ra.append(khoi)
        return ra

    ra = anyio.run(_chay)
    assert ra == [f"manh-{i}".encode() for i in range(5)]
    assert nk == ["dong"], "nguon chua duoc dong sau khi chay het"


def test_huy_thi_nguon_duoc_DONG():
    """Ve de quen nhat, va thieu no thi ban va gan nhu vo nghia.

    Thoat vong ma khong dong nguon chi day cung mot loi xuong mot tang: generator
    ben trong nam treo, `client.close()` cua `luong_vlm._di` chua chay, va may B
    VAN giu slot — tuc lease nha ma suat khong nha.
    """
    nk: list = []

    def _nguon():
        try:
            while True:
                yield b"x"
        finally:
            nk.append("dong")

    async def _chay():
        g = cua_luong.bat_dong_bo_hoa(_nguon())
        n = 0
        async for _ in g:
            n += 1
            if n >= 3:
                break
        await g.aclose()          # dung nhu Starlette buong khi khach cat

    anyio.run(_chay)
    assert nk == ["dong"], f"nguon CHUA duoc dong: {nk}"


def test_huy_KHONG_dung_cho_mot_luot_doc_dang_chan():
    """🔴 BAN LE: `abandon_on_cancel=True`.

    Mac dinh cua anyio la `False` — lenh bi huy VAN DUNG CHO luong chay xong.
    Voi ta, "luong chay xong" nghia la doi may B tra manh ke tiep, tuc dung lai
    chinh L-08 duoi mot cai ten khac.

    Bo nay dung mot nguon CHAN 10 giay. Co co ⇒ huy ve trong ~1 s. Khong co co
    ⇒ phai doi het 10 s.
    """
    da_vao = threading.Event()
    cho_nha = threading.Event()

    def _nguon():
        yield b"dau"
        da_vao.set()
        cho_nha.wait(10)          # mo phong mot luot doc socket dang chan
        yield b"sau"

    async def _chay():
        with anyio.move_on_after(1.0):
            async for _ in cua_luong.bat_dong_bo_hoa(_nguon()):
                pass

    t0 = time.monotonic()
    try:
        anyio.run(_chay)
        troi = time.monotonic() - t0
    finally:
        cho_nha.set()             # tha luong bi bo roi, khong de treo tien trinh

    assert da_vao.is_set(), "chua vao toi luot doc bi chan — phep do khong cham dich"
    assert troi < 5.0, (
        f"huy mat {troi:.1f}s — no DUNG CHO luong doc chay xong. "
        "`abandon_on_cancel=True` da bi go, va L-08 quay lai.")


def test_huy_goi_DONG_NGUON_chu_khong_chi_close_generator():
    """🔴 `close()` KHONG du, va day la cai bay da lam ban va dau tien nua voi.

    `abandon_on_cancel=True` buong luot cho, nhung LUONG kia van dang o TRONG
    `next(nguon)`. Do bang mot bo mo phong mot bien so:

        close() mot generator dang thuc thi o luong khac
        -> ValueError: generator already executing
        -> `finally` cua nguon KHONG BAO GIO chay
        -> `client.close()` cua httpx chua duoc goi

    ⇒ Lease nha ma MAY B VAN GIU SLOT. Nua duong, va la nua khach khong nhin
      thay. Ve nay chot rang `dong_nguon` — duong dong THANG toi httpx, goi duoc
      tu luong khac — thuc su duoc goi tren duong huy.
    """
    da_vao = threading.Event()
    cho_nha = threading.Event()
    nk: list = []

    def _nguon():
        yield b"dau"
        da_vao.set()
        cho_nha.wait(10)
        yield b"sau"

    def _dong():
        nk.append("da dong cua ra mang")
        cho_nha.set()          # dung nhu `client.close()` lam luot doc kia vo

    async def _chay():
        with anyio.move_on_after(1.0):
            async for _ in cua_luong.bat_dong_bo_hoa(_nguon(), _dong):
                pass

    try:
        anyio.run(_chay)
    finally:
        cho_nha.set()

    assert da_vao.is_set(), "chua toi luot doc bi chan — phep do khong cham dich"
    assert nk == ["da dong cua ra mang"], (
        f"`dong_nguon` KHONG duoc goi tren duong huy: {nk}. Lease se nha ma may "
        "B van giu slot.")


def test_nguon_khong_co_close_thi_khong_vo():
    async def _chay():
        return [k async for k in cua_luong.bat_dong_bo_hoa(iter([b"a", b"b"]))]

    assert anyio.run(_chay) == [b"a", b"b"]
