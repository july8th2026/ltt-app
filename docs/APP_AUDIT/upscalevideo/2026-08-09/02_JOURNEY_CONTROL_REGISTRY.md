# 02 — Journey & Control Registry: Upscale Video

## Journey/state matrix

| ID | Persona/JTBD | State | Kỳ vọng | Kết quả thật | Evidence | Verdict |
|---|---|---|---|---|---|---|
| J-01 | JTBD1 | Empty | CTA rõ, không báo giá giả | Có empty upload/queue; cost “Chọn video” | EV-BR-001 | LIVE |
| J-02 | JTBD1 | Input hợp lệ | Đọc metadata, preview, quote | Video thật 10s/2.9MB, quote 5 credit | EV-BR-003 | LIVE |
| J-03 | JTBD1 | Sai extension | Không thay state, lỗi theo locale | Chặn nhưng `/en/` báo tiếng Việt | EV-BR-004 | PARTIAL |
| J-04 | JTBD1 | File giả video | Server xác minh trước khi hold | Chỉ extension/client probe; worker mới probe sâu | EV-SRC-003/004 | PARTIAL |
| J-05 | JTBD1 | File >90MB local | Chuyển direct upload hoặc hướng dẫn dễ hiểu | Có fallback; copy lộ R2/CORS nội bộ | EV-SRC-002/003 | MISLEADING |
| J-06 | JTBD1 | Direct R2 | Giới hạn loại, size, quota, TTL | Ticket không CSRF/allowlist/size/quota; key tồn tại ngoài job | EV-SRC-003 | BROKEN |
| J-07 | JTBD1 | Insufficient credit | Không tạo job/artifact; hướng nạp | DB rollback nhưng artifact đã ghi trước hold | EV-SRC-003/005 | BROKEN |
| J-08 | JTBD1 | Batch 1–3 | Quote tổng, all-or-none | DB/credit nguyên tử, limit 3; artifact không nguyên tử | EV-SRC-003, EV-TEST-001 | PARTIAL |
| J-09 | JTBD1 | Submit | Chốt giá trước hold, feedback và chống double click | Quote hiện, button disable; không có confirm cuối | EV-SRC-002 | PARTIAL |
| J-10 | JTBD2 | Queued/running | Vị trí/ETA/progress tự cập nhật | Có position/ETA khi render; trang không polling | EV-SRC-001/002 | PARTIAL |
| J-11 | JTBD2 | Done | So sánh và tải đúng owner | Compare pointer/keyboard và download owner-only PASS | EV-BR-003, EV-TEST-001 | LIVE |
| J-12 | JTBD2 | Failed | Lỗi hiểu được, retry tại ngữ cảnh | Có error text; không có retry trong app | EV-BR-001, EV-SRC-002 | PARTIAL |
| J-13 | JTBD3 | Cancelled | Hủy/refund idempotent, giữ locale | Refund contract có; `/en/` hủy rơi về VI | EV-BR-004, EV-TEST-001 | PARTIAL |
| J-14 | JTBD3 | Retry | Dùng lại input/setting, không double charge | Nền tảng có retry nhưng app không lộ | EV-SRC-004 | MISSING |
| J-15 | JTBD3 | Reload/history | Khôi phục toàn bộ lịch sử có phân trang | Query 50 nhưng render 12; không link full history | EV-SRC-001/002 | PARTIAL |
| J-16 | JTBD3 | Offline/network fail | Giữ selection, retry upload/quote | Bắt lỗi bằng text; reload mất selection, không resume | EV-SRC-002 | PARTIAL |
| J-17 | JTBD3 | Artifact missing | Báo lỗi, retry/recover/cleanup | 404 đúng; không recovery hoặc cleanup customer-facing | EV-SRC-003 | PARTIAL |
| J-18 | JTBD2 | Output quality | Preview đại diện và chất lượng cạnh tranh | Preview 8s có; chưa blind benchmark temporal quality | EV-GPU-001/002 | UNKNOWN |

## Control Registry

