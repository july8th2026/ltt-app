"""L-32: do nac effort 3.8 voi budget MAY CHU dat, than dung bang ma cay t1c.

Than khach -> chuan_hoa_suy_nghi -> dat_effort_cho_engine -> _dat_budget_may_chu
(executor gia goi dung ngan_sach.budget_suy_nghi_dong_bo) -> gui thang engine B.
Do: token suy nghi (tokenize khoi thinking tren chinh engine), token ra, do tre,
dung/sai. Dung: python do_l32.py [n] [cua...]
Ghi JSON tung luot vao do_l32_<cua>.jsonl.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import pathlib
import statistics
import sys
import time
import types

DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(DIR.resolve().parents[3]))  # goc kho
sys.path.insert(0, str(DIR))

from do_effort_b import goi, mo_tunnel  # noqa: E402
from apps.ltt_llm.ngan_sach import budget_suy_nghi_dong_bo  # noqa: E402
from platform_core.runtime_noi_bo import luong  # noqa: E402

EXE = types.SimpleNamespace(sync_thinking_budget=lambda p: budget_suy_nghi_dong_bo(
    p["model"], p["max_tokens"], p.get("reasoning_effort")))
HE = "You are a careful assistant."
BAI = {
    "domino": ("How many ways are there to tile a 3x8 rectangle with 1x2 dominoes? "
               "Work it out carefully, then give the final number.", ["153"]),
    "nhan": ("What is 17 * 23? Reply with just the number.", ["391"]),
    "thu_do": ("What is the capital city of Australia? Answer in one word.", ["canberra"]),
}
MAX_RA = 8000


def than_khach(cua: str, muc: str, bai: str) -> tuple[str, dict]:
    if cua == "messages":
        return "/v1/messages", {"model": "ltt-3.8", "max_tokens": MAX_RA, "stream": False,
                                "system": HE, "reasoning_effort": muc,
                                "messages": [{"role": "user", "content": bai}]}
    if cua == "responses":
        return "/v1/responses", {"model": "ltt-3.8", "max_output_tokens": MAX_RA,
                                 "stream": False, "instructions": HE,
                                 "reasoning": {"effort": muc},
                                 "input": [{"role": "user", "content": bai}]}
    return "/v1/chat/completions", {"model": "ltt-3.8", "max_tokens": MAX_RA,
                                    "stream": False, "reasoning_effort": muc,
                                    "messages": [{"role": "system", "content": HE},
                                                 {"role": "user", "content": bai}]}


def tach(cua: str, kq: dict) -> tuple[str, str, int]:
    """(suy nghi, tra loi, token ra)."""
    if cua == "messages":
        nghi = "".join(b.get("thinking", "") for b in kq.get("content", [])
                       if b.get("type") == "thinking")
        tl = "".join(b.get("text", "") for b in kq.get("content", [])
                     if b.get("type") == "text")
        return nghi, tl, kq["usage"]["output_tokens"]
    if cua == "responses":
        nghi, tl = "", ""
        for it in kq.get("output", []):
            for c in it.get("content", []) or []:
                if c.get("type") in ("reasoning_text",):
                    nghi += c.get("text", "")
                elif c.get("type") == "output_text":
                    tl += c.get("text", "")
            for c in it.get("summary", []) or []:
                nghi += c.get("text", "")
        return nghi, tl, kq["usage"]["output_tokens"]
    m = kq["choices"][0]["message"]
    return m.get("reasoning_content") or "", m.get("content") or "", kq["usage"]["completion_tokens"]


def dem(txt: str) -> int:
    if not txt:
        return 0
    return len(goi("/upstream/qwen38-api/tokenize", {"content": txt})["tokens"])


def mot(cua: str, muc: str, ten_bai: str) -> dict:
    bai, dap = BAI[ten_bai]
    duong, than = than_khach(cua, muc, bai)
    gui, _ = luong.chuan_hoa_suy_nghi(than, "ltt-3.8")
    luong.dat_effort_cho_engine(gui, duong)
    luong._dat_budget_may_chu(gui, duong, EXE, "ltt-3.8", MAX_RA)
    gui["model"] = "qwen38-api"
    t0 = time.monotonic()
    kq = goi(duong, gui, timeout=900)
    tre = time.monotonic() - t0
    nghi, tl, ra = tach(cua, kq)
    return {"cua": cua, "muc": muc, "bai": ten_bai, "tre_s": round(tre, 1),
            "token_ra": ra, "token_nghi": dem(nghi), "token_tra_loi": dem(tl),
            "dung": any(d in tl.lower() for d in dap), "tra_loi_duoi": tl[-80:],
            "budget_gui": gui.get("thinking") or gui.get("reasoning_budget_tokens")}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    cac_cua = sys.argv[2:] or ["messages"]
    cac_bai = [b for b in BAI if b in (__import__("os").environ.get("BAI_L32") or ",".join(BAI)).split(",")]
    p = mo_tunnel()
    try:
        for cua in cac_cua:
            f = (DIR / f"do_l32_{cua}.jsonl").open("a", encoding="utf-8")
            for ten_bai in cac_bai:
                for muc in ("low", "medium", "xhigh"):
                    with cf.ThreadPoolExecutor(max_workers=2) as ex:
                        kq = list(ex.map(mot, [cua] * n, [muc] * n, [ten_bai] * n))
                    for k in kq:
                        f.write(json.dumps(k, ensure_ascii=False) + "\n")
                    f.flush()
                    nghi = [k["token_nghi"] for k in kq]
                    print(f"{cua:9s} {ten_bai:7s} {muc:6s} budget={kq[0]['budget_gui']} "
                          f"nghi={nghi} max={max(nghi)} med_nghi={statistics.median(nghi)} "
                          f"med_ra={statistics.median(k['token_ra'] for k in kq)} "
                          f"med_tre={statistics.median(k['tre_s'] for k in kq)}s "
                          f"dung={sum(k['dung'] for k in kq)}/{n}", flush=True)
    finally:
        p.kill()
