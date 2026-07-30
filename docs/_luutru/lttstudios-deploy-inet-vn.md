# Deploy LTTStudios.com sang inet.vn WordPress Hosting

> **Mục đích**: Thay thế toàn bộ site live hiện tại bằng bilingual site (43 files / 119 KB)
> đã build trong `docs/lttstudios-website/`.
>
> **Hosting**: inet.vn → `onehost-wphn092505.000nethost.com`
> **Domain**: `lttstudios.com`
> **Phương án**: A — Replace toàn bộ (không 301 redirect)
> **Thời gian**: ~30 phút

---

## ✅ Pre-flight checklist (làm trước khi bắt đầu)

| # | Kiểm tra | OK? |
|---|---|---|
| 1 | Có file `docs/lttstudios-website.zip` (119 KB) trên máy | ☐ |
| 2 | Đăng nhập được vào https://my.inet.vn (customer panel) | ☐ |
| 3 | Đã ngừng bot upload đang chạy (tránh OAuth race condition) | ☐ |
| 4 | Có backup credentials (đề phòng reset password do hosting) | ☐ |
| 5 | Có thời gian liên tục 30-45 phút (đừng dừng giữa chừng) | ☐ |

---

## 📦 Bước 1 — Backup site hiện tại (10 phút)

**Lý do**: Site live hiện tại có 5+ trang dùng được (EN homepage, EN privacy, EN terms,
VI features/Facebook, VI products/videobot). Backup để có thể rollback nếu cần.

### 1.1 Login customer panel inet.vn

1. Mở https://my.inet.vn
2. Login với credentials đã đăng ký
3. Sidebar trái → **"Quản lý dịch vụ"** → **"Hosting"**
4. Click vào hosting `onehost-wphn092505.000nethost.com` → **"Quản trị"**

### 1.2 Mở cPanel hoặc DirectAdmin

inet.vn thường dùng **DirectAdmin** cho gói hosting (không phải cPanel). Look for:
- Nút **"Đăng nhập DirectAdmin"** hoặc **"DirectAdmin Login"**
- Hoặc URL pattern: `https://onehost-wphn092505.000nethost.com:2222`

### 1.3 Backup current public_html

Trong DirectAdmin:

1. Click **"File Manager"** (icon thư mục)
2. Navigate vào folder **`public_html/`**
3. Select All (Ctrl+A trong file list)
4. Click nút **"Add to Archive"** hoặc **"Compress"**
5. Filename: `backup-before-lttstudios-deploy-2026-06-04.zip`
6. Format: ZIP
7. Click OK → đợi 30 giây tạo archive

**Hoặc qua FTP** (nếu thích):
```
Host: onehost-wphn092505.000nethost.com
Port: 21 (FTP) hoặc 22 (SFTP)
User: <FTP username từ DirectAdmin>
Pass: <FTP password>

Tải toàn bộ /public_html/ về máy → ZIP local.
```

### 1.4 Download backup về máy

