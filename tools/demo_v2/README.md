# Demo Video v3 — TikTok Direct Post Audit Recording

Complete pipeline để quay demo video cho TikTok audit submission.
Aligned chính xác với 4 yêu cầu trong form **Application to request access to Content Posting API**.

## 📋 TikTok audit requirements mapping

| TikTok requirement | Scene(s) covering it |
|--------------------|----------------------|
| **REQ-1**: TikTok authorization page user flow | Scene 5 ⭐⭐⭐ |
| **REQ-2**: Export/Post-to-TikTok page on your app | Scenes 8 + 9 ⭐⭐⭐ |
| **REQ-3**: User flow AFTER Post-to-TikTok action triggered | Scene 10 ⭐⭐⭐ |
| **REQ-4**: Content Sharing Guidelines compliance | Scenes 2, 9, 12 |

→ Mỗi requirement có scene riêng → reviewer dễ identify, không bị reject vì "không thấy chỗ X".

## 🎬 13 scenes (total ~3:00 min plan / ~4:48 min ElevenLabs)

| # | Scene ID | Plan | TT REQ | Critical |
|---|----------|------|--------|----------|
| 1 | 01_intro | 6s | — | |
| 2 | 02_privacy_terms | 22s | REQ-4 | |
| 3 | 03_bot_overview | 10s | — | |
| 4 | 04_oauth_app_disclosure | 15s | — | ⭐ |
| 5 | 05_tiktok_authorize_page | 15s | **REQ-1** | ⭐⭐⭐ |
| 6 | 06_callback_return | 8s | — | |
| 7 | 07_audit_dashboard | 12s | — | |
| 8 | 08_manual_form | 15s | **REQ-2 (p1)** | ⭐⭐⭐ |
| 9 | 09_consent_dialog | 35s | **REQ-2 (p2) + REQ-4** | ⭐⭐⭐ |
| 10 | 10_upload_progress | 22s | **REQ-3** | ⭐⭐⭐ |
| 11 | 11_verify_public | 12s | — | |
| 12 | 12_disconnect | 12s | REQ-4 | |
| 13 | 13_outro | 5s | — | |

---

## 🛠 Toolchain

| File | Purpose |
|------|---------|
| `scene_config.py` | Single source of truth — scene definitions, voice text, action checklists |
| `01_generate_voice.py` | Generate edge-tts MP3 (free, placeholder) — 13 files in `output/voice/` |
| `02_generate_slides.py` | Generate intro + outro PNG slides (1920×1080) |
| `03_teleprompter.py` | **MAIN TOOL** — voice-driven teleprompter with auto-advance |
| `VOICE_TEXT_FOR_ELEVENLABS.md` | Ready-to-paste English text for ElevenLabs (production voice) |

---

## 🚀 Workflow (30-45 phút end-to-end)

### Bước 1 — Pre-generate assets (5 phút, 1 lần)

```bash
cd "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook"

# 1a. Generate 13 voice MP3s (edge-tts, placeholder)
.venv\Scripts\python.exe -X utf8 tools\demo_v2\01_generate_voice.py

# 1b. Generate 2 slides (intro + outro)
.venv\Scripts\python.exe -X utf8 tools\demo_v2\02_generate_slides.py
```

Output:
- `tools/demo_v2/output/voice/*.mp3` (13 files, ~1.8 MB)
- `tools/demo_v2/output/slides/01_intro.png` + `13_outro.png`

### Bước 2 — Generate ElevenLabs voice (15-20 phút)

1. Mở `tools/demo_v2/VOICE_TEXT_FOR_ELEVENLABS.md`
2. Vào https://elevenlabs.io/app/speech-synthesis
3. Chọn voice **Antoni** (slow + clear, audit-friendly) — recommended
4. Settings: Stability 0.45 / Similarity 0.80 / Speed 0.95
5. Paste TỪNG SCENE → Generate → Download → save với tên CHÍNH XÁC như spec
6. Move 13 MP3 vào `tools/demo_v2/output/voice/` (override edge-tts)

> 💡 **Tip**: Generate 1 scene → nghe thử → nếu OK → batch generate 12 scene còn lại với cùng setting.

### Bước 3 — Setup OBS Studio (5 phút, 1 lần)

1. Install OBS từ https://obsproject.com/
2. Sources panel → `+`:
   - **Display Capture** → chọn main monitor (nơi bot/browser sẽ chạy)
   - **Audio Output Capture** → chọn Speakers (để bắt voice từ teleprompter)
3. Settings → Output → Recording:
   - Format: **mp4**
   - Encoder: x264 (hoặc NVENC nếu có NVIDIA)
   - Bitrate: **8000 Kbps** (file ~30-40 MB, dưới TikTok 50 MB limit)
4. Settings → Video: **1920×1080 @ 30fps**
5. Settings → Audio: 48 kHz, AAC 192k

### Bước 4 — Prepare bot state (3 phút, trước mỗi lần quay)

**Trước record**:
1. Bot GUI chạy (`run_gui.bat`) — verify version
2. Tab `🎵 Tài khoản TikTok` → **Disconnect `klcloset96`** nếu đang connect (để OAuth flow LIVE trong demo)
3. Chrome Incognito mở sẵn (Ctrl+Shift+N) — clean OAuth screen
4. Test video sẵn ở `C:\Users\Administrator\Downloads\clip_02 (4).mp4` (hoặc file mp4 5-15s)
5. **Mute mic Windows** (để chỉ thu voice TTS từ desktop audio, không tạp âm)
6. Close apps gây nhiễu (Zalo, Messenger, Discord, browser tabs không cần)

