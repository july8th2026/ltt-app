# Sổ tiến độ — Agent UI V2

Cập nhật lần cuối: 2026-09-27 · bởi: làn `ui3` (tách CanvasShell)

> ⛔ **Trạng thái công việc ghi vào TỆP NÀY, không chỉ trong hội thoại.** Một phiên
> bị `/compact` mất hội thoại; tệp thì còn.
> Plan điều phối: `docs/superpowers/plans/2026-09-27-agent-ui-v2-TONG.md`

## Bảng pha

Trạng thái hợp lệ (⛔ không tự chế thêm):
`CHƯA MỞ` · `ĐANG LÀM` · `CHỜ DUYỆT` · `ĐÃ GỘP` · `CHẶN`

| Pha | Làn | Trạng thái | Nhánh | Tệp SỞ HỮU | Gộp main | Ghi chú |
|---|---|---|---|---|---|---|
| UI-0 Lỗi P0 cơ khí | `ui0` | ✅ **ĐÃ GỘP** (`72ee199b`) | `claude/ltt-agent-automation-ux-audit-9e3764` | *(đã trả phiếu)* | ✅ | dải **5600-5699** · nghiệm thu trình duyệt PASS · ⏸ chưa deploy (chủ dự án: deploy CUỐI) |
| UI-3 Tách CanvasShell | `ui3` | ✅ **ĐÃ GỘP** | `phien/agent-ui-v2-ui3` | `src/**/*.tsx` · `editorState.ts` · `features/editor/**` | — | dải **5700-5799** · **ĐÃ MỞ KHOÁ song song hoá** — 31 tệp, lớn nhất 179 dòng · 165 test xanh · trình duyệt PASS |
| UI-2 Design system | `ui2` | ✅ **ĐÃ GỘP** | `worktree-agent-a710623353e7caab2` | **chỉ** `canvas.css` | — | dải **5800-5899** · hex 482→**63** · lớp chết 79→**0** · `@media 640px` 6→**1** · theme sáng 20/20 ô tối→**0/20** · ⚠️ 2 tiêu chí KHÔNG đạt, xem nhật ký |
| UI-N Nhãn ngắn node LTT | `uiN` | ✅ **ĐÃ GỘP** (`868f9db2`) | — | *(đã trả phiếu)* | ✅ | dải **5900-5999** · LTT_APPS 16/17 → **0/17** nhãn > 40 ký tự |
| UI-1 Automation Studio | `ui1` | **ĐANG LÀM** (agent) | worktree riêng | `apps/agent/routes/**` · `templates/**` | — | dải **6200-6299** · Q1 đã chốt = **B** · chủ **S5** |
| UI-4 Node UX V2 | `ui4` | **ĐANG LÀM** (agent) | worktree riêng | `src/nodes/**` · `WorkflowCanvas.tsx` · `useDisplayGraph.ts` | — | dải **6000-6099** |
| UI-7 Execution + Runs | `ui7` | **ĐANG LÀM** (agent) | worktree riêng | `ExecutionPanel/**` · `RunV3Panel/Inspector/Diff` · `workflowApi.ts` | — | dải **6100-6199** · chủ **S4** |
| UI-5 Inspector + Connections | `ui5` | **ĐANG LÀM** (agent) | worktree riêng | `ket_noi_v3.py` (mới) · `StepInspector/**` · `src/inspector/**` | — | dải **6300-6399** · Q4 đã chốt |
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
| ui3 | `frontend/agent-canvas/src/CanvasShell.tsx` → `src/features/editor/**` | 27/09 | **S2** |
| ui3 | `frontend/agent-canvas/src/editorState.ts` | 27/09 | **S3** (nhận bàn giao từ ui0) |


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
| Q1 | Kiến trúc thông tin | ✅ **B — Automation Studio** | 28/09 | điều phối (bằng chứng đã quyết) |
| Q4 | Tầng OAuth | ✅ **C** — CLOUD cho nhà cung cấp chính + self-managed | 28/09 | **chủ dự án**, và **nhận rủi ro** |
| Q11 | Trigger: mở `trigger.manual`? | ✅ **ĐÃ MỞ** — `ba51c9f0` | 28/09 | đo được sau UI-0; schedule/webhook vẫn là plan backend RIÊNG |
| Q2 | UI-0 làm thành phase riêng, deploy độc lập | **CHƯA** | | khuyến nghị A, độ tin CAO |
| — | Giữ `@xyflow/react` | ✅ CHỐT | 27/09 | bằng chứng: dùng 11/30 API |
| — | Sửa P0-1 ở **cổng biên dịch**, ⛔ không di trú dữ liệu | ✅ CHỐT | 27/09 | `…-TONG.md` §1.5 |

