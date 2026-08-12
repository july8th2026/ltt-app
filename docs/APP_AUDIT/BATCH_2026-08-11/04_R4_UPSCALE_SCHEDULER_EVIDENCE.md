# H33.R4 — Upscale scheduler evidence

Ngày: 2026-08-12  
Phạm vi: source scheduler lane; không phải commercial quality calibration.

## Kết quả

- Submit mới từ UI Upscale và handoff Seedance chọn lane theo preset đã chuẩn
  hóa: `render.fast` hoặc `render.quality`.
- Fast giữ 2.000 MB từ peak delta đo thật 848 MB; Quality giữ 12.000 MB từ peak
  delta 11.176 MB.
- Lane legacy `upscalevideo.render` tiếp tục giữ 12.000 MB và resolve cùng
  handler. Job đã tồn tại không bị migrate/đổi loại; Agent ToolSpec tĩnh giữ
  fallback an toàn.
- Dedupe key dùng đúng lane, nên request-id giống nhau trong cùng preset vẫn
  idempotent; Fast/Quality là hai ý định cấu hình khác nhau.

## Bằng chứng chạy thật

| Lệnh | Kết quả |
|---|---|
| `python -m pytest tests\test_82_upscalevideo.py tests\test_171_upscale_h32.py tests\test_72_vanhanh.py -q` | **50 passed** |
| `python tools\gate.py --quick` | **PASS 8/8** |
| `python tools\gate.py` | **PASS 9/9**, 1.806,3s; pytest 1.778,3s; secret scan 0 finding |
| `nvidia-smi --query-gpu=...` | GPU1 idle; GPU0 baseline 1.126 MB, vượt qualified guard 512 MB |

## Trạng thái trung thực

**SCHEDULER SOURCE PASS / COMMERCIAL QUALITY BLOCKED.** Chưa có dataset HR có
license/consent tối thiểu 12 video, blind A/B ít nhất ba rater/case và threshold
quality/cost/P95 có version. Không dùng fixture synthetic hoặc Lanczos diagnostic
làm commercial PASS. Dual-GPU chỉ rerun khi cả hai card qua idle guard; không
dừng workload ngoài phạm vi để tạo bằng chứng đẹp giả tạo.

## Rollback

Revert commit Q86. Lane legacy vẫn còn nên rollback không cần đổi Job trong DB.
Job mới thuộc lane Fast/Quality phải được drain hoặc giữ manifest Q86 cho tới khi
hàng đợi không còn các loại đó; tuyệt đối không xóa job type trước khi kiểm kê.
