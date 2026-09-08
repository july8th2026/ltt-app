# 27+28+29 — DI TRÚ · LỘ TRÌNH · SỔ RỦI RO (pha G)

> Gộp ba tài liệu vì chúng trả lời **một** câu: *làm theo thứ tự nào, và hỏng ở
> đâu*. Và vì `27_MIGRATION` gần như rỗng — **không có runtime nào để di trú**.
>
> **Đầu vào:** `21_22 §22.4` (5 đợt) · `23_24` + `25_26` (thiết kế) ·
> `02 §13` (10 ngưỡng số) · luật `CLAUDE.md` 07/09 (chưa có khách trên lớp này).

---

## PHẦN 27 — DI TRÚ

### 27.1 🔴 Bài toán di trú NHỎ — nhưng KHÔNG rỗng

⚠️ **ĐÃ SỬA 2026-09-08 sau khi đo `D2`.** Bản đầu của mục này viết *"gần như
KHÔNG TỒN TẠI"* và kết luận *"không có khách đứng trên đường cũ ⇒ thay thẳng,
gỡ bản cũ"*. Kết luận ấy **sai**, và nó sai từ một phép đo **đúng**.

```
0 job agent.advance / 28 ngày log production          (01 §A.1)      <- DUNG
agent_workflows 10 · agent_runs 4 · agent_workflow_snapshots 83      <- do D2, 08/09
đối chứng: users 27 · jobs 1770 · credit_entries 5500
```

🔑 `0 run` nói **KHÔNG AI CHẠY**. Nó **không** nói **KHÔNG AI ĐÃ DỰNG**. Hai
mệnh đề khác nhau, và bản đầu đã đọc mệnh đề thứ nhất thành mệnh đề thứ hai.

⇒ Vẫn **không có trạng thái thi hành để chuyển** (`0 run` — phần ấy đúng), và
  vẫn **không cần lớp tương thích runtime**. Nhưng **có 10 workflow người thật
  đã dựng**, nên "gỡ bản cũ" là xoá việc của họ.

## ⭐ Hình dạng thật của 10 bản ghi mới là thứ quyết cách làm

Đo tiếp (chỉ đọc, 08/09):

```
10/10 mang tên mặc định "Workflow mới"   không ai đổi tên
tối đa 3 node, tối đa 2 cạnh             không đồ thị nào thật sự
4/10 `document` RỖNG                     chỉ còn `nodes`/`edges` cũ
6/10 `document` 5 khoá                   active_page_id · budget_max_credit
                                         · goal · pages · version
3 `validated` · 7 `draft` · tất cả `plan_version = 1`
```

⇒ `M-1` **có thật nhưng nhỏ**, và nó phải xử **ba lớp** chứ không một. Xem
  `platform_core/workflow/di_tru_m1.py` và `tests/test_963`.

⛔ Cả hai kết luận trước — *"bài toán rỗng"* (từ `0 run`) và *"97 bản ghi cần di
   trú"* (từ tổng `D2`) — đều **đọc một con số tổng rồi suy ra cách làm**. Chỉ
   hình dạng nói được, và hình dạng chỉ có khi mở dữ liệu ra xem.

