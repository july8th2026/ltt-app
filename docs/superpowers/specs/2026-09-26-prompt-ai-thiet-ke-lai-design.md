# PROMPT AI — thiết kế lại (spec)

**Ngày**: 26/09/2026 · **App**: `apps/prompt_ai_ommi` · **Trạng thái**: spec chờ chủ dự án chốt

| Nguồn | Đường |
|---|---|
| Bảng đối chiếu + bằng chứng đo được | [`docs/PROMPT_AI/DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md`](../../PROMPT_AI/DOI_CHIEU_PROMPT_SEEDANCE_STUDIO.md) |
| 15 quyết định của chủ dự án | [`docs/PROMPT_AI/QUYET_DINH_26-09.md`](../../PROMPT_AI/QUYET_DINH_26-09.md) |
| Luật vận hành | `docs/00_LTT_OPERATING_CONTRACT.md` · `AGENTS.md` |

---

## 1. Mục tiêu

Biến `apps/prompt_ai_ommi` từ một app **đang trả `503` trên production** thành máy dựng
prompt có ba thứ bản gốc chứng minh là dùng thật: **storyboard**, **vòng lặp iterate**, và
**chỗ nối không mất dữ liệu** sang app sinh video.

**Ngoài phạm vi**: `platform_core/` và `server/` không sửa (quyết định D chọn đường khai
cạnh app→app, không bổ sung hợp đồng nền tảng).

### 1.1 Định nghĩa "xong" cho cả spec

| # | Tiêu chí | Đo bằng |
|---|---|---|
| X-1 | Giao bài sang `taovideo` mang theo **đủ** ảnh tham chiếu + `camera`/`lighting`/`mood` của cảnh | `tests/test_5101_*` — prompt có `@IMAGE_k` mà `refs` rỗng ⇒ test ĐỎ |
| X-2 | 12 meta prompt + 21 image template + 13 snippet của bản gốc chạy được trong PROMPT AI | `tests/test_5401_*` — mọi placeholder trong mọi mẫu đều có người cấp giá trị |
| X-3 | Brief là thực thể riêng, lối vào là 2-pane | `tests/test_5301_*` + kiểm trên `https://app.lttstudios.com` |
| X-4 | 2 lượt iterate đầu mỗi kịch bản miễn phí, lượt 3 trở đi thu credit | `tests/test_5312_*` — bộ đếm nằm trong CSDL, không trong phiên |
| X-5 | `apps/prompt_canh` đã xoá, `character_lock` chạy trong PROMPT AI | `tests/test_5321_*` + `apps/prompt_canh` không còn trong cây |
| X-6 | App chạy được trên production | `LTT_PROMPT_AI_OMMI_ROLLOUT=public` + một lượt tạo prompt thật của `khach1.thu` |

---

## 2. Global Constraints (áp cho MỌI task)

Mọi task ngầm mang toàn bộ mục này. Sao đúng giá trị, không diễn giải lại.

| # | Ràng buộc | Giá trị chính xác |
|---|---|---|
| G-1 | Tiền tố bảng | `ommi_` (khai ở `apps/prompt_ai_ommi/manifest.py:232 table_prefix="ommi"`) |
| G-2 | App chỉ được import 4 module của `server` | `server.deps`, `server.auth.session`, `server.auth.csrf`, `server.templating` (`AGENTS.md` §8.2b) |
| G-3 | App→app | Chỉ cạnh khai tường minh trong `tools/lint_app_contract.py:85 APP_DUOC_DUNG_APP`. Spec này thêm **đúng một** cạnh: `("prompt_ai_ommi", "taovideo")`. ⚠️ Xem G-3b — cạnh có **HAI** đầu phải khai |
| G-3b | ⭐ Khai cạnh là việc **HAI BÊN**, lệch một tên là **gate ĐỎ** | `tools/lint_app_contract.py:381-398` đối chiếu hai chiều: bên gọi khai trong `APP_DUOC_DUNG_APP`, **bên bị gọi phải tự khai `BE_MAT_CONG_KHAI` trong `apps/<slug>/__init__.py`**, và hai tập phải **BẰNG NHAU**. `apps/taovideo/__init__.py` hiện **RỖNG** ⇒ thêm cạnh mà không khai bề mặt là `ERROR` ngay. Bản khai phải là **TUPLE LITERAL**, ⛔ không bọc `frozenset(...)`/`set(...)` — linter đọc bằng `ast.literal_eval` trên cây nguồn, một lời gọi hàm làm hàng rào **im lặng tưởng như app chưa khai gì**. Mẫu để copy: `apps/upscalevideo/__init__.py`. Tập phải khai ở CẢ HAI nơi, đúng từng ký tự:<br>`("apps.taovideo.refs", "normalize_image")`<br>`("apps.taovideo.refs", "image_to_inline")`<br>`("apps.taovideo.refs", "image_role")`<br>`("apps.taovideo.refs", "VALID_IMAGE_ROLES")`<br>`("apps.taovideo.refs", "MAX_INLINE_BYTES")` |
| G-4 | `platform_core` không được biết tên app | Kể cả trong comment/docstring (`test_no_app_slug_is_hardcoded_in_the_platform`) |
| G-5 | Alembic | **MỘT head duy nhất**. Head hiện tại: `edb8b0fc0ac9` (`alembic/versions/20260925_1800_marketplace_piece.py`). 116 revision, chuỗi thẳng |
| G-6 | Tên tệp test | `tests/test_<so>_<ten>.py`, số **không được trùng** (`tools/check_so_test.py` là bánh cóc). Số cao nhất đang dùng: **5000** |
| G-7 | Ghi tệp cấu hình | KHÔNG BOM: `[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))`. `.ps1` thuần ASCII. Không viết Python inline qua PowerShell (`AGENTS.md` §5) |
| G-8 | Việc > vài giây | Đi qua hàng đợi job (`platform_core/job_submit.py:40 submit_with_credit`). Cloudflare cắt upload 100 MB / phản hồi 100 giây |
| G-9 | Tiền | Giữ chỗ → quyết toán → hoàn. `credit.giu_cho()` khi nộp; `credit.quyet_toan(db, user_id, job_id, actual)`; handler **phải ném exception khi lỗi** — trả về êm ru là mất tiền hoàn của khách |
| G-10 | Đổi CSS/JS tĩnh | Cache-bust `?v={{ asset_ver }}`, `server/templating.py:ASSET_VER` |
| G-11 | Đổi giao diện | Kiểm bằng trình duyệt, chốt trên `https://app.lttstudios.com` (loopback bỏ qua Cloudflare) |
| G-12 | Lệnh nặng | Qua `python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`, `-n` ≤ 7. Kiểm `tools\cua_so_yen.py trang-thai` + `tools\tai_may.py` trước |
| G-13 | Trong phiên | Test NHẮM cụm vừa sửa. ⛔ KHÔNG chạy gate — không L1, không L2, không L3. Gate chỉ một lần ở CUỐI PLAN |
| G-14 | `D:\BOT GEMINI` | Kho tham chiếu **CHỈ ĐỌC**. Đọc `.db` phải copy sang scratchpad rồi mở `mode=ro` |
| G-15 | Ngôn ngữ | Chuỗi hiển thị bọc `platform_core.i18n._`. Comment/docstring tiếng Việt, mã ASCII |

---

## 3. Kiến trúc: 5 pha, mỗi pha deploy được riêng

