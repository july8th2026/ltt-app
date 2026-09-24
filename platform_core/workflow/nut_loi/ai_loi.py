"""Node `ai.*` — ánh xạ kết quả job `text.chat` -> FAILED + kiểm lược đồ.

Plan wf-v2 P7 (Task 3+4). Spec §12.1: `ai.extract` "kết quả không khớp lược
đồ ⇒ FAILED `dau_ra_sai_luoc_do`".

🔴 BẪY ĐÃ ĐO (memory `model-nha-tren-may-b.md`, `_luutru/
   model-nha-tra-ve-rong-khoang-mot-nua-luot.md`, 10–12/09/2026): máy B có
   thể trả **HTTP 200**, job kết thúc **SUCCEEDED**, mà `content` RỖNG — khối
   suy nghĩ (`--reasoning-format deepseek`) không bao giờ đóng. "Vô hình với
   quan trắc": `dem.ok` vẫn cộng một, không log lỗi nào. Đây đúng là triệu
   chứng `chuyen_loi_thoai: model tra ve rong` từng làm đỏ `test_448`.

   Cầu nối job chung (`platform_core/workflow/cau_noi.py::ap_ket_qua`) chỉ
   đọc `job.status`/`sig.status` — nó KHÔNG mở `result` ra xem `content` có
   dùng được không. Với node thường (vd `app.image.generate`) điều đó đúng:
   job xong là có tệp. Với `text.chat` thì KHÔNG: job xong không đảm bảo có
   chữ. `dien_giai()` là lớp diễn giải THÊM mà node `ai.*` phải áp lên kết
   quả job TRƯỚC khi coi là SUCCEEDED.

⛔ CHƯA nối hàm này vào `cau_noi.ap_ket_qua` — cầu nối đó nằm ngoài phạm vi
   tệp cho phép của làn p7 (`nut_loi/ai_*.py` + test). Xem
   `docs/superpowers/reports/p7-ai/task-3-report.md`.

⛔ Không tự viết bộ kiểm JSON Schema: dùng `jsonschema` (PyPI, Draft
   2020-12) — đã có sẵn trong môi trường (phụ thuộc bắc cầu của `chromadb`),
   nay khai tường minh trong `requirements-server.txt`.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import jsonschema

#: Mã lỗi node `ai.*` công bố (spec §5.6 `NodeError.ma`) — khuôn giống
#: `nut.MA_LOI_APP` nhưng khai riêng: node `ai.*` không dùng lại mã của job
#: app thường (vd `provider_loi`), vì lỗi ở đây phát hiện SAU KHI job đã
#: SUCCEEDED, không phải lỗi job.
MA_LOI_AI: tuple[str, ...] = ("dau_ra_rong", "dau_ra_sai_luoc_do")


def noi_dung_rong(content: Any) -> bool:
    """`content` không dùng được: không phải chuỗi, hoặc rỗng sau khi `strip`.

    ⭐ Đây chính là hình dạng của ca đã đo: `content` có thể là `""` hoặc chỉ
       toàn khoảng trắng — HTTP 200, `job.status == JOB_DONE`.
    """
    return not isinstance(content, str) or not content.strip()


def kiem_luoc_do(gia_tri: Any, luoc_do: dict) -> Optional[str]:
    """`None` = khớp lược đồ. Khác `None` = thông điệp lỗi.

    Bắt CẢ HAI loại lỗi của `jsonschema`: `ValidationError` (dữ liệu sai) và
    `SchemaError` (chính lược đồ do người dùng khai sai cú pháp) — cả hai
    phải biến thành FAILED có lý do, không được thoát ra ngoài thành một
    ngoại lệ chưa bắt (đó chính là cách `dong_co.xu_ly_run` sẽ nuốt và treo
    node ở QUEUED nếu không dịch tại đây).
    """
    try:
        jsonschema.validate(instance=gia_tri, schema=luoc_do)
    except jsonschema.ValidationError as loi:
        return str(loi.message)
    except jsonschema.SchemaError as loi:
        return f"luoc_do sai cu phap: {loi.message}"
    return None


def dien_giai(ket_qua: dict, *, luoc_do: Optional[dict] = None
             ) -> tuple[str, str, str]:
    """Diễn giải `result` của job `text.chat` ĐÃ SUCCEEDED ở tầng job.

    Trả `(trang_thai, ma_loi, chi_tiet)`:
      - `trang_thai` ∈ {"SUCCEEDED", "FAILED"}.
      - `ma_loi` rỗng khi SUCCEEDED, nằm trong `MA_LOI_AI` khi FAILED.

    Thứ tự kiểm: `content` rỗng trước (áp cho MỌI node `ai.*`, kể cả không
    khai `luoc_do` — `ai.llm` không có lược đồ vẫn phải bắt được ca content
    rỗng). Không khai `luoc_do` (dùng cho `ai.llm` không ép JSON) thì dừng ở
    đây — SUCCEEDED. Có `luoc_do` (bắt buộc với `ai.extract`, tuỳ chọn với
    `ai.llm`) thì `content` phải là JSON hợp lệ VÀ khớp lược đồ.
    """
    content = ket_qua.get("content")
    if noi_dung_rong(content):
        return ("FAILED", "dau_ra_rong",
                "model tra ve content rong (job da bao SUCCEEDED)")
    if luoc_do is None:
        return ("SUCCEEDED", "", "")
    try:
        # `content or ""`: `noi_dung_rong(content)` o tren DA loai `None` va
        # chuoi rong, nhung phep thu hep do di qua mot ham nen mypy khong theo
        # duoc. Viet thang ra thay vi de `except TypeError` gánh ca "content la
        # None" — mot ngoai le bat duoc khong phai mot phep kiem kieu.
        gia_tri = json.loads(content or "")
    except (TypeError, ValueError) as loi:
        return ("FAILED", "dau_ra_sai_luoc_do", f"content khong phai JSON: {loi}")
    thong_diep = kiem_luoc_do(gia_tri, luoc_do)
    if thong_diep is not None:
        return ("FAILED", "dau_ra_sai_luoc_do", thong_diep)
    return ("SUCCEEDED", "", "")


__all__ = ["MA_LOI_AI", "dien_giai", "kiem_luoc_do", "noi_dung_rong"]
