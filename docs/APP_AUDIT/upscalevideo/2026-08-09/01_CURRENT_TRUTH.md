# 01 — Current Truth: Upscale Video

## Sơ đồ đầu-cuối

`manifest → /upscalevideo + template/JS → session/CSRF/owner → upload local hoặc
presigned R2 → submit_upscale_batch → hold credit → worker GPU/FFmpeg → settle
hoặc refund → storage output → compare/download/history`

## Inventory

| Thành phần | Hiện trạng | Evidence ID | Confidence | Ghi chú/rủi ro |
|---|---|---|---:|---|
| Manifest/route | Released, route `/upscalevideo`, job `upscalevideo.render`, GPU VRAM 4 GB | EV-SRC-001 | E4 | Surface thật, tên public đúng |
| UI/frontend | SSR template + JS, desktop hai cột, mobile progressive disclosure, compare slider | EV-SRC-002, EV-BR-001/002 | E4 | Có trạng thái queue nhưng chỉ render 12 job |
| Auth/ownership | Login, CSRF ở submit/cancel; source/output owner-scoped | EV-SRC-003, EV-TEST-001 | E4 | Ticket upload không CSRF, chưa có upload quota/policy chặt |
| Job/worker | Queue dùng chung, cooperative cancel, retry nền tảng, GPU UUID lease | EV-SRC-004, EV-TEST-001, EV-GPU-001 | E4 | App không lộ retry tại chỗ; danh sách không live-poll |
| Provider/model | Real-ESRGAN NCNN ×4 Fast/Quality + FFmpeg stabilize/interpolate | EV-SRC-004, EV-GPU-001 | E4 | Spatial, chưa có temporal AI Detail/denoise/deblur |
| Credit | Quote server-side, batch hold nguyên tử, settle/refund dùng chung | EV-SRC-005, EV-TEST-001 | E4 | Artifact được ghi trước khi hold thành công |
| Storage/artifact | Local/R2, direct upload, owner-only video/download | EV-SRC-003, EV-TEST-001 | E4 | Orphan upload/retention và proxy download lớn chưa giải quyết |
| Test/ops/rollback | 50 targeted PASS; dual-GPU evidence; SLO/telemetry dùng chung | EV-TEST-001, EV-GPU-001 | E4 | Production SLO chưa đủ mẫu; output chưa blind-score |

## Nội tại tái sử dụng được

| Năng lực đã có | Vị trí | Có thể tái sử dụng | Giới hạn |
|---|---|---|---|
| Submit một/batch + credit | `apps/upscalevideo/service.py` | Seedance và app trực tiếp | Cần cleanup artifact quanh transaction |
| GPU lease, engine và FFmpeg | `jobs.py`, `engine.py`, `ff.py` | Fast/Quality, stabilize, motion | Chưa phải temporal restoration |
| JobEvent/history/retry/refund | `platform_core` + `/jobs` | Mọi app | Upscale UI chưa đưa retry/full history vào đúng ngữ cảnh |
| Owner-only media serving | `routes.py` | Preview/source/output | Download lớn đang proxy qua web process |
| Telemetry/SLO | `telemetry.py`, `platform_core/job_metrics.py` | Operator | Chưa có đủ production sample theo app |
| Watch Agent | `watch_agent.py`, `watch_auth.py` | Workflow folder admin | Không phải tính năng customer; giữ sau quyền admin |

## Unknown và baseline defect

| ID | Unknown/defect | Cách xác minh | Có chặn audit không |
|---|---|---|---|
| U-01 | Chất lượng cảm nhận Fast/Quality so với temporal leaders | Blind panel cùng source/output, SSIM/LPIPS + flicker | Chặn COMMERCIAL, không chặn inventory |
| U-02 | Production success/P95/cost theo app | Thu ≥20 terminal job từ metric operator | Chặn COMMERCIAL |
| U-03 | R2 có lifecycle rule ngoài repo hay không | Operator đọc bucket policy, không đưa secret vào hồ sơ | Có; hiện code không chứng minh cleanup |
| U-04 | Presigned PUT có giới hạn Content-Length ở lớp Cloudflare | Kiểm policy thực tế và thử payload vượt ngưỡng ở staging | Có; route hiện không biểu diễn giới hạn |
| U-05 | Người dùng hiểu Fast/Quality và chấp nhận chênh lệch 15× runtime | Moderated test 5 người, task-based | Không chặn audit; chặn tối ưu UX |

