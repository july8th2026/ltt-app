# LTT Studios — Golden UI Implementation Plan

> Tệp điều hành DUY NHẤT của chiến dịch Golden UI. Quy trình test/commit/deploy
> KHÔNG định nghĩa lại ở đây — theo `docs/00_LTT_OPERATING_CONTRACT.md`.

## Mission

Biến các giao diện hiện có thành **ONE GOLDEN LTT STUDIOS UI SYSTEM** — đồng nhất
token, chữ, khoảng cách, control, shell, state; responsive + accessibility tốt —
**không đổi một dòng business logic nào**.

Mục tiêu chất lượng: Overall ≥ 93/100 · critical flows ≥ 95 · không họ trang lớn
nào < 88 · critical UI xác minh ở mức render thật (E3).

## Scope Lock

- ĐƯỢC: Jinja template, CSS, JS thuần trình bày, token, ARIA/focus, chuỗi i18n,
  test giao diện/trình duyệt/a11y/ảnh chụp.
- KHÔNG: route semantics, request/response, DB, auth/session/CSRF, quyền,
  thanh toán/webhook/idempotency, giá/credit, job/queue/worker, storage, GPU,
  provider, deploy, env, secrets.
- Đọc backend chỉ để render đúng state. Vấn đề ngoài UI ⇒ `Out-of-Scope Findings`.
- Cải tiến UI buộc đổi backend ⇒ dừng riêng hạng mục đó và hỏi.

| Mục | Giá trị |
|---|---|
| Worktree | `D:\LTTSTUDIOSAPP-golden-ui` |
| Nhánh | `phien/golden-ui` |
| BASE_SHA | `efa9188cc9477f50a298892ae0fa01da511b113d` (`main` lúc 16/09/2026) |
| Hồ sơ cây | `FAST_BUILD` / `BUILDING` từ 16/09 18:43 (baseline = BASE_SHA). Commit checkpoint không gate; chứng nhận ở `CERTIFYING` bằng `gate --doi --tu efa9188c` rồi L3 một lần (hợp đồng §4.10) |
| Máy chủ soi | `python tools\golden_ui_dev.py --cong 8140` (sqlite dùng một lần ở `tmp/golden_ui/`, 3 tài khoản giả, đủ state đơn nạp/job; bật `LTT_VPS`/`LTT_NEXUS`/`LTT_AUTO_SCAN_VIDEO`; KHÔNG có `secrets/`) |
| Bộ quét | `node tools/golden_ui_quet.mjs --cau-hinh routes.json --ra <dir> [--khung ...]` — HTTP, ảnh toàn trang, console, request hỏng, tràn ngang, axe WCAG 2.2 AA, h1/main/lang, ô chạm, ô nhập <16px |

## Overall Progress
67%

(Trọng số: P0 5 · P1 10 · P2 15 · P3 15 · P4 20 · P5 15 · P6 10 · P7 10. Tính: 5 + 10 + 55%·15 + 40%·15 + 70%·20 + 65%·15 + 80%·10 + 0·10 = 5+10+8,25+6+14+9,75+8 = 61 → **63%** sau khi toàn hệ về axe 0 ở 4 khung; chưa có chứng nhận gate và Phase 7 chưa bắt đầu.)

| Phase | % | Trạng thái |
|---|---|---|
| 0 Discovery & Tooling | 100 | ✅ |
| 1 Baseline Audit | 100 | ✅ |
| 2 Golden Design System | 55 | 🟡 |
| 3 Shared UI Components | 40 | 🟡 |
| 4 Critical Pages | 70 | 🟡 Error ✅ · Jobs 🟡 · Billing 🟡 · Auth 🟡 · Shell/Workspace 🟡 · Public ⏳ |
| 5 Remaining Pages & Apps | 65 | 🟡 Admin ✅ · sqladmin ✅ · Status ✅ · Apps a11y ✅ · VPS/Nexus tương phản ✅ · còn i18n chuỗi cứng + chip thể loại + ảnh bìa |
| 6 Responsive & Accessibility | 80 | 🟡 448 phép đo 390/768/1440/1920: axe serious **0**, tràn 0, main/h1 lệch 0, console 0; chưa đo 430×932 + keyboard walkthrough |
| 7 Visual Regression & Final QA | 35 | 🟡 regression ảnh 28 mẫu ✅ · CERTIFYING (gate) ⏳ · URL công khai ⏳ (cần deploy) |

## Current Baseline

**Baseline Overall UI Quality: 72/100** (E3 — 224 phép đo render thật: 112 route×state × {390×844, 1440×900}, 16/09/2026).

### Tổng hợp máy đo (E2/E3)

| Chỉ số | Giá trị | Ghi chú |
|---|---|---|
| Route×state quét | 112 | 12 họ trang |
| Tràn ngang | 1 | `/admin/khach-hang` @390 |
| `color-contrast` (serious) | **312 nút / 89 trang** | chủ yếu `--text-muted` và link đỏ trên nền tối |
| `scrollable-region-focusable` | 35 / 19 trang | khối `<pre>` mã cuộn ngang không focus được |
| `target-size` | 35 / 7 trang | checkbox bảng, link nhỏ |
| `nested-interactive` | 18 | thẻ giọng Voice: `article[role=button]` chứa nút |
| `aria-progressbar-name` | 12 / 6 trang | thanh tiến độ job không tên |
| `label` / `select-name` / `button-name` (critical) | 16 | admin `api-key-them`, sqladmin |
| `main` bị nhân đôi | 10 màn | home đã đăng nhập, autosub, chatltt, ommi, taovideo, lttvideo |
| Không có `h1` | 3 | `/status`, `/agent/canvas`, autosub/chatltt |
| Lỗi JS | 1 | `/agent/canvas` — `Cannot read properties of undefined (reading 'map')` ⇒ **màn đen** |
| Thuộc tính `style=""` | ~3.500 lượt render | nhiều nhất: vps, gia_api, nexus_may, vps_chi_tiet |
| Mã hex thô | 483 trong `ltt.css`, 115 trong template | |
| `!important` | 39 | 1 cố ý (sàn 16px ô nhập cảm ứng) |
| Font thân chữ | **2 họ** | `base_plain`/`base_public`/admin = `"Segoe UI"`; `base.html` = `system-ui` |

