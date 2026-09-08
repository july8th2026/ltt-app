# 02 — YÊU CẦU CỦA LTT WORKFLOW V2

> **Quy tắc của bước này.** Yêu cầu phải được chốt **TRƯỚC** khi tải bất kỳ kho
> mã nguồn mở nào. Không dự án nào được phép định nghĩa bài toán của chúng ta.
> Sau tài liệu này, mọi hệ thống OSS chỉ được chấm điểm **theo bảng dưới đây**,
> không theo điểm mạnh mà nó tự quảng cáo.
>
> **Đầu vào:** `01_CURRENT_LTT_ARCHITECTURE.md` (đo 2026-09-07, commit `9e73bf1f`).
> **Ngày chốt:** 2026-09-07.
> **Chưa tải kho OSS nào.** `CONFIRMED` — `../LTT_ARCHITECTURE_LAB/` chưa tồn tại.

---

## 0. BỐN SỰ THẬT ĐO ĐƯỢC ĐỊNH HÌNH MỌI YÊU CẦU BÊN DƯỚI

Không phải nguyên tắc. Là số đo. Mỗi yêu cầu trong tài liệu này truy về ít nhất
một trong bốn dòng sau.

| # | Sự thật | Đo ở đâu | Hệ quả |
|---|---|---|---|
| **F1** | Engine hiện tại **chưa từng chạy** trên production (0 `agent.advance` / 28 ngày) | 01 §A.1 | Không có di trú runtime. Được phép thiết kế lại tầng executor từ đầu. |
| **F2** | **92 %** lượt nhặt job kết thúc bằng *nhả ra vì tài nguyên bận*; 13,7 lượt nhặt cho mỗi job xong | 01 §A.3 | Khan hiếm tài nguyên là **trạng thái thường trực**, không phải ngoại lệ. Lập lịch phải nhận biết tài nguyên. |
| **F3** | Worker khởi động lại **13,6 lần/ngày**; `AmbiguousProviderError` **10 lần/28 ngày** | 01 §A.6, §A.4 | Bền qua crash không phải tính năng nâng cao — là điều kiện vận hành hằng ngày. |
| **F4** | Tải thật = **ít loại việc, mỗi việc nặng** (89 % là `ltt_llm.chat`, phần còn lại là ảnh/giọng/video) | 01 §A.2 | LTT **không** là Zapier. Tối ưu cho *ít node, node đắt* chứ không cho *nhiều node, node rẻ*. |

⭐ **F4 là điều dễ chép sai nhất từ OSS.** Mọi nền tảng automation phổ biến tối
ưu cho hàng nghìn bước rẻ (gọi HTTP, ghi dòng Sheets). Một node của LTT có thể
là **20 phút A100** hoặc **2 GB video**. Trần `MAX_STEPS=100` hiện tại **không
phải** giới hạn cần phá bằng mọi giá — xem `WF-101`.

---

## 1. PHẠM VI, PHI PHẠM VI, VÀ ĐIỀU BẤT KHẢ XÂM PHẠM

### 1.1 Workflow V2 LÀ gì

Một **runtime thi hành đồ thị bền vững**, đa tenant, biết tài nguyên, tính được
tiền trước, chạy trên hạ tầng job/credit/GPU **đang có**, và phục vụ **ba** mặt
tiêu thụ: Canvas (người), Agent (LLM lập kế hoạch), Public API (máy).

### 1.2 Workflow V2 KHÔNG phải gì (phi phạm vi, chốt cứng)

| Không làm | Vì sao |
|---|---|
| Không thay hàng đợi `jobs` bằng Redis/Kafka/Temporal-history | 01 §12 mục 2 — đang phục vụ khách thật, đã trả giá |
| Không thay sổ credit | 01 §12 mục 3 |
| Không thay hợp đồng app (`AppManifest`) | 01 §12 mục 1 — chỉ **mở rộng** |
| Không thay lease GPU 3 tầng | 01 §12 mục 7 |
| Không phá 24 route `/api/v1` đóng băng | test hai chiều đang chốt |
| Không viết ngôn ngữ workflow riêng (DSL/script) | F4: ít node đắt, không cần biểu đạt phức tạp; và một DSL là một trình biên dịch phải nuôi |
| Không chạy mã do người dùng gửi lên (custom code node) | bề mặt sandbox không tương xứng lợi ích, ở giai đoạn này |
| Không làm "engine tổng quát cho mọi người" | LTT là sản phẩm, không phải nền tảng OSS |

### 1.3 Bất khả xâm phạm — bốn ranh giới V2 không được vượt

1. **Chi phí tối đa phải tính được TRƯỚC khi chạy, tất định, không cần LLM.**
   *(kế thừa `validator` + `budget.quote`, 01 §4.3)*
2. **Chi phí thực tế không bao giờ vượt số đã giữ chỗ.**
   *(kế thừa `ensure_can_spend`, 01 §7)*
3. **Side effect ngoài là at-most-once khi kết quả không xác định.**
   *(kế thừa `provider_state = ambiguous`, 01 §6.2 — F3 chứng minh nó cần thật)*
4. **Nền tảng không được biết tên app/tool nào tồn tại.**
   *(kế thừa `registry.py`; và V2 phải sửa cả vi phạm hiện có ở frontend, 01 §C1)*

---

## 2. TỪ VỰNG CHÍNH THỨC (dùng nhất quán từ đây trở đi)

Định nghĩa trước, so sánh sau. Bảng ánh xạ sang thuật ngữ OSS sẽ nằm ở
`12_TERMINOLOGY_MAPPING.md`.

