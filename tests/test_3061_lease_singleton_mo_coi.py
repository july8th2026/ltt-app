"""Lease singleton mo coi: ai don, va sau bao lau.

🔴 **Do duoc tren CSDL production 26/09 (chi doc):**

       singleton_leases
         name         = 'asvcc:82839212a2870b3390df2830cb36114bda'
         holder       = 'DESKTOP-H9AGFUQ:25716:6a97967b-c927-437d'
         acquired_at  = 2026-09-25 15:57:07
         heartbeat_at = 2026-09-25 15:57:37   <- dung tu 25/09, hon MOT NGAY
         (tien trinh 25716 da chet)

   Dong `maintenance` canh no co nhip tim **tuoi** ⇒ co che nhip tim **co chay**.
   Thieu la buoc **DON**.

⭐ **Vi sao `reclaim_expired` khong bat duoc no.** `leases.acquire` co goi
   `reclaim_expired(name=...)`, nhung phep do ay **chi nham DUNG MOT TEN** — cai
   ten ma nguoi goi dang xin. Ten `asvcc:<bam noi dung>` la ham bam cua mot noi
   dung cu the: khong ai xin lai dung ten do thi khong ai thu hoi no. Tuc cau tra
   loi truoc ban sua la **KHONG BAO GIO** — khong phai "cham", ma la "khong".

   Do la mot lo hong **khac loai** voi "thu hoi cham": `reclaim_expired` van dung
   cho viec cua no (gianh lai mot vai tro). Thieu la mot **nguoi quet** khong phu
   thuoc vao viec co ai xin lai ten do hay khong — dung thu `gpu_lease.py` da co
   (`reclaim_orphans`, `ORPHAN_TIMEOUT`).
"""
from __future__ import annotations

import ast
import inspect
import pathlib
from datetime import datetime, timedelta, timezone

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Ten mo coi that tren production, giu nguyen hinh dang (tien to + bam).
TEN_MO_COI = "asvcc:82839212a2870b3390df2830cb36114bda"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'lease_mo_coi.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session

    Base.metadata.create_all(get_engine())
    gen = get_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def _dung_nhip(db, ten: str, *, holder: str, tuoi: timedelta):
    """Dung mot lease co nhip tim CU `tuoi` — chu da chet, khong ai nha."""
    from platform_core.models import SingletonLease

    khi = datetime.now(timezone.utc) - tuoi
    row = SingletonLease(name=ten, holder=holder, acquired_at=khi, heartbeat_at=khi)
    db.add(row)
    db.commit()
    return row


def _con_lai(db) -> set[str]:
    from sqlalchemy import select

    from platform_core.models import SingletonLease
    return set(db.execute(select(SingletonLease.name)).scalars().all())


# -- Phep kiem DO ------------------------------------------------------------

def test_DO_lease_mo_coi_KHAC_TEN_khong_bao_gio_duoc_don(db):
    """Tai hien dung dong production: mot ngay troi qua, vong bao tri van tick.

    Truoc ban sua: `maintenance` duoc gianh lai binh thuong, con `asvcc:...` **con
    nguyen** — vi `reclaim_expired` chi nham cai ten dang duoc xin.
    """
    from platform_core import leases

    _dung_nhip(db, TEN_MO_COI, holder="DESKTOP-H9AGFUQ:25716:6a97967b",
               tuoi=timedelta(days=1, minutes=7))
    # Vong bao tri cua dich vu dang song: no xin lease CUA NO, moi chu ky.
    for _ in range(3):
        cho = leases.acquire(db, name=leases.MAINTENANCE, holder="dich-vu-song")
        assert cho is not None
        leases.release(db, cho)

    assert TEN_MO_COI not in _con_lai(db), (
        "lease mo coi cua mot chu da chet 1 ngay van con: khong ai DON dong mo "
        "coi, chi co nguoi GIANH LAI dung mot ten")


def test_DO_thu_hoi_mo_coi_tra_ve_SO_DONG_da_don(db):
    """Cung khuon `gpu_lease.reclaim_orphans`: tra so dong thu hoi duoc."""
    from platform_core import leases

    _dung_nhip(db, TEN_MO_COI, holder="chu-chet", tuoi=timedelta(days=1))
    _dung_nhip(db, "asvcc:khac", holder="chu-chet-2", tuoi=timedelta(hours=5))
    assert leases.reclaim_orphans(db) == 2
    assert leases.reclaim_orphans(db) == 0, "lan hai khong con gi de don"


def test_khong_CUOP_lease_cua_chu_con_song(db):
    """⛔ Nguong quet phai RONG hon moi TTL, khong thi no cuop lease dang dung.

    `apps/vps/jobs.KHOA_MAY_TTL` la **45 phut** va duong do ⛔ KHONG dap nhip —
    nhip tim cua no dung yen tu luc gianh. Mot nguoi quet lay nguong 2 phut se
    xoa khoa cua mot job cai VPS dang chay, va hai job se cung lam viec tren
    mot may (dung su co 25/08 ma khoa ay sinh ra de chan).
    """
    from platform_core import leases

    _dung_nhip(db, "vps-may:100", holder="worker-song", tuoi=timedelta(minutes=50))
    _dung_nhip(db, "asvcc:dang-tinh", holder="worker-song-2", tuoi=timedelta(seconds=5))
    assert leases.reclaim_orphans(db) == 0
    assert _con_lai(db) == {"vps-may:100", "asvcc:dang-tinh"}


