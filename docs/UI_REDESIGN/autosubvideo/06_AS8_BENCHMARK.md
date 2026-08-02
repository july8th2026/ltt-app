# AS8 — Hardening, corpus, GPU và end-to-end

Ngày chạy: 2026-08-03. Mọi job dùng database/storage cô lập; video đầu vào là
file test Dev đã cho phép trong `G:\My Drive\AI\Tool AI\Video seedacne`. Không
ghi transcript hay dữ liệu người dùng vào hồ sơ này.

## Kết quả GPU render

| Nguồn | Đầu ra | Encoder | Thời gian | Kiểm tra |
|---|---|---|---:|---|
| 10,054s; 864×496; 24fps; AAC | 1882×1080; 24fps; AAC | h264_nvenc | 1,296s | PASS |
| 8,057s; 864×496; 24fps; AAC | 1254×720; 24fps; AAC | h264_nvenc | 1,001s | PASS |
| 5,062s; 1280×720; 24fps; AAC | 3840×2160; 24fps; AAC | h264_nvenc | 1,695s | PASS |

Cả ba ca đi qua hàng đợi/job context thật, giữ và quyết toán 1 credit, số dư từ
100 còn 99, tạo video cùng ASS/SRT/VTT/JSON/ZIP. Tỉ lệ khung hình, FPS và trạng
thái audio đều đúng; không dùng đường tắt gọi FFmpeg trực tiếp ngoài worker.

## ASR A/B

Audio kiểm tra tiếng Anh tổng hợp dài 8,128 giây có reference 14 từ:

| Model | Alignment | Từ aligned | Thời gian | RTF | WER |
|---|---|---:|---:|---:|---:|
| tiny | aligned | 14 | 13,908s | 1,711 | 0,000 |
| large-v3 | aligned | 14 | 14,264s | 1,755 | 0,000 |

Đây là sanity/parity test trên giọng tổng hợp, **không phải** số đo độ chính xác
ngoài thực địa. Mốc tiếng Việt AS2 được giữ làm corpus thứ hai: file 30 giây,
`large-v3` aligned trong 19,36 giây, RTF 0,645. Chưa có transcript chuẩn do người
duyệt cho video tiếng Việt nên không công bố WER suy đoán.

Benchmark phát hiện một lỗi vận hành: sidecar ghi nhiều vào `stderr` có thể làm
đầy pipe trong lúc tiến trình cha chỉ poll. Nay stderr đi vào file tạm, có timeout
cấu hình qua `LTT_WHISPERX_TIMEOUT_SECONDS`, hủy/timeout dừng cả process tree và
mọi file tạm được dọn.

## Project lớn và security corpus

- 3.000 cue / 3.150 giây: validate và tạo đủ ASS/SRT/VTT/JSON/ZIP trong 0,438s;
  peak 8,98 MB — PASS ngưỡng 5s/256 MB.
- Download video/ZIP bị khóa theo owner; byte Range trả 206; traversal bị từ chối.
- Track render không tồn tại và nguồn ASR trên 120 phút bị từ chối 422.
- Chuỗi `{\\p1}` trong cue từng lọt thành ASS override. Sanitizer nay thay mọi
  ngoặc nhọn do người dùng nhập trước khi hệ thống thêm override nội bộ; regression
  test khóa việc không cho inject drawing/font/file directive.
- Autosave offline hiển thị “Mất kết nối — thay đổi chưa được lưu.” và giữ trạng
  thái error, không nói sai rằng đã lưu.

## Browser thật

Playwright chạy fixture cô lập tại 1440×900, 1280×800, 390×844 và 360×800:
document overflow ngang bằng 0; input/select/textarea đều có accessible name; không
có nút rỗng không tên. Luồng offline tạo đúng failed PUT dự kiến, sau khi phục hồi
mạng và reload thì console 0 lỗi/0 cảnh báo, request ứng dụng đều thành công.

## Gate AS8

- Backend regression mở rộng: 170 passed, 1 deprecation warning.
- Frontend: 9 passed; TypeScript + Vite production build PASS.
- Secret scan: 0 finding.
- AS8 PASS. AS9 vẫn phải chạy full suite, migration/backup rehearsal, release
  package, production canary và rollback gate trước khi mở public.
