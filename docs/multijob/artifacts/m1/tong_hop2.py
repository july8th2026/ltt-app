"""tong_hop2.py -- THROWAWAY (spike M-2). Doc ketqua_m2.jsonl, in bang tom tat."""
import json
import pathlib

P = pathlib.Path(__file__).with_name("ketqua_m2.jsonl")
for x in P.read_text(encoding="utf-8").splitlines():
    if not x.strip():
        continue
    r = json.loads(x)
    L, ten = r.get("loai"), r.get("cauhinh", "")
    if L == "nap":
        print("\n=== %-22s nap ok=%s %.1fs VRAM3090=%s slots=%s" % (
            ten, r.get("ok"), r.get("nap_s") or 0, (r.get("vram_sau_nap") or {}).get("0", {}).get("dung"),
            len(r.get("slots") or [])))
        if not r.get("ok"):
            for d in (r.get("log") or {}).get("duoi", [])[-8:]:
                print("     duoi:", d[:160])
    elif L == "c1":
        t = (r.get("kq") or {}).get("timings") or {}
        print("  C1  decode %.1f tok/s  spec %s/%s" % (t.get("predicted_per_second", 0),
                                                     t.get("draft_n_accepted"), t.get("draft_n")))
    elif L == "c4":
        print("  C4  tong %s tok/s  wall %.1fs" % (r.get("tok_s_tong"), r.get("wall") or 0))
    elif L == "wm3":
        w = r.get("whale") or {}
        wt = w.get("timings") or {}
        print("  WM3 whale %s tok: prefill %.1fs (%.0f tok/s) wall %s" % (
            r.get("whale_token"), (wt.get("prompt_ms") or 0) / 1000, wt.get("prompt_per_second", 0), w.get("wall")))
        for i, m in enumerate((r.get("tom") or {}).get("minnow", [])):
            print("      minnow%d: %s" % (i + 1, m))
    elif L == "anh":
        k = r.get("kq") or {}
        if r.get("kieu") == "mot_minh":
            t = k.get("timings") or {}
            print("  ANH mot minh: ma=%s wall=%s prompt_n=%s tra_loi=%r loi=%s" % (
                k.get("ma"), k.get("wall"), t.get("prompt_n"), (k.get("tra_loi") or "")[:90], k.get("loi")))
        else:
            a = k.get("anh") or {}
            tx = [((t or {}).get("timings") or {}).get("predicted_per_second") for t in k.get("text", [])]
            print("  ANH + 3 text: anh ma=%s wall=%s loi=%s | text tok/s=%s" % (
                a.get("ma"), a.get("wall"), a.get("loi"), tx))
        print("      vram_dinh=%s" % r.get("vram_dinh"))
    elif L == "tat":
        print("  tat: VRAM dinh=%s" % r.get("vram_dinh"))
    elif L in ("loi_bai", "loi_cauhinh", "loi_main", "bo", "bo_qua"):
        print("  !! %s %s %s" % (L, ten, (r.get("loi") or r.get("ly_do") or r.get("vi") or r.get("tb", ""))[:300]))
    elif L == "xong":
        print("\nXONG dung_giua_chung=%s vram=%s" % (r.get("dung_giua_chung"), r.get("vram")))
