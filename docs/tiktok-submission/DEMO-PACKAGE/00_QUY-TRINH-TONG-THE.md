# 📋 00 — QUY TRÌNH TỔNG THỂ

> File này tóm tắt **6 bước** từ video OBS đến TikTok approval, có timestamp + checkpoint.

---

## Sơ đồ tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│   📹 Video OBS đã quay (input)                                  │
│   C:\Users\KENLY\Videos\2026-05-18 15-50-04.mp4                 │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Bước 1: REVIEW      │  │  Bước 2: VOICE       │
│  ~5 phút             │  │  ~15 phút            │
│  Kiểm 14 cảnh        │  │  ElevenLabs gen 10   │
│  đủ hay thiếu        │  │  MP3 từ scripts      │
└──────────────────────┘  └──────────────────────┘
              │                       │
              ▼                       ▼
              └─── ─── ┬── ─── ────────
                       ▼
              ┌──────────────────────┐
              │  Bước 3: EDIT        │
              │  ~30 phút            │
              │  CapCut: cắt + chèn  │
              │  voice + export MP4  │
              └──────────────────────┘
                       │
                       ▼
              ┌──────────────────────┐
              │  Bước 4: YOUTUBE     │
              │  ~10 phút            │
              │  Upload Unlisted     │
              └──────────────────────┘
                       │
                       ▼
              ┌──────────────────────┐
              │  Bước 5: TIKTOK      │
              │  ~10 phút            │
              │  Submit Portal       │
              └──────────────────────┘
                       │
                       ▼
              ┌──────────────────────┐
              │  Bước 6: WAIT        │
              │  5-14 ngày           │
              │  TT review email     │
              └──────────────────────┘
```

---

## Bước 1 — Review video OBS (5 phút)

**Mục đích**: Đảm bảo video đủ 14 cảnh BẮT BUỘC. Nếu thiếu → quay phụ riêng trước khi tiếp tục.

**Hành động**:
1. Mở `C:\Users\KENLY\Videos\2026-05-18 15-50-04.mp4` bằng VLC hoặc Windows Media Player
2. Tua từng cảnh, đánh dấu ☑ vào bảng:

```
[00:15] ☐ Privacy Policy URL mở browser
[00:25] ☐ Terms URL mở browser
[00:50] ☐ "Continue with TikTok" button + logo
[00:55] ☐ Pre-OAuth Disclosure Modal (scope + reason)        ⭐
[01:10] ☐ URL bar tiktok.com authorize
[01:12] ☐ TikTok scope list trên authorize page
[01:25] ☐ Redirect về app, account appears
[01:30] ☐ Audit dashboard 11 checks ✅
[02:05] ☐ Privacy dropdown (user CHỌN)                       ⭐
[02:20] ☐ 3 toggles Comment/Duet/Stitch                      ⭐
[02:27] ☐ AI Generated checkbox user-controlled              ⭐
[02:28] ☐ Branded content checkbox                           ⭐
[02:55] ☐ Video xuất hiện trên TikTok
[03:05] ☐ Disconnect/Revoke flow
```

**Kết quả**:
- ✅ Đủ 14/14 → tiếp Bước 2
- ⚠️ Thiếu 1-2 cảnh → quay phụ riêng cảnh đó, ghép vào trong Bước 3
- ❌ Thiếu 3+ cảnh → quay lại toàn bộ bằng `python scripts/_demo_record.py`

---

## Bước 2 — Tạo voice ElevenLabs (15 phút)

**Mục đích**: Có 10 file MP3 lồng vào video.

**Hành động**:
1. Mở [01_VOICE-SCRIPTS.md](01_VOICE-SCRIPTS.md)
2. Đăng nhập https://elevenlabs.io
3. Vào **Speech Synthesis**
4. Chọn voice **Adam** (đề xuất) → Settings: Stability 0.50, Similarity 0.75, Speed 1.0
5. Paste lần lượt 10 đoạn → Generate → Download
6. Lưu vào folder mới `voiceover/` với tên: `scene_01_opening.mp3`, `scene_02_privacy.mp3`, …

**Verify**: Tổng character ≈ 3,080 → còn dư trong free tier (10.000/tháng).

**Checkpoint**: Folder `voiceover/` có đủ 10 file MP3.

---

## Bước 3 — Cắt + dựng CapCut (30 phút)

**Mục đích**: Ghép video OBS + 10 voice MP3 → file MP4 final.

**Hành động**:
1. Mở [03_CAPCUT-EDIT-GUIDE.md](03_CAPCUT-EDIT-GUIDE.md)
2. Mở CapCut Desktop → New Project 1920×1080 30fps
3. Import video OBS + 10 file MP3
4. Mute audio gốc của video OBS
5. Drag từng MP3 vào timeline theo bảng timestamp trong [02_TIMING-REFERENCE.md](02_TIMING-REFERENCE.md)
6. Sync voice với cảnh (nếu cần co giãn 0.95-1.05x)
7. (Optional) Thêm subtitle Vietnamese
8. Export 1920×1080, H.264, 10 Mbps, AAC 192k

**Checkpoint**: File `LTTStudio_VideoBot_TikTok_Audit_Demo.mp4` (~200-300MB) đã sẵn trên máy.

---

## Bước 4 — Upload YouTube Unlisted (10 phút)

**Mục đích**: Lấy link YouTube để paste vào TT portal.

**Hành động**:
1. Mở [04_YOUTUBE-UPLOAD-GUIDE.md](04_YOUTUBE-UPLOAD-GUIDE.md)
2. Vào https://studio.youtube.com → CREATE → Upload
3. Chọn file MP4 → điền title + description theo template trong guide
4. **Visibility: UNLISTED** ⚠️ (KHÔNG Private, KHÔNG Public)
5. Đợi YouTube process xong → copy link `https://youtu.be/XXXXXXXXX`
6. **Test link**: mở Incognito → paste link → verify phát được

