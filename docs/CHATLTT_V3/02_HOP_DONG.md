# P02 · HỢP ĐỒNG — máy trạng thái · lược đồ · sự kiện · chính sách

*H44 · 2026-09-05 · đi kèm `02_ADR_ORCHESTRATION.md`.*

---

## §1 — MÁY TRẠNG THÁI của một `run`

```
                    ┌──────────────────────────────────────────┐
                    ▼                                          │
  CREATED ──▶ MODEL_RUNNING ──▶ TOOL_REQUESTED ──▶ AWAITING_APPROVAL
     │              │  │              │                  │  │
     │              │  │              ▼                  │  │
     │              │  │        TOOL_RUNNING ◀───────────┘  │
     │              │  │           │      │                 │
     │              │  │           │      ▼                 ▼
     │              │  │           │  WAITING_BACKGROUND  (tu choi)
     │              │  │           │      │                 │
     │              │  │           ▼      ▼                 │
     │              │  │      TOOL_RESULT_READY ◀───────────┘
     │              │  │              │
     │              │  └──────────────┤ (het tool, model tra loi cuoi)
     │              │                 ▼
     │              │          MODEL_RESUMING ──┐
     │              │                           │ (vong ke tiep)
     │              └───────────────────────────┘
     │              ▲
     │        WAITING_SLOT  ◀── mat suat `llm_remote` (R1)
     ▼
  COMPLETED / FAILED / CANCELLED
```

### Bảng chuyển đổi HỢP LỆ — mọi cái khác là lỗi lập trình, **ném**

| Từ | Tới | Kích hoạt |
|---|---|---|
| `CREATED` | `MODEL_RUNNING` | giành được suất |
| `CREATED` | `WAITING_SLOT` | mất suất ngay từ đầu |
| `MODEL_RUNNING` | `TOOL_REQUESTED` | gộp xong ≥ 1 `tool_call.delta` |
| `MODEL_RUNNING` | `COMPLETED` | `finish_reason` ≠ `tool_calls` |
| `MODEL_RUNNING` | `FAILED` / `CANCELLED` | lỗi / người dùng Dừng |
| `TOOL_REQUESTED` | `AWAITING_APPROVAL` | `policy_class` đòi duyệt |
| `TOOL_REQUESTED` | `TOOL_RUNNING` | `READ_ONLY`/`FREE`, hoặc chính sách tự-chạy |
| `TOOL_REQUESTED` | `TOOL_RESULT_READY` | validate hỏng ⇒ **lỗi có cấu trúc trả về model**, không giết run |
| `AWAITING_APPROVAL` | `TOOL_RUNNING` | duyệt |
| `AWAITING_APPROVAL` | `TOOL_RESULT_READY` | **từ chối** ⇒ kết quả `{"tu_choi": …}` trả về model |
| `AWAITING_APPROVAL` | `CANCELLED` | hết hạn / người dùng huỷ run |
| `TOOL_RUNNING` | `WAITING_BACKGROUND` | tool đi qua `job_runner` |
| `TOOL_RUNNING` / `WAITING_BACKGROUND` | `TOOL_RESULT_READY` | có kết quả (kể cả lỗi) |
| `TOOL_RESULT_READY` | `MODEL_RESUMING` | còn vòng (dưới trần) |
| `TOOL_RESULT_READY` | `COMPLETED` | chạm trần vòng/tool/credit |
| `MODEL_RESUMING` | `MODEL_RUNNING` | giành lại được suất |
| `MODEL_RESUMING` | `WAITING_SLOT` | mất suất (R1) |
| `WAITING_SLOT` | `MODEL_RUNNING` | giành lại được |
| `WAITING_SLOT` | `FAILED` | quá trần chờ |

⭐ **`AWAITING_APPROVAL` → `TOOL_RESULT_READY` khi TỪ CHỐI** là chuyển đổi dễ bỏ
sót nhất, và bỏ nó là hỏng sản phẩm: người dùng bấm "không" thì model phải
**biết** nó bị từ chối để nói lại cho người dùng, chứ không phải run chết im.
P01 N8 đã đo: model xử lý *"TỪ CHỐI: vi phạm chính sách"* đúng cách.

⛔ `TOOL_REQUESTED` → `TOOL_RESULT_READY` khi **validate hỏng** cũng vậy: đối số
sai schema là **dữ liệu để model sửa**, không phải lý do giết lượt. P01 đã đo
schema hợp lệ 100 %, nhưng ở dạng tải thật (tool nhiều tham số) con số đó sẽ
tụt, và đường này là thứ đỡ.

---

## §2 — LƯỢC ĐỒ: ba bảng mới, **không sửa bảng cũ**

