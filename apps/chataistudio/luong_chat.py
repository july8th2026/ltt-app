"""luong_chat.py — một lượt chat của CHAT AI STUDIO trên **LTT_LLM**.

🔴 AI CLEAN REBUILD V2 pha 05.7. Thay đường cũ: sidecar `LTTStudioCodex`
   (đăng nhập ChatGPT) → `platform_core.runtime_noi_bo.luong.mo_luong`.

## Ba thứ biến mất, và cả ba đều là thứ pha 05 cấm

    sidecar loopback -> Codex -> ChatGPT       execution ngoai
    cost.reserve/settle_credit + _hold_more    VONG DOI CREDIT THU HAI
    codex_thread_id giu ngu canh o may chu     phu thuoc mot dich vu ngoai

`mo_luong` đã làm **cả ba**: giành suất → ước token → giữ chỗ → commit → mở
luồng → đếm → quyết toán trong `finally`. Giữ thêm một vòng đời credit ở đây là
**thu tiền hai lần** hoặc **hoàn nhầm** — hai lỗi sổ sách không đảo được.

## ⚠️ NGỮ CẢNH nay do TA dựng, không do máy chủ họ giữ

Sidecar giữ hội thoại phía nó (`codex_thread_id`); LTT_LLM thì không. Nên mỗi
lượt phải gửi lại lịch sử. Đó là một **khác biệt hành vi thật**, không phải chi
tiết cài đặt:

- lịch sử dài ⇒ tốn token đầu vào ⇒ **tốn credit** hơn trước;
- và nó có trần: quá cửa sổ ngữ cảnh thì `chuan_bi` ném `ThamSoSai`.

⇒ Cắt theo **ngân sách ký tự**, giữ các lượt **gần nhất** (phần liên quan nhất),
  và luôn giữ tin cuối của người dùng. Cắt ở đây là cắt **có luật đọc được**,
  hơn là để nền tảng ném một lỗi mà khách không hiểu.

## ⛔ Chữ lỗi ra trình duyệt đi qua `loi_ra_ngoai`, KHÔNG qua `str(e)`

Đo 07/09 trên đường đang phục vụ khách: `str(e)` từng mang nguyên thân lỗi
thượng nguồn ra ngoài — đường dẫn `.gguf`, id model nội bộ, `base_url`, IP nội
bộ. Ở đây mọi câu cho khách dựng từ **mã lỗi** (tập đóng do ta viết).
"""
from __future__ import annotations

import logging
from typing import Iterator

from platform_core.llm import loi_ra_ngoai as LRN
from platform_core.llm.canonical import MODEL_MAC_DINH

log = logging.getLogger(__name__)

#: Tên ToolSpec của cửa chat nội bộ. Giống `chatltt` — một đường, một bảng giá.
TOOL_CHAT = "text.chat"

#: Ngân sách ký tự cho lịch sử gửi kèm. Chọn **ký tự** chứ không token vì ở đây
#: ta chỉ cần một cái trần thô, và đếm token thật cần nạp tokenizer của model.
#: `ngan_sach.TOKEN_VAO_TRAN` là 169.984 token; 120.000 ký tự nằm an toàn dưới
#: đó với mọi tỉ lệ ký tự/token thực tế của tiếng Việt lẫn tiếng Anh.
NGAN_SACH_KY_TU = 120_000

#: Trần cho một tin đơn lẻ, để một tin khổng lồ không nuốt cả ngân sách.
TRAN_MOT_TIN = 20_000