**Checkpoint**: Có link YouTube unlisted, phát được trong Incognito.

---

## Bước 5 — Submit TikTok Portal (10 phút)

**Mục đích**: Gửi audit cho TikTok review.

**Hành động**:
1. Mở [05_TIKTOK-PORTAL-SUBMIT.md](05_TIKTOK-PORTAL-SUBMIT.md)
2. Vào https://developers.tiktok.com → Manage apps → app của bạn
3. Tab **Audit Submission**
4. Điền form:
   - Demo Video URL: link YouTube từ Bước 4
   - Use Case Description (paste template trong guide)
   - Scope Justifications cho 3 scope (paste template)
5. Tick compliance checkboxes
6. **Submit for Review**

**Checkpoint**: Portal hiện "Pending review" + email confirmation từ TT.

---

## Bước 6 — Đợi kết quả (5-14 ngày)

**Email từ**: `noreply@tiktok-developer.com`

**Outcome có thể**:

| Trạng thái | Xử lý |
|---|---|
| ✅ **Approved** | Mở bot → Settings → tick `tiktok_audit_approved=true` → Save → Manual TT tab tự enable PUBLIC_TO_EVERYONE |
| ⚠️ **Needs revisions** | Đọc email list issue → fix code/re-record cảnh cần → resubmit |
| ❌ **Rejected** | Đọc reason → forward email cho dev (mình) → fix triệt để → resubmit |

---

## ⚡ Tổng thời gian (1 lần qua)

| Bước | Thời gian | Cộng dồn |
|---|---|---|
| 1. Review | 5p  | 5p   |
| 2. Voice | 15p | 20p  |
| 3. Edit  | 30p | 50p  |
| 4. YouTube | 10p | 60p (1h) |
| 5. Submit | 10p | 70p  |
| 6. Wait | — | 5-14 ngày |

---

## 🆘 Vướng ở bước nào? Mở `06_TROUBLESHOOTING.md`
