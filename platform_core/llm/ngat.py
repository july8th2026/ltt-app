"""ngat.py — khách ngắt giữa một lượt ĐỒNG BỘ thì cắt luôn lượt ở máy B. (spec §16)

## Vấn đề

Cửa stream đã có đường hủy: `luong_vlm` đóng `httpx.Client` ⇒ `upstream.close()`
⇒ llama.cpp nhả slot ≤ 1 s. Cửa **đồng bộ** thì không có gì cả — nó gọi một hàm
chặn (`executor.run`) và chỉ biết khách đã đi khi hàm ấy trả về, tức **sau** khi
GPU đã chạy xong một lượt không ai đọc.

## Vì sao không truyền thêm tham số xuống `executor.run`

`executor.run(db, params, *, timeout_s)` là **hợp đồng app** (`ToolSpec`), và
`apps/ltt_llm/executor.py` chỉ chuyển tiếp ba thứ nó biết. Thêm một tham số
`đóng-khi-ngắt` vào đó là bắt **mọi** app khai lại chữ ký cho một việc chỉ
`dieu_phoi` làm được.

⇒ Dùng `ContextVar`. Cửa mở một **sổ đóng** (danh sách rỗng) rồi chạy lời gọi
  trong `contextvars.copy_context()`; `dieu_phoi._goi_openai` ghi `client.close`
  vào sổ ấy. Bản sao ngữ cảnh chép **con trỏ**, nên danh sách là CÙNG MỘT vật
  thể ở hai luồng — cửa đóng được thứ luồng kia đang dùng.

⛔ Đừng đổi `SO_DONG` thành một giá trị bất biến (tuple, số). Bản sao ngữ cảnh
   chỉ chia sẻ được **vật thể thay đổi tại chỗ**; gán lại biến trong luồng con
   thì luồng cha không thấy gì, và tính năng này lặng lẽ thành không.
"""
from __future__ import annotations

import contextvars
import logging
import threading
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

_log = logging.getLogger(__name__)

log = logging.getLogger("platform_core.llm.ngat")

#: Sổ các hàm "đóng cửa ra mạng" của lượt đang chạy trong ngữ cảnh này.
SO_DONG: contextvars.ContextVar[Optional[list]] = contextvars.ContextVar(
    "ltt_llm_so_dong", default=None)

#: Nhịp thăm `is_disconnected` trong lúc gọi model (spec §16: ~1 s).
NHIP_THAM_S = 1.0


class KhachNgat(Exception):
    """Khách đã ngắt trong lúc lượt đang chạy.

    `ket_qua` là kết quả lời gọi **nếu** nó kịp về trước khi ta nhận ra: cửa
    quyết toán theo `usage` đo được, chứ không hoàn trọn một lượt đã chạy xong.
    """

    def __init__(self, ket_qua: Any = None):
        super().__init__("khach ngat giua luot")
        self.ket_qua = ket_qua


@contextmanager
def so_dong() -> Iterator[list]:
    """Mở một sổ đóng cho ngữ cảnh hiện tại."""
    ds: list = []
    moc = SO_DONG.set(ds)
    try:
        yield ds
    finally:
        SO_DONG.reset(moc)


def ghi_nhan(dong: Callable[[], None]) -> None:
    """Ghi một hàm đóng vào sổ của ngữ cảnh. Không có sổ ⇒ không làm gì."""
    ds = SO_DONG.get()
    if ds is not None:
        ds.append(dong)


def dong_het(ds: Optional[list]) -> int:
    """Đóng mọi cửa ra mạng đã ghi nhận. Trả số cửa đã đóng.

    ⚠️ Nuốt ngoại lệ có chủ ý: ta đang ở đường hủy, và một `close()` hỏng không
       được che mất việc quyết toán tiền ngay sau đó.
    """
    n = 0
    for dong in list(ds or ()):
        try:
            dong()
            n += 1
        except Exception:  # noqa: BLE001 - duong huy khong duoc nem
            log.exception("khong dong duoc cua ra mang khi khach ngat")
    return n


#: Han doc mot tin `receive` khi tham "khach ngat chua". Ngan co chu y: ham nay
#: chay tren LUONG GOI cua endpoint, moi `NHIP_THAM_S` mot lan, va moi mili giay
#: o day la mot mili giay luot goi khong duoc `join`.
HAN_DOC_NGAT_S = 0.05


