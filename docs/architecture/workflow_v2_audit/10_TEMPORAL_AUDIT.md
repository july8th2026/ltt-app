# 10 — KHẢO SÁT MÃ NGUỒN: TEMPORAL

> **Kho:** `temporalio/temporal` · **tag** `v1.31.2` ·
> **commit** `19a774302c613da9adc4436ab14278ccdca8e0a5` · 2026-07-07
> **Giấy phép:** ✅ **MIT** — dễ chịu nhất trong 7 kho.
> **Phân loại:** *Durable Execution*. Đây là **máy chủ**; SDK ở kho riêng, **chưa clone**.
>
> Quy mô: **872.231 dòng Go**. Tài liệu kiến trúc: `docs/architecture/` (3.062 dòng, 12 tệp).

---

## 0. KẾT LUẬN NGẮN

Temporal trả lời **ba câu hỏi hẹp** tôi mang sang, và câu quan trọng nhất được
trả lời bằng **một dòng trong tài liệu của chính họ** — dòng thẳng thắn nhất mà
tôi gặp trong cả cuộc khảo sát:

> *"Workflow code must be deterministic and have no side effects (with specific
> exceptions), and activity code must either be idempotent or non-retryable
> (i.e. **at least once or at most once**)."*
> — `docs/architecture/README.md:35`

⭐ **Temporal không hứa exactly-once. Nó nói thẳng: bạn chỉ có at-least-once
hoặc at-most-once, và việc chọn cái nào là NGHĨA VỤ CỦA MÃ BẠN VIẾT.**

Đó chính là hình dạng mà `WF-302` của LTT đòi hỏi — và nó xác nhận rằng yêu cầu
*"bảo đảm phải được viết ra, không được ngầm hiểu"* không phải là đòi hỏi quá
đáng: hệ thống nghiêm túc nhất trong lĩnh vực này **đặt nó ở dòng đầu tài liệu
kiến trúc.**

| Câu hỏi mang sang | Trả lời |
|---|---|
| `WF-302` bảng bảo đảm ở đâu, cưỡng chế bằng gì? | ⭐ **Ở tài liệu, dưới dạng HỢP ĐỒNG VỚI MÃ NGƯỜI DÙNG.** Máy chủ **không** cưỡng chế được |
| `WF-303` giá của replay là gì? | 🔴 **Đòi mã người dùng TẤT ĐỊNH** — và máy chủ chỉ **đếm** vi phạm, không chặn được |
| `WF-202` matching so với Trigger.dev? | 🟡 **Xếp hàng công bằng có TRỌNG SỐ** `<pass, id>`; tinh vi hơn, nhưng **không lọc theo sức chứa** |

---

## 1. ⭐ `WF-302` — BẢO ĐẢM LÀ MỘT HỢP ĐỒNG, KHÔNG PHẢI MỘT TÍNH NĂNG

### 1.1 Bằng chứng

```
kho : temporal @ 19a77430
tệp : docs/architecture/README.md:20-36
```

```
**Requirements**
- Durable execution of workflows must be guaranteed: workflows must still execute
  correctly in the face of transient failures in server processes and user-hosted processes.
- User code is executed in environments owned by the user.

**Design decisions**
- The system functions via event sourcing: an append-only history of events is stored for
  each workflow execution, and all required workflow state can be recreated at any time by
  replaying this history.
- Workflow code must be deterministic and have no side effects (with specific exceptions),
  and activity code must either be idempotent or non-retryable
  (i.e. at least once or at most once).
```

`CONFIRMED`

### 1.2 Ba điều đọc ra, cả ba đều đổi cách viết `WF-302`

**① Bảo đảm được nêu như một RÀNG BUỘC ĐẶT LÊN NGƯỜI DÙNG, không phải một lời
hứa của hệ thống.** Câu *"activity code must either be idempotent or
non-retryable"* là một **nghĩa vụ**, không phải một tính năng.

