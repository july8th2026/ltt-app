# 23+24 — KIẾN TRÚC ĐÍCH & MÔ HÌNH DỮ LIỆU (pha F)

> Gộp `23_TARGET_ARCHITECTURE` và `24_TARGET_DATA_MODEL`: lược đồ **là** kiến
> trúc ở hệ này, tách ra sẽ phải nhắc lại nhau.
>
> **Đầu vào:** 21 sửa tích luỹ từ bảy kho (`12_19 §22`) · 47 khoảng trống
> (`21_22`) · 41 yêu cầu (`02`) · 10 ngưỡng số (`02 §13`).
> **Chốt trong tài liệu này:** `Q2` (lưu định nghĩa) · `Q4` (đánh thức).
>
> ⭐ **Áp dụng luật mới của `CLAUDE.md` (07/09): chưa có khách trên lớp này** —
> 0 job `agent.advance` / 28 ngày. Nên bản thiết kế dưới đây **không có** lớp
> tương thích ngược, **không có** đường di trú Plan v1, **không có** cờ bật dần.
> Thiết kế thẳng thứ đúng.

---

## 1. HÌNH DẠNG TỔNG THỂ

```
                         ┌──────────────── NGƯỜI ─────────────────┐
                         │ Canvas (React Flow)   Agent (LLM)      │
                         └───────────┬───────────────┬────────────┘
                                     │ soạn          │ đề xuất
                                     ▼               ▼
   ╔═══════════════════════ WORKFLOW CORE (mới) ══════════════════════════╗
   ║                                                                      ║
   ║   workflow ──► workflow_draft ──publish──► workflow_version (BẤT BIẾN)║
   ║                                              │  hash + node[] + edge[]║
   ║                                              ▼                       ║
   ║   VALIDATOR (tất định · không LLM · không tiền · không mạng)          ║
   ║                                              │                       ║
   ║                                              ▼                       ║
   ║   QUOTE  ──► trần chi phí tất định ──► APPROVAL ──► HOLD (1 lần/run)  ║
   ║                                              │                       ║
   ║                                              ▼                       ║
   ║   ┌────────────── SCHEDULER = 8 HỆ THỐNG CON ─────────────────┐      ║
   ║   │ enqueue · dequeue · attempt · waitpoint · snapshot ·        │     ║
   ║   │ foreach · ttl · finally                                     │     ║
   ║   └────────────────────┬───────────────────────────────────────┘     ║
   ║                        │ ghi MỘT HÀNG mỗi lần chuyển trạng thái      ║
   ║                        ▼                                             ║
   ║   node_run_snapshot (CHỈ THÊM) ◄── waitpoint ◄── waitpoint_signal    ║
   ╚════════════════════════╤═════════════════════════════════════════════╝
                            │ submit job  (đi qua MIDDLEWARE CẠNH)
                            ▼
   ╔════════════════ NỀN TẢNG HIỆN CÓ — KEEP, không đụng ══════════════════╗
   ║  jobs.py (hàng đợi)   credit.py (sổ)   gpu_lease/leases   registry     ║
   ║  job_runner (worker)  storage.py       public_api (24 route)           ║
   ╚═══════════════════════════════════════════════════════════════════════╝
```

⭐ **Ranh giới quan trọng nhất:** Workflow Core **không thay** bất kỳ hộp nào ở
tầng dưới. Nó **ngồi trên** hàng đợi hiện có và submit job như mọi app khác.
Đó là điều kiện để `KEEP 13` giữ được giá trị.

---

## 2. 🔴 CHỐT `Q2` — LƯU ĐỊNH NGHĨA: **LAI, và ranh giới là "ai đọc nó"**

Ba lựa chọn của đề bài §17:

| | Ưu | Nhược |
|---|---|---|
| A. một khối JSONB bất biến | đọc một phát; hash dễ | không truy vấn được *"workflow nào dùng tool X"* |
| B. bảng chuẩn hoá `node`/`edge` | truy vấn được | dựng lại đồ thị = nhiều JOIN; hash phải tính lại |
| C. **lai** | | phải giữ hai thứ khớp nhau |

**Chốt: C — lai, cắt theo NGƯỜI ĐỌC, không theo dữ liệu.**

