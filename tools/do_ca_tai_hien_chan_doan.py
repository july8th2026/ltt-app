r"""
do_ca_tai_hien_chan_doan.py — mỗi luật chẩn đoán có một CA TÁI HIỆN ĐƯỢC không.

    powershell -ExecutionPolicy Bypass -File .\setup\do_ca_tai_hien_chan_doan.ps1

## Điều kiện qua của K4, nguyên văn

    "Qua khi mỗi luật có ít nhất một ca thật tái hiện được, và bộ khuyến nghị
     đề xuất đúng thay đổi trên ca đó."

Một luật chưa từng nổ là một luật **không ai biết nó có chạy hay không**. Nó
trông y hệt một luật đang canh tốt — cho tới ngày cần nó.

⭐ Đây là cùng phương pháp với `do_diem_mu_cong.py` của K3, và cố ý: tiêm một
   hỏng hóc ĐÃ BIẾT rồi xem chỉ số/luật nào phản ứng. Khác một chỗ quan trọng:
   K3 hỏi *"cổng có THẤY không"*, tệp này hỏi *"luật có nổ ĐÚNG luật không"* —
   một luật nổ nhầm chỗ còn tệ hơn một luật im, vì nó gửi khách đi sửa nhầm thứ.

## ⛔ KHÔNG CHẠM GPU

Nó tiêm hỏng hóc vào **những tệp K0 đã sinh** (`tmp/k0/vieneu/*.wav`) và so với
**clip tham chiếu gốc** (`tmp/giong_cu/*.wav`). Không sinh tiếng mới lần nào.

⭐ Nghĩa là nó chạy được trong lúc một lô GPU khác đang chạy, và nó **lặp lại
   được** — cùng tệp vào, cùng kết quả ra. Một phép kiểm tái hiện mà bản thân nó
   không tái hiện được thì chứng minh được gì?

## Giới hạn đã biết, ghi ra thay vì giấu

Vài luật khó tiêm sạch bằng xử lý tín hiệu thuần:

  · **R15 (đơn điệu hơn)** cần làm phẳng đường F0 mà giữ nguyên nội dung. Cách
    làm ở đây — đổi tần số từng cửa sổ để kéo F0 về trung vị — là **thô**, và nó
    cũng đụng vào nhịp. Nếu R15 không nổ thì đọc là *"phép tiêm chưa đủ sạch"*,
    KHÔNG phải *"luật hỏng"*.
  · **R13/R14 (cao độ)** tiêm bằng đổi tần số, nên nó đổi cả **độ dài**. Với
    `delta_f0_trung_vi_hz_ti_le` thì không sao — phép đo lấy trung vị, không lấy
    thời lượng. Nhưng đừng dùng cùng tệp ấy để chấm nhịp.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)


# ── các phép tiêm ───────────────────────────────────────────────────────────

def _loc_thap(w, sr, cat=2500.0):
    from scipy.signal import butter, sosfilt
    import numpy as np
    sos = butter(6, cat / (sr / 2), btype="low", output="sos")
    return np.asarray(sosfilt(sos, w), dtype="float32")


def _day_dai_cao(w, sr, tang_db=14.0):
    """Nâng dải cao — bản sinh ra 'chói' hơn tham chiếu."""
    from scipy.signal import butter, sosfilt
    import numpy as np
    sos = butter(4, 4000.0 / (sr / 2), btype="high", output="sos")
    cao = np.asarray(sosfilt(sos, w), dtype="float32")
    k = 10 ** (tang_db / 20.0) - 1.0
    return np.asarray(w + k * cao, dtype="float32")


def _nghieng_pho(w, sr):
    """Dịch trọng tâm phổ mà không cắt hẳn dải nào."""
    from scipy.signal import butter, sosfilt
    import numpy as np
    sos = butter(2, 1200.0 / (sr / 2), btype="high", output="sos")
    return np.asarray(w + 2.0 * np.asarray(sosfilt(sos, w)), dtype="float32")


def _doi_cao_do(w, sr, ti_le):
    """Đổi cao độ bằng đổi tần số. ⚠️ Đổi cả độ dài — xem docstring."""
    import numpy as np
    try:
        import soxr
        return np.asarray(soxr.resample(w, sr, int(sr / ti_le)),
                          dtype="float32")
    except ImportError:
        n = int(round(len(w) / ti_le))
        return np.interp(np.linspace(0, len(w) - 1, n),
                         np.arange(len(w)), w).astype("float32")


def _lam_phang_f0(w, sr):
    """Kéo F0 từng cửa sổ về trung vị chung. THÔ — xem docstring."""
    import numpy as np
    from voice_sidecar.do_on_dinh import _f0_khung
    f0, huu = _f0_khung(np.asarray(w, dtype=np.float64), sr)
    if huu.sum() < 24:
        return np.asarray(w, dtype="float32")
    tv = float(np.median(f0[huu]))
    n = int(sr * 0.25)
    manh = []
    for i in range(0, len(w), n):
        doan = np.asarray(w[i:i + n], dtype="float32")
        if doan.size < 64:
            manh.append(doan)
            continue
        f, h = _f0_khung(doan.astype(np.float64), sr)
        if h.sum() < 4:
            manh.append(doan)
            continue
        cuc_bo = float(np.median(f[h]))
        if cuc_bo <= 0:
            manh.append(doan)
            continue
        manh.append(_doi_cao_do(doan, sr, tv / cuc_bo))
    return np.concatenate(manh).astype("float32")


def _rung_bien_do(w, sr, sau=0.35, nhip=5.0):
    import numpy as np
    t = np.arange(len(w)) / sr
    return (w * (1.0 + sau * np.sin(2 * np.pi * nhip * t))).astype("float32")


def _doi_do_to(w, sr, db=9.0):
    import numpy as np
    return np.asarray(w * (10 ** (db / 20.0)), dtype="float32")


#: `(ma_luat_mong_doi, ten, ham)`.
TIEM = [
    ("R12a", "duc_2k5",        lambda w, sr: _loc_thap(w, sr)),
    # ⚠️ +30 dB, không phải +14. Lần đo đầu tiêm +14 và luật IM: nó đẩy
    #    `delta_db_dai_cao` đi +5,36 trên một dung sai **13,53 dB**.
    #    Dung sai rộng như vậy vì `lech` đo được là 3,38 dB — độ sáng của clip
    #    tham chiếu **khác nhau rất nhiều giữa các người nói**, và baseline gộp
    #    chung tám giọng nên nó nuốt cả biến động ấy.
    #
    # ⭐ Nên con số đúng để ghi lại KHÔNG phải "R12b có nổ" mà là **R12b chỉ
    #    thấy được lệch độ sáng cỡ trên +10 dB**. Nó là một luật bắt hỏng hóc
    #    THÔ, và nói ra điều đó có ích hơn là chỉnh phép tiêm cho tới khi xanh.
    ("R12b", "choi_+30dB",     lambda w, sr: _day_dai_cao(w, sr, 30.0)),
    ("R12c", "nghieng_pho",    lambda w, sr: _nghieng_pho(w, sr)),
    ("R13",  "tram_-25pc",     lambda w, sr: _doi_cao_do(w, sr, 0.75)),
    ("R14",  "cao_+33pc",      lambda w, sr: _doi_cao_do(w, sr, 1.33)),
    ("R17",  "to_+9dB",        lambda w, sr: _doi_do_to(w, sr)),
]

#: Hỏng hóc ta **BIẾT là không bắt được**, giữ lại để nó có tên.
#:
#: 🔴 Rung biên độ từng là luật R16, và đã **gỡ 01/09** — không phải vì nó không
#:    quan trọng mà vì ta không có phép đo nào thấy được nó, và điều đó đã chứng
#:    minh hai lần:
#:
#:      · K3 thử BA cơ chế (năng lượng dải 3–8 Hz · độ nhọn trên bao tuyến tính
#:        · độ nhọn trên **log** bao). Cao nhất 1,7σ trên ngưỡng 4σ. Lý do là
#:        vật lý: nhịp rung giọng người (~5,5 Hz) **trùng nhịp âm tiết** tiếng
#:        Việt, nên không có mốc dải nào tách được chúng.
#:      · Ca tái hiện của K4: tiêm rung **35%** — gấp sáu lần mức K3 thử — chỉ
#:        đẩy `delta_dao_dong_khung` đi −0,005 trên dung sai 0,135, tức **sai
#:        chiều và bằng 1/27 ngưỡng**.
#:
#: ⭐ Giữ nó ở đây thay vì xoá, vì một điểm mù **có tên** là một điểm mù người
#:    sau biết mà tránh; một điểm mù bị xoá khỏi mã thì lần sau có người lại
#:    khám phá ra nó từ đầu. Và nếu ngày nào đó một chỉ số mới bắt được nó, bộ
#:    dò sẽ NÓI RA — lúc ấy đưa R16 về là có căn cứ.
TIEM_MU = [
    ("(da go R16)", "rung_35pc", lambda w, sr: _rung_bien_do(w, sr)),
    # 🔴 R15 (đơn điệu hơn) gỡ 01/09 vì một lý do khác hẳn R16: chỉ số ĐO ĐƯỢC
    #    hiện tượng, nhưng nền của nó là **-0,4556** (bản sinh ra chỉ giữ 54%
    #    biến thiên cao độ của gốc, ở mọi bản khoẻ mạnh) với độ lệch 0,2519.
    #    Một bản PHẲNG LÌ HOÀN TOÀN — cận dưới tuyệt đối -1,0 — chỉ cách trung
    #    bình 2,2σ, dưới ngưỡng 4σ.
    #
    # ⭐ Giữ phép tiêm ở đây để nếu ngày nào đó chỉ số bớt nhiễu (vd baseline
    #    theo TỪNG GIỌNG thay vì gộp 8 giọng) thì bộ dò sẽ NÓI RA ngay.
    ("(da go R15)", "phang_f0", lambda w, sr: _lam_phang_f0(w, sr)),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", default="tmp/k0/vieneu")
    ap.add_argument("--clip-ref", default="tmp/giong_cu")
    ap.add_argument("--so-mau", type=int, default=6,
                    help="So ban lay mau cho moi phep tiem.")
    ap.add_argument("--ra", default="tmp/ca_tai_hien_chan_doan.json")
    a = ap.parse_args(argv)

    import soundfile as sf

    from voice_sidecar import chan_doan, lech_tham_chieu

    bl = "voice_sidecar/baseline_lech.json"
    if not os.path.isfile(bl):
        print(f"THIEU {bl} — chay `do_lech_tham_chieu.ps1 -Ghim` truoc.",
              file=sys.stderr)
        return 2
    san = (json.load(open(bl, encoding="utf-8")) or {}).get("do") or {}

    cac = sorted(glob.glob(os.path.join(a.wav, "*.wav")))
    if not cac:
        print(f"KHONG CO WAV trong {a.wav}", file=sys.stderr)
        return 2
    buoc = max(1, len(cac) // a.so_mau)
    cac = cac[::buoc][:a.so_mau]

    print(f"{len(cac)} ban x {len(TIEM)} phep tiem  (KHONG cham GPU)\n")

    ket = {}
    for ma, ten, ham in TIEM:
        no_dung, no_nham, im = 0, [], 0
        for p in cac:
            goc_ma = os.path.basename(p).split("__")[0]
            ref = os.path.join(a.clip_ref, f"{goc_ma}.wav")
            if not os.path.isfile(ref):
                continue
            w, sr = sf.read(p, dtype="float32", always_2d=False)
            wr, srr = sf.read(ref, dtype="float32", always_2d=False)
            if getattr(w, "ndim", 1) > 1:
                w = w.mean(axis=1)
            if getattr(wr, "ndim", 1) > 1:
                wr = wr.mean(axis=1)
            try:
                hong = ham(w, int(sr))
            except Exception as e:                        # noqa: BLE001
                print(f"  [tiem hong] {ten}: {type(e).__name__}: {e}")
                continue
            lech = lech_tham_chieu.do_lech(hong, int(sr), wr, int(srr))
            pf = chan_doan.chan_doan(lech, san).get("phat_hien") or []
            ma_no = {x["ma"] for x in pf}
            if ma in ma_no:
                no_dung += 1
            elif ma_no:
                no_nham.append(sorted(ma_no))
            else:
                im += 1
        ket[ma] = {"phep_tiem": ten, "no_dung": no_dung,
                   "no_nham": no_nham, "im": im, "so_ban": len(cac)}
        dau = "OK  " if no_dung else "🔴 IM"
        print(f"  {dau} {ma:5} {ten:16} no dung {no_dung}/{len(cac)}"
              + (f"  | no NHAM: {no_nham[:2]}" if no_nham else "")
              + (f"  | im {im}" if im else ""))

    # ── điểm mù có tên: KHÔNG được nổ ─────────────────────────────────────
    print()
    for nhan, ten_mu, ham_mu in TIEM_MU:
        no, bo_qua = 0, []
        for p2 in cac:
            goc2 = os.path.basename(p2).split("__")[0]
            ref2 = os.path.join(a.clip_ref, goc2 + ".wav")
            if not os.path.isfile(ref2):
                continue
            w2, sr2 = sf.read(p2, dtype="float32", always_2d=False)
            wr2, srr2 = sf.read(ref2, dtype="float32", always_2d=False)
            if getattr(w2, "ndim", 1) > 1:
                w2 = w2.mean(axis=1)
            if getattr(wr2, "ndim", 1) > 1:
                wr2 = wr2.mean(axis=1)
            try:
                l2 = lech_tham_chieu.do_lech(ham_mu(w2, int(sr2)), int(sr2),
                                             wr2, int(srr2))
            except Exception as ex:                       # noqa: BLE001
                # 🔴 ĐẾM VÀ NÓI RA, đừng `continue` trần.
                #
                #    Trong một bộ đo PHÉP TIÊM, "bỏ qua vì lỗi" và "chạy xong,
                #    không phát hiện" là **hai sự kiện khác hẳn**. Nuốt lỗi gộp
                #    chúng làm một: mẫu nhỏ đi mà không ai biết, rồi
                #    `co_luat_no` đọc lên như kết quả trên mẫu đầy đủ — tức tỉ
                #    lệ "không tác dụng" bị thổi phồng **theo hướng làm hại**,
                #    lặng lẽ.
                #
                # ⭐ Chỗ này do phiên `lttstudiosapp-c3` chỉ ra khi nó làm gate
                #    đỏ ở `check_silent_except.py` (64 > mốc 63). Đề xuất của
                #    họ đúng hơn bản đầu của tôi, và nó hạ bánh cóc một cách
                #    THẬT chứ không phải bằng cách nâng mốc.
                #
                # ⚠️ `# noqa: BLE001` chỉ tắt **ruff**. `check_silent_except.py`
                #    đọc AST riêng và vẫn đếm — hai cơ chế không liên quan.
                bo_qua.append(f"{os.path.basename(p2)}: "
                              f"{type(ex).__name__}: {ex}")
                continue
            if chan_doan.chan_doan(l2, san).get("phat_hien"):
                no += 1
        ket[nhan] = {"phep_tiem": ten_mu, "diem_mu": True, "co_luat_no": no,
                     "bo_qua": bo_qua, "so_ban": len(cac),
                     "so_da_chay": len(cac) - len(bo_qua)}
        if bo_qua:
            print(f"  ⚠️ {nhan}: bo qua {len(bo_qua)}/{len(cac)} ban vi loi — "
                  f"ket qua duoi day tinh tren {len(cac) - len(bo_qua)} ban")
            for x in bo_qua[:3]:
                print(f"     {x}")
        if no:
            # ⭐ Đây là TIN TỐT, không phải lỗi: một chỉ số nào đó nay thấy được
            #    thứ trước kia mù. Nhưng nó phải được NÓI RA, không lặng lẽ.
            print("  ⭐ " + nhan + " " + ten_mu
                  + " nay CO luat no o " + str(no) + "/" + str(len(cac))
                  + " ban => co the dua R16 ve, da co can cu.")
        else:
            print("  (mu) " + nhan + " " + ten_mu
                  + " khong luat nao no — dung nhu da biet")

    # ⛔ Bỏ qua các mục ĐIỂM MÙ: chúng không có `no_dung` vì chúng không phải
    #    một luật đang canh — chúng là một hỏng hóc ta đã biết là không bắt
    #    được, giữ lại để nó có tên.
    thieu = sorted(k for k, v in ket.items()
                   if not v.get("diem_mu") and not v["no_dung"])
    if thieu:
        print(f"  🔴 LUAT CHUA CO CA TAI HIEN: {thieu}")
        print("     Mot luat chua tung no la mot luat khong ai biet no co chay")
        print("     hay khong — no trong y het mot luat dang canh tot.")
    else:
        print("  ✅ MOI LUAT DEU CO IT NHAT MOT CA TAI HIEN DUOC.")
    print("=" * 72)

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ket, f, ensure_ascii=False, indent=2)
    print(f"Da ghi: {a.ra}")
    return 1 if thieu else 0


if __name__ == "__main__":
    raise SystemExit(main())
