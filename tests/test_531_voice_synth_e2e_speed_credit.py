"""E2E synthesize + speed/language qua PIPELINE THẬT — chot bat bien muc 5.

Khe ho ma cac test khac chua phu: speed/language MOI (D01-D03) chay qua DUONG
NGHIEP VU THAT cua worker (`jobs.handle` -> `features.chuan_hoa`/`giai_giong`
-> do thoi luong -> `toc_do.ap_dung_tep` -> cat kho -> credit), khong phai chi
kiem `params_schema` hay `validate_public_input`.

⭐ CHI MOCK CUOC GOI GPU (`features.goi_cong` tra WAV canned) — moi thu khac
   CHAY THAT: SQLite tam, LocalStorage that, credit that, ffprobe that, atempo
   that. Dung muc 29 ("isolated DB + real sidecar where safe"): GPU dang bi
   phien khac tranh, va mot WAV canned du chung minh lop dieu phoi + tinh tien.

🔴 BAT BIEN TRUNG TAM (toc_do.py chot ①): tinh tien theo thoi luong GOC (truoc
   keo gian). speed=2.0 lam tep ngan di mot nua NHUNG credit KHONG giam — chon
   nhanh hon khong duoc re hon. Neu ai dao thu tu (keo gian truoc khi do) thi
   day la test do.
"""
from __future__ import annotations

import io
import struct
import subprocess
import wave

import pytest


def _wav_bytes(giay: float = 6.0, sr: int = 24000) -> bytes:
    """WAV mono co tin hieu, dung thay cho dau ra sidecar that."""
    n = int(giay * sr)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        mau = bytearray()
        for i in range(n):
            v = 3000 if (i // 300) % 2 == 0 else -3000
            mau += struct.pack("<h", v)
        w.writeframes(bytes(mau))
    return buf.getvalue()


def _ffprobe_dur(path: str) -> float:
    from platform_core.media import ffprobe_bin
    out = subprocess.run(
        [ffprobe_bin(), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=30)
    return float((out.stdout or "0").strip() or 0)


class _Ctx:
    def __init__(self):
        self.attempt = 1
        self.job_type = "ltt_voice.synthesize"
        self.job_id = "test-synth-531"
        self.gpu_uuid = ""


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    """App that tren SQLite tam + LocalStorage + mot user co credit."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-531.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-531")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core import credit
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="voice-531@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 100000, note="test_531")
        uid = str(u.id)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # Mock DUNG bien GPU: sidecar san sang + goi_cong tra WAV canned 6s.
    from apps.ltt_voice import features, sidecar_client
    monkeypatch.setattr(sidecar_client, "san_sang", lambda: True)
    canned = _wav_bytes(6.0)
    monkeypatch.setattr(
        features, "goi_cong",
        lambda text, **kw: (canned, {"X-Duration-S": "6.0", "X-Gen-S": "1.5"}))

    try:
        yield uid, dbmod
    finally:
        set_storage(None)
        dbmod.reset_engine()


def _preset_vi() -> str:
    """Mot preset lan VI hop le, lay tu nguon that (khong hardcode ten).
    `preset` nhan `GiongMau.ma`; lan o truong `ngon_ngu`."""
    from apps.ltt_voice import giong_mau
    for g in giong_mau.DANH_SACH:
        if getattr(g, "ngon_ngu", "") == "vi":
            return g.ma
    return giong_mau.MAC_DINH


def _chay(uid, speed=1.0, language="vi", text="Xin chào, đây là một câu kiểm thử."):
    from apps.ltt_voice import jobs
    params = {"text": text, "voice_id": "", "preset": _preset_vi(),
              "owner_id": uid, "speed": speed, "language": language}
    return jobs.handle(params, _Ctx())


def _doc_store(dbmod, audio_key: str, path: str):
    from platform_core.storage import get_storage
    with get_storage().open(audio_key) as f:
        data = f.read()
    with open(path, "wb") as f:
        f.write(data)
    return data


class TestSynthE2E:

    def test_speed_1_credit_tren_thoi_luong_goc(self, moi_truong, tmp_path):
        uid, dbmod = moi_truong
        kq = _chay(uid, speed=1.0)
        assert kq["audio_key"], "khong co artifact"
        # Thoi luong do duoc (co so tinh tien) = 6s canned.
        assert abs(float(kq["duration_s"]) - 6.0) < 0.2, kq
        assert int(kq["credit_cost"]) > 0

    def test_speed_2x_credit_KHONG_giam_nhung_tep_NGAN_di(self, moi_truong, tmp_path):
        """🔴 Bat bien trung tam: credit tinh theo GOC, speed ap SAU."""
        uid, dbmod = moi_truong
        kq1 = _chay(uid, speed=1.0)
        kq2 = _chay(uid, speed=2.0)

        # Credit nhu nhau: speed khong lam re hon (do tren thoi luong goc 6s).
        assert int(kq1["credit_cost"]) == int(kq2["credit_cost"]), (
            f"speed 2.0 lam credit doi ({kq2['credit_cost']} vs "
            f"{kq1['credit_cost']}) — speed phai ap SAU khi do tinh tien")
        # duration_s (co so tinh tien) van la ~6s o ca hai.
        assert abs(float(kq2["duration_s"]) - 6.0) < 0.2

        # NHUNG tep luu that o speed 2.0 ngan di ~mot nua.
        p = str(tmp_path / "ra2x.wav")
        _doc_store(dbmod, kq2["audio_key"], p)
        dur = _ffprobe_dur(p)
        assert abs(dur - 3.0) < 0.3, (
            f"speed 2.0: tep luu {dur:.2f}s, ky vong ~3s (6/2)")

    def test_speed_0_5_tep_DAI_gap_doi(self, moi_truong, tmp_path):
        uid, dbmod = moi_truong
        kq = _chay(uid, speed=0.5)
        p = str(tmp_path / "ra05.wav")
        _doc_store(dbmod, kq["audio_key"], p)
        dur = _ffprobe_dur(p)
        assert abs(dur - 12.0) < 0.5, f"speed 0.5: tep {dur:.2f}s, ky vong ~12s"

    def test_language_vi_preset_vi_chay_duoc(self, moi_truong):
        uid, dbmod = moi_truong
        kq = _chay(uid, language="vi", text="Xin chào các bạn.")
        assert kq["audio_key"]

    def test_language_en_tren_giong_VI_bi_chan(self, moi_truong):
        """Van ban tieng Anh CHAC CHAN + giong VI + khai language=en ⇒ lech lan,
        `giai_giong` nem LoiGiongNoi (khong tinh tien, khong artifact)."""
        uid, dbmod = moi_truong
        from apps.ltt_voice import features
        with pytest.raises(features.LoiGiongNoi):
            _chay(uid, language="en",
                  text="The quick brown fox jumps over the lazy dog today.")
