# Triển khai `app.lttstudios.com`

> Runbook để đưa dashboard lên domain công khai (P9/P10).
> **Không có giá trị bí mật nào trong file này.**

## Tại sao cần VPS riêng

`lttstudios.com` hiện nằm trên hosting WordPress của inet.vn (DirectAdmin —
xem `docs/lttstudios-deploy-inet-vn.md`). Hosting đó **chỉ chạy được web
tĩnh/PHP, không chạy được ứng dụng Python thường trú**. Dashboard là một
tiến trình FastAPI chạy liên tục, nên `app.lttstudios.com` phải trỏ về một
**VPS Windows riêng**, không phải hosting hiện tại.

`lttstudios.com` giữ nguyên như cũ (không đụng tới).

---

## Những gì đã sẵn sàng

| Thành phần | Trạng thái |
|---|---|
| Ứng dụng web (dashboard, đăng nhập, worker control) | ✅ Đã xong, đã kiểm chứng |
| Gói script triển khai | ✅ `deploy/windows/` |
| Build release artifact | ✅ `python tools/build_release.py` |
| Diễn tập cài sạch (venv riêng, chế độ production) | ✅ Đã chạy thành công |
| Cấu hình Caddy mẫu | ✅ `deploy/windows/Caddyfile.example` |
| Chẩn đoán sức khoẻ | ✅ `python tools/doctor.py` |

## Những gì **bạn** phải làm (tôi không có quyền truy cập)

Tôi không có IP VPS, tài khoản quản trị, hay quyền quản lý DNS, nên các
bước dưới đây phải do bạn thực hiện. Mỗi bước đều có lệnh kiểm chứng.

---

## Bước 0 — Chuẩn bị (trên máy dev này)

```bash
cd "BOT UP Facebook"
python -m pytest tests -q          # phải PASS
python tools/build_release.py      # tạo dist/ltt-release-<version>.zip
```

Ghi lại SHA-256 mà lệnh build in ra — dùng để đối chiếu sau khi upload.

---

## Bước 1 — Chuẩn bị VPS Windows

Yêu cầu tối thiểu: Windows Server 2019+, 2 vCPU, 4 GB RAM, 60 GB đĩa,
IPv4 tĩnh.

1. Cài **Python 3.11+** (tick "Add python.exe to PATH").
2. Cài **NSSM** (để chạy app như Windows Service):
   `choco install nssm` hoặc tải từ https://nssm.cc
3. Cài **Caddy**: `choco install caddy` hoặc tải từ https://caddyserver.com

Kiểm chứng:
```powershell
python --version ; nssm version ; caddy version
```

---

## Bước 2 — DNS

Tại nơi quản lý DNS của `lttstudios.com`, thêm bản ghi:

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `app` | `<IP-công-khai-của-VPS>` | 300 |

Kiểm chứng (đợi DNS lan truyền, thường 5–30 phút):
```powershell
nslookup app.lttstudios.com
```
Phải trả về đúng IP VPS thì mới sang bước sau — Caddy **không xin được
chứng chỉ HTTPS** nếu DNS chưa trỏ đúng.

---

## Bước 3 — Firewall

