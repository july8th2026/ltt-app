r"""
tai_dnsmos.py — tải model DNSMOS P.835 về cache, một lần, có kiểm băm.

    python -m voice_sidecar.tai_dnsmos            # tải nếu chưa có
    python -m voice_sidecar.tai_dnsmos --kiem     # chỉ kiểm, không tải

Gọi từ `deploy/windows/install-vieneu-sidecar.ps1` sau bước làm ấm cache HF.

## Vì sao ghim theo COMMIT chứ không theo nhánh

`microsoft/DNS-Challenge` là kho đang sống. Tải theo `master` nghĩa là hai lần
cài cách nhau vài tháng có thể lấy hai model khác nhau — và điểm chất lượng sẽ
đổi mà không ai đổi dòng mã nào. Ghim commit + kiểm sha256 thì một lần cài hôm
nay và một lần cài sang năm cho cùng một con số.

## Giấy phép

`microsoft/DNS-Challenge` — **CC-BY-4.0**. Ghi công là điều kiện dùng:

    Reddy, Gopal, Cutler. *DNSMOS P.835: A non-intrusive perceptual objective
    speech quality metric to evaluate noise suppressors.* ICASSP 2022.
    https://arxiv.org/pdf/2110.01763.pdf

⚠️ KHÔNG commit tệp `.onnx` vào kho này. Nó là tài sản của người khác, có giấy
   phép riêng, và 1,1 MB nhị phân trong git là 1,1 MB không ai diff được. Tải
   lúc cài, cùng chỗ với model giọng.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request

#: Ghim cứng. Đổi ba dòng này cùng lúc, hoặc không đổi dòng nào.
COMMIT = "82f1b17e7776a43eee395d0f45bae8abb700ad00"
SHA256 = "269fbebdb513aa23cddfbb593542ecc540284a91849ac50516870e1ac78f6edd"
SO_BYTE = 1_157_965

URL = (f"https://raw.githubusercontent.com/microsoft/DNS-Challenge/{COMMIT}"
       f"/DNSMOS/DNSMOS/sig_bak_ovr.onnx")


def _bam(duong: str) -> str:
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def kiem(duong: str) -> tuple[bool, str]:
    """`(hợp lệ, lý do)`. Sai băm cũng là **không hợp lệ**, không phải cảnh báo."""
    if not os.path.isfile(duong):
        return False, "chua co"
    co = os.path.getsize(duong)
    if co != SO_BYTE:
        return False, f"kich thuoc {co:,} != {SO_BYTE:,}"
    b = _bam(duong)
    if b != SHA256:
        return False, f"sha256 lech: {b[:16]}… != {SHA256[:16]}…"
    return True, "khop ghim"


def tai(duong: str) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tai"
    # ⛔ Tải ra tệp TẠM rồi mới đổi tên. Tải thẳng vào đích thì một lần đứt mạng
    #    để lại một tệp cụt ở đúng chỗ, và lượt sau `os.path.isfile` nói "có rồi".
    with urllib.request.urlopen(URL, timeout=300) as r, open(tam, "wb") as f:
        while True:
            khoi = r.read(1 << 20)
            if not khoi:
                break
            f.write(khoi)
    ok, ly_do = kiem(tam)
    if not ok:
        os.unlink(tam)
        raise SystemExit(f"DNSMOS tai ve KHONG khop ghim: {ly_do}")
    os.replace(tam, duong)


def main(argv=None) -> int:
    from .dnsmos import duong_model

    ap = argparse.ArgumentParser()
    ap.add_argument("--kiem", action="store_true", help="Chi kiem, khong tai.")
    a = ap.parse_args(argv)

    duong = duong_model()
    ok, ly_do = kiem(duong)
    if ok:
        print(f"[OK] DNSMOS da co va {ly_do}: {duong}")
        return 0
    if a.kiem:
        print(f"[THIEU] DNSMOS: {ly_do}", file=sys.stderr)
        return 1

    print(f"[..] Tai DNSMOS ({SO_BYTE:,} byte) -> {duong}")
    tai(duong)
    print(f"[OK] DNSMOS san sang: {duong}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
