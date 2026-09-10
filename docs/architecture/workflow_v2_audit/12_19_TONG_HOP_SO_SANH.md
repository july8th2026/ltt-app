# 12–19 — TỔNG HỢP SO SÁNH NGANG (pha D, gộp 8 tài liệu)

> **Gộp** `12_TERMINOLOGY` · `13_EXECUTION_MODEL` · `14_CANVAS` · `15_NODE_SDK` ·
> `16_DURABILITY` · `17_PARALLELISM` · `18_SECURITY` · `19_LICENSE` thành một
> tài liệu. Chúng tổng hợp từ 04–10 chứ không đọc mã mới, nên tách ra chỉ làm
> loãng.
>
> **Nguồn:** bảy khảo sát 04·05·06·07+08·09·10. Mọi số liệu truy về đó.
> **Mục tiêu:** chốt bốn câu hỏi mở `Q1` `Q3` `Q5` `Q7`, và dựng bảng điểm.

---

## 12. TỪ VỰNG — CÙNG MỘT TỪ, BẢY NGHĨA

⛔ Đây là lý do đề bài §7 nói *"đừng tin cái tên"*. Bảng này quy mọi thứ về từ
vựng LTT (`02 §2`).

| Từ LTT | Activepieces | n8n | Node-RED | Kestra | Windmill | Trigger.dev | Temporal |
|---|---|---|---|---|---|---|---|
| **Workflow** | Flow | Workflow | Flow (tab) | Flow | Flow | — *(là mã)* | Workflow Type |
| **WorkflowVersion** | FlowVersion `LOCKED` | published version | — | revision | version | Deploy | Build ID |
| **WorkflowRun** | FlowRun | Execution | — *(không có)* | Execution | Flow job | TaskRun | Workflow Execution |
| **NodeType** | Piece + action | Node type | Node type (registry) | Task type | Script/Path | Task | Activity Type |
| **NodeInstance** | Action (`nextAction`) | Node | Node | Task | FlowModule | — | — |
| **Edge** | ❌ *(cây)* | connection | `wires[i][j]` | `dependsOn` | ❌ *(lồng nhau)* | ❌ | ❌ |
| **Port** | input field | connection index | ❌ *(1 vào)* | input | JSON schema | — | — |
| **NodeRun** | StepOutput | run data | ❌ | TaskRun | FlowStatusModule | **ExecutionSnapshot** | Event |
| **Attempt** | attempt | tryIndex | ❌ | attempt | retry | attemptNumber | Activity Attempt |
| **Waitpoint** | **Waitpoint** ⭐ | `waitTill` | ❌ | pause | `suspend` | **Waitpoint** ⭐ | Timer/Signal |
| **Artifact** | trong blob | **binary-data** ⭐ | trong `msg` | storage | S3 object | run-store | payload |
| **Trigger** | Trigger piece | Trigger node | Inject/HTTP | Trigger | **11 gói** ⭐ | schedule-engine | Schedule |
| **Job** | worker job | execution | ❌ | WorkerJob | queued job | TaskRun | Task |

🔴 **Ba cái bẫy đặt tên đã bắt được trong khảo sát này:**

1. **`EXECUTE_ALL_MATCH` của Activepieces** nghe như "chạy mọi nhánh khớp" — nó
   chạy chúng **tuần tự** (`04 §2.2`). Tên nói về *tập*, không nói về *cách*.
2. **"Canvas" của Activepieces** trông như đồ thị, thực chất vẽ từ **cây**
   (`04 §1.1`). Giao diện không phải bằng chứng kiến trúc.
3. **"Workflow" của Trigger.dev và Temporal** không phải đồ thị mà là **mã**.
   Chấm chúng bằng `WF-101/102` là chấm sai câu hỏi.

---

## 13. MÔ HÌNH THI HÀNH — và chốt `Q1`

### 13.1 Bảy hệ, bốn kiểu máy thi hành

| Kiểu | Ai | Cơ chế |
|---|---|---|
| **Thông dịch cây, một luồng** | Activepieces | `while(nextAction)` + `await` |
| **Máy ngăn xếp, một luồng** | n8n | `stack.shift()` + `await` |
| **Hướng thông điệp, đan xen** | Node-RED | `setImmediate` mỗi lượt giao cạnh |
| **Điều phối job bền** | Kestra · Windmill · Trigger.dev · **LTT** | trạng thái ở CSDL, worker kéo việc |
| *(riêng)* **Replay lịch sử** | Temporal | event sourcing + tất định |

