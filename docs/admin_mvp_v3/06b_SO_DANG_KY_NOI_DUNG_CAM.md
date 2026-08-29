# 06b — Sổ đăng ký nội dung cấm (Forbidden Content Register)

Tài liệu này là **dữ liệu**, không phải văn xuôi. `tests/test_317_admin_nav_contract.py`
đọc bảng §2 và grep template Admin. Thêm/bớt dòng ở đây là thêm/bớt phép kiểm.

## 1. Vì sao nó tồn tại

Bộ prompt cấm "fake metric" bằng lời, ở 21 chỗ, nhưng **không có cơ chế cưỡng
chế nào**. Và thứ dễ lọt nhất trong bộ ảnh **không trông giống metric**: nó là
cột `Gói dịch vụ: Starter / Pro / Business` xuất hiện ở ba trang, cho một nền
tảng bán **credit** chứ không bán thuê bao (`01` §3, `02` F7).

Một dòng văn xuôi "đừng bịa dữ liệu" không chặn được điều đó. Một phép kiểm thì có.

Khuôn tham chiếu: `test_212` đọc `APP_API_COVERAGE_FINAL.md` như dữ liệu và so
với registry cả hai chiều.

## 2. Bảng cấm

**Cột `Kiểm`:** `AUTO` = test grep mẫu trong template Admin · `MẮT` = quá mơ hồ
để grep, người rà ở cổng D1.
**Cột `Mẫu`:** chuỗi con, so khớp **không phân biệt hoa thường**.

