# 01 — Current Truth: Tạo Video Seedance

## Sơ đồ đầu-cuối

`manifest/model registry → /taovideo + SSR/HTMX/JS → login/CSRF → upload hoặc
chọn reference → lưu blob → submit_with_credit/hold → worker ModelArk → poll →
download R2/local → settle token thật hoặc refund → gallery/download/upscale`

## Inventory

| Thành phần | Hiện trạng | Evidence | Confidence | Rủi ro chính |
|---|---|---|---:|---|
| Manifest | Released; 3 model; job `taovideo.generate`; ToolSpec cho Agent | EV-SRC-001 | E4 | Cost hold dùng ước lượng ×1,25 |
| UI | SSR + HTMX + JS; composer trái, gallery phải, mobile drawer | EV-SRC-002, EV-BR-001/002 | E4 | EN không bền; drawer ẩn vẫn focus được |
| Input/reference | Ảnh/video/audio, role/handle, tối đa 4, chọn lại asset cũ | EV-SRC-003, EV-BR-003 | E4 | Tin MIME, đọc toàn bộ RAM, không xóa từng ref, blob preview lỗi |
| Job/worker | Async provider, persist task id, key pool, retry moderation/privacy | EV-SRC-004 | E4 | Không cancel/retry/live refresh tại app; giả định billing retry chưa chứng minh |
| Credit | Quote, hold, settle token thật/refund nền tảng | EV-SRC-005, EV-TEST-001 | E4 | Actual có thể vượt hold và làm số dư âm |
| Storage | Owner namespace, Local/R2, signed URL | EV-SRC-003/004 | E4 | Ref được ghi trước hold; thiếu retention/cleanup orphan |
| History/assets | 60 job gần nhất; asset suy từ params; gallery trạng thái | EV-SRC-002/003 | E4 | Không pagination/delete; tài sản cũ biến mất khỏi picker |
| Bridge Upscale | Quote/confirm owner-scoped + CSRF | EV-SRC-006, EV-TEST-001 | E4 | Phụ thuộc trực tiếp app-to-app đang được allowlist như nợ kiến trúc |
| Test/ops | 77 targeted PASS; browser desktop/mobile/VI/EN | EV-TEST-001, EV-BR-001..006 | E4 | Test không phủ negative balance/orphan/i18n/focus |

## Nội tại nên tái sử dụng

| Năng lực | Vị trí | Giá trị | Giới hạn |
|---|---|---|---|
| Job/credit/event/retry/refund | `platform_core` | Hợp đồng chung, idempotent theo job | Settle cho phép trừ quá hold |
| Model capability registry | `models.py` | UI thay theo model | Endpoint ID hardcode trong source |
| Persist provider task id | `jobs.py` | Worker retry không submit provider lần hai | Customer chưa thấy recovery state rõ |
| Owner-scoped saved refs | `routes.py` | Không nhận storage key tùy ý từ browser | Chỉ quét 60 job, không lifecycle riêng |
| Prompt assist/translate | `routes.py`, `translate.py` | Hỗ trợ người không chuyên | Nhiều literal VI, assist chỉ nối chuỗi deterministic |
| Upscale handoff | `upscalevideo.service` | Lợi thế hệ sinh thái | Import chéo app, cần contract dùng chung về sau |

## Unknown/baseline defect

| ID | Unknown/defect | Cách xác minh | Chặn gì |
|---|---|---|---|
| U-01 | Chất lượng prompt adherence, identity, motion, audio so với leader | Blind panel cùng prompt/ref/seed class | COMMERCIAL/G1 |
| U-02 | Phân phối token thực theo model/resolution/input | Thu ≥100 usage sample, P50/P95/max | G3 |
| U-03 | Provider có tính token cho output moderation retry hay không | Hóa đơn/API usage theo từng task attempt | G3/G8 |
| U-04 | R2 có lifecycle rule ngoài repo | Operator đọc policy, không chép secret | G5/G8 |
| U-05 | Production success/queue/render P95/cost | ≥20 terminal/model | G7/G8 |
| U-06 | Model endpoint hiện tại có đủ edit/extend/video-to-video capability | Capability probe staging + official API | Roadmap parity |

