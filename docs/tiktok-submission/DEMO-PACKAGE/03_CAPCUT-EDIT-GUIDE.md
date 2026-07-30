# ✂️ 03 — CAPCUT EDIT GUIDE

> Hướng dẫn từng click trong CapCut Desktop để cắt + chèn voice + export.
> Đối tượng: chưa quen CapCut, lần đầu dùng.

---

## A. Cài CapCut Desktop (nếu chưa)

1. Tải: https://www.capcut.com/tools/desktop-video-editor
2. Cài đặt → mở app → đăng nhập (Google account OK)
3. Bỏ qua tutorial nếu muốn

---

## B. Tạo project

1. CapCut hiện ra → click **New Project**
2. Trên thanh top: chọn **16:9 Landscape**
3. Click vào project name (góc trên trái) → đổi thành `LTTStudio_TikTok_Demo`

---

## C. Import nguyên liệu

1. Bấm **Import** (góc trên trái panel Media)
2. Chọn **2 nhóm file**:
   - Video: `C:\Users\KENLY\Videos\2026-05-18 15-50-04.mp4`
   - 10 file MP3 từ folder `voiceover/` (tạo từ Bước 2)
3. Tất cả sẽ xuất hiện trong panel Media bên trái

---

## D. Đặt video lên timeline

1. Drag-and-drop file **video MP4** vào timeline (track Video 1, dòng đầu tiên)
2. Verify thông số:
   - Click vào clip video → Tab **Video** (phải)
   - Resolution: **1920×1080** ✓
   - FPS: **30** ✓
   - Nếu sai → Export sẽ lỗi

---

## E. MUTE audio gốc video OBS ⚠️ QUAN TRỌNG

1. Click vào clip video trên timeline
2. Tab **Audio** (panel phải)
3. Kéo slider **Volume xuống 0** (hoặc bấm icon loa mute)

Lý do: video OBS có thể có tiếng chuột click hoặc noise — voice ElevenLabs sẽ thay thế.

---

## F. Chèn 10 file MP3 vào timeline

### Cách 1: Manual drag-drop (chính xác hơn)

1. Click trên timeline, chuyển playhead về **00:00**
2. Drag `scene_01_opening.mp3` từ Media → **track Audio 2** (dòng dưới video)
3. Verify position = 00:00 (panel phải Position)
4. Tiếp theo:
   - `scene_02_privacy.mp3` → position **00:15**
   - `scene_03_overview.mp3` → position **00:35**
   - `scene_04_oauth.mp3` → position **00:50**
   - `scene_05_audit.mp3` → position **01:30**
   - `scene_06_form.mp3` → position **01:50**
   - `scene_07_consent.mp3` → position **02:10**
   - `scene_08_upload.mp3` → position **02:40**
   - `scene_09_disconnect.mp3` → position **03:00**
   - `scene_10_closing.mp3` → position **03:10**

### Cách 2: Nhanh hơn — Snap to playhead

1. Press `Ctrl+T` để show ruler timeline lớn
2. Type timestamp vào ô **Time** (panel dưới): `00:15`
3. Press Enter → playhead nhảy tới 00:15
4. Drag file MP3 → snap tự động vào playhead
5. Lặp lại cho 10 file

---

## G. Sync voice với video (5-10 phút)

Lý do cần sync: voice có thể dài/ngắn hơn cảnh thực tế trong video.

### Quy trình check từng cảnh:

1. Click playhead về **00:00** → bấm **Space** để play
2. Theo dõi từng cảnh:
   - Voice nói có khớp action không?
   - Voice có cắt ngang giữa câu khi chuyển cảnh không?
3. Nếu lệch → 3 cách sửa:

**Cách A — Voice dài hơn cảnh** (thường gặp ở Scene 07):
```
1. Click vào clip MP3
2. Tab Speed (panel phải) → tăng từ 1.0 lên 1.05-1.10
3. Test play lại
```

