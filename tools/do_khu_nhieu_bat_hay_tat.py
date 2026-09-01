r"""
do_khu_nhieu_bat_hay_tat.py — ghi danh với `denoise=True` hay `denoise=False`
cho giọng nhân bản tốt hơn.

    powershell -ExecutionPolicy Bypass -File .\setup\do_khu_nhieu_bat_hay_tat.ps1

## Câu hỏi, và vì sao nó đáng đo chứ không đáng tranh luận

Đường ghi danh của ta chạy `encode_reference(..., denoise=True)` — mặc định của
upstream. Chủ sản phẩm hỏi một câu thẳng: **khử nhiễu bản thân nó là một phép
méo tiếng; nếu nó không mua được gì thì tắt đi có hơn không?**

Tài liệu của chính bộ khử nhiễu trả lời:

    "x-vector lands in the training distribution (train data is denoised +
     LUFS-20)"

⛔ Nhưng đó là **đọc tài liệu**, và đọc tài liệu/mã rồi kết luận đã sai **ba
   lần** trong dự án này chỉ trong một phiên:

     · `voice_profiles.yaml` ghi `lang: en` trên tên tiếng Việt ⇒ tôi viết
       "nhãn không đáng tin". Sai — cột `engine` mang câu trả lời, ASR khớp 25/25.
     · `sea_g2p.SUPPORTED_LANGS = ("vi","th","id")` ⇒ tôi viết "engine không nói
       được tiếng Anh". Sai — nó đọc tiếng Anh đúng từng chữ, `[en 0,996]`.
     · Sàn nhiễu n=4 ⇒ tôi đuổi theo những con số có sai số 41%.

⇒ Một khẳng định về thứ hệ thống **làm được hay không** phải đến từ việc bắt nó
  làm thử. Tệp này bắt nó làm thử.

## Cách đo

Cùng giọng, cùng câu, hai đường ghi danh:

    A: encode_reference(..., denoise=True)    <- dang chay
    B: encode_reference(..., denoise=False)   <- de nghi cua chu san pham

Rồi chấm bằng **đúng bộ chấm trung lập của K0** — không trục nào đi qua bộ mã
hoá người nói của VieNeu, vì bộ ấy tối ưu chính thứ ta đang hỏi:

  ① CER (Whisper)                — de hieu
  ② DNSMOS P.835 OVRL            — chat luong cam nhan
  ③ |lech| vs clip THAM CHIEU GOC — trung thanh am hoc (tang K4)

⛔ Mốc so ở trục ③ là clip **THÔ**, giống nhau cho cả hai nhánh. Nếu lấy mốc là
   clip đã khử nhiễu thì nhánh A được so với chính đầu vào của nó còn nhánh B
   thì không — một phép so tự thiên vị.

## Ba kết quả có thể, và chúng dẫn tới ba việc khác nhau

  · **B tốt hơn** ⇒ tắt khử nhiễu. Tài liệu upstream nói quá lời, và ta có số.
  · **A tốt hơn** ⇒ giữ nguyên, và câu hỏi đã có câu trả lời bằng số thay vì
    bằng một dòng docstring.
  · **Hoà** ⇒ chọn theo tiêu chí khác. Khi ấy nghiêng về **tắt**, vì ít xử lý
    hơn là ít thứ hỏng hơn — nhưng nói rõ đó là lựa chọn theo nguyên tắc, không
    phải theo số đo.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

CAU = [
    "Ba tôi bảo bà ấy bán bánh ở bãi biển vào buổi sáng.",
    "Cô ấy cố gắng có được một cỗ máy mới cho công việc.",
    "Tôi thấy thầy giáo đứng ở cửa lớp từ sáng sớm.",
]


def _cham(wav, sr, wav_ref, sr_ref, cau, duong):
    from voice_sidecar import dnsmos, do_chat_luong, lech_tham_chieu
    ra = {}
    dh = do_chat_luong.do_de_hieu(duong, cau, "vi") or {}
    ra["cer"] = dh.get("cer")
    d = dnsmos.cham(wav, sr) or {}
    ra["dnsmos_ovrl"] = d.get("ovrl")
    lc = lech_tham_chieu.do_lech(wav, sr, wav_ref, sr_ref)
    for k, t in (("lech_sang", "delta_db_dai_cao"),
                 ("lech_f0", "delta_f0_trung_vi_hz_ti_le")):
        if lc.get(t) is not None:
            ra[k] = abs(float(lc[t]))
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default="tmp/giong_cu")
    ap.add_argument("--so-giong", type=int, default=6)
    ap.add_argument("--ra", default="tmp/khu_nhieu_bat_tat.json")
    a = ap.parse_args(argv)

    import soundfile as sf

    from apps.ltt_voice import sidecar_client
    from voice_sidecar import engine as eng

    cac = sorted(glob.glob(os.path.join(a.clip, "*.wav")))
    buoc = max(1, len(cac) // a.so_giong)
    cac = cac[::buoc][:a.so_giong]
    if not cac:
        print(f"KHONG CO WAV trong {a.clip}", file=sys.stderr)
        return 2

    # ⛔ `ghi_danh` là phương thức của `CongGiong`, lấy qua `lay_cong()` — KHÔNG
    #    dựng một thể hiện mới. `lay_cong()` giữ MỘT cổng dùng chung, và cổng ấy
    #    nắm model đã nạp; dựng thêm một cái là nạp model lần thứ hai vào cùng
    #    một card, tức 641 MB VRAM nữa cho không việc gì.
    e = eng.lay_cong()

    print(f"{len(cac)} giong x {len(CAU)} cau x 2 nhanh\n")
    gom = {"bat": {}, "tat": {}}
    for i, p in enumerate(cac, 1):
        ten = os.path.basename(p).replace(".wav", "")
        wr, srr = sf.read(p, dtype="float32", always_2d=False)
        if getattr(wr, "ndim", 1) > 1:
            wr = wr.mean(axis=1)
        for nhan, dn in (("bat", True), ("tat", False)):
            try:
                hs = e.ghi_danh(p, denoise=dn)
            except Exception as ex:                       # noqa: BLE001
                print(f"  [ghi danh hong] {ten}/{nhan}: "
                      f"{type(ex).__name__}: {ex}")
                continue
            ref_b64 = hs.get("ref_b64") or hs.get("bieu_dien") or ""
            if not ref_b64:
                print(f"  [bo] {ten}/{nhan}: ghi_danh khong tra ref_b64 "
                      f"(khoa co: {sorted(hs)[:6]})")
                continue
            for c in CAU:
                try:
                    raw, _ = sidecar_client.noi(c, ref_b64=ref_b64)
                except Exception as ex:                   # noqa: BLE001
                    print(f"  [sinh hong] {ten}/{nhan}: "
                          f"{type(ex).__name__}: {ex}")
                    continue
                w, sr = sf.read(io.BytesIO(raw), dtype="float32",
                                always_2d=False)
                if getattr(w, "ndim", 1) > 1:
                    w = w.mean(axis=1)
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                t.close()
                sf.write(t.name, w, int(sr))
                try:
                    m = _cham(w, int(sr), wr, int(srr), c, t.name)
                finally:
                    try:
                        os.unlink(t.name)
                    except OSError:
                        pass
                for k, v in m.items():
                    if v is not None:
                        gom[nhan].setdefault(k, []).append(float(v))
            print(f"  [{i}/{len(cac)}] {ten:26} denoise={nhan}")

    print("\n" + "=" * 74)
    print("  KHU NHIEU THAM CHIEU: BAT  vs  TAT")
    print("=" * 74)
    print(f"  {'truc':16} {'BAT (dang chay)':>22} {'TAT (de nghi)':>22} {'?':>10}")
    ra = {}
    import math
    for truc in ("cer", "dnsmos_ovrl", "lech_sang", "lech_f0"):
        A, B = gom["bat"].get(truc) or [], gom["tat"].get(truc) or []
        if not A or not B:
            continue
        ma, mb = statistics.mean(A), statistics.mean(B)
        sa = statistics.pstdev(A) / math.sqrt(len(A)) if len(A) > 1 else 0.0
        sb = statistics.pstdev(B) / math.sqrt(len(B)) if len(B) > 1 else 0.0
        sd = math.hypot(sa, sb)
        d = mb - ma
        nho_tot = truc in ("cer", "lech_sang", "lech_f0")
        if sd <= 0 or abs(d) < 1.96 * sd:
            kl = "hoa"
        else:
            kl = "TAT hon" if (d < 0) == nho_tot else "BAT hon"
        ra[truc] = {"bat": round(ma, 5), "tat": round(mb, 5),
                    "chenh": round(d, 5), "sai_so": round(sd, 5),
                    "ket_luan": kl, "n": min(len(A), len(B))}
        print(f"  {truc:16} {ma:>15.4f} ±{sa:.4f} {mb:>15.4f} ±{sb:.4f} "
              f"{kl:>10}")

    print("\n  'hoa' = khoang tin cay 95% cua CHENH LECH co chua 0.")
    print("  Neu hoa o moi truc: chon theo nguyen tac, va nguyen tac la IT XU LY")
    print("  HON — nhung phai noi ro do la lua chon, khong phai so do.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ra, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
