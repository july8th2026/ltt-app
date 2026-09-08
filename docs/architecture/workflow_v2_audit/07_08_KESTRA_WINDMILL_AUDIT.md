# 07+08 — KHẢO SÁT MÃ NGUỒN: KESTRA & WINDMILL (nhóm *Orchestration*)

> **Gộp hai kho vào một tài liệu** vì sau nhóm *durable execution* (09, 10) chỉ
> còn **ba câu hỏi** cần nhóm này trả lời. Gộp để đi nhanh hơn, không phải để
> đọc ít hơn.
>
> **Kestra:** `kestra-io/kestra` · tag `v1.3.37` · commit
> `035a5b36f5742b168b9e2ed1615c8e1e1d215093` · 2026-09-02 · **Apache-2.0** ·
> Java/Micronaut · 313.175 dòng.
> **Windmill:** `windmill-labs/windmill` · tag `v1.804.0` · commit
> `c37f59e22a1948d63f10ad443690a6d341248c5b` · 2026-09-05 · 🔴 **AGPLv3** ·
> Rust/Svelte · 1.346.331 dòng.
>
> ⛔ Windmill là **AGPLv3** — chỉ đọc để học ý tưởng. Không chép mã.

---

## 0. KẾT LUẬN NGẮN — VÀ MỘT BẤT NGỜ

Tôi xếp nhóm này ưu tiên **thấp** sau tài liệu 06, với lý do *"đóng góp là
trigger và versioning, không phải tính bền"*. **Đánh giá đó SAI về Windmill.**

⭐ **Windmill là kho DUY NHẤT trong bảy kho vừa có mô hình flow thật, vừa khai
báo được song song, vừa thi hành song song thật.** Nó trả lời `WF-201` và
`WF-204` tốt hơn **tất cả** những kho đã đọc — kể cả Trigger.dev.

| | Kestra | Windmill |
|---|---|---|
| ⭐ Đóng góp chính | **`Concurrency{limit, behavior}`** — cái LTT thiếu hẳn | **`FlowModule` — hợp đồng mỗi bước giàu nhất đã thấy** |
| ⭐ Thứ hai | `tasks/errors/finally` — mô hình lỗi kiểu try-catch | **ForEach `parallel` + `parallelism` + `skip_failures`** |
| ⭐ Thứ ba | revision so nội dung **loại trừ metadata** | **`AiTransform`** — đầu vào do LLM quyết lúc chạy |
| 🔴 Ràng buộc | không | **AGPLv3 — không mượn mã được** |

⛔ **Đính chính một số tôi nêu ở tài liệu 03 và 06:** tôi viết *"14 gói
`windmill-trigger-*`"*. Đếm thật: **11** (`amqp azure email gcp http kafka mqtt
nats postgres sqs websocket`), cộng `windmill-trigger` (lõi) và
`windmill-native-triggers` = 13 thư mục. Con số 14 là ước lượng của tôi lúc lướt
danh sách, không phải phép đếm.

---

## 1. ⭐ KESTRA — `Concurrency`: THỨ LTT THIẾU HẲN

### 1.1 Bằng chứng

```
kho : kestra @ 035a5b36
tệp : core/src/main/java/io/kestra/core/models/flows/Concurrency.java
```

```java
public class Concurrency {
    @Min(1) @NotNull
    private Integer limit;

    @NotNull @Builder.Default
    private Behavior behavior = Behavior.QUEUE;

