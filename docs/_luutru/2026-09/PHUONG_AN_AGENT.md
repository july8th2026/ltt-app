> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: `docs/AGENT_LTT/01_DAC_TA_AGENT.md` + `02_LO_TRINH.md` (Q49/Q39, 02/08). Chỉ đọc để hiểu lịch sử.

# Phương án xây AI Agent cho LTTSTUDIOSAPP — chấm điểm & đề xuất — 2026-08-01

> **TÀI LIỆU NGHIÊN CỨU LỊCH SỬ.** Kết luận “hoãn/không Canvas ở v1” bên dưới đã
> bị thay bởi Q49/Q39 ngày 2026-08-02: xây full Agent + Canvas + video/GPU, kiến
> trúc hybrid React/TypeScript/React Flow/Vite cho Canvas và HTMX cho phần còn lại.
> Giữ nội dung cũ để bảo toàn lý do/trade-off, không làm theo kết luận cũ.

> Tài liệu **để thẩm duyệt**. Chưa sửa code, chưa sửa quyết định nào.
>
> Đầu vào: `KHAO_SAT_PLENX_AGENT.md` (mổ PLENX thật) · `PHAN_TICH_PLENX.md` ·
> nghiên cứu FLORA/FAUNA, OpenMontage, các bài báo agentic · một bản tư vấn ngoài
> (ChatGPT) do chủ dự án cung cấp · và chính mã nguồn nền tảng hiện có.

---

## 1. Đọc lại bản tư vấn ngoài — đúng ở đâu, sai ở đâu

Bản tư vấn đó **đúng về mặt tổng quát** nhưng **được viết cho một dự án trắng**.
Nó không biết `D:\LTTSTUDIOSAPP` đã có gì. Phải tách bạch trước khi dùng.

### 1.1 Những chỗ nó ĐÚNG, và trùng với thứ tôi đo được ở PLENX

| Nó nói | Bằng chứng từ khảo sát của ta |
|---|---|
| "Không nên thêm AI Agent ngay từ đầu… Agent chỉ nên **đề xuất hoặc tạo graph**, còn executor vẫn phải là hệ thống **deterministic**" | **Đúng y hệt PLENX đang làm.** `add_nodes_to_canvas` chỉ ghi canvas; executor `pics-workflow/run/node` là code tất định. FLORA cũng vậy. |
| Cần **provider adapter** chuẩn hoá (submit/getStatus/cancel/normalizeOutput) | PLENX có `pool_id`/`pool_code`/`serverId`; ta đã có `providers.py` + `api_pool.py` |
| Cần khai **kiểu cổng vào/ra** để không nối nhầm | PLENX làm bằng `config{}` của model (qualities, aspect_ratios, durations, supports_reference) |
| Cần **reproducibility**: lưu prompt cuối, model version, seed, input assets | PLENX lưu `generation_id`, `media_id`, **`api_key_id`**, `project_number` |
| Cần **state machine job** đầy đủ + retry | PLENX có `status`, `retry_count`, `error` + `error_message` |
| Phần khó **không phải giao diện** | đúng — ta đã có sẵn phần khó |

### 1.2 Những chỗ nó KHÔNG áp dụng được cho dự án này

