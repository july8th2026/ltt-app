# Cloudflare Tunnel

Tunnel tạo một đường từ Internet vào máy chủ mà **không cần mở cổng và không
cần IP tĩnh**. `cloudflared` chạy trên máy chủ, tự gọi ra Cloudflare và giữ
kết nối; Cloudflare đẩy request qua đường đó.

---

## Ba giới hạn phải biết TRƯỚC khi xây app

Không phải để can bạn — bạn đã quyết dùng Tunnel. Nhưng ba con số này quyết
định **cách viết app**, nên biết trước rẻ hơn biết sau rất nhiều.

| Giới hạn | Free / Pro | Business | Enterprise |
|---|---|---|---|
| Kích thước request body (**upload**) | **100 MB** | 200 MB | 500 MB |
| Thời gian chờ phản hồi | **100 giây** | 100 s | tới 600 s |
| Serve video/file lớn không host trên Cloudflare | hạn chế theo ToS | | |

### Nghĩa là gì trong thực tế

**Giới hạn 100 MB chỉ áp dụng cho chiều UPLOAD.** Người dùng gửi file 500 MB
lên sẽ nhận HTTP 413 **trước khi** tới máy chủ. Tải file lớn **xuống** thì
không bị giới hạn này.

**Giới hạn 100 giây áp dụng cho việc chờ phản hồi.** Job render 3 phút sẽ
nhận lỗi 524 dù bot vẫn đang chạy tốt. Vì vậy **mọi việc dài hơn vài giây
phải đi qua hàng đợi job**, không được làm đồng bộ trong một request. Đây
không phải lựa chọn thiết kế, mà là bắt buộc.

**Mọi lượt tải file đều ăn băng thông upload của máy chủ.** 10 người tải cùng
một video 200 MB là đường truyền phải đẩy 2 GB. Cloudflare không cache file
lớn từ origin ngoài nên không có gì đỡ.

### Khi nào phải đổi cách

Khi app xử lý file vượt 100 MB, hoặc khi số lượt tải làm nghẽn đường truyền.
Lúc đó chuyển file sang object storage (Cloudflare R2) và cho trình duyệt
upload/tải **trực tiếp**, không đi qua máy chủ.

`platform_core/storage.py` đã tách sẵn cho việc này — chỉ cần thêm một
backend, **không phải sửa app nào**. Chi phí R2 tại thời điểm viết: 0,015
USD/GB-tháng lưu trữ, **egress miễn phí**, và hạn mức miễn phí 10 GB.

---

## ⚠️ Điều kiện tiên quyết — uỷ quyền subdomain (quyết định Q22)

DNS của `lttstudios.com` đang ở **inet.vn**, không phải Cloudflare. Cloudflare
Tunnel cần một bản ghi trong **zone Cloudflare**, nên trước khi chạy script phải
đưa riêng subdomain `app` sang Cloudflare — **không đụng** trang giới thiệu ở
`lttstudios.com`.

Làm **một lần**, theo thứ tự:

1. **Kiểm tra trước tiên:** trên bảng điều khiển Cloudflare, thử **Add a site**
   với `app.lttstudios.com`. Gói miễn phí *có thể* không cho tạo zone cấp
   subdomain — đây là điều **chưa xác minh**. Nếu Cloudflare từ chối, xem "Nếu
   không tạo được zone subdomain" bên dưới.
2. Nếu được: Cloudflare cấp **2 nameserver** (dạng `x.ns.cloudflare.com`).
3. Vào DNS của `lttstudios.com` ở **inet.vn**, thêm hai bản ghi `NS`:
   - `app  NS  <ns1>.ns.cloudflare.com`
   - `app  NS  <ns2>.ns.cloudflare.com`
4. Đợi lan truyền (vài phút đến vài giờ). Zone ở Cloudflare chuyển **Active**.

Chỉ khi zone `app.lttstudios.com` **Active** ở Cloudflare mới chạy script được —
nếu không, bước trỏ DNS sẽ báo "không tìm thấy zone".

### Nếu không tạo được zone subdomain (gói miễn phí từ chối)

Hai đường thay thế, **phải ghi lại thành quyết định thay Q22** (giao thức trong
`AGENTS.md` mục 6) trước khi làm:

- **Chuyển cả `lttstudios.com` sang nameserver Cloudflare.** Mạnh nhất, thêm
  CDN + chống DDoS miễn phí cho cả trang giới thiệu. Nhưng phải **chép đủ và
  đúng mọi bản ghi DNS hiện có** (web, email...) sang Cloudflare *trước* khi đổi
  nameserver — sót một bản ghi là trang giới thiệu hoặc email công ty chết.
- **Bỏ Tunnel, mở cổng 80/443 + Caddy.** Không phụ thuộc Cloudflare, không đụng
  trần 100 MB / 100 giây. Nhưng IP nhà là IP động (cần DDNS) và mở cổng vào
  máy đang chứa token + khoá.

---

## Dựng lần đầu — dùng script, đừng làm tay

```powershell
powershell -ExecutionPolicy Bypass -File .\setup\3-cloudflare.ps1
```

