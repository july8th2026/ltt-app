# Kiểm kê tài sản thật + lộ trình xây agent như PLENX/FLORA — 2026-08-01

> **TÀI LIỆU NGHIÊN CỨU LỊCH SỬ.** Mọi đoạn nói Canvas “để sau/hoãn” đã bị
> Q49/Q39 (Q49 thay Q38, 2026-08-02) thay thế. Lộ trình đang hiệu lực là
> `docs/AGENT_LTT/02_LO_TRINH.md`: full Agent + Canvas + 7 tool ảnh/text/video/GPU.

> Đọc `D:\BOT GEMINI` (**CHỈ ĐỌC**, không sửa gì) và đối chiếu với `D:\LTTSTUDIOSAPP`.
> Mục tiêu: biết chính xác **đã có gì**, **thiếu gì**, rồi chấm điểm lộ trình.
>
> Tài liệu **để thẩm duyệt**. Chưa sửa code, chưa đổi quyết định nào.
> Nối tiếp `PHUONG_AN_AGENT.md` (chấm điểm kiến trúc agent) và
> `KHAO_SAT_PLENX_AGENT.md` (mổ PLENX thật).

---

## 1. Phát hiện quyết định trước khi bàn lộ trình

> ### Agent là thứ **điều phối công cụ**. Nền tảng ta hiện có **đúng 1 công cụ thật** (`thumbnail`).
>
> Một agent điều phối một công cụ thì không có gì để điều phối. **Thứ tự đúng bắt buộc
> là: công cụ trước, agent sau.** Đây là điều thay đổi kết luận so với phiên trước.

Ở `D:\BOT GEMINI` có **55.925 dòng module** — đó là kho công cụ đã chạy thật, phục vụ
người dùng thật. Đó mới là tài sản lớn nhất, không phải hạ tầng.

---

## 2. Kiểm kê `D:\BOT GEMINI` — số liệu đo được

### 2.1 Quy mô theo tầng

| Tầng | File | Dòng | Đánh giá tái dụng |
|---|---:|---:|---|
| `app/modules/` | 266 | **55.925** | ⭐ **tài sản chính** — logic nghiệp vụ |
| `app/services/` | 48 | 9.338 | hỗn hợp — xem 2.4 |
| `app/models/` | 18 | 2.733 | ⭐ registry model rất đáng lấy |
| `app/storage/` | 11 | 2.700 | ❌ store JSON — ta đã có Postgres |
| `app/resources/` | 8 | 2.143 | ⭐ pool khoá + discovery |
| `app/providers/` | 11 | 1.390 | ⭐ adapter nhà cung cấp |
| `app/workers/` | 6 | 804 | ⚠ mẫu tham khảo |
| `app/kernel/` + `orchestrator/` + `engines/` | 6 | 369 | ⚠ **khung dựng dở** |

### 2.2 Module theo dòng code

| Dòng | Module | Loại | Ghi chú |
|---:|---|---|---|
| 28.685 | `seedance` | Prompt Studio | có **CSDL riêng, i18n riêng, routes riêng** → là một *ứng dụng*, không phải module |
| 6.454 | `auto_sub_video` | ffmpeg | cần H10 |
| 5.656 | `seedance_video` | API video | ⭐ có `cost.py` + **`face_detect.py`** |
| 2.884 | `cut_clip_short` | GPU | cần H10 + GPU |
| 2.731 | `plenx` | API video | ⭐ adapter + runner sạch nhất |
| 2.404 | `codex` | agent code | rủi ro cao (Q: để sau hoặc không làm) |
| 1.460 | `video_upscale` | GPU | vendor 48 MB binary |
| 1.418 | `thumbnail_api` | API ảnh | **đã port sang LTT, mới đạt ~30%** |
| 908 | `gemini_video` | API video | |
| 857 | `concat_pro` | ffmpeg | |
| 800 | `whisk_nano` | cookie | ❌ không đưa lên (Q10/nhóm D) |
| 763 | `gemini_api_chat` | API chat | giá trị thương mại thấp |
| 456 | `video_chain` | ffmpeg | nhỏ nhất nhóm ffmpeg |
| 310 | `gemini_image` | API ảnh | ⭐ nhỏ, dễ port |
| 139 | `youtube_script` | API text | ⭐ nhỏ nhất, kiểm chứng hợp đồng |