| Nó đề xuất | Vấn đề | Sự thật ở dự án ta |
|---|---|---|
| **Redis + BullMQ / Celery** | thêm một dịch vụ phải trông, sao lưu, khởi động cùng Windows | `platform_core/jobs.py` đã có hàng đợi trên Postgres với `FOR UPDATE SKIP LOCKED`, heartbeat, `reclaim_orphans`, backoff luỹ thừa. **Q26 đã cân nhắc và bác bỏ hàng đợi ngoài** — vì nó tách khỏi bảng nghiệp vụ nên job và credit không atomic được. |
| **Next.js + React + Zustand + Tailwind** | kéo toàn bộ hệ sinh thái Node.js + bước build lên máy chủ Windows | **Q18 đã chốt HTMX**, lý do: không Node.js, không bước build, **mọi logic ở lại máy chủ** — trình duyệt không bao giờ thấy quy tắc tính tiền |
| **NestJS hoặc FastAPI (mới)** | dựng backend thứ hai | đã có FastAPI + SQLAlchemy + Alembic đang chạy production |
| **PostgreSQL + Cloudflare R2** | — | Postgres đã có; R2 là **H10 đã nằm trong kế hoạch** |
| **Fork InvokeAI** | InvokeAI xây quanh **Stable Diffusion cục bộ**, có **CSDL riêng, hàng đợi riêng, hệ người dùng riêng, model manager riêng** | ta là nền tảng **API-first**, đã có user/credit/admin/queue. Fork = **vận hành hai nền tảng song song rồi phải hợp nhất** — đắt hơn tự viết phần còn thiếu |
| **ComfyUI làm worker** | GPL-3.0 + cài đặt nặng + **hàng đợi thứ hai** + cần GPU | mọi app hiện tại đều `requires=("api",)`; **chưa có nhu cầu model cục bộ**. Máy chủ này còn đang chạy `D:\BOT GEMINI` phục vụ người thật |
| Ước lượng "SaaS ban đầu 4–7 tháng" | tính cả user/credit/billing/admin/nhiều provider | **những thứ đó đã XONG** (H1/H3/H8/H9). Ước lượng không áp dụng. |

### 1.3 Câu hỏi mà bản tư vấn đó không đặt ra — và là câu hỏi quan trọng nhất

> **Nếu agent tự dựng workflow, người dùng còn cần canvas node để làm gì?**

Canvas node tồn tại ở FLORA và PLENX vì họ bán **"tự tay dựng quy trình"**. Agent là
tính năng thêm vào sau. Còn luận điểm của ta là ngược lại: **agent làm thay, người
dùng không phải dựng gì cả.**

Với luận điểm đó, canvas trở thành thứ **tuỳ chọn**, không phải nền móng. Bỏ canvas
khỏi v1 tiết kiệm **hàng tháng** và giữ nguyên Q18. Kế hoạch do agent sinh ra hoàn
toàn có thể hiển thị bằng **một danh sách bước đọc được + báo giá**, không cần trình
soạn đồ thị.

---

## 2. Cái thật sự đang phải quyết

Không phải "chọn framework". Ta đã có **~70% hạ tầng nặng**. Cái phải quyết là:

**(A) Mức độ tự chủ của agent** — nó quyết định trước khi chạy, hay quyết định trong
lúc chạy?
**(B) Cách hiển thị** — danh sách bước, hay canvas đồ thị?
**(C) Ranh giới với hợp đồng app** — agent là app, hay là hạ tầng?

### 2.1 Ta đã có gì (đối chiếu code thật)

| Bộ phận agent cần | Có sẵn | Ở đâu |
|---|---|---|
| Durable execution, resume, retry, orphan | ✅ | `platform_core/jobs.py` |
| Worker tiến trình riêng, chạy dài | ✅ | `job_worker.py`, `job_runner.py` |
| Provider registry | ✅ | `platform_core/providers.py` |
| Pool khoá + cascade + rpm/tpm + cooldown | ✅ | `platform_core/api_pool.py` |
| Sổ tiền giữ-chỗ → quyết-toán → **hoàn** | ✅ | `platform_core/credit.py` |
| Lưu file trừu tượng | ⚠️ local | `platform_core/storage.py` (R2 = H10) |
| Thanh toán | ✅ | `platform_core/billing.py` (H9) |
| Phân quyền, phiên, CSRF, admin | ✅ | `server/` |
| **Tool registry** | ❌ | — |
| **Planner** | ❌ | — |
| **Verifier** | ❌ | — |
| **Job cha–con (fan-out)** | ❌ | `jobs` không có `parent_id` |
| **Báo giá trước khi chạy** | ❌ | — |
| **Tính tiền lượt suy luận** | ❌ | — |

