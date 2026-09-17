"""test_1251 — suat `mode='sync'` mo coi: han rieng, va nhip tim phai CHUNG MINH tien trien.

## Su co (18/09/2026) — do duoc, khong phai lo xa

`docs/ltt_llm_dual/artifacts/bench_hang_cho/KET_QUA_CACHE_18_09.md` §6. Mot phien
khac deploy luc 00:55 GIUA mot luot `/chat/completions` cua 3.8. Worker bi giet,
dong `execution_leases` nam lai:

    resource='ltt_38_3090'  slot=0  mode='sync'  token_dat_truoc=14457
    acquired_at = heartbeat_at = 00:54:55.896    (nhip tim KHONG BAO GIO tien them)

Hau qua: **moi** luot 3.8 tra `429 concurrency_limited / reason=het_cho` suot
**20 phut** (00:55 -> 01:14:55); 10 luot cua phep do dinh, moi luot cho du 60 s.

## Hai khuyet tat, khong phai mot

1. **Khong co han rieng.** `admission.reclaim_expired` co han rieng cho `stream`
   (180 s) va `job` (300 s); `sync` roi vao mac dinh `ORPHAN_TIMEOUT` = 20 phut —
   **gap 6,7 lan** luot stream, du no la loai luot NGAN NHAT (tran 90 s,
   `SYNC_BILLED_MAX_SECONDS`).

2. **Nhip tim cua cua dong bo noi doi.** `giu_suat_dong_bo` goi
   `admission.keep_alive(lease_id)` **khong** `con_song` — tuc dap nhip VO DIEU
   KIEN, dung loi noi doi cua L-08 (`test_1247`). Ha han xuong 120 s ma khong sua
   dieu nay la ha mot han **khong bao gio khai hoa** chung nao tien trinh con
   song: lop 3 lai bi bit mat y het nam ngoai.

⇒ Ca hai ve deu can, va tep nay chot ca hai.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest

from platform_core.llm import admission


# ── 1. Hang so: co nguon, khong phai so dep ──────────────────────────────────

def test_han_mo_coi_cua_SYNC_ngan_hon_han_chung():
    assert admission.ORPHAN_TIMEOUT_SYNC < admission.ORPHAN_TIMEOUT, (
        "lease sync dung chung han 20 phut voi job nen — do chinh la su co "
        "18/09: mot deploy lam mat TOAN BO suc chua 3.8 trong 20 phut.")


def test_han_SYNC_lay_tu_NGUON_ngan_sach_cua_chinh_cua_dong_bo():
    """🔴 Nguong phai co NGUON. O day co hai nguon, va ca hai deu bat buoc.

    * Chan DUOI: >= `SYNC_BILLED_MAX_SECONDS` — cua dong bo hua tra loi trong
      ngan sach ay va kep `max_tokens` theo dung no, nen mot suat sync SONG
      khong the vuot qua. Ha duoi la thu suat cua nguoi DANG duoc phuc vu.
    * Chan TREN: <= han cua `stream`. Luot sync la luot NGAN NHAT trong ba cua;
      cho no han rong hon luot dai nhat la lap lai su co duoi mot con so khac.
    """
    from platform_core.public_api.protocol import SYNC_BILLED_MAX_SECONDS

    giay = admission.ORPHAN_TIMEOUT_SYNC.total_seconds()
    assert giay >= float(SYNC_BILLED_MAX_SECONDS), (
        f"ORPHAN_TIMEOUT_SYNC={giay}s thap hon ngan sach cua dong bo "
        f"({SYNC_BILLED_MAX_SECONDS}s) — mot luot chay dung ngan sach cua no se "
        "bi thu suat giua chung.")
    assert giay <= admission.ORPHAN_TIMEOUT_STREAM.total_seconds(), (
        f"han sync ({giay}s) rong hon han stream "
        f"({admission.ORPHAN_TIMEOUT_STREAM.total_seconds()}s) — luot ngan nhat "
        "khong duoc giu xac lau hon luot dai nhat.")


def test_han_SYNC_khong_duoi_hai_nhip_tim():
    """⛔ Duoi 2x nhip la thu lease cua nguoi chi LO MOT nhip — xem chu thich cua
    `ORPHAN_TIMEOUT_STREAM` ("DUNG ha xuong duoi 2x (120 s)")."""
    ty_le = admission.ORPHAN_TIMEOUT_SYNC.total_seconds() / admission.HEARTBEAT_SECONDS
    assert ty_le >= 2.0, (
        f"han/nhip = {ty_le:.1f}x. Mot nhip lo (GC, CSDL cham) se lam thu suat "
        "cua mot luot dang duoc phuc vu.")


# ── 2. Hanh vi cua `reclaim_expired`: don sync, khong don nen ─────────────────

class _LeaseGia:
    def __init__(self, mode: str, nhip: datetime):
        self.mode, self.heartbeat_at, self.resource = mode, nhip, "r"


class _DbGia:
    def __init__(self, ds):
        self._d, self.da_xoa = ds, []

    def query(self, *a):
        return self

    def filter(self, *a):
        return self

    def all(self):
        return self._d

    def delete(self, x):
        self.da_xoa.append(x.mode)

    def flush(self):
        pass


def _quet(monkeypatch, tuoi_s: float) -> list:
    gio = datetime.now(timezone.utc)
    cu = gio - timedelta(seconds=tuoi_s)
    db = _DbGia([_LeaseGia("sync", cu), _LeaseGia("nen", cu),
                 _LeaseGia("job", cu)])
    monkeypatch.setattr(admission, "_now", lambda: gio)
    admission.reclaim_expired(db)
    return db.da_xoa


def test_reclaim_don_lease_SYNC_ma_KHONG_don_lease_nen(monkeypatch):
    """Hanh vi, khong phai hang so: cung mot moc nhip, sync bi thu con nen thi khong."""
    da_xoa = _quet(monkeypatch, 5 * 60)      # 5 phut: qua 120 s, chua qua 20 phut
    assert "sync" in da_xoa, (
        f"lease sync im 5 phut van khong bi thu (da xoa: {da_xoa}) — dung ca "
        "phep do 18/09 da do: 20 phut mat suc chua.")
    assert "nen" not in da_xoa, (
        f"da thu ca lease nen (da xoa: {da_xoa}). Job nen chay dai va dap nhip "
        "thua thot hon — thu no som la giet mot job dang chay.")


def test_DOI_CHUNG_lease_SYNC_con_trong_han_thi_KHONG_bi_thu(monkeypatch):
    """⛔ Khong co ve nay thi ve tren khong chung minh duoc gi: mot bo don xoa
    sach moi thu cung lam ve tren XANH."""
    tuoi = admission.ORPHAN_TIMEOUT_SYNC.total_seconds() - 20
    assert _quet(monkeypatch, tuoi) == [], (
        f"thu lease sync moi im {tuoi:.0f}s — duoi han da khai. Mot luot dang "
        "chay dung se bi cuop suat.")


# ── 3. Thu hoi tra lai CA HAI thu: slot VA token da dat cho ──────────────────

POOL = 200_000


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'mocoi.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


def _lui_nhip(db, lease_id: str, giay: float) -> None:
    """Keo `heartbeat_at` lui — gia bo tien trinh giu suat da chet bay nhieu giay."""
    from platform_core.models import ExecutionLease

    lease = db.get(ExecutionLease, lease_id)
    lease.heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=giay)
    db.commit()


def _xin(db, **kw):
    from platform_core.llm import luat_nhan as L

    mac_dinh = dict(resource="r", slots=1, user_id="u", mode="sync",
                    holder_id="h", token_pool=POOL, lop=L.TUONG_TAC,
                    token_dat_truoc=150_000)
    mac_dinh.update(kw)
    return admission.xet_va_giu(db, **mac_dinh)


def test_suat_sync_mo_coi_tra_lai_ca_SLOT_va_TOKEN_DAT_TRUOC(db):
    """Mot dong duy nhat giu ca hai tai nguyen — thu hoi phai tra lai ca hai."""
    from platform_core.llm import luat_nhan as L
    from platform_core.models import ExecutionLease

    xac, ly_do = _xin(db, slots=2, holder_id="xac", token_dat_truoc=150_000)
    assert xac is not None, ly_do
    db.commit()

    # Con slot trong (2 suat), nhung token thi khong: 150K + 100K > pool 200K.
    moi, ly_do = _xin(db, slots=2, user_id="b", holder_id="moi",
                      token_dat_truoc=100_000)
    assert moi is None and ly_do == L.CHO_NGAN_SACH, (
        "phep do khong cham dich: luot moi phai bi chan boi NGAN SACH, nen khi "
        "no duoc nhan ta biet chinh xac la token da duoc tra lai.")
    db.rollback()

    _lui_nhip(db, xac.id, admission.ORPHAN_TIMEOUT_SYNC.total_seconds() + 1)

    moi, ly_do = _xin(db, slots=2, user_id="b", holder_id="moi",
                      token_dat_truoc=100_000)
    assert moi is not None, (
        f"suat sync mo coi van chan luot moi ({ly_do}) — token dat cho chua "
        "duoc tra lai.")
    db.commit()
    assert db.get(ExecutionLease, xac.id) is None, "dong lease mo coi con nam do"
    assert moi.slot == 0, (
        f"luot moi nhan slot {moi.slot} — slot cua xac chua duoc tra lai, no chi "
        "duoc cap slot con trong. Thu hoi phai tra CA HAI.")


# ── 4. Luot sync DANG CHAY lau hon han thi KHONG bi thu ──────────────────────

def test_luot_sync_DANG_CHAY_lau_hon_han_KHONG_bi_thu(db, monkeypatch):
    """Vi tu song = CONG VIEC con tien trien, khong phai dong ho cua lease.

    Dong lease o day da "gia" 10 phut — gap 5 lan han sync. Neu cua dong bo dap
    nhip that (vi cong viec con chay) thi `reclaim_expired` phai KHONG cham vao
    no, du dong ho tuyet doi cua lease da qua han tu lau.
    """
    import platform_core.runtime_noi_bo.luong as cua_luong
    from platform_core.models import ExecutionLease

    ve, ly_do = _xin(db, holder_id="dang-chay")
    assert ve is not None, ly_do
    db.commit()
    _lui_nhip(db, ve.id, 600)

    monkeypatch.setattr(admission, "HEARTBEAT_SECONDS", 0.05)
    suat = cua_luong.SuatDongBo(ve.id, "w1")
    with cua_luong.giu_suat_dong_bo(suat):
        time.sleep(0.3)
        suat.cham()                    # cong viec vua nhuc nhich (mot luot goi B)
        time.sleep(0.2)
        db.expire_all()
        song = db.query(ExecutionLease).filter(ExecutionLease.id == ve.id).first()
        assert song is not None, "luong nhip da NHA suat cua mot luot dang chay"
        nhip = song.heartbeat_at
        if nhip.tzinfo is None:
            nhip = nhip.replace(tzinfo=timezone.utc)
        assert (datetime.now(timezone.utc) - nhip) < timedelta(seconds=60), (
            "nhip tim KHONG tien them — phep do duoi day se xanh vi khong co bo "
            "don nao chay, chu khong vi luot nay duoc bao ve.")
        n = admission.reclaim_expired(db, resource="r")
        db.commit()
        assert n == 0, (
            "thu suat cua mot luot DANG CHAY. Cua dong bo dap nhip that ma "
            "`reclaim_expired` van don — han sync dang do bang dong ho cua "
            "lease chu khong bang nhip tim.")
    db.expunge_all()
    con_lai = db.query(ExecutionLease).filter(ExecutionLease.id == ve.id).first()
    assert con_lai is None, (
        "ra khoi khoi ma suat chua duoc nha — `giu_suat_dong_bo` khong con nha.")


def test_DOI_CHUNG_cung_lease_ay_KHONG_ai_dap_nhip_thi_BI_thu(db):
    """⛔ Tien trinh chet (dung ca 18/09): khong ai dap nhip ⇒ phai bi thu."""
    ve, ly_do = _xin(db, holder_id="xac-2")
    assert ve is not None, ly_do
    db.commit()
    _lui_nhip(db, ve.id, 600)

    assert admission.reclaim_expired(db, resource="r") == 1, (
        "lease sync im 600 s van khong bi thu — ve tren vo nghia, vi no xanh ca "
        "khi khong co bo don nao.")


def test_vi_tu_cua_cua_dong_bo_hoi_TIEN_TRIEN_chu_khong_phai_DONG_HO(monkeypatch):
    """🔴 L-08 o cua dong bo: `keep_alive` khong `con_song` la dap nhip VO DIEU KIEN.

    Nhip ay chung minh *luong con song*, khong chung minh *cong viec con tien
    trien* — va no lam han 120 s vua dat KHONG BAO GIO khai hoa chung nao tien
    trinh con song. Ve nay chot rang cua dong bo hoi dung cau hoi, bang dung
    hang so ma cua stream dung (`TRAN_IM_LANG_S`).
    """
    import platform_core.runtime_noi_bo.luong as cua_luong

    bat: dict = {}

    @contextmanager
    def _keep_alive_gia(lease_id, con_song=None):
        bat["lease_id"] = lease_id
        bat["con_song"] = con_song
        yield

    monkeypatch.setattr(admission, "keep_alive", _keep_alive_gia)
    monkeypatch.setattr(cua_luong, "_nha_suat", lambda i: None)

    suat = cua_luong.SuatDongBo("lease-x", "w1")
    with cua_luong.giu_suat_dong_bo(suat):
        pass

    con_song = bat.get("con_song")
    assert con_song is not None, (
        "`giu_suat_dong_bo` dap nhip VO DIEU KIEN — dung loi noi doi cua L-08. "
        "Han 120 s se khong bao gio khai hoa khi tien trinh con song ma cong "
        "viec da bi bo roi.")

    # Luot da giu suat rat lau (dong ho tuyet doi vuot xa 120 s) nhung cong viec
    # VUA nhuc nhich ⇒ con song. Day la ve "khong phai dong ho".
    suat.luc_khoi_cuoi = time.monotonic() - 3600
    suat.cham()
    assert con_song() is True, (
        "vi tu bao chet mot luot vua co tien trien — no dang do DONG HO cua "
        "lease chu khong do tien trien, va se giet luot dang chay dung.")

    # Im qua tran ⇒ luong nhip tu nha (lop 2), khong cho ai tinh co don ho.
    suat.luc_khoi_cuoi = time.monotonic() - (admission.TRAN_IM_LANG_S + 1)
    assert con_song() is False, (
        f"im qua TRAN_IM_LANG_S={admission.TRAN_IM_LANG_S}s van bao con song — "
        "lop 2 khong con khai hoa.")


def test_moc_tien_trien_duoc_CAP_NHAT_moi_lan_goi_may_B():
    """Noi hai dau lai: `goi_dong_bo_co_xep_lai` phai `cham()` moi luot thu.

    ⚠️ Mot vi tu doc mot moc khong ai cap nhat se bao chet sau dung mot `TRAN_IM_LANG_S`
       ke tu luc VAO KHOI — tuc lai la mot dong ho, chi cham hon.
    """
    import inspect

    import platform_core.runtime_noi_bo.luong as cua_luong

    ma = inspect.getsource(cua_luong.goi_dong_bo_co_xep_lai)
    assert ".cham()" in ma, (
        "khong ai CAP NHAT moc tien trien o duong goi dong bo — vi tu `con_song` "
        "se thay im lang ngay ca khi mot luot xep lai dang chay.")


def test_vi_tu_dong_bo_dung_DUNG_hang_so_cua_cua_stream():
    """Hai cho khai cung mot dieu ma khong ai bat khop — khuon nay da can du an
    nay nhieu lan (`test_1247`). Cua dong bo phai HOI `admission.TRAN_IM_LANG_S`."""
    import inspect

    import platform_core.runtime_noi_bo.luong as cua_luong

    ma = inspect.getsource(cua_luong.giu_suat_dong_bo)
    assert "admission.TRAN_IM_LANG_S" in ma, (
        "cua dong bo chep tay mot con so thay vi hoi `admission.TRAN_IM_LANG_S` "
        "— doi hang so kia se KHONG doi hanh vi, va bo test van xanh rong.")


# ── 5. Tien: thu hoi suat KHONG dong vao so, va hoan dung MOT lan ─────────────

def test_thu_hoi_suat_KHONG_dong_vao_SO_TIEN_va_hoan_dung_MOT_lan(db):
    """💰 Suat va tien la HAI so doc lap. Thu hoi suat cham vao so tien la mo
    duong thu hai ket so cho cung mot luot — dung thu INV cua phuong an C cam."""
    from sqlalchemy import func, select

    from platform_core import credit
    from platform_core.models import CreditEntry
    from tests.conftest import bao_dam_user

    bao_dam_user(db, "u_sync")
    credit.cap_tay(db, "u_sync", 100, by="test")
    credit.giu_cho(db, "u_sync", 30, "rid-sync")
    db.commit()
    assert credit.so_du(db, "u_sync") == 70

    ve, ly_do = _xin(db, user_id="u_sync", holder_id="rid-sync")
    assert ve is not None, ly_do
    db.commit()
    _lui_nhip(db, ve.id, admission.ORPHAN_TIMEOUT_SYNC.total_seconds() + 1)

    assert admission.reclaim_expired(db, resource="r") == 1
    db.commit()
    assert credit.so_du(db, "u_sync") == 70, (
        "thu hoi suat da dong vao so tien. Suat va tien la hai so doc lap: bo "
        "don suat khong biet gi ve `da_quyet_toan`, nen no khong duoc quyet dinh "
        "so phan mot khoan giu.")

    # Duong ra cua chinh cua (hoan) chay SAU khi suat da bi thu — va van dung
    # MOT lan, du no duoc goi hai lan (luoi + `finally`).
    credit.hoan(db, "u_sync", "rid-sync")
    db.commit()
    credit.hoan(db, "u_sync", "rid-sync")
    db.commit()

    assert credit.so_du(db, "u_sync") == 100
    so_dong_hoan = db.execute(
        select(func.count()).select_from(CreditEntry).where(
            CreditEntry.job_id == "rid-sync",
            CreditEntry.kind == credit.CREDIT_REFUND)).scalar_one()
    assert so_dong_hoan == 1, (
        f"co {so_dong_hoan} but toan hoan cho mot luot — hoan hai lan la tra "
        "tien thua that.")
