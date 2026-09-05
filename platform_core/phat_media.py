r"""phat_media.py — MỘT bộ trả lời HTTP Range cho toàn nền tảng.

    from platform_core.phat_media import phat_tu_kho

    # app đã kiểm sở hữu xong, chỉ còn việc chuyển byte:
    return phat_tu_kho(kho, khoa, kieu_noi_dung="audio/wav",
                       dai_range=request.headers.get("range"))

## Vì sao module này tồn tại

Đo ngày 2026-09-05 (`docs/MOBILE/02_BASELINE.md`): **năm** app tự viết bộ phân
tích `Range`, gần như giống nhau từng dòng — `taovideo`, `taoclipngan`,
`upscalevideo`, `agent`, `autosubvideo` — và **hai** app phục vụ media mà không
có Range gì cả: `ltt_voice`, `chatltt`.

⭐ Điều đáng nói không phải "có năm bản chép". Là **cả năm bản đều mang cùng bốn
   khiếm khuyết**, nên sửa một chỗ không cứu bốn chỗ kia, và không ai biết mình
   đang chạy bản nào:

1. **Không bao giờ trả `416`.** Dải vô nghĩa bị nắn thành `start=0` rồi trả `206`
   với `Content-Range` sai. Trình phát tin con số ấy.
2. **Suffix range hiểu ngược.** `bytes=-500` nghĩa là *500 byte CUỐI*. Bản cũ đọc
   `s=""` → `start=0`, `e="500"` → `end=500`, tức trả **501 byte ĐẦU**. Đây là
   sai dữ liệu, không phải sai định dạng — và nó im lặng.
3. **`bytes=0-` nuốt cả tệp vào RAM.** `end = total-1` rồi `f.read(length)`.
   Chrome gửi đúng dạng này thường xuyên nhất; một video 400 MB là 400 MB RSS
   mỗi lượt xem.
4. **`start > end` xử lý mỗi nơi một kiểu.** Bốn app đặt `start = 0` và *giữ*
   `end`; `agent` đặt `start, end = 0, total-1`. Cùng đầu vào, hai đầu ra.

🔴 Nên module này **không chuẩn hoá cái đang có** — nó viết lại theo RFC 9110.
   Việc migrate năm app kia là thay một bản sai bằng một bản đúng, không phải
   gom năm bản giống nhau về một chỗ.

## Ranh giới — app giữ quyền, shared giữ đường ống

    app                          module nay
    ---                          ----------
    kiem so huu khoa      -->    phan tich Range
    chon media_type              200 / 206 / 416
    quyet dinh redirect R2       Accept-Ranges, Content-Range, Content-Length
                                 phat byte theo khoi 1 MiB

⛔ **Phép kiểm sở hữu KHÔNG được chuyển lên đây.** Mỗi app có hình dạng khoá
   riêng (`voice/out/<uid>/…`, `taovideo/<uid>/…`), và một bản chép thứ hai của
   một phép kiểm bảo mật là bản sẽ lệch. Gọi module này *sau* khi đã kiểm.

⛔ **Redirect R2 cũng ở lại app.** Mã trạng thái khác nhau giữa các app (302 và
   307), và `autosubvideo` còn chặn nó sau một cờ. Đó là chính sách sản phẩm,
   không phải chuyện vận chuyển byte.
"""
from __future__ import annotations

import logging
from typing import BinaryIO, Optional

from starlette.responses import Response, StreamingResponse

_log = logging.getLogger(__name__)

#: Đọc theo khối 1 MiB. Đủ lớn để không phải gọi `read()` hàng nghìn lần cho một
#: video, đủ nhỏ để một lượt tải không bao giờ chiếm quá 1 MiB RAM cho phần thân.
KHOI = 1024 * 1024

#: `Range` không nhận ra được thì **bỏ qua** và trả toàn tệp — RFC 9110 §14.2 nói
#: đúng như vậy. Chỉ dải *đọc hiểu được mà không thoả mãn nổi* mới là 416.
_BO_QUA = object()


def phan_tich_range(dai: Optional[str], tong: int):
    """`Range` -> `(dau, cuoi)` bao gồm hai đầu, hoặc `_BO_QUA`, hoặc `None`.

    - `_BO_QUA`: không có header, sai cú pháp, hoặc nhiều dải → gọi nơi trả 200.
    - `None`: đọc hiểu được nhưng **không thoả mãn nổi** → 416.
    - `(dau, cuoi)`: dải hợp lệ → 206.

    ⚠️ Tệp rỗng trả `_BO_QUA` chứ không phải `None`. Đúng chuẩn thì mọi dải trên
       tệp 0 byte đều không thoả mãn nổi; nhưng trả 416 cho một tệp rỗng chỉ làm
       trình phát báo lỗi thay vì phát ra sự im lặng đúng độ dài. 200 với thân
       rỗng là câu trả lời vô hại hơn, và nó không giấu lỗi nào cả.
    """
    if not dai or tong <= 0:
        return _BO_QUA
    dai = dai.strip()
    if not dai.lower().startswith("bytes="):
        return _BO_QUA
    phan = dai[6:].strip()
    if "," in phan:
        # Nhiều dải là hợp lệ, và máy chủ được phép trả toàn tệp thay vì dựng
        # multipart/byteranges. Ta chọn đường đó — multipart thêm một bộ sinh
        # nữa để bảo trì mà không trình phát nào ở đây cần.
        return _BO_QUA
    if "-" not in phan:
        return _BO_QUA
    dau_txt, _, cuoi_txt = phan.partition("-")
    dau_txt, cuoi_txt = dau_txt.strip(), cuoi_txt.strip()

    if not dau_txt:
        # bytes=-N  ->  N byte CUOI. Day la cho bon ban chep cu doc nguoc.
        if not cuoi_txt.isdigit():
            return _BO_QUA
        n = int(cuoi_txt)
        if n == 0:
            return None            # "0 byte cuoi" khong thoa man noi
        return max(0, tong - n), tong - 1

    if not dau_txt.isdigit():
        return _BO_QUA
    dau = int(dau_txt)
    if dau >= tong:
        return None                # bat dau sau khi tep het
    if not cuoi_txt:
        return dau, tong - 1
    if not cuoi_txt.isdigit():
        return _BO_QUA
    cuoi = min(int(cuoi_txt), tong - 1)
    if cuoi < dau:
        return None
    return dau, cuoi


