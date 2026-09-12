"""tong_hop.py -- THROWAWAY (spike M-1). Doc ketqua.jsonl, in bang tom tat."""
import json
import pathlib

P = pathlib.Path(__file__).with_name("ketqua.jsonl")
rows = [json.loads(x) for x in P.read_text(encoding="utf-8").splitlines() if x.strip()]


def g(d, *k, mac=None):
    for x in k:
        if not isinstance(d, dict):
            return mac
        d = d.get(x)
    return mac if d is None else d


def spec(t):
    if not t:
        return "-"
    dn, da = t.get("draft_n"), t.get("draft_n_accepted")
    return "%s/%s=%.0f%%" % (da, dn, 100.0 * da / dn) if dn else "-"


for r in rows:
    L, ten = r.get("loai"), r.get("cauhinh", "")
    if L == "bat_dau":
        print("BAT DAU  vram=%s  production=%s" % (r.get("vram"), r.get("production_dang_chay")))
    elif L == "nap":
        v = g(r, "vram_sau_nap", "0", "dung")
        print("\n=== %-18s nap ok=%s  %.1fs  VRAM3090 sau nap=%s MiB  slots=%s" % (
            ten, r.get("ok"), r.get("nap_s") or 0, v, r.get("slots")))
        for x in g(r, "log", "khop", mac=[]):
            if any(s in x for s in ("buffer size", "llama_memory_recurrent", "n_ctx_seq", "n_seq_max",
                                    "out of memory", "failed", "error")):
                print("      log:", x[:170])
        if not r.get("ok"):
            for x in g(r, "log", "duoi", mac=[])[-10:]:
                print("      duoi:", x[:170])
    elif L == "c1":
        t = g(r, "kq", "timings", mac={})
        print("  C1  ra=%s  decode=%.1f tok/s  prefill=%.0f tok/s  ttft~%.2fs  wall=%.1fs  spec=%s" % (
            t.get("predicted_n"), t.get("predicted_per_second", 0), t.get("prompt_per_second", 0),
            (t.get("prompt_ms") or 0) / 1000, g(r, "kq", "wall", mac=0), spec(t)))
    elif L == "c4":
        per = [x["timings"].get("predicted_per_second", 0) for x in r["kq"] if x and x.get("timings")]
        ttft = sorted(round(x["timings"].get("prompt_ms", 0) / 1000 + 0, 2) for x in r["kq"] if x and x.get("timings"))
        walls = sorted(round(x["wall"], 1) for x in r["kq"] if x and x.get("wall"))
        print("  C4  tong=%s tok/s  wall=%.1fs  moi-luong decode=%s  wall tung request=%s" % (
            r.get("tok_s_tong"), r.get("wall") or 0, [round(x, 1) for x in per], walls))
        loi = [x for x in r["kq"] if x and "loi" in x]
        if loi:
            print("      LOI:", loi[:2])
    elif L == "wm":
        tom = r.get("tom", {})
        w = g(r, "kq", "whale", mac={})
        wt = w.get("timings") or {}
        print("  WM  whale %s tok: prefill %.1fs (%.0f tok/s) wall=%s | minnow ttft=%s, token trong luc whale=%s @ %s tok/s, sau whale %s tok/s" % (
            r.get("whale_token"), (wt.get("prompt_ms") or 0) / 1000, wt.get("prompt_per_second", 0),
            w.get("wall"), tom.get("minnow_ttft"), tom.get("minnow_token_trong_luc_whale"),
            tom.get("minnow_tok_s_trong_luc_whale"), tom.get("minnow_tok_s_sau_whale")))
        for k in ("whale", "minnow"):
            if "loi" in g(r, "kq", k, mac={}):
                print("      LOI %s: %s" % (k, g(r, "kq", k, "loi")[:200]))
    elif L == "tat":
        print("  tat: VRAM dinh=%s  exit=%s" % (r.get("vram_dinh"), r.get("exit")))
    elif L in ("loi_bai", "loi_cauhinh", "loi_main", "bo", "bo_qua"):
        print("  !! %s %s %s" % (L, ten, (r.get("loi") or r.get("ly_do") or r.get("vi") or r.get("tb", ""))[:300]))
    elif L == "xong":
        print("\nXONG  dung giua chung=%s  vram=%s" % (r.get("dung_giua_chung"), r.get("vram")))
