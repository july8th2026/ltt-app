# 00 — Kế hoạch triển khai Admin Control Plane MVP V3

Nguồn: bộ prompt `G:\My Drive\AI\A\New folder (7)` (21 prompt + 8 tài liệu + 10 ảnh).
Tài liệu này là **phân tích bộ prompt đó đối chiếu với repo thật**, và là kế
hoạch thi hành. Đọc nó TRƯỚC khi chạy prompt 00.

Ngày lập: 2026-08-29. Nhánh lúc lập: `public-api-v2`.

---

## 1. Bộ prompt yêu cầu gì

Biến `/admin` từ **danh mục route** thành **control plane theo miền**.

| | |
|---|---|
| Sidebar đích | Tổng quan · Khách hàng · Tài chính · API Platform · Vận hành · Hệ thống |
| Page families | 10 (Overview, Customers, Customer 360, Finance, Orders+Ledger, API Overview/Access, API Governance, API Operations, Provider Ops, System+Explorer) |
| Golden Journeys | GJ1 hỗ trợ khách · GJ2 sửa tiền · GJ3 job hỏng · GJ4 sự cố API · GJ5 lỗi thanh toán · GJ6 sức khoẻ nền tảng |
| 4 pha | A đọc/kiến trúc (00–05) · B ảnh (06) · C thi hành (07–17) · D cổng phát hành (18–20) |
| Kết luận cho phép | `MVP PASS` · `MVP PASS WITH NON-BLOCKING DEFERRED` · `MVP FAIL` |

Ràng buộc cứng (17 điều "non-negotiable" lặp ở mọi prompt), tóm gọn: không rewrite
framework, không React SPA, không bỏ SQLAdmin, không đổi semantics nghiệp vụ để
khớp mockup, ledger vẫn append-only, mark-paid vẫn idempotent, không lộ secret,
không trộn Provider Credentials với Customer API Keys, **không fake metric**,
không xoá/làm yếu test, không `overflow-x:hidden` toàn site.

**Đánh giá:** bộ prompt tốt. Nó đã đoán trước đúng những cái bẫy mà ảnh mockup tạo
ra (prompt 14 nói thẳng "đừng biến kill switch có reason thành toggle một-cú-bấm").
Phần dưới chỉ là những chỗ nó **chưa biết về repo này**.

---

## 2. Đối chiếu repo thật — 11 phát hiện

### F1 (FACT) — Admin là 173 KB HTML dựng bằng f-string trong Python

`server/admin.py` 1.388 dòng / 75 KB · `server/admin_api.py` 1.897 dòng / 98 KB.
Vỏ trang do `server/admin.py:145 _admin_shell()` sinh chuỗi. `server/admin_templates/`
chỉ có `sqladmin/` — **không có một template Jinja nào cho trang admin tự viết**.

⇒ Đây là gốc của mọi thứ prompt 02 sẽ tìm thấy: trùng lặp vỏ/card/table, inline
style, không test được markup, không tái dùng được.

### F2 (FACT) — Sidebar là danh mục route, đúng như prompt 02 dự đoán

`server/admin.py:103 _ADM_NAV` = 13 mục + 4 nhóm, rồi `*_NAV_API` chèn thêm
**12 mục "API — …"** từ `server/admin_api.py:1883 NAV`.
⇒ **25 mục ngang cấp** trong một thanh bên. Trong đó `/admin/grant-credit` và
`/admin/api-kill-switch` là **trang hành động** nằm ở primary nav.

### F3 (FACT) — 19 view đăng ký, trộn hai loại

`server/admin.py:1364–1387`: 19 `add_view`. Trong đó 8 là `ModelView` (bảng thô:
User, CreditEntry, AppAccess, Job, Session, PlatformInfo, NhatKyAdmin, ApiKey) và
11 là `BaseView` (trang nghiệp vụ tự viết). Cộng `server/admin_api.py:1875 VIEWS`
= 12 view nữa. Tổng **31 `@expose`**, trong đó **11 handler POST** — đó chính là
"danger surface" mà prompt 05/18 phải liệt kê.