Đối chiếu với `§22` của đề bài (*"Never perform a big-bang rewrite unless
evidence overwhelmingly supports it"*): bằng chứng **có** ủng hộ — nhưng chỉ cho
**một lớp**. Bảng dưới nói rõ ranh giới:

| Lớp | Có khách? | Cách làm |
|---|---|---|
| `platform_core/agent/` (1.843 dòng) | **0 run**, nhưng **10 workflow đã dựng** | thay thẳng phần THI HÀNH; bản nháp đi qua `M-1` |
| `frontend/agent-canvas` (2.061 dòng) | không | đổi tại chỗ, 52 test là lưới |
| `jobs.py` · `credit.py` · `job_runner.py` · `gpu_lease.py` | **CÓ** — 868 job/28 ngày | **sửa tại chỗ, từng thay đổi nhỏ, gate xanh** |

### 27.2 Ba thứ **thật sự** phải chuyển

| # | Thứ | Lượng | Cách |
|---|---|---|---|
| M-1 | `AgentWorkflow.document` (Canvas v2) → `workflow_draft.document` (v3) | **`UNKNOWN`** — cần `D2` | **một script chạy một lần**, không phải lớp tương thích runtime |
| M-2 | `AgentWorkflowSnapshot` → lịch sử bản nháp | như trên | giữ nguyên bảng, đổi tên cột nếu cần |
| M-3 | `AgentWorkflowShare` | ít | giữ nguyên — token hash không phụ thuộc lược đồ đồ thị |

⭐ **Chỉ M-1 là công việc thật**, và nó là một phép biến đổi JSON thuần: Canvas v2
đã có `nodes[]`/`edges[]` với `sourceHandle`/`targetHandle` (`01 §3.2`) — tức
**dữ liệu để dựng cạnh có kiểu ĐÃ CÓ SẴN**, chỉ là hôm nay `canvas_to_plan()`
vứt nó đi. Script chuyển **giữ lại** thứ đang bị vứt.

### 27.3 Thứ **bị gỡ**, không phải bị di trú

```
platform_core/agent/executor.py       334 dòng   → thay bằng 8 hệ con
platform_core/agent/workflows.py      314        → tách: draft store + publish
platform_core/agent/runs.py           138        → workflow_run + snapshot
platform_core/agent/budget.py         136        → giữ logic, đổi chỗ neo
Plan v1 (canvas_to_plan/plan_to_canvas)          → GỠ HẲN
AgentRun.checkpoint (cột JSON)                   → GỠ HẲN
```

⚠️ **`validator.py` (261) và `verifier.py` (179) KHÔNG gỡ** — validator là tài
sản (`WF-501`, thứ không kho nào có); verifier là AI-specific và vẫn đúng, chỉ
phải **ra khỏi transaction** (`G23`).

### 27.4 Một câu cần số đo — và giả định đang chạy

`D2`: bao nhiêu `AgentWorkflow` bản nháp trong CSDL production?
Không đọc được — `LTT_DATABASE_URL` ở `secrets/`, ACL chặn **cố ý** (W1.5).

> **Giả định đang chạy:** *có bản nháp, cần viết script M-1.*
> Nếu số là **0** thì bỏ luôn M-1 và pha di trú thành **rỗng hoàn toàn**.
> **Không chặn gì** — script M-1 nằm ở đợt 5, cuối lộ trình.

---

## PHẦN 28 — LỘ TRÌNH

### 28.0 Nguyên tắc xếp thứ tự

Xếp theo **giá trị đo được / rủi ro**, không theo thứ tự logic của kiến trúc.
Hệ quả: **đợt 1 không đụng gì tới Workflow V2** — nó sửa một thứ đang làm hỏng
tải thật hôm nay.

Mỗi đợt có **ngưỡng nghiệm thu bằng số**. Không đạt ngưỡng ⇒ không sang đợt sau.

---

### ĐỢT 1 — Sửa thứ đang chảy máu hôm nay
**Không chạm Workflow V2. Chạm `platform_core/jobs.py`.**

| # | Việc | Giải | Ngưỡng |
|---|---|---|---|
| 1.1 | `claim()` lọc theo sức chứa tài nguyên **trước khi** nhặt | `G11` | **`M3`: 13,7 → ≤2,0** lượt nhặt/job |
| 1.2 | `UNIQUE(user_id, dedupe_key) WHERE status IN (queued,running)` | `G24` | đóng cửa sổ tranh chấp |
| 1.3 | Đo đường cơ sở trước/sau bằng chính log worker | — | có số đối chứng |

**Vì sao đứng đầu:** `F2` đo được **92,2 %** lượt nhặt `ltt_llm.chat` kết thúc
bằng *nhả ra vì bận*; **11.929 lượt nhặt cho 868 job xong**. Đây là mục **duy
nhất** trong toàn kế hoạch có tác dụng lên lưu lượng **đang chạy thật**.

⚠️ **Rủi ro cao nhất trong cả lộ trình** — đây là mã đang phục vụ. Làm nhỏ, một
thay đổi một lần, gate đầy đủ mỗi lần.

**Ước lượng:** 2–3 ngày làm việc.

---

### ĐỢT 2 — Nền tảng bền vững mới (song song, chưa nối vào gì)

| # | Việc | Giải | Ngưỡng |
|---|---|---|---|
| 2.1 | Bảng `workflow` · `workflow_draft` · `workflow_version` (+2 chỉ mục) | `G07` | hash ổn định; publish trùng nội dung → cùng version |
| 2.2 | Bảng `node_run` · `node_run_snapshot` (chỉ thêm) | `G18`·`G19`·`G20`·`G21` | **`M1`: `O(node đổi)`**, không phải `O(31+N)` |
| 2.3 | Bảng `waitpoint` · `waitpoint_signal` · `node_run_waitpoint` | `G25` | barrier `N-of-M` + `sealed` có test |
| 2.4 | Bảng `wakeup` + chỉ số bộ phận + bộ quét 5 giây | `G26` | **`M2`: run chờ 60' → `O(1)` SQL** |

**Không nối vào đường chạy nào.** Chỉ lược đồ + service + test. Rủi ro ~0.

**Ước lượng:** 1 tuần.

---

### ĐỢT 3 — Scheduler mới, chạy sau cờ

| # | Việc | Giải | Ngưỡng |
|---|---|---|---|
| 3.1 | 8 hệ con thay `executor.tick()` | `G09`·`G12`·`G23` | không I/O ngoài trong transaction (kiểm tĩnh) |
| 3.2 | Hệ con `finally` — kết sổ trong cùng transaction kết thúc | `G16`·`G32` | **`M10`: 145 → 0** hold treo |
| 3.3 | Middleware trên cạnh (3 hook) | `G45` | quyền tool kiểm **lúc thi hành** |
| 3.4 | Bộ chaos: giết tiến trình ở 10 điểm | — | **`M6`: 10/10 cùng kết quả** |

⚠️ **`verifier.verify()` phải ra khỏi transaction** (`G23`) — đây là lỗi LTT
đang mắc mà chính `job_runner` đã cấm cho handler.

**Ước lượng:** 1,5–2 tuần.

---

### ĐỢT 4 — Nguyên hàm đồ thị

| # | Việc | Giải | Ngưỡng |
|---|---|---|---|
| 4.1 | Edge là thực thể; 3 `kind` (`DATA`/`CONTROL`/`RESOURCE`) | `G02`·`G03`·`G04` | đồ thị dựng qua API ≡ dựng qua Canvas |
| 4.2 | Hệ kiểu 15 kiểu + cardinality; **một nguồn luật nối dây** | `G37`·`G38`·`G39` | **`M9`: client ≡ server 100 %** |
| 4.3 | ForEach: `parallel` · `parallelism` (biểu thức) · `max_items` **bắt buộc** | `G13` | **`M7`: 100 phần tử, crash giữa → 100 kết quả, 0 lặp** |
| 4.4 | Join `ALL`/`ANY`/`N-of-M` + `behavior` tràn | `G12`·`G10` | **`M4`: song song khai được** |
| 4.5 | Node không sinh Job (8 loại điều khiển) | `G15` | rẽ nhánh không tạo dòng sổ tiền |
| 4.6 | Trần chi phí mở rộng: ForEach · nhánh · subflow · `ai_choice` | `WF-501` | **`M8`: báo giá kèm hai số** |

⭐ **4.6 là mục không có đối chứng ngành** — không kho nào trong bảy kho có trần
chi phí. Phải có bộ test riêng, không được coi là an toàn vì "ngành làm thế".

**Ước lượng:** 2–3 tuần.

---

### ĐỢT 5 — Artifact · Canvas · Trigger · API

| # | Việc | Giải | Ngưỡng |
|---|---|---|---|
| 5.1 | Bảng `artifact`, id `<backend>:<key>`, lineage, TTL theo lớp | `G33`·`G35`·`G36` | R2 + Local song song không mơ hồ |
| 5.2 | Canvas v3: cạnh có kiểu thật, auto-layout, chi phí trên node | `G40` | frontend **không** hardcode tên tool (có test) |
| 5.3 | Script di trú M-1 (nếu `D2` > 0) | §27.2 | bản nháp cũ mở được |
| 5.4 | Trigger: API · schedule · webhook (mỗi loại một mô-đun) | `G42` | thêm loại thứ tư không sửa `platform_core` |
| 5.5 | `POST /api/v1/workflows/{id}/runs` + webhook `run.*` | `G43` | qua `inventory.py`, không dựng API thứ hai |
| 5.6 | `ToolSpec` 6 trường mới + `mock` | `G05`·`G41` | registry kiểm được lúc nạp |

**Ước lượng:** 2–3 tuần.

---

### 28.6 Tổng và đường tới hạn

```
Đợt 1  ██                2–3 ngày    ← độc lập, làm được ngay
Đợt 2  █████             1 tuần      ← độc lập với đợt 1
Đợt 3  ████████          1,5–2 tuần  ← cần đợt 2
Đợt 4  ████████████      2–3 tuần    ← cần đợt 3
Đợt 5  ████████████      2–3 tuần    ← cần đợt 4 (trừ 5.1, 5.6 làm sớm được)
                         ─────────
                         7–10 tuần
```

⚠️ Ước lượng cho **một người làm liên tục**, và nó **không** gồm:
- `N2` — nguyên mẫu chạy thật (Trigger.dev + Temporal) để gỡ các nhãn `UNKNOWN`
- `N1` — nhánh node media/GPU (đã ghi nợ)
- Bất kỳ tính năng sản phẩm nào ngoài Workflow V2

---

## PHẦN 29 — SỔ RỦI RO

Xếp theo **hệ quả × khả năng**, không theo thứ tự phát hiện.

### R1 — Đợt 1 làm hỏng đường job đang phục vụ 🔴🔴

| | |
|---|---|
| **Hệ quả** | Job thật không được nhặt, hoặc bị nhặt trùng. Ảnh hưởng **868 job/28 ngày** |
| **Khả năng** | trung bình — `claim()` là mã tinh vi (`SKIP LOCKED` + fair-share + aging) |
| **Vì sao vẫn làm** | đây là chỗ **duy nhất** đang chảy máu; không sửa thì 92 % lãng phí tiếp diễn |
| **Giảm thiểu** | thay đổi nhỏ từng bước · gate đầy đủ mỗi bước · đo log worker trước/sau · giữ đường cũ sau một cờ **chỉ cho mục này** |

⚠️ **Ngoại lệ có chủ ý với luật "chưa có khách":** đợt 1 chạm lớp **đang phục vụ
thật**, nên nó là chỗ duy nhất trong lộ trình **được phép** có cờ và đường lùi.
Luật `CLAUDE.md` nói không cần lo cho khách ở lớp Agent — không nói ở lớp job.

### R2 — Ba mục `INFERRED` không có đối chứng ngành 🔴

| | |
|---|---|
| **Là gì** | lọc sức chứa từ **tài nguyên vật lý** · `est_duration_s` làm đầu vào xếp chỗ · trần chi phí phủ ForEach/nhánh |
| **Hệ quả** | thiết kế đúng trên giấy, sai khi gặp GPU thật bị tiến trình ngoài chiếm |
| **Vì sao có** | sổ nợ `N1` — không kho nào có bài toán "node = 20 phút GPU" |
| **Giảm thiểu** | mỗi mục một thí nghiệm riêng trong đợt tương ứng; **không** gộp vào test chung |

### R3 — Snapshot chỉ-thêm làm bảng phình 🟠

| | |
|---|---|
| **Hệ quả** | một run 100 node × ~6 lần chuyển = ~600 hàng/run |
| **Khả năng** | chắc chắn xảy ra; câu hỏi là ở quy mô nào |
| **Giảm thiểu** | TTL theo `ttl_class` · gộp snapshot cũ sau N ngày · chỉ số `(run_id, created_at)` |
| **Đối chứng** | Trigger.dev sống với mô hình này ở quy mô lớn hơn LTT nhiều |

### R4 — Đo lại `M1`/`M3` trên Postgres cho kết quả khác SQLite 🟠

| | |
|---|---|
| **Hệ quả** | ngưỡng đặt sai; tưởng đạt mà không đạt |
| **Vì sao** | `31+N` đo trên **SQLite** (`01 §5.6`); kế hoạch truy vấn Postgres khác |
| **Giảm thiểu** | đo lại trên Postgres **trước** đợt 2. Độ dốc `O(N)` không đổi; hằng số thì đổi |

### R5 — Phiên khác sửa cùng cây 🟠

| | |
|---|---|
| **Hệ quả** | gate đỏ vì việc của phiên khác; deploy chép cả cây |
| **Khả năng** | **đã xảy ra hai lần trong phiên khảo sát này** |
| **Giảm thiểu** | ranh giới thư mục · `?? ` lạ = phiên khác đang làm · hỏi trước deploy |

### R6 — 21 sửa của tài liệu 02 chưa hợp nhất 🟡

| | |
|---|---|
| **Hệ quả** | phiên sau đọc `02` tưởng đó là yêu cầu cuối cùng, bỏ sót 21 sửa |
| **Giảm thiểu** | `00_TIEN_DO §6` đã cảnh báo; `23_24`+`25_26` là bản đã hợp nhất |
| **Cố ý không sửa `02`** | giữ dấu vết *"yêu cầu của ta TRƯỚC khi nhìn ai khác"* — đề bài §3 |

### R7 — Ước lượng 7–10 tuần sai 🟡

| | |
|---|---|
| **Vì sao** | không có đường cơ sở nào cho "viết lại một scheduler" ở kho này |
| **Giảm thiểu** | đợt 1 (2–3 ngày) là **phép hiệu chuẩn**: đo thật rồi nhân lại |

### R8 — Gỡ Plan v1 làm gãy thứ chưa biết 🟡

| | |
|---|---|
| **Khả năng** | thấp — `grep` cho thấy chỉ `apps/agent` và `tools/agent_browser_server.py` dùng |
| **Giảm thiểu** | grep toàn kho trước khi gỡ; 103 test Python là lưới |

### R9 — Ổ D: đầy 🟡

41 GB/466 GB (92 %). Lab đã 1,0 GB. `N2` (chạy thật) cần vài GB nữa.
**Giảm thiểu:** chuyển lab sang ổ C: (459 GB) trước khi làm `N2`.

---

## 29.10 Rủi ro ĐÃ ĐÓNG nhờ khảo sát

Ghi lại để thấy khảo sát mua được gì:

| Rủi ro giả định ban đầu | Vì sao đóng |
|---|---|
| *"Viết lại executor sẽ ảnh hưởng khách"* | **0 run/28 ngày** — không có khách trên lớp đó |
| *"Phải giữ tương thích Plan v1"* | không có run nào để tương thích |
| *"Có thể phải bỏ React Flow"* | đối chứng Node-RED **5×**; giữ, `CONFIRMED` |
| *"Nên adopt Temporal"* | máy chủ **không cưỡng chế được** tất định; bước LTT không thể tất định |
| *"Trạng thái JSON là đủ"* | ba hệ dùng nó **đều đụng trần**; n8n phải xây `db\|fs\|s3\|az` |
| *"Không biết bắt đầu từ đâu"* | đợt 1 có ngưỡng số và tác dụng lên tải thật |

---

## 29.11 PHA G ĐÓNG

Còn pha H: `30_FINAL_ARCHITECTURE_DECISION` (so 5 phương án A–E) ·
`ARCHITECTURE_DECISION_RECORD` · `00_EXECUTIVE_SUMMARY` (20 câu của đề bài §25).

---

*Không sửa mã sản phẩm LTT. Lộ trình trong tài liệu này là **đề xuất**; không
dòng mã nào được viết cho tới khi có phê duyệt.*
