"""
Demo Video v3 — Scene Configuration
─────────────────────────────────────
Aligned with TikTok Content Posting API Direct Post audit requirements:
  REQ-1: TikTok authorization page user flow         → Scene 5
  REQ-2: Export/Post-to-TikTok page on your app      → Scenes 8, 9
  REQ-3: User flow AFTER Post-to-TikTok triggered    → Scenes 10, 11
  REQ-4: Content Sharing Guidelines compliance       → Scenes 2, 9, 12

Design principles:
  - Each TikTok requirement has a DEDICATED scene reviewer can identify clearly
  - Voice MP3 duration drives scene duration (auto-advance when audio ends)
  - All English voice (TikTok reviewers international) with VI alternative
  - Total target: ~3:00 minute video (audit sweet spot 1-5 min)

Edit this file to tweak content/timing without touching tools.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Scene:
    """One scene in the demo video."""
    id:           str                # short identifier (used for output filenames)
    title:        str                # short title for teleprompter UI
    duration_s:   float              # planned duration (used as fallback if no MP3)
    voice_en:     str                # voice-over text in English
    voice_vi:     str = ""           # optional Vietnamese alternative
    on_screen:    List[str] = field(default_factory=list)  # action checklist
    tt_req:       str = ""           # which TikTok requirement this maps to
    critical:     bool = False       # if true, reviewer focuses heavily here


# ─── 13 SCENES — TikTok audit aligned ────────────────────────────────────────

SCENES: List[Scene] = [
    # ── Scene 1: Intro slide (5s) ────────────────────────────────────────────
    Scene(
        id="01_intro",
        title="Intro slide",
        duration_s=6.0,
        voice_en=(
            "LTTStudio VideoBot. TikTok Content Posting API integration. "
            "Direct Post audit demonstration."
        ),
        voice_vi=(
            "LTTStudio VideoBot. Tích hợp TikTok Content Posting API. "
            "Demo audit Direct Post."
        ),
        on_screen=[
            "Display intro slide (auto-shown by runner if available)",
            "OR display blank desktop wallpaper",
        ],
    ),

    # ── Scene 2: Privacy + Terms compliance proof (22s) ──────────────────────
    Scene(
        id="02_privacy_terms",
        title="Privacy Policy + Terms walkthrough",
        duration_s=22.0,
        tt_req="REQ-4: Content Sharing Guidelines compliance",
        voice_en=(
            "Before connecting any TikTok account, our published Privacy Policy at "
            "lttstudios.com slash legal slash privacy explicitly lists every piece of "
            "TikTok data we access: open ID, display name, avatar URL, access token, "
            "and refresh token. All tokens are encrypted at rest using Fernet, "
            "machine-bound, and never leave the user's computer. "
            "Terms of Service are at the same domain."
        ),
        voice_vi=(
            "Privacy Policy của chúng tôi tại lttstudios.com/legal/privacy.html liệt kê "
            "rõ mọi dữ liệu TikTok ta access: open_id, display_name, avatar, "
            "access_token, refresh_token. Token mã hóa bằng Fernet, gắn với máy, "
            "không rời máy user. Terms of Service cũng tại domain này."
        ),
        on_screen=[
            "Open Chrome Incognito (Ctrl+Shift+N)",
            "Navigate: https://lttstudios.com/legal/privacy.html",
            "Scroll slowly through section '4b. TikTok data' (~6s)",
            "Switch tab: https://lttstudios.com/legal/terms.html",
            "Brief scroll showing Terms exist (~4s)",
        ],
    ),

    # ── Scene 3: Bot overview (10s) ──────────────────────────────────────────
    Scene(
        id="03_bot_overview",
        title="Bot interface tour",
        duration_s=10.0,
        voice_en=(
            "This is LTTStudio VideoBot. The interface has dedicated tabs for "
            "TikTok account management, manual posting, and an audit compliance dashboard. "
            "We start by connecting a TikTok account."
        ),
        voice_vi=(
            "Đây là LTTStudio VideoBot. Có các tab quản lý tài khoản TikTok, "
            "đăng thủ công, và dashboard audit compliance. Bắt đầu bằng kết nối TikTok."
        ),
        on_screen=[
            "Bring LTTStudio VideoBot to foreground (Alt+Tab if needed)",
            "Pan slowly across all tabs",
            "Click tab '🎵 Tài khoản TikTok' (TikTok Accounts)",
            "Account list should be EMPTY (disconnect klcloset96 first if connected)",
        ],
    ),

    # ── Scene 4: OAuth app-side disclosure modal (15s) ───────────────────────
    Scene(
        id="04_oauth_app_disclosure",
        title="App-side OAuth disclosure modal",
        duration_s=15.0,
        critical=True,
        voice_en=(
            "Clicking 'Continue with TikTok' triggers our mandatory pre-authorization "
            "disclosure modal. The user sees every scope we will request, the exact "
            "reason for each, and instructions on how to revoke access later — both "
            "inside our app and through tiktok.com directly. The OAuth flow only starts "
            "after the user explicitly clicks 'Continue'."
        ),
        voice_vi=(
            "Click 'Continue with TikTok' mở modal disclosure bắt buộc. User thấy mọi "
            "scope ta yêu cầu, lý do, và cách thu hồi quyền sau này. Chỉ khi user "
            "explicit click 'Tiếp tục', OAuth mới bắt đầu."
        ),
        on_screen=[
            "Click button 'Continue with TikTok' (purple, official TikTok logo)",
            "PAUSE 3s: Disclosure modal opens — 3 scopes + reasons visible",
            "PAUSE 4s: Show revocation instructions section",
            "Click '✓ Tôi đồng ý — Tiếp tục đăng nhập TikTok →'",
        ],
    ),

    # ── Scene 5: TikTok authorization page (15s) ⭐ TT REQ #1 ────────────────
    Scene(
        id="05_tiktok_authorize_page",
        title="TikTok authorization page (TT REQ #1)",
        duration_s=15.0,
        critical=True,
        tt_req="REQ-1: TikTok authorization page user flow",
        voice_en=(
            "The user is redirected to TikTok's official authorization page at "
            "tiktok.com slash v2 slash auth slash authorize. The user sees the requested "
            "scopes — user info basic, video upload, video publish — and clicks 'Authorize' "
            "to grant access. Our app uses PKCE for security throughout this flow."
        ),
        voice_vi=(
            "User được redirect tới trang authorize chính thức của TikTok tại "
            "tiktok.com/v2/auth/authorize. User thấy 3 scopes — user.info.basic, "
            "video.upload, video.publish — và click Authorize. Bot dùng PKCE bảo mật."
        ),
        on_screen=[
            "Browser opens TikTok auth page",
            "HIGHLIGHT URL bar showing 'tiktok.com/v2/auth/authorize/'",
            "PAUSE 5s: Show scopes list on TikTok page (3 scopes visible)",
            "User logs in if needed",
            "Click 'Authorize' button on TikTok page",
        ],
    ),

    # ── Scene 6: Callback + account connected (8s) ───────────────────────────
    Scene(
        id="06_callback_return",
        title="Callback redirect + account connected",
        duration_s=8.0,
        voice_en=(
            "TikTok redirects to our HTTPS callback page at lttstudios.com, which forwards "
            "the authorization code back to the local app. The TikTok account is now "
            "connected and appears in the account list with avatar and display name."
        ),
        voice_vi=(
            "TikTok redirect về HTTPS callback tại lttstudios.com, forward code về app "
            "local. Account TikTok đã kết nối, hiện trong list với avatar và display name."
        ),
        on_screen=[
            "Browser briefly shows lttstudios.com callback page (spinner)",
            "Auto-redirect back / dialog closes",
            "Back in bot: account klcloset96 appears in list with avatar",
            "Token info shown: Access Token = '23h remaining'",
        ],
    ),

    # ── Scene 7: Audit dashboard (12s) ───────────────────────────────────────
    Scene(
        id="07_audit_dashboard",
        title="Compliance dashboard",
        duration_s=12.0,
        voice_en=(
            "Inside the app we built a real-time audit compliance dashboard. It verifies "
            "every TikTok policy requirement — client credentials, HTTPS redirect URI, "
            "privacy and terms URLs reachable, scope set correctly, user-confirmation "
            "required, and safe defaults. All eleven checks pass."
        ),
        voice_vi=(
            "Bot có dashboard audit compliance thời gian thực. Verify mọi yêu cầu "
            "policy của TikTok: credentials, HTTPS redirect, privacy + terms URLs, scopes, "
            "user confirm, default an toàn. 11/11 checks pass."
        ),
        on_screen=[
            "Click tab '📋 TT Audit'",
            "PAUSE 3s: Show summary '✅ Ready to submit (11 checks pass)'",
            "PAUSE 5s: Show 11 green checkmarks in left panel",
            "Show right panel: 3 OAuth scopes with justifications",
        ],
    ),

    # ── Scene 8: Manual TikTok form ⭐ TT REQ #2 part 1 (15s) ────────────────
    Scene(
        id="08_manual_form",
        title="Post-to-TikTok form (TT REQ #2 part 1)",
        duration_s=15.0,
        critical=True,
        tt_req="REQ-2: Export/Post-to-TikTok page on your app",
        voice_en=(
            "To post a video, the user navigates to the Manual TikTok tab. The user selects "
            "a video file, types a title, chooses the target account from the dropdown, "
            "and selects Direct Post Public as the post type. Then clicks the Post to TikTok button."
        ),
        voice_vi=(
            "Để đăng video, user vào tab Manual TikTok. User chọn file video, gõ tiêu đề, "
            "chọn account từ dropdown, chọn Direct Post Public làm post type, "
            "rồi click nút Đăng TikTok."
        ),
        on_screen=[
            "Click tab '🎵 Manual TikTok'",
            "File Video: click 'Choose' → select demo MP4 (e.g. clip_02 (4).mp4)",
            "Title: type 'Bot demo direct public — <timestamp>'",
            "Account dropdown: select 'klcloset96'",
            "Post type dropdown: select 'Direct Post — Public'",
            "Click bottom-bar '🎵 Đăng TikTok' button",
        ],
    ),

    # ── Scene 9: Consent dialog ⭐⭐⭐ TT REQ #2 part 2 (35s) ─────────────────
    Scene(
        id="09_consent_dialog",
        title="Per-publish consent dialog (TT REQ #2 part 2)",
        duration_s=35.0,
        critical=True,
        tt_req="REQ-2: Export/Post-to-TikTok page on your app + REQ-4: Compliance",
        voice_en=(
            "Before any API call, this comprehensive consent dialog appears. The video "
            "summary at the top shows title, post type, and target account. "
            "The privacy dropdown is populated dynamically from TikTok's creator_info "
            "endpoint and shows all options the user is permitted: Public to everyone, "
            "Mutual follow friends, and Self only. It is never pre-set — the user must "
            "select. Three interaction toggles let the user allow comments, duets, and "
            "stitches. Two disclosure checkboxes capture AI-generated and branded-content "
            "declarations. Finally, the user must tick the compliance acknowledgement "
            "before the Confirm and Post button enables."
        ),
        voice_vi=(
            "Trước mọi API call, dialog consent này xuất hiện. Video summary trên cùng. "
            "Privacy dropdown populated từ creator_info, hiển thị options user được phép: "
            "Public to everyone, Mutual friends, Self only. Không bao giờ pre-set — user "
            "phải chọn. 3 toggle interaction (comment, duet, stitch). 2 checkbox disclosure "
            "(AI, branded). Checkbox compliance bắt buộc tick mới enable nút Confirm."
        ),
        on_screen=[
            "Status flashes 'Querying creator info from TikTok...'",
            "PAUSE 3s: Consent dialog opens",
            "Walk through dialog sections (top to bottom):",
            "  → Video summary (title, post_type, account)",
            "  → Privacy dropdown — CLICK to expand, SHOW 3 OPTIONS",
            "  → Close dropdown, select 'Public to everyone'",
            "  → Show 3 interaction toggles (all enabled by default)",
            "  → Show 2 content disclosure checkboxes (AI / Branded)",
            "  → Show compliance acknowledgement checkbox (UNTICKED)",
            "  → Try clicking Confirm button — it is DISABLED",
            "  → Tick compliance checkbox",
            "  → Confirm button ENABLES (color change visible)",
            "  → Click '✅ Confirm & Publish'",
        ],
    ),

    # ── Scene 10: Upload progress ⭐ TT REQ #3 (22s) ─────────────────────────
    Scene(
        id="10_upload_progress",
        title="Upload progress after action triggered (TT REQ #3)",
        duration_s=22.0,
        critical=True,
        tt_req="REQ-3: User flow after Post-to-TikTok action triggered",
        voice_en=(
            "After the user confirms, the bot calls TikTok's video init endpoint, "
            "uploads the file in chunks, and polls the publish status endpoint. "
            "The status bar shows each phase clearly: init, upload, processing, "
            "and finally publish complete. The publish ID and timestamp are logged "
            "to the audit trail for compliance."
        ),
        voice_vi=(
            "Sau khi user confirm, bot gọi TikTok video init endpoint, upload file theo "
            "chunks, poll publish status. Status bar hiển thị rõ: init, upload, processing, "
            "publish complete. Publish ID và timestamp log vào audit trail."
        ),
        on_screen=[
            "Status bar progression (real-time):",
            "  → 'Init direct upload (PUBLIC_TO_EVERYONE)...'",
            "  → 'Uploading video (1 chunk, 60 MB)...'",
            "  → 'Trạng thái: PROCESSING_UPLOAD'",
            "  → 'Trạng thái: PUBLISH_COMPLETE'",
            "  → '✅ Published successfully! publish_id=...'",
            "Right pane shows Result: status=success, publish_id, timestamp, URL",
        ],
    ),

    # ── Scene 11: Verify on TikTok PUBLIC (12s) ──────────────────────────────
    Scene(
        id="11_verify_public",
        title="Verify video is PUBLIC on TikTok",
        duration_s=12.0,
        voice_en=(
            "We verify the result by opening TikTok web in the browser. The video appears "
            "on the user's profile feed exactly as configured — public to everyone, with "
            "the chosen interaction settings. The audit log file records every detail of "
            "this publish event for transparency."
        ),
        voice_vi=(
            "Verify bằng cách mở TikTok web trong browser. Video xuất hiện trên profile "
            "user — public, đúng interaction settings. Audit log file ghi mọi chi tiết "
            "publish event để minh bạch."
        ),
        on_screen=[
            "Open Chrome → tiktok.com/@klcloset96 (or paste video URL)",
            "Show video on profile (top position)",
            "PAUSE 3s: Click video → show 'Public' privacy badge",
            "Optional: open audit_log.jsonl in text editor → show latest entries",
        ],
    ),

    # ── Scene 12: Disconnect / revoke flow (12s) ─────────────────────────────
    Scene(
        id="12_disconnect",
        title="Disconnect + revoke",
        duration_s=12.0,
        tt_req="REQ-4: Content Sharing Guidelines — user control",
        voice_en=(
            "Users can disconnect at any time. The bot calls TikTok's revoke endpoint, "
            "then deletes the encrypted token from disk. The account is fully removed. "
            "Users can also revoke our app directly from tiktok.com slash setting slash "
            "manage apps."
        ),
        voice_vi=(
            "User có thể disconnect bất cứ lúc nào. Bot gọi TikTok revoke endpoint, "
            "xóa token mã hóa khỏi disk. Account bị xóa hoàn toàn. User cũng có thể "
            "revoke trực tiếp từ tiktok.com/setting/manage-apps."
        ),
        on_screen=[
            "Switch back to bot — tab '🎵 Tài khoản TikTok'",
            "Click account klcloset96 in list",
            "Right panel shows account details",
            "Click '🗑 Ngắt kết nối' button at bottom (red)",
            "Confirmation dialog → click 'Yes / Confirm'",
            "Account removed from list (empty state)",
        ],
    ),

    # ── Scene 13: Outro slide (5s) ───────────────────────────────────────────
    Scene(
        id="13_outro",
        title="Closing",
        duration_s=5.0,
        voice_en=(
            "Thank you for reviewing LTTStudio VideoBot. "
            "Documentation at lttstudios.com."
        ),
        voice_vi=(
            "Cảm ơn đã review LTTStudio VideoBot. "
            "Tài liệu tại lttstudios.com."
        ),
        on_screen=[
            "Display outro slide (auto if available)",
            "Or blank desktop with title visible",
        ],
    ),
]


def total_duration_s() -> float:
    return sum(s.duration_s for s in SCENES)


def critical_scenes() -> List[Scene]:
    return [s for s in SCENES if s.critical]


def tt_req_mapping() -> dict:
    """Group scenes by TikTok requirement for audit cross-reference."""
    mapping: dict[str, list[str]] = {}
    for s in SCENES:
        if s.tt_req:
            for req in s.tt_req.split("+"):
                req = req.strip()
                mapping.setdefault(req, []).append(s.id)
    return mapping


if __name__ == "__main__":
    print(f"Total scenes: {len(SCENES)}")
    print(f"Total duration: {total_duration_s():.1f}s ({total_duration_s()/60:.1f} min)")
    print(f"Critical scenes: {len(critical_scenes())}")
    print()
    print("TikTok requirement mapping:")
    for req, scenes in tt_req_mapping().items():
        print(f"  {req}")
        for sid in scenes:
            print(f"    → {sid}")
    print()
    print("All scenes:")
    for s in SCENES:
        marker = "⭐" if s.critical else "  "
        print(f"  {marker} [{s.id}] {s.duration_s:5.1f}s — {s.title}")
