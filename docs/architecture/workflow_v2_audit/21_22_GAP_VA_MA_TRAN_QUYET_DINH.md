# 21+22 — KHOẢNG TRỐNG CỦA LTT & MA TRẬN KEEP / ADOPT / ADAPT / REWRITE

> Gộp `21_LTT_GAP_ANALYSIS` và `22_KEEP_ADOPT_ADAPT_REWRITE`: cái thứ hai là
> **câu trả lời** cho cái thứ nhất, tách ra chỉ bắt người đọc lật qua lại.
>
> **Nguồn:** `01` (đo LTT) · `02` (41 yêu cầu) · `04–10` (bảy kho) · `12–19` (tổng hợp).
> **Quy tắc:** mỗi khoảng trống phải **trỏ đúng tệp và dòng** trong LTT. Không
> đoán.

---

## PHẦN 21 — KHOẢNG TRỐNG

### 21.0 Bảng phân loại

| Nhãn | Nghĩa |
|---|---|
| `EXISTS` | có, và đúng |
| `PARTIAL` | có, nhưng thiếu một vế |
| `MISSING` | không có |
| `WRONG_ABSTRACTION` | **có, nhưng đặt sai chỗ / sai hình dạng** — nguy hiểm nhất, vì nó *trông như* đã xong |
| `DEBT` | nợ kỹ thuật đã đo được |

---

### 21.1 Mô hình đồ thị

| # | Yêu cầu | Nhãn | Nguồn trong LTT | Ghi chú |
|---|---|---|---|---|
| G01 | DAG nhiều cha/con | `EXISTS` | `agent/validator.py:_has_cycle` · `workflows.py:canvas_to_plan` | **mạnh hơn 4/7 kho** |
| G02 | Edge là thực thể | `WRONG_ABSTRACTION` | `workflows.py:130-170` | **handle bị VỨT**; dữ liệu đi bằng chuỗi `"$n.port"` trong `params` ⇒ **hai biểu diễn song song do client đồng bộ tay** |
| G03 | Data vs Control edge | `WRONG_ABSTRACTION` | `workflows.py` `condition ∈ {success,error}` | control edge **tồn tại do tai nạn**, không khai được, không vẽ được |
| G04 | Cạnh `RESOURCE` (model/connection) | `MISSING` | — | n8n có 12 loại; LTT dùng tham số `model_ref` |
| G05 | NodeType ≠ NodeInstance | `PARTIAL` | `registry.ToolSpec` | **không ghim `type_version`** ⇒ đổi schema tool làm gãy workflow cũ **âm thầm** |
| G06 | Page ≠ phạm vi chạy | `WRONG_ABSTRACTION` 🔴 | `workflows.py:_page_graph:60-99` | **chỉ page đang mở được chạy**; node ở 19 page kia không bao giờ chạy, **không báo lỗi** |
| G07 | Version bất biến + hash | `PARTIAL` | `models.AgentWorkflow.revision` · `AgentRun.plan` | `plan` **có** đóng băng (tốt); `revision` chỉ là bộ đếm, **không có hash**, không có "bản publish" |
| G08 | Subworkflow | `MISSING` | — | |

### 21.2 Thi hành

