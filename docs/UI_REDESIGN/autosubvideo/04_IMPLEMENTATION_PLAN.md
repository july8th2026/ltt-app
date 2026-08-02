# UI-RD Auto Sub Video — kế hoạch AS0–AS9

Thứ tự bắt buộc. Phase trước chưa PASS thì phase sau không được đóng/deploy.

## AS0 — Khóa logic, baseline và rollback

- Dev trả lời Decision Gate; nếu chọn React/AppProject thì ghi quyết định nền tảng.
- Fixture cô lập đủ empty/imported/transcribing/editing/queued/running/done/error/
  cancelled/insufficient-credit/conflict; baseline 1440/1280/390/360.
- Chốt corpus test VI/EN, 1/2 speaker, noise/music, long-form; file user chỉ đọc,
  copy derivative vào vùng test cô lập.

**PASS:** G0–G2, worktree phân loại, rollback trước code. **Rollback:** docs-only.

## AS1 — Project/transcript contract và lifecycle

- Project owner-scoped, revision optimistic, autosave/idempotency, source video key,
  transcript words/cues/speakers/style/output settings; không nhét project dài vào Job.
- API create/list/get/update/archive; validation timing/text/style; CSRF/rate limit.
- Cancel/refund/retry cooperative contract cho ASR/preview/render; artifact policy.

**PASS:** owner khác 404; If-Match conflict; double save/submit; queued/running cancel,
race settle/refund; migration backup/rollback. **Rollback:** feature flag off, drain job,
giữ project/job/ledger audit.

## AS2 — Upload/import và ASR local

- Upload/probe R2/local theo Q48; import parser hiện có; extract audio FFmpeg.
- Copy/chắt lọc adapter Whisper nội tại vào app hoặc contract dùng chung đã duyệt:
  model cache, GPU/CPU fallback, word timestamps, VAD, VI/EN hardening, progress/cancel.
- Server quote theo duration/model; hold/settle riêng ASR; transcript project chỉ ghi
  khi job hoàn tất, retry không nhân đôi.

**PASS:** no-audio, corrupt, silent, VI/EN, model missing/OOM, cancel, insufficient
credit, word timing monotonic, benchmark WER proxy/RTF/VRAM. **Rollback:** tắt ASR,
import transcript vẫn hoạt động.

## AS3 — Studio shell và preview nền

- Jinja shell + editor island theo Decision Gate; layout ba cột/stepper/toolbar,
  desktop target từ ảnh; drawer/mobile target suy ra.
- Video player, overlay từ project state, empty/loading/error/offline/conflict; project
  selector và autosave state rõ.

**PASS:** keyboard/focus, no overflow, long text/project names, console/network sạch.
**Rollback:** route về form cũ; contract AS1/AS2 giữ tương thích.

## AS4 — Transcript editor và timeline

- Cue list/search/edit/add/delete/split/merge, undo/redo; speaker rename; timing input.
- wavesurfer Regions/Timeline self-host; predecoded peaks cho file dài; one caption
  track; snapping, playhead, seek và active cue đồng bộ.
- Autosave debounce + revision; offline queue/conflict không ghi đè âm thầm.

**PASS:** editing/timing invariant, 500/5000 cue performance, drag conflict, undo/
redo, mobile simplified. **Rollback:** timeline read-only/cue editor text giữ hoạt động.

## AS5 — Style, template, karaoke và render parity

- Mở schema style hiện có; font discovery/fallback; template owner/shared versioned.
- Preset preview sinh từ renderer nội bộ; keyword/word karaoke; animation subset chỉ
  khi ASS/libass và preview khớp; safe area theo aspect/resolution.
- Preview still/8s có quote/dedupe/cancel; cache theo project revision + style hash.

**PASS:** golden ASS + frame/clip visual set, missing font, unicode/ASS injection,
portrait/landscape/4K, reduced motion. **Rollback:** giữ 8 preset, ẩn custom/animation.

## AS6 — Speaker Labels và Translate tùy chọn

- Pyannote Community-1 local nếu Decision Gate/benchmark PASS; anonymous label,
  min/max speakers, manual rename; không nhận dạng danh tính.
- Gemini translate theo cue IDs bằng structured output; chunk/retry/dedupe, preserve
  timing/source track, quote/credit/provider error/redaction.

**PASS:** 1/2 speaker, overlap warning, token/model missing soft-disable; translation
đủ/mất/thừa cue bị từ chối, provider retry không trừ hai lần. **Rollback:** feature
flag off; transcript gốc không đổi.

## AS7 — Render/export/jobs

- Quote/confirm render; output preserve aspect, source/720/1080/4K, MP4/MKV/WebM;
  video + SRT/VTT/ASS/JSON/ZIP. Cooperative FFmpeg cancel, progress/ETA thật.
- Jobs panel owner-scoped; retry từ immutable project revision; preview/full phân biệt.

**PASS:** probe FPS/audio/resolution, artifact owner/Range/R2, no disk leak, cancel/
refund/race/retry/resume. **Rollback:** dừng nhận render mới, drain/cancel, giữ artifacts.

## AS8 — Hardening và benchmark

- ASR model A/B VI/EN; diarization tùy chọn; preview/render parity; long video/load.
- Fuzz transcript/ASS injection/path/key; quota/rate/CSRF/ownership; accessibility,
  mobile, offline/conflict; telemetry không filename/transcript/token.

**PASS:** app regression, GPU smoke, perf budgets, G0–G5; mọi DEFER/REJECT đúng UI.

## AS9 — Release/rollout/deploy

- Full pytest, secret scan, contract lint, dependency check, frontend typecheck/test/
  build/audit nếu có; Playwright 1440/1280/390/360 mọi state.
- Backup/restore, migration rehearsal, release, admin canary với test data, allowlist,
  public sau metric; production chỉ khi user yêu cầu deploy rõ.

**PASS:** G0–G7, health/worker/GPU/browser/console/network; quote/credit/artifact đúng.
**Rollback:** flags off, drain/cancel/settle, `app.previous`, không xóa ledger/project/audit.

## Nguồn nghiên cứu chính

- faster-whisper (MIT, word timestamps, VAD, GPU):
  https://github.com/SYSTRAN/faster-whisper
- WhisperX (BSD-2, forced alignment + diarization):
  https://github.com/m-bain/whisperX
- pyannote Community-1 (local, gated model, CC-BY-4.0 model):
  https://huggingface.co/pyannote/speaker-diarization-community-1
- wavesurfer.js v7 Regions/Timeline (BSD-3): https://wavesurfer.xyz/docs/
- FFmpeg ASS/libass: https://ffmpeg.org/ffmpeg-filters.html#ass
- WebVTT: https://www.w3.org/TR/webvtt1/
- Gemini structured output/pricing: https://ai.google.dev/gemini-api/docs/structured-output
  và https://ai.google.dev/gemini-api/docs/pricing

