# Quy tắc audit chất lượng app

**Mã:** LTT-AQA v1.0

**Chốt:** 2026-08-03

**Phạm vi:** mọi app và control plane trong `D:\LTTSTUDIOSAPP`

Đây là nguồn chuẩn cho việc đánh giá một app trước khi sửa, thiết kế lại, mở
rộng tính năng hoặc phát hành. Audit phải trả lời được bốn câu hỏi: app hiện tốt
đến đâu; so với thị trường đang thiếu/thừa gì; rủi ro nào chặn phát hành; nên đầu
tư hạng mục nào trước.

LTT-AQA đứng **trước** UI-RD. Audit xác định vấn đề và cơ hội; khi kết luận cần
thiết kế lại giao diện thì chuyển sang
`docs/QUY_TRINH_THIET_KE_LAI_GIAO_DIEN_APP.md`. Ảnh tham khảo là bằng chứng thị
giác và nguồn giả thuyết, không chứng minh backend hoặc tính năng tồn tại.

## 1. Cách gọi quy trình

Gửi `AUDIT <MODE> -- app: <slug>`; có thể kèm URL, ảnh và nhóm đối thủ.

| Mode | Phạm vi | Dùng khi |
|---|---|---|
| `QUICK` | Luồng lõi, code/browser, control và rủi ro nổi bật | Sàng lọc 2–4 giờ |
| `STANDARD` | Đủ A0–A10, 5–7 đối thủ, state và viewport chính | Mặc định, 1–2 ngày |
| `DEEP` | STANDARD + telemetry, tải/GPU, bảo mật sâu, trial đối thủ và user test | Trước major rebuild/commercial, 3–7 ngày |

Nếu chỉ có tên app, mặc định `STANDARD`, môi trường local/staging và dữ liệu
canary. Không chạm production nếu lệnh không ghi rõ. Audit chỉ đọc/kiểm tra;
không tự chuyển thành BUILD hoặc DEPLOY.

## 2. Dashboard kết quả bắt buộc

Không dùng một điểm tổng để che rủi ro. Báo cáo luôn có bốn kết quả độc lập:

1. **Quality Score (Q, 0–100):** chất lượng nội tại.
2. **Market Score (M, 0–100):** năng lực cạnh tranh theo cùng job-to-be-done.
3. **Evidence Confidence (E, 0–100):** độ chắc của kết luận.
4. **Release Gate:** `BLOCKED`, `INTERNAL`, `BETA`, `PUBLIC` hoặc `COMMERCIAL`.

Mẫu kết luận: `Q 78 · M 66 · E 91 · BLOCKED bởi G3 Credit`.

### 2.1 Thang điểm từng tiêu chí

| Điểm | Ý nghĩa |
|---:|---|
| 0 | Không có hoặc hỏng hoàn toàn |
| 1 | Có hình thức nhưng khó dùng, thiếu logic hoặc không an toàn |
| 2 | Hoạt động một phần, còn giới hạn đáng kể |
| 3 | Đạt baseline hợp lý của thị trường |
| 4 | Hoàn chỉnh, mạnh và cạnh tranh |
| 5 | Xuất sắc hoặc khác biệt có bằng chứng |

`Điểm nhóm = trung bình tiêu chí / 5 × trọng số nhóm`. Không thay trọng số sau
khi thấy kết quả. Xếp hạng Q: 90–100 hàng đầu; 80–89 mạnh; 70–79 cạnh tranh
nhưng còn gap; 60–69 có nợ sản phẩm; dưới 60 cần nâng cấp lớn. Gate có quyền
chặn release nhưng **không sửa giả điểm Q**.

## 3. Scorecard chất lượng 100 điểm

