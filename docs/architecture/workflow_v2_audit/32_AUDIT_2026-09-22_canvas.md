# Audit frontend/agent-canvas (chỉ đọc, main, 22/09/2026)

Đường dẫn tuyệt đối: `D:\LTTSTUDIOSAPP\frontend\agent-canvas`

## 1. Cấu trúc

`src/` (10 tệp, 2455 dòng):
- `src/editorState.ts:1-360` — reducer + kiểu `PaletteTool`/`EditorAction`, undo/redo, graph ops
- `src/nodePresentation.ts:1-99` — modality/label suy từ tên tool (chế độ "legacy")
- `src/presentationAdapter.ts:1-119` — lớp trình bày "creative-v1" (modality core/secondary/internal)
- `src/workflowApi.ts:1-453` — API client + v2↔v3 converter
- `src/CanvasEdgeView.tsx:1-16` — edge tuỳ biến (nút "+" chèn bước)
- `src/CanvasShell.tsx:1-910` — component gốc, toàn bộ state + wiring ReactFlow
- `src/Inspector.tsx:1-57` — panel field phụ (không phải content field)
- `src/RunInspector.tsx:1-22` — hiển thị run/checkpoint/lịch sử
- `src/ToolNode.tsx:1-202` — 4 component node: `ToolNode`, `CreativeToolNode`, `FrameNode`, `AnnotationNode`
- `src/main.tsx:1-9` — entry, mount `#agent-canvas-root`

`tests/` (7 tệp, 1056 dòng, 71 `it/test`): `CanvasShell.test.tsx` (23), `workflowApi.test.ts` (18),
`editorState.test.ts` (19), `presentationAdapter.test.ts` (5), `Inspector.test.tsx` (3),
`nodePresentation.test.ts` (3). Chỉ **vitest 4.1.10** + `@testing-library/react` 16.3.2 + jsdom 28 —
**không có Playwright/E2E** trong package này.

Thư viện chính (`package.json`):
- `@xyflow/react` **12.11.2** (React Flow, rebrand)
- `react`/`react-dom` **19.2.8**
- **Không** có state lib ngoài (không Zustand/Redux/Jotai) — state là `useReducer` thuần
  (`editorReducer` trong `editorState.ts`) + nhiều `useState` cục bộ trong `CanvasShell.tsx`
- Build: Vite 8.2.0, output vào `../../server/static/agent-canvas` (`vite.config.ts:9`)

## 2. Node rendering

`nodeTypes` đăng ký ở `CanvasShell.tsx:22`: `{ tool: ToolNode, creativeTool: CreativeToolNode, frame: FrameNode, annotation: AnnotationNode }`.
Chỉ **hai loại node thật sự có dữ liệu tool**: `ToolNode` (chế độ "legacy") và `CreativeToolNode`
(chế độ "creative", mặc định — chọn theo `data-presentation` trên `#agent-canvas-root`,
`CanvasShell.tsx:120-121`). `FrameNode`/`AnnotationNode` chỉ là trang trí (không có `data.tool`).

**Không có NodeRenderer tổng quát theo loại (Trigger/Control/...)** — cả hai component node đều
giả định **mọi node là một "tool"** với `data.tool` (chuỗi tên) + `data.params`; UI suy ra modality
(`text/image/video/audio/batch/transform/input/tool`) từ **tên chuỗi tool** qua
`nodeModality()` (`nodePresentation.ts:19-33`) hoặc `creativeModality()` (`presentationAdapter.ts:47-52`),
dùng `tool.name.startsWith('image.')` v.v.

**Canvas CÓ hardcode slug cụ thể** ở nhiều chỗ (không chỉ suy loại chung chung):
- `nodePresentation.ts:21,24-31,36-39,45-47,80` — `asset.images`, `asset.image/video/audio`, `video.social_import`, prefix `text./image./video./audio.`
- `presentationAdapter.ts:24-26,29-35,37-45` — `coreTools` (`text.generate`,`image.generate`,`video.generate`,`audio.generate`), `explicitModalities` map ~20 tool name cụ thể, `actionLabels` cho từng tool
- `CanvasShell.tsx:335,351,352` — `asset.images`, `image.batch_generate`
- `ToolNode.tsx:36,106` — `tool?.name==='video.social_import'`

