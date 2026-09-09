"""
translate.py — dịch prompt video qua **LTT_LLM** (model nhà). Giữ tag @IMG_n +
thông số kỹ thuật; chỉ trả bản dịch.

🔴 DI TRÚ 08/09/2026 — AI CLEAN REBUILD V2 pha 05.4. Bản cũ vi phạm **ba** điều
   pha 05 cấm, và tệp này là ca mẫu của cả ba:

       _BASE = "https://generativelanguage.googleapis.com"   # HTTP THANG
       api_pool.lay_key(db, "gemini", ...)                   # api_pool o tang APP
       os.environ.get("GEMINI_API_KEY")                      # fallback bien moi truong

   Nay đi qua `platform_core.llm.dieu_phoi` — app không còn biết provider nào
   tồn tại, không dựng HTTP, không cấp khoá, không đọc biến môi trường.

⭐ Vì sao `dieu_phoi` chứ không gọi thẳng cổng LTT: `dieu_phoi` gom việc dịch
   giao thức, cấp khoá và xử lý *dispatch mơ hồ* về một chỗ. Gọi thẳng là dựng
   lại bản sao thứ hai của cùng những quyết định ấy — đúng thứ tệp này vừa thoát.
"""
from __future__ import annotations

import uuid as _uuid

from platform_core.i18n import _ as _t

_LANG = {"en": "English", "zh": "Chinese (Simplified)", "vi": "Vietnamese"}

#: Trần token ra. Dịch một prompt video: đầu vào cắt ở 10.000 ký tự (route),
#: nên bản dịch không thể dài hơn nhiều.
_MAX_TOKENS = 2048
_TIMEOUT_S = 60.0


def _he_thong(lang: str) -> str:
    return (f"Translate the following AI video prompt to {lang}. Return ONLY "
            f"the translation — no quotes, no notes. Keep unchanged: technical "
            f"specs (fps, aspect ratio, resolution) and any @IMG_n/@VID_n/@AUD_n "
            f"tags.")


def dich(prompt: str, target: str = "en") -> str:
    """Dịch `prompt` sang `target`. Ném khi không dịch được.

    🔴 **GIÀNH SUẤT ADMISSION TRƯỚC KHI CHẠM MÁY B.**

       Máy B chỉ có **một** suất đồng thời (`DONG_THOI_MAY_B=1`). Một đường mới
       tới nó mà quên `admission` không chỉ chen hàng — nó làm chính cơ chế đếm
       suất **sai**, nên hai đường khác cũng hỏng theo.

       ⚠️ Lỗ đó đã có thật: tới 01/09 `agent/planner.py` là đường **duy nhất**
       tới máy B không giành suất. Di trú một app mà quên bước này là dựng lại
       đúng lỗ ấy, ở một tệp khác, và lần này sẽ khó tìm hơn vì nó **mới**.

    ⭐ Không giành được suất thì **hỏng ngay, không xếp hàng**. Đây là một tiện
       ích dịch không tính tiền; để nó chờ một suất là để nó chen chỗ một
       request khách đang trả tiền.
    """
    from platform_core.db import get_session
    from platform_core.llm import admission, canonical as C, dieu_phoi
    from platform_core.models import APIKEY_CAT_CHAT

    van_vao = (prompt or "").strip()
    if not van_vao:
        raise ValueError(_t('Chưa có nội dung để dịch.'))

    tai_nguyen, suat = C.tai_nguyen_nha()
    gen = get_session()
    db = next(gen)
    ve = None
    try:
        ve = admission.acquire(
            db, resource=tai_nguyen, slots=suat, user_id="he-thong:taovideo",
            mode="sync", holder_id="taovideo-dich:" + _uuid.uuid4().hex[:12])
        if ve is None:
            raise RuntimeError(_t('Model đang bận, thử lại sau ít phút.'))

        kq = dieu_phoi.goi(
            db,
            messages=[{"role": "system", "content": _he_thong(
                _LANG.get(target, "English"))},
                {"role": "user", "content": van_vao}],
            category=APIKEY_CAT_CHAT,
            thu_tu_provider=C.THU_TU_PROVIDER,
            model_theo_provider=C.ban_do_model(),
            max_tokens=_MAX_TOKENS,
            timeout_s=_TIMEOUT_S,
        )
        db.commit()
    finally:
        # Nhả suất dù đi đường nào — giữ một suất không dùng đúng bằng chiếm nó.
        if ve is not None:
            admission.release_by_id(ve.id)
        try:
            next(gen)
        except StopIteration:
            pass

    van = (kq.noi_dung or "").strip()
    if not van:
        # ⛔ Rỗng KHÔNG được trả về lặng lẽ: bên gọi sẽ ghi đè ô nhập của khách
        #    bằng một chuỗi rỗng và mất bản gốc họ vừa gõ.
        raise RuntimeError(_t('Model không trả bản dịch.'))
    return van
