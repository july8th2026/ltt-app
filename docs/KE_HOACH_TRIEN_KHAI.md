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
H0.1  Kiểm chứng đường ra Internet  ⚠️ CHẶN việc dựng Tunnel
     │
H1  Người dùng + PostgreSQL   ─┐
H2  Hàng đợi job              ─┼─►  H4  Nghiệm thu bằng apps/demo
H3  Sổ credit                 ─┘         │
                                         ▼
                              H5  Tool thật đầu tiên (thumbnail_api)
                                         │
                       ┌─────────────────┼─────────────────┐
                       ▼                 ▼                 ▼
              H6 Thanh toán    H7 File lớn (R2)    H8 Thêm tool
```

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

## H0.1 — Kiểm chứng đường ra Internet ⚠️ CHẶN VIỆC DỰNG TUNNEL

**Mục tiêu:** biết chắc đường ra Internet khả thi **trước khi** viết thêm code
hay chạy `setup/3-cloudflare.ps1`.

### Vì sao đây là một hạng mục riêng

Đo được ngày 2026-07-31:

```
lttstudios.com  →  hoian.vclouddns.com / danang.vclouddns.com   (inet.vn)
MX  : không có       TXT : không có
```

Cloudflare Tunnel hoạt động bằng một CNAME trỏ tới
`<tunnel-id>.cfargotunnel.com`, và tên miền đó **chỉ phân giải được qua chính
hệ thống Cloudflare**. Lệnh `cloudflared tunnel route dns` trong
`setup/3-cloudflare.ps1` gọi API Cloudflare để tạo bản ghi trong zone — zone chỉ
hoạt động khi tên miền dùng nameserver của Cloudflare.

Chạy bước 3 bây giờ sẽ **hỏng ở khâu gần cuối**, sau khi đã tải cloudflared,
đăng nhập, tạo tunnel và ghi cấu hình. Đó là kiểu hỏng tốn thời gian nhất.

### Việc phải làm — theo đúng thứ tự

- [ ] **Người dùng:** thử thêm `app.lttstudios.com` như một site trong bảng điều
      khiển Cloudflare, xem gói miễn phí có cho tạo **zone cấp subdomain** không
- [ ] Nếu **được**: lấy 2 nameserver Cloudflare cấp → thêm bản ghi `NS` cho
      `app` tại inet.vn → đợi phân giải → chạy `setup/3-cloudflare.ps1`
- [ ] Nếu **không được**: dừng lại, **đổi quyết định Q22 theo đúng giao thức**
      (`AGENTS.md` mục 6), chọn giữa hai đường còn lại:
      - chuyển cả `lttstudios.com` sang nameserver Cloudflare — phải chép đủ và
        đúng mọi bản ghi hiện có trước khi đổi, sót một bản ghi là trang giới
        thiệu hoặc email công ty chết;
      - bỏ Tunnel, mở cổng 80/443 + Caddy như máy chủ cũ đang chạy — cần DDNS vì
        IP nhà là IP động, và mở cổng vào máy đang chứa token/khoá.

**Tiêu chí hoàn thành:** `https://app.lttstudios.com/health/ready` trả
`{"status":"ready"}` từ **một mạng bên ngoài** (không phải từ trong LAN — kiểm
tra từ trong LAN cho kết quả dương tính giả do hairpin NAT).

**Ghi chú thành thật:** tôi không xác minh được điều kiện gói miễn phí của
Cloudflare từ đây, và đã nói rõ điều đó lúc đưa lựa chọn. Đây là việc 5 phút
trên bảng điều khiển của bạn, và nó quyết định cả nhánh còn lại — nên nó đứng
trước mọi thứ khác, không phải một dòng chú thích.

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

**Phần cần khoá thật của người dùng: để lại đúng cho người có khoá.**

- [ ] **Người dùng:** tạo tài khoản Resend, đặt `RESEND_API_KEY` + `LTT_MAIL_FROM`
      vào `secrets/app.env`, thêm 3 bản ghi DNS (SPF, DKIM, DMARC) tại inet.vn
      → khi đó thư xác thực tới hộp thư thật (giờ đang ghi vào log qua ConsoleMailer)
- [ ] **Người dùng:** tạo widget Turnstile, đặt `TURNSTILE_SITE_KEY` +
      `TURNSTILE_SECRET_KEY` → khi đó form đăng ký có ô chống bot thật

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