⇒ `WF-302` bản nháp của tôi liệt kê bảo đảm theo *"đối tượng → bảo đảm → cơ
chế"*. Thiếu một cột: **ai phải làm gì để bảo đảm đó đúng.** Với LTT, cột đó
thuộc về **app** — và nó phải nằm trong `AppManifest`/`ToolSpec`, đúng khuôn
*"app khai, nền tảng đọc"*.
**→ đây chính là trường `side_effect: none | external | irreversible` mà
`WF-706` đã đề xuất.** Temporal xác nhận nó là trường bắt buộc, không phải tuỳ chọn.

**② "at least once **or** at most once" — không có lựa chọn thứ ba.** Không hệ
nào cho exactly-once với side effect ngoài. LTT đã viết đúng điều này ở
`WF-302` (*"Không hứa exactly-once cho lời gọi provider. Không thể hứa."*), và
giờ nó có một trích dẫn để đứng sau.

**③ "User code is executed in environments owned by the user."** Đây là tiền đề
làm cho toàn bộ phần còn lại của Temporal trở nên **hợp lý với họ và không hợp
lý với LTT** — xem §2.3.

---

## 2. 🔴 `WF-303` — GIÁ CỦA REPLAY, VÀ VÌ SAO LTT KHÔNG NÊN TRẢ

Ở tài liệu 02 tôi viết: *"LTT chọn reconcile. (Đây là một quyết định, không phải
một kết luận đo được. Phải kiểm chứng lại ở tài liệu 16 — nếu bằng chứng nói
ngược, sửa mục này.)"*

**Bằng chứng không nói ngược. Nó củng cố.**

### 2.1 Giá thứ nhất: mã workflow phải TẤT ĐỊNH

`docs/architecture/README.md:33-35`: toàn bộ trạng thái được **tái tạo bằng cách
chạy lại lịch sử sự kiện**. Muốn thế thì cùng một lịch sử phải cho cùng một
chuỗi lệnh ⇒ **không `now()`, không `random()`, không đọc biến ngoài, không lặp
trên map không thứ tự**.

### 2.2 🔴 Giá thứ hai — và đây là điều tôi không lường: MÁY CHỦ KHÔNG CƯỠNG CHẾ ĐƯỢC

```
grep -rn "NonDeterministicError|nondeterministic|NonDeterminism" --include=*.go service/ common/
→ common/metrics/metric_defs.go:665:
    ServiceErrNonDeterministicCounter = NewCounterDef("service_errors_nondeterministic")
```

**Một kết quả duy nhất trong 872.231 dòng, và nó là một BỘ ĐẾM.** `CONFIRMED`

Máy chủ **đếm** vi phạm tất định; nó không **phát hiện** và không **ngăn**.
Việc phát hiện nằm ở SDK, chạy trong tiến trình của người dùng — tức ngoài tầm
kiểm soát của hệ thống.

⭐ **Đây là lập luận mạnh nhất cho quyết định của LTT.** Một bảo đảm mà **hệ
thống không cưỡng chế được** thì nó là một **quy ước**, và quy ước sẽ bị vi
phạm. Temporal chấp nhận đánh đổi đó vì họ **phải** — người dùng viết mã và
chạy mã trên máy của người dùng (§1.2 ③).

**LTT ở vị trí ngược lại:**

| | Temporal | LTT |
|---|---|---|
| Ai viết bước? | người dùng | **app trong kho của ta** |
| Bước chạy ở đâu? | máy của người dùng | **worker của ta** |
| Bước là gì? | mã tuỳ ý | **một `Job` gọi provider** |
| Có tất định được không? | phải yêu cầu | **không thể** — provider ngoài, GPU, LLM |

⇒ Ép replay lên mô hình của LTT là **mua một ràng buộc không thể thoả mãn**
(lời gọi provider vốn không tất định) để đổi lấy một lợi ích LTT không cần
(tái tạo trạng thái — LTT đã có nó trong CSDL).