| # | Yêu cầu | Nhãn | Nguồn | Ghi chú |
|---|---|---|---|---|
| G09 | Song song khai được | `WRONG_ABSTRACTION` 🔴 | `agent/executor.py:238` `max_parallel=4` | hằng số trong mã; `apps/agent/jobs.py:16` **không truyền tham số** ⇒ production luôn 4. Đếm **step**, không đếm job |
| G10 | Hành vi khi chạm trần | `MISSING` | — | mặc định `QUEUE` khắp nơi, **chưa từng khai**. Kestra bắt buộc khai |
| G11 | Lập lịch biết tài nguyên | `WRONG_ABSTRACTION` 🔴🔴 | `jobs.py:claim` + `job_runner.py:194-250` | **nhặt trước, hỏi sau** ⇒ đo được **92,2 %** lượt nhặt bị nhả, **13,7 lượt nhặt / 1 job xong** |
| G12 | JOIN đa ngữ nghĩa | `MISSING` | `executor.py:280` `after ⊆ done` | **chỉ ALL** |
| G13 | ForEach + concurrency | `MISSING` 🔴 | `executor.py:308` `for index in range(fanout)` | `fanout ≤ 4` là **N bản sao CÙNG params**, không phải map |
| G14 | Rẽ nhánh theo dữ liệu | `MISSING` | — | chỉ `success`/`error` |
| G15 | Node không sinh Job | `MISSING` | `ToolSpec.job_type` bắt buộc | mọi nguyên hàm điều khiển phải giả trang thành job |
| G16 | `finally` cấp workflow | `MISSING` | — | ⇒ **145 lần hold treo / 28 ngày** (`01 §A.5`) |
| G17 | Huỷ/timeout lan truyền | `PARTIAL` | `jobs.cancel` · `_het_gio` | có ở tầng job; **không** ở tầng workflow |

### 21.3 Bền vững

| # | Yêu cầu | Nhãn | Nguồn | Ghi chú |
|---|---|---|---|---|
| G18 | Trạng thái là hàng | `WRONG_ABSTRACTION` 🔴🔴 | `models.AgentRun.checkpoint` (JSON) · `executor.py:330` | đọc–sửa–ghi **toàn bộ mỗi tick**; đo được **`31+N` câu SQL/tick**, tick mỗi **2 giây** |
| G19 | Lưu chuyển trạng thái thất bại | `MISSING` | `agent/runs.py:transition` | ném `AgentRunError`, **không để lại dấu vết** |
| G20 | `RUNNING` ⇄ `WAITING` đồng thời | `MISSING` | `models.AGENT_*` | không biểu đạt được "một số node xong, một số đang chờ" |
| G21 | Tách lỗi hệ thống / nghiệp vụ | `MISSING` | `AGENT_ERROR` | gộp hết ⇒ không phân biệt được **hoàn tiền** với **cảnh báo vận hành** |
| G22 | Bảo đảm được viết ra | `MISSING` | — | có **trong mã** (`LoiNguoiGoi`/`DangBan`/`ambiguous`), **không có tài liệu** |
| G23 | Không I/O trong khoá | `DEBT` 🔴 | `executor.py:89-97` | `verifier.verify()` (gọi mạng) chạy **trong** transaction giữ `FOR UPDATE` |
| G24 | Khử trùng bằng ràng buộc CSDL | `DEBT` | `jobs.py:submit` | `dedupe_key` kiểm bằng `SELECT` rồi `INSERT` ⇒ **cửa sổ tranh chấp thật**. Ba kho dùng UNIQUE bộ phận |

### 21.4 Tài nguyên & waitpoint

| # | Yêu cầu | Nhãn | Nguồn | Ghi chú |
|---|---|---|---|---|
| G25 | Waitpoint | `MISSING` 🔴 | `apps/agent/jobs.py:38` | thay bằng **polling 2 giây**, mỗi lượt `31+N` câu SQL |
| G26 | Đánh thức bằng sự kiện | `MISSING` | — | không có; Activepieces + n8n **hội tụ** ở index trên mốc thời gian |
| G27 | Nền tảng cấp GPU | `EXISTS` ⭐ | `gpu_lease.py` · `leases.py` · `gpu_claims.py` · `job_runner._giu_gpu` | **3 tầng lease, mạnh hơn mọi kho đã đọc** |
| G28 | Thời lượng ước tính là đầu vào lập lịch | `PARTIAL` | `AppManifest.cho_tai_nguyen_s` | chỉ dùng cho **giãn cách thử lại**, không dùng để **xếp chỗ** |

### 21.5 Tiền

