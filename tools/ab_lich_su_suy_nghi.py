"""ab_lich_su_suy_nghi.py — A/B giữ/bỏ suy nghĩ trong lịch sử cho LTT-3.5 (S2 §2.5, R-17). Đo thẳng engine.

    python tools/ab_lich_su_suy_nghi.py --base http://127.0.0.1:18280 --bien-the A --ra <tệp.json>
    python tools/ab_lich_su_suy_nghi.py --so-sanh A.json B.json

Biến thể A = yaml hiện tại; B = hồ sơ `qwen35-api` thêm `--no-reasoning-preserve` (đổi bằng
`llm_gateway/deploy/ma_tran_cache.ps1`, phép đo có hoàn nguyên). Tool này KHÔNG đổi cấu hình máy B.

Hai phần:
  chất lượng    — bộ đề `danh_gia_llm.py` (12 bài × `--lan`), chấm cùng hàm chấm ⇒ so được với số cũ.
  tool liên tục — 10 kịch bản agent nhiều lượt, dựng TẤT ĐỊNH ở đây; lịch sử giữ `reasoning_content`
                  của lượt trước như client thật; chấm đúng tool + tham số khoá từng lượt.

Luật (khoá TRƯỚC khi đo, plan P3 T1c Step 4): B thắng nếu `chat_luong` và `tool_lien_tuc` của B không
thấp hơn A quá khoảng tin cậy Wilson 95 % **và** `token_ctx_p50` của B thấp hơn A. Ngược lại giữ A.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = "qwen35-api"


# ── Chấm (thuần) ─────────────────────────────────────────────────────────────

def cham_dap_an(tra_loi: str, dap_an: str) -> bool:
    # Biên: không dính chữ/số, và không là phần của số thập phân ("4.42", "42.5") — dấu chấm câu thì được.
    return bool(tra_loi) and re.search(
        r"(?<![\w])(?<!\d\.)" + re.escape(dap_an) + r"(?![\w])(?!\.\d)", tra_loi) is not None


def cham_tool(luot: list[dict], ky_vong: list[tuple[str, dict]]) -> tuple[int, int]:
    """Số lượt gọi đúng tool (tên + mọi tham số khoá) trên số lượt kỳ vọng."""
    dung = 0
    for thuc, (ten, tham) in zip(luot, ky_vong, strict=False):  # lượt đứt giữa chừng ⇒ ngắn hơn
        goi = (thuc.get("tool_calls") or [{}])[0]
        if goi.get("name") == ten and all(goi.get("arguments", {}).get(k) == v for k, v in tham.items()):
            dung += 1
    return dung, len(ky_vong)


def wilson(dat: int, tong: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng tin cậy Wilson của tỉ lệ `dat/tong`."""
    if tong <= 0:
        return 0.0, 1.0
    p = dat / tong
    mau = 1 + z * z / tong
    tam = (p + z * z / (2 * tong)) / mau
    le = z * math.sqrt(p * (1 - p) / tong + z * z / (4 * tong * tong)) / mau
    return max(0.0, tam - le), min(1.0, tam + le)


def phan_quyet(a: dict, b: dict) -> dict:
    """Áp luật đã khoá. `a`/`b` là kết quả `ab()`."""
    def khong_thap_hon(ten_dat: str, ten_tong: str) -> bool:
        tb = b[ten_dat] / max(b[ten_tong], 1)
        _thap_a, _cao_a = wilson(a[ten_dat], a[ten_tong])
        return tb >= _thap_a
    cl = khong_thap_hon("chat_luong_dung", "tong")
    tl = khong_thap_hon("tool_lien_tuc_dung", "tool_tong")
    ctx = b["token_ctx_p50"] < a["token_ctx_p50"]
    return {"chat_luong_khong_thap_hon": cl, "tool_khong_thap_hon": tl,
            "ctx_thap_hon": ctx, "thang": "B" if (cl and tl and ctx) else "A"}


# ── Kịch bản tool nhiều lượt (tất định) ─────────────────────────────────────

TOOLS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a file",
     "parameters": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Replace text in a file",
     "parameters": {"type": "object", "required": ["path", "old", "new"], "properties": {
         "path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Run the test suite",
     "parameters": {"type": "object", "properties": {}}}},
]

HE_THONG = ("You are a coding agent. Work in steps: first read_file the file named by the user, then "
            "edit_file to fix exactly the bug described, then run_tests. Call exactly one tool per turn.")


def _kich_ban(i: int) -> dict:
    """Kịch bản thứ i: tệp, dòng lỗi, dòng sửa — sinh tất định."""
    tep = f"src/mod_{i}.py"
    cu = f"return a - b  # add_{i}"
    noi_dung = f"def add_{i}(a, b):\n    {cu}\n"
    return {"tep": tep, "nhac": f"The function add_{i} in {tep} subtracts instead of adding. Fix it.",
            "noi_dung": noi_dung,
            "ky_vong": [("read_file", {"path": tep}), ("edit_file", {"path": tep}), ("run_tests", {})]}


KET_QUA_TOOL = {"edit_file": "ok: 1 replacement", "run_tests": "12 passed"}


