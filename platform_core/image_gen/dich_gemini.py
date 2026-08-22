"""
dich_gemini.py — đường gọi LLM THẬT cho `prompt_dich`. (H37/A6)

⭐ `prompt_dich.dich_prompt_anh` nhận `goi_llm` **tiêm được** để test chạy không cần
   mạng. Tệp này là bản thật của cái đó: lấy key qua `api_pool`, gọi Gemini, trả về
   bản dịch — và **báo lại đúng loại lỗi** để `api_pool` xoay key cho đúng.

⛔ BÁO SAI LOẠI LỖI LÀ TỰ TẮT KEY. `api_pool.danh_dau_loi` phân nhánh theo
   `http_status`:

   | mã | `api_pool` làm gì |
   |---|---|
   | 401/403 | đếm lỗi xác thực → **`disable` sau 3 lần** |
   | 429 | cooldown theo `Retry-After` |
   | 4xx khác | **KHÔNG phạt** — đó là lỗi của ta, không phải của key |
   | 5xx / mạng | đếm lỗi → `error` sau ngưỡng |

   Nên phải truyền `http_status` THẬT. Gộp mọi thứ thành "lỗi" là một prompt sai
   cú pháp của ta cũng làm key bị phạt oan.

⭐ Dùng lại `api_pool` chứ KHÔNG dựng pool thứ hai — cùng bài học của Public API:
   "đừng dựng hàng đợi, sổ tiền hay pool thứ hai".

⚠️ `apps/taovideo/translate.py` làm việc tương tự nhưng nằm trong một app và tự lấy
   key riêng. Tệp này là bản dùng chung ở `platform_core`. Chưa gộp hai bên vì
   taovideo đang chạy thật — ghi ra để không quên (D-028).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

#: Model dịch. Rẻ, nhanh, và đã có trong registry ở category `chat`.
MODEL_DICH = "gemini-2.5-flash"

#: Thử tối đa mấy key trước khi bỏ cuộc. `api_pool` tự xoay sang key khác sau khi
#: key hỏng bị đánh dấu, nên hai lượt là đủ để vượt qua một key vừa hết quota.
SO_KEY_THU = 2

_BASE = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT_S = 30.0


class GoiLLMThatBai(Exception):
    """Không gọi được LLM. `prompt_dich` sẽ bọc lại thành `DichThatBai`."""


def _than_yeu_cau(text: str, he_thong: str) -> dict:
    return {
        "contents": [{"parts": [{"text": text}]}],
        "systemInstruction": {"parts": [{"text": he_thong}]},
    }


def _doc_ban_dich(than: dict) -> str:
    for ung in (than.get("candidates") or []):
        for phan in ((ung.get("content") or {}).get("parts") or []):
            if phan.get("text"):
                return str(phan["text"]).strip()
    return ""


def _dem_token(than: dict) -> int:
    """Tổng token của lượt gọi, để `api_pool` ghi telemetry tpm (H8 Pha 2)."""
    try:
        return int((than.get("usageMetadata") or {}).get("totalTokenCount") or 0)
    except (TypeError, ValueError):
        return 0


def goi_gemini(text: str, he_thong: str, *, db, model: str = MODEL_DICH,
               http: Optional[Callable] = None, timeout_s: float = TIMEOUT_S) -> str:
    """Gọi Gemini để dịch. Trả bản dịch; ném `GoiLLMThatBai` nếu không được.

    `http(method, url, *, headers, json, timeout) -> (status, body_dict)` tiêm được
    để test không cần mạng.
    """
    from platform_core import api_keys, api_pool
    from platform_core.models import APIKEY_CAT_CHAT

    goi = http or _http_that
    loi_cuoi = ""
    for _ in range(max(1, SO_KEY_THU)):
        try:
            key = api_pool.lay_key(db, "gemini", category=APIKEY_CAT_CHAT, model=model)
        except Exception as e:                                    # noqa: BLE001
            raise GoiLLMThatBai(f"khong co key gemini kha dung: {e}") from e

        cred = api_keys.lay_credential(db, key)
        try:
            ma, than = goi("POST", f"{_BASE}/models/{model}:generateContent",
                           headers={"x-goog-api-key": cred,
                                    "Content-Type": "application/json"},
                           json=_than_yeu_cau(text, he_thong), timeout=timeout_s)
        except Exception as e:                                    # noqa: BLE001
            # Lỗi mạng: KHÔNG có http_status ⇒ `api_pool` tính là 5xx/mạng. Đúng.
            api_pool.danh_dau_loi(db, key, message=f"{type(e).__name__}: {e}")
            loi_cuoi = f"{type(e).__name__}: {e}"
            continue

        if ma == 200:
            ban_dich = _doc_ban_dich(than or {})
            if ban_dich:
                api_pool.danh_dau_thanh_cong(db, key, tokens=_dem_token(than or {}))
                return ban_dich
            # 200 mà rỗng: KHÔNG phải lỗi của key (thường do bộ lọc an toàn chặn).
            # Đánh dấu lỗi ở đây là phạt oan.
            raise GoiLLMThatBai(_t("Gemini trả lời rỗng — có thể prompt bị bộ lọc "
                                   "an toàn chặn."))

        retry_after = None
        if isinstance(than, dict):
            retry_after = (than.get("error") or {}).get("retryAfter")
        api_pool.danh_dau_loi(db, key, http_status=ma, retry_after_s=retry_after,
                              message=str(than)[:300])
        loi_cuoi = f"HTTP {ma}"
        # ⛔ 4xx CỦA TA thì thử key khác cũng vô ích — hỏng ngay, đừng đốt key thứ hai.
        if 400 <= ma < 500 and ma not in (401, 403, 429):
            raise GoiLLMThatBai(f"HTTP {ma}: {str(than)[:200]}")

    raise GoiLLMThatBai(loi_cuoi or "khong goi duoc Gemini")


def tao_ham_dich(db, *, model: str = MODEL_DICH,
                 http: Optional[Callable] = None) -> Callable[[str, str], str]:
    """Trả một hàm đúng khuôn `goi_llm(text, he_thong)` cho `dich_prompt_anh`."""
    def _goi(text: str, he_thong: str) -> str:
        return goi_gemini(text, he_thong, db=db, model=model, http=http)
    return _goi


def _http_that(method: str, url: str, *, headers: dict, json: Any, timeout: float):
    import httpx
    r = httpx.request(method, url, headers=headers, json=json, timeout=timeout)
    try:
        than = r.json()
    except ValueError:
        than = {"_raw": r.text[:500]}
    return r.status_code, than
