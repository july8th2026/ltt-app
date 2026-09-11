# Kế hoạch triển khai

> Lập 2026-07-31. Đây là **kế hoạch** — nó ghi *ý định*.
> `NHAT_KY.md` ghi *sự thật đã xảy ra*. Khi hai file mâu thuẫn, nhật ký đúng,
> và phải sửa lại kế hoạch cho khớp thực tế.
>
> Quyết định nền: `QUYET_DINH_NEN_TANG.md`. Quy tắc làm việc: `AGENTS.md`.

---

## Cách đọc file này

- **Một hệ đánh số duy nhất: `H0`, `H1`, …** Trước đây dự án có bốn hệ song
  song (P0–P11, PA–PE, W1–W6) và không hệ nào tuyên bố mình đã bị thay thế —
  đó là nguyên nhân chính gây rối. Từ nay chỉ có `H`.
- Mỗi hạng mục có **tiêu chí hoàn thành**. Chưa đạt đủ thì chưa được đánh `[x]`,
  kể cả khi code đã viết xong.
- Ô `[ ]` → chưa làm. `[x]` → xong **và đã chạy test thật**, có ghi ngày.

---

## Bản đồ tổng

```
H0    Dọn nền                      ✅ 2026-07-31
H0.1  Đưa lên mạng qua Cloudflare   ✅ 2026-07-31 (app.lttstudios.com sống)
     │
H1  Người dùng + PostgreSQL   ─┐
H2  Hàng đợi job              ─┼─►  H4  Nghiệm thu bằng apps/demo   ✅
H3  Sổ credit                 ─┘         │
                                         ▼
                              H5  Tool thật đầu tiên (thumbnail)    ✅
                                         │
                              H6  Cốt lõi vận hành nền tảng          ✅
                                  (catalog công khai + SSO UX + login return-to)
                                         │
                              H7  Củng cố MVP (Hardening)  ✅ (Wave 0+1+2)
                                         │
                       ┌─────────────────┼─────────────────┐
                       ▼                 ▼                 ▼
              H8 APIKEYS (quản trị nguồn API)  ✅ Pha 1 ◄─ kế tiếp: Pha 2
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
  H9 Thanh toán   H10 File lớn (R2)   H11 Thêm tool
```

> **Chèn H6 (2026-07-31):** cốt lõi vận hành (catalog + đăng nhập một-lần cho mọi
> app) là điều kiện để KHÁCH thật dùng được nền tảng, nên đứng TRƯỚC thanh toán.
>
> **Chèn H7 (2026-07-31):** audit toàn diện (`docs/AUDIT_MVP_2026-07-31.md`) tìm ra
> các lỗ hổng P0 tiền/bảo mật/khôi phục → **Củng cố MVP** phải xong TRƯỚC khi mở
> khách trả tiền. Dời tiếp: Thanh toán→**H9**, R2→**H10**, Thêm tool→**H11**.

H1 → H2 → H3 làm theo thứ tự (job cần chủ sở hữu; credit cần job). Cả ba phải
xong mới nghiệm thu được ở H4.

---

## H0 — Dọn nền ✅ XONG 2026-07-31

**Mục tiêu:** không xây gì lên trên một cái nền có lỗi âm thầm.

- [x] `git init` + commit mốc chuẩn — trước đó ~45.000 dòng không hề có version
      control, trong khi đã có một bản production đang chạy
- [x] Cài `requirements-server.txt` (thiếu `itsdangerous` làm 7 module test
      không nạp được → `pytest` đỏ ngay từ khâu thu thập)
- [x] Chốt cận trên phiên bản cho mọi thư viện (Q17)
- [x] Sửa ranh giới đường dẫn: token store, các CSDL, nhật ký kiểm toán, cache,
      bản dịch, logo audit — tất cả đi qua `core.runtime_paths.data_path()`
- [x] Đổi cổng mặc định 8000 → 8100 ở `setup/`, `deploy/`, `cloudflare/`,
      `server/run.py`, tài liệu (Q4)
- [x] Dọn 19 tài liệu cũ vào `docs/_luutru/` kèm README giải thích (Q8)
- [x] Viết lại `AGENTS.md`, `CLAUDE.md`, `docs/00`, và bộ tài liệu gốc
- [x] Bộ khoá logic `tests/test_62_khoa_logic.py`

**Kết quả test:** `python -m pytest -q` → **1.422 pass, 1 skip, 23 subtests**
(238s) · `python tools/scan_source_secrets.py` → **0 finding**
· `tests/test_62_khoa_logic.py` → 11 pass

Chi tiết và lý do tổng số test đổi từ 1.424 → 1.423: xem `NHAT_KY.md`.

---

## H0.1 — Đưa lên mạng qua Cloudflare (Q27) ✅ XONG 2026-07-31

**Mục tiêu:** `https://app.lttstudios.com` chạy thật qua Cloudflare Tunnel, giữ
trang chủ `lttstudios.com` ở inet.vn OnePanel.

**Đã hoàn tất + nghiệm thu thật (xem NHAT_KY):** thêm zone (Free), dọn DNS (@ +
www → 103.57.220.210 DNS-only, đã kiểm origin phục vụ trang chủ trực tiếp), đổi
NS sang Cloudflare, zone Active. Cài `setup/2` (app :8100), backup Q28 sang
`D:\LTTBackups`. Dựng Tunnel: PHẢI sửa `setup/3` — `cloudflared service install`
2026.x tạo dịch vụ ImagePath trần (không kết nối) → cài lại **qua NSSM**
(`--config ... tunnel run`). Tunnel ổn định (8/8 curl 200 + active connection).
Đăng nhập admin → control plane OK. `setup/4` nghiệm thu ĐẠT. Đặt mật khẩu admin.

**Nợ để lại (cleanup, không chặn):** control plane còn branding socialbot cũ
("đăng bài Facebook & TikTok") + socialbot route ở đường gốc; lỗi console
Cloudflare Insights beacon (CSP chặn — nên tắt auto-inject); favicon 404.

**Quy trình đầy đủ (chia rõ việc bạn/tôi): `docs/05_LEN_MANG_CLOUDFLARE.md`.**

### Đã chốt (thay cho hướng subdomain ban đầu)

Điều kiện chưa xác minh của Q22 giờ **đã xác minh**: tạo subdomain thành zone
riêng là **Enterprise-only** (tài liệu chính thức Cloudflare). Nên đổi sang Q27:
**chuyển cả zone `lttstudios.com` sang Cloudflare**, để `@`/`www` ở "DNS only"
(giữ inet.vn phục vụ trang chủ), chỉ `app` "Proxied" + Tunnel. Free đủ.

### Các bước (chi tiết ở `docs/05`)

- [x] 🧑 Add site `lttstudios.com` vào Cloudflare (Free), kiểm đủ bản ghi, `@`/
      `www` để DNS-only; 🤖 rà danh sách trước khi đổi NS
- [x] 🧑 Đổi nameserver ở nhà đăng ký tên miền sang 2 NS Cloudflare
- [x] ⏳ Đợi zone Active; 🤖 kiểm NS + trang chủ vẫn sống
- [x] 🧑 Cài `C:\LTTPlatform` (`setup/2`, Administrator); 🤖 nghiệm thu cục bộ
- [x] 🧑 Chạy `setup/3-cloudflare.ps1` (sửa dùng NSSM), đăng nhập chọn zone `lttstudios.com`
- [x] 🤖 Nghiệm thu `https://app.lttstudios.com` từ mạng ngoài + browser

**Tiêu chí hoàn thành:** `https://app.lttstudios.com/health/ready` trả
`{"status":"ready","environment":"production"}` từ **mạng ngoài** (không phải
trong LAN — hairpin NAT cho dương tính giả), và `https://lttstudios.com` (trang
chủ) vẫn chạy như cũ.

---

## H1 — Người dùng + PostgreSQL

**Mục tiêu:** hệ thống biết "ai đang dùng", và dữ liệu của người này người kia
không thấy được.

### H1.1 — Dựng PostgreSQL và lớp CSDL ✅ XONG 2026-07-31

**Phần code: xong và đã kiểm chứng.**

- [x] Thêm `sqlalchemy`, `alembic`, `psycopg[binary]` vào
      `requirements-server.txt` **kèm cận trên** (Q17) — 2026-07-31
- [x] `platform_core/db.py`: engine + session factory, đọc chuỗi kết nối từ
      `LTT_DATABASE_URL`, **che mật khẩu ở mọi đường lỗi**
- [x] `platform_core/models.py` + Alembic + migration đầu tiên
      (`0001_platform_info`)
- [x] `/health/ready` kiểm tra CSDL bằng `SELECT 1` thật và báo rõ lý do
- [x] Bổ sung bước cài PostgreSQL + tạo role/database + chạy migration vào
      `setup/2-cai-dat.ps1`
- [x] Bổ sung `pg_dump` vào `deploy/windows/backup.ps1`
- [x] `tests/test_63_lop_csdl.py` — 17 test

**Phần cần PostgreSQL thật: đã xong 2026-07-31** (người dùng cài PostgreSQL 17,
uỷ quyền tôi tự tạo và lưu mật khẩu).

- [x] PostgreSQL 17 chạy trên cổng 5432
- [x] Đổi mật khẩu superuser mặc định `postgres` → mật khẩu ngẫu nhiên, lưu
      `secrets/postgres-superuser.txt`
- [x] Tạo role `ltt_app` + database `lttplatform`, ghi `LTT_DATABASE_URL` vào
      `secrets/app.env`
- [x] `alembic upgrade head` chạy trên **PostgreSQL thật** — bảng `platform_info`
      + `alembic_version` đúng
- [x] `/health/ready` trả `{"status":"ready","database":"ok"}` với CSDL thật
- [x] **Khôi phục thật** đã nghiệm thu: ghi dòng nhận biết → `pg_dump -Fc` →
      `pg_restore` sang database khác → đọc lại KHỚP → dọn sạch

**Tiêu chí hoàn thành**
- [x] `alembic upgrade head` chạy sạch trên một CSDL trống
- [x] `alembic downgrade -1` rồi `upgrade` lại vẫn sạch
- [x] `/health/ready` báo lý do khi CSDL không kết nối được
- [x] Mật khẩu không lọt vào thông báo lỗi (có test cho đường lỗi thật)
- [x] `backup.ps1`/`pg_dump` tạo ra bản **khôi phục lại được** (nghiệm thu thật)

**Rủi ro đã xử lý:** mật khẩu CSDL lọt vào log hoặc thông báo lỗi →
`che_mat_khau()` áp cho mọi đường ra, có test chạy đường lỗi thật (nối tới cổng
chết) và khẳng định mật khẩu không xuất hiện.

**Một lỗi thật phát hiện trong lúc làm:** kết nối tới địa chỉ chết mất **130
giây** mới bỏ cuộc — trên production nghĩa là một worker phục vụ request nằm im
hai phút, người dùng chỉ thấy trang treo, và trình quản lý dịch vụ không thấy
gì bất thường để khởi động lại. Đã đặt `CONNECT_TIMEOUT_S = 5`, còn 5 giây, có
test chốt.

### H1.2 — Bảng người dùng và đăng nhập ✅ XONG 2026-07-31

- [x] Bảng `users`: id (UUID), email, hash mật khẩu, vai trò, trạng thái,
      `is_verified`, thời điểm tạo, lần đăng nhập cuối
- [x] Bảng `sessions`: phiên đăng nhập **phía máy chủ**, thu hồi được
- [x] `platform_core/users.py`: tạo user, xác thực (chống timing oracle +
      không lộ email nào đã đăng ký), tạo/thu hồi phiên, đổi mật khẩu
- [x] Xác thực bằng bảng `users` (Q24 — **không** fastapi-users) — **dựng song
      song** với auth hiện có
- [x] Phiên lưu phía máy chủ: cookie chỉ mang `sid`, thu hồi = xoá dòng
- [x] Giữ `admin` từ biến môi trường **làm đường lui**, chưa gỡ (xem ghi chú)
- [x] `tests/test_64_nguoi_dung.py` — 18 test (SQLite) + nghiệm thu thật trên
      PostgreSQL (đăng nhập → vào được → đăng xuất → phiên bị thu hồi)

**Tiêu chí hoàn thành**
- [x] Đăng nhập → vào được → đăng xuất → không vào lại được (phiên bị xoá ở DB)
- [x] Đổi mật khẩu làm **mọi phiên khác** hết hiệu lực (có test)
- [x] Xác thực sai không tiết lộ email nào đã đăng ký (có test)
- [x] Toàn bộ test cũ (CSRF, rate-limit, cookie an toàn, admin-env) vẫn xanh

**Điều chỉnh có lý do — CHƯA gỡ đường admin-env:** kế hoạch gốc ghi "chỉ khi
đường mới xanh thì gỡ `session.py` cũ". Nhưng gỡ admin-env **bây giờ** là sai:
chưa có cách nào tạo tài khoản admin **trong CSDL** (trang quản trị đến H3 mới
có, qua sqladmin). Gỡ trước khi có cách đó nghĩa là một CSDL trống = không ai
đăng nhập được. Vì vậy admin-env được giữ làm **đường lui chính thức** tới khi
H3 có trang tạo admin trong DB — đó cũng là lúc gỡ, không phải bây giờ.

**Ghi chú về cái giá đã biết:** `server/auth/` có 4 file đã test và đang chạy.
Thứ tự **dựng song song → chứng minh xanh → mới gỡ cũ** đã theo đúng; riêng
bước "gỡ" dời sang H3 theo lý do trên.

### H1.3 — Đăng ký, xác thực email, chống lạm dụng ✅ XONG (code) 2026-07-31

Đây là hệ quả trực tiếp của Q7 (tự đăng ký + credit dùng thử). Không có phần
này thì credit dùng thử **sẽ** bị hút cạn bằng tài khoản ảo.

**Phần code: xong và đã nghiệm thu (test + PostgreSQL thật + browser).**

- [x] Tầng gửi mail tách riêng `platform_core/mailer.py`: `ResendMailer` (Q19)
      + `ConsoleMailer` (dev/test). Chọn theo biến môi trường, không theo code.
- [x] Token xác thực + đặt lại mật khẩu `platform_core/tokens.py`
      (`itsdangerous`, Q24): ký, hết hạn, mỗi loại một salt riêng
- [x] **Cloudflare Turnstile** `server/auth/turnstile.py` — xác minh phía máy
      chủ; bỏ qua có kiểm soát khi chưa cấu hình khoá
- [x] Luồng đăng ký → gửi mã xác thực → `/verify-email` bật `is_verified`
- [x] Chặn tên miền mail dùng-một-lần + giới hạn IP `platform_core/antifraud.py`
- [x] Quên mật khẩu / đặt lại mật khẩu (đặt lại **thu hồi mọi phiên**)
- [x] `tests/test_65_dang_ky.py` — 8 test

**Phần khoá thật: ĐÃ XONG 2026-07-31 (điều khiển trình duyệt).**

- [x] **Resend:** tạo tài khoản, thêm domain **`mail.lttstudios.com`** (subdomain
      riêng, không đụng SPF trang chủ). DNS (DKIM/SPF/MX) áp qua **Cloudflare
      Domain Connect** (one-time, KHÔNG cấp Resend quyền thường trực) → domain
      **verified**. API key **Sending access** (least-privilege). Đặt
      `RESEND_API_KEY` + `LTT_MAIL_FROM="LTT AI Studio <no-reply@mail.lttstudios.com>"`
      vào `secrets/app.env` → mailer chuyển sang **ResendMailer** (mail thật).
- [x] **Turnstile:** tạo widget "LTT app" cho `app.lttstudios.com` (Managed);
      đặt `TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET_KEY` → form đăng ký có ô chống
      bot thật (đã kiểm: `/register` render `cf-turnstile` + script). CSP đã cho
      phép `challenges.cloudflare.com` từ H1.4.

→ **Đăng ký cho khách thật giờ đã đủ điều kiện chạy** (Turnstile + mail xác thực
+ credit dùng thử sau verify từ H3-admin).

**Nối ở H3, chưa làm được bây giờ:**

- [x] **Cấp credit dùng thử sau xác thực** — ✅ ĐÃ LÀM (H3 xong): `server/routes/register.py:155`
      cấp credit dùng thử MỘT LẦN đúng lần xác thực đầu tiên. Ô này bị bỏ quên
      từ thời chưa có bảng credit. Ghi chú gốc:
  ~~`/verify-email` đã có đúng chỗ nối~~
      (ghi chú trong code), nhưng chưa có bảng credit (H3). Cấp credit là việc
      của H3.

**Tiêu chí hoàn thành**
- [x] Token giả mạo/hết hạn bị từ chối (có test); mỗi loại token một salt riêng
- [x] Tài khoản chưa xác thực có `is_verified=False` (credit/job chặn theo cờ
      này khi H2/H3 tới)
- [x] Đăng ký quá giới hạn IP/ngày bị từ chối (có test)
- [x] Không phản hồi nào tiết lộ email đã đăng ký — đăng ký trùng và quên-mật-
      khẩu email-không-tồn-tại đều cho phản hồi giống hệt (có test)

### H1.4 — Phân quyền app cho từng người dùng ✅ XONG 2026-07-31

- [x] Bảng `app_access`: mỗi (user × app) → `enabled`/`locked`/`hidden`, chỉ
      lưu ngoại lệ (Q25 — mặc định mở)
- [x] `platform_core/app_access.py`: `muc_quyen`, `dat_quyen` (về mặc định thì
      xoá dòng), `app_cho_path` (khớp prefix dài nhất), `loc_app_hien_thi`
- [x] Chặn ở tầng route bằng `server/access_middleware.py` — phủ mọi đường vào,
      **kể cả gõ thẳng URL**, không sửa từng app (giữ hợp đồng)
- [x] Trang chủ **và** sidebar đều lọc app `hidden` theo user
- [x] `tests/test_66_phan_quyen_app.py` — 10 test

**Tiêu chí hoàn thành**
- [x] Gõ thẳng URL app bị ẩn → 404; bị khoá → 403 (có test + nghiệm thu Postgres)
- [x] Admin thấy hết, kể cả khi có dòng khoá (có test)
- [x] Ẩn danh vào app-path vẫn được `require_login` đưa về /login (middleware
      không nuốt redirect)

**Sửa kèm — lỗi CSP sẽ chặn Turnstile:** CSP cũ chỉ cho script `'self'`, nên
khi bật Turnstile (H1.3) script của Cloudflare sẽ bị chặn — một lỗi chỉ lộ lúc
production bật chống-bot. Đã thêm `challenges.cloudflare.com` vào `script-src`
và `frame-src`.

**Nối ở H3:** trang admin đặt quyền (qua sqladmin). Hiện đặt quyền bằng hàm
`dat_quyen` (đã test); UI quản trị là việc của H3.

---

## ✅ H1 (Người dùng) HOÀN TẤT 2026-07-31

Toàn bộ H1.1→H1.4 xong. Nền tảng giờ biết "ai đang dùng", tách được dữ liệu
người này người kia, cho tự đăng ký an toàn, và phân quyền được từng app.
Còn hai việc chờ khoá của người dùng (Resend, Turnstile — H1.3) và một việc
nối ở H3 (cấp credit sau xác thực, trang admin đặt quyền).

---

## H2 — Hàng đợi job

**Mục tiêu:** việc dài chạy được ngoài vòng đời một request, sống sót qua khởi
động lại, và không bao giờ bị hai worker làm hai lần.

### H2.1 + H2.2 — hàng đợi + worker ✅ XONG 2026-07-31

- [x] Tự quản bảng `jobs` + `SELECT … FOR UPDATE SKIP LOCKED` (Q26)
- [x] Bảng `jobs`: id, chủ sở hữu, app, loại job, tham số, trạng thái, tiến độ,
      kết quả, lỗi, attempts, dedupe_key, heartbeat, thời điểm
- [x] `platform_core/jobs.py`: submit / claim / heartbeat / set_progress /
      complete / fail / reclaim_orphans / resolve_handler
- [x] `platform_core/job_runner.py` + `job_worker.py`: vòng chạy + entry
- [x] Dịch vụ Windows `LTTStudioWorker` riêng (Q6), đăng ký trong
      `setup/2-cai-dat.ps1`; `update.ps1`/`rollback.ps1`/`4-nghiem-thu.ps1`
      biết về nó
- [x] Retry luỹ thừa có giới hạn (base×2^n, chặn trên); job mồ côi được nhặt lại
- [x] Cửa sổ chống trùng qua `dedupe_key`
- [x] `tests/test_67_hang_doi_job.py` — 15 test

**Tiêu chí hoàn thành**
- [x] Tắt worker giữa chừng → nhặt lại (reclaim_orphans, có test)
- [x] **Hai worker không làm trùng** — nghiệm thu thật: 5 worker × 30 job trên
      PostgreSQL, không job nào chạy hai lần, tất cả done
- [x] Khởi động lại → job đang chờ vẫn còn (nằm trong CSDL)
- [x] `LTTWeb` restart không giết job đang chạy (worker là tiến trình riêng)
- [x] Nghiệm thu worker **process** thật: submit → worker nhặt → complete đúng

**Hoãn có lý do — lọc capability worker (Q6):** claim hiện không lọc theo
`requires` của app vì giai đoạn này **một worker đa năng** (máy chủ có cả GPU).
Khi có worker ở nhiều máy mới cần — chỗ lọc đã ghi sẵn trong `claim()`.

### H2.3 — Web submit + tiến độ về trình duyệt ✅ XONG 2026-07-31

- [x] `server/routes/jobs.py`: trang danh sách + chi tiết + fragment tiến độ,
      **lọc theo user** (A không thấy job B → 404)
- [x] Tiến độ đẩy về trình duyệt bằng HTMX (Q18), **self-host** `htmx.min.js`
      trong `server/static/` (CSP chặn CDN) + mount StaticFiles
- [x] Nối `apps/demo` nút "Chạy qua hàng đợi" → `submit_with_credit` → trang job
- [x] `tests/test_69_web_jobs.py` — 6 test (gồm A-không-đọc-được-job-B)

**Rủi ro lớn nhất:** job bị làm hai lần trên một API tính tiền. Đã chứng minh
bằng nghiệm thu 5-worker, không suy luận.

---

## H3 — Sổ credit ✅ XONG 2026-07-31 (trừ trang admin, dời H3-sqladmin)

**Mục tiêu:** tiền không bao giờ sai. Đây là phần ít code nhất nhưng ít được
phép sai nhất.

- [x] Bảng `credit_entries` **chỉ ghi thêm**; số dư = tổng của sổ, không ô sửa đè
- [x] `platform_core/credit.py`: nạp / cấp-tay / giữ-chỗ / quyết-toán / hoàn
- [x] Ba thao tác cùng giao dịch với tạo job (`platform_core/job_submit.py`):
      giữ chỗ khi submit; quyết toán/hoàn ở worker (`job_runner`)
- [x] Từ chối job khi không đủ credit **trước khi** tạo job (rollback cả cụm)
- [x] Chặn đường lách "Tạo lại"/F5 qua `dedupe_key` — giữ chỗ đúng một lần
- [x] Quyết toán/hoàn **idempotent theo job** (worker retry không trừ/hoàn 2 lần)
- [x] `tests/test_68_credit.py` — 13 test
- [x] **Trang admin (sqladmin, Q15): dời sang mốc riêng "H3-admin"** — ✅ H3-admin
      ĐÃ XONG 2026-07-31; dòng này chỉ là con trỏ, không phải việc còn nợ.

**Tiêu chí hoàn thành**
- [x] Số dư = tổng sổ (append-only)
- [x] Job lỗi → hoàn **đủ**, số dư về như cũ (có test + nghiệm thu)
- [x] Job chạy lại → chỉ trừ một lần (idempotent, có test)
- [x] Không đủ credit → job bị từ chối, không tạo job (có test)
- [x] Nghiệm thu sổ thật trên PostgreSQL: `topup +100 → hold -1 → settle +0`,
      số dư 99, dấu vết append-only đầy đủ

### H3-admin — Trang quản trị credit/quyền (sqladmin, Q15) ✅ XONG 2026-07-31

Gom mọi trang admin vào một mốc: xem/sửa user, xem sổ credit, cấp credit tay,
đặt quyền app (H1.4 hiện đặt bằng hàm), **tạo admin trong CSDL** → đó cũng là
lúc gỡ đường admin-env (H1.2). Tách riêng vì cả cụm dùng chung sqladmin và đều
là mặt admin, không phải mặt khách.

**Đã làm (MVP, nghiệm thu browser thật):**
- [x] Thêm `sqladmin>=0.20.1,<0.21` + `wtforms` (Q17 cận trên); tương thích
      Starlette 1.3 (đã kiểm dry-run, không hạ version)
- [x] `server/admin.py`: `AdminAuth` chỉ cho admin (dùng chung phiên nền tảng
      qua `session_secret`; không admin → 303 /login), gắn ở `/admin`
- [x] ModelView: User (sửa role/is_active/is_verified, KHÔNG sửa email/hash,
      không xoá), **CreditEntry read-only (append-only)**, AppAccess (CRUD),
      Job (read-only), Session (xoá = thu hồi), PlatformInfo (read-only)
- [x] `GrantCreditView` `/admin/grant-credit`: cấp/điều chỉnh credit tay qua
      `credit.cap_tay` (ghi bút toán `grant` mới, không sửa sổ cũ)
- [x] `create_app` gắn admin có guard: thiếu sqladmin hoặc chưa có CSDL → bỏ qua
      an toàn (không làm vỡ ~1500 test chạy bằng system python/không DB)
- [x] Nghiệm thu browser: đăng nhập admin → /admin hiện 7 view, đọc PostgreSQL
      thật OK; chưa đăng nhập → 303 /login. Full suite: 1512 pass (+3 test sửa
      theo thay đổi: wording home + loại `.playwright-mcp` khỏi release scan).

**Đã làm thêm (2026-07-31, đợt 2):**
- [x] **Tạo admin TRONG CSDL**: `tools/create_admin.py` (tạo/nâng user role=admin,
      băm mật khẩu đúng, idempotent). Đã tạo `admin@lttstudios.com` và **nghiệm thu
      qua production thật** (curl ép Cloudflare edge: login email → 303, /admin → 200).
- [x] **Cấp credit dùng thử sau xác thực email**: `/verify-email` gọi
      `credit.cap_tay` MỘT LẦN đúng lần verify đầu (idempotent theo chuyển trạng
      thái); lượng qua `LTT_TRIAL_CREDIT` (mặc định 20).
- [x] Test `tests/test_70_admin_h3.py`: trial-credit idempotent + /admin đá ẩn
      danh về /login + chỉ role=admin vào /admin (user thường bị chặn). Full suite
      **1518 pass, 1 skip**.

**admin-env — đã chốt Q29 (2026-07-31):** giữ code làm **break-glass**, **VÔ HIỆU
ở production**. Đã xoá `LTT_ADMIN_PASSWORD_HASH` khỏi `secrets/app.env` + nạp lại
env dịch vụ; `settings.py` bỏ hash/username khỏi danh sách secret bắt buộc (chỉ
còn `LTT_SESSION_SECRET`). Nghiệm thu qua Cloudflare edge: admin-env `admin/...`
→ **401**; DB admin `admin@lttstudios.com` → **303 + /admin 200**. Full suite
1518 pass. Bật lại break-glass = đặt lại env hash khi cứu hộ.

**Tham khảo:** `app/modules/seedance_video/cost.py` bên `D:\BOT GEMINI` có mô
hình giá token thật + markup + VND — đọc khi port `seedance_video` (H11), không
cần cho demo.

**Lỗi đã có tiền lệ (đã tránh):** BOT GEMINI từng để nút "Tạo lại" đi vòng cổng
kiểm tra → chạy job miễn phí + xếp hàng vô hạn (`P0-5`). Ở đây `dedupe_key` +
giữ-chỗ-một-lần chặn đúng đường đó, có test.

**Tham khảo có sẵn:** `app/modules/seedance_video/cost.py` bên `D:\BOT GEMINI`
đã có mô hình giá theo token thật + markup + quy đổi VND + `reserve_check`.
Đọc để học, **viết lại** theo hợp đồng app của dự án này (Q3).

**Lỗi đã có tiền lệ:** BOT GEMINI từng để nút "Tạo lại" đi vòng qua cổng kiểm
tra, cho phép chạy job không mất tiền và xếp hàng vô hạn. Họ đã phải vá
(`P0-5`). Đừng lặp lại — viết test cho đúng đường đó ngay từ đầu.

---

## H4 — Nghiệm thu bằng `apps/demo` ✅ XONG 2026-07-31 (chuỗi chính)

**Mục tiêu:** chứng minh cả chuỗi thông suốt **trước khi** cắm một tool tốn
tiền API vào.

- [x] Chạy đủ chuỗi (browser + PostgreSQL + worker thật): đăng nhập → demo →
      chạy qua hàng đợi → tạo job + giữ chỗ credit → worker nhận → xử lý → HTMX
      hiện tiến độ → kết quả đúng → trừ credit đúng (99), sổ append-only đủ
- [x] Hỏng có chủ ý: job lỗi → credit hoàn đủ (test + nghiệm thu)
- [x] Hai người dùng: A không đọc được job B (test tầng route)
- [x] Kiểm tra thật bằng browser (Playwright), console 0 lỗi
- [x] Hỏng có chủ ý: giết worker giữa chừng → nhặt lại — **nghiệm thu sống
      2026-09-07**, `tools/nghiem_thu_mo_coi.py`.

      Ba test đã có (`test_67`, `test_150`, `test_313`) đều làm **một** việc:
      đặt `heartbeat_at` lui về quá khứ rồi gọi `reclaim_orphans()`. Tức chúng
      kiểm **phía đọc**. Hai phía không test nào chạm tới:

      1. **phía ghi** — worker thật có cập nhật nhịp khi đang chạy không;
      2. **phía lịch** — có vòng nào *tự* gọi nhặt lại không.

      ⭐ Một bộ test xanh ở phía đọc vẫn tương thích hoàn toàn với một hệ thống
         **không bao giờ nhặt lại gì** — vì không ai ghi nhịp, hoặc không ai gọi
         vòng. Nên phép nghiệm thu này giết một **tiến trình thật** và không giả
         lập gì cả.

      | Mốc | Đo được |
      |---|---|
      | đối chứng A | nhịp **tiến** 2 lần khi worker A còn sống |
      | giết | `taskkill /F`, nhịp đóng băng ở `01:20:46` |
      | đối chứng B | 45 giây sau nhịp **vẫn** `01:20:46` — lệnh giết ăn thật |
      | nhặt lại | worker B nhận job sau **265 giây**, `attempts 0 → 1` |

      Hai lớp đối chứng có mặt vì nếu chỉ đo *"sau khi giết, B nhận job"* thì
      kết quả ấy còn khớp với hai giả thuyết tầm thường: **A chưa bao giờ chạy**,
      và **lệnh giết không ăn**.

      🔴 **Phát hiện kèm theo:** `platform_core/jobs.py:248 heartbeat()`
         **không được gọi ở đâu cả**. Nhịp của job chỉ nhích khi app gọi
         `ctx.progress` → `jobs.set_progress` (`jobs.py:336`). Đó là hợp đồng
         thật — `apps/taovideo/jobs.py:5` ghi rõ — nhưng **không có gì cưỡng
         chế** nó. Một app render 6 phút mà không báo tiến độ sẽ bị nhặt oan
         **trong khi worker vẫn đang chạy nó**. Đo 07/09: mọi app chạy lâu đều
         gọi (`autosubvideo` 17, `upscalevideo` 14, `taovideo` 8,
         `taoclipngan` 6), nên hôm nay không có app nào dính.

      ⛔ Không biến việc này thành bước gate: nó ngủ ~7 phút theo đúng
         `ORPHAN_TIMEOUT` thật, và rút ngắn bằng cách ví nhịp về quá khứ là
         quay lại **đúng** phép đo mà ba test kia đã làm. Và **đừng** dựng bánh
         cóc đếm lời gọi `progress` — đếm lời gọi không chứng minh khoảng cách
         giữa hai nhịp nhỏ hơn 5 phút (`AGENTS.md` §4d lớp E).
- [ ] Tắt CSDL → giao diện báo lỗi rõ (dời cùng H3-admin/observability)

**Trạng thái:** chuỗi chính đã nghiệm thu thật. Hai mục còn lại cần tình huống
chạy-lâu hoặc thuộc observability, không chặn H5.

---

## H5 — Tool thật đầu tiên: `thumbnail_api` ✅ XONG 2026-07-31 (chạy thật, trừ credit đúng)

**Mục tiêu:** một tool có người trả tiền, đi qua đúng hợp đồng app.

- [x] Tham chiếu `D:/BOT GEMINI/app/modules/thumbnail_api` (chỉ đọc) — lấy đúng
      cách gọi Gemini Image API, BỎ api-pool/cascade/prompt-fragment của họ (Q3)
- [x] Dựng `apps/thumbnail/` theo hợp đồng: manifest + jobs (httpx sync gọi
      `gemini-2.5-flash-image`, lưu ảnh qua storage) + routes + templates
- [x] `credit_cost` = số ảnh × 5 (là hàm; TODO: quyết toán theo token thật)
- [x] Khoá API đọc `GEMINI_API_KEY` phía máy chủ, che khoá ở mọi thông báo lỗi,
      KHÔNG xuống trình duyệt
- [x] Test `tests/test_71_thumbnail.py` (5, Gemini mock): thiếu topic/khoá → ném;
      tạo ảnh → lưu storage; lỗi Gemini → ném + che khoá. Full suite 1523 pass.
- [x] Nghiệm thu render: `/thumbnail` hiện form + gallery, app tự lên trang chủ/
      sidebar (không sửa giao diện nền tảng) — kiểm qua Cloudflare edge.
- [x] **Chạy thật (nghiệm thu):** `GEMINI_API_KEY` đã nạp; tạo thumbnail thật →
      ảnh 1.8 MB PNG, số dư 50→45 (trừ đúng 5), ảnh phục vụ có kiểm sở hữu.
- [x] **Vá lỗi bảo mật kèm:** ảnh .png bị Cloudflare cache → rò cho người chưa
      đăng nhập. Fix: `no-store` cho mọi response ngoài `/static/` + purge +
      test khoá. Xem NHAT_KY.

**Hai lỗ hổng hợp đồng H5 lộ ra & đã lấp (đây là "phép thử thật của hợp đồng"):**
1. **Template app:** `server/templating.py` nay tìm cả `apps/*/templates/`
   (ChoiceLoader) → app tự mang UI, không đụng `server/templates/`.
2. **File output tải về:** app tự phục vụ qua route `/image/{key}` đọc storage +
   kiểm sở hữu theo key (download_token của storage không dùng được qua ranh giới
   worker→web vì giữ trong RAM mỗi tiến trình). Ghi vào `docs/03`.

**KHÔNG sửa `platform_core/`; chỉ sửa `server/templating.py`** (bổ sung hợp đồng
có chủ đích, đã ghi tài liệu) — đúng tinh thần Q3/hợp đồng app.

**Tiêu chí hoàn thành**
- **Không sửa một dòng nào** trong `platform_core/` hay `server/`. Nếu buộc
  phải sửa → dừng, ghi lại vì sao, bổ sung vào hợp đồng app (đây chính là phép
  thử thật của hợp đồng)
- App tự hiện trên trang chủ và sidebar
- Chạy thật một job, trừ đúng credit
- Quét bí mật 0 finding

---

## H6 — Cốt lõi vận hành nền tảng (catalog công khai + SSO UX) ✅ XONG 2026-07-31

**Quyết định nền:** Q30. **Mục tiêu:** khách vào `app.lttstudios.com` thấy trang
chủ công khai liệt kê app; bấm một app → (nếu chưa đăng nhập) đăng nhập rồi quay
lại đúng app; một tài khoản dùng cho mọi app (SSO tự nhiên vì cùng một host).

### Sơ đồ vận hành

```
Khách ─► app.lttstudios.com/  (CATALOG CÔNG KHAI: box app + [Đăng nhập][Đăng ký])
              │ bấm "Dùng /thumbnail"
       ┌──────┴───────┐
   đã đăng nhập?     chưa
       │ có            │
       ▼               ▼
  mở /thumbnail   /login?next=/thumbnail ─► đăng nhập (Turnstile+mail) ─► /thumbnail
       │
       ▼
  VỎ ĐÃ ĐĂNG NHẬP: sidebar (app launcher) + topbar [số dư credit][email ▾ Đăng xuất]
  1 phiên/1 host = 1 tài khoản cho MỌI /app. Trang động = no-store (H5).
```

### Nguyên tắc
- 1 host, path-based (`apps/<slug>/` → `/<slug>`); **không** subdomain/cookie-cha/OIDC.
- Hai lớp giao diện: **catalog công khai** (không sidebar) vs **vỏ app đã đăng nhập**.
- `require_login` giữ nguyên cho **route app**; chỉ trang chủ `/` mở công khai.
- Deep-link login `?next=` + **chống open-redirect** (chỉ nhận đường dẫn tương đối).

### H6.1 — Trang chủ CÔNG KHAI (catalog)
- `server/auth/session.py`: thêm `current_identity_optional(request) -> str|None`
  (trả username admin-env HOẶC email DB HOẶC None; **không raise**).
- `server/routes/dashboard.py` `home()`: bỏ `Depends(require_login)`; dùng
  `current_identity_optional`. Truyền `authed = user is not None`. Lọc quyền app
  (`loc_app_hien_thi`) CHỈ khi authed; khách thấy mọi app `enabled`. Blockers +
  `broken` chỉ hiện khi authed.
- `server/templates/base_public.html` (MỚI): vỏ công khai — logo + `[Đăng nhập]`
  `[Đăng ký]`, **không sidebar**.
- `server/templates/home.html`: `{% extends "base.html" if authed else
  "base_public.html" %}`. Box app: authed → `[Mở →] {{ m.route_prefix }}`; khách
  → `[Đăng nhập để dùng] /login?next={{ m.route_prefix }}`. Ẩn blockers khi khách.
- **Tiêu chí:** khách GET `/` → 200 (KHÔNG redirect), thấy box app + Đăng nhập/
  Đăng ký, không sidebar nội bộ, không blockers. User GET `/` → sidebar + Mở +
  account. Test cũ giả định `/` redirect-khi-ẩn-danh (nếu có) → cập nhật.

### H6.2 — Đăng nhập có return-to (`?next=`)
- `server/auth/session.py`: thêm `safe_next(raw) -> str` — trả `raw` nếu bắt đầu
  `/` **và** không `//` **và** không chứa `://` **và** không có ký tự xuống dòng;
  ngược lại `/`. Sửa `require_login`: `Location = "/login?next=" + quote(path)`.
- `server/routes/auth.py`: GET `/login` nhận `next` (đã đăng nhập → về
  `safe_next(next)`); POST login nhận `next` (Form) → sau đăng nhập (cả DB lẫn
  admin-env) `RedirectResponse(safe_next(next), 303)`.
- `server/templates/login.html`: thêm `<input type="hidden" name="next"
  value="{{ next|e }}">`.
- **Tiêu chí (test):** GET `/thumbnail` khi logout → 303 `/login?next=/thumbnail`;
  POST /login (next=/thumbnail) → 303 `/thumbnail`; `safe_next` từ chối
  `//evil.com`, `https://evil`, `/\nx` → trả `/`.

