# 02 — LTT RUNTIME BASELINE

Đo **2026-09-09**, trên `admin-mvp-v3 @ 05464239980c25de4cb316755efd41b27da7ddce`.

> Mọi khẳng định dưới đây truy được về **mã nguồn**, kèm tệp và dòng. Chỗ nào
> chưa đo thì ghi `UNKNOWN` — MASTER-GUARDRAILS cấm biến `UNKNOWN` thành một
> quyết định thiết kế.

---

## 🔑 Kết luận đứng trước, vì nó đổi hình dạng cả chương trình

Nền tảng có **HAI** đường "node → job", và chúng **không cùng độ chín**. Prompt
pack giả định có một; thực tế có hai, và đường đang sống không phải đường mà cái
tên *"Workflow"* gợi ra.

| Đường | Trạng thái | Bằng chứng |
|---|---|---|
| **Agent executor** — plan đã duyệt → step → `ToolSpec` → `jobs.submit()` | **ĐANG SỐNG** | `platform_core/agent/executor.py:318` → `agent/runs.py:117` → `platform_core/jobs.py` |
| **Workflow V2 / Canvas** — `WorkflowRun` → `NodeRun` → job | **CHƯA NỐI** | `workflow/thi_hanh.py` tự khai *"chưa nối vào đường chạy nào"*; `workflow/dieu_phoi.py` đứng sau cờ `LTT_WORKFLOW_V2` **mặc định TẮT** |

⇒ **Macro Node của 4 App phải là một `ToolSpec` trong manifest**, tiêu thụ bởi
Agent executor. Đó là đường có thật, và nó thoả đúng bất biến #2 của
MASTER-GUARDRAILS (*cùng service, cùng job handler*).

⛔ Nếu chương trình nhắm Macro Node vào Canvas V2 thì nó đang xây trên một cạnh
đồ thị **chưa tồn tại**, và việc đó lớn hơn nhiều lần một *"minimal generic gap
fix"* — tức một điều kiện DỪNG theo START-HERE §8.

**`READY_FOR_APP_MIGRATION: YES`** — cho nửa App (GUI · job · worker · credit ·
artifact) và cho Macro Node **qua Agent**.
**`READY_FOR_CANVAS_NODE: NO`** — và nó không nằm trong MVP boundary của §7.

---

## Tám câu hỏi, trả lời bằng mã

### 1. App → ToolSpec → Job type → Worker handler

```
apps/<slug>/manifest.py   AppManifest(job_types=(...), requires=(...),
                                      credit_cost=<callable>, tools=(ToolSpec...))
   ↓ platform_core/registry.py:1194  discover()      quét apps/, xác thực bản khai
   ↓ registry.py:1316                job_type_owners()  job_type → app
   ↓ platform_core/job_submit.py     submit_with_credit()  giá + giữ chỗ + xếp hàng
                                     — MỘT giao dịch
   ↓ platform_core/jobs.py:286       claim()  `FOR UPDATE SKIP LOCKED` (dòng 334)
   ↓ apps/<slug>/jobs.py             handler chạy trong worker
```

`ToolSpec` (`registry.py:102`) là **metadata tất định**, không chứa handler:
`name` · `job_type` · `params_schema` · `returns` · `verifiable` ·
`customer_visible` · `api_exposed` + `api_contract` · `admission_resource` +
`admission_slots` · `sync_executor` · `tuy_chon_dong`.

### 2. WorkflowRun → NodeRun → job dispatch

**Không có cạnh này.** `server/api/workflows.py:214` `start_run()` làm đúng ba
việc rồi dừng: xác thực báo giá đã ký → `thi_hanh.tao_run()` → `tien.giu_cho_run()`.
Không lời gọi `enqueue`, không job nào được tạo.

Cạnh **đang sống** nằm ở Agent: `executor.py:318` gọi `runs.submit_child()`, và
hàm ấy tiêm `owner_id` **do máy chủ sở hữu** vào params trước khi `jobs.submit()`
(`agent/runs.py:115-121`).

### 3. Job xong → output → Workflow

`workflow/thi_hanh.py:ghi_chuyen()` — mô hình **C**: mỗi lần chuyển ghi **một**
hàng `NodeRunSnapshot` bất biến, rồi cập nhật con trỏ `NodeRun` **chỉ khi**
`is_valid`. Chi phí `O(node đổi)`, không phụ thuộc kích thước đồ thị.

