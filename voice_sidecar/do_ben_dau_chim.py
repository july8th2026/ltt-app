r"""
do_ben_dau_chim.py — dấu chìm còn đọc được sau khi tệp bị ĐỘNG VÀO chưa?

    C:\LTTPlatform\vieneu-venv\Scripts\python.exe -m voice_sidecar.do_ben_dau_chim ra.wav

## Vì sao phép đo này cần tồn tại

`do_chat_luong` báo dấu chìm đọc lại được `1.0`. Đúng, và **gần như vô nghĩa**:
nó đo trên tệp WAV nguyên vẹn vừa ra khỏi model. Không khách nào giữ tệp ở dạng
đó. Họ nén sang MP3 để đăng, cắt lấy một đoạn, chỉnh tốc độ cho khớp video.

Một lời hứa provenance chỉ đúng với tệp chưa ai đụng vào thì **không phải một
lời hứa** — nó là một con số đẹp ở chỗ không ai cần nó.

## Năm phép hành hạ, và vì sao đúng năm phép này

Chọn theo thứ **khách thật sự làm**, không theo thứ dễ viết:

  1. **MP3 128 kbps** — thao tác phổ biến nhất. Nén có mất dữ liệu chính là thứ
     xoá dấu chìm dễ nhất.
  2. **Cắt 5 giây ở giữa** — người ta cắt lấy một câu. Dấu *toàn cục* sẽ chết ở
     đây; dấu *cục bộ* (kiểu AudioSeal) thì sống.
  3. **Đổi tốc độ ±10 %** — khớp với độ dài video.
  4. **Thêm nhiễu nền** (SNR 20 dB) — trộn với nhạc nền.
  5. **Chuẩn hoá độ to về −16 LUFS** — mọi nền tảng phát trực tuyến đều làm.

⛔ KHÔNG có ngưỡng ĐẠT/HỎNG ở đây, cùng luật với `do_chat_luong`: Perth không
   công bố ngưỡng tin cậy nào cho `get_watermark`, nên gán một mốc là tự bịa.
   Báo số, và người đọc quyết định.

⭐ Con số này dùng để trả lời MỘT câu hỏi sản phẩm: có nên đổi sang **AudioSeal**
   (Meta, MIT, 776★) không. AudioSeal đóng dấu **cục bộ** và công bố là bền hơn.
   Đổi bộ đóng dấu là đổi thứ nằm trong mọi tệp đã bán, nên nó phải có số.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: SNR cho phép thêm nhiễu. 20 dB là mức nhạc nền còn nghe rõ lời.
SNR_DB = 20.0
#: Mốc chuẩn hoá độ to, cùng con số với `do_chat_luong.LUFS_MUC_TIEU`.
LUFS_MUC_TIEU = -16.0


def _ffmpeg(vao: str, ra: str, *loc: str) -> bool:
    lenh = ["ffmpeg", "-y", "-loglevel", "error", "-i", vao, *loc, ra]
    try:
        r = subprocess.run(lenh, capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and os.path.getsize(ra) > 0


def _doc(duong: str):
    import soundfile as sf
    wav, sr = sf.read(duong, dtype="float32", always_2d=False)
    if getattr(wav, "ndim", 1) > 1:
        wav = wav.mean(axis=1)
    return np.asarray(wav, dtype=np.float32), int(sr)


def _ghi(duong: str, wav, sr: int) -> None:
    import soundfile as sf
    sf.write(duong, np.asarray(wav, dtype=np.float32), sr)


def _doc_dau(duong: str) -> float:
    """Đọc lại dấu chìm. Trả điểm tin cậy, hoặc `-1.0` nếu không đọc được."""
    from .do_chat_luong import do_watermark
    wav, sr = _doc(duong)
    kq = do_watermark(wav, sr)
    # ⚠️ Khoá là `doc_lai_duoc`, không phải `doc_lai`. Gõ nhầm tên khoá cho ra
    #    `-1.0` ở MỌI phép — kể cả đối chứng — và bảng đó đọc y hệt "dấu chìm
    #    không bền chút nào". Đối chứng có mặt chính là để bắt kiểu sai này:
    #    nếu tệp nguyên vẹn cũng hỏng thì thủ phạm là phép đo, không phải dấu.
    v = kq.get("doc_lai_duoc")
    return float(v) if v is not None else -1.0


# ── năm phép hành hạ ────────────────────────────────────────────────────────

def _mp3(vao: str, tmp: str) -> str | None:
    giua = os.path.join(tmp, "x.mp3")
    ra = os.path.join(tmp, "mp3.wav")
    if not _ffmpeg(vao, giua, "-codec:a", "libmp3lame", "-b:a", "128k"):
        return None
    return ra if _ffmpeg(giua, ra) else None


def _cat(vao: str, tmp: str) -> str | None:
    wav, sr = _doc(vao)
    giay = len(wav) / float(sr)
    if giay < 7:
        return None
    bat_dau = int((giay / 2 - 2.5) * sr)
    ra = os.path.join(tmp, "cat.wav")
    _ghi(ra, wav[bat_dau:bat_dau + int(5 * sr)], sr)
    return ra


def _doi_toc_do(vao: str, tmp: str, he_so: float) -> str | None:
    ra = os.path.join(tmp, f"tocdo_{he_so}.wav")
    return ra if _ffmpeg(vao, ra, "-filter:a", f"atempo={he_so}") else None


def _them_nhieu(vao: str, tmp: str) -> str | None:
    wav, sr = _doc(vao)
    rms = float(np.sqrt((wav.astype(np.float64) ** 2).mean()))
    if rms <= 0:
        return None
    # Nhiễu trắng ở đúng SNR yêu cầu. Dùng hạt cố định để chạy lại ra y hệt.
    muc = rms / (10 ** (SNR_DB / 20.0))
    rng = np.random.default_rng(20260831)
    ra = os.path.join(tmp, "nhieu.wav")
    _ghi(ra, np.clip(wav + rng.standard_normal(len(wav)) * muc, -1.0, 1.0), sr)
    return ra


def _chuan_do_to(vao: str, tmp: str) -> str | None:
    ra = os.path.join(tmp, "lufs.wav")
    return ra if _ffmpeg(vao, ra, "-filter:a",
                         f"loudnorm=I={LUFS_MUC_TIEU}:TP=-1.5:LRA=11") else None


def _am_trang(vao: str, tmp: str) -> str | None:
    """ĐỐI CHỨNG ÂM: nhiễu trắng, CHƯA TỪNG được đóng dấu."""
    _, sr = _doc(vao)
    rng = np.random.default_rng(1)
    ra = os.path.join(tmp, "amtrang.wav")
    _ghi(ra, (rng.standard_normal(sr * 6) * 0.1).astype(np.float32), sr)
    return ra


def _im_lang(vao: str, tmp: str) -> str | None:
    """ĐỐI CHỨNG ÂM: im lặng tuyệt đối."""
    _, sr = _doc(vao)
    ra = os.path.join(tmp, "imlang.wav")
    _ghi(ra, np.zeros(sr * 6, dtype=np.float32), sr)
    return ra


def _mp3_32k(vao: str, tmp: str) -> str | None:
    """Nén rất nặng — nếu dấu vẫn 1.0 ở đây thì gần như chắc chắn bộ dò bão hoà."""
    giua = os.path.join(tmp, "y.mp3")
    ra = os.path.join(tmp, "mp3_32k.wav")
    if not _ffmpeg(vao, giua, "-codec:a", "libmp3lame", "-b:a", "32k", "-ar", "16000"):
        return None
    return ra if _ffmpeg(giua, ra) else None


# 🔴 BA DÒNG ĐẦU LÀ ĐỐI CHỨNG, VÀ CHÚNG QUAN TRỌNG HƠN CẢ BẢY DÒNG SAU.
#
#    Một bảng toàn `1.0` có ĐÚNG HAI cách đọc: dấu chìm rất bền, hoặc bộ dò
#    luôn trả lời "có". Hai cách đọc đó cho cùng một bảng số, và chỉ đối chứng
#    ÂM mới tách được chúng.
#
#    Nếu nhiễu trắng — thứ chưa từng đi qua bộ đóng dấu — cũng cho `1.0`, thì
#    toàn bộ phần dưới không nói gì về độ bền cả, và lời hứa provenance của sản
#    phẩm đang dựa trên một phép đo không phân biệt được.
PHEP = [
    ("DOI_CHUNG_am_trang", "nhieu trang, CHUA TUNG dong dau", _am_trang),
    ("DOI_CHUNG_im_lang", "im lang tuyet doi", _im_lang),
    ("goc", "tep nguyen ven (doi chung duong)", lambda v, t: v),
    ("mp3_128k", "nen MP3 128 kbps roi giai nen", _mp3),
    ("cat_5s", "cat 5 giay o giua", _cat),
    ("toc_do_110", "tang toc 10%", lambda v, t: _doi_toc_do(v, t, 1.1)),
    ("toc_do_090", "giam toc 10%", lambda v, t: _doi_toc_do(v, t, 0.9)),
    ("nhieu_20db", f"them nhieu trang SNR {SNR_DB:.0f} dB", _them_nhieu),
    ("chuan_do_to", f"chuan hoa ve {LUFS_MUC_TIEU:.0f} LUFS", _chuan_do_to),
    ("mp3_32k", "nen rat nang: MP3 32 kbps @ 16 kHz", _mp3_32k),
]


def do_tat_ca(duong: str) -> list:
    ra = []
    with tempfile.TemporaryDirectory() as tmp:
        for ma, mo_ta, ham in PHEP:
            try:
                tep = ham(duong, tmp)
            except Exception as e:      # noqa: BLE001 - mot phep hong khong duoc lam do ca bo
                ra.append({"phep": ma, "mo_ta": mo_ta, "loi": f"{type(e).__name__}: {e}"})
                continue
            if not tep or not os.path.isfile(tep):
                ra.append({"phep": ma, "mo_ta": mo_ta,
                           "loi": "khong tao duoc tep (thieu ffmpeg?)"})
                continue
            ra.append({"phep": ma, "mo_ta": mo_ta,
                       "doc_lai": round(_doc_dau(tep), 4),
                       "so_byte": os.path.getsize(tep)})
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("duong")
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)

    if not os.path.isfile(a.duong):
        print(f"khong thay {a.duong}", file=sys.stderr)
        return 2

    kq = do_tat_ca(a.duong)
    print(f"\n{'=' * 72}")
    print(f"  DO BEN DAU CHIM — {os.path.basename(a.duong)}")
    print("=" * 72)
    print(f"  {'phep':<14} {'doc lai':>9}   mo ta")
    for m in kq:
        gt = m.get("doc_lai")
        print(f"  {m['phep']:<14} "
              f"{('KHONG DOC DUOC' if gt is None else f'{gt:>9.4f}')}   "
              f"{m['mo_ta']}" + (f"   [{m['loi']}]" if m.get("loi") else ""))
    print()
    print("  DOC HAI DONG DOI_CHUNG TRUOC. Chung chua tung di qua bo dong dau,")
    print("  nen chung PHAI cho gia tri khac han phan con lai. Neu khong khac,")
    print("  bo do dang bao hoa va MOI con so duoi day khong noi gi ve do ben.")
    print()
    print("  Khong co nguong DAT/HONG o day: Perth khong cong bo muc tin cay nao,")
    print("  nen gan mot moc la tu bia.")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(kq, f, ensure_ascii=False, indent=2)
        print(f"\nDa ghi: {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
