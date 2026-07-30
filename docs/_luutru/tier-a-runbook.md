# Tier A — Complete Runbook for Meta App Review Submission

> **Status sau bước này**: Sẵn sàng submit Meta App Review.
> **Tổng thời gian**: ~8-12 giờ (spread 5-7 ngày vì cần đợi Meta verify).
> **Cập nhật**: 2026-06-04

---

## 📋 Tổng quan 7 Tier A items

| # | Item | Thời gian active | Thời gian wait | Bắt đầu |
|---|---|---|---|---|
| 1 | Deploy site lên lttstudios.com | 30' | 0 | Day 0 |
| 2 | Convert SVG → PNG icons | ✅ DONE | 0 | — |
| 3 | OG image 1200×630 PNG | ✅ DONE | 0 | — |
| 4 | Business Verification + Domain Verification | 30' | 1-3 ngày Meta | Day 0 |
| 5 | Test FB user + test Page | 30' | 1-2h Meta verify email | Day 1-2 |
| 6 | Test Google Sheet | 15' | 0 | Day 1-2 |
| 7 | 4 Screencast videos | 2-3h | 0 | Day 3-4 |

---

## ▶️ Item 1 — Deploy lttstudios-website lên inet.vn

**Xem guide riêng**: `docs/lttstudios-deploy-inet-vn.md`
**ZIP**: `docs/lttstudios-website.zip` (đã update, 170 KB+)

Sau deploy, verify bằng:
```bash
cd "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook\docs\lttstudios-website"
python -X utf8 tests/run_tests.py --live
```

→ Phải 760+ tests pass.

---

## ▶️ Item 2-3 — Icons (ĐÃ XONG)

Generated 16 files trong `assets/img/`:
- `favicon-16/32/48/64/96/128/192/256/512/1024.png` — favicon các size
- `favicon.ico` (multi-size ICO cho old browsers)
- `apple-touch-icon.png` (180×180)
- `og-default.png` (1200×630)
- `app-icon-1024.png` (cho Meta App Dashboard)

→ Upload kèm site khi deploy (bước 1).

---

## ▶️ Item 4 — Business Verification + Domain Verification

### Step 4.1 — Mở Meta Business Manager

1. Mở https://business.facebook.com/
2. Login với account có quyền admin Meta App `2021063792619148` (Lttstudios)
3. Sidebar trái → **Settings** → **Business settings**
4. Trong **Business settings**, sidebar → **Security center**
5. Click **"Start verification"** (nút xanh)

### Step 4.2 — Nhập thông tin business

Form Meta yêu cầu:

| Field | Giá trị |
|---|---|
| Business legal name | LTTStudios (hoặc tên cá nhân LE THANH TRUNG nếu chưa có ĐKKD) |
| Business address | Mê Linh, Hà Nội, Vietnam |
| Phone number | (số phone bạn nhận SMS) |
| Website | https://lttstudios.com |
| Business email | letammeiu@gmail.com |

Click **Next**.

### Step 4.3 — Chọn method Verification

Meta cho 3 cách:

| Method | Time | Recommendation |
|---|---|---|
| **Document upload** (CCCD/GPKD) | 1-3 ngày | Bắt buộc nếu có công ty |
| **Domain verification (DNS TXT)** | 24h | NHANH NHẤT — chọn cái này |
| **Confirmation code via mail** | 5-7 ngày | Chậm |

→ **Chọn Domain Verification (DNS TXT)**.

### Step 4.4 — DNS TXT record cho lttstudios.com

Meta sẽ generate 1 string dạng:
```
facebook-domain-verification=abc123xyz456...
```

Vào **DNS panel** (nơi quản lý DNS của `lttstudios.com`):

| Hosting / Registrar | Đường dẫn |
|---|---|
| Cloudflare | DNS → Records → Add record |
| inet.vn | DNS Management → Add record |
| Namecheap | Domain List → Advanced DNS → Add new record |
| GoDaddy | DNS → Add → TXT |

