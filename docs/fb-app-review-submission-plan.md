# Facebook App Review Submission Plan — LTTStudio VideoBot

> **Mục tiêu**: Đưa app `Lttstudio` (ID `2021063792619148`) từ trạng thái **"Đã hủy đăng" (Development Mode)** lên **Live Mode** với Advanced Access cho mọi permission bot đang dùng.
>
> **Thời gian dự kiến tổng**: 2-4 tuần (1-3 ngày prep + 1-3 ngày business verification + 5-14 ngày Meta review).

---

## 0. Tóm tắt tình trạng hiện tại

| Chỉ số | Hiện tại | Đích |
|---|---|---|
| App Mode | ⚠️ Đã hủy đăng (Unpublished) | ✅ Live |
| Permissions với Advanced Access | 0 / 6 | 6 / 6 |
| Business Verification | ❌ Chưa | ✅ Verified |
| Data Deletion URL | ❌ Trống | ✅ Có |
| Use Cases configured | 1 (Pages API custom) | 1-2 (Pages + có thể thêm) |
| Số call API đã dùng | 589 (pages_*) | — |
| Roles trong app | 1 admin | + tester nội bộ |

---

## 1. Bot Function Inventory — Permissions Mapping

### 1.1 Facebook Use Case → Permissions cần Advanced Access

Bot dùng **Use Case "Pages API"** (đã tick xanh trong Dashboard). Use case này bundle 4 permission CỐT LÕI cộng 2 phụ trợ:

| Permission | Bot dùng để | API endpoints | Trạng thái cần |
|---|---|---|---|
| `pages_show_list` | Liệt kê Pages user admin sau OAuth | `GET /me/accounts` | **Advanced Access** |
| `pages_manage_posts` | Upload video feed/reels, schedule post | `POST /{page_id}/videos`, `POST /{page_id}/video_reels` | **Advanced Access** |
| `pages_read_engagement` | Đọc insights, reactions, comments count | `GET /{video_id}/video_insights`, `GET /{video_id}?fields=reactions.summary()` | **Advanced Access** |
| `pages_manage_engagement` | Post comment lên video | `POST /{video_id}/comments` | **Advanced Access** |
| `business_management` | Multi-app rotation (optional) | App-level metadata | Standard OK |
| `public_profile` + `email` | OAuth basic | `GET /me` | Standard (mặc định) |

### 1.2 Tính năng GUI map sang permission

