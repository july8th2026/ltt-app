# 04 — KHẢO SÁT MÃ NGUỒN: ACTIVEPIECES

> **Kho:** `activepieces/activepieces` · **tag** `0.90.2` ·
> **commit** `fad84c1a58a596d5d0dc1a2f043104f8a4df3af8` · 2026-09-04
> **Giấy phép:** MIT Expat, **trừ** `packages/ee/` và
> `packages/server/api/src/app/ee` (giấy phép riêng).
> **Phân loại:** *Visual Automation*.
>
> Mọi khẳng định dưới đây gắn với **đường dẫn tệp + tên hàm** trong chính bản
> clone đó. Không trích README làm bằng chứng kiến trúc.

---

## 0. KẾT LUẬN NGẮN

Activepieces **không phải một workflow engine dạng đồ thị**. Nó là một **trình
thông dịch cây, một luồng, chạy trọn một lượt trong một tiến trình**, giữ toàn
bộ trạng thái trong RAM rồi tuần tự hoá ra **một tệp blob** để tạm dừng/khôi
phục.

Với 41 yêu cầu của LTT (tài liệu 02), Activepieces **trượt phần lớn các yêu cầu
lõi** — nhưng nó có **một thứ xuất sắc mà LTT thiếu nhất**, và thứ đó nằm gọn ở
vùng MIT, tách rời, có bảng CSDL riêng, có thể học nguyên vẹn:

| | |
|---|---|
| 🔴 Trượt | đồ thị · edge · song song · ForEach đồng thời · trạng thái dạng hàng · chi phí |
| ⭐ Xuất sắc | **Waitpoint + Barrier** — đúng `WF-401` và `WF-203`, thiết kế tốt hơn thứ tôi định đề xuất |
| 🟡 Đáng học | **di trú lược đồ 24 bước, lười, có sao lưu trước khi di trú** |

⭐ **Một câu đáng nhớ:** Activepieces trả lời câu hỏi *"chờ như thế nào"* rất
hay, và trả lời câu hỏi *"chạy song song như thế nào"* bằng cách **không chạy
song song bao giờ**.

---

## 1. MÔ HÌNH ĐỒ THỊ — 🔴 KHÔNG PHẢI ĐỒ THỊ

### 1.1 Bằng chứng

**Khẳng định:** *Flow của Activepieces là một CÂY đệ quy, không phải đồ thị.
Không tồn tại thực thể cạnh.*

```
kho     : activepieces @ fad84c1a
tệp     : packages/core/execution/src/lib/flows/actions/action.ts
kiểu    : FlowAction  (dòng ~338-343)
```

```ts
export type FlowAction =
  | (BaseActionProps & { type: CODE,          settings, nextAction?: FlowAction,
                         continueOnFailureBranches?: ContinueOnFailureBranches })
  | (BaseActionProps & { type: PIECE,         settings, nextAction?: FlowAction,
                         continueOnFailureBranches?: ContinueOnFailureBranches })
  | (BaseActionProps & { type: LOOP_ON_ITEMS, settings, nextAction?: FlowAction,
                         firstLoopAction?: FlowAction })
  | (BaseActionProps & { type: ROUTER,        settings, nextAction?: FlowAction,
                         children: (FlowAction | null)[] })
```

**Điều này chứng minh:**
- `nextAction` là **con trỏ một chiều** ⇒ danh sách liên kết, không phải cạnh.
- Rẽ nhánh chỉ có ba hình thức **lồng nhau**: `children[]` (router),
  `firstLoopAction` (loop), `continueOnFailureBranches` (lỗi).
- **Không có mảng `edges`.** Grep toàn `packages/core/execution/src/lib/flows`
  không có thực thể cạnh nào.
- Một node có **đúng một cha**. Không có fan-in. Không có nhiều cha.

`CONFIRMED`

### 1.2 Hệ quả trực tiếp

| Đề bài | Activepieces |
|---|---|
| TEST 3 — Join (`B,C → D`) | **Không biểu đạt được.** Hai nhánh router hợp lại *ngầm* qua `nextAction` của chính router, không phải một node join |
| Nhiều cha | không |
| Fan-in dữ liệu | không |
| Subgraph trong cùng version | không |

⚠️ **Bẫy nhận thức cần nêu rõ:** giao diện Activepieces *trông như* một canvas
đồ thị. Nó **không** là. Canvas được **vẽ ra từ cây**, và người dùng không kéo
được một cạnh tuỳ ý. Đây đúng lớp lỗi mà tài liệu 03 §7 quy tắc 2 cảnh báo:
đừng suy kiến trúc từ giao diện.

