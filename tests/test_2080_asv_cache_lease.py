"""ASV final — cache dung chung: MOT tinh, cac ben kia CHO (lease nen tang).

🔑 Hai lan chay CUNG khach, CUNG noi dung nop cung luc: dung MOT lan goi engine.
   Ben den sau khong ngu trong worker — no nem `jobs.DangBan`, worker hoan job.
⭐ Moi vế "cho" di kem mot vế "KHONG duoc cho": khach khac, chu chet, chu huy.

Dong thoi duoc dung TAT DINH: engine gia cua lan A goi `chay_giai_doan` cua lan
B ngay giua luc A dang tinh — dung khoanh khac hai worker chong nhau, qua CSDL
that (SQLite tep; PostgreSQL khi co `LTT_TEST_DATABASE_URL`).
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests import test_478_asv_v6_cache_chung as _t478
from tests.pg_scratch import scratch_url, skip_without_postgres

db, kho, asr_gia = _t478.db, _t478.kho, _t478.asr_gia
_nguon, _run, _chay, _gd = _t478._nguon, _t478._run, _t478._chay, _t478._gd

HAI = ("audio_prepare", "transcribe")


def _mod(ten):
    from apps.auto_scan_video import giai_doan_am_thanh, giai_doan_chep_loi
    return {"audio_prepare": giai_doan_am_thanh, "transcribe": giai_doan_chep_loi}[ten]


def _hai_run(db, kho, tmp_path, *, owner2="uA"):
    """Hai lan chay cung noi dung, `media_prepare` xong ca hai, chua gi khac."""
    k1 = _nguon(kho, tmp_path)
    r1 = _run(db, k1)
    k2 = _nguon(kho, tmp_path, owner=owner2, ten="b", chep_tu=k1)
    r2 = _run(db, k2, owner=owner2)
    for r in (r1, r2):
        _chay(db, r, "media_prepare")
    return r1, r2


def _goi(run, ten):
    from apps.auto_scan_video import thi_hanh
    return thi_hanh.chay_giai_doan(ten, {"run_id": run.id, "owner_id": run.owner_id})


def _khoa(db, run, ten):
    from apps.auto_scan_video import cache_chung, thi_hanh
    return cache_chung.khoa(db, run, ten, engine=thi_hanh.phien_ban_engine(ten))


def _chen_trong_engine(monkeypatch, ten, khi_dang_tinh):
    """Boc engine `ten`: dem lan goi; o lan goi DAU, chay `khi_dang_tinh()` giua chung."""
    mod = _mod(ten)
    that = mod.chay
    dem = {"n": 0, "ben_kia": None}

    def boc(*a, **kw):
        dem["n"] += 1
        if dem["n"] == 1:
            dem["ben_kia"] = khi_dang_tinh()
        return that(*a, **kw)
    monkeypatch.setattr(mod, "chay", boc)
    return dem


def _thu(fn):
    try:
        return ("xong", fn())
    except Exception as e:                      # noqa: BLE001
        return ("loi", e)


def _nguoi_giu(db, kc):
    from apps.auto_scan_video import cache_chung
    from platform_core import leases
    db.expire_all()
    return leases.current_holder(db, name=cache_chung.ten_lease(kc))


# ══ 1. Dong thoi, cung khach: dung MOT lan tinh ════════════════════════════

@pytest.mark.parametrize("ten", HAI)
def test_hai_lan_chay_DONG_THOI_chi_MOT_lan_tinh(db, kho, tmp_path, asr_gia,
                                                  monkeypatch, ten):
    from platform_core.jobs import DangBan
    from platform_core import job_runner

    r1, r2 = _hai_run(db, kho, tmp_path)
    if ten == "transcribe":
        for r in (r1, r2):
            _chay(db, r, "audio_prepare")
    kc = _khoa(db, r2, ten)
    assert kc and kc == _khoa(db, r1, ten), "tien de: hai lan chay phai trung khoa"
    # Nhu dieu phoi vien that: giai doan cua B da nop job ⇒ `queued` + job_id.
    from apps.auto_scan_video import features
    features.danh_dau_dang_chay(db, _gd(db, r2, ten), "job-B")
    db.commit()
    truoc = _gd(db, r2, ten)
    trang_thai_truoc, luot_truoc = truoc.status, truoc.attempt

    dem = _chen_trong_engine(monkeypatch, ten, lambda: _thu(lambda: _goi(r2, ten)))
    _chay(db, r1, ten)

    kieu, loi = dem["ben_kia"]
    assert kieu == "loi" and isinstance(loi, DangBan), (
        f"B dang luc A tinh phai bi HOAN (DangBan), nhan {dem['ben_kia']!r}")
    # Worker hoan job ve hang doi, KHONG tieu luot thu.
    assert job_runner._provider_failure_kind(loi, provider_state="")[0] == "resource_wait"
    db.expire_all()
    sau = _gd(db, r2, ten)
    assert (sau.status, sau.attempt, sau.job_id) == (trang_thai_truoc, luot_truoc, "job-B"), (
        "DangBan khong duoc cham dong asv_stage")
    assert not sau.error

    assert _nguoi_giu(db, kc) == "", "A xong ma khong nha lease"
    _chay(db, r2, ten)                          # luot hoan quay lai
    assert dem["n"] == 1, "hai lan chay dong thoi van goi engine hai lan"
    o2 = _gd(db, r2, ten).outputs
    assert _gd(db, r2, ten).status == "succeeded" and o2["tu_cache_chung"] is True


def test_ben_kia_cong_bo_giua_lan_hoi_va_luc_gianh_thi_KHONG_tinh_lai(
        db, kho, tmp_path, asr_gia, monkeypatch):
    """Hoi lai cache SAU khi gianh lease: A nha lease ngay truoc khi B gianh."""
    from apps.auto_scan_video import cache_chung

    r1, r2 = _hai_run(db, kho, tmp_path)
    _chay(db, r1, "audio_prepare")
    that = cache_chung.lay
    lan = {"n": 0}

    def lay_tre(*a, **kw):          # lan hoi DAU cua B "truoc khi A cong bo"
        lan["n"] += 1
        return None if lan["n"] == 1 else that(*a, **kw)
    monkeypatch.setattr(cache_chung, "lay", lay_tre)
    dem = _chen_trong_engine(monkeypatch, "audio_prepare", lambda: None)
    _chay(db, r2, "audio_prepare")
    assert lan["n"] == 2 and dem["n"] == 0
    assert _gd(db, r2, "audio_prepare").outputs["tu_cache_chung"] is True


# ══ 2. KHONG duoc cho ═════════════════════════════════════════════════════

def test_khach_KHAC_dong_thoi_van_HAI_lan_tinh(db, kho, tmp_path, asr_gia, monkeypatch):
    """⛔ I19: chu so huu nam trong khoa ⇒ lease khac ⇒ khong ai cho ai."""
    r1, r2 = _hai_run(db, kho, tmp_path, owner2="uB")
    assert _khoa(db, r1, "audio_prepare") != _khoa(db, r2, "audio_prepare")
    dem = _chen_trong_engine(monkeypatch, "audio_prepare",
                             lambda: _thu(lambda: _goi(r2, "audio_prepare")))
    _chay(db, r1, "audio_prepare")
    assert dem["ben_kia"][0] == "xong", dem["ben_kia"]
    assert dem["n"] == 2
    assert not _gd(db, r2, "audio_prepare").outputs.get("tu_cache_chung")


def test_A_HONG_thi_nha_lease_ngay_va_B_tu_tinh(db, kho, tmp_path, asr_gia, monkeypatch):
    r1, r2 = _hai_run(db, kho, tmp_path)
    kc = _khoa(db, r1, "audio_prepare")
    mod = _mod("audio_prepare")
    that = mod.chay
    dem = {"n": 0}

    def boc(*a, **kw):
        dem["n"] += 1
        if dem["n"] == 1:
            raise RuntimeError("engine A no tung")
        return that(*a, **kw)
    monkeypatch.setattr(mod, "chay", boc)
    with pytest.raises(RuntimeError, match="engine A no tung"):
        _goi(r1, "audio_prepare")
    assert _nguoi_giu(db, kc) == "", "A hong ma lease van bi giu"
    _chay(db, r2, "audio_prepare")
    assert dem["n"] == 2 and _gd(db, r2, "audio_prepare").status == "succeeded"


def test_A_CHET_thi_B_cho_toi_khi_lease_HET_HAN_roi_tu_tinh(
        db, kho, tmp_path, asr_gia, monkeypatch):
    """Tien trinh A bi kill: khong `finally`, khong nhip — chi con dong lease."""
    from apps.auto_scan_video import cache_chung
    from platform_core import leases
    from platform_core.jobs import DangBan
    from platform_core.models import SingletonLease

    r1, r2 = _hai_run(db, kho, tmp_path)
    kc = _khoa(db, r2, "audio_prepare")
    ten = cache_chung.ten_lease(kc)
    assert leases.acquire(db, name=ten, holder="may-chet:4242:job-A") is not None
    dem = _chen_trong_engine(monkeypatch, "audio_prepare", lambda: None)

    with pytest.raises(DangBan):                # nhip con moi: B cho
        _goi(r2, "audio_prepare")
    assert dem["n"] == 0

    row = db.query(SingletonLease).filter_by(name=ten).one()
    cu = datetime.now(timezone.utc) - cache_chung.TTL_GIU_CHO - timedelta(seconds=5)
    row.heartbeat_at = row.acquired_at = cu
    db.commit()

    _chay(db, r2, "audio_prepare")              # het han: B thu hoi va tu tinh
    assert dem["n"] == 1 and _gd(db, r2, "audio_prepare").status == "succeeded"
    assert _nguoi_giu(db, kc) == ""


def test_A_BI_HUY_giua_chung_thi_B_KHONG_ket(db, kho, tmp_path, asr_gia, monkeypatch):
    from platform_core.job_runner import JobCancelled

    r1, r2 = _hai_run(db, kho, tmp_path)
    kc = _khoa(db, r1, "audio_prepare")
    mod = _mod("audio_prepare")
    that = mod.chay
    dem = {"n": 0}

    def boc(*a, **kw):
        dem["n"] += 1
        if dem["n"] == 1:
            raise JobCancelled()
        return that(*a, **kw)
    monkeypatch.setattr(mod, "chay", boc)
    with pytest.raises(JobCancelled):
        _goi(r1, "audio_prepare")
    assert _nguoi_giu(db, kc) == ""
    _chay(db, r2, "audio_prepare")
    assert dem["n"] == 2 and _gd(db, r2, "audio_prepare").status == "succeeded"


def test_chu_BI_HUY_ma_engine_chua_dung_thi_THOI_DAP_NHIP(db, monkeypatch):
    """Engine khong chiu dung khi huy: nhip tat ⇒ ben cho nhan sau TTL."""
    from apps.auto_scan_video import cache_chung
    from platform_core.models import SingletonLease

    monkeypatch.setattr(cache_chung, "NHIP_GIU_CHO_S", 0.05)
    huy = threading.Event()
    g = cache_chung.giu_cho("b" * 64, holder="t:huy", con_song=lambda: not huy.is_set())
    try:
        ten = cache_chung.ten_lease("b" * 64)
        db.expire_all()
        dau = db.query(SingletonLease).filter_by(name=ten).one().heartbeat_at
        time.sleep(0.3)
        db.expire_all()
        assert db.query(SingletonLease).filter_by(name=ten).one().heartbeat_at > dau, (
            "chu con song ma khong dap nhip")
        huy.set()
        g.luong.join(timeout=2)
        assert not g.luong.is_alive(), "chu da huy ma luong nhip van chay"
    finally:
        g.nha()
    db.expire_all()
    assert db.query(SingletonLease).filter_by(name=ten).count() == 0


# ══ 3. Gianh lease: dung MOT nguoi thang, tren CSDL that ════════════════════

def _dua_gianh(n=8):
    from apps.auto_scan_video import cache_chung
    from platform_core.jobs import DangBan

    rao = threading.Barrier(n)
    kq, khoa = [], threading.Lock()

    def mot(i):
        rao.wait()
        try:
            g = cache_chung.giu_cho("c" * 64, holder=f"t:{i}")
            r = "thang" if g is not None else "khong_lease"
        except DangBan:
            g, r = None, "cho"
        with khoa:
            kq.append((r, g))
    ts = [threading.Thread(target=mot, args=(i,)) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=30)
    for _, g in kq:
        if g is not None:
            g.nha()
    return [r for r, _ in kq]


def test_tam_luong_gianh_cung_khoa_SQLITE_dung_mot_nguoi_thang(db):
    kq = _dua_gianh()
    assert kq.count("thang") == 1, kq
    assert kq.count("cho") == 7, kq


PG_URL = scratch_url()


@skip_without_postgres()
def test_tam_luong_gianh_cung_khoa_POSTGRES_dung_mot_nguoi_thang(monkeypatch):
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.models import SingletonLease

    monkeypatch.setenv("LTT_DATABASE_URL", PG_URL)
    dbmod.reset_engine()
    try:
        SingletonLease.__table__.create(dbmod.get_engine(), checkfirst=True)
        kq = _dua_gianh()
        assert kq.count("thang") == 1 and kq.count("cho") == 7, kq
    finally:
        dbmod.reset_engine()


# ══ 4. Ten lease vua cot ════════════════════════════════════════════════════

def test_ten_lease_vua_String64_va_KHAC_theo_khoa():
    from apps.auto_scan_video import cache_chung
    from platform_core.models import SingletonLease

    toi_da = SingletonLease.__table__.c.name.type.length
    # Giu 58 hex dau cua sha256 (232 bit) — va cham khong dang ke.
    a = cache_chung.ten_lease("a" * 64)
    assert len(a) <= toi_da and a.startswith("asvcc:")
    assert cache_chung.ten_lease("0" * 57 + "1" + "0" * 6) != cache_chung.ten_lease("0" * 64)
