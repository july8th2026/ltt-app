# UI-RD Upscale — feature matrix

| ID | Feature | Hiện trạng | Quyết định | Điều kiện BUILD/PASS |
|---|---|---|---|---|
| UP-01 | Studio shell responsive | form/card | RESTYLE | desktop/mobile không overflow, keyboard/focus đúng |
| UP-02 | Fast/Quality | engine thật | KEEP | capability/data-driven, warning VRAM thật |
| UP-03 | AI Detail | chưa có engine | DEFER | benchmark quality/latency/VRAM/license trước bật |
| UP-04 | 1080/1440/2160 + codec | có | KEEP | server normalize, cost thật |
| UP-05 | Preserve FPS/audio | mặc định có | EXTEND | option map đúng FFmpeg; test probe output |
| UP-06 | Upload/R2 | có một file | EXTEND | direct PUT, retry/failure, cap hiển thị theo backend |
| UP-07 | Compare thật | WIP | BUILD | source/output owner-only; range/R2; sync/fallback |
| UP-08 | Queue/status/progress | có 12 job | EXTEND | owner scope; queued/running/done/error/cancelled |
| UP-09 | Batch max 3 | chưa có | BUILD | preflight + quote tổng + transaction job/credit |
| UP-10 | Cancel/refund | WIP core | BUILD | cooperative subprocess kill; race/idempotency/refund test |
| UP-11 | Pause/resume | chưa checkpoint | DEFER | cần checkpoint frame/chunk bền và settlement contract |
| UP-12 | Watch Folder | chưa có | BUILD | agent token scope, stable file, dedupe, retry/quarantine |
| UP-13 | Admin telemetry | chưa có | BUILD | admin-only; GPU/storage/queue từ số đo thật |
| UP-14 | ETA/FPS | chưa bền | BUILD | tính từ completed frames/elapsed; không fake khi thiếu mẫu |
| UP-15 | Delete/bulk delete | chưa lifecycle | DEFER | soft delete, retention, audit, undo, storage GC |
| UP-16 | Seedance→Upscale | service có; UI/API WIP | BUILD | quote/confirm/ownership/credit/dedupe E2E |
| UP-17 | Preview 8s | có | KEEP/RESTYLE | chi phí và artifact phân biệt rõ |