### 2.2 Hai va chạm bắt buộc phải giải

**Va chạm 1 — bất biến "job không tra được giá thì bị từ chối chạy".**
`registry.credit_for()` raise nếu không có giá. Một agent **tự do quyết định từng
bước** thì không thể biết trước tổng chi phí → **phá bất biến**.

**Va chạm 2 — ràng buộc "thêm app = thêm thư mục, không sửa `platform_core`".**
Agent điều phối job của **nhiều app** thì không phải một app. `AGENTS.md` mục 2.3 yêu
cầu: *nếu buộc phải sửa nền tảng thì **dừng lại và giải thích vì sao***. Tôi đang làm
đúng điều đó ở mục 6.

---

## 3. Năm phương án

### PA-1 — Agent **lập kế hoạch**, executor **tất định**, giao diện HTMX
Người dùng gõ một câu → agent sinh **Plan JSON** (danh sách bước có schema) →
validate → **báo giá** → người duyệt → executor chạy qua hàng đợi hiện có → gallery.
Agent gọi LLM **một lần** ở đầu (cộng vài lần nếu người sửa yêu cầu).
Không canvas. Không vòng lặp tự do.

### PA-2 — Agent **vòng lặp đầy đủ**, tự quyết từng bước lúc chạy
Vòng `planner → chọn tool → chạy → verifier chấm → quyết định → lặp`, chặn bằng trần
số bước / trần credit / trần retry. Chi phí chỉ biết được sau khi chạy.

### PA-3 — **Canvas node + agent** (mô hình FLORA/PLENX)
React Flow + Next.js phía trước, workflow API + executor phía sau, agent ghi vào
canvas như `add_nodes_to_canvas` của PLENX.

### PA-4 — **Fork InvokeAI**
Lấy sản phẩm AI media hoàn chỉnh (React WebUI + node editor + executor + gallery +
model manager, Apache 2.0) rồi sửa thành sản phẩm của mình.

### PA-5 — **ComfyUI làm worker AI**
Giữ giao diện riêng, đẩy phần xử lý model sang ComfyUI (GPL-3.0) chạy cục bộ.

---

## 4. Bảng chấm điểm

### 4.1 Tiêu chí và trọng số

Trọng số đặt theo **rủi ro thật của dự án này** (nền tảng thương mại, một người phát
triển, máy chủ Windows tại nhà, đã có khách trả tiền qua H9).

| # | Tiêu chí | Trọng số | Vì sao trọng số đó |
|---|---|---:|---|
| C1 | **Kiểm soát chi phí / không mất tiền ngoài ý muốn** | **20%** | cao nhất — agent là cỗ máy tiêu tiền tự động; bất biến "không chạy job không có giá" tồn tại vì lý do này |
| C2 | Tái dụng hạ tầng đã có | 15% | 70% đã xong; phá đi để làm lại là lãng phí lớn nhất có thể |
| C3 | Không phá quyết định đã chốt (Q18/Q26/ràng buộc app) | 15% | đổi quyết định là được phép, nhưng phải trả giá bằng thời gian và rủi ro |
| C4 | Thời gian tới giá trị đầu tiên | 15% | một người làm; dự án cần kết quả dùng được sớm |
| C5 | Rủi ro kỹ thuật/vận hành (Windows, Cloudflare, một máy) | 15% | trần 100 giây/100 MB, máy chủ dùng chung với BOT GEMINI |
| C6 | Trần thương mại (đi được bao xa) | 10% | quan trọng nhưng không phải bây giờ |
| C7 | Chi phí bảo trì dài hạn | 10% | một người bảo trì |

### 4.2 Điểm (thang 10)

