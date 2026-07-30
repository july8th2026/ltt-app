# FB App Review — 3-Video Screencast Tool

Records **3 separate screencasts**, one per permission, for the Facebook App
Review (Advanced Access) submission:

| Video | Permission | Save as | ~length |
|-------|------------|---------|---------|
| 1 | `pages_show_list` | `pages_show_list.mp4` | ~38s |
| 2 | `pages_manage_posts` | `pages_manage_posts.mp4` | ~56s |
| 3 | `pages_read_engagement` | `pages_read_engagement.mp4` | ~24s |

## Pipeline
| File | Purpose |
|------|---------|
| `fb_scenes.py` | Single source of truth — scenes, voice text (EN/VI), on-screen actions |
| `gen_voice.py` | Generate one narration MP3 per scene (edge-tts, free) → `output/voice/` |
| `teleprompter.py` | Voice-driven guide, **per video**; plays narration + shows actions + auto-advances |
| `VOICE_TEXT.md` | The narration text (EN + VI) — for reference / ElevenLabs upgrade |

## How the recording works
The teleprompter runs on a **second monitor** (or a phone via remote desktop).
OBS records the **main** screen where you operate the bot. The teleprompter
plays the scene narration (OBS captures it as desktop audio) and shows you the
exact clicks to make; it auto-advances when each narration clip ends.

## Workflow (~30 min)

### 1. Generate voice (once)
```
.venv\Scripts\python.exe -m tools.demo_fb.gen_voice          # English (default)
.venv\Scripts\python.exe -m tools.demo_fb.gen_voice --lang vi  # Vietnamese
```
→ 9 MP3s in `tools/demo_fb/output/voice/`. (Already generated.)

### 2. Set up OBS (once)
- Install OBS Studio → add a **Display Capture** source (main monitor).
- Enable **Desktop Audio** (so the narration is captured). Mute the mic.
- Output: MP4, 1280×720 or 1080p, 30fps.

### 3. Record each video
For each video (do them one at a time):
1. Prepare the bot state (e.g. Video 1: disconnect the account so the OAuth
   consent shows fresh).
2. **Start OBS recording.**
3. Run the teleprompter for that video on the 2nd monitor:
   ```
   .venv\Scripts\python.exe -m tools.demo_fb.teleprompter --video 1
   .venv\Scripts\python.exe -m tools.demo_fb.teleprompter --video 2
   .venv\Scripts\python.exe -m tools.demo_fb.teleprompter --video 3
   ```
4. Press **Space** to start each scene; do the on-screen actions while the
   narration plays. It auto-advances. When it says "STOP OBS now" → **stop OBS**.
5. Rename the OBS file to `pages_show_list.mp4` / `pages_manage_posts.mp4` /
   `pages_read_engagement.mp4`.

### 4. (Optional) Better voice via ElevenLabs
Paste the text from `VOICE_TEXT.md` into https://elevenlabs.io, generate, and
save the MP3s with the **same filenames** into `output/voice/` (overwrite).

## Tips
- Do NOT show passwords, tokens, or the App Secret on screen.
- Only the test Page should be visible (avoid other real brand Pages).
- Keep the mouse movements slow and clear.
- `--lang vi` for Vietnamese narration; `--no-autoplay` to advance manually.
