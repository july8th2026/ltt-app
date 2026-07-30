# LTTStudios Website — Production Bundle (Bilingual EN/VI)

> Toàn bộ website cho `lttstudios.com` — **song ngữ Anh-Việt full**, mỗi
> ngôn ngữ là 1 folder riêng biệt với URL riêng (SEO-friendly + zero JS bug).
> Static HTML/CSS/JS — không cần backend.
>
> **Phiên bản**: 3.0 · **Ngày build**: 2026-06-02 · **Pages**: 14 EN + 14 VI = 28 content + 5 utility = 33 HTML

## 🌐 Cách hoạt động ngôn ngữ

- **Tiếng Anh (default)**: `https://lttstudios.com/[page].html`
- **Tiếng Việt**: `https://lttstudios.com/vi/[page].html`
- **Switcher** nằm ở góc nav: bấm `EN` hoặc `VI` → nhảy thẳng sang counterpart
  page của ngôn ngữ kia (cùng nội dung, khác ngôn ngữ)
- **Zero JS** cho switching — pure HTML link, không bug khi tắt JavaScript
- **hreflang tags** đầy đủ cho SEO (Google biết 2 phiên bản)
- **Roundtrip verified**: EN → VI → quay lại EN chính xác cùng page (14/14 OK)

---

## 📁 Cấu trúc đầy đủ

```
lttstudios-website/
│
├── 🇺🇸 ENGLISH (default)
│   ├── index.html
│   ├── about.html
│   ├── products.html
│   ├── support.html (FAQ + Schema.org FAQPage)
│   ├── download.html
│   ├── contact.html
│   ├── changelog.html
│   ├── 404.html
│   ├── 500.html
│   ├── auth/fb-callback.html
│   └── legal/
│       ├── privacy.html
│       ├── terms.html
│       ├── data-deletion.html
│       ├── cookies.html
│       ├── security.html
│       ├── dpa.html
│       └── callback.html (TikTok OAuth)
│
├── 🇻🇳 VIETNAMESE
│   └── vi/
│       ├── index.html
│       ├── about.html
│       ├── products.html
│       ├── support.html
│       ├── download.html
│       ├── contact.html
│       ├── changelog.html
│       ├── 404.html
│       ├── 500.html
│       └── legal/
│           ├── privacy.html
│           ├── terms.html
│           ├── data-deletion.html
│           ├── cookies.html
│           ├── security.html
│           └── dpa.html
│
├── 🗺 TECHNICAL SEO
│   ├── robots.txt              ← AI bot blocks + sitemap ref
│   ├── sitemap.xml             ← 26 URLs + xhtml:link hreflang
│   ├── manifest.json           ← PWA manifest
│   └── .well-known/security.txt ← RFC 9116
│
└── 🎨 SHARED ASSETS
    └── assets/
        ├── css/main.css        ← Design system (650+ lines, lang-switch CSS)
        ├── js/main.js          ← Nav toggle, smooth-scroll, copy buttons
        ├── img/
        │   ├── favicon.svg
        │   ├── logo.svg
        │   └── og-default.svg
        └── _partials.html      ← Dev reference (HTML snippets)
```

**Total**: **43 files / 317 KB** = 28 content pages (14 EN + 14 VI) + 4 utility (OAuth/500/etc.) + technical SEO + shared assets.

---

## 🚀 Upload guide — theo loại hosting

### A. Shared hosting (cPanel — Hostinger, AZDIGI, TinoHost, GoDaddy...)

**Phương án 1: File Manager (web UI)**

1. cPanel → **File Manager** → vào `public_html/` (root domain)
2. **Upload** → kéo thả toàn bộ folder `lttstudios-website/` content
   (⚠️ KHÔNG upload folder cha — phải upload INSIDE để `index.html` nằm
   thẳng trong `public_html/`)
3. Tạo subfolders `legal/`, `auth/`, `assets/`, `.well-known/` nếu File
   Manager không tự tạo
4. Verify quyền: tất cả file = 644, tất cả folder = 755
5. Cấu hình custom 404: cPanel → **Error Pages** → 404 → set to
   `/404.html`

**Phương án 2: FTP/SFTP**

```bash
# Local máy bạn
cd "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook\docs\lttstudios-website"

# Upload qua FileZilla / WinSCP:
#   Remote: /public_html/
#   Local: . (folder hiện tại)
#   Transfer: binary mode cho SVG/HTML/CSS/JS
```

**Phương án 3: ZIP + extract trên server**

