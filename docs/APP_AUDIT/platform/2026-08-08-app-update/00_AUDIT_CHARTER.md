# 00 - Audit charter

**Mã:** LTT-AQA `AUDIT STANDARD -- platform/app portfolio update`  
**Ngày snapshot:** 2026-08-08  
**Môi trường:** source `D:\LTTSTUDIOSAPP`, local `http://127.0.0.1:8100`,
Chrome thật qua Playwright session `ltt`. Không dùng dữ liệu production và không
gọi provider trả phí trong lượt lập kế hoạch.

## Phạm vi

1. Kho ứng dụng và điều hướng chung.
2. Xử lý ba bề mặt không còn dành cho khách: Kịch bản YouTube, Demo kiểm tra hạ
   tầng và Media Tools.
3. Lịch sử job, nhật ký sự kiện và log debug dùng chung cho mọi tool còn chạy.
4. Đối chiếu source hiện tại với ảnh và `MoTa.txt` trong
   `C:\Users\Thang Tuong\Desktop\AppLttStudio_Update_08082025`.
5. Lập roadmap tuần tự; chưa chuyển AUDIT thành BUILD/DEPLOY khi các quyết định
   tại `06_OPTIONS_AND_DECISIONS.md` chưa được khóa.

## Persona và JTBD

- Persona chính: khách hàng sáng tạo nội dung, không phải developer.
- JTBD: tìm đúng công cụ, hiểu nó đang sẵn sàng hay bảo trì, tạo tác vụ, biết
  chi phí/trạng thái, lấy kết quả, và tự xử lý lỗi phổ biến mà không cần hỏi hỗ
  trợ.
- Persona phụ: quản trị viên cần correlation ID, timeline và log đã lọc bí mật
  để debug.

## Ngoài phạm vi lượt này

- Không đánh giá chất lượng output AI hay thay provider/model.
- Không xóa dữ liệu, migration hay route cũ.
- Không sửa `D:\BOT GEMINI`; chỉ khảo sát read-only khi đến phase Prompt AI.
- Không nâng cấp tính năng Socialbot vì app đang đóng băng; chỉ được thay đổi
  trạng thái hiển thị và dùng hạ tầng observability chung.

## Điều kiện hoàn tất audit

- Có inventory thật, finding gắn evidence, Q/M/E và G0-G8.
- Có ba phương án REPAIR/PARITY/DIFFERENTIATED.
- Có decision gate và roadmap Phase 0-5 với acceptance, test, rollback.
- Hạng mục chưa có mô tả/ảnh phải ghi `UNKNOWN`, không tự phát minh yêu cầu.

