r"""
k0_kiem_chung_resample.py — PHÉP ĐỐI CHỨNG cho K0: bước hạ tần số của chính tôi
có ăn mất điểm của VieNeu không.

    powershell -ExecutionPolicy Bypass -File .\setup\k0_kiem_chung_resample.ps1

## Vì sao phải có phép này trước khi tin kết quả K0

K0 chấm hai hệ ở **cùng một tần số**, và tần số ấy là 24 kHz — tần số gốc của
F5. Hệ quả là một **bất đối xứng do chính bộ chấm tạo ra**:

    F5     : 24 kHz  ->  (khong doi)     ->  DNSMOS tu ha ve 16 kHz   = 1 lan
    VieNeu : 48 kHz  ->  soxr ha ve 24   ->  DNSMOS tu ha ve 16 kHz   = 2 lan

Mỗi lần đổi tần số là một phép lọc, và mỗi phép lọc lấy đi một ít. Nếu bước
thừa ấy đủ để hạ DNSMOS thì kết quả *"F5 thắng DNSMOS 31–9"* **một phần là kết
quả của bộ chấm**, không phải của hai model — và K0 sẽ đưa ra một quyết định
chiến lược (K5, ~7.800 dòng) dựa trên một tạo tác.

⭐ Nâng F5 lên 48 kHz để tránh điều đó thì tệ hơn: nó tặng F5 một dải 12–24 kHz
   **rỗng** mà DNSMOS có thể đọc thành thiếu độ trong. Hạ xuống là lựa chọn ít
   sai hơn, nhưng "ít sai hơn" chưa phải "không sai" — nên phải ĐO.

## Cách đo

Chấm CHÍNH những tệp VieNeu đã sinh ở K0, hai lần:

    ① ở 48 kHz gốc  -> DNSMOS ha 48 -> 16   (mot lan)
    ② ha ve 24 kHz  -> DNSMOS ha 24 -> 16   (hai lan, dung nhu K0 da lam)

Chênh lệch giữa hai cột là **cái giá của bước thừa**, đo trên đúng dữ liệu của
K0 chứ không phải trên một mẫu khác.

⛔ Nếu chênh lệch ấy lớn hơn khoảng cách DNSMOS giữa hai hệ thì kết luận "F5
   thắng DNSMOS" **không đứng được**, và phải chấm lại theo cách khác.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", default="tmp/k0/vieneu")
    ap.add_argument("--k0", default="tmp/k0/ket_qua.json")
    ap.add_argument("--ra", default="tmp/k0/kiem_chung_resample.json")
    a = ap.parse_args(argv)

    import numpy as np
    import soundfile as sf

    from voice_sidecar import dnsmos

    if not dnsmos.co_san():
        print("THIEU model DNSMOS", file=sys.stderr)
        return 2

    try:
        import soxr
    except ImportError:
        print("THIEU soxr — phep doi chung nay can dung BO DOI TAN SO ma K0 da "
              "dung, khong duoc thay bang mot bo khac.", file=sys.stderr)
        return 2

    cac = sorted(glob.glob(os.path.join(a.wav, "*.wav")))
    if not cac:
        print(f"KHONG CO WAV trong {a.wav} — chay `k0_cham_mu.ps1` truoc.",
              file=sys.stderr)
        return 2

    goc, ha = [], []
    for i, p in enumerate(cac, 1):
        w, sr = sf.read(p, dtype="float32", always_2d=False)
        if getattr(w, "ndim", 1) > 1:
            w = w.mean(axis=1)
        d1 = dnsmos.cham(w, int(sr)) or {}
        w24 = np.asarray(soxr.resample(w, int(sr), 24000), dtype="float32")
        d2 = dnsmos.cham(w24, 24000) or {}
        if d1.get("ovrl") is None or d2.get("ovrl") is None:
            continue
        goc.append(float(d1["ovrl"]))
        ha.append(float(d2["ovrl"]))
        print(f"  [{i}/{len(cac)}] {os.path.basename(p):32} "
              f"{sr} Hz {d1['ovrl']:.4f}  ->  24k {d2['ovrl']:.4f}  "
              f"({d2['ovrl'] - d1['ovrl']:+.4f})")

    if not goc:
        print("KHONG CHAM DUOC GI", file=sys.stderr)
        return 1

    gia = statistics.mean(g - h for g, h in zip(goc, ha))
    print("\n" + "=" * 72)
    print("  GIA CUA BUOC HA TAN SO (chi VieNeu phai chiu)")
    print("=" * 72)
    print(f"  DNSMOS o 48 kHz goc : {statistics.mean(goc):.4f}")
    print(f"  DNSMOS sau khi ha   : {statistics.mean(ha):.4f}")
    print(f"  MAT DI              : {gia:+.4f}  (n={len(goc)})")

    ra = {"n": len(goc), "ovrl_48k": round(statistics.mean(goc), 5),
          "ovrl_24k": round(statistics.mean(ha), 5), "mat_di": round(gia, 5)}

    if os.path.isfile(a.k0):
        k0 = json.load(open(a.k0, encoding="utf-8"))
        f5 = [c["f5"]["dnsmos_ovrl"] for c in k0["cap"]
              if c["f5"].get("dnsmos_ovrl") is not None]
        vn = [c["vieneu"]["dnsmos_ovrl"] for c in k0["cap"]
              if c["vieneu"].get("dnsmos_ovrl") is not None]
        if f5 and vn:
            kc = statistics.mean(f5) - statistics.mean(vn)
            ra["khoang_cach_hai_he"] = round(kc, 5)
            print(f"\n  Khoang cach DNSMOS giua hai he (F5 - VieNeu): {kc:+.4f}")
            print(f"  Gia cua buoc ha tan so                      : {gia:+.4f}")
            if gia >= kc:
                print("\n  🔴 BUOC HA TAN SO LON HON HOAC BANG KHOANG CACH.")
                print("     => Ket luan 'F5 thang DNSMOS' KHONG dung duoc.")
                ra["ket_luan"] = "khong dung duoc"
            elif gia >= kc * 0.5:
                print("\n  ⚠️ Buoc ha tan so chiem HON MOT NUA khoang cach.")
                print("     => Khoang cach that nho hon nhieu so voi bang K0.")
                ra["ket_luan"] = "phai chiet khau nhieu"
            else:
                print(f"\n  ✅ Buoc ha tan so chi chiem "
                      f"{gia / kc * 100:.0f}% khoang cach.")
                print("     => Ket luan 'F5 thang DNSMOS' van dung, nhung "
                      "khoang cach that nho hon.")
                ra["ket_luan"] = "van dung, co chiet khau"

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ra, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
