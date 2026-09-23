# Khảo sát bổ sung: n8n (sâu hơn) + Flowise AgentFlow v2 + Langflow + Temporal (ngắn)

> Nguồn: GitHub MCP (`get_file_contents`, `search_code`, `get_latest_release`) đọc trực tiếp mã tại
> commit/tag nêu dưới mỗi mục. Không dùng WebFetch/WebSearch (không cần — mọi câu hỏi trả lời được
> bằng mã nguồn). Đọc lướt `05_N8N_AUDIT.md`, `10_TEMPORAL_AUDIT.md`, `12_19_TONG_HOP_SO_SANH.md` —
> KHÔNG lặp lại nội dung đã có ở đó, chỉ bổ sung phần đề bài hỏi mà ba tài liệu đó chưa trả lời.
> Flowise và Langflow là khảo sát MỚI hoàn toàn (không có audit cũ).

---

## 0. TÓM TẮT — 5 phát hiện đáng giá nhất

1. **Langflow có checkpoint/resume thật gần nhất với LTT cần** (`graph/checkpoint/*`, mã `LE-1440`):
   một `GraphCheckpoint` Pydantic bất biến, serialize theo "wire envelope" gắn nhãn kiểu
   (`{__lfx_ser__: raw|dict|list|model}`), **giá trị không serialize được (client LLM, Tool) suy biến
   thành `None` một cách CÓ CHỦ Ý** thay vì crash, rồi khi resume **tính lại điểm chạy tiếp bằng
   fixpoint** (un-build đúng các vertex có giá trị bị rớt mà một vertex chưa build sẽ đọc phải).
   Đây là câu trả lời hay nhất cho `WF-301/WF-401` mà cả nhóm workflow-automation (n8n, Activepieces)
   không có.
2. **Edge có kiểm KIỂU DỮ LIỆU thật ở thời điểm dựng cạnh** (Langflow `types_compatible()`,
   `Edge._validate_edge`) — so khớp `source.outputs[].types` với `target.required_inputs +
   target.optional_inputs`, có cả bảng **di trú kiểu** (`Data→JSON`, `DataFrame→Table`). Đây là
   `WF-701` được giải trọn vẹn nhất trong toàn bộ đợt khảo sát (n8n chỉ có *loại kết nối*, không có
   *kiểu dữ liệu*; Flowise không kiểm kiểu ở cạnh).
3. **Flowise AgentFlow v2 KHÔNG có Loop/Iteration thật** — `Loop` là một **goto lùi** (nhảy về node id
   đã chạy, đếm bằng `maxLoopCount`, không phải một khối lặp), `Iteration` là **đệ quy trong tiến
   trình** (`isRecursive: true`, gọi lại `executeNode`) — tuần tự, giống hệt `SplitInBatches` của n8n.
   `ExecuteFlow` (subflow) gọi lại **API HTTP của chính nó** (`POST /api/v1/prediction/<flowId>`),
   không phải lời gọi trong tiến trình như n8n/Langflow — một lựa chọn kiến trúc khác hẳn, đáng chú ý
   khi so `WF-106`.
4. **Phần lớn engine thi hành AgentFlow của Flowise là Apache-2.0** (chỉ `packages/server/src/
   enterprise/` và tệp có `.ee.`/copyright riêng là Commercial License) — kể cả tệp orchestrator
   `packages/server/src/utils/buildAgentflow.ts` và mọi node trong `packages/components/nodes/
   agentflow/*`. Khác hẳn n8n (Sustainable Use License chặn mọi mục đích thương mại) — **Flowise CÓ
   THỂ chép mã** cho LTT (SaaS thương mại), n8n thì không.
5. **n8n đã thay hẳn sandbox expression**: `tmpl` (cũ) → `@n8n/tournament` (biến đổi AST + `new
   Function()`, KHÔNG cách ly tiến trình) → **`@n8n/expression-runtime` chạy trong V8 isolate qua
   `isolated-vm`** (mặc định hiện nay; `N8N_EXPRESSION_ENGINE=legacy` mới quay lại cũ). Đáng học nếu
   LTT tự viết engine expression: `new Function()`/`vm` KHÔNG cách ly bộ nhớ/CPU, `isolated-vm` mới.

---

## 1. n8n — BỔ SUNG (không lặp `05_N8N_AUDIT.md`)

> Kho: `n8n-io/n8n`, commit `dfe014a2ba414efc5b37f20da3f2414db7716f4c` (mới hơn bản 05, 2026-09-22) và
> `6433934db70b10073026235263c35687c5d3f239` cho `Wait.node.ts`.

### 1.1 Cú pháp expression — ba tầng, không phải một

`{{ $json.foo }}`, `$node["Name"].json`, `$input.first()/last()/all()`, `$execution.resumeUrl` là cú
pháp **bề mặt**; bên dưới có ba tầng hoàn toàn khác audit cũ chưa nhắc:

```
packages/workflow/src/expression.ts            → Expression.vmEvaluator, chọn evaluator
packages/workflow/src/expression-sandboxing.ts → AST hooks (astBuilders, TournamentHooks) chặn
                                                   truy cập arguments/module built-in qua spread
packages/@n8n/tournament/src/                  → Tournament: biến đổi {{ }} → JS, VariablePolyfill
                                                   ("x" in this ? this : global).x
packages/@n8n/expression-runtime/src/          → LỚP MỚI: IsolatedVmBridge (isolated-vm), cache mã
                                                   đã biến đổi theo Tournament, README ghi rõ
                                                   "default engine; N8N_EXPRESSION_ENGINE=legacy
                                                   opts out"
```

