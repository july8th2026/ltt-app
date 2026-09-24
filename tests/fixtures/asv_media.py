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
    # `en`, khong `vi`: dich mac dinh la `vi`, va hop dong ngon ngu (22/09) tu
    # choi nguon trung dich. Loi "cau thu N" khong phai tieng Anh — khong sao,
    # khong bo phan nao doc lai ngon ngu tu chu.
    return {"segments": doan, "language": "en", "engine": "gia",
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

    # ⚠️ Chu ky phai BAM theo `ai.goi_tinh_tien`: ban gia thieu mot tham so thi
    #    moi phep kiem chay het chuoi do bang `TypeError`, va thong diep ⛔ khong
    #    tro vao cho that. `luoc_do` them 24/09 (N-23 ve ba, ep luoc do o tang
    #    giai ma) da lam dung nhu vay voi bon bai cua `test_440`.
    def gia(db, run, thao_tac, messages, *, stage, item_key, uoc_credit=0,
            ctx=None, temperature=None, luoc_do=None):
        # ⭐ Phan hoi BAM VAO dau vao: mot ban gia tra ve du lieu co dinh se khong
        #    bao gio phat hien duoc loi ghep sai ma doan.
        import json

        # ── DOC CANH (pha 27) ──────────────────────────────────────────────
        #
        # 🔑 Nhan theo `thao_tac`, khong theo hinh dang goi tin: o CUA nay ta co
        #    san thao tac, nen doan mo la thua. (`tests/fixtures/asv_e2e` thay o
        #    tang duoi — `dieu_phoi.goi` — nen no BUOC phai doan, va docstring
        #    cua no ghi ro dieu do.)
        san = phan_hoi_ngoai_dich(thao_tac, messages)
        if san is not None:
            return san

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


def phan_hoi_ngoai_dich(thao_tac, messages):
    """Phan hoi cho moi thao tac AI **khong phai** dich, hoac `None`.

    🔑 Cong khai co chu dinh. `test_440` co ba ban thay the CUC BO cua
       `ai.goi_tinh_tien` — chung ton tai vi tung phep kiem can dem xem model
       duoc gui gi. Ba ban do chi biet luoc do DICH, nen ngay pha 27 them nguoi
       goi model thu hai chung deu hong cung mot luc, dung nhu docstring cua
       `cua_ai_gia` da canh bao ve ba ban sao truoc do.

    ⇒ Chung uy quyen cho ham nay cho phan **khong** thuoc thu chung dang do.
      Them mot thao tac AI moi thi chi phai sua MOT cho.
    """
    import json

    from apps.auto_scan_video import ai

    ma = getattr(thao_tac, "ma", "")
    if ma == ai.DOC_CANH.ma:
        return {"noi_dung": json.dumps(_canh_gia(messages), ensure_ascii=False),
                "su_dung": None}
    if ma == ai.HO_SO_NOI_DUNG.ma:
        return {"noi_dung": json.dumps(_ho_so_gia(messages), ensure_ascii=False),
                "su_dung": None}
    if ma == ai.QC_HINH.ma:
        # ⭐ Mac dinh DAT: mot ban gia mac dinh "hong" se lam moi phep kiem
        #    dau-cuoi sinh ra mot vong sua ma chung khong noi gi ve no. Phep
        #    kiem nao can chieu HONG thi tu dat ban gia cua rieng no
        #    (`test_2120`), va no phai noi ro dieu do.
        return {"noi_dung": json.dumps(
            {"dat": True, "do_tin": 0.9, "ly_do": ""}, ensure_ascii=False),
            "su_dung": None}
    return None


def _ho_so_gia(messages) -> dict:
    """Phan hoi `HO_SO_NOI_DUNG` — dung tu vung CATALOG, khong phai chu tu nghi.

    🔴 **Ban gia nay co mot viec phai lam dung, va no la viec de lam sai nhat
       o ca duong `AUTO_MATCH`.** Mot model that rat de tra ve `phong_cach:
       "thuyet minh"` — mot chu dung tieng Viet ma catalog KHONG co, va khi do
       `giong_mau.loc` tra ve rong. Neu ban gia o day tra ve mot gia tri "dep"
       nam ngoai catalog thi phep kiem se xanh quanh mot ho so khong rang duoc
       giong nao; neu no tra ve dung tu vung catalog thi phep kiem chi chung
       minh duong ong, chu khong chung minh phep loc tu vung.

    ⇒ Nen no tra ve mot gia tri CATALOG (duong ong), con phep loc tu vung duoc
      do rieng o `test_2006` bang chinh chu ngoai catalog.

    ⚠️ `gioi` de RONG co chu dinh: duong that lay `gioi` tu phep do F0
      (`cao_do.py`), va mot ban gia tu dien `gioi` se che mat cau hoi "phep do
      co thuc su duoc dung khong".
    """
    from apps.ltt_voice.giong_mau import UU_TIEN_PHONG_CACH

    return {
        "the_loai": "giai tri",
        "giong_dieu": "vui",
        "khan_gia": "nguoi xem tre",
        "nhip": "nhanh",
        "tom_tat": "mot doan video ngan",
        "dac_diem_giong": {
            "gioi": "",
            "vung": "",
            "phong_cach": min(UU_TIEN_PHONG_CACH, key=UU_TIEN_PHONG_CACH.get),
        },
    }


def _canh_gia(messages) -> dict:
    """Phan hoi `DOC_CANH` — BAM VAO tin hieu do duoc gui kem.

    ⛔ Mot ban gia luon tra "giu" se lam moi phep kiem ve chinh sach cat thanh
       rong ruot: chung se xanh du `_quyet_dinh_mot_canh` co doc `de_xuat` hay
       khong. Nen o day canh KHONG co loi thoai duoc de nghi BO voi do tin cao,
       dung phan doan ma mot VLM se dua ra.

    ⚠️ Tin nhan co the la da phuong thuc (mot phan van ban + N phan anh). Gop
       cac phan van ban lai roi doc doi tuong JSON dau tien — do la `tin_hieu`
       ma `loi_nhac_canh` gui.
    """
    import json

    noi_dung = messages[-1].get("content")
    if isinstance(noi_dung, list):
        van = " ".join(p.get("text", "") for p in noi_dung
                       if isinstance(p, dict))
    else:
        van = str(noi_dung or "")

    tin = {}
    dau, cuoi = van.find("{"), van.find("}")
    if 0 <= dau < cuoi:
        try:
            tin = json.loads(van[dau:cuoi + 1])
        except ValueError:
            tin = {}
    co_thoai = bool(tin.get("co_thoai"))
    return {
        "loai": "hoi thoai" if co_thoai else "chuyen canh",
        "chu_the": ["nguoi noi"] if co_thoai else [],
        "hanh_dong": "dang noi" if co_thoai else "khong co hanh dong ro",
        "cam_xuc": "trung tinh",
        "quan_trong": 0.75 if co_thoai else 0.1,
        "de_xuat": "giu" if co_thoai else "bo",
        "do_tin": 0.9,
        "ly_do": ("canh co loi thoai" if co_thoai
                  else "canh khong co loi thoai nao"),
        "canh_bao": [],
    }
