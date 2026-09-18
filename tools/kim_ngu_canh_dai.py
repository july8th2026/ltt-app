"""kim_ngu_canh_dai.py — kim trong đống cỏ 100K–200K token cho LTT-3.8 (llama.cpp #27756).

    python tools\\kim_ngu_canh_dai.py --base http://127.0.0.1:18280 --model qwen38-api \\
        --do-sau 100000,130000,160000,186368,200000 --ra <tệp.jsonl>

Nguồn (GitHub MCP, 18/09): ggml-org/llama.cpp#27756 (mở, chưa có PR sửa) — Qwen3.8-27B (64 lớp, 48
Gated DeltaNet) trên llama.cpp **im lặng phát EOS ngay token đầu** (`tokens_predicted=1`, content rỗng,
`stop_type=eos`) khi prompt vượt ~100–130K token; CPU và CUDA như nhau; vLLM cùng trọng số thì ĐẠT ⇒ lỗi
engine. Bình luận cuối (07/09): **không có ngưỡng sạch** — các "lỗ" không đơn điệu (96.519 hỏng trong khi
95.979 và 99.003 đạt), tất định theo số token ⇒ *"validate your exact serving depth(s)"*. Mặt thứ hai của
cùng lỗi: sinh tiếp nhưng lan man, không nhớ được sự kiện.

Đề giữ đúng công thức của issue (hai ghi chú đầu/cuối, bốn sự kiện: hai mã cổng, hai tên người) để số
so được với bảng của người báo; đống cỏ là đoạn văn lặp, đo số token THẬT bằng `/tokenize` của engine
(không ước ký tự). Mỗi độ sâu gửi `cache_prompt: false` và một muối riêng ở đầu ⇒ không lượt nào hưởng
cache tiền tố của lượt trước (issue: *"fresh server per probe, prefix-cache contamination excluded"*).

Gọi thẳng llama-swap trên máy B (qua `ssh -L 18280:127.0.0.1:8280`), đúng đường chat của khách (template
v22.5, suy nghĩ xhigh, budget 4096 của yaml) — không đổi cờ engine. Không tốn credit.
Mã thoát: 0 mọi độ sâu đạt · 3 có độ sâu hỏng · 2 không đo được.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Công thức của #27756 (bước 3 của issue), giữ nguyên chữ.
DOAN = ("The history of Luxembourg is shaped by its strategic position between larger powers, "
        "its fortress walls, and its evolution into a modern financial center. ")
GHI_DAU = ("IMPORTANT EARLY NOTE: The access code for the northern gate is ZEBRA-4711 "
           "and the librarian's name is Marlene. ")
GHI_CUOI = ("IMPORTANT LATE NOTE: The access code for the southern gate is FALCON-8802 "
            "and the archivist's name is Otto. ")
CAU_HOI = "\nQuestion: State both gate access codes and both staff names mentioned above."
SU_KIEN = ("ZEBRA-4711", "FALCON-8802", "Marlene", "Otto")


def dung_de(so_doan: int, muoi: str = "") -> str:
    """Đống cỏ: muối + ghi chú đầu + `so_doan//2` đoạn + ghi chú cuối + phần còn lại + câu hỏi."""
    nua = so_doan // 2
    dau = f"[probe {muoi}]\n" if muoi else ""
    return dau + GHI_DAU + DOAN * nua + GHI_CUOI + DOAN * (so_doan - nua) + CAU_HOI


def so_doan_cho(dich: int, token_moi_doan: float, token_khung: int) -> int:
    """Số đoạn để prompt ≈ `dich` token (khung = phần không phải đoạn lặp + template)."""
    return max(0, int(round((dich - token_khung) / token_moi_doan)))


def cham(text: str) -> int:
    """Số sự kiện (trên 4) xuất hiện trong câu trả lời."""
    t = (text or "").lower()
    return sum(1 for s in SU_KIEN if s.lower() in t)


def phan_loai(luot: dict) -> str:
    """`eos_tuc_thi` (dấu vân tay #27756) · `suy_giam` · `dat` · `het_token` · `khong_do_duoc`."""
    if luot.get("status") != 200:
        return "khong_do_duoc"
    text = luot.get("text") or ""
    n_ra = int(luot.get("token_ra") or 0)
    if not text.strip() and not (luot.get("reasoning") or "").strip() and n_ra <= 8:
        return "eos_tuc_thi"
    if cham(text) == len(SU_KIEN):
        return "dat"
    if luot.get("finish") == "length" and not text.strip():
        return "het_token"
    return "suy_giam"


# ── Mạng ─────────────────────────────────────────────────────────────────────

def _post(url: str, than: dict, timeout: float) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=json.dumps(than).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "ltt-kim/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {"loi": e.read()[:300].decode("utf-8", "replace")}
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return 0, {"loi": f"{type(e).__name__}: {e}"}


def dem_token(base: str, model: str, text: str) -> int:
    ma, d = _post(f"{base}/upstream/{model}/tokenize", {"content": text}, 300)
    if ma != 200:
        raise RuntimeError(f"tokenize HTTP {ma}: {d.get('loi')}")
    return len(d["tokens"])


def hieu_chinh(base: str, model: str) -> tuple[float, int]:
    """(token/đoạn, token khung) đo bằng tokenizer của engine."""
    a, b = dem_token(base, model, dung_de(200, "x")), dem_token(base, model, dung_de(1200, "x"))
    moi = (b - a) / 1000
    return moi, int(a - 200 * moi) + 40  # +40 ≈ khung template chat (system/assistant, <think>)


def mot_do_sau(base: str, model: str, dich: int, moi: float, khung: int, max_tokens: int,
               timeout: float) -> dict:
    n = so_doan_cho(dich, moi, khung)
    than = {"model": model, "max_tokens": max_tokens, "cache_prompt": False,
            "messages": [{"role": "user", "content": dung_de(n, f"{dich}-{time.time_ns() % 10**9}")}]}
    t0 = time.monotonic()
    ma, d = _post(f"{base}/v1/chat/completions", than, timeout)
    giay = time.monotonic() - t0
    if ma != 200:
        return {"dich": dich, "status": ma, "giay": round(giay, 1), "loi": d.get("loi")}
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    tm = d.get("timings") or {}
    us = d.get("usage") or {}
    return {"dich": dich, "so_doan": n, "status": ma, "giay": round(giay, 1),
            "prompt_n": us.get("prompt_tokens") or (tm.get("prompt_n", 0) + tm.get("cache_n", 0)),
            "cache_n": tm.get("cache_n"), "token_ra": us.get("completion_tokens") or tm.get("predicted_n"),
            "prefill_tok_s": round(tm.get("prompt_per_second") or 0, 1),
            "finish": ch.get("finish_reason"), "text": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or ""}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="http://127.0.0.1:18280")
    ap.add_argument("--model", default="qwen38-api")
    ap.add_argument("--do-sau", default="100000,130000,160000,186368,200000")
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--timeout", type=float, default=1800)
    ap.add_argument("--ra", required=True, type=pathlib.Path)
    a = ap.parse_args(argv)
    moi, khung = hieu_chinh(a.base, a.model)
    print(f"hieu chinh: {moi:.3f} token/doan, khung {khung}", flush=True)
    a.ra.parent.mkdir(parents=True, exist_ok=True)
    loai_ds = []
    for dich in (int(x) for x in a.do_sau.split(",")):
        r = mot_do_sau(a.base, a.model, dich, moi, khung, a.max_tokens, a.timeout)
        r["loai"] = phan_loai(r)
        r["su_kien"] = cham(r.get("text", ""))
        loai_ds.append(r["loai"])
        luu = {k: v for k, v in r.items() if k not in ("text", "reasoning")}
        luu["text_dau"] = (r.get("text") or "")[:300]
        luu["reasoning_ky_tu"] = len(r.get("reasoning") or "")
        with a.ra.open("a", encoding="utf-8") as f:
            f.write(json.dumps(luu, ensure_ascii=False) + "\n")
        print(json.dumps({k: luu.get(k) for k in ("dich", "prompt_n", "loai", "su_kien", "token_ra",
                                                   "finish", "giay", "prefill_tok_s")}), flush=True)
    if all(x == "khong_do_duoc" for x in loai_ds):
        return 2
    return 0 if all(x == "dat" for x in loai_ds) else 3


if __name__ == "__main__":
    sys.exit(main())
