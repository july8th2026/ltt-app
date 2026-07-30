# Voice-Over Scripts cho ElevenLabs — Demo v3 (13 scenes)

> **Cách dùng**:
> 1. Vào https://elevenlabs.io/app/speech-synthesis
> 2. Chọn voice (đề xuất: **Adam** male, **Brian** male, hoặc **Bella** female — giọng professional)
> 3. Settings (gear icon):
>    - **Stability**: 0.50 (vừa phải, không robotic, không quá emotional)
>    - **Similarity Boost**: 0.75
>    - **Style Exaggeration**: 0.0
>    - **Speaker Boost**: ON
>    - **Speed**: 1.0
> 4. Paste TỪNG đoạn dưới đây (1 đoạn/scene) → Generate → Download MP3
> 5. **Lưu với tên file CHÍNH XÁC** như spec dưới (để teleprompter auto-detect):
>    `tools/demo_v2/output/voice/01_intro.mp3`
>    `tools/demo_v2/output/voice/02_privacy_terms.mp3`
>    ... etc
> 6. **Replace** các file MP3 edge-tts hiện có bằng file ElevenLabs (cùng tên)
> 7. Chạy `03_teleprompter.py` — auto dùng ElevenLabs MP3s

**Tổng character count**: ~3,000 / 10,000 free tier — đủ generate hết + dư cho re-generate.

---

## Scene 01 — Intro slide (~10s)
**File output**: `tools/demo_v2/output/voice/01_intro.mp3`

```
LTTStudio VideoBot. TikTok Content Posting API integration. Direct Post audit demonstration.
```

---

## Scene 02 — Privacy + Terms walkthrough (~28s) — REQ-4: Content Sharing Guidelines compliance
**File output**: `tools/demo_v2/output/voice/02_privacy_terms.mp3`

```
Before connecting any TikTok account, our published Privacy Policy at lttstudio dot top slash legal slash privacy explicitly lists every piece of TikTok data we access: open ID, display name, avatar URL, access token, and refresh token. All tokens are encrypted at rest using Fernet, machine-bound, and never leave the user's computer. Terms of Service are at the same domain.
```

**ElevenLabs tips**: viết "lttstudio dot top slash legal slash privacy" rõ hơn URL — TTS đọc tự nhiên hơn.

---

## Scene 03 — Bot interface tour (~15s)
**File output**: `tools/demo_v2/output/voice/03_bot_overview.mp3`

```
This is LTTStudio VideoBot. The interface has dedicated tabs for TikTok account management, manual posting, and an audit compliance dashboard. We start by connecting a TikTok account.
```

---

## Scene 04 — App-side OAuth disclosure modal (~23s) ⭐ CRITICAL
**File output**: `tools/demo_v2/output/voice/04_oauth_app_disclosure.mp3`

```
Clicking Continue with TikTok triggers our mandatory pre-authorization disclosure modal. The user sees every scope we will request, the exact reason for each, and instructions on how to revoke access later — both inside our app and through tiktok dot com directly. The OAuth flow only starts after the user explicitly clicks Continue.
```

---

## Scene 05 — TikTok authorization page (~23s) ⭐⭐⭐ TT REQ #1
**File output**: `tools/demo_v2/output/voice/05_tiktok_authorize_page.mp3`

```
The user is redirected to TikTok's official authorization page at tiktok dot com slash v 2 slash auth slash authorize. The user sees the requested scopes — user info basic, video upload, video publish — and clicks Authorize to grant access. Our app uses P K C E for security throughout this flow.
```

**ElevenLabs tips**:
- "v 2" với space để đọc "vee two"
- "P K C E" với spaces để đọc từng chữ

---

## Scene 06 — Callback redirect + account connected (~16s)
**File output**: `tools/demo_v2/output/voice/06_callback_return.mp3`

```
TikTok redirects to our HTTPS callback page at lttstudio dot top, which forwards the authorization code back to the local app. The TikTok account is now connected and appears in the account list with avatar and display name.
```

---

## Scene 07 — Audit compliance dashboard (~22s)
**File output**: `tools/demo_v2/output/voice/07_audit_dashboard.mp3`

```
Inside the app we built a real-time audit compliance dashboard. It verifies every TikTok policy requirement — client credentials, HTTPS redirect URI, privacy and terms URLs reachable, scope set correctly, user-confirmation required, and safe defaults. All eleven checks pass.
```

---

## Scene 08 — Post-to-TikTok form (~18s) ⭐⭐⭐ TT REQ #2 part 1
**File output**: `tools/demo_v2/output/voice/08_manual_form.mp3`

```
To post a video, the user navigates to the Manual TikTok tab. The user selects a video file, types a title, chooses the target account from the dropdown, and selects Direct Post Public as the post type. Then clicks the Post to TikTok button.
```

---