### Bước 5 — RECORD (5 phút)

1. **OBS → Start Recording** (red Record button)
2. Đợi 2-3 giây cho OBS stabilize
3. Mở teleprompter (ideally trên màn hình thứ 2 hoặc phone qua Remote Desktop):
   ```bash
   .venv\Scripts\python.exe -X utf8 tools\demo_v2\03_teleprompter.py
   ```
4. Cho mỗi scene:
   - **Đọc actions list panel trái** (đó là những gì bạn làm trên main screen)
   - Click `▶ Play Voice + Start Timer` (hoặc nhấn **Space**)
   - Voice phát + timer countdown
   - **Thực hiện actions** trên main screen (bot/browser)
   - Khi voice hết phát + buffer 1.5s → teleprompter **AUTO-ADVANCE** sang scene kế tiếp
5. Cuối scene 13, teleprompter hiện "✅ Recording complete — STOP OBS now"
6. **OBS → Stop Recording**

→ Output: file `*.mp4` raw trong `~/Videos/` (OBS default location)

### Bước 6 — Compose final trong CapCut (10 phút)

1. Open CapCut Desktop → New project (16:9, 1080p, 30fps)
2. Import media:
   - `tools/demo_v2/output/slides/01_intro.png` → drag to timeline, set duration **5s**
   - Raw OBS recording → drag tiếp theo
   - `tools/demo_v2/output/slides/13_outro.png` → set duration **5s**
3. (Optional) Add background music — TikTok-friendly royalty-free, volume **-25dB** (background only)
4. (Optional) Add subtitle với CapCut Auto Caption (cho English voice)
5. (Optional) Trim dead air giữa các scene transitions
6. Export:
   - Resolution: **1080p**
   - Frame rate: **30fps**
   - Bitrate: **8 Mbps** (file ~30-40 MB)
   - Format: **MP4 (H.264)**
7. Save as `Demo-tiktok-full-v3-DirectPost-Audit.mp4`

### Bước 7 — Upload vào TikTok audit form (2 phút)

Quay lại form audit submission (Step 3: Supporting Documents):
1. Click **Upload**
2. Select `Demo-tiktok-full-v3-DirectPost-Audit.mp4`
3. Verify file < 50 MB
4. Field 2 "API response data fields": paste text từ message Claude đã gửi
5. Click **Next** → Step 4 Review → **Submit**

→ Email confirmation từ TikTok trong 5-15 ngày.

---

## 🎯 Tips quay đẹp

1. **Slow down**: Đừng vội. Reviewer có thể tua lại, không tua nhanh được.
2. **Pause ở UI quan trọng**: Modal/dialog phải dừng 3-4s cho reviewer kịp đọc.
3. **One-take preferable**: Nếu sai 1 scene, click `Previous` → quay lại. Stitch lại trong CapCut.
4. **Mouse pointer**: Di chuyển chậm + cố ý. Pointer di nhanh khó theo dõi.
5. **Highlight key UI**: Nếu OBS có Source "Mouse Highlight" plugin, bật để pointer có vòng tròn vàng.
6. **Audio levels**: Test trước. Voice MP3 không quá nhỏ (audit reviewer nghe khó). OBS audio meter nên ở -12 đến -6 dB.

## ⚠ Lỗi thường gặp

| Lỗi | Cách fix |
|-----|----------|
| Voice không phát trong OBS | OBS → Audio Mixer → check "Audio Output Capture" volume |
| Voice phát nhưng OBS không thu | OBS Sources → Audio Output Capture → Properties → chọn đúng device |
| Teleprompter auto-advance nhanh quá | Click `Previous` quay lại + dùng `--no-autoplay` để manual |
| MP3 không found | Verify file ở `tools/demo_v2/output/voice/*.mp3` (đúng filenames) |
| File MP4 > 50 MB | Re-export bitrate 6 Mbps trong CapCut |
| Bot UI khác script | Adapt — script là gợi ý, không bắt buộc đúng từng chi tiết |

## 📐 Architecture

```
tools/demo_v2/
├── README.md                       ← this file
├── VOICE_TEXT_FOR_ELEVENLABS.md    ← copy-paste ready for ElevenLabs
├── scene_config.py                 ← 13 scenes, single source of truth
├── 01_generate_voice.py            ← edge-tts placeholder generator
├── 02_generate_slides.py           ← PIL slide generator
├── 03_teleprompter.py              ← MAIN: voice-driven auto-advance GUI
└── output/                         ← generated assets
    ├── voice/                      ← 13 MP3 files (replace with ElevenLabs)
    └── slides/                     ← 01_intro.png + 13_outro.png
```

## 🔄 Iteration workflow

Nếu sau khi quay xong thấy thiếu/sai:
1. Edit `scene_config.py` (thêm/sửa text + duration)
2. Re-run `01_generate_voice.py` (regen edge-tts) OR regenerate ElevenLabs cho scenes thay đổi
3. Re-record CHỈ scene thay đổi qua teleprompter (click `Previous` đến scene đó)
4. Stitch trong CapCut: cắt scene cũ ra, insert scene mới quay lại

Voice timing tự động khớp vì teleprompter đo MP3 duration runtime.
