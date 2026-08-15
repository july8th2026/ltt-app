# Runbook — API đang có vấn đề, làm gì

Trang quản trị cho **thấy** mọi thứ; file này nói **phải làm gì** khi thấy. Một
bảng điều khiển trả lời được mọi câu hỏi riêng lẻ mà không dẫn tới hành động thì
sẽ không được dùng vào đúng ngày cần tới nó.

Mỗi mục theo cùng một khuôn: **dấu hiệu → nhìn ở đâu → nguyên nhân thường gặp →
làm gì → biết là đã hết chưa**.

Mọi mục ở đây đều là chế độ hỏng **có thật** của hệ thống này, không phải danh
sách chung chung: chúng đến từ bản audit 2026-08-15 và từ những lỗi đã thực sự
xảy ra.

---

## 1. Webhook dồn đống, khách kêu không nhận được callback

**Nhìn ở đâu.** `/admin/api-tong-quan` → ô "Webhook chết" và "Tiến trình đã
gộp"; `/admin/api-tong-quan` cũng hiện **ai đang giữ lease bảo trì**.

**Nguyên nhân thường gặp, theo thứ tự nên nghi.**

1. **Không ai giữ lease bảo trì.** Ô đó ghi "chưa ai giữ" nghĩa là **không tiến
   trình worker nào đang chạy việc nền** — webhook không được gửi, dữ liệu hết
   hạn không được dọn, cảnh báo không được quét. Đây là kiểu hỏng im lặng nhất
   của hệ thống: không job nào lỗi, không trang nào đỏ.
2. Bên nhận của khách đang chết → delivery chuyển `dead` sau 6 lần thử (30 giây
   → 6 giờ). Đây là hành vi **đúng**, không phải sự cố của ta.
3. Worker bận job dài. Không còn là nguyên nhân từ khi việc nền chạy luồng
   riêng, nhưng nếu thấy lại thì đó là dấu hiệu luồng bảo trì đã chết.

**Làm gì.**

- Lease trống: xem dịch vụ `LTTStudioWorker` còn chạy không. Lease tự hết hạn
  sau 2 phút, nên nếu vẫn trống sau 3 phút thì **không có worker nào sống**.
- `dead` nhiều mà chỉ của một khách: đó là endpoint của họ. Trang webhook có
  đường gửi lại sau khi họ sửa xong.
- `dead` rải khắp nhiều khách cùng lúc: nghi mạng ra ngoài của máy chủ, không
  phải bên nhận.

**Biết là đã hết chưa.** Ô "Webhook chết" ngừng tăng, và lease bảo trì có tên
một tiến trình.

---

## 2. Hàng đợi job dài ra, khách chờ lâu

**Nhìn ở đâu.** `/admin/api-tong-quan` → "Chờ vào hàng đợi" (`queue_pickup_ms`)
và "Job xong / Job hỏng".

**Nguyên nhân thường gặp.**

1. **Đội hình worker sai loại.** Nếu `LTT_WORKER_POOLS` chưa đặt, số worker bằng
   số GPU — trong khi 4/5 công cụ đang mở chỉ ngồi chờ mạng nhà cung cấp và
   không đụng card. Chúng xếp hàng sau nhau không vì lý do gì.
2. Nhà cung cấp chậm hoặc đang chặn nhịp → xem "Job hỏng" và mã lỗi.
3. Một khách đẩy nhiều việc. **Không** phải nguyên nhân thường gặp: trần đồng
   thời chặn ngay lúc nhận và tính cả job đang chờ, nên một tài khoản không thể
   làm ngập hàng đợi.

**Làm gì.** Đặt `LTT_WORKER_POOLS` trong `secrets\app.env`, ví dụ:

```
LTT_WORKER_POOLS=api:8, gpu+ffmpeg:2
```

rồi khởi động lại `LTTStudioWorker`. Pool `gpu` **vẫn nhặt được** job chỉ cần
`api`, nên nó không nằm không khi hàng đợi toàn việc chờ mạng.

**Biết là đã hết chưa.** "Chờ vào hàng đợi" giảm; ô "Tiến trình đã gộp" hiện đủ
số worker mong đợi.

---

## 3. Nhà cung cấp trả 429 hàng loạt

**Nhìn ở đâu.** `/admin/api-tong-quan` → "Job hỏng"; `/admin/api-job` xem mã lỗi.

**Làm gì.** Job hỏng vì provider **đã tự hoàn tiền** — khách không mất credit, và
host của nhà cung cấp không lọt ra ngoài. Việc cần làm là ở phía pool khoá:
`/admin` → APIKEYS, xem còn khoá nào dùng được cho category đó không.

