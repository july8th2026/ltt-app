"""trich_van_ban.py — byte của một tệp → văn bản theo TRANG. (H44 P06 bước 3)

## 🔴 Ba loại hỏng, ba ngoại lệ — và vì sao gộp chúng là một lỗi CÓ THẬT

Ngày 06/09 tôi tìm ra ở `apps/chataistudio/features.py:46-51`:

    elif mime == "application/pdf":
        try:
            from pypdf import PdfReader
            text = ...
        except Exception as exc:
            raise ValueError(_t('Không đọc được nội dung PDF.')) from exc

`pypdf` **không tồn tại** trên máy chủ (đo: vắng ở cả bốn `requirements*.txt` và
ở `C:/LTTPlatform/venv`). Nên `ImportError` rơi vào `except Exception` và đi ra
với câu *"Không đọc được nội dung PDF."* — tức **máy chủ thiếu thư viện, mà
thông báo đổ lỗi cho tệp của khách**.

⭐ Cái giá không phải một lỗi bị che. Khách sẽ đi thử tệp khác, rồi tệp khác
   nữa, rồi kết luận sản phẩm hỏng — và **không ai báo lỗi**, vì thông báo đã
   trả lời họ rồi. Một thông báo lỗi trỏ sai hướng đắt hơn im lặng, vì nó khiến
   người ta đi tìm ở chỗ không có gì.

⇒ Ba loại phải phân biệt được **ở tầng kiểu**, không phải ở tầng câu chữ:

    ThieuThuVien   may chu thieu thu vien   -> viec cua VAN HANH, khong phai cua khach
    KhongHoTro     dinh dang khong nhan     -> viec cua NGUOI DUNG, noi truoc khi ho tra tien
    KhongDocDuoc   tep that su hong/ma hoa  -> viec cua TEP, va no la ca THUONG (PDF anh scan)
"""
from __future__ import annotations

import io
import json
import logging

log = logging.getLogger(__name__)

#: Định dạng nhận được. Cùng tập với ô chọn tệp — một giao diện **mời** người
#: dùng chọn thứ ta không đọc được là một lời hứa hỏng.
PDF = "application/pdf"
CHU_THUAN = ("text/plain", "text/markdown", "text/csv", "application/json")
DUOC_NHAN = (PDF, *CHU_THUAN)

#: Trần ký tự cho MỘT tệp. Trần Cloudflare là 100 MB/request, và một PDF 100 MB
#: có thể ra hàng chục triệu ký tự — tức hàng chục nghìn đoạn cho một tệp.
#:
#: ⚠️ 2.000.000 ≈ 700 trang chữ dày. Đặt ở đây vì "trần đặt DƯỚI nhu cầu bình
#:    thường biến thất bại thành MẶC ĐỊNH": tài liệu người ta hỏi thường là
#:    10–50 trang, nên trần này cao hơn ca thường **hai bậc độ lớn**. Nó chặn
#:    ca bệnh lý, không chặn ca thường.
TRAN_KY_TU = 2_000_000


class ThieuThuVien(RuntimeError):
    """Máy chủ thiếu thư viện. KHÔNG phải lỗi của tệp, KHÔNG phải lỗi của khách."""


class KhongHoTro(ValueError):
    """Định dạng không nhận. Phải nói ra **trước** khi khách trả tiền."""


class KhongDocDuoc(ValueError):
    """Tệp thật sự không đọc được: hỏng, mã hoá, hoặc PDF chỉ có ảnh."""


def _chu_thuan(du_lieu: bytes, content_type: str) -> list[tuple[int, str]]:
    """Tệp chữ thuần → một "trang" số 0.

    ⭐ `trang = 0` nghĩa là **không biết**, không phải "trang đầu": `.txt` không
       có khái niệm trang. Trích dẫn sau này phải hiện được khác biệt ấy.
    """
    try:
        van = du_lieu.decode("utf-8")
    except UnicodeDecodeError as e:
        raise KhongDocDuoc("tep chu phai la UTF-8") from e
    if content_type == "application/json":
        try:
            json.loads(van)
        except ValueError as e:
            raise KhongDocDuoc("JSON khong hop le") from e
    return [(0, van)]


def _pdf(du_lieu: bytes) -> list[tuple[int, str]]:
    """PDF → [(số trang 1-based, chữ của trang)].

    ⛔ `ImportError` KHÔNG được lẫn vào nhánh "tệp hỏng". Xem đầu tệp: đó chính
       là lỗi đang sống trên production ở một app khác.
    """
    try:
        from pypdf import PdfReader
    except ImportError as e:                     # noqa: F841 — dung o dong duoi
        log.error("thieu `pypdf` — day la viec VAN HANH, khong phai loi cua tep")
        raise ThieuThuVien(
            "may chu chua cai `pypdf`; day khong phai loi cua tep ban tai len"
        ) from e

    try:
        doc = PdfReader(io.BytesIO(du_lieu))
        trang = [(i, (t.extract_text() or "")) for i, t in enumerate(doc.pages, 1)]
    except Exception as e:                       # noqa: BLE001
        # ⛔ BAT RONG o day la DUNG, va khac han ca tren: moi loi cua `pypdf`
        #    deu la "tep nay khong doc duoc". Nhung phai LOG day du, khong nuot.
        log.exception("pypdf khong doc duoc tep")
        raise KhongDocDuoc(f"khong doc duoc PDF: {type(e).__name__}") from e

    if not any(t.strip() for _, t in trang):
        # 🔴 Ca THUONG, khong phai goc hiem: PDF anh scan khong co lop chu.
        #    Phai la mot loi RIENG vi no quyet dinh chuyen tien (xem `job`).
        raise KhongDocDuoc(
            "PDF khong co lop chu — co the la ban scan thanh anh")
    return trang


def trich(du_lieu: bytes, *, content_type: str) -> list[tuple[int, str]]:
    """Byte → [(trang, chữ)]. Ném một trong **ba** ngoại lệ ở trên, không gộp."""
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct == PDF:
        trang = _pdf(du_lieu)
    elif ct in CHU_THUAN:
        trang = _chu_thuan(du_lieu, ct)
    else:
        raise KhongHoTro(f"chua doc duoc dinh dang {ct!r}")

    tong = sum(len(t) for _, t in trang)
    if tong > TRAN_KY_TU:
        raise KhongDocDuoc(
            f"tai lieu qua dai: {tong:,} ky tu, tran {TRAN_KY_TU:,}")
    return trang


def thanh_doan(trang: list[tuple[int, str]], **cau_hinh) -> list[tuple[int, int, str]]:
    """[(trang, chữ)] → [(thứ tự, trang, đoạn)], thứ tự chạy suốt cả tệp.

    ⛔ Cắt **trong từng trang**, không cắt xuyên trang. Một đoạn vắt qua hai
       trang thì `trang` của nó là số nào? Không có câu trả lời đúng, và trích
       dẫn sẽ trỏ sai. Mất một chút mạch văn ở ranh giới trang là cái giá rẻ hơn
       một trích dẫn chỉ sai chỗ.
    """
    from apps.chatltt.services import chia_doan

    ra: list[tuple[int, int, str]] = []
    for so, van in trang:
        for d in chia_doan.chia(van, **cau_hinh):
            ra.append((len(ra), so, d))
    return ra