| Nhóm | Trọng số | Nội dung tối thiểu |
|---|---:|---|
| Giá trị sản phẩm/kết quả lõi | 15 | Persona, JTBD, task success, time-to-value, kết quả cuối |
| Tính năng và độ đầy đủ | 12 | Core/support, history, batch, import/export, empty/error state |
| Đúng chức năng và control | 12 | Form/nút/menu, state, validation, cancel/retry/undo, keyboard |
| UX/workflow/IA | 12 | Số bước, learnability, feedback, navigation, error prevention |
| UI/thẩm mỹ/design system | 8 | Hierarchy, density, spacing, type, color, icon, motion, brand |
| Responsive/accessibility | 7 | Viewport, focus, label, contrast, touch, screen reader |
| Hiệu năng/độ tin cậy | 9 | Load, latency, timeout, recovery, tải lớn, hàng đợi |
| AI output/provider economics | 8 | Quality, consistency, latency, cost, fallback, model routing |
| Security/privacy/tenant/credit | 10 | Auth, ownership, upload, secret, quote/hold/settle/refund |
| Kiến trúc/vận hành/quan sát | 7 | Test, log, metrics, alert, rollback, support, maintainability |
| **Tổng** | **100** | |

App không dùng AI phải phân bổ 8 điểm AI trước A0 và ghi lý do. Chuẩn tham chiếu
tối thiểu: WCAG 2.2 AA cho luồng lõi; Core Web Vitals tại percentile 75 với
LCP <= 2,5 giây, INP <= 200 ms, CLS <= 0,1; security control dựa OWASP ASVS.

## 4. Gate không được bù bằng điểm

| Gate | PASS khi |
|---|---|
| G0 Scope | Đúng app/version/persona/JTBD/môi trường/phạm vi dữ liệu |
| G1 Core Outcome | Luồng chính chạy đầu-cuối và tạo kết quả thật |
| G2 Security | Auth, tenant ownership, quyền, secret và privacy đúng |
| G3 Money/Credit | Quote/confirm/hold/settle/refund/idempotency đúng |
| G4 Honest UI | Không nút chết, CTA giả hoặc trạng thái gây hiểu nhầm |
| G5 Data Recovery | Không mất project/job; retry/resume/khôi phục rõ |
| G6 Accessibility | Core journey đạt baseline đã khóa |
| G7 Performance | Đạt budget latency/reliability đã khóa ở A0 |
| G8 Operations | Có log/metric/alert/runbook/rollback và release evidence |

Một gate FAIL phải ghi blocker, owner, cách tái hiện và điều kiện mở lại. P0 về
tiền, bảo mật, tenant, mất dữ liệu hoặc core outcome luôn chặn release.

## 5. Bằng chứng và độ tin cậy

| Cấp | Bằng chứng |
|---|---|
| E0 | Suy đoán, mockup hoặc ảnh tham khảo |
| E1 | Source code hoặc tài liệu |
| E2 | Unit/integration/API test đã chạy |
| E3 | Quan sát trên browser/render thật |
| E4 | Canary/production telemetry hoặc user test thật |

Mỗi finding phải gắn bằng chứng và ngày. E0/E1 không được gọi là “đã xác minh”.
Điểm E công bố riêng; không âm thầm nhân E vào Q. Công thức mặc định cho hồ sơ:
`E = tổng(trọng số tiêu chí × cấp bằng chứng / 4) / tổng trọng số`.

Browser evidence phải ghi viewport, state, console error, failed network request
và ảnh chụp khi liên quan. Không tuyên bố GUI PASS chỉ từ source hoặc `curl`.

## 6. Control Registry — audit mọi nút

Mỗi nút, link, menu, input, switch, slider, upload zone và shortcut phải map:

`screen → control → visible/enabled rule → role → action → API/workflow → credit
→ loading → success → error → cancel/retry/undo → keyboard/mobile → telemetry → evidence`.

Trạng thái chỉ gồm:

- `LIVE`: hoàn chỉnh; `PARTIAL`: hoạt động một phần; `BROKEN`: lỗi;
- `DEAD`: có UI nhưng không hành động; `MISLEADING`: hành vi khác kỳ vọng;
- `REDUNDANT`: trùng/không thêm giá trị; `MISSING`: luồng cần nhưng chưa có.

