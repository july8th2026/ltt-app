# 05 - Findings

| ID | Sev | Finding/root cause | Phương án và acceptance |
|---|---|---|---|
| F01 | P0 | Xóa Kịch bản/Media sẽ làm gãy Agent vì đang sở hữu ToolSpec runtime | soft-retire surface trước; test tool registry và Agent graph không đổi |
| F02 | P1 | `public=False` chỉ ẩn anonymous; customer đăng nhập mặc định vẫn thấy Demo/Media/Social | thêm contract audience/surface từ manifest, route guard theo audience |
| F03 | P1 | `Job` chỉ giữ snapshot cuối, không có event timeline | `JobEvent` append-only dùng chung, role-aware, redacted |
| F04 | P1 | Card không phải một control thống nhất; icon cover lặp; metadata `cần: api/gpu` hướng dev | card-link accessible, bỏ icon giữa, bỏ metadata kỹ thuật khỏi customer |
| F05 | P1 | Category cứng trong template và badge `MỚI` không biểu diễn lifecycle | taxonomy + lifecycle trong manifest, không hardcode app slug |
| F06 | P1 | Thumbnail và Tạo ảnh là hai UI dù cùng JTBD ảnh | một shell Tạo ảnh AI với mode General/Thumbnail; backend job cũ giữ tương thích |
| F07 | P1 | AutoSub production default legacy nếu thiếu rollout env | preflight bundle/hash/flag, canary browser, sau đó chuyển public có rollback |
| F08 | P1 | Upscale cho bật preserve FPS và smooth 2x cùng lúc; server cũng nhận cả hai | mutual exclusion UI + server normalize/reject + quote test |
| F09 | P1 | Compare divider không draggable; hai video dễ drift; range tách khỏi divider | pointer capture + keyboard slider + master clock và drift correction |
| F10 | P1 | Queue Upscale thiếu filter/view/thumbnail; download chưa có attachment endpoint | filter/sort/grid/list, thumbnail thật, download response contract |
| F11 | P1 | “32 GB GPU” là 2x16 GB, không phải một pool 32 GB | mỗi job <= budget một card; tận dụng throughput 2 worker/2 lease, đo trước khi tăng concurrency |
| F12 | P2 | Upscale lộ Watch Folder, AI Detail/HDR nghiên cứu và câu “hoãn theo Q47” cho customer | move integration sang admin/advanced; ẩn experimental; bỏ jargon nội bộ |
| F13 | P1 | Prompt AI target có team cost/activity nhưng scope hiện tại chủ yếu single-user | khóa quyết định team trước; không dựng dashboard số giả |
| F14 | P1 | Nhiều folder yêu cầu còn trống | audit browser + benchmark rồi trình decision gate; không build từ suy đoán |

## Trạng thái xử lý

- **F01-F02 đóng ở Phase 0:** surface/lifecycle contract và route guard đã có
  regression test; Kịch bản/Media runtime-only, Demo admin-only.
- **F03 đóng ở Phase 1:** `JobEvent`, History API/UI, redaction/retention,
  support/operator metrics và ownership test đã PASS.
- **F04-F06 đóng ở Phase 2:** card-link/accessibility, taxonomy/lifecycle từ
  manifest và hai mode Tạo ảnh AI đã PASS browser matrix + full gate. Backend
  Thumbnail cũ được giữ để tương thích, không phải xóa hay di trú dữ liệu.
- **F07 đóng ở Phase 3.2 / H26.6:** AutoSub bundle public được khóa bằng
  preflight/hash/browser canary và có rollback; không còn phụ thuộc default
  legacy mơ hồ.
- **F08-F12 đóng ở Phase 3.1 / H26.5:** Upscale mutual exclusion có cả UI và
  server guard; compare dùng pointer/keyboard/master clock; queue có
  filter/view/thumbnail/download; GPU budget theo từng card; Watch Folder và
  control experimental không còn lộ ở customer surface.
- **F13 đóng theo quyết định honest scope ở Phase 3.4 / H26.8:** Prompt AI chỉ
  hiển thị project/activity owner-scoped đã có dữ liệu thật; không dựng team
  cost, số thành viên hoặc dashboard cộng tác giả.
- **F14 đóng ở Phase 3.3-3.6 / H26.7-H26.10:** các folder có yêu cầu được xử lý
  tuần tự bằng audit browser + evidence; folder trống giữ `UNKNOWN`, không build
  từ suy đoán. Socialbot vẫn maintenance/frozen đúng quyết định nền.

Tại release re-audit 2026-08-09, **F01-F14 đều đóng**. Nợ sản phẩm mới về asset
library/project xuyên app và collaboration được ghi là roadmap sau release,
không hồi sinh các finding đã đóng.

## Chỉ số sau sửa

- 0 tool internal/retired xuất hiện trong customer catalog/header/search.
- 100% job async có timeline tối thiểu submit/queue/start/progress terminal.
- 100% app async có History entry point dùng cùng nguồn `Job`.
- Console error và failed network bất ngờ = 0 trên core journey.
- Upscale compare drift <= 120 ms sau seek/play và divider/range sai lệch <= 1 px.
- Job success, retry, credit refund, P50/P95 và support rate đo được theo app.