Script tự làm 6 việc: tải `cloudflared`, đăng nhập, tạo tunnel, ghi cấu hình
(không BOM), trỏ DNS, cài dịch vụ Windows. Rồi tự kiểm tra từ bên ngoài.

**Chỉ một bước cần bạn:** ở phần đăng nhập, `cloudflared tunnel login` in ra
một đường link rồi **đợi**. Mở link trên trình duyệt máy nào cũng được, đăng
nhập Cloudflare, chọn zone **`app.lttstudios.com`** (zone subdomain vừa uỷ
quyền ở trên, **không** phải `lttstudios.com` gốc). Script tự chạy tiếp.

Đừng ngắt lệnh vì tưởng nó treo — nó đang đợi bạn.

### Tuỳ chọn

```powershell
# Tên miền khác
.\setup\3-cloudflare.ps1 -Hostname app.tenmien.com -TunnelName ten-tunnel

# Tắt luôn Caddy (Cloudflare đã lo HTTPS, giữ Caddy chỉ thêm chỗ hỏng)
.\setup\3-cloudflare.ps1 -DisableCaddy
```

Chạy lại được nhiều lần: đã có tunnel thì dùng lại, chỉ ghi lại cấu hình và
khởi động lại dịch vụ.

### Vì sao không nên gõ tay từng lệnh

Ba chỗ dễ sai mà script đã xử sẵn:

1. **BOM trong `config.yml`** — `Out-File` chèn BOM, cloudflared không đọc
   được dòng đầu YAML.
2. **File credentials nằm sai chỗ** — mặc định nó vào
   `%USERPROFILE%\.cloudflared`, mà dịch vụ Windows chạy bằng tài khoản khác
   nên không đọc được. Script chuyển vào `C:\LTTPlatform\cloudflare`.
3. **Thiếu quy tắc `http_status:404` cuối phần ingress** — cloudflared từ chối
   khởi động, và thông báo lỗi không nói rõ nguyên nhân.

## Tunnel và Caddy — chọn một

Hiện máy chủ đang chạy **Caddy** ở cổng 443, tự lấy chứng chỉ Let's Encrypt.
Nếu dùng Tunnel thì **Cloudflare lo phần HTTPS**, Caddy không còn cần thiết.

Hai lựa chọn:

**A. Chỉ dùng Tunnel** — gỡ Caddy, cloudflared trỏ thẳng vào `127.0.0.1:8100`.
Đơn giản nhất. Đóng được cổng 80/443 ở firewall.

**B. Tunnel → Caddy → uvicorn** — giữ Caddy làm lớp trung gian. Chỉ đáng làm
nếu bạn cần Caddy cho việc khác (phục vụ file tĩnh, nhiều site). Thêm một
tầng là thêm một chỗ hỏng.

Khuyến nghị: **chọn A**. Ít thành phần hơn thì ít chỗ sai hơn.

Nếu chọn A:
```powershell
Stop-Service Caddy
Set-Service Caddy -StartupType Disabled
```

Rồi kiểm tra `https://app.lttstudios.com` vẫn vào được — lúc này chứng chỉ do
Cloudflare cấp chứ không phải Let's Encrypt.

---

## Kiểm tra sau khi dựng

```powershell
Get-Service cloudflared                              # phải Running
Get-Content C:\LTTPlatform\logs\cloudflared.log -Tail 20
Invoke-RestMethod https://app.lttstudios.com/health/ready
```

Kết quả mong đợi: `{"status":"ready","environment":"production"}`

---

## Khi có sự cố

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| **Error 1033** | tunnel không chạy, hoặc DNS chưa trỏ. Xem `Get-Service cloudflared` |
| **Error 502** | tunnel chạy nhưng uvicorn chết. Xem `Get-Service LTTStudioWeb` |
| **Error 524** | việc chạy quá 100 giây → phải chuyển sang hàng đợi job |
| **HTTP 413** | file upload vượt 100 MB → phải chuyển sang R2 |
| Web sập sau khi sửa config | có thể do BOM. Kiểm 3 byte đầu file |

Kiểm BOM:
```powershell
[IO.File]::ReadAllBytes("C:\LTTPlatform\data\config.json")[0..2]
# 239,187,191 = có BOM
```

---

## Bảo mật

Tunnel **không mở cổng** trên máy chủ, tốt hơn NAT port-forward. Nhưng nó
**vẫn tạo một đường từ Internet vào máy**. Nghĩa là một lỗ hổng trong web app
dẫn thẳng vào máy đang chứa token Facebook/TikTok và khoá Google.

Vì vậy khi mở cho người ngoài công ty, cần thêm:
- kiểm duyệt nội dung người dùng gửi lên (file lạ chạy qua ffmpeg là đường
  thực thi mã)
- tách máy chạy job khỏi máy chứa bí mật
- bật Cloudflare Access nếu chỉ nội bộ dùng (thêm một lớp đăng nhập trước cả
  app)

Với giai đoạn nội bộ dùng thì mức hiện tại chấp nhận được.