### Điểm theo họ trang (thang 100; E3 trừ khi ghi khác)

| Họ trang | Visual | Consist. | Hierarchy | Clarity | Responsive | A11y | Component | State | **Tổng** |
|---|---|---|---|---|---|---|---|---|---|
| Auth (login/register/forgot/reset/verify) | 86 | 76 | 86 | 84 | 88 | 92 | 82 | 76 | **84** |
| Public (catalog ẩn danh, hướng dẫn, giá API, điều khoản) | 78 | 70 | 80 | 78 | 84 | 70 | 74 | 76 | **76** |
| Workspace (home đã đăng nhập) | 80 | 58 | 76 | 74 | 76 | 78 | 70 | 76 | **73** |
| Billing (nạp, đơn ×6 state, không thấy) | 82 | 74 | 84 | 84 | 86 | 78 | 78 | 84 | **81** |
| Jobs (list, detail ×5 state, retry) | 76 | 72 | 76 | 68 | 84 | 76 | 76 | 76 | **75** |
| Error (404/403/401/500) | 60 | 70 | 58 | 52 | 82 | 88 | 60 | 50 | **65** |
| Status (`/status/api`, `/status`) | 72 | 68 | 62 | 74 | 80 | 70 | 70 | 72 | **71** |
| Developer portal (17 màn) | 84 | 70 | 82 | 82 | 82 | 74 | 80 | 82 | **80** |
| VPS (3 màn soi được) | 80 | 66 | 80 | 80 | 82 | 72 | 72 | 80 | **77** |
| Nexus (giới thiệu, máy của tôi, tải xuống) | 72 | 58 | 74 | 74 | 80 | 64 | 64 | 72 | **70** |
| Admin — trang tự dựng (24 màn) | 76 | 70 | 78 | 76 | 72 | 70 | 70 | 74 | **73** |
| Admin — sqladmin ModelView | 50 | 30 | 56 | 60 | 50 | 48 | 40 | 60 | **49** |
| Apps (21 màn app) | 74 | 60 | 74 | 66 | 76 | 70 | 64 | 68 | **69** |

Critical flows baseline: Auth 84 · Billing 81 · Jobs 75 · Error 65 ⇒ **76**.

## Golden UI Rules

(Hợp đồng dự kiến — chốt sau Decision Locks; mọi quy tắc dưới áp cho mọi họ trang.)

1. **Một nguồn token**: `:root` trong `server/static/ltt.css`. Không hex thô mới
   ngoài khối token. Token ngữ nghĩa (`--surface-*`, `--text-*`, `--border-*`,
   `--brand-*`, `--status-*`, `--focus-*`) — không dùng alias cũ (`--bg`, `--fg`…) trong mã mới.
2. **Một họ chữ** cho mọi shell; thang chữ có tên (page-title / section / card /
   body / label / helper / caption / mono).
3. **Thang khoảng cách 4px** (`--space-1..8`) và **thang bo góc 3 bậc** đã có.
4. **Component dùng chung trước, lớp riêng sau**: `.btn` (primary/secondary/ghost/danger),
   field, card, alert, badge trạng thái, table, empty/loading/error/result state,
   page header. Biến thể riêng của một trang phải có lý do ngữ nghĩa.
5. **State không lộ enum nội bộ**: `running`, `queued`, `taoanh.generate` không bao giờ là chữ khách đọc.
6. **Mọi chuỗi khách đọc đi qua `_()`** (trừ brand, mã, định danh kỹ thuật).
7. **A11y sàn**: 1 `h1`, 1 `main`, landmark, tên cho mọi control/progressbar,
   tương phản AA, vùng cuộn focus được, ô chạm ≥24px (≥44px trên cảm ứng cho control).
8. **Responsive**: không tràn ngang ở 390; sửa ở component, không vá theo viewport.
9. Đổi CSS/JS tĩnh ⇒ cache-bust (`asset_ver`) + đồng bộ `tools/gui/ltt.css` (`tools\dong_goi_gui.py`).

## Decision Locks

Chủ sản phẩm chọn 16/09/2026. Một DL đã LOCKED không được tự thay đổi.

### DL-001 — LOCKED
Decision: **C — giữ hai khung, chuẩn hoá.** Workspace shell chỉ cho trang chủ đã đăng nhập; top-nav cho mọi trang còn lại. Hai khung phải dùng CHUNG: tên + dấu thương hiệu, ô credit, menu avatar, ô tìm kiếm, footer, token, chữ, focus, và cùng component nhãn trạng thái.
Reason: giữ trải nghiệm "kho ứng dụng" của trang chủ, bỏ cảm giác sang sản phẩm khác khi rời trang chủ.
Affected areas: `home.html` (nhánh authed), `_header.html`, `base.html`, `_platform_footer.html`, CSS `.ws-*`/`.hdr-*`.

### DL-002 — LOCKED
Decision: **B — nền ấm Carbon Red mọi nơi.** Developer portal bỏ override nền trung tính + cyan; VPS bỏ teal riêng. Một bảng màu duy nhất; màu phụ chỉ có ở token ngữ nghĩa `--status-*` (thêm `--status-info*`).
Reason: tông nền ấm là đa số và là nhận diện hiện có.
Hệ quả bắt buộc: lỗi tương phản phải sửa bằng **độ sáng** của `--text-*` / link trong họ ấm, không bằng cách trung tính hoá nền.
Affected areas: `ltt.css` (`:root`, `.khu-dev`, `--vps-teal*`, `.goi-*`), `developers_base.html`, `vps*.html`.

### DL-003 — LOCKED
Decision: **A — system stack, Segoe UI trước**: `"Segoe UI", -apple-system, BlinkMacSystemFont, system-ui, Roboto, "Helvetica Neue", Arial, sans-serif`. Một biến `--font` cho mọi shell, kể cả sqladmin và SPA.
Reason: 0 KB tải thêm, không dependency, tiếng Việt chuẩn.
Affected areas: `ltt.css`, `base*.html`, `sqladmin/base.html`, `frontend/*/src/*.css`.

