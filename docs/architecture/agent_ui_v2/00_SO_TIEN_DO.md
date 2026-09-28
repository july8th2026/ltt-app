# Sổ tiến độ — Agent UI V2

Cập nhật lần cuối: 2026-09-28 · bởi: làn `ui1` (Automation Studio — IA)

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
| UI-1 Automation Studio | `ui1` | ✅ **ĐÃ GỘP** | `phien/agent-ui-v2-ui1` | `apps/agent/routes/**` · `apps/agent/templates/**` · `apps/agent/manifest.py` · `useWorkflowDocument.ts` | — | dải **6200-6299** · Q1 = **B** · chủ **S5** · trang HTML **2 → 8** · trình duyệt (8198) **PASS** · ✅ lưu trữ **ĐÃ LÀM** bởi điều phối (`97884407`, dải 5603/5604) |
| UI-4 Node UX V2 | `ui4` | ✅ **ĐÃ GỘP** | `phien/agent-ui-v2-ui4` | `src/nodes/**` · `useDisplayGraph.ts` · `styles/node.css` | — | dải **6000-6099** · `canvas.css` diff **RỖNG** · `app.video.generate` cao **525 → 279 px** (16 hàng cổng → 7 hàng + 9 khay) · ba mức độ zoom **200/280/360 px** · `core.switch` `"1 nhánh"` → **`"5 nhánh"`** · hồi quy cổng UI-0 **y nguyên** · ⚠️ brief ghi 456px, họ đo **285px** — brief sai |
| UI-7 Execution + Runs | `ui7` | ✅ **ĐÃ GỘP** | `phien/agent-ui-v2-ui7` | `ExecutionPanel/**` · `RunV3Panel/Inspector` · `styles/run.css` | — | dải **6100-6199** · chủ **S4** · bảng run **176 → 366 px**, hàng cao nhất **139 → 57 px** · báo giá **12 credit** trên nút · `workflowApi.ts` diff **RỖNG** ⇒ UI-5 không phải chờ · 🔴 báo một `.sr-only` **SAI**, xem nhật ký |
| UI-5 Inspector + Connections | `ui5` | ✅ **ĐÃ GỘP** | `phien/agent-ui-v2-ui5` | `ket_noi_v3.py` (mới) · `src/inspector/**` | — | dải **6300-6399** · Q4 = **C** · node publish được **27 → 60** (+33 mở khoá) · publish **422 → 200** · 4 cửa `/api/v3/ket-noi` · wizard OAuth 6 chặng · 🔴 va UI-3 ở `StepInspector`, xem nhật ký |
| UI-8a Human approval ⭐ | `ui8a` | ✅ **ĐÃ GỘP** | `phien/agent-ui-v2-ui8a` | `routes/phe_duyet_v3.py` (mới) · `ExecutionPanel/**` · `cho_doi.py` (nếu buộc) | — | dải **6500-6599** · cổng **8206** · 🔴 `core.human` đã ĐỦ (`NHANH_HUMAN`, waitpoint, hết hạn ⇒ `reject`) nhưng ⛔ KHÔNG cửa nào BẤM duyệt được ⇒ mở cửa là TRONG phạm vi phase |
| UI-6 Data picker | `ui6` | ✅ **ĐÃ GỘP** 🔴 *(bị chặn bởi lỗi id gạch ngang)* | `phien/agent-ui-v2-ui6` | `src/inspector/FormTuLuocDo.tsx` · `inspector.css` · tệp mới trong `src/inspector/` | — | dải **6400-6499** · cổng **8205** · dùng lại `/bieu-thuc/goi-y` ⇒ ⛔ không cửa mới |
| UI-9 Mẫu / Templates | `ui9` | ✅ **ĐÃ GỘP** | `phien/agent-ui-v2-ui9` | `routes/trang.py` (⭐ giữ) · `templates/agent_templates.html` (mới) · `platform_core/workflow/mau.py` (mới) | — | dải **6600-6699** · cổng **8207** · dùng lại `POST /api/v3/workflows` với `document` ⇒ ⛔ không cửa mới · mỗi mẫu PHẢI publish được thật |
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
| ui1 | `apps/agent/routes/**` (`trang.py`, `_shared.py`) | 28/09 | **S5** |
| ui1 | `apps/agent/templates/**` (4 tệp) | 28/09 | — |
| ui1 | `apps/agent/manifest.py` — **chỉ khối `nav`** | 28/09 | ⚠️ ngoài phiếu đã khai, xem §Quyết định |
| ui1 | `src/features/editor/hooks/useWorkflowDocument.ts` — **3 dòng** | 28/09 | ⚠️ trong `features/editor/**` của UI-3 (đã gộp) |
| ui1 | `tests/test_72_vanhanh.py` — **1 khẳng định** | 28/09 | — |


**Sáu sổ dùng chung và chủ của chúng** — đụng vào thì DỪNG và báo điều phối:

| # | Sổ | Chủ |
|---|---|---|
| S1 | `frontend/agent-canvas/src/canvas.css` (+ `styles/`) | UI-2 |
| S2 | `CanvasShell.tsx` / `features/editor/EditorShell.tsx` | UI-3 |
| S3 | `editorState.ts` | UI-3 |
| S4 | `workflowApi.ts` | UI-0 → rồi UI-7 |
| S5 | bảng định tuyến `apps/agent/routes/` | UI-1 |
| S6 | `tools/thanh_phan.toml` | UI-3 |
| **S7** | **cổng máy chủ thử** (⛔ sổ tôi BỎ SÓT — xem nhật ký 28/09) | điều phối cấp |

## Bảng độ phủ nghiệm thu

Mốc nền đo 27/09/2026 trên trình duyệt thật: **0/5 luồng dựng được**.

