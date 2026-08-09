# A6 — Findings

## P0 (1)

| ID | Finding → root cause/impact | Acceptance |
|---|---|---|
| AGT-P0-01 | Browser run một Text→Image sinh hai child `kichban.generate`; step 3 credit bị tính 6, run 8-credit dừng trước image và refund 2. Frontend `/tick` cùng worker `agent.advance` tạo hai đường advance; SQLite không có row lock. Production PostgreSQL impact UNKNOWN nhưng money/core đã fail ở môi trường audit. | chỉ một orchestration owner; idempotent step-attempt DB constraint; Postgres+SQLite concurrency test; ledger/job/run cùng chứng minh 1 child, 3+5=8 |

## P1 (7)

| ID | Finding → root cause/impact | Acceptance |
|---|---|---|
| AGT-P1-01 | Text node không có manual/literal mode. Starter “viết một lần” biến nội dung nhập tay thành `text.generate`, tốn 3 credit rồi mới tạo ảnh. | tách Text Input 0 credit và Text Generate; migration/starter/golden test |
| AGT-P1-02 | Cancel AgentRun chỉ hủy job `agent.advance`, không hủy child image/video/audio đang queued/running; có thể tiếp tục đốt provider và tạo orphan sau refund. | cooperative cancel toàn cây; settle sau terminal child; race/crash test |
| AGT-P1-03 | Không có Workflow Library customer UI. Canvas luôn lấy `listing.items[0]`; clone/import/archive có API nhưng người dùng không mở/chuyển/quản lý workflow cũ. | library search/filter/pagination/new/open/archive/delete/restore; ownership test |
| AGT-P1-04 | `/agent` là legacy planner song song Canvas, lộ `text.script`, fan-out, retry, raw status/decision log và tạo mental model thứ hai. | `/agent` thành project/library/onboarding; kỹ thuật chỉ operator/advanced details |
| AGT-P1-05 | Asset upload và artifact output không có DB reference/TTL/GC/delete/export lifecycle; workflow/archive/delete không khép kín dữ liệu. | asset registry owner/reference, retention, self-service delete/export, GC audit |
| AGT-P1-06 | Error inspector cho raw node ID và “không đủ ngân sách attempt” nhưng không nêu duplicate/root step/cách sửa; replay dễ lặp lỗi/chi phí. | customer label, cause/remediation, safe retry failed step, receipt từng step |
| AGT-P1-07 | Planner/assistant gửi goal/current plan/private pattern names sang provider; disclosure/retention contract chưa rõ và limiter chỉ general 120 hoặc expensive 30 POST/phút/process. | consent/privacy contract; persistent per-user quota/circuit breaker; abuse/expense tests |

## P2 (18)

1. Mobile là view-only nhưng nhãn giải thích bị CSS ẩn; Run/tên/tools chỉ disabled.
2. Mobile advanced catalog dài hơn viewport, không search/toggle và không customer runner.
3. `/en/agent` pha English/VI; Canvas `/en/` phần lớn VI.
4. API GET unprefixed bị locale 302 rồi gọi lại, tăng request/latency.
5. Workflow list `.all()` không pagination/cursor/status filter.
6. Archived workflow vẫn nằm trong list và có thể trở thành item tự mở.
7. Run history chỉ 20 items, không pagination/filter/status/date.
8. Context pane advanced phơi 15 tool; category “Khác” và mô tả kỹ thuật quá dày.
9. Node hiển thị mọi input handle kỹ thuật, làm block lớn và khó hiểu.
10. “Chạy block này” và “chạy từ đây” không preview rõ graph scope trước quote.
11. Model dropdown phụ thuộc catalog chung; fixture đưa model text vào Image selector.
12. Schedule input không nêu timezone, notification hay trạng thái queued-by-time.
13. `/tick` chạy executor trong web request, phá ranh giới web/worker và tạo polling writes.
14. Bundle ZIP dựng toàn bộ tối đa 200 MB trong `BytesIO` web process.
15. Artifact endpoint thiếu filename/content-disposition và manifest customer metadata.
16. Assistant analyze/improve không có conversation/undo diff theo field; proposal thay toàn Canvas.
17. Share UI tạo link nhưng không liệt kê/revoke/copy-status hay preview quyền rõ.
18. No unsaved-leave confirmation; autosave conflict recovery chỉ reload, có nguy cơ mất draft local.

## P3 (6)

1. React Flow attribution chiếm góc điều khiển sản phẩm.
2. Dùng ký hiệu `↗`, `AI`, `□`, `◌` thiếu label trực quan cho người mới.
3. “AUTO ROUTING · 11 model · platform_auto” là copy cho operator/dev.
4. Page/frame/note/comment xuất hiện sớm hơn workflow library và asset/result panel.
5. Snapshot chỉ hiển thị `vN · save`, thiếu thời gian/mô tả/diff.
6. Không có sample output/education theo ngữ cảnh ở node trống sau onboarding.

Tổng: **1 P0 · 7 P1 · 18 P2 · 6 P3**. AGT-P0-01 là lỗi đã quan sát ở
fixture; production impact chưa được khẳng định và phải được kiểm chứng bằng
PostgreSQL concurrency canary trước mọi quyết định phát hành.
