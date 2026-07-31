# Nhật ký

> File này ghi **sự thật đã xảy ra**. `KE_HOACH_TRIEN_KHAI.md` ghi *ý định*,
> `QUYET_DINH_NEN_TANG.md` ghi *điều đã chốt*. Khi kế hoạch và nhật ký mâu
> thuẫn, **nhật ký đúng** và phải sửa lại kế hoạch cho khớp.
>
> Mục mới thêm **lên trên cùng**. Mẫu ghi ở cuối file.
>
> **Không bao giờ ghi giá trị bí mật vào đây** — chỉ ghi tên biến, nơi lưu,
> trạng thái xoay vòng.
>
> Nhật ký của giai đoạn desktop → web (2026-07-29 đến 2026-07-30) nằm ở
> `_luutru/PROJECT_MEMORY.md`. Vẫn đáng đọc: nó ghi từng lỗi thật và cách sửa.

---

## 2026-07-31 — H7 Wave 0: sửa 6 lỗ hổng P0 (củng cố MVP trước khách trả tiền)

Từ audit toàn diện (`docs/AUDIT_MVP_2026-07-31.md`, điểm tổng ~73/100). Sửa 6 lỗ
hổng P0 tiền/bảo mật/khôi phục, MỖI lỗ kèm test:

- **W0.1 Race double-spend credit** — `credit.giu_cho` thêm `pg_advisory_xact_lock`
  theo user (chỉ Postgres; SQLite bỏ qua). Test **đồng thời trên PostgreSQL thật**
  (`test_73_dong_thoi_pg.py`, cần `LTT_TEST_DATABASE_URL`): 8 request song song
  giữ 10/10 credit → đúng 1 thành công, số dư 0 (không âm). + test claim SKIP LOCKED
  không nhặt trùng. **Cả 2 PASS trên DB `lttplatform_test`.**
- **W0.2 Dedupe không đấu dây** — thêm `job_submit.dedupe_key_for()`; đấu vào route
  `apps/demo` + `apps/thumbnail`. Test: POST /demo/queue 2 lần cùng nội dung → 1 job.
- **W0.3 IP thật sau Tunnel** — `session.client_ip()` đọc `CF-Connecting-IP`; dùng ở
  `auth.py` + `register.py`. Test: 5 sai từ IP A khoá A, IP B không vạ lây.
- **W0.4 Restore không khôi phục DB** — `restore.ps1` thêm `pg_restore --clean
  --if-exists --no-owner -1` (parse LTT_DATABASE_URL như backup.ps1). Test guard
  tĩnh + backup.ps1 pg_dump đã chạy thật lúc deploy.
- **W0.5 Lộ token phiên ở admin** — **băm token khi lưu** (`users._bam_sid`, SHA-256):
  cookie giữ token thô, DB giữ hash; `Session.id` String(43)→(64) + migration
  `b1c2d3e4f5a6` (xoá phiên cũ → đăng nhập lại). SessionAdmin bỏ cột id. Test:
  `/admin/session/list` không chứa token.
- **W0.6 update.ps1 bỏ migration** — thêm `alembic upgrade head` trước `Start-Service`.
  Test guard: có lệnh + đứng trước start.
- **W0.7 CLAUDE.md drift** — bảng "Việc còn dở" sửa lại (PostgreSQL/job/credit ✅),
  thêm H7 Hardening; đồng bộ mô hình admin (Q29).

**Kiểm chứng:** full suite **1547 passed, 3 skipped** (2 skip là test PG khi không
có env), scan 0. Deploy production + chạy migration (rc=0, sau khi pg_dump backup) +
restart. Verify edge: login token-băm 303, /jobs không lặp 200, /admin/session/list
không lộ token, health 200. Trình duyệt: /admin ẩn danh → /login (cổng auth đúng).

**Hạ tầng test:** DB `lttplatform_test` (owner ltt_app) trên PostgreSQL máy chủ,
dùng cho `test_73` khi đặt `LTT_TEST_DATABASE_URL`. Suite thường vẫn portable (tự
skip khi không có env).

## 2026-07-31 — H6.6: vỏ app launcher hai tầng + lối vào quản trị + sửa bug vòng lặp

- **Vấn đề người dùng nêu:** đăng nhập admin thấy sidebar bị 8 mục của socialbot
  (Sheet/Manual/Tài khoản FB+TikTok/Monitor/Audit) chiếm kín → tưởng "chưa tách
  app FB/TikTok". Thực ra socialbot ĐÃ là 1 app; lỗi là **cách vẽ sidebar** gộp
  phẳng mọi trang con của mọi app.
- **Sửa (thuần nền tảng, KHÔNG đụng socialbot):** sidebar thành **hai tầng** —
  tầng 1 mỗi app một dòng (launcher); tầng 2 (trang con) chỉ bung khi đang Ở
  TRONG app đó (`active_app()` dùng `app_cho_path`). socialbot co còn 1 dòng.
- **Lối vào quản trị:** thêm global `is_admin(request)` → link **🛡️ Quản trị**
  (`/admin/`) chỉ hiện cho admin CSDL. Chốt: admin về trang chủ + dùng được mọi
  app, KHÔNG ép vào panel (theo lựa chọn người dùng).
- **Banner FB/TikTok:** bỏ banner blocker TOÀN CỤC ở trang chủ; blocker doctor
  gắn vào ĐÚNG thẻ app qua field mới `AppManifest.blocker_titles` (socialbot tự
  khai "Tài khoản Facebook/TikTok") → badge "cần thiết lập" trên thẻ. Nền tảng
  KHÔNG hardcode tên app (test_60 vẫn xanh). Chi tiết vẫn ở /status.
- **BUG THẬT phát hiện khi kiểm trình duyệt (ERR_TOO_MANY_REDIRECTS):**
  `login_form` chỉ kiểm sid CÓ MẶT (`current_sid`) trong khi `require_login`
  XÁC THỰC sid với CSDL. Phiên có sid nhưng đã bị thu hồi (đổi mật khẩu/hết hạn)
  → `/login` đá sang trang, route đá về `/login` → **lặp vô tận**. Sửa:
  `login_form` dùng `current_identity_optional` (resolve sid) — đồng nhất với
  require_login. Thêm regression `test_phien_thu_hoi_khong_gay_vong_lap_redirect`.
  Ảnh hưởng mọi user bị đổi mật khẩu/hết hạn phiên, không riêng phiên này.
- **Test:** sửa `test_dashboard_surfaces_blockers` (banner→badge); thêm 4 test
  test_72 (launcher gọn / sub-nav bung / link admin / redirect loop). Full suite
  **1534 passed, 1 skipped**; scan 0.
- **Kiểm chứng production (curl edge, đăng nhập admin):** trang chủ launcher gọn
  (sub "Sheet TikTok"=0), link Quản trị hiện, badge "cần thiết lập" trên thẻ
  socialbot, banner cũ=0; trong /facebook sub-nav bung; /jobs sau login=200
  (không lặp); /login khi đã đăng nhập=303. Trình duyệt trên MÁY CHỦ chập vì
  IPv6 hỏng (curl -6 fail) — lỗi mạng máy, không phải app; xem [[don-dep-sau-h6]].

## 2026-07-31 — H6: cốt lõi vận hành (catalog công khai + SSO + login return-to) — XONG

- **Xây xong H6.1–H6.4** đúng kế hoạch Q30:
  - `current_identity_optional()` + `safe_next()` (chống open-redirect) trong
    `server/auth/session.py`; `require_login` giờ 303 về `/login?next=<path>`.
  - Trang chủ `/` **CÔNG KHAI**: `dashboard.home()` bỏ `require_login`, khách xem
    catalog (app `enabled and public`), authed thấy launcher + blockers + credit.
  - Vỏ công khai mới `base_public.html` (không sidebar); `home.html` `extends` động
    theo `authed`. `login.html` mang `next` ẩn; POST/GET login về `safe_next(next)`.
  - Trường **`public`** thêm vào `AppManifest` (mặc định True). `demo`+`socialbot`
    đặt `public=False` → ẩn khỏi catalog khách, vẫn vào được qua sidebar+phân quyền.
  - `so_du_credit(request)` global → topbar badge credit. socialbot giữ path gốc.
- **Sửa comment `registry.py`** bỏ tên slug (test_60 quét slug hardcode trong nền).
- **Test:** thêm `test_72_vanhanh.py` (6); sửa các test cũ giả định `/`→/login khi
  ẩn danh (nay `/` công khai 200) ở test_37/41/47/64/66. Full suite **1530 passed,
  1 skipped**; `scan_source_secrets` 0 finding.
- **Kiểm trình duyệt thật (Playwright, qua Cloudflare):** khách `/` → catalog chỉ
  hiện `thumbnail`; bấm → `/login?next=/thumbnail`; đăng nhập → về đúng `/thumbnail`;
  vỏ authed hiện `💳 45 credit` + `[Đăng xuất (admin@lttstudios.com)]`. DNS máy đã
  trỏ đúng Cloudflare (104.21.58.244/172.67.166.73), hết cache server cũ Vultr.
- **Lỗi test-harness ghi lại để khỏi mắc lại:** curl trong Git-Bash **path-mangle**
  `--data-urlencode "next=/thumbnail"` thành `C:/Program Files/Git/thumbnail` →
  tưởng app sai. Thực ra `safe_next` từ chối đúng chuỗi méo. Trình duyệt thật đúng.
- **Còn nợ (không phải code):** Cloudflare tự tiêm `beacon.min.js`, CSP chặn đúng →
  1 console error vô hại; tắt ở Cloudflare dashboard. Server cũ Vultr 45.32.104.192
  vẫn chạy nền (không còn trong DNS) — dọn sau.

## 2026-07-31 — Q30 + H6: chốt mô hình vận hành nền tảng (kế hoạch, chưa code)

- **Làm rõ thuật ngữ với người dùng:** mỗi app = 1 thư mục `apps/<slug>/` chạy tại
  `app.lttstudios.com/<slug>` (path-based, KHÔNG subdomain). "1 tài khoản cho mọi
  app" = SSO tự nhiên vì cùng 1 host, 1 cookie phiên — không cần thêm hạ tầng.
- **Nghiên cứu thị trường + chấm điểm 4 phương án** (path-based / subdomain+cookie-cha
  / subdomain+OIDC / hybrid). Path-based 1 host thắng: khớp ý người dùng, SSO miễn
  phí, công sức thấp, rủi ro thấp, hiện đại (mô hình "app launcher").