### DL-004 — LOCKED
Decision: **A — phủ CSS Golden + dịch chuỗi** cho sqladmin qua template override `server/admin_templates/sqladmin/*` và CSS. Không đổi ModelView/route.
Reason: giữ công cụ quản trị sẵn có, đưa về cùng hệ thị giác.
Affected areas: `server/admin_templates/sqladmin/`, `ltt.css` (khối `.sqladmin-*`/`--tblr-*`).

## Route / Screen Inventory

Nguồn: đọc mã tại BASE_SHA + quét render. `Auth` = cần đăng nhập.

### Base / shell hiện có

| Shell | Template | Dùng bởi | Font |
|---|---|---|---|
| Top-nav nền tảng | `base.html` (+`_header.html`, `_platform_footer.html`) | 46 template: nap/jobs/status/error, app, dev, VPS, Nexus | `system-ui` |
| Workspace (rail trái + rail phải) | `home.html` nhánh `authed` (`home_workspace`) | **chỉ** trang chủ đã đăng nhập | `system-ui` |
| Public | `base_public.html` | home ẩn danh, huong_dan*, gia_api, api_dieu_khoan, nexus_gioi_thieu, tai-xuong | `Segoe UI` |
| Auth | `base_plain.html` (+`_auth_brand.html`) | login/register/sent/verify/forgot/reset | `Segoe UI` |
| Developer (sub-nav trái trong top-nav) | `developers_base.html` (`.khu-dev`: nền trung tính + cyan) | 18 màn | `system-ui` |
| VPS (sub-nav trái trong top-nav) | `vps_base.html` (teal) | 5 màn | `system-ui` |
| Admin tự dựng | `admin/_vo.html` + `_kieu_chung.html`; 10 màn thân dựng bằng f-string ở `server/admin.py` | 34 màn | `Segoe UI` |
| Admin sqladmin | `admin_templates/sqladmin/base.html` (Tabler/Bootstrap, nền navy) | 8 ModelView × list/details/edit/create | `-apple-system` |
| SPA Vite | `frontend/{agent-canvas,chatltt,prompt-ai-ommi,autosub-studio}` | canvas, chatltt, ommi workspace, autosub studio | token riêng (33/0/29/5 biến) |

### Họ trang × route

| Họ | Route (state quét được) |
|---|---|
| Public | `/` ẩn danh · `/en/` · `/huong-dan` · `/huong-dan/cong-cu` · `/gia-api` · `/api-dieu-khoan` · `/tai-xuong` · `/nexus` (broker tắt) · `/vps` ẩn danh · `/vps/dieu-khoan`. Privacy/terms là link WordPress ngoài (`PUBLIC_LINKS`) |
| Auth | `/login` · `/register` · `/register` (sent) · `/verify-email` ok/hỏng · `/forgot-password` form/sent · `/reset-password` hợp lệ/hết hạn |
| Account | **Không có trang tài khoản/cài đặt riêng** (gỡ 26/08). Số dư + menu avatar ở header |
| Billing | `/nap` · `/nap/don/{id}` pending/pending-không-link/pending-vừa-về/huỷ-ở-cổng/paid/expired/cancelled/failed · `/nap/don/{id}` 404 · fragment `/trangthai` |
| Jobs | `/jobs` (rỗng/có/lọc/admin-env) · `/jobs/{id}` queued/running/done/error/cancelled/retry-child · fragment `/progress` |
| Status | `/status/api` (công khai) · `/status` (operator) |
| Error | `error.html` cho mọi HTTPException ngoài API: 400/401/403/404/429/500 (+405/413 dùng `detail` thô) · `access_middleware` 404/403 |
| Developer | `/developers` + quickstart, pricing, playground, cli, docs, tools, tools/{name}, projects, keys, settings, privacy, logs, logs/{id}, jobs, usage, notifications, webhooks |
| VPS | `/vps` · `/vps/dieu-khoan` · `/vps/{id}` · `/vps/{id}/cai-dat` · `/vps/{id}/console` (3 màn sau cần máy seed — chưa soi) |
| Nexus | `/nexus` giới thiệu · `/may-cua-toi` · `/tai-xuong` (broker pages sau `LTT_NEXUS_WEB_BROKER` — chưa soi) |
| Admin | `/admin/` + nguoi-dung, khach-hang, tim, he-thong, nang-cao, 13 trang `api-*`, apikeys, grant-credit, api-key-them/sua/test, api-models, doanh-thu, goi, don · sqladmin `/admin/{user,credit-entry,app-access,job,session,platform-info,nhat-ky,api-key}/list|details|edit|create` |
| Apps (khách) | agent, agent/canvas, audio-pause, auto-scan-video, autosubvideo, chatltt, ltt-voice (studio/giong/lich-su/du-an/api), prompt-ai-ommi (+classic), prompt-canh, taoanh, taoanh/thumbnail, taoclipngan, taovideo, transcript, upscalevideo, video-assembly |
| Apps (admin) | lttvideo, qualitylab |

## State Inventory

| Miền | State (nguồn mã) |
|---|---|
| Job | `queued` `running` `done` `error` `cancelled` (`platform_core/models.py:250-254`) + retry lineage + artifacts + timeline `job_events` |
| Đơn nạp | `pending` `paid` `expired` `cancelled` `failed` (`models.py:914-918`) + `?cancel=true`, `?ve=1`, không-checkout-url, không-thấy |
| Auth | login: CSRF 400 · 429 IP/tài khoản · Turnstile 401 · chưa xác thực 403 · sai 401 · register: email/mật khẩu/disposable/Turnstile 400 · 503 không DB · 429 IP · verify ok/400 · reset hợp lệ/400 |
| Lỗi | `_ERROR_MESSAGES` 400/401/403/404/429/500 (`server/app.py:32-39`) + `correlation_id` |
| App | enabled/disabled card · lifecycle released/development/maintenance/internal/retired · HIDDEN 404 · LOCKED 403 · bundle Vite thiếu 503 · sidecar/engine chưa sẵn sàng |
| Developer | API tắt / read-only / bình thường · khoá lộ một lần · rỗng/lọc rỗng |
| VPS | cờ tắt 404 · hạ tầng lỗi · hết chỗ · máy: đang tạo/chạy/tắt/treo/xoá/cách ly/mất liên lạc |

