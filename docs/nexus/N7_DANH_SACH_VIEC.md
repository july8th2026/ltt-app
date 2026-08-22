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

### A3 ✅ Mục "Về LTTNexus" vẫn là RustDesk
**Đã sửa (1.2.0 + 1.3.0).** Nay hiện `Phiên bản: 1.3.0` (số LTT) rồi `Dựa trên
RustDesk 1.4.9`, copyright LTT Studios kèm ghi công AGPL, link trỏ về LTT.

Một cái bẫy đã dính ở 1.2.0: phép đổi thương hiệu trong `src/lang.rs` thay **mọi**
chữ "RustDesk" trong chuỗi dịch, nên dòng ghi công biến thành *"Dựa trên LTTNexus
1.4.9"* — vừa vô nghĩa vừa xoá đúng cái tên AGPL bắt phải giữ. Nay có danh sách
`GIU_TEN_GOC` loại trừ các khoá ghi công. Dòng bản quyền cũng hết chữ không dấu
và khẩu hiệu của RustDesk (`Slogan_tip`) đã thay bằng `ltt_slogan_tip`. Bản
Android/iOS (`mobile/pages/settings_page.dart`) sửa cùng một lượt.

### A4 ✅ Thanh dưới xui người dùng đi dựng máy chủ riêng
**Bằng chứng:** *"Sẵn sàng. Để kết nối nhanh hơn, hãy tự thiết lập máy chủ riêng"*
— câu này của RustDesk, **sai hoàn toàn** với LTT Nexus vì ta đã có relay riêng
và đó là thứ khách trả tiền. **Đã bỏ hẳn khối đó** trong `connection_page.dart`;
thanh dưới nay chỉ còn trạng thái dịch vụ ("Sẵn sàng" / "Dịch vụ hiện đang dừng").
Xác minh trên máy thật ở 1.2.0.

### A5 ✅ Hai hệ tài khoản chồng nhau
**Bằng chứng:** Cài đặt → **Tài khoản → "Đăng nhập"** (tài khoản RustDesk) hiện
ra *trong khi* thanh trên đã đăng nhập LTT (`akak… 1342 cr`).
**Đã sửa:** bỏ `account` khỏi `tabKeys` của Cài đặt. Xác minh trên máy thật:
sidebar còn đúng 6 mục (Chung / Bảo mật / Mạng / Hiển thị / Máy in / Giới thiệu),
không còn mục Tài khoản thứ hai.

### A6 ✅ Còn nhiều link rustdesk.com người dùng bấm được
`connection_page.dart` (pricing), `desktop_home_page.dart` (download, docs
Linux ×3), `desktop_setting_page.dart` (privacy), `common.dart` (whitelist docs).
**Đã sửa:** URL trỏ hết về `lttstudios.com`. Vòng soi 1.3.0 bắt thêm ba chỗ mà
vòng trước bỏ sót vì chỉ tìm URL chứ không tìm **chữ hiển thị**: hai nhãn
`rustdesk.com` in ra màn Cài đặt của bản mobile, tiêu đề `About RustDesk`, và
`powered_by_me` bản tiếng Việt dịch nhầm thành *"Cung cấp bởi tôi"*. Bản mobile
cũng đã hiện số phiên bản LTT thay vì số RustDesk.

### A7 ✅ `/nexus` trên web vẫn là app web-broker cũ
**Bằng chứng:** `apps/nexus` vẫn đăng ký route `/nexus` + hiện trong menu, nội
dung là luồng "mã ghép + agent" đã bị **đóng băng theo Q101**.
**Đã sửa:** `/nexus` nay là **trang giới thiệu công khai** (không cần đăng nhập)
— sản phẩm là gì, 4 nền tảng, 4 bước dùng, giá credit/máy/tháng, FAQ. Tám route
web-broker cũ nằm sau cờ `LTT_NEXUS_WEB_BROKER`, **mặc định TẮT** → 404 kể cả khi
gõ thẳng URL (theo tiền lệ `LTT_SOCIALBOT_ROUTES` của H22.10: đóng sau cờ chứ
không xoá lặng lẽ). Test `test_248`.

Một điểm dễ sai đã chốt bằng test: cổng phải là `Depends` đặt **trước**
`Depends(require_login)` trong chữ ký — để sau thì route đã đóng vẫn trả 303 về
`/login`, tức vẫn xác nhận bề mặt đó tồn tại.

---

## B. THIẾU — cần xây

### B1 ✅ Installer + tự cập nhật thật *(ưu tiên cao nhất)*
Hiện chỉ **phát hiện** bản mới rồi mở trang tải; người dùng tự giải nén đè.
Bản ZIP portable **không thể** tự cập nhật sạch (không ghi đè được exe đang chạy,
không biết thư mục cài ở đâu).
**Đã xong.** Không dùng Inno Setup mà dùng thẳng bộ đóng gói một-file có sẵn của
RustDesk (`libs/portable`) + `--silent-install`. Client tải `setup_url`, **bắt buộc
https**, đối chiếu SHA-256 64 ký tự, chạy im lặng rồi tự khởi động lại.
`phat-hanh-windows.ps1` lo đóng gói + băm + cập nhật bản kê.

