"""
do_chat_luong.py — bộ đo chất lượng cho MỘT tệp tiếng nói.

    python -m voice_sidecar.do_chat_luong ra.wav --text "câu đã yêu cầu đọc"
    ... --ref clip_mau.wav --json ket_qua.json

Chạy trong `vieneu-venv` (cần onnxruntime + librosa + scipy). Phần nhận dạng
tiếng nói gọi sang venv nền tảng — xem `_asr()`.

═══════════════════════════════════════════════════════════════════════════════
⭐ NGUYÊN TẮC ĐỨNG SAU MỌI CON SỐ Ở ĐÂY
═══════════════════════════════════════════════════════════════════════════════

**Một phép đo không có ngưỡng có nguồn thì báo SỐ, không báo ĐẠT/HỎNG.**

Đây không phải sự dè dặt. Ba loại con số trộn lẫn trong mọi bộ đo âm thanh, và
gộp chúng làm một là cách nhanh nhất để một bảng màu xanh nói dối:

  1. **Có tiêu chuẩn ngoài** — LUFS, true peak. EBU R128 và ITU-R BS.1770-4 nói
     rõ ngưỡng. Ở đây ĐẠT/HỎNG là phán quyết thật.
  2. **Có ngưỡng vật lý** — clipping, DC offset, khoảng lặng. Không cần ai chuẩn
     hoá: một mẫu chạm trần là chạm trần.
  3. **Chỉ so sánh được** — CER, tương đồng người nói, trôi giọng. Một CER 4%
     KHÔNG có nghĩa là tốt hay xấu cho tới khi biết **sàn của chính bộ nhận
     dạng** trên giọng người thật. Nhóm này báo số + `chua_hieu_chuan`.

⛔ `apps/qualitylab` của kho này đã học đúng bài đó và ghi thẳng vào giao diện:
   *"Kết quả foundation dùng để chẩn đoán; chưa được hiệu chuẩn với đánh giá mù
   của con người và không được dùng làm release gate."* Bộ đo này theo cùng luật.

═══════════════════════════════════════════════════════════════════════════════
BẢY NHÓM ĐO, VÀ VÌ SAO TỪNG NHÓM CÓ MẶT
═══════════════════════════════════════════════════════════════════════════════

A. **Hợp đồng kỹ thuật** — giải mã được, tần số lấy mẫu, số kênh, thời lượng.
   Rẻ nhất và bắt được lỗi ngu nhất: một tệp 0 giây vẫn là một tệp hợp lệ.

B. **Toàn vẹn tín hiệu** — true peak, clipping, LUFS, DC offset, nền nhiễu.
   Đây là nhóm DUY NHẤT có tiêu chuẩn ngoài, nên cũng là nhóm duy nhất phán
   quyết được mà không cần hiệu chuẩn.

C. **Khoảng lặng và đứt quãng** — im đầu/cuối, khoảng lặng dài nhất ở giữa.
   🔴 Nhóm này bắt "chunk câm": model sinh ra một đoạn rỗng giữa câu. Upstream
   có chốt `MIN_FRAMES_PER_PHONE = 0.25` cho đường batch, nhưng `infer` đơn lẻ
   KHÔNG đi qua chốt đó — nên phải đo ở đầu ra.

D. **Dễ hiểu** — CER/WER bằng cách cho máy NGHE LẠI tệp vừa sinh rồi so với văn
   bản đã yêu cầu. Đây là phép đo quan trọng nhất của một hệ TTS: mọi thứ khác
   đo *âm thanh*, phép này đo *nó có nói đúng thứ ta bảo không*.

   ⭐ Kèm **tỉ lệ sai DẤU** — một chỉ số riêng cho tiếng Việt mà các bộ đo phổ
      thông không có. "má/mà/mã/mạ" khác nghĩa hoàn toàn; một CER 3% gồm toàn
      lỗi dấu tệ hơn hẳn một CER 3% gồm lỗi phụ âm cuối. Upstream #168 báo đúng
      lớp lỗi này (`ch` ↔ `tr`, đổi giọng vùng miền).

E. **Giữ giọng** — cosine giữa embedding của clip mẫu và của tệp sinh ra.
   ⚠️ Dùng CHÍNH bộ mã hoá của VieNeu, và điều đó vừa đúng vừa có giới hạn: nó
      đo đúng thứ model coi là "cùng một giọng", nên nó **không thấy được** chỗ
      chính bộ mã hoá mù. Đây là phép tự đối chiếu, không phải phép độc lập.

F. **Trôi giọng** — chia tệp thành cửa sổ, tính embedding từng cửa sổ, báo độ
   lệch. 🔴 Đây là phép đo cho upstream #173 (*"giọng đọc giữa các câu giống như
   cùng một người nhưng ở các tâm trạng hoặc cao độ hơi khác nhau"*), và nó là
   thứ duy nhất trong bộ này đo được **chất lượng của một bài dài** thay vì chất
   lượng của một câu.

G. **Đóng dấu** — dấu chìm có đọc lại được không.
   Lời hứa provenance phải kiểm được, nếu không nó là một lời hứa suông — và
   upstream đã hứa suông đúng chỗ này suốt (gói `perth` sai, issue #191).

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import unicodedata

# Console Windows mac dinh cp1252: in mot chu tieng Viet la UnicodeEncodeError,
# va bo do se chet DUNG O BUOC IN — sau khi da do xong het.
#
# 🔴 `reconfigure()`, KHONG phai `sys.stdout = io.TextIOWrapper(...)`.
#
#    Gan mot TextIOWrapper MOI de len cung mot `buffer` la dat mot qua bom hen
#    gio: khi module thu hai lam dung viec do, wrapper cua module thu nhat mat
#    tham chieu, bi thu hoi, va **dong luon buffer ben duoi**. Ca hai cung chet.
#
#    Da no that 31/08/2026: `tools/do_van_ban_dai.py` boc stdout roi `import
#    voice_sidecar.do_chat_luong` boc lan nua. Phep do chay xong sach se, roi
#    dong `print` dau tien nem `ValueError: I/O operation on closed file` —
#    mot thong diep khong he nhac toi ma hoa, tuc no giau ca nguyen nhan lan
#    noi xay ra.
#
#    `reconfigure()` sua tai cho, khong tao doi tuong moi, va goi hai lan vo hai.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── ngưỡng CÓ NGUỒN ─────────────────────────────────────────────────────────
#
# Mỗi hằng số dưới đây kèm nguồn. Một ngưỡng không có nguồn thì không được nằm ở
# đây — nó thuộc nhóm `chua_hieu_chuan` và chỉ được báo số.

#: EBU R128 / ITU-R BS.1770-4: đỉnh thật tối đa −1 dBTP cho phát sóng.
#: Vượt mức này là méo khi qua bộ giải mã có mất dữ liệu (MP3, AAC).
TRAN_TRUE_PEAK_DBTP = -1.0

#: Mục tiêu độ to. −16 LUFS là mức các nền tảng phát trực tuyến chuẩn hoá về cho
#: nội dung giọng nói (Spotify/YouTube ~−14, podcast ~−16). Dải chấp nhận rộng
#: vì chuẩn hoá lại là việc rẻ; lệch QUÁ xa mới là vấn đề.
LUFS_MUC_TIEU = -16.0
LUFS_DUNG_SAI = 6.0

#: Một mẫu |x| >= mức này coi như chạm trần. 0,999 chứ không 1,0: PCM16 làm tròn.
NGUONG_CHAM_TRAN = 0.999
#: Tỉ lệ mẫu chạm trần tối đa còn chấp nhận. Vài mẫu là bình thường; 1% là méo.
TY_LE_CHAM_TRAN_TOI_DA = 0.001

#: DC offset. Vật lý: |trung bình| của một tín hiệu tiếng nói phải quanh 0.
DC_OFFSET_TOI_DA = 0.01

#: Ngưỡng coi là im lặng (RMS trong một khung 20 ms), theo dBFS.
NGUONG_IM_DBFS = -50.0
#: Khoảng lặng GIỮA câu dài hơn mức này là dấu hiệu đứt quãng, không phải nhịp thở.
KHOANG_LANG_GIUA_TOI_DA_S = 1.5

#: Cửa sổ để đo trôi giọng. 3 giây đủ dài cho một embedding ổn định, đủ ngắn để
#: một bài 60 giây có 20 điểm đo.
CUA_SO_TROI_S = 3.0


# ═══════════════════════════════════════════════════════ tiện ích chung ══════

def _db(x: float) -> float:
    return 20.0 * math.log10(max(x, 1e-12))


def _khung_rms(wav, sr: int, khung_ms: float = 20.0):
    import numpy as np
    n = max(1, int(sr * khung_ms / 1000.0))
    du = len(wav) % n
    x = wav[:len(wav) - du] if du else wav
    if len(x) == 0:
        return np.zeros(0, dtype=np.float32), n
    return np.sqrt((x.reshape(-1, n).astype(np.float64) ** 2).mean(axis=1)), n


# ═══════════════════════════════════════════ A. hợp đồng kỹ thuật ════════════

def do_hop_dong(duong: str) -> dict:
    import soundfile as sf
    thong_tin = sf.info(duong)
    wav, sr = sf.read(duong, dtype="float32", always_2d=False)
    if getattr(wav, "ndim", 1) > 1:
        wav = wav.mean(axis=1)
    return {
        "duong": os.path.basename(duong),
        "so_byte": os.path.getsize(duong),
        "dinh_dang": thong_tin.format,
        "subtype": thong_tin.subtype,
        "sample_rate": int(sr),
        "so_kenh": int(thong_tin.channels),
        "giay": round(len(wav) / float(sr), 4) if sr else 0.0,
        "so_mau": int(len(wav)),
    }, wav, int(sr)


# ═══════════════════════════════════════════ B. toàn vẹn tín hiệu ════════════

def do_tin_hieu(wav, sr: int) -> dict:
    import numpy as np

    if len(wav) == 0:
        return {"loi": "tep rong"}

    dinh = float(np.max(np.abs(wav)))
    cham_tran = int(np.sum(np.abs(wav) >= NGUONG_CHAM_TRAN))
    ty_le_tran = cham_tran / len(wav)
    dc = float(np.mean(wav))

    # True peak: lấy mẫu lên 4x rồi đo đỉnh. Đỉnh giữa hai mẫu có thể cao hơn
    # đỉnh mẫu — đó chính là lý do EBU R128 đo dBTP chứ không đo dBFS.
    try:
        from scipy.signal import resample_poly
        tp = float(np.max(np.abs(resample_poly(wav, 4, 1))))
    except Exception:      # noqa: BLE001 - khong co scipy thi bao dinh mau
        tp = dinh

    lufs = None
    try:
        import pyloudnorm as pyln
        lufs = float(pyln.Meter(sr).integrated_loudness(
            np.asarray(wav, dtype=np.float64)))
        if not math.isfinite(lufs):
            lufs = None
    except Exception:      # noqa: BLE001 - thieu pyloudnorm khong lam hong ca bo do
        lufs = None

    rms, _ = _khung_rms(wav, sr)
    if len(rms):
        # Nền nhiễu = mức của 10% khung yên nhất. Nếu không có khung yên nào thì
        # tệp không có khoảng lặng để đo nền — báo None, đừng bịa.
        yen = np.sort(rms)[:max(1, len(rms) // 10)]
        nen = _db(float(np.mean(yen))) if len(rms) >= 10 else None
        tieng = _db(float(np.mean(np.sort(rms)[-max(1, len(rms) // 4):])))
        snr = (tieng - nen) if nen is not None else None
    else:
        nen = snr = None

    return {
        "dinh_mau": round(dinh, 5),
        "true_peak_dbtp": round(_db(tp), 2),
        "so_mau_cham_tran": cham_tran,
        "ty_le_cham_tran": round(ty_le_tran, 6),
        "lufs": round(lufs, 2) if lufs is not None else None,
        "dc_offset": round(dc, 6),
        "nen_nhieu_dbfs": round(nen, 2) if nen is not None else None,
        "snr_uoc_db": round(snr, 2) if snr is not None else None,
    }


# ═══════════════════════════════════════════ C. khoảng lặng, đứt quãng ═══════

def do_khoang_lang(wav, sr: int) -> dict:
    import numpy as np

    rms, n = _khung_rms(wav, sr)
    if not len(rms):
        return {"loi": "khong du mau"}
    nguong = 10 ** (NGUONG_IM_DBFS / 20.0)
    im = rms < nguong
    giay_moi_khung = n / float(sr)

    dau = 0
    while dau < len(im) and im[dau]:
        dau += 1
    cuoi = 0
    while cuoi < len(im) and im[len(im) - 1 - cuoi]:
        cuoi += 1

    # Khoảng lặng GIỮA: bỏ phần đầu/cuối rồi tìm chuỗi im dài nhất.
    giua = im[dau:len(im) - cuoi] if dau + cuoi < len(im) else np.zeros(0, bool)
    dai_nhat = hien_tai = 0
    cac_khoang = []
    for v in giua:
        if v:
            hien_tai += 1
            dai_nhat = max(dai_nhat, hien_tai)
        else:
            if hien_tai:
                cac_khoang.append(hien_tai)
            hien_tai = 0
    if hien_tai:
        cac_khoang.append(hien_tai)

    return {
        "im_dau_s": round(dau * giay_moi_khung, 3),
        "im_cuoi_s": round(cuoi * giay_moi_khung, 3),
        "im_giua_dai_nhat_s": round(dai_nhat * giay_moi_khung, 3),
        "so_khoang_lang_giua": len(cac_khoang),
        "ty_le_im_toan_bo": round(float(np.mean(im)), 4),
    }


# ═══════════════════════════════════════════ D. dễ hiểu (CER/WER/dấu) ════════

_DAU_THANH = "\u0300\u0301\u0303\u0309\u0323"     # huyền sắc ngã hỏi nặng


def _chuan_hoa_so_khop(s: str) -> str:
    """Chuẩn hoá để SO KHỚP — giữ dấu, bỏ hoa/thường và dấu câu.

    ⛔ KHÔNG bỏ dấu. Một bộ đo bỏ dấu trước khi so sẽ chấm "ma" và "mà" là giống
       nhau, tức mù đúng lớp lỗi nguy hiểm nhất của tiếng Việt.
    """
    s = unicodedata.normalize("NFC", (s or "").lower())
    s = re.sub(r"[^\w\s\u00C0-\u1EF9]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _chi_dau(s: str) -> str:
    """Rút RIÊNG chuỗi dấu thanh, giữ nguyên thứ tự.

    "cà phê" -> "\\u0300" (một dấu huyền). So hai chuỗi này cho ra tỉ lệ sai dấu
    độc lập với việc đọc đúng phụ âm/nguyên âm hay không.
    """
    nfd = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in nfd if c in _DAU_THANH)


def _levenshtein(a, b) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    truoc = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        hien = [i]
        for j, cb in enumerate(b, 1):
            hien.append(min(truoc[j] + 1, hien[j - 1] + 1,
                            truoc[j - 1] + (ca != cb)))
        truoc = hien
    return truoc[-1]


def _asr(duong: str, ngon_ngu: str = "vi") -> dict:
    """Cho MÁY NGHE LẠI tệp vừa sinh.

    ⭐ Gọi sang venv NỀN TẢNG (đã có `faster_whisper`) thay vì cài thêm một bản
       whisper nữa vào venv này. Cùng khuôn sidecar mà `apps/autosubvideo` dùng —
       một model ASR gần 1 GB không nên tồn tại hai bản trên cùng một máy.
    """
    py = os.environ.get("LTT_PLATFORM_PYTHON",
                        r"C:\LTTPlatform\venv\Scripts\python.exe")
    if not os.path.isfile(py):
        return {"co": False, "ly_do": f"khong thay {py}"}
    ma = (
        "import sys,json\n"
        "from faster_whisper import WhisperModel\n"
        "m=WhisperModel(sys.argv[2], device='cpu', compute_type='int8')\n"
        # 🔴 `condition_on_previous_text=False`. Mac dinh cua Whisper la True:
        #    moi cua so 30 giay duoc moi lam dieu kien bang ban dich cua cua so
        #    truoc. Tren audio DAI va lap noi dung, no sinh vong lap roi **BO
        #    HAN mot doan** — va no bo o GIUA, nen ban ghi van ket thuc dung
        #    cho, trong y het mot ban ghi day du.
        #
        #    Do that 31/08/2026: ban 2.907 ky tu, ban ghi lai chi phu 74,5% van
        #    ban trong khi PHAN CUOI khop hoan hao. CER bao 29,9% — gan nhu
        #    toan bo con so do la chu BI BO, khong phai chu doc SAI. Ket luan
        #    "ghep lam giam chat luong" rut ra tu do se la sai.
        "seg,_=m.transcribe(sys.argv[1], language=sys.argv[3], beam_size=5,\n"
        "                   condition_on_previous_text=False)\n"
        "print(json.dumps({'text':' '.join(s.text for s in seg)}))\n"
    )
    try:
        r = subprocess.run(
            [py, "-c", ma, duong, os.environ.get("LTT_ASR_MODEL", "small"),
             ngon_ngu],
            capture_output=True, text=True, encoding="utf-8", timeout=900)
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"co": False, "ly_do": f"{type(e).__name__}: {e}"}
    if r.returncode != 0:
        return {"co": False, "ly_do": (r.stderr or "")[-300:]}
    try:
        return {"co": True, "text": json.loads(r.stdout.strip().splitlines()[-1])["text"]}
    except (ValueError, IndexError, KeyError) as e:
        return {"co": False, "ly_do": f"khong doc duoc ket qua ASR: {e}"}


def do_de_hieu(duong: str, text_goc: str, ngon_ngu: str = "vi") -> dict:
    if not text_goc:
        return {"co": False, "ly_do": "khong truyen --text nen khong so duoc"}
    kq = _asr(duong, ngon_ngu)
    if not kq.get("co"):
        return {"co": False, "ly_do": kq.get("ly_do", "?")}

    goc = _chuan_hoa_so_khop(text_goc)
    nghe = _chuan_hoa_so_khop(kq["text"])
    cer = _levenshtein(goc, nghe) / max(1, len(goc))
    wer = _levenshtein(goc.split(), nghe.split()) / max(1, len(goc.split()))

    d_goc, d_nghe = _chi_dau(text_goc), _chi_dau(kq["text"])
    ter = _levenshtein(d_goc, d_nghe) / max(1, len(d_goc)) if d_goc else None

    # ⭐ TỈ LỆ PHỦ. Không có nó thì một bản ghi bị bỏ mất 25% ở giữa vẫn cho ra
    #    một CER trông hoàn toàn bình thường, và người đọc sẽ quy tội cho TTS.
    #    Nó không phải một ngưỡng — nó là **điều kiện để CER có nghĩa**: hai CER
    #    chỉ so được với nhau khi hai lượt phủ xấp xỉ như nhau.
    phu = len(nghe) / max(1, len(goc))

    return {
        "co": True,
        "text_goc": text_goc,
        "text_nghe_lai": kq["text"].strip(),
        "ty_le_phu": round(phu, 4),
        "cer": round(cer, 4),
        "wer": round(wer, 4),
        "ter_sai_dau": round(ter, 4) if ter is not None else None,
        "so_dau_goc": len(d_goc),
        "chua_hieu_chuan": True,
        "ghi_chu": ("CER/WER phu thuoc chat luong bo nhan dang, KHONG chi phu "
                    "thuoc TTS. Muon phan quyet thi phai do SAN cua chinh bo "
                    "nhan dang tren giong nguoi that truoc."
                    + ("" if phu >= 0.95 else
                       f" [!] Ban ghi lai chi phu {phu * 100:.1f}% van ban goc "
                       f"— bo nhan dang da BO mot phan audio, nen CER o day "
                       f"chu yeu do chu BI BO chu khong phai chu doc SAI. "
                       f"Dung so CER nay voi mot luot co ty le phu khac.")),
    }


# ═══════════════════════════════════════════ E/F. giữ giọng và trôi giọng ════

_BO_MA_HOA = None


def _bo_ma_hoa_giong():
    """Bộ mã hoá người nói của VieNeu. `None` nếu không nạp được.

    ⭐ Dùng CHÍNH `speaker_encoder.onnx` mà model dùng khi nhân bản. Đó vừa là
       điểm mạnh vừa là giới hạn, và cả hai phải nói ra — xem `do_giu_giong`.

    Nạp một lần cho cả tiến trình: một bài 60 giây có 20 cửa sổ, nạp lại 20 lần
    là 20 lần đọc một tệp 28 MB.
    """
    global _BO_MA_HOA
    if _BO_MA_HOA is not None:
        return _BO_MA_HOA or None
    try:
        from vieneu._v3_turbo_engine.speaker.onnx_extractor import (
            OnnxSpeakerEncoder)
        from huggingface_hub import hf_hub_download
        duong = hf_hub_download(
            repo_id=os.environ.get("LTT_VOICE_MODEL_REPO",
                                   "pnnbao-ump/VieNeu-TTS-v3-Turbo"),
            filename="speaker_encoder.onnx",
            revision=os.environ.get("LTT_VOICE_MODEL_REV") or None)
        _BO_MA_HOA = OnnxSpeakerEncoder(duong)
    except Exception:      # noqa: BLE001 - khong co model thi bo qua nhom nay,
        _BO_MA_HOA = False  #                khong lam hong ca bo do
    return _BO_MA_HOA or None


def _embed(bo, wav, sr: int):
    """Embedding người nói. `None` khi đoạn quá ngắn hoặc bộ mã hoá từ chối."""
    import numpy as np
    try:
        v = bo.embed(np.asarray(wav, dtype=np.float32), sr)
    except TypeError:
        try:
            v = bo.embed(np.asarray(wav, dtype=np.float32))
        except Exception:      # noqa: BLE001
            return None
    except Exception:          # noqa: BLE001
        return None
    return np.asarray(v, dtype=np.float32).reshape(-1)


def _cosine(a, b) -> float:
    import numpy as np
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def do_giu_giong(wav, sr: int, duong_ref: str | None) -> dict:
    if not duong_ref:
        return {"co": False, "ly_do": "khong truyen --ref"}
    bo = _bo_ma_hoa_giong()
    if bo is None:
        return {"co": False, "ly_do": "khong nap duoc bo ma hoa nguoi noi cua VieNeu"}
    import soundfile as sf
    ref, sr_ref = sf.read(duong_ref, dtype="float32", always_2d=False)
    if getattr(ref, "ndim", 1) > 1:
        ref = ref.mean(axis=1)
    e_ref, e_ra = _embed(bo, ref, sr_ref), _embed(bo, wav, sr)
    if e_ref is None or e_ra is None:
        return {"co": False, "ly_do": "bo ma hoa khong tra ve embedding"}
    return {
        "co": True,
        "cosine": round(_cosine(e_ref, e_ra), 4),
        "chua_hieu_chuan": True,
        "ghi_chu": ("Dung CHINH bo ma hoa cua VieNeu, nen day la phep TU DOI "
                    "CHIEU: no do dung thu model coi la 'cung mot giong', va vi "
                    "the KHONG thay duoc cho chinh bo ma hoa mu. Muon phan quyet "
                    "thi phai co phan bo cung-nguoi/khac-nguoi de so."),
    }


def do_troi_giong(wav, sr: int) -> dict:
    """🔴 Phép đo cho upstream #173 — trôi giọng giữa các đoạn của một bài dài."""
    import numpy as np

    n = int(CUA_SO_TROI_S * sr)
    if len(wav) < 2 * n:
        return {"co": False,
                "ly_do": f"tep ngan hon {2 * CUA_SO_TROI_S:.0f} giay, khong do troi duoc"}
    bo = _bo_ma_hoa_giong()
    if bo is None:
        return {"co": False, "ly_do": "khong nap duoc bo ma hoa nguoi noi"}

    embs, f0s = [], []
    for i in range(0, len(wav) - n + 1, n):
        cua = wav[i:i + n]
        e = _embed(bo, cua, sr)
        if e is not None:
            embs.append(e)
        try:
            import librosa
            f0 = librosa.yin(cua, fmin=60, fmax=400, sr=sr)
            f0 = f0[np.isfinite(f0)]
            if len(f0):
                f0s.append(float(np.median(f0)))
        except Exception:      # noqa: BLE001 - thieu librosa thi bo phan cao do
            pass

    if len(embs) < 2:
        return {"co": False, "ly_do": "khong du cua so de so"}

    cap = [_cosine(embs[i], embs[j])
           for i in range(len(embs)) for j in range(i + 1, len(embs))]
    ra = {
        "co": True,
        "so_cua_so": len(embs),
        "cua_so_giay": CUA_SO_TROI_S,
        "cosine_trung_binh": round(float(np.mean(cap)), 4),
        "cosine_thap_nhat": round(float(np.min(cap)), 4),
        "cosine_lech_chuan": round(float(np.std(cap)), 4),
        "chua_hieu_chuan": True,
        "ghi_chu": ("`cosine_thap_nhat` la con so dang nhin: mot bai troi giong "
                    "co trung binh van cao trong khi HAI cua so xa nhau da lech "
                    "han. Trung binh giau dung thu can tim."),
    }
    if len(f0s) >= 2:
        ra["cao_do_median_hz"] = round(float(np.median(f0s)), 1)
        ra["cao_do_lech_chuan_hz"] = round(float(np.std(f0s)), 1)
        ra["cao_do_bien_do_hz"] = round(float(np.max(f0s) - np.min(f0s)), 1)
    return ra


