# 09 — KHẢO SÁT MÃ NGUỒN: TRIGGER.DEV

> **Kho:** `triggerdotdev/trigger.dev` · **tag** `v4.5.16` ·
> **commit** `ee34a4b13710742ae26d94831547fa2b6cddc9bd` · 2026-09-02
> **Giấy phép:** ✅ **Apache-2.0** — mượn mã được (giữ NOTICE).
> **Phân loại:** *Durable Execution*.
>
> Quy mô lõi: `internal-packages/run-engine` = **25.357 dòng**.
> Lược đồ CSDL: `internal-packages/database/prisma/schema.prisma` = **3.374 dòng**.

---

## 0. KẾT LUẬN NGẮN

**Đây là kho đầu tiên trả lời được cả bốn câu hỏi nặng nhất của LTT.** Bốn kho
trước (Activepieces, n8n, Node-RED — và cả LTT hôm nay) đều trượt `WF-301`;
Trigger.dev không những không trượt, nó đưa ra một **mô hình thứ ba** mà tôi
chưa từng cân nhắc khi viết tài liệu 02.

| Câu hỏi mang vào | Trả lời |
|---|---|
| `WF-301` trạng thái là hàng hay khối? | ⭐ **Chuỗi ảnh chụp BẤT BIẾN, một hàng mỗi lần chuyển trạng thái** |
| `WF-202` hàng đợi có biết tài nguyên? | ⭐ **CÓ — loại hàng đợi hết sức chứa RA KHỎI danh sách trước khi chọn** |
| `WF-401/402` waitpoint? | ⭐ **Bảng riêng + bảng nối, có idempotency key, 4 loại** |
| `WF-302` bảo đảm có được viết ra? | ✅ README có sơ đồ trạng thái; ⚠️ bảo đảm thì vẫn nằm trong mã |

⭐ **Một câu đáng nhớ:** Trigger.dev không lưu *"trạng thái hiện tại"*. Nó lưu
**mọi lần trạng thái từng đổi** — kể cả những lần đổi **thất bại**.

---

## 1. ⭐ `WF-301` — MÔ HÌNH THỨ BA: CHUỖI ẢNH CHỤP BẤT BIẾN

### 1.1 Bằng chứng

```
kho : trigger.dev @ ee34a4b1
tệp : internal-packages/database/prisma/schema.prisma:1338-1393
```

```prisma
model TaskRunExecutionSnapshot {
  id                 String  @id @default(cuid())
  engine             RunEngineVersion @default(V2)
  executionStatus    TaskRunExecutionStatus
  description        String                    /// For debugging

  /// We store invalid snapshots as a record of the run state when we tried to move
  isValid            Boolean @default(true)
  error              String?

  previousSnapshotId String?                   /// ← CHUỖI LIÊN KẾT

  runId              String
  run                TaskRun  @relation(...)
  runStatus          TaskRunStatus
  batchId            String?
  attemptNumber      Int?
  environmentId      String
  environmentType    RuntimeEnvironmentType
  projectId          String
  organizationId     String

  completedWaitpoints      Waitpoint[] @relation("completedWaitpoints")
  completedWaitpointOrder  String[]

  checkpointId       String?
  checkpoint         TaskRunCheckpoint? @relation(...)

  workerId           String?
  runnerId           String?
  createdAt          DateTime @default(now())
  lastHeartbeatAt    DateTime?
  metadata           Json?
}
```

`CONFIRMED`

### 1.2 Vì sao đây là **mô hình thứ ba**

| Mô hình | Ai dùng | Đặc điểm |
|---|---|---|
| **A. Một khối có thể sửa** | Activepieces (tệp blob) · n8n (cột `text`) · **LTT (`checkpoint` JSON)** | đọc–sửa–ghi toàn bộ mỗi lượt |
| **B. Không lưu gì** | Node-RED | mất khi restart |
| **C. Chuỗi ảnh chụp bất biến** | **Trigger.dev** | mỗi lần chuyển trạng thái = **một hàng MỚI**, trỏ về hàng trước |

