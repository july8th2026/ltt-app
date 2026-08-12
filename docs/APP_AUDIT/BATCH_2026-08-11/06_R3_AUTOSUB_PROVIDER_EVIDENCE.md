# H33.R3.1 — AutoSub provider/output evidence

**Ngày:** 2026-08-12
**Phạm vi:** môi trường cô lập cổng 8153, CSDL/data/test user riêng. Production
8100 không bị đọc, sửa hoặc deploy.

## 1. Engine smoke trên GPU thật

Nguồn là clip speech 45,13 giây trích từ tài nguyên test người dùng cung cấp.
Không dùng file SRT đi kèm làm ground truth vì nội dung đó không khớp lời nói
thật trong video. Vì vậy WER được ghi `UNKNOWN`, không biến thành PASS/FAIL giả.

| Model | Segment | Aligned word | Thời gian | RTF | Timing |
|---|---:|---:|---:|---:|---|
| Tiny | 6 | 129 | 15,469s | 0,343 | monotonic |
| Large-v3 | 9 | 131 | 22,492s | 0,498 | monotonic |

Hai model chạy bằng LTTWhisperX trên GPU1 và đều sinh transcript/alignment. Đây
là **engine smoke PASS**, chưa phải chuẩn chất lượng ngôn ngữ.

## 2. Browser A–Z như khách hàng

1. Đăng nhập test user 1.000 credit, upload clip speech thật.
2. Bấm WhisperX. Lần đầu worker hoàn thành nhưng UI đứng ở “đang chạy”.
3. Nguyên nhân: đường transcribe không tạo `auxJob`, nên effect poll không chạy.
   Đã sửa và thêm Vitest khóa queued→done→reload project.
4. Chạy lại: UI poll `/api/jobs/<id>`, worker claim GPU1, hoàn thành/release
   lease, Studio tải lại project thành 1 track/9 cue.
5. Quote render Standard 45 giây là 4 credit; confirm, worker NVENC hoàn thành,
   số dư sau reload 996. Có MP4, ASS, SRT, VTT, JSON và ZIP.
6. `ffprobe`: H.264 + AAC, 1920×1080, 30 fps, 45,133 giây, khoảng 69,9 MB.
   Frame 3,5 giây xác minh subtitle đã burn-in, dễ đọc và nằm đúng vùng dưới.
7. Desktop và mobile 390×844 không overflow; console cuối cùng 0 lỗi.

## 3. Preflight trước paid render

- Overlap, cue rỗng hoặc cue vượt source: HTTP 422 trước quote/hold.
- Cue dưới 0,5 giây, trên 20 ký tự/giây hoặc vượt line budget: hiện cảnh báo
  trong confirmation nhưng khách vẫn được quyết định tiếp tục.
- API lồng dưới route app nay trả JSON an toàn theo Q88. Trước đó global handler
  trả HTML làm frontend mất nội dung lỗi 422.
- Preflight chỉ lưu count/score/code, không đưa transcript khách vào evidence.

## 4. Kết luận gate

| Gate | Kết quả | Ghi chú |
|---|---|---|
| Local engine/worker/GPU | PASS | Tiny và Large-v3 có output/alignment |
| Studio polling/project reload | PASS | lỗi thật đã tái hiện, sửa và khóa test |
| Paid render/output/ledger | PASS | 4 credit; MP4 + subtitle bundle |
| Fatal/warning preflight | PASS | browser negative + warning path |
| ASR accuracy VI/EN | CONDITIONAL | chưa có corpus ground truth; WER UNKNOWN |
| Diarization/translation | BLOCKED | chưa có pyannote/Gemini evidence thật |
| Source draft lifecycle | PASS | Q89 owner/project attach, TTL/recovery/sweep |

**Quyết định:** AutoSub đạt **technical conditional PASS**, chưa đạt commercial
quality/release PASS. Không hạ chuẩn Q50/Q83 để hợp thức hóa thiếu evidence.

## 5. Việc còn lại theo thứ tự

1. Tạo corpus VI/EN có license/consent và transcript chuẩn; đo WER, timing drift.
2. Chạy pyannote có speaker ground truth và Gemini translation có human review.
3. Sau AutoSub mới chuyển tuần tự Prompt → Image → Clip trên exact RC.
