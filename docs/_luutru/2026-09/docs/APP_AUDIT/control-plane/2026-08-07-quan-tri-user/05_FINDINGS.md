# A6 — Findings

Mỗi finding: `hiện tượng → bằng chứng → ảnh hưởng → root cause → severity →
phạm vi → phương án → acceptance`.

---

## F-01 · P0 · Cấp credit cho user không tồn tại không bị chặn

**Hiện tượng.** Form `/admin/grant-credit` nhận UUID gõ tay. Gõ sai một ký tự thì
hệ thống vẫn ghi bút toán và báo thành công: *"Đã cấp **+500** credit cho
`3f2a…`. Số dư mới: **500**."*

**Bằng chứng.**
- E1 — `server/admin.py:399`: ô nhập là `name="user_id"`, nhãn *"User ID (UUID —
  lấy ở mục Người dùng)"*.
- E1 — `platform_core/credit.py:77` `cap_tay()` gọi thẳng `_ghi()`, **không kiểm
  người dùng tồn tại**.
- E2 — CSDL production 2026-08-07: `credit_entries` **không có khoá ngoại** nào.
- E2 — hiện **0 bút toán mồ côi**. Lỗ có thật nhưng **chưa bị sập vào**.

**Ảnh hưởng (JTBD J1, J3).** Credit rơi vào hư không. Nhân viên báo chưa có
credit, màn hình admin nói đã cấp rồi. Không lỗi nào ở đâu cả, và cách duy nhất
phát hiện là tự đi truy vấn CSDL. Với ~10 nhân viên sắp onboard, đây là chuyện
**sẽ xảy ra**, không phải "có thể".

**Root cause.** Hai tầng cùng thiếu kiểm: nghiệp vụ (`cap_tay` không xác thực) và
CSDL (không FK). FK là hạng mục **đã cố ý hoãn từ H7** — nay đã có hậu quả cụ thể.

**Severity P0** — về tiền, theo mục 4: *"P0 về tiền … luôn chặn release"*.
Chặn G3 và G4.

**Phạm vi.** `platform_core/credit.py`, migration mới, `server/admin.py`.

**Phương án.** Kiểm tồn tại trong `cap_tay()` + thêm FK `credit_entries.user_id →
users.id`. Hai tầng, vì tầng nghiệp vụ cho thông báo lỗi tử tế còn FK là lưới an
toàn cuối khi có đường ghi khác.

**Acceptance.** Cấp credit cho UUID không tồn tại → **từ chối kèm thông báo rõ**,
không ghi bút toán nào. Có test hồi quy chứng minh được tính bác bỏ (trồng lại
bug thì test đổ).

---

## F-02 · P1 · Phải gõ UUID bằng tay

**Hiện tượng.** Muốn cấp credit phải sang trang Người dùng, bôi đen UUID, quay
lại, dán.

**Bằng chứng.** E1 — `admin.py:399`; E1 — Control Registry J1 có `MISSING` cho
"copy UUID".

**Ảnh hưởng (J1).** Mỗi lần cấp là hai trang và một thao tác copy dễ sai. UUID là
chuỗi con người **không kiểm tra được bằng mắt** — đó là điều kiện làm F-01 nguy
hiểm.

**Root cause.** Form dựng thẳng HTML, dùng khoá chính làm ô nhập thay vì dùng
danh tính người đọc được.

**Severity P1.** **Phương án.** Nhận **email** thay cho UUID.
**Acceptance.** Nhập email hợp lệ → cấp đúng người; email không tồn tại → từ chối
trước khi ghi.

---

## F-03 · P1 · Không cấp được hàng loạt

**Hiện tượng.** Onboarding N người = N lần submit.
**Bằng chứng.** E1 — không có control nào cho hàng loạt.
**Ảnh hưởng (J1).** Đúng việc đang cần làm tuần này.
**Severity P1.** **Phương án.** Dán danh sách email + một số credit + một ghi chú;
**kiểm toàn bộ trước, ghi trong một transaction**, báo rõ email nào không thấy.
**Acceptance.** Một email sai → **không ai** được cấp, và báo rõ email nào sai.

---

## F-04 · P2 · Số dư không có ở nơi quản lý người dùng

