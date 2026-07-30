"""
settings_schema.py — presentation schema for the web Settings page.

Mirrors the 11 cards of the desktop `gui/settings_tab.py`, but declares the
fields as data instead of hand-built widgets. Rendering is generic, so the
page stays a fraction of the desktop tab's 1,600 lines while covering the
same keys.

Values and defaults come from `core.config_defaults.DEFAULTS` — this module
only describes how to *show* them. Adding a config key there and listing it
here is all that is needed for it to appear in the UI.

Secret fields are marked `secret=True`: their current value is never sent to
the browser, and an empty submission means "keep what is stored" rather than
"clear it".
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from core.config_defaults import DEFAULTS
from core.config_help import FIELD_HELP

# Field kinds the template knows how to render.
TEXT, PASSWORD, NUMBER, BOOL, SELECT, TEXTAREA, JSONLIST = (
    "text", "password", "number", "bool", "select", "textarea", "jsonlist"
)


@dataclass(frozen=True)
class Field:
    key:     str
    label:   str
    kind:    str = TEXT
    hint:    str = ""
    options: tuple = ()
    secret:  bool = False

    @property
    def default(self):
        return DEFAULTS.get(self.key, "")

    @property
    def help_text(self) -> str:
        """Explicit hint wins; otherwise fall back to the desktop tooltip for
        this key (core.config_help), so the web shows the same guidance the
        desktop showed rather than a reworded version."""
        return self.hint or FIELD_HELP.get(self.key, "")


@dataclass(frozen=True)
class Group:
    id:     str
    title:  str
    colour: str
    note:   str = ""
    fields: tuple = dc_field(default_factory=tuple)


GROUPS: tuple = (
    Group("general", "Chung", "#9C27B0", fields=(
        Field("app_language", "Ngôn ngữ giao diện", SELECT,
              options=(("vi", "Tiếng Việt"), ("en", "English"))),
        Field("timezone", "Múi giờ", TEXT, "Dùng cho lịch đăng và giới hạn theo ngày"),
    )),

    Group("identity", "Thông tin ứng dụng", "#00695C",
          note="Bắt buộc khi nộp duyệt TikTok.", fields=(
        Field("app_name", "Tên ứng dụng"),
        Field("app_support_email", "Email hỗ trợ"),
        Field("app_privacy_policy_url", "URL chính sách riêng tư"),
        Field("app_terms_url", "URL điều khoản"),
    )),

    Group("meta", "Meta App (Facebook)", "#1565C0",
          note="Lấy từ Meta Developers → App → Settings → Basic.", fields=(
        Field("meta_app_id", "App ID"),
        Field("meta_app_secret", "App Secret", PASSWORD, secret=True,
              hint="Để trống = giữ nguyên giá trị đang lưu"),
        Field("graph_api_version", "Phiên bản Graph API"),
        Field("meta_redirect_uri", "OAuth Redirect URI",
              hint="Phải trùng chính xác với khai báo trong Meta App"),
    )),

    Group("tiktok", "TikTok (Content Posting API v2)", "#6A0DAD", fields=(
        Field("tiktok_client_key", "Client Key"),
        Field("tiktok_client_secret", "Client Secret", PASSWORD, secret=True,
              hint="Để trống = giữ nguyên"),
        Field("tiktok_redirect_uri", "Redirect URI"),
        Field("tiktok_scopes", "Scopes"),
        Field("tiktok_publish_mode", "Chế độ đăng", SELECT, options=(
            ("draft_upload", "draft_upload — đẩy vào nháp (an toàn nhất)"),
            ("direct_private", "direct_private — đăng riêng tư"),
            ("direct_public", "direct_public — đăng công khai"),
        )),
        Field("tiktok_privacy_level", "Mức riêng tư", SELECT, options=(
            ("SELF_ONLY", "SELF_ONLY"),
            ("FOLLOWER_OF_CREATOR", "FOLLOWER_OF_CREATOR"),
            ("MUTUAL_FRIEND_FRIENDS", "MUTUAL_FRIEND_FRIENDS"),
            ("PUBLIC_TO_EVERYONE", "PUBLIC_TO_EVERYONE"),
        )),
        Field("tiktok_enable_direct_post", "Cho phép đăng trực tiếp", BOOL),
        Field("tiktok_audit_approved", "TikTok đã duyệt app", BOOL,
              hint="Chỉ bật khi TikTok đã chính thức duyệt — ảnh hưởng đăng công khai"),
        Field("tiktok_require_user_confirm", "Bắt buộc xác nhận trước khi đăng", BOOL),
        Field("tiktok_disable_comment", "Tắt bình luận", BOOL),
        Field("tiktok_disable_duet", "Tắt duet", BOOL),
        Field("tiktok_disable_stitch", "Tắt stitch", BOOL),
        Field("tiktok_poll_interval_s", "Chu kỳ hỏi trạng thái (giây)", NUMBER),
        Field("tiktok_upload_timeout_s", "Timeout upload (giây)", NUMBER),
        Field("tiktok_request_timeout_s", "Timeout request (giây)", NUMBER),
    )),

    Group("sheets", "Google Sheets", "#1B5E20", fields=(
        Field("google_credentials_path", "Đường dẫn credentials.json",
              hint="Đường dẫn TRÊN MÁY CHỦ, ví dụ C:\\LTTPlatform\\secrets\\credentials.json"),
        Field("sheet_id", "Sheet ID"),
        Field("sheet_tab", "Tab mặc định"),
        Field("skip_overdue_minutes", "Bỏ qua job trễ quá (phút)", NUMBER),
        Field("job_delay_seconds", "Nghỉ giữa các job (giây)", NUMBER),
        Field("max_retries", "Số lần thử lại tối đa", NUMBER),
    )),

    Group("columns", "Tên cột trong Sheet", "#37474F",
          note="Phải khớp CHÍNH XÁC header dòng 1 của tab. Trang Tình trạng sẽ "
               "báo nếu lệch và gợi ý tên đúng.", fields=(
        Field("col_schedule_time", "Lịch đăng (BẮT BUỘC)",
              hint="Không có cột này bot sẽ không xử lý được row nào"),
        Field("col_status", "Trạng thái (BẮT BUỘC)"),
        Field("col_video_drive", "Link video nguồn"),
        Field("col_title", "Tiêu đề"),
        Field("col_description", "Mô tả"),
        Field("col_keywords", "Từ khoá"),
        Field("col_thumbnail_url", "Link ảnh thumbnail"),
        Field("col_comment", "Bình luận"),
        Field("col_target_page", "Page đích"),
        Field("col_error", "Thông báo lỗi",
              hint="Thiếu cột này thì lỗi sẽ KHÔNG được ghi ngược lại sheet"),
        Field("col_fb_link", "Link bài Facebook"),
        Field("col_fb_video_id", "Facebook video ID"),
        Field("col_uploaded_at", "Thời điểm đăng"),
        Field("col_upload_duration", "Thời lượng upload"),
        Field("col_post_type", "Kiểu bài"),
        Field("col_platform", "Nền tảng"),
    )),

    Group("columns_tiktok", "Tên cột — TikTok", "#4A148C", fields=(
        Field("col_tiktok_account", "Tài khoản TikTok"),
        Field("col_tiktok_status", "Trạng thái TikTok"),
        Field("col_tiktok_link", "Link bài TikTok"),
        Field("col_tiktok_id", "TikTok ID"),
        Field("col_tiktok_privacy", "Mức riêng tư"),
        Field("col_tiktok_ai_content", "Nội dung AI"),
        Field("col_tiktok_commercial", "Nội dung thương mại"),
        Field("col_tiktok_confirmed_at", "Thời điểm xác nhận"),
    )),

    Group("safety_fb", "Chống khoá — Facebook", "#B71C1C", fields=(
        Field("min_interval_per_page_s", "Giãn cách tối thiểu mỗi page (giây)", NUMBER),
        Field("min_inter_page_interval_s", "Giãn cách giữa các page (giây)", NUMBER),
        Field("jitter_s", "Nhiễu ngẫu nhiên (giây)", NUMBER),
        Field("active_hours_start", "Giờ bắt đầu hoạt động", NUMBER, "0 = không giới hạn"),
        Field("active_hours_end", "Giờ kết thúc", NUMBER),
        Field("max_posts_per_page_per_day", "Tối đa bài/page/ngày", NUMBER, "0 = không giới hạn"),
        Field("max_posts_per_account_per_day", "Tối đa bài/tài khoản/ngày", NUMBER,
              "Khuyến nghị ~30 nếu 1 tài khoản quản 5-7 page"),
        Field("max_concurrent_uploads_per_page", "Upload đồng thời mỗi page", NUMBER),
    )),

    Group("safety_tt", "Chống khoá — TikTok", "#6A0DAD",
          note="Để 0 = dùng lại giá trị Facebook ở trên.", fields=(
        Field("tt_min_interval_per_account_s", "Giãn cách mỗi tài khoản (giây)", NUMBER),
        Field("tt_min_inter_account_interval_s", "Giãn cách giữa tài khoản (giây)", NUMBER),
        Field("tt_jitter_s", "Nhiễu ngẫu nhiên (giây)", NUMBER),
        Field("tt_active_hours_start", "Giờ bắt đầu", NUMBER),
        Field("tt_active_hours_end", "Giờ kết thúc", NUMBER),
        Field("tt_max_posts_per_account_per_day", "Tối đa bài/tài khoản/ngày", NUMBER),
        Field("tt_job_delay_seconds", "Nghỉ giữa job TikTok (giây)", NUMBER),
    )),

    Group("antispam", "Chống spam nâng cao", "#5D1A8B", fields=(
        Field("anti_spam_dedup", "Chặn đăng trùng nội dung", BOOL),
        Field("anti_spam_random_order", "Xáo thứ tự hàng", BOOL,
              hint="Đăng đúng thứ tự sheet mỗi ngày là dấu hiệu của bot"),
        Field("anti_spam_circuit_breaker", "Ngắt mạch khi lỗi liên tiếp", BOOL),
        Field("anti_spam_session_lock_enabled", "Bật khoá phiên", BOOL),
        Field("anti_spam_warmup_enabled", "Khởi động dần tài khoản mới", BOOL),
        Field("anti_spam_video_validate", "Kiểm tra video hợp lệ", BOOL),
        Field("anti_spam_watermark_check", "Kiểm tra watermark", BOOL),
        Field("anti_spam_audio_rights_check", "Kiểm tra bản quyền âm thanh", BOOL),
        Field("anti_spam_scope_verify", "Kiểm tra quyền (scope)", BOOL),
        Field("anti_spam_content_policy", "Kiểm tra chính sách nội dung", BOOL),
        Field("anti_spam_app_status_check", "Kiểm tra trạng thái Meta App", BOOL),
        Field("anti_spam_retention_days", "Giữ lịch sử (ngày)", NUMBER),
        Field("anti_spam_video_variation_mode", "Chế độ biến đổi video"),
        Field("anti_spam_cross_target_warn_threshold", "Ngưỡng cảnh báo trùng đích", NUMBER),
        Field("caption_rotator_enabled", "Xoay vòng caption", BOOL),
        Field("caption_rotator_keep_original", "Giữ caption gốc", BOOL),
        Field("network_identity_enabled", "Đổi User-Agent / proxy", BOOL),
    )),

    Group("comments", "Bình luận tự động", "#0277BD", fields=(
        Field("fb_comment_enabled", "Bật bình luận Facebook", BOOL),
        Field("fb_comment_delay_min_s", "Chờ tối thiểu (giây)", NUMBER),
        Field("fb_comment_delay_max_s", "Chờ tối đa (giây)", NUMBER),
        Field("tt_comment_delay_min_s", "TikTok — chờ tối thiểu (giây)", NUMBER),
        Field("tt_comment_delay_max_s", "TikTok — chờ tối đa (giây)", NUMBER),
    )),

    Group("insights", "Thống kê bài đăng", "#00838F", fields=(
        Field("insights_min_age_h", "Chỉ lấy bài cũ hơn (giờ)", NUMBER),
        Field("insights_scan_interval_s", "Chu kỳ quét (giây)", NUMBER),
        Field("col_insights_at", "Cột: thời điểm lấy"),
        Field("col_views", "Cột: lượt xem"),
        Field("col_reach", "Cột: tiếp cận"),
        Field("col_reactions", "Cột: cảm xúc"),
        Field("col_comments_count", "Cột: số bình luận"),
        Field("col_shares", "Cột: chia sẻ"),
        Field("col_minutes_viewed", "Cột: phút đã xem"),
    )),

    Group("notify", "Thông báo Telegram", "#1565C0",
          note="Tuỳ chọn. Dùng để báo lỗi và token sắp hết hạn.", fields=(
        Field("telegram_bot_token", "Bot Token", PASSWORD, secret=True,
              hint="Để trống = giữ nguyên"),
        Field("telegram_chat_id", "Chat ID"),
        Field("notify_on_error", "Báo khi lỗi", BOOL),
        Field("notify_on_token_expiry", "Báo khi token sắp hết hạn", BOOL),
        Field("notify_on_complete", "Báo khi chạy xong", BOOL),
    )),

    Group("storage", "Lưu trữ và video", "#455A64", fields=(
        Field("temp_video_dir", "Thư mục video tạm"),
        Field("delete_video_after_upload", "Xoá video sau khi đăng", BOOL),
        Field("verify_video_after_upload", "Kiểm tra lại sau khi đăng", BOOL),
    )),

    Group("advanced", "Nâng cao — danh sách JSON", "#546E7A",
          note="Các mục này là danh sách/đối tượng nên sửa trực tiếp dạng JSON. "
               "Cú pháp sai sẽ bị từ chối, cấu hình đang chạy không bị ghi đè.",
          fields=(
        Field("sheets", "Danh sách Google Sheet", JSONLIST,
              hint='Ví dụ: [{"id": "...", "alias": "Default"}]'),
        Field("meta_app_pool", "Pool Meta App", JSONLIST),
        Field("tiktok_client_pool", "Pool TikTok Client", JSONLIST),
        Field("page_mapping", "Ánh xạ tab sheet → page", JSONLIST),
        Field("caption_rotator_templates", "Mẫu caption", JSONLIST),
        Field("caption_rotator_pools", "Pool caption", JSONLIST),
        Field("tiktok_banned_hashtags", "Hashtag bị cấm", JSONLIST),
        Field("network_user_agents", "Danh sách User-Agent", JSONLIST),
        Field("network_proxies", "Danh sách proxy", JSONLIST),
    )),
)


def all_field_keys() -> set:
    return {f.key for g in GROUPS for f in g.fields}


def field_by_key(key: str):
    for g in GROUPS:
        for f in g.fields:
            if f.key == key:
                return f
    return None


def secret_keys() -> set:
    return {f.key for g in GROUPS for f in g.fields if f.secret}


def coverage_report() -> dict:
    """Which DEFAULTS keys are not yet exposed in the UI.

    Used by a test so a config key added to core.config_defaults cannot be
    silently unreachable from the web UI.
    """
    shown = all_field_keys()
    return {
        "shown": sorted(shown),
        "missing": sorted(set(DEFAULTS) - shown),
        "unknown": sorted(shown - set(DEFAULTS)),
    }