Thêm record:
```
Type:  TXT
Name:  @ (hoặc bỏ trống — nghĩa là root domain)
Value: facebook-domain-verification=abc123xyz456...
TTL:   Auto (hoặc 3600)
```

Save.

### Step 4.5 — Wait + Verify

1. Đợi DNS propagate (15 phút - 24h, thường 1-2h)
2. Test bằng cmd:
   ```cmd
   nslookup -type=TXT lttstudios.com
   ```
   → Phải thấy `facebook-domain-verification=...`
3. Trên Meta Business Manager, click **Verify**
4. Trang refresh → status thành **Verified** ✅

### Step 4.6 — Submit document verification song song (tăng trust)

Trong khi đợi Domain Verification, làm thêm Document Verification:
1. Business settings → Security center → **Submit business documentation**
2. Upload:
   - **CCCD** mặt trước + mặt sau (chụp rõ, không che số)
   - **Hoặc** GPKD hộ kinh doanh nếu có
3. Meta xử lý 1-3 ngày

Document Verification + Domain Verification cùng pass = Business Verification COMPLETE.

---

## ▶️ Item 5 — Test FB user + Test Page setup

### Step 5.1 — Tạo Test User trong App Dashboard

1. Vào https://developers.facebook.com/apps/2021063792619148/roles/test-users/
2. Click **"Create Test Users"**
3. Form:
   - Number: **1**
   - Permission to install: tick các permission bot dùng (`pages_show_list`, `pages_manage_posts`, `pages_read_engagement`, `pages_manage_engagement`)
   - Installed app: tick **Lttstudios**
4. Click **Create Test Users**
5. Meta tạo 1 test account với email pattern `test_xxx@tfbnw.net`

### Step 5.2 — Lưu credentials test user

Sau khi Meta tạo, click vào test user:
- Click **"Edit"** → copy ra:
  - Email: `test_xxx@tfbnw.net`
  - Password: (tự đặt — phải có chữ + số + ký tự đặc biệt)
  - Save password

Lưu credentials vào file ngoài:
```
docs/fb-app-review-assets/test-user-credentials.txt
```
**KHÔNG commit file này lên public repo.**

### Step 5.3 — Tạo Test Page cho test user

1. Login vào Facebook bằng test user (browser ẩn danh để không conflict với account chính)
2. Vào https://www.facebook.com/pages/create/
3. Tạo Page:
   - Name: **LTTStudios Reviewer Test Page**
   - Category: **Video Creator**
   - Make Public
4. Sau khi tạo, copy Page ID (URL có dạng `facebook.com/{page_id}` hoặc trong About)

### Step 5.4 — Make sure test user has admin role on test Page

Test Page tạo lúc đăng nhập bằng test user → test user tự động admin. Verify:
- Page → Settings → Page Roles → check test user có role Admin

### Step 5.5 — Add test user vào App như Tester

1. Vào https://developers.facebook.com/apps/2021063792619148/roles/roles/
2. Tab **Người dùng thử** (Testers)
3. Click **Thêm người dùng thử**
4. Type email test user → Send invite
5. Open email của test user (gmail tạm Meta) → accept invite

→ Test user giờ có thể OAuth vào app này.

---

## ▶️ Item 6 — Test Google Sheet

### Step 6.1 — Tạo Sheet mới

1. Login Google Sheets bằng account riêng (có thể dùng `akakenly.design@gmail.com`)
2. Tạo Sheet mới: **"LTTStudios Reviewer Test Sheet"**

### Step 6.2 — Setup columns (header row 1)

Copy/paste vào row 1:

```
video_drive_url	schedule_time	title	description	keywords	thumbnail_url	target_page	post_type	platform	comment	status	video_url_fb	uploaded_at	error_message
```

### Step 6.3 — Add 3 sample rows