| # | Yêu cầu | Nhãn | Nguồn | Ghi chú |
|---|---|---|---|---|
| G29 | Trần chi phí tất định | `EXISTS` ⭐⭐ | `validator.py` + `budget.quote` | **không kho nào trong 7 có.** Tài sản lớn nhất |
| G30 | Hold ở run, không ở node | `EXISTS` ⭐ | `budget.approve` · `runs.submit_child` | |
| G31 | Chi phí theo attempt | `DEBT` | `executor.py:118 actual_cost` | **tính lại** `credit_for()` cho mọi job con, **mọi tick** |
| G32 | Đóng hold ở luồng chính | `PARTIAL` | `credit.giu_cho_treo` | bộ dọn chạy đúng, nhưng **145 lần/28 ngày** ⇒ luồng chính để lọt |

### 21.6 Artifact

| # | Yêu cầu | Nhãn | Nguồn | Ghi chú |
|---|---|---|---|---|
| G33 | Artifact có danh tính | `MISSING` 🔴 | `public_api/media.py:artifact_id` vs `routes/_shared.py:_artifact_key` | **hai cách suy khác nhau ở hai nơi**; một cách quét tên khoá `_key`/`_keys` |
| G34 | State mang tham chiếu | `EXISTS` ⭐ | `Job.result` chứa khoá lưu trữ | **đúng, và hiếm** — 3/7 kho mang giá trị |
| G35 | Id tự mô tả backend | `MISSING` | `storage.get_storage()` singleton | bật R2 song song Local ⇒ **mọi khoá cũ thành mơ hồ** |
| G36 | Lineage · TTL riêng · checksum | `MISSING` | — | TTL bám `Job.content_expired_at` |

### 21.7 Hệ kiểu & SDK

| # | Yêu cầu | Nhãn | Nguồn | Ghi chú |
|---|---|---|---|---|
| G37 | Hệ kiểu không mất thông tin | `PARTIAL` | `validator._port_for_param:38-45` | 13 kiểu → 9 cổng; `int`·`number`·`bool`·`dict` **đều thành `json`** |
| G38 | Cardinality cổng | `MISSING` | — | không phân biệt *"cổng nhận mảng"* với *"cổng nhận nhiều cạnh"* |
| G39 | Một nguồn luật nối dây | `DEBT` 🔴 | `editorState.connectionAllowed` (TS) vs `validator` (Py) | **hai bản, hai ngôn ngữ, đã lệch** |
| G40 | Frontend không biết tên tool | `DEBT` 🔴 | `presentationAdapter.ts` | liệt kê `image.generate`, `video.generate`, `asset.*`… — backend **cấm** điều này và có test; frontend **không có bánh cóc** |
| G41 | `side_effect` · `idempotency` · `mock` | `MISSING` | `ToolSpec` | |

### 21.8 Trigger · API · quan sát · bảo mật

| # | Yêu cầu | Nhãn | Nguồn | Ghi chú |
|---|---|---|---|---|
| G42 | Trigger đa dạng | `PARTIAL` | manual + `scheduled_at` ≤30 ngày | thiếu cron lặp, webhook vào, sự kiện |
| G43 | API chạy workflow | `MISSING` | `server/api/inventory.py` | `/api/v1` **chỉ có job** |
| G44 | Quan sát tầng workflow | `PARTIAL` | `JobEvent` mạnh · `decision_log` JSON yếu | không trả lời được *"vì sao node này bị bỏ qua"* |
| G45 | Quyền tool lúc **thi hành** | `MISSING` 🔴 | `validator.validate_plan` | kiểm lúc validate; **version đã publish vẫn chạy sau khi quyền bị thu hồi** |
| G46 | Đa tenant · bí mật | `EXISTS` ⭐ | `app_access` · `_CLIENT_FORBIDDEN` · `owner_id` server-side | |
| G47 | Không cần sandbox | `EXISTS` ⭐ | không chạy mã người dùng | **tài sản**, không phải thiếu sót |

**Đếm:** `EXISTS` **9** · `PARTIAL` **8** · `MISSING` **22** · `WRONG_ABSTRACTION` **6** · `DEBT` **6**

🔴 **Sáu mục `WRONG_ABSTRACTION` là nguy hiểm nhất** (G02, G03, G06, G09, G11,
G18) — chúng *trông như đã có*. Ví dụ rõ nhất: G06 — Canvas **có** nhiều page,
nên ai cũng tưởng có subworkflow; thực tế 19/20 page **không bao giờ chạy** và
không có lỗi nào báo.

