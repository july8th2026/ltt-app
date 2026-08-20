# N3.2 — dựng máy thử nghiệm để đo, và vì sao KHÔNG dùng RDP

> Lập 2026-08-20. Đi kèm `N3_2_ENGINE.md` (bảy câu V1–V7 phải trả lời trên máy thật).

---

## 1. Vì sao SSH chứ không phải RDP + chụp màn hình

Phiên trước dùng **computer-use + RDP** và gặp đúng ba vấn đề của cách đó:

- nó chụp ảnh **màn hình máy chủ sản phẩm**, RDP chỉ là một cửa sổ trên đó — nên
  **phím gõ lọt sang cửa sổ khác** (đã thật sự xảy ra: phím lọt vào một ứng dụng
  production đang mở);
- đọc chữ trong ảnh chậm và hay sai;
- mỗi thao tác mất một vòng chụp-nhìn-bấm.

Nhưng bản chất V1–V5 là **"chạy lệnh, đọc kết quả"** — đó là việc của một kênh
**văn bản**, không phải của ảnh. Nên:

| Việc | Kênh đúng |
|---|---|
| V1–V5 (cấu hình, mật khẩu, ID, credential), cài đặt, bắt gói | **SSH** |
| V6 / T10 (bắt gói tại relay rồi soi payload) | **SSH** + `pktmon`/Wireshark CLI |
| V7 (nhìn chỉ báo phiên, nhìn cửa sổ RustDesk) | **chụp NGAY TRÊN VM** rồi `scp` file PNG về |
| Bấm nút trong GUI khi không có đường lệnh | RDP — **chỉ khi hết cách** |

Chụp-trên-VM tốt hơn hẳn chụp-qua-RDP: ảnh đúng độ phân giải của VM, không có
cửa sổ RDP chen vào, và **không có đường nào để phím lọt sang máy khác**.

## 2. Chạy trên MỖI VPS — một lần, cần quyền Administrator

Mở PowerShell **as Administrator** trên VPS rồi dán nguyên khối:

> ⚠️ **Bản đầu của khối này SAI và đã sửa 2026-08-20.** Nó dùng
> `Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0`, nhưng **Windows
> Server 2016 không có OpenSSH dạng Windows Capability** — đường đó chỉ có từ
> **Server 2019 / Windows 10 1809** trở lên. Trên 2016 nó không cài gì cả, rồi
> mọi lệnh sau đổ theo vì `sshd` không tồn tại. Khối dưới đây tải thẳng bản
> OpenSSH **chính thức của Microsoft** nên chạy được trên **mọi** phiên bản.

```powershell
# ===== N3.2: cai OpenSSH Server. Chay AS ADMINISTRATOR. =====
Set-ExecutionPolicy Bypass -Scope Process -Force
# Server 2016 mac dinh TLS 1.0/1.1 -> moi tai HTTPS deu chet neu khong bat 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
"OS: " + (Get-CimInstance Win32_OperatingSystem).Caption

# 1. Tai ban OpenSSH chinh thuc moi nhat (khong ghim phien ban -> khong doan sai)
$rel = (Invoke-RestMethod 'https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases')[0]
$url = ($rel.assets | Where-Object { $_.name -eq 'OpenSSH-Win64.zip' }).browser_download_url
"Tai $($rel.tag_name): $url"
Invoke-WebRequest $url -OutFile "$env:TEMP\OpenSSH-Win64.zip" -UseBasicParsing

# 2. Giai nen + dang ky dich vu
Expand-Archive "$env:TEMP\OpenSSH-Win64.zip" -DestinationPath 'C:\Program Files' -Force
& 'C:\Program Files\OpenSSH-Win64\install-sshd.ps1'
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd

# 3. Firewall — xoa luat cu truoc de chay lai duoc nhieu lan
Remove-NetFirewallRule -Name sshd -ErrorAction SilentlyContinue
New-NetFirewallRule -Name sshd -DisplayName "OpenSSH Server (sshd)" `
  -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null

