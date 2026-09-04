# 06 — Dọn hạ tầng (vệ sinh trước khi làm tính năng lớn)

Runbook dọn các phần thừa/lỏng lẻo còn lại sau H6→UX. Chia làm hai loại:
**việc Claude đã làm tự động** (an toàn, cục bộ) và **việc bạn phải tự làm**
(đụng tài khoản bên thứ ba hoặc mạng máy chủ đang chạy thật).

Cập nhật: 2026-08-01.

---

## Bức tranh hạ tầng hiện tại

| Thành phần | Trỏ về | Trạng thái |
|---|---|---|
| `app.lttstudios.com` | Cloudflare (104.21.58.244 / 172.67.166.73 + IPv6) → Tunnel → máy chủ :8100 | ✅ đúng, đang phục vụ |
| `lttstudios.com` (trang chủ) | iNET 103.57.220.210 | ✅ đúng |
| VPS Vultr `45.32.104.192` | **không còn trong DNS** | ⚠️ vẫn chạy Caddy (HTTP 308), **vẫn tính tiền** — cần huỷ |
| Cloudflare Web Analytics beacon | chèn `beacon.min.js` vào trang | ⚠️ bị CSP chặn (vô hại) — nên tắt cho gọn |
| IPv6 trên máy chủ | có địa chỉ nhưng không có route ra Internet | ⚠️ chỉ ảnh hưởng trình duyệt CHẠY TRÊN máy chủ, không ảnh hưởng khách |

---

## A. Việc Claude đã làm tự động (xong)

1. **Chốt lỗ hổng `.gitignore`** — thêm quy tắc tổng quát `data/*.enc` (trước chỉ
   chặn từng file cụ thể). Nền tảng giờ mã hoá nhiều loại token/key hơn.
   Commit `8f72479`.
2. **Kiểm chứng sạch trước khi push**:
   - `python tools/scan_source_secrets.py` → **0 finding, PASS**.
   - Rà toàn bộ lịch sử git: file nhạy cảm DUY NHẤT từng được commit là
     `cloudflare/config.yml.example` (bản mẫu, không có credential thật). Sạch.
3. **Đẩy git lên bản sao dự phòng cục bộ** — tạo bare repo
   `D:\LTTBackups\LTTSTUDIOSAPP.git` và push toàn bộ (24 commit). Đây là remote
   tên `backup`, cho dự phòng phiên bản ngay, **không lộ gì ra Internet**.
   ⛔ **HẾT DÙNG TỪ 04/09/2026.** Remote `backup` đã gỡ: `D:\LTTBackups`
   chứa `app.env` + dump CSDL và đã được siết ACL đúng theo hạng mục **W1.5**
   (*"chỉ SYSTEM/Admin đọc"*), nên không đẩy mã vào đó được — và **không nên**.
   Bản sao off-site nay là **GitHub riêng tư** `origin`. Xem
   `docs/16_CAP_NHAT_VA_DEPLOY.md`.

---

## B. Việc bạn phải tự làm (Claude không có quyền/không nên tự làm)

### B1. Huỷ VPS Vultr cũ `45.32.104.192` — ƯU TIÊN (đang đốt tiền)

Máy này đã ra khỏi DNS nhưng vẫn chạy. Nền tảng mới **không dùng nó chút nào**.

1. Đăng nhập <https://my.vultr.com>.
2. (Tuỳ chọn, an toàn) Products → chọn server → **Snapshot** để giữ ảnh phòng khi
   cần lục lại cấu hình Caddy cũ. Snapshot rẻ hơn nhiều so với để nguyên VPS.
3. Xác nhận không còn dịch vụ nào cần: đây chỉ là reverse-proxy Caddy đời trước
   khi chưa dùng Cloudflare Tunnel — nền tảng hiện tại không phụ thuộc.
4. **Server → Settings → Destroy** (hoặc nút Destroy). Nhập tên máy để xác nhận.
5. Kiểm tra sau khi huỷ: `curl -m6 -o NUL -w "%{http_code}" http://45.32.104.192/`
   phải **không phản hồi** (000/timeout).

> Không đụng gì tới iNET (`lttstudios.com`) — đó là trang chủ, vẫn dùng.

### B2. Tắt Cloudflare Web Analytics beacon

