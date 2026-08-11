# H32.7 — Tổng audit sáu tool

## Dashboard toàn batch

| Tool | Q | M | E | Gate | Kết luận ngắn |
|---|---:|---:|---:|---|---|
| AutoSub Video | 70 | 69 | 88 | CONDITIONAL | Render/style/SRT pass; AI transcript/diarization chưa E4 |
| Prompt AI | 72 | 68 | 86 | CONDITIONAL | Composer/catalog/preflight pass; provider E4 chưa có |
| Tạo ảnh AI | 74 | 70 | 88 | INTERNAL | Hai mode/handoff pass; provider và pricing parity còn mở |
| Tạo Clip ngắn | 77 | 58 | 95 | INTERNAL | Fast canary pass; tier/count/genre/editor matrix còn thiếu |
| Tạo Video Seedance | 63 | 64 | 84 | **BLOCKED** | Visual pass; P0 billing/canonical quote kế thừa |
| Upscale Video | 72 | 57 | 94 | **BLOCKED** | 17/17 technical; upload/lifecycle/calibrated quality còn mở |
| **Trung bình tham khảo** | **71,3** | **64,3** | **89,2** | **BLOCKED** | Gate theo rủi ro cao nhất, không theo trung bình |

## Phạm vi đã hoàn tất

- Sáu folder yêu cầu và tài nguyên đã được kiểm kê/read-only.
- Sáu app được xử lý tuần tự; mỗi app có hồ sơ 00–07 và evidence tương ứng.
- Mọi thay đổi customer-facing đã được render trên browser desktop/mobile,
  kiểm console và failed application request ở phase của chính app đó.
- AutoSub, Clip và Upscale có media/output/runtime thật. Seedance theo yêu cầu
  visual-only; Prompt/Image không giả provider output khi provider chưa sẵn.
- Targeted test, frontend test/build và quick gate được ghi bằng kết quả thật
  trong từng hồ sơ/nhật ký.

## Release blockers hợp nhất

| Thứ tự | Blocker | App | Gate mở lại |
|---:|---|---|---|
| 1 | Actual charge/canonical hold của Seedance | Tạo Video | G3 exactly-once + cap/reconcile/refund pass |
| 2 | Upload session và artifact lifecycle | Upscale, Clip, Image/Video | G2/G5 abuse + sweeper/reconcile pass |
| 3 | Provider E4/output quality | Prompt, Image, AutoSub AI | Canary thật + ownership/credit/output pass |
| 4 | Calibrated HR/blind quality | Upscale | Dataset hợp lệ + human agreement + threshold version |
| 5 | Tier/count/genre/cancel/recovery matrix | Clip và các job dài | E2/E3/E4 matrix pass |
| 6 | Live progress/retry/history/draft recovery | Nhiều app | State/recovery browser regression pass |

Không có một lệnh deploy chung an toàn ở trạng thái này. `BLOCKED` không có
nghĩa code kỹ thuật H32 hỏng; nó có nghĩa chưa được mở rộng phát hành thương
mại cho đến khi blocker liên quan đóng.

## Điểm mạnh đã hình thành

- Credit/job/owner contract dùng chung và nhiều luồng đã có canary thực.
- Lợi thế handoff nội bộ Seedance → Upscale và catalog Prompt AI.
- Browser fixture cô lập, GPU sampler fail-closed, Quality Lab không ngụy tạo
  metric chưa calibrate.
- UI nhất quán hơn: progressive disclosure, customer wording, responsive focus,
  lịch sử/log có lối vào.

## Điểm yếu hệ thống

- Capability thị trường còn thấp ở temporal restoration, denoise/deblur,
  transcript/diarization AI và recovery dài hạn.
- Upload/object lifecycle chưa có một state machine dùng chung hoàn chỉnh.
- Một số app có E3 tốt nhưng thiếu E4 provider/production SLO; không được xem
  screenshot đẹp là core outcome pass.