`CanvasEdgeView.tsx` — edge view riêng (`creative` edgeType), chỉ vẽ path + nút "chèn bước" (không
hiển thị kiểu cổng trên cạnh).

`Inspector.tsx` — panel field phụ không thuộc "content field" (`prompt/topic/text/url/source_url`
bị lọc ra ở `Inspector.tsx:35` vì đã hiển thị trực tiếp trong node).
`RunInspector.tsx` — hiển thị trạng thái/step/artifact của run + lịch sử run.

`presentationAdapter.ts` chính là "presentation adapter" theo nghĩa yêu cầu — nhưng nó adapt theo
**modality nội dung** (text/image/video/audio), không theo **loại node** (Trigger/Control/...).

## 3. Palette

Nguồn: `GET /agent/api/palette` (`workflowApi.ts:250`, hàm `loadPalette`). Server trả
`{ tools: PaletteTool[], models?: [...], routing?: { mode } }` — client chỉ đếm `models.length`
và đọc `routing.mode` để hiển thị "AUTO ROUTING" (`CanvasShell.tsx:185,715`).

`PaletteTool` (`editorState.ts:270-286`) có sẵn field `category?: 'content'|'input'|'transform'|
'specialized'|'advanced'`, `primary?: boolean`, `customer_visible?: boolean` — server đã phân loại,
client chỉ hiển thị lại (`categoryLabels` map ở `CanvasShell.tsx:562`).

Palette có **tìm kiếm** (`paletteQuery`, input `.palette-search`, `CanvasShell.tsx:86,689`) lọc theo
`label/name/app_name/description` (`CanvasShell.tsx:564`), và **phân nhóm** theo `category` (hoặc
gộp về "Công cụ chính" khi `catalogMode==='simple'` không có query, `CanvasShell.tsx:566`).
Có toggle "advanced/simple" lưu vào `preferences.catalog_mode` (`GET/PUT /agent/api/preferences`,
`workflowApi.ts:254-258`).

Chế độ "creative" còn lọc qua `customerPaletteTools()` (`presentationAdapter.ts:73-77`): ẩn tool
`customer_visible===false` và tier `internal` (asset.* — trừ khi advanced).

## 4. Form cấu hình node

**Viết tay theo schema, không phải JSON-Schema chuẩn.** `params_schema` của mỗi tool là
`Record<string, {type,required?,default?,values?,options?,min?,max?,depends_on?}>` — một schema rút
gọn tự định nghĩa (`editorState.ts:280-282`), không dùng `ajv`/JSON Schema chuẩn/`react-jsonschema-form`.
`Inspector.tsx:40-53` lặp `primaryFields()` rồi tự map `rule.values→<select>`, `rule.type==='bool'→checkbox`,
`int/number→<input type=number>`, còn lại `<input type=text>` — 3 loại control cứng, không đọc
`format`/`pattern`/nested object/array từ schema. `primaryFields()` (`nodePresentation.ts:68-77`)
chọn tối đa 6 field theo danh sách ưu tiên cứng (`priorities` mảng tên field, dòng 64-66) + field
`required`/có `values`. Field nội dung chính (prompt/topic/text/url) hiển thị **trực tiếp trong node**
(`ToolNode.tsx:55-58,133-137,157-164`), không qua Inspector.

`schema_variants` (editorState.ts:283) cho phép server đổi `params_schema` theo giá trị 1 field khác
(`nodePresentation.ts:70-71` áp dụng) — cơ chế biến thể sơ khai, cũng viết tay ở client.

## 5. Cạnh/cổng có kiểu

