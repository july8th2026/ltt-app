# LTT Quality Lab — ma trận bộ đo theo app

## Ưu tiên 1 — Upscale Video

### Bộ chuẩn bắt buộc

- Tập ảnh/video HR sở hữu hợp pháp; sinh LR có kiểm soát theo bicubic, blur,
  noise, compression và tổ hợp. Giữ seed, ffmpeg command và hash.
- Contract: decode error, kích thước đích, duration/FPS drift, audio sync và
  stream preservation, codec/profile, frame count.
- Full-reference: PSNR/SSIM chỉ làm baseline; LPIPS cho khác biệt cảm nhận;
  VMAF/SSIMPLUS-equivalent theo frame/video đã căn chỉnh; CAMBI/banding khi có.
- Temporal: flicker, optical-flow residual, motion consistency và duplicate/
  dropped frame; benchmark hiện tại chỉ có temporal delta toàn cục nên phải nâng.
- Artifact: halo/oversharpen, ringing, noise amplification, face/identity drift,
  text/OCR deformation.
- No-reference trên video thật: pyiqa (TOPIQ/MUSIQ/NIQE theo suitability) và
  DOVER-Mobile; hiển thị từng dimension, không đổi thành “đúng tuyệt đối”.
- Vận hành: sec/frame, FPS, VRAM đỉnh, GPU utilization, output size, OOM/retry,
  NVENC/CPU fallback và credit/thời gian.

### Gate MVP

File/stream phải PASS; chất lượng phải tốt hơn bicubic baseline trên đa số tập
degradation và không regress LPIPS/temporal/artifact quá tolerance. Threshold
chia theo preset, source class và target resolution; không dùng một ngưỡng 4K
cho mọi nguồn.

## Ưu tiên 2 — AutoSub Video

### Nội dung và thời gian

- Golden transcript Việt/Anh: WER, CER, MER/WIL; normalization version hóa,
  báo cả raw và normalized; hallucination-on-silence và bỏ sót speech.
- Punctuation/casing F1, số/tên riêng/thuật ngữ theo glossary.
- Word/segment start/end MAE, median, P95; coverage, overlap, gap, negative/
  non-monotonic timestamp; crossing shot-change.
- Diarization: DER/JER và speaker-attribution accuracy; overlapping speech là
  slice riêng vì WhisperX/diarization có giới hạn đã công bố.
- Translation: COMET + chrF/SacreBLEU + glossary consistency; vẫn cần human
  spot-check cho nghĩa, giọng điệu và tên riêng.

### Trình bày và render

- CPS/WPM, ký tự mỗi dòng, số dòng, min/max duration, orphan word, line break;
  các ngưỡng theo ngôn ngữ/profile, không hardcode một chuẩn cho mọi nội dung.
- Safe-area, bounding box, clipping, contrast, font size, stroke/shadow,
  karaoke/animation timing; sampling đầu-giữa-cuối của mọi cue.
- OCR frame burn-in so với cue dự kiến (PaddleOCR có model tiếng Việt), đồng
  thời kiểm pixel vùng subtitle để bắt chữ không render hoặc màu nền che chữ.
- A/V duration sync, audio preservation, SRT/ASS parse round-trip và export.
- Browser A–Z: upload→transcribe→edit→style→preview→render→download, responsive,
  keyboard, progress/cancel/retry, console và failed request.

### Gate MVP

Không cue ngoài duration, không timestamp đảo, không clipping/safe-area FAIL,
không mất audio. WER/alignment/DER được chấm theo golden slice (sạch, ồn, nhiều
speaker, tiếng Việt vùng miền) và phải báo confidence; chưa có truth thì UNKNOWN.

## Ưu tiên 3 — Seedance/Tạo Video AI

- Contract: playable, duration/aspect/resolution/audio đúng request, không frame
  hỏng/đen kéo dài, không duplicate bất thường.
- VBench subset phù hợp custom input: subject/background consistency, temporal
  flicker, motion smoothness, dynamic degree, aesthetic/imaging quality.
- Prompt/reference adherence theo object/action/color/layout/camera; identity
  và reference similarity chỉ dùng khi có quyền xử lý khuôn mặt.
- OCR phát hiện chữ lỗi khi prompt yêu cầu text; safety/moderation; watermark.
- Human pairwise A/B theo prompt suite LTT; ít nhất 3 rater, random thứ tự và
  ẩn model. VideoScore 8B chỉ khảo sát phase sau vì quá nặng cho MVP 16 GB.
- API latency, token/credit actual, provider failure/retry và artifact lifecycle.

## Ưu tiên 4 — Tạo ảnh AI và Thumbnail

- Contract kích thước/format/alpha/corruption.
- Prompt-image alignment (CLIPScore-style), human preference (HPS) và pyiqa;
  luôn tách semantic khỏi aesthetic/technical.
- Reference/identity/style consistency; anatomy/face/hand slice; OCR và text
  legibility; logo/brand color; safe crop theo aspect.
- Thumbnail: title promise, focal point, contrast ở kích thước nhỏ, mobile crop,
  brand fit và human A/B. Không tuyên bố dự đoán CTR nếu chưa có telemetry A/B
  người dùng thật.

## Ưu tiên 5 — Tạo Clip ngắn

- Golden highlight interval: temporal IoU/mAP, boundary MAE, coverage/redundancy.
- Transcript/semantic relevance của đoạn chọn, hook đầu clip và diversity.
- Scene-cut integrity, subject crop/tracking occupancy, face/active speaker;
  subtitle dùng trọn pack AutoSub; A/V sync và loudness.
- Package SRT timestamp phải tương đối theo clip, artifact/download đầy đủ.

## Ưu tiên 6 — Chat, Kịch bản, Prompt AI

- Schema/ràng buộc/output format, language, length, banned content, citation.
- Golden facts: groundedness, citation precision/recall, contradiction và
  hallucination; pairwise rubric cho usefulness/clarity/style.
- Prompt regression + red-team bằng cấu hình version hóa (Promptfoo là adapter
  khả thi); judge model phải pin version và hiệu chuẩn với human, không tự chấm
  chính mình rồi coi là truth.
- Latency, token, credit, retry, context preservation, stop/delete/privacy.

## Ưu tiên 7 — LTT Agent AI

- Graph validity, type compatibility, cycle policy, input/output mapping.
- Task completion và exact-once; resume/cancel/retry/refund; child-job lineage.
- Chạy node độc lập và workflow E2E. Mỗi node gọi đúng pack chất lượng của loại
  output; một node bắt buộc FAIL thì workflow FAIL, không lấy trung bình che đi.
- User journey Playwright: tạo node, nối dây, run node, run graph, inspect,
  history, reload, mobile/read-only, error recovery.

## Media/audio và phạm vi đóng băng

- Media Tools: frame/timestamp/merge exactness, decode/stream preservation.
- Audio Enhance/Voice: loudness EBU R128, clipping/silence, STOI khi có clean
  reference, DNSMOS/NISQA khi không có, speaker similarity chỉ có consent.
- Socialbot đóng băng: chỉ contract/authorization/operational regression.
- Demo/Kịch bản/Media soft-retired: không ưu tiên xây quality pack sản phẩm;
  chỉ giữ runtime contract đến khi dependency di trú xong.

