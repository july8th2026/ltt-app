# 05 — KHẢO SÁT MÃ NGUỒN: n8n

> **Kho:** `n8n-io/n8n` · **tag** `n8n@2.37.10` ·
> **commit** `5542b8b6419cb6925cca8f11b270c9bfbe09d85e` · 2026-09-04
> **Giấy phép:** 🔴 **Sustainable Use License + n8n Enterprise License**
> **Phân loại:** *Visual Automation*.
>
> ⛔ **Ràng buộc thi hành của phiên này:** chỉ **đọc để học kiến trúc**.
> Không chép một dòng mã nào. Không đọc tệp có `.ee.` trong tên hay `.ee` trong
> tên thư mục (giấy phép EE loại chúng khỏi Sustainable Use License).
> Mọi đoạn trích dưới đây là **trích dẫn ngắn làm bằng chứng**, không phải mã
> được mang về.

---

## 0. KẾT LUẬN NGẮN

n8n là **đồ thị thật** (khác Activepieces), nhưng **vẫn chạy tuần tự** trong một
lượt thi hành, và **vẫn lưu trạng thái thành một khối**. Nó mạnh hơn Activepieces
ở mô hình đồ thị, ngang bằng ở tính bền, và **vượt trội ở một chỗ duy nhất mà
lại đúng là chỗ LTT cần nhất sau waitpoint**: **hệ thống dữ liệu nhị phân**.

| | |
|---|---|
| ⭐ Xuất sắc | **`binary-data`** — hệ artifact đa backend, id tự mô tả, streaming. Đúng `WF-601/602` |
| ⭐ Đáng học | **cạnh CÓ KIỂU** (13 loại) — kiểu thứ ba ngoài data/control: *cạnh tiêm năng lực* |
| ✅ Tốt | đồ thị nhiều cha/con thật · fan-in theo cổng vào · thứ tự duyệt **có phiên bản** |
| 🔴 Trượt | song song trong một lượt · lập lịch biết tài nguyên · trạng thái dạng hàng |
| 🔴 Ràng buộc | giấy phép — không mượn mã được |

⭐ **Một câu đáng nhớ:** n8n có đồ thị thật nhưng **cố tình** thi hành nó tuần
tự, và họ quan tâm tới *thứ tự duyệt* đủ nhiều để **đánh phiên bản cho nó**.

---

## 1. MÔ HÌNH ĐỒ THỊ — ✅ ĐỒ THỊ THẬT, CẠNH CÓ KIỂU

### 1.1 Cấu trúc

```
kho : n8n @ 5542b8b6
tệp : packages/workflow/src/interfaces.ts:93, 461-474
```

```ts
export interface IConnection {
    node: string;               // node đích
    type: NodeConnectionType;   // loại đầu vào ở node đích, vd "main"
    index: number;              // chỉ số cổng vào/ra
}
export interface IConnections   { [nodeName: string]: INodeConnections }
export interface INodeConnections { [outputType: string]: NodeInputConnections }
```

**Đọc ra:** một **bản đồ kề** (adjacency map) từ *tên node nguồn* → *loại đầu ra*
→ *mảng theo chỉ số cổng ra* → *danh sách node đích*.

⇒ Fan-out (nhiều đích trên một cổng ra) và fan-in (nhiều nguồn trỏ vào một node)
đều biểu đạt được. **Đây là đồ thị, không phải cây.** `CONFIRMED`

### 1.2 🔴 Nhưng cạnh được khoá bằng TÊN node, không phải id

`IConnections` có khoá là `nodeName`, và `IConnection.node` cũng là tên. Nghĩa
là **đổi tên một node phải viết lại mọi cạnh trỏ tới nó**.

LTT dùng `id` (`edge.source`/`edge.target` là step id, `01 §3.2`) — **LTT đang ở
phía đúng**, và `WF-102` giữ nguyên yêu cầu dùng id.

### 1.3 ⭐ Cạnh CÓ KIỂU — và có một kiểu thứ ba mà tài liệu 02 chưa nghĩ tới