## Rủi ro đang mở

| # | Rủi ro | Trạng thái |
|---|---|---|
| **R3** | Task 2 của UI-0 **đổi hành vi**: `core.if` nay chạy **một** nhánh thay vì cả hai | ⚠️ phải báo chủ dự án **trước khi deploy** |
| R7 | 3 hạng mục (media preview, test một bước, run history) **không đạt 98 bằng công việc UI** | đã ghi ở `10_IMPLEMENTATION_PLAN.md` §3 |
| R8 | Phình phạm vi ở UI-1 (chia sẻ, phân quyền, marketplace) | UI-1 chỉ làm điều hướng + 5 trang |
| R10 | Hai làn cùng sửa `canvas.css`/`CanvasShell.tsx` | ✅ **KHÉP phía UI-3**: đo được `git diff -- canvas.css` RỖNG và tập `className` 97→97 (MẤT 0/THÊM 0) |

## Nhật ký

_(mới nhất ở trên)_

- `2026-09-28` `điều phối` — **CHỐT Q4 = C, chủ dự án NHẬN RỦI RO. Mở UI-5.**
  LTT quản lý OAuth app cho **nhà cung cấp chính**, khách **tự mang app** cho
  phần còn lại. Đây là câu duy nhất tôi ⛔ không tự quyết được, vì nó cam kết LTT
  đi xin duyệt app với Google/YouTube và **chịu hạn mức API thay khách** — ràng
  buộc pháp lý/vận hành nằm **ngoài mã**.

  ⭐ **Và hoá ra UI-5 nhỏ hơn audit ước lượng.** Audit xếp nó cỡ **L** với lý do
  *"cần CRUD credential + OAuth callback"*. Đọc `platform_core/credential.py` thì
  phần khó nhất **đã có và làm rất kỹ**:

  ```
  tao · liet_ke · kiem_ref · thay_bi_mat · thu_hoi · lay_de_dung · xoay_khoa
  Fernet (MultiFernet — xoay khoá được) · sổ nhật ký CredentialNhatKy
  META_CAM = access_token · refresh_token · client_secret · password  <- CẤM trong `meta`
  ```

  Và hai cửa chặn đã đấu sẵn: `bien_dich._node_tu_dinh_nghia` **đã đọc**
  `credential_ref`, `dinh_nghia._kiem_credential` **đã chặn ở publish**.

  ⇒ Thiếu đúng **hai** thứ: cửa HTTP cho khách, và giao diện. Đó là việc **nối
  dây**, ⛔ không phải xây mới. Brief bắt UI-5 dùng lại, ⛔ cấm viết lại lớp lưu
  trữ hay tự mã hoá. *(Đúng luật "dùng lại trước, tự viết sau" — và nó vừa cắt
  một hạng mục từ L xuống M.)*

  ⚠️ **Phần LTT-quản-lý-app ⛔ không làm được trong phiên này:** đăng ký OAuth app
  là thao tác trên dashboard ngoài + bí mật vào `secrets/`, tức **việc chỉ chủ dự
  án làm được**. Brief chỉ định dựng **cấu trúc** + trạng thái *"chưa cấu hình"*
  rõ ràng, và **sinh một wizard** để chủ dự án tự làm. ⛔ Tuyệt đối không tự nhập
  bí mật, ⛔ không bịa một luồng giả vờ hoạt động.

  **Bốn làn đang chạy song song:** UI-4 · UI-7 · UI-1 · UI-5. Tệp sở hữu rời nhau;
  một chỗ **cố ý** để lại cho điều phối: UI-5 viết module route **mới** và ⛔
  không đụng `routes/__init__.py` (của **UI-1**, chủ **S5**) — điều phối đấu dòng
  import lúc gộp.