Mô hình C là **lai giữa event sourcing và máy trạng thái**: không replay hàm
người dùng (nên không đòi tất định như Temporal), nhưng vẫn có **lịch sử đầy đủ,
bất biến, truy vấn được bằng SQL**.

⇒ Khi viết `WF-301` tôi mới đề xuất *"bảng `node_runs` + `attempts`"* — tức
**hàng có thể sửa**. Trigger.dev cho thấy có lựa chọn tốt hơn: **hàng chỉ thêm**.
Nó giải luôn `WF-805` (quan sát được) mà không cần một bảng nhật ký thứ hai.
**→ sửa `WF-301` và `24_TARGET_DATA_MODEL.md`.**

### 1.3 🔴 Chi tiết đắt giá nhất trong cả tài liệu này

```prisma
/// We store invalid snapshots as a record of the run state when we tried to move
isValid Boolean @default(true)
error   String?
```

**Họ ghi lại cả những lần chuyển trạng thái BỊ TỪ CHỐI.**

Một chuyển trạng thái không hợp lệ thường được xử lý bằng cách ném lỗi rồi thôi —
và thông tin *"có ai đó đã cố đi từ X sang Y lúc nào, vì sao"* biến mất. Ở đây nó
thành một hàng, có `description`, có `error`, nằm đúng vị trí trong chuỗi.

⭐ **Đối chiếu trực tiếp với LTT.** `runs.transition()` (`01 §9`) ném
`AgentRunError` khi chuyển sai và **không để lại dấu vết nào**. Với `F3` (worker
restart 13,6 lần/ngày) thì chuyển trạng thái tranh chấp là chuyện sẽ xảy ra —
và hôm nay LTT sẽ không có cách nào điều tra nó sau sự việc.

Đây đúng tinh thần *"đặt tên cho cái không biết, thay vì để nó thành im lặng"*
mà LTT đã làm đúng với `provider_state = ambiguous`.
**→ thêm vào `WF-207`: lưu cả chuyển trạng thái thất bại.**

### 1.4 Hai tầng trạng thái — xác nhận `WF-207`

```
tệp: internal-packages/database/prisma/schema.prisma:1399-1420
```

```prisma
enum TaskRunExecutionStatus {
  RUN_CREATED                /// Run has been created
  DELAYED                    /// waiting to be enqueued
  QUEUED                     /// in the RunQueue
  QUEUED_EXECUTING           /// in queue AND executing — khi continue mà không giành lại được concurrency
  PENDING_EXECUTING          /// đã lấy khỏi queue nhưng chưa chạy
  EXECUTING                  /// đang chạy trên worker
  EXECUTING_WITH_WAITPOINTS  /// đang chạy NHƯNG đang chờ waitpoint
  SUSPENDED                  /// đã treo, có thể đang chờ waitpoint
  PENDING_CANCEL
  FINISHED
}
```

Và `TaskRunStatus` (trạng thái *công khai*) riêng, với các giá trị kết thúc:
`CANCELED · INTERRUPTED · COMPLETED_SUCCESSFULLY · COMPLETED_WITH_ERRORS ·
SYSTEM_FAILURE · CRASHED · EXPIRED · TIMED_OUT`
(`internal-packages/run-engine/src/engine/statuses.ts:43-52`)

⭐ Hai chi tiết LTT nên lấy:

1. **`EXECUTING_WITH_WAITPOINTS`** — *đang chạy* và *đang chờ* **không loại trừ
   nhau**. `WF-207` của tôi viết `RUNNING ⇄ WAITING` như hai trạng thái tách rời;
   với `WF-204` (ForEach 100 job GPU: một số xong, một số đang chờ) thì mô hình
   tách rời **không biểu đạt được**. Phải sửa.
