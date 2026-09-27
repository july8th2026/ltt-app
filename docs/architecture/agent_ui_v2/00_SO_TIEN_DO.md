# Sổ tiến độ — Agent UI V2

Cập nhật lần cuối: 2026-09-27 · bởi: điều phối (phiên audit)

> ⛔ **Trạng thái công việc ghi vào TỆP NÀY, không chỉ trong hội thoại.** Một phiên
> bị `/compact` mất hội thoại; tệp thì còn.
> Plan điều phối: `docs/superpowers/plans/2026-09-27-agent-ui-v2-TONG.md`

## Bảng pha

Trạng thái hợp lệ (⛔ không tự chế thêm):
`CHƯA MỞ` · `ĐANG LÀM` · `CHỜ DUYỆT` · `ĐÃ GỘP` · `CHẶN`

| Pha | Làn | Trạng thái | Nhánh | Tệp SỞ HỮU | Gộp main | Ghi chú |
|---|---|---|---|---|---|---|
| UI-0 Lỗi P0 cơ khí | `ui0` | **ĐANG LÀM** | `claude/ltt-agent-automation-ux-audit-9e3764` | `bien_dich.py` · `workflowApi.ts` · `canvas.css` · `editorState.ts` · `CanvasEdgeView.tsx` · `CanvasEdgeView.tsx` | — | dải test **5600-5699** |
| UI-3 Tách CanvasShell | — | CHƯA MỞ | — | — | — | chặn bởi UI-0. **Mở khoá song song hoá** |
| UI-2 Design system | `ui2` | **CHỜ DUYỆT** | `worktree-agent-a710623353e7caab2` (commit `7d43e9b0`) | `canvas.css` | — | ⚠️ chạy **trước** UI-3 tách xong theo brief điều phối nhận được — xem ghi chú R10 bên dưới |
| UI-1 Automation Studio | — | CHƯA MỞ | — | — | — | **chặn bởi Q1** · chủ S5 (bảng định tuyến) |
| UI-4 Node UX V2 | — | CHƯA MỞ | — | — | — | chặn bởi UI-3 |
| UI-7 Execution + Runs | — | CHƯA MỞ | — | — | — | chặn bởi UI-3 · chủ S4 (đợt 2) |
| UI-5 Inspector + Connections | — | CHƯA MỞ | — | — | — | **chặn bởi Q4** |
| UI-8a Human approval ⭐ | — | CHƯA MỞ | — | — | — | chặn bởi UI-7 · nâng ưu tiên sau phân tích CrewAI |
| UI-6 Data picker | — | CHƯA MỞ | — | — | — | chặn bởi UI-5 |
| UI-8b Agent Designer diff | — | CHƯA MỞ | — | — | — | chặn bởi UI-3 |
| UI-9 Templates | — | CHƯA MỞ | — | — | — | chặn bởi UI-1 |
| UI-10 i18n + trợ năng + mobile | — | CHƯA MỞ | — | — | — | ⛔ **không song song hoá được** — chạm mọi tệp |
| UI-11 Nghiệm thu + hồi quy | — | CHƯA MỞ | — | — | — | cuối cùng, rồi mới **gate một lần** |

## Phiếu tệp đang giữ

| Làn | Tệp | Từ lúc | Sổ dùng chung? |
|---|---|---|---|
| ui0 | `platform_core/workflow/bien_dich.py` | 27/09 | — |
| ui0 | `frontend/agent-canvas/src/workflowApi.ts` | 27/09 | **S4** |
| ui0 | `frontend/agent-canvas/src/editorState.ts` | 27/09 | **S3** (bàn giao UI-3) |
| ui0 | `frontend/agent-canvas/src/canvas.css` | 27/09 | **S1** (bàn giao UI-2) |
| ui0 | `frontend/agent-canvas/src/nodes/NodeKhung.tsx` | 27/09 | — |
| ui0 | `frontend/agent-canvas/src/CanvasEdgeView.tsx` | 27/09 | — |


**Sáu sổ dùng chung và chủ của chúng** — đụng vào thì DỪNG và báo điều phối:

| # | Sổ | Chủ |
|---|---|---|
| S1 | `frontend/agent-canvas/src/canvas.css` (+ `styles/`) | UI-2 |
| S2 | `CanvasShell.tsx` / `features/editor/EditorShell.tsx` | UI-3 |
| S3 | `editorState.ts` | UI-3 |
| S4 | `workflowApi.ts` | UI-0 → rồi UI-7 |
| S5 | bảng định tuyến `apps/agent/routes/` | UI-1 |
| S6 | `tools/thanh_phan.toml` | UI-3 |

## Bảng độ phủ nghiệm thu

Mốc nền đo 27/09/2026 trên trình duyệt thật: **0/5 luồng dựng được**.

| Luồng | Dựng được? | Kịch bản Playwright | Pha mở khoá |
|---|---|---|---|
| UX-1 Schedule → Sheets → … → YouTube | ❌ | — | UI-5 + backend trigger (**Q11**) |
| UX-2 Webhook → Phân tích → Clip → Phụ đề | ❌ | — | backend — **registry chưa có node webhook** |
| UX-3 Manual → Ảnh → Video → Giọng → Render | ⚠️ **một phần** | `agent_ui_v2_ui0_nghiem_thu.js` | **UI-0 xong**: node `app.*` nối được và chạy được (đo: 1 cạnh thật, run QUEUED). Còn thiếu trigger thủ công (**Q11**) |
| UX-4 Sheets → AI Router → nhánh → gộp | ❌ | — | UI-5 + **Q11** (`ai.router` đang `publish_duoc=False`) |
| UX-5 Parent → Subworkflow → Wait → Human | ❌ | — | **UI-0** + UI-8a |

## Quyết định đã chốt

| # | Câu | Chốt | Ngày | Ai |
|---|---|---|---|---|
| Q1 | Kiến trúc thông tin (khuyến nghị **B** Automation Studio, độ tin CAO) | **CHƯA** | | |
| Q4 | Tầng OAuth (khuyến nghị **C**, độ tin **THẤP** — cần chủ dự án) | **CHƯA** | | |
| Q11 | Trigger: mở `trigger.manual`? schedule/webhook? | **CHƯA** | | |
| Q2 | UI-0 làm thành phase riêng, deploy độc lập | **CHƯA** | | khuyến nghị A, độ tin CAO |
| — | Giữ `@xyflow/react` | ✅ CHỐT | 27/09 | bằng chứng: dùng 11/30 API |
| — | Sửa P0-1 ở **cổng biên dịch**, ⛔ không di trú dữ liệu | ✅ CHỐT | 27/09 | `…-TONG.md` §1.5 |

## Rủi ro đang mở

| # | Rủi ro | Trạng thái |
|---|---|---|
| **R3** | Task 2 của UI-0 **đổi hành vi**: `core.if` nay chạy **một** nhánh thay vì cả hai | ⚠️ phải báo chủ dự án **trước khi deploy** |
| R7 | 3 hạng mục (media preview, test một bước, run history) **không đạt 98 bằng công việc UI** | đã ghi ở `10_IMPLEMENTATION_PLAN.md` §3 |
| R8 | Phình phạm vi ở UI-1 (chia sẻ, phân quyền, marketplace) | UI-1 chỉ làm điều hướng + 5 trang |
| R10 | Hai làn cùng sửa `canvas.css`/`CanvasShell.tsx` | UI-2 và UI-3 ⛔ không chạy song song |

## Nhật ký

_(mới nhất ở trên)_