⭐ **Kết luận `WF-303`: LTT chọn RECONCILE. Nâng từ *quyết định* lên
`HIGH CONFIDENCE`, có bằng chứng.** Và mô hình **C** của Trigger.dev (chuỗi ảnh
chụp bất biến, `09 §1`) cho LTT **lịch sử đầy đủ mà không phải trả giá tất
định** — đó là điểm ngọt.

### 2.3 Một hệ quả kiến trúc: `service/history` là gì

52 tệp `.go` ở `service/history/`, gồm `history_engine.go`, `chasm_engine.go`,
`handler.go`, `archival_queue_task_executor.go`, `deletemanager/`, `events/`,
`circuitbreakerpool/`. Toàn bộ tồn tại để **lưu, phân đoạn, nén, lưu trữ và
phát lại lịch sử sự kiện**.

⇒ Đó là chi phí kỹ thuật thường trực của lựa chọn event-sourcing-có-replay.
LTT **không cần** trả chi phí đó.

---

## 3. 🟡 `WF-202` — XẾP HÀNG CÔNG BẰNG CÓ TRỌNG SỐ, NHƯNG KHÔNG LỌC SỨC CHỨA

### 3.1 Cơ chế: "fair level" `<pass, id>`

```
tệp: service/matching/fairness.md
```

```
Task ID   : sequential int64 assigned to tasks. Two tasks never have the same id.
Pass      : int64 used to "spread out" tasks.
Fair level: tuple of <pass, id>. Fair levels are ordered lexicographically and
            ordered that way by persistence.

Tasks are _written_ out of order and we rely on persistence to order them by level
(most importantly by pass).
```

```
tệp: service/matching/fairness_util.go:10-29
minWeight = 0.001
func getEffectiveWeight(overrides fairnessWeightOverrides, pri *commonpb.Priority) float32 {
    weight, ok := overrides[key]
    if !ok { weight = pri.GetFairnessWeight() }
    if weight <= 0.0 { weight = 1.0 } else { weight = max(weight, minWeight) }
    return weight
}
```

**Đọc ra:** mỗi task có một **khoá công bằng** và một **trọng số**; trọng số
quyết định `pass`; **tầng lưu trữ sắp xếp theo `(pass, id)`**. Tức xếp hàng công
bằng có trọng số **được thực hiện bằng THỨ TỰ SẮP XẾP trong CSDL**, không phải
bằng một bộ lập lịch trong bộ nhớ. `CONFIRMED`

⭐ Ý tưởng đẹp và LTT **đã dùng một phiên bản của nó**: `jobs.claim()` xếp theo
`aged_first → never_served_first → last_claimed_at → created_at → id`
(`01 §6.2`) — cũng là công bằng thực hiện bằng `ORDER BY`, cũng có index chuyên
dụng (`ix_jobs_fairness`).

**Khác biệt:** Temporal có **trọng số khai được theo khoá**; LTT thì công bằng
**đều nhau**. Với ít tenant thì đều nhau là đủ và **giải thích được** — giữ nguyên.

### 3.2 🔴 Nhưng Temporal KHÔNG lọc theo sức chứa

Không tìm thấy trong `service/matching` cơ chế tương đương
`envsAtFullConcurrency` của Trigger.dev (`09 §2.1`). Matching **phân phát** task
cho worker đang hỏi (long-poll); nếu không có worker, task nằm trong backlog.

⇒ Mô hình của họ là **worker kéo**, nên "sức chứa" tự nhiên bằng số worker đang
hỏi — không cần lọc. LTT thì **có tài nguyên bị chiếm bởi thứ ngoài đội worker**
(máy B một suất, GPU dùng chung với tiến trình ngoài — `01 §8.1`), nên số worker
**không** đại diện cho sức chứa.

⭐ **Xác nhận: bản lọc-sức-chứa của Trigger.dev vẫn là lời giải đúng cho `F2`,
không phải bản của Temporal.**