- `2026-09-28` `điều phối` — **ĐỢT 2: mở ba làn song song.** UI-3 đã tách
  `CanvasShell` nên mỗi mặt có chủ riêng; đây là lần đầu ba làn **thật sự** không
  giẫm nhau.

  | Làn | Sở hữu | Dải test |
  |---|---|---|
  | **UI-4** Node UX V2 | `src/nodes/**` · `WorkflowCanvas.tsx` · `useDisplayGraph.ts` | 6000-6099 |
  | **UI-7** Execution UX | `ExecutionPanel/**` · `RunV3Panel/Inspector/Diff` · `workflowApi.ts` | 6100-6199 |
  | **UI-1** Automation Studio | `apps/agent/routes/**` · `templates/**` | 6200-6299 |

  ⭐ **Hai điều đưa vào brief lần này mà lần trước thiếu** (cả hai học từ đợt 1):
  1. **"Commit từng bước, và nền là `main` HIỆN TẠI"** — đợt 1 một làn ⛔ không
     commit và nhánh lùi **15 commit**; đó là lỗi brief của tôi.
  2. **"Đặt khung nhìn TƯỜNG MINH trong kịch bản trình duyệt"** — profile dùng
     chung giữa các kịch bản, và một kịch bản mobile để lại 390px làm nút "Chạy"
     bị `disabled` ⇒ kịch bản sau treo 30 giây rồi chết với một thông điệp ⛔
     không hề nhắc tới khung nhìn.

  🔴 **UI-7 nhận một ràng buộc riêng về CÁCH nghiệm thu**, vì hai trần cứng cộng
  dồn (§3b.3b): worker nạp **mã đã deploy** *và* chạy dưới **`LocalSystem`**.
  ⇒ Brief chỉ định **đo lớp trình bày bằng dữ liệu run GIẢ**, và bắt trả lời
  trước một câu: *cửa nào cho tôi đặt được trạng thái tôi cần đo?* Nếu ⛔ không có
  cửa thì dựng cửa là **việc đầu tiên**, ⛔ không phải việc cuối.

- `2026-09-28` `điều phối` — **CHỐT Q1 = B (Automation Studio).** ⛔ Không hỏi lại:
  bằng chứng đã quyết và độ tin CAO (`08_DECISION_QUESTIONS.md` Q1).
  **Lý do rút gọn:** 11 hạng mục chấm **0**, phần lớn vì *"tính năng này không có
  nhà"* (Run history, Templates, Connections, Version UX). Backend **đã** hỗ trợ
  nhiều workflow / phiên bản / credential / so sánh run; giao diện chỉ có **hai**
  trang HTML và luôn mở `items[0]`. B là việc **nối dây cái đã có**, ⛔ không phải
  xây mới.
  **Cái giá nếu sai:** ~3 pha cho điều hướng + 5 trang. Nếu sau này đo được rằng
  khách chỉ muốn gõ một câu rồi nhận kết quả (hướng C, Agent-first), công ấy
  **⛔ không mất** — C dùng lại toàn bộ Runs/Connections/Templates của B và chỉ
  đổi **trang mặc định**. Chiều ngược lại mới là một lần viết lại.
  ⇒ **UI-1 và UI-9 hết chặn.**

