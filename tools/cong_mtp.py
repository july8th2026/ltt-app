"""cong_mtp.py — cổng đúng/sai MTP × `-np` (S1 §4). Correctness > performance.

    python tools\\cong_mtp.py --base http://127.0.0.1:18280 --model qwen38-api --song-song 3 --lan 3 \\
        --ra docs/ltt_llm_dual/artifacts/serving_v2/s1_mtp_E0_qwen38_c3.jsonl [--doi-chung <jsonl E3>]

Bộ đề (khoá trước khi đo, tất định):
  W1 13K "giải thích mã" (chỉ đo rỗng/hỏng hình thức) · W2 bộ đề chấm thật của `tools/danh_gia_llm.py`
  (chữ, lập trình CHẠY THẬT, JSON, đếm dòng) · W3 JSON theo khuôn · W4 tool call · W5 ngữ cảnh dài (kim trong đống cỏ).

Mỗi lượt ghi một dòng JSONL: `w, ma_bai, lan, loai, dung, finish, content_ky_tu, reasoning_ky_tu, giay, status`.
`--doi-chung`: tệp kết quả E3 (np1, không MTP) — một bài ĐÚNG ở đối chứng ≥ 2/3 lượt mà SAI ở đây ⇒ `hong_noi_dung`.
Mã thoát: 0 đạt cổng · 3 trượt · 2 không đo được.
"""
from __future__ import annotations

from typing import cast

import argparse
import json
import pathlib
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Chép từ `platform_core/llm/admission.py::TRAN_IM_LANG_S` — test_1408 đối chiếu.
TRAN_IM_LANG_S = 900.0

_LAP = re.compile(r"(.{8,}?)\1{6,}", re.S)


def _hong_hinh_thuc(text: str, schema: dict | None) -> bool:
    if "�" in text or _LAP.search(text):
        return True
    if schema is not None:
        try:
            obj = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
        except ValueError:
            return True
        return not isinstance(obj, dict) or any(k not in obj for k in schema.get("required", []))
    return False


def phan_loai(luot: dict, *, max_tokens: int, dap_an: str | None, schema: dict | None,
              doi_chung_dung: bool | None) -> str:
    text = (luot.get("text") or "").strip()
    if not text and not luot.get("tool_calls"):
        rt = luot.get("reasoning_tokens") or len(luot.get("reasoning") or "") // 3
        if luot.get("finish") == "length" and rt >= 0.9 * max_tokens:
            return "rong_giai_thich"
        return "rong_khong_giai_thich"
    if text and _hong_hinh_thuc(text, schema):
        return "hong_noi_dung"
    if dap_an is not None and doi_chung_dung:
        if re.search(r"(?<![\w.])" + re.escape(dap_an) + r"(?![\w.])", text) is None:
            return "hong_noi_dung"
    return "ok"


def cong(ket_qua: list[dict], *, deadlock: int, ro_slot: int) -> dict:
    dem = {"rong_khong_giai_thich": 0, "hong_noi_dung": 0, "rong_giai_thich": 0, "ok": 0}
    for k in ket_qua:
        dem[k["loai"]] = dem.get(k["loai"], 0) + 1
    return {"dat": dem["rong_khong_giai_thich"] == 0 and dem["hong_noi_dung"] == 0 and deadlock == 0 and ro_slot == 0,
            **dem, "deadlock": deadlock, "ro_slot": ro_slot, "tong": len(ket_qua)}


# ── Bộ đề ────────────────────────────────────────────────────────────────────

def _code_blob(chars: int, seed: int) -> str:
    import random
    r = random.Random(seed)
    tu = "request queue worker scheduler latency cache token prompt decode prefill slot budget".split()
    out: list[str] = []
    while sum(len(x) + 1 for x in out) < chars:
        out.append("def f_%d(%s):\n    return %d  # %s" % (r.randint(1, 10**6), r.choice(tu), r.randint(0, 999),
                                                           " ".join(r.sample(tu, 5))))
    return "\n".join(out)[:chars]


def bo_de() -> list[dict]:
    """Danh sách bài: {w, ma_bai, than (không có model), max_tokens, cham (callable|None), schema}."""
    from tools import danh_gia_llm as G
    de = []
    for k in range(4):
        de.append({"w": "W1", "ma_bai": f"w1-{k}", "max_tokens": 1500, "cham": None, "schema": None,
                   "than": {"messages": [{"role": "user", "content": _code_blob(45000, 900 + k)
                                          + "\n\nExplain what these functions do in 5 bullet points."}]}})
    for b in cast(list[dict], G.BO_DE):
        nhac = b.get("nhac")
        w = "W5" if b["nhom"] == "ngu_canh_dai" else ("W3" if b["cham"] == "json_khop" else "W2")
        if b["nhom"] == "ngu_canh_dai":
            nhac = (G._dong_co(b["so_dong"], G.KIM, b["vi_tri"])
                    + "\n\nDoc ky van ban tren. Ma bi mat cua du an LTT la gi? Tra loi chi bang ma do.")
        fn = G.CHAM[b["cham"]]
        de.append({"w": w, "ma_bai": b["ma"], "max_tokens": 1400, "schema": None,
                   "cham": (lambda ra, tc, b=b, fn=fn: fn(b, {"ra": ra, "tool_calls": tc})[0]),
                   "than": {"messages": [{"role": "user", "content": nhac}]}})
    for b in G.BO_DE_TOOL:
        de.append({"w": "W4", "ma_bai": b["ma"], "max_tokens": 400, "schema": None,
                   "cham": (lambda ra, tc, b=b: G.cham_tool(b, {"ra": ra, "tool_calls": tc})[0]),
                   "than": {"tools": G.TOOLS, "messages": [{"role": "user", "content": b["nhac"]}]}})
    return de


