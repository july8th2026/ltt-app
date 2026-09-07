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
#:
#: 📌 `"mo_rong_prompt"` (`A5`) **cố ý chưa có mặt ở đây.** Đường mã đã viết đủ
#:    (`ho_so.khoa_mo_rong`, `jobs`, route, giao diện), nhưng trọng số của bộ mở
#:    rộng — `Qwen3.5-9B Abliterated`, `enhancer_enabled = 4` — chưa từng tải và
#:    chưa từng chạy trên ngăn xếp py3.11/cu130 hiện tại. Bật một ô tick mà máy
#:    phía sau chưa có model là **nói dối người dùng bằng giao diện**: WanGP bỏ
#:    qua khoá ấy trong im lặng (`wgp.py:6853` cần `enhancer_enabled > 0`), nên
#:    không có gì đỏ lên — chỉ là ô tick không làm gì cả.
#:
#: ⇒ Đợt B: chạy `tools/wangp/cau_hinh_enhancer.py`, sinh thật **một** video có
#:   bật mở rộng, rồi mới thêm `"mo_rong_prompt"` vào tuple này.
NANG_LUC_MO: tuple[str, ...] = ("tao_video",)

#: Vai được dùng app — **đọc `User.role` của nền tảng**, không phải một bảng vai
#: riêng của app.
#:
#: 🔴 Bản đầu viết `{"nhan_vien", "admin"}` và đọc `user.vai`. Cả hai đều không
#:    tồn tại: `platform_core/models.py:106` khai đúng một cột `role` với hai giá
#:    trị `admin`/`user`, và chuỗi `"nhan_vien"` không xuất hiện ở bất cứ đâu
#:    khác trong kho.
#:
#: ⛔ Nó **không đỏ** ở đâu cả, vì nơi gọi viết `getattr(user, "vai",
#:    "nhan_vien")`. Thiếu thuộc tính ⇒ nhận giá trị mặc định ⇒ mặc định nằm
#:    trong danh sách cho phép ⇒ cổng luôn trả `True`. Một cổng quyền chấm trên
#:    hằng số của chính nó là một cổng không chấm gì. Bộ test cũng xanh, vì nó
#:    truyền thẳng chuỗi `vai="nhan_vien"` chứ không đi qua một `User` thật.
#:
#: ⭐ `admin` là vai **duy nhất** tới được app này, và điều đó đã đúng từ trước:
#:    manifest khai `surface="admin"`, nên `server/access_middleware.py:71` trả
#:    **404** cho mọi tài khoản có `role != "admin"`. Nghĩa là hàng dưới đây
#:    không siết thêm gì — nó chép lại đúng thứ đang xảy ra, thay cho một từ vựng
#:    chưa bao giờ có thật.
VAI_DUOC_DUNG: frozenset[str] = frozenset({"admin"})

#: Tên hiển thị bằng ngôn ngữ sản phẩm, để thông báo từ chối không rò tên nội bộ.
_TEN_THAN_THIEN = {
    "tao_video": N_("tạo video từ mô tả"),
    "mo_rong_prompt": N_("mở rộng mô tả tự động"),
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
