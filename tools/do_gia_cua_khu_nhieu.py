r"""
do_gia_cua_khu_nhieu.py — bộ khử nhiễu tham chiếu lấy đi bao nhiêu dải cao.

    powershell -ExecutionPolicy Bypass -File .\setup\do_gia_cua_khu_nhieu.ps1

## Giả thuyết đang kiểm

Baseline K4 đo được bản sinh ra **tối hơn clip tham chiếu 3,65 dB** trên 4 kHz,
và con số ấy là thứ duy nhất giải thích được vì sao F5 thắng VieNeu ở trục
`lech_sang` trong K0 (30–10).

Nhưng đường ghi danh của ta chạy `encode_reference(..., denoise=True)` — mặc
định của upstream. Và docstring của chính bộ khử nhiễu nói vì sao nó bật:

    "x-vector lands in the training distribution (train data is denoised +
     LUFS-20)"

⇒ Khử nhiễu **không phải lỗi**: model được train trên dữ liệu đã khử nhiễu, nên
  đưa clip thô vào là đưa nó **ra ngoài phân bố huấn luyện**.

🔴 NHƯNG NÓ CÓ NGHĨA LÀ PHÉP SO CỦA K4 ĐANG SO NHẦM MỐC. Model nhân bản clip
   **đã khử nhiễu**; K4 lại so bản sinh ra với clip **thô**. Nếu bộ khử nhiễu
   cắt dải cao — mà bộ khử nhiễu nào cũng thế, vì nhiễu tập trung ở dải cao —
   thì một phần của −3,65 dB **không phải khuyết tật của model**, nó là khoảng
   cách giữa hai mốc khác nhau.

## Phép đo

Với mỗi clip tham chiếu: đo `db_dai_cao` **thô** và `db_dai_cao` **sau khử
nhiễu**, rồi lấy hiệu.

⛔ Dùng ĐÚNG bộ khử nhiễu mà đường ghi danh dùng (`OnnxDenoiser` của gói
   `vieneu`, cùng tệp `denoiser.onnx`), không phải một bộ tương đương. Một phép
   đối chứng dùng công cụ khác thì đo một thứ khác.

## Đọc kết quả

  · Nếu hiệu ≈ **−3,65 dB** ⇒ toàn bộ độ tối đo được là **do so nhầm mốc**.
    Sửa K4 để so với clip đã khử nhiễu, và khoảng cách với F5 ở trục ấy biến mất.
  · Nếu hiệu ≈ **0** ⇒ độ tối là thật, do codec. Chấp nhận như DV-002 đã ghi,
    và hướng vá là hậu kỳ chứ không phải đổi mốc.
  · Ở giữa ⇒ cả hai, và tỉ lệ nói phần nào đáng vá trước.
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


def _tim_denoiser() -> str | None:
    for goc in (r"C:\LTTPlatform\hf-cache", r"D:\LTTPlatform-runtime\hf-cache",
                os.environ.get("HF_HOME") or ""):
        if not goc:
            continue
        cac = glob.glob(os.path.join(goc, "**", "denoiser.onnx"), recursive=True)
        if cac:
            return cac[0]
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default="tmp/giong_cu")
    ap.add_argument("--ra", default="tmp/gia_cua_khu_nhieu.json")
    a = ap.parse_args(argv)

    import numpy as np
    import soundfile as sf

    from voice_sidecar import do_on_dinh

    d = _tim_denoiser()
    if not d:
        print("KHONG THAY denoiser.onnx", file=sys.stderr)
        return 2
    print(f"denoiser: {d}\n")

    from vieneu._v3_turbo_engine.onnx_denoiser import OnnxDenoiser
    den = OnnxDenoiser(d)

    cac = sorted(glob.glob(os.path.join(a.clip, "*.wav")))
    if not cac:
        print(f"KHONG CO WAV trong {a.clip}", file=sys.stderr)
        return 2

    hieu_db, hieu_vat, ket = [], [], []
    print(f"{'clip':26} {'db_dai_cao tho':>15} {'sau khu nhieu':>14} {'hieu':>8}")
    for p in cac:
        w, sr = sf.read(p, dtype="float32", always_2d=False)
        if getattr(w, "ndim", 1) > 1:
            w = w.mean(axis=1)
        try:
            sach = np.asarray(den.denoise(w, int(sr)), dtype="float32")
        except Exception as e:                            # noqa: BLE001
            print(f"  [hong] {os.path.basename(p)}: {type(e).__name__}: {e}")
            continue
        # ⛔ Bộ khử nhiễu trả 44.1 kHz. Đo `db_dai_cao` ở hai tần số khác nhau
        #    là so hai thứ khác nhau — mốc 4 kHz thì như nhau, nhưng phần "tổng
        #    năng lượng" ở mẫu số trải trên hai dải Nyquist khác nhau.
        #    Hạ bản sạch về đúng tần số của bản thô.
        try:
            import soxr
            sach = np.asarray(soxr.resample(sach, 44100, int(sr)),
                              dtype="float32")
        except ImportError:
            n = int(round(len(sach) * int(sr) / 44100.0))
            sach = np.interp(np.linspace(0, len(sach) - 1, n),
                             np.arange(len(sach)), sach).astype("float32")

        a1 = do_on_dinh.do_sang(w, int(sr))
        a2 = do_on_dinh.do_sang(sach, int(sr))
        if not a1 or not a2:
            continue
        hd = a2["db_dai_cao"] - a1["db_dai_cao"]
        hv = (a2["vat_95_hz"] - a1["vat_95_hz"]) / max(a1["vat_95_hz"], 1e-6)
        hieu_db.append(hd)
        hieu_vat.append(hv)
        ket.append({"clip": os.path.basename(p),
                    "db_tho": a1["db_dai_cao"], "db_sach": a2["db_dai_cao"],
                    "hieu_db": round(hd, 4), "hieu_vat95_ti_le": round(hv, 4)})
        print(f"{os.path.basename(p)[:26]:26} {a1['db_dai_cao']:>15.3f} "
              f"{a2['db_dai_cao']:>14.3f} {hd:>+8.3f}")

    if not hieu_db:
        print("KHONG DO DUOC GI", file=sys.stderr)
        return 1

    tb = statistics.mean(hieu_db)
    print("\n" + "=" * 72)
    print("  GIA CUA BUOC KHU NHIEU THAM CHIEU")
    print("=" * 72)
    print(f"  hieu db_dai_cao   : {tb:+.3f} dB  "
          f"(lech {statistics.pstdev(hieu_db):.3f}, n={len(hieu_db)})")
    print(f"  hieu vat_95_hz    : {statistics.mean(hieu_vat):+.3f} (ti le)")
    print(f"\n  Do toi da do o baseline K4: -3,649 dB")
    if tb <= -1.0:
        pc = min(100.0, abs(tb) / 3.649 * 100)
        print(f"  => Buoc khu nhieu giai thich {pc:.0f}% do toi ay.")
        if pc >= 60:
            print("     🔴 PHAN LON do toi la do SO NHAM MOC, khong phai codec.")
            print("     Sua: K4 phai so voi clip DA KHU NHIEU.")
    else:
        print("  => Buoc khu nhieu KHONG giai thich duoc do toi.")
        print("     Do toi la that, do codec. DV-002 dung, va huong va la hau ky.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"hieu_db_trung_binh": round(tb, 5), "chi_tiet": ket}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