    public enum Behavior { QUEUE, CANCEL, FAIL; }
}
```

`CONFIRMED`

### 1.2 Vì sao ba dòng này quan trọng hơn vẻ ngoài của nó

`WF-201` của LTT đề xuất **bốn tầng trần** (run · tài nguyên · tenant · node) —
và **không tầng nào nói điều gì xảy ra khi chạm trần.**

Kestra bắt buộc khai **hành vi tràn**, và ba lựa chọn là ba chính sách kinh
doanh khác nhau, không phải chi tiết kỹ thuật:

| `behavior` | Nghĩa với khách hàng |
|---|---|
| `QUEUE` | *"xếp hàng, sẽ tới lượt"* — phù hợp render video |
| `CANCEL` | *"bỏ lượt cũ, chạy lượt mới"* — phù hợp preview/xem trước |
| `FAIL` | *"báo lỗi ngay, đừng bắt chờ"* — phù hợp API đồng bộ |

⭐ **LTT hôm nay mặc định `QUEUE` ở khắp nơi và chưa từng khai điều đó.** Job
chạm trần tài nguyên thì `defer_resource` → về hàng đợi (`01 §6.1`). Với `F2`
(92 % lượt nhặt bị nhả) đó là **hàng nghìn lượt xếp lại mỗi ngày** — và với một
tool tương tác (chat) thì `FAIL` nhanh có thể là câu trả lời **đúng hơn** với
khách so với xếp hàng 82 giây (đo được ở `AppManifest.cho_tai_nguyen_s`).

**→ sửa `WF-201`: mỗi tầng trần phải khai kèm `behavior` tràn.**

### 1.3 Mô hình lỗi: `tasks` / `errors` / `finally`

```
tệp: core/src/main/java/io/kestra/core/models/flows/Flow.java:75-86
List<Task> tasks;
List<Task> errors;
@JsonProperty("finally") protected List<Task> _finally;
```

**Try-catch-finally ở cấp flow.** So với ba mô hình đã thấy:

| Hệ | Xử lý lỗi |
|---|---|
| **LTT** | **cạnh** mang `condition: error` — lỗi là một hướng đi trong đồ thị |
| Activepieces | `continueOnFailureBranches {onSuccess, onFailure}` gắn **trong node** |
| Node-RED | node `catch` bắt lỗi của cả tab |
| **Kestra** | **ba danh sách ở cấp flow**: thân · lỗi · cuối cùng |

⭐ **`finally` là thứ cả LTT lẫn ba hệ kia đều KHÔNG có** — *"chạy dù thành hay
bại"*. Với LTT nó có ứng dụng cụ thể và có thật: **dọn artifact tạm**, **nhả
lease**, **kết sổ credit**. Hôm nay việc kết sổ nằm rải trong `_terminal_status`
+ `budget.settle` và có **145 lần hold treo trong 28 ngày** (`01 §A.5`) — đúng
lớp vấn đề mà một khối `finally` được cưỡng chế sẽ đóng lại.

**→ thêm vào `WF-209` (mới): mỗi WorkflowVersion khai được một khối `finally`
chạy đúng một lần khi run chạm trạng thái kết thúc, bất kể kết quả.**

### 1.4 Versioning: so nội dung, loại trừ metadata

```
tệp: core/src/main/java/io/kestra/core/models/flows/Flow.java:61, 364
List<String> exclusions = Arrays.asList("revision", "deleted", "source", "updated");
...
.revision(this.revision + 1)
```

Revision **chỉ tăng khi nội dung có nghĩa đổi** — bốn trường metadata bị loại
khỏi phép so sánh. `CONFIRMED`

So với `WF-105` của LTT (*"hash nội dung tất định"*): cùng mục tiêu, hai cách.
Hash **mạnh hơn** (so sánh được hai version bất kỳ, không chỉ liền kề) và
**rẻ hơn** (một chuỗi 64 ký tự thay vì một phép so sánh đối tượng có danh sách
loại trừ phải bảo trì). Nhưng Kestra chỉ ra một chi tiết `WF-105` chưa nói:
**phải khai TƯỜNG MINH trường nào KHÔNG vào hash.** Nếu không, `updated_at` sẽ
lọt vào và mọi lần lưu đều ra hash mới.

**→ `WF-105` bổ sung: danh sách trường loại trừ khỏi hash là một phần của hợp
đồng, phải khai và phải có test.**

---

## 2. ⭐⭐ WINDMILL — `FlowModule`: HỢP ĐỒNG MỖI BƯỚC GIÀU NHẤT ĐÃ THẤY

### 2.1 Bằng chứng

```
kho : windmill @ c37f59e2
tệp : openflow.openapi.yaml:283-340   (lược đồ CÔNG KHAI của flow)
```

```yaml
FlowModule:
  description: A single step in a flow. Can be a script, subflow, loop, or branch
  properties:
    id                       # tham chiếu kết quả qua 'results.step_id'
    value                    # FlowModuleValue
    stop_after_if            # dừng sớm sau khi bước xong
    stop_after_all_iters_if  # chỉ cho loop — dừng sau khi hết vòng
    skip_if: { expr }        # biểu thức JS trả true thì BỎ QUA bước
    sleep                    # InputTransform  ← có thể là BIỂU THỨC
    cache_ttl                # số giây đệm kết quả bước này
    cache_ignore_s3_path
    timeout                  # InputTransform  ← có thể là BIỂU THỨC
    delete_after_secs        # xoá args/result/logs sau N giây kể từ khi xong
    summary
    mock: { enabled, return_value }        # ← MOCK ĐỂ KIỂM THỬ, NGAY TRONG LƯỢC ĐỒ
    suspend: { required_events, timeout }  # ← DUYỆT, cần N lượt phê duyệt