- [ ] Đưa `procrastinate` vào (Q13), tạo bảng của nó bằng migration
- [ ] Bảng `jobs` của ứng dụng: id, chủ sở hữu, app, loại job, tham số, trạng
      thái, tiến độ, kết quả, lỗi, thời điểm — **tách khỏi bảng nội bộ của
      procrastinate** để đổi thư viện sau này không phải đổi mô hình nghiệp vụ
- [ ] Dịch vụ Windows `LTTWorker` riêng (Q6), đăng ký bằng NSSM như `LTTWeb`
- [ ] Worker khai báo năng lực (`api` / `ffmpeg` / `gpu`); job chỉ vào worker
      có đủ năng lực — khớp với trường `requires` đã có sẵn trong hợp đồng app
- [ ] Thử lại luỹ thừa; phân biệt lỗi tạm thời (nên thử lại) và lỗi vĩnh viễn
      (đừng thử lại — thử lại một lỗi tham số chỉ tốn tiền API)
- [ ] Cửa sổ chống trùng: cùng một người gửi cùng tham số trong N giây → nhận
      lại job cũ, không tạo job mới
- [ ] Đẩy tiến độ về trình duyệt
- [ ] Job "mồ côi" (worker chết giữa chừng) phải được nhận ra và xử lý

**Tiêu chí hoàn thành**
- Tắt worker giữa lúc chạy → bật lại → job được nhận lại hoặc báo lỗi rõ ràng,
  **không nằm im mãi ở trạng thái "đang chạy"**
- Hai worker cùng chạy → không job nào bị làm hai lần (có test)
- Khởi động lại máy → job đang chờ vẫn còn
- Người dùng A không đọc được job của người dùng B (có test ở tầng route)
- `LTTWeb` restart **không** giết job đang chạy

**Rủi ro lớn nhất:** job bị làm hai lần trên một API tính tiền. Test phải chứng
minh điều này, không được suy luận.

---

## H3 — Sổ credit

**Mục tiêu:** tiền không bao giờ sai. Đây là phần ít code nhất nhưng ít được
phép sai nhất.

- [ ] Bảng sổ **chỉ ghi thêm** (append-only): mọi biến động là một dòng mới.
      Số dư = tổng của sổ, **không bao giờ là một ô được sửa đè**
- [ ] Ba thao tác, tất cả trong **một giao dịch CSDL** cùng với việc tạo job:
      - **giữ chỗ** — khi nhận job, trừ tạm theo giá ước tính
      - **quyết toán** — khi xong, chốt theo giá thật
      - **hoàn lại** — khi lỗi, trả đủ phần đã giữ
- [ ] Từ chối job khi không đủ credit, **trước khi** gọi API tính tiền
- [ ] Chặn mọi đường lách: nút "Tạo lại", gửi lại form, F5 — đều phải qua đúng
      cổng kiểm tra như lần đầu
- [ ] Trang quản trị bằng `sqladmin` (Q15): xem sổ, cấp credit tay, xem lịch sử
- [ ] Admin cấp credit cũng phải ghi vào sổ, kèm ai cấp và vì sao

**Tiêu chí hoàn thành**
- Số dư tính từ sổ **luôn** khớp với tổng các dòng — có test chạy nhiều thao
  tác đồng thời rồi đối chiếu
- Job lỗi → credit được hoàn **đủ**, không thiếu không thừa
- Job chạy hai lần (do thử lại) → **chỉ trừ tiền một lần**
- Không đủ credit → job bị từ chối và **không có lệnh gọi API nào được phát ra**
- Hai request đồng thời của cùng một người không tạo ra số dư âm

**Tham khảo có sẵn:** `app/modules/seedance_video/cost.py` bên `D:\BOT GEMINI`
đã có mô hình giá theo token thật + markup + quy đổi VND + `reserve_check`.
Đọc để học, **viết lại** theo hợp đồng app của dự án này (Q3).

**Lỗi đã có tiền lệ:** BOT GEMINI từng để nút "Tạo lại" đi vòng qua cổng kiểm
tra, cho phép chạy job không mất tiền và xếp hàng vô hạn. Họ đã phải vá
(`P0-5`). Đừng lặp lại — viết test cho đúng đường đó ngay từ đầu.

---

## H4 — Nghiệm thu bằng `apps/demo`

**Mục tiêu:** chứng minh cả chuỗi thông suốt **trước khi** cắm một tool tốn
tiền API vào.

- [ ] Chạy đủ chuỗi: đăng ký → xác thực email → nhận credit dùng thử → tạo job
      → worker nhận → xử lý → trả kết quả → trừ credit đúng → xem lịch sử
