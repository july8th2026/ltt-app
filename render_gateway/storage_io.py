"""
storage_io.py — ảnh vào bằng presigned GET, ảnh ra bằng presigned PUT.

⛔ RANH GIỚI (Q102): máy B **không giữ khoá R2**. Máy A ký sẵn hai loại vé rồi đưa
   URL sang; cổng này chỉ dùng URL. Nhờ vậy mất máy B không mất khoá, và máy A
   không phải trung chuyển từng byte ảnh.

⛔ PRESIGNED PUT PHẢI GỬI ĐÚNG `Content-Type` ĐÃ KÝ. `platform_core/storage.py` ghi
   rõ điều này: sai header thì R2 trả **403** (chống lạm dụng vé). Nên máy A phải
   nói kiểu nội dung, và ta gửi đúng chuỗi đó — **không tự đoán từ đuôi tệp**.

⛔ Ảnh tham chiếu phải nằm trong thư mục `input` của ComfyUI thì node `LoadImage`
   mới thấy. Ta ghi vào đó bằng tên có tiền tố `job_id` để hai job không giẫm nhau.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

#: Trần một ảnh tham chiếu. Trùng với trần phía máy A (`apps/taoanh/jobs.py`) để
#: hai bên không lệch nhau — lệch trần là loại lỗi chỉ lộ ra với ảnh thật của khách.
TRAN_ANH_REF_MB = 8
TRAN_TONG_REF_MB = 20

#: Nhận dạng bằng magic byte, không tin đuôi tệp và không tin `Content-Type`
#: của bên gửi. Một tệp `.png` thật ra là `.txt` phải bị chặn ở đây.
_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}


class HttpFetcher(Protocol):
    def get(self, url: str, *, timeout: float) -> tuple[int, bytes]: ...
    def put(self, url: str, *, data: bytes, content_type: str,
            timeout: float) -> tuple[int, bytes]: ...


class StorageIOError(RuntimeError):
    pass


@dataclass(frozen=True)
class RefSpec:
    url: str
    #: Vai trò của ảnh: `edit` (ảnh cần sửa) / `subject` (giữ nhân dạng) /
    #: `structure` (giữ bố cục). Cổng không diễn giải, chỉ chuyển cho template.
    role: str = "edit"


def kieu_anh(data: bytes) -> Optional[str]:
    """Kiểu ảnh theo magic byte, hoặc None nếu không nhận ra."""
    for magic, mime in _MAGIC.items():
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _ten_an_toan(job_id: str, chi_so: int, mime: str) -> str:
    duoi = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[mime]
    goc = re.sub(r"[^A-Za-z0-9_-]", "", str(job_id))[:48] or "job"
    # Thêm băm ngắn để hai job có `job_id` bị cắt giống nhau vẫn không đụng tên.
    bam = hashlib.sha256(str(job_id).encode("utf-8")).hexdigest()[:8]
    return f"ltt_{goc}_{bam}_{chi_so}.{duoi}"


def tai_refs(fetcher: HttpFetcher, refs: list[RefSpec], *, job_id: str,
             input_dir: Path, timeout: float = 120.0) -> list[str]:
    """Tải ảnh tham chiếu về thư mục `input` của ComfyUI. Trả danh sách TÊN TỆP.

    Trả tên chứ không trả đường dẫn: node `LoadImage` nhận tên tương đối trong
    `input`, đưa đường dẫn tuyệt đối vào là nó không tìm thấy.
    """
    if not refs:
        return []
    input_dir.mkdir(parents=True, exist_ok=True)
    tong = 0
    ten_files: list[str] = []
    for i, ref in enumerate(refs):
        status, data = fetcher.get(ref.url, timeout=timeout)
        if status >= 400:
            raise StorageIOError(f"khong tai duoc anh tham chieu #{i + 1}: HTTP {status}")
        if not data:
            raise StorageIOError(f"anh tham chieu #{i + 1} rong")
        if len(data) > TRAN_ANH_REF_MB * 1024 * 1024:
            raise StorageIOError(
                f"anh tham chieu #{i + 1} vuot {TRAN_ANH_REF_MB} MB")
        tong += len(data)
        if tong > TRAN_TONG_REF_MB * 1024 * 1024:
            raise StorageIOError(f"tong anh tham chieu vuot {TRAN_TONG_REF_MB} MB")
        mime = kieu_anh(data)
        if mime is None:
            raise StorageIOError(
                f"anh tham chieu #{i + 1} khong phai PNG/JPEG/WebP (kiem magic byte)")
        ten = _ten_an_toan(job_id, i, mime)
        (input_dir / ten).write_bytes(data)
        ten_files.append(ten)
    return ten_files


def day_ket_qua(fetcher: HttpFetcher, anh: list[bytes], put_urls: list[str],
                *, content_type: str = "image/png", timeout: float = 300.0) -> int:
    """Đẩy ảnh kết quả lên R2 qua presigned PUT. Trả số ảnh đã đẩy.

    Số vé PUT do máy A cấp có thể ÍT hơn số ảnh sinh ra (khách xin 2 ảnh mà
    workflow trả 4). Đẩy theo số vé và **nói ra** phần dư, đừng vứt im lặng.
    """
    if not put_urls:
        raise StorageIOError("may A khong cap ve PUT nao")
    n = min(len(anh), len(put_urls))
    for i in range(n):
        status, body = fetcher.put(put_urls[i], data=anh[i],
                                   content_type=content_type, timeout=timeout)
        if status >= 400:
            # 403 ở đây gần như luôn là sai `Content-Type` so với lúc ký vé.
            raise StorageIOError(
                f"day anh #{i + 1} len R2 that bai: HTTP {status} "
                f"{body[:120].decode('utf-8', 'replace')}")
    return n
