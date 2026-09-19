# A9–A10 — Roadmap H26.9

Trạng thái 2026-08-09: **Phase A/B/C PASS development; chưa deploy**. Evidence
chi tiết nằm trong `08_RELEASE_AUDIT.md`.

## Phase A — Contract và regression

- [x] Test canonical `/thumbnail` 308 và `/taoanh/thumbnail` 200.
- [x] Test fragment chỉ user đăng nhập xem được, chứa form/job cũ và không có full
  document shell.
- [x] Test source không import app chéo; queue/history/ownership/cost giữ nguyên.

## Phase B — Unified shell

- [x] `taoanh` sở hữu header, mode navigation, loading/error state.
- [x] General giữ form hiện tại; Thumbnail nạp fragment qua HTMX từ public route
  của app con, không gọi Python internals.
- [x] Success/remix quay về canonical mode; URL output/file cũ vẫn dùng được.

## Phase C — Browser và release evidence

- [x] Fixture SQLite/LocalStorage, user có credit, seed done/error của cả hai mode.
- [x] Desktop/mobile: mode switch, empty/loading/error, form, quote, queued/history,
  compare, edit/remix, legacy redirect; console/network/overflow/keyboard.
- [x] Targeted tests → quick gate → full gate; cập nhật Q/M/E/G0–G8, plan, journal,
  commit riêng. Không deploy trước H26.12.

Rollback: revert H26.9. Không migration; hai executor/job/history/storage cũ còn
nguyên nên có thể trả presentation về hai trang tức thì.