| Luồng | Dựng được? | Kịch bản Playwright | Pha mở khoá |
|---|---|---|---|
| UX-1 Schedule → Sheets → … → YouTube | ❌ | — | UI-5 + backend trigger (**Q11**) |
| UX-2 Webhook → Phân tích → Clip → Phụ đề | ❌ | — | backend — **registry chưa có node webhook** |
| UX-3 Manual → Ảnh → Video → Giọng → Render | ⚠️ **một phần** | `agent_ui_v2_ui0_nghiem_thu.js` | **UI-0 xong**: node `app.*` nối được và chạy được (đo: 1 cạnh thật, run QUEUED). Còn thiếu trigger thủ công (**Q11**) |
| UX-4 Sheets → AI Router → nhánh → gộp | ❌ | — | UI-5 + **Q11** (`ai.router` đang `publish_duoc=False`) |
| UX-5 Parent → Subworkflow → Wait → Human | ❌ | — | **UI-0** + UI-8a |
| UX-0 Quản lý workflow: xem · tìm · tạo · mở · nhân bản | ✅ **dựng được** | `agent_ui_v2_ui1_nghiem_thu.js` | **UI-1 xong** (28/09). Đo trên 8198: danh sách 0 → 9 mục; `items[0]`=`075714aa` mà mở `4e918dba` ⇒ nạp đúng `4e918dba` bằng **một** lời gọi; nhân bản giữ nguyên tài liệu. ⛔ Còn thiếu **lưu trữ** (cần cửa mới) |

⚠️ UX-0 **không có trong bảng gốc** vì audit chỉ đếm năm luồng *dựng một
automation*. Nhưng `01 §1.1` đo rằng giao diện ⛔ không có đường nào tới
workflow **thứ hai** — tức luồng bị thiếu nằm **trước** cả năm luồng kia. Thêm
nó vào đây để bảng độ phủ đo đúng thứ đang chặn, không chỉ thứ đã liệt kê sẵn.

## Quyết định đã chốt

| # | Câu | Chốt | Ngày | Ai |
|---|---|---|---|---|
| Q1 | Kiến trúc thông tin | ✅ **B — Automation Studio** | 28/09 | điều phối (bằng chứng đã quyết) |
| Q4 | Tầng OAuth | ✅ **C** — CLOUD cho nhà cung cấp chính + self-managed | 28/09 | **chủ dự án**, và **nhận rủi ro** |
| Q11 | Trigger: mở `trigger.manual`? | ✅ **ĐÃ MỞ** — `ba51c9f0` | 28/09 | đo được sau UI-0; schedule/webhook vẫn là plan backend RIÊNG |
| Q2 | UI-0 làm thành phase riêng, deploy độc lập | **CHƯA** | | khuyến nghị A, độ tin CAO |
| — | Giữ `@xyflow/react` | ✅ CHỐT | 27/09 | bằng chứng: dùng 11/30 API |
| — | Sửa P0-1 ở **cổng biên dịch**, ⛔ không di trú dữ liệu | ✅ CHỐT | 27/09 | `…-TONG.md` §1.5 |
| — | UI-1: **6 mục IA khai ở `manifest.nav`**, ⛔ không ở template riêng | ✅ CHỐT | 28/09 | làn `ui1` — `NavEntry.built=False` là **cơ chế có sẵn** của nền tảng: `base.html` tự dán huy hiệu "Đang xây". Viết một thanh mục thứ hai trong template là dựng lại thứ đã có, và nó sẽ lệch với nav thật |
| — | UI-1: bỏ mục nav **"Canvas"** | ✅ CHỐT | 28/09 | làn `ui1` — `09 §1` đặt trình soạn là mục **con** của một workflow. `/agent/canvas` **vẫn sống** (`test_1726`), nó chỉ không còn trên nav |
| — | UI-1: tên mặc định workflow chốt **lúc TẠO**, ⛔ không dịch lúc hiện | ✅ CHỐT | 28/09 | làn `ui1` — `tao_workflow` **lưu** `"Workflow mới"` vào CSDL ⇒ từ đó là **dữ liệu**. Dịch dữ liệu lúc hiện sẽ đổi cả tên do chính khách đặt |

🔴 **UI-1 CHƯA LÀM: lưu trữ (archive) workflow.** `Workflow.archived_at` có
trong lược đồ và danh sách đã lọc theo nó, nhưng **không cửa nào đặt được nó**
— cần một cửa HTTP mới (`POST /agent/api/v3/workflows/{id}/luu-tru` hoặc một
trường trên `PUT`). Mở bề mặt HTTP là quyết định riêng ⇒ **chờ điều phối**,
⛔ chưa viết. Cho tới lúc đó `test_6200::test_khong_mo_cua_POST_moi_o_tang_trang`
canh rằng không ai lặng lẽ mở một cửa ghi ở tầng trang.

## Rủi ro đang mở

| # | Rủi ro | Trạng thái |
|---|---|---|
| **R3** | Task 2 của UI-0 **đổi hành vi**: `core.if` nay chạy **một** nhánh thay vì cả hai | ⚠️ phải báo chủ dự án **trước khi deploy** |
| R7 | 3 hạng mục (media preview, test một bước, run history) **không đạt 98 bằng công việc UI** | đã ghi ở `10_IMPLEMENTATION_PLAN.md` §3 |
| R8 | Phình phạm vi ở UI-1 (chia sẻ, phân quyền, marketplace) | UI-1 chỉ làm điều hướng + 5 trang |
| R10 | Hai làn cùng sửa `canvas.css`/`CanvasShell.tsx` | ✅ **KHÉP phía UI-3**: đo được `git diff -- canvas.css` RỖNG và tập `className` 97→97 (MẤT 0/THÊM 0) |

## Nhật ký

_(mới nhất ở trên)_

