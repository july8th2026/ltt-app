# UI-RD Upscale — kế hoạch triển khai UP0–UP8

Thứ tự dưới đây là bắt buộc. Phase trước chưa PASS thì phase sau không được đánh
hoàn thành. Có thể viết test của phase kế tiếp, nhưng không deploy lát cắt dở.

## UP0 — Recovery baseline và khóa nguồn sự thật

- Ghi Q47, hồ sơ UI-RD, map toàn bộ WIP hiện tại và video test Downloads.
- Tách rõ thay đổi Seedance, lifecycle core và UI Upscale; viết rollback trước.
- Baseline Playwright desktop/mobile và mọi state tạo được bằng fixture cô lập.

**PASS:** G0–G2; plan/nhật ký không còn ghi “chờ Decision Gate”; không có feature
ngoài ma trận. **Rollback:** docs-only; code WIP chưa deploy.

## UP1 — Contract job lifecycle và cầu Seedance

- Hoàn thiện trạng thái `cancelled` additive trong job contract.
- Cancel queued/running; nối `cancel_check` xuống NCNN subprocess và checkpoint
  FFmpeg/chunk; refund/settlement idempotent, xử lý race cancel-vs-complete.
- Seedance quote server-side → confirm CSRF/owner → `submit_upscale_job()`.
- Không cho client gửi giá hoặc storage key tùy ý.

**PASS:** unit/integration ownership, CSRF, insufficient credit, dedupe, queued/
running cancel, subprocess stop, double cancel và settle/refund. Q47 + rollback
được khóa. **Rollback:** ẩn control/route nhận job mới, để job active drain; giữ
ledger/job audit, revert contract additive chỉ sau khi không còn `cancelled` active.

## UP2 — Studio shell, upload và quote

- Xây layout theo ảnh: settings rail, dropzone, compare panel, queue panel.
- Upload 1 file qua R2/local fallback; probe metadata; quote server-side.
- Preserve FPS/audio là option thật; Fast/Quality/target/codec data-driven.
- AI Detail hiển thị “đang nghiên cứu” hoặc ẩn, tuyệt đối không chạy Quality dưới
  tên mới.

**PASS:** upload small/large/failure, keyboard, error/empty/loading, 1440/1280/
390/360 viewport; console/request sạch. **Rollback:** template/CSS/route UI về bản
trước, backend UP1 giữ tương thích.

## UP3 — Compare nguồn/kết quả thật

- Endpoint theo `job_id`, kiểm owner/app; không nhận storage key tùy ý.
- R2 presigned/local Range; player before/after có fallback hai player khi browser
  không đồng bộ được; download output thật.

**PASS:** owner khác nhận 404; source Seedance và upload trực tiếp đều xem được;
Range/presigned, missing artifact và mobile PASS. **Rollback:** tắt compare UI,
giữ download output.

## UP4 — Batch tối đa 3

- Chọn/kéo tối đa 3 file, probe từng file, quote từng file + tổng.
- Preflight storage/capability/credit; tạo các job và hold trong một transaction.
- Upload artifact có thể thành công từng file nhưng submit batch phải trả manifest
  kết quả rõ; dedupe chống double submit; không âm thầm tạo 1/3 job.
- Queue hiện vị trí, trạng thái và lỗi theo từng file.

**PASS:** 1/2/3 file, file thứ 4 bị chặn, mixed invalid, thiếu credit, double click,
R2 failure và owner isolation. **Rollback:** giới hạn UI/API về một file; job đã
tạo tiếp tục chạy/settle bình thường.

## UP5 — Watch Folder / Watch Agent

- Agent Windows riêng đặt ở máy chứa folder; polling ổn định thay vì tin một event.
- File chỉ nhận khi size+mtime ổn định qua nhiều lần; allowlist extension/cap.
- Token scope chỉ upload/quote/submit Upscale của đúng account; không cookie, không
  secret trong repo/log. Dedupe fingerprint; archive success, quarantine failure.
- Tôn trọng batch max 3 và dừng nhận mới khi thiếu credit/storage/GPU unavailable.

**PASS:** create/partial-write/rename/duplicate/restart/offline/token revoked/
insufficient credit; service install/uninstall ASCII PowerShell; data path an toàn.
**Rollback:** stop/disable Watch Agent; không xóa source; queued job tiếp tục xử lý.

## UP6 — Admin telemetry và ETA thật

- Admin-only: GPU model/util/temp/VRAM, worker heartbeat/capability, queue depth,
  storage used/quota khi backend cung cấp.
- User: progress, stage, vị trí và ETA chỉ sau khi có throughput đủ mẫu; nếu không
  ghi “đang ước tính”, không bịa FPS/ETA.
- Metric không chứa filename, prompt, token hay storage key nhạy cảm.

**PASS:** role tests, stale/unavailable telemetry, sampling overhead, redaction,
browser admin/user. **Rollback:** ẩn panel, không ảnh hưởng worker/job.

## UP7 — Nghiên cứu AI Detail và lifecycle hoãn

- Benchmark ứng viên engine/model bằng video chuẩn: detail recovery, artifact,
  temporal consistency, VRAM, latency, license và cost.
- Chỉ mở AI Detail khi thắng acceptance đã ghi và có fallback; nếu không tiếp tục
  DEFER. Thiết kế riêng Pause và delete/retention, không ghép lén vào release.

**PASS:** báo cáo + dữ liệu benchmark tái lập; control chỉ bật khi engine thật PASS.
**Rollback:** feature flag off/ẩn mode; Fast/Quality không đổi.

## UP8 — Nghiệm thu, release và deploy

- GPU smoke video `eeae72a7_seedance_f56d2de3_1080p.mp4` trong Downloads: probe,
  preview rồi full hợp lý; kiểm FPS/audio/resolution/artifact/credit/temp cleanup.
- App/regression → full pytest; secret scan; contract lint; dependency check.
- Playwright tất cả state/viewport, console 0, failed request 0, no overflow.
- Backup + restore/read archive, migration rehearsal nếu có, build release, canary,
  production health/browser/worker/GPU smoke; ghi nhật ký và commit từng phase.

**PASS:** G0–G7 đều có evidence. **Rollback:** dừng nhận job mới, drain/cancel +
settle/refund, rollback binary bằng `app.previous`; Watch Agent disabled trước khi
rollback; không xóa ledger/job/artifact audit.