### `chatltt_run` — một LƯỢT của người dùng

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | `String(40)` `run_…` | |
| `conversation_id`, `user_id` | `String(40)`, `String(36)` | ⛔ `String(36)` — bài học `ltt_voice/tables.py:66-75` |
| `message_id` | `String(40)` | message assistant mà run này gắn vào |
| `trang_thai` | `String(24)` | một trong 10 trạng thái §1 |
| `so_vong_model`, `so_loi_goi_tool` | `Integer` | cưỡng chế trần §4 |
| `credit_giu_tong`, `credit_thu_tong`, `credit_hoan_tong` | `Integer` | **dẫn xuất**, cộng từ `execution` con |
| `ly_do_ket` | `String(40)` | `xong` · `tran_vong` · `tran_credit` · `huy` · `loi` |
| `lease_id` | `String(40)` | rỗng khi không giữ (mặc định — R1 chọn C) |
| `created_at`, `updated_at`, `finished_at` | | |

### `chatltt_step` — một BƯỚC trong run

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | `String(40)` `st_…` | |
| `run_id`, `user_id` | | mọi truy vấn có `user_id` — IDOR chặn ở service |
| `thu_tu` | `Integer` | duy nhất trong run |
| `loai` | `String(16)` | `model` \| `tool` |
| `execution_id` | `String(40)` \| NULL | trỏ `chatltt_execution` khi `loai='model'` |
| `tool_name`, `tool_call_id` | `String(64)`, `String(64)` | |
| `doi_so` | `JSON` | đối số **đã gộp và đã validate** |
| `doi_so_tho` | `Text` | chuỗi trước khi gộp — để chẩn đoán mảnh cắt |
| `ket_qua` | `JSON` | kết quả **có cấu trúc**; lỗi cũng là kết quả |
| `job_id` | `String(36)` \| NULL | khi tool đi qua `job_runner` |
| `trang_thai` | `String(16)` | |
| `bam_trung` | `String(64)` | `sha256(tool_name + đối số chuẩn hoá)` — chặn trùng |

⭐ `doi_so_tho` có mặt vì `test_800` đã chứng minh runtime **không gộp mảnh**.
Ngày nào đó gộp sai, thứ cần đọc là chuỗi trước khi gộp — và lúc đó nó phải đã
được lưu, không thể dựng lại.

### `chatltt_approval` — một QUYẾT ĐỊNH duyệt

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | `String(40)` `ap_…` | |
| `step_id` | `String(40)` | 🔴 **UNIQUE** |
| `run_id`, `user_id` | | |
| `tool_name`, `doi_so` | | thứ người dùng **nhìn thấy** khi bấm |
| `policy_class` | `String(16)` | §3 |
| `bao_gia_credit`, `phien_ban_gia` | `Integer`, `String(32)` | số đã hiện ra |
| `quyet_dinh` | `String(16)` | `cho` · `duyet` · `tu_choi` · `het_han` |
| `doi_so_da_sua` | `JSON` \| NULL | khi người dùng sửa đối số |
| `quyet_boi`, `quyet_luc` | `String(36)`, datetime | |
| `idempotency_key` | `String(64)` | **UNIQUE** |

🔴 **`UNIQUE(step_id)` là thứ làm cho "duyệt hai lần" KHÔNG THỂ xảy ra** — ở
tầng CSDL, không phải ở một `if` trong route. Route có thể quên; ràng buộc
không quên. Cùng lý do `job_submit` dùng `dedupe_key`.

### Sửa bảng cũ: đúng hai cột, đều `nullable`

```
chatltt_execution + run_id  String(40) NULL
                  + step_id String(40) NULL
```

⛔ Không đổi ngữ nghĩa cột nào đang có. `chatltt_execution` **vẫn là** một lần
gọi model/job, và ba cột tiền vô hướng của nó **vẫn đúng** cho việc đó.
`chatltt_message.blocks` **không đổi hình dạng** — khối mới là phần tử mới.

---

## §3 — CHÍNH SÁCH: năm lớp, hai lớp cuối rỗng mà vẫn phải có

| Lớp | Ai thuộc (V3 làn A) | Xử lý mặc định |
|---|---|---|
| `READ_ONLY` | `calculator`, tìm trong hội thoại của chính mình | tự chạy |
| `FREE` | đọc dữ liệu nền tảng của chính người dùng | tự chạy, ghi log |
| `PAID` | `image.ltt`, `speech.ltt` | báo giá → duyệt, **hoặc** tự chạy dưới ngưỡng người dùng đặt |
| `EXTERNAL_WRITE` | — (rỗng) | **luôn hỏi** |
| `DESTRUCTIVE` | — (rỗng) | **luôn hỏi** + gõ xác nhận |