| Tiêu chí | Trọng số | **PA-1** | **PA-2** | **PA-3** | **PA-4** | **PA-5** |
|---|---:|---:|---:|---:|---:|---:|
| C1 Kiểm soát chi phí | 20% | **9** | 5 | 7 | 4 | 6 |
| C2 Tái dụng hạ tầng | 15% | **9** | 8 | 6 | 2 | 7 |
| C3 Không phá quyết định | 15% | **8** | 7 | 3 | 2 | 6 |
| C4 Thời gian tới giá trị | 15% | **8** | 6 | 3 | 4 | 5 |
| C5 Rủi ro kỹ thuật/vận hành | 15% | **8** | 6 | 4 | 3 | 5 |
| C6 Trần thương mại | 10% | 7 | 8 | **10** | 6 | 7 |
| C7 Bảo trì dài hạn | 10% | **8** | 6 | 5 | 3 | 5 |
| **TỔNG có trọng số** | 100% | **🥇 8,35** | 6,45 | 5,20 | 3,25 | 5,90 |

### 4.3 Giải trình vài điểm số đáng tranh luận

- **PA-2 C1 = 5.** Không phải vì agent vòng lặp *chắc chắn* đốt tiền, mà vì **không
  tính được tổng trước khi chạy** → không báo giá được → không duyệt được →
  **phá bất biến của nền tảng**. Trần cứng chỉ giảm thiệt hại, không khôi phục được
  khả năng báo giá.
- **PA-3 C3 = 3.** Không phải React Flow xấu — nó rất tốt và MIT. Điểm thấp vì nó kéo
  theo **Node.js + bước build lên máy chủ Windows**, đúng thứ Q18 chốt là không làm.
  Đổi Q18 là được, nhưng phải trả giá thật.
- **PA-4 C2 = 2.** InvokeAI **không thiếu** thứ ta thiếu (nó cũng không có agent
  verifier), mà **thừa** thứ ta đã có (user, queue, DB, model manager). Fork nghĩa là
  hợp nhất hai hệ người dùng và hai hệ tiền — công việc lớn hơn tự viết planner.
- **PA-5** không thật sự là đối thủ của PA-1/2/3 — nó **trực giao**. Chỉ có ý nghĩa
  khi xuất hiện app cần **GPU cục bộ**. Hiện mọi app đều `requires=("api",)`.
  → Xếp vào "để mở", không chọn bây giờ.

---

## 5. Phương án đề xuất — PA-1+ ("kế hoạch có kiểm chứng")

PA-1 thắng, **nhưng PA-1 thuần chưa đáp ứng yêu cầu gốc của bạn**: *"nếu khuôn mặt
sai thì tự tạo lại"*. Đó là verifier — thứ chỉ PA-2 có.

Đề xuất là **PA-1 cộng đúng một cơ chế mượn từ PA-2**, và đây là điểm mấu chốt của cả
tài liệu này:

> ### Vòng lặp tự sửa nằm ở EXECUTOR, không nằm ở AGENT.
>
> Agent không được phép lặp. Nhưng **mỗi bước trong kế hoạch được khai kèm điều kiện
> nghiệm thu và số lần làm lại tối đa**. Executor (code tất định) mới là thứ chạy vòng
> kiểm-tra-làm-lại, trong giới hạn đã khai.

Hệ quả: **tổng chi phí vẫn tính được trước khi chạy.**

```
chi_phi_toi_da = Σ ( gia_buoc_i × (1 + so_lan_lam_lai_toi_da_i) ) + gia_lap_ke_hoach
```

- Giữ chỗ = `chi_phi_toi_da` → **`credit.giu_cho()` hiện có, không sửa gì**
- Quyết toán = chi phí thật → **`credit.quyet_toan()` tự ghi bút toán bù, hoàn phần dư**
- Job lỗi hẳn → **`credit.hoan()`**

Ba hàm này **đã tồn tại và đã có test**. Bất biến "job không tra được giá thì bị từ
chối" **được giữ nguyên**: mỗi bước là một `job_type` đã biết với tham số đã biết, nên
`registry.credit_for()` chạy được bình thường.