2. **Tách `SYSTEM_FAILURE` / `CRASHED` / `INTERRUPTED` khỏi
   `COMPLETED_WITH_ERRORS`.** LTT hôm nay gộp tất cả vào `AGENT_ERROR`
   (`01 §5.5`) ⇒ không phân biệt được *"việc của khách hỏng"* với *"máy của ta
   hỏng"* — và đó là hai chuyện khác nhau cả về **hoàn tiền** lẫn **cảnh báo
   vận hành**.

---

## 2. ⭐ `WF-202` — HÀNG ĐỢI **BIẾT** SỨC CHỨA. ĐÂY LÀ BẢN VÁ CHO `F2`.

### 2.1 Bằng chứng quyết định

```
tệp: internal-packages/run-engine/src/run-queue/fairQueueSelectionStrategy.ts:412-433
```

```ts
const envsAtFullConcurrency = envs.filter(
  (env) => env.concurrency.current >= env.concurrency.limit
);
const envIdsAtFullConcurrency = new Set(envsAtFullConcurrency.map((env) => env.id));

const envsSnapshot = envs.reduce((acc, env) => {
  if (!envIdsAtFullConcurrency.has(env.id)) { acc[env.id] = env; }
  return acc;
}, {} as Record<string, { concurrency: FairQueueConcurrency }>);
...
const queuesSnapshot = queues.filter((queue) => !envIdsAtFullConcurrency.has(queue.env));
```

**Hàng đợi thuộc môi trường đã hết sức chứa bị LOẠI KHỎI ảnh chụp trước khi
chọn.** Bộ lấy việc **không bao giờ nhìn thấy chúng.** `CONFIRMED`

### 2.2 Vì sao đây là điều LTT cần nhất sau `WF-301`

`F2` đo từ production LTT (`01 §A.3`):

```
9.833 / 10.663 = 92,2 %  lượt nhặt `ltt_llm.chat` kết thúc bằng "nhả ra vì llm_remote bận"
11.929 lượt nhặt  →  868 job hoàn tất   =  13,7 lượt nhặt cho mỗi job xong
```

Nguyên nhân kiến trúc (`01 §6`): `jobs.claim()` nhặt job **rồi mới** giành
`ExecutionLease`, thất bại thì `defer_resource`. Tức **nhặt trước, hỏi sau**.

Trigger.dev làm ngược lại: **hỏi trước, nhặt sau** — và làm ở tầng *chọn hàng
đợi*, không ở tầng *chọn việc*, nên chi phí là O(số hàng đợi) chứ không phải
O(số việc).

⇒ **Đây là bản mẫu trực tiếp cho `WF-202`**, và là con đường để đạt ngưỡng `M3`
(*lượt claim / job xong ≤ 2,0*).

⚠️ **Nhưng có một khác biệt phải nói rõ.** "Tài nguyên" của họ là **hạn mức đồng
thời theo tenant** — một con số trong Redis. "Tài nguyên" của LTT là **một suất
vật lý trên máy B** và **một card GPU** — thứ có thể bị chiếm bởi tiến trình
ngoài nền tảng (`gpu_claims`, `01 §8.1`). Nên LTT **không đọc được sức chứa từ
một bộ đếm của chính mình**; nó phải hỏi tài nguyên thật.
⇒ Cơ chế lấy được; **nguồn của con số thì không**. `INFERRED` cho phần đó.

### 2.3 Chọn hàng đợi công bằng, có thiên lệch khai được

```
tệp: .../fairQueueSelectionStrategy.ts:21-24, 174-198
concurrencyLimitBias   /// thiên về môi trường có hạn mức cao hơn
availableCapacityBias  /// thiên về môi trường còn nhiều chỗ trống
...
const usedCapacityPercentage = env.concurrency.current / env.concurrency.limit;
weight *= 1 + Math.pow(normalizedLimit * biases.concurrencyLimitBias, 2);
```

