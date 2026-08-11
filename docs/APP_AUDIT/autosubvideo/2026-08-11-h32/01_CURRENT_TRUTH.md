# H32.1 — Current truth: AutoSub Video

## Kết quả journey thật

| Bước | Thiết lập | Kết quả |
|---|---|---|
| Upload | `VideoTest.mp4` | PASS; nhận 15s, 864×496 |
| Transcript | SRT tiếng Việt, 4 cue | PASS; timeline, preview, tìm kiếm và QA hoạt động |
| Preset | TikTok Bold | PASS; text trắng/active-word vàng, outline đen |
| Style | Montserrat, 64px, giữa màn hình | PASS; thể hiện trong output |
| Animation | Có None/Fade/Pop/Slide up, duration 180ms | Control tồn tại; chưa có golden parity cho mọi preset |
| Output | source, MP4, Standard, 1 track | PASS |
| Quote | 0,25 phút, source, MP4 | PASS; 2 credit, khoảng 200đ |
| Job | `71d7dd4f-f09d-427e-acfb-1217faad3bba` | PASS; queued 16:40:35, chạy 16:40:37, xong 16:40:40 |
| Encode | `h264_nvenc`, preset p4, CQ 23, audio copy | PASS |
| Credit | 1000 → 998 sau reload | PASS; đúng quote |
| Artifact | video, ASS, ZIP | PASS; tải video thành công |
| Persistence | reload project/job | PASS trong phiên fixture trước restart |

## Kiểm output

- File giao cho chủ sản phẩm:
  `AutoSubVideo/20260811_autosubvideo_tiktok-bold_source-mp4-standard_71d7dd4f.mp4`.
- 4.940.747 byte; H.264 + AAC; 864×496; 24 fps; 15,069 giây.
- Khung 2s và 6s xác nhận text, outline, word emphasis và Unicode tiếng Việt được
  burn đúng. Audio stream vẫn còn.
- Transcript QA 95/100 vì một cue dài hơn ngưỡng 50 ký tự; đây là cảnh báo hợp
  lệ của dữ liệu test, không phải lỗi render.

## Bề mặt tính năng hiện có

- Nhập SRT/VTT/ASS; tạo transcript; nhiều track; hide/show track; search.
- Diarization, dịch transcript, speaker label; capability được báo trạng thái.
- Cue add/split/merge/delete; chỉnh text/timing; waveform/timeline; undo/redo.
- 9 preset: LTT Brand, TikTok Bold, Reels Clean, Cinematic, Meme Punch, Kids
  Color, Punchline, Word Emphasis, Default.
- Style: font, size, text/outline/shadow/background colors, outline width,
  shadow offset, top/middle/bottom, karaoke mode/color, bold, italic.
- Animation: none, fade, pop, slide-up và duration.
- Output: source/720p/1080p/4K; MP4/MKV/WebM; draft/standard/high; export
  SRT/VTT/JSON/ASS/ZIP.
- Quote/hold/settlement, cancel render, progress, project job history, support ID.

## Thay đổi đã triển khai

- `apps/autosubvideo/manifest.py`: đổi `display_name` và nav label từ
  “Khắc phụ đề video” sang **“AutoSub Video”**.
- Đã restart fixture và xác minh title + page heading trên Chrome thật.