```
workflow_version.graph   JSONB BẤT BIẾN   ← nguồn chân lý cho THI HÀNH
                                            đọc một lần lúc bắt đầu run
workflow_version_node    bảng             ← CHỈ MỤC cho TRUY VẤN VẬN HÀNH
workflow_version_edge    bảng               sinh ra từ graph lúc publish
```

**Vì sao cắt theo người đọc là ranh giới đúng:**

- **Runtime** cần đồ thị **nguyên vẹn, một lần, bất biến** ⇒ JSONB thắng. Nó
  cũng làm hash tầm thường (`sha256` của chuỗi chuẩn hoá).
- **Vận hành** cần trả lời *"tool `video.generate` đang nằm trong bao nhiêu
  version đã publish?"* trước khi đổi schema của nó — câu này JSONB trả lời
  bằng cách quét toàn bảng.
- **Hai thứ không thể lệch**, vì bảng chỉ mục **sinh ra từ** JSONB tại đúng một
  điểm: `publish()`. Không có đường nào khác ghi vào chúng.

⇒ Đây **không phải** hai nguồn chân lý. Là **một nguồn + một chỉ mục dẫn xuất**.
Cùng khuôn `AgentWorkflow.document` + cột chiếu hiện có (`01 §3.1`) — LTT đã
đúng, chỉ là chưa nói ra lý do.

`HIGH`

---

## 3. 🔴 CHỐT `Q4` — ĐÁNH THỨC: **bảng `wakeup` + `LISTEN/NOTIFY` làm gia tốc**

| | Ưu | Nhược |
|---|---|---|
| A. `LISTEN/NOTIFY` thuần | tức thì, không polling | **mất khi mất kết nối**; không bền qua restart |
| B. Bảng `wakeup` + quét theo chỉ số | bền; hội tụ 2 kho | trễ bằng chu kỳ quét |
| C. **B + A** | bền **và** tức thì | hai đường phải cùng idempotent |

**Chốt: C.** Bảng là **nguồn chân lý**; `NOTIFY` chỉ **rút ngắn độ trễ**.

```sql
-- nguồn chân lý
CREATE TABLE wakeup (
  id            uuid PRIMARY KEY,
  run_id        uuid NOT NULL,
  node_run_id   uuid,
  kind          text NOT NULL,          -- job_done | waitpoint_due | approval | child_run | resource_free
  due_at        timestamptz NOT NULL,
  claimed_at    timestamptz,
  UNIQUE (run_id, node_run_id, kind, due_at)      -- khử trùng bằng RÀNG BUỘC
);
CREATE INDEX ix_wakeup_due ON wakeup (due_at)
  WHERE claimed_at IS NULL;                        -- ⭐ CHỈ SỐ BỘ PHẬN
```

**Bằng chứng chọn hình dạng này — hội tụ độc lập ba lần:**

| Kho | Cơ chế |
|---|---|
| Activepieces | `idx_waitpoint_pending_resume_date_time WHERE status='PENDING' AND resumeDateTime IS NOT NULL` |
| n8n | `@Index(['waitTill','id'])` trên execution |
| Trigger.dev | `delayedRunSystem` + Redis worker |

⭐ **`F3` quyết định vì sao bảng phải là nguồn chân lý, không phải `NOTIFY`:**
worker restart **13,6 lần/ngày** (`01 §A.6`). Một `NOTIFY` phát lúc worker đang
khởi động lại **biến mất không dấu vết**. Bảng thì không.

⇒ Đây chính là *"polling như dự phòng, không phải cơ chế chính"* mà `WF-402` yêu
cầu. Quét mỗi **5 giây** (không phải 2 giây như hôm nay) vì `NOTIFY` lo phần tức
thì.

**Ngưỡng `M2` đạt được thế nào:** một run chờ 60 phút có **1 hàng** trong
`wakeup` với `due_at = +60min`. Trong 60 phút đó nó phát sinh **0 câu SQL** —
bộ quét toàn cục hỏi *"có hàng nào `due_at <= now()` không"* bằng **một** truy
vấn cho **toàn hệ thống**, đi thẳng vào chỉ số bộ phận.
`HIGH`

---

## 4. LƯỢC ĐỒ ĐÍCH

### 4.1 Định nghĩa workflow

