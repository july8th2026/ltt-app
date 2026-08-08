# UI-RD — Seedance reference map

| Vùng trong ảnh | Ý đồ UX | Tương ứng thật của LTT | Nhận định |
|---|---|---|---|
| Rail trái: Create/Library/Templates/Assets/Settings | chuyển nhanh giữa các không gian | `/taovideo`, `/jobs`, asset history anchor, `/settings` admin | PASS; không dựng Templates giả |
| Composer trái | cấu hình luôn thấy khi xem thư viện | form tạo video hiện có | RESTYLE thành rail/sticky composer trên desktop |
| Model tiles | so sánh Mini/Standard/Fast | `apps.taovideo.models.MODELS` | KEEP, data-driven, không hardcode capability |
| Prompt, translate, prompt history | soạn/tái dùng prompt | textarea + `/translate` + 10 prompt owner-scoped | PASS; không có kho prompt thứ hai |
| Reference slots image/video/audio, handles | điều khiển input multimodal | ba picker + preview local + role/handle; worker dùng cùng `ref_images` | PASS; giữ backend cap 4, không giả cap 12 từ ảnh |
| Duration/aspect/resolution/audio/count/estimate | báo giá trước submit | all present; capability dependent và HTMX estimate | RESTYLE, giữ server estimate/credit truth |
| Main library/status tabs/filter/sort | tìm và quản lý output | owner-scoped 60 job; status/model/aspect/sort | PASS, gồm cancelled/empty |
| Video cards | preview, status, metadata, prompt, actions | output thật, model/time, progress/error, download/remix/upscale/log | PASS |
| Retry/delete/bulk delete | quản trị output | chưa có route/retention contract | DEFER until behavior/credit/storage retention lock |
| Grid/list controls | density theo nhu cầu | localStorage theo browser | PASS, không tạo profile setting giả |

## Layout extraction

Desktop reference is a 3-zone workspace: narrow global rail (~96px), fixed composer
(~370px), fluid result gallery (3 cards). At ≤1024px composer must become a drawer or
above-content panel; at ≤640px one primary flow is preferable: composer then results.
The reference uses red-on-black as an accent system. Its content density is useful, but
native video player/browser controls and real status data remain authoritative.
