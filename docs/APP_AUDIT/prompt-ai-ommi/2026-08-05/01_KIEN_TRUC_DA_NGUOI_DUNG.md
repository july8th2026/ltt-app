# 01 — Kiến trúc: giữ cấu trúc vận hành, đổi mô hình sở hữu

Yêu cầu của chủ sản phẩm: **giữ nguyên cấu trúc vận hành của module, gọi ra đầy
đủ tính năng, khác duy nhất là mỗi người dùng có kho tài nguyên riêng và prompt
meta riêng.**

Tài liệu này biến câu đó thành thiết kế kiểm chứng được.

## 1. Nguyên tắc bất di bất dịch

1. **Không sửa `platform_core/` hay `server/`.** Nếu thấy buộc phải sửa thì dừng
   và báo — đó là dấu hiệu hợp đồng app còn thiếu (CLAUDE.md).
2. **Không copy runtime, DB, auth, secret từ BOT GEMINI.** Chỉ đọc để đối chiếu
   hành vi. Logic thuần và tài nguyên có provenance thì viết lại.
3. **Mọi truy vấn đều lọc theo `owner_id`.** Không có `master_user_id`, không có
   namespace dùng chung. Đây là điểm khác nguồn quan trọng nhất.
4. **Tiền đi qua credit của nền tảng.** Không dựng `cost_log`/`user_budget`
   thứ hai. Nguồn có hai bảng đó; ta loại bỏ.
5. **Provider/API key đi qua APIKEYS.** Không có trang settings nhập key.

## 2. Ba tầng dữ liệu — thay cho `scoping.py` của nguồn

Nguồn có ba tầng trên giấy nhưng thực thi thành một. Ta làm ba tầng thật:

| Tầng | Ai thấy | Ai sửa | Dùng cho |
|---|---|---|---|
| **PRIVATE** | chỉ chủ sở hữu | chỉ chủ sở hữu | Kho tài nguyên, prompt meta, phong cách riêng, project, storyboard |
| **CATALOG** | mọi người (read-only) | chỉ admin | Meta prompt mẫu, phong cách mẫu, khung storyboard mẫu |
| **CLONE** | — | — | Người dùng bấm "Dùng mẫu này" → tạo **bản sao PRIVATE**, sửa thoải mái |

Không có tầng "team shared" ở v1. Nguồn có nó (`is_team_published`,
`owner_user_id NULL`) nhưng LTT là SaaS bán cho khách lẻ — chia sẻ chéo giữa
người lạ là lỗ hổng, không phải tính năng. Nếu sau này cần team thì thêm
`workspace_id`, và phải qua giao thức đổi quyết định.

**Kiểm chứng bắt buộc:** mỗi bảng PRIVATE phải có test "user B gọi ID của user A
→ 404" (không phải 403, để không lộ sự tồn tại của bản ghi).

## 3. Ánh xạ 49 bảng nguồn → lược đồ đích

Không bê 1-1. Gom theo miền và bỏ thứ nền tảng đã có.

### 3.1 GIỮ — Kho tài nguyên (yêu cầu lõi của chủ sản phẩm)

| Bảng đích | Gộp từ nguồn | Ghi chú |
|---|---|---|
| `ommi_resource` | `asset_groups`, `characters`, `backgrounds`, `outfits`, `poses` | Một bảng, phân biệt bằng `kind` (character/background/prop/vehicle/misc — đúng 5 nhóm trong ảnh tham chiếu) |
| `ommi_resource_variant` | `asset_variants` | Ảnh biến thể, khoá vào Storage qua `storage_key` |
| `ommi_resource_tag` | `asset_tags`, `asset_group_tags`, `tags`, `entity_tags` | Gộp 4 bảng thành 1 quan hệ |
| `ommi_collection` + `ommi_collection_item` | `asset_collections`, `asset_collection_groups` | |

**Loại bỏ:** `face_embeddings` (dữ liệu sinh trắc — cần quyết định riêng về
quyền riêng tư, không đưa vào v1), `resource_folders` (Q65 đã DEFER cây thư mục).

### 3.2 GIỮ — Prompt & Meta (yêu cầu lõi)

| Bảng đích | Gộp từ nguồn | Ghi chú |
|---|---|---|
| `ommi_meta_prompt` | `meta_prompts` | **Có `owner_id`.** Bản admin publish thì `owner_id = NULL` + `is_catalog = true`, chỉ đọc |
| `ommi_prompt_snippet` + `ommi_prompt_version` | `prompt_snippets`, `prompt_versions`, `prompt_samples`, `prompt_history` | Versioning giữ nguyên tinh thần nguồn |
| `ommi_style` | `style_presets`, `style_presets_v` | PRIVATE + CATALOG |