Chọn **ngẫu nhiên có trọng số**, hai hệ số thiên lệch **cấu hình được**, và
`0` cho cả hai ⇒ quay về công bằng thuần.

So với LTT (`jobs.claim`, `01 §6.2`): LTT xếp theo `aging → account chưa từng
phục vụ → last_claimed_at → FIFO` — **tất định, không ngẫu nhiên**, và chú thích
ghi rõ *"Không có giá tiền trong phép xếp thứ tự này"*.

⭐ **Đánh giá: mô hình của LTT tốt hơn cho bài toán của LTT.** Ngẫu nhiên có
trọng số hợp với hàng nghìn tenant; LTT có ít tenant và cần **giải thích được vì
sao job này chạy trước job kia** khi khách hỏi. Đừng đổi.

---

## 3. ⭐ `WF-401` — WAITPOINT: BẢN ĐẦY ĐỦ NHẤT ĐÃ THẤY

### 3.1 Ba bảng, không phải một

```
tệp: schema.prisma:1453-1570
```

```prisma
model Waitpoint {
  id, friendlyId
  type    WaitpointType     // RUN | DATETIME | MANUAL | BATCH
  status  WaitpointStatus   // PENDING | COMPLETED
  completedAt DateTime?

  idempotencyKey             String
  userProvidedIdempotencyKey Boolean
  idempotencyKeyExpiresAt    DateTime?
  inactiveIdempotencyKey     String?   /// workaround: Prisma không hỗ trợ partial index

  completedByTaskRunId String?  @unique      // waitpoint kiểu RUN
  completedAfter       DateTime?             // kiểu DATETIME, hoặc timeout của MANUAL
  completedByBatchId   String?               // kiểu BATCH

  blockingTaskRuns TaskRunWaitpoint[]        /// các run đang bị CHẶN bởi waitpoint này
  connectedRuns    TaskRun[]                 /// mọi run TỪNG bị chặn — để hiển thị
  completedExecutionSnapshots TaskRunExecutionSnapshot[]

  output String?  outputType String  outputIsError Boolean

  @@unique([environmentId, idempotencyKey])
  @@index([environmentId, type, status])
  @@index([environmentId, type, createdAt(sort: Desc)])
}

model TaskRunWaitpoint {          /// BẢNG NỐI nhiều-nhiều
  taskRunId, waitpointId, projectId
  spanIdToComplete String?
  batchId String?  batchIndex Int?
  @@unique([taskRunId, waitpointId, batchIndex])
}
```

### 3.2 Bốn thứ LTT nên lấy nguyên

1. **Waitpoint là thực thể ĐỘC LẬP với run, nối bằng bảng nhiều-nhiều.**
   Một waitpoint chặn **nhiều** run (`blockingTaskRuns`). Cả Activepieces
   (`04 §3`) lẫn `WF-401` bản nháp của tôi đều gắn waitpoint vào **một** bước —
   không biểu đạt được *"20 node cùng chờ một job GPU"*, đúng thứ `WF-204` cần.
2. **`idempotencyKey` với `@@unique([environmentId, idempotencyKey])`** — hội tụ
   lần thứ **ba** với Activepieces và n8n (`04 §3.2`, `05 §3.5`): **khử trùng
   bằng ràng buộc CSDL.** Ba hệ độc lập, một lời giải. Không còn là gợi ý.
3. **`inactiveIdempotencyKey` + chú thích thẳng thắn**
   *"This is a workaround because Prisma doesn't support partial indexes"* —
   họ **muốn** partial unique index, ORM không cho, nên phải chuyển khoá cũ sang
   cột khác. LTT dùng SQLAlchemy + Postgres ⇒ **làm được partial index thật**,
   không cần workaround này.
4. **`output` + `outputType` + `outputIsError` NGAY TRÊN waitpoint.** Kết quả
   của việc-được-chờ nằm ở điểm chờ, không phải trong state của run. Với `F4`
   (output là khoá artifact) thì đây đúng chỗ.