# ═══════════════════════════════════════════ G. đóng dấu ═════════════════════

def do_watermark(wav, sr: int) -> dict:
    try:
        import numpy as np
        import perth
    except Exception as e:      # noqa: BLE001
        return {"co": False, "ly_do": f"khong nap duoc perth: {e}"}
    if not hasattr(perth, "PerthImplicitWatermarker"):
        return {"co": False, "ly_do": ("goi `perth` dang cai KHONG phai "
                                       "watermarker (xem upstream #191)")}
    try:
        import numpy as np
        v = perth.PerthImplicitWatermarker().get_watermark(
            np.asarray(wav, dtype=np.float32), sample_rate=sr)
        return {"co": True, "doc_lai_duoc": round(float(np.mean(v)), 4)}
    except Exception as e:      # noqa: BLE001
        return {"co": False, "ly_do": f"{type(e).__name__}: {e}"}


# ═══════════════════════════════════════════ phán quyết ══════════════════════

def phan_quyet(kq: dict) -> dict:
    """ĐẠT/HỎNG **chỉ** cho phép đo có ngưỡng nguồn. Còn lại: báo số."""
    muc = []

    def them(ten, dat, chi_tiet, nguon):
        muc.append({"ten": ten, "dat": dat, "chi_tiet": chi_tiet, "nguon": nguon})

    hd, th, kl = kq["hop_dong"], kq["tin_hieu"], kq["khoang_lang"]

    them("Giải mã được", hd["giay"] > 0,
         f"{hd['giay']}s @ {hd['sample_rate']} Hz, {hd['so_kenh']} kênh",
         "vật lý")

    if th.get("true_peak_dbtp") is not None:
        dat = th["true_peak_dbtp"] <= TRAN_TRUE_PEAK_DBTP
        them("Đỉnh thật", dat,
             f"{th['true_peak_dbtp']} dBTP (trần {TRAN_TRUE_PEAK_DBTP})",
             "EBU R128 / ITU-R BS.1770-4")

    them("Không vỡ tiếng", th.get("ty_le_cham_tran", 0) <= TY_LE_CHAM_TRAN_TOI_DA,
         f"{th.get('so_mau_cham_tran', 0)} mẫu chạm trần "
         f"({th.get('ty_le_cham_tran', 0) * 100:.4f}%)", "vật lý")

    if th.get("lufs") is not None:
        lech = abs(th["lufs"] - LUFS_MUC_TIEU)
        them("Độ to", lech <= LUFS_DUNG_SAI,
             f"{th['lufs']} LUFS (mục tiêu {LUFS_MUC_TIEU} ± {LUFS_DUNG_SAI})",
             "ITU-R BS.1770-4, mục tiêu theo thông lệ phát trực tuyến")

    them("DC offset", abs(th.get("dc_offset", 0)) <= DC_OFFSET_TOI_DA,
         f"{th.get('dc_offset', 0):.6f}", "vật lý")

    if "im_giua_dai_nhat_s" in kl:
        them("Không đứt quãng",
             kl["im_giua_dai_nhat_s"] <= KHOANG_LANG_GIUA_TOI_DA_S,
             f"khoảng lặng giữa dài nhất {kl['im_giua_dai_nhat_s']}s "
             f"(trần {KHOANG_LANG_GIUA_TOI_DA_S}s)",
             "vật lý — dài hơn nhịp thở là đứt quãng")

    wm = kq.get("watermark", {})
    if wm.get("co"):
        them("Đóng dấu chìm", True, f"đọc lại được {wm['doc_lai_duoc']}",
             "lời hứa provenance của sản phẩm")

    hong = [m for m in muc if not m["dat"]]
    return {
        "muc": muc,
        "so_dat": len(muc) - len(hong),
        "so_muc": len(muc),
        "ket_luan": "DAT" if not hong else "HONG",
        "hong": [m["ten"] for m in hong],
        "pham_vi": ("Phan quyet nay CHI phu cac muc co nguong co nguon. CER, "
                    "tuong dong nguoi noi va troi giong duoc BAO SO va danh dau "
                    "`chua_hieu_chuan` — chung khong tham gia ket luan."),
    }


