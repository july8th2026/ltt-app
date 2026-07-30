# LTTStudios.com — Deployment Guide

> **Hướng dẫn step-by-step** sau khi Claude đã migrate bot code. Bạn làm theo đúng thứ tự.
>
> **Ngày tạo**: 2026-06-02 · **Migration version**: 1.0

---

## ✅ Checklist tổng quan

```
□ STEP 1 — Backup project trước khi triển khai
□ STEP 2 — Upload website lên hosting (lttstudios.com)
□ STEP 3 — Verify website 6 URL trả 200 OK
□ STEP 4 — Update Meta App Dashboard
□ STEP 5 — Update TikTok Developer Portal
□ STEP 6 — Test bot khởi động OK
□ STEP 7 — Test OAuth flow Facebook
□ STEP 8 — Test OAuth flow TikTok
□ STEP 9 — Submit Business Verification cho lttstudios.com
□ STEP 10 — Sau verify xong → Submit App Review
```

---

## STEP 1 — Backup project

Trước khi làm gì, backup toàn bộ project:

```cmd
cd /d "C:\Users\Administrator\Desktop"
xcopy "BOT UP FB + TikTok" "BOT UP FB + TikTok.backup-2026-06-02" /E /I /H /Y
```

→ Nếu có sự cố, restore bằng cách xoá folder hiện tại + rename folder backup về.

---

## STEP 2 — Upload website

### 2.1 Find folder website đã tạo

Toàn bộ file website cho `lttstudios.com` đã được Claude tạo tại:

```
C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook\docs\lttstudios-website\
```

Cấu trúc:
```
lttstudios-website/
├── README.md                      ← hướng dẫn upload chi tiết
├── index.html
├── auth/
│   └── fb-callback.html
└── legal/
    ├── privacy.html
    ├── terms.html
    ├── data-deletion.html
    └── callback.html
```

### 2.2 Upload theo hosting

Đọc `lttstudios-website/README.md` để có hướng dẫn cụ thể cho:
- A. Shared hosting (cPanel)
- B. VPS
- C. Cloudflare Pages
- D. GitHub Pages

→ **Khuyến nghị nhanh nhất**: dùng **Cloudflare Pages** (free + auto SSL + CDN).

### 2.3 Verify upload thành công

Chạy script này từ máy bạn:

```cmd
cd /d "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook"
python -X utf8 -c "import urllib.request as u; ^
[print(f' {u.urlopen(url, timeout=10).status:3} {url}') for url in [^
'https://lttstudios.com/', ^
'https://lttstudios.com/legal/privacy.html', ^
'https://lttstudios.com/legal/terms.html', ^
'https://lttstudios.com/legal/data-deletion.html', ^
'https://lttstudios.com/legal/callback.html', ^
'https://lttstudios.com/auth/fb-callback.html']]"
```

Tất cả phải trả **200**. Nếu 403/404 → quay lại Step 2.2 fix permission.

---

## STEP 3 — Update Meta App Dashboard

### 3.1 Vào App Settings

URL: https://developers.facebook.com/apps/2021063792619148/settings/basic/

### 3.2 Sửa các trường này (mỗi trường + Save):

| Field | Giá trị mới |
|---|---|
| **App Domains** | Thêm `lttstudios.com` (giữ `lttstudio.top` parallel) |
| **Privacy Policy URL** | `https://lttstudios.com/legal/privacy.html` |
| **Terms of Service URL** | `https://lttstudios.com/legal/terms.html` |
| **User Data Deletion URL** | `https://lttstudios.com/legal/data-deletion.html` |
| **Business Use** | (Giữ nguyên) |
| **Contact Email** | (Giữ nguyên `letammeiu@gmail.com`) |

Click **Lưu thay đổi** sau khi sửa.

### 3.3 Update OAuth Redirect URIs

URL: https://developers.facebook.com/apps/2021063792619148/fb-login/settings/

Tìm **Valid OAuth Redirect URIs**, ADD (không thay thế):
```
https://lttstudios.com/auth/fb-callback.html
```

Giữ cũ song song:
```
https://lttstudio.top/auth/fb-callback.html
```

→ Click **Lưu thay đổi**.

---

## STEP 4 — Update TikTok Developer Portal

### 4.1 Vào TikTok Portal

