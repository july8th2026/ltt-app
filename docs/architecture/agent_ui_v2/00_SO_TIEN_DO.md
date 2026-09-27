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
| UI-0 Lỗi P0 cơ khí | `ui0` | **ĐANG LÀM** | `claude/ltt-agent-automation-ux-audit-9e3764` | `bien_dich.py` · `workflowApi.ts` · `canvas.css` · `NodeKhung.tsx` · `editorState.ts` · `CanvasEdgeView.tsx` | — | dải test **5600-5699** |
| UI-3 Tách CanvasShell | — | CHƯA MỞ | — | — | — | chặn bởi UI-0. **Mở khoá song song hoá** |
| UI-2 Design system | — | CHƯA MỞ | — | — | — | chặn bởi UI-3 · chủ S1 (`canvas.css`) |
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
| ui0 | `server/templating.py` (chỉ `ASSET_VER`) | 27/09 | — |

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
| UX-3 Manual → Ảnh → Video → Giọng → Render | ❌ | — | **UI-0** |
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