```
tệp: packages/workflow/src/interfaces.ts:2836-2854
```

```ts
export const NodeConnectionTypes = {
    AiAgent: 'ai_agent',            AiChain: 'ai_chain',
    AiDocument: 'ai_document',      AiEmbedding: 'ai_embedding',
    AiLanguageModel: 'ai_languageModel',  AiMemory: 'ai_memory',
    AiOutputParser: 'ai_outputParser',    AiRetriever: 'ai_retriever',
    AiReranker: 'ai_reranker',      AiTextSplitter: 'ai_textSplitter',
    AiTool: 'ai_tool',              AiVectorStore: 'ai_vectorStore',
    Main: 'main',
} as const;
export type AINodeConnectionType = Exclude<NodeConnectionType, 'main'>;
```

**13 loại cạnh. Đúng MỘT loại (`main`) là luồng dữ liệu/thi hành.** 12 loại còn
lại là thứ khác hẳn:

> Một cạnh `ai_languageModel` **không** có nghĩa *"chạy sau"* và cũng **không**
> có nghĩa *"truyền dữ liệu"*. Nó có nghĩa: **"node này CUNG CẤP một mô hình
> ngôn ngữ cho node kia."** Đây là **tiêm phụ thuộc vẽ thành cạnh.**

🔴 **Đây là phát hiện đáng giá nhất về mô hình đồ thị trong cả cuộc khảo sát cho
tới giờ**, vì LTT đang giải cùng bài toán bằng cách khác:

| | n8n | LTT hôm nay |
|---|---|---|
| Chọn model | **một cạnh** `ai_languageModel` từ node Model | một **tham số** `model_ref` trong `params` |
| Chọn tài khoản/khoá | cạnh (một số piece) | `api_pool` ở tầng nền tảng, node không thấy |
| Bộ nhớ hội thoại | cạnh `ai_memory` | không có |

⭐ **Ưu điểm cách của n8n:** thứ vô hình trở nên **nhìn thấy được trên canvas** —
người dùng thấy ngay *cái gì đang cấp model cho bước này*, và đổi model = kéo lại
một sợi dây, không phải mở panel tìm dropdown.
⚠️ **Nhược:** số loại cạnh nở theo số năng lực. 12 loại hôm nay, và mỗi năng lực
AI mới lại thêm một loại — một enum ở lõi phải sửa mỗi lần, đúng thứ hợp đồng app
của LTT sinh ra để tránh.

⇒ **Đề xuất cho tài liệu 23:** LTT nên có **`kind: DATA | CONTROL | RESOURCE`**
(ba, không phải hai như `WF-103` đang viết), trong đó `RESOURCE` mang một
`port_type` thuộc nhóm tham chiếu (`model_ref`, `connection_ref`) — **giữ số
lượng loại cạnh cố định** trong khi vẫn vẽ được sợi dây.

---

## 2. THI HÀNH — 🔴 ĐỒ THỊ THẬT, NHƯNG CHẠY TUẦN TỰ

### 2.1 Bằng chứng: một máy ngăn xếp, một node mỗi lượt

```
tệp: packages/core/src/execution-engine/workflow-execute.ts  (2.912 dòng)
```

```ts
executionLoop: while (this.runExecutionData.executionData!.nodeExecutionStack.length !== 0) {
    ...
    executionData = this.runExecutionData.executionData!.nodeExecutionStack.shift() as IExecuteData;
    ...
    let runNodeData = await this.runNode( ... );
}
```

`shift()` lấy **một** mục, `await` chạy xong **rồi mới** lặp tiếp. Không có
`Promise.all` trên các nhánh. `CONFIRMED`

⇒ **Hai hệ visual automation lớn nhất (Activepieces và n8n) đều KHÔNG chạy song
song trong một lượt workflow.** Đó không phải trùng hợp — với `F4` của họ (bước
gần như miễn phí, phần lớn là gọi HTTP vài trăm ms) thì song song hoá không mua
được gì đáng kể, và nó làm mọi thứ khó gỡ lỗi.