```
Pha 1  CHỖ NỐI ĐÚNG          bindings + refs thật + phép kiểm biên + bật rollout
  │                           ⇒ deploy: khách giao bài sang taovideo không mất ảnh
Pha 2  GIAO BÀI              ommi_handoff + prefill form taovideo + cạnh app→app
  │                           ⇒ deploy: khách sửa tham số trong taovideo rồi tự chạy
Pha 3  LÕI STUDIO            ommi_brief + 2-pane + character_lock + Bundle + iterate
  │                           ⇒ deploy: PROMPT AI mới thành hình; xoá apps/prompt_canh
Pha 4  KHO CHUNG + THƯ VIỆN  chia sẻ bằng mã + nhập 12 meta/21 template/13 snippet
  │                           ⇒ deploy: kho dùng được, nội dung bản gốc đã sang
Pha 5  KHO TÀI NGUYÊN SÂU    dedupe + bulk + ZIP + thumbnail + thùng rác + composite
                              ⇒ deploy: kho tài nguyên ngang bản gốc
```

**Ranh giới deploy**: mỗi pha kết thúc bằng test nhắm xanh → gộp `main` →
`pre-commit run --all-files`. Gate (L1 hoặc L2) chạy **một lần duy nhất ở cuối pha 5**.

---

## 4. Mô hình dữ liệu

### 4.1 Bảng đã có — giữ nguyên

`ommi_resource`, `ommi_resource_variant`, `ommi_tag`, `ommi_resource_tag`,
`ommi_collection`, `ommi_collection_item`, `ommi_resource_usage`, `ommi_meta_prompt`,
`ommi_prompt_snippet`, `ommi_style`, `ommi_prompt_version`, `ommi_storyboard`,
`ommi_scene`, `ommi_scene_version`.

⛔ Mô hình `owner_id IS NULL` = catalog **giữ nguyên**, và hai cột `archived_at` /
`deprecated_at` **không được gộp** (lý do ghi ở `apps/prompt_ai_ommi/tables.py:203-207`).

### 4.2 Bảng mới theo pha

Mọi bảng: `id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)`,
`created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())`.
`owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)` trừ khi nói khác.

#### Pha 1

**`ommi_binding`** — nguồn chân lý `thẻ ↔ variant`. Đây là bảng chữa N-2.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `project_id` | `String(36)`, index, not null | `AppProject.id` |
| `scene_id` | `String(36)`, nullable, index | **id của CẢNH KỊCH BẢN** — xem §4.3. `NULL` = binding cấp project. ⛔ **Không bao giờ** là id khung hình storyboard |
| `tag` | `String(16)`, not null | `@IMAGE_1`, `@VIDEO_2`… (chữ hoa, có `@`) |
| `kind` | `String(8)`, not null | `image` \| `video` \| `audio` |
| `variant_id` | `String(36)`, not null, index | `ommi_resource_variant.id` |
| `position` | `Integer`, not null, default 0 | thứ tự trong cùng `kind` |
| `role` | `String(24)`, not null, default `"reference_image"` | bộ giá trị của `apps/taovideo/refs.py:VALID_IMAGE_ROLES` |

Ràng buộc: `UniqueConstraint("project_id", "scene_id", "tag", name="uq_ommi_binding_tag")`.

#### Pha 2

**`ommi_handoff`** — vé giao bài. Dùng **một lần**, hết hạn 30 phút.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `project_id` / `scene_id` | `String(36)`, not null | cảnh được giao |
| `target_app_slug` | `String(64)`, not null | pha này chỉ `"taovideo"` |
| `payload` | `JSON`, not null | `{prompt, params, refs, tag_map, skipped}` — §6.2 |
| `used_at` | `DateTime(timezone=True)`, nullable | khác `NULL` ⇒ vé đã dùng, từ chối |
| `expires_at` | `DateTime(timezone=True)`, not null | `created_at + 30 phút` |

#### Pha 3

**`ommi_brief`** — Brief thành thực thể riêng (Q-3). Thay việc nhúng trong `AppProject.payload`.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `project_id` | `String(36)`, nullable, index | brief có thể chưa gắn project |
| `title` | `String(200)`, not null | |
| `story_vi` | `Text`, not null, default `""` | nội dung kịch bản, tiếng Việt |
| `goal` / `audience` | `String(300)`, default `""` | |
| `target_duration_sec` | `Integer`, not null, default 15 | 3–600 |
| `target_scenes` | `Integer`, not null, default 3 | 1–20 |
| `aspect_ratio` | `String(8)`, not null, default `"16:9"` | |
| `language` | `String(8)`, not null, default `"vi"` | |
| `style_id` / `meta_prompt_id` / `character_id` / `background_id` | `String(36)`, nullable | |
| `referenced_variants` | `JSON`, default list | danh sách `variant_id` |
| `status` | `String(16)`, not null, default `"draft"` | `draft` \| `locked` \| `generated` |
| `free_iterations_used` | `Integer`, not null, default 0 | **bộ đếm lượt miễn phí (Q-7/H-7)** |
| `archived_at` | `DateTime(timezone=True)`, nullable | |
| `updated_at` | `DateTime(timezone=True)`, `onupdate=func.now()` | |

**`ommi_iteration`** — log mỗi lượt gọi LLM + verdict.

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `brief_id` | `String(36)`, not null, index | |
| `seq` | `Integer`, not null | 1, 2, 3… trong cùng brief |
| `feedback` | `Text`, default `""` | khách nhập gì để sửa |
| `prompt_sent` | `Text`, default `""` | đã render, để tra lại |
| `output` | `Text`, default `""` | JSON LLM trả |
| `job_id` | `String(36)`, nullable | job nền tảng |
| `credit_charged` | `Integer`, not null, default 0 | 0 nếu là lượt miễn phí |
| `was_free` | `Boolean`, not null, default False | |
| `verdict` | `String(10)`, nullable | `NULL` \| `kept` \| `rejected` |

Ràng buộc: `UniqueConstraint("brief_id", "seq", name="uq_ommi_iteration_seq")`.

**`ommi_character`** — khoá nhân vật (gộp `character_lock` của `prompt_canh`, Q-4).

| Cột | Kiểu |
|---|---|
| `name` | `String(160)`, not null |
| `gender` / `age_range` | `String(32)`, default `""` |
| `face_description` / `body_description` / `hair_description` / `outfit_description` | `Text`, default `""` |
| `personality` / `expression_style` / `movement_style` | `Text`, default `""` |
| `fixed_prompt_block` | `Text`, default `""` — khối chữ CHÈN NGUYÊN VĂN vào mọi cảnh |
| `negative_notes` | `Text`, default `""` |
| `reference_variant_ids` | `JSON`, default list |
| `share_level` | `String(12)`, not null, default `"private"` (pha 4 dùng) |
| `archived_at` | `DateTime(timezone=True)`, nullable |
| `updated_at` | `DateTime(timezone=True)`, `onupdate=func.now()` |

**`ommi_outfit`**: `character_id String(36) not null index`, `name String(160)`,
`description Text`, `reference_variant_ids JSON`.

**`ommi_pose`**: `name String(160)`, `description Text`, `pose_block Text`,
`tags JSON`, `reference_variant_ids JSON`, `share_level`.

**`ommi_background`**: `name String(160)`, `location_type String(64)`,
`environment_description Text`, `lighting_description Text`, `color_palette String(200)`,
`camera_feel String(200)`, `important_objects Text`, `fixed_prompt_block Text`,
`negative_notes Text`, `reference_variant_ids JSON`, `share_level`, `archived_at`, `updated_at`.

**`ommi_face_embedding`**: `character_id String(36) not null index`,
`variant_id String(36) not null`, `vector_json JSON not null`, `backend String(32) not null`.