### 1.3 Điều đó nói gì cho LTT

LTT **đã** có DAG thật (`after`/`after_error` + nhiều cha, 01 §4.2). Về mô hình
đồ thị, **LTT đang ở phía mạnh hơn.** Không có gì để học ở đây, và có một thứ
để **không** bắt chước: bỏ đồ thị để lấy cây đổi lại sự đơn giản của trình
thông dịch.

---

## 2. THI HÀNH — 🔴 MỘT LUỒNG, TUẦN TỰ TUYỆT ĐỐI

### 2.1 Bằng chứng #1 — vòng lặp chính

```
tệp  : packages/server/engine/src/lib/handler/flow-executor.ts
hàm  : flowExecutor.execute()
```

```ts
while (!isNil(currentAction)) {
    const handler = this.getExecutorForAction(currentAction.type)
    flowExecutionContext = await handler.handle({ action: currentAction,
                                                  executionState: flowExecutionContext, ... })
    previousAction = currentAction
    currentAction  = currentAction.nextAction
}
```

Một `await` mỗi lượt, `flowExecutionContext` được **luồn qua** tuần tự. Không có
`Promise.all`, không có hàng đợi nội bộ, không có worker pool. `CONFIRMED`

### 2.2 Bằng chứng #2 — 🔴 nhánh Router chạy TUẦN TỰ, kể cả `EXECUTE_ALL_MATCH`

```
tệp  : packages/server/engine/src/lib/handler/router-executor.ts
hàm  : handleRouterExecution()
```

```ts
for (let i = 0; i < resolvedInput.branches.length; i++) {
    const condition = routerOutput.output?.branches[i].evaluation
    if (!condition) continue
    executionState = await flowExecutor.execute({          // ← await TRONG vòng for
        action: action.children[i], executionState, constants,
    })
    const shouldBreakExecution = executionState.verdict.status !== FlowRunStatus.RUNNING
        || routerExecutionType === RouterExecutionType.EXECUTE_FIRST_MATCH
    if (shouldBreakExecution) break
}
```

**Điều này chứng minh:** ngay cả `EXECUTE_ALL_MATCH` — cái tên gợi ý *"chạy mọi
nhánh khớp"* — vẫn chạy chúng **lần lượt**, và `executionState` bị luồn tuần tự
nên **không thể** song song hoá mà không viết lại. `CONFIRMED`

⭐ Đây chính là ví dụ §26 của đề bài (*"Router branches execute sequentially"*),
và nó **đúng** ở đây — nhưng phải đọc mã mới biết, vì tên hằng số nói ngược.

### 2.3 Bằng chứng #3 — 🔴 Loop cũng tuần tự, và **không có tham số đồng thời**

```
tệp  : packages/server/engine/src/lib/handler/loop-executor.ts
hàm  : loopExecutor.handle()
```

```ts
for (let i = 0; i < resolvedInput.items.length; ++i) {
    ...
    newExecutionContext = await flowExecutor.execute({ action: firstLoopAction, ... })
}
```

Và lược đồ cấu hình của loop **chỉ có một trường**:

```
tệp: packages/core/execution/src/lib/flows/actions/action.ts
LoopOnItemsActionSettings = z.object({ ...commonActionSettings, items: z.string() })
```

**Không có `concurrency`. Không có `maxItems`. Không có `on_item_error`.**
`CONFIRMED`

⇒ Với `WF-204` của LTT (ForEach có concurrency, `max_items` hữu hạn bắt buộc,
thử lại một phần tử), Activepieces **không đóng góp gì**.

⭐ **Một điểm sáng nhỏ trong đó:** loop **khôi phục được giữa chừng**.
`previousStepOutput`, `stepOutput.hasIteration(i)`, `addIteration()` cho phép
chạy lại một loop dở mà không lặp lại vòng đã xong — đúng nửa sau của `WF-204`.

### 2.4 Bảng kiểm 10 phép thử của đề bài §8