⛔ Nhưng với `F4` của **LTT** (một node = 20 phút A100) thì kết luận đảo ngược
hoàn toàn. **Đây chính là lý do đề bài §30 cấm chép kiến trúc automation truyền
thống.**

### 2.2 ⭐ Thứ tự duyệt được ĐÁNH PHIÊN BẢN — bài học về một thứ tưởng là nội bộ

```
tệp: packages/core/src/execution-engine/workflow-execute.ts:450
```

```ts
const enqueueFn = workflow.settings.executionOrder === 'v1' ? 'unshift' : 'push';
```

Một dòng, và nó nói rất nhiều:

| `executionOrder` | thao tác | duyệt kiểu |
|---|---|---|
| `v1` (mới) | `unshift` → LIFO | **theo chiều sâu** — chạy hết một nhánh rồi mới sang nhánh khác |
| mặc định cũ | `push` → FIFO | **theo chiều rộng** — xen kẽ các nhánh |

⭐ **Bài học:** thứ tự duyệt **không phải chi tiết nội bộ**. Nó nhìn thấy được
(thứ tự các bước chạy, thứ tự side effect ra ngoài), nên n8n **không dám** đổi
nó cho workflow cũ — họ giữ cả hai và gắn cờ **theo từng workflow**.

⇒ Với LTT: hôm nay executor duyệt **theo thứ tự khai báo trong `plan.steps`**
(`01 §5.2`), và điều đó chưa từng được viết ra như một hợp đồng. Nếu V2 đổi sang
lập lịch theo tài nguyên (`WF-202`), **thứ tự side effect sẽ đổi**. Phải khai
báo điều đó, không được để nó là hệ quả phụ.
**Bổ sung vào `WF-207`.**

### 2.3 Fan-in / join — ✅ có thật, ngữ nghĩa ALL theo cổng vào

```
tệp: packages/core/src/execution-engine/workflow-execute.ts:453-515
```

```ts
// Check if node has multiple inputs as then we have to wait for all input data
// to be present before we can add it to the node-execution-stack
const numberOfInputs = workflow.connectionsByDestinationNode[connectionData.node]?.main?.length ?? 0;
if (numberOfInputs > 1) { ... waitingExecution[node][waitingNodeIndex].main[connectionData.index] = ... }
```

**Ngữ nghĩa:** node có N cổng vào chỉ được đẩy lên ngăn xếp khi **cả N cổng đều
đã có dữ liệu**. Đây là `ALL`-join, nhưng khoá theo **cổng vào**, không theo
*"cha đã xong"*.

**Khác biệt then chốt với LTT:**

| | Điều kiện READY |
|---|---|
| n8n | **dữ liệu đã tới đủ mọi cổng vào** (dataflow) |
| LTT | **mọi phụ thuộc đã `done`** (`after ⊆ done`) |

n8n gần dataflow hơn; LTT gần đồ thị phụ thuộc hơn. Với `WF-103` (tách DATA/
CONTROL edge), mô hình của LTT xử lý được *"chạy sau nhưng không nhận dữ liệu"*
một cách tự nhiên, còn n8n thì phải giả trang bằng một cạnh `main` bị bỏ qua.

⚠️ Và `waitingExecution` là **một từ điển trong RAM với sổ sách chỉ số thủ công**
(`waitingNodeIndex`, `createNewWaitingEntry`, vòng lặp dò cổng trống). So với
`BarrierPolicy` của Activepieces (§04 §3.3) thì đây là bản kém hơn hẳn: không
`sealed`, không `N-of-M`, không trạng thái tín hiệu.

### 2.4 Thử lại — trong chính vòng thi hành

```ts
let runNodeData = await this.runNode( ... );
let nodeFailed = checkFailure(runNodeData);
while (nodeFailed && tryIndex !== maxTries - 1) {
    runNodeData = await this.runNode( ... );
    nodeFailed = checkFailure(runNodeData);
}
```

