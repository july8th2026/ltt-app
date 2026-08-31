r"""
do_troi_tong.py — giọng có TRÔI TÔNG qua các đoạn của một bài dài không?

    powershell -ExecutionPolicy Bypass -File .\setup\do_troi_tong.ps1

## Câu hỏi, và vì sao nó là một chốt của V9

Một bài dài không sinh được trong một lượt: nó bị chia thành nhiều đoạn, mỗi
đoạn là một lượt `infer` riêng. Upstream **#173** báo rằng khi làm vậy, tông
giọng có thể **trôi dần** qua từng đoạn — người nghe thấy một giọng "đổi người"
ở giữa bài, dù mọi đoạn đều dùng chung một đoạn tham chiếu.

`docs/LTT_VOICE/00_PHUONG_AN_VA_LO_TRINH.md` đặt nó thành điều kiện qua V9:
*"đã đo trôi tông (#173) và độ dài công bố lấy từ số đo"*. Tệp này là phép đo đó.

## Cách đo

F0 (tần số cơ bản) là thứ đo được của "tông giọng". Với mỗi đoạn, lấy **trung vị
F0 của các khung có tiếng** — trung vị chứ không phải trung bình, vì F0 của khung
không có tiếng là rác và một khung rác kéo trung bình đi rất xa.

Hai đường, vì chúng hỏng theo hai kiểu khác nhau:

    A. gộp lô   — `/v1/speech-dai`, cả bài trong một `infer_batch`
    B. lần lượt — `/v1/speech` từng đoạn, mỗi đoạn một lượt gọi riêng

## ⛔ SÀN NHIỄU LÀ PHẦN QUAN TRỌNG NHẤT CỦA PHÉP ĐO NÀY

F0 dao động **ngay trong một đoạn**, vì người ta lên giọng xuống giọng trong một
câu. Nên "chênh 8 Hz giữa đoạn đầu và đoạn cuối" **không nói lên gì** cho tới khi
biết F0 dao động bao nhiêu bên trong một đoạn.

Phép đo này lấy **độ lệch F0 trong từng đoạn** làm sàn, rồi hỏi: chênh GIỮA các
đoạn có lớn hơn dao động BÊN TRONG một đoạn không? Nếu không, thì không có trôi
tông nào để nói — chỉ có ngữ điệu bình thường.

Đúng bài học G4 ở `docs/ANH_NOI_BO/`: một khác biệt nhỏ hơn sàn nhiễu không phải
một khác biệt.

⚠️ Chạm GPU thật, không chạm sổ tiền (gọi thẳng cổng giọng).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ⛔ `reconfigure`, KHÔNG bọc lại `sys.stdout` bằng một TextIOWrapper mới.
#    Bọc lại tạo một đối tượng thứ hai trên cùng một `buffer`, và hai lớp đệm
#    trên một luồng thì thứ tự dòng in ra không còn bảo đảm. `test_353` chốt
#    việc này — và nó vừa bắt tôi ba lần trong một buổi.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Giọng người lớn nằm gọn trong khoảng này. Đặt hẹp hơn mặc định của librosa để
#: `pyin` không đi lạc lên hoà âm bậc hai — một lỗi khiến F0 nhảy gấp đôi và đọc
#: lên y hệt một cú trôi tông rất mạnh.
F0_MIN, F0_MAX = 70.0, 400.0

#: Mười hai đoạn của một bài đọc thật. Trôi tông là hiện tượng TÍCH LUỸ, nên đo
#: bằng ba đoạn thì không thấy gì kể cả khi nó có.
BAI = [
    "Chào các bạn, hôm nay tôi muốn kể một câu chuyện về nghề làm gốm.",
    "Ở làng tôi, gần như nhà nào cũng có một lò nung dựng sau vườn.",
    "Người ta lấy đất từ bãi bồi ven sông, phơi khô rồi đập cho tơi ra.",
    "Đất được nhào với nước cho tới khi dẻo và mịn, không còn hạt sạn nào.",
    "Khâu khó nhất là chuốt, vì bàn xoay không chờ ai bao giờ.",
    "Tay phải giữ thành, tay trái đỡ lòng, và cả hai phải cùng một nhịp.",
    "Một chiếc bình chuốt hỏng thì đập ra, trộn lại, làm lại từ đầu.",
    "Sau khi chuốt xong, sản phẩm được phơi trong bóng râm chừng ba ngày.",
    "Phơi nắng gắt thì nứt, mà phơi ẩm quá thì khi nung sẽ nổ trong lò.",
    "Men được pha từ tro trấu, đá vôi và một ít bột đá nghiền rất mịn.",
    "Lửa nung phải lên từ từ, suốt một ngày một đêm mới tới độ cần thiết.",
    "Mở lò là lúc hồi hộp nhất, vì không ai biết trước màu men sẽ ra sao.",
]


class ThieuTruong(RuntimeError):
    """Phản hồi thiếu trường cần đo. Phép đo VỠ, không lặng lẽ thành 0."""


def _f0(wav, sr: int) -> list:
    """F0 của các khung CÓ TIẾNG, Hz. Rỗng nếu đoạn không có tiếng nào."""
    import librosa
    import numpy as np

    f0, co_tieng, _ = librosa.pyin(
        np.asarray(wav, dtype=np.float32), fmin=F0_MIN, fmax=F0_MAX, sr=sr)
    if f0 is None:
        return []
    v = [float(x) for x, c in zip(f0, co_tieng) if c and x == x]  # x==x loại NaN
    return v


def _thong_ke(v: list) -> dict:
    if not v:
        return {}
    return {"trung_vi": round(statistics.median(v), 2),
            "lech": round(statistics.pstdev(v), 2) if len(v) > 1 else 0.0,
            "so_khung": len(v)}


def _doc_wav(raw: bytes):
    import soundfile as sf
    w, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
    return w, int(sr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-doan", type=int, default=12)
    ap.add_argument("--json", default="tmp/troi_tong.json")
    a = ap.parse_args(argv)

    # ⛔ TỰ KIỂM DỤNG CỤ Ở DÒNG ĐẦU, trước khi chạm GPU một lần nào.
    #
    #    Bản đầu của tệp này sinh **mười hai lượt** rồi mới chết ở
    #    `import soundfile` — vì trình bọc chạy nó bằng venv của nền tảng, còn
    #    `librosa`/`soundfile` chỉ có trong `vieneu-venv`. Mất vài phút GPU cho
    #    một câu trả lời mà một dòng `import` trả lời được trong 50 ms.
    #
    # ⭐ Và bài học rộng hơn, `-a5` đúc ra cùng ngày sau bốn lần dính: **kiểm
    #    dụng cụ trước khi tin số liệu** là một THÓI QUEN, không phải một bước
    #    thêm. Cả bốn lần đó dụng cụ hỏng đều cho ra thứ **đọc lên y hệt một
    #    kết quả thật**.
    thieu = []
    for ten in ("numpy", "soundfile", "librosa"):
        try:
            __import__(ten)
        except ImportError:
            thieu.append(ten)
    if thieu:
        print(f"THIEU {thieu} — chay bang python cua `vieneu-venv` "
              f"(LTT_VIENEU_PYTHON), khong phai venv nen tang.", file=sys.stderr)
        return 2

    import numpy as np

    from apps.ltt_voice import sidecar_client

    if not sidecar_client.san_sang():
        print("Cong giong CHUA san sang.", file=sys.stderr)
        return 2

    doan = BAI[:max(3, min(a.so_doan, len(BAI)))]
    print(f"{len(doan)} doan\n")
    sidecar_client.noi(doan[0])            # lam am

    ra = {}

    # ── B. lần lượt: từng đoạn một lượt gọi riêng ────────────────────────────
    # Đây là kịch bản #173 mô tả, nên đo nó trước.
    print("[B] lan luot — moi doan mot luot goi rieng")
    ho_so_b = []
    for i, d in enumerate(doan):
        raw, _ = sidecar_client.noi(d)
        w, sr = _doc_wav(raw)
        tk = _thong_ke(_f0(w, sr))
        if not tk:
            raise ThieuTruong(f"doan {i + 1} khong co khung co tieng nao")
        ho_so_b.append(tk)
        print(f"  doan {i + 1:2d}: F0 {tk['trung_vi']:6.1f} Hz "
              f"(lech trong doan {tk['lech']:5.2f})")
    ra["lan_luot"] = ho_so_b

    # ── A. gộp lô: cả bài trong một lượt, rồi cắt lại theo mốc ghép ──────────
    # ⭐ CẢ BÀI, không cắt bớt. Bộ đo này từng phải cắt còn 8 đoạn vì cửa văn bản
    #    dài áp `TRAN_SO_VAN_BAN_BATCH` — kích thước một lượt gộp lô, tức một
    #    chi tiết thi hành bên trong — lên chính người gọi. Nó tìm ra điều đó
    #    bằng cách đâm vào: 12 đoạn → `413 "Lo 12 van ban, vuot tran 8"`.
    #
    #    Nay cửa tự chia nhóm, nên số đoạn không còn là hợp đồng của khách.
    doan_a = doan
    print("\n[A] gop lo — ca bai, cua tu chia nhom")
    raw, dau = sidecar_client.noi_dai(list(doan_a))
    w, sr = _doc_wav(raw)
    doc = {str(k).lower(): v for k, v in dict(dau or {}).items()}
    if not doc.get("x-duration-s"):
        raise ThieuTruong(f"dau phan hoi thieu x-duration-s; co: {sorted(doc)}")
    # ⛔ Không có mốc từng đoạn thì KHÔNG bịa ra bằng cách chia đều: bản ghép có
    #    chèn nghỉ giữa các đoạn, nên chia đều sẽ cắt lệch dần và mọi đoạn sau
    #    đều đo nhầm vùng. Chia bằng nhau chỉ dùng khi hồ sơ ghép không nói mốc,
    #    và khi đó phải NÓI RA là con số kém tin hơn.
    # ⛔ MỘT DỤNG CỤ ĐO SAI KHÔNG ĐƯỢC PHÉP CHẠY TIẾP. Bản đầu lui về chia đều
    #    khi thiếu mốc, và lượt đo 01/09 đã cho ra một "phát hiện" rất thuyết
    #    phục nhờ đúng cái lối lui ấy: −5,05 Hz mỗi đoạn, có hướng, vượt sàn
    #    nhiễu. Nhưng chia đều sai **luỹ tiến** (mỗi mối nối chèn thêm `nghi`
    #    giây), nên nó tự sinh ra một xu hướng đơn điệu — đúng hình dạng của
    #    thứ ta đang đi tìm.
    #
    # ⭐ Nên chỗ này KHÔNG lui nữa: thiếu mốc thì **vỡ**. Một phép đo nói "kém
    #    tin hơn" ở dòng cuối vẫn sẽ được ai đó trích ra khỏi ngữ cảnh và đọc
    #    như một kết luận. Ba lần trong ngày hôm nay một dụng cụ hỏng đã cho ra
    #    thứ đọc lên y hệt một kết quả thật.
    tho = (doc.get("x-moc-s") or "").strip()
    if not tho:
        raise ThieuTruong(
            "dau phan hoi thieu X-Moc-S. Cong giong phai noi moc tung doan — "
            "chia deu ma doan se cat lech luy tien va sinh ra mot xu huong GIA. "
            f"Dau co: {sorted(doc)}")
    moc = [float(x) for x in tho.split(",") if x.strip()]
    if len(moc) != len(doan_a) + 1:
        raise ThieuTruong(
            f"X-Moc-S co {len(moc)} moc cho {len(doan_a)} doan; can "
            f"{len(doan_a) + 1}")
    ho_so_a, cach_cat = [], "moc that tu ho so ghep"
    for i in range(len(doan_a)):
        seg = w[int(moc[i] * sr):int(moc[i + 1] * sr)]
        tk = _thong_ke(_f0(seg, sr))
        ho_so_a.append(tk)
        if tk:
            print(f"  doan {i + 1:2d}: F0 {tk['trung_vi']:6.1f} Hz "
                  f"(lech trong doan {tk['lech']:5.2f})")
    ra["gop_lo"] = ho_so_a
    ra["cach_cat_gop_lo"] = cach_cat
    ra["so_doan_gop_lo"] = len(doan_a)

    # ── phán quyết ──────────────────────────────────────────────────────────
    print("\n" + "=" * 68)
    print("  TROI TONG — chenh GIUA cac doan so voi dao dong BEN TRONG mot doan")
    print("=" * 68)
    ket = {}
    for ten in ("lan_luot", "gop_lo"):
        hs = ra[ten]
        tv = [x["trung_vi"] for x in hs if x]
        if len(tv) < 3:
            print(f"  {ten}: khong du doan do duoc")
            continue
        giua = max(tv) - min(tv)
        san = statistics.mean(x["lech"] for x in hs if x)
        # Độ dốc: trôi tông là hiện tượng CÓ HƯỚNG. Một bài F0 nhảy lung tung
        # quanh một mức không phải trôi; một bài đi lên đều mới là trôi.
        n = len(tv)
        xm, ym = (n - 1) / 2, statistics.mean(tv)
        mau = sum((i - xm) ** 2 for i in range(n))
        doc_ = sum((i - xm) * (tv[i] - ym) for i in range(n)) / mau if mau else 0.0
        ket[ten] = {"chenh_giua_doan_hz": round(giua, 2),
                    "san_nhieu_trong_doan_hz": round(san, 2),
                    "doc_hz_moi_doan": round(doc_, 3),
                    "vuot_san": giua > san}
        print(f"\n  {ten}:")
        print(f"    chenh giua cac doan : {giua:6.2f} Hz")
        print(f"    dao dong trong doan : {san:6.2f} Hz  <- san nhieu")
        print(f"    do doc              : {doc_:+6.3f} Hz moi doan")
        if giua <= san:
            print("    ⇒ KHONG co troi tong do duoc — chenh nho hon san nhieu.")
        elif abs(doc_ * (n - 1)) < san:
            print("    ⇒ Co chenh nhung KHONG CO HUONG: la ngu dieu, khong phai troi.")
        else:
            print(f"    🔴 CO TROI TONG: chenh vuot san VA co huong "
                  f"({'len' if doc_ > 0 else 'xuong'}).")
    ra["ket_luan"] = ket

    os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as f:
        json.dump(ra, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
