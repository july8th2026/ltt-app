# 02 — Capability, vai trò và Information Architecture

## 1. IA dành cho khách hàng

Không bê 14–16 tab ngang cấp của nguồn. Dùng progressive disclosure:

| Khu vực | Nội dung khách thấy |
|---|---|
| **Bắt đầu** | Project gần đây, template khởi đầu, job của tôi, credit hiện có |
| **Studio** | Brief → Director → scene prompt editor; đây là core outcome |
| **Storyboard** | Scene cards/composite, consistency anchors, version, compare |
| **Tài nguyên** | Asset, character, location, prop, style; upload và `@` mention |
| **Thư viện** | Prompt snippet, meta prompt, style, framework: Của tôi / LTT cung cấp |
| **Xuất & lịch sử** | Prompt package, JSON/Markdown/PDF/ZIP, handoff và job/version |
| **Cài đặt cá nhân** | Ngôn ngữ, tỉ lệ mặc định, model trong allowlist, theme, export |

Desktop dùng shell `immersive`; rail icon thu gọn và drawer theo ngữ cảnh.
Mobile chuyển thành one-pane stepper/drawer, không scale nhỏ studio ba cột.

## 2. Ma trận Admin/User

| Năng lực | User | Admin/operator | Quy tắc |
|---|---|---|---|
| Project/brief/scene/storyboard | CRUD của mình | Xem số liệu; không mặc định đọc nội dung | Owner-scoped, optimistic revision |
| Asset/private library | CRUD của mình | Chỉ maintenance metadata/abuse theo audit | Storage key chứa owner; không lộ file path |
| LTT template/style/framework | Đọc và clone | CRUD, publish/unpublish, version | User không sửa bản published tại chỗ |
| User template/style | CRUD riêng | Không chiếm ownership | Muốn chia sẻ phải qua moderation |
| Provider/model | Chọn model được phép | Key, routing, active model, health | User không thấy key/base URL bí mật |
| Preview/quote | Xem prompt + giá trước | Cấu hình bảng giá/markup ở platform | Quote server-authoritative |
| Generate/regen/batch | Chạy job của mình | Kill switch, retry vận hành | Hold trước provider, settle/refund một lần |
| Cost | Credit/chi phí của mình | Tổng hợp theo app/provider/model | Không mang `user_budget` USD từ nguồn |
| Export/import | Dữ liệu của mình, import dry-run | Policy/limit/retention | ZIP bomb/path traversal/schema validation |
| Trash/restore | Soft-delete/restore của mình | Retention job + legal/abuse hold | Không purge chung khi mở trang |
| Audit/telemetry | Activity của mình | Aggregated ops, không hiện prompt mặc định | Redact PII/prompt/secret |
| Backup/vacuum/orphan cleanup | Không | Admin job có dry-run | Không chạy sync trong HTTP request |
| API keys/global setting | Không | Existing LTT admin | Không tạo Settings bí mật trong app |

Giai đoạn đầu chỉ có role platform `admin`; “curator” là một permission tương
lai, không tạo role giả trong UI. Admin chịu vai trò curator cho catalog LTT.

## 3. Phân loại 14 nhóm nguồn

| Nhóm nguồn | Quyết định | Đích |
|---|---|---|
| Dashboard | RESTYLE | Bắt đầu, chỉ số owner-scoped |
| Projects | KEEP+REWRITE | AppProject project root |
| Assets | KEEP+REWRITE | Tài nguyên riêng + Storage |
| Brief | KEEP | Bước 1 Studio |
| Director | KEEP+REWRITE | Bước 2; Job/credit/provider LTT |
| Editor | MERGE | Bước 3 Studio, scene cards + inspector |
| Storyboard | KEEP+EXTEND | Workspace riêng, version/compare |
| Image Gen | INTEGRATE | Gọi năng lực Tạo ảnh LTT qua job contract |
| Prompt Library | KEEP | Private + published clone-only |
| Styles | MERGE | Tab trong Thư viện/Tài nguyên |
| Meta Director | ADMIN+ADVANCED | Admin catalog; user clone/override riêng |
| Export | KEEP+EXTEND | Prompt package + handoff owned refs |
| Cost | REPLACE | Credit UI chung; admin metrics chung |
| Settings/Maintenance | SPLIT | User preferences vs platform admin/ops |

## 4. Core workflow bắt buộc

`Tạo project → nhập brief/asset → preflight → xem prompt và quote → duyệt →
Job Director → chỉnh scene/version → storyboard/ảnh tham chiếu → export hoặc
handoff sang Tạo ảnh/Tạo video → theo dõi job → kết sổ credit`.

Mọi nhánh lỗi phải giữ project và input, cho retry idempotent, báo phí đã hoàn
hay đã quyết toán; không có nút “Tạo” nào chỉ làm UI giả.

