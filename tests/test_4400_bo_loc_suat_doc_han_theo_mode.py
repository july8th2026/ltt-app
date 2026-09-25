"""Khoa chet o TANG NEN: bo loc suat cua `jobs.claim` doc han mo coi CHUNG,
nhung `admission.reclaim_expired` thu hoi theo TUNG MODE.

🔴 TAI HIEN TREN WORKER PRODUCTION THAT, 25/09/2026.

    run asvr_39a2bc9fc8d042ffacd6d941bcd1e15
      job 33c1c0c6 (asv_gpu.audio_prepare) giu lease 84022f68-...
      tai nguyen tach_nguon_cuc_bo, slot 0, mode='job'
      worker bi restart boi deploy; nhip cuoi 07:15:59Z
      job ve terminal (error) 07:21Z — nhung LEASE VAN CON luc 07:33Z

    run asvr_9fc9cc89bb104c06bb190fa3ac47bd3
      nop asv_gpu.audio_prepare (job 59adb210) ~07:30Z
      => nam `queued`, KHONG worker nao trong 8 worker production nhat len

⭐ VONG TRON. Hai ben doc hai con so khac nhau cho CUNG MOT cau hoi
   "lease nay con song khong":

       reclaim_expired       : ORPHAN_TIMEOUT_JOB     = 300 s  (5 phut)
       _con_cho_tai_nguyen   : ORPHAN_TIMEOUT         = 1200 s (20 phut)

   Voi lease `mode='job'` cua mot worker da chet, khe 5 -> 20 phut co tinh chat
   nay: bo loc claim con tinh lease la CON SONG, nen moi job tren tai nguyen ay
   bi GIAU khoi `jobs.claim`; khong worker nao nhat; nen `admission.acquire` /
   `_giu_slot_trong` — **thu duy nhat** goi `reclaim_expired` tren duong nong —
   khong bao gio toi; nen lease khong duoc thu hoi.

   => Thu duy nhat don duoc lease treo lai bi gac sau chinh cai lease ay.
      Hang doi chet dung 15 phut.

⚠️ Bo loc nay la **bo loc co hoi, khong phai khoa** (docstring cua
   `_con_cho_tai_nguyen`). Phep kiem duoi day KHONG doi no thanh trong tai —
   lop gianh that van la `UNIQUE(resource, slot)`. No chi doi mot dieu: nguong
   "con song" cua hai duong phai la MOT.
"""
from __future__ import annotations

import ast
import pathlib
from datetime import datetime, timedelta, timezone

import pytest


GOC = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'khoa_chet.db').as_posix()}")
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


def _lease_cu(db, *, resource: str, mode: str, tuoi: timedelta):
    """Mot lease dang nam trong bang voi nhip tim da cu `tuoi`.

    ⛔ Ghi nhip tim NAIVE: cot la `DateTime(timezone=True)` nhung SQLite cua bo
       test luu khong mui gio — dung dung khuon `tests/test_313` da chay that.
    """
    from platform_core.llm import admission
    from platform_core.models import ExecutionLease

    giu = admission.acquire(db, resource=resource, slots=1, user_id="u_chu",
                            mode=mode, holder_id="worker-da-chet")
    if isinstance(giu, tuple):
        giu = giu[0]
    assert giu is not None
    lease = db.get(ExecutionLease, giu.id)
    lease.heartbeat_at = datetime.now(timezone.utc).replace(tzinfo=None) - tuoi
    db.flush()
    return lease


def _nop(db, *, resource: str):
    from platform_core import jobs

    return jobs.submit(db, user_id="u_khach", app_slug="ltt_llm",
                       job_type="ltt_llm.chat", params={},
                       admission_resource=resource, admission_slots=1)


# ---------------------------------------------------------------------------
# 1. Chinh ca production: lease `mode='job'` qua han CUA NO (300 s)
# ---------------------------------------------------------------------------

def test_claim_thay_job_khi_lease_job_qua_han_300s(db):
    """🔴 Ca 25/09: nhip cuoi cach day 6 phut > `ORPHAN_TIMEOUT_JOB` (5 phut).

    `reclaim_expired` da coi lease nay la mo coi. Bo loc suat thi chua — nen job
    bi giau, va khong ai goi `reclaim_expired` de phat hien ra dieu do.
    """
    from platform_core import jobs
    from platform_core.llm import admission

    assert admission.ORPHAN_TIMEOUT_JOB < timedelta(minutes=6) \
        < admission.ORPHAN_TIMEOUT, "tien de: 6 phut nam DUNG trong khe 5->20"

    _lease_cu(db, resource="tach_nguon_cuc_bo", mode="job",
              tuoi=timedelta(minutes=6))
    job = _nop(db, resource="tach_nguon_cuc_bo")
    db.commit()

    nhat = jobs.claim(db, worker_id="w1")
    assert nhat is not None and nhat.id == job.id, (
        "lease mode='job' im 6 phut da qua `ORPHAN_TIMEOUT_JOB` (300 s) — "
        "`reclaim_expired` coi no la mo coi, nen bo loc suat cung phai coi no "
        "la CHET. Con tinh no la dang chiem suat = hang doi chet dung toi phut "
        "thu 20, va khong ai goi duoc `reclaim_expired` de pha vong tron.")


