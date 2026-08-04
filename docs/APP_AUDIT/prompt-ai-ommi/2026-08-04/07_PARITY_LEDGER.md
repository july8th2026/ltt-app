# 07 — Parity ledger sau replatform

Ledger này phủ 100% 22 router file nguồn; số endpoint 261 là baseline AST đã đo
ở H19.0. Disposition áp dụng cho toàn bộ endpoint trong router tương ứng. Không
endpoint nguồn nào được coi là API tương thích trực tiếp.

| Router nguồn | Disposition | Đích PROMPT AI OMMI |
|---|---|---|
| assets (33) | MERGE | resources owner-scoped + Storage upload; library riêng nằm trong project |
| briefs (6) | KEEP | schema `brief`, CRUD theo AppProject revision |
| collections (8) | MERGE | project/resource groups; published catalog clone-only |
| cost (15) | REPLACE | registry quote + credit hold/settle/refund chung |
| dashboard (5) | MERGE | project rail + Jobs chung |
| director (9) | KEEP | preview miễn phí + durable `prompt_ai_ommi.generate` |
| exchange (5) | REPLACE | ToolSpec handoff ảnh/video, không import chéo |
| export (19) | MERGE | JSON/Markdown/ZIP versioned; import tạo bản mới |
| folders (6) | DEFER | chưa có user-value đủ lớn để thêm cây thư mục v1 |
| image_gen (29) | REPLACE | `image.generate` của app Tạo ảnh, quote/confirm riêng |
| iterations (4) | MERGE | scene versions + snapshot/revision; regenerate riêng còn backlog |
| maintenance (8) | ADMIN/REJECT | health read-only; purge/vacuum/repair trực tiếp bị loại |
| meta_prompts (12) | MERGE | catalog resource có provenance; admin publish |
| projects (6) | KEEP | CRUD/clone/archive/unarchive/snapshot/restore |
| prompt_library (19) | MERGE | built-in catalog + published admin catalog; private data trong project |
| settings (5) | REJECT/REPLACE | key/provider ở APIKEYS; app chỉ giữ theme owner-scoped |
| storyboard (38) | KEEP/MERGE | scene/anchor/board/frame batch + ToolSpec image jobs |
| styles (11) | MERGE | catalog style + custom style per project |
| tags (8) | DEFER | search/project resource trước; tag CRUD chưa đủ giá trị v1 |
| trash (6) | MERGE/ADMIN | archive/unarchive; purge tự động phía user bị loại |
| videos (10) | REPLACE | `video.generate` của Seedance qua ToolSpec |
| routes/__init__ | REPLACE | manifest discovery của LTT |

## Handoff contract đã chứng minh

PROMPT AI OMMI chỉ gọi `discover_tools` → `validate_tool_params` →
`submit_with_credit`; `owner_id` do server gắn. Ảnh đi tới `image.generate`,
video tới `video.generate`. Capability model được chuẩn hóa trước validate;
quote trả trước, chỉ submit khi `confirmed=true`. Không sửa `platform_core`.

## Provenance

Không copy runtime, DB, user data hay secret từ BOT GEMINI. Tài nguyên mới trong
`apps/prompt_ai_ommi/prompts/` được viết lại từ capability contract; nguồn BOT
GEMINI chỉ dùng read-only để đối chiếu hành vi.

