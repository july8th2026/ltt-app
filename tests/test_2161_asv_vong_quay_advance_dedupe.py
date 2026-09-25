# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.
"""Vong quay NONG cua `auto_scan_video.advance` (NHAT_KY.md 2026-09-25 (chieu)
muc 5): **37.010** job `advance` trong 52,5 phut (~11,7/giay) tren worker
THAT — khuon test `test_448._chay_hang_doi` (mot luong, TUAN TU) chi sinh
**11**, vi khi mot luot `advance` chay thi giai doan truoc DA XONG roi, khong
con gi de quay vong.

Nguyen nhan (da ghi trong nhat ky): `features._nop_dieu_phoi` nop luot ke KHONG
do tre, va khoa dedupe mang `ctx.job_id` cua CHINH job dang goi no -- `job_id`
do LUON khac nhau moi luot, nen khoa LUON moi, nen `jobs.submit` khong bao gio
tim thay job trung de dedupe.

Hai bai duoi day tai hien theo dung yeu cau: **DONG THOI**, khong phai bang
mot luot chay that (`_chay_het_hang_doi` chay tuan tu, xem tren -- khong dung
lai duoc). "Dong thoi" o day nghia la HAI job `advance` CUNG TON TAI, ca hai
CUNG quan sat dung MOT trang thai (giai doan dau con dang chay o "noi khac",
chua xong) -- dung khuon nhat ky muc 5 mo ta, khong phai gia dinh rieng cua
bai kiem.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from platform_core.job_runner import JobContext
from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job
from platform_core import jobs as job_queue

from apps.auto_scan_video import features, jobs as asv_jobs
from tests.test_402_asv_mach_doc_gia import _tao_run, db, kho_tam  # noqa: F401


def _job_advance_con_song(db, run_id: str) -> list[Job]:
    """Moi job `advance` cua run nay con QUEUED/RUNNING -- doc lai tu CSDL,
    khong dung cache doi tuong cu."""
    db.expire_all()
    ds = db.execute(
        select(Job).where(Job.job_type == features.JOB_DIEU_PHOI,
                          Job.status.in_((JOB_QUEUED, JOB_RUNNING)))
    ).scalars().all()
    return [j for j in ds if dict(j.params or {}).get("run_id") == run_id]


def _chay_job_that(db, job: Job) -> dict:
    """Chay DUNG mot job da biet qua handler that (khong qua `claim` -- bai
    kiem chon thu tu tuong minh, xem docstring tung bai). Tra ve ket qua."""
    ctx = JobContext(job.id)
    ctx.job_type = job.job_type
    ket_qua = asv_jobs.handle(dict(job.params), ctx) or {}
    db.expire_all()
    j = db.get(Job, job.id)
    job_queue.complete(db, j, ket_qua)
    db.commit()
    return ket_qua


# ══════════════════════════════════════════════════════════════════════════════
#  Bai 1 -- hai luot CHONG NHAU phai GOP thanh mot, khong fan-out
# ══════════════════════════════════════════════════════════════════════════════

def test_hai_luot_advance_CHONG_NHAU_cung_gen_GOP_thanh_mot_khong_fan_out(
        tmp_path, monkeypatch, db, kho_tam):
    """Mo phong dung tinh huong nhat ky: giai doan dau dang "chay o noi khac"
    (QUEUED, chua xong), va HAI job `advance` doc lap cung ton tai cho CUNG
    mot the he (`gen=0`) -- vi du hai worker cung nhat phai mot ban sao cua
    cung mot tick.

    Truoc ban va: moi job tu chon khoa dedupe rieng (theo `ctx.job_id`) ⇒ CA
    HAI deu tao job KE TIEP cua rieng minh ⇒ 2 job moi cho MOT trang thai.
    Sau ban va: ca hai tinh ra CUNG mot khoa (`(run_id, gen)`) ⇒ luot thu hai
    nhan lai dung job luot dau da tao ⇒ CHI 1 job moi.
    """
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    db.commit()

    # Giai doan dau: gia lap DANG CHAY O NOI KHAC (chua xong). `job_id` khong
    # ton tai trong bang Job -- `_thu_ket_qua_job_con` doc `db.get(Job, ...)`
    # ra None va bo qua (an toan, xem jobs.py); `_nop_giai_doan_san_sang` bo
    # qua giai doan nay vi trang thai da la QUEUED (khong con PENDING).
    stage0 = features.cac_giai_doan(db, run)[0]
    features.danh_dau_dang_chay(db, stage0, "gia-lap-dang-chay-o-noi-khac")
    db.commit()

    # `_tao_run` da nop MOT job `advance` that (`gen=0`, ly_do="tao") -- dung
    # lai no lam `job_a`, khong tao rieng: no la mot job SONG that su, khong
    # phai mot dao cu. `job_b` la BAN SAO CHONG NHAU -- vi du dung `hau_to`
    # khac de tao mot dedupe_key rieng (dung khuon khoa CU, truoc ban va, de
    # dung tao ra hai row doc lap -- gia lap dung tinh huong "hai luot advance
    # chong nhau" ma khong can dung thread that tren SQLite).
    con_ban_dau = _job_advance_con_song(db, run.id)
    assert len(con_ban_dau) == 1, "tien de: _tao_run nop dung 1 job 'tao'"
    job_a = con_ban_dau[0]
    job_a.status = JOB_RUNNING

    job_b = job_queue.submit(
        db, user_id=run.owner_id, app_slug=features.SLUG,
        job_type=features.JOB_DIEU_PHOI,
        params={"run_id": run.id, "owner_id": run.owner_id, "gen": 0},
        dedupe_key=f"asv:advance:{run.id}:gia-lap:worker-b",
        max_attempts=3)
    job_b.status = JOB_RUNNING
    db.commit()
    assert job_a.id != job_b.id, "tien de: hai job DOC LAP, khong phai mot"

    _chay_job_that(db, job_a)
    con_sau_a = _job_advance_con_song(db, run.id)
    # job_a vua chay xong (`done`, khong con "song") va tao 1 job gen=1 moi.
    # `job_b` VAN con song -- no la ban sao CHONG NHAU, chua duoc chay.
    assert len(con_sau_a) == 2, (
        f"sau luot a: 1 job gen=1 moi + job_b van song = 2, thuc te "
        f"{len(con_sau_a)}")
    gen1_sau_a = [j for j in con_sau_a if j.id != job_b.id]
    assert len(gen1_sau_a) == 1, "dung 1 job gen=1 duoc tao boi luot a"
    job_gen1 = gen1_sau_a[0]

    _chay_job_that(db, job_b)
    con_sau_b = _job_advance_con_song(db, run.id)

    assert len(con_sau_b) == 1, (
        "hai luot advance CHONG NHAU (cung gen=0) phai GOP thanh MOT job ke "
        f"tiep, khong fan-out -- thuc te con {len(con_sau_b)} job song sau "
        "khi ca hai da chay (ky vong 1, tung do la 2 truoc ban va)")
    assert con_sau_b[0].id == job_gen1.id, (
        "job gen=1 con lai sau luot b phai la DUNG job gen=1 luot a da tao "
        "(dedupe gop vao no), khong phai mot job gen=1 THU HAI")


# ══════════════════════════════════════════════════════════════════════════════
#  Bai 2 -- do tre: CHI khi khong nop duoc gi, KHONG lam cham duong binh thuong
# ══════════════════════════════════════════════════════════════════════════════

def test_do_tre_chi_ap_dung_khi_khong_nop_duoc_gi_duong_binh_thuong_KHONG_cham(
        tmp_path, monkeypatch, db, kho_tam):
    """Luot 1 (`tao` -> nop giai doan dau THAT, co viec) phai KHONG do tre.
    Luot 2 (giai doan dau VAN dang chay, khong con gi de nop) phai CO do tre
    it nhat `NHIP_DIEU_PHOI_S` giay -- dung hai nhanh NHAT_KY.md muc 5 + 6."""
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    db.commit()

    # Chi co dung MOT job queued luc nay (job "tao"), claim() chon no chac
    # chan.
    job_tao = job_queue.claim(db, worker_id="w-tao")
    assert job_tao is not None and job_tao.job_type == features.JOB_DIEU_PHOI
    db.commit()
    ket_qua_1 = _chay_job_that(db, job_tao)
    assert ket_qua_1.get("da_nop"), (
        "luot 'tao' phai nop duoc giai doan dau that -- tien de cua bai nay")

    con_1 = _job_advance_con_song(db, run.id)
    assert len(con_1) == 1
    job_ke_1 = con_1[0]
    bay_gio = datetime.now(timezone.utc)
    han = job_ke_1.next_run_at
    if han is not None and han.tzinfo is None:
        han = han.replace(tzinfo=timezone.utc)
    assert han is None or han <= bay_gio + timedelta(seconds=1), (
        f"duong NOP THAT (da_nop khac rong) khong duoc do tre -- next_run_at="
        f"{job_ke_1.next_run_at!r}, bay gio={bay_gio!r}")

    # Luot 2: giai doan dau VAN dang chay that (job cua no van QUEUED, chua
    # hoan tat) -- luot nay khong con gi de nop.
    job_ke_1.status = JOB_RUNNING
    db.commit()
    ket_qua_2 = _chay_job_that(db, job_ke_1)
    assert not ket_qua_2.get("da_nop"), (
        "luot 2 phai KHONG nop duoc gi -- tien de cua nhanh do tre")

    con_2 = _job_advance_con_song(db, run.id)
    assert len(con_2) == 1
    job_ke_2 = con_2[0]
    han2 = job_ke_2.next_run_at
    if han2 is not None and han2.tzinfo is None:
        han2 = han2.replace(tzinfo=timezone.utc)
    assert han2 is not None, "luot khong nop duoc gi phai co next_run_at"
    assert han2 >= bay_gio + timedelta(seconds=features.NHIP_DIEU_PHOI_S - 0.5), (
        f"luot khong nop duoc gi phai bi hen cham it nhat {features.NHIP_DIEU_PHOI_S}"
        f" giay -- next_run_at={job_ke_2.next_run_at!r}")