Thử lại là một **vòng lặp trong bộ nhớ**, không phải một hàng đợi lên lịch lại.
⇒ Nếu tiến trình chết giữa các lần thử, số lần đã thử **mất**. LTT ghi
`Job.attempts` xuống CSDL (`01 §6.1`) — **LTT ở phía đúng**, và `F3` (worker
restart 13,6 lần/ngày) làm khác biệt này thành thiết yếu chứ không phải tinh tế.

---

## 3. BỀN VỮNG — 🔴 LẠI LÀ MỘT KHỐI, VÀ HỌ ĐÃ ĐỤNG TRẦN

### 3.1 Bằng chứng

```
tệp: packages/@n8n/db/src/entities/execution-data.ts
```

```ts
@Entity()
export class ExecutionData {
    @Column('text')  data: string;                    // ← TOÀN BỘ trạng thái, MỘT chuỗi
    @JsonColumn()    workflowData: Omit<IWorkflowBase,'pinData'> & { pinData?: ... };
    @PrimaryColumn() executionId: string;
    @Column(...)     workflowVersionId: string | null;
}
```

`data` là **một cột `text`** chứa trạng thái đã tuần tự hoá của cả lượt chạy.
`CONFIRMED`

⇒ **Cùng mô hình với Activepieces (blob tệp) và với `AgentRun.checkpoint` của
LTT (blob JSON).** Ba hệ, ba lần, cùng một lựa chọn.

### 3.2 ⭐ Và bằng chứng rằng lựa chọn đó ĐỤNG TRẦN

```
tệp: packages/workflow/src/interfaces.ts:112
export type ExecutionStorageLocation = 'db' | 'fs' | 's3' | 'az';

tệp: packages/@n8n/db/src/entities/execution-entity.ts:93
@Column({ type: 'varchar', length: 2, nullable: false, default: 'db' })
```

Họ phải thêm khả năng **đẩy chính khối trạng thái ra hệ tệp / S3 / Azure**, ghi
vị trí vào một cột hai ký tự trên mỗi lượt chạy.

🔴 **Đây là bằng chứng mạnh nhất tôi có cho `WF-301`.** Ba hệ thống độc lập chọn
"trạng thái là một khối", và cái lớn nhất trong ba **đã phải xây một tầng lưu trữ
phân cấp để cứu chính lựa chọn đó**. LTT đang ở bước đầu của cùng con dốc
(`checkpoint` JSON, ghi lại toàn bộ mỗi tick).

⇒ Giữ nguyên `WF-301` (trạng thái là **hàng CSDL**), và ghi rõ trong tài liệu 23
rằng **cả ba hệ visual automation đều không đi đường đó** — nên LTT sẽ không có
tiền lệ để chép, phải tự thiết kế. Tiền lệ nằm ở nhóm *durable execution*
(Temporal, Trigger.dev), sẽ đọc ở tài liệu 09/10.

### 3.3 Ghim phiên bản — bằng cách CHÉP, không phải bằng cách trỏ

`ExecutionData.workflowData` giữ **nguyên bản sao của workflow** tại thời điểm
chạy, cạnh `workflowVersionId`. Và có thực thể `WorkflowPublishedVersion`.

⇒ Ghim version **chắc chắn tuyệt đối** (bản sao không đổi được), đổi lại **nhân
bản dữ liệu theo từng lượt chạy**. Với LTT — nơi `AgentRun.plan` cũng là một bản
sao đóng băng (`01 §9.1`) — đây là **xác nhận rằng cách LTT đang làm là cách
ngành làm**, không phải một lối tắt.

### 3.4 ⭐ Chờ và đánh thức: chỉ số trên `waitTill`

```
tệp: packages/@n8n/db/src/entities/execution-entity.ts:27, 88
@Index(['waitTill', 'id'])
...
waitTill: Date | null;
```

Một cột mốc thời gian trên **lượt chạy** + một chỉ số ⇒ bộ quét tìm mọi lượt đến
hạn bằng **một truy vấn**.

