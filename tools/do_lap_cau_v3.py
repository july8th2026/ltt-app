r"""
do_lap_cau_v3.py — v3 Turbo CÒN lặp câu như upstream #159 không?

    powershell -ExecutionPolicy Bypass -File .\setup\do_lap_cau_v3.ps1

## Vì sao phép đo này quyết định số phận của cả pha K1

`pnnbao97/VieNeu-TTS` **#159** báo đúng lỗi mà K1 định chặn, kèm chữ ký số liệu
hiếm khi có được:

    input : "Người ta thường nói,"
    ra    : "Người ta thường nói, Người ta thường nói,"
    7 lượt: 2,70 · 2,68 · 1,30 · 2,64 · 2,54 · 1,30 · 2,68 giây
            (~1,30 s là ĐÚNG, ~2,6 s là bản lặp đôi ⇒ 5/7 lượt hỏng)

⭐ Nhưng issue ấy nói về checkpoint **0.3B-ngoc-huyen**, và tác giả trả lời rõ:
   *"phiên bản này đã khá cũ… team sẽ không hotfix… v3 sẽ giải quyết triệt để
   bài toán lặp câu và chèn từ lạ nhờ kiến trúc alignment và decoding ổn định
   hơn"* — rồi đóng issue vào milestone v3.

   **Ta chạy v3 Turbo.** Nên câu hỏi không còn là "chặn lặp thế nào" mà là
   **"lỗi ấy còn không"**.

⛔ Và đây là chỗ dễ làm sai nhất: mang một chốt sang vì *hệ cũ có nó* là mang
   theo cả một giả định về engine đã đổi. Nếu v3 không lặp nữa thì chốt lặp là
   bảo hiểm, không phải bản vá — và nói nó là bản vá cho một lỗi đang sống là
   nói sai với chính mình.

## Cách đo

Chạy **đúng câu của #159**, N lượt, ghi phân bố thời lượng. Rồi thêm hai câu
ngắn khác để biết đây là chuyện của câu ấy hay của mọi câu ngắn.

Dấu hiệu lặp đôi rất rõ trong số liệu: phân bố **hai cụm**, cụm trên gần gấp đôi
cụm dưới. Một phân bố **một cụm** hẹp nghĩa là không lặp.

⚠️ Chạm GPU thật, không chạm sổ tiền.
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

#: Câu của chính issue #159, giữ nguyên từng ký tự kể cả dấu phẩy cuối.
CAU_159 = "Người ta thường nói,"

#: Hai câu ngắn khác, để phân biệt "lỗi của câu này" với "lỗi của câu ngắn".
CAU_KHAC = ["Xin chào các bạn,", "Hôm nay trời đẹp."]


def _cum(gia: list) -> dict:
    """Phân bố này một cụm hay hai cụm?

    Cách chia đơn giản và đủ cho câu hỏi đang hỏi: lấy trung điểm giữa nhỏ nhất
    và lớn nhất, đếm hai bên. Lặp đôi cho hai cụm cách nhau gần gấp đôi; nhiễu
    bình thường cho một cụm và bên kia rỗng.
    """
    if len(gia) < 3:
        return {}
    lo, hi = min(gia), max(gia)
    giua = (lo + hi) / 2
    duoi = [g for g in gia if g <= giua]
    tren = [g for g in gia if g > giua]
    ra = {"nho_nhat": round(lo, 3), "lon_nhat": round(hi, 3),
          "so_duoi": len(duoi), "so_tren": len(tren),
          "ti_le_hi_lo": round(hi / lo, 3) if lo else None}
    if duoi and tren:
        ra["ti_le_hai_cum"] = round(statistics.mean(tren) / statistics.mean(duoi), 3)
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--luot", type=int, default=20)
    ap.add_argument("--ra", default="tmp/lap_cau_v3.json")
    a = ap.parse_args(argv)

    try:
        import soundfile as sf  # noqa: F401
    except ImportError:
        print("THIEU soundfile — chay bang python cua `vieneu-venv`.",
              file=sys.stderr)
        return 2

    from apps.ltt_voice import sidecar_client

    if not sidecar_client.san_sang():
        print("Cong giong CHUA san sang.", file=sys.stderr)
        return 2

    sidecar_client.noi("Lam am.")
    ket = {}
    for ten, cau in [("issue_159", CAU_159)] + [
            (f"khac_{i + 1}", c) for i, c in enumerate(CAU_KHAC)]:
        print(f'\n[{ten}] "{cau}"  ({len(cau)} ky tu)')
        giay = []
        for i in range(a.luot):
            raw, dau = sidecar_client.noi(cau)
            doc = {str(k).lower(): v for k, v in dict(dau or {}).items()}
            d = doc.get("x-duration-s")
            if not d:
                print("  [!] dau phan hoi thieu x-duration-s", file=sys.stderr)
                return 2
            giay.append(float(d))
            print(f"  {i + 1:2}: {float(d):.3f}s", end="\n" if (i + 1) % 5 == 0 else "  ")
        if a.luot % 5:
            print()
        c = _cum(giay)
        ket[ten] = {"cau": cau, "so_ky_tu": len(cau), "giay": giay,
                    "trung_binh": round(statistics.mean(giay), 3),
                    "do_lech": round(statistics.pstdev(giay), 4),
                    "cum": c}
        print(f"  tb {statistics.mean(giay):.3f}s  lech "
              f"{statistics.pstdev(giay):.4f}  "
              f"nho nhat {min(giay):.3f}  lon nhat {max(giay):.3f}")

    print("\n" + "=" * 72)
    print("  V3 TURBO CO CON LAP CAU NHU #159 KHONG")
    print("=" * 72)
    print("  Chu ky cua loi: phan bo HAI CUM, cum tren gan gap doi cum duoi.")
    print("  (#159 tren 0.3B-ngoc-huyen: 1,30s va ~2,6s, 5/7 luot hong)\n")
    co_lap = False
    for ten, m in ket.items():
        c = m["cum"]
        hai_cum = bool(c.get("so_duoi") and c.get("so_tren")
                       and (c.get("ti_le_hai_cum") or 0) > 1.6)
        co_lap = co_lap or hai_cum
        print(f"  {ten:10} tb {m['trung_binh']:6.3f}s  lech {m['do_lech']:.4f}  "
              f"lon/nho {c.get('ti_le_hi_lo')}  "
              f"{'🔴 HAI CUM — CO LAP' if hai_cum else 'mot cum'}")
    print()
    if co_lap:
        print("  🔴 V3 TURBO VAN LAP. Chot K1 la mot BAN VA cho loi dang song.")
        print("     Ghi lai chu ky nay vao test lam ca tai hien.")
    else:
        print("  ✅ KHONG THAY LAP. Tac gia upstream noi dung: v3 da sua.")
        print("     ⇒ Chot K1 la BAO HIEM, khong phai ban va. Van nen co —")
        print("       mot model tu hoi quy khong bao gio het kha nang ket —")
        print("       nhung dung xep no uu tien nhu mot loi dang chay.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"nguon": "github.com/pnnbao97/VieNeu-TTS issue #159",
                   "ket_qua": ket, "co_lap": co_lap}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
