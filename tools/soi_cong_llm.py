"""soi_cong_llm.py — đối chiếu HAI nguồn sự thật về cổng LLM trên máy B.

    python tools/soi_cong_llm.py               # đọc, in bảng, trả mã thoát
    python tools/soi_cong_llm.py --im          # chỉ nói khi có gì đó lệch

## ⛔ VÌ SAO KHÔNG PHẢI "THÊM MỘT TRƯỜNG VÀO `/health`"

Đo 01/09 trên máy B. Dừng vỏ bọc `nssm.exe` của `LTTLlmGateway`:

    + 0.0s   /health=200  Get-Service=Stopped   cong8299=26528
    +62.9s   /health=200  Get-Service=Paused    cong8299=26528
    +99.0s   /health=200  Get-Service=Paused    cong8299=26528

Tiến trình con **sống sót mồ côi**, vẫn giữ cổng, vẫn trả 200 — suốt 99 giây,
trong khi dịch vụ đã chết và `FAILURE_ACTIONS` của SCM không giành lại được cổng.

🔴 Không sửa được bằng cách làm `/health` thông minh hơn. `/health` **do chính
   con mồ côi phục vụ**; một endpoint sức khoẻ được phục vụ bởi thứ cần kiểm tra
   thì vĩnh viễn không nói được *"tôi là tiến trình không nên tồn tại"*. Nó
   không nói dối — nó thành thật báo cáo về một tiến trình thật sự khoẻ, chỉ là
   tiến trình đó lẽ ra không nên đang chạy.

⇒ Lớp lỗi này chỉ lộ ra khi **hai nguồn độc lập** không khớp:

      nguồn 1  `/health`      — do TIẾN TRÌNH tự nói
      nguồn 2  `Get-Service`  — do WINDOWS nói

  Đo một nguồn thì không bao giờ thấy, dù đo kỹ đến đâu. Đây không phải chuyện
  "kiểm cho chắc"; nó là chuyện **số nguồn**.

## Đọc kết quả

| /health | Get-Service | nghĩa |
|---|---|---|
| 200 | Running | lành |
| 200 | **không Running** | 🔴 **MỒ CÔI** — health xanh giả, chờ sập |
| ✗ | Running | đang khởi động, hoặc cổng treo |
| ✗ | không Running | chết thật, và ít nhất nó *nói* là chết |

Hàng thứ hai là hàng đắt nhất: hệ thống trông khoẻ, không cảnh báo nào nổi, và
tiến trình đang phục vụ **không có ai dựng dậy** nếu nó chết.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Node máy B trong LTT Nexus. Xem `Ket_noi.md` trên Desktop và CLAUDE.md.
NODE_B = "f8b24d88-6e3e-4719-8143-d5e83f68ed82"
NEXUS = f"https://192.168.2.17:9444/api/v1/nodes/{NODE_B}/proxy/api/v1/exec"

LANH, LECH, KHONG_DO_DUOC = 0, 1, 2


#: Phán xử tách khỏi phần gọi mạng, để chốt được bằng test mà không cần máy B.
#:
#: ⭐ Vì sao đáng tách: `LANH` chỉ có nghĩa nếu công cụ **có khả năng** trả
#:    `LECH`. Tối 31/08 một đồng hồ đọc sai tên trường đã cho ra một dãy số
#:    trông hoàn hảo trong khi nó không đo gì cả. Một hàm thuần thì chứng minh
#:    được cả hai chiều bằng dữ liệu tổng hợp, không cần dựng lại sự cố.
def phan_xu(health: str, gateway: str) -> tuple[int, str]:
    """(mã thoát, nhãn) từ hai nguồn. Xem bảng ở docstring đầu tệp."""
    khoe = health == "200"
    chay = gateway == "Running"
    if khoe and chay:
        return LANH, "lanh"
    if khoe and not chay:
        # Hàng đắt nhất: trông khoẻ, không cảnh báo nào nổi, và tiến trình đang
        # phục vụ không có ai dựng dậy nếu nó chết.
        return LECH, "xanh-gia"
    if not khoe and chay:
        return LECH, "dang-khoi-dong-hoac-treo"
    return LECH, "chet-that"


def _token_nexus() -> str:
    """Token điều khiển Nexus. Ưu tiên đường dẫn khai tường minh.

    ⛔ `Path.home()` KHÔNG DÙNG ĐƯỢC KHI CHẠY THEO LỊCH, và đó là lý do biến môi
       trường này tồn tại. Một Scheduled Task chạy bằng `SYSTEM` có
       `USERPROFILE` = `C:\\Windows\\system32\\config\\systemprofile`, nơi không
       có tệp token nào. Công cụ khi đó trả `KHONG_DO_DUOC` — **thành thật**,
       nhưng vô dụng: nó chạy mỗi 15 phút để nói rằng nó không đo được.

    ⭐ Đây chính là hình dạng của khuyết tật P08 F-07. Công cụ đã tồn tại, đã có
       `test_370` chốt phán xử của nó, và **không ai chạy nó** — không task, không
       vòng bảo trì, không caller nào ngoài phép kiểm. Một bộ dò không ai chạy
       giảm nhẹ được **0**; năng lực có mà chốt kiểm soát thì không.
    """
    from os import environ
    duong = environ.get("LTT_NEXUS_TOKEN_FILE", "").strip()
    p = Path(duong) if duong else Path.home() / ".nexus" / "claude-code.token"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def _tren_may_b(lenh: str, tok: str, timeout: int = 60) -> str | None:
    """Chạy một lệnh đọc trên máy B. None = không hỏi được (KHÁC với 'hỏng')."""
    than = json.dumps({"command": lenh, "shell": "powershell",
                       "reason": "soi_cong_llm: doi chieu hai nguon"}).encode()
    yc = urllib.request.Request(
        NEXUS, data=than, method="POST",
        headers={"Content-Type": "application/json",
                 "X-Nexus-Protocol": "1", "Authorization": f"Bearer {tok}",
                 "User-Agent": "ltt-soi/1.0"})
    import ssl
    # Nexus dùng chứng chỉ tự ký trong LAN; đây là kênh nội bộ đã có bearer.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(yc, timeout=timeout, context=ctx) as r:
            d = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            OSError, ValueError) as e:
        print(f"  [!] khong hoi duoc may B: {type(e).__name__}: {e}")
        return None
    if d.get("error"):
        print(f"  [!] Nexus tra loi: {json.dumps(d['error'])[:200]}")
        return None
    return (d.get("data") or {}).get("stdout", "")


def main() -> int:
    p = argparse.ArgumentParser(
        description="Doi chieu /health voi Get-Service tren may B.")
    p.add_argument("--im", action="store_true",
                   help="chi in khi co gi do lech (hop de chay theo lich)")
    a = p.parse_args()

    tok = _token_nexus()
    if not tok:
        print("KHONG CO TOKEN NEXUS (~/.nexus/claude-code.token)")
        return KHONG_DO_DUOC

    # Một lượt gọi lấy CẢ HAI nguồn, để chúng nói về CÙNG một khoảnh khắc.
    # Hai lượt gọi cách nhau vài giây là hai ảnh chụp khác nhau, và đúng cái
    # lệch ta đang săn có thể lọt qua khe giữa chúng.
    # ⛔ KHÔNG dùng dấu nháy kép lồng trong chuỗi này. Nó đi qua BA tầng —
    #    JSON → Nexus → PowerShell — và mỗi tầng ăn một loại escape khác nhau.
    #    Bản đầu viết `\"Authorization: ...\"`: PowerShell thoát bằng backtick
    #    chứ không phải backslash, nên nó nhận literal `\"` và cả lệnh câm, trả
    #    stdout rỗng.
    #
    # ⇒ Chỉ nháy đơn + nối chuỗi bằng `+`. Nhàm hơn, nhưng nó qua được cả ba tầng.
    lenh = "; ".join((
        r"$e = Get-Content C:\ProgramData\LTTLlm\gateway.env",
        r"$t = ($e | Select-String '^LTT_LLM_TOKEN=').ToString().Split('=',2)[1].Trim()",
        r"$ha = 'Authorization: Bearer ' + $t",
        r"$h = (curl.exe -s -o NUL -w '%{http_code}' --max-time 5 -H $ha "
        r"-H 'User-Agent: ltt-soi/1.0' http://127.0.0.1:8299/health)",
        r"$s = (Get-Service LTTLlmGateway).Status",
        r"$l = (Get-Service LTTLlamaSwap).Status",
        r"$c = (Get-NetTCPConnection -LocalPort 8299 -State Listen "
        r"-ErrorAction SilentlyContinue).OwningProcess",
        r"$m = (Get-WmiObject Win32_Service | Where-Object Name -eq "
        r"'LTTLlmGateway').ProcessId",
        r"'health=' + $h + ';gateway=' + $s + ';llamaswap=' + $l + "
        r"';pid_cong=' + $c + ';pid_scm=' + $m",
    ))
    ra = _tren_may_b(lenh, tok)
    if ra is None:
        print("=> KHONG KET LUAN DUOC. Day KHONG phai 'lanh'.")
        return KHONG_DO_DUOC

    # Không để một stdout lạ làm vỡ công cụ bằng `IndexError`. Một công cụ giám
    # sát mà chết vì đầu vào lạ thì im lặng đúng lúc nó cần nói nhất.
    dong = [x for x in ra.strip().splitlines() if "health=" in x]
    if not dong:
        print("  [!] may B tra ve thu khong doc duoc:")
        print("      " + (repr(ra)[:400] if ra.strip() else "<stdout RONG>"))
        print("=> KHONG KET LUAN DUOC. Day KHONG phai 'lanh'.")
        return KHONG_DO_DUOC
    d = dict(x.split("=", 1) for x in dong[-1].split(";") if "=" in x)
    health = d.get("health", "")
    gateway = d.get("gateway", "")
    ma, nhan = phan_xu(health, gateway)
    lech = nhan == "xanh-gia"

    if not a.im or ma != LANH:
        print(f"  /health            : {health or '<khong tra loi>'}")
        print(f"  Get-Service gateway: {gateway}")
        print(f"  Get-Service swap   : {d.get('llamaswap')}")
        print(f"  pid giu cong 8299  : {d.get('pid_cong') or '<khong ai>'}")
        print(f"  pid SCM biet       : {d.get('pid_scm')}")

    if lech:
        print()
        print("  🔴 LECH -- HEALTH XANH GIA.")
        print(f"     /health=200 nhung dich vu = {gateway}.")
        print("     Nhieu kha nang mot tien trinh MO COI dang giu cong 8299 va")
        print("     phuc vu /health. No KHONG co ai dung day neu no chet.")
        print()
        print("     Xu ly tren may B:")
        print(f"       Stop-Process -Id {d.get('pid_cong')} -Force")
        print("       Start-Service LTTLlmGateway")
        return ma

    if ma != LANH:
        print(f"\n  Dich vu khong khoe ({nhan}), NHUNG hai nguon KHOP nhau "
              "-- do la mot hong TU BAO, khong phai xanh gia.")
        return ma

    if not a.im:
        print("\n  LANH -- hai nguon khop nhau.")
    return ma


if __name__ == "__main__":
    sys.exit(main())
