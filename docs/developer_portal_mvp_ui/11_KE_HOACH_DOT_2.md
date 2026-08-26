# 11 — Kế hoạch Đợt 2 khu `/developers`: bám ảnh tham chiếu, không bịa dữ liệu

**2026-08-27** · nhánh `public-api-v2` · nguồn: ảnh chủ sản phẩm +
`LTT_Developer_Portal_MVP_UI_Prompt_Pack_V3` + mã đang chạy

> Đọc trước: `09_FINAL_MVP_REPORT.md` (Đợt 1 đã làm gì) và
> `10_DEVELOPER_UI_CONTRACT.md` (luật giao diện hiện hành). Kế hoạch này
> **tiếp** chúng, không thay chúng.

---

## 0. Ba câu tóm tắt

1. **Đợt 1 (26/08) đã sửa xong tầng "thô"** — bề rộng 898→1318px, 0 ô nhập
   `inset`, 0 `fieldset` `groove`, 0 tràn ngang, 14 primitive `.dev-*`. Cái còn
   lại **không phải lỗi, mà là *độ dày*: trang đúng nhưng trống.** `/developers`
   ở 1920×1080 chỉ dùng ~530px chiều cao; ảnh tham chiếu lấp đầy khung hình.
2. **Ảnh tham chiếu chứa ba loại thứ trộn lẫn**: thứ dựng lại được bằng CSS
   thuần, thứ cần một truy vấn tổng hợp mới (có thật, rẻ), và thứ **không có
   dữ liệu nào đỡ** (badge Beta/Alpha, bảng bóc tách giá theo dòng). Phần lớn
   rủi ro của đợt này nằm ở việc phân loại sai nhóm thứ ba.
3. **Prompt Pack V3 nghiêm hơn V2 ở đúng chỗ ta cần** (contract lock riêng, tách
   batch bảo mật, cấm fake metric). Nhưng nó giả định chạy trên kho **chưa từng
   làm Đợt 1** — chạy nguyên văn sẽ tốn 3 prompt để dựng lại tài liệu đã có và
   sinh **9 tệp trùng số** với thư mục hiện tại. Mục §6 nói cách ghép.

---

## 1. Hệ thống: `/developers` nằm ở đâu

```
app.lttstudios.com
├─ /                     catalog công khai + 14 app  (bán hàng)
├─ /vps  /nexus  /…      app trong `apps/`            (sản phẩm)
├─ /api/v1               BEARER surface               ← khách gọi bằng khoá
└─ /developers           SESSION surface   (32 route) ← khách QUẢN LÝ khoá
```

**`/developers` không phải một app.** Nó là adapter/policy layer của H35: domain
ở `platform_core/public_api/`, HTTP ở `server/api/` (bearer) và
`server/routes/developer/` (session). Nó **không** có `manifest.py`, không lên
catalog, không có bảng riêng ngoài `public_api_*`.

Hệ quả cho đợt này, ba điều:

| | |
|---|---|
| Vỏ `.app-shell` **dùng chung với khu VPS** | đổi `.app-side` là chạm hai khu — phải đo cả hai |
| `_kieu_chung.html` **nạp cho mọi trang nền tảng** | vá nguyên tố ở đó chạm 14 app khác |
| `/api/v1` **đang bán thật** (`text.chat`, `image.ltt`) | không được sửa một dòng Python nào của tầng thi hành để làm đẹp |

Trạng thái đang chạy trên production (đọc 26/08): `LTT_PUBLIC_API=1`,
`LTT_PUBLIC_API_TOOLS=text.chat,image.ltt`. **Có khách trả tiền.**

---

## 2. `/developers` hiện tại — bản đồ chính xác

### 2.1. 32 route, 16 bề mặt trang, 3 nhóm điều hướng

`test_197` chốt đúng **32 route**; `test_303` chốt **trần 12 mục** thanh bên và
đúng **một** `aria-current="page"`.

```
Bắt đầu     overview(/developers) · cli(/developers/cli)
              └ con: notifications → overview,  quickstart → cli
Tham chiếu  tools · pricing · docs
              └ con: playground → tools
Tài khoản   keys · logs · usage · webhooks · settings
              └ con: projects → keys,  jobs → logs,  privacy → settings
```

Khai ở **một chỗ**: `server/routes/developer/_chung.py` — `SECTIONS`,
`NHOM_NAV`, `CHA_CUA`, `MUC_CON`. `TRANG_CONG_KHAI` **rỗng có chủ ý** (chốt
25/08): cả khu đứng sau đăng nhập.