⭐ **LTT đã ở đúng nhóm** — nhóm duy nhất chịu được `F3` (worker restart 13,6
lần/ngày) và `F4` (node = 20 phút GPU).

### 13.2 🔴 CHỐT `Q1` — điều kiện đặt trên CẠNH hay trong node ROUTER?

| Hệ | Cách làm |
|---|---|
| Activepieces | **node Router** có `children[]` |
| n8n | **node IF/Switch** có nhiều cổng ra |
| Node-RED | **node switch** |
| Kestra | **task `Switch`** |
| Windmill | ⭐ **cả hai** — `BranchOne` (node) **và** `skip_if` / `stop_after_if` (trên bước) |
| **LTT hôm nay** | **trên CẠNH** (`condition ∈ {success, error}`) |

**Sáu trên bảy dùng node.** Nhưng bằng chứng không nghiêng về node — nó nghiêng
về **hình dạng đồ thị của họ**: bốn hệ kia là **cây/lồng nhau**, nên rẽ nhánh
*bắt buộc* phải là một node có con. Họ không chọn; họ không có lựa chọn khác.

Windmill — hệ có mô hình phong phú nhất — dùng **cả hai**, và cách dùng phân
vai rõ:

```
BranchOne / BranchAll   → rẽ nhánh CÓ CẤU TRÚC (nhiều đường đi khác nhau)
skip_if / stop_after_if → ĐIỀU KIỆN CỤC BỘ trên một bước (bỏ qua / dừng sớm)
```

⭐ **Chốt `Q1`:** **giữ điều kiện trên CẠNH** (LTT có DAG thật, không cần node
để tạo nhánh), **và bổ sung `skip_if` ở cấp NODE** cho điều kiện cục bộ.
Lý do dứt điểm: một node Router trong LTT sẽ tạo một `NodeRun` thật, một
`attempt`, một dòng chi phí bằng 0 — **mỗi lần rẽ nhánh**. Với mô hình
`WF-301` (một hàng mỗi lần chuyển trạng thái) thì đó là hàng rác nhân theo số
nhánh. Cạnh thì không tốn hàng nào.
`HIGH` — có lập luận, có đối chứng Windmill.

### 13.3 🔴 CHỐT `Q5` — ngôn ngữ biểu thức

| Hệ | Biểu thức |
|---|---|
| Activepieces | **22 toán tử cố định**, OR-của-AND |
| n8n | JS đầy đủ trong `{{ }}` |
| Node-RED | JSONata + JS |
| Kestra | Pebble template |
| Windmill | **JS đầy đủ** (`results.step_id`, `flow_input`) |

Hai cực. Bên cố định: an toàn, hiển thị được bằng dropdown, đánh giá được trong
scheduler. Bên JS: mạnh, nhưng phải chạy sandbox.

⭐ **Chốt `Q5`: tập toán tử cố định + tham chiếu `$node.port`.** Ba lý do, mỗi
lý do đủ một mình:

1. **Biểu thức chạy trong scheduler**, và scheduler đang giữ khoá hàng (`WF-305`).
   Một biểu thức JS trong transaction là đúng lỗi `D4` mà LTT đang mắc với
   `verifier.verify()`.
2. **`WF-501` cần trần chi phí tất định.** Một biểu thức tuỳ ý làm `max_items`
   và `parallelism` không tính trước được.
3. Activepieces là bằng chứng sản phẩm: hàng nghìn người dùng, 10.077 connector,
   **không cần** ngôn ngữ biểu thức để rẽ nhánh.

⚠️ **Ngoại lệ đã chấp nhận:** `parallelism` **được phép** là biểu thức
(`07+08 §2.3`) vì nó phải đọc sức chứa lúc chạy. Nhưng chỉ trên một tập hàm
đóng (`resource.free_slots()`), không phải JS tuỳ ý.
`HIGH`

---

## 14. CANVAS — chốt `Q7`

