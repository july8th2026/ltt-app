# 05 — Page + Danger Contract Matrix

MODE: CONTRACT FREEZE. Prerequisites: `01`–`04`.

Đây là hợp đồng mà **mỗi lô của pha C phải đọc trước khi viết dòng đầu tiên**.
Cột "Cấm" quan trọng ngang cột "Có".

---

## PHẦN I — Nguồn dữ liệu được phép (authority)

Chốt trước, vì mọi thứ khác dựa vào nó.

| Read-model | Trả về gì | Dùng cho trang |
|---|---|---|
| `billing.doanh_thu(db)` (`billing.py:173`) | **đúng 3 số**: `vnd`, `credits`, `orders` — không có cửa sổ thời gian | Finance Overview |
| `billing.liet_ke_don(db, user_id=, status=, limit=)` (`:163`) | danh sách đơn | Orders, Customer 360 |
| `billing.lay_don_theo_code(db, code)` (`:157`) | một đơn | Orders |
| `credit.so_du(db, uid)` · `credit.tim_theo_email(db, q)` | số dư, tra khách | Customers, Customer 360, ô tìm topbar |
| `public_api.admin_console.overview(db, hours=24)` (`:108`) | accounts_with_keys · keys{total,live,test,revoked} · projects_active · requests_recorded · requests_failed · failures_by_code · jobs{succeeded,failed} · credit{held,settled,refunded,net_charged} · webhooks{subscriptions,pending,dead} | API Overview, Admin Overview |
| `admin_console.accounts_page` · `keys_page` · `key_usage` · `tools_page` · `jobs_by_tool` · `requests_page` · `jobs_page` · `failing_webhooks` | phân trang có lọc | API Access/Operations |
| `admin_console.disable_key/enable_key/revoke_key(reason=)` (`:389–436`) | **reason bắt buộc** (`_require_reason:436`) | API Access |
| `public_api.policy` · `pricing` · `costing` · `security_log` | policy/kill-switch/giá/margin/sự kiện bảo mật | Governance, Economics, Operations |
| ORM thô (`Job`, `DbSession`, `AppAccess`, `NhatKyAdmin`, `ApiKey`) | – | Customer 360, Vận hành, Hệ thống |

### 🔴 Ghi chú authority quan trọng nhất

`admin_console.py:143–145` (nguyên văn trong mã):
> *"Only failures and non-GET calls are recorded (EXT-09), so this is a failure
> count over recorded traffic — not over all traffic."*

⇒ Nền tảng **không ghi mọi request**. Do đó **không tồn tại**: tổng số request,
tỉ lệ lỗi, error rate, uptime, "độ tin cậy hệ thống %", P95 latency.
Ảnh mockup có cả sáu. **Cả sáu đều bị cấm.**

---

## PHẦN II — Hợp đồng 10 page family

Mỗi trang: câu hỏi vận hành · thực thể · authority · chỉ số cho phép · lọc ·
hành động · điều hướng · trạng thái · **cấm**.

---

### P1 — Admin Overview · `/admin/`

| | |
|---|---|
| **Câu hỏi** | "Việc gì cần tôi ngay bây giờ?" |
| **Authority** | `admin_console.overview()`, `Job` (status=error), `billing.liet_ke_don(status=pending/failed)`, `NhatKyAdmin` gần nhất, `ApiKey` (status≠active) |
| **Chỉ số cho phép** (≤6 ô) | job lỗi (cửa sổ) · đơn chờ/lỗi · request lỗi ghi được · webhook dead · provider key không hoạt động · kill switch đang bật |
| **Khối chính** | Hàng đợi chú ý · Hoạt động admin gần đây (`NhatKyAdmin`) · Ảnh chụp vận hành |
| **Luật deep-link** | **Mọi mục trong Hàng đợi chú ý phải mở đúng trang giải quyết được nó**, kèm bộ lọc đã đặt sẵn |
| **Trạng thái** | khoẻ (hàng đợi rỗng) · có chú ý · rỗng hoàn toàn (hệ mới) · một nguồn không đọc được → ô đó ghi "không lấy được", **không** hiện 0 |
| **CẤM** | uptime · SLA · % độ tin cậy · biểu đồ xu hướng · so-với-hôm-qua · số worker · Redis/S3 · môi trường "Production" · chuông thông báo có số |

