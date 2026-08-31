"""to_tien.py — cổng tự biết mình còn nằm dưới dịch vụ hay đã thành mồ côi.

## Vấn đề nó giải

Đo trên máy B 01/09, sau khi dừng vỏ bọc `nssm.exe` của `LTTLlmGateway`:

    + 0.0s   /health=200  Get-Service=Stopped   cong8299=26528
    +99.0s   /health=200  Get-Service=Paused    cong8299=26528

Tiến trình con **sống sót mồ côi**, vẫn giữ cổng, vẫn trả 200 — suốt 99 giây,
trong khi dịch vụ đã chết và không ai dựng nó dậy nữa. Người trực nhìn `/health`
thấy xanh và đi ngủ; hệ đang chờ sập mà không cảnh báo nào nổi.

⭐ Con mồ côi **biết được** điều đó. Nó không tự nhìn thấy mình, nhưng nó nhìn
   thấy một sự thật về thế giới bên ngoài: **tổ tiên `nssm.exe` của nó đã chết**.

## Ba cái bẫy, cả ba đều đã trả giá bằng một phép đo

**1. Phải là TỔ TIÊN, không phải CHA.** Cây thật là `nssm → python → python`.
   Cha trực tiếp của tiến trình phục vụ là một `python` khác, không phải NSSM.
   Neo vào cha trực tiếp thì mất đúng trường hợp cần bắt.

**2. Phải so PID + TÊN + GIỜ SINH, không chỉ PID.** Windows tái sử dụng PID sau
   một thời gian. `Get-Process -Id <ppid>` trả về *một thứ gì đó* không có nghĩa
   là cha ta còn sống — có thể là một tiến trình hoàn toàn khác vừa được cấp lại
   số đó. Một phép kiểm chỉ nhìn PID sẽ im lặng đúng lúc nó cần nói.

**3. Chụp tổ tiên MỘT LẦN lúc khởi động, đừng dò lại mỗi lần.** Sau khi tổ tiên
   chết, đường đi lên cây **không còn** — không dò lại được nữa. Phải nhớ từ lúc
   nó còn sống.

## ⛔ Không tự thoát

Mô-đun này chỉ **báo cáo**. Một tiến trình tự sát khi hiểu nhầm hoàn cảnh là một
lớp lỗi mới, và nó sẽ sát ngay giữa lúc đang phục vụ khách. Việc quyết định
thuộc về người trực, và `/health` cho họ dữ liệu để quyết.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys

log = logging.getLogger(__name__)

#: Tên tiến trình vỏ bọc dịch vụ. Đổi nó là mất khả năng phát hiện mồ côi.
VO_BOC = "nssm"


def _cay_len(pid: int, sau_toi_da: int = 8) -> list[dict]:
    """Chuỗi tổ tiên từ `pid` đi lên, mỗi nút gồm pid + tên + giờ sinh.

    Một lượt gọi PowerShell cho cả cây — gọi từng nút là N lần khởi động
    PowerShell, và mỗi lần mất ~0,3 s.
    """
    if sys.platform != "win32":
        return []
    ps = (
        f"$id = {pid}; $ra = @(); "
        f"for ($i = 0; $i -lt {sau_toi_da} -and $id -gt 0; $i++) {{ "
        "  $w = Get-CimInstance Win32_Process -Filter \"ProcessId=$id\" "
        "       -ErrorAction SilentlyContinue; "
        "  if (-not $w) { break }; "
        "  $ra += ('{0}|{1}|{2}' -f $w.ProcessId, $w.Name, "
        "          $w.CreationDate.ToString('yyyy-MM-ddTHH:mm:ss')); "
        "  $id = $w.ParentProcessId }; "
        "$ra -join [Environment]::NewLine"
    )
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                            "-Command", ps],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("khong doc duoc cay tien trinh: %s: %s", type(e).__name__, e)
        return []
    nut = []
    for d in (r.stdout or "").splitlines():
        p = d.strip().split("|")
        if len(p) == 3 and p[0].isdigit():
            nut.append({"pid": int(p[0]), "ten": p[1], "sinh": p[2]})
    return nut


class ToTien:
    """Nhớ tổ tiên `nssm.exe` lúc khởi động, rồi trả lời 'ta còn dưới dịch vụ?'"""

    def __init__(self) -> None:
        self.moc: dict | None = None
        self.ly_do_khong_theo_doi = ""
        cay = _cay_len(os.getpid())
        for nut in cay:
            if VO_BOC in nut["ten"].lower():
                self.moc = nut
                log.info("to tien dich vu: pid=%s %s sinh=%s",
                         nut["pid"], nut["ten"], nut["sinh"])
                return
        # Chạy tay lúc phát triển là trường hợp BÌNH THƯỜNG, không phải lỗi.
        # ⛔ Nhưng phải phân biệt nó với "đang dưới dịch vụ mà không tìm thấy" —
        #    gộp hai cái làm một thì một lỗi cấu hình thật sẽ đọc lên y hệt một
        #    lượt chạy tay, và không ai đi tìm.
        self.ly_do_khong_theo_doi = (
            f"khong thay {VO_BOC} trong {len(cay)} to tien "
            f"({' <- '.join(n['ten'] for n in cay) or 'khong doc duoc cay'})")
        log.info("khong chay duoi %s: %s", VO_BOC, self.ly_do_khong_theo_doi)

    def trang_thai(self) -> dict:
        if self.moc is None:
            return {"theo_doi": False, "ly_do": self.ly_do_khong_theo_doi,
                    "mo_coi": None}
        con = _cay_len(self.moc["pid"], sau_toi_da=1)
        # So CẢ BA. Xem bẫy #2 ở docstring: chỉ so PID là một phép kiểm sẽ im
        # lặng đúng lúc nó cần nói.
        song = bool(con) and (con[0]["ten"] == self.moc["ten"]
                              and con[0]["sinh"] == self.moc["sinh"])
        return {
            "theo_doi": True,
            "vo_boc_pid": self.moc["pid"],
            "vo_boc_sinh": self.moc["sinh"],
            "mo_coi": not song,
            **({} if song else {
                "canh_bao": (
                    "TIEN TRINH NAY DA MO COI: vo boc dich vu da chet nhung ta "
                    "van chay va van giu cong. Khong ai dung ta day neu ta chet. "
                    "Xu ly: dung tien trinh nay roi Start-Service."),
            }),
        }
