# 05 — Findings

Tổng: **2 P0 · 5 P1 · 8 P2 · 4 P3**.

| ID | Sev | Hiện tượng/root cause | Ảnh hưởng | Acceptance mở lại |
|---|---|---|---|---|
| SOC-001 | P0 | `public=False` không chặn route; route account chỉ `require_login`; token store global | customer xem/ghi/xóa credential kênh LTT | toàn bộ route Socialbot operator-only, test âm mọi path |
| SOC-002 | P0 | worker/controller/monitor global cũng chỉ require login | customer start/stop/reset vận hành của người khác | operator authorization + audit actor/action |
| SOC-003 | P1 | OAuth callback gắn token vào global store, không tenant owner | account attribution sai | mô hình owner rõ hoặc operator-only tuyệt đối |
| SOC-004 | P1 | runner riêng ngoài Job/Credit/Event chung | thiếu history/retry/support chuẩn | adapter history/event hoặc runbook legacy được khóa |
| SOC-005 | P1 | disconnect/reset không undo/confirm đầy đủ | mất token/metric | confirm + immutable audit + restore path |
| SOC-006 | P1 | monitor/log có thể lộ dữ liệu vận hành cho customer | privacy/support risk | operator-only + redaction test |
| SOC-007 | P1 | fallback lưu token plaintext nếu thiếu dependency | secret at rest có thể yếu | startup hard-fail production nếu crypto vắng |
| SOC-008 | P2 | route đặc cách rải ở nhiều module | khó giới hạn/rollback | route group có policy chung |
| SOC-009 | P2 | không draft/approval/RBAC | dưới baseline nhưng Q10 đóng băng | ghi DELIBERATE_OMISSION |
| SOC-010 | P2 | UI legacy/8 nav dày, ngôn ngữ operator | không phù hợp customer | chỉ hiển thị operator shell |
| SOC-011 | P2 | no canonical Job history | debug phân mảnh | correlation ID/event export |
| SOC-012 | P2 | provider/queue load telemetry UNKNOWN | không chứng minh reliability | SLO sample/canary operator |
| SOC-013 | P2 | token rotation/restore chưa diễn tập trong vòng này | DR chưa chứng minh | restore rehearsal không lộ secret |
| SOC-014 | P2 | access regression test đang thiếu đúng ca lỗi | lỗi tái phát | test customer `/facebook` `/sheet/*` = 404/403 |
| SOC-015 | P2 | lifecycle maintenance không mang nghĩa authorization | dễ hiểu sai manifest | contract/test tách visibility và route access |
| SOC-016–019 | P3 | copy, responsive, focus, visual consistency chưa chuẩn | polish/operator efficiency | audit sau khi G2 đóng |

Root cause chung: **nhầm visibility (`public`) với authorization** trên một app
legacy có state dùng chung toàn tiến trình.

