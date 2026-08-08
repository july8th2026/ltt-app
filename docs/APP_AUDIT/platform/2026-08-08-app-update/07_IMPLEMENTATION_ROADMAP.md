# 07 - Implementation roadmap H26

Thực hiện **tuần tự**, mỗi phase phải PASS mới sang phase sau. Không deploy trong
audit dossier này.

## Phase 0 - Scope, surface và rollback (P0)

1. Khóa decision gate ở `06_OPTIONS_AND_DECISIONS.md`.
2. Mở rộng manifest bằng audience/surface và lifecycle có enum/test; platform
   không hardcode slug.
3. Kịch bản YouTube: gỡ card/header/search/standalone customer; gỡ
   `text.script` khỏi customer palette; giữ `text.generate` nội bộ.
4. Demo: admin/ops-only, customer direct URL 404.
5. Media Tools: runtime-only, không card/header/search; Agent capability không
   đổi.
6. Regression: anonymous/customer/admin catalog, direct URL, Agent tool registry,
   old workflow load/run.

**PASS:** ba tool không còn ở customer UI; Agent Text/Image/Video/Audio vẫn nạp
đủ; console/network sạch.  
**Rollback:** revert manifest/route audience commit; không migration dữ liệu.

## Phase 1 - Job history, event log và support (P1 core)

1. Migration `JobEvent` append-only: sequence, job/app/user, level, event code,
   public message, redacted metadata, correlation ID, timestamp; index theo
   job/sequence và user/app/time.
2. API/service dùng chung để append event; worker tự ghi submit/claim/start/
   progress/retry/reclaim/cancel/done/error/settle/refund.
3. Redaction allowlist, size cap, retention và purge job; tuyệt đối không log
   secret/raw credential/cross-tenant payload.
4. Global Jobs: filter app/status/date, cursor pagination, lifecycle timeline,
   lineage parent-child, artifact/download, retry/cancel.
5. Component/contract History dùng trong từng async app; app sync như Chat dùng
   conversation history và operation trace tương đương.
6. Metrics/alert: success rate, queue wait, runtime P50/P95, retry, refund,
   stale job, event write failure.

**PASS:** test ownership chéo user, event order/idempotency, retry/refund, purge,
redaction; browser customer/admin; restore drill.  
**Rollback:** UI đọc lại `Job`; migration downgrade chỉ khi chưa có dữ liệu cần giữ.

## Phase 2 - Marketplace và design system chung (P1/P2)

1. Toàn card clickable/accessibility, control con không bubble sai; bỏ icon giữa
   cover và metadata kỹ thuật.
2. Lifecycle + capability taxonomy từ manifest; status filter và category filter
   độc lập; sort ưu tiên theo lifecycle đã chốt.
3. Trạng thái theo yêu cầu ban đầu:
   - phát hành: Upscale, Prompt AI, Tạo Video Seedance;
   - phát triển: Clip ngắn, Tạo ảnh AI, AutoSub, Chat, Agent;
   - bảo trì: Socialbot.
4. Hợp nhất Thumbnail vào Tạo ảnh AI bằng hai mode, giữ job type/history cũ;
   redirect tương thích, chưa xóa app owner.
5. Browser matrix 390/768/1366/1920, keyboard/focus/screen reader cơ bản,
   console và failed request.

**PASS:** card behavior đúng 100%, không icon lặp, không category cứng, no
horizontal overflow, không mất history/link cũ.  
**Rollback:** feature flag shell/taxonomy cũ trong một release.

## Phase 3 - Từng app, không song song

### 3.1 Upscale Video

- Đổi tên; khóa mutual exclusion FPS trên UI/server/quote/result.
- Rebuild compare: draggable divider + một slider semantics, master controls,
  seek/play/rate/end sync và drift correction.
- Queue filter status, newest default, grid/list, thumbnail thật, option chip
  màu có text/icon (không chỉ màu), download attachment.
- Ẩn experimental/dev UI; Watch Agent chuyển Integration/Admin.
- Benchmark/autotune trên **từng GPU 16 GB**; đo fast/quality, 1080/1440/4K,
  video ngắn/dài; chạy hai worker chỉ sau soak không OOM/thermal throttle.

### 3.2 AutoSubVideo

- Đối chiếu bundle/hash/build-meta và production flag; tái hiện vì sao legacy.
- Canary React Studio, test Upload -> Transcribe -> Style -> Render -> Download,
  giữ legacy rollback một release.
- Chỉ sau parity mới gắn tag/đổi mặc định public.

### 3.3 Tạo Video Seedance

- Đổi tên; map ảnh target vào capability thật: model, prompt, references,
  duration/aspect/resolution/audio/count, filters/history/remix/upscale.
- Không thêm button/library/settings nếu backend chưa có contract.
- Mọi option phải test quote -> params -> provider -> result metadata.

### 3.4 Prompt AI

- Đổi tên; khảo sát read-only Prompt Seedance trong `D:\BOT GEMINI`, lập bảng
  `reuse/copy/adapt/reject`, copy tài nguyên cần thiết sang app, không import chéo.
- Dùng ảnh target cho IA/dashboard nhưng không tạo số team/cost giả.
- Ưu tiên project, assets, script/scenes, storyboard, export, version và activity
  thật; team workspace chỉ làm nếu Decision 9 đổi thành BUILD.

### 3.5 Tạo ảnh AI + Thumbnail

- Một shell/một entry point; mode quyết định form và preset, dùng hai executor
  cũ phía sau; history filter theo mode và tìm được mọi output cũ.

### 3.6 Các app yêu cầu đang UNKNOWN

Theo thứ tự: Tạo Clip ngắn -> Chat AI -> LTT Agent AI -> Socialbot maintenance.
Với mỗi app: bổ sung MoTa/evidence hoặc browser audit, benchmark 5-7 đối thủ,
control registry, Q/M/E, decision gate riêng rồi mới BUILD. Không suy đoán từ
folder trống.

## Phase 4 - Performance, privacy và operations

- Retention/purge/archive, support export đã lọc, dashboards/alerts/runbook.
- Load/soak queue, upload lớn, worker restart, orphan reclaim, storage/provider
  outage, two-GPU concurrency và cost/successful output.
- SLO theo app; không lấy throughput tổng che P95 xấu.

## Phase 5 - Release

1. `python tools\gate.py` xanh, secret scan 0.
2. Browser A-Z từng app với test account/canary, console 0, failed request 0.
3. Backup/migration/rollback rehearsal, release notes và known issues.
4. Deploy canary -> quan sát -> production; sau deploy kiểm manifest/build-meta,
   health, job/event/credit và UI thật.
5. Re-audit Q/M/E và G0-G8; chỉ đóng khi G0-G8 PASS hoặc exception được chủ sản
   phẩm chấp nhận bằng văn bản.