```sql
CREATE TABLE workflow (
  id, owner_id, name, created_at, updated_at,
  published_version_id  uuid,          -- version đang được trigger dùng
  archived_at           timestamptz
);

CREATE TABLE workflow_draft (           -- bản đang soạn; SỬA ĐƯỢC
  workflow_id  uuid PRIMARY KEY,
  document     jsonb NOT NULL,          -- Canvas v3: pages, frames, notes, layout
  revision     int  NOT NULL,           -- khoá lạc quan (409)
  updated_at   timestamptz
);

CREATE TABLE workflow_version (         -- BẤT BIẾN sau khi tạo
  id            uuid PRIMARY KEY,
  workflow_id   uuid NOT NULL,
  seq           int  NOT NULL,          -- 1,2,3… hiển thị cho người
  graph         jsonb NOT NULL,         -- {schema_version, nodes[], edges[]}
  graph_hash    char(64) NOT NULL,      -- sha256(chuẩn hoá tất định)
  estimated_max int  NOT NULL,          -- trần chi phí, ĐÓNG BĂNG cùng graph
  created_at, created_by,
  UNIQUE (workflow_id, seq),
  UNIQUE (workflow_id, graph_hash)      -- publish nội dung trùng → trả version cũ
);
```

⭐ **`UNIQUE (workflow_id, graph_hash)`** khiến *"publish hai lần cùng nội dung"*
trở thành **không thể**, bằng ràng buộc chứ không bằng mã cẩn thận — khuôn đã
hội tụ ba lần (`12_19 §16`).

⚠️ **Trường loại trừ khỏi hash** (bài học Kestra, `07+08 §1.4`) — khai tường
minh, có test:
```
LOAI_TRU_KHOI_HASH = {"position", "label", "summary", "_ui", "created_at", "updated_at"}
```
Không khai thì `position` lọt vào hash ⇒ kéo một node sang phải sinh version mới.

**Chỉ mục dẫn xuất, sinh tại `publish()`:**
```sql
CREATE TABLE workflow_version_node (
  version_id, node_id, node_type, type_version, PRIMARY KEY (version_id, node_id));
CREATE TABLE workflow_version_edge (
  version_id, edge_id, source_node, source_port, target_node, target_port,
  kind,                                  -- DATA | CONTROL | RESOURCE
  condition jsonb,
  PRIMARY KEY (version_id, edge_id));
CREATE INDEX ix_wvn_type ON workflow_version_node (node_type);   -- "tool X ở đâu?"
```

### 4.2 Thi hành — mô hình C

```sql
CREATE TABLE workflow_run (
  id, owner_id, workflow_id,
  version_id       uuid NOT NULL,        -- GHIM, không bao giờ đổi
  status           text NOT NULL,        -- xem §5
  trigger_kind     text NOT NULL,
  idempotency_key  text,
  estimated_max    int, actual_cost int,
  hold_id          uuid,                 -- trỏ sổ credit
  created_at, started_at, finished_at,
  UNIQUE (owner_id, idempotency_key)     -- ⭐ ràng buộc, không phải SELECT-rồi-INSERT
);

CREATE TABLE node_run (                  -- MỘT hàng mỗi node mỗi run · con trỏ
  run_id, node_id,
  latest_snapshot_id uuid NOT NULL,
  PRIMARY KEY (run_id, node_id)
);

-- ⭐⭐ TRÁI TIM CỦA THIẾT KẾ: CHỈ THÊM, KHÔNG BAO GIỜ SỬA
CREATE TABLE node_run_snapshot (
  id                   uuid PRIMARY KEY,
  run_id, node_id,
  previous_snapshot_id uuid,             -- chuỗi liên kết
  execution_status     text NOT NULL,    -- §5
  run_status           text NOT NULL,
  attempt_number       int,
  is_valid             boolean NOT NULL DEFAULT true,   -- ⭐ GHI CẢ LẦN CHUYỂN BỊ TỪ CHỐI
  error                text,
  description          text NOT NULL,    -- vì sao chuyển
  job_id               uuid,
  output_ref           jsonb,            -- CHỈ tham chiếu artifact, không bytes
  cost_credit          int,              -- ⭐ ghi LÚC KẾT THÚC, không tính lại
  created_at           timestamptz NOT NULL
);
CREATE INDEX ix_nrs_run ON node_run_snapshot (run_id, created_at);
```

