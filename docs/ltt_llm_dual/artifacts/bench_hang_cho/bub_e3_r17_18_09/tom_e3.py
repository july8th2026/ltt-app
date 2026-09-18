"""Tom tat E3: dem loai/finish cua cong_mtp va e3_kim cho hai nhanh (on/off) + Fisher chinh xac cho rong_stop."""
import json
import math
import pathlib
import sys

R = pathlib.Path(__file__).parent / "ket_qua"


def doc(p):
    p = R / p
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def fisher(a, b, c, d):
    """p hai phia chinh xac cho bang [[a,b],[c,d]]."""
    n1, n2, k, n = a + b, c + d, a + c, a + b + c + d

    def pr(x):
        return math.comb(n1, x) * math.comb(n2, k - x) / math.comb(n, k)
    p0 = pr(a)
    return min(1.0, sum(pr(x) for x in range(max(0, k - n2), min(k, n1) + 1) if pr(x) <= p0 + 1e-12))


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 1)
    p = k / n
    d = 1 + z * z / n
    g = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0, g - w), 3), round(g + w, 3))


out = {}
for arm in ("on", "off"):
    cg = doc(f"e3_cong_{arm}_qwen38.jsonl")
    km = doc(f"e3_kim_{arm}.jsonl")
    c = {}
    for r in cg:
        c[r["loai"]] = c.get(r["loai"], 0) + 1
    w5 = [r for r in cg if r["w"] == "W5"]
    rong_cg = [r for r in cg if r["loai"].startswith("rong")]
    fin = {}
    for r in km:
        fin[str(r["finish"])] = fin.get(str(r["finish"]), 0) + 1
    rs = sum(r["rong_stop"] for r in km)
    rs_ctx10 = sum(r["rong_stop"] for r in km if r["ma_bai"] == "ctx-10")
    n_ctx10 = sum(r["ma_bai"] == "ctx-10" for r in km)
    out[arm] = {
        "cong_luot": len(cg), "cong_loai": c,
        "cong_rong": [(r["ma_bai"], r["lan"], r["finish"], r["content_ky_tu"], r["reasoning_ky_tu"]) for r in rong_cg],
        "cong_W5": f"{sum(bool(r['dung']) for r in w5)}/{len(w5)} dung",
        "cong_cham_dung": f"{sum(r['dung'] is True for r in cg)}/{sum(r['dung'] is not None for r in cg)}",
        "kim_luot": len(km), "kim_finish": fin, "kim_rong_stop": rs, "kim_rong_length": sum(r["rong"] and r["finish"] == "length" for r in km),
        "kim_dung": sum(r["dung"] for r in km), "kim_ctx10_rong_stop": f"{rs_ctx10}/{n_ctx10}",
        "kim_rong_stop_theo_kieu": {k: sum(r["rong_stop"] for r in km if r["kieu"] == k) for k in ("nguyen", "lanh")},
        "tong_rong_stop": rs + sum(1 for r in rong_cg if r["finish"] == "stop"),
        "tong_luot": len(km) + len(cg),
    }
    out[arm]["wilson_rong_stop"] = wilson(out[arm]["tong_rong_stop"], out[arm]["tong_luot"])
if all(out[a]["tong_luot"] for a in ("on", "off")):
    a, b = out["on"]["tong_rong_stop"], out["on"]["tong_luot"] - out["on"]["tong_rong_stop"]
    c, d = out["off"]["tong_rong_stop"], out["off"]["tong_luot"] - out["off"]["tong_rong_stop"]
    out["fisher_p_rong_stop_on_vs_off"] = round(fisher(a, b, c, d), 4)
json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
