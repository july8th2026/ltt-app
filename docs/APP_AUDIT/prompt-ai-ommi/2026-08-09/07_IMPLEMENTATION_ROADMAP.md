# 07 — Implementation Roadmap: Prompt AI OMMI

## Thứ tự bắt buộc

| Phase | Phạm vi | Vé triển khai | Exit criteria |
|---|---|---|---|
| 0 — Release safety | khóa rollout, paid apply, autosave, error contract | OMMI-R01..R05 | integration paid path; 0 data loss trong browser race; JSON errors có message |
| 1 — Data/storage | upload admission, staging/promote/delete/TTL, partial output | OMMI-D01..D05 | fake MIME bị chặn; DB fail/delete/abandon để 0 orphan; refund/retry contract |
| 2 — Canonical journey | hợp nhất IA thành Project–References–Board–Export | OMMI-U01..U07 | customer hoàn thành reference→board không vào module rời/classic |
| 3 — Production chain | model/quote per run, per-scene output, handoff, unified jobs | OMMI-P01..P06 | scene→image/video→job→result/retry chạy A–Z |
| 4 — Recovery & reach | clone/archive/snapshot/restore, library version, VI/EN/theme/mobile/a11y | OMMI-X01..X07 | reload/deep-link/recovery; locale/theme A–Z; 390px và keyboard pass |
| 5 — Market parity | template project, consistency guidance, selected canvas experiment | OMMI-M01..M04 | blind usability ≥4/5 task success; quyết định canvas bằng usage data |

## Backlog vé chi tiết

- **OMMI-R01:** sửa revision contract và idempotency của Director apply.
- **OMMI-R02:** integration test quote→paid job→apply→storyboard, bao gồm retry.
- **OMMI-R03:** thay global busy bằng state theo action; flush draft trước mọi run.
- **OMMI-R04:** local durable draft/outbox, conflict compare/merge và unsaved guard.
- **OMMI-R05:** JSON error envelope; map field/action; telemetry không chứa prompt bí mật.
- **OMMI-D01:** streaming admission + magic/decode/dimension/pixel validation.
- **OMMI-D02:** staging key, DB transaction, promote/rollback và TTL janitor.
- **OMMI-D03:** xóa variant/resource phải xóa blob idempotent; audit orphan scanner.
- **OMMI-D04:** bỏ storage key nội bộ khỏi customer DTO/export.
- **OMMI-D05:** result completeness, partial outcome, retry missing/refund ledger.
- **OMMI-U01:** project setup modal/draft trước persist; chống blank record.
- **OMMI-U02:** IA 4 bước, gỡ mục trùng Project/Brief.
- **OMMI-U03:** resource picker và `@reference` ở project/scene.
- **OMMI-U04:** style/meta thành progressive controls trong context, không màn hình rời mặc định.
- **OMMI-U05:** storyboard reorder/camera/continuity/history/compare/restore.
- **OMMI-U06:** retire `/classic` sau capability parity và redirect có migration note.
- **OMMI-U07:** empty state dùng một template demo không tiêu credit.
- **OMMI-P01:** model intent selector + advanced details ẩn mặc định.
- **OMMI-P02:** canonical signed quote theo operation/model/output count.
- **OMMI-P03:** per-scene run/cancel/retry/result/version trong scene card.
- **OMMI-P04:** handoff image/video với reference/prompt/aspect đã điền sẵn.
- **OMMI-P05:** unified cross-app job history, filter, detail log và recovery.
- **OMMI-P06:** sửa job classification và metrics p95; SLO dashboard.
- **OMMI-X01..X03:** expose project/library lifecycle, deep-link và restore state.
- **OMMI-X04..X07:** app-owned i18n, theme DOM tokens, mobile drawer, keyboard/focus/ARIA.
- **OMMI-M01..M04:** templates, consistency evaluator, usability panel và canvas discovery.

## Test pyramid bắt buộc

1. Unit: revision/state machine, quote, partial result, storage transitions.
2. API integration: ownership/CSRF/credit/idempotency/rollback/orphan cleanup.
3. Frontend integration: draft flush, error mapping, attach reference, recovery.
4. Playwright: desktop/mobile, VI/EN/theme, paid fixture A–Z, cancel/retry/handoff.
5. Gate: `python tools\gate.py`; canary/auth production verification chỉ khi người
   dùng ra lệnh deploy rõ ràng.

## Rollback

- Mỗi phase giữ feature flag riêng; không đổi schema phá hủy.
- Dual-read chỉ trong thời gian migration; mọi write dùng canonical contract mới.
- Nếu canary lỗi money/data, tắt flag và giữ job/result để replay, không xóa.
