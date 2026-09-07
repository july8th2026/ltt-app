"""chia_doan.py — cắt văn bản thành ĐOẠN để truy hồi và trích dẫn. (H44 P06 b3)

## Vì sao KHÔNG tái dùng `apps/ltt_voice/text_pipeline.chia_doan`

Hai lý do, và lý do thứ hai mới là lý do thật:

1. **Hợp đồng**: app không được nhập app (`CLAUDE.md`). Chuyển hàm kia lên
   `platform_core` là sửa nền tảng, và nó chạm một app **đang phục vụ khách**.

2. **Hai mục tiêu khác nhau ở đúng chỗ quyết định.** Chia cho đọc thành tiếng
   **không được chồng lấn** — chồng là đọc lặp một câu. Chia cho truy hồi
   **phải chồng lấn**: một dữ kiện nằm vắt qua ranh giới mà không chồng thì
   không đoạn nào chứa đủ nó, và câu trả lời sẽ thiếu đúng phần người ta hỏi.

⭐ Nhưng có một tính chất **chung**, và nó vay được: *"cắt giữa câu là cắt giữa
   một mệnh đề"*. Với TTS nó hỏng ngữ điệu; với truy hồi nó hỏng cả hai đầu —
   đoạn tìm ra không đọc được, và trích dẫn chỉ vào nửa câu. Nên thứ tự nhượng
   bộ ở đây giống bên ấy: **câu → dấu phẩy → cắt cứng**, mỗi bậc chỉ chạy khi
   bậc trước không đủ.

## Ba tham số, và vì sao từng con số

⛔ Không con số nào ở đây là linh cảm; nhưng cũng không con số nào được đo trên
   corpus thật của khách, vì **chưa có khách nào tải tài liệu lên**. Chúng là
   giá trị khởi đầu **có căn cứ**, và mục §6 của P06 đòi đo lại sau 20–50 tài
   liệu thật. Ghi ra đây để lần sau không ai đọc chúng như đã được đo.

* `TRAN` = 1.200 ký tự. Tiếng Việt ~4,5 ký tự/token ⇒ ~270 token/đoạn. Năm đoạn
  vào ngữ cảnh là ~1.350 token — vừa với ngân sách một lượt mà vẫn đủ dài để
  một đoạn tự nó có nghĩa khi hiện ra làm trích dẫn.
* `CHONG` = 150 ký tự (12,5%). Đủ chứa một câu ngắn trọn vẹn nằm vắt ranh giới.
  Chồng nhiều hơn làm chỉ số phình mà không tìm ra thêm gì; ít hơn thì mất đúng
  cái nó sinh ra để cứu.
* `TOI_THIEU` = 40 ký tự. Dưới mức này thì đoạn là rác của bộ trích (số trang
  lẻ, tiêu đề chạy), không phải nội dung — và mỗi mẩu rác vẫn tốn một hàng CSDL
  và một chỗ trong kết quả tìm.

⚠️ **Trần đặt DƯỚI nhu cầu bình thường thì biến thất bại thành mặc định.** Đó là
   lý do `TRAN` không nhỏ hơn: một đoạn 400 ký tự nghe có vẻ "gọn", nhưng nó cắt
   phần lớn đoạn văn thật làm đôi, và khi ấy **mọi** truy hồi đều phải ghép —
   tức chế độ hỏng thành chế độ thường.
"""
from __future__ import annotations

import hashlib
import re

TRAN = 1200
CHONG = 150
TOI_THIEU = 40

#: Ranh giới câu. Giữ dấu kết ở cuối câu trước (`(?<=...)`) nên ghép lại không mất gì.
_CAU = re.compile(r"(?<=[.!?…])\s+|\n{2,}")
_PHAY = re.compile(r"(?<=[,;:])\s+")
#: Khoảng trắng thừa của bộ trích PDF: xuống dòng giữa câu, dấu cách kép.
_TRANG_THUA = re.compile(r"[ \t]+")


