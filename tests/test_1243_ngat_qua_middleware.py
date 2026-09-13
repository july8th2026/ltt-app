"""test_1243 — phat hien khach NGAT phai song qua `BaseHTTPMiddleware`. L-06.

## Su that do duoc 13/09/2026

Mot thi nghiem MOT BIEN SO, cung phien ban thu vien, cung hinh dang endpoint
`def` nhu cua dong bo that:

    khong middleware        -> thay khach ngat o giay 2,02
    co BaseHTTPMiddleware   -> KHONG BAO GIO thay

`server/app.py` co `AccessControlMiddleware` va `PublicApiGuardMiddleware`, ca
hai ke thua `BaseHTTPMiddleware`. Nen tinh nang huy-khi-khach-ngat da chet lang
le tu luc chung duoc them vao, va no chi lo ra o hoa don: slot bi giu 24-36 s
cho mot nguoi da di, va khach van bi tinh tien phan token khong nhan duoc.

## Co che, doc tu chinh ma Starlette

`Request.is_disconnected()` doc `receive` trong mot `CancelScope` **da huy san**:

    with anyio.CancelScope() as cs:
        cs.cancel()
        message = await self._receive()

Khong middleware: `receive` cua uvicorn tra ngay tu hang doi, khong qua diem
kiem tra nao, nen gia tri ve kip.

Co `BaseHTTPMiddleware`: `receive` ma route nhan la `receive_or_disconnect`, va
ham ay **mo mot task group** -- tuc co diem kiem tra -- nen scope da huy cat
truoc khi gia tri ve. Ket qua: `is_disconnected()` tra False MAI MAI.

## ⛔ Ban DAU cua bo nay quet VAN BAN, va no da xanh qua mot dot bien

Ban dau ba phep kiem doc `inspect.getsource(do_ngat)` va tim chuoi `_body`,
`request.receive()`. Tiem dot bien (go rao, quay ve `is_disconnected`) -- **van
xanh**, vi hai chuoi ay con nam trong DOCSTRING giai thich.

⇒ Viet lai theo HANH VI: dung mot `Request` gia, roi hoi `do_ngat` lam gi voi
  no. Mot phep kiem quet van ban chi bao ve thu no NHIN THAY, va no nhin thay
  loi giai thich chu khong nhin thay ma.
"""
import anyio
import pytest

from platform_core.llm import ngat


class RequestGia:
    """Du hinh dang cho `do_ngat`, va DEM so lan `receive` bi cham."""

    def __init__(self, tin: dict | None, *, than_da_doc: bool):
        self._tin = tin or {}
        self.so_lan_receive = 0
        self.so_lan_is_disconnected = 0
        if than_da_doc:
            # Starlette dat thuoc tinh nay sau khi `body()` chay xong.
            self._body = b"{}"

    async def receive(self) -> dict:
        self.so_lan_receive += 1
        return self._tin

    async def is_disconnected(self) -> bool:
        self.so_lan_is_disconnected += 1
        return False


def _hoi(req) -> bool:
    """Goi vi tu trong mot LUONG CONG NHAN anyio — dung noi endpoint `def` chay.

    ⛔ Goi thang tu luong chinh thi `anyio.from_thread.run` nem, `do_ngat` nuot,
       va phep kiem se xanh cho MOI ban cai dat. Phai dung dung ngu canh that.
    """
    async def chay():
        return await anyio.to_thread.run_sync(ngat.do_ngat(req))

    return bool(anyio.run(chay))


def test_thay_ngat_khi_receive_tra_http_disconnect():
    """Menh de chinh: than da doc xong + `receive` tra `http.disconnect` => True.

    Day la truong hop ma `is_disconnected()` **khong** lam duoc sau
    `BaseHTTPMiddleware`, va la ly do ca bo sua ton tai.
    """
    req = RequestGia({"type": "http.disconnect"}, than_da_doc=True)
    assert _hoi(req) is True
    assert req.so_lan_receive == 1


def test_khong_thay_ngat_khi_khong_co_tin():
    """Doi chung: khong co tin nao thi KHONG duoc bao ngat.

    Thieu phep nay thi mot ban cai dat `return True` cung xanh o phep tren.
    """
    req = RequestGia(None, than_da_doc=True)
    assert _hoi(req) is False


def test_tin_khac_disconnect_khong_bi_doc_thanh_ngat():
    req = RequestGia({"type": "http.request", "body": b"x"}, than_da_doc=True)
    assert _hoi(req) is False


def test_than_CHUA_doc_xong_thi_KHONG_duoc_cham_receive():
    """🔴 RAO AN TOAN, va no quan trong hon menh de chinh.

    Doc mot tin la **lay** no khoi hang doi. Than chua doc het ma cham vao la
    nuot mat mot manh than — mot loi nang hon nhieu, va im lang hon nhieu, so
    voi mot slot bi giu lau.

    ⇒ Khong co `_body` thi phai ve duong cu (`is_disconnected`), va `receive`
      phai **khong bi cham lan nao**.
    """
    req = RequestGia({"type": "http.disconnect"}, than_da_doc=False)
    assert _hoi(req) is False
    assert req.so_lan_receive == 0, "da cham `receive` khi than chua doc xong"
    assert req.so_lan_is_disconnected == 1, "phai ve duong cu, khong bo qua"


def test_khong_co_request_thi_tra_False_chu_khong_nem():
    assert ngat.do_ngat(None)() is False


def test_hoi_khong_duoc_thi_coi_nhu_khach_con_day():
    """Fail-open co chu y: hoi khong duoc thi chay tiep, dung huy nham mot luot
    dang tinh tien. `object()` khong co `_body` lan `is_disconnected`."""
    assert ngat.do_ngat(object())() is False


def test_han_doc_la_mot_hang_so_co_ten():
    """Ham nay chay tren LUONG GOI cua endpoint, moi nhip tham mot lan. Mot con
    so go tay o giua than ham la con so khong ai tim thay khi can chinh."""
    assert isinstance(ngat.HAN_DOC_NGAT_S, float)
    assert 0 < ngat.HAN_DOC_NGAT_S <= 0.5, ngat.HAN_DOC_NGAT_S


@pytest.mark.parametrize("tin", [{"type": "http.disconnect"}, None])
def test_khong_bao_gio_nem_ra_ngoai(tin):
    """Vi tu nay chay trong vong lap tham cua `chay_canh_ngat`. Mot ngoai le o
    day giet luot goi that — tra `bool` la hop dong, khong phai su tien tay."""
    assert isinstance(_hoi(RequestGia(tin, than_da_doc=True)), bool)