⭐ Lần chuyển **bị từ chối** vẫn được ghi (`is_valid=False`) — thứ duy nhất trả
lời được *"ai đã thử gì"* sau một sự cố.

Phía Agent, kết quả job gom bằng `executor._aggregate()` đọc `Job.status`.

### 4. Credit settle ở đâu

`workflow/ket_so.py:ket_so()`, và điểm mấu chốt là **nó không có transaction
riêng**: `may_trang_thai.chuyen_run()` gọi thẳng vào nó, nên trạng thái kết thúc
và bút toán nằm **cùng một giao dịch**.

```
actual_cost = 0                      khi status ∈ RUN_LOI_CUA_TA   (lỗi của ta thì không thu)
            = tong_chi_phi_hop_le()  ngược lại — chỉ cộng ảnh chụp `is_valid`
QUYẾT TOÁN trước, rồi mới xoá `hold_id`
```

🔴 Lý do hình dạng ấy là một con số production: **145 dòng "GIU CHO TREO" trong
28 ngày log worker**, sinh ra bởi khoảng trống giữa *ghi trạng thái* và
*settle*, và worker restart **13,6 lần/ngày** nên khoảng trống ấy được thử 13,6
lần mỗi ngày.

TTL của run là **20 giờ**, cố ý **ngắn hơn** `credit.TU_HOAN_SAU` (24 giờ) —
nếu bằng nhau thì số tiền thu được phụ thuộc vòng quét nào chạy trước
(`dieu_phoi.py:TRAN_RUN`, chốt ở `test_965`).

### 5. ArtifactRef

`workflow/artifact.py` — id **tự mô tả backend**: `"<backend>:<key>"`,
`BACKEND = {"local", "r2"}`. Lý do kỹ thuật, không phải sở thích đặt tên: tham
chiếu đi vào `output_ref` (JSONB) của bước sau, và JSONB **không tra bảng được**.

`TTL_CLASS = {EPHEMERAL 6h · RUN 7d · PROJECT 90d · PERMANENT}`. Backend có vòng
đời riêng (R2) thì nền tảng **không tự xoá** (`_TU_XOA = {"local": True, "r2": False}`).

### 6. App mới khai group/nav/tool mà KHÔNG sửa platform

Chỉ bằng `AppManifest` (`registry.py:306`): `nav` · `job_types` · `requires` ·
`credit_cost` · `capabilities` · `surface` · `lifecycle` · `public` · `enabled`.
`registry.discover()` quét `apps/`, `mount_all()` mắc route.

⭐ Nền tảng **không suy** gì từ slug hay tên app — `test_60` chốt điều đó.

### 7. Visibility / public / lifecycle chặn ở đâu

`registry.visible_on_surface()` (dòng 1180), trên ba trục **độc lập**:

```
enabled   app chạy được thật chưa
public    có hiện trong catalog công khai (khách chưa đăng nhập)
surface   customer | admin | runtime
lifecycle APP_LIFECYCLES
```

Public API là **ba cổng độc lập**, cố ý: `api_exposed=True` **VÀ** `api_contract`
đủ **VÀ** operator bật trong `LTT_PUBLIC_API_TOOLS`. Quên một cái thì hậu quả là
*thiếu tính năng*, không phải *lộ năng lực nội bộ*.

### 8. Tool naming / version / resource / side-effect

- tên: `_TOOL_NAME_RE = ^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` (`registry.py:80`)
- side effect: `SIDE_EFFECT_VALUES = {none, external, irreversible}` (dòng 715)
- tài nguyên: `RESOURCE_KEYS = {class, vram_min_mb, slots, est_duration_s}` (dòng 720)
- admission: `admission_resource` + `admission_slots` trên từng `ToolSpec`

---

## R1 · R2 · R3

### R1 — ForEach atomic completion → **RACE THẬT · ĐÃ VÁ**

`foreach.ghi_ket_qua()` trước 2026-09-09 là **đọc · xét · ghi** trong Python:

```python
row = db.get(...)              # doc
if row is None or row.xong:    # xet
    return False
row.xong = True                # ghi
```

Ba câu, ba thời điểm, **không** khoá hàng và **không** cập nhật có điều kiện.
`ForeachMuc` (`models.py:1357`) không có cột phiên bản, không ràng buộc nào chặn
lần ghi thứ hai. Nên câu *"bản ghi đầu tiên thắng"* trong chính docstring của nó
là một lời hứa mã **không cưỡng chế được**; thứ xảy ra là *bản ghi cuối thắng*.

