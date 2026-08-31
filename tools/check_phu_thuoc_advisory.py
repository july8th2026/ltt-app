"""check_phu_thuoc_advisory.py — hỏi OSV.dev xem thư viện đang cài có lỗ hổng nào.

    python tools/check_phu_thuoc_advisory.py            # goi nhay cam
    python tools/check_phu_thuoc_advisory.py --tat-ca   # moi goi da cai

## ⛔ VÌ SAO KHÔNG ĐƯA VÀO `gate.py`

Nó gọi mạng. Một cổng chất lượng phải **tất định và chạy được offline** — thêm
một lượt gọi ra Internet nghĩa là gate đỏ khi mất mạng, đỏ khi OSV chậm, và đỏ
vào một buổi sáng không ai đổi dòng mã nào. Một cổng đỏ vì lý do ngoài kho là
một cổng người ta học cách bỏ qua.

⭐ Và nó còn một tính chất khiến nó **không hợp làm bánh cóc**: kết quả đổi **mà
   mã không đổi**. Một advisory mới công bố hôm nay làm hôm nay đỏ trong khi
   commit cuối cùng là tuần trước. Đó là thông tin đúng, nhưng nó là **tin tức**,
   không phải **phán quyết về một thay đổi**.

⇒ Chạy nó theo lịch hoặc trước mỗi đợt phát hành, đọc bằng mắt, rồi quyết.

## Đọc kết quả thế nào

Một advisory **không** tự động là một việc phải làm. Ba câu hỏi, theo thứ tự:

1. **Chạm được không?** Gói đó có nằm trên đường dữ liệu **không tin cậy** đi
   vào không? `python-multipart` phân tích thân multipart của khách ⇒ chạm được.
   Một gói chỉ dùng trong script dựng thì không.
2. **`AV:N` + `PR:N`?** Kích được từ mạng, không cần quyền — đó là mức đáng sửa
   sớm.
3. **Bản vá cách bao xa?** Một số hiệu patch khác hẳn một lần nâng major.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Gói **chạm dữ liệu không tin cậy** hoặc **giữ bí mật**. Danh sách này là một
#: phán đoán, không phải một sự thật — thêm bớt khi kiến trúc đổi.
#:
#: ⛔ Đừng in emoji ra stdout: console PowerShell 5.1 là CP1252 và một ký tự
#:    ngoài bảng làm cả công cụ chết giữa chừng (đã dính 31/08).
NHAY_CAM = (
    "fastapi", "starlette", "uvicorn", "httpx", "requests", "urllib3",
    "aiohttp", "python-multipart", "jinja2", "itsdangerous", "pyjwt",
    "cryptography", "sqlalchemy", "alembic", "psycopg", "pydantic",
    "pillow", "boto3", "botocore", "paramiko", "lxml", "pyyaml",
)


def _da_cai() -> dict[str, str]:
    r = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"],
                       capture_output=True, text=True, timeout=300)
    return {g["name"].lower(): g["version"] for g in json.loads(r.stdout or "[]")}


def _hoi_osv(truy: list[dict]) -> list[dict]:
    req = urllib.request.Request(
        "https://api.osv.dev/v1/querybatch",
        data=json.dumps({"queries": truy}).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "ltt-audit/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r).get("results", [])


def _ban_va(ma: str) -> str:
    """Bản đầu tiên đã vá — con số quyết định việc này rẻ hay đắt."""
    try:
        req = urllib.request.Request(f"https://api.osv.dev/v1/vulns/{ma}",
                                     headers={"User-Agent": "ltt-audit/1.0"})
        with urllib.request.urlopen(req, timeout=45) as r:
            d = json.load(r)
    except Exception:                                           # noqa: BLE001
        return "?"
    for a in d.get("affected", []):
        for rg in a.get("ranges", []):
            for ev in rg.get("events", []):
                if "fixed" in ev:
                    return ev["fixed"]
    return "?"


def main() -> int:
    p = argparse.ArgumentParser(description="Hoi OSV.dev ve thu vien da cai.")
    p.add_argument("--tat-ca", action="store_true",
                   help="quet moi goi da cai, khong chi goi nhay cam")
    p.add_argument("--chi-tiet", action="store_true",
                   help="tra them ban da va cho tung advisory (cham hon)")
    a = p.parse_args()

    cai = _da_cai()
    ten = sorted(cai) if a.tat_ca else [g for g in NHAY_CAM if g in cai]
    truy = [{"package": {"name": g, "ecosystem": "PyPI"}, "version": cai[g]}
            for g in ten]
    if not truy:
        print("khong co goi nao de hoi")
        return 0

    print(f"Hoi OSV.dev ve {len(truy)} goi da cai...\n")
    try:
        kq = _hoi_osv(truy)
    except Exception as e:                                      # noqa: BLE001
        # ⛔ Khong noi loi mang thanh "sach". Mot cong cu bao mat im lang khi no
        #    khong hoi duoc la mot cong cu noi doi.
        print(f"KHONG HOI DUOC OSV ({type(e).__name__}: {e})")
        print("=> KHONG KET LUAN DUOC. Day KHONG phai 'sach'.")
        return 2

    co = []
    for q, res in zip(truy, kq):
        vulns = res.get("vulns") or []
        g, v = q["package"]["name"], q["version"]
        if vulns:
            co.append((g, v, vulns))
        else:
            print(f"     {g:<20} {v:<14} sach")

    print()
    for g, v, vulns in co:
        print(f"  [CO] {g} {v} — {len(vulns)} advisory")
        for x in vulns[:5]:
            ma = x.get("id", "?")
            tt = (x.get("summary") or "").strip()[:78]
            hau = f"   -> va tu {_ban_va(ma)}" if a.chi_tiet else ""
            print(f"        {ma:<22} {tt}{hau}")
        if len(vulns) > 5:
            print(f"        ... con {len(vulns) - 5} advisory nua")

    print(f"\n  {len(co)}/{len(truy)} goi co advisory")
    if co:
        print("\n  Doc bang ba cau hoi, theo thu tu (xem docstring dau tep):")
        print("    1. goi do co nam tren duong DU LIEU KHONG TIN CAY khong?")
        print("    2. advisory co AV:N + PR:N khong?")
        print("    3. ban va cach bao xa?")
    # ⛔ Luon tra 0: day la mot ban tin, khong phai mot phan quyet. Tra khac 0 se
    #    khien ai do cam no vao gate, va gate se do vao mot buoi sang khong ai
    #    doi mot dong ma nao.
    return 0


if __name__ == "__main__":
    sys.exit(main())
