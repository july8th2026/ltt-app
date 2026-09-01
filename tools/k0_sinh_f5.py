r"""
k0_sinh_f5.py — BƯỚC 1 của K0: sinh tiếng bằng hệ CŨ (F5-TTS đã tinh chỉnh).

    powershell -ExecutionPolicy Bypass -File .\setup\k0_sinh_f5.ps1

⚠️ CHẠY BẰNG PYTHON CỦA HỆ CŨ (`D:\Voiceclone_TTS\venv`), không phải venv nào
   của ta. Nó gọi `src.inference.engine_router.generate_voice`, và hàm ấy tự
   sinh một tiến trình con chạy `venv_f5tts` để nạp checkpoint.

## ⛔ CHỈ ĐỌC `D:\Voiceclone_TTS`

Đã kiểm trước khi chạy dòng nào: `f5tts_engine.py` dùng
`tempfile.TemporaryDirectory(prefix="f5tts_")` cho mọi tệp liên lạc và cho cả
`worker_stderr.log`, tức chúng nằm ở thư mục tạm của HỆ THỐNG. Đầu ra thì tệp
này truyền `output_path` tuyệt đối vào `tmp/k0/f5/` của kho ta.

⇒ Không có đường ghi nào vào kho cũ. Nhưng đó là kết luận từ việc **đọc mã**,
  và đọc mã đã sai hai lần trong phiên này — nên tệp này cũng **đếm số tệp**
  trong `speakers/` trước và sau, rồi báo nếu lệch.

## Vì sao K0 tồn tại

Kế hoạch kế thừa tự khai K0 là pha **chặn mọi pha sau**:

    Nếu zero-shot ngang ngửa, cả đường huấn luyện (~7.800 dòng) là thứ KHÔNG
    nên mang sang, và K5 biến mất khỏi kế hoạch. Nếu F5 thắng rõ, K5 thành pha
    chiến lược. Không đo thì mọi pha sau đều đang đoán.

⭐ Nói cho công bằng với những gì đã làm: K1–K4 hoá ra **không** phụ thuộc câu
   trả lời ấy — chúng là chốt chất lượng và tầng chẩn đoán, đúng dù engine nào
   thắng. Nhưng **K5 phụ thuộc hoàn toàn**, và K5 là hạng mục lớn nhất còn lại.

## Tám giọng, và vì sao đúng tám

Hệ cũ có 8 giọng chạy F5 (`engine: f5tts`, `lang: vi`) — và **đúng tám giọng ấy**
nay đã ở hệ mới sau đợt nhập 01/09. Mười bảy giọng còn lại chạy XTTS; so chúng
với VieNeu là so hai thứ khác nhau, và K0 không hỏi câu đó.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

KHO_CU = r"D:\Voiceclone_TTS"

#: Cùng bộ câu với `tools/do_lan_cheo.py::CAU_VI` — cố ý.
#:
#: ⭐ Dùng chung bộ câu nghĩa là hai phép đo khác nhau vẫn so được với nhau, và
#:    con số của K0 đọc được cạnh con số của bảng 2×2 mà không phải hỏi "hai
#:    bên có đọc cùng thứ không". Đổi một câu ở đây là cắt đứt liên hệ ấy.
CAU = [
    "Ba tôi bảo bà ấy bán bánh ở bãi biển vào buổi sáng.",
    "Cô ấy cố gắng có được một cỗ máy mới cho công việc.",
    "Mẹ dặn mà tôi mải mê nên quên mất lời mẹ nói.",
    "Tôi thấy thầy giáo đứng ở cửa lớp từ sáng sớm.",
    "Hôm nay trời hơi lạnh, nhớ mặc áo ấm khi ra ngoài.",
]


def _dem_tep(goc: str) -> int:
    n = 0
    for _, _, tep in os.walk(goc):
        n += len(tep)
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", default="tmp/k0/f5")
    ap.add_argument("--so-lieu", default="tmp/k0/f5_sinh.json")
    a = ap.parse_args(argv)

    sys.path.insert(0, KHO_CU)
    os.chdir(KHO_CU)          # engine của họ giả định cwd là gốc kho của họ

    import yaml
    hs = yaml.safe_load(open(os.path.join(KHO_CU, "configs",
                                          "voice_profiles.yaml"),
                             encoding="utf-8")).get("profiles", {})
    giong = sorted(k for k, v in hs.items()
                   if not str(k).startswith("_")
                   and str(v.get("engine")) == "f5tts")
    print(f"{len(giong)} giong f5tts: {giong}\n")

    ra = os.path.abspath(os.path.join(r"D:\LTTSTUDIOSAPP", a.ra))
    os.makedirs(ra, exist_ok=True)

    canh = os.path.join(KHO_CU, "speakers")
    truoc = _dem_tep(canh)

    from src.inference.engine_router import generate_voice

    ket = []
    for i, g in enumerate(giong, 1):
        for j, c in enumerate(CAU, 1):
            duong = os.path.join(ra, f"{g}__c{j}.wav")
            t0 = time.time()
            try:
                p, meta = generate_voice(c, g, output_path=duong,
                                         output_format="wav")
            except Exception as e:                        # noqa: BLE001
                # Một câu hỏng là một SỐ ĐO, không phải lý do dừng.
                print(f"  [hong] {g} c{j}: {type(e).__name__}: {e}")
                ket.append({"giong": g, "cau": c, "ok": False,
                            "loi": f"{type(e).__name__}: {e}"})
                continue
            giay = time.time() - t0
            ket.append({"giong": g, "cau": c, "ok": True, "wav": p,
                        "giay": round(giay, 2),
                        "meta": {k: v for k, v in dict(meta or {}).items()
                                 if isinstance(v, (int, float, str, bool))}})
            print(f"  [{i}/{len(giong)}] {g:24} c{j}  {giay:5.1f}s  "
                  f"{os.path.basename(p)}")

    sau = _dem_tep(canh)
    if sau != truoc:
        # ⛔ NÓI RA. Kho cũ là chỉ-đọc, và một thay đổi ở đó là chuyện phải biết
        #    ngay, không phải chuyện phát hiện sau ba tuần.
        print(f"\n🔴 SO TEP TRONG `speakers/` DOI: {truoc} -> {sau}. "
              f"Kho cu la CHI DOC — xem lai ngay.", file=sys.stderr)

    d = os.path.abspath(os.path.join(r"D:\LTTSTUDIOSAPP", a.so_lieu))
    os.makedirs(os.path.dirname(d), exist_ok=True)
    with open(d, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"cau": CAU, "giong": giong, "ket": ket}, f,
                  ensure_ascii=False, indent=2)
    ok = sum(1 for k in ket if k.get("ok"))
    print(f"\n{ok}/{len(ket)} thanh cong. Da ghi: {a.so_lieu}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