9 module khác (`veo3`, `taoanh_flow`, `suno`, `story_browser`, `gemini_chat`,
`flow_text2video`, `flow_img2video`, `chatgpt_chat`, `character_browser`) hiện **0 dòng**
— đã rỗng/archive.

### 2.3 Tài sản ĐÁNG PORT (đo được, không suy đoán)

| Tài sản | Đường dẫn | Dòng | Vì sao quý |
|---|---|---:|---|
| **Image Model Registry** | `app/models/image_model_registry.py` | 193 | `tier` · `endpoint` · **`supported_aspects`** · **`max_count`** · `is_active`. Đây **chính là `params_schema`** mà `PHUONG_AN_AGENT.md` xác định ta thiếu — PLENX gọi là `config{}` |
| **Video Model Registry** | `app/models/video_model_registry.py` | 178 | tương tự cho video |
| **Cost model token-based** | `modules/seedance_video/cost.py` | 134 | tính theo `(w×h×fps×dur)/DIVISOR`, **hằng số hiệu chỉnh từ job thật** (50.638 token đo được), markup %, quy VND, làm tròn **over-estimate an toàn cho cổng ngân sách** |
| **PLENX adapter** | `modules/plenx/adapters/plenx_adapter.py` | 382 | adapter API hoàn chỉnh |
| **PLENX runner** | `modules/plenx/runner.py` | 360 | ⭐ **submit → poll → download** đã tôi luyện: xoay khoá theo mã lỗi · **poll timeout động theo duration×resolution** · tách *queue budget* / *gen budget* / *hard ceiling 90 phút* · **% tiến độ mượt theo thời gian trôi** (thay cách "+10 mỗi poll" bị đứng ở 95) · **ghi `task_id` TRƯỚC khi poll** để khởi động lại còn resume · backoff 429/5xx cùng khoá trước |
| **Face detect** | `modules/seedance_video/face_detect.py` | 119 | insightface `buffalo_sc` (SCRFD, CPU) + fallback Haar, **singleton thread-safe**, ngưỡng 0.5 **hiệu chỉnh từ bộ ảnh thật** với hai chế độ hỏng được ghi lại rõ |
| **API pool** | `app/resources/api_pool_manager.py` + `api_allocator.py` + `api_lease_tracker.py` | 484+ | ⚠ ta **đã có bản tốt hơn** (`api_pool.py` có cascade + rpm/tpm) |
| **Module discovery** | `app/resources/module_discovery.py` | 175 | quét `modules/*/manifest.py` — **cùng ý tưởng `registry.discover()` của ta** |
| **Manifest + `config_schema`** | mọi `modules/*/manifest.py` | — | ⭐ khai **`max_workers`, `max_inflight_per_user`, `poll_interval_s`, `poll_timeout_s`, `submit_max_retry`, `usd_to_vnd`, `markup_percent`, `daily_budget_usd`, `ref_retention_days`** |
| **Kho prompt** | `prompts/` | **130 file `.txt`** + `_labels.json` | 7 danh mục: `thumbnail_youtube`, `thumbnail_pro`, `gemini_thumbnail`, `character`, `story`, `youtube_script`, `prompt_fixer` |
| **Batch engine** | `app/services/batch_engine.py` | 640 | `asyncio.Semaphore(max_concurrent)` + `gather` — mẫu fan-out |

### 2.4 Tài sản **KHÔNG** nên port (ta đã có bản tốt hơn)

| BOT GEMINI | Vấn đề | LTTSTUDIOSAPP đã có |
|---|---|---|
| `kernel/job_registry.py` | **JSON file**, ghi cả file mỗi lần cập nhật; docstring tự nhận *"NO state machine, NO retry"* | bảng `jobs` Postgres + state machine + retry backoff |
| `services/job_queue.py` | **asyncio trong tiến trình** — chết là mất hàng đợi | `SKIP LOCKED` + heartbeat + `reclaim_orphans` |
| `storage/*.json` (11 file) | store JSON rời rạc | Postgres + Alembic |
| `services/quota_guard.py` | 15 dòng, đếm lượt/ngày | **sổ credit append-only** giữ-chỗ→quyết-toán→hoàn |
| `services/user_manager.py`, `workspace_policy.py` | quyền theo file | `users` + `app_access` + middleware + `sessions` thu hồi được |
| `kernel/`, `orchestrator/`, `engines/` | **khung dựng dở** — docstring ghi *"existing executors are NOT modified yet"*, `_KNOWN_PROVIDERS` gần như rỗng | `registry.py` đã hoàn chỉnh và **có test chốt** |

