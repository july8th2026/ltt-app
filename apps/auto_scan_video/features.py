"""Quy tac nghiep vu cua Auto Scan Video: vong doi run, tien, quyen so huu.

`routes.py` chi lo HTTP. Moi bat bien ve tien va quyen nam o day, vi mot bat
bien nam trong handler HTTP la mot bat bien khong ap dung cho worker.

## Ba dieu de sai nhat, ghi ngay dau tep

1. **Job giai doan KHONG BAO GIO giu credit.** Chung nop bang `jobs.submit`,
   khong bao gio `job_submit.submit_with_credit`. Chi `tao_run()` giu tien, va
   giu tren `run.id`. Neu mot giai doan tu giu, khach bi tinh tien **muoi lan**
   cho mot lan chay — mot lan cho run, chin lan cho stage — va **so credit van
   can**, nen khong co gi trong nhu bi hong.
   Chot boi `tests/test_401...::test_job_giai_doan_KHONG_duoc_tu_giu_credit`.

2. **`credit_actual` la so DO DUOC, khong phai gia tinh lai.**
   `platform_core/agent/executor.py:130 actual_cost` tinh lai bang
   `credit_for(job_type, params) x attempts` va **bo qua** `result["credit_cost"]`
   — tuc tinh tien theo thu khach XIN, khong phai thu may GIAO. Loi do da ra
   production hai lan (CLAUDE.md: H38 23/08, H37/D-051 24/08 — xin 4 anh, may
   tra 2, van thu 4). Chi phi cua ta bien thien theo ky tu TTS / token LLM /
   giay GPU, nen dung lai ham do la chep lai mot loi tien da biet.

3. **Quyen so huu giai o may chu, luon luon.** Khong ham nao o day nhan
   `owner_id` tu client.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from platform_core import credit, jobs
from platform_core.i18n import _ as _t

from . import pipeline
from .tables import (RUN_CANCELLED, RUN_DONE, RUN_ERROR, RUN_QUEUED,
                     RUN_RUNNING, RUN_TERMINAL, STAGE_FAILED_TERMINAL,
                     STAGE_PENDING, STAGE_QUEUED, STAGE_SUCCEEDED,
                     AsvRun, AsvStage)

SLUG = "auto_scan_video"
JOB_DIEU_PHOI = "auto_scan_video.advance"

#: Giay cho truoc khi job dieu phoi tu nop lai. Ngan de tien do muot, du dai de
#: khong quay vong dày trên CSDL. Cung bac voi `apps/agent/jobs.py:37`.
NHIP_DIEU_PHOI_S = 2


class AsvError(ValueError):
    """Loi nghiep vu cua Auto Scan. Route doi thanh 4xx."""


class KhongTimThay(AsvError):
    pass


class XungDot(AsvError):
    """Mot ban ghi da bi doi boi tien trinh khac. Doc lai roi thu lai."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ══════════════════════════════════════════════════════════════════════════════
#  Doc co pham vi chu so huu (I6)
# ══════════════════════════════════════════════════════════════════════════════

def lay_run(db: Session, run_id: str, owner_id: str, *, lock: bool = False) -> AsvRun:
    """Mot run CUA CHINH `owner_id`. Nem `KhongTimThay` neu khong phai cua ho.

    ⭐ Nem "khong tim thay" chu khong phai "khong co quyen": phan biet hai cau
       tra loi do cho phep mot nguoi la do xem run nao ton tai (I6).
    """
    stmt = select(AsvRun).where(AsvRun.id == run_id, AsvRun.owner_id == owner_id)
    if lock:
        stmt = stmt.with_for_update()
    row = db.execute(stmt).scalars().first()
    if row is None:
        raise KhongTimThay(_t('Không tìm thấy phiên chạy.'))
    return row


def cac_giai_doan(db: Session, run: AsvRun) -> list[AsvStage]:
    return list(db.execute(
        select(AsvStage).where(AsvStage.run_id == run.id)
        .order_by(AsvStage.id)).scalars())


def giai_doan_theo_ten(db: Session, run_id: str, ten: str) -> AsvStage | None:
    return db.execute(
        select(AsvStage).where(AsvStage.run_id == run_id,
                               AsvStage.stage == ten)).scalars().first()


# ══════════════════════════════════════════════════════════════════════════════
#  Tao run — CHO DUY NHAT cham vao vi tien
# ══════════════════════════════════════════════════════════════════════════════

