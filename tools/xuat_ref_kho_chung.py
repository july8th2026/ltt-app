r"""
xuat_ref_kho_chung.py — xuất biểu diễn tham chiếu của kho giọng dùng chung ra
một tệp JSON, để bộ đo chạy được ở venv KHÁC.

    powershell -ExecutionPolicy Bypass -File .\setup\xuat_ref_kho_chung.ps1

## Vì sao phải tách làm hai bước

Hai venv trên máy này có hai tập thư viện **rời nhau**, và không phải ngẫu
nhiên:

  · `C:\LTTPlatform\venv`          — có `sqlalchemy`, `faster_whisper`; KHÔNG có
                                     `soundfile`, `librosa`.
  · `D:\LTTPlatform-runtime\vieneu-venv` — ngược lại: có `soundfile`,
                                     `torch`, engine; KHÔNG có `sqlalchemy`.

Bộ đo chất lượng cần venv thứ hai (đọc wav, chấm DNSMOS). Đọc hồ sơ giọng cần
venv thứ nhất (CSDL). Một bộ đo cần cả hai thì phải đi qua một tệp.

🔴 Đã trả giá cho việc bỏ qua điều này: bản đầu của `do_giong_nguon_ngoai_ngu.py`
   chạy ở venv nền tảng, và **mọi lượt đều hỏng** với
   `ModuleNotFoundError: No module named 'soundfile'` — nhưng nó bắt ngoại lệ
   theo từng câu (đúng, vì một câu hỏng là một số đo) nên nó vẫn in ra một bảng
   kết quả đầy đủ với `n=0` ở mọi dòng. Một bảng trống trông rất giống một bảng
   có số nếu không nhìn cột `n`.

⚠️ Tệp sinh ra chứa **biểu diễn giọng của khách**. Nó là dữ liệu sinh trắc:
   ghi vào `tmp/`, đừng commit, xoá sau khi đo xong.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", default="tmp/ref_kho_chung.json")
    a = ap.parse_args(argv)

    from sqlalchemy import select

    from apps.ltt_voice import tham_chieu
    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        ds = list(db.execute(select(VoiceProfile).where(
            VoiceProfile.dung_chung.is_(True),
            VoiceProfile.trang_thai == "active")
            .order_by(VoiceProfile.ten_hien_thi)).scalars())
        ra = []
        for h in ds:
            bd = tham_chieu.tim_repr_active(db, h.id)
            if bd is None:
                print(f"  [bo] {h.ten_hien_thi}: khong co bieu dien active")
                continue
            ra.append({"public_id": h.public_id, "ten": h.ten_hien_thi,
                       "ngon_ngu_khai": h.ngon_ngu,
                       # ⛔ PHẢI kèm `ghi_chu`: nó chứa `ma_cu`, và đó là thứ
                       #    DUY NHẤT nối một hồ sơ với clip tham chiếu gốc của
                       #    nó. Bản đầu bỏ trường này, nên
                       #    `do_lech_tham_chieu.py` ghép được **0 giọng**.
                       #    Ghép bằng TÊN thì trượt cả bốn giọng đầu tiên (tên
                       #    đã đổi hoàn toàn: "Ivy" ← `hoathinh_female`).
                       "ghi_chu": h.ghi_chu or "",
                       "ref_b64": tham_chieu.nap_ref_b64(bd)})
            print(f"  [ok] {h.ten_hien_thi}")
    finally:
        gen.close()

    if not ra:
        print("KHO CHUNG RONG", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ra, f, ensure_ascii=False)
    print(f"\nDa ghi {len(ra)} giong: {a.ra}")
    print("⚠️ Tep nay chua bieu dien giong — xoa sau khi do xong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
