r"""
do_giu_giong_nhieu_luot.py — CÂU HỎI QUYẾT ĐỊNH THIẾT KẾ CỦA ĐƯỜNG VĂN BẢN DÀI.

    C:\LTTPlatform\vieneu-venv\Scripts\python.exe -m voice_sidecar.do_giu_giong_nhieu_luot

## Câu hỏi

Văn bản 3.000–5.000 ký tự vượt `TRAN_KY_TU_MOT_LUOT` (1.500), nên nó phải chia
thành nhiều **lượt sinh riêng**. Câu hỏi không phải "ghép các tệp WAV thế nào" —
đó là việc dễ, và engine upstream **đã tự chia chunk 256 ký tự** rồi ghép bên
trong một lượt (`tham_so.MAX_CHARS_CHUNK`). Câu hỏi thật là:

    Hai LƯỢT GỌI riêng biệt có cho ra CÙNG MỘT NGƯỜI NÓI không?

Nếu có, chia lượt là an toàn. Nếu không, thì mọi cách ghép đều vô nghĩa: đoạn 1
và đoạn 4 sẽ là hai người khác nhau, và không hậu xử lý nào cứu được.

## Vì sao phải ĐO chứ không đọc mã

`engine._voice_arg` trả `None` khi không có `ref_b64` lẫn `preset` — tức "giọng
mặc định của SDK". Mã đó **không nói** giọng mặc định được chọn một lần khi nạp
model hay chọn lại mỗi lượt. Đọc mã upstream có thể trả lời, nhưng bộ trọng số
mới là thứ quyết định, và nó không nằm trong mã.

`docs/BAY_TRONG_CONG_CHAT_LUONG.md` của chính kho này đã ghi bài học: **viết lệnh
tái hiện, đừng viết kết luận.**

## Cách đo

Đọc CÙNG một câu N lần, mỗi lần một lượt `infer` riêng, rồi so speaker embedding
từng cặp. Đối chứng là **sàn nhiễu**: cùng một lượt, cắt đôi, so hai nửa với
nhau. Hai nửa của một câu chắc chắn là cùng người, nên tương đồng của chúng là
mức "giống nhau nhất có thể đạt" của thước đo này.

    · giữa các lượt ~= sàn nhiễu   ->  giọng mặc định ỔN ĐỊNH, chia lượt an toàn
    · giữa các lượt << sàn nhiễu   ->  PHẢI ghim một tham chiếu trước khi chia

⛔ Không đặt ngưỡng ĐẠT/HỎNG ở đây. Cùng nguyên tắc với `do_chat_luong.py`: một
   phép đo không có ngưỡng có nguồn thì báo SỐ, và người đọc quyết định.
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np

#: Câu thử. Đủ dài để có đủ tín hiệu cho speaker encoder (~4 giây), đủ ngắn để
#: chạy N lượt không tốn cả buổi.
CAU = ("Hôm nay trời trong xanh, gió nhẹ thổi qua hàng cây bên đường, và những "
       "người đi bộ dừng lại nghe một bản nhạc quen thuộc.")


def _encoder():
    """Cùng bộ mã hoá người nói mà `do_chat_luong.py` dùng — để hai bộ đo so
    được với nhau. Hai thước khác nhau cho hai con số không so được."""
    from .do_chat_luong import _bo_ma_hoa_giong
    return _bo_ma_hoa_giong()


def _cos(a, b) -> float:
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-luot", type=int, default=4)
    ap.add_argument("--preset", default="", help="Do voi mot giong dung san.")
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)

    from . import engine as eng

    c = eng.CongGiong()
    c.nap()
    sr = c.sample_rate
    ma_hoa = _encoder()

    wavs = []
    for i in range(a.so_luot):
        wav, giay = c.noi(CAU, preset=(a.preset or None))
        wavs.append(np.asarray(wav, dtype=np.float32))
        print(f"  luot {i + 1}/{a.so_luot}: {len(wav) / sr:.2f}s tieng, "
              f"{giay:.2f}s sinh")

    from .do_chat_luong import _embed

    nhung = [_embed(ma_hoa, w, sr) for w in wavs]

    # ── sàn nhiễu: hai nửa của CÙNG một lượt ────────────────────────────────
    san = []
    for w in wavs:
        giua = len(w) // 2
        if giua < sr:                      # dưới 1 giây mỗi nửa thì bỏ
            continue
        san.append(_cos(_embed(ma_hoa, w[:giua], sr),
                        _embed(ma_hoa, w[giua:], sr)))

    # ── giữa các lượt ───────────────────────────────────────────────────────
    cap = [(i, j, _cos(nhung[i], nhung[j]))
           for i in range(len(nhung)) for j in range(i + 1, len(nhung))]

    kq = {
        "so_luot": a.so_luot,
        "preset": a.preset or "(mac dinh SDK)",
        "san_nhieu": {
            "mo_ta": "hai nua cua CUNG mot luot — chac chan cung nguoi noi",
            "gia_tri": [round(x, 4) for x in san],
            "trung_binh": round(float(np.mean(san)), 4) if san else None,
            "thap_nhat": round(float(np.min(san)), 4) if san else None,
        },
        "giua_cac_luot": {
            "gia_tri": [round(v, 4) for _, _, v in cap],
            "trung_binh": round(float(np.mean([v for _, _, v in cap])), 4) if cap else None,
            "thap_nhat": round(float(np.min([v for _, _, v in cap])), 4) if cap else None,
        },
    }

    sn = kq["san_nhieu"]["trung_binh"]
    gl = kq["giua_cac_luot"]["trung_binh"]
    print()
    print("=" * 66)
    print(f"  giong: {kq['preset']}")
    print(f"  san nhieu (trong mot luot) : tb {sn}  thap nhat "
          f"{kq['san_nhieu']['thap_nhat']}")
    print(f"  giua cac luot              : tb {gl}  thap nhat "
          f"{kq['giua_cac_luot']['thap_nhat']}")
    if sn is not None and gl is not None:
        kq["chenh"] = round(sn - gl, 4)
        print(f"  chenh                      : {kq['chenh']}")
        print()
        print("  Doc con so nay the nao: `chenh` gan 0 nghia la hai luot rieng")
        print("  giong nhau NGANG hai nua cua mot luot — tuc giong mac dinh on")
        print("  dinh, va chia van ban dai thanh nhieu luot la an toan.")
        print("  `chenh` lon nghia la moi luot mot nguoi khac -> PHAI ghim mot")
        print("  tham chieu truoc khi chia, khong co cach ghep nao cuu duoc.")
    print("=" * 66)

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(kq, f, ensure_ascii=False, indent=2)
        print(f"Da ghi: {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