**Cách B — Voice ngắn hơn cảnh** (thường gặp ở Scene 05):
```
1. Cảnh hoặc video → có thể slow xuống 0.95
2. Click clip video → Speed 0.95
3. Hoặc giữ nguyên (im lặng cuối cảnh là OK)
```

**Cách C — Voice bắt đầu trễ/sớm**:
```
1. Drag clip MP3 trái-phải để sync
2. Snap tự động to nearest second
```

---

## H. (Optional) Thêm subtitle Vietnamese

Nếu muốn người Việt xem hiểu được (TT reviewer English chỉ cần voice English):

1. Click **Text** (toolbar trái)
2. **Add Caption** → **Auto Captions**
3. Chọn ngôn ngữ: **English** → tạo English caption tự động
4. (Optional) Translate sang Vietnamese:
   - Click vào caption → **Translate** → Vietnamese
5. Style:
   - Font: **Arial**
   - Size: **24**
   - Color: **White**
   - Stroke: **Black 2px**
   - Position: **Bottom Center**

---

## I. (Optional) Transition giữa các cảnh

Đẹp hơn nhưng không bắt buộc:

1. Click khoảng giữa 2 cảnh trên timeline
2. **Effects** → **Transitions** → **Dissolve** hoặc **Fade**
3. Duration: **0.3s** (đủ nhẹ)

---

## J. Preview trước khi export

1. Playhead về 00:00 → bấm **Space** play full video
2. Check:
   - ☐ Voice rõ ràng, không méo, không cắt giữa câu
   - ☐ Mỗi voice khớp action trong cảnh
   - ☐ Audio gốc OBS đã MUTE
   - ☐ Tổng thời lượng = 3:00-3:20 phút
   - ☐ Cảnh 4 (OAuth) — voice nói "disclosure modal" khi modal đang hiện
   - ☐ Cảnh 7 (Consent) — voice nói "privacy dropdown" khi pan qua dropdown

---

## K. Export final video

1. Click **Export** (góc trên phải)
2. Settings:
   ```
   Resolution:   1920×1080
   Frame rate:   30 fps
   Code rate:    Higher quality (preset)
   Format:       MP4
   Encoder:      H.264
   Audio:        AAC, 192k
   ```
3. **File name**: `LTTStudio_VideoBot_TikTok_Audit_Demo.mp4`
4. **Path**: chọn nơi lưu, ví dụ `D:\demo\`
5. **Export** → đợi ~3-5 phút

**Kích thước dự kiến**: 150-300 MB.

---

## L. Verify file export

1. Mở file `.mp4` vừa export bằng **VLC** hoặc **Windows Media Player**
2. Play full → check:
   - ☐ Voice nghe trong VLC, không bị mất
   - ☐ Resolution 1920×1080 (Right-click → Codec info)
   - ☐ Không có frame đen ở đầu/cuối
   - ☐ Subtitle (nếu có) hiển thị rõ

---

## M. (Optional) Test trên YouTube trước khi submit TT

Nếu muốn yên tâm hơn:
1. Upload tạm vào YouTube với **Privacy: Private** (chỉ mình xem)
2. Xem video trên YouTube → check chất lượng final
3. Nếu OK → đổi sang **Unlisted** trong Bước 4
4. Nếu chưa OK → re-edit trong CapCut

---

## ⚠️ Lỗi CapCut thường gặp

| Triệu chứng | Xử lý |
|---|---|
| Video import bị lag khi preview | Settings → Proxy → Enable Low-Quality Preview |
| Audio không phát | Click waveform, verify volume > 0 |
| Export báo "No space left on device" | Cleanup ổ đĩa, cần ~5GB rảnh |
| Export báo "Codec unsupported" | Đổi sang H.264 (không phải H.265) |
| Export chậm > 10 phút | Bật GPU acceleration trong Settings → Performance |

---

**Tiếp theo**: Mở `04_YOUTUBE-UPLOAD-GUIDE.md` để upload file vừa export.