| # | Phép thử | Activepieces | Bằng chứng |
|---|---|---|---|
| 1 | Tuyến tính `A→B→C` | ✅ | `nextAction` |
| 2 | **Song song** | ❌ **tuần tự** | `router-executor.ts` §2.2 |
| 3 | **Join `B,C→D`** | ❌ không biểu đạt được | không có cạnh §1.1 |
| 4 | Điều kiện | ✅ | Router + 22 toán tử |
| 5 | Nhánh lỗi | ✅ | `continueOnFailureBranches` |
| 6 | **Loop 100 phần tử, đồng thời 4** | ⚠️ loop có, **đồng thời không** | §2.3 |
| 7 | **Chờ việc ngoài 10 phút** | ⭐ **có, làm tốt** | §3 |
| 8 | Giết worker giữa chừng | ⚠️ khôi phục từ **blob** | §4 |
| 9 | Workflow con | ✅ | `parentRunId`, `failParentOnFailure` |
| 10 | Artifact lớn | ❌ | trạng thái là blob có trần MB, §4.3 |

---

## 3. ⭐ WAITPOINT — THỨ ĐÁNG GIÁ NHẤT TRONG KHO NÀY

Đây là lý do tôi đọc Activepieces trước tiên (tài liệu 03 §9), và nó xứng đáng.

### 3.1 Nó có thật, ở tầng CSDL

```
tệp: packages/server/api/src/app/waitpoints/waitpoint-entity.ts
     packages/server/api/src/app/waitpoints/waitpoint-signal-entity.ts
di trú: .../migration/postgres/1775747638323-AddWaitpointTable.ts
        .../migration/postgres/1821000000000-AddWaitpointSignals.ts
```

**Hai bảng thật**, không phải một kiểu TypeScript:

```
waitpoint         flowRunId · projectId · type · status · resumeDateTime
                  responseToSend(jsonb) · workerHandlerId · httpRequestId
                  version(V0|V1) · stepName · resumePayload(jsonb)
                  sealed(bool) · policy(jsonb)

waitpoint_signal  waitpointId · projectId · status · refId
                  sequence · label · result(jsonb)
```

### 3.2 🔴 Ba chi tiết chỉ số hoá mà LTT nên chép nguyên

```ts
indices: [
  { name: 'idx_waitpoint_flow_run_id_step_name',
    columns: ['flowRunId', 'stepName'], unique: true },              // ①

  { name: 'idx_waitpoint_pending_resume_date_time',
    columns: ['resumeDateTime'],
    where: '"status" = \'PENDING\' AND "resumeDateTime" IS NOT NULL' }, // ②
]
```

① **UNIQUE `(flowRunId, stepName)`** — mỗi bước trong mỗi lượt chạy có **đúng
một** waitpoint. Đây là *idempotency được cưỡng chế bằng ràng buộc CSDL*, không
phải bằng mã cẩn thận. Đúng khuôn `ExecutionLease` UNIQUE(resource, slot) mà
LTT đã dùng đúng ở chỗ khác.

② **Index BỘ PHẬN cho bộ quét hết hạn.** Chỉ đánh chỉ mục những dòng đang chờ
*và* có mốc thời gian. Bộ quét delay đọc đúng những dòng đến hạn thay vì quét cả
bảng.

