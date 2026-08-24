"""
dieu_phoi.py — MỘT đường gọi model ngôn ngữ cho toàn nền tảng. (H38)

⭐ ĐÂY LÀ CÂY CẦU CÒN THIẾU. Trước nó, ba nơi tự gọi nhà cung cấp, mỗi nơi một kiểu:

     platform_core/agent/planner.py    ghi cứng `thu_tu_provider=["gemini"]` VÀ
                                       ghi cứng luôn HTTP của Gemini
     apps/autosubvideo/ai_workflows.py
     apps/kichban/jobs.py

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

from platform_core.llm.cong_vlm import (BanError, CongVlm, CongVlmError,
                                        KetQuaChat, SuDung, VuotNganSachError)

log = logging.getLogger(__name__)

#: Provider nói giao thức OpenAI (cổng VLM máy B). Thêm provider mới cùng loại
#: thì thêm vào đây, **không** viết thêm một nhánh `if` ở dưới.
PROVIDER_OPENAI = ("ltt_llm",)

#: Provider nói giao thức Gemini.
PROVIDER_GEMINI = ("gemini",)


class KhongCoProviderNao(RuntimeError):
    """Mọi provider trong danh sách đều bận hoặc không cấp được key.

    ⛔ **Không phải lỗi provider.** Bên gọi nên báo "hệ thống đang bận, thử lại
       sau" chứ đừng đánh dấu lỗi cho key nào.
    """

    def __init__(self, chi_tiet: Sequence[str]):
        super().__init__("khong provider nao phuc vu duoc: " + "; ".join(chi_tiet))
        self.chi_tiet = list(chi_tiet)


def _goi_openai(base_url: str, credential: str, than: dict, timeout_s: float) -> KetQuaChat:
    import httpx

    def goi(method, path, *, json=None, timeout=None):
        headers = {"Authorization": f"Bearer {credential}"} if credential else {}
        try:
            r = httpx.request(method, base_url.rstrip("/") + path, json=json,
                              headers=headers, timeout=timeout or timeout_s)
        except httpx.HTTPError as e:
            return 599, {"loi": f"{type(e).__name__}"}
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {}

    return CongVlm(goi=goi, timeout_s=timeout_s).chat(**than)


def _goi_gemini(model: str, credential: str, messages: list,
                max_tokens: Optional[int], timeout_s: float) -> KetQuaChat:
    """Dịch sang dạng dây của Gemini. Chỉ ở ĐÂY, không rải khắp nơi."""
    import httpx

    phan = []
    for tin in messages:
        noi = tin.get("content")
        if isinstance(noi, str) and noi:
            phan.append({"text": noi})
        elif isinstance(noi, list):
            for p in noi:
                if isinstance(p, dict) and p.get("type") in ("text", "input_text"):
                    phan.append({"text": str(p.get("text") or "")})

    than: dict[str, Any] = {"contents": [{"parts": phan}]}
    if max_tokens:
        than["generationConfig"] = {"maxOutputTokens": int(max_tokens)}

    try:
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": credential}, json=than, timeout=timeout_s)
    except httpx.HTTPError as e:
        raise CongVlmError(f"gemini loi mang: {type(e).__name__}") from None

    if r.status_code == 429:
        # Gemini cung dung 429 cho "qua nhieu yeu cau". Cung mot luat: khong phai loi.
        raise BanError("gemini gioi han tan suat")
    if r.status_code != 200:
        raise CongVlmError(f"gemini HTTP {r.status_code}")

    d = r.json()
    ung = (d.get("candidates") or [{}])[0]
    van = "".join(str(p.get("text") or "")
                  for p in ((ung.get("content") or {}).get("parts") or []))
    um = d.get("usageMetadata") or {}
    co_so = "promptTokenCount" in um
    return KetQuaChat(
        noi_dung=van,
        finish_reason=str(ung.get("finishReason") or ""),
        model=model,
        su_dung=SuDung(token_vao=int(um.get("promptTokenCount") or 0),
                       token_ra=int(um.get("candidatesTokenCount") or 0),
                       dang_tin=co_so),
        tho=d,
    )


def goi(db, *, messages: list, thu_tu_provider: Sequence[str],
        category: Optional[str] = None, model: Optional[str] = None,
        model_theo_provider: Optional[dict] = None,
        tools: Optional[list] = None, max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
        timeout_s: float = 120.0) -> KetQuaChat:
    """Gọi model theo **thứ tự provider bên gọi khai**, bỏ qua provider đang bận.

    ⭐ `model_theo_provider` — vì **mỗi provider có id model riêng**. Model nhà tên
       `ltt_llm`, Gemini tên `gemini-2.5-flash`; gửi nhầm tên sang provider kia thì
       nó từ chối, và bên gọi sẽ tưởng provider đó "đang hỏng". Khai rõ:

           model_theo_provider={"ltt_llm": "ltt_llm", "gemini": "gemini-2.5-flash"}

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
            if pid in PROVIDER_GEMINI:
                kq = _goi_gemini(ten_model, credential, messages, max_tokens, timeout_s)
            elif pid in PROVIDER_OPENAI:
                than = {"model": ten_model, "messages": messages, "tools": tools,
                        "max_tokens": max_tokens, "temperature": temperature,
                        "reasoning_effort": reasoning_effort}
                if not base:
                    # Không có địa chỉ thì đừng gửi đi đâu cả và đừng đánh dấu lỗi
                    # cho khoá — đây là **thiếu cấu hình**, không phải provider hỏng.
                    ly_do.append(f"{pid}: thieu base_url (ca o khoa lan o registry)")
                    continue
                kq = _goi_openai(base, credential,
                                 {k: v for k, v in than.items() if v is not None},
                                 timeout_s)
            else:
                ly_do.append(f"{pid}: chua biet giao thuc cua provider nay")
                continue
        except BanError as e:
            # ⛔ KHÔNG `danh_dau_loi`. Bận không phải hỏng — xem đầu tệp.
            log.info("provider %s dang ban, di tiep: %s", pid, e)
            ly_do.append(f"{pid}: ban")
            continue
        except VuotNganSachError:
            # ⛔ KHÔNG cascade. Quá to ở đây thì quá to ở mọi nơi.
            raise
        except CongVlmError as e:
            api_pool.danh_dau_loi(db, key)
            ly_do.append(f"{pid}: loi ({e})")
            continue
        finally:
            credential = ""

        api_pool.danh_dau_thanh_cong(db, key, tokens=kq.su_dung.token_ra)
        return kq

    raise KhongCoProviderNao(ly_do)
