"""Kiểm khoá SSH của **dịch vụ** — đúng đường mà worker đi.

    python tools\\vps_kiem_khoa.py          # kiểm cả hai khoá
    python tools\\vps_kiem_khoa.py --nhanh  # chỉ kiểm quyền, không nối mạng

## 🔴 Vì sao công cụ này tồn tại

Ngày 2026-08-27 một khách trả 1.490 credit và nhận về chữ "Lỗi". Nguyên nhân:
worker chạy bằng **LocalSystem**, còn khoá SSH nằm ở `C:\\Users\\<người>\\.ssh\\`
nơi ACL thừa kế cho cả tài khoản người dùng. Từ góc nhìn của SYSTEM đó là khoá
"hở", và OpenSSH **từ chối dùng nó**:

    WARNING: UNPROTECTED PRIVATE KEY FILE!
    Permissions for '...\\ltt_pve' are too open.

⛔ **Lỗi đó im lặng hoàn toàn.** `/vps` vẫn bán, `/health/ready` vẫn 200, gate vẫn
xanh, `tools/gate.py` không có gì để nói. Tín hiệu duy nhất là một khách đã trả
tiền. Đó là lý do công cụ này phải tồn tại: **không phải để sửa, mà để BIẾT.**

## ⚠️ Và vì sao phép kiểm cũ không bắt được

`vps_doctor.py` **có** kiểm SSH — nhưng bằng `ssh ltt-gw`, tức một **bí danh
trong SSH config**, chạy bằng **tài khoản con người**. Nó không đi qua đường
worker đi (đường dẫn tệp khoá + `BatchMode`, chạy bằng LocalSystem), nên nó
**xanh trong khi worker chết**.

⭐ Bài học tổng quát hơn cả cái lỗi: *một phép kiểm phải đi đúng đường mà thứ nó
canh sẽ đi.* Đo một đường dễ hơn rồi gọi nó là bằng chứng cho đường khó hơn là
cách tạo ra một phép kiểm xanh vĩnh viễn.

## Hai thứ được kiểm, và vì sao cần cả hai

1. **Quyền tệp** — chép đúng luật mà chính OpenSSH áp trên Windows: ngoài chủ sở
   hữu, chỉ `SYSTEM` và `Administrators` được có quyền. Một ACE cho tài khoản
   người dùng thường là đủ để nó từ chối. Kiểm được **mà không cần chạy dưới
   SYSTEM**, nên chạy ở đâu cũng đúng.
2. **Nối thật** — khoá đúng quyền vẫn có thể sai nội dung, sai host, hoặc máy
   kia đã đổi khoá. Chỉ một lần `ssh` thật mới trả lời được.

Cái (1) là cái đã hỏng và không ai thấy; cái (2) là cái người ta hay nghĩ tới.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Chủ thể được phép có quyền trên một khoá riêng, theo đúng luật của Win32
#: OpenSSH. So sánh KHÔNG phân biệt hoa thường và bỏ phần tên máy.
CHU_THE_DUOC_PHEP = {"system", "administrators", "trustedinstaller"}

#: Hai khoá dịch vụ và biến môi trường khai chúng.
KHOA_DICH_VU = (
    ("LTT_VPS_ROUTER_SSH_KEY", "VM router"),
    ("LTT_VPS_GATEWAY_SSH_KEY", "cong vao"),
)


def _nap_app_env(duong: pathlib.Path) -> dict[str, str]:
    """Đọc `app.env` thành dict. Không đặt vào `os.environ` — công cụ chẩn đoán
    không nên đổi môi trường của chính tiến trình nó."""
    ra: dict[str, str] = {}
    try:
        noi_dung = duong.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ra
    except PermissionError:
        # ⭐ Đây là dấu hiệu bước siết quyền ĐÃ CHẠY ĐÚNG, không phải một lỗi.
        #    Sau khi siết, `secrets\` chỉ còn SYSTEM + Administrators — nên một
        #    tiến trình thường không đọc được, đúng như thiết kế.
        #
        # ⚠️ Nói ra điều đó thay vì ném `PermissionError` kèm stack trace. Một
        #    công cụ chẩn đoán mà đổ stack vào đúng tình huống hay gặp nhất là
        #    một công cụ bắt người đọc đi chẩn đoán chính nó.
        print(f"KHONG DOC DUOC {duong}: khong du quyen.")
        print("Day thuong la dau hieu TOT - secrets\\ da duoc siet ve")
        print("SYSTEM + Administrators. Chay lai cong cu nay bang PowerShell")
        print("Administrator.")
        raise SystemExit(3)
    for dong in noi_dung.splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#") or "=" not in dong:
            continue
        k, _, v = dong.partition("=")
        ra[k.strip()] = v.strip()
    return ra


def chu_the_thua(duong: str) -> list[str]:
    """Những chủ thể có quyền trên tệp mà OpenSSH sẽ **không** chấp nhận.

    Trả danh sách rỗng = quyền sạch. Danh sách khác rỗng = OpenSSH sẽ từ chối
    khoá này khi chạy dưới một tài khoản không phải chủ sở hữu.

    ⚠️ Chủ sở hữu **luôn** được phép, nên nó bị loại khỏi phép so. Đó cũng là lý
       do một khoá "chạy tốt khi tôi thử tay" vẫn hỏng trong dịch vụ: lúc thử
       tay, người thử CHÍNH LÀ chủ sở hữu.
    """
    ra = subprocess.run(["icacls", duong], capture_output=True, text=True)
    if ra.returncode != 0:
        raise RuntimeError(f"icacls that bai: {(ra.stderr or ra.stdout).strip()[:200]}")

    chu = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-Acl '{duong}').Owner"], capture_output=True, text=True)
    chu_so_huu = (chu.stdout or "").strip().split("\\")[-1].lower()

    thua: list[str] = []
    for dong in ra.stdout.splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("Successfully") or dong.startswith("Failed"):
            continue
        # Dạng: `<đường dẫn> DOMAIN\Ten:(I)(F)` hoặc `DOMAIN\Ten:(F)`
        phan = dong.replace(duong, "").strip()
        if ":" not in phan:
            continue
        ten = phan.rsplit(":", 1)[0].strip().split("\\")[-1].lower()
        if not ten or ten == chu_so_huu:
            continue
        if ten in CHU_THE_DUOC_PHEP:
            continue
        thua.append(ten)
    return sorted(set(thua))


def _noi_thu(bien: str, cau_hinh: dict[str, str], nhan: str) -> bool:
    """Nối thật bằng ĐÚNG khoá và ĐÚNG tuỳ chọn mà worker dùng."""
    from apps.vps.services.ssh_lenh import DichDen, SshLenhError, chay_ssh

    host_bien = bien.replace("_SSH_KEY", "_HOST")
    user_bien = bien.replace("_SSH_KEY", "_USER")
    dich = DichDen(host=cau_hinh.get(host_bien, ""),
                   user=cau_hinh.get(user_bien, "root"),
                   khoa=cau_hinh.get(bien, ""), nhan=nhan)
    try:
        dich.verify(bien)
        chay_ssh(dich, ["true"], timeout=20)
        print(f"    noi that      OK  ({dich.user}@{dich.host})")
        return True
    except SshLenhError as exc:
        print(f"    noi that      HONG: {str(exc)[:160]}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--env", type=pathlib.Path,
                    default=pathlib.Path(r"C:\LTTPlatform\secrets\app.env"))
    ap.add_argument("--nhanh", action="store_true",
                    help="chi kiem quyen, khong noi mang")
    ts = ap.parse_args()

    cau_hinh = _nap_app_env(ts.env)
    if not cau_hinh:
        print(f"KHONG DOC DUOC {ts.env}")
        return 2

    loi = 0
    for bien, nhan in KHOA_DICH_VU:
        duong = cau_hinh.get(bien, "")
        print(f"\n{nhan}  ({bien})")
        if not duong:
            print("    CHUA KHAI trong app.env")
            loi += 1
            continue
        print(f"    duong dan     {duong}")
        if not pathlib.Path(duong).exists():
            print("    LOI: khong thay tep khoa")
            loi += 1
            continue

        # 1. Quyen — cai da hong va khong ai thay.
        try:
            thua = chu_the_thua(duong)
        except RuntimeError as exc:
            print(f"    quyen         KHONG DOC DUOC: {exc}")
            loi += 1
        else:
            if thua:
                print(f"    quyen         HO: co them {', '.join(thua)}")
                print("                  -> OpenSSH se tu choi khoa nay khi chay")
                print("                     duoi LocalSystem. Chay:")
                print("                     setup\\vps_khoa_dich_vu.ps1 (nang quyen)")
                loi += 1
            else:
                print("    quyen         OK  (chi chu so huu + SYSTEM/Administrators)")

        # 2. Noi that.
        if not ts.nhanh and not _noi_thu(bien, cau_hinh, nhan):
            loi += 1

    print()
    if loi:
        print(f"RESULT: FAIL ({loi} van de)")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
