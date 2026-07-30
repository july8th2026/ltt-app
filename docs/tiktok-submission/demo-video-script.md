# Demo Video Script — LTTStudio VideoBot for TikTok Audit (v2)

> **Target:** 3:00 minute video showing complete OAuth + upload flow
> **Tools:** OBS Studio (free) hoặc ShareX
> **Format:** 1920×1080, MP4 H.264 ~10 Mbps, **voice-over English** (subtitle Vietnamese optional)
> **Mode:** Microphone ON — TikTok reviewers expect narrated demo, not silent screen recording

---

## 📋 Pre-recording Checklist

Trước khi nhấn Record:

```
□ Bot đã start (python main.py)
□ File config.json đã có Client Key + Secret + redirect_uri HTTPS
□ Tài khoản TikTok klcloset96 ĐÃ DISCONNECT khỏi bot (sẽ connect live trong demo)
□ Tạo lại browser session sạch (Ctrl+Shift+N — Incognito) để OAuth screen rõ ràng
□ Video test ngắn 8-15s đã sẵn ở C:\Users\KENLY\Downloads\
   (đề xuất: Sunset_over_ocean_dramatic_clouds_a10d65a628.mp4)
□ Đóng tất cả ứng dụng nhiễu (notification Zalo/FB Messenger/Discord)
□ Mic kiểm tra — speak test "TikTok demo recording test"
□ OBS scene preset: 1920×1080 @ 30fps, audio bitrate 192k
□ Logo TikTok đã có ở data/assets/tiktok_logo.png  ✅ (verified)
□ Privacy + Terms URL trả 200 OK  ✅ (verified)
```

---

## 🎬 Script chi tiết — 3:00 phút

### [00:00 – 00:15] Opening (15s)

**Screen:**
- Slide 1 (PowerPoint hoặc OBS text overlay):
  ```
  LTTStudio VideoBot
  TikTok Content Posting API Integration

  Demo for App Audit Review
  May 2026
  ```
- Optional: Sub-title nhỏ "Built on TikTok Content Posting API v2 + Login Kit"

**Voice-over (English):**
> "Hello, this is the audit demo of LTTStudio VideoBot — a Windows desktop application that helps Vietnamese content creators schedule and publish short-form videos to TikTok using the official Content Posting API v2 and Login Kit. The entire flow runs locally on the user's machine — no cloud server, no third-party data sharing."

---

### [00:15 – 00:35] Privacy & Terms (20s) ⭐ NEW

**Screen:**
1. Open Chrome (or Edge), incognito mode
2. Navigate to **https://lttstudio.top/legal/privacy.html**
3. Scroll slowly through section "4b. TikTok data" (highlights: open_id, access_token, video, scope)
4. Open new tab → **https://lttstudio.top/legal/terms.html**
5. Brief scroll

**Voice-over:**
> "Before connecting any TikTok account, here is our published Privacy Policy at lttstudio.top/legal/privacy.html. It explicitly lists every piece of TikTok data we access — open_id, display name, avatar URL, access token, refresh token — and our retention policy. All tokens are encrypted at rest using AES-128 Fernet and never leave the user's computer. The Terms of Service link is also accessible at lttstudio.top/legal/terms.html."

---

### [00:35 – 00:50] Bot Overview (15s)

**Screen:**
1. Bring LTTStudio VideoBot to foreground
2. Pan slowly across the 9 tabs:
   ```
   📊 Sheet FB   📊 Sheet TikTok   ⚙️ Manual FB   🎵 Manual TikTok
   🔐 Tài khoản FB   🎵 Tài khoản TikTok   📈 Monitor   📋 TT Audit   🔧 Cài đặt
   ```
3. Highlight the **🎵 Tài khoản TikTok** tab — click on it

**Voice-over:**
> "Here is the LTTStudio VideoBot interface. We have dedicated tabs for TikTok account management, manual posting, and an audit dashboard which I'll show in a moment. Let's start by connecting a TikTok account."

---

### [00:50 – 01:30] OAuth Flow + Pre-OAuth Disclosure (40s) ⭐⭐⭐ MOST IMPORTANT