Mở **80** và **443** (cổng 80 bắt buộc để Let's Encrypt xác thực):

```powershell
New-NetFirewallRule -DisplayName "HTTP"  -Direction Inbound -Protocol TCP -LocalPort 80  -Action Allow
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

**Không** mở cổng 8000 ra ngoài — ứng dụng chỉ lắng nghe `127.0.0.1`.
Giới hạn RDP về IP quản trị của bạn nếu VPS có mở RDP.

Nếu dùng Vultr/nhà cung cấp có firewall riêng, mở tương ứng ở đó nữa.

---

## Bước 4 — Cài ứng dụng

Copy file `ltt-release-<version>.zip` lên VPS (ví dụ `C:\Temp\`), rồi:

```powershell
cd C:\Temp
Expand-Archive ltt-release-<version>.zip -DestinationPath C:\Temp\rel
cd C:\Temp\rel\deploy\windows
.\install.ps1 -SourceZip C:\Temp\ltt-release-<version>.zip
```

Script tạo cấu trúc:
```
C:\LTTPlatform\
  app\        <- mã nguồn (bị thay khi update)
  data\       <- config, token, database  (KHÔNG bị thay khi update)
  secrets\    <- app.env, ACL đã siết
  logs\
  backups\
  venv\
```

---

## Bước 5 — Điền secret

Sinh các giá trị (chạy trên VPS):

```powershell
# Session secret
python -c "import secrets;print(secrets.token_urlsafe(32))"

# Khoá mã hoá token — LƯU GIỮ VĨNH VIỄN, mất là mất hết token (ADR-013)
python -c "import secrets;print(secrets.token_urlsafe(32))"

# Hash mật khẩu admin (nhập mật khẩu, không hiện ra màn hình)
cd C:\LTTPlatform\app
..\venv\Scripts\python.exe tools\hash_admin_password.py
```

Mở `C:\LTTPlatform\secrets\app.env`, điền vào:
`LTT_SESSION_SECRET`, `LTT_TOKEN_ENCRYPTION_KEY`, `LTT_ADMIN_PASSWORD_HASH`.

> ⚠️ Đừng bao giờ commit hay gửi file này qua chat/email.

Nạp vào service rồi khởi động:
```powershell
cd C:\Temp\rel\deploy\windows
.\set-service-env.ps1
Start-Service LTTStudioWeb
```

Kiểm chứng **cục bộ trước khi mở ra ngoài**:
```powershell
curl http://127.0.0.1:8000/health/ready
# mong đợi: {"status":"ready","environment":"production"}
```

---

## Bước 6 — Caddy (HTTPS)

```powershell
mkdir C:\LTTPlatform\caddy
copy C:\Temp\rel\deploy\windows\Caddyfile.example C:\LTTPlatform\caddy\Caddyfile
notepad C:\LTTPlatform\caddy\Caddyfile     # sửa dòng email
```

Chạy Caddy như service:
```powershell
nssm install Caddy "C:\ProgramData\chocolatey\bin\caddy.exe" "run --config C:\LTTPlatform\caddy\Caddyfile"
nssm set Caddy Start SERVICE_AUTO_START
Start-Service Caddy
```

Kiểm chứng — **đây là lúc `app.lttstudios.com` bắt đầu chạy được**:
```powershell
curl https://app.lttstudios.com/health/ready
```

Mở trình duyệt vào `https://app.lttstudios.com` → hiện trang đăng nhập.

---

## Bước 7 — Kiểm tra sau triển khai

```powershell
cd C:\LTTPlatform\app
..\venv\Scripts\python.exe tools\doctor.py
```

Danh sách phải rà:

- [ ] `https://app.lttstudios.com` hiện trang đăng nhập, có khoá HTTPS hợp lệ
- [ ] Đăng nhập được bằng tài khoản admin đã tạo
- [ ] `/status` hiển thị báo cáo sức khoẻ
- [ ] `https://app.lttstudios.com/docs` trả **404** (docs bị chặn ở production)
- [ ] Truy cập trực tiếp `http://<IP-VPS>:8000` **không** vào được từ ngoài
- [ ] Khởi động lại VPS → service tự chạy lại, không cần đăng nhập RDP
- [ ] Kết nối lại tài khoản Facebook/TikTok (xem mục dưới)

---

## Bước 8 — Tài khoản Facebook / TikTok

Token hiện tại **không dùng lại được trên VPS** — chúng được mã hoá theo
danh tính máy cũ (xem `docs/_luutru/AUDIT_REPORT.md` B1/B2). Trên VPS bạn phải
kết nối lại tài khoản.

Vì `LTT_TOKEN_ENCRYPTION_KEY` đã được đặt ở Bước 5, các token lưu **từ
giờ trở đi** sẽ dùng lại được sau khi cài lại VPS — miễn là bạn giữ
nguyên khoá đó.

Hiện việc kết nối tài khoản vẫn thực hiện trên **app desktop**; OAuth từ
trình duyệt là hạng mục kế tiếp chưa làm.

---

## Cập nhật phiên bản sau này

```powershell
cd C:\Temp\rel\deploy\windows
.\update.ps1 -SourceZip C:\Temp\ltt-release-<version-mới>.zip
```

Script tự: sao lưu dữ liệu → dừng service → giữ bản cũ ở `app.previous`
→ giải nén bản mới → cài lại thư viện → khởi động → kiểm tra health.
Nếu health fail, nó báo và bạn chạy:

```powershell
.\rollback.ps1
```

Dữ liệu **không** bị lùi khi rollback (lùi database sẽ mất lịch sử đăng
bài thật). Muốn lùi cả dữ liệu thì chạy `restore.ps1 -Live` một cách có
chủ ý.

---

## Sao lưu

```powershell
.\backup.ps1                          # thủ công
.\restore.ps1 -Archive <file.zip>     # DIỄN TẬP — không đụng dữ liệu thật
.\restore.ps1 -Archive <file.zip> -Live   # phục hồi thật, có xác nhận
```

Đặt lịch chạy hằng ngày:
```powershell
$a = New-ScheduledTaskAction -Execute 'powershell.exe' `
     -Argument '-File C:\Temp\rel\deploy\windows\backup.ps1'
$t = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName 'LTT Backup' -Action $a -Trigger $t -RunLevel Highest
```

---

## Quan trọng: desktop và VPS không được chạy cùng lúc

`WorkerApplication` giữ khoá theo tài khoản để chặn đăng trùng, nhưng khoá
đó là **file trên từng máy** — nó không nhìn thấy nhau qua mạng.

→ Khi VPS bắt đầu chạy worker, **tắt worker trên máy desktop** (app vẫn mở
được để quản lý tài khoản). Chạy song song cùng một Page/tab sheet sẽ gây
đăng trùng bài.

Đây là giới hạn đã biết của kiến trúc release 1 (ADR-005: một orchestrator
duy nhất). Khoá phân tán chỉ cần khi có nhiều worker thật sự.

---

## Khi gặp sự cố

| Triệu chứng | Kiểm tra |
|---|---|
| Caddy không xin được chứng chỉ | DNS đã trỏ đúng chưa (`nslookup`), cổng 80 đã mở chưa |
| Service không khởi động | `C:\LTTPlatform\logs\service-err.log` |
| `/health/ready` trả 503 | config chưa hợp lệ — chạy `tools\doctor.py` |
| Đăng nhập không được | `LTT_ADMIN_PASSWORD_HASH` chưa nạp — chạy lại `set-service-env.ps1` rồi `Restart-Service` |
| Bot không đăng được bài | `tools\doctor.py` — gần như luôn là token hoặc mapping cột sheet |