**Luật nối dây nằm hoàn toàn ở client**, không hỏi server lúc kéo-thả:
- `connectionAllowed()` (`editorState.ts:291-302`) — so khớp `source.returns[handle]` (kiểu output)
  với `target.params_schema[handle].type` qua `inputPort()` (ánh xạ `string/text→text`,
  `int/number/bool→json`, còn lại giữ nguyên); chấp nhận khớp mảng (`type[]` nhận phần tử `type`).
  Có luật đặc biệt: không nối được vào node `asset.*`, không nối `targetHandle==='refs'` hoặc bắt đầu `_`.
- `connectionCreatesCycle()` (`editorState.ts:304-311`) — chặn tạo chu trình, chạy ở client trước khi gọi `addEdge`.
- Cổng: `params_schema` (input, type target) và `returns` (output, type nguồn) — cả hai do server
  cung cấp qua palette, nhưng **việc cho phép nối là tính toán client-side thuần**, server không được
  hỏi lúc thao tác; server chỉ validate lại khi `POST /workflows/{id}/validate`
  (`workflowApi.ts:360-364`) hoặc lúc save.
- Khi đổi tool của node đã có input/output nối (`replaceNodeTool`, `editorState.ts:196-268`), client
  tự tìm lại cổng tương thích gần nhất (exact match theo `inputPort`, rồi theo `targetHandle`, rồi
  `sourceHandle`, rồi bất kỳ) — logic phỏng đoán phức tạp, toàn bộ ở client.

## 6. Định dạng document (v2/v3)

**Hai định dạng song song** trong `workflowApi.ts`:
- **v2** (`CanvasDocument`, dùng làm shape soạn thảo trong toàn bộ UI): `{version:2, goal,
  budget_max_credit, active_page_id, pages:[{id,name,nodes,edges,viewport,frames,notes,comments,view}]}`.
  `CanvasNode={id,type:'tool',position,label?,data}`. `CanvasEdge={id,source,target,sourceHandle?,
  targetHandle?,data?}` — dùng `sourceHandle/targetHandle` (hợp đồng React Flow, xem comment
  `workflowApi.ts:164-175`).
- **v3** (`CanvasDocumentV3`, shape lưu trữ ở server, "LTT WORKFLOW V2, Dot 5.2"): cạnh có
  `source_node/target_node/source_port/target_port/kind:'DATA'|'CONTROL'` (`workflowApi.ts:90-98`).
  Converter `edgeToV3`/`edgeFromV3`/`toV3`/`fromV3` (dòng 109-158) chuyển đổi Ở RANH GIỚI — comment
  trong mã (dòng 78-176, tiếng Việt) cảnh báo tên trường phải khớp CHỮ với
  `platform_core/workflow/di_tru_m1.py::_canh_v3` nếu không cổng "biến mất trong im lặng".
  **`kind:'CONTROL'` được định nghĩa ở kiểu nhưng `edgeToV3` luôn gán cứng `'DATA'`** — client hiện
  không tạo được cạnh CONTROL (edgeToV3, dòng 116).

Round-trip API: `GET/POST /agent/api/v3/workflows` (`listWorkflowsV3`,`createWorkflowV3`,
`workflowApi.ts:198-219`), `GET/PUT /agent/api/v3/workflows/{id}` (`loadWorkflowV3`/`saveWorkflowV3`,
dòng 201-236, optimistic lock qua `If-Match: "{revision}"`), `POST .../publish` (`publishWorkflowV3`,
dòng 239-248). Đây là API **đang dùng thật** trong `CanvasShell.tsx` (`loadOrCreateWorkflowV3`,
`saveWorkflowV3`, dòng 16-18). Bộ API v2 cũ (`loadOrCreateWorkflow`, `saveWorkflow`, `planWorkflow`,
`validateWorkflow`, `createRun`... dòng 324-424) **vẫn tồn tại và được gọi** (`validateWorkflow`,
`createRun`, `planWorkflow` ở `CanvasShell.tsx:375,385,720`) nhưng thao tác trên `/agent/api/workflows`
(không phải `/v3/`) — nghĩa là **luồng lưu dùng v3, nhưng luồng validate/run/AI-dựng-canvas vẫn
gọi endpoint `/agent/api/workflows/{id}/...` kiểu cũ** trên cùng object `Workflow` đã được `tuV3()`
map ngược lại v2. Đây là điểm ghép nối hai bảng dữ liệu (`WorkflowDraft` v3 và `AgentWorkflow.document`
v2) mà comment trong mã tự nhận là "cửa nối tạm, không phải lớp tương thích vĩnh viễn"
(`workflowApi.ts:138-145`).

