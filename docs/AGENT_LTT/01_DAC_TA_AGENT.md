# Đặc tả kỹ thuật — AI Agent LTT

> **Đây là HỢP ĐỒNG.** Nó ít thay đổi. Nếu phải đổi thì đổi có chủ đích, ghi lý do
> vào `../QUYET_DINH_NEN_TANG.md`, không sửa lặng lẽ.
>
> Cơ sở: `../PHUONG_AN_AGENT.md` (chấm điểm → PA-1+) và `../KHAO_SAT_PLENX_AGENT.md`
> (bằng chứng đo từ PLENX thật).

---

## 1. Định nghĩa một câu

> Agent nhận **một yêu cầu tiếng Việt**, sinh **một kế hoạch nhiều bước có lược đồ**,
> báo giá, chờ người duyệt, rồi giao cho **executor tất định** chạy qua hàng đợi job
> có sẵn — trong đó mỗi bước **tự kiểm tra kết quả và làm lại nếu sai**, trong giới
> hạn đã khai trước.

---

## 2. Nguyên tắc nền — bốn điều không được vi phạm

### NT1 — Agent lập kế hoạch. Agent KHÔNG lặp. Executor mới lặp.

Vòng kiểm-tra-làm-lại nằm ở **executor** (code tất định), không nằm ở LLM. Mỗi bước
tự khai `verify` + `on_fail` + `max_retry`; executor chạy vòng đó trong đúng giới hạn.

**Vì sao:** một agent tự do quyết định từng bước thì **không tính được tổng chi phí
trước khi chạy** → không báo giá được → không duyệt được → **phá bất biến** *"job
không tra được giá thì bị từ chối chạy"* (`QUYET_DINH_NEN_TANG.md` mục 2.4).

### NT2 — Không tiêu một đồng nào trước khi người duyệt.

Kế hoạch → báo giá → **cổng duyệt** → mới giữ chỗ credit → mới chạy.
FLORA làm đúng thế (*Assist mode*, mặc định). **PLENX KHÔNG có cổng này** — đó là
điểm ta cố ý làm khác.

### NT3 — Chi phí luôn có trần tính được trước.

```
chi_phi_toi_da = Σ ( gia_buoc_i × (1 + max_retry_i) ) + gia_lap_ke_hoach
```

- Giữ chỗ = `chi_phi_toi_da` → `credit.giu_cho()`
- Quyết toán = chi phí thật → `credit.quyet_toan()` tự ghi bút toán bù, **hoàn phần dư**
- Job hỏng hẳn → `credit.hoan()`

**Ba hàm này đã tồn tại, đã có test, KHÔNG sửa một dòng nào.**

### NT4 — Nền tảng không biết tên app nào tồn tại.

Tool registry quét `apps/*/manifest.py` y hệt `registry.discover()`. Agent **không
bao giờ** `import apps.<slug>...`. Test chốt: `test_60::test_no_app_slug_is_hardcoded_in_the_platform`.

---

## 3. ToolSpec — hợp đồng công cụ

Mỗi app khai **năng lực** của mình. Đây là thứ agent đọc để biết làm được gì.

```python
# apps/<slug>/manifest.py
from platform_core.registry import AppManifest, ToolSpec

MANIFEST = AppManifest(
    slug="thumbnail",
    ...
    job_types=("thumbnail.generate",),
    credit_cost=_cost,

    tools=(
        ToolSpec(
            name="image.thumbnail",          # DUY NHẤT toàn hệ thống, dạng <miền>.<hành động>
            job_type="thumbnail.generate",   # nối tới hàng đợi có sẵn
            description="Sinh ảnh thumbnail YouTube từ chủ đề + tiêu đề.",
            params_schema={
                "topic":        {"type": "string", "required": True,
                                 "desc": "chủ đề/mô tả nội dung"},
                "title":        {"type": "string", "required": False},
                "aspect_ratio": {"type": "enum", "values": ["16:9","1:1","9:16","4:3"],
                                 "default": "16:9"},
                "count":        {"type": "int", "min": 1, "max": 4, "default": 1},
                "model":        {"type": "model_ref", "category": "image"},
            },
            returns={"image_keys": "image[]", "prompt": "text"},
            verifiable=("face_identity", "vlm_judge"),   # verifier dùng được với output này
        ),
    ),
)
```