`DEAD`/`MISLEADING` trên luồng trả phí làm G3/G4 FAIL. Control nguy hiểm phải có
phòng ngừa lỗi, xác nhận hoặc undo phù hợp.

## 7. Audit UX/UI có thể kiểm chứng

Không chấm “đẹp” bằng sở thích cá nhân. Chấm riêng: bố cục/hierarchy; mật độ;
alignment/spacing; typography; color/contrast/state; component consistency;
icon/ảnh; độ rõ CTA; loading/empty/error/disabled/success; responsive; motion;
brand và mức phù hợp persona.

Kiểm theo nguyên tắc: trạng thái hệ thống rõ; ngôn ngữ gần người dùng; quyền
hủy/thoát; nhất quán; phòng ngừa lỗi; nhận biết thay vì ghi nhớ; hiệu quả cho cả
người mới/lâu năm; tối giản; thông báo lỗi có cách sửa; trợ giúp theo ngữ cảnh.

Mỗi nhận định phải có `state + viewport + bằng chứng + tiêu chí + ảnh hưởng JTBD
+ đề xuất kiểm thử lại`. Visual parity không được đánh đổi ownership, credit,
accessibility hoặc thông tin trạng thái thật.

## 8. Benchmark app trên thế giới

### 8.1 Chọn mẫu

STANDARD chọn 5–7 sản phẩm: 3 direct leaders, 1–2 innovator/adjacent, 1 low-cost
và 1 lựa chọn gần thị trường Việt Nam nếu có. Chọn theo cùng persona/JTBD/platform,
không chỉ vì UI giống. Ghi snapshot date, region, plan, device và nguồn.

Ưu tiên bằng chứng: hands-on/trial → official docs/release/pricing → demo chính
thức. Marketing claim không chứng minh chất lượng vận hành.

### 8.2 Ma trận thị trường

Phân capability thành:

- `TABLE_STAKES`: chuẩn tối thiểu để cạnh tranh;
- `DIFFERENTIATOR`: tạo kết quả tốt hơn/nhanh hơn/rẻ hơn;
- `NICHE`: giá trị cho nhóm nhỏ;
- `ANTI_FEATURE`: tăng phức tạp/rủi ro hơn giá trị;
- `DELIBERATE_OMISSION`: chủ động không xây và có lý do.

Chấm từng capability: 0 vắng; 1 yếu; 2 ngang chuẩn; 3 tốt hơn. Market Score dùng
70% table stakes + 30% differentiator, theo trọng số JTBD đã khóa; không đếm số
tính năng thô và không sao chép nhận diện/IP của đối thủ.

Quyết định cho LTT dùng chung ngôn ngữ UI-RD: `KEEP`, `FIX`, `RESTYLE`, `EXTEND`,
`BUILD`, `REJECT`, `DEFER`. Một tính năng chỉ BUILD khi có giá trị, khả thi,
contract/error/credit/ops rõ và không trùng năng lực nội tại.

## 9. Pipeline A0–A10

### A0 — Charter

Khóa app/version, persona, 3 JTBD chính, market/device, mode, môi trường, quyền
dữ liệu, benchmark set, trọng số, budget và ranh giới production. **PASS:** không
còn hai cách hiểu tạo ra hai sản phẩm khác nhau.

### A1 — Current Truth

Đọc nguồn chân lý, kế hoạch, nhật ký, manifest/routes/templates/frontend,
auth/ownership, job/worker/provider, credit, storage/artifact, tests và trạng
thái git. Tài liệu kế hoạch không chứng minh code đã chạy. **PASS:** truth map
đầu-cuối và dependency/rollback đã rõ.

### A2 — Journey & Control Inventory

Lập journey/state matrix và Control Registry; bao gồm happy, empty, validation,
setup, insufficient credit, queued/running/done/failed/cancel/retry, timeout,
offline/conflict và upload/artifact phù hợp. **PASS:** mọi control có verdict.

### A3 — Verification

Chạy test phù hợp và browser render thật ở desktop/mobile; xem console/network,
keyboard/focus, overflow, quyền, credit, tải lỗi/lớn và recovery. DEEP thêm load,
GPU/provider, security abuse và user task. **PASS:** finding tái hiện được.