```
App              đơn vị sản phẩm, sở hữu tool + job + bảng riêng      (ĐÃ CÓ)
Tool             năng lực nghiệp vụ do app khai                       (ĐÃ CÓ: ToolSpec)
NodeType         hình dạng một node trên đồ thị = chiếu của Tool      (MỚI, dẫn xuất)
NodeInstance     một node cụ thể trong một WorkflowVersion            (MỚI, có id bền)
Port             một đầu vào/ra có KIỂU của NodeType                  (ĐÃ CÓ, cần mạnh hơn)
Edge             thực thể bậc một nối (node,port) → (node,port)       (MỚI — nay chỉ là dẫn xuất)
Workflow         vật thể người dùng sở hữu, có tên, có bản nháp       (ĐÃ CÓ: AgentWorkflow)
WorkflowVersion  ảnh chụp BẤT BIẾN đã publish, có hash                (MỚI)
WorkflowRun      một lượt thi hành, GHIM vào đúng một WorkflowVersion (ĐÃ CÓ một nửa: AgentRun)
NodeRun          trạng thái thi hành của MỘT node trong MỘT run       (MỚI — nay là khoá JSON)
Attempt          một lượt thử của một NodeRun                         (MỚI — nay là số nguyên)
Job              đơn vị công việc trong hàng đợi                      (ĐÃ CÓ)
Worker           tiến trình chạy job                                  (ĐÃ CÓ)
Waitpoint        điểm run tạm dừng, KHÔNG giữ tài nguyên nào          (MỚI)
Artifact         tệp/khối dữ liệu có danh tính bền, tách khỏi state    (MỚI)
Connection       tham chiếu bí mật/tài khoản dùng cho một node         (MỚI, khác ApiKey hiện có)
Trigger          nguồn khởi tạo một WorkflowRun                        (MỚI, nay chỉ manual+hẹn giờ)
Agent            thứ TẠO/SỬA workflow. KHÔNG phải thứ chạy workflow.   (ĐÃ CÓ)
```

**Quy ước ID trong tài liệu này:**
`WF-1xx` mô hình đồ thị · `WF-2xx` thi hành · `WF-3xx` bền vững · `WF-4xx` tài
nguyên/GPU · `WF-5xx` tiền · `WF-6xx` artifact · `WF-7xx` mở rộng/SDK ·
`WF-8xx` API/trigger · `WF-9xx` bảo mật/vận hành.

**Mức ưu tiên:** `MUST` (V2 không có nó thì không phải V2) · `SHOULD` (thiếu
thì V2 vẫn dùng được nhưng nợ) · `MAY` (giai đoạn sau, nhưng kiến trúc **không
được cấm**).

---

## 3. WF-1xx — MÔ HÌNH ĐỒ THỊ

### WF-101 · Đồ thị có hướng, không chu trình, nhiều cha nhiều con — `MUST`

`WorkflowVersion = (Nodes[], Edges[])`. Cho phép fan-out, fan-in, nhiều cha,
nhiều con, nhiều thành phần liên thông trong cùng một version.

**Trần đề xuất:** **500 node / version** (nay 100).
*Vì sao 500 chứ không phải 10.000:* F4 — một node là một việc đắt. 500 node ×
giá tối thiểu đã là một hoá đơn không ai bấm duyệt. Trần tồn tại để **chặn
kế hoạch hỏng của LLM**, không phải để chặn người dùng.
**Nghiệm thu:** validate 500 node < 300 ms; từ chối node thứ 501 bằng lỗi rõ nghĩa.

### WF-102 · Edge là thực thể bậc một — `MUST`

```
Edge {
  id, workflow_version_id,
  source_node, source_port,
  target_node, target_port,
  kind: DATA | CONTROL,
  condition: expr | null,
  metadata
}
```

**Vì sao đây là yêu cầu chứ không phải tuỳ chọn.** Hôm nay handle của edge
**bị vứt bỏ** khi dựng Plan (01 §3.4); dữ liệu thật đi bằng chuỗi `"$n.port"`
trong params, và hai biểu diễn được giữ khớp **bằng tay ở trình duyệt**. Đó là
một bất biến do client cưỡng chế — thứ mà một khách gọi API sẽ phá ngay lần
đầu.
**Nghiệm thu:** đồ thị dựng qua API (không qua Canvas) cho **cùng** kết quả thi
hành như đồ thị vẽ trên Canvas; xoá một edge làm mất đúng một ràng buộc, không
để lại tham chiếu mồ côi.

### WF-103 · Tách DATA edge và CONTROL edge, **khai báo tường minh** — `MUST`

```
DATA edge     : output của A chảy vào input của B  ⇒ B phụ thuộc A (suy ra)
CONTROL edge  : B chỉ được chạy sau khi A đạt trạng thái X (không truyền dữ liệu)
```

**Vì sao.** LTT **đã có** control edge — do tai nạn (01 §3.4): một cạnh không
kèm tham chiếu chính là control edge, nhưng không ai khai là có, không vẽ được
có chủ đích, và không tài liệu nào nói. Một năng lực tồn tại mà không khai là
một năng lực sẽ bị phá lúc refactor.
**Nghiệm thu:** `kind` là trường bắt buộc; validator từ chối DATA edge không có
`source_port`/`target_port`; từ chối CONTROL edge **có** cổng.

### WF-104 · NodeType tách khỏi NodeInstance — `MUST`

```
NodeType     ← chiếu 1:1 (hoặc 1:n theo lane) từ ToolSpec. KHÔNG phải bảng chép tay.
NodeInstance { id, type_ref, type_version, config, position, policies… }
```

**Ràng buộc quyết định:** `ToolSpec` **nuôi** NodeType, không phải là NodeType.
*Vì sao:* `ToolSpec` đã mang `job_type`, `admission_resource`, `sync_executor`,
`job_type_lanes` — thứ thuộc về **thi hành**. NodeType cần thêm thứ thuộc về
**đồ thị** (cardinality cổng, cổng biến thiên, giá trị mặc định UI). Trộn hai
vai vào một dataclass frozen sẽ buộc mọi app phải sửa manifest khi Canvas đổi.
**Nghiệm thu:** thêm một trường chỉ-Canvas vào NodeType **không** đụng
`registry.ToolSpec`; và không app nào phải sửa để lên V2.

### WF-105 · Version bất biến, có hash, run ghim vào version — `MUST`

```
Workflow  ──► Draft (sửa tự do)  ──publish──►  WorkflowVersion (BẤT BIẾN, có hash)
                                                      ▲
                                          WorkflowRun ─┘ ghim, không bao giờ đổi
```

`hash = sha256(chuẩn hoá tất định của {nodes, edges, schema_version})`.

**Vì sao.** Hôm nay `AgentRun.plan` **đã** được đóng băng (tốt), nhưng
`AgentWorkflow.revision` chỉ là bộ đếm tự tăng mỗi lần lưu — không có khái niệm
"bản đã publish". Một khách API muốn gọi *"chạy bản v3"* không có gì để trỏ tới.
**Nghiệm thu:** sửa Canvas trong lúc một run đang chạy → run không đổi hành vi;
hai lần publish nội dung giống hệt → cùng một hash; báo giá gắn với hash.

### WF-106 · Subgraph / Workflow-as-Node — `SHOULD`

Một `WorkflowVersion` được dùng làm một node trong version khác, với **hợp đồng
vào/ra tường minh** và **ghim version**.

