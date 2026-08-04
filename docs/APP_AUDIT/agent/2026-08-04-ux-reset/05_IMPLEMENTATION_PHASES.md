# Roadmap triển khai tuần tự — không chồng chéo

## P0 — Khóa contract và rollback

- Chốt Presentation Adapter, modality/intent matrix và migration của document
  cũ; không đổi ToolSpec/executor/credit.
- Đổi quyết định theme mặc định theo đúng giao thức nếu chọn nền gần đen.
- Ghi rollback: feature flag trả về renderer H20; không đổi schema không lùi được.

**Pass:** contract test mapping đầy đủ mọi ToolSpec public; document H20 mở được;
không có tên field/tool nội bộ trong UX fixture user.

## P1 — Canonical 4-block model

- Xây `BlockPresentation` cho Text/Image/Video/Audio.
- Asset trở thành state của media block; import/generate là action.
- Transform giữ secondary và chỉ xuất hiện khi executor/quote/output gate đủ.

**Pass:** fresh user chỉ thấy 4 block; Text/Image/Video/Audio có empty, ready,
running, success, failed; ownership/provenance test không đổi.

## P2 — Node shell và composer tối giản

- Cap kích thước/zoom; visual-first preview; contextual toolbar on hover/select.
- Một composer, safe-area Canvas, 4–6 chip; advanced drawer tách riêng.
- Chuẩn hóa CTA/price/state.

**Pass:** 1366/1720/1920 không overlap; selected node luôn nhìn thấy; first
action không quá 2 click; keyboard/focus/contrast gate.

## P3 — Connection grammar

- Một `+` output; drop-to-node, drop-to-blank intent menu; unique destination.
- Edge arrow/type color/running animation; midpoint insert; reconnect/delete.
- Prevent cycle và lỗi tiếng Việt; server validation vẫn là quyết định cuối.

**Pass:** matrix Text↔Text/Image/Video, Image→Image/Video/Text,
Video→Text/transform, Audio→supported intent; 0 duplicate destination label.

## P4 — Execution UX

- Run node, Run from here, Run flow với cùng preflight/quote/approval.
- Scope preview, prerequisite/downstream list, cancel/retry và run drawer.
- Debounce/cache quote theo normalized params; không quote lại do selection.

**Pass:** actual credit 0 trước confirm; estimate khớp server; cancel/refund/retry
test; UI state đồng bộ API/job ở reload/reconnect.

## P5 — Onboarding, templates và advanced

- First-run guided chain `Text → Image` và `Image → Text`.
- Template theo kết quả, không theo tên tool; Assets/History ở vùng riêng.
- Assistant chỉ vào sau core flow; Assist mặc định, Plan không spend, Auto opt-in.

**Pass:** người mới hoàn thành hai chain không mở Inspector; Assistant luôn hiện
phạm vi và credit trước action có spend.

## P6 — Browser/regression/a11y

- Playwright production-like desktop 1366/1720/1920 và mobile view/read-only.
- Console, failed network, keyboard, screen reader labels, visual regression.
- Performance budget cho 1/10/50 node; save conflict/offline/recovery.

**Pass:** mọi journey P0/P1 xanh; console 0; request 4xx/5xx bất ngờ 0; không
overflow; không regression tenant/credit/undo.

## P7 — Controlled beta và re-audit

- 5 người chưa biết kiến trúc; nhiệm vụ tạo Text→Image, Image→Text, Image→Video,
  chạy một node và chạy từ đây.
- Đo task success, time, misclick, help request, abandon và perceived clarity.

**Pass:** ≥80% task success; median first valid chain ≤120 giây; ≤1 help request
mỗi task; UX/UI ≥75/100, Q≥80, không P0/P1 mở. Chỉ sau đó mới deploy rộng.

## Thứ tự bắt buộc

`P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7`.

Không làm Assistant/templates trước khi bốn block và dây đạt pass. Không mở thêm
model/tool để che UX yếu. Mỗi phase phải browser-verify rồi mới sang phase sau.