🔴 **Bốn thứ giải quyết cùng lúc bởi bảng cuối** (`21_22`: G18·G19·G20·G21·G44):
lịch sử đầy đủ · điều tra được chuyển trạng thái tranh chấp · chi phí theo
attempt · dòng thời gian mà **không cần bảng nhật ký thứ hai**.

**`M1` đạt thế nào:** một lượt tiến ghi `INSERT` cho **đúng những node vừa đổi**
+ `UPDATE` con trỏ `node_run.latest_snapshot_id`. Không có đọc–sửa–ghi khối nào.
`O(node đổi)`, không phải `O(31+N)`.

### 4.3 Waitpoint

```sql
CREATE TABLE waitpoint (
  id, run_id, owner_id,
  kind        text NOT NULL,   -- DELAY | JOB | WEBHOOK | HUMAN | CHILD_RUN | BARRIER
  status      text NOT NULL,   -- PENDING | COMPLETED | EXPIRED | CANCELLED
  sealed      boolean NOT NULL DEFAULT false,   -- ⭐ "sẽ không còn tín hiệu nào nữa"
  policy      jsonb,           -- {required_successes, release_on_first_failure}
  due_at      timestamptz,
  token_hash  char(64),        -- đánh thức từ ngoài
  output_ref  jsonb, output_is_error boolean,
  idempotency_key text,
  UNIQUE (owner_id, idempotency_key)
);
CREATE INDEX ix_waitpoint_due ON waitpoint (due_at)
  WHERE status = 'PENDING' AND due_at IS NOT NULL;      -- ⭐ chỉ số bộ phận

CREATE TABLE waitpoint_signal (
  waitpoint_id, seq int,
  status  text NOT NULL,   -- PENDING | SUCCEEDED | FAILED | CANCELLED | NOT_DISPATCHED
  ref_id  text, result_ref jsonb,
  UNIQUE (waitpoint_id, seq)
);

CREATE TABLE node_run_waitpoint (      -- ⭐ NHIỀU-NHIỀU: 1 waitpoint chặn N node
  run_id, node_id, waitpoint_id,
  PRIMARY KEY (run_id, node_id, waitpoint_id)
);
```

⭐ **Nhiều-nhiều là bắt buộc, không phải tiện nghi** (bài học Trigger.dev,
`09 §3.2`): `WF-204` có kịch bản *"20 node ForEach cùng chờ một job GPU"*. Mô
hình một-waitpoint-một-bước của Activepieces không biểu đạt được.

⭐ **`sealed`** (bài học Activepieces, `04 §3.3`): không có nó thì `ALL` **không
định nghĩa được** khi số nhánh là động.
⭐ **`NOT_DISPATCHED`**: tín hiệu lẽ ra phải gửi mà chưa bao giờ gửi — không có
nó, một nhánh chết treo barrier vĩnh viễn.

### 4.4 Artifact

```sql
CREATE TABLE artifact (
  id            text PRIMARY KEY,        -- ⭐ "<backend>:<key>" — TỰ MÔ TẢ
  owner_id      uuid NOT NULL,
  created_by_snapshot_id uuid,           -- ⭐ LINEAGE
  kind          text,                    -- image|video|audio|text|json|file
  mime, size_bytes bigint, checksum_sha256 char(64),
  ttl_class     text NOT NULL,           -- EPHEMERAL | RUN | PROJECT | PERMANENT
  expires_at    timestamptz,
  metadata      jsonb
);
CREATE INDEX ix_artifact_expiry ON artifact (expires_at)
  WHERE ttl_class <> 'PERMANENT' AND expires_at IS NOT NULL;
```

⭐ **`id` tự mô tả backend** (bài học n8n, `05 §4.1`) — vì tham chiếu đi vào
`output_ref` của bước sau, và JSONB **không tra bảng được**.
🔴 Đây là bản vá cho một lỗ **sẽ nổ** khi LTT bật R2 song song Local:
`storage.get_storage()` là singleton toàn cục ⇒ mọi khoá cũ thành mơ hồ (`G35`).

⚠️ **Hợp đồng lưu trữ có `delete` TUỲ CHỌN** (bài học n8n): backend nào có vòng
đời riêng (R2 lifecycle) thì **không** ép nó tự xoá — đừng chồng TTL của ta lên
TTL của R2.

### 4.5 Trigger & đánh thức

