"""
TikTok creator info query — required by audit before publish.

TikTok Content Posting API audit requirement: app phải gọi
`/v2/post/publish/creator_info/query/` TRƯỚC khi hiển thị publish dialog,
để lấy:
  • privacy_level_options — danh sách privacy mà tài khoản user được phép
    chọn (phụ thuộc account-level setting + audit status của app)
  • comment_disabled / duet_disabled / stitch_disabled — toggle setting của
    creator (nếu creator tắt comment ở tài khoản, app KHÔNG được override
    bằng cách bật lại)
  • max_video_post_duration_sec — giới hạn duration cho account này
  • creator_username / creator_nickname / creator_avatar_url — để show
    trong confirm dialog

Audit reject ngay nếu thấy app pre-set privacy hoặc bypass creator toggle.

Reference:
  https://developers.tiktok.com/doc/content-posting-api-reference-query-creator-info
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from core.tiktok.client import TikTokClient, TikTokError

log = logging.getLogger(__name__)


@dataclass
class CreatorInfo:
    """Snapshot creator capabilities + restrictions tại thời điểm query.

    Bot phải dùng các field này làm SOURCE OF TRUTH cho publish dialog —
    không được hardcode hoặc cache lâu (TT setting có thể thay đổi).
    """
    creator_username:               str = ""
    creator_nickname:               str = ""
    creator_avatar_url:             str = ""
    privacy_level_options:          list[str] = field(default_factory=list)
    comment_disabled:               bool = False
    duet_disabled:                  bool = False
    stitch_disabled:                bool = False
    max_video_post_duration_sec:    int = 600

    @property
    def has_public_option(self) -> bool:
        """True nếu account được phép đăng PUBLIC_TO_EVERYONE.
        Sandbox/unaudited app chỉ có SELF_ONLY trong list này."""
        return "PUBLIC_TO_EVERYONE" in self.privacy_level_options

    def safe_default_privacy(self) -> str:
        """Privacy default an toàn nhất cho user.

        Theo TT policy: nếu app unaudited (chỉ SELF_ONLY khả dụng) → trả
        về SELF_ONLY. Nếu audited → vẫn trả SELF_ONLY làm default (user
        chủ động chuyển sang PUBLIC nếu muốn).
        """
        if "SELF_ONLY" in self.privacy_level_options:
            return "SELF_ONLY"
        # Edge case: API trả về list không có SELF_ONLY → fallback option đầu
        return self.privacy_level_options[0] if self.privacy_level_options else "SELF_ONLY"


def query_creator_info(
    access_token: str,
    *,
    timeout_s: int = 15,
    on_log=None,
) -> CreatorInfo:
    """Gọi API creator_info/query với access_token + parse response.

    Raises
    ------
    TikTokError nếu API trả lỗi (token revoked / scope thiếu / network).

    Returns
    -------
    CreatorInfo dataclass. Field còn thiếu trong response → fallback an toàn.
    """
    client = TikTokClient(
        access_token=access_token,
        on_log=on_log or (lambda msg, lvl: None),
        timeout=timeout_s,
    )
    # Endpoint trả về dạng {data: {...}, error: {code, message}}
    resp = client.post(
        "/v2/post/publish/creator_info/query/",
        payload={},   # endpoint không cần body nhưng phải POST với content-type JSON
    )

    if not isinstance(resp, dict):
        raise TikTokError("creator_info trả về không phải JSON object")

    info = CreatorInfo(
        creator_username=str(resp.get("creator_username", "") or ""),
        creator_nickname=str(resp.get("creator_nickname", "") or ""),
        creator_avatar_url=str(resp.get("creator_avatar_url", "") or ""),
        privacy_level_options=list(resp.get("privacy_level_options", []) or []),
        comment_disabled=bool(resp.get("comment_disabled", False)),
        duet_disabled=bool(resp.get("duet_disabled", False)),
        stitch_disabled=bool(resp.get("stitch_disabled", False)),
        max_video_post_duration_sec=int(
            resp.get("max_video_post_duration_sec", 600) or 600
        ),
    )

    # Nếu API không trả privacy_level_options (rare), default sang SELF_ONLY
    if not info.privacy_level_options:
        info.privacy_level_options = ["SELF_ONLY"]
        log.warning(
            "creator_info.privacy_level_options empty — falling back to ['SELF_ONLY']. "
            "App có thể chưa được TikTok audit duyệt cho PUBLIC."
        )

    return info


# Vietnamese labels cho từng privacy option (DEPRECATED — dùng label_for_privacy())
# Giữ lại cho backward compat với code cũ + tests; label_for_privacy() đã chuyển
# sang i18n.
PRIVACY_LABELS_VI: dict[str, str] = {
    "SELF_ONLY":             "🔒  Chỉ mình tôi xem (SELF_ONLY)",
    "MUTUAL_FOLLOW_FRIENDS": "🤝  Bạn bè cùng follow (MUTUAL_FOLLOW_FRIENDS)",
    "FOLLOWER_OF_CREATOR":   "👥  Người theo dõi (FOLLOWER_OF_CREATOR)",
    "PUBLIC_TO_EVERYONE":    "🌐  Công khai (PUBLIC_TO_EVERYONE)",
}

# Map TikTok privacy enum → i18n key (resolved per-call via t())
_PRIVACY_I18N_KEYS: dict[str, str] = {
    "SELF_ONLY":             "privacy.self_only",
    "MUTUAL_FOLLOW_FRIENDS": "privacy.mutual_friends",
    "FOLLOWER_OF_CREATOR":   "privacy.followers",
    "PUBLIC_TO_EVERYONE":    "privacy.public",
}


def label_for_privacy(value: str) -> str:
    """Get localized label for a TikTok privacy enum.

    i18n: returns English by default, Vietnamese if user switched language.
    Fallback to raw enum if neither i18n key nor legacy VI label exists.
    """
    key = _PRIVACY_I18N_KEYS.get(value)
    if key:
        try:
            from core.i18n import t
            return t(key, default=value)
        except Exception:
            pass
    return PRIVACY_LABELS_VI.get(value, value)
