r"""xuat_mau_toc_do.py — xuat MOT ban thu tieng Viet o NHIEU toc do de nghe thu.

    C:\LTTPlatform\vieneu-venv\Scripts\python.exe tools\xuat_mau_toc_do.py \
        --ra-dir "G:\My Drive\AI\A\Voice"

Tong hop MOT lan (speed 1.0 la ban goc), roi ap toc_do.ap_dung cho tung nac,
luu moi nac thanh mot tep ten = toc do (vd `1.0.wav`, `2.0.wav`). In thoi luong
that cua ban goc (ffprobe) de xac nhan ~1 phut.

⛔ Goi thang sidecar_client.noi (nhe, chi requests) — chay tron vieneu-venv.
   Chay qua lop nap app.env (LTT_VOICE_SIDECAR_TOKEN). Xem wrapper .ps1.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

#: Ban thu tieng Viet ~1200+ ky tu -> speed 1.0 khoang 1 phut. Khong bi mat.
TEXT = (
    "Xin chào và chào mừng bạn đến với LTT Studios. Đây là bản thu thử để bạn "
    "nghe cách giọng đọc thể hiện ở nhiều tốc độ khác nhau. Cùng một đoạn văn "
    "bản, cùng một giọng, chỉ khác tốc độ phát, sẽ giúp bạn cảm nhận rõ sự thay "
    "đổi về độ tự nhiên và độ rõ ràng của lời đọc. "
    "Trong một buổi sáng mùa thu, ánh nắng nhẹ trải dài trên con đường quen "
    "thuộc. Những hàng cây hai bên đường khẽ đung đưa theo làn gió, mang theo "
    "hương thơm dịu của lá và của đất sau cơn mưa đêm. Người đi đường bước chậm "
    "rãi, nhấp một ngụm cà phê nóng, và lắng nghe âm thanh của thành phố đang "
    "dần thức giấc. "
    "Chúng tôi tin rằng một giọng đọc tốt không chỉ phát ra đúng từng chữ, mà "
    "còn phải giữ được nhịp điệu, cảm xúc và sự mạch lạc từ đầu đến cuối. Khi "
    "bạn tăng tốc độ, câu chữ trở nên gấp gáp hơn; khi bạn giảm tốc độ, từng âm "
    "tiết được kéo dài ra và nghe thong thả hơn. Hãy thử so sánh các phiên bản "
    "để chọn tốc độ phù hợp nhất với nội dung mà bạn muốn truyền tải. "
    "Mỗi tốc độ đều có chỗ dùng riêng: bản chậm hợp cho hướng dẫn cần nghe kỹ, "
    "bản nhanh hợp khi bạn muốn lướt nhanh qua nội dung đã quen. Điều quan trọng "
    "là giọng đọc vẫn giữ được sự tự nhiên và dễ nghe ở mức tốc độ bạn chọn. "
    "Cảm ơn bạn đã dành thời gian lắng nghe bản thu này. Nếu nó hữu ích, hãy "
    "tiếp tục khám phá thêm những khả năng khác mà chúng tôi mang lại. Chúc bạn "
    "một ngày làm việc thật hiệu quả và tràn đầy niềm vui."
)

SPEEDS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


def _ffprobe_dur(path: str) -> float:
    from platform_core.media import ffprobe_bin
    out = subprocess.run(
        [ffprobe_bin(), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=30)
    return float((out.stdout or "0").strip() or 0)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra-dir", required=True, help="Thu muc luu WAV.")
    ap.add_argument("--preset", default="", help="Ten preset. Bo trong=mac dinh.")
    ap.add_argument("--text-file", default="", help="Doc text tu tep UTF-8 (thay TEXT).")
    a = ap.parse_args(argv)

    from apps.ltt_voice import giong_mau, sidecar_client, toc_do

    if not sidecar_client.san_sang():
        print("DUNG: sidecar chua san sang (thieu LTT_VOICE_SIDECAR_TOKEN).")
        return 2

    text = TEXT
    if a.text_file:
        with open(a.text_file, encoding="utf-8") as f:
            text = f.read().strip()
    preset = a.preset or giong_mau.MAC_DINH
    os.makedirs(a.ra_dir, exist_ok=True)

    print(f"Text: {len(text)} ky tu | preset={preset} | ra-dir={a.ra_dir}")
    print("Tong hop ban goc (speed 1.0)...")
    wav_goc, _ = sidecar_client.noi(text, preset=preset)

    for sp in SPEEDS:
        wav = toc_do.ap_dung(wav_goc, sp) if abs(sp - 1.0) >= 0.01 else wav_goc
        ten = f"{sp}.wav"
        duong = os.path.join(a.ra_dir, ten)
        with open(duong, "wb") as f:
            f.write(wav)
        dur = _ffprobe_dur(duong)
        print(f"  luu {ten:<9} {dur:6.1f}s  {len(wav):>9} byte")

    goc_path = os.path.join(a.ra_dir, "1.0.wav")
    print(f"\nBan goc (1.0): {_ffprobe_dur(goc_path):.1f}s "
          f"— muc tieu ~60-70s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
