"""nghiem_thu_l08_ba_lop.py — do L-08 sau khi dung co che BA LOP.

## ⛔ VI SAO VIET LAI THAY VI CHAY LAI BO CU

Bo cu (`nghiem_thu_l08_sau_deploy.py`) bao:

    2 slot may B nha <= 30 s : DAT   (20,8 s)

**Con so ay khong noi gi.** Prompt cu dat `max_tokens=2048`, va may B sinh xong
2048 token trong khoang 20 s. Nen o giay 20,8 may B ranh **du ta co cat hay
khong**. Phep do khong phan biet duoc "ta dong ket noi" voi "no sinh xong" —
tuc no mu dung o chieu no dinh do. Toi da bao DAT cho mot ve nhu the.

⇒ Bo nay sua bang mot **DOI CHUNG**, khong bang mot nguong dep hon:

    luot A (DOI CHUNG): chay TRON VEN, khong cat  -> do T_tron
    luot B (PHEP DO)  : cat o manh thu 5          -> do T_nha

Ket luan chi co nghia khi **T_nha << T_tron**. Neu hai so xap xi nhau thi ta
dang do thoi gian SINH, khong do thoi gian NHA — bo nay tu khai dieu do thay vi
in ra mot chu "DAT".

## Ba lop, ba chan tren khac nhau — phai biet lop NAO da nha

    lop 1  `khi_dut`                        ~0,05 s  (+ ~17 s neu qua Cloudflare)
    lop 2  nhip tim chung minh tien trien    tran im lang (900 s)
    lop 3  `reclaim_expired`                 20 phut

Mot lan nha o giay 900 hay 1200 **khong phai** thanh cong cua lop 1 — do la
luoi do ho. Bo nay in ra lop nao da bat, de mot ket qua "co nha" khong bi doc
thanh "lop 1 chay".

## Loopback truoc, Cloudflare sau

Cong M do duoc: khach cat toi thang may A la 1,43 s, qua Cloudflare la 16,8 s —
bien khong bao origin. Nen do LOOPBACK truoc de thay co che that, roi do qua
Cloudflare de thay con so khach nhin thay. Lan luot, khong tron.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
#: Goc kho — suy tu vi tri tep nay, KHONG ghim cung mot worktree.
GOC_CAY = str(pathlib.Path(__file__).resolve().parents[2])
sys.path.insert(0, GOC_CAY)

from tools.do_tai_hai_model import _doc_khoa  # noqa: E402

# Sinh DAI co chu dich: phai dai hon han moi cua so do, neu khong ta lai do
# nham thoi gian sinh mot lan nua.
THAN = {
    "model": "ltt-3.8",
    "stream": True,
    "max_tokens": 8000,
    "messages": [{"role": "user",
                  "content": "Count from 1 to 2000. One number per line. "
                             "Do not stop early, do not summarise."}],
}


def _lease_stream() -> int:
    ma = (
        "import json,os,pathlib,sys\n"
        "sys.path.insert(0, r'" + GOC_CAY + "')\n"
        "if not os.environ.get('LTT_DATABASE_URL'):\n"
        "    t = pathlib.Path(r'C:\\LTTPlatform\\secrets\\app.env')\n"
        "    for d in t.read_text(encoding='utf-8', errors='replace').splitlines():\n"
        "        if d.strip().startswith('LTT_DATABASE_URL'):\n"
        "            os.environ['LTT_DATABASE_URL'] = d.split('=',1)[1].strip().strip('\"')\n"
        "            break\n"
        "from sqlalchemy import text\n"
        "from platform_core.db import get_engine\n"
        "with get_engine().connect() as c:\n"
        "    n = c.execute(text(\"SELECT COUNT(*) FROM execution_leases \"\n"
        "                       \"WHERE mode='stream'\")).scalar()\n"
        "print(json.dumps({'n': int(n or 0)}))\n"
    )
    r = subprocess.run([sys.executable, "-c", ma], capture_output=True,
                       text=True, cwd=GOC_CAY, timeout=60)
    try:
        return int(json.loads((r.stdout or "").strip().splitlines()[-1])["n"])
    except (ValueError, IndexError, KeyError):
        return -1


def _cho_nen_sach(han_s: float = 120.0) -> bool:
    t0 = time.monotonic()
    while time.monotonic() - t0 < han_s:
        if _lease_stream() == 0:
            return True
        time.sleep(3)
    return False


def luot_tron(goc: str, khoa: str, han_s: float) -> float:
    """DOI CHUNG: chay het, khong cat. Tra ve thoi luong."""
    import httpx
    t0 = time.monotonic()
    n = 0
    with httpx.Client(timeout=han_s) as kh:
        with kh.stream("POST", f"{goc}/api/v1/messages", json=THAN,
                       headers={"Authorization": f"Bearer {khoa}",
                                "Idempotency-Key": str(uuid.uuid4())}) as r:
            if r.status_code != 200:
                print(f"   HTTP {r.status_code}: {r.read()[:200]!r}")
                return -1.0
            for _ in r.iter_raw():
                n += 1
    tron = time.monotonic() - t0
    print(f"   chay tron: {tron:.1f}s, {n} manh")
    return tron


def luot_cat(goc: str, khoa: str, doc_manh: int, han_s: float) -> dict:
    """PHEP DO: cat o manh thu N, dem toi luc lease bien mat."""
    import httpx
    with httpx.Client(timeout=120.0) as kh:
        with kh.stream("POST", f"{goc}/api/v1/messages", json=THAN,
                       headers={"Authorization": f"Bearer {khoa}",
                                "Idempotency-Key": str(uuid.uuid4())}) as r:
            if r.status_code != 200:
                return {"loi": f"HTTP {r.status_code}: {r.read()[:200]!r}"}
            n = 0
            for _ in r.iter_raw():
                n += 1
                if n >= doc_manh:
                    break
    t_cat = time.monotonic()
    print(f"   da doc {n} manh — CAT")

    while time.monotonic() - t_cat < han_s:
        con = _lease_stream()
        giay = round(time.monotonic() - t_cat, 1)
        if con == 0:
            print(f"   {giay:7.1f}s  lease=0  <- DA NHA")
            return {"t_nha": giay}
        if int(giay) % 20 < 3:
            print(f"   {giay:7.1f}s  lease={con}")
        time.sleep(2)
    return {"t_nha": None}


def _lop_nao(t: float) -> str:
    """Mot lan nha o giay 900 KHONG phai thanh cong cua lop 1."""
    if t < 60:
        return "LOP 1 (khi_dut) — duong chinh"
    if t < 960:
        return "LOP 2 (nhip tim chung minh tien trien) — LUOI do ho lop 1"
    return "LOP 3 (reclaim_expired) — chan cuoi; lop 1 va 2 DEU truot"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--khoa", required=True)
    ap.add_argument("--goc", default="http://127.0.0.1:8100",
                    help="loopback de thay co che; URL cong khai de thay so khach nhin")
    ap.add_argument("--doc-manh", type=int, default=5)
    ap.add_argument("--han", type=float, default=360.0)
    a = ap.parse_args()

    khoa = _doc_khoa(pathlib.Path(a.khoa))
    print(f"== goc: {a.goc}")

    print("\n== 0. nen phai sach ==")
    if not _cho_nen_sach():
        print("   !! con luot stream khac dang chay. DUNG.")
        return 2
    print("   lease mode=stream = 0")

    print("\n== 1. DOI CHUNG: chay TRON VEN, khong cat ==")
    print("   (khong co so nay thi 'nha nhanh' co the chi la 'sinh xong nhanh')")
    tron = luot_tron(a.goc, khoa, a.han)
    if tron < 0:
        return 2
    _cho_nen_sach()

    print(f"\n== 2. PHEP DO: cat o manh thu {a.doc_manh} ==")
    kq = luot_cat(a.goc, khoa, a.doc_manh, a.han)
    if "loi" in kq:
        print(f"   !! {kq['loi']}")
        return 2

    t_nha = kq["t_nha"]
    print("\n== PHAN QUYET ==")
    print(f"  T_tron (doi chung, khong cat) : {tron:.1f}s")
    print(f"  T_nha  (sau khi cat)          : "
          f"{f'{t_nha:.1f}s' if t_nha is not None else f'CHUA NHA sau {a.han:.0f}s'}")
    if t_nha is None:
        print("\n  >> TRUOT: ca ba lop deu khong nha trong cua so do.")
        return 1

    # ⛔ Ve NAY moi la thu bo cu thieu.
    if t_nha > 0.5 * tron:
        print(f"\n  >> KHONG KET LUAN DUOC: T_nha ({t_nha:.1f}s) khong nho hon han "
              f"so voi T_tron ({tron:.1f}s).")
        print("     Ta dang do thoi gian SINH chu khong do thoi gian NHA. Tang "
              "`max_tokens`/do dai prompt roi do lai.")
        return 1

    print(f"  ty le T_nha/T_tron            : {t_nha / tron:.3f}  (phai << 1)")
    print(f"  lop da bat                    : {_lop_nao(t_nha)}")
    print()
    if t_nha < 60:
        print("  >> DAT: lop 1 nha suat, va DOI CHUNG chung minh do la do CAT.")
        return 0
    print("  >> MOT PHAN: suat co duoc nha, nhung LOP 1 DA TRUOT — luoi do ho.")
    print("     Dung bao 'L-08 dong'. Doc log tim `khong nha duoc suat khi khach dut`.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
