"""Cap lai consumer key OVH khi khoa cu bi tu choi (403 "credential is not valid").

Vi sao can cong cu rieng: application key + secret la thu DAI HAN (dang ky ung dung
mot lan), con consumer key la thu HET HAN / BI THU HOI. OVH cho cap consumer key moi
chi bang application key - khong can khoa cu - roi chu tai khoan bam xac nhan mot lan
tren trang OVH. Ta giu nguyen AK/AS, chi thay CK.

Chay:
    python tools\vps_ovh_khoa_moi.py            # tao khoa moi + ghi vao app.env
    python tools\vps_ovh_khoa_moi.py --chi-kiem # chi hoi OVH xem khoa hien tai con song

Khoa moi KHONG BAO GIO duoc in ra man hinh: script ghi truc tiep vao
secrets\app.env (sao luu truoc), va chi in van tay sha256 de doi chieu.
Khoa tao theo duong nay khong co thoi han - khac voi khoa tao o trang createToken.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TEP_ENV = Path(r"C:\LTTPlatform\secrets\app.env")
KHOA_CK = "LTT_OVH_CONSUMER_KEY"
CHO_PHEP = "https://app.lttstudios.com/"

#: Dung cac duong ma apps/vps/services/ovh.py + ovh_ordering.py that su goi.
#: Rong hon mot chut o /order va /me vi luong mua IP di qua gio hang + hop dong.
QUYEN = [
    {"method": "GET", "path": "/ip"},
    {"method": "GET", "path": "/ip/*"},
    {"method": "POST", "path": "/ip/*"},
    {"method": "PUT", "path": "/ip/*"},
    {"method": "DELETE", "path": "/ip/*"},
    {"method": "GET", "path": "/order/*"},
    {"method": "POST", "path": "/order/*"},
    {"method": "PUT", "path": "/order/*"},
    {"method": "DELETE", "path": "/order/*"},
    {"method": "GET", "path": "/me"},
    {"method": "GET", "path": "/me/*"},
    {"method": "POST", "path": "/me/*"},
    {"method": "GET", "path": "/vps"},
    {"method": "GET", "path": "/vps/*"},
    {"method": "GET", "path": "/auth/currentCredential"},
]


def van_tay(gia_tri: str) -> str:
    return f"sha={hashlib.sha256(gia_tri.encode()).hexdigest()[:10]} len={len(gia_tri)}"


def doc_env() -> tuple[bytes, dict[str, str]]:
    tho = TEP_ENV.read_bytes()
    cap: dict[str, str] = {}
    for dong in tho.decode("utf-8-sig").splitlines():
        dong = dong.strip()
        if dong and not dong.startswith("#") and "=" in dong:
            ten, gia = dong.split("=", 1)
            cap[ten.strip()] = gia.strip()
    return tho, cap


def hoi_ovh(base: str, ak: str, secret: str, ck: str, duong: str) -> tuple[int, str]:
    url = base + duong
    with urlopen(Request(base + "/auth/time"), timeout=20) as r:
        moc = r.read().decode()
    raw = "+".join((secret, ck, "GET", url, "", moc))
    dau = {"X-Ovh-Application": ak, "X-Ovh-Consumer": ck, "X-Ovh-Timestamp": moc,
           "X-Ovh-Signature": "$1$" + hashlib.sha1(raw.encode()).hexdigest()}
    try:
        with urlopen(Request(url, headers=dau), timeout=25) as r:
            return r.status, r.read().decode()[:300]
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:300]


def xin_khoa_moi(base: str, ak: str) -> tuple[str, str]:
    than = json.dumps({"accessRules": QUYEN, "redirection": CHO_PHEP}).encode()
    yeu_cau = Request(base + "/auth/credential", data=than, method="POST", headers={
        "X-Ovh-Application": ak, "Content-Type": "application/json"})
    with urlopen(yeu_cau, timeout=30) as r:
        tra = json.loads(r.read().decode())
    return str(tra["consumerKey"]), str(tra["validationUrl"])


def ghi_khoa(tho: bytes, khoa_moi: str) -> None:
    mau = re.compile(rb"(?m)^([ \t]*" + KHOA_CK.encode() + rb"[ \t]*=)(.*)$")
    if not mau.search(tho):
        raise SystemExit(f"KHONG THAY dong {KHOA_CK} trong {TEP_ENV} - dung lai, khong ghi")
    luu = TEP_ENV.with_suffix(
        f".env.bak-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    luu.write_bytes(tho)

    def thay(khop: "re.Match[bytes]") -> bytes:
        # Giu nguyen ket dong cua chinh dong do (\r neu tep dung CRLF).
        duoi = b"\r" if khop.group(2).endswith(b"\r") else b""
        return khop.group(1) + khoa_moi.encode() + duoi

    TEP_ENV.write_bytes(mau.sub(thay, tho, count=1))
    print(f"  da ghi {KHOA_CK} vao {TEP_ENV}  ({van_tay(khoa_moi)})")
    print(f"  ban cu: {luu}")


def main() -> int:
    bo = argparse.ArgumentParser()
    bo.add_argument("--chi-kiem", action="store_true",
                    help="chi hoi OVH xem khoa hien tai con song, khong ghi gi")
    tham_so = bo.parse_args()

    tho, cap = doc_env()
    ak = cap.get("LTT_OVH_APPLICATION_KEY", "")
    secret = cap.get("LTT_OVH_APPLICATION_SECRET", "")
    ck = cap.get(KHOA_CK, "")
    base = cap.get("LTT_OVH_API_BASE", "") or "https://ca.api.ovh.com/1.0"
    if not (ak and secret):
        raise SystemExit("app.env thieu LTT_OVH_APPLICATION_KEY/SECRET")

    print(f"diem cuoi   : {base}")
    print(f"application : {van_tay(ak)}")
    print(f"khoa hien co: {van_tay(ck) if ck else 'RONG'}")
    ma, than = hoi_ovh(base, ak, secret, ck, "/auth/currentCredential") if ck else (0, "")
    print(f"OVH tra     : {ma} {than}")
    if ma == 200:
        print("\nKhoa hien tai CON SONG - khong can cap lai.")
        return 0
    if tham_so.chi_kiem:
        print("\nKhoa hien tai DA CHET. Chay lai khong co --chi-kiem de cap khoa moi.")
        return 1

    print("\nXin OVH mot consumer key moi (khong can khoa cu)...")
    khoa_moi, duong_xac_nhan = xin_khoa_moi(base, ak)
    print("\n" + "=" * 70)
    print("MO DUONG NAY, DANG NHAP TAI KHOAN OVH va bam dong y:")
    print(f"\n  {duong_xac_nhan}\n")
    print("Khoa moi da sinh nhung CHUA co hieu luc cho den khi ban bam dong y.")
    print("=" * 70)
    input("\nXong roi thi bam Enter de kiem tra... ")

    ma, than = hoi_ovh(base, ak, secret, khoa_moi, "/auth/currentCredential")
    if ma != 200:
        print(f"\nOVH van tu choi khoa moi: {ma} {than}")
        print("Chua ghi gi vao app.env. Kiem lai buoc dong y roi chay lai.")
        return 1
    print(f"\nOVH chap nhan khoa moi: {than}")
    ghi_khoa(tho, khoa_moi)
    print("\nCON MOT BUOC NUA - app.env mot minh KHONG du, vi nssm nuong env luc CAI:")
    print("  powershell -ExecutionPolicy Bypass -File setup\nap_lai_env.ps1")
    print("roi doi mot vong bao tri (10 phut) hoac restart dich vu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
