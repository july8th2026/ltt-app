"""Cho agent tự chạy lại sau khi khởi động máy — Scheduled Task ĐƯỢC NÂNG QUYỀN (Q99).

Ba lựa chọn trên Windows:

|                          | Admin lúc cài? | UAC mỗi lần chạy? | Trước đăng nhập? | DPAPI |
|--------------------------|----------------|-------------------|------------------|-------|
| Task (user, thường)      | không          | không             | không            | user  |
| **Task `/rl HIGHEST`** ← | **có (1 lần)** | **không**         | không            | user  |
| Service `/ru SYSTEM`     | có             | không             | có               | SYSTEM|

**Chọn Task `/rl HIGHEST` (Q99).** N3.3b ban đầu chọn task **không** admin vì Q95/
T1: đừng dạy khách bấm qua UAC. Nhưng đo trên máy thật (`N3_2_ENGINE.md` §V8):
xoay mật khẩu phiên RustDesk **đòi admin**. Điều khiển không giám sát bản chất
cần admin — N3.3b đã lường ("khi cần thì đổi kèm quyền admin"). Q99 chốt.

Chi tiết vì sao `/rl HIGHEST` (token admin của người dùng) chứ không `/ru SYSTEM`,
và vì sao nó **không** phá đánh đổi UAC/T1 của Q95 (chỉ một lần nâng quyền lúc
cài, không mỗi lần chạy; giữ ngữ cảnh DPAPI để đọc được khoá thiết bị) — ở
docstring của `lenh_tao_task`.

**Cái giá, có thật:** agent chỉ chạy **sau khi đăng nhập** (`onlogon`). Vào máy
trước lúc đăng nhập cần `/ru SYSTEM` — và giải bài toán DPAPI đổi ngữ cảnh — để
dành cho sau.

## Vì sao `schtasks` chứ không phải một thư viện

`schtasks.exe` có sẵn trong mọi bản Windows. Một thư viện Python để tạo task là
thêm một phụ thuộc **trên máy khách** — thứ phải đóng gói, và phải vá khi có
CVE. Ở đây đổi lại là phải tự lo việc trích dẫn dấu ngoặc, và đó chính là chỗ
loại code này hay hỏng: đường dẫn Windows có dấu cách, còn `schtasks` nhận lệnh
như **một chuỗi**.

Vì vậy phần dựng lệnh được tách thành hàm thuần và test kỹ, còn phần chạy chỉ là
một lớp mỏng gọi nó.
"""
from __future__ import annotations

import subprocess
import sys

#: Tên task. Có tiền tố để người mở Task Scheduler biết ngay nó của ai.
TASK_NAME = "LTTNexusAgent"


class ServiceError(Exception):
    """Không cài/gỡ được lịch chạy."""


def lenh_chay(python_exe: str, base_url: str, thu_muc: str = "") -> str:
    """Chuỗi lệnh mà task sẽ chạy.

    `schtasks /tr` nhận **một chuỗi**, nên đường dẫn có dấu cách phải được bọc
    ngoặc kép. Đây là chỗ hỏng kinh điển: máy của lập trình viên thường ở
    `C:\\Python`, còn máy khách ở `C:\\Program Files\\...`, nên lỗi chỉ xuất hiện
    trên máy khách và không bao giờ trên máy người viết.
    """
    phan = [f'"{python_exe}"', "-m", "nexus_agent", "run",
            "--url", f'"{base_url}"']
    if thu_muc:
        # `--dir` la tham so cua parser goc, phai dat TRUOC lenh con.
        phan = ([f'"{python_exe}"', "-m", "nexus_agent",
                 "--dir", f'"{thu_muc}"', "run", "--url", f'"{base_url}"'])
    return " ".join(phan)


