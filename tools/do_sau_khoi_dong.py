"""do_sau_khoi_dong.py — N7 + N9: đo máy A NGAY SAU khi khởi động lại.

    python tools/do_sau_khoi_dong.py --ra tmp/sau_khoi_dong.json

## ⛔ CHỈ CÓ MỘT LẦN

Nhật ký khởi động, thứ tự dịch vụ lên, và "bao lâu tới lúc `/health/ready` xanh"
chỉ đọc được **ngay sau một lần boot**. Chạy muộn thì nhật ký vẫn còn nhưng
trạng thái đã bị các lượt khởi động lại thủ công che mất.

⇒ Chạy nó **trước khi làm bất cứ việc gì khác** sau khi máy lên.

## Nó trả lời gì

`reports/06` §12 dựng bảng F05 *"nếu máy A khởi động lại thì sao"* **từ cấu
hình**, không từ quan sát — và đã ghi rõ giới hạn đó. Tệp này biến suy luận
thành số đo:

| Câu hỏi | Suy ra từ cấu hình | Tệp này đo |
|---|---|---|
| Dịch vụ có tự lên? | `StartType=Automatic` | **có lên thật không** |
| Mất bao lâu? | không biết | **giây, từ boot tới `/health/ready`** |
| Thứ tự có đúng? | `DependsOn` | **thứ tự thật trong nhật ký** |
| `FAILURE_ACTIONS` có phải đỡ? | vừa bật 01/09 | **có lần nào phải dựng dậy không** |
| Job dở dang / tiền treo? | lease hết hạn (`test_215`) | **số job `running` mồ côi** |

## ⛔ Không kết luận từ sự vắng mặt

Nhật ký không có dòng lỗi **không** chứng minh mọi thứ tốt — có thể ta lọc sai,
có thể log chưa flush. Mỗi phép ở đây ghi rõ **đã tìm gì** để người đọc biết
phạm vi, thay vì đọc một dấu tích xanh trống rỗng.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DICH_VU = ("cloudflared", "LTTStudioWeb", "LTTStudioWorker",
           "LTTStudioVoice", "LTTStudioCodex")


def ps(lenh: str, timeout: int = 90) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-Command", lenh], capture_output=True, text=True,
                       timeout=timeout)
    return (r.stdout or "").strip()


def ghi(ra: dict, khoa: str, gt) -> None:
    ra[khoa] = gt
    print(f"  {khoa:<26} {gt if not isinstance(gt, (list, dict)) else json.dumps(gt, ensure_ascii=False)[:150]}")


def main() -> int:
    p = argparse.ArgumentParser(description="Do may A ngay sau khoi dong.")
    p.add_argument("--ra", type=Path, default=Path("tmp/sau_khoi_dong.json"))
    a = p.parse_args()
    ra: dict = {"luc": time.strftime("%Y-%m-%d %H:%M:%S")}

    print("== 1. May len tu bao gio ==")
    boot = ps("(Get-CimInstance Win32_OperatingSystem).LastBootUpTime."
              "ToString('yyyy-MM-ddTHH:mm:ss')")
    ghi(ra, "boot_luc", boot)
    tuoi = ps("[int]((Get-Date) - (Get-CimInstance Win32_OperatingSystem)"
              ".LastBootUpTime).TotalMinutes")
    ghi(ra, "phut_tu_luc_boot", tuoi)
    if tuoi.isdigit() and int(tuoi) > 60:
        print("  ⚠️ May da len hon mot tieng. Cac so 'bao lau toi khi xanh' ben")
        print("     duoi VAN doc duoc tu nhat ky, nhung trang thai hien tai co")
        print("     the da bi cac luot khoi dong lai thu cong che mat.")

    print("\n== 2. Nam dich vu co TU LEN khong (N7) ==")
    tt = {}
    for n in DICH_VU:
        tt[n] = ps(f"(Get-Service {n} -ErrorAction SilentlyContinue).Status") or "KHONG CO"
    ghi(ra, "trang_thai_dich_vu", tt)
    ghi(ra, "tat_ca_Running", all(v == "Running" for v in tt.values()))

    print("\n== 3. Thu tu len va thoi diem, tu nhat ky Windows (N9) ==")
    # ⚠️ Cần Administrator để đọc log System. Không có quyền thì NÓI RA, đừng
    #    trả một danh sách rỗng — rỗng đọc lên y hệt "không có sự kiện nào".
    sk = ps(
        "try { Get-WinEvent -FilterHashtable @{LogName='System';"
        "ProviderName='Service Control Manager';StartTime=(Get-CimInstance "
        "Win32_OperatingSystem).LastBootUpTime} -ErrorAction Stop | "
        "Where-Object { $_.Message -match 'LTTStudio|cloudflared' } | "
        "Sort-Object TimeCreated | ForEach-Object { "
        "$_.TimeCreated.ToString('HH:mm:ss') + ' | ' + ($_.Message -replace "
        "'\\s+',' ') } } catch { 'LOI: ' + $_.Exception.Message }",
        timeout=180)
    dong = [d.strip() for d in sk.splitlines() if d.strip()][:40]
    if not dong:
        ghi(ra, "nhat_ky_khoi_dong", "KHONG DOC DUOC (can Administrator) "
                                     "-- KHONG phai 'khong co su kien nao'")
        print("   ⚠️ ĐÂY LÀ PHẦN CHỈ ĐỌC ĐƯỢC MỘT LẦN. Lấy nó bằng LocalSystem:")
        print("      NexusAgent trên máy A chạy `LocalSystem`, và node của máy A là")
        print("      286e1065-8eaa-4419-8681-2af26090578d. Gọi `exec` qua controller")
        print("      https://192.168.2.17:9444 (token: %USERPROFILE%\\.nexus\\")
        print("      claude-code.token, header `X-Nexus-Protocol: 1`) rồi chạy lại")
        print("      chính tệp này. Xem `Ket_noi.md` trên Desktop.")
    elif dong[0].startswith("LOI:"):
        ghi(ra, "nhat_ky_khoi_dong", dong[0])
    else:
        ra["nhat_ky_khoi_dong"] = dong
        for d in dong[:14]:
            print("   ", d[:120])
        # `FAILURE_ACTIONS` phải đỡ = dịch vụ đã chết một lần rồi được dựng dậy.
        do = [d for d in dong if "terminated unexpectedly" in d
              or "restart the service" in d.lower()]
        ghi(ra, "co_lan_phai_dung_day", bool(do))
        if do:
            print("   ⚠️ CO dich vu phai nho FAILURE_ACTIONS dung day:")
            for d in do[:5]:
                print("     ", d[:120])

    print("\n== 4. Bao lau toi khi /health/ready xanh ==")
    t0 = time.monotonic()
    xanh = None
    for _ in range(120):
        r = ps("try { (Invoke-RestMethod http://127.0.0.1:8100/health/ready "
               "-TimeoutSec 5).status } catch { 'chua' }")
        if r == "ready":
            xanh = round(time.monotonic() - t0, 1)
            break
        time.sleep(2)
    ghi(ra, "giay_cho_health_ready", xanh if xanh is not None else "QUA 240s")

    print("\n== 5. Cong tu khai co mo coi khong ==")
    dd = ps("try { (Invoke-RestMethod http://127.0.0.1:8100/health/ready "
            "-TimeoutSec 10).duoi_dich_vu | ConvertTo-Json -Compress } "
            "catch { 'khong goi duoc' }")
    ghi(ra, "duoi_dich_vu", dd)

    print("\n== 6. Job do dang / tien treo ==")
    print("  (chay bang cau hep vi can app.env:)")
    print("    powershell -File .\\setup\\chay_voi_env.ps1 -Viec soi-su-co")

    print("\n== 7. May B co bi anh huong khong ==")
    b = ps("try { (Test-NetConnection 192.168.2.66 -Port 8299 "
           "-InformationLevel Quiet -WarningAction SilentlyContinue) } "
           "catch { $false }")
    ghi(ra, "may_B_cong_8299_song", b)
    print("  (may B la MAY KHAC -- no khong reboot theo may A)")

    a.ra.parent.mkdir(parents=True, exist_ok=True)
    a.ra.write_text(json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nDA LUU: {a.ra}")

    thieu = [k for k in ("tat_ca_Running", "giay_cho_health_ready")
             if not ra.get(k) or ra.get(k) == "QUA 240s"]
    if thieu:
        print(f"⚠️ CHUA DAT: {thieu}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
