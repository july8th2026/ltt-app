r"""
do_chon_doan.py — bộ chọn đoạn có THẬT SỰ cho giọng nhân bản giống hơn không?

    $env:PYTHONPATH = 'D:\LTTSTUDIOSAPP'
    C:\LTTPlatform\vieneu-venv\Scripts\python.exe tools\do_chon_doan.py

## Câu hỏi

`voice_sidecar/chon_doan.py` chọn đoạn "đại diện nhất" thay vì để SDK cắt 8 giây
đầu. Lập luận nghe vững, và **lập luận không phải bằng chứng**. Phép đo này hỏi
một câu trả lời được:

    Nhân bản từ đoạn ĐÃ CHỌN có giống người nói hơn nhân bản từ 8 GIÂY ĐẦU không?

## Cách đo — A/B trên cùng một clip

Cùng clip nguồn, cùng câu đọc, cùng tham số. Chỉ khác **đoạn tham chiếu**:

    A. 8 giây đầu          — đúng thứ SDK tự làm hôm nay
    B. đoạn bộ chọn chọn   — thứ ta vừa xây

Rồi so bản sinh ra với **cả clip nguồn** bằng bộ mã hoá người nói. Cả clip là
thứ gần nhất ta có với "giọng thật của người này", nên bản nào gần nó hơn là bản
nhân bản tốt hơn.

⛔ MỘT LƯỢT KHÔNG PHẢI MỘT KẾT LUẬN. Sinh tiếng có ngẫu nhiên (`temperature`
   0,8), nên chạy nhiều lượt và báo cả độ lệch. Một lượt A thắng B không nói lên
   gì nếu khoảng cách nhỏ hơn dao động giữa hai lượt của cùng một bên — đúng bài
   học của G4 trong `docs/ANH_NOI_BO/`.

⚠️ Nạp model trong tiến trình này, tức thêm ~641 MB VRAM bên cạnh dịch vụ
   `LTTStudioVoice` đang chạy. Card 16 GB nên thoải mái, nhưng đừng chạy khi máy
   đang có lô ảnh.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Câu đọc để so. Cố định, vì ta đang so ĐOẠN THAM CHIẾU chứ không so văn bản.
CAU_DOC = ("Hôm nay tôi thử đọc một đoạn ngắn để kiểm tra giọng nói vừa được "
           "nhân bản từ bản thu của chính mình.")

#: Bốn câu dựng clip nguồn. Cố ý khác nhau về nhịp và nội dung — một clip thật
#: không phải một câu lặp lại.
CAU_NGUON = [
    "Xin chào, tôi là người đang thử tính năng nhân bản giọng nói của LTT Studios.",
    "Buổi sáng hôm nay trời khá đẹp, gió nhẹ và nắng vừa đủ để đi bộ một vòng.",
    "Tôi sẽ đọc thêm vài câu nữa để bản thu đủ dài cho hệ thống học cách nói.",
    "Cuối cùng, xin cảm ơn bạn đã lắng nghe đoạn ghi âm ngắn này.",
    "Tôi làm việc ở một công ty nhỏ, mỗi ngày đi qua ba con phố quen thuộc.",
    "Có hôm trời mưa rất to, tôi đứng trú dưới mái hiên và nhìn dòng người vội vã.",
    "Bản ghi này chỉ dùng để thử, và tôi không đọc theo một kịch bản nào cả.",
]


def _im(giay: float, sr: int):
    return np.zeros(int(sr * giay), dtype=np.float32)


def dung_clip_nguon(cong, sr: int, *, them_nhieu: bool) -> np.ndarray:
    """Clip nguồn ~25–30 giây, có cấu trúc như một bản thu thật.

    `them_nhieu=True` bôi nhiễu lên **8 giây đầu** — mô phỏng ca hay gặp nhất:
    khách bấm ghi rồi mới chỉnh micro, nên phần đầu là phần tệ nhất. Đó đúng là
    phần SDK sẽ lấy nếu không ai chọn.
    """
    manh = []
    for i, cau in enumerate(CAU_NGUON):
        wav, _ = cong.noi(cau)
        wav = np.asarray(wav, dtype=np.float32)
        if them_nhieu and i == 0:
            rng = np.random.default_rng(20260831)
            wav = (wav + rng.standard_normal(len(wav)) * 0.06).astype(np.float32)
        manh.append(wav)
        manh.append(_im(0.5, sr))
    return np.concatenate(manh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-luot", type=int, default=3,
                    help="So luot sinh moi ben. Mot luot khong phai mot ket luan.")
    ap.add_argument("--sach", action="store_true",
                    help="Clip nguon KHONG boi nhieu dau — doi chung.")
    ap.add_argument("--clip", default="",
                    help="Luu/dung lai clip nguon. BAT BUOC khi so hai cau hinh "
                         "voi nhau — sinh lai clip moi luot thi hai lan chay "
                         "khong con so duoc.")
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)

    import soundfile as sf

    from voice_sidecar import chon_doan, engine
    from voice_sidecar.do_chat_luong import _bo_ma_hoa_giong, _embed

    def cos(x, y):
        x = np.asarray(x, np.float64).ravel()
        y = np.asarray(y, np.float64).ravel()
        nx, ny = np.linalg.norm(x), np.linalg.norm(y)
        return 0.0 if nx == 0 or ny == 0 else float(np.dot(x, y) / (nx * ny))

    cong = engine.CongGiong()
    cong.nap()
    sr = cong.sample_rate
    bo = _bo_ma_hoa_giong()
    if bo is None:
        print("khong nap duoc bo ma hoa giong", file=sys.stderr)
        return 2

    # ⛔ CLIP NGUON PHAI CO DINH khi so hai cau hinh. Sinh tieng co ngau nhien
    #    (`temperature` 0,8), nen hai lan chay tren hai clip khac nhau cho hai
    #    duong co so khac nhau — va chenh giua chung khong noi gi ve cau hinh.
    #    Da suyt doc nham dung kieu do: SNR ra +0,0873, DNSMOS ra +0,0152, tren
    #    HAI clip khac nhau.
    if a.clip and os.path.isfile(a.clip):
        nguon, sr_doc = sf.read(a.clip, dtype="float32", always_2d=False)
        nguon = np.asarray(nguon, dtype=np.float32)
        sr = int(sr_doc)
        print(f"Dung lai clip nguon co san: {a.clip}")
    else:
        print(f"Dung clip nguon ({'SACH' if a.sach else 'nhieu o 8 giay dau'})…")
        nguon = dung_clip_nguon(cong, sr, them_nhieu=not a.sach)
        if a.clip:
            sf.write(a.clip, nguon, sr)
            print(f"  da luu de dung lai: {a.clip}")
    print(f"  clip nguon: {len(nguon) / sr:.1f}s")

    kq_chon = chon_doan.chon(nguon, sr)
    print(f"  bo chon    : {kq_chon.bat_dau_s}s → {kq_chon.ket_thuc_s}s  "
          f"(dai dien {kq_chon.diem_dai_dien}, {kq_chon.so_ung_vien} ung vien)")
    print(f"  ly do      : {kq_chon.ly_do}")

    n8 = int(chon_doan.CUA_SO_S * sr)
    ben = {
        "A_tam_giay_dau": nguon[:n8],
        "B_doan_da_chon": nguon[int(kq_chon.bat_dau_s * sr):
                                int(kq_chon.ket_thuc_s * sr)],
    }

    emb_nguon = _embed(bo, nguon, sr)
    bang: dict = {}
    for ten, cua in ben.items():
        tam = f"_ref_{ten}.wav"
        sf.write(tam, np.asarray(cua, dtype=np.float32), sr)
        try:
            ref = cong.ghi_danh(tam, denoise=True)["ref_b64"]
        finally:
            try:
                os.unlink(tam)
            except OSError:
                pass

        diem = []
        for i in range(a.so_luot):
            wav, _ = cong.noi(CAU_DOC, ref_b64=ref)
            diem.append(cos(_embed(bo, np.asarray(wav, np.float32), sr), emb_nguon))
            print(f"  {ten}  luot {i + 1}: {diem[-1]:.4f}")
        bang[ten] = {"diem": [round(d, 4) for d in diem],
                     "trung_binh": round(float(np.mean(diem)), 4),
                     "lech_chuan": round(float(np.std(diem)), 4)}

    A, B = bang["A_tam_giay_dau"], bang["B_doan_da_chon"]
    chenh = B["trung_binh"] - A["trung_binh"]
    dao_dong = max(A["lech_chuan"], B["lech_chuan"])

    print(f"\n{'=' * 68}")
    print("  NHAN BAN TU DOAN NAO GIONG NGUOI NOI HON")
    print("=" * 68)
    print(f"  A · 8 giay dau     : {A['trung_binh']:.4f}  (lech {A['lech_chuan']:.4f})")
    print(f"  B · doan da chon   : {B['trung_binh']:.4f}  (lech {B['lech_chuan']:.4f})")
    print(f"  chenh B - A        : {chenh:+.4f}")
    print(f"  dao dong trong ben : {dao_dong:.4f}")
    print()
    if abs(chenh) <= dao_dong:
        print("  ⚠️ CHENH NHO HON DAO DONG TRONG MOT BEN — chua ket luan duoc.")
        print("     Chay them luot, hoac chap nhan rang bo chon khong do duoc o")
        print("     cau hinh nay. Dung doc mot dau cong nho thanh mot chien thang.")
    elif chenh > 0:
        print("  ⇒ Doan da chon giong hon, va khoang cach LON HON dao dong.")
    else:
        print("  🔴 8 giay dau giong HON. Bo chon dang lam hai — dung bat no.")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"clip_giay": round(len(nguon) / sr, 2),
                       "chon": kq_chon.__dict__, "ben": bang,
                       "chenh": round(chenh, 4)}, f, ensure_ascii=False, indent=2)
        print(f"\nDa ghi: {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
