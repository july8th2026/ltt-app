# H21.8 — Giao thức controlled beta Agent Canvas

> Trạng thái: **READY TO RUN, CHƯA CÓ KẾT QUẢ**. Tài liệu này không phải bằng
> chứng beta và không được dùng để đánh dấu H21.8 PASS khi chưa có đủ 5 người
> dùng thật.

## 1. Mục tiêu và điều kiện mở phiên

Đo xem người chưa biết ToolSpec/kiến trúc có tự hoàn thành các chuỗi sáng tạo
cốt lõi hay không. Chỉ mở phiên khi:

- môi trường staging/local beta dùng build chứa commit H21.7 trở lên;
- tài khoản beta tách biệt, không có quyền admin và không có dữ liệu production;
- có sẵn 1 ảnh test thuộc quyền LTT, credit cap theo phiên và rollback dữ liệu;
- console/network recorder bật nhưng không ghi token, mật khẩu hoặc nội dung
  riêng tư;
- moderator đã đọc nguyên tắc không gợi ý bên dưới.

## 2. Cohort bắt buộc

- Đủ **5 người thật**, không tham gia xây Agent Canvas và không được xem sơ đồ
  kiến trúc trước phiên.
- Tối thiểu 3 người thuộc nhóm khách hàng mục tiêu sáng tạo nội dung; tối đa 2
  người có nền tảng kỹ thuật.
- Ghi mã `P01`–`P05`, không ghi tên/email vào hồ sơ audit.
- Mỗi người dùng một workflow mới và cùng một bộ asset/prompt xuất phát.

## 3. Kịch bản kiểm tra

Moderator chỉ đọc nguyên văn mục tiêu, không chỉ vị trí nút hoặc tên block.
Thứ tự T1–T3 được hoán đổi luân phiên giữa người tham gia; T4–T5 làm sau khi đã
có graph.

| Task | Chỉ dẫn đọc cho người dùng | Thành công khi |
|---|---|---|
| T1 | “Tạo một workflow biến mô tả thành hình ảnh.” | Có Text→Image hợp lệ, nhập prompt được và tới màn kiểm tra chi phí |
| T2 | “Tải ảnh mẫu và nhờ AI mô tả/phân tích ảnh đó.” | Có Image→Text hợp lệ, asset thuộc user và Text nhận đúng reference |
| T3 | “Dùng ảnh mẫu làm khung đầu để tạo video.” | Có Image→Video hợp lệ và Video nhận đúng reference |
| T4 | “Chỉ kiểm tra/chạy block đang chọn, không chạy toàn workflow.” | Scope là một node, quote hiện trước xác nhận và actual bằng 0 trước approve |
| T5 | “Từ một block ở giữa, chạy tiếp phần phụ thuộc phía sau.” | Người dùng tìm đúng hành vi chạy từ đây/scope tương đương và hiểu phạm vi |

Nếu staging không có provider an toàn, T4–T5 dừng ở quote/approval screen và ghi
`provider_not_executed`; không biến lỗi hạ tầng thành lỗi UX. Mọi lần chạy thật
phải có cap và được người dùng nhìn thấy chi phí trước khi xác nhận.

## 4. Cách đo nhất quán

Bấm giờ từ lúc moderator đọc xong task đến lúc đạt điều kiện thành công hoặc quá
5 phút. Ghi trực tiếp vào `08_CONTROLLED_BETA_RESULTS.csv`:

- `success`: `1` nếu tự hoàn thành, `0` nếu bỏ cuộc/sai kết quả/hết giờ;
- `first_valid_chain_seconds`: chỉ cho T1–T3, tính tới dây hợp lệ đầu tiên;
- `misclicks`: click không đưa gần hơn tới mục tiêu, click lặp do không phản hồi;
- `help_requests`: câu hỏi xin moderator chỉ cách làm; moderator chỉ trả lời tối
  đa một gợi ý trung tính rồi đánh dấu;
- `abandoned`: `1` nếu người dùng chủ động dừng;
- `clarity_1_5`: sau task, hỏi “Bạn hiểu màn hình và bước tiếp theo rõ tới mức
  nào?” từ 1 đến 5;
- `observed_issue`: mô tả hành vi nhìn thấy, không suy đoán nguyên nhân.

Không sửa giao diện giữa cohort. Nếu xuất hiện P0/P1 về quyền, credit, mất dữ
liệu hoặc provider chạy trước xác nhận: dừng cohort, lưu bằng chứng đã che bí
mật, sửa và bắt đầu lại đủ 5 người trên cùng một build.

## 5. Công thức và gate PASS

- `task_success = tổng success / 25 × 100`; yêu cầu **≥80%**.
- Median `first_valid_chain_seconds` của các task T1–T3 thành công: **≤120 s**.
- Trung bình `help_requests` trên mỗi task: **≤1**; không participant nào cần
  moderator làm thay.
- Không có P0/P1 mở; abandon phải được phân tích, không được loại khỏi mẫu.
- Điểm UX/UI re-audit theo `quy_tac_audit.md`: **≥75/100**; Q **≥80**.

Thiếu bất kỳ điều kiện nào là H21.8 FAIL/REWORK, không làm tròn lên và không mở
H21.9.

## 6. Vòng sửa có kiểm soát

1. Tổng hợp issue theo tần suất × tác động; gắn evidence `Pxx-Tx`.
2. Sửa từng lát cắt, thêm regression test, chạy browser flow liên quan.
3. Với P0/P1 hoặc thay đổi hành vi task, chạy lại cohort 5 người mới hoặc reset
   hoàn toàn kiến thức của cohort nếu chứng minh được họ chưa thấy phần sửa.
4. Chốt scorecard Q/M/E và link commit/build đã test.
5. Chỉ đề xuất H21.9 khi toàn bộ gate mục 5 PASS.

## 7. Checklist bàn giao sau phiên

- [ ] Đủ 25 dòng dữ liệu, không có thông tin nhận dạng cá nhân.
- [ ] Có build/commit, viewport, browser và thời điểm cho từng participant.
- [ ] Console/network issue đã phân loại; không chứa secret.
- [ ] Credit trước/sau phiên đối soát khớp các run được xác nhận.
- [ ] Issue list có severity, owner, acceptance test.
- [ ] Scorecard Q/M/E được cập nhật bằng evidence E4.
- [ ] Quyết định PASS/REWORK được ghi trong `NHAT_KY.md`.
