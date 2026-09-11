# Scheduler V1 — performance, rollout và rollback

## Số đo 2026-09-10

Lệnh: `python bench\scheduler_v1_benchmark.py`. CSDL SQLite nằm trong thư mục
tạm của hệ điều hành; mỗi cỡ hàng đợi được dựng sạch. Mỗi selector lấy median
5 lượt, snapshot lấy median 3 lượt. Kết quả thô nằm ở
`evidence/benchmark_20260910.json`.

| queued | FIFO cũ | selector canonical | queue snapshot |
|---:|---:|---:|---:|
| 1.000 | 0,319 ms | 2,158 ms | 20,585 ms |
| 5.000 | 0,820 ms | 10,288 ms | 81,586 ms |
| 10.000 | 3,845 ms | 23,990 ms | 174,181 ms |

Selector và snapshot tăng gần tuyến tính trong phép đo này; snapshot 10k vẫn
dưới 200 ms. Phần chênh selector là giá của correlated fair-share theo
account/resource/priority. Hai index migration phục vụ chính điều kiện đó và
lọc queue. PostgreSQL migration và M-1 được gate thi hành thật; test đồng thời
PostgreSQL chốt hai worker không nhặt trùng và cùng ưu tiên INTERNAL khi còn đủ
ứng viên.

ETA của mẫu là `null` có chủ ý vì không seed lịch sử runtime. Đây là phép kiểm
đường suy biến: thiếu bằng chứng không được biến thành một con số bịa.

## Rollout

1. Chạy migration additive trước hoặc cùng release. Hai cột có server default
   `unknown`/`external`, nên binary cũ vẫn ghi được và không tự nâng priority.
2. Server và worker có thể lệch phiên bản trong cửa sổ ngắn: worker cũ bỏ qua
   metadata; worker mới coi hàng do writer cũ tạo là EXTERNAL.
3. Sau khi toàn bộ worker mới chạy, theo dõi depth/wait theo class/resource,
   `scheduler_priority_override_total`, `scheduler_fair_rotation_total` và
   `external_queue_starvation`.

## Rollback

- Rollback code: đưa server/worker về bản trước; giữ hai cột/index additive.
  Queue, credit, dedupe, retry và lease vẫn dùng đúng bảng cũ.
- Roll-forward được ưu tiên nếu lỗi chỉ ở telemetry/ETA: tắt bề mặt mới bằng
  code không cần đổi dữ liệu.
- `downgrade()` có đủ thao tác bỏ index rồi bỏ cột cho môi trường chưa cần giữ
  audit metadata. Không downgrade production nếu đã cần lịch sử nguồn gọi.