> **Kết luận tầng:** hạ tầng lấy của **LTTSTUDIOSAPP** (mạnh hơn hẳn), nghiệp vụ lấy
> của **BOT GEMINI** (đã chạy thật). Đúng như Q3 đã chốt: *"Viết mới trong
> LTTSTUDIOSAPP, chỉ tham chiếu BOT GEMINI"*.

---

## 3. Kiểm kê `D:\LTTSTUDIOSAPP` — nền móng

### 3.1 Đã có và đã chạy production

| Bộ phận | Trạng thái | Vai trò với agent |
|---|---|---|
| Hàng đợi Postgres bền (`SKIP LOCKED`, heartbeat, reclaim, backoff) | ✅ | **executor của agent** |
| Worker tiến trình riêng | ✅ | chạy job dài |
| Sổ credit append-only: giữ chỗ → quyết toán → **hoàn** | ✅ | **ngân sách agent — không phải sửa dòng nào** |
| Thanh toán PayOS idempotent (H9) | ✅ | khách nạp tiền |
| APIKEYS: mã hoá, cascade đa-provider, rpm/tpm, cooldown (H8) | ✅ | **hơn BOT GEMINI** |
| Provider Registry | ✅ | thiếu `params_schema` |
| Storage trừu tượng | ⚠ local | R2 = **H10 chưa làm** |
| User/phiên/CSRF/phân quyền/admin | ✅ | |
| Registry app + test chốt hợp đồng | ✅ | nền cho tool registry |
| Giao diện HTMX, header/catalog | ✅ | |

### 3.2 Chưa có

| Thiếu | Cần cho |
|---|---|
| **Công cụ thật** (mới 1: `thumbnail`, và mới đạt ~30% parity) | mọi thứ |
| `params_schema` cho model | agent chọn tham số hợp lệ |
| Tool registry (`tools=()` trong manifest) | agent biết làm được gì |
| Job cha–con (`parent_id`) + fan-out | chạy N nhánh song song |
| Planner / Validator / Verifier | agent |
| Báo giá + cổng duyệt | kiểm soát tiền |
| R2 / CDN (H10) | mọi công cụ video |
| Canvas node | mô hình PLENX/FLORA đầy đủ |

---

## 4. Bản đồ khoảng cách — 3 tầng

```
┌─ TẦNG 3 — TRẢI NGHIỆM ────────────────────────────────────┐
│  Canvas node  ·  Composer  ·  Gallery  ·  Agent chat      │
│  Ta: ❌ (chỉ có form HTMX)   PLENX: ✅   BOT GEMINI: ❌      │
└───────────────────────────────────────────────────────────┘
┌─ TẦNG 2 — ĐIỀU PHỐI ──────────────────────────────────────┐
│  Tool registry · Planner · Validator · Verifier · Fan-out │
│  Ta: ❌   PLENX: một phần (không verifier)   BOT GEMINI: ❌ │
└───────────────────────────────────────────────────────────┘
┌─ TẦNG 1 — NĂNG LỰC + HẠ TẦNG ─────────────────────────────┐
│  Công cụ (ảnh/video/text) · adapter · cost · prompt        │
│    → BOT GEMINI: ✅ 55.925 dòng đã chạy thật               │
│  Hàng đợi · credit · khoá API · thanh toán · quyền         │
│    → LTTSTUDIOSAPP: ✅ đã production                       │
└───────────────────────────────────────────────────────────┘
```

**Tầng 1 gần như đủ — nhưng bị chia đôi ở hai kho.** Việc chính là **hợp nhất tầng 1**,
rồi mới xây tầng 2, rồi mới cân nhắc tầng 3.

