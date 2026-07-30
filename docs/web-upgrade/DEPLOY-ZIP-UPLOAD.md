# 🚀 DEPLOY — Zip + Upload (10 phút)

> **Approach**: Zip toàn bộ folder `lttstudio-web/` → upload zip lên cPanel → extract overwrite. Một thao tác duy nhất.

---

## 📂 Web local của bạn

```
D:\CODE AI\BOT UP FB + TikTok\lttstudio-web\
├── .well-known/
├── assets/                       (CSS, JS, images, fonts)
├── auth/
├── components/                   (header.html, footer.html)
├── features/
├── legal/
│   ├── callback.html             ⭐ ĐÃ ENHANCE (auto-redirect + error handling)
│   ├── privacy.html              (VN — đầy đủ)
│   ├── privacy-en.html           ⭐ ĐÃ ENHANCE (+ GDPR/CCPA section)
│   ├── terms.html                (VN)
│   └── terms-en.html             (EN)
├── products/
├── support/
├── 404.html
├── about.html
├── index.html
├── robots.txt
├── sitemap.xml
└── preview.bat                   (skip — không upload)
```

## ⭐ Thay đổi trong session này (3 file)

| File | Enhancement |
|---|---|
| `legal/privacy-en.html` | + Section 4c (Data Retention table) + Section 4d (GDPR + CCPA compliance) + Contact mở rộng (privacy@, legal@) |
| `legal/callback.html` | + Handle `?error=access_denied` / `?error=invalid_request` + Handle no-params (direct visit) + Friendly UX cho 3 case |
| Bot `data/config.json` | URL privacy → `/legal/privacy-en.html`, URL terms → `/legal/terms-en.html` |

Web architecture của bạn đã có sẵn:
- Language switcher VN ↔ EN trong components.js ✅
- Header/footer inject qua components ✅
- CSS modular đẹp ✅
- TT submission URL trỏ tới English version → reviewer đọc thẳng ✅

---

## 🚀 Quy trình deploy (3 bước)

### Bước 1: Tạo zip (1 phút)

#### Windows Explorer

```
1. Mở D:\CODE AI\BOT UP FB + TikTok\
2. Right-click folder lttstudio-web → Send to → Compressed (zipped) folder
3. → tạo file lttstudio-web.zip cùng cấp
```

Hoặc command line (PowerShell):

```powershell
cd "D:\CODE AI\BOT UP FB + TikTok"
Compress-Archive -Path lttstudio-web\* -DestinationPath lttstudio-web.zip -Force
```

⚠️ Lưu ý: `lttstudio-web\*` (có dấu `\*`) → zip CONTENTS bên trong folder, không zip cả folder.

### Bước 2: Upload + Extract trên cPanel (5 phút)

```
1. cPanel → File Manager → vào public_html/
2. (Backup) Right-click public_html → Compress → backup_2026-05-18.zip → Download
3. Upload nút trên thanh → chọn lttstudio-web.zip → đợi upload xong
4. Sau khi upload, right-click file zip → Extract
   - Extract to: /public_html  (đường dẫn hiện tại)
   - Bấm Extract Files
5. cPanel hỏi "Overwrite existing files?" → YES (Replace All)
6. Sau extract xong → xóa file lttstudio-web.zip trên server (không cần nữa)
```

### Bước 3: Email forwarders (4 phút) — chỉ làm 1 LẦN

Privacy/Terms reference 3 email. Phải có forwarder để TT reviewer/user gửi mail tới được:

```
cPanel → Email → Forwarders → Add Forwarder

privacy@lttstudio.top  → letammeiu@gmail.com
support@lttstudio.top  → letammeiu@gmail.com
legal@lttstudio.top    → letammeiu@gmail.com
```

Test: Gửi email từ Gmail khác tới `support@lttstudio.top` → 1-2 phút sau check Inbox `letammeiu@`.

---

## ✅ Verify deployment (3 phút)

Mở Chrome Incognito (Ctrl+Shift+N), test:

```
□ https://lttstudio.top
   → Homepage Vietnamese (default)
   → Header có 🇻🇳 VI active + 🇬🇧 EN link

□ Click 🇬🇧 EN ở header → đi tới English version
□ Click 🇻🇳 VI quay về Vietnamese

□ https://lttstudio.top/legal/privacy-en.html
   → English Privacy
   → TOC bên trái có "GDPR & CCPA" (section 4d) ⭐
   → Scroll xuống section 4c thấy bảng Data Retention
   → Scroll xuống section 4d thấy GDPR Article 5/6/15/17/18/20/21 + CCPA

□ https://lttstudio.top/legal/callback.html
   → Hiển thị "Trang chỉ dành cho OAuth callback"
   → Có link "Về trang chủ"

□ https://lttstudio.top/legal/callback.html?error=access_denied
   → Hiển thị "Xác thực thất bại" + "Bạn đã từ chối ủy quyền"

□ https://lttstudio.top/legal/callback.html?code=test&state=test
   → Hiển thị spinner → auto-redirect localhost:8766 sau 600ms
   → (Sẽ thất bại redirect vì bot không chạy — đó là expected)

□ https://lttstudio.top/legal/privacy.html
   → Vietnamese version vẫn hoạt động bình thường
```

---

## 🆘 Troubleshooting

| Lỗi | Fix |
|---|---|
| Extract zip báo "File exists" | Chọn **Overwrite** / **Replace All** trong dialog |
| Một số file không extract | Check permission folder `public_html/`. Phải 755 |
| Privacy-en.html vẫn version cũ | Browser cache → Ctrl+F5 hard reload. Hoặc Cloudflare Purge Everything |
| 500 sau extract | Có thể `.htaccess` cũ conflict với CSS. Check error log cPanel |
| Component header/footer không load | Check `/components/header.html` accessible. Xem console F12 |
| Language switch không hoạt động | Check `/assets/js/components.js` đã load (Network tab F12) |

---

## 🧪 Verify bot config

Bot đã update URL trỏ về `-en.html` cho TT submission. Verify:

```
Bot LTTStudio → Tab 🔧 Cài đặt → mục TikTok:
  app_privacy_policy_url: https://lttstudio.top/legal/privacy-en.html  ✅
  app_terms_url:          https://lttstudio.top/legal/terms-en.html   ✅
  tiktok_redirect_uri:    https://lttstudio.top/legal/callback.html
```

Sau khi web deploy xong, tab **📋 TT Audit** → bấm **Refresh** → checklist chuyển:

```
✅ Sẵn sàng submit TikTok audit (11 checks pass)
✅ Privacy + Terms URLs: HTTP 200 (cả 2 URL English)
✅ Privacy mentions TikTok: đầy đủ keywords (English version + GDPR/CCPA)
```

---

## 📝 Sau khi deploy

Gửi tôi tin nhắn: **"deploy web xong"** → tôi:

1. **WebFetch verify** 4 URL chính (homepage VN, EN, privacy-en, callback)
2. **Test callback flow** với param ?code/?error
3. **Test language switcher** 2 chiều
4. **Run audit checklist** trong bot → confirm 11/11 ✅
5. Báo tỉ lệ pass rate TT audit dự kiến cuối

Nếu OK → submit TT Portal ngay (URL privacy English đã chuẩn).

---

## ⏱️ Tổng: ~13 phút

| Bước | Thời gian |
|---|---|
| 1. Zip folder | 1 phút |
| 2. Backup + Upload + Extract cPanel | 5 phút |
| 3. Email forwarders (1 lần) | 4 phút |
| Verify URLs | 3 phút |

**TỔNG** ~13 phút (sau lần đầu thì sau này chỉ ~5 phút zip+upload).