## 7. Run view

**Poll, không SSE**, cho run: `useEffect` ở `CanvasShell.tsx:213-220` — khi `run.status==='running'`,
`setTimeout` gọi `tickRun()` (`POST /agent/api/runs/{id}/tick`) sau 1200ms (hoặc tới `scheduled_at`,
tối đa 60s), rồi lặp qua re-render. Không dùng `EventSource`/WebSocket cho run.

(Ghi chú: `previewAssistant()` ở `workflowApi.ts:264-282` DÙNG SSE thật — đọc `response.body` dạng
`event:/data:` — nhưng đó là luồng "AI assistant" phân tích/đề xuất canvas, không phải run.)

Trạng thái node: `__status` tính từ `run?.checkpoint[node.id]?.status` (fallback `invalid`/`draft`/
`validated`, `CanvasShell.tsx:518-520`), hiển thị nhãn tiếng Việt trong `ToolNode.tsx:27-29,98-100`.
Edge "đang chạy" tô sáng khi `source done && target !=='done'` (`CanvasShell.tsx:548`).

Chi phí: `run.estimated`/`run.actual` hiển thị ở `RunInspector.tsx:11,660,670`; báo giá node qua
`quoteTool()` polling debounce 450ms mỗi khi `page.nodes` đổi (`CanvasShell.tsx:236-244`,
`POST /agent/api/tools/{tool}/quote`).

Lỗi: `run.checkpoint[step].error|reason` hiển thị trong `RunInspector.tsx:12`; lỗi chung
(`runError` state) hiển thị banner `role="alert"` (`CanvasShell.tsx:671`). Có nhánh lỗi trên edge
(`condition:'error'`, `toggleErrorBranch`, `CanvasShell.tsx:435`) — chỉ ở chế độ "legacy".

Retry: **không có nút retry từng step riêng lẻ** trong UI hiện tại — chỉ có "Chạy lại theo cấu hình
này" (`runAgain()`, toàn bộ run mới, `CanvasShell.tsx:668`) và "Hủy chạy"/"Hủy bản chạy"
(`cancelRun`). `on_fail`/`max_retry` là param mỗi node (`editorState.ts:359`, mặc định
`on_fail:'retry_same', max_retry:0`) nhưng đây là cấu hình gửi lên server lúc build node
(`nextNode()`), không phải điều khiển retry thủ công trong Run panel.

## 8. Biểu thức {{ }} / variable picker / autocomplete

**Không có cú pháp `{{ }}`** trong toàn bộ package (grep không khớp). Cơ chế tham chiếu dữ liệu
giữa node dùng chuỗi `$<nodeId>.<outputHandle>` (vd. `editorState.ts:70,217,252,258`,
`CanvasShell.tsx:277,279,301`), gán trực tiếp vào `params[field]` khi user nối dây (không phải
người dùng gõ tay biểu thức).

**Có "variable picker" dạng UI**, không phải autocomplete gõ chữ:
- `CreativeToolNode` (`ToolNode.tsx:168-173`) có `<select>` "Thêm nội dung từ block khác" liệt kê
  `__references` (tính từ `referenceOptions`, `CanvasShell.tsx:132-147`) — chọn xong gọi
  `__onReference` → tạo edge (không sinh text biểu thức).
- `quickConnect`/`quickCreate`/`edgeInsert` (`CanvasShell.tsx:579-603,781-793`) là các picker
  "bước tiếp theo tương thích" khi kéo dây ra khoảng trống hoặc bấm "+" trên output handle.
