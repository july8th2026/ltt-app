"""test_1246 — cua STREAM phai TU DUNG khi khach cat. Su co L-08, 13/09/2026.

## Su co that ma bo nay sinh ra de chan

Do 13/09: khach cat giua mot luot stream, may B da ranh
(`requests_processing = 0`), nhung lease `mode=stream` VAN SONG **>=643 s** va
van dap nhip. Mot suat GPU bi giu cho mot nguoi da dong cua so.

## Goc — doc tu ma thu vien DANG CAI, khong tu tri nho

    1. uvicorn khai ASGI spec_version "2.3" (< 2.4) => nhanh CO
       `listen_for_disconnect` moi la nhanh chay. Ngat CO duoc nghe.
    2. `await self.background()` nam o thut le NGOAI `async with` => cai
       `BackgroundTask` nha lease CO chay khi khach cat.
    3. Nhung `LuongMo.luong` la `Iterator[bytes]` DONG BO, nen Starlette boc no
       bang `iterate_in_threadpool` — va cancel scope cua anyio KHONG cat duoc
       mot LUONG dang cho doc socket.

⇒ Huy duoc phat, roi ket cho luong; task group khong sap; `background()` khong
  toi luot; lease khong nha. **643 s la luc MAY B buong**, khong phai mot han
  dinh nao cua may A.

⛔ Ba huong sua da bi loai tru BOI chuoi bang chung tren, va bo kiem nay chot lai
   de khong ai di lai:
     · ha `ORPHAN_TIMEOUT` — nhip tim lam han ay khong bao gio toi
     · `gc.collect()` dinh ky — GC khong phai co che (gia thuyet dau cua toi,
       DA BI BAC: bo mo phong toi dung gia dinh lease nha trong `finally` cua
       generator, trong khi ma that nha trong `BackgroundTask`)
     · doi `BackgroundTask` chay som hon — no DA chay dung cho

## Nam menh de

| # | menh de | no chan dieu gi |
|---|---|---|
| 1 | khach con doc ⇒ khong mat manh nao | ban va khong duoc cat nham nguoi vo can |
| 2 | khach cat ⇒ DUNG phat | chinh L-08 |
| 3 | va ĐÓNG nguon ⇒ `finally` cua no chay NGAY | nua de quen: khong dong thi chi day loi xuong mot tang |
| 4 | tham theo NHIP, khong tham moi manh | moi luot tham ton 0,05 s; tham tung manh la gay mot loi te hon |
| 5 | `ngat_chua` nem ⇒ CHAY TIEP | coi im lang la "da ngat" se cat ngang khach dang doc |
"""
import time

from platform_core.llm import ngat


#: ⛔ GIU THAM CHIEU TOI MOI GENERATOR NGUON. Day KHONG phai mot chi tiet don
#:    dep — no la thu lam phep kiem nay do dung vat.
#:
#: 🔴 Ban dau `_nguon` khong giu gi ca, va doi chung DA TRUOT: go han nua
#:    `close()` khoi ban va ma 6/6 ve VAN XANH. Vi sao: khi ham boc ket thuc,
#:    khong ai con tro toi generator nguon, refcount ve 0, CPython dong no NGAY
#:    — `finally` chay nho REFCOUNT chu khong nho ban va. Phep kiem do mot co
#:    che khac voi co che no tuong minh dang do.
#:
#: ⭐ San that KHONG nhu vay: generator nguon duoc `LuongMo.luong` giu, va
#:    `LuongMo` duoc khoi dung phan hoi giu. No song. Chi mot `close()` TUONG
#:    MINH moi chay duoc `finally` — dung cai L-08 noi ve.
_GIU: list = []


def _nguon(so_manh: int, nhat_ky: list):
    """Generator co `finally` GHI LAI — de biet no da thuc su ket thuc chua."""
    def _g():
        nhat_ky.append("mo")
        try:
            for i in range(so_manh):
                yield f"manh-{i}".encode()
        finally:
            nhat_ky.append("dong")
    g = _g()
    _GIU.append(g)          # mo phong `LuongMo` giu luong o san that
    return g


# -- 1. Khach con doc: khong duoc mat manh nao ------------------------------

def test_khach_con_doc_thi_khong_mat_manh_nao():
    nk: list = []
    ra = list(ngat.dung_khi_khach_cat(_nguon(5, nk), lambda: False))
    assert ra == [f"manh-{i}".encode() for i in range(5)]
    assert nk == ["mo", "dong"]


