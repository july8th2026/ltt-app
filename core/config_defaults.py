"""
config_defaults.py — canonical default values for data/config.json.

Extracted from gui/settings_tab.py so the web server can use the same
source of truth without importing gui.* (which pulls in customtkinter and
is forbidden on the server path — see AGENTS.md).

gui/settings_tab.py re-imports DEFAULTS from here, so there is exactly one
definition. Do not copy this dict anywhere else.
"""
from __future__ import annotations

DEFAULTS = {
    # i18n: UI language. "en" = English (default, audit-friendly), "vi" = Vietnamese
    "app_language":          "en",
    # Meta App (Facebook Login / Graph API)
    "meta_app_id":           "",
    "meta_app_secret":       "",
    "graph_api_version":     "v21.0",
    "meta_redirect_uri":     "",   # HTTPS bridge URL (e.g. https://lttstudios.com/auth/fb-callback.html)
    # Google Sheet
    "google_credentials_path": "data/credentials.json",
    "sheet_id":                "",
    "sheet_tab":               "",
    "sheets":                  [],   # multi-sheet: list[{id, alias}]
    "job_delay_seconds":       900,
    "timezone":                "Asia/Ho_Chi_Minh",
    "skip_overdue_minutes":    60,
    "max_concurrent_uploads_per_page": 1,
    "min_interval_per_page_s": 30,
    # Production-safety rate-limit dimensions (0/empty = disabled, backwards compat)
    "min_inter_page_interval_s":  0,    # min seconds between ANY two posts (recommend 180 cho 15-20 page)
    "jitter_s":                   0,    # random ±s added to interval (anti-fingerprint)
    "active_hours_start":         0,    # start hour 0-23 (e.g. 8). 0=0 disables window
    "active_hours_end":           0,    # end hour 0-23 (e.g. 23)
    "max_posts_per_page_per_day": 0,    # daily cap per page (0=unlimited)
    "max_posts_per_account_per_day": 0, # daily cap per FB user account (0=unlimited) — RECOMMEND 30 cho 1 acc quản 5-7 page
    # ─── TikTok-specific rate-limit overrides (prefix tt_*) ─────────────────
    # Empty/0 = fallback về key chung phía trên (backwards compat)
    "tt_min_interval_per_account_s":   0,   # giây giữa 2 post cùng acc TikTok
    "tt_min_inter_account_interval_s": 0,   # giây giữa 2 post bất kỳ acc TT
    "tt_jitter_s":                     0,   # ±s random cho TikTok
    "tt_active_hours_start":           0,
    "tt_active_hours_end":             0,
    "tt_max_posts_per_account_per_day": 30,  # TT enforce ~30/day per user — bot tự tracking để cảnh báo
    "tt_job_delay_seconds":            0,   # giây giữa các job TikTok (0 = dùng job_delay_seconds chung)
    # ─── Anti-spam Phase 1 toggles (all default ON) ─────────────────────────
    "anti_spam_dedup":              True,   # skip re-upload of same video to same target trong 30 ngày
    "anti_spam_random_order":       True,   # shuffle các row ready trước khi pick → phá pattern
    "anti_spam_circuit_breaker":    True,   # auto-pause khi error rate spike
    "anti_spam_warmup_enabled":     True,   # P3.2: page warm-up cap cho page mới (FB only)
    "anti_spam_retention_days":     90,     # GAP-8: tự xoá record content_history cũ hơn N ngày
    # ─── Sprint A: Content-layer variation ─────────────────────────────────
    "caption_rotator_enabled":      True,   # A1: auto-rotate caption per (target, video, day)
    "caption_rotator_templates":    [],     # A1: list[str] custom templates với {var} placeholders
    "caption_rotator_pools":        {},     # A1: dict[str, list[str]] override default pools
    "caption_rotator_keep_original": True,  # A1: include original caption in template pool
    "anti_spam_video_variation_mode": "off",  # A4: off|metadata_pad|ffmpeg|auto (recommend metadata_pad)
    "anti_spam_cross_target_warn_threshold": 3,  # A3: warn nếu video lặp lại ≥ N target trong 7d
    # ─── Sprint B+C runtime toggles ────────────────────────────────────────
    "anti_spam_session_lock_enabled": True,    # B2: file-lock chống concurrent bot
    "anti_spam_app_status_check":     True,    # B3: probe Meta App status mỗi 24h
    "meta_app_pool":                  [],      # B1: list[dict] of fallback apps; empty = use single meta_app_id/secret
    "network_identity_enabled":       False,   # C: enable per-account UA/proxy rotation
    "network_user_agents":            [],      # C: optional override of UA pool
    "network_proxies":                [],      # C: list of "http://user:pass@host:port"
    # ─── Sprint TT-1..4 — TikTok-specific advanced ────────────────────────
    "tt_comment_delay_min_s":         0,       # TT-1.6: min s delay before TT comment
    "tt_comment_delay_max_s":         0,       # TT-1.6: max s delay (recommend 30-180)
    "tiktok_client_pool":             [],      # TT-1.4: list[dict] {client_key, client_secret, redirect_uri, name}
    # ─── Sprint TT-5 (F1-F6): pre-flight validation toggles ───────────────
    "anti_spam_video_validate":       True,    # F1: ffprobe video properties
    "anti_spam_scope_verify":         True,    # F2: runtime scope check
    "anti_spam_watermark_check":      True,    # F4: filename + encoder watermark heuristic
    "anti_spam_audio_rights_check":   True,    # F5: ID3 + filename audio rights heuristic
    "anti_spam_content_policy":       True,    # F6: caption + hashtag policy
    "tiktok_banned_hashtags":         [],      # F6: extra ban list (user-defined)
    "fb_comment_delay_min_s":       0,      # P4.3: min delay s trước comment FB (0=tắt)
    "fb_comment_delay_max_s":       0,      # P4.3: max delay s trước comment FB (recommend 30-180)
    # Cột
    "col_video_drive":         "video short",
    "col_schedule_time":       "schedule_time",
    "col_title":               "Tieu_de_SEO",
    "col_description":         "Mo_ta",
    "col_keywords":            "Tu_Khoa_Chinh",
    "col_thumbnail_url":       "Link_anh_Thumb",
    "col_comment":             "Binh_luan_video",
    "col_target_page":         "target_page",
    "col_status":              "status",
    "col_error":               "error_message",
    "col_fb_link":             "VIDEO_URL",
    "col_fb_video_id":         "fb_video_id",
    "col_uploaded_at":         "uploaded_at",
    "col_upload_duration":     "upload_duration_s",
    "col_post_type":           "post_type",
    "col_insights_at":         "insights_at",
    "col_views":               "views",
    "col_reach":               "reach",
    "col_reactions":           "reactions",
    "col_comments_count":      "comments_count",
    "col_shares":              "shares",
    "col_minutes_viewed":      "minutes_viewed",
    "insights_min_age_h":         24,
    "insights_scan_interval_s":   1800,
    "max_retries":                   3,
    # Telegram notifications
    "telegram_bot_token":            "",
    "telegram_chat_id":              "",
    "notify_on_error":               True,
    "notify_on_token_expiry":        True,
    "notify_on_complete":            False,
    # Misc
    "temp_video_dir":                "temp_videos",
    "delete_video_after_upload":     True,
    "verify_video_after_upload":     True,
    "page_mapping":                  [],
    # TikTok
    "tiktok_client_key":             "",
    "tiktok_client_secret":          "",
    "tiktok_scopes":                 "user.info.basic,video.upload,video.publish",
    "tiktok_privacy_level":          "SELF_ONLY",
    "tiktok_disable_duet":           False,
    "tiktok_disable_comment":        False,
    "tiktok_disable_stitch":         False,
    "tiktok_poll_interval_s":        5,
    "tiktok_upload_timeout_s":       600,
    "tiktok_request_timeout_s":      60,
    # TikTok columns
    "col_platform":                  "platform",
    "col_tiktok_link":               "tiktok_link",
    "col_tiktok_id":                 "tiktok_id",
    "col_tiktok_account":            "tiktok_account",
    "col_tiktok_status":             "tiktok_status",
    "col_tiktok_confirmed_at":       "tiktok_confirmed_at",
    "col_tiktok_privacy":            "tiktok_privacy_level",
    "col_tiktok_ai_content":         "tiktok_is_ai_generated",
    "col_tiktok_commercial":         "tiktok_commercial_content",
    # TikTok publish control (audit flags)
    "tiktok_publish_mode":           "draft_upload",
    "tiktok_audit_approved":         False,
    "tiktok_enable_direct_post":     False,
    "tiktok_require_user_confirm":   True,
    # App identity (for TikTok audit submission)
    "app_name":                      "LTTStudio VideoBot",
    "app_support_email":             "support@lttstudios.com",
    "app_privacy_policy_url":        "https://lttstudios.com/legal/privacy.html",
    "app_terms_url":                 "https://lttstudios.com/legal/terms.html",
}
