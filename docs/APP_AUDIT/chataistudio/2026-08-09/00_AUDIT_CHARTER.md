# A0 — Audit charter H26.10B Chat AI Studio

Mode STANDARD thu gọn theo Phase H26.10; persona là khách hàng sáng tạo nội
dung, không phải dev. Ba JTBD: bắt đầu hội thoại nhanh; gửi câu hỏi/tệp và nhận
phản hồi có thể dừng; tìm lại/tiếp tục/xuất/nhánh hội thoại riêng tư.

Phạm vi local fixture cô lập, desktop 1920×1080 và mobile 390×844. Không gọi
provider thật, không dùng production, không đổi sidecar/model/cost/schema.
Folder desktop `ChatAIStudio` chỉ có `desktop.ini`, không có `MoTa.txt` hay ảnh;
mọi capability mới ngoài code/browser giữ UNKNOWN.

Acceptance: không lộ engine ID; tiếng Anh/Việt nhất quán trong app; send/stop,
title, credit và operation trace phản hồi đúng; lịch sử bền; credit không âm khi
sidecar phát sinh ảnh; lỗi/ngắt sau partial output không làm mất phần đã giao.

