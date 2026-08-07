# A0 — Charter

**Audit:** `AUDIT QUICK -- app: control-plane (quản trị user + credit)`
**Chuẩn:** LTT-AQA v1.0 · **Ngày:** 2026-08-07 · **Người chấm:** Claude

## Vì sao QUICK chứ không STANDARD

Phạm vi hẹp và đã khoanh rõ: **quản trị người dùng và cấp credit**, không audit
toàn bộ control plane. QUICK được gộp file nhưng **không bỏ** Q/M/E/Gate/evidence
(quy tắc mục 11). Các mục ngoài phạm vi (APIKEYS, Doanh thu, Job, Phiên) chỉ ghi
nhận sự tồn tại, không chấm.

## Persona và JTBD

**Persona:** chủ sản phẩm — một người, đọc tiếng Việt, không phải kỹ sư vận hành
chuyên trách, dùng trang quản trị vài lần một tuần.

Ba JTBD, khoá theo việc sắp làm (mở cho ~10 nhân viên test thực chiến):

| # | JTBD | Tần suất |
|---|---|---|
| J1 | Cấp credit cho một nhóm nhân viên để họ bắt đầu test | đợt, mỗi lần nhiều người |
| J2 | Biết một người dùng đang thế nào: số dư, đã tiêu gì, job nào lỗi | hằng ngày trong đợt test |
| J3 | Xử lý sự cố tiền: cấp bù, thu hồi, đối soát khi khách khiếu nại | hiếm, nhưng nghiêm trọng |

## Môi trường và ranh giới dữ liệu

- Đọc mã nguồn `D:\LTTSTUDIOSAPP` (E1).
- **Đọc** CSDL production để đếm sự thật (E2) — chỉ `SELECT`, không ghi.
- **Không** thao tác cấp credit thật trên production trong audit này.
- Chưa render trang admin trên browser (E3) — xem giới hạn ở 04_SCORECARD.

## Trọng số

Dùng nguyên trọng số mục 3 của LTT-AQA, **khoá trước khi chấm**. App này không
sinh nội dung AI → 8 điểm nhóm "AI output/provider economics" phân bổ lại:
+4 vào "Security/privacy/tenant/credit" (thành 14) và +4 vào "Đúng chức năng và
control" (thành 16). Lý do: giá trị và rủi ro của trang quản trị nằm ở **tiền và
đúng thao tác**, không nằm ở chất lượng sinh nội dung.

**PASS A0:** phạm vi không còn hai cách hiểu.
