r"""
do_eq_sua_sang.py — EQ sửa độ sáng có THẬT SỰ cải thiện không, hay chỉ làm một
con số đẹp lên.

    powershell -ExecutionPolicy Bypass -File .\setup\do_eq_sua_sang.ps1

## ⛔ CÂU HỎI PHẢI HỎI, VÀ NÓ KHÔNG PHẢI "db_dai_cao CÓ LÊN KHÔNG"

Tất nhiên nó lên — đó là định nghĩa của việc nâng dải cao. Câu hỏi thật:

  ① **DNSMOS có lên không?** Đây là trọng tài bên thứ ba, và là **đúng trục F5
     đang thắng ta ở K0** (31–9). Nếu EQ không nâng được nó thì EQ không thu
     hẹp khoảng cách, dù `db_dai_cao` có đẹp tới đâu.
  ② **CER có xấu đi không?** EQ nâng cả nhiễu codec trong dải nó nâng. Một bản
     sáng hơn mà khó nghe hơn là một bước lùi.
  ③ **Đỉnh thật có vượt trần không?** Nâng thì đỉnh lên theo.

⭐ Một chỉ số đi đúng hướng trong khi hai chỉ số khác đi sai là kết quả **tệ
   nhất** có thể, vì nó dễ báo cáo thành thành công. Nên cả ba đi cùng nhau
   trong một bảng.

## Vì sao quét nhiều mức thay vì lấy thẳng 3,65 dB

Trực giác nói: hụt 3,65 dB thì nâng lại 3,65 dB. Nhưng:

  · Hụt đo trên **năng lượng trung bình** của cả dải >4 kHz; một kệ cao ở
    4 kHz nâng không đều trên dải ấy.
  · Bù đủ có thể **quá tay về mặt cảm nhận**: khuyết tật của codec không phải
    một bộ lọc tuyến tính, nên bù tuyến tính không khôi phục được thứ đã mất —
    nó chỉ nâng những gì còn lại, **kể cả nhiễu**.

⇒ Nên quét, và để DNSMOS chọn. Nếu đỉnh của DNSMOS rơi đúng ở ~3,65 thì đó là
  một xác nhận; nếu nó rơi ở 1,5 thì trực giác sai và ta biết vì sao.

## ⛔ KHÔNG CHẠM GPU

Chạy trên 40 tệp K0 đã sinh. Nghĩa là nó lặp lại được, và nó không tranh card
với việc khác.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

#: Mức kệ cao đem quét, dB. 0 là ĐỐI CHỨNG — bản không đụng gì.
MUC = (0.0, 1.0, 2.0, 3.0, 3.65, 4.0)

#: Tần số gối của kệ cao. 4 kHz vì đó là mốc `do_on_dinh.CAT_SANG_HZ` đang đo,
#: nên phép đo và phép sửa nói về cùng một dải.
GOI_HZ = 4000.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", default="tmp/k0/vieneu")
    ap.add_argument("--k0", default="tmp/k0/f5_sinh.json")
    ap.add_argument("--clip-ref", default="tmp/giong_cu")
    ap.add_argument("--so-mau", type=int, default=12)
    ap.add_argument("--ra", default="tmp/eq_sua_sang.json")
    a = ap.parse_args(argv)

    import soundfile as sf

    from voice_sidecar import (dnsmos, do_chat_luong, do_on_dinh, eq_sua_sang,
                               lech_tham_chieu)

    cac = sorted(glob.glob(os.path.join(a.wav, "*.wav")))
    if not cac:
        print(f"KHONG CO WAV trong {a.wav}", file=sys.stderr)
        return 2
    buoc = max(1, len(cac) // a.so_mau)
    cac = cac[::buoc][:a.so_mau]

    cau = {}
    if os.path.isfile(a.k0):
        for m in json.load(open(a.k0, encoding="utf-8"))["ket"]:
            if m.get("ok"):
                cau[os.path.basename(m["wav"]).replace(".wav", "")] = m["cau"]

    print(f"{len(cac)} ban x {len(MUC)} muc  (KHONG cham GPU)\n")

    gom = {m: {"ovrl": [], "cer": [], "lech": [], "tp": []} for m in MUC}
    for i, p in enumerate(cac, 1):
        ten = os.path.basename(p).replace(".wav", "")
        goc_ma = ten.split("__")[0]
        ref = os.path.join(a.clip_ref, f"{goc_ma}.wav")
        if not os.path.isfile(ref):
            continue
        w, sr = sf.read(p, dtype="float32", always_2d=False)
        wr, srr = sf.read(ref, dtype="float32", always_2d=False)
        if getattr(w, "ndim", 1) > 1:
            w = w.mean(axis=1)
        if getattr(wr, "ndim", 1) > 1:
            wr = wr.mean(axis=1)
        c = cau.get(ten, "")

        for m in MUC:
            x = (w if m == 0.0 else
                 eq_sua_sang.ap(w, int(sr), ke_cao_db=m, ke_cao_hz=GOI_HZ))
            d = dnsmos.cham(x, int(sr)) or {}
            if d.get("ovrl") is not None:
                gom[m]["ovrl"].append(float(d["ovrl"]))
            th = do_chat_luong.do_tin_hieu(x, int(sr)) or {}
            if th.get("true_peak_dbtp") is not None:
                gom[m]["tp"].append(float(th["true_peak_dbtp"]))
            lc = lech_tham_chieu.do_lech(x, int(sr), wr, int(srr))
            if lc.get("delta_db_dai_cao") is not None:
                gom[m]["lech"].append(abs(float(lc["delta_db_dai_cao"])))
            if c:
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                t.close()
                sf.write(t.name, x, int(sr))
                try:
                    dh = do_chat_luong.do_de_hieu(t.name, c, "vi") or {}
                    if dh.get("cer") is not None:
                        gom[m]["cer"].append(float(dh["cer"]))
                finally:
                    try:
                        os.unlink(t.name)
                    except OSError:
                        pass
        print(f"  [{i}/{len(cac)}] {ten}")

    def _tb(v):
        return (statistics.mean(v), statistics.pstdev(v) if len(v) > 1 else 0.0,
                len(v)) if v else (None, None, 0)

    print("\n" + "=" * 76)
    print("  QUET MUC KE CAO @ 4 kHz  —  DOC CA BA COT CUNG LUC")
    print("=" * 76)
    print(f"  {'ke cao':>8} {'DNSMOS':>18} {'CER':>16} "
          f"{'|lech sang|':>12} {'true peak':>11}")
    ra = {}
    for m in MUC:
        o, os_, on = _tb(gom[m]["ovrl"])
        c, cs, cn = _tb(gom[m]["cer"])
        l, _, _ = _tb(gom[m]["lech"])
        t, _, _ = _tb(gom[m]["tp"])
        ra[str(m)] = {"dnsmos_ovrl": o, "cer": c, "lech_sang": l,
                      "true_peak": t, "n": on}
        print(f"  {m:>7.2f}dB {(o or 0):>10.4f} ±{(os_ or 0):.3f} "
              f"{(c if c is not None else -1):>10.4f} ±{(cs or 0):.3f} "
              f"{(l or 0):>12.3f} {(t or 0):>11.2f}")

    nen = ra["0.0"]
    tot = max((k for k in ra if ra[k]["dnsmos_ovrl"] is not None),
              key=lambda k: ra[k]["dnsmos_ovrl"])
    print(f"\n  Doi chung (0 dB) : DNSMOS {nen['dnsmos_ovrl']:.4f}  "
          f"CER {nen['cer']:.4f}  |lech| {nen['lech_sang']:.3f}")
    print(f"  Muc tot nhat     : {tot} dB -> DNSMOS "
          f"{ra[tot]['dnsmos_ovrl']:.4f}  CER {ra[tot]['cer']:.4f}  "
          f"|lech| {ra[tot]['lech_sang']:.3f}")

    d_ovrl = ra[tot]["dnsmos_ovrl"] - nen["dnsmos_ovrl"]
    d_cer = ra[tot]["cer"] - nen["cer"]
    print(f"\n  DNSMOS doi : {d_ovrl:+.4f}   (F5 hon ta 0,143 o K0)")
    print(f"  CER doi    : {d_cer:+.4f}   (am = tot hon)")
    if float(tot) == 0.0:
        print("\n  🔴 MUC TOT NHAT LA 0 dB — EQ KHONG cai thien gi.")
        print("     Do toi la that nhung bu tuyen tinh khong khoi phuc duoc no:")
        print("     codec vut di thong tin, EQ chi nang phan con lai + nhieu.")
    elif d_cer > 0.005:
        print("\n  ⚠️ DNSMOS len nhung CER XAU DI. Mot ban sang hon ma kho nghe")
        print("     hon la mot buoc lui — KHONG bat EQ theo bang nay.")
    else:
        pc = d_ovrl / 0.143 * 100
        print(f"\n  ✅ EQ dong duoc {pc:.0f}% khoang cach DNSMOS voi F5, "
              f"khong lam xau CER.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"goi_hz": GOI_HZ, "muc": ra, "tot_nhat": tot}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
