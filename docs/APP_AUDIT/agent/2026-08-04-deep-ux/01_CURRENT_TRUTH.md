# Current Truth

## Runtime giữ lại

- Palette sinh từ ToolSpec server; chỉ công cụ có executor thật mới xuất hiện.
- Typed graph, server validation, quote, immutable scoped run, approval và credit
  vẫn do backend quyết định.
- Preference theme/catalog lưu theo user; mặc định mới là dark/advanced.
- Node run và selection run được backend cắt scope kèm transitive prerequisite.

## Presentation H20

- Node renderer theo modality: text, image, video, audio, batch, input, transform.
- Empty/configured/output state; upload/generate/manual; preview artifact.
- Composer chỉ đưa trường phục vụ người dùng; schema kỹ thuật ở Inspector.
- Context menu pane/node; duplicate/delete/move page; run node/run-from-here.
- Kéo output ra khoảng trống mở compatible picker; `@node` tạo typed edge thật.
- Mỗi input chỉ có một source đang hiệu lực; chọn reference mới thay edge cũ.
- Node có measured size và handle registry rõ ràng để React Flow render edge ổn định.

## Bằng chứng

- Source: `CanvasShell.tsx`, `ToolNode.tsx`, `nodePresentation.ts`, `editorState.ts`.
- Frontend: 27 test pass; typecheck/build pass.
- API/Canvas: 22 test pass.
- Full platform: 2.063 pass, 8 skip, 23 subtest pass.
- Secret scan cuối: 1.493 file, 196.292 dòng, 0 finding.