- `2026-09-27` `ui2` — **Bốn việc XONG, đo trên trình duyệt thật (`agent_ui_v2_ui2_nghiem_thu.js`, máy chủ cô lập 8198).**
  ⚠️ Nhận brief chạy UI-2 **trước khi** thấy UI-3 (tách `CanvasShell.tsx`) đã gộp
  `main` — brief nói UI-3 "đang chạy song song ngay lúc này". Đã kiểm
  `git diff --stat -- '*.tsx'` **rỗng** trước khi commit; không đụng `.tsx` nào.
  Điều phối cần xác nhận thứ tự gộp (UI-2 trước hay sau UI-3) trước khi merge.

  | Tiêu chí | Trước | Sau |
  |---|---|---|
  | hex cứng trong `canvas.css` | 482 | **63** (chưa đạt ≤25 — xem lý do dưới) |
  | lớp CSS chết (đo lại, không dùng số 49 cũ) | 79 (đo lại 27/09, khác con số audit) | **0** |
  | khối `@media (max-width:640px)` | 6 (không phải 5 như audit ghi) | **1** |
  | theme-light: ô form giữ nền TỐI | 7/11 (audit), đo lại thực tế **20/20** ô kiểm tra đều tối trước sửa | **0/20** |
  | cỡ chữ < 12px | nhiều chỗ (phần lớn nằm trong lớp CHẾT vừa xoá) | **0** |
  | tương phản bề mặt minimap/controls | 1,04:1 | **~1,08:1 nền phẳng** (đã thêm viền `border-strong` + `box-shadow`; tương phản KHUNG viền đo **1,45:1**, nhưng nền-với-nền vẫn thấp — xem lý do dưới) |

  🔴 **Nguyên nhân thật của "7/11 ô form giữ nền tối" (khác giả thuyết ban đầu
  của audit — không phải "thiếu một luật theme"):** `server/static/ltt.css` có
  luật `input:not([type=…])×8, select, textarea {background:var(--panel2)…}`.
  Mỗi `:not([type=x])` cộng (0,1,0) độ đặc hiệu ⇒ nhánh `input` của luật này đạt
  **(0,8,1)** — cao hơn MỌI selector `.class input` trong `canvas.css`. `--panel2`
  là một **alias ĐÓNG BĂNG tại `:root`** (`--panel2:var(--surface-overlay)`,
  ltt.css dòng ~41) — biến CSS lồng bên trong một khai báo custom-property được
  thay thế BẰNG GIÁ TRỊ KẾ THỪA CỦA CHÍNH PHẦN TỬ ĐANG KHAI BÁO NÓ (ở đây là
  `:root`, luôn tối), **không** đọc lại theo phần tử đang DÙNG nó. Nhánh
  `select`/`textarea` của luật ltt.css chỉ có độ đặc hiệu (0,0,1) nên KHÔNG bị —
  khớp đúng với audit: 4 ô (textarea + 2 select) đã sáng, 7 ô còn lại đều là
  `<input>`. Sửa bằng `!important` trên đúng các khai báo `background`/`color`/
  `border-color` cần thắng, **chỉ trong `canvas.css`** (không đụng `ltt.css`,
  không tạo `.theme-light` biến thể mới). Đo lại trên 20 ô form thật (kể cả
  `prompt`/`image_key`/`seed`… trong FormTuLuocDo) — **0/20 còn tối**.

  ⚠️ **Không đạt ≤25 hex, nói thật thay vì né:** phần còn lại là (a) ~15 hex là
  CHÍNH bảng token `.theme-light{...}` (định nghĩa 1 lần, y hệt cách `ltt.css`
  tự làm cho bảng của nó — không thể "token hoá" một token bằng chính nó),
  (b) ~6 hex trạng thái riêng cho nền sáng (`--status-success`/`--status-danger`
  của `ltt.css` được canh cho nền TỐI; dùng thẳng trên nền trắng sẽ **hỏng AA**,
  nên `save-state`/`run-error`/`validation-banner` ở theme-light cần sắc độ khác),
  (c) phần còn lại là màu/bóng một-lần không có token tương đương (sticky note,
  glow khung, bóng đổ theo từng lớp nổi). Đạt ≤25 tuyệt đối cần HOẶC đổi bảng màu
  nền sáng cho đơn giản hơn (quyết định thiết kế, ngoài phạm vi "dọn CSS"), HOẶC
  chuyển hex sang cú pháp `rgb()`/`hsl()` để né đúng chữ của phép đếm — không làm
  vế sau vì đó là né phép đo, không phải sửa.

  ⚠️ **Minimap/controls không đạt 3:1 nền-với-nền:** bảng màu `.theme-light` chỉ
  có vài sắc GẦN TRẮNG theo chủ đích (`--surface-canvas:#f5f6f8` → `--surface-
  raised:#fff`, chênh nhau rất ít). Muốn tỉ lệ tương phản NỀN-với-NỀN đạt 3:1 cần
  một nền xám đậm hơn nhiều (ước tính độ sáng tương đối ~0,28, tức khoảng
  `#6b7280`) — sẽ lệch hẳn phong cách "nổi bằng bóng đổ, không bằng nền tối" mà
  MỌI panel nổi khác của theme-light đang dùng (`.canvas-palette.is-open`,
  `.command-palette`,… đều `#fffffff5` + `box-shadow`, không phải nền tối hơn).
  Đã thêm viền + bóng cho minimap/controls (khớp quy ước có sẵn), là cải thiện
  THẬT về mặt cảm nhận, nhưng phép đo nền-phẳng không bắt được nó. Đổi sang một
  nền xám đậm hơn là quyết định thiết kế, không phải việc "dọn + token hoá".

  Danh sách 79 lớp đã xoá (theo họ): `tool-node`/`typed-port`/`node-preview`/
  `node-status`/`node-title`/`node-inline-text`/`node-primary-actions`/`node-
  preview-actions`/`node-image-grid`/`node-empty`/`node-footer-actions`/`node-
  run`/`node-upload`/`node-customer-composer`/`node-input-chips`/`node-
  reference`/`node-inspector`/`node-duplicate`/`node-chips`/`node-composer`/
  `node-artifacts`/`is-selected`/`has-output`/`input-port`/`output-port`/
  `primary-output`/`connectingto`/`valid`/`invalid`/`accent` (họ node cũ, thay
  bởi `node-khung`); `assistant-drawer`/`assistant-context`/`assistant-error`/
  `assistant-modes`/`context-composer`/`context-fields`/`composer-*` (đã bỏ,
  xem comment trong `CanvasShell.tsx`); `history-drawer`; `run-inspector`/
  `run-badge`/`run-dot`/`run-steps`/`run-artifacts`/`run-history`/`run-history-
  details`/`run-quote`/`run-validation`/`run-state`/`legacy-run-tools`/`replay-
  run`/`restore-workflow`/`schedule-control`/`scheduled-time` (thay bởi
  `run-v3`); `quick-connect-picker`/`quick-create-picker`/`context-tool-list`;
  `creative-node`/`has-composer`/`is-chon` (biến thể `data-presentation=creative`
  không còn code path nào đặt); `catalog-toggle`/`cache-control`/`asset-field`/
  `check-field`/`compact-check`/`palette-search`/`template-actions`/`legacy-
  save-state`/`routing-note`/`starter-flows`/`detail-empty`/`node-more`.

  Nghi ngờ nhưng KHÔNG xoá: không có — mọi lớp còn lại đều xác nhận được bằng
  literal match trong `.tsx`, template động đã biết (`panel-${x}`, `node-kind-
  ${x}`, `edge-${kind}`, `theme-${theme}`, `node-cong-${phia}`, `react-flow__*`),
  hoặc lớp trang server-side (`hdr`/`apptabs`/`platform-footer`/`agent-canvas-
  immersive`, đặt ở `apps/agent/templates/agent_canvas.html` + `server/templates/`).