```bash
# Trên máy local Windows (PowerShell)
cd "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook\docs"
Compress-Archive -Path lttstudios-website\* -DestinationPath lttstudios-website.zip

# Upload ZIP qua cPanel File Manager, sau đó:
# Right-click ZIP → Extract → /public_html/
```

### B. VPS (DigitalOcean / Vultr / AWS / Linode)

```bash
# Trên local Windows (Git Bash hoặc WSL)
tar -czf lttstudios-website.tar.gz -C "C:/Users/Administrator/Desktop/BOT UP FB + TikTok/BOT UP Facebook/docs" lttstudios-website

# Upload
scp lttstudios-website.tar.gz user@vps-ip:/tmp/

# Trên VPS
ssh user@vps-ip
cd /var/www/
sudo tar -xzf /tmp/lttstudios-website.tar.gz
sudo mv lttstudios-website lttstudios
sudo chown -R www-data:www-data lttstudios
sudo find /var/www/lttstudios -type f -exec chmod 644 {} \;
sudo find /var/www/lttstudios -type d -exec chmod 755 {} \;
```

**Nginx config** (`/etc/nginx/sites-available/lttstudios.com`):

```nginx
server {
    listen 80;
    server_name lttstudios.com www.lttstudios.com;
    return 301 https://lttstudios.com$request_uri;
}

server {
    listen 443 ssl http2;
    server_name www.lttstudios.com;
    return 301 https://lttstudios.com$request_uri;
    ssl_certificate     /etc/letsencrypt/live/lttstudios.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lttstudios.com/privkey.pem;
}

server {
    listen 443 ssl http2;
    server_name lttstudios.com;

    root /var/www/lttstudios;
    index index.html;

    ssl_certificate     /etc/letsencrypt/live/lttstudios.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lttstudios.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), camera=(), microphone=()" always;

    # OAuth callback — never cache
    location ~* /(auth|legal)/.*callback\.html$ {
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
        try_files $uri =404;
    }

    # Assets — cache 1 year
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # HTML pages — cache 1 hour
    location / {
        try_files $uri $uri.html $uri/ =404;
        expires 1h;
    }

    # Custom error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /500.html;

    # security.txt content type
    location = /.well-known/security.txt {
        default_type text/plain;
    }

    # MIME types
    types {
        application/manifest+json json;
    }
}
```

Setup SSL với certbot:

```bash
sudo certbot --nginx -d lttstudios.com -d www.lttstudios.com
sudo nginx -t && sudo systemctl reload nginx
```

### C. Cloudflare Pages (recommended — miễn phí, fast, auto SSL)

```bash
# Tạo repo private trên GitHub
cd "C:\Users\Administrator\Desktop\BOT UP FB + TikTok\BOT UP Facebook\docs\lttstudios-website"
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USER/lttstudios-website.git
git push -u origin main
```

Trong Cloudflare Pages:
1. https://dash.cloudflare.com → Pages → **Create a project** → Connect repo
2. Build settings:
   - **Framework preset**: None
   - **Build command**: (empty)
   - **Build output directory**: `/`
3. **Save and Deploy**
4. Custom domain: Pages → Custom domains → Add `lttstudios.com`
   - Cloudflare tự config DNS nếu domain đã ở Cloudflare
5. Auto SSL trong 5 phút

**Bonus**: tự động deploy lại mỗi lần `git push`.

### D. GitHub Pages

```bash
# Tương tự cách C, nhưng repo phải PUBLIC (hoặc trả gói GitHub Pro)
git push -u origin main

# GitHub repo Settings → Pages → Source: main branch / root
# Custom domain: lttstudios.com → save
# Tạo file CNAME trong repo:
echo "lttstudios.com" > CNAME
git add CNAME && git commit -m "Set custom domain" && git push
```

DNS: trỏ `lttstudios.com` qua CNAME đến `YOUR_USER.github.io`.

---

## ✅ Verify deployment (Python script)

```python
import urllib.request

urls = [
    'https://lttstudios.com/',
    'https://lttstudios.com/about.html',
    'https://lttstudios.com/products.html',
    'https://lttstudios.com/support.html',
    'https://lttstudios.com/contact.html',
    'https://lttstudios.com/download.html',
    'https://lttstudios.com/changelog.html',
    'https://lttstudios.com/legal/privacy.html',
    'https://lttstudios.com/legal/terms.html',
    'https://lttstudios.com/legal/data-deletion.html',
    'https://lttstudios.com/legal/cookies.html',
    'https://lttstudios.com/legal/security.html',
    'https://lttstudios.com/legal/dpa.html',
    'https://lttstudios.com/legal/callback.html',
    'https://lttstudios.com/auth/fb-callback.html',
    'https://lttstudios.com/robots.txt',
    'https://lttstudios.com/sitemap.xml',
    'https://lttstudios.com/manifest.json',
    'https://lttstudios.com/.well-known/security.txt',
    'https://lttstudios.com/assets/css/main.css',
    'https://lttstudios.com/assets/js/main.js',
    'https://lttstudios.com/assets/img/favicon.svg',
    'https://lttstudios.com/404.html',
]
fail = 0
for u in urls:
    try:
        r = urllib.request.urlopen(u, timeout=10)
        print(f'  ✅ {r.status} | {u}')
    except Exception as e:
        print(f'  ❌ ERR | {u}  ({e})')
        fail += 1
print(f'\nTotal: {len(urls)-fail}/{len(urls)} OK')
```

