# Pha 5 — nâng cấp GUI theo bot vận hành + `taovideo`

Nguồn: `D:\BOT GEMINI\app\modules\seedance` *(chỉ đọc)* và `apps/taovideo`.

## Nguyên tắc rút từ bot vận hành

Ba thứ, lấy từ chính chú thích trong mã của nó:

1. **Dày đặc thay vì trang trí.** Nó bỏ hero 180px, thay bằng dải mỏng đầy số
   thật — chú thích ghi rõ: tiết kiệm ~125px chiều dọc.
2. **Số thật, và nói rõ là thật.** Huy hiệu `THẬT` phân biệt số đo được với số
   ước. Một con số ước đặt cạnh một con số thật thì cả hai mất giá trị.
3. **Giải thích đẩy vào tooltip**, để bề mặt gọn mà không mất thông tin.

## Làm — xếp theo giá trị thật cho app NÀY

| # | Việc | Vì sao đáng, đo được |
|---|---|---|
| **A** | **Tự làm mới thư viện khi có job chạy** | một video mất **hàng chục phút**; hiện người dùng phải tự bấm. Đây là khác biệt lớn nhất giữa "màn tĩnh" và "studio" |
| **B** | **Nút Huỷ ngay trên thẻ** | nền tảng đã có `POST /jobs/{id}/cancel` — kiểm sở hữu, **hoàn credit**. Không có nút thì người dùng phải vào trang job mới huỷ được |
| **C** | **Công cụ prompt: mở rộng + hoàn tác** | mượn thẳng bot vận hành (`Mở prompt ra bảng lớn`, `Hoàn tác N bước`). Prompt là thứ người dùng sửa nhiều nhất |
| **D** | **Tooltip ⓘ ở tên màn** | mượn `sdv-strip-info`. Giải thích màn làm gì mà không tốn một dòng nào |
| **E** | **Dạng danh sách khác dạng lưới thật sự** | nút đã có, nhưng phải kiểm `.list-view` có đổi gì không — một nút không đổi gì là một nút hỏng |

## KHÔNG làm — và vì sao

| Bỏ | Lý do |
|---|---|
| Xoá hàng loạt | `C2` đã tự xoá sau 3 ngày. Thêm một thao tác **không hoàn tác** để làm sớm việc hệ thống tự làm là đổi rủi ro lấy tiện nghi |
| Bảng thống kê + lịch nhiệt | `tom_tat` đã trả lời 80% câu hỏi ("tôi đã dùng bao nhiêu"). Phần còn lại là một màn riêng, không phải trang trí cho màn này |
| Dịch prompt | cần LLM. `ltt_llm` có, nhưng đó là một dây nối riêng, không thuộc pha giao diện |
| Chip token theo model | ta không mua gói theo model. Không có số thật để hiện ⇒ theo nguyên tắc 2, **không hiện gì** |
| Asset ID của ModelArk | đặc thù nhà cung cấp |
| Chọn model | `A1` đã khoá |

## Cách nghiệm thu

Mỗi mục: soi bằng Playwright thật, và với `A`/`B` thì phải thấy **hiệu ứng ở
CSDL**, không dừng ở màn hình — cùng chuẩn đã dùng cho `seed`/`negative_prompt`.
