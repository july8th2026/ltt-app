# 05 — Findings: Upscale Video

## Summary

| Severity | Số lượng | Release impact |
|---|---:|---|
| P0 | 0 | Không có mất dữ liệu/tiền đang được chứng minh xảy ra tức thời |
| P1 | 2 | Chặn G2/G5/G8 và chặn release mới |
| P2 | 10 | Phải đóng trong Core/Parity trước COMMERCIAL |
| P3 | 4 | Tối ưu sau khi blocker đóng |

## P1

### F-001 — Presigned upload chưa có hàng rào size/type/quota/rate đủ mạnh

- Severity: **P1**
- Nhóm score/gate: Security/privacy; G2.
- Hiện tượng: user đăng nhập có thể gọi `/upload-url` nhiều lần với extension
  và content type tùy ý; route không verify CSRF, media allowlist, content length,
  quota hoặc rate. Presigned PUT không biểu diễn giới hạn 90MB của local path.
- Evidence IDs: EV-SRC-003.
- Cách tái hiện: đọc route và storage contract; ticket được cấp trước job/hold.
- Ảnh hưởng persona/JTBD: tăng chi phí R2, lưu payload không phải video, đường
  abuse không cần tạo job hoặc trả credit.
- Root cause: coi ticket như bước UI nội bộ thay vì resource-creation API.
- Phạm vi ảnh hưởng: browser direct upload và R2 bucket.
- Tính năng liên quan: upload lớn, batch, abandoned form.
- Phương án: CSRF + allowlist MIME/ext + policy size ký được + user quota +
  rate limit + upload session TTL; chỉ promote key vào namespace job sau submit.
- Acceptance: abuse cases sai MIME, >limit, quá quota/rate đều bị chặn; ticket
  hết hạn; key staging không được serve; regression owner/cross-tenant PASS.
- Regression cần thêm: route tests + staging presigned upload boundary.
- Owner/dependency: backend/storage/Cloudflare R2 policy.

### F-002 — Artifact upload mồ côi và retention không khép kín

- Severity: **P1**
- Nhóm score/gate: Data recovery/ops/credit; G5/G8.
- Hiện tượng: local/direct artifact được ghi trước `submit_upscale_batch()` giữ
  credit; khi thiếu credit/RegistryError, DB rollback nhưng blob không xóa. User
  upload direct rồi đóng tab cũng để key không gắn job. Policy H26 chỉ purge
  Job/JobEvent, chưa purge artifact.
- Evidence IDs: EV-SRC-003/005, U-03.
- Cách tái hiện: theo thứ tự `storage.put → submit → rollback`; không có `delete`
  trong failure path hoặc sweeper staging.
- Ảnh hưởng persona/JTBD: dữ liệu cá nhân tồn tại ngoài lịch sử/xóa dữ liệu;
  chi phí storage tăng; support không truy vết được ownership lifecycle.
- Root cause: atomicity chỉ khóa DB/credit, không có upload-session state machine.
- Phạm vi ảnh hưởng: single, batch, Watch và direct R2.
- Tính năng liên quan: insufficient credit, abandon, retry, retention.
- Phương án: staging key + upload session có owner/expiry; promote sau hold;
  `finally` cleanup; sweeper idempotent; retention artifact theo policy.
- Acceptance: mọi failure/abandon được dọn; active/job-owned artifact không bị
  xóa; dry-run/report, recovery và audit event có.
- Regression cần thêm: credit fail, partial batch, process crash, sweeper race.
- Owner/dependency: backend/storage/operator retention.

## P2

### F-003 — Engine chưa đạt table-stakes “enhance”, chỉ spatial upscale

- Severity: **P2**; nhóm: Core outcome/Market; G1 trước COMMERCIAL.
- Hiện tượng: Fast/Quality đều Real-ESRGAN frame-by-frame; chưa có temporal
  consistency, denoise, deblur/focus hay auto content preset.
- Evidence: EV-SRC-004, EV-MKT-001, EV-GPU-001/002.
- Ảnh hưởng: output có thể lớn hơn nhưng flicker/noise/blur vẫn thua leader.
- Root cause: AI Detail đã DEFER vì thiếu temporal engine.
- Phương án: benchmark BasicVSR++/provider phù hợp; chỉ lộ Auto/Fast/Quality và
  ba intent Detail/Denoise/Deblur, không lộ model dev.
- Acceptance: blind panel thắng baseline, flicker metric không xấu, cost/P95 rõ.
- Regression: golden clips theo animation/live/noise/motion.

### F-004 — Nhãn `PRO` không có entitlement thật

