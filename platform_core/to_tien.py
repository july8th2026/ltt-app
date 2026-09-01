"""to_tien.py — dịch vụ tự biết mình còn nằm dưới NSSM hay đã thành mồ côi.

Bản của **máy A**. Xem `llm_gateway/to_tien.py` cho bản của máy B.

## ⚠️ VÌ SAO CÓ HAI BẢN, VÀ ĐỪNG "GỘP LẠI CHO GỌN"

`llm_gateway` được deploy **sang máy B**, nơi **không có `platform_core`**. Nó
mang theo `render_gateway` và chỉ hai gói đó. Một lệnh `import platform_core`
trong `llm_gateway` sẽ chạy tốt trên máy A và **vỡ khi deploy** — và vỡ ở lúc
khởi động dịch vụ, tức lúc tệ nhất.

⇒ Trùng lặp ở đây là **hệ quả của ranh giới triển khai**, không phải cẩu thả.
  `test_379` chốt hai bản giữ **cùng một hợp đồng**, nên chúng không âm thầm
  trôi khỏi nhau.

## Vấn đề nó giải

Đo trên máy B 01/09, sau khi dừng vỏ bọc `nssm.exe`: tiến trình con **sống sót
mồ côi**, vẫn giữ cổng, `/health` vẫn trả **200** — suốt 99 giây, trong khi
`Get-Service` nói `Stopped` và **không ai dựng nó dậy nữa**.

Máy A đo 01/09 có **cùng lỗ**: năm dịch vụ đều `Automatic` và NSSM có
`AppExit=Restart` (con chết thì dựng lại), nhưng **không dịch vụ nào có
`FAILURE_ACTIONS` của SCM** — vỏ bọc chết thì không ai dựng dậy. Và ở đây nó nằm
trên máy **đang phục vụ khách thật**: trang web vẫn trả lời, `Get-Service` nói
`Stopped`.

## Ba cái bẫy, cả ba đã trả giá bằng một phép đo trên máy B

1. **Phải là TỔ TIÊN, không phải CHA.** Cây thật là `nssm → python → python`.
   Neo vào cha trực tiếp thì mất đúng trường hợp cần bắt.
2. **Phải so PID + TÊN + GIỜ SINH.** Windows tái sử dụng PID; một phép kiểm chỉ
   nhìn PID sẽ im lặng đúng lúc nó cần nói.
3. **Chụp tổ tiên MỘT LẦN lúc khởi động.** Sau khi nó chết thì đường đi lên cây
   không còn — dò lại là muộn.

## ⛔ Không tự thoát

Chỉ **báo cáo**. Một tiến trình tự sát khi hiểu nhầm hoàn cảnh là một lớp lỗi
mới, và nó sẽ sát ngay giữa lúc đang phục vụ khách.
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
    """Chuỗi tổ tiên từ `pid` đi lên: pid + tên + giờ sinh.

    Một lượt gọi PowerShell cho cả cây — gọi từng nút là N lần khởi động
    PowerShell, mỗi lần ~0,3 s.
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
        # ⛔ Nhưng phải phân biệt với "đang dưới dịch vụ mà không tìm thấy" —
        #    gộp hai cái thì một lỗi cấu hình thật sẽ đọc lên y hệt một lượt
        #    chạy tay, và không ai đi tìm.
        self.ly_do_khong_theo_doi = (
            f"khong thay {VO_BOC} trong {len(cay)} to tien "
            f"({' <- '.join(n['ten'] for n in cay) or 'khong doc duoc cay'})")
        log.info("khong chay duoi %s: %s", VO_BOC, self.ly_do_khong_theo_doi)

    def trang_thai(self) -> dict:
        if self.moc is None:
            return {"theo_doi": False, "ly_do": self.ly_do_khong_theo_doi,
                    "mo_coi": None}
        con = _cay_len(self.moc["pid"], sau_toi_da=1)
        # So CẢ BA — xem bẫy #2 ở docstring.
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


_TO_TIEN: ToTien | None = None


def khoi_tao() -> None:
    """Chụp tổ tiên. Gọi MỘT LẦN lúc ứng dụng khởi động.

    ⛔ **KHÔNG lười khởi tạo.** Một `if _TO_TIEN is None: _TO_TIEN = ToTien()`
       trong `trang_thai()` trông vô hại và **hỏng đúng lúc cần nhất**: nếu lượt
       gọi đầu tiên rơi vào *sau* khi vỏ bọc đã chết thì nó chụp được một cây
       **không có** `nssm`, kết luận "đang chạy tay", và im lặng **mãi mãi** —
       đúng sự cố nó sinh ra để phát hiện.

       (Tôi đã viết đúng cái bẫy đó ở bản đầu của tệp này, ngay dưới một chú
       thích cảnh báo về nó.)

    ⛔ Cũng KHÔNG chụp lúc `import`: nó tốn một lượt gọi PowerShell (~0,3 s) cho
       mọi tiến trình chạm tới `platform_core`, kể cả từng lượt chạy test.
    """
    global _TO_TIEN
    if _TO_TIEN is None:
        _TO_TIEN = ToTien()


def trang_thai() -> dict:
    """Trạng thái đã chụp. Chưa `khoi_tao()` thì NÓI RA, không tự chụp muộn."""
    if _TO_TIEN is None:
        return {"theo_doi": False, "mo_coi": None,
                "ly_do": "chua goi khoi_tao() luc khoi dong ung dung"}
    return _TO_TIEN.trang_thai()