### 3.3 ⭐ `fairness.md` — bài học về VĂN HOÁ TÀI LIỆU

Tài liệu này liệt kê thẳng những gì **chưa giải xong**:

```
TODO: Is that enough to prevent all problems in the fairness schema? It seems like yes.
## Counting — How are pass numbers assigned?  TODO
### Ack level movement while a write is in flight
    ... at this point we need to set the ack level backwards?!?
    ... How to fix it?
### TTLs on tasks — We can't use TTLs on tasks so disable that for now.
```

Và một kịch bản mất task được kể **từng bước**, kết thúc bằng
*"The task is now effectively lost"*, rồi mới tới cách vá (LWT có điều kiện trên
range id).

⭐ Đây đúng tinh thần đã có trong `CLAUDE.md` và trong chú thích mã của LTT:
**ghi lại vì sao, kể cả khi câu trả lời là "chưa biết".** Một hệ thống hạ tầng
hàng đầu công khai `TODO` trong tài liệu thiết kế của mình — đó là sự cho phép
để LTT làm điều tương tự ở `23_TARGET_ARCHITECTURE.md` thay vì giả vờ mọi thứ đã
được giải.

---

## 4. HỘI TỤ THỨ TƯ: PHÂN LOẠI LỖI THEO KIỂU, "BẬN" LÀ MỘT LOẠI RIÊNG

```
tệp: docs/architecture/retry.md:1-12
- `backoff.IsRetryable` which decides whether to retry based on the error type
- `backoff.RetryPolicy` which decides how long to backoff first - or not retry at all

It's important to note that a special retry policy is used for `ResourceExhausted` service errors.
```

Đối chiếu với LTT (`01 §6.2`, `platform_core/jobs.py`):

| | Temporal | LTT |
|---|---|---|
| Không thử lại | `IsRetryable` trả false | **`LoiNguoiGoi`** |
| Bận — thử lại, chính sách RIÊNG | `ResourceExhausted` + policy riêng | **`DangBan`** (thử lại, **không tiêu lượt**) |
| Lỗi thoáng qua | backoff thường | `fail(retry=True)` backoff `10·2^n` |

⭐ **Hội tụ độc lập lần thứ tư trong cuộc khảo sát này** (sau: index đánh thức ·
UNIQUE khử trùng · ghim version bằng bản sao). Và LTT **đi xa hơn một bước**:
`DangBan` **không tiêu lượt thử**, còn Temporal chỉ đổi chính sách backoff.

⇒ Ghi vào tài liệu 22 (`KEEP`): phân loại lỗi ba nhánh của LTT **không phải nợ
kỹ thuật, mà là một tài sản** — hai hệ hàng đầu độc lập cùng đi tới đó.

---

## 5. BẢNG CHẤM THEO YÊU CẦU CỦA LTT

⚠️ **Đọc bảng này cẩn thận.** Temporal giải một bài toán **khác**: chạy mã tuỳ
ý của người dùng, trên máy người dùng, bền vững ở quy mô rất lớn. Nhiều ô `❌`
dưới đây không phải khuyết điểm của Temporal — chúng là **dấu hiệu không cùng
bài toán**.

