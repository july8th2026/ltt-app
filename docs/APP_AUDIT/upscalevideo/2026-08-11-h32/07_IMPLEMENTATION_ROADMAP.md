# H32.6 — Roadmap hoàn thiện Upscale Video

## Phase 0 — Release blockers

- Upload session: CSRF, allowlist, declared/actual size, quota/rate, TTL.
- Artifact state machine: staging → held → job-owned → retained/deleted;
  sweeper/reconcile idempotent.
- Quality benchmark: HR truth đa thể loại, blind rating, PSNR/SSIM/VMAF/temporal
  threshold version; không dùng Lanczos-reference report hiện tại làm gate.
- **PASS:** G2/G5 xanh, quality verdict có calibration version.

## Phase 1 — Queue và scheduler

- Tách `upscalevideo.fast` và `upscalevideo.quality`, khai VRAM theo evidence.
- Poll/SSE owner-scoped, visibility backoff, retry/cancel/resume rõ.
- Rerun dual-GPU qualified khi cả hai card idle.
- **PASS:** Fast không giữ 12 GB; hai GPU chạy đồng thời, queue/credit đúng.

## Phase 2 — Customer workflow

- Canonical server probe trước hold; cost/runtime/output-size range.
- Confirmation cho batch/Quality giá cao; preview chọn segment.
- Global history cursor + retry tại card; poster/lazy video metadata.
- **PASS:** E3 desktop/mobile/offline/error/recovery, không request thừa đáng kể.

## Phase 3 — Chất lượng cạnh tranh

- Benchmark denoise, deblur và temporal consistency trên cùng bộ dữ liệu.
- Giữ UI intent `Auto/Fast/Quality`; model/tiles ở operator config.
- **PASS:** blind panel và metrics không kém baseline; cost/successful output đạt
  ngưỡng economics đã khóa.

## Phase 4 — Release

- Full gate, staging canary, P50/P95/error/refund/storage SLO, rollback drill.
- **PASS:** G0–G8 theo target release; chỉ deploy khi có yêu cầu riêng.

