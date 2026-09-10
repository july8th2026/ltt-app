"""Quet chuoi CAM tren URL CONG KHAI that — hau deploy, khong phai trong gate.

    python tools\vps_quet_ro_ri.py
    python tools\vps_quet_ro_ri.py --goc http://127.0.0.1:8100   # doi chung

## 🔴 Vi sao co tep nay

Ngay 09/09/2026, `RELEASE_SCORECARD.md` cham GUI **95** kem dung mot dong ghi
chu: *"chua chot tren URL cong khai"*. Cung ngay do, mot luot `curl` len
`https://app.lttstudios.com/vps` tim ra **hai** cho dua noi bo ra cho khach:

  - trang ban hang cong khai in `LTT_VPS_PROXMOX_CA` va chu `Proxmox`;
  - trang may in `ProxmoxError: 500 loi tai https://10.10.0.2:8006/api2/json/...`

Ca hai deu **co san tu truoc**, va ca hai deu lot qua `test_557` + `test_559`.
Khong phai vi hai bo test do yeu: vi chung do **ma** va do **render local**,
con thu vua hong thi chi lo ra sau Cloudflare, tren mot may co cau hinh that.

⭐ Nen bai hoc khong phai "them ca test". La: mot han che DA BIET va DA GHI ra
   giay khong tu bien thanh mot phep do. Tep nay la buoc bien no thanh phep do.

## ⛔ Vi sao KHONG nam trong gate

Gate phai chay duoc khi khong co mang, va no do **commit dang o cay**, con tep
nay do **ban dang phuc vu khach**. Hai cau hoi khac nhau. Nhet no vao gate la
lam gate do vi Cloudflare hat hoi.

Cho dung: sau moi luot deploy, canh `nghiem_thu_deploy.py`.

## Khong the xanh RONG

Mot bo quet tra "0 phat hien" tren mot trang tai hong trong y het mot bo quet
tra "0 phat hien" tren mot trang sach. Nen truoc khi khang dinh dieu gi, tep
nay doi **tien de**: moi URL phai tra 200 va it nhat `TOI_THIEU_BYTE`. Khong
dat thi no bao LOI, khong bao PASS.
"""
from __future__ import annotations

import argparse
import re
import urllib.error
import urllib.request

GOC_MAC_DINH = "https://app.lttstudios.com"

#: Trang cong khai — khach CHUA dang nhap cung mo duoc.
#:
#: Chi nhung trang khong doi phien. Mot trang doi dang nhap se tra ve trang
#: `/login`, va quet trang dang nhap roi bao "sach" la mot ket luan rong.
DUONG = ("/vps",)

#: Toi thieu bao nhieu byte thi coi la "trang co noi dung".
#:
#: `/vps` that nang ~40 KB. Nguong 2 KB du de bat trang loi, trang chuyen huong
#: va trang rong, ma khong gay bao dong gia khi trang duoc rut gon.
TOI_THIEU_BYTE = 2048

#: Chuoi khong bao gio duoc co mat tren mot trang khach doc.
#:
#: Gom theo **hang**, khong theo tung ca da gap: mot danh sach chi liet ke hai
#: chuoi da lo hom qua se khong bat duoc chuoi thu ba lo ngay mai.
CAM = (
    # Ten lop ha tang — `services/proxmox.py` viet rang khach "khong bao gio
    # nhin thay" no.
    "Proxmox",
    "proxmox",
    # Cong quan tri cua PVE.
    ":8006",
    # Ten bien moi truong noi bo.
    "LTT_VPS_",
    "LTT_ENV",
    # Ten class Python / dau vet ngoai le.
    "Traceback",
    "Exception",
    "RuntimeError",
    # Hinh dang cum.
    "/api2/json",
    "/nodes/",
    "qemu",
    "vmid",
    "upid",
    "UPID",
)

#: Dia chi noi bo — bat bang mau, khong bang danh sach.
RIENG_TU = re.compile(
    r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")


def _tai(url: str, cho: int) -> tuple[int, str]:
    yc = urllib.request.Request(url, headers={"User-Agent": "ltt-quet-ro-ri/1"})
    with urllib.request.urlopen(yc, timeout=cho) as r:   # noqa: S310 - URL cua ta
        return r.status, r.read().decode("utf-8", "replace")


def quet(goc: str, cho: int = 30) -> int:
    loi = 0
    for duong in DUONG:
        url = goc.rstrip("/") + duong
        try:
            ma, than = _tai(url, cho)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"  [LOI] {url}: khong tai duoc ({type(exc).__name__}: {exc})")
            loi += 1
            continue

        # Tien de TRUOC khi khang dinh. Thieu no thi moi dong duoi deu rong.
        if ma != 200 or len(than) < TOI_THIEU_BYTE:
            print(f"  [LOI] {url}: HTTP {ma}, {len(than)} byte "
                  f"— duoi nguong {TOI_THIEU_BYTE}, KHONG ket luan duoc")
            loi += 1
            continue

        thay = [c for c in CAM if c in than]
        ip = sorted(set(RIENG_TU.findall(than)))
        if thay or ip:
            print(f"  [RO] {url} ({len(than)} byte)")
            for c in thay:
                # In kem mot doan ngu canh de nguoi doc biet no nam o dau.
                i = than.index(c)
                doan = " ".join(than[max(0, i - 70):i + 70].split())
                print(f"        {c!r}: …{doan}…")
            for a in ip:
                print(f"        dia chi noi bo: {a}")
            loi += 1
        else:
            print(f"  [OK]  {url} ({len(than)} byte, {len(CAM)} chuoi cam)")
    return loi


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--goc", default=GOC_MAC_DINH)
    ap.add_argument("--cho", type=int, default=30, help="giay cho moi URL")
    a = ap.parse_args()

    print(f"Quet ro ri tren {a.goc}")
    loi = quet(a.goc, a.cho)
    print("RESULT: " + ("PASS" if loi == 0 else f"FAIL ({loi} URL co van de)"))
    return 1 if loi else 0


if __name__ == "__main__":
    raise SystemExit(main())
