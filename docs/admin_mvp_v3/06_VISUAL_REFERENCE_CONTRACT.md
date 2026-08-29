# 06 — Visual Reference Contract

MODE: VISUAL ANALYSIS ONLY. Prerequisites: `01`–`05` đã tồn tại.

Ảnh là **north star thị giác**. Không được rút ra từ ảnh: tính năng, chỉ số,
quyền, route, SLA, uptime, cam kết hỗ trợ, danh mục provider/model, luật tài
chính, cách lộ secret. Danh sách cấm cụ thể ở `06b_SO_DANG_KY_NOI_DUNG_CAM.md`.

---

## 1. Bộ ảnh thực tế

Nguồn: `G:\My Drive\AI\A\New folder (7)`. Manifest ghi 10 ảnh với tên tiếng Việt
**không khớp** tên file thật. Bảng ánh xạ đã soi bằng mắt:

| Manifest | Trang | File thật | Hợp đồng liên quan |
|---|---|---|---|
| 01 | Admin Overview | 🔴 **KHÔNG CÓ** — `…(1).png` là 34 byte chứa `{"detail":"Internal Server Error"}` | P1 |
| 02 | Customers List | `…20_57_44 (6).png` | P2 |
| 03 | Customer 360 | `…20_57_42 (2).png` | P3 |
| 04 | Finance Overview | `…20_57_42 (3).png` | P4 |
| 05 | Orders & Credit Ledger | `…20_57_42 (4).png` | P5 |
| 06 | API Platform Overview | `…20_57_46 (9).png` | P6 |
| 07 | API Governance | `…20_57_47 (10).png` | P7 |
| 08 | API Operations | `…20_57_43 (5).png` | P8 |
| 09 | Provider Operations | `…20_57_44 (7).png` | P9 |
| 10 | System & Data Explorer | `…20_57_45 (8).png` | P10 |

### Xử lý ảnh thiếu (chốt theo chỉ đạo chủ sản phẩm)

**Không sinh lại.** Ngôn ngữ thị giác của Admin Overview **suy ra từ 9 ảnh còn
lại** cộng hệ token đang có. Cụ thể P1 mượn:
- lưới ô chỉ số ở đầu trang — từ ảnh 06 (API Overview) và 02 (Customers)
- danh sách "ưu tiên xử lý" có icon tròn + nhãn mức + dấu thời gian — từ ảnh 06
- dòng thời gian hoạt động ở rail phải — từ ảnh 07 (Governance)
- khối "sự cố & lỗi gần đây" có chip lọc — từ ảnh 10 (System)

⛔ Không được viết ở bất kỳ đâu rằng đã có ảnh tham chiếu cho Admin Overview.

---

## 2. Ngôn ngữ thị giác rút ra — và ánh xạ vào token đang có

Điểm mấu chốt: bảng màu mockup **đã là** `ltt.css:6–33`. Không cần token mới.

| Vai trò trong ảnh | Token có sẵn |
|---|---|
| nền carbon gần đen của trang | `--surface-canvas` `#08090a` |
| thanh bên / nền chìm | `--surface-base` `#0d0a0a` |
| mặt thẻ, hàng bảng | `--surface-raised` `#151111` |
| ô nhập, chip, hover | `--surface-overlay` `#1b1413` |
| viền mảnh 1px | `--border-subtle` `#382422` |
| viền nhấn | `--border-strong` `#63332e` |
| chữ chính / phụ / mờ | `--text-primary` / `--text-secondary` / `--text-muted` |
| đỏ LTT thương hiệu + phá huỷ | `--brand-primary` `#ef3731` |
| xanh lá "khoẻ / thành công" | `--status-success` `#62d889` |
| hổ phách "chú ý / chờ" | `--status-warning` `#efb84f` |
| đỏ "lỗi / nguy hiểm" | `--status-danger` `#ff6b63` |

**Một khác biệt duy nhất so với ảnh:** ảnh dùng cyan/tím/xanh dương cho một số
icon danh mục (ví/khoá/biểu đồ). Bộ token không có màu thông tin lạnh.
**Chốt: không thêm.** Lý do — thêm một họ màu thứ hai vào một hệ đang chỉ có
brand + 3 trạng thái sẽ làm màu mất nghĩa: người vận hành phải học "xanh dương
nghĩa là gì" trong khi xanh lá/hổ phách/đỏ đã có nghĩa rõ. Icon dùng
`--text-muted`, nhấn bằng `--brand-soft` khi cần.

---

## 3. Bố cục — cái phải áp dụng

### 3a. Vỏ

