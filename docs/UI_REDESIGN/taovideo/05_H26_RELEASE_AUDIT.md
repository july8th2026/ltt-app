# H26.7 — Tạo Video Seedance release audit

Ngày bắt đầu: 2026-08-08
Ngày hoàn tất: 2026-08-09
Trạng thái: code và browser PASS trong fixture cô lập; chưa deploy.

## Finding đã đóng

- Tên public đổi từ Tạo video AI thành **Tạo Video Seedance**; slug, route,
  ToolSpec và `taovideo.generate` không đổi.
- Camera/motion/style/seed vẫn hoạt động nhưng chuyển vào vùng sáng tạo mặc định
  đóng, không đẩy thuật ngữ nâng cao vào luồng chính của khách hàng.
- Ảnh/video/audio có picker riêng, preview file thật, role và handle. Giới hạn
  vẫn là bốn tài sản theo backend; không sao chép con số minh họa trong ảnh.
- Thư viện bổ sung status/model/aspect/sort, cancelled, grid/list lưu qua reload,
  metadata model/time và link nhật ký trên mọi job.
- Báo giá trước đây chỉ hiện một video khi quantity=2. Nay hiện tổng credit hold
  thật: browser mini/480p/4s ×2 báo 94 credit, đồng thời ghi rõ quyết toán theo
  token provider thật.
- Preview ảnh ban đầu dùng blob và bị CSP chặn. Browser audit bắt được; ảnh nay
  dùng data URL, video/audio dùng blob đúng `media-src`, không nới CSP nền tảng.

## Browser A-Z cô lập

Fixture cổng 8112, SQLite/local storage trong `tmp/`, tài khoản test 1000 credit,
không có worker và không gọi BytePlus.

- Desktop 1920×1080: ba vùng, gallery ba cột, output video thật Range 206.
- Grid/list đổi và khôi phục sau reload.
- Standard hiện 480p/720p/1080p/4K; Fast hiện 480p/720p; duration và sáu aspect
  lấy từ registry; seed vẫn enabled đúng capability.
- Chọn ảnh tham khảo hiển thị preview 1586×992, console sạch sau CSP fix.
- Advanced mở được; camera tracking, motion cinematic, realistic, seed 123 đi
  cùng submit hai biến thể. Fixture tạo hai job queued, credit 1000→906, một
  asset history và ba link nhật ký; không chạy provider.
- Filter Mini trả đúng hai queued job; cancelled trả empty state.
- Popup Upscale của output owner-scoped báo 3 credit; không confirm trong audit.
- Mobile 390×844: drawer mở/đóng đúng, rộng 375,2 px; không overflow toàn trang;
  list view và video card hoạt động.
- Console cuối: 0 error, 0 warning. Request ứng dụng 200/206; không request fail.

## Test

| Lệnh | Kết quả |
|---|---|
| Targeted Taovideo H26 | PASS 41 test |
| Vận hành/adaptive/layering | PASS 35 test; 1 warning TestClient cũ |
| `python tools/gate.py --quick` lượt đầu | FAIL đúng một chuỗi báo giá chưa bọc i18n; đã sửa |
| `python tools/gate.py --quick` sau sửa | PASS 8/8 trong 25,6 giây |
| `python tools/gate.py` | PASS 9/9 trong 1.616,1 giây; pytest 1.590,7 giây |

Hai lượt gate trước bị kênh theo dõi ngắt/timeout nhưng để lại hai pytest con
chạy đồng thời. Đã xác minh command line/PID, dừng đúng các tiến trình do phiên
này tạo, đóng fixture 8112 rồi chạy lại một lượt sạch duy nhất nêu trên.

## Ranh giới và rollback

- Không thêm retry/delete/bulk delete/template khi chưa có retention/idempotency.
- Không đổi model endpoint, provider, cost formula hoặc worker.
- Rollback bằng revert commit H26.7. Job đã nộp vẫn giữ lifecycle/ledger hiện có;
  không xóa artifact hoặc lịch sử để lùi UI.