def test_co_job_dang_cho_tai_nguyen_khong_ke_lease_job_qua_han(db):
    """Cung mot menh de o duong `co_job_dang_cho_tai_nguyen` (bao thuc worker).

    Hai ham cung di qua `_con_cho_tai_nguyen`, nen mot phep kiem khong du: neu
    ai sua rieng `claim` thi ca nay bat.
    """
    from platform_core import jobs

    _lease_cu(db, resource="tach_nguon_cuc_bo", mode="job",
              tuoi=timedelta(minutes=6))
    _nop(db, resource="tach_nguon_cuc_bo")
    db.commit()

    assert jobs.co_job_dang_cho_tai_nguyen(db) is False, (
        "job nhat duoc ngay (lease da mo coi) => khong phai 'dang cho tai nguyen'")


# ---------------------------------------------------------------------------
# 2. DOI CHUNG — ⛔ ban sua KHONG duoc la "bo qua moi lease"
#
# ⚠️ Khong co muc nay thi `return true_()` cung xanh muc 1, va ta da bien mot
#    bo loc co hoi thanh mot cai khong loc gi.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode,tuoi_song", [
    ("job", timedelta(seconds=60)),
    ("stream", timedelta(seconds=30)),
    ("sync", timedelta(seconds=30)),
    ("", timedelta(minutes=3)),
])
def test_lease_con_dap_nhip_van_giu_suat(db, mode, tuoi_song):
    """Lease con song (theo han CUA MODE no) van phai giau job — nhu truoc."""
    from platform_core import jobs

    _lease_cu(db, resource="r_doi_chung", mode=mode, tuoi=tuoi_song)
    _nop(db, resource="r_doi_chung")
    db.commit()

    assert jobs.claim(db, worker_id="w1") is None, (
        f"lease mode={mode!r} im {tuoi_song.total_seconds():.0f}s van trong han "
        "cua chinh no => suat con bi chiem, job chua duoc nhat")
    assert jobs.co_job_dang_cho_tai_nguyen(db) is True


@pytest.mark.parametrize("mode,tuoi_chet", [
    ("job", timedelta(seconds=301)),
    ("stream", timedelta(seconds=181)),
    ("sync", timedelta(seconds=121)),
])
def test_moi_mode_co_han_rieng_va_bo_loc_ton_trong_dung_han_do(db, mode, tuoi_chet):
    """Ba mode, ba han. `stream` (180 s) va `sync` (120 s) cung tung mac khe nay.

    ⭐ Khong chi `job`: L-11 (stream) va su co 18/09 (sync) da ha han cua CHUNG
       trong `reclaim_expired`, nhung bo loc suat khong he biet — nen ca hai
       cung mang chinh vong tron nay, chi voi khe rong hon (3 -> 20 va 2 -> 20
       phut).
    """
    from platform_core import jobs

    _lease_cu(db, resource=f"r_{mode}", mode=mode, tuoi=tuoi_chet)
    job = _nop(db, resource=f"r_{mode}")
    db.commit()

    nhat = jobs.claim(db, worker_id="w1")
    assert nhat is not None and nhat.id == job.id, (
        f"lease mode={mode!r} im {tuoi_chet.total_seconds():.0f}s da qua han "
        "cua chinh no trong `reclaim_expired` — bo loc suat phai doc CUNG han do")


def test_mode_la_khong_biet_van_dung_han_chung(db):
    """Mode ngoai bang (`video_crawler/kho_tai_khoan.py` co y dung mot ten khac)
    van roi vao `ORPHAN_TIMEOUT` chung — hanh vi cu, tung byte."""
    from platform_core import jobs
    from platform_core.llm import admission

    _lease_cu(db, resource="r_la", mode="kho_tk", tuoi=timedelta(minutes=10))
    _nop(db, resource="r_la")
    db.commit()

    assert admission.ORPHAN_TIMEOUT > timedelta(minutes=10), "tien de"
    assert jobs.claim(db, worker_id="w1") is None, (
        "mode ngoai bang khong duoc bi thu hoi som hon `reclaim_expired` thu — "
        "`kho_tai_khoan.py` dua vao dung dieu do de giu tai khoan qua mot luot "
        "tai dai")


