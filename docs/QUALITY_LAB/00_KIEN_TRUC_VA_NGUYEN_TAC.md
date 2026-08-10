# LTT Quality Lab — kiến trúc và nguyên tắc đo chất lượng

Ngày khảo sát: 2026-08-10  
Trạng thái: **H31.1–H31.2 foundation đã BUILD local; chưa tải model học máy,
chưa calibrated, chưa deploy production**

## 1. Bài toán thật

`Job DONE` chỉ chứng minh tiến trình kết thúc, không chứng minh đầu ra tốt. LTT
cần một app operator riêng, tạm gọi **Quality Lab**, nhận đầu ra của một job và
chạy đúng bộ đánh giá theo loại sản phẩm. Nó không thay thế test code, audit
LTT-AQA hay kiểm thử người dùng; nó cung cấp bằng chứng đầu ra để ba việc đó bớt
cảm tính.

Máy phát triển hiện có NVIDIA GeForce RTX 5060 Ti, 16.311 MiB VRAM. Cấu hình
này phù hợp chạy tuần tự các evaluator cỡ vừa; không được lập lịch nhiều model
thị giác/âm thanh nặng cùng lúc hoặc suy 2 GPU 16 GB thành một GPU 32 GB.

## 2. Không có một “điểm chất lượng” vạn năng

Mỗi lần đánh giá phải trả về **vector bằng chứng**, gồm sáu lớp:

1. **Contract/kỹ thuật:** file giải mã được, codec, kích thước, FPS, duration,
   audio stream, timestamp và schema đúng.
2. **Đối chiếu chuẩn (full-reference):** có đầu ra chuẩn thì so PSNR/SSIM/LPIPS,
   VMAF, WER/CER, sai số thời gian... Không có chuẩn thì lớp này là `UNKNOWN`.
3. **Không tham chiếu/cảm nhận:** phát hiện nhiễu, mờ, banding, flicker, độ tự
   nhiên hoặc thẩm mỹ. Đây là proxy, không phải chân lý.
4. **Ngữ nghĩa/tác vụ:** bám prompt, đúng người/vật, đúng nội dung phụ đề, đúng
   đoạn highlight, đúng ràng buộc nghiệp vụ.
5. **UX/render:** Playwright kiểm tra luồng, trạng thái, nút, responsive,
   console/network; OCR và computer vision kiểm tra nội dung đã render.
6. **Vận hành:** latency, throughput, VRAM đỉnh, OOM, retry, credit, dung lượng,
   độ ổn định qua nhiều lần chạy.

Một lỗi bắt buộc như file hỏng, mất audio hoặc phụ đề bị cắt phải làm gate
`FAIL`; điểm trung bình đẹp không được che lỗi đó. Điểm tổng hợp chỉ được bật
sau khi tương quan với bộ chấm mù của con người và có version calibration.

## 3. Phương án kiến trúc

| Phương án | Điểm | Nhận xét |
|---|---:|---|
| A. App `apps/qualitylab/` dạng adapter, operator-only | **9/10** | Tận dụng Job, Storage, H30 observability; metric version hóa; không nhúng code đo vào từng app |
| B. Script/notebook rời | 6/10 | Ra nhanh nhưng khó phân quyền, lưu evidence, chạy lại và theo dõi xu hướng |
| C. API đánh giá thương mại | 5/10 | Tốn phí, rủi ro riêng tư/vendor lock-in, khó audit model |
| D. Nhúng evaluator vào từng app sản xuất | 4/10 | Trùng code, làm job khách chậm, khó nâng model đo độc lập |

**Chọn A.** App mới chỉ đọc artifact mà operator có quyền và tạo job đánh giá
riêng. App sản xuất không phải sửa trong MVP. Tự động đánh giá sau job là phase
sau, theo sampling/consent rõ ràng.

## 4. Hợp đồng dữ liệu đề xuất

Mỗi evaluation lưu:

- `evaluation_id`, `source_job_id`, opaque artifact key và owner/operator scope;
- `app_slug`, `output_kind`, profile/model/preset/language/resolution;
- evaluator name/version, model weight hash, metric direction/range/unit;
- dataset/calibration version, hardware/driver, thời gian và VRAM đỉnh;
- kết quả từng sample/frame/segment, aggregate, confidence và lý do;
- verdict từng dimension: `PASS | WARN | FAIL | UNKNOWN | NOT_APPLICABLE`;
- evidence key (ảnh vùng lỗi, timeline, JSON/HTML report), không nhét payload
  provider hoặc nội dung bí mật vào log;
- threshold profile và baseline run dùng để so regression.

Kết quả phải tái lập được: cùng artifact + evaluator/model/dataset version phải
cho sai số trong tolerance đã khai. Thay model đo hoặc threshold là calibration
version mới, không sửa đè lịch sử.

## 5. Ranh giới an toàn và trung thực

- Không dùng nội dung production của khách làm dataset nếu chưa có consent và
  retention policy. MVP dùng dữ liệu synthetic, tự sở hữu hoặc license rõ.
- Không tải model lúc worker đang chạy. Model được provision trước, pin phiên
  bản + checksum + license; thiếu model trả `UNKNOWN`, không fallback im lặng.
- Raw media tạm phải xóa sau evaluation; mặc định chỉ giữ metric, hash và vùng
  evidence tối thiểu theo chính sách artifact sau khi Q75 được chốt.
- Metric học máy phải có bộ chấm mù con người. Tương quan kém thì chỉ hiển thị
  “tham khảo”, không chặn release.
- Không gọi VMAF/PSNR trên hai video khác nội dung hoặc chưa căn chỉnh. VMAF có
  hành vi riêng với enhancement; Upscale phải dùng tập HR→degrade→restore đã
  kiểm soát và xem nhiều metric, không lấy một VMAF cao làm bằng chứng đủ.
- UI phải nói rõ `đã đo`, `không đo được`, `chưa có chuẩn` và evidence level,
  đúng nguyên tắc Honest UI trong `docs/quy_tac_audit.md`.

## 6. Nguồn kỹ thuật chính

- VMAF và enhancement/NEG: https://github.com/Netflix/vmaf
- LPIPS: https://github.com/richzhang/PerceptualSimilarity
- IQA-PyTorch/pyiqa: https://github.com/chaofengc/IQA-PyTorch
- DOVER no-reference video quality: https://github.com/VQAssessment/DOVER
- VBench video generation: https://github.com/Vchitect/VBench
- JiWER: https://github.com/jitsi/jiwer
- WhisperX: https://github.com/m-bain/whisperX
- pyannote metrics: https://github.com/pyannote/pyannote-metrics
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- COMET: https://github.com/Unbabel/COMET
- SacreBLEU: https://github.com/mjpost/sacrebleu
- DNSMOS/DNS Challenge: https://github.com/microsoft/DNS-Challenge
- STOI: https://github.com/mpariente/pystoi
- NISQA: https://github.com/gabrielmittag/NISQA
- Promptfoo: https://github.com/promptfoo/promptfoo
- WCAG captions: https://w3c.github.io/wcag/guidelines/22/#captions-prerecorded
- Netflix subtitle timing guide: https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394-Timed-Text-Style-Guide-Subtitle-Timing-Guidelines
