"""
Facebook Graph API error code → user-friendly Vietnamese message mapping.

F5-04 fix: mirrors core/tiktok/error_codes.py pattern.
Translates cryptic Graph API error codes into actionable user messages.

Reference: https://developers.facebook.com/docs/graph-api/guides/error-handling
"""
from __future__ import annotations

from typing import Optional


# (error_code or subcode) → (user-friendly message, suggested action)
_ERROR_MAP: dict[int, tuple[str, str]] = {
    # ─── Auth / OAuth errors ───────────────────────────────────────────────
    190: (
        "Access token Facebook không hợp lệ hoặc đã hết hạn.",
        "Vào tab Tài khoản FB → Ngắt kết nối → Kết nối lại.",
    ),
    102: (
        "Phiên đăng nhập Facebook đã hết hạn.",
        "Vào tab Tài khoản FB → Ngắt kết nối → Kết nối lại.",
    ),
    104: (
        "Cần access_token nhưng không có.",
        "Kiểm tra cấu hình Meta App trong tab Cài đặt.",
    ),

    # ─── Permission errors ────────────────────────────────────────────────
    200: (
        "Tài khoản chưa cấp đủ quyền để đăng bài.",
        "Ngắt kết nối → Kết nối lại, đảm bảo chấp nhận TẤT CẢ quyền.",
    ),
    10: (
        "App không có quyền (permission) thực hiện thao tác này.",
        "Vào developers.facebook.com → App của bạn → Review quyền cần thiết.",
    ),
    230: (
        "Người dùng đã chặn app này.",
        "Yêu cầu user gỡ block app trong Facebook Settings → Apps.",
    ),

    # ─── Rate limit / quota ───────────────────────────────────────────────
    4: (
        "Vượt giới hạn API rate limit của Facebook.",
        "Bot sẽ chờ và thử lại tự động. Giảm tần suất nếu lặp lại nhiều.",
    ),
    17: (
        "Vượt user-level rate limit (quá nhiều request/giờ).",
        "Chờ 1 tiếng, hoặc giảm số worker concurrent. ",
    ),
    32: (
        "Page-level rate limit — page này đã vượt mức cho phép.",
        "Chờ 1-24 giờ trước khi đăng tiếp lên page này.",
    ),
    613: (
        "App-level rate limit.",
        "App của bạn đã vượt mức cho phép trong giờ này. Chờ 1 tiếng.",
    ),

    # ─── Content / post errors ────────────────────────────────────────────
    100: (
        "Tham số không hợp lệ.",
        "Kiểm tra: video path, page ID, privacy setting. Xem log để biết chi tiết.",
    ),
    1: (
        "Lỗi nội bộ Facebook (API hiccup).",
        "Bot sẽ retry tự động. Nếu lặp lại nhiều, kiểm tra status Facebook API.",
    ),
    2: (
        "Lỗi tạm thời từ Facebook server.",
        "Bot sẽ retry tự động. Thường tự khỏi sau vài phút.",
    ),
    341: (
        "Hành động bị Facebook chặn (rate-limit / spam).",
        "Đăng quá nhanh, quá nhiều. Chờ 30-60 phút trước khi tiếp tục.",
    ),
    368: (
        "Tài khoản tạm thời bị Facebook block do vi phạm chính sách cộng đồng.",
        "Kiểm tra Facebook Support Inbox để biết lý do và cách khắc phục.",
    ),

    # ─── Video upload specific ────────────────────────────────────────────
    6000: (
        "Video format không hỗ trợ.",
        "Chuyển video sang MP4 H.264. Dùng HandBrake hoặc FFmpeg.",
    ),
    6001: (
        "Video quá lớn.",
        "Giới hạn ~10GB. Nén video xuống dưới 4GB cho ổn định.",
    ),
    6080: (
        "Video duration vượt giới hạn cho phép.",
        "Page thường: max 240 phút. Reels: max 90 giây.",
    ),
}


def get_friendly_message(
    error_code: int | str,
    fallback: Optional[str] = None,
) -> str:
    """Return user-friendly Vietnamese message for a Facebook Graph API error code.

    Args:
        error_code:  the error code from Graph API (integer or string).
        fallback:    original message to show if code not mapped.

    Returns:
        Formatted message with action recommendation if mapped,
        or fallback/generic message otherwise.
    """
    # Normalize to int
    try:
        code = int(error_code)
    except (ValueError, TypeError):
        return fallback or f"Facebook Graph API trả lỗi không xác định (code: {error_code})."

    if code in _ERROR_MAP:
        msg, action = _ERROR_MAP[code]
        return f"{msg}\n💡 Khắc phục: {action}"

    if fallback:
        return f"Facebook Graph API lỗi: {fallback}\n(Mã lỗi: {code})"

    return f"Facebook Graph API trả lỗi không xác định (code: {code})."


def is_retryable(error_code: int | str, http_status: int = 0) -> bool:
    """Determine if an error is worth retrying."""
    try:
        code = int(error_code)
    except (ValueError, TypeError):
        return False
    if code in {1, 2, 4, 17, 341}:
        return True
    if http_status in {429, 500, 502, 503, 504}:
        return True
    return False