### F4 (FACT) — An toàn hiện có ĐÃ đúng, đừng đụng

- Audit: `server/admin.py:68 ghi_nhat_ky()` → bảng `NhatKyAdmin` (`platform_core/models.py:574`).
- CSRF: `server/auth/csrf.py` `issue_csrf_token` / `verify_csrf_token`, đã dùng ở
  các POST (vd `server/admin.py:522`, `:681`).
- Kill switch: `platform_core/public_api/policy.py:428` — **`reason` bắt buộc, kiểm
  ở service chứ không ở UI**; `public_api/tables.py:618` `reason` NOT NULL; có `expires_at`.
- Ledger: `CreditEntry` append-only; `PaymentOrder.credited` chỉ True một lần
  (`platform_core/billing.py`).

⇒ Guardrail trong `SOURCE_DERIVED_GUARDRAILS.md` **đã được xác minh đúng trên live
repo**. Prompt 01 chỉ cần trích dẫn, không cần điều tra lại từ đầu.

### F5 (FACT, QUAN TRỌNG NHẤT) — Repo ĐÃ làm đúng bài này một lần rồi, ở `/developers`

`docs/developer_portal_mvp_ui/` có đủ 11 tài liệu cùng khuôn (01 route map → 09
final report → 10 UI contract) + `dot2/` + `evidence/`. Sản phẩm của nó:

| Thứ bộ prompt yêu cầu | Đã tồn tại ở đâu |
|---|---|
| "một shared shell" (prompt 07) | `server/templates/developers_base.html` |
| "một registration/nav authority" (prompt 04) | `server/routes/developer/_chung.py:132` `SECTIONS` / `:176` `NHOM_NAV` / `:184` `CHA_CUA` / `:198` `MUC_CON` |
| AdminStat · AdminTable · AdminBadge · AdminEmptyState · AdminFilterBar · AdminFormField · AdminCard · AdminButton (prompt 07) | `.chi-so-luoi/.chi-so` · `.dev-bang` · `.dev-tt` · `.dev-trong` · `.dev-loc` · `.dev-field/.dev-hang` · `.card` · `.btn` — trong `server/static/ltt.css` + `server/templates/_kieu_chung.html` |
| "trần mục nav để không phình" (prompt 04) | `test_303` chốt trần 12 mục |
| "hợp đồng cho AI sau" (prompt 20) | `docs/developer_portal_mvp_ui/10_DEVELOPER_UI_CONTRACT.md` |

⛔ **Bộ prompt không biết chuyện này** — `SOURCE_DERIVED_GUARDRAILS.md` liệt kê
`server/admin.py`, `admin_api.py`, `public_api/*` nhưng **không nhắc `/developers`
một chữ nào**. Chạy prompt 04 và 07 nguyên văn thì Claude sẽ **thiết kế lại từ
đầu** một hợp đồng đăng ký và một bộ primitive đã có sẵn, đã có test, đã chạy
production.

⇒ **Sửa bắt buộc:** prompt 04 và 07 đổi từ *"thiết kế"* thành *"port khuôn
`/developers` sang `/admin`, và ghi rõ chỗ nào buộc phải khác vì sao"*.
Đây là khoản tiết kiệm lớn nhất của cả dự án.

### F6 (FACT) — Chỉ có 9/10 ảnh; ảnh thiếu đúng là ảnh của trang đầu tiên phải làm

`ChatGPT Image 20_57_41 27 thg 8, 2026 (1).png` **34 byte**, nội dung là
`{"detail":"Internal Server Error"}` — file hỏng lúc sinh, không phải ảnh.
Đối chiếu `IMAGE_REFERENCE_MANIFEST.md` với 9 ảnh còn lại:

| # Manifest | Trang | File thật |
|---|---|---|
| 01 | Admin Overview | 🔴 **KHÔNG CÓ** (file (1) hỏng) |
| 02 | Customers List | `(6).png` |
| 03 | Customer 360 | `(2).png` |
| 04 | Finance Overview | `(3).png` |
| 05 | Orders & Credit Ledger | `(4).png` |
| 06 | API Platform Overview | `(9).png` |
| 07 | API Governance | `(10).png` |
| 08 | API Operations | `(5).png` |
| 09 | Provider Operations | `(7).png` |
| 10 | System & Data Explorer | `(8).png` |

Tên file trong manifest (tiếng Việt, vd `bảng_điều_khiển_quản_trị_ltt_studios.png`)
**không khớp** tên file thật. Bảng trên là bản ánh xạ đã kiểm bằng mắt.

⇒ Prompt 08 (Admin Overview) mất reference. Xem §5.

### F7 (FACT) — Mockup bán một mô hình kinh doanh KHÁC với repo

Ảnh Customers List, Customer 360 và Orders đều có cột **"Gói dịch vụ:
Starter / Pro / Business — 30 ngày"**, "Gia hạn 23/06/2025 (còn 29 ngày)",
"Hiệu suất gói dịch vụ".

Repo **không có subscription**. `platform_core/models.py:753 PaymentOrder` có
`package_id` nhưng đó là **gói NẠP credit** (`price_vnd` + `credits` +
`bonus_percent`, chốt tại lúc tạo đơn), không phải bậc thuê bao.

⛔ Đây là cái bẫy nguy hiểm nhất trong bộ ảnh: nó **không trông giả**. Nó không
phải "uptime 99.99%", nó trông như một cột dữ liệu bình thường — nên người thi
hành sẽ thêm cột `plan` rồi bịa dữ liệu cho nó.

### F8 (FACT) — Danh sách nội dung trong ảnh KHÔNG có authority

Ngoài F7, đã soi từng ảnh:

| Ảnh | Nội dung không có nguồn dữ liệu thật |
|---|---|
| Customer 360 | ngày sinh · SĐT · địa chỉ · quốc gia · KYC level · "Support notes" · ảnh đại diện khách · success rate 99.91% · rate limit 600 req/phút · vị trí địa lý của phiên (Hà Nội/HCM) |
| Finance | donut **VNPay / MoMo / thẻ quốc tế / chuyển khoản** (repo chỉ PayOS) · "Anomalies phát hiện" · "Đối soát — khớp dữ liệu với ngân hàng" · "Sức khoẻ tài chính" · "Hiệu suất gói dịch vụ" |
| Orders | avatar khách · cột "Gói dịch vụ 30 ngày" |
| API Overview | "Độ tin cậy hệ thống 99.93%" · P95 từng dịch vụ · 6 toggle *Rate Limit Shield / IP Reputation Filter / Schema Strict Mode / Anomaly Auto Block* |
| API Governance | panel marketing "Uptime SLA 99.9% · Hỗ trợ 24/7 · Hạ tầng NVMe Enterprise" · kill switch vẽ thành **toggle không có ô lý do** |
| API Operations | "Xem payload" (repo **không lưu** raw request/response) · export cURL |
| Provider Ops | provider **Azure OpenAI / Anthropic** (repo: gemini, apiai, cheapkeyai, byteplus, plenx — `platform_core/providers.py:66`) · "Routing 32.4%" · "Trạng thái đồng bộ provider" |
| System | uptime 30 ngày 99.94% · "Worker 32/32" · Redis · Object Storage S3 · P95 từng dịch vụ · lịch bảo trì |
| Mọi ảnh | dropdown môi trường **"Production"** · chuông thông báo **8** · avatar admin · "support@lttstudios.com" · "docs.lttstudios.com" |

⇒ **Bắt buộc:** prompt 06 phải đẻ ra một **Sổ đăng ký nội dung cấm** dạng bảng, và
pha D phải có **test đọc bảng đó** rồi grep markup — giống cách `test_212` đọc
`APP_API_COVERAGE_FINAL.md` như dữ liệu.