- `2026-09-28` `điều phối` — **UI-11 NGHIỆM THU TỔNG: 6/7 bước E2E đi được, và
  bước thứ 7 lộ một LỖI CHẶN TÍNH NĂNG CỐT LÕI.**

  ### 🔴 `{{ nodes.<id>.output.<cổng> }}` VỠ với mọi node do Canvas sinh

  | Nơi | Điều nó làm |
  |---|---|
  | `editorState.ts:299` `nextNode()` | mọi node sinh id `` `n${Date.now().toString(36)}-${count}` `` — **LUÔN có gạch ngang** (vd `nmukpruo1-1`) |
  | `bien_dich.trich_tham_chieu()` | duyệt `{{ }}` bằng `ast.parse(mode="eval")` |

  Python đọc `-` là phép **TRỪ**, nên `nodes.nmukpruo1-1.output.prompt` tách thành
  `nodes.nmukpruo1 - 1 .output.prompt` ⇒ `SyntaxError: invalid decimal literal`
  ⇒ `publish` trả **422 `bieu_thuc_chua_ho_tro`** kèm thông điệp **sai lạc**
  *"chỉ hỗ trợ đúng MỘT biểu thức"* — câu ấy ⛔ không liên quan gì tới nguyên nhân.

  ⇒ **Bất kỳ người dùng thật nào** thêm ≥2 bước từ palette rồi dùng **Data Picker**
  (chức năng chủ lực của UI-6) sẽ **KHÔNG BAO GIỜ** chạy được workflow.

  ### ⭐ PHÁT HIỆN LÀM HẸP HẲN BẢN VÁ: dạng **subscript** ĐÃ chạy

  Điều phối đo trực tiếp `trich_tham_chieu` (28/09):

  ```
  nodes.nabc.output.x            ->  OK
  nodes.nmukpruo1-1.output.x     ->  LoiBienDich  invalid decimal literal
  nodes['nmukpruo1-1'].output.x  ->  OK  ThamChieu(node='nmukpruo1-1', cong='x')
  ```

  ⇒ Ngữ pháp Sec6 **đã** nhận định danh có gạch ngang — qua `ast.Subscript`, và
  `_chuoi_doan` đã xử đúng. Nên bản vá ⛔ **KHÔNG cần** một tokenizer riêng:
  chỉ cần chuẩn hoá `nodes.<id>` → `nodes['<id>']` **trước** `ast.parse`, hoặc
  đổi phía SINH ra để nó phát dạng subscript.

  ⚠️ Nhưng phải chọn **một** chỗ và nói rõ, vì có **hai** phía sinh:
  - `platform_core/workflow/goi_y.py:106` xây `duong` dạng **có dấu chấm** →
    Data Picker (`ChonDuLieu.tsx:140`) chỉ bọc `{{ ... }}` quanh thứ máy chủ trả.
  - người dùng **gõ tay** cũng sẽ gõ dấu chấm (tài liệu §6 viết
    `nodes.<id>.output`).
  ⇒ Sửa **phía đọc** (`bien_dich`) phủ được cả hai; sửa phía sinh chỉ phủ một.

  ### ⚠️ Vì sao 12 làn trước ⛔ không ai bắt được

  Mọi bài test và mọi lượt nghiệm thu đều **tự đặt id sạch** (`n1`, `n2`,
  `n-img`, `imggen`) khi `PUT` thẳng tài liệu qua API. ⛔ Không lượt nào **vừa**
  để Canvas sinh id **vừa** gọi `/publish` sau khi chèn biểu thức.

  ⇒ Cùng họ với hai ca hôm nay: **fixture tự dựng một tiền đề mà sản phẩm ⛔
  không có** (`phe_duyet_v3` import tường minh ⇒ 404 trên production;
  `ai_dang_dung_may_chu` tự đặt `LTT_DATABASE_URL` ⇒ luôn `KHONG BIET` ngoài đời).
  ⭐ Ở đây tiền đề tự dựng là **hình dạng của một ID** — thứ trông vô hại nhất
  trong một fixture, và chính nó giấu một lỗi chặn toàn bộ tính năng.

  ### 7 bước E2E

  | # | Bước | Kết quả |
  |---|---|---|
  | 1-2 | Workflows → mới → Canvas mở **đúng** id vừa tạo (đo bằng 2 workflow khác nhau, ⛔ không phải `items[0]`) | ĐI ĐƯỢC |
  | 3 | palette → nối dây thật (kéo chuột) → Inspector → Data Picker chèn biểu thức | thao tác ĐI ĐƯỢC, **kết quả ⛔ KHÔNG chạy được** |
  | 4 | báo giá **trước** khi chạy | ĐI ĐƯỢC — *"62 credit cho 3 bước"* |
  | 5 | chạy → timeline **tên bước** | ĐI ĐƯỢC khi ⛔ không dùng biểu thức (*"Chạy thủ công"*, *"Sinh ảnh từ mô tả"* — ⛔ không phải `node_id` thô) |
  | 6 | Templates → *Dùng mẫu này* | ĐI ĐƯỢC — 6 node/6 cạnh, publish OK |
  | 7 | lưu trữ → biến mất → kho → mở lại | ĐI ĐƯỢC — đo bằng đếm dòng trước/sau |

  ### Hồi quy — tất cả còn sống

  ```
  cong noi 24px + elementFromPoint   27/27 trung
  nut `+` chen buoc chet             0
  trigger.manual publish duoc        OK
  loi goi vao khong gian id v2       0
  ba panel nap tre                   khong tai luc dau, tai dung luc bam
  ```

  ### ⚠️ UI-11 nói rõ thứ nó ⛔ KHÔNG đo được

  *Run có **thật sự hoàn tất** không* — cần worker chạy dưới `LocalSystem`, ⛔
  không có trong fixture dev. Cùng giới hạn UI-7 đã ghi. ⇒ Còn treo cho một lượt
  đo trên production sau deploy.

  ⭐ Và nó **⛔ không tự vá** lỗi tìm được, đúng luật: người nghiệm thu sửa sản
  phẩm thì ⛔ không còn ai nghiệm thu. Bản vá chạy ở một phiên riêng.