### Vì sao từng trường

| Trường | Vì sao bắt buộc |
|---|---|
| `name` | agent gọi theo tên này; `<miền>.<hành động>` để LLM đoán đúng |
| `job_type` | nối vào hàng đợi có sẵn — **không tạo cơ chế chạy thứ hai** |
| `description` | LLM chọn tool dựa vào đây; viết cho máy đọc, không phải cho người |
| `params_schema` | **quan trọng nhất** — không có nó thì LLM đoán bừa tham số. PLENX gọi là `config{}` của model; BOT GEMINI có sẵn ở `image_model_registry.py` (`supported_aspects`, `max_count`) |
| `returns` | để validator kiểm **kiểu vào/ra khớp nhau** giữa hai bước |
| `verifiable` | verifier nào áp được lên output này |

### Kiểu dữ liệu cổng

```
text · image · image[] · video · video[] · audio · json · model_ref
```

Validator dùng bộ này để **từ chối nối output `video` vào input chỉ nhận `text`**.

---

## 4. Plan JSON — sản phẩm của agent

### 4.1 Lược đồ

```json
{
  "version": 1,
  "goal": "video nữ thần tượng K-pop 15 giây từ ảnh này",
  "budget_max_credit": 320,
  "steps": [
    { "id": "s1", "tool": "image.analyze",
      "params": { "image_ref": "$input.image" } },

    { "id": "s2", "tool": "image.remove_bg",
      "params": { "image_ref": "$s1.image" },
      "after": ["s1"] },

    { "id": "s3", "tool": "image.generate",
      "params": { "prompt": "...", "count": 4, "aspect_ratio": "9:16" },
      "after": ["s2"],
      "fanout": 4,
      "verify":  { "check": "face_identity", "against": "$input.image", "min_score": 0.75 },
      "on_fail": "regenerate",
      "max_retry": 2 },

    { "id": "s4", "tool": "video.generate",
      "params": { "image_ref": "$s3.best", "duration_s": 15 },
      "after": ["s3"],
      "verify":  { "check": "vlm_judge",
                   "rubric": "đúng người trong ảnh gốc, không lỗi tay/mặt" },
      "on_fail": "retry_same",
      "max_retry": 1 }
  ]
}
```

### 4.2 Bốn cơ chế

| Cơ chế | Việc |
|---|---|
| `$s1.image`, `$input.image`, `$s3.best` | tham chiếu đầu ra bước trước. **Executor phân giải**, LLM chỉ viết tên |
| `verify` + `on_fail` + `max_retry` | **hợp đồng tự sửa** — khai trong *dữ liệu*, không nằm trong đầu LLM. Nhờ vậy tính được trần |
| `fanout: N` | sinh N nhánh song song (= nút **▶ trên Frame** của PLENX) |
| `budget_max_credit` | trần cứng; validator **từ chối** kế hoạch vượt trần |

### 4.3 `on_fail` — bốn nhánh

| Giá trị | Nghĩa | Dùng khi |
|---|---|---|
| `retry_same` | chạy lại cùng tham số, đổi seed | lỗi ngẫu nhiên |
| `refine` | sửa **cục bộ** trên kết quả cũ | **sai một phần** |
| `regenerate` | vứt, làm lại từ đầu | **sai cấu trúc** |
| `switch_model` | đổi sang model khác cùng năng lực | model này liên tục hỏng |

Quy tắc chọn nhánh lấy từ *Generation Navigator*: **sai một phần → sửa cục bộ; sai
cấu trúc → vứt, làm lại.** Verifier trả về *loại* lỗi để executor chọn nhánh, không
chỉ trả điểm.

---

## 5. Luồng đầy đủ

