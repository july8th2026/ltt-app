# Dependency graph và thứ tự BUILD tuần tự

Không sửa nhiều app song song. Chỉ một hạng mục có trạng thái `in_progress`;
app sau bắt đầu khi PASS gate app trước hoặc có biên bản DEFER rõ.

## Luồng phụ thuộc

`Security/money containment` → `shared contracts` → `runtime primitives` →
`Agent` → `customer apps` → `portfolio release`.

## Wave 0 — Stop-the-line, theo đúng thứ tự

1. **Socialbot security maintenance:** operator-only cho toàn bộ route/token/
   worker/monitor; test anonymous/customer/operator.
2. **Agent P0:** exactly-one child/attempt, một advance owner, PostgreSQL +
   SQLite race test, ledger 3+5=8; cascade cancel.
3. **Media direct URL:** đóng SSRF/DNS rebinding; có thể tạm ẩn tool import.
4. **Chat containment:** khóa arbitrary sidecar path; quyết định provider
   commercial/data contract; bounded quote và durable turn reconciliation.

PASS Wave 0: 3 P0 = 0 open; G2/G3 blocker trên bốn phạm vi có regression và
rollback. Không thêm tính năng UI ở wave này.

## Wave 1 — Shared foundation, một contract mỗi lần

1. Canonical upload/admission + staging/promote.
2. Artifact registry/retention/export/delete/GC.
3. Canonical quote/hold/settle/refund/receipt/reconciler.
4. Job/run event history, correlation, cancel/deadline.
5. Project draft/outbox/conflict/restore contract.
6. Shared i18n/a11y/responsive release harness.

Mỗi contract phải vào `platform_core` khi thật sự dùng chung; app chỉ gọi API,
không copy logic. Không sửa `platform_core` để phục vụ riêng một slug.

## Wave 2 — Runtime cho Agent

1. **Media Tools** — explicit operation, typed artifact, lifecycle.
2. **Kịch bản/Text** — literal input 0-credit, strict text generation/output.
3. **Agent AI** — node semantics/ports, standalone run, workflow library,
   customer IA, history/recovery; đối soát FLORA/PlenX sau từng slice.

## Wave 3 — App customer, hoàn thành từng app rồi mới sang app kế

1. **Chat AI Studio**
2. **Tạo ảnh AI + Thumbnail**
3. **Seedance Video**
4. **Upscale Video**
5. **Auto Sub**
6. **Tạo Clip ngắn**
7. **Prompt AI OMMI**

Thứ tự ưu tiên money/data dependency trước; Prompt cuối vì phụ thuộc artifact,
project và handoff từ ảnh/video.

## Wave 4 — Internal/portfolio

1. Demo synthetic full-chain + SLO evidence.
2. Socialbot operator canary maintenance (không feature parity).
3. Cross-app authenticated A–Z, full gate, backup/restore/rollback, canary rồi
   mới cân nhắc deploy.