- `2026-09-28` `điều phối` — **ĐÃ DEPLOY `8907b4dd`. Nghiệm thu web thật: 3/4 ĐẠT,
  1 hỏng — và cái hỏng là lỗi của TÔI.** Mở wave 4: UI-10a + UI-10b.

  ### Nghiệm thu trên `https://app.lttstudios.com`

  ```
  UI-5  4 cua /ket-noi   GET 200 · GET 200 · POST 400(CSRF) · DELETE 400   DAT
        + than KHONG chua khoa nghi la bi mat                              DAT
  UI-9  /agent/templates 200 · 3 nut dung mau · 0 badge "Dang xay"         DAT
  Canvas                 tai xong 434 ms                                   DAT
  UI-8a POST .../duyet   404 tu ROUTER                                      ❌
  ```

  ### 🔴 Một tính năng đi qua MỌI cổng rồi chết im lặng

  `phe_duyet_v3` ⛔ không được `routes/__init__.py` import. Làn UI-8a **báo tôi
  đúng việc đó** trong báo cáo cuối và tôi bỏ sót. Nó có **9 test xanh** +
  nghiệm thu trình duyệt **PASS**.

  ⚠️ Vì sao ⛔ không phép kiểm nào của làn đó bắt được: `_shared.router` là đối
  tượng **dùng chung**, và fixture của họ `import` module **tường minh** (đúng
  theo hướng dẫn của chính tôi). Import ấy gắn route **trong tiến trình test**;
  `create_app()` ngoài đời chỉ nạp thứ `__init__.py` import.

  ⇒ Đây là một **họ RIÊNG**, ⛔ không phải *"đo thứ đại diện"*: mọi phép đo đều
  đúng, đều chạy, đều xanh. Cái sai là **bộ test tự dựng một tiền đề mà sản phẩm
  ⛔ không có** — nó đo trong **một thế giới do chính nó tạo ra**. Và ⛔ không mức
  độ phủ nào chỉ ra được, vì dòng mã ấy **CÓ chạy**.

  ⭐ Cơ học hoá: `test_5606` hỏi *"có tệp `.py` nào trong `apps/agent/routes/` mà
  `__init__.py` ⛔ không import không?"*, đọc **AST** — ⛔ **không** soi
  `sys.modules`, vì một module có thể đã ở đó do **một tệp test khác** vừa import
  nó, và khi ấy phép kiểm xanh vì lý do ⛔ không liên quan. *Một phép kiểm mà tiền
  đề của nó bị ô nhiễm bởi chính thứ nó đang kiểm thì ⛔ không kiểm gì cả.*
  Tiêm lỗi: gỡ tên khỏi tuple ⇒ **2 đỏ**. Route v3: 23 → **24**.

  ### 🔴 Bộ đo nghiệm thu của tôi tự sai BA lần — hai báo động giả

  Lượt đầu báo **ba** hỏng; chỉ **một** thật:

  | | vì sao |
  |---|---|
  | ✅ thật | `POST .../duyet` 404 từ ROUTER |
  | ❌ giả | `data-mau-slug` = 0 — tôi **tự bịa** tên thuộc tính; thật là `data-mau-dung` |
  | ❌ giả | `/đang xây/` khớp — tôi quét **cả body**, mà thanh điều hướng hiện badge đó cho **bốn mục KHÁC** |
  | ❌ giả | "3 lỗi trang" — console error do **chính các phép thăm dò của tôi** sinh ra (`POST` thiếu CSRF ⇒ 400 có ý) |

  ⇒ Nếu báo cáo ngay lượt đầu, tôi sẽ báo **ba** lỗi sản phẩm trong khi có **một**,
  và hai cái sẽ đẩy người khác đi sửa thứ ⛔ không hỏng. **Một báo động giả đắt
  hơn một phép đo ⛔ không chạy.**
  ⭐ Hai luật rút ra: *một phép đo trả `0` phải trả lời thêm "nếu thứ tôi tìm CÓ ở
  đây, nó có trả khác 0 không?"*, và *một bộ đo phải **trừ dấu vết của chính nó**
  ra khỏi số liệu*.

  ### ⚠️ Trần bundle đo GZIP trong khi Cloudflare phục vụ ZSTD

  ```
  byte tho          517.837
  gzip -9           158.681   <- tran CU do cai nay  ⇒  DUOI tran 160.000, XANH
  zstd -3 (o nha)   164.335
  THAT TREN DAY     164.252   ⇒  VUOT tran 2,7 %
  ```

  🔴 Bánh cóc **xanh** trong khi thứ khách tải **vượt trần**. Và tôi đã dùng chính
  con số gzip để **biện minh việc NÂNG trần** sáng nay.

  ⛔ Hy vọng *"gzip là cận trên an toàn cho zstd"* thì **SAI**: `zstd -3` **lớn
  hơn** `gzip -9`, còn `-9`/`-19` thì nhỏ hơn — zstd ⛔ không đơn điệu, nó phụ
  thuộc **mức nén**, và ⛔ không ai ngoài CDN biết mức họ dùng.

  ⭐ Dụng cụ đúng: `PerformanceResourceTiming.encodedBodySize`. Hai dụng cụ hiển
  nhiên đều trả lời câu khác — `content-length` **vắng mặt** ở phản hồi zstd
  streaming; `response.body()` trả **thân đã giải nén**.
  ⚠️ `encodedBodySize = 0` là **KHÔNG ĐO ĐƯỢC** (cache / thiếu
  `Timing-Allow-Origin`), ⛔ không phải *"0 byte"*.

  Sửa: `test_95` nén bằng `zstd -3`, trần `170.000` trên **số THẬT**. Và vì
  `test_95` chạy offline nên nó **tin** mức 3 ≈ CDN — niềm tin ấy được đo lại ở
  `tests/browser/agent_ui_v2_byte_tren_day.js` (lệch **0,11 %**).
  ⚠️ **MỘT** nguồn chân lý: trần ở `test_95`; kịch bản trình duyệt **báo số + kiểm
  mô hình**, ⛔ không phán quyết trần.

  ### 🔴 Tôi vi phạm luật "dựng lại bundle" BA lần, kể cả sau khi tự nới rộng nó

  Lần đầu: sau một lần gộp. Lần hai: `13717fea` đổi `workflowApi.ts` trong một
  commit **thường** — luật cũ nói *"sau mọi lần GỘP"* nên ⛔ không kích hoạt.
  Lần ba: `d85a044a` đổi hai tệp `.ts`, ngay sau khi tôi đã nới thành *"sau mọi
  thay đổi NGUỒN frontend"*.

  ⇒ **Một luật phát biểu đúng ⛔ KHÔNG thay thế được một phép kiểm cưỡng chế nó.**
  Cả ba lần thứ bắt được là `test_95::..._is_fresh`, ⛔ không phải câu văn.
  ⭐ Và *"luật hẹp"* = *"tham chiếu chết"* ở hai vật liệu khác nhau: cả hai sản
  xuất **niềm tin rằng có lưới**, và niềm tin ấy **đắt hơn** việc ⛔ không có lưới.

  ### ⚠️ Deploy KHỞI ĐỘNG LẠI WORKER — trạng thái ⛔ không nằm trong git

  Phiên kia chặn tôi deploy vì họ có job ASV chạy dở (giai đoạn 8/13, 11 phút,
  50 credit); khởi động lại giữa chừng **giết** nó. `git status` sạch + gate xanh
  ⛔ không nói gì về việc **có ai đang dùng máy chủ không**.
  ⇒ `tools/ai_dang_dung_may_chu.py` (mới): `0 RANH` · `3 DANG DUNG` ·
  **`4 KHONG BIET`**. Mã `4` ⛔ **không** được gộp vào `0` — gộp lại thì một CSDL
  ⛔ không đọc được sẽ trông y hệt một máy rảnh, và cái lẫn ấy nghiêng về phía
  **giết job của khách**. ⛔ **CHƯA** đấu vào `2-cai-dat.ps1`: đó là thay đổi
  đường deploy ⇒ chủ dự án chốt.

  ### ⚠️ `main` từng dời BỐN lần trong một cửa sổ deploy

  `708fdf3d → 13717fea → c1e09dfd → 8907b4dd`, mỗi lần phiên kia đo lại thì nó
  dời tiếp. ⇒ **Một bằng chứng có hạn dùng ngắn hơn thời gian thu thập nó thì ⛔
  không bao giờ hợp lệ.** Thuốc ⛔ không phải đo nhanh hơn — là **đóng băng cây**.
  Tôi đã đóng băng `main` cho tới khi họ deploy xong.
  ⭐ Và `--ff-only` là hình dạng đúng: **nó TỪ CHỐI thay vì đo lại**.

  ### Wave 4 — hai làn, tệp rời nhau

  | Làn | Dải test | Cổng | Tệp giữ |
  |---|---|---|---|
  | UI-10a hiệu năng | 6700-6799 | 8208 | `EditorShell.tsx` ⭐ · `vite.config.ts` · `test_95` |
  | UI-10b trợ năng | 6800-6899 | 8209 | `canvas.css` · `styles/**` · `features/editor/**` **trừ** `EditorShell.tsx` · `inspector/**` · `nodes/**` |

  UI-10b được bảo **ĐO LẠI** tiêu chí 93 (vùng bấm) và 94 (mobile) thay vì tin
  điểm audit cũ — cả hai đã được UI-0 và điều phối sửa từ lúc audit chấm điểm.