🔴 **Hội tụ độc lập.** Activepieces làm y hệt bằng chỉ số **bộ phận** trên
`waitpoint.resumeDateTime` (`04 §3.2`). Hai hệ, hai đội, cùng một lời giải cho
`M2` của LTT (*"run chờ 60 phút phải tốn O(1) SQL"*).

⇒ Với LTT, đây không còn là một ý tưởng nữa mà là **một khuôn đã được xác nhận
hai lần**: đừng để từng run tự hỏi; hãy để **một** truy vấn theo chỉ số tìm mọi
thứ đến hạn.

⚠️ Khác biệt: n8n đặt `waitTill` trên **cả lượt chạy** (một lượt chờ một chỗ),
Activepieces đặt trên **waitpoint theo bước** (nhiều điểm chờ song song). LTT
cần bản của Activepieces, vì `WF-204` (ForEach 100 job GPU) sinh ra nhiều điểm
chờ đồng thời trong một run.

### 3.5 Khử trùng — lại một chỉ số duy nhất BỘ PHẬN

```
tệp: packages/@n8n/db/src/entities/execution-entity.ts:38
@Index(['deduplicationKey'], { unique: true, where: '"deduplicationKey" IS NOT NULL' })
```

Hội tụ lần thứ hai với Activepieces (`UNIQUE (flowRunId, stepName)`, `04 §3.2`).
**Idempotency được cưỡng chế bằng ràng buộc CSDL, không bằng mã cẩn thận.**

LTT đã dùng đúng khuôn này ở `ExecutionLease UNIQUE(resource, slot)`, nhưng
**không** dùng cho `dedupe_key` của job (nó chỉ được kiểm bằng `SELECT` trước
khi `INSERT`, `01 §6.1` / `jobs.submit`). Đó là một cửa sổ tranh chấp thật.
**→ thêm vào `LTT_GAP_ANALYSIS` (tài liệu 21).**

---

## 4. ⭐ `binary-data` — HỆ ARTIFACT, VÀ LÀ THỨ GẦN LTT NHẤT CHO TỚI GIỜ

Đây là câu tôi mang sang từ tài liệu 04, và nó được trả lời tốt hơn mong đợi.

### 4.1 Backend và id tự mô tả

```
tệp: packages/core/src/binary-data/binary-data.config.ts:8
export const BINARY_DATA_MODES = ['default', 'filesystem', 's3', 'azure', 'database'] as const;

tệp: packages/core/src/binary-data/binary-data.service.ts:134, 150, 156, 239
const [mode, fileId] = binaryDataId.split(':');
```

**Định dạng id: `<mode>:<fileId>`.** Bản thân tham chiếu **mang theo backend
đang giữ nó**.

⭐ **Vì sao điều này quan trọng với LTT.** `platform_core/storage.py` hôm nay là
một **singleton toàn cục** (`get_storage()` trả về Local **hoặc** R2). Nên khi
LTT bật R2, **mọi khoá cũ trỏ vào Local trở thành mơ hồ** — không có gì trong
chuỗi khoá nói nó nằm ở đâu. n8n đã trả giá cho bài học đó và giải bằng hai ký
tự và một dấu hai chấm.

⇒ **Sửa `WF-601`:** `Artifact.id` phải **tự mô tả backend**, không chỉ có cột
`storage_backend` trong bảng — vì tham chiếu đi vào JSON của bước sau, và JSON
đó không tra bảng được.

### 4.2 Giao diện Manager — hợp đồng lưu trữ đầy đủ

```
tệp: packages/core/src/binary-data/types.ts:38-66
export interface Manager {
    store(location, bufferOrStream, metadata): Promise<WriteResult>;
    getPath(fileId): string;
    getAsBuffer(fileId): Promise<Buffer>;
    getAsStream(fileId, chunkSize?): Promise<Readable>;
    getMetadata(fileId): Promise<Metadata>;
    deleteMany?(locations): Promise<void>;          // ← TUỲ CHỌN, xem dưới
    deleteManyByFileId?(ids): Promise<void>;
    copyByFileId(targetLocation, sourceFileId): Promise<string>;
    copyByFilePath(targetLocation, sourcePath, metadata): Promise<WriteResult>;
    rename(oldFileId, newFileId): Promise<void>;
}
```

