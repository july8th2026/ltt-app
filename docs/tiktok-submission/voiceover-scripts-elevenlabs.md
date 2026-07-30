# Voice-Over Scripts cho ElevenLabs — 10 cảnh

> **Cách dùng**:
> 1. Vào https://elevenlabs.io/app/speech-synthesis
> 2. Chọn voice (đề xuất: Adam / Charlie / Brian)
> 3. Settings: Stability 0.50, Similarity 0.75, Speed 1.0
> 4. Paste TỪNG đoạn dưới đây (1 lần/cảnh) → Generate → Download MP3
> 5. Lưu vào folder `voiceover/scene_01.mp3`, `scene_02.mp3`, ...
> 6. Mở CapCut → import + match timestamp tương ứng

**Tổng character count: ~3,100 / 10,000 free tier** — đủ thoải mái.

---

## Scene 01 — Opening (15s, ~250 chars)

```
Hello, this is the audit demo of LTTStudio VideoBot, a Windows desktop application that helps Vietnamese content creators schedule and publish short-form videos to TikTok using the official Content Posting API v2 and Login Kit. The entire flow runs locally on the user's machine. No cloud server, no third-party data sharing.
```

**File output**: `voiceover/scene_01_opening.mp3`

---

## Scene 02 — Privacy & Terms URL (20s, ~350 chars)

```
Before connecting any TikTok account, here is our published Privacy Policy at lttstudio.top slash legal slash privacy dot html. It explicitly lists every piece of TikTok data we access — open_id, display name, avatar URL, access token, refresh token — and our retention policy. All tokens are encrypted at rest using AES one twenty-eight Fernet and never leave the user's computer. The Terms of Service link is also accessible at lttstudio.top slash legal slash terms dot html.
```

**File output**: `voiceover/scene_02_privacy.mp3`

**Note**: ElevenLabs đọc URL khá lạ → tôi đã viết "slash" và "dot" thay vì ký tự để TTS đọc tự nhiên hơn.

---

## Scene 03 — Bot Overview (15s, ~180 chars)

```
Here is the LTTStudio VideoBot interface. We have dedicated tabs for TikTok account management, manual posting, and an audit dashboard which I'll show in a moment. Let's start by connecting a TikTok account.
```

**File output**: `voiceover/scene_03_overview.mp3`

---

## Scene 04 — OAuth Flow + Disclosure Modal (40s, ~550 chars) ⭐⭐⭐

```
Clicking 'Continue with TikTok' triggers our mandatory pre-authorization disclosure modal. Per TikTok policy, the user sees every scope we will request, the exact reason we need each one, and instructions on how to revoke access later — both inside our app and through tiktok.com directly. Only after the user reads this disclosure and explicitly clicks 'Continue' does the OAuth flow start. We use PKCE for security. After TikTok's authorize screen, the code returns to our HTTPS callback at lttstudio.top, then locally to the app. The TikTok account is now connected and visible in the list.
```

**File output**: `voiceover/scene_04_oauth.mp3`

---

## Scene 05 — Audit Dashboard (20s, ~440 chars) ⭐

```
We've built a real-time audit-readiness dashboard inside the application itself. It verifies every TikTok compliance requirement — client credentials present, redirect URI uses HTTPS, privacy and terms URLs reachable, privacy policy mentions TikTok by name, official login button branding present, demo video script exists, scope set correctly, audit flags consistent, user-confirmation required, and a safe SELF_ONLY default. All eleven checks pass. The right panel shows each OAuth scope with its justification.
```

**File output**: `voiceover/scene_05_audit.mp3`

---

## Scene 06 — Manual Form (15s, ~180 chars)

```
To post a video, the user fills the form on the Manual TikTok tab and clicks the post button. Our app first calls TikTok's creator_info query endpoint to fetch the user's current account-level settings.
```

**File output**: `voiceover/scene_06_form.mp3`

---

