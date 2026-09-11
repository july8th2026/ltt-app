"""
dieu_phoi.py — MỘT đường gọi model ngôn ngữ cho toàn nền tảng. (H38)

⭐ ĐÂY LÀ CÂY CẦU CÒN THIẾU. Trước nó, ba nơi tự gọi nhà cung cấp, mỗi nơi một kiểu:

     platform_core/agent/planner.py    ghi cứng `thu_tu_provider=["gemini"]` VÀ
                                       ghi cứng luôn HTTP của Gemini
                                       (cả hai đã gỡ ở pha 05.3 / 07)
     apps/autosubvideo/ai_workflows.py
     apps/<slug>/jobs.py

   Cascade đa-provider của H8 **có tồn tại**, nhưng chỉ ở tầng *cấp key*. Không ai
   bắc cầu nó sang tầng *gọi model*. Hệ quả: thêm một provider vào `REGISTRY`
   **không làm app nào dùng nó cả**. Module này là cây cầu đó.

⭐ CASCADE Ở ĐÂY LÀ HỢP LỆ — VÀ NÓ KHÁC HẲN CÁI D-010 CẤM.

   D-010 cấm **đổi model sau lưng khách**. Chỗ đó là API bán ra ngoài: khách trả
   tiền cho Qwen3.8-27B mà nhận về Gemini là bán sai hàng. `llm_gateway` và
   `cong_vlm.chat()` **không có** đường fallback, và có test soi chữ ký hàm để
   giữ nguyên như vậy.

   Module này phục vụ **việc nội bộ của nền tảng** (lập kế hoạch agent, tóm tắt,
   sinh phụ đề…). Ở đó không có lời hứa nào với khách về *model nào*, và bên gọi
   **tự khai thứ tự** trong `thu_tu_provider`. Khai ra thì không phải là lén.

⛔ BẬN KHÔNG PHẢI LỖI. `BanError` ⇒ **đi tiếp provider sau**, và **KHÔNG** gọi
   `api_pool.danh_dau_loi()`. Nếu lẫn, key `ltt_llm` bị cooldown rồi
   `disable` sau 5 lần — một tối máy B chạy video sẽ tự tắt vĩnh viễn model nhà.

⛔ VƯỢT NGÂN SÁCH KHÔNG PHẢI LỖI CỦA PROVIDER, VÀ KHÔNG ĐƯỢC CASCADE. Một yêu cầu
   quá to sẽ quá to với **mọi** provider. Thử lại ở nơi khác chỉ tốn thêm tiền và
   thêm thời gian, rồi vẫn hỏng.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Sequence

from platform_core.llm.cong_vlm import (AmbiguousProviderError, BanError,
                                        CongVlm, CongVlmError, KetQuaChat,
                                        ProviderOomError, SuDung,
                                        VuotNganSachError)

log = logging.getLogger(__name__)

#: Provider nói giao thức OpenAI (cổng VLM máy B). Thêm provider mới cùng loại
#: thì thêm vào đây, **không** viết thêm một nhánh `if` ở dưới.
PROVIDER_OPENAI = ("ltt_llm",)

# 🔴 `PROVIDER_GEMINI` ĐÃ GỠ 09/09/2026 (AI CLEAN REBUILD V2 pha 07) cùng hàm
#    `_goi_gemini` và nhánh `if` của nó trong vòng lặp bên dưới.
#
# ⛔ Đừng thêm lại một hằng số nào có hình dạng ấy. Chú thích ngay trên đã nói
#    luật: *"thêm provider mới cùng loại thì thêm vào `PROVIDER_OPENAI`, KHÔNG
#    viết thêm một nhánh `if` ở dưới"*. Một họ giao thức thứ hai chỉ đáng có khi
#    nó **thật sự** khác giao thức — Gemini là họ duy nhất từng như vậy, và nó
#    không còn được phục vụ.


class KhongCoProviderNao(RuntimeError):
    """Mọi provider trong danh sách đều bận hoặc không cấp được key.

    ⛔ **Không phải lỗi provider.** Bên gọi nên báo "hệ thống đang bận, thử lại
       sau" chứ đừng đánh dấu lỗi cho key nào.
    """

    def __init__(self, chi_tiet: Sequence[str]):
        super().__init__("khong provider nao phuc vu duoc: " + "; ".join(chi_tiet))
        self.chi_tiet = list(chi_tiet)
        self.busy_only = bool(self.chi_tiet) and all(
            item.rstrip().endswith(": ban") for item in self.chi_tiet)


def _goi_openai(base_url: str, credential: str, than: dict, timeout_s: float) -> KetQuaChat:
    import httpx

    from platform_core.llm import ngat

    # 🔴 MỘT `Client` CÓ TÊN, KHÔNG PHẢI `httpx.request`. Hai lý do, và lý do thứ
    #    hai mới là lý do đổi:
    #      1. dùng lại kết nối giữa hai lượt liên tiếp tới cùng máy B;
    #      2. **có thứ để đóng**. Khách ngắt giữa một lượt đồng bộ thì cửa phải
    #         cắt được kết nối tới máy B (spec §16) — `httpx.request` dựng client
    #         bên trong rồi vứt đi, nên không ai cầm được cái tay nắm ấy, và lượt
    #         vẫn chạy hết trên GPU cho một người đã đi.
    client = httpx.Client(timeout=timeout_s)
    ngat.ghi_nhan(client.close)

    def goi(method, path, *, json=None, timeout=None):
        headers = {"Authorization": f"Bearer {credential}"} if credential else {}
        try:
            r = client.request(method, base_url.rstrip("/") + path, json=json,
                               headers=headers, timeout=timeout or timeout_s)
        except httpx.HTTPError as e:
            raise AmbiguousProviderError(
                f"mat ket noi sau khi bat dau gui: {type(e).__name__}") from None
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {}

    try:
        return CongVlm(goi=goi, timeout_s=timeout_s).chat(**than)
    finally:
        client.close()


def goi(db, *, messages: list, thu_tu_provider: Sequence[str],
        category: Optional[str] = None, model: Optional[str] = None,
        model_theo_provider: Optional[dict] = None,
        tools: Optional[list] = None, max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
        timeout_s: float = 120.0, on_dispatch=None,
        on_rejected=None) -> KetQuaChat:
    """Gọi model theo **thứ tự provider bên gọi khai**, bỏ qua provider đang bận.

    ⭐ `model_theo_provider` — vì **mỗi provider có id model riêng**. Gửi nhầm tên
       sang provider kia thì nó từ chối, và bên gọi sẽ tưởng provider đó "đang
       hỏng". Khai rõ:

           model_theo_provider={"ltt_llm": "qwen38-api"}

    🔴 VÍ DỤ TRÊN TỪNG GHI `{"ltt_llm": "ltt_llm"}`, VÀ NÓ ĐÃ DẠY SAI HAI NƠI.

       `ltt_llm` là **bí danh công khai** của app, không phải id model. Khoá của
       provider chỉ khai `qwen38-api` / `qwen38-vision`, nên `chon_key` với
       `model="ltt_llm"` **luôn** ném `ThieuKeyError` — và hàm này đọc đó là
       "provider không phục vụ được, đi tiếp", tức **im lặng bỏ qua provider**.

       Hai nơi chép theo ví dụ cũ và cả hai đều hỏng suốt nhiều tháng:
       `platform_core/agent/planner.py` (mọi lượt lập kế hoạch rơi xuống Gemini
       dù khai "model nhà đi trước") và `tools/kiem_ltt_llm.py` (không bao giờ
       xanh nổi, và đỏ về phía báo động). Tìm ra ở Prompt 08, 01/09.

    ⭐ Bài học đáng hơn cả hai lỗi: **một ví dụ trong docstring là mã mà người ta
       chép**. Nó sai thì nó không sai một mình.

    ⛔ Đừng gõ id nội bộ ở bên gọi — hỏi `providers.models_for(...)`. Ngày đổi
       GGUF bên dưới, registry đổi và bên gọi đi theo.

       Thiếu khai cho provider nào thì rơi về `model` chung.

    Ném `KhongCoProviderNao` khi cạn danh sách, `VuotNganSachError` ngay lập tức
    khi yêu cầu quá to (không cascade — nó sẽ quá to ở mọi nơi).
    """
    from platform_core import api_keys, api_pool, providers
    from platform_core.models import APIKEY_CAT_CHAT

    cat = category or APIKEY_CAT_CHAT
    ban_do = dict(model_theo_provider or {})
    ly_do: list[str] = []

    for pid in thu_tu_provider:
        # ⛔ AI CLEAN REBUILD V2 — CỔNG FAIL-CLOSED, ĐẶT TRƯỚC MỌI THỨ KHÁC.
        #
        #    Provider đã ngừng thì **không bao giờ** tới được `chon_key`, nên
        #    không có đường nào lọt xuống HTTP. Ghi vào `ly_do` để thông điệp
        #    lỗi cuối nói thật ra chuyện gì, thay vì đổ cho "bận".
        #
        # ⚠️ ĐÂY KHÔNG PHẢI `BanError`. "Bận" nghĩa *đi tiếp rồi quay lại sau*;
        #    "đã ngừng" nghĩa *không còn là một đường chạy*. Nếu ai đó về sau
        #    đổi nhánh này thành `BanError` thì đường lui legacy sống lại y
        #    nguyên — chỉ khác cái tên.
        #    ⚠️ Hỏi `providers.da_ngung()` chứ KHÔNG đọc `.is_active` trên vật
        #       thể `get()` trả về: `get()` bị monkeypatch ở nhiều phép kiểm và
        #       trả `SimpleNamespace` không có trường đó. Sự thật về retire nằm
        #       ở `REGISTRY`, nên hỏi đúng chỗ ấy.
        if providers.da_ngung(pid):
            ly_do.append(f"{pid}: da ngung phuc vu (khong phai ban)")
            log.info("provider %s da ngung, bo qua", pid)
            continue

        ten_model = ban_do.get(pid, model) or ""
        try:
            key = api_pool.chon_key(db, category=cat, model=ten_model or None,
                                    thu_tu_provider=[pid])
        except Exception as e:
            ly_do.append(f"{pid}: khong cap duoc key ({type(e).__name__})")
            continue

        prov = providers.get(pid)
        credential = api_keys.lay_credential(db, key)

        # ⭐ `base_url` CỦA KHOÁ ĐI TRƯỚC `base_url` CỦA REGISTRY.
        #
        #    Registry đọc `LTT_LLM_BASE_URL` từ biến môi trường — nó có mặt trong
        #    tiến trình web/worker nhưng **không** có trong một script chạy tay.
        #    Bản ghi khoá thì luôn mang theo địa chỉ, vì `api_keys.tao_key()` có sẵn
        #    trường đó chính để làm việc này.
        #
        #    ⚠️ Đã dính thật 22/08: `dieu_phoi` chỉ đọc registry ⇒ `base_url` rỗng ⇒
        #    HTTP 599 ⇒ `KhongCoProviderNao`, trông y như "máy B chết" trong khi máy
        #    B đang chạy tốt và khoá thì hoàn toàn đúng.
        base = (getattr(key, "base_url", "") or "").strip() \
            or (getattr(prov, "base_url", "") or "").strip()
        try:
            if pid in PROVIDER_OPENAI:
                than = {"model": ten_model, "messages": messages, "tools": tools,
                        "max_tokens": max_tokens, "temperature": temperature,
                        "reasoning_effort": reasoning_effort}
                if not base:
                    # Không có địa chỉ thì đừng gửi đi đâu cả và đừng đánh dấu lỗi
                    # cho khoá — đây là **thiếu cấu hình**, không phải provider hỏng.
                    ly_do.append(f"{pid}: thieu base_url (ca o khoa lan o registry)")
                    continue
                if on_dispatch is not None:
                    on_dispatch(pid)
                kq = _goi_openai(base, credential,
                                 {k: v for k, v in than.items() if v is not None},
                                 timeout_s)
            else:
                ly_do.append(f"{pid}: chua biet giao thuc cua provider nay")
                continue
        except BanError as e:
            if on_rejected is not None:
                on_rejected(pid)
            # ⛔ KHÔNG `danh_dau_loi`. Bận không phải hỏng — xem đầu tệp.
            log.info("provider %s dang ban, di tiep: %s", pid, e)
            ly_do.append(f"{pid}: ban")
            continue
        except VuotNganSachError:
            # ⛔ KHÔNG cascade. Quá to ở đây thì quá to ở mọi nơi.
            raise
        except (AmbiguousProviderError, ProviderOomError):
            # Không cascade: timeout sau POST có thể đã tạo side effect; OOM
            # nguyên request sẽ lặp lại y hệt ở sản phẩm không cho fallback.
            raise
        except CongVlmError as e:
            if on_rejected is not None:
                on_rejected(pid)
            api_pool.danh_dau_loi(db, key)
            ly_do.append(f"{pid}: loi ({e})")
            continue
        finally:
            credential = ""

        api_pool.danh_dau_thanh_cong(db, key, tokens=kq.su_dung.token_ra)
        return kq

    raise KhongCoProviderNao(ly_do)
