# Tài liệu xây dựng — app AI Agent LTT

> Đây là **bản thiết kế thi công**: xây cái gì, đặt ở đâu, hợp đồng từng phần,
> tiêu chí nghiệm thu từng bước. Đọc cùng [`01_DAC_TA_AGENT.md`](01_DAC_TA_AGENT.md)
> (hợp đồng kỹ thuật) và [`05_DOI_SOAT.md`](05_DOI_SOAT.md) (trạng thái công cụ).
>
> **Chưa viết code.** Tài liệu này để thẩm duyệt và để thi công theo.
> Thứ tự phase, trạng thái, PASS gate và rollback chỉ có một nguồn:
> [`02_LO_TRINH.md`](02_LO_TRINH.md). Bảng kỹ thuật trong file này không được dùng
> để đánh dấu tiến độ độc lập.

## 0. Không xây lại runtime đã có

App agent là lớp **điều phối** trên các primitive hiện hữu. Thi công phải nối vào:

- `registry.discover()` và `credit_for()` để tìm tool/giá;
- `job_submit`, `jobs`, `job_runner` để chạy bền, retry, heartbeat và reclaim;
- `credit` để giữ chỗ/quyết toán/hoàn;
- `api_pool`/`providers` để chọn model/key;
- `storage.url_for()`/`put_url()` và R2 cho artifact;
- `media` cho verifier kỹ thuật video;
- Jinja/HTMX, `_job_progress.html` và design system hiện có cho UI;
- `lint_app_contract.py` làm cổng kiểm tra cơ học.

Chỉ các phần thật sự mới được xây: ToolSpec metadata, Plan/validator, checkpoint
agent, executor cấp-plan và verifier. Nếu thiết kế mới một queue, ledger, storage,
API allocator, uploader hoặc media runner thứ hai thì thiết kế sai.

---

## 1. Sản phẩm cuối trông như thế nào

```
app.lttstudios.com/agent

┌──────────────────────────────────────────────────────────┐
│  Bạn muốn làm gì?                                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Tạo video nữ thần tượng K-pop 15 giây từ ảnh này   │  │
│  └────────────────────────────────────────────────────┘  │
│  [📎 Đính kèm ảnh]        Ngân sách tối đa: [200] 💎     │
│                                        [ Lập kế hoạch ]  │
└──────────────────────────────────────────────────────────┘
                            ↓  (agent.plan — 1 job, có tính phí)
┌──────────────────────────────────────────────────────────┐
│  KẾ HOẠCH ĐỀ XUẤT                        Tổng tối đa: 178 💎│
│                                                          │
│  1. Phân tích ảnh              image.analyze        2 💎  │
│  2. Viết prompt nhân vật       text.script          3 💎  │
│  3. Tạo 4 ảnh nhân vật ×4      image.generate      20 💎  │
│       ✓ kiểm: khuôn mặt khớp ảnh gốc · làm lại tối đa 2  │
│  4. Tạo video 15 giây          video.generate     153 💎  │
│       ✓ kiểm: đúng người, không lỗi tay · làm lại tối đa 1│
│                                                          │
│  Số dư: 420 💎         [ Sửa yêu cầu ]   [ ✓ Duyệt & chạy ]│
└──────────────────────────────────────────────────────────┘
                            ↓  (duyệt → giữ chỗ 178 → chạy)
┌──────────────────────────────────────────────────────────┐
│  ĐANG CHẠY                                    62%        │
│  ✅ 1. Phân tích ảnh                          2 💎        │
│  ✅ 2. Viết prompt                            3 💎        │
│  🔄 3. Tạo ảnh nhân vật    3/4 xong · 1 làm lại (mặt sai) │
│  ⏳ 4. Tạo video           chờ bước 3                     │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│  XONG · thật tiêu 141 💎 · hoàn lại 37 💎                 │
│  [video]  [4 ảnh]   [ Xem nhật ký quyết định ]           │
└──────────────────────────────────────────────────────────┘
```

**Bốn trạng thái nghiệp vụ:** nhập yêu cầu → soạn/duyệt kế hoạch trên Canvas →
theo dõi trực tiếp trên node → kết quả. Canvas là editor/visualizer của cùng Plan
JSON; không phải runtime thứ hai.

### Stack Canvas đã chốt (Q49, thay Q38)

