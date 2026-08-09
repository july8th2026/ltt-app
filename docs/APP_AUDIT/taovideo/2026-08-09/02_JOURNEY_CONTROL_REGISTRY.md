# 02 — Journey & Control Registry: Tạo Video Seedance

## Journey/state matrix

| ID | State | Kỳ vọng customer | Kết quả thật | Evidence | Verdict |
|---|---|---|---|---|---|
| J-01 | Empty | Biết bắt đầu ở đâu, giá chưa bị giả | Form rõ, quote mặc định theo setting dù chưa có prompt | EV-BR-001 | PARTIAL |
| J-02 | Prompt hợp lệ | Giữ nguyên nội dung, hỗ trợ nhưng không viết đè bất ngờ | Prompt/assist/history hoạt động | EV-BR-003 | LIVE |
| J-03 | Chọn model | Chỉ thấy capability model hỗ trợ | Resolution/duration đổi động đúng registry | EV-BR-003 | LIVE |
| J-04 | Thêm ảnh/video/audio | Preview, vai trò, tên, xóa từng item | Preview/role có; không nút xóa từng item; đổi selection gây blob fail | EV-BR-004 | PARTIAL |
| J-05 | Quá 4 reference | Lỗi ngay cạnh input, giữ 4 item hợp lệ | Render 5 row rồi chỉ dùng browser validity message khi submit | EV-BR-004 | PARTIAL |
| J-06 | File giả/lớn | Chặn trước lưu/hold, không ngốn RAM | Tin MIME; đọc tối đa 4×60MB vào RAM rồi mới xử lý | EV-SRC-003 | BROKEN |
| J-07 | Quote có video ref | Quote/hold khớp request thật | `/estimate` luôn `has_video_input=False` | EV-SRC-003/005 | MISLEADING |
| J-08 | Submit một/hai biến thể | Một action, chống double submit, all-or-none | DB batch nguyên tử; button không disable; ref mới làm dedupe key đổi | EV-SRC-002/003 | BROKEN |
| J-09 | Thiếu credit | Giữ form/locale/ref, CTA nạp, không artifact | POST 400 rơi EN→VI, prompt/model/count mất; ref mới đã lưu | EV-BR-005, EV-SRC-003 | BROKEN |
| J-10 | Queued/running | Live progress, hủy được | Card có progress nhưng không poll/SSE/cancel tại app | EV-BR-001, EV-SRC-002 | PARTIAL |
| J-11 | Failed/cancelled | Lỗi thân thiện, retry dùng lại setting/ref | Lộ provider error; chỉ có “Biến thể” và log, không retry | EV-BR-001 | PARTIAL |
| J-12 | Done | Preview/tải/variant/upscale | Video, tải, variant, quote Upscale có | EV-BR-001, EV-TEST-001 | LIVE |
| J-13 | Settle token thật | Không vượt số dư đã chấp thuận | Actual > hold được trừ thêm, không check balance | EV-SRC-005, EV-COST-001 | BROKEN |
| J-14 | Reload/history | Tìm đủ job/tài sản, trạng thái mới | Chỉ 60 job; không pagination; trang không live refresh | EV-SRC-002/003 | PARTIAL |
| J-15 | EN A-Z | Không lẫn VI, giữ `/en/` | Title/status/quote/action/link literal VI/absolute; lỗi credit rơi VI | EV-BR-002/005 | BROKEN |
| J-16 | Mobile keyboard | Drawer đóng không nhận focus; Escape trả focus | Tab vào radio ngoài màn hình; Escape để focus ở panel ẩn | EV-BR-002 | BROKEN |

## Control registry

