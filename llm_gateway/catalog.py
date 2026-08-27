"""
catalog.py — model nào được mở, và mỗi model chịu được gì.

⭐ BA HỒ SƠ, MỘT TRỌNG SỐ. Cùng một file GGUF, ba cách khởi động, vì trên card
   24 GB **không thể vừa nạp `mmproj` vừa mở ngữ cảnh 200K**:

     qwen38-api      131K ngữ cảnh, KV q8_0, KHÔNG vision ~20,7 GB  ← MẶC ĐỊNH
     qwen38-ops     200K ngữ cảnh, KV q4_0, KHÔNG vision  ~23,3 GB
     qwen38-vision   64K ngữ cảnh, KV q8_0, CÓ  vision    ~19,9 GB

   `llama-swap` đổi giữa ba hồ sơ theo tên model client gọi, **chỉ một cái nằm
   trong VRAM tại một thời điểm**.

⛔ `qwen38-api` PHỤC VỤ KHÁCH NGOÀI, `qwen38-ops` THÌ KHÔNG. Ràng buộc không phải
   VRAM mà là **Cloudflare mặc định cắt ở 125 giây**. Prefill đo được ~1.000 tok/s ⇒ một
   prompt lấp đầy 200K tốn ~200 s ⇒ **524**, dù máy vẫn chạy tốt. Mở `qwen38-ops`
   ra Internet là bán một cửa sổ khách không dùng nổi.

⭐ MỘT HỒ SƠ CHO MỌI LOẠI VIỆC — coding, chat, agent, tóm tắt. Không tách model
   theo tác vụ: tất cả đều là *"text vào, text ra, có tool"*, cùng một hình dạng.
   Khách điều khiển độ sâu bằng `reasoning_effort` trong từng request.

⛔ FAIL-CLOSED (Q92): danh mục ở đây là *danh sách có thể có*. Model chỉ thật sự
   mở khi tên nó nằm trong `LTT_LLM_MODELS`. Thêm một dòng vào đây **không** mở
   thêm gì cả.

✅ `qwen38-api` 131072 đã được xác nhận bằng warm/combined benchmark trên RTX
   3090 (job Nexus `job_01M11M0DQXMFFNNAM6JJ8RBGQ2`, build 10580, KV q8_0):
   90.112 → 872,7 tok/s, 98.304 → 845,5 tok/s, 131.072 → 756,5 tok/s.
   Canary qua gateway thật: 86.101 token prompt / 89.716 token ước lượng chạy
   102,0 giây, trả đúng sentinel đầu-cuối, VRAM đỉnh 22.639 MiB, không OOM.
   `qwen38-vision` vẫn giữ 65536 cho tới benchmark có mmproj.
   Nguồn của mốc 200K: sweep cộng đồng
   trên đúng RTX 3090 (23,3/24,6 GB, 54,2 tok/s) — *"262K exceeded 24 GB at model
   load"*, nên **204800 chứ không phải 262144**.
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
        max_context=131_072,
        mo_ta="Qwen3.8-27B - coding, chat, agent, tom tat. Ngu canh 131K.",
    ),
    ModelSpec(
        ten="qwen38-ops",
        co_vision=False,
        max_context=204_800,
        mo_ta="Qwen3.8-27B - van hanh, ngu canh dai 200K, khong doc anh",
    ),
    ModelSpec(
        ten="qwen38-vision",
        co_vision=True,
        max_context=65_536,
        mo_ta="Qwen3.8-27B - doc anh/anh chup man hinh, ngu canh 64K",
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
