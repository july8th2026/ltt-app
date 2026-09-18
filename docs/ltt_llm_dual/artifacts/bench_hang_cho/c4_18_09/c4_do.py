"""C4 (18/09/2026): do so slot (-np) tren may B, goi THANG llama-swap (qua tunnel), khong qua cong 8299.

    python c4_do.py --base http://127.0.0.1:18280 --model qwen38-api --np 3 --nhan np3 --ra ket_qua

Buoc (--buoc, mac dinh tat ca): prefill, don, tong, lang, mtp
  warm-up : 1 luot ngan + 1 luot 32K bo di (va hieu chinh do dai tai lieu -> ~32K token)
  prefill : 3 x 32K mot minh, max_tokens 1 -> prompt_ms engine
  don     : 3 x 1 luong, prompt ~1K, max_tokens 1024 -> predicted_per_second engine
  tong    : 3 dot x N=np luong dong thoi, max_tokens 1024 -> moi luong + tong
  lang    : 3 dot: (np-1) luong nho dang sinh + 1 prefill 32K chen vao sau 8 s -> khoang lang dai nhat
  mtp     : 2 dot x np luong dong thoi, moi luong ~16K token KHAC nhau (cong thuc #27572), dem content rong
Moi prompt co nonce o DAU. Moi luot ghi 1 dong JSON.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import statistics
import threading
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:18280"
RA: pathlib.Path | None = None
NHAN = "?"
KHOA = threading.Lock()
TU = ("request queue worker scheduler latency cache token prompt decode prefill slot budget fairness "
      "cancel stream credit invoice lease retry timeout backoff gateway tunnel render voice ledger").split()


def ghi(**kw):
    kw.setdefault("nhan", NHAN)
    kw.setdefault("t", round(time.time(), 2))
    with KHOA, RA.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def tai_lieu(ky_tu: int, hat: int) -> str:
    r = random.Random(hat)
    dong, n = [], 0
    while n < ky_tu:
        s = "def ham_%d(%s):\n    return %d  # %s" % (r.randint(1, 10**6), r.choice(TU), r.randint(0, 999),
                                                      " ".join(r.sample(TU, 6)))
        dong.append(s)
        n += len(s) + 1
    return "\n".join(dong)[:ky_tu]


def nonce() -> str:
    return "%d-%d" % (time.time_ns(), random.SystemRandom().randint(0, 10**9))


def ngan(tag: str) -> list:
    than = ("Ma lo %s. " % nonce() + tag + "\n") + "\n".join(
        "Dong %d: he thong ban cong cu AI theo credit, hang doi job, worker GPU." % i for i in range(1, 70))
    return [{"role": "user", "content": than + "\n\nWrite a long, detailed explanation of the architecture above."}]


def lon(ky_tu: int, tag: str) -> list:
    return [{"role": "user", "content": "Ma lo lon %s %s.\n\n" % (nonce(), tag)
             + tai_lieu(ky_tu, random.SystemRandom().randint(0, 10**9)) + "\n\nSummarize in one sentence."}]


def goi(model: str, messages: list, max_tokens: int, dung: threading.Event | None = None,
        timeout: float = 900.0) -> dict:
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": True,
            "reasoning_effort": "low", "cache_prompt": True, "stream_options": {"include_usage": True}}
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    moc, text, reas, finish, timings, status, loi, huy = [], [], [], None, {}, None, None, False
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.status
            for line in r:
                if dung is not None and dung.is_set():
                    huy = True
                    break
                line = line.strip()
                if not line.startswith(b"data:") or line[5:].strip() == b"[DONE]":
                    continue
                try:
                    d = json.loads(line[5:].strip())
                except ValueError:
                    continue
                timings = d.get("timings") or timings
                for ch in d.get("choices") or []:
                    de = ch.get("delta") or {}
                    c, rc = de.get("content") or "", de.get("reasoning_content") or ""
                    if c or rc:
                        moc.append(time.time())
                    text.append(c)
                    reas.append(rc)
                    finish = ch.get("finish_reason") or finish
    except urllib.error.HTTPError as e:
        status, loi = e.code, (e.read() or b"")[:300].decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        loi = type(e).__name__ + ":" + str(e)[:200]
    return {"status": status, "loi": loi, "t0": t0, "t1": time.time(), "moc": moc, "huy": huy,
            "content": "".join(text), "reasoning": "".join(reas), "finish": finish, "timings": timings}


def ban_ngoai() -> list:
    """Tai ngoai tren B: slot dang xu ly o BAT KY model nao dang nap (khong goi model chua nap)."""
    ban = []
    try:
        run = json.load(urllib.request.urlopen(BASE + "/running", timeout=20)).get("running") or []
    except Exception as e:  # noqa: BLE001
        return ["running_loi:" + type(e).__name__]
    for m in run:
        ten = m.get("model")
        if m.get("state") != "ready":
            ban.append("%s:%s" % (ten, m.get("state")))
            continue
        try:
            sl = json.load(urllib.request.urlopen(BASE + "/upstream/%s/slots" % ten, timeout=20))
            n = sum(1 for x in sl if x.get("is_processing"))
            if n:
                ban.append("%s:%d slot ban" % (ten, n))
        except Exception as e:  # noqa: BLE001
            ban.append("%s:slots_loi:%s" % (ten, type(e).__name__))
    return ban


def cho_ranh(buoc: str, tran_giay: int = 3600):
    t0 = time.time()
    while True:
        b = ban_ngoai()
        if not b:
            return
        print("  [cho] %s: B ban %s (%.0f s)" % (buoc, b, time.time() - t0), flush=True)
        ghi(buoc="cho_ranh", truoc=buoc, ban=b)
        if time.time() - t0 > tran_giay:
            raise SystemExit("B ban qua lau truoc " + buoc)
        time.sleep(30)


def tom(k: dict) -> dict:
    t = k.get("timings") or {}
    return {"status": k["status"], "loi": k["loi"], "finish": k["finish"], "huy": k["huy"],
            "prompt_n": t.get("prompt_n"), "prompt_ms": t.get("prompt_ms"), "prompt_tps": t.get("prompt_per_second"),
            "pred_n": t.get("predicted_n"), "pred_ms": t.get("predicted_ms"), "pred_tps": t.get("predicted_per_second"),
            "draft_n": t.get("draft_n"), "draft_acc": t.get("draft_n_accepted"),
            "content_kt": len(k["content"]), "reasoning_kt": len(k["reasoning"]),
            "ttft": (k["moc"][0] - k["t0"]) if k["moc"] else None, "giay": k["t1"] - k["t0"]}


def rong(k: dict) -> bool:
    """Chu ky #27572: finish=stop ma content rong."""
    return k.get("status") == 200 and (k.get("finish") == "stop") and not (k.get("content") or "").strip()