**Vì sao `SHOULD` chứ không `MUST`:** hôm nay hoàn toàn không có (01 §3.3), và
F4 nói workflow của LTT không sâu. Nhưng **kiến trúc không được cấm nó** — cụ
thể: `NodeType` phải cho phép một type mà `job_type` rỗng (WF-206), và
`WorkflowRun` phải có `parent_run_id` + `parent_node_run_id` **ngay từ v2.0**,
kể cả khi chưa dùng. Thêm cột sau khi đã có dữ liệu tốn hơn nhiều.

### WF-107 · Page là khái niệm TRÌNH SOẠN, không phải phạm vi thi hành — `MUST`

Hôm nay chỉ page đang mở được chạy, âm thầm (01 §3.3). Hai đường ra hợp lệ:
(a) một version thi hành **toàn bộ** node của mọi page; (b) page trở thành
subgraph thật (WF-106). **Không được giữ hành vi im lặng hiện tại.**
**Nghiệm thu:** không tồn tại đồ thị hợp lệ nào mà một node nằm trong version
lại không bao giờ có `NodeRun`.

---

## 4. WF-2xx — MÔ HÌNH THI HÀNH

### WF-201 · Song song có ràng buộc, và ràng buộc phải KHAI ĐƯỢC — `MUST`

Trần song song hôm nay là hằng số **4 step**, không truyền được từ đâu
(01 §5.3). V2 phải có **bốn** tầng trần, đồng thời:

```
1. theo run          workflow_version.max_parallel_nodes        (mặc định 8)
2. theo tài nguyên   sức chứa của admission resource            (F2 — tầng THẬT SỰ chặn)
3. theo tenant       số node đang chạy của một user
4. theo node         max_parallel của riêng node (vd loop)
```

**Trần thật của hệ thống là (2), không phải (1).** F2 cho thấy 92 % lượt nhặt
đã bị tài nguyên chặn — nên tăng (1) mà không đụng (2) chỉ làm tăng số vòng
nhặt-rồi-nhả. Đây là bẫy *"phanh luôn ăn tệ hơn không có phanh"* ở chiều ngược
lại: đặt trần **trên** nhu cầu thì trần biến mất, việc chặn dồn hết xuống tầng
tài nguyên và biểu hiện thành lãng phí.
**Nghiệm thu:** đo được số lượt `claim→defer` **giảm** so với đường cơ sở 13,7
lượt/job (01 §A.3). Nếu không giảm, thiết kế sai.

### WF-202 · Lập lịch nhận biết tài nguyên — `MUST` 🔴

**Đây là yêu cầu có bằng chứng mạnh nhất trong toàn tài liệu.**

Hôm nay: `claim()` nhặt job mà **không biết** `llm_remote` còn suất không, rồi
mới giành lease, thất bại thì `defer_resource`. Đo được: **9.833 / 10.663 =
92,2 %** lượt nhặt của `ltt_llm.chat` kết thúc bằng nhả ra (01 §A.3).

Yêu cầu: **không nhặt một việc mà tài nguyên của nó chắc chắn không có chỗ.**
Ba cách hợp lệ (chọn ở `23_TARGET_ARCHITECTURE.md`):
(a) `claim` lọc theo sức chứa còn lại của resource; (b) hàng đợi tách theo
resource, worker đăng ký theo resource; (c) đánh thức theo sự kiện "resource
vừa rảnh" thay vì quay vòng theo thời gian.

**Nghiệm thu:** tỉ lệ `defer / claim` ≤ 20 % trên cùng hỗn hợp tải của §A.2.

### WF-203 · JOIN nhiều ngữ nghĩa — `MUST` (ALL, ANY, N-of-M) / `MAY` (barrier)

Hôm nay chỉ có `ALL` (01 §5.4). Cần tối thiểu:

| Ngữ nghĩa | Node READY khi | Ưu tiên |
|---|---|---|
| `ALL` | mọi cha `SUCCEEDED` | `MUST` (đã có) |
| `ANY` / `FIRST_SUCCESS` | cha đầu tiên `SUCCEEDED`; **huỷ các cha còn lại** | `MUST` |
| `N_OF_M` | ≥ N cha `SUCCEEDED` | `MUST` |
| `FIRST_COMPLETE` | cha đầu tiên terminal (kể cả lỗi) | `SHOULD` |
| `BARRIER` | mọi cha terminal, bất kể kết quả | `SHOULD` |

⚠️ **`ANY` có hệ quả tiền.** Huỷ nhánh thua nghĩa là **đã tiêu tiền cho việc bị
vứt**. Trần chi phí (WF-501) phải tính theo **mọi nhánh có thể chạy**, không
theo nhánh thắng. Đây là chỗ dễ tính sai nhất.

### WF-204 · ForEach / Map với concurrency — `MUST` 🔴

Hôm nay **không có** (01 §8.4). `fanout ≤ 4` là *N bản sao cùng tham số*, không
phải map trên một danh sách.

```
ForEach {
  over: <ref tới port kiểu ...[]>
  concurrency: int          (bị chặn thêm bởi WF-201 tầng 2)
  max_items: int            (bắt buộc, hữu hạn — trần chi phí cần nó)
  on_item_error: FAIL_ALL | CONTINUE | COLLECT_ERRORS
  output: gom theo THỨ TỰ ĐẦU VÀO, không theo thứ tự hoàn thành
}
```

**Bắt buộc:** *thử lại được MỘT phần tử*, *tiếp tục được bộ sưu tập dở dang sau
crash*. F3 nói crash là chuyện hằng ngày; một map 100 ảnh mà mất hết vì worker
restart là không dùng được.
**Nghiệm thu:** map 100 phần tử, giết worker ở phần tử thứ 50, khôi phục →
đúng 100 kết quả, không có phần tử nào chạy hai lần.

### WF-205 · Rẽ nhánh có điều kiện dựa trên DỮ LIỆU — `MUST`

Hôm nay chỉ có `success`/`error` trên cạnh (01 §5.5). Cần thêm điều kiện đọc
được **giá trị đầu ra**.

**Quyết định kiến trúc phải chốt:** điều kiện đặt **trên cạnh** hay trong một
**node Router**?
**Khuyến nghị của tài liệu này: trên cạnh**, vì (a) LTT đã đi đường đó với
`condition ∈ {success,error}`, (b) một node Router thêm một NodeRun không làm gì
— tức thêm một hàng, một attempt, một dòng chi phí bằng 0 cho mỗi lần rẽ.
Phải xác minh lại ở `13_EXECUTION_MODEL_COMPARISON.md`.

