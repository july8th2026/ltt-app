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

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from platform_core import credit, jobs
from platform_core.i18n import _ as _t

from . import pipeline
from . import su_dung
from .tables import (RUN_CANCELLED, RUN_DONE, RUN_ERROR, RUN_QUEUED,
                     RUN_RUNNING, RUN_TERMINAL, STAGE_FAILED_TERMINAL,
                     STAGE_PENDING, STAGE_QUEUED, STAGE_SUCCEEDED,
                     AsvRun, AsvStage, AsvWorkItem)

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


#: Tran so lan mot GIAI DOAN duoc chay lai sau mot truot thoang qua.
#:
#: 🔴 **Truoc pha 23 con so nay khong ton tai, va khong co lan chay lai nao.**
#:    `loi.phan_loai` van phan biet `TAM_THOI` voi loi cuoi cung, va
#:    `STAGE_FAILED_RETRYABLE` van nam trong bang trang thai — nhung
#:    `_thu_ket_qua_job_con` goi `danh_dau_hong` voi mac dinh `cuoi_cung=True`
#:    cho MOI job con hong, nen phan loai do khong bao gio toi duoc trang thai
#:    giai doan. Mot lan het cho dia trong nua giay lam hong ca lan chay.
#:
#: ⚠️ Va hau qua khong dung o do: mot run da ket thuc thi `thu_lai_giai_doan`
#:    tu choi (no da quyet toan, khong con cho giu), nen khach chi con duong nop
#:    mot lan chay MOI — tinh lai tu dau ca demucs lan ASR, vi cache artifact
#:    khoa theo `run_id`.
#:
#: ⛔ Ba, khong phai vo han: mot truot "thoang qua" ma lap lai ba lan thi no
#:    khong thoang qua, va thu tiep la dot cho.
LAN_THU_GIAI_DOAN_TOI_DA = 3


