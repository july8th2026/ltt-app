"""Workflow V2 trên PostgreSQL thật: hai vòng động cơ song song, crash giữa chừng.

Chạy qua `tools/check_multiproc.py` (tự dựng CSDL scratch theo cây).
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlalchemy as sa

from tests import pg_scratch

pytestmark = pg_scratch.skip_without_postgres()

#: Khoa advisory Postgres (muc phien) giu SUOT tep nay dang chay mot test —
#: xem ly do o fixture `pg`. So bat ky, chi can khong dung so nao khac trong
#: kho (khong phoi hop bang dat ten dep, phoi hop bang mot hang co dinh).
_KHOA_LOCK_KEY = 172012001720   # tuy y, gan voi ten tep "1720" de de nhan dien

#: Giay moi luong giu transaction mo trong ve doi chung ben duoi. Du dai de
#: mot lan xep hang lo ra trong tong thoi gian, du ngan de bai kiem khong cham.
_NGU = 0.6


@pytest.fixture()
def pg(monkeypatch):
    url = pg_scratch.scratch_url()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    # `pytest-xdist -n 2` (hoac hon) phan hai test CUA CHINH TEP NAY cho hai
    # worker KHAC NHAU, va ca hai tro ve CUNG MOT CSDL scratch (`scratch_url`
    # doc cung mot bien moi truong). Khong co gi ngan hai worker goi
    # `drop_all`/`create_all` CUNG LUC — da thay that (23/09): hai `CREATE
    # TABLE` dung ten dua nhau tren catalog he thong Postgres, nem
    # `UniqueViolation` ngay o buoc dung fixture. Ke ca khong dung DDL, hai
    # bai test chay THAT SU song song tren CUNG schema se ghi de du lieu cua
    # nhau (vd `WorkflowRun` cua bai nay lo vao truy van "moi run SUCCEEDED"
    # cua bai kia). `xdist_group` KHONG giai duoc: no chi co hieu luc voi
    # `--dist=loadgroup`, va khong noi goi lenh nao o day dam bao co co.
    # Khoa advisory cua chinh Postgres thi dung bat ke `-n` bao nhieu hay
    # `--dist` gi: worker thua vao SAU se doi tai `pg_advisory_lock` cho toi
    # khi worker truoc giai phong (fixture teardown), nen hai test trong tep
    # nay luon chay TUAN TU voi nhau tren cung mot CSDL - it hai worker khac
    # (vd tu `test_214`) van chay song song binh thuong.
    khoa_engine = sa.create_engine(url, future=True)
    khoa_conn = khoa_engine.connect()
    khoa_conn.execute(sa.text("SELECT pg_advisory_lock(:k)"), {"k": _KHOA_LOCK_KEY})

    try:
        dbmod.Base.metadata.drop_all(dbmod.get_engine())
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        yield dbmod
    finally:
        dbmod.reset_engine()
        khoa_conn.execute(sa.text("SELECT pg_advisory_unlock(:k)"), {"k": _KHOA_LOCK_KEY})
        khoa_conn.close()
        khoa_engine.dispose()


def _mo(dbmod):
    return lambda: next(dbmod.get_session())


def _chuan_bi(dbmod, monkeypatch, so_run=10):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    from tests.conftest import bao_dam_user
    from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC, _draft
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    db = _mo(dbmod)()
    w = _draft(db)
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    # `credit.nap` ghi vao `credit_entries`, cot `user_id` mang khoa ngoai
    # tham chieu `users.id` (F-01, audit 2026-08-07) — Postgres THAT SU thi
    # ep FK nay (SQLite mac dinh KHONG, nen cac test cung dong cua tren
    # SQLite khong bao gio bat duoc thieu buoc nay). `bao_dam_user` la
    # helper dung chung cua kho (`tests/conftest.py`), tao mot user gia mang
    # dung id neu chua co.
    bao_dam_user(db, "u1")
    credit.nap(db, "u1", 10_000, note="test")
    ids = []
    import platform_core.workflow.tao_run as tr
    monkeypatch.setattr(tr, "MAX_RUN_DONG_THOI", 1000)
    for i in range(so_run):
        r, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                               trigger_kind="manual", idempotency_key=f"k{i}")
        ids.append(r.id)
    db.commit()
    db.close()
    return ids


def _hoan_tat_job(dbmod):
    from platform_core import jobs
    from platform_core.job_scheduler import ORIGIN_WORKFLOW
    from platform_core.models import JOB_QUEUED, Job
    from platform_core.workflow import tao_run
    db = _mo(dbmod)()
    for j in db.query(Job).filter(Job.origin == ORIGIN_WORKFLOW,
                                  Job.job_type != tao_run.DONG_CO_JOB,
                                  Job.status == JOB_QUEUED).all():
        jobs.complete(db, j, {"text": "x"})
    db.commit()
    db.close()


def test_hai_vong_song_song_khong_nop_doi(pg, monkeypatch):
    """Hai luồng gọi `dong_co.mot_vong` THẬT SỰ cùng chạm vào cùng một hàng
    run tại cùng một thời điểm (review round 1, Important #2): riêng lệch
    khởi động luồng của hệ điều hành đủ để hai luồng không bao giờ thực sự
    tranh chấp — phép kiểm khi đó xanh dù khoá đúng hay sai, vì mỗi luồng chỉ
    thấy hàng đã bị dọn dẹp bởi luồng kia TỪ TRƯỚC (khoá không được thử thật).
    `threading.Barrier(2)` ép cả hai gọi `mot_vong` cùng một nhịp; sleep bên
    trong đoạn ĐÃ KHOÁ (`xu_ly_run`, chạy sau `FOR UPDATE SKIP LOCKED`, trước
    `commit`) cho vài lần gọi đầu kéo dài cửa sổ tranh chấp đủ để luồng thua
    thật sự chạm đúng hàng đang bị khoá — buộc `SKIP LOCKED` phải bỏ qua
    (không chờ), đúng cơ chế đang được kiểm.

    Also review round 1, Important #1: `threading.Thread` + `join()` nuốt mọi
    exception ném trong luồng (in traceback ra stderr rồi im lặng chết) — một
    lỗi thật trong `mot_vong` sẽ không làm phép kiểm này đỏ. Dùng
    `ThreadPoolExecutor` + `future.result()` để lỗi của luồng được ném lại ở
    luồng chính (sibling: `tests/test_214_multi_process_runtime.py:335` kiểm
    exit code của worker process vì cùng lý do)."""
    from platform_core.models import Job, WorkflowRun
    from platform_core.workflow import dong_co

    ids = _chuan_bi(pg, monkeypatch)

    goc_xu_ly = dong_co.xu_ly_run
    dem = {"n": 0}
    khoa_dem = threading.Lock()

    def _xu_ly_cham(db, rid, **kw):
        with khoa_dem:
            can_cham = dem["n"] < 6
            dem["n"] += 1
        if can_cham:
            time.sleep(0.08)   # keo dai cua so da khoa de ep tranh chap that
        return goc_xu_ly(db, rid, **kw)

    monkeypatch.setattr(dong_co, "xu_ly_run", _xu_ly_cham)

    for vong in range(3):
        rao = threading.Barrier(2)

        def _chay(rao=rao, vong=vong):
            # `wait()` khong timeout se treo VINH VIEN ca luong nay lan luong
            # kia (roi ca `future.result()` o luong chinh) neu mot worker
            # khong bao gio toi duoc rao (kiet thread/tai nguyen, scheduler
            # doi khi chay duoi quyen nang - review round 2, Important). Gioi
            # han 30s + bao loi ro rang, thay vi treo im lang.
            try:
                rao.wait(timeout=30)
            except threading.BrokenBarrierError:
                raise AssertionError(
                    f"vong {vong}: luong thu hai khong toi rao trong 30s - "
                    "khong ep duoc tranh chap that") from None
            dong_co.mot_vong(_mo(pg))

        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = [pool.submit(_chay) for _ in range(2)]
            for f in futs:
                f.result()   # nem lai loi that cua luong - khong nuot
        _hoan_tat_job(pg)
    dong_co.mot_vong(_mo(pg))

    db = _mo(pg)()
    for rid in ids:
        viec = db.query(Job).filter_by(plan_id=rid).all()
        assert len(viec) == 2, (
            f"run {rid}: {len(viec)} job, ky vong dung 2 (a va b, khong doi)")
        khoa_ids = [j.dedupe_key for j in viec]
        assert len(khoa_ids) == len(set(khoa_ids)), (
            f"dedupe_key trung cho run {rid}: {khoa_ids} - da nop doi")
    assert {r.status for r in db.query(WorkflowRun).all()} == {"SUCCEEDED"}
    db.close()


def test_ttl_hai_luong_song_song_khong_sap_ca_luot(pg, monkeypatch):
    """F3 (final-review.md): hai luồng gọi `dong_co.ttl` THẬT SỰ cùng chạm
    một run quá hạn tại cùng thời điểm. Trước fix, `ttl()` chạy cả vòng trong
    MỘT transaction không khoá hàng nào — hai luồng cùng đọc run RUNNING quá
    hạn, cùng ghi sự kiện `WorkflowFailed`, `UNIQUE(run_id, seq)` làm luồng
    thua `IntegrityError` sập NGUYÊN vòng TTL của luồng đó (không chỉ run va
    chạm). Sau fix, mỗi run một transaction + khoá `SKIP LOCKED`: luồng thua
    bỏ qua êm, không ném, và run chỉ chuyển TIMED_OUT đúng MỘT lần."""
    from datetime import timedelta

    from platform_core.models import Job, JOB_CANCELLED, WorkflowRun
    from platform_core.workflow import dong_co

    ids = _chuan_bi(pg, monkeypatch, so_run=1)
    rid = ids[0]
    db = _mo(pg)()
    dong_co.mot_vong(_mo(pg))              # QUEUED -> RUNNING, started_at set
    run = db.get(WorkflowRun, rid)
    run.started_at = dong_co._bay_gio() - timedelta(hours=7)   # > mac dinh 6h
    db.commit()
    db.close()

    goc_ghi = dong_co.su_kien.ghi
    rao = threading.Barrier(2)

    def _ghi_cham(db_, run_id, *a, **k):
        if run_id == rid:
            try:
                rao.wait(timeout=30)
            except threading.BrokenBarrierError:
                pass
            time.sleep(0.05)   # keo dai cua so tranh chap that su
        return goc_ghi(db_, run_id, *a, **k)
    monkeypatch.setattr(dong_co.su_kien, "ghi", _ghi_cham)

    ket_qua = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(dong_co.ttl, _mo(pg)) for _ in range(2)]
        for f in futs:
            ket_qua.append(f.result())   # khong duoc nem - nem la F3 con song

    assert sum(ket_qua) == 1, (
        f"dung MOT luong duoc tinh TIMED_OUT cho run nay, duoc {ket_qua}")

    db = _mo(pg)()
    assert db.get(WorkflowRun, rid).status == "TIMED_OUT"
    assert db.query(Job).filter_by(
        plan_id=rid, status=JOB_CANCELLED).count() >= 1
    db.close()


def test_crash_giua_chung_resume_dung(pg, monkeypatch):
    """FLOW H: vòng động cơ chết sau khi nộp job, trước commit ⇒ không job ma."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, dong_co
    ids = _chuan_bi(pg, monkeypatch, so_run=1)
    goc = cau_noi.nop_job

    def chet(*a, **k):
        goc(*a, **k)
        raise SystemExit("worker bi giet")
    monkeypatch.setattr(cau_noi, "nop_job", chet)
    with pytest.raises(SystemExit):
        dong_co.mot_vong(_mo(pg))
    monkeypatch.setattr(cau_noi, "nop_job", goc)
    db = _mo(pg)()
    assert db.query(Job).filter_by(plan_id=ids[0]).count() == 0   # đã rollback
    db.close()
    dong_co.mot_vong(_mo(pg))
    _hoan_tat_job(pg)
    dong_co.mot_vong(_mo(pg))
    _hoan_tat_job(pg)
    dong_co.mot_vong(_mo(pg))
    db = _mo(pg)()
    assert db.query(Job).filter_by(plan_id=ids[0]).count() == 2
    db.close()


# ── "MOT RUN = MOT KHOAN GIU CHO" tren PostgreSQL that ──────────────────────
#
# Bai `test_73::test_agent_approve_dong_thoi_chi_mot_hold` (go 23/09 cung model
# `AgentRun`) la thu DUY NHAT tung chay hai luong that de kiem menh de nay.
# Ba bai duoi day dung lai no cho duong v3, va tach ro HAI cau hoi khac nhau ma
# bai cu gop lam mot:
#
#   1. `tien.giu_cho_run()` co tu giu bat bien khi hai phien cung cam MOT run?
#   2. Duong VAO THAT (`tao_run.tao_run`) co giu bat bien khong, va bang gi?
#
# Tach ra vi cau tra loi KHAC NHAU, va gop lai thi mot bai xanh se che mat mot
# lo hong that (hoac nguoc lai: mot bai do se doi mot khoa khong ai can).


def _nap_run_tran(dbmod, owner: str, tran: int = 20):
    """Mot `WorkflowRun` DA COMMIT, chua giu cho. Tra `run_id`.

    Khong di qua `tao_run.tao_run` — bai duoi day kiem CHINH `giu_cho_run`, va
    `tao_run` se giu cho ngay trong cung transaction (dung thu bai ke tiep do).
    """
    from platform_core import credit
    from platform_core.models import WorkflowRun
    from tests.conftest import bao_dam_user

    db = _mo(dbmod)()
    try:
        bao_dam_user(db, owner)
        credit.nap(db, owner, 1000, note="test")
        run = WorkflowRun(owner_id=owner, workflow_id="w-test",
                          version_id="v-test", trigger_kind="manual",
                          idempotency_key="", estimated_max=tran)
        db.add(run)
        db.commit()
        return run.id
    finally:
        db.close()


@pytest.mark.xfail(strict=True, reason=(
    "LO HONG DA DO, CHUA CO DUONG TOI. `giu_cho_run()` doc `run.hold_id` roi "
    "ghi ma KHONG khoa hang, nen hai phien cam cung mot run DA COMMIT deu tao "
    "hold (do duoc: 40 credit cho mot run tran 20). Hom nay khong chay toi "
    "duoc: cho goi DUY NHAT la `tao_run.tao_run()`, noi hang run vua duoc "
    "INSERT trong cung transaction nen khong phien nao khac thay no; hai "
    "request cung khoa thi ke thua chan o `ux_workflow_run_idem` TRUOC duong "
    "tien (xem bai ke tiep, xanh). `strict=True`: neu ai do khoa hang va bai "
    "nay XPASS, buoc phai quay lai day bo `xfail` — mot lo hong da dong khong "
    "duoc phep nam im duoi mot cai nhan 'du kien do'. Tien de dang giu no an "
    "toan duoc ghim boi tests/test_965_wf_duong_tien.py::"
    "test_giu_cho_run_chi_co_MOT_cho_goi_va_cho_do_tu_tao_run."))
def test_giu_cho_run_dong_thoi_chi_mot_hold(pg):
    """Hai phien CSDL that cung `giu_cho_run` MOT run ⇒ dung MOT but toan hold.

    ⚠️ SQLite khong tai hien duoc cuoc dua nay: `credit._khoa_so_du_user` chi
       phat `pg_advisory_xact_lock` tren PostgreSQL, va hai phien SQLite trong
       mot tien trinh test khong bao gio doc cung mot anh chup.

    Hinh dang cuoc dua: ca hai phien doc `run.hold_id` (rong) TRUOC rao, roi
    cung goi `giu_cho_run`. Khoa advisory trong `credit.giu_cho` tuan tu hoa
    hai luot GHI SO (nen so du khong bao gio am), nhung no KHONG lam phien thua
    doc lai `run.hold_id` — nen neu `giu_cho_run` khong khoa hang run, phien
    thua van di tiep va ghi khoan giu thu hai.
    """
    from platform_core import credit
    from platform_core.models import WorkflowRun
    from platform_core.workflow import tien

    rid = _nap_run_tran(pg, "u-hold-dua", tran=20)
    rao = threading.Barrier(2)

    def _chay():
        ss = _mo(pg)()
        try:
            run = ss.get(WorkflowRun, rid)     # anh chup rieng cua phien nay
            try:
                rao.wait(timeout=30)
            except threading.BrokenBarrierError:
                raise AssertionError(
                    "luong thu hai khong toi rao trong 30s - khong ep duoc "
                    "tranh chap that") from None
            ket_qua = tien.giu_cho_run(ss, run)
            ss.commit()
            return bool(ket_qua)
        finally:
            ss.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(_chay) for _ in range(2)]
        da_giu = [f.result() for f in futs]

    db = _mo(pg)()
    try:
        so = credit.so_da_giu(db, rid)
        assert so == 20, (
            f"MOT run = MOT khoan giu cho, nhung so credit dang bi giu cho "
            f"run nay la {so} (tran cua run chi la 20) - hai phien cung tao "
            f"hold. `giu_cho_run` tra True {da_giu.count(True)} lan.")
        assert credit.so_du(db, "u-hold-dua") == 980
    finally:
        db.close()