### 3.3 `TaskRunCheckpoint` — và vì sao LTT **không** cần nó

```prisma
model TaskRunCheckpoint {
  type     TaskRunCheckpointType   // DOCKER | KUBERNETES | COMPUTE
  location String
  imageRef String?
}
```

Họ **chụp ảnh cả container** để treo một lượt chạy rồi khôi phục — vì với họ,
một lượt chạy là **mã của người dùng đang sống trong một tiến trình**.

⛔ LTT **không có bài toán này**: mỗi bước của LTT là một `Job` riêng, chạy xong
là kết thúc; không có tiến trình nào cần đông lạnh. Đây là chỗ **kiến trúc job
của LTT đơn giản hơn và tốt hơn** — ghi lại để tài liệu 22 không nhầm lẫn mà
"adopt" một thứ giải bài toán ta không có.

---

## 4. `WF-403` — TÀI NGUYÊN: CÓ MÔ HÌNH, NHƯNG LÀ CPU/RAM

```
tệp: internal-packages/run-engine/src/engine/machinePresets.ts:7-51
```

```ts
export function getMachinePreset({ defaultMachine, machines, config, run }): MachinePreset {
  if (run.machinePreset) { ... }
  if (parsedConfig.data.preset) { return machinePresetFromName(machines, parsedConfig.data.preset) }
  if (parsedConfig.data.cpu && parsedConfig.data.memory) {
    const name = derivePresetNameFromValues(machines, parsedConfig.data.cpu, parsedConfig.data.memory)
    ...
  }
  return machinePresetFromName(machines, "small-1x");
}
```

**Mô hình:** task khai `preset` **hoặc** `(cpu, memory)`; nền tảng suy ra preset
gần nhất; giá trị được ghim vào `run.machinePreset` (nên deploy đổi cấu hình
không đổi run đang chạy — đúng tinh thần `WF-105`).

⇒ Khuôn **giống hệt** `AppManifest.gpu_vram_mb` của LTT (`01 §2.1`): *app khai,
nền tảng quyết*. Xác nhận LTT đang đúng.
❌ Nhưng **không có GPU, không có lease, không có tài nguyên chia sẻ bởi tiến
trình ngoài**. `WF-403/404` của LTT vẫn không có tiền lệ — đúng như sổ nợ `N1`
đã cảnh báo.

---

## 5. `WF-302` — BẢO ĐẢM: CÓ SƠ ĐỒ, CHƯA CÓ BẢNG BẢO ĐẢM

`internal-packages/run-engine/README.md` có:
- danh sách trách nhiệm (dòng 5-10)
- **sơ đồ trạng thái ASCII đầy đủ** từ `Run triggered` → `DELAYED`/`RUN_CREATED` → …
- mục về heartbeat: *"Heartbeats are used to determine if a run has become
  stalled. Depending on the current execution status, we do different things.
  For example, if the run has been dequeued but the attempt hasn't been started
  we requeue it."* (dòng 164)

✅ Tốt hơn LTT (không có sơ đồ nào).
⚠️ Nhưng **không có bảng "bảo đảm nào áp cho đối tượng nào"** như `WF-302` yêu
cầu. Ngữ nghĩa at-least-once/at-most-once vẫn phải đọc ra từ mã.

⇒ `WF-302` giữ nguyên như một yêu cầu **LTT tự đặt cao hơn ngành**. Điều đó hợp
lý: LTT có sổ tiền, họ không.

Khoá phân tán: `locking.ts` dùng **Redlock trên Redis** (`redlock` + `Redis`),
có `LockAcquisitionTimeoutError` kèm `resources`, `totalWaitTime`, `attempts`,
và đo bằng OpenTelemetry.
⚠️ LTT **không có Redis** và không nên thêm — LTT đã có
`pg_advisory_xact_lock` + `SELECT FOR UPDATE` + `UNIQUE(resource, slot)`, đủ và
ít bộ phận chuyển động hơn. Đây là chỗ **không** nên chép.

