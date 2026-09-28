"""upload_zip.py — giai nen ZIP an toan cho kho tai nguyen (pha 5).

Ba lop chan CUA CA ZIP, theo dung thu tu kiem tra (re nhat truoc):

1. So luong entry — mot ZIP hop le cho kho anh khong can hang nghin tep.
2. Kich thuoc GIAI NEN cua tung entry va TONG CA ZIP — chan bomb "nhieu tep
   vua".
3. Ti le nen/goc tren TUNG entry — chan bomb "mot tep nen cuc tot" (vi du
   toan so 0) ma hai kiem tra tren khong bat duoc vi so luong entry va tong
   kich thuoc van nho.

Ca ba vi pham tren TU CHOI TOAN BO zip (ném `ZipImportError` truoc khi yield
bat cu entry nao) — day la loi "adversarial", khong phai mot tep hop le nguoi
dung vo tinh ket vao.

Zip-slip: `ZipInfo.filename` sau khi chuan hoa dau `/` va bo `./` khong duoc
chua doan `..` — tu choi CA ZIP ngay khi thay MOT entry xau, khong chi bo qua
rieng entry do. Mot file doc duoc TRONG mot zip bi tu choi van la "khong co
tep nao duoc ghi ra ngoai" — dung boc toan bo trong mot vong kiem TRUOC khi
ghi bat cu byte nao.

## Bat bien KHAC voi ba loi tren: KHONG entry nao duoc bien mat im lang

Mot entry co duoi khong phai anh, 0 byte, hoac trung ten voi mot entry khac
trong CUNG zip KHONG phai loi adversarial — no la mot tep nguoi dung vo tinh
nen vao chung, va nguoi dung can THAY no bi bo qua kem LY DO, khong phai
doan tai sao so anh nhap vao it hon so tep trong zip. `iter_safe_entries` ghi
nhan ca hai loai ket cuc trong CUNG mot `ZipEntry`: `skip_reason is None` la
da chap nhan, `skip_reason` khac None la bi bo qua kem ly do. Goi noi dung
bang mot vong so sanh:

    ok, skipped = 0, []
    for entry in iter_safe_entries(data):
        if entry.skip_reason is not None:
            skipped.append(entry)
        else:
            ... nhap entry.data ...

va bat bien can giu la `len(entries) == so entry TEP (khong tinh thu muc)
trong zip` — khong entry nao roi khoi danh sach nay.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

MAX_ENTRIES = 300
MAX_ENTRY_UNCOMPRESSED = 20 * 1024 * 1024      # 20 MiB — dong bo _RESOURCE_IMAGE_CAP
MAX_TOTAL_UNCOMPRESSED = 500 * 1024 * 1024     # 500 MiB
MAX_COMPRESSION_RATIO = 100

_ANH_EXT = (".png", ".jpg", ".jpeg", ".webp")


class ZipImportError(ValueError):
    """Zip khong an toan hoac khong hop le — route/job tra loi ro rang."""


@dataclass(frozen=True)
class ZipEntry:
    """Một kết cục ĐÃ GHI NHẬN cho một entry trong zip.

    `skip_reason is None` -> `data` là bytes ảnh, sẵn sàng nhập.
    `skip_reason` khác None -> entry KHÔNG được nhập; `data` rỗng (`b""`), lý
    do nằm trong `skip_reason` (không bao giờ rỗng khi bị bỏ qua).
    """

    name: str
    data: bytes
    skip_reason: str | None = None


def _safe_name(raw: str) -> str:
    cleaned = raw.replace("\\", "/").strip("/")
    parts = [p for p in cleaned.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ZipImportError(f"zip-slip: duong dan di ra ngoai: {raw!r}")
    if not parts:
        raise ZipImportError(f"ten tep rong trong zip: {raw!r}")
    return "/".join(parts)


def iter_safe_entries(zip_bytes: bytes):
    """Sinh `ZipEntry` cho TỪNG entry tệp trong zip — không entry nào bị bỏ
    sót khỏi kết quả này.

    Ba vi phạm "adversarial" (so lượng entry, kích thước một entry, tổng kích
    thước, tỉ lệ nén) ném `ZipImportError` NGAY, từ chối TOÀN BỘ zip trước khi
    yield bất cứ thứ gì — một zip bị từ chối nghĩa là KHÔNG có `ZipEntry` nào
    (chấp nhận lẫn bỏ qua) được sinh ra từ nó.

    Các trường hợp còn lại (đuôi không phải ảnh, tệp rỗng, trùng tên) được
    ghi nhận là `ZipEntry(skip_reason=...)` thay vì bị loại khỏi kết quả —
    đây là điểm khác với một bản cũ từng dùng `continue`, khiến những entry
    này biến mất im lặng: không nằm trong danh sách nhập, và không có dấu vết
    nào nói chúng đã bị loại.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise ZipImportError("tep khong phai ZIP hop le") from exc

    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise ZipImportError(
            f"vuot so luong tep cho phep ({MAX_ENTRIES})")

    # Bước 1 — kiểm TRƯỚC KHI đọc bất kỳ byte nào, và trước khi yield bất kỳ
    # entry nào: một zip bị từ chối vì kích thước/tỉ lệ phải bị từ chối TOÀN
    # BỘ, không phải "từ chối nửa chừng sau khi đã trả về vài entry".
    total_uncompressed = 0
    seen_names: set[str] = set()
    ke_hoach: list[tuple[zipfile.ZipInfo, str, str | None]] = []
    for info in infos:
        if info.is_dir():
            continue
        name = _safe_name(info.filename)          # ném ngay nếu zip-slip

        if not any(name.lower().endswith(ext) for ext in _ANH_EXT):
            ke_hoach.append((info, name,
                             "khong phai dinh dang anh (png/jpg/jpeg/webp)"))
            continue
        if name in seen_names:
            ke_hoach.append((info, name,
                             "trung ten voi mot tep khac trong cung zip"))
            continue
        if info.file_size == 0:
            ke_hoach.append((info, name, "tep rong (0 byte)"))
            continue
        if info.file_size > MAX_ENTRY_UNCOMPRESSED:
            raise ZipImportError(
                f"tep {name!r} qua lon sau giai nen "
                f"(> {MAX_ENTRY_UNCOMPRESSED} bytes)")
        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > MAX_COMPRESSION_RATIO:
                raise ZipImportError(
                    f"tep {name!r} co ti le nen bat thuong ({ratio:.0f}x) "
                    "— tu choi de an toan")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
            raise ZipImportError(
                f"tong dung luong sau giai nen vuot {MAX_TOTAL_UNCOMPRESSED} bytes")
        seen_names.add(name)
        ke_hoach.append((info, name, None))

    # Bước 2 — mọi kiểm tra đã qua (hoặc đã ném ở trên); giờ mới đọc bytes.
    for info, name, skip_reason in ke_hoach:
        if skip_reason is not None:
            yield ZipEntry(name=name, data=b"", skip_reason=skip_reason)
        else:
            yield ZipEntry(name=name, data=zf.read(info), skip_reason=None)


THUMB_MAX_PX = 320
THUMB_JPEG_QUALITY = 82


def _thumb_key_for(original_key: str) -> str:
    base = original_key.rsplit(".", 1)[0]
    return f"{base}__thumb.jpg"


def make_thumbnail(storage, *, original_key: str, data: bytes) -> str:
    """Sinh thumbnail JPEG, khung tối đa 320x320, lưu ở khoá RIÊNG.

    ⛔ Không bao giờ ghi đè `original_key`: ảnh gốc là thứ khách tải lên và có
    quyền tải lại nguyên vẹn; thumbnail chỉ để hiển thị nhanh trong lưới kho.
    """
    from PIL import Image

    opened = Image.open(io.BytesIO(data))
    rgb = opened.convert("RGB")
    rgb.thumbnail((THUMB_MAX_PX, THUMB_MAX_PX))
    out = io.BytesIO()
    rgb.save(out, format="JPEG", quality=THUMB_JPEG_QUALITY)
    out.seek(0)

    thumb_key = _thumb_key_for(original_key)
    storage.put(thumb_key, out, content_type="image/jpeg")
    return thumb_key