def _xuat_ban(dbmod, monkeypatch, owner: str, nap: int = 1000) -> str:
    """Mot workflow DA PUBLISH cua `owner`, vi co san credit. Tra `workflow_id`.

    Khong dung `_draft` cua `test_1716`: no ghim `owner_id="u1"`, va bai doi
    chung duoi day can HAI chu khac nhau (cung mot chu thi khoa advisory cua
    `credit` tuan tu hoa hai luot — do la khoa CO SAN, khong phai thu dang kiem).
    """
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia
    from tests.conftest import bao_dam_user
    from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC

    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": "tool", "position": {"x": 0, "y": 0},
         "data": {"tool": "text.chat", "params": {}}}],
        "edges": []}]}
    db = _mo(dbmod)()
    try:
        bao_dam_user(db, owner)
        credit.nap(db, owner, nap, note="test")
        wf = dinh_nghia.tao_workflow(db, owner_id=owner, name="t")
        dinh_nghia.luu_draft(db, wf.id, document=doc, revision=0)
        v = dinh_nghia.xuat_ban_draft(db, wf.id, created_by=owner, cong_cu=CC)
        wf.published_version_id = v.id
        db.commit()
        return wf.id
    finally:
        db.close()


def test_tao_run_dong_thoi_cung_khoa_chi_mot_hold(pg, monkeypatch):
    """DUONG VAO THAT: hai request song song, CUNG `Idempotency-Key`, mot hold.

    Day la bai tra loi cau hoi ma `giu_cho_run` mot minh KHONG tra loi duoc:
    bat bien "mot run = mot khoan giu cho" co duoc giu tren duong thuc te
    khong, va bang gi. `tao_run.tao_run()` la cua DUY NHAT goi `giu_cho_run`
    (grep 23/09), va o do run duoc INSERT trong CUNG transaction voi khoan giu
    — nen phien kia khong nhin thay hang do de ma dua vao no. Cai chan that su
    la chi muc bo phan `ux_workflow_run_idem`: phien thua CHAN ngay tai INSERT,
    chu chua di toi `giu_cho_run`.
    """
    from platform_core import credit
    from platform_core.models import Workflow, WorkflowRun
    from platform_core.workflow import tao_run

    wid = _xuat_ban(pg, monkeypatch, "u-cua")
    rao = threading.Barrier(2)

    def _chay():
        ss = _mo(pg)()
        try:
            wf = ss.get(Workflow, wid)
            try:
                rao.wait(timeout=30)
            except threading.BrokenBarrierError:
                raise AssertionError("khong ep duoc tranh chap that") from None
            run, moi = tao_run.tao_run(
                ss, workflow=wf, owner_id="u-cua", trigger_kind="manual",
                idempotency_key="mot-y-dinh")
            rid = run.id
            ss.commit()
            return (rid, moi)
        except Exception as exc:              # noqa: BLE001 - giu chan doan
            ss.rollback()
            return ("err", f"{type(exc).__name__}: {exc}")
        finally:
            ss.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ket = [f.result() for f in [pool.submit(_chay) for _ in range(2)]]

    assert not [k for k in ket if k[0] == "err"], ket
    assert len({k[0] for k in ket}) == 1, (
        f"hai request cung khoa phai tra CUNG mot run, duoc {ket}")
    assert [k[1] for k in ket].count(True) == 1, (
        f"dung MOT request duoc tinh la tao moi, duoc {ket}")

    rid = ket[0][0]
    db = _mo(pg)()
    try:
        assert db.query(WorkflowRun).filter_by(owner_id="u-cua").count() == 1
        tran = db.get(WorkflowRun, rid).estimated_max
        assert tran > 0                       # bai nay vo nghia neu tran = 0
        assert credit.so_da_giu(db, rid) == tran, (
            "hai request cung khoa tao hai khoan giu cho cung mot run")
        assert credit.so_du(db, "u-cua") == 1000 - tran
    finally:
        db.close()