def con_luot_thu(stage: AsvStage) -> bool:
    """Giai doan nay con duoc chay lai sau mot truot thoang qua khong."""
    return int(stage.attempt or 0) < LAN_THU_GIAI_DOAN_TOI_DA


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

    🔴 **PHAI HUY JOB CON TRUOC KHI XOA `job_id`.** Ban dau ham nay chi dat
       `job_id=""`, va do la mot JOB MO COI: dong giai doan quen no, nhung no
       van nam trong hang doi va van duoc mot worker nhat len sau do.

       Trieu chung do duoc (02/09, `test_417::test_sau_khi_thu_lai_thi_chuoi_
       CHAY_TIEP_toi_done`): thu lai `media_prepare` -> job `audio_prepare` cu
       tu lan truoc van chay -> `transcribe` chay tren mot ban tieng thuoc lan
       chay TRUOC do -> `Chua co ban tieng de chep loi`.

    ⚠️ Va no la mot loi CO DIEU KIEN: no chi lo ra khi thu tu nhat job doi. Loi
       nam san tu pha 16; chinh viec khai `tai_nguyen` cho lan GPU o pha 21 lam
       doi thu tu va lam no hien hinh. Mot loi chi hong "doi khi" thi truoc do
       no van hong, chi la chua ai thay.
    """
    if stage.job_id:
        from platform_core.models import Job
        job = db.get(Job, stage.job_id)
        if job is not None and job.status in ("queued", "running"):
            jobs.cancel(db, job)

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

    # ⛔ ADR-001 D9. Mot lan gui MO HO la mot lan **khong biet** provider da chay
    #    chua. Thu lai giai doan do la co the tra tien lan thu hai cho dung mot
    #    viec — va khong cach nao phat hien sau, vi ca hai lan deu trong nhu that.
    #
    # 🔑 Chan o day chu khong o `su_dung`: `su_dung.ghi` chi biet mot luot goi,
    #    con cau hoi "co duoc chay lai ca giai doan nay khong" chi tra loi duoc
    #    o cho nhin thay ca giai doan.
    #
    # ⇒ Cach mo khoa la mot NGUOI ket luan (`su_dung.giai_quyet_mo_ho`), khong
    #   phai mot lan bam lai.
    mo_ho = su_dung.cac_mo_ho(db, run, stage=ten)
    if mo_ho:
        raise AsvError(su_dung.loi_dispatch_mo_ho(len(mo_ho)))

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

# ══════════════════════════════════════════════════════════════════════════════
#  Don vi viec (ADR-V4-002 D-V4-10/12)
# ══════════════════════════════════════════════════════════════════════════════

def cac_don_vi(db: Session, run_id: str, stage: str = "") -> list[AsvWorkItem]:
    """Don vi viec cua mot lan chay, loc theo giai doan neu co."""
    dk = [AsvWorkItem.run_id == run_id]
    if stage:
        dk.append(AsvWorkItem.stage == stage)
    return list(db.execute(
        select(AsvWorkItem).where(*dk)
        .order_by(AsvWorkItem.stage, AsvWorkItem.item_key)).scalars())


def don_vi_theo_khoa(db: Session, run_id: str, stage: str,
                     item_key: str) -> AsvWorkItem | None:
    return db.execute(select(AsvWorkItem).where(
        AsvWorkItem.run_id == run_id, AsvWorkItem.stage == stage,
        AsvWorkItem.item_key == item_key)).scalar_one_or_none()


def giai_doan_co_don_vi(db: Session, run_id: str) -> set[str]:
    """Ten cac giai doan da chia don vi viec. Rong = chua giai doan nao chia.

    ⭐ Tra ve TAP HOP thay vi mot co boolean tren tung giai doan: quy tac cong
       tien o duoi can biet "giai doan nay co item khong", va suy dieu do tu du
       lieu that thi khong the lech voi du lieu that.
    """
    return {t for (t,) in db.execute(
        select(AsvWorkItem.stage).where(AsvWorkItem.run_id == run_id).distinct())}


def tong_don_vi(db: Session, run_id: str, stage: str) -> int:
    """Tong chi phi DO DUOC cua cac don vi trong mot giai doan."""
    tong = db.execute(select(func.coalesce(func.sum(AsvWorkItem.credit_actual), 0))
                      .where(AsvWorkItem.run_id == run_id,
                             AsvWorkItem.stage == stage)).scalar_one()
    return int(tong or 0)


class TinhHaiLan(AsvError):
    """Mot giai doan vua co don vi viec vua tu ghi chi phi cua chinh no."""


def _kiem_khong_tinh_hai_lan(db: Session, run: AsvRun) -> None:
    """⛔ Be mat duy nhat de tinh tien khach hai lan cho mot viec.

    ADR-V4-002 D-V4-12: mot giai doan CO don vi viec thi `credit_actual` cua no
    la TONG cua cac don vi, va no khong duoc tu ghi them mot so nao nua. Cong ca
    hai la thu tien hai lan.

    🔴 Day la mot dong ma de viet nham va **khong bao gio lo ra qua mot phep
       kiem chuc nang**: lan chay van xong, video van dung, chi la so tien lon
       hon no phai the. Nen cho nay nem, thay vi tin vao ky luat.
    """
    co_don_vi = giai_doan_co_don_vi(db, run.id)
    if not co_don_vi:
        return
    xau = [s.stage for s in cac_giai_doan(db, run)
           if s.stage in co_don_vi and int(s.credit_actual or 0) != 0]
    if xau:
        raise TinhHaiLan(
            f"giai doan {sorted(xau)} vua co don vi viec vua tu ghi credit_actual "
            f"— xem ADR-V4-002 D-V4-12")


def tong_da_dung(db: Session, run: AsvRun) -> int:
    """Tong chi phi **DO DUOC**. Khong tinh lai tu bang gia (ADR-001 D4).

    Hai muc, theo D-V4-12:

        giai doan CO don vi viec  -> tong `credit_actual` cua cac don vi
        giai doan KHONG co        -> `credit_actual` cua chinh no

    ⚠️ Khong phai `stage.credit_actual + tong_don_vi(...)`. Cong ca hai la loi
       tinh tien hai lan ma `_kiem_khong_tinh_hai_lan` sinh ra de chan; o day ta
       CHON mot trong hai, va cho kia nem neu ca hai cung khac 0.
    """
    _kiem_khong_tinh_hai_lan(db, run)
    co_don_vi = giai_doan_co_don_vi(db, run.id)
    tong = 0
    for s in cac_giai_doan(db, run):
        tong += (tong_don_vi(db, run.id, s.stage) if s.stage in co_don_vi
                 else int(s.credit_actual or 0))
    return tong


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

    # ⛔ Bang chung phai giai thich duoc con so TRUOC khi con so duoc thu.
    #
    # 🔑 `su_dung.ghi` la duong duy nhat cong tien vao mot don vi viec, nen no
    #    khong the tu lam lech. Cai phep doi soat nay thuc su bat la mot duong
    #    ghi **khac** — mot lan `item.credit_actual = ...` viet tay o pha sau.
    #    Do la thu chi lo ra khi doi chieu hai nguon, va cho de lo ra la day:
    #    sau khi quyet toan thi tien da thu, va mot phep kiem sau do chi con la
    #    mot bao cao.
    su_dung.doi_soat(db, run)

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


# ══════════════════════════════════════════════════════════════════════════════
#  Phuc vu giao dien (pha 20)
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#  Duong dau vao BEN VUNG (G6)
# ══════════════════════════════════════════════════════════════════════════════

#: MIME duoc nhan. Ke thua `MVP_CONTRACT.md` muc 2; `video/webm` co y vang mat
#: (VP8/VP9 khong copy duoc vao MP4, va preset giu hinh la mot phep copy).
KIEU_VIDEO_HOP_LE = ("video/mp4", "video/quicktime", "video/x-m4v")

#: Tran cua duong ben vung. Bang tran cua `upload_sessions` (2 GiB) chu khong
#: phai tran 90 MB cua Cloudflare — vi tep KHONG di qua Cloudflare nua.
TRAN_BEN_VUNG = 2 * 1024 * 1024 * 1024


def tao_ve_tai_len(db: Session, kho, *, owner_id: str, ten_tep: str,
                   kieu: str, co_du_kien: int) -> dict:
    """Ve tai len TRUC TIEP browser -> kho. Tra ve mo ta de client tu PUT.

    🔑 Toan bo diem cua ham nay: **tep khong bao gio di qua tien trinh app**.
       V2 doc `await video.read()` roi giu bytes do trong khi vua ghi mot ban
       tam vua day len kho — ca video nam trong RAM hai lan, va tran 90 MB ton
       tai chinh vi dieu do.

    ⭐ Khong co gi moi duoc xay o day. `platform_core.upload_sessions` da lam
       viec nay, da co mot nguoi goi that (`apps/autosubvideo/services/
       source_drafts.py:33-49`), va da mang san han muc chong lam dung (20 phien,
       2 GiB dang bay, 12 ve/phut) cung phep kiem chu ky magic byte.

    Tra `{"mode": "direct", ...}` khi kho cap duoc ve, `{"mode": "local"}` khi
    khong — luc do client quay ve duong multipart nho.
    """
    from platform_core import upload_sessions

    phien = upload_sessions.create(
        db, user_id=owner_id, app_slug=SLUG, filename=ten_tep,
        content_type=kieu, expected_size=int(co_du_kien),
        max_size=TRAN_BEN_VUNG, allowed_types=KIEU_VIDEO_HOP_LE)
    dich = upload_sessions.upload_target(kho, phien)
    if dich is None:
        # Kho khong cap duoc presigned PUT (LocalStorage). Bo ve di thay vi de
        # lai mot dong `pending` khong bao gio duoc dung.
        db.delete(phien)
        db.flush()
        return {"mode": "local"}
    return {"mode": "direct", "upload_id": phien.id, "url": dich.url,
            "method": dich.method, "headers": dich.headers or {}}


def tao_run_tu_ve(db: Session, kho, *, owner_id: str, upload_id: str,
                  settings: dict) -> AsvRun:
    """Ve da tai xong -> soi -> chuyen sang khoa ben -> tao run.

    ## Chu so huu duoc giai o PHIA MAY CHU

    `upload_sessions.owned(...)` loc theo `user_id` VA `app_slug` ngay trong cau
    truy van, nen mot `upload_id` cua nguoi khac khong tra ve dong nao — no
    khong the tro thanh mot loi "khong co quyen" ma ke goi doan duoc tu.

    ## Soi TRUOC khi chuyen, va soi ma KHONG tai ve

    `assets.nguon_soi_duoc` cho ra mot presigned URL (R2) hoac mot duong dan
    (local). ffprobe doc vai khoi dau bang range request. Mot tep khong dat
    chinh sach thi bi tu choi truoc khi chiem mot khoa ben trong kho.

    ## ⚠️ Vi sao KHONG dung `upload_sessions.promote`

    Ham do doi `credit.so_da_giu(db, job.id) > 0` — no gia dinh tien duoc giu
    tren MOT JOB. Auto Scan giu **mot lan tren `run.id`** va moi job con cua no
    co gia 0 (ADR-001 D4), nen dieu kien do khong bao gio dung o day.

    ⇒ Ta dung `kho.promote()` — chinh API `platform_core` ma `assets.py` da dung
      cho artifact. Khong nhan ban gi: phan `upload_sessions` lam tot (ve, han
      muc, chu ky magic byte, quyen so huu) van duoc dung nguyen.

    ⛔ Ghi lai o day vi day la mot **lech ngu nghia that** giua hai mo hinh tinh
       tien, khong phai mot cho di tat. Neu sau nay platform_core mo mot duong
       promote cho "chu giu tien khong phai job", ta nen chuyen sang no.
    """
    import uuid
    from pathlib import Path

    from platform_core import upload_sessions

    from . import assets, gia, nhap_media

    phien = upload_sessions.owned(db, session_id=str(upload_id or ""),
                                  user_id=owner_id, app_slug=SLUG)
    if phien is None:
        raise KhongTimThay(_t('Không tìm thấy lượt tải lên.'))

    try:
        phien = upload_sessions.confirm(db, kho, phien)
    except upload_sessions.UploadSessionError as exc:
        raise AsvError(str(exc)) from exc

    # Soi TAI CHO. Khong tai ve.
    try:
        tt = nhap_media.soi(assets.nguon_soi_duoc(kho, phien.staging_key))
        nhap_media.kiem_chinh_sach(tt)
    except nhap_media.MediaError as exc:
        raise AsvError(str(exc)) from exc
    uoc = gia.uoc_credit(float(tt.get("thoi_luong") or 0))

    duoi = (Path(phien.filename or "").suffix or ".mp4").lstrip(".").lower()
    if not duoi.isalnum() or len(duoi) > 5:
        duoi = "mp4"
    khoa = f"asv/{owner_id[:16]}/nguon/{uuid.uuid4().hex}.{duoi}"
    kho.promote(phien.staging_key, khoa, content_type=phien.content_type)

    return tao_run(db, owner_id=owner_id, source_key=khoa,
                   settings=settings, uoc_luong_credit=uoc)


def tao_run_tu_tai_len(db: Session, *, owner_id: str, du_lieu: bytes,
                       ten_tep: str, settings: dict) -> AsvRun:
    """Nhan bytes tu mot lan tai len -> luu vao kho -> tao run.

    🔑 **Uoc gia phai duoc tinh o day, khong o route.** No can biet thoi luong
       video, tuc can soi tep — va soi tep cung la cho `MVP_CONTRACT` §2 tu choi
       mot tep khong co luong tieng. Ca hai deu la quyet dinh nghiep vu.

    ⛔ Khoa luu tru KHONG mang ten tep cua khach. Ten do do khach dat, va mot ten
       tep di vao khoa la mot chuoi cua client di vao duong dan — dung thu ma
       `assets.dat_khoa` sinh ra de chan.
    """
    import io
    import tempfile
    import uuid
    from pathlib import Path

    from platform_core.storage import get_storage

    from . import gia, nhap_media

    duoi = (Path(ten_tep or "").suffix or ".mp4").lstrip(".").lower()
    if not duoi.isalnum() or len(duoi) > 5:
        duoi = "mp4"

    # Soi TRUOC khi luu: mot tep khong dung chinh sach thi khong nen chiem cho
    # trong kho, va khach nen biet ngay thay vi sau mot vong hang doi.
    with tempfile.TemporaryDirectory(prefix="asv-nhan-") as tam:
        tep = Path(tam) / f"nguon.{duoi}"
        tep.write_bytes(du_lieu)
        try:
            tt = nhap_media.soi(str(tep))
        except nhap_media.MediaError as exc:
            raise AsvError(str(exc)) from exc
        try:
            nhap_media.kiem_chinh_sach(tt)
        except nhap_media.MediaError as exc:
            raise AsvError(str(exc)) from exc
        uoc = gia.uoc_credit(float(tt.get("thoi_luong") or 0))

    khoa = f"asv/{owner_id[:16]}/nguon/{uuid.uuid4().hex}.{duoi}"
    get_storage().put(khoa, io.BytesIO(du_lieu), content_type="video/mp4")

    return tao_run(db, owner_id=owner_id, source_key=khoa,
                   settings=settings, uoc_luong_credit=uoc)


def lich_su(db: Session, owner_id: str, *, toi_da: int = 20) -> list:
    """Lan chay CUA CHINH nguoi nay, moi nhat truoc."""
    return list(db.execute(
        select(AsvRun).where(AsvRun.owner_id == owner_id)
        .order_by(AsvRun.created_at.desc()).limit(max(1, int(toi_da)))
    ).scalars().all())


def khoa_ket_qua(db: Session, run: AsvRun) -> str:
    """Khoa luu tru cua ban long tieng, hoac chuoi rong.

    ⚠️ Doc tu `outputs` cua giai doan RENDER chu khong quet kho theo tien to:
       mot phep quet tien to se tim thay ca artifact cua mot lan chay lai da bi
       thay the, va phuc vu nham ban cu.
    """
    s = giai_doan_theo_ten(db, run.id, pipeline.RENDER)
    if s is None or s.status != STAGE_SUCCEEDED:
        return ""
    return next((k for k in ((s.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".mp4")), "")
