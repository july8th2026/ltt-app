# 📋 HANDOFF — Toàn bộ dự án LTTStudio VideoBot

> File này tổng hợp toàn bộ trạng thái dự án để chuyển sang chat session mới.
> Đọc kỹ từ đầu đến cuối để hiểu mọi thứ trước khi tiếp tục công việc.

**Last updated:** 2026-05-15
**User:** Lê Tâm Mèo (letammeiu@gmail.com)
**Project owner:** LTTStudio

---

## 🎯 0. TÓM TẮT NHANH

**Dự án:** Phần mềm desktop (Python + CustomTkinter GUI) tự động đăng video lên Facebook Pages và TikTok từ Google Sheet / Excel.

**Đối thủ tham chiếu:** Metricool, Make.com — bot này MIỄN PHÍ + LOCAL-FIRST.

**Brand:** LTTStudio · Domain: `lttstudio.top` (đã deploy lên Hostinger inet.vn)

**Trạng thái tổng thể:**
- ✅ Bot code: 554/554 tests PASS, production-ready
- ✅ GUI: 100/100 sau 6 vòng audit, 6/6 tabs PASS
- ✅ Website: 17/17 trang PASS, đã live tại lttstudio.top
- ✅ Meta App đã tạo: `App ID: 2021063792619148`
- ⏳ Còn: Upload fb-callback.html, config FB Portal, test OAuth, đăng ký TikTok Portal, quay demo video

---

## 📁 1. CẤU TRÚC PROJECT

```
D:\CODE AI\BOT UP FB + TikTok\
│
├── BOT UP Facebook\                       ← ROOT của BOT (chạy từ đây)
│   ├── main.py                            Entry point (GUI bootstrap)
│   ├── version.py                         LTTStudio VideoBot v1.0
│   ├── requirements.txt
│   ├── run_gui.bat                        Click double để chạy GUI
│   ├── run_debug.bat                      Run + show console
│   ├── build_exe.bat                      Build .exe via PyInstaller
│   │
│   ├── gui/                               10 GUI files (CustomTkinter)
│   ├── core/                              Bot logic
│   │   ├── facebook/                      FB integration (separate module)
│   │   ├── tiktok/                        TikTok integration (separate module)
│   │   └── ...                            sheet_runner, upload_engine, etc.
│   ├── utils/                             logger, atomic_io, audit_logger
│   ├── tests/                             554 tests + GUI smoke validator
│   ├── data/                              Runtime (tokens.enc, config.json, audit log)
│   ├── docs/                              ← THIS FILE LIVES HERE
│   │   ├── docs/_luutru/HANDOFF.md                     (this file)
│   │   ├── docs/_luutru/PROJECT_STATE.json             (machine-readable state)
│   │   ├── tiktok-workflow.md             Stage-by-stage doc
│   │   ├── facebook-workflow.md           Stage-by-stage doc
│   │   └── tiktok-submission/             (5 docs cho audit submit)
│   └── logs/
│
└── lttstudio-web\                         ← WEBSITE (deployed to lttstudio.top)
    ├── index.html                         Trang chủ (FB + TT showcase)
    ├── 404.html
    ├── about.html
    ├── preview.bat                        Local HTTP server (port 8080)
    │
    ├── components/header.html             Shared nav (auto-injected via JS)
    ├── components/footer.html
    │
    ├── features/                          ⭐ Dedicated platform pages
    │   ├── facebook.html                  FB integration detail
    │   ├── tiktok.html                    TikTok integration detail
    │   └── excel.html                     Excel workflow detail
    │
    ├── products/videobot/                 Product landing
    ├── legal/                             Privacy / Terms (VI + EN) + TikTok callback
    ├── auth/fb-callback.html              ⭐ Facebook OAuth bridge (HTTPS → localhost)
    ├── support/                           FAQ + Report violation
    ├── assets/css|js|images/              5 CSS files, 1 JS, logo + favicon
    ├── _test/                             Web validator (Selenium + HTTP server)
    └── sitemap.xml + robots.txt + .well-known/security.txt
```