### H6.3 — Vỏ đã-đăng-nhập (account + credit + launcher)
- `server/templating.py`: thêm global `so_du_credit(request) -> int|None` (an
  toàn như `nav_apps`; None khi admin-env/không DB).
- `server/templates/base.html`: topbar phải = email/username + `{{
  so_du_credit(request) }} credit` + `[Đăng xuất]`. Sidebar = app launcher (đã có)
  + "🏠 Trang chủ" (đã có).
- **Tiêu chí:** trang authed hiện email + số dư credit + đăng xuất; đổi app qua
  sidebar; số dư khớp `credit.so_du`.

### H6.4 — Hai app đúng đường dẫn
- **thumbnail:** `/thumbnail` ✅ — chỉ kiểm hiện đúng trong catalog (box, giá, Mở).
- **socialbot (Q30/Q10):** GIỮ path gốc (`/facebook`...), hiện **1 box** catalog
  trỏ `route_prefix`. KHÔNG sửa socialbot (đóng băng). Đổi `/socialbot` để sau
  (kèm Redirect URI) khi tách bán riêng.
- **Quyết định phụ (ĐÃ CHỐT):** `demo` và `socialbot` đặt `public=False` → **ẩn
  khỏi catalog khách**, chỉ hiện trong sidebar sau khi đăng nhập + phân quyền.
  Cờ dùng chung là `public` trên `AppManifest` (không thêm cờ `internal` riêng).
  Đã kiểm trình duyệt: catalog khách chỉ hiện `thumbnail`.

### H6.5 — Quy ước slug + tài liệu + test tổng
- Slug **thường-gạch-nối** (`thumbnail`, `youtube-script`) → ghi `docs/03`.
- Cập nhật `docs/00_BAT_DAU_TU_DAY.md` (mô hình vận hành + trạng thái).
- `tests/test_72_vanhanh.py`: catalog công khai (khách 200 + có box + không
  sidebar), login `next` + open-redirect, account/credit khi authed.
- Full `pytest -q` + `scan_source_secrets` + **kiểm trình duyệt thật** (khách →
  catalog → click → `/login?next` → dùng thumbnail → thấy account/credit).

### Rủi ro & phòng
- Mở `/` công khai chỉ lộ manifest (tên/mô tả/giá) — không dữ liệu user; app
  routes vẫn `require_login`. An toàn.
- Open-redirect → `safe_next`. | Jinja `extends` động → test cả 2 nhánh.
- Không phá test cũ giả định `/`→/login khi ẩn danh → cập nhật cùng H6.1.

### Thứ tự & tiêu chí hoàn thành H6
H6.1 → H6.2 → H6.3 → H6.4 → H6.5; **mỗi bước** phải xanh test + kiểm trình duyệt
mới sang bước sau. **Xong H6 khi:** khách duyệt catalog không cần đăng nhập; bấm
app → đăng nhập → về đúng app; 1 tài khoản vào mọi app; account+credit hiện ở vỏ;
full suite xanh + scan 0.

**✅ Hoàn thành 2026-07-31.** Full suite **1530 passed, 1 skipped**; scan 0
finding. Kiểm trình duyệt thật (Playwright) qua `app.lttstudios.com`: (1) khách
GET `/` → 200 catalog công khai, CHỈ hiện `thumbnail` (demo/socialbot ẩn), có
`[Đăng nhập][Đăng ký]`, không sidebar; (2) bấm "Đăng nhập để dùng" →
`/login?next=/thumbnail`; (3) đăng nhập → nhảy đúng về `/thumbnail`; (4) vỏ
authed hiện sidebar + badge `💳 45 credit` + `[Đăng xuất (admin@lttstudios.com)]`.
`safe_next` chặn open-redirect (unit test + kiểm chứng chuỗi méo trả `/`). Console
chỉ 1 lỗi: CSP chặn `beacon.min.js` Cloudflare tự tiêm — **CSP hoạt động đúng**,
dọn ở dashboard (không phải code).

### H6.6 — Vỏ app launcher hai tầng + lối vào quản trị ✅ XONG 2026-07-31

Phát sinh từ phản hồi người dùng: sidebar bị 8 mục socialbot chiếm kín. Chốt 3
điểm (người dùng chọn): admin về trang chủ + link Quản trị; banner FB/TikTok →
badge trên thẻ app; xây luôn.

- **Sidebar hai tầng:** `templating.py` thêm `active_app()` + `is_admin()`;
  `base.html` render mỗi app một dòng (tầng 1), trang con chỉ bung khi đang trong
  app (tầng 2). Không đụng socialbot.
- **Link 🛡️ Quản trị** (`/admin/`) chỉ cho admin CSDL. Admin dùng được mọi app.
- **Blocker theo app:** `AppManifest.blocker_titles` (mới) → badge "cần thiết lập"
  trên đúng thẻ app; bỏ banner toàn cục ở trang chủ. Không hardcode tên app.
- **Sửa bug ERR_TOO_MANY_REDIRECTS:** `login_form` xác thực sid đồng nhất với
  `require_login` (`current_identity_optional`) — phiên bị thu hồi không còn gây
  vòng lặp `/login` ⇄ route. Regression trong test_72.
- Full suite **1534 passed**; kiểm chứng production qua edge (browser máy chủ chập
  do IPv6 hỏng — lỗi mạng máy, không phải app).

---

## H7 — Củng cố MVP (Hardening) 🔧 ĐANG LÀM

Nguồn: audit toàn diện `docs/AUDIT_MVP_2026-07-31.md` (điểm tổng ~73/100). Ba wave;
mỗi mục có cổng test riêng. Kết mỗi wave: `pytest -q` xanh + `scan_source_secrets`
0 + kiểm trình duyệt. Chi tiết đầy đủ ở file audit.

- **Wave 0 (P0 — chặn khách ngoài) ✅ XONG 2026-07-31.** Khoá credit (advisory
  lock) + test đồng thời PostgreSQL; đấu `dedupe_key`; `CF-Connecting-IP`; restore
  `pg_restore`; băm token phiên (migration `b1c2d3e4f5a6`) + che SessionAdmin;
  `update.ps1` chạy alembic; sửa drift CLAUDE.md. Full suite **1547 pass** + 2 test
  PG đồng thời pass; deploy + migration production OK.
- **Wave 1 (P1 — trước khách trả tiền) ✅ XONG 2026-07-31.** thumbnail tính tiền
  theo ảnh thành công + loop resume-safe; handler 500 tổng (no-store + correlation
  id); CSRF sqladmin/GrantCredit + dropdown AppAccess.level; khoá theo tài khoản +
  rate-limit forgot-password + CSRF logout + chặn login khi chưa xác thực email;
  siết ACL backup off-drive (icacls SID); validate hợp đồng sớm trong `_validate`
  (job_types thiếu credit_cost / trùng job_type → fail lúc discover); scanner thêm
  rule session/token key. Full suite **1562 pass**. Commit `5f00302`.
  *Ghi chú:* mở rộng scan slug sang `server/` BỎ — từ "thumbnail" trùng trường
  thumbnail-video của socialbot + "socialbot" trong comment → substring-scan báo
  nhầm; không khả thi mà không có allowlist.
- **Wave 2 (hoàn thiện + quan sát được) ✅ XONG 2026-07-31.** API key Gemini qua
  header (không URL query); test HTTP kiểm sở hữu `/image/{key}` (cross-user 404);
  `reclaim_orphans` SKIP LOCKED + index tổng hợp `ix_jobs_claim` (migration
  `c7d8e9f0a1b2`); log rotation theo kích thước (AppRotateBytes 10MB × 3 dịch vụ,
  áp cả bản đang chạy); smoke Playwright opt-in (`test_74`, skip nếu chưa cài).
  *Hoãn có chủ đích:* **`Storage.url_for()` + presigned R2 → làm ở H9** (gắn chặt
  với backend R2; làm nửa vời bây giờ chỉ thêm bề mặt, không lợi ích khi chưa có
  file lớn). **FK constraints** hoãn (rủi ro migration trên DB tiền thật + FK trên
  `credit_entries.job_id` bất khả vì sentinel `""`; `CHECK(delta<>0)` SAI vì
  quyết toán ghi delta=0 hợp lệ). **Đánh dấu ~929 test socialbot đóng băng** hoãn
  (churn lớn, giá trị thấp).

---

## H8 — Bộ máy APIKEYS (quản trị nguồn API) — Pha 1 ✅ XONG 2026-07-31

**✅ Hoàn thành:** H8.1–H8.7 (bảng ApiKey + secretbox + Provider Registry +
allocator + menu `/admin/api-key` + import 6 key + đấu thumbnail). Full suite
**1583 pass**, scan 0. Production: migration `d8e9f0a1b2c3`; 6/6 key import;
`/admin/api-key/list` 0 secret thô; Test key gemini HTTP 200. Chi tiết ở
`NHAT_KY.md`. **Pha 2 (sau):** telemetry rpm/tpm/token, cascade đa-provider,
làm mới model tự động.

---

## H8 — Bộ máy APIKEYS — Pha 2 ✅ XONG 2026-08-01 (telemetry · cascade · làm mới model)

**✅ Hoàn thành:** H8.8–H8.10. Migration `e9f0a1b2c3d4` chạy trên production;
`/admin/apikeys` có cột Tải + nút Làm mới; `api-models-refresh` lấy 50 model sống
từ Gemini thật; full suite **1598 pass / 4 skip**, scan 0. Chi tiết ở `NHAT_KY.md`.
Kế hoạch chi tiết ban đầu giữ nguyên bên dưới để đối chiếu.

---

## H8 — Bộ máy APIKEYS — Pha 2 📋 (kế hoạch gốc: telemetry · cascade · làm mới model)

**Mục tiêu:** một key hỏng/nghẽn KHÔNG làm chết cả loại API; admin thấy tải thực;
model không còn hardcode. Giữ nguyên bất biến Pha 1 (không lộ credential thô; app
xin key qua engine; thêm provider = sửa `providers.py`).

### H8.8 — Telemetry rpm/tpm/token (cửa sổ trượt trong-hàng)
- `models.py` thêm cột vào `ApiKey`: `rpm_limit`, `tpm_limit` (Integer, 0 = không
  giới hạn), `total_tokens` (BigInteger), và cửa sổ cố định 60s ngay trong hàng:
  `window_start` (DateTime), `window_requests`, `window_tokens` (Integer). KHÔNG
  lập bảng time-series (thừa cho quy mô này) — cửa sổ cố định đủ để chặn tải + hiện số.
- `api_pool.py`: `_cuon_cua_so(key, now)` reset cửa sổ khi quá 60s; `lay_key`/
  `chon_key` **bỏ qua** key đã chạm `rpm_limit`/`tpm_limit` trong cửa sổ hiện tại
  (coi như tạm hết), tăng `window_requests` khi chọn. `danh_dau_thanh_cong(...,
  tokens=0)` cộng token vào `window_tokens` + `total_tokens`. Hàm `rpm(key)`/`tpm(key)`.
- Migration thêm cột (chain từ `d8e9f0a1b2c3`).
- **Test:** cửa sổ reset sau 60s; `rpm_limit` chặn chọn key; kế toán token cộng đúng.

### H8.9 — Cascade đa-provider (theo category)
- `api_pool.py`: `chon_key(db, *, category, model=None, thu_tu_provider=None)` gom
  key **mọi provider** phục vụ `category` (tự hồi cooldown, bỏ disabled/rate-cap,
  lọc `model`), xếp theo (thứ tự provider ưu tiên nếu có) → `priority desc` →
  `health desc` → tải thấp. `lay_key(db, provider, ...)` giữ nguyên chữ ký, gọi
  `chon_key` với `thu_tu_provider=[provider]` (tương thích ngược). `ThieuKeyError`
  khi cạn mọi provider.
- **Test:** gemini cạn (cooldown hết) → rớt sang apiai; tôn trọng thứ tự provider;
  lọc model xuyên provider; hết sạch → `ThieuKeyError`.

### H8.10 — Làm mới model tự động
- `platform_core/providers_live.py`: `lay_models_song(prov, credential) -> list[str]`
  gọi `list_models_path`, parse cả hai dạng: OpenAI `{"data":[{"id":...}]}` (bearer)
  và Gemini `{"models":[{"name":"models/..."}]}` (query_key). Che credential khi lỗi.
- `api_keys.py`: `cap_nhat_supported_models(db, key, models)` ghi `supported_models`
  từ danh sách sống (thay hardcode). Provider video (không có `list_models_path`)
  bỏ qua.
- `admin.py`: nút **"Làm mới model"** ở ModelsView (dùng key active ưu tiên nhất của
  provider để lấy danh sách sống, hiện ra) + trên từng key (ghi vào `supported_models`).
- **Test:** parse OpenAI; parse Gemini; cập nhật `supported_models` (mock httpx);
  provider không có endpoint → không đổi gì.

### Thứ tự & tiêu chí xong H8 (Pha 2)
H8.8 → H8.9 → H8.10; mỗi bước xanh test mới sang bước sau. **Xong Pha 2 khi:**
allocator tôn trọng rpm/tpm + kế toán token; cascade rớt provider khi cạn key;
admin làm mới được model sống; migration chạy trên production; full suite xanh +
scan 0 + kiểm trình duyệt `/admin/apikeys`.

---

## H8 — Bộ máy APIKEYS (quản trị nguồn API) — Pha 1 📋 (kế hoạch gốc)

**Nguồn:** khảo sát `docs/KHAO_SAT_APIKEYS.md` (từ D:\BOT GEMINI). **Quyết định
duyệt 2026-07-31:** Phương án **D** (nền tảng theo pha); model **provider + tập
category** (model_control/chat/image/video); **import 6 key** thật ngay. Đứng
TRƯỚC khi xây các app mới (app cần nguồn key). Không dùng file JSON/pool RAM như
BOT GEMINI — bảng SQLAlchemy + mã hoá bằng `LTT_TOKEN_ENCRYPTION_KEY`.

**Nguyên tắc:** app KHÔNG giữ key nữa; app xin key từ bộ máy theo (provider,
category, model). Thêm loại API sau này = thêm 1 dòng Provider Registry (+ tuỳ 1
adapter), KHÔNG sửa nền tảng. Credential cookie/browser (Veo, ChatGPT web) là
loại KHÁC — KHÔNG thuộc bộ máy key này.

### H8.1 — Model + lưu trữ mã hoá
- `platform_core/models.py`: bảng `ApiKey` — `id`, `owner_user_id` (rỗng=pool
  chung), `name`, `provider`, `categories` (CSV/JSON các loại), `credential_enc`
  (Fernet), `base_url`, `supported_models` (JSON), `default_model`, `status`
  (active/exhausted/cooldown/error/disabled), `enabled`, `priority`,
  `health_score`, `error_count`, `auth_error_count`, `cooldown_until`,
  `last_used_at`, `last_error`, `total_requests`, `total_success`, `total_failed`.
- `platform_core/api_keys.py`: `tao_key/sua_key/xoa_key/lay_key_theo_id/liet_ke`,
  `dat_credential`(mã hoá qua `core/token_store` bằng `LTT_TOKEN_ENCRYPTION_KEY`),
  `key_preview` (4 số cuối). KHÔNG hàm nào trả credential thô ra ngoài.
- Migration bảng `api_keys`.
- **Test:** mã hoá round-trip; `key_preview` không lộ secret; categories nhiều giá
  trị; liệt kê lọc theo provider/category.

### H8.2 — Provider Registry (một chỗ)
- `platform_core/providers.py`: dataclass `Provider` {`id`, `auth_style`
  (query_key|bearer|x_api_key), `base_url` mặc định, `categories`, `models:
  list[ModelInfo]`, `list_models_path` (None nếu không có)} + `ModelInfo` {`id`,
  `provider_model_id`, `endpoint`/`endpoint_id`, `categories`, `is_active`,
  `credit_cost` (hàm, tuỳ)}. Tách 3 ID (bài học ModelArk).
- Seed: `gemini` (query_key, chat+image+model_control), `apiai`/`cheapkeyai`
  (bearer OpenAI-compat, chat+image, có `/v1/models`), `byteplus` (bearer, video,
  async), `plenx` (x_api_key, video, async).
- **Test:** toàn vẹn registry; auth_style đúng từng provider; model thuộc đúng
  category; không hardcode tên app.

### H8.3 — Allocator gọn
- `platform_core/api_pool.py`: `lay_key(db, provider, *, category=None, model=None)`
  → chọn key `enabled && status∈{active}` (bỏ cooldown chưa hết/disabled), khớp
  provider + (model ∈ supported_models hoặc supported_models rỗng), sắp theo
  `priority desc, total_requests asc`; tự hồi cooldown khi hết hạn. (Key CHIA SẺ
  được cho nhiều request — KHÔNG cần khoá độc quyền như job.)
- `danh_dau_thanh_cong(key)` / `danh_dau_loi(key, http_status, retry_after)`:
  401/403→`auth_error_count++`, disable sau 5 liên tiếp; 429→cooldown theo
  retry-after (mặc định 60s), status exhausted/cooldown; 4xx→KHÔNG phạt; 5xx→error.
- **Test:** chọn đúng key theo priority; bỏ key cooldown; disable sau 5 lần 401;
  429 đặt cooldown; 4xx không phạt; ThieuKeyError khi không có key khả dụng.

### H8.4 — Menu quản trị APIKEYS
- `server/admin.py`: `ApiKeyAdmin` (ModelView, `column_list` gồm `key_preview`,
  provider, categories, status, priority — TUYỆT ĐỐI không cột credential;
  form thêm/sửa có ô nhập credential ghi-mã-hoá, đọc chỉ preview) + view tuỳ biến
  **"Test key"** (probe sống: gọi `/v1/models` hoặc 1 call rẻ theo provider) +
  actions bật/tắt/reset-cooldown. View **"Models"** (registry, chỉ đọc) + nút
  "Làm mới model" cho provider có `list_models_path`.
- **Test:** chỉ admin vào; HTML không chứa credential thô; test-key trả trạng
  thái; bật/tắt đổi `enabled`.

### H8.5 — Import 6 key từ BOT GEMINI (một lần)
- `tools/import_api_keys_from_botgemini.py`: đọc `D:\BOT GEMINI\data\api_keys.json`,
  giải mã bằng `FERNET_KEY` của BOT GEMINI (đọc từ env/.env của nó) → map trường
  → mã hoá lại bằng `LTT_TOKEN_ENCRYPTION_KEY` → INSERT. Mang theo `base_url`,
  `supported_models`. Secret KHÔNG ghi log/đĩa (chỉ 4 số cuối). Idempotent theo
  (provider, key_preview). Chạy một lần trên máy chủ.
- **Nghiệm thu:** 6 key vào bảng, `/admin` APIKEYS hiện 6 dòng, Test key xanh.

### H8.6 — Đấu thumbnail dùng bộ máy key
- `apps/thumbnail/jobs.py`: thay `os.environ["GEMINI_API_KEY"]` bằng
  `api_pool.lay_key(db, "gemini", category="image", model=...)`; gọi
  `danh_dau_thanh_cong/loi` theo kết quả. Fallback env khi không có key (dev/test).
- **Test:** thumbnail lấy key từ engine (mock allocator); lỗi 429→đánh dấu cooldown.

### H8.7 — Tài liệu + nghiệm thu
- Cập nhật `docs/03_THEM_APP_MOI.md` (app xin key qua `api_pool`, không đọc env),
  `docs/KHAO_SAT_APIKEYS.md` (đánh dấu Pha 1 xong), NHAT_KY.
- Full `pytest -q` + scan 0 + **kiểm trình duyệt** menu APIKEYS (thêm/test/tắt).

### Thứ tự & tiêu chí xong H8 (Pha 1)
H8.1→H8.2→H8.3→H8.4→H8.5→H8.6→H8.7; mỗi bước xanh test mới sang bước sau. **Xong
Pha 1 khi:** admin quản mọi key ở `/admin` APIKEYS (4 category), 6 key đã import +
Test key xanh, thumbnail chạy bằng key từ engine (không còn env), full suite xanh
+ scan 0. **Pha 2 (sau):** telemetry rpm/tpm/token, cascade đa-provider, làm mới
model tự động.

---

## H9 — Thanh toán *(chốt 2026-08-01: PayOS + agnostic — xem Q31)*

**Quyết định (Q31):** cổng **PayOS** (VietQR + webhook chữ ký), kiến trúc
**agnostic** (đăng ký cổng như Provider Registry). Tỉ giá **1 credit = 100đ**
(100.000đ = 1.000 credit). Gói nạp có **bonus theo %**, admin sửa được. **Mọi tiền
đi qua `credit.nap` (sổ H3)** — không đường tắt. Đơn hàng **idempotent** (webhook
lặp không cộng đôi). Credential ở `secrets\app.env` (`LTT_PAYOS_*`), vắng → adapter
tắt mềm (dev/test vẫn chạy).

### H9.1 — Model + toán tiền
- `models.py`: `CreditPackage` (name, price_vnd, credits_base, bonus_percent,
  sort_order, active) + `PaymentOrder` (order_code UNIQUE int cho PayOS, user_id,
  package_id, price_vnd, credits (tổng đã gồm bonus), bonus_percent snapshot,
  status pending/paid/expired/cancelled/failed, gateway, gateway_ref, checkout_url,
  paid_at, credited flag, created_at, expires_at, note). Hằng `ORDER_*`.
- `platform_core/billing_math.py`: `credits_base_tu_vnd(vnd)` = vnd//100;
  `bonus_credits(base, pct)` = base*pct//100; `tong_credits(base, pct)`.
- Migration (chain từ `e9f0a1b2c3d4`). Seed vài gói mặc định (admin sửa sau).
- **Test:** toán base/bonus/tổng; ràng buộc gói; order_code duy nhất.

### H9.2 — Cổng agnostic + adapter PayOS
- `platform_core/payments/__init__.py`: giao diện `Gateway` {`id`, `tao_thanh_toan
  (order) -> {checkout_url, qr, ref}`, `xac_thuc_webhook(headers, raw_body) ->
  {order_code, paid, ref}`} + registry `GATEWAYS`.
- `payments/payos.py`: tạo payment link (POST PayOS, ký HMAC-SHA256 checksumKey);
  verify webhook (ký lại data sắp theo khoá, so `signature`). Đọc `LTT_PAYOS_CLIENT_ID
  /API_KEY/CHECKSUM_KEY` từ env; vắng → `GatewayChuaCauHinh` (tắt mềm).
- **Test:** ký + verify round-trip (khoá test); chữ ký sai bị từ chối; thiếu env → tắt mềm.

### H9.3 — Nghiệp vụ đơn (billing service)
- `platform_core/billing.py`: `tao_don(db, user, package, gateway)` → PaymentOrder
  pending + gọi gateway → checkout_url; `ghi_nhan_tra(db, order_code, ref)`
  **idempotent** (đã credited thì bỏ qua) → `credit.nap(user, credits)` + paid;
  `het_han_don`; `liet_ke_don`. Khoá theo order để không cộng đôi.
- **Test:** vòng đời đơn; idempotent (gọi 2 lần chỉ cộng 1); hết hạn; số dư khớp.

### H9.4 — Trang /nap (người dùng)
- `server/routes/billing.py`: `/nap` (gói + base+bonus+tổng + nút Nạp) → tạo đơn →
  hiện **VietQR + thông tin CK + mã đơn** ở `/nap/don/<id>`, HTMX poll trạng thái →
  khi paid hiện thành công + số dư mới. Wire header **Bảng giá**→`/nap`, **Nạp thêm**→`/nap`.
- **Test:** trang cần đăng nhập; tạo đơn ra QR; poll trả trạng thái.

### H9.5 — Webhook
- `server/routes/webhooks.py`: `POST /webhooks/payment/payos` — verify chữ ký,
  tìm đơn theo order_code, `ghi_nhan_tra` idempotent, trả 200. **Miễn CSRF** (API,
  không phải form) nhưng **bắt buộc chữ ký**. Log gọn, không ghi secret.
- **Test:** chữ ký hợp lệ → cộng credit; sai → 400 không cộng; lặp → không cộng đôi.

### H9.6 — Admin sâu (quản trị thanh toán)
- Console **Gói nạp** (CRUD: giá/credit/bonus%/bật/thứ tự) — dark như APIKEYS.
- Console **Đơn hàng** (lọc theo trạng thái, xem chi tiết, **Đánh dấu đã trả** tay
  = dự phòng khi webhook lỗi, đi qua `ghi_nhan_tra` nên vẫn idempotent).
- **Doanh thu** (tổng VND đã thu, tổng credit đã bán, theo ngày).
- **Test:** chỉ admin; CRUD gói; mark-paid cộng credit đúng + không đôi.

### H9.7 — Nghiệm thu
- Full `pytest -q` + scan 0 + deploy `setup\2` + migration + **kiểm trình duyệt**
  `/nap` (ra QR) + `/admin` Gói/Đơn. Cập nhật NHAT_KY + tài liệu.

### Thứ tự & tiêu chí xong H9
H9.1→…→H9.7; mỗi bước xanh test mới sang bước sau. **Xong khi:** user nạp được
(gói+bonus), PayOS webhook cộng credit idempotent qua sổ H3, admin quản gói+đơn+
doanh thu, migration production, full suite xanh + scan 0 + kiểm trình duyệt.

> **Ghi chú lịch sử (trước khi chốt):** cần cổng nào (VNPAY/MoMo/CK webhook), hoá
> đơn, hoàn tiền — nay chốt PayOS + agnostic (Q31). Hoá đơn VAT: hoãn tới khi cần.

---

## H10 — File lớn (R2) *(chưa chốt)*

Bắt buộc trước khi làm bất kỳ tool nào thuộc nhóm FFmpeg hoặc GPU
(`auto_sub_video`, `concat_pro`, `cut_clip_short`, `video_upscale`).

- Trình duyệt upload **thẳng** lên R2, không đi qua máy chủ — trần 100 MB của
  Cloudflare nằm ở đường qua máy chủ
- Thêm backend R2 vào `platform_core/storage.py`, **không sửa app nào**
- **Hiện thực `Storage.url_for(key)`** (hoãn từ H7 Wave 2): LocalStorage trả route
  app hiện tại, R2Storage trả **presigned URL** để trình duyệt tải thẳng từ CDN.
  App đổi sang `RedirectResponse(url_for(...))` thay vì stream qua tunnel bằng
  `open()` (đang làm ở thumbnail) — nếu không, file lớn vẫn nghẽn 100 MB/100 s.
  Docstring `storage.py` đã hứa `url_for` nhưng CHƯA có — H9 là lúc lấp.
- Kiểm duyệt file người lạ tải lên trước khi đưa vào FFmpeg — file media dị
  dạng là đường thực thi mã có thật

---

## H11 — Thêm tool

Theo thứ tự khuyến nghị trong `KHAO_SAT_BOT_GEMINI.md`:

1. `youtube_script` (139 dòng — rẻ nhất để kiểm chứng lại hợp đồng app)
2. `seedance_video` (5.508 dòng — giá trị thương mại cao nhất; cần H7)
3. `plenx` (2.731 dòng — cùng cấu trúc, port chung một lượt)
4. Nhóm FFmpeg / GPU (cần H7)

**Không đưa lên nền tảng:** mọi module dùng cookie hoặc trình duyệt
(`whisk_nano` và 16 module đã archive). Lý do đầy đủ ở `KHAO_SAT_BOT_GEMINI.md`
nhóm D.

---

## H12 — LTT Agent AI + Canvas + full tool ảnh/text/video/GPU ✅

**Đã chốt phạm vi Q49/Q39 (2026-08-02):** xây hoàn chỉnh Agent + Canvas, không
hoãn Canvas và không cắt video/GPU khỏi sản phẩm cuối. Kiến trúc giao diện hybrid:
Jinja/HTMX giữ cho trang thường; Canvas dùng React + TypeScript + `@xyflow/react`,
Vite build static asset do FastAPI phục vụ; không có Node runtime production.

Kế hoạch triển khai duy nhất: `docs/AGENT_LTT/02_LO_TRINH.md` — P0→P13, mỗi phase
có entry gate, PASS gate, test, browser/PostgreSQL check và rollback. Đặc tả:
`docs/AGENT_LTT/01_DAC_TA_AGENT.md`; thiết kế thi công:
`docs/AGENT_LTT/06_XAY_DUNG_APP_AGENT.md`.

- [x] P0 Quyết định còn lại + baseline — 2026-08-02: 1710 pass, scan 0, lint 0/0
- [x] P1 ToolSpec core — 2026-08-02: 34 test hẹp; full 1721 pass, scan 0, lint 0/0
- [x] P2 ToolSpec cho 7 app job-based — 2026-08-02: 113 test app; full 1752 pass, scan 0, lint 0/0
- [x] P3 AgentRun/checkpoint/fan-out — 2026-08-02: PG up/down/up + concurrency + restore; full 1759 pass
- [x] P4 Planner/normalizer/validator — 2026-08-02: 81 test hẹp; full 1781 pass, scan 0, lint 0/0
- [x] P5 Budget/approval/credit atomic — 2026-08-02: SQLite 8 pass; PG 4 concurrency + migration/restore; full 1789 pass, scan 0, lint 0/0
- [x] P6 Executor/resume/fan-out — 2026-08-02: headless 6 pass; PG 5 concurrency + migration/restore; full 1795 pass, scan 0, lint 0/0
- [x] P7 Verifier/bounded retry — 2026-08-02: 55 test hẹp; full 1807 pass, scan 0, lint 0/0
- [x] P8 App/UX nghiệp vụ — 2026-08-02: 9 Playwright flow + 57 test hẹp; full 1815 pass, scan 0, lint 0/0
- [x] P9 React/Vite build foundation — 2026-08-02: Node 22.12.0, deterministic
  production bundle; Playwright console/network sạch; full 1821 pass, scan 0,
  10 app lint 0/0; release archive PASS
- [x] P10 Canvas data model/API — 2026-08-02: migration up/down/up + 6 PG
  concurrency/restore; 99 test hẹp; frontend 4 pass; Playwright API 200/201;
  full 1831 pass, scan 0, lint 0/0
- [x] P11 Node editor đầy đủ — 2026-08-02: frontend 12 pass; 16 test Python
  hẹp; Playwright desktop/mobile/keyboard/conflict/offline/100-node + drag/drop
  và disconnect PASS; full 1832 pass, scan 0, lint 0/0, npm audit 0
- [x] P12 Agent↔Canvas↔Run + video/GPU E2E — 2026-08-02: 64 test hẹp,
  frontend 13 pass; 7 ToolSpec production-like + R2/resume/verifier PASS;
  Playwright prompt→done/run-again/cancel/insufficient-credit PASS; full 1835
  pass, scan 0, lint 0/0, npm audit 0
- [x] P13 Hardening/rollout production — 2026-08-02: backup đầy đủ + `pg_dump`
  sang ổ D; migration production và health loopback/Cloudflare PASS; rollout
  `off → admin → allowlist → public`; admin canary chạy Canvas thật `done`
  (estimated/actual 7/7), hai user thường tạo run rồi cancel; metrics production
  estimated/actual/refund 21/15/6. Playwright cuối console 0/network 0 lỗi;
  full 1849 pass, 8 skip, 23 subtest; scan 0; strict lint 0/0; frontend 13 pass.

Không đánh dấu phase ở file này độc lập: chỉ đồng bộ từ bảng bằng chứng trong
`AGENT_LTT/02_LO_TRINH.md` sau khi test thật PASS.

---

## H13 — Chương trình thiết kế lại giao diện app từ ảnh tham khảo

Quy trình duy nhất: `docs/QUY_TRINH_THIET_KE_LAI_GIAO_DIEN_APP.md` (Q45).

- [x] H13.0 Chuẩn hóa UI-RD v1.0 — 2026-08-02: pipeline R0–R10, ma trận
  giữ/bỏ/xây, gate G0–G7, chế độ ANALYZE/BUILD/FULL và cơ chế cập nhật quy tắc.
  Playwright catalog production desktop/mobile: console 0, failed request 0;
  phát hiện baseline mobile overflow ở 390 px. Đây là nghiên cứu/tài liệu, chưa
  sửa giao diện app. Full suite 1851 pass, 8 skip, 23 subtest; secret scan 0.
- [x] H13.1 Nhận app đầu tiên + ảnh tham khảo; tạo hồ sơ UI-RD — 2026-08-02:
  `UI_REDESIGN/home/` gồm brief, map reference, ma trận feature và plan thực thi.
- [x] H13.2 Audit authenticated và chốt ma trận tính năng — 2026-08-02: Q46 khóa
  public catalog/marketplace authenticated, owner-scoped jobs, credits thật,
  popular aggregate và các phần bị hoãn.
- [x] H13.3 Prototype desktop/mobile và visual target — 2026-08-02: shell 5 cột
  desktop và grid 390 px không tràn ngang; artwork là crop từ ảnh user cung cấp.
- [x] H13.4 Xây lát cắt dọc, test nghiệp vụ + visual regression — 2026-08-02:
  test isolation activity/running job; browser desktop/mobile, Ctrl+K, filter/sort
  PASS; không phát sinh migration.
- [x] H13.5 Nghiệm thu G0–G7 và rollout đúng phạm vi yêu cầu — 2026-08-02:
  local release gate PASS (1852 pass, scan 0, lint 0/0); production backup,
  release update, migration no-op, health và Cloudflare browser PASS.

Mỗi app sau dùng nhánh H13.`<slug>` riêng. Chỉ PASS khi có hồ sơ bằng chứng,
test thật và browser thật theo UI-RD.

### H13.taovideo — UI-RD Seedance / Tạo video AI

- [x] R0–R3.5 Audit và Decision Gate chuẩn bị — 2026-08-02: xác nhận ảnh tham
  khảo thuộc app `/taovideo`; hồ sơ `docs/UI_REDESIGN/taovideo/` đã map code,
  dữ liệu thật và feature chưa có.
- [x] Decision Gate đã khóa — 2026-08-02: Dev trả lời 9 lựa chọn; Seedance giữ
  app/route hiện hành, xây studio trên dữ liệu/job thật và tích hợp Upscale qua
  popup quote/confirm credit dùng chung `submit_upscale_job()`.
- [x] R4–R7 Contract, design và lát cắt dọc — **đã đóng** *(đo lại 07/09/2026)*.
  Dòng cũ ghi *"WIP, chưa commit/deploy … đang có code dở"*; cả ba mệnh đề của
  nó nay **đều sai**, mỗi cái có một phép đo riêng:
  - *studio* — `apps/taovideo/templates/taovideo.html` có `tv-studio` (dòng 6)
    và hợp đồng `immersive` (dòng 2).
  - *filter/history owner-scoped* — `apps/taovideo/routes.py:60`:
    `select(Job).where(Job.user_id == u.id, Job.app_slug == MANIFEST.slug)`,
    cùng `tv-library-filters` (template dòng 76).
  - *cầu Seedance→Upscale* — vào kho ở `a8058e3f`, và **đang chạy trên
    production**: `git show 9f555599:apps/taovideo/routes.py` có cả hai dòng
    549/578.

  Điều kiện đóng do chính dòng này đặt ra — *"phải đóng theo UP1/UP3"* — cũng
  đã thoả: **UP1** và **UP3** đều `[x]` ngay bên dưới trong chính tệp này.

- [ ] R8–R10 Nghiệm thu đa state/viewport, full gate, memory và release.
  ⚠️ **Đo lại 07/09: ô này đúng một nửa — giữ mở, nhưng thu hẹp lại.**
  - *release* — **xong**: mã này có trong `9f555599`, và vẫn còn trong
    `0ad9c868` — bản **đang chạy trên production** (deploy 07/09 09:13).
  - *viewport* — **xong**, và vừa đo lại: `taovideo` nằm trong lượt quét 24
    route ngày 07/09 (bộ quét lấy route từ **registry**, không chép tay), chạy
    trên **cả WebKit lẫn Chromium**, 0 tràn ngang — `BAN_GIAO_S1_S7_2026-09-07.md`.
  - *đa state* (`empty/queued/running/done/error/cancelled`) và *memory* —
    **chưa có phép đo nào từ cây này**. Đó là phần còn lại thật của ô.

  ⭐ Không tick cả ô dù hai trong bốn vế đã xong: `04_IMPLEMENTATION_PLAN.md`
     mục 5 ghi `[x]` cho toàn bộ, nhưng đó là **một tệp chép tay** — chính cơ
     chế đã nói sai năm lần ở `CLAUDE.md`. Tick theo nó là tin lời khai, không
     phải tin phép đo.

### H13.upscalevideo — UI-RD Upscale Video Studio

Nguồn kế hoạch chi tiết: `docs/UI_REDESIGN/upscalevideo/04_IMPLEMENTATION_PLAN.md`.
Decision Gate đã khóa theo Q47; **không đóng băng tính năng mới**. Full scope gồm
batch tối đa 3, Watch Folder, compare thật, cancel/refund, telemetry admin và
cầu Seedance; Pause/delete và AI Detail chưa có engine được quản lý bằng DEFER.

- [x] UP0a Audit lại hội thoại, ảnh và code; khóa Q47 + hồ sơ UI-RD — 2026-08-02.
- [x] UP0b Baseline browser/state + phân loại WIP/rollback — 2026-08-02: fixture
  cô lập có Seedance done và Upscale running/done/error; source/output Range 206,
  console 0, request ứng dụng không lỗi. Mobile đầy đủ tiếp tục gate UP2/UP8.
- [x] UP1 Contract lifecycle cancel/refund + Seedance quote/confirm dùng chung —
  2026-08-02: cooperative cancel xuống NCNN/FFmpeg; race cancel-vs-error không
  retry; owner/CSRF/refund-idempotent; 50 test web/core và 67 regression nhóm pass;
  Playwright quote 3 credit → job queued → cancel → credit phục hồi PASS.
- [x] UP2 Studio shell + upload R2/local + quote + option FPS/audio thật —
  2026-08-02: desktop/mobile không overflow; video Downloads được probe, preview
  và quote thật; 53 test lát cắt PASS, console 0.
- [x] UP3 Compare nguồn/kết quả owner-scoped — 2026-08-02: source Seedance và
  upload trực tiếp, Range 206, owner khác/missing artifact 404; browser PASS.
- [x] UP4 Batch tối đa 3, preflight và transaction job/credit — 2026-08-02:
  1–3 file, file thứ 4, owner, thiếu credit rollback và double-submit PASS.
- [x] UP5 Watch Folder qua Watch Agent Windows có token scope/dedupe/quarantine
  — 2026-08-02: stable polling, R2/local, restart dedupe, revoke/pause,
  archive/quarantine và install/uninstall PowerShell ASCII PASS.
- [x] UP6 Telemetry admin + progress/ETA dựa số đo thật — 2026-08-02: role gate
  PASS; GPU/VRAM/temp/queue/storage thật; ETA chỉ hiện sau ít nhất 3 mẫu.
- [x] UP7 Benchmark AI Detail; Pause/delete tiếp tục DEFER nếu chưa đủ contract
  — 2026-08-02: benchmark RTX 5060 Ti hoàn tất, AI Detail **DEFER** đúng Q47 vì
  chưa có engine temporal riêng đạt acceptance; không giả lập bằng Quality.