def don(tho: str) -> str:
    """Dọn khoảng trắng mà **không** dán liền hai đoạn văn.

    ⛔ `\\n` đơn trong PDF là xuống dòng do bề rộng trang, không phải ranh giới ý
       ⇒ thay bằng dấu cách. `\\n\\n` thì ngược lại: đó là ranh giới thật, giữ.
    """
    if not tho:
        return ""
    tho = tho.replace("\r\n", "\n").replace("\r", "\n")
    tho = re.sub(r"\n{3,}", "\n\n", tho)
    tho = re.sub(r"(?<!\n)\n(?!\n)", " ", tho)
    return _TRANG_THUA.sub(" ", tho).strip()


def _cat_cung(cau: str, tran: int) -> list[str]:
    """Bậc nhượng bộ cuối. Chỉ chạy khi một câu dài hơn cả trần."""
    return [cau[i:i + tran] for i in range(0, len(cau), tran)]


def _don_vi(van: str, tran: int) -> list[str]:
    """Câu → (nếu quá dài) dấu phẩy → (nếu vẫn quá dài) cắt cứng."""
    ra: list[str] = []
    for cau in (c.strip() for c in _CAU.split(van) if c and c.strip()):
        if len(cau) <= tran:
            ra.append(cau)
            continue
        for manh in (m.strip() for m in _PHAY.split(cau) if m and m.strip()):
            ra.extend([manh] if len(manh) <= tran else _cat_cung(manh, tran))
    return ra


def chia(van: str, *, tran: int = TRAN, chong: int = CHONG,
         toi_thieu: int = TOI_THIEU) -> list[str]:
    """Cắt `van` thành các đoạn ≤ `tran`, chồng lấn `chong`, bỏ mẩu < `toi_thieu`.

    ⭐ Chồng lấn tính bằng **ký tự đuôi của đoạn trước**, nhưng vẫn cắt ở ranh
       giới câu: phần chồng là các câu cuối cùng của đoạn trước cộng lại vừa
       trong `chong`. Chồng giữa câu thì đoạn sau mở đầu bằng nửa câu, và một
       trích dẫn mở đầu bằng nửa câu là một trích dẫn không dùng được.
    """
    van = don(van)
    if not van:
        return []
    tran = max(1, int(tran))
    chong = max(0, min(int(chong), tran - 1))

    don_vi = _don_vi(van, tran)
    ra: list[str] = []
    dem: list[str] = []
    dai = 0

    def day() -> None:
        nonlocal dem, dai
        if not dem:
            return
        ra.append(" ".join(dem).strip())
        # Giữ lại các đơn vị CUỐI vừa trong `chong` để làm phần chồng.
        giu: list[str] = []
        n = 0
        for u in reversed(dem):
            if n + len(u) > chong:
                break
            giu.insert(0, u)
            n += len(u) + 1
        dem = giu
        dai = sum(len(u) + 1 for u in dem)

    for u in don_vi:
        if dem and dai + len(u) + 1 > tran:
            day()
        dem.append(u)
        dai += len(u) + 1
    if dem:
        ra.append(" ".join(dem).strip())

    # ⛔ Bỏ mẩu quá ngắn — TRỪ khi cả tệp chỉ có đúng một mẩu. Một tệp ngắn thật
    #    (một ghi chú ba dòng) mà bị bỏ sạch thì người dùng thấy "trích xong, 0
    #    đoạn", và đó là một câu trả lời tệ hơn cả một lỗi.
    loc = [d for d in ra if len(d) >= toi_thieu]
    return loc or ([ra[0]] if ra else [])


def bam(noi_dung: str) -> str:
    """Vân tay của một đoạn. Để "đã trích rồi" kiểm được ở tầng dữ liệu."""
    return hashlib.sha256(noi_dung.encode("utf-8")).hexdigest()[:64]
