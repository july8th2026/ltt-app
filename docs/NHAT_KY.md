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