### A4 — Market Benchmark

Khóa competitor set, thu evidence snapshot và lập capability matrix theo JTBD.
**PASS:** không so gói/region/use case lệch nhau; unknown vẫn ghi unknown.

### A5 — Scorecard

Chấm Q/M/E và G0–G8; mọi điểm có evidence ID. Hai người chấm lệch hơn 1 điểm
trên thang 0–5 phải thảo luận rubric, không lấy trung bình để che khác biệt.

### A6 — Finding & Root Cause

Mỗi finding ghi: `hiện tượng → bằng chứng → ảnh hưởng → root cause → severity
→ phạm vi → phương án → acceptance`. Severity: P0 critical; P1 lớn; P2 material;
P3 polish.

### A7 — Ba phương án

Luôn lập: `REPAIR` (đóng blocker/debt), `PARITY` (đạt chuẩn thị trường),
`DIFFERENTIATED` (lợi thế LTT). Chấm mỗi phương án theo giá trị, coverage,
rủi ro, time-to-value, chi phí, reuse và confidence. Mặc định ưu tiên lộ trình
ghép `Repair → Parity chọn lọc → Differentiation`, không build-all.

### A8 — Decision Gate

Trình Dev bảng câu hỏi/lựa chọn/khuyến nghị/hệ quả để khóa: scope, BUILD/DEFER/
REJECT, đối thủ, asset, responsive, credit/quyền, provider, rollout, acceptance
và rollback. Không chuyển audit thành code khi chưa khóa logic.

### A9 — Roadmap

Phase 0 gate blocker; Phase 1 core/table stakes; Phase 2 UX/UI/parity; Phase 3
differentiator; Phase 4 cost/performance/ops; Phase 5 release/production verify.
Mỗi phase có owner, dependency, test, PASS gate và rollback.

### A10 — Closed Loop

Đo trước/sau: task completion, time-to-first-result, error/retry, job success,
credit dispute/refund, cost/successful output, P50/P95, adoption/retention và
support rate. Vấn đề mới đi qua `evidence → root cause → fix → regression → rule`.

## 10. Ưu tiên nâng cấp

P0 không qua công thức. Hạng mục còn lại chấm 0–5:

`Opportunity = 30% user value + 20% frequency + 15% market gap + 15% revenue
+ 10% risk reduction + 10% confidence`.

`Delivery Priority = Opportunity / (Effort 1–5 × Dependency Risk 1–3)`.

Điểm cao không tự cấp quyền sửa core, dùng production data hoặc deploy; vẫn tuân
thủ ranh giới nền tảng và quyết định hiện hành.

## 11. Hồ sơ bắt buộc

Sao chép `docs/APP_AUDIT/_MAU/` thành
`docs/APP_AUDIT/<slug>/<YYYY-MM-DD>/`:

1. `00_AUDIT_CHARTER.md`
2. `01_CURRENT_TRUTH.md`
3. `02_JOURNEY_CONTROL_REGISTRY.md`
4. `03_COMPETITOR_BENCHMARK.md`
5. `04_SCORECARD.md`
6. `05_FINDINGS.md`
7. `06_OPTIONS_AND_DECISIONS.md`
8. `07_IMPLEMENTATION_ROADMAP.md`
9. `evidence/` cho ảnh, log đã lọc secret và kết quả máy đọc được.

QUICK được gộp file nhưng không bỏ Q/M/E/Gate/evidence. Audit chỉ hoàn thành khi
hồ sơ ghi rõ `đã chạy/chưa chạy`, unknown, blocker và ngày snapshot.

## 12. Changelog

| Version | Ngày | Thay đổi | Lý do |
|---|---|---|---|
| 1.0 | 2026-08-03 | LTT-AQA A0–A10, Q/M/E, G0–G8, Control Registry, benchmark và templates | Chuẩn hóa audit từ nội tại đến vị thế thế giới; tránh một điểm đẹp che lỗi critical |