| Hệ | Nền | Dòng mã lớp canvas |
|---|---|---:|
| **LTT** | **React 19 + @xyflow/react 12** | **2.061** *(toàn bộ ứng dụng)* |
| Node-RED | SVG tự viết + d3 | **10.203** *(chỉ lớp view)* |
| n8n | Vue | 289.149 *(toàn bộ frontend)* |
| Windmill | Svelte | 364.132 *(toàn bộ frontend)* |
| Kestra | Vue | 58.444 |
| Activepieces | React | 169.427 |
| Trigger.dev / Temporal | *không có canvas* | — |

🔴 **CHỐT `Q7`: GIỮ React Flow.** `CONFIRMED` bằng số đo.

Node-RED là đối chứng định lượng duy nhất *cùng phạm vi* (tự viết lớp canvas):
**10.203 dòng cho lớp view**, so với **2.061 dòng cho cả ứng dụng canvas** của
LTT — **gấp 5×**, và LTT đã có sẵn: cổng có kiểu, chặn nối sai kiểu, chặn chu
trình, undo/redo 50 bước, copy/paste remap `$ref`, chèn node giữa cạnh, minimap,
đồng thời lạc quan 409, pages/frames/notes (`01 §10.1`).

**Điều Canvas LTT còn thiếu — và không cái nào cần đổi thư viện:**

| Thiếu | Lấy từ |
|---|---|
| auto-layout thật (nay xếp lưới 4 cột) | dagre/ELK — thêm thư viện, không đổi nền |
| hiển thị chi phí + tài nguyên trên node | tự làm |
| ⭐ **frontend đang biết tên tool cụ thể** (`WF-704`, vi phạm) | phải sửa, không liên quan React Flow |
| ⭐ **luật kiểu nối dây viết tay ở 2 nơi** (`WF-703`) | phải sinh từ một nguồn |

---

## 15. SDK NODE — ai làm cho người ngoài viết được?

| Hệ | Bằng chứng định lượng | Cơ chế |
|---|---|---|
| **Activepieces** | ⭐ **926.762 dòng / 10.077 tệp** connector = **67 % kho** | `packages/pieces`, khai bằng TS |
| n8n | `nodes-base` + `@n8n/create-node` | cặp `.node.ts` + credential |
| Node-RED | `registry` + cặp `.js`/`.html` | npm package |
| Windmill | script bất kỳ (Python/TS/Go/Bash) | không cần SDK |
| **LTT** | **15 `ToolSpec` / 11 app** | `AppManifest` + `ToolSpec` |

⭐ **Activepieces thắng tuyệt đối về bằng chứng** — 67 % kho là do người ngoài
viết. Đó là thước đo duy nhất đáng tin cho "SDK có dễ không".

**Ba thứ họ có mà `ToolSpec` chưa có:**

1. **Ghim phiên bản node type trong chính node** — `pieceName` **+** `pieceVersion`
   (`04 §9`). LTT ghim `tool.name` mà **không** ghim version ⇒ đổi schema của
   một tool làm gãy mọi workflow đã lưu, âm thầm.
2. **`mock` trong lược đồ** (Windmill) — thử workflow không tốn GPU.
3. **`side_effect`** (Temporal, dưới dạng hợp đồng tài liệu) — quyết định hành vi
   khôi phục.

⇒ `WF-705` giữ nguyên (**SDK = mở rộng `AppManifest`, không dựng registry thứ
hai**), nhưng `ToolSpec` phải thêm: `type_version` · `side_effect` ·
`idempotency.key_fields` · hỗ trợ `mock`.

---

## 16. TÍNH BỀN — chốt `Q3`

### 16.1 Bốn mô hình, và ai dùng

| Mô hình | Ai | Nhược điểm quan sát được |
|---|---|---|
| **A. Một khối sửa được** | Activepieces (tệp) · n8n (cột `text`) · **LTT (JSON)** | n8n **phải xây `db\|fs\|s3\|az`** để cứu; Activepieces có `LOG_SIZE_EXCEEDED` + `MEMORY_LIMIT_EXCEEDED` |
| **B. Không lưu** | Node-RED | mất im lặng khi restart |
| **C. Chuỗi ảnh chụp bất biến** | ⭐ **Trigger.dev** | nhiều hàng hơn — nhưng chỉ-thêm nên không tranh chấp |
| **D. Event sourcing + replay** | Temporal | **đòi mã tất định**, và máy chủ **không cưỡng chế được** |

