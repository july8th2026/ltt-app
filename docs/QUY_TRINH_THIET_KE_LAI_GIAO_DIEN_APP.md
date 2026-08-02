# Quy trình thiết kế lại giao diện app từ ảnh tham khảo

**Mã:** UI-RD v1.0 · **Chốt:** 2026-08-02 · **Phạm vi:** mọi app trong `apps/`

Ảnh tham khảo là **đích thị giác và nguồn giả thuyết tính năng**, không phải đặc
tả nghiệp vụ. Mọi nút nhìn thấy trong ảnh phải được phân loại và kiểm chứng với
code đang chạy. Không dựng nút giả; không suy từ ảnh tĩnh rằng backend, quyền,
credit, trạng thái lỗi hay dữ liệu đã tồn tại.

Nếu yêu cầu là chấm chất lượng toàn app, so sánh đối thủ hoặc xác định thiếu/thừa
tính năng, phải chạy LTT-AQA trong `docs/quy_tac_audit.md` trước. UI-RD nhận các
finding/quyết định đã khóa để thiết kế; không tự tạo một scorecard audit thứ hai.

Ưu tiên khi có xung đột: (1) an toàn/ownership/credit/contract; (2) giá trị thật
cho app; (3) bố cục và hành vi giống ảnh; (4) trang trí/pixel. Giữ nhận diện LTT
và trạng thái vận hành thật. Asset do người dùng/ChatGPT tạo có thể dùng; asset
thiếu được tạo mới, không lấy logo/hình độc quyền của sản phẩm khác.

## 1. Ba họ giao diện hiện có

| Họ | App tiêu biểu | Kiến trúc nên giữ |
|---|---|---|
| Form → báo giá → job → kết quả | thumbnail, taoanh, kichban, taovideo, autosubvideo, taoclipngan, upscalevideo | Jinja + HTMX/JS nhỏ; tái dùng jobs, credit, storage |
| Hội thoại streaming | chataistudio | Jinja shell + JS streaming; conversation theo tài khoản |
| Workspace/node editor | agent/canvas | React + TypeScript + `@xyflow/react`; FastAPI phục vụ bundle |

Header, tài khoản, credit, catalog và token là vỏ nền tảng. UI riêng phải scope
trong app; chỉ sửa shared shell khi yêu cầu thật sự áp dụng cho nhiều app và đã
được chốt thành hạng mục nền tảng.

## 2. Cách gọi quy trình về sau

Gửi `UI-RD <MODE> — app: <slug>` cùng ảnh desktop/mobile.

- `ANALYZE`: phân tích ảnh, audit app, lập hồ sơ; không sửa code.
- `BUILD`: ANALYZE → thiết kế → code → test local/staging.
- `FULL`: BUILD + chuẩn bị release. Chỉ deploy production khi câu lệnh ghi rõ
  `DEPLOY PRODUCTION`; không suy diễn production từ chữ “design”.

Nếu chỉ có tên app + ảnh, mặc định `ANALYZE`. Codex tự chọn phương án trong phạm
vi chế độ, không dừng xin duyệt mỗi phase. Chỉ dừng khi thiếu quyền/ảnh bắt buộc,
có nguy cơ mất dữ liệu, cần đổi contract nền tảng, hoặc hai cách hiểu tạo ra hai
sản phẩm khác nhau.

## 3. Hồ sơ bằng chứng mỗi app

Tạo `docs/UI_REDESIGN/<slug>/`:

1. `00_BRIEF.md`: mục tiêu, ảnh, viewport, luồng và phạm vi.
2. `01_CURRENT_STATE.md`: tính năng/hành vi đang có, kèm bằng chứng.
3. `02_REFERENCE_MAP.md`: giải phẫu ảnh, control và giả thuyết.
4. `03_FEATURE_MATRIX.md`: quyết định giữ/bỏ/mở rộng/xây.
5. `04_IMPLEMENTATION_PLAN.md`: phase, PASS gate, test và rollback.
6. `evidence/`: baseline và ảnh nghiệm thu desktop/mobile/state chính.

App nhỏ có thể gộp thành một file, nhưng không được thiếu loại bằng chứng.

## 4. Pipeline UI-RD R0–R10

### R0 — Intake và khóa baseline

Nhận app/ảnh; ghi kích thước/viewport; đọc nguồn chân lý, kế hoạch, hai nhật ký
mới, manifest/routes/templates/jobs/tests và `git status`. Chốt MODE và ranh giới
production. **PASS:** app/ảnh hợp lệ, biết ảnh mô tả màn hình và state nào. Thiếu
ảnh mobile thì ghi responsive là giả thuyết phải test, không nhận là thiết kế gốc.

### R1 — Audit code đến browser

Map đầy đủ:

`manifest → route/API → auth/CSRF/ownership → form/state → job/worker/provider → credit → storage/artifact → result/error/retry`.

Kiểm mọi state: loading, empty, validation/setup/credit error, queued, running,
done, failed, cancelled, retry, offline/conflict nếu có. Playwright desktop/mobile
phải ghi console, failed request, keyboard, `scrollWidth/clientWidth` và hình học
vùng chính. **PASS:** mỗi tính năng có bằng chứng code/test/browser; lỗi baseline
được ghi riêng, không che đi và không đổ cho redesign.