### F9 (FACT) — Đơn vị tiền trong ảnh trộn credit với đồng

Ảnh Customer 360 ghi "Số dư credit **512.600 đ**"; ảnh Orders ghi "Số tiền
179.000 đ / Credits +179.000". Repo: **1 credit = 100 đ** (Q31), và `PaymentOrder`
tách hẳn `price_vnd` với `credits`.

⇒ Bê nguyên nhãn của ảnh vào là **sai số tiền hiển thị 100 lần**. Hợp đồng trang
(prompt 05) phải chốt: credit hiện bằng `credit`, tiền hiện bằng `đ`, không ô nào
trộn hai đơn vị.

### F10 (FACT) — Bề rộng đang khoá ở 1.180px, mockup vẽ ở ~1.600px + rail phải

`server/static/ltt.css:163` `.adm-content{padding:22px;max-width:1180px}`.
`ltt.css:139` `.adm-side{width:236px}`.
Còn `ltt.css:629` `.app-side{...210px}` — **dùng chung `/developers` và `/vps`**
(ghi rõ ở `docs/developer_portal_mvp_ui/10_DEVELOPER_UI_CONTRACT.md` §2).

⇒ Mọi trang trong ảnh là bố cục dày 3–4 cột + rail phải, không vừa 1.180px. Đây là
**quyết định phải chốt trước prompt 07**, không được để nó xảy ra như tác dụng
phụ. Và tuyệt đối không sửa `.app-side` để "cho giống ảnh".

### F11 (FACT) — Bối cảnh vận hành ràng buộc cách làm

- Máy này **là production** (`Test-Path C:\LTTPlatform`). `/admin` là công cụ hỗ
  trợ khách đang dùng thật; `LTT_PUBLIC_API_TOOLS=text.chat,image.ltt` đang thu
  tiền thật ⇒ hỏng admin = mất khả năng hỗ trợ, không phải "lỗi giao diện".
- Deploy **chép cả cây**, không tách được phần của một phiên ⇒ kiểm `git status`
  và hỏi phiên khác trước khi deploy.
- Đổi `ltt.css` **phải cache-bust**; admin đã có đường riêng
  `server/admin.py:135 _asset_ver()` → `server/templating.py ASSET_VER`. Giữ nó.
- Kiểm giao diện trên **URL công khai** `https://app.lttstudios.com`, không chỉ
  `127.0.0.1:8100` (CLAUDE.md quy tắc 5b).
- Nhánh hiện tại `public-api-v2` đang có sửa đổi chưa commit (`docs/NHAT_KY.md`,
  `docs/PUBLIC_API/CONTRACT_BASELINE.json`) + nhiều thư mục evidence chưa track.

---

## 3. Phải sửa bộ prompt trước khi chạy (5 điểm)

| # | Prompt | Sửa gì | Vì sao |
|---|---|---|---|
| S1 | 04 + 07 | Đổi mode từ "thiết kế hợp đồng mở rộng / dựng shell + primitive" → **"port khuôn `/developers`"**. Đọc bắt buộc: `docs/developer_portal_mvp_ui/10_DEVELOPER_UI_CONTRACT.md`, `server/routes/developer/_chung.py`, `server/templates/developers_base.html` | F5 — đã có sẵn, đã có test, đã chạy production |
| S2 | 01 | Thêm vào read set: `docs/developer_portal_mvp_ui/**`, `server/routes/developer/_chung.py`, `server/templates/developers_base.html`, `server/templates/_kieu_chung.html`, khối `.dev-*` + `.adm-*` trong `ltt.css` | Cùng lý do; để prompt 02 không kết luận "repo không có tiền lệ" |
| S3 | 06 | Bổ sung **bảng ánh xạ ảnh** ở F6 (tên manifest ≠ tên file), và bắt buộc đẻ ra **Sổ đăng ký nội dung cấm** dạng bảng máy đọc được | F6 + F8 |
| S4 | 08 | Ghi rõ: **không có ảnh reference cho Admin Overview**. Suy ngôn ngữ thị giác từ 9 ảnh còn lại; không được bịa rằng đã thấy ảnh | F6 |
| S5 | 18 + 19 | Thêm cổng thứ ba: **Data-truth gate** — test đọc Sổ đăng ký nội dung cấm và grep markup admin, đỏ nếu có chuỗi cấm (`Starter`/`Pro`/`Business` như bậc thuê bao, `VNPay`, `MoMo`, `SLA`, `uptime`, `KYC`, `Azure OpenAI`, `payload`…) | F7 + F8; bộ prompt cấm bằng lời nhưng không có cơ chế cưỡng chế |