# ═══════════════════════════════════════════ chạy ════════════════════════════

#: Phiên bản BỘ ĐO. Baseline của cổng V10 khoá theo `(PHIEN_BAN_THAM_SO, cái
#: này)` — đổi cách đo là baseline cũ hết hiệu lực, phải đo lại.
#:
#: 🔴 Nó phải là một biến **cấp module**. Trước 01/09 con số này nằm thẳng
#:    trong dict trả về, còn `tools/cong_chat_luong_voice.py` thì tra
#:    `do_tat_ca.__globals__["_PHIEN_BAN_BO_DO"]` — một tên **không tồn tại** —
#:    rồi rơi vào giá trị mặc định cứng. Tức cái ghim vẫn ở đó, vẫn in ra, và
#:    **không nối vào gì cả**: đổi hẳn cách đo mà baseline cũ vẫn được coi là
#:    hợp lệ. Cùng lớp lỗi với một bánh cóc chưa từng đỏ.
_PHIEN_BAN_BO_DO = "ltt-voice-do-2026-09-01a"


def do_tat_ca(duong: str, *, text: str = "", ref: str = "",
              ngon_ngu: str = "vi", bo_qua_asr: bool = False) -> dict:
    from voice_sidecar import do_on_dinh

    hop_dong, wav, sr = do_hop_dong(duong)
    kq = {
        "phien_ban_bo_do": _PHIEN_BAN_BO_DO,
        "hop_dong": hop_dong,
        "tin_hieu": do_tin_hieu(wav, sr),
        "khoang_lang": do_khoang_lang(wav, sr),
        "watermark": do_watermark(wav, sr),
        "giu_giong": do_giu_giong(wav, sr, ref or None),
        "troi_giong": do_troi_giong(wav, sr),
        # K3: bốn phép bịt điểm mù đã đo được — xem `do_on_dinh.py`.
        "on_dinh": do_on_dinh.do_tat_ca(wav, sr),
    }
    kq["de_hieu"] = ({"co": False, "ly_do": "bo qua theo yeu cau"}
                     if bo_qua_asr else do_de_hieu(duong, text, ngon_ngu))
    kq["phan_quyet"] = phan_quyet(kq)
    return kq