## Phase 0 — Discovery & Tooling
Progress: 100%

Completed:
- git state, worktree riêng từ `main`, tài sản gitignore chép sang (`yolov8n.pt`, `apps/upscalevideo/vendor`).
- Đọc hợp đồng vận hành, CLAUDE.md, quy trình worktree.
- Inventory route × template × state (hai lượt đọc mã độc lập, tổng hợp ở trên).
- Tooling: Node 24.17 · Playwright 1.62/1.63 (Chromium 1232–1243 đã cài) · `playwright-cli` · Python playwright · axe-core 4.13.0 (mượn từ `frontend/chatltt/node_modules`, không cài mới).
- VS Code: lệnh `code` không có trong PATH của phiên ⇒ **không cài extension** (không có cách an toàn để kiểm); không cần cho chiến dịch vì Playwright + axe chạy bằng CLI.
- Stylelint: không có trong kho; **không thêm** (bộ quét + test pin đủ; thêm linter là dependency mới).
- Dựng `tools/golden_ui_dev.py` (máy chủ soi có dữ liệu) + `tools/golden_ui_quet.mjs` (bộ quét).

## Phase 1 — Baseline Audit
Progress: 100%

Completed: 224 phép đo E3; điểm theo họ trang; P0/P1/P2 bên dưới.
Evidence: `scratchpad/baseline/p1`, `p2` (ảnh + `ket_qua.json`) — ảnh mốc sẽ chép vào `tests/visual/` khi dựng regression ở Phase 7.

## Phase 2 — Golden Design System
Progress: 55%

Completed:
- `:root` thêm `--brand-fill`/`--brand-fill-hover` (chữ trắng 4,84:1 / 5,7:1), `--status-info*`, `--radius-pill`, thang `--space-1..8`, thang chữ `--fs-*`/`--lh-*`, `--shadow-*`.
- `--text-muted` #927f79 → #9d8c87 (≥4,85:1 trên 10 nền bề mặt + soft).
- DL-003: `--font` một stack; `base.html` bỏ `system-ui` riêng.
- DL-002: gỡ override nền trung tính `.khu-dev`; `--dev-cyan*`/`--vps-teal*` trỏ về token brand; định nghĩa `--vps-teal-text` (trước bị tham chiếu mà không có); chuỗi "Request" trên biểu đồ dùng `--status-info`.
- Mọi nền đỏ có chữ trắng (10 khối trong `ltt.css` + `button,.btn` ở `_kieu_chung.html`) → `--brand-fill`; hover tối hơn thay `brightness(1.1)`.
- `tools/gui/ltt.css` đồng bộ (`dong_goi_gui.py --kiem` OK).

Pending:
- Nguồn hex thô còn lại trong template (115) và `ltt.css` ngoài khối token.
- `_kieu_chung.html` ép `.btn{display:inline-block}` ngược `ltt.css` (`inline-flex`) — hợp nhất ở Phase 3.
- `.chip.i/.v/.m`, `.health` còn hex riêng.

Kế hoạch:
- Một khối `:root` token: thêm `--status-info*`, thang `--space-*`, thang chữ `--text-*`/`--leading-*`, `--shadow-*`; `--font` là một họ cho mọi shell.
- Gỡ override `.khu-dev`/`--vps-teal` theo DL-002; định nghĩa `--vps-teal-text` đang bị tham chiếu mà không có.
- Nâng `--text-muted` và link đỏ lên AA (đo bằng axe, không bằng mắt).

## Phase 3 — Shared UI Components
Progress: 40%

Completed:
- `.ui-state` (+ `--warn/--err/--ok/--info/--inline`): eyebrow · title · lead · body · actions · meta · id. Dùng ở `error.html`, trạng thái rỗng `/jobs` (không lọc / có lọc).
- `server/templates/_ui.html`: `nhan_trang_thai(status, loai)` (job + đơn nạp), `ten_trang_thai`, `thanh_tien_do(pct, nhan)` (progressbar có tên, kẹp 0–100, độ rộng qua `--p`). Bảng nhãn nằm trong macro (tránh Jinja cache `import` đóng băng ngôn ngữ).
- `.ui-progress`, `.job-progress-head`.
- Jinja global `ten_app(slug)` (`server/templating.py`) — tên hiển thị từ manifest, chỉ đọc.

Pending: page header chuẩn, field/form, table cuộn focus được, alert, code block `tabindex`, tabs/chips, pagination; hợp nhất `.btn` giữa `_kieu_chung.html` và `ltt.css`.

Kế hoạch: page header · button 4 biến thể · field (label/helper/error) · card · alert 4 mức · status badge (job/đơn/lifecycle, tiếng người đọc) · table (cuộn ngang focus được) · progress (có tên) · empty/loading/error/result/offline state · code block (`tabindex=0`) · pagination · tabs/filter chips.
Macro Jinja dùng chung ở `server/templates/_ui.html` — chỉ nếu ≥3 nơi dùng.

## Phase 4 — Critical Pages
Progress: 70%

