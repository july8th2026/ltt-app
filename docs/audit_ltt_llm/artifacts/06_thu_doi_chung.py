# -*- coding: utf-8 -*-
"""thu_doi_chung.py -- DOI CHUNG cho `thu_luong_treo.py`. Chay TREN MAY B.

## Vi sao can to nay

`thu_luong_treo.py` ket luan DAT vi no doc `dang_chay=0` sau moi lan cat. Nhung
`0` chi co nghia neu phep do NAY co kha nang doc ra `1`. Neu `dang_chay` khong
bao gio nhuc nhich -- vi ta doc nham cho, vi cong dem kieu khac, vi bat cu ly do
gi -- thi mot day so 0 doc len y het mot he thong lanh lan, va ta se bao "khong
ro suat" trong khi thuc ra ta khong do gi ca.

⇒ To nay doc dong ho TRONG LUC mot luong dang chay that. Phai thay `1`.

🔴 Day chinh la cai bay vua suyt bat duoc ta 4 phut truoc: ban dau `thu_luong_treo`
   doc ten truong sai, `.get()` tra None, va no in "RO SUAT quay lai" voi giong
   chac nich trong khi he thong khong sao ca. Lan do ta may vi ket qua SAI ve
   phia bao dong. Lan nay neu sai thi no sai ve phia TRAN AN -- nguy hiem hon
   nhieu, va khong co gi tu dong bat duoc.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONG = "http://127.0.0.1:8299"
TOK = ""
for _d in Path(r"C:\ProgramData\LTTLlm\gateway.env").read_text(
        encoding="utf-8-sig").splitlines():
    if _d.startswith("LTT_LLM_TOKEN="):
        TOK = _d.split("=", 1)[1].strip()


def dang_chay() -> int:
    yc = urllib.request.Request(
        CONG + "/health", headers={"User-Agent": "ltt-dc/1.0",
                                   "Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(yc, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))["gioi_han"]["dang_chay"]


def mot_luong_tu_te() -> None:
    """Mot luong DOC DEN CUNG -- khong cat, de no giu suat mot luc that."""
    yc = urllib.request.Request(
        CONG + "/v1/chat/completions",
        data=json.dumps({"model": "qwen38-api", "max_tokens": 400,
                         "stream": True,
                         "messages": [{"role": "user",
                                       "content": "Viet 300 tu ve mua thu."}]}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOK}",
                 "User-Agent": "ltt-dc/1.0"})
    with urllib.request.urlopen(yc, timeout=300) as r:
        for _ in r:
            pass


def main() -> int:
    print(f"DOI CHUNG  {time.strftime('%H:%M:%S')}", flush=True)
    print(f"  truoc khi bat dau: dang_chay={dang_chay()}", flush=True)

    t = threading.Thread(target=mot_luong_tu_te, daemon=True)
    t.start()

    # Doc lien tuc trong luc luong chay. Ghi lai GIA TRI LON NHAT thay duoc.
    dinh, mau = 0, []
    t0 = time.monotonic()
    while t.is_alive() and time.monotonic() - t0 < 120:
        try:
            v = dang_chay()
        except Exception as e:                                  # noqa: BLE001
            v = -1
            print(f"   (doc loi: {type(e).__name__}: {e})", flush=True)
        mau.append(v)
        dinh = max(dinh, v)
        time.sleep(0.4)
    t.join(timeout=60)

    time.sleep(2)
    sau = dang_chay()
    print(f"  trong luc chay:    {len(mau)} mau, dinh={dinh}, "
          f"chuoi dau={mau[:12]}", flush=True)
    print(f"  sau khi xong:      dang_chay={sau}", flush=True)
    print("", flush=True)

    if dinh >= 1 and sau == 0:
        print("  DAT -- dong ho CO nhuc nhich (0 -> 1 -> 0).", flush=True)
        print("     => Nhung so 0 trong `thu_luong_treo` la MOT PHEP DO THAT,", flush=True)
        print("        khong phai mot dong ho chet.", flush=True)
        return 0
    if dinh == 0:
        print("  KHONG DAT -- dong ho KHONG BAO GIO len 1 du luong chay that.", flush=True)
        print("     => `thu_luong_treo` khong do gi ca; ket luan DAT cua no VO GIA TRI.", flush=True)
        print("        Phai tim dung cho dem suat truoc khi tin bat cu so nao.", flush=True)
        return 1
    print(f"  KHONG DAT -- dinh={dinh} nhung sau khi xong van {sau} (mong doi 0).", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
