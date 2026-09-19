> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: docs/developer_portal_mvp_ui/ (đợt ổn định UI khác, đang sống). Chỉ đọc để hiểu lịch sử.

# 05 — Kế hoạch di trú (đã thi hành xong phần P1)

Nguyên tắc: **gốc → sửa dùng chung → đổi nơi gọi**, không vá từng trang.

| Batch | Việc | Trạng thái |
|---|---|---|
| 1 | primitive `.ltt-file` + macro + `chon_tep.js`; `overflow:auto`→`overflow-y` ở 3 panel | ✅ |
| 2 | trang tham chiếu `/taoanh` | ✅ đo lại: 6 tràn → **0** |
| 3 | 4 bản sao luật hàng chip → `flex-wrap:wrap` | ✅ `.th-chips` 1322/391 → **0** |
| 4 | ẩn input native còn hiện ở `/upscalevideo`, `/taoclipngan` | ✅ |
| 5 | 316 màu cứng → token | ⏸️ **cố ý hoãn** |
| 6 | primitive khác (Dialog, Toast, JobState…) | ⏸️ **cố ý hoãn** |

## Vì sao batch 5 và 6 hoãn, chứ không phải bỏ quên

**Batch 5 (màu cứng).** Quét hàng loạt 316 màu là một đợt regression lớn đổi lấy
một cải thiện không ai nhìn thấy. Một màu cứng có thể đang **bù cho một token
sai** ở chỗ khác; thay mù là làm hỏng chỗ đang đúng. ⇒ Luật thay thế: **cái mới
phải sạch** (`test_310` chốt primitive không được dùng hex), cái cũ thay dần khi
có lý do chạm vào.

**Batch 6 (primitive khác).** Audit chỉ chứng minh được **một** primitive đang gây
lỗi đo được. `.btn` đã lành (28 luật mở rộng, không mâu thuẫn). Dựng 19 primitive
cho nhu cầu chưa tồn tại là đúng thứ mục T của đề bài cấm.

## Thứ KHÔNG làm, và lý do

| Không làm | Vì |
|---|---|
| `overflow-x:hidden` toàn site | che lỗi, không sửa lỗi. `test_310` chặn |
| Đổi breakpoint | 768/390 **không tràn** — responsive đang đúng |
| Chuyển React↔Jinja | không giải quyết lỗi nào đo được |
| Dựng `FileDropzone` primitive | đúng **một** nơi gọi Jinja (`/upscalevideo`); React tự lo |
| Phục hồi 4 app đã gỡ | chủ sản phẩm đã quyết. Không còn dấu vết CSS nào |
