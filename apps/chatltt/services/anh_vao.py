"""
anh_vao.py — ảnh người dùng **gửi vào** cho model vision. (H43 Phase 13)

## Vì sao là một tệp riêng, không nhét vào `tao_media.py`

`tao_media` lo ảnh **đi ra**: báo giá, nộp job, chờ worker, quyết toán. Ảnh đi
vào không có job, không có tiền, không có worker — nó chỉ có *kiểm* và *lưu*.
Trộn hai thứ đó là mời một hàm `bao_gia` mọc thêm nhánh "nếu là ảnh vào thì bỏ
qua tiền", tức đúng cách một luồng tiền học được cách không thu tiền.

## Ba việc, đúng ba việc

  1. **Kiểm ảnh đã giải mã**, không tin MIME của trình duyệt —
     `platform_core.image_input.validate_reference` là chỗ duy nhất biết luật đó.
  2. **Lưu dưới khoá mang chủ sở hữu**, để cửa `/tai-san` kiểm được sở hữu bằng
     hình dạng khoá, cùng lối với `anhnoibo/` và `voice/out/`.
  3. **Đọc lại thành `data:` URI** cho `messages` gửi model.

⛔ KHÔNG gửi model một URL trỏ về máy này. Máy B nằm trong LAN và không đăng
   nhập được vào web; một URL `/chatltt/tai-san/...` với nó là một trang login.
   Và nếu nó *đọc được*, thì ta vừa mở một đường tải ảnh của khách không cần
   phiên. `data:` URI đắt hơn nhưng nó không tạo cửa nào cả.
"""
from __future__ import annotations

import base64
import io
import uuid

from platform_core import image_input, storage

#: Hình khoá: `chatltt/anh-vao/<uid>/<id>.<duoi>`.
#:
#: ⚠️ Thêm hình này thì PHẢI thêm nó vào `tao_media.kiem_so_huu_khoa` — cửa
#:    `/tai-san` fail-closed, nên quên khai là ảnh vừa tải lên không hiện được,
#:    và triệu chứng (ảnh vỡ trong hội thoại) không trỏ về đây.
TIEN_TO = "chatltt/anh-vao"

DUOI = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}

#: Trần **số ảnh trong một lượt gửi**.
#:
#: 🔴 Không phải con số cho đẹp. `ltt_llm_vision` có ngữ cảnh **28.262** token —
#:    bằng một phần ba bản text. Ảnh chiếm chỗ trong đúng ngân sách đó, nên bốn
#:    ảnh là đã ăn phần lớn chỗ dành cho hội thoại, và người dùng sẽ gặp "vượt
#:    trần ngữ cảnh" mà không hiểu vì sao — họ nghĩ mình mới gõ có một dòng.
#:
#: ⭐ Chặn ở đây, lúc gửi, thì thông báo nói đúng thứ họ vừa làm. Chặn ở tầng
#:    model thì thông báo nói về token.
TOI_DA_MOI_LUOT = 4

#: Trần **số ảnh gửi lại cho model ở mỗi lượt** trên cả đường hội thoại.
#:
#: OpenAI-format gửi lại toàn bộ lịch sử mỗi lượt, nên một hội thoại mười lượt
#: có ảnh sẽ gửi lại chồng chất. Giữ những ảnh **mới nhất**: ảnh cũ hầu như
#: luôn là ngữ cảnh đã được nói thành lời ở các lượt sau.
TOI_DA_TRONG_NGU_CANH = 6


class LoiAnhVao(ValueError):
    """Lỗi của người gọi — thông báo đưa thẳng ra giao diện được."""


def khoa_moi(user_id: str, mime: str) -> str:
    return f"{TIEN_TO}/{user_id}/{uuid.uuid4().hex}.{DUOI.get(mime, 'png')}"


def luu(data: bytes, content_type: str, *, user_id: str) -> dict:
    """Kiểm rồi lưu một ảnh vào. Trả `{key, mime, rong, cao, bytes}`.

    ⛔ Ném `LoiAnhVao` chứ không trả `None`: một chỗ tải ảnh im lặng bỏ qua tệp
       hỏng là một chỗ người dùng bấm Gửi và không hiểu vì sao model không thấy
       ảnh của mình.
    """
    if not str(user_id or "").strip():
        raise LoiAnhVao("thieu chu so huu")
    try:
        mime, (rong, cao) = image_input.validate_reference(data, content_type)
    except ValueError as e:
        raise LoiAnhVao(str(e)) from e
    if mime not in DUOI:
        raise LoiAnhVao(f"kieu anh khong duoc ho tro: {mime}")
    khoa = khoa_moi(str(user_id), mime)
    storage.get_storage().put(khoa, io.BytesIO(data), content_type=mime)
    return {"key": khoa, "mime": mime, "rong": rong, "cao": cao, "bytes": len(data)}


def la_khoa_anh_vao(khoa: str, user_id: str) -> bool:
    """`chatltt/anh-vao/<uid>/<ten>` và đúng chủ.

    Cùng lối `tao_media.kiem_so_huu_khoa`: kiểm **từng đoạn** trước, vì chỉ so
    tiền tố thì `chatltt/anh-vao/<uid>/../../secrets/app.env` đi lọt — ba đoạn
    đầu đúng hết, phần thoát nằm ở sau. Đúng lỗi `test_625` đã bắt một lần.
    """
    khoa = str(khoa or "")
    if "\\" in khoa:
        return False
    doan = khoa.split("/")
    if any(d in ("", ".", "..") for d in doan):
        return False
    return (len(doan) == 4 and doan[0] == "chatltt" and doan[1] == "anh-vao"
            and doan[2] == str(user_id))


def data_uri(khoa: str) -> str:
    """Đọc ảnh từ kho thành `data:<mime>;base64,...`.

    Trả chuỗi rỗng khi không đọc được — người gọi bỏ ảnh đó ra khỏi ngữ cảnh.
    Một lượt chat **không được chết** vì một ảnh cũ đã bị dọn khỏi kho.
    """
    duoi = khoa.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg",
            "jpeg": "image/jpeg", "webp": "image/webp"}.get(duoi, "")
    if not mime:
        return ""
    try:
        with storage.get_storage().open(khoa) as f:
            data = f.read()
    except (OSError, KeyError, ValueError, storage.StorageError):
        # Anh cu da bi don khoi kho la chuyen BINH THUONG (retention), khong
        # phai su co. Mot luot chat khong duoc chet vi no.
        return ""
    if not data:
        return ""
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