| Row | video_drive_url | schedule_time | title | description | keywords | target_page | post_type | platform |
|---|---|---|---|---|---|---|---|---|
| 2 | https://drive.google.com/file/d/SAMPLE_ID/view | 2026-06-10 10:00 | Sample test video 1 | Reviewer test description | test,sample | LTTStudios Reviewer Test Page | feed | facebook |
| 3 | https://drive.google.com/file/d/SAMPLE_ID2/view | 2026-06-10 14:00 | Sample test Reel | Test Reel for FB review | test,reel | LTTStudios Reviewer Test Page | reels | facebook |
| 4 | https://drive.google.com/file/d/SAMPLE_ID3/view | 2026-06-11 09:00 | TikTok test post | Audit test for TikTok flow | test,tiktok | (test_tiktok_account) | feed | tiktok |

### Step 6.4 — Upload sample videos to Drive

1. Drive → Upload **3 short MP4 files** (10-30s, < 10MB)
2. Right-click → Share → **Anyone with link**
3. Copy link, paste vào sheet column `video_drive_url`

### Step 6.5 — Share Sheet với test user

1. Sheet → Share (button góc phải)
2. Add test user email (`test_xxx@tfbnw.net`)
3. Role: **Editor**
4. Send

### Step 6.6 — Note Sheet ID

URL Sheet có dạng:
```
https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
```

Lưu Sheet ID vào `docs/fb-app-review-assets/test-user-credentials.txt`.

---

## ▶️ Item 7 — Screencast Recording

### Setup chung

