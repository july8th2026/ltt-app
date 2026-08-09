# 01 — Current truth

- Manifest: `surface=runtime`, `lifecycle=internal`, 9 ToolSpec customer-visible,
  một job type `mediatools.process`, cost dispatch theo field.
- Asset passthrough kiểm prefix ownership và existence; merge/extract dùng
  Pillow/FFmpeg; TTS dùng Gemini; output key scoped owner/job.
- Social import bắt `confirm_rights`, allowlist platform hoặc HTTPS direct,
  giới hạn 250/90 MB, duration 15 phút, content type và redirect count.
- `_safe_remote_url` kiểm DNS trước request nhưng HTTP client tự resolve lại;
  không pin IP đã kiểm → còn cửa sổ DNS rebinding/TOCTOU cho direct URL.
- Output được lưu storage nhưng không có artifact registry/retention/delete UX.
- Handler chọn operation bằng field presence; params có nhiều field có thể đi
  nhầm branch nếu vượt qua validator.
- Browser `/mediatools` → `/agent/canvas`, console 0 và requests 200.
- 186 targeted tests PASS; external download/provider/GPU-free large media E4
  là UNKNOWN.