def song_song(fs):
    kq = [None] * len(fs)

    def chay(i):
        kq[i] = fs[i]()
    ths = [threading.Thread(target=chay, args=(i,)) for i in range(len(fs))]
    [t.start() for t in ths]
    [t.join() for t in ths]
    return kq


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


class Do:
    def __init__(self, model: str, np_: int, ky_32k: int):
        self.model, self.np, self.ky = model, np_, ky_32k
        self.dem_rong = 0
        self.dem_luot = 0

    def g(self, buoc: str, messages, mt, **kw):
        k = goi(self.model, messages, mt, **kw)
        s = tom(k)
        self.dem_luot += 1
        if rong(k):
            self.dem_rong += 1
        ghi(buoc=buoc, model=self.model, np=self.np, rong_27572=rong(k), **s)
        return k, s

    def warm(self, muc_tieu: int = 32768):
        self.g("warm_ngan", ngan("warm"), 32)
        _, s = self.g("warm_32k", lon(self.ky, "warm"), 1)
        if s["prompt_n"]:
            self.ky = int(self.ky * muc_tieu / s["prompt_n"])
        print("  warm-up 32K: prompt_n=%s %.1f s -> ky_tu=%d" % (s["prompt_n"], (s["prompt_ms"] or 0) / 1000, self.ky),
              flush=True)
        return s

    def prefill(self, lan=3):
        ra = []
        for i in range(lan):
            _, s = self.g("prefill32k", lon(self.ky, "pf%d" % i), 1)
            ra.append(s)
            print("  prefill32k #%d: n=%s %.2f s (%.0f tok/s)" % (i, s["prompt_n"], (s["prompt_ms"] or 0) / 1000,
                                                                s["prompt_tps"] or 0), flush=True)
        return {"prefill32k_s": med([(s["prompt_ms"] or 0) / 1000 for s in ra]),
                "prefill32k_tps": med([s["prompt_tps"] for s in ra])}

    def don(self, lan=3, mt=1024):
        ra = []
        for i in range(lan):
            _, s = self.g("don", ngan("don%d" % i), mt)
            ra.append(s)
            print("  1 luong #%d: %.1f tok/s ra=%s finish=%s ttft=%.2f" % (i, s["pred_tps"] or 0, s["pred_n"],
                                                                          s["finish"], s["ttft"] or 0), flush=True)
        return {"don_tps": med([s["pred_tps"] for s in ra]), "don_ttft": med([s["ttft"] for s in ra])}

    def tong(self, lan=3, mt=1024, n=None):
        n = n or self.np
        tongs, moi = [], []
        for r in range(lan):
            ks = song_song([(lambda j=j, r=r: goi(self.model, ngan("tong%d-%d" % (r, j)), mt)) for j in range(n)])
            ss = [tom(k) for k in ks]
            for k, s in zip(ks, ss, strict=True):
                self.dem_luot += 1
                self.dem_rong += int(rong(k))
                ghi(buoc="tong", model=self.model, np=self.np, n=n, dot=r, rong_27572=rong(k), **s)
            dau = min((k["moc"][0] for k in ks if k["moc"]), default=None)
            cuoi = max((k["moc"][-1] for k in ks if k["moc"]), default=None)
            tok = sum((s["pred_n"] or 0) for s in ss)
            agg = tok / (cuoi - dau) if dau and cuoi and cuoi > dau else None
            tongs.append(agg)
            moi.extend(s["pred_tps"] for s in ss)
            print("  %d luong dot %d: moi luong %s | tong %.1f tok/s (%d tok)" % (
                n, r, "/".join("%.1f" % (s["pred_tps"] or 0) for s in ss), agg or 0, tok), flush=True)
            ghi(buoc="tong_dot", model=self.model, np=self.np, n=n, dot=r, tong_tps=agg, tok=tok)
        return {"tong_n": n, "tong_tps": med(tongs), "moi_luong_tps": med(moi),
                "moi_luong_min": round(min(x for x in moi if x), 1) if any(moi) else None}

    def lang(self, lan=3, mt_nho=2600, cho=8.0):
        n_nho = max(1, self.np - 1)
        kqs = []
        for r in range(lan):
            dung = threading.Event()
            nho = [None] * n_nho
            to = {}

            def chay_nho(j, nho=nho, r=r, dung=dung):
                nho[j] = goi(self.model, ngan("lang%d-%d" % (r, j)), mt_nho, dung=dung)

            def chay_to(to=to, r=r, dung=dung):
                time.sleep(cho)
                to["k"] = goi(self.model, lon(self.ky, "lang%d" % r), 64)
                time.sleep(3.0)
                dung.set()
            ths = [threading.Thread(target=chay_nho, args=(j,)) for j in range(n_nho)]
            ths.append(threading.Thread(target=chay_to))
            [t.start() for t in ths]
            [t.join() for t in ths]
            k2 = to["k"]
            s2 = tom(k2)
            self.dem_luot += 1
            if not k2["moc"] or not s2["prompt_ms"]:
                print("  lang dot %d: LOI job to %s" % (r, s2), flush=True)
                ghi(buoc="lang_loi", model=self.model, np=self.np, dot=r, **s2)
                continue
            w1 = k2["moc"][0]
            w0 = w1 - s2["prompt_ms"] / 1000.0
            lang_max, trong_tps, truoc_tps = [], [], []
            for j, k in enumerate(nho):
                m = k["moc"]
                # khoang lang dai nhat giao voi cua so prefill
                g = 0.0
                truoc = [x for x in m if x <= w0]
                sau = [x for x in m if x >= w1]
                trong = [x for x in m if w0 < x < w1]
                diem = ([truoc[-1]] if truoc else [w0]) + trong + ([sau[0]] if sau else [w1])
                for a, b in zip(diem, diem[1:], strict=False):
                    g = max(g, min(b, w1) - max(a, w0))
                lang_max.append(g)
                trong_tps.append(len(trong) / (w1 - w0))
                truoc_tps.append(len([x for x in m if w0 - 5 <= x <= w0]) / 5.0)
                ghi(buoc="lang_nho", model=self.model, np=self.np, dot=r, j=j, lang_max=g,
                    trong_tps=len(trong) / (w1 - w0), **tom(k))
            e = {"dot": r, "lang_max": max(lang_max), "trong_tps_min": min(trong_tps),
                 "trong_tps_tb": sum(trong_tps) / len(trong_tps), "truoc_tps_tb": sum(truoc_tps) / len(truoc_tps),
                 "prefill_s": s2["prompt_ms"] / 1000, "prompt_n": s2["prompt_n"]}
            ghi(buoc="lang", model=self.model, np=self.np, n_nho=n_nho, **e)
            kqs.append(e)
            print("  lang dot %d (%d nho + 32K): lang max %.2f s | nho trong prefill %.1f (min %.1f) tok/s, truoc %.1f"
                  " | prefill 32K %.1f s" % (r, n_nho, e["lang_max"], e["trong_tps_tb"], e["trong_tps_min"],
                                             e["truoc_tps_tb"], e["prefill_s"]), flush=True)
            time.sleep(2)
        return {"lang_n_nho": n_nho, "lang_max_s": med([e["lang_max"] for e in kqs]),
                "lang_trong_tps": med([e["trong_tps_tb"] for e in kqs]),
                "lang_truoc_tps": med([e["truoc_tps_tb"] for e in kqs]),
                "lang_prefill_s": med([e["prefill_s"] for e in kqs])}

    def mtp(self, lan=2, mt=1200, muc=16000):
        ky = int(self.ky * muc / 32768)
        rong_n = length_rong = tong = 0
        acc0 = 0
        for r in range(lan):
            def mot(j, r=r):
                sysp = "You are an agent. Reference material follows.\n\n" + tai_lieu(ky, random.SystemRandom().randint(0, 10**9))
                return goi(self.model, [{"role": "system", "content": "Session %s.\n" % nonce() + sysp},
                                        {"role": "user", "content": "[%d] Say hello and list what you can help with, one line." % j}], mt)
            ks = song_song([(lambda j=j: mot(j)) for j in range(self.np)])
            for k in ks:
                s = tom(k)
                tong += 1
                self.dem_luot += 1
                b = rong(k)
                rong_n += int(b)
                self.dem_rong += int(b)
                length_rong += int(k["finish"] == "length" and not k["content"].strip())
                if s["draft_n"] and not s["draft_acc"]:
                    acc0 += 1
                ghi(buoc="mtp27572", model=self.model, np=self.np, dot=r, rong_27572=b, **s)
            print("  mtp dot %d: %s" % (r, " | ".join("%s c=%d r=%d n=%s acc=%s/%s" % (
                k["finish"], len(k["content"]), len(k["reasoning"]), (k["timings"] or {}).get("prompt_n"),
                (k["timings"] or {}).get("draft_n_accepted"), (k["timings"] or {}).get("draft_n")) for k in ks)), flush=True)
        return {"mtp_luot": tong, "mtp_rong_stop": rong_n, "mtp_rong_length": length_rong, "mtp_acc0": acc0}


