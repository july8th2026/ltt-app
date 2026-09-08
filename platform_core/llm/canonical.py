"""canonical.py — ĐIỂM NỐI DUY NHẤT cho model ngôn ngữ nội bộ. (AI CLEAN REBUILD V2, pha 05)

## Vì sao nó phải nằm ở `platform_core`, không nằm ở `apps/ltt_llm`

Ba bên cần cùng một bảng bí danh, và **không bên nào** được lấy nó từ
`apps/ltt_llm` — `.importlinter` cưỡng chế cả ba ranh giới:

    apps/{taovideo,autosubvideo,prompt_ai_ommi,chataistudio}
        -> chan boi contract `app-doc-lap-voi-nhau` (independence)
    platform_core/agent/planner.py
        -> chan boi contract `nen-tang-khong-phu-thuoc-app` (forbidden)
    server/api/streaming.py
        -> chan boi `server-khong-phu-thuoc-app-cu-the`, dang mang 2 `ignore_imports`

⭐ Đây **không phải** một thiết kế tôi nghĩ ra. Chính `.importlinter` đã ghi
   sẵn đáp án, ngay cạnh hai món nợ nó đang miễn trừ:

       "Duong ra dung la day hai thu ay len `platform_core` (mot diem noi cho
        provider LLM), khong phai noi long hop dong."

`apps/ltt_llm/features.py` giữ nguyên tên cũ nhưng **trỏ về đây**, nên hợp đồng
công khai của app không đổi và không có hai bản chân lý.

## ⛔ KHÔNG thêm provider ngoài vào `THU_TU_PROVIDER`

Đây là hàng **bán ra ngoài**: khách trả tiền cho `ltt_llm` mà nhận về Gemini là
bán sai hàng (**D-010**). Máy B bận thì **báo bận** và để khách quyết định.

⚠️ Khác hẳn `platform_core/agent/planner.py`, nơi cascade là **hợp lệ** vì đó là
việc nội bộ và không có lời hứa nào với khách về *model nào*. Hai chỗ ấy trông
giống nhau và có luật ngược nhau — đó là lý do câu này viết ra thay vì để người
sau tự suy.
"""
from __future__ import annotations

#: Thứ tự provider cho **mọi** đường gọi LLM nội bộ. Một phần tử, không đường lui.
THU_TU_PROVIDER: tuple[str, ...] = ("ltt_llm",)

#: 🔑 ALIAS CÔNG KHAI → ID NỘI BỘ. Lớp đệm, và nó có lý do sống:
#:
#:    "Aliases exist so a vendor change is not a breaking change. If the raw id
#:     leaks anywhere a customer reads, integrations start pinning to it and the
#:     alias stops being a layer of insulation."   — test_212
ALIAS_SANG_ID: dict[str, str] = {
    "ltt_llm": "qwen38-api",
    "ltt_llm_vision": "qwen38-vision",
}

MODEL_MAC_DINH = "ltt_llm"
MODEL_HOP_LE = tuple(ALIAS_SANG_ID)


def ban_do_model(*alias: str) -> dict[str, str]:
    """`model_theo_provider` cho `dieu_phoi.goi()` — id THẬT, không phải bí danh.

        >>> ban_do_model()                 # {"ltt_llm": "qwen38-api"}
        >>> ban_do_model("ltt_llm_vision") # {"ltt_llm": "qwen38-vision"}

    🔴 **HÀM NÀY TỒN TẠI ĐỂ CHẶN MỘT LỖI ĐÃ XẢY RA HAI LẦN.**

    Docstring của `dieu_phoi.goi` từng dạy:

        model_theo_provider={"ltt_llm": "ltt_llm"}      # ⛔ SAI

    `ltt_llm` là **bí danh app**, không phải id model — khoá provider chỉ khai
    `qwen38-api`/`qwen38-vision`. Nên `api_pool.chon_key(model="ltt_llm")`
    **luôn** ném `ThieuKeyError`, và `dieu_phoi.goi()` đọc đó thành *"provider
    không phục vụ được, đi tiếp"* ⇒ **bỏ qua model nhà trong im lặng** rồi
    xuống provider sau. Không lỗi, không cảnh báo, chỉ một hoá đơn.

    ⭐ Và lỗi ấy **đã bị bắt một lần rồi** — `apps/ltt_llm/features.py` ghi:
       *"Bản đầu của tôi đặt alias TRÙNG HỆT id nội bộ (`ltt_llm` → `ltt_llm`),
       tức là xoá sạch lớp đệm."* Nó được sửa **ở đó** và sống tiếp **ở
       docstring `dieu_phoi`**, rồi dạy sai hai nơi chép theo. Hai bản sao của
       một đoạn ý, một bản đã học bài học.

    ⇒ Bên gọi **không bao giờ** tự dựng dict này nữa. `test_1001` chốt rằng
      không bí danh nào ánh xạ về chính nó.
    """
    ten = alias[0] if alias else MODEL_MAC_DINH
    if ten not in ALIAS_SANG_ID:
        raise KeyError(f"bi danh la: {ten!r} (hop le: {MODEL_HOP_LE})")
    return {THU_TU_PROVIDER[0]: ALIAS_SANG_ID[ten]}
