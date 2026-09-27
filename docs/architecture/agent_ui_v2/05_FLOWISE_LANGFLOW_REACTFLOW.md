# Flowise + Langflow + React Flow — UI/UX benchmark (2026-09-27)

## Quan hệ với audit cũ

`docs/architecture/workflow_v2_audit/32_AUDIT_2026-09-22_benchmark.md` §2 (Flowise, dòng 165–306)
và §3 (Langflow, dòng 308–478) đã khảo sát **runtime semantics**: `$flow.state`, cơ chế Human Input
(ghi DB rồi đợi lượt gọi API mới ở Flowise, so với `CycleEdge`/checkpoint bền vững ở Langflow),
kiểm tra cạnh theo kiểu lúc dựng đồ thị, `ExecuteFlow`/"Flow as Tool", và giấy phép (Apache-2.0 /
MIT). Tài liệu đó **không** khảo sát lớp giao diện — cách node được vẽ, cách người dùng cấu hình
một trường, cách trình sinh flow bằng AI trình bày kết quả, cách panel thực thi bố trí trên màn
hình. Tài liệu này chỉ trả lời phần UI/UX đó, và bổ sung một khảo sát mới hoàn toàn về React Flow/
xyflow — framework LTT đang dùng thật ở `frontend/agent-canvas/`.

## 1. Flowise AgentFlow v2 — Node editor UX

Nguồn: `FlowiseAI/Flowise` (repo trạng thái **archived** tại thời điểm khảo sát 2026-09-27 — xem
`gh api repos/FlowiseAI/Flowise --jq .archived` → `true`; không rõ khi nào bị archive, không ảnh
hưởng việc code vẫn đọc được). Đây là gói UI **mới**, `packages/agentflow/` (TypeScript, kiến trúc
`atoms/`/`features/`/`core/`/`infrastructure/`), khác hẳn `packages/ui/src` (JSX cũ) mà audit
22/09 nhiều khả năng đã xem — bản thân đây đã là một phát hiện: Flowise đang viết lại UI AgentFlow
v2 bằng một gói riêng, có test Jest cho gần như mọi component.

**Node card anatomy** (`packages/agentflow/src/features/canvas/containers/AgentFlowNode.tsx`):
card MUI (`CardWrapper`) rộng cố định, bố cục ngang: icon 50px bên trái, nhãn (`data.label`) +
tóm tắt cấu hình model (`NodeModelConfigs`) + icon công cụ (`NodeToolIcons`) bên phải; `Handle`
input ở mép trái (`NodeInputHandle`, có thể ẩn qua `data.hideInput`), các `Handle` output ở mép
phải được sinh động theo `outputAnchors.length` (`NodeOutputHandles`, quyết định luôn chiều cao
tối thiểu của card qua `getMinimumNodeHeight`). Hai badge nổi tuyệt đối ở góc: trạng thái thực thi
(tròn, góc phải-trên, màu theo `ExecutionStatus` — xanh `FINISHED`, cam xoay `INPROGRESS`, đỏ
`ERROR`/`STOPPED`/`WAITING_FOR_INPUT`) và cảnh báo (góc trái-trên, icon chấm than cam, tooltip liệt
kê cảnh báo phiên bản node + lỗi validate). Viền card đổi màu/độ dày khi có lỗi validate
(`hasValidationErrors`).

**Cấu hình: side dialog, không inline** — double-click vào node hoặc bấm icon "Edit" trên
`NodeToolbarActions` (toolbar nổi phía trên node, dùng `NodeToolbar` của React Flow, chỉ hiện khi
`selected || isHovered`, có 4 nút: Duplicate/Edit/Delete/Info) đều gọi `openNodeEditor(nodeId)`,
mở `EditNodeDialog` — một MUI `Dialog` (modal, `maxWidth='sm'`) render TOÀN BỘ danh sách
`inputParams` của node bằng `NodeInputHandler` (`packages/agentflow/src/features/node-editor/
EditNodeDialog.tsx`). Trên node KHÔNG có input nào chỉnh trực tiếp ngoại trừ double-click để mở
dialog và sửa tên node qua icon bút chì cạnh tiêu đề dialog (không phải trên canvas). Icon "Info"
mở một dialog thứ hai riêng, `NodeInfoDialog.tsx` — hiển thị icon/badge (id, version, badge
DEPRECATING…)/mô tả/link tài liệu và một bảng cấu hình (tên/kiểu/override) chỉ đọc, tách biệt hẳn
khỏi dialog sửa.

**Resize/collapse**: node thường (`AgentFlowNode`) có kích thước **cố định theo nội dung**
(`minHeight` tính từ số lượng output anchor), không kéo giãn tay được. Riêng node Iteration
(`IterationNode.tsx`) LÀ container co giãn được: dùng `NodeResizer` (React Flow, `minWidth={300}`,
`minHeight` tính động) + `NodeToolbar` cố định hiển thị nhãn ở góc trên — đúng hai API mà bảng
kiểm kê React Flow (§12) ghi nhận LTT **chưa dùng**. Không có "collapse" (thu gọn nội dung node)
ở bất kỳ loại node nào được khảo sát.

**Bài học cho LTT:** (1) tách "sửa cấu hình" (dialog riêng, toàn bộ field) khỏi "xem thông tin"
(dialog info chỉ đọc) là một ranh giới UX rõ ràng LTT có thể học — tránh nhồi cả hai vào một
popup; (2) `NodeToolbar` (hiện khi hover/selected, 3-4 nút hành động nhanh) là mẫu rẻ, khớp đúng
khoảng trống P1 đã ghi ở §12; (3) `NodeResizer` cho riêng loại node "container" (iteration/group)
— khớp ý tưởng sub-flow (`parentId`/`extent:'parent'`) đã đề xuất P1 ở §12, Flowise là bằng chứng
sống rằng cặp API này ghép được với nhau trong thực tế.

## 2. Flowise AgentFlow v2 — AI flow generation ("Generate Agentflow")

Nguồn: `packages/agentflow/src/features/generator/GenerateFlowDialog.tsx`,
`packages/server/src/services/agentflowv2-generator/{index.ts,prompt.ts}`,
`packages/components/src/agentflowv2Generator.ts` (repo `FlowiseAI/Flowise`, đọc trực tiếp qua
GitHub Contents API — API `search/code` của GitHub trả `total_count:0` liên tục trong lượt khảo
sát này kể cả trên repo đối chứng `facebook/react`, nên phần khảo sát này dùng `git/trees?recursive=1`
+ đọc từng tệp thay vì tìm-theo-từ-khoá).

- **Người dùng gõ gì**: một ô văn bản nhiều dòng (`OutlinedInput multiline rows={8}`, placeholder
  "Describe your agent here") + bắt buộc chọn 1 chat model từ dropdown nạp động
  (`chatflowsApi.getChatModels()`). Có sẵn **gợi ý nhanh dạng chip** (`SuggestionChips`,
  `defaultSuggestions`) để bấm điền thẳng vào ô prompt thay vì gõ từ đầu.
- **Nhận lại gì**: gọi `chatflowsApi.generateAgentflow({question, selectedChatModel})` →
  server (`generateAgentflowv2_json` trong `flowise-components`, prompt ở `prompt.ts`) trả về
  `{nodes, edges}` (schema Zod `AgentFlowV2Type`, có thể kèm `description`/`usecases` không dùng ở
  UI). Server dựng prompt bằng cách nhét vào ba biến: `{userRequest}`, `{agentFlow2Nodes}` (danh
  sách node khả dụng, tên+nhãn+mô tả, lấy từ `nodesPool.componentNodes` đang chạy — nghĩa là LLM
  chỉ được phép chọn trong đúng tập node cài trên instance đó) và `{marketplaceTemplates}` (toàn bộ
  flow mẫu trong `marketplaces/agentflowsv2/*.json`, dùng làm ví dụ few-shot, KHÔNG phải RAG có
  chọn lọc theo độ liên quan — nạp hết thư mục).