#### Pha 4

**Alter — thêm cột `share_level`** (`String(12)`, not null, `server_default="private"`,
bộ giá trị `{"private", "code", "catalog"}`) vào: `ommi_meta_prompt`,
`ommi_prompt_snippet`, `ommi_style`, `ommi_character`, `ommi_background`, `ommi_pose`,
`ommi_image_template`, `ommi_storyboard_framework`, `ommi_sample`, `ommi_profile`.

⚠️ `share_level="catalog"` **chỉ admin đặt được**. `"code"` là mức khách tự đặt (Q-10).
⛔ Không có trang "kho công khai" trong spec này.

**Alter `ommi_meta_prompt`** thêm:

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `target_format` | `String(24)`, not null, `server_default="gemini_style"` | bộ: `gemini_style` \| `storyboard` |
| `is_default` | `Boolean`, not null, `server_default=false` | mặc định **theo từng `target_format`** |
| `placeholders` | `JSON`, not null, default list | danh sách tên CHỮ HOA — §7 |

Ràng buộc: chỉ một `is_default=true` cho mỗi `(owner_id, target_format)` — ép ở
tầng service (`library.dat_mac_dinh()`), không ở tầng CSDL (owner_id NULL làm
partial index rối).

**Alter `ommi_style`** thêm `parent_id String(36) nullable` và
`provider_overrides JSON default dict`.

**`ommi_share_code`** — chia sẻ bằng mã (Q-10).

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `code` | `String(12)`, unique, not null, index | sinh bằng `secrets.token_urlsafe(8)[:12]` |
| `target_kind` | `String(32)`, not null | `meta_prompt` \| `style` \| `snippet` \| `character` \| `background` \| `pose` \| `image_template` \| `storyboard_framework` \| `sample` \| `profile` |
| `target_id` | `String(36)`, not null | |
| `uses` | `Integer`, not null, default 0 | |
| `max_uses` | `Integer`, nullable | `NULL` = không giới hạn |
| `expires_at` | `DateTime(timezone=True)`, nullable | |
| `revoked_at` | `DateTime(timezone=True)`, nullable | |

**`ommi_image_template`** — 21 mẫu composite của bản gốc (§8.3 báo cáo đối chiếu).

| Cột | Kiểu |
|---|---|
| `name` | `String(200)`, not null |
| `icon` | `String(16)`, default `""` |
| `description` | `Text`, default `""` |
| `prompt_text` | `Text`, not null |
| `n_outputs` | `Integer`, not null, default 1 |
| `aspect` | `String(8)`, default `"1:1"` |
| `asset_type` | `String(16)`, not null | `character` \| `prop` \| `background` |
| `asset_subtype` | `String(32)`, default `""` |
| `grid_layout` | `String(16)`, default `""` — ví dụ `"4x2"` |
| `output_mode` | `String(16)`, default `"grid"` |
| `requires_ref` | `Boolean`, default False |
| `multi_ref_max` | `Integer`, default 1 |
| `bg_style` | `String(64)`, default `""` |
| `negative_lock` | `Text`, default `""` |
| `placeholder_hint` | `String(200)`, default `""` |
| `placeholders` | `JSON`, not null, default list | ⭐ **bổ sung 26/09** — xem §7.2. Đo được: 21 mẫu dùng `{SUBJECT}`, `{STYLE}`, `{EXTRA}`, `{EQUIPMENT}`, **không** dùng bộ của meta prompt. Thiếu cột này thì không kiểm được mẫu nào cần biến gì |
| `is_builtin` | `Boolean`, default False |
| `use_count` | `Integer`, default 0 |
| `share_level` · `archived_at` · `updated_at` | như trên |

**`ommi_storyboard_framework`** — 5 khung của bản gốc.

`name String(200)`, `icon String(16)`, `description Text`, `composite_header Text`,
`composite_rules Text`, `composite_negative_footer Text`, `breakdown_llm_prompt Text`,
`default_style_id String(36) nullable`, `default_aspect String(8)`,
`default_n_scenes Integer`, `is_builtin Boolean`, `use_count Integer`,
`share_level`, `archived_at`, `updated_at`.

**`ommi_sample`**: `title String(200)`, `final_prompt Text`, `style_id String(36) nullable`,
`meta_prompt_id String(36) nullable`, `rating Integer` (1–5), `rating_reasons JSON`,
`used_model String(64)`, `actual_credit Integer`, `iter_count Integer`, `notes Text`,
`share_level`.

**`ommi_profile`**: `name String(160)`, `style_id String(36) nullable`,
`meta_prompt_id String(36) nullable`, `asset_tag_filter JSON`, `share_level`, `archived_at`.

**`ommi_budget`**: `owner_id String(36) unique not null`,
`monthly_cap_credit Integer nullable`, `alert_at_pct Integer default 80`, `updated_at`.

#### Pha 5

**Alter `ommi_resource_variant`** thêm `file_hash String(64) nullable index`,
`favorite Boolean not null server_default=false`, `rating Integer nullable`.

⚠️ `file_hash` là `sha256` của **bytes tệp gốc trước chuẩn hoá**. Dedupe theo
`(owner_id, file_hash)`, **không** theo `file_hash` toàn cục — hai khách tải cùng một ảnh
là hai bản ghi riêng, vì quyền sở hữu khác nhau.

**`ommi_trash`**: `target_kind String(32)`, `target_id String(36)`, `payload JSON`,
`deleted_at DateTime(timezone=True) not null`, `purge_after DateTime(timezone=True) not null`.

**`ommi_image_job`**: `template_id String(36) nullable`, `resource_id String(36) nullable`,
`params JSON`, `job_id String(36) nullable`, `version Integer not null default 1`,
`parent_id String(36) nullable`, `status String(16) not null default "queued"`.

### 4.3 ⭐ HAI thứ đang cùng tên "cảnh" — phán quyết

Bổ sung 26/09. Đo được: app **đã có hai nguồn chân lý** cho khái niệm "cảnh", **không có
khoá liên kết nào** giữa chúng, và cả hai đều có `prompt` + `camera` + `continuity`:

| | `AppProject.payload["scenes"]` | bảng `ommi_scene` |
|---|---|---|
| Thực chất là | **Cảnh kịch bản** — AI Director sinh ra | **Khung hình storyboard** — có `storyboard_id`, `position`, `image_key` |
| Trường | `prompt` (10 000), `negative_prompt`, `camera`, `lighting`, `mood`, `continuity`, `duration_seconds`, `versions` | `prompt`, `camera`, `continuity`, `resource_ids`, `image_key`, `version` |
| Ai đọc | `jobs.py:15`, `project_schema.py:128`, `routes/handoff.py:73`, `routes/projects.py:299`, `routes/assets_catalog.py:90` | `services/storyboard.py`, `services/retention.py:76` |
| Liên kết sang bên kia | **KHÔNG CÓ** | **KHÔNG CÓ** |

⇒ Đây đúng dạng lỗi `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`. Phán quyết:

| # | Luật | |
|---|---|---|
| S-1 | **Cảnh kịch bản là nguồn chân lý duy nhất của prompt đi ra ngoài.** Giao bài, bindings, iterate — tất cả đọc cảnh kịch bản | |
| S-2 | **`ommi_scene` là KHUNG HÌNH storyboard, không phải cảnh.** `prompt`/`camera` của nó là bản **sao phục vụ việc sinh ảnh**, ⛔ không phải nguồn. Pha 3 thêm `canh_id String(36) nullable index` để nói khung hình này vẽ cho cảnh nào | |
| S-3 | `ommi_binding.scene_id` **luôn** là id cảnh kịch bản | pha 1–2: `payload["scenes"][].id`; từ pha 3: `ommi_canh.id` |
| S-4 | ⭐ **Pha 3 tái dùng ĐÚNG id cũ** khi chuyển cảnh kịch bản từ `payload` sang bảng `ommi_canh` — `ommi_canh.id = payload["scenes"][].id`. Nhờ vậy bindings pha 1 **sống sót** qua pha 3 mà không cần di trú | |
| S-5 | ⛔ Không đổi tên cột `ommi_binding.scene_id` | Đổi tên làm plan pha 1/2 phải viết lại, mà ngữ nghĩa thì S-3 đã khoá bằng chữ |

**`ommi_canh`** (pha 3) — cảnh kịch bản, lấy đúng hình dạng `clean_scene()` ở
`apps/prompt_ai_ommi/project_schema.py:70-95`:

| Cột | Kiểu |
|---|---|
| `brief_id` | `String(36)`, not null, index |
| `position` | `Integer`, not null, default 0 |
| `title` | `String(200)`, default `""` |
| `duration_seconds` | `Integer`, not null, default 5 (1–60) |
| `summary` | `Text`, default `""` |
| `prompt` | `Text`, default `""` |
| `negative_prompt` | `Text`, default `""` |
| `camera` / `lighting` / `mood` | `Text`, default `""` — **chữ tự do**, xem §6.2b |
| `continuity` | `Text`, default `""` |
| `selected_version` | `Integer`, not null, default 0 |

Ràng buộc: `UniqueConstraint("brief_id", "position", name="uq_ommi_canh_vitri")`.

⚠️ Vì `id` phải tái dùng được id cũ (S-4), `ommi_canh.id` **không** dùng `default=_uuid`
bắt buộc — chỗ tạo phải cho phép truyền id vào.

---

## 5. Bố cục tệp

### 5.1 Tệp tạo mới

| Tệp | Trách nhiệm |
|---|---|
| `apps/prompt_ai_ommi/services/bindings.py` | Sinh/đọc/đồng bộ `ommi_binding`. **Chỉ** việc thẻ↔variant. ⭐ **Chữ ký công khai — CHỐT 26/09 sau soát liên pha.** Mọi tham số sau `db` là **keyword-only**, và mọi hàm nhận `owner_id` (quyền sở hữu kiểm ở tầng service, không ở route):<br>`list_bindings(db, *, project_id: str, owner_id: str, scene_id: str \| None = None) -> list[OmmiBinding]`<br>`replace_bindings(db, *, project_id: str, owner_id: str, scene_id: str \| None, items: list[dict]) -> tuple[list[OmmiBinding], int]` (đánh số lại toàn bộ theo §6.3; `int` là số bản ghi đổi)<br>`delete_binding(db, *, project_id: str, owner_id: str, scene_id: str \| None, tag: str) -> list[OmmiBinding]`<br>`binding_lines(db, *, project_id: str, owner_id: str, scene_id: str \| None = None) -> list[dict]` (dòng mô tả cho `ASSET_LIST`/`VIDEO_LIST`)<br>`class BindingError(ValueError)` · `class BindingNotFound(LookupError)`<br>⚠️ **Không có `co_binding`.** `has_binding` của §8 suy ra bằng `bool(list_bindings(db, project_id=…, owner_id=…, scene_id=…))`.<br>⛔ Tên tiếng Việt (`doc_bindings`/`dat_bindings`/`co_binding`) trong bản spec đầu là **SAI** — đã bỏ. Soát liên pha 26/09 bắt được: plan pha 1 cài đặt bộ tên trên, plan pha 3 gọi bộ tên kia. |
| `apps/prompt_ai_ommi/services/handoff_stage.py` | Dựng `payload` giao bài (gọi `apps.taovideo.refs`), tạo/tiêu vé `ommi_handoff` |
| `apps/prompt_ai_ommi/routes/bindings.py` | Endpoint bindings |
| `apps/prompt_ai_ommi/services/briefs.py` | CRUD `ommi_brief` + clone + trạng thái |
| `apps/prompt_ai_ommi/routes/briefs.py` | Endpoint brief |
| `apps/prompt_ai_ommi/services/iterate.py` | Vòng lặp regen + verdict + bộ đếm miễn phí |
| `apps/prompt_ai_ommi/routes/iterate.py` | Endpoint iterate |
| `apps/prompt_ai_ommi/services/nhan_vat.py` | `ommi_character`/`outfit`/`pose`/`background`/`face_embedding` |
| `apps/prompt_ai_ommi/routes/nhan_vat.py` | Endpoint nhân vật/bối cảnh |
| `apps/prompt_ai_ommi/services/placeholders.py` | **Bảng quy đổi + bộ kiểm placeholder** (§7) |
| `apps/prompt_ai_ommi/services/bundle.py` | Render meta-prompt KHÔNG gọi LLM (Q-6) |
| `apps/prompt_ai_ommi/services/chia_se.py` | `ommi_share_code`: sinh/đổi/thu hồi/nhận |
| `apps/prompt_ai_ommi/routes/chia_se.py` | Endpoint chia sẻ |
| `apps/prompt_ai_ommi/services/nhap_mau_goc.py` | Nhập 12 meta + 21 template + 13 snippet từ JSON đóng gói |
| `apps/prompt_ai_ommi/prompts/mau_goc/*.json` | Dữ liệu mẫu đã xuất từ bản gốc (ASCII-safe JSON, UTF-8 không BOM) |
| `apps/prompt_ai_ommi/services/dedupe.py` | `file_hash` + gom trùng |
| `apps/prompt_ai_ommi/services/thung_rac.py` | `ommi_trash` |
| `apps/prompt_ai_ommi/services/composite.py` | Sinh ảnh composite theo `ommi_image_template` |
| `apps/prompt_ai_ommi/services/breakdown.py` | Chia cảnh tự động theo `ommi_storyboard_framework` |
| `apps/taovideo/prefill.py` | Đọc vé giao bài → dựng giá trị điền sẵn form. **Không** import `prompt_ai_ommi` |

### 5.2 Tệp sửa

| Tệp | Sửa gì |
|---|---|
| `apps/prompt_ai_ommi/tables.py` | Thêm model mới. ⚠️ Tệp đang 385 dòng — **tách** thành `tables/` (package): `__init__.py` re-export, `tai_nguyen.py`, `thu_vien.py`, `kich_ban.py`, `nhan_vat.py`, `chia_se.py`. Giữ mọi tên lớp cũ để import cũ không vỡ |
| `apps/prompt_ai_ommi/routes/handoff.py` | **Xoá `refs: []`**; dùng `handoff_stage` |
| `apps/prompt_ai_ommi/routes/_shared.py` | Thêm helper `_binding_map()`; giữ `_run_mode()` |
| `apps/prompt_ai_ommi/services/composer.py` | `resource_lines()` đọc từ `ommi_binding`, không tự đánh số |
| `apps/prompt_ai_ommi/routes/__init__.py` | Đăng ký router mới |
| `apps/prompt_ai_ommi/manifest.py` | Giá cho job mới; `tools` cho kho chung (Q-1) |
| `apps/taovideo/routes.py` | Nhận `?tu_studio=<ve>`, gọi `prefill` |
| `apps/taovideo/templates/*` | Điền sẵn form từ vé |
| `tools/lint_app_contract.py:85` | Thêm cạnh `("prompt_ai_ommi", "taovideo")` — xem G-3b |
| `apps/taovideo/__init__.py` | ⭐ **Đang RỖNG.** Thêm `BE_MAT_CONG_KHAI` dạng **tuple literal** với đúng 5 cặp ở G-3b. Không có bước này thì thêm cạnh là gate ĐỎ |
| `frontend/prompt-ai-ommi/src/*` | 2-pane Studio + các màn mới |