def main():
    global BASE, RA, NHAN
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--model", required=True)
    ap.add_argument("--np", type=int, required=True)
    ap.add_argument("--nhan", required=True)
    ap.add_argument("--ra", default="ket_qua")
    ap.add_argument("--buoc", default="prefill,don,tong,lang,mtp")
    ap.add_argument("--ky", type=int, default=100000)
    ap.add_argument("--mtp-mt", type=int, default=1200)
    a = ap.parse_args()
    BASE, NHAN = a.base, a.nhan
    RA = pathlib.Path(a.ra) / ("%s_%s.jsonl" % (a.model, a.nhan))
    RA.parent.mkdir(parents=True, exist_ok=True)
    d = Do(a.model, a.np, a.ky)
    print("===== %s %s np=%d =====" % (a.model, a.nhan, a.np), flush=True)
    t0 = time.time()
    tong_hop = {"model": a.model, "nhan": a.nhan, "np": a.np}
    cho_ranh("warm")
    tong_hop["warm"] = d.warm()
    buoc = a.buoc.split(",")
    for b in ("prefill", "don", "tong", "lang", "mtp"):
        if b in buoc:
            cho_ranh(b)
            tong_hop.update(d.mtp(mt=a.mtp_mt) if b == "mtp" else getattr(d, b)())
    tong_hop["rong_27572_tat_ca"] = d.dem_rong
    tong_hop["luot_tat_ca"] = d.dem_luot
    tong_hop["giay"] = round(time.time() - t0)
    ghi(buoc="TONG_HOP", **tong_hop)
    print("TONG_HOP " + json.dumps(tong_hop, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