```sql
CREATE TABLE workflow_trigger (
  id, workflow_id, owner_id,
  kind      text NOT NULL,     -- MANUAL | API | SCHEDULE | WEBHOOK
  config    jsonb,             -- cron / đường dẫn webhook / …
  enabled   boolean,
  next_fire_at timestamptz
);
CREATE INDEX ix_trigger_due ON workflow_trigger (next_fire_at)
  WHERE enabled AND next_fire_at IS NOT NULL;
```

⭐ **Mỗi `kind` là một MÔ-ĐUN riêng**, không phải một `if` trong lõi (bài học
Windmill: 11 crate trigger). Cùng khuôn hợp đồng app — thêm loại thứ năm không
sửa `platform_core`.

---

## 5. MÁY TRẠNG THÁI (tài liệu 26, gộp vào đây)

```
workflow_run.status
   CREATED → VALIDATING → QUEUED → RUNNING ⇄ WAITING
                                      ├→ SUCCEEDED
                                      ├→ FAILED            (lỗi nghiệp vụ)
                                      ├→ SYSTEM_FAILURE    ⭐ lỗi CỦA TA
                                      ├→ CANCELLED
                                      └→ TIMED_OUT

node_run.execution_status
   PENDING → READY → QUEUED → RUNNING ⇄ RUNNING_WITH_WAITPOINTS
                                   ├→ SUCCEEDED
                                   ├→ FAILED
                                   ├→ SKIPPED     (nhánh không khớp)
                                   ├→ ABANDONED   ⭐ provider có thể ĐÃ nhận
                                   └→ CANCELLED
```

Ba thứ lấy từ Trigger.dev (`09 §1.4`):

1. **`RUNNING_WITH_WAITPOINTS`** — *đang chạy* và *đang chờ* **không loại trừ
   nhau**. `WF-207` bản nháp viết `RUNNING ⇄ WAITING` tách rời; với ForEach
   (một số vòng xong, một số đang chờ) thì **không biểu đạt được**.
2. **`SYSTEM_FAILURE` tách khỏi `FAILED`** — hai chuyện khác nhau về **hoàn
   tiền** và **cảnh báo vận hành**. LTT hôm nay gộp hết vào `AGENT_ERROR` (`G21`).
3. **`ABANDONED`** — kế thừa `provider_state = ambiguous` đã đúng của LTT.
   `AmbiguousProviderError` xảy ra **10 lần / 28 ngày** (`01 §A.4`) ⇒ có thật.

**Cưỡng chế:** bảng chuyển hợp lệ như `runs._TRANSITIONS` hiện có — và **mọi lần
chuyển bị từ chối vẫn ghi một snapshot** với `is_valid = false`.

---

## 6. SCHEDULER — TÁM HỆ THỐNG CON THAY MỘT `tick()`

| Hệ con | Trách nhiệm | Thay gì trong `executor.py` |
|---|---|---|
| `enqueue` | run mới → hàng đợi | `_prepare_run` |
| `dequeue` | ⭐ **lọc theo sức chứa TRƯỚC khi chọn** | `jobs.claim` (sửa) |
| `attempt` | submit job · nhận kết quả · thử lại | `_sync_children` + vòng submit |
| `waitpoint` | tạo · đánh thức · barrier | *(không có)* |
| `snapshot` | ghi chuyển trạng thái · con trỏ | `run.checkpoint = …` |
| `foreach` | map · concurrency · gom kết quả | *(không có)* |
| `ttl` | hết hạn run · waitpoint · artifact | rải rác |
| `finally` | ⭐ kết sổ credit · nhả lease **đúng một lần** | `_terminal_status` + `budget.settle` |

⭐ **`finally` là hệ con đáng chú ý nhất** (bài học Kestra): nó đóng lại
`G16`→`G32` — **145 lần hold treo / 28 ngày**. Hôm nay việc kết sổ nằm rải và
dựa vào một bộ dọn nền; ở đây nó là **một hệ con chạy trong cùng transaction
chuyển sang trạng thái kết thúc**.

**Middleware trên cạnh** (bài học Node-RED, 6 hook): mỗi lượt truyền qua một
cạnh đi qua `before_route → before_dispatch → after_dispatch`, hook trả `False`
thì **chặn**. Đây là chỗ cắm cho `WF-903` (kiểm quyền tool **lúc thi hành** —
`G45`) và đo `M3`, **mà không phình scheduler**.