| ID | Control | Action/credit | State/error/recovery | Keyboard/mobile | Evidence | Verdict |
|---|---|---|---|---|---|---|
| C-01 | Mobile “Thiết lập” | Mở drawer local | Đóng bằng Escape | Focus không restore, panel không inert | EV-BR-002 | BROKEN |
| C-02 | Model Mini/Standard/Fast | Đổi capability + quote | Stable | Label click/keyboard được | EV-BR-003 | LIVE |
| C-03 | Prompt | Required, 10k | Counter/history hint | Textarea tốt | EV-BR-001 | LIVE |
| C-04 | Translate EN/中/VI | Không credit, CSRF | Error literal VI | HTMX thay textarea | EV-SRC-003 | PARTIAL |
| C-05 | Creative options | Nối camera/motion/style vào prompt | Preview riêng | Advanced collapse | EV-BR-003 | PARTIAL |
| C-06 | Image/video/audio picker | Lưu blob trước submit | Không per-item remove/undo | Mobile input dùng được | EV-BR-004 | PARTIAL |
| C-07 | Ref role/handle | First/last/mask/reference/@handle | Validation không giải thích capability conflict | Select/text | EV-SRC-002/003 | PARTIAL |
| C-08 | Saved asset picker | Chọn key owner-scoped | Chỉ 60 job, không delete | Checkbox | EV-SRC-003 | PARTIAL |
| C-09 | Duration/aspect/resolution | Quote lại | Registry lọc theo model | Combobox | EV-BR-003 | LIVE |
| C-10 | Audio toggle | Param provider | Không nêu model/language constraint | Checkbox | EV-SRC-001/002 | PARTIAL |
| C-11 | Count 1/2 | Hold ×N | Không disable submit | Combobox | EV-BR-003 | PARTIAL |
| C-12 | Seed | Repro biến thể | Validation server làm mất form khi lỗi | Advanced input | EV-SRC-003 | PARTIAL |
| C-13 | Live estimate | POST `/estimate` | Lệch video-ref; gọi dồn không debounce | aria-live gián tiếp | EV-BR-003/004 | BROKEN |
| C-14 | Tạo video | POST queue + hold | Thiếu credit 400/mất dữ liệu | Button không chống double click | EV-BR-005 | BROKEN |
| C-15 | Filter/status/model/aspect/sort | Query SSR | EN label và link không giữ locale | Keyboard dùng được | EV-BR-001/002 | PARTIAL |
| C-16 | Grid/list | LocalStorage | Stable | Responsive không overflow | EV-BR-001/002 | LIVE |
| C-17 | Job progress/card | Read Job | Không refresh; status kỹ thuật/lẫn ngôn ngữ | Semantics có | EV-BR-001 | PARTIAL |
| C-18 | Variant | Điền lại prompt/settings | Không xác nhận ref còn tồn tại | Button | EV-SRC-002 | PARTIAL |
| C-19 | Download | Redirect signed/local | Có thể mở player thay attachment qua R2 | Link | EV-SRC-003 | PARTIAL |
| C-20 | Upscale | Quote rồi confirm + hold | Owner/CSRF tốt | Modal/button | EV-SRC-006/TEST-001 | LIVE |
| C-21 | Cancel/retry | Không có tại card | Chỉ global Jobs | — | EV-BR-001 | MISSING |
| C-22 | Full history/delete asset | Không có | Không recovery/retention self-service | — | EV-SRC-002/003 | MISSING |

## Browser matrix

| Viewport/flow | Console/network | Overflow | Focus/i18n | Verdict |
|---|---|---|---|---|
| 1440×900 VI, 7 job đủ state | Sạch ở initial load | Không | Core controls dùng được | PASS có điều kiện |
| Real image + real video refs | Nhiều `blob:` `ERR_FILE_NOT_FOUND` sau đổi selection | Không | 5 item chỉ báo validity khi submit | FAIL |
| Safe submit 2 variants | 2 queued; 94 credit hold; 1000→906 | Không | Không gọi provider | PASS |
| `/en/` 1440 | Quote/status/title/action lẫn VI | Không | Locale không bền | FAIL |
| Insufficient credit EN | POST 400/console error; URL `/taovideo/queue` | Không | Prompt/model/count mất, EN→VI | FAIL |
| 390×844 EN | Initial request không fail | Không | Tab/Escape focus vào panel ngoài màn hình | FAIL |

## Deep-round registry delta

| ID | Control/journey | Kết quả thật | Verdict |
|---|---|---|---|
| J-17 | Job thật image+video → provider → output | 1 canary DONE; asset stage, poll, R2 MP4 và browser playback đều PASS | LIVE có điều kiện |
| J-18 | Audio reference contract | Route accepts UI file nhưng worker maps audio to Image/image/png | BROKEN |
| J-19 | Remix saved references | `Biến thể` mở drawer/count=2 nhưng không tick saved refs/handles | MISLEADING |
| J-20 | Actual credit settlement | 78 actual vs 29 video-rate hold; balance 520→442 | BROKEN/P0 |
| C-23 | Asset remote lifecycle | No hash cache/reconcile/pin/grace/LRU/delete registry in LTT | MISSING |
| C-24 | Output verification | Browser + ffprobe evidence PASS for canary; handler still lacks runtime ffprobe contract | PARTIAL |

Deep-round evidence: EV-RJ-001..004, EV-BR-007..009, EV-MEDIA-001.
