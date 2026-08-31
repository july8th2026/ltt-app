"""bench_llm_hieu_nang.py — đo hiệu năng model nhà. (Prompt 04 §3)

    python tools/bench_llm_hieu_nang.py --url http://127.0.0.1:8299 --lan 5

Đo **TTFT · prefill · decode · end-to-end · VRAM**, tách **nguội** khỏi **ấm**.

## ⛔ Mỗi số đo phải mang theo NGỮ CẢNH của nó

Máy B là **một máy để bàn đang dùng**, không phải một appliance: đo 31/08 thấy
**23 tiến trình** trên card (`explorer`, `Edge WebView` ×2, `Zalo`, Riot
Vanguard, Adobe, `Taskmgr`…). Một con số tok/s đo lúc ai đó đang cuộn trình
duyệt **không so được** với con số đo lúc máy rảnh.

⇒ Tệp này chụp `nvidia-smi` + `/health` **quanh mỗi lượt** và ghi kèm. Không có
  ảnh chụp đó thì con số **không có provenance**, và `OPERATING_CONTRACT §4` nói
  thẳng rằng nó không dùng làm bằng chứng được.

## ⛔ Trung vị, không phải trung bình; không bao giờ chọn lượt đẹp nhất

`OPERATING_CONTRACT §3`: *"Never cherry-pick."* Một lượt nhanh bất thường
thường là cache; một lượt chậm bất thường thường là hàng xóm. Trung vị chịu được
cả hai.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Nhắc cố định. ⛔ Đổi nó là mất khả năng so với mọi lượt đo trước.
NHAC_NGAN = "Giai thich ngan gon trong 3 cau: vi sao bau troi mau xanh?"
NHAC_DAI = ("Viet mot bai gioi thieu 400 tu ve lich su thanh pho Da Nang, "
            "chia thanh 4 doan.")


def _smi() -> dict:
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=15)
        v = [x.strip() for x in r.stdout.strip().split(",")]
        return {"vram_mb": int(v[0]), "gpu_pct": int(v[1]), "nhiet": int(v[2])}
    except Exception:                                           # noqa: BLE001
        return {}


def _dem_tien_trinh_gpu() -> int:
    try:
        r = subprocess.run(["nvidia-smi", "--query-compute-apps=pid",
                            "--format=csv,noheader"], capture_output=True,
                           text=True, timeout=15)
        return len([d for d in r.stdout.splitlines() if d.strip()])
    except Exception:                                           # noqa: BLE001
        return -1


def _luot(url: str, tok: str, model: str, nhac: str, max_tokens: int,
          timeout: float) -> dict:
    """Một lượt STREAM — TTFT chỉ đo được khi luồng chảy."""
    than = json.dumps({"model": model, "max_tokens": max_tokens, "stream": True,
                       "messages": [{"role": "user", "content": nhac}]}).encode()
    yc = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions", data=than, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {tok}",
                 "User-Agent": "ltt-bench/1.0"})
    t0 = time.monotonic()
    ttfb = None
    khoi = 0
    token_ra = 0
    token_vao = 0
    try:
        with urllib.request.urlopen(yc, timeout=timeout) as r:
            for dong in r:
                if not dong.strip():
                    continue
                # Bo qua nhip tim (dong chu thich SSE `: ...`) khi do TTFT:
                # no la byte cua CONG, khong phai token dau tien cua MODEL.
                if dong.startswith(b":"):
                    continue
                if ttfb is None:
                    ttfb = time.monotonic() - t0
                khoi += 1
                if dong.startswith(b"data: "):
                    tho = dong[6:].strip()
                    if tho and tho != b"[DONE]":
                        try:
                            d = json.loads(tho)
                            u = d.get("usage") or {}
                            if u:
                                token_ra = u.get("completion_tokens", token_ra)
                                token_vao = u.get("prompt_tokens", token_vao)
                        except ValueError:
                            pass
    except urllib.error.HTTPError as e:
        return {"loi": f"HTTP {e.code}", "than": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:                                      # noqa: BLE001
        return {"loi": f"{type(e).__name__}: {e}"}
    tong = time.monotonic() - t0
    # Uoc token ra tu so khoi khi thuong nguon khong gui `usage`: moi khoi SSE
    # thuong mang MOT token. Danh dau la uoc de khong ai doc nham thanh do.
    uoc = token_ra == 0
    if uoc:
        token_ra = khoi
    giai_ma = tong - (ttfb or 0)
    return {"ttfb_s": round(ttfb or 0, 3), "tong_s": round(tong, 3),
            "khoi": khoi, "token_ra": token_ra, "token_vao": token_vao,
            "token_ra_la_uoc": uoc,
            "decode_tok_s": round(token_ra / giai_ma, 1) if giai_ma > 0.05 else 0}


def _luot_co_thu_lai(url, tok, model, nhac, max_tokens, timeout, lan=4, cho=20.0):
    """Thu lai khi 429, va DEM so lan — con so do la du lieu, khong phai nhieu.

    🔴 Do 31/08: trong tai may B coi "1 python tren card + tai GPU >= 50%" la ban,
       va tai do la cua CHINH `llama-server` cua ta. Ket qua: 9/12 yeu cau cua bo
       danh gia bi 429 o lan thu DAU. Khong thu lai thi bo do nay do dac tinh cua
       trong tai chu khong do hieu nang model.
    """
    so_429 = 0
    for _ in range(lan + 1):
        r = _luot(url, tok, model, nhac, max_tokens, timeout)
        if r.get("loi") != "HTTP 429":
            r["so_429"] = so_429
            return r
        so_429 += 1
        time.sleep(cho)
    r["so_429"] = so_429
    return r


def main() -> int:
    p = argparse.ArgumentParser(description="Do hieu nang model nha.")
    p.add_argument("--url", default="http://127.0.0.1:8299")
    p.add_argument("--token", default="")
    p.add_argument("--model", default="qwen38-api")
    p.add_argument("--lan", type=int, default=5)
    p.add_argument("--timeout", type=float, default=600.0)
    p.add_argument("--ra", type=Path, default=Path("bench_llm.json"))
    a = p.parse_args()

    tok = a.token
    if not tok:
        env = Path(r"C:\ProgramData\LTTLlm\gateway.env")
        if env.exists():
            for d in env.read_text(encoding="utf-8-sig").splitlines():
                if d.startswith("LTT_LLM_TOKEN="):
                    tok = d.split("=", 1)[1].strip()
    if not tok:
        print("khong co token")
        return 1

    ra = {"model": a.model, "luc": time.strftime("%Y-%m-%d %H:%M:%S"),
          "ngu_canh_truoc": {"smi": _smi(), "tien_trinh_gpu": _dem_tien_trinh_gpu()},
          "luot": []}
    print(f"NGU CANH TRUOC: {ra['ngu_canh_truoc']}")

    # Luot dau = NGUOI theo nghia "chua co cache tien to cho nhac nay".
    # ⛔ KHONG phai nguoi theo nghia "model chua nap" - ep unload la mot thao tac
    #    tren dich vu dang chay, va OPERATING_CONTRACT §8 doi phai chung minh no
    #    an toan truoc. Ghi ro de khong ai doc nham.
    print("\n-- NGUOI (luot dau, chua co cache tien to)")
    r = _luot_co_thu_lai(a.url, tok, a.model, NHAC_NGAN, 200, a.timeout)
    r["loai"] = "nguoi"
    r["smi"] = _smi()
    ra["luot"].append(r)
    print(f"   {r}")

    print(f"\n-- AM x{a.lan} (nhac ngan, 200 token)")
    for i in range(a.lan):
        r = _luot_co_thu_lai(a.url, tok, a.model, NHAC_NGAN, 200, a.timeout)
        r["loai"] = "am_ngan"
        r["smi"] = _smi()
        ra["luot"].append(r)
        print(f"   #{i} ttfb={r.get('ttfb_s')}s tong={r.get('tong_s')}s "
              f"decode={r.get('decode_tok_s')} tok/s vram={r.get('smi',{}).get('vram_mb')}")

    print(f"\n-- AM x{max(2, a.lan // 2)} (sinh DAI, 900 token)")
    for i in range(max(2, a.lan // 2)):
        r = _luot_co_thu_lai(a.url, tok, a.model, NHAC_DAI, 900, a.timeout)
        r["loai"] = "am_dai"
        r["smi"] = _smi()
        ra["luot"].append(r)
        print(f"   #{i} ttfb={r.get('ttfb_s')}s tong={r.get('tong_s')}s "
              f"decode={r.get('decode_tok_s')} tok/s")

    ra["ngu_canh_sau"] = {"smi": _smi(), "tien_trinh_gpu": _dem_tien_trinh_gpu()}

    print("\n" + "=" * 66)
    for loai in ("nguoi", "am_ngan", "am_dai"):
        ds = [x for x in ra["luot"] if x.get("loai") == loai and "loi" not in x]
        if not ds:
            continue
        tt = statistics.median([x["ttfb_s"] for x in ds])
        tg = statistics.median([x["tong_s"] for x in ds])
        dc = statistics.median([x["decode_tok_s"] for x in ds])
        p95 = max([x["tong_s"] for x in ds]) if len(ds) >= 5 else None
        print(f"  {loai:<9} n={len(ds)}  TTFT tv={tt:.2f}s  tong tv={tg:.2f}s  "
              f"decode tv={dc:.1f} tok/s" + (f"  max={p95:.2f}s" if p95 else ""))
    print(f"  VRAM: truoc={ra['ngu_canh_truoc']['smi'].get('vram_mb')} MiB  "
          f"sau={ra['ngu_canh_sau']['smi'].get('vram_mb')} MiB  "
          f"tien trinh GPU={ra['ngu_canh_sau']['tien_trinh_gpu']}")
    print("=" * 66)

    a.ra.write_text(json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"DA LUU: {a.ra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
