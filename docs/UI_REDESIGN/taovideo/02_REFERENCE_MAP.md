# UI-RD — Seedance reference map

| Vùng trong ảnh | Ý đồ UX | Tương ứng thật của LTT | Nhận định |
|---|---|---|---|
| Rail trái: Create/Library/Templates/Assets/Settings | chuyển nhanh giữa các không gian | `/taovideo`, `/jobs`, `/settings`; chưa có template/asset library | chỉ link tới route thật; template/asset library cần quyết định riêng |
| Composer trái | cấu hình luôn thấy khi xem thư viện | form tạo video hiện có | RESTYLE thành rail/sticky composer trên desktop |
| Model tiles | so sánh Mini/Standard/Fast | `apps.taovideo.models.MODELS` | KEEP, data-driven, không hardcode capability |
| Prompt, translate, prompt history | soạn/tái dùng prompt | textarea + `/translate`; chưa có history | translate KEEP; history phải BUILD với retention/privacy |
| Reference slots image/video/audio, handles | điều khiển input multimodal | upload `ref_images`; worker đã hỗ trợ kind/role/handle nhưng UI chưa expose role/handle | EXTEND UI, không cần runtime mới |
| Duration/aspect/resolution/audio/count/estimate | báo giá trước submit | all present; capability dependent và HTMX estimate | RESTYLE, giữ server estimate/credit truth |
| Main library/status tabs/filter/sort | tìm và quản lý output | owner-scoped 12 jobs, status/progress/result; chưa có query/filter | BUILD additive read model/query |
| Video cards | preview, status, metadata, prompt, actions | video player/download and status exist; params/result not supplied to template | EXTEND job view DTO; preview only output thật |
| Retry/delete/bulk delete | quản trị output | chưa có route/retention contract | DEFER until behavior/credit/storage retention lock |
| Grid/list controls | density theo nhu cầu | no persisted preference | visual-only client preference possible after decision |

## Layout extraction

Desktop reference is a 3-zone workspace: narrow global rail (~96px), fixed composer
(~370px), fluid result gallery (3 cards). At ≤1024px composer must become a drawer or
above-content panel; at ≤640px one primary flow is preferable: composer then results.
The reference uses red-on-black as an accent system. Its content density is useful, but
native video player/browser controls and real status data remain authoritative.
