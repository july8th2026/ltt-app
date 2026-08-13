# FULL PLATFORM TARGET — trạng thái cuối của API Platform

Đây là **đích**, không phải hiện trạng. Hiện trạng ở
`FULL_PLATFORM_GAP_MATRIX.md`; đường đi ở `FULL_PLATFORM_DEPENDENCY_GRAPH.md`.

Nguyên tắc bao trùm, giữ nguyên từ V2: **một engine**. Mọi thứ dưới đây chạy trên
đúng sổ credit, đúng bảng `jobs`, đúng worker, đúng storage, đúng provider đang
có. Extension thêm **bề mặt và quản trị**, không thêm động cơ.

---

## 1. Người dùng ngoài (developer / hệ thống bên thứ ba)

Vào `app.lttstudios.com` → khu **API**:

| Trang | Trả lời câu hỏi gì |
|---|---|
| Overview | Tôi đang dùng bao nhiêu, còn bao nhiêu, có gì hỏng không |
| Projects / Applications | Tách tích hợp A với tích hợp B, mỗi cái có khoá và hạn mức riêng |
| API Keys / Service Accounts | Tạo, xoay, thu hồi, giới hạn IP, đặt hạn dùng |
| Apps, Models & Tools | Có những gì bán, tham số nào, giá bao nhiêu, chạy kiểu gì |
| Playground | Thử một lời gọi thật, thấy giá trước khi bấm |
| Request Logs | Một request của tôi đã đi qua những gì, hỏng ở đâu |
| Jobs | Việc đang chạy, tiến độ, kết quả, huỷ |
| Usage / Budgets / Credits | Tiêu theo tool/khoá/ngày; đặt ngân sách và cảnh báo |
| Webhooks | Đăng ký sự kiện, xem lần giao, gửi lại |
| Documentation & SDK | Quickstart, biến môi trường, ví dụ cURL/Python/TS, OpenAPI, Postman |
| Notifications | Sắp hết credit, khoá sắp hết hạn, webhook chết, vượt ngân sách |
| Settings / Security | Xoay khoá, IP, xoá dữ liệu, xuất dữ liệu |
| OAuth Apps *(nếu bật)* | Ứng dụng của tôi xin quyền thay mặt người dùng LTT |

Máy gọi máy làm được trọn vòng: **tạo credential → khám phá schema → upload →
báo giá → gửi job idempotent → theo dõi bằng poll hoặc webhook → tải artifact →
đọc usage và log → hiểu lỗi và biết có nên thử lại không.**

## 2. Bốn chế độ chạy, khai báo tường minh

| Mode | Dùng cho | Bắt buộc kèm |
|---|---|---|
| `ASYNC_JOB` | mặc định: AI, ảnh, video, GPU, FFmpeg, mọi thứ tính tiền | quote → hold → job → settle |
| `SYNC` | chỉ thao tác rẻ, ngắn, có biên trên | không được chiếm worker |
| `STREAM` | chỉ khi cần kết quả tăng dần (chat) | ngữ nghĩa credit/cancel/retry phải thiết kế trước |
| `BATCH` | gói nhiều lời gọi con | không phá idempotency/credit |
| `NOT_PUBLIC` | năng lực nội bộ | không có đường tắt nào ra ngoài |

Không ép mọi thứ vào một mode. Không biến việc dài thành đồng bộ cho SDK dễ viết.
Không thêm WebSocket khi SSE/HTTP đủ.

## 3. Quản trị (admin)

Admin → **API Management**: Overview · Users/Projects · Keys/Service
Accounts/OAuth Clients · Apps/Models/Tools exposure · Policies/Tiers/Limits ·
Pricing · Requests · Jobs · Webhooks · Security/Abuse · Health/Capacity ·
Budgets/Alerts · Support Trace · Versioning/Status/Incidents · Kill switches.

Hai việc admin phải làm được trong **một phút**, vì đó là lúc cần chúng nhất:
1. Từ một `request_id` khách gửi trong ticket → ra được key, job, tiền, webhook.
2. Tắt một tool, một khoá, hoặc cả bề mặt — không cần deploy.

## 4. Thương mại

- Bảng giá **có phiên bản**; quote và job ghi lại phiên bản đã dùng.
- Chi phí provider/GPU/storage phân tích **tách khỏi** credit khách.
- Biên lợi nhuận tính được theo tool và theo model.
- Ngân sách và cảnh báo **không phải** sổ cái — chúng cảnh báo, không ghi tiền.
- Sandbox không sinh chi phí provider thật theo mặc định.

## 5. Vòng đời và niềm tin

- `/api/v1` là hợp đồng; thay đổi phá vỡ phải qua version mới + changelog +
  thời hạn deprecation công bố trước.
- Trang status/incident công khai cho khách đang tích hợp.
- Chính sách lưu trữ nói rõ giữ gì, bao lâu, xoá thế nào; khách xuất và xoá được
  dữ liệu của mình.
- 100% app, tool, model và execution mode có disposition — **không UNKNOWN**, và
  máy kiểm được, như `test_190` đang làm cho app.

## 6. Cái sẽ **không** làm

| Không làm | Vì sao |
|---|---|
| Ledger/queue/storage/provider engine thứ hai | Bất biến của nền tảng; hai nguồn tiền là hai câu trả lời khác nhau về cùng một số dư |
| Redis/Kafka/dịch vụ mới khi chưa có bằng chứng cần | Mỗi dịch vụ là một thứ phải cài, sao lưu, và mất lúc 2 giờ sáng |
| OAuth vì "API xịn phải có OAuth" | Chỉ mở khi có bên thứ ba thật cần hành động thay mặt người dùng |
| Đưa route UI vào `/api/v1` hoặc ngược lại | Hai bề mặt, hai mô hình xác thực |
| Dùng provider `api_keys` làm khoá khách | Một cái giải mã được, một cái băm một chiều — trộn là hỏng cả hai |
| Deploy production trong pack này | Ngoài phạm vi; kết luận cuối cùng chỉ là `READY` hoặc `NOT_READY` |

## 7. Điều kiện gọi là xong (EXT-21)

1. Mọi domain trong gap matrix ở trạng thái `DONE`, `NOT_APPLICABLE`, hoặc
   `DEFERRED_WITH_ADR` — **không còn** `MISSING`/`PARTIAL` không có chủ.
2. Mọi operation công khai có execution mode đã chứng nhận từ ngoài vào.
3. Full gate xanh trên cây mã cuối; secret scan 0 finding.
4. Bơm lỗi cho credit/queue/webhook/provider/storage (và OAuth nếu bật) đều kết
   sổ đúng một lần.
5. Có checklist rollback và deploy có kiểm soát.
6. Kết luận duy nhất: `API_PLATFORM_FULL_READY_FOR_CONTROLLED_DEPLOY` hoặc
   `API_PLATFORM_NOT_READY`.
