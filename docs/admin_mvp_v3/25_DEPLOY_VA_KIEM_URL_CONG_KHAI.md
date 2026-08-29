# 25 — Deploy và kiểm trên URL công khai

Đóng mục §E của `24_DEFERRED_POST_MVP.md` (*"chặn bởi deploy — bắt buộc trước khi
tuyên bố xong"*).

Ngày: 2026-08-29. Nhánh: `admin-mvp-v3`.

---

## 1. Điều kiện tiền deploy — kiểm trước, không kiểm sau

| Điều kiện | Kết quả |
|---|---|
| Cổng chất lượng đầy đủ | `python tools\gate.py` → **RESULT: PASS** 23/23 |
| Phiên khác đang sửa cây? | `ListAgents` → **9 phiên, tất cả offline** |
| Migration lệch? | **59 = 59** revision, không có migration mới phải chạy |
| Độ lệch giữa cây nguồn và bản đang chạy | `tools/so_deploy.py` → **đúng bằng công việc của đợt này**: 11 tệp mới + `ltt.css`. Không có phần đang dở của phiên nào khác |
| Đợt Nexus "chờ deploy" (CLAUDE.md cảnh báo) | `docs/nexus/N8_CHO_DEPLOY.md` — **đã deploy 23/08**, cảnh báo trong CLAUDE.md đã lỗi thời |

⭐ Bước `so_deploy.py` là bước quan trọng nhất trong bảng này, và nó đáng làm
**trước** mỗi lần deploy: deploy ở kho này **xoá và thay TOÀN BỘ** `app\`, nên
nếu độ lệch chứa việc đang dở của phiên khác thì ta vừa phát hành hộ họ.

---

## 2. Deploy

Theo giao thức hai lớp của `AGENTS.md` 9.3 (`Start-Process -Verb RunAs` **không**
dùng chung được với `-RedirectStandardOutput`; trộn chúng thì hỏng **im lặng**).

```
BAT DAU  = 2026-08-29 08:20:36
ADMIN    = True
EXITCODE = 0
KET THUC = 2026-08-29 08:21:37
```

⚠️ `EXITCODE=0` khác hẳn `EXITCODE` **rỗng**. Rỗng nghĩa là tiến trình chưa từng
chạy — và đó là cách người ta báo "đã deploy xong" trong khi chưa có gì xảy ra.

Nhật ký: `C:\LTTPlatform\logs\deploy-20260829-082036.{out,err,ket}.*`
`stderr` chỉ có hai dòng INFO của alembic, không có lỗi.

Deploy chạy: dừng dịch vụ → `app` → `app.previous` (đường lùi) → copy 3.406 tệp
→ `alembic upgrade head` → khởi động lại → tự kiểm sức khoẻ.

---

## 3. Sau deploy — origin

| Kiểm | Kết quả |
|---|---|
| `tools/so_deploy.py` | **khớp 461 · lệch 0 · thiếu 0 · thừa 0** |
| Dịch vụ | `LTTStudioWeb` **Running** · `LTTStudioWorker` **Running** |
| `/health/ready` | `{"status":"ready","environment":"production","database":"ok"}` |
| Hash 3 tệp mới quan trọng | `_chung.py` · `_vo.html` · `admin_console.py` — **KHỚP** từng byte |
| `_ADM_NAV` trong bản đang chạy | chỉ còn **trong chú thích** (`admin.py:106`), danh sách đã bị gỡ |
| Mixin ẩn menu SQLAdmin | **13** chỗ dùng trong `admin_api.py` đã deploy |

### Route mới có thật sự sống không

Đây là phép kiểm quyết định, chạy trên **bản đang chạy**:

| Đường dẫn | HTTP | Nghĩa |
|---|---|---|
| `/admin/` | 303 → `/login` | tồn tại |
| `/admin/khach-hang` | 303 → `/login` | tồn tại |
| `/admin/he-thong` | 303 → `/login` | tồn tại |
| `/admin/nang-cao` | 303 → `/login` | tồn tại |
| `/admin/khong-co-that-dau` | **404** | *đối chứng* — route không có thì 404, nên 303 ở trên không phải là "chuyển hướng mọi thứ" |

⭐ Không có dòng đối chứng cuối thì bốn dòng trên không chứng minh gì cả.

---

## 4. Sau deploy — **URL công khai** `https://app.lttstudios.com`

Đây là phần mà `CLAUDE.md` quy tắc 5b đòi, và loopback **không** thay thế được:
loopback bỏ qua Cloudflare (cache, CSP biên, minify).

### 4a. Cái bẫy lịch sử: Cloudflare phục vụ CSS cũ

Dự án đã dính đúng lỗi này một lần — sau khi sửa `ltt.css`, CF phục vụ bản **cũ**
(TTL 4h) nên chip hiện thành radio thô, dù origin đã đúng. Đợt này đổi `ltt.css`
rất nhiều, nên đây là phép kiểm bắt buộc.

| Kiểm | Kết quả |
|---|---|
| `ASSET_VER` trong nguồn | `8aae308b` |
| `ASSET_VER` trong HTML trang công khai | `8aae308b` — **KHỚP** |
| `cf-cache-status` của `ltt.css?v=8aae308b` | **MISS** — lấy mới từ origin, không phải bản cache cũ |
| 8 lớp CSS mới của đợt này có trong bản CF phục vụ | `adm-o-link` · `adm-hangdoi` · `adm-luoi-360` · `adm-nguyhiem` · `adm-banhmi` · `adm-mien-luoi` · `adm-timkiem` · `max-width:1600px` — **8/8 có** |

⚠️ Kích thước lệch: CF **203.612 byte** vs nguồn **216.789 byte**. Đây là
**minify của Cloudflare**, không phải bản cũ — chứng minh bằng việc cả 8 lớp mới
đều có mặt. Đừng đọc chênh lệch kích thước thành "CF chưa cập nhật".

### 4b. HTML không bị CF cache

| Đường dẫn | `Cache-Control` | `cf-cache-status` |
|---|---|---|
| `/` | `no-store` | DYNAMIC |
| `/admin/` | `no-store` | DYNAMIC |
| `/admin/khach-hang` | `no-store` | DYNAMIC |

⇒ Trang HTML tới người dùng **ngay** sau deploy, không chờ TTL.

### 4c. Không hồi quy ở các trang công khai

`ltt.css` là tệp dùng chung của cả nền tảng, nên đổi nó có thể làm vỡ khu khác.

| Trang | Kết quả |
|---|---|
| `/` | 200, render đúng, nạp `ltt.css?v=8aae308b` |
| `/vps` | 200, **không tràn ngang** (body 739 ≤ khung 754) |
| `/gia-api` | 200, tiêu đề đúng, không tràn ngang |
| `/developers`, `/nap`, `/status` | 303 → `/login` như thiết kế |
| Lỗi console | chỉ **một** 403 — là thử thách bot của Cloudflare ở `/login`, không phải lỗi site |

---

## 4d. Soi admin ĐÃ ĐĂNG NHẬP trên production — **đã làm**

Chủ sản phẩm đăng nhập bằng `admin@lttstudios.com` trong Playwright (Playwright
**tự vượt** được thử thách Cloudflare, khác với khung Browser bị chặn 403). Toàn
bộ phần dưới là **chỉ đọc** — không cấp credit, không xác nhận đơn, không thu hồi
phiên, không bật kill switch.

| Kiểm | Kết quả |
|---|---|
| 31 trang admin | **31/31 trả 200**, ≤1 `<h1>`, ≤1 `aria-current` |
| Thanh bên | đúng **6 mục** |
| Lỗi console từ trang admin | **0** (4 lỗi ghi nhận đều là thử thách Cloudflare hoặc chính lệnh chẩn đoán của tôi) |

### Dữ liệu thật — thứ CSDL nháp không có

| | |
|---|---|
| Khách hàng | **24** khách thật, email dài, số dư thật (2.510 · 520 · 100 · 21 credit) |
| Rail chú ý | **10** tài khoản vô hiệu hoá · **2** chưa xác thực — đếm từ bảng thật |
| Hàng đợi Tổng quan | **4** job hỏng · **5** đơn chờ · **10** tài khoản vô hiệu |
| Nhật ký admin | mục thật từ 22–27/08, `cap_credit` bởi `admin@lttstudios.com` |
| Provider credentials | **8** khoá, tất cả `hoạt động` |
| Tài chính | tổng đã thu **200.000đ**, có "Đơn cần xử lý" + "Hành động tiền của admin" |

### Deep-link có đúng bộ lọc đặt sẵn không — đo bằng số

Đây là luật cứng của hợp đồng P1, và nó **khớp chính xác** trên dữ liệu thật:

| Mục hàng đợi | Số | Trang đích | Số dòng thực tế |
|---|---|---|---|
| Đơn nạp đang chờ | 5 | `/admin/don?st=pending` | **5** (không lọc: 9) |
| Tài khoản bị vô hiệu hoá | 10 | `/admin/khach-hang?trang_thai=vo_hieu` | **10** (không lọc: 24), và **tất cả** đều vô hiệu |

### Bất biến an toàn — trên 7 trang có dữ liệu thật

| Bất biến | Kết quả |
|---|---|
| `credential_enc` · `password_hash` · khoá Gemini thô · `sk_live_` | **không rò ở đâu cả** |
| Provider key | chỉ hiện preview 4 số cuối (8/8 khoá) |
| Sổ credit | **không** có nút tạo/sửa/xoá |
| Kill switch | **form** có `reason` **`required`** + hạn tự tắt + ô xác nhận + CSRF — **không** phải toggle |

### GJ1 trên khách thật

Hồ sơ 360 của một khách production: **8/8 khối** có mặt, **0** nội dung bị cấm
(KYC · ngày sinh · SĐT · quốc gia · ghi chú hỗ trợ · gói dịch vụ · VNPay · uptime
· SLA), số dư ghi bằng `credit`, nút nguy hiểm có hộp xác nhận.

---

## 4e. 🔴 Một lỗi CHỈ dữ liệu production mới lộ ra

**Tìm được bằng mắt, ở khung 1440px.**

Bảng khách hàng cần **867px** nhưng khung chỉ có **791px** (rail 320px chiếm
phần còn lại). Bảy cột cộng lại đúng 867 — mỗi cột đã ở mức tối thiểu. Thứ bị
đẩy ra ngoài là **nút hành động chính của trang**: "Mở hồ sơ 360". Người vận
hành phải cuộn ngang mới bấm được việc chính.

⛔ **Phép quét tự động không bắt được**, và lý do đáng ghi lại: bảng cuộn *trong
khung của nó* nên `body.scrollWidth` vẫn đúng — không có tràn ngang. Phép kiểm
tôi viết đo tràn body, không đo "hành động chính có nhìn thấy không".

⛔ **CSDL nháp cũng không bắt được**: hai dòng email ngắn thì bảng vừa thoải mái.
Chỉ 24 khách thật với email dài mới đẩy nó qua ngưỡng.

**Lần sửa thứ nhất SAI.** Tôi cắt bớt User ID (`max-width:15ch`) — CSS áp đúng
(ID còn 101px) nhưng bảng **vẫn cần 867px**. Cột đầu rộng vì **email**, không vì
UUID. Đo lại từng cột mới thấy.

**Lần sửa thứ hai đúng:** nâng ngưỡng gập rail **1280 → 1500px**. Ở 1440px rail
xuống dưới, bảng được 1129px, cần 1127px — **vừa**, và nút hành động chính nằm
trong khung.

Cả hai thay đổi đều giữ lại: ID cắt bớt vẫn có ích (giá trị đầy đủ ở `title`).

---

## 5. Hạng mục CHƯA kiểm được, và vì sao

### ~~Giao diện admin đã đăng nhập~~ → **ĐÃ LÀM**, xem §4d

Ghi lại rào cản ban đầu để lần sau không mất thời gian dò lại:

1. **Cloudflare chặn trình duyệt tự động ở `/login`** bằng thử thách "Verify you
   are human". Điều này `tools/so_deploy.py` đã ghi lại từ 27/08 và nay xác nhận
   lại — request `/login` trả **403**, trang hiện hộp thử thách.
   ⛔ Tôi **không giải CAPTCHA**. Đó là ranh giới cứng, không phải một trở ngại
   kỹ thuật.
2. **Không có mật khẩu admin production**, và tôi không nhập mật khẩu vào biểu
   mẫu — cũng là ranh giới cứng.

`mcp__claude-in-chrome` **chưa kết nối** — `list_connected_browsers` trả rỗng.

⭐ **Đường đi được:** **Playwright**. Nó tự vượt thử thách Cloudflare (khung
Browser thì không), rồi chủ sản phẩm đăng nhập một lần trong cửa sổ đó — sau đó
phiên giữ nguyên cho cả buổi soi. Ghi lại vì đây là khác biệt thật giữa hai công
cụ trình duyệt, và nó quyết định soi được hay không.

### Còn lại chưa làm

Đi hết bằng phím Tab bằng tay để cảm nhận thứ tự focus. Máy đã xác nhận thứ tự =
thứ tự DOM (không có `tabindex` dương), nên đây là việc cảm nhận, không phải việc
phát hiện lỗi.

---

## 6. Đường lùi

`C:\LTTPlatform\app.previous` giữ nguyên bản trước. Muốn quay lại thì đổi chỗ
hai thư mục và khởi động lại hai dịch vụ. Migration của đợt này: **không có**
(59 = 59), nên lùi mã là lùi được toàn bộ.
