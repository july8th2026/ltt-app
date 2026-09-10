# 00 — TÓM TẮT ĐIỀU HÀNH: 20 CÂU TRẢ LỜI

> Đề bài §25. Mỗi câu trả lời gọn, kèm con trỏ tới bằng chứng.
> **Viết cuối cùng**, sau 14 tài liệu · 7 kho OSS đọc mã · 28 ngày log production.

---

## 1. LTT HÔM NAY THẬT SỰ LÀ GÌ

Một **nền tảng job SaaS đa tenant trưởng thành** — hàng đợi tự quản trên
Postgres, sổ credit append-only, lease GPU ba tầng, Public API 24 route đóng
băng — **cộng với** một lớp orchestration MVP **1.843 dòng** gắn lên trên.

Hai lớp có độ chín **hoàn toàn khác nhau**, và đó là phát hiện quan trọng nhất:
tầng nền phục vụ **868 job thật/28 ngày**; tầng orchestration **chưa từng chạy
một lần nào**. `01 §0`, `§A.1`

## 2. CÁI GÌ SAI / BỊ GIỚI HẠN

Bốn nút thắt **đo được**, không phải cảm nhận:

| | |
|---|---|
| **92,2 %** lượt nhặt job kết thúc bằng *nhả ra vì tài nguyên bận*; **13,7** lượt nhặt cho mỗi job xong | `01 §A.3` |
| **`31+N`** câu SQL mỗi tick, lặp mỗi **2 giây**, mãi mãi | `01 §5.6` |
| Song song trần **cứng 4 step**, không khai được, đếm step chứ không đếm job | `01 §5.3` |
| Trạng thái là **một khối JSON** bị đọc–sửa–ghi toàn bộ mỗi tick | `01 §D2` |

Cộng sáu chỗ **`WRONG_ABSTRACTION`** — nguy hiểm hơn vì chúng *trông như đã có*:
Canvas có nhiều page nhưng **chỉ page đang mở được chạy** (19/20 page không bao
giờ chạy, không báo lỗi); **cạnh không mang dữ liệu** (dữ liệu đi bằng chuỗi
`"$n.port"`, hai biểu diễn song song do trình duyệt đồng bộ tay). `21_22 §21`

## 3. CÁI GÌ TUYỆT ĐỐI PHẢI GIỮ

**13 hệ con** (`21_22 §22.1`). Bốn cái quan trọng nhất:

1. **Trần chi phí tất định tính trước** — **không kho nào trong bảy kho có**.
   Tài sản riêng lớn nhất của LTT.
2. **Hợp đồng app (`registry.py`)** — nền tảng không biết tên app nào; đã bị ép
   mở rộng bởi sự cố thật 8+ lần, mỗi lần ghi lý do trong mã.
3. **Hàng đợi job** — `SKIP LOCKED` · dedupe · orphan reclaim · công bằng có
   aging · `provider_state = ambiguous`.
4. **Lease GPU ba tầng** + nguyên tắc *app khai, nền tảng quyết*.

Thêm: sổ credit append-only · tách LLM khỏi đường thi hành · phân loại lỗi ba
nhánh · state mang tham chiếu · Canvas React Flow · không cần sandbox.

## 4. CÁI GÌ NÊN GỠ / THAY

**Bốn hệ con**, tất cả nằm trong `platform_core/agent/` + mô hình edge Canvas:
trạng thái thi hành · scheduler · edge · hệ kiểu cổng.

Gỡ hẳn: **Plan v1** (`canvas_to_plan`/`plan_to_canvas`) · cột
**`AgentRun.checkpoint`** · `executor.tick()`.
Giữ lại trong thư mục đó: `validator.py` (tài sản) và `verifier.py` (đúng, chỉ
phải ra khỏi transaction). `27_29 §27.3`

## 5. BÀI HỌC TỐT NHẤT TỪ MỖI KHO

| Kho | Bài học |
|---|---|
| **Trigger.dev** | **Chuỗi ảnh chụp bất biến** — một hàng mỗi lần chuyển trạng thái, **ghi cả lần bị từ chối**; và **lọc hàng đợi hết sức chứa TRƯỚC khi chọn** |
| **Temporal** | **Cách VIẾT bảo đảm**: *"at least once **or** at most once"* là **hợp đồng đặt lên mã**, không phải tính năng của hệ |
| **Activepieces** | **Waitpoint + `BarrierPolicy`** với `sealed` (*"sẽ không còn tín hiệu nào nữa"*) và `NOT_DISPATCHED` (*"lẽ ra phải gửi mà chưa bao giờ gửi"*) |
| **Windmill** | **`parallel` + `parallelism` khai theo NODE, và `parallelism` là BIỂU THỨC**; **`mock` nằm trong lược đồ flow**, không trong bộ test |
| **n8n** | **Artifact id `<backend>:<key>` — tự mô tả**; cạnh **có kiểu** (13 loại, 12 là *tiêm năng lực*) |
| **Kestra** | **`Concurrency{limit, behavior: QUEUE\|CANCEL\|FAIL}`** — khai *hành vi tràn*; và **`finally`** cấp workflow |
| **Node-RED** | **Sáu hook trên đường định tuyến một cạnh**, hook trả `false` thì chặn |