| Mẫu | Kiểm | Loại | Vì sao không có authority | Trang dễ mắc |
|---|---|---|---|---|
| `Gói dịch vụ` | AUTO | thuê bao | Nền tảng bán **credit**, không bán bậc thuê bao. `PaymentOrder.package_id` là gói **nạp** (`models.py:753`) | P2 P3 P5 |
| `Gia hạn` | AUTO | thuê bao | Không có chu kỳ thuê bao để gia hạn | P3 |
| `còn * ngày` | MẮT | thuê bao | như trên | P3 |
| Starter / Pro / Business là **bậc thuê bao** | MẮT | thuê bao | Được phép dùng các từ này làm **tên gói nạp** nếu `CreditPackage` thật có tên đó; cấm dùng làm bậc dịch vụ | P2 P3 P5 |
| `KYC` | AUTO | hồ sơ khách | Không có trường KYC ở `User` | P3 |
| `Ngày sinh` | AUTO | hồ sơ khách | Không có trường | P3 |
| `Số điện thoại` | AUTO | hồ sơ khách | Không có trường | P3 |
| `Quốc gia` | AUTO | hồ sơ khách | Không có trường | P3 |
| `Địa chỉ` | AUTO | hồ sơ khách | Không có trường | P3 |
| `Ghi chú hỗ trợ` | AUTO | hỗ trợ | Không có bảng ghi chú/ticket | P3 |
| `ticket` | AUTO | hỗ trợ | Không có hệ ticket | P1 P2 P3 |
| `VNPay` | AUTO | thanh toán | Cổng duy nhất là **PayOS** (`billing.py`) | P4 P5 |
| `MoMo` | AUTO | thanh toán | như trên | P4 P5 |
| `Thẻ quốc tế` | AUTO | thanh toán | như trên | P4 P5 |
| `Đối soát` | AUTO | thanh toán | Không có luồng đối soát ngân hàng | P4 |
| `Sức khỏe tài chính` | AUTO | tài chính | Không có chỉ số nào như vậy | P4 |
| `Anomal` | AUTO | tài chính/API | Không có phát hiện bất thường | P1 P4 P6 |
| `uptime` | AUTO | observability | Không đo uptime ở đâu cả | P1 P6 P7 P10 |
| `SLA` | AUTO | observability | Không có cam kết SLA nào | P6 P7 P10 |
| `P95` | AUTO | observability | Không đo latency phân vị | P6 P10 |
| `Độ tin cậy hệ thống` | AUTO | observability | Không tồn tại | P6 |
| `Queue depth` · `Delayed Jobs` | AUTO | observability | Không có nguồn | P10 |
| `Redis` | AUTO | observability | Không phải thành phần của nền tảng | P10 |
| `Object Storage` · `S3 bucket` | MẮT | observability | Có R2, nhưng **không** có trạng thái/health để hiện | P10 |
| `Worker */ *` (dạng "32 / 32") | MẮT | observability | Số worker theo `LTT_WORKER_POOLS`, không có bộ đếm sống | P10 |
| `Bảo trì định kỳ` · `lịch bảo trì` | AUTO | observability | Không có lịch bảo trì công bố | P10 |
| **Tổng số request** / `Tổng yêu cầu` | AUTO | API | 🔴 `admin_console.py:143–145`: **chỉ ghi log lỗi và call non-GET**. Không tồn tại tổng số request | P1 P6 |
| `Error rate` · `Tỷ lệ lỗi` (dạng %) | MẮT | API | Không có mẫu số ⇒ không tính được | P1 P6 |
| `Rate Limit Shield` | AUTO | API | Không có tính năng | P6 |
| `IP Reputation` | AUTO | API | Không có tính năng | P6 P7 |
| `Schema Strict Mode` | AUTO | API | Không có tính năng | P6 |
| `DDoS` | AUTO | API | Không có tính năng | P7 |
| `IP Whitelist` | AUTO | API | Không có tính năng ở tầng admin | P7 |
| `payload` (dạng nút "Xem payload") | MẮT | API | 🔴 **Không lưu raw request/response.** Cấm thêm lưu trữ để chiều mockup | P8 |
| `Azure OpenAI` | AUTO | provider | Registry thật: gemini · apiai · cheapkeyai · byteplus · plenx (`providers.py:66`) | P9 |
| `Anthropic` | AUTO | provider | Không có trong registry | P9 |
| `Routing *%` | MẮT | provider | Không đo tỉ lệ định tuyến | P9 |
| `Đồng bộ provider` | AUTO | provider | Không có luồng đồng bộ | P9 |
| `support@lttstudios.com` | AUTO | cam kết | Không có hộp thư hỗ trợ công bố cho admin | mọi trang |
| `docs.lttstudios.com` | AUTO | cam kết | Tên miền không tồn tại | mọi trang |
| `Hỗ trợ 24/7` | AUTO | cam kết | Không có cam kết | P7 |
| `NVMe` | AUTO | cam kết | Marketing, không phải dữ liệu vận hành | P7 |
| Chip môi trường `Production` | MẮT | vỏ | Không có khái niệm nhiều môi trường trong nền tảng | vỏ |
| Chuông thông báo **có số đếm** | MẮT | vỏ | Không có hàng đợi thông báo cho admin | vỏ |
| Ảnh đại diện khách hàng | MẮT | vỏ | `User` không có trường avatar | P2 P3 P5 |
| `so với hôm qua` · `so với tháng qua` | AUTO | xu hướng | Không read-model nào trả về số của kỳ trước | P1 P2 P4 P6 |

## 3. Luật áp dụng

**R1.** Mẫu `AUTO` bị cấm trong **template Admin** (`server/templates/admin*/**`)
và trong chuỗi HTML do `server/admin.py` / `server/admin_api.py` sinh ra.
Không cấm trong tài liệu, bình luận mã, hay tên biến.

**R2.** Mẫu `MẮT` được rà ở cổng D1, ghi kết quả vào `18_SAFETY_GATE.md`.

**R3.** Muốn dùng một mẫu bị cấm thì **không** sửa test — phải chỉ ra read-model
thật cung cấp nó, ghi vào `05` Phần I, rồi xoá dòng ở bảng §2 kèm lý do. Đổi
chiều nào cũng phải đi qua tài liệu trước.

**R4.** Một chỉ số có authority nhưng **đọc không được lúc chạy** thì ô hiển thị
"không lấy được", **không** hiện `0`. Đây là luật của `05` Phần IV, nhắc lại ở đây
vì nó cũng là một dạng nói dối bằng số.
