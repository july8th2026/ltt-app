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

from platform_core.registry import AdmissionModel

#: Thứ tự provider cho **mọi** đường gọi LLM nội bộ. Một phần tử, không đường lui.
THU_TU_PROVIDER: tuple[str, ...] = ("ltt_llm",)

#: 🔑 ALIAS CÔNG KHAI → ID NỘI BỘ. Lớp đệm, và nó có lý do sống:
#:
#:    "Aliases exist so a vendor change is not a breaking change. If the raw id
#:     leaks anywhere a customer reads, integrations start pinning to it and the
#:     alias stops being a layer of insulation."   — test_212
#:
#: 🔴 CẮT TÊN CŨ 11/09/2026 (D02, dual-model 2.3). Trước ngày này bảng là
#:    `{"ltt_llm": "qwen38-api", "ltt_llm_vision": "qwen38-vision"}` — hai bí
#:    danh **trùng hệt tên app**, tức lớp đệm chỉ tồn tại trên giấy. Nay đúng
#:    HAI tên công khai, và cả hai đều khác app slug:
#:
#:        ltt-3.8   -> qwen38-api    (mặc định, cư trú 3090)
#:        ltt-3.5   -> qwen35-api    (5060 Ti)
#:
#: ⛔ `ltt_llm`, `ltt_llm_vision`, `qwen38-vision` **không còn là model**. Mọi
#:    cửa phải trả `model_not_found`, không phải 500 và không phải "im lặng rơi
#:    về mặc định" — một tên cũ âm thầm chạy trên model khác là bán sai hàng.
ALIAS_SANG_ID: dict[str, str] = {
    "ltt-3.8": "qwen38-api",
    "ltt-3.5": "qwen35-api",
}

MODEL_MAC_DINH = "ltt-3.8"
MODEL_HOP_LE = tuple(ALIAS_SANG_ID)

#: 🔑 Mặc định cho việc LLM **NỘI BỘ** (D09 phương án C, dual-model 2.4).
#:
#: ⚠️ ĐỪNG gộp nó với `MODEL_MAC_DINH`. Hai hằng số này trả lời hai câu khác
#:    nhau và **cố ý** mang hai giá trị khác nhau:
#:
#:        MODEL_MAC_DINH          khách gọi `text.chat` mà không nói model
#:                                ⇒ `ltt-3.8` (hàng đầu bảng, cư trú 3090)
#:        MODEL_NOI_BO_MAC_DINH   nền tảng/app tự gọi LLM cho việc của mình
#:                                ⇒ `ltt-3.5` (5060 Ti)
#:
#: 🔴 Lý do CƠ HỌC, không phải khẩu vị: D01 B cho model ảnh mượn 3090 trong cửa
#:    sổ sinh ảnh, nên `ltt-3.8` **không nạp được** trong lúc một job ảnh đang
#:    chạy. Một job ảnh vừa GIỮ 3090 vừa CHỜ `ltt-3.8` là một vòng chờ kín.
#:
#: ⭐ Và nó còn là lựa chọn NHANH HƠN, nên đừng đọc dòng trên như một sự hy
#:    sinh: đo 11/09/2026 trên máy B — LTT-3.5 73 tok/s ở cửa sổ 262.144
#:    (5060 Ti); LTT-3.8 66,7 tok/s ở 221.184 (3090); cùng 3 slot.
MODEL_NOI_BO_MAC_DINH = "ltt-3.5"


