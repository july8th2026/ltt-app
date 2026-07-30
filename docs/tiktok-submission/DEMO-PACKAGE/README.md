# 📦 DEMO-PACKAGE — Hoàn thiện Video Demo TikTok Audit

> **Mục tiêu**: Cắt dựng video OBS + lồng voice ElevenLabs + upload + submit TikTok audit.
> **Đối tượng**: Bạn (đã quay xong video bằng OBS, giờ cần lồng voice + submit).
> **Thời gian dự kiến**: ~1 giờ tổng (15p voice + 30p edit + 10p upload + 10p submit).

---

## 🗂️ Cấu trúc folder

```
DEMO-PACKAGE/
├── README.md                          ⭐ ĐỌC FILE NÀY TRƯỚC
├── 00_QUY-TRINH-TONG-THE.md          📋 Workflow tổng thể, theo thứ tự
├── 01_VOICE-SCRIPTS.md               🎤 10 đoạn voice cho ElevenLabs
├── 02_TIMING-REFERENCE.md            ⏱️ Bảng timestamp sync
├── 03_CAPCUT-EDIT-GUIDE.md           ✂️  Hướng dẫn cắt dựng
├── 04_YOUTUBE-UPLOAD-GUIDE.md        📤 Title + Description + Settings
├── 05_TIKTOK-PORTAL-SUBMIT.md        🎯 Form fields + scope justification
├── 06_TROUBLESHOOTING.md             🆘 Xử lý sự cố
└── assets/
    ├── opening_slide.png             Slide opening 1920×1080
    ├── closing_slide.png             Slide closing 1920×1080
    └── lttstudio-icon-1024.png       App icon submit vào portal
```

---

## 🚀 Bắt đầu nhanh (5 bước)

```
1. Đọc 00_QUY-TRINH-TONG-THE.md → nắm thứ tự việc làm
2. Mở 01_VOICE-SCRIPTS.md → paste 10 đoạn vào ElevenLabs → tải MP3
3. Mở 03_CAPCUT-EDIT-GUIDE.md → cắt video + chèn voice → export MP4
4. Mở 04_YOUTUBE-UPLOAD-GUIDE.md → upload Unlisted → copy link
5. Mở 05_TIKTOK-PORTAL-SUBMIT.md → paste link + scope → Submit
```

---

## 📋 File MP4 nguồn (OBS recording)

Đường dẫn: `C:\Users\KENLY\Videos\2026-05-18 15-50-04.mp4` (3m36s, 263MB)

**Nếu file khác**: cập nhật path trong 03_CAPCUT-EDIT-GUIDE.md, các bước còn lại không đổi.

---

## ⚠️ Trước khi bắt đầu — kiểm tra nhanh

```
□ Video OBS đã quay xong, độ dài ~3:00-3:30 phút
□ Tài khoản ElevenLabs đã đăng ký (miễn phí 10.000 ký tự/tháng)
□ CapCut Desktop đã cài (https://www.capcut.com)
□ Tài khoản YouTube/Google sẵn sàng upload
□ Đã đăng nhập developers.tiktok.com
```

Nếu thiếu mục nào → quay lại pre-check trong `00_QUY-TRINH-TONG-THE.md`.

---

## 🆘 Cần hỗ trợ?

Mở file `06_TROUBLESHOOTING.md` cho các vấn đề thường gặp.

Nếu vẫn vướng → gửi screenshot/log cho mình, mình hỗ trợ ngay.

---

**Bắt đầu**: Mở file `00_QUY-TRINH-TONG-THE.md` 👉
