# Kích hoạt plugin WordPress — quy trình cho máy làm web

> Lập 2026-08-06. Dùng khi thực hiện `DEFERRED-WP-001` (Q60).
>
> **Nguồn plugin là repo này**, không phải file copy tay. Máy làm web `git pull`
> là có bản mới nhất — chép tay sẽ lệch nguồn ngay lần sửa kế tiếp.

---

## Prompt để dán cho agent trên máy làm web

Sao nguyên khối dưới đây:

```text
Kích hoạt plugin WordPress cho lttstudios.com theo DEFERRED-WP-001.

NGUỒN CHÂN LÝ
- Plugin: deploy/wordpress/lttstudios-integration/ trong repo LTTSTUDIOSAPP
  (git@github.com:giaitritruyenthongltt-spec/LTTSTUDIOSAPP.git, nhánh master).
- Đọc deploy/wordpress/README.md trước khi làm.
- KHÔNG sửa plugin trên host. Sửa trong repo → commit → pull → deploy lại.
- KHÔNG upload docs/lttstudios-website/ đè lên public_html.

BASELINE ĐÃ ĐO 2026-08-06 (trước khi kích hoạt), để có cái so:
- python tools/audit_public_web.py  →  30 FAIL / 0 PASS
- 29 FAIL là alias .html cũ trả 404 (/products.html, /support.html,
  /contact.html, /download.html, /changelog.html, /architecture.html,
  /transparency.html, /compliance/*.html, /legal/*.html và bản /vi/* của chúng)
- 1 FAIL là: "content home: WordPress login still exposed"

VIỆC CẦN LÀM, theo đúng thứ tự

1. SAO LƯU TRƯỚC KHI ĐỘNG VÀO GÌ
   - Sao lưu file WordPress + database qua công cụ của host.
   - Ghi lại danh sách plugin đang bật (chụp màn hình là đủ) để lùi được.
   - Không có bản sao lưu thì DỪNG. Không làm bước 2.

2. ĐÓNG GÓI VÀ CÀI
   - git pull để chắc chắn có bản mới nhất.
   - Nén thư mục deploy/wordpress/lttstudios-integration/ thành ZIP.
     Cấu trúc bên trong ZIP phải là: lttstudios-integration/lttstudios-integration.php
     (nén chính THƯ MỤC, không nén nội dung bên trong nó).
   - wp-admin → Plugins → Add New → Upload Plugin → chọn ZIP → Install → Activate.
   - Hoặc chép thẳng vào wp-content/mu-plugins/ nếu muốn nó luôn bật.

3. KIỂM BẰNG SỐ, KHÔNG KIỂM BẰNG CẢM GIÁC
   - Chạy: python tools/audit_public_web.py
   - ĐIỀU KIỆN NGHIỆM THU: 0 FAIL. Còn dù chỉ 1 FAIL thì chưa xong.
   - So với baseline 30 FAIL ở trên để biết đã sửa được bao nhiêu.

4. KIỂM BẰNG TRÌNH DUYỆT THẬT (test xanh không chứng minh trang hiển thị đúng)
   - Desktop 1366x900 và mobile 390x844.
   - Với mỗi kích thước: không tràn ngang, console 0 lỗi, không request hỏng.
   - Bấm thử CTA sang app: phải tới https://app.lttstudios.com và đăng nhập được.
   - Kiểm vài alias cũ: /about.html, /products.html, /legal/privacy.html
     → phải chuyển hướng đúng, không phải 404.

5. HAI ĐƯỜNG OAUTH CALLBACK PHẢI KHÔNG ĐỔI
   - Plugin CỐ Ý không đụng tới hai file .html callback của Facebook/TikTok.
   - Mở đúng hai URL đó, xác nhận nội dung y như trước khi cài.
   - Đây là chỗ dễ hỏng nhất và hỏng thì gãy đăng nhập mạng xã hội của khách.

CÁCH LÙI LẠI
- Tắt rồi xoá ĐÚNG plugin này. Không cần khôi phục database.
- Plugin không tạo bảng, không tạo option, không đụng bài viết hay người dùng.
- Lùi xong chạy lại audit_public_web.py, kỳ vọng quay về 30 FAIL.

TUYỆT ĐỐI KHÔNG
- Không đặt mật khẩu/Application Password của WordPress vào repo hay vào log chat.
- Không sửa file plugin trực tiếp trên host.
- Không coi "đã kích hoạt" là "đã xong" khi audit chưa về 0 FAIL.

BÁO CÁO LẠI
- Số FAIL trước và sau (con số thật, không phải ước lượng).
- Kết quả kiểm trình duyệt ở cả hai kích thước.
- Xác nhận hai OAuth callback không đổi.
- Nếu có bước nào bỏ qua, nói rõ bỏ qua bước nào và vì sao.
```

---

## Ghi chú cho người đọc (không thuộc prompt)

**Vì sao lấy plugin từ repo chứ không chép tay:** chép tay tạo ra hai bản
plugin — bản trên host và bản trong repo — và chúng sẽ lệch nhau ngay lần sửa
kế tiếp. Lúc đó không ai biết bản nào đúng. Repo là nguồn chân lý; host chỉ là
nơi chạy.

**Plugin làm gì:** chuyển hướng 29 đường `.html` cũ sang đường WordPress mới và
thêm CTA sang app. Không tạo bảng, không tạo option, không đụng dữ liệu — nên
gỡ ra là sạch.

**Vì sao hai file OAuth callback bị chừa ra:** đó là đường Facebook và TikTok
gọi ngược về sau khi người dùng cho phép. Đổi chúng là gãy đăng nhập mạng xã
hội, và lỗi chỉ lộ ra khi có khách thật bấm nút đó.