---

## 6. KIẾN TRÚC TỔNG THỂ — "HỆ THỐNG CON" LÀ MỘT KHUÔN ĐÁNG HỌC

```
run-engine/src/engine/systems/
    enqueueSystem · dequeueSystem · runAttemptSystem · waitpointSystem
    executionSnapshotSystem · checkpointSystem · batchSystem · debounceSystem
    delayedRunSystem · ttlSystem · pendingVersionSystem · raceSimulationSystem
```

Mười hai *system*, mỗi cái một mối lo, dùng chung `SystemResources`.

⭐ **Đối chiếu đau đớn với LTT:** toàn bộ những mối lo trên nằm trong **một hàm
`executor.tick()`** (`01 §5.2`) — đồng bộ con, lan truyền skip, kiểm kết thúc,
kiểm ngân sách, cache, thử lại, submit. Đó là lý do `tick()` vừa khó đọc vừa
chạy `31+N` câu SQL.

Và có `raceSimulationSystem.ts` — **một hệ thống con chỉ để mô phỏng tranh
chấp**. Họ coi việc *kiểm thử được điều kiện đua* là một tính năng của sản phẩm.
LTT nên học điều này khi viết bộ chaos test của `WF-304`.

---

## 7. BẢNG CHẤM THEO YÊU CẦU CỦA LTT

| ID | Yêu cầu LTT | TD | Ghi chú |
|---|---|:--:|---|
| WF-101/102 | DAG · Edge thực thể | ❌ | **không có đồ thị** — task gọi task bằng mã |
| WF-104 | NodeType ≠ NodeInstance | ✅ | task version + `machinePreset` ghim vào run |
| WF-105 | Version bất biến | ✅ | deploy bất biến, run ghim version |
| WF-106 | Subworkflow | ⭐ | waitpoint kiểu `RUN` + `BATCH` — mô hình sạch nhất đã thấy |
| WF-201 | Song song khai được | ✅ | đồng thời theo tenant, cấu hình được |
| WF-202 | **Lập lịch biết tài nguyên** | ⭐ | **loại hàng đợi hết chỗ trước khi chọn** |
| WF-203 | JOIN đa ngữ nghĩa | ✅ | `BATCH` waitpoint + `completedWaitpointOrder` |
| WF-204 | ForEach + concurrency | ⭐ | `batch-queue` + `completionTracker` |
| WF-205 | Rẽ nhánh theo dữ liệu | — | là mã, không phải đồ thị |
| WF-206 | Node không sinh Job | — | không áp dụng |
| WF-207 | **Máy trạng thái tường minh** | ⭐ | **2 tầng + lưu cả chuyển trạng thái THẤT BẠI** |
| WF-208 | Huỷ/timeout lan truyền | ✅ | `PENDING_CANCEL`, `EXPIRED`, `TIMED_OUT`, `ttlSystem` |
| WF-301 | **Trạng thái là hàng CSDL** | ⭐⭐ | **chuỗi ảnh chụp bất biến** — mô hình thứ ba |
| WF-302 | Bảo đảm được viết ra | 🟡 | sơ đồ có; bảng bảo đảm không |
| WF-303 | Reconcile | ✅ | heartbeat + phục hồi run treo theo trạng thái |
| WF-304 | Không state chỉ trong RAM | ✅ | + `raceSimulationSystem` để kiểm |
| WF-401 | **Waitpoint** | ⭐⭐ | **3 bảng, nhiều-nhiều, có idempotency, có output** |
| WF-402 | Đánh thức bằng sự kiện | ✅ | Redis worker + `delayedRunSystem` |
| WF-403 | Nền tảng cấp tài nguyên | 🟡 | CPU/RAM preset; **không GPU, không lease** |
| WF-501 | Trần chi phí tất định | ❌ | `billingCache` là hạn mức, không phải trần trước |
| WF-601 | Artifact có danh tính | 🟡 | `run-store`, `object-store`; chưa đọc sâu |
| WF-701 | Hệ kiểu cổng | ❌ | không có cổng |
| WF-801 | Trigger đa dạng | ✅ | `schedule-engine` gói riêng |
| WF-805 | Quan sát tầng workflow | ⭐ | chuỗi snapshot **là** dòng thời gian; + `tracing`, `clickhouse` |