- [x] UP8 GPU smoke + full test/scan/lint/Playwright + backup/release/deploy —
  2026-08-02: local GPU smoke PASS; 1869 test + 23 subtest PASS, scan 0;
  backup/restore catalog PASS; production canary 2 job done, desktop/mobile và
  console sạch; health loopback/Cloudflare ready. Browser R2 direct giữ off theo
  Q48 đến khi bucket CORS được cấp quyền cấu hình.

### H13.autosubvideo — UI-RD Auto Sub Video Studio

Nguồn hồ sơ: `docs/UI_REDESIGN/autosubvideo/`. Ảnh tham khảo 1680×935 mô tả
subtitle editor đầy đủ, trong khi app hiện tại mới là form burn transcript có sẵn.

- [x] R0–R4 ANALYZE — 2026-08-02: audit ảnh, browser desktop/mobile, code app,
  engine/job/credit/storage, `D:\BOT GEMINI` chỉ-đọc và nguồn công nghệ chính thức;
  tạo brief/current-state/reference-map/feature-matrix/plan AS0–AS9. Baseline
  1440×900 + 390×844 không overflow, console 0, `/estimate` 200.
- [x] R3.5 Decision Gate — 2026-08-02: Dev khóa 1C/2A/3B/4A/5A/6A/7A/
  8B/9A/10C/11C/12B thành Q49–Q50: Quick + Full Editor, React island,
  `AppProject`, WhisperX/pyannote/Gemini, multi-track/full mobile, chỉ render tính
  credit và mở thẳng public sau toàn bộ gate.
- [x] AS0 baseline/contract/rollback — 2026-08-02: khóa container `AppProject`
  generic, payload Auto Sub v1, multi-track/job/credit/flag contract, 11 state fixture
  và 4 viewport; chưa sửa runtime/migration.
- [x] AS1 `AppProject` runtime — 2026-08-02: additive model/migration/service/API,
  owner 404, CSRF, ETag/revision conflict, archive mềm, payload limit/secret guard,
  Auto Sub schema v1/multi-track; 127 targeted regression PASS, scan 0.
- [x] AS2 upload/import + WhisperX — 2026-08-02: import vào revision; transcription
  job 0-credit có owner/CSRF/dedupe, 12 lượt/ngày, user-row lock, 120 phút/job,
  cooperative cancel và conflict artifact. Sidecar cô lập Torch 2.8 cu128 khỏi
  Torch 2.11 nền tảng; RTX 5060 Ti CUDA PASS; smoke VI 30s `large-v3` aligned,
  19,36s/RTF 0,645; 96 regression PASS, scan 0.
- [x] AS3 React Studio shell/project/upload — 2026-08-02: Vite/React island có
  hashed production bundle + build-meta, project load/create/autosave/revision,
  source upload/import/transcribe action và legacy rollback. 128 regression +
  5 frontend test PASS; Playwright file thật desktop/mobile, overflow 0,
  console 0, mọi request 2xx/206.
- [x] AS4 editor cue + multi-track timeline/waveform/undo-redo/full mobile drag —
  2026-08-02: import fixture 3 cue, sửa/tách/undo/redo/autosave và pointer drag
  desktop/mobile PASS; WebAudio waveform thật, fallback an toàn; 7 frontend test
  PASS, document overflow 0, console/network sạch.
- [x] AS5 style/template/animation có preview-render parity — 2026-08-02:
  typed style schema/hex guard, 8 preset từ server, full inspector, karaoke và
  none/fade/pop/slide-up dùng chung contract React/ASS. 23 backend + 7 frontend
  test PASS; Playwright desktop/mobile style autosave, console/network sạch.
- [x] AS6 diarization/translation và workflow auxiliary 0-credit — 2026-08-02:
  Pyannote Community-1 sidecar/in-memory audio + speaker overlap, Gemini structured
  JSON chunk translation, project revision/artifact, quota/dedupe/cancel/job status
  và honest capability UI. 102 regression + 7 frontend PASS; token/key local thiếu
  nên browser xác minh soft-disable, không gọi giả dịch/phân vai.
- [x] AS7 render snapshot/quote/credit/output/job control — 2026-08-03:
  immutable revision snapshot + SHA-256, server quote/confirm/hold, multi-track
  ASS và SRT/VTT/JSON/ZIP, source/720p/1080p/4K, MP4/MKV/WebM, measured ETA,
  cancel kill FFmpeg + refund, retry snapshot, owner artifact; 29 backend +
  8 frontend PASS; Playwright desktop/mobile popup/submit/cancel, overflow 0,
  console/network sạch.
- [x] AS8 hardening/performance/corpus/GPU/end-to-end — 2026-08-03: sửa deadlock/
  timeout process tree WhisperX và ASS override injection; 3 GPU render thật
  720p/1080p/4K NVENC + credit/artifact PASS; A/B tiny/large-v3 aligned; 3.000 cue
  xuất đủ artifact trong 0,438s/8,98 MB; 170 backend + 9 frontend PASS, scan 0;
  Playwright 4 viewport, offline recovery, accessibility, console/network sạch.
- [x] AS9 full gate/release/deploy — 2026-08-03: final full suite 1.894 PASS,
  8 skip/23 subtest, scan 0, pip/npm audit/lint/build/migration/backup-restore
  PASS; PostgreSQL lên `d4e5f6a7b8c9`; rollout public. Production canary video
  thật upload/import/quote 1 credit/render GPU/artifact PASS; 4 viewport overflow
  0, console/network sạch. Canary còn bắt và khóa 4 lỗi deploy/R2 bằng regression.

---

## Việc phải làm ngay ở phiên tiếp theo

`H13.autosubvideo` AS0–AS9 đã hoàn thành và đang public trên production. Việc kế
tiếp là theo dõi telemetry/job thực tế và chỉ bật browser R2 direct sau khi bucket
CORS vượt browser gate Q48. Hạ tầng
độc lập còn việc cấu hình bucket CORS rồi mới bật cờ Q48 cho browser upload >90MB.

---

## H14 — Chuẩn audit chất lượng app

- [x] H14.0 LTT-AQA v1.0 — 2026-08-03: khóa Q51; tạo
  `docs/quy_tac_audit.md` với score Q/M/E, gate G0–G8, control registry,
  benchmark thế giới, pipeline A0–A10 và ưu tiên roadmap; tạo bộ 8 template tại
  `docs/APP_AUDIT/_MAU/`; liên kết một chiều audit → UI-RD. Đây là thay đổi tài
  liệu/quy trình, không sửa runtime hoặc deploy. Test khóa tài liệu 94 pass;
  full suite 1.896 pass, 8 skip, 23 subtest; secret scan 0 finding.

---

## H15 — Đồng nhất giao diện và nâng cấp sản phẩm toàn nền tảng

Nguồn audit/roadmap/vé:
`docs/APP_AUDIT/platform/2026-08-03/`. Q52 khóa LTT Carbon Red và thứ tự
system-first, không làm nhiều app song song.

Tiến độ H15 hiện tại: **37/38 vé (97,4%)**; **15/16 stage hoàn tất**. Phần
WordPress production đã tách sang backlog không chặn `DEFERRED-WP-001` theo
Q60; bước tuần tự tiếp theo là H15.S15 DEEP re-audit + full release gate.

- [x] H15.AUDIT Inventory + production browser + market baseline — 2026-08-03:
  kiểm kê 11 module, toàn bộ route/trang control plane và website source; 25 bề
  mặt production authenticated/public render 200; phát hiện public mobile overflow
  48 px, a11y target/label debt, bốn style layer và website source/live mismatch.
  Score baseline Q70/M50/E86; backlog 38 vé và roadmap Stage 0–15 đã tạo.
  Gate tài liệu: 1.896 passed, 8 skipped, 23 subtests; secret scan 0 finding.
- [x] H15.S0 Design contract/harness — DS-001..005 — 2026-08-03:
  semantic token Carbon Red có compatibility alias; shell/component/a11y/icon/
  content contract được lưu tại `docs/DESIGN_SYSTEM_LTT.md`; focus, coarse touch
  target, reduced motion và Escape menu có regression guard. Browser local
  desktop/mobile PASS; full suite 1.901 pass, 8 skip, 23 subtest; secret scan 0.
- [x] H15.S1 Public catalog/Auth — PLAT-001, AUTH-001 — 2026-08-03:
  catalog 390 px overflow 13→0; public search/mobile menu có accessible name;
  login/register/forgot/reset/verify dùng chung Carbon Red auth shell, label và
  announced error/success states. Browser desktop/mobile PASS; 1.907 passed,
  8 skipped, 23 subtests; secret scan 0.
- [x] H15.S2 Billing/Jobs/Settings — BILL-001, JOBS-001, SET-001 — 2026-08-03:
  cả ba gate tuần tự đã PASS; 1.919 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S2.1 BILL-001 — 2026-08-03: báo giá, đơn, trạng thái và lịch sử 10
    đơn theo user; browser isolated desktop/mobile PASS; 1.910 passed, 8 skip,
    23 subtests; secret scan 0.
  - [x] H15.S2.2 JOBS-001 — 2026-08-03: filter/status, progress a11y,
    owner-only cancel/refund, retry/credit, opaque artifact download và error
    state; browser isolated PASS; 1.915 passed, 8 skip, 23 subtests; scan 0.
  - [x] H15.S2.3 SET-001 — 2026-08-03: Settings/Status operator-only dùng
    chung một nguồn quyền; IA thu gọn theo nhóm, a11y/mobile/browser PASS;
    1.919 passed, 8 skipped, 23 subtests; secret scan 0.
- [x] H15.S3 Home authenticated — HOME-001..002 — 2026-08-03: cả hai gate
  tuần tự PASS; 1.925 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S3.1 HOME-001 — 2026-08-03: marketplace shell dùng semantic
    Carbon Red; mobile drawer/account, filter state, progress a11y và keyboard
    Escape hoạt động; browser 390/1280 PASS; 1.922 passed, 8 skipped,
    23 subtests; secret scan 0.
  - [x] H15.S3.2 HOME-002 — 2026-08-03: My Apps dùng toàn bộ lịch sử owner;
    Agent Canvas trỏ năng lực thật; Mẫu/Tài nguyên/Cộng đồng DEFER rõ, không
    link giả; browser 390/1280 PASS; 1.925 passed, 8 skipped, 23 subtests;
    secret scan 0.
- [x] H15.S4 Tạo video AI — 2026-08-03: TV-UI-001 và TV-FEAT-001/002
  đều PASS tuần tự; 1.940 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S4.1 TV-UI-001 — 2026-08-03: shell/control/form/job card/empty
    state thống nhất; drawer/Escape/a11y và file-reference browser PASS;
    1.930 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S4.2 TV-FEAT-001 — 2026-08-03: asset library suy ra từ storage +
    job history owner-scoped; chọn lại asset, MIME/role/size/tổng-4 validation,
    batch atomic-before-write; browser file thật PASS; 1.935 passed, 8 skipped,
    23 subtests; secret scan 0.
  - [x] H15.S4.3 TV-FEAT-002 — 2026-08-03: prompt preview server-side,
    camera/motion/style guidance trung thực, provider seed, 2 variation và remix;
    browser desktop/mobile PASS; 1.940 passed, 8 skipped, 23 subtests; scan 0.
- [x] H15.S5 Upscale Video — 2026-08-03: UI → benchmark engine → motion/cost
  gate hoàn thành tuần tự; BUILD chống rung + smooth 2×, DEFER AI Detail/
  denoise/deblur/HDR có bằng chứng; 1.952 passed, 8 skipped, 23 subtests;
  secret scan 0.
  - [x] H15.S5.1 UP-UI-001 — 2026-08-03: mobile progressive settings,
    compare slider đồng bộ, queue status/progress semantics và telemetry live
    region; browser desktop/mobile + file thật PASS; 1.943 passed, 8 skipped,
    23 subtests; secret scan 0.
  - [x] H15.S5.2 UP-FEAT-001 — 2026-08-03: benchmark schema 2 chạy thật
    3 model × bicubic/noise/blur; hash binary/model và preflight dependency;
    cả AI Detail/denoise/deblur **DEFER có bằng chứng**, UI không mở giả;
    1.946 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S5.3 UP-FEAT-002 — 2026-08-03: libvidstab two-pass và
    minterpolate 2× nối quote/job/worker/result, cost 1,2×/2,2×; HDR DEFER vì
    không có SDR→HDR pipeline trung thực; browser/pipeline smoke PASS;
    1.952 passed, 8 skipped, 23 subtests; secret scan 0.
- [x] H15.S6 Auto Sub — 2026-08-03: UI polish → brand/transcript/speaker
  workflow hoàn thành tuần tự; 1.952 passed, 8 skipped, 23 subtests; scan 0.
  - [x] H15.S6.1 AS-UI-001 — 2026-08-03: React island dùng semantic Carbon
    Red chung; workflow step/status live có semantics; WhisperX/Pyannote/Gemini
    hiển thị capability trung thực; mọi control visible desktop/mobile đạt 44 px,
    overflow 0, console/network sạch; frontend 10 test và backend 35 test PASS;
    full suite 1.952 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S6.2 AS-FEAT-001 — 2026-08-03: LTT Brand preset server-driven
    có render parity; transcript QA chấm timing/nội dung/tốc độ đọc/line budget;
    speaker alias owner-project autosave và hiện xuyên cue list. Browser desktop/
    mobile PASS, alias còn sau reload; frontend 11 test, backend 35 test PASS;
    full suite 1.952 passed, 8 skipped, 23 subtests; secret scan 0.
- [x] H15.S7 Agent/Canvas — 2026-08-03: UI/run inspector → replay/debug/template
  → one-time schedule/version recovery hoàn thành tuần tự; 1.955 passed,
  8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S7.1 AG-UI-001 — 2026-08-03: Canvas dùng semantic Carbon Red,
    target ≥44 px; mobile tabs mở Canvas/Công cụ/Inspector; Run Inspector đọc
    checkpoint/cost/decision/artifact server-driven. Browser desktop/mobile
    overflow 0, console/network sạch; frontend 15 và backend 34 test PASS;
    full suite 1.952 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S7.2 AG-FEAT-001 — 2026-08-03: owner run history/detail và
    replay snapshot; clone/export/import template dùng contract sẵn có; cạnh
    error đi xuyên Canvas→Plan→validator→executor, nhánh không đạt điều kiện
    được skip tất định và lỗi đã xử lý có audit decision. Browser plan→quote→
    approve→done→replay PASS, console/network sạch; frontend 17 và backend 54
    test PASS; full suite 1.954 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S7.3 AG-FEAT-002 — 2026-08-03: `agent.advance` chạy nền bằng
    Job `next_run_at`, snapshot/quote/approval/hold trước lịch tối đa 30 ngày;
    server chặn tick sớm, cancel dọn orchestration job; run snapshot khôi phục
    thành workflow mới. Browser phát hiện và đã sửa toolbar overlay + early tick;
    schedule/recovery/console/network PASS; frontend 17 và Agent 111 test PASS;
    full suite 1.955 passed, 8 skipped, 23 subtests; secret scan 0.
- [x] H15.S8 Thumbnail — UI → reference/brand/score/remix handoff hoàn thành
  tuần tự; 1.957 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S8.1 TH-UI-001 — 2026-08-03: Thumbnail Studio dùng Carbon Red,
    form/control responsive, báo giá theo manifest; lịch sử owner-scoped có
    trạng thái/metadata/output thật và chọn so sánh tối đa hai ảnh. Browser
    desktop/mobile tạo 2 ảnh thật qua fixture cô lập, cost 10 credit, overflow 0,
    target visible ≥44 px, console/network sạch; regression 73 passed; full suite
    1.955 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S8.2 TH-FEAT-001 — 2026-08-03: reference ảnh owner-scoped có
    MIME/size/pixel validation và Gemini inline; Brand Kit lưu bằng AppProject;
    score kỹ thuật v1 từ output pixel thật; output remix trở lại Studio với
    ownership guard. Pixel editor DEFER theo Q54, không mở giả. Browser desktop/
    mobile PASS; regression 75 passed; full suite 1.957 passed, 8 skipped,
    23 subtests; secret scan 0.
- [x] H15.S9 Tạo ảnh — Studio/history/compare → reference/edit engine gate;
  1.965 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S9.1 IMG-UI-001 — 2026-08-03: Image Studio Carbon Red thay toàn
    bộ inline layout cũ; prompt counter/config preview/cost theo manifest;
    history owner-scoped có metadata/progress/error và compare tối đa hai output
    thật. Browser desktop/mobile tạo 2 ảnh 1024 px, overflow 0, target ≥44 px,
    console/network sạch; regression 65 passed; full suite 1.959 passed,
    8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S9.2 IMG-FEAT-001 — 2026-08-03: spike provider/cost/privacy chốt
    tại Q55; model ổn định + legacy alias, đơn giá model-specific, reference
    source/style owner-scoped có MIME/size/pixel validation; multimodal edit,
    semantic inpaint, outpaint, style transfer và output→edit handoff chạy thật.
    Precision mask DEFER minh bạch. Browser desktop/mobile PASS: quote 16 credit
    cho 2 ảnh Gemini 3.1 Flash, 2 output/edit link, overflow 0, console/network
    sạch; regression 41 passed; full suite 1.965 passed, 8 skipped, 23 subtests;
    secret scan 0.
- [x] H15.S10 Chat AI Studio — UI → project/file/search/export/branch hoàn
  thành tuần tự; 1.970 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S10.1 CHAT-UI-001 — 2026-08-03: Carbon Red shell/sidebar/search,
    empty/thread/message/image states và composer responsive; counter 20.000,
    Enter/Shift+Enter, status live và DOM SSE an toàn. Attachment hiện disabled
    với capability note, không giả backend. Browser SSE/credit/DB fixture PASS:
    100→97 credit, message còn sau reload, mobile overflow 0, console/network
    sạch; regression 15 passed; full suite 1.967 passed, 8 skipped, 23 subtests;
    secret scan 0.
  - [x] H15.S10.2 CHAT-FEAT-001 — 2026-08-03: conversation là project theo
    Q56; image/text/PDF attachment có type/size/context validation, vision input
    và owner Storage; search title/message, Markdown/JSON export, branch thread
    mới. Hosted File Search DEFER có bằng chứng. Browser file thật/search/export/
    branch/mobile PASS, console/network sạch; regression 13 passed; full suite
    1.970 passed, 8 skipped, 23 subtests; secret scan 0.
- [x] H15.S11 Kịch bản — tuần tự SCRIPT-UI-001 → SCRIPT-FEAT-001 hoàn thành;
  1.976 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S11.1 SCRIPT-UI-001 — 2026-08-03: Carbon Red composer với output
    outline, counter/cost; history 12 job owner-scoped; result workspace chia
    title/hook/sections/outro/metadata thành field chỉnh sửa trong phiên và
    copy/download Markdown. Persistence/version ghi rõ phase sau. Browser job/
    credit/history/editor/download/mobile PASS, console/network sạch; regression
    14 passed; full suite 1.972 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S11.2 SCRIPT-FEAT-001 — 2026-08-03: source/research giới hạn
    và prompt chống bịa nguồn; version AppProject owner-scoped với optimistic
    revision; shot list tất định từ script snapshot. Browser tạo job/lưu hai
    revision/reload/mobile PASS, credit 100→97, overflow 0, console/network sạch;
    regression 13 passed; full suite 1.976 passed, 8 skipped, 23 subtests;
    secret scan 0.
- [x] H15.S12 Clip ngắn — tuần tự CLIP-UI-001 → CLIP-FEAT-001 hoàn thành;
  1.983 passed, 8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S12.1 CLIP-UI-001 — 2026-08-03: source library owner-scoped từ
    Storage/Job, timed transcript và local range editor trung thực, compare tối
    đa hai output thật; Carbon Red responsive/status/a11y. Browser file MP4 thật
    tạo 2 clip, quote/settle 12 credit, mobile overflow 0, console/network sạch;
    regression 11 passed; full suite 1.980 passed, 8 skipped, 23 subtests;
    secret scan 0.
  - [x] H15.S12.2 CLIP-FEAT-001 — 2026-08-03: score rationale/breakdown
    từ engine có disclaimer; bốn brand preset nối render thật; AppProject lưu
    package/revision owner-scoped và ZIP video+SRT+metadata cho TikTok/Shorts/
    Reels không render/phí lặp. Browser file MP4 thật, revision 1→2, reload và
    download ZIP PASS; mobile overflow 0, console/network sạch; regression
    14 passed; full suite 1.983 passed, 8 skipped, 23 subtests; secret scan 0.
- [x] H15.S13 Admin/operator — 2026-08-03: ADM-001 hợp nhất custom console và
  SQLAdmin theo Carbon Red; dense table, skip link, semantic nav, active state,
  mobile menu và scroll containment. Browser desktop/mobile PASS, overflow 0,
  console/network sạch; regression 10 passed; full suite 1.985 passed,
  8 skipped, 23 subtests; secret scan 0.
- [x] H15.S14 Website marketing route/deploy — phần control plane hoàn thành;
  phần WordPress được chủ sản phẩm chủ động hoãn sang `DEFERRED-WP-001` theo Q60.
  - [x] H15.S14.1 WEB-001 — khóa route map đủ 40/40 trang static ↔ WordPress
    pretty URL; giữ chính xác hai OAuth callback `.html`; `/vi/` fallback về
    `/` thay vì route sản phẩm sai. Production browser/REST inventory xác nhận;
    contract 3 passed, static reference 761 passed; full suite 1.988 passed,
    8 skipped, 23 subtests; secret scan 0.
  - [x] H15.S14.2 WEB-002 — 2026-08-03: runtime dùng một PUBLIC_LINKS pretty
    URL; footer chung App/Support/Legal/Commerce trên public/auth/app; config
    Privacy/Terms bỏ URL `.html`; contract CTA WordPress ↔ control plane sẵn
    cho deploy. Browser desktop/mobile overflow 0, console/network sạch;
    regression 36 passed; full suite 1.991 passed, 8 skipped, 23 subtests;
    secret scan 0.
  - [x] H15.S14.3 WEB-003 — 2026-08-04: nghiệm thu phạm vi control plane và
    bàn giao gói WordPress; activation production tách sang backlog Q60.
    - [x] Build release 1.149 file/173,2 MB, secret 0; backup PostgreSQL; deploy
      `C:\LTTPlatform`; migration/health/services/Cloudflare PASS; production
      catalog/login desktop-mobile overflow 0, console/network sạch.
    - [x] Plugin WordPress redirect/CTA data-free + rollback và crawler gate;
      contract 3 passed; full suite 1.994 passed, 8 skipped, 23 subtests.
    - [x] Ghi rõ trạng thái chưa deploy WordPress, rollback và điều kiện mở lại;
      không coi phần bị hoãn là đã hoàn tất production.
- [x] `DEFERRED-WP-001` (Q60, không chặn H15.S15) — 2026-08-06: đã sao lưu
  toàn bộ 7.779 file WordPress (501,57 MiB), database 21 bảng/13.603 dòng và
  danh sách plugin active trước thay đổi; build/upload/activate integration
  plugin 1.0.2 từ commit `5671435`, checksum local/host khớp. Public audit
  **30 fail → 0 fail** sau khi purge LiteSpeed/object cache. Chromium thật
  desktop 1366×900 và mobile 390×844: HTTP 200, overflow 0, console 0,
  request hỏng 0; CTA tới `https://app.lttstudios.com/`, login form hiển thị;
  ba alias mẫu chuyển đúng. Hai OAuth callback giữ nguyên SHA-256 so với
  baseline. Bản 1.0.1 còn trên host ở thư mục rollback.
  - **Kiểm chứng độc lập từ máy nguồn (2026-08-06):** chạy lại
    `audit_public_web.py` từ máy này — `canonical targets: 13 | failures: 0`,
    khớp con số máy làm web báo. Bốn alias mẫu trả 301 đúng đích; trang chủ
    desktop 1366 + mobile 390 đều 0 tràn ngang / 0 lỗi console / có CTA; hai
    OAuth callback trả **200 không chuyển hướng**.
    Ghi lại một báo động giả của Claude: grep rộng báo "wp-login còn lộ ở trang
    chủ", hoá ra chỉ là tên biến CSS `--wp-admin-theme-color`. Phép kiểm của
    `audit_public_web.py` mới là cái có thẩm quyền, không phải grep tuỳ hứng.
- [x] H15.S15 DEEP re-audit + full release gate — **đóng 07/09/2026**, xem
  phép đo ở `LAYOUT-001` bên dưới (phát hiện **duy nhất** của lượt re-audit).
  - [x] H15.S15.1 `LAYOUT-001` — checkpoint 2026-08-04, **đóng 07/09/2026**:
    thêm hợp đồng `standard/catalog/wide/immersive`; mở
    rộng Seedance, Upscale, Auto Sub, Agent Canvas và năm workspace `wide`;
    bỏ margin âm ở Upscale/Auto Sub; rebuild bundle Auto Sub.
    - [x] Targeted gate: `tests/test_129_adaptive_page_layouts.py` 3 passed;
      Auto Sub frontend 11 passed + typecheck/build pass.
    - [x] Browser fixture 8118: 9 app × 7 viewport 1920→390, overflow toàn
      trang 0; desktop/mobile đã xem; console 0 error/0 warning; không request
      4xx/5xx. Tại 1720 px immersive root 1.657 px, wide root 1.552 px.
    - [x] Bộ test đầy đủ — **đã xanh, trên chính commit đang chạy production**.
      Tiêu chí cũ (`python -m pytest -q`) nay là **tiêu chí đã bị kho bãi bỏ**:
      `CLAUDE.md` cấm chạy nó cho toàn kho vì nó **bỏ sót 77 test frontend**
      — tức chính nó không bao giờ chứng minh được điều ô này đòi. Người
      kế nhiệm là `tools/gate.py`, và nó **bao cả bốn bộ frontend**.
    - [x] Secret scan, commit, build release, deploy và smoke production.

    ⭐ **Bằng chứng cho cả hai ô trên là một bản ghi MÁY SINH RA, không phải
       lời khai**: `test-results/gates/20260906T163550Z-23388.json` — gate
       **29/29 PASS**, 668 giây, `sha = 9f555599` — bản ghi neo vào **`sha`**,
       nên nó là bằng chứng bền: nó nói *"đúng cây mã này qua trọn 29 bước"*,
       bất kể máy chủ sau đó chạy bản nào. Production nay ở `0ad9c868`
       (`9f555599` là tổ tiên của nó). Trong đó:

    | Bước | Kết quả | Đóng ô nào của nhật ký 04/08 |
    |---|---|---|
    | 2 `secret scan` | PASS 17,5s | *"`scan_source_secrets.py` — Chưa chạy"* |
    | 29 `bo test (song song)` | PASS 523,1s | *"`python -m pytest -q` — ĐÃ DỪNG"* |
    | 25–28 bốn bộ frontend | PASS | phần mà tiêu chí cũ bỏ sót |

    Còn *commit / build release / deploy*: mã của `LAYOUT-001` **có mặt trong
    chính `9f555599`** — `git show 9f555599:server/static/ltt.css` có 8 chỗ
    `immersive`, `git show 9f555599:tests/test_129_adaptive_page_layouts.py`
    tồn tại, và 13 template đang dùng hợp đồng layout. *Smoke*: 07/09 đo
    `/health/version`, `/health/ready` 200 và `/login` tại origin 200.

    ⚠️ Ô này nằm mở **34 ngày sau khi việc của nó xong**, vì người đóng
       release ngày ấy không biết nó tồn tại. Đó là giá của một ô chỉ đóng
       được bằng tay: nó không đợi ai — nó **im lặng**.

- [x] H16 Agent Canvas parity với PlenX — triển khai tuần tự sau Decision Gate;
  không thay runtime/credit/queue hiện có và không sao chép lỗi PlenX.
  - [x] H16.0 DEEP discovery/audit — 2026-08-04: tạo workflow hands-on trên
    PlenX, kiểm kê 11 node active, model composer, page/frame/version/share/log/
    annotation/assistant; đối soát browser local, 7 ToolSpec, provider và code
    Agent hiện hành. Baseline `Q 67 · M 52 · E 76 · INTERNAL`; hồ sơ tại
    `docs/APP_AUDIT/agent/2026-08-04/`. Không tiêu credit, không sửa code,
    không deploy và chưa chạy full suite.
  - [x] H16.1 Khóa D1–D12 và acceptance matrix functional parity — 2026-08-04:
    Dev duyệt triển khai phương án B; ghi Q62 làm nguồn chân lý. Đích là parity
    capability + LTT brand/safety, Canvas v2, scoped run có quote/approval,
    provider qua gate và feature-flag/canary; không sao chép bug/IP PlenX.
  - [x] H16.2 Canvas v2 — 2026-08-04: pages/frames/annotations/view state,
    importer v1 lossless, revision/snapshot và migration additive PASS.
  - [x] H16.3 Immersive shell — 2026-08-04: Carbon Red full-height, rail/topbar/
    drawers, layers/shortcuts, desktop/mobile và browser console/network PASS.
  - [x] H16.4 Composer/catalog — 2026-08-04: capability động, model/provider/
    mode/ratio/quality/duration và quote server-authoritative PASS.
  - [x] H16.5 Media nodes — 2026-08-04: ánh xạ đủ 11/11 nhóm PlenX; upload
    owner-scoped, Text/Image/Batch/Video/Upscale/TTS/Extract/Merge/Social;
    SSRF/ACL và GPU image upscale smoke thật PASS.
  - [x] H16.6 Scoped execution — 2026-08-04: node/selection/frame/full +
    upstream closure, cache same-owner/exact params, frame export và ZIP bundle;
    quote/approval/credit vẫn bắt buộc.
  - [x] H16.7 Assistant — 2026-08-04: SSE analyze/improve, private pattern
    context, signed preview diff và validator trước apply. VLM video độc lập
    chưa có và được ghi backlog minh bạch.
  - [x] H16.8 Version/share/collab — 2026-08-04: snapshot/restore, private
    view/clone/revoke, annotation persistence và activity; không tuyên bố
    realtime multi-user.
  - [x] H16.9 Scale/ops local gate — 2026-08-04: Canvas 512 KiB/Plan 100 bước,
    frontend/backend 100-node PASS; metrics, rollout/kill switch/runbook; full
    `2.049 passed, 8 skipped, 23 subtests`, frontend 20 pass, npm audit 0,
    app lint 0/0, secret scan 0.
  - [x] H16.10 Production deploy/canary handoff — 2026-08-04: archive 1.187
    file/174,2 MB, release secret scan 0; PostgreSQL/data backup; migration lên
    `f6a7b8c9d0e1`; services/loopback/Cloudflare/catalog/docs/security/app load
    PASS. Production login desktop không overflow, console 0; phiên auth hết
    hạn nên browser tự chuyển đúng về login. Authenticated Canvas đã browser
    E2E trên fixture cùng bundle (desktop/mobile, API 200/201, console 0).
    Hai tab PlenX và LTT được giữ mở để chủ sản phẩm đăng nhập/nghiệm thu.

### H17 — Agent Canvas launch UX + audit độc lập

- [x] H17.0 Khóa UX contract Q63 — 2026-08-04: audit render thật LTT/PlenX,
  chọn full immersive Canvas; không đổi runtime/credit/provider.
- [x] H17.1–H17.3 Shell/rail/drawer/node/composer — route toàn viewport, rail
  48 px, palette/Inspector đóng mặc định, tìm tool, node visual-first và composer
  dưới theo ngữ cảnh.
- [x] H17.4 Connector — typed port 44×44, hover `+`, picker chỉ liệt kê input
  tương thích; invalid edge vẫn bị server/client contract từ chối.
- [x] H17.5 Browser acceptance local — 1720×940 và 390×844 không page overflow;
  Canvas desktop 1720×892; console 0; request của lượt reload mới 200.
- [x] H17.6 DEEP audit độc lập theo `quy_tac_audit.md` — 2026-08-04: hồ sơ
  `APP_AUDIT/agent/2026-08-04-launch`; Q 92,3/M 89/E 97; full regression
  2.050 pass, 8 skip, 23 subtests; controlled launch còn gate production.
- [x] H17.7 Release/deploy/canary handoff — 2026-08-04: commit `b3a0df4`;
  archive 1.203 file/174,6 MB, scan 0; backup PostgreSQL/data, update/migration,
  health loopback/Cloudflare/12 app/log PASS. Production login desktop/mobile
  overflow 0, console 0; deployed manifest khớp source SHA-256. Phiên auth hết
  hạn nên authenticated production Canvas được ghi đúng là manual gate còn mở.

### H18 — Agent Canvas presentation reset theo nghiệm thu thực tế

- [x] H18.0 Q64 + re-audit PlenX/LTT — 2026-08-04: khóa progressive
  disclosure; ba node chính Text/Image/Video; nền sáng mặc định, không đổi
  runtime/credit/provider.
- [x] H18.1 Catalog và node semantics — palette mặc định chỉ ba hành động chính;
  tìm kiếm/bật nâng cao mới hiện toàn bộ ToolSpec; nhãn, mô tả và chip thông số
  thay metadata kỹ thuật trên node.
- [x] H18.2 Theme per-user — GET/PUT preferences có CSRF, ownership, validation;
  lưu `light/dark` và `simple/advanced` trong AppProject riêng của user.
- [x] H18.3 Browser debug loop — Playwright bắt và sửa hai lỗi render thật:
  node 300 px nhưng spacing 260 px gây chồng; rule toolbar cũ ép action thành
  cột và che nút drawer. Desktop 1720×940 + mobile 390×844 overflow 0,
  theme/catalog giữ qua reload, palette đóng được, console 0.
- [x] H18.4 Full release gate + deploy/canary handoff — commit `6c5c066`;
  frontend 21 pass; backend/build 22 pass; full 2.051 pass, 8 skip, 23
  subtests; npm audit 0, app lint 0/0, secret scan 0. Release 1.206 file/174,8
  MB; backup/migration/update/health/Cloudflare/12 app/log PASS; bundle deploy
  khớp source. Production login desktop/mobile overflow 0, console 0;
  authenticated production Canvas còn là manual handoff vì không có credential.

### H19 — PROMPT AI OMMI từ Prompt Seedance Studio

- [x] H19.0 DEEP source/product audit — 2026-08-04: khảo sát read-only
  `D:\BOT GEMINI\app\modules\seedance` theo `KHAO_SAT_BOT_GEMINI.md` và
  LTT-AQA; đo 194 file/47.665 dòng, 261 endpoint, 49 bảng; lập capability/admin-
  user/data/job/credit/provider matrix, benchmark và roadmap P0–P8 tại
  `docs/APP_AUDIT/prompt-ai-ommi/2026-08-04/`. Baseline nguồn Q 59,8 · M 84 ·
  E 68 · BLOCKED; không sửa BOT GEMINI, không build/deploy, chưa có browser E2.
- [x] H19.1 Khóa kiến trúc Q65 — capability-preserving replatform, folder
  `apps/prompt_ai_ommi`, URL `/prompt-ai-ommi`, private-by-default, catalog do
  admin publish/user clone; dùng toàn bộ contract LTT, không copy runtime nguồn.
- [x] H19.2 P0 contract/parity ledger/threat model/ToolSpec handoff spike —
  2026-08-04: phủ 22/22 router nguồn, threat model; public ToolSpec handoff không
  sửa platform tại `07_PARITY_LEDGER.md`/`08_THREAT_MODEL.md`.
- [x] H19.3 P1 app shell + tenant-safe AppProject/Storage/preferences —
  owner-scoped CRUD/revision/archive/unarchive/snapshot/restore/upload; theme
  server-side; two-user/stale revision tests PASS.
- [x] H19.4 P2 core Studio + Director Job + quote/credit + scene editor —
  preflight miễn phí, durable job, APIKEYS Gemini, quote/hold, scene editor.
- [x] H19.5 P3 consistency/iteration/storyboard/version — ✅ ĐÓNG 2026-08-06 (`3b7c38f`):
  bổ sung chạy-lại-kèm-góp-ý (lưu vào chính bản sinh ra từ nó) và màn so hai bản
  cạnh nhau kèm phần prompt đã đổi. Phần cũ — **2026-08-05 làm lại
  trên bảng thật** (`ommi_storyboard`/`ommi_scene`/`ommi_scene_version`): chạy
  lại TỪNG cảnh có báo giá riêng, phiên bản theo cảnh, khôi phục bản cũ, reorder
  và xoá dồn vị trí; ghép prompt lấy phong cách + tài nguyên của chính chủ.
  26 test, có kiểm chứng đỏ khi gỡ từng guard. Còn regenerate-with-feedback và
  màn so sánh hai bản cạnh nhau trước khi đóng phase.
- [x] H19.6 P4 private library + published Admin catalog — ✅ ĐÓNG 2026-08-06 (`538390c`):
  bổ sung ngừng-dùng-mẫu-catalog (tách khỏi archive) và dọn dữ liệu có chạy thử.
  Phần cũ — **2026-08-05 đã xong
  phần lõi**: Kho tài nguyên (14 endpoint, upload + sinh ảnh) và ba thư viện
  meta/snippet/style với tầng catalog admin, clone-thành-bản-riêng, version.
  Mọi truy vấn lọc `owner_id`; không còn namespace dùng chung như module nguồn.
  Còn catalog deprecate và retention operator job.
- [x] H19.7 P5 export/import + Tạo ảnh/Tạo video/Agent handoff — JSON/MD/ZIP
  round-trip, ToolSpec ảnh/video quote-confirm, ToolSpec OMMI hiện trong Agent;
  PDF native là backlog không chặn v1.
- [x] H19.8 P6 batch/recovery/metrics/retention/runbook — ✅ ĐÓNG 2026-08-06 (`90c7707`):
  metric P95/chi phí theo loại việc, huỷ+thử lại job, diễn tập khôi phục trên
  LƯỢC ĐỒ THẬT (đã chạy: 32 bảng/38 ràng buộc nguyên vẹn). Phần cũ — bounded atomic image
  batch, job status, health, rollout/runbook đã có; còn retry/cancel UX, P95/cost
  metric, retention dry-run và backup drill.
- [x] H19.9 P7 Carbon Red immersive UI + browser accessibility/responsive gate —
  ✅ ĐÓNG 2026-08-06 (`371b976`): đo bằng trình duyệt thật — 31 phần tử đi hết
  vòng Tab đều có viền focus, 38 phần tử tương tác đều có tên đọc được, 0
  tabindex dương. Thiếu duy nhất là Escape đóng lớp phủ, đã thêm. Phần cũ —
  desktop + 390x844 render, overflow 0, console 0, failed network 0; còn
  keyboard/focus/axe/visual regression trước khi đóng phase.
- [ ] H19.10 P8 parity ≥90% + LTT-AQA G0–G8 + full release/canary/deploy.

Phải làm tuần tự H19.2→H19.10. Deployment chỉ được đánh dấu khi có lệnh deploy
rõ và kết quả production thật; kế hoạch hoặc source audit không phải release.

### H20 — Agent Canvas Deep UX / node-native reset

Triển khai theo Q66, tuần tự; không thay runtime Agent, hàng đợi, credit, provider
hay ownership. Mỗi phase UI phải được kiểm trên browser render thật trước khi đóng.