### 16.2 🔴 CHỐT `Q3`: mô hình **C**

```
node_run_snapshots   một hàng MỖI LẦN chuyển trạng thái · chỉ thêm
  ├─ previous_snapshot_id   → chuỗi liên kết
  ├─ is_valid + error       → GHI CẢ LẦN CHUYỂN BỊ TỪ CHỐI
  ├─ execution_status       → trạng thái thi hành
  ├─ run_status             → trạng thái công khai
  └─ completed_waitpoints   → quan hệ
```

**Bốn lý do, mỗi lý do độc lập:**

1. **Phá được ngưỡng `M1`.** Mô hình A buộc đọc–sửa–ghi toàn bộ ⇒ `31+N` câu SQL
   mỗi tick. Mô hình C ghi `O(số node vừa đổi)`.
2. **Giải luôn `WF-805`** — chuỗi snapshot **chính là** dòng thời gian. Không
   cần bảng nhật ký thứ hai.
3. **Không trả giá tất định** như mô hình D. Bước của LTT là lời gọi provider,
   không thể tất định (`10 §2.2`).
4. **`is_valid` + `error`** cho phép điều tra chuyển trạng thái tranh chấp — thứ
   `runs.transition()` của LTT hôm nay ném đi không dấu vết, trong khi `F3` nói
   tranh chấp **sẽ** xảy ra.

`HIGH` — dựa trên một hệ sản xuất (Trigger.dev) + ba hệ chứng minh mô hình A hỏng.

---

## 17. SONG SONG — bảng dứt điểm

| Hệ | Trong MỘT lượt chạy | Khai báo được? | Trần |
|---|---|---|---|
| Activepieces | ❌ tuần tự | — | — |
| n8n | ❌ tuần tự | — | instance-global, **tắt ở chế độ queue** |
| Node-RED | ✅ **đan xen** (`setImmediate`) | ❌ | **không có** |
| Kestra | ✅ | ⭐ `Concurrency{limit, **behavior**}` | theo flow |
| **Windmill** | ✅ **thật** | ⭐⭐ **`parallel` theo NODE + `parallelism` là BIỂU THỨC** | theo node |
| Trigger.dev | ✅ nhiều run | ✅ theo tenant | ⭐⭐ **lọc hàng đợi hết chỗ TRƯỚC khi chọn** |
| Temporal | ✅ | ✅ | trọng số công bằng `<pass,id>` |
| **LTT hôm nay** | 🟡 **trần cứng 4 step** | ❌ | hằng số trong mã |

⭐ **Ba mảnh ghép cho `WF-201/202`, mỗi mảnh từ một kho khác nhau:**

```
Trigger.dev  →  LỌC hàng đợi hết sức chứa trước khi chọn      (giải F2: 92%)
Windmill     →  parallel/parallelism khai THEO NODE, là BIỂU THỨC
Kestra       →  behavior khi chạm trần: QUEUE | CANCEL | FAIL
```

Không kho nào có cả ba. **LTT sẽ là kho đầu tiên** — và đó không phải sáng tạo,
là ghép ba thứ đã được chứng minh riêng lẻ.

---

## 18. BẢO MẬT & SANDBOX

| Hệ | Cách ly mã bước | Bí mật | Đa tenant |
|---|---|---|---|
| Activepieces | sandbox riêng (`packages/server/sandbox`) | app-connection | project |
| n8n | `html-sandbox`, `Code` node trong vm | credential mã hoá | project/EE |
| Node-RED | ❌ **không** — node chạy trong tiến trình | `credentials` | ❌ **không** |
| Kestra | script runner (docker) | secret | namespace |
| Windmill | ⭐ `sandbox-image`, nsjail | resource/variable | workspace |
| Trigger.dev | container theo deploy | env | ⭐ environment |
| Temporal | ⭐ **mã chạy trên máy NGƯỜI DÙNG** | ngoài phạm vi | ⭐ namespace |