---

## PHẦN 22 — MA TRẬN QUYẾT ĐỊNH

### 22.0 Định nghĩa

| | |
|---|---|
| **KEEP** | LTT đang đúng về chiến lược. Không đụng. |
| **ADOPT** | Dùng lại một thành phần OSS gần như nguyên trạng. |
| **ADAPT** | Mượn **kiến trúc**, tự viết trong LTT. |
| **REWRITE** | Thay bản LTT hiện có. |
| **IGNORE** | Không liên quan / sai bài toán. |

### 22.1 Ma trận

| # | Hệ con | LTT hôm nay | Nguồn tốt nhất | **Quyết định** | Vì sao |
|---|---|---|---|---|---|
| 1 | **Hợp đồng app (`registry.py`)** | ⭐ xuất sắc | — | **KEEP** | Đã bị ép mở rộng bởi sự cố thật 8+ lần, mỗi lần ghi lý do. Không kho nào có tương đương |
| 2 | **Hàng đợi job (`jobs.py`)** | ⭐ mạnh | — | **KEEP** + vá G11/G24 | `SKIP LOCKED` · dedupe · orphan · công bằng có aging · `ambiguous` |
| 3 | **Sổ credit** | ⭐ mạnh | — | **KEEP** | append-only · SUM · idempotent · advisory lock |
| 4 | **Trần chi phí tất định** | ⭐⭐ | **không ai có** | **KEEP** + mở rộng | Tài sản lớn nhất. Mở rộng cho ForEach/nhánh/subflow |
| 5 | **Lease GPU 3 tầng** | ⭐⭐ | không ai có | **KEEP** | Mạnh hơn mọi kho |
| 6 | **Tách LLM khỏi đường thi hành** | ⭐ | Temporal xác nhận | **KEEP** | |
| 7 | **Phân loại lỗi 3 nhánh** | ⭐ | Temporal hội tụ | **KEEP** | LTT **đi xa hơn**: `DangBan` không tiêu lượt thử |
| 8 | **State mang tham chiếu** | ⭐ | n8n hội tụ | **KEEP** | 3/7 kho mang giá trị và đã đụng trần |
| 9 | **Không sandbox** | ⭐ | — | **KEEP** | Hệ quả của "không chạy mã người dùng" |
| 10 | **Public API kernel** | ⭐ 24 route đóng băng | — | **KEEP** + mở rộng | Waitpoint của V2 cắm vào đây |
| 11 | **Canvas React Flow** | ⭐ 2.061 dòng | Node-RED 10.203 (đối chứng) | **KEEP** + bổ sung | `Q7` `CONFIRMED` |
| 12 | **Máy trạng thái job** | ✅ | — | **KEEP** | |
| 13 | **`JobEvent`** | ✅ | — | **KEEP** | |
| — | | | | | |
| 14 | **Trạng thái thi hành workflow** | 🔴 `checkpoint` JSON | **Trigger.dev** `ExecutionSnapshot` | **REWRITE → ADAPT** | Mô hình C: chuỗi ảnh chụp bất biến. Giải G18·G19·G20·G21·G44 + `M1` |
| 15 | **Executor / scheduler** | 🔴 `tick()` một hàm | Trigger.dev *systems* | **REWRITE** | 12 hệ thống con thay một `tick()` |
| 16 | **Song song** | 🔴 hằng số 4 | **Windmill** + Kestra | **ADAPT** | `parallel` theo node · `parallelism` biểu thức · `behavior` tràn |
| 17 | **Lấy việc theo tài nguyên** | 🔴 nhặt-trước-hỏi-sau | **Trigger.dev** | **ADAPT** | Lọc hàng đợi hết chỗ **trước** khi chọn. Giải G11 (92 %) |
| 18 | **Waitpoint** | 🔴 không có | **Activepieces** + **Trigger.dev** | **ADAPT** | Thực thể độc lập + bảng nối nhiều-nhiều + `sealed` + `NOT_DISPATCHED` + index bộ phận |
| 19 | **Join** | 🔴 chỉ ALL | **Activepieces** `BarrierPolicy` | **ADAPT** | `requiredSuccesses` · `releaseOnFirstFailure` · `sealed` |
| 20 | **ForEach** | 🔴 không có | **Windmill** | **ADAPT** | + `max_items` **bắt buộc** (Windmill không có, `WF-501` cần) |
| 21 | **Edge** | 🔴 dẫn xuất | n8n (có cạnh) + n8n (có kiểu) | **REWRITE** | Thực thể bậc một, khoá bằng **id** (không phải tên như n8n), 3 `kind` |
| 22 | **Artifact** | 🔴 suy từ tên khoá | **n8n `binary-data`** | **ADAPT** | Id `<backend>:<key>` · stream · `copy` · `delete` tuỳ chọn |
| 23 | **Versioning workflow** | 🟡 bộ đếm | Kestra + Activepieces | **ADAPT** | hash + **khai trường loại trừ** + di trú **lười, sao lưu trước, hỏng thì gọi người** |
| 24 | **Hệ kiểu cổng** | 🟡 13→9 mất thông tin | n8n + Node-RED | **REWRITE** | + cardinality; **một** nguồn luật (giải G39) |
| 25 | **`ToolSpec`** | ✅ nền tốt | Activepieces `pieceVersion` | **ADAPT** *(mở rộng, không thay)* | + `type_version` · `side_effect` · `idempotency` · `mock` · `timeout` biểu thức |
| 26 | **Trigger** | 🟡 2/5 loại | **Windmill** 11 gói | **ADAPT** | một gói mỗi loại — cùng khuôn hợp đồng app |
| 27 | **Middleware trên cạnh** | 🔴 không có | **Node-RED** 6 hook | **ADAPT** | Chỗ cắm cho G11·G44·G45 mà không phình scheduler |
| 28 | **`finally` cấp workflow** | 🔴 không có | **Kestra** | **ADAPT** | Giải G16 → G32 (145 hold treo) |
| 29 | **Cách viết bảo đảm** | 🔴 chỉ trong mã | **Temporal** | **ADAPT** | Bảng + cột **"nghĩa vụ thuộc ai"**, neo vào `ToolSpec.side_effect` |
| 30 | **`mock`** | 🔴 không có | **Windmill** | **ADAPT** | Điều kiện để test workflow có bước 20 phút GPU |
| — | | | | | |
| 31 | Replay / event sourcing | — | Temporal | **IGNORE** | Đòi tất định — bước LTT là lời gọi provider |
| 32 | Container checkpoint | — | Trigger.dev | **IGNORE** | LTT không có tiến trình người dùng cần đông lạnh |
| 33 | Redis / Redlock | — | Trigger.dev | **IGNORE** | LTT có advisory lock + `FOR UPDATE` + UNIQUE |
| 34 | Chọn hàng đợi ngẫu nhiên có trọng số | — | Trigger.dev · Temporal | **IGNORE** | Ít tenant; LTT cần **giải thích được** thứ tự |
| 35 | Custom code node / sandbox | — | Activepieces · Windmill | **IGNORE** | `02 §1.2` cấm |
| 36 | Cây thay đồ thị | — | Activepieces · Windmill | **IGNORE** | LTT đã có DAG — đi lùi |
| 37 | `AiTransform` nguyên bản | — | Windmill | **IGNORE** *(tạm)* | Phá `WF-501`. Xem `Q8` |
| 38 | Enum loại cạnh nở theo năng lực | — | n8n (12 loại AI) | **IGNORE** | Sửa lõi mỗi lần thêm năng lực |

