# 02 — Journey & Control Registry: Prompt AI OMMI

## Hành trình chuẩn và kết quả

| ID | Hành trình | Kỳ vọng khách hàng | Kết quả | Gate |
|---|---|---|---|---|
| J-01 | Mở workspace | Hiểu điểm bắt đầu trong ≤30 giây | 10 mục ngang, nhiều thuật ngữ; chưa có CTA hành trình | FAIL |
| J-02 | Tạo project | Có setup/name/cancel trước khi lưu | Tạo record trống ngay lập tức | FAIL |
| J-03 | Viết brief | Autosave rõ, không mất dữ liệu | click/action race làm mất prompt | FAIL |
| J-04 | Gắn resource/style/meta | Chọn asset tham chiếu ngay trong brief/scene | Backend có, UI không có | FAIL |
| J-05 | Quote Director | Thấy giá/phạm vi trước chạy | Quote 6 credit hiển thị rõ | PASS |
| J-06 | Chạy Director | Kết quả trả về đúng project đã trả tiền | apply revision 0 → 409 | FAIL/P1 |
| J-07 | Sửa storyboard | CRUD/reorder/continuity/history dễ hiểu | CRUD cơ bản; nhiều capability không lộ | PARTIAL |
| J-08 | Chạy một cảnh | Quote/run/cancel/retry và output gắn cảnh | Có phần lớn; lỗi validation chỉ hiện `Lỗi 422` | PARTIAL |
| J-09 | Chuyển ảnh/video | Một click handoff sang app phù hợp | Không có UI | FAIL |
| J-10 | Khôi phục | clone/archive/snapshot/restore/version | API/legacy có, UI mới thiếu | FAIL |
| J-11 | Tìm job | lịch sử, trạng thái, retry và log dễ hiểu | recent-only, sai nhãn/mất cross-app | FAIL |
| J-12 | Dùng EN/theme | locale/theme áp dụng A–Z và lưu theo user | EN vẫn VI; theme không áp dụng | FAIL |
| J-13 | Mobile | thao tác chính không bị che/cắt | panel chặn nav; nav ribbon khó khám phá | FAIL |
| J-14 | Reload/deep-link | trở lại đúng màn hình/project | luôn về Overview, không URL state | FAIL |

## Registry control chính

| Control | Vị trí | State/feedback | Quyền/credit | Kết quả |
|---|---|---|---|---|
| Tạo project/storyboard/resource/library | các màn hình | tạo ngay, không confirm/setup | owner | PARTIAL |
| Lưu field onBlur | project/resource/storyboard | global busy, không dirty indicator | owner | FAIL |
| Chạy Director | Project | quote/confirm/poll | 6 credit fixture | FAIL apply |
| Sinh resource | Resource | quote/confirm/poll | 5 credit fixture | PARTIAL |
| Sinh scene | Storyboard | quote/run/cancel/retry | credit | PARTIAL |
| Upload image | Resource | preview cơ bản | owner | FAIL security lifecycle |
| Export JSON/MD/ZIP | Project | download | owner | PASS cơ bản |
| Theme/locale | Settings | báo đã lưu | owner | FAIL honest UI |
| Library history | Prompt Library | chỉ xem version list | owner | PARTIAL |
| Nav desktop/mobile | shell app | ribbon ngang | public/auth | PARTIAL/FAIL mobile |

## Ma trận dữ liệu và phục hồi

| Đối tượng | Tạo | Sửa | Xóa/archive | Version/restore | Orphan policy |
|---|---|---|---|---|---|
| Project | Có | Có | archive API | snapshot API | UI mới thiếu recovery |
| Resource row | Có | Có | Có | variants | blob delete/promotion chưa atomic |
| Storyboard/scene | Có | Có | Có | history/compare/restore backend | UI chỉ lộ một phần |
| Library item | Có | Có | Có | versions | không restore/diff từ UI |
| Job/output | Có | poll | cancel một phần | retry một phần | recent-only, cross-app mất |