# ---------------------------------------------------------------------------
# 3. BANH COC — ⭐ doc AST, ⛔ khong so chuoi
#
# ⚠️ Mot phep kiem so chuoi ngay 24/09 da TU KHOP VAO DOCSTRING CUA CHINH NO va
#    do gia. Nen o day ta di qua cay cu phap: `ast.ImportFrom` va `ast.Call` la
#    su that ve thi hanh, docstring thi khong.
# ---------------------------------------------------------------------------

def _ham(tep: pathlib.Path, ten: str) -> ast.FunctionDef:
    cay = ast.parse(tep.read_text(encoding="utf-8"))
    for node in ast.walk(cay):
        if isinstance(node, ast.FunctionDef) and node.name == ten:
            return node
    raise AssertionError(f"khong tim thay ham {ten} trong {tep.name}")


#: Ho helper mot-nguon trong `admission.py`. `han_mo_coi` la GOC; hai cai kia
#: la vo boc (mot moc `datetime`, mot bieu thuc SQL) va phai goi goc.
GOC_HAN = "han_mo_coi"
HO_HELPER = ("han_mo_coi", "moc_lease_con_song", "bieu_thuc_lease_con_song")


def _ten_duoc_goi(ham: ast.FunctionDef) -> set[str]:
    return {
        (node.func.attr if isinstance(node.func, ast.Attribute)
         else getattr(node.func, "id", ""))
        for node in ast.walk(ham) if isinstance(node, ast.Call)
    }


def test_bo_loc_suat_khong_con_doc_mot_HANG_CHUNG():
    """`_con_cho_tai_nguyen` ⛔ khong duoc doc `ORPHAN_TIMEOUT` nua.

    Do la chinh cai import CUC BO trong than ham (dong 351 truoc ban va) da che
    hang `ORPHAN_TIMEOUT` = 5 phut o dau chinh tep nay. Mot cai ten, hai gia
    tri, cung mot tep.
    """
    ham = _ham(GOC / "platform_core" / "jobs.py", "_con_cho_tai_nguyen")
    xau = []
    for node in ast.walk(ham):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name.startswith("ORPHAN_TIMEOUT"):
                    xau.append(f"{node.module}.{alias.name}")
        if isinstance(node, ast.Name) and node.id.startswith("ORPHAN_TIMEOUT"):
            xau.append(node.id)
        if isinstance(node, ast.Attribute) and node.attr.startswith("ORPHAN_TIMEOUT"):
            xau.append(node.attr)
    assert not xau, (
        "`_con_cho_tai_nguyen` con doc hang mo coi truc tiep: " + ", ".join(xau)
        + f" — no phai goi `admission.{HO_HELPER[2]}()` de khong lech khoi "
          "`reclaim_expired` duoc nua")