```
 Người dùng gõ một câu  (+ tuỳ chọn: ảnh đính kèm)
      │
      ▼
 ① PLANNER   — 1 lượt LLM, TÍNH PHÍ như một job (job_type `agent.plan`)
      │   ngữ cảnh nạp vào prompt:
      │     • danh mục ToolSpec (tên + mô tả + params_schema)
      │     • model khả dụng + schema tham số của chúng
      │     • kết quả phân tích ảnh đầu vào (nếu có)
      │     • trần ngân sách người dùng đặt
      │   ra: Plan JSON
      ▼
 ② VALIDATOR — code tất định, KHÔNG phải LLM
      │   • tool có thật?      • tham số hợp params_schema?
      │   • kiểu vào/ra khớp?  • đồ thị không có chu trình?
      │   • mọi bước tra được giá?   • tổng ≤ budget_max_credit?
      │   sai → trả lỗi cho planner sửa (tối đa N lần) → vẫn sai thì BÁO NGƯỜI, không chạy
      ▼
 ③ BÁO GIÁ + CỔNG DUYỆT
      │   hiện: từng bước · model · giá mỗi bước · số lần làm lại tối đa · TỔNG TỐI ĐA
      │   người bấm Duyệt   ← chưa duyệt thì CHƯA TIÊU ĐỒNG NÀO
      ▼
 ④ GIỮ CHỖ credit = tổng tối đa   (credit.giu_cho, cùng transaction với tạo job)
      ▼
 ⑤ EXECUTOR — worker hiện có
      │   theo thứ tự topo, mỗi bước:
      │     chạy tool → có `verify`? → chấm → đạt: đi tiếp
      │                                    → trượt: theo `on_fail`, tối đa `max_retry`
      │                                    → hết lượt: dừng nhánh, ghi lý do vào nhật ký
      ▼
 ⑥ QUYẾT TOÁN theo chi phí thật → tự hoàn phần dư
      ▼
 ⑦ Trả kết quả + NHẬT KÝ QUYẾT ĐỊNH
      (mỗi bước: làm gì, model nào, khoá nào, chấm bao nhiêu, vì sao làm lại, tốn bao nhiêu)
```

---

## 6. Verifier

| Kiểu | Cách làm | Chi phí | Trạng thái tài nguyên |
|---|---|---|---|
| **`vlm_judge`** | gửi ảnh + ảnh gốc + rubric cho Gemini Vision, **bắt trả JSON có điểm + loại lỗi** | 1 lượt LLM | ✅ đã có key qua `api_pool` |
| **`face_identity`** | embedding khuôn mặt → cosine similarity → ngưỡng | CPU cục bộ | ⚠ **`D:\BOT GEMINI\app\modules\seedance_video\face_detect.py`** đã giải xong phần khó: insightface `buffalo_sc`, singleton thread-safe, fallback Haar, ngưỡng hiệu chỉnh từ ảnh thật. Hiện chỉ `detection` — thêm `"recognition"` là có identity |
| `technical` | ffprobe/kích thước/thời lượng/khung hình | ~0 | dùng cho video |

**Mặc định `vlm_judge`.** `face_identity` là nâng cấp — **không đổi Plan JSON**, chỉ
thêm một giá trị cho trường `check`.

### Verifier phải trả về gì

```json
{ "pass": false, "score": 0.42,
  "fault": "structural",              // "partial" | "structural" | "policy"
  "reason": "khuôn mặt không khớp người trong ảnh gốc" }
```

`fault` quyết định nhánh `on_fail`: `partial` → `refine`; `structural` → `regenerate`;
`policy` → **dừng hẳn, không làm lại** (nội dung bị chặn thì làm lại cũng bị chặn).

---

## 7. Bảy thay đổi nền tảng cần thiết (N1–N7)

Tất cả **additive**; migration có `server_default`; app cũ chạy nguyên.

| # | Sửa gì | Vì sao không đi vòng được |
|---|---|---|
| N1 | `AppManifest` thêm `tools=(ToolSpec…)` | agent phải biết làm được gì; import thẳng app là phá chiều phụ thuộc (test_60 chặn) |
| N2 | `ToolSpec` + kiểu cổng | không có `params_schema` thì LLM đoán bừa tham số |
| N3 | `jobs` thêm `parent_id`, `plan_id`, `step_id` | fan-out + "chờ N job con xong"; `claim()` hiện lấy đúng 1 job |
| N4 | Bảng `agent_runs` (plan, trạng thái, ngân sách, nhật ký quyết định) | resume sau khi worker chết + kiểm toán vì sao tốn tiền |
| N5 | mở rộng schema model trong `providers.py` | kiểm kê `providers.py` + registry app (`taovideo/models.py`) trước; chỉ lấy schema nghiệp vụ còn thiếu từ nguồn ngoài |
| N6 | ghi `api_key_id` vào `job.result` | truy vết khoá nào tạo ra sản phẩm nào (PLENX đã làm) |
| N7 | job type `agent.plan` để tính tiền lượt suy luận | PLENX thu **4 credit/lượt**, gấp đôi một lần sinh ảnh. Không tính là lỗ ngầm |