1. Trong File Manager, click chuột phải vào `backup-before-...zip` → **Download**
2. Lưu vào `C:\Users\Administrator\Desktop\` để khi cần có ngay

✅ **Bây giờ bạn có thể rollback bất kỳ lúc nào.**

---

## 🚀 Bước 2 — Clear current files (5 phút)

### 2.1 Xác nhận content sắp xoá

Vào File Manager, thư mục `public_html/`. Liệt kê những gì hiện có:

```
public_html/
├── index.html               ← homepage cũ
├── features/
│   ├── facebook.html
│   ├── tiktok.html
│   └── excel.html
├── products/
│   └── videobot/
│       ├── index.html
│       ├── download.html
│       └── changelog.html
├── legal/
│   ├── privacy.html
│   ├── terms.html
│   ├── privacy-vi.html
│   └── terms-vi.html
├── support/
│   ├── faq.html
│   └── report.html
├── about.html
├── sitemap.xml
├── robots.txt
├── .htaccess              ← KHÔNG XOÁ (config Apache)
└── ... (có thể có file khác)
```

### 2.2 Xoá tất cả TRỪ `.htaccess`

⚠️ **GIỮ LẠI `.htaccess`** vì nó là Apache config quan trọng.

Trong File Manager:
1. Select toàn bộ files + folders
2. **BỎ select** `.htaccess` (Ctrl+click để uncheck)
3. Click **"Delete"** → confirm

Hoặc qua SSH (nếu hosting cho):
```bash
cd public_html
find . -mindepth 1 ! -name '.htaccess' -delete
```

---

## 📤 Bước 3 — Upload site mới (10 phút)

### 3.1 Upload ZIP

1. Vào File Manager → `public_html/`
2. Click **"Upload"** (icon mũi tên lên)
3. Drag file `C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook\docs\lttstudios-website.zip` vào
4. Đợi 100% upload (119 KB → vài giây)

### 3.2 Extract ZIP

1. Quay lại File Manager
2. Click chuột phải vào `lttstudios-website.zip` → **"Extract"**
3. Extract to: `/public_html/` (đường dẫn hiện tại)
4. Đợi extract xong (3-5 giây cho 119 KB)
5. Verify cấu trúc:
   ```
   public_html/
   ├── index.html          ← homepage mới (EN)
   ├── about.html
   ├── products.html
   ├── support.html
   ├── contact.html
   ├── download.html
   ├── changelog.html
   ├── 404.html
   ├── 500.html
   ├── robots.txt
   ├── sitemap.xml
   ├── manifest.json
   ├── .htaccess           ← GIỮ NGUYÊN từ trước
   ├── .well-known/
   │   └── security.txt
   ├── assets/
   │   ├── css/main.css
   │   ├── js/main.js
   │   └── img/
   ├── auth/
   │   └── fb-callback.html
   ├── legal/
   │   ├── privacy.html
   │   ├── terms.html
   │   ├── data-deletion.html  ← REQUIRED CHO META REVIEW
   │   ├── cookies.html
   │   ├── security.html
   │   ├── dpa.html
   │   └── callback.html
   └── vi/                  ← VIETNAMESE FOLDER
       ├── index.html
       ├── about.html
       ├── ... (tương tự EN)
       └── legal/
           └── ... (đầy đủ)
   ```

### 3.3 Xoá ZIP

Sau khi extract, xoá `lttstudios-website.zip` (để tránh user download được ZIP source).

### 3.4 Permissions check

DirectAdmin → File Manager → select all → **"Change Permissions"**:
- Folders: **755**
- Files: **644**
- `.htaccess`: **644**

Hoặc dùng SSH:
```bash
cd public_html
find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
```

---

## ✅ Bước 4 — Verify deployment (10 phút)

### 4.1 Quick smoke test (mở browser thường)

Mở **trình duyệt ẩn danh** (Chrome Ctrl+Shift+N) để tránh cache:

| URL | Expected | OK? |
|---|---|---|
| https://lttstudios.com/ | Landing EN với logo "LTT Studios" + 6 feature card | ☐ |
| https://lttstudios.com/products.html | Products EN với feature breakdown | ☐ |
| https://lttstudios.com/support.html | FAQ EN với 15+ Q&A collapsible | ☐ |
| https://lttstudios.com/legal/privacy.html | Privacy EN với TOC | ☐ |
| https://lttstudios.com/legal/data-deletion.html | Data deletion guide EN | ☐ |
| https://lttstudios.com/vi/ | Landing VI với "Đăng video hàng loạt" | ☐ |
| https://lttstudios.com/vi/products.html | Products VI | ☐ |
| https://lttstudios.com/vi/legal/privacy.html | Privacy VI "Chính sách Quyền riêng tư" | ☐ |
| https://lttstudios.com/404.html | Error 404 page | ☐ |
| https://lttstudios.com/sitemap.xml | XML với 26 URLs lttstudios.com | ☐ |
| https://lttstudios.com/robots.txt | Plain text với AI bot blocks | ☐ |

### 4.2 Test language switcher

1. Mở https://lttstudios.com/ (EN)
2. Click nút **VI** ở góc nav phải
3. Phải tới https://lttstudios.com/vi/ (VI homepage)
4. Click nút **EN** ở góc nav phải
5. Phải về lại https://lttstudios.com/ (EN homepage)
6. Lặp tương tự cho /about.html ↔ /vi/about.html

### 4.3 Test responsive

Mở Chrome DevTools (F12) → toggle device toolbar (Ctrl+Shift+M):
- 📱 iPhone 12 Pro → hamburger menu xuất hiện, không broken layout
- 📱 iPad → menu vẫn show full
- 💻 Desktop → menu desktop hiển thị

### 4.4 Run Python verify script

Trên máy local, chạy:

```bash
cd "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook\docs"
python -X utf8 verify-deploy.py
```

(Script này tôi tạo sẵn ở bước cuối)

---

## 🚨 Rollback (nếu deploy fail)

Nếu site mới có bug nghiêm trọng và cần khôi phục site cũ:

1. Vào File Manager → `public_html/`
2. Xoá tất cả (trừ `.htaccess`)
3. Upload `backup-before-lttstudios-deploy-2026-06-04.zip` từ Desktop
4. Extract
5. Site cũ sống lại sau ~5 phút

---

## 🔄 Sau khi deploy thành công

### Cập nhật Meta App Dashboard

1. Login https://developers.facebook.com/apps/2021063792619148/settings/basic/
2. Verify các URL sau ĐÚNG (đã là `.com`):
   - **Privacy Policy URL**: `https://lttstudios.com/legal/privacy.html`
   - **Terms of Service URL**: `https://lttstudios.com/legal/terms.html`
   - **Data Deletion URL**: `https://lttstudios.com/legal/data-deletion.html` ⬅ MỚI
3. Click **Save Changes**

### Submit sitemap

1. https://search.google.com/search-console
2. Add property `https://lttstudios.com` (nếu chưa có)
3. Sidebar → **Sitemaps**
4. Submit: `https://lttstudios.com/sitemap.xml`
5. Đợi Google crawl trong 1-7 ngày

### Restart bot

Sau khi confirm OAuth callback `https://lttstudios.com/auth/fb-callback.html`
hoạt động, có thể restart bot và resume publish.

---

## 📋 Final checklist

| Step | Done? |
|---|---|
| ✅ Pre-flight checklist 1-5 | ☐ |
| 1. Backup site hiện tại (ZIP downloaded to Desktop) | ☐ |
| 2. Xoá public_html (giữ .htaccess) | ☐ |
| 3. Upload + extract `lttstudios-website.zip` | ☐ |
| 4. Verify 11 URL trả 200 + content đúng | ☐ |
| 4. Test lang switcher EN ↔ VI roundtrip | ☐ |
| 4. Test mobile responsive | ☐ |
| 5. Update Meta App Dashboard URLs | ☐ |
| 5. Submit sitemap to Google Search Console | ☐ |
| 5. Restart bot, resume normal operation | ☐ |

---

## 📞 Hỗ trợ

Nếu kẹt ở bước nào:
1. Screenshot màn hình + chia sẻ với Claude
2. Hoặc gọi inet.vn support hotline (1900 1232) — họ hỗ trợ DirectAdmin
3. Reference doc: README trong `docs/lttstudios-website/README.md`

**Build**: 2026-06-04 · LTTStudios Migration Plan v1.0