# ── Chạy ─────────────────────────────────────────────────────────────────────

def _goi(base: str, model: str, bai: dict, timeout: float) -> dict:
    than = {"model": model, "max_tokens": bai["max_tokens"], **bai["than"]}
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(than).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
            st = r.status
    except urllib.error.HTTPError as e:
        return {"status": e.code, "giay": time.monotonic() - t0, "loi": e.read()[:200].decode("utf-8", "replace")}
    except TimeoutError:
        return {"status": None, "giay": time.monotonic() - t0, "loi": "timeout", "deadlock": True}
    except (urllib.error.URLError, OSError) as e:
        return {"status": None, "giay": time.monotonic() - t0, "loi": type(e).__name__}
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    ctd = (d.get("usage") or {}).get("completion_tokens_details") or {}
    return {"status": st, "giay": time.monotonic() - t0, "text": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or "", "tool_calls": msg.get("tool_calls") or [],
            "finish": ch.get("finish_reason"), "reasoning_tokens": ctd.get("reasoning_tokens")}


def doc_doi_chung(duong: pathlib.Path) -> dict[str, bool]:
    """ma_bai -> True nếu đối chứng đúng ≥ 2/3 số lượt đo được."""
    dem: dict[str, list[bool]] = {}
    for dong in duong.read_text("utf-8").splitlines():
        r = json.loads(dong)
        if r.get("dung") is not None:
            dem.setdefault(r["ma_bai"], []).append(bool(r["dung"]))
    return {k: sum(v) * 3 >= 2 * len(v) for k, v in dem.items() if v}


def chay(base: str, model: str, song_song: int, lan: int, ra: pathlib.Path,
         doi_chung: dict[str, bool] | None = None, timeout: float = TRAN_IM_LANG_S) -> dict:
    de = bo_de()
    viec = [(b, i) for i in range(lan) for b in de]
    ra.parent.mkdir(parents=True, exist_ok=True)
    khoa, ket, deadlock, khong_do = threading.Lock(), [], 0, 0

    def mot(bi):
        nonlocal deadlock, khong_do
        b, i = bi
        r = _goi(base, model, b, timeout)
        dung = None
        if r.get("status") == 200:
            loai = phan_loai(r, max_tokens=b["max_tokens"], dap_an=None, schema=b["schema"], doi_chung_dung=None)
            if b["cham"] is not None and loai == "ok":
                dung = bool(b["cham"](r.get("text") or "", r.get("tool_calls")))
                if not dung and (doi_chung or {}).get(b["ma_bai"]):
                    loai = "hong_noi_dung"
        else:
            loai = "khong_do_duoc"
        with khoa:
            deadlock += int(bool(r.get("deadlock")))
            khong_do += int(loai == "khong_do_duoc")
            if loai != "khong_do_duoc":
                ket.append({"loai": loai})
            with ra.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"w": b["w"], "ma_bai": b["ma_bai"], "lan": i, "model": model, "loai": loai,
                                    "dung": dung, "finish": r.get("finish"), "status": r.get("status"),
                                    "content_ky_tu": len(r.get("text") or ""),
                                    "reasoning_ky_tu": len(r.get("reasoning") or ""),
                                    "giay": round(r.get("giay", 0), 2), "loi": r.get("loi")},
                                   ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(max_workers=song_song) as ex:
        list(ex.map(mot, viec))
    time.sleep(10)
    ro_slot = _dang_xu_ly(base, model)
    kq = cong(ket, deadlock=deadlock, ro_slot=ro_slot)
    kq["khong_do_duoc"] = khong_do
    return kq


def _dang_xu_ly(base: str, model: str) -> int:
    """Số request engine còn đang xử lý sau khi mọi lượt đã xong (rò slot)."""
    try:
        with urllib.request.urlopen(f"{base}/upstream/{model}/metrics", timeout=20) as r:
            for dong in r.read().decode("utf-8", "replace").splitlines():
                if dong.startswith("llamacpp:requests_processing"):
                    return int(float(dong.split()[-1]))
    except (urllib.error.URLError, OSError, ValueError):
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:18280")
    ap.add_argument("--model", required=True)
    ap.add_argument("--song-song", type=int, default=3)
    ap.add_argument("--lan", type=int, default=3)
    ap.add_argument("--ra", required=True, type=pathlib.Path)
    ap.add_argument("--doi-chung", type=pathlib.Path)
    a = ap.parse_args(argv)
    dc = doc_doi_chung(a.doi_chung) if a.doi_chung else None
    kq = chay(a.base, a.model, a.song_song, a.lan, a.ra, dc)
    print(json.dumps(kq, ensure_ascii=False))
    if kq["tong"] == 0:
        return 2
    return 0 if kq["dat"] else 3


if __name__ == "__main__":
    sys.exit(main())