### R2 — Giải phẫu ảnh

Chia shell/header, toolbar, sidebar/palette, workspace/form/canvas, inspector,
history/result/artifact, modal/toast/status. Đo lưới/cột, tỷ lệ, spacing, alignment,
mật độ, type scale, màu, border/radius/shadow, icon/asset, CTA và breakpoint.
Tọa độ quan trọng ghi theo tỷ lệ ảnh, không khóa cứng một màn hình.

Mỗi control gắn độ chắc chắn: `V` nhìn thấy; `I` suy ra mạnh; `S` suy đoán. Không
biến `S` thành yêu cầu BUILD nếu chưa chứng minh giá trị và logic.

### R3 — Ma trận tính năng

Mẫu bắt buộc:

| ID | Bằng chứng ảnh | Hành vi kỳ vọng | Hiện trạng code | Quyết định | Lý do | Phụ thuộc/rủi ro | Acceptance |
|---|---|---|---|---|---|---|---|

Quyết định chỉ gồm:

- `KEEP`: có và phù hợp; `RESTYLE`: giữ hành vi, đổi trình bày;
- `EXTEND`: có một phần; `BUILD`: chưa có và đáng xây;
- `REJECT`: không phù hợp/xung đột/an toàn kém;
- `DECORATIVE`: chỉ thị giác, không hứa hành vi; `DEFER`: có giá trị nhưng chưa đủ.

Chấm 0–3 cho phù hợp app, giá trị, tái sử dụng nội tại, khả thi, doanh thu/chất
lượng; trừ bảo mật/privacy, giá provider, vận hành và nợ UX. Điểm không được vượt
ranh giới nền tảng. REJECT tính năng trùng, gây hiểu sai, để secret ở client, bỏ
ownership/CSRF/credit, phụ thuộc cookie/browser automation bị cấm. Giữ chức năng
an toàn/chi phí/artifact/error hiện có dù ảnh không vẽ.

### R3.5 — Decision Gate: Dev khóa logic trước BUILD

Sau mỗi lượt thu thập, phân tích và lập ma trận, Codex phải đưa ra **bảng câu hỏi
có phương án, khuyến nghị và hệ quả** cho Dev chọn. Các câu hỏi phải bao phủ ít
nhất: đối tượng/trạng thái màn hình, phạm vi tính năng, dữ liệu thật hay không,
nhóm feature BUILD/DEFER/REJECT, asset/nhận diện, responsive, quyền/credit và
rollout. Không được chuyển sang R4/R5/R7 chỉ vì ảnh trông rõ.

Mỗi lựa chọn được ghi vào `00_BRIEF.md` hoặc `04_IMPLEMENTATION_PLAN.md` với mã
quyết định, ngày, lý do và acceptance criteria. Quyết định làm thay đổi kiến trúc,
sản phẩm hoặc quy tắc nền tảng phải theo giao thức quyết định trong `AGENTS.md`.
Sau khi Dev trả lời, Codex tóm tắt logic đã khóa, cập nhật ma trận và mới bắt đầu
BUILD. Nếu Dev chọn phương án có dữ liệu/tính năng chưa tồn tại, R4 phải hoàn tất
contract và đường failure trước khi UI hiển thị control đó.

### R4 — Nghiên cứu EXTEND/BUILD

1. Viết Job Story và acceptance quan sát được.
2. Tìm nội tại trước: registry, ToolSpec, jobs, credit, provider, prompt, R2,
   storage, media/GPU, component và tests.
3. Chỉ nghiên cứu ngoài khi còn thiếu; ưu tiên tài liệu chính thức/nguồn gốc.
4. Chọn tool/provider theo quality, latency, giá/quota, license, privacy, fallback
   và testability.
5. Thiết kế API/data/state, quyền, rate limit, credit, failure, idempotency,
   retry, audit, observability và rollback.
6. Xây lát cắt backend thật trước khi bật control.

**PASS:** không nút chết; happy/failure path rõ; không tạo runtime/job/storage thứ
hai nếu năng lực hiện có có thể mở rộng additive.

### R5 — Design architecture và asset

Chuyển ảnh thành token/layout spec, không rải magic number. Chốt từng vùng khi
responsive: giữ, co, wrap, collapse, drawer, hide hoặc read-only; chốt focus order,
label, hit target, contrast và reduced motion.

Asset theo thứ tự: asset LTT → crop/biến thể từ ảnh tham khảo do user cấp quyền dùng
→ CSS/SVG/icon system → raster gốc bằng ImageGen khi thật sự cần minh họa/texture/cover.
Crop phải ghi nguồn, vùng cắt và mục đích trong hồ sơ; không được suy diễn quyền dùng
ảnh bên ngoài. Prompt asset (nếu đến bước ImageGen) phải ghi size, nền, palette, safe
area, mục đích; kiểm ở kích thước render. Không dùng ImageGen thay icon/SVG đơn giản.

### R6 — Prototype và visual target

