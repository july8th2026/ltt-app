# 05 — Findings: Tạo Video Seedance

## P1 — phải đóng trước mở rộng thương mại

### F-001 — Token settlement có thể làm số dư credit âm

- Nhóm/gate: economics/credit; G3.
- Hiện tượng: estimate được hiệu chỉnh từ đúng một job Mini 480p/5s, hold bằng
  estimate ×1,25; `quyet_toan()` cho phép actual > held và ghi adjustment âm mà
  không kiểm balance.
- Evidence: EV-SRC-005, EV-COST-001. Chỉ cần token thật bằng 130% estimate:
  Standard 720p/5s giữ 260 nhưng charge 270; Fast 1080p/10s giữ 933 nhưng charge
  970. Nếu số dư lúc submit bằng hold, kết quả âm.
- Ảnh hưởng: giá sau chạy vượt mức khách đã chấp thuận, ledger âm, tranh chấp.
- Phương án: customer charge cap tại quote/held; phần variance là platform risk;
  calibration P95 theo model/input; cảnh báo/không chạy nếu không thể cap.
- Acceptance: mọi settle không làm balance âm; actual provider cost vẫn được
  ghi metric riêng; race/concurrency/idempotency test.

### F-002 — Reference được lưu trước hold và không có lifecycle cleanup

- Nhóm/gate: privacy/data recovery/ops; G2/G5/G8.
- Hiện tượng: `_luu_refs()` ghi blob trước transaction credit; thiếu credit,
  registry fail hoặc bỏ form không xóa. Asset/Job retention hiện không quản lý
  các key mồ côi này.
- Evidence: EV-SRC-003; browser insufficient credit EV-BR-005.
- Ảnh hưởng: dữ liệu cá nhân tồn tại ngoài lịch sử, tăng storage, không self-delete.
- Phương án: upload session/staging owner+TTL → validate → hold → promote; cleanup
  idempotent/finally/sweeper/report; retention và data-deletion contract.
- Acceptance: fail/abandon/crash không còn blob sau TTL; active/job-owned không
  bị xóa; dry-run và event audit có.

### F-003 — Double submit với reference mới có thể vượt dedupe

- Nhóm/gate: credit/idempotency; G3/G5.
- Hiện tượng: submit button không disable. Mỗi POST lưu ref với UUID mới trước khi
  dựng dedupe key; cùng prompt/file tạo params khác nên có thể tạo thêm job/hold.
- Evidence: EV-SRC-002/003.
- Ảnh hưởng: double provider cost/credit và blob trùng khi click nhanh/retry mạng.
- Phương án: client disable chỉ là phụ; server idempotency key ổn định theo form
  intent/file digest + request nonce, upload session dùng lại.
- Acceptance: click đôi/replay/concurrent POST tạo đúng một batch và một hold.

## P2 — chất lượng/recovery/parity

### F-004 — Validation failure làm mất input, locale và để browser ở POST URL

- EN thiếu credit chuyển `/en/taovideo` → `/taovideo/queue` 400, về VI; prompt,
  model Standard, 4K, 15s, count 2 đều reset mặc định. Refresh có nguy cơ resubmit.
- Evidence: EV-BR-005.
- Fix: Post/Redirect/Get với flash state hoặc render preserving canonical form;
  localized action/redirect; file staging token để không bắt upload lại.

### F-005 — Quote không tính video reference nên có thể lệch hold thật

- `/estimate` luôn gọi `has_video_input=False`; actual submit/cost nhận refs và
  dùng rate khác. Copy nói “credit tạm giữ” như con số canonical.
- Evidence: EV-SRC-003/005, official BytePlus pricing EV-MKT-001.
- Fix: quote server từ upload-session/saved refs; trả quote id/version được submit
  xác minh; bất kỳ thay đổi input nào invalidate quote.

### F-006 — EN và mobile keyboard journey không đạt

- Title, status tab/card, quote và route action lẫn VI. Drawer đóng bằng transform
  nhưng không inert/aria-hidden; Tab vào radio ngoài viewport, Escape không trả focus.
- Evidence: EV-BR-002/005.
- Fix: locale-aware URL/message/status code; focus trap/inert/restore; Playwright
  keyboard VI/EN ở 390/768/1440.

### F-007 — Reference manager gây request blob lỗi và thiếu thao tác từng item

- Đổi selection revoke ObjectURL sớm, video còn request nên browser báo
  `ERR_FILE_NOT_FOUND`; không có remove/replace riêng từng reference, dễ mất role.
- Evidence: EV-BR-004.
- Fix: revoke sau media unload/removal; state manager keyed item; remove/replace,
  reorder, role conflict và accessible status.

