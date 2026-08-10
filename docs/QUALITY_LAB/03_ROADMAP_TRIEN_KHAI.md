# LTT Quality Lab — roadmap triển khai tuần tự

## Phase 0 — Khóa measurement contract và license (2–3 ngày)

- Chốt schema evaluation/metric/evidence/verdict và registry evaluator.
- Lập bảng license/model size/checksum/runtime/VRAM; chọn bản Windows/Python phù
  hợp. Chưa tải model nào trước khi bảng này PASS.
- Chốt retention/consent cho raw media và evidence (phụ thuộc quyết định artifact
  của Q75); thiết kế rollback là xóa riêng app Quality Lab và model cache.
- Acceptance: schema test, license review, threat/privacy review, 0 runtime app
  sản xuất bị sửa.

## Phase 1 — MVP CPU/FFmpeg + giao diện operator (4–6 ngày)

- Tạo `apps/qualitylab/`, operator-only, chọn source Job/artifact và pack.
- Job evaluation riêng; ffprobe/media integrity, hash, stream/duration/FPS/audio,
  SRT/ASS parser, CPS/CPL/timing/safe-area logic, report JSON + HTML.
- Playwright kiểm A–Z, access-negative, console/network, responsive.
- Acceptance: fixtures deterministic, retry/idempotency, cleanup temp, H30 events,
  full gate; chưa tự động chạy trên mọi job.

## Phase 2 — Pack Upscale chuẩn (5–8 ngày)

- Nâng `benchmark_upscale_ai_detail.py` thành adapter dùng dataset manifest;
  giữ PSNR/SSIM nhưng thêm LPIPS, artifact/temporal và pyiqa/DOVER-Mobile.
- Thu VRAM/utilization/runtime; scheduler chỉ một evaluator GPU nặng tại một lúc.
- Calibrate 30 ảnh + 12 video; so fast/quality với bicubic baseline.
- Acceptance: reproduce tolerance, report per-slice, human A/B calibration,
  không còn dùng một global SSIM làm kết luận.

## Phase 3 — Pack AutoSub chuẩn (6–9 ngày)

- JiWER + alignment/DER/JER; authoring/timing/shot-cut; OCR burn-in/safe-area;
  translation adapter; browser render journey.
- Dùng WhisperX/pyannote làm evaluator/aligner độc lập có version, không lấy
  chính transcript app làm ground truth.
- Acceptance: golden VI/EN pass; lỗi cố ý (trễ cue, cắt chữ, sai speaker, mất
  audio) đều bị bắt; false-positive rate được ghi.

## Phase 4 — Pack tạo sinh và workflow (8–12 ngày)

- Seedance: VBench subset + reference/prompt suites + human A/B.
- Image/Thumbnail: pyiqa/LPIPS/HPS/CLIP/OCR adapters và brand/crop rules.
- Clip, Chat/Prompt, Agent: task-specific evaluator; Promptfoo chỉ là adapter,
  verdict cuối tuân schema Quality Lab.
- Acceptance từng pack độc lập; không làm song song nhiều app và không bật gate
  khi chưa calibrated.

## Phase 5 — Release regression và trend (4–6 ngày)

- Baseline/candidate diff, dashboard xu hướng theo model/preset/slice.
- CLI cho release candidate; exit code chỉ theo calibrated hard gates.
- Sampling production chỉ opt-in/consent, không giữ raw media mặc định.
- Acceptance: canary, rollback rehearsal, retention cleanup, full LTT-AQA audit.

## Thứ tự và ngân sách GPU

Ưu tiên tuần tự: **foundation → Upscale → AutoSub → Seedance → Image/Thumbnail
→ Clip → Text/Agent**. RTX 5060 Ti 16 GB chạy evaluator nặng độc quyền; metric
CPU/FFmpeg có thể song song giới hạn. VBench đầy đủ/VideoScore 8B và HPSv3 nặng
được để sau khi đo VRAM/runtime thật; MVP dùng subset/mobile adapter trước.

## Danh sách câu hỏi phải khóa trước BUILD

Các câu dưới không chặn nghiên cứu, nhưng phải thành quyết định sản phẩm ở Phase 0:

1. Quality Lab chỉ operator hay có report rút gọn cho khách hàng?
2. Raw artifact/evidence được giữ bao lâu và ai được mở?
3. Release gate chạy local, staging hay cả hai?
4. Ngân sách thời gian tối đa cho một pack và số sample mỗi release?
5. Những loại nội dung nào cấm dùng để calibration (mặt trẻ em, dữ liệu khách,
   giọng nói chưa consent...)?

**Khuyến nghị mặc định:** operator-only; raw temp xóa ngay, metric/hash giữ theo
policy; chạy local/staging; fast gate 15 phút mỗi core pack và nightly đầy đủ;
không dùng dữ liệu khách hay sinh trắc học nếu chưa có consent rõ ràng.