---

### P2 — Customers List · `/admin/khach-hang`

| | |
|---|---|
| **Câu hỏi** | "Tìm khách tôi cần hỗ trợ." |
| **Thực thể** | `User` (+ số dư từ `credit.so_du`) |
| **Cột cho phép** | email · User ID · số dư (**credit**) · vai trò · đang hoạt động · đã xác thực · tạo lúc · đăng nhập cuối |
| **Lọc** | tìm email/ID · trạng thái hoạt động · đã/chưa xác thực |
| **Hành động chính** | **Mở Hồ sơ 360** |
| **Danger trong bảng** | **không có** — không đặt mutation trong bảng danh sách |
| **Trạng thái** | có dữ liệu · không tìm thấy · trang nhiều · email rất dài (phải cắt bằng ellipsis, không tràn) |
| **CẤM** | **gói dịch vụ Starter/Pro/Business** · ảnh đại diện · số điện thoại · quốc gia · KYC · ticket hỗ trợ · "khách cần hỗ trợ" · %so-với-tháng-qua |

⚠️ Rail "cần chú ý" chỉ được có nếu tín hiệu **đơn định**: tài khoản bị vô hiệu
hoá, số dư âm, chưa xác thực email. Không có "nợ quá hạn" (không có công nợ),
không có "sắp hết hạn gói" (không có gói).

---

### P3 — Customer 360 · `/admin/nguoi-dung?q=`

| | |
|---|---|
| **Câu hỏi** | "Khách này đang thế nào, và tôi làm gì được an toàn?" |
| **Khối live-backed** | Danh tính/tài khoản · Số dư + bút toán gần nhất · Job gần nhất · Đơn nạp gần nhất · Phiên đang mở · Quyền app (`AppAccess`) · Ngữ cảnh API nếu khách có khoá · Nhật ký admin về khách này |
| **Hành động** | Cấp credit (D) · Thu hồi phiên (D) · Mở đơn · Mở job · Mở ngữ cảnh API |
| **Nhóm danger** | **Không dồn mọi nút đỏ vào một thanh.** Hành động đọc/điều hướng ở đầu; hành động SENSITIVE/DANGEROUS ở một khối riêng cuối trang, có nhãn |
| **Cross-link** | không có luồng copy UUID bằng tay ở bất kỳ đâu |
| **Trạng thái** | chưa nhập tìm kiếm · không tìm thấy (404) · khách mới chưa có gì · khách nhiều dữ liệu |
| **CẤM** | ngày sinh · SĐT · địa chỉ · quốc gia · KYC · ảnh đại diện · ghi chú hỗ trợ · gói/gia hạn · success rate · rate limit · vị trí địa lý của phiên |

Cơ sở: `ChiTietNguoiDungView` (`admin.py:204`) đã có 5/8 khối. Đây là **mở rộng**,
không phải trang mới.

---

### P4 — Finance Overview · `/admin/doanh-thu`

| | |
|---|---|
| **Câu hỏi** | "Dòng tiền có ổn không, và đơn nào cần xử?" |
| **Chỉ số cho phép** | **đúng 3**: tổng VND đã thu · credit đã bán · số đơn đã trả (`billing.doanh_thu`). Cộng: số đơn pending, số đơn failed/expired |
| **Khối** | 3 ô số · đơn cần xử lý · đơn đã trả gần đây · hành động tài chính gần đây (`NhatKyAdmin` lọc theo hành động tiền) · link sang Đơn hàng / Sổ credit |
| **Đơn vị** | VND ghi `đ`; credit ghi `credit`. **Không ô nào trộn** |
| **Trạng thái** | chưa có đơn · có đơn · có pending · có failed |
| **CẤM** | biểu đồ xu hướng theo giờ · donut theo kênh (**VNPay/MoMo/thẻ/chuyển khoản không tồn tại — chỉ có PayOS**) · "anomalies" · "đối soát ngân hàng" · "sức khoẻ tài chính" · "hiệu suất gói dịch vụ" · bộ chọn khoảng ngày (`doanh_thu()` không nhận cửa sổ) |

---

### P5 — Orders & Credit Ledger · `/admin/don` + `/admin/credit-entry/list`

