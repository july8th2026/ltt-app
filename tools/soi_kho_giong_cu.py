r"""
soi_kho_giong_cu.py — chấm kho giọng của hệ CŨ (`D:\Voiceclone_TTS`) bằng bộ đo
của hệ MỚI, để chọn giọng mẫu.

    powershell -ExecutionPolicy Bypass -File .\setup\soi_kho_giong_cu.ps1

## Vì sao đo lại thay vì tin điểm cũ

Hệ cũ đã có `audit_report.json` cho từng kho tham chiếu, và nó tốt. Nhưng nó
chấm cho **F5-TTS**, và thang điểm ấy có những mục **không áp dụng được** cho
VieNeu:

  · Luật rò chú thích (`wps <= 2.8`, `<= 12 từ`, phải kết thúc bằng dấu chấm)
    là một hiện tượng của cơ chế **attention trên văn bản tham chiếu** ở F5.
    VieNeu **không nhận văn bản tham chiếu** — `ghi_danh` nhận một tệp wav và
    trả về một embedding. Không có chữ nào để rò.
  · Điểm tổng hợp của họ cân theo trọng số trong đó `text_structure` chiếm
    **0,22** — mục nặng nhất, và là mục vô nghĩa với ta.

⇒ Phần tín hiệu (SNR, clipping, độ to, im lặng) thì dùng lại được; phần văn bản
  thì không. Nên chấm lại bằng thang của ta, và **so hai bảng** thay vì thay thế
  một bảng bằng bảng kia.

## ✅ NHÃN `lang` ĐÁNG TIN — VÀ ĐÂY LÀ MỘT PHỎNG ĐOÁN CỦA TÔI ĐÃ BỊ BÁC BỎ

⛔ Chỗ này trước 01/09/2026 khẳng định điều ngược lại: rằng `voice_profiles.yaml`
   ghi `lang: en` cho những cái tên tiếng Việt rành mạch (`hoathinh_female`,
   `meoquan_men`, `tamlyhoc_men`, `cg_huong_nam`) nên `lang` hẳn có nghĩa *"làn
   XTTS"* chứ không phải ngôn ngữ người nói. Nó được viết ra như một **phát
   hiện**. Nó là một **phỏng đoán**, và nó sai.

Chủ sản phẩm nói thẳng cách hệ cũ được xây: **F5-TTS train bằng giọng tiếng
Việt, XTTS bằng giọng tiếng Anh.** Chính tệp này đã đo và số liệu khớp tuyệt
đối — chỉ là tôi đọc nó qua một giả thuyết sai:

    engine   số giọng   nhãn `lang`   ASR đo được   độ tin
    f5tts        7          vi           vi 7/7      0,987 – 0,998
    xtts        17          en           en 17/17    0,992 – 1,000

24/24 khớp. Không có một ngoại lệ nào để giả thuyết của tôi bám vào.

⭐ Cái tên tiếng Việt trên một giọng nói tiếng Anh không phải mâu thuẫn: nó là
   tên **kênh/nhân vật** mà giọng ấy phục vụ, không phải tên người nói. Tôi đã
   đọc tên như dữ liệu và bỏ qua cột `engine` — cột duy nhất mang câu trả lời.

🔴 Vì sao ghi lại thay vì lặng lẽ xoá: một phiên sau đọc phải đoạn cũ sẽ đi "sửa"
   những cái nhãn **vốn đúng**, và nó sẽ làm vậy một cách tự tin vì đoạn ấy tự
   xưng là kết quả đo. Bài học không phải "đừng đoán" mà là: **viết ra thứ đo
   được, đừng viết ra cách giải thích nó** — số liệu 24/24 ở trên đúng từ đầu,
   chỉ có câu kết luận cạnh nó là sai.

⚠️ Hệ quả thi hành, và nó không hiển nhiên: engine mới **không nói được tiếng
   Anh**. `vieneu_utils/phonemize_text.py` khoá cứng `SEAPipeline(lang="vi")` +
   `G2P(lang="vi")` ở tầng singleton — mọi văn bản đi qua G2P tiếng Việt. Nên 17
   giọng XTTS chỉ dùng được như **nguồn âm sắc**, không phải như "giọng tiếng
   Anh của nền tảng".

## Cách chấm

Mỗi giọng có 3–5 clip tham chiếu **đã được hệ cũ tuyển**. Ta nối chúng lại
thành một clip dài rồi:

  · chấm DNSMOS P.835 (SIG/BAK/OVRL) — chất lượng cảm nhận, không cần bản gốc
  · chạy `chon_doan` — đúng bộ chọn mà `ghi_danh` sẽ chạy
  · nghe lại bằng ASR — ngôn ngữ + một câu để người đọc tự đối chiếu

⭐ Nối cả kho lại là chỗ hai hệ bổ sung cho nhau: hệ cũ đã lọc ra **những đoạn
   sạch nhất của người nói**, hệ mới **chọn cửa sổ đại diện nhất trong đó**.

⚠️ Chỉ ĐỌC `D:\Voiceclone_TTS`. Không ghi, không sửa, không xoá.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

KHO_CU = r"D:\Voiceclone_TTS"
NGHI_S = 0.35            # khoảng nghỉ chèn giữa hai clip khi nối


class KhongDoDuoc(RuntimeError):
    """Không đo được thì VỠ, không lặng lẽ thành một con số."""


def _nghe_lai(duong: str) -> dict:
    """`{ngon_ngu, do_tin, text}` — gọi ASR ở venv NỀN TẢNG.

    Cùng khuôn `do_chat_luong._asr`: một model ASR gần 1 GB không nên tồn tại
    hai bản trên cùng một máy.
    """
    py = os.environ.get("LTT_PLATFORM_PYTHON",
                        r"C:\LTTPlatform\venv\Scripts\python.exe")
    if not os.path.isfile(py):
        return {"loi": f"khong thay {py}"}
    ma = (
        "import sys,json\n"
        "from faster_whisper import WhisperModel\n"
        "m=WhisperModel(sys.argv[2], device='cpu', compute_type='int8')\n"
        # language=None => de Whisper TU DO ngon ngu. Do la ca muc dich.
        "seg,info=m.transcribe(sys.argv[1], beam_size=5,\n"
        "                      condition_on_previous_text=False)\n"
        "t=' '.join(s.text for s in seg)\n"
        "print(json.dumps({'lang':info.language,'p':info.language_probability,\n"
        "                  'text':t}))\n"
    )
    try:
        r = subprocess.run([py, "-c", ma, duong,
                            os.environ.get("LTT_ASR_MODEL", "small")],
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=600)
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"loi": f"{type(e).__name__}: {e}"}
    if r.returncode != 0:
        return {"loi": (r.stderr or "")[-200:]}
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
        return {"ngon_ngu": d["lang"], "do_tin": round(float(d["p"]), 3),
                "text": (d["text"] or "").strip()}
    except (ValueError, IndexError, KeyError) as e:
        return {"loi": f"khong doc duoc ket qua ASR: {e}"}


def _noi_kho(cac: list):
    """Nối các clip tham chiếu thành một clip dài. Trả `(wav, sr)`."""
    import numpy as np
    import soundfile as sf

    manh, sr = [], None
    for p in cac:
        w, s = sf.read(p, dtype="float32", always_2d=False)
        if w.ndim > 1:
            w = w.mean(axis=1)
        if sr is None:
            sr = int(s)
        elif int(s) != sr:
            # ⛔ Trộn hai tần số lấy mẫu là tạo ra một tệp không ai nghe đúng.
            raise KhongDoDuoc(f"kho co hai sample rate: {sr} va {s}")
        if manh:
            manh.append(np.zeros(int(sr * NGHI_S), dtype="float32"))
        manh.append(np.asarray(w, dtype="float32"))
    if not manh:
        raise KhongDoDuoc("kho rong")
    return np.concatenate(manh), sr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kho", default=KHO_CU)
    ap.add_argument("--bo-asr", action="store_true",
                    help="Bo qua buoc nghe lai (nhanh hon nhieu, mat ngon ngu).")
    ap.add_argument("--ra", default="tmp/kho_giong_cu.json")
    ap.add_argument("--luu-clip", default="tmp/giong_cu",
                    help="Noi ghi clip da noi, de con ghi danh sau nay.")
    a = ap.parse_args(argv)

    thieu = [m for m in ("numpy", "soundfile", "librosa")
             if not _co(m)]
    if thieu:
        print(f"THIEU {thieu} — chay bang python cua `vieneu-venv`.",
              file=sys.stderr)
        return 2

    import soundfile as sf
    import yaml

    from voice_sidecar import chon_doan, dnsmos

    if not dnsmos.co_san():
        print(f"THIEU model DNSMOS ({dnsmos.duong_model()}).", file=sys.stderr)
        return 2

    hs = yaml.safe_load(open(os.path.join(a.kho, "configs", "voice_profiles.yaml"),
                             encoding="utf-8")).get("profiles", {})
    os.makedirs(a.luu_clip, exist_ok=True)

    ra = []
    ten_ds = sorted(k for k in hs if not k.startswith("_"))
    for i, ten in enumerate(ten_ds, 1):
        cac = sorted(glob.glob(os.path.join(a.kho, "speakers", ten,
                                            "reference", "*.wav")))
        if not cac:
            print(f"[{i:2}/{len(ten_ds)}] {ten:28} — khong co clip nao")
            continue
        try:
            wav, sr = _noi_kho(cac)
        except KhongDoDuoc as e:
            print(f"[{i:2}/{len(ten_ds)}] {ten:28} — BO: {e}")
            continue

        duong = os.path.join(a.luu_clip, f"{ten}.wav")
        sf.write(duong, wav, sr)

        d = dnsmos.cham(wav, sr) or {}
        kq = chon_doan.chon(wav, sr)
        muc = {
            "ten": ten,
            "lang_khai": str(hs[ten].get("lang") or ""),
            "gioi": str(hs[ten].get("gender") or ""),
            "engine": str(hs[ten].get("engine") or ""),
            "so_clip": len(cac),
            "giay": round(len(wav) / float(sr), 2),
            "sample_rate": sr,
            "dnsmos": d,
            "chon_doan": {"bat_dau_s": kq.bat_dau_s, "ket_thuc_s": kq.ket_thuc_s,
                          "diem_dai_dien": kq.diem_dai_dien,
                          "thang": kq.thang_chat_luong,
                          "so_ung_vien": kq.so_ung_vien},
            "clip": duong,
        }
        if not a.bo_asr:
            muc["nghe_lai"] = _nghe_lai(duong)
        ra.append(muc)
        ng = (muc.get("nghe_lai") or {}).get("ngon_ngu", "?")
        print(f"[{i:2}/{len(ten_ds)}] {ten:28} {muc['giay']:6.1f}s  "
              f"OVRL {d.get('ovrl', 0):5.3f}  dai dien "
              f"{kq.diem_dai_dien or 0:.4f}  khai={muc['lang_khai']:2} "
              f"do={ng}")

    ra.sort(key=lambda m: -(m["dnsmos"].get("ovrl") or 0))
    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ra, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 78)
    print("  XEP HANG THEO DNSMOS OVRL (cao hon la sach hon)")
    print("=" * 78)
    print(f"  {'giong':28} {'OVRL':>6} {'SIG':>6} {'BAK':>6} {'khai':>5} {'do':>4}")
    for m in ra:
        d = m["dnsmos"]
        ng = (m.get("nghe_lai") or {}).get("ngon_ngu", "?")
        lech = " <- LECH NHAN" if ng not in ("?", m["lang_khai"]) else ""
        print(f"  {m['ten']:28} {d.get('ovrl', 0):6.3f} {d.get('sig', 0):6.3f} "
              f"{d.get('bak', 0):6.3f} {m['lang_khai']:>5} {ng:>4}{lech}")
    print(f"\nDa ghi: {a.ra}")
    return 0


def _co(m: str) -> bool:
    try:
        __import__(m)
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
