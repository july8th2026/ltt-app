# Danh sách việc — sau vòng test thật 2 máy (2026-08-22)

Lập sau khi chủ sản phẩm chạy app trên **hai máy cùng một tài khoản**, cộng với
một vòng soi giao diện trực tiếp trên máy thật. Mỗi mục có **bằng chứng**, không
phải phỏng đoán.

Trạng thái: ✅ đã xong · 🔨 đang làm · ⬜ chưa bắt đầu

---

## A. LỖI — có bằng chứng, phải sửa

### A1 ✅ Mọi máy luôn hiện "tắt" dù đang chạy
**Bằng chứng:** ảnh chụp app — `DESKTOP-VDG9UNP` chấm xám, trong khi chính máy
đó đang chạy và hiện online ở danh sách peer bên phải.
**Nguyên nhân:** client Model B chỉ gọi `/status` (mỗi 60 giây) và **không bao
giờ** gọi `/heartbeat` — mà chỉ `/heartbeat` mới ghi `last_seen_at`. Nên
`dang_online()` luôn trả False.
**Đã sửa:** `/status` ghi nhịp tim. `OFFLINE_AFTER_S=180` so với nhịp 60 giây là
khớp. Test `test_247`.

### A2 ✅ Mạng chớp một cái là ngừng báo cập nhật
`return` trong `_refresh()` thoát cả hàm, bỏ luôn phần kiểm bản mới. Đã thu hẹp
lại đúng phạm vi cần bảo vệ.

### A3 ⬜ Mục "Về LTTNexus" vẫn là RustDesk
**Bằng chứng:** ảnh chụp — `Copyright © 2026 Purslane Tech Pte. Ltd.`,
**Phiên bản: 1.4.9** (số của RustDesk, không phải `LTT_VERSION` 1.1.0), link
*Chính sách bảo mật* → `rustdesk.com/privacy.html`, *Trang web* → `rustdesk.com`.
**Sửa:** đổi copyright sang LTT Studios, hiện **cả hai** số (LTT 1.1.0 / nền
RustDesk 1.4.9 — giữ minh bạch AGPL), trỏ link về `lttstudios.com`.

### A4 ⬜ Thanh dưới xui người dùng đi dựng máy chủ riêng
**Bằng chứng:** *"Sẵn sàng. Để kết nối nhanh hơn, hãy tự thiết lập máy chủ riêng"*
— câu này của RustDesk, **sai hoàn toàn** với LTT Nexus vì ta đã có relay riêng
và đó là thứ khách trả tiền. **Sửa:** bỏ hoặc thay bằng trạng thái relay LTT.

### A5 ⬜ Hai hệ tài khoản chồng nhau
**Bằng chứng:** Cài đặt → **Tài khoản → "Đăng nhập"** (tài khoản RustDesk) hiện
ra *trong khi* thanh trên đã đăng nhập LTT (`akak… 1342 cr`).
**Sửa:** ẩn mục tài khoản của RustDesk, thay bằng thông tin tài khoản LTT.

### A6 ⬜ Còn nhiều link rustdesk.com người dùng bấm được
`connection_page.dart` (pricing), `desktop_home_page.dart` (download, docs
Linux ×3), `desktop_setting_page.dart` (privacy), `common.dart` (whitelist docs).
**Sửa:** trỏ về `lttstudios.com` hoặc bỏ mục không áp dụng.

### A7 ⬜ `/nexus` trên web vẫn là app web-broker cũ
**Bằng chứng:** `apps/nexus` vẫn đăng ký route `/nexus` + hiện trong menu, nội
dung là luồng "mã ghép + agent" đã bị **đóng băng theo Q101**.
**Sửa:** thay bằng trang **giới thiệu + hướng dẫn + tải về**, hoặc chuyển hướng
sang `/tai-xuong`.

---

## B. THIẾU — cần xây

### B1 ⬜ Installer + tự cập nhật thật *(ưu tiên cao nhất)*
Hiện chỉ **phát hiện** bản mới rồi mở trang tải; người dùng tự giải nén đè.
Bản ZIP portable **không thể** tự cập nhật sạch (không ghi đè được exe đang chạy,
không biết thư mục cài ở đâu).
**Cần:** installer `.exe` (Inno Setup) → client tải installer, **kiểm SHA-256**,
chạy im lặng, tự khởi động lại. Đây cũng đúng cách RustDesk gốc làm.

### B2 ⬜ Nhật ký truy cập cho người dùng
Hiện chỉ có **danh sách máy**, không có *"ai đã vào máy nào, lúc nào"*. Dữ liệu
**đã có sẵn** (`nexus_sessions`, sự kiện P8 start/end) nhưng chưa có chỗ xem.
**Cần:** thêm mục nhật ký vào `/may-cua-toi` — lọc theo máy, hiện thời gian +
IP bên điều khiển.

### B3 ⬜ Đồng nhất tài khoản app ↔ web (SSO)
Bấm **Nạp credit** trong app mở trình duyệt tới `/nap` nhưng **phải đăng nhập
lại**. Cùng một tài khoản mà phải nhập mật khẩu hai lần.
**Cần:** app xin token đăng nhập một lần từ nền tảng (đã ký), mở URL kèm token →
web tự tạo phiên. Trang tài khoản trên web cũng nên hiện máy + thuê bao.

### B4 ⬜ Trang giới thiệu LTT Nexus trên web
Thay `/nexus`: sản phẩm là gì, dùng để làm gì, ảnh chụp, bảng tải 4 nền tảng,
hướng dẫn từng nền tảng, giá credit/máy/tháng, câu hỏi thường gặp.

---

## C. HẠ TẦNG — còn nợ từ audit trước

| # | Việc | Vì sao gấp |
|---|---|---|
| C1 | Dời relay khỏi **Windows Server 2016 Eval** | Hết hạn **15/12/2026** → máy tự tắt mỗi giờ, sập cả mạng VM |
| C2 | Thêm relay thứ hai | Một relay = một điểm chết |
| C3 | Bật `LTT_NEXUS_RELAY_HOST` | Cảnh báo relay đã deploy nhưng **chưa chạy** vì thiếu biến này |
| C4 | Đổi mật khẩu relay + đóng RDP 3389 | Mật khẩu đã lộ (tài liệu của chính dự án ghi) |

---

## Thứ tự đề xuất

1. **A3 + A4 + A5 + A6** — gom một vòng đổi thương hiệu, build một lần. Rẻ, và
   là thứ khách nhìn thấy đầu tiên.
2. **B1 installer + tự cập nhật** — có nó thì mọi bản vá sau này tới được người
   dùng mà không cần hướng dẫn.
3. **A7 + B4** — dọn `/nexus`, dựng trang giới thiệu thật.
4. **B2 nhật ký** rồi **B3 SSO**.
5. **C1–C4** hạ tầng, làm trước tháng 12.
