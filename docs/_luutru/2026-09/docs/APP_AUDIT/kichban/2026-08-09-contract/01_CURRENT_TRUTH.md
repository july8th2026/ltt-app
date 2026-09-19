# 01 — Current truth

- Manifest `surface=runtime`, `lifecycle=retired`, `public=False`.
- `/kichban` trả 308 sang `/agent/canvas` (browser E3).
- `text.script` bị ẩn khỏi customer palette; `text.generate` vẫn customer-visible.
- Một job type `kichban.generate` dispatch theo `prompt` hay `topic`; giá 3 text,
  4 image, 6 video.
- Generic text hỗ trợ source text, nhiều ảnh owned, một video owned, model
  Gemini, plain/markdown/json; video upload tạm được xóa `finally`.
- Ownership key được kiểm bằng prefix user và storage existence.
- Legacy project revision có optimistic conflict/owner tests nhưng không còn UI
  trực tiếp.
- 186 targeted tests PASS (gồm registry, credit, runtime media, Kịch bản UI/
  features và Agent multimodal text). Provider/output quality E4 UNKNOWN.