def test_tao_run_hai_chu_khac_nhau_khong_chan_nhau(pg, monkeypatch):
    """VE DOI CHUNG: hai run cua HAI chu khac nhau phai chay CHONG len nhau.

    Mot ban va cho bai `giu_cho_run` o tren rat de tro thanh mot khoa QUA RONG
    (vd khoa bang, hay mot advisory lock dung chung) — no se lam bai kia xanh
    va lam moi luot tao run tren toan he tuan tu hoa.

    ⭐ Do bang CHONG LAN, khong bang TONG THOI GIAN. Nguong kieu "tong < 1.6 x
       _NGU" do duoc that nhung no do ca TAI CUA MAY: do lan dau 23/09 tren cay
       nay la 1.11s cho `_NGU = 0.6` va ket luan "dang xep hang" — trong khi
       mot phep do lai bang ba ket noi rieng cho thay 0.77s va `pg_stat_activity`
       KHONG ghi nhan mot lan cho khoa nao. Tuc nguong thoi gian bien tai may
       cua agent khac thanh mot phat hien gia.

    ⇒ Moi luong ghi lai hai moc: VAO (ngay sau khi khoan giu duoc ghi) va RA
      (ngay sau `commit`). Hai luong that su chay chong khi `max(VAO) < min(RA)`
      — ca hai cung giu mot khoan chua commit tai cung mot thoi diem. Bi tuan tu
      hoa thi VAO cua ke thua nam SAU RA cua ke thang, bat ke may nhanh hay cham.
    """
    from platform_core import credit
    from platform_core.models import Workflow, WorkflowRun
    from platform_core.workflow import tao_run

    chu = ("u-doi-1", "u-doi-2")
    wid = {c: _xuat_ban(pg, monkeypatch, c) for c in chu}

    # ⚠️ NOI SAN job dong co TRUOC cuoc dua, va day KHONG phai de bai de xanh:
    #    `tao_run.danh_thuc_dong_co()` hoi "co job dong co nao dang song
    #    khong" bang mot SELECT roi moi INSERT. Hai luot tao run song song cua
    #    HAI chu khac nhau deu thay "khong co" va deu nop ⇒ `ux_jobs_dedupe_active`
    #    nem `UniqueViolation`, va vi `_tim(owner, key)` khong tim thay run nao
    #    mang khoa do, `tao_run` NEM LEN tren — mot trong hai nguoi dung nhan
    #    500 du khong ai lam gi sai. Da do that tren PostgreSQL 23/09.
    #
    # ⇒ Do la mot loi RIENG, tren duong hang doi chu khong phai duong tien
    #   (savepoint cuon lai ca khoan giu, khong mat tien), va sua no o day se
    #   tron hai cau hoi vao mot ban va. Ghi ra day + bao cao rieng; bai NAY do
    #   thu khac (co khoa nao tuan tu hoa hai run khong), nen no loai bien do ra
    #   bang cach cho job dong co ton tai san — trang thai THUONG GAP tren
    #   production, noi dong co gan nhu luon dang song.
    from platform_core.workflow import tao_run as _tr
    _db = _mo(pg)()
    _tr.danh_thuc_dong_co(_db)
    _db.commit()
    _db.close()

    rao = threading.Barrier(2)

    def _chay(c):
        ss = _mo(pg)()
        try:
            wf = ss.get(Workflow, wid[c])
            rao.wait(timeout=30)
            run, _ = tao_run.tao_run(ss, workflow=wf, owner_id=c,
                                     trigger_kind="manual",
                                     idempotency_key=f"k-{c}")
            rid = run.id
            vao = time.monotonic()   # khoan giu DA ghi, transaction con MO
            time.sleep(_NGU)         # giu no mo - o day mot khoa moi lo ra
            ss.commit()
            return rid, vao, time.monotonic()
        finally:
            ss.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ket = [f.result() for f in [pool.submit(_chay, c) for c in chu]]

    ids = [k[0] for k in ket]
    assert len(set(ids)) == 2
    db = _mo(pg)()
    try:
        for rid in ids:
            tran = db.get(WorkflowRun, rid).estimated_max
            assert credit.so_da_giu(db, rid) == tran
    finally:
        db.close()

    vao_muon = max(k[1] for k in ket)
    ra_som = min(k[2] for k in ket)
    assert vao_muon < ra_som, (
        f"hai run cua HAI chu khac nhau KHONG chong lan nhau: luong vao muon "
        f"nhat bat dau {vao_muon - ra_som:.2f}s SAU khi luong ra som nhat da "
        f"commit. Tuc mot khoa dang tuan tu hoa ca duong tao run, chu khong "
        f"chi mot run.")