**Đã chạy thật trọn vòng 2026-08-22:** từ bản 1.2.0 đang chạy, bấm *Cập nhật ngay*
→ exe trong `C:\Program Files\LTTNexus` thay lúc 16:52:37, app tự bật lại lúc
16:52:41, mục Giới thiệu hiện 1.3.0. **Không có cửa sổ UAC.**

### B2 ✅ Nhật ký truy cập cho người dùng
**Đã xong.** `/may-cua-toi` có bảng **Nhật ký truy cập**: thời gian, máy, IP bên
điều khiển, thời lượng (hoặc nhãn *đang mở*). Chỉ lấy phiên **đã thực sự kết
nối** (`consumed_at`) — vé cấp ra rồi bỏ đó không phải một lần truy cập, đưa vào
chỉ làm nhật ký nhiễu và gây hoảng.

Ba điều chốt bằng test (`test_245`): nhật ký **không rò sang tài khoản khác**,
**còn nguyên sau khi thu hồi máy** (thu hồi cắt quyền, không được xoá bằng
chứng), và khi chưa có phiên nào thì nói rõ là chưa có.

### B3 ✅ Đồng nhất tài khoản app ↔ web (SSO)
**Đã xong.** `POST /nexus-agent/web-login` (ký bằng khoá thiết bị) phát một **vé
một-lần**; app mở `/nexus-sso?ma=…&next=…`, web đổi vé lấy phiên rồi đi tiếp.
Nút *Nạp credit* trong app dùng đường này.

**Không thêm bảng nào:** vé chính là một hàng `sessions` tuổi thọ 90 giây. Không
phải để tiết kiệm một bảng, mà vì vé và phiên có cùng vòng đời và cùng cách thu
hồi — dựng bảng thứ hai nghĩa là có hai chỗ phải nhớ dọn, và một trong hai sẽ bị
quên.

Bốn hàng rào, mỗi cái một test (`test_250`, 12 test):

| Rào | Vì sao |
|---|---|
| Vé sống **90 giây** | Nó đi qua thanh địa chỉ nên nằm lại trong lịch sử trình duyệt |
| **Dùng một lần** — đổi xong xoá vé, cấp phiên MỚI | Thứ còn trong lịch sử phải là token đã chết, không phải cookie đang sống |
| **Từ chối cookie phiên thường** | Không kiểm thì đây thành "đưa cookie qua URL cũng đăng nhập được" |
| `next` qua `safe_next` | Open-redirect gắn sẵn phiên đăng nhập là món quà cho kẻ lừa đảo |

Còn nợ: trang tài khoản trên web chưa hiện máy + thuê bao (đã có ở
`/may-cua-toi`, chỉ thiếu liên kết chéo).

### B4 ✅ Trang giới thiệu LTT Nexus trên web
Xong cùng A7 — `server/templates/nexus_gioi_thieu.html`. Còn thiếu **ảnh chụp màn
hình** (chưa có bộ ảnh sản phẩm); mọi phần chữ đã đủ.

---

## C. HẠ TẦNG — còn nợ từ audit trước

| # | Việc | Vì sao gấp |
|---|---|---|
| C1 | Dời relay khỏi **Windows Server 2016 Eval** | Hết hạn **15/12/2026** → máy tự tắt mỗi giờ, sập cả mạng VM |
| C2 | Thêm relay thứ hai | Một relay = một điểm chết |
| C3 | Bật `LTT_NEXUS_RELAY_HOST` | Cảnh báo relay đã deploy nhưng **chưa chạy** vì thiếu biến này |
| C4 | Đổi mật khẩu relay + đóng RDP 3389 | Mật khẩu đã lộ (tài liệu của chính dự án ghi) |

---

## Còn lại sau vòng 2026-08-22

**Toàn bộ mục A và B đã xong.** Còn:

* **C1–C4** hạ tầng, xem bảng trên
* ảnh chụp sản phẩm cho trang giới thiệu
* macOS `.dmg` chưa build; iOS chờ tài khoản Apple Developer

---

## Thứ tự đề xuất (bản gốc, giữ để đối chiếu)

1. **A3 + A4 + A5 + A6** — gom một vòng đổi thương hiệu, build một lần. Rẻ, và
   là thứ khách nhìn thấy đầu tiên.
2. **B1 installer + tự cập nhật** — có nó thì mọi bản vá sau này tới được người
   dùng mà không cần hướng dẫn.
3. **A7 + B4** — dọn `/nexus`, dựng trang giới thiệu thật.
4. **B2 nhật ký** rồi **B3 SSO**.
5. **C1–C4** hạ tầng, làm trước tháng 12.
