# UI-RD Auto Sub Video — hiện trạng có bằng chứng

## Chuỗi vận hành hiện tại

`manifest → /autosubvideo → login/CSRF → upload R2 hoặc multipart ≤90MB → parse
transcript → submit_with_credit → worker probe duration thật/giữ thêm credit →
normalize/segment → ASS/SRT → FFmpeg libass/NVENC → storage → settle/download`.

## Năng lực đã có và nên tái sử dụng

- Parser SRT/VTT/ASS/SSA/JSON; normalizer overlap/short/long; 5 segmentation mode.
- 8 preset: default, TikTok bold, Reels clean, cinematic, meme, kids, punchline,
  word emphasis. Schema đã có custom font, màu, outline, shadow, box, alignment,
  safe area, highlight/karaoke và keyword highlight nhưng route chưa mở ra UI.
- `burn_preview()` đã tồn tại; full burn hỗ trợ MP4/MKV/WebM, NVENC/QSV/CPU,
  progress, audio, faststart. Route hiện chưa dùng preview.
- Worker đo duration thật và nâng hold trước encode; output resume idempotent;
  R2/Local và HTTP Range/artifact guard theo owner.
- `faster-whisper 1.2.1`, CTranslate2 4.7.1 và nhiều model Whisper đã cache;
  RTX 5060 Ti 16GB. App Tạo Clip Ngắn có adapter word timestamp, VAD, auto language,
  sửa lỗi tiếng Việt và chống hallucination để tham chiếu/copy có chọn lọc.
- `D:\BOT GEMINI` Auto Sub v3 có editor, split/merge/timing, timeline drag/zoom,
  safe area, custom style, template import/export/server store, preview, cancel,
  retry, job history và keyboard. Core normalizer/segmenter gần như đã được port;
  không được import chéo hay dùng storage tương đối của bản cũ.

## Khoảng trống và rủi ro

- Transcript bắt buộc; không ASR, word timing, diarization, translate.
- Không project/revision/autosave/conflict; thay đổi form mất khi reload.
- Không editor cue, search, undo/redo, waveform/timeline, video overlay live.
- Custom style/preview là năng lực “ngủ”: backend một phần có nhưng UI/API không nối.
- Không cancel cooperative xuống FFmpeg; không preview job/quote riêng; retry chỉ
  qua cơ chế chung, không có UI app.
- `upload-url` chưa nhận CSRF token; upload direct browser vẫn phụ thuộc Q48 CORS.
- Job params chứa toàn transcript; phù hợp file nhỏ nhưng không phải project store
  versioned và làm row phình với video dài.
- Chưa có retention/project delete, style template owner scope hoặc audit revision.
- Speaker “Linus/Luke” trong ảnh là nội dung minh họa. Diarization chỉ có thể sinh
  Speaker 1/2; không được suy đoán danh tính thật.

## Browser baseline 2026-08-02

Fixture cô lập `http://127.0.0.1:18101/autosubvideo`, test user, không production:

| Viewport | Kết quả |
|---|---|
| 1440×900 | form + empty history, document 1440×900, overflow X=false |
| 390×844 | document 390×1113, CTA hiện, overflow X=false |
| Console/network | 0 error/warning; `/estimate` 200 |

Baseline chỉ chứng minh UI hiện tại render sạch; chưa chứng minh các state queued/
running/done/error hoặc editor tương lai.

## Chấm điểm hiện trạng so với đích ảnh (10 điểm)

| Nhóm | Điểm | Nhận xét |
|---|---:|---|
| Core render/artifact | 7.5 | nền ASS/FFmpeg/storage tốt |
| Auth/owner/credit | 7.5 | đo giá thật; còn CSRF upload-url/cancel gap |
| Transcript intelligence | 2.0 | chỉ parse transcript có sẵn |
| Editing workflow | 1.5 | không project/editor/timeline |
| Style/render parity | 4.5 | schema mạnh nhưng UI không mở |
| Responsive/accessibility | 6.0 | form sạch; chưa có studio phức tạp |
| **Tổng có trọng số** | **4.4** | backend đáng tái dùng, sản phẩm chưa đạt studio |

