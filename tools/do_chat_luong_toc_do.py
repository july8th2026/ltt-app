r"""do_chat_luong_toc_do.py — đo chất lượng giọng Ở BIÊN SPEED, trên bản ĐÃ kéo giãn.

    C:\LTTPlatform\venv\Scripts\python.exe tools\do_chat_luong_toc_do.py \
        --ra test-results\voice-acceptance\chat_luong_toc_do.jsonl

Chạy qua một lớp nạp `app.env` (cần `LTT_VOICE_SIDECAR_TOKEN` để gọi sidecar) —
xem `setup\chay_thu_giong.ps1` cho khuôn nạp env; hoặc đặt env sẵn.

## Câu hỏi tệp này trả lời

D01/PA2 (2026-09-13) nới `speed` ra **[0.5, 2.0]** rồi bảo *"đo chất lượng ở
biên"*. Chưa ai đo, và có một lý do KIẾN TRÚC khiến chưa ai đo:

  `toc_do.py` ràng buộc ② — cổng chất lượng đo **TRƯỚC** khi kéo giãn, vì
  time-stretch làm lệch mọi phép đo F0. Nên cổng V10 (`cong_chat_luong_voice`)
  đo bản CHƯA kéo giãn. Câu *"atempo ở 0.5/2.0 có làm tụt chất lượng không"* thì
  phải đo bản ĐÃ kéo giãn — đúng thứ tệp này làm, và CHỈ tệp này.

## Không tự chế metric (quy tắc mục 20/24/36 của chiến dịch)

  · Naturalness  → **DNSMOS P.835** (`voice_sidecar/dnsmos.py`, model Microsoft
                   CC-BY-4.0, ghim commit+sha). SIG/BAK/OVRL thang MOS 1–5.
  · Intelligibility → **ASR CER/WER/TER** (`do_chat_luong.do_de_hieu`, dùng
                   faster-whisper). VI và EN đo riêng.

## Cách đọc kết quả (mục 24 — đo phân phối, KHÔNG bịa ngưỡng)

Tổng hợp MỖI câu MỘT lần (speed là hậu kỳ, không tốn thêm GPU), rồi áp từng
speed. So OVRL/CER ở mỗi speed với **speed 1.0 của chính câu ấy** (đối chứng nội
bộ, khử khác biệt giữa câu). `delta_ovrl_vs_1x < ~0` ở biên = atempo hại chất
lượng ở biên; ~0 = biên an toàn. Ngưỡng CHỈ đề xuất sau khi thấy phân phối.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

#: Corpus cố định, KHÔNG chứa bí mật/dữ liệu khách (mục 23). Nhỏ có chủ ý: đây là
#: phép thăm dò biên, không phải bộ đo đầy đủ.
CORPUS = [
    ("vi", "Xin chào, đây là giọng đọc thử của LTT Studios."),
    ("vi", "Hôm nay trời nắng đẹp, chúng tôi bắt đầu lúc chín giờ sáng."),
    ("vi", "Một triệu năm trăm nghìn đồng cho ba sản phẩm khác nhau."),
    ("en", "The quick brown fox jumps over the lazy dog near the river."),
    ("en", "Please confirm your order before the end of business today."),
]

SPEEDS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _synth(text: str, preset: str):
    """Một lượt tổng hợp qua sidecar. Trả `(wav_bytes, headers)`.

    ⛔ Gọi THẲNG `sidecar_client.noi` (chỉ cần `requests`), KHÔNG qua
       `features.goi_cong` — cái sau kéo `platform_core.jobs` → `sqlalchemy`,
       không có trong `vieneu-venv` (venv DUY NHẤT có onnxruntime + soundfile cho
       DNSMOS). Harness này phải chạy trọn trong một venv, và vieneu-venv là venv
       đó; nên đường tổng hợp phải nhẹ đúng bằng một lời gọi HTTP.
    """
    from apps.ltt_voice import sidecar_client
    return sidecar_client.noi(text, preset=preset)


def _dnsmos(wav_bytes: bytes) -> dict | None:
    from voice_sidecar import dnsmos
    if not dnsmos.co_san():
        return None
    try:
        import io
        import soundfile as sf
        wav, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32", always_2d=False)
        if getattr(wav, "ndim", 1) > 1:
            wav = wav.mean(axis=1)
        return dnsmos.cham(wav, int(sr))
    except Exception as e:  # noqa: BLE001 - thieu onnxruntime/scipy -> degrade, khong crash
        print(f"    (DNSMOS bo qua: {type(e).__name__}: {str(e)[:60]})")
        return None


def _asr(wav_bytes: bytes, text: str, lang: str) -> dict | None:
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        f.write(wav_bytes)
        f.close()
        from voice_sidecar.do_chat_luong import do_de_hieu
        return do_de_hieu(f.name, text, lang)
    except Exception as e:  # noqa: BLE001 - ASR loi (thieu venv whisper...) -> degrade
        print(f"    (ASR bo qua: {type(e).__name__}: {str(e)[:60]})")
        return None
    finally:
        try:
            os.unlink(f.name)
        except OSError:
            pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="", help="Ten preset. Bo trong = mac dinh.")
    ap.add_argument("--ra", default="", help="Duong ghi JSONL. Bo trong = chi in.")
    ap.add_argument("--bo-asr", action="store_true", help="Bo qua ASR (chi DNSMOS).")
    a = ap.parse_args(argv)

    from apps.ltt_voice import giong_mau, sidecar_client, toc_do

    if not sidecar_client.san_sang():
        print("DUNG: sidecar chua san sang (thieu LTT_VOICE_SIDECAR_TOKEN). "
              "Chay qua lop nap app.env.")
        return 2

    preset = a.preset or giong_mau.MAC_DINH
    from voice_sidecar import dnsmos
    if not dnsmos.co_san():
        print("CANH BAO: chua co model DNSMOS (tai qua voice_sidecar/tai_dnsmos.py). "
              "Se bo qua naturalness, chi do ASR.")

    ban_ghi = []
    fout = open(a.ra, "w", encoding="utf-8", newline="\n") if a.ra else None
    try:
        for i, (lang, text) in enumerate(CORPUS):
            # Tong hop MOT lan cho ca cau (speed la hau ky).
            try:
                wav_goc, _ = _synth(text, preset)
            except Exception as e:  # noqa: BLE001
                print(f"[{i}] LOI tong hop: {type(e).__name__}: {e}")
                continue
            th = _sha256(text.encode("utf-8"))[:16]
            print(f"\n[{i}] {lang} | {text[:48]}... | preset={preset}")
            for sp in SPEEDS:
                wav_sp = toc_do.ap_dung(wav_goc, sp)
                dns = _dnsmos(wav_sp)
                asr = None if a.bo_asr else _asr(wav_sp, text, lang)
                rec = {
                    "test_id": f"QTD-{i}-{sp}",
                    "lang": lang,
                    "text_hash": th,
                    "preset": preset,
                    "speed": sp,
                    "audio_sha256": _sha256(wav_sp),
                    "dnsmos": dns,
                    "cer": (asr or {}).get("cer") if asr else None,
                    "wer": (asr or {}).get("wer") if asr else None,
                    "ter_sai_dau": (asr or {}).get("ter_sai_dau") if asr else None,
                    "ty_le_phu": (asr or {}).get("ty_le_phu") if asr else None,
                }
                ban_ghi.append(rec)
                if fout:
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fout.flush()
                ovrl = (dns or {}).get("ovrl")
                cer = rec["cer"]
                print(f"    speed {sp:<4} OVRL={ovrl!s:<6} CER={cer!s:<8} "
                      f"phu={rec['ty_le_phu']}")
    finally:
        if fout:
            fout.close()

    _tong_hop(ban_ghi)
    return 0


def _tong_hop(ban_ghi: list) -> None:
    """Phan phoi + delta so voi speed 1.0 CUA CHINH CAU (doi chung noi bo)."""
    import statistics as st

    print("\n" + "=" * 62)
    print("PHAN PHOI theo speed (median tren corpus) — mục 24, chua dat nguong")
    print("=" * 62)
    # Goc 1.0 theo (text_hash) de tinh delta noi bo.
    goc = {r["text_hash"]: r for r in ban_ghi if r["speed"] == 1.0}
    theo_speed: dict = {}
    for r in ban_ghi:
        theo_speed.setdefault(r["speed"], []).append(r)

    print(f"{'speed':>6} {'OVRL_med':>9} {'dOVRL_1x':>9} {'CER_med':>9} {'dCER_1x':>9}")
    for sp in sorted(theo_speed):
        rs = theo_speed[sp]
        ovrls = [r["dnsmos"]["ovrl"] for r in rs
                 if r.get("dnsmos") and r["dnsmos"].get("ovrl") is not None]
        cers = [r["cer"] for r in rs if r.get("cer") is not None]
        d_ovrl = [r["dnsmos"]["ovrl"] - goc[r["text_hash"]]["dnsmos"]["ovrl"]
                  for r in rs
                  if r.get("dnsmos") and goc.get(r["text_hash"], {}).get("dnsmos")]
        d_cer = [r["cer"] - goc[r["text_hash"]]["cer"] for r in rs
                 if r.get("cer") is not None
                 and goc.get(r["text_hash"], {}).get("cer") is not None]
        print(f"{sp:>6} "
              f"{(round(st.median(ovrls),3) if ovrls else '-')!s:>9} "
              f"{(round(st.median(d_ovrl),3) if d_ovrl else '-')!s:>9} "
              f"{(round(st.median(cers),4) if cers else '-')!s:>9} "
              f"{(round(st.median(d_cer),4) if d_cer else '-')!s:>9}")
    print("\n⇒ Doc: dOVRL_1x ~0 o bien = atempo KHONG hai naturalness o bien do.")
    print("  dCER_1x ~0 = van de-hieu. Am ro ret o 0.5/2.0 = de xuat thu hep dai.")


if __name__ == "__main__":
    raise SystemExit(main())
