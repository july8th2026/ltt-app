"""
test_612 — `speech.ltt`: TIỀN THEO GIÂY ĐO ĐƯỢC, không theo phần đã giữ. (H43 Phase 05)

Đường thật: `bao_gia` giữ chỗ theo `gia.uoc_tran(so_ky_tu)` (bi quan có chủ ý) →
worker → `jobs._tao_tieng` → cổng (GIẢ) → `_do_thoi_luong` (GIẢ, thay ffprobe) →
`KetQua.credit_that = gia.tinh(giay)` → `job_runner._quyet_toan_credit` thu đúng số
đó, hoàn phần dư; không đo được ⇒ thu 0 (khuôn 3.5).

Không sửa giá: mọi con số đọc từ `apps/ltt_voice/gia.py`.
"""
from __future__ import annotations

import uuid

import pytest

TOOL = "speech.ltt"
VAN_BAN = ("Hôm nay chúng ta cùng nhau điểm lại những việc đã làm trong tuần, "
           "những điều còn dang dở, và kế hoạch cho tuần tới của cả đội.")


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "tieng612.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "thu-nghiem-612")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import storage
    kho = storage.LocalStorage(str(tmp_path / "kho"))
    storage.set_storage(kho)
    yield kho
    storage.set_storage(None)
    dbmod.reset_engine()


def _session():
    from platform_core.db import get_session
    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _user(credits=100) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen, db = _session()
    try:
        u = tao_nguoi_dung(db, email="v612-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id
    finally:
        _close(gen)


def _cong_gia(monkeypatch, *, giay: float, khai: str | None = None):
    from apps.ltt_voice import jobs as vj, sidecar_client
    goi = []

    def _noi(*a, **k):
        goi.append((a, k))
        h = {"X-Duration-S": khai} if khai is not None else {}
        return b"RIFF0000WAVEfmt " + b"\x00" * 64, h

    monkeypatch.setattr(sidecar_client, "noi", _noi)
    monkeypatch.setattr(sidecar_client, "noi_dai", _noi)
    monkeypatch.setattr(vj, "_do_thoi_luong", lambda p: giay)
    return goi


# ── 1. Handler báo đúng giá theo giây ───────────────────────────────────────

def test_handler_credit_cost_bang_gia_tinh_giay_do_duoc(moi_truong, monkeypatch):
    from apps.ltt_voice import gia, giong_mau, jobs as vj

    goi = _cong_gia(monkeypatch, giay=6.0, khai="6.0")
    owner = str(uuid.uuid4())
    kq = vj.handle({"text": VAN_BAN, "preset": giong_mau.MAC_DINH, "owner_id": owner,
                    "_job_type": "ltt_voice.synthesize"},
                   type("Ctx", (), {"job_id": "job612", "job_type": "ltt_voice.synthesize"})())
    assert len(goi) == 1
    assert kq["credit_cost"] == gia.tinh(6.0)
    assert kq["credit_cost"] == -(-(6.0 * gia.MCREDIT_MOI_GIAY) // gia.MCREDIT_MOI_CREDIT)
    assert kq["duration_s"] == 6.0
    assert kq["audio_key"] == f"voice/out/{owner}/job612/tieng.wav"
    assert kq["phien_ban_gia"] == gia.PHIEN_BAN_GIA
    assert moi_truong.exists(kq["audio_key"])


def test_khong_do_duoc_thi_thu_0(moi_truong, monkeypatch):
    from apps.ltt_voice import giong_mau, jobs as vj
    _cong_gia(monkeypatch, giay=0.0, khai="12.0")      # header nói 12 s, ffprobe nói 0
    kq = vj.handle({"text": VAN_BAN, "preset": giong_mau.MAC_DINH,
                    "owner_id": str(uuid.uuid4()), "_job_type": "ltt_voice.synthesize"})
    assert kq["credit_cost"] == 0 and kq["duration_s"] == 0


def test_toc_do_hau_ky_khong_lam_re_di(moi_truong, monkeypatch):
    """Tính tiền theo giây SINH RA (trước kéo giãn), không theo giây khách nghe."""
    from apps.ltt_voice import gia, giong_mau, jobs as vj, toc_do
    _cong_gia(monkeypatch, giay=6.0)
    monkeypatch.setattr(toc_do, "ap_dung", lambda wav, td: wav)
    kq = vj.handle({"text": VAN_BAN, "preset": giong_mau.MAC_DINH, "toc_do": 1.5,
                    "owner_id": str(uuid.uuid4()), "_job_type": "ltt_voice.synthesize"})
    assert kq["credit_cost"] == gia.tinh(6.0)
    assert kq["duration_played_s"] == pytest.approx(4.0)


# ── 2. Worker thật: thu đúng, hoàn phần dư ──────────────────────────────────

def test_worker_thu_theo_giay_va_hoan_phan_giu_du(moi_truong, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core import credit
    from platform_core.models import JOB_DONE, Job, JobEvent
    from platform_core.runtime_noi_bo import job as rj
    from apps.ltt_voice import gia, giong_mau

    monkeypatch.setattr(runner, "_vram_can", lambda jt: 0)
    u = _user(100)
    bg = rj.bao_gia(TOOL, {"text": VAN_BAN, "preset": giong_mau.MAC_DINH})
    gen, db = _session()
    try:
        j = rj.nop_job(db, user_id=u, bao_gia=bg, idempotency_key="idem-612")
        db.commit()
        job_id, held = j.id, credit.so_da_giu(db, j.id)
    finally:
        _close(gen)
    assert held == bg.credit > 0

    giay = 3.0                                   # ~135 ký tự ước ~9 s ⇒ giữ 2; 3 s ⇒ thu 1
    thu = gia.tinh(giay)
    assert 0 < thu < held, "so lieu test phai lam 'hoan phan du' do duoc"
    _cong_gia(monkeypatch, giay=giay, khai=str(giay))
    assert runner._chay_mot_job("w-612") is True

    gen, db = _session()
    try:
        j = db.get(Job, job_id)
        assert j.status == JOB_DONE
        assert j.result["credit_cost"] == thu
        assert j.result["audio_key"] == f"voice/out/{u}/{job_id}/tieng.wav"
        ma = {e.event_code for e in db.query(JobEvent).filter(JobEvent.job_id == job_id)}
        assert "credit_settled" in ma
        assert credit.so_du(db, u) == 100 - thu
    finally:
        _close(gen)