**Tổng:** ⭐ **7** · ✅ **10** · 🟡 **4** · ❌ **4** · — **2**.

⚠️ **Điểm cao nhất cho tới giờ — nhưng đọc cho đúng.** Trigger.dev trượt hẳn
`WF-101/102` (**không có mô hình đồ thị**: workflow của họ là *mã người dùng gọi
task*, không phải node + cạnh). Nó **không** là ứng viên để "adopt toàn bộ";
nó là **nguồn tốt nhất để ADAPT phần runtime bền vững**.

---

## 8. RÚT RA CHO LTT

### 🟢 LẤY — và đây là kho đầu tiên mà "lấy" có nghĩa là chép được (Apache-2.0)

1. **⭐⭐ Chuỗi ảnh chụp bất biến thay cho một khối trạng thái sửa được.**
   Một hàng mỗi lần chuyển, `previousSnapshotId` nối chuỗi, **ghi cả lần chuyển
   thất bại** (`isValid` + `error`). Giải cùng lúc `WF-301`, `WF-207`, `WF-805`
   và ngưỡng `M1`.
2. **⭐⭐ Loại hàng đợi hết sức chứa RA KHỎI danh sách trước khi chọn.**
   Bản vá trực tiếp cho `F2` (92 %) và ngưỡng `M3` (13,7 → ≤ 2,0).
3. **⭐ Waitpoint là thực thể độc lập + bảng nối nhiều-nhiều.**
   Một waitpoint chặn nhiều run — thứ mà cả `WF-401` bản nháp lẫn Activepieces
   đều không biểu đạt được, và `WF-204` thì cần.
4. **Tách `SYSTEM_FAILURE`/`CRASHED`/`INTERRUPTED` khỏi lỗi nghiệp vụ.**
   LTT gộp hết vào `AGENT_ERROR` — hai chuyện khác nhau về hoàn tiền và cảnh báo.
5. **`EXECUTING_WITH_WAITPOINTS`** — *đang chạy* và *đang chờ* không loại trừ nhau.
6. **Khuôn "hệ thống con"** thay cho một `tick()` khổng lồ.
7. **`raceSimulationSystem`** — coi việc kiểm thử điều kiện đua là một phần sản
   phẩm, không phải một bài test viết thêm.

### 🔴 KHÔNG LẤY

1. **Redlock/Redis.** LTT đã có `pg_advisory_xact_lock` + `SELECT FOR UPDATE` +
   `UNIQUE(resource, slot)`. Thêm Redis là thêm một hệ phải vận hành.
2. **Container checkpoint (`DOCKER`/`KUBERNETES`).** LTT không có tiến trình
   người dùng cần đông lạnh — mỗi bước là một job. Đây là chỗ LTT **đơn giản
   hơn**, đừng làm phức tạp lên.
3. **Chọn hàng đợi ngẫu nhiên có trọng số.** LTT có ít tenant và cần giải thích
   được thứ tự cho khách; `aging → fair-share → FIFO` tất định là bản đúng hơn.
4. **`inactiveIdempotencyKey`.** Đó là workaround cho giới hạn của Prisma. LTT
   dùng Postgres trực tiếp ⇒ **partial unique index thật**.

### 📌 Sửa vào tài liệu 02

