"""test_1241 — cua DONG BO phai CAT DUOC luot khi khach di. L-06, 13/09/2026.

## Su that do duoc tren production

Khach cat ket noi giua chung, slot van bi giu:

    max_tokens  900 -> 15,37 s
    max_tokens 1024 -> 17,17 s
    max_tokens 2000 -> 31,90 s      (2000/1024 = 1,95x ; 31,90/17,17 = 1,86x)

Gan ti le thuan => khong phai ro lease, khong phai han cho co dinh: nen tang
**chay het** roi moi tra slot. Nguong cong M la 2 s. Va khach VAN bi tinh tien
cho token ho khong nhan duoc.

## Ba gia thuyet, va hai cai dau deu SAI

| # | gia thuyet | phep do | ket |
|---|---|---|---|
| 1 | Cloudflare che mat `http.disconnect` | do ca qua CF (18,67 s) lan loopback (16,54 s) | **SAI** — loopback cung hong |
| 2 | `is_disconnected()` khong bao gio thay | thi nghiem uvicorn toi gian | **SAI** — thay o giay 2,02 |
| 3 | phat hien duoc nhung khong CAT duoc | doc `dieu_phoi._dong()` | **DUNG** |

## Goc

`dieu_phoi._dong()` — duong huy day du — lam ba viec, va HAI trong ba phu thuoc
`ma_luot`:

    1. huy_luot.danh_dau(ma_luot)       chi khi CO ma
    2. client.close()                   luon luon
    3. _bao_may_b_huy(..., ma_luot)     chi khi CO ma   <- "bao may B thoi sinh chu"

`apps/ltt_llm/executor.run()` khong nhan `ma_luot`, nen cua dong bo chi lam viec
2 — ma `httpx.Client.close()` **khong cat** mot request dang bay o luong khac.
May B sinh chu toi het, luong goi cho toi het, `chay_canh_ngat` cho luong ay
truoc khi nem `KhachNgat`.

⛔ Bo nay chot o TANG HOP DONG giua hai lop, khong o tang HTTP: cai hong la mot
   tham so khong duoc truyen, va do la thu mot phep kiem hop dong nhin thay
   duoc con mot phep kiem end-to-end thi phai dung ca may B.
"""
import inspect

from apps.ltt_llm.executor import EXECUTOR


def test_run_nhan_ma_luot():
    """Chot canh cua: `run()` phai co tham so `ma_luot`.

    Xoa no di thi cua dong bo mat duong cat, va mat mot cach IM LANG — khong
    ngoai le, khong log, chi la mot hoa don cao hon binh thuong.
    """
    tham = inspect.signature(EXECUTOR.run).parameters
    assert "ma_luot" in tham, (
        "bo `ma_luot` la tra cua dong bo ve trang thai L-06: khach di ma may B "
        "van sinh chu toi het")


def test_ma_luot_di_TOI_features_chay():
    """⛔ Co tham so chua du — no phai ĐI TỚI `features.chay`.

    Mot `run(..., ma_luot=...)` nhan roi bo qua van xanh o phep kiem tren, va
    van hong y het. Phep kiem nay bat dung cho ay.
    """
    thay = {}

    def gia(db, params, **kw):
        thay.update(kw)
        return "xong"

    from apps.ltt_llm import features
    goc = features.chay
    try:
        features.chay = gia
        EXECUTOR.run(None, {"model": "ltt-3.8"}, timeout_s=1.0, ma_luot="ch_abc")
    finally:
        features.chay = goc
    assert thay.get("ma_luot") == "ch_abc"


def test_ma_luot_rong_thi_KHONG_truyen_xuong():
    """Rong van hop le: ben goi noi bo khong can cat.

    ⭐ Va no phai **khong truyen** chu khong phai truyen chuoi rong: `features.chay`
       co mac dinh rieng, va mot chuoi rong truyen xuong se de len mac dinh ay.
       Khac biet nay vo hinh cho toi ngay ai do doi mac dinh.
    """
    thay = {}

    def gia(db, params, **kw):
        thay.update(kw)
        return "xong"

    from apps.ltt_llm import features
    goc = features.chay
    try:
        features.chay = gia
        EXECUTOR.run(None, {"model": "ltt-3.8"}, timeout_s=1.0)
    finally:
        features.chay = goc
    assert "ma_luot" not in thay


def test_cua_dong_bo_truyen_request_id_xuong_run():
    """Chot ben GOI: `server/api/chat.py` phai truyen `ma_luot=request_id`.

    ⛔ Doc ma nguon chu khong goi that: goi that doi CSDL, admission, tien va
       may B — bon thu khong lien quan gi toi menh de nay. Mot phep kiem phai
       hep bang dung dieu no do.
    """
    import pathlib

    import server.api.chat as m

    nguon = pathlib.Path(m.__file__).read_text(encoding="utf-8")
    i = nguon.find("executor.run(")
    assert i > 0, "khong tim thay loi goi executor.run trong chat.py"
    khoi = nguon[i:i + 700]
    assert "ma_luot=request_id" in khoi, (
        "cua dong bo phai truyen ma luot xuong, khong thi duong huy chi dong "
        "socket va may B van sinh chu toi het (L-06)")
