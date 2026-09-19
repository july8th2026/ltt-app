# 02 — Journey & Control Registry

| Journey/control | Kết quả | Evidence | Verdict |
|---|---|---|---|
| Empty state + 3 flow khởi đầu | Tạo được flow mẫu có nghĩa | Browser 1920 | LIVE |
| Palette chế độ đơn giản | Chỉ thấy Text/Image/Video/Audio | Browser, `aria-pressed=false` | LIVE |
| Công cụ nâng cao | Có opt-in, không ép mental model dev | Browser/source | LIVE |
| Text → Image | 2 node/1 edge, nhập prompt trực tiếp | Browser | LIVE |
| Run block Image | Drawer nói rõ target, 2 bước upstream, max 8 credit | Browser/API | LIVE |
| Confirm/settlement | Hoàn tất 2 bước, dùng 8/8 | Browser/DB fixture | LIVE |
| Reload | Graph/kết quả còn bền | Browser reload | LIVE |
| Theme | Light lưu qua reload; dark khôi phục được | Browser | LIVE |
| Mobile 390 | Không overflow; drawer 318 px nằm trong viewport | Browser | LIVE |
| Console/network | 0 error/warning; API 200/201, locale 302→200 hợp lệ | Browser | LIVE |
| Provider thật, timeout/offline | Chưa chạy trong delta | — | MISSING E3/E4 |
| Load/soak/SLO | Chuyển H26.11 | — | MISSING |

Không phát hiện control DEAD/MISLEADING mới trong phạm vi đã chạy. Run block là
scoped execution có dependency closure, không phải nút giả chạy toàn workflow.