- **Chốt Q30:** đa-app path-based; trang chủ `/` = catalog CÔNG KHAI; đăng nhập có
  return-to (`?next=`, chống open-redirect); slug thường-gạch-nối. socialbot giữ
  path gốc (đặc cách Q10), là 1 box trong catalog; đổi `/socialbot` để sau.
- **Viết H6 chi tiết** trong KE_HOACH (H6.1 trang chủ công khai → H6.2 login next →
  H6.3 vỏ account/credit/launcher → H6.4 hai app đúng path → H6.5 slug+tài liệu+
  test), kèm sơ đồ vận hành + file/hàm cụ thể + tiêu chí + rủi ro. Dời 3 mốc tương
  lai: Thanh toán H6→H7, R2 H7→H8, Thêm tool H8→H9.
- **Phiên này CHỈ phân tích + viết kế hoạch (không sửa code)** theo yêu cầu.

## 2026-07-31 — H5: app thumbnail (tool tính phí đầu tiên) — dựng xong, chờ khoá

- **Dựng `apps/thumbnail/`** theo hợp đồng app (manifest/jobs/routes/templates),
  viết mới từ tham chiếu `D:/BOT GEMINI/.../thumbnail_api` (chỉ đọc): gọi
  `gemini-2.5-flash-image` bằng httpx sync (bỏ api-pool/cascade của họ), lưu ảnh
  qua `platform_core.storage`, `GEMINI_API_KEY` phía máy chủ + che khoá ở lỗi.
- **Hai lỗ hổng hợp đồng lộ ra (H5 = phép thử hợp đồng) & đã lấp:**
  (1) template app — `server/templating.py` ChoiceLoader tìm `apps/*/templates/`;
  (2) tải file output — app tự phục vụ `/image/{key}` (kiểm sở hữu theo key);
  download_token storage KHÔNG dùng được qua worker→web (RAM mỗi tiến trình).
  Ghi vào `docs/03`. KHÔNG đụng `platform_core/`.
- **Test:** `test_71` (5, Gemini mock) + `test_60` registry xanh; full suite
  **1523 pass, 1 skip**; scan 0 (thêm `.playwright-mcp`/`.claude` vào loại trừ
  của cả `scan_source_secrets.py` lẫn `build_release.py`).
- **Nghiệm thu render (Cloudflare edge):** `/thumbnail` hiện form + gallery, app
  **tự lên trang chủ/sidebar** không sửa giao diện nền tảng.
- **✅ CHẠY THẬT — H5 KHÉP:** người dùng nạp `GEMINI_API_KEY` vào app.env; nạp lại
  env dịch vụ + restart. Cấp 50 credit cho `admin@lttstudios.com`, tạo 1 thumbnail
  qua Cloudflare edge → job **done**, ảnh **1.8 MB PNG thật** (magic `89 50 4e 47`)
  lưu ở `data/files/thumbnail/<uid>/<job>/0.png`, số dư **50 → 45** (trừ đúng 5).

- **🔴 LỖI BẢO MẬT phát hiện & VÁ khi test chặn truy cập:** ẩn danh gọi
  `/thumbnail/image/<key>.png` vẫn nhận ảnh (HTTP 200) dù origin chặn (303) —
  vì **Cloudflare cache file .png** theo đuôi (`cf-cache-status: HIT`,
  `max-age=14400`) rồi phục vụ cho người KHÔNG đăng nhập, bỏ qua auth. Middleware
  cũ chỉ `no-store` cho text/html. **Vá:** `server/app.py` đặt `Cache-Control:
  no-store` cho MỌI response ngoài `/static/` (chặn cả lớp lỗi). Deploy + purge
  cache → ẩn danh giờ **303 /login, cf-cache-status: BYPASS**; chủ vẫn 200. Thêm
  test khoá `test_43::test_dynamic_responses_are_not_cacheable`. Full suite
  **1524 pass**. BÀI HỌC: sau CDN, nội dung riêng-tư phải no-store; đừng để đuôi
  file quyết định cache.

## 2026-07-31 — Resend + Turnstile (điều khiển trình duyệt) — đăng ký sẵn sàng

- **Turnstile:** tạo widget "LTT app" (Managed) cho `app.lttstudios.com` trong
  Cloudflare. Site key `0x4AAAAAAECt29NR1TKkMFDx` (công khai), Secret key đặt vào
  app.env (`TURNSTILE_SITE_KEY`/`TURNSTILE_SECRET_KEY`). Kiểm: `/register` render
  `cf-turnstile` + api.js.
- **Resend:** thêm domain **`mail.lttstudios.com`** (subdomain riêng để không đụng
  SPF trang chủ iNET). DNS (DKIM/SPF/MX) áp qua **Cloudflare Domain Connect** —
  chuẩn one-time, Cloudflare ghi rõ "không cấp Resend quyền sửa về sau" (least-
  privilege, hơn OAuth token). Domain **verified**. Bản ghi đã kiểm sống qua
  8.8.8.8. API key **Sending access** (`re_...`) đặt vào `RESEND_API_KEY`;
  `LTT_MAIL_FROM="LTT AI Studio <no-reply@mail.lttstudios.com>"`.
- **Chú ý chép DKIM:** trang Resend cắt giữa giá trị (`[…]`) → chép tay sai. Domain
  Connect (URL query `domainKey=...`) mang giá trị đầy đủ → dùng đường đó, chính xác.
- **Nạp khoá:** cả 4 khoá vào `C:\LTTPlatform\secrets\app.env` + `nssm set
  AppEnvironmentExtra` cho Web+Worker + restart. health ready. mailer → ResendMailer.
- **Còn lại (người dùng tự kiểm khi muốn):** đăng ký thử bằng email thật → nhận
  mail xác thực → +credit dùng thử. Chưa test end-to-end vì không có hộp thư kiểm.

## 2026-07-31 — H3-admin đợt 2: admin trong DB + credit dùng thử + test

- **`tools/create_admin.py`**: tạo/nâng user role=admin (băm PBKDF2, idempotent,
  mật khẩu qua getpass hoặc `LTT_NEW_ADMIN_PASSWORD`, không in ra). Đã tạo
  `admin@lttstudios.com`. **Nghiệm thu production thật** (curl ép Cloudflare edge):
  login bằng email → 303, `/admin` với phiên đó → 200 → admin DB vào được, KHÔNG
  cần admin-env.
- **Credit dùng thử**: `/verify-email` gọi `credit.cap_tay` một lần đúng lần
  verify đầu (idempotent theo `was_verified`); lượng `LTT_TRIAL_CREDIT` mặc định 20.
- **Test `test_70_admin_h3.py`** (3): trial-credit idempotent, /admin đá ẩn danh,
  chỉ role=admin vào /admin. Full suite **1518 pass, 1 skip**; scan 0 finding.
- **Phát hiện thêm:** dashboard hiện `[email protected]` do **Cloudflare "Email
  Obfuscation" (Scrape Shield)** tự sửa HTML động (cùng họ beacon) — bug hiển thị
  thật, cần tắt Scrape Shield/beacon trong dashboard cho host proxied.
- **admin-env: chốt Q29 (giữ break-glass, vô hiệu production).** Xoá
  `LTT_ADMIN_PASSWORD_HASH` khỏi app.env + nạp lại env dịch vụ. LỖI GẶP: web
  service chết (Paused, 502) vì `settings.py` bắt buộc hash ở production →
  `MissingServerSecretError`. Sửa: bỏ ADMIN_USERNAME/HASH khỏi danh sách secret
  bắt buộc (chỉ còn SESSION_SECRET), deploy settings.py, restart → web sống lại.
  Nghiệm thu: admin-env → 401; DB admin → 303 + /admin 200. → **H3-admin XONG.**
  BÀI HỌC: xoá secret bắt buộc mà không sửa validator = tự sập app.

## 2026-07-31 — H3-admin: trang quản trị sqladmin (MVP xong)

- **Kiểm tương thích trước:** app chạy Starlette 1.3.1; `pip install --dry-run`
  cho thấy `sqladmin 0.20.1` chấp nhận Starlette 1.3 (không hạ version) → Q15
  giữ nguyên. Thêm `sqladmin>=0.20.1,<0.21` + `wtforms>=3.1.2,<4.0` (Q17).
- **`server/admin.py`:** `AdminAuth(AuthenticationBackend)` dùng CHUNG phiên nền
  tảng (truyền `session_secret` → cùng cookie "session"); admin = admin-env
  (`session["user"]`) hoặc user DB role=admin. Không admin → 303 /login. 7 view:
  User (sửa role/active/verified, không sửa email/hash, không xoá), CreditEntry
  **read-only (append-only H3)**, AppAccess CRUD, Job read-only, Session xoá-để-
  thu-hồi, PlatformInfo read-only, và `GrantCreditView` /admin/grant-credit gọi
  `credit.cap_tay`.
- **Gắn ở `create_app` CÓ GUARD:** `try/except` quanh import+setup — thiếu
  sqladmin (test chạy system python) hoặc chưa có CSDL → `admin_ready=False`,
  bỏ qua, KHÔNG vỡ app. Đã cài sqladmin vào cả venv (bản chạy) lẫn system python
  (môi trường test).
- **Nghiệm thu browser thật:** đăng nhập admin → `/admin` hiện đủ 7 view, đọc
  PostgreSQL thật OK; chưa đăng nhập → 303 /login. curl `/admin/` (ẩn danh) → 303.
- **Test:** full suite **1512 pass, 1 skip** sau khi sửa 3 chỗ do thay đổi hôm
  nay: (1) `test_41` assert wording home "đang chặn bot"→"việc cần thiết lập";
  (2)(3) `test_44` release scanner bắt `.playwright-mcp/*.yml` → thêm
  `.playwright-mcp` vào `EXCLUDED_DIRS` của `build_release.py` + `.gitignore` +
  xoá rác. `scan_source_secrets` = 0 finding.
- **Còn lại H3-admin:** tạo admin trong DB → gỡ admin-env; cấp credit dùng thử
  sau verify email (nối H1.3); test tự động cho admin.py.

---

## 2026-07-31 — Dọn branding + fix Cache-Control + phát hiện DNS resolver cũ

### Dọn nợ H0.1 (mục A — "socialbot chỉ là 1 app")

- `base.html` + `home.html` vốn ĐÃ đúng: sidebar/danh sách app sinh từ
  `apps/*/manifest.py` (không viết cứng). socialbot là 1 nav-group hợp lệ.
