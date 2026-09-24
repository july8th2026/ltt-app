"""Khoá khử trùng — MỘT nơi sinh, cho waitpoint và cho trigger (spec §5.7, §8.1).

🔴 VÌ SAO MỘT TỆP RIÊNG, VÀ VÌ SAO ĐỌC TRƯỚC KHI THÊM KHOÁ MỚI

Phase gốc 4 đã dính **ba** lần cùng một lỗi ở **ba** bảng — `wakeup`,
`node_run`, `dedupe_key` — đều khoá theo `node_id` **trần**. Hậu quả giống hệt
nhau mỗi lần: hai vòng của một `foreach` sinh **cùng một khoá**, vòng 2 va vào
vòng 1, và run treo hoặc chạy thiếu **trong im lặng**.

⇒ Luật của phase này: **mọi khoá mới phải trả lời được câu "hai vòng foreach có
  đụng nhau không" TRƯỚC khi được viết.** Tệp này là chỗ câu trả lời được viết
  ra một lần, thay vì mỗi nơi tự nghĩ lại.

## Câu trả lời cho từng khoá ở đây

| Khoá | Hai vòng `foreach` có đụng nhau? |
|---|---|
| `khoa_cho` (waitpoint của một NODE) | **Không** — khoá mang `duong_thi_hanh`, tức `f1:0/delay1` ≠ `f1:1/delay1` |
| `khoa_webhook` · `khoa_cron` · `khoa_event` · `khoa_poll` | **Không liên quan** — chúng khử trùng *một lần bắn của một trigger*, tạo ra **run**; không có node và không có vòng lặp nào ở cửa đó |

⛔ `khoa_cho` KHÔNG tự dựng chuỗi đường: nó gọi `danh_thuc.duong_thi_hanh` —
   đúng hàm mà `wakeup` (`hen_node`) và `node_run` (`thi_hanh.khoa_node`) đã
   dùng. Một bộ sinh khoá thứ hai là một chỗ để hai bảng trôi khỏi nhau.

⭐ NGUỒN (tra trước, không suy): activepieces
   `brain/knowledge/decisions/000015-fan-in-is-an-event-driven-waitpoint-barrier.md`
   (activepieces@`17e2ac0b`) — *"Identity is path-keyed… a delay or approval
   inside a loop used to reuse one waitpoint row across every iteration, so
   iteration 2 found iteration 1's COMPLETED row … and skipped its pause
   entirely."* Cùng họ với issue công khai `activepieces#3798`
   (*"Create Approval Link ⇒ Wait for Approval doesn't work when there's a step
   in between"*) và `activepieces#14388` (*"Support multiple pauses within a
   single step run"*).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Sequence

from platform_core.workflow import danh_thuc

#: Bề rộng THẬT của `waitpoint.idempotency_key` và `workflow_run.idempotency_key`
#: (`models.py`, cả hai `String(120)`). Không phải một con số tự chọn:
#: PostgreSQL ném `StringDataRightTruncation` ở ký tự thứ 121, còn SQLite nuốt
#: im lặng — nên một khoá quá dài chỉ lộ ra trên production.
TRAN_KHOA = 120

#: Ký tự `#` không nằm trong tập id hợp lệ (`bien_dich._ID`) ⇒ một khoá đã băm
#: không bao giờ đụng một khoá đường-thật. Cùng quy ước với `danh_thuc`.
_TIEN_TO_BAM = "#"


def _gon(khoa: str) -> str:
    """Vượt trần cột ⇒ **BĂM**, ⛔ không CẮT CỤT.

    Cắt cụt là cách im lặng nhất để hai khoá khác nhau thành một — đúng lỗi mà
    cả tệp này tồn tại để chặn, chỉ đổi nguyên nhân.
    """
    if len(khoa) <= TRAN_KHOA:
        return khoa
    return _TIEN_TO_BAM + hashlib.sha256(khoa.encode("utf-8")).hexdigest()


def khoa_cho(run_id: str, node_id: str, kind: str, *,
             vong: Sequence[tuple[str, int]] = ()) -> str:
    """Khoá của MỘT điểm chờ do MỘT lần node chạy mở ra.

    ⭐ Nó phải **lặp lại được**: cùng run + cùng đường thi hành + cùng loại ⇒
       cùng chuỗi. Đó là điều kiện để `core.delay`/`core.wait`/`core.human`
       luỹ đẳng — động cơ gọi lại bộ thi hành của chúng nhiều lượt, và lượt thứ
       hai phải **tìm lại** waitpoint cũ chứ không mở một cái mới.

    ⛔ Và nó phải **tách được**: `f1:0/delay1` ≠ `f1:1/delay1`, nếu không thì
       vòng 2 tìm thấy waitpoint ĐÃ MỞ của vòng 1 và bỏ qua lần chờ của chính
       nó (activepieces `000015`).
    """
    duong = danh_thuc.duong_thi_hanh(str(node_id), vong=tuple(vong))
    return _gon(f"wp:{run_id}:{duong}:{str(kind).upper()}")


# ── Khoá khử trùng của TRIGGER (spec §8.1) ───────────────────────────────────
#
# Bảng spec §8.1, chép nguyên:
#
#   manual  -> ui:<request_id>
#   api     -> header Idempotency-Key
#   webhook -> Idempotency-Key, hoặc sha256(thân) + PHÚT
#   cron    -> cron:<trigger_id>:<thời điểm LỊCH ISO>
#   event   -> evt:<trigger_id>:<workflow_event.id>
#   poll    -> poll:<trigger_id>:<id bản ghi từ piece>


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def khoa_webhook(trigger_id: str, *, idempotency_key: str = "",
                 than: bytes = b"", luc: datetime | None = None) -> str:
    """Khoá của một cú POST vào `/hooks/wf/{trigger_id}`.

    ⭐ Hai đường, theo đúng thứ tự spec:

      1. Người gọi gửi `Idempotency-Key` ⇒ **tin họ**. Thân và thời điểm không
         được đếm: cùng một khoá nghĩa là *"vẫn là việc đó"*, kể cả khi họ gửi
         lại với một thân đã sửa.
      2. Không có ⇒ `sha256(thân)` **cộng PHÚT**. Phút là thứ khiến một cú gửi
         lại **sau đó** (một việc mới, cùng nội dung) không bị nuốt mất: khử
         trùng vĩnh viễn theo thân là một cách im lặng để mất việc thật.
    """
    if idempotency_key:
        return _gon(f"wh:{trigger_id}:k:{idempotency_key}")
    bam = hashlib.sha256(than or b"").hexdigest()[:32]
    phut = (luc or _bay_gio()).strftime("%Y%m%dT%H%M")
    return _gon(f"wh:{trigger_id}:b:{bam}:{phut}")


def khoa_cron(trigger_id: str, moc: datetime) -> str:
    """Khoá của một mốc lịch — ⛔ **mốc**, không phải lúc bắn.

    ⭐ n8n `#17187` (*"Scheduled tasks executing multiple times at once"*) và
       `#34628`/`#23906` (*"Missed schedule trigger can cause unexpectedly long
       delays"*) là hai mặt của cùng một đồng xu: nếu khoá mang thời điểm BẮN
       thì một mốc bị bắn bù (hoặc bắn bởi hai tiến trình) thành hai run. Khoá
       mang MỐC thì bắn mấy lần cũng đúng một run.
    """
    return _gon(f"cron:{trigger_id}:{_iso(moc)}")


def khoa_event(trigger_id: str, event_id: str) -> str:
    return _gon(f"evt:{trigger_id}:{event_id}")


def khoa_poll(trigger_id: str, ban_ghi_id: str) -> str:
    return _gon(f"poll:{trigger_id}:{ban_ghi_id}")


def khoa_ui(request_id: str) -> str:
    return _gon(f"ui:{request_id}")


def _iso(luc: datetime) -> str:
    """ISO không có micro-giây và không có `+00:00` — một mốc lịch, một chuỗi.

    ⚠️ Chuẩn hoá ở đây chứ không ở bên gọi: hai bên gọi khác nhau (bộ quét cron
       và một lần bắn tay) phải ra **cùng** chuỗi cho **cùng** mốc, nếu không
       khoá khử trùng không khử được gì.
    """
    return luc.replace(microsecond=0, tzinfo=None).isoformat()


__all__ = ["TRAN_KHOA", "khoa_cho", "khoa_cron", "khoa_event", "khoa_poll",
           "khoa_ui", "khoa_webhook"]