def test_BANH_COC_nguong_quet_RONG_hon_moi_TTL_trong_kho(db):
    """Mot lease moi voi TTL dai hon nguong quet se bi cuop giua chung.

    ⭐ Do bang cach **doc ma**, khong bang cach nho: tim moi `leases.acquire(...,
       ttl=<hang so>)` trong kho, giai gia tri hang so ay, va chot no nho hon
       `ORPHAN_TIMEOUT`. Mot phien them `ttl=timedelta(hours=6)` se lam do o day
       thay vi lam mat lease trong production.
    """
    from platform_core import leases

    ttl = _moi_ttl_dung_voi_acquire()
    assert ttl, "khong tim duoc `leases.acquire(..., ttl=...)` nao — phep do hong"
    for cho, ten, gt in ttl:
        assert gt < leases.ORPHAN_TIMEOUT, (
            f"{cho}: {ten} = {gt} >= ORPHAN_TIMEOUT "
            f"({leases.ORPHAN_TIMEOUT}) ⇒ nguoi quet se cuop lease dang dung")


def test_dung_lai_KHUON_cua_gpu_lease(db):
    """⛔ Khong dat khuon moi: kho da co mot khuon da chung minh trong production.

    Chot **hinh dang** (ten ham, ten tham so, kieu tra ve) de hai co che khong
    lech nhau — hai khuon cho cung mot viec la hai cho se lech.
    """
    from platform_core import gpu_lease, leases

    a = inspect.signature(gpu_lease.reclaim_orphans)
    b = inspect.signature(leases.reclaim_orphans)
    assert list(a.parameters)[1:] == list(b.parameters)[1:] == ["timeout"]
    assert a.parameters["timeout"].kind is inspect.Parameter.KEYWORD_ONLY
    assert b.parameters["timeout"].kind is inspect.Parameter.KEYWORD_ONLY
    assert isinstance(leases.ORPHAN_TIMEOUT, timedelta)


def test_reclaim_expired_VAN_lam_viec_cua_no(db):
    """Nguoi quet la **them**, khong thay: gianh lai mot vai tro van theo TTL
    rieng cua no (2 phut), khong phai theo nguong quet (rong hon nhieu)."""
    from platform_core import leases

    _dung_nhip(db, leases.MAINTENANCE, holder="chu-chet",
               tuoi=timedelta(minutes=30))
    moi = leases.acquire(db, name=leases.MAINTENANCE, holder="chu-moi")
    assert moi is not None, "vai tro bao tri phai duoc gianh lai sau TTL 2 phut"
    assert leases.current_holder(db, name=leases.MAINTENANCE) == "chu-moi"


# -- Doc ma: cac TTL dung voi `leases.acquire` -------------------------------

def _gia_tri_timedelta(node: ast.AST) -> timedelta | None:
    if not (isinstance(node, ast.Call)
            and getattr(node.func, "id", getattr(node.func, "attr", "")) == "timedelta"):
        return None
    kw = {}
    for k in node.keywords:
        if not isinstance(k.value, ast.Constant) or not isinstance(
                k.value.value, (int, float)):
            return None
        kw[k.arg] = k.value.value
    try:
        return timedelta(**kw)
    except TypeError:
        return None


def _moi_ttl_dung_voi_acquire() -> list[tuple[str, str, timedelta]]:
    """[(cho, ten hang so, gia tri)] moi `leases.acquire(..., ttl=<Name>)`."""
    ket: list[tuple[str, str, timedelta]] = []
    for thu_muc in ("apps", "platform_core", "server"):
        for p in sorted((GOC / thu_muc).rglob("*.py")):
            try:
                cay = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError):
                continue
            hang: dict[str, timedelta] = {}
            for n in ast.walk(cay):
                if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(
                        n.targets[0], ast.Name):
                    gt = _gia_tri_timedelta(n.value)
                    if gt is not None:
                        hang[n.targets[0].id] = gt
            for n in ast.walk(cay):
                if not (isinstance(n, ast.Call)
                        and getattr(n.func, "attr", "") == "acquire"
                        and getattr(getattr(n.func, "value", None), "id", "") == "leases"):
                    continue
                for k in n.keywords:
                    if k.arg != "ttl":
                        continue
                    ten = getattr(k.value, "id", "")
                    gt = hang.get(ten) or _gia_tri_timedelta(k.value)
                    if gt is not None:
                        ket.append((f"{p.relative_to(GOC).as_posix()}:{n.lineno}",
                                    ten or "timedelta(...)", gt))
    return ket


if __name__ == "__main__":       # pragma: no cover
    for cho, ten, gt in _moi_ttl_dung_voi_acquire():
        print(f"{cho:45s} {ten:18s} {gt}")
