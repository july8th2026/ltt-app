# Scheduler V1 — báo cáo chốt kỹ thuật

Ngày: 2026-09-10

## Đã xây dựng

- Một durable queue jobs; không thêm broker hoặc engine thứ hai.
- Priority INTERNAL > EXTERNAL chỉ với job queued/eligible cùng tài nguyên;
  lease đang chạy không bị cắt ngang.
- Ingress tin cậy, dữ liệu thiếu/lạ và yêu cầu public đều fail-closed EXTERNAL.
- Ranking canonical dùng chung cho claim, position, ahead count và ETA.
- Queue snapshot qua status/polling; event và terminal webhook cũ giữ nguyên.
- Metric theo resource/priority và cảnh báo external starvation.

## Bằng chứng hiện có

- Các lượt test mục tiêu: 33 PASS; cụm scheduler/public/history: 18 PASS.
- PostgreSQL migration PASS; claim đồng thời hai worker không trùng và lấy hai
  job INTERNAL trước.
- Browser local cô lập: position động đúng, ETA null khi thiếu lịch sử,
  console 0 error và không có failed request.
- Benchmark 1k/5k/10k nằm ở evidence/benchmark_20260910.json; snapshot 10k
  khoảng 174 ms trên máy phát triển.

## Trạng thái phát hành

Chưa deploy production. L3 cuối chạy đủ 32 bước: 30 PASS, 2 FAIL; 9.392 test
PASS và toàn bộ test Scheduler xanh. Blocker là 7 assertion bằng chứng ASV,
test hook thiếu sh và ký tự VT trong scorecard Voice, đều ngoài changeset
Scheduler. Không chạy lại gate hoặc sửa lấn các worktree sở hữu chúng.
