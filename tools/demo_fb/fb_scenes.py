"""
Facebook App Review — Screencast Scene Configuration
─────────────────────────────────────────────────────
THREE separate videos, one per permission requested for Advanced Access:

  VIDEO 1  →  pages_show_list        (connect account + list Pages)
  VIDEO 2  →  pages_manage_posts     (publish a video to a Page)
  VIDEO 3  →  pages_read_engagement  (read insights)

Each Scene carries voice-over text (EN + VI) and an on-screen action checklist.
The MP3 duration drives scene timing (auto-advance) in teleprompter.py.

Record ONE video at a time:
    teleprompter.py --video 1   → record → save as pages_show_list.mp4
    teleprompter.py --video 2   → record → save as pages_manage_posts.mp4
    teleprompter.py --video 3   → record → save as pages_read_engagement.mp4

Edit this file to tweak wording/timing without touching the tools.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Scene:
    id:         str                 # output filename stem (also MP3 name)
    video:      int                 # which of the 3 videos this belongs to (1/2/3)
    permission: str                 # the permission this video demonstrates
    title:      str                 # teleprompter title
    duration_s: float               # fallback duration if no MP3
    voice_en:   str                 # English narration (reviewers international)
    voice_vi:   str = ""            # Vietnamese alternative
    on_screen:  List[str] = field(default_factory=list)


# ─── VIDEO 1 — pages_show_list ────────────────────────────────────────────────
VIDEO_1: List[Scene] = [
    Scene(
        id="v1_01_intro", video=1, permission="pages_show_list",
        title="Intro — pages_show_list", duration_s=6.0,
        voice_en=(
            "LTTStudios VideoBot. Facebook Graph API integration. "
            "This clip demonstrates the pages underscore show underscore list permission."
        ),
        voice_vi=(
            "LTTStudios VideoBot, tích hợp Facebook Graph API. "
            "Clip này minh họa quyền pages_show_list."
        ),
        on_screen=[
            "Bot open on the '🔐 Tài khoản FB' (Facebook Accounts) tab",
            "Account list is EMPTY (disconnect first if needed)",
        ],
    ),
    Scene(
        id="v1_02_connect", video=1, permission="pages_show_list",
        title="Connect Facebook — OAuth consent", duration_s=18.0,
        voice_en=(
            "The user clicks Connect Facebook Account. The browser opens Facebook's "
            "official login and consent screen, where the user grants three permissions: "
            "pages underscore show underscore list, pages underscore manage underscore posts, "
            "and pages underscore read underscore engagement. The user clicks Continue."
        ),
        voice_vi=(
            "User bấm Kết nối tài khoản Facebook. Trình duyệt mở màn đăng nhập và cấp quyền "
            "chính thức của Facebook, user cấp 3 quyền: pages_show_list, pages_manage_posts, "
            "pages_read_engagement, rồi bấm Continue."
        ),
        on_screen=[
            "Click '➕ Kết nối tài khoản Facebook'",
            "Browser opens Facebook login/consent",
            "PAUSE ~4s: the 3 requested permissions are visible on the consent screen",
            "Click 'Continue' / 'Tiếp tục'",
        ],
    ),
    Scene(
        id="v1_03_pages_list", video=1, permission="pages_show_list",
        title="Pages list appears", duration_s=14.0,
        voice_en=(
            "The app calls GET slash me slash accounts and displays the list of Pages the "
            "user manages, each with its name and category. The user ticks the Pages to "
            "enable for publishing. This is exactly what pages underscore show underscore "
            "list is used for."
        ),
        voice_vi=(
            "App gọi GET /me/accounts và hiển thị danh sách Page user quản lý, kèm tên và "
            "category. User tick chọn Page để dùng. Đây chính là công dụng của pages_show_list."
        ),
        on_screen=[
            "Back in the app: the Pages list is now populated (name + category + Page ID)",
            "PAUSE 3s: show the list clearly",
            "Tick one Page → the 'N/N page được chọn' counter updates",
        ],
    ),
]

# ─── VIDEO 2 — pages_manage_posts ─────────────────────────────────────────────
VIDEO_2: List[Scene] = [
    Scene(
        id="v2_01_intro", video=2, permission="pages_manage_posts",
        title="Intro — pages_manage_posts", duration_s=6.0,
        voice_en=(
            "This clip demonstrates the pages underscore manage underscore posts permission "
            "— publishing a video to a Facebook Page the user manages."
        ),
        voice_vi=(
            "Clip này minh họa quyền pages_manage_posts — đăng một video lên Trang Facebook "
            "mà user quản lý."
        ),
        on_screen=[
            "Bot open on the 'Manual FB' tab",
        ],
    ),
    Scene(
        id="v2_02_form", video=2, permission="pages_manage_posts",
        title="Fill the publish form", duration_s=16.0,
        voice_en=(
            "On the Manual FB tab, the user selects the target Page, chooses a local video "
            "file, and enters a title and description. Privacy is set to Public."
        ),
        voice_vi=(
            "Ở tab Manual FB, user chọn Trang đích, chọn file video trên máy, nhập tiêu đề "
            "và mô tả. Quyền riêng tư đặt Công khai."
        ),
        on_screen=[
            "Account dropdown: select the connected account",
            "Page dropdown: select the target test Page",
            "Video: click '📁 Chọn' → pick a short local MP4 (10-30s)",
            "Type a Title and a Description",
            "Privacy = 'Công khai' (Public / EVERYONE)",
        ],
    ),
    Scene(
        id="v2_03_publish", video=2, permission="pages_manage_posts",
        title="Publish — resumable upload", duration_s=22.0,
        voice_en=(
            "The user clicks Publish to Facebook. The app calls POST slash Page-ID slash "
            "videos using the resumable upload protocol — start, transfer, and finish phases. "
            "The log shows the upload progressing from zero to one hundred percent, then the "
            "resulting Facebook video URL."
        ),
        voice_vi=(
            "User bấm Đăng Facebook. App gọi POST /{page-id}/videos theo giao thức resumable "
            "upload — start, transfer, finish. Log hiển thị tiến trình 0 đến 100%, rồi hiện "
            "link video Facebook."
        ),
        on_screen=[
            "Click '🎬 Đăng Facebook'",
            "Log panel: upload phases 0% → 100%",
            "Log: '✅ Upload xong: facebook.com/...'",
        ],
    ),
    Scene(
        id="v2_04_verify", video=2, permission="pages_manage_posts",
        title="Verify on the Page", duration_s=12.0,
        voice_en=(
            "We open the Page in a browser and confirm the video has been published to the "
            "Page. This is the core function pages underscore manage underscore posts enables."
        ),
        voice_vi=(
            "Ta mở Trang trên trình duyệt và xác nhận video đã được đăng lên Trang. Đây là "
            "chức năng cốt lõi mà pages_manage_posts cho phép."
        ),
        on_screen=[
            "Open a browser, paste the video URL (or open the test Page)",
            "PAUSE 4s: the published video is visible on the Page",
        ],
    ),
]

# ─── VIDEO 3 — pages_read_engagement ──────────────────────────────────────────
VIDEO_3: List[Scene] = [
    Scene(
        id="v3_01_intro", video=3, permission="pages_read_engagement",
        title="Intro — pages_read_engagement", duration_s=6.0,
        voice_en=(
            "This clip demonstrates the pages underscore read underscore engagement "
            "permission — reading engagement metrics for the Page's videos."
        ),
        voice_vi=(
            "Clip này minh họa quyền pages_read_engagement — đọc số liệu tương tác cho "
            "video của Trang."
        ),
        on_screen=[
            "Bot open on the 'Monitor' tab",
        ],
    ),
    Scene(
        id="v3_02_insights", video=3, permission="pages_read_engagement",
        title="Read insights", duration_s=18.0,
        voice_en=(
            "On the Monitor tab the user clicks Refresh. The app calls GET slash video-ID "
            "slash video underscore insights and the reactions, comments and shares fields, "
            "then fills a read-only table with views, reach, reactions, comments and shares. "
            "This is what pages underscore read underscore engagement is used for."
        ),
        voice_vi=(
            "Ở tab Monitor user bấm Refresh. App gọi GET /{video-id}/video_insights cùng các "
            "trường reactions, comments, shares, rồi điền bảng chỉ-đọc: views, reach, "
            "reactions, comments, shares. Đây là công dụng của pages_read_engagement."
        ),
        on_screen=[
            "Click 'Refresh' on the Monitor tab",
            "PAUSE 4s: the metrics table populates (views/reach/reactions/comments/shares)",
            "Optionally click a row → opens the post on facebook.com",
        ],
    ),
]

ALL_SCENES: List[Scene] = VIDEO_1 + VIDEO_2 + VIDEO_3

VIDEO_TITLES = {
    1: "pages_show_list",
    2: "pages_manage_posts",
    3: "pages_read_engagement",
}


def scenes_for_video(n: int) -> List[Scene]:
    return [s for s in ALL_SCENES if s.video == n]


if __name__ == "__main__":
    for v in (1, 2, 3):
        scs = scenes_for_video(v)
        total = sum(s.duration_s for s in scs)
        print(f"VIDEO {v} — {VIDEO_TITLES[v]}: {len(scs)} scenes, ~{total:.0f}s")
        for s in scs:
            print(f"   [{s.id}] {s.duration_s:4.0f}s — {s.title}")
