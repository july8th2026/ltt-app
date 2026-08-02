# UI-RD Upscale — hiện trạng có bằng chứng

## Năng lực đã có

- `Fast` (`realesr-general-x4v3`) và `Quality` (`realesrgan-x4plus`), autotune
  tile/thread theo VRAM; vendor NCNN-Vulkan đã được kiểm tra trên GPU.
- 1080p/1440p/2160p, H.264/H.265, giữ tỷ lệ/FPS/audio; VFR được chuẩn hóa CFR.
- Presigned PUT R2, local fallback dưới 90MB, HTTP Range/presigned output.
- Worker job nền: probe → giữ thêm credit theo duration thật → guard đĩa → tách
  frame → upscale/chunk 360 frame → encode/mux → storage → quyết toán.
- Preview 8 giây, resume theo output key, watchdog stall, OOM tile fallback.
- `submit_upscale_job()` là service dùng chung cho upload trực tiếp và Seedance.

## Khoảng trống so với ảnh/logic đã khóa

- UI hiện là form + card; chưa có studio grid hoàn chỉnh hay upload dropzone lớn.
- Chưa có batch tối đa 3 và quote tổng atomic.
- Compare mới ở trạng thái WIP; chưa có scrubber đồng bộ hoặc đầy đủ test quyền.
- Cancel lifecycle đang WIP; chưa truyền `cancel_check` vào engine và chưa phủ đủ
  queued/running/race/settlement/refund.
- Chưa có Watch Agent, token scope, stable-file detection, quarantine hay audit.
- Chưa có telemetry admin bền vững; ETA/throughput chưa được đo.
- Chưa có retention/delete contract. Không có Pause an toàn giữa FFmpeg/NCNN.
- AI Detail trong ảnh chưa có engine thứ ba; không được đổi tên Quality thành AI
  Detail để tạo cảm giác có tính năng chưa tồn tại.

## Bằng chứng kiểm thử hiện có

- App gốc từng GPU smoke và browser E2E thành công, ghi trong `docs/NHAT_KY.md`.
- Lượt WIP gần nhất: 64 test hẹp pass; Playwright desktop empty state của Upscale
  console 0 và estimate 200. Đây chưa phải gate R8.
- Worktree hiện bẩn, chưa commit/deploy; kế hoạch này không coi WIP là hoàn thành.