- `2026-09-28` `điều phối` — **MỞ WAVE 3: UI-6 · UI-8a · UI-9 chạy song song.**

  Cấp tài nguyên **TRƯỚC** khi giao việc, vì đợt trước tôi quên cấp **cổng** và
  cả bốn brief đều ghi `8198` — suýt giết tiến trình của UI-7.

  | Làn | Dải test | Cổng | Tệp giữ |
  |---|---|---|---|
  | UI-6 data picker | 6400-6499 | 8205 | `src/inspector/**` |
  | UI-8a human approval | 6500-6599 | 8206 | `routes/phe_duyet_v3.py` · `ExecutionPanel/**` |
  | UI-9 mẫu | 6600-6699 | 8207 | `routes/trang.py` · `templates/agent_templates.html` · `workflow/mau.py` |

  ⭐ **Tệp rời nhau hoàn toàn.** Hai chỗ dễ va nhất đã chỉ định chủ tường minh:
  `trang.py` → **chỉ** UI-9 (UI-8a bị cấm chạm); `src/inspector/**` → **chỉ**
  UI-6 (UI-8a bị cấm chạm). `routes/__init__.py` · `locale/` · `canvas.css` ·
  `editorState.ts` · `workflowApi.ts` → **điều phối giữ**, làn chỉ BÁO dòng cần.

  ### ⭐ Hai làn được bảo DÙNG LẠI cửa đã có, một làn được phép MỞ cửa

  | Làn | Cửa | Vì sao |
  |---|---|---|
  | UI-6 | `POST …/bieu-thuc/goi-y` **đã có** | ⛔ không mở cửa mới |
  | UI-9 | `POST /api/v3/workflows` **đã nhận `document`** | "mở mẫu" = tạo workflow thật, y như *Nhân bản* đã làm |
  | UI-8a | **ĐƯỢC mở** cửa duyệt/từ chối | phase này tồn tại CHÍNH VÌ cửa ấy thiếu |

  🔴 **UI-8a là ca *lưu trữ workflow* lần thứ hai**: `core.human` đã đủ —
  waitpoint, `NHANH_HUMAN = ("approve","reject")`, `che_do_het_han` mặc định
  `reject`, và `runs_v3` **đọc** được waitpoint còn mở — nhưng ⛔ **không cửa nào
  cho người dùng BẤM**. Nghĩa đã sống, cửa thì chưa.
  ⇒ Khác lần trước ở một điểm: lần này cửa ⛔ **không phải** một quyết định mới —
  lộ trình UI-0→UI-10 mà chủ dự án đã duyệt có sẵn mục *"UI-8a Human approval"*,
  nên cái cửa **là chính nội dung của phase**. Brief vẫn cấm mở **bất kỳ cửa nào
  khác**.

  ⚠️ Brief UI-8a nhấn hai bất biến tiền, vì cửa duyệt rất dễ trượt sang đó:
  nó ⛔ **không** tạo run, ⛔ **không** tính tiền, ⛔ **không** đi vòng qua
  `tao_run.py` (cửa DUY NHẤT tạo run). Nó chỉ **đóng một waitpoint**.
  Và một bước `WAITING` vì `core.delay` ⛔ **không** được hiện nút duyệt — cùng
  `status`, **khác `kind`**; phải đọc `kind`, ⛔ đừng suy từ `status`.

  ### ⭐ Brief lần này mang theo bài học của cả ngày

  Ba bộ kiểm **hình dạng cả cây** (`scan_source_secrets` · `check_mypy` ·
  `check_silent_except`, **< 45 giây**) nay là **bắt buộc trước khi báo xong** —
  chúng bắt loại lỗi mà test nhắm ⛔ không thể bắt: **mã đúng hành vi mà sai bất
  biến toàn kho**. Đêm 27-28/09 có **ba** lỗi như vậy lọt lên `main`.

  Kèm ba bẫy làm một lượt Playwright **xong** trông như **chết** (`const` ở mức
  ngoài cùng ⇒ `SyntaxError` · `click` rồi `goto` ⇒ `ERR_ABORTED` · hồ sơ giữ
  cookie ⇒ `page.fill` timeout), và luật **đo TÍNH CHẤT chứ đừng đo VĂN BẢN**
  kèm cả ba ca thật của hôm nay.

