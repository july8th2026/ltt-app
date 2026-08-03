# 07 — Roadmap tuần tự

Mỗi stage chỉ có một workstream active. Không bắt đầu stage sau khi gate stage
trước chưa PASS.

| Stage | Scope | Exit gate |
|---:|---|---|
| 0 | Design contract + visual baseline + regression harness | token/shell/component spec; desktop/mobile/auth states PASS |
| 1 | Public catalog + login/register/reset/verify | brand đỏ thống nhất; overflow 0; G6 core PASS |
| 2 | Billing/order + Jobs + Settings/Status | money/error/loading/empty states và keyboard PASS |
| 3 | Home authenticated | marketplace/nav/activity/job/credit thống nhất với shell |
| 4 | Tạo video AI | UI + asset/reference/prompt workflow ưu tiên; Seedance→Upscale giữ quote |
| 5 | Upscale Video | UI polish rồi enhancement engine theo benchmark/acceptance |
| 6 | Auto Sub | a11y/capability/brand cleanup; không phá editor/render parity |
| 7 | Agent + Canvas | shell + execution debug/replay/template, rồi trigger/schedule nếu contract PASS |
| 8 | Thumbnail | studio + reference/brand/variant flow |
| 9 | Tạo ảnh | reference/edit/version flow |
| 10 | Chat AI Studio | project/file/search/export/branch theo provider capability |
| 11 | Kịch bản | outline/section revision/source/export |
| 12 | Tạo Clip ngắn | transcript editor/score rationale/brand/export |
| 13 | Admin/operator | Carbon Red nhưng mật độ cao; không biến admin thành app khách |
| 14 | Website marketing | map source→pretty URL, deploy, link app/legal/support, SEO/accessibility |
| 15 | Cross-platform DEEP re-audit | Q/M/E/G0–G8, full suite, backup/canary/deploy |

## Rollback chung

- Từng stage một commit/release train; không gộp nhiều app.
- CSS/token thay đổi dùng compatibility alias trước khi xóa selector cũ.
- App state-heavy giữ feature flag/legacy entry hiện có.
- Trước production: backup, migration rehearsal nếu có, build, test, browser,
  canary; rollback release và không xóa job/project/ledger.
