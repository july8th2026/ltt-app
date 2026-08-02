# UI-RD Upscale — reference map

| Vùng/control trong ảnh | Kỳ vọng | Năng lực hiện tại | Quyết định |
|---|---|---|---|
| Header logo/tên/Pro | nhận diện app | shell LTT + credit/account đã có | RESTYLE; không giả Pro entitlement |
| GPU/VRAM, queue, storage | trạng thái vận hành | GPU probe rời rạc; jobs/storage có nguồn thật | BUILD admin-only |
| Mode Fast/Quality/AI Detail | chọn engine/preset | Fast/Quality thật; AI Detail chưa có | KEEP 2 mode; DEFER AI Detail |
| 1080p/1440p/4K | output target | có thật | KEEP/RESTYLE |
| Codec | H.264/H.265 | có thật | KEEP/RESTYLE |
| Giữ FPS/audio | chính sách output | engine đang giữ mặc định | BUILD thành option có validation |
| Batch toggle | nhiều video | job engine chunk nội bộ, chưa phải multi-file | BUILD tối đa 3 |
| Watch Folder | tự nhận file ổ đĩa | chưa có | BUILD Watch Agent |
| Dropzone 50GB | upload lớn | R2 presigned; ảnh ghi 50GB không phải contract | RESTYLE; cap theo cấu hình/storage thật |
| Before/after slider | so sánh | source/result keys có thể truy xuất | BUILD dữ liệu thật |
| Queue rows/progress/ETA | vận hành job | status/progress có; ETA chưa có | EXTEND; ETA chỉ từ throughput đo thật |
| Pause/Cancel | điều khiển job | cancel WIP; pause chưa có checkpoint bền | BUILD Cancel; DEFER Pause |
| Delete all/completed | lifecycle | chưa retention/audit/undo | DEFER |
| Rename job | metadata | chưa có field/route | DEFER, không cần cho core value |

Tỷ lệ mục tiêu desktop: rail thiết lập khoảng 19%, workspace khoảng 81%; hàng trên
upload/compare khoảng 53% chiều cao, queue khoảng 39%, footer khoảng 4%. Mobile
không sao chép ba cột: settings thành drawer, upload/compare xếp dọc, queue một cột.