---

## ✅ 2. NHỮNG GÌ ĐÃ TRIỂN KHAI

### 2.1 BOT CODE

**Phases 1-9 (original implementation — đã xong):**
- Phase 1-6: Core TikTok integration (OAuth PKCE, draft + direct upload, compliance, status poll)
- Phase 7: Audit logging (`utils/audit_logger.py`) — JSONL thread-safe
- Phase 8: UI polish (audit banner, manual post card)
- Phase 9: Final test 524/524 + security patches (token leakage fixes)

**Audit fixes (34 issues → all resolved):**
- BUG-01: Sheet runner account key mismatch ✅
- BUG-02: Token store race condition ✅
- BUG-03: Graph session pool thread-unsafe ✅
- BUG-04: Timezone token expiry ✅
- BUG-05: TikTokTokenStore(config) bug ✅
- BUG-06: Hardcoded v21.0 OAuth URL ✅
- BUG-07: TokenStore singleton ✅
- INC-03: Dead code task_queue.py removed ✅
- INC-04: Token decrypt silent fail → warn ✅
- OPT-04: Extract `_upload_chunks` to upload_utils.py ✅
- C1-H8, M1-M9, L2-L5: 27 P0/P1/P2/P3 fixes (TikTok submission readiness)

**GUI audit (6 loops → 100/100 PASS):**
- Loop 1: Phase 1-4 (22 fixes — silent excepts, snapshot, etc.)
- Loop 2: 10 regression must-fix (NameError, key mismatch, OAuth cancel)
- Loop 3: 4 deduction fixes (FB OAuth parity, column rows, version source)
- Loop 4: 35 silent excepts swept
- Loop 5 (fresh): 12 new findings (F5 race, atomic write, single-flight Monitor)
- Loop 6 (final): 6 deduction fixes (audit rotation, FB errors, tooltips)
- **Final: 100/100 PASS**

**TikTok Stage 7 (Commenter — NEW):**
- `core/tiktok/commenter.py` (new module, 188 lines)
- `CommentResult` dataclass, `TikTokCommenter` class
- Validation, stop-event, friendly errors, 3 audit events
- Wired into `publisher_service.py` Stage 7
- 23 test cases in `test_15_tiktok_commenter.py`
- Guarantee: comment failure NEVER breaks publish

**Facebook Stage 7 (Commenter — NEW):**
- `core/facebook/commenter.py` (new module, 180 lines)
- Same CommentResult shape, FB Graph API endpoint `/{video_id}/comments`
- Wired into `FacebookPublisher.publish()`
- 25 test cases in `test_16_facebook_commenter.py`
- Same guarantee: failure preserved publish

**Configurable Redirect URI:**
- TikTok: `tiktok_redirect_uri` config key
- Facebook: `meta_redirect_uri` config key (NEW)
- Both fall back to `http://localhost:{port}/callback` if empty

### 2.2 WEBSITE

**Total: 17 pages, 100% PASS**

| URL | Status |
|-----|--------|
| `/index.html` | ✅ FB + TikTok showcase + product cards |
| `/about.html` | ✅ Mission + use cases + tech stack |
| `/404.html` | ✅ Custom error page with full header |
| `/features/facebook.html` | ⭐ NEW — FB integration deep-dive |
| `/features/tiktok.html` | ⭐ NEW — TikTok integration deep-dive |
| `/features/excel.html` | ⭐ NEW — Excel/Sheets workflow |
| `/products/videobot/*` | ✅ Product landing + download + changelog |
| `/legal/privacy.html` + `-en.html` | ✅ TikTok-compliant Privacy Policy |
| `/legal/terms.html` + `-en.html` | ✅ Terms of Service |
| `/legal/callback.html` | ✅ TikTok OAuth bridge HTML |
| `/auth/fb-callback.html` | ⭐ NEW — Facebook OAuth bridge HTML |
| `/support/faq.html` | ✅ 14 Q&A |
| `/support/report.html` | ✅ Abuse/security report |
| `/.well-known/security.txt` | ✅ Security disclosure policy |