| Tab GUI | Action | API call | Permission cần |
|---|---|---|---|
| FB Accounts | Connect (OAuth) | `oauth/access_token` + `/me/accounts` | `pages_show_list` |
| FB Accounts | Refresh token | `oauth/access_token` (`fb_exchange_token`) | (none extra) |
| Manual FB | Upload video | 3-phase `/{page_id}/videos` | `pages_manage_posts` |
| Manual FB | Upload Reels | 2-phase `/{page_id}/video_reels` | `pages_manage_posts` |
| Manual FB | Post comment | `POST /{video_id}/comments` | `pages_manage_engagement` |
| Sheet FB | Bulk publish (20 worker) | Như Manual × N | Cả 2 trên |
| Monitor | View insights | `GET /{video_id}/video_insights` | `pages_read_engagement` |
| Background | Insights fetcher (30') | Như Monitor | `pages_read_engagement` |
| Background | Token refresher (1h) | `oauth/access_token` | (none extra) |

### 1.3 Optional features chưa dùng (KHÔNG submit)

- ❌ Instagram cross-posting (`instagram_basic`, `instagram_content_publish`) — bot không hỗ trợ
- ❌ Ads management — bot không hỗ trợ
- ❌ Messenger / Webhooks — bot không hỗ trợ
- ❌ `pages_messaging` — bot không hỗ trợ

→ **Nguyên tắc**: chỉ request permission đang dùng. Permission thừa = lý do reject lớn nhất.

---

## 2. Pre-Submission Checklist (làm TRƯỚC khi submit)

### Phase A — App Settings (1-2 giờ)

| # | Task | Trạng thái | Hướng dẫn |
|---|---|---|---|
| A1 | Privacy Policy URL | ✅ Có | https://lttstudios.com/legal/privacy.html — verify còn live |
| A2 | Terms of Service URL | ✅ Có | https://lttstudios.com/legal/terms.html — verify còn live |
| A3 | **Data Deletion URL** | ❌ **Thiếu** | Phải tạo trang `/legal/data-deletion.html` |
| A4 | App Icon 1024×1024 | ✅ Có | logo LTT đã upload |
| A5 | App Category | ✅ "Tiện ích & Năng suất" | Giữ nguyên |
| A6 | Contact Email | ✅ letammeiu@gmail.com | OK |
| A7 | DPO contact (GDPR) | ✅ Đã điền | Giữ nguyên |
| A8 | App Domains | ⚠️ Verify | Phải có `lttstudios.com` trong list |
| A9 | OAuth Redirect URIs | ⚠️ Verify | Phải có `https://lttstudios.com/auth/fb-callback.html` |
| A10 | Long-form description (English) | ⚠️ Cần soạn | Xem template ở phần 4 |

### Phase B — Business Verification (1-3 ngày Meta xử lý)

| # | Task | Hướng dẫn |
|---|---|---|
| B1 | Tạo Meta Business Account | https://business.facebook.com — nếu chưa có |
| B2 | Verify Business Domain | Domain `lttstudios.com` — verify qua DNS TXT record (cách nhanh nhất) |
| B3 | Submit Business Verification | Upload giấy tờ: CCCD/Hộ chiếu cá nhân HOẶC GPKD công ty |
| B4 | Đợi Meta duyệt | 1-3 ngày làm việc thường |

### Phase C — Test environment cho reviewer (4-6 giờ)

| # | Task | Hướng dẫn |
|---|---|---|
| C1 | Tạo 1 Test Page riêng cho reviewer | Tên: "LTTStudio Reviewer Test Page" |
| C2 | Tạo Test User trong app | Roles → Người dùng thử → Add → đặt password tạm |
| C3 | Add test user vào test page làm Admin | Page Settings → Page Roles |
| C4 | Soạn Test Instructions (English) | Xem template Section 5 |
| C5 | Quay screencast cho từng permission | Xem Section 4 |

### Phase D — Backend prep

| # | Task | Hướng dẫn |
|---|---|---|
| D1 | Bot có rate-limit hợp lý | ✅ Đã có (4h/Page, 3 post/day) |
| D2 | Logging mọi API call để debug | ✅ Đã có (logs/app.log) |
| D3 | Error handling rõ ràng | ✅ Đã có (graph_client error codes) |
| D4 | Tạm dừng bot trong thời gian chờ review | ⚠️ Recommended — tránh spike API → bị flag |

---

## 3. Submission Workflow — 6 bước

```
┌─────────────────────────────────────────────────────────────────────┐
│ BƯỚC 1 — Fix app settings (A1-A10)                          1-2h    │
│   ↓                                                                  │
│ BƯỚC 2 — Submit Business Verification (B1-B4)               1-3 ngày│
│   ↓ (chờ Meta verify domain + identity)                              │
│ BƯỚC 3 — Tạo test environment (C1-C5)                       4-6h    │
│   ↓                                                                  │
│ BƯỚC 4 — Quay screencast (4 video × ~30s mỗi cái)          2-3h    │
│   ↓                                                                  │
│ BƯỚC 5 — Submit App Review qua dashboard                    1h      │
│   ↓ (chờ Meta review)                                                │
│ BƯỚC 6 — Wait → fix nếu reject → re-submit                  5-14 ngày│
│   ↓                                                                  │
│ ✅ App Live, bot hoạt động bình thường với public            ✓       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Permission Use Case Descriptions (English)

> Meta YÊU CẦU mô tả use case bằng **tiếng Anh** rõ ràng, cụ thể, không marketing-fluff. Reviewer là người thật, đọc 100 app/ngày — câu chữ rõ ràng sẽ giảm reject rate.

### 4.1 `pages_show_list`

**Permission purpose:**
> Our app allows content creators to publish video content to multiple Facebook Pages they manage from a single dashboard. After the creator authenticates via OAuth, we call `GET /me/accounts` to retrieve the list of Pages they admin so they can select which Page to publish to. We store only `page_id`, `page_name`, and the `access_token` returned by Facebook, encrypted locally using AES-128 (Fernet).

**User flow Meta reviewer will see in screencast:**
1. User opens our app, clicks "Connect Facebook Account"
2. Browser opens Facebook OAuth dialog, user logs in, grants `pages_show_list` permission
3. App displays the list of Pages the user manages (Page Name + thumbnail)
4. User checks the Pages they want to enable for publishing
5. App saves the encrypted page tokens locally

**Why we need Advanced Access:**
Creators typically manage multiple Pages across different brands. Without `pages_show_list`, the app cannot present the Page picker UI — the entire workflow is broken.

---

### 4.2 `pages_manage_posts`

**Permission purpose:**
> Our app publishes user-created video content to Facebook Pages owned by the creator. The creator uploads a video file (from their device or Google Drive), enters a title/description, and our app posts it via `POST /{page_id}/videos` (resumable upload, 3 phases: start/transfer/finish) or `POST /{page_id}/video_reels` for Reels format. We support scheduled publishing via `scheduled_publish_time` parameter when the creator wants to schedule content for off-hours.

**User flow:**
1. User opens "Bulk Upload" tab, points to a Google Sheet with rows of {video_url, title, description, schedule_time, target_page}
2. App reads each row, downloads video from creator's own Google Drive
3. App calls 3-phase upload to the target Page
4. App writes the resulting Facebook video URL back to the sheet
5. Logs the operation in audit_log.jsonl

**Why we need Advanced Access:**
This IS the core feature. The app exists to automate video publishing for content creators who manage many Pages.

**Rate limits we enforce client-side** (proves we're respectful):
- Min 4 hours between posts on the same Page
- Min 15 minutes between posts on different Pages  
- Max 3 posts per Page per day
- Active hours: 7am-10pm only
- Backoff on FB error codes 4/17/32 (rate-limit) and 368 (spam)

---

### 4.3 `pages_read_engagement`

**Permission purpose:**
> After a video is published, our app fetches engagement metrics so the creator can see how their content is performing. We call `GET /{video_id}?fields=reactions.summary(),comments.summary(),shares` and `GET /{video_id}/video_insights?metric=post_impressions_unique,post_video_views,post_video_view_time` to populate a dashboard. Insights are fetched as a background daemon every 30 minutes, starting 24 hours after publish (configurable).

**User flow:**
1. User opens "Monitor" tab
2. App shows table: video_url | views | reach | reactions | comments | shares | minutes_viewed
3. Background fetcher refreshes data every 30 minutes
4. User can click a row to see the post on Facebook

**Why we need Advanced Access:**
Insights are useless if they only work for the app admin's own posts. Creators need to see analytics for the Pages they manage.

---

### 4.4 `pages_manage_engagement`

**Permission purpose:**
> After publishing a video, our app optionally posts a single "pinned-style" first comment containing additional links or hashtags. The comment text is supplied by the creator in the sheet column `binh_luan_video`. We call `POST /{video_id}/comments` with `{message: "<text>"}` exactly once per video, and only when the sheet column has content. Reels are excluded (the Reels comment endpoint behaves differently).

**User flow:**
1. In the sheet row, user fills the `binh_luan_video` column with comment text
2. After successful video upload, app waits configurable delay (default 0-3 minutes)
3. App calls `POST /{video_id}/comments`
4. On failure, video remains published (comment failure NEVER reverts publish)

**Why we need Advanced Access:**
First-comment is standard creator workflow (e.g., for putting affiliate links, video index, additional context). Manual posting defeats the purpose of bulk automation.

**Safety measures:**
- Max 8000 chars per comment (Graph API limit)
- Hardcoded "1 comment per video" — never spam
- Skipped on Reels to respect platform difference
- Configurable random delay 0-300s to avoid burst patterns

---

### 4.5 `business_management` (optional)

> If you remove this from the app, do so before submitting. Currently the bot doesn't actively call business management endpoints — it's declared but never used. Removing reduces reviewer suspicion.

**Action: Remove this permission from app config** unless multi-app rotation needs it.

---

### 4.6 `public_profile` + `email`

These are **standard access by default** — no review needed. Used only for `GET /me` to display the connected user's name in the GUI.

---

## 5. Test Instructions for Reviewer (English template)

> Paste this verbatim in the "Instructions for Testing" field of each permission submission. Reviewers spend 2-5 minutes per app — clarity wins.

```
TEST ENVIRONMENT
================

Test User:
  Email:    reviewer-test@lttstudios.com
  Password: <provide via Meta secure channel>

Test Page:  "LTTStudio Reviewer Test Page" (ID: <fill after creating>)
  This Page is owned by the test user and exists solely for review purposes.

Test Sheet: <Google Sheets URL with 2 sample rows>
  Already populated with sample video URLs, titles, descriptions.
  Test user has Editor access.


HOW TO TEST EACH PERMISSION
============================

[pages_show_list] + [pages_manage_posts]
----------------------------------------
1. Download our app installer from:
     https://lttstudios.com/download (one-click portable .exe, ~50MB)
2. Launch BOT_UP_FACEBOOK.exe → click "Settings" tab → fill:
     - Google Credentials path: (provided in the .zip)
     - Sheet ID: <from test sheet URL>
3. Click "Facebook Accounts" tab → "Connect Account"
4. Browser opens, log in as test user, approve permissions
5. The app shows the list of Pages — verify "LTTStudio Reviewer Test Page" appears (proves pages_show_list works)
6. Tick the Page → "Save"
7. Click "Sheet FB" tab → add a worker (Test sheet + Tab "Test" + the test Page)
8. Click "▶ Start" — bot picks up row #2, uploads the video
9. After ~3 minutes, video appears on the test Page (proves pages_manage_posts works)

[pages_read_engagement]
------------------------
10. Wait 24 hours after step 9 (or use sheet row with old `uploaded_at`)
11. Click "Monitor" tab — table shows views/reach/reactions/comments for the test video
    (proves pages_read_engagement works)

[pages_manage_engagement]
-------------------------
12. In the test sheet, row #3 has the `binh_luan_video` column filled with:
      "Test comment from LTTStudio reviewer review"
13. Click "▶ Start" again — bot publishes the video AND posts a comment
14. Navigate to the test Page on facebook.com — verify the comment under the video
    (proves pages_manage_engagement works)


WHAT THIS APP DOES (1-sentence)
================================
LTTStudio VideoBot is a desktop tool that lets video content creators bulk-publish 
pre-recorded videos to multiple Facebook Pages they own, with scheduling, optional 
first-comment, and engagement analytics — all driven by a Google Sheets row queue.


WHAT THIS APP DOES NOT DO
==========================
- Does NOT collect or store user PII beyond Page name and Page ID
- Does NOT share or transmit data to third parties
- Does NOT post on behalf of users without explicit row-by-row scheduling
- Does NOT auto-generate content (creators supply all text/video)
- Does NOT support Instagram, Messenger, Ads, or Business management


DATA HANDLING
==============
- Page access_token: stored locally, AES-128 Fernet encryption, bound to Windows Machine GUID
- Sheet data: read-only access; bot writes back only status columns (status, uploaded_at, video_url)
- Audit log: timestamped JSONL with operation events (no caption content, no PII)
- Data deletion: see https://lttstudios.com/legal/data-deletion.html — user can request
  full deletion by emailing akakenly.design@gmail.com; deleted within 30 days

CONTACT
========
Email: akakenly.design@gmail.com
Support: support@lttstudios.com
Website: https://lttstudios.com
```

---

## 6. Screencast Recording Guide

> Meta requires 1 screencast per permission (or 1 combined). Mỗi screencast 15-60 giây, MP4, < 25MB. Quay bằng OBS Studio (free) hoặc Snipping Tool (Windows 11).

### 6.1 Universal setup
- Resolution: 1280×720 (16:9)
- FPS: 30
- Audio: KHÔNG cần (Meta tắt audio khi review)
- Cursor: bật cursor highlight (OBS plugin) để thấy rõ click
- Browser: dùng Chrome Incognito để tránh suggest tab cũ

### 6.2 Screencast 1 — `pages_show_list`

**Duration: ~20 giây**

| Time | Hành động | Hiển thị |
|---|---|---|
| 0:00 | Mở BOT_UP_FACEBOOK.exe | GUI dark theme load |
| 0:03 | Click tab "FB Accounts" | Tab account hiển thị |
| 0:05 | Click nút "Connect Facebook" | Browser mở |
| 0:08 | (Browser) Login test user | FB OAuth dialog |
| 0:12 | Click "Continue" để grant permission | Permission grant page |
| 0:15 | Quay lại app — thấy list Pages | "LTTStudio Reviewer Test Page" trong list |
| 0:18 | Tick Page → Save | Confirmation toast |
| 0:20 | END | — |

### 6.3 Screencast 2 — `pages_manage_posts`

**Duration: ~40 giây**

| Time | Hành động | Hiển thị |
|---|---|---|
| 0:00 | Tab "Sheet FB" | Sheet runner UI |
| 0:03 | Add worker: sheet + tab + Page | Worker row appear |
| 0:06 | Show queue preview với 1 row | Row #2 visible |
| 0:10 | Click "▶ Start" | Log scroll bắt đầu |
| 0:15 | Log: "Tải video từ Drive..." | Download progress |
| 0:20 | Log: "Bắt đầu upload..." | Upload chunks 0-100% |
| 0:32 | Log: "✅ Upload xong: facebook.com/..." | Success message |
| 0:35 | Mở browser, paste URL | Video xuất hiện trên Page |
| 0:40 | END | — |

### 6.4 Screencast 3 — `pages_read_engagement`

**Duration: ~20 giây**

| Time | Hành động | Hiển thị |
|---|---|---|
| 0:00 | Tab "Monitor" | Insights table empty |
| 0:03 | Click "Refresh" | Loading spinner |
| 0:08 | Table populate với data | views/reach/reactions cho videos |
| 0:15 | Click 1 row → mở link FB | Bài video trên FB |
| 0:20 | END | — |

### 6.5 Screencast 4 — `pages_manage_engagement`

**Duration: ~30 giây**

| Time | Hành động | Hiển thị |
|---|---|---|
| 0:00 | Show Google Sheet với row có `binh_luan_video` filled | Cột comment có text "Test comment..." |
| 0:05 | Tab "Sheet FB" → "▶ Start" | Worker chạy |
| 0:12 | Log: "Upload xong..." | Video success |
| 0:15 | Log: "Đăng comment..." | Comment progress |
| 0:18 | Log: "✅ Comment posted" | Success |
| 0:22 | Browser: vào Page → thấy video | Video hiện |
| 0:25 | Scroll xuống comments → thấy comment vừa post | Comment visible |
| 0:30 | END | — |

### 6.6 Tips để pass review nhanh
- Đừng quay GUI có account khác / Page khác xuất hiện — chỉ test environment
- Đừng show thông tin nhạy cảm (mật khẩu, token) ngay cả khi blur
- Nói rõ "Test user logged in" qua text overlay (1 dòng đầu video)
- Render H.264 baseline để file nhỏ
- Tên file: `permission_NAME_v1.mp4` (vd: `pages_manage_posts_v1.mp4`)

---

## 7. Required Asset Checklist

| Asset | Trạng thái | Đường dẫn / Note |
|---|---|---|
| App Icon 1024×1024 PNG | ✅ | Đã upload (logo LTT) |
| Long description (English) | ⚠️ Soạn | ~200-500 chữ; xem Section 4.1 làm template |
| Short description (50-100 chữ) | ⚠️ Soạn | "LTTStudio VideoBot is a desktop automation tool..." |
| Privacy Policy URL | ✅ | https://lttstudios.com/legal/privacy.html |
| Terms of Service URL | ✅ | https://lttstudios.com/legal/terms.html |
| **Data Deletion URL** | ❌ | **PHẢI tạo** https://lttstudios.com/legal/data-deletion.html |
| Business Verification | ❌ | Submit qua Business Manager |
| Screencast 1 (pages_show_list) | ❌ | Quay theo Section 6.2 |
| Screencast 2 (pages_manage_posts) | ❌ | Quay theo Section 6.3 |
| Screencast 3 (pages_read_engagement) | ❌ | Quay theo Section 6.4 |
| Screencast 4 (pages_manage_engagement) | ❌ | Quay theo Section 6.5 |
| Test User credentials | ❌ | Tạo test user mới (KHÔNG dùng account thật) |
| Test Page | ❌ | Tạo "LTTStudio Reviewer Test Page" |
| Test Sheet | ❌ | Tạo Google Sheet với 3 row mẫu |
| App installer download link | ⚠️ Nếu chưa public | Upload zip lên lttstudios.com/download |

---

## 8. Data Deletion Page — Content gợi ý

> File: `lttstudios.com/legal/data-deletion.html` (cần tạo và publish trước khi submit)

```html
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>Data Deletion Instructions — LTTStudio VideoBot</title>
</head>
<body>
<h1>Data Deletion Instructions</h1>

<h2>What data we store</h2>
<p>LTTStudio VideoBot stores the following data locally on the user's machine
(NOT on any LTTStudio server):</p>
<ul>
  <li>Facebook Page access tokens (encrypted, AES-128)</li>
  <li>Page IDs and Page names of Pages you connected</li>
  <li>Operation logs and audit trail (timestamps, post IDs)</li>
  <li>Cached video files in temporary folder</li>
</ul>

<h2>How to delete your data</h2>
<p><strong>Option A — Self-service (instant):</strong></p>
<ol>
  <li>Close the bot</li>
  <li>Delete the folder containing the bot installation</li>
  <li>Optionally revoke the app at:
    <a href="https://www.facebook.com/settings?tab=business_tools">
      Facebook Settings → Business Integrations
    </a> — find "Lttstudio" and click Remove
  </li>
</ol>

<p><strong>Option B — Email request (within 30 days):</strong></p>
<p>Email <a href="mailto:akakenly.design@gmail.com">akakenly.design@gmail.com</a>
with subject "Data Deletion Request" and include:</p>
<ul>
  <li>Your Facebook user ID or the email address used during OAuth</li>
  <li>Confirmation that you want all data associated with your account
      deleted from any LTTStudio system</li>
</ul>
<p>We respond within 5 business days and complete deletion within 30 days.</p>

<h2>Contact</h2>
<p>Data Protection Officer: LE THANH TRUNG<br>
Email: akakenly.design@gmail.com<br>
Address: Mê Linh, Hà Nội, Vietnam</p>

<p><em>Last updated: 2026-06-02</em></p>
</body>
</html>
```

---

## 9. Step-by-step Dashboard Walkthrough

### Step 1 — Điền Data Deletion URL

1. Vào https://developers.facebook.com/apps/2021063792619148/settings/basic/
2. Scroll xuống mục **"Xóa dữ liệu người dùng"** / "User Data Deletion"
3. Dropdown chọn **"URL hướng dẫn xóa dữ liệu"** (đã đúng)
4. Trường text: paste `https://lttstudios.com/legal/data-deletion.html`
5. Click **"Lưu thay đổi"** (Save Changes) cuối trang

### Step 2 — Submit Business Verification

1. Trên Dashboard, click banner xanh **"Trở thành Nhà cung cấp công nghệ"**
2. Hoặc trực tiếp: https://business.facebook.com/settings/security
3. Choose **"Verify Business"**
4. Chọn cách verify:
   - **Domain verification** (nhanh nhất): add DNS TXT record cho `lttstudios.com`
   - **Document verification** (chậm hơn): upload CCCD/GPKD
5. Submit → chờ Meta verify (thường < 24h cho domain, 1-3 ngày cho document)

### Step 3 — Tạo Test User

1. Dashboard → **Vai trò trong ứng dụng** → tab **"Người dùng thử"**
2. Click **"Thêm người"** → chọn **"Create Test Users"** (FB tạo account giả lập)
3. Tạo 1 test user → save credentials vào file để paste vào instructions
4. Test user này sẽ tự động được seed với 1 Test Page có thể publish

### Step 4 — Tạo Test Sheet

1. Tạo Google Sheet mới: `LTTStudio FB Reviewer Test Sheet`
2. Tab "Test" với header columns đúng config bot:
   ```
   video_goc | schedule_time_fb_dai | tieu_de_seo | mo_ta | tu_khoa_chinh
   | link_anh_thumb | binh_luan_video | target_page | status_fb
   | error_message_dai | video_url_fb | fb_video_id | uploaded_at
   | upload_duration_s | post_type | platform
   ```
3. Add 3 row sample:
   - Row 1: Feed video không comment
   - Row 2: Feed video có comment
   - Row 3: Reels (post_type=reels)
4. Share sheet cho test user với quyền Editor
5. Note Sheet ID để paste vào Test Instructions

### Step 5 — Quay screencast

Theo Section 6 — quay 4 video, save dạng MP4, < 25MB mỗi cái.

### Step 6 — Submit App Review

1. Dashboard → **Trường hợp sử dụng** → click vào use case "Quản lý mọi thứ trên Trang"
2. Tab **"Quyền và tính năng"**
3. Với mỗi permission đang ở "Sẵn sàng thử nghiệm" — click **"Request Advanced Access"**:
   - Paste Use case description từ Section 4
   - Upload screencast tương ứng
   - Paste Test Instructions từ Section 5
4. Click **"Submit for Review"**

### Step 7 — Switch app sang Live (sau khi approved)

1. Dashboard header có toggle **"App Mode: Development / Live"**
2. Click toggle → confirm
3. Trạng thái sidebar đổi từ "Đã hủy đăng" → **"Đã đăng" (Live)**
4. ✅ Bot có thể đăng public từ giờ phút này

---

## 10. Common Rejection Reasons & Mitigation

| Lý do reject | Tại sao xảy ra | Cách tránh |
|---|---|---|
| **"Insufficient demonstration"** | Screencast quá ngắn, không show full flow | Quay ≥ 20s, có overlay text mô tả từng bước |
| **"Permission usage unclear"** | Mô tả use case quá generic | Dùng template Section 4, cụ thể endpoint + tham số |
| **"Cannot reproduce flow"** | Test instructions thiếu chi tiết / sheet ID sai | Test lại instructions trên máy khác trước khi submit |
| **"Privacy policy missing details"** | URL trả 404 hoặc nội dung sơ sài | Verify URL live + đề cập rõ Facebook data |
| **"Data deletion not accessible"** | URL không có hoặc không nói rõ cách xoá | Dùng template Section 8 |
| **"Suspicious activity"** | App đang Production và bị spam complaint | **Tạm dừng bot** trong thời gian chờ |
| **"Business not verified"** | Skip Business Verification | Phải xong B1-B4 trước |
| **"Test user can't log in"** | Reviewer dùng test creds nhưng fail | Save credentials chính xác, không có ký tự đặc biệt gây paste lỗi |
| **"Unused permission requested"** | Request `business_management` nhưng không có code dùng | Remove permissions không dùng |

---

## 11. Post-Approval Maintenance

Sau khi app Live, vẫn phải:

| Việc | Tần suất | Lý do |
|---|---|---|
| Monitor app status via `core/app_status.py` | Daily auto | Detect FB disable / suspend |
| Refresh page tokens trước expiry | Hourly auto (đã có) | Tránh `code=190` |
| Theo dõi rate-limit warning | Per upload | FB error 4/17/32 |
| Audit Telegram notifications | Real-time | `notify_on_token_expiry`, `notify_on_error` |
| Annual Data Use Review | Yearly | Meta yêu cầu confirm vẫn dùng |
| Update Privacy Policy nếu thay đổi data handling | Khi cần | GDPR compliance |

---

## 12. Risk & Contingency

### Nếu Review bị REJECT lần 1
- ĐỌC KỸ feedback của Meta — họ chỉ ra exact điểm fail
- Fix → re-submit. KHÔNG tranh cãi. Meta không reply email
- Mỗi lần reject reset queue → có thể chờ thêm 5-14 ngày

### Nếu Business Verification bị REJECT
- Document Verification (CCCD): chụp rõ, không che số
- Domain Verification: confirm DNS TXT record đã propagate qua dnschecker.org
- Có thể call hotline Meta Business Vietnam: hỗ trợ tiếng Việt

### Nếu chờ quá 14 ngày không có response
- Vào **App Dashboard → Support** → mở ticket
- Meta thường response trong 48h cho dev nghiêm túc

### Plan B nếu Meta reject vĩnh viễn (rất hiếm)
- Tạo App MỚI với app ID khác
- KHÔNG ÉN tham vọng — submit với CHỈ 2 permission cốt lõi trước (`pages_show_list` + `pages_manage_posts`)
- Add các permission khác trong các round sau khi đã Live

---

## 13. Timeline Tracker (điền vào khi làm)

| Phase | Task | Bắt đầu | Hoàn thành | Note |
|---|---|---|---|---|
| A1-A10 | App settings | _____ | _____ | |
| B1-B4 | Business Verification submit | _____ | _____ | |
| B4 | Business Verification approved | _____ | _____ | |
| C1-C5 | Test environment | _____ | _____ | |
| Screencast 1-4 | Recording | _____ | _____ | |
| Submit | App Review submit | _____ | _____ | |
| Result | Approved / Rejected | _____ | _____ | Nếu reject ghi lý do |
| Switch Live | Go live | _____ | _____ | ✅ Done |

---

## 14. Quick Reference URLs

- App Dashboard: https://developers.facebook.com/apps/2021063792619148/dashboard/
- App Settings (Basic): https://developers.facebook.com/apps/2021063792619148/settings/basic/
- App Roles: https://developers.facebook.com/apps/2021063792619148/roles/roles/
- Use Cases: https://developers.facebook.com/apps/2021063792619148/use-cases/
- Permissions and Features: https://developers.facebook.com/apps/2021063792619148/use_cases/customize/?use_case_enum=PAGES_API&selected_tab=permissions
- Business Manager: https://business.facebook.com/settings/
- Meta App Review docs: https://developers.facebook.com/docs/app-review

---

**Ngày tạo**: 2026-06-02
**Phiên bản**: 1.0
**Author**: LTTStudio + Claude