Completed:
- Error (P0-02) — xem P0 Issues. Browser E3: 404/403 thật + 400/401/403/404/413/429/500/503 render state, 390 & 1440, axe 0 serious/critical.
- Jobs (PARTIAL): `/jobs` tên app thay slug, bỏ cột `job_type`, nhãn trạng thái dùng chung, lọc app theo tên, trạng thái rỗng có CTA; `/jobs/{id}` h1 = tên app, mã việc ở eyebrow, progressbar có tên. E3: 18 phép đo (list/lọc/5 state/retry/admin) axe **0** (baseline 22). Còn: 430/768/1920, tương tác hủy/thử lại trên trình duyệt.
- Billing (PARTIAL): `nap.html`, `nap_don.html`, `_nap_trangthai.html`, `nap_khong_thay.html` — số kiểu Việt qua `| so` / `| tien_vnd` (hết `200,000đ`), 0 inline style (gom về `billing-*`), gradient bìa thẻ gói KHÔNG hợp lệ (`var(--accent)22`) thay bằng token, khối trống 120px → 72px, lịch sử đơn dùng `ui.nhan_trang_thai(…, 'don')` phân biệt đủ 5 trạng thái, bảng lịch sử là vùng cuộn focus được, `nap_khong_thay` dùng `.ui-state`. Form `/nap/tao`, `hx-get`/`hx-trigger`/`id="tt"`/`role`/`aria-live` giữ nguyên (chốt test). E3: 20 phép đo (8 state đơn + không thấy) axe **0** (baseline 30); htmx fragment tải và thay đúng, 0 request hỏng. Hồi quy tự gây ra đã sửa: `span.sr-only` trong bảng cuộn kéo trang @390 lên 604px ⇒ `.tablewrap{position:relative}`.
- Auth (PARTIAL): 8 template — `auth_title`/`auth_subtitle`/`title`/đoạn thông báo qua `_()` (trước đây `/en/login` hiện tiêu đề tiếng Việt), mọi link qua `u()` (trước đây bấm "Tạo tài khoản" ở bản EN rơi về VI), nút nền `--brand-fill` thay gradient `#ef3731→` (axe không đo được gradient nên lỗi 3,99:1 lọt mọi lượt quét), bỏ hex `#4b1512`. Email trong `register_sent` vẫn escape (thử `<script>`). E3: 20 phép đo VI+EN axe 0. EN đã xác nhận sau khởi động lại (`Sign in to LTT AI Studio`, `Forgot password`).
- Shell / Workspace — DL-001 (PARTIAL): `home.html` bỏ `<main>` lồng (1 landmark), dấu thương hiệu dùng `.mark` như `_header.html` (bỏ "LTT STUDIOS"), credit `| so` (1.250 như header), `aria-label` dịch được, `select#market-sort` có tên (axe critical @768), chuỗi "Khám phá"/"công cụ sẵn sàng"/"app nạp lỗi" qua `_()`. Khối CSS workspace cũ (dòng `.home-page{min-height…}`) 76 hex 6 chữ số → token theo màu gần nhất đúng vai (chữ/nền). E3: 9 phép đo 390/768/1440, axe 0, `main`=1; trang chủ ẩn danh 11 → 0. Còn: chip thể loại lẫn hoa/thường (`audio`, `video`) — nhãn đến từ manifest, cần bảng tên hiển thị; ảnh bìa thẻ trống ở 5 app (P1-12); menu avatar hai khung khác cấu trúc.
Thứ tự: Error → Auth → Billing → Jobs → Shell/Header/Workspace home.

## Phase 5 — Remaining Pages & Apps
Progress: 65%

Completed:
- Admin tự dựng (24 màn + 10 thân f-string ở `server/admin.py`): 19 nhãn form nối `for`/`id`, 5 màu chấm provider đổi sang sắc tối cùng họ để chữ trắng ≥4,5:1 (cũ 2,77–3,56:1), mọi `.tablewrap` focus được. E3: 52 phép đo, **axe 0** trên mọi trang admin tự dựng (còn lại chỉ `/admin/user/list` — sqladmin, DL-004). Bánh cóc `check_server_routes` (admin.py chỉ được nhỏ đi) PASS.

- **sqladmin — DL-004 ✅**: RCA "Actions đè bảng" = luật `ltt.css` KHÔNG phạm vi `.dropdown a,.dropdown button{width:100%}` (menu header) trùng lớp `.dropdown` của Bootstrap ⇒ 8 luật `.dropdown` thu về `.hdr .dropdown` (đối chứng menu header 390/1440 với CSS HEAD qua Playwright route: kích thước trùng khít). Override `list.html` + `layout.html` (chép từ gói 0.20.1, chỉ chuỗi hiển thị qua `_()`: Thao tác/Xuất dữ liệu/Tìm/Hiển thị x–y trên n mục/Trước/Sau/…; `search-reset` có tên; `table-responsive` focus được; menu `<li>` bọc trong `<ul>`). `_` của nền tảng cấp cho Jinja env của gói trong `setup_admin` (2 dòng thay 2 dòng — bánh cóc admin.py PASS). `base.html`: `--tblr-*` → token Golden, sidebar/ô nhập/checkbox/nút phụ bỏ navy Tabler, font `--font`. ⛔ KHÔNG override `edit.html`/`create.html`: nhãn nút là `value` của `<input name="save">` mà sqladmin so khớp — dịch là đổi dữ liệu gửi lên. E3: 8 trang list + details + edit + EN, axe 0 trên mọi trang list (baseline user-list 14–22).

- **Status ✅**: `/status` có `h1` thật (trước chỉ `strong` trong `pagebar`), mọi chuỗi qua `_()` — khối Nexus từng in không dấu ("may da ghep", "Khong doc duoc so lieu"), 0 inline style (lớp `status-*`, màu cảnh báo qua token thay `#c2453f`), `pre` chi tiết focus được. `/status/api` axe 0. E3 390/1440.
- `/admin/khach-hang` @390 hết tràn: `<caption class="sr-only">` trong `.dev-bang` — cùng cơ chế `/nap` ⇒ `.dev-bang{position:relative}`.

