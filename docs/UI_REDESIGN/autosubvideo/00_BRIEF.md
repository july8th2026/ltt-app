# UI-RD Auto Sub Video — brief và Decision Gate

**Mode:** ANALYZE · **Ngày:** 2026-08-02 · **App:** `autosubvideo` ·
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

## Decision Gate — chờ Dev khóa trước AS0/BUILD

| # | Câu hỏi | A | B | C | Khuyến nghị |
|---|---|---|---|---|---|
| 1 | Đích sản phẩm | Full project editor | Quick auto-caption form | Cả hai mode | **C**: Quick là entry, Editor là workspace |
| 2 | Kiến trúc UI editor | React/TypeScript island + Jinja shell | JS module thuần | Alpine port nguyên | **A**: state/timeline/autosave/undo đủ phức tạp |
| 3 | ASR mặc định | local faster-whisper large-v3/turbo | WhisperX ngay từ đầu | API cloud | **A**, benchmark rồi mới chọn model mặc định |
| 4 | Speaker Labels | pyannote Community-1 tùy chọn | cloud Precision-2 | hoãn | **A** sau benchmark; label vô danh, user tự đổi tên |
| 5 | Dịch transcript | Gemini theo batch + quote riêng | chỉ Whisper translate→English | hoãn | **A**, giữ timing/segment ID bằng structured output |
| 6 | Lưu project | Generic `AppProject` Postgres contract | JSON trong object storage | chỉ lưu job | **A**: revision/autosave/list/conflict đúng; đây là contract gap cần quyết định nền tảng |
| 7 | Style/animation | Toàn bộ style inspector + subset animation render thật | chỉ 8 preset | full motion graphics tùy ý | **A**; C bị REJECT vì ASS không bảo đảm parity tùy ý |
| 8 | Timeline | Một caption track + waveform/regions | multi-track caption | card cue, không waveform | **A**; multi-track DEFER |
| 9 | Output | giữ source + 720/1080/4K, preserve aspect | chỉ source | cho crop/reframe tự do | **A**; reframe thuộc app khác |
| 10 | Credit | quote/hold riêng ASR, diarization, translate, render; edit miễn phí | một gói trọn dự án | chỉ tính render | **A**: minh bạch và retry/idempotency rõ |
| 11 | Mobile | editor transcript/style + timeline giản lược/drawer | desktop-only | full timeline drag như desktop | **A** |
| 12 | Rollout | off→admin→allowlist→public | public ngay | admin-only lâu dài | **A** |

Sau khi Dev trả lời, lựa chọn làm thay đổi kiến trúc sẽ được ghi thành quyết định
nền tảng mới; ma trận và plan được cập nhật trước khi viết code.