Đây chính là chỗ mà **thiết kế sổ credit từ H3 trả cổ tức** — nó đã sẵn sàng cho agent
mà không ai cố ý thiết kế cho agent.

### 5.1 Luồng đầy đủ

```
 Người dùng gõ: "Tạo video nữ thần tượng K-pop 15 giây từ ảnh này"
      │
      ▼
 ① PLANNER  (1 lượt LLM, tính phí như một job)
      │   ngữ cảnh: danh mục tool + schema tham số + ảnh đã phân tích
      │   ra:      Plan JSON
      ▼
 ② VALIDATOR (code tất định — KHÔNG phải LLM)
      │   • mọi tool có thật? • tham số hợp schema? • kiểu vào/ra khớp?
      │   • đồ thị không vòng? • mọi bước tra được giá?
      │   sai → trả lỗi cho planner sửa (tối đa N lần), KHÔNG chạy
      ▼
 ③ BÁO GIÁ + CỔNG DUYỆT
      │   hiện: các bước · model mỗi bước · giá mỗi bước · TỔNG TỐI ĐA
      │   người bấm Duyệt  ← không duyệt thì không tiêu một đồng nào
      ▼
 ④ GIỮ CHỖ credit = tổng tối đa   (credit.giu_cho, một transaction với tạo job)
      ▼
 ⑤ EXECUTOR (worker hiện có)
      │   với mỗi bước theo thứ tự topo:
      │     chạy tool  →  nếu bước có `verify`:
      │                      chấm  →  đạt   : đi tiếp
      │                            →  không: theo `on_fail`
      │                                      • retry_same   (đổi seed)
      │                                      • refine       (sửa cục bộ)
      │                                      • regenerate   (làm lại từ đầu)
      │                                      • switch_model (đổi model)
      │                      hết lượt → dừng nhánh, ghi lý do
      ▼
 ⑥ QUYẾT TOÁN theo chi phí thật → hoàn phần dư tự động
      ▼
 ⑦ Trả kết quả + nhật ký quyết định (mỗi bước: làm gì, chấm bao nhiêu, vì sao lại)
```

### 5.2 Plan JSON — lược đồ đề xuất

Học trực tiếp từ PLENX: **cho LLM sinh lược đồ PHẲNG, máy chủ chuẩn hoá.**

```json
{
  "version": 1,
  "goal": "video nữ thần tượng K-pop 15 giây từ ảnh",
  "budget_max_credit": 320,
  "steps": [
    { "id": "s1", "tool": "image.analyze",
      "params": { "image_ref": "$input.image" } },

    { "id": "s2", "tool": "image.remove_bg",
      "params": { "image_ref": "$s1.image" }, "after": ["s1"] },

    { "id": "s3", "tool": "image.generate",
      "params": { "prompt": "...", "count": 4, "aspect_ratio": "9:16" },
      "after": ["s2"],
      "fanout": 4,
      "verify": { "check": "face_identity",
                  "against": "$input.image",
                  "min_score": 0.75 },
      "on_fail": "regenerate",
      "max_retry": 2 },

    { "id": "s4", "tool": "video.generate",
      "params": { "image_ref": "$s3.best", "duration_s": 15 },
      "after": ["s3"],
      "verify": { "check": "vlm_judge",
                  "rubric": "đúng người trong ảnh gốc, không lỗi tay/mặt" },
      "on_fail": "retry_same",
      "max_retry": 1 }
  ]
}
```

Bốn điều cần chú ý:

1. **`$s1.image`** — tham chiếu đầu ra bước trước. Executor phân giải, LLM chỉ viết tên.
2. **`verify` + `on_fail` + `max_retry`** — **hợp đồng tự sửa**, khai trong dữ liệu chứ
   không nằm trong đầu LLM. Nhờ vậy tính được trần chi phí.