⚠️ Hậu quả nặng hơn "một giá trị bị đè": `so_luot_chay()` đếm hàng `xong=True`,
nên một phần tử chạy **hai** lần vẫn hiện là **một** lượt — ngưỡng `M7`
(*"0 lượt lặp"*) báo **đạt** trong khi tiền đã tiêu hai lần. Một phép đo che đúng
thứ nó sinh ra để đo.

**Bản vá tối thiểu** (`platform_core/workflow/foreach.py`): `UPDATE … WHERE
xong = false` + `rowcount`, cùng khuôn `jobs.claim()`. Kèm `db.expire_all()` —
thiếu nó, `chi_so_chua_xong()` gọi ngay sau đó đọc bản sao cũ trong bộ nhớ và
trả về một chỉ số **vừa ghi xong**.

**Chốt**: `tests/test_1101_foreach_gianh_nguyen_tu.py` (6 phép kiểm, có đối
chứng dựng lại bản cũ và chứng minh nó trượt).

⭐ Một ghi chú về *cách* đo, vì nó suýt cho âm tính giả: hai cách dựng lại cuộc
đua đầu tiên đều **thất bại** — hai `db.get()` trong một phiên trả **cùng một
đối tượng** (identity map), và hai `Session` riêng thì bản sao của phiên B vẫn
được làm mới trước khi tới cửa. Cả hai lần, **một lớp cache che mất khiếm
khuyết** — và đó cũng chính là lý do nó sống sót qua `test_959`, nơi phép kiểm
luỹ đẳng chạy trong một phiên.

### R2 — Workflow scheduler claim → **CHƯA CÓ, và mã tự khai điều đó**

`dieu_phoi.dequeue()` lọc ứng viên rồi trả danh sách. Chú thích trong chính hàm:

> *"Vẫn là **bộ lọc cơ hội, không phải khoá** … Lớp giành thật thuộc về Đợt sau
> (`FOR UPDATE SKIP LOCKED` trên PostgreSQL)."*

⇒ Đây **không** phải một phát hiện mới; nó là một món nợ đã ghi. Hai worker vẫn
có thể cùng thấy một run sẵn sàng.

**Không vá trong phase này**, và lý do là *phạm vi* chứ không phải *độ khó*:
đường ấy đứng sau cờ `LTT_WORKFLOW_V2` **mặc định TẮT** và không có ai gọi, nên
rủi ro hiện tại bằng **không**. Vá nó là xây tầng giành cho một scheduler chưa
chạy — lớn hơn hẳn một *minimal generic gap fix*.

⚠️ Nhưng nó là **điều kiện chặn** của bất kỳ phase nào định bật cờ đó.

### R3 — Vertical slice thật → **KHÔNG QUA ĐƯỢC bằng Canvas · QUA ĐƯỢC bằng Agent**

```
WorkflowVersion → WorkflowRun → ready Tool Node → Job → Worker → …
                              ↑
                     ĐỨT Ở ĐÂY (câu 2)
```

Đường Agent thì đủ mắt xích và có test: plan → step → ToolSpec → `jobs.submit`
→ `claim()` → handler → `Job.status` → `_aggregate()` → `actual_cost()`.

---

## Khoảng trống còn lại

| # | Khoảng trống | Nặng | Ai chặn ai |
|---|---|---|---|
| G1 | `WorkflowRun` không dispatch job | CAO | chặn Canvas Node, **không** chặn 4 App |
| G2 | `dequeue()` không có khoá giành | VỪA | chặn việc bật `LTT_WORKFLOW_V2` |
| G3 | `bao_gia`/`tien` chạy trên đường Canvas chưa sống | THẤP | ghi nhận |

## ⛔ Không phải khoảng trống của chương trình này

Hai bánh cóc đang đỏ trên trunk từ commit `3eae396d` (`mypy` +6 ·
`nuot loi lang le` 63>62, trong ba tệp `tools/do_*.py`). Đo đối chứng trên bản
export **sạch** của `05464239` cho kết quả y hệt ⇒ **đỏ có sẵn của trunk**, không
phải của chiến dịch này. Phiên tác giả đã kết thúc; chủ dự án đã chỉ đạo **không
động vào công việc của phiên khác**, nên ở đây chỉ ghi nhận.