- [x] H20.0 Decision Gate — 2026-08-04: Q64 được thay đúng giao thức bởi Q66;
  chọn nền gần đen mặc định, node-native renderer, contextual composer, run theo
  node và quick-create khi kéo connection ra khoảng trống.
- [x] H20.1 Research baseline — 2026-08-04: Control Registry đầy đủ cho
  toolbar/context menu, 11 node PlenX và State × Action Matrix tại
  `docs/APP_AUDIT/agent/2026-08-04-deep-ux/00_CONTROL_MATRIX.md`; không tiêu
  credit benchmark.
- [x] H20.2 Interaction kernel — 2026-08-04: context menu pane/node, copy/delete/move page,
  run node/run-from-here, quick-create node tương thích, auto-layout và toggle
  connection đã chạy; viewport không còn làm bẩn undo history; regression PASS.
- [x] H20.3 Core node-native UX — 2026-08-04: Text/Image/Video/Audio có empty/configured/
  running/success/error state; upload/manual/generate đúng capability; contextual
  composer chỉ hiện thông số nghiệp vụ, kỹ thuật nằm trong Inspector.
- [x] H20.4 Input/transform UX — 2026-08-04: Batch Images, Social Video, asset input,
  Upscale/Video Upscale/Extract Frames/Merge Image/Merge Video có hành động,
  preview/input typed; palette chỉ lấy ToolSpec server có executor thật.
- [x] H20.5 Agent context — 2026-08-04: `@node` tạo typed edge thật và thay source
  cũ trên cùng input; Assistant nhận selection context; run node chỉ xét lỗi của
  target + prerequisite; E3 tạo awaiting approval 10 credit, actual 0.
- [x] H20.6 Browser/regression gate — 2026-08-04: desktop 1366/1720/1920 và mobile 390;
  console 0 error, failed request mới 0, overflow 0, keyboard/focus PASS; node/
  selection scope giữ contract quote→approval; edge state/renderer đồng bộ.
- [x] H20.7a LTT-AQA/release candidate — 2026-08-04: audit DEEP mới chấm
  `Q83 · M80 · E82 · BETA`; frontend 27 pass, targeted 22 pass, full pytest
  2.063 pass/8 skip/23 subtest, npm audit 0, contract 12/12, secret scan 0.
- [x] H20.7b Production release — 2026-08-04: phát hành commit `b02e2eb` bằng
  `update.ps1`; backup PostgreSQL/data xác minh được, giữ `app.previous`, migration
  PASS, Web/Worker/Codex/Cloudflare running, loopback/edge ready. Authenticated
  browser desktop/mobile tải bundle H20.8; console 0, fresh failed request 0.
- [x] H20.8 Re-audit PlenX vòng 2 và interaction polish — 2026-08-04: thao tác sâu
  title/Text/source/input chip/output/shortcut; triển khai display label ngoài
  Plan, inline Text, chip tháo edge+param, direct shortcut, drag/drop và artifact
  actions. Frontend 29 pass, build PASS; desktop/mobile browser console 0, save
  PUT 200. Asset Catalog/URL/batch/output lineage được tách thành vé có gate tại
  `docs/APP_AUDIT/agent/2026-08-04-deep-ux/08_REAUDIT_PLENX_GAPS.md`.
- [x] H20.9 Purchased workflow parity + multimodal execution — 2026-08-04:
  đối chiếu Lookbook mua sẵn 13 node/13 edge; bổ sung Image nhận nhiều ảnh,
  Image/Video→Text, Text→Image/Video, Social Video, transform thật, variadic edge
  và clipboard/selection. Browser dựng nhánh 8 node/9 edge, validate/báo giá
  132 credit, actual 0, console 0, request lỗi 0. Hồ sơ ở `09_PURCHASED_WORKFLOW_PARITY.md`.
- [x] H20.10a Full release gate + production deploy — 2026-08-04: commit
  `6dbc347`; full 2.091 pass/8 skip/23 subtest, secret scan 0; archive 1.165
  file/78,0 MB; backup PostgreSQL+data, migration, update, loopback/edge/13 app/
  log PASS. Manifest và build-meta production khớp source; login desktop console
  0, failed request 0.
- [x] H20.10b Authenticated production Canvas handoff — 2026-08-04: theo quyền
  mới của chủ sản phẩm, đã bảo đảm canary role `user`, tải production Canvas,
  tạo graph audit không chạy provider; console 0, request API 200/201, actual
  credit 0. Runtime smoke PASS nhưng product UX bị owner reject và chuyển H21.

Production H20.8 đã có đủ backup, update, health và authenticated browser evidence.

### H21 — Agent Canvas UX Reset theo Q67 → Q68

H20 là lịch sử triển khai renderer theo ToolSpec; không mở lại hay vá chồng chéo.
H21 thay presentation model sau bằng chứng E3 production và phản hồi 3/10 của
chủ sản phẩm. Runtime/credit/provider/ownership của Q62 giữ nguyên.

- [x] H21.0 Audit reset + benchmark chính thức — 2026-08-04: production canary
  user-role, PlenX 13 node/13 connection, source LTT và tài liệu chính thức
  FLORA/React Flow/ComfyUI/Langflow/n8n. Baseline `Q58 · M42 · E93 · BLOCKED`,
  UX/UI 2,8/10; chọn Presentation Adapter bốn modality. Hồ sơ tại
  `docs/APP_AUDIT/agent/2026-08-04-ux-reset/`.
- [x] H21.1 P0 Contract/migration/feature flag/rollback — 2026-08-04:
  `creative-v1`, H20 v1/v2 mở nguyên, preference cũ migrate presentation-only,
  env rollback `legacy`; contract tại `06_PRESENTATION_CONTRACT.md`.
- [x] H21.2 P1 Canonical Text/Image/Video/Audio block — 2026-08-04: fresh user
  chỉ thấy bốn block; Audio primary; `asset.*` ẩn khỏi palette/context nhưng
  node cũ/upload state vẫn render và giữ ownership/provenance.
- [x] H21.3 P2 Node shell + composer tối giản — 2026-08-04: renderer
  `CreativeToolNode` tách khỏi H20 legacy, node 300 px/một cổng `+`, bỏ CTA chạy
  trùng; composer tối đa bốn field và chiếm safe-area riêng. Browser
  1366/1720/1920: 4 node, overlap 0, overflow 0, console 0.
- [x] H21.4 P3 Connection grammar theo intent, unique destination, edge insert
  — 2026-08-04: destination dùng nhãn block duy nhất (`Văn bản 2` khi trùng),
  chặn cycle trước khi ghi graph, reconnect nguyên tử, dây có mũi tên/màu theo
  modality và midpoint `+` chèn block tương thích. Browser 1366/1720/1920:
  5 node/2 edge, 2 midpoint CTA, overflow 0, console 0, API 200/201.
- [x] H21.5 P4 Run/quote/approval/cancel/retry thống nhất — 2026-08-04: bảng
  Chạy creative chỉ còn scope/cache/preflight/quote/confirm/progress; thao tác
  tổ chức node bị loại khỏi bảng này. Scope khóa sau quote, hiển thị đúng block
  và số bước; confirm chỉ mở khi actual=0. Browser local tạo quote 5 credit cho
  1 block, actual 0, không gọi approve/provider, hủy trước duyệt giữ actual 0.
- [x] H21.6 P5 First-run/templates/assets-history/Assistant progressive —
  2026-08-04: blank page có hướng dẫn ba bước và mẫu theo kết quả
  Text→Image, Image→Text, Image→Video; mẫu dựng 2 block/1 dây, chọn upstream để
  nhập/upload ngay, không cần Inspector. Fresh workflow ẩn Assistant, History,
  Layers/Note/Comment và khóa Run đến khi có block. Mobile 390: overflow 0.
- [x] H21.7 P6 Browser/regression/a11y/performance/recovery gate — 2026-08-04:
  48 frontend test và 2.092 backend test pass; Playwright 1366/1720/1920 với
  50 block đều full-width/overflow 0, mobile 390 tự fit graph và chỉ-xem,
  console 0, request bất ngờ 4xx/5xx 0. Keyboard/screen-reader label pass;
  conflict có CTA tải bản mới, offline xếp hàng và tự lưu khi online lại.
- [x] H21.7a Chrome user-journey hardening — 2026-08-05: thao tác người dùng
  thật trên Text→Image, Image→Text, Image→Video; sửa menu `•••`, terminal run
  bị khóa, composer/node bị che, preview ảnh tràn khung, input port kỹ thuật và
  lỗi ngân sách toàn cục bị lọc mất rồi gắn nhầm thành “Lỗi lưu”. Kéo nối/tháo
  dây, quick-create Video→Text, chèn transform, undo/redo, offline→online,
  reload, theme per-user và mobile 390 đều PASS. Node asset chạy xuyên suốt
  quote→approve→artifact với actual 0; không gọi provider. Frontend 49 pass,
  full 2.092 pass/8 skip/23 subtest, npm audit 0, console 0, fresh request 2xx.
- [x] H21.7b Customer-first hardening theo Q68 — 2026-08-05: nền `rgb(0,0,0)`;
  prompt và CTA `Chi tiết` / `N credit · Chạy` nằm trong block; `Chi tiết` chỉ
  còn nhãn nghiệp vụ, không lộ ToolSpec/field/type/ID/provider/Fan-out. Sửa lỗi
  picker `@` trong node chào mời kết nối tạo chu trình rồi im lặng không làm gì
  (thiếu `connectionCreatesCycle` mà picker `+` đã có), kèm test chốt đã kiểm
  chứng fail khi gỡ guard. Fixture browser được vá để phủ đúng chuỗi
  `text.generate → image.generate`. Browser thật: desktop 1366 rail không đè
  node, mobile 390 không tràn ngang, quote 8 → actual 0 trước duyệt → hoàn tất
  8/8 credit, console 0 error/0 warning, request 2xx. Frontend 51 pass, full
  2.092 pass/8 skip/23 subtest, secret scan 0 finding. Runtime/credit/provider
  không đổi. Tồn đọng ghi ở nhật ký: gate Node hiện không kiểm được version thật.
- [ ] H21.8 P7 Controlled beta 5 user task + re-audit Q/M/E — protocol và CSV
  đo đã sẵn sàng tại `07_CONTROLLED_BETA_PROTOCOL.md` / `08_CONTROLLED_BETA_RESULTS.csv`;
  còn thiếu E4 từ đúng 5 người dùng thật nên chưa được đánh dấu PASS.
- [x] H21.9 Deploy production — 2026-08-05: chủ sản phẩm yêu cầu deploy **trước**
  khi H21.8 PASS, khác điều kiện "chỉ sau H21.8 PASS" ghi ban đầu; ghi lại để
  không hiểu nhầm là beta đã đạt. Bundle `main-DbE16SG4.js` đã lên, asset cũ trả
  404, public `/health/ready` 200, ba dịch vụ Running, trang chủ console 0 error.
  **Deploy làm production ngưng 2 lần (~24 phút và ~13 phút)** — nguyên nhân và
  cách sửa ghi đầy đủ trong nhật ký; `setup/2-cai-dat.ps1` đã được vá kèm test.

Thứ tự bắt buộc H21.1→H21.9; không làm Assistant/model breadth trước core block
và connection grammar. Không deploy UX Reset từ hồ sơ audit này.


---

## H22 — Rà soát hệ điều hành: bố cục mã nguồn và tầng nghiệp vụ

Nguồn: `docs/APP_AUDIT/control-plane/2026-08-06/`. Phạm vi là **chất lượng nền
tảng**, không phải một app: logic vận hành, bố cục/phân loại file, hiển thị
mobile. Chín hạng mục ưu tiên ở `03_SCORECARD.md` §5.

- [x] H22.1 Một lệnh gate duy nhất — 2026-08-06 (`139c2b2`): `tools/gate.py`
  chạy quét bí mật · lint hợp đồng app · 3 bộ test frontend · pytest. Trước đó
  `pytest -q` không chạy 77 test vitest nên "full regression xanh" là câu nói
  sai. `test_145` đỏ nếu thêm frontend mà quên khai.
- [x] H22.2 Vùng chạm 24px (WCAG 2.2 AA 2.5.8) — 2026-08-06 (`139c2b2`):
  9 vi phạm thật (không phải 22–41 như lần đếm đầu — 31 cái là radio trong
  label 44px, đã ghi bài học vào hồ sơ audit). `test_146` chốt.
- [x] H22.3 Bỏ phụ thuộc ngược + hợp đồng quyền admin — 2026-08-06 (`cd34989`).
- [x] H22.4 Chuẩn hoá **nơi đặt logic nghiệp vụ** trong hợp đồng app —
  2026-08-06 (`67e3a3e`): `AGENTS.md` **mục 8** + bản rút gọn ở `CLAUDE.md`.
  `routes.py` chỉ lo HTTP; nghiệp vụ ở `services/` (nhiều miền) hoặc
  `features.py` (một miền); `tables.py` cho bảng CSDL. Trần 900 dòng /
  30 handler do `tools/lint_app_contract.py` gác, **tính theo từng file** để
  không phạt đúng thứ mình muốn khuyến khích.
- [x] H22.5 Tách `apps/prompt_ai_ommi/routes.py` — 2026-08-06 (`67e3a3e`):
  1.799 dòng / 64 handler → 9 module, lớn nhất 551. Router vẫn đủ 64 route.
  Test bắt 4 lỗi do chính việc tách gây ra, đều đã sửa.
- [x] H22.6 Tách `apps/agent/routes.py` — 2026-08-06 (`be5331b`): 1.308 dòng /
  48 handler → 9 module, lớn nhất 237. So khớp `(path, method, tên handler)`
  với bản HEAD: **giống hệt 48/48**.
- [x] H22.7 Gom việc dùng chung về nền tảng — 2026-08-06: thêm
  `platform_core/frontend_bundle.py` (ba app tự đọc manifest Vite và tự neo gốc
  repo bằng `parents[2]`), và chuyển `core.runtime_paths` →
  `platform_core/runtime_paths.py`. Sau bước hai, **`platform_core/` và toàn bộ
  app không còn phụ thuộc `core/`** (`test_147` chốt).
- [x] H22.8 Bản đồ `core/` còn sống / đã chết — 2026-08-06:
  `04_BAN_DO_CORE.md`. Đo khả đạt bắc cầu từ điểm vào thật, cố ý loại `tests/`.
  **99,4% của 15.668 dòng không phục vụ app nào đang bán**; 43/69 = 62% route
  công khai thuộc sản phẩm đã đóng băng.
- [x] H22.9 Presign R2 không nuốt lỗi thật — 2026-08-06 (`9f40b18`): thêm
  `Storage.try_url_for()` / `try_put_url()`, chuyển 15 chỗ gọi. Vẫn degrade
  nhưng **ghi log** để sự cố R2 nhìn thấy được.
- [x] H22.10 ✅ ĐÓNG 2026-08-06 (`352ad67`) → **VƯỢT QUA 2026-08-25 (Q108)** — 43
  route đó **đã bị xoá**, không còn nằm sau cờ nữa. Cờ `LTT_SOCIALBOT_ROUTES`
  không còn được đọc ở đâu.
  Gốc: ~~43 route vào cờ `LTT_SOCIALBOT_ROUTES`, mặc định BẬT; chủ sản phẩm đặt
  `=0` khi xác nhận không còn ai dùng~~ — câu hỏi *"có ai còn dùng không"* nay
  đã có số đo, và câu trả lời là **không ai**: CSDL production có 0 job, 0
  `app_access`, 0 `app_projects` mang slug socialbot, và hai kho token
  `tokens.enc`/`tiktok_tokens.enc` **chưa bao giờ được tạo**. Cờ tồn tại để
  hoãn một quyết định thiếu dữ liệu; có dữ liệu rồi thì quyết định được.
- [x] H22.11 ✅ ĐÓNG 2026-08-06 (`59846bf`) — xoá **2 module / 533 dòng**, không
  phải 5/535: ba file `__init__.py` là dấu hiệu package, xoá là gãy
  `core.facebook.commenter` đang chạy. Gốc: ~~chưa làm vì xoá~~
  code của sản phẩm **đóng băng chứ chưa khai tử** là quyết định sản phẩm.
- [x] H22.12 ✅ ĐÓNG 2026-08-06 (`47638dd`) — đo lại chặt hơn cho **99** chứ không
  phải 145 (phép đo cũ tính nhầm handler biến lỗi thành giá trị nhìn thấy được).
  `platform_core` về **0**; 90 chỗ còn lại trong mã sống nằm sau bánh cóc
  `tools/check_silent_except.py` trong gate — không cho tăng thêm.
  H22.9 chỉ xử lý nhóm presign vì nhóm đó hại rõ và sửa được cùng một chỗ.

Hai lỗi **thật** tìm được trong lúc làm (không nằm trong danh sách audit):
`POST /upscalevideo/queue` gọi `get_session()` mà không import (mọi lần nộp đều
500, có từ 2026-08-02, không test nào chạm), và nhóm presign ở H22.9. Cả hai
thuộc loại test-từng-route không bắt được; nay có `tools/check_undefined_names.py`
trong gate.

---

## H24 — Đa ngôn ngữ VI/EN *(chốt 2026-08-06, đang làm)*

**Quyết định của chủ sản phẩm (2026-08-06):**

| Câu hỏi | Chốt |
|---|---|
| Phạm vi | Đường khách đi trước; **trang admin giữ tiếng Việt** (chỉ một người đọc) |
| Không xác định được quốc gia | **EN** (VI vẫn là ngôn ngữ gốc của mã nguồn) |
| Địa chỉ trang | **Tiền tố `/en/`**, VI ở gốc — được SEO và link chia sẻ |
| Tiến độ | **Chạy hết cả 4 pha**, vì app chưa mở ra thế giới, chưa có khách thật |

**Thứ tự nhận diện ngôn ngữ** (dừng ở tầng đầu tiên có kết quả):
1. Người dùng tự chọn (nút đổi) — **không bao giờ bị máy ghi đè**
2. Hồ sơ tài khoản (đã đăng nhập)
3. `CF-IPCountry` — `VN` → VI, khác → EN *(Cloudflare đã BẬT IP Geolocation,
   header về sẵn máy chủ; không cần thư viện GeoIP, không tốn tiền)*
4. `Accept-Language` — cứu khi CF trả `XX` (Tor/VPN)
5. Mặc định EN

**Đường TUYỆT ĐỐI không gắn tiền tố** — bên ngoài gọi vào URL cố định:

| Đường | Ai gọi | Hỏng thì sao |
|---|---|---|
| `/webhooks/payment/payos` | PayOS | **khách trả tiền, không nhận credit** |
| OAuth callback FB/TikTok | Facebook, TikTok | gãy đăng nhập mạng xã hội |
| `/health/*` | giám sát, `4-nghiem-thu.ps1` | báo động giả |
| `/static/*` | trình duyệt | mất CSS/JS |
| API JSON của app React | chính trang đó | app trắng |

Đây là rủi ro riêng của phương án tiền tố. Cùng loại với lỗi `return_url=PLACEHOLDER`
ngày 2026-08-06: bên ngoài gọi đúng URL ta đưa, ta đổi URL thì họ gọi vào chỗ trống.
**Khoá bằng test, không bằng trí nhớ.**

**Đo được 2026-08-06:** 2.562 chuỗi hiện cho người dùng (đã loại chú thích và
docstring bằng AST). Template nền tảng 426 · template app 396 · React/TS 366 ·
`server/` 522 · `platform_core/` 273 · `apps/` 681. Trong đó 2.224 chuỗi ngắn,
338 chuỗi dài. Chưa có một dòng hạ tầng i18n nào.

**Chữ nằm NGOÀI mã nguồn** (dễ sót nhất): `display_name`/`description` của 14
manifest app; tên gói credit trong CSDL (admin sửa được); nội dung email ở
`platform_core/mailer.py`.

**Pha 0** hạ tầng: Babel/gettext, middleware 5 tầng, helper sinh link có tiền tố,
danh sách miễn trừ, và **bánh cóc trong `tools/gate.py`** — chuỗi hiện cho người
dùng không bọc `_()` thì gate đỏ. Không có bánh cóc thì công dịch sẽ mục dần,
đúng như hiện trạng "Marketplace"/"My Apps" lẫn giữa trang tiếng Việt.
**Pha 1** đường khách đi (~700) · **Pha 2** từng app (~1.100) · **Pha 3** dữ liệu.

---

## H25 — Cổng thanh toán quốc tế 📋 *(chủ sản phẩm sẽ xử lý sau)*

**Vấn đề:** PayOS chỉ làm VietQR và chuyển khoản ngân hàng Việt Nam (tài khoản
nhận là MBBank). Khách ở Mỹ/Nhật/Đức **không có cách nào nạp credit**. Họ đọc
được trang tiếng Anh, hiểu sản phẩm, bấm "Nạp credit" rồi gặp mã QR ngân hàng
Việt Nam không dùng được.

**Hệ quả:** H24 (đa ngôn ngữ) là điều kiện **cần nhưng không đủ** để bán ra thế
giới. Làm xong H24 vẫn chưa mở được cửa bán cho khách nước ngoài.

**Thuận lợi:** kiến trúc cổng đã **agnostic** từ H9 (Q31) — thêm Stripe/PayPal/
Paddle chỉ là viết adapter trong `platform_core/payments/`, không đụng nghiệp vụ
`billing.py` hay sổ credit. Đơn hàng đã idempotent sẵn.

**Vướng nằm ngoài kỹ thuật:** Stripe/Paddle đòi pháp nhân, khai thuế, hoá đơn,
và chính sách hoàn tiền. Đây là việc pháp lý/kế toán, không phải việc mã nguồn —
**chủ sản phẩm nhận xử lý** (chốt 2026-08-06).

---

## H26 — Chuẩn hóa portfolio app, lịch sử job và UX update 2026-08-08

Nguồn: `docs/APP_AUDIT/platform/2026-08-08-app-update/`. Phạm vi và thứ tự ở
`07_IMPLEMENTATION_ROADMAP.md`; thực hiện tuần tự, phase trước PASS mới sang
phase sau. Baseline tạm: `Q58 · M UNKNOWN · E31 · BLOCKED`.

- [x] H26.0 Audit STANDARD + inventory + roadmap — 2026-08-08: đọc toàn bộ ảnh/
  `MoTa.txt`, kiểm source/browser/hardware, lập Q/M/E, G0-G8, findings, decision
  gate và Phase 0-5. Không sửa runtime, không deploy.
- [x] H26.1 Khóa 12 quyết định sản phẩm — 2026-08-08: chủ sản phẩm chọn toàn bộ
  phương án A; ghi thành Q69-Q80 trong nguồn chân lý.
- [x] H26.2 Phase 0 — 2026-08-08: thêm contract `surface/lifecycle` và
  `customer_visible`; Kịch bản + Media runtime-only, landing 308 sang Canvas;
  Demo admin-only/customer 404; build lại Canvas, browser anonymous/customer/
  operator PASS, console 0, full `python tools\gate.py` PASS 9/9.
- [x] H26.3 Phase 1 — 2026-08-08: `JobEvent` append-only + redaction/retention
  365/30 ngày; lifecycle event và credit settle/refund dùng chung; History API,
  Jobs filter/date/cursor/timeline/lineage/artifact/retry/cancel; metrics/operator
  log; migration restore drill, browser customer/cross-tenant/operator/mobile và
  full `python tools\gate.py` PASS 9/9.
- [x] H26.4 Phase 2 — 2026-08-08: card-link accessible; capability/lifecycle từ
  manifest; filter độc lập và sort lifecycle; hợp nhất presentation Thumbnail
  thành mode Tạo ảnh AI nhưng giữ route/job/history cũ; Playwright
  390/768/1366/1920 + keyboard/console/network PASS; full
  `python tools\gate.py` PASS 9/9 (pytest 2.540 pass, 8 skip, 23 subtest).
- [x] H26.5 Phase 3.1 — 2026-08-08: đổi tên Upscale Video; mutual exclusion FPS
  ở UI/service; compare slider kéo/phím + đồng bộ player/drift; queue filter/
  sort/grid-list/thumbnail thật; download attachment owner-only; Watch chỉ admin,
  ẩn research. Sửa root cause two-GPU: UUID lease → NCNN `-g` + env FFmpeg;
  2 preset × 3 resolution × 2 GPU PASS, dual-worker 100% tải mỗi card, max 64°C,
  không thermal slowdown; browser customer/admin/mobile sạch; full
  `python tools\gate.py` PASS 9/9 trong 1.663,3 giây. Chưa deploy.
- [x] H26.6 Phase 3.2 — **PASS 2026-08-08, chưa deploy**: AutoSub — sửa root
  cause version drift (rollout thiếu/rỗng nay giữ Studio public), tách lifecycle
  render khỏi auxiliary AI, thêm lịch sử job theo user/project và khôi phục sau
  reload; giữ `off` + bundle-missing làm legacy rollback một release. Browser
  A-Z dùng video thật: upload → import SRT → style → quote/hold 1 credit → worker
  FFmpeg/NVENC → download video/ASS/ZIP; ZIP đủ 5 artifact, desktop/mobile sạch,
  không overflow. Frontend 13 PASS; backend/bundle 44 PASS; full gate PASS 9/9.
- [x] H26.7 Phase 3.3 — **PASS 2026-08-09, chưa deploy**: đổi tên public thành
  Tạo Video Seedance nhưng giữ slug/job/provider; advanced mặc định đóng, ba
  picker ref + preview/role/handle, status/model/aspect/sort, cancelled,
  grid/list lưu local, metadata/log; sửa quote quantity=2 hiển thị đúng tổng
  hold. Browser fixture tạo 2 queued job, 1000→906 credit, asset history/log,
  Upscale quote 3 credit, desktop/mobile không overflow, console/network sạch.
  Targeted 76 PASS; full gate 9/9 trong 1.616,1 giây.
- [x] H26.8 Phase 3.4 — **PASS 2026-08-09, chưa deploy**: đổi tên public thành
  Prompt AI nhưng giữ slug/job/provider/cost; catalog tích hợp read-only gồm
  8 style + 4 meta + 4 snippet, clone thành bản user riêng; dashboard owner-only
  có credit/resource/project/activity thật, responsive desktop/mobile. Không
  import runtime hay dữ liệu user từ BOT GEMINI. Targeted backend 41 PASS,
  frontend 22 PASS; browser console sạch; full gate PASS 9/9 trong 1.630,2 giây.
- [x] H26.9 Phase 3.5 — **PASS 2026-08-09, chưa deploy**: một catalog entry
  và shell canonical `/taoanh`; General + Thumbnail chuyển mode trong cùng
  product. `/thumbnail` redirect 308, Thumbnail nạp fragment owner-scoped qua
  HTTP; giữ hai executor/job/credit/storage/history và không import chéo app.
  Desktop 1920×1080 + mobile 390×844 không overflow, submit/quote/history/
  compare/remix thật, console/network sạch. Targeted 32 PASS; quick gate 8/8;
  full gate 9/9 trong 1.673,8 giây.
- [x] H26.10 Phase 3.6 — **PASS 2026-08-09, chưa deploy**: audit rồi mới build Clip ngắn, Chat, Agent và maintenance
  Socialbot; các folder mô tả trống giữ UNKNOWN.
  - [x] H26.10A — **PASS 2026-08-09, chưa deploy**: Clip Studio customer-first;
    source preview/summary/clear; số clip+tỉ lệ là control chính; tùy chọn nâng
    cao mặc định đóng; không lộ engine metadata; i18n runtime; mọi card có job
    log. Browser file thật quote 20/settle 15 credit, compare/package revision,
    desktop/mobile/console/network PASS. Targeted 16; full gate 9/9 trong
    1.670,8 giây.
  - [x] H26.10B — **PASS 2026-08-09, chưa deploy**: Chat AI customer-first;
    incremental hold 20 credit trước từng ảnh chặn số dư âm; partial output được
    lưu và settle, zero output refund; public model label, i18n 0 missing/fuzzy,
    suggestions, Stop, live title/balance và per-turn trace. Browser SSE 100→97,
    reload bền, desktop/mobile/console/network PASS. Targeted 17; full gate 9/9
    trong 1.648,4 giây.
  - [x] H26.10C — **PASS 2026-08-09, chưa deploy**: Agent delta audit theo
    Q68; browser desktop/mobile chạy flow Text→Image theo scope 2 bước, quote
    và settle 8/8 credit, reload/theme bền, simple palette chỉ có bốn creative
    block, console/network sạch. Frontend 52 PASS + typecheck; Python targeted
    Agent/Socialbot/registry/access 98 PASS. Không phát hiện gap code mới nên
    không tạo churn. Socialbot giữ frozen/maintenance theo Q10/Q78, không đụng
    runtime/OAuth; `public=False` tiếp tục ẩn anonymous và phân quyền sau login.
- [x] H26.11 Phase 4: performance/privacy/ops, retention, SLO, load/soak và
  failure recovery.
  - [x] H26.11A — **PASS 2026-08-09, chưa deploy/chưa apply production**:
    retention report operator-only; event 365/30 ngày; CLI dry-run mặc định và
    purge explicit có confirm cho Job terminal >365 ngày. Job active, ledger và
    artifact không bị xóa. Support export JSON lọc params/result/error/note/PII,
    customer 403. Policy platform được viết lại, nêu rõ artifact gap. Targeted
    18 PASS; quick gate 8/8.
  - [x] H26.11B — **PASS development 2026-08-09, chưa deploy**: SLO theo
    profile executor và metric tách từng app; dưới 20 finished là
    `insufficient_data`. Queue soak cô lập 300 Job/3 profile PASS, success 98%,
    queue-wait p95 5,444–5,607s, 3 credit/success; AutoSub 3.000 cue
    0,429s/8,98 MB.
    Targeted concurrency/body-cap/GPU 31 PASS; dual-GPU/matrix dùng evidence
    2026-08-08 còn hiệu lực, không chạy lặp. Production SLO chờ H26.12.
  - [x] H26.11C — **PASS development 2026-08-09, chưa deploy**: worker
    restart/orphan, retry/cancel race, provider/storage outage, process timeout,
    GPU lease và refund/settle idempotent đạt 102 targeted test. Bịt gap lỗi
    provider thô trong `Job.error`/worker/storage log; LocalStorage partial được
    dọn nguyên tử. Secret scan 0, quick gate 8/8. Full gate lần 1 đạt 2.578 pass
    nhưng đỏ 1 test do chữ `P95` bị hiểu nhầm là hệ kế hoạch P9; test đó đã sửa
    và PASS. Output full gate lần 2 bị host làm mất sau khi process kết thúc;
    release gate cuối được chạy lại một lần ở H26.12, không giả báo PASS.
- [x] H26.12 Phase 5: **PASS + DEPLOYED 2026-08-09** — full gate, browser A-Z,
  backup/rollback, canary, deploy và
  re-audit Q/M/E + G0-G8.
  - [x] H26.12A — **PASS local 2026-08-09, chưa deploy**: browser pre-release
    11 route desktop + mobile sạch; Chat SSE 3 credit, Agent Text→Image 2 bước
    8/8 credit, Tạo ảnh AI 5 credit. Sửa overflow Seedance mobile và polling
    lịch sử Tạo ảnh không reload form. Targeted 9 PASS; quick gate 8/8.
  - [x] H26.12B — **PASS 2026-08-09, chưa deploy**: backup production sang ổ
    D có dump DB + protected env; restore cô lập đủ 4 entry; rollback rehearsal
    3/3. Sửa rollback điều khiển đủ Web/Worker/Codex và bắt readiness thật.
    Deploy regression 48 PASS; full `python tools\\gate.py` PASS 9/9, pytest
    1.596,9 giây.
  - [x] H26.12C — **PASS + DEPLOYED 2026-08-09**: build archive 1.404 file,
    SHA-256 `8148becd1342a6685caa6fa93069d7dae8d9ce502f289d37d2b6731501890750`;
    canary đúng archive đạt 22/22 route desktop/mobile và Tạo ảnh settle 5
    credit. Deploy `EXITCODE=0`; ba service RUNNING; local/public health ready,
    build `v1.0`, hash production khớp source. Public browser không overflow;
    Turnstile render và sinh token. Re-audit `Q87 · M73 · E80 · PUBLIC`, G0-G8
    PASS theo baseline; chưa nâng COMMERCIAL do chưa đủ production SLO sample,
    authenticated browser sau deploy và đánh giá output độc lập.

Điều kiện chặn: không xóa vật lý Kịch bản/Media trước khi ToolSpec dependency đã
di trú; không coi 2 GPU 16 GB là một GPU 32 GB; không gọi app “đã hoàn thiện”
theo quality gate khi còn G4/G8 FAIL.

---

## H27 — Audit DEEP độc lập từng app theo LTT-AQA

> **Superseded một phần bởi H28:** các điểm E ghi trong lịch sử H27 là snapshot
> chấm sai taxonomy; dùng điểm E hiệu chỉnh ở H28. Q/finding/Gate vẫn hiệu lực.

Nguồn quy tắc: `docs/quy_tac_audit.md`. H26 là audit portfolio/release, không
thay thế audit A0–A10 độc lập của từng sản phẩm. H27 chỉ audit và khóa roadmap;
không sửa runtime, không deploy trước Decision Gate của app tương ứng.

- [x] H27.0 Inventory và thứ tự — 2026-08-09: 8 customer product; audit tuần
  tự, không chồng chéo: Upscale → Seedance → AutoSub → Prompt AI → Tạo ảnh +
  Thumbnail → Clip ngắn → Chat AI → Agent AI; sau đó Socialbot maintenance và
  Demo/Kịch bản/Media runtime contract; cuối cùng tổng hợp cross-app.
- [x] H27.1 Upscale Video DEEP — 2026-08-09: hồ sơ
  `docs/APP_AUDIT/upscalevideo/2026-08-09/` đủ 00–07 + evidence desktop/mobile.
  Chốt `Q64 · M57 · E84 · BLOCKED`; 0 P0, 2 P1, 10 P2, 4 P3. G2/G4/G5/G6/G8
  FAIL, G7 UNKNOWN. Targeted 50 PASS; browser video thật/VI/EN/responsive/
  controls/console/network đã chạy. Không sửa code, không deploy.
- [x] H27.2 Tạo Video Seedance DEEP — 2026-08-09: hồ sơ
  `docs/APP_AUDIT/taovideo/2026-08-09/` đủ 00–07 + 3 evidence screenshot.
  Chốt `Q57 · M64 · E87 · BLOCKED`; 0 P0, 3 P1, 11 P2, 4 P3. G2/G3/G4/G5/
  G6/G8 FAIL, G7 UNKNOWN. Targeted 77 PASS; quick gate 8/8; browser file thật,
  2 variants, credit failure, VI/EN, desktop/mobile/keyboard/console/network đã
  chạy. Không sửa code, không deploy.
- [x] H27.3 AutoSub Video DEEP — 2026-08-09: hồ sơ
  `docs/APP_AUDIT/autosubvideo/2026-08-09/` đủ 00–07 + evidence desktop/mobile/
  EN/video thật/network. Chốt `Q56 · M65 · E90 · BLOCKED`; 0 P0, 3 P1,
  14 P2, 5 P3. G2–G8 FAIL; G1 PASS có điều kiện. Targeted 36 Python +
  13 frontend PASS nhưng còn 2 unhandled-thread warning; quick gate 8/8 PASS.
  Browser chứng minh 4K/source cùng 1 credit, QA lỗi vẫn quote, waveform tải
  trọn video, mobile bị cắt và `/en/` vẫn VI. Không sửa code, không deploy.
- [x] H27.4 Prompt AI DEEP — 2026-08-09: hồ sơ
  `docs/APP_AUDIT/prompt-ai-ommi/2026-08-09/` đủ 00–07 + evidence desktop/
  mobile/EN/theme/classic. Chốt `Q48 · M51 · E92 · BLOCKED`; 0 P0, 5 P1,
  14 P2, 6 P3. Paid Director apply conflict, autosave mất dữ liệu, workflow
  reference→storyboard→handoff đứt và upload lifecycle là blocker. 170 backend
  195 backend + 22 frontend test pass nhưng chưa phủ paid A–Z.
- [x] H27.5 Tạo ảnh AI + Thumbnail mode DEEP — 2026-08-09: giữ hồ sơ H26
  lịch sử, lập audit độc lập tại `docs/APP_AUDIT/taoanh/2026-08-09-deep/` đủ
  00–07 + 5 screenshot. Chốt `Q56 · M54 · E91 · BLOCKED`; 0 P0, 3 P1,
  15 P2, 6 P3. Blocker: Thumbnail flat-price làm Pro vẫn 5 credit, validation
  xóa form và reference/artifact lifecycle không khép kín. 48 targeted test pass
  nhưng không phủ ba blocker.
- [x] H27.6 Tạo Clip ngắn DEEP — 2026-08-09: hồ sơ
  `docs/APP_AUDIT/taoclipngan/2026-08-09-deep/` đủ 00–07 + 6 screenshot.
  Chốt `Q58 · M56 · E92 · BLOCKED`; 0 P0, 4 P1, 15 P2, 5 P3. Blocker:
  package SRT giữ timestamp video nguồn, upload/admission và quote chưa
  canonical, worker không cooperative cancel/deadline, vòng đời source/output
  chưa khép kín. Browser file thật/VI/EN/desktop/mobile/ba trạng thái job/
  compare/transcript/ZIP/Range/console/network đã chạy; 19 targeted test PASS.
  Không sửa code, không deploy.
- [x] H27.7 Chat AI Studio DEEP — 2026-08-09: hồ sơ
  `docs/APP_AUDIT/chataistudio/2026-08-09-deep/` đủ 00–07 + 6 screenshot.
  Chốt `Q48 · M42 · E94 · BLOCKED`; 0 P0, 7 P1, 17 P2, 5 P3. Blocker:
  provider commercial/auth/data-control chưa có evidence; branch/restart không
  giữ AI context; lượt ảnh không khóa trần/confirm; stop/error/crash/idempotency
  có gap credit; delete để orphan image/thread; sidecar image path không được
  validate. Browser SSE/file/reload/delete/VI/EN/desktop/mobile/console/network
  đã chạy; 20 targeted test PASS. Không sửa code, không deploy.
- [x] H27.8 LTT Agent AI DEEP — 2026-08-09: hồ sơ
  `docs/APP_AUDIT/agent/2026-08-09-deep/` đủ 00–07 + 5 screenshot. Chốt
  `Q43 · M38 · E95 · BLOCKED`; 1 P0, 7 P1, 18 P2, 6 P3. Browser phát hiện
  dual orchestration tạo hai child text, quote 8 nhưng settle 6 rồi dừng trước
  image; starter nhập tay vẫn gọi text AI trả phí; cancel không hủy child,
  workflow library vắng, legacy `/agent` lộ dev jargon và mobile chỉ xem nhưng
  phơi catalog disabled. 225 backend + 52 frontend + typecheck PASS; lần gộp
  đầu TIMEOUT 125 giây được ghi đúng, không tính PASS. Không sửa runtime/deploy.
