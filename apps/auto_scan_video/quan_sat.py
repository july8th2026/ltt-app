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

from datetime import datetime, timezone

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


def _theo_utc(t):
    """Mot `datetime` doc tu CSDL -> luon co mui gio.

    🔴 **Cot khai `DateTime(timezone=True)` nhung SQLite KHONG luu mui gio.**

       `tables._now()` ghi `datetime.now(timezone.utc)`, con SQLite doc ra
       `2026-09-08 04:08:46.572361` — **naive**. Tren PostgreSQL thi co tz.

    ⇒ Cung mot cot, hai kieu gia tri, tuy backend. Va do la kieu lech te nhat:
      no dung o production va sai o moi cho ta NHIN THAY.

    ⭐ Naive o day **chinh la UTC**, vi chi `_now()` ghi cot nay. Nen gan UTC vao
       khong phai mot phong doan — no la doc lai dieu ta da biet.
    """
    if t is None or t.tzinfo is not None:
        return t
    return t.replace(tzinfo=timezone.utc)


def _giay_da_chay(run) -> float | None:
    """Giay tu luc tao toi luc xong (hoac toi bay gio).

    🔴 **Ban dau cho nay bat `TypeError` roi tra `None`** — mot cai bay dung
       hinh dang "nuot loi an toan": khong ai thay gi sai, va **dong ho khong
       bao gio hien o dev lan trong bo test**. Chi production (PostgreSQL) moi
       co tz, nen loi an o dung nhung noi ta soi.

    ⇒ Sua nguyen nhan (chuan hoa mui gio) thay vi giu nhanh nuot.
    """
    tao = _theo_utc(getattr(run, "created_at", None))
    if tao is None:
        return None
    moc = _theo_utc(getattr(run, "finished_at", None)) or datetime.now(timezone.utc)
    return max(0.0, (moc - tao).total_seconds())


def _tien_do_khach(giai_doan: list[dict], run) -> dict:
    """Ba so ma man tien do cua khach can: `%`, buoc dang chay, giay da chay.

    ⛔ **KHONG co ETA o day, va do la mot quyet dinh.**

       `V5_UI_INFORMATION_ARCHITECTURE.md` §7 cam gia ETA. Mot uoc "con 2 phut"
       dung tren mot lan chay chua do duoc gi la mot con so bia — va khach nho
       con so do, roi doi gap ba lan no. Khong hien gi thi ho khong bi hua.

    ⭐ Phan tram dem theo SO GIAI DOAN da xong tren tong so giai doan, khong theo
       thoi gian. No khong deu — `RENDER` lau hon `MEDIA_PREPARE` nhieu — nhung
       no **khong bao gio giat lui**, va mot thanh tien do giat lui la thu lam
       nguoi ta mat long tin vao ca man hinh.
    """
    tong = len(giai_doan) or 1
    xong = sum(1 for m in giai_doan if m["trang_thai"] == "succeeded")
    dang = next((m["giai_doan"] for m in giai_doan
                 if m["trang_thai"] == "running"), "")
    # Chua co buoc nao "running" nhung da co buoc xong -> buoc ke tiep la thu
    # khach dang cho. Noi ten no van dung hon la de trong.
    if not dang and run.status in ("queued", "running"):
        dang = next((m["giai_doan"] for m in giai_doan
                     if m["trang_thai"] in ("queued", "chua_tao")), "")

    da_chay = _giay_da_chay(run)

    return {
        "phan_tram": 100 if run.status == "done" else int(xong * 100 / tong),
        "dang_chay": dang,
        "da_chay_giay": da_chay,
    }


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

        # ── Don vi viec: thu ma DIEM CHOT biet ma giai doan khong biet ─────
        #
        # 🔑 Mot giai doan "succeeded" khong noi duoc **bao nhieu viec da lam
        #    that** va **bao nhieu duoc dung lai**. Hai lan chay cung ra
        #    "succeeded" nhung mot lan goi model 200 lan con lan kia goi 0 —
        #    va hoa don cua chung khac han nhau.
        dv = dem_don_vi(db, run, g.ten)
        if dv["tong"]:
            muc["don_vi"] = dv

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
        # ── Ba so cho giao dien khach (V5) ─────────────────────────────────
        #
        # 🔑 Tinh o DAY chu khong o template. Mot phep tinh trong Jinja la mot
        #    phep tinh khong phep kiem nao voi toi duoc, va ba so nay tra loi
        #    cau hoi khach hoi nhieu nhat ("con bao lau nua").
        **_tien_do_khach(giai_doan, run),
    }
    if cho_van_hanh:
        ra["chu_so_huu"] = run.owner_id
        ra["credit_da_giu"] = int(run.credit_held or 0)
        ra["credit_da_tinh"] = int(run.credit_actual or 0)
        # 🔑 So cai o CUNG mot cho voi dong thoi gian. Truoc pha 20 hai thu nay
        #    ton tai o hai truy van khac nhau, va mot nguoi van hanh muon tra loi
        #    "vi sao lan chay nay ton bao nhieu" phai tu ghep chung — tuc phai TU
        #    lam mot phep noi ma khong ai kiem.
        from . import su_dung as sd

        ra["so_ke"] = sd.so_ke(db, run)
        ra["doi_soat"] = doi_soat_nhanh(db, run)
    return ra


