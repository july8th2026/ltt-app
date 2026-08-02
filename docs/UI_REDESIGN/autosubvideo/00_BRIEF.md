# UI-RD Auto Sub Video — brief và Decision Gate

**Mode:** DECISION LOCKED · **Ngày:** 2026-08-02 · **App:** `autosubvideo` ·
**Route:** `/autosubvideo` · **Ảnh:** `G:\My Drive\AI\A\New folder\AUTO SUB.png`
(1680×935, desktop, state Style có video/transcript).

## Mục tiêu sản phẩm

Nâng app từ form “video + transcript có sẵn → burn” thành subtitle studio thật:
upload → tự chép lời hoặc nạp transcript → sửa nội dung/timing → chọn style/
animation có preview đúng render → báo giá → export. Không tạo runtime, sổ credit,
storage hay engine render thứ hai.

## Phạm vi đã chắc chắn

- Giữ slug, job/worker, credit, R2/Local, FFmpeg/libass, ASS/SRT builder, 8 preset,
  normalizer, segmenter và owner-scoped artifact hiện có.
- Internal-first: chọn lọc logic editor/preview/template/cancel trong
  `D:\BOT GEMINI` (chỉ đọc), và engine `faster-whisper` đã có trong dự án.
- Không ImageGen. Khi BUILD, chỉ dùng CSS/icon LTT và crop từ ảnh user cung cấp;
  không lấy khuôn mặt/video/nhãn hiệu trong ảnh làm asset production.
- Ảnh chỉ có desktop. Mobile là thiết kế suy ra và bắt buộc kiểm 390/360 px.
- Chưa deploy và chưa thay code trong lượt ANALYZE này.

## Decision Gate — đã khóa trước AS0/BUILD

| # | Câu hỏi | A | B | C | Đã chọn |
|---|---|---|---|---|---|
| 1 | Đích sản phẩm | Full project editor | Quick auto-caption form | Cả hai mode | **C** |
| 2 | Kiến trúc UI editor | React/TypeScript island + Jinja shell | JS module thuần | Alpine port nguyên | **A** |
| 3 | ASR mặc định | local faster-whisper large-v3/turbo | WhisperX ngay từ đầu | API cloud | **B** |
| 4 | Speaker Labels | pyannote Community-1 tùy chọn | cloud Precision-2 | hoãn | **A** |
| 5 | Dịch transcript | Gemini theo batch | chỉ Whisper translate→English | hoãn | **A** |
| 6 | Lưu project | Generic `AppProject` Postgres contract | JSON trong object storage | chỉ lưu job | **A** |
| 7 | Style/animation | Toàn bộ style inspector + subset animation render thật | chỉ 8 preset | full motion graphics tùy ý | **A** |
| 8 | Timeline | Một caption track + waveform/regions | multi-track caption | card cue, không waveform | **B** |
| 9 | Output | giữ source + 720/1080/4K, preserve aspect | chỉ source | cho crop/reframe tự do | **A** |
| 10 | Credit | quote/hold riêng ASR, diarization, translate, render; edit miễn phí | một gói trọn dự án | chỉ tính render | **C** |
| 11 | Mobile | editor transcript/style + timeline giản lược/drawer | desktop-only | full timeline drag như desktop | **C** |
| 12 | Rollout | off→admin→allowlist→public | public ngay | admin-only lâu dài | **B** |

Các lựa chọn trên đã được khóa thành **Q49–Q50**. Cách hiểu bắt buộc:

- “Chỉ tính render” nghĩa là ASR/diarization/translation vẫn là job server-side
  có quota, rate-limit, dedupe và admission control, nhưng báo giá **0 credit** cho
  khách. Full render mới quote/confirm/hold/settle/refund theo Q5.
- Multi-track là dữ liệu project thật: mỗi track có language/type/cues/style/
  visibility và z-order tất định; export từng track, render các track được chọn.
- Full mobile drag phải có pinch/zoom, touch target, snapping và numeric fallback;
  không được tuyên bố parity chỉ vì desktop responsive.
- WhisperX là đường mặc định ngay AS2; nếu alignment model không hỗ trợ ngôn ngữ,
  fallback word timestamp phải rõ trên UI, không làm mất transcript.
- “Public ngay” là **không rollout sản phẩm qua admin/allowlist**. Feature vẫn off
  trong lúc build; chỉ mở thẳng public sau AS0–AS9, G0–G7, migration rehearsal,
  browser/GPU smoke và rollback rehearsal đều PASS.