`beacon.min.js` đang bị Content-Security-Policy của nền tảng chặn (nên console
báo lỗi vô hại). Tắt để log sạch:

1. Cloudflare dashboard → chọn `lttstudios.com` → **Analytics & Logs → Web Analytics**.
2. Tìm site đang bật **Automatic Setup / JS beacon**, chuyển sang **Manual** hoặc
   xoá site đó. (Ta không cần beacon — sẽ đo bằng log server nếu cần.)
3. Reload `app.lttstudios.com`, mở DevTools Console: không còn dòng CSP chặn beacon.

> Cách khác nếu muốn giữ beacon: thêm `static.cloudflareinsights.com` vào
> `script-src`/`connect-src` trong CSP (`server/app.py`). Không khuyến nghị —
> thêm bên thứ ba vào CSP chỉ để có analytics là đánh đổi không đáng.

### B3. Thiết lập remote GitHub riêng tư (đưa mã lên off-site)

Bản mirror ở B-A3 chỉ nằm trên `D:` — cùng ổ với mã nguồn. Để an toàn thật sự
cần một remote **off-site** và **PRIVATE** (repo có tham chiếu hạ tầng, dù không
có secret). Máy chủ **chưa cài `gh` CLI**, nên làm thủ công:

1. Tạo repo **Private** trên GitHub (hoặc GitLab), ví dụ `lttstudios/platform`.
   **Đừng** khởi tạo kèm README/license (tránh lệch lịch sử).
2. Trên máy chủ:
   ```powershell
   cd D:\LTTSTUDIOSAPP
   git remote add origin https://github.com/<user>/<repo>.git
   git push -u origin master
   ```
3. Xác thực push: dùng **Personal Access Token** (Settings → Developer settings →
   Fine-grained token, chỉ quyền `Contents: Read/Write` trên đúng repo đó) làm
   mật khẩu khi Git hỏi. Không dùng mật khẩu tài khoản.
4. Kiểm chứng: `git ls-remote origin master` trả về đúng commit HEAD.

> Bảo mật: repo **BẮT BUỘC Private**. Trước khi mời cộng tác viên, rà lại
> `.gitignore` — `data/`, `secrets/`, `cloudflare/` không bao giờ được lên.

### B4. IPv6 máy chủ — khuyến nghị HOÃN

`curl -6 https://app.lttstudios.com` trả 000: máy chủ có địa chỉ IPv6 nhưng
**không có route ra Internet**. Việc này **không ảnh hưởng khách** (khách vào qua
Cloudflare từ máy họ) và **không ảnh hưởng vận hành** (cloudflared, PostgreSQL,
app đều đi IPv4/loopback). Nó chỉ làm trình duyệt *chạy trên chính máy chủ* không
mở được hostname công khai — mà việc đó đã kiểm bằng loopback `127.0.0.1:8100`.

→ **Giá trị thấp, rủi ro đụng mạng máy đang chạy thật cao. Hoãn.**

Nếu về sau vẫn muốn xử lý (cách đảo ngược được, tác dụng ngay, không cần reboot):
```powershell
# Xem card mang dang hoat dong
Get-NetAdapter | Where-Object Status -eq 'Up'
# Uu tien IPv4, tat IPv6 tren DUNG card do (thay '<Ten>')
Disable-NetAdapterBinding -Name '<Ten>' -ComponentID ms_tcpip6
# Hoan tac neu can:
# Enable-NetAdapterBinding -Name '<Ten>' -ComponentID ms_tcpip6
```
Làm khi máy rảnh, và xác nhận `cloudflared`/dịch vụ vẫn xanh ngay sau đó.

---

## Checklist nghiệm thu dọn hạ tầng

- [x] `.gitignore` chặn `data/*.enc`
- [x] Scanner secret 0 finding
- [x] Lịch sử git sạch (chỉ có `config.yml.example`)
- [x] Mirror `backup` trên `D:\LTTBackups\LTTSTUDIOSAPP.git`
- [ ] **Huỷ VPS Vultr `45.32.104.192`** (B1)
- [ ] Tắt CF Web Analytics beacon (B2)
- [ ] Remote GitHub Private + push (B3)
- [ ] (Hoãn) IPv6 máy chủ (B4)
