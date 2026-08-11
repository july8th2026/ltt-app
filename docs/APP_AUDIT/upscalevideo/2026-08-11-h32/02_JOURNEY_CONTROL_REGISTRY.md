# H32.6 — Journey và Control Registry

| Journey/control | Hành vi/contract | Verdict | Evidence |
|---|---|---|---|
| Upload/drop file | MP4/MOV/MKV/AVI, probe metadata, batch tối đa 3 | LIVE | Browser actual source |
| Fast/Quality | Đổi engine và quote | LIVE | 12 core GPU cases |
| 1080/1440/2160 | Output height đúng, width giữ aspect | LIVE | 12 core GPU cases |
| H.264/HEVC | Codec output đúng | LIVE | 12 core GPU cases |
| Giữ FPS | 24 fps giữ nguyên | LIVE | Matrix |
| Chuẩn hóa FPS | 30 fps khi bỏ preserve | LIVE | normalize30 case |
| Giữ audio | AAC parity | LIVE | Matrix/full source |
| Bỏ audio | Không có audio stream | LIVE | normalize30-noaudio |
| Smooth motion | Tự loại preserve và nhân đôi source 24→48 | LIVE sau FIX | Regression + runtime |
| Stabilize | two-pass libvidstab path | LIVE | Matrix |
| Preview | Render sample, giảm quote | LIVE | Browser + runtime |
| Batch 2 file | Một submit, một hold 96, hai job | LIVE | Browser batch probe |
| Queue position | Hiện 1/2 rồi 2/2 | LIVE snapshot | Browser probe |
| History | Link owner-scoped global history | LIVE sau FIX | Browser |
| Job status | Friendly localized state, không lộ worker text | LIVE sau FIX | Browser EN |
| Activity log | Link `/jobs/<id>` | LIVE sau FIX | Browser |
| Compare slider | pointer/keyboard contract hiện hữu | LIVE | Regression kế thừa |
| Mobile settings | đóng bằng inert/aria-hidden, mở/đóng, trả focus | LIVE sau FIX | 390×844 |
| Cancel | queued/running form có CSRF | LIVE | E2 kế thừa |
| Retry tại card app | Không có | MISSING | Source/control inventory |
| Live progress không reload | Không có polling/SSE | MISSING | Source/control inventory |
| Upload abuse/lifecycle | Policy staging chưa khép kín | PARTIAL | Audit 2026-08-09 |
| Chất lượng cảm nhận | Chưa calibrate/blind review | UNKNOWN | Quality Lab |

## State coverage

Happy upload/quote/batch/queued, done/error fixture, desktop/mobile và negative
blob lifetime đã chạy. Insufficient credit, R2 partial upload, crash/resume,
retry và production large download chưa chạy trong H32.6.