- Sửa branding platform-level: `login.html` "đăng bài Facebook & TikTok" →
  "Nền tảng công cụ AI — dùng theo credit"; `home.html` "việc đang chặn bot
  đăng bài" → "việc cần thiết lập". Thêm favicon SVG (`server/static/favicon.svg`
  + link ở base/base_plain) → hết 404.
- **Nợ SÂU chưa động (cần quyết định, mâu thuẫn Q10 freeze):** route + template
  socialbot (sheet/manual/accounts/monitor/oauth/workers) nằm trong `server/`,
  không ở `apps/socialbot/`. Tách ra là refactor lớn code đóng băng → để sau.

### Fix bảo mật: Cache-Control cho HTML

- `server/app.py`: HTML response nay gửi `Cache-Control: no-store` (file tĩnh
  không đụng). Trước đó không có → proxy/CDN có thể cache trang động (rủi ro
  phục vụ trang người này cho người khác). Đã xác minh qua Cloudflare edge:
  `cf-cache-status: DYNAMIC` (không cache). `test_43`+`test_37` xanh (41).

### Phát hiện: máy chủ tự thấy nội dung CŨ do DNS resolver, KHÔNG phải lỗi nền tảng

- curl/local trên máy chủ trỏ `app.lttstudios.com` → **45.32.104.192** (máy Vultr
  CŨ vẫn chạy Caddy+bản LTT cũ) vì **DNS resolver của router/ISP còn cache A record
  cũ** từ iNET trước khi đổi NS; `ipconfig /flushdns` không xoá được cache router.
- **Public đúng:** ép curl qua Cloudflare edge 104.21.58.244 → tagline MỚI,
  `Server: cloudflare`, `Cache-Control: no-store`, favicon 200, health ready.
  Trình duyệt (IPv6→Cloudflare) cũng hiện bản mới. → **Người dùng thật thấy app
  mới**; chỉ máy chủ thấy cũ tới khi cache resolver hết TTL (hoặc đổi DNS máy sang
  1.1.1.1). **Lưu ý:** có một máy chủ CŨ ở 45.32.104.192 vẫn chạy — cân nhắc gỡ.
- Còn 1 lỗi console: Cloudflare tự chèn `static.cloudflareinsights.com/beacon.min.js`,
  bị CSP chặn (đúng — không nhận JS bên thứ ba). Vô hại; tắt auto-inject trong
  dashboard sau nếu muốn.

---

## 2026-07-31 — ✅ H0.1 HOÀN TẤT: app.lttstudios.com sống, nghiệm thu thật

- **Tunnel:** sửa `setup/3` cài `cloudflared` **qua NSSM** (`--config ... tunnel
  run`) thay `cloudflared service install` (bản 2026.x cho ImagePath trần → không
  kết nối). Hardened: kill process + `sc delete` thay `Stop-Service` (tránh treo
  StopPending). Ổn định: curl **8/8 = 200**, `tunnel info` có active connection.
- **Quyền Admin:** shell Claude không elevated → không cài dịch vụ được. Người
  dùng **relaunch VS Code as administrator** → Claude tự chạy nốt (kill service
  kẹt, `sc delete`, chạy `setup/3`, đặt mật khẩu, nghiệm thu).
- **Mật khẩu admin:** đặt `admin` / (mật khẩu người dùng cấp, tạm, sẽ đổi) qua
  hash + nạp vào env cả 2 dịch vụ + restart. Lưu ở memory cục bộ (ngoài git).
- **Nghiệm thu browser thật:** đăng nhập admin → control plane hiện "2 app đã
  nạp" (demo, socialbot). Demo "chạy qua hàng đợi" trả 400 **đúng thiết kế**
  (admin bootstrap không có sổ credit; cần user đăng ký thật). `setup/4`: mọi
  mục ĐẠT (3 dịch vụ Running, chỉ nghe 127.0.0.1, /docs 404, secrets siết, 2 app).
- **Test:** `test_45` + `test_61` = 73 pass; `scan_source_secrets` = **0 finding**
  (sau khi dọn rác `.playwright-mcp/`).
- **Nợ để lại (không chặn):** control plane còn branding socialbot cũ + route gốc;
  lỗi console Cloudflare beacon (CSP); favicon 404. Cần cấu hình Resend/Turnstile
  trước khi mở đăng ký cho khách.

---

## 2026-07-31 — Q28: bố trí ổ đĩa + sao lưu chống mất dữ liệu; setup/2 đã cài xong

### Bối cảnh — làm rõ hiểu lầm về bố trí

- Người dùng lo mất dữ liệu nếu ổ C:/Windows hỏng. Ban đầu tưởng muốn dời bản
  chạy sang D:, nhưng làm rõ lại: **giữ mô hình chuẩn** — bản chạy `C:\LTTPlatform`
  (ổ C = Disk 0), nguồn/bộ cài `D:\LTTSTUDIOSAPP` (ổ D = Disk 1) — và **thêm cơ
  chế backup C: → `D:\LTTBackups`** (ổ vật lý khác). Chốt thành **Q28**.
- Ổ: C = Lexar 1TB (645GB trống, Disk 0), D = Samsung 970 EVO Plus 500GB (114GB
  trống, Disk 1) — hai ổ vật lý riêng. PostgreSQL data ở `C:\Program Files\
  PostgreSQL\17\data`.

### Đã làm

- **Q28** thêm vào `QUYET_DINH_NEN_TANG.md`: bản chạy C:, nguồn/backup D:,
  off-site khi thương mại. Nhấn: backup PHẢI gồm `secrets\app.env` (mất
  `LTT_TOKEN_ENCRYPTION_KEY` = mất token dù DB còn); tự động + định kỳ + restore
  thử; cùng máy vẫn là điểm chết chung → off-site bắt buộc khi có tiền.
- `deploy\windows\backup.ps1`: thêm tham số `-BackupDir` (mặc định `$Root\backups`,
  cho phép trỏ sang ổ khác). Đã có sẵn `pg_dump -Fc` + gói `*.enc`/config/audit +
  `-IncludeSecrets` + giữ 14 bản + kiểm zip đọc được.
- `deploy\windows\5-lich-backup.ps1` (MỚI): đăng ký Scheduled Task chạy backup
  mỗi ngày, tài khoản SYSTEM, ghi sang `D:\LTTBackups`; cảnh báo nếu BackupDir
  cùng ổ với bản chạy; chạy thử một lần để kiểm.
- Kiểm: cả 2 `.ps1` thuần ASCII + không BOM; PowerShell parse OK; `test_61` xanh
  (49 passed).

### setup/3 (Tunnel) — LỖI dịch vụ cloudflared + đã sửa bằng NSSM

- Người dùng chạy `setup\3`: bước 5 (route dns) từng CRASH vì cloudflared ghi log
  ra stderr → dưới `ErrorActionPreference='Stop'` + `2>&1` thành NativeCommandError.
  Sửa bằng hàm `Invoke-Cf` (chuyển stderr ra file tạm rồi gộp, không thành error
  record). Bản ghi `app.lttstudios.com` (CNAME → tunnel) đã tạo.
- **Lỗi thật hơn:** `cloudflared service install` bản **2026.7.3** tạo dịch vụ
  Windows với **ImagePath TRẦN** (`cloudflared.exe`, không tham số) → dịch vụ chạy
  nhưng không biết chạy tunnel/config nào → `tunnel info` báo **"no active
  connection"** → `app.lttstudios.com` trả **530/1033**. (Lúc script vừa cài, health
  check thoáng qua `status=ready` rồi rớt — gây hiểu nhầm là đã xong.)
- **Sửa:** viết lại bước 6 của `setup\3` — cài dịch vụ `cloudflared` **qua NSSM**
  với đúng dòng lệnh `--config C:\LTTPlatform\cloudflare\config.yml tunnel run`
  (giống cách setup\2 cài Web/Worker); tự gỡ bản dịch vụ cũ (kể cả ImagePath trần)
  trước khi cài lại. ASCII + không BOM + parse OK + test_61 xanh.
- **CHẶN:** cần người dùng chạy LẠI `setup\3` trong PowerShell Admin để áp bản sửa
  (idempotent: dùng lại tunnel + cert, chỉ cài lại dịch vụ cho đúng).

### setup/2 — người dùng đã tự chạy, THÀNH CÔNG