`CONFIRMED` — ba thế hệ: **tmpl** (bỏ, xem `deprecation.service.ts`: *"n8n has replaced `tmpl` with
`tournament`"*) → **tournament + `new Function()`** (không cách ly, chỉ chặn bằng AST) → **tournament +
`isolated-vm`** (cách ly V8 isolate thật, mặc định hiện nay). `expression-runtime/README.md` nói rõ lý
do: chuyển dữ liệu qua ranh giới isolate chỉ theo **metadata** (khoá, độ dài), không phải toàn bộ dữ
liệu — giữ hiệu năng khi payload lớn.

⇒ **Với LTT** (nếu tự cho phép expression trong bước — hiện `WF-2xx` chưa nhắc): `new Function()`/`vm`
Node hay `eval` Python **không phải sandbox**, chỉ là chặn cú pháp bằng AST; nếu LTT cần cách ly thật
(người dùng nhập biểu thức chạy trên server LTT), mô hình đúng là "biến đổi AST + chạy trong tiến trình
con/cô lập bộ nhớ" như `isolated-vm`, không phải chặn bằng danh sách đen.

### 1.2 Credential — mã hoá hai tầng (DEK + khoá instance)

```
packages/core/src/encryption/cipher.ts
packages/cli/src/__tests__/credentials-helper.test.ts
  cipher.encryptDEKWithInstanceKey('test_key_for_testing')
  { algorithm: 'aes-256-cbc', format: 'no-prefix' }
```

`CONFIRMED` (từ test, chưa đọc trọn `cipher.ts`) — mỗi credential có **DEK riêng** (Data Encryption
Key), DEK đó được mã hoá bằng **khoá instance** (`InstanceSettings`) — mô hình **envelope encryption**
hai tầng, không phải một khoá toàn cục mã trực tiếp mọi secret. `algorithm: aes-256-cbc`.

`credential_ref` trong workflow JSON: node chỉ giữ `{ id, name }` của credential (không giữ giá trị) —
giá trị được `CredentialsHelper` tra ở thời điểm thi hành, theo `nodeCredentialType` khai trong
`INodeType.description.credentials[].name`, và mỗi `ICredentialType` khai `properties[]` (schema field
+ `typeOptions.password: true` để ẩn UI) + tuỳ chọn `authenticate` (tự thêm header/query) hoặc
`test` (request kiểm tra credential còn sống).

### 1.3 Wait node — bốn chế độ resume, và một ngưỡng chi phí đáng chép

```
packages/nodes-base/nodes/Wait/Wait.node.ts (đọc trọn, 400 dòng)
```

Bốn `resume`: `timeInterval` · `specificTime` · `webhook` · `form`. `CONFIRMED`.

⭐ **Chi tiết đáng chép nhất:** với `timeInterval`/`specificTime`, nếu thời gian chờ **< 65 giây**,
n8n **KHÔNG** đẩy execution vào trạng thái `waiting` trong CSDL — nó giữ tiến trình sống bằng
`setTimeout` trong bộ nhớ:

```ts
if (waitValue < 65000) {
    // If wait time is shorter than 65 seconds leave execution active because
    // we just check the database every 60 seconds.
    return await new Promise((resolve) => { const timer = setTimeout(...); ... })
}
return await this.putToWait(context, waitTill)   // ≥ 65s: mới ghi DB + giải phóng worker
```

Lý do ghi thẳng trong code: bộ quét `waitTill` của họ (`05 §3.4`) chạy **mỗi 60 giây**, nên chờ ngắn
hơn chu kỳ quét thì ghi DB không mua được gì, chỉ tốn một round-trip. `webhook`/`form` luôn
`WAIT_INDEFINITELY` (hằng số) trừ khi bật `limitWaitTime`.

⇒ **Với LTT:** nếu `WF-401` (waitpoint) định kỳ quét bằng SQL, nên có **ngưỡng dưới** tương tự — chờ
ngắn hơn chu kỳ quét thì không đáng đẩy job ra khỏi worker.

`$execution.resumeUrl` / `$execution.resumeFormUrl` là URL **có chữ ký** sinh tại runtime, không phải
URL tĩnh — người dùng gài nó vào bước trước (gửi email/Slack) rồi Wait chờ webhook gọi lại đúng URL đó.
`builderHint` trong code còn khuyên AI-builder **ưu tiên node `sendAndWait`** (Slack/email có nút
Approve/Reject dựng sẵn) hơn là tự ráp Wait+webhook cho luồng duyệt người — một quy ước UX đáng cân
nhắc cho LTT's Human-in-loop node.

### 1.4 Error workflow — chỉ kích hoạt khi THẬT SỰ lỗi, không khi đang chờ

```
packages/cli/src/execution-lifecycle/execution-lifecycle-hooks.ts
  if (fullRunData.status !== 'success' && fullRunData.status !== 'waiting') {
      executeErrorWorkflow(...)
  }
```

`CONFIRMED` — trạng thái `waiting` (Wait node, hoặc chờ human input) **không** kích hoạt error
workflow — chỉ `error`/`crashed` mới kích. Error workflow là **một workflow khác** (tham chiếu qua
`settings.errorWorkflow` = id), chạy như **sub-execution** với `IWorkflowErrorData` (lỗi + node lỗi +
execution id gốc) làm input — không tự viết trong cùng đồ thị.

### 1.5 Execution history / Merge / Sub-workflow / Credential types

Không tìm thêm gì mới đáng kể ngoài những gì `05_N8N_AUDIT.md §3` đã ghi (bảng `ExecutionData`, một
cột `text`). **Merge node** và **Execute Workflow** không đọc lại — audit cũ đã xác nhận `WF-106 ✅`
(`executeWorkflow`, sub-execution) ở mức đủ cho quyết định kiến trúc; không có phát hiện mới thay đổi
kết luận đó.

### 1.6 Giấy phép — xác nhận chính xác bằng văn bản gốc

```
LICENSE.md (đọc trọn)
```

**Sustainable Use License 1.0**: cho phép dùng/sửa/phân phối **chỉ cho mục đích nội bộ của bạn, hoặc
phi thương mại/cá nhân**; phân phối lại cho người khác **phải miễn phí và phi thương mại**. `CONFIRMED`
— văn bản này **cấm** LTT (SaaS thương mại bán credit) chép mã n8n vào sản phẩm, kể cả sửa đổi, vì
mục đích của LTT là thương mại. Tệp `.ee.`/thư mục `.ee` còn bị khoá chặt hơn (Commercial License
riêng, `LICENSE_EE.md`). ⇒ giữ nguyên kết luận `05_N8N_AUDIT.md §8`: **học ý tưởng, không chép dòng
nào.**

---

## 2. Flowise AgentFlow v2 — KHẢO SÁT MỚI

> Kho: `FlowiseAI/Flowise`, bản mới nhất `flowise@3.1.4` (2026-07-29), đọc tại HEAD commit
> `9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb`. Giấy phép: **Apache-2.0** cho mọi thứ NGOÀI
> `packages/server/src/enterprise/` và tệp có ghi chú bản quyền riêng (`IdentityManager.ts`) —
> `CONFIRMED` từ `LICENSE.md`. Mọi tệp đọc trong mục này (`packages/components/nodes/agentflow/*`,
> `packages/server/src/utils/buildAgentflow.ts`) nằm NGOÀI thư mục enterprise ⇒ **Apache-2.0, PORT
> được** (giữ notice bản quyền FlowiseAI, Inc.).

### 2.1 Danh sách node AgentFlow v2

```
packages/components/nodes/agentflow/
  Agent · Condition · ConditionAgent · CustomFunction · DirectReply · ExecuteFlow · HTTP ·
  HumanInput · Iteration · LLM · Loop · Retriever · Start · StickyNote · Tool
```

`CONFIRMED` (liệt kê thư mục). Không phải node kiểu Activepieces/n8n (JS class implement `INode` với
`inputs: INodeParams[]` — kiểu UI nguyên thuỷ: `string|number|boolean|options|asyncOptions|array|json`,
**không có kiểu dữ liệu ở output** — `outputs: INodeOutputsValue[]` chỉ có `{label, name}`, không có
`types[]`). ⇒ Flowise AgentFlow v2 **không có typed port thật** — thấp hơn cả n8n (loại kết nối) và xa
dưới Langflow (kiểu dữ liệu ở output + kiểm ở cạnh).

### 2.2 `$flow.state` — trạng thái chảy xuyên toàn bộ đồ thị

```
packages/components/nodes/agentflow/Interface.Agentflow.ts
  interface IFlowState { key: string; value: string }
packages/server/src/utils/buildAgentflow.ts:97-101
  interface IAgentFlowRuntime { state?: ICommonObject; chatHistory?: IMessage[];
                                 form?: Record<string, any>; webhook?: Record<string, any> }
```

`CONFIRMED`. Cơ chế: node `Start` khai **schema ban đầu** (`startState: IFlowState[]`, mảng
key/value) → runtime làm phẳng thành `ICommonObject` (`options.agentflowRuntime.state`) → **mọi node**
(`HumanInput`, `Loop`, `ExecuteFlow`, `Iteration`, ...) đều nhận `state` này trong `options`, có thể
đọc bằng `{{ $flow.state.key }}` trong expression, và ghi lại qua một mảng input UI lặp lại
**"Update Flow State"** (`{key: asyncOptions từ listRuntimeStateKeys, value: string acceptVariable}`)
— mọi node type có field này tự áp `updateFlowState(state, updates)` rồi trả `state: newState` ra
trong `nodeOutput`. Đây là **truyền tay** (mỗi node output mang state mới), không phải một bảng CSDL
riêng — giống mô hình "biến workflow" của n8n nhưng phạm vi rộng hơn (không chỉ đọc, còn có UI chuẩn
hoá để ghi ở bất kỳ node nào).

`$webhook.*` cũng nằm trong cùng runtime object (`IAgentFlowRuntime.webhook`), resolve bằng
`resolveWebhookRefs()` — regex `{{ $webhook.body.* }}` có chặn path traversal `__proto__` tường minh
(`buildAgentflow.ts:104-118`) — một chi tiết bảo mật đáng chú ý khi LTT viết resolver tương tự.

### 2.3 Human Input — tạm dừng bằng cách GHI DB rồi ĐỢI LƯỢT GỌI API MỚI

```
packages/components/nodes/agentflow/HumanInput/HumanInput.ts (đọc trọn)
packages/server/src/utils/buildAgentflow.ts:1409-1502, 1773-1841 (đọc qua grep có định vị)
```

Cơ chế hai lượt gọi, không phải webhook như n8n:

1. **Lượt 1** (không có `humanInput` trong input): node `HumanInput` sinh mô tả (cố định hoặc bằng
   LLM), trả `nodeOutput` bình thường; **server** phát hiện `reactFlowNode.data.name ===
   'humanInputAgentflow'` (hoặc Agent có `output.isWaitingForHumanInput`), đặt
   `status: 'STOPPED'` cho node đó, đặt **execution state `STOPPED`**, stream sự kiện SSE
   `'STOPPED'` + `humanInputAction` (chứa `startNodeId`), rồi **dừng vòng lặp thi hành**
   (`shouldStop: true`) — ghi nguyên `agentFlowExecutedData` (mảng kết quả từng node) xuống bảng
   `Execution` trong CSDL.
2. **Lượt 2** (client gọi lại API `/prediction` với `humanInput: {type: 'proceed'|'reject',
   startNodeId, feedback}`): server **nạp lại `previousExecution`**, bắt buộc
   `previousExecution.state === 'STOPPED'` (hoặc `ERROR` ngay sau `STOPPED` — cho phép thử lại lỗi),
   nếu không ném lỗi rõ ràng; nếu `startNodeId` không kèm theo, **tự dò ngược** node `STOPPED` cuối
   cùng trong `executionData`; rồi **chạy lại từ `startNodeId`**, tiêm `humanInput` vào input của đúng
   node đó, và **xoá `humanInput` khỏi ngữ cảnh** ngay sau khi node đó tiêu thụ (tránh node
   `HumanInput` khác phía sau vô tình dùng lại).

`CONFIRMED` (đọc trực tiếp cả `HumanInput.ts` lẫn đoạn resume trong `buildAgentflow.ts`).

**So với LTT:** đây là mô hình "resume-bằng-API-call-mới-mang-quyết-định", **không phải
webhook-URL-ký-sẵn** như n8n Wait. Gần với ý tưởng `WF-401` nếu LTT làm waitpoint qua chính API
`/jobs/{id}/resume` thay vì sinh URL riêng — đơn giản hơn để vận hành (không cần lộ URL công khai),
nhưng đòi hỏi client biết gọi lại đúng API, không nhét được vào form/webhook bên thứ ba dễ dàng.

⚠️ Vòng lặp thi hành toàn cục có **hai trần chống-treo** đáng ghi nhận:
`MAX_LOOP_COUNT` (mặc định 10, biến môi trường, áp cho node `Loop`/goto) và
`MAX_ITERATIONS` (mặc định **1000**, biến môi trường `MAX_ITERATIONS`, áp cho **toàn vòng thi hành**
— đếm mọi bước kể cả không phải Loop) — hai trần khác nhau, khác tầng.

### 2.4 Loop / Iteration — KHÔNG phải hai cơ chế lặp thật, mà một goto + một đệ quy

```
packages/components/nodes/agentflow/Loop/Loop.ts       (đọc trọn, 155 dòng)
packages/components/nodes/agentflow/Iteration/Iteration.ts (đọc trọn, 75 dòng)
```

- **`Loop`**: không lặp một khối — nó chỉ output `{ nodeID: <id đã chạy trước đó>, maxLoopCount }`;
  server đọc `nodeID` này và **nhảy ngược về đó** trong hàng đợi thi hành, đếm bằng
  `loopCounts: Map<nodeId, number>`, có `fallbackMessage` khi vượt `maxLoopCount`. Đây là **goto có
  điều kiện dừng**, hint UI còn nhắc *"bật memory ở LLM/Agent phía trước để giữ lịch sử hội thoại"* —
  tức là Loop **không tự lưu trạng thái vòng lặp**, phụ thuộc hoàn toàn vào memory của node khác.
- **`Iteration`**: node chỉ parse một mảng đầu vào (`iterationInput`, JSON string hoặc mảng); các node
  *bên trong khối Iteration* trên canvas được server thực thi bằng **đệ quy trong tiến trình**
  (`buildAgentflow.ts` dùng `iterationContext` + gọi lại hàm thực thi với `isRecursive: true` cho từng
  phần tử, biến `$iteration.value` truy cập phần tử hiện tại) — **tuần tự, không đồng thời**, giống hệt
  kết luận về `SplitInBatches` của n8n (`05_N8N_AUDIT.md §6`, dòng `WF-204`).

⇒ **Xác nhận thêm một hội tụ độc lập cho `WF-201/WF-204`**: ba hệ visual-automation riêng biệt
(Activepieces, n8n, Flowise) — không hệ nào cho ForEach chạy song song trong một lượt. Bằng chứng càng
dày cho quyết định "song song trong một run là bài toán RIÊNG của LTT, không có tiền lệ để chép".

### 2.5 ExecuteFlow (subflow) — gọi lại CHÍNH API HTTP của nó, không phải lời gọi trong tiến trình

```
packages/components/nodes/agentflow/ExecuteFlow/ExecuteFlow.ts (đọc trọn, 280 dòng)
```

`CONFIRMED` — node build `POST {baseURL}/api/v1/prediction/{selectedFlowId}` bằng `axios`
(`secureAxiosRequest`), có `flowise-tool: true` header, `Authorization: Bearer <chatflowApiKey>` từ
credential riêng (`chatflowApi`). Không cho gọi lại chính flow đang chạy (`selectedFlowId ===
options.chatflowid` ⇒ ném lỗi). Trả về text/JSON của response, có thể tiếp tục cập nhật `$flow.state`
qua cùng cơ chế "Update Flow State" ở §2.2.

**Khác biệt kiến trúc đáng ghi vào tài liệu 23 của LTT:** đây là **subflow-qua-self-HTTP-call**, không
phải in-process (n8n `executeWorkflow`) hay đệ quy đồ thị (Langflow `RunFlowComponent`, §3.5). Ưu
điểm: cô lập hoàn toàn (subflow chạy như một request độc lập, tận dụng lại đúng hạ tầng scaling/auth
của chính nó); nhược điểm: **mất transaction chung** (subflow không thấy state runtime của flow cha
trừ khi truyền qua `executeFlowInput`/`overrideConfig` dạng string), thêm một vòng network, và giới
hạn 100s/upload của Cloudflare (luật chết người #8 của LTT) áp trực tiếp lên bước này nếu triển khai
kiểu tương tự.

### 2.6 Bảng chấm nhanh Flowise theo `WF-*`

| ID | Flowise AgentFlow v2 | Ghi chú |
|---|:--:|---|
| WF-101 DAG | ✅ | React Flow nodes/edges, đồ thị thật |
| WF-102 Edge là thực thể | 🟡 | có, nhưng không mang kiểu dữ liệu |
| WF-103 Data/Control edge | ❌ | không phân loại cạnh — mọi cạnh như nhau |
| WF-106 Subworkflow | 🟡 | có (`ExecuteFlow`), nhưng qua self-HTTP-call, không in-process |
| WF-201 Song song | ❌ | vòng thi hành tuần tự (giống n8n) |
| WF-204 ForEach+concurrency | ❌ | `Iteration` = đệ quy tuần tự |
| WF-207 Máy trạng thái | 🟡 | `ExecutionState` (STOPPED/ERROR/...) nhưng ít trạng thái hơn n8n |
| WF-301 Trạng thái = hàng CSDL | 🟡 | `agentFlowExecutedData` là mảng JSON trên **một hàng** `Execution` — vẫn là khối, nhưng nhỏ hơn n8n (mỗi *bước*, không phải cả run, là một entry trong mảng) |
| WF-401 Waitpoint | ⭐ | resume-bằng-API-call-mới, xem §2.3 — đáng học nhất mục Flowise |
| WF-601/602 Artifact | 🟡 | có `artifacts[]`/`fileAnnotations[]` trong output, không có hệ storage đa backend như n8n `binary-data` |
| WF-701 Hệ kiểu cổng | ❌ | không có — thấp nhất trong ba kho mới/cũ đã đọc |

---

## 3. Langflow — KHẢO SÁT MỚI

> Kho: `langflow-ai/langflow`, bản mới nhất `v1.12.2` (2026-09-16), đọc tại HEAD commit
> `5621dcfd84e11108e4cc1ecb0c51f41053c4211c`. Giấy phép: **MIT**, toàn bộ repo kể cả gói lõi tách riêng
> `src/lfx` (không có LICENSE riêng ⇒ thừa kế MIT gốc) — `CONFIRMED`, **cho phép chép mã tự do** (giữ
> notice). Đây là kho **duy nhất trong toàn bộ đợt khảo sát KHÔNG có ràng buộc giấy phép nào** cho
> LTT.

### 3.1 Cấu trúc — lõi thực thi đã tách thành gói riêng `lfx`

Đáng chú ý: Langflow gần đây tách lõi (`graph`, `template`, `inputs`, `custom`, `workflow`,
`checkpoint`...) ra khỏi backend chính (`src/backend/base/langflow`) thành một package Python độc lập
**`lfx`** (`src/lfx`, có `pyproject.toml` riêng, CLI riêng `lfx run`), để chạy standalone không cần
server FastAPI đầy đủ. `langflow.schema.data.Data` giờ chỉ là **re-export** từ `lfx.schema.data`.
`CONFIRMED`. Ý nghĩa cho LTT: một mẫu tách "core thi hành đồ thị" khỏi "server SaaS" đáng cân nhắc nếu
LTT muốn thứ tương tự (ví dụ chạy plan/step engine độc lập với `server/`).

### 3.2 Component contract — Input/Output có KIỂU, không chỉ có UI type

```
src/lfx/src/lfx/template/field/base.py (đọc trọn)
```

`class Input(BaseModel)`: `field_type` (kiểu UI: str/int/bool/...), **`input_types: list[str] | None`**
— danh sách **kiểu dữ liệu luận lý** mà cổng vào này chấp nhận (khác `field_type` là kiểu UI-widget).
`class Output(BaseModel)`: **`types: list[str]`** — danh sách kiểu dữ liệu mà cổng ra này phát ra,
`method: str` (tên hàm Python sinh giá trị), `allows_loop: bool` + `loop_types: list[str] | None` (cổng
ra có thể **là điểm bắt đầu một cạnh vòng lặp**, xem §3.4), `group_outputs: bool` (nhiều output hiển
thị không cần dropdown — dùng cho `HumanInput` nhánh theo lựa chọn, §3.6), `tool_mode: bool` (cổng ra
này có thể trở thành một "tool" cho Agent — xem §3.5).

`CONFIRMED`. Đây là câu trả lời rõ ràng nhất trong cả đợt khảo sát cho "cổng có kiểu dữ liệu, không chỉ
có kiểu kết nối" — mạnh hơn 13-loại-cạnh của n8n (đó là loại **kết nối**, không phải kiểu **dữ liệu**
lưu thông qua cổng).

### 3.3 Kiểm tương thích cạnh theo KIỂU — thật, chạy khi dựng đồ thị

```
src/lfx/src/lfx/graph/edge/base.py (đọc trọn, 260 dòng)
```

```python
TYPE_MIGRATIONS = {"Data": "JSON", "DataFrame": "Table"}   # bảng di trú kiểu qua các version

def types_compatible(output_types, input_types) -> bool:
    # so khớp trực tiếp HOẶC qua di trú, hai chiều
    ...

class Edge:
    def _validate_edge(self, source, target):
        self.source_types = [o for o in source.outputs if o["name"] == self.source_handle.name]
        self.target_reqs = target.required_inputs + target.optional_inputs
        self.valid = any(types_compatible(o["types"], self.target_reqs) for o in self.source_types)
        if self.matched_type is None:
            raise ValueError(f"Edge between {source} and {target} has no matched type.")
```

`CONFIRMED` — cạnh **ném lỗi ngay khi khởi tạo** (`Edge.__init__` gọi `validate_edge` ở cuối) nếu
không có kiểu nào khớp. Có cả nhánh riêng cho **cạnh vòng lặp** (`is_loop_input`, dùng
`target_handle.input_types` đã gộp thêm `loop_types` từ frontend) và một lớp tương thích ngược
(`_legacy_validate_edge`, dùng `base_classes` thay vì `types`, cho flow cũ trước khi có `Output.types`).

⇒ **Ghi vào tài liệu 23/`WF-701` của LTT:** đây là bằng chứng mạnh nhất cho việc "hệ kiểu cổng" khả
thi và đáng làm — Langflow chứng minh nó chạy được ở quy mô hàng nghìn component, bằng một hàm so khớp
tập hợp chuỗi rất đơn giản (`types_compatible`), không cần type system phức tạp.

### 3.4 `CycleEdge` — vòng lặp là CẠNH thật trong đồ thị, không phải goto

```
src/lfx/src/lfx/graph/edge/base.py: class CycleEdge(Edge)
```

`CONFIRMED` — Langflow có hẳn một lớp con `CycleEdge` (đặt `is_cycle = True`, `source.has_cycle_edges
= True`) cho cạnh nối ngược trong một vòng lặp trực quan. Khác hẳn Flowise (`Loop` = goto giả lập bằng
nhảy `nodeID`, §2.4) và n8n (không có loop node có cạnh thật). `resume.py` xác nhận thêm:
`graph.cycle_vertices` được cấu hình riêng, và có ghi chú "without this a resumed Loop flow never
schedules its loop vertex and hangs" — tức là loop-as-real-edge **có cái giá phải trả ở phần
resume/checkpoint** (phải xử lý minh bạch, không tự nhiên đúng).

### 3.5 "Flow as Tool" — biến một flow thành LangChain Tool cho Agent khác gọi

```
src/lfx/src/lfx/base/tools/run_flow.py, flow_tool.py
src/lfx/src/lfx/components/flow_controls/run_flow.py (RunFlowComponent)
src/lfx/src/lfx/components/flow_controls/__init__.py: "RunFlowComponent": "run_flow",
                                                        "SubFlowComponent": "sub_flow"
```

`CONFIRMED` (đọc kết quả `search_code`, chưa đọc trọn `run_flow.py`/`flow_tool.py` — `HIGH`). Có **hai**
cơ chế subflow riêng biệt: `RunFlowComponent` (chạy một flow khác **trong cùng tiến trình**, dùng
`lfx.graph.graph.base.Graph` trực tiếp — khác Flowise §2.5 là self-HTTP-call) và `SubFlowComponent`
(biên dịch một flow thành khối tái dùng). `get_component_toolkit()` (trong
`custom/custom_component/component.py`) bọc một Component/Flow thành LangChain `Tool` — đây chính là
"Flow as Tool" mà đề bài hỏi: một flow con được Agent cha gọi như một tool có schema đầu vào/đầu ra rõ
ràng, không chỉ nối cạnh tĩnh.

### 3.6 Human Input — checkpoint bền vững thật, không phải "ghi khối rồi đợi API gọi lại"

```
src/lfx/src/lfx/graph/checkpoint/schema.py   (đọc trọn, "LE-1440")
src/lfx/src/lfx/graph/checkpoint/resume.py   (đọc trọn)
src/lfx/src/lfx/graph/checkpoint/store.py    (đọc trọn)
src/lfx/src/lfx/components/flow_controls/human_input.py (đọc trọn, "LE-1449")
```

Đây là phần **đáng học nhất của toàn bộ đợt khảo sát Flowise+Langflow**, mô hình gần LTT nhất:

- **`GraphCheckpoint`** (Pydantic): không chỉ lưu output từng vertex mà lưu **toàn bộ sổ sách lập
  lịch** của graph runner tại thời điểm dừng — `run_map`, `run_predecessors`, `vertices_to_run`,
  `vertices_being_run`, `ran_at_least_once`, `run_queue`, `vertices_layers` (các lớp topo đã tính),
  `inactivated_vertices`/`branch_inactivation_sources` (nhánh đã bị `ConditionalRouter` loại bỏ),
  `human_input_decisions` (quyết định đã tiêm cho từng `request_id`), `pause_context`.
- **Serialize theo "wire envelope" gắn nhãn kiểu** (`serialize_value`/`deserialize_value`,
  `_WIRE_KIND = "__lfx_ser__"`): mọi giá trị build ra được bọc `{__lfx_ser__: raw|dict|list|model,
  value: ...}`. Giá trị **không JSON hoá được** (client LLM, handle Tool) suy biến thành `None` một
  cách **CÓ CHỦ Ý, có ghi log**, thay vì crash checkpoint — comment trong code nói thẳng: *"a
  checkpoint must still be writable when one vertex holds e.g. a client handle"*.
- **Khi resume**: `_unbuild_needed_dropped_producers()` chạy một **vòng lặp đến điểm cố định
  (fixpoint)** để tìm đúng tập vertex có giá trị bị rớt (`checkpoint_opaque_dropped_ids`) mà một
  vertex **chưa build** sẽ đọc phải — chỉ những vertex đó bị đánh dấu `built=False` để chạy lại (không
  build lại cả nhánh, tránh gọi lại LLM/tính phí hai lần cho vertex không cần). Bình luận trong code
  giải thích rõ động cơ kinh tế: *"a producer with side effects (an Agent re-bills its LLM and
  re-emits its message)"*.