⭐ **LTT ở vị trí thuận lợi và nên giữ:** `WF` không chạy mã người dùng
(`02 §1.2` cấm custom code node). Mọi bước là một `Job` gọi app **trong kho của
ta**. ⇒ **Không cần sandbox**, và đó là một tài sản, không phải một thiếu sót.

Điểm cần vá, đã biết: `WF-903` — quyền tool được kiểm lúc `validate` nhưng
**không kiểm lại lúc thi hành** (`01 §13.3`). Một version đã publish vẫn chạy
sau khi quyền bị thu hồi.

---

## 19. GIẤY PHÉP — bảng quyết định

| Kho | Giấy phép | Chép mã vào LTT? | Căn cứ (trích từ bản clone) |
|---|---|---|---|
| **Temporal** | **MIT** | 🟢 **được** | `LICENSE`: "The MIT License" |
| **Node-RED** | **Apache-2.0** | 🟢 được (giữ NOTICE) | `LICENSE` (OpenJS Foundation) |
| **Kestra** | **Apache-2.0** | 🟢 được (giữ NOTICE) | `LICENSE` |
| **Trigger.dev** | **Apache-2.0** | 🟢 **được** — và là kho ta muốn mượn nhất | `LICENSE` |
| **Activepieces** | MIT **trừ `ee/`** | 🟡 né `packages/ee/` (1.099 dòng/4 tệp) | `LICENSE`: "Portions… licensed as follows" |
| **n8n** | **Sustainable Use + EE** | 🔴 **không** | `LICENSE.md`: files with `.ee.` "are NOT licensed under the Sustainable Use License" |
| **Windmill** | **AGPLv3** | 🔴 **không** | `LICENSE`: "Every file is under License AGPL unless otherwise specified" |

⭐ **May mắn về mặt pháp lý:** hai thứ LTT muốn mượn nhất — **chuỗi ảnh chụp bất
biến** và **lọc hàng đợi hết sức chứa** — đều ở **Trigger.dev (Apache-2.0)**.
Hai thứ ở vùng đỏ (Windmill `parallelism`, n8n `binary-data`) là **ý tưởng thiết
kế**, và ý tưởng không có bản quyền — chỉ **cách diễn đạt** mới có.

⛔ Không phải tư vấn pháp lý. Trước khi chép bất kỳ dòng nào từ nhóm 🟡/🔴, cần
rà soát pháp lý của người dùng.

---

## 20. BẢNG ĐIỂM — chấm theo TOÀN BỘ 41 yêu cầu của LTT

⚠️ Sửa lỗi phương pháp đã tự bắt ở `07+08 §4`: chấm mọi kho theo **toàn bộ** yêu
cầu, không chỉ theo câu hỏi của nhóm nó bị xếp vào.

| Kho | ⭐ | ✅ | 🟡 | ❌ | Đóng góp quyết định |
|---|--:|--:|--:|--:|---|
| **Temporal** | **11** | 3 | 1 | 6 | cách **viết bảo đảm**; bằng chứng **không** chọn replay |
| **Windmill** | **9** | 5 | 5 | 3 | `parallel`/`parallelism` theo node; `mock`; 11 gói trigger |
| **Trigger.dev** | **7** | 10 | 4 | 4 | **ảnh chụp bất biến**; **lọc sức chứa** |
| n8n | 6 | 13 | 6 | 5 | `binary-data`; cạnh có kiểu |
| Activepieces | 5 | 10 | 4 | 10 | **waitpoint + barrier + `sealed`** |
| Kestra | 4 | 8 | 4 | 3 | `Concurrency{limit,behavior}`; **`finally`** |
| Node-RED | 3 | 7 | 4 | 17 | **6 hook trên cạnh** |

⛔ **Đừng đọc bảng này thành xếp hạng để chọn một kho.** Temporal đứng đầu ⭐ và
lại là kho **ít phù hợp nhất** để adopt (`10 §6`). Điểm ⭐ đo *"có thứ đáng
học"*, không đo *"nên dùng"*.

### 20.1 Không kho nào có, LTT phải tự thiết kế