- Không có ô nhập text nào cho phép gõ `$node.output` hay `{{ }}` thủ công; toàn bộ tham chiếu được
  tạo qua thao tác kéo-nối hoặc chọn trong picker/select — không có autocomplete kiểu Slack/Notion.

Server-side (`platform_core/workflow/bieu_thuc.py` — tên "biểu thức" = expression) dường như đã có
khái niệm expression riêng, nhưng **canvas frontend hiện tại không expose nó** (không tham chiếu
`bieu_thuc` hay cú pháp biểu thức nào trong `frontend/agent-canvas`).

## 9. Test frontend

Chỉ **vitest** (config: `vite.config.ts:14-27`, `environment:'jsdom'`, `testTimeout:20000` — nâng từ
mặc định 5000ms sau sự cố đo sai do máy bận, xem comment trong file). **Không có Playwright/E2E**
trong package này (không thấy `@playwright/test` trong `package.json`, không thư mục `e2e/`).

71 `it/test(...)` trong 6 tệp:
- `tests/CanvasShell.test.tsx` — 23 test (component lớn nhất, nhiều side-effect nhất)
- `tests/workflowApi.test.ts` — 18 test (v2/v3 converter, request wrapper)
- `tests/editorState.test.ts` — 19 test (reducer, connectionAllowed, cycle, clone…)
- `tests/presentationAdapter.test.ts` — 5 test
- `tests/Inspector.test.tsx` — 3 test
- `tests/nodePresentation.test.ts` — 3 test
- `tests/setup.ts` — 19 dòng, chỉ thiết lập môi trường (không test case)

## 10. Đánh giá — refactor cần thiết cho NodeRenderer tổng quát (Trigger/Control/Utility/Connector/App/AI/Subworkflow)

**Vấn đề gốc**: kiến trúc hiện tại giả định **một kiểu node duy nhất** ("tool" với `data.tool` là
tên chuỗi + `data.params`) và suy loại hiển thị bằng cách **soi tiền tố tên chuỗi** (`text./image./
video./audio./asset.`), không có khái niệm "loại node" (`kind`) tách biệt khỏi "tool nào". Không có
kiểu `NodeKind` nào ở phía client dù server (`platform_core/workflow/trigger.py`, `dieu_khien.py`
=control, `foreach.py`, `join.py`, `bieu_thuc.py`=expression, `he_kieu.py`=type system) rõ ràng đã
có mô hình phong phú hơn nhiều loại node so với những gì canvas hiện lộ ra.

Refactor cần làm, theo tệp:

1. **`src/workflowApi.ts`** — thêm field `kind: 'trigger'|'control'|'utility'|'connector'|'app'|
   'ai'|'subworkflow'|'tool'` vào `CanvasNode`/`PaletteTool` (hoặc đối tượng schema mới), và ánh xạ
   `kind` này trong `edgeToV3`/`fromV3` nếu server v3 phân biệt loại node — hiện `CanvasNode.type`
   bị khoá cứng `'tool'` (dòng 3) và mọi node record chỉ có `data.tool`/`data.params`, không có
   trường phân loại độc lập với tool cụ thể. **Đây là thay đổi kiểu dữ liệu nền, mọi nơi khác phụ
   thuộc vào nó.**

2. **`src/nodePresentation.ts` + `src/presentationAdapter.ts`** — thay `nodeModality()`/
   `creativeModality()` (suy loại từ tiền tố tên chuỗi) bằng hàm đọc trực tiếp `node.kind`/`tool.kind`
   do server cấp — bỏ toàn bộ danh sách hardcode (`explicitModalities`, `coreTools`, `actionLabels`,
   các `startsWith('text.')...`). Cần bảng icon/label/tier theo 7 loại mới thay cho 4 modality
   text/image/video/audio hiện có.