```

`CONFIRMED`

### 2.2 Năm thứ trong đó LTT nên lấy, mỗi thứ giải một vấn đề đã đo được

| Trường | Giải vấn đề nào của LTT |
|---|---|
| **`delete_after_secs`** | `WF-603` TTL artifact **theo bước**. LTT hôm nay chỉ có `Job.content_expired_at` toàn cục (`01 §11.1`) |
| **`cache_ttl`** | LTT có cache nhưng **bật mặc định, không tắt được theo bước, không có TTL** (`01 §5.7`) — và nó quét 50 job + gọi `storage.exists()` trong đường nóng |
| **`mock: {enabled, return_value}`** | `23_TEST_STRATEGY` — kiểm một workflow **không tốn tiền GPU**. Với `F4` (node = 20 phút A100) đây không phải tiện nghi, là **điều kiện để test được** |
| **`timeout` là biểu thức** | LTT có `max_runtime_s` **tĩnh trong manifest**. Video 60 giây và video 5 giây không nên chung một trần |
| **`suspend.required_events`** | `WF-803` human-in-the-loop, **N lượt duyệt** — hội tụ với `BarrierPolicy.requiredSuccesses` của Activepieces (`04 §3.3`) |

⭐ **`mock` là thứ tôi bỏ sót hoàn toàn khi viết tài liệu 02.** Nó nằm trong
**lược đồ công khai của flow**, không phải trong bộ test — nghĩa là họ coi
"chạy thử workflow mà không chạm bước đắt tiền" là một **năng lực sản phẩm**.
Với LTT thì đây là cách duy nhất để một khách hàng thử một workflow 8 bước mà
không đốt tám lượt GPU.

### 2.3 ⭐⭐ `WF-204` — ForEach: BẢN ĐẦY ĐỦ NHẤT

```
tệp: openflow.openapi.yaml:802-834
ForloopFlow:
  modules        # các bước chạy mỗi vòng
  iterator       # InputTransform — biểu thức JS trả về mảng
  skip_failures  # BẮT BUỘC — vòng lỗi không dừng cả loop, trả null
  parallel       # chạy các vòng đồng thời
  parallelism    # InputTransform — TRẦN đồng thời, tĩnh HOẶC biểu thức
  squash
  required: [modules, iterator, skip_failures, type]
