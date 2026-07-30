# Triển khai lên VPS Windows Server 2016

> Quy trình cụ thể cho Server 2016. Nếu VPS của bạn là 2019/2022, dùng
> `docs/DEPLOY_APP_LTTSTUDIOS.md` thay vì file này — 2019+ cài OpenSSH
> bằng một dòng lệnh, không cần bước tải từ GitHub.
>
> **Không có giá trị bí mật nào trong file này.**

## Cần biết trước

| Điểm | Chi tiết |
|---|---|
| **Hết hỗ trợ bảo mật** | **12/01/2027.** Sau mốc này Microsoft ngừng vá lỗi. Nên lên kế hoạch nâng cấp trước thời điểm đó. |
| **OpenSSH** | Server 2016 **không có** gói OpenSSH trong Windows. Phải tải từ GitHub — script `bootstrap-server2016.ps1` lo việc này. |
| **Python** | Dùng **3.12**, không dùng 3.13. Server 2016 chạy nhân Windows 10 build 1607; 3.12 là dòng cuối được kiểm thử kỹ trên đó. App yêu cầu 3.10+ nên 3.12 dư dùng. |
| **PowerShell** | 5.1 có sẵn ✅ — mọi script deploy chạy được. |
| **TLS** | Server 2016 mặc định dùng TLS 1.0 khi tải file, GitHub và python.org đều từ chối. Script đã ép TLS 1.2. |

---

## Bước 1 — Cài đặt OS trên VPS

Trong bảng điều khiển nhà cung cấp (Vultr/…), chọn **Reinstall / Rebuild**
với **Windows Server 2016**.

> ⚠️ Thao tác này **xoá sạch** mọi thứ trên VPS. Nếu đang có dữ liệu, sao
> lưu trước.

Ghi lại: **IP công khai** và **mật khẩu Administrator** do nhà cung cấp
sinh ra.

---

## Bước 2 — Chuẩn bị máy chủ (một lần duy nhất)

Vào VPS bằng **RDP**, mở **PowerShell với quyền Administrator**.

Script `bootstrap-server2016.ps1` làm hết: ép TLS 1.2, cài Python 3.12,
tải và cài OpenSSH từ GitHub, mở tường lửa cổng 22, đặt PowerShell làm
shell mặc định cho SSH, và nạp khoá công khai.

Cách đưa script lên VPS — chọn một trong hai:

**Cách A — Dán trực tiếp.** Mở Notepad trên VPS, dán toàn bộ nội dung
`deploy/windows/bootstrap-server2016.ps1`, lưu thành
`C:\bootstrap.ps1`.

**Cách B — Copy qua RDP.** Bật chia sẻ ổ đĩa trong Remote Desktop
(Show Options → Local Resources → More → tick ổ chứa file), rồi copy
sang.

Sau đó chạy:

```powershell
powershell -ExecutionPolicy Bypass -File C:\bootstrap.ps1 -PublicKey "<khoá công khai>"
```

Khoá công khai sẽ do Claude cung cấp — nó **không phải bí mật**, dán
thoải mái.

Script tự kiểm tra từng bước và in ra `[OK]` hoặc `[!]`. Chạy lại nhiều
lần vô hại.

Cuối cùng nó in ra IP của máy — **gửi IP + username cho Claude** để tiếp
tục.

---

## Bước 3 — Claude cài ứng dụng qua SSH

Từ đây trở đi Claude làm, bạn chỉ theo dõi:

1. Copy file release (`ltt-release-<version>.zip`) lên VPS, kiểm tra SHA-256
2. Cài NSSM + Caddy
3. Chạy `install.ps1` → tạo `C:\LTTPlatform\` + venv + service
4. Sinh `LTT_SESSION_SECRET` và `LTT_TOKEN_ENCRYPTION_KEY` **ngay trên VPS**
5. Khởi động service, kiểm tra `/health/ready`

---

## Bước 4 — Mật khẩu admin (bạn tự làm)

Claude không đặt mật khẩu này — bạn phải là người duy nhất biết. Trong RDP:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Temp\set-admin-password.ps1
```

Hỏi mật khẩu 2 lần (không hiện ra màn hình), băm bằng PBKDF2 rồi ghi hash
vào `app.env`. **Mật khẩu gốc không được lưu ở đâu** — quên thì chạy lại
script để đặt mới.

