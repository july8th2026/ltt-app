# H33.R5 — Job Center recovery evidence

Ngày: 2026-08-12  
Phạm vi: lát cắt progress/offline/terminal dùng chung; chưa phải toàn bộ R5.

## Thay đổi

- Poll 2 giây khi request thành công; lỗi mạng tăng 4→8→16→30 giây.
- `online` và quay lại tab visible đưa lịch về 2 giây.
- Notice customer-safe xuất hiện khi mất mạng và tự ẩn khi hồi phục.
- Terminal response mang `X-LTT-Job-Terminal: 1`; trang reload đúng một lần để
  action, artifact và credit mới nằm ngoài progress fragment xuất hiện.
- Poll dừng ở terminal và `beforeunload`; ownership/API hiện có không đổi.

## Bằng chứng

| Kiểm tra | Kết quả |
|---|---|
| Targeted integration/template | **29 passed** |
| `python tools\gate.py --quick` | **PASS 8/8** |
| `python tools\gate.py` | **PASS 9/9**, 1.783,8s; pytest 1.756,6s |
| Playwright fixture 8152, job queued thật | offline 15s chỉ 3 request mới (2→4→8), notice hiện |
| Bật mạng lại | progress 200, notice ẩn |
| Terminal từ tab thứ hai | tab theo dõi tự reload, hiện `Thử lại`, credit 995→1000 |
| Mobile 390×844 | scrollWidth = clientWidth = 390 |
| Console sau recovery/terminal | **0 error, 0 warning** |

Fixture 8151/8152 và browser tabs đã dừng/đóng. Production 8100 không bị chạm.

## Còn mở

- Draft recovery cần contract privacy/user scoping; không lưu prompt nhạy cảm
  tùy tiện vào localStorage.
- Preflight/confirmation matrix còn lại và browser A–Z sáu app phải chạy trên
  exact staging release candidate ở R6.
