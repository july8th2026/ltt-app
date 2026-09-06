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

#: Định dạng đọc qua `markitdown` (H44 B2, 06/09). Chúng **không có khái niệm
#: trang**, nên rơi vào nhánh `trang = 0` đã có sẵn từ P06 — không phải một
#: thoả hiệp, mà là đúng nhánh hợp đồng đã định nghĩa cho *"không biết"*.
#:
#: ⛔ PDF **không** ở đây, dù `markitdown[pdf]` đọc được và còn trích được bảng.
#:    Đo mã `_pdf_converter.py`: nó duyệt **theo trang** bên trong nhưng API công
#:    khai trả về **một khối markdown** — số trang không ra tới ngoài. Mà
#:    `(tep_id, doan_id, trang)` là toàn bộ lý do bước 5 của P06 tồn tại.
#:    ⇒ Đổi đường PDF là đổi một tính năng đã chốt lấy một tính năng chưa cần.
QUA_MARKITDOWN = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/html": ".html",
}

DUOC_NHAN = (PDF, *CHU_THUAN, *QUA_MARKITDOWN)

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


#: Tệp BẮT BUỘC phải có bên trong một OOXML thật, theo đuôi.
_MOC_OOXML = {".docx": "word/document.xml", ".pptx": "ppt/presentation.xml"}


def _kiem_ooxml(du_lieu: bytes, duoi: str) -> None:
    """Zip này có **thật sự** là docx/pptx không.

    🔴 Đo 06/09: `markitdown` **không ném** với một zip không phải OOXML — nó
       rơi về bộ đọc ZIP và trích nội dung **mọi tệp bên trong**:

           'Content from the zip file `None`:
            ## File: khong-phai-ooxml.txt
            noi dung ben trong zip ...'

    ⇒ Một zip đổi tên thành `.docx` sẽ được đánh chỉ số nguyên đám. Không phải
      một lỗ bảo mật (tệp của chính khách, hội thoại của chính họ), nhưng nó
      làm `content_type` thành một lời khai **vô nghĩa**: khách nói "tài liệu
      Word" và ta lập chỉ số một thứ khác, rồi trích dẫn về nó.

    ⭐ Cửa nền tảng chỉ kiểm được magic `PK` — nó **không thể** phân biệt docx
       với một zip bất kỳ. Nên hàng phòng thủ thứ hai nằm ở đây, và nó rẻ: một
       OOXML thật luôn chứa một tệp có tên cố định.
    """
    import zipfile

    moc = _MOC_OOXML.get(duoi)
    if not moc:
        return
    try:
        with zipfile.ZipFile(io.BytesIO(du_lieu)) as z:
            ten = set(z.namelist())
    except (zipfile.BadZipFile, OSError) as e:
        raise KhongDocDuoc(f"khong phai mot tep {duoi} hop le") from e
    if moc not in ten:
        raise KhongDocDuoc(
            f"tep khong phai {duoi} that: thieu {moc!r} ben trong")


def _markitdown(du_lieu: bytes, duoi: str) -> list[tuple[int, str]]:
    """docx/pptx/html → một "trang" số 0. (H44 B2)

    ⭐ **Lắp thay vì tự viết.** Trước B2 tôi tự viết bộ trích và nó chỉ đọc PDF
       + chữ thuần — trong khi `markitdown` (MIT, 6 phụ thuộc lõi nhẹ) đọc thêm
       docx/pptx/outlook và trích cả **bảng biểu**. Đó là ~3 ngày tự viết đổi
       lấy nửa ngày lắp.

    ⛔ Cùng ba loại hỏng như `_pdf`: `ImportError` là việc **vận hành**, không
       phải lỗi của tệp khách. Đúng lỗi đang sống ở `chataistudio`.
    """
    _kiem_ooxml(du_lieu, duoi)
    try:
        from markitdown import MarkItDown
    except ImportError as e:
        log.error("thieu `markitdown` — viec VAN HANH, khong phai loi cua tep")
        raise ThieuThuVien(
            "may chu chua cai `markitdown`; day khong phai loi cua tep ban tai len"
        ) from e
    try:
        kq = MarkItDown().convert_stream(io.BytesIO(du_lieu), file_extension=duoi)
        van = (kq.text_content or "").strip()
    except Exception as e:                       # noqa: BLE001
        log.exception("markitdown khong doc duoc tep %s", duoi)
        raise KhongDocDuoc(f"khong doc duoc {duoi}: {type(e).__name__}") from e
    if not van:
        raise KhongDocDuoc(f"khong trich duoc chu nao tu {duoi}")
    return [(0, van)]


def trich(du_lieu: bytes, *, content_type: str) -> list[tuple[int, str]]:
    """Byte → [(trang, chữ)]. Ném một trong **ba** ngoại lệ ở trên, không gộp."""
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct == PDF:
        trang = _pdf(du_lieu)
    elif ct in CHU_THUAN:
        trang = _chu_thuan(du_lieu, ct)
    elif ct in QUA_MARKITDOWN:
        trang = _markitdown(du_lieu, QUA_MARKITDOWN[ct])
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
