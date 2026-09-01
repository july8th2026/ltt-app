r"""
do_gia_von_voice.py — GIÁ VỐN một giây tiếng nói, đo thật trên máy A.

    powershell -ExecutionPolicy Bypass -File .\setup\do_gia_von_voice.ps1

## Vì sao phải đo chứ không ước

`apps/ltt_voice/gia.py` bán **200 mcredit mỗi giây tiếng** và tự nói ra rằng đó
là **giá tạm**: *"Chưa đối chiếu được với giá vốn vì chưa có RTF đo thật"*. Tức
hôm nay ta đang bán mà không biết mình lãi hay lỗ. `test_261` đã có sẵn phép
chốt "bán >= vốn" và nó **không chạy** cho voice, chỉ vì thiếu một mục trong
`platform_core/gia_von.json`.

## Mô hình chi phí — chép đúng khuôn `hidream-o1` đã dùng

Model nhà không trả tiền nhà cung cấp, nhưng **chiếm GPU**. Nên giá vốn gồm hai
phần, và cả hai đều là **giả định có thể sai** — ghi ra để sau này sửa được:

    điện     = công suất trung bình lúc chạy x thời gian / 3.600.000 x giá điện
    khấu hao = giá card / (số năm x số ngày x số giờ mỗi ngày) x thời gian

⭐ Dùng **công suất TOÀN PHẦN lúc chạy**, không phải phần tăng thêm so với lúc
   rảnh. Bảo thủ hơn, và khớp với cách `hidream-o1` đã tính (358,65 W) nên hai
   con số so được với nhau.

⛔ ĐỪNG đo bằng một câu ngắn rồi nhân lên, và cũng đừng đo bằng một đoạn dài rồi
   nhân lên. RTF của model này **không tuyến tính**: câu ngắn khoảng 0,70 còn
   đoạn 3.000 ký tự khoảng 0,121 — gần **sáu lần**. Chi phí cố định mỗi lượt
   (nạp ngữ cảnh, CUDA graph) chia cho một câu ngắn thì thành đắt.

   Nên đo **nhiều bậc độ dài** rồi lấy bậc ĐẮT NHẤT làm giá vốn. Bán lỗ ở câu
   ngắn là lỗ thật; tính đắt ở đoạn dài chỉ là bảo thủ.

⚠️ Nó CHẠM GPU thật trên máy đang phục vụ. Đừng chạy khi có lô ảnh hay job video.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ⛔ `reconfigure`, KHÔNG bọc lại `sys.stdout` bằng một TextIOWrapper mới.
#    Bọc lại tạo một đối tượng thứ hai trên cùng một `buffer`, và hai lớp đệm
#    trên một luồng thì thứ tự dòng in ra không còn bảo đảm. `test_353` chốt
#    việc này — và nó vừa bắt tôi ba lần trong một buổi.
if hasattr(sys.stdout, "reconfigure"):
    # 🔴 `line_buffering=True` KHÔNG phải chuyện gọn gàng — nó là thứ quyết định
    #    một phép đo dài có theo dõi được hay không.
    #
    #    Khi stdout đi ra MÀN HÌNH, Python tự đệm theo dòng. Khi nó đi ra một
    #    TỆP — tức mọi lần chạy qua trình bọc PowerShell với `*> log.txt` — nó
    #    chuyển sang đệm KHỐI, và tệp log nằm im ở 0 byte suốt hàng chục phút.
    #
    # ⛔ Hệ quả không phải bất tiện: tôi mất hai lượt chờ vì không phân biệt được
    #    "đang chạy" với "đã treo", và phải đi hỏi `nvidia-smi` để biết tiến
    #    trình còn sống. Một công cụ đo mà không nói nó đang ở đâu thì mọi sự cố
    #    của nó đều trông giống nhau.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

#: Giả định giá. Đổi ở đây thì đổi luôn `ghi_chu` trong JSON sinh ra.
GIA_DIEN_VND_KWH = 3_000.0
GIA_CARD_VND = 12_000_000.0        # RTX 5060 Ti 16 GB
NAM_KHAU_HAO = 3
GIO_DUNG_MOI_NGAY = 8

#: Câu nền để dựng các bậc dài. Viết như văn xuôi thật chứ không lặp một chuỗi —
#: model đọc một chuỗi lặp nhanh hơn văn bản thật, và đó là một phép đo dối.
_CAU_NEN = ("Giọng nói nhân tạo tiếng Việt cần được đo bằng chính thứ nó sẽ đọc "
            "hằng ngày, nên đoạn này viết như một đoạn văn bình thường chứ "
            "không phải một chuỗi lặp lại. ")

BAC_NGAN = [
    ("cau_ngan", "Xin chào, đây là một câu ngắn để đo."),
    ("mot_doan", "Hôm nay tôi thử đọc một đoạn vừa phải để đo tốc độ sinh "
                 "tiếng của hệ thống. Đoạn này dài chừng hai trăm ký tự, đủ "
                 "để chi phí cố định mỗi lượt không còn chiếm phần lớn."),
]
#: Hai bậc dài dựng theo số ký tự. 1.500 là trần chất lượng mỗi lượt (Q119).
BAC_DAI = [("nam_tram", 500), ("mot_nghin_nam_tram", 1_500)]


def _dung_bac():
    ra = list(BAC_NGAN)
    for ten, can in BAC_DAI:
        s = (_CAU_NEN * (can // len(_CAU_NEN) + 2))[:can]
        ra.append((ten, s.rsplit(" ", 1)[0] + "."))
    return ra


class DoDien:
    """Lấy mẫu công suất GPU trong lúc chạy. Chạy nền, 200 ms một mẫu."""

    def __init__(self, chu_ky: float = 0.2):
        self.chu_ky = chu_ky
        self.mau: list = []
        self._chay = False
        self._t = None

    def _vong(self):
        while self._chay:
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=index,power.draw",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5)
                doc = {}
                for d in r.stdout.strip().splitlines():
                    i, w = d.split(",")
                    doc[int(i)] = float(w)
                if doc:
                    self.mau.append(doc)
            except Exception as e:               # noqa: BLE001
                # Mất một mẫu không sao; mất HẾT mẫu thì `tong_ket` trả rỗng và
                # người gọi phải xử lý nó như "không đo được", không phải "0 W".
                print(f"  [!] mau dien hong: {type(e).__name__}", file=sys.stderr)
            time.sleep(self.chu_ky)

    def __enter__(self):
        self._chay = True
        self._t = threading.Thread(target=self._vong, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a):
        self._chay = False
        if self._t is not None:
            self._t.join(timeout=3)

    def tong_ket(self) -> dict:
        if not self.mau:
            return {}
        chi = sorted(self.mau[0])
        return {i: {"tb": round(statistics.mean(m[i] for m in self.mau), 2),
                    "dinh": round(max(m[i] for m in self.mau), 2),
                    "so_mau": len(self.mau)} for i in chi}


class ThieuTruong(RuntimeError):
    """Phản hồi thiếu trường cần đo. Phép đo VỠ, không lặng lẽ thành 0."""


def _doc_dau(r) -> tuple[float, float]:
    """`(giây tiếng, giây GPU)` đọc từ ĐẦU PHẢN HỒI của chính cổng giọng.

    ⭐ `sidecar_client.noi` trả `(wav_bytes, headers)`, và cổng giọng đã tự báo
       `X-Duration-S` (dài bản tiếng) cùng `X-Gen-S` (thời gian sinh). Dùng số
       của nó thay vì tự bấm giờ ở đây: bấm giờ ngoài còn cộng cả thời gian
       truyền HTTP và giải mã WAV, tức tính chi phí GPU đắt hơn thật.

    ⛔ Thiếu trường thì NÉM, đừng trả 0. Bản đầu của tệp này đoán tên trường
       (`giay`, `seconds`, …), `.get` trả `None`, và cả bốn bậc đều ra "không
       đo được" — may là nó nói ra. Nếu tôi đã viết `or 0.0` thì nó đã báo giá
       vốn **bằng không** và mọi phép so "bán >= vốn" đều xanh.

       Cùng lớp lỗi với `$ten`/`-Ten` và `h["dang_giu"]` cùng ngày: một cái tên
       không trỏ tới ô mình tưởng, và giá trị thay thế thì **trông hợp lý**.
    """
    if not (isinstance(r, tuple) and len(r) >= 2):
        raise ThieuTruong(f"phan hoi khong phai (wav, headers): {type(r)}")
    h = r[1] or {}
    doc = {str(k).lower(): v for k, v in dict(h).items()}
    thieu = [k for k in ("x-duration-s", "x-gen-s") if not doc.get(k)]
    if thieu:
        raise ThieuTruong(f"dau phan hoi thieu {thieu}; co: {sorted(doc)}")
    return float(doc["x-duration-s"]), float(doc["x-gen-s"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--luot", type=int, default=3, help="So luot moi bac.")
    ap.add_argument("--json", default="tmp/gia_von_voice.json")
    a = ap.parse_args(argv)

    from apps.ltt_voice import sidecar_client

    if not sidecar_client.san_sang():
        print("Cong giong CHUA san sang.", file=sys.stderr)
        return 2

    print("Do cong suat luc RANH (10 giay)...")
    with DoDien() as d0:
        time.sleep(10)
    ranh = d0.tong_ket()
    if not ranh:
        print("KHONG doc duoc cong suat GPU — khong ket luan duoc gia von.",
              file=sys.stderr)
        return 2
    for i, v in ranh.items():
        print(f"  GPU{i}: tb {v['tb']} W")

    ket = {}
    for ten, cau in _dung_bac():
        print(f"\n[{ten}] {len(cau)} ky tu")
        luot = []
        with DoDien() as dd:
            for k in range(a.luot):
                t0 = time.time()
                r = sidecar_client.noi(cau)
                cho = time.time() - t0
                tieng, sinh = _doc_dau(r)      # ném nếu thiếu — xem `_doc_dau`
                luot.append({"cho_s": round(cho, 3), "tieng_s": round(tieng, 3),
                             "sinh_s": round(sinh, 3),
                             "rtf": round(sinh / tieng, 4)})
                print(f"  luot {k + 1}: sinh {sinh:.2f}s -> tieng {tieng:.2f}s "
                      f"(RTF {sinh / tieng:.3f}, cho ca HTTP {cho:.2f}s)")
        if not luot:
            print(f"  [!] bac {ten} khong co luot nao dung — BO", file=sys.stderr)
            continue
        dien = dd.tong_ket()
        if not dien:
            print(f"  [!] bac {ten} khong do duoc dien — BO", file=sys.stderr)
            continue
        # GPU nào NHÚC NHÍCH nhiều nhất so với lúc rảnh chính là GPU đang chạy.
        # Đo chênh chứ không lấy GPU to nhất: card kia có thể đang bận việc khác.
        gpu = max(dien, key=lambda i: dien[i]["tb"] - ranh.get(i, {}).get("tb", 0.0))
        w = dien[gpu]["tb"]
        rtf = statistics.mean(x["rtf"] for x in luot)

        # Một GIÂY TIẾNG tốn `rtf` giây GPU.
        vnd_dien = w * rtf / 3_600_000.0 * GIA_DIEN_VND_KWH
        vnd_kh = (GIA_CARD_VND
                  / (NAM_KHAU_HAO * 365 * GIO_DUNG_MOI_NGAY * 3600)) * rtf
        ket[ten] = {
            "so_ky_tu": len(cau), "so_luot": len(luot),
            "rtf": round(rtf, 4), "gpu": gpu,
            "cong_suat_tb_W": round(w, 2),
            "vnd_moi_giay_tieng": round(vnd_dien + vnd_kh, 4),
            "mcredit_moi_giay_tieng": round((vnd_dien + vnd_kh) * 10, 2),
            "chi_tiet": {"dien_vnd": round(vnd_dien, 4),
                         "khau_hao_vnd": round(vnd_kh, 4)},
            "luot": luot,
        }
        print(f"  RTF tb {rtf:.4f} · GPU{gpu} {w:.1f} W -> "
              f"{ket[ten]['mcredit_moi_giay_tieng']} mcredit/giay tieng")

    if not ket:
        print("KHONG BAC NAO DO DUOC.", file=sys.stderr)
        return 1

    dat = max(ket, key=lambda k: ket[k]["mcredit_moi_giay_tieng"])
    ra = {"ranh_W": ranh, "bac": ket, "bac_dat_nhat": dat,
          "mcredit_moi_giay_tieng": ket[dat]["mcredit_moi_giay_tieng"],
          "gia_dinh": {"gia_dien_vnd_kwh": GIA_DIEN_VND_KWH,
                       "gia_card_vnd": GIA_CARD_VND,
                       "nam_khau_hao": NAM_KHAU_HAO,
                       "gio_dung_moi_ngay": GIO_DUNG_MOI_NGAY}}
    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as f:
        json.dump(ra, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 64)
    print(f"  GIA VON: bac dat nhat la `{dat}` -> "
          f"{ra['mcredit_moi_giay_tieng']} mcredit/giay tieng")
    print("  Dang ban: 200 mcredit/giay tieng")
    print(f"  Da ghi: {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