def tao_run(db: Session, *, owner_id: str, source_key: str, settings: dict,
            uoc_luong_credit: int) -> AsvRun:
    """Tao run + giu credit + nop job dieu phoi, trong MOT transaction.

    KHONG commit — caller commit. Nho vay hoac ca ba cung thanh, hoac ca ba cung
    khong: khong bao gio co run khong tra tien, hay tien giu ma khong co run
    (I2). Cung khuon voi `platform_core/job_submit.py`.

    `uoc_luong_credit` uoc theo **thoi luong** vi luc nay chua co transcript, nen
    chua biet so ky tu TTS hay token LLM. Uoc thua la binh thuong — quyet toan
    tra lai phan du (chot boi
    `test_400...::test_quyet_toan_it_hon_giu_cho_thi_hoan_phan_du`).
    """
    if not owner_id:
        raise AsvError(_t('Thiếu chủ sở hữu.'))
    if not source_key:
        raise AsvError(_t('Thiếu tệp nguồn.'))
    uoc_luong_credit = max(0, int(uoc_luong_credit))

    run = AsvRun(owner_id=owner_id, source_key=source_key,
                 settings=dict(settings or {}), status=RUN_QUEUED,
                 credit_held=uoc_luong_credit)
    db.add(run)
    db.flush()          # can `run.id` de giu cho va de dat ten dedupe

    # Mot dong `pending` cho MOI giai doan, ngay tu dau. Nho vay tien do doc
    # duoc ngay lap tuc va `resume` khong phai doan xem con thieu gi.
    for g in pipeline.CHUOI:
        db.add(AsvStage(run_id=run.id, owner_id=owner_id, stage=g.ten,
                        status=STAGE_PENDING))

    if uoc_luong_credit > 0:
        # `ThieuCreditError` -> caller rollback -> khong con run lan stage nao.
        credit.giu_cho(db, owner_id, uoc_luong_credit, run.id)

    _nop_dieu_phoi(db, run, ly_do="tao")
    db.flush()
    return run


def _nop_dieu_phoi(db: Session, run: AsvRun, *, ly_do: str) -> None:
    """Nop mot luot `advance`. Dedupe theo `(run, ly_do)` de khong fan-out.

    ⚠️ Job dieu phoi **khong** giu credit — no dung `jobs.submit`. No la mot job
       dieu khien, khong phai mot giai doan tinh tien.
    """
    jobs.submit(db, user_id=run.owner_id, app_slug=SLUG,
                job_type=JOB_DIEU_PHOI,
                params={"run_id": run.id, "owner_id": run.owner_id},
                dedupe_key=f"asv:advance:{run.id}:{ly_do}",
                max_attempts=3)


# ══════════════════════════════════════════════════════════════════════════════
#  Ghi mot dong giai doan — dong thoi an toan (I18)
# ══════════════════════════════════════════════════════════════════════════════

def cap_nhat_giai_doan(db: Session, stage: AsvStage, **truong) -> AsvStage:
    """`UPDATE ... WHERE revision = :r`. Nem `XungDot` neu ai do da ghi truoc.

    Khuon lay tu `platform_core/app_projects.py:85`. Mot dong cho moi giai doan
    da lam hai giai doan khac nhau khong the dam nhau; cai nay lo not truong hop
    con lai — mot worker mat dap nhip nhung chua chet han, con job mo coi cua no
    da bi worker khac nhat.
    """
    rev = int(stage.revision)
    ket_qua = db.execute(
        update(AsvStage)
        .where(AsvStage.id == stage.id, AsvStage.revision == rev)
        .values(revision=rev + 1, **truong))
    if ket_qua.rowcount != 1:
        raise XungDot(
            _t('Giai đoạn đã được cập nhật ở tiến trình khác.'))
    db.flush()
    db.expire(stage)
    return stage


def danh_dau_dang_chay(db: Session, stage: AsvStage, job_id: str) -> AsvStage:
    return cap_nhat_giai_doan(db, stage, status=STAGE_QUEUED, job_id=job_id,
                              attempt=int(stage.attempt) + 1,
                              started_at=_now())


def danh_dau_xong(db: Session, stage: AsvStage, *, outputs: dict,
                  fingerprint: str, credit_actual: int = 0) -> AsvStage:
    """Giai doan xong. CHI goi sau khi output da ben va da hop le.

    ⛔ `Job.status == done` **khong** phai dieu kien du. ADR-001 D7 doi du nam
       buoc: engine tra ve -> output hop le -> `storage.promote` xong -> ghi
       tham chieu + van tay -> commit. Goi ham nay sau buoc mot la vi pham I8, va
       trieu chung se la khach nhan mot tep rong kem chu "thanh cong".
    """
    return cap_nhat_giai_doan(
        db, stage, status=STAGE_SUCCEEDED, outputs=dict(outputs or {}),
        fingerprint=str(fingerprint or ""), credit_actual=max(0, int(credit_actual)),
        finished_at=_now(), error="")


