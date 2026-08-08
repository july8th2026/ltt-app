# 06 - Options và decision gate

## Ba phương án tổng

| Phương án | Giá trị | Coverage | Rủi ro | Time-to-value | Điểm /10 |
|---|---:|---:|---:|---:|---:|
| A - REPAIR tối thiểu: chỉ ẩn card và vá lỗi Upscale | 6 | 4 | thấp | nhanh | 6,3 |
| B - REPAIR -> PARITY chọn lọc: audience contract, JobEvent chung, shell chung rồi từng app | 9 | 9 | vừa | tốt | **8,8** |
| C - Build-all/redesign mọi app đồng thời | 8 | 10 | rất cao | chậm | 5,2 |

**Khuyến nghị: B.** Đây là cách duy nhất xử lý gốc mà vẫn triển khai tuần tự,
không chồng chéo và có rollback theo phase.

## Câu hỏi đã được chủ sản phẩm khóa ngày 2026-08-08

| # | Lựa chọn | Khuyến nghị | Hệ quả |
|---:|---|---|---|
| 1 | “Bỏ” = xóa code ngay hay gỡ bề mặt khách trước? | **Gỡ surface, giữ runtime tạm** | không làm gãy Agent; xóa vật lý chỉ sau dependency migration |
| 2 | URL cũ `/kichban` và `/thumbnail` xử lý thế nào? | **redirect 308 tới đích mới trong một chu kỳ**, sau đó 410 nếu cần | giữ bookmark/history, rollback dễ |
| 3 | Demo ai được dùng? | **admin/ops only** | customer 404; vẫn nghiệm thu pipeline rẻ |
| 4 | Media Tools có tên trong Agent không? | **không hiện như app; capability vẫn hiện bằng tên nghiệp vụ Image/Video/Audio** | bỏ jargon kỹ thuật nhưng giữ chức năng |
| 5 | Nhãn `Đã hoàn thiện` có nghĩa product live hay quality PASS? | **đổi thành `Đã phát hành`**; quality gate tách riêng | tránh tuyên bố sai khi Upscale còn bug |
| 6 | Filter marketplace | **hai trục: Trạng thái và Thể loại** | không trộn lifecycle với AI Image/Video |
| 7 | Job history retention | **metadata/timeline 365 ngày; internal debug 30 ngày; artifact theo policy riêng** | cân bằng hỗ trợ, privacy và storage; cần chốt pháp lý |
| 8 | Customer được xem log mức nào? | **timeline đã làm sạch; raw technical chỉ admin/support** | giảm lộ tenant/secret và bớt gây rối |
| 9 | Prompt AI target có team/workspace/cost team ngay không? | **DEFER team**, làm single-user workflow đúng trước | không dựng số/feature giả; giảm scope |
| 10 | Socialbot | **giữ frozen + maintenance**, chỉ hưởng shell/log chung | muốn phát triển lại phải đổi quyết định nền riêng |
| 11 | Thứ tự app | **Upscale -> AutoSub drift -> Marketplace/merge -> Tạo Video -> Prompt -> app thiếu mô tả** | đóng bug xác định trước, không build từ folder trống |
| 12 | AutoSub rollout | **canary user -> public**, giữ legacy flag một release | sửa đúng nguyên nhân và có rollback tức thì |

**Kết quả:** chủ sản phẩm chọn toàn bộ phương án khuyến nghị. Các lựa chọn đã
được ghi thành Q69-Q80 trong `docs/QUYET_DINH_NEN_TANG.md`; BUILD H26 được mở.