**Ngôn ngữ biểu thức: giới hạn cứng, không Turing-complete.** So sánh, tồn tại,
`and/or/not`, truy cập trường. Không vòng lặp, không gọi hàm, không truy cập
mạng. *Vì sao:* biểu thức chạy **trong** scheduler, và scheduler đang giữ khoá.

### WF-206 · Node không sinh Job — `MUST`

Cần các NodeType không đi qua hàng đợi: `Const/Input`, `Router`, `Join`,
`Delay`, `Approval`, `Subworkflow`, `Collect`. Chúng có `NodeRun` (để quan sát
và bền vững) nhưng **không** có `Job` và **không** tốn credit.

**Vì sao là yêu cầu:** `ToolSpec.job_type` hiện là bắt buộc. Không có đường này
thì mọi nguyên hàm điều khiển phải giả trang thành một job — thêm một vòng
hàng đợi, một lượt claim, một dòng sổ tiền bằng 0 cho mỗi lần rẽ nhánh.

### WF-207 · Máy trạng thái tường minh, được cưỡng chế — `MUST`

```
WorkflowRun : CREATED → VALIDATING → QUEUED → RUNNING ⇄ WAITING
                                        → SUCCEEDED | FAILED | CANCELLED | TIMED_OUT
NodeRun     : PENDING → READY → QUEUED → RUNNING ⇄ WAITING
                                        → SUCCEEDED | FAILED | SKIPPED | CANCELLED
Attempt     : CREATED → RUNNING → SUCCEEDED | FAILED | TIMED_OUT | ABANDONED
```

`ABANDONED` = worker chết sau khi provider đã nhận (kế thừa `ambiguous`, F3).

**Cưỡng chế bằng bảng chuyển như `runs._TRANSITIONS` hiện có** — mô hình đó
đúng và phải giữ. **Nghiệm thu:** không có đường mã nào gán trạng thái trực
tiếp; mọi chuyển đi qua một hàm kiểm.

### WF-208 · Huỷ và timeout lan truyền — `MUST`

Huỷ run → mọi NodeRun chưa terminal thành `CANCELLED`, mọi Job đang chạy được
báo huỷ **hợp tác** (kế thừa `jobs.cancel`, không kill mù), waitpoint bị đóng,
credit được kết sổ đúng một lần. Timeout ở ba tầng: attempt, node, run.

---

## 5. WF-3xx — BỀN VỮNG (yêu cầu nặng nhất, vì F3)

### WF-301 · Trạng thái thi hành là HÀNG CSDL, không phải một khối JSON — `MUST` 🔴

Hôm nay toàn bộ trạng thái nằm trong `AgentRun.checkpoint` (JSON), bị **đọc–
sửa–ghi toàn bộ mỗi tick** (01 §5.6, D2), và mỗi tick tốn `31+N` câu SQL.

```
node_runs   (run_id, node_id) — PK; status, attempt_count, ready_at,
                                 started_at, finished_at, output_ref, error
attempts    (node_run_id, seq) — PK; status, job_id, provider_state,
                                 started_at, finished_at, cost_credit
```

**Nghiệm thu (số, không phải cảm nhận):**
`SQL cho một lượt tiến của run` phải là **O(số node vừa đổi trạng thái)**, không
phải `O(tổng số node)`. Đường cơ sở phải phá: 100 node → 131 câu/tick.

### WF-302 · Bảo đảm phải được **viết ra**, không được ngầm hiểu — `MUST`

| Đối tượng | Bảo đảm | Cơ chế |
|---|---|---|
| Lập lịch một node | **at-least-once** | tick idempotent + `dedupe_key` |
| Side effect ngoài (provider) | **at-most-once khi kết quả không xác định** | `provider_state=dispatched` → `ABANDONED` |
| Bút toán credit | **exactly-once theo run** | idempotent theo id (đã có) |
| Ghi Artifact | **idempotent theo (attempt_id, port)** | khoá tất định |
| Webhook ra ngoài | **at-least-once, có chữ ký, có khử trùng phía khách** | đã có |

**Không hứa exactly-once cho lời gọi provider. Không thể hứa.** Viết ra để lần
sau không ai vô tình hứa.

### WF-303 · Khôi phục là RECONCILE, không phải REPLAY — `MUST`

Chọn dứt khoát giữa hai họ:
- **Replay/event-sourcing** (Temporal): tái tạo trạng thái bằng cách chạy lại
  lịch sử. Đòi hàm workflow tất định.
- **Reconcile/state-machine**: đọc trạng thái bền hiện tại, tính bước kế tiếp.

**LTT chọn reconcile.** *Vì sao:* nguồn chân lý đã là CSDL; các bước là **job
bên ngoài** với side effect thật; và không có mã người dùng để yêu cầu tất
định. Ép replay lên mô hình này là gánh một ràng buộc không mua được gì.
*(Đây là một quyết định, không phải một kết luận đo được. Phải kiểm chứng lại ở
`16_DURABILITY_COMPARISON.md` — nếu bằng chứng nói ngược, sửa mục này.)*

### WF-304 · Không phần nào của mạch tiến được giữ chỉ trong RAM — `MUST`

Bao gồm: kết quả biểu thức điều kiện, tiến độ ForEach, thời điểm hết hạn
waitpoint, và **quyết định "node này đã bị bỏ qua"**.
**Nghiệm thu:** giết tiến trình ở 10 điểm khác nhau trong một run 10 node → cả
10 lần khôi phục ra cùng một kết quả cuối. *(Đây là bộ chaos test bắt buộc, sẽ
mô tả ở `23_TEST_STRATEGY`.)*

### WF-305 · Không gọi mạng bên trong transaction đang giữ khoá — `MUST`

Hôm nay `verifier.verify()` (có thể gọi model qua mạng) chạy **trong**
transaction giữ `FOR UPDATE` trên `agent_runs` (01 §5.10, D4). Chính
`job_runner` đã cấm điều này cho handler và ghi lý do trong docstring; tầng
Agent lại tái phạm.
**Nghiệm thu:** một phép kiểm tĩnh (như `tools/lint_app_contract.py`) chặn mọi
lời gọi I/O ngoài trong thân hàm scheduler.

---

## 6. WF-4xx — WAITPOINT, TÀI NGUYÊN, GPU

### WF-401 · Waitpoint là nguyên hàm bậc một — `MUST` 🔴

```
Waitpoint {
  id, run_id, node_run_id,
  kind: DELAY | EXTERNAL_JOB | WEBHOOK | HUMAN | CHILD_RUN | EVENT | SCHEDULE
  token           (bí mật, dùng để đánh thức từ ngoài)
  expires_at, timeout_action, payload_ref
}
```

