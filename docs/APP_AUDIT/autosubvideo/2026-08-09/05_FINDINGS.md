# 05 — Findings: Auto Sub Studio

## P1 — phải đóng trước mở rộng thương mại

### F-001 — Upload/source không có staging contract và tạo orphan

- Nhóm/gate: security/privacy/storage; G2/G5/G8.
- `/upload-url` chỉ require login, không CSRF, allowlist extension/MIME, quota/rate
  hoặc upload-session. Source attach nhận bất kỳ key owner-prefix tồn tại; local
  và direct blob được ghi trước project commit/credit, replace không xóa source cũ.
- Ảnh hưởng: CSRF/resource abuse, file không phải video đi vào worker, dữ liệu cá
  nhân mồ côi sau abandon/conflict/archive, storage không kiểm soát.
- Evidence: EV-SRC-004, EV-BR-002.
- Fix: upload session owner+nonce+CSRF, expected size/hash/type, staging TTL,
  signature/container/server probe, promote atomic khi attach, cleanup/sweeper.
- Acceptance: cross-site/forged key/corrupt/oversize bị chặn; fail/abandon/crash
  không còn blob quá TTL; replace/archive/delete có retention audit.

### F-002 — Admission và giá render tin metadata client, không tính workload thật

- Nhóm/gate: money/economics/performance; G3/G7.
- Duration/resolution nguồn do browser gửi. Quote chỉ duration×quality; bỏ qua
  output pixels, codec, track. Schema nhận 24 giờ, transcribe chặn 2 giờ nhưng
  render/diarize không có cùng cap. Worker chỉ probe duration thật sau submit.
- Browser chứng minh source và 4K đều 1 credit; copy công bố tối đa 120 phút.
- Ảnh hưởng: báo giá sai, GPU/queue abuse, hold tăng hoặc job fail muộn, 4K/VP9
  có thể lỗ chi phí.
- Evidence: EV-SRC-005/006/008, EV-BR-004.
- Fix: probe server trước attach; admission matrix duration×pixels×codec×track;
  signed quote id/version; hard cap thống nhất; cost calibration P50/P95.
- Acceptance: source/720/1080/4K phản ánh tải; tamper metadata không đổi quote;
  >limit bị chặn trước hold; provider/infra variance đo riêng.

### F-003 — Autosave/conflict/offline có đường mất chỉnh sửa

- Nhóm/gate: data recovery/UX; G5.
- Autosave nuốt network error, không persistent outbox/retry; 409 chỉ báo message,
  không reload/merge/copy. Reload/tab close trước mutation tiếp theo làm mất edit.
  Global Ctrl/Cmd+Z/Y chặn native undo cả trong textarea/input.
- Ảnh hưởng: khách sửa transcript dài rồi mất công, conflict lặp không thoát.
- Evidence: EV-SRC-002/003.
- Fix: local durable draft/outbox theo project+revision, dirty indicator và
  beforeunload; conflict screen diff/merge/reload/save-copy; scope keyboard undo.
- Acceptance: offline→reload→online không mất edit; two-tab conflict có recovery;
  Ctrl+Z trong cue chỉ undo text, project undo chỉ khi canvas/editor focus.

## P2 — chất lượng/recovery/parity

### F-004 — Upload validation dựa extension/MIME và đọc file local toàn bộ RAM

Local fallback đọc tới 90 MB vào bytes; không magic/container probe trước storage.
Direct ticket cho content-type tùy client. Cần streaming cap tổng, probe và corpus
malformed/polyglot/truncated trước worker. Evidence EV-SRC-004.

### F-005 — QA phát hiện lỗi nhưng không chặn paid render

Browser tạo hai cue overlap, QA 70 nhưng dialog quote/hold vẫn mở. Cue end có thể
vượt source duration; schema không enforce ordering/overlap/duration. Cần fatal
vs warning taxonomy, disable submit và CTA jump/fix. Evidence EV-BR-004/EV-SRC-005.

### F-006 — Job AI miễn phí không có admission theo tải

Quota hiện là số job/ngày: transcribe 12×120 phút; diarize 6 job nhưng thiếu cap
duration route; translate 20×10k cue. 0 customer credit không đồng nghĩa 0 GPU/API
cost. Cần weighted minutes/cues/concurrency/queue budget và quota remaining UI.
Evidence EV-SRC-006.

### F-007 — True duration tăng hold ở worker quá muộn

Worker probe rồi `_dam_bao_giu_cho` trước encode. Khách có thể đã chờ queue mới
biết thiếu credit; quote ban đầu không còn là cam kết. Probe/quote/hold phải hoàn
tất trước job, worker chỉ verify và fail-safe. Evidence EV-SRC-008.

### F-008 — Capability và nhãn model mâu thuẫn

Capability nói WhisperX chỉ ready khi có sidecar, nhưng transcription có fallback
faster-whisper; nút enable theo source chứ không theo capability và vẫn ghi
“WhisperX”. Cần customer intent “Tạo transcript”, engine ở support detail, route
chọn capability thật và estimate/limitations rõ. Evidence EV-BR-001/EV-SRC-006.

### F-009 — Waveform tải toàn bộ video và âm thầm vẽ dữ liệu giả

