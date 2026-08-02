# Auto Sub Studio — contract khóa tại AS0

## Ranh giới nền tảng

`AppProject` là container generic, không biết cue/style/video của Auto Sub:

- `id`, `user_id`, `app_slug`, `name`, `schema_version`, `revision`, `status`;
- `payload` JSON do app validate; core chỉ giới hạn kích thước/độ sâu và cấm secret;
- `created_at`, `updated_at`, index owner/app/update;
- optimistic concurrency qua `If-Match`; owner khác luôn 404;
- archive mềm, không xóa job/ledger/artifact.

Auto Sub sở hữu schema payload version 1: source media, duration, transcript tracks,
speaker map, style, output, active step và metadata autosave. Job chỉ nhận immutable
snapshot của revision cần chạy; không đọc project đang thay đổi giữa lúc worker chạy.

## Multi-track v1

Mỗi track có `id`, `kind` (`source|translation|custom`), `language`, `name`,
`visible`, `z_index`, `style_id`, `cues`. Mỗi cue có stable ID, start/end, text,
speaker và word timing tùy chọn. Track ID/cue ID duy nhất; timing hữu hạn, không âm,
end > start; z-index không trùng trong các track visible.

## Job và tiền

- `autosubvideo.transcribe`, `.diarize`, `.translate`: 0 credit nhưng bắt buộc
  owner, CSRF, quota, rate-limit, dedupe, admission control và cooperative cancel.
- `autosubvideo.preview`: 0 credit, quota/dedupe/cache theo revision + style hash.
- `autosubvideo.render`: quote/confirm/hold/settle/refund theo Q5.

## Feature flag và rollback

`LTT_AUTOSUB_STUDIO_ROLLOUT=off|public`; production mặc định `off`, giá trị sai về
`off`. Form cũ tiếp tục là fallback trong AS1–AS8. Nếu migration/API lỗi: chuyển
flag `off`, dừng nhận auxiliary/render mới, drain/cancel/settle job, giữ project
để audit rồi downgrade một revision chỉ khi đã backup và xác nhận không còn writer.

## Corpus/viewport gate

- Fixture logic: empty/imported/transcribing/editing/queued/running/done/error/
  cancelled/quota/conflict.
- Corpus ASR: VI/EN, 1/2 speaker, noise/music, no-audio, silent, long-form.
- Browser: 1440×900, 1280×800, 390×844, 360×800; console và failed request = 0.
- File user cung cấp chỉ đọc; derivative test nằm trong thư mục tạm và phải dọn.
