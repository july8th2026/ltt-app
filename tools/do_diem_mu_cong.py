r"""
do_diem_mu_cong.py — cổng chất lượng hiện tại MÙ với những hỏng hóc nào?

    powershell -ExecutionPolicy Bypass -File .\setup\do_diem_mu_cong.ps1

## Vì sao đo cái này TRƯỚC khi thêm bất kỳ chỉ số nào (K3)

Pha K3 vốn đặt ra là "mang HNR · jitter · shimmer từ hệ cũ sang". Tra cộng đồng
xong thì cả tiền đề ấy lung lay:

  · Jitter/shimmer là chỉ số **lâm sàng**, đo trên nguyên âm kéo dài để đánh giá
    bệnh lý thanh quản. Cộng đồng đo TTS bằng **bộ dự đoán MOS** — UTMOS, NISQA,
    DNSMOS — chứ không dùng chúng.
  · Bản của hệ cũ lại **không phải** định nghĩa lâm sàng: nó lấy chu kỳ trên các
    khung cách nhau 10 ms chứ không phải hai chu kỳ thanh môn liền kề. Gọi nó là
    "jitter" rồi so với ngưỡng lâm sàng (< 1%) là so hai thứ khác nhau.
  · `NISQA-TTS` — đúng công cụ cho việc này — có trọng số **CC BY-NC-SA**, tức
    **không dùng được** trong một sản phẩm thương mại.
  · `UTMOS` (MIT) dùng được, nhưng trọng số **411 MB** và được huấn luyện trên
    tiếng Anh, nên giá trị tuyệt đối trên tiếng Việt là một ẩn số.

⇒ Không chỉ số nào trong số đó hiển nhiên đáng thêm. Câu hỏi đúng không phải
  *"thêm gì"* mà **"cổng đang bỏ sót gì"** — và đó là câu đo được.

## Cách đo

Lấy tiếng THẬT do chính engine sinh, rồi **tiêm từng hỏng hóc đã biết**, mỗi lần
một loại. Với mỗi loại, chạy toàn bộ bộ đo hiện có và xem chỉ số nào **nhúc
nhích**.

    hỏng hóc nào làm ít nhất một chỉ số đổi rõ  ->  cổng THẤY
    hỏng hóc nào không làm chỉ số nào đổi       ->  cổng MÙ  <- chỗ đáng thêm

⭐ Đây là phép đo nói cho ta biết **nên mua gì**, thay vì mua rồi mới hỏi nó
   dùng làm gì. Ba pha trước đều dạy cùng một điều: thứ mượn được không phải
   thứ đáng mượn.

⛔ "Đổi rõ" phải so với **nhiễu giữa hai lượt sinh bình thường**, không so với 0.
   Mọi chỉ số ở đây đều dao động giữa hai lượt; một thay đổi nhỏ hơn dao động ấy
   không phải một phát hiện.

⚠️ Chạm GPU thật, không chạm sổ tiền.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

CAU = ("Hôm nay trời nắng đẹp nên tôi đi bộ ra công viên gần nhà, ngồi ở cái "
       "ghế quen thuộc dưới gốc cây và đọc nốt mấy trang sách còn dở.")


class KhongDoDuoc(RuntimeError):
    """Không đo được thì VỠ, không lặng lẽ thành một con số."""


# ── các kiểu hỏng, mỗi kiểu một hàm thuần ───────────────────────────────────
def _nhieu(w, sr, snr_db=15.0):
    """Cộng nhiễu trắng ở SNR cho trước."""
    import numpy as np
    cs = float(np.mean(w.astype(np.float64) ** 2))
    cn = cs / (10 ** (snr_db / 10.0))
    rng = np.random.default_rng(11)
    return (w + rng.normal(0, cn ** 0.5, len(w))).astype("float32")


def _vo_tieng(w, sr, tran=0.35):
    """Kẹp cứng — méo hài, thứ tai nghe ra ngay."""
    import numpy as np
    return np.clip(w, -tran, tran).astype("float32")


def _muffled(w, sr, cat_hz=3500.0):
    """Lọc thông thấp — mất độ sáng, giọng 'đục'."""
    import numpy as np
    from scipy.signal import butter, sosfilt
    sos = butter(6, cat_hz / (sr / 2), btype="low", output="sos")
    return np.asarray(sosfilt(sos, w), dtype="float32")


def _lap_giua(w, sr, giay=0.5):
    """Chèn một đoạn lặp vào GIỮA — lỗi mà chốt lặp đuôi không thấy."""
    import numpy as np
    n = int(sr * giay)
    i = len(w) // 2
    return np.concatenate([w[:i], w[i - n:i], w[i:]]).astype("float32")


def _dut_quang(w, sr, giay=1.5):
    """Chèn im lặng vào giữa — đứt quãng."""
    import numpy as np
    i = len(w) // 2
    return np.concatenate([w[:i], np.zeros(int(sr * giay), "float32"),
                           w[i:]]).astype("float32")


def _run_giong(w, sr, sau=0.06, nhip=5.5):
    """Rung biên độ đều đặn — 'giọng run'.

    🔴 ĐÂY LÀ HỎNG HÓC MÀ JITTER/SHIMMER SINH RA ĐỂ BẮT. Nếu bộ đo hiện tại
       thấy nó, thì K3 không cần chúng; nếu mù, đó là lập luận cụ thể để thêm.
    """
    import numpy as np
    t = np.arange(len(w)) / sr
    return (w * (1.0 + sau * np.sin(2 * np.pi * nhip * t))).astype("float32")


def _lech_tong_nua_sau(w, sr, ti_le=1.06):
    """Nửa sau đổi cao độ — 'trôi giọng' trong một lượt."""
    import numpy as np
    i = len(w) // 2
    a, b = w[:i], w[i:]
    n = int(len(b) / ti_le)
    cu = np.linspace(0, len(b) - 1, n)
    b2 = np.interp(cu, np.arange(len(b)), b)
    return np.concatenate([a, b2]).astype("float32")


HONG = [
    ("nhieu_15dB", _nhieu),
    ("vo_tieng", _vo_tieng),
    ("duc_3k5", _muffled),
    ("lap_o_giua", _lap_giua),
    ("dut_quang_1s5", _dut_quang),
    ("run_giong_6pc", _run_giong),
    ("lech_tong_nua_sau", _lech_tong_nua_sau),
]


def _do_het(w, sr, text: str) -> dict:
    """Mọi chỉ số bộ đo hiện có trả về, làm phẳng thành một dict số."""
    import soundfile as sf

    from voice_sidecar import chot_sinh, dnsmos, do_chat_luong, do_on_dinh

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    try:
        sf.write(tmp.name, w, sr)
        kq = do_chat_luong.do_tat_ca(tmp.name, text=text)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    d = dnsmos.cham(w, sr) or {}
    th = kq.get("tin_hieu") or {}
    kl = kq.get("khoang_lang") or {}
    dh = kq.get("de_hieu") or {}
    tg = kq.get("troi_giong") or {}
    pq = chot_sinh.kiem_het(w, sr, len(text))

    ra = {
        "dnsmos_ovrl": d.get("ovrl"), "dnsmos_sig": d.get("sig"),
        "dnsmos_bak": d.get("bak"),
        "true_peak_dbtp": th.get("true_peak_dbtp"), "lufs": th.get("lufs"),
        "ty_le_cham_tran": th.get("ty_le_cham_tran"),
        "im_giua_dai_nhat_s": kl.get("im_giua_dai_nhat_s"),
        "cer": dh.get("cer") if dh.get("co") else None,
        "wer": dh.get("wer") if dh.get("co") else None,
        "on_dinh_giong": tg.get("cosine_trung_binh"),
        "lap_duoi": chot_sinh.so_do(pq, "lap_duoi", "tuong_quan"),
        "chot_bat": 0.0 if pq.dat else 1.0,
    }
    # K3: bon phep nham dung bon diem mu da do duoc.
    ra.update(do_on_dinh.do_tat_ca(w, sr))
    return {k: (None if v is None else float(v)) for k, v in ra.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nen", type=int, default=24,
                    help="So luot sinh binh thuong de do SAN NHIEU (>=12).")
    ap.add_argument("--ra", default="tmp/diem_mu_cong.json")
    a = ap.parse_args(argv)

    for m in ("numpy", "soundfile", "scipy"):
        try:
            __import__(m)
        except ImportError:
            print(f"THIEU {m} — chay bang python cua `vieneu-venv`.",
                  file=sys.stderr)
            return 2

    import soundfile as sf

    from apps.ltt_voice import sidecar_client

    if not sidecar_client.san_sang():
        print("Cong giong CHUA san sang.", file=sys.stderr)
        return 2

    sidecar_client.noi("Lam am.")

    # ── 1. sàn nhiễu: N lượt sinh BÌNH THƯỜNG ───────────────────────────────
    print(f"Do san nhieu — {a.nen} luot sinh binh thuong:")
    nen = []
    for i in range(a.nen):
        raw, _ = sidecar_client.noi(CAU)
        w, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
        nen.append(_do_het(w, int(sr), CAU))
        print(f"  luot {i + 1}/{a.nen}")
    goc_w, goc_sr = w, int(sr)          # lượt cuối làm bản gốc để tiêm lỗi

    san = {}
    for k in nen[0]:
        gia = [m[k] for m in nen if m.get(k) is not None]
        if len(gia) > 1:
            san[k] = {"tb": statistics.mean(gia),
                      "lech": statistics.pstdev(gia),
                      "n": len(gia)}

    # 🔴 SAI SỐ CỦA CHÍNH CÁI THƯỚC. Bài học đắt nhất của K3, và nó không nằm
    #    ở chỉ số nào cả — nó nằm ở phép đo.
    #
    #    Độ lệch chuẩn ước từ n mẫu có sai số tương đối ≈ 1/√(2(n−1)). Với
    #    **n = 4** — mặc định của ba lượt đo đầu — con số ấy là **41%**. Nên mọi
    #    σ in ra mang sẵn ±40%, và ranh giới "thấy / mù" ở 4σ nằm gọn bên trong
    #    sai số ấy.
    #
    #    Hậu quả đo được — cùng hỏng hóc, cùng bản gốc, KHÔNG đổi một dòng mã
    #    nào giữa hai lượt:
    #
    #        duc_3k5      12,1σ  ->  7,9σ
    #        lap_o_giua    4,1σ  ->  3,2σ    tức "đã đóng" -> "còn mù"
    #        lech_tong     4,2σ  ->  3,1σ
    #
    #    Tôi đã sửa chỉ số suốt hai lượt để đuổi theo những con số ấy. Sửa đúng
    #    hướng hay không thì không biết được, vì cái thước co giãn nhiều hơn thứ
    #    nó đo.
    #
    # ⇒ n = 24 đưa sai số về ~15%. Đắt hơn — mỗi lượt là một lần sinh + DNSMOS +
    #   ASR — nhưng một kết luận rẻ và sai thì không có giá nào cả.
    ss = 1.0 / math.sqrt(2.0 * max(1, a.nen - 1))
    print(f"\n{len(san)} chi so do duoc san nhieu"
          f"  (n={a.nen}, sai so cua chinh sigma ~{ss * 100:.0f}%)\n")
    if a.nen < 12:
        print("!! n < 12: sai so cua sigma qua lon de phan biet 'thay' voi 'mu'.")
        print("!! Moi ket luan duoi day chi la GOI Y, khong phai bang chung.\n")

    # ── 2. tiêm từng hỏng hóc ───────────────────────────────────────────────
    ket, mu = {}, []
    for ten, ham in HONG:
        hong = ham(goc_w, goc_sr)
        m = _do_het(hong, goc_sr, CAU)
        # ⛔ GHI SIGMA CỦA **MỌI** CHỈ SỐ, KHÔNG CHỈ NHỮNG CHỈ SỐ QUA NGƯỠNG.
        #
        #    Bản đầu chỉ giữ chỉ số vượt 4σ, nên nó in "0 chi so nhuc nhich"
        #    **giống hệt nhau** cho hai trạng thái rất khác: mọi chỉ số phẳng
        #    lì, và mọi chỉ số ở 3,9σ.
        #
        #    Hai trạng thái ấy đòi hai hành động khác hẳn: cái đầu cần một chỉ
        #    số MỚI, cái sau chỉ cần một phép đo **bớt nhiễu hơn** (vd bộ ASR
        #    lớn hơn). Một bộ đo không phân biệt được chúng thì lời khuyên nó
        #    đưa ra là một phép đoán.
        tat_ca, hang_so = {}, []
        for k, v in m.items():
            if v is None or k not in san:
                continue
            # 🔴 SÀN NHIỄU BẰNG 0 THÌ KHÔNG CÓ SIGMA, KHÔNG PHẢI SIGMA VÔ HẠN.
            #
            #    `max(lech, 1e-6)` của bản trước biến mọi chỉ số phương sai 0
            #    thành một phát hiện giả to đùng: `f0_so_cua_so` (một CÁI ĐẾM)
            #    hiện ra ở 1.000.000σ chỉ vì clip dài thêm 0,5 giây, và bộ dò
            #    tuyên bố `lap_o_giua` "đã thấy" trong khi nó vẫn mù hoàn toàn.
            #    Một bộ đo điểm mù mà tự tạo ra điểm mù là thứ tệ hơn không có.
            #
            #    Phương sai 0 giữa các lượt bình thường nghĩa là chỉ số ấy
            #    KHÔNG phải một phép đo — nó là một hằng số hoặc một cái đếm.
            #    Loại nó ra và NÓI RA, đừng cho nó bỏ phiếu.
            if san[k]["lech"] <= 1e-9:
                hang_so.append(k)
                continue
            sigma = abs(v - san[k]["tb"]) / san[k]["lech"]
            tat_ca[k] = {"nen": round(san[k]["tb"], 4), "hong": round(v, 4),
                         "sigma": round(sigma, 1)}
        thay = {k: x for k, x in tat_ca.items() if x["sigma"] >= 4.0}
        ket[ten] = {"qua_nguong": thay, "tat_ca": tat_ca,
                    "loai_vi_san_bang_0": sorted(set(hang_so))}
        if not thay:
            mu.append(ten)
        xep = sorted(tat_ca.items(), key=lambda i: -i[1]["sigma"])[:3]
        print(f"  {ten:20} {len(thay)} chi so qua nguong 4σ"
              f"{'  🔴 CONG MU' if not thay else ''}")
        for k, x in xep:
            print(f"      {k:20} {x['nen']:>9} -> {x['hong']:>9}  "
                  f"({x['sigma']}σ){'' if x['sigma'] >= 4 else '  (duoi nguong)'}")

    print("\n" + "=" * 70)
    print("  CONG DANG MU VOI GI")
    print("=" * 70)
    if mu:
        for t in mu:
            print(f"  🔴 {t}")
        print("\n  Do la danh sach nhung gi mot chi so MOI phai bat duoc.")
        print("  Them mot chi so KHONG nam trong danh sach nay la them mot")
        print("  con so nua vao mot cho da nhin thay roi.")
    else:
        print("  ✅ Moi hong hoc tiem vao deu lam it nhat mot chi so nhuc nhich.")
        print("     Cong khong co diem mu nao trong bo nay — them chi so moi")
        print("     can mot lap luan KHAC, khong phai lap luan 'do sau hon'.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"san_nhieu": {k: {kk: round(vv, 5) for kk, vv in v.items()}
                                 for k, v in san.items()},
                   "hong_hoc": ket, "diem_mu": mu}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