3. **`src/ToolNode.tsx`** — đây là chỗ nặng nhất. Cả `ToolNode` và `CreativeToolNode` viết cứng logic
   hiển thị cho "block tạo nội dung tạo sinh" (preview ảnh/video/audio, nút "Tạo bằng AI", upload
   file, textarea nội dung). Cần tách thành **NodeRenderer điều phối theo `kind`** + các "renderer
   con" chuyên biệt: `AIBlockNode` (giữ logic hiện có gần nguyên), `TriggerNode` (không có `params`
   dạng content, cần UI lịch/sự kiện), `ControlNode` (if/foreach/join — cần hiển thị nhánh, không có
   1 input/1 output cố định như hiện tại — xem điểm 5), `ConnectorNode`/`AppNode` (kết nối dịch vụ
   ngoài — cần UI auth/cấu hình khác hẳn upload-file), `SubworkflowNode` (tham chiếu workflow khác —
   cần link "mở workflow con" + hiển thị input/output của sub-workflow đó, khác hẳn `params_schema`
   phẳng hiện tại). `icon:Record<string,string>` (dòng 19) và `labels` trạng thái (dòng 27-29,
   98-100) cần mở rộng/tách theo kind.

4. **`src/editorState.ts`** — `connectionAllowed()` (dòng 291-302) giả định input/output đều nằm
   trong `params_schema`/`returns` phẳng của một "tool". Node Control (if/foreach/join) có nhiều
   output theo nhánh (true/false, mỗi lần lặp...) và Trigger có 0 input — cần khái quát hoá luật
   cổng để không giả định "mọi node đều có params_schema kiểu field=value". `replaceNodeTool()`
   (dòng 196-268, logic suy đoán lại kết nối khi đổi tool) cũng giả định đổi trong cùng một họ
   "tool" — đổi *kind* (vd Trigger→Control) cần luật khác hẳn.

5. **`src/CanvasShell.tsx`** (910 dòng, file trung tâm) — `nodeTypes` (dòng 22) cần thêm entry mới
   cho từng renderer; `displayNodes` (dòng 490-543) hiện gắn cứng `inputFields`/`outputHandles` dựa
   trên `params_schema`/`returns` — cần nhánh theo `kind` để tính handle cho Control (nhiều output
   nhánh) khác Trigger (0 input) khác Subworkflow. Palette (`groups`, dòng 563-569) và các picker
   (`quickConnect`/`quickCreate`/`edgeInsert`, dòng 579-603) lọc tool bằng `connectionAllowed` — cần
   mở rộng để Trigger chỉ xuất hiện như điểm bắt đầu (không "nối vào" như hiện tại), Subworkflow cần
   luồng chọn workflow con (chưa có UI nào ở đây), Connector/App cần luồng cấu hình credential
   (hoàn toàn chưa tồn tại — hiện chỉ có form field/select/checkbox/upload chung).

6. **`src/Inspector.tsx`** — `primaryFields()`/`contentFields` giả định 1 danh sách field phẳng ưu
   tiên cứng (`prompt/topic/text/url/source_url`) — không có khái niệm "cấu hình đặc thù theo kind"
   (vd Trigger cần lịch cron, Subworkflow cần chọn workflow + map input).

**Kết luận ngắn**: hệ thống hiện tại là **canvas chuyên biệt cho một loại node** ("AI generation
tool", ẩn dưới các modality text/image/video/audio), không phải canvas tổng quát nhiều loại node.
Để có 7 NodeRenderer như yêu cầu, cần: (a) thêm trường `kind` ở tầng dữ liệu (workflowApi.ts) đến từ
server, (b) tách renderer theo kind thay vì theo modality suy từ tên chuỗi, (c) khái quát hoá mô
hình cổng/kết nối để không giả định input/output luôn là `params_schema`/`returns` phẳng 1-1.
Không có refactor "nhỏ" khả thi — đây là thay đổi kiến trúc xuyên suốt cả 6 tệp `src/` (trừ
`workflowApi.ts` phần converter v2/v3 và `RunInspector.tsx`/`CanvasEdgeView.tsx` ít bị ảnh hưởng
hơn vì chúng không giả định loại node).