- **Không có preview/diff**: `handleGenerate` gọi API rồi gọi thẳng `onGenerated(result.nodes,
  result.edges)` và ĐÓNG dialog ngay khi thành công — không có bước xem trước, không có diff, không
  hỏi xác nhận lần hai. Thanh tiến trình trong lúc chờ là **giả** (fake progress animation chạy theo
  bộ đếm thời gian nội bộ, tăng nhanh/chậm theo mốc cố định 30/60/80%, dừng ở 95% chờ response thật
  rồi nhảy lên 100% — không phản ánh tiến độ thật của LLM).
- **Chỉ tạo mới, không sửa flow có sẵn**: `handleFlowGenerated` (`packages/agentflow/src/
  Agentflow.tsx`) gọi thẳng `setLocalNodes(generatedNodes); setLocalEdges(generatedEdges)` —
  **THAY TOÀN BỘ** canvas hiện tại bằng kết quả sinh ra, bất kể canvas đang có gì. Prompt server
  cũng chỉ nhận `{userRequest}`, không có tham số nào truyền flow hiện tại vào làm ngữ cảnh chỉnh
  sửa — đây thuần là "sinh mới từ mô tả", không phải "sửa flow theo yêu cầu". Dòng cảnh báo trong
  UI tự thừa nhận giới hạn: "Only nodes and edges are generated, you will need to fill in the input
  fields for each node" — tức các trường cấu hình bên trong mỗi node (API key, model, prompt con…)
  đều để trống, người dùng phải tự mở từng `EditNodeDialog` mà điền tay.

**Bài học cho LTT:** (1) mất dữ liệu im lặng khi "Generate" ghi đè canvas không hỏi lại là một
anti-pattern rõ — nếu LTT làm tính năng tương tự, cần preview/diff trước khi áp, hoặc chí ít hỏi
xác nhận khi canvas không rỗng; (2) giới hạn tập node được chọn đúng bằng danh sách node cài trên
instance (không bịa tên node) là một ràng buộc prompt đáng chép; (3) progress bar giả là một mẫu
UX cần TRÁNH, không phải học theo — người dùng không biết đang ở bước nào thật; nếu LTT cần
progress cho job dài, nên có tín hiệu thật (SSE/poll trạng thái job) thay vì hoạt náo giả.

## 3. Flowise AgentFlow v2 — Variable picker / data reference UX

Nguồn: `packages/agentflow/src/atoms/{VariableInput.tsx,VariablePicker.tsx,suggestionConfig.ts}`,
`packages/agentflow/src/core/primitives/customMention.ts`,
`packages/agentflow/src/features/node-editor/useAvailableVariables.ts`.

Người dùng **không cần biết cú pháp `{{...}}`**. Có hai cơ chế song song, tuỳ loại field:

1. **Field văn bản dài (prompt, message…) → gõ inline, gợi ý theo `{{`.** `VariableInput.tsx` là
   một rich-text editor dựng trên TipTap (`@tiptap/react` + extension `Mention` tuỳ biến
   `CustomMention`). Khi người dùng gõ ký tự trigger (mặc định `{{`), một dropdown gợi ý
   (`SuggestionDropdown`, cấu hình qua `createSuggestionConfig`) hiện ngay tại vị trí con trỏ,
   liệt kê các biến khả dụng; chọn một mục chèn vào editor như một **mention chip** có style riêng
   (nền xanh nhạt, bo góc — style `.mention` trong `StyledEditorContent`) thay vì text thô, và
   editor tự render lại thành đúng cú pháp `{{tenBien}}` khi xuất ra markdown
   (`getEditorMarkdown`). Người dùng chỉ thấy "một chip có tên biến", không bao giờ phải gõ tay
   hai dấu ngoặc nhọn.
2. **Field khác (JSON editor theo từng key, hoặc field không dùng TipTap) → panel chọn dạng cây có
   nhóm.** `VariablePicker.tsx` là một popover/panel liệt kê biến theo NHÓM có tiêu đề + icon màu
   riêng từng nhóm (`Chat Context` — icon chat, `Node Outputs` — icon lịch sử, `Flow State` — icon
   cây nhị phân; nhóm lạ rơi vào `Other` với icon ghim mặc định), mỗi mục có icon + label + mô tả
   ngắn (vd "Output from <tên node>"), bấm để chèn thẳng chuỗi `value` đã có sẵn cú pháp.

**Nguồn danh sách biến** (`useAvailableVariables.ts`) gộp 4 nhóm, tính lại mỗi khi mở field:
biến hệ thống cố định (`{{question}}`, `{{chat_history}}`, `{{current_date_time}}`,
`{{runtime_messages_length}}`, `{{loop_count}}`, `{{file_attachment}}`, `{{$flow.sessionId}}`,
`{{$flow.chatId}}`, `{{$flow.chatflowId}}`); `{{$iteration}}` chỉ xuất hiện khi node đang nằm
trong một Iteration container (`extent === 'parent'`); output của MỌI node ngược dòng
(`getUpstreamNodes`, nhãn ưu tiên `chainName`/`functionName`/`variableName` rồi mới tới id thô,
kèm icon của chính node đó); và các khoá `$flow.state.<key>` được suy ra từ node `startAgentflow`
(`getDefinedStateKeys`). Danh sách này **chỉ tính theo đồ thị tĩnh** (nút nào ở ngược dòng), không
gọi API để lấy giá trị runtime thật.

**Bài học cho LTT:** (1) mention-chip trong rich-text editor (TipTap) là cách xoá hoàn toàn gánh
nặng cú pháp — người dùng thao tác với "tên biến có icon", không phải chuỗi `{{...}}`; đáng cân
nhắc nếu LTT có field prompt tự do dài; (2) với field ngắn/JSON, một popover phân nhóm theo NGUỒN
GỐC biến (ngữ cảnh chat / output node / state cờ) dễ quét hơn một danh sách phẳng; (3) suy biến khả
dụng từ chính đồ thị (ai là ngược dòng của node đang sửa) thay vì liệt kê toàn bộ biến của cả flow
là một ràng buộc đáng học — tránh gợi ý biến chưa tồn tại tại thời điểm node đó chạy.

## 4. Flowise AgentFlow v2 — Conditional / dynamic node properties

Nguồn: `packages/agentflow/src/core/utils/fieldVisibility.ts`,
`packages/agentflow/src/features/node-editor/{EditNodeDialog.tsx,ConfigInput.tsx,AsyncInput.tsx}`,
`packages/agentflow/src/infrastructure/api/hooks/useAsyncOptions.ts`.

**Show/hide (`fieldVisibility.ts` → `evaluateFieldVisibility`)**: mỗi `InputParam` có thể khai
`show`/`hide` là một object `{ tenFieldKhac: giaTriSoSanh }`. So khớp đi qua `conditionMatches`:
giá trị hiện tại của field điều kiện được ép về mảng, so với giá trị cần so sánh — nếu chuỗi so
sánh chứa ký tự có "ý định regex" (`REGEX_INTENT = /[|()^$*+?[\]]/`) thì chạy `safeRegexTest` (có
giới hạn độ dài 200 ký tự và tự phát hiện nested-quantifier để chặn ReDoS trước khi `new RegExp`),
ngược lại so khớp chuỗi thường. `EditNodeDialog` gọi `evaluateFieldVisibility` lại **mỗi lần** một
field đổi giá trị (`onCustomDataChange`) — UI cập nhật field ẩn/hiện ngay lập tức trong cùng
frame, không có hiệu ứng chờ. Giá trị mặc định của field bị ẩn vẫn được merge vào `inputs` từ lúc
mở dialog (`applyVisibleFieldDefaults`) để field khác tham chiếu tới nó qua điều kiện `show` vẫn
đánh giá đúng ngay từ lần render đầu — tránh trường hợp "field A ẩn vì field B chưa có giá trị mặc
định của nó".

