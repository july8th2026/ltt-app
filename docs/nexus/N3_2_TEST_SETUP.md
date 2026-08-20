# N3.2 — dựng 2 VPS thử nghiệm để đo, và vì sao KHÔNG dùng RDP

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

```powershell
# 1. Bat OpenSSH Server (co san trong Windows, khong phai tai them)
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd

# 2. Mo firewall cho SSH
New-NetFirewallRule -Name sshd -DisplayName "OpenSSH Server (sshd)" `
  -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22

# 3. Cai khoa cong khai cua Claude (KHONG can mat khau sau buoc nay)
$key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILMYu0kb2vrbAaHMvXMqVmxENs9OeKTbVJjVzZggT4Pg claude-nexus-test"
$f = "C:\ProgramData\ssh\administrators_authorized_keys"
Add-Content -Path $f -Value $key
icacls $f /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"

# 4. PowerShell lam shell mac dinh (de lenh chay dung cu phap)
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
  -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
  -PropertyType String -Force

Restart-Service sshd
"XONG. IP may nay:"; (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content
```

Xong bước này, đưa tôi **hai địa chỉ IP**. Tôi không cần mật khẩu.

**Lưu ý về khoá:** đây là khoá **dùng riêng cho thử nghiệm**, cất ở thư mục tạm
của phiên làm việc, **không** vào repo. Hai VPS này là máy vứt đi nên khoá cũng
vứt theo; đừng dùng lại nó cho máy thật.

## 3. Hai VPS này đo được gì — và KHÔNG đo được gì

Nói trước để không ai tưởng đã đo xong:

| Số | 2 VPS public IP |
|---|---|
| **T10 — relay có đọc được nội dung màn hình không** | ✅ đo được (ép relay + bắt gói). **Quan trọng nhất** |
| **GB/giờ khi qua relay** | ✅ đo chính xác (ép `ALWAYS_USE_RELAY`) |
| **Độ trễ direct vs relay** | ✅ đo được (direct hơi lạc quan vì không qua NAT) |
| **V1–V7** (cấu hình/credential/chỉ báo) | ✅ đo được hết |
| **Tỉ lệ direct / relay THẬT** | ❌ **không đại diện** |

Lý do dòng cuối: VPS có **IP công khai trực tiếp, không sau NAT**, nên xuyên NAT
luôn thành công → sẽ ra ~100% direct. Khách thật ngồi sau router nhà hoặc CGNAT
thì hoàn toàn khác. Tỉ lệ đó chỉ đo được bằng **máy sau NAT thật** (một máy mạng
nhà + một điện thoại phát 4G là cặp rẻ nhất).

Nghĩa là 2 VPS đóng **3/4 con số của R3 + toàn bộ V1–V7**; còn đúng một con số
phải chờ hai mạng dân dụng.

## 4. Sau khi có IP, tôi làm theo thứ tự

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

## 5. Dọn sau khi xong

Hai VPS là máy vứt đi. Khi đo xong: xoá VPS, xoá cặp khoá thử trong thư mục tạm.
**Không** để khoá thử này còn hiệu lực ở bất kỳ máy nào sống tiếp.