### 2.2. Mỗi trang lấy dữ liệu ở đâu — *quyền uy dữ liệu*

| Trang | Nguồn thật | Ghi chú |
|---|---|---|
| overview | `_overview_counts` + `credit.so_du` + `usage.usage_totals` + `config.*` | **chưa** đọc `request_log`, **chưa** đọc `notifications` |
| cli / quickstart | hằng số cấu hình + `_goc_url` | không đọc tài khoản |
| tools / tool_detail | `build_catalog(config)` → `ToolSpec.api_contract` | bảng tham số **sinh từ `input_schema`** |
| playground | catalog + `dev_playground.js` (314 dòng) | gọi `/api/v1` thật |
| pricing | `pricing.simulate` → `Simulation` | **một số**, không bóc tách dòng |
| docs | OpenAPI sinh từ registry | `/developers/openapi/download` |
| keys / projects | `devkeys.list_for_user` · `projects.list_for` | bí mật hiện **một lần** |
| logs | `request_log.list_for` + `.counts(since)` | **có đủ** time/status/tool/request_id/key_id/latency_ms/credit_delta |
| log_detail | `request_log.timeline` + `error_registry.REGISTRY` | |
| jobs | `_recent_api_jobs` (lọc `api_meta`) | |
| usage | `usage.usage_lines` · `usage_totals` · `budgets` | |
| webhooks | `WebhookSubscription` + `WebhookDelivery` | có `status`, `attempts`, `created_at` |
| notifications | `notifications.list_for` · `unread_count` | 12 loại cảnh báo thật |
| settings / privacy | cấu hình + `/developers/privacy/export` | |

### 2.3. Vấn đề còn lại — đo chứ không cảm

Từ ảnh chụp `evidence/sau/1920/` (bản có dữ liệu):

| Triệu chứng | Số đo | Gốc |
|---|---|---|
| **Overview trống** | nội dung cao ~530px / 1080px; 6 thẻ chỉ số + 1 thẻ nút, hết | không có lưới hai cột; không panel nào đọc `request_log`/`notifications` |
| **Keys quá dài** | ~1.500px, biểu mẫu tạo khoá chiếm 2/3 | biểu mẫu nằm thẳng trên trang, không sau một nút |
| **Sáu thẻ chỉ số một hàng** | mỗi thẻ ~205px | `auto-fit` không có trần số cột |
| **Không có sắc kỹ thuật** | 0 token cyan/teal trong `ltt.css` | mọi nhấn mạnh đều là `--brand-primary` đỏ |
| **Viền ngả nâu-đỏ** | `--border-subtle:#382422` | token nền tảng ấm; ảnh dùng xám trung tính |
| **CLI là một cột văn xuôi dài** | ~1.900px, 8 thẻ xếp dọc | không dùng lưới hai cột dù nội dung tách đôi tự nhiên |

⭐ **Không cái nào là "thiếu hệ thống thiết kế".** Hệ thống đã có. Thiếu là
**ba primitive bố cục** (lưới 2 cột, đầu trang có ô hành động, biểu đồ) và
**một bảng màu vận hành**.

---

## 3. Ảnh tham chiếu — bóc thành hợp đồng

### 3.1. Ngôn ngữ hình

| Thành phần | Trong ảnh | Ta có chưa |
|---|---|---|
| Nền canvas | ~`#0a0a0b` trung tính | `#08090a` — **khớp** |
| Nền thẻ | ~`#141416` | `--surface-raised:#151111` — **khớp về độ sáng**, lệch về sắc (ta ngả đỏ) |
| Viền | xám trung tính ~`#232326` | `#382422` ngả nâu — **lệch thấy được** |
| Đỏ thương hiệu | mục đang chọn, nút chính, lỗi | `--brand-primary:#ef3731` — **khớp** |
| **Cyan/teal** | đường "Request", chip `Live`, ô mã, biểu tượng credit | **CHƯA CÓ** |
| Xanh lá | "Hoạt động tốt", ✓ hoàn tất, mã 2xx | `--status-success:#62d889` — khớp |
| Vàng/hổ phách | tiền (`15 credit`, `≈1.500 VND`), lưu ý | `--status-warning:#efb84f` — khớp |
| Bo góc | thẻ ~12px, chip ~6px | `--radius-lg/sm` — khớp |
| Mật độ | ô bảng ~10–12px dọc, chữ 12,5px | `.dev-bang` đã đúng |