Nếu hết khoá dùng được, `capacity.check` sẽ **từ chối ngay lúc nhận** thay vì
nhận rồi hỏng — nghĩa là khách nhận lỗi rõ ràng thay vì chờ một job chắc chắn
thất bại. Đó là hành vi đúng; đừng "sửa" bằng cách tắt kiểm tra.

**Biết là đã hết chưa.** Ô "Hết chỗ tài nguyên" về 0 và job mới chạy được.

---

## 4. Biên lợi nhuận âm

**Nhìn ở đâu.** `/admin/api-margin`.

**Nguyên nhân.** Giá nhà cung cấp đổi, hoặc bảng giá của ta đặt sai cho một
công cụ.

**Làm gì.** `/admin/api-gia` → tạo **phiên bản giá mới**, không sửa đè bản đang
chạy. Báo giá đã phát cho khách vẫn được tôn trọng theo giá cũ cho tới khi hết
hạn — đó là lý do bảng giá có phiên bản.

**Biết là đã hết chưa.** Margin của công cụ đó dương trở lại ở cửa sổ 24 giờ kế.

---

## 5. Lease bảo trì đổi chủ liên tục

**Dấu hiệu.** Ô "bảo trì" trên trang tổng quan đổi tên mỗi lần tải lại.

**Nghĩa là gì.** Tiến trình đang giữ lease **chết rồi được thay** liên tục.
Thường là: một job vượt trần thời gian chạy (kết thúc tiến trình theo thiết
kế), hoặc một thư viện C sập, hoặc thiếu bộ nhớ.

**Làm gì.** `logs\worker-err.log` tìm dòng `vuot tran` — nếu có, đó là job treo
và tiến trình bị kết thúc **đúng ý đồ**; tìm job đó ở `/admin/api-job` để biết
công cụ nào. Nếu không có dòng đó thì là sập thật, đọc traceback.

**Biết là đã hết chưa.** Tên trong ô "bảo trì" đứng yên qua vài lần tải lại.

---

## 6. Số "Tiến trình web" khác 1

**Nghĩa là gì.** Bộ đếm hạn mức nhịp (RPM) sống **trong tiến trình**. Hai tiến
trình web nghĩa là mỗi khách được **gấp đôi** hạn mức, im lặng — không có lỗi
nào, chỉ là hàng rào rộng gấp đôi ý định.

**Làm gì.** Chỉ chạy một dịch vụ `LTTStudioWeb`. Nếu thật sự cần nhiều tiến
trình web, bộ đếm nhịp phải chuyển xuống CSDL trước — đó là lúc cân nhắc thêm
một dịch vụ, chứ không phải trước đó.

---

## 7. Dấu hiệu bất thường trên trang bảo mật

`/admin/api-bao-mat` → bảng "Dấu hiệu bất thường".

| Dấu hiệu | Nghĩa | Làm gì |
|---|---|---|
| **Khoá đã thu hồi vẫn bị gọi** | Thứ đang giữ khoá **không phải** hệ thống khách vừa cập nhật | Liên hệ khách. Nếu nhiều địa chỉ khác nhau → coi như credential đã ra ngoài |
| **Chi tiêu vọt** | Có thể là chiến dịch thật, có thể là khoá bị lộ | Xem `/admin/api-tai-khoan` của họ; **hỏi trước khi chặn** |
| **Thiếu quyền** | Rất nhiều lỗi trên **một** route = khách cấu hình thiếu scope. Rải khắp nhiều route = đang dò | Cấu hình sai thì báo khách; dò thì cân nhắc kill switch theo khoá |

**Cố ý không tự chặn.** Một hệ tự khoá dựa trên suy đoán sẽ chặn nhầm khách thật
vào đúng ngày họ chạy chiến dịch lớn, và mất một khách vì nghi oan đắt hơn xử lý
muộn vài giờ.

---

## 8. Cần dừng khẩn cấp

Theo thứ tự **từ hẹp tới rộng** — luôn dùng cái hẹp nhất còn đủ:

| Phạm vi | Cách | Ảnh hưởng |
|---|---|---|
| Một khoá | `/admin/api-kill-switch` | Chỉ khoá đó |
| Một khách | như trên, phạm vi tài khoản | Mọi khoá của họ |
| Một công cụ | bỏ khỏi `LTT_PUBLIC_API_TOOLS` | Mọi khách, công cụ đó |
| Cả khu API | `LTT_PUBLIC_API=0` | Web thường **không đổi gì** — có test chốt |

Kill switch **bắt buộc ghi lý do**. Dòng đó được đọc lại vài tháng sau bởi người
không có mặt hôm nay.