### 3.3 GIỮ — Project & Storyboard

| Bảng đích | Gộp từ nguồn |
|---|---|
| `ommi_project` (dùng `AppProject` của nền tảng) | `projects`, `project_profiles`, `briefs` |
| `ommi_scene` + `ommi_scene_version` | `scenes`, `scenes_v`, `ai_iterations` |
| `ommi_storyboard` + `ommi_storyboard_scene` | `storyboards`, `storyboard_scenes`, `storyboard_scene_versions`, `storyboard_packs`, `storyboard_composite_versions` |
| `ommi_framework` | `storyboard_frameworks` — CATALOG |

### 3.4 THAY bằng năng lực nền tảng — không dựng lại

| Bảng nguồn | Thay bằng |
|---|---|
| `cost_log`, `user_budget` | Sổ credit của nền tảng (Q31/H9) |
| `app_settings` (API key, master uid) | APIKEYS (H8) + preferences owner-scoped |
| `image_gen_jobs`, `render_jobs`, `batch_jobs`, `batch_items`, `rendered_outputs`, `image_gen_job_versions` | Hàng đợi Job của nền tảng (H2) + ToolSpec `image.generate` |
| `audit_log` | Log nền tảng |
| `seedance_trash` | `archived_at` trên chính bản ghi |
| `videos_v` | ToolSpec `video.generate` |

### 3.5 LOẠI HẲN

`image_gen_templates`, `image_gen_combos` (đặc thù UI cũ), `prompt_refs` (thay
bằng khoá ngoại thật), `db_migration`, `user_seeder`, `folder_scanner` (quét thư
mục máy chủ — vô nghĩa và nguy hiểm trong SaaS đa người dùng),
`library_maintenance` / `library_health` (purge/vacuum trực tiếp — Q65 đã REJECT).

**Kết quả: 49 bảng → 12 bảng.** Không mất năng lực nào chủ sản phẩm yêu cầu;
phần cắt là hạ tầng nền tảng đã có hoặc thứ không hợp mô hình SaaS.

## 4. Vì sao phải bỏ JSON blob hiện tại

App hiện tại nhét cả project vào một JSON trong `AppProject`. Không thể xây tiếp
trên đó, vì:

- Kho tài nguyên cần **dùng chung giữa nhiều project** — JSON theo project thì
  mỗi project một bản sao, sửa một chỗ không lan sang chỗ khác.
- Prompt meta riêng cần **tồn tại độc lập với project**.
- Không truy vấn được: "tài nguyên nào đang dùng ở bao nhiêu project" — chính là
  con số ảnh tham chiếu hiển thị.
- Không phân trang được kho 178 tài nguyên.

**Đường di trú:** JSON hiện tại vẫn đọc được. Viết migration một chiều đọc blob
cũ, tách ra bảng mới, giữ `AppProject` làm con trỏ. Người dùng hiện tại (nếu có)
không mất dữ liệu. Cần kiểm: hiện production có project OMMI thật nào chưa.

## 5. Ranh giới với các app khác

Giữ đúng Q65: OMMI **không tự sinh ảnh/video**. Nó gọi
`discover_tools → validate_tool_params → submit_with_credit`; ảnh đi tới
`image.generate` của app Tạo ảnh, video tới `video.generate` của Seedance.
Màn "Tạo ảnh" trong ảnh tham chiếu là **giao diện đặt hàng + xem kết quả**, không
phải một engine thứ hai.

## 6. Rủi ro đã nhận diện

| Rủi ro | Mức | Cách chặn |
|---|---|---|
| Rò rỉ tài nguyên giữa khách hàng | **P0** | Mọi query lọc `owner_id`; test cross-user 404 cho từng endpoint; lint hợp đồng app |
| Upload ảnh nặng vượt giới hạn Cloudflare 100 MB | P1 | Presigned R2 (H10), không upload qua origin |
| Sinh ảnh hàng loạt vượt 100 giây | P1 | Bắt buộc qua hàng đợi job, không làm đồng bộ |
| Kho lớn làm chậm trang | P2 | Phân trang + index `(owner_id, kind)` từ đầu |
| Ảnh tham chiếu là E0 | P2 | Không suy ra backend từ ảnh; mọi số liệu dashboard phải có nguồn thật |