⇒ **Delta màu đúng hai dòng**: thêm họ token cyan/teal vận hành, và trung tính
hoá viền/nền *trong phạm vi khu API*. Đã có tiền lệ đúng dạng này: khối
`--vps-teal*` ở `ltt.css:1162`.

### 3.2. Ngữ pháp bố cục (thứ ảnh dạy, mà ta chưa có)

1. **Đầu trang có ô hành động** — H1 + phụ đề bên trái, nút chính bên phải
   (`+ Tạo khóa mới`, `+ Tạo webhook`).
2. **Lưới nội dung 2 cột `2fr / 1fr`** — dùng ở overview (biểu đồ|checklist,
   bảng|thông báo), cli (cấu hình|chọn công cụ), pricing (soạn|kết quả).
3. **Dải mục con là tab gạch chân**, không phải viên thuốc.
4. **Thẻ chỉ số có ô biểu tượng bên phải** + một dòng biến thiên có màu.
5. **Bảng không viền dọc**, chỉ hairline ngang; chân bảng có tổng + phân trang.
6. **Bậc thang ngang 4 bước** với ba trạng thái: xong (teal ✓) · đang làm
   (đỏ đặc) · chưa tới (xám).
7. **Thanh trên riêng của khu** — liên kết phụ + viên trạng thái hệ thống +
   chuông thông báo.

---

## 4. Ma trận: từng chi tiết trong ảnh → phán quyết

Ba mức: **THẬT** (dữ liệu đã có, chỉ bày lại) · **SUY RA ĐƯỢC** (cần một truy
vấn tổng hợp mới trên bảng đã có, không đổi schema) · **KHÔNG CÓ DỮ LIỆU** (bịa
nếu làm).

### Vỏ

| Chi tiết ảnh | Phán quyết | Quyết định |
|---|---|---|
| Khối thương hiệu đầu thanh bên | thuần kiểu | **NHẬN** |
| Biểu tượng cho 10 mục điều hướng | thuần kiểu (SVG nội tuyến — đã có tiền lệ ở `nexus_*.html`) | **NHẬN** |
| Ô chọn **Project** đầu thanh bên | THẬT (`projects.list_for`) nhưng *chức năng lọc chéo trang* là tính năng mới | **HOÃN** — thêm nút thì phải thêm tham số lọc cho keys/logs/usage + test; ngoài 4 Golden Outcome |
| Thẻ người dùng cuối thanh bên | trùng avatar ở header nền tảng | **TỪ CHỐI** |
| Thanh trên khu: viên "Tất cả hệ thống hoạt động" | THẬT (`api_enabled`/`read_only`) | **NHẬN** — thay banner cảnh báo ở ca khoẻ, giữ banner ở ca hỏng |
| Chuông + số chưa đọc | THẬT (`notifications.unread_count`) | **NHẬN** |

### Tổng quan

| Chi tiết ảnh | Phán quyết | Quyết định |
|---|---|---|
| 4 thẻ chỉ số (ta đang có 6) | THẬT | **NHẬN** — gộp còn 4, trần 4 cột |
| "Request hôm nay 248 · 3 lỗi (1,2%)" | THẬT (`request_log.counts(since=đầu ngày)`) | **NHẬN** |
| "+120 so hôm qua" | SUY RA ĐƯỢC (gọi `counts` lần hai với `since=đầu hôm qua`, trừ) | **NHẬN** — 4 dòng, không đổi schema |
| **Biểu đồ 7 ngày (Request/Credit)** | SUY RA ĐƯỢC — `GROUP BY date(created_at)` trên `public_api_requests`, đã có index `ix_public_api_requests_owner_time` | **NHẬN, Đợt 3** — kèm luật: thiếu ngày thì **hiện trạng thái rỗng**, tuyệt đối không nội suy |
| "Bắt đầu nhanh" 3 bước có ✓ | THẬT (`active_keys`, `projects`, `da_goi_api`) | **NHẬN** — giá trị cao nhất trên mỗi đơn vị công |
| "Request gần đây" (5 dòng) | THẬT (`request_log.list_for(limit=5)`) | **NHẬN** — tỉ lệ giá trị/công tốt nhất cả đợt |
| "Thông báo" (danh sách) | THẬT (`notifications.list_for`) | **NHẬN** |