| | |
|---|---|
| **Câu hỏi** | "Đơn này ra sao?" / "Cái gì làm đổi credit của khách?" |
| **Orders — lọc** | trạng thái · mã đơn · user · (gateway nếu có giá trị thật) |
| **Orders — danger** | **mark-paid** = DANGEROUS. Phải: nhãn *"đường dự phòng khi cổng không callback"* · xác nhận · CSRF · phản hồi thành công/thất bại rõ |
| **Ledger** | **chỉ đọc**. Không nút tạo/sửa/xoá. Dùng `credit-entry/list` của SQLAdmin (đã `can_create/edit/delete = False`) |
| **Cross-link** | Đơn → khách · Đơn → bút toán sinh ra · Bút toán → khách · Bút toán → job/đơn khi có quan hệ. Đặt trong Hồ sơ 360 và trang Đơn |
| **CẤM** | gộp dòng đơn và dòng bút toán vào một model sửa được · cột "gói dịch vụ 30 ngày" · ảnh đại diện · nút sửa/xoá bút toán dưới bất kỳ hình thức nào |

---

### P6 — API Platform Overview + Access · `/admin/api-tong-quan`, `/admin/api-tai-khoan`, `/admin/api-khoa`

| | |
|---|---|
| **Chỉ số cho phép** | **đúng những khoá `overview()` trả về** (Phần I) — không thêm một số nào |
| **Access** | tài khoản API · khoá của khách (live/test/revoked) · project |
| **Secret** | khoá khách hiện **masked**; không "reveal lại" (backend không tái tạo được) |
| **Ranh giới** | **Provider credentials KHÔNG xuất hiện ở đây.** Chúng ở Vận hành |
| **Cross-link** | tài khoản API → Customer 360 · khoá → tài khoản · lỗi → Operations |
| **Trạng thái** | API tắt · chưa ai có khoá · khoá đã thu hồi/hết hạn |
| **CẤM** | tổng request · error rate · uptime · "độ tin cậy hệ thống %" · P95 · dãy toggle *Rate Limit Shield / IP Reputation Filter / Schema Strict Mode / Anomaly Auto Block* (không tồn tại) |

---

### P7 — API Governance · `/admin/api-cong-cu`, `/api-chinh-sach`, `/api-kill-switch`

| | |
|---|---|
| **Câu hỏi** | "Cái gì được chạy, dưới hạn mức nào, và dừng thế nào khi có sự cố?" |
| **Nhóm** | Công cụ/khả năng · Chính sách/hạn mức · Kiểm soát khẩn cấp |
| **Kill switch** | scope · subject · **lý do BẮT BUỘC** · hạn hiệu lực · audit · CSRF · xác nhận tường minh |
| 🔴 **Luật cứng** | **Không được biến kill switch thành toggle một cú bấm.** `policy.py:428` và `tables.py:618` bắt `reason` không rỗng ở tầng service — một toggle không có ô lý do sẽ **luôn lỗi**, và ảnh mockup vẽ đúng như vậy (ba switch, ba dòng "Lý do —" trống) |
| **Chính sách** | hiện policy hiệu lực + nguồn/gán nếu service hỗ trợ |
| **Ranh giới** | **Giá KHÔNG thuộc Governance** — ở Economics |
| **CẤM** | panel "Uptime SLA 99.9% · Hỗ trợ 24/7 · Hạ tầng NVMe Enterprise" · quy tắc bảo mật không có backend (IP Whitelist, DDoS Protection, Anomaly Detection…) trừ khi chứng minh được service thật |

---

### P8 — API Operations · `/admin/api-request`, `/api-job`, `/api-bao-mat`, `/api-trace`

| | |
|---|---|
| **Câu hỏi** | "Vì sao tích hợp này hỏng?" |
| **Dòng chảy** | Request → API job → sự kiện lỗi/bảo mật → trace/ngữ cảnh |
| **Trường cho phép** | chỉ metadata log thật đang lưu: request id · user/account · route/tool · HTTP status · error code · thời gian · quan hệ credit/job · quan hệ webhook |
| **Trace** | là thao tác **theo ngữ cảnh**, không phải mục sidebar |
| **Bảo mật** | sự kiện bảo mật tách khỏi nhật ký request thường |
| 🔴 **CẤM** | **thêm lưu raw request/response payload để chiều mockup** · nút "Xem payload" · export cURL dựng lại body · tổng request · error rate |