### 5.3 Tệp xoá (pha 3, sau khi X-5 xanh)

`apps/prompt_canh/` (toàn bộ) + migration `drop` bảng của nó.

---

## 6. Hợp đồng endpoint

Tiền tố: `/prompt-ai-ommi`. Mọi endpoint ghi: `require_login` + `_csrf(request, body)` +
`_require_run_enabled(user)` nếu tạo job.

### 6.1 Pha 1 — bindings

| Method + Path | Body | Trả |
|---|---|---|
| `GET /api/projects/{pid}/bindings` | — | `{bindings:[{tag,kind,variant_id,position,role,scene_id}]}` |
| `PUT /api/projects/{pid}/bindings` | `{scene_id?, items:[{kind,variant_id,role?}]}` | `{bindings:[...], changed:int}` — **đánh số lại toàn bộ** theo §6.3 |
| `DELETE /api/projects/{pid}/bindings/{tag}` | — | `{bindings:[...]}` |

### 6.2 Pha 2 — giao bài

| Method + Path | Body | Trả |
|---|---|---|
| `POST /api/projects/{pid}/handoff/video` | `{scene_id, model?, resolution?, duration?, generate_audio?}` | `{ticket_id, expires_at, open_url:"/taovideo/?tu_studio=<id>", skipped:[{variant_id,ly_do}], skipped_over_limit:int}` |
| `GET /api/handoff/{ticket}/payload` | — | `payload` (§bên dưới), rồi **đặt `used_at`** |

`payload` (hình dạng cố định — `apps/taovideo/prefill.py` đọc đúng cái này):

```json
{
  "prompt": "<đã renumber @IMG_k>",
  "params": {"model": "seedance-2.0-mini", "resolution": "480p", "duration": 5,
             "aspect_ratio": "16:9", "generate_audio": true,
             "camera": "<từ scene.camera>", "motion": "<từ scene.mood>",
             "visual_style": "<từ style>"},
  "refs": [{"kind": "image", "url": "data:image/jpeg;base64,...",
            "role": "reference_image", "handle": "@IMG_1"}],
  "tag_map": {"@IMAGE_1": "@IMG_1"},
  "skipped": [{"variant_id": "...", "ly_do": "tep khong ton tai"}],
  "skipped_over_limit": 0
}
```

⛔ `params.camera` / `motion` / `visual_style` **phải lấy từ cảnh**, không được ghi đè
cứng `"cinematic"` như `apps/prompt_ai_ommi/routes/handoff.py:44` đang làm (N-1).

### 6.2b ⭐ Enum đóng của `taovideo` — chỗ N-1 dễ bị "sửa" thành mất dữ liệu lần hai

`apps/taovideo/manifest.py:196-198` khai ba trường này là **enum ĐÓNG**, không phải chữ tự do:

| Trường | Bộ giá trị hợp lệ | Mặc định |
|---|---|---|
| `camera` | `""`, `static`, `dolly_in`, `tracking`, `orbit`, `aerial`, `handheld` | `""` |
| `motion` | `""`, `subtle`, `dynamic`, `cinematic` | `""` |
| `visual_style` | `""`, `realistic`, `cinematic`, `anime`, `product` | `""` |

Nhưng `ommi_scene.camera` / `.lighting` / `.mood` do AI Director sinh ra là **chữ tự do
giàu chi tiết** (`"medium shot, 35mm, slow push in"`). Nhét chữ đó vào enum là `422`.

⇒ **Luật bắt buộc, hai đường song song:**

1. **Chi tiết đầy đủ đi vào `prompt`** (chữ tự do, `max_length=10000`). Ghép cuối prompt:
   `Camera: <scene.camera>. Lighting: <scene.lighting>. Mood: <scene.mood>.`
   Đây là nơi thông tin THẬT sống.
2. **Enum chỉ là gợi ý thô**, suy ra bằng khớp từ khoá, ⛔ **không khớp được thì `""`**
   (là giá trị hợp lệ). Không bao giờ đoán một enum khác.

⛔ Sai lầm phải tránh: chỉ khớp enum rồi **bỏ** chữ gốc — đó là vứt trường im lặng lần
thứ hai, đúng con bọ N-1 mà pha này đang chữa. Phép kiểm: prompt gửi đi **phải chứa**
`scene.camera` nguyên văn khi `scene.camera` khác rỗng.

⚠️ `camera` nằm trong `idempotency.key_fields` của `taovideo` (`manifest.py:216`) ⇒ hai
lần giao bài cùng cảnh phải suy ra **cùng một** enum, nếu không job dedupe sẽ tách đôi.
Hàm suy ra phải **tất định**, không dùng LLM, không dùng thứ tự `dict` không xác định.

**Trần**: 9 ảnh + 3 video. Vượt trần: **không lỗi**, cắt bớt và đếm vào
`skipped_over_limit` (giữ đúng hành vi bản gốc, §9 báo cáo đối chiếu).

### 6.3 Luật đánh số thẻ (copy từ bản gốc, đã đo)

1. Hai bộ đếm **độc lập**: `image` → `@IMG_1, @IMG_2…`; `video` → `@VID_1…`.
2. Variant **không còn bản ghi** ⇒ **không tiêu** số.
3. Variant còn bản ghi nhưng **mất tệp** ⇒ **có tiêu** số, và vào `skipped`.
4. Thay trong prompt cả `@IMAGE_k` (dạng của ta) **và** `[Image k]`.
5. Ảnh ép `≤ 8 MiB`, cạnh dài `≤ 2048 px` — gọi `apps.taovideo.refs.normalize_image()` +
   `image_to_inline()`, ⛔ không viết lại.

### 6.4 Pha 3 — brief · bundle · iterate

| Method + Path | Body | Trả |
|---|---|---|
| `GET /api/briefs` | `?archived=&q=` | `{briefs:[...], total}` |
| `POST /api/briefs` | `{title, story_vi, ...}` | `{brief}` |
| `GET/PUT/DELETE /api/briefs/{bid}` | | `{brief}` |
| `POST /api/briefs/{bid}/clone` | — | `{brief}` |
| `POST /api/briefs/{bid}/preflight` | — | `{checklist:[{id,label,passed}], passed:bool}` — **miễn phí** |
| `POST /api/briefs/{bid}/bundle` | `{meta_prompt_id?}` | `{rendered, asset_list, bindings, missing_placeholders:[]}` — **miễn phí (Q-6)** |
| `POST /api/briefs/{bid}/quote` | — | `{credit, free_left:int}` |
| `POST /api/briefs/{bid}/generate` | `{confirmed:bool, feedback?}` | `{confirmed, credit, job_id, iteration_id, was_free}` |
| `POST /api/iterations/{iid}/verdict` | `{verdict:"kept"\|"rejected"}` | `{iteration}` — ⛔ **không hoàn credit** |
| `GET /api/briefs/{bid}/iterations` | — | `{iterations:[...]}` |

