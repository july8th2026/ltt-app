# 01 — Current Truth

## Kiến trúc LTT hiện có

```text
React Flow Canvas
  → Workflow API + optimistic revision/autosave
  → Plan v1 conversion
  → deterministic validator (typed refs, cycle, limits, permissions)
  → quote → create run → approve/schedule
  → credit hold → DAG executor → verifier/retry → settle/refund
  → artifacts, checkpoint, replay/restore
```

Đây là nền phải tái sử dụng, không xây runtime/queue/credit/storage thứ hai.

## Tài sản đã đáp ứng

| Năng lực | Trạng thái | Bằng chứng/ghi chú |
|---|---|---|
| Canvas React Flow, drag/drop, zoom, minimap | LIVE | E-LTT-01/E-CODE-01 |
| Undo/redo/copy/paste/duplicate/delete/auto layout | LIVE | source + toolbar |
| Typed port tại client và server | LIVE | `connectionAllowed`, validator `port_type` |
| Cycle/dependency/fan-out/retry/budget validation | LIVE | validator; mạnh hơn PlenX quan sát được |
| Autosave + revision conflict | LIVE | 800 ms, `If-Match`; mạnh hơn last-write-wins |
| AI dựng Canvas từ goal | LIVE | planner + `/workflows/plan` |
| Quote/approve/schedule/hold/settle/refund | LIVE | run/credit contract |
| Error branch, checkpoint, cancel, run-again, restore | LIVE | Canvas + executor/run API |
| Clone/import/export workflow | LIVE | API/UI |
| 7 công cụ thực thi thật | LIVE | image.generate, image.thumbnail, text.script, video.generate, video.subtitle, video.short_clips, video.upscale |
| 4 provider registry | PARTIAL | Gemini, apiai, cheapkeyai, BytePlus, PlenX connector; công cụ đang lọc hẹp provider |
| Desktop adaptive width | LIVE local | stage 1205×696 trong viewport 1720×940 |
| Mobile Canvas | PARTIAL | ≤640 px chỉ xem; không parity chỉnh sửa |

## Tool inventory hiện hành

| Tool | I/O chính | LTT resource | PlenX gần nhất | Verdict |
|---|---|---|---|---|
| `text.script` | text/json | Kịch bản + Gemini chat | Text | KEEP + EXTEND generic text |
| `image.generate` | text→image[] | Gemini Image | Image | KEEP + EXTEND composer/catalog |
| `image.thumbnail` | text→image[] | Prompt catalogs | Không node riêng | DIFFERENTIATOR |
| `video.generate` | refs/text→video | Seedance BytePlus | Video | KEEP + EXTEND multi-provider |
| `video.upscale` | video→video | Real-ESRGAN/GPU | Video Upscale | KEEP; LTT control/credit mạnh hơn |
| `video.subtitle` | video+transcript→video | FFmpeg/ASR ecosystem | Không node tương đương rõ | DIFFERENTIATOR |
| `video.short_clips` | video→clips | Whisper/YOLO/FFmpeg | Social Video gần một phần | DIFFERENTIATOR |

## Model/resource inventory

- Image active nội tại: 4 Gemini id mới + 2 alias cũ bất hoạt; PlenX quan sát 7 model image active và 4 locked trong composer.
- Video nội tại: Seedance 2.0/fast/mini qua BytePlus; provider PlenX khai Seedance 2.0/Pro và Kling 3.0 nhưng `video.generate` hiện chỉ cho BytePlus.
- Text nội tại: Gemini 2.5 Flash cho planner/script; PlenX composer hiển thị ba Gemini text model.
- Audio/voice: chưa có ToolSpec, job contract, pricing, storage journey hoặc voice catalog.
- Media transforms còn thiếu ToolSpec: batch images, extract frames, merge image, merge video, social URL input.
- Tài sản sẵn có để tái sử dụng: R2/media abstraction, upload contract các app video, FFmpeg, GPU worker, app registry, API key pool, model capability seam, job/credit/artifact/telemetry.

## Giới hạn schema hiện tại

- Canvas v1 chỉ lưu tool nodes/edges/viewport; chưa có page, frame, sticky, comment, share ACL hoặc version snapshot.
- Planner output vẫn tối đa 64 KiB; Canvas document tối đa 512 KiB; Plan tối đa
  100 bước, fan-out 4, retry 2. Đây là các trần độc lập để editor lớn không làm
  mất ranh giới an toàn của planner/provider.
- Node config đang nằm trong Inspector bên phải; chưa có composer trực tiếp trong card.
- Cách chạy chính là toàn workflow sau quote; chưa có quote/run node hoặc frame độc lập.

## Trạng thái kiểm chứng vòng này

- Đã chạy browser PlenX và local LTT; console cả hai: 0 error/warning tại thời điểm kiểm tra.
- Local Agent requests quan sát: palette/workflows/runs/workflow detail đều HTTP 200.
- Chưa chạy full pytest, frontend suite, secret scan, provider thật, GPU, load, CWV, accessibility scanner hoặc production canary. Đây là chủ ý theo phạm vi audit và checkpoint gom test của dự án.