- **Apps (landmark/h1/a11y)**: `<main>` lồng bỏ ở lttvideo, taovideo, prompt-ai-ommi (template) + chatltt, autosub-studio, prompt-ai-ommi, agent-canvas (SPA — build lại 4 bundle, `build-meta` khớp nguồn theo `tools/build_release._frontend_source_sha256`); `h1` sr-only cho chatltt/autosub/canvas; ommi classic 6 `h1` → 1 `h1` + 5 `h2`. Canvas: tab trang tên rỗng → "Page n" (hiển thị, không đổi tài liệu), `<Controls orientation="horizontal">` hết bị minimap che. **Voice — BUG THẬT**: nút "Chi tiết" trên thẻ giọng không làm gì (chuột lẫn Enter) vì thẻ `role=button` bỏ qua mọi nút con; thẻ thôi là nút (hết 18 `nested-interactive`), "Chi tiết" mở panel + mang `aria-pressed`; tái hiện Playwright trước/sau (3 đường đều mở). Studio Tạo video/Upscale: 40 dòng CSS hex xám lạnh → token (DL-002, tương phản). ChatLTT nút chính `--brand-fill`. Upscale ô file có tên. Sàn ô chạm checkbox/radio/summary (`:where`, độ đặc hiệu 0).

Pending: sqladmin `details` `.table-responsive` chưa focus được (details.html không override), Status (`/status` thiếu h1), Developer, VPS, Nexus, 21 màn app.
Thứ tự: Status → Developer → VPS → Nexus → Admin tự dựng → sqladmin (DL-004) → Apps (taoanh, voice, taovideo, upscale, taoclipngan, thumbnail, chatltt, ommi, agent/canvas, autosub, form-app nhỏ).

## Phase 6 — Responsive & Accessibility
Progress: 80%

- **Đo toàn hệ `sau/v2` (448 phép đo, 112 route × 390/768/1440/1920)**: axe serious/critical **0** (trừ 3 nút canvas, đã sửa và đo lại 0 ở cả 4 khung), tràn ngang 0, `main`≠1 0, `h1`≠1 0, lỗi console 0, lỗi quét 0.
- Gốc chung của nhóm lỗi cuối: **làm mờ bằng `opacity`** (thẻ gói VPS hết chỗ .62, "Sắp có" .45, mô tả .75–.85, dòng máy Nexus tắt .62) kéo CHỮ xuống 2,9–4,46:1 ⇒ thay bằng màu token + viền đứt; `.check input{width:auto}` trả checkbox 13px ⇒ 18px; link-duy-nhất-trong-`li` sàn 24px (`:where`); nút tải Nexus `--brand-fill`; canvas: minimap đè cụm nút (luật `bottom` thua CSS thư viện) + nhãn React Flow đè nút cuối ⇒ sửa hai toạ độ.

Completed:
- `scrollable-region-focusable`: 67 khung cuộn `.tablewrap`/`.dev-bang` trên 33 template + `admin.py` có `tabindex="0"`; `pre` do `sao_chep.js` bọc focus được. Nút "Sao chép" theo `<html lang>` (bản EN trước đây vẫn tiếng Việt). Đo ở 390 cho Public/Status/Developer/Admin: khung cuộn **35 → 2** (2 còn lại là `admin.py` chưa nạp lại, đã hết sau khởi động lại), tương phản **87 → 6**.
Khung: 390×844 · 430×932 · 768×1024 · 1440×900 · 1920×1080 cho critical; axe 0 critical/serious trên critical flows.

## Phase 7 — Visual Regression & Final QA
Progress: 35%

- Screenshot regression: `tools/golden_ui_anh_mau.py` + `tests/visual/golden_ui/` (28 ảnh). Không dùng `@playwright/test` (kho không có, không thêm dependency): Playwright Python chụp khung nhìn với `mask` vùng động (giờ, id, mã tra cứu, cột thời gian sqladmin) + Pillow so pixel, ngưỡng 0,2%. Hai vùng chưa che lộ ra ở lần đo đầu (sát ngưỡng 0,199%/0,186%) ⇒ che đúng chỗ thay vì nới ngưỡng.
Screenshot regression Playwright (`toHaveScreenshot`) cho critical screens; test pin a11y; L3 một lần trước bàn giao.

## P0 Issues

| ID | Màn | Vấn đề | Bằng chứng |
|---|---|---|---|
| P0-01 ✅ FIXED | `/agent/canvas` | Màn **đen hoàn toàn** khi tài khoản chưa có workflow: `pageerror: Cannot read properties of undefined (reading 'map')`. Cần RCA: nếu gốc là bundle JS đọc sai hình dạng dữ liệu ⇒ sửa UI; nếu API trả hình dạng khác hợp đồng ⇒ Out-of-Scope + hỏi | `baseline/p2/app-agent-canvas@1440.png` |
| P0-02 ✅ FIXED | `error.html` (mọi 4xx/5xx) | Trang lỗi chỉ có mã số + một câu + "Về trang chính": 401 không có nút đăng nhập, 403/404 không giải thích, 429 không nói chờ bao lâu, 500 không có "thử lại"/hỗ trợ. Người dùng không có đường phục hồi đúng | `baseline/p1/loi-404@1440.png`, `loi-403-status@*` |

## P1 Issues

