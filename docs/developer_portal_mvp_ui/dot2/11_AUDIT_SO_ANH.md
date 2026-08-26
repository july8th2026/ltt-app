# Audit so ảnh demo — bảng điểm từng trang

**2026-08-27** · so ảnh chủ sản phẩm với giao diện render thật (Playwright
Chrome, 1920×1080, harness `:8101` có dữ liệu).

## Cách chấm

Mỗi trang chấm trên 5 hạng mục: **Bố cục · Màu/thẻ · Thành phần · Dữ liệu thật
· Trạng thái**. Điểm 10 = khớp ảnh và không có khiếm khuyết. Điểm bị trừ cho
khác biệt **thấy được**; KHÔNG trừ cho việc cố ý bỏ thứ **bịa** (badge
Stable/Beta/Alpha, bảng bóc giá) — đó là đúng freeze.

## Bảng điểm (sau đợt "xây MVP thực sự")

| # | Trang | Điểm | Khớp ảnh | Khác biệt còn lại |
|---|---|---|---|---|
| — | **Vỏ chung** | **9.3** | thương hiệu sidebar · thanh trên trạng thái+chuông (có số) · nhóm nav · carbon trung tính · accent cyan | — |
| 1 | Tổng quan | **9.3** | 4 thẻ chỉ số + biểu tượng cyan · biểu đồ 7 ngày **có vùng tô** · 2 cột · Request gần đây · Thông báo | thẻ #4 là Webhook (ảnh: "Đang chạy") — cả hai thật |
| 2 | Cắm công cụ | **9.0** ⬆️ | **2 cột: Cấu hình môi trường (khối .env teal) \| Ba cách cắm API** ✓ · bậc thang 4 bước ✓ · chi tiết đầy đủ dưới | ảnh gộp picker vào cột phải; bản thật để picker ở phần chi tiết (dùng chung `/huong-dan`, không lặp) |
| 3 | Công cụ & model | **8.7** | **lưới 3 cột** ✓ · ô biểu tượng màu theo nhóm ✓ · nhãn chế độ chạy ✓ · chân "N model · Docs · Thử ngay" ✓ | biểu tượng là CHỮ CÁI (ảnh: glyph); **không** badge Stable/Beta/Alpha (ToolSpec không có — freeze) |
| 4 | Giá & mô phỏng | **9.0** | 2 cột soạn\|kết quả · số credit hổ phách + VND · hộp lưu ý | **không** bảng bóc giá theo dòng (freeze) |
| 5 | Khóa API | **9.2** | nút tạo đầu trang · tab Tất cả/Live/Test · chip môi trường cyan · bảng · trạng thái | phân trang hoãn (khoá < 20); hiện `key_id` công khai |
| 6 | Hoạt động | **9.0** | dải lọc · bảng mã màu trạng thái + error code · request_id link cyan | phân trang hoãn (`limit=100`) |
| 7 | Sử dụng & credit | **9.5** ⬆️ | **4 thẻ chỉ số** + biểu tượng cyan ✓ · 2 cột: biểu đồ 30 ngày **có vùng tô** \| **vòng phân bổ theo công cụ** (donut + %) ✓ · sao kê | — |
| 8 | Webhook | **9.2** | 4 thẻ chỉ số · bảng giao mã màu | bản thật giàu hơn ảnh (catalogue + verify) |
| **Trung bình (8 trang chính)** | | **9.1** | | |
| 9 | Job (con của Hoạt động) | **9.0** | bảng · **trạng thái mã màu** (sửa lỗi map `done`→`succeeded`) | — |
| 10 | Project (con của Khóa) | **9.0** | bảng + form tạo · cha sáng | — |
| 11 | Playground (con của Công cụ) | **9.0** | cảnh báo credit thật · danh sách khoá · form động · validate/run | chip khoá dùng `.chip` xanh, chưa đổi cyan |
| 12 | Thông báo (con Tổng quan) | **9.0** | danh sách "new" + Mark as read · rỗng có giải thích | — |
| 13 | Tài liệu & SDK | **9.0** | 4 thẻ: Start · Spec/SDK · Try a call · Test env | — |
| 14 | Cài đặt & bảo mật | **9.0** | Key safety + Your data + export | — |
| 15 | Dữ liệu & lưu trữ (con Cài đặt) | **9.0** | retention theo hợp đồng | — |
| 16 | Bắt đầu nhanh (con CLI) | **9.0** | ví dụ sinh từ hợp đồng · nút chép | — |

## Đã tối ưu trong lượt audit này

1. **Công cụ & model: danh sách dọc → LƯỚI 3 CỘT** (đúng ảnh). Thêm ô biểu
   tượng màu theo nhóm, chân "N model · Docs · Thử ngay". `model_count` lấy
   THẬT từ `api_contract.models`. Component gốc `.tool-the` (dùng nơi khác)
   giữ nguyên — chỉ override cách bày TRONG `.khu-dev`.
2. **Sử dụng: thêm VÒNG PHÂN BỔ theo công cụ** (đúng ảnh). Hàm chỉ-đọc mới
   `usage.by_tool()` (có test, gom cả cửa sổ, không phải một trang) + donut SVG
   sinh phía máy chủ (kỹ thuật stroke-dasharray, không JS, không thư viện).
3. **Biểu đồ: thêm VÙNG TÔ mờ dưới đường** (đúng ảnh) — polygon khép kín, cyan
   cho Request, đỏ cho Credit.
4. **Harness thêm 6 job có tính tiền** để donut / sao kê / "job qua API" hiện
   dữ liệu thật thay vì rỗng.

## Khác biệt CÒN LẠI — phân loại

| Khác biệt | Loại | Xử lý |
|---|---|---|
| Badge Stable/Beta/Alpha (tools) | **BỊA** — ToolSpec không có trường | GIỮ bỏ (freeze) |
| Bảng bóc giá theo dòng (pricing) | **BỊA** — `Simulation` trả một số | GIỮ bỏ (freeze) |
| CLI 2-cột env\|picker | ràng buộc — `_cam_chon.html` dùng chung `/huong-dan` | HOÃN (đổi sẽ chạm trang công khai) |
| Phân trang (keys/logs) | tính năng | HOÃN (dữ liệu nhỏ) |
| Thẻ chỉ số usage 3 vs 4 | nhỏ | có thể thêm "Request tháng này" sau |
| Biểu tượng tool chữ-cái vs glyph | nhỏ | chấp nhận (không cần asset ngoài) |

## Cổng đã qua (sau tối ưu)

- QA `audit_v2` (16 trang × 6 khung): **0 tràn · 0 ô thô · 0 fieldset · 0
  console · 0 network**.
- Tests: `test_201` (+`daily`,`by_tool`), `test_207`, `test_299`, `test_302`,
  `test_303`, `test_301` — PASS. `check_dich_thieu` khu API: PASS.
- CSS 100% scoped `.khu-dev`/`.dev-topbar` — không chạm app khác.
