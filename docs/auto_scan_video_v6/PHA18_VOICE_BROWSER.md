# Pha 18 — Voice Browser UX

**Trạng thái: XONG phần giao diện.** Ngày 11/09/2026.

Đề bài: *tìm/lọc giới–vùng–phong cách · tab My Voices / LTT Voices · nghe thử ·
làm mới/cập nhật sống · trạng thái thiếu mẫu nghe.*

## 0. Đo trước

| đề bài | trước pha 18 |
|---|---|
| lọc giới/vùng/phong cách | **có** — ba ô, nhãn lấy từ `ltt_voice` |
| nghe thử | **có** — nút khoá + câu *"đang chuẩn bị bản nghe thử"* khi không có tệp |
| tìm theo tên | không |
| tách *giọng của tôi* / *giọng mẫu* | không — trộn trong một danh sách |
| làm mới / cập nhật sống | không — giọng vừa nhân bản chỉ hiện sau khi **tải lại trang**, tức mất video đã chọn và mọi ô đã chỉnh |
| thiếu mẫu nghe | chỉ biết **sau khi** chọn rồi nhìn nút |
| danh sách lọc ra rỗng | 🔴 **lỗi có sẵn** — xem §1 |

## 1. 🔴 Lỗi có sẵn: lọc ra rỗng mà vẫn gửi giọng đã bị ẩn

`locGiong()` chỉ chọn lại khi `conLai > 0`. Khi **không** giọng nào khớp, giọng
đang chọn — đã bị ẩn — vẫn nằm trong `value` và vẫn đi lên máy chủ. Khách lọc
*"Nữ · miền Nam"*, thấy danh sách rỗng, bấm Gửi, và nhận một video đọc bằng giọng
nam họ vừa lọc bỏ. Chính chú thích trong mã đã ghi *"một `<select>` giữ một value
đang hidden vẫn GỬI giá trị đó đi"* — cho nhánh khác.

Sửa: rỗng ⇒ `setCustomValidity(...)` trên ô giọng — trình duyệt **chặn gửi** và
nói lý do; câu ấy cũng hiện ở `#asv-giong-tt` (aria-live).

⛔ **Không** thêm `<option value="">` để biểu diễn trạng thái rỗng: `test_447` cấm ô
giọng có mục rỗng — đó là đường *"Giọng mặc định"* quay lại.

## 2. Làm được gì

* **Hai nguồn**: ba nút *Tất cả · Giọng của tôi (n) · Giọng mẫu LTT (n)* —
  `aria-pressed`, không `name`, nên không đi theo form. Giọng nhân bản của khách
  vẫn **không** bị ba ô nhãn lọc mất (chúng không có nhãn); tab *Giọng mẫu* thì ẩn
  chúng — vì đó là điều khách vừa yêu cầu.
* **Tìm không dấu**: `minh duc` tìm ra *Minh Đức* (`đ` đổi riêng vì NFD không tách).
* **Làm mới**: nút gọi `routes.danh_muc_giong` (đã lọc theo chủ sở hữu ở máy chủ),
  dựng lại danh sách, giữ giọng đang chọn nếu còn. Tự làm mới khi tab được nhìn lại,
  tối đa một lần mỗi 30 giây. Máy chủ trả **rỗng** ⇒ giữ danh sách cũ.
* **Thiếu mẫu nghe** hiện ngay trong danh sách: *"Minh Đức · chưa có mẫu nghe"*.

## 3. Trình duyệt thật (Playwright)

Trang dựng bằng máy chủ thật (TestClient + phiên fixture); tài sản tĩnh thật từ
đĩa; `/giong` trả danh mục thật + **một giọng vừa nhân bản** + một mẫu nghe —
đúng kịch bản khách nhân bản ở LTT VOICE rồi quay lại.

```
nạp trang            20 giọng, đếm (0)/(20), nút nghe khoá + câu giải thích   0 yêu cầu hỏng
tìm "minh duc"       -> ["Minh Đức · chưa có mẫu nghe"]
lọc nam·trung·tin tức -> 0 giọng: form.checkValidity() = false,
                        thông báo "Không có giọng nào khớp bộ lọc — hãy bỏ bớt điều kiện."
bỏ lọc               -> 20 giọng, ô giọng hợp lệ, thông báo xoá
bấm "Làm mới"        -> 1 lần gọi /giong, "Đã cập nhật danh sách: 21 giọng.", đếm (1)/(20)
tab Giọng của tôi    -> ["Giọng của Lan (nhân bản)"], tự chọn nó, aria-pressed [false,true,false]
tab Giọng mẫu        -> 20 giọng, không có giọng nhân bản
chọn mẫu có tệp      -> nút nghe mở
console              0 lỗi · 375 px: không tràn ngang (360/375)
```

## 4. Phép kiểm

`test_480` (9 bài) — phía client là **đọc văn bản** mã nguồn (kho không có bộ chạy
JS); hành vi thật là §3. Bảy lần tiêm, bảy lần đỏ.

⚠️ Lượt đầu, phép kiểm *"không có mục rỗng"* đỏ trên **chính dòng chú thích** giải
thích luật đó. Bộ quét nay bỏ chú thích trước khi quét và khẳng định một mệnh đề
dương (`o.value = g.ma`).

## 5. Còn lại

* Lọc theo **ngôn ngữ giọng** — pha 17, chặn ở `ltt_voice.giong_mau.loc()`.
* `routes.danh_muc_giong?gioi=...` lọc mất giọng nhân bản (không nhãn) trong khi
  client giữ chúng — hai luật cho cùng một câu hỏi. Giao diện hôm nay gọi `/giong`
  **không** tham số nên không chạm; ghi lại để không ai dùng tham số đó cho màn này.