def doc_khoi(luong: BinaryIO, dau: int, do_dai: int):
    """Phát `do_dai` byte từ vị trí `dau`, theo khối, rồi đóng luồng.

    Xử lý cả hai loại luồng mà `platform_core.storage` trả về: tệp cục bộ (tua
    được) và `StreamingBody` của R2 (**không** tua được — phải đọc bỏ).
    """
    try:
        try:
            luong.seek(dau)
        except (AttributeError, OSError):
            da_bo = 0
            while da_bo < dau:
                m = luong.read(min(KHOI, dau - da_bo))
                if not m:
                    return
                da_bo += len(m)
        con = do_dai
        while con > 0:
            m = luong.read(min(KHOI, con))
            if not m:
                return
            con -= len(m)
            yield m
    finally:
        # Bản cũ ở `autosubvideo` không có `finally` này: một client ngắt giữa
        # chừng thì bộ sinh bị bỏ dở và mô tả tệp treo tới lúc GC dọn.
        try:
            luong.close()
        except Exception as e:  # noqa: BLE001 - kho co the nem nhieu loai loi
            # ⚠️ Không ném: đóng hỏng thì byte ĐÃ tới người dùng rồi, ném ở đây
            #    chỉ biến một lượt tải thành công thành một lỗi. Nhưng cũng KHÔNG
            #    im: một kho không đóng được mô tả tệp là dấu hiệu rò tài nguyên,
            #    và nó chỉ lộ ra khi máy chủ hết handle — tức ở chỗ khó tìm nhất.
            _log.warning("khong dong duoc luong media: %s", type(e).__name__)


def phat_tu_kho(kho, khoa: str, *, kieu_noi_dung: str,
                dai_range: Optional[str] = None,
                tong: Optional[int] = None,
                tieu_de_them: Optional[dict] = None) -> Response:
    """Trả 200 / 206 / 416 cho `khoa` trong `kho`, đúng RFC 9110.

    `kho` là `platform_core.storage.Storage`. Nơi gọi **phải** đã kiểm sở hữu.
    Ném `StorageError`/`FileNotFoundError` lên cho nơi gọi quyết định 404 —
    module này không biết app muốn giấu hay lộ sự tồn tại của khoá.
    """
    if tong is None:
        tong = kho.size(khoa)

    tieu_de = {"Accept-Ranges": "bytes"}
    if tieu_de_them:
        tieu_de.update(tieu_de_them)

    pv = phan_tich_range(dai_range, tong)

    if pv is None:
        # 416 PHAI kem `Content-Range: bytes */N` — do la cach client biet do dai
        # that de hoi lai cho dung. Thieu no thi 416 la mot nga cut.
        tieu_de["Content-Range"] = f"bytes */{tong}"
        return Response(status_code=416, headers=tieu_de)

    if pv is _BO_QUA:
        tieu_de["Content-Length"] = str(tong)
        # ⚠️ Đi qua `doc_khoi` chứ không đưa thẳng luồng cho `StreamingResponse`.
        #    Starlette lặp trên thứ ta đưa, và **lặp trên một tệp nhị phân là lặp
        #    theo dòng** — nó cắt ở mỗi byte `0x0A`, nên một tệp WAV bị băm thành
        #    hàng nghìn mẩu dài ngắn ngẫu nhiên. Năm bản chép cũ đều làm vậy; nó
        #    chạy được nên không ai để ý. `doc_khoi` cho khối đều 1 MiB và **đóng
        #    luồng** khi xong, thứ mà bản cũ cũng không làm.
        return StreamingResponse(doc_khoi(kho.open(khoa), 0, tong),
                                 media_type=kieu_noi_dung, headers=tieu_de)

    dau, cuoi = pv
    do_dai = cuoi - dau + 1
    tieu_de["Content-Range"] = f"bytes {dau}-{cuoi}/{tong}"
    tieu_de["Content-Length"] = str(do_dai)
    return StreamingResponse(doc_khoi(kho.open(khoa), dau, do_dai),
                             status_code=206, media_type=kieu_noi_dung,
                             headers=tieu_de)
