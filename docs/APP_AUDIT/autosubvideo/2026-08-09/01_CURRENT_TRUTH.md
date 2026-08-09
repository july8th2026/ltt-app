# 01 — Current Truth: Auto Sub Studio

## Sơ đồ đầu-cuối

`manifest → React Studio → AppProject revision/autosave → upload/source attach →
import hoặc ASR → cue/track/style/timeline → quote/hold → worker FFmpeg/libass →
video + ASS/SRT/VTT/JSON/ZIP → job history/download/refund hoặc settle`

Luồng phụ: `source + transcript → Pyannote diarize` và `track → Gemini translate`.

## Inventory

| Thành phần | Hiện trạng | Evidence | Confidence | Rủi ro chính |
|---|---|---|---:|---|
| Manifest | Public UI nhưng lifecycle còn `development`; 4 job type | EV-SRC-001 | E4 | Trạng thái vận hành không trung thực |
| Studio UI | React 4 bước, 3 cột, timeline, preview, style, QA | EV-SRC-002, EV-BR-001 | E4 | Project lifecycle thiếu; mobile/EN fail |
| Project | Generic AppProject, revision optimistic, payload ≤1 MiB | EV-SRC-003 | E4 | Conflict/offline không recovery; history RAM lớn |
| Input | Local/direct R2, metadata lấy từ browser | EV-SRC-004, EV-BR-002 | E4 | Ticket không CSRF/allowlist; tin metadata/MIME/key |
| Transcript | SRT/VTT/ASS/SSA/JSON; cue/track/speaker; QA | EV-SRC-005, EV-BR-003 | E4 | Vẫn cho quote/render khi QA lỗi |
| AI phụ | WhisperX/faster-whisper, Pyannote, Gemini | EV-SRC-006 | E4 | Capability/copy mâu thuẫn; free quota không weighted |
| Preview/style | 9 preset, CSS overlay, animation/highlight | EV-SRC-007 | E4 | Preview karaoke không dùng word timing thật |
| Render | Snapshot SHA, libass/FFmpeg, multi-track, nhiều artifact | EV-SRC-008, EV-TEST-001 | E4 | Giá bỏ qua resolution/format; duration thật kiểm quá muộn |
| Job/history | Owner-scoped cancel render; retry render terminal | EV-SRC-009 | E4 | Filter sau top-100; UI chỉ project gần nhất/8 job |
| Storage/download | Owner prefix, Range local, signed URL R2 | EV-SRC-010 | E4 | MIME/filename redirect và retention/orphan chưa kín |
| Test | 36 Python + 13 Vitest PASS | EV-TEST-001 | E4 | 2 warning thread bị test xanh che; nhiều journey chưa phủ |

## Nội tại nên giữ và tái sử dụng

| Năng lực | Vị trí | Giá trị | Giới hạn hiện tại |
|---|---|---|---|
| Project revision + payload guard | `platform_core/app_projects.py` | Ownership, conflict, size/depth/secret guard | Không merge/outbox/pagination |
| Job/credit/refund | `platform_core` | Contract chung, immutable snapshot | Quote workload chưa canonical |
| Parser đa định dạng | `apps/autosubvideo/parsers.py` | Import nhanh, không phụ thuộc AI | Cần corpus lỗi/encoding lớn hơn |
| ASS injection sanitization | `ass_builder.py` | Giảm rủi ro directive injection | Preview không đồng nhất render |
| Multi-track artifacts | `project_render.py` | ASS/SRT/VTT/JSON/ZIP | Track phụ bị ép top, chưa layout riêng |
| ASR fallback | `transcription.py` | Có đường chạy khi sidecar thiếu | UI/capability vẫn gọi “WhisperX” |
| Typed style/preset | schema + style registry | Reuse brand/style tốt | Thiếu style per-track và parity proof |
| Cooperative render cancel | progress callback + process cleanup | Có thể ngắt FFmpeg | Pyannote process tree chưa đồng nhất |

## Unknown/baseline defect

| ID | Unknown/defect | Cách xác minh | Chặn gì |
|---|---|---|---|
| U-01 | WER/word timing/speaker accuracy theo tiếng Việt và noise | Golden corpus + human review | G1/COMMERCIAL |
| U-02 | Preview so với pixel render trên 9 preset/4 aspect | Golden frame diff | G4 |
| U-03 | Production success/queue/render P95 và GPU utilization | ≥20 terminal/workload class | G7/G8 |
| U-04 | R2 lifecycle/CORS/content-disposition ngoài repo | Operator audit policy | G2/G5/G8 |
| U-05 | Actual cost theo duration×pixels×codec×track | Telemetry + calibration | G3 |
| U-06 | Browser memory với video 30/60/120 phút | Performance trace/device matrix | G7 |