### Cắm vào công cụ

| Chi tiết ảnh | Phán quyết | Quyết định |
|---|---|---|
| Bậc thang 4 bước có trạng thái | bước 1–2 THẬT; bước 3 "đang cấu hình" **KHÔNG CÓ DỮ LIỆU** | **NHẬN ĐÚNG PHẦN THẬT** — 4 bước là *nội dung*, chỉ tô "xong" cho bước ta biết chắc |
| Ô mã có sắc teal + nút chép | thuần kiểu (`sao_chep.js` đã có) | **NHẬN** |
| Lưới 2×3 ô chọn công cụ | THẬT (đã có 5 ô, chỉ đổi bố cục) | **NHẬN** |
| H1 tô đỏ từ đầu ("**Kết nối** LTT API…") | thuần kiểu, nhưng **vỡ khi dịch** (trật tự từ EN khác) | **TỪ CHỐI** — đổi lấy `.dev-h1` + phụ đề, giữ nguyên giá trị thị giác |

### Công cụ & model

| Chi tiết ảnh | Phán quyết | Quyết định |
|---|---|---|
| Lưới thẻ công cụ | THẬT (đã có, gấp mở được) | **NHẬN** — chỉ chỉnh lưới/mật độ |
| Badge `Stable` / `Beta` / `Alpha` | **KHÔNG CÓ DỮ LIỆU** — `ToolSpec` (`platform_core/registry.py:78`) không có trường độ ổn định | **TỪ CHỐI** |
| Badge thật thay vào | `execution_mode` (sync/async), `capability`, số model trong `api_contract.models`, `deprecated` | **NHẬN** |

### Giá & mô phỏng

| Chi tiết ảnh | Phán quyết | Quyết định |
|---|---|---|
| 2 cột: soạn JSON \| kết quả | thuần bố cục | **NHẬN** |
| "15 credit" + "≈ 1.500 VND" | THẬT (`Simulation.credit`; 1 credit = 100đ — Q31) | **NHẬN** |
| **Bảng bóc tách theo dòng** (Model 10 · Độ phân giải 3 · Steps 1 · Guidance 1) | **KHÔNG CÓ DỮ LIỆU** — `Simulation` trả một số; bóc tách phải mổ `invocation.price`, tức chạm quyền uy giá | **TỪ CHỐI** |
| Thay bằng | `pricing_version`, cờ `bounded`, `detail`, và câu "mô phỏng, không gọi provider, không thu tiền" | **NHẬN** |
| Hộp lưu ý hổ phách 3 gạch đầu dòng | THẬT (đúng ba câu trên) | **NHẬN** |

### Khóa API

| Chi tiết ảnh | Phán quyết | Quyết định |
|---|---|---|
| Nút `+ Tạo khóa mới` ở đầu trang | thuần bố cục | **NHẬN** — biểu mẫu vào `<details class="dev-tao">`, không JS, không route mới, không hỏng deep link |
| Tab `Tất cả / Live / Test` | THẬT (`key.mode`) | **NHẬN** — tham số truy vấn `?mode=`, **không** thêm route ⇒ `test_197` vẫn 32 |
| Chip môi trường xanh-teal | thuần kiểu | **NHẬN** |
| Menu `⋮` gộp hành động | thuần kiểu, nhưng **giấu hành động không hoàn tác** | **TỪ CHỐI** — Prompt 07 đòi "danger actions rõ"; giữ nút hiện |
| Chân bảng "Tổng cộng 4 khóa" + phân trang | tổng THẬT; phân trang SUY RA ĐƯỢC (`offset`) | tổng **NHẬN**; phân trang **HOÃN** (khoá thường < 20) |

### Hoạt động · Sử dụng · Webhook

| Chi tiết ảnh | Phán quyết | Quyết định |
|---|---|---|
| Dải lọc gọn + bảng gỡ lỗi | THẬT, gần xong | **NHẬN** — chỉ chỉnh mật độ + mã màu trạng thái |
| Phân trang nhật ký | SUY RA ĐƯỢC (hiện `limit=100`, không phân trang) | **NHẬN, Đợt 4** |
| Biểu đồ 30 ngày ở Sử dụng | SUY RA ĐƯỢC (cùng bộ gom ngày) | **NHẬN, Đợt 3** |
| Vòng tròn tỉ lệ theo công cụ | SUY RA ĐƯỢC (`usage_lines` gom theo `tool`) | **NHẬN, Đợt 3** |
| Webhook "98,5% thành công (7 ngày)" | SUY RA ĐƯỢC (`WebhookDelivery.status` + `created_at`) | **NHẬN, Đợt 3** |
| Webhook "1.247 sự kiện (7 ngày)" | SUY RA ĐƯỢC (đếm delivery) | **NHẬN, Đợt 3** |

