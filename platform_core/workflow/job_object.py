"""Windows **Job Object** cho tiến trình runner connector — spec §11.2.

⭐ **Vai đúng của nó, và chỉ vai đó.** Job Object giới hạn **bộ nhớ, CPU và cây
   tiến trình**, và giết cả cây khi handle đóng. Nó **KHÔNG lọc socket**.

⛔ Spec §11.2 (bản viết trước) xếp Job Object vào mục *"mạng đi ra"*. Đó là
   **nhầm vai**, và spike P6/P6B đã đo ra hậu quả: một piece `spawn` một tiến
   trình con gọi `https` vẫn ra Internet trong khi vẫn nằm gọn trong job.
   Ranh giới egress là **AppContainer** (`vo_boc.py`), không phải tệp này.

## Vì sao vẫn cần nó khi đã có AppContainer

AppContainer trả lời câu *"piece có gọi được ra ngoài không"*. Nó **không** trả
lời *"piece có ăn hết 20 lõi và 12 GB của máy production không"*. Hai câu hỏi
khác nhau ⇒ hai cơ chế. Cụ thể ba thứ tệp này mua:

1. `ProcessMemoryLimit` 512 MB — một piece nạp một phản hồi 3 GB vào bộ nhớ thì
   **tiến trình đó** chết, không phải máy chủ.
2. `ActiveProcessLimit` — trần số tiến trình trong job.
3. `KILL_ON_JOB_CLOSE` — ⭐ điều đáng giá nhất: khi tiến trình Python nhả handle
   (kể cả khi nó **bị giết**), Windows giết **cả cây** trong job. Không còn
   tiến trình mồ côi giữ khoá/giữ tệp tmp sau một lượt bị ngắt.

## ⛔ Không dùng `JOB_OBJECT_LIMIT_JOB_TIME` làm hạn giờ

`JOB_OBJECT_LIMIT_JOB_TIME` đếm **thời gian CPU của người dùng**, không phải
thời gian trôi. Một piece ngồi chờ một API chậm tiêu ~0 s CPU và sẽ **không bao
giờ** chạm trần đó. Hạn giờ thật đặt ở `vo_boc.py` bằng `WaitForSingleObject`
trên thời gian TRÔI, và đó là hạn giờ duy nhất.
"""
from __future__ import annotations

import pywintypes
import win32job

#: 512 MB — spec §11.2. Node chạy kèm `--max-old-space-size=384` nên heap của V8
#: chạm trần của chính nó (lỗi `JavaScript heap out of memory`, đọc được) TRƯỚC
#: khi job giết tiến trình (không đọc được gì). Hai con số phải giữ đúng thứ tự
#: đó, nếu không mọi lỗi bộ nhớ đều trông như "tiến trình chết không lý do".
BO_NHO_MAC_DINH_MB = 512

#: `JOB_OBJECT_LIMIT_ACTIVE_PROCESS` = 4 (spec §11.2). Trong AppContainer
#: `spawn` trả `ENOENT` nên con số này gần như không bao giờ chạm tới — nó là
#: lớp thứ hai cho ngày ai đó chạy runner NGOÀI vỏ (vd gỡ lỗi).
SO_TIEN_TRINH_MAC_DINH = 4


class LoiJobObject(OSError):
    """Không dựng được job object. ⛔ Không nuốt: chạy runner không có job là
    chạy mã không tin cậy trên máy production mà không có trần bộ nhớ."""


def tao(*, bo_nho_mb: int = BO_NHO_MAC_DINH_MB,
        so_tien_trinh: int = SO_TIEN_TRINH_MAC_DINH):
    """Một job object **ẩn danh** (không tên) đã đặt hạn mức.

    ⭐ Ẩn danh có chủ đích: một job **có tên** dùng chung giữa hai lượt chạy
       thì trần bộ nhớ và `KILL_ON_JOB_CLOSE` áp cho **cả hai** — lượt A kết
       thúc sẽ giết tiến trình của lượt B. Mỗi lệnh một job, đúng như mỗi lệnh
       một tiến trình.
    """
    try:
        h = win32job.CreateJobObject(None, "")
        info = win32job.QueryInformationJobObject(
            h, win32job.JobObjectExtendedLimitInformation)
        co_ban = info["BasicLimitInformation"]
        co_ban["LimitFlags"] = (
            win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            | win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | win32job.JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION)
        co_ban["ActiveProcessLimit"] = int(so_tien_trinh)
        info["BasicLimitInformation"] = co_ban
        info["ProcessMemoryLimit"] = int(bo_nho_mb) * 1024 * 1024
        win32job.SetInformationJobObject(
            h, win32job.JobObjectExtendedLimitInformation, info)
        return h
    except Exception as loi:  # noqa: BLE001 — bọc lại thành một kiểu đọc được
        raise LoiJobObject(f"khong tao duoc job object: {loi}") from loi


def gan(h_job, h_process) -> None:
    """Gán một tiến trình vào job. Gọi khi tiến trình **còn treo**
    (`CREATE_SUSPENDED`) — gán sau khi nó đã chạy là để hở một khoảng thời gian
    trong đó mã không tin cậy chạy **ngoài** mọi hạn mức."""
    try:
        win32job.AssignProcessToJobObject(h_job, int(h_process))
    except Exception as loi:  # noqa: BLE001
        raise LoiJobObject(f"khong gan duoc tien trinh vao job: {loi}") from loi


def giet(h_job, ma: int = 1) -> None:
    """Giết **cả cây** trong job. Dùng cho đường hết giờ."""
    try:
        win32job.TerminateJobObject(h_job, int(ma))
    except pywintypes.error:
        # ⚠️ `pywintypes.error` ke thua THANG `Exception`, KHONG phai `OSError`
        #    — bat `OSError` o day se hut. Duong don dep: job co the da dong.
        pass


def so_lieu(h_job) -> dict:
    """Số đo tiêu thụ của job: CPU (100 ns), đỉnh bộ nhớ, số tiến trình.

    ⭐ Đọc được **sau khi** tiến trình kết thúc, chừng nào handle job còn mở —
    đó là cách `bench/` lấy số RAM/CPU thật thay vì lấy mẫu bằng `psutil` và
    hy vọng bắt đúng lúc đỉnh.
    """
    ke_toan = win32job.QueryInformationJobObject(
        h_job, win32job.JobObjectBasicAccountingInformation)
    gioi_han = win32job.QueryInformationJobObject(
        h_job, win32job.JobObjectExtendedLimitInformation)
    return {
        "cpu_user_100ns": int(ke_toan.get("TotalUserTime", 0)),
        "cpu_kernel_100ns": int(ke_toan.get("TotalKernelTime", 0)),
        "so_tien_trinh_tong": int(ke_toan.get("TotalProcesses", 0)),
        "dinh_bo_nho_byte": int(gioi_han.get("PeakProcessMemoryUsed", 0)),
        "dinh_bo_nho_job_byte": int(gioi_han.get("PeakJobMemoryUsed", 0)),
    }


__all__ = ["BO_NHO_MAC_DINH_MB", "LoiJobObject", "SO_TIEN_TRINH_MAC_DINH",
           "gan", "giet", "so_lieu", "tao"]
