"""Tiny deterministic media fixtures for Auto Scan Video (Phase 04).

## Why synthetic and not a real clip

A fixture built from customer or downloaded material carries copyright, PII and an
approval question into every future test run. `ffmpeg`'s `lavfi` sources carry none of
that, and they are **reproducible**: three separate invocations of `tiny_mp4()` on this
machine produced byte-identical files (measured in Phase 01, 42 982 bytes each).

That reproducibility is the point. Phase 08+ has to test a **fingerprint cache**
(ADR-001 D8), and a cache test needs an input whose identity does not drift.

## Why both streams

Auto Scan's first two stages are MEDIA_PREPARE and AUDIO_PREPARE, so a video-only
fixture would leave the second one untestable. `sine` also gives a known frequency, so
an audio stage has a property to assert rather than just a byte count.

⚠ Byte-level determinism is a property of *this* ffmpeg build (8.0.1 here). Assert on
  decoded properties — duration, dimensions, sample rate, stream count — not on a file
  hash, unless the test also pins the encoder version.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

#: Small enough to commit-free-generate in a fraction of a second, long enough that a
#: segmenter has something to segment.
DEFAULT_DURATION_S = 3.0
DEFAULT_SIZE = "320x240"
DEFAULT_FPS = 12
DEFAULT_TONE_HZ = 440


def ffmpeg_bin() -> str | None:
    """Path to ffmpeg, or None. Never raises — callers decide whether to skip."""
    from platform_core import media
    try:
        return media.ffmpeg_bin()
    except Exception:  # noqa: BLE001 - a missing binary is a skip, not an error
        return shutil.which("ffmpeg")


def require_ffmpeg() -> str:
    """ffmpeg path, or skip the test. Media fixtures are worthless without it."""
    binary = ffmpeg_bin()
    if not binary:
        pytest.skip("khong co ffmpeg de dung fixture media")
    return binary


def tiny_mp4(dest: Path, *, duration_s: float = DEFAULT_DURATION_S,
             size: str = DEFAULT_SIZE, fps: int = DEFAULT_FPS,
             tone_hz: int = DEFAULT_TONE_HZ) -> Path:
    """H.264 + AAC MP4 with one video and one audio stream. Deterministic."""
    binary = require_ffmpeg()
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [binary, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc=size={size}:rate={fps}:duration={duration_s}",
         "-f", "lavfi", "-i", f"sine=frequency={tone_hz}:duration={duration_s}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
         str(dest)],
        check=True, capture_output=True)
    return dest


def nap_nguon_vao_kho(kho, tmp_path: Path, *, owner_id: str = "uA",
                      im_lang: bool = False, **kw) -> str:
    """Build a fixture video, put it in storage, return its key.

    Every Auto Scan run needs a real source object from Phase 08 onward — before
    that, tests used a placeholder key because MEDIA_PREPARE was a dummy that
    never opened it. Now it probes, enforces policy and extracts audio, so a
    placeholder produces a failure that says nothing about the code under test.

    `im_lang=True` seeds a video with **no audio stream**, which is what
    `MVP_CONTRACT.md` §2 rejects at submit.
    """
    import io

    nguon = tmp_path / ("cam.mp4" if im_lang else "nguon.mp4")
    (tiny_mp4_silent(nguon, **kw) if im_lang else tiny_mp4(nguon, **kw))
    khoa = f"asv/{owner_id}/nguon/{nguon.name}"
    with open(nguon, "rb") as f:
        kho.put(khoa, io.BytesIO(f.read()), content_type="video/mp4")
    return khoa


def ban_ghi_gia(duration_s: float = DEFAULT_DURATION_S) -> dict:
    """A deterministic raw-engine transcript, shaped like `transcribe_file` returns.

    ## Why chain tests need this

    The video fixtures are `lavfi` tones — they contain **no speech**. Real ASR on
    them correctly returns zero segments, and TRANSCRIBE then correctly refuses the
    run: a video with nothing spoken has nothing to dub.

    That is the right product behaviour and the wrong test input for a chain test,
    which is about the execution spine rather than about recognition accuracy.

    Making the stage tolerate zero segments to keep a fixture working would weaken
    the product to suit the test. Substituting the engine does not.

    ⭐ Real ASR is smoke-tested separately against the real engine
      (`test_407…::test_engine_ASR_that_chay_duoc`). Measured on this machine:
      2 s of audio took 22.8 s with the `tiny` model on CPU — which is also why a
      chain test cannot call it.
    """
    n = max(1, int(duration_s))
    doan = []
    for i in range(n):
        bat, ket = float(i), float(i) + 0.8
        doan.append({
            "start": bat, "end": ket, "text": f"cau thu {i + 1}",
            "words": [{"start": bat, "end": bat + 0.4, "text": "cau"},
                      {"start": bat + 0.4, "end": ket, "text": f"thu-{i + 1}"}],
        })
    return {"segments": doan, "language": "vi", "engine": "gia",
            "alignment_status": "gia"}


def tiny_mp4_silent(dest: Path, *, duration_s: float = DEFAULT_DURATION_S) -> Path:
    """Video with NO audio stream.

    `MVP_CONTRACT.md` §2 rejects this at submit rather than at TRANSCRIBE — a silent
    video has nothing to localize, and finding that out three paid stages later is a
    refund. This fixture is how that rule gets tested.
    """
    binary = require_ffmpeg()
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [binary, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc=size={DEFAULT_SIZE}:rate={DEFAULT_FPS}"
         f":duration={duration_s}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest)],
        check=True, capture_output=True)
    return dest


# ══════════════════════════════════════════════════════════════════════════════
#  Cua goi model — MOT cho chan cho ca bo test
# ══════════════════════════════════════════════════════════════════════════════

def cua_ai_gia(monkeypatch, *, chu=None):
    """Thay `ai.goi_tinh_tien` — cua DUY NHAT moi loi goi model cua app di qua.

    ⚠️ BAT BUOC cho moi phep kiem chay het chuoi: `CONTENT_PROCESS` goi ra
       `platform_core/llm/dieu_phoi.py`, va bo dieu phoi can mot khoa API that.
       Khong co khoa thi no tu choi — **dung nhu no nen lam**. Mot bo test khong
       duoc phep doi hoi mot khoa tra tien.

    🔴 **Vi sao ham nay ton tai o day chu khong nam trong tung tep test.**

       Truoc pha 14 co **BA ban sao** cua cung mot stub (`test_402`, `test_403`,
       va mot ban inline trong `test_408`), va ca ba deu thay
       `dich_thuat.dich_ban_ghi`. Pha 14 doi `CONTENT_PROCESS` sang goi
       `ai.goi_tinh_tien`, nen ca ba **thoi chan** cung mot luc.

    ⛔ Va mot stub thoi chan con te hon khong co stub: phep kiem van xanh cho toi
       khi no bat ngo doi mot khoa API tra tien — o mot may khac, vao mot ngay
       khac, voi mot thong bao khong lien quan gi toi thay doi da gay ra no.

    ⭐ Nen: mot cho chan, o CUA (pha 08 gom moi loi goi model ve day). Them mot
       nguoi goi model moi thi khong can nho sua stub nao ca.
    """
    from apps.auto_scan_video import ai, long_tieng

    def gia(db, run, thao_tac, messages, *, stage, item_key, uoc_credit=0,
            ctx=None, temperature=None):
        # ⭐ Phan hoi BAM VAO dau vao: mot ban gia tra ve du lieu co dinh se khong
        #    bao gio phat hien duoc loi ghep sai ma doan.
        import json

        goi = json.loads(messages[-1]["content"])
        lam = chu or (lambda ma: f"loi thoai cua {ma}")
        than = {"doan": {
            str(d["ma"]): {"chu": lam(d["ma"]),
                           "cam_xuc": long_tieng.CAM_XUC[0],
                           "kieu_noi": long_tieng.KIEU_NOI[0],
                           "nhan_manh": []}
            for d in goi.get("doan") or []}}
        # 🔴 **CHUOI, khong phai dict.** `ai.goi` tra ve nguyen van phan hoi cua
        #    model (`ai.py:270`), va bo doc JSON la `ai.doc_json`.
        #
        #    Truoc pha 22 ham nay tra ve mot **dict** o `noi_dung` — thu ma cua
        #    that khong bao gio tra ve — va vi the che mat mot loi khong the
        #    khong xay ra: `giai_doan_noi_dung` va `giai_doan_giong` deu goi
        #    `.get("doan")` thang tren chuoi do, nen **moi lan goi model that
        #    deu nem `AttributeError`**. Ca bo test van xanh, vi ban gia tra ve
        #    dung thu ma nguon muon nhan thay vi thu cua that tra ve.
        #
        # ⭐ Bai hoc: mot ban thay the phai trung thanh voi **hop dong cua cai
        #    no thay**, khong phai voi mong doi cua nguoi goi.
        return {"noi_dung": json.dumps(than, ensure_ascii=False),
                "su_dung": None}

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)
    return True