- `2026-09-27` `ui0` — **Task 6 XONG — nghiệm thu trên TRÌNH DUYỆT THẬT: `status: PASS`**
  (chế độ A, máy chủ cô lập 8198, sqlite scratchpad; production 8100 vẫn 200 sau đó).

  | Phép đo | Mốc nền 27/09 | Sau UI-0 |
  |---|---|---|
  | `core.set` từ palette → Chạy | `node_khong_ton_tai` | **`null`** |
  | cổng `app.video.generate` | 15 cổng / **1** vị trí / 6×6px | 15 cổng / **15** vị trí / vùng bấm **24px** |
  | kéo dây cặp hợp lệ `image[]→image[]` | 0 cạnh, im lặng | **1 cạnh** |
  | kéo dây cặp SAI kiểu `image[]→image` | — | vẫn 1 cạnh (hệ kiểu không thủng) |
  | nút `+` chết | 2 nút no-op | **0** |

  🔴 **Hai lần phép đo của tôi SAI, không phải mã sai** — ghi lại vì cả hai đều là
  bẫy thật:
  1. Kéo `image_keys (image[]) → image_key (image)` trả 0 cạnh. Tra
     `cap_noi_duoc`: `image[]→image` = **false**. Hệ thống **từ chối đúng**; kịch
     bản chọn sai cặp. ⇒ luôn tra bảng luật trước khi kết luận "kéo dây hỏng".
  2. Đo bằng `getBoundingClientRect` thì 15 cổng / 15 vị trí = **xanh**, nhưng vẫn
     không kéo được. Phép đo THẬT là `elementFromPoint` tại tâm cổng — nó trả
     `.node-cong-kieu`, tức **nhãn kiểu đè lên cổng** (nhãn đứng sau trong DOM và
     `opacity:.6` tạo stacking context). ⇒ toạ độ đúng **không** đồng nghĩa với
     bấm được.

  ⚠️ **Cái giá đã biết:** mỗi hàng cổng `min-height:24px` làm node cao hơn
  (`app.video.generate` 381px → **525px**). Đó là đánh đổi có chủ ý của UI-0 (bấm
  được > gọn); **UI-4** phải giải bằng 3 mức mật độ, không phải bằng cách hạ vùng bấm.