**Luật lượt miễn phí (Q-7/H-7)**: `ommi_brief.free_iterations_used < 2` ⇒ lượt này
`credit=0`, `was_free=true`, và **tăng bộ đếm trong CÙNG transaction** với việc tạo
`ommi_iteration`. Lượt 3 trở đi đi qua `submit_with_credit`.
⛔ `verdict="rejected"` **không** hoàn credit — nếu hoàn thì khách bấm rejected mọi lần
là LLM miễn phí vô hạn.

### 6.5 Pha 3 — nhân vật (character_lock)

| Method + Path | Ghi chú |
|---|---|
| `GET/POST /api/characters`, `GET/PUT/DELETE /api/characters/{cid}` | CRUD |
| `POST /api/characters/{cid}/lock` | Gọi LLM dựng `fixed_prompt_block` từ mô tả — **thay bước 1 của `prompt_canh`** |
| `GET/POST /api/characters/{cid}/outfits` | |
| `GET/POST /api/poses`, `GET/POST /api/backgrounds` | |
| `POST /api/backgrounds/{bid}/lock` | Như trên, cho bối cảnh |

### 6.6 Pha 4 — chia sẻ + nhập mẫu

| Method + Path | Ghi chú |
|---|---|
| `POST /api/share` | `{target_kind, target_id, max_uses?, expires_in_days?}` → `{code}` |
| `DELETE /api/share/{code}` | Thu hồi (đặt `revoked_at`) |
| `GET /api/share/{code}` | Xem trước (không clone) |
| `POST /api/share/{code}/nhan` | Clone về tài khoản mình, tăng `uses` |
| `POST /api/library/{kind}/{item_id}/share-level` | ⭐ **bổ sung 26/09** — đặt `share_level`. `"private"`/`"code"`: chủ sở hữu đặt được. `"catalog"`: **chỉ admin**, khách thường ⇒ `403`. Không có endpoint này thì cột `share_level` ở §4.2 không ai đặt được |
| `POST /api/admin/nhap-mau-goc` | Admin: nhập `prompts/mau_goc/*.json` vào catalog. **Idempotent** theo `(target_format, name)` |

### 6.7 Pha 5

| Method + Path | Ghi chú |
|---|---|
| `POST /api/resources/{rid}/variants/bulk` | `{action:"favorite"\|"rating"\|"delete"\|"tag"\|"move"\|"rename", ids:[...], value?}` |
| `POST /api/resources/upload-zip` | Giải nén, dedupe theo `file_hash` |
| `GET /api/trash`, `POST /api/trash/{id}/restore`, `DELETE /api/trash/{id}` | |
| `POST /api/image-templates/{tid}/generate` | Sinh composite; job `taoanh.generate` |
| `POST /api/storyboards/{sid}/breakdown` | Chia cảnh tự động theo framework |

---

## 7. Placeholder: bảng quy đổi + bộ kiểm (H-4)

Bản gốc dùng CHỮ HOA khai tường minh; ta đang dùng chữ thường tĩnh trong
`prompts/director_user.txt`. Bảng quy đổi **duy nhất**, đặt trong
`services/placeholders.py`:

| Placeholder bản gốc | Nguồn giá trị bên ta |
|---|---|
| `TITLE` | `ommi_brief.title` |
| `PROJECT_NAME` | `AppProject.name` (rỗng nếu brief chưa gắn project) |
| `BRIEF_VI` | `ommi_brief.story_vi` |
| `DURATION` | `ommi_brief.target_duration_sec` |
| `SCENES` | `ommi_brief.target_scenes` |
| `ASPECT_RATIO` | `ommi_brief.aspect_ratio` |
| `ASPECT` | đồng nghĩa `ASPECT_RATIO` (mẫu `storyboard` dùng tên này) |
| `STYLE_FULL` | `composer.style_description(style)` |
| `STYLE_POSITIVE` | `ommi_style.body` |
| `STYLE_NEGATIVE` | `ommi_style.negative` |
| `ASSET_LIST` | dựng từ `ommi_binding` kind=`image` (§6.3) |
| `VIDEO_LIST` | dựng từ `ommi_binding` kind=`video` |
| `PROMPT` | prompt của cảnh (mẫu `storyboard`) |
| `REF_NOTE` | ghi chú ảnh tham chiếu của cảnh |
| `CHARACTER_DESCRIPTION` | `ommi_character.fixed_prompt_block` |

**Placeholder tự do**: mẫu `Ông Ngoại` dùng 4 biến không có nguồn hệ thống
(`FACTION_A`, `FACTION_B`, `MIN_COMBAT_DISTANCE`, `NEUTRAL_LIST`). Chúng lấy giá trị từ
`ommi_meta_prompt.placeholders` + một ô nhập cho khách. Nếu khách để trống ⇒ **báo
`missing_placeholders`, không gửi LLM**.

### 7.1 Bộ kiểm bắt buộc

```
kiem_placeholder(body: str, khai_bao: list[str], co_gia_tri: dict) -> list[str]
```

Trả danh sách tên **thiếu**. Ba phép, tất cả phải xanh:

1. **Mọi `{TEN}` xuất hiện trong `body` đều có trong `khai_bao`** — nếu không, mẫu có
   biến mà không ai biết để hỏi.
2. **Mọi tên trong `khai_bao` đều có trong `co_gia_tri`** — nếu không, render ra
   `{BRIEF_VI}` nguyên văn rồi gửi LLM.
3. **Chuỗi trả về không còn cặp `{...}` CHỮ HOA nào** — lưới cuối, bắt cả hai ca trên.

⛔ Phép 3 một mình **không đủ**: mẫu có thể chứa `{}` hợp lệ trong ví dụ JSON. Chỉ khớp
`\{[A-Z][A-Z0-9_]*\}`.

### 7.2 ⭐ Image template dùng bộ placeholder KHÁC — đừng trộn hai bộ

Bổ sung 26/09 sau khi đo trên bản copy CSDL. Bảng §7 ở trên là bộ của **meta prompt**.
21 `image_gen_template` dùng một bộ **hoàn toàn khác**, không giao nhau:

| Placeholder của image template | Nguồn giá trị bên ta |
|---|---|
| `SUBJECT` | mô tả đối tượng: `ommi_character.fixed_prompt_block`, `ommi_background.fixed_prompt_block`, hoặc `ommi_resource.prompt_text` tuỳ `asset_type` |
| `STYLE` | `ommi_style.body` |
| `EXTRA` | ô nhập tự do của khách cho lần sinh này |
| `EQUIPMENT` | mô tả trang bị — `ommi_outfit.description` khi có, ngược lại rỗng |

⚠️ **Hệ quả cho phép kiểm T-2, phải nói rõ để không đo sai câu hỏi:**

| Loại mẫu | Pha nào cấp giá trị | T-2 đo được gì ở pha 4 |
|---|---|---|
| 12 meta prompt | Pha 3 (`services/placeholders.py`) đã có đủ nguồn | **Đo thật**: `kiem_placeholder` trên cả 12, `missing == []` |
| 21 image template | Pha 5 (`services/composite.py`) mới cấp giá trị | **Chỉ đo được TÍNH NHẤT QUÁN CÚ PHÁP**: tập khai bằng tập dùng, không tên lạ |

⛔ Đừng ghi báo cáo pha 4 là "đã kiểm 21 template" mà không nói rõ là kiểm cú pháp —
đó đúng là dạng lỗi `pham-vi-phep-do-hep-hon-loi-tuyen-bo`. Phép đo giá trị thật cho
21 template thuộc **pha 5**, và pha 5 phải chạy lại `kiem_placeholder` đầy đủ trên chúng.

---

## 8. Phép kiểm ở BIÊN (H-3) — điều kiện sống của pha 1