| ID | Vấn đề | Phạm vi |
|---|---|---|
| P1-01 🟡 PARTIAL (DL-001 áp phần thương hiệu/credit/landmark/token) | **Shell drift**: home đã đăng nhập dùng workspace shell (rail trái/phải, logo "LTT STUDIOS"), mọi trang khác dùng top-nav ("LTT AI Studio"); bấm vào bất kỳ app nào là đổi hẳn khung | DL-001 |
| P1-02 | **Hai họ chữ**: auth/public/admin `Segoe UI`, phần còn lại `system-ui` | DL-003 |
| P1-03 | **Ba bảng màu**: Carbon Red ấm; Developer nền trung tính + cyan; VPS teal (`--vps-teal-text` tham chiếu nhưng không định nghĩa); sqladmin navy/Tabler | DL-002, DL-004 |
| P1-04 ✅ (312 → 0 ở 448 phép đo) | Tương phản: 312 nút / 89 trang dưới AA | toàn hệ |
| P1-05 ✅ (đo lại toàn hệ: main≠1 = 0, h1≠1 = 0) | `main` nhân đôi (10 màn) · thiếu `h1` (`/status`, canvas, chatltt, autosub) · `h1` ×6 ở ommi classic | shell + app |
| P1-06 🟡 PARTIAL (jobs, rail trang chủ, taoanh, thumbnail, transcript, prompt-canh, audio-pause, video-assembly xong; còn dev/admin nội bộ) | Enum nội bộ lộ ra khách: `running · 20%`, `queued · 0%`, `cancelled · 10%` (taoanh), `running/queued/done` (rail home), tiêu đề `Job 8fde2d41`, `taoanh · taoanh.generate` (job detail) | jobs, workspace, apps |
| P1-07 🟡 PARTIAL (error/auth/jobs/billing/status/sqladmin list/home chip/nhãn app xong; còn chuỗi trong JS app + dev portal kỹ thuật) | i18n: nhãn tiếng Anh cứng (`GENERATIVE IMAGE`, `OUTPUT HISTORY`, `REFERENCE & EDIT`), chip thể loại lẫn hoa/thường (`audio`, `video` cạnh `AI Video`), chuỗi không qua `_()` ở error/jobs/nap/auth/status, sqladmin toàn tiếng Anh (`Search`, `Actions`, `Showing 1 to 3`) | toàn hệ |
| P1-08 🟡 PARTIAL (billing xong; còn home rail/dev/VPS kiểm lại) | Định dạng số kiểu Anh trong giao diện Việt: `200,000đ`, `2,200 credit`, `1,000,000đ` (billing) trong khi VPS/Developer dùng `149.000đ`, `1.250` | billing, jobs |
| P1-09 🟡 PARTIAL (progressbar jobs/home ✅, khung cuộn ✅, nhãn admin ✅; còn Voice nested-interactive, upscale `#vfile`) | Progressbar không tên (12) · vùng cuộn `<pre>` không focus được (35) · control lồng control ở thẻ giọng Voice (18) · control thiếu nhãn ở admin `api-key-them` | a11y |
| P1-10 ✅ | sqladmin list: menu "Actions" đè dòng đầu bảng, "Show 10 / Page" trôi ngoài card (gốc: `.dropdown` không phạm vi trong ltt.css) | admin |
| P1-11 ✅ | `/admin/khach-hang` tràn ngang ở 390 (gốc: sr-only absolute trong khung cuộn không định vị) | admin |
| P1-12 ✅ (gốc: lớp `cover-audio/video/chat/ai-text` không có luật; 16/16 thẻ có bìa) | Ảnh bìa thẻ app không đồng nhất: nửa có ảnh, nửa là khối tối rỗng (catalog ẩn danh + workspace) | public, workspace |
| P1-13 ✅ KHÔNG PHẢI LỖI | Nút "Tạo tiếng nói" (Voice) "che mô tả" chỉ thấy trong ảnh chụp TOÀN TRANG — Playwright vẽ phần tử `sticky` tại vị trí cuộn lúc chụp. Khung nhìn thật 1440/390 ở 3 vị trí cuộn: không đè (`sau/voice`) | apps |
| P1-16 ✅ | Voice "Giọng của tôi": nút "Chi tiết" trên thẻ giọng KHÔNG mở gì (chuột + bàn phím) — thẻ `role=button` nuốt click nút con | apps |
| P1-14 | ~3.500 `style=""` + `<style>` riêng ở 10 template; biến thể nút/badge riêng theo trang | toàn hệ |
| P1-15 🟡 PARTIAL (`htmx.min.js` ×9 template có `?v=` + vào `TAI_SAN_CO_VERSION`; còn noVNC, sqladmin static) | Tài sản không cache-bust: `htmx.min.js` (8 template), noVNC `rfb.js`, static sqladmin | shell |

## P2 Issues

| ID | Vấn đề |
|---|---|
| P2-01 ✅ | Thẻ gói nạp: khối trống 120px phía trên chỉ chứa icon kim cương nhỏ (gốc: gradient CSS không hợp lệ) |
| P2-02 | Link inline dùng gạch chân đỏ đậm lẫn link không gạch chân — hai ngôn ngữ link |
| P2-03 | Số bước đánh lệch trong Tạo ảnh (01, 02, 03 rồi 04 ở cột khác) |
| P2-04 | Icon emoji lẫn icon SVG trong thẻ app và menu |
| P2-05 | Trạng thái rỗng dùng 3 kiểu viền (nét đứt, liền, không viền) |
| P2-06 | Chuyển động hover/transition không thống nhất (`transition:.15s` vs `--motion-*`) |

## Out-of-Scope Findings

| ID | Phát hiện | Vì sao ngoài phạm vi |
|---|---|---|
| OOS-01 | `_ERROR_MESSAGES` (`server/app.py:32-39`) **ghi đè** `detail` của route cho 400/401/403/404/429/500 ⇒ "Không tìm thấy job." (`jobs.py:186`) và thông điệp operator (`deps.py:105`) không bao giờ tới người dùng | đổi handler ngoại lệ = đổi hành vi backend. UI sẽ chỉ làm giàu presentation theo `code` |
| OOS-02 | Form HTML có `Form(...)` bắt buộc (vd `POST /login`) có lẽ trả JSON 422 mặc định của FastAPI thay vì trang lỗi (chưa đo) | handler ngoại lệ backend |
| OOS-03 | Trả lời thuần văn bản `CSRF` 400 / `Khong thay key.` 404 ở admin và `Not found` ở `nexus_devices.py:24`, `nexus_sso.py:30` | đổi response của route |
| OOS-04 | 🔴 Trong lượt khảo sát, một lệnh tìm kiếm của agent đọc `secrets/app.env` quá rộng và **in vài ký tự đầu của giá trị `LTT_VPS_PROXMOX_*` / `LTT_VPS_GATEWAY_*`** (gồm một phần secret token Proxmox) vào transcript cục bộ của phiên này | bảo mật — chủ dự án cân nhắc xoay token; phiên này không chạm secrets |
| OOS-06 | `apps/agent/routes/drafts_v3.py::_tai_lieu_rong()` tạo trang v3 thiếu `viewport/frames/notes/comments/view` trong khi `di_tru_m1` sinh đủ — hai nguồn cùng một hình dạng lệch nhau. UI đã chịu được (P0-01), nhưng nên thống nhất ở backend | đổi dữ liệu backend tạo ra |
| OOS-07 | `/admin/user/edit/{id}`: `pageerror: Cannot read properties of null (reading 'checked')` trong `sqladmin/statics/js/bootstrap.min.js` (handler jQuery). Không thuộc tệp override nào; CHƯA đối chứng với cây gốc — làm ở CERTIFYING | mã JS của gói bên thứ ba |
| OOS-05 | `/tai-xuong` công khai **không** sau cờ `LTT_NEXUS` trong khi mọi trang Nexus khác sau cờ | route gating |

