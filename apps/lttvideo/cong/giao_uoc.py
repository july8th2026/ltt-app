"""Giao ước giữa LTT và WanGP — **mười một** phương thức, không hơn.

## Vì sao bề mặt phải HẸP

WanGP rất rộng: 28 handler họ model, 46 model type riêng họ Wan, hậu kỳ, âm
thanh, LoRA. Một mối nối "cho tiện" sẽ mọc thêm đường mỗi lần có việc mới, và
khi ấy nó thành `wangp_client` thứ hai — thứ đã trộn *cách nói chuyện* với
*biết gì về model*, và giữ độ phủ ở 2/46.

Mười một cửa dưới đây là **toàn bộ** thứ sản phẩm cần:

    tra cứu    liet_ke_model · so_do · mac_dinh · kha_dung
    đưa vào    nap_media
    chạy việc  gui_viec · tien_do · ket_qua · huy
    lấy ra     tai_ve
    dọn        don_dep

Thứ gì WanGP làm mà không lọt qua mười một cửa này thì tầng trên không dùng
được — và đó là chủ ý. Thêm cửa thứ mười hai là một quyết định, không phải một
tiện nghi, nên `test_738` chốt **con số** để người thêm phải dừng lại một nhịp.

## 🔴 Con số này ban đầu là TÁM, và phép kiểm ấy bắt được chính người viết nó

Bản đầu khai tám cửa — thiết kế **trước khi** đọc xem `wangp_client` cũ thật sự
cần gì. Đọc rồi mới thấy ba cửa nữa đang được dùng thật: `nap_media`
(`/nap_media`), `tai_ve` (`/tai/{job}/{i}`), `don_dep` (`/cleanup/{job}`).

⭐ Không có ba cửa ấy thì đường ống **không chạy nổi một lượt nào**: ảnh của
  người dùng nằm ở R2 phía LTT, mà WanGP chỉ nhận **đường dẫn tệp trên chính
  máy nó**; và video sinh ra nằm trên pod, phải kéo về mới lưu vào R2 được.

Đây đúng là việc `test_738` sinh ra để làm — chốt con số buộc người sửa dừng
lại một nhịp, kể cả khi người sửa là người đã viết ra nó.

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

    # ── Đưa media vào ──────────────────────────────────────────────────────

    def nap_media(self, du_lieu: bytes, *, duoi: str = "png") -> str:
        """Nạp byte một tệp lên máy chạy WanGP, trả **đường dẫn trên máy đó**.

        ⭐ Mắt xích bắt buộc, không bỏ được: `docs_API.md` §*Accepted Input
          Shapes* nói mọi đầu vào media của WanGP là **đường dẫn tệp trên chính
          máy chạy nó** — không URL, không base64. Ảnh của người dùng nằm ở R2
          phía LTT.

        ⛔ Gửi **byte thô**, không bọc JSON: base64 phồng 33%, và một ảnh 8 MB
           thành 11 MB đi qua một proxy vốn đã có trần thời gian.
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

    # ── Lấy ra và dọn ──────────────────────────────────────────────────────

    def tai_ve(self, ma_viec: str, chi_so: int = 0) -> bytes:
        """Kéo tệp thứ `chi_so` của việc về dạng byte.

        `ket_qua()["tep"]` trả **đường dẫn trên máy WanGP**, không phải nội
        dung. Không có cửa này thì video sinh xong nằm lại trên pod và không
        bao giờ tới R2 — job XONG mà người dùng không tải được gì.
        """
        ...

    def don_dep(self, ma_viec: str) -> None:
        """Xoá tệp tạm của việc trên máy WanGP, sau khi đã kéo về.

        ⚠️ Không dọn thì volume đầy dần một cách im lặng, và nó là volume
           **300 GB dùng chung với trọng số model** — đầy ở đây nghĩa là không
           tải thêm được model nào.
        """
        ...
