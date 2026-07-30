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
đoạn PowerShell bằng chuỗi Python không phải raw-string, `in` thành `in`
và `pp.env` thành `pp.env`. Năm chỗ, hai file.

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