**Screen:**
1. On the **🎵 Tài khoản TikTok** tab, account list is empty (we disconnected before recording)
2. **Highlight the button "Continue with TikTok"** — note: official TikTok logo on the left, English label
3. Click the button
4. **Pre-OAuth Disclosure Modal appears** — pause 4 seconds. Show:
   ```
   🔐 Quyền truy cập TikTok
   ─────────────────────────
   ▐ Thông tin cơ bản tài khoản    (user.info.basic)
     Đọc username + ảnh đại diện…

   ▐ Upload video (Draft mode)     (video.upload)
     Gửi video vào Inbox của bạn…

   ▐ Đăng video trực tiếp           (video.publish)
     Đăng bài lên TikTok ngay từ bot…

   ℹ Bạn có thể thu hồi quyền bất cứ lúc nào:
     1. Trong bot: tab 🎵 Tài khoản TikTok → bấm 🗑 Ngắt kết nối
     2. Trên TikTok: tiktok.com/setting/manage-apps
   ```
5. Click **"Tiếp tục đăng nhập TikTok →"**
6. Browser opens → TikTok auth page at `https://www.tiktok.com/v2/auth/authorize/`
7. **HIGHLIGHT URL BAR** showing it's tiktok.com domain
8. **HIGHLIGHT the scopes list** TikTok displays
9. Click **"Authorize"** on TikTok page
10. Browser redirects to `https://lttstudio.top/legal/callback.html` → spinner
11. Auto-redirect back to localhost (callback complete)
12. Back in bot: account `klcloset96` appears in list with avatar + display name

**Voice-over:**
> "Clicking 'Continue with TikTok' triggers our mandatory pre-authorization disclosure modal. Per TikTok policy, the user sees every scope we will request, the exact reason we need each one, and instructions on how to revoke access later — both inside our app and through tiktok.com directly. Only after the user reads this disclosure and explicitly clicks 'Continue' does the OAuth flow start. We use PKCE for security. After TikTok's authorize screen, the code returns to our HTTPS callback at lttstudio.top, then locally to the app. The TikTok account, klcloset96, now appears as connected."

---

### [01:30 – 01:50] Audit Compliance Dashboard (20s) ⭐ NEW

**Screen:**
1. Click on tab **📋 TT Audit**
2. Show the **"TikTok Audit Readiness"** view:
   - Summary line: "✅ Sẵn sàng submit TikTok audit (11 checks pass)"
   - Left panel: 11 checks all green
   - Right panel: "🔑 OAuth Scopes đang dùng" — show 3 scopes with explanations
3. Pause 4 seconds so reviewer can read

**Voice-over:**
> "We've built a real-time audit-readiness dashboard inside the application itself. It verifies every TikTok compliance requirement — client credentials present, redirect URI uses HTTPS, privacy and terms URLs reachable, privacy policy mentions TikTok by name, official login button branding present, demo video script exists, scope set correctly, audit flags consistent, user-confirmation required, and a safe SELF_ONLY default. All eleven checks pass. The right panel shows each OAuth scope with its justification."

---

### [01:50 – 02:40] Manual Upload + Enhanced Consent Dialog (50s) ⭐⭐⭐ KEY

**Screen:**
1. Click tab **🎵 Manual TikTok**
2. Quickly fill the form:
   - File Video: click **📁 Chọn** → pick `Sunset_over_ocean_dramatic_clouds_a10d65a628.mp4`
   - File info auto-shows: "ℹ Sunset_over… • 2.8 MB • .mp4" (green)
   - Title: type **"Bot demo — Sunset 8s"**
   - Tài khoản TikTok: pre-selected as `klcloset96`
   - Loại đăng: combobox shows "Direct — Riêng tư (SELF_ONLY)" (default safe)
