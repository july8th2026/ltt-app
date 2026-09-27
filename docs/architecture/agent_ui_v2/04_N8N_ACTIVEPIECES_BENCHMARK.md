# n8n + Activepieces — UI/UX benchmark (2026-09-27)

Phạm vi: CHỈ UI/UX (canvas, node search, NDV/data mapping, expression editor, execution UX,
trạng thái node trên canvas, onboarding, connections UX, terminology, giấy phép). KHÔNG lặp lại
phần runtime/engine (đồ thị, thi hành, bền vững, credential mã hoá, expression sandbox, wait mode,
error-workflow, license) đã có ở các audit cũ — xem mục "Quan hệ với audit cũ" ngay dưới.

Sources: điền dần theo từng mục — mỗi claim có URL (docs.n8n.io / activepieces.com/docs),
repo path (`n8n-io/n8n`, `activepieces/activepieces`), hoặc số issue/PR.

---

## Quan hệ với audit cũ

`05_N8N_AUDIT.md` và `04_ACTIVEPIECES_AUDIT.md` (thư mục `workflow_v2_audit/`) khảo sát mã nguồn
tầng RUNTIME/ENGINE: mô hình đồ thị (n8n có đồ thị thật cạnh có kiểu; Activepieces không phải đồ
thị), thi hành (cả hai tuần tự), bền vững (n8n binary-data; Activepieces waitpoint ở CSDL), version,
mô hình lỗi, SDK piece, credit. `32_AUDIT_...benchmark.md` §1 khảo sát thêm n8n: ba tầng cú pháp
expression, mã hoá credential hai tầng (DEK + khoá instance), 4 chế độ resume của Wait node,
error-workflow chỉ kích hoạt khi lỗi thật, và giấy phép Sustainable Use License nguyên văn — **các
mục này KHÔNG lặp lại ở tài liệu này**, chỉ dẫn số mục khi liên quan. Tài liệu này bổ sung phần các
audit cũ **không đụng tới**: cách người dùng THẤY và THAO TÁC — canvas, tìm node, NDV/kéo-thả map dữ
liệu, expression editor UI (không phải sandbox), execution replay, trạng thái node trên canvas,
onboarding, và — quan trọng nhất với Activepieces — luồng UI tạo connection/OAuth.

---

## 1. n8n — Canvas UX

**Thư viện canvas**: `@vue-flow/core` — xác nhận trực tiếp trong
`packages/frontend/editor-ui/package.json` (n8n-io/n8n) và trong kiểu `CanvasNode = Node<CanvasNodeData>`,
`GraphNode`, `OnConnectStartParams` import từ `@vue-flow/core` tại
`packages/frontend/editor-ui/src/features/workflows/canvas/canvas.types.ts`. n8n không tự viết canvas từ
đầu — họ bọc Vue Flow bằng lớp `CanvasNodeData`/`CanvasGroupNodeData` riêng.