def dem_don_vi(db, run, stage: str) -> dict:
    """Dem don vi viec cua MOT giai doan, theo trang thai.

    ⭐ `dung_lai` la con so quan trong nhat o day va no khong co trong bang:
       mot don vi `succeeded` co van tay **khac** van tay hien tai la mot don vi
       thuoc mot cau hoi cu — no khong duoc tinh la "da lam roi". Xem
       `su_dung.da_xong`.
    """
    from .tables import ITEM_SUCCEEDED

    dem: dict[str, int] = {}
    credit = 0
    for it in features.cac_don_vi(db, run.id, stage):
        dem[it.status] = dem.get(it.status, 0) + 1
        credit += int(it.credit_actual or 0)
    return {"tong": sum(dem.values()), "theo_trang_thai": dem,
            "xong": dem.get(ITEM_SUCCEEDED, 0), "credit": credit}


def doi_soat_nhanh(db, run) -> dict:
    """Moi don vi CO TINH TIEN co truy duoc ve so cai khong, va nguoc lai.

    🔴 **Day la cau tra loi cho cong thoat cua pha 20**: "mot nguoi van hanh giai
       thich duoc MOI don vi da tinh tien tu bang chung ben vung".

       `su_dung.doi_soat` da chot dieu do o cap **rang buoc** — no NEM khi lech.
       Ham nay khong nem: no **bay ra** cho nguoi doc, vi mot man quan sat phai
       tra loi duoc ca khi he thong dang hong.

    ⛔ Hai chieu, khong phai mot:
         * don vi co credit ma khong co dong so cai -> tinh tien tu dau ra?
         * dong so cai da giao ma khong co don vi   -> lam viec gi ma khong ai ghi?
       Chi kiem mot chieu la de ngo dung nua kia ma minh khong nghi toi.
    """
    from . import su_dung as sd

    dong = list(sd.cac_dong(db, run))
    co_dong = {(d.stage, d.item_key) for d in dong if d.trang_thai == sd.DA_GIAO}

    thieu_dong, thieu_don_vi = [], []
    co_don_vi = set()
    for it in features.cac_don_vi(db, run.id):
        co_don_vi.add((it.stage, it.item_key))
        if int(it.credit_actual or 0) > 0 and (it.stage, it.item_key) not in co_dong:
            thieu_dong.append(f"{it.stage}/{it.item_key}")
    for k in co_dong:
        if k not in co_don_vi:
            thieu_don_vi.append(f"{k[0]}/{k[1]}")

    return {
        "khop": not thieu_dong and not thieu_don_vi,
        "so_don_vi": len(co_don_vi),
        "so_dong_da_giao": len(co_dong),
        # Cat ngan: mot man quan sat khong duoc bien thanh mot bai dai khi hong.
        "don_vi_co_tien_khong_co_so_cai": sorted(thieu_dong)[:20],
        "so_cai_khong_co_don_vi": sorted(thieu_don_vi)[:20],
    }


def tom_tat_cho_khach(db, run) -> dict:
    """Tien do va chi phi cho KHACH. Khong ten giai doan noi bo, khong duong dan.

    ⛔ Khach thay **so buoc da xong tren tong so buoc**, khong thay ten giai doan.
       Ten giai doan la mot chi tiet ky thuat cua ta; lo no ra bien moi lan doi
       ten mot giai doan thanh mot thay doi giao dien, va bien so do chuoi thanh
       thong tin cong khai.

    ⭐ Chi phi thi hien ra: khach tra tien, nen khach duoc biet minh tra cho cai
       gi — nhung theo **nang luc** (long tieng, tach tieng) chu khong theo ten
       ky thuat cua nha cung cap.
    """
    from . import su_dung as sd

    ds = features.cac_giai_doan(db, run)
    xong = sum(1 for s in ds if s.status == "succeeded")
    sk = sd.so_ke(db, run)
    return {
        "trang_thai": run.status,
        "so_buoc_xong": xong,
        "so_buoc": len(pipeline.CHUOI),
        "phan_tram": int(round(100.0 * xong / max(1, len(pipeline.CHUOI)))),
        "credit_da_giu": int(run.credit_held or 0),
        "credit_da_tinh": int(run.credit_actual or 0),
        # ⚠️ CHI ten nang luc va so luong. Khong `app_chu` — do la ten noi bo cua
        #    nha cung cap, va no khong phai viec cua khach.
        "chi_phi_theo_nang_luc": [
            {"nang_luc": m["nang_luc"], "don_vi": m["don_vi"],
             "so_luong": round(float(m["so_luong"]), 2), "credit": int(m["credit"])}
            for m in sk.get("theo_nang_luc") or []],
        "loi": tom_tat_loi_cho_khach(db, run),
    }


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
