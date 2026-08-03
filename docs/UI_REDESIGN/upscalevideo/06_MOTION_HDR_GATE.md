# UP-FEAT-002 — motion/HDR engine và cost gate

## Kết luận

- **BUILD chống rung:** FFmpeg cài thật có `vidstabdetect` + `vidstabtransform`.
- **BUILD mượt chuyển động 2×:** FFmpeg cài thật có `minterpolate`; frame được
  nội suy trước Real-ESRGAN nên AI xử lý đủ frame mới, không nhân frame giả ở UI.
- **DEFER HDR:** build hiện có `tonemap` cho HDR→SDR, không có pipeline tạo HDR
  trung thực từ SDR kèm color primaries/transfer/mastering metadata. Không gắn
  nhãn HDR cho video SDR.

## Benchmark thật trên file người dùng chỉ định

Nguồn: 864×496, 24 FPS, 10,054 giây. Đo trên đoạn 8 giây:

| Engine | Kết quả | Runtime | Hệ số cost |
|---|---|---:|---:|
| libvidstab two-pass | 864×496, 24 FPS, 192 frame/8,000s | 1,34s | 1,2× |
| minterpolate MCI/AOBMC | 864×496, 48 FPS, 381 frame/7,938s | 25,29s | 2,2× |

Mượt chuyển động vừa tốn bước optical-flow CPU vừa làm gần gấp đôi frame qua
Real-ESRGAN. Hệ số 2,2× thấp hơn tổng runtime worst-case nhưng đủ bù GPU frame
gấp đôi; phải theo dõi telemetry thực tế sau release trước khi chỉnh giá.

## Luồng triển khai

1. Quote server nhận hai boolean, không nhận giá từ client.
2. Worker đo duration thật rồi nâng hold theo cùng multiplier.
3. Chống rung chạy hai pass trong temp dir bằng transform filename tương đối để
   không vỡ parser FFmpeg trên đường dẫn ổ đĩa Windows.
4. Smooth dùng `minterpolate` khi extract; output FPS là rational gốc ×2.
5. Real-ESRGAN/encode/mux audio dùng pipeline hiện có; output key mang suffix
   enhancement để resume không nhầm artifact thường.
6. Disk guard nhân đôi frame cho smooth; ETA sample tách theo đúng hai flag.

## Evidence kiểm thử

- Browser canary cô lập: quote 5 → 6 → 14 credit; submit giữ 14, card hiện
  `Chống rung` và `FPS 2×`; desktop/mobile overflow 0; console/network sạch.
- CPU pipeline smoke 0,625 giây (mock đúng riêng bước Real-ESRGAN đang giữ
  nguyên): output 1882×1080, 48 FPS, 27 frame/0,5625 giây. Hai motion engine,
  probe, scale, encode và contract result đều chạy thật.
- GPU Real-ESRGAN không chạy cạnh process production của BOT GEMINI. Engine
  Real-ESRGAN không đổi trong vé này và đã có benchmark/GPU gate riêng ở
  `05_AI_DETAIL_BENCHMARK.md`.

## Rollback

Tắt/ẩn hai checkbox và ngừng nhận flag mới; job đã tạo vẫn chứa params additive
và worker cũ bỏ qua an toàn. Revert app-only commit; không migration/core change.