- **`compute_resume_layer()`**: tính lại đúng "lớp kế tiếp có thể chạy" (predecessor đã build hết,
  chưa bị loại nhánh) bằng một lần duyệt tuyến tính trên vertex đã phục hồi — **không** sort lại toàn
  đồ thị.
- **`request_id` định tuyến quyết định**: `f"{vertex_id}:{graph.run_id}"` — một node HumanInput cụ thể
  trong một lần chạy cụ thể; `resume_graph_with_decision()` tiêm `decision` vào đúng `request_id`,
  un-build đúng vertex đó để nó tự đọc lại quyết định qua `_injected_decision()`.
- **`HumanInput` component** (`LE-1449`): **User Choices tuỳ ý** (không chỉ Approve/Reject — bất kỳ
  nhãn nào, mỗi nhãn thành một `Output` nhánh riêng, `group_outputs=True` để không cần dropdown trên
  canvas), **Timeout** có đơn vị Minutes/Hours/Days + **nhánh Fallback tuỳ chọn** khi hết hạn — nhưng
  code ghi rõ: *"The run stays paused until a response arrives or the server's suspended-run deadline
  expires it"* — tức Timeout ở đây chỉ **định tuyến nhánh nào chạy khi có phản hồi trễ**, KHÔNG tự
  đánh thức run (việc đánh thức theo hạn vẫn là trách nhiệm của lớp server/scheduler bên ngoài).
  `_has_downstream_consumer()`: **không tạm dừng nếu HumanInput không nối ra đâu cả** — tránh treo một
  run vì một quyết định "không đi đến đâu".