| Yếu tố | Ảnh | Áp dụng |
|---|---|---|
| Thanh bên | tối, sát mép trái, cao hết màn, thương hiệu ở đỉnh, mục có icon + nhãn, mục đang mở có nền sáng hơn + vạch đỏ trái | ✅ **đã có** `.adm-side` + `.adm-nav a.on` (`ltt.css:139–155`). Việc cần: đổi nội dung từ 25 mục phẳng → cây 2 cấp |
| Nút thu gọn thanh bên | "« Thu gọn" ở đáy | ⏭️ **hoãn** — thêm trạng thái phải nhớ; không thuộc MVP |
| Topbar | ô tìm ở giữa, chip môi trường, chuông, tài khoản | ⚠️ **áp dụng một phần**: chỉ ô tìm khách hàng + tài khoản. Chip "Production" và chuông có số → cấm (`06b`) |
| Tiêu đề trang | H1 + một dòng mô tả + vùng nút bên phải | ✅ áp dụng (chuẩn hoá `.pagehead` đang mỗi trang tự viết) |
| Breadcrumb | "Tài chính / Đơn hàng & sổ credit" (ảnh 05) | ✅ áp dụng, 2 cấp (`03` §5b) |
| Subnav | dải tab có icon (ảnh 06, 07, 10) | ✅ áp dụng bằng `.dev-sub` (`ltt.css:586–598`) |
| Rail phải | cột ngữ cảnh 300–360px (ảnh 02, 05, 07, 10) | ✅ áp dụng khi có nội dung thật; ẩn ≤1280 |
| Chân trang | giờ hệ thống · email hỗ trợ · link tài liệu | ⚠️ chỉ giữ giờ hệ thống; email/tài liệu → cấm nếu không có đích thật |

### 3b. Mật độ và nhịp

- Hàng bảng cao ~40–44px, padding ô ~`.58rem .75rem` — **trùng khớp** với
  `sqladmin/base.html:33` đang đặt. Giữ.
- Khoảng cách thẻ 14–16px; padding thẻ 16px.
- Tiêu đề cột: chữ nhỏ, in hoa, giãn chữ, màu mờ. Đã có (`sqladmin/base.html:32`).
- H1 ~24px, mô tả 13px màu phụ — trùng `.dev-h1`/`.dev-dan` (`ltt.css:599–601`).

### 3c. Ngữ pháp trạng thái (badge)

Ảnh dùng nhất quán: viên thuốc bo tròn, có **chấm màu** ở đầu, nền là biến thể
mờ của màu trạng thái, viền cùng tông.

✅ Đã có hai bộ: `.badge`+`.dot` (`admin.py:190` `_status_badge`) và `.dev-tt`
với `.ok/.canh/.loi/.tat`. **Chốt: dùng `.dev-tt`**, bỏ dần `.badge` — một ngữ
pháp, không hai.

Ánh xạ nghĩa (bắt buộc, không được đảo):

| Nghĩa | Lớp | Ví dụ |
|---|---|---|
| khoẻ / thành công / đang hoạt động | `.ok` | job done, đơn paid, key active |
| chờ / cần chú ý / suy giảm | `.canh` | đơn pending, key cooldown/exhausted |
| lỗi / nguy hiểm / bị thu hồi | `.loi` | job error, đơn failed, key error |
| đã tắt / không áp dụng | `.tat` | key disabled, gói inactive |

### 3d. Bảng

Áp dụng: cột số căn phải + `.tnum`; ID dùng `--mono` và cắt bằng `.dev-id`; cột
"Thao tác" cuối cùng; hàng có trạng thái xấu được đánh dấu bằng **vạch trái**
(ảnh 08 dùng vạch xanh/đỏ đầu hàng) chứ không tô nền cả hàng.

Không áp dụng: ảnh đại diện trong ô đầu (`06b`); menu `⋯` chứa hành động ẩn —
hành động nguy hiểm phải nhìn thấy được, không giấu sau ba chấm.

### 3e. Form và hành động nguy hiểm

