# 00 — Audit Charter: Upscale Video

- App/slug: Upscale Video / `upscalevideo`
- Version/commit: `1f90d8a`
- Ngày snapshot: 2026-08-09
- Mode: **DEEP**
- Môi trường/URL: fixture cô lập `http://127.0.0.1:8130/upscalevideo`;
  source + test + evidence GPU hiện có trong repo. Không ghi production.
- Production authorization: **KHÔNG** cho mutation; production chỉ là baseline
  triển khai đã ghi ở H26.12C.
- Persona chính: người làm nội dung không chuyên kỹ thuật, có video mờ/thấp độ
  phân giải và cần kết quả tải về nhanh, dễ hiểu.
- Ba JTBD:
  1. Chọn video, biết rõ chất lượng/chi phí/thời gian dự kiến và nâng lên
     1080p/1440p/2160p.
  2. Xem trước/so sánh kết quả, theo dõi tiến độ và tải đúng artifact của mình.
  3. Xử lý nhiều video, khôi phục sau lỗi/hủy/thử lại mà không mất credit hoặc
     để lại dữ liệu không kiểm soát.
- Device/viewport/region/language: Chrome desktop 1440×900; mobile 390×844;
  VI và `/en/`; timezone Asia/Saigon.
- Benchmark set: Topaz Video, TensorPix, AVCLabs Video Enhancer AI, HitPaw
  VikPea, Krea Video Upscaling, CapCut AI Video Enhancer.
- Dữ liệu test và giới hạn: video 10 giây do chủ sản phẩm chỉ định trong thư mục
  test; fixture SQLite/LocalStorage tách biệt; không chạy GPU lặp lại; không trả
  phí đối thủ; không blind-test output ở vòng này.
- Trọng số điều chỉnh: dùng nguyên trọng số LTT-AQA v1.0, khóa trước khi chấm.
- Performance/reliability budget: profile `compute`; success ≥90% khi có ít
  nhất 20 job terminal; queue wait P95 ≤120 giây; stale job = 0; event-write
  failure = 0. Runtime báo theo preset, không ép Fast và Quality chung một ngưỡng.
- In scope: manifest, UI, route/API, auth/ownership, credit, storage, worker/GPU,
  job history/log, i18n, responsive/a11y, benchmark và release gate.
- Out of scope: sửa code, deploy, thay model, chạy lại ma trận GPU 12 case, dữ
  liệu production, đánh giá chủ quan output không có panel mù.
- Người audit/người khóa logic: Codex / chủ sản phẩm LTT Studios.

## Gate A0

- [x] App/version/persona/JTBD rõ
- [x] Mode và ranh giới production rõ
- [x] Trọng số và benchmark khóa trước khi chấm
- [x] Không có hai cách hiểu tạo ra hai sản phẩm khác nhau