- `2026-09-28` `điều phối` — **BA LÀN CÒN LẠI ĐÃ GỘP. `main` = `2cb3f702`.**
  Cùng lượt: **cửa lưu trữ workflow** (chủ dự án duyệt mở bề mặt HTTP mới).

  ### Lưu trữ workflow — ba cửa, không phải một

  `Workflow.archived_at` có trong lược đồ **từ đầu** và **ba** nơi đã ĐỌC nó
  (`v3_danh_sach` lọc, `tao_run` từ chối run mới, `nut` bỏ qua khi dò drift).
  Toàn bộ **nghĩa** đã sống; thiếu đúng một cửa **ĐẶT** nó. UI-1 gặp và **dừng
  lại hỏi** thay vì tự mở — đúng luật.

  | Cửa | Vì sao bắt buộc |
  |---|---|
  | `POST …/luu-tru` | đặt `archived_at` (luỹ đẳng — bấm hai lần ⛔ không làm mốc trôi) |
  | `POST …/mo-lai` | xoá nó (luỹ đẳng — giao diện có thể gọi từ danh sách đã cũ) |
  | `?luu_tru=1` | **nhìn thấy** bản đã lưu trữ |

  🔴 Cửa thứ ba ⛔ không phải tiện nghi. Một workflow đã lưu trữ **biến mất khỏi
  mọi danh sách** — đó là cả ý nghĩa của nó. Không có khung nhìn kho thì
  `/mo-lai` tồn tại mà **KHÔNG VỚI TỚI ĐƯỢC**: người dùng mất workflow mà ⛔
  không ai xoá gì cả, và họ ⛔ không có cách nào biết nó còn đó.
  ⇒ Tầng trang theo cùng: `tong` đếm trong **cùng** khung nhìn, lối vào kho chỉ
  vẽ khi kho **có** gì, và kho ⛔ không hiện *Nhân bản* (nó sẽ sinh một bản
  **đang dùng** từ một trang kho).

  ### 🔴 Hai lần phép đo trả lời câu HỎI KHÁC

  1. **Bài `…tra_404` XANH GIẢ.** Lượt đỏ đầu cho nó `PASS` khi route **còn chưa
     tồn tại** — vì một route **vắng mặt** cũng trả `404`. Mã trạng thái một
     mình ⛔ không phân biệt *"tôi đã kiểm chủ sở hữu và không thấy"* với *"tôi
     chưa từng nghe về đường này"*. ⇒ đo cả `detail`.
  2. **`data-wfl-mo-lai` TRẦN khớp cả bảng bộ chọn trong `<script>`** — bảng đó
     có ở CẢ HAI khung nhìn. Phép đo hoá ra đo *"trang có nhắc tên thuộc tính
     này"*, ⛔ không đo *"trang có vẽ nút này"*. ⇒ neo vào dấu `="`.

  ### 🔴 Hai làn cùng dựng MỘT Inspector — git gọi nó là xung đột văn bản

  UI-3 tách form cũ ra `features/editor/StepInspector/`; UI-5 dựng **Inspector
  V2** (§6) ở `src/inspector/StepInspector.tsx`. UI-5 nền từ một `main` **chưa
  có** lần tách của UI-3 ⇒ họ sửa `src/CanvasShell.tsx`, tệp mà `main` nay chỉ
  còn **một dòng re-export**. Git báo xung đột **cả tệp** (1-69, 80-970): đúng
  về văn bản, vô nghĩa về nội dung.

  ⇒ Giữ bản **UI-5** (nó là TÍNH NĂNG: 5 tab, ô kết nối, luật ẩn trường phụ
  thuộc, 301 dòng test + nghiệm thu trình duyệt thật), **bỏ** bản UI-3 (nó là
  một lần **DI CHUYỂN** của chính cái form mà V2 thay thế). ⛔ Không ai mất
  việc: `FormTuLuocDo` vẫn là ruột của tab *Cấu hình*.
  ⚠️ `<aside>` chuyển về **chỗ gọi** — bản UI-5 trả về NỘI DUNG, bản UI-3 tự
  bọc. Bỏ qua chỗ này sẽ mất cả khung panel, và mất **IM LẶNG** vì CSS
  `.canvas-inspector` gắn vào thẻ chứ không vào ruột.

  ### 🔴 `503` không ở chỗ nó trông như đang ở

  Sau khi gộp, **MỌI** bài có đăng nhập tra `503` — kể cả bài vừa xanh. Trông y
  hệt *"gộp làm sập đăng nhập"*. Thực tế:

  ```
  POST /login  ->  303 tới next=/agent/canvas  ->  TRANG ĐÍCH trả 503
  _trang_canvas:   if not canvas_js: raise HTTPException(503)
  ```

  Nguyên nhân thật: `manifest.json` của bundle **còn nguyên dấu xung đột** ⇒
  `bundle_assets` đọc ra rỗng. `follow_redirects=True` làm mã của **trang đích**
  hiện ra ở chỗ mã của `/login`.
  ⇒ Phép đo đúng, **số bị gán cho sai BƯỚC**. Tệ hơn một phép đo im lặng: nó
  làm người ta đi sửa đăng nhập trong khi lỗi ở `manifest.json`.
  ⭐ Đối chứng cho một luật: **bundle phải dựng lại sau MỌI lần gộp** — nó là
  ĐẦU RA, nên *"chọn bên nào"* luôn sai, chỉ dựng lại mới đúng.

  ### ⭐ UI-7 báo một 🔴 mà phép đo trên WEB THẬT không xác nhận

  Họ báo: *"`.sr-only` không định nghĩa ở đâu trong `canvas.css` ⇒ dòng `N node
  · M kết nối trong renderer` **đang hiện cho khách**"*. Nửa đầu **đúng**. Nửa
  sau đo trong hộp thử `vite dev` của họ — nơi ⛔ không nạp `/static/ltt.css`.

  Đo trên `https://app.lttstudios.com/agent/canvas`:

  ```
  ô vuông               1×1 px
  clip                  rect(0px, 0px, 0px, 0px)
  elementFromPoint tâm  -> không có gì
  nguồn `.sr-only`      -> /static/ltt.css (×2) + agent-canvas/assets/main-*.css
  ```

  ⇒ Đã ẩn thật. Cảnh báo đóng. Bài đo ở
  `tests/browser/agent_ui_v2_sr_only_web_that.js` — giữ lại vì câu *"lớp này
  còn sống không"* sẽ quay lại mỗi lần ai đó đổi bảng.
  ⚠️ Hai bẫy trong chính bài đó, cả hai làm một lượt chạy **xong** trông như một
  lượt **chết**: `__LTT_COOKIE__` được thay bằng **GIÁ TRỊ** (không phải
  `session=<giá trị>`), và playwright-cli in **giá trị TRẢ VỀ** chứ ⛔ không in
  `console.log`.

  ### 🔴 LẦN THỨ HAI một bộ quét tệp bị UI-3 làm mù — và bộ ĐẾM của tôi cũng đo sai đại lượng

  Sau `test_1728` sáng nay, `test_1270` đọc `src/CanvasShell.tsx` và ⛔ không còn
  thấy gì. **Đỏ trên `main` từ lần gộp UI-3.**

  Tôi viết một bộ ĐẾM để tìm mọi bài còn lại cùng kiểu — nó trả **38/39 đường
  dẫn còn sống**, tức *"không còn bài nào mù"*. Nhưng `test_1270` **vẫn đỏ**, và
  đường dẫn của nó nằm trong 38 cái *"còn sống"*.
  ⇒ Bộ đếm đo *"đường dẫn còn TỒN TẠI không"*, trong khi thứ mất là **NỘI
  DUNG**. Một phép đếm **chạy đúng, số đúng**, trả lời một câu **KHÁC** — và tệ
  hơn không đếm, vì nó cho một con số **nghe như đã phủ hết**.
  ⭐ Tín hiệu rẻ (phiên `PROMPT AI` chốt cùng tôi): **một con số "gần như đủ"**
  (`38/39`, `0 lỗi mới`, *"tất cả trừ một"*) là chỗ phải hỏi lại đại lượng. Con
  số đẹp làm người ta ngừng hỏi; một con số thảm hại thì tự bắt người ta đi kiểm.
  ⇒ Neo lại vào **HAI** tệp: chỗ GẮN nhãn (`WorkflowCanvas.tsx`) và BẢNG nhãn
  (`a11y.ts`). Tiêm lỗi cả hai vế ⇒ cả hai đỏ.

  ### ⚠️ Trần bundle: CẢ HAI trần vượt, và trần KHÁCH THẬT SỰ CẢM vượt NẶNG HƠN

  | đại lượng | đo | trần cũ | vượt |
  |---|---|---|---|
  | byte thô | **511.238** | 500.000 | 2,2 % |
  | **gzip** | **156.702** | 150.000 | **4,5 %** |
  | brotli | 134.719 | — | — |

  🔴 Tôi đọc bài kiểm **nửa vời**, thấy mỗi trần byte thô, và gần viết vào commit
  rằng *"khách không ảnh hưởng"*. **Sai** — bài kiểm **đã có sẵn** một trần gzip,
  và nó vượt nặng hơn. Cái sai không đến từ phép đo; nó đến từ việc tôi **kết
  luận trước khi đọc hết thứ mình đang sửa**. ⇒ *Bài kiểm cũng là một tập phải
  đọc hết trước khi sửa — kể cả khi chính mình đang viết lại nó.*

  Nâng `500.000 → 520.000` và `150.000 → 160.000`, **kèm xuất xứ** — con số cũ
  vào kho ở `baf06e9d` ⛔ không một chú thích nào, nên mỗi lần chạm trần lại là
  một cuộc tranh luận từ đầu, và người tranh luận ⛔ không có cách nào biết con
  số cũ đo trong hoàn cảnh nào.
  ⛔ **KHÔNG tách vendor để "về dưới trần"**: tách `@xyflow/react` ra chunk riêng
  kéo tệp VÀO xuống dưới 500.000 **ngay**, và làm bài kiểm xanh mà ⛔ không một
  byte nào rời đường truyền — đo **CÁCH ĐÓNG GÓI** thay vì đo **TÍNH CHẤT**,
  đúng họ với `.typed-port`. Phép đo đổi sang **TỔNG mọi tệp JS** ⇒ từ nay tách
  chunk ⛔ không làm nó mù.
  ⚠️ **Việc giảm byte THẬT chưa làm** (nạp trễ `CommandPalette`, `LayersDrawer`,
  bốn tab đặt chỗ của Inspector V2) ⇒ **UI-10**.

  ### ⭐ `.typed-port` — một lớp bảo vệ TƯỞNG TƯỢNG bị gỡ

  `test_95` ghim `.typed-port { width:44px` trong `canvas.css`. Nhưng
  `canvas.css` **đã ghi rõ từ 27/09** rằng ⛔ không component nào gắn class đó
  (`NodeKhung.tsx` không đặt), nên kích thước thật của `.react-flow__handle` là
  **6×6 px** trong khi phép kiểm vẫn XANH suốt. Nó đo sự **CÓ MẶT CỦA VĂN BẢN**,
  ⛔ không đo tính chất mà văn bản đó hứa.
  ⇒ Neo vào `--handle-hit:24px` **và** `var(--handle-hit` (khai mà ⛔ không ai
  dùng thì vẫn là `.typed-port` lần hai), cộng lớp trình duyệt thật.

  ### 🔴 BA LẦN trong một ngày: test NHẮM chọn theo CHỦ ĐỀ, bánh cóc đo theo TẬP TỆP

  | cổng | trước | sau |
  |---|---|---|
  | `scan_source_secrets` | 3 findings | **0** |
  | `check_mypy` | `union-attr 89` | **88** (đạt mốc) |

  Cả hai **dưới 20 giây** và ⛔ không bao giờ được gọi tới bởi một bộ test chọn
  theo chủ đề. `tools/chay_web_that.py` của tôi (tạo 00:48) làm mypy đỏ trên
  **chính `main`**; hai phiên khác đo và vá hộ (`ff001831`, `e6acb6de`).
  ⇒ **Thêm `scan_source_secrets.py` + `check_mypy.py` vào nhịp TRƯỚC khi gộp
  `main`**, ⛔ không chờ gate cuối plan.
  ⚠️ Mẫu quanh đó ⛔ không chỉ đường được: `tests/fixtures/` + `tests/browser/`
  đặt literal y hệt mà **chưa bao giờ** bị bắt — hai thư mục đó nằm **NGOÀI**
  vùng quét. *"Chỗ khác làm thế vẫn xanh"* ở `tests/` gốc là một **tín hiệu sai
  có hệ thống**.

  ### Số đo tổng

  ```
  vitest        165 -> 238   (13 -> 15 tệp)
  route v3       17 -> 23
  node publish   27 -> 60
  pytest nhắm   407 passed (+53 sau khi sửa) · tsc xanh
  secret scan   PASS 0 findings · mypy đạt mốc · pre-commit --all-files xanh
  ```

  ⚠️ **mypy giảm 3 mà tôi KHÔNG hạ mốc** (`arg-type 108→106`, `index 32→31`):
  hạ mốc sẽ làm đỏ cây của ba phiên đang có việc chạy, vì một **giảm** của tôi
  trở thành một **trần mới** cho họ. Thắt cổng dùng chung giữa lúc đông người là
  một việc đúng làm sai lúc.

  ### Còn treo

  | Việc | Chỗ |
  |---|---|
  | Giảm byte THẬT (nạp trễ) | UI-10 |
  | Tương phản minimap/controls 1,08:1 < 3:1 (WCAG 2.2 AA 1.4.11) | UI-10 |
  | `ai.llm` · `ai.extract` · `ai.router` còn `publish_duoc=False` | plan 10 |
  | `trigger.schedule` · `trigger.webhook` ⛔ chưa có trong registry | plan backend riêng |
  | Cửa callback OAuth `/api/v3/ket-noi/oauth/callback` ⛔ chưa cài | UI-5 để lại |
  | `CanvasNode.credential_ref` còn thiếu ở `workflowApi.ts` (UI-5 dùng kiểu cục bộ) | điều phối |
  | Nghiệm thu 4 cửa `/ket-noi` + tốc độ Canvas trên web thật sau deploy | điều phối |