**KHÔNG sửa:** `credit.py`, `db.py`, `billing.py`, `secretbox.py`, phiên/CSRF/phân quyền.
**Theo Q38:** Jinja/HTMX giữ cho phần server-rendered; Canvas dùng React/TypeScript
+ React Flow, build Vite thành static assets. **Không đổi Q26** (hàng đợi Postgres)
và không đưa logic validation/giá/credit/execution xuống trình duyệt.

---

## 8. Bố cục mã nguồn

```
platform_core/agent/          ← HẠ TẦNG, không biết tên app nào
    tools.py       gom ToolSpec từ mọi manifest (quét như registry.discover)
    planner.py     câu người → Plan JSON  (gọi LLM qua api_pool)
    validator.py   kiểm lược đồ/kiểu/chu trình/giá — TẤT ĐỊNH, không LLM
    executor.py    chạy Plan qua hàng đợi; xử lý verify / retry / fanout
    verifier.py    vlm_judge · technical · (sau) face_identity
    budget.py      trần, báo giá, cổng duyệt

apps/<slug>/                  ← APP, mặt khách, một mục đích
    manifest.py    khai tools=(ToolSpec…) + credit_cost
    routes.py      ô nhập yêu cầu · trang duyệt kế hoạch · gallery kết quả
    jobs.py        handler của chính các tool nó khai
```

---

## 9. Ba mẫu thiết kế bắt buộc — học từ PLENX (đo thật)

### M1 — Làm phẳng ngữ cảnh thành văn bản có nhãn

Không gửi JSON đồ thị cho LLM. PLENX gửi:

```
[WORKFLOW CONTEXT]
Workflow "..." có 2 nodes:
- node-a (text): model=default, prompt=""
- node-b (image): model=default, prompt=""
Connections:
  node-a → node-b

[USER REQUEST]
<câu của người dùng>
```

Rẻ về token, dễ soi log, không cần schema phía LLM.

### M2 — LLM sinh lược đồ PHẲNG, máy chủ chuẩn hoá

PLENX cho LLM trả `{id, type, title, x, y, prompt}` (thứ tự khoá lộn xộn tuỳ ý), rồi
**máy chủ** đổi sang `{id, type, title, position:{x,y}, config:{prompt}}`.

→ **Đừng bắt LLM sinh đúng lược đồ lưu trữ.** Cho nó viết dạng dễ nhất, ta chuẩn hoá.

### M3 — Luôn có đường lui bóc JSON từ văn bản

Front-end PLENX có nhánh: hết stream mà **chưa nhận `action_card`** thì tự tìm JSON
trong phần văn bản — thử ```` ```json ````, rồi tìm khoá đặc trưng, **đếm ngoặc để
cắt đúng khối**, `JSON.parse`, áp dụng.

→ **Không tin LLM luôn gọi tool đúng cách.** Ta cũng phải có đường lui này.

---

## 10. Điều CỐ Ý không làm ở phiên bản đầu

| Không làm | Vì sao | Xem lại khi nào |
|---|---|---|
| Canvas runtime thứ hai trong browser | Q38 chỉ cho Canvas làm editor/visualizer; executor vẫn ở server | không bao giờ |
| Agent tự do vòng lặp | phá bất biến báo giá | có lẽ không bao giờ |
| Nhiều agent phối hợp | chưa có việc cho một agent làm hết | sau |
| Agent tự chạy không cần duyệt (Auto mode) | rủi ro tiền | khi cổng duyệt đã chạy ổn định và khách xin |
| RAG trên kho mẫu workflow (PLENX có) | cần có kho mẫu trước | sau khi có ≥ 20 kế hoạch thật |