### 22.2 Đếm

```
KEEP    13   ← nhiều nhất, và đó là kết luận quan trọng nhất
ADAPT   14
REWRITE  4   ← trạng thái thi hành · executor · edge · hệ kiểu cổng
IGNORE   8
ADOPT    0   ← KHÔNG kho nào đủ gần để lấy nguyên
```

### 22.3 🔴 Ba kết luận đọc ra từ bảng đếm

**① `ADOPT = 0`.** Không kho nào trong bảy kho là thứ LTT có thể lấy nguyên,
và lý do đo được: **ba kho mạnh nhất về runtime (Trigger.dev, Temporal,
Windmill) đều không có mô hình đồ thị node+cạnh** mà Canvas của LTT đang đứng
lên trên. Còn ba kho có canvas (Activepieces, n8n, Node-RED) thì **đều thất bại
ở `WF-301`**.

⇒ Bằng chứng loại bỏ **phương án A** (adopt một hệ) và làm yếu **phương án B**
(fork). Chốt chính thức ở tài liệu 30.

**② `KEEP` (13) nhiều hơn `REWRITE` (4).** Phần LTT làm đúng lớn hơn phần làm
sai — và bốn mục `REWRITE` **nằm gọn trong một lớp**: `platform_core/agent/`
(1.843 dòng) cộng mô hình edge trên Canvas. **Không mục `REWRITE` nào chạm vào
tầng đang phục vụ khách thật.**