- **`CheckpointStore`** là interface trừu tượng (`save/load/delete/load_by_run_id/list_by_session` +
  `save_blob/load_blob` cho blob riêng của agent tool-approval) — có **bản in-memory tham chiếu**
  (dùng cho CLI/standalone) và comment nói rõ *"the durable DB-backed store lands in LE-1441 behind
  this same interface"* — tách contract khỏi backend lưu trữ, đúng mẫu Strategy mà LTT nên theo cho
  `WF-401`.

`CONFIRMED` (đọc trọn cả bốn tệp). **Mức tin cậy về "đã triển khai xong bản DB-backed" là `UNKNOWN`** —
comment ghi rõ "lands in LE-1441", chưa xác minh version DB-backed đã merge vào `v1.12.2` hay còn ở
nhánh khác; điều CHẮC CHẮN là **contract + bản in-memory** đã có trong mã chính.

### 3.7 Component palette / kiến trúc mở rộng

Không đọc sâu registry UI (ngoài phạm vi câu hỏi cốt lõi); từ cấu trúc thư mục
`src/lfx/src/lfx/components/<category>/*.py` (mỗi component là một file/class kế thừa `Component`,
tự khai `inputs`/`outputs`, palette sinh từ quét thư mục theo category) — cùng họ với cách Flowise quét
`packages/components/nodes/**` và n8n quét `packages/nodes-base/nodes/**`. Không có phát hiện khác biệt
đáng ghi ở tầng này so với hai kho kia. `INFERRED` — suy từ cấu trúc thư mục, chưa đọc registry/loader.