**Tổng kết ma trận:** 24 NHẬN · 3 SUY RA ĐƯỢC gom vào một đợt riêng ·
**5 TỪ CHỐI có lý do viết ra** · 2 HOÃN.

---

## 5. Kế hoạch thi hành — sáu đợt

Nguyên tắc xuyên suốt, thừa kế Prompt Pack: **không viết lại · không đổi hợp
đồng bảo mật · không bịa số · không tạo hệ thiết kế thứ hai · sửa nền trước,
sửa trang sau.**

### Đợt 0 — Chốt & dọn (≈ 2 giờ, không sửa runtime)

- Chép lại (không dựng lại) hợp đồng từ `01_LIVE_ROUTE_MAP.md` +
  `02_BEHAVIOR_AND_SECURITY_CONTRACT.md`, xác minh lại **32 route** và **12 mục
  trần** bằng `pytest tests/test_197* tests/test_300* tests/test_303*`.
- Quyết chỗ đặt đầu ra V3: **`docs/developer_portal_mvp_ui/dot2/`**. Lý do ở §6.
- Chốt danh sách **TỪ CHỐI** (5 mục ở §4) vào `dot2/00_FREEZE.md` *trước khi
  code*, để không ai "làm nốt cho giống ảnh" ở đợt sau.

**Cổng ra:** 3 tệp test xanh · `dot2/00_FREEZE.md` tồn tại.

### Đợt 1 — Token + vỏ (≈ 1 ngày, CSS + `developers_base.html`, **không đổi nội dung trang**)

| Việc | Tệp |
|---|---|
| Họ token vận hành `--dev-cyan / -soft / -line / -hover`, và trung tính hoá viền **chỉ trong khu API** | `ltt.css` (khối `.dev-*` cuối tệp) |
| `.dev-topbar` — liên kết phụ + viên trạng thái + chuông có số | `developers_base.html` + `ltt.css` |
| `.dev-dau` — đầu trang có ô hành động (`{% block dau_hanh_dong %}`) | `developers_base.html` |
| `.dev-luoi` / `.dev-luoi-2-1` — lưới nội dung 2 cột, gãy xuống 1 cột < 1024px | `ltt.css` |
| `.dev-sub` viên thuốc → tab gạch chân | `ltt.css` (giữ nguyên `aria-current`) |
| Thanh bên: khối thương hiệu, 10 biểu tượng SVG, `210px → 230px` | `developers_base.html`, `ltt.css` |
| `.chi-so` thêm ô biểu tượng + dòng biến thiên; trần 4 cột | `ltt.css` |

⚠️ **`.app-side` dùng chung khu VPS.** Đổi bề rộng phải chụp `/vps` +
`/vps/chi-tiet` trước/sau. Nếu lệch → đưa `230px` vào biến scoped cho
`.app-shell` trong khu API, không đổi giá trị chung.

**Cổng ra (BẮT BUỘC dừng nếu đỏ):** 16 trang × 6 khung, `.app-main@1920 ≥
1300px`, 0 tràn ngang, 0 lỗi console, và ảnh `/vps` **trùng khít** trước/sau.

### Đợt 2 — Bốn trang trục, chỉ dùng dữ liệu THẬT (≈ 2 ngày)

| Trang | Đổi gì |
|---|---|
| **overview** | 6→4 thẻ chỉ số · lưới 2 cột × 2 hàng · panel **Request gần đây** (`request_log.list_for(limit=5)`) · panel **Thông báo** (`notifications.list_for(limit=4)`) · **checklist 3 bước** từ `_overview_counts` |
| **cli** | bậc thang 4 bước · 2 cột (cấu hình \| chọn công cụ) · ô chọn công cụ thành lưới 2×3 · ô mã sắc teal |
| **keys** | đầu trang có nút `+ Tạo khóa mới` · biểu mẫu vào `<details>` · tab `?mode=live\|test` · chân bảng có tổng |
| **logs** | mật độ ô · mã trạng thái tô màu theo lớp (2xx/4xx/5xx) · `request_id` dùng `.dev-id` |

