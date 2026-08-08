# 02 - Journey và control registry

## Journey chung A-Z

`Discover -> chọn tool -> hiểu trạng thái -> nhập dữ liệu -> validate -> quote ->
confirm -> upload/submit -> queue -> progress -> result -> download/remix ->
history -> retry/cancel/support`

| Screen/control | Hiện trạng | Trạng thái audit | Acceptance chính |
|---|---|---|---|
| Marketplace card | chỉ CTA mở app; click vùng còn lại không có contract rõ | PARTIAL/MISLEADING theo user report | toàn card mở app bằng click/Enter/Space; control con không kích hoạt card |
| Icon cover | icon lớn ở giữa ảnh + icon cạnh tên | REDUNDANT | bỏ icon giữa cover; giữ một nhận diện nhỏ nhất quán |
| Category chips | danh sách cố định trong template | PARTIAL | category lấy từ manifest; không hardcode slug |
| Lifecycle chips | chưa có contract | MISSING | `released/development/maintenance/internal/retired`, nhãn và màu thống nhất |
| Kịch bản card/header | public và live | REDUNDANT | biến mất khỏi customer surface; Agent Text vẫn hoạt động |
| Demo card/header/direct URL | public false nhưng customer auth mặc định vẫn thấy | MISLEADING | admin-only diagnostic, customer 404 |
| Media Tools | runtime app có tên customer | REDUNDANT | runtime-only, không card/header/search |
| Job history | global `/jobs` + nhiều list riêng | PARTIAL | cùng API/query, filter app/status/date, cursor pagination |
| Job detail | trạng thái hiện tại, artifact, retry/cancel | PARTIAL | thêm timeline public, correlation ID, lineage, log support phù hợp role |
| Internal debug log | log process phân tán | MISSING | structured event có redaction, retention, metric và trace |
| AutoSub Studio | feature flag có thể trả legacy | BROKEN/version drift | production bundle/hash/flag khớp, browser journey mới PASS |
| Upscale FPS switches | hai option bật đồng thời | MISLEADING | mutual exclusion cả client và server; quote/result phản ánh state thật |
| Upscale compare divider | chỉ range dưới kéo được | BROKEN | drag/pointer/keyboard trực tiếp trên divider; hai vị trí luôn khớp |
| Upscale video sync | sync ở play/pause/seeking, không drift correction | PARTIAL | một master timeline; seek/play/rate/end/duration đồng bộ trong tolerance |
| Upscale queue | list cố định, thumb placeholder | PARTIAL | filter/status/sort/list-grid/preview thật và empty state |
| Upscale download | streaming inline, chưa có attachment contract | PARTIAL | endpoint download trả `Content-Disposition: attachment`, filename an toàn |

## Quy ước log theo role

- Customer thấy timeline dễ hiểu: đã nhận file, đang chờ, đang xử lý bước nào,
  hoàn tất/lỗi, credit được giữ/quyết toán/hoàn, CTA retry/cancel.
- Admin/support thấy thêm: event code, attempt, worker, GPU UUID rút gọn,
  provider/model alias, latency, correlation ID và metadata đã lọc.
- Không ai được thấy secret, token, raw credential, đường dẫn bí mật hoặc dữ liệu
  tenant khác. Prompt/media nhạy cảm không được chép nguyên vào log.