| ID | Yêu cầu LTT | TP | Ghi chú |
|---|---|:--:|---|
| WF-101/102 | DAG · Edge thực thể | ❌ | **không có đồ thị** — workflow là mã |
| WF-104 | NodeType ≠ NodeInstance | — | không áp dụng |
| WF-105 | Version bất biến | ⭐ | `worker-versioning.md` 332 dòng — mô hình version sâu nhất đã thấy |
| WF-106 | Subworkflow | ⭐ | child workflow là nguyên hàm bậc một |
| WF-201 | Song song khai được | ⭐ | song song thật, nhiều tiến trình |
| WF-202 | Lập lịch biết tài nguyên | 🟡 | công bằng **có trọng số**; **không lọc sức chứa** |
| WF-203 | JOIN đa ngữ nghĩa | ✅ | selector/future ở SDK |
| WF-204 | ForEach + concurrency | ✅ | ở SDK |
| WF-207 | Máy trạng thái tường minh | ⭐ | `workflow-lifecycle.md` 571 dòng |
| WF-208 | Huỷ/timeout lan truyền | ⭐ | huỷ hợp tác, nhiều tầng timeout |
| WF-301 | Trạng thái là hàng CSDL | ⭐ | event history chỉ-thêm (nhưng kèm giá replay) |
| WF-302 | **Bảo đảm được viết ra** | ⭐⭐ | **dòng hay nhất trong cả cuộc khảo sát** |
| WF-303 | Reconcile | ❌ | họ chọn **replay** — và đó là lý do LTT **không** theo |
| WF-304 | Không state chỉ trong RAM | ⭐ | toàn bộ là history |
| WF-401 | Waitpoint | ✅ | timer/signal; nhưng gắn với mô hình mã |
| WF-403 | Nền tảng cấp GPU | ❌ | không có |
| WF-501 | Trần chi phí tất định | ❌ | không có |
| WF-601 | Artifact có danh tính | ❌ | payload trong history, có trần kích thước |
| WF-701 | Hệ kiểu cổng | ❌ | không có cổng |
| WF-801 | Trigger đa dạng | ⭐ | `schedules.md` 393 dòng |
| WF-805 | Quan sát tầng workflow | ⭐ | history **là** dòng thời gian |
| WF-901 | Đa tenant | ⭐ | namespace là nguyên hàm bậc một |

**Tổng:** ⭐ **11** · ✅ **3** · 🟡 **1** · ❌ **6** · — **1**.

---

## 6. RÚT RA CHO LTT

### 🟢 LẤY

1. **⭐⭐ Cách VIẾT bảo đảm.** Không phải *"hệ thống bảo đảm X"* mà
   *"để có X, mã của bạn phải làm Y"*. Thêm cột **"ai phải làm gì"** vào
   `WF-302`, và neo nó vào `ToolSpec.side_effect` (`WF-706`) — app khai, nền
   tảng đọc.
2. **Nói thẳng "at-least-once hoặc at-most-once, không có lựa chọn thứ ba"** ở
   ngay đầu tài liệu kiến trúc, không giấu trong phần phụ lục.
3. **Văn hoá `TODO` trong tài liệu thiết kế** (`fairness.md`). Ghi cả cái chưa
   giải, kèm kịch bản hỏng cụ thể.
4. **Xác nhận phân loại lỗi ba nhánh của LTT là đúng** — và LTT đi xa hơn
   Temporal ở chỗ `DangBan` không tiêu lượt thử.
5. `worker-versioning.md` (332 dòng) — đọc lại khi làm `WF-105`/`27_MIGRATION`.

### 🔴 KHÔNG LẤY

1. **Replay / event sourcing đòi tất định.** Ba lý do, mỗi lý do đủ một mình:
   bước của LTT là lời gọi provider **không thể tất định**; LTT **không cần**
   tái tạo trạng thái (đã có trong CSDL); và máy chủ **không cưỡng chế được**
   ràng buộc đó (§2.2).
2. **Toàn bộ hạ tầng `service/history`.** 52 tệp để lưu/nén/lưu-trữ/phát-lại
   lịch sử — chi phí của một lựa chọn LTT không chọn.
3. **Trọng số công bằng theo khoá.** LTT ít tenant; công bằng đều nhau vừa đủ
   vừa **giải thích được cho khách**.
4. **Adopt Temporal làm lõi V2 (phương án D của đề bài §14).** Bằng chứng ở
   §2.2 làm phương án này **yếu đi rõ rệt** — nó buộc LTT nhận một ràng buộc
   (tất định) mà chính bản chất công việc của LTT vi phạm. *(Chốt ở tài liệu 30.)*

### 📌 Sửa vào tài liệu 02