| Tool | Recommendation |
|---|---|
| Screen recorder | **OBS Studio** (free, https://obsproject.com) |
| Format | MP4 H.264, 1280×720 30fps |
| Audio | Tắt mic — không cần voice (Meta reviewer mute) |
| Duration | 15-60s mỗi video |
| Size limit Meta | < 25MB mỗi file |
| Cursor highlight | Bật để thấy click rõ |

### Recording environment

Trước khi quay:
1. Mở bot trên **clean Windows** (close apps khác, hide taskbar đẹp)
2. Login bot bằng **test FB user credentials** (Item 5)
3. Mở **test Google Sheet** (Item 6) trong tab background
4. Resolution màn hình: 1920×1080 hoặc 1280×720
5. Disable notifications (Windows Focus Assist → Priority only)

### Video 1: `pages_show_list` (15-20s)

**Script (text overlay từng bước)**:

```
[0:00-0:03]  Open bot → Settings tab (Test environment shown)
[0:03-0:06]  Click "FB Accounts" tab
[0:06-0:10]  Click "Connect Facebook Account" button
[0:10-0:14]  Browser opens FB OAuth (test user logged in)
             Show permissions screen including pages_show_list
[0:14-0:18]  Click "Continue" → redirect to lttstudios.com/auth/fb-callback.html
[0:18-0:20]  Back to bot — list of Pages appears (incl. test Page)
             User ticks Page → Save
```

Save file: `docs/fb-app-review-assets/screencasts/1-pages_show_list.mp4`

### Video 2: `pages_manage_posts` (30-40s)

```
[0:00-0:05]  Bot already connected → Sheet FB tab
[0:05-0:10]  Add worker: Test Sheet + Tab "Test" + Test Page
[0:10-0:15]  Worker appears → Click "▶ Start"
[0:15-0:25]  Log scrolls: "Downloading video...", "Upload started"
             Show progress chunks 0% → 50% → 100%
[0:25-0:32]  Log: "Video status: processing → ready", "Upload OK: facebook.com/..."
[0:32-0:40]  Open the URL → video appears on test Page (publish proof)
```

Save: `docs/fb-app-review-assets/screencasts/2-pages_manage_posts.mp4`

### Video 3: `pages_read_engagement` (15-20s)

```
[0:00-0:05]  Bot → Monitor tab
[0:05-0:10]  Click "🔄 Refresh" — insights load
[0:10-0:15]  Table shows: views, reach, reactions, comments, shares for test video
[0:15-0:20]  Click a row → opens FB post showing same engagement numbers
```

Save: `docs/fb-app-review-assets/screencasts/3-pages_read_engagement.mp4`

### Video 4: `pages_manage_engagement` (25-30s)

```
[0:00-0:05]  Show Test Sheet — row 3 has "binh_luan_video" filled
             Text: "Watch this on YouTube too! https://youtube.com/@channel"
[0:05-0:10]  Bot Sheet FB tab → Click "▶ Start" — bot picks up row 3
[0:10-0:18]  Log: "Upload OK..." → "Posting comment..."
[0:18-0:22]  Log: "✅ Comment posted (id=...)"
[0:22-0:30]  Open test Page on FB → see video + first comment underneath
             showing the comment text from sheet
```

Save: `docs/fb-app-review-assets/screencasts/4-pages_manage_engagement.mp4`

### Quay nhanh với OBS

1. Cài OBS Studio
2. Settings → Output → Recording:
   - Path: `docs/fb-app-review-assets/screencasts/`
   - Format: **mp4**
   - Encoder: **x264** (or NVIDIA NVENC)
   - Quality: High
3. Settings → Video:
   - Output Resolution: 1280×720
   - FPS: 30
4. Settings → Audio: **Disable all input/output devices**
5. Add Source → Display Capture → select monitor
6. Hotkeys → Start Recording: `F9`, Stop: `F10`
7. Bấm F9 → quay video → F10 → save

### Tip để pass review

- ✅ Show test environment text trên góc trên ("TEST USER: test_xxx@tfbnw.net")
- ✅ Each click is visible cursor + small pause
- ❌ Don't show real production data
- ❌ Don't show password input (use already-logged-in state)
- ✅ Render H.264 — universal compatible
- ✅ Filename theo permission để reviewer dễ match

---

## ✅ Checklist hoàn tất Tier A

| Item | Done | Note |
|---|---|---|
| 1. Site deployed to lttstudios.com | ☐ | Verify với verify-deploy.py |
| 2. PNG icons created | ✅ | 14 files trong assets/img/ |
| 3. OG image PNG created | ✅ | og-default.png 1200×630 |
| 4a. Business Verification — Domain TXT submitted | ☐ | Add DNS record |
| 4b. Business Verification — Domain verified (24-72h) | ☐ | Wait Meta |
| 4c. Business Verification — Document submitted | ☐ | CCCD upload |
| 5a. Test FB user created | ☐ | Save credentials |
| 5b. Test Page "LTTStudios Reviewer Test Page" | ☐ | Save Page ID |
| 5c. Test user added as App Tester | ☐ | Accept invite |
| 6a. Test Google Sheet created | ☐ | Save Sheet ID |
| 6b. Sheet shared with test user | ☐ | Editor role |
| 6c. 3 sample videos uploaded to Drive | ☐ | "Anyone with link" |
| 7a. Screencast 1 (pages_show_list) | ☐ | < 25MB MP4 |
| 7b. Screencast 2 (pages_manage_posts) | ☐ | < 25MB MP4 |
| 7c. Screencast 3 (pages_read_engagement) | ☐ | < 25MB MP4 |
| 7d. Screencast 4 (pages_manage_engagement) | ☐ | < 25MB MP4 |

**Tổng cộng**: 16 sub-items. Done hết là **MVP cho Meta App Review submission**.

---

## 📅 Timeline thực tế

| Day | Item | Activity |
|---|---|---|
| **Day 0** (hôm nay) | 1, 4a | Deploy site + Add DNS TXT |
| **Day 1** | 4b, 4c, 6 | Wait DNS verify + submit document + tạo Sheet |
| **Day 2-3** | 5 | Tạo test user + test Page (sau Business Verify approve) |
| **Day 3-4** | 7 | Record 4 screencasts |
| **Day 5** | Submit | Submit Meta App Review |
| **Day 5-19** | Wait | 5-14 ngày Meta review |
| **Day 20+** | Live | Toggle App Live |

---

## 🎯 Sau khi submit Meta App Review

1. Check email letammeiu@gmail.com daily
2. Meta có thể request thêm info → respond trong 5 ngày (timeout sau 5 ngày)
3. Approved → toggle App Mode sang Live → bot có thể đăng public
4. Rejected → đọc feedback → fix → re-submit (mất thêm 5-14 ngày)

---

**Author**: LTTStudios + Claude · **Updated**: 2026-06-04