---

## 5. Năm lộ trình

| | Lộ trình | Thứ tự |
|---|---|---|
| **LT-1** | **Công cụ trước** | port module BOT GEMINI thành app LTT (**khai sẵn `tools=` agent-ready**) → agent → canvas |
| **LT-2** | **Agent trước** | xây agent trên 1–2 công cụ có sẵn → port thêm công cụ → canvas |
| **LT-3** | **Canvas trước** | dựng canvas + node runtime (React Flow) → port công cụ thành node → agent |
| **LT-4** | **Đồng thời** | ba tầng cùng lúc |
| **LT-5** | **Fork ngoài** | InvokeAI hoặc ComfyUI làm nền |

### Tiêu chí và trọng số

| # | Tiêu chí | Trọng số | Lý do |
|---|---|---:|---|
| C1 | Kiểm soát chi phí / không mất tiền ngoài ý muốn | 18% | nền tảng đã có khách trả tiền (H9) |
| C2 | Tái dụng tài sản đã có ở **cả hai kho** | 17% | 55.925 + hạ tầng production |
| C3 | Thời gian tới **sản phẩm bán được** | 16% | một người làm |
| C4 | Rủi ro kỹ thuật / vận hành | 15% | Windows, một máy, dùng chung với BOT GEMINI |
| C5 | Không phá quyết định đã chốt | 12% | đổi được nhưng phải trả giá |
| C6 | Đạt mục tiêu "vận hành như PLENX/FLORA" | 12% | mục tiêu chủ dự án nêu |
| C7 | Bảo trì dài hạn | 10% | một người bảo trì |

### Bảng điểm

| Tiêu chí | TS | **LT-1** | **LT-2** | **LT-3** | **LT-4** | **LT-5** |
|---|---:|---:|---:|---:|---:|---:|
| C1 Kiểm soát chi phí | 18% | **9** | 7 | 6 | 4 | 4 |
| C2 Tái dụng tài sản | 17% | **10** | 7 | 5 | 7 | 2 |
| C3 Thời gian tới bán được | 16% | **8** | 6 | 4 | 3 | 4 |
| C4 Rủi ro kỹ thuật | 15% | **9** | 7 | 5 | 3 | 3 |
| C5 Không phá quyết định | 12% | **9** | 8 | 3 | 4 | 2 |
| C6 Đạt mục tiêu PLENX/FLORA | 12% | 6 | 8 | 9 | **10** | 7 |
| C7 Bảo trì dài hạn | 10% | **9** | 8 | 6 | 5 | 3 |
| **TỔNG** | 100% | **🥇 8,65** | 7,18 | 5,36 | 5,02 | 3,53 |

### Giải trình

- **LT-1 thắng chủ yếu ở C2 và C4.** Nó là lộ trình duy nhất **dùng ngay 55.925 dòng
  đã chạy thật**, và mỗi công cụ port xong là **bán được ngay** — không phải chờ agent
  hay canvas. Đường này đã được kiểm chứng một lần rồi: `thumbnail` (H5).
- **LT-2 mất điểm ở C2/C3** vì agent chỉ có 1 công cụ để điều phối → **không tạo ra giá
  trị nào cho khách** cho tới khi có thêm công cụ. Đó là lý do tôi **đổi kết luận so
  với phiên trước**.
- **LT-3 mất điểm nặng ở C5** — canvas React Flow kéo Node.js + bước build lên máy chủ
  Windows, đúng thứ Q18 chốt là không làm. Ngoài ra canvas không có công cụ để hiển thị
  thì rỗng.
- **LT-4** điểm C6 cao nhất (10) nhưng C3/C4 thấp nhất — làm ba tầng cùng lúc với một
  người là cách chắc chắn nhất để **không có gì chạy được** trong nhiều tháng.
- **LT-5 = 3,53**, thấp nhất. InvokeAI/ComfyUI **thừa** thứ ta đã có (user, queue, DB,
  model manager) và **thiếu** thứ ta thiếu (verifier, credit, agent). Fork = hợp nhất
  hai hệ người dùng và hai hệ tiền.

---

## 6. Lộ trình đề xuất — LT-1 "công cụ agent-ready"

