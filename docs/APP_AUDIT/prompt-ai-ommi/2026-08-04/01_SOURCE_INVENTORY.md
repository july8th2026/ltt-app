# 01 — Current Truth và kiểm kê nguồn

## 1. Quy mô đã đo

Snapshot chỉ đọc gồm mã Python module, UI Seedance, tài liệu và test Seedance:

| Hạng mục | Số đo |
|---|---:|
| File liên quan (`.py/.js/.html/.md`) | 194 |
| Dòng | 47.665 |
| Python trong module | 112 file |
| Router | 22 file / 261 endpoint |
| Service | 40 file |
| UI | 14 JS + 16 HTML partial |
| Test Seedance | 31 file |
| `CREATE TABLE` | 49 |

Đây là một sản phẩm con lớn, không phải “module nhỏ để copy”. Di trú theo file
sẽ mang theo cả runtime, dữ liệu, auth và giả định vận hành không phù hợp LTT.

## 2. Capability map của module nguồn

### Workspace và nội dung

- Dashboard và recent project.
- Project, brief/kịch bản, project profile.
- Character, background, outfit, pose, style preset.
- Asset library: group/variant, upload, thumbnail, tag, folder, collection,
  favorite/rating, bulk operation, usage history, staging/offline cache.
- Prompt Library: snippet, version, reference, sample/rating.
- Meta Director, placeholder validation, style library.

### AI production

- Preflight, preview prompt miễn phí.
- AI Director: API, bundle không provider, streaming, batch.
- Sinh video-project/scenes từ brief; editor, reorder, prompt history.
- Iteration/feedback/regenerate/cleanup.
- Image template/combo/render/generate, job/version/retry/revert/trash.
- Storyboard framework/pack; split scene; consistency anchors; per-scene và
  composite generation; clone/reorder/version; save-to-library.
- Media binding `@IMG_n/@VID_n/@AUD_n` và handoff sang video.

### Output và vận hành

- Export prompt/checklist/tệp, ZIP/PDF, project package import/export.
- Cost log, budget theo user/global, audit log, event stream.
- Backup, health, vacuum, repair thumbnail, orphan cleanup, trash/retention.

## 3. Những gì có giá trị để chuyển

| Năng lực/tri thức | Cách dùng lại |
|---|---|
| Prompt assembly, placeholder và negative prompt | Copy có chọn lọc vào `apps/prompt_ai_ommi/`, tách template/resource khỏi code |
| Consistency anchors và scene composition | Viết lại thành pure service có schema/test vàng |
| Brief → scene → prompt workflow | Giữ hành vi, thay persistence/identity/job/credit |
| Framework, pack, style, meta prompt mẫu | Di trú tài nguyên sau license/provenance review |
| Export format/checklist | Port pure logic; output qua Storage owner-scoped |
| Import dry-run, version, clone, reorder | Viết lại theo AppProject revision và validation |
| Test vectors/invariant | Chuyển thành golden fixture không chứa dữ liệu người thật/bí mật |

## 4. Những gì tuyệt đối không chuyển nguyên trạng

| Thành phần nguồn | Lý do chặn | Thay bằng LTT |
|---|---|---|
| SQLite `app.db` và 49 bảng riêng | Tạo nguồn dữ liệu thứ hai, không hợp nhiều worker | PostgreSQL + AppProject/Job/Storage hiện có |
| Data/output/cache nằm trong thư mục module | Mất khi release thay app, sai Q28/runtime path | `platform_core.storage` và dữ liệu bền vững |
| `get_current_user`/Bearer context của BOT | Auth khác, dễ tạo đường vòng | `server.auth.session.require_login` |
| `scoping.py` hiện tại | Dùng shared master namespace; mọi user có thể đọc/ghi chung |
  ownership bắt buộc theo `user_id`; published catalog chỉ read/clone |
| API key trong `app_settings` và ghi vào `os.environ` | Secret/lifecycle không an toàn, trùng APIKEYS | Admin `/admin/apikeys`, `api_pool`, masked status |
| `user_budget` USD và `cost_log` riêng | Hai sổ tiền, dễ lệch/charge hai lần | Credit reserve–settle–refund + telemetry LTT |
| `asyncio.create_task`/SSE task map trong web | Job chết khi web restart, không reclaim/idempotent | PostgreSQL Job + worker/heartbeat/retry |
| File path thật trong prompt/handoff | Rò máy chủ, không owner-scoped | Storage key/artifact reference |
| Endpoint maintenance/user purge trực tiếp | Xóa đồng bộ và quyền quá rộng | Admin/operator job, dry-run, audit, retention |
| Provider list/config “có tên” nhưng chưa chứng minh chạy | UI có thể hứa sai capability | Provider registry + live status/capability gate |
| Codex workspace-write làm render provider | Blast radius và quota không hợp SaaS | Provider/job được allowlist; không chạy code tùy ý |

## 5. Blocker nguồn phát hiện bằng đọc code

1. `personal_where()` và `library_where()` đều quy về shared master user.
2. `can_access_owned()` luôn trả `True`.
3. Asset owner checks và collection admin check bị vô hiệu trong single-tenant.
4. Publish/unpublish có thể trở thành sửa chung thay vì clone riêng.
5. Trash tự purge khi mở danh sách; user có endpoint purge-old.
6. Secret setting sống cùng DB module và được đẩy vào process environment.
7. Long-running generation sống trong tiến trình web.

Các test cũ vẫn hữu ích làm nguồn test vector, nhưng tên test “user isolation”
không thể thay bằng chứng code hiện hành. PROMPT AI OMMI phải viết ownership
contract mới và test hai user độc lập từ đầu.

