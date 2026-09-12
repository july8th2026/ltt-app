"""
catalog.py — model nào được mở, và mỗi model chịu được gì.

⭐ HAI HỒ SƠ, HAI MODEL, HAI CARD (từ 12/09 — Dual-model). Mỗi hồ sơ nạp cả
   `mmproj`, nên **không còn hồ sơ vision riêng**:

     qwen38-api   Qwen3.8-27B  221K ngữ cảnh, KV q4_0, text+ảnh   RTX 3090
     qwen35-api   Qwen3.5-9B   262K ngữ cảnh, KV q8_0, text+ảnh   RTX 5060 Ti

   `llama-swap` định tuyến theo tên model client gọi. Hai hồ sơ này ở **hai card
   khác nhau** nên chúng nằm trong VRAM **cùng lúc** — khác hẳn thời hai hồ sơ
   tranh một card, và đó là lý do sổ suất phải tách theo model
   (`so_theo_model.py`).

🔴 TRƯỚC 12/09 CÓ MỘT HỒ SƠ VISION RIÊNG (`qwen38-vision`, 131K) VÌ TRÊN CARD
   24 GB **không thể vừa nạp `mmproj` vừa mở ngữ cảnh 200K** — và việc đổi giữa
   hai hồ sơ ấy **giết lượt đang chạy** (đo 03/09; khách chỉ nhận
   `ConnectionReset`). §G1b đo lại ở `-np 3`: `-c 221184` + mmproj **cùng vừa**
   card, biên 445 MiB. Nên hồ sơ vision không bị "dọn cho gọn" — nó hết lý do
   tồn tại, và cùng lúc nguồn `ConnectionReset` ấy biến mất.

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

✅ (LỊCH SỬ — hồ sơ này đã gỡ 12/09; số đo giữ lại vì nó là bằng chứng KV q4_0
   **không** làm mù mắt model, và câu hỏi đó sẽ quay lại ở mọi lần đổi KV.)
   `qwen38-vision` 131072 / KV q4_0 — đo thật 03/09, cùng ngày, trên một hồ sơ
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
    #: Trần ngữ cảnh của hồ sơ — phải bằng đúng `-c` mà `llama-swap.yaml` truyền
    #: cho `llama-server`. Đây chỉ là chỗ **công bố**; tệp kia mới là chỗ **khởi
    #: động tiến trình**, và `test_334_ngan_sach_ltt_llm.py` buộc hai bên khớp
    #: (lệch thì `/v1/models` nói một đằng, model chạy một nẻo).
    #:
    #: ⛔ "CHỜ P5 xác nhận" là câu cũ ở đây; P5 đã đo xong 03/09 và số đã chốt.
    max_context: int
    #: Mô tả ngắn, trả trong `/v1/models` để người dùng chọn đúng hồ sơ.
    mo_ta: str


#: Bảng khai. Đây KHÔNG phải danh sách đang mở — xem `nap_catalog`.
#:
#: 🔵 12/09 (Dual-model 4.2): **đúng hai hồ sơ, cả hai `text + image`**.
#:
#:    `qwen38-vision` biến mất. Không phải dọn dẹp: `llama-swap.yaml` (Task 3.3,
#:    commit faf5e864) chỉ còn mở `qwen38-api` và `qwen35-api`, nên từ lúc yaml
#:    ấy deploy thì một dòng `qwen38-vision` ở đây **công bố một model llama-swap
#:    không khởi động nổi** — khách gọi nó sẽ nhận lỗi thượng nguồn, không phải
#:    một câu trả lời chậm. Thứ duy nhất đứng giữa là `LTT_LLM_MODELS`
#:    fail-closed, và một cái van đóng không phải một lời khai đúng.
#:
#:    Cả hai hồ sơ nạp `mmproj` (L-14 hệ quả 4, §G1b/§G3b) ⇒ không còn hồ sơ nào
#:    từ chối ảnh, nên `co_vision=False` không còn tồn tại trong bảng này. Đó là
#:    chỗ nguồn `ConnectionReset` cũ biến mất: llama-swap không phải đổi hồ sơ
#:    giữa chừng để nhìn một cái ảnh nữa.
HO_SO: tuple[ModelSpec, ...] = (
    ModelSpec(
        ten="qwen38-api",
        co_vision=True,
        # 📈 12/09: 204.800 -> 221.184 (L-14, 10_BENCHMARK_P3 §G1b). Nguon
        #    chan ly `apps/ltt_llm/ngan_sach.CUA_SO_THEO_MODEL`; kho nay deploy
        #    sang may B nen khong import duoc, `test_334` buoc hai dau lai.
        max_context=221_184,
        mo_ta="Qwen3.8-27B - coding, chat, agent, tom tat, doc anh. Ngu canh 221K.",
    ),
    ModelSpec(
        ten="qwen35-api",
        co_vision=True,
        # 📈 12/09: ho so moi (D06/L-14). 262.144 x 3 slot VUA THOAI MAI tren
        #    5060 Ti (§G3: VRAM 13.423, bien 2.888; §G3b voi MTP: 15.309, bien
        #    1.002) — khac 3090, noi cung con so ay tran. Nguon chan ly
        #    `apps/ltt_llm/ngan_sach.CUA_SO_THEO_MODEL`; kho nay deploy sang may B
        #    nen khong import duoc, `test_334` buoc hai dau lai.
        max_context=262_144,
        mo_ta="Qwen3.5-9B Q6_K - nhanh, re, doc anh. Ngu canh 262K.",
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