---

### P9 — Provider Operations · `/admin/apikeys`

| | |
|---|---|
| **Mô hình** | Đây là hạ tầng provider của **NỀN TẢNG**. Nhãn: `Provider Credentials`, **không** phải "APIKEYS" chung chung (`02` A-04) |
| **Năng lực giữ nguyên** | provider · preview credential · category · status · health · priority · RPM/token · models · test · refresh · enable/disable/reset · thêm/sửa credential |
| **Secret** | không bao giờ plaintext, không bao giờ log plaintext. `credential_enc` không vào form |
| **Ba lớp phải tách rõ** | ① registry provider/model (`platform_core/providers.py`) ② model phát hiện được khi chạy ③ `supported_models` của từng khoá |
| **Cross-link** | provider/khoá lỗi → API Operations / ngữ cảnh Job |
| **CẤM** | provider không có trong registry (**Azure OpenAI, Anthropic** — registry thật: gemini, apiai, cheapkeyai, byteplus, plenx) · "Routing %" · "trạng thái đồng bộ provider" · uptime/health % bịa · "đội ngũ hỗ trợ 24/7" |

---

### P10 — System + Data Explorer · `/status`, `/admin/nhat-ky-admin/list`, `/admin/nang-cao`

| | |
|---|---|
| **System** | chỉ sự thật vận hành có nguồn: trạng thái dịch vụ từ `/status` · `PlatformInfo` · cảnh báo cấu hình nếu có nguồn thật |
| **Data Explorer** | 5 bảng thô SQLAdmin (`user`, `session`, `app-access`, `api-key`, `platform-info`) + đường tới 3 bảng đã lên subnav |
| **Kiểm secret bắt buộc** | rà **mọi** ModelView: không `DbSession.id`, không `password_hash`, không `credential_enc`, không secret khách. (`01` §2 đã xác nhận đạt — phải giữ) |
| **UI** | SQLAdmin giữ bảng dày của nó; chỉ cần vỏ/ngữ cảnh cho thấy nó thuộc LTT Admin |
| **CẤM** | dựng bộ observability: uptime 30 ngày · P95 từng dịch vụ · Redis · Object Storage S3 · "Worker 32/32" · Queue depth · lịch bảo trì — **trừ khi** chỉ ra được nguồn thật |

---

## PHẦN III — Ma trận danger (11 POST + 4 thao tác SQLAdmin)

Mức: R · RW · S(ENSITIVE) · D(ANGEROUS).