| ID | Screen/control | Visible/enabled rule | Role | Action/API | Credit | Loading/success/error | Cancel/retry/undo | Keyboard/mobile | Telemetry | Evidence | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C-01 | Mobile “Thiết lập nâng cấp” | ≤720px | button/expanded | Mở/đóng form local | Không | Tức thời | Đóng lại | Keyboard PASS; sticky mobile | Không | EV-BR-002 | LIVE |
| C-02 | Fast | Luôn | radio | `preset=fast` | Quote lại | Có mô tả | Không | Label target tốt | Params/job | EV-BR-003 | LIVE |
| C-03 | Quality | Luôn | radio | `preset=quality` | Quote lại | Có cảnh báo chậm nhưng không ETA | Không | Label target tốt | Params/job | EV-SRC-002 | PARTIAL |
| C-04 | 1080/1440/2160 | Luôn | radio group | `target_height` | Quote lại | Tức thời | Không | Label target tốt | Params/job | EV-BR-003 | LIVE |
| C-05 | Codec H264/HEVC | Luôn | combobox | `codec` | Không đổi | Không giải thích tương thích | Không | A11y name có | Params/job | EV-SRC-002 | PARTIAL |
| C-06 | Giữ FPS | Luôn | checkbox | `preserve_fps` | Không đổi | Tắt smooth khi bật | Không | Mobile PASS | Params/job | EV-BR-003 | LIVE |
| C-07 | Giữ audio | Luôn | checkbox | `preserve_audio` | Không đổi | Trạng thái rõ | Không | Mobile PASS | Params/job | EV-SRC-002 | LIVE |
| C-08 | Preview 8s | Luôn | checkbox | `preview` | Quote lại | Không cho biết đoạn preview | Không | Mobile PASS | Params/job | EV-BR-003 | PARTIAL |
| C-09 | Chống rung | Luôn | checkbox | `stabilize` | +20% | Copy kỹ thuật “libvidstab two-pass” | Không | Mobile PASS | Params/job | EV-SRC-002 | PARTIAL |
| C-10 | Smooth motion 2× | Luôn | checkbox | `smooth_motion` | +120% | Tắt preserve FPS | Không | Mobile PASS | Params/job | EV-BR-003 | LIVE |
| C-11 | Batch | Luôn | checkbox | Multi-file tối đa 3 | Quote tổng | Cắt danh sách >3 với status | Không | Mobile PASS | request_id/job | EV-SRC-002/003 | PARTIAL |
| C-12 | Cost estimate | Khi có file | live status | `POST /batch-quote` | Hiển thị tổng | Error text; không breakdown thời gian/size | Không | aria-live gián tiếp | Không | EV-BR-003 | PARTIAL |
| C-13 | Dropzone | Luôn | file input/drop target | Chọn/probe client | Không | Có filename/size/duration | Chọn lại | Touch/button có | Không | EV-BR-003 | LIVE |
| C-14 | Upload direct/local | Khi submit | hidden workflow | `POST /upload-url`, PUT R2 hoặc multipart | Trước hold | Có % direct; thiếu policy/quota | Không resume | Mobile phụ thuộc browser | Không đủ | EV-SRC-002/003 | BROKEN |
| C-15 | Bắt đầu xử lý | Khi form | submit button | `POST /batch` | Hold khi submit | Disable; trả error | Không confirm/undo | Keyboard PASS | JobEvent sau submit | EV-SRC-002/003 | PARTIAL |
| C-16 | Source preview | Có latest/file | video controls | blob/source endpoint | Không | Native player | Không | Keyboard native | Range request | EV-BR-003/005 | LIVE |
| C-17 | Before/after slider | Có output; disabled nếu chưa có | slider | clip-path + sync player | Không | Pointer + arrows/home/end | Reset 50 | 50→100→90 PASS | Không | EV-BR-003 | LIVE |
| C-18 | Queue filters | Có queue | pressed buttons | Client filter | Không | Count shown | All reset | Keyboard/mobile PASS | Không | EV-BR-001 | LIVE |
| C-19 | Queue sort | Có queue | combobox | Client sort | Không | Tức thời | Chọn lại | Keyboard PASS | Không | EV-BR-001 | LIVE |
| C-20 | List/grid | Có queue | pressed buttons | LocalStorage view | Không | Tức thời | Chọn lại | Keyboard/mobile PASS | Không | EV-BR-001/002 | LIVE |
| C-21 | Job card/progress | 12 job mới nhất | article/progressbar | Render server | Đã hold | Không tự refresh; status nội bộ có thể lộ | Không | Semantics có | JobEvent ngoài app | EV-SRC-001/002 | PARTIAL |
| C-22 | Download | Job done | link | owner-only stream attachment | Không | 404 nếu thiếu | Không resume trong UI | Keyboard PASS | Access log | EV-TEST-001 | PARTIAL |
| C-23 | Compare job | Job done | link | Đổi source/output trong panel | Không | Tức thời | Không | Keyboard link PASS | Không | EV-BR-003 | LIVE |
| C-24 | Cancel | Queued/running | form/button | `POST /jobs/{id}/cancel` | Refund idempotent | Redirect; mất locale EN | Không undo | Keyboard PASS | JobEvent/refund | EV-BR-004 | PARTIAL |
| C-25 | Retry | Failed/cancelled | — | Nền tảng `/jobs`, app không có | Giữ mới theo contract | Không hiện | MISSING | — | JobEvent nền tảng | EV-SRC-002/004 | MISSING |
| C-26 | Full history/pagination | >12 job | — | Query có 50, UI cắt 12 | Không | Count chỉ 12 | — | — | Có DB | EV-SRC-001 | MISSING |
| C-27 | Watch token controls | Chỉ admin | buttons | rotate/revoke token | Không | One-time token | Revoke | Keyboard | Admin telemetry | EV-SRC-002/003 | LIVE |
| C-28 | Shared topbar icon links | Shell | links | Điều hướng | Không | Một số icon không có accessible name | — | Focus được nhưng tên rỗng | Không | EV-BR-001/002 | BROKEN |

## Browser matrix

| Viewport/state | Console | Failed requests | Overflow | Keyboard/focus | Screenshot/evidence | PASS |
|---|---|---|---|---|---|---|
| 1440×900 VI, 3 job | 0 error/warning | 0 failed | Không | Compare/filter/form PASS; shell icon name rỗng | EV-BR-001/003/005 | PARTIAL |
| 390×844 VI | 0 error/warning | 0 failed | Không | Form collapse và control chính dùng được | EV-BR-002 | PASS |
| 390×844 EN invalid | 0 | 0 | Không | Lỗi phát âm/hiển thị sai ngôn ngữ | EV-BR-004 | FAIL |
| 390×844 EN cancel | 0 | 0 | Không | Redirect làm mất `/en/` | EV-BR-004 | FAIL |
| Upload video thật/quote | 0 | 0 | Không | Upload, quote, toggle mutual exclusion PASS | EV-BR-003 | PASS |
| Compare done artifact | 0 | 0 | Không | Pointer + arrows/home/end PASS | EV-BR-003 | PASS |