def do_ngat(request) -> Callable[[], bool]:
    """Hàm hỏi *"khách ngắt chưa?"*, gọi được từ luồng threadpool của FastAPI.

    ⭐ `Request.is_disconnected()` là coroutine, còn thân của một endpoint `def`
       chạy ở luồng công nhân do `anyio.to_thread.run_sync` sinh ra — nên
       `anyio.from_thread.run` bắc được cầu về vòng lặp sự kiện. Ngoài luồng ấy
       (ví dụ một phép kiểm gọi thẳng) thì không có cầu nào: trả `False` và để
       lượt chạy bình thường, **không** coi im lặng là "đã ngắt".
    """
    if request is None:
        return lambda: False

    async def _doc_mot_tin() -> bool:
        """Doc `receive` voi HAN GIO NGAN. Tra True neu do la `http.disconnect`.

        🔴 VI SAO KHONG DUNG `Request.is_disconnected()` — do duoc 13/09 (L-06).

           Ham ay doc `receive` trong mot `CancelScope` **da huy san**:

               with anyio.CancelScope() as cs:
                   cs.cancel()
                   message = await self._receive()

           Khong co middleware thi uvicorn tra ngay tu hang doi nen van kip. Co
           `BaseHTTPMiddleware` thi `receive` ma route nhan duoc la
           `receive_or_disconnect`, va ham ay **mo mot task group** — tuc co mot
           diem kiem tra — nen scope da huy cat truoc khi gia tri ve.
           `is_disconnected()` khi ay tra **False mai mai**.

           Do bang mot thi nghiem mot bien so, cung phien ban thu vien, cung
           hinh dang endpoint `def`:

               khong middleware        -> thay ngat o giay 2,02
               co BaseHTTPMiddleware   -> KHONG BAO GIO thay

           `server/app.py` co `AccessControlMiddleware` va
           `PublicApiGuardMiddleware`, ca hai ke thua `BaseHTTPMiddleware`. Nen
           tinh nang huy-khi-khach-ngat da chet lang le tu luc chung duoc them
           vao, va no chi lo ra o hoa don: slot bi giu 24-36 s cho mot nguoi da
           di, va khach van bi tinh tien phan token khong nhan duoc.

        ⛔ CHI AN TOAN KHI THAN DA DOC XONG. Doc mot tin la **lay** no khoi hang
           doi; neu than chua doc het thi ta vua nuot mat mot manh than. Rao o
           duoi kiem dung dieu do bang `_body` — thu Starlette dat sau khi
           `body()` chay xong.
        """
        import anyio

        tin: dict = {}
        with anyio.move_on_after(HAN_DOC_NGAT_S):
            tin = await request.receive()
        return bool(tin) and tin.get("type") == "http.disconnect"

    def _hoi() -> bool:
        try:
            import anyio.from_thread

            # ⛔ Than CHUA doc xong ⇒ khong duoc cham `receive`. Ve duong cu, va
            #    duong cu se tra False — dung, vi mot cua stream ma mat mot manh
            #    than la mot loi nang hon nhieu so voi mot slot giu lau.
            if not hasattr(request, "_body"):
                return bool(anyio.from_thread.run(request.is_disconnected))
            return bool(anyio.from_thread.run(_doc_mot_tin))
        except Exception as e:  # noqa: BLE001 - khong hoi duoc thi coi nhu con ket noi
            # ⚠️ Nuốt lỗi ở đây là CỐ Ý — hỏi không được thì coi như khách còn
            #    kết nối, tức nghiêng về "chạy tiếp" thay vì huỷ nhầm một lượt
            #    đang tính tiền. Nhưng nuốt **lặng lẽ** thì khác: nếu
            #    `anyio.from_thread.run` hỏng vì một lý do cấu trúc (đổi phiên
            #    bản, gọi ngoài luồng worker) thì tính năng huỷ-khi-khách-ngắt
            #    chết hẳn mà không ai biết — và nó chỉ lộ ra ở hoá đơn.
            #
            # `debug` chứ không `warning`: hàm này chạy theo NHỊP TIM, một cảnh
            # báo mỗi nhịp sẽ nhấn chìm log thật.
            _log.debug("khong hoi duoc trang thai ket noi: %r", e)
            return False

    return _hoi


def chay_canh_ngat(chay: Callable[[], Any], *,
                   ngat_chua: Optional[Callable[[], bool]] = None,
                   nhip_s: Optional[float] = None) -> Any:
    """Chạy `chay()` và thăm `ngat_chua()` mỗi `nhip_s` giây song song.

    Ngắt ⇒ đóng mọi cửa đã ghi nhận (httpx tới máy B), **chờ lời gọi kết thúc**
    rồi ném `KhachNgat` kèm kết quả nếu nó kịp về.

    ⛔ Chờ luồng kết thúc chứ không bỏ mặc nó: một luồng còn sống đang cầm phiên
       CSDL và sẽ ghi vào cùng chỗ mà đường hủy sắp quyết toán. Hai bên ghi một
       lượt tiền là đúng khuôn của một sai lệch sổ sách.

    ⚠️ NỢ ĐÃ BIẾT (ghi ở rà soát 1.5): `chay` mang theo `Session` của request
       sang luồng này, và `Session` của SQLAlchemy **không** an toàn đa luồng.
       Hiện an toàn vì luồng gọi chỉ `join` chứ không chạm `db` trong lúc chờ,
       và đường hủy chỉ chạm sau khi `join` xong. Sửa đúng là truyền một phiên
       RIÊNG cho lời gọi — để lượt rà cuối quyết.
    """
    nhip = NHIP_THAM_S if nhip_s is None else float(nhip_s)
    with so_dong() as ds:
        if ngat_chua is None:
            return chay()

        ket: dict = {}
        ctx = contextvars.copy_context()

        def _chay() -> None:
            try:
                ket["gt"] = ctx.run(chay)
            except BaseException as e:                      # noqa: BLE001
                ket["loi"] = e

        luong = threading.Thread(target=_chay, name="ltt-dong-bo", daemon=True)
        luong.start()
        da_ngat = False
        while True:
            luong.join(max(0.0, nhip))
            if not luong.is_alive():
                break
            if not da_ngat and ngat_chua():
                da_ngat = True
                log.warning("khach ngat giua luot dong bo — dong %s cua ra mang",
                            dong_het(ds))
        if da_ngat:
            raise KhachNgat(ket.get("gt"))
        if "loi" in ket:
            raise ket["loi"]
        return ket.get("gt")