3. **`fanout`** — sinh N biến thể song song (chính là "▶ Play trên Frame" của PLENX).
4. **`budget_max_credit`** — trần cứng; validator từ chối kế hoạch vượt trần.

### 5.3 Hai kiểu verifier

| Kiểu | Cách làm | Chi phí | Dùng khi |
|---|---|---|---|
| **`vlm_judge`** | gửi ảnh + ảnh gốc + rubric cho Gemini Vision, đòi trả JSON có điểm | 1 lượt LLM | **mặc định** — không thêm phụ thuộc, ta đã có key |
| **`face_identity`** | embedding khuôn mặt, cosine similarity, ngưỡng số | CPU cục bộ | khi cần **con số khách quan, lặp lại được** |

Bắt đầu bằng `vlm_judge`. `face_identity` là nâng cấp, thêm sau, **không đổi Plan JSON**
— chỉ thêm một giá trị cho trường `check`.

Quy tắc **sửa hay làm lại** lấy từ *Generation Navigator*: **sai một phần → sửa cục bộ;
sai cấu trúc → vứt, làm lại.** Chính verifier trả về loại lỗi để executor chọn nhánh.

### 5.4 Vì sao phương án này thắng cả về mặt thương mại

Nó làm được thứ **cả PLENX lẫn FLORA hiện chưa làm**:

| | PLENX | FLORA | **PA-1+** |
|---|---|---|---|
| Agent dựng quy trình | ✅ | ✅ | ✅ |
| **Cổng duyệt kèm báo giá** | ❌ | ✅ | ✅ |
| **Verifier chấm kết quả** | ❌ | ❌ | ✅ |
| **Tự làm lại khi sai** | ❌ | ❌ | ✅ |
| **Trần chi phí tính được trước** | ❌ | ❌ | ✅ |
| Canvas node | ✅ | ✅ | ⏸️ để sau |

Ta bỏ thứ đắt nhất (canvas) để lấy thứ khác biệt nhất (tự kiểm chứng).

---

## 6. Phải sửa nền tảng — và vì sao (theo `AGENTS.md` mục 2.3)

`AGENTS.md` yêu cầu dừng lại giải thích khi buộc phải sửa `platform_core/`. Dưới đây là
danh sách đầy đủ và lý do từng mục.

| # | Sửa gì | Vì sao KHÔNG đi vòng được |
|---|---|---|
| **N1** | `AppManifest` thêm **`tools=(...)`** | Agent phải biết **làm được những gì**. Nếu agent import thẳng `apps.<slug>.jobs` thì phá chiều phụ thuộc một hướng và bị `test_60` chặn. Đây đúng nghĩa **"bổ sung vào hợp đồng"** mà AGENTS.md cho phép. |
| **N2** | `ToolSpec`: `name, description, params_schema, returns, cost_fn` | Agent cần **schema tham số** mới sinh được lời gọi hợp lệ. PLENX gọi cái này là `config{}` của model. Không có nó thì LLM đoán bừa. |
| **N3** | `jobs` thêm **`parent_id`** + `plan_id` + `step_id` | Fan-out và "chờ N job con xong". `claim()` hiện lấy đúng 1 job, không có quan hệ cha–con. |
| **N4** | Bảng **`agent_runs`** (plan JSON, trạng thái, ngân sách, nhật ký quyết định) | Cần checkpoint để **resume** và để **kiểm toán vì sao tốn tiền**. OpenMontage gọi là checkpoint + decision log. |
| **N5** | `providers.py` thêm **schema tham số model** (`qualities`, `aspect_ratios`, `durations`, `supports_reference`, mặc định) | Bài học trực tiếp từ PLENX. Thiếu nó thì agent chọn tỉ lệ/thời lượng model không hỗ trợ. |
| **N6** | Ghi **`api_key_id`** vào `job.result` | Truy vết khoá nào tạo ra sản phẩm nào. Rẻ, làm ngay được, PLENX đã làm. |
| **N7** | Loại job mới **`agent.plan`** để tính tiền lượt suy luận | PLENX thu **4 credit/lượt**. Không tính là lỗ ngầm. |