- `2026-09-28` `điều phối` — **Q11 trả lời được vì UI-0 đã sửa đúng cái chặn nó.**
  Lúc lập plan tôi để Q11 ở độ tin **THẤP** với lý do *"cần một người đọc
  `bien_dich` xác nhận `core.*` đã compile được chưa"*. UI-0 Task 1 chính là việc
  đó ⇒ câu hỏi thành **đo được**, ⛔ không còn là câu hỏi ý kiến.

  🔴 **Và phép đo cứu tôi khỏi một bản vá tệ hơn bệnh.** Lật cờ `publish_duoc`
  một mình sẽ cho ra node **publish sạch rồi FAILED lúc chạy**
  (`dong_co._chay_mot_inline`: thiếu bộ thi hành ⇒ `loi_he_thong`). Hiện trạng ít
  ra chặn **trước** khi khách bấm Chạy và giữ tiền. ⇒ Đăng ký bộ thi hành trước,
  mở cờ sau.

  | | Trước | Sau |
  |---|---|---|
  | trigger dùng được | **0/7** | **1/7** |
  | tổng node dùng được | 35/72 | **36/72** |

  ⚠️ Còn chặn vì `publish_duoc`: `ai.llm`, `ai.extract`, `ai.router` (plan 10).
  `trigger.schedule` / `trigger.webhook` **⛔ không tồn tại trong registry** — đó
  là một plan **backend riêng**, ⛔ không nhét vào plan UI.

- `2026-09-27` `điều phối` — **UI-3 và UI-2 đã KIỂM và GỘP vào nhánh điều phối.**
  Ba nghiệm thu trình duyệt thật đều `PASS` sau khi gộp cả hai:
  UI-0 (15 cổng/15 vị trí/vùng bấm 24px, kéo dây ra 1 cạnh) · UI-3 mobile (4 tab
  đúng, 7/7 ô khoá) · UI-2 (16/16 `elementFromPoint` trả về chính cổng).
  165/165 vitest xanh.

  🔴 **Điều phối bắt được MỘT LỖI THẬT mà làn UI-3 tự nhận "chưa chắc":** trên
  mobile, bấm một node rồi đổi tab thì Inspector **dính cứng** — tab "Công cụ" và
  "Canvas" vẫn hiện nó, đè lên khung vẽ. Đây là **lỗi kế thừa** từ `CanvasShell`
  cũ (điều kiện `desktopPanel==='inspector' || mobilePanel==='inspector'`), ⛔
  không phải do UI-3 gây ra — họ giữ nguyên đúng như yêu cầu. Nó chỉ lộ ra vì đây
  là **phép kiểm đầu tiên ĐỔI TAB**; mốc nền 27/09 chỉ bắt được nửa trước của nó.
  ⇒ Bài học: *"tự nhận chưa chắc" là một tín hiệu đáng tiền — phải đi kiểm, đừng
  gật.*

  ⚠️ **Một phép kiểm cũ phải sửa, và đó là LÀM CHẶT:** `CanvasShell.test.tsx`
  bấm **tab mobile** trong khi jsdom báo bề rộng 1024 — một trạng thái ⛔ không
  xảy ra được ngoài đời (thanh tab mobile là `display:none` ở màn rộng). Nay đặt
  bề rộng 390 thật, và khẳng định thêm điều trước đây không ai giữ: **đổi tab
  phải TẮT Inspector**.

  ⚠️ **Kịch bản nghiệm thu UI-0 có một lỗi phụ thuộc thứ tự:** nó không đặt khung
  nhìn, nên chạy sau kịch bản mobile thì thừa hưởng 390px ⇒ `readOnly=true` ⇒ nút
  "Chạy" `disabled` ⇒ treo 30 giây rồi chết với một thông điệp ⛔ không hề nhắc
  tới khung nhìn. Đã đặt khung nhìn tường minh. *Một phép kiểm phụ thuộc thứ tự
  chạy là một phép kiểm sẽ đỏ vì lý do sai.*

