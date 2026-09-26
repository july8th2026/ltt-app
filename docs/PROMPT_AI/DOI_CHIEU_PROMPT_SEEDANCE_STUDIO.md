# Đối chiếu: `apps/prompt_ai_ommi` (PROMPT AI) ⟷ Prompt Seedance Studio (BOT GEMINI)

Ngày lập: 26/09/2026 · Cây: `restore-incomplete-sessions-d63d42` · Trạng thái: **kiểm kê, chưa quyết định thiết kế**

Nguồn đối chiếu (CHỈ ĐỌC): `D:\BOT GEMINI\app\modules\seedance\` (~20 k LOC Python),
`app\ui\static\js\modules\seedance\*.js` (8 508 LOC), `app\ui\templates\partials\seedance\*.html` (6 492 LOC).
Bên ta: `apps/prompt_ai_ommi` (4 919 LOC) + `frontend/prompt-ai-ommi/src` (3 605 LOC) + `apps/prompt_canh` (694 LOC).

> ⚠️ Tỉ lệ khối lượng thô: **~34 500 LOC** (nguồn) so với **~9 200 LOC** (ta). Khoảng cách KHÔNG phải
> "thiếu vài nút" mà là thiếu chiều sâu ở 6/13 miền.

---

## 0. Ba phát hiện nặng nhất (đọc trước khi đọc bảng)

| # | Phát hiện | Bằng chứng | Hệ quả |
|---|---|---|---|
| **N-1** | **Handoff sang app video VỨT SẠCH ảnh tham chiếu.** `refs` luôn là `[]`, không có `image_key`/`image_keys`, `camera=""`, `motion`/`visual_style` bị ghi đè cứng `"cinematic"` | `apps/prompt_ai_ommi/routes/handoff.py:44-45` | Toàn bộ giá trị của Studio (khoá nhân vật/bối cảnh xuyên cảnh) **bị mất ngay tại chỗ nối**. Khách trả credit cho bước dựng prompt rồi nhận video không có nhân vật của mình. Đây đúng dạng lỗi memory `cho-noi-hai-module-vut-truong-im-lang` |
| **N-2** | **Thẻ `@IMAGE_k` được sinh RỒI QUÊN.** `composer.resource_lines()` đánh số `@IMAGE_1…` vào text prompt, nhưng không có bảng nào lưu `thẻ ↔ variant_id` | `apps/prompt_ai_ommi/services/composer.py:29-42`; đối chiếu `bindings` trong `/director/bundle` của nguồn | Prompt nhắc "@IMAGE_2" mà không ai biết đó là ảnh nào ⇒ N-1 không thể sửa bằng cách truyền ảnh bừa; phải có bảng bindings trước |
| **N-3** | **App ĐANG TẮT chạy job trên production — đã đo, không còn là nghi vấn.** `_run_mode()` trả `"off"` khi `LTT_ENV=production` và chưa set `LTT_PROMPT_AI_OMMI_ROLLOUT` | `apps/prompt_ai_ommi/routes/_shared.py:47-65`; đo 26/09 trên `LTTStudioWeb`+`LTTStudioWorker`: `LTT_ENV=production` **có**, `LTT_PROMPT_AI_OMMI_ROLLOUT` **không có** (104 biến/service) | Trang mở được, mọi nút tạo job trả `503`. **App chưa từng phục vụ khách thật** ⇒ được thiết kế lại tự do, không phải di trú bản nháp, và N-1 chưa ai khiếu nại vì chưa ai chạy được |

---

## 1. Bảng check theo MIỀN (13 miền)

Ký hiệu: ✅ có và tương đương · 🟡 có nhưng nông hơn · ❌ chưa có · ➖ cố ý không cần (SaaS đa người dùng)

### 1.1 Studio Kịch bản (AI Director) — *miền trung tâm*

| Hạng mục | BOT GEMINI | Bên ta | TT |
|---|---|---|---|
| Brief là **thực thể riêng** (bảng `briefs`, list/CRUD/clone) | `routes/briefs.py`, `service/brief_manager.py` | Brief nhúng trong `AppProject.payload` — không có danh sách brief, không clone brief | ❌ |
| Layout 2 pane (danh sách brief ⟷ soạn) | `_sd_director.html` + `sd_briefs.js` | Wizard 5 bước (`/classic`) hoặc `ProjectScreen.tsx` | 🟡 |
| **Preflight** kiểm miễn phí trước khi gọi LLM | `POST /director/preflight` | `POST /api/projects/{id}/preview` | ✅ |
| **Bundle** — render meta-prompt + danh sách asset **KHÔNG gọi LLM** để khách tự dán sang ChatGPT/Gemini riêng | `POST /director/bundle` | — | ❌ |
| Báo giá trước khi chạy | (không có, dùng cost cap) | `POST /api/projects/{id}/quote` | ✅ (ta hơn) |
| Gọi LLM dựng prompt | `POST /director/generate` | `POST /api/projects/{id}/generate` → job `prompt_ai_ommi.generate` | ✅ |
| **Streaming** SSE xem prompt chảy ra | `POST /director/generate-stream` | Polling `GET /api/jobs/{id}` | ❌ |
| Một bước "tạo video" (bundle+generate+save bản ghi `prompt_ready`) | `POST /director/create-video` | — | ❌ |
| **Vòng lặp iterate**: regen theo feedback ở cấp cả kịch bản | `POST /director/regen` | Chỉ có version/feedback theo **từng cảnh** (`ommi_scene_version`) | 🟡 |
| **Verdict** kept/rejected + trần 5 lần/video | `POST /iterations/{id}/verdict`, `SEEDANCE_ITER_CAP` | — | ❌ |
| Log mỗi lượt LLM (tokens, cost, feedback) | bảng `ai_iterations` | Sổ credit nền tảng (không theo lượt LLM) | 🟡 |
| **Batch** nhiều brief một lượt (≤50, async, poll) | `POST /director/batch`, `GET /director/batch/{id}` | `manifest._cost` đã tính giá `kind="batch"` nhưng **không có route nào** | ❌ |
| Bảng **bindings** `@IMG_k/@VID_k ↔ variant` là nguồn chân lý | response `/director/bundle` | Sinh thẻ trong text, không lưu (xem N-2) | ❌ |
| Storyboard 1 ảnh từ prompt | `POST /director/storyboard` | `POST /api/scenes/{id}/render` | ✅ |

### 1.2 Kho tài nguyên (Assets)

| Hạng mục | Bên ta | TT |
|---|---|---|
| Nhóm + variant + thứ tự | `ommi_resource` / `ommi_resource_variant` | ✅ |
| Nhãn tự do | `ommi_tag` / `ommi_resource_tag` | ✅ |
| Bộ sưu tập | `ommi_collection(_item)` (bảng có, frontend React chưa gọi) | 🟡 |
| "Dùng ở đâu" chống xoá nhầm | `ommi_resource_usage` (frontend chưa gọi `/usage`) | 🟡 |
| Retention | `services/retention.py` | ✅ |
| **Dedupe theo `file_hash`** | grep `hash|dedupe` trong `services/resources.py` ⇒ **0 kết quả** | ❌ |
| Favorite / rating | — | ❌ |
| Bulk ops (favorite, rating, xoá, chuyển nhóm, gắn tag, đổi tên) | — | ❌ |
| Upload ZIP | — | ❌ |
| Sinh thumbnail | — | ❌ |
| Thùng rác (restore/purge) | — | ❌ |
| Quét thư mục đĩa máy chủ (862 LOC `folder_scanner.py`) | — | ➖ (SaaS: khách không có đĩa trên máy chủ) |

### 1.3 Tạo ảnh / Composite reference sheet — *miền lớn nhất của nguồn (3 269 LOC)*

| Hạng mục | Bên ta | TT |
|---|---|---|
| Sinh ảnh cho tài nguyên | `POST /api/resources/{id}/images/generate`, `/images/from-job` | 🟡 |
| **Template composite** 3 loại (nhân vật / đạo cụ / nền) | — | ❌ |
| Job versioning + revert + retry | — | ❌ |
| Save-to-library | — | ❌ |
| Trash/restore cho job ảnh | — | ❌ |

### 1.4 Storyboard

| Hạng mục | Bên ta | TT |
|---|---|---|
| CRUD cảnh, sắp lại thứ tự | `/api/scenes/{id}` + `reorder` | ✅ |
| Phiên bản từng cảnh + khôi phục + so sánh | `versions`, `restore/{v}`, `compare` | ✅ (ta hơn) |
| Render ảnh từng cảnh + gắn kết quả job | `render`, `attach/{jid}` | ✅ |
| **Breakdown tự động** (chia cảnh từ kịch bản) | — | ❌ |
| **Khung kịch bản mẫu** (`storyboard_framework_manager.py`, 407 LOC) | — | ❌ |
| **To-video**: đẩy CẢ storyboard sang app video một lượt | chỉ `handoff-batch/**image**`, không có video | ❌ |
| Xuất `export.zip` / `export.pdf` | — | ❌ |

### 1.5 Xuất prompt

| Hạng mục | Bên ta | TT |
|---|---|---|
| TXT / MD / JSON | `GET /api/.../export/{fmt}` (MD/JSON/ZIP) | ✅ |
| **Checklist asset** kèm bản xuất | — | ❌ |
| Đóng gói cả project | `snapshot`/`snapshots`/`restore` (khác mục đích) | 🟡 |
| PDF | — | ❌ |
| Frontend React gọi export | Chỉ `/classic` có | 🟡 |

### 1.6 Thư viện prompt

| Hạng mục | Bên ta | TT |
|---|---|---|
| Meta prompt (riêng + catalog, clone, version, publish/deprecate) | `ommi_meta_prompt`, `ommi_prompt_version` — tách `archived_at` vs `deprecated_at` rất đúng | ✅ (ta hơn) |
| Snippet | `ommi_prompt_snippet` | ✅ |
| **Mẫu hay (samples) + rating 1–5** | — | ❌ |
| **Image template** | — | ❌ |
| Tìm/lọc/bulk | 🟡 (cơ bản) | 🟡 |

### 1.7 Phong cách (Styles)

| Hạng mục | Bên ta | TT |
|---|---|---|
| Preset riêng + catalog + clone | `ommi_style` | ✅ |
| **Kế thừa cha–con (`parent_id`)** | grep `parent|inherit|effective` ⇒ **0 kết quả** | ❌ |
| **Xem "effective" sau kế thừa** | — | ❌ |
| **`provider_overrides`** (một style, nhiều engine) | — | ❌ |

### 1.8 Meta Director (template gửi LLM)

| Hạng mục | Bên ta | TT |
|---|---|---|
| Nội dung template + biến | `body` + `variables` (JSON) | ✅ |
| **Placeholder tường minh** `{BRIEF_VI}`, `{DURATION}`… có bộ kiểm | `prompts/director_user.txt` có `{story}`, `{duration}`… nhưng **tĩnh trong code**, meta người dùng không dùng cùng bộ placeholder | 🟡 |
| **`is_default` theo `target_format`** | Chỉ có `purpose` (mặc định `"director"`) | ❌ |
| Dependency tracking chống xoá meta/style đang dùng (`prompt_refs`) | Chỉ có cho resource | ❌ |

### 1.9 Hồ sơ (Profiles)

| Hạng mục | Bên ta | TT |
|---|---|---|
| Gói `(style + meta + bộ lọc asset theo tag)` tái dùng, clone | — | ❌ **thiếu hoàn toàn** |

### 1.10 Chi phí

| Hạng mục | Bên ta | TT |
|---|---|---|
| Sổ tiền | `platform_core/credit.py` (giữ chỗ → quyết toán → hoàn) | ✅ (ta hơn hẳn) |
| `/api/credit`, `/api/metrics` (P95) | có | ✅ |
| **Breakdown theo feature / provider / model / tokens** | — | ❌ |
| **Budget cap tự đặt theo user** | — | ❌ |

### 1.11 Cài đặt

| Hạng mục | Bên ta | TT |
|---|---|---|
| Theme sáng/tối | `GET/PUT /api/preferences` | ✅ |
| Khách nhập API key riêng (Fernet) | dùng `platform_core/api_pool.py` chung | ➖ cố ý |
| Quản lý thư mục đĩa | — | ➖ cố ý |

### 1.12 Trao đổi tài nguyên (Exchange)

| Hạng mục | Bên ta | TT |
|---|---|---|
| Xuất/nhập một resource | `POST /api/import`, export MD/JSON/ZIP | 🟡 |
| **Bundle**: đóng gói CẢ BỘ (style + meta + asset group) để chuyển giữa tài khoản | — | ❌ |

### 1.13 Wizard / lối vào cho người mới

| Hạng mục | Bên ta | TT |
|---|---|---|
| Wizard 5 bước | `/prompt-ai-ommi/classic` — nhưng đang là **UI phụ**, workspace React mới là mặc định | 🟡 |
| Tình trạng frontend React | **chưa gọi**: handoff, handoff-batch, `/api/import`, snapshot/snapshots/restore, unarchive, reorder, `resources/{id}/usage`, `/api/admin/catalog` | 🟡 |

---

## 2. Liên kết app: nguồn làm gì, ta làm gì

| | BOT GEMINI | Bên ta |
|---|---|---|
| Đích | `seedance_video` và `plenx` (PLEN X) | `taovideo` (= Seedance Video; slug KHÔNG được là `seedance`, xem `apps/taovideo/manifest.py:6-8`) và `taoanh` |
| Hợp đồng | `POST /api/{seedance-video\|plenx}/references/import-from-studio` — **nạp REFERENCE vào form** của app đích | `POST /api/projects/{id}/handoff/{image\|video}` — **đặt hàng JOB ngay** qua `ToolSpec` + `submit_with_credit` |
| Payload | `{prompt, bindings:[{tag,kind,variant_id}]}`; server copy file ảnh sang module đích, renumber `@IMG_k` (`service/staging.py`) | `{prompt, model, aspect_ratio, duration, …}` + **`refs: []`** ⇒ mất ảnh (N-1) |
| Nhiều cảnh một lượt | có (storyboard → to-video) | chỉ `handoff-batch/image`, ≤20 cảnh |
| Trần ảnh tham chiếu | PLENX ≤ 7 ảnh; Seedance ≤ 15 s | chưa có khái niệm |

**Khác biệt UX quan trọng**: nguồn *giao bài* (khách xem lại, sửa, rồi mới bấm chạy và trả tiền);
ta *chạy luôn và trừ tiền* (có bước `confirmed=false` báo giá, nhưng khách không được sửa tham số trong app đích).

---

## 3. Hạ tầng nền tảng — cái gì đã có để dựng "kho chung"

| Câu hỏi | Trả lời (đã kiểm) |
|---|---|
| Có kho asset/media dùng chung cấp nền tảng chưa? | **CHƯA.** `platform_core` không có bảng `assets`/media-library nào |
| Cái gì đang dùng chung? | **Ống dẫn, không phải kho**: `platform_core/storage.py` (`put/open/delete/promote` theo `key`), `platform_core/phat_media.py` (HTTP Range — "app giữ quyền, shared giữ đường ống", dòng 35-45) |
| Cơ chế cho output app A thành input app B? | `server/api/uploads.py:314 resolve_upload_reference()` — id artifact `<job>.<field>.<index>`, khoá theo chủ sở hữu + danh sách trắng output |
| Cái gì đang khoá theo app? | `UploadSession` khoá theo `(user_id, app_slug)` (`server/api/uploads.py:349-351`) — vé upload của app A không dùng được ở app B (cố ý) |
| App được import ruột app khác không? | **KHÔNG**, trừ cạnh khai tường minh trong `tools/lint_app_contract.py:85 APP_DUOC_DUNG_APP` (hiện chỉ có `("taovideo","upscalevideo")`) |
| `platform_core` được biết tên app không? | **KHÔNG BAO GIỜ**, kể cả trong comment — `test_no_app_slug_is_hardcoded_in_the_platform` |
| Được sửa `platform_core`/`server` khi nào? | Chỉ khi **bổ sung hợp đồng chung** cho mọi app tương lai, không phải để một app chạy (`docs/03_THEM_APP_MOI.md`, `AGENTS.md` §8) |

⇒ **"Copy Studio Kịch bản sang làm kho chung của nền tảng" đụng trực tiếp vào luật này.** Có ba đường đi
khác nhau về kiến trúc, cần chủ dự án chọn (xem §5).

---

## 4. `prompt_canh` — trùng lặp cần giải quyết

3 bước `character_lock → scene_list → json_prompt` (`apps/prompt_canh/services/kich_ban.py:206-281`),
gọi model tuần tự qua `runtime_noi_bo.luong`. **Trùng ý tưởng** với AI Director của OMMI nhưng
**không chia sẻ code/DB**: không kho tài nguyên, không storyboard ảnh, không handoff.
`lifecycle="development", public=False` — nhưng manifest tự cảnh báo: `public=False` chỉ ẩn trang web,
**tool vẫn bấm chạy được qua agent** (`apps/prompt_canh/manifest.py:86-102`).

Đáng chú ý: bước `character_lock` của `prompt_canh` chính là mảnh mà OMMI đang thiếu
(khoá nhân vật trước khi chia cảnh).

---

## 5. Ba đường kiến trúc cho "kho chung" (chưa chọn)

| | A. Kho trong app, mở qua ToolSpec | B. Nâng kho lên `platform_core` | C. App "kho" riêng biệt |
|---|---|---|---|
| Bảng ở đâu | `ommi_*` giữ nguyên | bảng mới trong `platform_core` | app mới `apps/kho_sang_tao` |
| App khác đọc bằng gì | Public API / ToolSpec của PROMPT AI | import trực tiếp `platform_core` | ToolSpec của app kho |
| Đụng luật nền tảng | Không | **Có** — phải bổ sung hợp đồng chung, `platform_core` không được biết tên app | Không |
| Công | Thấp | Cao | Trung bình |
| Rủi ro | PROMPT AI thành phụ thuộc cứng của mọi app | Sai một lần là sai cho mọi app | Thêm một app phải nuôi |

---

## 6. Việc phải làm trước mọi việc khác (không cần quyết định thiết kế)

| # | Việc | Vì sao không thể hoãn |
|---|---|---|
| 1 | ~~Xác minh `LTT_PROMPT_AI_OMMI_ROLLOUT`~~ — **ĐÃ ĐO 26/09: chưa đặt ⇒ app đang trả `503`**. Việc còn lại: quyết định khi nào bật, và bật ở mức nào (`admin`/`allowlist`/`public`) | App chưa phục vụ khách thật ⇒ mọi tuyên bố "đang sống" trước đây là sai (N-3) |
| 2 | Sửa `refs=[]` + truyền ảnh tham chiếu ở handoff video | Đang mất giá trị cốt lõi và khách vẫn bị trừ tiền (N-1) |
| 3 | Bảng bindings `thẻ ↔ variant` | Điều kiện cần của việc 2 (N-2) |
| 4 | Phép kiểm ở BIÊN handoff: prompt có `@IMAGE_k` mà `refs` rỗng ⇒ **đỏ** | Đúng thuốc cho dạng lỗi `cho-noi-hai-module-vut-truong-im-lang` |

---

## 7. Tổng kết đếm được

| Miền | ✅ | 🟡 | ❌ | ➖ |
|---|---|---|---|---|
| Studio Kịch bản | 3 | 3 | 8 | 0 |
| Kho tài nguyên | 2 | 2 | 7 | 1 |
| Tạo ảnh | 0 | 1 | 4 | 0 |
| Storyboard | 3 | 0 | 4 | 0 |
| Xuất prompt | 1 | 2 | 2 | 0 |
| Thư viện prompt | 2 | 1 | 2 | 0 |
| Phong cách | 1 | 0 | 3 | 0 |
| Meta Director | 1 | 1 | 2 | 0 |
| Hồ sơ | 0 | 0 | 1 | 0 |
| Chi phí | 2 | 0 | 2 | 0 |
| Cài đặt | 1 | 0 | 0 | 2 |
| Exchange | 0 | 1 | 1 | 0 |
| Wizard/FE | 0 | 2 | 0 | 0 |
| **Tổng** | **16** | **13** | **36** | **3** |

---

## 8. BẰNG CHỨNG SỬ DỤNG — đo từ CSDL thật của Studio (26/09)

Phương pháp: copy `app/modules/seedance/data/app.db` (+`-wal`, `-shm`) sang scratchpad, mở
`mode=ro`. **Không chạm bản gốc.** Cảnh báo phạm vi: đây là MỘT cơ sở dữ liệu với **một
`owner_user_id` thật** ⇒ "0 dòng" nghĩa là *chủ dự án chưa bao giờ dùng*, KHÔNG phải
*khách sẽ không dùng*. Đừng đọc bảng này như dự báo nhu cầu khách.

### 8.1 Tính năng ĐƯỢC DÙNG THẬT

| Bảng | Số dòng | Đọc ra điều gì |
|---|---|---|
| `audit_log` | 8 179 | Nhật ký chạy đều |
| `cost_log` | 6 211 | Theo dõi chi phí là tính năng SỐNG |
| `storyboards` | **2 700** | ⭐ Storyboard là việc chính của Studio |
| `prompt_refs` | 1 429 | Dependency tracking được dùng nhiều |
| `ai_iterations` | **767** | ⭐ Vòng lặp iterate/regen là việc thật, không phải trang trí |
| `asset_groups` / `asset_variants` | 233 / 233 | Kho tài nguyên có dùng, quy mô nhỏ |
| `seedance_trash` | 199 | Thùng rác có dùng |
| `briefs` | 98 | Brief là thực thể sống |
| `storyboard_packs` | 62 | Có dùng |
| `image_gen_templates` | **30** (21 mẫu thật + 9 tự sinh) | ⭐ Nội dung có giá trị, xem §8.3 |
| `prompt_snippets` | 21 (13 thật + 8 tự sinh) | Có dùng |
| `meta_prompts` | **12** | ⭐ Nội dung cần chuyển sang, xem §8.3 |
| `image_gen_combos` | 6 | Có dùng, ít |
| `storyboard_frameworks` | 5 | Có dùng, ít |
| `videos_v2` | **2** | ⚠️ Chỉ 2 — bản ghi video nội bộ gần như KHÔNG dùng |

### 8.2 Bảng RỖNG — tính năng đã xây mà chưa bao giờ dùng

| Bảng | Tính năng | Ghi chú |
|---|---|---|
| `project_profiles` | **Hồ sơ (Profiles)** | 0 dòng. §1.9 từng liệt "thiếu hoàn toàn" ⇒ **đừng xây** |
| `characters`, `outfits`, `poses`, `backgrounds` | Hệ nhân vật / trang phục / dáng / bối cảnh có cấu trúc (16/6/7/13 cột) | 0 dòng cả bốn. Thiết kế công phu, chưa ai nhập một dòng |
| `face_embeddings` | Khoá mặt bằng vector | 0 dòng |
| `user_budget` | Budget cap theo user | 0 dòng ⇒ hạ ưu tiên |
| `prompt_history`, `prompt_versions` | Lịch sử prompt | 0 dòng (ta đã có `ommi_prompt_version`) |
| `render_jobs`, `rendered_outputs` | Hàng đợi render riêng của Studio | 0 dòng — nền tảng ta đã có job queue |
| `entity_tags`, `asset_collections` | Nhãn / bộ sưu tập nâng cao | 0 dòng |

`style_presets_v2`: **4 dòng, 2 trong đó là rác test** (`TestStyleW4`, `PutTestStyle`), 2 còn
lại là cùng một style + bản `(imported)`. **`parent_id=None` ở cả 4, `provider_overrides={}`
ở cả 4** ⇒ kế thừa cha–con và ghi đè theo engine **đã xây mà chưa dùng một lần**.
Sửa §1.7: đừng port độ phức tạp này.

### 8.3 Nội dung cần chuyển sang PROMPT AI (chủ dự án yêu cầu 26/09)

**12 meta prompt, tất cả `is_team_published=1`**, hai `target_format`:

| `target_format` | Số | `is_default` | Tên |
|---|---|---|---|
| `gemini_style` | 9 | `Anh Thang` (1 889 ký tự) | `Anh Thang` · `Character reference sheet 4×2` · `Seedance — video phân cảnh` · `Ông Ngoại` (3 010) · `🌀 Flow Omni · Phân cảnh có timecode` · `🌀 Flow Omni · Đơn cảnh liền mạch` · `🎬 Seedance · Phân cảnh có timecode` · `🎬 Seedance · Phân cảnh có timecode + VIDEO` · `🎬 Seedance · Đơn cảnh liền mạch` |
| `storyboard` | 3 | `Storyboard — lưới phân cảnh` | + `thumbnail nhanh (rough)` · `điện ảnh chi tiết` |

**Bộ placeholder chuẩn của nguồn** (CHỮ HOA, khai tường minh trong cột `placeholders`):
`TITLE`, `PROJECT_NAME`, `BRIEF_VI`, `DURATION`, `SCENES`, `ASPECT_RATIO`, `STYLE_FULL`,
`STYLE_POSITIVE`, `STYLE_NEGATIVE`, `ASSET_LIST`, `VIDEO_LIST`; riêng storyboard: `ASPECT`,
`PROMPT`, `REF_NOTE`; riêng reference sheet: `CHARACTER_DESCRIPTION`; mẫu `Ông Ngoại` thêm
4 biến riêng (`FACTION_A`, `FACTION_B`, `MIN_COMBAT_DISTANCE`, `NEUTRAL_LIST`).

⚠️ **Bên ta dùng bộ khác**: `prompts/director_user.txt` là chữ thường, tên khác (`{story}`,
`{duration}`, `{scenes}`, `{aspect}`…) và **tĩnh trong mã**, không phải template người dùng
sửa được. ⇒ Port 12 mẫu này **bắt buộc kèm bảng quy đổi placeholder + bộ kiểm "mọi
placeholder trong mẫu đều có người cấp giá trị"** — nếu không, mẫu render ra chuỗi
`{BRIEF_VI}` nguyên văn rồi gửi cho LLM.

**30 image_gen_template** — 21 mẫu thật: `character` 7 · `prop` 7 · `background` 7 (7/7/7, do 26/09 tren ban copy CSDL)
(ví dụ `👤 Nhân vật — Chỉ nhân vật (8 góc)`, `⚔️ Đạo cụ — Loadout exploded (1×4)`,
`🌳 Ảnh nền — 4 mùa cùng cảnh`). Đây là **nội dung nghiệp vụ**, không phải mã — chuyển sang
được ngay mà không cần port 3 269 LOC của miền Tạo ảnh. 9 mẫu tên `snippet-*` là bản tự sinh,
**không cần chuyển**.

**13 snippet thật**: `action_chase`, `anime`, `cinematic_35mm`, `doc_portrait`, `documentary`,
`drama_dialogue`, `kids_storybook`, `scifi_journey`, `storybook`, và 4 snippet hệ thống
`sb.breakdown.llm_gemini`, `sb.composite.header`, `sb.composite.rules`,
`sb.composite.negative_footer` — đây là **ruột của tính năng breakdown + composite**,
chuyển sang là có sẵn logic chia cảnh.

### 8.4 Cơ chế "khách chia sẻ cho nhau" — nguồn ĐÃ CÓ

Cột `is_team_published` + `owner_user_id` có trên `meta_prompts`, `style_presets_v2`,
`prompt_samples`, `image_gen_templates`, `storyboard_frameworks`, `prompt_snippets`.
Mô hình bên ta (`owner_id NULL` = catalog) **chỉ có 2 mức** (riêng / catalog-admin); nguồn có
3 mức (riêng / chia sẻ / mặc định) ⇒ quyết định 26/09 (khách chia sẻ được cho nhau) cần
**thêm một cột mức chia sẻ**, không phải thêm bảng.

⚠️ **Nghĩa vụ mới đi kèm**: khách publish nội dung cho khách khác thấy ⇒ phải có đường báo
cáo / rút nội dung (ảnh người thật, bản quyền, nội dung cấm). Đây là nghĩa vụ **pháp lý**,
không phải việc kỹ thuật, và nguồn **KHÔNG có** — không bảng report/moderation nào trong 74 bảng.

---

## 9. ⛔ "Vận hành như bên Prompt Seedance Studio" — KHÔNG copy nguyên được

Chủ dự án yêu cầu 26/09: giao bài cho app video vận hành như bản gốc. Đã truy đường mã — bản
gốc chạy được **vì nó cùng một tiến trình và cùng một đĩa**:

| Bản gốc làm gì | Bên ta có làm được không |
|---|---|
| `seedance_video/api.py` gọi `from app.modules.seedance.service import staging` — **import Python trực tiếp** | ❌ `.importlinter` contract `app-doc-lap-voi-nhau` cấm app import ruột app khác; mở phải khai tường minh cả hai chiều trong `tools/lint_app_contract.py:85` |
| `staging.resolve_variants()` đọc thẳng SQLite của Studio, cùng connection | ❌ Mỗi app ta một tiền tố bảng, không đọc bảng của nhau |
| `shutil.copy2` path đĩa tuyệt đối sang thư mục `refs` **cùng ổ đĩa** | ❌ Ta dùng `platform_core/storage.py` (R2/local theo `key`), không có path đĩa chung |
| `sdv_refs.path` là đường dẫn đĩa, phục vụ bằng `FileResponse(path)` | ❌ Phải là storage key, phục vụ qua `platform_core/phat_media.py` |

⇒ **Hành vi** copy được (và nên copy), **đường ống** phải dựng lại trên hợp đồng nền tảng.
Hành vi cần giữ nguyên:

| Hành vi bản gốc | Chi tiết đã đo |
|---|---|
| Trần ảnh | `seedance_video` 9 ảnh + 3 video (tổng 12); `plenx` 7 ảnh. Vượt trần **không lỗi**, cắt âm thầm, trả `skipped_over_limit` |
| Chuẩn hoá ảnh | Mọi ảnh bị ép ≤ 8 MB, cạnh dài ≤ 2048 px (re-encode JPEG) trước khi nạp |
| Renumber | Hai bộ đếm độc lập `@IMG_k` / `@VID_k`; variant đã xoá **không tiêu** số, variant còn bản ghi mà mất tệp **có tiêu** số; client thay cả `@IMG_N` và `[Image N]` trong prompt |
| Sau khi gửi | **Tự điều hướng** sang app video, nạp vào **MỘT form duy nhất** — ⛔ không có hàng đợi. Form đang có dữ liệu ⇒ hỏi ghi đè, đồng ý thì xoá ref cũ |
| Khách sửa được trước khi chạy | prompt, `aspect_ratio` (nếu model hỗ trợ), `duration` (snap về giá trị hợp lệ), từng chip reference (đổi tên handle, xoá, thêm ảnh khác) |
| Lỗi từng phần | Ref mất tệp ⇒ vào mảng `skipped`, các ref khác vẫn nạp, HTTP vẫn 200, **không rollback** file đã copy |
| Thất bại cả request | Client **không xoá** dữ liệu form đang có — "một import thất bại không được phá việc đang làm" |

### 9.1 Sửa lại §1.4 — `storyboard/to-video` KHÔNG gửi sang app video

`POST /seedance/storyboard/{id}/to-video` tạo **1 `VideoV2` + 1 `Brief` nội bộ ngay trong
module seedance**, mọi cảnh "done" thành `SceneV2` con, thời lượng chia đều. Đích là
`/api/seedance/videos/{id}` — **Video Editor nội bộ**, không phải app BytePlus. Ảnh composite
**không được copy**, chỉ nhét path dạng text vào `notes`. Và `videos_v2` chỉ có **2 dòng**
(§8.1) ⇒ đường này gần như không được dùng.

⇒ Đường giao bài THẬT của bản gốc là `sdSendToVideo()` → `import-from-studio`, **một bài một
lần**. Yêu cầu "gửi cả bộ storyboard" của ta là **tính năng MỚI** — bản gốc không có, nên
không thể "làm như bên đó"; phải thiết kế mới.