Bốn chi tiết đáng học, mỗi cái giải một vấn đề LTT sẽ gặp:

1. **`getAsStream(fileId, chunkSize?)`** — luồng, không chỉ buffer. Với video
   2 GB của LTT, `getAsBuffer` là một lỗi hết bộ nhớ đang chờ xảy ra.
2. **`copyByFileId`** — sao chép **trong tầng lưu trữ**, không đi qua tiến trình
   thi hành. LTT hôm nay không có nguyên hàm này; mọi lượt "dùng lại ảnh của
   bước trước" đều phải nhắc lại khoá.
3. ⭐ **`deleteMany?` là TUỲ CHỌN**, và chú thích nói rõ vì sao:

   > *"Present for `FileSystem`, absent for `ObjectStore` (delegated to S3
   > lifecycle config)"*

   Tức: **backend nào có cơ chế hết hạn riêng thì hợp đồng KHÔNG ép nó tự xoá.**
   Đây là một quyết định thiết kế tinh tế mà LTT nên chép nguyên khi thêm R2 —
   đừng viết một bộ dọn TTL của riêng mình rồi chạy song song với vòng đời của
   R2.
4. **`FileLocation` là union có nhãn:**
   ```ts
   | { type: 'execution'; workflowId: string; executionId: string }
   | { type: 'custom'; pathSegments: string[]; sourceType?: string; sourceId?: string }
   ```
   Vòng đời của tệp gắn với **lượt chạy** hay **tách rời** được khai ngay ở chỗ
   ghi. Đúng `ttl_class` mà `WF-601` đang đề xuất (`EPHEMERAL | RUN | PROJECT |
   PERMANENT`) — và n8n xác nhận rằng **hai** mức là đủ để bắt đầu.

### 4.3 Điều n8n KHÔNG có mà LTT vẫn phải tự làm

- `checksum` / khử trùng nội dung — không thấy.
- **lineage** (artifact này sinh ra từ attempt nào) — không thấy; chỉ có vị trí.
- **quyền theo artifact** — chỉ có `SigningPayload = { id }` cho URL ký.

⇒ `WF-603` (lineage) vẫn là phần LTT tự thiết kế.

---

## 5. ĐỒNG THỜI — 🔴 TOÀN INSTANCE, KHÔNG THEO TÀI NGUYÊN, KHÔNG THEO TENANT

```
tệp: packages/cli/src/concurrency/concurrency-control.service.ts
export type ConcurrencyQueueType = 'production' | 'evaluation';
private readonly limits: Map<ConcurrencyQueueType, number>;
...
if (this.globalConfig.executions.mode === 'queue') { this.isEnabled = false; return; }
```

Ba điều đọc ra:

1. Giới hạn là **hai con số toàn instance** (`production`, `evaluation`) — không
   theo người dùng, không theo workflow, không theo tài nguyên.
2. **Tắt hẳn khi chạy chế độ `queue`** — khi mở rộng bằng hàng đợi ngoài, việc
   giới hạn được giao cho số worker.
3. Có `CLOUD_TEMP_PRODUCTION_LIMIT = 999` và ngưỡng báo cáo — dấu vết của một
   hạn mức thương mại, không phải một mô hình tài nguyên.

⇒ **`WF-202` của LTT (lập lịch nhận biết tài nguyên) không có tiền lệ ở đây.**
Hai kho đã đọc, cả hai đều không có. Ghi nhận: đó là vì **họ không có tài nguyên
khan hiếm để lập lịch quanh** — không GPU, không suất `llm_remote` duy nhất.
`F2` của LTT (92 % lượt nhặt bị nhả) là một bài toán **của riêng LTT** trong
nhóm này.

---

## 6. BẢNG CHẤM THEO YÊU CẦU CỦA LTT