def _in_dep(kq: dict) -> None:
    pq = kq["phan_quyet"]
    print(f"\n{'=' * 72}\n  {kq['hop_dong']['duong']}  "
          f"({kq['hop_dong']['giay']}s @ {kq['hop_dong']['sample_rate']} Hz)\n{'=' * 72}")
    print(f"\nPHAN QUYET: {pq['ket_luan']}  ({pq['so_dat']}/{pq['so_muc']} muc co nguong)")
    for m in pq["muc"]:
        print(f"  [{'OK ' if m['dat'] else 'HONG'}] {m['ten']:22} {m['chi_tiet']}")
        print(f"         nguon: {m['nguon']}")

    print("\nDO DUOC, CHUA HIEU CHUAN (khong tham gia phan quyet):")
    dh = kq["de_hieu"]
    if dh.get("co"):
        print(f"  phu {dh.get('ty_le_phu', 0):.1%} van ban goc"
              + ("" if dh.get('ty_le_phu', 1) >= 0.95 else
                 "  <- BO NHAN DANG BO BOT, CER duoi day khong so duoc voi luot khac"))
        print(f"  CER {dh['cer']:.2%}  WER {dh['wer']:.2%}  "
              f"sai dau {dh['ter_sai_dau']:.2%}" if dh.get("ter_sai_dau") is not None
              else f"  CER {dh['cer']:.2%}  WER {dh['wer']:.2%}")
        print(f"    nghe lai: {dh['text_nghe_lai'][:88]}")
    else:
        print(f"  de hieu     : KHONG DO DUOC — {dh.get('ly_do')}")

    gg = kq["giu_giong"]
    print(f"  giu giong   : cosine {gg['cosine']}" if gg.get("co")
          else f"  giu giong   : KHONG DO DUOC — {gg.get('ly_do')}")

    tg = kq["troi_giong"]
    if tg.get("co"):
        print(f"  troi giong  : thap nhat {tg['cosine_thap_nhat']}  "
              f"tb {tg['cosine_trung_binh']}  lech {tg['cosine_lech_chuan']}  "
              f"({tg['so_cua_so']} cua so)")
        if "cao_do_lech_chuan_hz" in tg:
            print(f"                cao do {tg['cao_do_median_hz']} Hz  "
                  f"lech {tg['cao_do_lech_chuan_hz']} Hz  "
                  f"bien do {tg['cao_do_bien_do_hz']} Hz")
    else:
        print(f"  troi giong  : KHONG DO DUOC — {tg.get('ly_do')}")
    print(f"\n{pq['pham_vi']}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bo do chat luong tep tieng noi.")
    ap.add_argument("duong")
    ap.add_argument("--text", default="", help="Van ban da yeu cau doc (de tinh CER).")
    ap.add_argument("--ref", default="", help="Clip mau, de do giu giong.")
    ap.add_argument("--ngon-ngu", default="vi")
    ap.add_argument("--bo-qua-asr", action="store_true")
    ap.add_argument("--json", default="", help="Ghi ket qua day du ra tep JSON.")
    # ⚠️ `--text` đi qua dòng lệnh, và trên Windows dòng lệnh **đổi bảng mã**:
    #    PowerShell 5.1 đưa tham số cho `.exe` theo bảng mã ANSI của máy, nên
    #    "Chào" tới Python thành "Ch├áo". CER tính trên văn bản đã méo vẫn ra
    #    một con số trông hợp lệ — chỉ là nó đo sai thứ. Đọc từ TỆP UTF-8 thì
    #    không đi qua chỗ đổi bảng mã nào cả.
    ap.add_argument("--text-tep", default="",
                    help="Doc van ban tu tep UTF-8 (an toan hon --text tren Windows).")
    a = ap.parse_args(argv)

    text = a.text
    if a.text_tep:
        if a.text:
            print("Chi duoc mot trong --text va --text-tep.", file=sys.stderr)
            return 2
        with open(a.text_tep, encoding="utf-8") as f:
            text = f.read().strip()

    if not os.path.isfile(a.duong):
        print(f"khong thay {a.duong}", file=sys.stderr)
        return 2

    kq = do_tat_ca(a.duong, text=text, ref=a.ref, ngon_ngu=a.ngon_ngu,
                   bo_qua_asr=a.bo_qua_asr)
    _in_dep(kq)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(kq, f, ensure_ascii=False, indent=2)
        print(f"Da ghi: {a.json}")
    return 0 if kq["phan_quyet"]["ket_luan"] == "DAT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