## Scene 09 — Per-publish consent dialog (~47s) ⭐⭐⭐ TT REQ #2 part 2 + REQ #4
**File output**: `tools/demo_v2/output/voice/09_consent_dialog.mp3`

```
Before any API call, this comprehensive consent dialog appears. The video summary at the top shows title, post type, and target account. The privacy dropdown is populated dynamically from TikTok's creator info endpoint and shows all options the user is permitted: Public to everyone, Mutual follow friends, and Self only. It is never pre-set — the user must select. Three interaction toggles let the user allow comments, duets, and stitches. Two disclosure checkboxes capture AI-generated and branded-content declarations. Finally, the user must tick the compliance acknowledgement before the Confirm and Post button enables.
```

---

## Scene 10 — Upload progress (~22s) ⭐⭐⭐ TT REQ #3
**File output**: `tools/demo_v2/output/voice/10_upload_progress.mp3`

```
After the user confirms, the bot calls TikTok's video init endpoint, uploads the file in chunks, and polls the publish status endpoint. The status bar shows each phase clearly: init, upload, processing, and finally publish complete. The publish ID and timestamp are logged to the audit trail for compliance.
```

---

## Scene 11 — Verify on TikTok PUBLIC (~19s)
**File output**: `tools/demo_v2/output/voice/11_verify_public.mp3`

```
We verify the result by opening TikTok web in the browser. The video appears on the user's profile feed exactly as configured — public to everyone, with the chosen interaction settings. The audit log file records every detail of this publish event for transparency.
```

---

## Scene 12 — Disconnect / revoke (~19s)
**File output**: `tools/demo_v2/output/voice/12_disconnect.mp3`

```
Users can disconnect at any time. The bot calls TikTok's revoke endpoint, then deletes the encrypted token from disk. The account is fully removed. Users can also revoke our app directly from tiktok dot com slash setting slash manage apps.
```

---

## Scene 13 — Outro (~8s)
**File output**: `tools/demo_v2/output/voice/13_outro.mp3`

```
Thank you for reviewing LTTStudio VideoBot. Documentation at lttstudio dot top.
```

---

# 📊 Verify character count

| Scene | English chars |
|-------|---------------|
| 01 Intro                    | 95   |
| 02 Privacy + Terms          | 410  |
| 03 Bot overview             | 200  |
| 04 OAuth app disclosure ⭐  | 360  |
| 05 TikTok auth page ⭐⭐⭐  | 320  |
| 06 Callback                 | 230  |
| 07 Audit dashboard          | 310  |
| 08 Manual form ⭐⭐⭐       | 270  |
| 09 Consent dialog ⭐⭐⭐   | 680  |
| 10 Upload progress ⭐⭐⭐  | 340  |
| 11 Verify public            | 280  |
| 12 Disconnect               | 250  |
| 13 Outro                    | 80   |
| **TOTAL**                   | **~3,830** / 10,000 free tier |

→ Còn dư ~6,170 chars — đủ generate lại các scene chưa ưng.

---

# 🎙 ElevenLabs voice recommendations

| Voice | Gender | Best for |
|-------|--------|----------|
| **Adam** (`pNInz6obpgDQGcFmaJgB`) | Male | Default — clear American accent |
| **Brian** (`nPczCjzI2devNBz1zQrb`) | Male | More formal, business tone |
| **Bella** (`EXAVITQu4vr4xnSDxMaL`) | Female | Friendly, professional |
| **Antoni** (`ErXwobaYiN019PkySvjV`) | Male | Slow + clear (audit-friendly) |

**Khuyến nghị**: dùng **Antoni** vì:
- Tốc độ nói tự nhiên (~150 wpm, không quá nhanh)
- Phát âm rõ ràng (audit reviewer có thể không phải native English)
- Pause tự nhiên ở dấu câu

---

# ⚙ Settings tối ưu cho audit demo

```
Stability:          0.45   ← nhẹ hơn 0.50 mặc định để giọng có cảm xúc, không robotic
Similarity Boost:   0.80   ← cao để giữ giọng nhất quán giữa các scene
Style Exaggeration: 0.0    ← off (formal context)
Speaker Boost:      ON     ← giữ giọng rõ ràng
Speed:              0.95   ← chậm hơn 5% — audit-friendly
```

---

# 🚀 Quy trình batch generation

1. Mở 13 tab ElevenLabs (mỗi tab 1 scene)
2. Paste text → Generate → Download → đổi tên đúng spec file
3. Move tất cả MP3 vào `tools/demo_v2/output/voice/` (override edge-tts MP3s)
4. Verify: chạy `python tools/demo_v2/scene_config.py` (in danh sách scenes)
5. Test: `python tools/demo_v2/03_teleprompter.py --no-autoplay` (click Play từng scene nghe thử)
6. Khi voice OK → bật autoplay, mở OBS, record!