- [ ] Hỏng có chủ ý: giết worker giữa chừng → credit phải được hoàn
- [ ] Hỏng có chủ ý: tắt CSDL → giao diện báo lỗi rõ ràng, không trắng trang
- [ ] Hai người dùng chạy song song → không ai thấy dữ liệu của ai
- [ ] Kiểm tra thật bằng trình duyệt, không chỉ bằng test

**Tiêu chí hoàn thành:** cả năm mục trên đã chạy thật và ghi kết quả vào
`NHAT_KY.md`. **Chưa xanh thì không sang H5** — cắm một tool tính tiền vào một
đường ống chưa chứng minh được là cách đắt nhất để phát hiện lỗi.

---

## H5 — Tool thật đầu tiên: `thumbnail_api`

**Mục tiêu:** một tool có người trả tiền, đi qua đúng hợp đồng app.

- [ ] Copy `app/modules/thumbnail_api/` từ `D:\BOT GEMINI` sang — theo danh
      sách "phải mang theo" ở `KHAO_SAT_BOT_GEMINI.md` mục 3
- [ ] Dựng lại thành `apps/thumbnail/` theo hợp đồng app
- [ ] Viết `credit_cost` cho nó
- [ ] Khoá API của nhà cung cấp nằm phía máy chủ, **không bao giờ xuống trình
      duyệt**

**Tiêu chí hoàn thành**
- **Không sửa một dòng nào** trong `platform_core/` hay `server/`. Nếu buộc
  phải sửa → dừng, ghi lại vì sao, bổ sung vào hợp đồng app (đây chính là phép
  thử thật của hợp đồng)
- App tự hiện trên trang chủ và sidebar
- Chạy thật một job, trừ đúng credit
- Quét bí mật 0 finding

---

## H6 — Thanh toán *(chưa chốt cách làm)*

Chỉ bắt đầu khi H5 đã có người dùng thật. Cần chốt trước: cổng thanh toán nào
(VNPAY / MoMo / chuyển khoản có webhook), hoá đơn, hoàn tiền.

Nguyên tắc bắt buộc từ bây giờ: **mọi thứ liên quan tiền đi qua sổ credit ở
H3**, không bao giờ có đường tắt riêng cho thanh toán.

---

## H7 — File lớn (R2) *(chưa chốt)*

Bắt buộc trước khi làm bất kỳ tool nào thuộc nhóm FFmpeg hoặc GPU
(`auto_sub_video`, `concat_pro`, `cut_clip_short`, `video_upscale`).

- Trình duyệt upload **thẳng** lên R2, không đi qua máy chủ — trần 100 MB của
  Cloudflare nằm ở đường qua máy chủ
- Thêm backend R2 vào `platform_core/storage.py`, **không sửa app nào**
- Kiểm duyệt file người lạ tải lên trước khi đưa vào FFmpeg — file media dị
  dạng là đường thực thi mã có thật

---

## H8 — Thêm tool

Theo thứ tự khuyến nghị trong `KHAO_SAT_BOT_GEMINI.md`:

1. `youtube_script` (139 dòng — rẻ nhất để kiểm chứng lại hợp đồng app)
2. `seedance_video` (5.508 dòng — giá trị thương mại cao nhất; cần H7)
3. `plenx` (2.731 dòng — cùng cấu trúc, port chung một lượt)
4. Nhóm FFmpeg / GPU (cần H7)

**Không đưa lên nền tảng:** mọi module dùng cookie hoặc trình duyệt
(`whisk_nano` và 16 module đã archive). Lý do đầy đủ ở `KHAO_SAT_BOT_GEMINI.md`
nhóm D.

---

## Việc phải làm ngay ở phiên tiếp theo

1. **Người dùng — H0.1:** kiểm tra trên bảng điều khiển Cloudflare xem gói miễn
   phí có cho tạo zone cấp subdomain `app.lttstudios.com` không. Việc 5 phút,
   nhưng nó quyết định cả nhánh đường ra Internet. **Chưa biết kết quả thì chưa
   chạy `setup/3-cloudflare.ps1`.**
2. **H1.1** — dựng PostgreSQL + SQLAlchemy + Alembic, migration đầu tiên. Việc
   này **không phụ thuộc** H0.1, làm song song được.
3. Bổ sung bước cài Postgres vào `setup/2-cai-dat.ps1` và bước `pg_dump` vào
   `backup.ps1` **trong cùng lần đó** — thêm CSDL mà quên sao lưu là một sự cố
   đang chờ xảy ra.