# -- 2 + 3. Khach cat: dung phat VA dong nguon ------------------------------

def test_khach_cat_thi_dung_phat_va_DONG_nguon_ngay():
    """Ve 3 la nua de quen nhat, va thieu no thi ban va gan nhu vo nghia.

    Thoat vong lap ma khong `close()` chi day cung mot loi xuong mot tang:
    generator ben trong nam treo, `finally` cua no (`ctx.__exit__` +
    `client.close()`) chua chay, va ket noi httpx toi may B van mo cho toi khi
    GC don — tuc dung lai tinh trang L-08, chi khac ten.

    ⚠️ Ban dau toi viet bo nay voi mot vong `for ... break` o manh thu 51. No
       DO — va do la loi cua PHEP KIEM, khong phai cua ma: luot tham ngat chi no
       sau `NHIP_THAM_S` (1 s), con vong ay bo di sau vai micro giay. Toi da roi
       di truoc khi ban va kip lam viec cua no, roi doc ket qua nhu mot khuyet
       tat cua ban va.
    """
    nk: list = []

    def _vo_tan():
        nk.append("mo")
        try:
            while True:
                yield b"x"
        finally:
            nk.append("dong")

    # Nguon VO TAN: chi co ban va moi ket thuc duoc vong nay. Neu no khong dung,
    # phep kiem treo — va treo la mot ket cuc doc duoc, khac han "xanh gia".
    g = _vo_tan()
    _GIU.append(g)          # giu tham chieu — xem chu thich o `_GIU`
    dem = 0
    for _ in ngat.dung_khi_khach_cat(g, lambda: True):
        dem += 1
    assert dem > 0
    assert nk == ["mo", "dong"], (
        f"nguon CHUA duoc dong: {nk} — lease nha roi nhung suat o may B van bi "
        "giu, tuc chi doi cho bi ket chu khong het ket")


def test_dong_nguon_ke_ca_khi_ben_tren_bo_di_giua_chung():
    """Khach cat o TANG TREN (khong doc nua) cung phai dong duoc nguon.

    Day la duong ma Starlette di khi `listen_for_disconnect` thang cuoc dua:
    no ngung keo, con ta thi chua kip thay ngat.
    """
    nk: list = []
    boc = ngat.dung_khi_khach_cat(_nguon(100_000, nk), lambda: False)
    next(boc)
    next(boc)
    boc.close()                       # Starlette/threadpool buong bo boc
    assert nk == ["mo", "dong"], f"nguon chua duoc dong: {nk}"


# -- 4. Tham theo NHIP, khong tham moi manh ---------------------------------

def test_tham_theo_nhip_chu_khong_moi_manh():
    """Moi luot tham ton toi `HAN_DOC_NGAT_S` (0,05 s).

    Tham tung manh tren mot luong vai tram manh/giay la tu them hang chuc giay
    do tre cho khach CON DANG DOC — chua mot loi bang cach gay mot loi te hon
    cho nguoi khong mac loi ay.
    """
    dem = {"n": 0}

    def _hoi() -> bool:
        dem["n"] += 1
        return False

    t0 = time.monotonic()
    ra = list(ngat.dung_khi_khach_cat(_nguon(2_000, []), _hoi))
    troi = time.monotonic() - t0

    assert len(ra) == 2_000
    tran = int(troi / ngat.NHIP_THAM_S) + 2
    assert dem["n"] <= tran, (
        f"tham {dem['n']} lan trong {troi:.2f}s — nhip la {ngat.NHIP_THAM_S}s "
        f"nen toi da ~{tran}. Dang tham moi manh.")


# -- 5. Khong hoi duoc thi CHAY TIEP, khong coi la da ngat -------------------

def test_ngat_chua_nem_thi_van_chay_tiep():
    def _hoi() -> bool:
        raise RuntimeError("khong bac duoc cau ve vong lap su kien")

    nk: list = []
    ra = list(ngat.dung_khi_khach_cat(_nguon(3, nk), _hoi))
    assert ra == [f"manh-{i}".encode() for i in range(3)], (
        "coi 'khong hoi duoc' la 'da ngat' => cat ngang mot khach dang doc")
    assert nk == ["mo", "dong"]


def test_nguon_khong_co_close_thi_khong_vo():
    """Mot iterator thuong (list_iterator) khong co `close` — dung nem."""
    ra = list(ngat.dung_khi_khach_cat(iter([b"a", b"b"]), lambda: False))
    assert ra == [b"a", b"b"]