- Severity: **P2**; nhóm: Honest UI; G4.
- Hiện tượng: topbar hardcode `PRO` cho mọi user, không có contract plan/feature.
- Evidence: EV-SRC-002, EV-BR-001/002.
- Ảnh hưởng: gây hiểu nhầm đã mua Pro hoặc tính năng bị khóa.
- Root cause: copy từ mockup nhưng không nối entitlement.
- Phương án: bỏ badge; chỉ hiện khi backend truyền entitlement thật.
- Acceptance: anonymous/free không thấy Pro; plan thật có test quyền.

### F-005 — Customer copy lộ R2/CORS và giới hạn điều kiện sai ngữ cảnh

- Severity: **P2**; nhóm: UX/Honest UI; G4.
- Hiện tượng: dropzone nói “browser tối đa 90MB khi R2 CORS chưa được bật”.
- Evidence: EV-BR-001/002, EV-SRC-002.
- Ảnh hưởng: người không kỹ thuật không hiểu và copy có thể sai khi R2 bật.
- Root cause: trạng thái hạ tầng được hardcode vào copy customer.
- Phương án: backend trả capability/limit; copy “Tối đa X GB” và help đơn giản.
- Acceptance: copy phản ánh config thật; không có tên R2/CORS ở customer UI.

### F-006 — Luồng tiếng Anh không bền và JS/job text lẫn tiếng Việt

- Severity: **P2**; nhóm: UX/i18n/a11y; G4/G6.
- Hiện tượng: invalid file ở `/en/` báo tiếng Việt; cancel redirect về route VI;
  stored `progress_msg` “nâng nét…” xuất hiện trong UI EN.
- Evidence: EV-BR-004.
- Ảnh hưởng: customer quốc tế mất ngôn ngữ giữa core journey.
- Root cause: JS literal không qua i18n, redirect hardcode `/upscalevideo`, event
  lưu câu đã dịch thay vì code trạng thái + params.
- Phương án: message catalog/data attributes, localized URL helper, event code.
- Acceptance: EN A-Z upload/error/cancel/retry/done không có chuỗi VI.

### F-007 — Lịch sử trong app bị cắt 12/50 và count không nói tổng thật

- Severity: **P2**; nhóm: Feature/controls/recovery.
- Hiện tượng: DB query limit 50 rồi `rows[:12]`; heading/count chỉ dùng 12; không
  pagination hoặc link “xem toàn bộ lịch sử”.
- Evidence: EV-SRC-001/002.
- Ảnh hưởng: user tưởng job cũ mất và không tìm lại artifact.
- Root cause: queue widget bị dùng thay full history.
- Phương án: latest queue + link filtered global history, hoặc cursor pagination.
- Acceptance: >50 job có tổng/link/page đúng; owner-only; mobile PASS.

### F-008 — Failed job không có retry tại ngữ cảnh Upscale

- Severity: **P2**; nhóm: Control/recovery; G5.
- Hiện tượng: error card chỉ hiển thị lỗi; retry chỉ tồn tại ở global Jobs.
- Evidence: EV-SRC-002/004, J-12/J-14.
- Ảnh hưởng: user không biết phải đi đâu và phải upload/config lại.
- Root cause: capability nền tảng chưa được nối vào card app.
- Phương án: CTA “Thử lại” dùng retry contract, giữ setting/input còn sống.
- Acceptance: retry idempotent, quote/credit rõ, không double charge.

### F-009 — Queue/progress trong app không tự cập nhật

- Severity: **P2**; nhóm: UX/reliability.
- Hiện tượng: position/ETA/progress chỉ tính lúc server render; JS không poll/SSE.
- Evidence: EV-SRC-001/002.
- Ảnh hưởng: trang mở lâu hiển thị queued/running cũ dù job đã xong.
- Root cause: queue UI tĩnh sau H26.
- Phương án: polling fragment owner-scoped có backoff/visibility pause; terminal
  refresh riêng card, giữ form selection.
- Acceptance: queued→running→done/error không reload full form; offline recovery.

### F-010 — Video validation và duration tin client quá sớm

- Severity: **P2**; nhóm: Reliability/security/economics.
- Hiện tượng: browser/route chủ yếu dựa extension, MIME và client metadata;
  worker mới `ffprobe` sau upload/hold.
- Evidence: EV-SRC-002/003/004.
- Ảnh hưởng: junk upload, quote sai, job lỗi muộn và support/refund tăng.
- Root cause: không có lightweight server probe trước submit/promotion.
- Phương án: validate signature/container + probe staging; giới hạn duration/
  resolution; server quote canonical trước hold.
- Acceptance: file giả video, corrupt, duration/resolution vượt policy bị chặn
  trước job; artifact staging được dọn.

### F-011 — Download file lớn proxy qua web process

- Severity: **P2**; nhóm: Performance/reliability; G7.
- Hiện tượng: `_serve_download` luôn mở storage và stream qua app để ép
  Content-Disposition, thay vì signed direct download có response header.
