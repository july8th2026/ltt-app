"""Adapter văn bản của PROMPT AI OMMI — chạy trên **LTT_LLM** (model nhà).

🔴 DI TRÚ 08/09/2026 — AI CLEAN REBUILD V2 pha 05.5. Bản cũ vi phạm **bốn**
   điều pha 05 cấm:

       BASE_URL = "https://generativelanguage.googleapis.com"  # HTTP THANG
       lease()   -> api_pool.lay_key(db, "gemini", ...)        # api_pool tang APP
       report()  -> api_pool.danh_dau_thanh_cong/loi           # telemetry tang APP
       os.environ.get("GEMINI_API_KEY")                        # fallback env

   Cả bốn biến mất. `platform_core.llm.dieu_phoi` đã làm **cả bốn** việc đó:
   cấp khoá, gọi, đánh dấu thành công/lỗi lên khoá, và phân biệt *bận* với
   *hỏng*. Giữ lại `lease`/`report` ở đây là bản sao thứ hai của cùng quyết
   định — và hai bản sẽ trôi khỏi nhau.

## ⚠️ MỘT BẢO ĐẢM BỊ HẠ CẤP — nói ra, không giấu

Bản cũ đặt `responseMimeType: "application/json"`, tức Gemini **bảo đảm ở tầng
giao thức** rằng đầu ra là JSON. Cổng nhà thì:

    git grep -n "response_format" hoac "json_object" tren *.py   ->  KHONG mot cho nao
    apps/ltt_llm/manifest.py  khai: messages · tools · max_output_tokens ·
                                    reasoning_effort   (khong co response_format)

⇒ Nền tảng **chưa bao giờ** dùng JSON mode với model nhà, và không có gì cho
  biết cổng đỡ nó. Đoán một tham số rồi gửi đi là cách nhận về `400` ở
  production, nên ở đây **không đoán**.

⇒ Bảo đảm chuyển từ **tầng giao thức** xuống **tầng lời nhắc** + phân tích
  phòng thủ (bóc rào ```, `json.loads`, lỗi có tên khi hỏng). Đó là một sự hạ
  cấp **thật**, đo được, và nó thuộc về báo cáo pha 05 chứ không thuộc về một
  dòng chú thích im lặng.

⏭️ Mở lại JSON mode là việc riêng: đo cổng nhà có đỡ `response_format` không,
   rồi mới nối `them=` qua `dieu_phoi`.
"""
from __future__ import annotations

import json
import logging
import uuid as _uuid

from platform_core.i18n import _ as _t
from platform_core.llm import canonical as C

log = logging.getLogger(__name__)

#: Bí danh công khai, không phải id nội bộ. `jobs.py` đọc tên này.
DEFAULT_MODEL = C.MODEL_MAC_DINH

_MAX_TOKENS = 8192
_TIMEOUT_S = 115.0


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _bi_danh(model: str) -> str:
    """Chuẩn hoá tên model đến từ dữ liệu cũ về một bí danh hợp lệ.

    ⚠️ **Đây KHÔNG phải một provider fallback** — thứ mà chiến dịch cấm. Nó
    không chọn *nhà cung cấp khác*; nó chuẩn hoá một **tên model đã chết** trong
    một hàng `AppProject` cũ về động cơ duy nhất còn tồn tại.

    ⭐ Vì sao không ném: các hàng cũ có thể còn ghi `"gemini-2.5-flash"`, và một
       lỗi cứng ở đây làm hỏng dự án cũ của khách để đổi lấy đúng không gì cả.
    ⭐ Vì sao **ghi log**: một lần thay tên im lặng là một lần không ai biết dữ
       liệu cũ còn sót tới bao giờ.
    """
    ten = (model or "").strip()
    if ten in C.MODEL_HOP_LE:
        return ten
    if ten:
        log.info("PROMPT AI OMMI: ten model cu %r -> %r", ten, C.MODEL_MAC_DINH)
    return C.MODEL_MAC_DINH


def generate_json(system: str, prompt: str, *,
                  model: str = DEFAULT_MODEL) -> tuple[dict, int]:
    """Sinh một object JSON. Trả `(dict, số token)`; ném `ProviderError` khi hỏng.

    🔴 Giành **suất admission** trước khi chạm máy B — máy B chỉ có một suất
       đồng thời, và một đường quên bước này làm chính cơ chế đếm suất sai.
    """
    from platform_core.db import get_session
    from platform_core.llm import admission, dieu_phoi
    from platform_core.models import APIKEY_CAT_CHAT

    alias = _bi_danh(model)
    tai_nguyen, suat = C.tai_nguyen_nha()
    gen = get_session()
    db = next(gen)
    ve = None
    try:
        ve = admission.acquire(
            db, resource=tai_nguyen, slots=suat, user_id="he-thong:prompt_ai_ommi",
            mode="sync", holder_id="ommi:" + _uuid.uuid4().hex[:12])
        if ve is None:
            raise ProviderError(_t('Model đang bận, thử lại sau ít phút.'))
        try:
            kq = dieu_phoi.goi(
                db,
                messages=[
                    {"role": "system", "content": system
                     + "\n\nReturn ONLY one JSON object. No markdown fence, "
                       "no commentary before or after."},
                    {"role": "user", "content": prompt},
                ],
                category=APIKEY_CAT_CHAT,
                thu_tu_provider=C.THU_TU_PROVIDER,
                model_theo_provider=C.ban_do_model(alias),
                max_tokens=_MAX_TOKENS,
                temperature=0.45,
                timeout_s=_TIMEOUT_S,
            )
        except dieu_phoi.KhongCoProviderNao:
            # ⛔ Mọi provider bận / không cấp được khoá. `dieu_phoi` đã lo việc
            #    đánh dấu lỗi cho đúng trường hợp — KHÔNG đánh dấu lại ở đây.
            raise ProviderError(_t('Dịch vụ AI đang bận, thử lại sau.')) from None
        db.commit()
    finally:
        if ve is not None:
            admission.release_by_id(ve.id)
        try:
            next(gen)
        except StopIteration:
            pass

    van = (kq.noi_dung or "").strip()
    if not van:
        raise ProviderError(_t('Dịch vụ AI không trả dữ liệu.'))

    # Bóc rào ``` mà nhiều model vẫn thêm dù đã dặn. Giữ nguyên từ bản cũ: đây
    # là lớp phòng thủ, và nay nó **quan trọng hơn trước** vì không còn bảo đảm
    # JSON ở tầng giao thức (xem docstring module).
    if van.startswith("```"):
        van = van.split("\n", 1)[-1].rsplit("```", 1)[0]
    van = van.strip().removeprefix("json").strip()

    try:
        ket_qua = json.loads(van)
    except json.JSONDecodeError:
        raise ProviderError(
            _t('Dịch vụ AI trả cấu trúc không hợp lệ; hãy thử lại.')) from None
    if not isinstance(ket_qua, dict):
        raise ProviderError(_t('Dịch vụ AI trả sai loại dữ liệu.'))

    su_dung = getattr(kq, "su_dung", None)
    token = int(getattr(su_dung, "token_vao", 0) or 0) + \
        int(getattr(su_dung, "token_ra", 0) or 0)
    return ket_qua, token
