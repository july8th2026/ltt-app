# Voice Scripts v3 — TikTok Direct Post Audit Demo

> **Mục tiêu**: Generate 13 voice MP3 files với ElevenLabs cho demo video submit TikTok audit Direct Post tier
>
> **Khớp với**: `scripts/_demo_record_v3.py` — 13 scenes auto-driven

---

## 📋 TikTok Audit Requirements Coverage

| Requirement | Covered by Scene |
|-------------|------------------|
| REQ-1: TikTok authorization page user flow | Scene 5 ⭐ |
| REQ-2: Export/Post-to-TikTok page on app | Scene 8 + Scene 9 ⭐ |
| REQ-3: User flow AFTER Post-to-TikTok triggered | Scene 10 ⭐ |
| REQ-4: Content Sharing Guidelines compliance | Scenes 2, 9, 12 |

---

## 🎙 ElevenLabs Settings (khuyến nghị)

1. Vào https://elevenlabs.io/app/speech-synthesis
2. Chọn voice (recommend):
   - **Antoni** (`ErXwobaYiN019PkySvjV`) — slow + clear, audit-friendly ⭐
   - Hoặc **Adam** (`pNInz6obpgDQGcFmaJgB`) — default American male
   - Hoặc **Brian** (`nPczCjzI2devNBz1zQrb`) — formal business tone
3. Settings (gear icon):
   - **Stability**: 0.45
   - **Similarity Boost**: 0.80
   - **Style Exaggeration**: 0.0
   - **Speaker Boost**: ON
   - **Speed**: 0.95 (chậm hơn 5% — audit-friendly)
4. Paste TỪNG SCENE → Generate → Download MP3 → đổi tên đúng spec

**Lưu vào**: `voiceover/scene_NN.mp3` (folder mới trong project)

**Tổng character count**: ~3,200 / 10,000 free tier — đủ generate hết + dư cho re-generate.

---

## Scene 01 — Opening slide (~12s, 150 chars)

**Trùng với**: `scene_1_opening` trong `_demo_record_v3.py` (10s slide)
**File output**: `voiceover/scene_01_opening.mp3`

```
LTTStudio VideoBot. TikTok Content Posting API integration. Direct Post audit demonstration.
```

---

## Scene 02 — Privacy + Terms walkthrough (~28s, 420 chars) — REQ-4

**Trùng với**: `scene_2_privacy_terms` (22s — bot opens privacy + terms in browser)
**File output**: `voiceover/scene_02_privacy_terms.mp3`

```
Before connecting any TikTok account, our published Privacy Policy at lttstudio dot top slash legal slash privacy explicitly lists every piece of TikTok data we access: open ID, display name, avatar URL, access token, and refresh token. All tokens are encrypted at rest using Fernet, machine-bound, and never leave the user's computer. Terms of Service are at the same domain.
```

**ElevenLabs tip**: Viết "lttstudio dot top slash legal slash privacy" rõ hơn URL — TTS đọc tự nhiên hơn.

---

## Scene 03 — Bot interface tour (~14s, 200 chars)

**Trùng với**: `scene_3_bot_overview` (10s — pan 6 tabs)
**File output**: `voiceover/scene_03_bot_overview.mp3`

```
This is LTTStudio VideoBot. The interface has dedicated tabs for TikTok account management, manual posting, an audit compliance dashboard, and a real-time monitor. We start by connecting a TikTok account.
```

---

## Scene 04 — OAuth app disclosure modal (~22s, 360 chars) ⭐ REQ-4

**Trùng với**: `scene_4_oauth_app_disclosure` (15s — disclosure modal opens)
**File output**: `voiceover/scene_04_oauth_app_disclosure.mp3`

```
Clicking Continue with TikTok triggers our mandatory pre-authorization disclosure modal. The user sees every scope we will request, the exact reason for each, and instructions on how to revoke access later — both inside our app and through tiktok dot com directly. The OAuth flow only starts after the user explicitly clicks Continue.
```

---

## Scene 05 — TikTok authorization page (~22s, 340 chars) ⭐⭐⭐ TT REQ #1

**Trùng với**: `scene_5_tiktok_authorize` (18s — user manual login + Authorize)
**File output**: `voiceover/scene_05_tiktok_authorize.mp3`

```
The user is now on TikTok's official authorization page at tiktok dot com slash v 2 slash auth slash authorize. The user reviews the requested scopes — user info basic, video upload, and video publish — and clicks Authorize to grant access. Our app uses P K C E for security throughout this flow.
```

**ElevenLabs tip**:
- "v 2" với space để đọc "vee two"
- "P K C E" với spaces để đọc từng chữ

---

## Scene 06 — Callback return (~14s, 240 chars)