| ID | Yêu cầu LTT | n8n | Ghi chú |
|---|---|:--:|---|
| WF-101 | DAG nhiều cha/con | ✅ | bản đồ kề thật |
| WF-102 | Edge là thực thể | 🟡 | có cạnh, nhưng khoá bằng **tên node** |
| WF-103 | Data/Control edge | ⭐ | **13 loại**; phát hiện *cạnh tiêm năng lực* |
| WF-104 | NodeType ≠ NodeInstance | ✅ | `INodeTypeNameVersion { name, version }` |
| WF-105 | Version bất biến + hash | ✅ | `WorkflowPublishedVersion` + **chép cả workflow vào lượt chạy** |
| WF-106 | Subworkflow | ✅ | `executeWorkflow`, sub-execution |
| WF-201 | Song song khai được | ❌ | **máy ngăn xếp, một node mỗi lượt** |
| WF-202 | Lập lịch biết tài nguyên | ❌ | giới hạn toàn instance |
| WF-203 | JOIN đa ngữ nghĩa | 🟡 | chỉ `ALL` theo cổng vào; sổ sách trong RAM |
| WF-204 | ForEach + concurrency | 🟡 | `SplitInBatches` lặp; **không đồng thời** |
| WF-205 | Rẽ nhánh theo dữ liệu | ✅ | IF/Switch + biểu thức |
| WF-206 | Node không sinh Job | ✅ | mọi node đều trong tiến trình |
| WF-207 | Máy trạng thái tường minh | ✅ | `ExecutionStatus` + ⭐ **thứ tự duyệt có phiên bản** |
| WF-208 | Huỷ/timeout lan truyền | ✅ | `status === 'canceled'`, `executionTimeoutTimestamp` |
| WF-301 | Trạng thái là hàng CSDL | ❌ | **`@Column('text') data`** + phải đẩy ra fs/s3/az |
| WF-302 | Bảo đảm được viết ra | 🟡 | ⭐ chỉ số **unique bộ phận** cho khử trùng |
| WF-303 | Reconcile | ✅ | không replay |
| WF-401 | Waitpoint | 🟡 | `waitTill` ở mức **lượt chạy**, không theo bước |
| WF-402 | Đánh thức bằng sự kiện | ✅ | ⭐ `@Index(['waitTill','id'])` — hội tụ với Activepieces |
| WF-403 | Nền tảng cấp GPU | ❌ | không có |
| WF-501 | Trần chi phí tất định | ❌ | không có |
| WF-601 | Artifact có danh tính | ⭐ | **`<mode>:<fileId>` + Manager đa backend** |
| WF-602 | State mang tham chiếu | ⭐ | nhị phân **ra khỏi** JSON, có streaming |
| WF-603 | Lineage artifact | ❌ | chỉ có vị trí |
| WF-701 | Hệ kiểu cổng | 🟡 | cổng có **loại kết nối**, không có **kiểu dữ liệu** |
| WF-705 | SDK = mở rộng manifest | ✅ | `packages/@n8n/create-node`, `nodes-base` |
| WF-801 | Trigger đa dạng | ✅ | webhook/cron/poll/trigger node |
| WF-802 | API chạy workflow | ✅ | có |

**Tổng:** ⭐ **6** · ✅ **13** · 🟡 **6** · ❌ **5**.

---

## 7. RÚT RA CHO LTT

### 🟢 LẤY (ý tưởng — **không** chép mã, giấy phép cấm)

1. **Id artifact tự mô tả backend** (`<backend>:<key>`).
   → sửa `WF-601`. Giải bài toán mà `platform_core/storage.py` singleton sẽ tạo
   ra ngay khi LTT bật R2 song song với Local.
2. **Hợp đồng lưu trữ có `stream`, `copy`, và `delete` TUỲ CHỌN.**
   → `deleteMany?` vắng mặt cho object store là chi tiết đáng chép nguyên tinh
   thần: đừng chồng TTL của mình lên TTL của R2.
3. **Loại cạnh thứ ba: `RESOURCE`** (tiêm model/kết nối thành sợi dây).
   → sửa `WF-103` từ hai loại thành ba, nhưng **giữ enum cố định** thay vì nở
   theo năng lực như n8n.
