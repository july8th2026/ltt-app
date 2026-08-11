# H32 — Audit và nâng cấp sáu tool từ bộ yêu cầu 2026-08-11

## Charter

- Nguồn yêu cầu chỉ đọc:
  `C:\Users\Thang Tuong\Desktop\AppLttStudio_11082026`.
- Phương pháp: LTT-AQA `STANDARD`, nâng lên `DEEP` cho AutoSub, Clip và Upscale
  vì có media/job dài/GPU.
- Môi trường mặc định: server/browser fixture cô lập, tài khoản test và storage
  riêng. Không dùng production user/media/credit nếu không cần thiết.
- Thực hiện tuần tự: AutoSub → Prompt AI → Tạo ảnh → Tạo Clip → Seedance UI →
  Upscale. Không sửa song song nhiều app.
- Mỗi thay đổi hành vi có targeted test, browser desktop/mobile, console/network
  check và full gate trước khi kết thúc batch. Không deploy trong H32 nếu chưa có
  yêu cầu deploy riêng.

## Tài nguyên đã kiểm kê

| Tool | Tài nguyên | Contract đã probe |
|---|---|---|
| AutoSub Video | `VideoTest.mp4` | H.264/AAC, 864×496, 24 fps, 15,069 giây |
| Prompt AI | `AnhThamKhao.png` | PNG RGB, 1672×941 |
| Tạo ảnh AI | Không có media | Tự viết prompt canary; lưu output về folder người dùng |
| Tạo Clip ngắn | `VideoTest.mp4` | H.264/AAC, 1920×1080, ~29,88 fps, 265,202 giây, 523,9 MB |
| Seedance | `GiaoDien.png` | PNG RGB, 1586×992; chỉ visual audit, không chạy job |
| Upscale Video | `VideoTest.mp4` | Cùng hash với video AutoSub, 15,069 giây |

Hash đầy đủ được giữ trong evidence từng tool; báo cáo không suy diễn ảnh mockup
thành tính năng backend.

## Quy tắc output test

Tên file dùng ASCII để ổn định trên tool/CLI:

`YYYYMMDD_<tool>_<mode-or-preset>_<main-options>_<job8>.<ext>`

Ví dụ:

- `20260811_autosub_tiktok-bold_standard_<job8>.mp4`;
- `20260811_taoanh_general_16x9_<job8>.png`;
- `20260811_clip_balanced_talking-head_9x16_<job8>.mp4`;
- `20260811_upscale_quality_1080p_h264_<job8>.mp4`.

Chỉ output do test tạo được ghi vào folder người dùng. Source không sửa/xóa/đổi
tên. Mỗi output phải probe lại codec/resolution/duration và gắn job/config.

## Phase và gate

### H32.0 — Baseline và browser harness

- Đọc toàn bộ `MoTa.txt`, manifest, source, test và tài liệu hiện hành.
- Dựng browser fixture mới từ current checkout; không dùng server cũ để kết luận.
- Lập evidence index và baseline score Q/M/E/G0–G8.
- PASS: source/data/browser target và rollback rõ; worktree sạch trước sửa.

### H32.1 — AutoSub Video

- Đổi tên hiển thị toàn bộ bề mặt từ “Khắc phụ đề video” sang “AutoSub Video”.
- Upload video, tạo/import subtitle, chọn style/font, quote/confirm/render,
  polling/reload, preview/download và probe output.
- Audit đầy đủ preset, custom style, timing, text edit, track, export SRT/ASS/ZIP,
  retry/cancel/error/insufficient-credit/mobile.
- PASS: output có subtitle nhìn thấy và timing hợp lệ; credit/job/log đúng; không
  dead control; output được lưu theo quy tắc.

### H32.2 — Prompt AI

- Đối chiếu read-only `D:\BOT GEMINI` Prompt Seedance Studio với nội tại hiện có.
- Lập KEEP/EXTEND/REJECT cho Prompt Library, Style và Meta Director; copy dữ liệu
  tĩnh cần thiết vào app, không import chéo/runtime/secret.
