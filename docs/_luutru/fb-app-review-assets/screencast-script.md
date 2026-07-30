# Screencast Script — LTTStudios VideoBot App Review

> Record with **OBS Studio** (free) or Windows 11 Snipping Tool (video mode).
> Settings: 1280×720, 30fps, cursor visible, NO audio needed.
> Account used on screen: **Liên Nguyễn** (Admin on the app). Use a dedicated
> test Page or an existing Page — you can delete the test post afterward.
> Add a 1-line text overlay at the start of each clip (e.g. in OBS a Text source).
> Export H.264 MP4, keep each file < 25 MB.

---

## VIDEO 1 — `pages_show_list`  (~25s)

Purpose: show the user authenticating and the app listing the Pages they manage.

| Time | Action on screen | Overlay text |
|------|------------------|--------------|
| 0:00 | Bot open on the **"Tài khoản FB"** (Facebook Accounts) tab | "LTTStudios VideoBot — connecting a Facebook account" |
| 0:03 | (If Liên Nguyễn already connected: click **Ngắt kết nối** first so the fresh consent shows) | |
| 0:05 | Click **"➕ Kết nối tài khoản Facebook"** — browser opens the FB login/consent | |
| 0:10 | On the Facebook dialog, the requested permissions are visible → click **Continue/Tiếp tục** | "User grants pages_show_list + pages_manage_posts + pages_read_engagement" |
| 0:16 | Back in the app — the list of Pages the user manages appears (names + thumbnails) | "App calls GET /me/accounts → lists the Pages" |
| 0:20 | Tick the test Page → the "N/N page được chọn" counter updates | |
| 0:25 | END | |

---

## VIDEO 2 — `pages_manage_posts`  (~40s)

Purpose: show the app publishing a video to a Page the user manages.

| Time | Action on screen | Overlay text |
|------|------------------|--------------|
| 0:00 | Switch to the **"Manual FB"** tab | "Publishing a video to a Page" |
| 0:04 | Select the account **Liên Nguyễn** + the **test Page** in the dropdowns | |
| 0:08 | Click **Chọn** → pick a short local video file (10–30s) | |
| 0:12 | Type a **Title** and **Description** | |
| 0:16 | Privacy = **Công khai (EVERYONE)** | "post_type = feed, privacy = public" |
| 0:18 | Click **"🎬 Đăng Facebook"** | "App calls POST /{page_id}/videos (resumable)" |
| 0:22 | Log panel shows the upload phases 0→100% and "✅ Upload xong: facebook.com/…" | |
| 0:34 | Open a browser, go to the test Page → the published video appears | "Video is now on the Page" |
| 0:40 | END | |

---

## VIDEO 3 — `pages_read_engagement`  (~20s)

Purpose: show the app reading engagement metrics for the Page's videos.

| Time | Action on screen | Overlay text |
|------|------------------|--------------|
| 0:00 | Switch to the **"Monitor"** tab | "Reading engagement insights" |
| 0:03 | Click **Refresh** | "App calls GET /{video_id}/video_insights + reactions/comments/shares" |
| 0:08 | The table populates: video URL · views · reach · reactions · comments · shares | |
| 0:15 | Click a row → it opens the post on facebook.com | |
| 0:20 | END | |

---

## Do / Don't
- DO show only the test environment — avoid other real brand Pages appearing on screen.
- DO NOT show any password, token, or the App Secret on screen.
- DO keep clips short and cursor movements clear.
- File names: `pages_show_list.mp4`, `pages_manage_posts.mp4`, `pages_read_engagement.mp4`.

## Reviewer note (Cách 2 — screencast primary)
Include this in the App Review "notes to reviewer":

    LTTStudios VideoBot is a Windows DESKTOP application used by the owner to
    publish their own videos to the Facebook Pages they administer. It cannot be
    run on a hosted URL, so a full end-to-end screencast is attached for each
    permission. The app authenticates via Facebook Login (screencast 1) and uses
    pages_manage_posts to publish videos (screencast 2) and pages_read_engagement
    to read insights (screencast 3). Note: Meta has temporarily disabled test-user
    creation platform-wide, so a synthetic test user could not be provided; the
    attached screencasts demonstrate the full flow end to end.
    Contact: letammeiu@gmail.com
