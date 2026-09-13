"""test_1246 — luong stream phai NHA SUAT duoc khi khach cat. Su co L-08.

## ⛔ BO NAY TUNG XANH TRONG KHI PRODUCTION NGHEN — doc doan nay truoc

Ban truoc cua tep nay xanh tron ven, va bo do tren may that van cho thay lease
song them ~225 s. Ly do nam o MOT dong cua ban gia:

    def _dong():
        nk.append("da dong")
        cho_nha.set()        # <- NGUON GIA TU MO TROI CHO CHINH NO

May B khong lam the. Mot generator dong bo dang treo tai `yield` khong tinh day
vi ai do dong socket. Ban gia khac vat that **dung o chieu dang do**, nen phep
kiem tra loi cho cau hoi ma no khong he hoi.

⇒ Luat rut ra, va no duoc cuong che o `test_khi_dut_*` duoi day: **nguon gia
  khong duoc tu mo troi.** Muon chung minh duong huy chay thi phai chung minh
  bang mot tin hieu DI RA (`khi_dut`), khong bang mot tin hieu ta tu bom vao.

## Bang chung — tra duoc, khong phai tu suy

Ban truoc trich `fastapi/fastapi#7572` va `Kludex/starlette#2866`. **Ca hai deu
404** (kiem 13/09/2026, trong khi `#3538`/`#3000` cung kho tra ve binh thuong).
Hai trich dan ay la bia. Thay bang:

| nguon | no noi gi |
|---|---|
| `starlette/responses.py:250` (1.3.1) | than phan hoi chi `async for`, **khong bao gio `aclose()`** |
| `starlette/background.py` (1.3.1) | `BackgroundTask` **khong** `CancelScope(shield=True)` |
| `Kludex/starlette#1438` | background bi huy khi khach cat — **chi khi co `BaseHTTPMiddleware`**; ta co bon tang |
| `Kludex/starlette#3458` | thoi diem chay background duoi middleware VAN lech hop dong; 5 PR, khong PR nao duoc gop |

⇒ Khong duoc treo viec nha suat GPU vao `finally` cua generator, cung khong treo
  vao rieng `BackgroundTask`. Duong chinh la `khi_dut`.
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
        return [k async for k in cua_luong.bat_dong_bo_hoa(_nguon())]

    ra = anyio.run(_chay)
    assert ra == [f"manh-{i}".encode() for i in range(5)]
    assert nk == ["dong"], "nguon chua duoc dong sau khi chay het"


def test_huy_thi_nguon_duoc_DONG():
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
        await g.aclose()

    anyio.run(_chay)
    assert nk == ["dong"], f"nguon CHUA duoc dong: {nk}"


def test_huy_KHONG_dung_cho_mot_luot_doc_dang_chan():
    """🔴 BAN LE: `abandon_on_cancel=True`.

    Mac dinh cua anyio la `False` — lenh bi huy VAN DUNG CHO luong chay xong.
    Voi ta, "luong chay xong" nghia la doi may B tra manh ke tiep, tuc dung lai
    chinh L-08 duoi mot cai ten khac.
    """
    da_vao = threading.Event()
    cho_nha = threading.Event()

    def _nguon():
        yield b"dau"
        da_vao.set()
        cho_nha.wait(10)
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
        cho_nha.set()

    assert da_vao.is_set(), "chua vao toi luot doc bi chan — phep do khong cham dich"
    assert troi < 5.0, (
        f"huy mat {troi:.1f}s — no DUNG CHO luong doc chay xong. "
        "`abandon_on_cancel=True` da bi go, va L-08 quay lai.")


def test_khi_dut_chay_du_NGUON_KHONG_THE_tinh_day():
    """🔴 LOP 1 cua co che nha suat — va la phep kiem thay cho ban xanh gia.

    ⛔ Khac ban cu o DUNG MOT DIEU, va dieu ay la tat ca: `_dong()` **khong**
       set `khong_bao_gio`. Nguon nam treo that, y het may B khi httpx dong ma
       luot doc chua kip vo. Neu viec nha suat phu thuoc vao generator bung ra,
       phep kiem nay DO — va do la dung cai da xay ra tren production.

    Chung minh bang tin hieu DI RA: `khi_dut` co duoc goi khong.
    """
    da_vao = threading.Event()
    khong_bao_gio = threading.Event()
    nk: list = []

    def _nguon():
        yield b"dau"
        da_vao.set()
        khong_bao_gio.wait(30)
        yield b"sau"

    def _dong() -> None:
        nk.append("dong_nguon")

    def _dut() -> None:
        nk.append("khi_dut")

    async def _chay():
        with anyio.move_on_after(1.0):
            async for _ in cua_luong.bat_dong_bo_hoa(_nguon(), _dong, _dut):
                pass

    try:
        anyio.run(_chay)
    finally:
        khong_bao_gio.set()

    assert da_vao.is_set(), "chua toi luot doc bi chan — phep do khong cham dich"
    assert nk == ["dong_nguon", "khi_dut"], (
        f"sai duong hoac sai THU TU: {nk}. Bat bien: dong ket noi TRUOC (bao may "
        "B thoi sinh), nha suat SAU — nha truoc thi nguoi thu bay vao trong khi "
        "GPU van ban.")


class _VoLon(BaseException):
    """Khong ke thua `Exception` — nen `except Exception` KHONG bat duoc."""


def test_khi_dut_van_chay_khi_dong_nguon_nem_BASE_EXCEPTION():
    """🔴 Ve NAY moi that su cuong che `finally` LONG.

    ⚠️ Ve `..._DONG_NGUON_NEM` ben duoi khai rang no chot cau truc `finally`
       long. **No khong.** Thu cuu `khi_dut` o do la menh de `except Exception`
       quanh `dong_nguon()`; go `finally` long di thi ve ay VAN XANH. Mot phep
       kiem tuyen bo manh hon thu no do — dung cai khuon da can du an nay nhieu
       lan, va lan nay no can chinh toi trong luc toi dang viet ve chong no.

    Mot `BaseException` di xuyen `except Exception`. Luc ay chi con `finally`
    long giu duoc duong nha suat. Go no ⇒ ve nay DO.
    """
    nk: list = []

    def _nguon():
        yield b"a"

    def _dong() -> None:
        raise _VoLon("cua ra mang vo kieu khong ai bat")

    def _dut() -> None:
        nk.append("khi_dut")

    async def _chay():
        async for _ in cua_luong.bat_dong_bo_hoa(_nguon(), _dong, _dut):
            pass

    try:
        anyio.run(_chay)
    except _VoLon:
        pass                      # vo van phai lan ra — ta khong nuot no
    assert nk == ["khi_dut"], (
        "`khi_dut` bi bo qua khi `dong_nguon` nem mot `BaseException` — `finally` "
        "long da bi go, va mot su co mat MOT suat GPU thanh mat CA HAI.")


def test_khi_dut_van_chay_khi_DONG_NGUON_NEM():
    """`dong_nguon` ném `Exception` thi `khi_dut` van phai chay.

    ⚠️ Ve nay chot menh de `except Exception` quanh `dong_nguon()`, KHONG chot
       `finally` long — xem ve tren de biet vi sao phan biet ay quan trong.
    """
    nk: list = []

    def _nguon():
        yield b"a"
        yield b"b"

    def _dong() -> None:
        raise RuntimeError("cua ra mang hong")

    def _dut() -> None:
        nk.append("khi_dut")

    async def _chay():
        async for _ in cua_luong.bat_dong_bo_hoa(_nguon(), _dong, _dut):
            pass

    anyio.run(_chay)
    assert nk == ["khi_dut"], (
        "`dong_nguon` nem va da nuot mat `khi_dut` — hai viec dang nam chung mot "
        "khoi `try`.")


def test_VAT_THAT_phai_khai_dong_nguon_va_luc_khoi_cuoi():
    """⚠️ Cai gia cua `getattr` o `luong.py`, va cua LOP 2.

    Ben tieu thu doc `getattr(mo, "dong_nguon", None)` de mot BAN GIA khong phai
    khai lai chu ky day du. Nhung neu VAT THAT mot ngay khong con truong ay,
    `getattr` tra `None` lang le va L-08 quay lai ma khong phep kiem nao do.

    `luc_khoi_cuoi` cung the: thieu no thi vi tu `con_song` cua LOP 2 khong con
    nguon su that, va nhip tim quay ve noi doi.
    """
    import dataclasses

    from platform_core.llm.luong_vlm import LuongMo
    from platform_core.runtime_noi_bo.luong import LuotLuong

    assert "dong_nguon" in {f.name for f in dataclasses.fields(LuongMo)}, (
        "`LuongMo` khong con khai `dong_nguon` — `luong.py` doc bang `getattr` "
        "nen no se LANG LE tra None va L-08 quay lai. Sua o ca hai cho.")
    assert "luc_khoi_cuoi" in {f.name for f in dataclasses.fields(LuotLuong)}, (
        "`LuotLuong` khong con khai `luc_khoi_cuoi` — LOP 2 mat nguon su that.")


def test_nguon_khong_co_close_thi_khong_vo():
    async def _chay():
        return [k async for k in cua_luong.bat_dong_bo_hoa(iter([b"a", b"b"]))]

    assert anyio.run(_chay) == [b"a", b"b"]