Ngoài ra: bộ prompt viết *"cùng một Claude Code session nếu có thể"*. Với khối
lượng ở §4 điều đó **không khả thi**. Cơ chế bàn giao chính là các tài liệu pha A
(đó là lý do chúng phải xong trước) — cộng một `SESSION_LOG.md` cập nhật cuối mỗi phiên.

---

## 4. Kế hoạch thi hành

Quy ước mọi bước: theo **`docs/00_LTT_OPERATING_CONTRACT.md` §4** — vòng lặp là
`gate.py --doi`, đầy đủ trước khi báo xong một bước.

### Pha A — Đọc & kiến trúc (prompt 00–05) · READ ONLY

| Bước | Prompt | Ra tài liệu | Ghi chú riêng cho repo này |
|---|---|---|---|
| A1 | 00 | — | Chỉ nạp luật. Bổ sung 5 điểm sửa ở §3 |
| A2 | 01 | `01_LIVE_EVIDENCE.md` | Read set mở rộng theo S2. F3/F4 ở trên đã làm sẵn phần khung — trích dẫn, đừng điều tra lại |
| A3 | 02 | `02_DEEP_AUDIT.md` | Đã biết trước 3 finding P0/P1 chắc chắn: HTML f-string (F1), nav 25 mục (F2), trang hành động ở primary nav (F2) |
| A4 | 03 | `03_IA_FREEZE.md` | **Ma trận tương thích route là phần đắt nhất**: 31 `@expose` + 8 URL SQLAdmin `/admin/<model>/list` đều có thể đang nằm trong dấu trang của chủ sản phẩm. Không xoá URL nào |
| A5 | 04 | `04_EXTENSION_CONTRACT.md` | Theo S1: port `SECTIONS/NHOM_NAV/CHA_CUA/MUC_CON`. Kèm **trần mục sidebar** + test chốt trần (khuôn `test_303`) |
| A6 | 05 | `05_PAGE_CONTRACT_MATRIX.md` | Phân loại **11 POST handler** thành READ / REVERSIBLE_WRITE / SENSITIVE / DANGEROUS. Chốt đơn vị tiền theo F9 |

**Cổng ra pha A:** 5 tài liệu tồn tại; ma trận route cũ→mới **không có ô "xoá"**;
mọi POST đã có danger level. Chưa đụng một dòng runtime nào.

### Pha B — Ảnh (prompt 06) · VISUAL ONLY

Ra: `06_VISUAL_REFERENCE_CONTRACT.md` + **`06b_SO_DANG_KY_NOI_DUNG_CAM.md`**.

Tài liệu 06b là thứ bộ prompt gốc thiếu: bảng ba cột
`chuỗi/khái niệm cấm | vì sao không có authority | trang nào dễ mắc`. Nó là **dữ
liệu đầu vào của test** ở D1, không phải văn xuôi.

Ngôn ngữ thị giác rút từ 9 ảnh (đã soi): nền carbon gần đen, mặt phẳng thép xám,
đỏ LTT chỉ cho thương hiệu + phá huỷ, cyan/teal cho thông tin vận hành, xanh lá
khoẻ, hổ phách chú ý, đỏ lỗi; viền mảnh 1px; bảng dày, số căn phải dùng `tnum`;
badge trạng thái dạng viên thuốc có chấm màu; rail phải cho ngữ cảnh; card có
tiêu đề + icon nhỏ. Cái này **khớp** với `.dev-*` + biến màu đang có trong
`ltt.css` — nên là tinh chỉnh, không phải hệ thiết kế mới.

