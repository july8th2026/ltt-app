# A7 — Ba phương án · A8 — Decision Gate

## A7 — Ba phương án

### REPAIR — đóng blocker
F-01 (kiểm tồn tại + FK) và F-05 (test). Chỉ đủ để G3/G4/G8 PASS.
Không giải quyết việc onboarding tuần này.

| | |
|---|---|
| Giá trị | 4/5 — bỏ lỗ tiền |
| Coverage JTBD | J3 một phần |
| Rủi ro | thấp; FK cần migration, có thể vướng dữ liệu cũ (E2: 0 mồ côi → sạch) |
| Time-to-value | ngắn nhất |
| Chi phí | thấp |
| Confidence | cao (E2) |

### PARITY — đạt chuẩn dùng được
REPAIR + F-02 (email thay UUID) + F-03 (hàng loạt) + F-04 (số dư và trang chi tiết).
Phủ trọn J1 và J2.

| | |
|---|---|
| Giá trị | 5/5 — đúng việc đang cần |
| Coverage JTBD | J1, J2, J3 |
| Rủi ro | trung bình — F-04 chạm `UserAdmin`, phải cẩn thận không mở đường sửa email |
| Time-to-value | vừa |
| Chi phí | vừa |
| Confidence | cao |

### DIFFERENTIATED — vượt chuẩn
PARITY + thống kê theo thời gian, xếp hạng người tiêu nhiều, thống kê theo app,
nhật ký thao tác admin đầy đủ, cảnh báo số dư thấp.

| | |
|---|---|
| Giá trị | 2/5 **ở thời điểm này** — 10 người dùng nội bộ thì biểu đồ chưa nói lên gì |
| Rủi ro | kéo dài, chặn việc onboarding |
| Confidence | thấp — chưa biết cần đo gì cho tới khi có dữ liệu dùng thật |

## Khuyến nghị

**`REPAIR → PARITY chọn lọc`**, đúng lộ trình mặc định của LTT-AQA mục A7
(*"không build-all"*). DIFFERENTIATED **DEFER** cho tới khi có dữ liệu dùng thật
từ đợt test nhân viên — lúc đó mới biết cần đo gì, thay vì đoán.

Xếp theo mục 10 (`Delivery Priority = Opportunity / (Effort × Dependency Risk)`):

| Hạng mục | Opportunity | Effort | Dep. Risk | Ưu tiên |
|---|---:|---:|---:|---:|
| F-01 kiểm tồn tại + FK | **P0 — không qua công thức** | | | **1** |
| F-02 email thay UUID | 4,3 | 1 | 1 | **4,3** |
| F-03 cấp hàng loạt | 4,1 | 2 | 1 | **2,1** |
| F-05 test luồng credit | 3,4 | 1 | 1 | **3,4** |
| F-04 số dư + trang chi tiết | 3,6 | 3 | 2 | **0,6** |
| F-06 nhật ký admin | 1,8 | 3 | 1 | 0,6 → DEFER |

## A8 — Decision Gate

> LTT-AQA mục A8: *"Không chuyển audit thành code khi chưa khóa logic."*
> Sáu câu dưới đây phải có câu trả lời của chủ sản phẩm **trước khi** viết code.

| # | Câu hỏi | Khuyến nghị | Hệ quả nếu chọn khác |
|---|---|---|---|
| D1 | Phạm vi đợt này? | REPAIR + F-02 + F-03 + F-05 | Bỏ F-03 thì onboarding vẫn thủ công |
| D2 | Thêm FK `credit_entries.user_id` ngay? | **Có** — production hiện 0 mồ côi nên migration sạch | Hoãn thì lưới an toàn cuối vẫn trống |
| D3 | Cấp credit nhận email hay vẫn UUID? | **Email**, giữ UUID làm đường dự phòng | Chỉ UUID thì F-01 còn nguyên nguy cơ |
| D4 | Hàng loạt: một email sai thì sao? | **Từ chối toàn bộ**, không ai được cấp | Cấp một phần → trạng thái nửa vời, khó đối soát |
| D5 | Trang chi tiết user (F-04) đợt này hay sau? | **Sau** — ưu tiên 0,6, không chặn onboarding | Làm ngay thì chậm việc tuần này |
| D6 | Nhật ký thao tác admin (F-06)? | **DEFER** tới khi có admin thứ hai | |

## Quyết định đã khoá — 2026-08-07

| # | Chốt | Ghi chú |
|---|---|---|
| D1 | **Làm tất cả hạng mục** | Rộng hơn khuyến nghị `REPAIR → PARITY chọn lọc` của tôi |
| D2 | **Có** — thêm FK ngay | |
| D3 | **Email** thay UUID | |
| D4 | **Từ chối toàn bộ** khi có một email sai | |
| D5 | OK | Đọc cùng D1 = **làm trong đợt này**, nhưng xếp sau blocker |
| D6 | **Triển khai luôn** nhật ký thao tác admin | Đảo `DEFER` ở A7 |

**Cách hiểu D5 đã nêu rõ với chủ sản phẩm:** câu hỏi là "đợt này hay sau", trả
lời "OK" một mình thì lưỡng nghĩa; đọc cùng D1 ("tất cả") và D6 ("triển khai
luôn") thì kết luận là **làm trong đợt này**. Ghi lại đây để sau không ai phải
đoán lại.

**Hệ quả với A7:** phạm vi thành `REPAIR + PARITY + một phần DIFFERENTIATED`
(F-06). Phần DIFFERENTIATED còn lại — thống kê theo thời gian, xếp hạng người
tiêu nhiều, thống kê theo app — **vẫn DEFER**, vì với 10 người dùng nội bộ thì
biểu đồ chưa nói lên điều gì, và chưa ai yêu cầu.

**Trạng thái:** ✅ **ĐÃ KHOÁ.** Chuyển sang A9 Roadmap.