Dựng grid/skeleton → component → typography/color/detail. Tạo target desktop,
mobile và state quan trọng; so overlay/diff rồi kiểm hierarchy thủ công. Pixel
score chỉ là tín hiệu vì font rendering khác hệ điều hành. **PASS:** vùng chính,
thứ tự đọc, tỷ lệ cột, CTA, mật độ giống mục tiêu; content dài/ngắn không vỡ và
không overflow ngoài chủ ý.

### R7 — Xây lát cắt dọc

Mỗi lát: contract/data → backend → frontend state → UI → test → browser. App
thường giữ Jinja/HTMX; React dành cho state phức tạp như Canvas. Không sửa core/
server để né contract; năng lực dùng chung phải thành quyết định nền tảng. **PASS:**
luồng dùng được đầu-cuối, không mock production, có test và rollback viết trước.

### R8 — Nghiệm thu

- Test app/regression rồi full `python -m pytest -q`.
- Secret scan, app contract lint; frontend typecheck/test/build/audit nếu có.
- Playwright 1440×900, 1280×800, 390×844 và 360×800.
- Happy/empty/loading/error/insufficient-credit/cancel/retry/upload/artifact.
- Keyboard/focus/label/contrast/reduced motion khi liên quan.
- Console 0 error; failed request 0 ngoài lỗi chủ động tái hiện.
- `scrollWidth <= clientWidth` nếu màn hình không chủ ý cuộn ngang.

Visual PASS theo checklist: cấu trúc ≥95%, spacing/sizing ≥90%, typography/color
≥90%, decoration ≥80%; usability/nghiệp vụ đạt 100% acceptance. Đây là checklist
có bằng chứng, không phải tuyên bố cảm tính hay pixel score.

### R9 — Release/rollout

BUILD dừng ở local/staging PASS. FULL chuẩn bị release, backup, migration và
rollback. Production chỉ khi được nêu rõ; sau đó canary/flag nếu rủi ro, smoke URL
công khai và console/network lần cuối. Không dùng dữ liệu thật nếu có thể dùng canary.

### R10 — Đóng vòng học

Mọi vấn đề mới đi qua:

`quan sát → bằng chứng → nguyên nhân gốc → phạm vi → sửa → regression → quy tắc`.

- Một app: hồ sơ + test app.
- Lặp từ hai app: component/token/check chung.
- Kiến trúc/sản phẩm: giao thức đổi quyết định trong `AGENTS.md`.
- Phương pháp UI-RD: thêm changelog, không sửa âm thầm làm mất lý do.

Chỉ nâng thành quy tắc chung khi tái hiện được hoặc nguyên nhân áp dụng rộng. Cuối
hạng mục cập nhật kế hoạch, nhật ký và commit.

## 5. Gate G0–G7

| Gate | Câu hỏi | Không PASS khi |
|---|---|---|
| G0 Scope | Đúng app/ảnh/mode? | đoán nhầm màn hình/state |
| G1 Truth | Có code + browser evidence? | chỉ nhìn ảnh/template |
| G2 Feature | Mọi control đã phân loại? | còn control mơ hồ |
| G3 Logic | Feature mới có data/API/quyền/credit/failure/rollback? | chỉ có UI |
| G4 Visual | Desktop/mobile/state đạt checklist? | overflow/vỡ hierarchy |
| G5 Quality | Test/scan/console/network xanh? | “trông có vẻ ổn” |
| G6 Ops | Release/rollback/monitor rõ? | production không đường lùi |
| G7 Memory | Hồ sơ/plan/log/decision/test đồng bộ? | hai nguồn chân lý |

Gate trước chưa PASS thì không tuyên bố phase sau hoàn thành.

## 6. Baseline ngày 2026-08-02

Playwright catalog production:

- desktop 1440×1000: header 56 px, page 1228 px, grid 3 cột ~383 px; console 0,
  failed request 0;
- mobile 390×844: nav thành burger nhưng page rộng 438 px, card rộng 390 px tại
  x=24 — overflow ngang; xử lý ở redesign shell/catalog, không phải lỗi lượt này;
- token: nền `#0f1115`, panel `#171a21`, accent `#3b6ef2`, radius 11 px.

Trang authenticated chưa khảo sát trong lượt này: canary dừng trước khi tạo user
do credential PostgreSQL cục bộ không khớp. Không sửa credential; code được đối
chiếu bằng routes/templates/tests. App đầu tiên phải baseline authenticated ở R1.

## 7. Changelog

| Phiên bản | Ngày | Thay đổi | Bằng chứng/lý do |
|---|---|---|---|
| 1.0 | 2026-08-02 | Pipeline R0–R10, matrix và G0–G7 | Chuẩn hóa thiết kế từ ảnh; Playwright bắt mobile overflow mà đọc CSS không đủ |
| 1.1 | 2026-08-02 | Thêm R3.5 Decision Gate | Dev yêu cầu khóa lựa chọn sau phân tích, trước khi triển khai |
| 1.2 | 2026-08-03 | Liên kết LTT-AQA làm lớp audit trước UI-RD | Tách đánh giá sản phẩm/thị trường khỏi triển khai thiết kế, giữ một nguồn scorecard |
