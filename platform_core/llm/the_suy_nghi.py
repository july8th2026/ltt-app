"""Thẻ suy nghĩ LỌT vào câu trả lời — tách về suy nghĩ, không cắt bừa (T1b).

🔴 HIỆN TƯỢNG (production 18/09, 1/8 lượt sau T1): `content` =
   ``"Hà Nội\\n</think>\\n\\nHà Nội"``. Budget suy nghĩ máy chủ đặt (L-26) cắt
   ngang dòng suy nghĩ; llama.cpp ÉP `</think>` (không kèm lời dặn), parser
   `--reasoning-format deepseek` chuyển sang `content`; model chưa nghĩ xong nên
   viết tiếp phần suy nghĩ dở rồi TỰ sinh `</think>` lần hai — lần này parser đã
   ở `content`, nên thẻ lọt nguyên văn.

   Nguồn (tra trước khi sửa):
     * ggml-org/llama.cpp#28182 — đúng triệu chứng: "leftover reasoning and a
       literal `</think>` emitted as content" khi `thinking_budget_tokens` cắt.
       Maintainer đóng "not planned": model cần `--reasoning-budget-message`
       (Qwen3 Technical Report §thinking budget, arXiv 2505.09388).
     * ggml-org/llama.cpp#27661 — parser chỉ tách ở `</think>` ĐẦU TIÊN; mọi
       `</think>` sau đó ra `content` nguyên văn.
     * `common/reasoning-budget.cpp` @91f6a6cf3: COUNTING → FORCING → DONE; ở DONE
       chỉ `<think>` mới làm nó bật lại — `</think>` thứ hai không ai bắt.

⭐ LUẬT (tất định, một hàm, không cờ):
   1. Chỉ xét `</think>` **đầu tiên nằm ngoài mã** (khối ``` / ~~~, span
      `inline`), **không bị trích dẫn** (sát bên là ` " ' < > / \\) và có
      **hình thẻ máy** — liền sau là xuống dòng hoặc hết văn bản (template Qwen
      sinh ``</think>\\n\\n``). Văn xuôi "thẻ </think> đóng" có chữ liền sau ⇒
      giữ. Lọc tham làm MẤT chữ của khách — LiteLLM#10702, vLLM#56658 — nên luật
      chọn bỏ sót một ca hiếm hơn là cắt nhầm.
   2. Phần TRƯỚC thẻ là suy nghĩ dở ⇒ nối vào `suy_nghi`; phần SAU là câu trả
      lời. Bỏ thẻ và khoảng trắng đầu phần sau.
   3. Phần sau RỖNG (thẻ ở đuôi) ⇒ chỉ bỏ thẻ, giữ phần trước làm câu trả lời —
      không bao giờ biến một câu trả lời có chữ thành rỗng. Phần trước rỗng
      (thẻ ở đầu) ⇒ cũng chỉ bỏ thẻ.
   4. `content` mở đầu bằng `<think>` (sau khoảng trắng) và có `</think>` hợp lệ
      ⇒ khối giữa là suy nghĩ (model mở lại khối). `<think>` ở chỗ khác: giữ.
   Không có thẻ nào khớp ⇒ trả NGUYÊN đối số — đường nóng một phép `in`.
"""
from __future__ import annotations

import re

THE_DONG = "</think>"
THE_MO = "<think>"

#: Khối mã rào (``` hoặc ~~~, ≥ 3 ký tự) — đóng bằng đúng chuỗi rào ấy, hoặc hết văn bản.
_RAO = re.compile(r"(^|\n)[ \t]*(`{3,}|~{3,})[^\n]*\n.*?(\n[ \t]*\2[ \t]*(?=\n|$)|$)",
                  re.S)
#: Span mã một dòng: `...` (không vượt dòng).
_SPAN = re.compile(r"(`+)[^`\n]*?\1")
#: Sát bên thẻ mà là ký tự này ⇒ thẻ đang được TRÍCH/nhắc tới, không phải thẻ máy.
_TRICH = set("`\"'«»“”‘’<>/\\")
#: Liền sau thẻ MÁY: template Qwen sinh `</think>\n\n` / `<think>\n`.
_SAU_THE_MAY = ("", "\n", "\r")


def _vung_ma(van_ban: str) -> list[tuple[int, int]]:
    vung = [(m.start(), m.end()) for m in _RAO.finditer(van_ban)]
    rao = list(vung)
    for m in _SPAN.finditer(van_ban):
        if not any(a <= m.start() < b for a, b in rao):
            vung.append((m.start(), m.end()))
    return vung


def _vi_tri_the(van_ban: str, the: str) -> int:
    """Vị trí `the` ĐẦU TIÊN có hình thẻ máy, ngoài mã, không bị trích; -1 nếu không."""
    if the not in van_ban:
        return -1
    vung = _vung_ma(van_ban)
    i = van_ban.find(the)
    while i >= 0:
        j = i + len(the)
        truoc = van_ban[i - 1] if i > 0 else ""
        sau = van_ban[j] if j < len(van_ban) else ""
        trong_ma = any(a <= i < b for a, b in vung)
        bi_trich = truoc in _TRICH or sau in _TRICH
        if not trong_ma and not bi_trich and sau in _SAU_THE_MAY:
            return i
        i = van_ban.find(the, j)
    return -1


def _noi(suy_nghi: str, them: str) -> str:
    them = them.strip("\r\n")
    if not them.strip():
        return suy_nghi
    if not suy_nghi:
        return them
    return suy_nghi.rstrip("\r\n") + "\n" + them


def tach_the_lot(noi_dung: str, suy_nghi: str) -> tuple[str, str]:
    """(noi_dung, suy_nghi) → (noi_dung sạch, suy_nghi đã nhận phần lọt). Luật ở đầu tệp."""
    if not noi_dung or "think>" not in noi_dung:
        return noi_dung, suy_nghi

    # Luật 4: model mở lại khối suy nghĩ ngay đầu câu trả lời.
    dau = len(noi_dung) - len(noi_dung.lstrip())
    if noi_dung.startswith(THE_MO, dau):
        sau_mo = noi_dung[dau + len(THE_MO):]
        if sau_mo[:1] in _SAU_THE_MAY:
            k = _vi_tri_the(sau_mo, THE_DONG)
            if k >= 0:
                con = sau_mo[k + len(THE_DONG):].lstrip()
                if con.strip():
                    return con, _noi(suy_nghi, sau_mo[:k])

    # Luật 1–3: `</think>` lạc giữa câu trả lời.
    k = _vi_tri_the(noi_dung, THE_DONG)
    if k < 0:
        return noi_dung, suy_nghi
    truoc, sau = noi_dung[:k], noi_dung[k + len(THE_DONG):]
    if not sau.strip():
        return truoc.rstrip(), suy_nghi          # luật 3: thẻ ở đuôi
    if not truoc.strip():
        return sau.lstrip(), suy_nghi            # thẻ ở đầu
    return sau.lstrip(), _noi(suy_nghi, truoc)   # luật 2