---

## 7. BA MỤC KHÔNG CÓ ĐỐI CHỨNG NGÀNH

⚠️ Theo sổ nợ `N1` — phải gắn nhãn, không được trình bày như đã kiểm chứng.

| Mục | Nhãn | Vì sao không ai có |
|---|---|---|
| Lọc sức chứa từ **tài nguyên VẬT LÝ** (GPU, một suất máy B) | `INFERRED` | Trigger.dev đọc bộ đếm **của chính nó**; LTT phải hỏi thiết bị thật, và thiết bị đó bị tiến trình ngoài chiếm (`gpu_claims`) |
| `resource_class` · `vram_min_mb` · `est_duration_s` là đầu vào **xếp chỗ** | `INFERRED` | không hệ nào lập lịch quanh một thiết bị vật lý dùng chung |
| Trần chi phí tất định phủ ForEach · nhánh · subflow | `INFERRED` | **không kho nào có trần chi phí**; bước của họ gần như miễn phí |

⇒ Ba mục này **phải có thí nghiệm riêng** trong `28_ROADMAP`, không được coi là
đã an toàn vì "ngành làm thế".

---

## 8. ĐỐI CHIẾU VỚI 10 NGƯỠNG SỐ

| # | Ngưỡng | Cơ chế đạt | Mức |
|---|---|---|---|
| `M1` | SQL/lượt tiến: 131 → `O(node đổi)` | snapshot chỉ-thêm, không đọc–sửa–ghi khối | `HIGH` |
| `M2` | Run chờ 60': → `O(1)` | `wakeup` + chỉ số bộ phận; quét toàn cục 1 truy vấn | `HIGH` |
| `M3` | claim/job: 13,7 → ≤2,0 | `dequeue` lọc sức chứa trước khi chọn | `INFERRED` — cần đo |
| `M4` | song song: 4 → khai được | `parallel`/`parallelism` theo node | `HIGH` |
| `M5` | 500 node, validate <300ms | JSONB một lần + kiểm chu trình `O(V+E)` | `INFERRED` |
| `M6` | 10/10 điểm giết → cùng kết quả | mọi chuyển là một hàng đã commit | `HIGH` |
| `M7` | ForEach 100, crash giữa → 100 kết quả, 0 lặp | snapshot/vòng + `UNIQUE` dedupe | `HIGH` |
| `M8` | báo giá kèm **hai** số | `estimated_max` + kỳ vọng | `HIGH` |
| `M9` | luật nối dây client≡server | sinh từ một nguồn (`G39`) | `HIGH` |
| `M10` | hold treo: 145 → 0 | hệ con `finally` trong cùng transaction | `HIGH` |

---

## 9. ĐIỀU BẢN THIẾT KẾ NÀY **KHÔNG** CÓ — và vì sao

Theo luật `CLAUDE.md` 07/09 (*chưa có khách trên lớp này*):

| Không có | Vì sao |
|---|---|
| Lớp tương thích Plan v1 | **0 run trong 28 ngày**. Không có gì để tương thích |
| Đường di trú dữ liệu | Không có dữ liệu chạy nào để di trú |
| Cờ bật dần / canary | Không có ai để bật dần cho |
| Giữ song song engine cũ | Sẽ **gỡ**, không giữ |

⚠️ **Còn một số chưa đo được:** `AgentWorkflow` **bản nháp** đã lưu trong CSDL
production (`D2`, `secrets/` bị ACL chặn). Nếu > 0 thì cần **một** script chuyển
document sang lược đồ mới — **không** phải một lớp tương thích runtime.
Giả định đang chạy: **có bản nháp, cần script chuyển một lần**. Không chặn gì.

---

## 10. CÒN LẠI CỦA PHA F

`25_NODE_SDK_PROPOSAL` — chốt `Q8` (`AiTransform`) và mở rộng `ToolSpec`:
`type_version` · `side_effect` · `idempotency.key_fields` · `mock` ·
`timeout` là biểu thức · `resource{class, vram_min_mb, est_duration_s}`.

---

*Không sửa mã sản phẩm LTT. Không chép mã bên thứ ba. Lược đồ SQL trong tài
liệu này là **đề xuất**, chưa có migration nào được viết.*