def danh_dau_hong(db: Session, stage: AsvStage, loi: str, *,
                  cuoi_cung: bool = True) -> AsvStage:
    from .tables import STAGE_FAILED_RETRYABLE
    return cap_nhat_giai_doan(
        db, stage,
        status=STAGE_FAILED_TERMINAL if cuoi_cung else STAGE_FAILED_RETRYABLE,
        error=str(loi or "")[:2000], finished_at=_now() if cuoi_cung else None)


# ══════════════════════════════════════════════════════════════════════════════
#  Vo hieu ha nguon + thu lai (Prompt 16 muc 4 va 7)
# ══════════════════════════════════════════════════════════════════════════════

def _dat_lai_giai_doan(db: Session, stage: AsvStage) -> None:
    """Dua mot dong giai doan ve trang thai chua chay.

    ⚠️ Rong la `""` / `{}`, KHONG phai `None`: bon cot nay deu NOT NULL, va
       `outputs=None` bien thanh chuoi JSON `'null'` chu khong thanh SQL NULL —
       tuc "chua co ket qua" va "ket qua la null" se khong phan biet duoc.

    ⛔ KHONG dat lai `attempt`. So lan thu la mot su that ve lich su cua lan
       chay, khong phai mot bo dem tien do; xoa no la xoa dung thu can de tra
       loi "vi sao lan chay nay ton nhieu tien the".
    """
    cap_nhat_giai_doan(db, stage, status=STAGE_PENDING, fingerprint="",
                       outputs={}, job_id="", error="",
                       started_at=None, finished_at=None)


def vo_hieu_ha_nguon(db: Session, run: AsvRun, ten: str) -> list[str]:
    """Dat lai moi giai doan an theo `ten`. Tra ve danh sach da dat lai.

    🔑 Vi sao phai lam TAY, du van tay da tu lam moi cache: van tay cua mot giai
       doan gom van tay cua cac giai doan truoc (`thi_hanh._gom_dau_vao`), nen
       khi thuong nguon doi thi van tay ha nguon **cung doi** va cache truot.
       Nhung dong `asv_stage` cua no van ghi `succeeded` — va dieu phoi vien chi
       nop nhung giai doan **chua** succeeded. Ket qua: no khong bao gio chay
       lai, va lan chay ket thuc voi mot ban long tieng dung tep cu.

    ⇒ Van tay lo phan "khong dung lai ket qua sai"; ham nay lo phan "chay lai
      that". Thieu mot trong hai la du de hong.
    """
    ra: list[str] = []
    theo_ten = {s.stage: s for s in cac_giai_doan(db, run)}
    for sau in pipeline.ha_nguon_cua(ten):
        s = theo_ten.get(sau)
        if s is None or s.status == STAGE_PENDING:
            continue
        try:
            _dat_lai_giai_doan(db, s)
        except XungDot:
            # Mot worker dang ghi dong nay. Luot advance ke tiep doc lai va thay
            # van tay da lech, nen no se duoc dat lai o luot do.
            continue
        ra.append(sau)
    return ra


def thu_lai_giai_doan(db: Session, run_id: str, owner_id: str,
                      ten: str) -> dict:
    """Chay lai MOT giai doan va chi nhung giai doan an theo no (muc 7).

    ⛔ Khong chay lai ca lan chay. Chay lai `media_prepare` khi chi `render`
       hong la bat khach tra tien lai cho mot lan chep loi, mot lan dich va mot
       lan sinh tieng — ba thu dat nhat trong chuoi, va khong thu nao lien quan.

    ⛔ Va khong cho thu lai mot lan chay **da ket thuc**: `quyet_toan` da hoan
       phan credit chua dung, nen mot lan chay tiep sau do se tieu tien ma
       khong con cho giu. Muon lam lai thi nop mot run moi.
    """
    if ten not in pipeline.THEO_TEN:
        raise AsvError(_t('Không có giai đoạn tên này.'))

    run = lay_run(db, run_id, owner_id, lock=True)
    if run.status in RUN_TERMINAL:
        raise AsvError(
            _t('Lần chạy đã kết thúc — hãy tạo một lần chạy mới.'))

    stage = giai_doan_theo_ten(db, run.id, ten)
    if stage is None:
        raise KhongTimThay(_t('Không có giai đoạn tên này.'))

    _dat_lai_giai_doan(db, stage)
    da_vo_hieu = vo_hieu_ha_nguon(db, run, ten)

    run.error = ""
    if run.status not in (RUN_QUEUED, RUN_RUNNING):
        run.status = RUN_RUNNING
    # `ly_do` mang ten giai doan nen hai lan thu lai hai giai doan khac nhau
    # khong bi dedupe vao lam mot.
    _nop_dieu_phoi(db, run, ly_do=f"thu-lai:{ten}")
    db.flush()
    return {"run_id": run.id, "da_dat_lai": [ten] + da_vo_hieu}


