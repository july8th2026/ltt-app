"""Do truc tiep engine may B (llama-swap 8280 qua tunnel SSH): effort co doi prompt khong.

Dung: python do_effort_b.py prompt|dai [n]
  prompt: max_tokens nho, doc so token prompt theo (cua, dang truong, muc).
  dai   : bai suy luan, doc output_tokens theo (dang truong, muc) o /v1/messages.
Khong dung khoa API nao: goi thang llama-swap tren loopback cua B.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import statistics
import subprocess
import sys
import time
import urllib.request

KEY = r"C:\Users\Thang Tuong\.ssh\nexus_b"
CONG = 18280
URL = f"http://127.0.0.1:{CONG}"
MODEL = "qwen38-api"
HE = "Ban la tro ly lap trinh ngan gon."
BAI_NGAN = "Chao ban, 2+2 bang may?"
BAI_DAI = ("Count the positive integers below 1000 divisible by 7 or by 11 but "
           "not by both. Show brief reasoning, then the final number.")


def mo_tunnel() -> subprocess.Popen:
    p = subprocess.Popen(
        ["ssh", "-i", KEY, "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
         "-N", "-L", f"{CONG}:127.0.0.1:8280", "lengo@192.168.2.66"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        try:
            urllib.request.urlopen(URL + "/running", timeout=2).read()
            return p
        except Exception:
            time.sleep(0.5)
    p.kill()
    raise SystemExit("tunnel khong len")


def goi(duong: str, than: dict, timeout: float = 600) -> dict:
    rq = urllib.request.Request(URL + duong, data=json.dumps(than).encode(),
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(rq, timeout=timeout) as r:
        return json.loads(r.read())


def than(cua: str, dang: str | None, muc: str | None, bai: str, max_ra: int) -> tuple[str, dict]:
    """dang: None | top | ctk | reasoning (Responses reasoning.effort)."""
    them: dict = {}
    if dang == "top":
        them["reasoning_effort"] = muc
    elif dang == "ctk":
        them["chat_template_kwargs"] = {"reasoning_effort": muc}
    elif dang == "reasoning":
        them["reasoning"] = {"effort": muc}
    if cua == "chat":
        return "/v1/chat/completions", {
            "model": MODEL, "max_tokens": max_ra, "stream": False,
            "messages": [{"role": "system", "content": HE},
                         {"role": "user", "content": bai}], **them}
    if cua == "messages":
        return "/v1/messages", {
            "model": MODEL, "max_tokens": max_ra, "stream": False, "system": HE,
            "messages": [{"role": "user", "content": bai}], **them}
    return "/v1/responses", {
        "model": MODEL, "max_output_tokens": max_ra, "stream": False,
        "instructions": HE, "input": [{"role": "user", "content": bai}], **them}


def so_token(cua: str, kq: dict) -> tuple[int, int]:
    u = kq.get("usage") or {}
    if cua == "chat":
        return u.get("prompt_tokens", -1), u.get("completion_tokens", -1)
    if cua == "messages":
        vao = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
        return vao, u.get("output_tokens", -1)
    return u.get("input_tokens", -1), u.get("output_tokens", -1)


def do_prompt(n: int) -> None:
    ca = [("chat", None, None), ("chat", "top", "low"), ("chat", "top", "xhigh"),
          ("messages", None, None), ("messages", "top", "low"),
          ("messages", "top", "xhigh"), ("messages", "ctk", "low"),
          ("messages", "ctk", "medium"), ("messages", "ctk", "xhigh"),
          ("responses", None, None), ("responses", "top", "low"),
          ("responses", "reasoning", "low"), ("responses", "reasoning", "xhigh"),
          ("responses", "ctk", "low")]
    for cua, dang, muc in ca:
        vao = []
        for _ in range(n):
            d, t = than(cua, dang, muc, BAI_NGAN, 1)
            vao.append(so_token(cua, goi(d, t))[0])
        print(f"{cua:9s} {str(dang):9s} {str(muc):6s} prompt_tokens={vao}")


def do_dai(n: int, cua: str = "messages") -> None:
    for dang, muc in (("top", "low"), ("top", "xhigh"), ("ctk", "low"), ("ctk", "xhigh")):
        def mot(_, dang=dang, muc=muc):
            d, t = than(cua, dang, muc, BAI_DAI, 6000)
            t0 = time.monotonic()
            vao, ra = so_token(cua, goi(d, t))
            return vao, ra, time.monotonic() - t0
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            kq = list(ex.map(mot, range(n)))
        ra = [k[1] for k in kq]
        print(f"{cua} {dang:4s} {muc:6s} prompt={sorted({k[0] for k in kq})} "
              f"output_tokens={ra} median={statistics.median(ra)}", flush=True)


if __name__ == "__main__":
    che_do = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    p = mo_tunnel()
    try:
        do_prompt(n) if che_do == "prompt" else do_dai(n, *(sys.argv[3:4] or ["messages"]))
    finally:
        p.kill()
