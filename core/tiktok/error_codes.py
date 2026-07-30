"""
TikTok API error code → user-friendly Vietnamese message mapping.

H3 fix: Translate cryptic TikTok error codes into actionable user messages.

Reference: https://developers.tiktok.com/doc/content-posting-api-reference-error-codes
"""
from __future__ import annotations

from typing import Optional


# (error_code) → (user-friendly message, suggested action)
_ERROR_MAP: dict[str, tuple[str, str]] = {
    # ─── Auth errors ────────────────────────────────────────────────────────
    "access_token_invalid": (
        "Token TikTok không hợp lệ.",
        "Vào tab Tài khoản → Ngắt kết nối → Kết nối lại TikTok.",
    ),
    "access_token_expired": (
        "Token TikTok đã hết hạn.",
        "Bot đang tự động làm mới — nếu lỗi tái diễn, hãy reconnect.",
    ),
    "token_expired": (
        "Token TikTok đã hết hạn.",
        "Bot đang tự động làm mới — nếu lỗi tái diễn, hãy reconnect.",
    ),
    "scope_not_authorized": (
        "Tài khoản TikTok chưa cấp đủ quyền cho bot.",
        "Ngắt kết nối và kết nối lại — đảm bảo bấm 'Authorize' tất cả scopes.",
    ),
    "scope_permission_missed": (
        "Tài khoản TikTok thiếu quyền video.publish.",
        "Ngắt kết nối và kết nối lại. Nếu app chưa qua audit, chỉ dùng Draft mode.",
    ),

    # ─── Rate limit & spam ──────────────────────────────────────────────────
    "rate_limit_exceeded": (
        "Vượt giới hạn TikTok API.",
        "Bot sẽ chờ và thử lại tự động. Giảm tần suất đăng nếu lặp lại.",
    ),
    "spam_risk_too_many_pending_share": (
        "Quá nhiều bài đang xử lý — TikTok flag spam.",
        "Chờ 30-60 phút để các bài cũ xử lý xong, rồi tiếp tục.",
    ),
    "spam_risk_text": (
        "Caption có nội dung TikTok coi là spam.",
        "Sửa caption: giảm hashtag, bỏ link, viết tự nhiên hơn.",
    ),
    "spam_risk_user_banned_from_posting": (
        "Tài khoản TikTok này đang bị TikTok hạn chế đăng bài.",
        "Đăng nhập TikTok app, kiểm tra thông báo. Chờ TikTok gỡ hạn chế.",
    ),

    # ─── Content policy ─────────────────────────────────────────────────────
    "unaudited_client_can_only_post_to_private_accounts": (
        "App chưa được TikTok kiểm duyệt → chỉ đăng được tài khoản TikTok PRIVATE.",
        "Chuyển tài khoản sang Private trong TikTok app, HOẶC submit app cho TikTok audit.",
    ),
    "video_pull_failed": (
        "TikTok không tải được video.",
        "Kiểm tra: video < 4GB, format MP4/MOV, không hỏng file.",
    ),
    "publish_cancelled": (
        "TikTok hủy bài đăng (vi phạm chính sách hoặc lỗi xử lý).",
        "Mở TikTok app xem thông báo cụ thể. Có thể do nội dung vi phạm community guidelines.",
    ),
    "video_format_not_supported": (
        "Định dạng video không hỗ trợ.",
        "Chuyển video sang MP4 H.264 (dùng HandBrake hoặc FFmpeg).",
    ),
    "duration_exceeds_max_duration_limit": (
        "Video quá dài.",
        "Cắt ngắn dưới 10 phút (free account) hoặc 60 phút (verified).",
    ),
    "frame_rate_unsupported": (
        "Frame rate không hỗ trợ.",
        "Chuyển video sang 23-60 FPS.",
    ),
    "picture_size_check_failed": (
        "Kích thước video không hợp lệ.",
        "Resize video về 720p hoặc 1080p, aspect ratio 9:16 (dọc) hoặc 16:9 (ngang).",
    ),

    # ─── User account ───────────────────────────────────────────────────────
    "user_not_in_whitelist": (
        "Tài khoản chưa nằm trong whitelist sandbox của app.",
        "Vào TikTok Developer Portal → My Apps → Add target user.",
    ),

    # ─── Server errors ──────────────────────────────────────────────────────
    "internal_error": (
        "TikTok server gặp lỗi nội bộ.",
        "Bot sẽ retry tự động. Nếu lặp lại nhiều lần, kiểm tra status TikTok API.",
    ),
}


def get_friendly_message(error_code: str, fallback: Optional[str] = None) -> str:
    """Return user-friendly Vietnamese message for a TikTok error code.

    Args:
        error_code:  the error code returned by TikTok API
        fallback:    original message to show if code not mapped

    Returns:
        A formatted message string with action recommendation if mapped,
        or the fallback (or generic) message if not.
    """
    code = (error_code or "").lower().strip()

    if code in _ERROR_MAP:
        msg, action = _ERROR_MAP[code]
        return f"{msg}\n💡 Khắc phục: {action}"

    if fallback:
        return f"TikTok API lỗi: {fallback}\n(Mã lỗi: {code or 'unknown'})"

    return f"TikTok API trả lỗi không xác định (code: {code or 'unknown'})."


def is_retryable(error_code: str, http_status: int = 0) -> bool:
    """Determine if an error is worth retrying (transient vs permanent)."""
    code = (error_code or "").lower().strip()
    if code in {"rate_limit_exceeded", "internal_error",
                "spam_risk_too_many_pending_share"}:
        return True
    if http_status in {429, 500, 502, 503, 504}:
        return True
    return False
