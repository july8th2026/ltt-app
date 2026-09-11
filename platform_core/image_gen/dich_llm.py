"""dich_llm.py — dịch prompt ảnh qua **LTT_LLM**. Thay `dich_gemini.py`.

🔴 AI CLEAN REBUILD V2 pha 06.1. Cùng giao diện với module cũ
(`goi_llm(text, he_thong) -> str` và `tao_ham_dich(db)`), nên
`prompt_dich.dich_prompt_anh` và `image_gen.dieu_phoi` **không phải đổi một
dòng nào** — chỉ nơi *chọn* hàm dịch đổi.

⭐ Vì sao `anhnoibo` là ca rẻ nhất của pha 06: nó **đã** vẽ trên LTT_IMAGE
   (`cong_render` + `LTT_RENDER_BASE_URL`). Gemini chỉ còn làm **một** việc ở đó
   — dịch prompt sang tiếng Anh trước khi vẽ. Nên di trú nó là đổi một hàm, chứ
   không phải đổi một động cơ.

✅ Module cũ `dich_gemini.py` **đã bị xoá ở pha 07** (09/09/2026), đúng như
   dòng này hứa ở pha 06. Tách hai việc ra để một lượt hoàn tác chỉ phải lùi
   một trong hai — và cả hai đều đã đi trọn.
"""
from __future__ import annotations

import uuid as _uuid
from typing import Callable

from platform_core.i18n import _ as _t
from platform_core.llm import canonical as _C



class GoiLLMThatBai(Exception):
    """Không gọi được LLM. `prompt_dich` sẽ bọc lại thành `DichThatBai`.

    🔴 Lớp này **về nhà** ở pha 07: pha 06 còn nhập lại nó từ `dich_gemini` để
       không đổi hai thứ cùng lúc, nay module ấy đã xoá.

    ⛔ Đừng đổi tên: `prompt_dich` bắt **đúng lớp này**, và một nhánh `except`
       không còn bắt được gì là một nhánh hỏng **im lặng**.
    """


TIMEOUT_S = 30.0
MAX_TOKENS = 1024


def goi_llm(text: str, he_thong: str, *, db,
            timeout_s: float = TIMEOUT_S) -> str:
    """Dịch `text` theo chỉ dẫn `he_thong`. Ném `GoiLLMThatBai` khi không được.

    🔴 Giành **suất admission** trước khi chạm máy B — máy B chỉ có một suất
       đồng thời, và một đường quên bước này làm chính cơ chế đếm suất sai.
    """
    from platform_core.llm import admission, dieu_phoi
    from platform_core.models import APIKEY_CAT_CHAT

    suc = _C.tai_nguyen_nha(_C.MODEL_MAC_DINH)
    ve = None
    try:
        ve = admission.acquire(
            db, resource=suc.resource, slots=suc.slots, user_id="he-thong:image_gen",
            mode="sync", holder_id="dich-anh:" + _uuid.uuid4().hex[:12])
        if ve is None:
            raise GoiLLMThatBai(_t("Model đang bận, thử lại sau ít phút."))
        try:
            kq = dieu_phoi.goi(
                db,
                messages=[{"role": "system", "content": he_thong},
                          {"role": "user", "content": text}],
                category=APIKEY_CAT_CHAT,
                thu_tu_provider=_C.THU_TU_PROVIDER,
                model_theo_provider=_C.ban_do_model(),
                max_tokens=MAX_TOKENS,
                timeout_s=timeout_s,
            )
        except dieu_phoi.KhongCoProviderNao as e:
            raise GoiLLMThatBai(str(e)) from None
    finally:
        if ve is not None:
            admission.release_by_id(ve.id)

    van = (kq.noi_dung or "").strip()
    if not van:
        # ⛔ Rỗng KHÔNG được trả lặng lẽ: `dich_prompt_anh` sẽ gửi một prompt
        #    rỗng đi vẽ, và khách nhận về một tấm ảnh không liên quan gì tới
        #    thứ họ gõ — một lỗi đắt mà không có dấu vết nào.
        raise GoiLLMThatBai(_t("Model trả lời rỗng — thử lại hoặc đổi mô tả."))
    return van


def tao_ham_dich(db) -> Callable[[str, str], str]:
    """Trả một hàm đúng khuôn `goi_llm(text, he_thong)` cho `dich_prompt_anh`."""
    def _goi(text: str, he_thong: str) -> str:
        return goi_llm(text, he_thong, db=db)
    return _goi
