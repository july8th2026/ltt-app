"""
do_v1.py — lô đo V1. Chạy TRONG `vieneu-venv`, không import `platform_core`.

    python -m voice_sidecar.do_v1 --ra docs/LTT_VOICE/do_v1.json

Bốn con số phải điền (Q118/Q119 treo vào chúng):

    1. VRAM đỉnh trên 5060 Ti      -> `gpu_vram_mb` trong manifest
    2. RTF và TTFA trên GPU        -> giá, và `max_runtime_s`
    3. Ngưỡng ký tự trước khi trôi -> chốt `TRAN_KY_TU_MOT_LUOT`
    4. Watermark có áp không       -> ta được nói gì về provenance

⭐ GHI KẾT QUẢ SAU MỖI PHÉP ĐO, và bỏ qua phép đã xong khi chạy lại.
   Bài học từ lô đo máy B (`tests/test_266_tiep_tuc_lo_do.py`): một lần khởi động
   lại giữa chừng chỉ được phép mất **đúng một phép đo**, không phải cả lô.

⛔ ĐO HAI LẦN: một lần máy rảnh, một lần **trong lúc GPU đang bận việc khác**.
   Đo lúc rảnh rồi công bố là công bố một con số không bao giờ xảy ra trong đời
   thật — máy A chạy `autosubvideo` (~6 GB) và `upscalevideo` (2/12 GB) trên
   chính hai card này.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import statistics
import subprocess
import sys
import time

# ── ngữ liệu: mỗi mục nhắm một ô đã biết là hay hỏng ─────────────────────────
NGU_LIEU = [
    ("vi_ngan", "Xin chào, đây là giọng đọc thử của LTT Studios."),
    ("en_ngan", "This is a short English sentence to check pronunciation."),
    ("tron_vi_en", "Chúng tôi dùng API để gọi model text to speech trên server."),
    # Ô mà pack V2 nêu đích danh, và ô mà upstream #168 báo sai.
    ("so_tien_ngay", "Doanh thu tháng 8 đạt 1.500.000 đồng, tăng 12% so với "
                     "ngày 12/08/2026, lúc 14h30."),
    ("danh_sach", "1. Mở ứng dụng.\n2. Chọn giọng đọc.\n3. Bấm tạo tiếng."),
    ("ch_tr", "Chưởng môn phái Thiếu Lâm trò chuyện cùng trưởng lão."),
    ("viet_tat", "Bạn cần một GPU và một API key để chạy AI trên máy."),
]

#: Bậc độ dài để tìm ngưỡng trôi giọng. #168 báo trôi từ ~3.000 ký tự.
BAC_DO_DAI = [500, 1000, 1500, 2000, 3000]

_CAU_MAU = ("Công nghệ tổng hợp giọng nói đang thay đổi cách người ta làm nội "
            "dung số mỗi ngày. ")


def van_ban_dai(n: int) -> str:
    return (_CAU_MAU * (n // len(_CAU_MAU) + 1))[:n]


def _nvidia_smi_free_mb() -> list:
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=False)
        return [tuple(int(x.strip()) for x in d.split(","))
                for d in r.stdout.strip().splitlines() if d.strip()]
    except Exception:  # noqa: BLE001
        return []


class So:
    """Gom kết quả và ghi ra đĩa **sau mỗi phép đo**."""

    def __init__(self, duong: pathlib.Path):
        self.duong = duong
        self.data = {"phep": {}}
        if duong.exists():
            try:
                self.data = json.loads(duong.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
        self.data.setdefault("phep", {})

    def da_co(self, ten: str) -> bool:
        return ten in self.data["phep"]

    def ghi(self, ten: str, gia_tri: dict) -> None:
        self.data["phep"][ten] = gia_tri
        self.duong.parent.mkdir(parents=True, exist_ok=True)
        self.duong.write_text(json.dumps(self.data, ensure_ascii=False, indent=2),
                              encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", default="docs/LTT_VOICE/do_v1.json")
    ap.add_argument("--backend", default="pytorch",
                    choices=["pytorch", "onnx", "auto"])
    ap.add_argument("--device", default="auto")
    ap.add_argument("--nhan", default="ranh",
                    help="Nhãn điều kiện đo: 'ranh' hay 'gpu-ban'.")
    ap.add_argument("--lap", type=int, default=10,
                    help="Số lượt lặp để đo độ ổn định.")
    args = ap.parse_args(argv)

    ra = pathlib.Path(args.ra)
    so = So(ra)
    tien_to = f"{args.nhan}.{args.backend}"

    import numpy as np

    # ── nạp ──────────────────────────────────────────────────────────────────
    truoc = _nvidia_smi_free_mb()
    t0 = time.perf_counter()
    from vieneu import Vieneu
    tts = Vieneu(mode="v3turbo", backend=args.backend, device=args.device)
    nap_giay = time.perf_counter() - t0
    sau = _nvidia_smi_free_mb()

    import torch
    vram_torch = int(torch.cuda.memory_allocated() / 2**20) if torch.cuda.is_available() else 0
    vram_smi = 0
    if truoc and sau and len(truoc) == len(sau):
        vram_smi = max(s[0] - t[0] for s, t in zip(sau, truoc))

    sr = int(getattr(tts, "sample_rate", 48000))
    co_wm = getattr(tts, "watermarker", None) is not None

    so.ghi(f"{tien_to}.nap", {
        "nap_giay": round(nap_giay, 2),
        "backend": getattr(tts, "backend", "?"),
        "device": str(getattr(getattr(tts, "engine", None), "device", "?")),
        "sample_rate": sr,
        "vram_torch_mb": vram_torch,
        "vram_nvidia_smi_mb": vram_smi,
        "watermark_nap_duoc": co_wm,
        "co_infer_stream": callable(getattr(getattr(tts, "engine", None),
                                            "infer_stream", None)),
        "gpu_truoc": truoc, "gpu_sau": sau,
    })
    print(f"[nap] {nap_giay:.1f}s backend={getattr(tts,'backend','?')} "
          f"vram_torch={vram_torch}MB vram_smi={vram_smi}MB watermark={co_wm}")

    tham = dict(temperature=0.8, top_k=25, top_p=0.95, repetition_penalty=1.2)

    def mot_luot(text: str) -> tuple:
        t = time.perf_counter()
        wav = tts.infer(text, **tham)
        giay_gen = time.perf_counter() - t
        wav = np.asarray(wav, dtype=np.float32)
        giay_am = len(wav) / float(sr)
        return wav, giay_gen, giay_am

    # ── ma trận khói ─────────────────────────────────────────────────────────
    for ten, text in NGU_LIEU:
        khoa = f"{tien_to}.ngu_lieu.{ten}"
        if so.da_co(khoa):
            print(f"[bo qua] {khoa}")
            continue
        try:
            wav, gen, am = mot_luot(text)
            dinh = float(np.max(np.abs(wav))) if wav.size else 0.0
            so.ghi(khoa, {"so_ky_tu": len(text), "gen_s": round(gen, 3),
                          "audio_s": round(am, 3),
                          "rtf": round(gen / am, 4) if am else None,
                          "dinh": round(dinh, 4), "ok": True})
            print(f"[{ten}] {len(text)}ky_tu gen={gen:.2f}s audio={am:.2f}s "
                  f"rtf={gen/am if am else 0:.3f}")
        except Exception as e:  # noqa: BLE001 - lô đo phải sống sót một phép hỏng
            so.ghi(khoa, {"ok": False, "loi": f"{type(e).__name__}: {e}"})
            print(f"[{ten}] HONG: {e}")

    # ── VRAM đỉnh ────────────────────────────────────────────────────────────
    khoa = f"{tien_to}.vram_dinh"
    if not so.da_co(khoa) and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        mot_luot(van_ban_dai(1500))
        so.ghi(khoa, {
            "dinh_mb": int(torch.cuda.max_memory_allocated() / 2**20),
            "dat_truoc_mb": int(torch.cuda.max_memory_reserved() / 2**20),
            "smi_sau": _nvidia_smi_free_mb(),
        })
        print(f"[vram] dinh={int(torch.cuda.max_memory_allocated()/2**20)}MB "
              f"dat_truoc={int(torch.cuda.max_memory_reserved()/2**20)}MB")

    # ── bậc độ dài (tìm ngưỡng trôi) ─────────────────────────────────────────
    for n in BAC_DO_DAI:
        khoa = f"{tien_to}.do_dai.{n}"
        if so.da_co(khoa):
            continue
        try:
            wav, gen, am = mot_luot(van_ban_dai(n))
            so.ghi(khoa, {"so_ky_tu": n, "gen_s": round(gen, 2),
                          "audio_s": round(am, 2),
                          "rtf": round(gen / am, 4) if am else None,
                          "ky_tu_moi_giay": round(n / am, 2) if am else None,
                          "ok": True})
            print(f"[dai {n}] gen={gen:.1f}s audio={am:.1f}s "
                  f"rtf={gen/am if am else 0:.3f} "
                  f"ky_tu/giay={n/am if am else 0:.1f}")
        except Exception as e:  # noqa: BLE001
            so.ghi(khoa, {"so_ky_tu": n, "ok": False,
                          "loi": f"{type(e).__name__}: {e}"})
            print(f"[dai {n}] HONG: {e}")

    # ── ổn định: lặp cùng một câu ────────────────────────────────────────────
    khoa = f"{tien_to}.on_dinh"
    if not so.da_co(khoa):
        rtfs, ams = [], []
        for _ in range(max(2, args.lap)):
            _, gen, am = mot_luot(NGU_LIEU[0][1])
            if am:
                rtfs.append(gen / am)
                ams.append(am)
        so.ghi(khoa, {
            "so_lan": len(rtfs),
            "rtf_trung_binh": round(statistics.mean(rtfs), 4),
            "rtf_lech_chuan": round(statistics.pstdev(rtfs), 4),
            "audio_s_trung_binh": round(statistics.mean(ams), 3),
            "audio_s_lech_chuan": round(statistics.pstdev(ams), 3),
        })
        print(f"[on dinh] rtf={statistics.mean(rtfs):.3f} "
              f"+/-{statistics.pstdev(rtfs):.3f} tren {len(rtfs)} luot")

    # ── TTFA qua streaming ───────────────────────────────────────────────────
    khoa = f"{tien_to}.ttfa"
    if not so.da_co(khoa):
        try:
            t = time.perf_counter()
            dau = None
            tong = 0
            so_chunk = 0
            for chunk in tts.infer_stream(NGU_LIEU[0][1], **tham):
                if chunk is None or len(chunk) == 0:
                    continue
                if dau is None:
                    dau = time.perf_counter() - t
                so_chunk += 1
                tong += len(chunk)
            gen = time.perf_counter() - t
            am = tong / float(sr)
            so.ghi(khoa, {"ttfa_ms": round((dau or 0) * 1000, 1),
                          "so_chunk": so_chunk, "audio_s": round(am, 3),
                          "rtf": round(gen / am, 4) if am else None, "ok": True})
            print(f"[ttfa] {(dau or 0)*1000:.0f}ms qua {so_chunk} chunk")
        except Exception as e:  # noqa: BLE001
            so.ghi(khoa, {"ok": False, "loi": f"{type(e).__name__}: {e}"})
            print(f"[ttfa] HONG: {e}")

    # ── watermark: ĐO TRÊN TỆP RA, không tin cờ ──────────────────────────────
    #
    # 🔴 Đây là chốt của R3. Upstream đặt `self.watermarker = None` rồi trả wav
    #    nguyên xi, nên một biến `co_wm=True` ở trên MỚI CHỈ nói rằng object tồn
    #    tại. Bằng chứng duy nhất đáng tin là **lấy lại được dấu từ sóng âm**.
    khoa = f"{tien_to}.watermark"
    if not so.da_co(khoa):
        kq = {"nap_duoc": co_wm}
        try:
            wav_co = tts.infer(NGU_LIEU[0][1], apply_watermark=True, **tham)
            wav_khong = tts.infer(NGU_LIEU[0][1], apply_watermark=False, **tham)
            kq["hai_ban_khac_nhau"] = bool(
                np.asarray(wav_co).shape != np.asarray(wav_khong).shape
                or not np.allclose(wav_co, wav_khong))
            import perth
            wm = perth.PerthImplicitWatermarker()
            kq["doc_lai_duoc"] = float(
                np.mean(wm.get_watermark(np.asarray(wav_co, dtype=np.float32),
                                         sample_rate=sr)))
        except Exception as e:  # noqa: BLE001
            kq["loi"] = f"{type(e).__name__}: {e}"
        so.ghi(khoa, kq)
        print(f"[watermark] {kq}")

    print(f"\nDa ghi: {ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
