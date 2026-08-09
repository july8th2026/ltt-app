# A2–A3 — Journey và Control Registry

## State matrix

| State | Verdict | Evidence/gap |
|---|---|---|
| Empty/new | LIVE | model + CTA + suggestions rõ |
| Streaming success | LIVE có điều kiện | SSE 200, 3 credit, title/balance live |
| Attachment | PARTIAL | file parse thật; optimistic/reload khác nhau, retention mơ hồ |
| Image generation | MISLEADING | rate thấy ở header nhưng không khóa số ảnh/trần 83 trước send |
| Stop/partial/error | MISLEADING | backend settle; UI receipt/balance có thể báo 0/stale |
| Insufficient image credit | PARTIAL | text giữ, ảnh chặn; không cho chọn/confirm count |
| Branch | BROKEN | lịch sử clone để nhìn nhưng AI thread mới không có history |
| Sidecar restart/thread lost | BROKEN | không replay/rebuild context |
| Delete | BROKEN | DB mất nhưng Storage/remote thread còn |
| Concurrent/duplicate send | BROKEN | không idempotency/lock, có thể double charge/context race |
| Mobile | PARTIAL | không overflow; sidebar xếp trước transcript, dài khi nhiều chat |
| Offline/hung provider | BROKEN | timeout none, không server deadline/run recovery |

## Control Registry

| Control | API/credit | State | Finding |
|---|---|---|---|
| Mode + New | POST `/new`, 0 credit | PARTIAL | server không validate allowlist model; mode không đổi sau tạo |
| Search | GET `?q=`, max 100 conv | LIVE cơ bản | không pagination/filter/image prompt |
| Conversation item | GET `?c=` | LIVE | không rename/pin/archive/folder |
| Delete | POST `/delete/{id}` | BROKEN | orphan Storage/thread; no undo/export reminder |
| Suggestions | fill composer | LIVE | chỉ 3 static prompt |
| Attach | multipart `/send`, included in 3 | PARTIAL | full read/parser cost; stored text disclosure/visual mismatch |
| Composer/Enter | send SSE, hold 3 | PARTIAL | no max-cost confirm/idempotency/conversation lock |
| Stop | browser abort | MISLEADING | receipt and balance not returned after partial settle |
| Assistant output | text/image | PARTIAL | plain text, no Markdown/code/table/citation/copy |
| Turn detail | token/credit after done | PARTIAL | error/stop path inaccurate |
| Image event | hold +20 before save | PARTIAL | untrusted absolute path/no output validation; count controlled by model |
| MD/JSON export | owner check | PARTIAL | JSON leaks internal image key; no image/file bundle |
| Branch | DB clone | BROKEN | new AI thread has no cloned context |
| Admin device/API key | sidecar auth | PARTIAL | valid admin/CSRF; commercial auth/data terms unresolved |
| Ready badge | account exists | MISLEADING | not quota/rate-limit/latency/terms readiness |

## Browser evidence

- Desktop new/composer/success; mobile complete/file/reload; width 375=client 375, no overflow.
- Three fixture turns: 100→97→94→91; SSE all 200; console 0 error/warning; failed app requests 0.
- JSON attachment live view says generic fallback; reload renders extracted JSON in full.
- Uploaded PNG existed under owner/conversation Storage before delete and still existed after delete completed.
- Tested branch/export controls visually; branch context defect confirmed by source: clone DB only, `thread_start` receives settings, not history.
- `/en/chataistudio` dịch nội dung app nhưng top navigation vẫn hiện `Ảnh`, `Video`, `Đăng bài`, `AI Studio`, `Chat` bằng tiếng Việt.
