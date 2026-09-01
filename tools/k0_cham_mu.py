r"""
k0_cham_mu.py — BƯỚC 2 của K0: sinh bằng VieNeu rồi chấm CẢ HAI hệ bằng một
bộ chấm TRUNG LẬP.

    powershell -ExecutionPolicy Bypass -File .\setup\k0_sinh_f5.ps1     (buoc 1)
    powershell -ExecutionPolicy Bypass -File .\setup\xuat_ref_kho_chung.ps1
    powershell -ExecutionPolicy Bypass -File .\setup\k0_cham_mu.ps1     (buoc 2)

## 🔴 VẤN ĐỀ PHƯƠNG PHÁP: AI ĐƯỢC LÀM TRỌNG TÀI

Câu hỏi của K0 là *"zero-shot có ngang ngửa fine-tuned không"*, và nó quyết
định K5 (~7.800 dòng đường huấn luyện) có tồn tại hay không. Nên **trọng tài
phải trung lập**, và đó không phải chuyện hình thức:

  ⛔ Dùng bộ mã hoá người nói của **VieNeu** thì ta đang hỏi *"VieNeu có nghĩ
     bản của VieNeu giống người nói không"*. Nó tối ưu đúng thứ ấy.
  ⛔ Dùng bộ của **F5** thì lệch chiều ngược lại.

⭐ Ba trục dưới đây **không hệ nào tối ưu trực tiếp**, và cả ba đều so với cùng
   một mốc — chính clip tham chiếu gốc của người nói ấy trong kho cũ:

     ① **Dễ hiểu** — CER của Whisper. Bên thứ ba hoàn toàn.
     ② **Chất lượng cảm nhận** — DNSMOS P.835 OVRL. Bên thứ ba, CC-BY-4.0.
     ③ **Trung thành âm học** — |lệch| so với clip tham chiếu ở độ sáng phổ và
        cao độ (tầng K4). Không đi qua embedding nào của bên nào.

⭐ Trục ③ chính là tầng vừa dựng ở K4, và đây là lý do nó đáng dựng: một phép đo
   độc lập với embedding là thứ **duy nhất** chấm được hai hệ dùng hai bộ mã hoá
   khác nhau.

## Đọc kết quả

Mỗi cặp (giọng × câu) cho một phiếu **thắng/thua/hoà** trên từng trục. Điều kiện
qua của kế hoạch: **≥ 40 cặp** và **khoảng tin cậy không chứa 0,5**.

⛔ "Không chứa 0,5" phải đúng cho **từng trục**, và ba trục hoàn toàn có thể nói
   ba điều khác nhau — F5 dễ hiểu hơn mà VieNeu trung thành hơn là một kết quả
   hợp lệ, và nó dẫn tới một quyết định khác hẳn với "một bên thắng cả ba".
   Gộp ba trục thành một điểm tổng là vứt đi đúng thông tin ấy.

⚠️ Và một cảnh báo về chính phép so: hai hệ chạy ở **hai tần số lấy mẫu khác
   nhau** (F5 24 kHz, VieNeu 48 kHz). DNSMOS và các phép phổ **có nhạy với điều
   đó**. Nên bản sinh ra được hạ về cùng một tần số trước khi chấm, và tần số
   ấy là của bên THẤP hơn — nâng lên chỉ nội suy, còn hạ xuống là vứt dải cao
   đi thật, nên phải làm cho **cả hai** bên như nhau chứ không chỉ một.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

#: Trục nào "nhỏ hơn là tốt hơn".
NHO_LA_TOT = {"cer", "lech_sang", "lech_f0"}


def _doi_tan_so(w, tu: int, den: int):
    import numpy as np
    if tu == den:
        return w
    try:
        import soxr
        return np.asarray(soxr.resample(w, tu, den), dtype="float32")
    except ImportError:
        n = int(round(len(w) * den / float(tu)))
        return np.interp(np.linspace(0, len(w) - 1, n),
                         np.arange(len(w)), w).astype("float32")


def _cham(wav, sr: int, wav_ref, sr_ref: int, cau: str, duong: str) -> dict:
    """Ba trục, không trục nào đi qua bộ mã hoá của bên nào."""
    from voice_sidecar import dnsmos, do_chat_luong, lech_tham_chieu

    ra = {}
    dh = do_chat_luong.do_de_hieu(duong, cau, "vi") or {}
    ra["cer"] = dh.get("cer")
    d = dnsmos.cham(wav, sr) or {}
    ra["dnsmos_ovrl"] = d.get("ovrl")
    lech = lech_tham_chieu.do_lech(wav, sr, wav_ref, sr_ref)
    # ⛔ Lấy TRỊ TUYỆT ĐỐI: câu hỏi là "lệch bao nhiêu", không phải "lệch phía
    #    nào". Một hệ tối hơn và một hệ sáng hơn cùng một lượng thì trung thành
    #    như nhau, và giữ dấu ở đây sẽ cho một bên thắng chỉ vì nó lệch lên.
    if lech.get("delta_db_dai_cao") is not None:
        ra["lech_sang"] = abs(float(lech["delta_db_dai_cao"]))
    if lech.get("delta_f0_trung_vi_hz_ti_le") is not None:
        ra["lech_f0"] = abs(float(lech["delta_f0_trung_vi_hz_ti_le"]))
    return ra


def _kt_c(thang: int, tong: int) -> tuple:
    """Khoảng tin cậy Wilson 95% cho tỉ lệ thắng.

    ⭐ Wilson chứ không phải Wald (`p ± 1,96·√(p(1-p)/n)`): với n vài chục và p
       lệch khỏi 0,5, Wald cho khoảng lệch tâm và có thể tràn ra ngoài [0, 1] —
       tức một khoảng tin cậy nói những điều bất khả. Cùng phép mà `cham_mu.py`
       của dự án ảnh dùng, cố ý.
    """
    if tong <= 0:
        return 0.0, 0.0, 0.0
    z = 1.959963985
    p = thang / tong
    n = tong
    giua = (p + z * z / (2 * n)) / (1 + z * z / n)
    nua = (z / (1 + z * z / n)) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, max(0.0, giua - nua), min(1.0, giua + nua)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--f5", default="tmp/k0/f5_sinh.json")
    ap.add_argument("--ref-kho", default="tmp/ref_kho_chung.json")
    ap.add_argument("--clip-ref", default="tmp/giong_cu")
    ap.add_argument("--ra-wav", default="tmp/k0/vieneu")
    ap.add_argument("--ra", default="tmp/k0/ket_qua.json")
    a = ap.parse_args(argv)

    for d in (a.f5, a.ref_kho):
        if not os.path.isfile(d):
            print(f"THIEU {d}", file=sys.stderr)
            return 2

    import soundfile as sf

    from apps.ltt_voice import sidecar_client

    f5 = json.load(open(a.f5, encoding="utf-8"))
    kho = json.load(open(a.ref_kho, encoding="utf-8"))

    # Ghép giọng hệ cũ -> hồ sơ hệ mới qua XUẤT XỨ, không qua tên.
    theo_ma = {}
    for g in kho:
        try:
            ma = (json.loads(g.get("ghi_chu") or "{}") or {}).get("ma_cu")
        except ValueError:
            ma = None
        if ma:
            theo_ma[ma] = g

    os.makedirs(a.ra_wav, exist_ok=True)
    cap, thieu = [], set()
    for m in f5["ket"]:
        if not m.get("ok"):
            continue
        g = theo_ma.get(m["giong"])
        if g is None:
            thieu.add(m["giong"])
            continue
        cap.append({**m, "ho_so": g})
    if thieu:
        print(f"⚠️ khong ghep duoc {sorted(thieu)} — bo qua")
    print(f"{len(cap)} cap (giong x cau)\n")

    ket = []
    for i, c in enumerate(cap, 1):
        ten = os.path.basename(c["wav"]).replace(".wav", "")
        # ── bản VieNeu cho cùng giọng, cùng câu ────────────────────────────
        try:
            raw, _ = sidecar_client.noi(c["cau"], ref_b64=c["ho_so"]["ref_b64"])
        except Exception as e:                            # noqa: BLE001
            print(f"  [hong] {ten}: {type(e).__name__}: {e}")
            continue
        d_vn = os.path.join(a.ra_wav, f"{ten}.wav")
        with open(d_vn, "wb") as f:
            f.write(raw)

        w_f5, sr_f5 = sf.read(c["wav"], dtype="float32", always_2d=False)
        w_vn, sr_vn = sf.read(d_vn, dtype="float32", always_2d=False)
        if getattr(w_f5, "ndim", 1) > 1:
            w_f5 = w_f5.mean(axis=1)
        if getattr(w_vn, "ndim", 1) > 1:
            w_vn = w_vn.mean(axis=1)

        # ⛔ HẠ CẢ HAI về cùng tần số THẤP hơn. Chấm một bản 48 kHz cạnh một bản
        #    24 kHz là cho bên 48 kHz một lợi thế ở mọi phép phổ mà không liên
        #    quan gì tới chất lượng nhân bản.
        dich = min(int(sr_f5), int(sr_vn))
        w_f5 = _doi_tan_so(w_f5, int(sr_f5), dich)
        w_vn = _doi_tan_so(w_vn, int(sr_vn), dich)

        ref = os.path.join(a.clip_ref, f"{c['giong']}.wav")
        if not os.path.isfile(ref):
            print(f"  [bo] {ten}: khong co clip tham chieu {ref}")
            continue
        w_r, sr_r = sf.read(ref, dtype="float32", always_2d=False)
        if getattr(w_r, "ndim", 1) > 1:
            w_r = w_r.mean(axis=1)

        # ASR đọc từ TỆP, nên ghi bản đã hạ tần số ra tệp tạm cho công bằng.
        import tempfile
        tam = {}
        for nhan, w in (("f5", w_f5), ("vieneu", w_vn)):
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            t.close()
            sf.write(t.name, w, dich)
            tam[nhan] = t.name
        try:
            m_f5 = _cham(w_f5, dich, w_r, int(sr_r), c["cau"], tam["f5"])
            m_vn = _cham(w_vn, dich, w_r, int(sr_r), c["cau"], tam["vieneu"])
        finally:
            for t in tam.values():
                try:
                    os.unlink(t)
                except OSError:
                    pass

        ket.append({"ten": ten, "giong": c["giong"], "cau": c["cau"],
                    "sr_cham": dich, "f5": m_f5, "vieneu": m_vn})
        print(f"  [{i}/{len(cap)}] {ten:32} "
              f"CER f5={m_f5.get('cer')} vn={m_vn.get('cer')}")

    if not ket:
        print("KHONG CHAM DUOC CAP NAO", file=sys.stderr)
        return 1

    print("\n" + "=" * 76)
    print("  K0 — F5 tinh chinh  vs  VieNeu zero-shot")
    print("=" * 76)
    print(f"  {'truc':16} {'F5 thang':>9} {'VieNeu':>9} {'hoa':>6} "
          f"{'ti le VieNeu':>14} {'KTC 95%':>18}")
    tong_ket = {}
    for truc in ("cer", "dnsmos_ovrl", "lech_sang", "lech_f0"):
        f5t = vnt = hoa = 0
        for k in ket:
            x, y = k["f5"].get(truc), k["vieneu"].get(truc)
            if x is None or y is None:
                continue
            if abs(float(x) - float(y)) < 1e-9:
                hoa += 1
            elif (float(y) < float(x)) == (truc in NHO_LA_TOT):
                vnt += 1
            else:
                f5t += 1
        n = f5t + vnt
        p, lo, hi = _kt_c(vnt, n)
        chua = lo <= 0.5 <= hi
        tong_ket[truc] = {"f5": f5t, "vieneu": vnt, "hoa": hoa, "n": n,
                          "ti_le_vieneu": round(p, 4),
                          "ktc": [round(lo, 4), round(hi, 4)],
                          "ktc_chua_0_5": chua}
        print(f"  {truc:16} {f5t:>9} {vnt:>9} {hoa:>6} {p:>14.3f} "
              f"  [{lo:.3f}; {hi:.3f}]{'  (chua 0,5)' if chua else '  ***'}")

    print("\n  *** = khoang tin cay KHONG chua 0,5 => truc do da phan thang bai.")
    print(f"  So cap: {len(ket)}  (dieu kien ke hoach: >= 40)")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"cap": ket, "tong_ket": tong_ket, "so_cap": len(ket)}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