- `2026-09-27` `điều phối` — **Phán quyết hai tiêu chí UI-2 tự nhận KHÔNG đạt:**

  | Tiêu chí | Đích | Thật | Phán quyết |
  |---|---|---|---|
  | hex cứng trong `canvas.css` | ≤ 25 | **63** (482 trước) | ✅ **CHẤP NHẬN** |
  | tương phản nền minimap/controls | 3:1 | **1,08:1** (viền 1,45:1) | ❌ **ĐỂ MỞ** |

  **Vì sao chấp nhận 63:** đo lại — **20/63 là ĐỊNH NGHĨA token** (`--x: #hex`);
  ⛔ không thể định nghĩa một token mà không có literal. Phần còn lại chủ yếu là
  `#fff` và đen-alpha (`#0009`, `#000c`) cho bóng đổ/lớp phủ. Tiêu chí "≤ 25" của
  tôi đặt **tuỳ tiện**; ép cho đủ chỉ dẫn tới **lách regex bằng `rgb()`** — mà làn
  UI-2 đã cố ý ⛔ không làm và báo số thật. 482 → 63 là một cải thiện thật.

  **Vì sao KHÔNG chấp nhận 1,08:1:** `09_TARGET_DESIGN.md` §12 đặt đích **WCAG 2.2
  AA**, và **1.4.11 (Non-text Contrast)** đòi **3:1** cho ranh giới thành phần giao
  diện. Viền 1,45:1 ⛔ chưa đạt. Lập luận của UI-2 (*"panel nổi khác đều dựa vào
  bóng, không dựa vào nền"*) là một lập luận **thiết kế**, ⛔ không phải một phép
  đo đạt chuẩn. ⇒ Chuyển thành **hạng mục MỞ của UI-10 (trợ năng)**, ⛔ không đánh
  dấu đã xong. Nếu chủ dự án chấp nhận lệch chuẩn ở chỗ này thì đó là một quyết
  định sản phẩm và phải ghi ra, ⛔ không im lặng.

  ⚠️ Tôi cũng **đếm sai một lần**: báo 2 khối `@media 640px` trong khi chỉ có **1**
  — dòng thứ hai là một **chú thích** nhắc tới nó. Lời khai của UI-2 đúng.

- `2026-09-27` `uiN` — **XONG, đã gộp `868f9db2`.** LTT_APPS **16/17 → 0/17** nhãn
  vượt 40 ký tự; các nhóm khác 0/n, không bị đụng. Thêm trường tuỳ chọn `ten_ngan`
  trên `ToolSpec`/`CongCu` để **chính app tự khai**, `_tieu_de` lùi về hành vi cũ
  khi vắng. `test_967` (28 test) vẫn xanh ⇒ không phải bảng tra tập trung.

  🔴 **Ba thứ điều phối phải sửa sau agent** — ghi ra vì cả ba đều là bẫy lặp lại:
  1. **Agent KHÔNG commit** và nhánh của nó **lùi 15 commit** (không có UI-0). Lỗi
     brief của tôi: chỉ dặn "commit thường xuyên" trong brief UI-3. ⇒ **Brief sau
     phải luôn có: commit, và rebase/nền là `main` hiện tại.**
  2. **Hai nhãn TRÙNG `app_name`** (`taovideo`, `video_assembly`). Node hiện `title`
     ở đầu và `app_name` ở thân (`ThanApp`) ⇒ trùng nghĩa là **cùng một chữ hiện hai
     lần trên một node**. Agent không thấy vì nó không đọc `NodeRenderer`. Đã đổi;
     đo lại **0/17** trùng.
  3. **16 chuỗi mới chưa vào catalog EN** — bánh cóc `ban-dich-thieu` bắt. Đúng cái
     tôi phê trong audit (§8.4 i18n = 0). Đã thêm **tay** vào `.po`; ⛔ **không** chạy
     `i18n.py trich` vì `msgmerge` sẽ **đoán** bản dịch — một bản dịch đoán là lỗi im
     lặng: hiện ra cho khách, đúng ngữ pháp, sai nghĩa.

  ⚠️ **Chưa chắc, cần chủ dự án chốt:** `text.chat` → "Sinh văn bản bằng LLM". Mô tả
  của nó phủ 4 việc khác nhau (coding/chat/agent/tóm tắt); tên này an toàn nhưng
  chung chung.
- `2026-09-27` `ui3` — **UI-3 XONG — `CanvasShell.tsx` 959 dòng → `features/editor/` (31 tệp).**
  Nghiệm thu trình duyệt thật (chế độ A): **`status: PASS`**, 0 pageerror · 0 console
  error · 0 request hỏng · 0 phản hồi 5xx.
  ⚠️ Cổng **8197**, không 8198 — một phiên khác đang giữ 8198; ⛔ không giết tiến
  trình của làn khác để lấy một con số cho đẹp.

  | Phép đo | Trước | Sau |
  |---|---|---|
  | tệp lớn nhất của trình soạn | **959 dòng** (`Editor()` 740) | **177 dòng** (`useWorkflowRun`) |
  | `useState` trong một hàm | **33** | **5** (`EditorShell`) |
  | tệp > 250 dòng trong `features/editor/` | — | **0** |
  | test vitest | 156 xanh | **165 xanh**, ⛔ không sửa một test cũ nào |
  | tập hợp `className` | 97 | **97** — MẤT 0, THÊM 0 (đo bằng script) |
  | `git diff -- canvas.css` | — | **RỖNG** (S1 của UI-2 còn nguyên) |
  | autosave trên mạng THẬT | chưa ai đo | **0 PUT @400ms · đúng 1 PUT @1,8s** |

  **Sửa lỗi đi kèm:** `case 'replace'` trả `past: []` ⇒ "Soạn bằng AI" ghi đè đồ thị
  và **Ctrl+Z không cứu được**. Nay đi qua `changed()` khi `giuLichSu: true`; lượt
  NẠP lúc mở trang vẫn đặt lại lịch sử (nếu không, Ctrl+Z về **canvas trắng**).

  🔴 **Đặc tả trước khi di chuyển.** Kiểm kê 6 hành vi tinh vi của R4: 4 đã có phép
  kiểm, **2 thì không** (autosave 800 ms, `updateNodeInternals` theo rAF). Viết
  `tests/CanvasShellDacTa.test.tsx` cho hai cái ấy, xanh TRƯỚC khi tách.
  ⚠️ Bẫy đã tránh: `workflowApi.test.ts` có bài *"debounces autosave"* — nó đo
  `createAutosave(save,500)`, một helper `CanvasShell` **không hề gọi**. Đọc thứ
  ĐẠI DIỆN thay vì thứ THẬT thì tách xong vẫn xanh trong lúc autosave thật đã chết.
  Cả 4 phép đo mới đều **tiêm lỗi để chứng minh không xanh giả**.

  🔴 **Hai lần phép đo của TÔI sai, không phải mã sai** — cùng dạng bẫy `ui0` đã ghi:
  1. bản dọn rAF đo bằng `spyOn(cancelAnimationFrame)` ⇒ **XANH GIẢ**:
     `@xyflow/react` tự gọi hàm ấy cho việc của nó, nên phép đo vẫn xanh sau khi
     tôi gỡ hẳn khối rAF. Đổi sang đo **hệ quả** (callback đang chờ không được chạy).
  2. kịch bản trình duyệt khẳng định `rail.x < stage.x` và ĐỎ — nhưng
     `canvas.css:112` đặt `.canvas-rail{position:absolute}` **đè lên** khung vẽ
     (`x=0`). Tôi đo một quan hệ **chưa bao giờ tồn tại**. Đổi sang đo thứ đáng
     đo: nút ở thanh dọc có **bấm được** không (`elementFromPoint`).

  ⚠️ **Ba chỗ suýt mất hành vi lúc tách** (chi tiết ở commit `refactor(canvas)`):
  `xoaLuaChon` vs `boChon` · phải chuột KHÔNG mở inspector · `commandQuery` phải
  ở `EditorShell` (bản gốc chỉ xoá nó sau khi CHẠY một lệnh, nên `Esc` giữ chữ).
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
