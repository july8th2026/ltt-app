# UI-RD — Upscale Video Studio

**Trạng thái:** FULL — Decision Gate đã khóa, chuẩn bị BUILD theo UP0–UP8  
**App/route thật:** `upscalevideo` / `/upscalevideo`  
**Ảnh tham khảo:** `g:\My Drive\AI\A\New folder\UPSCALE.png` (1680×939)  
**Nguồn sự thật:** `apps/upscalevideo/`, `platform_core.jobs`, credit ledger,
`platform_core.storage` và worker GPU

## Mục tiêu

Nâng app Upscale hiện có thành studio xử lý video đầy đủ, bám sát bố cục ảnh:
thiết lập bên trái, upload + compare ở giữa/phải và hàng đợi phía dưới. Tất cả
control phải nối logic thật; không mô phỏng GPU, storage, ETA hay AI Detail.

## Logic Dev đã khóa

| Mã | Quyết định | Acceptance chính |
|---|---|---|
| UP-D1 | Full scope trước deploy | UP0–UP8 đều PASS mới release production |
| UP-D2 | AI Detail nghiên cứu riêng | Ẩn/disabled có giải thích đến khi có engine + benchmark thật |
| UP-D3 | Compare thật | Player nguồn và output owner-scoped, không dùng ảnh minh họa |
| UP-D4 | Batch tối đa 3 | Quote tổng, giữ credit và tạo tối đa 3 job có kết quả rõ từng file |
| UP-D5 | Cancel có; Pause hoãn | Cancel cooperative dừng subprocess ở checkpoint và hoàn credit idempotent |
| UP-D6 | Watch Folder làm ngay | Watch Agent cục bộ; không cho browser gửi đường dẫn máy khách như đường dẫn server |
| UP-D7 | Telemetry chi tiết chỉ admin | User chỉ thấy trạng thái/tiến độ; admin thấy GPU/VRAM/storage/queue thật |
| UP-D8 | Delete/retention hoãn | Không bật nút xóa trước soft-delete/retention/audit/undo contract |
| UP-D9 | Rollout tự động sau gate | Backup, GPU smoke, full gate và rollback phải xanh |
| UP-D10 | Seedance dùng chung Upscale | Popup quote/confirm credit rồi gọi `submit_upscale_job()`, không copy engine |

## Ranh giới

- Không đổi slug, job type hay tạo app Upscale thứ hai.
- Không dùng ImageGen; artwork nếu cần lấy crop từ ảnh Dev cung cấp hoặc CSS/SVG.
- File lớn tiếp tục upload thẳng R2; không đưa video >100MB qua Cloudflare.
- Watch Agent dùng token riêng, không dùng cookie trình duyệt hay secret trong UI.
- Production chỉ nhận bản đã qua UP8; không deploy worktree giữa phase.