def _goi(base: str, than: dict, timeout: float) -> tuple[int, dict, float, float]:
    """Stream `/v1/chat/completions`; trả (mã, thông điệp gộp, TTFT, tổng giây)."""
    yc = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions",
                                data=json.dumps({**than, "stream": True}).encode("utf-8"), method="POST",
                                headers={"Content-Type": "application/json", "User-Agent": "ltt-ab/1.0"})
    t0 = time.monotonic()
    ttft = 0.0
    msg: dict = {"content": "", "reasoning_content": "", "tool_calls": {}}
    timings: dict = {}
    try:
        with urllib.request.urlopen(yc, timeout=timeout) as r:
            for dong in r:
                s = dong.decode("utf-8", "replace").strip()
                if not s.startswith("data:") or s == "data: [DONE]":
                    continue
                ev = json.loads(s[5:])
                timings = ev.get("timings") or timings
                for ch in ev.get("choices") or []:
                    d = ch.get("delta") or {}
                    if not ttft and (d.get("content") or d.get("reasoning_content") or d.get("tool_calls")):
                        ttft = time.monotonic() - t0
                    msg["content"] += d.get("content") or ""
                    msg["reasoning_content"] += d.get("reasoning_content") or ""
                    for tc in d.get("tool_calls") or []:
                        o = msg["tool_calls"].setdefault(tc.get("index", 0), {"id": "", "name": "", "args": ""})
                        o["id"] = tc.get("id") or o["id"]
                        fn = tc.get("function") or {}
                        o["name"] += fn.get("name") or ""
                        o["args"] += fn.get("arguments") or ""
    except urllib.error.HTTPError as e:
        return e.code, {"loi": e.read().decode("utf-8", "replace")[:300]}, 0.0, time.monotonic() - t0
    except Exception as e:  # noqa: BLE001
        return 0, {"loi": f"{type(e).__name__}: {e}"}, 0.0, time.monotonic() - t0
    msg["timings"] = timings
    return 200, msg, ttft, time.monotonic() - t0


def chay_kich_ban(base: str, i: int, timeout: float) -> dict:
    kb = _kich_ban(i)
    lich_su: list[dict] = [{"role": "system", "content": HE_THONG}, {"role": "user", "content": kb["nhac"]}]
    luot: list[dict] = []
    ctx, cache, ttft = [], [], []
    for buoc in range(len(kb["ky_vong"])):
        ma, m, t, _g = _goi(base, {"model": MODEL, "messages": lich_su, "tools": TOOLS, "max_tokens": 4096}, timeout)
        if ma != 200:
            luot.append({"tool_calls": [], "loi": m.get("loi")})
            break
        tm = m.get("timings") or {}
        ctx.append(int(tm.get("prompt_n", 0)) + int(tm.get("cache_n", 0)))
        cache.append(int(tm.get("cache_n", 0)))
        ttft.append(t)
        goi = []
        for o in m["tool_calls"].values():
            try:
                args = json.loads(o["args"] or "{}")
            except ValueError:
                args = {"_hong": o["args"]}
            goi.append({"id": o["id"] or f"c{buoc}", "name": o["name"], "arguments": args})
        luot.append({"tool_calls": goi})
        if not goi:
            break
        # ⭐ Như client thật: giữ `reasoning_content` của lượt trước trong lịch sử.
        lich_su.append({"role": "assistant", "content": m["content"], "reasoning_content": m["reasoning_content"],
                        "tool_calls": [{"id": g["id"], "type": "function", "function": {
                            "name": g["name"], "arguments": json.dumps(g["arguments"])}} for g in goi[:1]]})
        kq = kb["noi_dung"] if goi[0]["name"] == "read_file" else KET_QUA_TOOL.get(goi[0]["name"], "error: unknown tool")
        lich_su.append({"role": "tool", "tool_call_id": goi[0]["id"], "content": kq})
    dung, tong = cham_tool(luot, kb["ky_vong"])
    return {"kich_ban": i, "dung": dung, "tong": tong, "ctx": ctx, "cache": cache, "ttft": ttft, "luot": luot}


def ab(base: str, bien_the: str, lan: int, timeout: float = 600.0) -> dict:
    from tools import danh_gia_llm as D

    thu = D.thu_thap(base, "", MODEL, lan, timeout)
    tam = GOC / "tmp" / f"ab_suy_nghi_{bien_the}_thu_thap.json"
    tam.parent.mkdir(exist_ok=True)
    tam.write_text(json.dumps(thu, ensure_ascii=False), encoding="utf-8")
    cl = D.cham(tam)
    kb = [chay_kich_ban(base, i, timeout) for i in range(10) for _ in range(3)]
    ctx = [c for k in kb for c in k["ctx"]] or [0]
    cache = [c for k in kb for c in k["cache"]] or [0]
    ttft = [t for k in kb for t in k["ttft"]] or [0.0]
    return {"bien_the": bien_the, "chat_luong_dung": cl["tong_dat"], "tong": cl["tong"],
            "tool_lien_tuc_dung": sum(k["dung"] for k in kb), "tool_tong": sum(k["tong"] for k in kb),
            "token_ctx_p50": int(statistics.median(ctx)), "cache_n_p50": int(statistics.median(cache)),
            "ttft_p50_s": round(statistics.median(ttft), 3), "kich_ban": kb}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base", default="http://127.0.0.1:18280")
    p.add_argument("--bien-the", choices=("A", "B"))
    p.add_argument("--lan", type=int, default=3)
    p.add_argument("--ra", type=Path)
    p.add_argument("--so-sanh", nargs=2, type=Path)
    a = p.parse_args()
    if a.so_sanh:
        x, y = (json.loads(f.read_text(encoding="utf-8")) for f in a.so_sanh)
        print(json.dumps(phan_quyet(x, y), ensure_ascii=False, indent=2))
        return 0
    if not (a.bien_the and a.ra):
        p.error("can --bien-the va --ra (hoac --so-sanh)")
    kq = ab(a.base, a.bien_the, a.lan)
    a.ra.write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print({k: v for k, v in kq.items() if k != "kich_ban"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
