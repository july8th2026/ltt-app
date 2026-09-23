"""canh_cong_may_b.py - canh cua /health/ready cong LLM may B.

🔴 VI SAO TON TAI. Ngay 23/09/2026 hai card cua may B rung khoi bus PCIe luc 16:20
   (long day PSU). `/live` van tra 200, be mat van khop cay, ping va cong deu mo -
   moi phep do o tang HTTP deu XANH trong khi khong model nao chay duoc. Phien chan
   doan goi nham `/live` roi ket luan sai la "dong khach tranh suat", mat ~40 phut.

   `/health/ready` DA tra 503 `thieu_card` dung luc ay. Khong ai hoi no.

Cong cu nay CHI DOC qua HTTP - khong khoi dong lai dich vu nao, khong dung tren
`C:\\LTTPlatform`. Ma thoat 0 = san sang, 1 = bao dong (503 hoac khong noi duoc),
de cam vao Task Scheduler o mot task rieng (khong tao trong plan/lan nay).
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

MAC_DINH = "http://192.168.2.66:8299/health/ready"


def _doc_that(url: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers={"user-agent": "ltt-canh-cong/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}


def kiem(url: str = MAC_DINH, *, doc=_doc_that) -> dict:
    """Hoi mot lan. KHONG bao gio nem: moi loi deu la 'chua san sang'."""
    try:
        http, than = doc(url)
    except Exception as e:  # noqa: BLE001 - loi mang cung la mot cau tra loi
        return {"ok": False, "http": 0, "ly_do": f"khong_noi_duoc: {type(e).__name__}"}
    if http == 200 and than.get("ok") is True:
        return {"ok": True, "http": 200, "ly_do": ""}
    return {"ok": False, "http": http, "ly_do": str(than.get("ly_do") or f"http_{http}")}


def main() -> int:
    kq = kiem(sys.argv[1] if len(sys.argv) > 1 else MAC_DINH)
    print(json.dumps(kq, ensure_ascii=False))
    return 0 if kq["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