---

## Bước 5 — DNS

VPS có **IP tĩnh**, nên không cần DDNS. Chỉ cần một bản ghi:

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `app` | `<IP công khai của VPS>` | 300 |

Tạo tại nơi quản lý DNS của `lttstudios.com` (inet.vn).

Kiểm tra:
```powershell
nslookup app.lttstudios.com
```
Phải trả đúng IP VPS **trước khi** sang bước sau — Caddy không xin được
chứng chỉ HTTPS nếu DNS chưa trỏ đúng.

---

## Bước 6 — Tường lửa

```powershell
New-NetFirewallRule -DisplayName "HTTP"  -Direction Inbound -Protocol TCP -LocalPort 80  -Action Allow
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

Cổng 80 **bắt buộc** phải mở — Let's Encrypt dùng nó để xác thực quyền sở
hữu domain.

**Không** mở cổng 8000: ứng dụng chỉ lắng nghe `127.0.0.1`, Caddy là mặt
tiền duy nhất.

Nếu nhà cung cấp có tường lửa riêng (Vultr Firewall), mở tương ứng ở đó.

---

## Bước 7 — HTTPS + chuyển sang production

Claude sẽ:
1. Đổi Caddyfile sang `app.lttstudios.com`, Caddy tự xin chứng chỉ
2. Chuyển `LTT_ENV=production` — cookie bắt buộc HTTPS, `/docs` bị chặn
3. Khởi động lại và kiểm tra

Xong bước này, `https://app.lttstudios.com` vào được dashboard.

---

## Bước 8 — Kết nối tài khoản Facebook / TikTok

Token cũ **không dùng lại được** trên VPS (chúng mã hoá theo danh tính máy
cũ — xem `docs/AUDIT_REPORT.md` B1/B2). Phải kết nối lại trên VPS.

Vì `LTT_TOKEN_ENCRYPTION_KEY` đã đặt ở Bước 3, token lưu **từ giờ trở đi**
sẽ dùng lại được sau khi cài lại máy hoặc chuyển server — miễn là giữ
nguyên khoá đó. **Sao lưu khoá này ở nơi an toàn.**

---

## Kiểm tra cuối

```powershell
cd C:\LTTPlatform\app
..\venv\Scripts\python.exe tools\doctor.py --check-sheet
```

- [ ] `https://app.lttstudios.com` hiện trang đăng nhập, có khoá HTTPS
- [ ] Đăng nhập được
- [ ] `/status` hiện báo cáo sức khoẻ
- [ ] `/docs` trả **404**
- [ ] `http://<IP-VPS>:8000` **không** vào được từ ngoài
- [ ] Khởi động lại VPS → service tự chạy, không cần đăng nhập RDP
- [ ] `doctor.py` báo không còn lỗi chặn

---

## Vận hành

| Việc | Lệnh |
|---|---|
| Cập nhật phiên bản | `.\update.ps1 -SourceZip <file.zip>` |
| Quay lui khi lỗi | `.\rollback.ps1` |
| Sao lưu | `.\backup.ps1` |
| Diễn tập phục hồi | `.\restore.ps1 -Archive <file.zip>` |
| Phục hồi thật | `.\restore.ps1 -Archive <file.zip> -Live` |
| Chẩn đoán | `..\venv\Scripts\python.exe tools\doctor.py` |

## Sự cố thường gặp trên 2016

| Triệu chứng | Nguyên nhân |
|---|---|
| Tải file báo "connection closed" | TLS 1.0 — chạy `[Net.ServicePointManager]::SecurityProtocol = 'Tls12'` trước |
| `Add-WindowsCapability` không nhận lệnh | Bình thường trên 2016 — dùng `bootstrap-server2016.ps1` |
| SSH vào lại ra `cmd.exe` | Chưa đặt `DefaultShell` trong registry |
| SSH báo `Permission denied (publickey)` | Sai file (phải là `administrators_authorized_keys`) hoặc quyền file quá rộng — chạy lại phần `icacls` |
| Caddy không xin được chứng chỉ | DNS chưa trỏ đúng, hoặc cổng 80 chưa mở |
