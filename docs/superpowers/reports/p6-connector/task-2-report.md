# P6 · Task 2 — Job Object (`win32job`) cho CPU / bộ nhớ / cây tiến trình

**Kết quả: ĐẠT.** `platform_core/workflow/job_object.py`.

Hạn mức mỗi lệnh: `JOB_OBJECT_LIMIT_PROCESS_MEMORY` **512 MB** ·
`LIMIT_ACTIVE_PROCESS` **4** · `KILL_ON_JOB_CLOSE` ·
`DIE_ON_UNHANDLED_EXCEPTION`. Node chạy kèm `--max-old-space-size=384` để lỗi
hết bộ nhớ lộ ra dưới dạng **đọc được** (`JavaScript heap out of memory`)
trước khi job giết tiến trình (không đọc được gì).

## ⚠️ Vai của nó, và ⛔ vai KHÔNG phải của nó

Spec §11.2 xếp Job Object vào mục *"mạng đi ra"*. Đó là **nhầm vai**, và spike
đã đo ra hậu quả: một piece `spawn` một tiến trình con vẫn ra Internet trong
khi vẫn nằm gọn trong job. **Job Object không lọc socket.** Ranh giới egress
là AppContainer (`vo_boc.py`, Task 1).

Cái nó thật sự mua, và không thứ gì khác mua được:

1. Trần bộ nhớ **theo tiến trình** — một piece nạp một phản hồi 3 GB thì
   **tiến trình đó** chết, không phải máy chủ (máy A là production).
2. `KILL_ON_JOB_CLOSE` — khi tiến trình Python nhả handle, **kể cả khi nó bị
   giết**, Windows giết cả cây. Không còn tiến trình mồ côi giữ tệp tạm sau
   một lượt bị ngắt. Đây là câu trả lời cơ học cho bài học
   *"ngắt gate: khoá còn sống"*.
3. **Kế toán** CPU/RAM đọc được **sau khi** tiến trình đã chết ⇒ số đo của
   Task 6 là kế toán, ⛔ không phải lấy mẫu `psutil` rồi hy vọng trúng đỉnh.

## ⛔ Không dùng `JOB_OBJECT_LIMIT_JOB_TIME` làm hạn giờ

Nó đếm **thời gian CPU**, không phải thời gian trôi. Một piece ngồi chờ một
API chậm tiêu ~0 s CPU và **không bao giờ** chạm trần đó. Hạn giờ thật là
`WaitForSingleObject` trên thời gian trôi ở `vo_boc.chay`, và hết giờ thì
`TerminateJobObject` giết **cả cây** — diễn tập `het_gio` đo được: `han_ms`
3 000 ⇒ lệnh kết thúc ở **8,0 s** (gồm biên 5 s), mã `het_gio`, không treo.

## Gán khi tiến trình **còn treo**

`CREATE_SUSPENDED` → `AssignProcessToJobObject` → `ResumeThread`. Gán sau khi
tiến trình đã chạy là để hở một khoảng trong đó mã không tin cậy chạy **ngoài**
mọi hạn mức.