### Pha C — Thi hành (prompt 07–17)

**C0 (prompt 07) — nền móng. Bước quyết định cả dự án.**

Việc thật của C0, viết lại theo repo (thay mô tả generic của prompt 07):

1. Tạo `server/templates/admin_base.html` theo khuôn `developers_base.html`.
2. Tạo `server/routes/admin/_chung.py` giữ **một** nguồn nav
   (`SECTIONS/NHOM_NAV/CHA_CUA/MUC_CON`), thay `_ADM_NAV` + `admin_api.NAV`.
   `admin_api.NAV` **biến mất khỏi sidebar**; 12 mục API thành subnav của một mục
   `API Platform` (Overview/Access/Governance/Operations/Economics).
3. Quyết định bề rộng (F10): đề xuất thêm `page_mode` cho admin thay vì sửa
   `max-width:1180px` tại chỗ — vì `.adm-content` đang dùng cho **tất cả** trang admin.
4. Tái dùng primitive `.dev-*`; chỉ thêm lớp mới khi **≥ 3 trang** cần và không
   ghép được (luật §5 của hợp đồng `/developers`).
5. SQLAdmin: **không rewrite**. Chỉ cho nó đội cùng vỏ và đặt dưới
   `Hệ thống → Advanced / Data Explorer`.
6. Cổng nghiệm thu C0: render 4 trang đại diện (1 trang admin tự viết · 1 trang API
   admin · 1 trang tài chính · 1 bảng SQLAdmin thô) — cùng vỏ, nav active đúng,
   không lỗi route, không tràn ngang.

⛔ **C0 đỏ thì DỪNG.** Không đi tiếp sang C1. Prompt 07 nói điều này và nó đúng.

**C1–C10 (prompt 08–17) — mỗi trang một lô.**

Thứ tự đề xuất **khác** thứ tự trong `START_HERE.md`, vì rủi ro:

| Lô | Trang | Prompt | Vì sao đặt ở đây |
|---|---|---|---|
| C1 | Customers List | 09 | Ít nguy hiểm nhất, chứng minh khuôn bảng+lọc+phân trang |
| C2 | Customer 360 | 10 | GJ1. Trang có giá trị vận hành cao nhất |
| C3 | Orders & Credit Ledger | 12 | GJ2/GJ5. **Tiền** — làm sớm khi còn nhiều ngân sách kiểm |
| C4 | Finance Overview | 11 | Phụ thuộc C3 |
| C5 | API Overview + Access | 13 | Bắt đầu gom 12 mục API |
| C6 | API Operations | 15 | GJ3/GJ4 |
| C7 | API Governance | 14 | **Rủi ro cao nhất** — kill switch. Làm sau khi khuôn form nguy hiểm đã ổn ở C3 |
| C8 | Provider Operations | 16 | Tách hẳn khỏi Customer API Keys |
| C9 | System + Data Explorer | 17 | SQLAdmin hạ xuống Advanced |
| C10 | Admin Overview | 08 | **Làm CUỐI**, không phải đầu: nó chỉ là mặt tiền deep-link tới 9 trang kia; làm trước thì mọi link trỏ vào chỗ chưa có. Và nó là trang **mất ảnh reference** (F6) |

Mỗi lô cùng nhịp: đọc hợp đồng trang ở `05_PAGE_CONTRACT_MATRIX.md` → thi hành →
`gate.py --vong-lap` → kiểm trình duyệt trang đó ở 1920/1280/768/390 → ghi
`docs/admin_mvp_v3/<nn>_<TEN>.md` → **không sang lô sau nếu còn P0/P1**.

### Pha D — Cổng phát hành (prompt 18–20)