```

Và **đây không phải chỉ là lược đồ** — thi hành thật ở
`backend/windmill-worker/src/worker_flow.rs` (**6.438 dòng**):

```
570:  let (is_loop, skip_loop_failures, parallelism, parallel_loop) = ...
773:  } if *parallel => {
841:  "parallel iteration {job_id_for_status} of flow {flow} update nindex: {nindex} len: {len}"
1096: if parallelism.is_some() { ... }
1084: // for parallel branchall and forloop, we do not want to trigger the error
      // handler again at the forloop/branchall node since it was already triggered at the leaf level
```

`CONFIRMED`

**Đối chiếu `WF-204` của LTT với thứ Windmill đã có:**

| `WF-204` yêu cầu | Windmill |
|---|---|
| `over: <ref tới port ...[]>` | ✅ `iterator` (biểu thức) |
| `concurrency` | ✅ **`parallelism`, và nó là BIỂU THỨC** |
| `max_items` bắt buộc hữu hạn | ❌ không có — **LTT vẫn phải tự đặt**, vì `WF-501` cần trần chi phí |
| `on_item_error: FAIL_ALL \| CONTINUE \| COLLECT_ERRORS` | 🟡 `skip_failures` (bool) — hai lựa chọn, không phải ba |
| gom theo thứ tự đầu vào | ✅ `nindex` |
| thử lại **một** phần tử | `UNKNOWN` — chưa đọc đủ sâu |
| tiếp tục bộ sưu tập dở sau crash | `UNKNOWN` |

⭐ **`parallelism` là một BIỂU THỨC**, không phải hằng số. Nghĩa là trần đồng
thời tính được **lúc chạy** từ dữ liệu — ví dụ *"số suất GPU đang rảnh"*. Đó
chính là cầu nối giữa `WF-204` (ForEach) và `WF-202` (lập lịch biết tài nguyên)
mà tôi chưa nghĩ ra cách bắc.

### 2.4 `BranchAll` — song song có khai báo, lỗi cô lập theo nhánh

```
tệp: openflow.openapi.yaml:902-935
BranchAll:
  description: Parallel branching where all branches execute simultaneously.
               Unlike BranchOne, all branches run regardless of conditions.
  branches[]: { summary, skip_failure, modules[] }
  parallel: bool   # true = đồng thời; false = tuần tự
```

Hai điểm:
1. **`parallel` là một cờ trên NODE**, không phải một cài đặt toàn cục. Cùng một
   flow có nhánh song song và nhánh tuần tự — đúng thứ `WF-201` cần
   (*"trần khai được"*, không phải hằng số 4 như LTT hôm nay).
2. **`skip_failure` theo TỪNG nhánh** — nhánh phụ hỏng không kéo cả flow xuống.
   LTT hôm nay chỉ có `after_error` ở tầng cạnh, không có "nhánh này được phép
   hỏng".

### 2.5 ⭐ `AiTransform` — đầu vào do LLM quyết LÚC CHẠY

```
tệp: openflow.openapi.yaml:399-450
InputTransform = StaticTransform | JavascriptTransform | AiTransform

StaticTransform:     value           # kể cả '$res:path/to/resource'
JavascriptTransform: expr            # 'results.step_id', 'flow_input', 'flow_input.iter.value'
AiTransform:         type: ai
  description: Value resolved by the AI runtime for this input.
               The AI engine decides how to satisfy the parameter.
```

`CONFIRMED`

🔴 **Đây là chỗ duy nhất trong bảy kho có một mô hình LAI giữa workflow tất định
và agent** — và nó chạm thẳng vào `WF-804` của LTT (*"Agent tạo workflow, Agent
không phải workflow engine"*).

Windmill vạch ranh giới ở chỗ **khác** LTT: đồ thị vẫn tất định, nhưng **một
tham số** được đánh dấu *"để AI quyết"*. Tức LLM không điều khiển luồng, nó chỉ
điền một ô.

⚠️ **Với LTT thì mô hình này đắt hơn nó có vẻ**, và lý do là `WF-501`: nếu một
tham số do LLM quyết lúc chạy thì **trần chi phí không tính trước được** —
LLM có thể chọn `model = cao cấp nhất` hoặc `duration = 60 giây`. Trần tất định
là ranh giới bất khả xâm phạm số 1 của LTT (`02 §1.3`).

⇒ **Nếu LTT muốn `AiTransform`, nó phải kèm ràng buộc**: giá trị AI chọn phải
nằm trong một **tập hữu hạn đã khai**, và trần chi phí tính theo **giá trị đắt
nhất trong tập đó**. Ghi lại như một hướng, không phải một yêu cầu.
**→ `Q8` (mới) cho tài liệu 25.**

### 2.6 Trigger tách thành gói — `WF-801`

```
backend/windmill-trigger-{amqp,azure,email,gcp,http,kafka,mqtt,nats,postgres,sqs,websocket}
+ windmill-trigger (lõi) + windmill-native-triggers
= 11 loại trigger, mỗi loại MỘT CRATE riêng
```

⭐ **Khuôn đáng học, và nó giống hệt hợp đồng app của LTT:** thêm một nguồn kích
hoạt = **thêm một gói**, không sửa lõi. `WF-801` của LTT cần 4 loại (manual ·
API · schedule · webhook) — nên áp dụng đúng khuôn này ngay từ đầu, để loại thứ
năm không phải sửa `platform_core`.

---

## 3. BẢNG CHẤM THEO YÊU CẦU CỦA LTT

| ID | Yêu cầu | Kestra | Windmill |
|---|---|:--:|:--:|
| WF-101/102 | DAG · Edge thực thể | 🟡 DAG qua `DependsOn` | 🟡 cây module lồng nhau, không có cạnh |
| WF-105 | Version bất biến | ⭐ revision **loại trừ metadata** | ✅ |
| WF-106 | Subworkflow | ✅ | ✅ `PathFlow` |
| **WF-201** | **Song song khai được** | ⭐ **`Concurrency{limit, behavior}`** | ⭐⭐ **`parallel` theo NODE** |
| WF-202 | Lập lịch biết tài nguyên | 🟡 trần theo flow | 🟡 |
| WF-203 | JOIN đa ngữ nghĩa | ✅ | ✅ `BranchAll` + `skip_failure`/nhánh |
| **WF-204** | **ForEach + concurrency** | ✅ | ⭐⭐ **`parallel` + `parallelism` (BIỂU THỨC) + `skip_failures`** |
| WF-205 | Rẽ nhánh theo dữ liệu | ✅ | ⭐ `skip_if` · `stop_after_if` · JS |
| WF-207 | Máy trạng thái | ✅ `State.Type` | ✅ `FlowStatus`/`FlowStatusModule` |
| WF-208 | Huỷ/timeout | ⭐ `behavior: CANCEL` | ⭐ `timeout` là **biểu thức** |
| WF-209 | **`finally`** *(mới)* | ⭐ **có** | ❌ |
| WF-301 | Trạng thái là hàng | ✅ JDBC repo | ✅ Postgres |
| WF-401 | Waitpoint | ✅ | ⭐ `suspend.required_events` |
| WF-403 | Nền tảng cấp GPU | ❌ | ❌ |
| WF-501 | Trần chi phí tất định | ❌ | ❌ (và `AiTransform` **làm khó hơn**) |
| WF-601/603 | Artifact · TTL | 🟡 storage-local | ⭐ **`delete_after_secs` theo bước** |
| WF-701 | Hệ kiểu cổng | 🟡 `Input` có kiểu | 🟡 JSON schema |
| WF-801 | Trigger đa dạng | ✅ | ⭐⭐ **11 gói riêng** |
| WF-803 | Human-in-the-loop | 🟡 pause | ⭐ `suspend` + N duyệt |
| — | **Kiểm thử được** | 🟡 | ⭐⭐ **`mock` trong lược đồ flow** |

**Kestra:** ⭐4 · ✅8 · 🟡4 · ❌3
**Windmill:** ⭐9 · ✅5 · 🟡5 · ❌3 — **điểm ⭐ cao nhất trong cả bảy kho**

---

## 4. RÚT RA — VÀ MỘT ĐÍNH CHÍNH VỀ CHÍNH TÔI

### 🟢 LẤY (ý tưởng; Windmill là AGPL nên **không** chép mã)

1. **⭐⭐ `parallel` + `parallelism` khai theo NODE, và `parallelism` là BIỂU
   THỨC.** Đây là cầu nối `WF-204` ↔ `WF-202`: trần đồng thời tính lúc chạy từ
   số suất tài nguyên đang rảnh.
2. **⭐ `Concurrency{limit, behavior: QUEUE|CANCEL|FAIL}`.** Mỗi tầng trần của
   `WF-201` phải khai hành vi tràn. LTT đang mặc định `QUEUE` khắp nơi mà chưa
   từng khai.
3. **⭐ `mock: {enabled, return_value}` trong lược đồ flow.** Điều kiện để test
   được một workflow có bước 20 phút GPU.
4. **⭐ `finally` ở cấp flow** (Kestra). Nơi đúng để kết sổ credit và nhả lease —
   145 lần hold treo/28 ngày là triệu chứng của việc thiếu nó.
5. **`delete_after_secs` theo bước** → `WF-603`.
6. **`timeout` là biểu thức, không phải hằng số manifest** → sửa `max_runtime_s`.
7. **`skip_failure` theo từng nhánh** → `WF-203`.
8. **Trigger = một gói mỗi loại** → `WF-801`.
9. **Khai tường minh trường nào KHÔNG vào hash version** (Kestra) → `WF-105`.

### 🔴 KHÔNG LẤY

1. **Mã Windmill** — AGPLv3, điều khoản mạng, LTT là SaaS thương mại.
2. **`AiTransform` nguyên bản** — nó phá `WF-501` (trần chi phí tất định), ranh
   giới bất khả xâm phạm số 1. Chỉ nhận nếu tập giá trị hữu hạn và trần tính
   theo giá trị đắt nhất (`Q8`).
3. **Cây module lồng nhau** thay cho đồ thị có cạnh — cùng hạn chế Activepieces.

### 📌 Đính chính về phán đoán của chính tôi

Ở `06 §10` tôi hạ Kestra/Windmill xuống ưu tiên trung bình với lý do
*"đóng góp là trigger và versioning, không phải tính bền"*. **Sai.** Windmill có
**⭐9** — cao nhất trong bảy kho — và trả lời `WF-201`/`WF-204` tốt hơn mọi kho
khác.

⭐ Cái tôi đo sai không phải Windmill mà là **câu hỏi**. Tôi phân loại nó vào
nhóm *orchestration* rồi hỏi nó những câu của nhóm đó (trigger, version), trong
khi thứ nó giỏi nhất nằm ở nhóm khác (**mô hình flow + song song khai báo**).
Phân loại giúp đi nhanh; nó cũng **giới hạn câu hỏi tôi nghĩ ra để hỏi**.

**→ ghi vào `20_OSS_SCORECARD.md`: chấm mọi kho theo TOÀN BỘ 41 yêu cầu, không
chỉ theo câu hỏi của nhóm nó bị xếp vào.**

### 📌 Sửa vào tài liệu 02

| Yêu cầu | Sửa |
|---|---|
| `WF-201` | mỗi tầng trần khai kèm **`behavior: QUEUE\|CANCEL\|FAIL`** |
| `WF-201` | `parallel` khai **theo node**, không phải hằng số toàn cục |
| `WF-204` | `concurrency` được phép là **biểu thức** đọc sức chứa lúc chạy |
| `WF-105` | khai tường minh **trường loại trừ khỏi hash** |
| `WF-209` | **MỚI** — khối `finally` cấp workflow, chạy đúng một lần |
| `WF-603` | TTL artifact khai **theo bước** (`delete_after_secs`) |
| `WF-706` | `timeout` là **biểu thức**, không phải hằng số manifest |
| `WF-803` | `required_events` — N lượt duyệt (hội tụ với Activepieces) |
| **mới** | **`mock`** phải nằm trong lược đồ workflow, không chỉ trong bộ test |
| `Q8` | **MỚI** — có nhận `AiTransform` không, và ràng buộc nào giữ `WF-501`? |

---

## 5. MỨC TIN CẬY

| Kết luận | Nhãn |
|---|---|
| Kestra `Concurrency{limit, behavior QUEUE\|CANCEL\|FAIL}` | `CONFIRMED` |
| Kestra `tasks`/`errors`/`finally` ở cấp flow | `CONFIRMED` |
| Kestra revision tăng theo nội dung, loại trừ 4 trường metadata | `CONFIRMED` |
| Windmill `FlowModule` có 14 trường gồm `mock`, `suspend`, `delete_after_secs` | `CONFIRMED` |
| `ForloopFlow` có `parallel` + `parallelism` + `skip_failures` | `CONFIRMED` |
| Song song **được thi hành thật**, không chỉ trong lược đồ | `CONFIRMED` — `worker_flow.rs:570,773,841,1096` |
| `AiTransform` — đầu vào do AI quyết lúc chạy | `CONFIRMED` |
| 11 gói trigger (không phải 14 như tôi nêu ở tài liệu 03) | `CONFIRMED` |
| Thử lại **một** phần tử trong ForEach song song | `UNKNOWN` — chưa đọc đủ trong 6.438 dòng |
| Tiếp tục ForEach dở dang sau crash | `UNKNOWN` |
| Năng lực trong vùng `enterprise` của Windmill | `UNKNOWN` — cố ý không đọc |

---

## 6. PHA C ĐÃ ĐÓNG — 7/7 KHO ĐÃ ĐỌC

| # | Kho | ⭐ | Đóng góp lớn nhất cho LTT |
|---|---|:--:|---|
| 04 | Activepieces | 5 | **Waitpoint + `BarrierPolicy` + `sealed` + `NOT_DISPATCHED`** |
| 05 | n8n | 6 | **`binary-data` id `<mode>:<fileId>`**; cạnh **có kiểu** |
| 06 | Node-RED | 3 | **6 hook trên đường định tuyến cạnh** |
| 09 | Trigger.dev | 7 | **Chuỗi ảnh chụp bất biến**; **lọc hàng đợi hết sức chứa** |
| 10 | Temporal | 11 | **Cách VIẾT bảo đảm**; bằng chứng để **không** chọn replay |
| 07 | Kestra | 4 | **`Concurrency{limit, behavior}`**; **`finally`** |
| 08 | **Windmill** | **9** | **`parallel`/`parallelism` theo node**; **`mock`**; **11 gói trigger** |

**Tổng số sửa đã tích luỹ cho tài liệu 02: 21** *(11 sau kho 06, +2 sau 09/10,
+8 sau 07/08)*, gồm **hai yêu cầu mới** (`WF-209` `finally`, `mock`) và **hai
câu hỏi mở mới** (`Q8` AiTransform).

⛔ **Không kho nào giải được:** `WF-403/404` (GPU, VRAM, thời lượng ước tính) và
`WF-501` (trần chi phí tất định). Đúng như sổ nợ `N1` đã cảnh báo — đây là phần
LTT **thiết kế một mình, không có đối chứng ngành**.

---

*Không sửa mã sản phẩm LTT. Không có mã Kestra hay Windmill nào được chép vào
`D:\LTTSTUDIOSAPP`. Windmill là AGPLv3 — chỉ đọc.*