Bất biến: **một run ở `WAITING` không chiếm worker, không chiếm GPU, không
chiếm suất admission, và không quay vòng hỏi lại.**

**Trạng thái hôm nay và vì sao chưa đủ.** LTT *đã* đạt được nửa quan trọng:
executor không ngồi chờ trong RAM — job GPU 20 phút chạy ở worker của nó, còn
executor chỉ hỏi lại (01 §8.4). Nhưng nửa còn lại thiếu: nó **hỏi lại mỗi 2
giây, mãi mãi**, và mỗi lần hỏi tốn `31+N` câu SQL. Với 100 run đồng thời đó là
tải nền không đổi cho một hệ thống **không có việc gì để làm**.
**Nghiệm thu:** một run có 1 node chờ 60 phút phải phát sinh **O(1)** câu SQL
trong 60 phút đó, không phải O(1.800 tick).

### WF-402 · Job hoàn tất phải ĐÁNH THỨC run, không để run đi hỏi — `MUST`

Chuyển từ *pull mỗi 2 giây* sang *push khi có chuyện xảy ra*. Nguồn đánh thức:
job terminal, waitpoint hết hạn, người duyệt bấm nút, webhook vào, child run
xong.

**Ràng buộc thực tế (F3):** đánh thức **không được** là cơ chế duy nhất — worker
restart 13,6 lần/ngày. Phải có **một vòng đối soát thưa** (ví dụ 60 s) làm lưới
an toàn cho tín hiệu bị mất. *Đây là "polling như dự phòng", không phải "polling
như cơ chế chính".*

### WF-403 · Node khai nhu cầu tài nguyên; nền tảng cấp phát — `MUST`

Kế thừa nguyên vẹn nguyên tắc đã đúng: **app khai, nền tảng quyết** (01 §8.2).
Node khai `resource_class`, `vram_min_mb`, `admission_resource`, `slots`,
`estimated_duration_s`. Nền tảng chọn card, giành lease, ghim
`CUDA_VISIBLE_DEVICES`.
**Cấm:** node **không được** chọn GPU, không được biết host, không được biết
provider nào đang phục vụ.

### WF-404 · Thời lượng ước tính là ĐẦU VÀO của lập lịch — `SHOULD`

`estimated_duration_s` để scheduler không xếp một việc 20 phút vào chỗ vừa nhả
ra bởi một việc 5 giây (mô hình đã được ghi trong `AppManifest.cho_tai_nguyen_s`
với số đo thật). Nay chỉ dùng cho giãn cách thử lại; V2 dùng cho xếp chỗ.

### WF-405 · Nhà cung cấp GPU ngoài không được cấm về kiến trúc — `MAY`

Hôm nay chỉ có card cục bộ + "máy B" (01 §8.4). Chưa cần Runpod/Vast. Nhưng
`resource_class` phải là **chuỗi do app khai**, không phải enum của nền tảng —
để thêm một lớp máy sau này là thêm dữ liệu, không phải sửa lõi.

---

## 7. WF-5xx — TIỀN

### WF-501 · Trần chi phí tất định, tính trước — `MUST` (giữ nguyên, mở rộng)

Công thức hiện tại (01 §4.3) đúng nhưng chỉ phủ đồ thị tĩnh:

```
max(step) = (giá + giá_verifier) × fanout × (1 + max_retry)
```

Phải mở rộng để phủ các nguyên hàm mới, **và vẫn hữu hạn**:

| Nguyên hàm | Trần |
|---|---|
| ForEach | `max_items × max(thân)` — `max_items` **bắt buộc hữu hạn** |
| Rẽ nhánh | **tổng của MỌI nhánh có thể chạy**, không phải nhánh đắt nhất |
| `ANY` join | tổng mọi nhánh (nhánh thua vẫn tiêu tiền) |
| Subworkflow | trần của version con, ghim theo version |
| Retry | `× (1 + max_retry)` như cũ |

⚠️ **Bẫy đã biết:** nếu trần trở nên quá bi quan, người dùng sẽ thấy báo giá
lớn hơn nhiều lần chi phí thật và không bấm duyệt. Đây đúng là *"phanh đặt dưới
nhu cầu bình thường biến thất bại thành mặc định"*. Nên **bắt buộc** hiển thị
**hai** con số: `chi phí kỳ vọng` và `trần tối đa`; và giữ chỗ theo **trần**.

### WF-502 · Chỗ giữ tiền: ở RUN, không ở node — `MUST` (giữ nguyên)

Một hold cho cả run lúc duyệt; `ensure_can_spend` trước mỗi lời gọi provider;
settle một lần lúc kết thúc; node con **không** tự giữ chỗ. Đây là ranh giới đã
trả giá (*"giá ở tầng job khi runtime đã thu là thu HAI LẦN"*). Không được đổi.

### WF-503 · Chi phí thật gắn với ATTEMPT, không tính lại từ tham số — `MUST`

Hôm nay `actual_cost()` **tính lại** `credit_for(job_type, params)` cho mọi job
con, mọi lần được gọi, mọi tick (01 §7.2, D7). Sai lệch xảy ra nếu bảng giá đổi
giữa chừng — và nó lãng phí CPU trong đường nóng.
**Yêu cầu:** ghi `cost_credit` vào hàng `attempts` **lúc attempt kết thúc**;
`actual = SUM(attempts.cost_credit)`. Một phép cộng, không phải một phép tính lại.

### WF-504 · Hold treo phải có đường đóng ở luồng chính — `SHOULD`

145 lần báo `GIU CHO TREO` trong 28 ngày (01 §A.5). Bộ dọn đang chạy đúng, nhưng
nó là *bộ dọn*. V2 phải có ràng buộc: **mọi run terminal đều settle trong cùng
transaction chuyển trạng thái**, để bộ dọn trở thành lưới an toàn chứ không phải
đường chính.

---

## 8. WF-6xx — ARTIFACT

### WF-601 · Artifact là thực thể có danh tính bền — `MUST` 🔴

Hôm nay không có bảng; danh tính được **suy ra** bằng hai cách khác nhau ở hai
nơi (`artifact_id(job_id, field, index)` vs quét tên khoá `_key`/`_keys`) —
01 §11.1, C2.

```
Artifact {
  id, owner_id, created_by_attempt_id,
  kind: image|video|audio|text|json|file,
  mime, size_bytes, checksum_sha256,
  storage_backend, storage_key,
  ttl_class: EPHEMERAL | RUN | PROJECT | PERMANENT,
  expires_at, metadata
}
```

