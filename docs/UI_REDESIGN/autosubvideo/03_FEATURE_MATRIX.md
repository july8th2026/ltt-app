# UI-RD Auto Sub Video — ma trận tính năng

Điểm: Fit/Value/Reuse/Feasible/Quality 0–3, trừ Risk 0–3. `Net` tối đa 15.
Decision Gate có quyền thay quyết định sơ bộ trước BUILD.

| ID | Feature | Hiện trạng | Quyết định | F/V/R/Fe/Q−Risk | Net | Acceptance cốt lõi |
|---|---|---|---|---:|---:|---|
| AS-01 | Studio shell/stepper | form | RESTYLE/BUILD | 3/3/2/3/3−1 | 13 | state thật, deep-link/reload không mất |
| AS-02 | Project/autosave/revision | không | BUILD | 3/3/1/2/3−2 | 10 | owner, revision/If-Match, conflict, retry offline |
| AS-03 | Upload/probe/R2 | có | EXTEND | 3/3/3/3/2−1 | 13 | progress, cancel, cap thật, fallback sạch |
| AS-04 | Import SRT/VTT/ASS/JSON | có | KEEP/RESTYLE | 3/3/3/3/2−0 | 14 | round-trip và validation |
| AS-05 | ASR word timestamp/VAD | dependency + adapter nội tại | BUILD | 3/3/3/3/3−1 | 14 | benchmark VI/EN, confidence, cancel, fallback |
| AS-06 | WhisperX alignment | chưa | DEFER | 2/2/1/1/3−2 | 7 | chỉ bật nếu timing thắng benchmark đáng kể |
| AS-07 | Speaker diarization | chưa | BUILD optional | 2/2/1/2/2−2 | 7 | anonymous speaker, rename, overlap warning |
| AS-08 | Translate | provider nền có, service chưa | BUILD | 2/2/2/2/2−2 | 8 | preserve cue IDs/timing, quote, schema validation |
| AS-09 | Cue editor/search | BOT có logic tham chiếu | BUILD | 3/3/3/3/3−1 | 14 | edit/add/delete/split/merge/search/undo/redo |
| AS-10 | Timing editor | BOT có logic | BUILD | 3/3/3/2/3−1 | 13 | no overlap/negative, keyboard, server validate |
| AS-11 | Waveform/timeline | chưa; wavesurfer phù hợp | BUILD | 3/3/1/2/3−1 | 11 | seek/drag/resize sync, large-file peaks fallback |
| AS-12 | Thumbnail strip | chưa | DEFER | 1/1/1/2/1−1 | 5 | chỉ làm khi waveform/cue chưa đủ |
| AS-13 | Live subtitle preview | burn_preview có | EXTEND | 3/3/3/2/3−1 | 13 | cùng style payload, sample frame/clip parity |
| AS-14 | 8 preset | có | KEEP/RESTYLE | 3/3/3/3/2−0 | 14 | thumbnail sinh từ renderer nội bộ, không ảnh giả |
| AS-15 | Full style inspector | schema có phần lớn | EXTEND | 3/3/3/2/3−1 | 13 | server normalize, font fallback, parity tests |
| AS-16 | Karaoke/word emphasis | có một phần | EXTEND | 3/3/3/2/3−1 | 13 | word timestamps → ASS tags chính xác |
| AS-17 | Animation subset | chưa | BUILD | 2/2/2/2/2−1 | 9 | fade/pop/slide có preview/render parity |
| AS-18 | Arbitrary motion graphics | không | REJECT | 1/1/0/0/2−3 | 1 | thuộc compositor khác, không giả bằng CSS |
| AS-19 | Style template store | BOT có bản cũ | BUILD | 3/2/2/2/2−1 | 10 | owner/shared role gate, version/import/export |
| AS-20 | Brand Kit generic | không | DEFER | 2/2/0/1/2−2 | 5 | cần contract asset/brand dùng chung |
| AS-21 | Preview job | function có | EXTEND | 3/3/3/3/3−1 | 14 | quote thấp, dedupe, cancel, artifact riêng |
| AS-22 | Full render/export ZIP | có video/SRT/ASS rời | EXTEND | 3/3/3/3/3−1 | 14 | video + SRT/VTT/ASS/JSON/ZIP owner-only |
| AS-23 | Cancel/refund/retry | core một phần, app UI thiếu | BUILD | 3/3/2/2/3−1 | 12 | cooperative FFmpeg/ASR, race/idempotent refund |
| AS-24 | Output resolution/aspect | source-only | EXTEND | 2/2/2/3/2−1 | 10 | preserve aspect; no silent crop/stretch |
| AS-25 | Jobs/history | 12 card | EXTEND | 3/2/3/3/2−1 | 12 | queued/running/done/error/cancelled/retry |
| AS-26 | Multi-track captions | không | DEFER | 1/1/0/1/2−2 | 3 | cần track/language/export contract riêng |
| AS-27 | Named speaker recognition | không | REJECT | 1/1/0/0/1−3 | 0 | privacy/accuracy; chỉ user tự đặt tên |
| AS-28 | Mobile full precision drag | không | REJECT | 1/1/0/1/1−2 | 2 | mobile dùng editor giản lược, không giả desktop |

## Kết luận công nghệ sơ bộ

- **Mặc định:** `faster-whisper` local, `large-v3`/turbo benchmark trên RTX 5060 Ti,
  word timestamps + Silero VAD; không tải lại model mỗi job.
- **Diarization tùy chọn:** pyannote Community-1 local, token/model gated, telemetry
  off mặc định; benchmark VRAM/DER tương đối trước rollout.
- **WhisperX:** ứng viên alignment Pro, không dependency mặc định ban đầu.
- **Timeline:** wavesurfer.js v7 Regions + Timeline, self-host/pin; predecoded peaks
  cho video dài. Project/server vẫn là source of truth.
- **Translation:** Gemini structured JSON theo cue ID qua API pool, job/quote riêng;
  không thay timing và không gửi storage key.
- **Render:** ASS/libass + FFmpeg hiện có; CSS preview không được coi là bằng chứng
  nếu output ASS khác.