## 6. ADOPT / FORK / LAI / TỰ XÂY LÕI?

**Giữ lõi của mình, mượn kiến trúc có chọn lọc — phương án C.**

Bằng chứng dứt điểm: **`ADOPT = 0`** trên 38 hệ con, và nó có cấu trúc — ba kho
mạnh nhất về runtime **không kho nào có mô hình đồ thị**; ba kho có canvas
**cả ba thất bại ở `WF-301`**. Không tồn tại kho vừa có đồ thị vừa có runtime
bền. `30 §1`, `21_22 §22.2`

## 7. KIẾN TRÚC WORKFLOW V2

```
Canvas / Agent  →  workflow_draft  ──publish──►  workflow_version (BẤT BIẾN, có hash)
                                                       │
                    VALIDATOR (tất định · không LLM · không mạng · không tiền)
                                                       │
                    QUOTE → APPROVAL → HOLD (một lần cho cả run)
                                                       │
                    SCHEDULER = 8 hệ con
                    enqueue · dequeue · attempt · waitpoint
                    snapshot · foreach · ttl · finally
                                                       │
                    node_run_snapshot (CHỈ THÊM) ◄─ waitpoint ◄─ waitpoint_signal
                                                       │ submit job (qua middleware cạnh)
                    ══════ NỀN TẢNG HIỆN CÓ — KEEP ══════
                    jobs · credit · gpu_lease · registry · storage · public_api
```

Workflow Core **ngồi trên** hàng đợi hiện có và submit job như mọi app khác —
đó là điều kiện để 13 mục `KEEP` giữ được giá trị. `23_24 §1`

## 8. MÔ HÌNH NODE

`ToolSpec` **mở rộng**, không thay. Sáu trường thêm, mỗi trường trỏ về một bằng
chứng: `type_version` · `side_effect` (`none|external|irreversible`) ·
`idempotency.key_fields` · `mock_result` ·
`resource{class, vram_min_mb, slots, est_duration_s}` · `timeout_expr`.

Cộng **8 node điều khiển không sinh Job** (Input · Const · Router · Join ·
Delay · Approval · Subworkflow · Collect) — có `node_run` và snapshot, **không**
tốn credit, **không** qua hàng đợi. `25_26`

## 9. MÔ HÌNH THI HÀNH

**Điều phối job bền** — không phải thông dịch, không phải replay. Tám hệ con
thay một `tick()`. Điều kiện rẽ nhánh **trên cạnh**; biểu thức là **tập toán tử
cố định** (ngoại lệ: `parallelism` được đọc sức chứa lúc chạy).

Song song khai **theo node**, bốn tầng trần (run · **tài nguyên** · tenant ·
node), mỗi tầng kèm `behavior: QUEUE|CANCEL|FAIL`. Tầng **thật sự chặn** là
tầng tài nguyên. `23_24 §6`, `12_19 §13`

## 10. MÔ HÌNH BỀN VỮNG

**Reconcile, không replay.** Trạng thái là **chuỗi ảnh chụp bất biến**:

```sql
node_run_snapshot(previous_snapshot_id, execution_status, run_status,
                  is_valid, error, description, cost_credit, output_ref)
```

Đánh thức: **bảng `wakeup`** là nguồn chân lý (chỉ số bộ phận
`WHERE claimed_at IS NULL`), `LISTEN/NOTIFY` chỉ rút ngắn độ trễ — vì worker
restart **13,6 lần/ngày**, một `NOTIFY` phát lúc restart **biến mất**.

Bảo đảm được **viết ra**: lập lịch node *at-least-once* · side effect ngoài
*at-most-once khi không xác định* (`ABANDONED`) · bút toán credit *exactly-once
theo run*. **Không hứa exactly-once cho lời gọi provider.** `23_24 §3`, `§4.2`

## 11. MÔ HÌNH TÍCH HỢP GPU

**Giữ nguyên ba tầng lease đang có** — `ExecutionLease` (slot từ xa) →
`GpuLease` (card cục bộ theo UUID) → `gpu_claims` (mặt phẳng cấp máy). Nền tảng
chọn card, ghim `CUDA_VISIBLE_DEVICES`; **node không được chọn GPU**.

Thêm: `resource.est_duration_s` thành **đầu vào xếp chỗ** (hôm nay chỉ dùng cho
giãn cách thử lại), và `dequeue` **lọc theo sức chứa vật lý trước khi nhặt**.