- [x] H27.9 Socialbot maintenance + Demo/Kịch bản/Media runtime contract —
  2026-08-09: bốn hồ sơ độc lập đủ 00–07 + browser evidence. Socialbot
  `Q41 · M35 · E94 · BLOCKED` (2 P0): customer thường vào được route operator,
  sửa token/worker state toàn cục dù app `public=False`; 411 targeted test PASS
  nhưng không có access-negative test. Demo `Q78 · M70 · E92 · INTERNAL`;
  customer `/demo` = 404 đúng. Kịch bản runtime `Q64 · M50 · E91 · BLOCKED`;
  route retired redirect Agent đúng nhưng literal Text/paid generation và
  dual-submit integration chặn G3/G4. Media Tools `Q59 · M47 · E90 · BLOCKED`;
  direct URL còn DNS-rebinding TOCTOU, artifact lifecycle và Agent orchestration
  chưa khép kín. 186 targeted runtime test PASS. Audit-only, không sửa/deploy.
- [x] H27.10 Tổng hợp cross-app — 2026-08-09: hồ sơ
  `docs/APP_AUDIT/portfolio/2026-08-09-deep/` khóa dashboard 13/13 manifest,
  12/12 hồ sơ sản phẩm/runtime, 248 raw finding = 3 P0/45 P1/146 P2/54 P3;
  khử trùng thành 12 shared program nhưng giữ acceptance từng app. Chốt thứ tự
  tuần tự: stop-the-line Socialbot → Agent → Media → Chat; shared foundation;
  Media/Kịch bản runtime → Agent; rồi từng customer app và portfolio P5. Audit
  inventory DONE; runtime fix cố ý 0% vì H27 audit-only, chờ Decision Gate.

Mỗi app bắt buộc có charter/current truth/journey-control registry/benchmark/
scorecard/findings/options/roadmap; UNKNOWN không được đổi thành PASS vì app khác
đã có test hoặc vì portfolio từng deploy thành công.

---

## H28 — Re-audit độc lập vòng 2 và kiểm định chính hồ sơ H27

H28 supersede điểm Evidence Confidence và trạng thái completeness của H27;
không thay finding/Q/Gate nếu không có bằng chứng mới. Audit-only, không sửa
runtime và không deploy.

- [x] H28.0 Integrity review — 2026-08-09: phát hiện H27 gắn nhầm source/test/
  browser thành E4; đúng phải là E1/E2/E3. Hiệu chỉnh hai evidence index và 12
  scorecard; E mới 38–61, trung bình 8 customer app 59,9.
- [x] H28.1 Browser route matrix — 2026-08-09: 13 manifest × desktop 1440×900
  + mobile 390×844; 26 navigation. Customer routes 200, Demo 404 đúng contract,
  Kịch bản/Media redirect Agent, Thumbnail redirect child mode; không failed
  request/JS console error ngoài 404 dự kiến. Phát hiện Socialbot overflow
  mobile và Upscale file input thiếu accessible name.
- [x] H28.2 Critical regression — 2026-08-09: registry/access/Agent run/executor/
  workflow API **89 PASS**, 1 deprecation warning. Test xanh không bác bỏ 3 P0
  vì thiếu negative authorization/exactly-once coverage tương ứng.
- [x] H28.3 A2/A4 completeness — 2026-08-09: Social/Demo/Kịch bản/Media còn
  control registry mỏng; Market Score của bốn phạm vi chuyển provisional. Bổ
  sung official-source benchmark 5–7 mẫu nhưng hands-on/plan/region còn thiếu.
- [x] H28.4 Corrected dashboard/roadmap — 2026-08-09: hồ sơ
  `docs/APP_AUDIT/portfolio/2026-08-09-reaudit/` ghi rõ phần đã xác minh và phần
  bắt buộc còn UNKNOWN. Q/Gate/P0 giữ nguyên; runtime fix/deploy 0%.

**Trạng thái đúng:** vòng re-audit hồ sơ đã hoàn thành; audit triệt để cấp E4
chưa hoàn thành vì thiếu telemetry/user test/provider/production và A2 chi tiết
của bốn runtime. Không được đổi UNKNOWN thành PASS.

---

## H29 — Deep audit Seedance: đối chiếu Bot Gemini + canary thật

H29 tiếp tục từ H28, chỉ audit/verification; **không sửa runtime và không
deploy**. Hồ sơ: `docs/APP_AUDIT/taovideo/2026-08-09/` (bổ sung
`08_DEEP_ROUND_BOT_GEMINI_REALJOB.md`).

- [x] H29.0 Preflight/Current Truth — 2026-08-09: đọc quyết định nền, plan,
  nhật ký, source Seedance và Bot Gemini read-only; fixture 8112 chỉ có UI,
  không có provider credential/R2.
- [x] H29.1 Browser A2 — 2026-08-09: desktop 1440 upload ảnh + video thật,
  role/handle/preview/quote; console warning=0, app request 2xx; mobile 390
  overflow=0, saved refs/output card.
- [x] H29.2 Real provider canary — 2026-08-09: Mini · 4s · 480p · 16:9, một
  ảnh + một video, prompt hai @handle; job `121eb14b…` DONE, log/progress/
  support ID, R2 output browser playable.
- [x] H29.3 Artifact verification — 2026-08-09: tải qua browser, `ffprobe`
  output H.264/AAC 864×496, 4.096s; frame strip xác nhận chuyển động và giữ
  visual reference.
- [x] H29.4 Billing/asset audit — 2026-08-09: quan sát 520→491→442 (78 actual
  vs 29 canonical video hold) → nâng F-001 lên P0; xác nhận audio Image/MIME
  bug và thiếu remote asset registry so với Bot Gemini.
- [x] H29.5 Hồ sơ/roadmap — 2026-08-09: cập nhật scorecard Q57/M64/E76,
  Gate BLOCKED, Control Registry, findings F-019..F-022, options/roadmap và
  evidence index; không BUILD.

**H29 kết luận:** core image+video generation đã có một canary E4 PASS, nhưng
app **chưa đạt “mọi tính năng vận hành tốt”**. G3 P0, audio contract và asset
lifecycle là stop-line; Phase 0A–0D trong `07_IMPLEMENTATION_ROADMAP.md` phải
được BUILD + regression trước canary trả phí tiếp theo.

## H30 — Job logging/observability toàn hệ thống

Mục tiêu: mọi app chạy qua hàng đợi có lịch sử job đủ để truy nguyên lỗi, credit
và worker; process log có redaction, correlation và cleanup có giới hạn. Không
đụng artifact/ledger bằng purge log, không deploy production trong hạng mục này.

- [x] H30.0 Audit hiện trạng — 2026-08-09: `JobEvent`, job history, support
  export, retention worker và 13 manifest đã được đối chiếu. Gap: thiếu mốc
  execution/duration/error fingerprint, credit hold detail và rotating file log
  thực thi.
- [x] H30.1 Lifecycle instrumentation — 2026-08-09: runner tự ghi
  `execution_started/completed/failed/cancelled`; `JobContext.event/stage` cho
  mốc đặc thù; details không ghi params/result/provider payload.
- [x] H30.2 Credit trace — 2026-08-09: ghi `credit_held`; settle ghi
  held/actual/adjustment; refund ghi số credit hoàn trong cùng transaction.
- [x] H30.3 Process log + TTL — 2026-08-09: thêm JSONL redacted rotating handler
  tại `platform_core/observability.py`; server/job worker/publisher/agent
  worker khởi tạo handler; chỉ prune `ltt-*.jsonl*` theo TTL 30 ngày mặc định.
- [x] H30.4 Tài liệu/runbook — 2026-08-09: `docs/LOGGING_OBSERVABILITY.md`
  và cập nhật `DATA_RETENTION_POLICY.md` với event catalogue, ma trận app,
  biến cấu hình, cách tra correlation/support export và ranh giới purge.
- [x] H30.5 Gate — 2026-08-10: `python tools\gate.py` **PASS 9/9**;
  full pytest 2.593 test mất 1.675,9s, tổng gate 1.702,9s. Gate bỏ đúng
  `tmp/`/`test-results/` khỏi collection vì đó là artefact browser/audit, không
  phải test source. Chưa deploy production; commit riêng H30 được tạo sau bước
  kiểm diff cuối.

## H31 — LTT Quality Lab: đo chất lượng đầu ra theo từng app

Mục tiêu: bổ sung bằng chứng chất lượng thực tế cho audit/debug; không nhầm
`Job DONE` với output tốt và không dùng một điểm proxy làm chân lý.

- [x] H31.0 Research + inventory — 2026-08-10: kiểm kê 13 manifest, benchmark
  Upscale hiện có và RTX 5060 Ti 16 GB; nghiên cứu nguồn chính VMAF/LPIPS/pyiqa/
  DOVER/VBench/JiWER/WhisperX/pyannote/PaddleOCR/COMET/DNSMOS/STOI/NISQA và
  LLM eval. Hồ sơ `docs/QUALITY_LAB/` khóa nguyên tắc, ma trận app, dataset/
  calibration và roadmap. **Chưa BUILD, chưa tải model, chưa deploy.**
- [x] H31.1 Measurement contract + license/model registry + privacy/retention —
  2026-08-10: schema vector v1, verdict `UNKNOWN/NOT_APPLICABLE`, artifact
  SHA-256, evaluator snapshot, environment không định danh; Q83 khóa input/
  transcript ephemeral và cấm release gate/model runtime-download.
- [x] H31.2 App Quality Lab operator-only: CPU/FFmpeg/SRT foundation + report —
  2026-08-10: app `/qualitylab`, Job giá 0, Pillow/ffprobe/media contract,
  SRT timing/overlap/CPS/CPL/WER chẩn đoán, JSON+HTML report và H30 timeline.
  Targeted **44 pass**; Playwright A–Z upload SRT/ảnh, worker/report/API,
  mobile 390 px không overflow, console 0 error, network 0 failed và input
  ephemeral còn 0 file. `python tools\gate.py` **PASS 9/9**; full pytest
  1.680,5 giây.
- [ ] H31.3 Pack Upscale calibrated: FR/NR/temporal/artifact/performance.
  - [x] H31.3a Paired diagnostic + dataset contract — 2026-08-10: PSNR/
    local-SSIM, bicubic delta, artifact proxy, hash ba đầu vào, consent/license/
    retention gate; mọi metric chưa calibrated giữ `UNKNOWN` và không release
    gate. Targeted **51 pass**, Playwright desktop/mobile console/network sạch,
    input ephemeral còn 0 file; `python tools\gate.py` **PASS 9/9**, full pytest
    1.661,8 giây. LPIPS là candidate chưa cài; pyIQA/DOVER bị chặn vì license.
  - [ ] H31.3b Evaluator provisioning: LPIPS offline + checksum; pyIQA và DOVER
    đang BLOCKED do license phi thương mại, không được cài/bật lặng lẽ.
    - [x] H31.3b1 Fail-closed provision gate — 2026-08-10: manifest source/
      license/version, artifact bytes/SHA, chống traversal, không tải mạng và
      chỉ public status; LPIPS chưa có assets hiển thị `manifest_missing`.
    - [~] H31.3b2 Cấp thật LPIPS 0.1.4 + AlexNet offline, ghi checksum rồi
      benchmark; thiếu file vẫn giữ evaluator disabled/`UNKNOWN`.
      **Cấp xong 07/09/2026; còn benchmark.**

      ```
      alex_linear_v0.1.pth        6.009 bytes   df73285e35b22355...
      alexnet-owt-7be5be79.pth  244.408.911     7be5be79115947 2b...
      verify_manifest("lpips") -> ready: True, reason: "verified"
      ```

      ⭐ **Đối chứng độc lập cho tệp 233 MB:** torchvision nhúng **8 ký tự đầu
         của SHA-256 vào chính tên tệp** (`...-7be5be79.pth`), và băm tính ra
         bắt đầu đúng bằng `7be5be79`. Tức có một phép kiểm toàn vẹn **không
         đến từ manifest do ta tự viết** — nếu chỉ so với con số mình vừa tự
         ghi thì đó là một vòng tự tham chiếu.

      ⭐ Linear weight **trích từ chính wheel `lpips-0.1.4`**, không tải rời:
         nguồn và version khớp nhau theo cấu tạo.

      **Cổng provision đã kiểm có răng** — ba phép tiêm trên một bản sao
      (`verify_manifest` nhận tham số `root`, nên không đụng bản thật):

      | tiêm | kết quả |
      |---|---|
      | lật **một bit** trong backbone | `ready: False` |
      | xoá linear weight | `ready: False` |
      | khai `license` sai (`MIT`) | `ready: False` |

      ⛔ **Còn lại: benchmark CPU/GPU + peak VRAM + latency** (điều kiện 6 của
         `04_EVALUATOR_LICENSE_MODEL_MATRIX.md`). Chưa có nó thì evaluator
         **vẫn `disabled`** — cấp được asset **không** phải bật được metric,
         và bật được metric **không** phải bật được release gate.

      ⚠️ Weight nằm ở `data/qualitylab/models/`, đã thêm vào `.gitignore`:
         `data/` không bị ignore mặc định, nên 233 MB thả vào đó sẽ hiện trong
         `git status` — và deploy chép **cả cây** kể cả phần chưa commit
         (**Bẫy 30**).
  - [ ] H31.3c Video temporal + performance: frame sampling, flicker/motion,
    decode/encode contract, latency/VRAM/throughput trên GPU đích.
    - [x] H31.3c1 Paired video diagnostic — 2026-08-10: contract A/V, sample
      frame tránh EOF, PSNR/SSIM/bicubic delta, temporal residual và source-job
      throughput. Targeted **28 pass**; Playwright video A-Z/report auto-refresh,
      mobile 390 px, console/network sạch, ephemeral 0; full gate **PASS 9/9**,
      pytest 1.670,9 giây.
    - [x] H31.3c1a VMAF evidence — 2026-08-10: dùng `libvmaf` trong FFmpeg đã
      cài, pin rõ model `vmaf_v0.6.1`, hash binary triển khai trong evaluator
      snapshot và lưu version libvmaf trong evidence. VMAF vẫn luôn `UNKNOWN`
      trước calibration, không thay temporal/artifact/human A/B. Targeted
      **29 pass**; Playwright mobile A-Z hiển thị 99,357 cho cặp video giống
      nhau nhưng overall vẫn UNKNOWN, console/network sạch, ephemeral 0;
      full gate **PASS 9/9**, pytest 1.660,7 giây.
    - [ ] H31.3c2 GPU evidence: benchmark dataset trên GPU đích và ghi peak VRAM
      theo job.
      - [x] H31.3c2a Isolated GPU sampler — 2026-08-10: lấy mẫu 200 ms theo
        UUID, baseline/peak/delta whole-device, từ chối GPU bận mặc định và hash
        engine/model/source. Ma trận 4 ca Fast/Quality × 1080p/1440p trên RTX
        5060 Ti đều pass contract; Fast +848 MB/5,53–5,94 fps, Quality
        +11.176–11.177 MB/0,68–0,70 fps, sampling error 0. Hồ sơ:
        `docs/QUALITY_LAB/05_UPSCALE_GPU_EVIDENCE.md`. Targeted **22 pass**;
        full gate **PASS 9/9**, pytest 1.690,8 giây.
      - [ ] H31.3c2b Production contract: runtime Upscale chưa ghi peak VRAM
        theo job nên report job thật vẫn `UNKNOWN`. H32.6 đã sửa manifest từ
        4.000 lên 12.000 MB theo peak Quality 11.176 MB và thêm CLI evidence;
        telemetry per-job/scheduler split Fast–Quality vẫn là phase riêng theo
        Q83, chưa được coi là hoàn tất.
  - [ ] H31.3d Calibration: tối thiểu 30 ảnh + 12 video có slice/degradation,
    human A/B mù, baseline và threshold theo từng slice/model.
    - [x] H31.3d1 Blind calibration contract — 2026-08-11: dataset thêm
      media kind/split/tags/artifact hash; assignment trái/phải dùng token HMAC
      không lộ storage key/model role; vote ẩn rater ID, ký HMAC chống sửa và
      chặn vote trùng. Aggregate tính Fleiss kappa/Spearman, chỉ báo
      `ready_for_threshold_review`, luôn giữ `release_gate_eligible=false`.
      CLI fixture và 7 test chuyên biệt PASS; full gate **PASS 9/9**, pytest
      1.655,0 giây. Runbook:
      `docs/QUALITY_LAB/06_HUMAN_AB_CALIBRATION.md`.
    - [ ] H31.3d2 Materialize dataset có license: tối thiểu 30 ảnh + 12 video,
      đủ six slice/five degradation, tách development/calibration/blind set.
      - [x] H31.3d2a Materializer fail-closed — 2026-08-11: intake chỉ nhận
        relative path trong source-root, probe file thật bằng Pillow/ffprobe,
        bắt buộc `license_evidence_id`, consent/retention với production, hash
        hai artifact, copy atomically và không ghi đè version cũ. Readiness
        kiểm đủ 30 ảnh/12 video, six slice/five degradation/three split nhưng
        luôn giữ `release_gate_eligible=false`. Targeted **19 pass**; quick gate
        **PASS 8/8**; full gate **PASS 9/9**, pytest 1.831,4 giây. Runbook:
        `docs/QUALITY_LAB/07_DATASET_MATERIALIZATION.md`.
      - [ ] H31.3d2b Khai báo intake và materialize media thực tế đủ số lượng;
        không tự suy luận license từ file tìm thấy trên máy.
    - [ ] H31.3d3 Thu vote người thật: tối thiểu 3 rater hợp lệ/case, review
      agreement/correlation theo slice rồi version threshold; không dùng vote
      synthetic trong test làm bằng chứng sản phẩm.
- [ ] H31.4 Pack AutoSub calibrated: transcript/alignment/diarization/render.
- [ ] H31.5 Pack Seedance/Image/Thumbnail/Clip/Text/Agent tuần tự.
- [ ] H31.6 Release regression, trend, canary, rollback và LTT-AQA audit.
- [x] H31.R1 Production deploy checkpoint — 2026-08-11: phát hành commit
  `82567eb` cùng checkpoint `f6eca9e` bằng archive 1.610 file/83,5 MB, SHA-256
  `ebd4a731…f0ea`; deploy `EXITCODE=0`, backup + `app.previous` sẵn sàng,
  Alembic head, ba service Running, health local/public ready. Playwright
  desktop/mobile landing không overflow, console/request app error 0; auth
  boundary Quality Lab đúng 303. Hồ sơ:
  `docs/QUALITY_LAB/08_PRODUCTION_DEPLOY_20260811.md`.

Điều kiện chặn: không dùng production media khi chưa consent/retention; không
tải model runtime; không bật release gate cho metric chưa tương quan human;
không sửa platform/server chỉ để thêm app Quality Lab.

## H32 — Batch audit/nâng cấp AppLttStudio_11082026

Nguồn yêu cầu/tài nguyên chỉ đọc:
`C:\Users\Thang Tuong\Desktop\AppLttStudio_11082026`. Quy trình chi tiết và
output naming: `docs/APP_AUDIT/BATCH_2026-08-11/00_MASTER_PLAN.md`.

- [x] H32.0 Charter, source truth, asset inventory và browser harness cô lập —
  2026-08-11: kiểm kê đủ 6 folder/MoTa/asset/hash/media probe; khóa thứ tự,
  evidence contract và output naming trong master plan; fixture AutoSub riêng
  cổng 8140, production 8100 không bị tác động.
- [x] H32.1 AutoSub Video — 2026-08-11: đổi tên manifest/nav; Playwright thật
  upload 15s → SRT → TikTok Bold/Montserrat 64/middle → quote 2 credit → NVENC
  render 3s → download/media/frame/history/reload/mobile. Output H.264+AAC
  864×496/24fps/15,069s, console 0, network 0 lỗi; **36 pytest + 13 Vitest
  pass**. AI WhisperX/Pyannote/Gemini chưa cấu hình nên giữ gate có điều kiện;
  roadmap/scorecard/finding ở `docs/APP_AUDIT/autosubvideo/2026-08-11-h32/`.
- [x] H32.2 Prompt AI — 2026-08-11: đối chiếu Prompt Seedance Studio read-only;
  nối 8 Style/4 Meta/4 Snippet vào prompt thật; brief đủ field, explicit save,
  preview/preflight miễn phí, quote khóa payload và apply đúng revision. Sửa GET
  locale 302; browser desktop/mobile console sạch, journey mới toàn 200;
  **83 pytest + 24 Vitest pass**, frontend build pass. Provider E4 chưa cấu hình
  nên gate CONDITIONAL; score 72/100 và hồ sơ tại
  `docs/APP_AUDIT/prompt-ai-ommi/2026-08-11-h32/`.
- [x] H32.3 Tạo ảnh AI — 2026-08-11: audit General + YouTube Thumbnail trên
  fixture cô lập; sửa preview công khai model/giá và đầy đủ Brand Kit/reference;
  edit/remix handoff pass; desktop/mobile không overflow, console 0, request lỗi
  0; **34 pytest pass**, scanner secret/contract/undefined pass. Q 74 · M 70 ·
  E 88 · INTERNAL; provider E4 và chênh pricing cùng model còn là blocker, nên
  không giả output fixture thành kết quả AI và không deploy. Hồ sơ:
  `docs/APP_AUDIT/taoanh/2026-08-11-h32/`.
- [x] H32.4 Tạo Clip ngắn — 2026-08-11: upload/reuse source 523,9 MB; ba
  job Fast thật, credit 28/job; sửa SRT timeline, progress lùi/spam, NVENC âm
  giả RTX 50xx, pixel geometry 4:5 và hardening upload. Output cuối H.264 NVENC
  1080×1350 SAR 1:1/AAC/18,633s, decode pass; ZIP SRT 0..19,750s; mobile sạch.
  **21 targeted pass**, quick gate chạy lần đầu fail i18n carry-forward Prompt
  AI rồi đã sửa; kết quả rerun ghi trong nhật ký. Q 77 · M 58 · E 95 · INTERNAL;
  matrix tier/count/genre, cancel/lifecycle/editor còn trong roadmap tại
  `docs/APP_AUDIT/taoclipngan/2026-08-11-h32/`.
- [x] H32.5 Seedance — 2026-08-11: visual-only đúng MoTa, không submit job/
  provider; composer scroll+dock, asset disclosure, i18n status/title, honest
  quote failure, mobile inert/close/focus. Browser 1.586×992 + 390×844 không
  overflow, final console 0/request 200–206; **50 targeted pass**, quick gate
  **PASS 8/8**. Q 63 · M 64 · E 84 · BLOCKED bởi P0 billing kế thừa; hồ sơ tại
  `docs/APP_AUDIT/taovideo/2026-08-11-h32/`.
- [x] H32.6 Upscale — 2026-08-11: actual source/browser batch, **17/17 GPU
  option matrix**, full Fast 15,069s pass; sửa smooth 24→48, blob metadata,
  mobile inert/focus, fake Pro/jargon/raw worker status; manifest 12.000 MB theo
  Quality peak 11.176 MB. Desktop/mobile console 0/request lỗi 0; **56 targeted
  pass**, quick gate **PASS 8/8**. Quality Lab contract PASS nhưng perceived
  quality `UNKNOWN`; dual-GPU current bị GPU0 external workload chặn an toàn.
  Q 72 · M 57 · E 94 · BLOCKED; hồ sơ tại
  `docs/APP_AUDIT/upscalevideo/2026-08-11-h32/`.
- [x] H32.7 Release audit — 2026-08-11: tổng hợp 6 app tại
  `docs/APP_AUDIT/BATCH_2026-08-11/01_RELEASE_AUDIT.md`; Q trung bình 71,3,
  M 64,3, E 89,2 nhưng overall BLOCKED theo gate cao nhất. Lập release plan
  tuần tự money → upload/lifecycle → provider → calibration/scheduler → UX →
  staging. Full `python tools\gate.py` **PASS 9/9**, 1.777s; pytest 1.734,2s,
  ba frontend và năm scanner PASS. Browser final sáu app desktop/mobile console
  0/request app lỗi 0. **Chưa deploy**; production 8100 giữ nguyên.

## H33 — Release hardening theo H32.7

- [x] H33.R1a Seedance money source contract — 2026-08-12: Q84 cap thu khách
  tại hold, provider overage thành warning variance; settle/refund khóa exactly-once;
  signed quote 15 phút khóa user/config/input/count và intent idempotent toàn batch.
  Sửa luôn quote upload 422. **48 targeted pass**, quick gate **PASS 8/8**;
  Playwright desktop/mobile MP4 thật 6,59 MB quote 47→29, double submit một
  job/hold, balance 500→424 đúng hai job 47+29, console sạch.
- [ ] H33.R1b Canary provider trên exact release candidate + ledger G3. Không
  chạy trên production cũ; thực hiện trong R6 staging hoặc môi trường cô lập có
  provider key test.
- [x] H33.R2 Shared upload/artifact lifecycle — 2026-08-12: Q85, Alembic
  `a5b6c7d8e9f0`, staging owner/app + MIME/signature/actual-size/quota/rate/TTL,
  hold→promote + DB compensation, retry không giữ tiền hai lần, cleanup lỗi/hủy,
  worker sweep/CLI reconcile. HTTP integration bốn app PASS; Playwright Upscale
  MP4 6,59 MB desktop/mobile console 0. **Source PASS; production migration
  đã deploy tới Q89 theo yêu cầu ngày 2026-08-12; staging CORS/direct-upload
  smoke vẫn chuyển R6.**
- [ ] H33.R3 Provider matrices AutoSub → Prompt → Image → Clip.
  - [x] AutoSub local engine + Studio A–Z — 2026-08-12: WhisperX Tiny/
    Large-v3 smoke GPU1, job queued→done, project 9 cue, NVENC render 1080p
    H.264/AAC, output subtitle bundle và ledger 1.000→996 đúng quote. Sửa lỗi
    transcribe không khởi tạo polling; thêm preflight fatal/warning và Q88 JSON
    API error. **Technical conditional PASS; không gọi là quality PASS.**
  - [x] AutoSub source draft lifecycle — 2026-08-12, Q89: staging validation,
    attach owner/app/project, TTL 30 ngày/touch khi mở, sweep/reconcile, báo tải
    lại khi source hết hạn; migration `b6c7d8e9f0a1`, browser reload/mobile PASS.
  - [ ] AutoSub quality: corpus VI/EN ground truth WER/timing, pyannote DER và
    Gemini translation.
  - [ ] Prompt provider/output/ledger matrix trên exact RC.
  - [ ] Image provider/output/ledger matrix trên exact RC.
  - [ ] Clip provider/output/ledger matrix trên exact RC.
- [ ] H33.R4 Upscale commercial calibration/scheduler.
  - [x] Scheduler lane Fast/Quality — 2026-08-12, Q86: submit UI và Seedance
    chọn `render.fast` 2.000 MB hoặc `render.quality` 12.000 MB; legacy
    `render` 12.000 MB giữ tương thích job cũ/ToolSpec. **50 targeted pass,
    quick gate PASS 8/8; full gate PASS 9/9 trong 1.806,3s.**
  - [ ] Dataset HR có license/consent ≥12 video, blind A/B ≥3 rater/case và
    threshold quality/cost/P95 có version. Không biến fixture/Lanczos thành PASS.
  - [ ] Qualified dual-GPU: chỉ chạy khi cả hai card qua idle guard; GPU0 đang
    baseline 1.126 MB > 512 MB nên chưa đủ điều kiện bằng chứng.
- [ ] H33.R5 UX/recovery parity.
  - [x] Job Center adaptive progress/recovery — 2026-08-12, Q87: poll 2s khỏe,
    exponential backoff tới 30s khi offline, online reset, terminal reload một
    lần để nạp Retry/Artifact. **29 targeted pass; quick gate PASS 8/8;
    full gate PASS 9/9 trong 1.783,8s; Playwright queued/offline/online/cancel/
    terminal/mobile PASS, console cuối 0.**
  - [ ] Draft recovery có privacy/user scoping cho form không dùng AppProject.
  - [ ] Preflight/confirmation matrix cho job giá cao/dài còn lại; AutoSub đã
    chặn fatal và cảnh báo trước confirm, còn Clip/Image/Prompt.
  - [ ] Browser A–Z sáu app trên exact staging RC.
- [ ] H33.R6 Staging, rollback drill và production decision riêng.
  - [x] Deploy production theo yêu cầu trực tiếp — 2026-08-12: commit
    `b957049`, release SHA-256 `6380f624...f9a28b`, backup PostgreSQL/runtime,
    Alembic head `b6c7d8e9f0a1`, ba service Running, public AutoSub bundle/API
    desktop/mobile PASS và console app 0.
  - [ ] Exact staging matrix sáu app, CORS direct upload, provider/ledger
    canary và rollback drill; production deploy trên không thay thế các gate này.

## H34 — Hồ sơ hệ thống tự cập nhật cho AI/người tiếp quản

- [x] H34.1 Schema và phạm vi — 2026-08-12, Q90: snapshot không chứa secret/
  runtime data, có thứ tự nguồn chân lý và fingerprint source.
- [x] H34.2 Generator — `tools/build_system_profile.py` sinh atomically UTF-8
  không BOM; `--check` deterministic, cấu hình tại
  `tools/system_profile_config.json`.
- [x] H34.3 Coverage — 14 app, manifest/job/ToolSpec/file map, toàn bộ route
  HTTP, bảng SQLAlchemy, migration, frontend, tên env, test/deploy và source
  index; test tự đối chiếu app/job/tool/migration/frontend.
- [x] H34.4 Anti-stale — `system profile` là bước bắt buộc của quick/full gate;
  `AGENTS.md` và `CLAUDE.md` yêu cầu đọc hồ sơ để định vị sau nguồn chân lý.
- [x] H34.5 Nghiệm thu — 2026-08-12: targeted contract/release **147 pass**,
  secret scan 0 finding; quick gate **PASS 9/9** trong 33,2s; full gate
  **PASS 10/10** trong 1.852,1s, pytest 1.818,5s; khóa trong checkpoint H34.
- [x] H34.6 Full-source dossier — 2026-08-12, Q91 thay Q90: bỏ mô hình chỉ mục;
  nhúng nguyên văn toàn bộ code/config nguồn thuộc 14 miền vận hành, gồm đủ
  `apps/`, backend/frontend, worker/sidecar, `cutclipshort`, migration, deploy,
  setup, tool và test; không có trần dung lượng. Mỗi block có path/hash/byte/
  dòng; test khóa coverage/integrity và exclusions. Kết quả nghiệm thu thật ghi
  tại mục H34.6 mới nhất trong `NHAT_KY.md`.

---

## H35 — Public API `/api/v1` cho khách lập trình

Quyết định nền: **Q92**. Nhật ký thật: mục `2026-08-15 — H35` trong
`NHAT_KY.md`. Nhật ký từng bước của pack: `docs/PUBLIC_API/EXTENSION_PROGRESS.md`.

- [x] H35.1 Nhân V2 — 2026-08-13: 24 route đóng băng ở `server/api/inventory.py`
  (so hai chiều route thật ↔ inventory ↔ OpenAPI), lỗi RFC 9457, khoá
  `ltt_sk_…` băm HMAC-SHA256 với pepper **ngoài CSDL**, quote ký số,
  idempotency trong CSDL, hold → quyết toán/hoàn **đúng một lần**.
- [x] H35.2 Không dựng engine thứ hai — dùng lại nguyên `jobs`, `credit`,
  `upload_sessions`, `storage`, `api_pool`; `platform_core/public_api/` là
  domain, `server/api/` là bề mặt HTTP, đúng Q92.
- [x] H35.3 Cổng cho lập trình viên — 2026-08-13→14: 15 trang (project, khoá,
  docs, playground, giá, nhật ký request, job, usage, webhook, thông báo, dữ
  liệu & lưu trữ).
- [x] H35.4 Bảng điều khiển vận hành — 2026-08-14→15: 12 trang admin, gồm
  chính sách/quota/kill switch, phiên bản giá và margin, truy vết hỗ trợ.
- [x] H35.5 Chế độ thử — 2026-08-14: khoá `ltt_tk_…` **không bao giờ** tiêu
  credit; sandbox lấy hình dạng từ hợp đồng nên không lệch được khỏi production.
- [x] H35.6 Riêng tư và lưu trữ — 2026-08-15: 42 store khai lớp/hạn/lý do, 6
  vòng dọn chạy trong worker, bản xuất dữ liệu của khách.
- [x] H35.7 Chứng nhận 100% — 2026-08-15: 14 app, 21 ToolSpec, 4 alias model, 5
  operation đang mở; **16 tool đóng có lý do ghi ra và máy kiểm hai chiều với
  registry** (`APP_API_COVERAGE_FINAL.md`, `test_212`).
- [x] H35.8 Nghiệm thu toàn nền tảng — 2026-08-15: bốn hành trình chạy thật
  (lập trình viên, máy chủ ngoài, vận hành, chỗ các hệ giao nhau), 8 kịch bản
  đo tải, full gate **PASS 13/13** (pytest 4.591 s), kiểm trình duyệt 27 trang.
  Kết luận `API_PLATFORM_FULL_READY_FOR_CONTROLLED_DEPLOY` ghi tại
  `docs/PUBLIC_API/API_PLATFORM_FULL_RELEASE_READINESS.md`.