**Nghiệm thu:** không còn đường mã nào suy ra artifact bằng quy ước đặt tên.

### WF-602 · State mang THAM CHIẾU, không mang bytes — `MUST` (giữ nguyên)

Đã đúng hôm nay và phải giữ. Bổ sung: một tham chiếu artifact phải **kiểm được
quyền** ở tầng artifact, chứ không chỉ dựa vào `owner_id` tiêm vào params.

### WF-603 · Lineage và TTL — `SHOULD`

`artifact → attempt → node_run → run → workflow_version`. Cho phép trả lời
*"tấm ảnh này ra đời từ đâu, bằng prompt nào, tốn bao nhiêu"* mà không phải đọc
log. TTL theo `ttl_class`, không theo `Job.content_expired_at` của job cha.

### WF-604 · Khử trùng nội dung (dedupe theo checksum) — `MAY`

Chỉ khi đo được là đáng. Ghi ở đây để lược đồ có sẵn `checksum_sha256`.

---

## 9. WF-7xx — HỆ KIỂU VÀ SDK NODE

### WF-701 · Hệ kiểu cổng không được làm mất thông tin — `MUST`

Hôm nay 13 kiểu tham số bị gộp còn 9 kiểu cổng; `int`, `number`, `bool`, `dict`
**đều thành `json`** (01 §2.3). Nghĩa là validator không phân biệt được một cổng
số với một cổng object.

```
Nguyên thuỷ : text · number · integer · boolean · json · file
Media       : image · video · audio · document
Tham chiếu  : model_ref · connection_ref · artifact_ref · workflow_ref · secret_ref
Tập hợp     : T[]  (mọi T ở trên)
Tương lai   : mask · latent · embedding · timeline · subtitle · frame_sequence
              — KHÔNG hiện thực bây giờ; hệ kiểu phải MỞ RỘNG ĐƯỢC bằng dữ liệu
```

**Quy tắc ép kiểu — chỉ một, và phải tường minh:** `T → T[]` (bọc). Mọi ép kiểu
khác bị **từ chối**. *Vì sao:* ép kiểu ngầm là chỗ lỗi trốn. Muốn `number → text`
thì đặt một node chuyển đổi — nó hiện trên đồ thị, người ta thấy được.

### WF-702 · Cardinality cổng — `MUST`

Mỗi cổng khai: `required?`, `multiple?` (nhận nhiều cạnh), `variadic?` (số cổng
sinh theo cấu hình). Hôm nay chỉ suy được qua kiểu `[]` — không phân biệt được
*"một cổng nhận một mảng"* với *"một cổng nhận nhiều cạnh"*.

### WF-703 · MỘT nguồn chân lý cho luật nối dây — `MUST` 🔴

Hôm nay luật kiểu viết tay ở **hai** nơi, **hai** ngôn ngữ:
`editorState.connectionAllowed()` (TS) và `validator` (Python) — 01 §10.3, D9.
Chúng gần giống nhau nhưng không bằng nhau. Đây đúng là cơ chế bảng-chép-tay đã
hỏng năm lần ở dự án này.

**Yêu cầu:** luật kiểu định nghĩa **một lần**, phát sinh ra cho client (hoặc
client hỏi server). Frontend vẫn được có **thêm** luật UX, nhưng không được có
bản sao của luật đúng-sai.
**Nghiệm thu:** một test đối chiếu: với mọi cặp (cổng ra, cổng vào) trong
palette, quyết định của client và của server **trùng khớp**.

### WF-704 · Frontend không được biết tên tool cụ thể — `MUST`

`presentationAdapter.ts` đang liệt kê `image.generate`, `video.generate`,
`asset.*`… (01 §C1). Backend cấm điều này và có test cưỡng chế; frontend không
có bánh cóc tương đương.
**Yêu cầu:** modality/nhãn/tier do app **khai** trong NodeType; frontend đọc dữ
liệu. **Nghiệm thu:** một test chặn mọi chuỗi khớp `^[a-z_]+\.[a-z_]+$` được
hardcode trong mã frontend.

### WF-705 · SDK node là phần MỞ RỘNG của `AppManifest`, không phải thứ song song — `MUST`

Thêm một node = thêm/mở rộng `ToolSpec` trong `apps/<slug>/manifest.py`.
**Không** sinh ra một registry thứ hai. *Vì sao:* hai registry là hai nguồn
chân lý; dự án này đã trả giá cho mô hình đó nhiều lần.

### WF-706 · Node phải khai được: đầu ra, chính sách lỗi, tài nguyên, giá, xác minh — `MUST`

```
NodeType {
  … (từ ToolSpec)
  ports_in[], ports_out[]        (cardinality, mặc định, UI hint)
  retry_policy                    (mặc định của type; instance ghi đè được)
  timeout_s
  resource { class, vram_min_mb, admission_resource, slots, est_duration_s }
  pricing   (hàm — giữ nguyên mô hình `credit_cost(params)`)
  verifiable[]
  idempotency  { key_fields[] }   ← MỚI: node tự khai cái gì làm nên danh tính
  side_effect  { none | external | irreversible }  ← MỚI
}
```

`side_effect` là trường quyết định hành vi khôi phục: `none` được chạy lại tự
do; `irreversible` **không bao giờ** được tự động thử lại sau `ABANDONED`.

---

## 10. WF-8xx — TRIGGER, API, AGENT, CON NGƯỜI

### WF-801 · Trigger là thực thể, tối thiểu bốn loại — `MUST`

Hôm nay chỉ manual + hẹn giờ một lần (01 §11).

| Loại | Ưu tiên |
|---|---|
| Manual (người bấm) | `MUST` (đã có) |
| API (`POST /api/v1/workflows/{id}/runs`) | `MUST` |
| Schedule / cron (lặp lại) | `MUST` |
| Webhook vào (có ký, có chống phát lại) | `SHOULD` |
| Sự kiện nội bộ (job xong, artifact mới) | `MAY` |

Mỗi trigger phải có: chủ sở hữu, khoá idempotency, trần tần suất, và **ghim
version** (chạy bản đã publish, không chạy bản nháp).

### WF-802 · Public API chạy được workflow — `MUST`

Hôm nay `/api/v1` chỉ có job, không có workflow (01 §3.24). Cần:
`POST /workflows/{id}/runs` · `GET /runs/{id}` · `POST /runs/{id}/cancel` ·
`GET /runs/{id}/artifacts` · webhook `run.succeeded` / `run.failed` /
`run.waiting`.

