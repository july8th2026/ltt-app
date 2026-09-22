"""Sổ "hệ" phiên âm của App `transcript` — một hệ = một bộ nhận chữ + CÙNG quy tắc LTT.

Chủ dự án chốt 22/09/2026: hệ gốc (quy tắc của `bot_transcript`) là chuẩn; App phải
**mở** để sau này thêm hệ/skill mới và người dùng chọn hệ trên giao diện và cổng API.

Mọi hệ đi qua cùng một đường (`phien_am.chay`): VAD → STT → sửa chữ V5 → dựng
dòng thời gian LTT → kiểm → sáu khoá. Một hệ chỉ được khác nhau ở PHẦN NHẬN CHỮ
(model STT); quy tắc câu, đoạn, khoảng lặng, kiểm lỗi là của chung — thêm hệ mới
không được fork logic đó.

Thêm hệ: thêm MỘT mục vào `HE` dưới đây (và test). Không sửa `phien_am`.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.i18n import N_


@dataclass(frozen=True)
class He:
    ma: str          # giá trị tham số `he` (API + form)
    ten: str         # nhãn trên giao diện
    mo_ta: str       # một câu cho người chọn
    model: str       # model STT (faster-whisper / CTranslate2)


#: Hệ mặc định = hệ gốc chủ dự án đã làm chuẩn quy tắc.
MAC_DINH = "ltt"

HE: dict[str, He] = {
    "ltt": He(
        ma="ltt",
        ten=N_("LTT chuẩn"),
        mo_ta=N_("Whisper large-v3 + quy tắc LTT (hệ gốc, mặc định)"),
        model="large-v3",
    ),
    # `ltt_turbo` (large-v3-turbo) đã thử 22/09 và bị chủ dự án GỠ cùng ngày:
    # giữ một hệ chuẩn. Thêm hệ mới = thêm một mục ở đây (+ test).
}


def lay(ma: str | None) -> He:
    """`ma` rỗng ⇒ hệ mặc định. Mã lạ ⇒ `KeyError` (bên gọi đổi thành lỗi tham số)."""
    return HE[(ma or "").strip() or MAC_DINH]