## Completed Work

- 16/09 — Worktree `phien/golden-ui` từ `efa9188c`.
- 16/09 — `tools/golden_ui_dev.py`, `tools/golden_ui_quet.mjs`.
- 16/09 — Baseline 224 phép đo E3 + bảng điểm + danh mục P0/P1/P2/OOS.
- 16/09 — DL-001..004 LOCKED.
- 16/09 — **P0-01**: RCA — `fromV3` giả định trang luôn có `frames/notes/comments/viewport`; tài liệu rỗng của máy chủ không có ⇒ `page.frames.map` ném trong `useMemo` ⇒ React sập. Sửa: `frontend/agent-canvas/src/workflowApi.ts::fromV3` điền mặc định; test vitest tái hiện đúng hình dạng máy chủ (đỏ trước, xanh sau); build lại bundle. Hành vi lưu: tài liệu gửi lên có thêm các mảng rỗng — đúng hình dạng `di_tru_m1` vốn sinh.
- 16/09 — **P0-02**: `error.html` theo mã (400/401/403/404/405/413/429/500/502/503/504 + mặc định) — tiêu đề, giải thích, hành động phục hồi (401 → đăng nhập với `next`; 429/5xx → thử lại; 403/5xx → hỗ trợ), mã tra cứu chọn được; 30 chuỗi mới có bản dịch EN.
- 16/09 — Phase 2 token (xem Phase 2).
- 16/09 — `tests/test_1270_golden_ui_nen_tang.py` (23 test): AA bằng phép tính, DL-002/DL-003, trang lỗi theo mã.

## Evidence

| Mã | Loại | Nội dung |
|---|---|---|
| EV-01 | E3 | `baseline/p1`: 39 route × 2 khung (public/auth/billing/jobs/status/error) |
| EV-02 | E3 | `baseline/p2`: 73 route × 2 khung (developer/admin/vps/nexus/apps) |
| EV-03 | E1 | Inventory route/state từ hai lượt đọc mã |
| EV-04 | E3 | `after/p0-01`: canvas render màn onboarding, 0 pageerror, 0 console |
| EV-05 | E3 | `after/p0-02*`: 14 phép đo trang lỗi, axe 0 serious/critical |
| EV-06 | E2 | vitest agent-canvas 62/62 + typecheck; pytest `test_1270` 23/23 |
| EV-07 | E2 | axe `color-contrast` theo cặp màu: `#fff`/`#ef3731` = 3,99:1 là 144/312 lỗi baseline |
| EV-08 | E3 | `after/p3-status`: 36 phép đo jobs/home/6 app — axe 0 trên jobs & home |
| EV-09 | E2 | `test_1270` 36/36; `test_107`, `test_109` cập nhật để chốt dùng macro (6/6) |
| EV-10 | E3 | `after/p4-billing`, `after/p4-nap`: 21 phép đo billing, axe 0, không tràn |
| EV-11 | E2 | `test_1270` 42/42 + `test_106` (3/3, cập nhật chốt macro), `test_369` asset_ver đủ |
| EV-12 | E3 | `after/p4-auth`, `after/p4-auth-en`: 23 phép đo auth VI+EN, axe 0 |
| EV-13 | E3 | `after/p4-home`, `after/p4-home768`: 10 phép đo trang chủ 3 khung, axe 0, main=1 |
| EV-14 | E2 | `test_1270` 52/52; `test_105/109/110` xanh |
| EV-15 | E3 | `after/p6-cuon`: 51 route @390 (Public/Status/Dev/Admin) — trước/sau theo luật axe |
| EV-16 | E3 | `after/p5-admin`: 52 phép đo admin, axe 0 ngoài sqladmin |
| EV-17 | E2 | `test_1270` 56/56; `test_294/306` (sao_chep), `test_317/322` (admin), `check_server_routes` PASS |
| EV-18 | E3 | `after/p5-sqladmin*`: 11 trang sqladmin × 2 khung; `after/p5-hdr`: menu header mở 390/1440; `hdr_doi_chung.mjs` đối chứng CSS HEAD |
| EV-19 | E2 | `test_1270` 59/59 |
| EV-20 | E3 | `sau/v1`: **224 phép đo toàn hệ** (cùng 112 route × 390/1440 như baseline) — serious 436→34, tương phản 312→24, khung cuộn 35→0, nested 18→0, progressbar 12→0, label 12→0, listitem 8→0, main/h1 lệch 26→0, tràn 1→0, console 0 |
| EV-21 | E3 | `voice_chitiet.mjs`: "Chi tiết" chuột/Enter + thân thẻ — trước: không mở; sau: mở cả 3 |
| EV-22 | E2 | vitest `CanvasShell` 22/22; `test_500`/`test_352` 73/73; 4 bundle `build-meta` khớp |
| EV-24 | E2+E3 | `tools/golden_ui_anh_mau.py`: 28 ảnh mẫu (14 màn × 390/1440), ổn định qua 2 lần seed (lệch lớn nhất 0,042%), đối chứng âm 11,95% |
| EV-23 | E3 | `sau/v2`: 448 phép đo 4 khung — axe serious 0 ngoài canvas; `sau/canvas`: canvas 0 ở 4 khung |

## Current Blocker

Không có.

## Next Action

i18n chuỗi cứng còn lại (taoanh `GENERATIVE IMAGE`/`OUTPUT HISTORY`/`REFERENCE & EDIT`, chip thể loại `audio`/`video`), rồi Phase 7: screenshot regression Playwright cho critical screens + chuyển FAST_BUILD sang CERTIFYING.