| Yêu cầu | Sửa gì |
|---|---|
| `WF-301` | Đổi từ *"hàng có thể sửa"* sang **chuỗi ảnh chụp CHỈ THÊM** |
| `WF-207` | Thêm: **lưu cả chuyển trạng thái thất bại** (`isValid` + `error`) |
| `WF-207` | Thêm: `RUNNING` và `WAITING` **không loại trừ nhau** |
| `WF-207` | Thêm: tách lỗi **hệ thống** khỏi lỗi **nghiệp vụ** ở trạng thái kết thúc |
| `WF-401` | Waitpoint là thực thể **độc lập**, nối run bằng bảng **nhiều-nhiều** |
| `WF-401` | Thêm `output`/`outputType`/`outputIsError` ngay trên waitpoint |
| `WF-202` | Cơ chế: **lọc theo sức chứa ở tầng CHỌN HÀNG ĐỢI**, không ở tầng chọn việc |
| `WF-302` | Khử trùng bằng **partial unique index** — hội tụ lần thứ **ba** |

---

## 9. MỨC TIN CẬY

| Kết luận | Nhãn |
|---|---|
| `TaskRunExecutionSnapshot` là hàng chỉ-thêm, nối bằng `previousSnapshotId` | `CONFIRMED` |
| Ghi cả ảnh chụp không hợp lệ (`isValid`, `error`) | `CONFIRMED` |
| Hai tầng trạng thái, 10 `TaskRunExecutionStatus` | `CONFIRMED` |
| Hàng đợi của env hết sức chứa bị loại trước khi chọn | `CONFIRMED` |
| Waitpoint là 3 bảng, nhiều-nhiều, có idempotency unique | `CONFIRMED` |
| Checkpoint container `DOCKER\|KUBERNETES\|COMPUTE` | `CONFIRMED` |
| Khoá bằng Redlock trên Redis | `CONFIRMED` |
| `machinePreset` ghim vào run, không đọc lại lúc chạy | `HIGH` — đọc `run.machinePreset` được ưu tiên trước `config` |
| Không có mô hình đồ thị node/cạnh | `HIGH` — không tìm thấy thực thể cạnh trong schema 3.374 dòng |
| Hiệu quả thật của việc lọc sức chứa | `INFERRED` — **chưa chạy đo**; sẽ cần thí nghiệm nếu muốn `CONFIRMED` |
| `run-store` lưu artifact thế nào | `UNKNOWN` — chưa đọc |
| Ngữ nghĩa at-least-once/at-most-once chính xác | `UNKNOWN` — không có bảng bảo đảm; phải đọc `runAttemptSystem` (2.340 dòng) |

---

## 10. BƯỚC KẾ TIẾP

`10_TEMPORAL_AUDIT.md` — MIT, Go, `service/history` + `service/matching`.

Sau Trigger.dev, câu hỏi mang sang **hẹp lại rõ rệt** (nhiều câu đã có lời giải
tốt rồi, không cần Temporal trả lời lại):

1. `WF-302` — Temporal là hệ **duy nhất** nổi tiếng vì viết ra bảo đảm của mình.
   Bảng bảo đảm đó nằm ở đâu trong mã, và nó cưỡng chế bằng gì?
2. `WF-303` — họ chọn **replay**; đâu là cái giá cụ thể trong mã (yêu cầu tất
   định, versioning hàm workflow)? Đây là đối chứng cho quyết định
   *"LTT chọn reconcile"* mà tôi đã ghi ở `WF-303` **chưa có bằng chứng**.
3. `WF-202` — `service/matching` xử lý task queue ra sao so với bản lọc-sức-chứa
   của Trigger.dev?

⛔ **Không** cần Temporal trả lời `WF-301` và `WF-401` nữa — Trigger.dev đã cho
lời giải phù hợp hơn với LTT (không đòi tất định, không đòi replay).

---

*Không sửa mã sản phẩm LTT. Không có mã Trigger.dev nào được chép vào
`D:\LTTSTUDIOSAPP` — dù Apache-2.0 cho phép, việc chép sẽ chỉ xảy ra ở pha
triển khai, sau khi có phê duyệt.*
