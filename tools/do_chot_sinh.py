r"""
do_chot_sinh.py — bốn chốt của K1 có báo động nhầm trên tiếng THẬT không?

    powershell -ExecutionPolicy Bypass -File .\setup\do_chot_sinh.ps1

## Vì sao phép đo này bắt buộc, không phải "cho chắc"

Ngưỡng `NGUONG_LAP = 0.92` mượn từ hệ cũ, nơi nó chạy trên **F5-TTS ở 24 kHz**.
Không có gì bảo đảm nó đúng cho **VieNeu ở 48 kHz** — hai model, hai cách sinh,
hai phân bố tương quan.

⭐ Và tôi đã có một cảnh báo sớm: chạy thử trên một sóng tuần hoàn tổng hợp, chốt
   báo lặp với tương quan **0,9855** trên một tín hiệu hoàn toàn bình thường. Đó
   *có thể* chỉ là hiện vật của fixture (sóng tuần hoàn thì tự giống nó), nhưng
   "có thể" không phải một câu trả lời.

⛔ Một chốt báo động nhầm còn tệ hơn không có chốt. Nó bắt hệ thống sinh lại một
   bản đọc **vốn đã đúng** — tốn GPU, tốn thời gian chờ của khách — rồi sẽ bị ai
   đó tắt đi, và khi tắt nó kéo theo cả ba chốt còn lại.

## Cách đo

Sinh N lượt tiếng thật với độ dài khác nhau, rồi với mỗi lượt:

  · chạy cả bốn chốt và đếm số lần báo động (đây đều là bản **đúng**, nên mọi
    báo động ở đây là báo động NHẦM);
  · ghi lại **phân bố tương quan đuôi** — thứ quyết định ngưỡng nên đặt ở đâu.

Rồi tiêm một lỗi thật: nhân đôi 0,6 giây cuối, và kiểm chốt có bắt được không.

⭐ Hai vế phải có cả hai. Một chốt không bao giờ báo nhầm mà cũng không bao giờ
   bắt được gì là một chốt vô dụng nhưng trông rất tốt trong báo cáo.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Câu đủ dài để `chot_lap_duoi` chạy (> 2 giây) và đủ khác nhau để không
#: vô tình đo cùng một ngữ điệu nhiều lần.
CAU = [
    "Hôm nay trời nắng đẹp nên tôi đi bộ ra công viên gần nhà một vòng.",
    "Chị ấy nói cuộc họp bắt đầu lúc chín giờ ba mươi sáng mai tại phòng lớn.",
    "Giá vé vào cửa là hai trăm bốn mươi lăm nghìn đồng cho một người lớn.",
    "Khâu khó nhất là chuốt, vì bàn xoay không chờ ai bao giờ, tay phải giữ thành.",
    "Men được pha từ tro trấu, đá vôi và một ít bột đá nghiền thật mịn.",
    "Đừng quên mang theo áo mưa, vì dự báo nói chiều nay có giông rải rác.",
    "Anh Tuấn vừa chuyển tới sống ở quận Bảy được khoảng ba tháng nay rồi.",
    "Cuối cùng, xin cảm ơn bạn đã lắng nghe đoạn ghi âm ngắn này của chúng tôi.",
]


class KhongDoDuoc(RuntimeError):
    """Không đo được thì VỠ, không lặng lẽ thành một con số."""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vong", type=int, default=2, help="So vong qua ca bo cau.")
    ap.add_argument("--ra", default="tmp/chot_sinh.json")
    a = ap.parse_args(argv)

    for m in ("numpy", "soundfile"):
        try:
            __import__(m)
        except ImportError:
            print(f"THIEU {m} — chay bang python cua `vieneu-venv`.",
                  file=sys.stderr)
            return 2

    import numpy as np
    import soundfile as sf

    from apps.ltt_voice import sidecar_client
    from voice_sidecar import chot_sinh as cs

    if not sidecar_client.san_sang():
        print("Cong giong CHUA san sang.", file=sys.stderr)
        return 2

    sidecar_client.noi(CAU[0])          # lam am
    tuong_quan, nham, mau = [], [], []
    print(f"{len(CAU)} cau x {a.vong} vong\n")

    for v in range(a.vong):
        for i, cau in enumerate(CAU):
            raw, dau = sidecar_client.noi(cau)
            w, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
            w = np.asarray(w, dtype=np.float32)

            pq = cs.kiem_het(w, int(sr), len(cau))
            tq = cs.chot_lap_duoi(w, int(sr)).chan_doan.get("tuong_quan")
            if tq is None:
                raise KhongDoDuoc(f"cau {i}: khong do duoc tuong quan duoi")
            tuong_quan.append(float(tq))
            if not pq.dat:
                nham.append({"cau": i, "vong": v, "chot": pq.chan_doan.get("chot"),
                             "ly_do": pq.ly_do})
            mau.append((w, int(sr), len(cau)))
            print(f"  v{v + 1} cau {i + 1}: {len(w) / sr:5.2f}s  "
                  f"tuong quan duoi {tq:.4f}  "
                  f"{'BAO DONG: ' + pq.ly_do if not pq.dat else 'dat'}")

    # ── vế thứ hai: tiêm lỗi thật ────────────────────────────────────────────
    print("\nTiem loi that — nhan doi 0,6 giay cuoi:")
    bat_duoc = 0
    for w, sr, n in mau[:6]:
        k = int(sr * cs.CUA_SO_DUOI_S)
        hong = np.concatenate([w, w[-k:]])
        pq = cs.chot_lap_duoi(hong, sr)
        bat_duoc += 0 if pq.dat else 1
        print(f"  tuong quan {pq.chan_doan.get('tuong_quan'):.4f}  "
              f"{'BAT DUOC' if not pq.dat else 'BO SOT'}")

    tb = statistics.mean(tuong_quan)
    lech = statistics.pstdev(tuong_quan) if len(tuong_quan) > 1 else 0.0
    cao = max(tuong_quan)

    print("\n" + "=" * 70)
    print("  TUONG QUAN DUOI TREN TIENG THAT (day deu la ban DUNG)")
    print("=" * 70)
    print(f"  trung binh : {tb:.4f}")
    print(f"  do lech    : {lech:.4f}")
    print(f"  cao nhat   : {cao:.4f}")
    print(f"  nguong     : {cs.NGUONG_LAP}")
    if lech > 0:
        print(f"  nguong cach trung binh: {(cs.NGUONG_LAP - tb) / lech:.1f} sigma")
    print()
    print(f"  bao dong NHAM : {len(nham)}/{len(tuong_quan)}")
    print(f"  bat duoc loi  : {bat_duoc}/6")
    print()
    if nham:
        print("  🔴 CO BAO DONG NHAM — nguong dang SAI cho engine nay.")
        for x in nham[:5]:
            print(f"     {x}")
    elif bat_duoc < 6:
        print("  🔴 BO SOT LOI TIEM VAO — chot khong lam duoc viec cua no.")
    elif cao > cs.NGUONG_LAP * 0.9:
        print("  ⚠️ Khong bao nham, nhung ban DUNG cao nhat da sat nguong.")
        print("     Bien an toan mong; mot giong khac co the vuot.")
    else:
        print("  ✅ Khong bao nham, bat het loi tiem vao, va con bien an toan.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"tuong_quan": [round(x, 4) for x in tuong_quan],
                   "trung_binh": round(tb, 4), "do_lech": round(lech, 4),
                   "cao_nhat": round(cao, 4), "nguong": cs.NGUONG_LAP,
                   "bao_dong_nham": nham, "bat_duoc_loi_tiem": bat_duoc},
                  f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0 if (not nham and bat_duoc == 6) else 1


if __name__ == "__main__":
    raise SystemExit(main())