| # | Hành động | Route/cơ chế | Mức | Xác nhận | Gõ để xác nhận | Lý do bắt buộc | CSRF | Audit | Idempotent | Hoàn tác |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Cấp credit | `POST /admin/grant-credit` | **D** | ✅ | ❌ | ⚠️ note hiện có | ✅ giữ | ✅ giữ | ❌ | ❌ (chỉ bù bằng bút toán ngược) |
| 2 | Mark-paid đơn | `POST /admin/don/action` | **D** | ✅ | ❌ | ❌ | ✅ giữ | ⚠️ **thiếu** (E-03) | ✅ (`billing.py:121`) | ❌ |
| 3 | Tạo/sửa gói nạp | `POST /admin/goi` | **S** | ✅ | ❌ | ❌ | ✅ giữ | ⚠️ thiếu | ❌ | ✅ (sửa lại) |
| 4 | Bật/tắt/xoá gói | `POST /admin/goi/action` | **S** | ✅ | ❌ | ❌ | ✅ giữ | ⚠️ thiếu | ❌ | ✅ |
| 5 | Thêm provider credential | `POST /admin/api-key-them` | **S** | ✅ | ❌ | ❌ | ✅ giữ | ⚠️ thiếu | ❌ | ✅ (xoá) |
| 6 | Sửa provider credential | `POST /admin/api-key-sua` | **S** | ✅ | ❌ | ❌ | ✅ giữ | ⚠️ thiếu | ❌ | ✅ |
| 7 | enable/disable/reset/xoá provider key | `POST /admin/api-key-action` | **D** | ✅ | ⚠️ chỉ cho **xoá** | ❌ | ✅ giữ | ⚠️ thiếu | ❌ | một phần |
| 8 | Revoke khoá API khách | `POST /admin/api-khoa-action` | **D** | ✅ | ❌ | ✅ (`_require_reason`) | ✅ giữ | ✅ giữ | ❌ | ❌ |
| 9 | Đổi policy/hạn mức | `POST /admin/api-chinh-sach-action` | **S** | ✅ | ❌ | theo service | ✅ giữ | ✅ giữ | ❌ | ✅ |
| 10 | Kill switch | `POST /admin/api-kill-switch-action` | **D** | ✅ | ❌ | ✅ **BẮT BUỘC** | ✅ giữ | ✅ giữ | ❌ | ✅ (tắt/hết hạn) |
| 11 | Publish/retire giá API | `POST /admin/api-gia-action` | **S** | ✅ | ❌ | theo service | ✅ giữ | ✅ giữ | ❌ | ✅ (bản mới) |
| 12 | Đổi vai trò / vô hiệu hoá tài khoản | SQLAdmin `user/edit` | **S** | sqladmin | ❌ | ❌ | ✅ | ✅ (`on_model_change:389`) | ❌ | ✅ |
| 13 | Thu hồi phiên | SQLAdmin `session/delete` + Hồ sơ 360 | **D** | ✅ | ❌ | ❌ | ✅ | ⚠️ thiếu | ✅ (đã xoá thì thôi) | ❌ |
| 14 | Sửa/xoá `ApiKey` thô | SQLAdmin `api-key/edit\|delete` | **S** | sqladmin | ❌ | ❌ | ✅ | ⚠️ thiếu | ❌ | một phần |
| 15 | Sửa/xoá `AppAccess` | SQLAdmin `app-access/*` | **S** | sqladmin | ❌ | ❌ | ✅ | ⚠️ thiếu | ❌ | ✅ |

### Luật đọc bảng này

**Cột "giữ" nghĩa là giữ.** Pha C không được nới lỏng bất kỳ ô ✅ nào.

**Ô ⚠️ là hiện trạng, không phải mục tiêu.** Chúng được ghi nhận ở `01` E-03.
Thêm audit cho 6 handler còn thiếu là **PROPOSAL**, thuộc `24_DEFERRED_POST_MVP.md`
— **không** làm trong pha C, vì phạm vi lô này là giao diện + bố cục danh mục.
Ngoại lệ duy nhất: nếu một trang đang viết lại **vốn đã** đi qua handler đó và
việc thêm một dòng `ghi_nhat_ky` không đổi luồng, thì được làm và phải ghi rõ.

**Không được đặt ra hành vi nghiêm hơn hoặc lỏng hơn** so với cột trên chỉ vì
mockup gợi ý. Ví dụ mockup vẽ kill switch là toggle → nếu làm theo, hành động sẽ
**luôn thất bại** ở `_require_reason`.

---

## PHẦN IV — Trạng thái bắt buộc cho mọi trang

Mỗi trang phải xử lý đủ **sáu**:

| Trạng thái | Yêu cầu |
|---|---|
| Có dữ liệu | bình thường |
| Rỗng | dùng `.dev-trong`, nói **vì sao rỗng** và **làm gì tiếp** |
| Lỗi tải | khối lỗi rõ, không sập cả trang |
| **Một nguồn không đọc được** | ô đó ghi "không lấy được"; **cấm** hiện `0` như thể là số thật |
| Thành công sau hành động | thông báo tường minh, nói rõ **cái gì đã đổi** |
| Thất bại sau hành động | nói lý do; không im lặng redirect |

---

## PHẦN V — Ràng buộc responsive

| Viewport | Yêu cầu |
|---|---|
| 1920 / 1440 | bố cục dày, tận dụng bề rộng |
| 1280 | rail phải xuống dưới hoặc ẩn |
| 1024 | 2 cột |
| 768 | 1 cột, thanh bên thành `.adm-mobilebar` (`admin.py:170`) |
| 390 | 1 cột; bảng cuộn ngang **trong khung của nó** |

⛔ Không `overflow-x:hidden` toàn site. Bảng rộng cuộn trong `.dev-bang`, **body
không bao giờ cuộn ngang**.

---

**STOP.** Bước tiếp: Pha B — `06_VISUAL_REFERENCE_CONTRACT.md`.
