"""bench_kim.py - KIM TRONG DONG CO o ngu canh THAT, cho A/B KV q8_0 vs q4_0.

    py bench_kim.py --ra kq.json --model qwen38-ops --moc 130000 --lan 2

## Vi sao can, khi bo `danh_gia_llm.py` da cham 36/36 cho CA HAI ho so

Vi 36/36 cho ca hai nghia la bo do ay **khong phan biet duoc hai ho so**. Mot
phep do ma moi ung vien deu dat kich tran thi no khong con la phep do — no chi
chung minh khong co suy giam THO. Do la ket qua that va co gia tri, nhung no
KHONG tra loi duoc cau hoi cua quyet dinh nay.

## Cho KV q4_0 dau tien lam hong la GIUA cua so

KV cache luong hoa lam nhoe attention, va cho no lo ra dau tien la nhung token
**khong o hai dau**: dau prompt duoc attention neo manh, cuoi prompt thi vua
moi doc. Bo kiem sentinel dau-cuoi cua lo truoc **bo qua dung vung rui ro nhat**.

Nen o day: nam cai kim o 10%, 30%, 50%, 70%, 90% do sau, va diem la so kim doc
lai dung. Cung mot hat giong ⇒ hai ho so nhan **cung mot prompt, cung mot kim**.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import string
import sys
import time
import urllib.request

SWAP = "http://127.0.0.1:8280"
DO_SAU = (0.10, 0.30, 0.50, 0.70, 0.90)


def _post(url, body, timeout=2400):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def _get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def cong_model(ten):
    for m in _get(SWAP + "/running").get("running", []):
        if m.get("model") == ten:
            return (m.get("proxy") or "").rstrip("/")
    return ""


def nap(ten, timeout=900):
    _post(SWAP + "/v1/chat/completions",
          {"model": ten, "messages": [{"role": "user", "content": "hi"}],
           "max_tokens": 1, "temperature": 0}, timeout=timeout).read()
    for _ in range(40):
        c = cong_model(ten)
        if c:
            return c
        time.sleep(1)
    return ""


_TU = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu "
       "xi omicron pi rho sigma tau upsilon phi chi psi omega quantum vector "
       "tensor gradient kernel buffer socket thread mutex latency throughput "
       "cache token context window inference decode prefill batch attention "
       "residual").split()


def dem_token(goc, s):
    r = _post(goc + "/tokenize", {"content": s}, timeout=600)
    return len(json.loads(r.read().decode("utf-8")).get("tokens", []))


def dung(goc, muc_tieu, rnd):
    """Prompt ~`muc_tieu` token voi nam cai kim o nam do sau."""
    kim = ["".join(rnd.choice(string.ascii_uppercase + string.digits)
                   for _ in range(8)) for _ in DO_SAU]
    so_tu = int(muc_tieu / 1.35)
    for _ in range(6):
        tu = [rnd.choice(_TU) for _ in range(so_tu)]
        for i, ds in enumerate(DO_SAU):
            vt = min(len(tu) - 1, max(0, int(len(tu) * ds)))
            tu[vt] = "\nKIM-" + str(i + 1) + "=" + kim[i] + "\n"
        s = " ".join(tu)
        n = dem_token(goc, s)
        if abs(n - muc_tieu) <= max(300, muc_tieu * 0.01):
            return s, kim, n
        so_tu = max(64, int(so_tu * (muc_tieu / max(1, n))))
    return s, kim, n


def mot_luot(model, muc_tieu, rnd, goc):
    s, kim, n = dung(goc, muc_tieu, rnd)
    cau = ("Trong van ban tren co nam dong dang `KIM-<n>=<gia tri>`. "
           "Liet ke DU nam, moi dong mot cai, dang `KIM-<n>=<gia tri>`. "
           "Khong giai thich gi them.")
    body = {"model": model, "temperature": 0, "max_tokens": 512,
            "chat_template_kwargs": {"reasoning_effort": "low"},
            "messages": [{"role": "user", "content": s + "\n" + cau}]}
    t0 = time.time()
    r = _post(SWAP + "/v1/chat/completions", body)
    d = json.loads(r.read().decode("utf-8"))
    giay = time.time() - t0
    ra = ""
    for ch in d.get("choices") or []:
        ra += (ch.get("message") or {}).get("content") or ""
    thay = [k in ra for k in kim]
    return {"model": model, "token_vao": n, "giay": round(giay, 1),
            "do_sau": list(DO_SAU), "tim_thay": thay,
            "diem": sum(thay), "tren": len(kim), "tra_loi": ra[:400]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--moc", type=int, default=130000)
    ap.add_argument("--lan", type=int, default=2)
    ap.add_argument("--seed", type=int, default=101)
    a = ap.parse_args()

    bao = {"model": a.model, "moc": a.moc, "luc": time.strftime("%H:%M:%S"),
           "luot": []}
    goc = nap(a.model)
    if not goc:
        bao["loi"] = "khong nap duoc"
        pathlib.Path(a.ra).write_text(json.dumps(bao, indent=1), encoding="utf-8")
        return 1
    for i in range(a.lan):
        # Cung `seed` cho moi model ⇒ hai ho so nhan CUNG prompt, CUNG kim.
        rnd = random.Random(a.seed + i)
        nap(a.model)
        kq = mot_luot(a.model, a.moc, rnd, goc)
        bao["luot"].append(kq)
        print(json.dumps({k: v for k, v in kq.items() if k != "tra_loi"}),
              flush=True)
        pathlib.Path(a.ra).write_text(json.dumps(bao, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    tong = sum(l["diem"] for l in bao["luot"])
    tren = sum(l["tren"] for l in bao["luot"])
    bao["tong"] = str(tong) + "/" + str(tren)
    pathlib.Path(a.ra).write_text(json.dumps(bao, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    print("TONG " + bao["tong"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
