"""Cho agent tự chạy lại sau khi khởi động máy — bằng Scheduled Task, KHÔNG service.

Hai đường trên Windows, và chúng đánh đổi ngược nhau:

|                     | Cần admin? | Chạy trước khi đăng nhập? |
|---------------------|------------|---------------------------|
| Windows Service     | **có**     | có                        |
| Scheduled Task (user)| **không** | không                     |

Chọn **Scheduled Task theo người dùng**, và lý do gắn thẳng với Q95: bản cài
chưa ký mã đã làm Windows cảnh báo rồi; thêm một lời xin quyền admin nữa là dựng
đúng màn hình mà kẻ lừa đảo T1 cần khách bấm qua. Bỏ được UAC là bỏ được một nửa
kịch bản đó.

**Cái giá, và nó có thật:** agent chỉ chạy khi người dùng đã đăng nhập. Máy đang
ở màn hình khoá thì không điều khiển được. Với v1 — khách tự ghép máy của chính
mình để dùng — đó là đánh đổi đúng. Khi nào cần vào máy trước lúc đăng nhập thì
phải đổi sang service, và **đổi kèm quyền admin**, không phải một cờ nhỏ.

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
    """
    return ["schtasks", "/create", "/tn", str(ten), "/tr", str(chay),
            # ONLOGON: chay khi nguoi dung nay dang nhap. Khong /ru SYSTEM va
            # khong /rl HIGHEST — ca hai deu keo theo yeu cau quyen admin.
            "/sc", "onlogon",
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