**③ Bốn mục `REWRITE` là mã CHƯA TỪNG CHẠY PRODUCTION.** `01 §A.1`: **0 job
`agent.advance` trong 28 ngày**. Nghĩa là *"viết lại"* ở đây **không có rủi ro
di trú khách hàng** — nó là viết lại một prototype, dưới sự bảo vệ của 103 test
Python + 52 test Canvas đang xanh.

---

## 22.4 THỨ TỰ THI HÀNH — suy ra từ ma trận, không từ sở thích

Xếp theo **giá trị đo được / rủi ro**, không theo thứ tự logic.

| Đợt | Việc | Giải | Ngưỡng phá được |
|---|---|---|---|
| **1** | Lấy việc theo tài nguyên (#17) | G11 | `M3`: **13,7 → ≤2,0** lượt nhặt/job |
| **1** | Ràng buộc UNIQUE cho `dedupe_key` (#2) | G24 | đóng cửa sổ tranh chấp |
| **2** | Trạng thái = chuỗi ảnh chụp (#14) | G18·G19·G20·G21·G44 | `M1`: **131 → O(node đổi)** |
| **2** | Waitpoint + đánh thức (#18) | G25·G26 | `M2`: **1.800 tick → O(1)** |
| **3** | Executor thành hệ thống con (#15) | G09·G12·G23 | mở đường cho #16·#19·#20 |
| **3** | Edge là thực thể (#21) | G02·G03·G04 | mở đường cho Canvas V2 |
| **4** | ForEach · join · song song (#16·#19·#20) | G12·G13·G09 | `M4`·`M7` |
| **4** | Artifact (#22) | G33·G35·G36 | |
| **5** | Version · trigger · API (#23·#26) | G07·G42·G43 | |
| **5** | `finally` · `mock` · middleware cạnh (#27·#28·#30) | G16·G32·G45 | `M10`: **145 → 0** hold treo |

⭐ **Đợt 1 đáng chú ý riêng:** nó **không đụng gì** tới `platform_core/agent/`.
Nó sửa `jobs.claim()` — và nó là thứ duy nhất trong toàn bộ kế hoạch **có tác
dụng lên khách hàng đang trả tiền hôm nay** (92 % lượt nhặt bị nhả là tải thật,
mỗi ngày). Mọi thứ còn lại phục vụ một tính năng chưa ai dùng.

---

## 22.5 Điều bảng này KHÔNG nói

- **Không** nói mất bao lâu — ở tài liệu 28.
- **Không** nói `Q2`/`Q4`/`Q6`/`Q8` — ở tài liệu 23/24/25/27.
- **Không** chốt phương án A–E — ở tài liệu 30. Nhưng `ADOPT = 0` đã loại A và
  làm yếu B.
- ⛔ **Không** cho phép bắt đầu viết mã. Điểm dừng ở tài liệu 30 giữ nguyên.

---

*Không sửa mã sản phẩm LTT. Không chép mã bên thứ ba vào kho.*