**Hiện tượng.** `column_list` không có số dư.
**Bằng chứng.** E1 — `admin.py:249`.
**Ảnh hưởng (J2).** Con số vận hành quan trọng nhất về một người không hiện ở chỗ
quản lý người. Không có trang nào trả lời "người này đang thế nào".
**Severity P2.** **Phương án.** Cột số dư + trang chi tiết gom số dư/job/đơn/phiên.
**Acceptance.** Mở một user thấy đủ bốn thứ mà không phải copy UUID đi đâu.

---

## F-05 · P2 · Không có test nào phủ luồng cấp credit của admin

**Hiện tượng.** Luồng động tới tiền, không có test.
**Bằng chứng.** E1 — không thấy test nào gọi `/admin/grant-credit` hay `cap_tay`
qua HTTP.
**Ảnh hưởng.** Chặn G8. Chính vì thiếu test mà F-01 sống sót tới hôm nay.
**Severity P2** (nhưng chặn gate). **Acceptance.** Có test cho: cấp thành công,
UUID/email sai bị từ chối, CSRF sai bị từ chối, hàng loạt nguyên tử.

---

## F-06 · P3 · Nhật ký thao tác admin chỉ có với credit

**Hiện tượng.** `cap_tay(by=)` ghi `admin=` vào ghi chú bút toán. Đổi vai trò,
vô hiệu hoá tài khoản thì không lưu dấu vết ai làm, lúc nào.
**Bằng chứng.** E1.
**Severity P3.** Với một admin thì rủi ro thấp; ghi nhận để không quên khi thêm
người quản trị thứ hai. **Phương án.** DEFER.


---

# Trạng thái thực hiện — cập nhật 2026-08-07

| Finding | Trạng thái | Bằng chứng |
|---|---|---|
| F-01 P0 | ✅ đóng | `cap_tay()` kiểm tồn tại + migration `c1d2e3f4a5b6` (FK RESTRICT). E2 test 16 mục, có tính bác bỏ (bỏ kiểm tra → 5 đổ) |
| F-02 P1 | ✅ đóng | Nhận email, giữ UUID dự phòng. E2 |
| F-03 P1 | ✅ đóng | `cap_hang_loat()` nguyên tử, email lặp chỉ cấp một lần. E2 |
| F-05 P2 | ✅ đóng | `test_163` 15 mục qua HTTP: quyền, CSRF, nguyên tử, nói thật. E2 |
| F-04 P2 | ✅ đóng (trang chi tiết, E2) · cột danh sách còn nợ E3 | xem dưới |
| F-06 P3 | ✅ đóng | bảng `nhat_ky_admin`, ghi tại 2 chỗ, view chỉ xem. E2 |

## F-04 — làm một phần, và phải nói rõ phần nào chưa chắc

**Đã làm:** thêm `User.so_du_credit` và khai cột "Số dư" trong `UserAdmin.column_list`.

**Chưa chắc:** test ban đầu `assert "777" in html` **đổ** — HTML trả về từ
`/admin/user/list` chỉ có vỏ trang, sqladmin dựng bảng theo cách khác. Tôi **không
nới lỏng test cho xanh rồi nói "đã xác minh"** — đó đúng là thứ mục 5 cấm.

Test hiện chốt: cột **đã được khai**, nhãn đúng, trang **mở được** (200). Nó
**không** chốt số dư hiện ra đúng.

**Việc còn nợ:** kiểm trên browser thật (E3). Cho tới lúc đó, F-04 là `PARTIAL`,
không phải `LIVE`.

**Chưa làm:** trang chi tiết một người dùng (`/admin/user/<id>` gom số dư, job,
đơn, phiên).


## F-04 — cập nhật sau khi làm trang chi tiết

**Đã đóng phần quan trọng.** `/admin/nguoi-dung?q=<email hoặc id>` gom số dư, 15
bút toán credit, 20 việc, 10 đơn nạp và số phiên đang mở về một chỗ. Đây chính là
JTBD J2 — "biết một người dùng đang thế nào" — trước đây phải mở 4 trang và tự
nối bằng một UUID copy tay.

Test chứng minh **ở mức E2**: số dư `777` xuất hiện thật trong HTML trả về, cùng
đủ năm mục. Khác hẳn cột trong danh sách, nơi test tương tự đã đổ.

**Còn nợ:** cột "Số dư" trong `/admin/user/list` vẫn chưa chứng minh được là hiện
đúng (sqladmin dựng bảng theo cách khác). Hạ mức độ quan trọng: giờ đã có trang
chi tiết trả lời được câu hỏi, cột trong danh sách chỉ còn là tiện lợi. Vẫn cần
kiểm browser (E3) để chốt.