## Scene 07 — Enhanced Consent Dialog (30s, ~660 chars) ⭐⭐⭐

```
This comprehensive consent dialog now appears. The user sees the video summary, then must actively select a privacy level. The dropdown is populated dynamically from TikTok's creator_info endpoint and shows all options the user is permitted: Public to everyone, Mutual follow friends, and Self only. It is never pre-set — the user must choose. Three interaction toggles let the user allow comments, duets, and stitches. Two disclosure checkboxes capture AI-generated and branded-content declarations as required by TikTok's policy. Finally, the user must tick the compliance acknowledgement before the Confirm and Post button enables. Only on this explicit, per-publish confirmation does the upload proceed.
```

**File output**: `voiceover/scene_07_consent.mp3`

**Note**: Voice updated for the post-audit state where Direct Post is approved. Previous version mentioned "still pending audit" — replaced with current dynamic-dropdown description.

---

## Scene 08 — Upload & Success (20s, ~280 chars)

```
The video uploads in chunks via the Content Posting API. We poll the publish status endpoint until completion. On success, the publish ID and timestamp are logged to the audit trail. The video is now visible on the user's TikTok account, exactly as the user configured — privacy level, interactions, and disclosure flags all reflecting the user's per-publish choice.
```

**File output**: `voiceover/scene_08_upload.mp3`

---

## Scene 09 — Disconnect (10s, ~140 chars)

```
Users can disconnect at any time. The bot calls TikTok's revoke endpoint, then deletes the encrypted token from disk. The account is fully removed.
```

**File output**: `voiceover/scene_09_disconnect.mp3`

---

## Scene 10 — Closing (5s, ~120 chars)

```
That concludes the demo. Privacy policy, terms of service, and support information are all available at lttstudio.top. Thank you for your review.
```

**File output**: `voiceover/scene_10_closing.mp3`

---

## Quy trình tạo voice với ElevenLabs

1. Vào https://elevenlabs.io/app/speech-synthesis
2. Voice → Library → search "Adam" (hoặc voice bạn thích)
3. Settings (gear icon):
   - Stability: **0.50** (vừa phải, không quá robotic, không quá emotional)
   - Similarity Boost: **0.75**
   - Style Exaggeration: **0.0**
   - Speaker Boost: **ON**
4. Paste đoạn Scene 01
5. **Generate** → đợi ~10s
6. **Download** → save as `scene_01_opening.mp3`
7. Lặp lại cho 9 cảnh còn lại
8. **Lưu vào folder mới**: `D:\CODE AI\BOT UP FB + TikTok\BOT UP Facebook\voiceover\`

## Verify tổng character

| Scene | Chars | Cộng dồn |
|---|---|---|
| 01 Opening      | 250  | 250 |
| 02 Privacy      | 350  | 600 |
| 03 Overview     | 180  | 780 |
| 04 OAuth        | 550  | 1,330 |
| 05 Audit        | 440  | 1,770 |
| 06 Form         | 180  | 1,950 |
| 07 Consent      | 620  | 2,570 |
| 08 Upload       | 250  | 2,820 |
| 09 Disconnect   | 140  | 2,960 |
| 10 Closing      | 120  | 3,080 |

**Tổng ≈ 3,080 / 10,000 free tier** — còn dư 6,920 ký tự cho re-generate nếu chưa ưng.

## Mẹo

- **Pre-listen trước khi Download**: nghe thử trong web ElevenLabs. Nếu chỗ nào đọc sai → edit text + Generate lại.
- **Đọc URL**: dùng "slash" / "dot" thay ký tự — TTS đọc tự nhiên hơn.
- **Số**: "AES one twenty-eight" thay "AES-128" — rõ hơn.
- **Tên app**: "LTTStudio VideoBot" — ElevenLabs đọc OK.
- **Pause**: Thêm dấu "—" hoặc "..." để tạo nhịp nghỉ.