# 4. Khoa cong khai cua Claude.
#    `-Encoding ascii` co chu y: authorized_keys CO BOM thi sshd tu choi khoa
#    va bao "permission denied" — dung cai bay BOM ma CLAUDE.md muc 1 canh bao.
if (-not (Test-Path "C:\ProgramData\ssh")) {
  New-Item -ItemType Directory "C:\ProgramData\ssh" -Force | Out-Null }
$f = "C:\ProgramData\ssh\administrators_authorized_keys"
$key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILMYu0kb2vrbAaHMvXMqVmxENs9OeKTbVJjVzZggT4Pg claude-nexus-test"
Set-Content -Path $f -Value $key -Encoding ascii
icacls $f /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"

# 5. PowerShell lam shell mac dinh (ban zip khong tu tao khoa registry nay)
if (-not (Test-Path "HKLM:\SOFTWARE\OpenSSH")) {
  New-Item -Path "HKLM:\SOFTWARE\OpenSSH" -Force | Out-Null }
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
  -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
  -PropertyType String -Force | Out-Null

Restart-Service sshd
"===== XONG ====="
Get-Service sshd | Format-Table Name,Status,StartType -AutoSize
"IP cong khai: " + (Invoke-WebRequest 'https://api.ipify.org' -UseBasicParsing).Content
```

Kỳ vọng thấy `sshd  Running  Automatic` và một địa chỉ IP. Nếu bước 1 chết vì
GitHub API, tải tay `OpenSSH-Win64.zip` từ
<https://github.com/PowerShell/Win32-OpenSSH/releases> rồi chạy tiếp từ bước 2.

Khối này chạy trên **cả hai** máy ở §4: VM Proxmox (máy vứt đi) và VPS gateway
`45.76.185.75` (**không** phải máy vứt đi — xem §6). Tôi không cần mật khẩu.

**Lưu ý về khoá:** đây là khoá **dùng riêng cho thử nghiệm**, cất ở thư mục tạm
của phiên làm việc, **không** vào repo. Đừng dùng lại nó cho máy thật.

## 3. Đã chốt 2026-08-20: máy đích là VM Proxmox, tỉ lệ đo sau

Chủ sản phẩm chọn: **máy đích = một VM Windows trên Proxmox**, và **hoãn** phép
đo tỉ lệ direct/relay.

**Vì sao KHÔNG cài lên máy production:** máy phát triển cũng chính là máy chủ —
`C:\LTTPlatform` tồn tại, `LTTStudioWeb`/`Worker`/`Codex` và `cloudflared` đều
đang Running, tức `app.lttstudios.com` đang phục vụ khách thật. Đặt một engine
điều khiển từ xa **có mật khẩu thường trực** lên đúng cái máy giữ secrets, CSDL
khách và tunnel — trong lúc bài test còn xoay mật khẩu và ép relay — là dựng ra
đúng thứ mà `04_THREAT_MODEL.md` T1 cảnh báo. VM cho ta **vị trí mạng và desktop
thật** mà không đụng vào production.

**Một hệ quả phải ghi lại, kẻo sau này hiểu nhầm:** VM Proxmox đi Internet **qua
chính VPS gateway** (`10.50.0.0/16` → `45.76.185.75`), mà đó cũng là máy chạy
relay. Nên VM đó thoát ra bằng IP của VPS — **nó không bao giờ cho được tỉ lệ
NAT-nhà thật**, kể cả sau này. Đừng ai lấy VM này đo tỉ lệ rồi tưởng đã xong.

### Đo được gì với cấu hình đã chốt

| Số | VM Proxmox + VPS |
|---|---|
| **T10 — relay có đọc được nội dung màn hình không** | ✅ đo được — phải **ép relay** nên topology không liên quan. **Quan trọng nhất** |
| **V1–V7** (cấu hình, mật khẩu, ID, chỉ báo phiên) | ✅ đo được hết — chỉ cần desktop Windows thật |
| **GB/giờ khi qua relay** | ✅ đo được (ép relay) |
| **Tỉ lệ direct / relay thật** | ⬜ **HOÃN có chủ ý** — cần NAT↔NAT thật (máy sau router nhà + điện thoại 4G/CGNAT). Ghi vào R3 là còn nợ |

## 4. Cần bạn dựng — hai máy, cùng một khối lệnh

**(a) VM Windows trên Proxmox** — máy đích. Dựng xong, chạy khối PowerShell ở §2
**as Administrator** trong VM.

**(b) VPS gateway `45.76.185.75`** — chạy **cùng khối lệnh §2** trên nó. Hai lý
do: tôi cần kiểm `hbbs`/`hbbr` bằng lệnh thay vì RDP, và tôi cần **tự thêm port
forward** cho VM thay vì nhờ bạn mỗi lần.

**(c) Mở một cổng vào VM.** Trên VPS, forward một cổng công khai vào SSH của VM
(thay `<IP-VM>` bằng IP `10.50.x.x` của VM):

```powershell
netsh interface portproxy add v4tov4 listenport=2222 listenaddress=0.0.0.0 `
  connectport=22 connectaddress=<IP-VM>
New-NetFirewallRule -Name ssh-vm -DisplayName "SSH to test VM" `
  -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 2222