Đây là thuốc cho dạng lỗi `cho-noi-hai-module-vut-truong-im-lang`: đọc sai tên khoá rồi
`continue`, vứt trường im lặng.

Hàm bất biến, gọi ở **đúng một chỗ** — ngay trước khi trả `payload` của vé giao bài:

```
bat_bien_giao_bai(prompt: str, refs: list[dict], skipped: list[dict],
                  *, has_binding: bool = False) -> None
```

⭐ `has_binding` là **sửa lỗi của spec bản đầu**: điều kiện B-5 hỏi "cảnh CÓ binding mà
không sinh được ref nào", và sự thật đó **không nằm** trong ba tham số kia — không có nó
thì B-5 không thể cài đặt được. Tham số keyword-only, mặc định `False` để chỗ gọi cũ
không vỡ; chỗ gọi trong `handoff_stage` **bắt buộc** truyền giá trị thật.

Ném `ValueError` khi:

| # | Điều kiện | Vì sao |
|---|---|---|
| B-1 | `prompt` có `@IMG_k`/`@VID_k` mà `refs` không có `handle` tương ứng, **và** `k` không nằm trong `skipped` | Chính N-1: prompt nhắc ảnh mà ảnh không đi theo |
| B-2 | `refs` có `handle` mà `prompt` không nhắc | Ảnh đi mà không ai dùng — trả tiền cho ảnh vô ích |
| B-3 | Một `handle` xuất hiện hai lần trong `refs` | Đánh số vỡ |
| B-4 | `ref["kind"]=="image"` mà `role` không thuộc `apps.taovideo.refs.VALID_IMAGE_ROLES` | Bên nhận sẽ âm thầm remap về `reference_image` |
| B-5 | `refs` rỗng **và** `skipped` rỗng **và** cảnh có `ommi_binding` | Bindings có mà không sinh được ref nào ⇒ chắc chắn lỗi đường đọc |

⚠️ B-1 **phải** xét `skipped`: ảnh khách xoá là ca hợp lệ, không phải lỗi. Nếu không xét,
phép kiểm sẽ đỏ oan và người ta sẽ tắt nó đi — đúng bài học
`banh-coc-do-cach-go-thay-vi-do-tinh-chat`.

---

## 9. Phân làn cho agent — ai sở hữu tệp nào

**Luật lõi**: một tệp **một chủ**. Làn không được sửa tệp của làn khác; cần thì khai
`Interfaces` và chờ.

### 9.1 Sổ đăng ký dùng chung — ai được ghi

Đây là chỗ các làn va nhau (bài học `so-dang-ky-dung-chung-la-cho-cac-lan-va-nhau`).
Phân chủ dứt khoát:

| Sổ dùng chung | Chủ duy nhất | Luật |
|---|---|---|
| `alembic/versions/` | **Làn M** | ⛔ Làn khác **KHÔNG** tạo tệp migration. Làn khác khai cột cần, làn M viết. Head hiện tại `edb8b0fc0ac9`; mỗi pha **đúng một** migration, `down_revision` nối thẳng theo thứ tự pha |
| `apps/prompt_ai_ommi/manifest.py` | **Làn M** | Giá + `tools`. Làn khác gửi yêu cầu, không tự sửa |
| `apps/prompt_ai_ommi/routes/__init__.py` | **Làn M** | Đăng ký router |
| `apps/prompt_ai_ommi/tables.py` → `tables/` | **Làn M** (tách package ở task đầu pha 1) | Sau khi tách, mỗi làn sở hữu **một tệp con** |
| `tools/lint_app_contract.py` | **Làn M** | Thêm cạnh `("prompt_ai_ommi","taovideo")` |
| Dải số test | bảng §9.3 | ⛔ Không lấy số ngoài dải của mình |
| `tools/check_so_test.moc` | **Không ai** | Chỉ giảm. Không `--accept` khi còn sửa dở của người khác |

### 9.2 Làn theo pha

| Làn | Pha | Sở hữu |
|---|---|---|
| **M** (hạ tầng) | mọi pha | `alembic/versions/`, `manifest.py`, `routes/__init__.py`, tách `tables/`, `tools/lint_app_contract.py` |
| **A** | 1 | `services/bindings.py`, `routes/bindings.py`, `tables/kich_ban.py` (phần `OmmiBinding`), sửa `services/composer.py` |
| **B** | 2 | `services/handoff_stage.py`, sửa `routes/handoff.py`, `apps/taovideo/prefill.py`, sửa `apps/taovideo/routes.py` + template |
| **C** | 3 | `services/briefs.py`, `routes/briefs.py`, `services/bundle.py`, `services/placeholders.py`, `tables/kich_ban.py` (phần `OmmiBrief`) |
| **D** | 3 | `services/iterate.py`, `routes/iterate.py`, `tables/kich_ban.py` (phần `OmmiIteration`) |
| **E** | 3 | `services/nhan_vat.py`, `routes/nhan_vat.py`, `tables/nhan_vat.py`, xoá `apps/prompt_canh/` |
| **F** | 4 | `services/chia_se.py`, `routes/chia_se.py`, `tables/chia_se.py` |
| **G** | 4 | `services/nhap_mau_goc.py`, `prompts/mau_goc/*.json`, `tables/thu_vien.py`, **và `services/library.py::dat_mac_dinh(db, owner_id, meta_prompt_id, target_format) -> None`** (bổ sung 26/09: §4.2 dùng hàm này để ép "một `is_default` cho mỗi `(owner_id, target_format)`" nhưng không làn nào sở hữu) |
| **H** | 5 | `services/dedupe.py`, `services/thung_rac.py`, `tables/tai_nguyen.py`, **và tệp route cho §6.7 phần kho: `routes/resources.py` + `jobs.py`** |
| **I** | 5 | `services/composite.py`, `services/breakdown.py`, **và tệp route cho §6.7 phần mẫu: `routes/library.py` + `routes/storyboard.py`** |
| **J** | 3–5 | `frontend/prompt-ai-ommi/src/*` (toàn bộ). Một chủ cho frontend để tránh xung đột CSS/state |

⚠️ `tables/kich_ban.py` có **ba** làn cùng đụng (A, C, D). Giải: làn M tạo tệp với **ba
khối trống có mốc bình luận** ở task đầu pha 1; mỗi làn chỉ ghi trong khối của mình.
Nếu vẫn thấy rủi ro, tách thành `tables/binding.py`, `tables/brief.py`,
`tables/iteration.py` — ba tệp ba chủ. **Khuyến nghị: tách ba tệp.**

### 9.3 Dải số test — cấp trước, không ai đi xin

Số cao nhất đang dùng: **5000**. Dải 5100–5599 còn trống hoàn toàn.

⭐ Làn M có **một số riêng cho mỗi pha**, không dùng chung dải với làn nghiệp vụ —
nếu không thì migration của pha sau sẽ cắn vào dải của làn khác.

| Làn | Pha | Dải | Ghi chú |
|---|---|---|---|
| M | 1 | 5100–5109 | migration pha 1, tách `tables/`, khai cạnh app (G-3b) |
| A | 1 | 5110–5129 | bindings |
| B | 2 | 5130–5159 | giao bài. ⚠️ `test_5131_bat_bien_giao_bai.py` là **của pha 1** (làn B phần bất biến) — pha 2 bắt đầu từ 5132 |
| M | 3 | **5300** | migration pha 3 (đúng một số) |
| C | 3 | 5301–5319 | brief + bundle + placeholder |
| D | 3 | 5320–5339 | iterate + lượt miễn phí |
| E | 3 | 5340–5369 | nhân vật + xoá `prompt_canh` |
| M | 4 | **5400** | migration pha 4 (đúng một số) |
| F | 4 | 5401–5419 | chia sẻ bằng mã |
| G | 4 | 5420–5449 | nhập mẫu gốc |
| M | 5 | **5500** | migration pha 5 + task GATE cuối cùng |
| H | 5 | 5501–5529 | dedupe + thùng rác + bulk + ZIP |
| I | 5 | 5530–5559 | composite + breakdown |
| J | 3–5 | 5560–5579 | frontend (Playwright) |