Đi qua **đúng** hạ tầng đã có: `inventory.py`, scope, idempotency, rate limit,
`SYNC`/`ASYNC_JOB`, webhook HMAC. **Không dựng bộ máy API thứ hai.**

### WF-803 · Human-in-the-loop nhiều hơn một điểm — `SHOULD`

Hôm nay duy nhất một điểm: duyệt báo giá (01 §3.17). Cần `Approval` như một
NodeType (WF-206) đứng trên `Waitpoint(kind=HUMAN)`: duyệt / từ chối / sửa tham
số rồi tiếp / hết hạn thì làm gì.

### WF-804 · Agent tạo và sửa workflow; Agent KHÔNG chạy workflow — `MUST` (giữ nguyên)

Đã đúng (01 §9.2) và là một trong những thứ hiếm cần *giữ nguyên không bàn*.
V2 mở rộng theo hướng: Agent tạo **bản nháp** → validator tất định → báo giá →
người duyệt → publish thành `WorkflowVersion` → runtime chạy. Agent được đọc
kết quả và đề xuất **version kế tiếp**; nó **không** được sửa một version đang
chạy.

### WF-805 · Quan sát được ở tầng workflow, không chỉ tầng job — `MUST`

`JobEvent` mạnh ở tầng job; tầng workflow chỉ có `decision_log` JSON (01 §3.21).
Cần: dòng thời gian theo `run → node_run → attempt → job`, có input ref, output
ref, thời lượng, provider, GPU, credit, lý do lỗi, lý do bỏ qua — và Canvas
hiển thị đúng trạng thái đó.

**Bắt buộc trả lời được:** *"vì sao node này bị bỏ qua?"* và *"tiền đi đâu?"*
— hai câu mà `decision_log` hiện tại chỉ trả lời được một nửa.

---

## 11. WF-9xx — BẢO MẬT, ĐA TENANT, VẬN HÀNH

### WF-901 · Cách ly theo tenant ở mọi thực thể mới — `MUST`
Mọi bảng mới mang `owner_id`; mọi truy vấn lọc theo nó; không có đường đọc chéo.
Kế thừa `_CLIENT_FORBIDDEN` + tiêm `owner_id` phía server.

### WF-902 · Connection tách khỏi node config — `MUST`
Node tham chiếu `connection_ref`, không nhúng khoá. Giá trị thật chỉ được tiêm ở
worker, không bao giờ vào Canvas, không bao giờ vào `WorkflowVersion` (thứ có
hash và chia sẻ được).

### WF-903 · Quyền theo tool được cưỡng chế lúc THI HÀNH, không chỉ lúc validate — `MUST`
Hôm nay `validate_plan` lọc theo `app_access` (tốt), nhưng một version đã publish
có thể chạy sau khi quyền bị thu hồi. Phải kiểm lại tại thời điểm chạy.

### WF-904 · Chia sẻ workflow không được rò bí mật — `MUST`
Chia sẻ hôm nay lưu SHA-256 của token và có hạn (tốt, 01 §15). V2 phải bảo đảm
`WorkflowVersion` **không chứa** connection value, artifact key của người khác,
hay `owner_id`.

### WF-905 · Ngân sách vận hành cho chính scheduler — `SHOULD`
Từ F2/F3: phải đo và giới hạn được *scheduler tự tiêu bao nhiêu* (câu SQL/giây,
lượt claim/job xong). Đường cơ sở phải phá: **13,7 lượt nhặt cho mỗi job xong**
và **131 câu SQL/tick ở 100 node**.

---

## 12. BẢNG ĐỐI CHIẾU YÊU CẦU ↔ HIỆN TRẠNG (rút gọn; bản đầy đủ ở tài liệu 21)

| ID | Yêu cầu | Hôm nay | Ưu tiên |
|---|---|---|---|
| WF-101 | DAG, nhiều cha/con | ✅ có | MUST |
| WF-102 | Edge là thực thể | ❌ dẫn xuất, handle bị vứt | MUST |
| WF-103 | Data/Control edge tường minh | ⚠️ có do tai nạn | MUST |
| WF-104 | NodeType ≠ NodeInstance | ⚠️ ngầm | MUST |
| WF-105 | Version bất biến + hash | ⚠️ chỉ đóng băng `AgentRun.plan` | MUST |
| WF-106 | Subworkflow | ❌ | SHOULD |
| WF-107 | Page ≠ phạm vi chạy | ❌ **im lặng bỏ node** | MUST |
| WF-201 | Song song khai được | ❌ hằng số 4 | MUST |
| WF-202 | Lập lịch biết tài nguyên | ❌ **92 % lượt nhặt bị nhả** | MUST |
| WF-203 | JOIN đa ngữ nghĩa | ❌ chỉ ALL | MUST |
| WF-204 | ForEach + concurrency | ❌ | MUST |
| WF-205 | Rẽ nhánh theo dữ liệu | ❌ chỉ success/error | MUST |
| WF-206 | Node không sinh Job | ❌ | MUST |
| WF-207 | Máy trạng thái tường minh | ⚠️ một phần | MUST |
| WF-208 | Huỷ/timeout lan truyền | ⚠️ một phần | MUST |
| WF-301 | Trạng thái là hàng CSDL | ❌ **JSON ghi lại toàn bộ** | MUST |
| WF-302 | Bảo đảm được viết ra | ⚠️ có trong mã, không có tài liệu | MUST |
| WF-303 | Reconcile (không replay) | ✅ đã theo hướng này | MUST |
| WF-304 | Không state chỉ trong RAM | ✅ phần lớn | MUST |
| WF-305 | Không I/O trong khoá | ❌ **verifier gọi mạng trong tx** | MUST |
| WF-401 | Waitpoint | ❌ **thay bằng polling 2 s** | MUST |
| WF-402 | Đánh thức bằng sự kiện | ❌ | MUST |
| WF-403 | Nền tảng cấp GPU | ✅ **mạnh** | MUST |
| WF-404 | Dùng thời lượng ước tính | ⚠️ chỉ cho retry delay | SHOULD |
| WF-501 | Trần chi phí tất định | ✅ **mạnh**, cần mở rộng | MUST |
| WF-502 | Hold ở run | ✅ | MUST |
| WF-503 | Chi phí theo attempt | ❌ tính lại mỗi tick | MUST |
| WF-504 | Đóng hold ở luồng chính | ⚠️ 145 lần treo/28 ngày | SHOULD |
| WF-601 | Artifact có danh tính | ❌ **suy ra bằng tên khoá** | MUST |
| WF-602 | State mang tham chiếu | ✅ | MUST |
| WF-701 | Hệ kiểu không mất thông tin | ⚠️ 13 → 9, gộp mất | MUST |
| WF-702 | Cardinality cổng | ❌ | MUST |
| WF-703 | Một nguồn luật nối dây | ❌ **hai bản, hai ngôn ngữ** | MUST |
| WF-704 | Frontend không biết tên tool | ❌ **đang vi phạm** | MUST |
| WF-705 | SDK = mở rộng manifest | ✅ nền tảng đã đúng | MUST |
| WF-706 | Node khai side_effect/idempotency | ❌ | MUST |
| WF-801 | Trigger đa dạng | ⚠️ 2/5 | MUST |
| WF-802 | API chạy workflow | ❌ | MUST |
| WF-804 | Agent ≠ engine | ✅ **đã đúng** | MUST |
| WF-805 | Quan sát tầng workflow | ⚠️ chỉ `decision_log` | MUST |
| WF-901..905 | Bảo mật/đa tenant | ✅ mạnh, trừ 903 | MUST |

