# 02 — Journey & Control Registry

## Journey parity

| Journey | PlenX | LTT hiện tại | Quyết định |
|---|---|---|---|
| Tạo workflow rỗng | LIVE | LIVE tự tạo workflow đầu | KEEP |
| Đổi tên + autosave | LIVE, có flash state khi hydrate | backend có revision; UI chưa nổi bật tên | FIX/EXTEND |
| Thêm/cấu hình node | 11 active + 4 disabled; composer trong node | 7 tool; Inspector riêng | EXTEND |
| Nối node | kéo full cạnh; nhận cả sai kiểu | typed handle và chặn sai | KEEP LTT, không copy bug |
| Chạy | node hoặc frame | toàn workflow | BUILD scoped run |
| Giá/credit | giá ở composer; UI có trường hợp CTA vẫn sáng khi thiếu | quote + approval + hold/settle | KEEP LTT, thêm live preview |
| Artifact/log | generation log success/fail | run inspector/checkpoint/artifact | RESTYLE + hợp nhất |
| Version/restore | autosnapshot + restore | restore từ run, chưa editor versions | BUILD |
| Multi-page | LIVE | MISSING | BUILD |
| Frame/template | run/save/download resources | MISSING | BUILD |
| Comments/sticky/layers/grid | LIVE | MISSING/partial grid nền | BUILD chọn lọc |
| Share/clone | link view+clone | clone owner-only, không share | BUILD ACL + revoke |
| Assistant | hội thoại + quick actions/patterns | one-shot AI dựng Canvas | BUILD |
| Import/export | page JSON | whole workflow JSON | KEEP + versioned upgrade |

## PlenX control inventory quan sát trực tiếp

| Khu vực | Control | State/behavior | Verdict cho LTT |
|---|---|---|---|
| Topbar | Back, title, save state | inline title; autosave | BUILD |
| Topbar | Generation Logs | tabs all/success/fail | MERGE vào Run Center |
| Topbar | Version history | nhiều autosnapshot, restore | BUILD có debounce/coalescing |
| Topbar | Brightness | 100% control | DEFER nếu chỉ decorative |
| Topbar | Export/Import page JSON | page-portable | BUILD trong Canvas v2 |
| Topbar | Share | public link, view/clone metrics | BUILD ACL/revoke/audit log |
| Left rail | Cursor/pan, Add node | editor basics | KEEP/RESTYLE |
| Left rail | Frame | color/run/save/download | BUILD |
| Left rail | Layers/Grid | organization/navigation | BUILD |
| Left rail | Comment/Sticky | collaboration/annotation | BUILD phase collaboration |
| Left rail | Undo/Redo | editor history | KEEP |
| Bottom | Pages | create/rename/delete, node count | BUILD |
| Bottom | Hide connections/Auto arrange | visual control/layout | KEEP + improve layout |
| Bottom | Keyboard help | shortcuts catalog | BUILD |
| Bottom | Logs/Assistant | drawers | BUILD |
| Assistant | quick-add 5 nodes | Image/Video/Upscale/Audio/Text | BUILD from ToolSpec groups |
| Assistant | analyze/improve/build prompts | workflow-aware chat | BUILD grounded assistant |

## Node catalog PlenX

| Node | State | LTT mapping/action |
|---|---|---|
| Image | active | `image.generate`, extend model composer |
| Batch Images | active | BUILD `image.batch_generate`/batch input contract |
| Video | active | `video.generate`, extend providers/modes |
| Social Video | active | BUILD safe URL/import node; SSRF/downloader policy |
| Text | active | EXTEND generic `text.generate`; giữ `text.script` chuyên biệt |
| Audio | active | BUILD `audio.generate`/TTS + voice catalog |
| Upscale | active | LTT chưa có image upscale; BUILD sau engine spike |
| Video Upscale | active | `video.upscale` |
| Extract Frames | active | BUILD FFmpeg ToolSpec |
| Merge Video | active | BUILD FFmpeg ToolSpec |
| Merge Image | active | BUILD compositor ToolSpec |
| Upload/Enhance/Remove BG/Animation | disabled | DEFER, không tính active parity |

## Model composer quan sát

- Image: model, ratio Auto/1:1/4:3/3:4/9:16/16:9, 1K/2K/4K, BUSINESS/VIP server, live cost.
- Video: 14 model quan sát, I2V/T2V/R2V, 16:9/9:16, 720p/1080p/4K, 4/6/8s, server và live cost.
- Text: ba Gemini model, server, cost.
- Audio: sáu model, search/filter voice theo giới tính/ngôn ngữ, preview/use, provider/server và cost.
- LTT cần dựng composer từ capability schema động; không hardcode danh sách trong JSX.

## PlenX defects không được sao chép

1. UI nhận edge sai kiểu `Text → Video Upscale`.
2. Merge Video dùng copy “Generate images…”.
3. Auto-layout 11 node rời thành một cột cao hơn 6.000 px.
4. Reload có flash `Untitled/0 nodes` trước hydrate.
5. Assistant trên Page 2 rỗng vẫn đếm 11 nodes/10 connections của Page 1.
6. Một số model locked/disabled nhưng default/cost/CTA gây khó hiểu; thiếu-credit preflight chưa rõ.
7. Mở Share tạo/đụng share resource; LTT phải tách “xem modal” khỏi “bật chia sẻ”.

## State bắt buộc khi build

Mỗi control/node phải có: empty, configuring, invalid, quote-loading, insufficient-credit, awaiting-approval, queued, running, partial, done, failed, cancelled, retrying, offline, save-conflict, permission-denied và artifact-expired. Không render CTA thật khi backend contract chưa tồn tại.