- [ ] H35.9 **Điều kiện của chữ "controlled" — cần máy chủ thật.** Năm điều kiện
  ở §11 của `API_PLATFORM_FULL_RELEASE_READINESS.md`:
  - [x] **H35.9a — tách ban sao pepper khỏi CSDL (phần công cụ), 2026-08-17.**
    Đo trên máy chủ: `ltt_data_20260817_023001.zip` chứa **cả** `app.env` lẫn
    `lttplatform.dump` trong **một** zip — nghĩa là một bản sao bị lấy cắp là đủ
    để đọc token đã mã hoá (`LTT_TOKEN_ENCRYPTION_KEY` nằm ngay cạnh bản mã) và,
    sau khi Public API lên, tấn công khoá API của khách ngoại tuyến
    (`LTT_API_KEY_PEPPER` nằm ngay cạnh hash). Sửa: `backup.ps1` ghi **hai**
    archive riêng — `ltt_data_*.zip` → `-BackupDir`, `ltt_secrets_*.zip` →
    `-SecretsDir` (mặc định thư mục **anh em** `<BackupDir>-secrets`, không phải
    thư mục con, để đồng bộ off-site không vô tình kéo theo bí mật).
    `5-lich-backup.ps1` truyền `-SecretsDir` và siết ACL cả hai thư mục;
    `restore.ps1` từ chối `-Live` trên bản secrets (đổ vào `data\` là sai chỗ, và
    ghi đè `app.env` của dịch vụ đang chạy có thể làm nền tảng không khởi động
    lại được). Bốn test chốt trong `test_45`, chạy thật hai kịch bản trên thư mục
    giả: tách đúng hai zip, và **máy mới cài (data\ rỗng) vẫn có bản sao secrets**
    — trước đây nhánh đó `exit 0` nên sẽ không sao lưu gì cả.

    **Đã áp lên máy chủ 2026-08-17**, và lúc áp phát hiện lỗ hổng thứ hai:
    `D:\LTTBackups` **chưa từng được siết ACL** (mọi ACE đều thừa kế từ `D:\`,
    gồm `Authenticated Users:(M)`), nên mọi tài khoản đăng nhập được máy đều đọc
    được `app.env` + dump CSDL. Test cũ chốt được *script có lệnh `icacls`*,
    không chốt được *lệnh đó đã chạy trên máy thật*. Nay hai thư mục chỉ còn
    `Administrators` + `SYSTEM`; bản sao ngày `154433` đã tách đúng
    (`ltt_data_*` không còn `app.env`). **13 bản cũ vẫn gói chung** — đã được ACL
    bảo vệ và tự rụng theo hạn giữ 14 bản.
  - [~] H35.9b **Pepper đã sinh 2026-08-17** — `LTT_API_KEY_PEPPER` (64 ký tự)
    + `_VERSION=1` ghi vào `secrets\app.env`, UTF-8 không BOM, giá trị chưa từng
    hiện ra ở đâu. **Còn lại: cất một bản NGOÀI máy này** — việc của người.
  - [x] H35.9c **Đo trên máy chủ thật qua Cloudflare — XONG 2026-08-17.**
    `LTT_PUBLIC_API=1` đã bật (giữ `LTT_PUBLIC_API_TOOLS` **vắng mặt = rỗng**).
    Công cụ mới `tools/api_prod_canary.py` (prepare/probe/cleanup) theo đúng nếp
    canary sẵn có: tạo `api-load-canary@lttstudios.com`, cấp khoá **chỉ-đọc**
    (`tools:read` + `jobs:read` — `jobs:create` thuộc `SPENDING_SCOPES` và không
    được cấp, nên phép đo **không tiêu được đồng nào**), đo, rồi thu hồi khoá +
    vô hiệu tài khoản.

    p50 **88–92 ms**, p95 90–116 ms, **không có 429 nào**. §6 đo p50 34,9 ms
    trong tiến trình không mạng; chênh ~55 ms là TLS + biên Cloudflare + tunnel,
    và nó gần bằng nhau ở cả đường trả 403 (không chạm CSDL) — nên phần cố định
    là đường truyền, không phải ứng dụng. PostgreSQL thật **không** làm
    control-plane chậm thấy được. Chi tiết ở §6 của readiness doc.

    **Bằng chứng đáng giá nhất:** `GET /api/v1/tools` trả `200` với danh sách
    tool **RỖNG** — fail-closed của Q92 được kiểm bằng một khoá thật trên hệ
    thống đang chạy, không phải bằng cách đọc lại biến môi trường.
  - [x] H35.9d **Trần 100 MB — ĐÃ CHỨNG MINH trên tunnel thật 2026-08-17.**
    `POST` 101 MB tới `/api/v1/jobs` → **`413 Payload Too Large`, `Server:
    cloudflare`**, ngắt sau 1,1 MB; origin không hề thấy request. Cùng path với
    95 MB → biên chuyển tiếp, origin trả lời. Vậy biên quyết định bằng
    `Content-Length` ngay từ đầu, trần nằm giữa 95 và 101 MB — khớp tài liệu
    Cloudflare và **xác nhận multipart ≤90 MB của Q48 đi lọt**.

    **Trần 100 giây: cố ý KHÔNG chứng minh được.** Production không có endpoint
    nào treo quá 100 giây — đó chính là ràng buộc bất biến #5, và cũng chính là
    biện pháp giảm thiểu. Dựng một endpoint treo trên production chỉ để đo là
    đổi một rủi ro thật lấy một con số. Ghi là *chưa đo, có lý do*, không ghi
    là đã đạt.

    **Phát hiện kèm theo:** `POST /login` bị Cloudflare trả `403` +
    `Cf-Mitigated: challenge` (managed challenge) cho client không phải trình
    duyệt. Đã kiểm: thách đố này **chỉ áp cho `/login`**, không áp cho
    `/api/v1/*` (POST tới đó đi thẳng tới origin). Nếu sau này có luật WAF mở
    rộng sang `/api/v1`, đường máy-gọi-máy sẽ chết — cần kiểm lại mỗi khi đổi
    cấu hình WAF.
  - [~] H35.9e **Đường ra đã có và kênh ĐÃ BẬT (2026-08-17).**
    ⚠️ *Đầu đề cũ ghi "kênh chưa bật" — sửa 07/09 vì nó mâu thuẫn với
       chính thân ô ngay bên dưới ("Đã bật trên máy chủ 2026-08-17"). Đo lại
       `secrets/app.env` trên máy chủ: cả ba khoá đều có mặt —
       `LTT_OPS_ALERT_EMAIL`, `LTT_MAIL_FROM`, `RESEND_API_KEY`. Ô vẫn để `[~]`
       vì việc còn nợ (**xoay khoá provider**) là hành động của chủ sản phẩm,
       không phải việc agent tự làm — xem cuối ô.*
    `platform_core/public_api/ops_alerts.py` đọc `metrics.aggregate()` — **cộng
    qua mọi tiến trình**, không phải `snapshot()` trong một tiến trình — và gửi
    email cho `LTT_OPS_ALERT_EMAIL`, chạy trong vòng bảo trì đã có lease (H36).
    15 test ở `test_222`, đã kiểm "có răng": hoàn nguyên quy tắc sườn → đỏ 2/15.

    **Kích theo sườn**, và cái giá được ghi rõ trong cả docstring lẫn thân thư:
    một sự cố kéo dài **chỉ gửi MỘT thư**. Chọn vậy để không phải thêm bảng
    chống trùng + migration lên CSDL vừa deploy — khoá chống trùng của
    `alerting.py` bám `user_id`, mà cảnh báo vận hành không có chủ sở hữu.

    **Phát hiện 2026-08-17:** `app.env` production **không có `LTT_SENTRY_DSN`**,
    nên Q21 (bắt lỗi production bằng Sentry) chưa bao giờ có hiệu lực trên máy
    chủ này. Chủ sản phẩm chọn cả hai kênh: Sentry cho exception, email cho
    ngưỡng.

    **Đã bật trên máy chủ 2026-08-17:** Sentry project `ltt-platform` (FastAPI,
    org `le-thanh-trung`) — `LTT_SENTRY_DSN` đã nạp, `sentry_sdk` 2.66.1 có sẵn
    trong venv, `server/telemetry.py` đặt `send_default_pii=False` + `scrub_event`
    đúng điều kiện kèm theo của Q21. `LTT_OPS_ALERT_EMAIL` =
    `giaitritruyenthongltt@gmail.com`. Ba dịch vụ nạp 40 biến, restart,
    `/health/ready` = ready.

    **`capacity.check` thấy pool thật — đã kiểm 2026-08-17:** 6 khoá provider
    trên 5 nhà (`gemini`, `byteplus`, `apiai`, `cheapkeyai`, `plenx`), tất cả
    `enabled` và khoẻ. Nên nhánh "im lặng vì pool rỗng" của `capacity.py` không
    áp dụng ở đây.

    **Còn nợ đúng một việc:** *xoay* khoá provider. Đó là hành động của chủ sản
    phẩm — phải lấy credential mới từ từng nhà cung cấp, và xoay sai thì job của
    khách chết. Không phải việc agent tự làm.
- [x] H35.10 ✅ **XONG 2026-08-29** — `video.upscale` và `video.subtitle` **đang
  bán thật** trên `/api/v1` (deploy 15:58, kiểm trên `openapi.json` công khai
  kèm đối chứng âm). `video.short_clips` **vẫn đóng** — chờ H35.10c.
  ⭐ Và kế hoạch đã nói **đúng**: mở được là nhờ **a+b**, không phải chỉ a.
  Chỉ có a thì worker vẫn chạy ffprobe riêng và `math.ceil` lệch một credit là
  quote đã ký bị vượt.
  Mở tool video. **Câu "chờ MỘT thay đổi, sửa một chỗ mở được cả ba"
  ở bản trước là SAI** — điều tra mã thật ngày 2026-08-17 cho thấy là **ba việc
  con**, và nó chỉ mở được **hai** tool chứ không phải ba. Giữ lại câu sai này
  để nhớ kiểu lỗi: ước lượng viết lúc chưa đọc `_dam_bao_giu_cho`.

  Chẩn đoán đã nằm sẵn trong `apps/upscalevideo/manifest.py:94-101`: giá phụ
  thuộc `duration_s` **do người gọi khai**, và worker **nâng giữ chỗ** khi đo
  được thời lượng thật. Với giao diện thì ổn — có người chọn file họ nhìn thấy.
  Với máy-gọi-máy thì nó phá lời hứa của một quote đã ký (Q84, sự cố Seedance
  giữ 29 thu 78).

  Đường đi hiện tại, giống hệt nhau ở `POST /quotes` và `POST /jobs`
  (`server/api/jobs.py:216` và `:281`):

  ```
  build_job_params() -> price(tool, params) -> credit_for() -> _cost(params["duration_s"])
  ```

  - [x] **H35.10a — ✅ XONG 2026-08-29** (`bf6cd84`). App khai `measured_from`,
    nền tảng giải quyết chung; `duration_s` vào `hidden` nên khách không gửi
    được nữa. `test_325`, 20 phép kiểm. **đo thời lượng phía máy chủ lúc báo giá.** File đã ở
    `staging/` từ lúc upload (Q85) và đã qua kiểm magic-byte, nên đo được ngay:
    R2 thì `storage.try_url_for()` cho ffprobe đọc thẳng URL (không tải cả
    2 GB về), local thì `storage.open()`. Đặt `params["duration_s"]` bằng số đo
    **trước** khi tính giá, ở cả hai route. Hai route tự khớp nhau vì
    `create_job` đã có sẵn phép so `price_changed`. Dùng
    `platform_core.media.duration_seconds`, **không** viết lại ffprobe.
    *Rủi ro thấp: không chạm sổ credit.*
  - [x] **H35.10b — ✅ XONG 2026-08-29** (`7850ea5`). Giữ chỗ đầu tiên của job
    API bị **niêm phong**; worker đòi nâng thì nền tảng **hấp thụ** chứ không
    ném — ném sẽ giết job của khách vì một khác biệt làm tròn một credit.
    Đường web vẫn nâng được, và đó là chủ ý. `test_326`, 10 phép kiểm.
    **trần cứng cho việc nâng giữ chỗ của job đến từ API.**
    H35.10a làm quote **đúng**, không làm nó **không thể sai**:
    `_dam_bao_giu_cho` vẫn còn đó và vẫn nâng nếu worker tính ra số khác (trim,
    preview, hay bất kỳ khác biệt nào giữa "thời lượng file" và `eff_dur`).
    Dựa vào "hai số này chắc bằng nhau" **chính là** kiểu lập luận đã đẻ ra Q84.
    Muốn Q84 là bảo đảm cấu trúc thì phải có trần ở tầng credit.
    *Rủi ro CAO: chạm `platform_core/credit.py`. Làm riêng một phiên, gate đầy
    đủ trước và sau, có đường lùi viết trước.*
  - [ ] **H35.10c — trần đồng thời GPU cho `video.short_clips`.** Việc thứ ba,
    **không liên quan thời lượng**: `APP_API_COVERAGE_FINAL.md` ghi *"thêm ràng
    buộc GPU chưa chốt được trần đồng thời"*. Làm xong a+b thì mở được
    `video.upscale` và `video.subtitle`; `video.short_clips` **vẫn đóng** cho
    tới khi có c.

---

## H36 — Củng cố phần thi hành của Public API

Audit: `docs/PUBLIC_API/AUDIT_API_2026-08-15.md`. Thiết kế:
`docs/PUBLIC_API/PLAN_RUNTIME_HARDENING.md`. Nhật ký thật: mục
`2026-08-16 — H36` trong `NHAT_KY.md`.

Nguyên nhân gốc của cả ba lỗi P0: **mọi vòng nền được viết với giả định "chỉ một
tiến trình chạy nó"**, trong khi số tiến trình worker mặc định bằng số GPU.

- [x] H36.1 Bộ khung đa tiến trình — 2026-08-16: `test_214` đẻ tiến trình worker
  THẬT trên PostgreSQL thật. Viết **trước** khi sửa, và có kiểm "có răng": hoàn
  nguyên `claim_due` thì đỏ 8/8.
- [x] H36.2 Lease có tên + vòng bảo trì chạy luồng riêng — `platform_core/leases.py`.
- [x] H36.3 Outbox claim đúng chuẩn hàng đợi job + cooldown cảnh báo do CSDL
  cưỡng chế (`event_key` + UNIQUE).
- [x] H36.4 Metrics rời khỏi tiến trình — bảng `api_metric_samples`, xả ở **mọi**
  tiến trình web lẫn worker, cộng khi đọc, hiện trên trang Tổng quan.
- [x] H36.5 Đội hình worker theo lớp tài nguyên — `LTT_WORKER_POOLS`; cha giám
  sát và **thay thế con đã chết** (lỗ sẵn có).
- [x] H36.6 Trần thời gian chạy job (`manifest.max_runtime_s`) + không thử lại
  job treo.
- [x] H36.7 Tách bằng chứng khỏi nội dung — nội dung job hết hạn 30 ngày, file
  bị xoá, hàng job ở lại; cửa sổ tải artifact được công bố trong hợp đồng.
- [x] H36.8 Ba tín hiệu bất thường (chỉ đọc), `retry` trong mọi phản hồi lỗi,
  `RUNBOOK.md`.
- [x] H36.9 **Lên đạn cho bánh cóc** — 2026-08-16: `tools/check_multiproc.py` là bước riêng của gate; tự tìm/tạo CSDL test từ chính cấu hình triển khai, và khi không có PostgreSQL thì **nói thành câu** thay vì một chữ `s`. CŨ: — gate phải chạy `test_214`. Hiện nó cần
  `LTT_TEST_DATABASE_URL` mà gate không đặt, nên **luôn skip**: bằng chứng mạnh
  nhất của H36 đã chạy đúng một lần, bằng tay.
- [x] H36.10 **Đã chạy thật ba đường** — 2026-08-16, `test_220`. CŨ: — `_het_gio` (test luôn
  monkeypatch nó đi), vòng cha-thay-con, luồng xả metrics của web.
- [x] H36.11 **R2: nối dây + GIAO THỨC đã chứng minh** — 2026-08-16, `test_221` chạy `boto3` thật với máy chủ S3 thật trong tiến trình (`moto`). Tầng "R2 thật trên mạng" **cố ý không chạy**: bucket dùng chung với BOT GEMINI (kiểm bằng dữ liệu), và `CLAUDE.md` cấm ghi vào đó. CŨ: — `test_221` chạy ngay khi có `LTT_TEST_R2_BUCKET`. Bị chặn vì token chỉ có quyền một bucket và bucket đó có thể dùng chung với hệ thống khác. CŨ: — `LTT_STORAGE=r2` ở production, còn
  test chỉ chạy trên `LocalStorage`.
- [x] H36.12 **Đã đo lại** — 2026-08-16: control-plane không đổi, thông lượng worker giảm ~6% do đồng hồ canh giờ mỗi job. CŨ: sau khi thêm luồng bảo trì, đồng hồ mỗi job và xả
  metrics.

Điểm trung thực: **7,0 → 8,5 → 9,0** sau khi làm H36.9–12 (`AUDIT_API_2026-08-15.md`
§4b rồi §4c). Việc duy nhất còn nợ là chạy `test_221` trên một bucket R2 vứt đi —
chặn bởi một quyết định về hạ tầng, không phải bởi code.

---

## H37 — Model tạo ảnh NỘI BỘ trên máy B (RTX 3090)

**Chốt 2026-08-21 · quyết định nền Q102 · trạng thái: G0 ✅ 9,5/10 · G2 ✅ 10/10.**

⭐ **Chủ dự án chốt: CHẤT LƯỢNG là tiêu chí duy nhất, không đánh về số lượng**
(D-010). Cấu hình đích là cấu hình đẹp nhất chạy được; thời gian mỗi ảnh chỉ là
ràng buộc khả thi, không phải tiêu chí chọn. Model đích: **HiDream-O1-Image**
(MIT, ~8B, chính là Qwen3-VL-8B cải biên) — D-009.

Mục tiêu: có một model tạo ảnh chạy trên máy nhà (từ prompt hoặc từ ảnh tham
chiếu), đóng gói thành **API nội bộ**, để mọi app cần ảnh gọi tới **y như đang gọi
API bên ngoài**. Không phải một app mới — là một **provider** (Q102).

Tài liệu chi tiết ở `docs/ANH_NOI_BO/`:

| File | Nội dung |
|---|---|
| `KE_HOACH_H37.md` | kiến trúc, hiện trạng đo thật hai máy, model, rủi ro |
| `PHAN_TICH_BUILD_PACK.md` | chấm bộ `flux2_klein9b_claude_build_pack` — giữ 7 bước, thu hẹp 12, bỏ 1 |
| `CHIA_GPU_VOI_VIDEO.md` | chia một card 3090 giữa việc video và việc ảnh |
| `KE_HOACH_THI_HANH.md` | **13 phase G0–G12, mỗi phase có cổng chấm điểm ≥ 9/10** |
| `DECISIONS.md` · `CHAM_DIEM.md` | sổ quyết định và sổ chấm điểm, ghi liên tục |

Ba điều phải biết trước khi đụng vào:

- **Máy B không giữ bí mật nào của nền tảng.** Không mật khẩu CSDL, không khoá R2,
  không khoá mã hoá. Ảnh vào bằng presigned GET, ảnh ra bằng presigned PUT.
- **ComfyUI trên máy B không có xác thực.** Nó chỉ được nghe `127.0.0.1`, vĩnh
  viễn. Chỉ cổng render (:8199, bearer token) nghe LAN, tường lửa chỉ mở cho
  192.168.2.17. Không bao giờ đưa ra Cloudflare.
- **Máy B chạy video cùng lúc.** Một lượt video từng chạy 72,5 phút và ăn 98,7 %
  VRAM. Job ảnh **không xếp hàng sau video** — bận thì cascade sang Gemini.

- [x] G0 Khung làm việc: Q102, H37, `DECISIONS.md`, `CHAM_DIEM.md`, `bench/` — **9,5/10**
- [x] G1 Đo phần cứng — **10/10**. **PCIe Gen 3 x16, 11,93 GB/s** (đổi model chỉ
  ~1,4 s) · E: là SATA 476 MB/s còn NVMe 849 GB trống ⇒ model ảnh về H: (D-014) ·
  fp8 tensor core **KHÔNG có** (CC 8.6) — nay là số đo · trần công suất **370 W**
  chứ không phải 250 W. **Bác bỏ bắt được lỗi thật**: `/system_stats` và
  `torch.mem_get_info` mù với tiến trình khác trên WDDM ⇒ `busy.py` đọc VRAM
  bằng `nvidia-smi` (D-013)
- [~] G3 **KHÔNG QUA lần 1 — C4 = 7 < 8** (luật §1.4 điều ②, không cho bù trừ).
  Trung bình 9,25 nhưng bốn dấu chân ngoài dự định trên máy dùng chung, nặng nhất là
  **lệnh tách khỏi SSH vẫn chạy tiếp khi chủ dự án ngắt** — đã khắc phục cả bốn
  (`dung_het.ps1`, prefix `ltt_h37/`, trả lại 2 tệp .mp4 chuyển nhầm).
  **Số đo cấu hình đích:** bf16 2560×1440 50 bước → **92–97 giây/ảnh**, VRAM đỉnh
  **16,8 GB**, nhiệt **82–83 °C** kèm **SW Thermal Slowdown**, không rò rỉ RAM.
  **Tái lập byte-identical** đã chứng minh. Thời gian ∝ số token (D-019).
  Hai lỗi thật đã bắt và sửa: `/history` có bản ghi ≠ job đã xong (D-018) · prefix
  đụng thư mục dự án video.
- [x] G4 **ĐÓNG 2026-08-24 (D-054)** — giữ **50 bước**, và đó là câu trả lời cuối
  chứ không phải "chưa đủ bằng chứng". 60 cặp: 50 bước **33–18**, điểm 0,625,
  KTC [0,507; 0,744] không chứa 0,5. ⚠️ Nhưng khác biệt **nhỏ hơn khác biệt
  giữa hai seed** — đừng đọc thành "36 bước tệ rõ"
- [x] G5 **ĐÓNG 2026-08-24 (D-053)** — `edit` và `subject` ở `ref_mp=4.0` đã đo
  và đã mở; trần token 7.506 → **11.412**, đo thật **20,1 GB · 239 s**
- [ ] G5b Chuỗi nâng chất: SeedVR2/upscale · VLM tự loại · nhiều seed. Nhánh nào
  không chứng minh được tác dụng thì **bỏ hẳn**
- [⛔] ~~**G6b ĐỐI CHỨNG TRẦN — cổng quyết định.**~~ **HUỶ 2026-08-24 (D-046)** —
  bỏ hẳn đối chứng ngoài; từ đây chỉ đo **HiDream đấu HiDream, một lô một biến**.
  Kết quả lô 23/08 đã đủ để quyết: Gemini **14–4** ở phần có nghĩa (D-045). Chạy
  thêm lô đối chứng chỉ tốn tiền API mà không đổi được lựa chọn nào
- [x] G6 Cổng render `render_gateway/` + `test_245` — **9,55/10**, 53 test xanh trên
  máy A không cần GPU. Mọi hợp đồng đọc từ mã ComfyUI kèm số dòng. Phát hiện quan
  trọng: `progress`/`executing` chỉ gửi tới client đã gửi prompt ⇒ **bỏ websocket**,
  ETA việc lạ suy từ trung vị thời lượng (D-012). Template `t2i` còn là **DRAFT**,
  G3 phải xác minh bằng cách chạy thật
- [x] G7 **XONG 2026-08-24** — `render_gateway/` chạy thật trên B như dịch vụ.
  ⚠️ `deploy/deploy.ps1` từng có **hai lỗi khiến nó chưa từng deploy thành công
  lần nào** (đích sai một cấp + `Join-Path` giải ổ đĩa của máy A); đã sửa, nay
  **29/29 khớp hash**
- [x] G8 **XONG** — `platform_core/image_gen/` (`cong_render.py` · `dich_gemini.py`
  · `dieu_phoi.py`) và `ltt_image` trong `platform_core/providers.py`.
  ⚠️ Số hiệu `test_246` trong dòng gốc **sai**: `tests/test_246_*` là test Nexus
  metrics, không liên quan. Phần kiểm của cổng render nằm ở `test_245`
- [x] G9 **ĐÓNG 2026-08-24 (D-056)** — **100/100 lượt, 0 hỏng**; VRAM dao động
  163 MB (0,9 %), nhiệt 69–74 °C, **không trôi gì** qua hơn ba giờ.
  ⭐ Kèm một đính chính: cảnh báo "VRAM 97,5 %" **đã lỗi thời**, đừng lên kế
  hoạch quanh nó
- [x] G10 **XONG** — `image.ltt` đang **bán thật** trên `/api/v1`; kiểm ngày
  2026-08-29 trên `openapi.json` **công khai** (đối chứng âm: không tool đóng
  nào lọt). Giá ở `apps/anhnoibo/gia.py`, công bố ở `/gia-api`
- [ ] G11 Giám sát chất lượng thường trực (lấy mẫu hằng tháng, chấm mù lại)
- [ ] G12 *(tuỳ chọn)* Gộp đường Gemini của `taoanh`/`thumbnail` vào adapter chung

**H38 (đề xuất, làm sau H37):** hợp nhất cơ chế kiểm VRAM + RAM cho toàn hệ. Phần
đo đã có sẵn (`GET /api/v1/metrics` của Nexus trả cùng một khuôn trên cả hai máy,
GPU neo bằng UUID); phần thiếu là sổ "ai đang giữ" và một bảng ngưỡng duy nhất.
Luật quan trọng nhất của H38: **mọi ngưỡng tài nguyên phải là lượng tuyệt đối (GB),
không phải tỉ lệ** — chi tiết và lý do ở `CHIA_GPU_VOI_VIDEO.md` §10.


---

## H39 — Bán VPS (máy chủ ảo Windows) trên `app.lttstudios.com`

**Quyết định nền:** Q103 + **Q104** (mở rộng cùng ngày).
**Phân tích + logic đã khoá (V1–V13):** `docs/VPS/PHAN_TICH_VPS_PROXMOX.md`.

**Trạng thái: CHƯA BẮT ĐẦU VIẾT CODE.** Logic khoá 2026-08-22; P0 chặn bởi hai thứ
ngoài repo (xem cuối mục).

**Hình dạng hạ tầng (đo thật 2026-08-22):** Proxmox VE 9.2 chạy **lồng trong VMware
Workstation trên MÁY B** — `H:\PVE-Nested\VMware\PVE-NESTED-VMWARE\`, 32 vCPU ảo,
RAM 44 GB (**sẽ nới 64**), `PVE-Data.vmdk` 217 GB (**sẽ nới ~600**), NIC bridged nên
có IP LAN `192.168.2.168`. **Không phải một máy chủ riêng.**

**Bốn con số phải nhớ trước khi đụng vào:**

- **Trần công suất THẬT (đo 2026-08-22): node đang ĐẦY, bán được 0 máy.** 8 máy của
  chủ nhà cam kết 35,9/43,2 GB RAM và 640/475 GB đĩa (**đã bán chồng 1,49×**). Sau khi
  nới RAM lên 64 GB còn ~23 GB ⇒ **~5 máy** ở mức 4 GB. Con số "10–14 máy" ở Q104
  tính khi chưa biết node có sẵn 8 máy — xem mục 0.1 của `docs/VPS/PHAN_TICH_VPS_PROXMOX.md`.
- **Upload đường nhà ~150 Mbps** (đo thật) — trần dùng chung cho TẤT CẢ khách. Một
  khách tải file lớn là nghẽn cả cụm ⇒ **giới hạn tốc độ mỗi VM là hạng mục bắt buộc**.
- **Vultr Singapore = 45 ms từ Hà Nội** ⇒ khách VN chọn IP Singapore chịu **~90 ms khứ
  hồi thêm**. Trang bán phải giải thích, không để khách chọn nhầm rồi phàn nàn.
- **V2 chốt là KHÔNG chống việc máy B tự khởi động lại** vì Windows Update. Một đêm là
  mọi khách mất máy. Trang bán **phải** in "best effort, không cam kết uptime".

### Việc

- [x] **P0a** — ✅ **XONG 2026-08-22.** Token `vpsapp@pve!ltt` (privilege separation,
      role `PVEAuditor` = chỉ đọc) tạo qua API Proxmox từ trình duyệt đã đăng nhập; bí
      mật đi thẳng clipboard → `secrets/app.env`, **không lọt vào hội thoại hay log**.
      `python tools\vps_doctor.py` → RESULT: PASS.
      **Kho là `vmdata`, kiểu LVM-thin, 475 GB** — không phải 217 GB; `PVE-Data.vmdk`
      217 GB chỉ là phần đã cấp phát trên `H:`. Nới bằng `pvresize` + `lvextend`,
      **không** phải `zpool online -e`.
- [x] **P0b** — ✅ **XONG 2026-08-23.** Chủ sản phẩm chạy `Tắt Proxmox an toàn` /
      `Bật Proxmox`; tôi sửa `.vmx` ở giữa. Xác minh VM đã tắt trên **hai dấu hiệu độc**
      **lập** (Proxmox không phản hồi + **không còn `.lck`**) trước khi động vào.
      Sao lưu `\*.vmx.bak-truoc-noi-ram-96gb` khớp từng ký tự → `memsize` 45056→98304
      → đối chiếu 108 dòng không đổi, mọi khoá khác giữ nguyên.
      *Kết quả thật:* `cleanShutdown=TRUE` (lần trước là FALSE); Proxmox lên sau **55**
      **giây**; **8/8 VM tự khởi động** (đều `onboot=1`); node **94,4 GB**.
      **Trần bán: 1 → 10 máy** ở gói `vps-vua` (16 nếu toàn gói nhỏ).
      *Chưa làm:* nới pool `vmdata` — chưa cần, đĩa còn 195 GB trước phanh 80 %.
- [x] **P0c** — ✅ **XONG 2026-08-22.** `apps/vps/` đầy đủ chứ không phải khung rỗng:
      `manifest.py` (fail-closed sau cờ `LTT_VPS`), `cost.py` (3 gói + quy đổi credit),
      `os_images.py` (catalog OS + ràng buộc tối thiểu của Microsoft), `tables.py`
      (5 bảng, 3 ràng buộc duy nhất làm trọng tài cấp phát), `services/proxmox.py`
      (driver **tự viết trên `requests`**, KHÔNG dùng `proxmoxer` — lý do ở mục 10.1
      của tài liệu phân tích), `services/capacity.py` (hai phép kiểm: cam kết + thực
      dùng, chặn ở 80 %), `services/provisioning.py` (cấp VMID/cổng/IP nguyên tử),
      `services/billing.py` (thu 30 ngày, treo → xoá +7 ngày), `jobs.py` (3 handler
      idempotent), `routes.py` + `server/templates/vps.html`, migration
      `20260822_1900_vps_tables.py`.
      *Kết quả thật:* **48 test xanh** — `tests/test_251_vps_ha_tang.py` (39) +
      `tests/test_252_vps_giao_dien.py` (9); `tools/lint_app_contract.py` 0 ERROR;
      registry nạp được app + bảng + 3 job type.
      *Hai lỗi thật do test bắt được trong lúc dựng:* (1) `VpsEvent.id` kiểu
      `BigInteger` **không tự tăng trên SQLite** → mọi INSERT nhật ký chết, tức là
      tầng nhật ký sẽ không có test nào đi qua được; (2) `_moc_ke_tiep` khi máy trễ
      **hơn một chu kỳ** trả về một mốc vẫn nằm trong quá khứ → máy vừa thu xong đã
      hết hạn ngay, và vòng thu sẽ **trừ tiếp mỗi lượt cho tới khi cạn số dư khách**.
      Cả hai đã sửa và có test chốt.
- [x] **P1** — ✅ **XONG 2026-08-23** (còn một bước thuộc về chủ sản phẩm, xem cuối mục).
      Template **Debian 12 `generic` dùng NỘI BỘ** (VMID `9101`, `khach_thay=False`,
      không bán) + job `vps.provision` + `services/mang.py` + 6 cột mạng trong
      `vps_gateway` (migration `8b2c5d1e40a7`) + cấp cổng **nguyên tử**
      (khuôn `IntegrityError` của `gpu_lease.py`). **62 test xanh.**

      Chạy thật trên cụm: **5 giây** từ lệnh tới máy đang chạy; máy boot sau **37 giây**
      và tự tải gói từ `deb.debian.org`. Bảng `ci-info` trên serial xác nhận
      `eth0 = 10.50.0.50/24, gw 10.50.0.1` — **đúng địa chỉ suy ra từ cổng NAT đã cấp**
      (`cong_goc + octet`), tức chuỗi *cấp cổng → suy địa chỉ → tiêm cloud-init* khớp
      hai đầu.

      🔴 **Luật hạ tầng phát hiện ở bước này: cụm KHÔNG chạy được virtio.** Proxmox
      nằm lồng trong VMware; guest ghi vào thanh ghi notify của `virtio-pci` thì treo
      cứng (RCU stall trong `vp_notify`). Máy bán ra phải là **`sata0` + `e1000`,
      `agent: 0`, `balloon: 0`** — đúng như 8 máy đang chạy của chủ nhà. Ghim trong
      `MO_HINH_CARD` (`services/mang.py`) kèm test chốt. Kéo theo: ảnh Linux phải là
      bản **`generic`**, không phải `genericcloud` (bản kia bỏ cả driver AHCI).

      ⏳ *Còn thiếu để đóng hẳn:* DNAT `45.76.185.75:33930 → 10.50.0.50:22` trên
      gateway Vultr — bước 6 của `Add-GuestToGateway.ps1`. Cần mật khẩu trong file
      DPAPI mà **chỉ tài khoản `lengo` giải mã được**, nên chủ sản phẩm phải chạy.
      Sau đó *xong khi:* SSH từ ngoài mạng vào `45.76.185.75:33930`.
### ⚠️ Đổi kiến trúc 2026-08-24 — P1b và P2–P9 cũ đã bị THAY

Chủ sản phẩm chốt: **mỗi máy một IP công khai riêng, bỏ hẳn `IP:cổng`.** Toàn bộ
phần chia cổng (`P1b` nạp ánh xạ tĩnh, dải 33930–34080, `cong_goc + octet`) **không
còn dùng**. Đã dọn khỏi mã nguồn cùng ngày: bỏ hai cột `dnat_dau`/`dnat_cuoi`, bỏ
`kiem_dai_da_nap`, xoá migration `4d7e91c2a6b8`, xoá
`tools/vps_gateway/nap-anh-xa-tinh.ps1` và bốn script tương ứng trên máy B.

Điều **không** đổi được, và phải nhắc lại vì nó hay bị hiểu nhầm: **không ai bán IP
rồi cắm thẳng vào máy ở nhà.** Một IPv4 chỉ sống khi có mạng nào đó quảng bá nó bằng
BGP; cáp nhà không quảng bá được gì. Nên đường hầm còn nguyên; thứ đổi là *thứ chạy
bên trên nó* (NAT 1:1 thay vì ánh xạ cổng) và *gateway là máy gì* (Debian thay Windows).

---

## Giai đoạn còn lại của H39 — đánh số lại theo kiến trúc mới

- [x] **G1 — hạ tầng mạng 1-IP-1-VM.** ✅ **XONG 2026-08-24, đo thật.**
      Gateway Debian 12 trên Vultr `sgp` (`45.32.114.249`, `vhp-1c-1gb-amd`, **$6/tháng**,
      2.048 GB) + WireGuard `10.51.255.1↔.2` MTU 1420 (RTT 57 ms) + `nftables` NAT 1:1
      bằng **`map`** + VM router `199` trên máy B (`10.51.0.1/24`, chặn LAN nhà).
      *Bằng chứng:* SSH thẳng từ máy A vào `45.77.45.29` → vào máy khách; máy khách ra
      Internet cũng bằng đúng IP đó. Rẻ hơn gateway Windows cũ **$4/tháng**.

- [x] **G2 — đưa hạ tầng vào MÃ NGUỒN.** ✅ **XONG 2026-08-24** (còn một việc, xem cuối).
      `services/vultr.py` + `services/gateway.py` + `mang.py` viết lại (bỏ octet-theo-cổng)
      + vòng đời IP trong `jobs.py` + `tools/vps_gateway/cai-dat-cong-vao.sh`.
      **81 test xanh** (`test_279` 16 test mới cho hai driver).

      *Đã chứng minh trên hạ tầng thật:* job tạo máy trong **26 giây** (clone + cấp địa chỉ
      riêng + mua IP + gắn + mở đường), vào được **từ Internet** bằng IP riêng, ra Internet
      cũng bằng đúng IP đó; job xoá trả IP về Vultr và gỡ đường sạch; cổng vào khởi động
      lại thì **tự hồi hoàn toàn sau 53 giây**.

      **Bốn lỗi thật tìm được khi chạy, không lỗi nào test bắt được:**
      ① `cap_vmid` chỉ hỏi CSDL nên job **chiếm máy có sẵn trên Proxmox** mà CSDL không
      biết — tức giao máy người này cho người khác. Nay hỏi cả máy chủ, có test chốt.
      ② `_xoa_may` gọi `DELETE` ngay sau lệnh tắt (tác vụ nền) ⇒ Proxmox trả **500**.
      ③ Trả IP về mà chỉ gỡ liên kết, không xoá bản ghi ⇒ Vultr **cấp lại chính địa chỉ
      vừa trả** và máy tiếp theo của khách **không tạo được**.
      ④ Mua IP xong mà ghi sổ hỏng thì IP nằm lại — **$3/tháng chảy mãi**. Nay trả về ngay.

      ⏳ *Còn nợ:* test đa tiến trình kiểu `test_214` chứng minh hai worker không cấp trùng
      địa chỉ. Ràng buộc duy nhất `(gateway_id, ip_noi_bo)` đã là trọng tài và đường
      `IntegrityError` có test, nhưng **chưa chạy thật hai tiến trình** — cần một CSDL
      PostgreSQL vứt đi mà vai `ltt_app` không tạo được (thiếu `CREATEDB`).

- [x] **G3 — vòng đời máy.** ✅ **XONG 2026-08-24.** `services/dieu_khien.py` +
      6 route + trang chi tiết máy + `tests/test_280_vps_vong_doi.py` (12 test).
      Bật/tắt/khởi động lại chạy **thẳng** (một lệnh gọi API, ~200 ms — nhét vào hàng
      đợi là bắt khách chờ một vòng worker); cài lại/xoá đi **qua job** (mất vài phút,
      Cloudflare cắt ở 100 giây).

      Ba luật của tầng này đều là **luật tiền**, không phải luật kỹ thuật: máy bị treo
      vì nợ thì khách **không tự bật lại được** (nếu bật được thì "treo" chỉ là một cái
      nút); máy đang tạo dở thì không ai đụng vào; **mọi thao tác kể cả thất bại đều ghi
      nhật ký vòng đời** — đó là thứ trả lời "vì sao máy tôi bị tắt" khi khách hỏi sau
      ba tháng, lúc log ứng dụng đã xoay vòng mất.

      Hai lỗi sửa nhân tiện: đường **cài lại** dính đúng cái bẫy `DELETE` chạy đua với
      lệnh tắt như đường xoá; và `dieu_khien.treo` ban đầu tự ghi sổ, tức **chỗ thứ hai**
      quyết định cùng một việc với `billing.treo` — cái này đặt `xoa_sau`, cái kia quên,
      và máy của khách nằm lại vĩnh viễn hoặc bị xoá sớm bảy ngày. Nay uỷ quyền hết.

      Cũng sửa một **dòng cảnh báo đã thành SAI** trên trang bán: *"bạn nhận cổng, không
      nhận IP riêng"* — từ 24/08 thì ngược lại. Một cảnh báo sai còn tệ hơn không có, vì
      khách tin nó. Test cũ chốt đúng câu sai đó, đã cập nhật.

- [x] **G3b — console noVNC.** ✅ **XONG 2026-08-24, đã kiểm bằng trình duyệt thật.**
      noVNC v1.7.0 nhúng ở `server/static/vps/novnc/` (chỉ `core/` + `vendor/pako`,
      **570 KiB**, không bê cả kho về) · bảng `vps_console_ve` (vé một-lần, lưu **băm**
      chứ không lưu vé) · cầu WebSocket trong `routes.py` · `services/console.py` ·
      `tests/test_282_vps_console.py` (13 test).

      *Bằng chứng:* mở trang console trong Chrome, noVNC vẽ đúng màn hình VGA của máy
      (`Debian GNU/Linux 12 … login:`), **0 lỗi JavaScript**, canvas 1280×800.

      **Hai lỗi chỉ trình duyệt mới bắt được — test không bao giờ thấy:**

      ① **`vga: serial0` trong template** ⇒ máy **không có màn hình đồ hoạ nào cả**.
      Job chạy đúng, Proxmox nhận lệnh, máy lên bình thường — chỉ là console mở ra thì
      thấy kết nối bị đóng. Với khách Windows, console là **đường cứu hộ** khi họ tự
      chặn mất RDP của chính mình, nên mất nó là mất đường về duy nhất. Nay `jobs.py`
      đặt `vga: std` tường minh.

      ② **`vncproxy` KHÁC `termproxy`.** Tôi gửi dòng `user:ticket` mở đầu như với
      xterm.js; với VNC thì vé là **mật khẩu VNC** đi qua bước bắt tay RFB, còn dòng
      chữ kia làm hỏng luồng nhị phân và Proxmox đóng ngay **không nói gì**. Triệu
      chứng duy nhất là "console trắng".

      Vé Proxmox có đi tới trình duyệt (làm mật khẩu VNC) — chính giao diện Proxmox
      cũng làm vậy. Nó chỉ mở được **đúng một cổng của đúng phiên đó**, trên một máy
      chủ mà khách không biết địa chỉ, và dòng vé bị **xoá khỏi CSDL ngay khi tiêu**.

- [x] **G4 — tiền.** ✅ **XONG 2026-08-24, diễn tập thật đầu-tới-cuối.**

      🔴 **Lỗi tìm được, và nó là lỗi nghiêm trọng nhất của cả H39:**
      `billing.thu_phi_dinh_ky` đã viết xong kèm test từ 23/08 nhưng **không nơi
      nào gọi nó**. Máy hết hạn không bị treo, không bị xoá, IP `$3/tháng` không
      được trả. Mở bán trong tình trạng đó là cho dùng miễn phí vô hạn trong khi
      vẫn trả tiền IP mãi mãi.

      Nguyên nhân gốc **không phải quên**: hợp đồng app không có chỗ khai việc
      định kỳ. Nên theo đúng quy tắc của dự án, chỗ đó được **bổ sung vào hợp
      đồng** thay vì đi vòng — `AppManifest.bao_tri` + `bao_tri_moi_giay`, nền
      tảng gọi trong `_mot_luot_bao_tri`, tức **dưới lease** `bao_tri`. Nhờ vậy
      nó chạy đúng một lần trên toàn cụm dù có bao nhiêu tiến trình worker (H36).
      App tự dựng vòng lặp riêng sẽ **trừ tiền khách N lần mỗi chu kỳ**, và sổ
      credit vẫn cân nên không lỗi nào lộ ra.

      🔴 **Lỗi thứ hai:** `billing.treo` **chỉ ghi sổ** — máy vẫn chạy trên
      Proxmox suốt 7 ngày ân hạn. "Treo" chỉ là một cái nhãn: khách hết tiền dùng
      tiếp bình thường, và RAM vẫn bị giữ. Nay vòng bảo trì tiêm
      `dieu_khien.treo` (có tắt máy) vào `thu_phi_dinh_ky`.

      **Xoá đi qua HÀNG ĐỢI**, không xoá tại chỗ: xoá gọi ra Vultr và chờ tác vụ
      Proxmox, nên làm thẳng trong vòng bảo trì nghĩa là một Vultr chậm **giữ
      lease bảo trì của cả nền tảng**. `dedupe_key=vps-destroy-<id>` chặn nộp
      trùng (vòng chạy mỗi giờ); job hỏng hẳn thì lượt sau nộp lại.

      **Diễn tập thật, không giả lập gì:** nạp 1.490 credit → tạo máy thật →
      đến kỳ: **thu đúng 1.490, số dư về 0** → đến kỳ lần hai, hết tiền: **treo
      VÀ máy `stopped` trên Proxmox** → quá hạn ân hạn: **nộp một job xoá**, chạy
      lại **không nộp trùng** → chạy job: VM biến mất, dòng `vps_ip` biến mất,
      chỗ DHCP biến mất, **IP trả về Vultr**. `KET LUAN: DAT`.

      *Bằng chứng:* `tests/test_287_vps_bao_tri.py` (13 test).

- [x] **G7 — chống lạm dụng + hạn mức băng thông.** ✅ **XONG 2026-08-24, đo thật.**

      **Chặn thư ra** — `tcp dport { 25, 465, 587 } reject` trên router. Chặn cả
      ba chứ không riêng 25: ba cổng này là ba *đường gửi*, không phải ba mức độ
      tin cậy. Một máy khách gửi thư rác là IP của **ta** vào danh sách đen và
      Vultr khoá cả tài khoản — tức mọi khách mất máy cùng lúc vì một người.
      *Đo thật:* cả ba cổng chặn, 443 vẫn mở.

      **Đo băng thông từng máy** — `set` của nftables khai `counter`, tức **mỗi
      phần tử một bộ đếm riêng**. Đo được từng khách mà không cần một luật cho
      mỗi người; ruleset dài làm chậm **mọi** kết nối (cùng lý do đã chọn `map`
      cho NAT). *Đo thật:* tải 150 MB → đọc ra 145 MB.

      **Hãm tốc khi vượt** — `limit rate over 1 mbytes/second drop`, **không cắt
      hẳn**: trang bán hứa *"giảm tốc, không bị tính thêm tiền"*, và cắt biến lời
      hứa đó thành lời nói dối. *Đo thật:* **6,76 MB/s → 1,05 MB/s**, máy vẫn
      dùng được.

      Hạn mức mỗi chu kỳ: Nhỏ **300 GB** · Vừa **600 GB** · Lớn **1.000 GB**.
      ⚠️ Bán chồng có chủ ý: bán hết 16 máy Nhỏ là hứa 4,8 TB trên cổng vào chỉ
      có **2 TB**. Cùng khuôn với đĩa thin (V14), nhưng nó **là** rủi ro —
      `bang_thong.tong_da_hua_gb()` có để nhìn con số đó thay vì phát hiện nó
      trên hoá đơn Vultr.

      🔴 **Lỗi thứ ba, chỉ lộ ra khi chạy hai máy thử trên CÙNG một địa chỉ:**
      xoá máy để lại **lease DHCP** sống tới 12 tiếng. Khách tiếp theo nhận đúng
      địa chỉ đó bị `no address available` — máy lên bình thường nhưng **không có
      mạng**, và không lỗi nào chỉ vào nguyên nhân. Nay `go_cho` gọi
      `dhcp_release`, và thời hạn lease hạ **12h → 1h** làm lưới đỡ nếu lệnh đó
      thất bại. *Đo thật:* trả lease xong, máy nhận `DHCPACK` ngay.

      🔴 **Lỗi thứ tư:** chạy lại `cai-dat-router.sh` là `delete table` rồi dựng
      lại — **cả ba set rỗng**. Máy đang sống mất phép đo, và máy đang bị hãm
      **hết bị hãm** trong khi CSDL vẫn ghi là có. Nay mỗi lượt bảo trì đối chiếu
      với **sự thật trên router** (`danh_sach_giam_toc`, `doc_bang_thong`) và ghi
      lại những gì thiếu — cùng nguyên tắc với `gateway.danh_sach_duong`.

      *Bằng chứng:* `tests/test_288_vps_bang_thong.py` (24 test), migration
      `8c1f4a67b209`.

### ⚠️ Đổi hướng 2026-08-24 (tối) — BỎ TEMPLATE, khách tự cài Windows

Chủ sản phẩm chốt: **không nhân bản từ template nữa.** Mỗi máy bán ra là một máy
trống + đĩa cài Windows; khách tự chạy trình cài đặt qua console và **tự đặt tài
khoản, mật khẩu của chính họ**. Áp dụng cho **mọi phiên bản Windows**.

**Ba thứ nó gỡ được, và đều là những thứ khó nhất còn lại:**

1. **Nền tảng không bao giờ biết mật khẩu của khách.** Đây là thay đổi lớn nhất, và
   nó là về trách nhiệm chứ không phải kỹ thuật: không giữ thì không làm lộ được.
   Toàn bộ Cloudbase-Init (cùng cái bẫy NoCloud-vs-ConfigDrive) biến mất.
2. **Hết việc nuôi template.** Không sysprep, không dựng lại mỗi lần Microsoft vá,
   không `autounattend.xml` cho từng phiên bản. Thêm một phiên bản Windows = **thêm
   một file ISO**, không phải thêm một quy trình.
3. **Hết ràng buộc đĩa của template.** Sàn đĩa quay về đúng yêu cầu của Microsoft
   (Server 2022: 32 GB, Win11: 64 GB) thay vì 80 GB của ảnh Win10 có sẵn.

**Ba cái giá phải trả, nói trước:**

1. **Console thành đường chính, không còn là đường cứu hộ.** Nó phải chắc. Và ghi
   chú ở G3b về việc phím Shift bị gõ sai **phải được kiểm bằng một người thật** —
   khách sẽ gõ mật khẩu có `!`, `@` vào trình cài đặt.
2. **Mất lợi thế nhân bản liên kết.** `clone(full=False)` chia sẻ ảnh nền nên gần
   như không tốn chỗ; máy tự cài thì **mỗi máy ghi trọn ~15–20 GB thật**. Kho thin
   475 GB chia cho 16 máy còn ~29 GB/máy — vẫn đủ, nhưng ba cái phanh của
   `capacity.py` từ nay là thật sự cần chứ không phải phòng xa.
3. **Chỗ chứa ISO.** `local` chỉ 27 GiB và đã có ~11 GiB ISO. Thêm Win10/11 là hết
   chỗ ⇒ phải bật loại nội dung `iso` cho kho `vmdata` (475 GB).

---

- [x] **G5a — đã đo, và kết quả vẫn dùng được.** Chuỗi *job → máy Windows → RDP từ
      Internet qua IP riêng* đã chứng minh chạy (128 ms). Phần "nhân bản template"
      bị thay, nhưng phần mạng, IP riêng, NAT 1:1 và console thì giữ nguyên.
      Ba lỗi tìm được vẫn có giá trị: **card mạng thứ hai của template** (job nay gỡ
      mọi `netN` thừa), **`vga: serial0`**, và **sàn đĩa của template**.

- [x] **G5 (mới) — khách tự cài Windows.** ✅ **XONG 2026-08-24, đo thật đầu-tới-cuối.**

      ① `os_images` mang **volid ISO** (`LTT_VPS_ISO_<ID>`) · ② `jobs.py` **tạo máy
      trống + gắn ISO** · ③ **DHCP theo MAC** trên VM router (`dnsmasq`,
      `services/router.py`) · ④ trang **hướng dẫn cài đặt** `/vps/<id>/cai-dat` ·
      ⑤ ISO — xem mục "chưa xong" ở cuối.

      **Chuỗi đã chạy thật, một lần, không sửa tay:** job tạo máy **17 giây** →
      máy boot **thẳng vào trình cài đặt Windows Server 2022** (không kẹt ở "Press
      any key") → console trong trình duyệt mở được, không lỗi JS → DHCP cấp
      **đúng** địa chỉ đã đặt chỗ (`DISCOVER → OFFER 10.51.0.99 → REQUEST → ACK`)
      → máy khách ra Internet được, tải 1 MB trọn vẹn ở 1,2 MB/s → job xoá **24
      giây**, trả sạch cả ba thứ (chỗ DHCP, dòng `vps_ip`, IP bên Vultr).

      ⚠️ `/reserved-ips` của Vultr **trễ vài chục giây** sau `DELETE`. Kiểm ngay
      sau khi xoá sẽ thấy IP còn đó và tưởng rò tiền — kiểm lại sau một phút.

      **Năm lỗi tìm được, tất cả chỉ lộ ra khi chạy thật:**

      1. 🔴 **Console chưa từng chạy được lần nào.** Cột `vps_console_ve.pve_ve`
         là `String(255)`; vé `vncproxy` thật dài hơn thế, nên Postgres từ chối
         INSERT và trang trả **500 cho mọi máy**. `test_282` xanh vì nó chạy trên
         **SQLite, thứ không cưỡng chế độ dài `VARCHAR`**. Migration
         `5b9e2c47a103`; nay có test chốt kiểu cột, không chốt bằng một chuỗi mẫu.
      2. 🔴 **VM router chưa từng có tường lửa** — `nft` chưa được cài. Việc chặn
         khách sang LAN nhà chỉ là **hệ quả phụ của bảng định tuyến 100**, và nó
         mất hiệu lực ngay khi `wg-quick@wg0` hỏng lúc khởi động: không có
         `ip rule` ⇒ gói của khách dùng bảng chính ⇒ `192.168.2.0/24 dev eth0` ⇒
         **máy khách nằm thẳng trong LAN nhà, cùng mạng với máy A và Proxmox**.
         Nay có lớp chặn thật (`tools/vps_gateway/cai-dat-router.sh`), và bộ đếm
         `nft` đo được **22 gói bị chặn** trong lượt thử — chặn thật, không phải
         may nhờ định tuyến. `mang.py` trước đây **khẳng định** luật này tồn tại.
      3. 🔴 **Trang bán mặc định chọn một vùng đã bị xoá.** Bộ chọn "Vùng đặt máy"
         viết cứng ba lựa chọn của mô hình chia cổng cũ, mặc định `port`. Khách
         bấm "Thuê máy này" là gặp `khong co cong vao nao dang mo o vung 'port'`.
         Nay dựng từ CSDL (`provisioning.vung_dang_mo`); một vùng thì không hiện
         bộ chọn nữa.
      4. **`vps_gateway` rỗng** — chưa ai khai cổng vào, nên app từ chối mọi lượt
         mua. Thêm `tools/vps_them_cong_vao.py` (chạy lại được, có `--xem`).
      5. **"Còn trống: 44.5 GB RAM · GB đĩa"** — template gọi `suc_chua.dia_gb_con`,
         thuộc tính **không tồn tại**, và Jinja in thuộc tính không tồn tại thành
         **chuỗi rỗng** thay vì báo lỗi. Nay có test đọc template và đối chiếu
         từng `<biến>.<thuộc tính>` với lớp thật.

      **Thêm một nút mà chỉ việc chạy thật mới cho thấy là bắt buộc:** đĩa cài nằm
      lại trong máy sau khi cài xong, nên mỗi lần khởi động lại hiện *"Press any
      key to boot from CD"* — **bấm nhầm một phím là vào lại trình cài đặt từ
      đầu**. `dieu_khien.go_dia_cai` + nút "Tôi đã cài xong". Không tự động được:
      máy khách không có guest agent (agent là thiết bị virtio), nên nền tảng
      **không có cách nào biết** khách đã cài xong hay chưa, và đoán theo thời
      gian là rút đĩa giữa lúc họ đang cài.

      *Bằng chứng:* `tests/test_286_vps_dhcp_router.py` (29) + phần bổ sung ở
      `test_280` (4) và `test_252` (3). Toàn bộ VPS **166 xanh**, `gate --quick`
      **PASS**.

      ✅ **⑤ kho ISO — XONG 2026-08-24, và kết luận trước đó của tôi SAI.**

      Tôi từng ghi "⛔ không thêm được ISO nào nữa, cần shell root trên node mà
      chưa có". **Cả hai vế đều sai**, và tôi đã không kiểm trước khi viết:

      * **Có shell root.** Token `vpsapp@pve!ltt` mở được `/nodes/pve/termproxy`,
        và termproxy LÀ một shell root trên node. `POST /storage` (`Sys.Modify`)
        cũng được chấp nhận. Đã thử thật cả ba. `tools/vps_node_shell.py` gói
        lại việc đó.
      * **Không cần thêm chỗ.** Danh mục đã chốt ở **ba đời Windows** (Server
        2016, Server 2022, Windows 10 LTSC) và **cả ba ISO đã nằm trên node**
        (15,75 GB). Không có bản nào chờ tải lên, nên "hết chỗ" không chặn gì.
        Tôi đã trình bày một giới hạn *tương lai* như một *rào chắn hiện tại*.

      **Đã dọn tàn dư của mô hình template** (chủ sản phẩm: *"sài qua cài đặt thì
      xoá các template"*): xoá **3 template** (`WIN10-LTSC-GOLD` 80 GB,
      `UBUNTU-2404` 3,5 GB, `DEBIAN12` 3 GB — kiểm không máy nào linked-clone
      trước khi xoá) và **7 ISO/ảnh không ai dùng** (`virtio-win` — cụm không
      chạy virtio; `debian-12-generic` ×2; `ltsc-answer`; `sysprep-template` ×3).
      `local` 3,5 → **5,1 GB trống**, `vmdata` 315 → **321 GB trống**.

      Kéo theo: **đường `clone` trong `jobs.py` đã gỡ hẳn** — không còn template
      nào để nhân bản, và một nhánh không ai đi qua trong đường tạo máy là nhánh
      không lần chạy nào thử tới. Hai bản Linux nội bộ (`debian-12`,
      `ubuntu-24-04`) cũng rời catalog: một mục mà mọi lần tạo đều ném lỗi là
      một cái bẫy, không phải một tuỳ chọn. Nay `os_images` **chỉ còn Windows**.

      ⚠️ **Ràng buộc mới đo được:** hạn ngạch Reserved IP của Vultr tính **cả IP
      vừa xoá gần đây**, nên vòng tạo/xoá liên tục lúc thử làm cạn hạn ngạch và
      lượt tạo kế tiếp hỏng ở mốc 92 %. Job xử lý đúng (đánh dấu máy **Lỗi**, không
      để nửa vời), nhưng với khách thật thì đó là một lượt mua hỏng — cần **xin
      Vultr nâng hạn ngạch** trước khi mở bán.

      ⚠️ **Tài khoản thử `vps-thu@lttstudios.com` đang sống trong CSDL thật** — tạo
      để kiểm giao diện bằng trình duyệt (không mượn tài khoản khách nào). **Phải
      xoá trước G10.**

- [x] **G5b — dọn sạch template + danh tính phần cứng riêng cho từng máy.**
      ✅ **XONG 2026-08-24.**

      **Dọn template.** `os_images.template_vmid` xoá hẳn; `vps_doctor` đối chiếu
      **volid ISO** thay vì đĩa template; `LTT_VPS_TEMPLATE_WIN10` gỡ khỏi
      `app.env`. Đường nhân bản còn sống **chỉ** cho bản `khach_thay=False` (Linux
      nội bộ, lên trong ~40 giây — thứ tách "lỗi đường ống" khỏi "lỗi lúc cài
      Windows"), và `_template_noi_bo` **từ chối** mọi bản bán cho khách kể cả khi
      biến môi trường được đặt. Hàng rào, không phải quy ước: thiếu nó thì một biến
      gõ nhầm đưa mọi khách về chung một mật khẩu, và không lỗi nào được ghi ra.

      **Danh tính phần cứng** — `apps/vps/services/dinh_danh.py`. Cụm mặc định phát
      ra những máy giống nhau hơn ta tưởng: Proxmox có sinh MAC và UUID riêng, nhưng
      **QEMU đặt số hiệu ổ theo chỉ số ổ**, nên mọi máy dùng `sata0` báo về cùng một
      chuỗi, và số hiệu SMBIOS bỏ trống ở mọi máy. Nay bốn thứ suy ra từ
      `instance_id`: **MAC · UUID · số hiệu đĩa · số hiệu máy**.

      **Suy ra, không bốc ngẫu nhiên** — và đây mới là lý do thật sự phải làm ngay:
      job tạo máy **chạy lại được**, còn bước 4 của nó **ghi đè `net0`**. Trước thay
      đổi này, mỗi lần chạy lại là một MAC mới ⇒ máy mất chỗ neo DHCP (thứ G5 sắp
      dựa vào), và **Windows đã cài xong thấy card "mới" nên đặt hồ sơ mạng về
      *Public* — tường lửa chặn RDP**. Khách mất đường vào máy của chính họ và không
      đọc được lý do ở đâu cả. Đó là một lỗi đang sống, không phải việc làm đẹp.

      Cái được thứ hai: hai khách không còn trùng danh tính phần cứng, nên bản sao
      lưu và phần mềm cấp phép của người này không lẫn sang người kia, và **một máy
      bị chặn thì máy kia không chịu chung**.

      ⛔ **Ranh giới cố ý — đọc trước khi ai đó "mở rộng" file này.** `smbios1` chỉ
      đặt `uuid` và `serial`; **không** đặt `manufacturer`/`product`/`family`, và MAC
      giữ nguyên OUI `BC:24:11` của Proxmox. Việc ở đây là *phân biệt máy khách này
      với máy khách kia*. Làm máy ảo **giả dạng máy vật lý**, hay dựng bộ tham số
      nhằm qua mặt hệ thống dò lạm dụng của một nền tảng nào đó, là việc khác — và
      ta không làm. Test chốt điều này: `test_smbios1_dat_uuid_va_serial_nhung_
      KHONG_gia_nha_san_xuat`.

      *Bằng chứng:* `tests/test_295_vps_dinh_danh.py` — 19 test, gồm 500 máy không
      trùng ở cả bốn mục, gọi lại cho kết quả y hệt, và một chốt cấm dùng nguồn ngẫu
      nhiên. Toàn bộ VPS: **130 xanh**, `gate --quick` **PASS**.

- [~] **G6 — Windows 11.** ⛔ **HUỶ 2026-08-24 — chủ sản phẩm chốt không bán.**
      Danh mục dừng ở **Server 2016, Server 2022, Windows 10 LTSC**.

      Việc đã làm theo quyết định này (không chỉ là gạch một dòng kế hoạch):
      bỏ bản `win11` và trường `can_uefi_tpm` khỏi `os_images.py`; **gỡ nhánh
      `ovmf` + `efidisk0` + `tpmstate0`** khỏi `jobs._cau_hinh_may_trong` — nhánh
      chỉ một bản đi qua là nhánh không lần chạy nào thử tới; **thêm Server 2016**
      (bản Core và bản có giao diện, dùng chung một ISO đã có sẵn trên node); gọi
      đúng tên **Windows 10 LTSC 2021** thay vì "Windows 10", vì đĩa cài là bản
      LTSC và nó **không có Microsoft Store** — khách mua nhầm kỳ vọng là một lần
      hoàn tiền.

      Dọn kèm: **bỏ trường `Plan.os_toi_thieu`**. Nó khai tay "gói này chạy bản
      nào" trong khi việc đó đã do `os_images.hop_le()` tính từ số thật —
      **không nơi nào đọc nó**, và nó đã kịp lệch: trỏ vào `win11`.

      ⚠️ **Một hệ quả về giá cần chủ sản phẩm xem lại.** Gói `vps-lon` (329.000đ)
      trước đây được biện minh bằng "đủ đĩa cho Windows 11 (cần 64 GB)". Bỏ
      Windows 11 thì **gói Lớn không còn mở thêm bản Windows nào** — mọi bản
      trong danh mục đã chạy ở gói Vừa (179.000đ). Nó vẫn bán gấp đôi CPU và RAM,
      và mô tả đã sửa cho đúng như vậy, nhưng **khoảng cách giá 179k → 329k nay
      chỉ đổi lấy CPU/RAM/đĩa**, không đổi lấy khả năng mới.

- [x] **G7b — phần còn lại của chống lạm dụng.** ✅ **XONG 2026-08-24.**

      🔴 **`cho_phep_ban` gác RAM và đĩa nhưng KHÔNG gác CPU chút nào** — nên mức
      bán chồng CPU là một hệ quả tình cờ chứ không phải một lựa chọn. Node đo
      được: **32 luồng**, mà riêng 8 máy của chủ nhà đã cam kết **41 vCPU**, tức
      **1,28× trước khi bán cho ai một máy nào**. Nay `SucChua` mang `cpu_tong` +
      `vcpu_da_hua`, và có phanh thứ tư ở trần **3,0×** (cùng con số với đĩa).
      Khác đĩa ở một chỗ có chủ ý: **không đo được CPU thì KHÔNG chặn** — thiếu
      CPU máy vẫn chạy (chỉ chậm), còn thiếu đĩa thì hỏng cả node.

      **`tools/vps_treo_khan.py`** — treo khẩn cấp khi có báo cáo lạm dụng. Tìm
      máy theo **instance_id, IP nội bộ, IP công khai, hoặc vmid**, vì thứ người
      xử lý sự cố cầm trong tay thường là một địa chỉ IP lấy từ báo cáo, không
      phải một UUID. Làm **ba việc**, theo thứ tự chắc-chắn-trước: hãm tốc →
      tắt máy → ghi sổ. `--bo-treo` bỏ hãm nhưng **không tự bật máy lại**: quyết
      định bật lại một máy bị treo vì lạm dụng phải là của một con người.

      Là **công cụ dòng lệnh, không phải nút trong trang admin** — thêm một
      `ModelView` cho bảng của app vào `server/admin.py` là viết cứng tên app vào
      nền tảng, đúng thứ hợp đồng app cấm (`test_60` chốt điều đó).

      *Đo thật:* treo một máy đang chạy bằng **IP công khai** của nó → VM
      `stopped` trên Proxmox, địa chỉ vào set `giam_toc` → `--bo-treo` gỡ hãm,
      máy vẫn tắt. Và một lỗi chỉ lộ khi chạy thật: console Windows là cp1252 nên
      công cụ **vỡ ngay ở dòng `print` đầu tiên** với `UnicodeEncodeError` —
      người đang xử lý sự cố không biết máy đã bị treo hay chưa. Đã vá.

      ⛔ **Cảnh báo "CPU 100 % kéo dài" — CỐ Ý KHÔNG LÀM.** Khách mua 4 vCPU thì
      dùng hết 4 vCPU **không phải là lạm dụng**, nên cảnh báo đó chủ yếu sinh ra
      tiếng ồn cho một người dùng nặng hợp lệ. Thứ thật sự bảo vệ hàng xóm là
      **trần bán chồng** (đã làm) và trọng số CPU bằng nhau giữa các máy (mặc
      định của Proxmox). Mở lại khi có một sự cố thật chứng minh điều ngược lại.

      *Bằng chứng:* 6 test mới trong `test_251` (66 test).

- [x] **G11 — bốn việc từ đợt rà soát 2026-08-25.** ✅ **XONG.**

      Đợt rà soát tìm ra bốn lỗ; ba đã vá, một là của nền tảng.

      🔴 **1. Khách trả tiền cho máy chưa từng chạy.** `routes.tao_may` trừ credit
      **trước** khi nộp job (đúng — không trừ trước thì người hết tiền vẫn chiếm
      chỗ). Nhưng job hỏng → máy vào `loi` → **không ai hoàn**. Khách trả
      149–329k và nhận một dòng chữ "Lỗi". Đã xảy ra thật 24/08 khi hạn ngạch
      Reserved IP cạn ở mốc 92 %.

      Nay `bao_tri._hoan_may_tao_hong` hoàn **chỉ khi máy chưa từng chạy** — mốc
      là sự kiện `tao_xong`; máy chạy rồi hỏng là chuyện khác, điều khoản đã nói
      chu kỳ đã bắt đầu thì không hoàn. Chống hoàn hai lần bằng chính sự kiện
      `hoan_tien`: thiếu nó thì một máy hỏng thành **máy in tiền 24 lần/ngày**.

      Kéo theo một lỗ trong **hợp đồng nền tảng**: `credit` có `tru()` nhưng
      **không có đường hoàn trực tiếp**. `nap()` sẽ thổi doanh thu nạp lên đúng
      bằng số trả lại; `cap_tay()` làm bẩn nhật ký kiểm toán. Đã thêm
      `credit.hoan_phi()` — nửa còn thiếu của `tru()`.

      🔴 **2. Bốn nguồn sự thật, không ai đối chiếu.** App giữ trạng thái ở năm
      chỗ, bốn nằm ngoài CSDL (Proxmox, DHCP+băng thông trên router, NAT trên
      cổng vào, Reserved IP ở Vultr). Mọi lần đọc chỉ xảy ra **bên trong một job,
      cho đúng một máy**. Mọi thứ mồ côi sống mãi và không lộ ra đâu cả — đắt nhất
      là **Reserved IP mồ côi, $3/tháng chảy mãi**.

      Nay `apps/vps/doi_chieu.py` quét tám chiều, và **hai nơi gọi chung một phép
      quét**: `vps_doctor` (người chạy tay) và `bao_tri` (**tự chạy mỗi ngày**).
      Chỉ chạy `vps_doctor` thì không đủ — một phép soi không ai chạy là một phép
      soi không tồn tại.

      Nó **chỉ nói ra, không tự sửa**: tự sửa là đặt cược rằng phép đối chiếu
      không bao giờ sai, và một phép đối chiếu sai mà tự sửa thì xoá đúng thứ nó
      hiểu nhầm — một VM đang được job khác dựng dở trông y hệt một VM mồ côi.

      🟡 **3. Hai job cùng làm việc trên một máy.** Khách bấm "Cài lại" rồi bấm
      "Xoá"; hoặc vòng bảo trì nộp job xoá đúng lúc khách bấm "Cài lại". Hậu quả
      không dừng ở một lỗi 500: job xoá có thể **nhả địa chỉ trong mạng riêng**
      trong khi job kia đang dựng VM, và địa chỉ vừa nhả được cấp cho khách tiếp
      theo — hai máy cùng một địa chỉ.

      Nay mọi nhánh chạy dưới `jobs._khoa_may`, dùng **lease của nền tảng**
      (`platform_core/leases.py`, sinh ra cho đúng lớp này ở H36) chứ không dựng
      bảng khoá thứ hai: hai cơ chế khoá trong một hệ thống là hai cơ chế sẽ lệch
      nhau. TTL 45 phút > `max_runtime_s` dài nhất (1800 giây), có test chốt.

      🟡 **4. Deploy không chạy gate.** Phát hiện khi gate báo `[FAIL] biên dịch
      được` một nhịp rồi tự xanh lại — nó bắt đúng lúc một tệp đang được ghi dở,
      vì hai phiên làm song song trên cùng cây nguồn. Phiên Public API kiểm và xác
      nhận: deploy chỉ robocopy + alembic, **không có gì chặn một tệp `.py` cụt**.

      Nay `setup/2-cai-dat.ps1` chạy `compileall` **TRƯỚC `Stop-Service`** — hỏng
      ở đó thì dịch vụ vẫn đang chạy và không ai mất gì; đặt sau thì ta đã tự tay
      tạo ra downtime rồi mới phát hiện không deploy được. Đã thử chốt bằng một
      tệp cụt thật: chặn đúng.

      *Bằng chứng:* `test_296` (12) + `test_297` (17). Toàn bộ VPS **307 xanh**.

- [x] **G8 — giao diện + trang bán công khai.** ✅ **XONG 2026-08-25.**
      Xem `docs/VPS/GIAO_DIEN.md`.

      **Trang tạo máy hai bước** với bảng tóm tắt dính bên phải: chọn gói → chọn
      hệ điều hành, giá và số dư còn lại cập nhật ngay khi bấm. Danh sách hệ điều
      hành lọc theo gói bằng JS, nhưng **máy chủ vẫn từ chối tổ hợp sai**
      (`os_images.hop_le`) — không có JS thì khách thấy đủ và vẫn không mua nhầm
      được.

      🔑 **`/vps` là MỘT URL phục vụ hai loại người xem**, không phải hai trang.
      Lý do cụ thể: thẻ app trong catalog hiện cho cả khách chưa đăng nhập
      (`manifest.public=True`), nên nếu `/vps` đòi đăng nhập thì người lạ bấm vào
      sẽ rơi thẳng vào trang đăng nhập — **ngõ cụt ở đúng bước đầu của phễu bán
      hàng**. Nay khách ẩn danh thấy sản phẩm là gì, bảng giá, và điều khoản;
      khách đã đăng nhập thấy máy của mình và biểu mẫu tạo máy.

      **Ba thứ mở-cho-khách-ẩn-danh KHÔNG kéo theo**, mỗi thứ một chốt trong
      `test_252`: không lộ máy của người khác (`_may_cua_toi` không được gọi với
      `user_id` rỗng — nó sẽ quét cả bảng), không dựng biểu mẫu sẽ POST rồi ăn
      401, và **cổng cờ `LTT_VPS` vẫn đứng trước** — công khai nghĩa là "không
      đòi đăng nhập", không phải "bỏ qua cờ".

      ⚠️ **Một lỗi dịch chỉ nhìn thấy khi render thật.** Cột thông số hiện là
      *"Settings"* trong bản tiếng Anh, vì msgid `"Cấu hình"` dùng chung với liên
      kết admin `⚙ Cấu hình` trỏ tới `/settings`. Đã tách thành `"Cấu hình máy"`
      → *"Specs"*. Đáng ghi lại vì việc đổi ngôn ngữ mặc định sang `vi` (phiên
      Public API, cùng ngày) **giấu** lỗi này đi chứ không sửa nó.

- [x] **G9a — ảnh chụp hằng tuần + khôi phục.** ✅ **XONG 2026-08-24, đo thật.**

      🔴 **Trang bán đã hứa "sao lưu hằng tuần, giữ 1 bản" từ trước khi có mã nào
      làm việc đó** — và chính `cost.py` trong cùng repo lại viết rằng đối thủ có
      *"backup tuần và SLA 99,9% — thứ hạ tầng của ta không có"*. Hai file nói
      ngược nhau, và file nói sai là file khách đọc.

      **Ảnh chụp, không phải `vzdump`** — và đó là kết luận sau khi thử, không
      phải lựa chọn cho tiện: `vzdump` ghi ra kho kiểu `dir`, mà kho `dir` duy
      nhất trên node còn **2,2 GiB**. Ảnh chụp LVM-thin tạo trong vài giây và gần
      như không tốn chỗ lúc tạo.

      **Trang bán đã sửa cho đúng thứ khách nhận:** *"Ảnh chụp hằng tuần, giữ 1
      bản. Ảnh chụp nằm trên cùng kho lưu trữ với máy — nó cứu bạn khỏi xoá nhầm
      hoặc một bản vá hỏng, nhưng KHÔNG thay thế bản sao lưu của riêng bạn."*
      Ảnh chụp nằm cùng pool với đĩa gốc; pool hỏng là mất cả hai.

      **Nút "Khôi phục về ảnh chụp"** đứng **trước** "Cài lại máy" trong khối Nguy
      hiểm: khách vào khối đó vì máy hỏng, và quay về ảnh chụp giữ được dữ liệu
      còn cài lại thì mất sạch. Đưa lựa chọn ít thiệt hại hơn lên trước là việc
      của người thiết kế, không phải của người đang hoảng.

      ⚠️ **Phép đo dạy được một điều, và nó đến từ một lần THẤT BẠI:** lần diễn
      tập đầu, tệp ghi *ba giây trước* khi chụp **không có** trong ảnh — nó còn
      nằm trong bộ đệm của guest. Chạy lại kèm `sync` thì tệp còn nguyên. Ảnh chụp
      giữ **những gì đã xuống đĩa**, không phải "mọi thứ tại thời điểm chụp" — máy
      khách không có guest agent để xả bộ đệm (agent là thiết bị virtio, và virtio
      treo trên cụm này). Đừng mô tả tính năng này là "khôi phục về đúng phút đó".

      *Diễn tập thật:* ghi tệp → `sync` → chụp → ghi đè tệp và tạo tệp mới →
      khôi phục → **tệp cũ nguyên vẹn, tệp mới biến mất**. `KET LUAN: DAT`.

      *Bằng chứng:* `tests/test_289_vps_sao_luu.py` (22 test), migration
      `a4d70e93f158`.

- [~] **G9b — chịu được cổng vào chết.** 🔨 **Đường đã dựng 2026-08-24; DIỄN
      TẬP CHƯA LÀM** — nói rõ như vậy, vì "có script" khác "đã chứng minh".

      ⚠️ **Bản trước của mục này tôi viết SAI**: rằng nó "cần mua thêm một VPS
      $6/tháng", như thể đó là điều kiện duy nhất. Ràng buộc thật hẹp hơn nhiều
      — **IP công khai phải nằm trên một máy Vultr** (Reserved IP chỉ gắn được
      vào instance Vultr, và nhà không có IP định tuyến được). Một cổng **chạy
      song song** thì đúng là cần máy thứ hai; nhưng **dựng lại trong vài phút**
      thì không, vì Reserved IP **không chết theo máy**.

      **Đã làm — thứ quan trọng nhất trước:** sao lưu khoá WireGuard của cổng
      vào ra `secrets/cong_vao/` (nằm trong `.gitignore`, đã kiểm). Trước đó khoá
      đó **chỉ tồn tại trên chính con VPS ấy**, và router bên nhà **ghim** khoá
      công khai của nó — nghĩa là cổng chết là mọi khách mất đường vào và **không
      dựng lại được** trừ khi sửa cả router. Đã đối chiếu: khoá sao lưu khớp đúng
      thứ router đang ghim (`2E96sK…`).

      **`tools/vps_gateway/dung-lai-cong-vao.sh`** — dựng một cổng vào hoàn chỉnh
      từ VPS Debian trắng: WireGuard (đòi khoá cũ, **từ chối tự sinh khoá mới**),
      chuyển tiếp gói, `rp_filter=2`, nftables nền, mở 51820, nới UFW.

      **`tools/vps_dung_lai_cong_vao.py`** — phần đi qua API: gỡ-rồi-gắn lại
      Reserved IP sang máy mới, mở lại đường NAT cho từng khách đọc từ `vps_ip`,
      cập nhật `vps_gateway`. Cố ý **không** tạo instance Vultr: tạo máy là thao
      tác tiêu tiền, và tạo nhầm một con là một dòng tiền nhỏ nhưng đều.

      🔴 **Một lỗi tôi tự tạo rồi tự bắt, và nó đáng ghi lại:** bản đầu của kịch
      bản do tôi **tự viết lại** một bộ luật "tương đương" bộ đang chạy. Nó thiếu
      đúng một dòng — `ip saddr 10.51.0.0/24 oifname "enp1s0" masquerade` — tức
      đường ra cho máy **chưa** được gắn IP riêng. Thiếu nó thì máy lên bình
      thường và không ra được Internet, im lặng. Một kịch bản dựng lại sinh ra
      cổng vào *gần giống* thì **tệ hơn không có**, vì nó trông như đã chạy xong.
      Nay kịch bản nhúng thẳng **bản sao lưu của bộ luật thật**, `test_291` chốt
      hai thứ không trôi khỏi nhau, và `vps_doctor` đối chiếu sao-lưu ↔ đang-chạy
      mỗi lần chạy.

      ⛔ **Vì sao chưa diễn tập:** diễn tập thật là **xoá con VPS đang chạy** rồi
      dựng lại. Hôm nay nó chứng minh được rất ít — **không có khách nào, không
      Reserved IP nào**, nên phần khó nhất (gắn lại IP, mở lại đường) sẽ chạy qua
      một danh sách rỗng. Và nó là thao tác không hoàn tác được trên một máy đang
      trả tiền. Đây là **quyết định của chủ sản phẩm**, không phải của tôi.

      *Xong khi:* có ít nhất một máy khách đang chạy với IP riêng → xoá thẳng
      cổng vào → chạy hai lệnh → khách vào lại được, **đo bằng đồng hồ**.

      *Bằng chứng hiện có:* `tests/test_293_vps_dung_lai_cong_vao.py` (14 test).

- [~] **G10 — nghiệm thu và mở bán.** 🔨 **Điều khoản + sao kê XONG 2026-08-25;
      còn hai việc cần chủ sản phẩm.**

      **Điều khoản riêng cho LTT VPS** — `docs/lttstudios-website/{vi/,}legal/vps-terms.html`,
      13 mục, cả hai ngôn ngữ. Đặt ở trang web chứ không trong app, theo đúng quy
      tắc có sẵn của nền tảng: *"a second copy of a legal promise is a second
      promise, and the two will differ"* (`public_api/governance.py`).

      🔑 **Điều đáng nói nhất không phải nội dung mà là cách nó không trôi được:**
      `test_298` đối chiếu **từng con số** trong điều khoản với hằng số thật —
      chu kỳ 30 ngày, ân hạn 7 ngày, giá và cấu hình cả ba gói, hạn mức băng
      thông, tốc độ hãm 1 MB/s (đọc từ `cai-dat-router.sh`), ba cổng thư bị chặn,
      nhịp ảnh chụp, hạn vé console 60 giây, tỷ giá credit. Đổi giá mà quên sửa
      điều khoản = **gate đỏ**. Đã kiểm phép kiểm có bám thật: thay bất kỳ số nào
      cũng làm test đỏ.

      Trang này từng mắc đúng lớp lỗi đó ở quy mô nhỏ hơn — hứa *"sao lưu hằng
      tuần"* khi không có mã nào làm, trong khi `cost.py` cùng kho lại viết ta
      *không có* backup.

      ⚠️ **Rủi ro lớn nhất đã viết thẳng ra: giấy phép Windows.** Đĩa cài đang
      dùng là bản **Evaluation** của Microsoft (180 ngày); Windows 10 LTSC cần
      giấy phép khối lượng. Điều khoản nói rõ **giá KHÔNG bao gồm giấy phép**,
      khách tự chấp nhận EULA và tự chịu trách nhiệm. Câu này còn được đặt **ngay
      trong khối "Đọc trước khi thuê"** trên trang bán, không giấu trong điều
      khoản — người đọc điều khoản là thiểu số.

      **Dọn sạch dấu vết diễn tập (25/08).** Không còn VM lạ trên Proxmox (chỉ
      100–107 của chủ nhà + router 199), **0 Reserved IP** bên Vultr, router và
      cổng vào rỗng, `vps_instance`/`vps_event`/`vps_ip`/`vps_console_ve` đều 0
      dòng. Giữ lại `vps_gateway` (1 dòng cấu hình production).

      🔑 **Tài khoản thử `vps-thu@lttstudios.com` bị VÔ HIỆU HOÁ, không bị xoá.**
      Nó có bút toán trong `credit_entries`, và sổ credit là **append-only** (H3)
      — xoá người dùng mà để bút toán nằm lại là để lại một bút toán không truy
      được về ai. Thay vào đó: `is_active=false` + mật khẩu đổi thành chuỗi 40 ký
      tự ngẫu nhiên **không ghi lại ở đâu**. Rủi ro (một tài khoản sống trong CSDL
      thật với mật khẩu nằm trong nhật ký phiên) biến mất, sổ sách nguyên vẹn.

      **Sao kê thanh toán** trong trang máy (điều khoản hứa thì phải có). Nguồn là
      `vps_event` chứ **không** phải `credit_entries`: sổ credit chỉ có `user_id`,
      không có `instance_id`, nên khách ba máy sẽ thấy ba dòng trừ tiền giống hệt
      nhau và không ai trả lời được "cái nào của máy nào".

      ⛔ **Đây KHÔNG phải hoá đơn điện tử, và trang nói thẳng như vậy.** Hoá đơn
      điện tử theo **Nghị định 123/2020** + **Thông tư 78/2021** phải phát hành
      qua nhà cung cấp được cấp phép và đăng ký với cơ quan thuế — cần mã số
      thuế, hợp đồng với một bên như Viettel/VNPT/MISA, và đăng ký. Không phải
      thứ viết bằng mã. `test_298` **cấm** chữ "hoá đơn"/"invoice" xuất hiện
      trong điều khoản cho tới khi việc đó có thật.

      **Còn lại — hai việc của chủ sản phẩm, không phải của mã:**

      1. 🔴 **Hạn ngạch Reserved IP của Vultr.** Nó tính **cả IP vừa xoá gần
         đây**, và đã cạn khi tôi diễn tập hôm 24/08 — lượt tạo kế tiếp hỏng ở
         mốc 92 %. Job xử lý đúng (đánh dấu **Lỗi**, dọn sạch), nhưng với khách
         thật đó là một lượt mua hỏng. **Xin Vultr nâng hạn ngạch trước khi mở
         bán.**
      2. 🔴 **Quyết định về giấy phép Windows.** Ba đường: (a) giữ như hiện tại —
         khách tự lo giấy phép, ta chỉ cấp đĩa; (b) mua **SPLA** của Microsoft và
         bán kèm giấy phép; (c) yêu cầu khách mang khoá của chính họ. Điều khoản
         đang viết theo **(a)**. Đây là quyết định kinh doanh có hệ quả pháp lý,
         và tôi không thay chủ sản phẩm quyết.

      *Xong khi:* hai việc trên đã chốt → `setup\cong_tac_tool_api.ps1` hoặc đặt
      `LTT_VPS=1` trong `secrets/app.env` của bản đã cài → deploy → kiểm trên
      **URL công khai** `https://app.lttstudios.com/vps` (quy tắc 5b) → xoá tài
      khoản thử `vps-thu@lttstudios.com`.

### 🔴 Một quyết định về giá phải chốt trước G4

**$3/tháng cho mỗi IP ≈ 78.000 đ.** Đối chiếu ba gói đã chốt ở V6:

| Gói | Giá | Còn lại sau tiền IP |
|---|---|---|
| Nhỏ | 89k | **11k** ← không sống được |
| Vừa | 179k | 101k |
| Lớn | 329k | 251k |

Mỗi máy một IP thì **gói 89k chết**. Ba lối ra, chủ sản phẩm chọn:
**(a)** bỏ gói 89k, gói vào cửa thành ~179k · **(b)** nâng giá gói Nhỏ lên ~149–169k ·
**(c)** giữ gói 89k **dùng chung IP theo cổng** như hạng phổ thông (nhưng đúng thứ vừa
bị bỏ, và làm đôi bề mặt của giao diện + tiền + tài liệu).

Chưa chốt thì G4 và G8 không làm dứt điểm được.

### Việc chủ sản phẩm giao 2026-08-22 (tối) — Q105

| # | Việc | Trạng thái | Chặn ở đâu |
|---|---|---|---|
| 1 | **Nới RAM máy ảo Proxmox 44 → 96 GB** | ✅ **XONG 2026-08-23** | `memsize` 45056→98304. Node nhận **94,4 GB**; 8 VM tự lên đủ 8/8 sau 55 giây. Trần bán: **16 / 10 / 6 máy** (nho/vừa/lớn) |
| 2 | **Giữ `WIN10-LTSC-GOLD` (9001), xoá `WIN10-GOLD-SYSPREP` (9000)** | ✅ **XONG 2026-08-22** | Chủ sản phẩm xác nhận "giữ Win 10 LTSC". Ba lớp kiểm trước khi xoá (đúng tên / đúng là template / không ai linked-clone). `vmdata` 173,6 → **149,1 GB** |
| 3 | **Đĩa là tài nguyên chia sẻ, không bán ổ cố định** | ✅ **XONG** | — |
| 4 | **Thêm Windows Server 2016 + 2022** | ✅ **XONG 2026-08-23** | Không dùng nguồn ngoài: trang Evaluation Center có link `go.microsoft.com/fwlink` **không cần biểu mẫu**, resolve thẳng ra CDN Microsoft. Proxmox tự tải bằng `download-url`; **cả hai khớp từng byte** (2022: 5.044.094.976 trong 506 giây; 2016: 6.972.221.440 trong 668 giây). ⚠️ `download-url` đòi **`Sys.Modify`** mà `PVEAdmin` không có — dùng phiên `root@pam` cho việc một lần này, **không** nới quyền token của app. Đã nới `local` 21→27 GiB bằng 5,88 GiB extent vốn trống trong VG `pve` (`lvextend`+`resize2fs`, chạy nóng, không xoá gì) để đủ chỗ |

**Việc 3 đã làm gì** (V14): `disk_gb` của gói thành **hạn mức** thay vì chỗ giữ cứng;
`SucChua` thêm `dia_gb_dang_dung` (chỗ **thực** đã ghi); `cho_phep_ban` đổi thành ba
câu hỏi — RAM (cứng) → kho thực dùng < 80 % → bán chồng ≤ **3,0×**. Trang bán thêm câu
*"dung lượng đĩa là hạn mức trên kho lưu trữ dùng chung, không phải ổ cứng cấp riêng"*.
**55 test xanh** (`test_251` 45 + `test_252` 10), trong đó 4 test mới cho ba cái phanh.

Hiệu quả đo được ngay: trước V14 node bán được **0 máy** (đĩa chặn); sau V14 còn
**1 máy `vps-nho`** — và giờ thứ chặn là **RAM**, đúng như nó phải thế.

**Cần cấp thêm để làm việc 1, 2, 4:**

- **Token Proxmox có quyền ghi** — role `LTTVps` (đã soạn sẵn lệnh trong tài liệu
  phân tích mục 8), hoặc tạm thời `PVEVMAdmin` + `Datastore.AllocateSpace`.
- **`command.run` cho credential Nexus trên máy B** — để dừng/khởi động VMware đúng
  cách. Không có nó thì chỉ còn `process.kill`, tức **cắt điện** Proxmox — đúng thứ
  đã để lại `cleanShutdown=FALSE` lần trước.
- **Một khung giờ bảo trì**: nới RAM làm **cả 8 máy của chủ nhà tắt theo**. Đây là
  quyết định về thời điểm, không phải về kỹ thuật.

### Còn chặn (ngoài repo)

1. ~~Kiểu kho + loại ổ~~ ✅ **ĐÃ TRẢ LỜI 2026-08-22**: kho `vmdata` là **LVM-thin
   475 GB**; ổ `H:` là **NVMe** (chủ sản phẩm xác nhận) → bảng giá giữ được chữ NVMe.
   **Việc mới thay chỗ nó:** node đang đầy — phải nới RAM (P0b) trước khi bán được máy nào.
2. ~~Dữ liệu cổng đang chạy sẵn~~ ✅ **ĐÃ TÌM THẤY 2026-08-22**: gateway dựng từ
   12/08 — Vultr **45.76.185.75**, WireGuard UDP 51820, DNAT 33891–33895, thêm máy
   bằng `Add-GuestToGateway.ps1`. Trần băng thông **~150–160 Mbps** (CPU 1 vCPU của
   VPS), RTT trong guest **54–56 ms**, tunnel chết thì fail-closed. Chi tiết ở mục
   4.5 của `docs/VPS/PHAN_TICH_VPS_PROXMOX.md`.
3. **Pháp lý VN** (đăng ký kinh doanh / hoá đơn) — việc của chủ sản phẩm, ảnh hưởng tới code.

*(Việc kiểm router VNPT forward dải cổng — **hết là vấn đề** từ Q104: đường về nhà là
WireGuard do phía nhà chủ động gọi ra, không cần mở cổng nào trên router.)*

---

## H40 — Dẹp app lỗi thời: gỡ HẲN 4 app khỏi kho mã

**Chốt 2026-08-25** theo yêu cầu chủ sản phẩm. Quyết định nền: **Q108** (socialbot,
thay Q10) và **Q109** (kichban · mediatools · demo).

- [x] **H40.1 — `socialbot`** ✅ **XONG 2026-08-25.** Xoá `apps/socialbot/`,
      `core/` (15.046 dòng), `utils/`, `server/services/` (12 tệp), 7 module route
      = **43 route công khai (62% bề mặt cũ)**, 10 template, **44 tệp test
      (~1.017 test)**, `worker_main.py`, `config.example.json`,
      `docs/tiktok-submission/`.
      *Đo trước khi xoá:* CSDL production có **0** job, **0** `app_access`, **0**
      `app_projects` mang slug đó, và hai kho token `tokens.enc`/`tiktok_tokens.enc`
      **chưa bao giờ được tạo** — chưa khách nào từng kết nối.

- [x] **H40.2 — ba móc nối của nền tảng vào `core/`** ✅ **XONG 2026-08-25.**
      Không cái nào hiện ra khi grep "socialbot":
      ① `/health/ready` trả 503 khi không đọc được `data/config.json` — tệp cấu
      hình **của socialbot** → nay nền tảng không đọc tệp cấu hình nào lúc khởi
      động (`platform_core/settings.py` mới, chỉ giữ `Environment`);
      ② trang chủ chạy `doctor.run()` mỗi lượt tải để tính một huy hiệu mà **chỉ
      socialbot khai** (`blocker_titles`);
      ③ `tests/conftest.py` có **ba fixture `autouse`** bắt MỌI test trong kho trả
      thuế dọn hộ một engine chúng không dùng.

- [x] **H40.3 — `kichban` · `mediatools` · `demo`** ✅ **XONG 2026-08-25.**
      1.405 dòng, **11 ToolSpec**, 4 tệp test, 11 nhãn palette Agent Canvas.
      ⚠️ **Cái giá đã đo và chủ sản phẩm đã chấp nhận:** **7/10 workflow Agent đang
      lưu mất node** (3 `text.script`, 4 `text.generate`, 1 `asset.image`) + **4
      `agent_runs`**. Bốn tool `asset.*` là node **đầu vào** của workflow.
      `apps/demo` — khuôn của bốn bộ test hạ tầng — thay bằng **app THỬ tổng hợp**
      ở `tests/conftest.py::app_thu`, sống trong bộ nhớ một test.

- [x] **H40.4 — audit dọn sạch** ✅ **XONG 2026-08-25.** Tìm ra và đã xử lý ba nhóm
      sót: ① `tools/demo_fb`, `tools/demo_v2`, `scripts/` — đồ dựng video nộp hồ sơ
      TikTok/FB (2.456 dòng + 3,3 MB media, gitignore nên **xoá không đảo được**);
      ② **10 chỗ tài liệu** chỉ vào `apps/demo/` như một khuôn còn tồn tại —
      nghiêm trọng nhất là `CLAUDE.md` và `docs/03_THEM_APP_MOI.md` dặn *"copy
      `apps/demo/`"*; ③ **105 mục `.po`** chỉ còn trỏ tới tệp đã xoá — **cố ý giữ**,
      vì trích lại làm `msgmerge` sinh thêm **25 bản dịch sai**.
      *Bằng chứng:* gõ thật vào **21 URL** của app đã gỡ → 404 cả 21; **12 URL** còn
      sống → 200/303. Không đếm đối tượng route: bản Starlette này để lại
      `_IncludedRouter` không mở ra được.

**Kết quả:** danh mục app **19 → 14**; bộ test **4.727 → 4.093**; bánh cóc hạ được
ba mốc (chuỗi chưa bọc `_()` 1.413→816, nuốt lỗi lặng lẽ 90→74, test trùng số 24→22).

- [x] **H40.5 — deploy** ✅ **XONG** — ~~"Production vẫn chạy bản đủ 19 app"~~.
      Đo 2026-08-29: `C:\LTTPlatform\app\apps\` có **15** thư mục, **bằng đúng**
      cây nguồn; `socialbot` · `demo` · `kichban` · `mediatools` **không còn** ở
      cả hai bên. Điểm lùi trước cả đợt vẫn là **`ec6a00c`**.
- [x] **H40.6 — kiểm trên trình duyệt thật** ✅ **XONG** — quy tắc 5b đòi kiểm
      trên **URL công khai**, và đây là số đo trên đúng URL đó (2026-08-29):

      /socialbot 404 · /demo 404 · /kichban 404 · /mediatools 404

      ⭐ Bốn dòng này là **đối chứng dương của việc gỡ**: một app đã gỡ mà route
      còn trả 200 hay 303 thì nó chưa gỡ xong. `404` là thứ duy nhất chứng minh
      được, và nó phải đo trên URL công khai chứ không phải loopback.

### 🔴 H40.7 — `gate.py` đầy đủ: **CHƯA CHẠY XONG LẦN NÀO**

Chủ sản phẩm quyết **bỏ gate** ngày 2026-08-25 để chuyển sang đợt sửa soạn lại hệ
thống. Ghi thẳng ở đây, không tô hồng: **hạng mục H40 đóng mà KHÔNG có một lượt
`python tools/gate.py` đầy đủ nào hoàn tất.**

Bốn lượt đều dừng giữa chừng, và ba lượt là do cây đổi chứ không do lỗi:

| Lượt | Dừng ở | Vì sao |
|---|---|---|
| 1 | bước 18/22 | chủ sản phẩm giao thêm 3 app → cây sắp đổi |
| 2 | `pytest` | audit tìm ra residue phải dọn |
| 3 | `pytest` (23 phút) | một phiên khác chạy `pytest` song song 23:30–23:50 ⇒ hai bộ tranh thư mục tạm/CSDL test, kết quả không đáng tin |
| 4 | `pytest` | chủ sản phẩm quyết bỏ |

⭐ **Bằng chứng THẬT SỰ có** (chạy trên đúng cây đã commit `09ee8e9`), để phiên sau
không phải chạy lại từ đầu:

```
bien dich duoc          PASS  2.100 tep, hong 0
ten chua dinh nghia     PASS  406 tep, 0
lint hop dong app       PASS  14 app, ERROR 0, WARN 1 (qualitylab, co tu truoc)
quet bi mat             PASS  0 finding
system profile          PASS  khop nguon
golden API              khong khac biet
hop dong API            27 route, 7 tool, 22 ma loi — khong doi
tai lieu sinh ra        PASS   SDK khop hop dong   PASS
pytest theo cum         test_35·37·43·60·61·63·66·72·88·145·147·173·187·190·212 PASS
go THAT vao URL         21/21 URL app da go -> 404 · 12/12 URL con song -> 200/303
```

⛔ **Thứ CHƯA có bằng chứng** — phiên sau phải tự chạy, đừng tin là đã xong:

1. **`pytest` toàn bộ 4.093 test** trên cây cuối. Các cụm đã chạy phủ phần bị đợt
   xoá đụng tới, nhưng **không phủ hết kho**.
2. **Ba bộ test frontend** trên cây cuối (chúng xanh ở `gate --quick` của một
   trạng thái cây **trước đó**, không phải cây này).
3. **Bất biến đa tiến trình** (`tools/check_multiproc.py`) — bước này chỉ có ở gate
   đầy đủ.
4. **Kiểm trên trình duyệt thật** — xem H40.6.

⚠️ Và một thứ đã đỏ **từ trước đợt xoá**, đừng chẩn đoán nhầm thành hậu quả của nó:
`test_44_release_build` đỏ 2 test vì **ba bundle frontend cũ** so với `vite.config.ts`
(phiên khác đổi). Đã chứng minh bằng `git stash`: đỏ y hệt ở `ec6a00c`. Hệ quả:
`tools/build_release.py` **chưa dựng được gói phát hành** cho tới khi chạy
`npm run build` cho cả ba rồi `python tools/build_system_profile.py`.

### H40.8 — Việc còn treo của đợt H40, chuyển từ nhật ký sang đây

⚠️ **Vì sao mục này tồn tại, và nó là một bài học về quy trình chứ không về việc.**

Sáu việc dưới đây vốn nằm ở mục *"Còn tồn đọng"* cuối hai mục nhật ký ngày
2026-08-25. Đo lại: **3/6 chưa từng vào kế hoạch.** Nghĩa là chúng chỉ tồn tại ở
một nơi được đọc **theo thời gian**, trong khi việc thì được tìm **theo việc** —
một việc chỉ nằm ở nhật ký là một việc chỉ tồn tại trong quá khứ.

⛔ Và đây đúng là lớp lỗi vừa sinh ra một sự cố tiền thật ở chỗ khác: chú thích
   `server/api/streaming.py:257` ghi thẳng *"KHÔNG AI QUÉT NÓ… khách mất tiền
   lặng lẽ"* — người viết **đã biết**, **đã ghi**, và việc vẫn không vào lịch.
   Khoảng cách giữa *"đã biết"* và *"đã xếp lịch"* là chỗ hỏng, không phải mã.

| # | Việc | Ai làm |
|---|---|---|
| a | **Deploy** đợt xoá 4 app | chủ sản phẩm |
| b | **7/10 workflow Agent mất node** ngay khi deploy. Không có bước di trú. Nếu muốn đỡ: một thông báo trong Canvas khi mở workflow có node không còn tồn tại — **không** hồi sinh app | chủ sản phẩm quyết, tôi làm được |
| c | **Ba bundle frontend stale** ⇒ `tools/build_release.py` không dựng được gói phát hành. Đỏ **từ trước** đợt xoá (chứng minh bằng `git stash` ở `ec6a00c`). Sửa: `npm run build` cả ba **rồi** `python tools/build_system_profile.py` | phiên nào rảnh |
| d | **14 ảnh PNG ở gốc kho đang được git theo dõi** (`audit_*`, `nexus_*`, `vm200-*`, `live_nexus_hero`). `.gitignore` không tác động tới tệp đã theo dõi ⇒ cần `git rm --cached`. Là tài sản của hai phiên khác | chủ sản phẩm |
| e | **Dữ liệu socialbot còn trong `data/`** (`config.json`, `content_history.db`, `audit_log.jsonl`, `session_locks/`). Không tiến trình nào còn mở chúng; xoá tệp trên máy đang chạy thật là **không đảo được** nên tách khỏi việc gỡ mã | chủ sản phẩm |
| f | **Đăng ký Meta App + TikTok app** — tài sản **ngoài kho**. Mã đã đi, đăng ký không tự mất | chủ sản phẩm |
| g | **Bẫy 7 + 8 chưa vào `BAY_TRONG_CONG_CHAT_LUONG.md`**: ⑦ `__pycache__` mồ côi hồi sinh một app đã xoá (gate báo *"thiếu manifest.py"* cho một thư mục rỗng); ⑧ `_frontend_source_sha256` băm cả `tests/` nên đổi một hằng số `timeout` làm gói phát hành thành stale, với câu báo lỗi **nêu tên sai nghi phạm** (*"built with the wrong Node"* trong khi Node vẫn đúng) | phiên nào đụng tới tài liệu đó |

⭐ **Đề xuất chặn tương lai, không dọn quá khứ:** thêm một bánh cóc vào gate đòi
mỗi gạch đầu dòng *"Còn tồn đọng"* trong `NHAT_KY.md` phải có mã ứng với một dòng
trong tệp này — cùng họ với `check_bo_qua.py` và `check_dich_thieu.py`. Chi phí
một lần, và nó bịt **lớp lỗi** thay vì từng ca.

> ### ✅ ĐỐI CHIẾU 2026-08-26 — đề xuất trên ĐÃ ĐƯỢC THI HÀNH, nhưng **khác cách**
>
> Nhận định của H40.8 đúng và nó là gốc rễ. Nhưng khi bắt tay làm, cách *"bắt mục
> Còn tồn đọng phải mang mã"* **đã bị bỏ**, vì hai lý do đo được:
>
> 1. **104 mục** hiện có đều là văn xuôi tự do ⇒ ép mã là **dọn quá khứ**, trong
>    khi bánh cóc phải **chặn tương lai**.
> 2. Một phép kiểm phán xét văn phong sẽ kêu sai liên tục — và một máy dò kêu
>    suốt ngày là một máy dò bị tắt trong tuần đầu.
>
> ⭐ Hình dạng **thật** của lớp lỗi không phải *"ghi chép thiếu mã"*. Nó là:
> **một hàm quét/cảnh báo tồn tại mà không đường thực thi nào gọi tới.** Cái đó
> đo được bằng máy, không cần phán xét gì.
>
> ⇒ Đã làm `tools/check_chuong_chua_treo.py`, vào gate. **Đã chứng minh nó bắt
> đúng ca gốc**: gỡ dòng cắm `costing.scan_for_alerts` trên một cây giả ⇒ báo
> ngay (`test_308`). Và nó tìm ra **ca thứ ba** chưa ai biết:
> `upload_sessions.reconcile`.
>
> ⚠️ **Nói thẳng giới hạn:** nó **không** bắt được ca sao lưu (kịch bản
> PowerShell) và ca link-404 (bài học nằm trong chú thích). Nó bắt hai ca nguy
> hiểm nhất, và bắt chắc chắn. Một phép kiểm hẹp mà đúng có giá trị hơn một phép
> kiểm rộng mà đoán.
>
> **Mục (c) của bảng trên cũng đã xong** — ba bundle đã dựng lại, `test_44` từ
> 2 đỏ về **35 passed** (`a5274bf`). Đáng ghi thêm một tầng mà bảng trên chưa
> nêu: lỗi thứ hai của `test_44` đỏ **không phải** vì đường chặn bí mật hỏng, mà
> vì chốt bundle-cũ bắn trước và **nuốt mất** `SystemExit` mà phép kiểm đó định
> bắt ⇒ **phép kiểm chặn rò rỉ bí mật đã không chạy** suốt thời gian đó. Một
> gốc, hai triệu chứng, và triệu chứng thứ hai đáng lo hơn hẳn.

---

## H41 — Chạy trọn bộ prompt MVP Optimization V2 (2026-08-26)

**Nguồn:** `AppStudios_MVP_Optimization_Prompt_Pack_V2` (16 prompt, 2 pha).
**Báo cáo:** `docs/MVP_OPTIMIZATION_V2/` — 14 tệp.
**Chủ sản phẩm bỏ cổng duyệt** và yêu cầu chạy thẳng 00→15.

### Đã xong

| | Việc | Commit |
|---|---|---|
| ✅ | 12 báo cáo pha A (00→11) | `ede373a`, `05a20ac` |
| ✅ | **M-01** máy dò giữ chỗ treo + cắm vào bảo trì dưới lease + cảnh báo `HOLD_STRANDED` | `a5274bf` |
| ✅ | **M-02** cắm cảnh báo biên lợi nhuận âm (viết xong từ lâu, chưa ai gọi) | `a5274bf` |
| ✅ | **B-01** dựng lại 3 bundle ⇒ gói phát hành dựng được, phép kiểm bí mật chạy lại | `a5274bf` |
| ✅ | **U-02** link 404 `/ltt-llm` trong header mọi khách + luật linter + bất biến `test_60` | `db6147e` |
| ✅ | **A-04** hợp đồng `apps → server` (4 module) + linter + `AGENTS.md` §8.2b/8.2c | `3d804ee` |
| ✅ | Bánh cóc **kích thước route `server/`** (3 tệp baseline) | `f625199` |
| ✅ | Bánh cóc **chuông chưa treo** + `test_308` | `f625199` |
| ✅ | Sửa mâu thuẫn `CLAUDE.md` về `LTT_PUBLIC_API_TOOLS` | `3d804ee` |
| ✅ | **H41.1/O-01** lịch sao lưu + diễn tập phục hồi; `DATA_RECOVERY_GATE: PASS` | `5a258e8` |
| ✅ | **H41.10** mốc context engine/public/output + canary 413 trước GPU | `6388394` |
| ✅ | **H41.11** admission thời gian non-stream theo input+output + canary biên | `3e6171b` |

**Gate: 19 → 21 bước.**

### Còn treo

| ID | Việc | Ai làm |
|---|---|---|
| ✅ **H41.2** | E3 cho các trang Golden Journey. **Sửa 2026-08-29:** hàng này ghi "treo" trong khi nhật ký 2026-08-26 đã có E3 thật — GJ-1/GJ-2/GJ-6 **PASS** trên `https://app.lttstudios.com` (job thật `23f40fa0`, tiêu 5 credit thật). Nhật ký thắng kế hoạch (`NHAT_KY.md` đầu file) | **GJ-3 cố ý giữ E2**: nghiệm thu nó đòi một giao dịch tiền thật, không phải một hạng mục kỹ thuật |
| **H41.3** | `hold_expires_at` + tự hoàn ⇒ INV-5 từ *quan sát* thành *bảo đảm*. Đụng schema + đường tiền | cần quyết định |
| ✅ **H41.4** | `server/api` không còn biết trực tiếp tên app: executor đồng bộ được khai báo trong `ToolSpec`, project sang catalog và resolver generic; `/messages` `/responses` `/chat/completions` dùng cùng adapter app-owned | `60a76bc` + deploy 2026-08-29 |
| ✅ **H41.9** | **Admission/queue nhiều API → GPU**: gom async, sync và streaming vào một admission plane; thêm global queue cap, quota-lock chống race, fair scheduler, retry/ambiguous-provider, queue metrics; Q0–Q3 chạy CPU/DB/mock, Q4–Q6 chạy trong cửa sổ GPU độc quyền. Plan chi tiết tại `docs/_luutru/codex_2026-08-27/PLAN_TRIEN_KHAI_NEXUS_QWEN.md` *(dời khỏi `.codex/` ngày 2026-08-29 khi đóng hồ sơ Codex)* | **ĐÃ NGHIỆM THU Q6 2026-08-29:** Q0–Q3 CPU/DB/mock đã khóa; full gate **23/23 PASS**; cap `65000`, engine `131072`, output `32768`, `parallel=1` đã deploy. Public async canary 7 arm có queue-age p50 `1,062s`, p95 `1,861s`; GPU telemetry 450 mẫu/15 phút, CPU soak `320/320`; over-cap hold được hoàn. Giữ `parallel=1`, chưa rollout rộng. |
| **H41.5** | Khai bề mặt công khai của `upscalevideo` — cạnh cross-product **duy nhất** của cả kho (`taovideo/routes.py:548,577`) | phiên sau |
| ✅ **H41.6** | Chẻ `server/routes/developer.py` (1.521 dòng / 32 handler) theo use case | `1f0e93c` |
| ✅ **H41.7** | **Bề mặt MVP**: **6/10** app khách ẩn danh thấy mang nhãn *Đang phát triển*. Bề mặt hôm nay là **mặc định manifest cộng lại**, không do ai chọn. ⚠️ **Sửa 2026-08-29:** con số cũ "5/8" là số của **máy dev** — máy dev thiếu cờ `LTT_VPS`/`LTT_NEXUS` nên đếm hụt hai app. Đo lại trên `https://app.lttstudios.com` (ẩn danh, HTTP 200): 10 thẻ app, 6 nhãn *Đang phát triển* — `agent` `autosubvideo` `chataistudio` `taoanh` `taoclipngan` `vps`; 4 mục `released` — `nexus` `prompt_ai_ommi` `taovideo` `upscalevideo`. Số dùng để quyết phải là số của production  | **DA QUYET 2026-08-29: GIU NGUYEN ca 10.** Khach van thay ca 6 app mang nhan *Dang phat trien*, va nhan do it nhat la TRUNG THUC. ⚠️ Day la quyet dinh CHAP NHAN mot cua hang nua hoan thien, khong phai mot viec chua lam — doi lai la moi app dang co nguoi dung that deu giu duoc duong vao. Dung mo lai nhu mot phat hien moi. |
| ✅ **H41.8** | ~~Cân nhắc đổi mặc định `AppManifest.public` thành `False`~~ — gốc của H41.7: viết một app mới mà không khai gì thì nó **tự lên catalog công khai** | **ĐÃ QUYẾT 2026-08-29: GIỮ `True`.** ⚠️ Đây là quyết định **chấp nhận rủi ro đã biết**, không phải "chưa xét": app thứ 15 viết ra mà quên khai vẫn sẽ **tự lên catalog công khai**. Ai gặp lại chuyện đó thì đây là câu trả lời, đừng mở lại như một phát hiện mới. Muốn lật thì phải có lý do mới, và phải rà 14 manifest hiện có trong cùng lô — quên một cái là một app **biến mất** khỏi cửa hàng. |

⛔ ~~**H41.2 và mọi phép đo E3 phải chờ deploy.** Production đang chạy `ec6a00c`;
link 404 `/ltt-llm` **vẫn còn ở đó**, và mọi bản vá của đợt này chưa có.~~
**ĐÃ QUA 2026-08-29.** Giữ câu cũ để truy vết. Production nay chạy `7bf6ba3`
(deploy 2026-08-29, `so_deploy` khớp 461 · lệch 0), link 404 `/ltt-llm` đã hết,
và E3 đã lấy được — xem hàng H41.2 ở trên.

📌 **Thứ tự làm các hàng còn treo, kèm đường phụ thuộc và tiêu chí nghiệm thu
từng đợt: `docs/KE_HOACH_NOI_TIEP_2026-08-29.md`.** Điểm mấu chốt của tài liệu đó,
không thấy được nếu chỉ đọc bảng phẳng này: **H41.5 và H35.10 có chung một nút
thắt là H35.10a** (đo thời lượng phía máy chủ lúc báo giá) — làm một việc rủi ro
thấp thì mở khoá cả hai.

**Checkpoint Q115 2026-08-28:** public cap đã triển khai thử ở `81000` qua Nexus,
nhưng canary 80K đo `88.224` token thật và `120,322s`; ladder 70K/65K lần lượt
đo `77.197`/`71.714` token và `90,575`/`82,325s`. Vì vậy H41.9 vẫn **ĐANG LÀM**;
chưa mở `parallel>1` hoặc public rộng cho tới khi chốt cap ổn định bằng lặp warm/cold.

**Checkpoint Q116 2026-08-28:** theo điều kiện “81K phải ổn định”, cap vận hành
được hạ xuống `65000`; artifact đã deploy trên B (health 200, service
Running/Automatic). Boundary code-like trả 413 trong `0,045s`, GPU trước-sau
`0%/22486 MiB`; canary 64K trả 200/quality PASS, usage `70613`, `92,875s`,
VRAM `22486 MiB`, max `69 C`. CPU admission harness đồng thời drain 160 jobs,
`p95=4,724s`, `provider_calls=0`, `gpu_reads=0`. Q4 cap gate qua; chuyển Q6
canary/queue soak với `parallel=1`, Q5 concurrency DEFER. Q6 arm 60K tiếp theo
trả 200/quality PASS, usage `66189`, `74,212s`, VRAM `22486 MiB`, max `69 C`;
tiếp tục lấy p50/p95 thay vì chốt SLA từ một arm.

**Q6 CPU soak checkpoint:** SQLite cô lập đã drain `1000/1000` jobs trên 16
accounts, queue cuối `0`, admission-delay p95 `27,734s`, poll p50 `1,112ms`,
không provider/GPU read. GPU canary đã có short/60K/64K/65K PASS; arm 65K lặp
`94,243s` và 60K lặp `73,727s`, p50 quan sát khoảng `74s`, max `94,243s`;
còn đo queue-age end-to-end trên canary plane trước khi nghiệm thu Q6.

---

## H42 — Dev API: ba phương thức cắm Codex/Claude (2026-08-26)

**Quyết định:** Q110. **Nguồn yêu cầu:** chủ sản phẩm yêu cầu hoàn thiện và
deploy trong cùng phiên.

- [x] **H42.1 — EXE MVP thật** (2026-08-26): chọn từng bề mặt, bắt lỗi bridge, hiện thời gian,
      đo trạng thái từ file/registry thật; có Codex VS Code; bước hỏng trả mã
      khác 0, không được ghi nhận thành công.
- [x] **H42.2 — ZIP + BAT không GUI** (2026-08-26): console EXE thật, không cần Python; BAT
      tự xin Administrator; khóa nhập ẩn và chỉ truyền qua environment của tiến
      trình con, không nằm trên command line hay tệp tạm.
- [x] **H42.3 — web + hướng dẫn** (2026-08-26): `/developers/cli`, `/huong-dan` và trang công
      cụ trình bày đúng ba phương thức; có route tải ZIP, phiên bản, dung lượng,
      SHA-256; hướng dẫn tay vẫn đầy đủ.
- [x] **H42.4 — phát hành** (2026-08-26): `gate.py` **23/23 PASS** trên cây sạch; EXE/ZIP được
      quét Defender; artifact chép vào `C:\LTTPlatform\data\api_dist`; deploy
      bằng release ZIP; Playwright xác minh tải được cả hai artifact, hướng dẫn
      tay hiển thị và không có console/network error.

**Rollback:** code/web dùng `C:\LTTPlatform\app.previous` qua
`deploy/windows/rollback.ps1`; artifact là dữ liệu ngoài release nên giữ lại
bản 1.0.0 và chỉ gỡ bản 1.1.0 nếu xác định chính artifact lỗi.

## H43 — ChatLTT: sản phẩm chat LTT-native trên ba model nhà (2026-09-02)

Gói: `LTTCHAT_AUTONOMOUS_DEEP_BUILD_V2` (14 phase tự chủ). **Kế hoạch + phân tích:
`docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md`. Trạng thái: `docs/CHATLTT/STATE.md`.**

Hình dạng: app mới `apps/chatltt/` (không sửa `chataistudio`), giao diện
LibreChat-class bằng React island, gọi `text.chat` / `image.ltt` / `speech.ltt`
qua **một facade mỏng `platform_core/runtime_noi_bo/`** (không API key, không
URL máy, không engine song song). Dữ liệu hội thoại dạng cây, bảng riêng `chatltt_*`.

| # | Phase gói | Việc | Trạng thái |
|---|---|---|---|
| H43.0 | 00 | Bootstrap: cây/gốc SHA/dải test 600–699/ranh giới phiên | ✅ 2026-09-02 |
| H43.1 | 01 | LibreChat `v0.8.7` tham chiếu hành vi — 12 hệ con, 22 ADOPT/8 ADAPT/11 REJECT, 18 tiêu chí nghiệm thu (`docs/CHATLTT/reports/01_librechat_tham_chieu.md`) | [x] 2026-09-03 |
| H43.2 | 02 | Gap runtime nội bộ → `platform_core/runtime_noi_bo/` (luong/danh_muc/job) + `AppManifest.so_lan_thu` + `ToolSpec.tuy_chon_dong`; `streaming.py` gọi facade; test_600–602 40 pass, 24 tệp ghim 500 pass (`reports/02_runtime_noi_bo.md`) | [x] 2026-09-03 |
| H43.3 | 03 | Text: chuẩn hoá chunk→sự kiện, `DemToken` đọc `timings.cache_n`, SLO text, **Q120** đóng D12 (Q116↔`ngan_sach.py`); LIVE hoãn Phase 12 (`reports/03_text_noi_bo.md`) | [x] 2026-09-03 (deterministic) |
| H43.4 | 04 | Ảnh: `platform_core/jobs.DangBan` ⇒ bận là `resource_wait` không tiêu lượt thử; `LoiYeuCauAnh`; hỏi `health()` trước khi dịch prompt (`test_606–608`, `reports/04_anh_noi_bo.md`) | [x] 2026-09-03 (deterministic) |
| H43.5 | 05 | Tiếng: `DangBanTam(DangBan)`; giọng người khác ≡ không tồn tại; trần 1.500 giữ nguyên; tiền theo giây `ffprobe` (`test_609–612`, `reports/05_tieng_noi_bo.md`) | [x] 2026-09-03 (deterministic) |
| H43.6 | 06 | Catalog theo chính sách sản phẩm, fail-closed — `apps/chatltt/services/chinh_sach.py`, `AppManifest.suc_khoe`, alias mới chỉ bằng registry (`test_613/614`, `reports/06_catalog_chinh_sach.md`) | [x] 2026-09-03 |
| H43.7 | 07 | Bảng `chatltt_*` (cây, `current_leaf_id` ở CSDL, xoá mềm) + migration `7d2c1e9f4a03` + `services/{hoi_thoai,su_kien}.py` + reload từ CSDL (`test_616–618` 16 pass, `reports/07_du_lieu_cay_su_kien.md`) | [x] 2026-09-03 |
| H43.8a | 08 | Text (máy chủ): `apps/chatltt/routes/*`, `services/{luot,dang_chay}`, SSE + Dừng + nối lại, IDOR/CSRF (`test_623`, `reports/08a_text_backend.md`) | [x] 2026-09-03 |
| H43.8b | 08 | Text (giao diện): bundle React `frontend/chatltt` (30 test), gate/build_release biết bundle thứ tư, kiểm trình duyệt thật (stream · tạo lại · chuyển nhánh · nhánh sống qua reload · 390 px) — **mốc "chỉ-text dùng được độc lập" ĐẠT** (`reports/08b_text_giao_dien.md`) | [x] 2026-09-03 |
| H43.9 | 09 | Ảnh + tiếng trong hội thoại: báo giá→xác nhận→nộp (Q84), tiến độ 2 s (Q87), khối ảnh/âm, cửa tài sản có kiểm sở hữu; bắt được path traversal và lỗi bố cục đè chân trang (`test_624/625`, `reports/09_anh_tieng_trong_hoi_thoai.md`) | [x] 2026-09-03 |
| H43.10 | 10 | UX: Đọc to · số dư tự cập nhật · `anhnoibo.suc_khoe` · ba phím tắt · focus/aria · **reduced-motion** · ma trận 390–1920 px · không lộ ID thô (`reports/10_ux.md`) | [x] 2026-09-03 |
| H43.11 | 11 | Mở rộng: ba fixture + hai phép kiểm tĩnh (không `if <tên model>`, không import provider) + `docs/CHATLTT/11_THEM_MODEL_MOI.md` có test canh (`test_626`, `reports/11_mo_rong.md`) | [x] 2026-09-03 |
| H43.12 | 12 | Torture: đồng thời/tiền/bảo mật/dữ liệu/hiệu năng | [ ] |
| H43.13 | 13 | Nghiệm thu tươi + gate đầy đủ + báo cáo cuối; **không deploy** | [ ] |

## H44 — Priority Scheduler + Queue Intelligence V1 (2026-09-10)

Nguồn yêu cầu: campaign `PRIORITY SCHEDULER + QUEUE INTELLIGENCE V1`.
Quyết định: Q122. Hồ sơ canonical: `docs/SCHEDULER_V1/`.

- [x] H44.0 Preflight + baseline + audit kiến trúc — 2026-09-10: tách worktree
      `architecture/scheduler-priority-v1`; xác nhận một queue PostgreSQL,
      SKIP LOCKED, fair-share, admission/lease, polling/events/webhook hiện hữu;
      full gate baseline chưa chạy và được ghi `NOT_RUN`, không mượn bằng chứng.
- [x] H44.1 Scheduler contract — 2026-09-10: khóa Q122, strict
      `INTERNAL > EXTERNAL`, non-preemptive, fairness trong lớp, một ranking cho
      claim/snapshot/ETA, metadata lạ fail-closed về external.
- [x] H44.2 Job metadata + additive migration — 2026-09-10: thêm
      origin/priority_class, default fail-closed và migration/index additive.
- [x] H44.3 Canonical ranking + claim/fairness/concurrency regression —
      2026-09-10: strict priority, fair account/aging/FIFO, non-preemptive;
      kiểm PostgreSQL hai worker đã PASS.
- [x] H44.4 Trusted ingress classification + chống spoof — 2026-09-10:
      middleware/server scope đóng lớp, public body/header không nâng quyền.
- [x] H44.5 Queue snapshot + dynamic position — 2026-09-10: claim và snapshot
      dùng chung ranking; position cập nhật theo trạng thái thật.
- [x] H44.6 ETA MVP + fallback trung thực — 2026-09-10: rolling median theo
      resource/priority; thiếu lịch sử trả null.
- [x] H44.7 Public/web status + polling; SSE/webhook compatibility —
      2026-09-10: status trả queue + nhịp poll; event/webhook hiện hữu giữ nguyên.
- [x] H44.8 Observability/admin + starvation visibility — 2026-09-10: metric
      depth/wait/lifecycle/override/fair rotation và cảnh báo external 300 giây.
- [x] H44.9 Performance 1k/5k/10k + full regression — 2026-09-11:
      benchmark đạt 20,585/81,586/174,181 ms; sau tích hợp checkpoint ASV,
      L3 PASS 32/32, gồm PostgreSQL migration, M-1 và bất biến đa tiến trình.
- [x] H44.10 Real E2E + `FINAL_REPORT.md` — 2026-09-10: Playwright local
      cô lập PASS, console 0 error, failed request 0; chưa deploy production.