**Không sửa:** `credit.py` (đã đủ), `db.py`, `billing.py`, `secretbox.py`, cơ chế phiên/
CSRF/phân quyền. **Không đổi Q18** (không Node.js). **Không đổi Q26** (giữ hàng đợi
Postgres).

Bảy mục trên đều là **bổ sung (additive)**, không đổi hành vi cũ → migration thêm cột
có `server_default`, app cũ chạy nguyên.

---

## 7. Agent là app hay là hạ tầng?

Đề xuất: **cả hai, tách vai trò rõ ràng.**

```
platform_core/agent/          ← HẠ TẦNG (dùng chung)
    tools.py       gom ToolSpec từ mọi manifest — KHÔNG biết tên app nào
    planner.py     câu người → Plan JSON (gọi LLM qua api_pool)
    validator.py   kiểm schema/kiểu/vòng/giá — code tất định, không LLM
    executor.py    chạy Plan qua hàng đợi, xử lý verify/retry/fanout
    verifier.py    vlm_judge · (sau) face_identity
    budget.py      trần chi phí, báo giá, cổng duyệt

apps/<ten_app>/               ← APP (mặt khách, một mục đích)
    manifest.py    khai tools=(...) + credit_cost
    routes.py      ô nhập yêu cầu · trang duyệt kế hoạch · gallery
    jobs.py        handler của chính các tool nó khai
```

Nền tảng **vẫn không biết tên app nào tồn tại** — `tools.py` quét manifest y hệt
`registry.discover()`. `test_60::test_no_app_slug_is_hardcoded_in_the_platform` vẫn xanh.

---

## 8. Lộ trình — 5 giai đoạn, mỗi giai đoạn tự đứng được

Đánh số theo hệ `H` hiện có. Đề xuất **H12** (H10 R2 và H11 thêm tool đã có chỗ).

| GĐ | Nội dung | Giá trị tự thân | Tiêu chí xong |
|---|---|---|---|
| **H12.1** | **Tool registry** (N1, N2) + báo giá một bước | app khai tool; `/agent/tools` liệt kê được | test: tool trùng tên bị chặn; thiếu `params_schema` bị chặn; agent không import app |
| **H12.2** | **Fan-out** (N3): `parent_id`, chờ job con, `agent_runs` (N4) | chạy N biến thể song song **không cần agent** | test: 4 job con, 1 chết → cha xử lý đúng; reclaim orphan vẫn chạy |
| **H12.3** | **Planner + Validator + Cổng duyệt** | **người gõ một câu → thấy kế hoạch + giá → duyệt → chạy** ⇦ *giá trị lớn nhất, đến sớm nhất* | test: plan sai schema bị từ chối; không duyệt = 0 credit; giữ chỗ = trần, hoàn phần dư |
| **H12.4** | **Verifier + vòng tự sửa** (`vlm_judge`) | **đúng yêu cầu gốc: mặt sai thì tự tạo lại** | test: verify trượt → retry đúng số lần; hết lượt → dừng + hoàn đúng; chi phí không vượt trần |
| **H12.5** | **App thật đầu tiên** dùng agent (video K-pop) | sản phẩm bán được | nghiệm thu trình duyệt, full suite xanh, scan 0 |

**Ngoài phạm vi H12:** canvas node (PA-3), ComfyUI (PA-5), face embedding, đa agent.
Ghi vào "để mở", quyết sau khi H12.5 có khách thật.

**Phụ thuộc cứng:** H12.5 nếu sinh **video** thì **cần H10 (R2 + `url_for`) trước** —
file video vượt trần Cloudflare nếu stream qua Tunnel. Nhánh **chỉ-ảnh** không cần H10.

---

## 9. Rủi ro và cách chặn

