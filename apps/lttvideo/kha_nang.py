"""Allowlist năng lực — **chính sách của LTT**, không phải khám phá năng lực.

⛔ ĐÂY KHÔNG PHẢI `CapabilityResolver`. Phân biệt hai câu hỏi:

    "Model làm được việc này không?"   -> WanGP tra loi.
                                         list_model_defs(inputs=, main_output=)
                                         get_model_availability()
                                         metadata.capabilities / media_inputs

    "Khách hạng này ĐƯỢC PHÉP không?"  -> chi LTT tra loi duoc.
                                         <- module nay

Câu thứ nhất là **dữ liệu**, suy được từ engine. Câu thứ hai là **quyết định
kinh doanh**, không suy được từ đâu cả. Trộn hai câu là dựng bản sao thứ hai của
sự thật — đúng cơ chế đã gỡ bảng 280 dòng khỏi `CLAUDE.md`.

🔒 Bất biến có phép kiểm canh (`test_721`): **module này không được biết tên
   model nào.** Biết tên model ở đây nghĩa là nó đã lấn sang câu hỏi của WanGP.
"""
from __future__ import annotations

from platform_core.i18n import N_, _

#: Năng lực đang mở cho baseline.
#:
#: ⭐ Mở **hẹp có chủ đích**. WanGP hỗ trợ rất nhiều thứ (video edit, character
#:    animation, talking head, nhạc, giọng nói…) — mở hết ngay là bỏ luôn khả
#:    năng biết thứ nào thật sự chạy được trên hạ tầng của ta.
#:
#: ⛔ Mở thêm một năng lực là **một quyết định**: phải có hồ sơ đã duyệt
#:    (`ho_so.py`) và một lượt chạy thật chứng minh nó chạy, rồi mới thêm vào đây.
NANG_LUC_MO: tuple[str, ...] = ("tao_video",)

#: Vai được dùng app. Baseline nội bộ ⇒ chỉ nhân viên (`D-V2-011`).
VAI_DUOC_DUNG: frozenset[str] = frozenset({"nhan_vien", "admin"})

#: Tên hiển thị bằng ngôn ngữ sản phẩm, để thông báo từ chối không rò tên nội bộ.
_TEN_THAN_THIEN = {
    "tao_video": N_("tạo video từ mô tả"),
}


def duoc_phep(nang_luc: str, *, vai: str) -> bool:
    return kiem(nang_luc, vai=vai)[0]


def kiem(nang_luc: str, *, vai: str) -> tuple[bool, str]:
    """Trả `(được_phép, lý_do)`.

    Lý do viết bằng **ngôn ngữ người dùng** và **không nhắc tên nội bộ** — thông
    báo từ chối là bề mặt công khai, nó không được kể ra ta có những gì.
    """
    if vai not in VAI_DUOC_DUNG:
        return False, _("Bạn chưa có quyền dùng công cụ này.")
    if nang_luc not in NANG_LUC_MO:
        return False, _("Tính năng này chưa mở. Hiện tại chỉ tạo video từ mô tả.")
    return True, ""


def ten_than_thien(nang_luc: str) -> str:
    return _TEN_THAN_THIEN.get(nang_luc, N_("tính năng này"))
