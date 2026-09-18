"""tong_hop_ttft_b.py — gộp TTFT p50/p95/p99 và sự kiện nạp nguội từ sổ lượt của cổng máy B (R-16).

    python tools\\tong_hop_ttft_b.py --so <gateway_err.log>... [--swap <llamaswap.log>...] [--tu 2026-09-17]

Nguồn số (không chép tay):
  * Sổ lượt: `llm_gateway/so_luot.py::ghi_so` ghi logger `llm_gateway.so` MỘT dòng JSON mỗi lượt
    (`<YYYY-mm-dd HH:MM:SS,ms> INFO llm_gateway.so {...}`), trong đó `ttft_s` do `api.py` đo:
    cửa stream bọc TRONG nhịp tim (byte thật đầu tiên), cửa đồng bộ = CẢ lượt (khách không thấy byte nào
    trước đó) ⇒ hai loại **không gộp chung** — tách theo `stream`.
  * TTL: `ttl` trong `llm_gateway/deploy/llama-swap.yaml` (đọc, không gõ số).
  * Nạp nguội — hai cách đếm, báo cả hai vì mỗi cách mù một phía:
      - `llamaswap.log`: dòng `<model> Unloading model, TTL of Ns reached` (log KHÔNG có giờ ⇒ chỉ đếm).
      - suy từ sổ: lượt đầu của một model sau khoảng lặng > TTL tính từ lượt trước của model đó (có giờ, có
        TTFT; mù với lưu lượng đi thẳng vào llama-swap không qua cổng, và với lần nạp do preload/unload tay).

⛔ Công cụ chỉ ĐO. Ngưỡng cảnh báo đề xuất sau khi có số (plan v2 Task 10, R-16), không đặt ở đây.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
from collections import defaultdict

GOC = pathlib.Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_DONG_SO = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d{3}) \w+ llm_gateway\.so (\{.*\})\s*$")
_TTL_YAML = re.compile(r"^\s*ttl:\s*(?:&\w+\s+)?(\d+)\s*$", re.M)
_UNLOAD = re.compile(r"<([\w.-]+)> Unloading model, TTL of (\d+)s reached")


def ttl_yaml(duong: pathlib.Path | None = None) -> int:
    """TTL (giây) của hồ sơ model trong yaml. Nhiều giá trị khác nhau ⇒ lỗi (không đoán)."""
    text = (duong or GOC / "llm_gateway/deploy/llama-swap.yaml").read_text(encoding="utf-8")
    gt = {int(x) for x in _TTL_YAML.findall(text)}
    if len(gt) != 1:
        raise ValueError(f"ttl trong yaml khong duy nhat: {sorted(gt)}")
    return gt.pop()


def doc_so(dong_iter, tu: dt.datetime | None = None) -> list[dict]:
    out = []
    for dong in dong_iter:
        m = _DONG_SO.match(dong)
        if not m:
            continue
        luc = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(microsecond=int(m.group(2)) * 1000)
        if tu and luc < tu:
            continue
        try:
            d = json.loads(m.group(3))
        except ValueError:
            continue
        d["_luc"] = luc
        out.append(d)
    out.sort(key=lambda r: r["_luc"])
    return out


def phan_vi(xs: list[float], q: float) -> float | None:
    """Phân vị kiểu nearest-rank (không nội suy — p95 là một lượt có thật)."""
    if not xs:
        return None
    s = sorted(xs)
    k = max(1, -(-len(s) * q // 100))  # ceil
    return s[int(k) - 1]


def danh_dau_nguoi(luot: list[dict], ttl: int) -> None:
    """Gắn `nguoi=True` cho lượt đầu của mỗi model sau khoảng lặng > ttl (và lượt đầu tiên của sổ = None)."""
    truoc: dict[str, dt.datetime] = {}
    for r in luot:
        m = r.get("model") or "?"
        t = truoc.get(m)
        r["nguoi"] = None if t is None else (r["_luc"] - t).total_seconds() > ttl
        truoc[m] = r["_luc"]


def tong_hop(luot: list[dict], ttl: int) -> dict:
    danh_dau_nguoi(luot, ttl)
    nhom: dict[tuple, list[dict]] = defaultdict(list)
    for r in luot:
        nhom[(r.get("model") or "?", "stream" if r.get("stream") else "dong_bo")].append(r)
    kq = {}
    for (model, loai), rs in sorted(nhom.items()):
        tt = [float(r["ttft_s"]) for r in rs if r.get("ttft_s") is not None and r.get("ma_http") == 200]
        am = [float(r["ttft_s"]) for r in rs if r.get("nguoi") is False and r.get("ttft_s") is not None
              and r.get("ma_http") == 200]
        nguoi = [r for r in rs if r.get("nguoi")]
        kq[f"{model}/{loai}"] = {
            "luot": len(rs), "luot_200_co_ttft": len(tt),
            "ttft_p50": phan_vi(tt, 50), "ttft_p95": phan_vi(tt, 95), "ttft_p99": phan_vi(tt, 99),
            "ttft_max": max(tt) if tt else None,
            "ttft_am_p95": phan_vi(am, 95),
            "nguoi_suy_tu_so": len(nguoi),
            "ttft_nguoi": [r.get("ttft_s") for r in nguoi],
            "ma_http": dict(sorted(_dem(r.get("ma_http") for r in rs).items(), key=lambda x: str(x[0]))),
            "huy": sum(1 for r in rs if r.get("huy")),
        }
    return kq


def _dem(xs) -> dict:
    d: dict = defaultdict(int)
    for x in xs:
        d[x] += 1
    return dict(d)


def dem_unload(dong_iter) -> dict[str, int]:
    d: dict[str, int] = defaultdict(int)
    for dong in dong_iter:
        m = _UNLOAD.search(dong)
        if m:
            d[m.group(1)] += 1
    return dict(d)


def _dong(duong: pathlib.Path):
    with duong.open(encoding="utf-8", errors="replace") as f:
        yield from f


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--so", nargs="+", type=pathlib.Path, required=True)
    ap.add_argument("--swap", nargs="*", type=pathlib.Path, default=[])
    ap.add_argument("--yaml", type=pathlib.Path)
    ap.add_argument("--tu", help="YYYY-mm-dd[ HH:MM] — chỉ lượt từ lúc này (giờ máy B)")
    a = ap.parse_args(argv)
    tu = dt.datetime.fromisoformat(a.tu) if a.tu else None
    ttl = ttl_yaml(a.yaml)
    luot = doc_so((d for p in a.so for d in _dong(p)), tu)
    kq = {"ttl_s": ttl, "tu": luot[0]["_luc"].isoformat() if luot else None,
          "den": luot[-1]["_luc"].isoformat() if luot else None, "nhom": tong_hop(luot, ttl),
          "unload_ttl_llamaswap": dem_unload(d for p in a.swap for d in _dong(p))}
    print(json.dumps(kq, ensure_ascii=False, indent=1, default=str))
    return 0 if luot else 2


if __name__ == "__main__":
    sys.exit(main())
