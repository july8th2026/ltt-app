"""do_do_tre_anh.py - do DO TRE MA HOA ANH tren GPU (phep do D-4).

## Vi sao cong cu nay ton tai

Ngay 28/09/2026 ta GO tran dem so anh (`max_images = 4`) va thay bang ngan sach
KV. Ngan sach ay dung cho KV, nhung no KHONG chan duoc mot ca:

    200 anh 64x64  =  ~1.600 token KV  (vua moi ngan sach)
                   =  200 luot ma hoa mmproj NOI TIEP

`mtmd_context` la DUNG CHUNG cho moi slot (`server-context.cpp:1173,1308`), nen
200 luot ma hoa lam ngheo cac slot khac trong suot thoi gian do. Va co whale
KHONG do ho: no bat theo `token_prefill_moi`, ma 1.600 token thi khong phai whale.

⇒ Rui ro ton du DA NHAN (ke hoach §7.2). Cong cu nay do MAU SO de - neu can -
  dung lai mot tran dem theo DO TRE, ⛔ khong theo KV va ⛔ khong go tay lai so 4.

## Phep do

Voi moi N, gui MOT request chua N anh CUNG kich thuoc, `max_tokens=1`, roi doc
`timings.prompt_ms` cua llama-server (qua `usage` cua cong may B neu co, khong
thi do dong ho tuong). Hieu giua N va N-1 la chi phi ma hoa mot anh.

⛔ Do o `-np 1` thi khong con dung: production chay `-np 3`/`-np 4`. Nen cong cu
   nay do tren cau hinh THAT va ghi ro rang so do la "co the bi tranh".

⭐ Chay TUAN TU, mot request mot luc: neu ta ban song song thi thu do duoc la
   trong tai, khong phai chi phi ma hoa.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.moi_truong_may_b import nap_env_may_b  # noqa: E402

CAU_HOI = "One word."


def _anh(rong: int, cao: int) -> str:
    from PIL import Image
    im = Image.linear_gradient("L").resize((rong, cao)).convert("RGB")
    d = io.BytesIO()
    im.save(d, format="PNG")
    return "data:image/png;base64," + base64.b64encode(d.getvalue()).decode()


def _goi(url: str, token: str, model: str, urls: list) -> tuple:
    than = {"model": model, "max_tokens": 1, "stream": False,
            "messages": [{"role": "user", "content":
                          [{"type": "image_url", "image_url": {"url": u}} for u in urls]
                          + [{"type": "text", "text": CAU_HOI}]}]}
    yc = urllib.request.Request(url + "/v1/chat/completions",
                                data=json.dumps(than).encode(),
                                headers={"content-type": "application/json",
                                         "authorization": f"Bearer {token}"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(yc, timeout=900) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return None, None, e.read().decode("utf-8", "replace")[:200]
    tuong_ms = (time.monotonic() - t0) * 1000.0
    vao = (d.get("usage") or {}).get("prompt_tokens")
    return tuong_ms, vao, None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen35-api")
    p.add_argument("--co", default="320x240", help="kich thuoc anh, vd 320x240")
    p.add_argument("--so", default="0,1,2,4,8,16,32",
                   help="cac gia tri N (so anh) do tuan tu")
    p.add_argument("--lap", type=int, default=3, help="so lan lap moi N")
    a = p.parse_args()

    env = dict(os.environ)
    print(nap_env_may_b(env))
    url = (env.get("LTT_LLM_BASE_URL") or "").rstrip("/")
    token = env.get("LTT_LLM_TOKEN") or ""
    if not url or not token:
        print("khong co duong vao cong may B")
        return 2

    rong, cao = (int(x) for x in a.co.split("x"))
    mot = _anh(rong, cao)
    cac_n = [int(x) for x in a.so.split(",")]

    # Luot ham: nap model + mtmd warmup. #27147 - lan ma hoa anh DAU TIEN cham
    # han vi warmup cua mtmd KHONG ma hoa thu mot anh nao.
    print("  (luot ham, khong tinh)")
    _goi(url, token, a.model, [mot])

    print(f"\n  anh {rong}x{cao}, model {a.model}, {a.lap} lan moi N, TUAN TU")
    print(f"  {'N':>4}{'tuong_ms (trung vi)':>22}{'token vao':>11}{'ms/anh them':>14}")
    print(f"  {'-' * 51}")
    truoc_ms = None
    truoc_n = None
    for n in cac_n:
        do = []
        vao = None
        for _ in range(a.lap):
            ms, v, loi = _goi(url, token, a.model, [mot] * n)
            if ms is None:
                print(f"  {n:>4}  LOI: {loi}")
                break
            do.append(ms)
            vao = v
        if not do:
            continue
        tv = statistics.median(do)
        them = ""
        if truoc_ms is not None and n > truoc_n:
            them = f"{(tv - truoc_ms) / (n - truoc_n):>13.1f}"
        print(f"  {n:>4}{tv:>22.1f}{vao if vao is not None else '?':>11}{them:>14}")
        truoc_ms, truoc_n = tv, n
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