| Yêu cầu | Vì sao không ai có |
|---|---|
| `WF-403/404` GPU · VRAM · thời lượng ước tính | không hệ nào lập lịch quanh **một** thiết bị vật lý dùng chung |
| `WF-501` **trần chi phí tất định tính trước** | bước của họ gần như miễn phí ⇒ không ai cần |
| `WF-202` sức chứa đọc từ **tài nguyên thật** | Trigger.dev đọc bộ đếm **của chính nó**; LTT phải hỏi GPU/máy B |

⇒ Ba mục này vào `23_TARGET_ARCHITECTURE` với nhãn
**`INFERRED — không có đối chứng OSS`**, đúng như sổ nợ `N1` yêu cầu.

---

## 21. BỐN CÂU HỎI MỞ — ĐÃ CHỐT

| # | Câu hỏi | Chốt | Mức |
|---|---|---|---|
| **Q1** | Điều kiện trên cạnh hay node Router? | **trên CẠNH** + bổ sung `skip_if` cấp node | `HIGH` |
| **Q3** | Trạng thái: bảng sửa được hay event log? | **mô hình C — chuỗi ảnh chụp BẤT BIẾN** | `HIGH` |
| **Q5** | Ngôn ngữ biểu thức? | **tập toán tử cố định**; ngoại lệ: `parallelism` | `HIGH` |
| **Q7** | Giữ React Flow? | **GIỮ** — đối chứng 5× của Node-RED | `CONFIRMED` |

**Còn mở:** `Q2` (JSONB / bảng chuẩn hoá / lai) · `Q4` (LISTEN/NOTIFY hay bảng
đánh thức) · `Q6` (bỏ Plan v1? — chờ số đếm production) · `Q8` (`AiTransform`?).
Cả bốn thuộc pha F, sẽ chốt ở tài liệu 23/24/25.

---

## 22. TỔNG SỐ SỬA CHO TÀI LIỆU 02: **21**

| Từ kho | Sửa |
|---|---|
| Activepieces | `sealed` · `NOT_DISPATCHED` · `Q5` nghiêng về toán tử cố định |
| n8n | **ba** loại cạnh (`DATA\|CONTROL\|RESOURCE`) · id artifact tự mô tả backend · thứ tự duyệt là hợp đồng · UNIQUE bộ phận |
| Node-RED | **middleware trên cạnh** (`WF-805`) · `WF-106` chọn lượt-chạy-con · `Q7` giữ React Flow |
| Trigger.dev | `WF-301` → **chuỗi ảnh chụp** · lưu chuyển trạng thái **thất bại** · `RUNNING`⇄`WAITING` không loại trừ · tách lỗi hệ thống/nghiệp vụ · waitpoint **nhiều-nhiều** · `output` trên waitpoint · lọc sức chứa ở tầng **chọn hàng đợi** |
| Temporal | `WF-302` thêm cột **"nghĩa vụ thuộc về ai"** · `WF-303` reconcile lên `HIGH` · `side_effect` thành **bắt buộc** |
| Kestra+Windmill | `behavior` tràn · `parallel` theo node · `parallelism` là biểu thức · trường loại trừ khỏi hash · **`WF-209` `finally`** · TTL theo bước · `timeout` là biểu thức · `required_events` · **`mock`** · **`Q8`** |

**Hai yêu cầu MỚI:** `WF-209` (`finally`) và `mock` trong lược đồ.
**Một câu hỏi MỚI:** `Q8` (`AiTransform`).

---

## 23. PHA D ĐÓNG — VÀO PHA E/F

Còn lại, theo thứ tự:

```
21  LTT_GAP_ANALYSIS          ← đã tích luỹ sẵn 6 mục cụ thể
22  KEEP_ADOPT_ADAPT_REWRITE  ← ma trận quyết định
23  TARGET_ARCHITECTURE       ← chốt Q4
24  TARGET_DATA_MODEL         ← chốt Q2
25  NODE_SDK_PROPOSAL         ← chốt Q8
26  EXECUTION_STATE_MACHINE
27  MIGRATION_STRATEGY        ← chốt Q6 (cần số đếm production)
28  IMPLEMENTATION_ROADMAP
29  RISK_REGISTER
30  FINAL_ARCHITECTURE_DECISION + ADR + 00_EXECUTIVE_SUMMARY
```

---

*Không sửa mã sản phẩm LTT. Không chép mã bên thứ ba vào kho.*