- `C:\LTTPlatform\` nay có đủ `app\ venv\ secrets\app.env tools\nssm.exe data\ logs\`.
- Dịch vụ `LTTStudioWeb` + `LTTStudioWorker`: **Running**. `:8100/health/ready` →
  **200**. DB nối đúng (nhờ `postgres-superuser.txt` đã stage trước → setup/2 tự
  tạo/khớp `LTT_DATABASE_URL` + migration).
- ⚠️ setup/2 in mật khẩu admin MỘT LẦN — cần xác nhận người dùng đã lưu.

### CHẶN — cần Admin (shell Claude không elevated)

1. `deploy\windows\5-lich-backup.ps1` — cài lịch backup sang `D:\LTTBackups`.
2. `setup\3-cloudflare.ps1` — dựng Tunnel (zone đã Active); có bước
   `cloudflared tunnel login` chọn zone `lttstudios.com`.
3. `setup\4-nghiem-thu.ps1` + kiểm `app.lttstudios.com` trên trình duyệt thật.

---

## 2026-07-31 — H0.1: thêm zone lttstudios.com vào Cloudflare + dọn DNS (điều khiển trình duyệt)

- **Mục tiêu:** đưa `app.lttstudios.com` lên mạng qua Cloudflare (Q27 — chuyển
  cả zone), giữ trang chủ `lttstudios.com` ở inet.vn OnePanel không đứt.
- **Hạng mục:** H0.1 — đã tới bước cuối cùng: đổi nameserver (CHẶN, chờ người dùng).

### Đã làm (điều khiển 2 tab qua Playwright)

- **Thêm site `lttstudios.com` vào Cloudflare, gói Free.** Tài khoản Cloudflare
  `Giaitritruyenthongltt@gmail.com` (account id 3530f3e5...).
- **Phát hiện quan trọng — IP gốc thật vs IP biên OneShield.** Quét tự động của
  Cloudflare chỉ thấy IP biên OneShield (rải: 103.166.183.10, 103.216.118.10,
  103.56.163.10; và 1 AAAA). Panel iNET mới cho IP gốc thật: **103.57.220.210**.
- **Đã kiểm chứng bằng curl:** gọi thẳng `103.57.220.210` (Host lttstudios.com,
  HTTPS) trả 200 và đúng trang chủ ("LTT Studios | Digital Products, Automation
  & Media Systems"), kích thước gần khớp bản qua OneShield. HTTP → 301 lên HTTPS.
  → Trỏ thẳng vào IP gốc DNS-only là **an toàn**, không cần OneShield.
- **Dọn DNS trên Cloudflare còn đúng bộ chuẩn (đều DNS only / mây xám):**
  - `A  lttstudios.com  103.57.220.210`  (DNS only)
  - `A  www            103.57.220.210`  (DNS only)
  - Đã xoá: bản ghi `app A 45.32.104.192` (Tunnel sẽ tạo lại CNAME sau), toàn bộ
    bản ghi IP-biên-OneShield của @ và www, và 1 bản ghi AAAA của www.
- **Lấy được nameserver Cloudflare cấp:** `elsa.ns.cloudflare.com` +
  `kipp.ns.cloudflare.com`.
- **ĐÃ ĐỔI NAMESERVER Ở iNET** (người dùng xác nhận "đổi ngay"): trang Chi tiết
  tên miền iNET nay hiện `elsa.ns.cloudflare.com` + `kipp.ns.cloudflare.com`.
  Đã BỎ TRỐNG checkbox "Tự động bật OneShield" (ta rời OneShield). Đã bấm "I
  updated my nameservers" ở Cloudflare → zone trạng thái **pending** ("Waiting
  for registrar to propagate", ~1–2 giờ, tối đa 24 giờ, Cloudflare tự kiểm).
- **Kiểm ngay sau đổi:** trang chủ vẫn 200 (còn qua IP biên OneShield do resolver
  công cộng chưa hết cache NS cũ). Khi NS mới lan tới, sẽ chạy thẳng 103.57.220.210.

### ZONE ĐÃ ACTIVE (2026-07-31, chỉ sau ít phút)

- NS mới lan tới resolver công cộng rất nhanh (8.8.8.8 + 1.1.1.1 trả `elsa`/`kipp`,
  `@` → 103.57.220.210). Cloudflare xác minh xong → zone **Active**: trang overview
  hiện đủ tính năng (CDN/cache, DDoS, SSL/TLS, WAF mặc định; có "Pause Cloudflare",
  đang cấp Universal SSL). **Phần zone/DNS Cloudflare COI NHƯ XONG.**
- Còn lại để `app.lttstudios.com` sống = **dựng Tunnel** (setup/3), cần app chạy
  `:8100` trước (setup/2). Cả hai cần Administrator.

### Đã chuẩn bị sẵn cho lần cài (Admin) — giảm rủi ro

- DB đã có sẵn từ dev H1–H4: role `ltt_app` + database `lttplatform` tồn tại,
  mật khẩu superuser trong `secrets/postgres-superuser.txt` khớp PostgreSQL 17
  đang chạy (đã kiểm bằng psql -w, auth OK).
- Đã copy `postgres-superuser.txt` vào `C:\LTTPlatform\secrets\` để `setup/2` tự
  tạo/khớp `LTT_DATABASE_URL` + chạy migration, không phải làm tay.
- CỐ Ý KHÔNG copy `app.env` dev sang (nó thiếu hash admin/session/token) — để
  `setup/2` tự sinh `app.env` đầy đủ + in mật khẩu admin mới đúng một lần.

### CHẶN — cần quyền Admin (shell của Claude không elevated)

1. `setup\2-cai-dat.ps1` (PowerShell **Run as administrator**) — cài nền tảng,
   in mật khẩu admin MỘT LẦN.
2. `setup\3-cloudflare.ps1` (Admin) — dựng Tunnel; có bước `cloudflared tunnel
   login` mở trình duyệt chọn zone `lttstudios.com`.
2. **Cài nền tảng:** `C:\LTTPlatform` hiện chỉ có thư mục `data` (rác từ test
   H1–H4). PostgreSQL 17 đang chạy, nhưng CHƯA có dịch vụ LTTStudioWeb/Worker/
   cloudflared, chưa có app/venv/secrets. Phải chạy `setup\2-cai-dat.ps1` trong
   **PowerShell Administrator** (shell hiện tại của Claude KHÔNG elevated).
   Script in mật khẩu admin đúng MỘT LẦN — lưu lại ngay.
3. **Dựng Tunnel:** sau khi zone Active + đã cài, chạy `setup\3-cloudflare.ps1`
   (Admin). Có một bước `cloudflared tunnel login` mở trình duyệt để cấp cert.
- **Lưu ý:** khi rời DNS iNET, OneShield (CDN/WAF của iNET) ngừng cho tên miền
  này; trang chủ chạy thẳng từ IP gốc 103.57.220.210 (đã kiểm chứng OK).

---

## 2026-07-31 — H0.1: kiện toàn script Cloudflare cho Q22 (phần chuẩn bị)

- **Mục tiêu:** chuẩn bị dựng Tunnel; người dùng chọn "đưa lên mạng trước H5".
- **Hạng mục:** H0.1 — phần code/tài liệu xong; phần thao tác chờ người dùng.
- **Trạng thái:** dở — chặn ở thao tác người dùng (Cloudflare + inet.vn + Admin).

### Đã làm (phía tôi)

- `setup/3-cloudflare.ps1`: sửa khớp Q22 (uỷ quyền subdomain). Bước đăng nhập
  nay hướng dẫn chọn zone `app.lttstudios.com` (không phải `lttstudios.com`
  gốc); bước trỏ DNS bắt lỗi "không tìm thấy zone" và giải thích điều kiện tiên
  quyết thay vì để một lỗi mờ mịt.
- `docs/04_CLOUDFLARE_TUNNEL.md`: thêm phần "Điều kiện tiên quyết — uỷ quyền
  subdomain (Q22)" với các bước cụ thể + hai đường lui nếu gói miễn phí không
  cho tạo zone subdomain.
- Kiểm cú pháp + ASCII + không-BOM cho script; test khoá `test_61` xanh.

### Chặn — cần người dùng (không code nào thay được)

1. **Kiểm Cloudflare zone subdomain (Q22 điều kiện chưa xác minh):** thử Add
   site `app.lttstudios.com` — gói miễn phí có thể từ chối.
2. Nếu được: uỷ quyền NS `app` ở inet.vn.
3. Cài hệ thống lên `C:\LTTPlatform` (setup/2, cần Administrator) — máy này
   CHƯA cài (`C:\LTTPlatform` chưa tồn tại).
4. Chạy `setup/3-cloudflare.ps1` (cần đăng nhập Cloudflare bằng trình duyệt).

### Lưu ý vận hành: máy phát triển == máy chủ

Máy này đang là máy phát triển và sắp thành máy chủ. Database `lttplatform`
hiện dev dùng (chỉ có schema, data nghiệm thu đã dọn). Khi `setup/2` cài
production, nó dùng lại chính PostgreSQL + database đó; schema đã sẵn. `setup/2`
sẽ đặt lại mật khẩu `ltt_app` → `secrets/app.env` của dev (ở `D:`) lệch, nhưng
không sao vì sau khi thành máy chủ chỉ chạy bản `C:\LTTPlatform`.

### Việc tiếp theo

1. **Người dùng:** kiểm Cloudflare zone subdomain (bước 1 ở trên) — báo kết quả.
2. Tuỳ kết quả: uỷ quyền NS rồi cài, hoặc đổi Q22 theo giao thức.
3. Sau khi lên mạng: H5 (thumbnail_api).

---

## 2026-07-31 — H3 (sổ credit) + H2.3 (web submit) + H4 (nghiệm thu): KHÉP HẠ TẦNG

- **Mục tiêu:** sổ credit không bao giờ sai; submit job qua web + tiến độ; nghiệm
  thu toàn chuỗi bằng demo.
- **Hạng mục:** H3 (trừ trang admin) + H2.3 + H4 — **hoàn thành**.
- **Trạng thái:** xong chuỗi chính. Giai đoạn hạ tầng (H1→H4) đã khép.

### Sổ credit (H3)

- Bảng `credit_entries` **chỉ ghi thêm**; số dư = tổng của sổ, không ô sửa đè.
  Với tiền, truy được nguồn gốc quan trọng hơn tiết kiệm vài dòng.
- `platform_core/credit.py`: nạp / cấp-tay / giữ-chỗ / quyết-toán / hoàn.
  Giữ chỗ kiểm số dư TRƯỚC (không đủ → không tạo job, không gọi API). Quyết
  toán/hoàn **idempotent theo job** (worker retry không trừ/hoàn hai lần).
- `platform_core/job_submit.py`: tạo job + giữ chỗ credit trong CÙNG transaction.
  Dedupe → giữ chỗ đúng một lần (chặn "Tạo lại"/F5 — đúng lỗi P0-5 của BOT GEMINI).
- Nối worker: complete → quyết toán; error hẳn → hoàn (job_runner).

### Web submit + tiến độ (H2.3)

- `server/routes/jobs.py`: danh sách + chi tiết + fragment tiến độ, **lọc theo
  user** (A xem job B → 404).
- Tiến độ đẩy về trình duyệt bằng HTMX (Q18). **Self-host** `htmx.min.js` trong
  `server/static/` + mount StaticFiles — CSP chặn CDN nên không dùng unpkg.
- `apps/demo` thêm nút "Chạy qua hàng đợi" → khuôn cho app thật.

### Nghiệm thu toàn chuỗi (H4) — browser + PostgreSQL + worker thật

Đăng nhập (user CSDL) → /demo → "Chạy qua hàng đợi" → job tạo + giữ chỗ credit
→ worker process nhặt → xử lý → **trang HTMX tự cập nhật** queued→done → kết quả
đúng ("nghiem thu toan chuoi H4" đảo ngược). Console 0 lỗi.

Sổ credit sau đó (đọc thật từ Postgres):
    topup  +100
    hold   -1    giu cho job
    settle +0    giu 1, that 1
    -> so du 99. Dau vet append-only day du, dung tuyet doi.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.513 passed**, 1 skipped, 23 subtests |
| `tests/test_68_credit.py` | 13 passed |
| `tests/test_69_web_jobs.py` | 6 passed (gồm A-không-đọc-job-B) |
| Nghiệm thu H4 browser + Postgres + worker | chuỗi đầy đủ, sổ đúng, console sạch |
| `python tools/scan_source_secrets.py` | 0 finding |

### Đã tách/dời có lý do

- **H3-admin** (trang quản trị credit/quyền qua sqladmin, tạo admin trong DB,
  gỡ đường admin-env): gom vào một mốc riêng — cả cụm là mặt admin, dùng chung
  sqladmin, không phải mặt khách.
- Hai mục H4 phụ (giết worker giữa job dài; tắt CSDL báo lỗi UI): cần tình huống
  chạy-lâu hoặc thuộc observability, không chặn H5.

### Cách lùi lại

Xoá `platform_core/{credit,job_submit}.py`, `server/routes/jobs.py`,
`server/static/`, 3 template job, `tests/test_68_credit.py`,
`tests/test_69_web_jobs.py`, migration `..._credit_entries`; hoàn
`platform_core/{models,job_runner}.py`, `server/{app,deps,templating}.py`,
`server/templates/{base,demo}.html`, `apps/demo/routes.py`.

### === GIAI ĐOẠN HẠ TẦNG (H1→H4) ĐÃ KHÉP ===

Nền tảng giờ chạy được toàn chuỗi: người dùng → phân quyền → hàng đợi job →
worker → sổ credit → tiến độ web. Mọi mắt xích nghiệm thu trên PostgreSQL thật,
phần lớn có cả browser. Sẵn sàng cắm tool tính phí đầu tiên (H5).

### Việc tiếp theo

1. H5 — port `thumbnail_api` từ BOT GEMINI thành app đầu tiên tính phí (Q11).
2. H3-admin — trang quản trị (sqladmin) khi cần vận hành thật.
3. (người dùng) H0.1 Cloudflare + khoá Resend/Turnstile.

---

## 2026-07-31 — H2.1+H2.2: hàng đợi job + worker (bỏ procrastinate)

- **Mục tiêu:** việc dài chạy ngoài vòng đời request, sống sót restart, không
  bao giờ hai worker làm trùng.
- **Hạng mục:** H2.1 (hàng đợi) + H2.2 (worker) — **hoàn thành**. H2.3 (web UI +
  tiến độ) tách ra, làm cùng H3.
- **Trạng thái:** xong phần lõi, nghiệm thu trên PostgreSQL thật.

### Quyết định đổi hướng: bỏ procrastinate (Q13 → Q26)

Khi thiết kế H2 mới thấy procrastinate giữ hàng đợi trong **bảng riêng của
nó**, tách khỏi bảng `jobs` nghiệp vụ → hai kho phải đồng bộ. Và để job+credit
atomic (chính lý do chọn nó) phải cho `defer` chung transaction với SQLAlchemy —
chia sẻ connection, tài liệu mỏng. Nghịch lý: cái lý do chọn nó lại **dễ hơn**
khi tự quản một bảng. Đưa lựa chọn cho chủ dự án → chọn tự viết. Dọn Q13 đúng
giao thức (đánh dấu ĐÃ THAY, thêm Q26, gỡ procrastinate khỏi venv, sửa kế hoạch).

### Đã làm

- Bảng `jobs` (nguồn chân lý duy nhất) + `platform_core/jobs.py`:
  - `submit` không commit (caller commit cùng credit — atomic hiển nhiên);
  - `claim` dùng `FOR UPDATE SKIP LOCKED` (nhiều worker không nhặt trùng);
  - `fail` retry luỹ thừa có giới hạn rồi mới thành `error`;
  - `reclaim_orphans` nhặt lại job của worker chết (tính một lượt đã tiêu);
  - `dedupe_key` chống double-submit/F5;
  - `resolve_handler` qua registry, không hardcode slug.
- `platform_core/job_runner.py` + `job_worker.py`: vòng chạy + entry. Mỗi bước
  (claim/tiến độ/complete) là transaction ngắn RIÊNG — không giữ khoá dòng suốt
  thời gian chạy handler.
- Dịch vụ `LTTStudioWorker` riêng (Q6) trong `setup/2-cai-dat.ps1`;
  `update.ps1`/`rollback.ps1`/`4-nghiem-thu.ps1` biết về nó.

### Nghiệm thu trên PostgreSQL thật (không phải suy luận)

- **SKIP LOCKED:** 5 worker (thread) × 30 job → mỗi job chạy ĐÚNG MỘT LẦN,
  không trùng, tất cả done. Đây là rủi ro lớn nhất (job làm hai lần trên API
  tính tiền) — chứng minh, không giả định.
- **Worker process thật:** chạy `job_worker.py`, submit job demo → worker nhặt →
  complete với kết quả đúng (`"worker process that"` → đảo ngược).

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.495 passed**, 1 skipped, 23 subtests |
| `tests/test_67_hang_doi_job.py` (SQLite) | 15 passed |
| SKIP LOCKED 5 worker × 30 job trên PostgreSQL | không trùng, tất cả done |
| Worker process thật end-to-end | job nhặt → complete đúng |
| `python tools/scan_source_secrets.py` | 0 finding |

### Quyết định mới

Q26 — hàng đợi tự quản bảng jobs + SKIP LOCKED (thay Q13 procrastinate).

### Hoãn có lý do

- Lọc capability worker (Q6): claim chưa lọc theo `requires` vì một worker đa
  năng. Chỗ lọc đã ghi sẵn trong `claim()`, thêm khi có nhiều máy.
- H2.3 (web submit + tiến độ + trang jobs): tách ra làm cùng H3, vì đường
  submit job và trừ credit là cùng một giao dịch — viết một lần có cả hai.

### Cách lùi lại

Xoá `platform_core/{jobs,job_runner}.py`, `job_worker.py`,
`tests/test_67_hang_doi_job.py`, migration `..._them_bang_jobs.py`; hoàn
`platform_core/models.py`, `setup/2-cai-dat.ps1`, `deploy/windows/*.ps1`,
`setup/4-nghiem-thu.ps1`.

### Việc tiếp theo

1. H3 — sổ credit (append-only, giữ chỗ → quyết toán → hoàn) + H2.3 (web submit
   + tiến độ) cùng lúc: submit job và trừ credit là một giao dịch.
2. (người dùng, độc lập) H0.1 Cloudflare + khoá Resend/Turnstile.

---

## 2026-07-31 — H1.4: phân quyền app + KHÉP H1 (Người dùng)

- **Mục tiêu:** mỗi (user × app) mở/khoá/ẩn; chặn ở tầng route, không chỉ ẩn nút.
- **Hạng mục:** H1.4 — **hoàn thành**. Cùng đó **khép toàn bộ H1**.
- **Trạng thái:** xong.

### Đã làm

- Bảng `app_access` + `platform_core/app_access.py`: mức `enabled`/`locked`/
  `hidden`, mặc định mở (Q25), chỉ lưu ngoại lệ (đặt về mặc định thì XOÁ dòng).
- `server/access_middleware.py`: chặn ở tầng route qua middleware đọc registry
  → ánh xạ path → app → kiểm quyền. Phủ **mọi** đường vào kể cả gõ thẳng URL,
  và không phải sửa từng app (giữ hợp đồng: nền tảng không biết trước app nào).
  - `hidden` → 404 (không xác nhận app tồn tại), `locked` → 403.
  - Fail-open có chủ ý: chưa có DB / admin-env / lỗi → cho qua (mặc định mở,
    chốt chặn tiền vẫn là credit).
  - Add TRƯỚC SessionMiddleware để chạy SAU nó (đọc được session).
- Trang chủ **và** sidebar cùng lọc app `hidden` theo user (`nav_apps(request)`).
- `tests/test_66_phan_quyen_app.py` — 10 test.

### Nghiệm thu chặn route trên PostgreSQL thật

Tạo user tạm → đăng nhập → `/demo` mặc định 200 → admin đặt `hidden` → `/demo`
404 → đặt `locked` → 403 → dọn. Đúng cả ba mức.

### Lỗi tiềm ẩn sửa kèm: CSP sẽ chặn Turnstile

CSP cũ chỉ cho script `'self'`. Turnstile (H1.3) nạp script + iframe từ
`challenges.cloudflare.com` → sẽ bị CSP chặn ngay khi bật, một lỗi chỉ lộ lúc
production bật chống-bot. Đã thêm domain đó vào `script-src` + `frame-src`.

### Test đã sửa (không làm yếu)

`test_31::test_g2_navigation_links_every_page` grep chuỗi cứng `nav_apps()`.
H1.4 đổi thành `nav_apps(request)` (thêm lọc theo user). Bất biến — "sidebar
sinh từ registry" — vẫn đúng; đổi assertion sang khớp `nav_apps(`.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.480 passed**, 1 skipped, 23 subtests |
| `tests/test_66_phan_quyen_app.py` | 10 passed |
| Nghiệm thu chặn route trên PostgreSQL thật | 200 / 404 / 403 đúng |
| `python tools/scan_source_secrets.py` | 0 finding |

### Quyết định mới

Q25 — mặc định phân quyền app là MỞ; chỉ lưu ngoại lệ; admin luôn thấy hết.

### Cách lùi lại

Xoá `platform_core/app_access.py`, `server/access_middleware.py`,
`tests/test_66_phan_quyen_app.py`, migration `..._them_bang_app_access.py`;
hoàn `platform_core/models.py`, `server/app.py`, `server/routes/dashboard.py`,
`server/templating.py`, `server/templates/base.html`, `tests/test_31...`.

### KHÉP H1 — còn tồn đọng chuyển sang H2/H3

- Chờ khoá người dùng (H1.3): Resend (`RESEND_API_KEY`, `LTT_MAIL_FROM`, 3 DNS)
  và Turnstile (`TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`).
- Nối ở H3: cấp credit dùng thử sau xác thực; trang admin đặt quyền + tạo admin
  trong DB (qua sqladmin) — đó cũng là lúc gỡ đường admin-env (H1.2).

### Việc tiếp theo

1. **H2 — hàng đợi job** (procrastinate trên Postgres, Q13): bảng jobs, worker
   tiến trình riêng, giữ chỗ job, retry, tiến độ.
2. (người dùng, độc lập) H0.1 Cloudflare + các khoá Resend/Turnstile.

---

## 2026-07-31 — H1.3: đăng ký, xác thực email, chống lạm dụng

- **Mục tiêu:** cho tự đăng ký an toàn (Q7) — không để credit dùng thử bị hút
  cạn bằng tài khoản ảo (Q9).
- **Hạng mục:** H1.3 — **xong phần code**; phần cần khoá thật để lại cho người dùng.
- **Trạng thái:** xong (code), có 2 việc chờ khoá của người dùng + 1 việc nối ở H3.

### Đã làm

- `platform_core/mailer.py`: tầng gửi mail tách khỏi nghiệp vụ. `ResendMailer`
  (production, gọi API qua httpx — không thêm SDK) và `ConsoleMailer` (dev/test,
  giữ thư trong RAM để test đọc lại link). Chọn theo biến môi trường. Nhờ tách
  này, toàn bộ luồng đăng ký test được **không cần khoá Resend**.
- `platform_core/tokens.py`: token xác thực email + đặt lại mật khẩu bằng
  `itsdangerous` (đây là chỗ Q24 thay fastapi-users). Ký + hết hạn + mỗi loại
  một salt riêng nên không dùng lẫn được.
- `server/auth/turnstile.py`: xác minh Turnstile phía máy chủ (Q20). Bỏ qua có
  kiểm soát khi chưa cấu hình; lỗi mạng tới Cloudflare thì TỪ CHỐI (an toàn
  mặc định), không cho qua.
- `platform_core/antifraud.py`: chặn tên miền mail dùng-một-lần (danh sách tĩnh,
  không thêm phụ thuộc) + giới hạn số tài khoản/IP/ngày (đếm qua cột
  `registration_ip` mới).
- `server/routes/register.py` + 5 template: đăng ký, xác thực email, quên/đặt
  lại mật khẩu. Đặt lại mật khẩu **thu hồi mọi phiên**.
- Migration thêm cột `registration_ip`.
- `tests/test_65_dang_ky.py` — 8 test.

### Không lộ email nào đã đăng ký — ở ba chỗ

- Đăng ký trùng email → trả trang "đã gửi thư" GIỐNG HỆT lần đầu (không báo
  "email đã tồn tại").
- Quên mật khẩu với email không tồn tại → phản hồi giống hệt email có tồn tại.
- (từ H1.2) xác thực sai không phân biệt email-không-có với sai-mật-khẩu.

### Nghiệm thu

- 8 test trên SQLite.
- **PostgreSQL thật + browser (Playwright):** mở /register → điền form → submit
  → user vào Postgres với `is_verified=False`, `registration_ip=127.0.0.1` →
  bấm link xác thực → trang báo thành công → DB đổi `is_verified=True`. Dọn
  user tạm sau đó. Console chỉ có 1 lỗi favicon 404 (vô hại).

### Lỗi thật phát hiện: migration chỉ-Postgres làm vỡ round-trip SQLite

Migration `registration_ip` dùng `ALTER COLUMN ... DROP DEFAULT` (bỏ default sau
khi backfill hàng cũ). PostgreSQL chạy được (đã nghiệm thu), nhưng SQLite không
hỗ trợ `ALTER COLUMN` → test round-trip trên SQLite vỡ. Bọc bước đó theo
`dialect.name == "postgresql"`: production là Postgres nên vẫn đúng ý định, còn
SQLite (chỉ dùng test bộ máy migration) không cần bỏ default. Test round-trip
SQLite chính là thứ bắt được — nó chạy MỌI migration nên tự bảo vệ chống lỗi
này tái diễn.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.470 passed**, 1 skipped, 23 subtests |
| `tests/test_65_dang_ky.py` | 8 passed |
| Round-trip migration trên SQLite + PostgreSQL thật | sạch cả hai |
| Nghiệm thu đăng ký→xác thực trên PostgreSQL + browser | thành công |
| `python tools/scan_source_secrets.py` | 0 finding |

### Còn chờ người dùng (code đã sẵn sàng)

1. Resend: đặt `RESEND_API_KEY` + `LTT_MAIL_FROM` + 3 bản ghi DNS (Q19) → thư
   xác thực tới hộp thư thật (giờ đang ghi vào log qua ConsoleMailer).
2. Turnstile: đặt `TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET_KEY` (Q20) → form
   đăng ký có ô chống bot thật.

### Nối ở H3

- Cấp credit dùng thử sau xác thực: `/verify-email` đã có đúng chỗ nối (ghi chú
  trong code), chờ bảng credit ở H3.

### Cách lùi lại

Xoá `platform_core/{mailer,tokens,antifraud}.py`, `server/auth/turnstile.py`,
`server/routes/register.py`, 5 template mới, `tests/test_65_dang_ky.py`,
migration `..._them_cot_registration_ip.py`; hoàn `platform_core/models.py`,
`platform_core/users.py`, `server/app.py`, `server/templates/{login,base_plain}.html`.

### Việc tiếp theo

1. H1.4 — phân quyền app cho từng người dùng (mở/khoá/ẩn), chặn ở tầng route.
2. (người dùng, độc lập) H0.1 Cloudflare, và các khoá Resend/Turnstile ở trên.

---

## 2026-07-31 — H1.2: người dùng, phiên đăng nhập phía máy chủ

- **Mục tiêu:** hệ thống biết "ai đang dùng"; dữ liệu người này người kia tách nhau.
- **Hạng mục:** H1.2 — **hoàn thành**.
- **Trạng thái:** xong (bước "gỡ đường admin-env" dời sang H3 — có lý do bên dưới).

### Quyết định đổi hướng: bỏ fastapi-users (Q14 → Q24)

Khi bắt tay H1.2 mới thấy `fastapi-users` (DB adapter) **bắt buộc
`sqlalchemy[asyncio]`** — async-only từ v10. Nền H1.1 vừa xây là đồng bộ, và
phần auth đang chạy production cũng đồng bộ. Đưa nó vào sẽ kéo async engine vào
codebase đồng bộ, **thay luôn cơ chế session đang chạy production**, mà vẫn phải
tự viết trang HTML. Lợi ích chính (logic token xác thực email) thì `itsdangerous`
đã có sẵn làm được.

Lúc chốt Q14 tôi chưa nhìn code thật. Đưa lựa chọn cho chủ dự án, chọn Q24: tự
viết trên nền đồng bộ. Đã dọn Q14 theo đúng giao thức (đánh dấu ĐÃ THAY, thêm
Q24, truy mọi nơi nhắc fastapi-users và sửa).

### Đã làm

- `platform_core/models.py`: bảng `users` (khoá chính UUID — không lộ quy mô,
  không đoán được id người khác; email chuẩn hoá chữ thường; `is_verified` tách
  khỏi `is_active`) và `sessions` (phiên phía máy chủ).
- `platform_core/users.py`: nghiệp vụ tách khỏi HTTP — tạo user, xác thực,
  tạo/thu hồi phiên, đổi mật khẩu. Băm mật khẩu **tái dùng** PBKDF2 của
  `server/auth/password_hashing.py`, không phát minh cách băm thứ hai.
- `server/deps.py`: `get_db` (bắt buộc, commit-khi-xong) và `mo_db_optional`
  (trả None khi CSDL chưa cấu hình — để đường admin-env vẫn chạy khi không có DB).
- `server/auth/session.py`: hai đường song song — admin-env (cookie, không chạm
  DB, đường lui) và user CSDL (cookie mang `sid` trỏ bảng sessions). Đường CSDL
  thất bại im lặng khi chưa có DB. `require_login` giữ nguyên chữ ký nên không
  route nào phải đổi.
- `server/routes/auth.py`: login thử user CSDL trước, admin-env sau.

### Ba tính chất bảo mật, có test

- **Mật khẩu không lưu thô** — chỉ hash PBKDF2.
- **Xác thực sai không tiết lộ email nào đã đăng ký** — email-không-tồn-tại và
  sai-mật-khẩu đều trả None, và vẫn băm-rồi-so với hash giả để thời gian phản
  hồi không làm timing oracle.
- **Phiên thu hồi được** — đăng xuất xoá dòng ở DB; đổi mật khẩu đá mọi phiên.
  Đây là điểm khác biệt cốt lõi so với cookie ký thuần (không có id để thu hồi).

### Điều chỉnh có lý do — CHƯA gỡ đường admin-env

Kế hoạch gốc ghi "đường mới xanh thì gỡ session.py cũ". Nhưng gỡ admin-env bây
giờ là sai: chưa có cách tạo admin **trong CSDL** (trang quản trị tới H3 mới có
qua sqladmin). Gỡ trước = một CSDL trống thì không ai đăng nhập được. Giữ
admin-env làm đường lui chính thức tới H3.

### Hai lỗi thật phát hiện trong lúc làm

1. **So sánh datetime naive vs aware.** SQLite không giữ tzinfo nên `expires_at`
   đọc ra là naive, so với thời gian aware thì ném TypeError. PostgreSQL không
   bị, nhưng code nên chịu được cả hai backend (test SQLite, production Postgres).
   Thêm `_aware()` chuẩn hoá tại điểm so sánh.
2. **Ký tự điều khiển tái diễn trong chính nhật ký H1.1** — đoạn văn mô tả lỗi
   `\b`/`\a` lại chứa đúng ký tự đó (heredoc nuốt escape). Lần thứ hai trong một
   phiên. `test_61` bắt được. Đã sửa và ghi lại như bằng chứng nó âm thầm cỡ nào.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.462 passed**, 1 skipped, 23 subtests, 256s |
| `tests/test_64_nguoi_dung.py` (SQLite) | 18 passed |
| Nghiệm thu đăng nhập trên **PostgreSQL thật** | 303→200→303, phiên bị thu hồi (0 dòng còn lại), user tạm đã dọn |
| `python tools/scan_source_secrets.py` | 0 finding |

### Cách lùi lại

Xoá `platform_core/users.py`, `server/deps.py`,
`tests/test_64_nguoi_dung.py`, migration `..._them_bang_users_va_sessions.py`;
hoàn `platform_core/models.py`, `server/auth/session.py`,
`server/routes/auth.py` về commit trước.

### Việc tiếp theo

1. H1.3 — đăng ký + xác thực email (Resend) + Turnstile chống lạm dụng. Đây là
   phần bắt buộc trước khi cho tự đăng ký (Q7): không có nó, credit dùng thử bị
   hút cạn bằng tài khoản ảo.
2. (người dùng, độc lập) H0.1 — kiểm tra Cloudflare zone subdomain.

---

## 2026-07-31 — H1.1 đóng: nghiệm thu trên PostgreSQL thật

- **Mục tiêu:** đóng nốt H1.1 sau khi có PostgreSQL.
- **Hạng mục:** H1.1 — **hoàn thành**.
- **Trạng thái:** xong.

### Đã làm

Người dùng cài PostgreSQL 17 qua winget và uỷ quyền tôi tự tạo + lưu mật khẩu
(sẽ đổi sau khi hoàn tất). Trình cài winget đặt mật khẩu superuser mặc định là
`postgres` — yếu, nên việc đầu tiên là thay.

- Đổi mật khẩu `postgres` → mật khẩu ngẫu nhiên 28 ký tự, lưu
  `secrets/postgres-superuser.txt` (đã gitignore, đọc bằng `utf-8-sig`).
- Tạo role `ltt_app` + database `lttplatform` (Q23 — ứng dụng không dùng
  superuser). Ghi `LTT_DATABASE_URL` vào `secrets/app.env`.
- `alembic upgrade head` chạy trên **PostgreSQL thật** — không còn là SQLite
  tạm. Bảng `platform_info` + `alembic_version` đúng, phiên bản
  `0001_platform_info`.
- `/health/ready` → `{"status":"ready","database":"ok"}` với CSDL thật.

### Nghiệm thu khôi phục thật — mảnh quan trọng nhất

Một bản sao lưu chưa từng thử khôi phục thì chưa phải bản sao lưu. Đã chạy đủ
chu trình bằng chính công cụ mà `backup.ps1` dùng:

1. ghi một dòng nhận biết được vào `lttplatform`;
2. `pg_dump -Fc` ra file (3.952 bytes);
3. tạo database mới `lttplatform_restore_test`, `pg_restore` vào đó;
4. đọc lại dòng vừa ghi từ database khôi phục → **KHỚP**;
5. dọn sạch: xoá database test, file dump, dòng nhận biết.

### Cách kiểm chứng mật khẩu

Toàn bộ thiết lập chạy bằng script Python (tránh bẫy quoting của PowerShell),
mật khẩu **không bao giờ đi qua khung chat**: sinh bằng `secrets`, ghi thẳng
vào `secrets/`, và chỉ in ra URL đã che mật khẩu để đối chiếu.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `alembic upgrade head` trên Postgres thật | thành công, bảng đúng |
| `/health/ready` với CSDL thật | 200, `database: ok` |
| Chu trình `pg_dump` → `pg_restore` → đọc lại | KHỚP |
| `git check-ignore secrets/app.env, postgres-superuser.txt` | cả hai IGNORED |

Bộ test đầy đủ đã 1.450 pass ở lần chạy trước đó (không đổi code kể từ đó).

### Còn tồn đọng

- Mật khẩu CSDL hiện do tôi tạo trong quá trình xây; **đổi lại khi hoàn tất**
  (người dùng đã dặn).
- Trên máy chủ thật, bộ cài `setup/2-cai-dat.ps1` sẽ tự làm lại đúng chuỗi này
  — nhưng chuỗi đó **chưa chạy trên một máy chủ thật**, mới chạy tương đương
  bằng tay trên máy phát triển này.

### Việc tiếp theo

1. H1.2 — bảng người dùng + `fastapi-users` dựng **song song** với auth hiện
   có, chỉ gỡ cũ khi phần mới đã xanh.
2. (người dùng, độc lập) H0.1 — kiểm tra Cloudflare cho tạo zone subdomain.

---

## 2026-07-31 — H1.1: lớp CSDL PostgreSQL + Alembic

- **Mục tiêu:** dựng lớp CSDL và bộ máy di trú lược đồ.
- **Hạng mục:** H1.1 — **dở, bị chặn**.
- **Trạng thái:** phần code xong và đã kiểm chứng; phần cần quyền
  Administrator chưa làm được.

### Đã làm

**1. `platform_core/db.py`** — engine dùng chung, session factory, và
`che_mat_khau()` áp cho **mọi** đường lỗi. Lý do tồn tại của hàm che: thông báo
lỗi của driver PostgreSQL thường nhúng nguyên chuỗi kết nối, `/health/ready`
thì cố ý không yêu cầu đăng nhập (để reverse proxy thăm dò được), và người ta
hay dán nguyên thông báo lỗi vào chat để hỏi. Ba điều đó cộng lại là một đường
rò rất thật.

**2. Alembic** — `alembic.ini` **cố ý không có dòng `sqlalchemy.url`** (file đó
nằm trong git); `env.py` đọc từ `LTT_DATABASE_URL`. Migration đầu tiên tạo bảng
`platform_info`.

*Lệch so với kế hoạch, có chủ ý:* kế hoạch ghi "migration đầu tiên tạo bảng
rỗng". Một migration không tạo gì thì **không kiểm chứng được** — vòng
`upgrade` → `downgrade` → `upgrade` không chứng minh được điều gì. Đổi thành
một bảng nhỏ có thật (ghi lược đồ này dựng khi nào, bởi bản nào), vừa hữu ích
khi hỗ trợ vừa làm việc kiểm chứng có nghĩa.

**3. `/health/ready` kiểm tra CSDL bằng `SELECT 1` thật**, không phải kiểm tra
"đã cấu hình chuỗi kết nối chưa". Một CSDL đã cấu hình nhưng không với tới được
chính là trạng thái khiến ứng dụng trông khoẻ mạnh trong khi mọi request đều
hỏng.

Tạm thời **chưa cấu hình CSDL chưa bị coi là lỗi** — chưa phần nào của ứng dụng
phụ thuộc vào nó, và bắt trả 503 ngay bây giờ sẽ làm trình quản lý dịch vụ khởi
động lại liên tục vì một phụ thuộc chưa ai dùng tới. **Phải đổi cùng lúc với
H1.2**, test đã ghi rõ điều đó.

**4. Bộ cài và sao lưu** — `setup/2-cai-dat.ps1` cài PostgreSQL, tạo role +
database riêng, ghi `LTT_DATABASE_URL`, rồi chạy `alembic upgrade head`
**trước** khi khởi động dịch vụ. `backup.ps1` thêm `pg_dump`.

### Hai lỗi thật phát hiện trong lúc làm

**Lỗi 1 — kết nối treo 130 giây.** Một test nối tới cổng chết mất 130 giây mới
bỏ cuộc. Đây không phải lỗi của test mà là lỗi của lớp CSDL: trên production,
một lần kết nối treo sẽ **giữ luôn worker phục vụ request** hai phút. Người
dùng chỉ thấy trang treo, và trình quản lý dịch vụ không thấy gì bất thường để
khởi động lại. Đã đặt `CONNECT_TIMEOUT_S = 5` → còn 5,16 giây, có test chốt
ngưỡng.

**Lỗi 2 — ký tự điều khiển vô hình lọt vào script (lỗi của tôi).** Khi chèn
đoạn PowerShell bằng chuỗi Python không phải raw-string, đường dẫn kết thúc
bằng "backslash-b-i-n" bị biến thành ký tự chr(8) rồi "in", và
"backslash-a-p-p" thành chr(7) rồi "pp". Năm chỗ, hai file. (Đúng lỗi này còn
tái diễn ngay trong chính đoạn nhật ký mô tả nó — lần thứ hai trong một phiên,
đủ để thấy nó âm thầm cỡ nào.)

Hậu quả nếu lọt qua:
- bộ cài không tìm thấy PostgreSQL rồi báo "cài thất bại" — **sai nguyên nhân**;
- `backup.ps1` không thấy `app.env` nên **âm thầm bỏ qua CSDL**, cho ra một bản
  sao lưu trông y hệt bản đầy đủ và chỉ lộ ra đúng lúc cần khôi phục.

Đáng chú ý: kiểm tra ASCII sẵn có **không** bắt được (các ký tự này < 128), và
kiểm tra cú pháp PowerShell cũng không (chúng nằm trong chuỗi). Dự án đã có
test ký tự điều khiển cho **tài liệu** từ một lần vấp trước, nhưng không có cho
**script** — mà script mới là chỗ nguy hiểm hơn vì không ai đọc bằng mắt. Đã bổ
sung vào `test_62_khoa_logic.py`.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | **1.450 passed**, 1 skipped, 23 subtests, 277s |
| `python -m pytest tests/test_63_lop_csdl.py -q` | 17 passed |
| Vòng di trú thật `upgrade` → `downgrade` → `upgrade` | sạch cả ba lần (SQLite tạm) |
| Kiểm tra cú pháp + ASCII + BOM cho 2 script `.ps1` | OK |
| `python tools/scan_source_secrets.py` | **0 finding** |

1.422 → 1.450 = +28 test (17 ở `test_63`, 11 ở `test_62` gồm 5 ca kiểm ký tự
điều khiển cho script).

### Quyết định mới

Q23 — ứng dụng dùng role `ltt_app`, **không bao giờ** dùng superuser
`postgres`. Lý do và cái giá ghi ở `QUYET_DINH_NEN_TANG.md`.

### Cách lùi lại

Xoá `platform_core/db.py`, `platform_core/models.py`, `alembic.ini`,
`alembic/`, `tests/test_63_lop_csdl.py`; hoàn `server/routes/health.py`,
`requirements-server.txt`, `setup/2-cai-dat.ps1`, `deploy/windows/backup.ps1`
về commit trước.

### Bị chặn — cần người dùng

**PostgreSQL chưa cài được: không có quyền Administrator.**
Cài PostgreSQL dạng dịch vụ Windows cần quyền đó, và tôi không tự nâng quyền
được (UAC là hộp thoại tương tác).

Hệ quả: ba việc chưa kiểm chứng được trên PostgreSQL thật —
1. migration chạy trên Postgres (mới chỉ chứng minh trên SQLite tạm);
2. bộ cài tạo được role/database;
3. **khôi phục thật** từ file `pg_dump`.

Việc thứ 3 quan trọng nhất: một bản sao lưu chưa từng được khôi phục thử thì
chưa phải là bản sao lưu.

### Việc tiếp theo

1. **Người dùng:** cài PostgreSQL (xem lựa chọn tôi đưa ra cuối phiên).
2. Sau khi có PostgreSQL: chạy migration thật + thử khôi phục `pg_dump` →
   đóng nốt H1.1.
3. H1.2 — bảng người dùng + đăng nhập, dựng `fastapi-users` **song song** với
   phần auth hiện có, chỉ gỡ cũ khi phần mới đã xanh.

---

## 2026-07-31 — H0: dọn nền, đưa vào git, chuẩn hoá tài liệu

- **Mục tiêu:** dọn sạch nền trước khi xây hạ tầng nhiều người dùng; chuẩn hoá
  tài liệu; chốt hướng đi thành một nguồn chân lý duy nhất.
- **Hạng mục:** H0 — hoàn thành.
- **Trạng thái:** xong.

### Đã làm

**1. Lần đầu đưa dự án vào git.** Trước đó ~45.000 dòng không hề có version
control, trong khi đã có một bản production đang chạy. Đây là rủi ro vận hành
lớn nhất, lớn hơn mọi lỗi kỹ thuật tìm được, vì nó làm mọi lỗi khác khó sửa và
không lùi được. Commit gốc: `44f36d6`.

**2. Vá lỗi ranh giới đường dẫn (nghiêm trọng).**
`TokenStore`, `content_history.db`, `page_health.db`, `audit_log.jsonl` và các
cache đều dùng `os.path.join("data", ...)` — tương đối theo **thư mục làm
việc**, không theo `LTT_DATA_DIR`. Trên máy chủ, dịch vụ chạy tại
`C:\LTTPlatform\app` nên chúng rơi vào `app\data\` — đúng thư mục bị chuyển
sang `app.previous` rồi tạo mới ở **mỗi lần cập nhật**.

Hậu quả nếu không sửa: token Facebook/TikTok biến mất sau lần cập nhật kế tiếp,
và biến mất **âm thầm** — `_save()` có `os.makedirs(exist_ok=True)` nên nó tạo
thư mục rồi ghi bình thường, không báo lỗi gì.

Kiểm chứng: đặt `LTT_DATA_DIR=C:/LTTPlatform/data` rồi đổi CWD sang `C:\Users`
- trước: `C:\Users\data\tokens.enc`
- sau: `C:\LTTPlatform\data\tokens.enc`

Lỗi này từng được phát hiện và sửa cho `core/session_lock.py` nhưng chỉ sửa
đúng một module. Nay gom về một chỗ: `core.runtime_paths.data_path()`.

**3. Ba lỗi phụ lộ ra trong lúc sửa lỗi trên** — không cái nào từng có ai thấy:

- `tests/conftest.py` gán đè `_DEFAULT_DB_PATH` để cách ly test khỏi CSDL thật,
  nhưng vì đó là **giá trị mặc định của tham số** (gán một lần lúc import) nên
  việc gán đè không bao giờ có tác dụng — bộ test vẫn ghi vào CSDL thật.
- `core/i18n.py` đọc bản dịch cạnh **mã nguồn**, trong khi bộ cài cố ý chép bản
  dịch vào thư mục **dữ liệu**. Trên máy chủ không nạp được bản dịch nào, và
  `t()` lặng lẽ rơi về tiếng Anh rồi về chính khoá.
- `audit_checklist` tìm logo TikTok theo đường dẫn tương đối, nên người dùng
  tải logo về đúng chỗ tài liệu chỉ mà cảnh báo vẫn không bao giờ tắt.

**4. Chốt cận trên phiên bản thư viện.** `pip install` kéo về Starlette 1.3
(bản major mới) làm việc liệt kê route không còn hoạt động. Ứng dụng vẫn chạy
đúng, nhưng **hai lần cài cùng một mã nguồn cho ra hai môi trường khác nhau**.
Đã thêm `<` cho mọi thư viện (Q17).

**5. Đổi cổng mặc định 8000 → 8100** (Q4). Máy này còn chạy `D:\BOT GEMINI`
trên cổng 8000, phục vụ 13 người dùng thật — bộ cài cũ sẽ giành cổng với nó.

**6. Chuẩn hoá tài liệu.** 19 file cũ chuyển vào `docs/_luutru/` kèm README
giải thích từng file là gì và vì sao ngừng dùng. Viết lại `AGENTS.md`,
`CLAUDE.md`, `docs/00`. Thêm `QUYET_DINH_NEN_TANG.md` (nguồn chân lý),
`KE_HOACH_TRIEN_KHAI.md`, `KHAO_SAT_BOT_GEMINI.md`, và file này.

Trước đó có **bốn hệ đánh số kế hoạch song song** (P0–P11, PA–PE, W1–W6, 00–04)
và không hệ nào tuyên bố mình đã bị thay thế. Từ nay chỉ còn một hệ: `H`.

**7. Bộ khoá logic** `tests/test_62_khoa_logic.py` (11 test): biến các ràng
buộc bất biến thành test, để lần sau ai vi phạm là biết ngay chứ không phải nhớ
đã đọc ở đâu. Khoá: đường dẫn dữ liệu, không import chéo sang BOT GEMINI, cổng
8100, cận trên phiên bản, ba tầng tài liệu, một hệ đánh số, quyết định không
trùng số.

### Test đã chạy

| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` (mốc chuẩn đầu phiên) | 1.424 passed, 1 skipped |
| `python -m pytest -q` (cuối phiên) | **1.422 passed**, 1 skipped, 23 subtests, 238s |
| `python -m pytest tests/test_62_khoa_logic.py -q` | 11 passed |
| `python tools/scan_source_secrets.py` | **0 finding**, PASS |
| Kiểm chứng đường dẫn với `LTT_DATA_DIR` + đổi CWD | đúng như mong đợi |

**Vì sao tổng số test giảm 1424 → 1423 mà không mất test nào:**
`test_61::test_doc_has_no_invisible_control_characters` được sinh theo **số file
`.md` trong `docs/`**. Chuyển 12 file sang `_luutru/` → giảm 12 ca; thêm 11 ca
mới ở `test_62` → tổng giảm đúng 1. Đã kiểm chứng bằng cách đếm lại, không phải
suy đoán. Hệ quả chấp nhận được: tài liệu trong `_luutru/` không còn được quét
ký tự điều khiển nữa — chúng đã đóng băng, không ai đọc.

### Quyết định mới ghi trong phiên này

Q13 procrastinate · Q14 fastapi-users · Q15 sqladmin · Q16 SQLAlchemy+Alembic ·
Q17 chốt cận trên phiên bản · Q18 HTMX · Q19 Resend · Q20 Cloudflare Turnstile ·
Q21 Sentry · Q22 uỷ quyền subdomain `app` (có điều kiện chưa xác minh).
Chi tiết và lý do ở `QUYET_DINH_NEN_TANG.md`.

Tổng chi phí dịch vụ ngoài khi bắt đầu: **0 đồng/tháng** (đều dùng gói miễn phí).

### Hai test đã sửa — và vì sao không phải là làm yếu test đi

- `test_51_oauth_web.py::test_callback_paths_match_the_routes` đổi từ soi nội
  bộ router sang **thăm dò bằng HTTP**. Cách cũ vỡ khi nâng thư viện; cách mới
  chứng minh được đường dẫn **thực sự gọi tới được** — đúng thứ mà callback URL
  khai ở Meta/TikTok Portal cần.
- `test_45_deploy_scripts.py` đổi từ khoá cứng `127.0.0.1:8000` sang khoá bất
  biến "chỉ được proxy địa chỉ loopback". Khoá con số làm một lần đổi cổng hợp
  lệ trông giống lỗi bảo mật.

### Đo được về hạ tầng mạng — và một quyết định bị chặn

`nslookup` cho thấy `lttstudios.com` đang dùng nameserver của inet.vn
(`hoian/danang.vclouddns.com`), **không phải Cloudflare**. Cloudflare Tunnel
cần một CNAME trỏ tới `<tunnel-id>.cfargotunnel.com`, mà tên miền đó chỉ phân
giải được qua chính hệ thống Cloudflare — nên `setup/3-cloudflare.ps1` sẽ hỏng
ở khâu gần cuối, sau khi đã tải cloudflared, đăng nhập và tạo tunnel.

Chủ dự án chọn hướng **uỷ quyền riêng subdomain `app`** (Q22) để không đụng vào
trang giới thiệu đang chạy. Hướng này phụ thuộc một điều **tôi không xác minh
được từ đây**: gói miễn phí của Cloudflare có cho tạo zone cấp subdomain không.
Đã ghi rõ điều kiện đó ngay trong Q22 và tách thành hạng mục **H0.1** đứng
trước mọi việc khác, kèm hai đường lui nếu câu trả lời là không.

Cũng đo được: tên miền **không có bản ghi MX hay TXT nào** → thêm SPF/DKIM cho
Resend sẽ sạch, không đụng gì đang chạy.

### Còn tồn đọng

- Chưa dựng Cloudflare Tunnel trên máy này.
- `app.lttstudios.com` hiện vẫn trỏ vào máy chủ cũ chạy Caddy trực tiếp (đo
  được: `45.32.104.192`, không qua Cloudflare). Khi chuyển sang Tunnel phải
  quyết định số phận máy đó.
- Bộ test có gọi mạng thật ra `api.telegram.org` (in ra `[Telegram] HTTP 401`).
  Không chặn gì, nhưng test không nên phụ thuộc mạng.

### Việc tiếp theo

1. **Người dùng — H0.1:** kiểm tra trên bảng điều khiển Cloudflare xem gói miễn
   phí có cho tạo zone cấp subdomain `app.lttstudios.com` không. **Chưa biết kết
   quả thì chưa chạy `setup/3-cloudflare.ps1`.**
2. H1.1 — dựng PostgreSQL + SQLAlchemy + Alembic, migration đầu tiên. Không phụ
   thuộc việc 1, làm song song được.
3. Bổ sung cài Postgres vào `setup/2-cai-dat.ps1` và `pg_dump` vào `backup.ps1`
   **trong cùng lần đó**.

---

## Mẫu ghi — chép nguyên phần này lên đầu file cho mỗi phiên

```markdown
## YYYY-MM-DD — <tiêu đề ngắn>

- **Mục tiêu:**
- **Hạng mục:** H<x> — <đang làm / hoàn thành>
- **Trạng thái:** xong | dở | bị chặn

### Đã làm
<Cái gì và VÌ SAO. Nếu sửa lỗi, ghi lỗi đó gây hậu quả gì nếu không sửa.>

### Test đã chạy
| Lệnh | Kết quả |
|---|---|
| `python -m pytest -q` | ... |
| `python tools/scan_source_secrets.py` | ... |

<Phân biệt rõ: đã chạy / chưa chạy / pass / fail. Không bao giờ ghi "xong"
dựa trên kế hoạch hay số test thu thập được.>

### Quyết định mới
<Nếu có: số Q, và đã thêm vào QUYET_DINH_NEN_TANG.md chưa.
Nếu ĐỔI một quyết định cũ: đã đánh dấu ĐÃ THAY và dọn hết chỗ nói theo cái cũ
chưa — xem giao thức ở AGENTS.md mục 6.>

### Cách lùi lại
<Commit nào, hoặc xoá file nào.>

### Còn tồn đọng

### Việc tiếp theo
1.
2.
3.
```