⛔ Trước khi tạo tệp test: `python tools/check_so_test.py --list` để chắc số chưa ai lấy.

### 9.4 Thứ tự chạy — cái gì chặn cái gì

```
M(pha1) ──> A ──> B ──> [deploy pha 2]
            │
            └──> M(pha3) ──> C ──┬──> D
                              └──> E ──> [xoa prompt_canh] ──> [deploy pha 3]
                                 J (theo sau C,D,E)
        M(pha4) ──> F ──> G ──> [deploy pha 4]
        M(pha5) ──> H ──> I ──> [deploy pha 5]  ──> GATE (mot lan, mot cap)
```

Song song được: `C ∥ E`, `F ∥ H` (khác pha nhưng khác tệp — chỉ khi làn M đã xong
migration của cả hai pha), `J` theo sau.
⛔ `B` phải chờ `A` (cần `ommi_binding`). `G` phải chờ `F` (cần `share_level`).

---

## 10. Kiểm thử

### 10.1 Cách viết

- `pytest`, một tệp một số, `tests/test_<so>_<ten>.py`.
- ⛔ **Không ghi vào cây** khi test chạy (bài học `viet-phep-kiem-va-bo-do`).
- Test CSDL dùng fixture có sẵn của repo; ⛔ không tự `drop_all` (khoá `postgres_test`).
- Chuỗi tiếng Việt trong assert: so bằng khoá/mã, không so bằng câu hiển thị.

### 10.2 Ba phép không được thiếu

| # | Phép | Vì sao |
|---|---|---|
| T-1 | **Tiêm lỗi cũ**: dựng cảnh có 2 ảnh, gọi giao bài, ép `refs=[]` ⇒ `bat_bien_giao_bai` **phải** ném | Số 0 không có đối chứng không phải phát hiện (`khong-doi-chung-thi-so-khong-khong-phai-phat-hien`) |
| T-2 | **Mọi mẫu, không phải mẫu mẫu**: chạy `kiem_placeholder` trên **cả 12** meta prompt + **cả 21** image template, assert `missing == []` | Bài học `vi-du-trong-loi-nhac-la-menh-lenh-ngam`: sửa theo vài ví dụ làm tụt cái vốn đúng |
| T-3 | **Lượt miễn phí đếm trong CSDL**: 2 lượt free, lượt 3 thu tiền; **khởi động lại session** giữa lượt 2 và 3 ⇒ vẫn thu | Bộ đếm trong phiên là LLM miễn phí vô hạn |

### 10.3 ⭐ Bánh cóc: hai chỗ khai cùng một điều

Bổ sung 26/09. G-3b cho phép `prompt_ai_ommi` dùng đúng 5 tên của `apps.taovideo.refs`
— **không có `manifest`**. Nên bộ enum `camera`/`motion`/`visual_style` ở §6.2b buộc phải
**chép thành literal** trong `prompt_ai_ommi`. Hai chỗ khai cùng một điều, không ai bắt khớp
⇒ `taovideo` thêm một giá trị enum là ta lệch mà không ai biết.

Thuốc: **một phép kiểm nằm NGOÀI cả hai app**, trong `tests/`, nơi import cả hai là hợp lệ
(`.importlinter` cai quản gói `apps/`, không cai quản `tests/`):

```
tests/test_5156_enum_taovideo_khop_hai_ben.py
```

Nội dung: đọc `apps.taovideo.manifest` lấy `params_schema["camera"]["values"]` (và
`motion`, `visual_style`), so **bằng nhau** với literal trong
`apps.prompt_ai_ommi.services.handoff_stage`. Lệch một giá trị ⇒ ĐỎ, kèm thông điệp nói rõ
phải sửa ở đâu.

⚠️ Đây là loại lỗi `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`: cơ học thắng giao ước.
Một dòng bình luận *"nhớ sửa cả hai chỗ"* ⛔ không phải phép kiểm.

### 10.4 Kiểm giao diện

Đổi UI ⇒ Playwright trên `https://app.lttstudios.com`, đăng nhập bằng
`khach1.thu` qua cookie (⛔ không gõ mật khẩu). Kiểm: console errors, failed network
requests, và kết quả trên giao diện thật. Đổi CSS/JS ⇒ cache-bust (G-10).

---

## 11. Rủi ro đã biết

| # | Rủi ro | Giảm thiểu |
|---|---|---|
| R-1 | 8 tính năng xây theo Q-14 không có bằng chứng ai cần (§8.2 báo cáo: 0 dòng ở bản gốc) | Chủ dự án đã chốt. Đặt cuối pha 3/4 để nếu cắt phạm vi thì cắt ở đây trước |
| R-2 | Cạnh `("prompt_ai_ommi","taovideo")` mở tiền lệ; app thứ ba muốn nhận ảnh phải khai cạnh nữa | Giới hạn cạnh ở **đúng một module** `apps.taovideo.refs`. ⛔ Không import `apps.taovideo.routes`/`jobs` |
| R-3 | Nhập mẫu gốc làm hỏng catalog đang có | `POST /api/admin/nhap-mau-goc` idempotent theo `(target_format, name)`; chạy thử trên tài khoản thử trước |
| R-4 | Tách `tables.py` thành package làm vỡ import cũ | `tables/__init__.py` re-export **đủ mọi tên lớp cũ**; một test khẳng định `from apps.prompt_ai_ommi.tables import <moi ten cu>` vẫn chạy |
| R-5 | Ảnh khách tải lên vẫn không đi được nếu quên đường D | B-5 trong §8 bắt đúng ca này |
| R-6 | Bật `ROLLOUT=public` khi pha 3 sẽ đổi lối vào ⇒ khách vừa quen lại phải học lại | Chủ dự án đã chốt bật luôn, và xác nhận chưa có khách thật (Q-11) |

---

## 12. Điều spec này CỐ Ý không làm

| Không làm | Vì |
|---|---|
| Kho asset/media dùng chung ở `platform_core` | Q-1 chọn đường A: kho trong app, mở qua ToolSpec |
| Bổ sung hình dạng tham chiếu thứ ba vào `server/api/uploads.py` | Đã hỏi, chủ dự án chọn đường D |
| Đẩy storyboard sang Seedance Video | Q-12: storyboard chỉ để tham chiếu trong PROMPT AI |
| Hàng đợi nhiều bài ở `taovideo` | Q-13: một bài một lần, y bản gốc |
| Trang "kho công khai" + kiểm duyệt nội dung | Q-10: chia sẻ bằng mã/link |
| Quét thư mục đĩa máy chủ (862 LOC của bản gốc) | SaaS: khách không có đĩa trên máy chủ. Thay bằng upload + ZIP |
| Khách nhập API key riêng | Nền tảng dùng `platform_core/api_pool.py` |
| Kế thừa style nhiều tầng có vòng | Chỉ **một** tầng cha–con; `parent_id` trỏ tới bản ghi **không có** `parent_id` |