**Đếm:** 41 yêu cầu chốt · **`MUST` = 33** · `SHOULD` = 6 · `MAY` = 2.
Trong 33 `MUST`: **7 đã đạt** · 9 đạt một phần · **17 chưa có**.

---

## 13. NGƯỠNG NGHIỆM THU BẰNG SỐ (đường cơ sở để chấm mọi phương án)

Mọi phương án ở tài liệu 30 phải nói rõ nó đạt hay không đạt từng dòng.

| # | Phép đo | Đường cơ sở hôm nay | Ngưỡng V2 |
|---|---|---|---|
| M1 | SQL cho một lượt tiến, run 100 node | **131 / tick** | `O(số node đổi trạng thái)` |
| M2 | SQL trong 60 phút của một run đang CHỜ | ~1.800 tick × 131 | **O(1)** |
| M3 | Lượt claim / job hoàn tất | **13,7** | **≤ 2,0** |
| M4 | Nhánh song song tối đa mỗi run | **4** (cứng) | khai được, mặc định 8 |
| M5 | Node tối đa / version | 100 | 500, validate < 300 ms |
| M6 | Khôi phục sau crash | resume mức step | **10/10 điểm giết → cùng kết quả** |
| M7 | ForEach 100 phần tử, crash giữa chừng | không hỗ trợ | 100 kết quả, 0 lượt lặp |
| M8 | Chênh giữa báo giá tối đa và chi phí thật | chưa đo | báo giá phải kèm **hai** số |
| M9 | Luật nối dây client vs server | **lệch, không đo** | **trùng khớp 100 %** |
| M10 | Hold treo / 28 ngày | **145 lần** | 0 ở luồng chính |

---

## 14. NHỮNG QUYẾT ĐỊNH CÒN MỞ (không được lặng lẽ chốt ở bước sau)

| # | Câu hỏi | Vì sao chưa chốt được | Chốt ở đâu |
|---|---|---|---|
| Q1 | Điều kiện rẽ nhánh: trên **cạnh** hay node **Router**? | cần xem cách OSS trả giá | tài liệu 13 |
| Q2 | Lưu định nghĩa: JSONB bất biến, bảng chuẩn hoá, hay lai? | phụ thuộc M1/M5 | tài liệu 24 |
| Q3 | Trạng thái thi hành: bảng `node_runs` hay event log? | WF-303 đã nghiêng, cần kiểm | tài liệu 16 |
| Q4 | Đánh thức: LISTEN/NOTIFY, bảng đánh thức, hay hàng đợi riêng? | đo trên Postgres thật | tài liệu 23 |
| Q5 | Ngôn ngữ biểu thức: JSON-logic, CEL, hay tập cố định? | đánh đổi biểu đạt/bảo mật | tài liệu 25 |
| Q6 | Có giữ Plan v1 làm lớp tương thích không? | **F1 nói có thể bỏ** — nhưng còn bản nháp đã lưu | tài liệu 27 |
| Q7 | Canvas: giữ React Flow hay đổi? | không đổi vì lý do thời trang | tài liệu 14 |

⚠️ **Q6 phụ thuộc một số chưa đo được:** số `AgentWorkflow` bản nháp trong CSDL
production. Không đọc được vì `secrets/` bị ACL chặn (đúng ý muốn). **Cần người
dùng quyết** có nâng quyền để đếm hay không. Nếu số đó là 0 thì Plan v1 có thể
bỏ hoàn toàn.

---

## 15. ĐIỀU NÀY *KHÔNG* NÓI

Tài liệu này **không** nói LTT nên tự viết engine, cũng **không** nói nên lấy
một engine có sẵn. Nó chỉ nói **thước đo**. Có thể sau khi đọc mã Temporal /
Kestra / Windmill / Activepieces / n8n / Node-RED / Trigger.dev, kết luận đúng
là *"lấy X, bọc lại"* — và điều đó vẫn hợp lệ, miễn X đạt bảng §12 và §13.

Ba tính chất mà **kinh nghiệm cho thấy sẽ khó tìm thấy đủ trong một hệ có sẵn**,
nên đây là chỗ cần soi kỹ nhất khi đọc mã người khác:

1. **Trần chi phí tất định tính trước** (WF-501) — hầu như không hệ automation
   nào cần tính chất này, vì bước của họ gần như miễn phí.
2. **Lập lịch nhận biết tài nguyên khan hiếm** (WF-202) — F2 là đặc thù của một
   nền tảng có **một** suất GPU dùng chung, không phải của một hệ chạy trên cloud
   co giãn.
3. **`ABANDONED` / at-most-once cho side effect ngoài** (WF-302) — nhiều hệ chọn
   at-least-once và đẩy việc khử trùng cho người viết node.

---

## 16. BƯỚC KẾ TIẾP

`03_REPOSITORY_MANIFEST.md` — dựng `../LTT_ARCHITECTURE_LAB/` **ngoài** ranh
giới kho sản phẩm, clone theo tag ổn định, ghi lại URL / license / tag / commit
SHA / ngày, rồi mới đọc mã.

Phân loại trước khi so sánh (đề bài §4): *visual automation* · *durable
execution* · *orchestration* · *data pipeline* · *AI graph* · *media node graph*.
Không chấm chung một bảng những thứ giải bài toán khác nhau.

---

*Không sửa mã sản phẩm. Chưa clone kho ngoài nào. Mọi con số trong tài liệu này
truy về `01_CURRENT_LTT_ARCHITECTURE.md` hoặc phụ lục đo của nó.*