def test_hai_duong_deu_doc_MOT_nguon_han():
    """⭐ Canh cho trong, khong chi sua: `_con_cho_tai_nguyen` va
    `reclaim_expired` phai lay han tu CUNG mot goc `han_mo_coi`.

    Hai ve, ca hai doc bang AST:
      (a) moi duong goi mot thanh vien cua ho helper;
      (b) moi vo boc trong ho ay THUC SU goi `han_mo_coi` — neu khong thi (a)
          chi la hai ham trung ten, khong phai mot nguon.

    Neu mot ngay ai do ha `ORPHAN_TIMEOUT_JOB` lan nua, ca hai duong doi theo —
    chung ⛔ khong the lech nhau duoc nua.
    """
    tep_adm = GOC / "platform_core" / "llm" / "admission.py"

    goi = {}
    for ten_tep, ten_ham in (("platform_core/jobs.py", "_con_cho_tai_nguyen"),
                             ("platform_core/llm/admission.py", "reclaim_expired")):
        goi[ten_ham] = _ten_duoc_goi(_ham(GOC / ten_tep, ten_ham))

    thieu = [h for h, c in goi.items() if not c & set(HO_HELPER)]
    assert not thieu, (
        f"khong goi helper mot-nguon {HO_HELPER}: {thieu}; "
        f"da thay: { {k: sorted(v) for k, v in goi.items()} }")

    # (b) TRUY BAC CAU trong ho: mot vo boc duoc phep goi vo boc khac, nhung
    #     duong di phai KET THUC o `han_mo_coi`. Chi nhin mot buoc thi mot chuoi
    #     hop le bi bao do, con mot vo boc tu tinh `now - HANG` lai lot.
    for vo_boc in HO_HELPER:
        if vo_boc == GOC_HAN:
            continue
        da_tham, con_lai = set(), [vo_boc]
        while con_lai:
            ten = con_lai.pop()
            if ten in da_tham:
                continue
            da_tham.add(ten)
            con_lai += [t for t in _ten_duoc_goi(_ham(tep_adm, ten))
                        if t in HO_HELPER]
        assert GOC_HAN in da_tham, (
            f"`{vo_boc}` khong lan nao toi duoc `{GOC_HAN}` (di qua {sorted(da_tham)}) "
            "— no dang tu tinh han, tuc ta co HAI nguon deo mot cai ten ho")

    # (c) Va goc thi ⛔ khong duoc co nguoi thu hai: chi `han_mo_coi` moi duoc
    #     doc thang cac hang `ORPHAN_TIMEOUT*` trong `admission.py`.
    cay = ast.parse(tep_adm.read_text(encoding="utf-8"))
    pham = []
    for node in ast.walk(cay):
        if not isinstance(node, ast.FunctionDef) or node.name == GOC_HAN:
            continue
        for con in ast.walk(node):
            if isinstance(con, ast.Name) and con.id.startswith("ORPHAN_TIMEOUT") \
                    and con.id != "ORPHAN_TIMEOUT":
                pham.append(f"{node.name} doc {con.id}")
    assert not pham, (
        "chi `han_mo_coi` duoc doc cac han THEO MODE; cac ham sau doc thang: "
        + ", ".join(sorted(set(pham)))
        + " — do dung la cach hai duong lech nhau lan truoc")


def test_helper_ton_tai_va_tra_dung_han_cho_tung_mode():
    """Helper la NGUON: no phai biet ca bon han, khong phai ba."""
    from platform_core.llm import admission

    assert hasattr(admission, "han_mo_coi"), \
        "thieu `admission.han_mo_coi(mode)` — nguon chan ly cho 'lease con song'"
    assert admission.han_mo_coi("job") == admission.ORPHAN_TIMEOUT_JOB
    assert admission.han_mo_coi("stream") == admission.ORPHAN_TIMEOUT_STREAM
    assert admission.han_mo_coi("sync") == admission.ORPHAN_TIMEOUT_SYNC
    assert admission.han_mo_coi("kho_tk") == admission.ORPHAN_TIMEOUT
    assert admission.han_mo_coi(None) == admission.ORPHAN_TIMEOUT
    # Y cua nguoi goi (don tay, timeout ngan hon) van phai THANG — `min`, khong
    # phai thay thang. Do la tinh chat `reclaim_expired` da khai tu L-11.
    ngan = timedelta(seconds=5)
    for mode in ("job", "stream", "sync", "", None, "kho_tk"):
        assert admission.han_mo_coi(mode, timeout=ngan) == ngan, (
            f"mode={mode!r}: nguoi goi truyen timeout NGAN hon thi y ho phai thang")


def test_jobs_khong_con_HAI_NGHIA_cho_mot_cai_ten():
    """⭐ `jobs.py` tung co `ORPHAN_TIMEOUT` = 5 phut (han cua DONG `jobs`) va
    mot import cuc bo cung ten = 20 phut (han cua LEASE). Nguoi doc dong 42
    hoan toan hop ly khi tuong dong 351 dung no.

    Nay tep nay ⛔ khong con ten `ORPHAN_TIMEOUT` nao: han cua dong `jobs` mang
    ten `JOB_ORPHAN_TIMEOUT`, va han cua lease chi song trong `admission`.
    """
    from platform_core import jobs

    assert hasattr(jobs, "JOB_ORPHAN_TIMEOUT"), \
        "han mo coi cua DONG `jobs` phai co ten rieng, khong dung ten chung"
    assert jobs.JOB_ORPHAN_TIMEOUT == timedelta(minutes=5)
    assert not hasattr(jobs, "ORPHAN_TIMEOUT"), (
        "`jobs.ORPHAN_TIMEOUT` la cai ten da mang HAI nghia trong cung mot tep "
        "(5 phut o dau tep, 20 phut o import cuc bo trong `_con_cho_tai_nguyen`) "
        "— dung giu lai mot bi danh cho no")


# ---------------------------------------------------------------------------
# 4. NGUOI DOC THU BA — `job_metrics` cung phai doc mot nguon
#
# ⚠️ No KHONG phai trong tai, nhung chinh vi the no nguy theo kieu khac: mot
#    nguoi dang go loi se thay BA cau tra loi khac nhau cho cung cau hoi "lease
#    nay con song khong" va khong biet tin cai nao.
# ---------------------------------------------------------------------------

