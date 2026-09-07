"""
theo_doi_may_b.py — hộp đen cho máy B trong lúc chạy lô đo. Qua Nexus, không SSH.

    python theo_doi_may_b.py --giay 10 --phut 60
    python theo_doi_may_b.py doc            # doc lai va tom tat

## Vì sao KHÔNG bật SSH cho việc này

`Ket_noi.md` §5: SSH trên máy B bị **cố ý** `DISABLED` ngày 27-08, sau khi nó tự
chết hai lần. Nó tồn tại cho **đúng một tình huống** — khi Nexus không còn chạy.
Nexus đang chạy.

⛔ Và SSH **không giải được** vấn đề đã hạ tôi hai lần hôm nay: ghi nhớ vận hành
   ghi rõ *"ssh và Start-Process đều chết theo phiên"*. Bật SSH là mở lại một bề
   mặt đã đóng để đổi lấy một công cụ hỏng theo đúng kiểu mình vừa phải đi vòng.

`metrics/gpu` qua Nexus trả lời trong ~50 ms và cho đủ thứ cần: VRAM, tải, nhiệt,
điện, xung. Việc thiếu không phải kênh — là **không ai ghi lại theo thời gian**.

## Ghi gì, và vì sao ghi từng dòng một

Mỗi mẫu là **một dòng JSON**, `flush` ngay. Cùng lý do hộp đen trên Desktop máy A
làm vậy: thứ ta muốn đọc nhất là **mẫu cuối trước khi máy chết**, và một bộ đệm
chưa xả thì đúng mẫu đó là mẫu bị mất.

⚠️ Dấu thời gian ghi **UTC**, cùng quy ước hộp đen máy A. Máy ở UTC+7.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import nexus_may_b as N                                          # noqa: E402

MAC_DINH = pathlib.Path(__file__).parent.parent / "artifacts" / "theo_doi_may_b.jsonl"


def mot_mau() -> dict:
    t = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        ma, tra = N.goi("metrics/gpu", timeout=20)
    except N.LoiNexus as e:
        return {"t": t, "loi": str(e)[:120]}
    if ma != 200:
        return {"t": t, "loi": f"HTTP {ma}"}
    g = ((json.loads(tra).get("data") or {}).get("gpus") or [{}])[0]
    return {"t": t,
            "vram_mb": g.get("vram_used_mb"), "vram_tong": g.get("vram_total_mb"),
            "tai_pct": g.get("utilization_gpu_pct"),
            "mem_pct": g.get("utilization_mem_pct"),
            "nhiet_c": g.get("temperature_c"),
            "dien_w": g.get("power_draw_w"), "tran_w": g.get("power_limit_w")}


def lenh_ghi(a) -> int:
    ra = pathlib.Path(a.ra); ra.parent.mkdir(parents=True, exist_ok=True)
    het = time.monotonic() + a.phut * 60
    n = 0
    print(f"Ghi moi {a.giay}s trong {a.phut} phut -> {ra}")
    with ra.open("a", encoding="utf-8") as f:
        while time.monotonic() < het:
            m = mot_mau()
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
            f.flush()                       # xem docstring: mau cuoi la mau quan trong nhat
            n += 1
            if n % 6 == 0:
                print(f"  {m.get('t')}  VRAM {m.get('vram_mb')}  tai {m.get('tai_pct')}%  "
                      f"{m.get('nhiet_c')}C  {m.get('dien_w')}W")
            time.sleep(a.giay)
    print(f"Xong: {n} mau")
    return 0


def lenh_doc(a) -> int:
    ra = pathlib.Path(a.ra)
    if not ra.exists():
        print("Chua co ban ghi nao.", file=sys.stderr); return 1
    mau = [json.loads(d) for d in ra.read_text(encoding="utf-8").splitlines() if d.strip()]
    tot = [m for m in mau if "loi" not in m]
    print(f"{len(mau)} mau, {len(mau)-len(tot)} loi | {mau[0]['t']} -> {mau[-1]['t']} (UTC)")
    if not tot:
        return 0
    for ten, khoa, dv in (("VRAM", "vram_mb", "MB"), ("tai", "tai_pct", "%"),
                          ("nhiet", "nhiet_c", "C"), ("dien", "dien_w", "W")):
        v = [m[khoa] for m in tot if m.get(khoa) is not None]
        if v:
            print(f"  {ten:<6} min {min(v):>8}  tb {sum(v)/len(v):>8.1f}  max {max(v):>8}  {dv}")
    # ⭐ Ba nguong nay khong phai trang tri: chung la ba cach may B da hong THAT.
    dinh = max((m.get("vram_mb") or 0) for m in tot)
    nong = max((m.get("nhiet_c") or 0) for m in tot)
    tran = max((m.get("tran_w") or 0) for m in tot)
    print("\nCanh bao:")
    print(f"  VRAM dinh {dinh} / 24576"
          + ("  <- SAT TRAN, nguy co OOM" if dinh > 23000 else "  (an toan)"))
    print(f"  nhiet dinh {nong}C"
          + ("  <- NONG, co the throttle" if nong >= 83 else "  (mat)"))
    if tran:
        cao = max((m.get("dien_w") or 0) for m in tot)
        print(f"  dien dinh {cao}/{tran}W"
              + ("  <- cham tran dien" if cao >= tran * 0.98 else ""))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("viec", nargs="?", default="ghi", choices=["ghi", "doc"])
    p.add_argument("--giay", type=float, default=10.0)
    p.add_argument("--phut", type=float, default=30.0)
    p.add_argument("--ra", default=str(MAC_DINH))
    a = p.parse_args()
    return (lenh_ghi if a.viec == "ghi" else lenh_doc)(a)


if __name__ == "__main__":
    raise SystemExit(main())
