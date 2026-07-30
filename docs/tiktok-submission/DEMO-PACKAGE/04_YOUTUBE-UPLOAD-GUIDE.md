# 📤 04 — YOUTUBE UPLOAD GUIDE

> Upload file MP4 final lên YouTube ở chế độ **Unlisted** để lấy link cho TT portal.

---

## ⚠️ Lưu ý CỰC QUAN TRỌNG về Visibility

| Mode | Reviewer xem được? | Index public? | TT chấp nhận? |
|---|---|---|---|
| 🔴 **Private** | ❌ Không (chỉ chủ kênh) | ❌ Không | ❌ REJECT auto |
| 🟢 **Unlisted** | ✅ Có (qua direct link) | ❌ Không | ✅ ĐÚNG |
| ⚠️ **Public** | ✅ Có | ✅ Có (mọi người tìm thấy) | ⚠️ Chấp nhận nhưng KHÔNG cần |

→ **Bắt buộc chọn "Unlisted"** trong Bước 7 dưới đây.

---

## Quy trình upload (10 phút)

### Bước 1: Vào YouTube Studio

1. Mở https://studio.youtube.com
2. Đăng nhập (Google account)
3. Nếu chưa có channel → tạo mới (Create channel)

### Bước 2: Upload video

1. Bấm nút **CREATE** (góc trên phải, icon máy quay 🎥)
2. Chọn **Upload videos**
3. Drag file `LTTStudio_VideoBot_TikTok_Audit_Demo.mp4` vào popup
4. Đợi upload ~2-5 phút tùy mạng

### Bước 3: Điền Details (trang 1/4)

#### Title

```
LTTStudio VideoBot — TikTok Content Posting API Audit Demo
```

#### Description

```
Audit demo for LTTStudio VideoBot, a Windows desktop application
integrating TikTok Content Posting API v2 and Login Kit.

Demonstrates the complete user flow including:
- Mandatory pre-authorization disclosure modal showing each OAuth scope with its reason
- Audit readiness dashboard verifying TikTok compliance requirements in real time
- Per-publish user confirmation with privacy level selection (dropdown, never pre-set)
- Allow comment / duet / stitch interaction toggles
- AI-generated content disclosure checkbox (per TikTok November 2024 policy)
- Branded content disclosure checkbox
- Disconnect / token revocation flow

Documentation:
- Privacy Policy: https://lttstudio.top/legal/privacy.html
- Terms of Service: https://lttstudio.top/legal/terms.html
- Support: support@lttstudio.top

Submitted for TikTok Developer App Audit Review.
May 2026
```

#### Thumbnail (optional)

- YouTube auto-generate 3 thumbnails. Chọn frame **Audit Dashboard** (01:35) nhìn pro nhất.
- Hoặc upload manual: dùng `assets/opening_slide.png` làm thumbnail.

#### Audience

- Chọn: **"No, it's not made for kids"**

#### More options (mở dropdown phía dưới)

| Field | Value |
|---|---|
| **Language** | English |
| **Captions certification** | (để trống) |
| **Recording date** | (optional) Chọn ngày quay |
| **Location** | (để trống) |
| **License** | Standard YouTube License |
| **Distribution** | ✓ Allow embedding (giữ mặc định) |
| **Category** | Science & Technology |
| **Comments** | Allow all comments |
| **Show "thumbs up" + "thumbs down"** | ✓ Yes |

→ Bấm **NEXT**

### Bước 4: Video elements (trang 2/4)

- **End screen**: Skip
- **Cards**: Skip

→ Bấm **NEXT**

### Bước 5: Checks (trang 3/4)

- YouTube auto-scan copyright. Đợi 1-2 phút.
- Kết quả phải là **"No issues found"** ✅
- Nếu có copyright issue (audio bị flag) → click **Dispute** hoặc re-edit ở CapCut bỏ audio đó

→ Bấm **NEXT**

### Bước 6: Visibility (trang 4/4)

🚨 **QUAN TRỌNG NHẤT** 🚨

| Option | Action |
|---|---|
| Save or publish | ⚠️ Click chọn **Unlisted** |
| Schedule | Bỏ qua |

```
○ Private — Only you and people you choose can watch
● Unlisted — Anyone with the video link can watch     ⭐ CHỌN CÁI NÀY
○ Public — Everyone can watch
```

→ Bấm **SAVE**

### Bước 7: Lấy link

1. Sau khi save, popup hiện link dạng:
   ```
   https://youtu.be/AbCdEfGhIjK
   ```
2. Bấm **Copy** → paste vào notepad lưu lại
3. Hoặc vào Videos list → click video vừa upload → URL trên trình duyệt

### Bước 8: TEST LINK ⚠️

**KHÔNG bỏ qua bước này!**

1. Mở **Chrome Incognito** (Ctrl+Shift+N) hoặc đăng xuất YouTube
2. Paste link YouTube đã copy
3. Verify:
   - ✅ Video phát được
   - ✅ Không yêu cầu đăng nhập
   - ✅ Title + Description hiển thị
   - ❌ Không xuất hiện trong YouTube search

Nếu video báo "Private" hoặc "Unavailable" → quay lại YouTube Studio → đổi sang Unlisted.

---

## Checklist hoàn thành Bước 4

```
□ File MP4 đã upload thành công lên YouTube
□ Title chính xác (tiếng Anh, có "TikTok Content Posting API")
□ Description đầy đủ 3 URL (privacy / terms / support)
□ Audience = Not for kids
□ Language = English
□ Visibility = UNLISTED (KHÔNG Private, KHÔNG Public)
□ Đã test link trong Incognito — video phát được
□ Đã copy link YouTube
```

---

## ⚠️ Nếu YouTube reject (hiếm)

| Lý do | Xử lý |
|---|---|
| Copyright (audio) | Re-edit CapCut, bỏ phần bị flag |
| Misleading thumbnail | Đổi thumbnail khác |
| Spam / community guidelines | Đọc kỹ lý do → chỉnh title/description |
| Audio quality quá kém | Re-export với Audio bitrate cao hơn (256k) |

---

**Tiếp theo**: Mở `05_TIKTOK-PORTAL-SUBMIT.md` để paste link YouTube vào portal.