```

Xong ba bước, đưa tôi **IP `10.50.x.x` của VM**. Tôi vào bằng
`ssh -p 2222 administrator@45.76.185.75` và tự làm tiếp — không cần mật khẩu.

**Ghi chú bảo mật:** VPS đang mở RDP 3389 ra Internet, rủi ro hơn SSH khoá nhiều.
Sau khi SSH chạy, nên **giới hạn 3389 theo IP nguồn** hoặc đóng hẳn. Và mật khẩu
VPS đã lộ trong phiên làm việc trước — vẫn cần đổi.

## 5. Sau khi có IP, tôi làm theo thứ tự

1. Kiểm SSH vào được cả hai, ghi lại phiên bản Windows.
2. Tải RustDesk **nguyên bản** (Q97 — không sửa, không dùng custom client
   generator) lên cả hai.
3. **V1**: tìm đường nạp cấu hình server (`45.76.185.75` + khoá công khai của
   Q96) vào client nguyên bản **không sửa binary**. Nếu đường duy nhất là build
   lại client thì **dừng và báo** — đó là Rổ 2, phải quay lại Q97.
4. **V2–V4**: đặt/xoay mật khẩu không giám sát bằng lệnh; bên điều khiển kết nối
   không tương tác.
5. **V5**: RustDesk ID có ổn định không, map vào `nexus_devices` thế nào.
6. **V6/T10**: ép relay, bắt gói tại hbbr trên `45.76.185.75`, soi payload.
7. **V7**: chụp màn hình trên VM, xác nhận chỉ báo phiên đủ mạnh cho ràng buộc 7.
8. Ghi kết quả vào `N3_2_ENGINE.md` §3 — **thay giả thuyết bằng sự thật đo được**.

## 6. Dọn sau khi xong — và một thứ TUYỆT ĐỐI không xoá

**Xoá được:** VM Windows trên Proxmox (máy vứt đi), và cặp khoá thử trong thư
mục tạm.

⚠️ **KHÔNG xoá VPS `45.76.185.75`.** Nó là **NAT gateway cho toàn bộ VM Proxmox**
(Q96) — xoá nó là sập cả mạng VM, không chỉ Nexus. Trên VPS chỉ dọn đúng ba thứ
đã thêm cho bài test:

```powershell
netsh interface portproxy delete v4tov4 listenport=2222 listenaddress=0.0.0.0
Remove-NetFirewallRule -Name ssh-vm
# Va go khoa thu khoi C:\ProgramData\sshdministrators_authorized_keys
```

Giữ hay gỡ `sshd` trên VPS là tuỳ bạn — nhưng nếu giữ thì **nên giữ**, vì SSH
khoá an toàn hơn RDP mật khẩu đang mở ra Internet nhiều.

**Không** để khoá thử này còn hiệu lực ở bất kỳ máy nào sống tiếp.