**`loadMethod` (async options, `AsyncInput.tsx` + `useAsyncOptions`)**: field kiểu
`asyncOptions`/`asyncMultiOptions` render bằng MUI `Autocomplete`. Khi đang tải: ô input hiện
`CircularProgress` làm end-adornment ngay trong ô (không che khuất field, không dialog chờ riêng),
`noOptionsText` đổi thành "Loading…". Khi tải lỗi: toàn bộ dropdown bị thay bằng một dòng
`AsyncFetchError` — thông báo lỗi màu đỏ + nút **Retry** gọi lại `refetch()`, không có silent-fail.
Một số `loadMethod` đặc biệt không gọi server: `listPreviousNodes` đọc thẳng từ đồ thị hiện tại
(`getUpstreamNodes`, không round-trip mạng); các `loadMethod` cần biết giá trị field khác
(`listToolInputArgs`, `listActions`, `listTables`) chỉ gửi kèm `inputs` khi thật sự cần — có
comment giải thích rõ lý do: gửi `inputs` vô điều kiện sẽ khiến MỌI keystroke ở field anh em kích
hoạt fetch lại (do `paramsKey` đổi), nên hàm `buildAsyncParams` lọc theo tên `loadMethod` trước.
Riêng field kiểu credential còn có thêm nút bút chì "Edit Credential" cạnh dropdown và tuỳ chọn
"- Create New -" ở cuối danh sách mở dialog tạo credential ngay tại chỗ, không phải rời trang.

**Cấu hình lồng (`ConfigInput.tsx`, field `loadConfig: true`)**: khi một field kiểu chọn (vd chọn
loại "agentModel") có cấu hình con phụ thuộc vào lựa chọn đó, UI fetch định nghĩa node con
(`nodesApi.getNodeByName`) rồi render bộ field phụ trong một `Accordion` thu gọn mặc định (tiêu đề
"<Tên model> Parameters" + icon bánh răng), tự đánh giá `evaluateFieldVisibility` cho chính bộ
field con này — tức show/hide và async-loading lồng được nhiều cấp.

**Bài học cho LTT:** (1) `show`/`hide` bằng object so khớp giá trị (không phải hàm JS tuỳ ý) an
toàn hơn để serialize/lưu trữ, và việc tự thêm chặn ReDoS khi cho phép cú pháp regex là chi tiết
đáng chép nếu LTT cũng muốn field điều kiện hỗ trợ regex; (2) tách rõ 3 trạng thái loading/error/
data cho mọi dropdown async, với nút Retry tường minh, là chuẩn tối thiểu UX cho bất kỳ field nạp
động nào; (3) lọc payload gửi kèm request theo đúng nhu cầu của từng `loadMethod` (tránh refetch
thừa mỗi keystroke) là một chi tiết hiệu năng dễ bỏ sót khi tự viết cơ chế tương tự.

## 5. Flowise AgentFlow v2 — Human input UX

Nguồn: `packages/observe/src/features/executions/components/HitlPanel.tsx`,
`packages/observe/src/features/executions/hooks/useHumanInput.ts`,
`packages/agentflow/src/features/canvas/components/NodeStatusIndicator.tsx`,
`packages/components/nodes/agentflow/HumanInput/HumanInput.ts`. Đây là lớp UI của gói **`observe`**
(mới, tách riêng khỏi `agentflow`) — bổ sung cho phần runtime "ghi DB rồi đợi API gọi lại" mà audit
22/09 §2.3 đã ghi, ở đây là **cách người dùng NHÌN THẤY và THAO TÁC** với việc tạm dừng đó.

**Trên canvas**, node đang chờ input hiện badge trạng thái tròn màu đỏ (nền trong suốt) với icon
stop-circle và tooltip "Waiting for input" (`NodeStatusIndicator`, trạng thái `WAITING_FOR_INPUT`)
— cùng cơ chế hiển thị với `STOPPED`/`TERMINATED`, không có huy hiệu riêng biệt về mặt hình dạng,
chỉ khác nội dung tooltip.

**Khi xem chi tiết thực thi** (`NodeExecutionDetail`, xem thêm §6), nếu node đang chọn là
`humanInputAgentflow` VÀ trạng thái đang `INPROGRESS` VÀ có callback `onHumanInput` được truyền
vào từ host app, một **thanh hành động nổi cố định ở góc dưới-phải màn hình** (`position: fixed`,
bo tròn, đổ bóng, `z-index: 1000`, `data-testid='hitl-action-bar'`) hiện hai nút **Proceed**
(primary) / **Reject** (outline đỏ) — nổi trên MỌI nội dung khác, không phải một phần của panel
chi tiết node cuộn theo. Nếu node bật cờ `humanInputEnableFeedback`, bấm Proceed/Reject không gửi
ngay mà mở một `Dialog` xin phản hồi dạng văn bản (textarea 3 dòng, nút Submit/Cancel) trước khi
gửi thật; nếu tắt cờ đó, bấm là gửi ngay. Trong lúc gửi, một `Dialog` overlay riêng (không đóng
được) hiện spinner + "Submitting response..." chặn tương tác cho tới khi có kết quả; lỗi gửi hiện
thành `Alert` nổi cố định ngay trên thanh nút, có nút đóng, KHÔNG làm mất trạng thái nút (vẫn có
thể bấm lại).

**Cách resume**: bấm Proceed/Reject gọi `onHumanInput(agentflowId, {question, chatId, humanInput:
{type: 'proceed'|'reject', startNodeId, feedback}})` — payload này do UI observe soạn sẵn, host
app (Flowise chatbot embed) chuyển thành lệnh gọi lại API thực thi của agentflow (đúng cơ chế
"gọi lại API mới" mà audit cũ mô tả), UI không tự biết chi tiết giao thức, chỉ biết gọi một
callback đã được tiêm sẵn.

**Bài học cho LTT:** (1) đặt nút hành động chờ-người-dùng ở một thanh NỔI CỐ ĐỊNH thay vì chôn
trong panel cuộn là lựa chọn hợp lý — người dùng luôn thấy được dù đang cuộn xem input/output dài;
(2) tách rõ "gửi ngay" và "xin phản hồi trước khi gửi" bằng một cờ cấu hình trên node (không phải
luôn luôn bắt nhập text) tránh ma sát không cần thiết cho ca đơn giản; (3) dialog "đang gửi" chặn
tương tác + thông báo lỗi không xoá mất khả năng bấm lại là chi tiết chống mất trạng thái đáng học
khi LTT làm cơ chế duyệt-tiếp/từ-chối tương tự cho workflow v2.

## 6. Flowise AgentFlow v2 — Execution details panel

Nguồn: `packages/observe/src/features/executions/components/{ExecutionDetail.tsx,
NodeExecutionDetail.tsx}`, `packages/observe/src/atoms/MetricsDisplay.tsx`.

**Vị trí trong layout**: `ExecutionDetail` là một layout 3-cột chiếm toàn bộ chiều cao khối chứa
(`display:flex, height:'100%'`) — KHÔNG phải popup che canvas. Cột trái (sidebar cây thực thi,
rộng có thể kéo giãn tay 240–480px qua một thanh `col-resize`, mặc định 300px) liệt kê từng bước
đã chạy dạng cây (`ExecutionTreeSidebar`, hỗ trợ lồng iteration); cột phải (chiếm phần còn lại)
là chi tiết của bước đang chọn. Header cột trái có 2 chip (mở lại Agentflow gốc, copy Execution ID
kèm phản hồi "Copied!" tạm 2 giây) + thời điểm cập nhật + nút refresh — panel tự poll lại
(`pollInterval` mặc định 3000ms), không cần bấm F5. Khi mở lần đầu: tự chọn node STOPPED đầu tiên
nếu cả execution đang STOPPED, ngược lại chọn node đầu tiên, và tự mở rộng (`expandedIds`) toàn bộ
cây — người dùng thấy ngay chỗ dừng/lỗi mà không phải tự dò.

**Nội dung mỗi node** (`NodeExecutionDetail`): header có icon+tên node, và **hàng chip metric**
(`MetricsDisplay`) — thời gian (giây, làm tròn 2 chữ số thập phân, chip màu secondary, icon đồng
hồ; ẩn nếu delta=0), token (số nguyên có dấu phân cách hàng nghìn + chữ "tokens", chip primary,
icon đồng xu), chi phí (`$X.XX` nếu ≥ 1 cent, hiển thị 6 chữ số thập phân nếu nhỏ hơn — tránh hiện
"$0.00" cho chi phí cực nhỏ, chip màu vàng riêng ngoài palette MUI). Toàn hàng chip biến mất nếu
không có metric nào — không hiện "0 giây / 0 token" giả.