Sửa Python **chỉ** ở `server/routes/developer/`: thêm `rows`/`notifications`
vào ngữ cảnh overview, thêm tham số `mode` cho keys. **Không** chạm
`platform_core/public_api/*` ở đợt này.

**Cổng ra:** `test_301` (luồng lần đầu) + `test_303` xanh · chiều cao nội dung
overview @1920 ≥ 900px · ảnh chụp 4 trang.

### Đợt 3 — Ba phép tổng hợp + primitive biểu đồ (≈ 1,5 ngày, có sửa `platform_core`)

Đây là **đợt duy nhất** thêm mã miền, và nó thêm đúng ba hàm:

```python
platform_core/public_api/request_log.py
    daily(db, *, user_id, since, until) -> list[{date, requests, failures, credit}]

platform_core/public_api/usage.py
    by_tool(db, *, user_id, since, until) -> list[{tool, calls, credit}]

platform_core/public_api/webhooks.py   (hoặc module thống kê tương ứng)
    delivery_health(db, *, user_id, since) -> {sent, succeeded, rate}
```

Cộng **một** primitive vẽ:

```
server/templating.py   filter `duong_ke(diem, w, h)` → chuỗi `points` cho <polyline>
ltt.css                .dev-bieu-do (SVG nội tuyến, không thư viện, không JS)
```

Ba luật cứng của đợt này:

1. **Không có dữ liệu ⇒ hiện `.dev-trong`**, không vẽ đường phẳng, không nội suy.
   Một biểu đồ trống nói "chưa gọi lần nào" là đúng; một đường 0 nằm ngang thì
   trông như hệ thống hỏng.
2. **Mỗi hàm mới một test riêng** đặt cạnh test của module đó (`test_201` cho
   request log, `test_202` cho webhook, usage ở `test_203`) — kiểm cả ca rỗng.
3. **Không thư viện biểu đồ, không JS.** SVG sinh phía máy chủ. Tiền lệ:
   `nexus_download.html` đã dùng SVG nội tuyến.

**Cổng ra:** ba test mới xanh · biểu đồ ở overview/usage hiển thị đúng ở ca
rỗng, ca 1 ngày, ca 7 ngày.

### Đợt 4 — Mười hai trang còn lại + route con (≈ 2 ngày)

`tools · tool_detail · playground · pricing · docs · usage · webhooks ·
settings · privacy · projects · jobs · notifications · quickstart · log_detail`

Chỉ áp primitive của Đợt 1–3, **không phát minh thêm lớp**. Kiểm bắt buộc cho
mỗi route con: cùng vỏ · cha vẫn sáng · dải mục con đúng · deep link sống.

Trong đợt này làm nốt: phân trang nhật ký, badge thật cho thẻ công cụ, cột
kết quả của trang giá.

**Cổng ra:** `test_299` (đã dịch) + `test_302` + `test_300` xanh · 16 trang cùng
một ngôn ngữ hình.

### Đợt 5 — QA, hồi quy, đóng băng (≈ 1 ngày)

```powershell
python tools/dev_portal_harness.py --port 8101
playwright-cli -s=devui open "http://127.0.0.1:8101/?qa=dot2"
playwright-cli -s=devui --raw run-code --filename=tools/qa/dev_portal_qa.js
playwright-cli -s=devui --raw run-code --filename=tools/qa/dev_portal_golden.js
python tools/gate.py
```

- 16 trang × 6 khung (1920/1440/1280/1024/768/390).
- Hồi quy bảo mật: CSRF · sở hữu theo `user.id` · bí mật hiện một lần · thu
  hồi/xoay · scope · live/test · IP · chữ ký webhook · ranh giới riêng tư.
- i18n: chuỗi mới **thêm tay** vào `.po`, giữ LF, rồi `python tools/i18n.py
  bien-dich`. ⛔ đừng chạy `i18n.py trich`.
- Đóng băng: `dot2/10_FINAL.md` ghi **MVP PASS** / **PASS WITH DEFERRED** /
  **FAIL**. Không dùng chữ "gần xong".

**Sau deploy** (luật 5b của `CLAUDE.md`, đã trả giá một lần):
kiểm trên `https://app.lttstudios.com`, **không chỉ** `127.0.0.1:8100`;
và soi lại `/vps`, `/nexus`, `/kichban`, `/anhnoibo`.

