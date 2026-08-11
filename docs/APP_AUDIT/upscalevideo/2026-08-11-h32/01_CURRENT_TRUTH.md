# H32.6 — Current truth: Upscale Video

## Chuỗi vận hành thật

`browser upload/direct ticket → server quote → atomic batch + credit hold →
upscalevideo.render → Real-ESRGAN/FFmpeg/NVENC → artifact → download/compare`.

- Fast dùng engine spatial nhẹ; Quality dùng Real-ESRGAN x4plus theo frame.
- Một job type đang phục vụ cả Fast/Quality. Đo thật cho thấy Fast peak delta
  khoảng 848 MB, Quality 11.176 MB; manifest vì vậy phải giữ 12.000 MB theo
  worst case cho tới khi tách loại job.
- H.264/HEVC, 1080p/1440p/2160p, audio, preserve/normalize FPS, preview,
  stabilization và smooth motion đều có worker path thật.
- Smooth motion phải nhân đôi cadence nguồn. Bug 24→60 đã được sửa thành 24→48.
- Queue card trong app là snapshot 12 job; lịch sử đầy đủ nằm ở control plane.

## Truth đã chứng minh

- 17/17 case option matrix pass trên GPU 1.
- Source đầy đủ 15,069 giây Fast 1080 H.264 hoàn thành trong 32,78 giây xử lý,
  32,944 giây wall; output 1882×1080, 24 fps, AAC, 26.009.834 byte.
- Browser batch hai file giữ đúng 96 credit và tạo hai job có vị trí 1/2.
- GPU 1 đạt 100% utilization, 67°C, không thermal slowdown.
- GPU 0 bị bộ đo từ chối vì baseline không idle; đây là safety PASS của bộ đo,
  không phải bằng chứng dual-GPU saturation.

## Unknown bắt buộc giữ

- Quality Lab chỉ xác minh contract video. PSNR/SSIM/temporal là diagnostic
  chưa calibrate; verdict hình ảnh vẫn `UNKNOWN`.
- Chưa có blind panel trên bộ HR ground-truth đa thể loại.
- Chưa chứng minh P95 production, large R2 download hoặc hai GPU đồng thời trong
  lần audit này.