- Chạy brief → build prompt → storyboard/preview/handoff; kiểm ownership/credit.
- PASS: chức năng được chọn có logic thật, API/UI/test; không chỉ dựng menu/vỏ.

### H32.3 — Tạo ảnh AI

- Kiểm cả `general` và `YouTube Thumbnail`, model/aspect/count/reference/options.
- Chạy canary thật khi provider sẵn sàng, tải ảnh về folder và probe file.
- PASS: quote/hold/settle, output/ownership/download/history và các state rõ.

**Checkpoint 2026-08-11:** hoàn tất audit/code/browser ở mức INTERNAL. Preview
hai mode đã disclosure model/giá/config; edit/remix/mobile/console/network pass.
Provider E4 và canonical pricing chưa pass, được chuyển thành release blocker
trong hồ sơ `docs/APP_AUDIT/taoanh/2026-08-11-h32/`; không tạo output giả.

### H32.4 — Tạo Clip ngắn

- Upload thẳng video 523,9 MB; kiểm tier/genre/aspect/language/count/duration/
  brand/platform, quote, queue/GPU, progress/cancel/retry và output nhiều clip.
- PASS: output đúng count/contract hoặc lỗi có root cause; download/probe từng
  clip; không giữ credit sai.

**Checkpoint 2026-08-11:** Fast/1 clip/VI/9:16+4:5 pass E4 trên source 523,9
MB và worker CUDA. Đã sửa SRT rebase, progress monotonic/throttle, NVENC probe
RTX 50xx, exact aspect geometry, upload CSRF/type/size/local cap và JSON error.
Output nghiệm thu 4:5 là 1080×1350 SAR 1:1, `h264_nvenc`, decode exit 0; credit
28/job khớp. Q 77 · M 58 · E 95 · INTERNAL. Balanced/Best, multi-clip, cancel,
actual object-size/lifecycle và Review/Edit vẫn là blocker, xem hồ sơ
`docs/APP_AUDIT/taoclipngan/2026-08-11-h32/`.

### H32.5 — Seedance UI

- Không chạy provider/job theo yêu cầu. So sánh current UI với `GiaoDien.png` ở
  desktop/mobile: IA, panel tạo, prompt/ref, model/duration/aspect/resolution,
  quote, history grid/list/filter/status/error/empty/loading.
- Chỉ nâng giao diện dựa trên chức năng có thật; không tạo CTA giả.
- PASS: visual/control regression xanh, console/network sạch, responsive.

### H32.6 — Upscale Video

- Chạy ma trận Fast/Quality × 1080p/1440p/2160p × H.264/HEVC cùng preview,
  preserve FPS/audio, stabilize và smooth motion theo compatibility hợp lệ.
- Đo latency/throughput/peak VRAM, queue hai job, autotune/fallback/recovery;
  Quality Lab so sánh trước/sau. Không dùng proxy chưa calibrated làm PASS.
- PASS: mọi option hỗ trợ được chứng minh; option không chạy phải ẩn/disable hoặc
  sửa; manifest GPU contract khớp bằng chứng runtime.

### H32.7 — Release audit

- Mỗi tool có: charter, current truth, control registry, scorecard Q/M/E/Gate,
  finding P0–P3, cấu hình tested/untested/broken, option roadmap và evidence.
- Targeted regression + ba frontend + full `python tools\gate.py` PASS.
- Browser retest desktop/mobile, console error 0, failed app request 0.
- Chưa deploy; phát hành là phase riêng có backup/rollback/public smoke.

## Trạng thái ban đầu

Chưa chấm điểm chính thức trước browser baseline. Mọi Q/M/E/Gate ghi UNKNOWN cho
tới khi có evidence; ảnh tham khảo chỉ là E0, source là E1, test là E2, browser
là E3 và canary/provider thật mới là E4.
