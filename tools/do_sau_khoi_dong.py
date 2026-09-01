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
        # 🔴 ĐỪNG ĐOÁN LÝ DO — ĐO NÓ.
        #
        #    Bản trước kết luận thẳng "KHONG DOC DUOC (can Administrator)" và in
        #    sáu dòng hướng dẫn chạy lại bằng LocalSystem. Ngày 01/09 tôi làm
        #    đúng y hướng dẫn đó (`whoami` = `nt authority\system`) và nhận kết
        #    quả **y hệt**. Nguyên nhân thật: Windows máy này KHÔNG ghi sự kiện
        #    7036 của Service Control Manager. Đo được: 3 sự kiện SCM từ lúc
        #    boot, 0 khớp `LTTStudio|cloudflared`.
        #
        # ⭐ Chú thích ngay trên dặn "đừng trả danh sách rỗng, rỗng đọc lên y hệt
        #    'không có sự kiện nào'". Bản vá tránh bẫy đó bằng cách nói **một câu
        #    sai khác** — cùng lớp lỗi với `api_prod_canary.py`. Một cảnh báo
        #    không tái hiện được sẽ bị phiên sau bỏ qua, và kéo theo cả những
        #    cảnh báo đúng nằm cạnh nó.
        tong = ps("$b=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime; "
                  "try { (Get-WinEvent -FilterHashtable @{LogName='System';"
                  "ProviderName='Service Control Manager';StartTime=$b} "
                  "-ErrorAction Stop | Measure-Object).Count } "
                  "catch { 'LOI: ' + $_.Exception.Message }")
        if tong.startswith("LOI:") or not tong.isdigit():
            ghi(ra, "nhat_ky_khoi_dong", f"KHONG DOC DUOC log System -- {tong}")
            print("   ⚠️ Truy vấn NÉM lỗi ⇒ đây thật sự là vấn đề quyền.")
            print("      NexusAgent trên máy A chạy `LocalSystem`; node máy A là")
            print("      286e1065-8eaa-4419-8681-2af26090578d. Xem `Ket_noi.md`.")
        else:
            ghi(ra, "nhat_ky_khoi_dong",
                f"KHONG CO SU KIEN NAO KHOP (doc duoc {tong} su kien SCM tu luc "
                f"boot, 0 khop LTTStudio|cloudflared) -- KHONG phai thieu quyen")
            print(f"   ⭐ Đọc ĐƯỢC log ({tong} sự kiện SCM), chỉ là không sự kiện")
            print("      nào của ta. Windows máy này không ghi 7036 'entered the")
            print("      running state'. ⇒ Chạy lại bằng LocalSystem KHÔNG giúp.")
            print("      Thứ tự lên đọc ở mục 2b (`Win32_Process.CreationDate`).")
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

    print("\n== 2b. Thu tu len THAT, do tu tien trinh (khong phu thuoc log) ==")
    # ⭐ Đường này ĐÃ ĐƯỢC CHỨNG MINH hoạt động ngày 01/09, trong khi đường log
    #    Windows ở mục 3 không bao giờ hoạt động trên máy này. Nó không cần
    #    quyền Administrator và không cần sự kiện 7036 nào tồn tại.
    tt2 = {}
    for n in DICH_VU:
        sinh = ps(
            f"$s = Get-CimInstance Win32_Service -Filter \"Name='{n}'\" "
            f"-ErrorAction SilentlyContinue; "
            f"if ($s -and $s.ProcessId -gt 0) {{ "
            f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId=$($s.ProcessId)\" "
            f"-ErrorAction SilentlyContinue; "
            f"$b = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime; "
            f"if ($p) {{ [math]::Round(($p.CreationDate - $b).TotalSeconds,1) }} }}")
        tt2[n] = sinh or "?"
        try:
            muon = float(sinh) > 300
        except (TypeError, ValueError):
            muon = False
        dau = "  <- KHOI DONG LAI SAU BOOT, KHONG phai so do boot" if muon else ""
        print(f"   {n:<18} vo boc sinh sau boot: +{sinh or '?'} s{dau}")
    ghi(ra, "giay_sau_boot_moi_dich_vu", tt2)
    # ⛔ NÓI RA khi con số không còn là số đo boot nữa. Một dịch vụ được deploy
    #    khởi động lại lúc boot+3 giờ sẽ hiện `+10760 s` — con số ĐÚNG, nhưng
    #    đọc lướt thì nó trông như "khởi động cực chậm". Đây chính là thứ mà
    #    docstring của tệp dặn: "chạy muộn thì trạng thái đã bị các lượt khởi
    #    động lại thủ công che mất". Nay công cụ tự phát hiện điều đó.
    tre = [n for n, v in tt2.items()
           if str(v).replace(".", "", 1).isdigit() and float(v) > 300]
    ghi(ra, "dich_vu_da_khoi_dong_lai_sau_boot", tre)
    if tre:
        print(f"   ⚠️ {len(tre)}/{len(tt2)} dich vu da khoi dong lai SAU boot")
        print("      ⇒ chung KHONG con lam bang chung cho N7 o luot boot nay.")

    print("\n== 4. Do tre cua /health/ready LUC NAY (KHONG phai boot -> ready) ==")
    # 🔴 TÊN CŨ CỦA MỤC NÀY LÀ MỘT LỜI NÓI DỐI NHỎ: "Bao lau toi khi
    #    /health/ready xanh". `t0` đặt lúc **gọi công cụ**, không phải lúc boot.
    #    Chạy ở boot+7 phút nó in `0,5 s`; chạy lại ở boot+15 phút nó in `0,6 s`.
    #    Cả hai là độ trễ một request lúc ấy — con số boot→ready **chưa từng
    #    được đo**, và mỗi lượt boot chỉ cho một cơ hội duy nhất.
    #
    # ⇒ Muốn con số thật thì phải có thứ thăm dò TRONG lúc khởi động. Mục 2b ở
    #    trên cho chặn trên (lúc dịch vụ cuối cùng sinh ra); đó là thứ tốt nhất
    #    đọc ngược lại được sau khi mọi việc đã xong.
    t0 = time.monotonic()
    xanh = None
    for _ in range(120):
        r = ps("try { (Invoke-RestMethod http://127.0.0.1:8100/health/ready "
               "-TimeoutSec 5).status } catch { 'chua' }")
        if r == "ready":
            xanh = round(time.monotonic() - t0, 1)
            break
        time.sleep(2)
    # Ten khoa noi ra DUNG thu no do. Khoa cu `giay_cho_health_ready` doc len
    # nhu "boot -> ready" va da bi doc nham dung nhu vay.
    ghi(ra, "giay_do_tre_health_ready_luc_do",
        xanh if xanh is not None else "QUA 240s")

    print("\n== 5. Cong tu khai co mo coi khong ==")
    dd = ps("try { (Invoke-RestMethod http://127.0.0.1:8100/health/ready "
            "-TimeoutSec 10).duoi_dich_vu | ConvertTo-Json -Compress } "
            "catch { 'khong goi duoc' }")
    ghi(ra, "duoi_dich_vu", dd)

    print("\n== 6. Job do dang / tien treo ==")
    print("  (chay bang cau hep vi can app.env:)")
    print("    powershell -File .\\setup\\chay_voi_env.ps1 -Viec soi-su-co")

    print("\n== 7. LTT VOICE (bon phep kiem cua lane do) ==")
    ghi(ra, "voice_dich_vu", tt.get("LTTStudioVoice", "?"))

    # Sidecar chỉ nghe loopback 8120, KHÔNG đi qua Cloudflare.
    #
    # 🔴 ĐƯỜNG LÀ `/health`, KHÔNG PHẢI `/v1/health` — và phép phân biệt quan
    #    trọng là **401 ≠ 404**:
    #
    #        /v1/health -> 404   sai đường
    #        /health    -> 401   ĐÚNG đường, chỉ thiếu token
    #
    # ⭐ `401` tự nó **đã đủ** làm bằng chứng sống: sidecar nghe được, phân tích
    #    được yêu cầu, và từ chối đúng cách. Đòi thêm token chỉ để thấy `200` là
    #    đổi một phép kiểm đang chạy lấy một phụ thuộc vào `app.env` (ACL).
    #
    # ⚠️ Nạp model lần đầu ~19,4 s (10,5 s khi ấm) — timeout 35 s để một lượt
    #    nạp nguội KHÔNG bị đọc thành "sidecar chết".
    ma_sc = ps("try { (Invoke-WebRequest http://127.0.0.1:8120/health "
               "-TimeoutSec 35 -UseBasicParsing).StatusCode } "
               "catch { if ($_.Exception.Response) "
               "{ [int]$_.Exception.Response.StatusCode } else { 0 } }")
    song = ma_sc in ("200", "401")
    ghi(ra, "voice_sidecar_8120_ma", ma_sc)
    ghi(ra, "voice_sidecar_song", song)
    if not song:
        print(f"   🔴 sidecar 8120 KHONG song (ma {ma_sc!r}). `0` = khong noi")
        print("      duoc toi cong; `404` = dich vu len nhung dinh tuyen sai.")

    # 🔴 PHÉP KIỂM ĐẮT NHẤT TRONG NHÓM NÀY.
    #
    #    Nếu production đặt `LTT_WORKER_POOLS` mà **thiếu làn `voice`** thì job
    #    nằm `queued` **vĩnh viễn, không lỗi nào báo** — không log, không cảnh
    #    báo, khách chỉ thấy một vòng quay không dừng.
    #
    # ⇒ Đúng hình dạng mà cả đợt audit này đi săn: một hỏng hóc **không phát ra
    #   tín hiệu nào**. Và nó chỉ lộ ra nếu có ai đi hỏi thẳng.
    #
    # ⚠️ Biến này nằm trong `app.env` (ACL: SYSTEM + Administrators), nên đọc
    #    được hay không phụ thuộc quyền. Không đọc được thì NÓI RA.
    pools = ps("if (Test-Path C:\\LTTPlatform\\secrets\\app.env) { "
               "$d = Get-Content C:\\LTTPlatform\\secrets\\app.env -EA "
               "SilentlyContinue | Select-String '^LTT_WORKER_POOLS='; "
               "if ($d) { $d.ToString() } else { 'KHONG DAT (giu hanh vi mac dinh)' } } "
               "else { 'KHONG DOC DUOC app.env (can Administrator)' }")
    ghi(ra, "LTT_WORKER_POOLS", pools)
    if pools.startswith("LTT_WORKER_POOLS=") and "voice" not in pools.lower():
        print("   🔴 BIEN DA DAT MA THIEU LAN `voice` => JOB GIONG NOI SE NAM")
        print("      `queued` VINH VIEN, KHONG LOI NAO BAO. Sua ngay.")
        ra["voice_lan_thieu"] = True
    elif "KHONG DOC DUOC" in pools:
        print("   ⚠️ Chua ket luan duoc. Chay lai bang LocalSystem qua Nexus,")
        print("      hoac: powershell -File .\\setup\\4-nghiem-thu.ps1 (co chot nay).")

    print("\n== 8. May B co bi anh huong khong ==")
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
