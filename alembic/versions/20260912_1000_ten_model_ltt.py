"""Cắt tên model cũ: `ltt_llm` / `ltt_llm_vision` → `ltt-3.8` (D02, dual-model 2.3).

## Việc này di trú CÁI GÌ — và cố ý KHÔNG di trú cái gì

Từ 2.3, `apps/ltt_llm/manifest.py` chỉ nhận đúng hai tên: `ltt-3.8`, `ltt-3.5`.
Mọi chỗ **còn phải chạy tiếp** mà đang giữ tên cũ sẽ 400 ở lượt kế:

* `jobs.params["model"]` của job `queued`/`running` — worker đọc nó để giải
  admission rồi gọi máy B;
* `chatltt_conversation.model_alias` — **lựa chọn đang có hiệu lực** của hội
  thoại, thứ lượt sau sẽ dùng;
* `chatltt_message.model_alias` của message **chưa xong** (`queued`/`streaming`),
  vì `services/luot.py` dựng `params = {"model": tra_loi.model_alias}` từ đúng
  cột này khi chạy tiếp.

⛔ **KHÔNG ĐỔI LỊCH SỬ.** Không chạm `credit_entries`, `job_events`, bảng
   `usage`/`request_logs`, cũng không chạm `chatltt_message` đã `done`/`error`.
   Một dòng sổ nói *"lượt này chạy trên `ltt_llm`"* là **sự thật của ngày ấy**;
   viết lại nó thành `ltt-3.8` là làm hỏng đúng thứ khách dùng để đối soát, và
   đổi lại chẳng được gì — không ai chạy lại một lượt đã quyết toán.

   Ranh giới nằm ở một câu hỏi: *hàng này còn được ĐỌC ĐỂ CHẠY nữa không?*
   Còn ⇒ di trú. Không ⇒ để yên.

## Vì sao `ltt_llm_vision` cũng về `ltt-3.8` chứ không về `ltt-3.5`

`ltt-3.5` là một model **khác**, trên card khác, với bảng giá khác. Ném một
lượt đang chờ của khách sang đó là đổi hàng họ đã chọn. `ltt-3.8` mới là model
kế thừa của cả hai tên cũ: cùng trọng số, và nó **cũng đọc ảnh** (hồ sơ
`qwen38-api` nạp mmproj), nên không lượt nào mất năng lực.

## Đảo lại

`downgrade()` không dựng lại tên cũ, và đó là câu trả lời đúng chứ không phải
chỗ trống: sau khi đi lên, `ltt_llm` **không còn là một model** — trả một hàng
về đó là dựng lại đúng cái 400 mà bước lên vừa dọn. Đảo mã nguồn (revert commit)
là cách quay lại, không phải đảo dữ liệu.

Revision ID: b4d7f2c19e30
Revises: 7c1e4b9a2d58
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "b4d7f2c19e30"
down_revision = "7c1e4b9a2d58"
branch_labels = None
depends_on = None

#: Tên cũ → tên mới. Cả hai về `ltt-3.8`; lý do ở docstring.
BAN_DO = {"ltt_llm": "ltt-3.8", "ltt_llm_vision": "ltt-3.8"}

#: Job còn được worker nhặt. Job đã `done`/`error`/`cancelled` là lịch sử.
TRANG_THAI_SONG = ("queued", "running")

#: Message chưa có câu trả lời cuối. `done`/`error`/`cancelled` là lịch sử.
MESSAGE_SONG = ("queued", "streaming")


def _co_bang(bind, ten: str) -> bool:
    return sa.inspect(bind).has_table(ten)


def upgrade() -> None:
    bind = op.get_bind()

    # ── jobs.params["model"] ────────────────────────────────────────────────
    #
    # ⛔ Sửa trong Python, KHÔNG bằng một `UPDATE ... jsonb_set`. Cột `params`
    #    khai `sa.JSON`, nên trên SQLite nó là TEXT và trên PostgreSQL là `json`
    #    (không phải `jsonb`) — không toán tử JSON nào chạy được trên cả hai.
    #    Số hàng ở đây là số job ĐANG CHỜ, tức hàng chục, không phải hàng triệu.
    if _co_bang(bind, "jobs"):
        hang = bind.execute(sa.text(
            "SELECT id, params FROM jobs "
            "WHERE job_type = :lane AND status IN ('queued', 'running')"
        ), {"lane": "ltt_llm.chat"}).fetchall()
        for job_id, params in hang:
            if isinstance(params, str):
                try:
                    doc = json.loads(params)
                except ValueError:
                    continue
            else:
                doc = params
            if not isinstance(doc, dict):
                continue
            moi = BAN_DO.get(str(doc.get("model") or ""))
            if not moi:
                continue
            doc["model"] = moi
            bind.execute(sa.text("UPDATE jobs SET params = :p WHERE id = :i"),
                         {"p": json.dumps(doc), "i": job_id})

    # ── ChatLTT: lựa chọn ĐANG CÓ HIỆU LỰC ──────────────────────────────────
    for cu, moi in BAN_DO.items():
        if _co_bang(bind, "chatltt_conversation"):
            bind.execute(sa.text(
                "UPDATE chatltt_conversation SET model_alias = :moi "
                "WHERE model_alias = :cu"), {"moi": moi, "cu": cu})
        if _co_bang(bind, "chatltt_message"):
            bind.execute(sa.text(
                "UPDATE chatltt_message SET model_alias = :moi "
                "WHERE model_alias = :cu AND status IN ('queued', 'streaming')"
            ), {"moi": moi, "cu": cu})


def downgrade() -> None:
    """Không đảo. Xem docstring: `ltt_llm` không còn là một model hợp lệ."""