def test_hai_chu_dua_danh_thuc_dong_co_khong_ai_bi_500(pg, monkeypatch):
    """HAI chu khac nhau tao run cung luc: KHONG ai duoc nhan 500.

    Day la cuoc dua ma `test_tao_run_hai_chu_khac_nhau_khong_chan_nhau` co y
    LOAI RA (no noi san job dong co truoc khi dua). O day ta do CHINH no.

    `tao_run.danh_thuc_dong_co()` hoi "co job dong co nao dang song khong"
    bang mot SELECT roi moi INSERT. Hai phien CSDL khac nhau deu thay "khong
    co" (phien kia chua commit ⇒ READ COMMITTED khong nhin thay) va deu INSERT
    ⇒ chi muc bo phan `ux_jobs_dedupe_active` nem `UniqueViolation`. Truoc ban
    sua, `tao_run` de no bay len tan route ⇒ MOT NGUOI DUNG NHAN 500 du khong
    lam gi sai.

    ⭐ EP TRANH CHAP THAT, khong dua vao lech thoi gian: chi mot `Barrier`
       truoc khi goi `tao_run` la KHONG du — luong nhanh hon co the commit xong
       truoc khi luong kia kip SELECT, va bai kiem se xanh du loi con nguyen.
       `tao_run.chu_dong_co()` duoc goi DUNG MOT LAN, ngay SAU cai SELECT do va
       NGAY TRUOC `jobs.submit` (doc `danh_thuc_dong_co`), nen boc no bang mot
       `Barrier` ghim ca hai luong vao dung khe cua so dua nhau.

    Ba ve phai dung CUNG LUC sau ban sua:
      1. ke thua VAN tao duoc run cua minh (khong 500),
      2. khoan giu cho credit cua ke thua VAN CON (savepoint chi cuon lai
         INSERT job, khong cuon ca chuoi tao run),
      3. van chi con DUNG MOT job dong co dang song (bat bien plan 01a).
    """
    from platform_core import credit
    from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job, Workflow
    from platform_core.models import WorkflowRun
    from platform_core.workflow import tao_run

    chu = ("u-dua-1", "u-dua-2")
    wid = {c: _xuat_ban(pg, monkeypatch, c) for c in chu}

    # ⛔ CO Y khong noi san job dong co: cuoc dua CHINH LA thu dang do.
    khe = threading.Barrier(2)
    that = tao_run.chu_dong_co

    def _cho_ca_hai_cung_khe():
        slug = that()
        # SELECT "co job dong co dang song?" cua CA HAI phien da chay xong va
        # ca hai deu thay "khong co"; INSERT cua ca hai con o phia truoc.
        khe.wait(timeout=30)
        return slug

    monkeypatch.setattr(tao_run, "chu_dong_co", _cho_ca_hai_cung_khe)

    def _chay(c):
        ss = _mo(pg)()
        try:
            wf = ss.get(Workflow, wid[c])
            run, _ = tao_run.tao_run(ss, workflow=wf, owner_id=c,
                                     trigger_kind="manual",
                                     idempotency_key=f"k-{c}")
            rid = run.id
            ss.commit()
            return ("ok", rid)
        except Exception as exc:            # noqa: BLE001 - giu chan doan
            ss.rollback()
            return ("err", f"{type(exc).__name__}: {exc}")
        finally:
            ss.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ket = [f.result() for f in [pool.submit(_chay, c) for c in chu]]

    loi = [k[1] for k in ket if k[0] == "err"]
    assert not loi, (
        "mot nguoi dung bi tu choi mot hanh dong HOP LE bang loi may chu chi "
        f"vi nguoi kia bam truoc vai mili giay: {loi}")

    ids = [k[1] for k in ket]
    assert len(set(ids)) == 2, f"hai chu khac nhau phai co hai run: {ket}"

    db = _mo(pg)()
    try:
        # (1) ca hai run ton tai that
        for rid in ids:
            assert db.get(WorkflowRun, rid) is not None, f"run {rid} bien mat"
        # (2) khoan giu cho cua CA HAI van con dung tran — savepoint cuon lai
        #     INSERT job chu KHONG duoc cuon mat khoan giu cua ke thua
        for rid in ids:
            tran = db.get(WorkflowRun, rid).estimated_max
            assert tran > 0, "bai nay vo nghia neu tran = 0"
            assert credit.so_da_giu(db, rid) == tran, (
                f"khoan giu cho cua run {rid} bi cuon mat theo savepoint")
        for c in chu:
            assert credit.so_du(db, c) < 1000, f"{c} chua bi giu cho gi"
        # (3) bat bien plan 01a: DUNG MOT job dong co dang song
        song = db.query(Job).filter(
            Job.job_type == tao_run.DONG_CO_JOB,
            Job.status.in_((JOB_QUEUED, JOB_RUNNING))).all()
        assert len(song) == 1, (
            f"phai co DUNG MOT job dong co dang song, dem duoc {len(song)}: "
            f"{[(j.id, j.dedupe_key, j.status) for j in song]}")
    finally:
        db.close()