| Rủi ro | Mức | Cách chặn (thiết kế sẵn, không phải lời hứa) |
|---|---|---|
| Agent đốt credit của khách | **cao** | trần `budget_max_credit` trong plan · validator từ chối plan vượt trần · **cổng duyệt bắt buộc** · giữ chỗ = trần tối đa · `max_retry` mỗi bước |
| LLM sinh plan sai lược đồ | cao | **validator tất định** + trả lỗi cho planner sửa tối đa N lần + **đường lui bóc JSON từ văn bản** (đúng cách PLENX làm) |
| Verifier chấm sai → làm lại vô ích | trung bình | `max_retry` nhỏ (1–2) · ghi điểm chấm vào nhật ký để chỉnh rubric · bắt đầu bằng ngưỡng lỏng |
| Vòng lặp không dừng | trung bình | agent **không có vòng lặp**; executor chạy đồ thị có hướng không chu trình, validator đã bác vòng |
| Job dài vượt 100 giây | thấp | đã đi qua hàng đợi + poll — kiến trúc hiện tại đúng sẵn |
| File video vượt 100 MB | **cao nếu làm video** | **chặn cứng: H10 trước** |
| Sửa `platform_core` làm vỡ app cũ | trung bình | 7 mục đều additive, migration có `server_default`, full suite phải xanh mỗi giai đoạn |
| Chi phí suy luận vượt chi phí sinh nội dung | trung bình | đo được ở PLENX: **4 credit/lượt = 2× một ảnh**. Tính `agent.plan` như một job có giá, hiện trong báo giá |

---

## 10. Ước lượng

Không lấy số của bản tư vấn ngoài vì nó tính cả phần đã xong. Ước lượng lại theo
**việc còn thiếu thật**, một người làm cùng Claude Code:

| Giai đoạn | Ước lượng |
|---|---|
| H12.1 Tool registry | 2–4 ngày |
| H12.2 Fan-out + agent_runs | 3–5 ngày |
| H12.3 Planner + validator + cổng duyệt | 5–8 ngày |
| H12.4 Verifier + vòng tự sửa | 4–7 ngày |
| H12.5 App thật đầu tiên | 5–10 ngày |
| **Tổng tới sản phẩm bán được** | **~3–5 tuần** |

So sánh: PA-3 (canvas) thêm **6–12 tuần** chỉ riêng phần front-end + hạ tầng build, và
đổi Q18. PA-4 (fork InvokeAI) — hợp nhất hai hệ người dùng/tiền, **không ước lượng nổi**
một cách trung thực.

---

## 11. Cần chủ dự án duyệt

1. **Chốt PA-1+** (kế hoạch có kiểm chứng, không canvas ở v1)?
2. **Duyệt 7 mục sửa nền tảng** (N1–N7)? Đây là điểm bắt buộc theo `AGENTS.md` —
   không duyệt thì tôi không đụng `platform_core/`.
3. **Ghi quyết định mới** vào `QUYET_DINH_NEN_TANG.md`:
   - **Q32** — Mô hình agent: *lập kế hoạch có kiểm chứng*; agent không lặp, executor lặp
     trong giới hạn khai trong plan.
   - **Q33** — Tiền cho agent: *ngân sách trần + cổng duyệt kèm báo giá*; giữ chỗ theo
     trần, quyết toán theo thật, hoàn phần dư. Lượt suy luận **có tính phí**.
   - **Q34** — Canvas node: **hoãn**, không phải nền móng; Q18 (HTMX) **giữ nguyên**.
4. **Chọn app thật đầu tiên** cho H12.5 — video K-pop (cần H10 trước) hay một app
   chỉ-ảnh (chạy được ngay)?
5. **Có lấy nốt phần khảo sát PLENX còn thiếu không** (Frame ▶ fan-out, ~4–6 credit)?
   Nó ảnh hưởng trực tiếp thiết kế H12.2.
