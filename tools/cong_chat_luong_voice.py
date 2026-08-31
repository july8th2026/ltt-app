r"""
cong_chat_luong_voice.py — V10 · CỔNG chất lượng, không phải một bản báo cáo.

    powershell -File .\setup\cong_chat_luong_voice.ps1 -Ghim    # dung baseline
    powershell -File .\setup\cong_chat_luong_voice.ps1          # chay cong

## Vì sao cần một cổng chứ không phải thêm số đo

`voice_sidecar/do_chat_luong.py` đã đo gần đủ mọi thứ V10 cần. Nhưng `phan_quyet`
của nó tự khai một giới hạn thẳng thắn:

    "Phan quyet nay CHI phu cac muc co nguong co nguon. CER, tuong dong nguoi
     noi va troi giong duoc BAO SO va danh dau `chua_hieu_chuan` — chung khong
     tham gia ket luan."

Tức ba phép đo quan trọng nhất về **chất lượng nghe được** đang chỉ in ra màn
hình. Không có gì đỏ khi chúng tụt. Đổi `tham_so.py` — `temperature`, `top_k`,
số bước — thì mọi con số ấy đổi theo, và **không ai biết là đã đổi theo hướng
nào**.

⭐ Vấn đề của chúng không phải "chưa ai đặt ngưỡng". Là **không có ngưỡng tuyệt
   đối nào để đặt**: CER 4% là tốt hay tệ phụ thuộc bộ câu, giọng, và cả bộ ASR.
   Con số duy nhất có nghĩa là **so với chính hệ thống này hôm qua**.

⇒ Nên cổng này so với một **baseline ghim theo phiên bản**, không so với một
   hằng số gõ tay.

## ⛔ DUNG SAI LẤY TỪ SỐ ĐO, KHÔNG GÕ TAY

Sinh tiếng có ngẫu nhiên. Chạy cùng một câu hai lần cho hai CER khác nhau. Nên
`--ghim` chạy corpus **nhiều vòng** và lấy độ lệch làm dung sai:

    ngưỡng = trung bình ± HE_SO_DUNG_SAI × độ lệch     (có sàn tối thiểu)

Gõ tay một dung sai là chọn giữa hai cái sai: rộng quá thì cổng không bắt được
gì, hẹp quá thì nó đỏ vì nhiễu và **sẽ bị tắt trong một tuần** — kéo theo cả
những mục nó bảo vệ đúng.

## 🔴 FAIL-CLOSED THEO PHIÊN BẢN

Baseline khoá theo `(PHIEN_BAN_THAM_SO, phien_ban_bo_do)`. Đổi một trong hai thì
**không có baseline** cho cấu hình mới, và cổng **từ chối** thay vì lấy đại
baseline cũ.

Đó chính là điều kiện V10 đòi: *"đổi `tham_so.py` cũng phải qua cổng này"* và
*"v3 full không được lên chỉ vì nghe hay hơn"*. Một cấu hình mới phải **đo lại**
để có baseline, và lúc đo lại thì mọi con số đều nằm trên bàn.

⚠️ Chạm GPU thật, không chạm sổ tiền (gọi thẳng cổng giọng).
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
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TEP_BASELINE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "voice_sidecar", "baseline_chat_luong.json")

#: Số lần độ lệch dùng làm dung sai. 3σ ≈ 99,7% nếu phân bố chuẩn — đủ rộng để
#: nhiễu bình thường không làm đỏ, đủ hẹp để một cú tụt thật thì thấy.
HE_SO_DUNG_SAI = 3.0

#: Sàn dung sai cho từng phép đo. Cần vì một chỉ số **rất ổn định** sẽ cho độ
#: lệch gần 0, và khi đó `3σ` thành một cửa hẹp tới mức vô lý.
SAN_DUNG_SAI = {
    "cer": 0.02,              # 2 điểm phần trăm
    "wer": 0.03,
    "on_dinh_giong": 0.02,
    "rtf": 0.05,
}

#: Corpus cố định. ⛔ ĐỔI CORPUS LÀ ĐỔI PHÉP ĐO — baseline cũ không còn so được,
#: nên corpus phải nằm trong khoá phiên bản (xem `_khoa`).
#:
#: 🔴 MỖI CÂU PHẢI DÀI HƠN 6 GIÂY KHI ĐỌC RA. `do_troi_giong` cắt cửa sổ 3
#:    giây và cần ít nhất hai cửa sổ; ngắn hơn thì nó trả `{co: False}` và
#:    **phép đo trôi giọng lặng lẽ vắng mặt khỏi baseline**.
#:
#:    Lô ghim đầu tiên (01/09) dính đúng thế: corpus 8 câu ngắn, và cổng
#:    dựng lên thiếu hẳn chỉ số quan trọng nhất mà **không có gì báo** —
#:    nó chỉ đơn giản không có trong bảng. Một cổng thiếu một mục thì vẫn
#:    in ra `CONG XANH`.
CORPUS = [
    "Hôm nay trời nắng đẹp nên tôi đi bộ ra công viên gần nhà, ngồi ở cái ghế "
    "quen thuộc dưới gốc cây và đọc nốt mấy trang sách còn dở từ tuần trước.",
    "Chị ấy nói rằng cuộc họp sẽ bắt đầu lúc chín giờ ba mươi sáng mai, và đề "
    "nghị mọi người đọc trước bản tóm tắt đã gửi qua thư điện tử chiều qua.",
    "Giá vé vào cửa là hai trăm bốn mươi lăm nghìn đồng cho một người lớn, trẻ "
    "em dưới sáu tuổi được miễn phí, còn nhóm từ mười người trở lên giảm hai "
    "mươi phần trăm.",
    "Nghĩa là chúng ta phải hoàn thành toàn bộ phần thiết kế trước ngày mười "
    "lăm tháng chín, sau đó còn hai tuần nữa để sửa những chỗ khách hàng góp ý.",
    "Anh Tuấn vừa chuyển tới sống ở quận Bảy được khoảng ba tháng, anh nói khu "
    "đó yên tĩnh hơn chỗ cũ nhiều nhưng đi làm thì xa hơn chừng bốn cây số.",
    "Món này ăn kèm với rau sống và nước chấm pha hơi ngọt một chút, nếu thích "
    "cay thì thêm vài lát ớt tươi, còn không thì để nguyên cũng đã rất vừa miệng.",
]


class KhongDoDuoc(RuntimeError):
    """Không đo được thì VỠ. Một phép đo thiếu không được thành một con số."""


def _khoa() -> dict:
    """Khoá phiên bản của baseline. Đổi bất cứ phần nào ⇒ baseline cũ hết hiệu lực."""
    import hashlib

    from voice_sidecar import do_chat_luong, tham_so

    bam = hashlib.sha256(chr(10).join(CORPUS).encode()).hexdigest()[:16]
    return {
        "phien_ban_tham_so": tham_so.PHIEN_BAN_THAM_SO,
        "phien_ban_bo_do": do_chat_luong.do_tat_ca.__globals__.get(
            "_PHIEN_BAN_BO_DO", "ltt-voice-do-2026-08-31a"),
        "bam_corpus": bam,
        "so_cau": len(CORPUS),
    }


def _do_mot_vong(giu_tep: bool = False) -> dict:
    """Sinh cả corpus rồi đo. Trả `{ten_do: [gia tri tung cau]}`."""
    from apps.ltt_voice import sidecar_client
    from voice_sidecar import do_chat_luong

    ra = {k: [] for k in ("cer", "wer", "on_dinh_giong", "rtf")}
    hong = 0
    for cau in CORPUS:
        try:
            raw, dau = sidecar_client.noi(cau)
        except Exception as e:                       # noqa: BLE001
            # Một câu hỏng là một SỐ ĐO (tỉ lệ hỏng), không phải một lý do dừng.
            print(f"  [hong] {type(e).__name__}: {e}")
            hong += 1
            continue
        doc = {str(k).lower(): v for k, v in dict(dau or {}).items()}
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        try:
            tmp.write(raw)
            tmp.close()
            kq = do_chat_luong.do_tat_ca(tmp.name, text=cau)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

        dh = kq.get("de_hieu") or {}
        if dh.get("co") and dh.get("cer") is not None:
            ra["cer"].append(float(dh["cer"]))
        if dh.get("co") and dh.get("wer") is not None:
            ra["wer"].append(float(dh["wer"]))
        # ⭐ `do_troi_giong` trả `cosine_trung_binh` — độ GIỐNG giữa các cửa sổ
        #    trong cùng một bản. CAO là ổn định, THẤP là trôi. Nên nó vào bảng
        #    dưới tên `on_dinh_giong` với chiều `+1`, không phải "trôi" chiều −1.
        #
        # ⛔ Đặt sai chiều thì cổng xanh đúng lúc chất lượng tụt, và đỏ đúng lúc
        #    nó tốt lên. Đây là chỗ một cái tên gần đúng gây hại nhiều nhất.
        tr = (kq.get("troi_giong") or {}).get("cosine_trung_binh")
        if tr is not None:
            ra["on_dinh_giong"].append(float(tr))
        # ⛔ KHÔNG đưa `lufs` và `true_peak_dbtp` vào cổng tương đối này.
        #    Chúng đã có ngưỡng TUYỆT ĐỐI CÓ NGUỒN (EBU R128 / BS.1770-4) và
        #    `do_chat_luong.phan_quyet` đã chốt. Một dải dung sai quanh trung
        #    bình có thể **nới lỏng** một bảo đảm tuyệt đối: lô ghim đầu tiên
        #    cho `true_peak` trần +0,0479 dBTP, tức cổng sẽ cho qua một bản
        #    VỠ TIẾNG trong khi hợp đồng nói trần là −1,0.
        if doc.get("x-rtf"):
            ra["rtf"].append(float(doc["x-rtf"]))

    ra["_ty_le_hong"] = [hong / float(len(CORPUS))]
    return ra


def _gom(vong: list) -> dict:
    """Gộp nhiều vòng thành `{ten: {tb, lech, n}}`.

    🔴 ĐỘ LỆCH LẤY GIỮA CÁC VÒNG, KHÔNG GỘP MỌI CÂU LẠI RỒI TÍNH.

       Bản đầu gộp mọi giá trị của mọi câu ở mọi vòng thành một đống rồi lấy độ
       lệch của đống ấy. Nó trộn **hai nguồn biến thiên khác hẳn nhau**:

         · giữa CÂU  — câu có số, câu có tên riêng thì CER cao hơn hẳn. Đây là
                       một khác biệt **hệ thống và luôn có mặt**, không phải
                       nhiễu, và nó KHÔNG lặp lại khác đi ở lượt sau.
         · giữa VÒNG — cùng câu, chạy lại cho kết quả khác. Đây mới là nhiễu,
                       và là thứ duy nhất cổng cần bỏ qua.

       Hệ quả đo được (lô ghim 01/09): CER trung bình 0,148 với "độ lệch" 0,134
       ⇒ dung sai `3σ` cho trần **0,549**. Một cổng cho phép CER 55% không chặn
       được bất cứ điều gì — nó chỉ trông như một cổng.

    ⭐ Đúng đơn vị: cổng chạy MỘT vòng rồi so **trung bình corpus của vòng đó**.
       Nên baseline phải là trung bình của các trung-bình-vòng, và độ lệch phải
       là độ lệch GIỮA các trung-bình-vòng. Cùng đại lượng, cùng thang.
    """
    ten = sorted({k for v in vong for k in v})
    ra = {}
    for k in ten:
        # Trung bình corpus của TỪNG vòng — đúng đại lượng mà cổng sẽ tính.
        tb_vong = [statistics.mean(v[k]) for v in vong if v.get(k)]
        if not tb_vong:
            continue
        ra[k] = {
            "tb": round(statistics.mean(tb_vong), 4),
            "lech": (round(statistics.pstdev(tb_vong), 4)
                     if len(tb_vong) > 1 else 0.0),
            "so_vong": len(tb_vong),
            "n": sum(len(v.get(k, ())) for v in vong),
            # Giữ lại để người đọc thấy hai nguồn biến thiên là hai thứ khác
            # nhau, và thấy cái nào lớn hơn.
            "lech_giua_cau": round(statistics.pstdev(
                [x for v in vong for x in v.get(k, ())]), 4)
            if sum(len(v.get(k, ())) for v in vong) > 1 else 0.0,
        }
    return ra


#: Chiều "xấu đi" của từng phép đo. `-1` = nhỏ hơn là tốt hơn.
CHIEU = {"cer": -1, "wer": -1, "rtf": -1,
         "on_dinh_giong": +1, "_ty_le_hong": -1}


def _nguong(ten: str, tb: float, lech: float) -> tuple:
    """`(thấp, cao)` cho một phép đo. `None` ở một đầu = không chặn đầu đó."""
    dung = max(HE_SO_DUNG_SAI * lech, SAN_DUNG_SAI.get(ten, 0.05))
    chieu = CHIEU.get(ten, 0)
    if chieu < 0:                       # nhỏ hơn là tốt ⇒ chỉ chặn phía TRÊN
        return None, round(tb + dung, 4)
    if chieu > 0:                       # lớn hơn là tốt ⇒ chỉ chặn phía DƯỚI
        return round(tb - dung, 4), None
    return round(tb - dung, 4), round(tb + dung, 4)   # lệch phía nào cũng xấu


def ghim(vong: int) -> dict:
    print(f"Dung baseline: {vong} vong x {len(CORPUS)} cau\n")
    cac = []
    for i in range(vong):
        print(f"[vong {i + 1}/{vong}]")
        cac.append(_do_mot_vong())
    gom = _gom(cac)
    bl = {"khoa": _khoa(), "so_vong": vong, "do": {}}
    for k, v in gom.items():
        thap, cao = _nguong(k, v["tb"], v["lech"])
        bl["do"][k] = {**v, "thap": thap, "cao": cao}
        print(f"  {k:16} tb {v['tb']:>9.4f}  lech {v['lech']:>7.4f}  "
              f"-> [{thap}, {cao}]")
    return bl


def chay_cong() -> int:
    if not os.path.isfile(TEP_BASELINE):
        print(f"KHONG CO BASELINE ({TEP_BASELINE}). Chay `--ghim` truoc.",
              file=sys.stderr)
        return 2
    with open(TEP_BASELINE, encoding="utf-8") as f:
        bl = json.load(f)

    # 🔴 FAIL-CLOSED. Khoá lệch ⇒ TỪ CHỐI, không lấy đại baseline cũ.
    khoa_nay = _khoa()
    lech = {k: (bl["khoa"].get(k), v) for k, v in khoa_nay.items()
            if bl["khoa"].get(k) != v}
    if lech:
        print("BASELINE KHONG DUNG CHO CAU HINH NAY:", file=sys.stderr)
        for k, (cu, moi) in lech.items():
            print(f"  {k}: baseline={cu!r}  hien tai={moi!r}", file=sys.stderr)
        print("\nDoi tham so / bo do / corpus la doi PHEP DO. Chay `--ghim` de\n"
              "do lai — do dung la cong ma V10 doi: mot cau hinh moi phai dat\n"
              "moi con so len ban, khong duoc muon ket qua cua cau hinh cu.",
              file=sys.stderr)
        return 2

    print("Chay cong (1 vong)\n")
    gom = _gom([_do_mot_vong()])

    xau, thieu = [], []
    for k, muc in bl["do"].items():
        if k not in gom:
            thieu.append(k)
            continue
        tb = gom[k]["tb"]
        thap, cao = muc.get("thap"), muc.get("cao")
        ok = ((thap is None or tb >= thap) and (cao is None or tb <= cao))
        dau = "ok  " if ok else "XAU "
        print(f"  [{dau}] {k:16} {tb:>9.4f}   baseline {muc['tb']:>9.4f} "
              f"[{thap}, {cao}]")
        if not ok:
            xau.append(f"{k}: {tb} ngoai [{thap}, {cao}] "
                       f"(baseline {muc['tb']})")

    print("\n" + "=" * 70)
    if thieu:
        # ⛔ Thiếu một phép đo KHÔNG được đọc thành "đạt". Bộ ASR chết là mất
        #    CER, và mất CER trong im lặng nghĩa là cổng còn xanh trong khi thứ
        #    quan trọng nhất không được kiểm.
        print(f"  🔴 THIEU {len(thieu)} phep do: {thieu}")
        print("     Khong ket luan duoc. Xem bo ASR / bo ma hoa giong.")
        return 2
    if xau:
        print(f"  🔴 CONG DO — {len(xau)} phep do tut khoi baseline:")
        for d in xau:
            print(f"     {d}")
        return 1
    print(f"  ✅ CONG XANH — {len(bl['do'])} phep do deu trong dung sai.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ghim", action="store_true",
                    help="Do lai va GHI baseline moi cho cau hinh hien tai.")
    ap.add_argument("--vong", type=int, default=3,
                    help="So vong khi ghim. Mot vong khong do duoc do lech.")
    a = ap.parse_args(argv)

    from apps.ltt_voice import sidecar_client
    if not sidecar_client.san_sang():
        print("Cong giong CHUA san sang.", file=sys.stderr)
        return 2

    if not a.ghim:
        return chay_cong()

    if a.vong < 2:
        print("`--ghim` can it nhat 2 vong: mot vong khong do duoc DO LECH, va "
              "khong co do lech thi dung sai phai go tay.", file=sys.stderr)
        return 2
    bl = ghim(a.vong)
    with open(TEP_BASELINE, "w", encoding="utf-8", newline="\n") as f:
        json.dump(bl, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nDa ghi baseline: {TEP_BASELINE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