URL: https://developers.tiktok.com/apps

Login → chọn app của bạn (`awqbvizbrptynef1`).

### 4.2 Sửa các trường:

| Field | Giá trị mới |
|---|---|
| **Privacy Policy URL** | `https://lttstudios.com/legal/privacy.html` |
| **Terms of Service URL** | `https://lttstudios.com/legal/terms.html` |
| **Redirect URI** | Thêm `https://lttstudios.com/legal/callback.html` (giữ `.top` cũ) |

→ Save.

⚠️ TikTok thường yêu cầu re-audit khi đổi domain. Nếu app TikTok đang submitted → chờ phản hồi rồi mới đổi.

---

## STEP 5 — Test bot khởi động

```cmd
cd /d "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook"
run_gui.bat
```

GUI phải mở bình thường. Check:
- [ ] Không có dialog "lỗi cấu hình"
- [ ] Tab Settings hiển thị `https://lttstudios.com/legal/privacy.html` trong field Privacy URL
- [ ] Tab FB Accounts load danh sách Page đã connect (token cũ vẫn valid)
- [ ] About dialog (Ctrl+F1) hiển thị `lttstudios.com`

→ Nếu có lỗi → đọc `logs/app.log` cuối file để xem stack trace.

---

## STEP 6 — Test OAuth flow Facebook

1. Tab **FB Accounts** → click **+ Connect Facebook**
2. Browser mở Facebook OAuth dialog
3. Đăng nhập (test với tài khoản LTTStudio admin)
4. Sau khi approve, browser redirect đến `https://lttstudios.com/auth/fb-callback.html`
5. Trang callback phải hiển thị **"✅ Đã kết nối thành công"**
6. Quay lại bot → list Pages phải hiển thị

→ Nếu fail: check `https://lttstudios.com/auth/fb-callback.html` mở trong browser bình thường (200), và Meta Dashboard đã save Redirect URI `.com`.

---

## STEP 7 — Test OAuth flow TikTok

Tương tự Step 6 nhưng cho TikTok:

1. Tab **TikTok Accounts** → click Connect
2. Browser mở TikTok OAuth
3. Approve
4. Callback `https://lttstudios.com/legal/callback.html`
5. Bot nhận code → token saved

→ Nếu TikTok dùng cross-machine QR flow → cần PHP relay (xem `lttstudios-website/README.md` section "Optional PHP relay")

---

## STEP 8 — Submit Business Verification cho lttstudios.com

### 8.1 Vào Business Manager

URL: https://business.facebook.com/settings/security

### 8.2 Verify domain `lttstudios.com`

1. **Brand Safety → Domains** → **Add Domain** → `lttstudios.com`
2. Chọn method **DNS TXT record** (nhanh nhất)
3. Meta cấp TXT value như: `facebook-domain-verification=abc123xyz...`
4. Vào DNS panel của Cloudflare (nơi bạn quản lý domain):
   - Type: **TXT**
   - Name: `@` (hoặc trống)
   - Content: `facebook-domain-verification=abc123xyz...`
   - TTL: Auto
5. Save → quay lại Meta → click **Verify**
6. Wait 1-72h (thường < 24h)

### 8.3 Verify Business (nếu chưa)

Tab **Business Info** → **Verify**:
- Upload CCCD/CMND của LE THANH TRUNG (chụp rõ 2 mặt, không che số)
- Hoặc GPKD nếu có
- Hoặc hoá đơn điện/internet với địa chỉ Mê Linh Hà Nội

→ Chờ 1-3 ngày.

---

## STEP 9 — Submit App Review

**Sau khi Business + Domain verified**, vào:

URL: https://developers.facebook.com/apps/2021063792619148/use-cases/

Click vào **"Quản lý mọi thứ trên Trang"** → tab **Quyền và tính năng**.

Với mỗi permission còn ở "Sẵn sàng thử nghiệm":

| Permission | Click |
|---|---|
| `pages_show_list` | **Request Advanced Access** |
| `pages_manage_posts` | **Request Advanced Access** |
| `pages_read_engagement` | **Request Advanced Access** |
| `pages_manage_engagement` | **Request Advanced Access** |