---

## 6. Ghép Prompt Pack V3 vào thực tế kho

V3 giả định kho **chưa từng** làm Đợt 1. Ba điều chỉnh:

1. **Prompt 00 + 01 rút thành Đợt 0.** `01_LIVE_ROUTE_MAP.md` và
   `03_UI_ROOT_CAUSE_AUDIT.md` đã trả lời chúng, có số đo. Chạy lại nguyên văn
   là dựng lại tài liệu đã đúng — và tệ hơn, sinh **hai tệp cùng số** trong một
   thư mục.
2. **Đầu ra V3 đi vào `docs/developer_portal_mvp_ui/dot2/`.** Trùng số hiện
   hữu: V3 muốn `01_UI_AUDIT.md` (đã có `01_LIVE_ROUTE_MAP.md`), `02_`, `03_`,
   `04_`…`09_`, và `10_FINAL_MVP_REPORT.md` (đã có `09_FINAL_MVP_REPORT.md` +
   `10_DEVELOPER_UI_CONTRACT.md`). Chín va chạm.
3. **Prompt 03 (shell/primitives) = Đợt 1 ở đây; Prompt 04–08 = Đợt 2 + 4.**
   Thứ tự V3 giữ nguyên, chỉ chèn **Đợt 3** (tổng hợp dữ liệu) vào giữa — V3
   không có chỗ cho nó vì V3 giả định *mọi* biểu đồ là fake. Ở kho này thì
   không: bảng đã có cột và có index.

Điểm V3 **đúng và phải giữ nguyên**: cấm dùng ảnh làm nguồn tính năng · tách
batch bảo mật khỏi refactor cấu trúc · route con là bề mặt tương thích · mọi
thay đổi phải phục vụ một trong 4 Golden Outcome · bằng chứng trình duyệt
không thay được bằng test xanh.

---

## 7. Rủi ro đã biết

| # | Rủi ro | Chặn thế nào |
|---|---|---|
| 1 | `.app-side` đổi bề rộng làm vỡ khu VPS | chụp `/vps` trước/sau; lệch thì đưa vào biến scoped |
| 2 | Trung tính hoá viền rò ra ngoài khu API | mọi luật mới đặt dưới vỏ của khu API, **không** sửa `:root` |
| 3 | Đợt 3 chạm `platform_core` — tầng đang bán thật | ba hàm **chỉ đọc**, không viết; mỗi hàm một test; không đụng đường thi hành |
| 4 | Truy vấn gom ngày chậm khi log lớn | dùng index `ix_public_api_requests_owner_time` đã có; cửa sổ trần 30 ngày |
| 5 | Chuỗi mới làm hỏng `.po` | thêm tay + `read_po` để đếm, không `grep`, không `trich` |
| 6 | Cloudflare phục vụ `ltt.css` cũ | `asset_ver` là hash nội dung; kiểm trên URL công khai sau deploy |
| 7 | Phiên Claude khác cùng ghi kho | kiểm `git status` + `ListAgents` trước khi deploy; gate trên cây đứng yên (nhớ **Bẫy 15**) |
| 8 | Đợt sau "làm nốt cho giống ảnh" | `dot2/00_FREEZE.md` viết 5 mục TỪ CHỐI kèm lý do, viết **trước** khi code |

---

## 8. Ước lượng

| Đợt | Công | Chạm `platform_core`? | Chạm Python khu API? |
|---|---|---|---|
| 0 chốt & dọn | 2 giờ | không | không |
| 1 token + vỏ | 1 ngày | không | 1 tệp (`developers_base.html`) |
| 2 bốn trang trục | 2 ngày | không | có (ngữ cảnh + 1 tham số) |
| 3 tổng hợp + biểu đồ | 1,5 ngày | **có** (3 hàm chỉ đọc) | có |
| 4 mười hai trang còn lại | 2 ngày | không | ít |
| 5 QA + đóng băng | 1 ngày | không | không |
| | **≈ 8 ngày** | | |

**Cắt được ở đâu nếu cần gấp:** Đợt 0 + 1 + 2 (≈ 3,5 ngày) đã lấy ~70% khác
biệt thị giác so với ảnh, và **không chạm một dòng nào của `platform_core`**.
Đợt 3 là phần đắt nhất và cũng là phần duy nhất có rủi ro chạm tầng đang bán.
