# Bổ sung cho `PHAP_LY_NHAP.md` — kho tài khoản hệ thống (chủ dự án duyệt 23/09/2026)

> Dán vào `docs/migrations/video_crawler/PHAP_LY_NHAP.md` thành mục mới. Chủ dự án đã chấp nhận LTT đứng tên phiên.

## X. Phiên nền tảng do LTT cung cấp ("kho tài khoản hệ thống")

**Sự việc.** Một số nền (Douyin, Xiaohongshu, TikTok ở chế độ tìm kiếm/kênh) chỉ trả dữ liệu cho phiên đã đăng nhập.
Khách không có `cookies.txt` thì không dùng được. LTT vận hành **tài khoản phụ của riêng LTT** trên các nền này; job
của khách mượn phiên đó khi khách chưa tự thêm phiên.

**Hệ quả pháp lý phải nói rõ, không giấu.**

1. **LTT là bên truy cập.** Với lượt dùng kho, phiên đăng nhập trên nền mang danh nghĩa LTT, không phải khách. Mọi
   ràng buộc trong điều khoản dịch vụ của nền (kể cả điều cấm truy cập tự động) áp lên LTT.
2. **Rủi ro tài khoản là của LTT**, không đẩy sang khách: nền khoá tài khoản phụ thì nền đó tạm ngừng phục vụ; khách
   không bị tính tiền cho lượt hỏng (job lỗi ⇒ hoàn credit theo sổ hiện hành).
3. **Trách nhiệm nội dung vẫn của khách.** Ô cam kết quyền (mục L1) áp cho MỌI lượt tải, kể cả lượt dùng kho. LTT
   không kiểm duyệt trước nội dung khách chọn, nhưng lưu nhật ký đủ để trả lời khiếu nại: ai, lúc nào, nền nào,
   mã video nào, nguồn phiên (`rieng` hay `kho`).
4. **Gỡ theo yêu cầu.** Kênh báo vi phạm `support@lttstudios.com` và trang báo vi phạm giữ nguyên cam kết 72 giờ
   (NĐ 17/2023 Đ.114). Với lượt dùng kho, LTT chủ động gỡ tệp và khoá tài khoản khách vi phạm lặp lại.
5. **Giới hạn kỹ thuật là một phần của cam kết**, không phải tuỳ chọn vận hành: một tài khoản kho phục vụ một job
   một lúc, có trần lượt/giờ và nghỉ giữa các lượt; mỗi khách có trần riêng khi dùng kho. Mục đích: không biến kho
   thành công cụ cào quy mô lớn dưới danh nghĩa LTT.
6. **Không dùng kho cho nội dung riêng tư theo tài khoản** (danh sách theo dõi, video đã thích, nội dung trả phí của
   nền). Kho chỉ để lấy nội dung mà một người dùng đã đăng nhập bình thường cũng xem được.
7. **Tài khoản kho là tài khoản phụ**, không phải tài khoản cá nhân/kênh kinh doanh của chủ dự án.

**Nền KHÔNG đưa vào kho ở đợt này.**

| Nền | Lý do |
|---|---|
| Bilibili | Tiền lệ pháp lý thật: luật sư đại diện Bilibili gửi thư cảnh cáo khiến `SocialSisterYi/bilibili-API-collect` (28/01/2026) và `Nemo2011/bilibili-api` (06/07/2026) đóng kho vĩnh viễn, với cáo buộc vượt xác thực và cào nội dung trả phí. Vận hành kho tài khoản Bilibili cho SaaS thương mại là rủi ro trực diện. |
| Instagram | Cơ chế khoá và bắt xác minh mạnh nhất; cộng đồng (instagrapi) yêu cầu mỗi tài khoản một IP cố định — chưa có hạ tầng đó. |

**Cần chủ dự án ký/duyệt:** mục này cùng `PHAP_LY_NHAP.md`; sau đó bổ sung một câu vào Điều khoản sử dụng công khai
rằng LTT có thể dùng phiên do LTT cung cấp để thực hiện yêu cầu của khách trên các nền nhất định.
