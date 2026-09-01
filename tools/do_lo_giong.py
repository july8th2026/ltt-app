r"""
do_lo_giong.py — gộp lô có THẬT SỰ nhanh hơn gọi lần lượt không?

    powershell -ExecutionPolicy Bypass -File .\setup\do_lo_giong.ps1

## Câu hỏi

`voice_sidecar/engine.noi_lo` dùng `infer_batch` và trích README của upstream:
*"The GPU win comes from batching"*. Cửa `/v1/batch` đã có, đã chạy, và **không
app nào gọi nó** — màn Chạy lô và màn Dự án nộp **một job cho mỗi dòng**.

Trước khi đổi kiến trúc, phải biết cái giá hiện tại. Số đo 01/09 nói GPU đang
**rảnh phần lớn thời gian** trong một lượt sinh: 29–39 W trên 180 W, 641 MB trên
16.311 MB. Nhưng "GPU trông có vẻ rảnh" **không phải** bằng chứng rằng gộp lô sẽ
nhanh hơn — công suất thấp cũng có thể vì model bị chặn ở một chỗ mà thêm việc
song song không gỡ được.

⇒ Nên đo, đừng suy.

## Cách đo — cùng N đoạn, hai đường

    A. lần lượt : N lần `/v1/speech`, mỗi lần một đoạn
    B. gộp lô   : 1 lần `/v1/batch`, cả N đoạn

So bằng **thông lượng**: *giây tiếng sinh ra trên mỗi giây GPU*. Không so bằng
tổng thời gian, vì hai đường có thể sinh ra tổng thời lượng tiếng khác nhau vài
phần trăm (model có ngẫu nhiên) và khi đó tổng thời gian không so được.

⛔ MỘT LƯỢT KHÔNG PHẢI MỘT KẾT LUẬN. Chạy nhiều vòng và báo cả độ lệch — nếu
   chênh giữa hai đường nhỏ hơn dao động giữa hai vòng của **cùng một** đường
   thì phép đo chưa nói được gì. Đúng bài học G4 ở `docs/ANH_NOI_BO/`.

⚠️ Nó chạm GPU thật trên máy đang phục vụ, nhưng **không chạm sổ tiền** — nó gọi
   thẳng cổng giọng, không qua hàng đợi job.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
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

#: Mười đoạn như một bài đọc thật: dài ngắn khác nhau, nội dung khác nhau.
#: ⛔ Đừng dùng cùng một câu lặp N lần — cache và cách chia chunk của model đều
#:    có thể ăn gian trên dữ liệu lặp, và con số ra sẽ đẹp một cách vô nghĩa.
DOAN = [
    "Chào bạn, đây là đoạn mở đầu của một bài đọc thử.",
    "Hôm nay chúng ta sẽ nói về cách một hệ thống sinh tiếng nói làm việc.",
    "Trước hết, văn bản được tách thành từng đoạn ngắn vừa phải.",
    "Mỗi đoạn được đưa qua model, và model trả về một đoạn sóng âm.",
    "Các đoạn sóng ấy sau đó được ghép lại thành một bản đọc liền mạch.",
    "Điều khó nhất không nằm ở việc sinh tiếng, mà ở chỗ giữ cho giọng đều.",
    "Nếu mỗi đoạn được sinh độc lập, tông giọng có thể trôi dần qua từng đoạn.",
    "Vì vậy hệ thống dùng chung một đoạn tham chiếu cho toàn bộ bài đọc.",
    "Cuối cùng, phần im lặng ở mối nối được đo và cân lại cho tự nhiên.",
    "Đó là toàn bộ câu chuyện, cảm ơn bạn đã lắng nghe tới đây.",
]


class ThieuTruong(RuntimeError):
    """Phản hồi thiếu trường cần đo. Phép đo VỠ, không lặng lẽ thành 0."""


def _dau(r) -> tuple[float, float]:
    """`(giây tiếng, giây sinh)` từ đầu phản hồi nhị phân của cổng giọng."""
    if not (isinstance(r, tuple) and len(r) >= 2):
        raise ThieuTruong(f"phan hoi khong phai (wav, headers): {type(r)}")
    doc = {str(k).lower(): v for k, v in dict(r[1] or {}).items()}
    thieu = [k for k in ("x-duration-s", "x-gen-s") if not doc.get(k)]
    if thieu:
        raise ThieuTruong(f"dau phan hoi thieu {thieu}; co: {sorted(doc)}")
    return float(doc["x-duration-s"]), float(doc["x-gen-s"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-doan", type=int, default=6)
    ap.add_argument("--vong", type=int, default=3,
                    help="So vong moi duong. Mot vong khong phai mot ket luan.")
    ap.add_argument("--json", default="tmp/lo_giong.json")
    a = ap.parse_args(argv)

    from apps.ltt_voice import sidecar_client

    if not sidecar_client.san_sang():
        print("Cong giong CHUA san sang.", file=sys.stderr)
        return 2

    doan = (DOAN * (a.so_doan // len(DOAN) + 1))[:a.so_doan]
    print(f"{len(doan)} doan, {a.vong} vong moi duong\n")

    # Một lượt làm ấm. Lượt đầu tiên sau khi nạp model bao giờ cũng chậm hơn, và
    # tính nó vào đường nào thì đường ấy thua oan.
    sidecar_client.noi(doan[0])

    ket = {"lan_luot": [], "gop_lo": []}

    for v in range(a.vong):
        # ---- A. lần lượt ----------------------------------------------------
        tieng = sinh = 0.0
        t0 = time.time()
        for d in doan:
            t, g = _dau(sidecar_client.noi(d))
            tieng += t
            sinh += g
        tuong = time.time() - t0
        ket["lan_luot"].append({"tieng_s": round(tieng, 3),
                                "sinh_s": round(sinh, 3),
                                "tuong_s": round(tuong, 3),
                                "thong_luong": round(tieng / sinh, 4)})
        print(f"  vong {v + 1} lan luot: {tieng:.1f}s tieng / {sinh:.1f}s sinh "
              f"= {tieng / sinh:.3f}x")

        # ---- B. gộp lô ------------------------------------------------------
        t0 = time.time()
        d = sidecar_client.noi_lo(list(doan))
        tuong = time.time() - t0
        muc = d.get("items") or []
        tieng = sum(float(m.get("duration_s") or 0.0) for m in muc)
        sinh = float(d.get("gen_s") or 0.0)
        if not muc or tieng <= 0 or sinh <= 0:
            raise ThieuTruong(f"/v1/batch tra thieu so: items={len(muc)} "
                              f"tieng={tieng} gen_s={sinh}")
        if len(muc) != len(doan):
            raise ThieuTruong(f"/v1/batch tra {len(muc)} muc cho {len(doan)} doan")
        ket["gop_lo"].append({"tieng_s": round(tieng, 3),
                              "sinh_s": round(sinh, 3),
                              "tuong_s": round(tuong, 3),
                              "thong_luong": round(tieng / sinh, 4)})
        print(f"  vong {v + 1} gop lo  : {tieng:.1f}s tieng / {sinh:.1f}s sinh "
              f"= {tieng / sinh:.3f}x")

    def tb(k):
        return statistics.mean(x["thong_luong"] for x in ket[k])

    def lech(k):
        v = [x["thong_luong"] for x in ket[k]]
        return statistics.pstdev(v) if len(v) > 1 else 0.0

    A, B = tb("lan_luot"), tb("gop_lo")
    dao = max(lech("lan_luot"), lech("gop_lo"))
    nhanh = B / A if A else 0.0

    print("\n" + "=" * 66)
    print("  THONG LUONG — giay tieng tren moi giay GPU (cao hon la tot hon)")
    print("=" * 66)
    print(f"  A · lan luot : {A:.3f}x  (lech {lech('lan_luot'):.3f})")
    print(f"  B · gop lo   : {B:.3f}x  (lech {lech('gop_lo'):.3f})")
    print(f"  B / A        : {nhanh:.2f} lan")
    print(f"  dao dong     : {dao:.3f}")
    print()
    if abs(B - A) <= dao:
        print("  ⚠️ CHENH NHO HON DAO DONG TRONG MOT DUONG — chua ket luan duoc.")
        print("     Chay them vong, hoac chap nhan rang gop lo khong do duoc o")
        print("     kich thuoc nay. Dung doc mot dau cong nho thanh mot chien thang.")
    elif B > A:
        print(f"  ⇒ Gop lo NHANH HON {nhanh:.2f} lan, va khoang cach lon hon dao dong.")
    else:
        print("  🔴 Gop lo CHAM HON. Dung doi kien truc sang no.")

    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as f:
        json.dump({"so_doan": len(doan), "vong": a.vong, "chi_tiet": ket,
                   "thong_luong_lan_luot": round(A, 4),
                   "thong_luong_gop_lo": round(B, 4),
                   "nhanh_hon": round(nhanh, 3),
                   "dao_dong": round(dao, 4)}, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