Ảnh 07 vẽ kill switch là **toggle có ba dòng meta rỗng** ("Lý do —", "Hết hiệu
lực —", "Thực hiện bởi —").

🔴 **Đọc ngược lại:** ba dòng đó chính là **ba trường bắt buộc** mà backend đòi
(`policy.py:428` reason NOT NULL, `tables.py` `expires_at`, tác giả). Ảnh vẽ
chúng như **kết quả hiển thị**; ta phải làm chúng thành **đầu vào**.

⇒ Kill switch trong LTT Admin là một **form** có ô lý do bắt buộc + chọn hạn hiệu
lực + nút xác nhận, và sau khi bật thì hiển thị đúng ba dòng meta như ảnh.
Toggle trần = hành động luôn thất bại.

### 3f. Dòng thời gian / trace

Ảnh 08 (Trace Flow) và 07 (Nhật ký hoạt động) dùng cột dọc: chấm/icon tròn bên
trái, đường nối, nội dung bên phải, dấu thời gian bên phải cùng.
✅ Áp dụng cho: trace request, nhật ký admin, hoạt động của khách trong Hồ sơ 360.
⚠️ Nhãn "12 ms / 8 ms" giữa các bước chỉ hiện khi log thật có mốc thời gian từng
bước; nếu không thì bỏ nhãn, giữ khung.

---

## 4. Ánh xạ từng ảnh → adopt / reinterpret / must-not

| Ảnh | Adopt | Reinterpret | **Must NOT implement** |
|---|---|---|---|
| **02 Customers** | lưới 4 ô chỉ số; bảng dày; rail "cần chú ý"; chip trạng thái | rail chỉ nhận tín hiệu đơn định (`05` P2) | gói Starter/Pro/Business · avatar · "khách cần hỗ trợ" · %so-với-tháng · ticket |
| **03 Customer 360** | thẻ hồ sơ ngang ở đầu; lưới 8 thẻ theo chủ đề; hàng nút hành động; dải chân trang thông tin hệ thống | hàng nút **tách theo mức nguy hiểm** (`05` P3) | ngày sinh · SĐT · địa chỉ · quốc gia · KYC · ghi chú hỗ trợ · gói/gia hạn · success rate · rate limit · vị trí phiên |
| **04 Finance** | ô chỉ số có icon; bảng "cần xử lý" có nút hành động ngay trong hàng | chỉ 3 ô số thật + 2 ô đếm đơn | biểu đồ xu hướng · donut theo kênh · anomalies · đối soát ngân hàng · sức khoẻ tài chính · hiệu suất gói · bộ chọn ngày |
| **05 Orders + Ledger** | breadcrumb; dải lọc trên cùng; hai bảng xếp dọc; **rail phải giải thích bất biến tiền** (idempotent · audit · append-only) | rail đó là ý **rất tốt** — giữ, viết bằng sự thật của repo | cột gói dịch vụ · avatar · gộp hai bảng |
| **06 API Overview** | dải 8 ô chỉ số cuộn ngang; danh sách ưu tiên xử lý; subnav 5 tab | chỉ dùng khoá `overview()` trả về | tổng request · % độ tin cậy · P95 · biểu đồ lưu lượng · 6 toggle kiểm soát |
| **07 API Governance** | bố cục 3 khối (công cụ · chính sách · khẩn cấp); rail nhật ký hoạt động; khung viền màu theo mức nguy hiểm | switch → **form có lý do** (§3e) | panel SLA/24-7/NVMe · quy tắc bảo mật không có backend |
| **08 API Operations** | dải lọc nhiều trường; bảng request có vạch trạng thái trái; **ba khối dưới: chi tiết · trace · sự kiện bảo mật**; bảng xếp hạng lý do lỗi | "lý do lỗi phổ biến" = `failures_by_code` (có thật) | "Xem payload" · export cURL · tổng request |
| **09 Provider Ops** | bảng provider có thanh hạn mức; badge sức khoẻ; khối "model phát hiện được"; rail nhật ký vận hành | ba lớp registry/live/per-key tách rõ (`05` P9) | Azure OpenAI · Anthropic · Routing % · trạng thái đồng bộ · uptime · đội hỗ trợ 24/7 |
| **10 System + Explorer** | subnav 3 tab; chip lọc sự cố; **khối Data Explorer có tab theo bảng + nhãn `ADV`** | nhãn `ADV` là cách gọn để nói "khu nâng cao" — giữ | uptime 99.94% · Worker 32/32 · Redis · S3 · P95 từng dịch vụ · queue depth · lịch bảo trì |

---

## 5. Điều KHÔNG được đổi vì ảnh

1. `.app-side` 210px — dùng chung `/developers` + `/vps` (`01` §8).
2. Bộ token — ảnh đã khớp; thêm màu là làm loãng nghĩa (§2).
3. Ngữ nghĩa hành động — ảnh vẽ trạng thái sau, không vẽ ràng buộc trước (§3e).
4. Đơn vị tiền — ảnh trộn credit với `đ`; repo tách. Repo thắng (`05` P4).

---

## 6. Điều kiện ra

- [x] Ánh xạ 9 ảnh → 10 hợp đồng trang
- [x] Ảnh thiếu được xử lý tường minh, không giả vờ có
- [x] Mọi màu ánh xạ về token đang có, không token mới
- [x] `06b_SO_DANG_KY_NOI_DUNG_CAM.md` sinh ra ở dạng máy đọc được

---

**STOP.** Chưa implement UI. Bước tiếp: C0 — `07_FOUNDATION_IMPLEMENTATION.md`.