- `2026-09-27` `ui0` — Task 3+4+5 XONG, 156/156 test frontend xanh. Đã **chứng minh
  test bắt được lỗi** bằng cách tiêm lại mã cũ (`kind:'DATA'` đóng cứng,
  `BUOC_XEP_X=430`) ⇒ 3 phép kiểm đỏ đúng chỗ, rồi khôi phục.
  Sửa plan: bước "bump `ASSET_VER`" là **sai** — `ASSET_VER` là hash tự tính của
  một danh sách tệp tĩnh cố định, **không có** `agent-canvas`; bundle Canvas do
  Vite đặt tên theo hash nội dung nên tự cache-bust. `server/templating.py` không
  bị đụng tới.
- `2026-09-27` `ui0` — Task 2 XONG. `_suy_kind_canh` + đấu vào `cau_truc`.
  `test_5601` 5/5 xanh; lưới hồi quy `1714 + 1719 + 1783 + 4250` = **81 passed**.
  🔴 **ĐỔI HÀNH VI (R3):** cạnh rời cổng `control` của một node có ≥2 cổng control
  nay mang `kind=CONTROL` + `condition=<tên cổng>`. Workflow hôm nay chạy **cả
  hai** nhánh của `core.if`; sau bản vá chạy **một** nhánh. Đúng, nhưng **phải báo
  chủ dự án TRƯỚC khi deploy** — nhánh lẽ ra không chạy hiện vẫn sinh job và bút
  toán thật.
- `2026-09-27` `ui0` — Task 1 XONG. `_node()` uỷ quyền `_node_loi` khi sổ công cụ
  app không có. `test_5600` 5/5 xanh; hồi quy `1714 + 4250 + 1783` = 62 passed.
- `2026-09-27` `ui0` — 🔴 **Sửa lỗi THIẾT KẾ trong plan trước khi viết mã.** Bước
  xác minh `nut_loi.tat_ca()` mà Task 1 dặn chạy đã bắt được: luật suy
  `(CONTROL, tên cổng)` của Task 2 sẽ gán `condition='nhanh'` cho `core.switch`
  (đo được: `core.switch` có **1** cổng control tên `nhanh`; tên nhánh nằm trong
  tham số `nhanh: array`) ⇒ động cơ so `_nhanh_da_chon(...) == "nhanh"`, không bao
  giờ khớp ⇒ **mọi nhánh switch chết**. Hôm nay switch chạy cả các nhánh (sai nhưng
  chạy) ⇒ bản suy bừa là **hồi quy tệ hơn**. Luật thu hẹp: **chỉ suy khi node nguồn
  có ≥ 2 cổng control** (`core.if` = 2 ✓, `core.switch` = 1 ✗). Thêm phép kiểm hồi
  quy ghim switch đi qua nguyên vẹn.
  ⚠️ **Khoảng trống còn lại:** `core.switch` vẫn chạy mọi nhánh — cần cửa đặt tên
  nhánh lên cạnh, thuộc **UI-4**, không thuộc UI-0.