Cho mỗi request, paste:
- **Use case description** từ `docs/fb-app-review-assets/use-case-descriptions.txt`
- **Test instructions** từ `docs/fb-app-review-assets/reviewer-test-instructions.txt`
- **Screencast** (4 video MP4 — bạn quay theo guide Section 6 của `fb-app-review-submission-plan.md`)

→ Click **Submit for Review**. Chờ 5-14 ngày.

---

## STEP 10 — Sau Approved → Toggle Live

App Dashboard → header → toggle **App Mode: Development → Live**.

Sidebar trái "Đăng" sẽ đổi từ "Đã hủy đăng" → **"Đã đăng"** ✅

Từ moment này, mọi bài bot đăng sẽ **public với cả thế giới**.

---

## 📊 Summary thay đổi đã làm (Claude execute)

### Files đã sửa (production):

| File | Loại thay đổi |
|---|---|
| `data/config.json` | 8 URL refs → .com |
| `version.py` | APP_URL → .com |
| `LICENSE` | 4 emails + website → .com |
| `gui/settings_tab.py` | 11 refs → .com |
| `gui/about_dialog.py` | 5 refs → .com |
| `gui/tiktok_account_tab.py` | 1 ref → .com |
| `gui/tiktok_oauth_url_dialog.py` | 1 comment → .com |
| `core/tiktok/auth_manager.py` | 2 comments → .com |
| `core/tiktok/audit_checklist.py` | 1 error msg → .com |
| `data/translations/vi.json` | 1 string → .com |
| `data/translations/en.json` | 1 string → .com |
| `tools/simulate_oauth_flow.py` | 15 refs → .com |
| `tools/check_oauth_relay.py` | 2 headers → .com |
| `tools/demo_v2/scene_config.py` | 7 refs → .com |
| `tools/demo_v2/02_generate_slides.py` | 4 refs → .com |
| `scripts/_demo_record.py` | 2 refs → .com |
| `scripts/_demo_record_v3.py` | 2 refs → .com |
| `scripts/demo_assets/_gen_slides.py` | 2 refs → .com |
| `tests/test_28_tiktok_parity.py` | 3 refs → .com |
| `docs/fb-app-review-assets/reviewer-test-instructions.txt` | All refs → .com |
| `docs/fb-app-review-submission-plan.md` | All refs → .com |

### Files KHÔNG đụng (theo design):

- `.backup_v2fix/`, `.backup_multisheet/`, `.backup_helpsystem/` — backup snapshot
- `data/audit_log.jsonl` — lịch sử
- `data/config.backup.*.json` — config backup lịch sử
- `docs/tiktok-submission/*` — historical TikTok submission docs (audit đã submit cũ)

### Files mới tạo:

| File | Mục đích |
|---|---|
| `docs/lttstudios-migration-plan.md` | Plan migration tổng |
| `docs/lttstudios-deployment-guide.md` | File này |
| `docs/lttstudios-website/index.html` | Landing page |
| `docs/lttstudios-website/auth/fb-callback.html` | OAuth FB callback |
| `docs/lttstudios-website/legal/privacy.html` | Privacy Policy |
| `docs/lttstudios-website/legal/terms.html` | Terms of Service |
| `docs/lttstudios-website/legal/data-deletion.html` | Data Deletion |
| `docs/lttstudios-website/legal/callback.html` | OAuth TikTok callback |
| `docs/lttstudios-website/README.md` | Upload guide |

---

## 🆘 Rollback plan

Nếu sau migration bot bị lỗi:

### Rollback config nhanh (5 phút)

```cmd
cd /d "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook"
copy data\config.backup.before_tt_audit_live.json data\config.json
```

→ Restart bot.

### Rollback full code (1 phút)

```cmd
cd /d "C:\Users\Administrator\Desktop"
rmdir /S /Q "BOT UP FB + TikTok"
ren "BOT UP FB + TikTok.backup-2026-06-02" "BOT UP FB + TikTok"
```

### Rollback Meta Dashboard

Vào Meta App Settings → các URL fields → đổi lại về `.top` → Save.

---

## 📞 Hỗ trợ

Nếu gặp issue khi thực thi guide này:
- Check `logs/app.log` cuối file để xem error chi tiết
- Check `data/audit_log.jsonl` cuối file để xem operation gần nhất

---

**Phiên bản**: 1.0 · **Ngày**: 2026-06-02