⚠️ Phần này mang nhãn **`INFERRED` — không có đối chứng OSS**: không kho nào
trong bảy kho lập lịch quanh **một** thiết bị vật lý dùng chung với tiến trình
ngoài. Hệ quả của sổ nợ `N1`. `23_24 §7`

## 12. MÔ HÌNH CREDIT

**Không đổi nguyên tắc** — đây là thứ LTT làm đúng và không ai khác có:

```
trần tất định tính trước  →  một HOLD cho cả run  →  ensure_can_spend trước
mỗi lời gọi provider  →  settle một lần, hoàn phần dư
```

Ba mở rộng: trần phủ **ForEach** (`max_items` bắt buộc hữu hạn) · **mọi nhánh
có thể chạy** (không phải nhánh đắt nhất) · **subflow** (ghim version).
Chi phí thật ghi vào `snapshot.cost_credit` **lúc attempt kết thúc**, không tính
lại mỗi tick. Thêm hệ con **`finally`** kết sổ trong cùng transaction kết thúc —
đóng lại **145 lần hold treo/28 ngày**.

## 13. MÔ HÌNH AGENT

**Không đổi — LTT đã đúng.** `executor` không import gì thuộc `planner`; LLM
chết thì run vẫn chạy tiếp.

```
ngôn ngữ tự nhiên → Planner → workflow_draft → Validator (tất định)
                  → Quote → người duyệt → publish → Runtime (không cần LLM)
```

Mở rộng duy nhất: **`ai_choice`** — LLM được **chọn trong một tập enum đã khai**,
trần chi phí tính theo **giá trị đắt nhất trong tập**. Từ chối `AiTransform`
dạng Windmill vì nó phá trần tất định. `25_26 §3`

## 14. MÔ HÌNH CANVAS

**Giữ React Flow** — `CONFIRMED` bằng số: Node-RED tự viết **10.203 dòng** cho
lớp view; toàn bộ ứng dụng canvas của LTT là **2.061 dòng**, đã có cổng có kiểu,
chặn chu trình, undo/redo, copy/paste remap `$ref`, chèn node giữa cạnh, đồng
thời lạc quan.

Phải sửa, **không** liên quan thư viện: cạnh có kiểu thật · auto-layout (dagre/
ELK) · chi phí + tài nguyên trên node · **một nguồn luật nối dây** (client hỏi
server, không chép) · **frontend không được biết tên tool cụ thể**. `12_19 §14`

## 15. THAY ĐỔI CSDL

**Thêm 11 bảng**, **gỡ 1 cột**:

```
workflow · workflow_draft · workflow_version
workflow_version_node · workflow_version_edge        (chỉ mục dẫn xuất)
workflow_run · node_run · node_run_snapshot
waitpoint · waitpoint_signal · node_run_waitpoint
wakeup · artifact · workflow_trigger

GỠ: AgentRun.checkpoint
```

Ba ràng buộc thay ba đoạn mã cẩn thận: `UNIQUE(workflow_id, graph_hash)` ·
`UNIQUE(owner_id, idempotency_key)` · chỉ số **bộ phận** trên `due_at`.
Không bảng nào của tầng nền bị đụng. `23_24 §4`

## 16. KẾ HOẠCH DI TRÚ

**Gần như rỗng.** 0 run/28 ngày ⇒ không có trạng thái thi hành để chuyển, không
có khách trên đường cũ, **không cần lớp tương thích**.

Việc thật duy nhất: **một script chạy một lần** chuyển `AgentWorkflow.document`
(Canvas v2) sang `workflow_draft.document` (v3) — và nó **giữ lại** thứ hôm nay
đang bị vứt (`sourceHandle`/`targetHandle`).

⚠️ Chưa đếm được số bản nháp (`secrets/` bị ACL chặn cố ý). Giả định đang chạy:
*có bản nháp, cần script*. Nếu là 0 thì bỏ luôn. **Không chặn gì.** `27_29 §27`

## 17. CÁC PHA TRIỂN KHAI

| Đợt | Nội dung | Ngưỡng | Thời lượng |
|---|---|---|---|
| **1** | `claim()` lọc sức chứa · UNIQUE `dedupe_key` | **`M3`: 13,7 → ≤2,0** | 2–3 ngày |
| **2** | Lược đồ mới (workflow · snapshot · waitpoint · wakeup) | **`M1`** `O(node đổi)` · **`M2`** `O(1)` | 1 tuần |
| **3** | 8 hệ con · `finally` · middleware cạnh · chaos test | **`M10`: 145 → 0** · **`M6`: 10/10** | 1,5–2 tuần |
| **4** | Edge thực thể · hệ kiểu · ForEach · join · trần mở rộng | **`M4` `M7` `M8` `M9`** | 2–3 tuần |
| **5** | Artifact · Canvas v3 · trigger · API · `ToolSpec` | | 2–3 tuần |