def ban_do_model(*alias: str) -> dict[str, str]:
    """`model_theo_provider` cho `dieu_phoi.goi()` — id THẬT, không phải bí danh.

        >>> ban_do_model()            # {"ltt_llm": "qwen38-api"}   (provider -> id)
        >>> ban_do_model("ltt-3.5")   # {"ltt_llm": "qwen35-api"}

    ⚠️ KHOÁ của dict là **provider id** (`ltt_llm`, `THU_TU_PROVIDER[0]`), không
       phải bí danh model. Hai thứ trùng chữ cho tới 11/09/2026 và chính sự
       trùng đó là thứ dạy sai ba nơi; nay bí danh là `ltt-3.8`/`ltt-3.5` nên
       khoảng cách nhìn thấy được.

    🔴 **HÀM NÀY TỒN TẠI ĐỂ CHẶN MỘT LỖI ĐÃ XẢY RA HAI LẦN.**

    Docstring của `dieu_phoi.goi` từng dạy:

        model_theo_provider={"ltt_llm": "ltt_llm"}      # ⛔ SAI

    `ltt_llm` là **bí danh app**, không phải id model — khoá provider chỉ khai
    `qwen38-api`/`qwen35-api`. Nên `api_pool.chon_key(model="ltt_llm")`
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


def model_noi_bo_cua(slug_app: str) -> str:
    """Model mà app `slug_app` khai cho việc LLM **nội bộ** của nó (D09).

        >>> model_noi_bo_cua("anhnoibo")      # "ltt-3.5"

    Không đọc được bản khai (app không tồn tại, registry lỗi, giá trị lạ) ⇒
    `MODEL_NOI_BO_MAC_DINH` **kèm một dòng cảnh báo**.

    ⭐ VÌ SAO ĐỌC BẢN KHAI THAY VÌ MỘT HẰNG SỐ. Trước 2.4 mọi đường nội bộ
       truyền `MODEL_MAC_DINH` — một hằng số duy nhất cho sáu người gọi ở sáu
       app. D01 B làm hằng số ấy **sai với một nhóm app**: job ảnh giữ 3090 rồi
       đi chờ một model chỉ nạp được khi 3090 rảnh. Sửa bằng cách đổi hằng số
       thì nhóm kia mất quyền chọn; sửa bằng một `if` theo tên app thì nền tảng
       biết tên app (điều `test_60` cấm). Nên app **khai**, nền tảng **đọc** —
       đúng khuôn `credit_cost`/`bang_gia`/`suc_khoe` ngay cạnh nó.

    ⛔ Cảnh báo chứ không ném: đây là đường nội bộ của một app đang chạy, và
       một `RegistryError` ở đây làm hỏng job của khách để đổi lấy đúng không
       gì cả — bản khai sai đã bị `registry._validate` từ chối **lúc nạp**, nên
       tới được đây nghĩa là app hỏng ở chỗ khác. Rơi về 3.5 là hướng an toàn:
       3.5 không bao giờ tranh card với model ảnh.
    """
    import logging

    log = logging.getLogger(__name__)
    try:
        from platform_core.registry import discover

        for it in discover():
            if it.manifest.slug != slug_app:
                continue
            ten = (getattr(it.manifest, "model_llm_noi_bo", "") or "").strip()
            if ten in ALIAS_SANG_ID:
                return ten
            log.warning(
                "app %r khai model noi bo la %r (khong hop le); dung %r",
                slug_app, ten, MODEL_NOI_BO_MAC_DINH)
            return MODEL_NOI_BO_MAC_DINH
        log.warning("khong tim thay app %r trong registry; dung model noi bo %r",
                    slug_app, MODEL_NOI_BO_MAC_DINH)
    except Exception:                                          # noqa: BLE001
        log.warning("khong doc duoc ban khai model noi bo cua %r; dung %r",
                    slug_app, MODEL_NOI_BO_MAC_DINH, exc_info=True)
    return MODEL_NOI_BO_MAC_DINH


#: Mặc định khi không đọc được bản khai của app. Xem `tai_nguyen_nha()`.
_TAI_NGUYEN_MAC_DINH = AdmissionModel("llm_remote", 1)


def tool_nha():
    """`ToolSpec` của tool model nhà, đọc từ **bản khai của app**. `None` nếu không có.

    ⭐ Một hàm chứ không phải ba vòng lặp giống nhau: `tai_nguyen_nha()` cần
       `AdmissionModel`, phòng chờ cần ngân sách KV của nó, và đường ước token
       cần chính `ToolSpec` để lấy executor. Ba bên đọc ba lần cùng một bản khai
       là ba chỗ sẽ trôi khỏi nhau khi bản khai đổi.

    ⛔ "Tool có khai admission" hỏi bằng `admission_cho`, KHÔNG bằng
       `admission_resource` (multijob 2.2): một tool khai `admission_theo_model`
       có `admission_resource` RỖNG, nên phép thử cũ sẽ bỏ qua đúng cái tool nó
       đi tìm — và rơi về mặc định trong im lặng.
    """
    from platform_core.registry import discover

    for it in discover():
        if it.manifest.slug != THU_TU_PROVIDER[0]:
            continue
        for t in it.manifest.tools:
            if t.admission_theo_model:
                return t
            if t.admission_cho() is not None:
                return t
    return None


def tai_nguyen_nha(model: str) -> AdmissionModel:
    """`AdmissionModel` để giành suất admission trước khi chạm máy B.

    🔴 **MỌI đường tới máy B phải giành suất.** Máy B có số suất hữu hạn mỗi
    model (ngày viết là một), nên một đường quên `admission` không chỉ chen
    hàng — nó làm chính cơ chế đếm suất **sai**.

    ⚠️ Lỗ đó đã có thật một lần: tới 01/09 `agent/planner.py` là **đường duy
    nhất** tới máy B không đi qua `admission`; ba đường kia (`streaming`,
    `chat`, `job_runner`) đều giành. Nó vô hại suốt nhiều tháng chỉ vì một lỗi
    **thứ hai** che nó (nhánh `ltt_llm` không bao giờ cấp được khoá vì lỗi bí
    danh) — tức sửa lỗi kia mà không sửa lỗi này là **kích hoạt** một đường lách.

    ⇒ Hàm này nằm ở `canonical` chứ không nằm riêng trong `planner`, vì pha 05
      di trú **bốn app** sang máy B và mỗi app tự chép sẽ thành bốn bản sao của
      cùng một quyết định — đúng khuôn hỏng mà chiến dịch này gặp ba lần.

    ⛔ Đọc từ **bản khai của app**, không gõ tay: gõ tay ở đây là bản sao thứ
      hai của bản khai admission trong manifest, và hai bản sẽ trôi khỏi nhau.

    ⭐ `model` BẮT BUỘC (multijob 2.2). `text.chat` sắp phục vụ hai model trên
       hai pool KV khác nhau, nên "tài nguyên của model nhà" không còn là MỘT
       câu trả lời. Một mặc định ngầm ở đây sẽ cho mọi bên gọi câu trả lời của
       model *khác* mà không ai thấy — nên bên gọi phải nói ra nó đang dùng model
       nào. Từ 2.4 bên gọi nội bộ truyền `model_noi_bo_cua(<slug app>)`, tức
       bản khai của chính app đó — **không** `MODEL_MAC_DINH` nữa (D09).

    🔴 `KeyError` KHÔNG bị nuốt. Model lạ trên một tool đã phân biệt theo model
       là fail-closed có chủ ý (`suc_chua_admission`); rơi về `_TAI_NGUYEN_MAC_DINH`
       ở đó nghĩa là giành **sai pool** — và một suất giành sai không bảo vệ gì.
    """
    import logging

    try:
        t = tool_nha()
        if t is not None:
            suc = t.admission_cho(model)
            if suc is not None:
                return suc
    except KeyError:
        raise
    except Exception:                                          # noqa: BLE001
        # ⛔ NÓI RA. Rơi về mặc định thì vẫn chạy được, nhưng nếu bản khai đã đổi
        #    mà chỗ này không đọc được thì ta sẽ giành **sai tài nguyên** — và
        #    một suất giành sai không bảo vệ gì cả. Nuốt im lặng ở đây nghĩa là
        #    lớp bảo vệ biến mất mà không ai biết.
        logging.getLogger(__name__).warning(
            "khong doc duoc ban khai %s; dung mac dinh %s",
            THU_TU_PROVIDER[0], _TAI_NGUYEN_MAC_DINH, exc_info=True)
    return _TAI_NGUYEN_MAC_DINH
