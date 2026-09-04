"""
catalog.py — model nào được mở, và mỗi model chịu được gì.

⭐ HAI HỒ SƠ, MỘT TRỌNG SỐ. Cùng một file GGUF, hai cách khởi động, vì trên card
   24 GB **không thể vừa nạp `mmproj` vừa mở ngữ cảnh 200K**:

     qwen38-api     200K ngữ cảnh, KV q4_0, KHÔNG vision  21,98 GB  ← MẶC ĐỊNH
     qwen38-vision  131K ngữ cảnh, KV q4_0, CÓ  vision    21,10 GB

   `llama-swap` đổi giữa hai hồ sơ theo tên model client gọi, **chỉ một cái nằm
   trong VRAM tại một thời điểm**.

🔴 TRƯỚC 03/09 CÓ **BA** HỒ SƠ, VÀ HỒ SƠ THỨ BA (`qwen38-ops`, 200K) BỊ GIỮ
   TRONG LAN VÌ MỘT LẬP LUẬN SAI. Chỗ này từng viết:

       "`qwen38-api` PHỤC VỤ KHÁCH NGOÀI, `qwen38-ops` THÌ KHÔNG. Ràng buộc
        không phải VRAM mà là Cloudflare mặc định cắt ở 125 giây."

   Đúng cho cửa **đồng bộ**, sai cho cửa **stream** — mà cửa stream mới là thứ
   Codex và Claude Code dùng. `nhip_tim.py` chèn chú thích SSE mỗi 15 giây
   **trong lúc prefill**, nên đồng hồ im-lặng của Cloudflare không bao giờ chạm.

   ⭐ Chú thích ấy được viết **trước khi** `nhip_tim.py` tồn tại, và không ai
      đọc lại nó sau đó. Nó không sai lúc viết; nó **hết đúng** và sống tiếp.

⛔ VÀ LÝ DO MẠNH HƠN ĐỂ CHỈ CÓ **MỘT** HỒ SƠ TEXT: đo thật 03/09, llama-swap
   **giết một lượt đang chạy** để nạp hồ sơ khác; lượt bị giết chỉ nhận
   `ConnectionReset`. Hai hồ sơ text cùng mở = một nguồn lỗi ngẫu nhiên không
   giải thích được cho khách. Nên `qwen38-api` **giờ chính là** hồ sơ 200K.

⭐ MỘT HỒ SƠ CHO MỌI LOẠI VIỆC — coding, chat, agent, tóm tắt. Không tách model
   theo tác vụ: tất cả đều là *"text vào, text ra, có tool"*, cùng một hình dạng.
   Khách điều khiển độ sâu bằng `reasoning_effort` trong từng request.

⛔ FAIL-CLOSED (Q92): danh mục ở đây là *danh sách có thể có*. Model chỉ thật sự
   mở khi tên nó nằm trong `LTT_LLM_MODELS`. Thêm một dòng vào đây **không** mở
   thêm gì cả.

✅ `qwen38-api` 204800 / KV q4_0 — đo thật 03/09 trên đúng card đang phục vụ
   (build 10689, prompt ngẫu nhiên nên không tái dùng prompt cache):

     50.000 tok  →  999,9 tok/s   ·  100.000  →  805,3  ·  130.000  →  726,5
    150.000      →  672,4         ·  165.000  →  639,1  ·  180.000  →  616,7
     VRAM đỉnh 21.979 MiB  (hồ sơ 131K/q8_0 cũ: 22.017 MiB — rộng gấp rưỡi mà
     tốn ÍT hơn, vì KV q4_0 ở 204.800 nhỏ hơn KV q8_0 ở 131.072)

   Mốc đầu và mốc cuối prompt đọc lại đúng ở **mọi** lượt ⇒ không cắt im lặng.
   Kim-trong-đống-cỏ ở 130K, năm kim ở 10/30/50/70/90 % độ sâu: **10/10**.
   Cao nhất chạy thật: **179.902 token vào** ⇒ trần công bố (169.984) nằm
   **bên trong** vùng đã chứng minh, không ở mép nó.

   Chi tiết + hai cái bẫy đo đạc: `docs/VLM_NOI_BO/NGU_CANH_DAI_2026-09-03.md`.

✅ `qwen38-vision` 131072 / KV q4_0 — đo thật 03/09, cùng ngày, trên một hồ sơ
   thử riêng (`qwen38-vision-thu`, KHÔNG khai trong `LTT_LLM_MODELS` nên cổng
   fail-closed từ chối và không request nào của khách rơi vào nó):

     50.128 tok  →  1.012,1 tok/s · TTFT 49,5 s   VRAM 21.095 MiB
     89.868 tok  →    847,2 tok/s · TTFT 106,1 s  VRAM 21.099 MiB
     mốc đầu + mốc cuối prompt đọc lại đúng ở cả hai lượt

   🔴 VÀ PHẢI ĐO CẢ VIỆC NÓ CÒN ĐỌC ĐƯỢC ẢNH. Đổi KV `q8_0 → q4_0` trên đúng
      hồ sơ mà công việc của nó là *nhìn* thì "chạy được ở ngữ cảnh dài" chưa
      trả lời gì cả. A/B trên **cùng một ảnh**, mốc ngẫu nhiên 6 ký tự:

        qwen38-vision      65K/q8_0  →  "OO1N0G"  ✓  21,2 s
        qwen38-vision-thu 131K/q4_0  →  "OO1N0G"  ✓   2,9 s

   ⚠️ VRAM **CÓ** tăng: 20.351 → 21.099 MiB (+748). Tôi dự đoán "không tăng" vì
      KV `131.072@q4_0` bằng đúng số byte với `65.536@q8_0` — dự đoán ấy đúng
      cho KV và **sai cho tổng**, vì buffer tính toán giãn theo ngữ cảnh. Biên
      còn lại 3.477 MiB, rộng hơn cả hồ sơ text (2.597 MiB).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    """Một hồ sơ phục vụ. `ten` là thứ client gửi trong trường `model`."""

    ten: str
    #: Hồ sơ này có nạp `mmproj` không. Quyết định request có ảnh có được nhận không.
    co_vision: bool
    #: Trần ngữ cảnh của hồ sơ (`-c` của llama-server). CHỜ P5 xác nhận.
    max_context: int
    #: Mô tả ngắn, trả trong `/v1/models` để người dùng chọn đúng hồ sơ.
    mo_ta: str


#: Bảng khai. Đây KHÔNG phải danh sách đang mở — xem `nap_catalog`.
HO_SO: tuple[ModelSpec, ...] = (
    ModelSpec(
        ten="qwen38-api",
        co_vision=False,
        max_context=204_800,
        mo_ta="Qwen3.8-27B - coding, chat, agent, tom tat. Ngu canh 200K.",
    ),
    ModelSpec(
        ten="qwen38-vision",
        co_vision=True,
        max_context=131_072,
        mo_ta="Qwen3.8-27B - doc anh/anh chup man hinh, ngu canh 131K",
    ),
)


class KhongCoModel(LookupError):
    """Tên model không có trong danh mục, hoặc có nhưng chưa được mở."""


def nap_catalog(models_mo: tuple[str, ...]) -> dict[str, ModelSpec]:
    """Danh mục **thật sự đang mở**.

    `models_mo` rỗng → trả dict rỗng. Đó là hành vi đúng, không phải lỗi cấu hình:
    `GET /v1/models` sẽ trả `200` với danh sách rỗng, y như `/api/v1/tools` của
    Public API khi `LTT_PUBLIC_API_TOOLS` rỗng.

    Tên lạ trong `models_mo` bị **bỏ qua trong im lặng có chủ ý**: một lỗi chính tả
    trong biến môi trường không được phép làm cổng không khởi động nổi. Nhưng nó
    hiện ra ở `/health` (`models_la`) để người vận hành thấy.
    """
    theo_ten = {m.ten: m for m in HO_SO}
    return {ten: theo_ten[ten] for ten in models_mo if ten in theo_ten}


def ten_la(models_mo: tuple[str, ...]) -> tuple[str, ...]:
    """Tên có trong `LTT_LLM_MODELS` nhưng không khớp hồ sơ nào. Cho `/health`."""
    biet = {m.ten for m in HO_SO}
    return tuple(t for t in models_mo if t not in biet)


def lay(catalog: dict[str, ModelSpec], ten: str) -> ModelSpec:
    spec = catalog.get(ten)
    if spec is None:
        raise KhongCoModel(ten)
    return spec