# ══════════════════════════════════════════════════════════════════════════════
#  Tien: tran chi va quyet toan (I2, I3, ADR-001 D4)
# ══════════════════════════════════════════════════════════════════════════════

def tong_da_dung(db: Session, run: AsvRun) -> int:
    """Tong chi phi **DO DUOC** cua cac giai doan. Khong tinh lai tu bang gia."""
    return sum(int(s.credit_actual or 0) for s in cac_giai_doan(db, run))


def kiem_tran_chi(db: Session, run: AsvRun, them: int) -> None:
    """Chot BAT BUOC truoc moi lan goi ton tien. Nem `AsvError` neu vuot hold.

    Vi sao can: `credit_held` uoc theo thoi luong truoc khi biet transcript
    (RISK-03-02). Mot uoc luong te phai thanh mot **that bai chinh sach sach se**
    chu khong phai mot lan tieu vuot ngoai phan da giu.
    """
    du_kien = tong_da_dung(db, run) + max(0, int(them))
    if du_kien > int(run.credit_held):
        raise AsvError(
            _t('Chi phí thực tế sẽ vượt mức đã giữ cho phiên chạy này.'))


def quyet_toan(db: Session, run: AsvRun, *, trang_thai_cuoi: str) -> AsvRun:
    """Quyet toan MOT LAN cho ca run. Phan khong dung duoc hoan.

    Idempotent: run da o trang thai ket thuc thi khong cham so lan nua. Can
    tinh chat do vi `advance` duoc phep chay lai sau khi worker chet
    (chot boi `test_400...::test_quyet_toan_hai_lan_khong_tinh_tien_hai_lan`).
    """
    if trang_thai_cuoi not in RUN_TERMINAL:
        raise AsvError(f"trang thai ket thuc khong hop le: {trang_thai_cuoi}")
    if run.status in RUN_TERMINAL:
        return run

    thuc_te = min(tong_da_dung(db, run), int(run.credit_held))
    if int(run.credit_held) > 0:
        credit.quyet_toan(db, run.owner_id, run.id, thuc_te)
    run.credit_actual = thuc_te
    run.status = trang_thai_cuoi
    run.finished_at = _now()
    run.revision = int(run.revision) + 1
    db.flush()
    return run


# ══════════════════════════════════════════════════════════════════════════════
#  Huy (I13)
# ══════════════════════════════════════════════════════════════════════════════

def huy_run(db: Session, run_id: str, owner_id: str) -> AsvRun:
    """Huy mot run cua chinh minh. Job con chua ket thuc bi huy theo.

    Nua con lai cua I13 — "da huy thi khong bao gio thanh cong" — nam o
    `_advance`: no doc lai `run.status` **duoi khoa** o dau moi luot va dung
    ngay neu da ket thuc. Nen mot job con ve dich muon van khong the lam song
    lai mot run da huy.
    """
    run = lay_run(db, run_id, owner_id, lock=True)
    if run.status in RUN_TERMINAL:
        return run

    from platform_core.models import Job
    con = db.execute(select(Job).where(Job.plan_id == run.id)).scalars().all()
    for job in con:
        jobs.cancel(db, job)

    for stage in cac_giai_doan(db, run):
        if stage.status not in (STAGE_SUCCEEDED, STAGE_FAILED_TERMINAL):
            from .tables import STAGE_CANCELLED
            try:
                cap_nhat_giai_doan(db, stage, status=STAGE_CANCELLED)
            except XungDot:
                pass    # mot worker vua ghi xong dong nay; khong sao
    return quyet_toan(db, run, trang_thai_cuoi=RUN_CANCELLED)


# ══════════════════════════════════════════════════════════════════════════════
#  Tien do
# ══════════════════════════════════════════════════════════════════════════════

def tien_do(db: Session, run: AsvRun) -> dict:
    """Tom tat cho giao dien va cho test. Khong co bi mat, khong co duong dan noi bo."""
    ds = cac_giai_doan(db, run)
    xong = sum(1 for s in ds if s.status == STAGE_SUCCEEDED)
    return {
        "run_id": run.id,
        "status": run.status,
        "phan_tram": int(xong * 100 / max(1, len(pipeline.CHUOI))),
        "da_xong": xong,
        "tong": len(pipeline.CHUOI),
        "credit_held": int(run.credit_held),
        "credit_actual": int(run.credit_actual),
        "giai_doan": [
            {"ten": s.stage, "trang_thai": s.status, "lan_thu": int(s.attempt),
             "loi": s.error or ""}
            for s in sorted(ds, key=lambda x: pipeline.TEN_GIAI_DOAN.index(x.stage))
        ],
    }
