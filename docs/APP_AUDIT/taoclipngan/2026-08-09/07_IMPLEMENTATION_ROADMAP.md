# A9–A10 — Roadmap H26.10A

Trạng thái 2026-08-09: **Phase A/B/C PASS development; chưa deploy**. Evidence
chi tiết tại `08_RELEASE_AUDIT.md`.

## Phase A — Regression đỏ

- [x] Customer labels không lộ engine; estimate theo locale.
- [x] Template có advanced disclosure, source summary/preview và link job log.

## Phase B — UX implementation

- [x] Giữ số clip + tỉ lệ ở bề mặt chính; gom tier/brand/platform/genre/language/
  min-max vào vùng nâng cao mặc định đóng.
- [x] File local có video preview + filename/duration + clear; library có summary.
- [x] Tất cả copy tĩnh/dynamic/JS qua i18n; job card có đường vào nhật ký.

## Phase C — Evidence

- [x] Targeted + quick/full gate.
- [x] Fixture 8116: file source thật, quote, submit fake worker, done/history,
  compare/package/log; desktop/mobile, console/network.
- [x] Cập nhật score/G0–G8, plan, journal và commit riêng; không deploy trước H26.12.

Rollback: revert H26.10A; không migration hay thay engine/job/output.