3. Click the bottom-bar **"🎵 Đăng TikTok"** button
4. Status flashes "⏳ Đang lấy thông tin creator từ TikTok..."
5. **Enhanced Consent Dialog opens** — pause 6 seconds. Walk through every section:
   ```
   📋  Xác nhận đăng TikTok — Audit-required disclosure
   ─────────────────────────────────────────────────────
   📹 Thông tin video
      Tiêu đề:    Bot demo — Sunset 8s
      Loại đăng:  📤 Đăng trực tiếp (tiktok_direct)
      Tài khoản:  @klcloset96

   🔐 Quyền riêng tư  (bạn chọn)
      [▼ 🔒 Chỉ mình tôi xem (SELF_ONLY)            ]
      ℹ App chưa được TikTok duyệt audit, chỉ có thể đăng SELF_ONLY.

   💬 Tương tác  (theo cài đặt creator)
      ☑ Cho phép comment
      ☑ Cho phép Duet
      ☑ Cho phép Stitch

   📢 Khai báo nội dung
      ☐ 🤖 Nội dung do AI tạo / chỉnh sửa
      ☐ 💼 Nội dung quảng cáo / tài trợ

   ✓ Xác nhận
      ☐ Tôi xác nhận nội dung này tuân thủ ĐKDV và NTCĐ TikTok.

   [❌ Hủy]                    [✅ Xác nhận & Đăng]
   ```
6. Pause to show the disabled "Confirm & Đăng" button
7. Click the consent checkbox → button enables
8. Click **"✅ Xác nhận & Đăng"**

**Voice-over:**
> "To post a video, the user fills the form on the Manual TikTok tab and clicks the post button. Our app first calls TikTok's creator_info query endpoint to fetch the user's current account-level settings. Then this comprehensive consent dialog appears. The user sees the video summary, then must actively select a privacy level — it's a dropdown, never pre-set. Because this app is still pending audit, only SELF_ONLY is available. Three interaction toggles let the user choose whether to allow comments, duets, and stitches. Two disclosure checkboxes capture AI-generated and branded-content declarations as required by TikTok's November 2024 policy. Finally, the user must tick the compliance acknowledgement before the 'Confirm and Post' button enables. Only on this explicit, per-publish confirmation does the upload proceed."

---

### [02:40 – 03:00] Upload progress + Success (20s)

**Screen:**
1. Dialog closes, status label shows progression:
   - "⏳ Đang đăng lên TikTok..."
   - "[TikTok] Init draft upload..."
   - "[TikTok] Đang upload video (1 chunk)..."
   - "[TikTok] Đang chờ TikTok xử lý video..."
   - "[TikTok] Trạng thái: PROCESSING_UPLOAD"
   - "✅ Đăng thành công! publish_id=v_inbox_file~v2.…"
2. Right pane Result tab shows: status=success + publish_id + timestamp
3. Switch to TikTok mobile app (or web tiktok.com profile) → show video in Inbox/profile

**Voice-over:**
> "The video uploads in chunks via the Content Posting API v2. We poll the publish status endpoint until completion. On success, the publish ID and timestamp are logged. The video is now visible in the user's TikTok account, exactly as configured — privacy SELF_ONLY, posted by the creator's own consent."

---

### [03:00 – 03:10] Disconnect flow (10s)

**Screen:**
1. Back to **🎵 Tài khoản TikTok** tab
2. Click selected account → right panel shows details
3. Click **"🗑 Ngắt kết nối"** button at bottom
4. Confirmation dialog → confirm
5. Token revoked at TikTok, account removed from list

**Voice-over:**
> "Users can disconnect at any time. The bot calls TikTok's revoke endpoint, then deletes the encrypted token from disk. The account is fully removed."

---

### [03:10 – 03:15] Closing (5s)

**Screen:**
- Slide back:
  ```
  Thank you for reviewing

  LTTStudio VideoBot
  https://lttstudio.top
  Support: support@lttstudio.top
  ```

**Voice-over:**
> "That concludes the demo. Privacy policy, terms of service, and support information are all available at lttstudio.top. Thank you for your review."

---

## 🎯 What MUST be visible in the recording

These are TikTok reviewer's actual checklist items — **mỗi cảnh này nếu thiếu là FAIL**:

| ✓ | Item | Scene |
|---|---|---|
| ☐ | **Privacy Policy URL** opened in browser, content readable | [00:15-00:35] |
| ☐ | **Terms URL** opened in browser | [00:15-00:35] |
| ☐ | **"Continue with TikTok" button** with official logo | [00:50-01:00] |
| ☐ | **Pre-OAuth Disclosure Modal** with each scope + reason | [00:55-01:10] |
| ☐ | **TikTok's authorize URL** visible in browser bar | [01:10-01:15] |
| ☐ | **TikTok's scope list** on authorize page | [01:10-01:15] |
| ☐ | **Successful redirect** back to app, account appears | [01:20-01:30] |
| ☐ | **Privacy level dropdown** (user selectable, not pre-set) | [02:05-02:15] |
| ☐ | **Comment / Duet / Stitch toggles** | [02:15-02:25] |
| ☐ | **AI Generated checkbox** (user-controlled) | [02:25-02:30] |
| ☐ | **Branded content checkbox** | [02:25-02:30] |
| ☐ | **Compliance acknowledgement** + Confirm button | [02:30-02:35] |
| ☐ | **Video appearing on TikTok** account after publish | [02:55-03:00] |
| ☐ | **Disconnect / revoke flow** | [03:00-03:10] |

---

## 📤 Upload Instructions

```
1. Export OBS recording:
   - Format: MP4 (H.264)
   - Resolution: 1920×1080
   - Bitrate: 8-12 Mbps
   - Audio: AAC 192k

2. Upload to YouTube:
   - Title:       "LTTStudio VideoBot — TikTok Content Posting API Audit Demo"
   - Visibility:  ⚠️ UNLISTED (NOT private — reviewers must be able to watch
                  with the direct link)
   - Description:
       "Audit demo for LTTStudio VideoBot, a Windows desktop app integrating
        TikTok Content Posting API v2 and Login Kit. Shows complete OAuth
        consent flow with mandatory pre-authorization disclosure, audit
        readiness dashboard, and per-publish user confirmation including
        privacy level selection, interaction toggles, AI/branded disclosure.

        Privacy: https://lttstudio.top/legal/privacy.html
        Terms:   https://lttstudio.top/legal/terms.html
        Support: support@lttstudio.top"

3. Copy the YouTube unlisted URL

4. Paste into TikTok Developer Portal:
   My Apps → [your app] → Audit Submission → "Demo Video URL" field
```

---

## ⚠️ Common Rejection Reasons (Avoid these)

- ❌ Video < 60s or > 5 min
- ❌ Doesn't show pre-OAuth disclosure modal
- ❌ Doesn't show full OAuth flow (browser URL + TikTok authorize page)
- ❌ Doesn't show the enhanced consent dialog with all 6 sections
- ❌ Privacy level pre-set instead of user-selected
- ❌ Doesn't show video actually appearing on TikTok account
- ❌ Doesn't show disconnect/revoke flow
- ❌ Audio muffled / no voice-over
- ❌ Wrong language (use English; Vietnamese subtitle OK)
- ❌ Video set to "Private" on YouTube — reviewers cannot watch
- ❌ Submit a video that shows a TT account already-connected (must demo the connect flow live)

---

## 🎤 Voice-over Tips

1. Speak slowly and clearly — non-native reviewers will rewatch
2. Pause 0.5s after key UI moments (modal appears, button clicked)
3. Don't fill silence with "uh", "um" — re-record if needed
4. If your English accent is heavy, use ElevenLabs or similar TTS instead of live mic
5. Total word count target: ~450 words for 3-minute video (~150 wpm)

---

## 🛠️ OBS Studio Settings (quick reference)

```
Settings → Output:
  Output Mode: Advanced
  Recording → Type: Standard
  Format: mp4
  Encoder: NVENC H.264 (if NVIDIA GPU) or x264
  Rate Control: CBR
  Bitrate: 10000 Kbps
  Keyframe Interval: 2

Settings → Audio:
  Sample Rate: 48 kHz
  Mic/Aux: your microphone
  Filter on Mic: Noise Suppression (RNNoise)

Settings → Video:
  Base Canvas: 1920×1080
  Output: 1920×1080
  Common FPS: 30
```