### 3.8 Bảng chấm nhanh Langflow theo `WF-*`

| ID | Langflow | Ghi chú |
|---|:--:|---|
| WF-101 DAG | ✅ | đồ thị thật, `graph/graph/base.py::Graph` |
| WF-102 Edge là thực thể | ✅ | `Edge`/`CycleEdge`, khoá theo handle, có kiểm hợp lệ |
| WF-103 Data/Control edge | ❌ | không phân DATA/CONTROL — mọi cạnh mang dữ liệu kiểu hoá |
| WF-106 Subworkflow | ⭐ | HAI cơ chế: `RunFlowComponent` (in-process) + `SubFlowComponent`; còn có Flow-as-Tool |
| WF-201 Song song | ❓ chưa đọc | không nằm trong phạm vi câu hỏi lần này — cần đọc `graph/graph/base.py::run()` để chốt |
| WF-207 Máy trạng thái | ✅ | `VertexStates` (ACTIVE/INACTIVE...), `inactivated_vertices`, `conditionally_excluded_vertices` tường minh |
| WF-301 Trạng thái = hàng CSDL | 🟡 | `GraphCheckpoint` là MỘT bản ghi JSON — vẫn là khối, nhưng thiết kế wire-envelope + fixpoint resume vượt xa n8n/Flowise |
| WF-401 Waitpoint | ⭐⭐ | checkpoint/resume đầy đủ nhất trong cả đợt khảo sát, xem §3.6 |
| WF-701 Hệ kiểu cổng | ⭐ | kiểm kiểu thật ở cạnh, có bảng di trú kiểu — mạnh nhất trong mọi kho đã đọc (kể cả Activepieces/n8n cũ) |