### F-008 — Upload tin MIME và đọc toàn bộ batch vào RAM

- Server phân loại bằng `content_type`, đọc toàn bộ file; bốn video có thể đạt
  240MB/request trước storage, chưa verify magic/container/duration.
- Evidence: EV-SRC-003.
- Fix: stream staging có tổng request cap; signature/container probe; quota/rate;
  reject trước hold và cleanup partial batch.

### F-009 — Progress tĩnh, không cancel/retry trong app

- Card queued/running chỉ mới khi reload; failed/cancelled không có CTA retry;
  cancel chỉ nằm ở global Jobs.
- Evidence: EV-BR-001, EV-SRC-002.
- Fix: owner-scoped polling/SSE có backoff; cancel/retry card giữ setting/ref và
  quote mới; terminal update không reload composer.

### F-010 — Lịch sử/tài sản bị giới hạn 60 và không có delete/retention UI

- Gallery/saved refs lấy tối đa 60 job; asset cũ biến mất khỏi picker dù blob có
  thể còn; không pagination, search, collection hoặc xóa.
- Evidence: EV-SRC-002/003.
- Fix: cursor history, asset table/lifecycle riêng, search/tag/delete/restore TTL.

### F-011 — Signed R2 redirect không bảo đảm attachment download

- Link có `download` nhưng endpoint có thể redirect cross-origin signed URL;
  browser có thể mở player và bỏ filename/attachment semantics.
- Evidence: EV-SRC-003.
- Fix: signed GET với response-content-disposition, owner check, short TTL,
  range/resume; proxy chỉ fallback local.

### F-012 — Endpoint model hardcode và capability chưa vận hành như config

- `ep-...` nằm trong `models.py`; rotation/model update cần code deploy. Provider
  capability edit/extend chưa được probe/registry hóa.
- Evidence: EV-SRC-001/004, EV-MKT-001.
- Fix: secret-safe operator config + health/capability probe/versioned registry;
  customer chỉ thấy intent label, không endpoint.

### F-013 — Retry moderation dựa giả định “blocked output bill 0 token”

- Worker có thể đổi seed render lại nhiều lần nhưng chỉ quyết toán token result
  cuối; chưa có hóa đơn/task evidence chứng minh attempt bị block miễn phí.
- Evidence: EV-SRC-004, U-03.
- Fix: ghi usage từng task attempt, đặt max provider budget, reconciliation alert;
  không biến unknown thành zero.

### F-014 — Mới khai thác generate, chưa có edit/extend/scene workflow

- Provider/leader có video edit, extend, first-last, multi-shot/project; LTT chủ
  yếu generate + Upscale. Không nên build trước P1, nhưng đây là market gap thật.
- Evidence: EV-MKT-001.
- Fix: sau Phase 0, probe edit/extend; chọn một flow “biến thể/chỉnh clip” và một
  sequence đơn giản, không nhồi professional timeline.

## P3 — polish/efficiency

### F-015 — Estimate HTMX gọi dồn

- Một vòng đổi model/setting/ref tạo khoảng 17 POST `/estimate`; không debounce.
- Fix: debounce 250–400ms, abort request cũ, cache theo canonical params.

### F-016 — Status/error lộ ngôn ngữ provider và kỹ thuật

- Card có “provider is rendering”, timeout raw và progress literal lưu sẵn.
- Fix: event code + localized customer message; raw detail chỉ support log.

### F-017 — Creative options có thể bị hiểu là native model control

- Camera/motion/style hiện chỉ nối câu vào prompt. UI cần nói đây là “gợi ý mô
  tả”, hoặc chuyển sang provider param khi capability thực hỗ trợ.

### F-018 — Shared shell còn control icon thiếu accessible name

- Finding dùng chung đã thấy ở Upscale; Seedance kế thừa shell.
- Fix một lần ở shell, regression axe/accessibility snapshot cho mọi app.

## Priority

| Thứ tự | Finding | Lý do |
|---:|---|---|
| 1 | F-001 | Chặn số dư âm/tranh chấp tiền |
| 2 | F-002 | Privacy + orphan + recovery |
| 3 | F-003 | Chặn double job/charge |
| 4 | F-004/F-005 | Không mất công việc; quote trung thực |
| 5 | F-006/F-008 | A11y/i18n và upload an toàn |
| 6 | F-009/F-010 | Core recovery/history |
| 7 | F-007/F-011 | Reference và delivery hoàn chỉnh |
| 8 | F-012/F-013 | Provider operations/economics |
| 9 | F-014 | Selective parity sau blocker |
| 10 | F-015..018 | Polish và shared fix |

