"""Quan sat mot lan chay — dong thoi gian tu du lieu BEN, khong tu log tam.

## Cau hoi ma tep nay phai tra loi duoc

Prompt 18 dat ra mot phep thu rat cu the: *"Mot ky su ho tro phai dinh vi duoc
giai doan hong ma khong phai doc thu muc tam hay Google Sheets."*

Do la mot phep thu ve **noi du lieu song**, khong phai ve dinh dang hien thi.
Mot dong thoi gian dep dung tu `logging.info` van truot phep thu do: log xoay
vong, log nam tren may cua worker, va worker do co the da bien mat.

⇒ Moi con so o day den tu ba nguon BEN: `asv_stage` (ta so huu), `jobs` (nen
  tang so huu), `job_events` (nen tang so huu). Khong nguon nao la tep tam.

## Hai khan gia, hai muc chi tiet — va do la mot yeu cau bao mat

Prompt 18 muc 6 doi tach "loi an toan cho nguoi dung" khoi "chi tiet cho nguoi
van hanh". Khong phai de goi gang: mot thong bao loi tho co the mang duong dan
tren dia, ten may, ten model, hay mot manh payload cua provider.

  `dong_thoi_gian(..., cho_van_hanh=False)`  -> khach doc duoc
  `dong_thoi_gian(..., cho_van_hanh=True)`   -> them attempt, worker, job id,
                                                loi goc, tai nguyen

⛔ Cai **mac dinh** la ban cho khach. Mot ham mac dinh tra ve ban day du roi doi
   nguoi goi nho tat di la mot ham se ro ri o lan quen dau tien.
"""
from __future__ import annotations

from sqlalchemy import select

from platform_core import job_events
from platform_core.models import Job

from . import features, pipeline

#: Chuoi hien cho khach khi mot giai doan hong ma ta khong co thong diep an toan.
#: ⚠️ Khong bao gio boc `str(exc)` tho vao day.
LOI_CHUNG = "giai doan nay khong hoan tat"


def _giay(bat, ket) -> float | None:
    if not bat or not ket:
        return None
    return round((ket - bat).total_seconds(), 3)


def dong_thoi_gian(db, run, *, cho_van_hanh: bool = False,
                   moi_giai_doan_toi_da: int = 50) -> dict:
    """Dong thoi gian cua ca lan chay, dung tu du lieu ben.

    ⭐ Sap theo `pipeline.CHUOI`, khong theo `created_at`: thu tu giai doan la
       mot su that cua **san pham**, con thu tu tao dong la mot chi tiet cua
       hang doi. Hai nhanh chay song song se lam thu tu thoi gian dao lung tung
       va mot nguoi doc se tuong chuoi da chay sai.
    """
    theo_ten = {s.stage: s for s in features.cac_giai_doan(db, run)}
    giai_doan: list[dict] = []

    for g in pipeline.CHUOI:
        s = theo_ten.get(g.ten)
        if s is None:
            giai_doan.append({"giai_doan": g.ten, "trang_thai": "chua_tao"})
            continue

        muc: dict = {
            "giai_doan": g.ten,
            "trang_thai": s.status,
            "bat_dau": s.started_at.isoformat() if s.started_at else None,
            "ket_thuc": s.finished_at.isoformat() if s.finished_at else None,
            "giay": _giay(s.started_at, s.finished_at),
            # Tham chieu ket qua: khoa luu tru, khong phai duong dan tren dia.
            "so_ket_qua": len((s.outputs or {}).get("khoa_asset") or []),
        }

        # ── Loi: hai muc chi tiet ──────────────────────────────────────────
        if s.error:
            muc["loi"] = (job_events.sanitize_text(s.error, limit=500)
                          if cho_van_hanh else LOI_CHUNG)

        if cho_van_hanh:
            muc.update({
                "so_lan_thu": int(s.attempt or 0),
                "job_id": s.job_id or "",
                "van_tay": s.fingerprint or "",
                "lan": g.app_slug,
                "tai_nguyen": g.tai_nguyen or "",
                "credit": int(s.credit_actual or 0),
            })
            job = db.get(Job, s.job_id) if s.job_id else None
            if job is not None:
                muc["job"] = {
                    "trang_thai": job.status,
                    "so_lan_thu": int(job.attempts or 0),
                    "worker": getattr(job, "worker_id", "") or "",
                    "provider_state": getattr(job, "provider_state", "") or "",
                }
                # 🔑 Su kien cua nen tang, DA duoc no loc. Ta khong tu loc lai:
                #    mot bo loc thu hai la mot bo loc thu hai phai bao tri, va no
                #    se lech khoi bo dau tien.
                muc["su_kien"] = [
                    {"ma": e.event_code, "muc": e.level,
                     "luc": e.created_at.isoformat(), "chi_tiet": e.details}
                    for e in job_events.timeline(
                        db, job.id, include_internal=True,
                        limit=moi_giai_doan_toi_da)
                ]

        giai_doan.append(muc)

    hong = [m for m in giai_doan if m["trang_thai"] in ("failed_terminal",
                                                        "failed_retryable")]
    ra = {
        "run_id": run.id,
        "trang_thai": run.status,
        "tao_luc": run.created_at.isoformat() if run.created_at else None,
        "ket_thuc_luc": run.finished_at.isoformat() if run.finished_at else None,
        "giai_doan": giai_doan,
        # 🔑 Cau tra loi cho "giai doan nao hong" — o ngay tang tren, khong bat
        #    nguoi doc phai duyet mang.
        "giai_doan_hong": [m["giai_doan"] for m in hong],
    }
    if cho_van_hanh:
        ra["chu_so_huu"] = run.owner_id
        ra["credit_da_giu"] = int(run.credit_held or 0)
        ra["credit_da_tinh"] = int(run.credit_actual or 0)
    return ra


def tom_tat_loi_cho_khach(db, run) -> str:
    """MOT cau, an toan, ve viec gi da hong. Rong neu khong hong.

    ⛔ `run.error` mang thong diep goc cua giai doan, va thong diep do co the
       chua duong dan tren dia hay ten model. Cho nay chi tra ve **ten giai
       doan** cong mot cau co dinh.
    """
    hong = [s for s in features.cac_giai_doan(db, run)
            if s.status == "failed_terminal"]
    if not hong:
        return ""
    ten = hong[0].stage
    return f"{ten}: {LOI_CHUNG}"