**Trùng với**: `scene_6_callback_return` (8s — account appears in bot)
**File output**: `voiceover/scene_06_callback_return.mp3`

```
TikTok redirects to our HTTPS callback page at lttstudio dot top, which forwards the authorization code back to the local app. The TikTok account is now connected and appears in the account list with avatar and display name.
```

---

## Scene 07 — Audit compliance dashboard (~22s, 320 chars)

**Trùng với**: `scene_7_audit_dashboard` (15s — show TT Audit tab)
**File output**: `voiceover/scene_07_audit_dashboard.mp3`

```
Inside the app we built a real-time audit compliance dashboard. It verifies every TikTok policy requirement — client credentials, HTTPS redirect URI, privacy and terms URLs reachable, scope set correctly, user confirmation required, and safe defaults. All eleven checks pass.
```

---

## Scene 08 — Post-to-TikTok form (~22s, 290 chars) ⭐⭐⭐ TT REQ #2 part 1

**Trùng với**: `scene_8_manual_form` (18s — fill video, title, select Direct Post Public)
**File output**: `voiceover/scene_08_manual_form.mp3`

```
To post a video, the user navigates to the Manual TikTok tab. The user selects a video file, types a title, and chooses the target TikTok account from the dropdown. The post type is set to Direct Post Public. The user then clicks the Post to TikTok button.
```

---

## Scene 09 — Per-publish consent dialog (~45s, 680 chars) ⭐⭐⭐ TT REQ #2 part 2 + REQ-4

**Trùng với**: `scene_9_consent_dialog` (35s — dialog walkthrough then Confirm)
**File output**: `voiceover/scene_09_consent_dialog.mp3`

```
Before any API call, this comprehensive consent dialog appears. The video summary at the top shows title, post type, and target account. The privacy dropdown is populated dynamically from TikTok's creator info endpoint and shows all options the user is permitted: Public to everyone, Mutual follow friends, and Self only. It is never pre-set — the user must select. Three interaction toggles let the user allow comments, duets, and stitches. Two disclosure checkboxes capture AI-generated and branded content declarations. Finally, the user must tick the compliance acknowledgement before the Confirm and Post button enables.
```

---

## Scene 10 — Upload progress (~28s, 380 chars) ⭐⭐⭐ TT REQ #3

**Trùng với**: `scene_10_upload_progress` (25s — engine runs: init → upload → poll → done)
**File output**: `voiceover/scene_10_upload_progress.mp3`

```
After the user confirms, the bot calls TikTok's video init endpoint, uploads the file in chunks, and polls the publish status endpoint. The status bar shows each phase clearly: init, upload, processing, and finally publish complete. The publish ID and timestamp are logged to our audit trail file for compliance.
```

---

## Scene 11 — Verify video on TikTok (~16s, 240 chars)

**Trùng với**: `scene_11_verify_public` (12s — opens TikTok profile in browser)
**File output**: `voiceover/scene_11_verify_public.mp3`

```
We verify the result by opening TikTok web in the browser. The video appears on the user's profile feed exactly as configured — public to everyone, with the chosen interaction settings preserved.
```

---

## Scene 12 — Disconnect / revoke (~16s, 270 chars) — REQ-4

**Trùng với**: `scene_12_disconnect` (12s — disconnect button + token removal)
**File output**: `voiceover/scene_12_disconnect.mp3`

```
Users can disconnect at any time. The bot calls TikTok's revoke endpoint, then deletes the encrypted token from disk. The account is fully removed. Users can also revoke our app directly from tiktok dot com slash setting slash manage apps.
```

---

## Scene 13 — Closing (~10s, 120 chars)

**Trùng với**: `scene_13_closing` (5s closing slide)
**File output**: `voiceover/scene_13_closing.mp3`

```
Thank you for reviewing LTTStudio VideoBot. Privacy, terms, and support information are all available at lttstudio dot top.
```

---

# 📊 Verify character count

| Scene | Chars | Voice ETA | Scene Duration |
|-------|-------|-----------|----------------|
| 01 Opening                    | 150 | ~12s | 10s |
| 02 Privacy + Terms            | 420 | ~28s | 22s |
| 03 Bot overview               | 200 | ~14s | 10s |
| 04 OAuth disclosure ⭐        | 360 | ~22s | 15s |
| 05 TikTok authorize ⭐⭐⭐   | 340 | ~22s | 18s |
| 06 Callback                   | 240 | ~14s | 8s |
| 07 Audit dashboard            | 320 | ~22s | 15s |
| 08 Manual form ⭐⭐⭐        | 290 | ~22s | 18s |
| 09 Consent dialog ⭐⭐⭐      | 680 | ~45s | 35s |
| 10 Upload progress ⭐⭐⭐    | 380 | ~28s | 25s |
| 11 Verify public              | 240 | ~16s | 12s |
| 12 Disconnect                 | 270 | ~16s | 12s |
| 13 Closing                    | 120 | ~10s | 5s |
| **TOTAL**                     | **4,010** | **~4:30** | **3:25** |

