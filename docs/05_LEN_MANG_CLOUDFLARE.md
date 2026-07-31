# Đưa `app.lttstudios.com` lên mạng qua Cloudflare — quy trình đầy đủ

> Runbook cho H0.1. Chia rõ **việc của bạn** (🧑) và **việc của tôi/Claude** (🤖).
> Quyết định nền: Q27 trong `QUYET_DINH_NEN_TANG.md`.
> Không có giá trị bí mật nào trong file này.

---

## 0. Hiểu đúng trước khi làm (đọc kỹ phần này)

Ba điều dễ hiểu nhầm, làm rõ ngay:

**1. Đổi nameserver ≠ chuyển hosting.**
Chuyển DNS sang Cloudflare **không** động tới nơi chứa trang chủ. inet.vn
OnePanel vẫn chứa và phục vụ `lttstudios.com`. Cloudflare chỉ làm việc "phân
giải tên miền → địa chỉ IP". Bản ghi trang chủ vẫn trỏ về IP inet.vn.

**2. "DNS only" giữ trang chủ nguyên vẹn.**
Mỗi bản ghi trong Cloudflare có một công tắc mây:
- **Mây xám (DNS only):** Cloudflare chỉ trả IP rồi đứng ngoài. Trình duyệt nối
  **thẳng** tới inet.vn. Trang chủ chạy **y hệt hiện tại**.
- **Mây cam (Proxied):** lưu lượng đi **qua** Cloudflare. Cần cho Tunnel.

Ta để `@` và `www` (trang chủ) **mây xám**, chỉ `app` **mây cam**.

**3. Không tốn tiền, không cần Enterprise.**
Cloudflare **Free** làm được tất cả những gì cần ở đây. Cái Enterprise-only là
"tạo riêng một subdomain thành zone" — ta **không** dùng cách đó (xem Q22 đã bị
thay bởi Q27). Chỉ cần **tài khoản Cloudflare miễn phí**.

---

## 1. Sơ đồ sau khi xong

```
Trình duyệt khách
      │
      ├─ lttstudios.com ──────► (DNS only) ──► inet.vn OnePanel (trang chủ, GIỮ NGUYÊN)
      │
      └─ app.lttstudios.com ──► (Proxied) ──► Cloudflare edge
                                                   │  (Tunnel, không mở cổng)
                                                   ▼
                                          máy chủ này: LTTStudioWeb :8100
```

DNS do Cloudflare quản; trang chủ vẫn ở inet.vn; app đi qua Tunnel về máy này.

---

## 2. Bản ghi DNS hiện có (đo ngày 2026-07-31)

Phải chép **đủ** những bản ghi này sang Cloudflare trước khi đổi nameserver.
Đây là toàn bộ — may mắn là ít và **không có email (MX)**, nên rủi ro thấp.

| Tên | Loại | Giá trị | Mây | Ghi chú |
|---|---|---|---|---|
| `@` (lttstudios.com) | A | `103.56.163.10` | xám | trang chủ inet.vn |
| `@` | AAAA | `2001:df7:ce00:19::3:0` | xám | trang chủ IPv6 |
| `www` | A/AAAA | (như `@`) | xám | trang chủ |
| `app` | — | (sẽ tạo bằng Tunnel) | cam | **không chép bản ghi `app` cũ** (nó trỏ máy chủ cũ 45.32.104.192) |
| MX | — | **không có** | — | không dùng email trên tên miền này |
| TXT | — | **không có** | — | |

> 🤖 Trước khi bạn đổi nameserver, tôi sẽ `nslookup` lại một lần nữa để chốt
> danh sách cuối (phòng khi có bản ghi phát sinh), và đối chiếu với những gì
> Cloudflare tự quét được.

---

## 3. Quy trình — theo đúng thứ tự

### Bước 1 🧑 — Tạo tài khoản + thêm site vào Cloudflare

1. Vào `dash.cloudflare.com`, tạo tài khoản miễn phí (nếu chưa có).
2. **Add a site** → gõ `lttstudios.com` → chọn gói **Free**.
3. Cloudflare tự quét bản ghi hiện có. **Đối chiếu với bảng ở mục 2.** Thiếu
   cái nào thì thêm tay.
4. Đặt `@` và `www` ở **DNS only** (bấm vào mây cho thành **xám**). Bản ghi
   `app` cũ (nếu Cloudflare quét được, trỏ `45.32.104.192`) → **xoá** (Tunnel
   sẽ tạo lại đúng ở bước 5).
5. Cloudflare hiện **2 nameserver** cấp cho bạn (dạng `x.ns.cloudflare.com`).
   Ghi lại hai tên đó.

> 🤖 Gửi tôi ảnh chụp trang DNS records của Cloudflare (che gì nhạy cảm nếu
> muốn) hoặc gõ lại danh sách — tôi rà giúp xem đã đủ và đúng mây chưa **trước
> khi** bạn đổi nameserver. Đây là bước dễ sót nhất.

### Bước 2 🧑 — Đổi nameserver ở nhà đăng ký tên miền

Nameserver hiện tại là `hoian/danang.vclouddns.com` (inet.vn). Đổi sang 2 NS
Cloudflare cấp:

- Vào nơi **đăng ký** `lttstudios.com` (nhiều khả năng là tài khoản inet.vn,
  phần **quản lý tên miền / nameserver** — *không* phải phần DNS zone).
- Thay hai nameserver cũ bằng hai của Cloudflare.
- Lưu.

> Nếu tên miền mua ở nơi khác inet.vn, đổi NS ở nơi đó. Không chắc mua ở đâu?
> 🤖 tôi tra whois giúp.

