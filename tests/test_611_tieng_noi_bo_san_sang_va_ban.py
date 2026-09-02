"""
test_611 — CỔNG GIỌNG: ba trạng thái sẵn sàng, và BẬN KHÔNG PHẢI HỎNG. (H43 Phase 05)

`sidecar_client.trang_thai()` có BA trạng thái: `chua_bat` (thiếu token — việc của
người cài đặt) · `khong_tra_loi` (đã cài mà chết) · `san_sang`. Đường job dùng
`san_sang()` (chỉ hỏi "có token không") **làm chốt cấu hình**, KHÔNG làm bằng
chứng sống: sống hay chết được quyết bởi chính lượt gọi cổng, và lượt đó hỏng
thì là `LoiHaTang` (thử lại có đếm), không phải một chip xanh.

Bận (`SidecarBan` 429) ⇒ `DangBanTam`, nay là `platform_core.jobs.DangBan` ⇒ worker
`resource_wait`: về hàng đợi, KHÔNG tiêu lượt thử, KHÔNG chạm tiền. Trước Phase 05
nó rơi vào `retry` và năm lần bận liên tiếp là một job hỏng (Phase 02 đo).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

TOOL = "speech.ltt"
VAN_BAN = "Xin chào các bạn, hôm nay chúng ta nói về một chủ đề mới."


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       "sqlite:///" + (tmp_path / "tieng611.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import storage
    storage.set_storage(storage.LocalStorage(str(tmp_path / "kho")))
    yield
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
        u = tao_nguoi_dung(db, email="v611-" + uuid.uuid4().hex[:8] + "@example.com",
                           password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, u.id, credits, by="test")
        db.commit()
        return u.id
    finally:
        _close(gen)


def _khong_duoc_goi_mang(monkeypatch):
    def _no(*a, **k):
        raise AssertionError("khong duoc goi mang trong test nay")
    monkeypatch.setattr("urllib.request.urlopen", _no)


# ── 1. Ba trạng thái ────────────────────────────────────────────────────────

def test_trang_thai_ba_gia_tri(monkeypatch):
    from apps.ltt_voice import sidecar_client as sc

    monkeypatch.delenv("LTT_VOICE_SIDECAR_TOKEN", raising=False)
    _khong_duoc_goi_mang(monkeypatch)
    assert sc.trang_thai() == "chua_bat"
    assert sc.san_sang() is False and sc.song(buoc=True) is False

    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "tok")
    monkeypatch.setattr(sc, "song", lambda buoc=False: False)
    assert sc.trang_thai() == "khong_tra_loi"
    monkeypatch.setattr(sc, "song", lambda buoc=False: True)
    assert sc.trang_thai() == "san_sang"


def test_san_sang_chi_la_cau_hoi_cau_hinh_khong_phai_bang_chung_song(monkeypatch):
    from apps.ltt_voice import sidecar_client as sc
    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "tok")
    _khong_duoc_goi_mang(monkeypatch)
    assert sc.san_sang() is True            # không hề chạm mạng ⇒ không nói gì về sống/chết


# ── 2. Đường job: chưa bật ≠ chết ≠ bận ──────────────────────────────────────

def test_job_chua_bat_la_loi_nguoi_goi_khong_goi_mang(monkeypatch):
    from platform_core import jobs as jobq
    from apps.ltt_voice import features, giong_mau, jobs as vj

    monkeypatch.delenv("LTT_VOICE_SIDECAR_TOKEN", raising=False)
    _khong_duoc_goi_mang(monkeypatch)
    with pytest.raises(features.LoiGiongNoi) as e:
        vj.handle({"text": VAN_BAN, "preset": giong_mau.MAC_DINH,
                   "_job_type": "ltt_voice.synthesize"})
    assert isinstance(e.value, jobq.LoiNguoiGoi)
    assert "chưa được thiết lập" in str(e.value)


def test_job_cong_chet_la_LoiHaTang_thu_lai_co_dem_khong_phai_chip_xanh(moi_truong, monkeypatch):
    """Token có ⇒ `san_sang()` True — nhưng cổng chết thì lượt gọi thật mới nói."""
    from platform_core.job_runner import _provider_failure_kind
    from apps.ltt_voice import features, giong_mau, jobs as vj, sidecar_client

    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "tok")
    assert sidecar_client.san_sang() is True

    def _chet(*a, **k):
        raise sidecar_client.LoiSidecar("Khong ket noi duoc toi cong giong")

    monkeypatch.setattr(sidecar_client, "noi", _chet)
    with pytest.raises(features.LoiHaTang) as e:
        vj.handle({"text": VAN_BAN, "preset": giong_mau.MAC_DINH,
                   "owner_id": str(uuid.uuid4()), "_job_type": "ltt_voice.synthesize"})
    kind, _ = _provider_failure_kind(e.value, provider_state="")
    assert kind == "retry"                  # có đếm lượt: cổng chết thật phải được báo


def test_ban_la_DangBan_cua_nen_tang_resource_wait_giu_retry_after(monkeypatch):
    from platform_core import jobs as jobq
    from platform_core.job_runner import _provider_failure_kind
    from apps.ltt_voice import features, sidecar_client

    def _ban(*a, **k):
        raise sidecar_client.SidecarBan(retry_after_s=7.5)

    monkeypatch.setattr(sidecar_client, "noi", _ban)
    with pytest.raises(features.DangBanTam) as e:
        features.goi_cong("xin chao", preset="p")
    assert isinstance(e.value, jobq.DangBan)
    assert e.value.retry_after_s == 7.5
    assert not isinstance(e.value, jobq.LoiNguoiGoi)
    assert not isinstance(e.value, features.LoiHaTang)
    assert _provider_failure_kind(e.value, provider_state="") == ("resource_wait", 7)


# ── 3. Worker thật: bận ⇒ xếp lại, không tiêu lượt, không chạm tiền ─────────

def _nop(user_id: str):
    from platform_core import credit
    from platform_core.runtime_noi_bo import job as rj
    from apps.ltt_voice import giong_mau
    bg = rj.bao_gia(TOOL, {"text": VAN_BAN, "preset": giong_mau.MAC_DINH})
    gen, db = _session()
    try:
        j = rj.nop_job(db, user_id=user_id, bao_gia=bg, idempotency_key="idem-611")
        db.commit()
        return j.id, j.max_attempts, credit.so_da_giu(db, j.id)
    finally:
        _close(gen)


def _doc(job_id):
    from platform_core.models import Job, JobEvent
    gen, db = _session()
    try:
        j = db.get(Job, job_id)
        ma = [e.event_code for e in db.query(JobEvent).filter(JobEvent.job_id == job_id)
              .order_by(JobEvent.sequence).all()]
        db.expunge(j)
        return j, ma
    finally:
        _close(gen)


def _cho_chay_ngay(job_id):
    from platform_core.models import Job
    gen, db = _session()
    try:
        db.get(Job, job_id).next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        _close(gen)


def test_worker_cong_ban_ve_hang_doi_khong_tieu_luot_khong_cham_tien(moi_truong, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core import credit
    from platform_core.models import JOB_QUEUED
    from apps.ltt_voice import sidecar_client

    monkeypatch.setenv("LTT_VOICE_SIDECAR_TOKEN", "tok")
    monkeypatch.setattr(runner, "_vram_can", lambda jt: 0)
    u = _user(100)
    job_id, so_lan, held = _nop(u)
    assert so_lan == 5 and held > 0

    goi = []

    def _ban(*a, **k):
        goi.append(1)
        raise sidecar_client.SidecarBan(retry_after_s=3)

    monkeypatch.setattr(sidecar_client, "noi", _ban)
    monkeypatch.setattr(sidecar_client, "noi_dai", _ban)

    # Bận NHIỀU HƠN số lượt thử — vẫn không hỏng, vẫn không tiêu lượt.
    for _ in range(so_lan + 1):
        _cho_chay_ngay(job_id)
        assert runner._chay_mot_job("w-611") is True
    assert len(goi) == so_lan + 1

    j, ma = _doc(job_id)
    assert j.status == JOB_QUEUED and j.attempts == 0
    assert j.provider_state == "rejected" and j.worker_id == ""
    assert ma.count("resource_wait") == so_lan + 1
    assert "retry_scheduled" not in ma and "failed" not in ma and "credit_settled" not in ma
    gen, db = _session()
    try:
        assert credit.so_da_giu(db, job_id) == held
        assert credit.so_du(db, u) == 100 - held
    finally:
        _close(gen)