def dung_messages(lich_su, tin_moi: str) -> list[dict]:
    """Dựng `messages` từ lịch sử hội thoại + tin mới.

    ⭐ Duyệt **ngược từ mới tới cũ** rồi đảo lại: khi phải cắt, thứ bị bỏ là
       phần **xa nhất**, không phải phần vừa nói. Cắt từ đầu danh sách sẽ bỏ mất
       chính câu người dùng vừa gõ.
    """
    ra: list[dict] = [{"role": "user", "content": (tin_moi or "")[:TRAN_MOT_TIN]}]
    con = NGAN_SACH_KY_TU - len(ra[0]["content"])
    for m in reversed(list(lich_su or ())):
        noi_dung = (getattr(m, "content", "") or "").strip()
        if not noi_dung:
            # Tin chỉ có ảnh: LTT_LLM text không đọc được, và một dòng rỗng chỉ
            # tốn chỗ. Bỏ qua — nhưng KHÔNG im lặng với người đọc mã.
            continue
        vai = "assistant" if getattr(m, "role", "") == "assistant" else "user"
        noi_dung = noi_dung[:TRAN_MOT_TIN]
        if len(noi_dung) > con:
            break
        con -= len(noi_dung)
        ra.insert(0, {"role": vai, "content": noi_dung})
    return ra


def chay(db, *, user_id: str, conv_id: str, messages: list[dict],
         holder_id: str) -> Iterator[dict]:
    """Chạy một lượt và sinh **sự kiện SSE** đúng hợp đồng cũ của giao diện.

    Hợp đồng ấy (`chataistudio.html`) là: `delta` · `warning` · `error` · `done`.
    Giữ nguyên nó là có chủ đích — giao diện không phải sửa, và một lượt hoàn
    tác chỉ phải lùi phía máy chủ.

    ⛔ `image` **không còn**: LTT_LLM là model văn bản. Đó là một tính năng bị
       gỡ, đã ghi trong `MIGRATION_MAP.md`, không phải một thiếu sót.
    """
    from platform_core.runtime_noi_bo import luong as L

    ghi_nhan: dict = {}
    tra_loi = ""
    token_vao = token_ra = 0
    credit_thu = 0

    it = L.mo_luong(db, user_id=user_id, tool_name=TOOL_CHAT,
                    params={"model": MODEL_MAC_DINH, "messages": messages},
                    correlation_id=conv_id, holder_id=holder_id,
                    ghi_nhan=ghi_nhan)
    try:
        for sk in it:
            loai = sk.get("type")
            if loai == "response.delta":
                chu = sk.get("text") or ""
                if chu:
                    tra_loi += chu
                    yield {"type": "delta", "text": chu}
            elif loai == "usage.updated":
                token_vao = int(sk.get("token_vao") or token_vao)
                token_ra = int(sk.get("token_ra") or token_ra)
            elif loai == "billing.updated":
                credit_thu = int(sk.get("credit_thu") or credit_thu)
            elif loai == "response.failed":
                # ⛔ Câu cho khách dựng từ MÃ, không từ `sk["ly_do"]` — thượng
                #    nguồn viết ra chuỗi ấy, và nó đã từng mang IP nội bộ.
                yield {"type": "error", "message": LRN.cau(str(sk.get("code") or ""))}
                return
    except L.LoiCuaLuong as e:
        ma = getattr(e, "ma", "") or _ma_tu_lop(e)
        log.warning("chataistudio_luot_hong conv=%s loai=%s",
                    conv_id[:8], LRN.hinh_dang(e))
        yield {"type": "error", "message": LRN.cau(ma)}
        return
    finally:
        # `mo_luong` quyết toán trong `finally` của chính nó; khi bên tiêu thụ
        # đóng generator, sự kiện `billing.updated` cuối được ghi vào `ghi_nhan`.
        if not credit_thu and ghi_nhan.get("billing"):
            credit_thu = int(ghi_nhan["billing"].get("credit_thu") or 0)

    yield {"type": "done", "text": tra_loi, "credit_cost": credit_thu,
           "tokens_total": token_vao + token_ra}


def _ma_tu_lop(e: BaseException) -> str:
    """Ngoại lệ → mã lỗi của tập đóng. Không khớp thì trả rỗng (⇒ câu chung)."""
    from platform_core.runtime_noi_bo import luong as L

    if isinstance(e, L.DangBan):
        return "ban"
    if isinstance(e, L.ThieuCredit):
        return "het_credit"
    if isinstance(e, L.ThamSoSai):
        return "tham_so"
    if isinstance(e, L.KhongMoDuoc):
        return "khong_mo_duoc"
    return ""


__all__ = ["TOOL_CHAT", "NGAN_SACH_KY_TU", "dung_messages", "chay"]