### Bước 3 ⏳ — Đợi lan truyền

Đổi NS mất **vài giờ đến 24h** để lan khắp Internet. Cloudflare gửi email khi
zone chuyển **Active**. Trong lúc chờ, trang chủ vẫn chạy bình thường (NS cũ và
mới đều trả cùng IP inet.vn cho `@`).

> 🤖 Khi bạn báo "đã đổi NS", tôi kiểm định kỳ bằng `nslookup -type=NS
> lttstudios.com` xem đã trỏ Cloudflare chưa, và xác nhận trang chủ vẫn sống.

### Bước 4 🤖🧑 — Cài hệ thống lên máy chủ (`C:\LTTPlatform`)

Máy này **chưa cài** (chưa có `C:\LTTPlatform`). Trước khi Tunnel, phải cài
nền tảng như một dịch vụ.

- 🤖 Tôi rà soát lần cuối `setup/1` và `setup/2` (đã thêm PostgreSQL + worker,
  **chưa chạy thật lần nào** — tôi bám sát để bắt lỗi lần-đầu).
- 🧑 Bạn mở **PowerShell bằng Run as administrator**, tại thư mục dự án chạy:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\setup\1-kiem-tra-may.ps1
  powershell -ExecutionPolicy Bypass -File .\setup\2-cai-dat.ps1
  ```
- `setup/2` **in mật khẩu admin đúng một lần** — lưu lại ngay.
- 🤖 Sau đó tôi nghiệm thu `http://127.0.0.1:8100/health/ready` (cục bộ, chưa
  cần Tunnel) và chạy `setup/4-nghiem-thu.ps1`.

> Lưu ý (đã ghi ở nhật ký): máy này vừa phát triển vừa sắp thành máy chủ.
> Database `lttplatform` dev đang dùng chỉ có schema, data đã dọn — `setup/2`
> dùng lại chính nó, không mất gì.

### Bước 5 🧑🤖 — Dựng Tunnel

- 🧑 Chỉ khi zone **Active**, mở **PowerShell Run as administrator**, chạy:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\setup\3-cloudflare.ps1
  ```
- Script **dừng ở phần đăng nhập**, in ra một **đường link**. Mở link trên
  trình duyệt bất kỳ, đăng nhập Cloudflare, **chọn zone `lttstudios.com`**.
  Script tự chạy tiếp — đừng ngắt vì tưởng treo.
- Script tự: tạo tunnel, ghi cấu hình (không BOM), tạo CNAME `app` → tunnel
  (Cloudflare tự đặt mây cam), cài dịch vụ `cloudflared`, kiểm tra từ ngoài.
- 🤖 Nếu bước trỏ DNS báo "không tìm thấy zone" → zone chưa Active, đợi thêm.
  Tôi đọc log `C:\LTTPlatform\logs\cloudflared.log` nếu có trục trặc.

### Bước 6 🤖🧑 — Nghiệm thu

- 🤖 Từ đây tôi gọi `https://app.lttstudios.com/health/ready` (mạng ngoài) —
  mong `{"status":"ready","environment":"production"}`.
- 🤖 Mở `https://app.lttstudios.com` bằng trình duyệt thật (Playwright), kiểm
  đăng nhập + chạy demo qua hàng đợi.
- 🧑 Bạn mở `https://lttstudios.com` xác nhận **trang chủ vẫn chạy** như cũ.
- 🤖 Đổi `LTT_ENV` sang `production` nếu chưa (cookie Secure hợp với HTTPS).

---

## 4. Sau khi lên mạng — dọn dẹp

- Máy chủ cũ `45.32.104.192` (đang chạy Caddy phục vụ app hiện tại) trở nên
  thừa. 🧑 quyết định giữ hay tắt sau khi app mới chạy ổn vài ngày.
- 🧑 Đặt các khoá còn treo vào `C:\LTTPlatform\secrets\app.env`: `RESEND_API_KEY`
  + `LTT_MAIL_FROM` (H1.3, gửi mail thật), `TURNSTILE_*` (H1.3, chống bot),
  và khi làm H5: `GEMINI_API_KEY`.

---

## 5. Nếu có trục trặc

| Triệu chứng | Nguyên nhân thường gặp | Ai xử |
|---|---|---|
| Cloudflare không cho Add site `lttstudios.com` | tên miền đang bị khoá ở registrar | 🧑 mở khoá ở nhà đăng ký |
| Zone mãi không Active | NS chưa đổi đúng, hoặc chưa lan truyền | 🧑 kiểm lại NS ở registrar; ⏳ đợi |
| Trang chủ `lttstudios.com` chết sau đổi NS | sót bản ghi `@`/`www` khi chép | 🤖 so bản ghi, 🧑 thêm lại ở Cloudflare |
| `setup/3` báo "không tìm thấy zone" | zone chưa Active | ⏳ đợi rồi chạy lại |
| Error 1033 | tunnel chưa chạy / DNS chưa trỏ | 🤖 `Get-Service cloudflared` |
| Error 502 | tunnel chạy nhưng app chết | 🤖 `Get-Service LTTStudioWeb` + log |

---

## 6. Việc ngay bây giờ

🧑 **Bước 1**: vào `dash.cloudflare.com`, **Add a site** `lttstudios.com` (gói
Free), rồi báo tôi — hoặc gửi danh sách bản ghi Cloudflare quét được để tôi rà
trước khi bạn đổi nameserver. Chưa đổi NS vội cho tới khi rà xong.