- Evidence: EV-SRC-003.
- Ảnh hưởng: giữ connection/bandwidth web, dễ timeout với 4K output lớn.
- Root cause: storage URL contract chưa hỗ trợ attachment disposition.
- Phương án: presigned GET ngắn hạn với response-content-disposition hoặc
  authenticated download gateway/CDN; fallback proxy chỉ local.
- Acceptance: file lớn tải qua R2/CDN, owner-only, filename đúng, range/resume.

### F-012 — Submit thiếu cost confirmation và dự báo thời gian/output size

- Severity: **P2**; nhóm: UX/economics/Honest UI.
- Hiện tượng: cost có nhưng click submit giữ credit ngay; Quality chậm khoảng
  15× Fast mà UI chỉ nói “chậm hơn nhiều”; không expected output size/queue ETA.
- Evidence: EV-BR-003, EV-GPU-002, EV-MKT-001.
- Ảnh hưởng: charge bất ngờ, user chọn Quality rồi tưởng app treo.
- Root cause: quote chỉ chứa credit, không nối telemetry/runtime class.
- Phương án: confirmation sheet khi cost/risk cao; ước lượng range, không hứa
  ETA giả khi mẫu thiếu; preset recommendation.
- Acceptance: user biết credit, runtime range và output trước hold.

## P3

### F-013 — Thumbnail video tạo nhiều request metadata lặp

- Severity: **P3**; nhóm: Performance.
- Hiện tượng: mỗi card là `<video preload=metadata>`; 12 card cộng source/compare
  tạo nhiều request 206, một số key lặp sau reload.
- Evidence: EV-BR-005, EV-SRC-002.
- Phương án: poster JPEG/WebP server-generated, lazy load video khi tương tác.
- Acceptance: initial media requests/bytes giảm, LCP không xấu.

### F-014 — Status/preset còn mang ngôn ngữ kỹ thuật

- Severity: **P3**; nhóm: UI/UX.
- Hiện tượng: card lộ `quality`, `HEVC`, `error/done`, “DỮ LIỆU THẬT”; stabilize
  mô tả “two-pass libvidstab”.
- Evidence: EV-BR-001/004.
- Phương án: friendly label + tooltip compatibility; engine detail chỉ admin.
- Acceptance: user test hiểu không cần giải thích dev.

### F-015 — Preview 8 giây không cho chọn đoạn đại diện

- Severity: **P3**; nhóm: Core/UX.
- Hiện tượng: worker lấy giới hạn cố định; user không chọn in-point cảnh khó.
- Evidence: EV-SRC-004, EV-MKT-001.
- Phương án: chọn đoạn 8 giây trên timeline, mặc định auto sample có cảnh động.
- Acceptance: preview đúng segment và cost không đổi ngoài quote.

### F-016 — Icon link của shared topbar không có accessible name

- Severity: **P3** trong app, nhưng là finding nền tảng dùng chung; nhóm: G6.
- Hiện tượng: nhiều anchor icon focusable có accessible text/name rỗng.
- Evidence: EV-BR-001/002.
- Phương án: `aria-label`/visually hidden name ở shell, sửa một lần cho mọi app.
- Acceptance: axe/accessibility snapshot không còn link name rỗng.

## Opportunity priority

Thang 1–5; Priority = giá trị/frequency/market/revenue/risk/confidence cao và
effort/dependency thấp được ưu tiên.

| ID | User value | Frequency | Market gap | Revenue | Risk reduction | Confidence | Effort | Dependency risk | Priority |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F-001 Upload policy | 4 | 5 | 3 | 4 | 5 | 5 | 3 | 3 | 1 |
| F-002 Artifact lifecycle | 5 | 4 | 4 | 4 | 5 | 5 | 4 | 3 | 2 |
| F-006 i18n journey | 4 | 5 | 3 | 4 | 3 | 5 | 2 | 2 | 3 |
| F-007/008 History+retry | 5 | 4 | 4 | 4 | 4 | 5 | 3 | 2 | 4 |
| F-009 Live progress | 4 | 5 | 3 | 3 | 3 | 5 | 2 | 2 | 5 |
| F-003 Temporal quality | 5 | 5 | 5 | 5 | 2 | 4 | 5 | 5 | 6 |
| F-010 Early validation | 4 | 4 | 3 | 3 | 4 | 5 | 3 | 3 | 7 |
| F-011 Direct download | 4 | 3 | 3 | 3 | 4 | 4 | 3 | 4 | 8 |
| F-012 Honest quote | 4 | 4 | 4 | 4 | 3 | 4 | 3 | 3 | 9 |
| F-013 Poster/lazy media | 3 | 5 | 2 | 2 | 2 | 4 | 2 | 2 | 10 |

