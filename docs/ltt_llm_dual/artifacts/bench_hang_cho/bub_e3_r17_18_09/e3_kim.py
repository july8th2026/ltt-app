"""E3 (18/09 toi): lap lai bai ngu canh dai cua `cong_mtp.py` (W5, ~54K token) nhieu lan de dem RONG, MTP bat vs tat.

    python e3_kim.py --base http://127.0.0.1:18381 --model qwen38-api --nhan on --ra e3_kim_on.jsonl

Bo luot (giong het o hai nhanh, khoa truoc khi do; than request = dung than cua cong_mtp.bo_de()):
  ctx-10 x 30 NGUYEN VAN (prompt tat dinh ⇒ tu luot 2 trung cache tien to — dung dieu kien lan rong 1/48 goc)
  ctx-10 x 8  LANH (nonce o DAU ⇒ prefill ~54K moi luot)
  ctx-50 x 5, ctx-90 x 5 nguyen van
Tron ngau nhien voi hat co dinh, `--song-song 2` (nhu cong_mtp goc). max_tokens 1400 (nhu cong_mtp).
Can `--goc` = cay co tools/cong_mtp.py (nhanh phien/kiem-dinh-ky).
Moi luot: finish, do dai content/reasoning, reasoning_tokens, completion_tokens, cache_n/prompt_n, draft_n/accepted, dung (chua ma kim).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

DAP = "XYLOPHONE-4417"


def goi(base: str, than: dict, timeout: float) -> dict:
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(than).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
            st = r.status
    except urllib.error.HTTPError as e:
        return {"status": e.code, "giay": time.monotonic() - t0, "loi": e.read()[:200].decode("utf-8", "replace")}
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return {"status": None, "giay": time.monotonic() - t0, "loi": type(e).__name__ + str(e)[:100]}
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    us = d.get("usage") or {}
    tm = d.get("timings") or {}
    return {"status": st, "giay": time.monotonic() - t0, "text": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or "", "tool_calls": msg.get("tool_calls") or [],
            "finish": ch.get("finish_reason"),
            "reasoning_tokens": (us.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "completion_tokens": us.get("completion_tokens"), "prompt_n": tm.get("prompt_n"), "cache_n": tm.get("cache_n"),
            "draft_n": tm.get("draft_n"), "draft_acc": tm.get("draft_n_accepted"), "pred_tps": tm.get("predicted_per_second")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--model", default="qwen38-api")
    ap.add_argument("--nhan", required=True)
    ap.add_argument("--ra", required=True, type=pathlib.Path)
    ap.add_argument("--goc", default=r"D:\LTTSTUDIOSAPP-kiem-dinh-ky")
    ap.add_argument("--song-song", type=int, default=2)
    ap.add_argument("--nguyen", type=int, default=30)
    ap.add_argument("--lanh", type=int, default=8)
    ap.add_argument("--khac", type=int, default=5)
    a = ap.parse_args()
    sys.path.insert(0, a.goc)
    from tools import cong_mtp  # noqa: PLC0415
    de = {b["ma_bai"]: b for b in cong_mtp.bo_de() if b["w"] == "W5"}
    assert set(de) == {"ctx-10", "ctx-50", "ctx-90"}, de.keys()
    viec = ([("ctx-10", "nguyen")] * a.nguyen + [("ctx-10", "lanh")] * a.lanh
            + [("ctx-50", "nguyen")] * a.khac + [("ctx-90", "nguyen")] * a.khac)
    random.Random(1809).shuffle(viec)
    khoa = threading.Lock()
    a.ra.parent.mkdir(parents=True, exist_ok=True)

    def mot(iv):
        i, (ma, kieu) = iv
        b = de[ma]
        msgs = json.loads(json.dumps(b["than"]["messages"]))
        if kieu == "lanh":
            msgs[0]["content"] = "Phien %d-%d.\n" % (time.time_ns(), random.SystemRandom().randint(0, 10**9)) + msgs[0]["content"]
        r = goi(a.base, {"model": a.model, "max_tokens": b["max_tokens"], "messages": msgs}, 900.0)
        text = (r.get("text") or "").strip()
        rong = r.get("status") == 200 and not text and not r.get("tool_calls")
        dong = {"nhan": a.nhan, "i": i, "ma_bai": ma, "kieu": kieu, "status": r.get("status"), "finish": r.get("finish"),
                "rong": rong, "rong_stop": rong and r.get("finish") == "stop", "dung": DAP in text,
                "content_ky_tu": len(text), "reasoning_ky_tu": len(r.get("reasoning") or ""),
                "reasoning_tokens": r.get("reasoning_tokens"), "completion_tokens": r.get("completion_tokens"),
                "prompt_n": r.get("prompt_n"), "cache_n": r.get("cache_n"), "draft_n": r.get("draft_n"),
                "draft_acc": r.get("draft_acc"), "pred_tps": r.get("pred_tps"), "giay": round(r.get("giay", 0), 1),
                "text_dau": text[:120], "reasoning_cuoi": (r.get("reasoning") or "")[-200:] if rong else None,
                "loi": r.get("loi"), "t": round(time.time(), 1)}
        with khoa:
            with a.ra.open("a", encoding="utf-8") as f:
                f.write(json.dumps(dong, ensure_ascii=False) + "\n")
            print("%s #%d %s %s st=%s fin=%s rong=%s dung=%s c=%d r=%d n=%s cache=%s %.1fs" % (
                a.nhan, i, ma, kieu, dong["status"], dong["finish"], rong, dong["dung"], dong["content_ky_tu"],
                dong["reasoning_ky_tu"], dong["prompt_n"], dong["cache_n"], dong["giay"]), flush=True)
        return dong

    with ThreadPoolExecutor(max_workers=a.song_song) as ex:
        kq = list(ex.map(mot, list(enumerate(viec))))
    tom = {"nhan": a.nhan, "luot": len(kq), "rong_stop": sum(k["rong_stop"] for k in kq),
           "rong_length": sum(k["rong"] and k["finish"] == "length" for k in kq),
           "dung": sum(k["dung"] for k in kq), "khong_200": sum(k["status"] != 200 for k in kq),
           "finish": {f: sum(k["finish"] == f for k in kq) for f in {k["finish"] for k in kq}}}
    print("TOM " + json.dumps(tom, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