Điểm mấu chốt để LT-1 **không phải việc làm lại về sau**:

> ### Mỗi công cụ port sang phải khai `tools=(ToolSpec…)` NGAY TỪ ĐẦU.
>
> Port công cụ mà không khai ToolSpec = phải mở lại từng app khi làm agent. Khai sẵn thì
> agent bật lên là có **hộp công cụ đầy đủ** mà không sửa app nào.

### Bốn chặng

```
CHẶNG A — Hợp nhất tầng 1  (công cụ + schema)
   A0  ToolSpec vào hợp đồng app (N1,N2)  ─ 2–4 ngày
   A1  params_schema cho model (port 2 registry BOT GEMINI)  ─ 2–3 ngày
   A2  thumbnail đạt parity (port 130 file prompt + 6/11/9/5 catalog + chọn model)  ─ 4–6 ngày
   A3  gemini_image + youtube_script (2 công cụ nhỏ, kiểm chứng hợp đồng)  ─ 3–5 ngày
        ⇒ 3 công cụ bán được, 0 rủi ro agent
                              │
CHẶNG B — H10 (R2 + url_for)  ─ 4–7 ngày   ◄── CHẶN mọi công cụ video
                              │
CHẶNG C — Công cụ video  (port plenx + seedance_video)
   C1  adapter + runner (port submit→poll→download đã tôi luyện)  ─ 5–8 ngày
   C2  cost model token-based + hiệu chỉnh từ job thật  ─ 2–3 ngày
        ⇒ sản phẩm giá trị cao nhất, đúng "Ứng viên số 1"
                              │
CHẶNG D — Tầng 2: AGENT  (thiết kế PA-1+ ở PHUONG_AN_AGENT.md)
   D1  fan-out: jobs.parent_id + agent_runs  ─ 3–5 ngày
   D2  planner + validator + cổng duyệt kèm báo giá  ─ 5–8 ngày
   D3  verifier + vòng tự sửa (vlm_judge → face embedding)  ─ 4–7 ngày
        ⇒ "gõ một câu → kế hoạch + giá → duyệt → chạy → tự sửa nếu sai"
                              │
CHẶNG E — Tầng 3: CANVAS  ── quyết định SAU khi D xong, không phải bây giờ
```

**Tổng chặng A→D: ~7–11 tuần.** Mỗi chặng có sản phẩm bán được, không chặng nào là
"đầu tư chờ".

### Vì sao verifier rẻ hơn tưởng

`face_detect.py` bên BOT GEMINI **đã giải xong phần khó nhất** của insightface: tải model
tự động, singleton thread-safe, fallback khi thiếu onnxruntime, ngưỡng hiệu chỉnh từ ảnh
thật. Nó hiện chỉ làm **phát hiện** (`allowed_modules=["detection"]`). Chuyển sang
**nhận dạng danh tính** là thêm `"recognition"` và so cosine giữa hai embedding — phần
hạ tầng đã xong.

→ `face_identity` verifier khả thi hơn nhiều so với ước lượng ở `PHUONG_AN_AGENT.md`.

### Thứ tự port công cụ và lý do

| Ưu tiên | Module | Dòng | Vì sao | Chặn bởi |
|---|---|---:|---|---|
| 1 | `thumbnail_api` (nâng parity) | 1.418 | đã có khung, thiếu 70% tính năng; port kho prompt là **rẻ nhất/giá trị cao nhất** | — |
| 2 | `youtube_script` | 139 | nhỏ nhất — kiểm chứng ToolSpec | — |
| 3 | `gemini_image` | 310 | nhỏ, cùng nhà cung cấp | — |
| 4 | `plenx` | 2.731 | adapter+runner **sạch nhất**, API thuần | **H10** |
| 5 | `seedance_video` | 5.656 | giá trị thương mại cao nhất, có `cost.py` + `face_detect.py` | **H10** |
| 6 | `gemini_video` | 908 | | H10 |
| sau | `video_chain` → `concat_pro` → `auto_sub_video` | ffmpeg | | H10 + CPU |
| sau cùng | `cut_clip_short`, `video_upscale` | GPU | `requires=("gpu",)` | H10 + GPU |
| **không** | `whisk_nano` + 16 module archive | cookie/browser | Q10 nhóm D — vi phạm điều khoản | — |
| **riêng** | `seedance` (Prompt Studio) | 28.685 | có CSDL + i18n + routes riêng → **là một dự án riêng** | quyết sau |
| **riêng** | `codex` | 2.404 | cho người ngoài chạy code trên máy chủ | Q: sau cùng hoặc không |