def lenh_tao_task(chay: str, *, ten: str = TASK_NAME) -> list:
    """Tham số cho `schtasks /create`. Trả list, không trả chuỗi.

    List chứ không chuỗi: `subprocess` nhận list thì **không** đi qua shell, nên
    một đường dẫn chứa `&` hay `^` không thể biến thành lệnh khác. Đó là khác
    biệt giữa "trích dẫn cẩn thận" và "không có chỗ để tiêm".

    ## `/rl HIGHEST` — vì sao giờ CÓ (Q99), trong khi N3.3b cố ý KHÔNG

    N3.3b chọn task không-admin để tránh màn hình UAC mà kịch bản lừa đảo T1 lợi
    dụng. Nhưng đo trên máy thật (N3_2_ENGINE §V8): xoay mật khẩu phiên RustDesk
    (`--password`) **đòi quyền admin**. Điều khiển không giám sát bản chất cần
    admin, và N3.3b đã lường: "khi cần thì đổi kèm quyền admin, không phải một cờ
    nhỏ." Q99 chốt đường đó.

    Chọn `/rl HIGHEST` (chạy bằng token admin của **chính người dùng**) thay vì
    `/ru SYSTEM`, có chủ ý:

    * **Không hỏi UAC mỗi lần chạy.** Task Scheduler nâng quyền một task HIGHEST
      tự động; khách chỉ thấy UAC **một lần lúc CÀI** (tạo task HIGHEST cần admin)
      — đúng bằng lúc cài RustDesk. Q99: né admin *mỗi lần chạy*, không né lúc cài.
    * **DPAPI khớp.** Khoá thiết bị mã hoá bằng DPAPI theo ngữ cảnh người dùng
      (`keystore.py`). Chạy `/ru SYSTEM` sẽ đổi ngữ cảnh sang SYSTEM và không đọc
      nổi khoá đã ghi lúc enroll (dưới người dùng) — một lỗi chỉ hiện trên máy
      thật. `/rl HIGHEST` giữ ngữ cảnh người dùng nên khoá vẫn đọc được.

    Cái giá (như N3.3b ghi): chỉ chạy **sau khi đăng nhập** (`onlogon`). Vào máy
    trước lúc đăng nhập cần `/ru SYSTEM` + giải bài toán DPAPI — để dành.
    """
    return ["schtasks", "/create", "/tn", str(ten), "/tr", str(chay),
            "/sc", "onlogon",
            # Q99: chay bang token admin cua nguoi dung -> --password chay duoc,
            # khong hoi UAC moi lan (chi luc cai). Xem docstring.
            "/rl", "HIGHEST",
            # Ghi de neu da co, de cai lai khong phai go tay truoc.
            "/f"]


def lenh_xoa_task(*, ten: str = TASK_NAME) -> list:
    return ["schtasks", "/delete", "/tn", str(ten), "/f"]


def lenh_kiem_task(*, ten: str = TASK_NAME) -> list:
    return ["schtasks", "/query", "/tn", str(ten)]


def _chay(argv: list, *, runner=None) -> tuple:
    """Trả `(ma_thoat, dau_ra)`. `runner` để test không đụng máy thật."""
    if runner is not None:
        return runner(argv)
    if not sys.platform.startswith("win"):
        raise ServiceError("lich chay tu dong chi ho tro Windows")
    ket = subprocess.run(argv, capture_output=True, text=True, check=False)
    return ket.returncode, (ket.stdout or "") + (ket.stderr or "")


def cai(python_exe: str, base_url: str, *, thu_muc: str = "",
        ten: str = TASK_NAME, runner=None) -> None:
    ma, ra = _chay(lenh_tao_task(lenh_chay(python_exe, base_url, thu_muc),
                                 ten=ten), runner=runner)
    if ma != 0:
        raise ServiceError(f"khong tao duoc lich chay (ma {ma}): {ra.strip()[:200]}")


def go(*, ten: str = TASK_NAME, runner=None) -> bool:
    """Gỡ lịch chạy. Trả False nếu vốn không có — **không** coi là lỗi.

    Gỡ một thứ không tồn tại là kết quả mong muốn, không phải sự cố. Ném ở đây
    sẽ làm đường gỡ cài đặt dừng giữa chừng và để lại máy ở trạng thái nửa vời.
    """
    ma, _ra = _chay(lenh_xoa_task(ten=ten), runner=runner)
    return ma == 0


def da_cai(*, ten: str = TASK_NAME, runner=None) -> bool:
    ma, _ra = _chay(lenh_kiem_task(ten=ten), runner=runner)
    return ma == 0


__all__ = ["ServiceError", "TASK_NAME", "cai", "da_cai", "go", "lenh_chay",
           "lenh_kiem_task", "lenh_tao_task", "lenh_xoa_task"]