- `2026-09-27` `ui0` — Mở làn. Dải số test **5600-5699** (quét 193 cây, cao nhất
  đang dùng `5562`). Dùng chính worktree audit làm làn, không tạo cây thứ hai.

- `2026-09-27` `điều phối` — Audit xong: 25,7/100 có trọng số, 0/5 luồng dựng được,
  7 điểm chặn. Plan TỔNG + plan UI-0 đã viết. ⭐ Trong lúc lập plan tìm ra cách sửa
  P0-1 **an toàn hơn** bản audit đề xuất: sửa ở cổng biên dịch (1 tệp backend, không
  di trú, mọi bản nháp production tự chạy được) thay vì sửa `nextNode` + di trú dữ
  liệu. Rủi ro R1 (di trú hỏng dữ liệu production) **bị loại bỏ hoàn toàn**.

## Điều phối liên phiên (27/09)

| Việc | Trạng thái |
|---|---|
| Phiên `Auto Scan Video final closure` định deploy HEAD `main` | ⏸ **đã dừng theo yêu cầu** — chốt phương án **A** |
| UI-0 đã ở trên `main` (`72ee199b`) | ✅ nhưng **CHƯA deploy** |
| Chủ dự án quyết deploy | ⏳ **đang chờ** — cả hai phiên cùng báo |

🔴 **Vì sao phải chặn.** Phiên kia chạy `git diff --name-only eb0335f5..HEAD`, thấy
thuần `docs/`, rồi kết luận deploy vô hại. Phép đo ấy đúng **lúc nó chạy**; vài phút
sau tôi ff-merge UI-0 (có mã, và có **đổi hành vi bút toán**) vào `main`.
⇒ **Một phép đo trên `main` có HẠN DÙNG.** `main` là trạng thái chia sẻ đang đổi;
phép đo phải chạy **ngay trước hành động**, ⛔ không phải trước đó mười phút.

⛔ **Phương án B (deploy từ `eb0335f5`) đã bị loại — có lý do kỹ thuật, đã tự kiểm:**
`setup/2-cai-dat.ps1:252` đóng cứng `git -C $src rev-parse HEAD` (đường deploy
**không nhận SHA**), và dòng ~272 chép `$VAN_CHUYEN` = `apps\*\vendor` + `yolov8n.pt`
từ **cây sống** — nhị phân vendor gitignored có chủ ý. Một worktree mới không có
chúng, và chú thích tại chỗ ghi hậu quả: app `upscalevideo` **chết IM LẶNG** trên
production (EXITCODE=0, `/health/ready` 200, `nghiem_thu_deploy` báo *thiếu 0* vì nó
**chỉ đếm tệp `.py`**).
⚠️ Phiên kia còn kể `axe.min.js` trong nhóm sẽ thiếu — **sai**: nó cố ý **không** nằm
trong `$VAN_CHUYEN` (người đọc duy nhất là `tools/check_a11y.py`, chạy từ cây nguồn
**trước** deploy). Không đổi kết luận, nhưng một mục sai trong một danh sách an toàn
sẽ khiến lần sau có người đi kiểm thứ vô hại và bỏ qua thứ thật — cùng họ với cái bẫy
`.typed-port "44px"` ở §Task 4.

**Gate:** một lượt gate XANH trên đúng SHA sẽ deploy (SHA đó chứa cả UI-0) **chính là**
bằng chứng cho UI-0. ⛔ Tôi không chạy lượt thứ hai: `l3_lai_bi_chan` khoá theo
(nhánh, cây), và "cuối plan" của tôi là sau **UI-11** — còn xa, trên mã mới hơn nhiều.