4. **Thứ tự duyệt là hợp đồng, phải khai và phải có phiên bản.**
   → bổ sung `WF-207`.
5. **Ràng buộc UNIQUE bộ phận cho khử trùng.**
   → LTT có `dedupe_key` nhưng cưỡng chế bằng `SELECT` rồi `INSERT`; đây là một
   cửa sổ tranh chấp thật. Ghi vào tài liệu 21.

### 🔴 TRÁNH

1. **Trạng thái một khối.** n8n là bằng chứng mạnh nhất: họ phải xây `db|fs|s3|az`
   để cứu chính lựa chọn đó. LTT đang ở đầu con dốc ấy.
2. **Cạnh khoá bằng tên node.** LTT dùng id — giữ nguyên.
3. **Thử lại bằng vòng lặp trong RAM.** Với `F3` (restart 13,6 lần/ngày) thì số
   lần thử phải nằm trong CSDL. LTT đã đúng.
4. **Enum loại cạnh nở theo năng lực.** 12 loại AI hôm nay, mỗi năng lực mới lại
   sửa lõi — đúng thứ hợp đồng app của LTT sinh ra để tránh.

### 📌 Sửa vào tài liệu 02

- `WF-103`: **ba** loại cạnh (`DATA | CONTROL | RESOURCE`), không phải hai.
- `WF-601`: id artifact **tự mô tả backend**.
- `WF-207`: **thứ tự duyệt** là một phần của hợp đồng thi hành.
- `WF-302`: thêm ràng buộc **UNIQUE bộ phận** làm cơ chế cưỡng chế khử trùng.

---

## 8. MỨC TIN CẬY

| Kết luận | Nhãn |
|---|---|
| `IConnections` là bản đồ kề thật, có fan-in/fan-out | `CONFIRMED` |
| 13 loại cạnh, 12 là "tiêm năng lực" | `CONFIRMED` |
| Thi hành tuần tự bằng máy ngăn xếp | `CONFIRMED` |
| `executionOrder v1/v0` đổi DFS/BFS | `CONFIRMED` |
| Trạng thái lưu trong một cột `text` | `CONFIRMED` |
| Có tầng đẩy trạng thái ra `db\|fs\|s3\|az` | `CONFIRMED` |
| Id nhị phân dạng `<mode>:<fileId>` | `CONFIRMED` |
| Đồng thời là toàn instance, tắt ở chế độ queue | `CONFIRMED` |
| Join `ALL` theo cổng vào, sổ sách trong RAM | `HIGH` — đọc `waitingExecution`; chưa chạy thí nghiệm |
| `SplitInBatches` không đồng thời | `INFERRED` — suy từ vòng thi hành tuần tự; **chưa đọc node đó** |
| Năng lực trong tệp `.ee.` | `UNKNOWN` — **cố ý không đọc**, ràng buộc giấy phép |
| Hành vi khi giết tiến trình giữa lượt chạy | `UNKNOWN` — chưa chạy thí nghiệm |

---

## 9. BƯỚC KẾ TIẾP

`06_NODE_RED_AUDIT.md`. Node-RED là kho **nhỏ nhất** (235.892 dòng), **giấy phép
sạch nhất** (Apache-2.0), và có ba thứ hai kho trước không trả lời được:

1. `WF-106` — `Subflow.js` là subgraph **thật** ở lõi runtime, không phải sub-execution.
2. `WF-201` — Node-RED là mô hình **hướng thông điệp**; các nhánh có thể thật sự
   chạy đan xen. Đây là kho đầu tiên có khả năng nói "có" cho song song.
3. `WF-704` — canvas SVG **tự viết** (không React Flow), có `registry` riêng.
   Đối chứng tốt cho quyết định giữ hay bỏ React Flow (`Q7`).

---

*Không sửa mã sản phẩm LTT. Không có mã n8n nào được chép vào `D:\LTTSTUDIOSAPP`.
Không đọc tệp nào có `.ee.` trong tên.*