---

## 4. Temporal — bổ sung NGẮN (nguyên tắc áp cho LTT, không lặp `10_TEMPORAL_AUDIT.md`)

Không đọc lại mã Temporal (đã có audit đủ sâu). Chỉ chốt lại **ba nguyên tắc** mà cả Flowise lẫn
Langflow (vừa đọc) đều **KHÔNG** làm được nhưng Temporal làm được, để LTT biết mình đang thiếu gì nếu
muốn học Temporal thay vì học nhóm visual-automation cho phần bền vững:

1. **Workflow vs Activity là ranh giới BẮT BUỘC, cưỡng chế bởi mô hình lập trình** (Workflow code phải
   tất định, mọi I/O/side-effect phải qua Activity) — cả Flowise và Langflow đều để component tự do
   gọi I/O trực tiếp trong hàm build; không có ranh giới tất định/không-tất định nào được cưỡng chế.
2. **Event History là nguồn sự thật duy nhất, replay để phục hồi state** — khác hẳn
   `GraphCheckpoint`/`ExecutionData` của Langflow/n8n/Flowise: những hệ đó lưu **snapshot cuối cùng**
   (đủ để resume tiếp, không đủ để trả lời "chuyện gì đã xảy ra ở bước thứ k" nếu không lưu riêng log).
   Checkpoint của Langflow (§3.6) là **snapshot + sổ lập lịch**, không phải log sự kiện đầy đủ.
3. **Retry Policy mặc định + Idempotency khuyến nghị theo Activity, không theo Workflow**: Temporal đặt
   `maximumAttempts`/`backoffCoefficient` **mỗi Activity**, và khuyến nghị Activity **tự thân
   idempotent** (dùng `idempotency key` do Workflow sinh, thường là `workflow_id + activity_seq`) vì
   một Activity có thể chạy lại sau khi kết quả đã tới nhưng ACK bị mất mạng. LTT có `Job.attempts`
   nhưng nên xác nhận: mỗi Job/Task LTT (đặc biệt bước GPU) có tự thân idempotent theo đúng nghĩa này
   không, hay chỉ chống trùng ở tầng `dedupe_key` (đã ghi ở `05_N8N_AUDIT.md §3.5` là còn hở).

`HIGH` — tổng hợp từ nguyên tắc đã xác nhận ở `10_TEMPORAL_AUDIT.md`, không đọc mã mới trong phiên này.

---

## 5. BẢNG CHẤM ĐIỂM 0–5 (n8n · Flowise · Langflow) — Activepieces để agent khác

Thang: 0 = không có · 1 = có dấu vết/một phần rất hẹp · 2 = có nhưng thô sơ/có lỗ hổng rõ · 3 = có, đạt
mức dùng được · 4 = tốt, có chi tiết đáng học · 5 = xuất sắc, đáng chép ý tưởng nguyên vẹn.

