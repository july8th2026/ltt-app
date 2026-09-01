r"""
do_lech_tham_chieu.py — đo BASELINE cho các chỉ số lệch của K4.

    powershell -ExecutionPolicy Bypass -File .\setup\xuat_ref_kho_chung.ps1
    powershell -ExecutionPolicy Bypass -File .\setup\do_lech_tham_chieu.ps1 -Ghim

## Baseline này đo cái gì

`voice_sidecar/lech_tham_chieu.do_lech` trả hiệu giữa bản sinh ra và clip tham
chiếu của chính giọng đó. `voice_sidecar/chan_doan` biến hiệu ấy thành phát
hiện — nhưng chỉ khi biết **hiệu bao nhiêu là bình thường**.

🔴 VÀ "BÌNH THƯỜNG" Ở ĐÂY KHÔNG PHẢI SỐ KHÔNG. Đó là điều dễ đoán sai nhất về
   tầng này:

     · Bản sinh ra đọc **văn bản khác** với clip tham chiếu, nên nhịp nghỉ, độ
       tản F0, dao động biên độ đều khác — kể cả khi nhân bản hoàn hảo.
     · Đường sinh có **chuẩn hoá độ to riêng**, nên `delta_lufs` lệch một cách
       hệ thống, không phải ngẫu nhiên.
     · Clip tham chiếu là tiếng thu thật; bản sinh ra đi qua một codec neural.
       Hai thứ ấy có phổ khác nhau **theo một hướng cố định**.

⇒ Nên baseline phải ghi cả **trung bình** (lệch hệ thống) lẫn **độ lệch chuẩn**
  (dao động quanh nó). Một tầng chẩn đoán giả định trung bình bằng 0 sẽ báo
  động ở **mọi** bản, và nó sẽ bị tắt trong một tuần.

## Vì sao lấy mẫu nhiều GIỌNG chứ không nhiều LƯỢT của một giọng

Hai nguồn dao động khác nhau:

  · giữa hai lượt sinh của **cùng một giọng, cùng câu** — nhiễu của model;
  · giữa **các giọng khác nhau** — clip tham chiếu của mỗi người một kiểu thu.

Ngưỡng của `chan_doan` phải chịu được cả hai, vì nó sẽ chấm một giọng bất kỳ
của một khách bất kỳ. Nên lô đo trải trên nhiều giọng, và số ghi ra là dao động
**tổng hợp**.

⚠️ Đó cũng là lý do nó KHÔNG so được với sàn nhiễu của K3 (n=24 lượt trên MỘT
   giọng). Hai con số đo hai thứ khác nhau; đặt cạnh nhau là mời người đọc trừ
   chúng cho nhau.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

#: Câu dùng để sinh. Ngắn và đa dạng — mục đích là lấy dao động, không phải
#: kiểm chất lượng từng câu.
CAU = [
    "Xin chào, đây là một câu để đo độ lệch so với bản tham chiếu.",
    "Hôm nay trời khá đẹp, chúng tôi sẽ bắt đầu công việc từ sáng sớm.",
    "Bản báo cáo cho thấy số lượng khách hàng tăng đều trong ba tháng.",
]

RA_BASELINE = "voice_sidecar/baseline_lech.json"


def _mot_luot(ref_b64: str, wav_ref, sr_ref: int, cau: str) -> dict:
    import io

    import soundfile as sf

    from apps.ltt_voice import sidecar_client
    from voice_sidecar import lech_tham_chieu

    raw, _ = sidecar_client.noi(cau, ref_b64=ref_b64)
    w, s = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
    if getattr(w, "ndim", 1) > 1:
        w = w.mean(axis=1)
    return lech_tham_chieu.do_lech(w, int(s), wav_ref, sr_ref)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="tmp/ref_kho_chung.json")
    ap.add_argument("--clip", default="tmp/giong_cu",
                    help="Thu muc chua clip THAM CHIEU goc (wav).")
    ap.add_argument("--so-giong", type=int, default=8)
    ap.add_argument("--ghim", action="store_true",
                    help="Ghi baseline. Khong co co nay thi chi IN.")
    ap.add_argument("--ra", default=RA_BASELINE)
    a = ap.parse_args(argv)

    if not os.path.isfile(a.ref):
        print(f"THIEU {a.ref} — chay `xuat_ref_kho_chung.ps1` truoc.",
              file=sys.stderr)
        return 2

    import soundfile as sf

    with open(a.ref, encoding="utf-8") as f:
        cac = json.load(f)

    # Ghép hồ sơ với clip tham chiếu GỐC qua `ghi_chu` (xuất xứ do K4 ghi lúc
    # nhập). Không có xuất xứ thì bỏ qua — đoán bằng tên là cách bốn giọng đầu
    # tiên đã mất đường truy.
    viec = []
    for g in cac:
        gc = g.get("ghi_chu") or ""
        try:
            ma = (json.loads(gc) or {}).get("ma_cu")
        except ValueError:
            ma = None
        if not ma:
            continue
        d = os.path.join(a.clip, f"{ma}.wav")
        if os.path.isfile(d):
            viec.append({**g, "ma_cu": ma, "clip_ref": d})
    viec.sort(key=lambda x: x["public_id"])
    buoc = max(1, len(viec) // a.so_giong)
    viec = viec[::buoc][:a.so_giong]

    if not viec:
        print("KHONG GHEP DUOC HO SO NAO VOI CLIP THAM CHIEU.", file=sys.stderr)
        print("Ho so can `ghi_chu` co `ma_cu` (do `nhap_kho_giong_cu.py` ghi).",
              file=sys.stderr)
        return 2

    print(f"{len(viec)} giong x {len(CAU)} cau\n")
    gom: dict = {}
    for i, g in enumerate(viec, 1):
        w, s = sf.read(g["clip_ref"], dtype="float32", always_2d=False)
        if getattr(w, "ndim", 1) > 1:
            w = w.mean(axis=1)
        for c in CAU:
            try:
                d = _mot_luot(g["ref_b64"], w, int(s), c)
            except Exception as e:                        # noqa: BLE001
                # Một câu hỏng là một SỐ ĐO, không phải lý do dừng.
                print(f"  [hong] {g['ten'][:24]}: {type(e).__name__}: {e}")
                continue
            for k, v in d.items():
                gom.setdefault(k, []).append(float(v))
        print(f"  [{i}/{len(viec)}] {g['ten'][:34]:34} ({g['ma_cu']})")

    if not gom:
        print("KHONG DO DUOC GI", file=sys.stderr)
        return 1

    do = {}
    for k, v in sorted(gom.items()):
        if len(v) < 2:
            continue
        do[k] = {"tb": round(statistics.mean(v), 5),
                 "lech": round(statistics.pstdev(v), 5), "n": len(v)}

    print("\n" + "=" * 74)
    print("  BASELINE CHI SO LECH  (trung binh KHONG phai 0 — xem docstring)")
    print("=" * 74)
    for k, m in do.items():
        print(f"  {k:34} tb {m['tb']:>10.4f}  lech {m['lech']:>9.4f}  n={m['n']}")

    if not a.ghim:
        print("\n(chi IN — them `-Ghim` de ghi baseline)")
        return 0

    from voice_sidecar import do_chat_luong
    bl = {"phien_ban_bo_do": do_chat_luong._PHIEN_BAN_BO_DO,
          "so_giong": len(viec), "so_cau": len(CAU), "do": do}
    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(bl, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi baseline: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
