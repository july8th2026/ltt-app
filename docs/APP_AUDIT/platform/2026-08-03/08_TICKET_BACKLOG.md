# 08 — Vé triển khai theo thứ tự

## Stage 0–3: nền tảng và trang chung

| Thứ tự | Vé | Hạng mục | Priority | Phụ thuộc |
|---:|---|---|---|---|
| 1 | DS-001 | Token LTT Carbon Red semantic: surface/text/accent/status/focus | P1 | — |
| 2 | DS-002 | Shared shell contract: logo/header/nav/account/credit/help | P1 | DS-001 |
| 3 | DS-003 | Shared component contract: button/input/card/modal/toast/tabs/job status | P1 | DS-001 |
| 4 | DS-004 | A11y contract: 44px target, label/focus/keyboard/reduced-motion/contrast | P1 | DS-003 |
| 5 | DS-005 | Icon/typography/content vocabulary; bỏ emoji không kiểm soát | P3 | DS-001 |
| 6 | PLAT-001 | Sửa public catalog mobile overflow 48 px + regression | P1 | DS-001 |
| 7 | AUTH-001 | Login/register/forgot/reset/verify theo Carbon Red, đủ state | P1 | DS-002..004 |
| 8 | BILL-001 | Nạp credit/packages/quote/order/status/history, money state | P1 | AUTH-001 |
| 9 | JOBS-001 | Job center/detail/filter/artifact/cancel/retry/error | P1 | BILL-001 |
| 10 | SET-001 | Tách IA Settings, accessible forms, advanced/operator boundary | P1 | DS-004 |
| 11 | HOME-001 | Hợp nhất Home authenticated với shared shell/token | P1 | DS-002 |
| 12 | HOME-002 | My Apps/Workspace/Templates/Resources: BUILD thật hoặc DEFER rõ | P2 | HOME-001 |

## Stage 4–12: từng app, không song song

| Thứ tự | Vé | App/hạng mục | Priority |
|---:|---|---|---|
| 13 | TV-UI-001 | Tạo video: shell/control/a11y/empty/job card thống nhất | P1 |
| 14 | TV-FEAT-001 | Asset library + saved reference + role/validation | P2 |
| 15 | TV-FEAT-002 | Prompt assist, variations/remix, camera control theo provider | P2 |
| 16 | UP-UI-001 | Upscale: shell/a11y/queue/compare/status thống nhất | P1 |
| 17 | UP-FEAT-001 | Engine spike AI Detail/denoise/deblur; benchmark thật | P2 |
| 18 | UP-FEAT-002 | Stabilization/interpolation/HDR chỉ sau engine+cost gate | P2 |
| 19 | AS-UI-001 | Auto Sub a11y/shell/capability/content cleanup | P1 |
| 20 | AS-FEAT-001 | Brand template, transcript QA và speaker workflow | P2 |
| 21 | AG-UI-001 | Agent/Canvas shared shell, run inspector, responsive controls | P1 |
| 22 | AG-FEAT-001 | Execution replay/debug/error branch/template | P2 |
| 23 | AG-FEAT-002 | Trigger/schedule/version recovery sau contract/credit gate | P2 |
| 24 | TH-UI-001 | Thumbnail studio + result compare/history | P1 |
| 25 | TH-FEAT-001 | Reference/brand kit/variant scoring, editor handoff | P2 |
| 26 | IMG-UI-001 | Tạo ảnh studio/history/compare | P1 |
| 27 | IMG-FEAT-001 | Style/structure reference, edit/inpaint/outpaint spike | P2 |
| 28 | CHAT-UI-001 | Chat shell/composer/message/attachment/a11y | P1 |
| 29 | CHAT-FEAT-001 | Project/file/search/export/branch | P2 |
| 30 | SCRIPT-UI-001 | Kịch bản workspace/outline/section editor/export | P1 |
| 31 | SCRIPT-FEAT-001 | Source/research/version/shot-list | P2 |
| 32 | CLIP-UI-001 | Clip library + transcript selection/editor/result compare | P1 |
| 33 | CLIP-FEAT-001 | Score rationale, brand preset, multi-platform package | P2 |

## Stage 13–15

| Thứ tự | Vé | Hạng mục | Priority |
|---:|---|---|---|
| 34 | ADM-001 | Admin/operator shell và dense components Carbon Red | P2 |
| 35 | WEB-001 | Chốt route map source website ↔ production pretty URL | P1 |
| 36 | WEB-002 | Đồng nhất brand/content/link App/Support/Legal/Commerce | P1 |
| 37 | WEB-003 | Deploy website, crawl sitemap/404/redirect/SEO/a11y | P1 |
| 38 | QA-001 | DEEP re-audit toàn bộ, visual regression, CWV, full gates | P1 |

Mỗi vé P1 app phải PASS: behavior tests, secret scan, desktop/mobile browser,
console 0, failed app requests 0, overflow 0, accessible name/focus, credit/error
state phù hợp. Vé feature P2 phải thêm provider/cost/privacy/rollback acceptance
trước khi hiện control.
