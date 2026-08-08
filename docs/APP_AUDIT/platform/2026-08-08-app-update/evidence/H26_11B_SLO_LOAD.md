# H26.11B — SLO và load/soak evidence

Ngày snapshot: 2026-08-09. Không gọi provider, không dùng production data và
không trừ credit thật trong lượt đo mới.

## SLO đã khóa

| Profile | Điều kiện executor | Success | Queue wait P95 | Mẫu tối thiểu | Hard gate |
|---|---|---:|---:|---:|---|
| API | mặc định/API | >=90% | <=30s | 20 finished | stale=0, event-write-failure=0 |
| Compute | GPU hoặc FFmpeg | >=90% | <=120s | 20 finished | như trên |
| Browser | browser automation | >=90% | <=300s | 20 finished | như trên |

Ít hơn 20 finished là `insufficient_data`, không được gọi PASS. Runtime P95 và
credit/success vẫn đo theo app nhưng chưa đặt một ngưỡng chung vì video 4 giây,
video 60 phút và text là các workload khác bản chất.

## Kết quả mới

- Queue soak SQLite cô lập: 300 Job thật qua `submit → claim → complete/fail`,
  100 mỗi profile, 4 worker ID, 2% synthetic provider failure/profile.
- Cả ba profile: success 98%, stale 0, event write failure 0, credit/success 3.
- Queue P95: API 5,444s; Compute 5,517s; Browser 5,607s. Ba SLO PASS.
- Wall time toàn soak: 2,922s. Đây là DB/state-machine soak, không được dùng làm
  latency provider hay throughput production.
- AutoSub project lớn chạy lại: 3.000 cue/3.150 giây, đủ ASS/SRT/VTT/JSON/ZIP,
  0,429s, peak 8,98 MB — PASS budget 5s/256 MB.
- Targeted load/limit/GPU contract: 31 PASS; gồm 10 Agent run concurrent không
  duplicate, request-body/asset cap và GPU lease/worker isolation.

## Evidence tái sử dụng, không chạy lại tốn thời gian

- Dual-GPU local 2026-08-08: hai RTX 5060 Ti 16 GB chạy đồng thời cùng video
  10,054s; wall 27,99s; hai output 1080p PASS; mỗi GPU đạt 100%, max 64°C, không
  thermal slowdown. File nguồn do Dev cho phép trong folder Video Seedance.
- Matrix cùng ngày: 2 preset × 3 resolution × 2 GPU PASS. Không coi 2×16 GB là
  một GPU 32 GB.
- Browser upload thực tế ở các phase app đã qua file 7,2 MB; middleware cap có
  regression riêng cho đường asset. Vòng này không cấp phát multipart 90 MB chỉ
  để tạo số đẹp; direct-upload >90 MB vẫn phụ thuộc R2/CORS gate Q48.

## Giới hạn bằng chứng

Chưa có P50/P95 production hoặc provider canary sau deploy; dashboard sẽ trả
`insufficient_data` cho app dưới 20 mẫu. H26.12 phải quan sát production theo
app, không lấy ba profile synthetic để mở G7 production.