⭐ Hai lớp cuối rỗng mà vẫn tồn tại vì: ngày đầu tiên có một tool ghi ra ngoài,
chỗ để nó rơi vào phải **đã có sẵn và đã fail-closed**. Thêm một lớp lúc đang
vội là lúc người ta chọn `PAID` cho một thứ đáng lẽ `DESTRUCTIVE`.

**Suy lớp thế nào:** từ `ToolSpec` + `chinh_sach`, **không** từ tên tool.
Cùng lý do `luot.doc_anh_duoc()` đọc `constraints.reads_images` chứ không tìm
chữ `"vision"` trong tên: tên là quy ước, hợp đồng là lời hứa.

**Chính sách người dùng** (`PAID` mới có): *luôn hỏi* · *tự chạy dưới X credit* ·
*không bao giờ*. Cưỡng chế **phía máy chủ**; giao diện chỉ hiển thị.

---

## §4 — TRẦN, và vì sao mỗi cái có một con số

| Trần | Giá trị | Vì sao đúng con số đó |
|---|---|---|
| Vòng model / lượt | **8** | P01 đo chuỗi 2 bước 100 %; 8 cho chỗ thở mà vẫn chặn vòng lặp. Với C1 thì 8 vòng = **8 credit sàn** (§R2b) — cao hơn nữa là đắt mà không thêm giá trị |
| Lời gọi tool / lượt | **12** | > 8 vì một vòng có thể gọi song song (P01 đo 2 lời gọi/vòng) |
| Credit tích luỹ / lượt | chờ §6 ADR | phụ thuộc quyết định làm tròn |
| Trùng: `bam_trung` lặp | **2** lần thì chặn | P01 đo lặp 0 %, nhưng rào là lưới đỡ chứ không phải chất lượng |
| Giữ lease (nếu nâng A) | **≤ 5 phút** | dưới xa `ORPHAN_TIMEOUT` 20 phút |

⛔ Chạm trần là **`COMPLETED` kèm `ly_do_ket`**, không phải `FAILED`. Người dùng
phải nhận được thứ model đã làm được, kèm câu nói rõ nó dừng vì trần.

---

## §5 — SỰ KIỆN: nối thêm, không đổi cơ chế

`su_kien.LOAI` fail-closed (ném với loại lạ), nên mọi loại mới **phải** khai:

```
run.started {run_id, so_vong_toi_da}
run.completed {ly_do_ket, so_vong, so_loi_goi_tool, credit_tong}
run.failed {code, ly_do}

tool.requested {step_id, tool_name, doi_so, policy_class}
tool.validated {step_id}
tool.rejected  {step_id, ly_do}          <- validate hong, KHONG giet run
tool.started   {step_id}
tool.progress  {step_id, progress}
tool.result    {step_id, tom_tat}        <- KHONG day nguyen ket qua vao SSE
tool.failed    {step_id, code, ly_do}

approval.required {approval_id, tool_name, doi_so, credit, policy_class}
approval.granted  {approval_id, doi_so_da_sua?}
approval.denied   {approval_id}
approval.expired  {approval_id}

task.queued / task.running / task.completed / task.failed   {job_id}
```

⛔ `tool.result` chỉ mang **tóm tắt**. Kết quả đầy đủ nằm ở `chatltt_step.ket_qua`
và lấy qua `su_that()`. Đẩy một kết quả tìm kiếm 200 KB qua SSE là biến cửa xem
thành cửa truyền dữ liệu — cùng lỗi mà ADR-0008 của Nexus cảnh báo cho control plane.

⭐ Sự kiện đã có (`response.*`, `execution.*`, `usage.*`, `billing.*`,
`artifact.*`) **giữ nguyên nghĩa**. `tool_call.delta` vẫn phát như cũ; thứ đổi
là ChatLTT **giữ** nó lại thay vì `pass` — và `test_800` mục 7 sẽ đỏ đúng lúc đó.

---

## §6 — Điều kiện để hợp đồng này đúng

| Điều kiện | Kiểm bằng | Pha |
|---|---|---|
| Bộ hiển thị bỏ qua khối lạ | test (A5) | P03 |
| `UNIQUE(step_id)` thật sự chặn duyệt hai lần | **test đột biến**: bỏ ràng buộc ⇒ test phải ĐỎ | P04 |
| Trần vòng cưỡng chế được ở máy chủ | test | P03 |
| Chạm trần ⇒ `COMPLETED` chứ không `FAILED` | test | P03 |
| Từ chối duyệt ⇒ model **biết** | test | P04 |
| `run` tổng hợp tiền khớp `credit_entries` | test đối soát | P04 |
