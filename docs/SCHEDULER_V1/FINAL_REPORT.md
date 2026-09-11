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

Chưa deploy production. Sau khi người dùng cho phép tích hợp checkpoint ASV
`694b8a4b`, merge commit `b15ef40c` được kiểm bằng L3 ngày 2026-09-11:
**PASS 32/32**. Bộ regression, migration PostgreSQL, M-1 và bất biến đa tiến
trình đều PASS. Bốn bước frontend React tự bỏ qua vì changeset không chạm bốn
bundle đó; gate ghi rõ chúng không phải bằng chứng.

Kết quả máy đọc:
`test-results/gates/20260911T084027Z-25272.json`.