| Tiêu chí | n8n | Flowise v2 | Langflow | Lý do (ngắn) |
|---|:--:|:--:|:--:|---|
| Node contract | 4 | 2 | 4 | n8n: `INodeType` đầy đủ version/credentials/webhooks. Flowise: JS class thô, không kiểu output. Langflow: `Component` + `Input`/`Output` Pydantic có kiểu. |
| Typed ports | 2 | 0 | 5 | n8n chỉ có *loại kết nối* (13 loại, không phải kiểu dữ liệu). Flowise không có gì. Langflow kiểm kiểu thật ở cạnh (§3.3), có bảng di trú. |
| Flow control (if/switch) | 4 | 3 | 3 | n8n IF/Switch nhiều cổng ra, mature. Flowise `Condition`/`ConditionAgent` node. Langflow `ConditionalRouter`-style (suy từ `inactivated_vertices`, chưa đọc mã node). |
| Loop | 2 | 1 | 3 | n8n `SplitInBatches` tuần tự trong tiến trình. Flowise `Loop` chỉ là goto lùi, không có state riêng (§2.4). Langflow có `CycleEdge` — vòng lặp là cạnh đồ thị thật (§3.4), tuy vẫn tuần tự trong một lượt build. |
| Subworkflow | 4 | 3 | 5 | n8n `executeWorkflow` in-process, mature. Flowise qua self-HTTP-call — hoạt động nhưng mất transaction chung (§2.5). Langflow có CẢ hai cơ chế in-process + Flow-as-Tool (§3.5). |
| Wait/Waitpoint | 3 | 4 | 5 | n8n: `waitTill` mức RUN, 4 chế độ resume, ngưỡng 65s đáng học (§1.3). Flowise: resume-bằng-API-call rõ ràng (§2.3). Langflow: checkpoint đầy đủ nhất, fixpoint resume, User Choices tuỳ ý (§3.6). |
| Trigger | 5 | 3 | 2 | n8n: webhook/cron/poll/trigger-node rất phong phú (audit cũ). Flowise: chủ yếu API-invoke + webhook đơn giản. Langflow: chủ yếu API/MCP-invoke, ít trigger gốc. |
| Expression | 4 | 2 | 2 | n8n: ba thế hệ, nay cách ly V8 isolate thật (§1.1) — mạnh nhất. Flowise: `{{ output }}`/`acceptVariable` đơn giản, không sandbox riêng biệt rõ. Langflow: chủ yếu truyền giá trị qua cổng có kiểu, ít cần expression string. |
| Connector (tích hợp bên thứ ba) | 5 | 4 | 4 | n8n có hàng nghìn node tích hợp, mature nhất thị trường. Flowise/Langflop đều tập trung AI/LLM stack, ít connector nghiệp vụ ngoài AI. |
| Credentials | 4 | 2 | 2 | n8n: envelope encryption hai tầng + `authenticate`/`test` (§1.2). Flowise: có credential nhưng đơn giản hơn (chưa đọc sâu mã hoá). Langflow: chủ yếu biến môi trường/Global Variables, ít mô hình credential riêng biệt theo loại. |
| Retries | 3 | 2 | 2 | n8n: vòng lặp trong bộ nhớ (không bền, `05 §2.4`). Flowise/Langflow: không thấy cơ chế retry cấp-node tường minh trong phần đã đọc — `UNKNOWN`, có thể nằm ở tầng LangChain bên dưới. |
| Durability (bền qua khởi động lại) | 2 | 3 | 5 | n8n: khối `text` một cột (`05 §3`). Flowise: mảng JSON theo bước trên một hàng, nhỏ hạt hơn n8n. Langflow: `GraphCheckpoint` có sổ lập lịch đầy đủ + wire-envelope + fixpoint resume. |
| Versioning | 4 | 3 | 3 | n8n: `WorkflowPublishedVersion` ghim bằng bản sao (`05 §3.3`). Flowise/Langflow: có version flow nhưng chưa đọc sâu cơ chế ghim. |
| Observability | 3 | 3 | 3 | Cả ba đều có execution log UI + SSE streaming (Flowise/Langflow) hoặc polling (n8n) — không có hệ nào có tracing phân tán sâu như Temporal. |
| Human input | 2 | 4 | 5 | n8n: phải tự ráp Wait+webhook/`sendAndWait` node riêng lẻ. Flowise: node `HumanInput` dựng sẵn, resume rõ ràng (§2.3). Langflow: `HumanInput` + checkpoint bền, User Choices tuỳ ý, fallback timeout (§3.6). |
| Agent workflow (multi-agent, tool routing) | 2 | 4 | 5 | n8n: AI nodes là bổ sung (12 loại cạnh AI, `05 §1.3`), không phải trọng tâm. Flowise: AgentFlow v2 thiết kế riêng cho agent (Agent/ConditionAgent/Tool node). Langflow: Component contract + Flow-as-Tool + checkpoint HITL là bộ ba mạnh nhất cho agent workflow thật. |
| Sandbox (expression/code người dùng) | 5 | 2 | 2 | n8n: `isolated-vm` cách ly V8 thật (§1.1) — duy nhất trong ba kho có cách ly tiến trình thật. Flowise/Langflow: chạy code Python/JS người dùng viết (CustomFunction) trong cùng tiến trình server — rủi ro cao hơn, chưa đọc sâu để xác nhận có sandbox riêng. |
| Extensibility (SDK viết node/component mới) | 4 | 3 | 4 | n8n: `@n8n/create-node`, quy ước version rõ (`05 §6`). Flowise: implement `INode`, ít tài liệu hoá hơn. Langflow: kế thừa `Component`, contract Input/Output rõ ràng, tách gói `lfx` để dùng ngoài server. |

**Ghi chú đọc bảng:** cột **Sandbox** và **Retries** của Flowise/Langflow ở mức 2 chủ yếu vì **chưa đọc
đủ sâu** để xác nhận (không phải chắc chắn là 0) — nếu cần chốt cho quyết định kiến trúc, đọc thêm
`CustomFunction` node (Flowise) và cơ chế retry trong `lfx/graph/graph/base.py` (Langflow) trước khi
dùng con số này làm căn cứ cuối cùng.

---

## 6. BẢNG TÁI DÙNG — ADOPT / PORT / REFERENCE / REJECT

Định nghĩa (theo yêu cầu đề bài): **ADOPT** = lấy Ý TƯỞNG, tự viết lại hoàn toàn bằng ngôn ngữ/kiến
trúc của LTT. **PORT** = có thể CHÉP MÃ (giấy phép cho phép), sửa lại cho khớp LTT. **REFERENCE** = giữ
làm tài liệu tham chiếu khi thiết kế, không lấy gì cụ thể ngay. **REJECT** = không phù hợp F1-F4 của
LTT hoặc giấy phép chặn.

### n8n (Sustainable Use License — ⛔ KHÔNG PORT được, mọi dòng dưới đây là ADOPT hoặc REFERENCE)

| Hạng mục | Quyết định | Vì sao |
|---|---|---|
| Envelope encryption cho credential (DEK + khoá instance) | **ADOPT** | Mô hình mã hoá hai tầng chuẩn ngành, LTT tự viết bằng Python/`cryptography`, không cần chép dòng nào để học ý tưởng. |
| Ngưỡng "chờ ngắn hơn chu kỳ quét thì đừng ghi DB" (Wait §1.3) | **ADOPT** | Một hằng số + một `if`, áp trực tiếp vào bất kỳ thiết kế waitpoint nào của LTT. |
| Cách ly expression bằng `isolated-vm` (V8 isolate thật) | **REFERENCE** | Chỉ liên quan NẾU LTT quyết định cho phép expression người dùng nhập chạy trên server — hiện chưa có yêu cầu đó trong `02`. Ghi lại để không tái phát minh sai (đừng dùng `eval`/`vm` trần). |
| Error workflow tách biệt trạng thái `waiting` khỏi `error` | **ADOPT** | Quy tắc đơn giản, tránh false-positive khi LTT có node chờ (waitpoint) và cũng có error-workflow/thông báo lỗi. |
| 13 loại cạnh AI ("cạnh tiêm năng lực") | **ADOPT** (đã ghi trong `05_N8N_AUDIT.md §7`) | Không lặp lại — xem tài liệu đó. |

### Flowise AgentFlow v2 (Apache-2.0 ngoài `enterprise/` — ✅ PORT được, giữ notice)

| Hạng mục | Quyết định | Vì sao |
|---|---|---|
| Mô hình resume-bằng-API-call-mới cho Human Input (§2.3) | **ADOPT** | Ý tưởng tốt (không cần lộ URL công khai), nhưng cấu trúc dữ liệu `IHumanInput`/`agentFlowExecutedData` gắn chặt vào ORM/Interface riêng của Flowise — viết lại theo schema Postgres của LTT nhanh hơn là chuyển đổi mã. |
| `resolveWebhookRefs()` — chặn `__proto__`/`constructor`/`prototype` khi resolve path động bằng `lodash.get` | **PORT** | Đoạn regex + kiểm tra ngắn (`buildAgentflow.ts:104-118`), tự chứa, không phụ thuộc phần còn lại của Flowise — copy thẳng logic (viết lại bằng Python nếu LTT dùng `jsonpath`/`get` kiểu Python, nhưng LÀ ứng viên PORT nếu LTT có tầng Node.js nào chạm tới cấu trúc tương tự). |
| Hai trần chống-treo tách tầng (`MAX_LOOP_COUNT` cho goto-loop, `MAX_ITERATIONS` cho toàn vòng thi hành) | **ADOPT** | Ý tưởng "hai trần khác tầng" đáng học; giá trị số (10, 1000) không có ý nghĩa gì với `F4` của LTT (bước 20 phút GPU) — LTT cần trần thấp hơn nhiều hoặc theo ngân sách chi phí (`WF-501`), không theo số bước. |
| `Loop` = goto lùi không lưu state riêng | **REJECT** | Đúng như audit n8n đã kết luận cho `SplitInBatches`: mô hình "lặp không có state runner riêng, dựa vào memory của node khác" quá mong manh cho `F4` (một lần lặp lỗi giữa chừng = mất tiền GPU không rõ nguyên nhân). |
| ExecuteFlow qua self-HTTP-call | **REFERENCE** | Đáng ghi vào tài liệu 23 như MỘT lựa chọn kiến trúc hợp lệ cho `WF-106` (cô lập hoàn toàn, tận dụng lại chính API công khai), đối lập với in-process — nhưng không phải khuyến nghị mặc định vì mất transaction chung và cộng thêm một vòng network trên đường găng GPU. |
| "Update Flow State" — array-input chuẩn hoá xuất hiện lặp lại trên MỌI node cần ghi state | **ADOPT** | Mẫu UI tốt: thay vì mỗi node tự định nghĩa cách ghi biến, dùng một field-type dùng chung (`{key: asyncOptions, value: string}`) — áp được cho canvas LTT nếu `WF-1xx` cần biến workflow do người dùng đặt tên. |