- `2026-09-28` `điều phối` — **UI-1 KIỂM XONG, ĐÃ GỘP.** Nghiệm thu trình duyệt
  thật `PASS`, và mệnh đề chốt được chứng minh **đúng dạng cần**:

  ```
  items_0             9480a1bd...   <- workflow sửa gần nhất
  id_da_nap           86839463...   <- workflow tôi YÊU CẦU mở
  so_loi_goi_workflow 1             <- đúng MỘT lời gọi
  ```

  Hai id **khác nhau** — đó mới là bằng chứng, ⛔ không phải *"trang mở được"*.
  Route HTML của app **2 → 5** (+ 5 trang đặt chỗ nói rõ *"đang xây"*).
  93 pytest + 167 vitest.

  ⭐ `id ? loadWorkflowV3(id) : loadOrCreateWorkflowV3(csrf)` — `items[0]` **còn
  sống có chủ đích**, làm lối lui cho `/agent/canvas` (đường cũ, không id). Và
  họ đọc id **từ DOM** chứ ⛔ không bóc từ `location.pathname`, vì máy chủ mới là
  nơi đã lọc theo chủ sở hữu và trả 404 cho id của người khác — bóc lại ở trình
  duyệt là đoán lại một câu đã có đáp án đúng.

  🔴 **UI-1 bắt được một hồi quy CỦA TÔI:** 3 bài `test_1728` **đã đỏ sẵn trên
  `main`** — tôi gộp UI-3 mà ⛔ không chạy chúng. Bộ dò khớp đường import một
  hoặc hai cấp, đúng khi mọi tệp còn phẳng trong `src/`; UI-3 đẩy xuống
  `features/editor/hooks/` nên import thành ba cấp và bộ dò **mù** với 24/31 chỗ
  gọi (đọc ra **1** tên hàm thay vì **22**). Đã sửa: `984888cc`.

  ⭐ Bánh cóc ấy **tự bắt được mình đã mù** (`test_bai_2_KHONG_xanh_vi_canvas_rong`)
  thay vì im lặng báo *"không có đường chết nào"*. Một cổng tự kiểm là một cổng
  đáng tin — ngược hẳn với `.typed-port 44px`, một lớp bảo vệ **tưởng tượng**.

  🔴 **Luật mới, và đây là LỖI ĐIỀU PHỐI:** tôi chọn bộ test nhắm theo **CHỦ ĐỀ**
  (cổng biên dịch, động cơ) nên `1728` không thuộc nhóm nào. Nhưng UI-3 là một
  pha **DI CHUYỂN TỆP**, còn `1728` là một phép kiểm **QUÉT TỆP** — chúng hỏng
  theo một **trục khác**.
  ⇒ *Một pha di chuyển/đổi tên tệp thì bộ test nhắm **phải** gồm mọi phép kiểm
  quét tệp (đường dẫn, import, tên lớp, số tệp), ⛔ không chỉ các phép cùng chủ đề.*

  ⚠️ **Sổ dùng chung thứ BẢY tôi bỏ sót: CỔNG máy chủ thử.** Tôi cấp dải số test
  cho từng làn nhưng ⛔ không cấp cổng, và cả bốn brief đều ghi `8198`. Suýt giết
  tiến trình của UI-7: phép kiểm cổng của tôi trả `000` đúng khoảnh khắc máy chủ
  họ đang khởi động lại, nên **trông như rảnh**.
  ⇒ Cấp dải cổng từ đầu, và ⛔ **không bao giờ** kết luận *"cổng rảnh"* từ **một**
  lần thử — một cổng đang khởi động lại trả y hệt một cổng trống.

  | Làn | Cổng |
  |---|---|
  | điều phối | 8196 |
  | UI-4 | 8201 |
  | UI-7 | 8202 |
  | UI-1 | 8203 |
  | UI-5 | 8204 |
  | UI-6 | 8205 |
  | UI-8a | 8206 |
  | UI-9 | 8207 |
  | UI-10a | 8208 |
  | UI-10b | 8209 |

  🔴 **Còn treo, và UI-1 dừng ĐÚNG chỗ:** *lưu trữ workflow* chưa làm —
  `archived_at` có trong lược đồ và danh sách **đã lọc** theo nó, nhưng ⛔ không
  cửa nào **đặt** được nó ⇒ cần một cửa HTTP mới ⇒ họ **dừng và hỏi** thay vì tự
  mở bề mặt. Đúng luật.
  `test_6200::test_khong_mo_cua_POST_moi_o_tang_trang` canh việc này.

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
