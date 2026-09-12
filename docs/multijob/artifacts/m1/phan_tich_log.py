"""phan_tich_log.py -- THROWAWAY (multijob). Chay TREN MAY B. Chi in SO TONG HOP, khong in noi dung.

Nguon: H:/LTT_LLM/logs/llamaswap.log (output llama-server: print_timing / release)
       H:/LTT_LLM/logs/gateway.log (uvicorn access log)
"""
import collections
import datetime
import json
import os
import re

LOG = r"H:/LTT_LLM/logs"
R_PROMPT = re.compile(r"id\s+(\d+) \| task (\d+) \| prompt eval time =\s+([\d.]+) ms /\s+(\d+) tokens")
R_EVAL = re.compile(r"id\s+(\d+) \| task (\d+) \|\s+eval time =\s+([\d.]+) ms /\s+(\d+) tokens")
R_REL = re.compile(r"id\s+(\d+) \| task (\d+) \| stop processing: n_tokens = (\d+), truncated = (\d+)")
R_ACC = re.compile(r'"(GET|POST) (\S+) HTTP/1\.1" (\d{3})')


def pct(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    k = min(len(xs) - 1, max(0, int(round(p / 100.0 * (len(xs) - 1)))))
    return xs[k]


def tom(xs):
    return {"n": len(xs), "p50": pct(xs, 50), "p90": pct(xs, 90), "p99": pct(xs, 99),
            "max": max(xs) if xs else None, "tong": sum(xs)}


def main():
    kq = {}
    p = os.path.join(LOG, "llamaswap.log")
    st = os.stat(p)
    kq["llamaswap_log"] = {"byte": st.st_size,
                           "tao": datetime.datetime.fromtimestamp(st.st_ctime).isoformat(timespec="minutes")}
    task = collections.defaultdict(dict)
    dem = collections.Counter()
    with open(p, "rb") as f:
        for raw in f:
            s = raw.decode("utf-8", "replace")
            m = R_PROMPT.search(s)
            if m:
                t = task[m.group(2)]
                t["pms"], t["pn"] = float(m.group(3)), int(m.group(4))
                continue
            m = R_EVAL.search(s)
            if m:
                t = task[m.group(2)]
                t["ems"], t["en"] = float(m.group(3)), int(m.group(4))
                continue
            m = R_REL.search(s)
            if m:
                t = task[m.group(2)]
                t["ctx"], t["trunc"] = int(m.group(3)), int(m.group(4))
                continue
            for k, pat in (("nap_mmproj", "mmproj"), ("dev_cuda1", "CUDA1"),
                           ("using_device", "using device"), ("ctx_exceeded", "Context size has been exceeded"),
                           ("oom", "out of memory"), ("n_slots", "n_slots =")):
                if pat in s:
                    dem[k] += 1
    full = [t for t in task.values() if "pn" in t and "en" in t and "ctx" in t]
    prefill = [t["pn"] for t in full]
    ctx = [t["ctx"] for t in full]
    gen = [t["en"] for t in full]
    cache = [max(0, t["ctx"] - t["pn"] - t["en"]) for t in full]
    pms = [round(t["pms"] / 1000, 2) for t in full]
    total_s = [round((t["pms"] + t["ems"]) / 1000, 1) for t in full]
    kq["so_request"] = len(full)
    kq["prefill_moi_token"] = tom(prefill)
    kq["tong_ngu_canh_token"] = tom(ctx)
    kq["cache_trung_token"] = tom(cache)
    kq["sinh_ra_token"] = tom(gen)
    kq["prefill_giay"] = tom(pms)
    kq["tong_giay_moi_luot"] = tom(total_s)
    nguong = [1000, 4000, 8000, 16000, 32000, 64000, 128000]
    kq["so_luot_prefill_moi_vuot"] = {str(n): sum(1 for x in prefill if x > n) for n in nguong}
    kq["so_luot_ngu_canh_vuot"] = {str(n): sum(1 for x in ctx if x > n) for n in nguong}
    kq["ti_le_cache_trung_tren_ngu_canh"] = round(sum(cache) / sum(ctx), 3) if ctx else None
    kq["truncated"] = sum(1 for t in full if t.get("trunc"))
    kq["dem_dong"] = dict(dem)

    g = os.path.join(LOG, "gateway.log")
    acc = collections.Counter()
    with open(g, "rb") as f:
        for raw in f:
            m = R_ACC.search(raw.decode("utf-8", "replace"))
            if m and m.group(2).startswith("/v1/"):
                acc["%s %s %s" % (m.group(1), m.group(2), m.group(3))] += 1
    kq["gateway_v1_theo_duong_ma"] = dict(acc.most_common(30))
    gst = os.stat(g)
    kq["gateway_log"] = {"byte": gst.st_size,
                         "tao": datetime.datetime.fromtimestamp(gst.st_ctime).isoformat(timespec="minutes")}
    print(json.dumps(kq, ensure_ascii=True, indent=1))


if __name__ == "__main__":
    main()
