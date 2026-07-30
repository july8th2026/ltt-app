# ⏱️ 02 — TIMING REFERENCE

> Bảng sync chính xác giữa **video OBS** và **10 file voice MP3**.
> In ra hoặc mở song song khi edit trong CapCut.

---

## Bảng sync chính

| Scene | File MP3 | Start | End | Dur | Hành động video trong khoảng |
|-------|----------|-------|-----|-----|------------------------------|
| 01 | `scene_01_opening.mp3` | 00:00 | 00:15 | 15s | Opening slide (PNG full screen) |
| 02 | `scene_02_privacy.mp3` | 00:15 | 00:35 | 20s | Browser show Privacy + Terms URL |
| 03 | `scene_03_overview.mp3` | 00:35 | 00:50 | 15s | Pan qua 9 tabs bot |
| 04 | `scene_04_oauth.mp3` | 00:50 | 01:30 | 40s | Click "Continue with TikTok" → Disclosure modal → OAuth → callback → account hiện |
| 05 | `scene_05_audit.mp3` | 01:30 | 01:50 | 20s | Tab Audit Dashboard show 11 checks ✅ |
| 06 | `scene_06_form.mp3` | 01:50 | 02:10 | 20s | Fill form Manual TikTok (file + title) |
| 07 | `scene_07_consent.mp3` | 02:10 | 02:40 | 30s | Open consent dialog → pan qua 5 sections → tick confirm |
| 08 | `scene_08_upload.mp3` | 02:40 | 03:00 | 20s | Upload progress + success log + show video trên TT |
| 09 | `scene_09_disconnect.mp3` | 03:00 | 03:10 | 10s | Disconnect TT account |
| 10 | `scene_10_closing.mp3` | 03:10 | 03:15 | 5s  | Closing slide |

**Tổng**: 3 phút 15 giây.

---

## Quy tắc sync

### Trường hợp 1: Voice ngắn hơn cảnh ✅
```
Cảnh: ──────────────────────  (20s)
Voice: ─────────────           (15s)
→ Im lặng 5s cuối (OK, tự nhiên — đừng kéo voice giãn ra)
```

### Trường hợp 2: Voice dài hơn cảnh ⚠️
```
Cảnh: ─────────────             (15s)
Voice: ──────────────────       (20s)
→ Cách 1: Slow video xuống 0.9x → tăng độ dài cảnh
→ Cách 2: Cắt bớt voice (trim cuối)
→ Cách 3: Speed up voice 1.1x trong CapCut (ít méo tiếng)
```

### Trường hợp 3: Voice và cảnh sync chính xác ✅
→ Không cần adjust gì.

---

## Lưu ý từng cảnh

### Scene 04 — quan trọng nhất ⭐⭐⭐
- Voice ~35s, cảnh ~40s → có ~5s đệm cuối
- **TT reviewer DỪNG nhiều ở cảnh này** — đảm bảo disclosure modal hiển thị **đầy đủ 4-6 giây** trước khi voice nhắc "Only after the user reads this disclosure..."

### Scene 07 — quan trọng nhất ⭐⭐⭐
- Voice ~40s, cảnh ~30s — voice DÀI HƠN cảnh!
- → Cách xử lý:
  - **Cách A** (đơn giản): Bắt đầu voice sớm 5s — voice fade-in lúc dialog đang mở (02:05 thay vì 02:10)
  - **Cách B**: Slow video phần dialog 0.9x — kéo dài cảnh thành 35s
  - **Cách C**: Cắt bớt 1-2 câu voice (giảm còn 30s)

### Scene 01, 02, 10 — slide tĩnh
- Cảnh là PNG, voice ngắn hơn → im lặng cuối là tự nhiên.
- Có thể thêm nhạc nền nhẹ -20dB (instrumental, no copyright) nếu thấy quá im.

---

## Audio level recommendation

| Track | Volume |
|---|---|
| Voice-over ElevenLabs | **0 dB** (gốc) |
| (Optional) Nhạc nền | **-20 dB** (rất nhẹ, không lấn voice) |
| Audio gốc video OBS | **MUTED** (0%) |
| SFX click button (optional) | **-15 dB** |

---

## Khi nào cần adjust speed?

Voice ElevenLabs **mặc định ở Speed 1.0** = phù hợp đa số cảnh.

Nếu cảm thấy:
- **Voice đọc quá nhanh** (đặc biệt scene 04 + 07): trong ElevenLabs settings, giảm Speed xuống 0.95
- **Voice đọc quá chậm** (cảnh 01 + 10 ngắn): giữ Speed 1.0 hoặc tăng 1.05
- **Cần đọc nhấn mạnh** (e.g. "MANDATORY pre-authorization"): chỉnh Stability 0.30-0.40 (emotional hơn)

---

## Checklist sync xong

```
□ 10 file MP3 đã đặt đúng vị trí timestamp trong CapCut timeline
□ Audio gốc video OBS đã MUTE
□ Voice nghe khớp với hành động video (không nói "click button" khi chưa thấy click)
□ Tổng video = 3:15 ± 5 giây
□ Không có khoảng > 3 giây hoàn toàn im lặng
```

---

**Sang Bước 3**: Mở `03_CAPCUT-EDIT-GUIDE.md` để hướng dẫn cụ thể thao tác trong CapCut.