⭐ **Đây chính là câu trả lời cho `M2` của LTT** (*"một run chờ 60 phút phải tốn
O(1) câu SQL"*): không ai đi hỏi từng run cả; **một** truy vấn theo index bộ
phận tìm mọi waitpoint đến hạn trên toàn hệ thống.

③ Và `waitpoint_signal` có `UNIQUE (waitpointId, sequence) WHERE sequence IS NOT NULL`
— khử trùng tín hiệu đến hai lần.

### 3.3 Chính sách barrier — chính là `WF-203` của LTT

```
tệp: packages/core/execution/src/lib/flow-run/waitpoint/index.ts
hàm: shouldReleaseBarrier()
```

```ts
export function shouldReleaseBarrier({ policy, sealed, counts }): boolean {
    if (policy?.releaseOnFirstFailure === true &&
        UNFAVOURABLE_SIGNAL_STATUSES.some(s => countOf({ counts, status: s }) > 0)) return true
    if (!isNil(policy?.requiredSuccesses) &&
        countOf({ counts, status: SUCCEEDED }) >= policy.requiredSuccesses)          return true
    if (!sealed) return false
    return countOf({ counts, status: PENDING }) === 0
}
```

Đọc ra ba ngữ nghĩa join **trong 6 dòng**:

| LTT gọi là | Activepieces biểu đạt bằng |
|---|---|
| `N_OF_M` | `policy.requiredSuccesses = N` |
| `FIRST_COMPLETE` (thất bại) | `policy.releaseOnFirstFailure = true` |
| `ALL` | `sealed = true` và không còn `PENDING` |
| `ANY` | `requiredSuccesses = 1` |

⭐ **`sealed` là khái niệm tôi đã bỏ sót khi viết `WF-203`.** Nó phân biệt
*"chưa đủ tín hiệu"* với *"sẽ không còn tín hiệu nào nữa"*. Không có nó thì
`ALL` **không định nghĩa được** khi số nhánh là động (fan-out theo dữ liệu chạy).
Tôi sẽ bổ sung vào `24_TARGET_DATA_MODEL.md`.

### 3.4 `NOT_DISPATCHED` — một trạng thái tín hiệu đáng học riêng

```ts
export enum BarrierSignalStatus {
    PENDING, SUCCEEDED, FAILED, REJECTED, CANCELED, NOT_DISPATCHED,
}
export const UNFAVOURABLE_SIGNAL_STATUSES = [FAILED, REJECTED, CANCELED, NOT_DISPATCHED]
```

`NOT_DISPATCHED` = *"tín hiệu này lẽ ra phải được gửi, nhưng chưa bao giờ được
gửi"*. Không có nó thì một nhánh chết trước khi kịp báo cáo sẽ **treo barrier
vĩnh viễn** — và không ai biết vì sao.

Đây họ hàng gần với `provider_state = ambiguous` của LTT: **đặt tên cho cái
không biết, thay vì để nó thành im lặng.** `HIGH`

### 3.5 Ba loại waitpoint, và điều CÒN THIẾU

```ts
type: z.enum(['DELAY', 'WEBHOOK', 'BARRIER'])
```

So với `WF-401` của LTT (`DELAY | EXTERNAL_JOB | WEBHOOK | HUMAN | CHILD_RUN |
EVENT | SCHEDULE`):

- ✅ `DELAY`, `WEBHOOK`, và `BARRIER` (LTT chưa nghĩ tới, nhưng nó gộp được
  `CHILD_RUN` và fan-in động).
- ❌ **không có `EXTERNAL_JOB`** — vì Activepieces không có khái niệm job GPU
  chạy ở nơi khác. Đây chính là chỗ LTT phải tự thiết kế, không mượn được.
- `HUMAN` được biểu đạt bằng `WEBHOOK` + `resumeUrl`/`confirmUrl` — gọn, và
  LTT dùng lại được cho `WF-803`.

---

## 4. BỀN VỮNG — 🔴 TRẠNG THÁI LÀ MỘT BLOB, KHÔNG PHẢI HÀNG

### 4.1 Bằng chứng

```
tệp: packages/server/api/src/app/flows/flow-run/flow-run-service.ts
```

```ts
const logsFileId = apId()                                   // dòng ~323, ~613
...
const stateFile = await readLogsFile(log, flowRun.logsFileId, flowRun.projectId)  // ~454, ~483
...
data: await logSerializer.serialize(outputFile)             // ~732
...
const data: ExecuteFlowJobData = params.executionType === ExecutionType.RESUME ? ... // ~640
```

**Cơ chế:** toàn bộ đầu ra của mọi bước được tuần tự hoá thành **một tệp**
(`logsFileId`); khi `RESUME`, tệp được đọc lại và nạp vào RAM, rồi trình thông
dịch chạy tiếp. `CONFIRMED`

### 4.2 Bằng chứng gián tiếp: chính danh sách trạng thái tố cáo mô hình

```
tệp: packages/core/execution/src/lib/flow-run/execution/flow-execution.ts
enum FlowRunStatus { ... MEMORY_LIMIT_EXCEEDED, LOG_SIZE_EXCEEDED, ... }
```

Một hệ lưu trạng thái theo **hàng CSDL** không cần hai trạng thái này. Chúng chỉ
tồn tại vì **cả lượt chạy sống trong bộ nhớ của một tiến trình và được ghi thành
một khối**. `HIGH`

Và có bộ chặn tường minh:

```
tệp: packages/server/engine/src/lib/handler/flow-executor.ts
hàm: applyLogSizeLimitIfExceeded()
     → `Flow run data size exceeded the maximum allowed size of ${maxLogSizeMb} MB`
```

### 4.3 Vì sao điều này quan trọng với LTT

Đây **cùng lớp lỗi** với `AgentRun.checkpoint` JSON của LTT (`WF-301`, 01 §D2) —
chỉ là ở quy mô lớn hơn và trong một tệp thay vì một cột.

⇒ **Activepieces KHÔNG giải bài toán `WF-301` cho ta.** Nếu chép mô hình này,
LTT sẽ đổi một khối JSON lấy một khối tệp, và mang thêm hai trạng thái lỗi mới.

⛔ Và với `F4` của LTT (node nặng, output 2 GB video) thì mô hình blob còn tệ
hơn nữa: LTT **bắt buộc** phải giữ nguyên tắc *state mang tham chiếu, không mang
bytes* (`WF-602`) mà nó **đã** làm đúng.

---

## 5. VERSION — 🟡 CÓ, NHƯNG KHÔNG BẤT BIẾN NHƯ TÊN GỌI

### 5.1 Cái có

```
tệp: packages/core/execution/src/lib/flows/flow-version.ts
enum FlowVersionState { LOCKED, DRAFT }
LATEST_FLOW_SCHEMA_VERSION = '24'
```

```
tệp: packages/server/api/src/app/flows/flow-run/flow-run-entity.ts
columns: { flowId, flowVersionId, parentRunId, failParentOnFailure, ... }
indices: [ ..., { columns: ['flowVersionId'] }, { columns: ['parentRunId'] } ]
```

✅ **Run GHIM version** (`flowVersionId` là cột có index), và flow có
`publishedVersionId`. Đúng tinh thần `WF-105`.

### 5.2 🔴 Nhưng `LOCKED` không có nghĩa là bất biến

```
tệp: packages/server/api/src/app/flows/flow-version/flow-version-migration.service.ts
hàm: flowVersionMigrationService.migrate()
```

```ts
if (flowVersion.schemaVersion === LATEST_FLOW_SCHEMA_VERSION) return flowVersion
...
const backupFiles = flowVersion.backupFiles ?? {}
if (!isNil(flowVersion.schemaVersion)) {
    backupFiles[flowVersion.schemaVersion] = await flowVersionBackupService(log).store(flowVersion)
}
await flowVersionRepo().update(flowVersion.id, { schemaVersion: migratedFlowVersion.schemaVersion, ... })
```

Một version `LOCKED` **bị ghi đè tại chỗ** khi lược đồ nâng cấp. Nó bất biến với
*người dùng*, không bất biến với *hệ thống*.

**Và không có hash nội dung ở đâu cả** — grep không tìm thấy checksum/hash trên
`FlowVersion`. Nên không có cách nào nói *"hai lần publish này giống hệt nhau"*
hay *"báo giá này gắn với đúng đồ thị kia"*.

⇒ `WF-105` của LTT (**version bất biến CÓ HASH**) là một yêu cầu **mạnh hơn**
thứ Activepieces có, và tôi giữ nguyên nó.

### 5.3 ⭐ Nhưng cách họ DI TRÚ thì đáng học nguyên vẹn

```
thư mục: packages/server/api/src/app/flows/flow-version/migrations/
         24 bản di trú tuần tự: migrate-v0-… → migrate-v23-…
```

Ba tính chất, cả ba đều đúng:

1. **Di trú LƯỜI, lúc đọc** — không có lượt "nâng cấp toàn bảng" nào phải chạy.
   `if (schemaVersion === LATEST) return` là đường thoát nhanh.
2. **SAO LƯU TRƯỚC KHI DI TRÚ**, giữ theo từng phiên bản lược đồ:
   `backupFiles[oldSchemaVersion] = await store(flowVersion)`. Di trú sai vẫn
   quay lại được đúng bản cũ.
3. **Di trú hỏng thì GỌI NGƯỜI**, không nuốt:
   `onCallService(...).page({ code: ErrorCode.FLOW_MIGRATION_FAILED })` rồi
   `throw`.

⭐ **Đây là câu trả lời tốt cho `Q2`/`WF-105` của LTT.** LTT hôm nay chỉ chấp
`version == 1` và **không có đường di trú nào** (01 §4.4). Ba tính chất trên là
thứ nên chép — về *cách làm*, không phải về *mã*.

---

## 6. MÔ HÌNH LỖI — 🟡 THỬ/BẮT THEO BƯỚC, KHÔNG PHẢI CẠNH LỖI

```
tệp: packages/core/execution/src/lib/flows/actions/action.ts
ActionErrorHandlingOptions = { continueOnFailure?: {value?}, retryOnFailure?: {value?} }
ContinueOnFailureBranches  = { onSuccess?: FlowAction, onFailure?: FlowAction }
```

```
tệp: packages/server/engine/src/lib/handler/flow-executor.ts
hàm: runContinueOnFailureBranchIfNeeded()
     → chọn branches.onFailure nếu stepOutput.status === FAILED, ngược lại onSuccess
```

**So với LTT:** LTT dùng **cạnh** mang `condition ∈ {success, error}`
(01 §5.5) — tức thứ tự lỗi là một tính chất của *đồ thị*. Activepieces gắn nó
vào *bên trong node*.

Đánh giá: **mô hình của LTT tổng quát hơn** (một node có thể có nhiều người xử
lý lỗi ở nhiều nơi), còn mô hình Activepieces **dễ đọc hơn trên giao diện** (bạn
thấy ngay node nào bắt lỗi của node nào).

`retryOnFailure` chỉ là một cờ `boolean` — **không có** số lần thử, không có
giãn cách, không có phân loại lỗi. So với `LoiNguoiGoi`/`DangBan`/backoff của
LTT (01 §6.2) thì đây là một bước lùi rõ rệt.

---

## 7. RẼ NHÁNH — 🟡 TẬP TOÁN TỬ CỐ ĐỊNH, KHÔNG PHẢI NGÔN NGỮ BIỂU THỨC

Đây là câu trả lời trực tiếp cho **`Q5`** của LTT (tài liệu 02 §14).

```
tệp: packages/server/engine/src/lib/handler/router-executor.ts
const CONDITION_EVALUATORS: Record<BranchOperator, (c: ConditionValues) => boolean>
```

**22 toán tử cố định**, không hơn:

```
TEXT_CONTAINS · TEXT_DOES_NOT_CONTAIN · TEXT_EXACTLY_MATCHES · TEXT_DOES_NOT_EXACTLY_MATCH
TEXT_STARTS_WITH · TEXT_DOES_NOT_START_WITH · TEXT_ENDS_WITH · TEXT_DOES_NOT_END_WITH
LIST_CONTAINS · LIST_DOES_NOT_CONTAIN · LIST_IS_EMPTY · LIST_IS_NOT_EMPTY
NUMBER_IS_GREATER_THAN · NUMBER_IS_LESS_THAN · NUMBER_IS_EQUAL_TO
BOOLEAN_IS_TRUE · BOOLEAN_IS_FALSE
DATE_IS_AFTER · DATE_IS_EQUAL · DATE_IS_BEFORE
EXISTS · DOES_NOT_EXIST
```

Cấu trúc: `conditions: BranchCondition[][]` với ngữ nghĩa
`some(group => group.every(cond))` — tức **OR của các nhóm AND**. Không lồng sâu
hơn được.

⭐ **Đây là một lá phiếu mạnh cho phương án "tập toán tử cố định"** ở `Q5` của
LTT: một sản phẩm trưởng thành, hàng nghìn người dùng, và họ **không** cần một
ngôn ngữ biểu thức để rẽ nhánh. Hai lợi ích cụ thể mà LTT cũng cần:
đánh giá được **trong scheduler mà không sợ chạy vô hạn** (`WF-205`), và
**hiển thị được trên giao diện** dưới dạng dropdown thay vì ô nhập tự do.

⚠️ Nhưng: fallback được tính bằng *"mọi nhánh khác đều không khớp"*
(`evaluatedConditionsWithoutFallback.filter((_, i) => i !== index).every(c => !c)`)
— nghĩa là **hai nhánh FALLBACK trong cùng một router sẽ triệt tiêu nhau**. Một
cạm bẫy mô hình mà LTT nên tránh bằng cách cho phép **đúng một** nhánh mặc định.

---

## 8. CHI PHÍ / CREDIT — ❌ KHÔNG TỒN TẠI

```
grep -rn "credit" packages/core/execution/src/lib --include=*.ts
→ 0 dòng khớp
```

`CONFIRMED`

Mô hình kinh doanh của họ là **đếm "tasks" sau khi chạy** (hạn mức), không phải
**tính trần trước khi chạy**.

⇒ Đúng như dự đoán ở tài liệu 03 §6: `WF-501` (trần chi phí tất định, tính
trước) là **thứ LTT phải tự làm**, và LTT **đã có** (01 §4.3). Không hệ visual
automation nào cần tính chất này, vì bước của họ gần như miễn phí — đúng `F4`.

---

## 9. SDK PIECE — ⭐ MẶT MẠNH THẬT SỰ THỨ HAI

Không đọc sâu ở tài liệu này (sẽ so sánh đầy đủ ở `15_NODE_PLUGIN_SDK_COMPARISON.md`),
nhưng con số đã nói:

```
packages/pieces/    926.762 dòng · 10.077 tệp
```

**67 % toàn bộ kho là connector do cộng đồng viết**, trong khi lõi thi hành chỉ
~270 K dòng. Đó là bằng chứng mạnh nhất có thể có rằng **SDK của họ dễ viết**.

Khung khai báo nằm ở `packages/core/piece-types/src/lib/`
(`piece.ts`, `trigger.ts`, `execution-contracts.ts`, `app-connection.ts`).

**Điểm khác biệt then chốt so với LTT:** một piece khai
`pieceName + pieceVersion` (`VersionType`) trong **chính node**
(`PieceActionSettings`). Tức node ghim **phiên bản của connector**, không chỉ
tên. LTT hôm nay ghim `tool.name` mà **không** ghim phiên bản tool
(`WF-104` mới yêu cầu `type_version`) — Activepieces xác nhận yêu cầu đó là
đúng, bằng một hệ đã sống với 10.000 connector.

---

## 10. BẢNG CHẤM THEO YÊU CẦU CỦA LTT

Chấm theo tài liệu 02, **không** theo điểm mạnh Activepieces tự nêu.

| ID | Yêu cầu LTT | AP | Ghi chú |
|---|---|:--:|---|
| WF-101 | DAG nhiều cha/con | ❌ | cây, một cha |
| WF-102 | Edge là thực thể | ❌ | không có cạnh |
| WF-103 | Data/Control edge | ❌ | không áp dụng |
| WF-104 | NodeType ≠ NodeInstance | ✅ | `pieceName + pieceVersion` ⭐ ghim phiên bản |
| WF-105 | Version bất biến + hash | 🟡 | LOCKED/DRAFT + ghim run; **không hash**, LOCKED bị di trú tại chỗ |
| WF-106 | Subworkflow | ✅ | `parentRunId`, `failParentOnFailure` |
| WF-107 | Page ≠ phạm vi chạy | — | không có page |
| WF-201 | Song song khai được | ❌ | **tuần tự tuyệt đối** |
| WF-202 | Lập lịch biết tài nguyên | ❌ | không có khái niệm tài nguyên khan hiếm |
| WF-203 | JOIN đa ngữ nghĩa | ⭐ | **BarrierPolicy — tốt hơn thiết kế của tôi** |
| WF-204 | ForEach + concurrency | 🟡 | loop có + resume giữa chừng; **không đồng thời** |
| WF-205 | Rẽ nhánh theo dữ liệu | ✅ | 22 toán tử cố định, OR-của-AND |
| WF-206 | Node không sinh Job | ✅ | router/loop không phải job |
| WF-207 | Máy trạng thái tường minh | ✅ | `FlowRunStatus` 10 trạng thái |
| WF-208 | Huỷ/timeout lan truyền | ✅ | `cancel`, `TIMEOUT` |
| WF-301 | **Trạng thái là hàng CSDL** | ❌ | **blob một tệp** — cùng lỗi với LTT |
| WF-302 | Bảo đảm được viết ra | 🟡 | `NOT_DISPATCHED` ⭐, còn lại ngầm |
| WF-303 | Reconcile | ✅ | không replay |
| WF-401 | **Waitpoint** | ⭐ | **2 bảng, index bộ phận, UNIQUE idempotency** |
| WF-402 | Đánh thức bằng sự kiện | ⭐ | `resumeUrl`/`confirmUrl` + quét delay theo index |
| WF-403 | Nền tảng cấp GPU | ❌ | không có GPU |
| WF-501 | Trần chi phí tất định | ❌ | **0 dòng "credit"** |
| WF-601 | Artifact có danh tính | ❌ | dữ liệu nằm trong blob |
| WF-602 | State mang tham chiếu | ❌ | mang **giá trị** → trần MB |
| WF-701 | Hệ kiểu cổng | ❌ | không có cổng có kiểu |
| WF-705 | SDK = mở rộng manifest | ⭐ | 10.077 tệp piece = bằng chứng SDK tốt |
| WF-801 | Trigger đa dạng | ✅ | webhook/schedule/piece trigger |
| WF-802 | API chạy workflow | ✅ | có |

**Tổng:** ⭐ xuất sắc **5** · ✅ đạt **10** · 🟡 một phần **4** · ❌ trượt **10**.

---

## 11. RÚT RA CHO LTT — ba thứ lấy, ba thứ tránh

### 🟢 LẤY (thiết kế, không phải mã — dù MIT vẫn cho phép chép)

1. **Waitpoint + Barrier như một cặp bảng riêng.** Cụ thể: `sealed`,
   `BarrierPolicy{requiredSuccesses, releaseOnFirstFailure}`, trạng thái tín
   hiệu **có `NOT_DISPATCHED`**, `UNIQUE(runId, stepName)`, và **index bộ phận**
   `WHERE status='PENDING' AND resumeDateTime IS NOT NULL`.
   → sửa `WF-203` và `WF-401`; giải trực tiếp ngưỡng `M2`.
2. **Di trú lược đồ: lười · sao lưu trước · hỏng thì gọi người.**
   → lấp khoảng trống hiện tại của LTT (chỉ chấp `version == 1`).
3. **Ghim phiên bản của node type trong chính node** (`pieceVersion`).
   → xác nhận `WF-104` cần `type_version`.

### 🔴 TRÁNH

1. **Trạng thái dạng blob.** LTT đang mắc lỗi này ở quy mô nhỏ hơn; Activepieces
   cho thấy nó dẫn tới đâu (`LOG_SIZE_EXCEEDED`, `MEMORY_LIMIT_EXCEEDED`).
   Với video 2 GB của LTT thì đây là ngõ cụt.
2. **Bỏ đồ thị lấy cây.** Nó làm trình thông dịch đơn giản, và làm join trở nên
   *không biểu đạt được*. LTT đã ở phía đúng — đừng đi lùi.
3. **Một trình thông dịch một luồng cho cả lượt chạy.** Với `F4` (node = 20 phút
   GPU) thì mô hình này giữ một tiến trình sống suốt lượt chạy — thứ mà kiến
   trúc job của LTT đã tránh được từ đầu.

### 📌 Sửa ngay vào tài liệu 02

- `WF-203`: bổ sung khái niệm **`sealed`** (phân biệt *"chưa đủ"* với *"sẽ không
  còn nữa"*). Không có nó, `ALL` không định nghĩa được khi fan-out là động.
- `WF-302`: bổ sung trạng thái tín hiệu **`NOT_DISPATCHED`** vào mô hình bảo đảm.
- `Q5`: nghiêng hẳn về **tập toán tử cố định** — có tiền lệ sản phẩm thật.

---

## 12. MỨC TIN CẬY

| Kết luận | Nhãn |
|---|---|
| Flow là cây, không có thực thể cạnh | `CONFIRMED` |
| Nhánh router chạy tuần tự kể cả `EXECUTE_ALL_MATCH` | `CONFIRMED` |
| Loop tuần tự, không có tham số đồng thời | `CONFIRMED` |
| Waitpoint/barrier có thật ở tầng CSDL, 2 bảng + 3 index | `CONFIRMED` |
| Không có khái niệm credit trong lõi thi hành | `CONFIRMED` |
| Version LOCKED bị ghi đè khi di trú lược đồ | `CONFIRMED` |
| Trạng thái chạy được tuần tự hoá thành một tệp blob | `HIGH` — đọc `logsFileId` + `logSerializer.serialize` + trạng thái `LOG_SIZE_EXCEEDED`; **chưa chạy thật để xác nhận** |
| SDK piece dễ viết | `HIGH` — suy từ 10.077 tệp connector, chưa tự viết thử một piece |
| Hành vi khi giết worker giữa chừng | `UNKNOWN` — chưa chạy thí nghiệm (đề bài §9). Sẽ làm ở tài liệu 16 nếu cần |
| Năng lực trong `packages/ee/` | `UNKNOWN` — cố ý không đọc, vùng giấy phép riêng |

---

## 13. BƯỚC KẾ TIẾP

`05_N8N_AUDIT.md`. Câu hỏi mang sang, chọn theo chỗ Activepieces **không** trả
lời được:

1. `WF-101/102` — n8n có **cạnh thật** không? (giao diện gợi ý có; phải đọc mã)
2. `WF-201` — nhánh song song có chạy đồng thời thật không?
3. `WF-301` — trạng thái là hàng hay blob? (n8n có bảng `execution_data` riêng)
4. `WF-602` — `binary-data` xử lý tệp lớn thế nào? Đây là câu **gần LTT nhất**
   trong cả cuộc khảo sát cho tới giờ.

⚠️ Nhắc lại ràng buộc: n8n là **Sustainable Use License + EE**. Chỉ đọc để học,
**không chép mã**, và **không đọc** tệp có `.ee.` trong tên.

---

*Không sửa mã sản phẩm LTT. Không có mã Activepieces nào được chép vào
`D:\LTTSTUDIOSAPP`.*