**Menu structure (sau redesign):**
```
Trang chủ │ Sản phẩm ▾ │ Tính năng ▾ │ Tải xuống │ Hỗ trợ ▾ │ Pháp lý ▾
                              │
                              ├─ 📘 Facebook
                              ├─ 🎵 TikTok
                              └─ 📊 Excel
```

**Architecture:**
- Component injection via JS (`components.js` fetch header.html + footer.html)
- Root-relative paths (require HTTP server, NOT file://)
- 5 modular CSS files (variables, base, components, layout, docs)
- Auto-validator: `_test/web_validator.py` (Selenium + HTTP server, 17/17 PASS)

### 2.3 META APP (Facebook Developer Portal)

**Đã làm xong:**
- ✅ Tạo App tên "Lttstudio" tại developers.facebook.com
- ✅ **App ID: `2021063792619148`**
- ✅ **App Secret: `[REDACTED — rotate and store externally]`** ⚠ Giá trị cũ đã lộ — cần xác minh đã reset!
- ✅ Thêm use case "Quản lý mọi thứ trên Trang" (Manage everything on a Page)
- ✅ Tick permissions: `pages_show_list`, `pages_manage_posts`, `pages_manage_engagement`, `pages_read_engagement`, `pages_read_user_content`, `email`, `read_insights`
- ✅ Privacy URL + Terms URL configured

**Vấn đề chính:**
- ❌ Facebook 2024+ TỪ CHỐI `http://localhost:8765/callback`
- ✅ Đã code support `meta_redirect_uri` config
- ✅ Đã tạo `lttstudio-web/auth/fb-callback.html` (HTTPS bridge)
- ⏳ User CHƯA upload bridge page lên Hostinger
- ⏳ User CHƯA config URI mới vào Facebook Portal
- ⏳ User CHƯA test OAuth flow end-to-end

### 2.4 HOSTING (inet.vn)

- ✅ Domain `lttstudio.top` đã đăng ký
- ✅ Hosting WordPress WP-H1 (39k/tháng) đã active
- ✅ Website đã upload `public_html/`
- ✅ HTTPS đã bật
- ⏳ Email MX cho `support@lttstudio.top` chưa setup
- ⏳ Cần upload `auth/fb-callback.html` lên `public_html/auth/`

### 2.5 TESTS

```
Test suite:        554/554 PASS  ✅
GUI smoke test:    6/6 tabs PASS ✅
Web validator:    17/17 pages PASS ✅
GUI audit score:   100/100 ✅
```

### 2.6 DOCUMENTATION

```
docs/_luutru/HANDOFF.md                        ← This file
docs/_luutru/PROJECT_STATE.json                ← Machine-readable state
docs/tiktok-workflow.md                ← 8-stage TikTok workflow
docs/facebook-workflow.md              ← 8-stage Facebook workflow
docs/tiktok-submission/
   ├── app-description.md              ← English app description (200+ words)
   ├── demo-video-script.md            ← 2:30 video script
   ├── scope-justification.md          ← Why each scope
   ├── checklist.md                    ← Submission checklist
   ├── app-icon-guide.md               ← Icon design guide
   ├── excel-template-guide.md         ← For reviewers
   └── lttstudio-icon-1024.png         ← App icon (already done)
LICENSE                                ← Custom license (free + trademark)
version.py                             ← Single source of truth for v1.0
```

---

## ⏳ 3. NHỮNG GÌ CHƯA TRIỂN KHAI

### 3.1 IMMEDIATE NEXT (để bot Facebook hoạt động)

**🔴 Bước 1: Upload Facebook callback bridge**
```
File local: D:\CODE AI\BOT UP FB + TikTok\lttstudio-web\auth\fb-callback.html
Upload tới: public_html/auth/fb-callback.html (inet.vn File Manager)
Verify:     https://lttstudio.top/auth/fb-callback.html  → phải thấy spinner
```

**🔴 Bước 2: Cấu hình URI mới trong Facebook Developer Portal**
```
1. developers.facebook.com → My Apps → Lttstudio (ID 2021063792619148)
2. Sidebar: Trường hợp sử dụng → Quản lý mọi thứ trên Trang → Cài đặt
3. XÓA URI cũ: http://localhost:8765/callback
4. ADD URI mới: https://lttstudio.top/auth/fb-callback.html
5. Lưu thay đổi (sẽ KHÔNG bị lỗi nữa vì là HTTPS)
```

**🔴 Bước 3: ⚠ Reset App Secret (đã lộ trong chat history)**
```
1. Cài đặt → Cơ bản → bên cạnh App Secret bấm "Đặt lại"
2. Copy Secret MỚI
3. Update vào bot Settings
```

**🔴 Bước 4: Cập nhật bot Settings**
```
Mở run_gui.bat → Tab ⚙ Cài đặt → mục META APP:
   App ID:               2021063792619148
   App Secret:           [NEW SECRET sau khi reset]
   OAuth Redirect Port:  8765
   Graph API Version:    v21.0
   Redirect URI (HTTPS): https://lttstudio.top/auth/fb-callback.html

Bấm "💾 Lưu cài đặt"
```

**🔴 Bước 5: Test FB OAuth flow**
```
Tab 🔐 Tài khoản FB → "➕ Kết nối tài khoản Facebook"
→ Chrome mở → Login → Cấp quyền → tick Pages
→ Browser redirect đến lttstudio.top/auth/fb-callback.html
→ JS redirect về http://localhost:8765/callback
→ Bot xổ pages → tick → DONE
```

### 3.2 TIKTOK SETUP (sau khi FB xong)

**🟠 Bước 6: Đăng ký TikTok Developer Portal**
```
1. developers.tiktok.com → My Apps → Create App
2. App Name: LTTStudio VideoBot
3. Add Product: Login Kit + Content Posting API
4. Redirect URI: https://lttstudio.top/legal/callback.html (đã có sẵn HTML)
5. Privacy URL: https://lttstudio.top/legal/privacy.html
6. Terms URL: https://lttstudio.top/legal/terms.html
7. Copy Client Key + Client Secret
```

**🟠 Bước 7: Configure TikTok trong bot**
```
Tab ⚙ Cài đặt → mục TIKTOK:
   Client Key:    [paste]
   Client Secret: [paste]
   Scopes:        user.info.basic,video.upload,video.publish (đã có sẵn)
   Redirect URI:  https://lttstudio.top/legal/callback.html (đã set)

Bấm Lưu → Tab Tài khoản TikTok → Kết nối
```

### 3.3 PRODUCTION READINESS (sau khi cả 2 platforms hoạt động)

**🟡 Bước 8: Quay demo video** (cho TikTok audit)
```
Theo kịch bản: docs/tiktok-submission/demo-video-script.md
Thời lượng: 2-3 phút
Show: OAuth flow → Excel input → Bot upload → TikTok hiển thị video
Upload lên YouTube unlisted → lấy URL
```

**🟡 Bước 9: Email MX setup**
```
Trong inet.vn cPanel → Email Accounts → tạo:
   support@lttstudio.top
   security@lttstudio.top
   privacy@lttstudio.top
   report@lttstudio.top
```

**🟡 Bước 10: Submit TikTok Audit**
```
Trong TikTok Developer Portal:
1. Provide demo video URL
2. Fill scope justifications (đã có sẵn: docs/tiktok-submission/scope-justification.md)
3. Upload app icon (đã có: docs/tiktok-submission/lttstudio-icon-1024.png)
4. Submit for review (chờ 7-14 ngày)
```

**🟡 Bước 11: (Tùy chọn) Submit Facebook App Review**
```
Chỉ cần khi muốn phân phối bot cho người khác (Live mode).
Nếu chỉ dùng cá nhân/team → giữ Development mode mãi mãi cũng OK.
```

---

## 🔑 4. KEY CREDENTIALS & URLS

### 4.1 Meta App (Facebook)
```
App ID:               2021063792619148
App Secret:           [REDACTED — store externally]   ⚠ XÁC MINH ĐÃ RESET
App Name:             Lttstudio
Owner email:          letammeiu@gmail.com
OAuth Redirect Port:  8765
Redirect URI:         https://lttstudio.top/auth/fb-callback.html
Permissions added:    pages_show_list, pages_manage_posts, pages_manage_engagement,
                      pages_read_engagement, pages_read_user_content, email, read_insights
Mode:                 Development (cá nhân/team only)
```

### 4.2 TikTok App
```
Status:               CHƯA tạo
Redirect URI (sẵn):   https://lttstudio.top/legal/callback.html
Scopes (sẵn):         user.info.basic,video.upload,video.publish
Audit approved:       false (chưa submit)
```

### 4.3 Hosting
```
Provider:             inet.vn
Plan:                 WordPress WP-H1 (39,000đ/tháng)
Domain:               lttstudio.top
SSL:                  Active (Let's Encrypt auto)
Public root:          public_html/
```

### 4.4 GitHub / Source
```
Currently:            Local only — D:\CODE AI\BOT UP FB + TikTok\
Future:               Có thể setup repo private/public sau
```

---

## 🐛 5. KNOWN ISSUES & GOTCHAS

### 5.1 Website chỉ chạy được với HTTP server, KHÔNG dùng file://
```
Lý do:    Root-relative paths (/assets/...) + fetch() cần HTTP origin
Fix:      Mở qua preview.bat HOẶC VS Code Live Server HOẶC live URL
Live URL: https://lttstudio.top/ (đúng cách 99% time)
```

### 5.2 Facebook 2024+ chặn http://localhost callback
```
Vì vậy phải dùng HTTPS bridge: https://lttstudio.top/auth/fb-callback.html
Bridge HTML đã có local, nhưng CHƯA upload lên hosting (bước 1 ở trên)
```

### 5.3 App Secret đã lộ trong chat
```
Secret cũ: [REDACTED] (đã từng xuất hiện trong ảnh/chat)
Action:    Bấm "Đặt lại" trong Meta App Settings → Cơ bản
```

### 5.4 Console encoding khi chạy validator
```
Lỗi: UnicodeEncodeError với emoji tab names trên Windows cp1252
Fix: Đã có sẵn — gui_smoke_validator.py force UTF-8 stdout
```

### 5.5 file .bat phải dùng ASCII pure (không Vietnamese diacritics)
```
Lý do: CMD parse trước chcp 65001 → diacritics break parser
Fix:   Tất cả .bat đã dùng English/ASCII only
```

---

## 🛠 6. CÁCH CHẠY/TEST

### 6.1 Chạy GUI bot
```bash
cd "D:\CODE AI\BOT UP FB + TikTok\BOT UP Facebook"
.\run_gui.bat
```

### 6.2 Chạy tests
```bash
cd "D:\CODE AI\BOT UP FB + TikTok\BOT UP Facebook"
python -m pytest tests/ --tb=short -q
# Expected: 554 passed
```

### 6.3 Test GUI tabs (auto-screenshot)
```bash
cd "D:\CODE AI\BOT UP FB + TikTok\BOT UP Facebook"
set PYTHONIOENCODING=utf-8
python tests/gui_smoke_validator.py
# Output: tests/screenshots/tab_*.png + PASS report
```

### 6.4 Preview website local
```bash
cd "D:\CODE AI\BOT UP FB + TikTok\lttstudio-web"
.\preview.bat
# Opens http://localhost:8080/index.html in Chrome
```

### 6.5 Test web (Selenium + screenshot)
```bash
cd "D:\CODE AI\BOT UP FB + TikTok\lttstudio-web"
set PYTHONIOENCODING=utf-8
python _test/web_validator.py
# Expected: 17/17 PASS
# Output: _test/screenshots/*.png
```

---

## 📚 7. TECHNICAL STACK SUMMARY

```
Backend:        Python 3.13 (works 3.10+)
GUI:            CustomTkinter 5.2+
HTTP client:    requests 2.31+
Crypto:         cryptography 42 (Fernet AES-128 token storage)
Google API:     google-api-python-client (Sheets)
Tests:          pytest 9
Web tools:      Selenium + webdriver_manager (for validator)
Web stack:      Pure HTML/CSS/JS (no framework)
Deploy:         PyInstaller for .exe · inet.vn shared hosting for website
```

---

## 🎯 8. WHAT TO DO IN NEXT CHAT

**Tell the new chat:**
> "Đọc file `D:\CODE AI\BOT UP FB + TikTok\BOT UP Facebook\docs\docs/_luutru/HANDOFF.md` để hiểu toàn bộ dự án LTTStudio VideoBot. Cũng có `docs/_luutru/PROJECT_STATE.json` cùng folder cho dữ liệu cấu trúc."

**Recommended next task order:**
1. **Bước 1**: Upload `lttstudio-web/auth/fb-callback.html` lên Hostinger inet.vn (`public_html/auth/`)
2. **Bước 2**: Update Facebook Developer Portal redirect URI → `https://lttstudio.top/auth/fb-callback.html`
3. **Bước 3**: Reset App Secret (đã lộ)
4. **Bước 4**: Update bot Settings với credentials mới
5. **Bước 5**: Test FB OAuth flow → kết nối được Pages → đăng test video
6. **Bước 6**: Đăng ký TikTok Developer Portal, lấy Client Key/Secret
7. **Bước 7**: Test TikTok OAuth flow
8. **Bước 8**: Quay demo video, submit TikTok audit

**Don't forget:**
- Web đã hoạt động — confirmed bởi user
- 554 tests + 100/100 GUI audit + 17/17 web pass
- Code production-ready, chỉ cần config + test live integration

---

## 📞 9. CONTACT POINTS IN CODE

| Thứ | File:Line |
|-----|-----------|
| Entry point | `main.py` |
| Main GUI window | `gui/main_window.py` |
| FB OAuth | `core/auth_manager.py` |
| TikTok OAuth | `core/tiktok/auth_manager.py` |
| FB upload | `core/upload_engine.py` + `core/graph_uploader.py` + `core/reels_uploader.py` |
| TikTok upload | `core/tiktok/uploader_direct.py` + `core/tiktok/uploader_draft.py` |
| FB comment (Stage 7) | `core/facebook/commenter.py` |
| TikTok comment (Stage 7) | `core/tiktok/commenter.py` |
| Publisher routing | `core/publisher_registry.py` |
| Sheet runner | `core/sheet_runner.py` |
| Compliance Guard | `core/tiktok/compliance_guard.py` |
| Spam check | `core/tiktok/spam_check.py` |
| FB error mapping | `core/facebook/error_codes.py` |
| TikTok error mapping | `core/tiktok/error_codes.py` |
| Audit logger | `utils/audit_logger.py` |
| Atomic file I/O | `utils/atomic_io.py` |
| Config defaults | `gui/settings_tab.py:DEFAULTS` |
| Version source | `version.py` |

---

## 🏆 10. FINAL STATUS

```
✅ Bot code:           554/554 tests + production-ready
✅ GUI quality:        100/100 sau 6 vòng audit
✅ Website:            17/17 pages, deployed at lttstudio.top
✅ Architecture docs:  FB workflow + TikTok workflow (8 stages each)
✅ Submission docs:    5 files ready trong tiktok-submission/
✅ Meta App:           Created (App ID 2021063792619148)

⏳ Pending tasks:      11 steps total (see Section 3 above)
⏳ Critical blocker:   Upload fb-callback.html + config FB Portal
⏳ Estimated time:     ~2 hours của user để xong tất cả config
```

**🎬 Demo video TikTok + email MX là việc CUỐI cùng — không gấp.**

---

*End of docs/_luutru/HANDOFF.md*