### Langflow (MIT toàn repo kể cả `lfx` — ✅ PORT được, giấy phép thoáng nhất trong cả đợt khảo sát)

| Hạng mục | Quyết định | Vì sao |
|---|---|---|
| `types_compatible()` + bảng `TYPE_MIGRATIONS` (§3.3) | **PORT** | ~15 dòng Python thuần, không phụ thuộc gì ngoài hai `dict`/`list` tham số — copy gần như nguyên văn, đổi tên kiểu theo hệ kiểu cổng LTT sẽ chọn (`DATA|CONTROL|RESOURCE` theo đề xuất ở `05_N8N_AUDIT.md §7`, hoặc kiểu chi tiết hơn nếu LTT theo hướng Langflow). |
| `GraphCheckpoint` schema + wire-envelope serialize/deserialize (§3.6, `schema.py`) | **ADOPT** (không PORT trực tiếp) | Ý tưởng (đặc biệt "giá trị không serialize được suy biến thành None có chủ ý, có log, không crash checkpoint") RẤT đáng học, nhưng cấu trúc gắn chặt vào `Vertex`/`RunnableVerticesManager` nội bộ của `lfx` — viết lại theo mô hình `Job`/`AgentRun.checkpoint` hiện có của LTT nhanh và an toàn hơn map 1-1. |
| `_unbuild_needed_dropped_producers()` — fixpoint re-run chỉ đúng tập vertex bị ảnh hưởng khi resume | **ADOPT** | Đây là lời giải cho một bài toán LTT SẼ gặp khi `WF-401` có nhiều waitpoint trong một run: đừng build lại cả đồ thị, chỉ build lại đúng nhánh phụ thuộc giá trị không phục hồi được. Thuật toán (vòng lặp đến điểm cố định) tự viết lại dễ, ~30 dòng. |
| `CheckpointStore` ABC (`save/load/delete/load_by_run_id/list_by_session` + `save_blob/load_blob`) | **PORT** (làm interface tham chiếu) | Interface trừu tượng ngắn, sạch, đúng mẫu Strategy — có thể chép nguyên chữ ký hàm (đổi `async def` Python giữ nguyên nếu LTT cũng Python) rồi viết bản Postgres-backed của LTT implement nó. |
| `CycleEdge` — vòng lặp là cạnh đồ thị thật | **ADOPT** | Ý tưởng "loop = cạnh có `is_cycle=True`, xử lý minh bạch ở resume" mạnh hơn goto ẩn của Flowise; nhưng lớp `CycleEdge`/`honor()` gắn với mô hình `built_object`/`built_result` riêng của Langflow — viết lại theo state machine bước của LTT. |
| `HumanInput` — User Choices tuỳ ý + `group_outputs` + Fallback-on-timeout KHÔNG tự đánh thức | **ADOPT** | Thiết kế UX tốt (đặc biệt điểm "Timeout không tự resume, chỉ định tuyến nhánh khi có phản hồi trễ — server/scheduler ngoài chịu trách nhiệm đánh thức thật") — khớp đúng kỳ vọng `WF-401/402` của LTT (waitpoint tách khỏi bộ quét đánh thức). Component cụ thể (`lfx.custom.Component`) gắn với runtime Langflow — không PORT trực tiếp được vào Python thuần của LTT nếu không kéo theo `lfx` làm dependency (không khuyến nghị — quá nặng chỉ để lấy một node). |
| `request_id = f"{vertex_id}:{run_id}"` định tuyến quyết định HITL | **PORT** | Một dòng, tự chứa, áp thẳng được cho khoá waitpoint của LTT (`f"{step_id}:{run_id}"`). |
| Tách lõi thi hành thành gói `lfx` độc lập khỏi server SaaS | **REFERENCE** | Đáng cân nhắc dài hạn cho LTT (`platform_core/workflow/` độc lập khỏi `server/`) nhưng KHÔNG phải việc của `WF-*` giai đoạn này — ghi vào `docs/architecture` làm ghi chú tương lai, không đưa vào quyết định V2 ngay. |

### Temporal (bổ sung, không lặp `10_TEMPORAL_AUDIT.md`)

| Hạng mục | Quyết định | Vì sao |
|---|---|---|
| Ranh giới Workflow (tất định) / Activity (I/O) cưỡng chế bởi SDK | **REFERENCE** | Đúng nguyên tắc LTT nên noi theo cho `plan.steps` (tách "quyết định luồng" khỏi "gọi GPU/API ngoài"), nhưng Temporal cưỡng chế bằng SDK/ngôn ngữ lập trình đặc thù — LTT không viết bằng Temporal SDK nên chỉ lấy được NGUYÊN TẮC, không có mã để soi. |
| Idempotency theo Activity (không theo Workflow) | **ADOPT** | Đối chiếu trực tiếp với lỗ hổng `dedupe_key` đã ghi ở `05_N8N_AUDIT.md §3.5` — xác nhận thêm từ góc nhìn Temporal rằng đơn vị idempotent đúng là **bước** (Job), không phải **cả run**. |

---

## 7. GIỚI HẠN CỦA KHẢO SÁT NÀY (đọc trước khi dùng để quyết định kiến trúc)

- **Chưa đọc**: cơ chế song song trong một lượt build của Langflow (`graph/graph/base.py::run`/`step`)
  — bảng ở §3.8 để trống ô này, đừng suy diễn từ các ô khác.
- **Chưa đọc**: `CustomFunction` (Flowise) và cơ chế chạy code người dùng của Langflow — cột Sandbox ở
  bảng §5 là ước lượng thận trọng (2/5), không phải kết luận đã xác minh.
- **Chưa xác nhận**: liệu bản DB-backed của `CheckpointStore` (Langflow, "LE-1441") đã có trong
  `v1.12.2` hay còn ở nhánh riêng — chỉ xác nhận chắc chắn phần **contract + bản in-memory**.
- Mọi trích dẫn mã đều kèm đường dẫn tệp + commit SHA để tự tra lại; không có trích dẫn nào dựa trên
  suy đoán từ tên biến mà không đọc thân hàm, trừ các chỗ đã gắn nhãn `INFERRED`/`UNKNOWN` tường minh.
