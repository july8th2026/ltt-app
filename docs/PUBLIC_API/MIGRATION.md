# Ngừng hỗ trợ và chuyển đổi

Trang này trả lời đúng một câu hỏi: **"cái tôi đang dùng còn sống bao lâu nữa,
và thay bằng gì?"**

## Hôm nay: chưa có gì bị ngừng hỗ trợ

Không route, không tool, không mã lỗi nào đang có lịch gỡ. `Deprecation` và
`Sunset` (RFC 8594) **không** xuất hiện trên bất kỳ phản hồi nào.

Nói ra điều này thay vì để trang trống là có lý do: một trang ngừng-hỗ-trợ trống
rỗng có thể nghĩa là "không có gì bị ngừng" hoặc "chưa ai cập nhật trang này", và
hai thứ đó khác nhau rất xa đối với người đang quyết định có nên tích hợp hay
không.

## Cách bạn sẽ biết, trước khi có gì hỏng

Ba kênh, theo thứ tự bạn gặp chúng:

1. **Header trên chính phản hồi của bạn.** Một operation đã có lịch gỡ sẽ trả
   `Deprecation: <ngày>` và `Sunset: <ngày>`. Không cần đăng ký gì; nếu bạn ghi
   log phản hồi thì bạn đã có nó.
2. **`docs/PUBLIC_API/CHANGELOG.md`** — mục **DEPRECATED**, kèm cái thay thế.
3. **Trang này** — bảng dưới đây, khi có mục đầu tiên.

| Cái gì | Ngừng hỗ trợ từ | Ngưng phục vụ | Thay bằng | Phải làm gì |
|---|---|---|---|---|
| *(chưa có)* | | | | |

## Cam kết về khoảng thời gian

Khi có mục đầu tiên, khoảng cách giữa **Ngừng hỗ trợ** và **Ngưng phục vụ** sẽ
được công bố ở đây trước, không phải quyết định sau. Một lịch gỡ chỉ có nghĩa
khi nó được biết trước đủ lâu để sửa.

## Những thứ sẽ **không** đổi trong `v1`

Đây là danh sách những gì đã đóng băng trong `CONTRACT_BASELINE.json` và được
`tools/check_api_compat.py` canh trong gate:

- **Đường dẫn và phương thức** của mọi route đang công bố;
- **Yêu cầu xác thực** của một operation (thêm yêu cầu là phá vỡ tương thích);
- **Hình dạng đầu vào/đầu ra** của mọi tool — đo bằng `contract_hash`;
- **Chế độ chạy** của một operation (client viết cho job id không đọc được câu
  trả lời đồng bộ);
- **Mã lỗi** đã công bố và mã HTTP đi kèm;
- **Loại sự kiện webhook**, phiên bản chữ ký và phiên bản payload.

Thêm route mới, tool mới, mã lỗi mới, sự kiện mới thì **không** nằm trong danh
sách này: một client không hỏi tới chúng thì không thể nhận ra chúng.

## Nếu bạn cần một thứ ở đây đổi

Mở một yêu cầu. Đổi được — nhưng nó sẽ đi kèm một phiên bản mới hoặc một lịch
ngừng hỗ trợ, chứ không phải một bản phát hành lặng lẽ vào một buổi chiều.