Dưới header là công tắc **Rendered / Raw** (`ToggleButtonGroup`) đổi cách xem TOÀN BỘ payload của
node: "Rendered" hiện input/output đã diễn giải theo ngữ nghĩa (bong bóng chat nếu là tin nhắn hội
thoại, danh sách tool đã dùng dạng chip, khối "Fulfilled Conditions" riêng cho node Condition, khối
lỗi viền đỏ riêng nếu có, khối "State" riêng nếu node có cập nhật flow-state); "Raw" thay toàn bộ
bằng một `RawJsonPanel` (JSON thô, có theme sáng/tối). Đây là điểm khác biệt UX chính: người
dùng thường KHÔNG cần đọc JSON, chỉ khi cần soát lỗi implementation mới bật Raw. Với node
`humanInputAgentflow` đang `INPROGRESS`, `HitlPanel` (xem §5) được mount ngay trong panel này.

**Bài học cho LTT:** (1) mô hình 3-cột (cây thực thi | chi tiết bước | metric ngay trên đầu chi
tiết) tách bạch "chọn bước nào" khỏi "xem gì" — nếu LTT có run-inspector tương tự
(`RunInspector.tsx`, `RunV3Panel.tsx` đã có trong `frontend/agent-canvas/src/`), cấu trúc cột
kéo-giãn-được kèm tự-chọn-node-lỗi-đầu-tiên là mẫu đáng đối chiếu; (2) toggle Rendered/Raw là cách
rẻ để phục vụ cả người dùng cuối (không muốn thấy JSON) lẫn người debug (cần JSON thô) trong CÙNG
một panel thay vì hai chỗ khác nhau; (3) ẩn hẳn chip metric khi giá trị rỗng/0 (thay vì hiện số 0)
tránh gây hiểu lầm "đã đo mà ra 0" — khớp đúng bài học đo lường "hai trạng thái gộp thành một giá
trị" đã có trong sổ tay dự án.

## 7. Langflow — Typed ports (visual + invalid-drag behaviour)

Nguồn: `langflow-ai/langflow`, `src/frontend/src/CustomNodes/GenericNode/components/
{handleRenderComponent,HandleTooltipComponent}/index.tsx`, `src/frontend/src/utils/
reactflowUtils.ts` (hàm `isValidConnection`).

- **Màu + nhãn, không hình dạng riêng**: mọi handle là hình tròn giống nhau (React Flow `Handle`
  mặc định); kiểu dữ liệu được truyền tải bằng MÀU nền lấy từ biến CSS
  `hsl(var(--datatype-<tên-màu>))` (tra theo tên kiểu qua bảng `nodeColorsName`) và bằng NHÃN chữ
  hiện trong tooltip dạng Badge (một badge riêng cho mỗi kiểu nếu field nhận nhiều kiểu — union
  type hiện thành nhiều badge cạnh nhau). Không có hình khối khác nhau theo kiểu (không tam
  giác/vuông/tròn phân biệt) — toàn bộ phân biệt kiểu dồn vào MÀU SẮC + CHỮ.
- **Tooltip đổi nội dung theo hành động**: đứng yên hover → "Input/Output type(s): <Badge màu>";
  đang kéo dây từ handle khác tới → đổi thành "**Connect** to <Badge>" (tương thích) hoặc câu dịch
  `node.incompatibleWith` (không tương thích) — nghĩa là LÝ DO được hiện ngay khi đang kéo, không
  phải chỉ sau khi thả hụt; kéo vào chính node đó hiện "Can't connect to the same node". Cuối
  tooltip luôn có gợi ý thao tác cố định: "**Drag** to connect compatible inputs/outputs" và
  "**Click** to filter compatible inputs/outputs and components" — Langflow cho phép CLICK một
  handle (không cần kéo) để lọc palette + làm mờ các handle khác không tương thích, một cơ chế
  khám phá loại kết nối hợp lệ mà không cần thử-sai bằng chuột.
- **Kéo không hợp lệ bị NGĂN, không chỉ cảnh báo**: `Handle` của React Flow nhận prop
  `isValidConnection={(connection) => isLocked ? false : isValidConnection(connection)}` — hàm
  `isValidConnection` trong `reactflowUtils.ts` chặn cả nối vào chính node nguồn (`source ===
  target`) lẫn nối tạo CHU TRÌNH (dò đường bằng `findCyclePath`, trả về path cạnh gây vòng lặp để
  báo lỗi cụ thể chỗ nào tạo vòng, không chỉ nói chung chung "invalid"). Kết hợp với việc handle
  không tương thích bị LÀM MỜ (`isMuted`) ngay khi bắt đầu kéo dây từ handle khác — người dùng thấy
  trước bằng mắt những handle nào chấp nhận được trước khi thả chuột, không phải thử rồi bị bật lại.
