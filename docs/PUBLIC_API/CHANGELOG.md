# Public API — nhật ký thay đổi

Ghi **thay đổi mà một tích hợp có thể cảm nhận được**, không phải mọi commit.
Ai muốn biết code đổi gì thì đọc git; trang này trả lời một câu khác: *"tôi có
phải sửa gì không, và khi nào?"*

Mỗi mục nói ba điều: **cái gì đổi**, **có phá vỡ tương thích không**, và **phải
làm gì**. Mục nào không trả lời được cả ba thì chưa đáng viết ra.

Bề mặt công khai được đóng băng trong `CONTRACT_BASELINE.json` và
`tools/check_api_compat.py` chạy trong gate. Một thay đổi phá vỡ tương thích
**không thể** lên tàu mà không có người ghi lại nó ở đây và chạy `--accept` —
lần ghi lại đó hiện ra trong diff.

## Phân loại

| Nhãn | Nghĩa |
|---|---|
| **BREAKING** | Tích hợp đang chạy sẽ hỏng. Chỉ được phép kèm phiên bản mới hoặc lịch ngừng hỗ trợ đã công bố. |
| **ADDED** | Thứ mới. Client không hỏi tới thì không thấy. |
| **DEPRECATED** | Vẫn chạy, đã có ngày kết thúc. Header `Deprecation` + `Sunset` (RFC 8594) xuất hiện trên phản hồi. |
| **FIXED** | Hành vi đã sai so với tài liệu, nay đúng. |

---

## v1 — chưa phát hành ra ngoài

Toàn bộ bề mặt `v1` được xây trong Public API V2 + Extension Pack và **chưa mở
cho khách bên ngoài**, nên không có mục BREAKING nào ở đây: chưa có tích hợp nào
để phá. Danh sách dưới đây là những gì `v1` **hứa** kể từ khi đóng băng.

### ADDED — 2026-08-15 (EXT-17)

- `CONTRACT_BASELINE.json` + bước gate `hop dong API`. Từ nay mọi thay đổi hợp
  đồng phải đi qua đây.
- Payload webhook có `payload_version` (bắt đầu từ `1`) và danh sách trường được
  khai tường minh. Trong một phiên bản, trường có thể **thêm** nhưng không được
  bỏ hay đổi tên.
- Trang trạng thái công khai `/status/api`, nhóm theo **năng lực** chứ không
  theo hạ tầng.

### ADDED — 2026-08-15 (EXT-15)

- Báo giá và job mang `pricing_version`. Giá vẫn do công thức của app tính;
  nhãn ghi lại chế độ giá đang có hiệu lực để đối soát về sau.
- `GET /api/v1/quotes` trả thêm trường `pricing_version`.

### FIXED — 2026-08-15 (EXT-15)

- Job giữ **đúng** số credit đã báo giá. Trước đó khoản giữ được tính lại từ
  công thức app và **bỏ qua sàn/trần đã công bố**, nên khách có thể được báo một
  số rồi bị trừ một số khác.

### ADDED — 2026-08-14 (EXT-12)

- Chế độ **test**: khoá tiền tố `ltt_tk`, chạy hết chuỗi thật nhưng không gọi
  nhà cung cấp và **không chạm sổ credit**.
- Mọi job và mọi payload webhook mang trường `mode` (`live` | `test`).
- `GET /api/v1/me` trả thêm `mode`.

### ADDED — 2026-08-14 (EXT-09 … EXT-11)

- Nhật ký request cho khách, console webhook (gửi lại, xoay secret, test), ngân
  sách + cảnh báo.

### ADDED — 2026-08-13 (EXT-02 … EXT-08)

- Bảng mã lỗi ổn định kèm ngữ nghĩa thử lại; `execution_mode` công bố trên mọi
  operation; project cho khoá; catalog model/tool; playground.

---

## Cách một thay đổi phá vỡ tương thích được phép xảy ra

1. Đặt cho nó một **phiên bản mới** (`/api/v2`), **hoặc** công bố lịch ngừng hỗ
   trợ trên bề mặt cũ (`deprecated_on` + `sunset_on` trong
   `server/api/inventory.py` — hai header sẽ tự xuất hiện).
2. Viết một mục **BREAKING** ở đây, kèm việc khách phải làm.
3. Cập nhật `docs/PUBLIC_API/MIGRATION.md`.
4. Chạy `python tools/check_api_compat.py --accept`.

Bỏ bước nào cũng được — gate sẽ chặn ở bước 4, và đó là chủ ý.
