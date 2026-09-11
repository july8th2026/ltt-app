# Pha 32 — UX polish + mobile + accessibility

**Trạng thái: MỘT PHẦN — kiểm xong 4 trạng thái trang, sửa lỗ nặng nhất; một lỗ
còn mở có lý do.** Ngày 11/09/2026.

Đề bài: *bàn phím · ARIA · responsive · trạng thái rỗng/đang tải/lỗi · xác nhận
huỷ · không tràn ngang · kiểm tra accessibility.*

## 1. Kiểm trước khi sửa — trình duyệt thật, bốn trạng thái, hai cỡ

Trang dựng bằng máy chủ thật (TestClient + phiên fixture): *chính · rỗng*, *chính ·
có lần chạy*, *chính · lỗi 400 ở cửa*, *chi tiết · đang chạy*; mỗi trang ở 1280 px
và 375 px. Bộ kiểm chạy trong trang:

| mục | kết quả |
|---|---|
| điều khiển thiếu tên truy cập (label / aria-label / title) | **0** ở cả 8 lượt |
| ảnh thiếu `alt` · id trùng | 0 · 0 |
| tràn ngang | không (scrollWidth nhỏ hơn cửa sổ 15 px ở mọi lượt) |
| `lang` | `vi` |
| thứ tự tiêu đề | H1 → H2 → H3 (→ H4 dưới *Thời lượng*), không nhảy bậc |
| vòng Tab | header → video → preset → nút nguồn giọng…; mọi phần tử có viền focus 1,6–2,4 px |
| lỗi ở cửa | `role="alert"` |
| danh sách rỗng | *"Bạn chưa có lần chạy nào."* |
| gửi hai lần | nút *Bắt đầu* bị khoá + đổi chữ *"Đang gửi video…"* (`tai_len.js`) |
| đích nhỏ < 24 px | 11 — đều là checkbox/radio **nằm trong `<label>`**; cả nhãn là đích bấm |
| **huỷ** | 🔴 **một cú bấm**, không xác nhận |
| **tiến độ cho trình đọc màn hình** | ⚠️ trang chi tiết có **0** vùng `aria-live` |

## 2. 🔴 Sửa: huỷ hai bước

`huy_run` quyết toán ngay; `RUN_CANCELLED` là trạng thái cuối và `thu_lai` từ chối
lần chạy đã kết thúc. Một cú bấm trượt tay là mất một lần chạy đã trả tiền, đã đi
qua tách nguồn và chép lời.

Nay: `<details>` — bấm *"Huỷ lần chạy"* mở câu hậu quả (*"dừng hẳn · credit chưa
dùng được hoàn lại · muốn làm lại phải tạo lần chạy mới"*) và nút *"Xác nhận huỷ"*
(`btn danger`). Không JS; bàn phím Enter/Space trên `summary`.

⚠️ **Cái bẫy của chính cách sửa**: mảnh tiến độ được htmx hỏi lại 3 giây một lần
bằng `outerHTML`. Khung xác nhận đang mở sẽ **tự đóng** giữa lúc khách đọc. Sửa
bằng `hx-preserve` (htmx 2.0.3) trên một id cố định.

```
375 px, trình duyệt thật:
  nút xác nhận ẩn lúc đầu                       ✔
  focus summary + Enter -> mở                   ✔
  bước 1 gửi POST?                              0 lần
  chờ 7 s (2 lượt hỏi lại) -> vẫn mở            ✔   1 khung, không nhân đôi
  bấm "Xác nhận huỷ" -> POST .../huy            1 lần
ĐỐI CHỨNG (bản sao ngoài kho, bỏ hx-preserve):
  mở -> chờ 7 s (2 lượt) -> ĐÃ ĐÓNG
```

`test_481` (4 bài) chốt hình dạng trên trang máy chủ dựng thật; ba lần tiêm, ba lần
đỏ.

## 3. Còn mở — và vì sao chưa làm

**Thông báo tiến độ cho trình đọc màn hình.** `role="progressbar"` + `aria-valuenow`
có, nhưng không vùng `aria-live` nào, nên người dùng trình đọc màn hình phải tự đi
tìm. Cách đúng là một vùng live **đứng yên** ngoài mảnh bị thay, nhận tên bước qua
`hx-swap-oob="innerHTML"`. Chưa làm vì phép đo duy nhất có nghĩa là **một trình đọc
màn hình thật** (NVDA/JAWS): thay nội dung bằng chính nó mỗi 3 giây có thể bị đọc
lặp hoặc im — cả hai đều tệ hơn hiện trạng, và máy này không có công cụ đo nó.
