"""Giao ước giữa LTT và WanGP — **tám** phương thức, không hơn.

## Vì sao bề mặt phải HẸP

WanGP rất rộng: 28 handler họ model, 46 model type riêng họ Wan, hậu kỳ, âm
thanh, LoRA. Một mối nối "cho tiện" sẽ mọc thêm đường mỗi lần có việc mới, và
khi ấy nó thành `wangp_client` thứ hai — thứ đã trộn *cách nói chuyện* với
*biết gì về model*, và giữ độ phủ ở 2/46.

Tám cửa dưới đây là **toàn bộ** thứ sản phẩm cần:

    tra cứu   liet_ke_model · so_do · mac_dinh · kha_dung
    chạy việc gui_viec · tien_do · ket_qua · huy

Thứ gì WanGP làm mà không lọt qua tám cửa này thì tầng trên không dùng được —
và đó là chủ ý. Thêm cửa thứ chín là một quyết định, không phải một tiện nghi,
nên `test_738` chốt **con số** để người thêm phải dừng lại một nhịp.

## Ranh giới với `dieu_phoi.py`

`dieu_phoi` là mối nối **RunPod** (bật máy, chờ card, tắt máy). Nó *không* thuộc
giao ước này. Trộn hai thứ lại thì đường ống lệ thuộc vòng đời pod, và cả kế
hoạch "giả lập trước" mất ý nghĩa.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class LoiMay(RuntimeError):
    """Mọi hỏng hóc phía WanGP — mạng, HTTP, thiếu bản ghi, việc lỗi.

    Tầng trên bắt **một** kiểu ngoại lệ này thay vì bắt `httpx.HTTPError`,
    `KeyError`, `json.JSONDecodeError` rời rạc. Bắt lẻ là cách một đường lỗi bị
    bỏ sót, và một đường lỗi bỏ sót trong worker nghĩa là job treo tới hết hạn.
    """


@runtime_checkable
class May(Protocol):
    """Mọi thứ LTT cần ở WanGP.

    ⛔ Tầng trên (`so_dang_ky`, `tac_vu`, `jobs`, `routes`) **không** được import
       `httpx`, `shared.api`, hay bất kỳ ký hiệu nào của WanGP. Chỉ import
       `apps.lttvideo.cong`.
    """

    # ── Tra cứu — KHÔNG nhân ma trận, nên chạy được cả khi cuBLAS hỏng ──────

    def liet_ke_model(self, **loc: Any) -> list[dict]:
        """`list_model_metadata(**loc)`.

        Bộ lọc hợp lệ (`docs_API.md:252`): `family` · `base_model_type` ·
        `finetune` · `model_type` · `main_output` · `inputs` · `name` ·
        `query` · `limit` · `offset`.

        Lọc chuỗi nhận mẫu `*` / `?` không phân biệt hoa thường. `main_output`
        và `inputs` nhận một giá trị hoặc một danh sách; nhiều giá trị là phép
        HOẶC.
        """
        ...

    def so_do(self, model_type: str) -> dict | None:
        """`get_model_schema(model_type)` — năng lực, vai trò media, giới hạn
        khung, hướng dẫn prompt, hỗ trợ cửa sổ trượt.

        Trả `None` khi WanGP **không biết** model ấy. Khác hẳn việc *thiếu bản
        ghi*, vốn phải NÉM — xem `MayGiaLap`.
        """
        ...

    def mac_dinh(self, model_type: str) -> dict:
        """`get_default_settings(model_type)` — settings gốc do WanGP sinh.

        ⭐ Đây là nơi mọi tham số phải đến từ. Gõ tay một giá trị settings là
          phạm G1, và là đúng cơ chế đã giữ V2.1 ở 2/46 model.
        """
        ...

    def kha_dung(self, model_type: str) -> dict:
        """`get_model_availability(model_type)` — trọng số đã có trên đĩa chưa.

        Cùng phép quét hệ tệp mà giao diện WanGP dùng cho ô trạng thái. Đây là
        câu trả lời cho "phải tải model nào", và nó đến từ máy chứ không từ một
        bảng ta chép.
        """
        ...

    # ── Chạy việc ──────────────────────────────────────────────────────────

    def gui_viec(self, settings: dict) -> str:
        """`submit_task(settings)`. Trả mã việc.

        ⚠️ Lỗi lúc **chạy** không ném ra từ đây (`docs_API.md:...`: *"Runtime
        failures do not raise from submit_task"*) — chúng nằm trong
        `ket_qua()["loi"]`. Chỉ lỗi lúc **nộp** mới ném `LoiMay`.
        """
        ...

    def tien_do(self, ma_viec: str) -> dict:
        """Một nhịp tiến độ: `{'pha': str, 'phan_tram': float, 'xong': bool}`."""
        ...

    def ket_qua(self, ma_viec: str) -> dict:
        """`{'tep': list[str], 'loi': list[str], 'huy': bool}`.

        ⛔ `huy=True` **không** kèm `loi`. Huỷ là một kết cục bình thường; nền
           tảng đã hoàn credit ở `POST /jobs/{id}/cancel`. Ghi thêm một dòng
           lỗi ở đây là dựng một báo động giả vĩnh viễn.
        """
        ...

    def huy(self, ma_viec: str) -> None:
        """Xin huỷ. Không chờ."""
        ...