---

## 7. Rủi ro và cách chặn

| Rủi ro | Mức | Cách chặn |
|---|---|---|
| Port công cụ xong lại phải mở ra sửa khi làm agent | **cao** | **bắt buộc khai `ToolSpec` ngay ở chặng A0**, trước khi port bất kỳ công cụ nào |
| Copy nhầm hạ tầng JSON của BOT GEMINI sang | cao | quy tắc cứng: **chỉ port `modules/`, `models/*registry*`, `prompts/`, adapter, cost, face_detect** — không port `kernel/`, `storage/`, `job_queue`, `quota_guard`, `user_manager` |
| Vô tình ghi vào `D:\BOT GEMINI` | **rất cao nếu bất cẩn** | chỉ đọc; copy sang LTT rồi mới sửa; đã có test chốt không import chéo |
| Làm công cụ video trước H10 | cao | H10 là **cổng chặn cứng** trước chặng C |
| Agent đốt credit | cao | thiết kế PA-1+: trần ngân sách + cổng duyệt + giữ chỗ theo trần |
| Máy chủ dùng chung với BOT GEMINI (cổng 8000) | trung bình | đã tách cổng 8100 (Q4); không cài đè, không dùng chung `data/` |
| Kho prompt 130 file làm phình repo | thấp | text thuần, vài trăm KB |

---

## 8. Điều thay đổi so với `PHUONG_AN_AGENT.md`

| Trước | Nay | Vì sao đổi |
|---|---|---|
| "Bắt tay xây agent (H12.1→H12.5), ~3–5 tuần" | **Port công cụ trước, agent sau** | kiểm kê cho thấy ta chỉ có **1 công cụ** — agent không có gì để điều phối |
| Verifier `face_identity` là "nâng cấp sau" | **khả thi sớm** | `face_detect.py` đã giải xong phần hạ tầng insightface |
| `params_schema` phải tự thiết kế | **port sẵn** | 2 model registry bên BOT GEMINI đã có `supported_aspects`/`max_count`/`tier`/`is_active` |
| Canvas "hoãn" | **vẫn hoãn, nhưng có điều kiện mở rõ ràng** | quyết sau chặng D, khi đã có công cụ + agent để hiển thị |

Thiết kế agent PA-1+ (kế hoạch có kiểm chứng, executor lặp chứ agent không lặp,
ngân sách trần + cổng duyệt) **giữ nguyên**, chỉ **dời sang chặng D**.

---

## 9. Cần chủ dự án duyệt

1. **Chốt LT-1** (công cụ trước → agent → canvas sau)?
2. **Duyệt A0 trước tiên** — thêm `tools=(ToolSpec…)` vào `AppManifest` (sửa
   `platform_core/registry.py`). Đây là **điều kiện để mọi công cụ port sau không phải
   làm lại**. Theo `AGENTS.md` tôi phải xin duyệt trước khi đụng `platform_core/`.
3. **Chốt danh sách port và thứ tự** ở mục 6 — có đổi ưu tiên nào không?
4. **H10 (R2) đưa lên trước hay sau chặng A?** Nếu bạn muốn video sớm thì H10 phải
   nhảy lên đầu.
5. **Ba module đặc biệt** — `seedance` Prompt Studio (28.685 dòng, là dự án riêng),
   `codex` (rủi ro bảo mật), `whisk_nano` + nhóm cookie (Q10 đã chốt **không** đưa lên):
   giữ nguyên quyết định cũ hay xem lại?
6. **Ghi quyết định mới** vào `QUYET_DINH_NEN_TANG.md`: **Q32** thứ tự công cụ→agent→
   canvas · **Q33** chuẩn ToolSpec agent-ready cho mọi app · **Q34** ranh giới port từ
   BOT GEMINI (nghiệp vụ có, hạ tầng không).