⭐ **Đợt 1 không đụng gì tới Workflow V2** — nó sửa `jobs.py`, và là mục **duy
nhất** có tác dụng lên tải **đang chạy thật hôm nay**.

## 18. CÔNG SỨC DỰ KIẾN

**7–10 tuần**, một người làm liên tục. Không gồm: nguyên mẫu chạy thật (`N2`) ·
nhánh node media/GPU (`N1`) · bất kỳ tính năng sản phẩm nào ngoài Workflow V2.

Đợt 1 (2–3 ngày) đóng vai **phép hiệu chuẩn** — đo thật rồi nhân lại phần còn
lại. `27_29 §28.6`

## 19. RỦI RO CHÍNH

| | Rủi ro | Giảm thiểu |
|---|---|---|
| 🔴🔴 | **Đợt 1 làm hỏng đường job đang phục vụ** (868 job/28 ngày) | thay đổi nhỏ từng bước · gate đầy đủ · đo log trước/sau · **cờ + đường lùi chỉ cho mục này** |
| 🔴 | **Ba mục `INFERRED` không có đối chứng ngành** (GPU · xếp chỗ theo thời lượng · trần ForEach) | mỗi mục một thí nghiệm riêng, không gộp vào test chung |
| 🟠 | `node_run_snapshot` phình | TTL · gộp snapshot cũ · chỉ số `(run_id, created_at)` |
| 🟠 | `M1`/`M3` đo trên **SQLite**, Postgres có thể khác | đo lại trên Postgres **trước** đợt 2 |
| 🟠 | Phiên khác sửa cùng cây — **đã xảy ra hai lần** | ranh giới thư mục · `??` lạ = phiên khác · hỏi trước deploy |

`27_29 §29`

## 20. KHUYẾN NGHỊ CUỐI CÙNG

> **Chấp thuận phương án C.** Bắt đầu bằng **đợt 1** — hai ngày công, chạm
> `jobs.py`, và là thứ duy nhất trong toàn kế hoạch sửa một vấn đề **đang tốn
> tiền thật mỗi ngày** (92 % lượt nhặt bị lãng phí).

Đợt 1 vừa mang lại giá trị đo được ngay, vừa là **phép hiệu chuẩn** cho ước
lượng 7–10 tuần còn lại. Nếu `M3` không xuống ≤2,0, ta biết ngay rằng giả định
*"đọc được sức chứa vật lý đủ rẻ"* sai — **trước khi** tiêu 9 tuần vào phần còn
lại.

⛔ **Điểm dừng.** Không dòng mã sản phẩm nào được viết cho tới khi có phê duyệt.
Mọi lược đồ SQL, hợp đồng `ToolSpec`, lộ trình trong bộ tài liệu này là **đề
xuất**. `platform_core/registry.py` chưa bị sửa một ký tự.

---

## PHỤ LỤC — BỘ TÀI LIỆU

| Tệp | Nội dung |
|---|---|
| `00_TIEN_DO.md` | bảng theo dõi · sổ nợ `N1` `N2` |
| `00_EXECUTIVE_SUMMARY.md` | **tệp này** |
| `01_CURRENT_LTT_ARCHITECTURE.md` | đo LTT + Phụ lục A (log production 28 ngày) |
| `02_LTT_WORKFLOW_V2_REQUIREMENTS.md` | 41 yêu cầu · 10 ngưỡng số |
| `03_REPOSITORY_MANIFEST.md` | 7 kho, tag + SHA + giấy phép |
| `04` `05` `06` `07_08` `09` `10` | khảo sát mã từng kho |
| `12_19_TONG_HOP_SO_SANH.md` | so sánh ngang · bảng điểm · chốt `Q1 Q3 Q5 Q7` |
| `21_22_GAP_VA_MA_TRAN_QUYET_DINH.md` | 47 khoảng trống · KEEP/ADAPT/REWRITE |
| `23_24_KIEN_TRUC_VA_MO_HINH_DU_LIEU.md` | kiến trúc đích · lược đồ · chốt `Q2 Q4` |
| `25_26_NODE_SDK_VA_HOP_DONG.md` | `ToolSpec` mở rộng · máy trạng thái · chốt `Q8` |
| `27_29_DI_TRU_LO_TRINH_RUI_RO.md` | di trú · 5 đợt · 9 rủi ro |
| `30_QUYET_DINH_KIEN_TRUC_CUOI_CUNG.md` | so 5 phương án · **ADR-WF-001** |

**Tổng:** 15 tệp. Kho OSS ở `D:\LTT_ARCHITECTURE_LAB\` (1,0 GB), **ngoài** kho
sản phẩm.

*Không sửa mã sản phẩm LTT. Không chép mã bên thứ ba vào kho.*