**Nối cạnh và chèn node giữa cạnh**: kéo từ chấm xám hoặc icon **Add node** bên phải một node sang
node kế tiếp để tạo cạnh
([Connect nodes together](https://docs.n8n.io/build/understand-workflows/workflow-components/connect-nodes-together)).
Docs không mô tả nút `+` giữa cạnh, nhưng mã nguồn xác nhận nó có thật: mỗi cạnh có một
`CanvasEdgeToolbar.vue` (hiện khi hover cạnh) với hai nút — `add` (chèn node giữa cạnh — hiện cho
`Main` connection, hoặc cho `AiTool` connection nối vào Agent, nhãn đổi thành "add human review step"
khi phù hợp) và `delete` (xoá cạnh). Nguồn:
n8n-io/n8n `packages/frontend/editor-ui/src/features/workflows/canvas/components/elements/edges/
CanvasEdgeToolbar.vue`.

**Node context menu** (hover → icon dấu ba chấm) — danh sách đầy đủ từ
`work-with-nodes.md`: Open node · Execute step · Rename node · Deactivate node · Pin node · Copy node
· Duplicate node · Tidy up workflow · Convert node to sub-workflow · Select all · Clear selection ·
Delete node. Ba control luôn hiện khi hover (không cần mở menu): **Execute step**, **Deactivate**,
**Delete**.

**Sticky notes**: hỗ trợ Markdown subset, thêm bằng double-click canvas trống → "Add Note", nút `+`
ở cuối canvas, hoặc phím tắt `S` (thả tại vị trí con trỏ).

**Pinned data**: phím `P` để ghim dữ liệu output của một node — n8n dùng dữ liệu ghim thay vì chạy
lại node đó khi test các node phía sau (tiết kiệm gọi API tốn tiền/chậm).

**Canvas Groups** (⭐ tính năng mới, rollout dần từ n8n 2.28.0, toàn instance từ 2.31.0) — gom nhiều
node liền kề thành một khối có tên + mô tả tuỳ chọn (≤145 ký tự), thu gọn/mở rộng độc lập (trạng thái
thu gọn lưu ở trình duyệt, KHÔNG lưu vào workflow — mỗi người xem tự chọn view của mình). Quy tắc hợp
lệ: nhóm phải là một chuỗi liên kết, không chứa trigger, node ngoài nhóm chỉ được nối vào node đầu/cuối
nhóm (không nối giữa), sub-node AI (chat model/memory/tool) phải cùng nhóm với node gốc của nó. Nhóm
tự "roll up" trạng thái thực thi con thành một `GroupExecutionStatus` (`waiting|running|error|issues|
warning|success`) khi thu gọn (`packages/frontend/editor-ui/.../canvas.types.ts`).

**Selection box / alignment / minimap**: chọn nhiều node bằng kéo vùng chọn hoặc `Ctrl/Cmd`+click
từng node (dùng để group). Docs không nhắc tới minimap hay alignment/helper-lines snapping —
KHÔNG XÁC MINH ĐƯỢC có tồn tại hay không (không tìm thấy trong docs chính thức lẫn keyboard-shortcuts
page); có "Tidy up workflow" trong context menu (tự động sắp bố cục) nhưng đó là auto-layout theo yêu
cầu, không phải helper-line khi kéo tay.

**Zoom-to-fit**: phím `1` = zoom to fit workflow, `0` = reset/center. Zoom bằng `+`/`-`/`Ctrl+wheel`.

**Bộ phím tắt đầy đủ** (nguồn: `docs.n8n.io/build/keyboard-shortcuts`):
- Workflow: `Ctrl/Cmd+Alt+N` tạo mới · `Ctrl/Cmd+O` mở · `Ctrl/Cmd+S` lưu · `Ctrl/Cmd+Z`/`Shift+Z`
  undo/redo · `Ctrl/Cmd+Enter` chạy workflow.
- Canvas: `Ctrl/Cmd`+kéo hoặc `Space`+kéo hoặc chuột giữa+kéo = pan; `+`/`-`/`0`/`1` zoom;
  `Ctrl/Cmd+Mouse Wheel` zoom.
- Node: double-click mở NDV · `Ctrl/Cmd`+double-click (sub-workflow) mở tab mới · `Alt+G`/`Shift+Alt+G`
  expand/collapse group · `Ctrl/Cmd+A` chọn hết · `Ctrl/Cmd+C/X/V` copy/cut/paste · `Ctrl/Cmd+G`/
  `Ctrl/Cmd+Shift+G` group/ungroup · phím mũi tên di chuyển giữa node kề · `Shift`+mũi tên chọn nhiều ·
  `D` deactivate · `Delete` xoá · `Enter` mở · `F2` rename · `P` pin · `Shift+S` thêm sticky note.
- Node Panel: `N` mở · `Enter` chèn · `Escape` đóng · mũi tên trái/phải collapse/expand category.
- Command bar: `Ctrl/Cmd+K` mở command palette (điều hướng workflow/executions/settings).
- Trong tham số: `=` chuyển ô tham số rỗng sang chế độ expression.

Nguồn: [Keyboard shortcuts](https://docs.n8n.io/build/keyboard-shortcuts),
[Connect nodes together](https://docs.n8n.io/build/understand-workflows/workflow-components/connect-nodes-together.md),
[Work with nodes](https://docs.n8n.io/build/understand-workflows/workflow-components/work-with-nodes.md),
[Canvas Groups](https://docs.n8n.io/build/understand-workflows/workflow-components/canvas-groups.md),
n8n-io/n8n `packages/frontend/editor-ui/src/features/workflows/canvas/canvas.types.ts`.

**Bài học cho LTT:**
1. **Canvas Groups** đáng chép nguyên ý tưởng nhất trong mục này: khối có tên, mô tả ngắn, thu gọn
   theo SỞ THÍCH NGƯỜI XEM (không phải trạng thái workflow) — LTT có thể dùng đúng mô hình này để dọn
   canvas Agent/Workflow phức tạp mà không đổi ngữ nghĩa đồ thị.
2. Roll-up trạng thái thực thi của một nhóm thành MỘT giá trị enum khi thu gọn (không hiển thị 12 node
   con nhấp nháy cùng lúc) là mẫu hình đáng học cho canvas LTT khi có sub-workflow lồng nhau.
3. Bộ điều khiển hover tối giản (Execute/Deactivate/Delete luôn hiện, còn lại vào menu ba chấm) là
   pattern giảm nhiễu thị giác đáng tham khảo hơn là phơi hết action ra ngoài.

## 2. n8n — Node search / quick-add

Mở panel bằng: nút **Add first step** (workflow rỗng), icon **Add node** cạnh phải một node, `+` góc
canvas, hoặc phím `N`. Ô tìm kiếm ở đầu panel; điều hướng bằng mũi tên trái/phải để collapse/expand
category, `Enter` để chèn.

**Phân loại (category) ở mức gốc** — trước khi thêm trigger, panel chỉ hiện các loại **trigger node**;
sau khi đã có trigger, panel đổi sang hiện: Advanced AI · Actions in an App · Data transformation ·
Flow · Core · Human in the loop
([Work with nodes](https://docs.n8n.io/build/understand-workflows/workflow-components/work-with-nodes.md);
hằng số xác nhận trong mã: `CORE_NODES_CATEGORY`, `HUMAN_IN_THE_LOOP_CATEGORY`,
`TRANSFORM_DATA_SUBCATEGORY`, `FLOWS_CONTROL_SUBCATEGORY`, `HELPERS_SUBCATEGORY`,
`FILES_SUBCATEGORY` — n8n-io/n8n `packages/frontend/editor-ui/src/app/constants/nodeCreator.ts`).

**"AI" là một subcategory RIÊNG, có cây phân loại con của chính nó** (không lẫn vào 6 category gốc
ở trên) — đọc trực tiếp từ hằng số trong `nodeCreator.ts`: `AI_CATEGORY_AGENTS` (Agents),
`AI_CATEGORY_CHAINS` (Chains), `AI_CATEGORY_LANGUAGE_MODELS` (Language Models), `AI_CATEGORY_MEMORY`
(Memory), `AI_CATEGORY_OUTPUTPARSER` (Output Parsers), `AI_CATEGORY_TOOLS` (Tools),
`AI_CATEGORY_VECTOR_STORES` (Vector Stores), `AI_CATEGORY_RETRIEVERS` (Retrievers),
`AI_CATEGORY_EMBEDDING` (Embeddings), `AI_CATEGORY_DOCUMENT_LOADERS` (Document Loaders),
`AI_CATEGORY_TEXT_SPLITTERS` (Text Splitters), `AI_CATEGORY_ROOT_NODES` (Root Nodes),
`AI_CATEGORY_MCP_NODES` (Model Context Protocol), `AI_CATEGORY_HUMAN_IN_THE_LOOP`, `AI_EVALUATION`
(Evaluation), `AI_UNCATEGORIZED_CATEGORY` (Miscellaneous) — tổng cộng 15 category con, phân theo VAI
TRÒ trong một cluster (LangChain-style) chứ không theo nhà cung cấp (Anthropic/OpenAI chỉ là item bên
trong "Language Models"). Có riêng `AI_SECTION_RECOMMENDED_TOOLS` (gợi ý Tool phù hợp) và
`NEW_TOOL_CATEGORIES` đánh dấu category mới (hiện là MCP Nodes) để làm nổi bật trong panel.

**Sub-node vs root-node (cluster node)**: một cụm chức năng AI gồm một **root node** (vd. AI Agent)
cộng một hoặc nhiều **sub-node** gắn vào nó (Chat Model, Memory, Tool — mỗi loại là một "input" kiểu
riêng trên root node, không phải cạnh dữ liệu Main bình thường). Sub-node hành xử KHÁC root node khi
xử lý nhiều item bằng expression (docs:
[Sub-nodes](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes)).

**Add node từ output handle**: kéo/chọn `+`/chấm xám bên phải một node → mở nodes panel đã lọc theo
ngữ cảnh (loại connection cần) → chọn node → n8n tự nối vào node đã chọn
([Connect nodes together](https://docs.n8n.io/build/understand-workflows/workflow-components/connect-nodes-together.md)).
Cùng cơ chế `add` dùng cho nút trên `CanvasEdgeToolbar` khi chèn giữa một cạnh có sẵn (mục 1).

Nguồn: n8n-io/n8n `packages/frontend/editor-ui/src/app/constants/nodeCreator.ts`,
`packages/frontend/editor-ui/src/features/shared/nodeCreator/`,
[Work with nodes](https://docs.n8n.io/build/understand-workflows/workflow-components/work-with-nodes.md),
[Sub-nodes](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes).

**Bài học cho LTT:**
1. Tách "AI" thành cây phân loại con theo VAI TRÒ (Agent/Model/Memory/Tool/Vector Store/Retriever…)
   thay vì theo nhà cung cấp là cách tổ chức panel node AI mà LTT nên chép khi node/tool AI của LTT
   tăng số lượng — tránh panel gốc phình ra hàng chục item phẳng.
2. Root-node/sub-node (input kiểu riêng, không phải cạnh Main) là mô hình đáng tham khảo để biểu diễn
   "Agent cần Model + Memory + Tools" trên canvas mà không biến mỗi phụ kiện thành một node độc lập nối
   bằng cạnh dữ liệu thường — giữ đồ thị chính sạch.
3. Panel đổi nội dung theo NGỮ CẢNH (trigger-only khi workflow rỗng, đầy đủ category sau đó) giảm
   nhiễu cho người mới — đáng áp dụng cho node picker của LTT.

## 3. n8n — NDV (Node Details View)

**Bố cục 3 cột INPUT | PARAMETERS | OUTPUT**: khi mở một node (double-click hoặc `Enter`), NDV hiện
dữ liệu vào ở cột trái, tham số cấu hình ở giữa, dữ liệu ra ở cột phải — cho phép so sánh trực tiếp
"trước" và "sau" khi chỉnh tham số.

**4 chế độ xem dữ liệu** (INPUT/OUTPUT pane), đọc trực tiếp từ danh sách trong
`RunDataDisplayModeSelect.vue`: **Schema** (mặc định), **Table**, **JSON**, và **Binary** (chỉ hiện khi
item có dữ liệu nhị phân); ngoài ra "HTML" hoặc "Rendered" (AI) được thêm vào đầu danh sách khi node
trả về HTML hoặc nội dung AI cần render. Việc đặt **Schema làm mặc định** (không phải Table hay JSON)
có chủ đích: Schema là view kéo-thả được, JSON/Table chỉ để đọc.

**Kéo-thả từ Schema view vào tham số — cách map KHÔNG GÕ SYNTAX**: Schema view (`VirtualSchema.vue` /
`VirtualSchemaItem.vue`) vẽ cây tên trường của node nguồn dạng có thể kéo. Người dùng cầm một
field-pill kéo sang một ô tham số bên cột PARAMETERS; trong lúc kéo, một "dragPill" nổi theo con trỏ
(`MappingPill.vue`) đổi màu — xanh dương (đang kéo, `defaultPill`) → xanh lá (`droppablePill`, hiện
đúng vị trí có thể thả) — cho phản hồi thị giác trước khi thả tay. Khi thả, n8n **tự sinh biểu thức**
tham chiếu tới trường đó (vd. `{{ $json.fieldName }}`) và ghi thẳng vào ô tham số — người dùng không
gõ một ký tự cú pháp nào
([Referencing data in the UI](https://docs.n8n.io/data/data-mapping/data-mapping-ui/)). Với tham số
chỉ nhận một chuỗi đơn (không phải collection), node cần khai `requiresDataPath: 'single'` hoặc
`'multiple'` để bật kéo-thả tên trường thay vì giá trị
([Node UI elements](https://docs.n8n.io/integrations/creating-nodes/build/reference/ui-elements/)).

**Tìm kiếm trong dữ liệu**: `RunDataSearch.vue` cho phép search trực tiếp trong input/output pane
(hữu ích khi item có hàng trăm field).

**Ghim/pin trực tiếp từ NDV**: `RunDataPinButton.vue` — cùng cơ chế phím tắt `P` ở mục 1, nhưng bấm
được ngay trong OUTPUT pane của NDV.

Nguồn: n8n-io/n8n `packages/frontend/editor-ui/src/features/ndv/runData/components/`
(`RunDataDisplayModeSelect.vue`, `VirtualSchema.vue`, `VirtualSchemaItem.vue`, `MappingPill.vue`,
`RunDataSearch.vue`, `RunDataPinButton.vue`),
[Referencing data in the UI](https://docs.n8n.io/data/data-mapping/data-mapping-ui/),
[Use the UI mapper](https://docs.n8n.io/build/work-with-data/reference-data/use-the-ui-mapper),
[Node UI elements](https://docs.n8n.io/integrations/creating-nodes/build/reference/ui-elements/).

**Bài học cho LTT:**
1. **Schema-là-mặc-định + kéo-thả sinh biểu thức tự động** là câu trả lời rõ nhất cho "map dữ liệu
   không cần gõ syntax" trong toàn bộ khảo sát — đáng PORT nguyên ý tưởng (không phải mã, xem mục 12)
   vào NDV-tương-đương của LTT: cây field kéo được + ô tham số nhận thả + tự sinh reference.
2. Đổi màu pill lúc kéo (xanh dương → xanh lá khi hợp lệ) là phản hồi thị giác rẻ tiền nhưng hiệu quả,
   dễ chép cho bất kỳ drag-drop mapping UI nào.
3. `requiresDataPath` là chi tiết cần nhớ nếu LTT làm SDK node/tool riêng: khai báo tường minh field
   nào nhận "đường dẫn" (path) thay vì "giá trị" khi kéo thả — nếu không, kéo-thả sẽ chèn nhầm loại dữ
   liệu vào tham số dạng chuỗi đơn.

## 4. n8n — Expression editor UX

**Inline VÀ modal, cả hai đều CodeMirror-based**: n8n có hai component riêng —
`InlineExpressionEditorInput.vue` (sửa ngay trong ô tham số, dùng khi biểu thức ngắn) và
`ExpressionEditorModalInput.vue` (mở modal lớn hơn, dùng khi biểu thức dài/phức tạp) — cả hai dùng
chung nền CodeMirror của n8n (deepwiki:
[Parameter Input and Expression Editor](https://deepwiki.com/n8n-io/n8n/6.3-parameter-input-and-expression-editor)).
Chuyển sang chế độ expression bằng cách gõ `=` vào đầu ô tham số rỗng, hoặc bấm icon expression cạnh
tham số.

**Preview kết quả evaluate TRỰC TIẾP (live)**: cả ô inline và modal đều hiện giá trị đã tính của biểu
thức ngay dưới/cạnh ô nhập, cập nhật theo dữ liệu input hiện tại của node (không cần chạy lại workflow
nếu đã có run data hoặc pinned data).

**Hiển thị lỗi ngay trong preview** — hai kiểu lỗi quan sát được:
- Không tính được vì thiếu dữ liệu chạy: cộng đồng gọi là lỗi
  `[ERROR: Can't get data for expression]` khi node nguồn CHƯA CHẠY hoặc bị rẽ nhánh cả hai đầu IF
  ([n8n Community](https://community.n8n.io/t/error-can-t-get-data-for-expression-on-set-node-variable-preview-when-connected-to-both-ends-of-if-node/26495)).
- Đọc field của item đã bị REDACT (ẩn vì chứa dữ liệu nhạy cảm): preview hiện `[undefined]` bằng style
  đỏ "invalid" — dễ gây hiểu lầm là cả run đã lỗi dù không phải; PR
  [#38577](https://github.com/n8n-io/n8n/pull/38577) đang sửa để hiện "reveal prompt" thay vì trực
  tiếp báo lỗi trong trường hợp này (⭐ bằng chứng rằng chính n8n cũng coi UX lỗi che dữ liệu là một bug
  cần sửa, không phải hành vi mong muốn).

**Autocomplete + info-box tooltip**: `infoBoxTooltips()` là một CodeMirror extension riêng cho hộp gợi
ý; `autocompleteTelemetry` gắn theo từng `parameterPath` (đo lường việc dùng autocomplete). Node Code
tích hợp CÙNG bộ autocomplete `$json`/`$node`/... ngay trong JS/Python thô, không chỉ trong ô tham số
biểu thức thường.

**Không có "variable/data browser tree" tách biệt khỏi NDV**: cây biến chính là Schema view của cột
INPUT (mục 3) — kéo từ đó sinh biểu thức, không có một panel "danh sách biến toàn cục" riêng như một
số công cụ khác.

Nguồn: n8n-io/n8n `packages/frontend/editor-ui/src/features/shared/editors/components/
InlineExpressionEditor/InlineExpressionEditorInput.vue`,
`packages/frontend/editor-ui/src/features/ndv/parameters/components/ExpressionEditorModal/
ExpressionEditorModalInput.vue`,
[DeepWiki 6.3 Parameter Input and Expression Editor](https://deepwiki.com/n8n-io/n8n/6.3-parameter-input-and-expression-editor),
[Expressions for data transformation](https://docs.n8n.io/data/expressions-for-transformation/),
[PR #38577](https://github.com/n8n-io/n8n/pull/38577),
[n8n Community — Can't get data for expression](https://community.n8n.io/t/error-can-t-get-data-for-expression-on-set-node-variable-preview-when-connected-to-both-ends-of-if-node/26495).

(Xem thêm `32_AUDIT_2026-09-22_benchmark.md` §1.1 cho ba TẦNG CÚ PHÁP expression ở mức engine — không
lặp lại ở đây, mục này chỉ nói UI của editor.)

**Bài học cho LTT:**
1. Preview evaluate-trực-tiếp ngay trong ô nhập (không cần "Run" riêng để xem giá trị) là chuẩn UX tối
   thiểu đáng chép cho bất kỳ ô biểu thức/expression nào LTT thêm vào Agent/Canvas.
2. Bài học NGƯỢC (tránh): đừng để trạng thái "dữ liệu bị che/ẩn vì nhạy cảm" và "biểu thức lỗi thật"
   dùng chung MỘT kiểu hiển thị lỗi màu đỏ — chính n8n đang phải vá lỗi này (PR #38577); LTT nên phân
   biệt rõ hai trạng thái ngay từ đầu.
3. Có cả inline lẫn modal (ngắn dùng inline, dài mở modal) là lựa chọn hợp lý để không ép người dùng
   luôn mở modal cho biểu thức một dòng.

## 5. n8n — Execution UX

**Executions list** — tab **Executions** trong workflow, lọc theo **Status** (`Failed`/`Running`/
`Success`/`Waiting`), theo thời điểm bắt đầu, hoặc theo custom data do Code node ghi
([View executions for a single workflow](https://docs.n8n.io/build/understand-workflows/understand-executions/view-executions-for-a-single-workflow.md)).
Chọn một hàng → n8n tách hành động theo kết quả: execution **thất bại** → nút **Debug in editor**;
execution **thành công** → nút **Copy to editor**. Cả hai đều COPY dữ liệu execution đó vào workflow
hiện tại và **ghim (pin) dữ liệu ngay ở node ĐẦU TIÊN** của workflow — tức là "replay trên canvas"
của n8n thực chất là biến toàn bộ input của lần chạy cũ thành pinned-data rồi cho người dùng chạy lại
từng bước trên chính canvas đang sửa, KHÔNG PHẢI một canvas "replay" riêng tách khỏi editor
([Debug and re-run past executions](https://docs.n8n.io/build/understand-workflows/understand-executions/debug-executions.md)).

**Retry của một execution đã fail** (không phải "retry from a node") — trong Executions list, bấm
**Refresh** trên hàng execution đó, rồi chọn: **Retry with currently saved workflow** (dùng workflow
đã sửa + input cũ) hoặc **Retry with original workflow** (chạy y hệt lần trước, không đổi gì).

**Partial execution ("execute this node only")**: chọn node → mở NDV → **Execute step**. n8n chạy
CHÍNH node đó cộng các node PHÍA TRƯỚC cần thiết để có đủ input cho nó (không phải chỉ một node đơn
lẻ cô lập). Yêu cầu workflow phải có trigger nối tới node đó (kể cả Manual Trigger) vì partial execution
cố mô phỏng production execution. Có giới hạn kích thước payload — workflow nhiều nhánh dễ gặp lỗi
"existing execution data is too large", khắc phục bằng Limit node tạm thời
([Manual, partial, and production executions](https://docs.n8n.io/build/understand-workflows/understand-executions/types-of-executions.md)).

**⭐ "Dirty node" — trạng thái stale, KHÔNG chỉ success/error** (đây là câu trả lời gián tiếp hay nhất
cho "waiting/error node được vẽ thế nào"): một node từng chạy OK nhưng n8n cho là dữ liệu đã CŨ/không
còn đáng tin — vẽ viền màu khác + tam giác vàng thay vì tick xanh; hover tam giác trong OUTPUT pane của
NDV ra tooltip giải thích lý do. Bị đánh dấu dirty khi: chèn/xoá node phía trước, sửa tham số, thêm
connector mới, deactivate node phía trước, unpin/sửa pinned data, hoặc bất kỳ điều trên xảy ra TRONG
một loop (khi đó cả node đầu loop cũng dirty). Với sub-node AI: sửa/thêm/xoá/(de)activate sub-node lan
dirty lên tới root node.
Xoá trạng thái dirty = chạy lại node đó (chạy cả workflow, hoặc partial execution bằng **Execute step**
trên chính nó hoặc một node phía sau)
([Dirty nodes](https://docs.n8n.io/build/understand-workflows/understand-executions/understand-dirty-nodes.md)).

Nguồn: các trang trên trong `docs/build/understand-workflows/understand-executions/` (n8n-io/n8n-docs),
đối chiếu với hằng số `CanvasNodeDirtiness` (`parameters-updated` · `incoming-connections-updated` ·
`pinned-data-updated` · `upstream-dirty`) trong n8n-io/n8n
`packages/frontend/editor-ui/src/features/workflows/canvas/canvas.types.ts`.

**Bài học cho LTT:**
1. **"Dirty node" là mẫu hình đáng chép nhất trong toàn mục Execution UX**: một tầng trạng thái thứ ba
   nằm giữa "chưa chạy" và "lỗi" — "đã chạy nhưng dữ liệu không còn đáng tin vì thứ gì đó phía trước đã
   đổi". LTT có sổ credit/job thật (không phải demo) nên việc CẢNH BÁO người dùng "kết quả này đang xem
   là output CŨ, bấm chạy lại để chắc chắn" — thay vì im lặng để họ tưởng nhầm là mới — trực tiếp ngăn
   một lớp lỗi vận hành (quyết định dựa trên output stale).
2. Copy/Debug execution cũ = pin dữ liệu vào node đầu rồi tái sử dụng CHÍNH canvas editor (không xây
   một trình xem "replay" tách biệt) là lựa chọn kiến trúc rẻ, đáng học nếu LTT muốn debug execution mà
   không nuôi hai UI song song.
3. Yêu cầu partial execution phải có trigger + giới hạn payload là bài học TRÁNH: nếu LTT làm
   "execute this node only", phải tính trước ngưỡng kích thước dữ liệu gửi lên để không lặp lại lỗi
   "existing execution data is too large" của n8n trên workflow nhiều nhánh.

## 6. n8n — Trạng thái node trên canvas

Đọc trực tiếp từ `CanvasNodeDefault.vue` (class binding) + `CanvasNodeStatusIcons.vue` — n8n-io/n8n
`packages/frontend/editor-ui/src/features/workflows/canvas/components/elements/nodes/render-types/`:

| Trạng thái | Cách vẽ |
|---|---|
| **success** | viền theo `status-success` mixin (màu xanh lá), tick xanh trong `CanvasNodeStatusIcons` |
| **error** | viền theo `status-error` mixin (đỏ) |
| **running** | viền `status-running-border` + lớp phủ `::after` có ANIMATION (`status-running-animation`) — viền chạy/nhấp nháy, không tĩnh |
| **waiting** | viền `status-waiting-border` + `::after` animation riêng (`status-waiting-animation`) — waiting và running dùng cùng cơ chế animated-border nhưng màu/nhịp khác nhau, phân biệt được bằng mắt |
| **pinned** | viền màu riêng qua biến CSS `--node--border-color--pinned` (không animation) |
| **disabled** | viền `--color-canvas-node-disabled-border-color` + một lớp **gạch chéo phủ lên node** (`CanvasNodeDisabledStrikeThrough.vue`) + nhãn text "(disabled)" dưới tên node |
| **dirty/stale** | KHÔNG phải màu viền riêng mà một icon tam giác vàng thay tick xanh trong status-icon, xem mục 5 |
| **warning** (chỉ ở cấp Group) | dùng khi gộp trạng thái con — mixin riêng, không có ở node đơn |

Ngoài viền, **`CanvasNodeStatusIcons`** ở góc dưới-phải mỗi node còn gộp thêm (không loại trừ lẫn
nhau, có thể hiện đồng thời): icon số lượng item output (`runDataIterations`), icon pin (khi có pinned
data — phân biệt pin "thủ công" và pin do execution có sẵn: `hasPinnedData` vs `hasExecutionPinData`),
icon lỗi validation (tham số thiếu/sai — khác lỗi thực thi), icon "cần cấu hình credential"
(`needsCredentialSetup`, chỉ khi bật `credentialSetupWarnings`), và icon cảnh báo cho community node
chưa cài. **Group node** (Canvas Group thu gọn) tự quy về MỘT trong 6 giá trị
`GroupExecutionStatus = waiting|running|error|issues|warning|success` — trạng thái `crashed` ở cấp
node bị gộp vào các giá trị này khi roll-up lên group (mục 1).

Nguồn: n8n-io/n8n `packages/frontend/editor-ui/src/features/workflows/canvas/canvas.types.ts`,
`.../components/elements/nodes/render-types/CanvasNodeDefault.vue`,
`.../parts/CanvasNodeStatusIcons.vue`.

**Bài học cho LTT:**
1. Tách RÕ hai trục: viền (health tổng quát — success/error/running/waiting/pinned/disabled) và badge
   góc (chi tiết định lượng — số item, lỗi validation riêng biệt với lỗi thực thi, cảnh báo credential)
   là cách nhồi nhiều thông tin vào một node nhỏ mà không rối mắt — LTT nên tách tương tự thay vì dồn
   hết vào một icon.
2. Animation khác nhau cho running vs waiting (không chỉ khác màu) giúp phân biệt "đang chạy" và "đang
   chờ tín hiệu ngoài" ngay từ xa, không cần zoom/hover — hữu ích cho canvas Workflow của LTT có
   waitpoint thật (theo audit cũ, Activepieces/LTT cùng có khái niệm waitpoint).
3. Lỗi VALIDATION (cấu hình sai, chưa chạy) và lỗi THỰC THI (chạy rồi mới lỗi) là hai icon khác nhau
   trong cùng node — đáng chép để người dùng không nhầm "chưa cấu hình xong" với "đã chạy và hỏng".

## 7. n8n — Template/onboarding UX

n8n docs gom onboarding thành một mục riêng **"Ways of building workflows"** liệt kê 5 con đường —
KHÔNG chỉ template tĩnh, mà cả AI-assisted:
1. **n8n Assistant** (preview) — chat agent trong app tự PLAN, BUILD, TEST workflow từ ngôn ngữ tự
   nhiên, trong đúng project người dùng chọn, và có thể sửa lỗi luôn; kết quả là một workflow BÌNH
   THƯỜNG (mở/sửa/test/publish như tự tay làm) — không phải một "bản demo" tách biệt.
2. **n8n MCP server** — build/run workflow từ MCP client ngoài (Claude Desktop/Claude Code).
3. **Templates** — khi tạo workflow mới, chọn giữa canvas rỗng hoặc template có sẵn; bấm **Templates**
   mở thư viện (mặc định điều hướng ra trang Workflows trên n8n.io; tổ chức có thể tự host thư viện
   riêng để search/browse ngay trong app). Import một template = kéo cả cấu hình vào, chỉ cần điền lại
   credential.
4. **Ask n8n AI** — trợ lý AI TRONG editor để build/debug/tối ưu workflow đang mở (khác n8n Assistant ở
   chỗ đây là hỗ trợ tại chỗ, không phải chat riêng tạo workflow từ đầu).
5. **Chat Hub** — chat với nhiều model AI + agent n8n từ một giao diện.

Với người mới hoàn toàn chưa dùng n8n: workflow rỗng đầu tiên bắt đầu bằng nút **Add first step** →
nodes panel chỉ hiện TRIGGER category (mục 2) — ép người dùng luôn bắt đầu đúng thứ tự (trigger trước,
action sau) ngay từ cú click đầu tiên, không cho chọn sai loại node trước.

Nguồn: [Ways of building workflows](https://docs.n8n.io/build/ways-of-building-workflows/README.md),
[Use n8n Assistant](https://docs.n8n.io/build/ways-of-building-workflows/n8n-assistant.md),
[Use templates](https://docs.n8n.io/build/ways-of-building-workflows/use-templates.md).

**Bài học cho LTT:**
1. n8n coi "AI tự build workflow từ chat" và "workflow tự tay kéo-thả" là HAI lối vào CÙNG một đối
   tượng dữ liệu (workflow bình thường) — không tách thành hai hệ song song. Nếu LTT làm Agent/Canvas
   có trợ lý AI dựng flow, nên theo đúng nguyên tắc này: AI sinh ra đúng định dạng canvas thật, người
   dùng mở lên sửa tay được ngay, không phải "export" hay "convert" từ định dạng khác.
2. Ép panel chỉ hiện Trigger khi workflow còn rỗng là một rào chắn onboarding rẻ tiền nhưng hiệu quả
   (loại bỏ toàn bộ lớp lỗi "workflow không có trigger" ngay từ đầu) — đáng áp dụng cho canvas LTT.
3. Cho tổ chức tự host thư viện template riêng (thay vì bắt buộc ra trang public) là chi tiết đáng cân
   nhắc nếu khách LTT muốn giữ template nội bộ không public.

## 8. Activepieces — Builder layout

Flow Builder gồm 5 mảng: **Canvas** (khung chính, đồ thị dọc — trigger trên cùng, action nối tiếp
xuống dưới, KHÔNG phải đồ thị tự do như n8n — khớp với audit cũ `04_ACTIVEPIECES_AUDIT.md` §1 "không
phải đồ thị"), **Step Panel** (mở khi CLICK vào một step trên canvas — đây chính là câu trả lời cho
câu hỏi "right drawer?": ĐÚNG, là một panel/drawer bên phải, không phải modal che canvas), **Pieces
Sidebar** (duyệt/tìm trong hơn 680 piece có sẵn), **Test Panel**, và tab **Runs** (lịch sử thực thi).

**Phân biệt trigger vs action bằng VỊ TRÍ + luồng thêm khác nhau**, không phải icon khác nhau:
- Trigger LUÔN ở đầu chuỗi (node đầu tiên trên canvas); khi thêm trigger, Piece Picker cho chọn 3
  loại: **Schedule** (đặt cron), **Webhook** (sinh URL duy nhất, gọi HTTP vào đó để chạy),
  hoặc **App Trigger** (chọn một piece rồi chọn sự kiện của nó).
- Action luôn nối TIẾP SAU trigger hoặc action khác, thêm qua nút "Add" dưới step trước đó, mở Pieces
  Sidebar lọc theo action mà piece hỗ trợ.
- Bản thân piece picker (Launch Week I) cho **xem trước trigger/action của một piece TRƯỚC khi thêm
  vào flow** — tránh việc phải thêm/test/xoá piece nhiều lần chỉ để biết nó có hành động cần dùng hay
  không (cải tiến so với version cũ, theo blog chính thức).

Nguồn: [Passing Data](https://www.activepieces.com/docs/flows/passing-data),
[Launch Week I Day 1 — piece selector](https://www.activepieces.com/blog/piece-selector),
DeepWiki [Core Concepts](https://deepwiki.com/activepieces/activepieces/1.1-core-concepts).
(Mô hình đồ thị/thi hành tuần tự chi tiết xem `04_ACTIVEPIECES_AUDIT.md` §1-2, KHÔNG lặp ở đây.)

**Bài học cho LTT:**
1. Step Panel là DRAWER bên phải, không che canvas — người dùng vẫn thấy vị trí step trong flow khi
   đang sửa tham số. Nếu LTT vẫn dùng modal full-screen cho cấu hình node, đây là điểm đáng cân nhắc
   đổi để giữ ngữ cảnh vị trí trong đồ thị.
2. Cho xem trước trigger/action của một piece TRƯỚC KHI thêm vào flow (thay vì thêm rồi mới biết) là
   pattern giảm số lần thử-sai đáng chép cho node/tool picker của LTT.

## 9. Activepieces — Connections/credentials UX

> Đây là câu quan trọng nhất theo yêu cầu đề bài — trả lời bằng cách đọc trực tiếp component nguồn
> (không chỉ docs): `packages/web/src/app/builder/step-settings/piece-settings/connection-select.tsx`,
> `packages/web/src/app/connections/create-edit-connection-dialog.tsx`,
> `packages/web/src/app/connections/oauth2-connection-settings.tsx` (activepieces/activepieces).

### 9.1 Vị trí trong điều hướng

Connections có trang riêng ở cấp PROJECT (route `connections`, liệt kê trong
`packages/web/src/app/routes/project-routes.tsx`, component `AppConnectionsPage`) — nghĩa là danh sách
connection KHÔNG nằm trong một step nào cụ thể, mà là tài nguyên dùng chung của cả project, các step
chỉ THAM CHIẾU tới nó. Một connection còn có SCOPE: `PROJECT` (mặc định, chỉ project đó dùng) hoặc
`PLATFORM` (connection "global", dùng chung nhiều project — chỉ platform-admin tạo được).

### 9.2 Cách một step CHỌN connection

Field `auth` của một piece (action/trigger có `piece.auth`) render bằng component `ConnectionSelect`
— một dropdown `Select` (không phải input tay):
- Mỗi dòng trong dropdown hiện: icon 🔑 nếu connection lấy secret từ secret manager ngoài, icon 🌐
  nếu là connection PLATFORM (global), tên hiển thị (`displayName`), một "account identifier" căn
  phải (vd. email/tên tài khoản đã kết nối) để phân biệt hai connection cùng loại piece, và một trạng
  thái nhỏ bên phải nếu connection đó KHÔNG active: ✓ xanh "Connected", ✗ đỏ "Error", hoặc icon phích
  cắm rời "Missing".
- Khi ĐÃ chọn một connection và nó không ở trạng thái `ACTIVE`, ô Select hiện icon trạng thái + nút
  **Reconnect** (icon dây cáp) NGAY TRÊN ô, không cần mở dropdown — sửa lỗi kết nối tại chỗ.
- **Dòng ĐẦU TIÊN trong dropdown luôn là hành động "+ Create Connection"** (icon dấu cộng, màu
  primary) — đây chính là "tạo connection MỚI ngay từ trong step" mà đề bài hỏi: không cần rời step,
  không cần mở trang Connections riêng. Nếu người dùng không có quyền `WRITE_APP_CONNECTION`, mục này
  vẫn hiện nhưng bị khoá kèm tooltip "Permission needed" (không ẩn hẳn — cho biết tính năng tồn tại
  nhưng thiếu quyền, thay vì im lặng).
- Bấm "+ Create Connection" mở `CreateOrEditConnectionDialog` — cùng dialog dùng để RECONNECT (khi
  reconnect, dialog nhớ đúng `pieceVersion` cũ và khoá `scope=PLATFORM` nếu connection cũ là global;
  tạo MỚI từ một step luôn mặc định `scope=PROJECT` — mã nguồn có comment giải thích đây là một
  fix cho bug GIT-1587: nếu không ép PROJECT, connection mới sẽ "thừa kế" lộn xộn scope của connection
  đang chọn và user không phải admin sẽ gọi nhầm vào API chỉ dành cho platform-admin).

### 9.3 Tạo connection mới — các LOẠI xác thực

Dialog tạo connection nhận diện qua `PieceAuthProperty` của piece và render đúng form con: OAuth2
(`OAuth2ConnectionSettings`), OIDC (`OIDCConnectionSettings`), Basic Auth
(`BasicAuthConnectionSettings`), Custom Auth nhiều field (`CustomAuthConnectionSettings`), hoặc chỉ một
ô Secret Text (`SecretTextConnectionSettings`). Nếu một piece hỗ trợ NHIỀU phương thức xác thực,
`MultiAuthList`/`AuthListItem` hiện danh sách chọn trước, có nút "Try another method" để quay lại chọn
lại giữa chừng — không phải cam kết một phương thức ngay từ đầu.

### 9.4 OAuth trình bày thế nào

- **Ba loại OAuth2** phân biệt bằng `oauth2App.oauth2Type`:
  - `CLOUD` — Activepieces (bản Cloud) đã đăng ký sẵn OAuth app của chính họ cho piece đó; người dùng
    KHÔNG cần Client ID/Secret, chỉ bấm nút Connect.
  - `OAUTH2` (self-managed/self-hosted mặc định) — người dùng phải tự đăng ký OAuth app phía nhà cung
    cấp (Google, Slack, …) rồi dán **Client ID** và **Client Secret** vào hai ô riêng (`SecretInput`,
    ô secret ẩn dạng password) NGAY TRONG dialog này — form hiện thêm một ô **Redirect URL** chỉ-đọc
    (disabled input) để người dùng copy sang cấu hình OAuth app phía nhà cung cấp.
  - `PLATFORM` — platform-admin cấu hình MỘT bộ Client ID/Secret dùng chung cho toàn platform (nhiều
    project không phải nhập lại).
- **Chọn phạm vi quyền (scope)**: nếu piece khai nhiều OAuth scope, hiện một mục "Permissions" dạng
  accordion (bấm để mở) chứa `MultiSelect` có ô tìm kiếm + nút "Select All" — mặc định GẤP LẠI để
  không doạ người dùng bằng danh sách quyền dài ngay khi mở dialog.
- **Nút Connect**: hiện logo + tên piece, một nút bên phải — nhãn đổi state (disabled khi thiếu
  Client ID/Secret hợp lệ hoặc chưa chọn scope bắt buộc; đổi màu "destructive" sau khi đã có `code` để
  báo đã kết nối, bấm lại để làm lại). Bấm nút mở **POPUP window** (`openOAuth2Popup`,
  `window.open`-based) chạy authorization-code flow — KHÔNG redirect cả trang (giữ nguyên form/dialog
  phía sau popup, không mất state đang nhập nếu OAuth thất bại).

### 9.5 Sau khi tạo xong

`setOpen(false, connection)` trả kết quả về `ConnectionSelect`, gọi `refetch()` danh sách connection và
tự gán `field.onChange` — connection mới chọn sẵn cho step luôn, người dùng không cần tự tìm lại nó
trong dropdown.

Nguồn: activepieces/activepieces `packages/web/src/app/builder/step-settings/piece-settings/
connection-select.tsx`, `packages/web/src/app/connections/create-edit-connection-dialog.tsx`,
`packages/web/src/app/connections/oauth2-connection-settings.tsx`,
[Predefined Connection](https://www.activepieces.com/docs/embedding/predefined-connection),
[Create/Update Connections (embed)](https://www.activepieces.com/docs/embedding/embed-connections).

**Bài học cho LTT:**
1. **Tạo connection/credential NGAY TỪ DROPDOWN của field auth** (mục đầu danh sách, không phải nút
   riêng ở nơi khác) là pattern trực tiếp trả lời "làm sao map connection không rời khỏi context đang
   cấu hình step" — LTT nên chép nguyên luồng này cho API key/OAuth của node AI/tool.
2. Ba loại OAuth (CLOUD dùng app chung / self-managed nhập Client ID+Secret / PLATFORM dùng chung toàn
   nền tảng) là mô hình phân tầng đáng học: LTT SaaS đa người dùng có thể áp except CLOUD→"LTT quản lý"
   mặc định, cho phép khách nâng cao tự mang OAuth app riêng khi cần (self-managed), và một cấu hình
   dùng chung ở cấp platform cho các app nội bộ LTT hay dùng.
3. Popup thay vì redirect toàn trang giữ nguyên state form đang nhập — tránh mất dữ liệu người dùng đã
   gõ nếu OAuth thất bại giữa chừng; đáng áp dụng bất cứ đâu LTT có OAuth trong một dialog/step config.
4. Ẩn nhưng khoá (không xoá hẳn) mục "Create Connection" kèm tooltip "Permission needed" khi thiếu
   quyền — cho người dùng BIẾT tính năng tồn tại thay vì im lặng — là chi tiết UX nhỏ nhưng giảm ticket
   hỗ trợ "sao tôi không thấy nút tạo connection".

## 10. Activepieces — "Test step" / "Test trigger" UX

**Bắt buộc test tuần tự, không cho nhảy cóc**: docs nêu rõ "we require you to test each step you add
before moving to the next step" — lý do KỸ THUẬT (không phải chỉ khuyến nghị): bước sau chỉ có dữ liệu
mẫu để map nếu bước trước ĐÃ có run data (test hoặc production). Step chưa có dữ liệu hiện chỉ báo
**"Test me"** ngay trên step.

**4 cách tạo dữ liệu mẫu**, khác nhau theo loại step (nguồn:
[Passing Data](https://www.activepieces.com/docs/flows/passing-data)):
- **Load Data** (một số trigger) — kéo thẳng dữ liệu có sẵn từ tài khoản đã kết nối, KHÔNG cần người
  dùng tự tạo sự kiện thật (vd. lấy vài email mới nhất từ Gmail để làm mẫu).
- **Test Trigger** (một số trigger khác) — bắt người dùng ra ứng dụng ngoài, tự bấm/gõ để sinh sự kiện
  thật, Activepieces lắng nghe rồi bắt lại.
- **Send Data** (Webhook) — gửi một request mẫu tới URL webhook do Activepieces sinh ra.
- **Test Action** — chạy THẬT action đó (gọi API thật) để lấy output mẫu.
- **Mock Data** (một số trigger) — dữ liệu mẫu TĨNH do chính piece định nghĩa sẵn, không cần chạm vào
  tài khoản/dịch vụ ngoài (hữu ích khi build offline hoặc piece chưa có tài khoản test).

**Dùng sample data để map bước sau — "Data to Insert Panel"**: khi người dùng click/focus vào một ô
tham số ở step sau, panel này tự bật lên, liệt kê các step PHÍA TRƯỚC có thể truy cập được kèm dữ liệu
mẫu của chúng; field có mũi tên `›` mở rộng được để xem field con lồng nhau; bấm trực tiếp vào một mục
(cha hoặc con) để CHÈN nó vào ô đang focus — tương tự cơ chế Schema-kéo-thả của n8n (mục 3) nhưng ở
đây là CLICK-để-chèn thay vì kéo-thả, và panel tự xuất hiện theo FOCUS thay vì luôn hiện cố định một
cột riêng.

Nguồn: [Passing Data](https://www.activepieces.com/docs/flows/passing-data),
[PR #15787 — fix trigger test drawer dismiss](https://github.com/activepieces/activepieces/pull/15787),
[Issue #15473 — Test Trigger drawer bug](https://github.com/activepieces/activepieces/issues/15473).

**Bài học cho LTT:**
1. Ép TEST TUẦN TỰ trước khi cho cấu hình bước sau (thay vì cho cấu hình xong toàn bộ rồi mới chạy thử
   một lần) là cách Activepieces đảm bảo LUÔN có dữ liệu mẫu để map — LTT nên cân nhắc rào chắn tương
   tự cho Agent/Canvas nếu tính năng map dữ liệu phụ thuộc vào run data.
2. Bốn cách lấy sample data (Load/Test/Send/Mock) cho thấy KHÔNG có một cách "test" chung cho mọi loại
   trigger — thiết kế "test button" của LTT nên phân theo LOẠI trigger/action tương tự, đặc biệt Mock
   Data (không chạm dịch vụ ngoài) đáng có cho node tốn credit/API-key để dev không mất tiền lúc build.
3. Panel map dữ liệu tự bật theo FOCUS (không chiếm chỗ cố định khi không cần) là lựa chọn tiết kiệm
   không gian màn hình so với 3-cột cố định của n8n — đáng cân nhắc cho layout hẹp/mobile của LTT.

## 11. Activepieces — Terminology

Từ dev/mã nguồn vẫn giữ nguyên trên UI phần lớn (`Flow`, `Piece`, `Step`, `Connection`, `Run` đều xuất
hiện trực tiếp trong nhãn UI: "Create Connection", tab "Runs", "Flow Builder") — Activepieces KHÔNG che
giấu từ kỹ thuật bằng một lớp từ khác như một số SaaS no-code khác. Điểm khác biệt thật sự nằm ở
COPY GIẢI THÍCH đi kèm, không phải đổi danh từ:

- **"Piece"** vẫn là từ chính thức cả trong code lẫn UI ("Explore Pieces", piece picker) — marketing
  site đôi khi dùng "integrations" cho SEO/người ngoài (vd. trang `activepieces.com/pieces` ghi "687
  open-source pieces"), nhưng TRONG builder luôn gọi là "Piece".
- **Trigger/Action** không đổi tên, nhưng copy giải thích được viết lại theo hướng NGÔN NGỮ THAO TÁC cụ
  thể thay vì mô tả trừu tượng — bằng chứng trực tiếp từ PR
  [#15405](https://github.com/activepieces/activepieces/pull/15405) (đổi copy cho Manual Trigger):
  - Trước: "Manually start your own flow without any extra configurations" (mô tả CHỨC NĂNG chung
    chung).
  - Sau: "Start the flow on demand with the Run Flow button" (trỏ thẳng vào NÚT cụ thể người dùng sẽ
    bấm) + thêm một dòng nói rõ hệ quả dữ liệu: "This trigger passes no data, so later steps have
    nothing to map from it." — chủ động cảnh báo trước một nhầm lẫn thường gặp (tưởng map được dữ liệu
    từ manual trigger) ngay tại nơi người dùng đang đứng, thay vì để họ tự phát hiện lỗi rồi tra cứu.
- **Nút chạy thủ công gọi là "Run Flow"** (không phải "Execute"/"Trigger") — nhất quán với "Run" là từ
  người dùng thấy trong tab lịch sử ("Runs") và trong copy hướng dẫn.
- **"Connection"** dùng cho cả UI lẫn API (`AppConnection` là tên dev, nhưng UI luôn hiện "Connection" —
  không có từ nào khác như "credential" hay "account" xuất hiện làm nhãn chính, dù đôi khi copy phụ có
  chữ "account" khi nói về tài khoản bên thứ ba đã kết nối, vd. "connected account").

Nguồn: [PR #15405](https://github.com/activepieces/activepieces/pull/15405),
[Launch Week I — piece selector](https://www.activepieces.com/blog/piece-selector),
`connection-select.tsx` (mục 9).

**Bài học cho LTT:**
1. Bài học chính KHÔNG phải "đổi tên gọi" mà là **viết copy trỏ vào ĐÚNG nút/hành động cụ thể** thay vì
   mô tả trừu tượng, và **chủ động nói trước hệ quả dữ liệu** ("bước này không có gì để map") ngay tại
   điểm người dùng dễ hiểu nhầm nhất — LTT nên áp dụng cách viết micro-copy này cho các node/trigger dễ
   gây hiểu lầm tương tự (vd. trigger không có payload, node webhook không có output mẫu).
2. Giữ nguyên thuật ngữ kỹ thuật khi nó đã đủ trực quan (Piece/Step/Flow/Run) thay vì sáng tạo từ mới
   để "thân thiện hoá" — tránh việc tài liệu, API, và UI dùng ba bộ từ khác nhau cho cùng một khái
   niệm (rủi ro mà LTT nên tránh khi đặt tên cho Agent/Canvas/Workflow).

## 12. Giấy phép — PORT hay chỉ ADAPT

### n8n — Sustainable Use License (⛔ KHÔNG PORT code)

Nguyên văn từ `LICENSE.md` gốc n8n-io/n8n (đã xác nhận lại y hệt `32_AUDIT_2026-09-22_benchmark.md`
§1.6 — không lặp phân tích, chỉ trích dẫn lại phần ràng buộc UI/UX cần nhớ khi làm việc này):

> "You may use or modify the software only for your own internal business purposes or for
> non-commercial or personal use. You may distribute the software or provide it to others only if you
> do so free of charge for non-commercial purposes."

LTT là SaaS bán credit — **mục đích thương mại, có tính phí** — nên KHÔNG được copy bất kỳ dòng mã
frontend nào của n8n (`packages/frontend/editor-ui/*`) kể cả một component UI nhỏ như
`CanvasEdgeToolbar.vue` hay `MappingPill.vue`. Chỉ được: (a) mô tả HÀNH VI/ý tưởng bằng lời (đã làm ở
mục 1-7), (b) tự viết lại từ đầu theo ý tưởng đó. Riêng file có `.ee.` trong tên/thư mục còn bị khoá
chặt hơn nữa (cần n8n Enterprise License) — nhưng phần UI/UX khảo sát ở tài liệu này (canvas, NDV,
node creator, execution UX) đều nằm NGOÀI `.ee.`, tức là ĐỌC được (mã nguồn mở public) nhưng vẫn không
PORT được vì lý do thương mại ở trên.

### Activepieces — MIT ngoài `packages/ee/` (✅ PORT được phần MIT)

Nguyên văn `LICENSE` gốc activepieces/activepieces:

> "All content that resides under the 'packages/ee/' and 'packages/server/api/src/app/ee' directory
> of this repository [...] is licensed under the license defined in packages/ee/LICENSE [...] Content
> outside of the above mentioned directories or restrictions above is available under the 'MIT Expat'
> license."

Toàn bộ mã UI/UX khảo sát ở mục 8-11 (`packages/web/src/app/connections/*`,
`packages/web/src/app/builder/step-settings/piece-settings/connection-select.tsx`) nằm NGOÀI
`packages/ee/` → **MIT, PORT được** (chép nguyên component, sửa theo LTT, chỉ cần giữ notice bản quyền
MIT). `packages/ee/LICENSE` (Activepieces Enterprise License) cấm merge/publish/distribute/sublicense
nếu không có Enterprise subscription hợp lệ — nhưng KHÔNG chặn dùng cho dev/test nội bộ ("you may copy
and modify the Software for development and testing purposes, without requiring a subscription"); mảng
`ee/` chủ yếu là tính năng doanh nghiệp (SSO, audit log, license-key), không phải phần UI builder/
connections khảo sát ở đây.

### Kết luận thực dụng cho LTT

| | n8n | Activepieces |
|---|---|---|
| Đọc mã để lấy Ý TƯỞNG | ✅ được (public repo) | ✅ được |
| PORT nguyên component/file | ⛔ không (Sustainable Use License chặn SaaS thương mại) | ✅ được cho phần MIT (`packages/web` ngoài `ee/`) |
| Vùng bị khoá thêm | file `.ee.*` (Enterprise License) | thư mục `packages/ee/` (Enterprise License, không tính phần UI đã khảo sát) |

→ Mọi "Bài học cho LTT" ở mục 1-7 (n8n) chỉ được hiện thực bằng cách TỰ VIẾT LẠI theo ý tưởng; mục 8-11
(Activepieces) có thể cân nhắc PORT trực tiếp component `connection-select.tsx`/dialog OAuth làm điểm
khởi đầu, miễn giữ giấy phép MIT gốc trong file chép sang.

Nguồn: n8n-io/n8n `LICENSE.md` (root), activepieces/activepieces `LICENSE` (root) và `packages/ee/LICENSE`.

**Bài học cho LTT:** (kết luận pháp lý, không phải pattern kỹ thuật — xem bảng trên)

## Bảng chấm 0-5

Thang: 0 = không có/rất kém, 5 = xuất sắc, dựa trên bằng chứng đã trích ở mục 1-11 (không chấm phần
runtime/engine — xem audit cũ cho điểm đó).

| Tiêu chí | n8n | Activepieces | Ghi chú |
|---|---|---|---|
| Canvas interaction | 4 | 2 | n8n: Vue Flow + Canvas Groups + edge-toolbar chèn giữa cạnh + animated status border. Activepieces: canvas chỉ là danh sách dọc render tuyến tính (đã xác nhận ở audit cũ "không phải đồ thị"), không có group/sticky/minimap tương đương. |
| Node discovery/search | 5 | 3 | n8n: taxonomy AI riêng 15 category con + panel đổi theo ngữ cảnh (trigger-only lúc đầu). Activepieces: search + category phẳng hơn, có preview trigger/action trước khi thêm (điểm cộng) nhưng không có tầng phân loại sâu như n8n. |
| Data mapping UX | 5 | 3 | n8n: Schema view mặc định kéo-thả sinh expression, đổi màu pill khi hợp lệ. Activepieces: "Data to Insert Panel" click-để-chèn theo focus, không kéo-thả, không đổi màu theo tính hợp lệ. Cả hai đều "không gõ syntax" được — n8n phong phú hơn ở chế độ xem (Table/JSON/Schema/Binary) và độ trực quan kéo-thả. |
| Per-step config UX | 4 | 4 | n8n: NDV 3 cột cố định, mạnh khi cần xem input/output cùng lúc. Activepieces: Step Panel drawer bên phải, nhẹ hơn, có preview trigger/action trước khi thêm — hai triết lý khác nhau, không hẳn bên nào vượt trội toàn diện. |
| Connections UX | 3 | 5 | Activepieces vượt trội rõ rệt: tạo connection NGAY TỪ dropdown auth field, 3 tầng OAuth (CLOUD/self-managed/PLATFORM), popup không mất state, badge trạng thái + nút Reconnect tại chỗ. n8n để credential là một trang riêng tách khỏi NDV (theo `32_AUDIT...` §1.2, không khảo sát sâu UI ở đây vì đã có ở audit cũ) — không có bằng chứng về luồng tạo-inline tương đương trong khảo sát này. |
| Execution debugging UX | 5 | 3 | n8n: dirty-node (stale-data warning độc đáo), partial execution, retry 2 chế độ, executions list lọc mạnh. Activepieces: 4 kiểu tạo sample data (Load/Test/Send/Mock) tốt cho việc TEST, nhưng không thấy khái niệm tương đương "dirty node" hay "retry with original/current workflow" trong khảo sát này. |
| Onboarding/templates | 5 | 3 | n8n: 5 con đường (Assistant/MCP server/Templates/Ask AI/Chat Hub) đều tạo ra workflow THẬT, dùng lại được. Activepieces: có piece picker cải tiến (xem trước trước khi thêm) giúp học nhanh hơn, nhưng KHÔNG XÁC MINH ĐƯỢC trong khảo sát này liệu có tương đương "AI Assistant tự build flow" như n8n Assistant (ngoài phạm vi câu hỏi đề bài, không đào sâu). |

**Tổng quan 1 dòng**: n8n mạnh hơn rõ rệt ở canvas/node-discovery/data-mapping/execution-debugging/
onboarding; Activepieces mạnh hơn rõ rệt duy nhất — nhưng RẤT rõ — ở connections/credentials UX, đúng
như đề bài đã dự đoán khi yêu cầu đào sâu câu hỏi 9.

## Giới hạn của khảo sát này

- **Không mở app thật trong trình duyệt** — toàn bộ khảo sát dựa trên đọc mã nguồn (GitHub qua `gh`
  CLI, không có quyền dùng GitHub MCP plugin trong phiên này nên chuyển sang `gh api`/`gh search`) và
  đọc docs chính thức (WebSearch/WebFetch). Một số hành vi UI runtime (animation cụ thể, độ trễ, thứ tự
  focus chính xác) suy ra từ tên class/biến trong mã, KHÔNG quan sát trực tiếp bằng mắt trên UI đang
  chạy — có rủi ro mã đã đổi giữa lúc đọc và lúc UI thực chạy, hoặc một behavior chỉ lộ ra khi tương
  tác thật (vd. thứ tự animation, timing của popup OAuth).
- **`docs.n8n.io` đã tái cấu trúc URL** (nhiều đường dẫn cũ trong đề bài như
  `workflows/components/nodes` trả về 404) — phải dò lại đường dẫn mới qua GitHub search trên
  `n8n-io/n8n-docs`; một vài trang rất mới/rất hẹp có thể chưa được index nên bỏ sót.
- **Minimap và alignment/helper-lines của n8n**: KHÔNG XÁC MINH ĐƯỢC có tồn tại hay không — không tìm
  thấy trong docs chính thức lẫn keyboard-shortcuts page; không đọc sâu tới mức component canvas
  container (`Canvas.vue`) để xác nhận trực tiếp trong mã do giới hạn thời gian của khảo sát UI-only.
- **n8n credential UX (trang riêng, không phải NDV)**: KHÔNG đào sâu ở tài liệu này vì đã có ở
  `32_AUDIT_2026-09-22_benchmark.md` §1.2 (mã hoá hai tầng) — tài liệu đó cũng là engine-focused, nên
  vẫn còn một khoảng trống UI-only cho luồng credential CỦA N8N (đối lập với Activepieces connections đã
  đào sâu ở mục 9) — nếu cần so sánh cân bằng hơn, nên khảo sát bổ sung UI trang Credentials của n8n.
  Activepieces theo đúng đề bài (câu 9), n8n theo đúng đề bài (không hỏi credentials UI, chỉ hỏi NDV/
  expression/execution/canvas) — nên đây là bất cân xứng CÓ CHỦ Ý theo yêu cầu, không phải thiếu sót.
- **Activepieces "AI Assistant tự build flow"**: không nằm trong 12 câu hỏi được giao nên không tra —
  nếu LTT muốn so sánh onboarding AI-assisted của cả hai công cụ cần một lượt khảo sát riêng.
- **Chưa test trên tài khoản thật** (n8n Cloud / Activepieces Cloud hay self-host) — không có ảnh chụp
  màn hình hay video, chỉ có mã nguồn + docs + một PR/issue làm bằng chứng phụ trợ (vd. PR #38577, PR
  #15405, PR #15787) — độ tin cậy các phần này ở mức "xác nhận qua mã", không phải "quan sát trực tiếp".
- **Phiên bản mã**: đọc tại HEAD của `n8n-io/n8n` và `activepieces/activepieces` tại thời điểm khảo sát
  (2026-09-27), không ghim theo một tag/release cụ thể — hai repo đổi rất nhanh nên số liệu (vd. số
  piece "687+", số category AI) có thể lệch vài tuần sau.