> **Note**: Voice ETA hơi dài hơn scene duration vì TTS đọc chậm. Trong CapCut bạn có thể:
> - Speed up voice 1.05x (giữ pitch)
> - Hoặc rút ngắn text các scene quá dài
> - Hoặc kéo dài scene duration tương ứng (edit `_demo_record_v3.py` dwell times)

---

# 🚀 Quy trình thực hiện

## Bước 1 — Generate 13 voice MP3 với ElevenLabs (15-20 phút)

1. Tạo folder mới: `voiceover/` trong project root
2. Mở 13 tab ElevenLabs (mỗi tab 1 scene) hoặc generate tuần tự
3. Settings: Antoni voice, Stability 0.45, Similarity 0.80, Speed 0.95
4. Paste text từng scene → Generate → Download → đổi tên đúng spec
5. Verify 13 file trong `voiceover/scene_01_opening.mp3` → `scene_13_closing.mp3`

## Bước 2 — Preflight bot state (3 phút)

```
□ Bot đã chạy: python main.py
□ Account klcloset96 DISCONNECTED (tab TikTok Accounts → Disconnect)
□ Test video sẵn ở: C:\Users\Administrator\Downloads\clip_02 (4).mp4
□ Chrome browser default + ready to login TikTok (klcloset96 password sẵn)
□ Notifications tắt (Zalo, Messenger, Discord)
□ Mic Windows MUTED nếu không narrate trực tiếp
```

## Bước 3 — Start OBS recording

- Display Capture (fullscreen 1920x1080)
- Audio Output Capture (desktop audio — bắt voice từ player nếu dùng MP3)
- Bitrate ~8000 Kbps (file ~30-40 MB, dưới TikTok 50MB limit)

## Bước 4 — Run demo recorder

```bash
cd "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook"
.venv\Scripts\python.exe scripts\_demo_record_v3.py
```

Script tự động:
- Hiện opening slide (10s)
- Mở Privacy + Terms URLs trong browser
- Pan qua 6 tabs bot
- Click Continue with TikTok → disclosure modal
- Click Tiếp tục → OAuth URL dialog mở
- Click "Mở Chrome ở máy này" → Chrome mở TikTok auth
- **PAUSE 90s**: bạn login TikTok + click Authorize trong Chrome
- Khi account appears → tiếp tục các scenes:
  - Audit dashboard
  - Manual TT form (auto fill video + title)
  - Click Post → consent dialog → auto tick + Confirm
  - Wait 25s engine upload
  - Open TikTok profile in browser
  - Disconnect
  - Closing slide

## Bước 5 — Stop OBS recording

Sau khi closing slide hiện ra ~5s, script log "DEMO COMPLETE" → STOP OBS.

## Bước 6 — CapCut compose (10 phút)

1. Import: raw OBS recording
2. Import 13 ElevenLabs MP3 (drag vào audio track)
3. Align từng MP3 với timestamp scene tương ứng:
   - scene_01 → 0:00 (over opening slide)
   - scene_02 → ~0:10 (over privacy/terms walk)
   - scene_03 → ~0:32 (over tab pan)
   - ... etc
4. Adjust volume: voice MP3 ở 0 dB, mute desktop audio nếu có
5. (Optional) Add subtitle (CapCut Auto Caption từ English voice)
6. Export:
   - 1080p, 30fps, 8 Mbps, MP4 H.264
   - File ~30-40 MB
7. Save as `Demo-TikTok-DirectPost-Audit-v3.mp4`

## Bước 7 — Upload vào TikTok audit form

Step 3 "Supporting documents":
1. Upload file MP4 vừa export
2. Field "API response data fields": paste text từ Claude (xem turn trước)
3. Click Next → Review → Submit

→ Email confirmation TikTok trong 5-15 ngày.

---

# ⚠ Lỗi thường gặp

| Lỗi | Cách fix |
|-----|----------|
| Bot không tự click Continue | Verify account đã disconnect trước khi chạy script |
| OAuth URL dialog không mở | Bot version cũ — update lên v2.2+ |
| Chrome không tự login | Login TikTok trong Chrome trước khi record (cùng profile) |
| Consent dialog không có dropdown 3 options | Run `python scripts/_check_tiktok_capabilities.py` verify FULL APPROVAL |
| Upload fail | Verify video < 64MB single chunk (đã fix chunk algorithm) |
| File MP4 > 50MB | Re-export CapCut bitrate 6 Mbps |