- React + TypeScript + [`@xyflow/react`](https://reactflow.dev/learn) cho node editor.
- Vite build static bundle; tài liệu chính thức xác nhận `vite build` tạo `dist`
  để phục vụ tĩnh: [Vite production build](https://vite.dev/guide/build).
- React Flow hỗ trợ save/restore graph qua nodes/edges/viewport:
  [Save and Restore](https://reactflow.dev/examples/interaction/save-and-restore).
- Frontend E2E dùng Playwright, cũng là công cụ React Flow khuyến nghị:
  [Testing](https://reactflow.dev/learn/advanced-use/testing).
- Không Next.js, SSR hay Node service production. FastAPI phục vụ bundle đã build.
- Không dùng localStorage làm nguồn chân lý; PostgreSQL + API versioned mới là nguồn.

---

## 2. Cây file sẽ tạo

```
platform_core/agent/              ← HẠ TẦNG (cần duyệt sửa platform_core)
├── __init__.py
├── tools.py          discover_tools() — quét manifest, KHÔNG hardcode slug
├── planner.py        câu người → Plan JSON (gọi LLM qua api_pool)
├── validator.py      kiểm lược đồ/kiểu/chu trình/giá — TẤT ĐỊNH, không LLM
├── budget.py         báo giá, trần, cổng duyệt
├── executor.py       chạy Plan qua hàng đợi; verify/retry/fanout
└── verifier.py       vlm_judge · technical · face_identity

apps/agent/                       ← APP (mặt khách)
├── __init__.py
├── manifest.py       slug="agent", job_types=("agent.plan","agent.run"), tools=()
├── routes.py         4 màn ở mục 1
├── jobs.py           handler cho agent.plan và agent.run
└── templates/
    ├── agent.html          ô nhập yêu cầu
    ├── agent_plan.html     bảng kế hoạch + báo giá + nút Duyệt
    ├── agent_run.html      theo dõi tiến độ
    └── _agent_progress.html  mẩu HTMX poll

alembic/versions/<ts>_agent.py    ← migration: jobs +3 cột, bảng agent_runs
tests/test_8x_agent_*.py          ← test theo từng bước
```

**Không sửa:** `credit.py` · `db.py` · `billing.py` · `secretbox.py` · auth/CSRF/phân quyền.

---

## 3. Hợp đồng từng phần

### 3.1 `tools.py` — hộp công cụ

```
discover_tools() -> dict[str, ToolSpec]
```

- Quét `registry.discover()` → gom `manifest.tools` của mọi app **không lỗi**
- Bỏ app bị `app_access` ẩn với người dùng hiện tại
- **Không bao giờ** `import apps.<slug>` — chỉ đọc manifest, như `registry.py`
- Giải `{"source": "prompts/<nhóm>"}` → đọc `_labels.json` trong app đó
- Giải `{"depends_on": "model"}` → tra `providers.py` theo model đã chọn

**Nghiệm thu:** tool trùng `name` bị chặn · `job_type` không thuộc app bị chặn ·
`test_60::test_no_app_slug_is_hardcoded_in_the_platform` vẫn xanh.

### 3.2 `planner.py` — sinh kế hoạch

**Vào:** câu người dùng · ảnh đính kèm (đã phân tích) · trần ngân sách · hộp công cụ
**Ra:** Plan JSON (lược đồ ở `01_DAC_TA_AGENT.md` mục 4)

Prompt gửi LLM theo mẫu **M1 — làm phẳng thành văn bản có nhãn** (học từ PLENX):

```
[CÔNG CỤ CÓ SẴN]
image.thumbnail — Sinh ảnh thumbnail YouTube từ chủ đề...
  topic (string, bắt buộc) · aspect_ratio (enum: 16:9|9:16|1:1|4:3|3:4, mặc định 16:9)
  · count (int 1-4, mặc định 1) · model (model_ref: image)
  → trả về: image_keys (image[])
video.generate — Sinh video AI từ mô tả...
  ...

[NGÂN SÁCH]  tối đa 200 credit

[ĐẦU VÀO]    image: ảnh chân dung nữ, 1 người, 1080×1350, có mặt rõ

[YÊU CẦU]
Tạo video nữ thần tượng K-pop 15 giây từ ảnh này
```

**Ba quy tắc bắt buộc:**
1. LLM được phép trả **lược đồ PHẲNG**; `planner.py` chuẩn hoá (mẫu M2)
2. Có **đường lui bóc JSON từ văn bản** khi LLM không gọi tool đúng (mẫu M3)
3. Gọi LLM qua `api_pool.chon_key(category=APIKEY_CAT_CHAT, thu_tu_provider=[...])`
   — **không đọc biến môi trường**

**Nghiệm thu:** LLM trả rác → không sập, báo lỗi rõ · trả JSON trong ```` ```json ````
→ bóc được · gọi 2 lần cùng yêu cầu → kế hoạch hợp lệ cả 2 lần.

### 3.3 `validator.py` — chốt chặn, TẤT ĐỊNH

Bảy phép kiểm, **không dùng LLM**:

| # | Kiểm | Sai thì |
|---|---|---|
| 1 | mọi `tool` có trong hộp công cụ | từ chối |
| 2 | mọi tham số hợp `params_schema` (kiểu, khoảng, enum, `depends_on`) | từ chối |
| 3 | tham chiếu `$sN.field` trỏ tới bước có thật, field có trong `returns` | từ chối |
| 4 | kiểu vào/ra khớp (`video` không nối vào ô nhận `text`) | từ chối |
| 5 | đồ thị `after` **không có chu trình** | từ chối |
| 6 | mọi bước tra được giá qua `registry.credit_for()` | từ chối |
| 7 | tổng trần ≤ `budget_max_credit` **và** ≤ số dư người dùng | từ chối |

Sai → trả **thông báo lỗi có cấu trúc** cho planner sửa, tối đa **N = 2** lần.
Vẫn sai → **báo người dùng, không chạy, không tiêu tiền**.

**Nghiệm thu:** mỗi phép kiểm có một test với kế hoạch cố tình sai ·
kế hoạch có chu trình bị bắt · kế hoạch vượt số dư bị bắt trước khi giữ chỗ.

### 3.4 `budget.py` — tiền

```
uoc_tinh(plan) -> {tong_toi_da, theo_buoc[], gia_lap_ke_hoach}
```

```
chi_phi_toi_da = Σ ( gia_buoc_i × (1 + max_retry_i) ) + gia_lap_ke_hoach
```

- Giữ chỗ = `tong_toi_da` → `credit.giu_cho()` **cùng transaction** với tạo `agent_run`
- Quyết toán = chi phí thật → `credit.quyet_toan()` (tự ghi bút toán bù, hoàn dư)
- Hỏng hẳn → `credit.hoan()`

**Không sửa `credit.py`.**

**Nghiệm thu:** chưa duyệt = **0 bút toán** trong sổ · duyệt rồi huỷ giữa chừng →
hoàn đúng phần chưa dùng · chi phí thật **không bao giờ vượt** trần đã báo · gọi
quyết toán 2 lần chỉ ghi 1 (đã idempotent sẵn).

### 3.5 `executor.py` — chạy

Vòng cho mỗi bước theo thứ tự topo:

```
1. chờ mọi bước trong `after` xong
2. phân giải tham chiếu $sN.field từ result của bước trước
3. nộp job qua job_submit (KHÔNG giữ chỗ lại — đã giữ ở cấp plan)
4. có `verify`? → chấm
   ├─ đạt   → ghi kết quả, đi tiếp
   └─ trượt → theo `fault`:  partial→refine · structural→regenerate · policy→DỪNG
              còn lượt → chạy lại;  hết lượt → dừng nhánh, ghi lý do
5. `fanout: N` → tạo N job con (parent_id), chờ đủ, chọn theo verifier
```

**Nghiệm thu:** 4 job con song song, 1 con chết → cha xử lý đúng ·
`reclaim_orphans` vẫn nhặt được job con mồ côi · worker restart giữa chừng → plan
resume từ `agent_runs`, **không chạy lại bước đã xong**.

### 3.6 `verifier.py` — chấm

Mọi verifier trả cùng một hình dạng:

```json
{ "pass": false, "score": 0.42,
  "fault": "structural",     // partial | structural | policy
  "reason": "khuôn mặt không khớp người trong ảnh gốc" }
```

| Verifier | Cách | Chi phí | Khi nào làm |
|---|---|---|---|
| `technical` | kích thước/thời lượng/khung hình/ffprobe | ~0 | **làm trước** — rẻ nhất, bắt lỗi thô |
| `vlm_judge` | Gemini Vision + rubric, ép trả JSON | 1 lượt LLM | mặc định |
| `face_identity` | insightface embedding + cosine | CPU | kiểm kê Haar/OpenCV nội tại trước; chỉ port recognition còn thiếu |

**Thứ tự chạy: `technical` → `face_identity` → `vlm_judge`.** Rẻ trước, đắt sau;
trượt ở bước rẻ thì không tốn bước đắt.

**Nghiệm thu:** verifier trả rác → coi như `pass` (không chặn oan) nhưng **ghi cảnh
báo** · `policy` → dừng hẳn, **không làm lại** (nội dung bị chặn thì làm lại vẫn bị).

---

## 4. Lược đồ CSDL — thêm gì

### 4.1 `jobs` — thêm 3 cột (additive, có `server_default`)

| Cột | Kiểu | Việc |
|---|---|---|
| `parent_id` | `String(36)`, index, `""` | job cha (fan-out) |
| `plan_id` | `String(36)`, index, `""` | thuộc `agent_runs` nào |
| `step_id` | `String(32)`, `""` | bước nào trong kế hoạch |

### 4.2 Bảng `agent_runs` — mới

| Cột | Việc |
|---|---|
| `id`, `user_id`, `app_slug` | định danh |
| `goal` | câu người dùng gõ |
| `plan` (JSON) | kế hoạch đã validate |
| `status` | `planning · awaiting_approval · running · done · error · cancelled` |
| `budget_max`, `estimated`, `actual` | tiền |
| `approved_at`, `approved_by` | **dấu vết cổng duyệt** |
| `decision_log` (JSON) | mỗi bước: tool, model, `api_key_id`, điểm chấm, số lần làm lại, credit |
| `created_at`, `finished_at` | |

`decision_log` là thứ trả lời câu **"vì sao job này tốn 141 credit"**. Không có nó
thì mọi khiếu nại của khách đều không tra được.

---

## 5. Ánh xạ hạng mục kỹ thuật sang phase thi công

| Hạng mục | Phase sở hữu | Xong khi kỹ thuật |
|---|---|---|---|
| ToolSpec core | P1 | validation metadata đầy đủ, app cũ tương thích |
| ToolSpec các app | P2 | 7 app job-based có schema/returns/cost khớp handler |
| Migration + checkpoint/fan-out | P3 | child concurrency, orphan và state machine đúng |
| Planner + validator | P4 | Plan rác/sai bị từ chối trước tiền/job |
| Budget + approval | P5 | chưa duyệt không hold; approve idempotent |
| Executor | P6 | DAG/fan-out/resume không chạy lại bước done |
| Verifier | P7 | retry hữu hạn và không vượt trần |
| UI bốn màn | P8 | browser E2E đầy đủ |
| Hardening/production | P9 | load/failure/backup/rollback và canary PASS |

Lệnh, bằng chứng và điều kiện qua phase theo `02_LO_TRINH.md`; không duy trì một
bảng tiến độ thứ hai trong file đặc tả này.

---

## 6. Sáu ràng buộc không được vi phạm khi thi công

1. **Agent không lặp. Executor lặp**, trong giới hạn `max_retry` khai trong plan.
2. **Không tiêu một đồng trước khi duyệt.** `approved_at` là điều kiện để `giu_cho`.
3. **Không hardcode slug app** trong `platform_core/agent/`. Test chốt đã có.
4. **Không chạy việc dài trong request.** `agent.plan` cũng là một job.
5. **Không sửa `credit.py`.** Thiếu gì thì bàn lại thiết kế, đừng nới sổ tiền.
6. **Migration additive, có `server_default`.** App cũ phải chạy nguyên sau migration.

---

## 7. Rủi ro thi công

| Rủi ro | Chặn bằng |
|---|---|
| Agent đốt credit | trần trong plan · validator từ chối vượt trần **và** vượt số dư · cổng duyệt · giữ chỗ = trần |
| LLM sinh plan sai lược đồ | validator tất định + cho sửa tối đa 2 lần + đường lui bóc JSON |
| Verifier chấm sai → làm lại vô ích | `max_retry` 1–2 · chạy verifier rẻ trước · ghi điểm vào `decision_log` để chỉnh rubric |
| Fan-out làm nghẽn worker | giới hạn số job con đồng thời mỗi plan (mặc định 4) |
| Kế hoạch vượt 100 giây | mọi bước đã là job nền — kiến trúc đúng sẵn |
| Video vượt 100 MB | dùng R2 + `url_for`/`put_url` đã có; không stream qua web |
| Khách khiếu nại "sao tốn nhiều" | `decision_log` + màn nhật ký quyết định |

---

## 8. Phần cố ý KHÔNG làm ở v1

| Không làm | Xem lại khi nào |
|---|---|
| Canvas tách thành runtime/executor riêng | không bao giờ; Canvas chỉ sửa/hiện Plan |
| Auto mode (chạy không cần duyệt) | khi cổng duyệt đã ổn định và khách xin |
| RAG trên kho mẫu kế hoạch (PLENX có) | sau ≥ 20 kế hoạch thật để làm kho |
| Nhiều agent phối hợp | chưa có việc cho một agent làm hết |
| Agent sửa kế hoạch giữa chừng | phá khả năng báo giá — có lẽ không bao giờ |
