# App Review Submission — Final Copy (3 permissions)

> App: **LTTStudios VideoBot** · App ID `2021063792619148`
> Scope submitted: `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`
> Comment feature (`pages_manage_engagement`) is DISABLED in this build (`fb_comment_enabled=false`) and is NOT part of this submission.
> Domain of record: **lttstudios.com**

---

## App summary (paste in the app overview / "What does your app do")

LTTStudios VideoBot is a **desktop application** (Windows) that lets a video
content creator bulk-publish their own pre-recorded videos to the Facebook
Pages they administer. The creator supplies every video file and caption; the
app authenticates the creator via Facebook Login, lists the Pages they manage,
publishes videos to a selected Page via the official Graph video endpoints, and
reads back engagement metrics so the creator can track performance. All data is
stored locally on the creator's machine — there is no LTTStudios server.

**What the app does NOT do:** no Instagram, Messenger, Ads, or Business
management; no posting without the creator's explicit per-row queue; no
collection of user PII beyond Page name and Page ID; no third-party data sharing.

---

## 1. `pages_show_list`

**How the app uses this permission**
> After the creator authenticates with Facebook Login, the app calls
> `GET /me/accounts` to retrieve the list of Pages the creator administers, so
> they can choose which Page to publish to. The app stores only the `id`,
> `name`, and `access_token` of the selected Pages, encrypted locally with
> AES-128 (Fernet), bound to the machine.

**Reviewer flow (shown in screencast 1)**
1. Open the app, go to the "Facebook Accounts" tab, click "Connect Facebook Account".
2. A browser opens the Facebook Login dialog; the test user logs in and grants the permission.
3. The app displays the list of Pages the test user manages (Page name + thumbnail).
4. The test user ticks the Page(s) to enable and clicks Save.

**Why Advanced Access is required**
Creators manage multiple brand Pages. Without `pages_show_list` the app cannot
show the Page picker and the entire workflow is impossible.

---

## 2. `pages_manage_posts`

**How the app uses this permission**
> This is the core feature. The creator selects a local video file (or one from
> their own Google Drive), enters a title and description, and the app publishes
> the video to the target Page using the resumable video endpoints:
> `POST /{page_id}/videos` (3-phase start/transfer/finish) for feed videos and
> `POST /{page_id}/video_reels` for Reels. Scheduled publishing is supported via
> the `scheduled_publish_time` parameter when the creator schedules content.

**Reviewer flow (shown in screencast 2)**
1. Open the "Manual FB" tab.
2. Select the connected test Page, choose a local video file, and enter a title/description.
3. Click "Publish to Facebook". The log shows the 3-phase resumable upload (0→100%).
4. On success the app displays the resulting Facebook video URL.
5. Open the test Page on facebook.com — the published video appears.

*(The app also supports bulk publishing from a Google Sheet queue, but the single-video Manual flow above is the simplest way to reproduce pages_manage_posts.)*

**Why Advanced Access is required**
Publishing video to the creator's Pages is the reason the app exists. Without
Advanced Access the post is only visible to app-role users, defeating the tool.

**Client-side safeguards (we are a respectful integration)**
- Minimum 4 hours between posts on the same Page.
- Minimum 15 minutes between posts on different Pages.
- Maximum 3 posts per Page per day; active hours 07:00–22:00 only.
- Exponential backoff on Graph error codes 4 / 17 / 32 (rate limit) and 368 (spam).
- Per-account request throttling and a circuit breaker that pauses on error spikes.

---

## 3. `pages_read_engagement`

**How the app uses this permission**
> After a video is published, the app fetches engagement metrics so the creator
> can see how the content performs. It calls
> `GET /{video_id}?fields=reactions.summary(true),comments.summary(true),shares`
> and `GET /{video_id}/video_insights?metric=post_impressions_unique,post_video_views,post_video_view_time`.
> A background task refreshes metrics every 30 minutes, starting ~24 hours after
> publish. Results populate a read-only analytics table in the app.

**Reviewer flow (shown in screencast 3)**
1. Open the "Monitor" tab, click Refresh.
2. The table populates: video URL | views | reach | reactions | comments | shares | minutes viewed.
3. Click a row to open the corresponding post on Facebook.

**Why Advanced Access is required**
Analytics are only useful across the Pages the creator manages, not just the
app admin's own posts.

---

## Test instructions (paste into "Instructions for testing")

    APP TYPE: Windows desktop application. A screencast of the full flow is
    attached for each permission. To reproduce live, run the provided portable
    build; otherwise the screencast demonstrates every step end to end.

    TEST USER:  <fill: FB test user email>  /  <fill: password>
    TEST PAGE:  "LTTStudios Reviewer Test Page" (ID: <fill>)
                The test user is an admin of this Page.

    STEPS
    1. Launch the app → "Facebook Accounts" → "Connect Facebook Account".
    2. Log in as the test user, approve pages_show_list + pages_manage_posts +
       pages_read_engagement.
    3. Verify the test Page appears in the list (pages_show_list). Tick it, Save.
    4. Open the "Manual FB" tab → select the test Page → choose the bundled
       sample video file → enter a title/description.
    5. Click "Publish to Facebook". After ~1-2 minutes the video appears on the
       test Page (pages_manage_posts).
    6. "Monitor" tab → Refresh → metrics table shows data for the test video
       (pages_read_engagement).

    DATA HANDLING
    - Page access tokens: stored locally, AES-128 Fernet, bound to machine GUID.
    - No LTTStudios server; no third-party sharing; no PII beyond Page id/name.
    - Data deletion: https://lttstudios.com/legal/data-deletion.html
    - Privacy: https://lttstudios.com/legal/privacy.html
    - Terms: https://lttstudios.com/legal/terms.html

    CONTACT: akakenly.design@gmail.com · support@lttstudios.com