- Handle có đầy đủ hỗ trợ bàn phím: `role="button"`, `tabIndex`, `aria-label` mô tả tên field + tên
  node, và `onKeyDown` route Enter/Space sang đúng hành vi click (vì React Flow tắt
  `disableKeyboardA11y` toàn canvas nên nếu không tự thêm, nút sẽ "được thông báo nhưng không thao
  tác được bằng bàn phím" — đúng nguyên văn comment trong mã nguồn).

**Bài học cho LTT:** (1) mã màu + badge chữ (không phải hình dạng) là cách rẻ và đủ rõ để phân biệt
kiểu dữ liệu trên handle, LTT có thể áp dụng trực tiếp qua CSS variable theo kiểu; (2) hiện lý do
tương thích/không tương thích NGAY LÚC ĐANG KÉO (không đợi thả) là chuẩn UX tối thiểu cho canvas có
kiểu; (3) tính năng "click một handle để lọc" là điểm khác biệt đáng cân nhắc — biến việc tìm node
tương thích thành duyệt danh sách đã lọc thay vì kéo-thử từng cái.

## 8. Langflow — Component palette

Nguồn: `src/frontend/src/pages/FlowPage/components/flowSidebarComponent/components/
{categoryDisclouse,categoryGroup,sidebarBundles,sidebarDraggableComponent,searchInput}.tsx`.

- **Phân loại hai tầng rõ rệt**: sidebar tách hẳn thành nhóm "Categories" (loại chức năng: LLM,
  Agent, Data, Logic…) và nhóm "**Bundles**" riêng (`sidebarBundles.tsx`, tiêu đề
  `t("sidebar.bundles")`) — bundles là các gói tích hợp bên thứ ba (provider cụ thể) VÀ cả
  package/extension được **phát hiện lúc chạy** (`ENABLE_EXTENSION_RELOAD`, cài qua package hoặc
  `lfx extension dev`), có nút "Reload" riêng cho loại bundle đó (`bundleHeaderActions.tsx`) — tách
  bạch rất rõ "cái gì lõi sẵn có" khỏi "cái gì là tích hợp/mở rộng cài thêm". Mỗi category/bundle là
  một `Disclosure` (accordion) đóng/mở độc lập, trạng thái mở nhớ theo tên (`openCategories`).
- **Tìm kiếm**: một ô tìm kiếm dạng `type="search"` ở đầu sidebar, có gợi ý phím tắt "**/**" hiện
  mờ bên phải ô khi đang rỗng và không focus (biến mất khi gõ hoặc focus) — mẫu UX quen thuộc kiểu
  Slack/GitHub. Khi có từ khoá, thứ tự sắp xếp category đổi theo mức độ liên quan
  (`sortedCategories`) thay vì thứ tự cố định.
- **Thao tác "thêm" — BA cách cho cùng một item, không bắt buộc kéo-thả**: mỗi dòng component
  trong `sidebarDraggableComponent.tsx` có thể (a) **kéo-thả** ra canvas (`draggable`, cursor
  `grab`), (b) **double-click** để thêm vào vị trí mặc định, hoặc (c) bấm nút "**+**" hiện khi
  hover/focus (ẩn mặc định — `opacity-0` → `100` khi `group-hover`/`group-focus-within`) — cả ba
  đều gọi chung một hàm `addComponent(apiClass, itemName)`. Item còn hỗ trợ đầy đủ bàn phím
  (Enter/Space kích hoạt), có tay cầm kéo (`GripVertical`) làm tín hiệu thị giác thêm cho việc kéo,
  và menu chuột phải (context menu) riêng cho việc xoá.
- **Trạng thái phụ trên mỗi item**: nhãn Beta/Legacy hiện thành badge cạnh tên (và được nhét vào
  chính `aria-label` để không mất thông tin với người dùng đọc màn hình/điều khiển bằng giọng nói —
  comment trong mã trích dẫn đúng tiêu chí WCAG 2.5.3 Label in Name); item "unavailable" (thiếu
  dependency/bị tắt) chuyển sang trạng thái `cursor-not-allowed`, không kéo được, có tooltip giải
  thích lý do thay vì chỉ làm mờ không rõ nguyên nhân; viền trái mỗi item nhuộm màu theo category
  (`borderLeftColor: color`) — cùng ngôn ngữ màu với handle ở §7.

**Bài học cho LTT:** (1) tách "lõi sẵn có" khỏi "tích hợp/mở rộng cài thêm" thành hai nhóm sidebar
riêng (không trộn chung một danh sách phẳng) giúp người dùng phân biệt cái gì luôn có, cái gì cần
cấu hình/credential thêm; (2) cho phép cả kéo-thả LẪN click/double-click để thêm node phục vụ cả
người dùng chuột lẫn bàn phím — nếu palette của LTT hiện chỉ kéo-thả, đây là khoảng trống rẻ để vá;
(3) tooltip giải thích rõ lý do một item "không dùng được" (thay vì chỉ làm mờ) là chi tiết nhỏ
nhưng giảm hẳn nhầm lẫn "tưởng app lỗi".

## 9. Langflow — Component inspector

Nguồn: `src/frontend/src/modals/editNodeModal/{index.tsx,hooks/use-column-defs.ts}`,
`src/frontend/src/modals/editNodeModal/components/editNodeComponent/index.tsx`,
`src/frontend/src/CustomNodes/helpers/process-node-advanced-fields.ts`,
`src/frontend/src/pages/FlowPage/components/nodeToolbarComponent/components/toolbar-modals.tsx`.

**Không phải tabs, không phải accordion theo section — là MỘT BẢNG** (ag-grid `TableComponent`,
`EditNodeModal` mở full-screen-ish qua `BaseModal size="x-large"`). Mỗi field của component là một
HÀNG với 4 cột cố định: (1) **Show/Expose** — toggle hiện/ẩn field đó trên thân node compact ngoài
canvas (cột đầu tiên, ẩn được qua `hideVisibility`); (2) tên field; (3) mô tả (tooltip khi hover,
`wrapText`); (4) giá trị — ô nhập đúng kiểu widget của field (`TableNodeCellRender` chọn control
theo kiểu, y hệt field đó render trên node). Đây chính là **cờ "advanced" per-field** mà đề bài hỏi
— không có một công tắc TOÀN CỤC "Show advanced settings", mà mỗi field có toggle RIÊNG ngay trên
hàng của nó trong bảng; gọn hơn nhưng cũng đòi hỏi người dùng duyệt qua từng hàng nếu muốn bật
nhiều field cùng lúc.
**Tự động lộ diện field advanced khi có kết nối** (`process-node-advanced-fields.ts`): nếu người
dùng nối một cạnh vào field đang bị đánh dấu `advanced: true` (đang ẩn khỏi thân node), hệ thống tự
đặt `advanced = false` cho field đó — người dùng không cần tự tìm trong bảng để "mở khoá" field vừa
nối dây vào.

**Code-editor escape hatch**: nút "Code" trên toolbar nổi của node (`nodeToolbarComponent`, chỉ
hiện khi `hasCode`) mở `CodeAreaModal` — cho sửa THẲNG mã Python định nghĩa component đó. Sau khi
sửa, một `ConfirmationModal` hỏi rõ hai lựa chọn: "**Replace component**" (ghi đè định nghĩa hiện
tại — icon SaveAll) hay "**Create New**" (tách ra thành component tuỳ biến mới, giữ nguyên bản gốc)
— không âm thầm ghi đè. Đây là lối thoát cho bất kỳ hạn chế nào của UI cấu hình field: khi form
không đủ biểu đạt, người dùng luôn có thể rơi xuống mã nguồn Python thật.

**Bài học cho LTT:** (1) mô hình bảng (một hàng một field, cột Show riêng) là cách nén nhiều field
vào một view có thể lọc/cuộn mà không cần accordion lồng nhau — đáng cân nhắc cho node có rất nhiều
tham số; (2) tự-lộ-diện field khi có cạnh nối vào là chi tiết nhỏ giảm hẳn ma sát "tôi nối dây vào
mà không thấy field đâu"; (3) tách rõ "sửa cấu hình qua form" khỏi "sửa mã nguồn thật" với xác nhận
tường minh khi rẽ nhánh (đè bản gốc hay tạo bản mới) là mẫu an toàn nếu LTT có node cho phép người
dùng viết code tuỳ biến (Python/JS).

## 10. Langflow — Subflow / grouping UX

Nguồn: `src/frontend/src/pages/FlowPage/components/SelectionMenuComponent/index.tsx`,
`src/frontend/src/utils/reactflowUtils.ts` (`expandGroupNode`, `updateGroupNodeTemplate`,
`getGroupStatus`, `updateGroupRecursion`).

**Cách vào**: chọn nhiều node (kéo khung chọn) → một `NodeToolbar` của React Flow nổi lên đúng
NGAY TRÊN vùng chọn — điểm kỹ thuật đáng chú ý: `nodeId` của `NodeToolbar` này nhận một **mảng** id
(`lastNodes.map(n => n.id)`), tức dùng đúng khả năng "toolbar theo nhiều node cùng lúc" của React
Flow, không phải tự tính toạ độ trung bình bằng tay. Nút "**Group**" bị vô hiệu hoá kèm tooltip nêu
lý do cụ thể (`errors[0]`) nếu lựa chọn hiện tại có cạnh nối ra ngoài theo cách không hợp lệ
(`validateSelection`) — không cho nhóm rồi báo lỗi sau.

**Kết quả nhóm KHÔNG phải một khung/box hiển thị các node con bên trong** (khác hẳn Iteration của
Flowise ở §1 — container `NodeResizer` luôn nhìn thấy nội dung bên trong). Langflow biến toàn bộ
lựa chọn thành **MỘT node "hộp đen"** duy nhất kiểu `GroupNode` — về mặt render nó là một
`genericNode` bình thường (cùng UI với mọi node khác, xem §11), nhưng `data.node.flow` bên trong
lưu nguyên vẹn đồ thị con (`nodes`+`edges` đã chọn); template của node hộp đen được viết lại
(`updateGroupNodeTemplate`) để chỉ lộ ra các field/handle biên (input/output thật sự nối ra ngoài
nhóm), ẩn hết field nội bộ (kể cả field code). Trạng thái build của node nhóm là trạng thái GỘP của
các node con (`getGroupStatus`) — một badge lỗi ở node nhóm nghĩa là có node con nào đó lỗi.
**"Ungroup" = thay thế tại chỗ**: `expandGroupNode` xoá node hộp đen và chèn lại đúng các node/cạnh
gốc vào CÙNG vị trí trên canvas chính (đổi lại toàn bộ id để tránh đụng độ — `updateIds`), giữ
chúng ở trạng thái đang chọn. Không có "double-click để chui vào xem bên trong rồi quay ra" kiểu
breadcrumb — chỉ có gộp/mở hẳn ra, hai trạng thái rời rạc. Nhóm có thể lồng nhau (
`updateGroupRecursion` đệ quy vào `groupNode.data.node.flow`), nhưng người dùng chỉ thấy được MỘT
cấp tại một thời điểm (cấp ngoài cùng là hộp đen, phải ungroup mới thấy cấp trong).

**Bài học cho LTT:** (1) `NodeToolbar` nhận mảng nhiều `nodeId` là một kỹ thuật React Flow đáng
chép cho bất kỳ hành động "áp dụng cho cả vùng chọn" nào (LTT hiện chưa dùng `NodeToolbar` — xem
P1 ở §12); (2) chặn hành động (Group) kèm lý do cụ thể TRƯỚC khi thực hiện, thay vì làm rồi báo lỗi,
là nguyên tắc chung nên áp dụng cho mọi thao tác gộp/xoá hàng loạt; (3) mô hình "hộp đen thay thế
tại chỗ" (không phải khung lồng luôn hiển thị) đơn giản hơn để cài đặt nhưng đánh đổi mất khả năng
"nhìn thoáng qua bên trong nhóm mà không cần mở" — nếu LTT muốn UX xem-nhanh tốt hơn, mô hình
`parentId`/`extent:'parent'` của React Flow (đã đề xuất P1 ở §12) gần với cách Flowise làm hơn.

## 11. Langflow — Visual hierarchy của node

Nguồn: `src/frontend/src/CustomNodes/GenericNode/index.tsx`,
`src/frontend/src/CustomNodes/GenericNode/components/{NodeStatus,NodeName}/index.tsx`.

**Kích thước & mật độ — hai cấp rời rạc, không liên tục**: node có đúng hai chiều rộng cố định,
`w-80` (320px, mở rộng — có thân hiển thị field) hoặc `w-48` (192px, thu gọn — chỉ icon+tên+cổng),
chuyển qua lại bằng cờ `showNode` trên chính data của node (không phải zoom-level tự động). Khi thu
gọn, các handle nhiều hơn 1 được RẢI ĐỀU theo chiều dọc card (`minimizedHandleTop`) để không chồng
lên nhau ở giữa — chi tiết nhỏ nhưng cho thấy trạng thái thu gọn được tính toán lại vị trí cổng chứ
không chỉ ẩn phần thân bằng CSS. Bo góc lớn (`rounded-xl`), viền mảnh + đổ bóng nhẹ đậm dần khi
hover (`shadow-sm hover:shadow-md`) — không có viền màu theo trạng thái build trên khung ngoài card
(khác Flowise, nơi viền đổi màu theo `stateColor`/lỗi validate ở §1); Langflow dồn toàn bộ tín hiệu
trạng thái vào MỘT nơi duy nhất.
**Trạng thái = nút, không phải huy hiệu tĩnh** (`NodeStatus`): góc phải-trên mỗi node KHÔNG phải một
badge chỉ để nhìn, mà là một NÚT bấm được, đổi hình theo `BuildStatus` (`TO_BUILD`/`BUILDING`/
`BUILT`/`ERROR`/`INACTIVE`) — bấm khi `BUILT` để build lại, hover khi đang `BUILDING` đổi thành nút
dừng. Gộp "xem trạng thái" và "hành động build/dừng" vào cùng một điểm bấm duy nhất, thay vì tách
badge trạng thái khỏi nút hành động như Flowise (badge trạng thái + nút Play là hai thứ riêng trong
NodeToolbarActions ở §1).
**Tiêu đề đổi tên tại chỗ** (`NodeName`): double-click trực tiếp lên tên node trên canvas (không
cần mở dialog) để sửa inline — khác Flowise, nơi đổi tên phải mở `EditNodeDialog` rồi mới bấm icon
bút chì bên trong dialog đó (§1).

**Bài học cho LTT:** (1) hai bậc rộng cố định (thu gọn/mở rộng) đơn giản hơn và dễ đoán hơn resize
tự do cho trường hợp phổ thông — chỉ node dạng container mới cần `NodeResizer` tự do (đúng như
Flowise chỉ dùng cho Iteration ở §1); (2) gộp trạng thái+hành động build vào một nút là một cách
giảm số điểm bấm trên mỗi node — đáng cân nhắc nếu LTT có khái niệm "build/chạy từng node"; (3) cho
sửa tên node tại chỗ bằng double-click trực tiếp trên canvas (không qua dialog) là thao tác nhanh
hơn hẳn cho một hành động rất thường gặp.

## 12. React Flow / xyflow — bảng kiểm kê tính năng

Nguồn: [API Reference](https://reactflow.dev/api-reference) (danh mục component/hook/util),
[`<ReactFlow>` props](https://reactflow.dev/api-reference/react-flow), [`Node` type — `parentId`/
`extent`](https://reactflow.dev/api-reference/types/node), [Helper Lines
example](https://reactflow.dev/examples/interaction/helper-lines). Cột "LTT dùng chưa" lấy từ
`grep -rn "@xyflow/react"` trên toàn bộ `frontend/agent-canvas/src/` (~3000 dòng, đọc hết —
xem §14 và danh sách file). Ưu tiên P0 = nên làm ngay trong v2 vì rẻ và bịt lỗ hổng UX rõ; P1 =
đáng làm khi có thời gian; P2 = cân nhắc, giá trị thấp hơn hoặc rủi ro/độ phức tạp cao hơn lợi ích.

| Import | Cho người dùng điều gì | LTT dùng chưa | Ưu tiên (P0/P1/P2) |
|---|---|---|---|
| `Background` | Lưới/chấm nền để định vị khi pan/zoom | **Có** — `CanvasShell.tsx:865`, bật/tắt qua `showGrid` | — |
| `Controls` | Nút zoom in/out/fit-view/khoá tương tác ở góc canvas | **Có** — `CanvasShell.tsx:865`, `orientation="horizontal"` | — |
| `MiniMap` | Bản đồ thu nhỏ toàn đồ thị, click để nhảy viewport | **Có** — `CanvasShell.tsx:865`, bật/tắt qua `showMinimap` | — |
| `Panel` | Đặt UI tuỳ ý (toolbar, badge) neo theo góc/canh của canvas, tự theo pan/zoom | **Chưa** | P2 — LTT tự định vị toolbar bằng CSS thường; `Panel` chỉ đáng nếu toolbar cần bám theo viewport |
| `NodeToolbar` | Toolbar nổi phía trên node đang chọn (xoá/nhân bản/…) tự căn theo `Handle`/zoom | **Chưa** | P1 — hiện LTT không có menu nhanh trên từng node (context-menu chuột phải thay cho việc này); `NodeToolbar` rẻ để thêm nút "xoá/nhân bản" mà không phải tự tính toạ độ |
| `NodeResizer` | Tay kéo resize node built-in, kèm ràng buộc min/max size, giữ tỉ lệ | **Chưa** | P2 — node LTT hiện có kích thước cố định theo loại; chỉ cần nếu thêm node dạng "group/note" cần co giãn |
| `Handle` + `useNodeConnections`/`useHandleConnections` | `Handle`: điểm nối vào/ra trên node. `useNodeConnections`/`useHandleConnections`: đọc danh sách cạnh đang nối vào một node/handle cụ thể theo kiểu React hook (thay vì tự lọc mảng `edges`) | `Handle` **có** (`nodes/NodeKhung.tsx`); hai hook **chưa** | P1 — `NodeKhung.tsx` nhiều khả năng đang tự lọc `edges` bằng tay để biết handle nào đã nối; hai hook này thay bằng subscribe có chọn lọc, giảm re-render toàn store (xem §13) |
| `useReactFlow` (`fitView`, `screenToFlowPosition`, `getNodesBounds`) | Instance API: `fitView` canh khung nhìn, `screenToFlowPosition` đổi toạ độ chuột→canvas, `getNodesBounds` tính hình chữ nhật bao một tập node | **Có một phần** — `fitView` (`CanvasShell.tsx:306,863`) và `screenToFlowPosition` (dòng 836/838/854) đã dùng; `getNodesBounds` **chưa** | P2 cho `getNodesBounds` — chỉ cần khi làm "zoom to selection" hoặc export ảnh một vùng chọn |
| `useOnSelectionChange` | Callback khi tập node/cạnh đang chọn thay đổi, không phải tự so sánh mảng mỗi render | **Chưa** | P1 — nếu Inspector panel cần biết "đang chọn gì" để đổi nội dung, hook này gọn hơn tự diff `selected` trên từng node |
| `useNodesState`/`useEdgesState` | Hook tiện ích bọc `useState` + `applyNodeChanges`/`applyEdgeChanges`, giảm code lặp cho flow đơn giản | **Chưa** (cố ý) — LTT dùng `editorReducer` riêng (`editorState.ts`) vì cần undo/redo và các bất biến khác `useNodesState` không có | — (quyết định kiến trúc, không phải lỗ hổng) |
| `SelectionMode` | `'full'` (mặc định) chỉ chọn node nằm trọn trong khung kéo, `'partial'` chọn cả node chạm biên | **Chưa** (mặc định `'full'`) | P2 — UX nhỏ, chỉ đáng đổi nếu người dùng phàn nàn khó chọn node lớn |
| `ConnectionMode` | `'strict'` (mặc định) chỉ cho nối source→target đúng chiều; `'loose'` cho nối handle bất kỳ | **Chưa** (mặc định `'strict'`) | — |
| `ConnectionLineType` | Kiểu đường vẽ TẠM khi đang kéo dây nối (bezier/step/…) trước khi thả | **Chưa** (mặc định bezier) | P2 — nên đổi sang `smoothstep` để khớp `getSmoothStepPath` đã dùng cho cạnh thật (`CanvasEdgeView.tsx`), tránh lệch hình dạng giữa lúc kéo và sau khi thả |
| `reconnectEdge` | Cho phép kéo lại một đầu cạnh đã có sang handle khác thay vì xoá-nối-lại | **Chưa** | P0 — đây là thao tác sửa flow rất thường gặp (đổi input của một node); thiếu nó buộc người dùng xoá cạnh rồi vẽ lại, dễ nhầm |
| `EdgeLabelRenderer` | Render label/nút HTML thường (không phải SVG) lên giữa cạnh, vẫn theo đúng toạ độ zoom/pan | **Có** — `CanvasEdgeView.tsx`, dùng cho nút "+" chèn node giữa cạnh | — |
| `BaseEdge` | Path SVG nền cho edge tuỳ biến, tự lo `markerEnd`/style | **Có** — `CanvasEdgeView.tsx` | — |
| `getSmoothStepPath` | Tính toạ độ path dạng "bậc thang bo góc" cho cạnh | **Có** — `CanvasEdgeView.tsx:8` | — |
| `ViewportPortal` | Portal render element vào layer theo toạ độ flow (không phải toạ độ màn hình), hữu ích cho overlay theo vùng | **Chưa** | P2 |
| `NodeOrigin` | Đổi điểm neo của node (mặc định góc trên-trái `[0,0]`) — ảnh hưởng animation/align | **Chưa** (mặc định) | — |
| Sub-flow (`parentId`, `extent: 'parent'`) | Nhóm node vào trong một node cha, giới hạn kéo-thả trong biên cha, cha tự phình khi con chạm biên (`expandParent`) | **Chưa** | P1 — đây là cơ chế "group box" mà cả Flowise (không có) lẫn Langflow (nhóm phẳng, xem §10) đều làm yếu; nếu LTT muốn nhóm node trực quan hơn hai đối thủ, đây là API rẻ nhất |
| `elevateNodesOnSelect` | Tự nâng z-index node đang chọn lên trên các node khác | **Chưa** (mặc định `true` — đang hưởng lợi mà không set tường minh) | — |
| `onlyRenderVisibleElements` | Chỉ render DOM cho node/cạnh nằm trong viewport hiện tại (viewport culling) | **Chưa** (mặc định `false`) | P1 — xem §13, đây là đòn bẩy hiệu năng rẻ nhất cho đồ thị lớn mà LTT chưa bật |
| Helper Lines (ví dụ chính thức, không phải export) | Đường gióng hàng + snap khi kéo node, tự vẽ bằng `useNodesState`/`onNodesChange` tuỳ biến, không cần thư viện ngoài | **Chưa** | P1 — Flowise/Langflow đều không có snap-to-align; đây là điểm khác biệt UX rẻ (thuần logic, không phụ thuộc gói ngoài) |
| `useNodesInitialized` | Biết khi nào tất cả node đã đo xong kích thước DOM thật (cần trước khi gọi `fitView`/layout tự động chính xác) | **Chưa** | P2 — chỉ cần nếu thêm auto-layout (dagre/elk) chạy sau khi node mount |
| `getViewportForBounds` | Tính zoom/x/y cần thiết để một vùng bao vừa khung nhìn cho trước (dùng khi export ảnh/PDF theo vùng) | **Chưa** | P2 |
| `toObject` (từ `useReactFlow`) | Xuất `{nodes, edges, viewport}` hiện tại thành object thuần để lưu/serialize | **Chưa** — LTT có `workflowApi.ts`/`editorState.ts` tự quản lý document riêng | — (LTT có mô hình dữ liệu riêng, không cần bản chụp của React Flow) |
| `deleteKeyCode` | Phím xoá node/cạnh đang chọn | **Có** — `CanvasShell.tsx:863` set `null` (cố ý TẮT, tự xử lý xoá bằng logic riêng) | — |
| `multiSelectionKeyCode` | Phím giữ để chọn nhiều node bằng click | **Có** — `CanvasShell.tsx:861` set `['Control','Meta']` | — |
| `selectionKeyCode` | Phím giữ để kéo khung chọn nhiều node | **Chưa** (mặc định `'Shift'`, không override) | — |
| `panActivationKeyCode` | Phím giữ để pan bằng chuột trái thay vì kéo chọn | **Chưa** (mặc định `'Space'`, không override) | — |
| `zoomActivationKeyCode` | Phím giữ để cuộn chuột = zoom thay vì scroll | **Chưa** (mặc định theo nền tảng, không override) | — |

**Đếm nhanh:** trong ~30 API được liệt kê ở scope, LTT đang dùng **11** (`Background`, `Controls`,
`MiniMap`, `Handle`, `useReactFlow`+`fitView`+`screenToFlowPosition`, `EdgeLabelRenderer`,
`BaseEdge`, `getSmoothStepPath`, `deleteKeyCode`, `multiSelectionKeyCode`) và **chưa dùng ~19**.

**Bài học cho LTT:** (1) `reconnectEdge` là lỗ hổng UX rõ nhất — thao tác "đổi input của node"
hiện chắc chắn phải xoá-vẽ-lại cạnh; (2) `onlyRenderVisibleElements` là đòn bẩy hiệu năng một dòng
cho đồ thị lớn, chưa bật; (3) sub-flow qua `parentId`/`extent:'parent'` + Helper Lines snap-to-align
là hai điểm có thể vượt cả Flowise lẫn Langflow về UX nhóm/canh node mà chi phí triển khai thấp
(thuần API có sẵn, không cần gói ngoài).

## 13. React Flow / xyflow — mẫu hiệu năng cho đồ thị lớn

Nguồn: [Performance guide](https://reactflow.dev/learn/advanced-use/performance) chính thức.

- **Memo hoá node/edge tuỳ biến**: "Components provided as props to the `<ReactFlow>` component,
  including custom node and edge components, should either be memoized using `React.memo` or
  declared outside the parent component." LTT: `nodes/NodeRenderer.tsx` — cần xác nhận riêng có bọc
  `React.memo` hay khai báo ngoài component cha hay không (không nằm trong scope grep của việc này).
- **Không subscribe cả store**: tài liệu cảnh báo mỗi lần mảng `nodes` đổi sẽ re-render mọi
  component phụ thuộc dù thay đổi không liên quan; khuyến nghị tách state phái sinh (ví dụ danh sách
  ID đang chọn) ra khỏi `nodes` để giảm phạm vi re-render. Đây chính là lý do `useNodeConnections`/
  `useHandleConnections` (đọc chọn lọc qua hook) tốt hơn tự lọc `edges` toàn cục trong component node
  — xem cảnh báo P1 ở bảng §12.
  Nguồn: [Performance guide](https://reactflow.dev/learn/advanced-use/performance).
- **`useCallback`/`useMemo` cho props hàm/mảng/object** (ví dụ `defaultEdgeOptions`) để tránh re-render
  khi kéo node. Nguồn: cùng trang.
- **Ẩn node bằng `hidden` thay vì render cả cây** cho cấu trúc lồng sâu — dùng khi cần thu gọn một
  nhánh lớn thay vì luôn render toàn bộ. Nguồn: cùng trang.
- **`onlyRenderVisibleElements`**: prop của `<ReactFlow>` (mặc định `false`) chỉ render DOM cho
  node/cạnh nằm trong viewport — đây là cơ chế viewport-culling chính thức nhưng **không nằm trong**
  trang "Performance" nói trên; nó được ghi trong trang props tham chiếu
  ([`<ReactFlow>` props](https://reactflow.dev/api-reference/react-flow)). LTT chưa bật (§12).
- **`nodesDraggable`**: LTT đã set theo `!readOnly` (`CanvasShell.tsx:860`) — tắt kéo node toàn cục
  khi ở chế độ chỉ xem, đúng khuyến nghị giảm việc tính toán không cần thiết ở chế độ đọc.
- **Trần số node thực tế**: `KHÔNG XÁC MINH ĐƯỢC` — trang Performance chính thức không nêu con số
  node/cạnh cụ thể ("does not mention specific node-count benchmarks or practical ceilings"). Đã
  tìm thêm qua GitHub issues của `xyflow/xyflow` nhưng không thấy một ngưỡng chính thức được đội
  ngũ xyflow xác nhận (các con số lưu hành trên cộng đồng — vài trăm đến ~1000 node mượt, hàng nghìn
  cần viewport-culning/virtualization thủ công — là suy luận từ issue riêng lẻ, không phải công bố
  chính thức, nên không trích dẫn số cụ thể ở đây).

**Bài học cho LTT:** (1) xác nhận `NodeRenderer.tsx` đã memo hoá đúng cách (rẻ, nên làm ngay khi số
node/flow tăng); (2) bật `onlyRenderVisibleElements` là thay đổi một dòng, nên thử đo trước/sau trên
một flow lớn thật trước khi bật mặc định (đo, không suy đoán — theo luật đo lường của dự án); (3) cân
nhắc tách "ID node đang chọn" ra khỏi vòng lặp render node thường qua `useNodeConnections` khi
`NodeKhung.tsx` cần biết trạng thái nối của chính nó.

## 14. React Flow / xyflow — phiên bản

- LTT pin `"@xyflow/react": "12.11.2"` trong `frontend/agent-canvas/package.json`.
- Bản mới nhất trên npm tại thời điểm khảo sát (2026-09-27, `npm view @xyflow/react version`):
  **12.12.0**. LTT lệch 4 bản patch/minor phía sau (12.11.2 → 12.11.3 → …12.11.6 → 12.12.0), không
  lệch major.
- Toàn bộ ~30 API trong bảng kiểm kê §12 (`Panel`, `NodeToolbar`, `NodeResizer`,
  `useNodeConnections`, `useHandleConnections`, `useOnSelectionChange`, `reconnectEdge`,
  `onlyRenderVisibleElements`, `parentId`/`extent:'parent'`, Helper Lines, v.v.) đều thuộc API dòng
  `@xyflow/react` v12 nói chung — namespace `@xyflow/react` (thay cho `react-flow-renderer` cũ) bắt
  đầu từ v12, và tất cả tính năng khảo sát ở đây không phải tính năng "next"/beta mới thêm gần đây
  theo nội dung trang API reference hiện hành. Không phát hiện tính năng nào trong danh sách yêu cầu
  bản mới hơn 12.11.2 mà LTT đang pin.
- `KHÔNG XÁC MINH ĐƯỢC` ở mức chi tiết: phiên bản v12.x CHÍNH XÁC nào lần đầu thêm từng hook/prop
  (ví dụ `useHandleConnections` có thể đã thêm ở một bản 12.x cụ thể) — trang docs hiện tại chỉ mô tả
  API mới nhất, không giữ lịch sử "thêm từ bản nào"; cần đọc CHANGELOG.md của `xyflow/xyflow` trên
  GitHub theo từng tag để xác nhận chính xác, việc này chưa làm trong khảo sát này.

**Bài học cho LTT:** không có áp lực nâng cấp bắt buộc — 12.11.2 đã hỗ trợ mọi API được đề xuất ở
§12. Nâng lên 12.12.0 (4 bản patch/minor) là việc rẻ, rủi ro thấp, nên làm trước khi bắt đầu dùng
`reconnectEdge`/`onlyRenderVisibleElements` để tránh vá lỗi trên bản cũ nếu có fix liên quan.

## Giới hạn của khảo sát này

- **Không chạy được UI thật trong trình duyệt** — khảo sát này đọc mã nguồn (GitHub Contents API +
  `gh api`/`git/trees`) và tài liệu chính thức, KHÔNG tự cài/chạy Flowise hay Langflow để thao tác
  bằng Playwright/tay. Mọi mô tả hành vi (tooltip đổi nội dung khi kéo, thanh tiến trình giả, toggle
  loading…) được suy từ đọc mã, không phải quan sát trực tiếp trên giao diện render thật — luật
  kiểm-GUI-bằng-trình-duyệt-thật trong CLAUDE.md toàn cục áp dụng cho việc **sửa GUI của LTT**, còn
  đây là khảo sát UI của SẢN PHẨM BÊN THỨ BA nên không có "ứng dụng của mình" để mở trong Playwright;
  bù lại, mọi khẳng định đều trích dẫn đường dẫn tệp + đôi khi số dòng để người đọc tự đối chiếu mã.
- **GitHub code-search API không dùng được trong lượt khảo sát này** — `gh api search/code` và
  `gh search code` đều trả `total_count: 0` / rỗng cho MỌI truy vấn, kể cả trên repo đối chứng
  `facebook/react` (không phải do FlowiseAI/Flowise bị archived) — nghi vấn giới hạn/token của phiên
  `gh auth status` hiện tại, không xác minh được nguyên nhân chính xác. Toàn bộ khảo sát Flowise và
  Langflow dùng `git/trees?recursive=1` + đọc từng tệp qua Contents API để bù lại — chậm hơn nhưng
  không phụ thuộc search, và có rủi ro bỏ sót tệp nếu tên không xuất hiện trong đường dẫn (search sẽ
  bắt được nội dung bên trong tệp mà đường dẫn không gợi ý).
- **Flowise `packages/agentflow`**: đã đọc phần lớn `features/canvas`, `features/node-editor`,
  `features/generator`, `atoms/Variable*`, và `packages/observe/src/features/executions` — nhưng
  KHÔNG đọc `packages/agentflow/src/atoms/{ConditionBuilder,ScenariosInput,MessagesInput,
  StructuredOutputBuilder,ArrayInput,JsonInput}.tsx` (các input phức hợp được `EditNodeDialog` gọi
  tới) và không đọc toàn bộ `packages/ui/src` (UI v1/legacy JSX) để so sánh trực tiếp cũ-mới.
- **Langflow**: chưa đọc `CustomEdges/index.tsx` (edge tuỳ biến, ngoài phần đã suy qua
  `isValidConnection`), chưa xem `PageComponent` (canvas wrapper chính, nơi cấu hình `ReactFlow`
  props như `disableKeyboardA11y` đã trích dẫn gián tiếp qua comment ở nơi khác), và KHÔNG xác minh
  được UI thật của `EditNodeModal` có được dùng làm đường sửa CHÍNH hay chỉ là đường phụ cho ca cần
  bật nhiều field advanced cùng lúc/xem tweaks cho API — đọc mã cho thấy nó tồn tại và cấu trúc thế
  nào, không cho thấy tần suất người dùng thực tế mở nó so với sửa field ngay trên thân node.
- **§13 (hiệu năng)**: KHÔNG XÁC MINH ĐƯỢC một ngưỡng số-node cụ thể do React Flow công bố chính
  thức — trang Performance guide không nêu con số, và không tìm được công bố chính thức khác của
  đội `xyflow` trong lượt khảo sát này (xem chi tiết trong §13).
- **§14**: không xác minh được bản `@xyflow/react` chính xác nào lần đầu thêm từng hook trong bảng
  §12 (đã ghi rõ trong §14) — cần đọc CHANGELOG theo tag trên GitHub, chưa làm.
- **Giấy phép**: không lặp lại phần giấy phép (đã có ở audit 22/09 §6) — riêng phát hiện MỚI đáng
  ghi chú: repo `FlowiseAI/Flowise` đang ở trạng thái `archived: true` tính đến 2026-09-27
  (`gh api repos/FlowiseAI/Flowise --jq .archived`); không xác minh được lý do hay thời điểm archive,
  và không rõ điều này có ảnh hưởng gì tới lộ trình PORT đã quyết định ở audit cũ hay không — đáng
  một dòng hỏi lại chủ dự án nếu quyết định PORT dựa trên giả định repo còn duy trì tích cực.