def test_job_metrics_dem_lease_chet_theo_dung_han_cua_mode(db):
    """`expired_execution_lease_candidates` nghia la "lease ma `reclaim_expired`
    SE XOA" — nen no phai hoi chinh ham ay hoi.

    Truoc 25/09 cho nay do bang mot nguong PHANG 20 phut: mot lease `mode='job'`
    im 6 phut da la mo coi voi `reclaim_expired`, nhung dashboard van dem no la
    `active`. Hai so, mot su that.
    """
    from platform_core import job_metrics

    _lease_cu(db, resource="tach_nguon_cuc_bo", mode="job",
              tuoi=timedelta(minutes=6))
    db.commit()

    snap = job_metrics.snapshot(db)
    assert snap["expired_execution_lease_candidates"] == 1, (
        "lease mode='job' im 6 phut da qua `ORPHAN_TIMEOUT_JOB` — "
        "`reclaim_expired` se xoa no, nen bao cao phai dem no la da chet")
    assert snap["active_execution_leases"] == 0


def test_job_metrics_van_de_nguoi_goi_THU_HEP_duoc(db):
    """`lease_stale_minutes` cua nguoi goi chi duoc lam han NGAN hon (`min`)."""
    from platform_core import job_metrics

    _lease_cu(db, resource="r_hep", mode="sync", tuoi=timedelta(seconds=90))
    db.commit()

    # Mac dinh: 90 s < ORPHAN_TIMEOUT_SYNC (120 s) => con song.
    assert job_metrics.snapshot(db)["active_execution_leases"] == 1
    # Nguoi goi thu hep xuong 1 phut => 90 s da chet.
    hep = job_metrics.snapshot(db, lease_stale_minutes=1)
    assert hep["expired_execution_lease_candidates"] == 1
    assert hep["active_execution_leases"] == 0


def test_ba_nguoi_doc_deu_lan_toi_han_mo_coi():
    """Banh coc AST: ⛔ khong con mot nguoi doc nao tu dung nguong phang.

    Ba cho tra loi cau hoi "lease con song khong" phai cung lan ve `han_mo_coi`.
    """
    for ten_tep, ten_ham in (("platform_core/jobs.py", "_con_cho_tai_nguyen"),
                             ("platform_core/llm/admission.py", "reclaim_expired"),
                             ("platform_core/job_metrics.py", "snapshot")):
        goi = _ten_duoc_goi(_ham(GOC / ten_tep, ten_ham))
        assert goi & set(HO_HELPER), (
            f"{ten_tep}::{ten_ham} khong goi helper mot-nguon {HO_HELPER} — "
            "no dang tu dung mot nguong rieng cho 'lease con song'")


# ---------------------------------------------------------------------------
# 5. LUOI DO — nhip cua watchdog, ⛔ khong phai nhip cua viec don log
# ---------------------------------------------------------------------------

def test_luoi_do_lease_co_ticker_RIENG_theo_nhip_dap():
    """⭐ Loi PHAN LOAI, khong phai loi chinh so.

    `6 gio` KHONG sai cho viec don log request / thong bao / mau metrics; no sai
    vi mot watchdog tinh song-chet KHONG thuoc nhom luu tru. Do la 72x
    `ORPHAN_TIMEOUT_JOB`, va cua so 17 phut quan sat duoc chi la 4,7 % chu ky —
    "khong kich hoat" la ca THUONG.
    """
    from platform_core import job_runner
    from platform_core.llm import admission

    assert job_runner.LEASE_RECLAIM_INTERVAL_S == admission.HEARTBEAT_SECONDS, (
        "watchdog phai chay theo nhip cua chinh thu no canh — va phai DOC hang "
        "`HEARTBEAT_SECONDS`, khong go lai 60")

    sweep = _ham(GOC / "platform_core" / "job_runner.py", "_don_du_lieu_het_han")
    assert "reclaim_expired" not in _ten_duoc_goi(sweep), (
        "`reclaim_expired` lai bi xep vao danh sach luu tru => no quay ve nhip "
        "6 gio. No co ticker rieng (`_quet_lease_mo_coi`)")

    luot = _ham(GOC / "platform_core" / "job_runner.py", "_mot_luot_bao_tri")
    assert "_quet_lease_mo_coi" in _ten_duoc_goi(luot), (
        "khong con ai goi luoi do => lease mo coi cua tai nguyen khong co ai xin "
        "suat se nam mai")
