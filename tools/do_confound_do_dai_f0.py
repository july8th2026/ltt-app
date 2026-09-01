r"""
do_confound_do_dai_f0.py — bao nhiêu phần của "-40% biểu cảm" là do ĐỘ DÀI, không
phải do nhân bản.

    powershell -ExecutionPolicy Bypass -File .\setup\do_confound_do_dai_f0.ps1

## Giả thuyết đang kiểm, và vì sao nó phải được kiểm TRƯỚC khi báo cáo

Baseline K4 đo `delta_f0_tan_tuong_doi_ti_le = -0,4556`, và tôi đã đọc nó thành
một sự thật về sản phẩm: *"giọng nhân bản chỉ giữ 54% biến thiên cao độ của
giọng thật"*.

⛔ Nhưng hai vế của phép trừ ấy **không cùng hình dạng**:

    ben trai  : mot cau, ~4 giay, sinh ra trong mot luot
    ben phai  : clip tham chieu — ~25 giay GHEP TU 3-7 DOAN THU RIENG,
                cach nhau boi khoang nghi 0,35 giay

Một bản ghép nhiều đoạn thu **đương nhiên** có độ tản F0 lớn hơn một câu đơn:
mỗi đoạn có ngữ điệu riêng, có thể thu ở buổi khác, và chỗ nối giữa hai đoạn là
một bước nhảy cao độ mà không câu nói tự nhiên nào có.

⇒ Nên một phần — có thể **phần lớn** — của −40% là *"dài so với ngắn"*, không
  phải *"nhân bản làm phẳng"*. Và đó là hai kết luận dẫn tới hai việc khác hẳn:
  cái đầu là một tạo tác của phép đo, cái sau là một khuyết tật của sản phẩm.

## Phép đo

Cắt clip tham chiếu thành những đoạn **dài bằng bản sinh ra** rồi đo lại độ tản
F0 trên từng đoạn. So ba con số:

    A. do tan F0 cua CA clip tham chieu (25 giay ghep)
    B. do tan F0 trung binh cua tung DOAN 4 giay trong chinh clip ay
    C. do tan F0 cua ban SINH RA (4 giay)

  · `A - B` là **cái giá của độ dài** — thuần tuý do phép đo.
  · `B - C` là phần còn lại, và **chỉ phần ấy** mới nói được gì về nhân bản.

⭐ Đây là cùng khuôn với phép đối chứng đã dùng cho K0 (`k0_kiem_chung_resample`):
   tách một confound do CHÍNH bộ đo tạo ra, bằng cách đo nó riêng, thay vì lập
   luận rằng nó nhỏ.

## ⛔ KHÔNG CHẠM GPU

Chạy trên tệp đã sinh (`tmp/k0/vieneu/*.wav`) và clip tham chiếu gốc.
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
    ap.add_argument("--clip-ref", default="tmp/giong_cu")
    ap.add_argument("--ra", default="tmp/confound_do_dai_f0.json")
    a = ap.parse_args(argv)

    import numpy as np
    import soundfile as sf

    from voice_sidecar import do_on_dinh

    cac = sorted(glob.glob(os.path.join(a.wav, "*.wav")))
    if not cac:
        print(f"KHONG CO WAV trong {a.wav}", file=sys.stderr)
        return 2

    theo_giong: dict = {}
    for p in cac:
        theo_giong.setdefault(os.path.basename(p).split("__")[0], []).append(p)

    ket = []
    print(f"{'giong':26} {'A ca clip':>10} {'B doan ngan':>12} "
          f"{'C sinh ra':>10} {'gia do dai':>11}")
    for ma, ds in sorted(theo_giong.items()):
        ref = os.path.join(a.clip_ref, f"{ma}.wav")
        if not os.path.isfile(ref):
            continue
        wr, srr = sf.read(ref, dtype="float32", always_2d=False)
        if getattr(wr, "ndim", 1) > 1:
            wr = wr.mean(axis=1)

        # A — cả clip tham chiếu
        ta = (do_on_dinh.do_on_dinh_f0(wr, int(srr)) or {}).get(
            "f0_tan_tuong_doi")
        if ta is None:
            continue

        # C — trung bình các bản sinh ra của giọng ấy
        cs = []
        dai_tb = []
        for p in ds:
            w, sr = sf.read(p, dtype="float32", always_2d=False)
            if getattr(w, "ndim", 1) > 1:
                w = w.mean(axis=1)
            v = (do_on_dinh.do_on_dinh_f0(w, int(sr)) or {}).get(
                "f0_tan_tuong_doi")
            if v is not None:
                cs.append(float(v))
                dai_tb.append(len(w) / float(sr))
        if not cs:
            continue
        tc = statistics.mean(cs)
        dai = statistics.mean(dai_tb)

        # B — cắt clip tham chiếu thành đoạn DÀI BẰNG bản sinh ra
        #
        # ⛔ Cắt NỐI TIẾP, không cắt chồng lấn: hai đoạn chồng nhau chia sẻ dữ
        #    liệu nên độ tản của chúng tương quan, và trung bình sẽ nhìn ổn định
        #    hơn thực tế.
        n = int(dai * srr)
        bs = []
        for i in range(0, len(wr) - n + 1, n):
            v = (do_on_dinh.do_on_dinh_f0(wr[i:i + n], int(srr)) or {}).get(
                "f0_tan_tuong_doi")
            if v is not None:
                bs.append(float(v))
        if not bs:
            continue
        tb = statistics.mean(bs)

        ket.append({"giong": ma, "A_ca_clip": round(ta, 5),
                    "B_doan_ngan": round(tb, 5), "C_sinh_ra": round(tc, 5),
                    "giay_moi_doan": round(dai, 2), "so_doan": len(bs)})
        print(f"{ma[:26]:26} {ta:>10.4f} {tb:>12.4f} {tc:>10.4f} "
              f"{(tb - ta) / max(ta, 1e-9):>+10.1%}")

    if not ket:
        print("KHONG DO DUOC GI", file=sys.stderr)
        return 1

    A = statistics.mean(k["A_ca_clip"] for k in ket)
    B = statistics.mean(k["B_doan_ngan"] for k in ket)
    C = statistics.mean(k["C_sinh_ra"] for k in ket)

    print("\n" + "=" * 76)
    print("  TACH 'GIA CUA DO DAI' KHOI 'KHUYET TAT NHAN BAN'")
    print("=" * 76)
    print(f"  A  do tan F0 cua CA clip tham chieu (~25s ghep) : {A:.4f}")
    print(f"  B  do tan F0 tung DOAN ngan trong chinh clip ay : {B:.4f}")
    print(f"  C  do tan F0 cua ban SINH RA                    : {C:.4f}")
    print()
    cu = (C - A) / max(A, 1e-9)
    moi = (C - B) / max(B, 1e-9)
    gia_dai = (B - A) / max(A, 1e-9)
    print(f"  Con so DA BAO CAO   (C so voi A) : {cu:+.1%}")
    print(f"  Gia cua DO DAI      (B so voi A) : {gia_dai:+.1%}")
    print(f"  Phan CON LAI        (C so voi B) : {moi:+.1%}   <- chi phan nay")
    print(f"                                                     noi ve nhan ban")

    if abs(cu) > 1e-9:
        pc = abs(gia_dai) / abs(cu) * 100
        print(f"\n  => Do dai giai thich {pc:.0f}% con so da bao cao.")
        if pc >= 60:
            print("     🔴 PHAN LON la TAO TAC CUA PHEP DO, khong phai khuyet tat.")
            print("     Phai sua lai DV-006 va cach `lech_tham_chieu` lay moc.")
        elif pc >= 25:
            print("     ⚠️ Mot phan dang ke. Con so that nho hon nhieu so voi")
            print("        con so da bao cao.")
        else:
            print("     ✅ Do dai khong giai thich duoc. Khuyet tat la that.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"A_ca_clip": A, "B_doan_ngan": B, "C_sinh_ra": C,
                   "da_bao_cao": cu, "gia_do_dai": gia_dai, "con_lai": moi,
                   "chi_tiet": ket}, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