| Bước | Prompt | Nội dung | Ra tài liệu |
|---|---|---|---|
| D1 | 18 + S5 | Auth 3 vai · CSRF trên **cả 11 POST** · bất biến tiền (append-only, idempotent mark-paid, atomic grant) · bất biến secret · audit · **UX nguy hiểm: reason-required không được thành toggle** · **Data-truth gate** đọc `06b` | `18_SAFETY_GATE.md` |
| D2 | 19 | 10 page family × 6 viewport (1920/1440/1280/1024/768/390) × ma trận trạng thái. Playwright theo chính sách global. **Cả loopback lẫn `https://app.lttstudios.com`** (CLAUDE.md 5b) | `19_BROWSER_QA.md` |
| D3 | 20 | 6 Golden Journey đầu-tới-cuối + cổng kiến trúc/UI/an toàn/trình duyệt | `20_FINAL_MVP_REPORT.md` + `21_ADMIN_UI_CONTRACT.md` + `22_ADMIN_EXTENSION_CONTRACT.md` + `23_ROUTE_COMPATIBILITY.md` + `24_DEFERRED_POST_MVP.md` |

Trước D3: `python tools\gate.py` đầy đủ, xanh. Kết luận đúng **một** trong ba nhãn,
không có "gần xong".

### Ước lượng

| Pha | Khối lượng | Rủi ro |
|---|---|---|
| A (00–05) | 6 phiên đọc/viết, không sửa code | Thấp |
| B (06) | 1 phiên | Thấp |
| C0 (07) | **Nặng nhất.** Dựng vỏ + nav + port primitive + không vỡ 31 route | **Cao** — hỏng ở đây thì hỏng tất cả |
| C1–C10 | 10 lô, mỗi lô 1 trang + kiểm trình duyệt. Đây là nơi 173 KB f-string thành Jinja | Trung bình, tích luỹ |
| D | 3 cổng | Trung bình — D1 có thể bật ra P0 phải quay lại pha C |

---

## 5. Bốn việc cần chủ sản phẩm chốt TRƯỚC khi chạy prompt 00

1. **Ảnh Admin Overview bị hỏng (F6).** Sinh lại ảnh, hay chấp nhận làm trang
   Overview không có reference? — Khuyến nghị: **chấp nhận không có**, vì ảnh chỉ
   là north star và Overview làm cuối cùng (C10), lúc đó ngôn ngữ thị giác đã khoá
   từ 9 ảnh kia.

2. **Bề rộng admin (F10).** `.adm-content` đang 1.180px cho *mọi* trang admin;
   mockup cần ~1.600px + rail phải. Nới cho tất cả, hay thêm `page_mode` từng
   trang? — Khuyến nghị: **`page_mode` từng trang**, và **không đụng `.app-side`**
   (dùng chung `/developers` + `/vps`).

3. **Nhánh làm việc.** `public-api-v2` đang có thay đổi chưa commit và deploy chép
   cả cây. Nhánh mới `admin-mvp-v3` hay tiếp `public-api-v2`? — Khuyến nghị:
   **nhánh mới**, vì pha C đụng vào đường hỗ trợ khách đang chạy thật.

4. **Phạm vi Vận hành/Hệ thống.** Ảnh System + Provider Ops vẽ một bộ observability
   (uptime, P95, Redis, S3, sync status) mà repo không có. Xác nhận MVP này **chỉ
   hiển thị sự thật đang có**, mọi thứ còn lại vào `24_DEFERRED_POST_MVP.md` —
   chứ không phải một hạng mục xây thêm.

---

## 6. Điều dễ mắc nhất, viết một dòng

Bộ prompt bảo *"đừng fake metric"* — nhưng thứ trong ảnh dễ lọt nhất **không trông
giống metric**: nó là cột **"Gói dịch vụ: Starter / Pro / Business"** ở ba trang
khác nhau, cho một nền tảng bán credit chứ không bán thuê bao (F7).
