# H26.6 — Auto Sub Studio release audit

Ngày: 2026-08-08
Trạng thái: PASS trong môi trường cô lập; chưa deploy.

## Root cause và phạm vi sửa

- React Studio và bundle production đã tồn tại, nhưng khi biến
  `LTT_AUTOSUB_STUDIO_ROLLOUT` mất/rỗng sau reset, route tự trả form legacy.
  Sau AS9/Q50, Studio nay là public mặc định; `off` vẫn là rollback chủ ý.
- Bundle thiếu hoặc hỏng vẫn tự về legacy, tránh trả một editor vỏ rỗng.
- Render từng dùng chung state với diarize/translate, làm UI hiển thị sai tiến
  độ công cụ AI. Hai lifecycle nay độc lập.
- Thêm API lịch sử job owner-only, lọc theo project; UI khôi phục render gần
  nhất sau reload và dẫn tới nhật ký job chung để phục vụ debug.
- Trạng thái job khách hàng nhìn thấy được Việt hóa; video/ASS/ZIP dùng cơ chế
  download của trình duyệt.

## Nghiệm thu người dùng thật

Môi trường fixture cô lập ở cổng 8111, SQLite và local storage trong `tmp/`;
cổng production 8100 không bị thay đổi. Video nguồn chỉ đọc từ thư mục người
dùng đã cho phép, transcript dùng fixture SRT trong repo.

Luồng đã chạy thật:

1. đăng nhập tài khoản test;
2. upload video 10 giây và đọc metadata 864×496;
3. import SRT ba cue, transcript QA 100/100;
4. chọn preset TikTok Bold;
5. nhận quote 1 credit, xác nhận hold và số dư giảm 1000 → 999;
6. reload khi job đang chờ, lịch sử và render panel khôi phục đúng;
7. worker FFmpeg/NVENC render hoàn tất;
8. tải ZIP bằng Playwright và mở kiểm tra đủ
   `sub-combined.ass`, `render-manifest.json`, SRT, VTT, JSON.

Desktop 1920×1080 và mobile 390×844 PASS. Mobile đo
`documentElement.scrollWidth=375 <= innerWidth=390`; không tràn ngang. Console
0 error/0 warning. Request ứng dụng là 200/202/206; 302 chỉ là middleware locale
rồi endpoint đích trả 200/206.

## Kiểm thử

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `npm test -- --run` | PASS 13 test |
| `npm run build` | PASS typecheck + Vite + build-meta |
| `python -m pytest tests/test_81_autosubvideo.py tests/test_103_autosub_projects.py tests/test_148_frontend_bundle.py -q` | PASS 44 test; 3 warning cũ |
| Playwright A-Z + reload + download + mobile | PASS |
| `python tools/gate.py` | PASS 9/9 trong 1.644,9 giây; pytest 1.617,2 giây |

## Rollback

Đặt `LTT_AUTOSUB_STUDIO_ROLLOUT=off` để trả form legacy trong release này.
Nếu bundle Studio không đọc được, route tự fail-safe về legacy. Không có
migration phá dữ liệu; lịch sử job dùng bảng job hiện hữu.

## Việc không thuộc phase

- Không deploy ở H26.6; release toàn hệ thống vẫn khóa tới H26.12.
- Không chạy dịch/diarization bằng provider ngoài khi capability chưa cấu hình.
- Không thay đổi giá Auto Sub.
