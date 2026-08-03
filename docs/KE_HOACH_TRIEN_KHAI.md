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

- [ ] **Cấp credit dùng thử sau xác thực** — `/verify-email` đã có đúng chỗ nối
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
- [ ] **Trang admin (sqladmin, Q15): dời sang mốc riêng "H3-admin"** — xem dưới

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
- [ ] Hỏng có chủ ý: giết worker giữa chừng → nhặt lại (đã có reclaim_orphans +
      test; nghiệm thu bằng cách giết process khi có job dài — để khi có tool
      chạy lâu thật, demo quá nhanh để giết giữa chừng)
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
- [ ] R4–R7 Contract, design và lát cắt dọc — **WIP, chưa commit/deploy**: studio,
  filter/history từ job owner-scoped và cầu Seedance→Upscale đang có code dở;
  phải đóng theo UP1/UP3 trước khi coi hoàn thành.
- [ ] R8–R10 Nghiệm thu đa state/viewport, full gate, memory và release.

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

Tiến độ H15 hiện tại: **30/38 vé (78,9%)**; **11/16 stage hoàn tất**. H15.S11
đang thực hiện tuần tự: SCRIPT-UI đã PASS, tiếp theo SCRIPT-FEAT.

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
- [ ] H15.S11 Kịch bản — tuần tự SCRIPT-UI-001 → SCRIPT-FEAT-001.
  - [x] H15.S11.1 SCRIPT-UI-001 — 2026-08-03: Carbon Red composer với output
    outline, counter/cost; history 12 job owner-scoped; result workspace chia
    title/hook/sections/outro/metadata thành field chỉnh sửa trong phiên và
    copy/download Markdown. Persistence/version ghi rõ phase sau. Browser job/
    credit/history/editor/download/mobile PASS, console/network sạch; regression
    14 passed; full suite 1.972 passed, 8 skipped, 23 subtests; secret scan 0.
  - [ ] H15.S11.2 SCRIPT-FEAT-001 — source/research/version/shot-list.
- [ ] H15.S12 Clip ngắn — tuần tự CLIP-UI-001 → CLIP-FEAT-001.
  - [ ] H15.S12.1 CLIP-UI-001 — library/transcript selection/editor/compare.
  - [ ] H15.S12.2 CLIP-FEAT-001 — score rationale/brand/multi-platform package.
- [ ] H15.S13 Admin/operator.
- [ ] H15.S14 Website marketing route/deploy.
- [ ] H15.S15 DEEP re-audit + full release gate.