Tất cả phải **200 OK**. Nếu 403/404 → check permissions hoặc đường dẫn case-sensitive.

---

## 🖼 Asset notes — chuyển SVG → PNG nếu cần

**Favicon**:
- `favicon.svg` đã có (scalable, support Chrome/Firefox/Safari/Edge mới)
- Browser cũ cần `favicon.ico` fallback — convert qua:
  https://realfavicongenerator.net/ → upload `favicon.svg` → download full bundle
- Hoặc dùng ImageMagick local:
  ```bash
  magick assets/img/favicon.svg -resize 32x32 favicon.ico
  ```

**Open Graph image**:
- Meta/Twitter/Facebook chấp nhận SVG nhưng **một số scraper cũ chỉ đọc PNG/JPEG**
- Convert qua https://cloudconvert.com/svg-to-png hoặc:
  ```bash
  magick assets/img/og-default.svg -resize 1200x630 assets/img/og-default.png
  ```
- Sau đó update meta tag trong các page: đổi `og-default.svg` → `og-default.png`

---

## 🔌 Optional — PHP relay cho TikTok cross-machine OAuth

Nếu host hỗ trợ PHP 7.4+, thêm folder `api/oauth-relay/` với 2 file PHP để bot
poll OAuth code từ máy khác. Xem section "Optional PHP relay" trong file
`docs/fb-app-review-submission-plan.md` cho code mẫu.

Nếu KHÔNG dùng (most users): không sao — bot vẫn OAuth được trên cùng máy.

---

## 📋 Pre-launch checklist

- [ ] Tất cả 22 file upload đúng path
- [ ] HTTPS cert đã issue cho `lttstudios.com` + `www.lttstudios.com`
- [ ] Run verify script Python → tất cả 200 OK
- [ ] Mở `https://lttstudios.com/` trong Chrome → hiển thị landing page đẹp
- [ ] Test mobile responsive (Chrome DevTools → mobile preview)
- [ ] Kiểm `View Source` → `<link rel="stylesheet" href="/assets/css/main.css">` resolve OK
- [ ] Click test footer link → tất cả page khác load đúng
- [ ] Test Open Graph: paste URL homepage vào https://www.opengraph.xyz
- [ ] Test Twitter card: https://cards-dev.twitter.com/validator
- [ ] Test Schema.org: https://search.google.com/test/rich-results
- [ ] Submit sitemap to Google Search Console: https://search.google.com/search-console
- [ ] Configure Meta App Dashboard URLs sang `lttstudios.com`
- [ ] Configure TikTok Developer URLs sang `lttstudios.com`
- [ ] Submit Business Verification cho `lttstudios.com`

---

## 🛠 Maintenance

### Khi cần update content:
1. Sửa HTML file trong folder này (cả EN và VI)
2. Update `lastmod` trong `sitemap.xml`
3. Bump version trong `changelog.html`
4. Re-upload file đó lên hosting
5. Clear CDN cache nếu dùng Cloudflare

### Khi cần thêm page mới:
1. Copy `about.html` làm template
2. Sửa `<title>`, meta tags, content
3. Add link vào nav + footer của tất cả page khác (xem `_partials.html`)
4. Add URL vào `sitemap.xml`
5. Re-upload

---

## 📊 Stats

| Metric | Value |
|---|---|
| Total pages | 13 |
| Total file size | ~85 KB (uncompressed) |
| Total file size (gzipped) | ~22 KB |
| Page load time | < 1s (static, no JS frameworks) |
| Lighthouse Performance | 95+ (expected) |
| Lighthouse Accessibility | 100 (expected) |
| Lighthouse SEO | 100 (expected) |
| Lighthouse Best Practices | 100 (expected) |

---

**Built**: 2026-06-02 · **Maintainer**: LE THANH TRUNG · **License**: All content © LTTStudios