`Waveform.tsx` fetch + `arrayBuffer` + `decodeAudioData` toàn source, song song
video Range. Nếu fail/codec unsupported, canvas vẽ pattern synthetic không nhãn.
Browser thấy GET 200 toàn file; reload/mobile lặp lại. Cần precomputed peak file
nhỏ/cache, loading/error/placeholder trung thực, hủy và memory budget. Evidence
EV-SRC-007/EV-BR-002/005.

### F-010 — AI job conflict báo hoàn tất dù kết quả chưa áp dụng

Worker auxiliary có thể trả `project_conflict=true` và artifact, nhưng UI polling
vẫn nói hoàn tất rồi reload. Customer không được chọn apply/merge/discard; translate
artifact conflict có thể orphan. Cần terminal outcome riêng và merge by stable cue id.
Evidence EV-SRC-002/006/009.

### F-011 — Project/history lifecycle gần như không có UI

API list/archive có nhưng React luôn mở active đầu tiên; không new/open/duplicate/
archive/delete/search. Job route lấy top 100 toàn app rồi mới filter project, nên
project cũ có thể hiện history rỗng; UI chỉ tải 20/hiển thị ngắn. Evidence EV-SRC-002/009.

### F-012 — EN A-Z và mobile editor không đạt

`/en/autosubvideo` vẫn title/copy/control/status tiếng Việt. 390 px cho thấy cue
lane/timeline bị cắt ngang bởi min-width; chưa có mobile precision mode. Cần locale
prefix-aware API/nav/messages và responsive staged panels/timeline zoom. Evidence
EV-BR-005/006.

### F-013 — Preview karaoke/style không phải render truth

Preview active word chia đều cue duration theo số từ thay vì `cue.words`; CSS không
chứng minh parity underline/bg_flash/safe area/wrap/animation với libass. Cần cùng
intermediate layout model và golden-frame matrix. Evidence EV-SRC-007, U-02.

### F-014 — Artifact/output lifecycle không atomic và không self-service

Render upload video/subtitles tuần tự; terminal failure sau partial upload có thể
để artifact trong storage dù refund. Không retention/delete/restore UI. Cần output
staging manifest, promote terminal atomic, cleanup idempotent và data-deletion.
Evidence EV-SRC-008/010.

### F-015 — Download R2 không đảm bảo tên/MIME/attachment

`/v` và `/f` redirect signed URL; không truyền response-content-disposition.
Video endpoint luôn `video/mp4` kể cả MKV/WebM. Cần signed response headers đúng
format, Range/resume và filename sanitized. Evidence EV-SRC-010.

### F-016 — Source key owner-prefix chưa đủ là authorization theo purpose

User có thể attach key output/subtitle/blob khác trong namespace của chính họ làm
video source. Ownership đúng nhưng purpose/token sai. Cần opaque upload-session id,
server resolve đúng kind/state, không nhận raw key từ browser. Evidence EV-SRC-004.

### F-017 — Timeline accessibility/precision thiếu

Cue block pointer-centric, waveform canvas không focus/action; không frame-step,
zoom/snap/nudge keyboard. Mobile horizontal lane không cung cấp overview/fit.
Học zoom/fit và tool modes từ Descript ở mức progressive disclosure. Evidence
EV-SRC-002/007, EV-BR-005, EV-MKT-001.

## P3 — polish/operability

### F-018 — Full-project clone cho mỗi keystroke có thể phình RAM

History giữ tối đa 80 `structuredClone` của project ≤1 MiB; transcript lớn có thể
tạo hàng chục MB và clone CPU mỗi input. Dùng command/diff history, coalesce typing,
đo memory với 10k cue. Evidence EV-SRC-002/003.

### F-019 — Manifest lifecycle `development` mâu thuẫn trạng thái public

UI đang public/default theo baseline H26 nhưng manifest vẫn development. Cần một
source of truth cho release ring/status; không đổi nhãn nếu gate chưa pass.
Evidence EV-SRC-001.

### F-020 — Copy và information architecture còn dev-facing

WhisperX/Pyannote/Gemini/capability cards chiếm diện tích customer; customer cần
intent “Tạo transcript/Phân vai/Dịch”, engine ở help/support. Thực hiện progressive
disclosure, giữ diagnostic id trong job detail. Evidence EV-BR-001/002.

### F-021 — Browser tải waveform lại sau reload/state change

Không cache peak/key/version; video GET 200 lặp ở desktop, mobile và EN navigation.
Peaks immutable theo source hash, CDN cache và abort khi source đổi. Evidence
EV-BR-002/005/006.

### F-022 — Test xanh che unhandled thread exception

Hai media progress test PASS nhưng thread `_drain_err` ném `TypeError` vì stderr
double không iterable. Cần test double đúng contract, join thread và cấu hình warning
thành fail cho `PytestUnhandledThreadExceptionWarning`. Evidence EV-TEST-001.

## Priority

| Thứ tự | Finding | Lý do |
|---:|---|---|
| 1 | F-001/F-004/F-016 | Đóng upload/source/orphan/security |
| 2 | F-002/F-006/F-007 | Đóng economics/admission/quote |
| 3 | F-003/F-010/F-011 | Không mất edit/kết quả/project |
| 4 | F-005/F-008/F-009/F-013 | Output/capability/preview trung thực |
| 5 | F-012/F-017 | EN/mobile/keyboard customer-ready |
| 6 | F-014/F-015 | Artifact/download lifecycle |
| 7 | F-018/F-021/F-022 | Performance và test hygiene |
| 8 | F-019/F-020 | Release truth và giảm dev-facing copy |