| Yêu cầu | Sửa gì |
|---|---|
| `WF-302` | Thêm cột **"nghĩa vụ thuộc về ai"**; neo vào `ToolSpec.side_effect` |
| `WF-303` | Nâng *"LTT chọn reconcile"* từ **quyết định** lên **`HIGH`, có bằng chứng** |
| `WF-706` | `side_effect` từ *"nên có"* thành **bắt buộc** — nó là chỗ neo của `WF-302` |

---

## 7. MỨC TIN CẬY

| Kết luận | Nhãn |
|---|---|
| Bảo đảm nêu là hợp đồng với mã người dùng, at-least-once **hoặc** at-most-once | `CONFIRMED` — trích nguyên văn |
| Máy chủ chỉ **đếm** vi phạm tất định, không phát hiện | `CONFIRMED` — 1 kết quả grep trong 872 K dòng |
| Xếp hàng công bằng bằng `<pass, id>` sắp xếp ở tầng lưu trữ | `CONFIRMED` |
| Trọng số công bằng khai được theo khoá, `minWeight = 0.001` | `CONFIRMED` |
| `ResourceExhausted` có chính sách thử lại riêng | `CONFIRMED` |
| Matching **không** lọc theo sức chứa | `HIGH` — không tìm thấy; không chứng minh được phủ định tuyệt đối |
| Chi phí thật của ràng buộc tất định trong thực tế | `UNKNOWN` — nằm ở **SDK**, kho riêng, **chưa clone** |
| Hành vi replay khi mã workflow đổi | `UNKNOWN` — cần SDK + chạy thật |

---

## 8. NHÓM *DURABLE EXECUTION* — TỔNG KẾT

Hai kho, hai lời giải khác nhau cho cùng bài toán:

| | Trigger.dev | Temporal |
|---|---|---|
| Mô hình bền | **chuỗi ảnh chụp bất biến** | **event sourcing + replay** |
| Đòi tất định? | **không** | **có** |
| Trạng thái tái tạo bằng | đọc hàng mới nhất | **chạy lại lịch sử** |
| Bước là gì | task đã đăng ký | mã tuỳ ý của người dùng |
| Chạy ở đâu | hạ tầng của họ | **máy của người dùng** |
| Lọc sức chứa trước khi lấy việc | ⭐ **có** | không |
| Phù hợp LTT | ⭐⭐ **cao** | thấp — sai tiền đề |

⭐ **Kết luận nhóm:** LTT nên **ADAPT mô hình của Trigger.dev**, và **lấy cách
diễn đạt bảo đảm của Temporal**. Không adopt cái nào toàn bộ — cả hai đều
**không có mô hình đồ thị**, thứ mà LTT đã có và Canvas đang phụ thuộc vào.

---

## 9. BƯỚC KẾ TIẾP

Ba nhóm đã xong: *visual automation* (04, 05, 06) và *durable execution*
(09, 10). Còn **nhóm orchestration**: `07_KESTRA` và `08_WINDMILL`.

Câu hỏi mang sang **hẹp lại còn ba** — mọi câu khác đã có lời giải:

1. `WF-801` — **Windmill có 14 gói `windmill-trigger-*`** (http, kafka, mqtt,
   nats, postgres, sqs, websocket, email, azure, gcp, amqp…). Đây là bộ sưu tập
   trigger đầy đủ nhất; LTT cần 4 loại (`WF-801`) và nên xem cách họ **tách
   trigger thành gói** thay vì nhồi vào lõi.
2. `WF-105` — **Kestra** khai workflow bằng **YAML có lược đồ**, nên mô hình
   version/di trú của họ khác hẳn hai nhóm trên.
3. `Q7` — **canvas Svelte của Windmill**: đối chứng cuối cùng cho quyết định
   giữ React Flow (hiện đang `HIGH` sau số đo 5× của Node-RED, `06 §6`).

---

*Không sửa mã sản phẩm LTT. Không có mã Temporal nào được chép vào
`D:\LTTSTUDIOSAPP`.*
