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

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from platform_core import job_events
from platform_core.models import Job

from platform_core.i18n import N_

from . import features, ma_loi, pipeline, rang_giong

log = logging.getLogger(__name__)

#: Chuoi hien cho khach khi mot giai doan hong ma ta khong co thong diep an toan.
#: ⚠️ Khong bao gio boc `str(exc)` tho vao day.
LOI_CHUNG = "giai doan nay khong hoan tat"

# ⭐ **`NHAN_NANG_LUC` / `NHAN_NANG_LUC_KHAC` / `NHAN_DON_VI` da bi XOA — 25/09/2026.**
#
#    Ba bang nhan tieng Viet ("Doc loi long tieng", "Dich", "token", "giay"...)
#    ton tai de in **hoa don theo nang luc** cua khach (V6 pha 30). Gia phang thay
#    hoa don do bang MOT dong (`gia.hoa_don`), nen ⛔ khong con man hinh nao in nhan.
#
# 🔑 Da doc truoc khi xoa, ⛔ khong doan — ba cho, va ca ba deu am:
#      `su_dung.so_ke`                     tra ve `nang_luc` THO, ⛔ khong nhan
#      `dong_thoi_gian(cho_van_hanh=True)` nhet `so_ke` vao nguyen ven
#      `asv_chi_tiet.html` khoi van hanh   in `giai_doan`/`run_id`/`credit_*`/
#                                          `ket_xuat` — ⛔ khong he doc `so_ke`
#    Khong mot template, route, public API hay man quan tri nao doc ba bang nay.
#
# ⚠️ Va banh coc `test_482::test_moi_nang_luc_TINH_TIEN_trong_ma_deu_co_NHAN` da bi
#    xoa **cung luc**, co chu dinh: giu mot phep kiem gac mot **nghia vu ma** thi te
#    hon xoa ca hai. No van xanh, van bat moi nang luc moi phai dich mot cau — cho
#    mot man hinh ⛔ khong con ton tai.
#
# ⇒ Ngay nao co mot man VAN HANH thuc su muon doc ten nang luc bang tieng Viet:
#   dung lai bang **o do**, cho nguoi doc that, ⛔ dung khoi phuc mot bang chung.
#   Nguoi van hanh doc `nang_luc` tho duoc — do la ngon ngu cua ho.


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


#: `{ten_giai_doan: khoa trong `outputs` noi rang no CO THAT SU lam viec cua no}`.
#:
#: 🔴 `succeeded` tra loi *"⛔ khong hong"*, ⛔ khong tra loi *"da lam"*. Mot giai
#:    doan bi TAT bang cau hinh van chay qua tuc thi roi bao `succeeded`, va nhan
#:    cua no tren man khach thi khang dinh viec ay DA XONG.
#:
#: ⭐ Bang nay CO Y chi mot dong. No ⛔ khong phai mot khuon cho moi giai doan —
#:    chi nhung giai doan **tat duoc bang cau hinh** moi can tra loi cau hoi nay,
#:    va hom nay chi co `qc_ai`. Them mot giai doan tat duoc thi them mot dong.
KHOA_DA_LAM: dict[str, str] = {"qc_ai": "qc_ai_bat"}


def _da_lam(ten: str, outputs) -> bool | None:
    """`True`/`False` khi giai doan CO khai, `None` khi no ⛔ khong khai gi.

    ⚠️ Ba trang thai, ⛔ khong hai: *"da lam"*, *"da chay va ⛔ khong lam"*, va
       *"⛔ khong khai"*. Gop hai cai sau lai thi moi giai doan ⛔ khong co bang
       khai deu bi in ra la "bo qua" — mot bao dong gia tren 12 trong 13 giai
       doan, va bao dong gia lam nguoi ta tat cong.
    """
    khoa = KHOA_DA_LAM.get(ten)
    if not khoa:
        return None
    v = (outputs or {}).get(khoa)
    return None if v is None else bool(v)


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
            # ── `succeeded` co nghia la DA LAM, hay chi la DA CHAY QUA? ──────
            #
            # 🔴 `qc_ai` **mac dinh TAT** (`LTT_ASV_QC_AI`) va khi tat no chay qua
            #    tuc thi roi bao `succeeded`. Nhan cua no la *"Soat lai nghia ban
            #    dich"*, nen khach doc duoc mot dong khang dinh ban dich DA DUOC
            #    SOAT trong khi ⛔ khong mot cau nao duoc doc. Cung ho loi voi
            #    `"VLM de xuat bo"` (`123285ae`): mot ban khai SAI xuat xu di ra
            #    **cho khach**.
            #
            # ⭐ Con so tra loi da nam san trong `outputs` tu truoc
            #    (`giai_doan_qc_ai.py:140` ghi `qc_ai_bat: False`) — ⛔ khong ai
            #    doc no. Day la cho no duoc doc.
            #
            # ⚠️ `None` = *"giai doan nay ⛔ khong khai gi"*, khac han `False` =
            #    *"da chay va ⛔ khong lam gi"*. Nguoi doc template phan biet hai
            #    cai, nen ⛔ khong duoc gop chung vao mot gia tri gia.
            "da_lam": _da_lam(g.ten, s.outputs),
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
        # W4': khuon cau cho giai doan hong MANG MA (vd lech lan) — `LOI_CO_MA`.
        "loi_co_ma": loi_co_ma_cho_khach(db, run),
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
        # 🔑 **LY DO HONG o CUNG mot cho voi dong thoi gian** (Task 25, 27/09).
        #    Cung lap luan voi `so_ke` ngay tren: mot nguoi van hanh mo man nay ra
        #    la de hoi *"vi sao lan chay nay hong"*, va truoc day cau tra loi nam
        #    o **ba** cho khac nhau (`AsvUsage`, `AsvStage.error`, `run.error`) —
        #    nen ai muon tra loi phai TU lam mot phep noi ma khong ai kiem. Do la
        #    dung cho `test_448` lam sai va in `[]` cho mot luot co ly do ro rang.
        #
        # ⛔ CHI o nhanh `cho_van_hanh`: `ly_do` la thong diep THO. Ban cho khach
        #    la `loi` (da `sanitize_text`) va `loi_co_ma` o tren.
        ra["vi_sao_hong"] = vi_sao_hong(db, run)
        # ⭐ Preset khach chon + duong render no keo theo — xem `duong_render_cua`.
        ra["duong_render"] = duong_render_cua(run)
    return ra


def duong_render_cua(run) -> dict:
    """`{"preset", "duong"}` — khach chon preset nao, va no di duong RE hay DAT.

    🔴 **Vi sao truong nay ton tai.**

       Gia phang (`gia.py`, 25/09/2026) tinh `10 credit x so phut video nguon` —
       mot ham cua **do dai**, khong cua tap thao tac. Gia thiet ngam duoi no la
       *phan lon luot chay di duong `SAO_CHEP`*, o do luong hinh duoc **chep**
       (`-c:v copy`) va gan nhu khong ton mot giay ma hoa nao.

    ⭐ **Bien dieu khien la PRESET.** `che_do_render.che_do_cho` nhan **dung mot**
       tham so — `preset` — va co phep kiem chot chu ky do. Cac co bien tap
       (`vung_che`, `lop_phu`, `logo`, `phu_de` dot hinh, `bien_tap`) bi `ban_dung.kiem`
       tu choi tren duong `SAO_CHEP`, tuc chung chi song o `smart_localize`, **noi
       da ma hoa lai san** ⇒ chung ⛔ khong day luot nao sang duong dat.

    ⇒ Nen cau hoi dung la *"bao nhieu % luot di duong dat, va PRESET nao?"* — va
      truong nay ghi **ca hai**, cho tung lan chay. Sau mot thang no tra loi bang
      **so lieu**: *khach chon "Rut gon co bien tap" bao nhieu %?*

    ⛔ Va no **khong** duoc vao hoa don cua khach: khach tra mot gia phang, duong
       render la viec cua ta. Lo no ra la mo cua cho cau *"sao toi phai tra them vi
       may cua anh cham hon"* cho mot khoan khach khong he tra them.

    ⭐ Ca hai gia tri suy tu **PRESET da khai**, khong tu du lieu cua lan chay (mot
       ban bien tap giu **tat ca** canh van la preset cat, va no van ma hoa lai).
       Nen truong nay doc duoc **tu luc tao run**, truoc khi mot giai doan nao chay.
    """
    from . import cai_dat as cd
    from . import che_do_render as cdr

    try:
        preset = cd.doc(run).preset
        return {"preset": preset, "duong": cdr.che_do_cho(preset)}
    except Exception as e:                   # noqa: BLE001 - preset la, ban ghi cu
        # ⛔ `""` chu khong `cdr.SAO_CHEP`: mot preset khong doc duoc la "chua
        #    biet", va dem no vao o duong RE lam thong ke nghieng ve phia de chiu
        #    — dung chieu lech khien khong ai di kiem lai.
        # ⛔ VAN NUOT (ban ghi cu / preset la khong duoc lam sap man hinh),
        #    nhung phai de lai vet: neu MOI luot roi vao day thi ca cot thong ke
        #    la rong, va mot cot rong khong tu noi vi sao no rong.
        log.warning("quan_sat: khong doc duoc preset render (run=%s): %s",
                    getattr(run, "id", "?"), type(e).__name__)
        return {"preset": "", "duong": ""}


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


#: Nhan `nguon` cua tung dong `vi_sao_hong`. ⭐ MOI dong khai no den tu dau:
#: "so cai noi vay" va "giai doan noi vay" la hai loai bang chung khac nhau, va
#: mot nguoi van hanh doc chung khac nhau.
NGUON_SO_CAI = "so_cai"
NGUON_GIAI_DOAN = "giai_doan"
NGUON_RUN = "run"

#: 🔴 **Gia tri quan trong nhat cua tep nay.** Xem `vi_sao_hong`.
NGUON_KHONG_DOC_DUOC = "khong_doc_duoc"


def vi_sao_hong(db, run) -> list[dict]:
    """MOI ly do khong-thanh-cong cua mot lan chay. ⛔ Khong bao gio rong im lang.

    🔴 **Vi sao ham nay ton tai — do duoc 27/09/2026 (Task 25).**

       `test_448` dung bang ly do CHI tu `AsvUsage` co `trang_thai != "da_giao"`.
       Bon luot G17 hong o `voice_synthesis` ⛔ khong co dong nao nhu vay — giai
       doan chet **TRUOC** khi ghi so — nen bao cao in `[]`, trong khi
       `asv_stage.error` VA `asv_run.error` mang dung cau
       `"voice_synthesis: Tep tieng sinh ra qua ngan (0.0s)."`.

    ⇒ Cho noi giua *"lan chay hong"* va *"ly do hong"* **vut truong im lang**,
      va `[]` doc **y het** *"lan chay nay khong co ly do hong"*. Do la ho loi
      "hai trang thai gop thanh mot gia tri": ⛔ khong sai ket qua, chi **mat
      kha nang phan biet** — va o day cai mat la thu duy nhat con lai khi he
      thong dang hong.

    ⭐ Nen ham nay:
      · doc **BA** nguon, ⛔ khong mot: so cai (`nang_luc` nao tu choi), giai
        doan (`error` cua tung giai doan hong), va `run.error` (cau cuoi cung
        `thi_hanh` da chot);
      · va khi lan chay **da hong** ma ⛔ khong nguon nao noi duoc gi, no tra
        **mot dong** `nguon = NGUON_KHONG_DOC_DUOC` thay vi `[]`. *"Toi khong
        doc duoc ly do"* va *"khong co ly do"* la hai cau khac nhau, va gop
        chung lai la giau dung cho dang hong.

    ⚠️ `[]` VAN co nghia — cho mot lan chay ⛔ khong hong gi ca. Do la ly do dieu
       kien duoi day doc `run.status`, ⛔ khong doc "co tim thay gi khong".

    ⛔ Cho NGUOI VAN HANH, ⛔ khong cho khach: `error` tho co the chua duong dan
       hay ten model. Ban cho khach la `tom_tat_loi_cho_khach` (mot cau, an toan).
    """
    # ⛔ Dung `select` DA import o dau tep, ⛔ khong import lai tai cho: mot ban
    #    thu hai lam `ruff` bao `F811` va — dang ke hon — lam ban o dau tep
    #    thanh "khong ai dung" (`F401`), tuc mot don dep dung sau se xoa no va
    #    lam hong mot cho khac.
    from .tables import RUN_DONE, STAGE_FAILED_RETRYABLE, STAGE_FAILED_TERMINAL
    from .tables import AsvUsage

    ra: list[dict] = []

    # ── (1) So cai: don vi nao KHONG "da giao" ─────────────────────────────
    #    ⭐ Nguon CU (`test_448`) — giu nguyen, ⛔ khong thay the. Mot ban sua
    #       lam mat nguon cu la doi mot lo hong lay mot lo hong khac.
    for r in db.execute(select(AsvUsage).where(
            AsvUsage.run_id == run.id)).scalars():
        if r.trang_thai == su_dung_da_giao():
            continue
        ra.append({"nguon": NGUON_SO_CAI, "nang_luc": r.nang_luc,
                   "stage": str(r.stage or ""),
                   "trang_thai": r.trang_thai,
                   "ly_do": str((r.ghi_chu or {}).get("ly_do") or "")[:300]})

    # ── (2) Giai doan hong: `error` cua CHINH no ───────────────────────────
    for s in features.cac_giai_doan(db, run):
        if s.status not in (STAGE_FAILED_TERMINAL, STAGE_FAILED_RETRYABLE):
            continue
        ra.append({"nguon": NGUON_GIAI_DOAN, "stage": s.stage,
                   "trang_thai": s.status,
                   "ma_loi": str((s.outputs or {}).get("ma_loi") or ""),
                   "ly_do": str(s.error or "")[:600]})

    # ── (3) Cau cuoi cung cua ca lan chay ─────────────────────────────────
    #    ⚠️ Them ke ca khi (2) da noi: `run.error` la cau `thi_hanh` CHOT, va no
    #       co the mang ten giai doan + mot phan loai ma `s.error` khong co.
    if str(run.error or "").strip():
        ra.append({"nguon": NGUON_RUN, "trang_thai": str(run.status or ""),
                   "ly_do": str(run.error)[:600]})

    # 🔴 **Dieu kien la "khong DOC DUOC ly do", ⛔ khong phai "khong co dong".**
    #    Ban dau cho nay hoi `if not ra`, va phep kiem do bat ngay: mot giai doan
    #    `failed_terminal` voi `error = ""` cho ra MOT dong co that voi
    #    `ly_do = ""` — tuc dung cai cam giac "khong co ly do" da mac phai, chi
    #    doi tu `[]` sang `[{…, 'ly_do': ''}]`. Mot dong khong co ly do ⛔ khong
    #    phai mot ly do.
    if str(run.status or "") != RUN_DONE and not any(
            str(d.get("ly_do") or "").strip() for d in ra):
        ra.append({
            "nguon": NGUON_KHONG_DOC_DUOC,
            "trang_thai": str(run.status or ""),
            "so_dong_khong_ly_do": len(ra),
            "ly_do": (f"lan chay o trang thai {run.status!r} va KHONG nguon nao "
                      f"doc duoc ly do: {len(ra)} dong tim thay deu co `ly_do` "
                      f"rong (so cai / giai doan / run.error)"),
        })
    return ra


def su_dung_da_giao() -> str:
    """`su_dung.DA_GIAO`, nap muon — ⛔ khong go lai chuoi.

    ⚠️ `quan_sat` ⛔ khong import `su_dung` o dau tep (vong import: `su_dung`
       doc `tables`, `quan_sat` doc `features` doc `su_dung`). Mot chuoi go tay
       o day se la ban thu hai cua mot hang so, va ho loi do da co ten trong kho
       nay.
    """
    from . import su_dung

    return su_dung.DA_GIAO


def tom_tat_cho_khach(db, run) -> dict:
    """Tien do va chi phi cho KHACH. Khong ten giai doan noi bo, khong duong dan.

    ⛔ Khach thay **so buoc da xong tren tong so buoc**, khong thay ten giai doan.
       Ten giai doan la mot chi tiet ky thuat cua ta; lo no ra bien moi lan doi
       ten mot giai doan thanh mot thay doi giao dien, va bien so do chuoi thanh
       thong tin cong khai.

    ⭐ Chi phi thi hien ra: khach tra tien, nen khach duoc biet minh tra cho cai
       gi.

    ## 🔑 Gia PHANG (25/09/2026) — hoa don la MOT dong, khong phai nam

    Truoc do cho nay tra ve `chi_phi_theo_nang_luc`: mot bang theo nang luc (doc
    loi long tieng · dich · viet loi thoai · xem tung canh · ...), vi gia cu **cong
    don** theo tung nang luc. Gia phang xoa can cu cua bang do: khach tra
    `10 x so phut video nguon`, va mot bang nam dong cho mot con so phang la mot
    bang **noi doi ve cach tinh** — no goi y rang bo mot nang luc di se tra it hon.

    ⚠️ Phan **do luong** theo nang luc ⛔ KHONG bi xoa: `su_dung.so_ke` va ban van
       hanh (`dong_thoi_gian(cho_van_hanh=True)`) giu nguyen no, vi no tra loi cau
       *"cho nao dang dot tien"* — cau cua nguoi van hanh, khong phai cua khach.
    """
    from . import gia
    from .tables import RUN_TERMINAL

    ds = features.cac_giai_doan(db, run)
    xong = sum(1 for s in ds if s.status == "succeeded")
    giay_nguon, nguon_do = features.thoi_luong_nguon_giay(db, run)
    da_do_do_dai = nguon_do != features.CHUA_DO
    hd = gia.hoa_don(giay_nguon) if da_do_do_dai else {}
    return {
        "trang_thai": run.status,
        "so_buoc_xong": xong,
        "so_buoc": len(pipeline.CHUOI),
        "phan_tram": int(round(100.0 * xong / max(1, len(pipeline.CHUOI)))),
        "credit_da_giu": int(run.credit_held or 0),
        "credit_da_tinh": int(run.credit_actual or 0),
        # ⭐ MOT dong hoa don: `<so_phut> phut x <don_gia> = <credit>`.
        #
        # ⛔ `None` chu khong `0` khi chua do duoc do dai: *"chua do duoc"* khac
        #    *"video dai 0 giay"*, va gop hai trang thai vao mot gia tri la mot ho
        #    loi da co ten trong kho nay. Man hinh doc `da_do_do_dai` de biet no
        #    dang o ca nao, va truoc do khach doc `credit_da_giu` ngay tren.
        #
        # ⛔ KHONG dua `nguon_do` vao day: gia tri cua no la ten mot giai doan noi
        #    bo (`media_prepare`), va `test_446` chan dung viec do.
        "hoa_don": {
            "so_phut": hd.get("so_phut"),
            "credit": hd.get("credit"),
            "giay_nguon": hd.get("giay_nguon"),
            "don_gia": gia.GIA_CREDIT_MOI_PHUT,
            "luat_lam_tron": gia.luat_lam_tron(),
            "da_do_do_dai": da_do_do_dai,
        },
        # ⭐ Hoan lai CHI noi khi da quyet toan: truoc do con so "da tinh" con
        #    dang tang, va mot con so hoan lai tinh giua chung la mot loi hua sai.
        #    Cung cong thuc voi `features.quyet_toan`: thu min(thuc te, giu).
        "da_quyet_toan": run.status in RUN_TERMINAL,
        "hoan_lai": (max(0, int(run.credit_held or 0) - int(run.credit_actual or 0))
                     if run.status in RUN_TERMINAL else None),
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


#: Ma loi ON DINH (`thi_hanh` ghi vao `outputs.ma_loi` cua giai doan hong) ⇒ cau
#: cho khach. Chi nhung ma ma "Thu lai buoc nay" **chac chan** hong y het.
#:
#: ⭐ **DAN XUAT tu `ma_loi.SO_MA`, khong go lai.** Truoc 24/09 bang nay go lai
#:    hai cau lech-lan cua `ltt_voice` VA spread `rang_giong.CAU_CHUA_RANG` —
#:    tuc mot nua no la ban thu hai cua cung mot cau, mot nua la ban duy nhat.
#:    `ma_loi.py` gio la so duy nhat va tep nay tro toi no; `test_3200` so bang
#:    `is` nen mot ban sao khong lot qua duoc.
#:
#: ⚠️ Hom nay `LOI_CO_MA` == `SO_MA`: **moi** ma on dinh hien co deu la ma ma thu
#:    lai chac chan hong. Neu mai co mot ma thu lai duoc thi tach o day (loc
#:    `SO_MA`), ⛔ khong phai bang cach go lai cau.
LOI_CO_MA = dict(ma_loi.SO_MA)


def loi_co_ma_cho_khach(db, run) -> str:
    """Khuon cau `N_()` (chua dich) cho giai doan hong MANG MA da biet; rong neu
    khong co. Rong ⇒ man hinh giu ban loi chung kem nut thu lai.

    ⭐ Doc `outputs.ma_loi` — truong co cau truc — chu khong doc `error`: chu tu
       do cua van hanh doi theo ngon ngu tien trinh va theo moi lan ai do viet
       lai cho de doc.
    """
    for s in features.cac_giai_doan(db, run):
        if s.status == "failed_terminal":
            ma = str((s.outputs or {}).get("ma_loi") or "")
            return LOI_CO_MA.get(ma, "")
    return ""


# ══════════════════════════════════════════════════════════════════════════════
#  Duyet canh — V6 pha 09
# ══════════════════════════════════════════════════════════════════════════════

#: Ti le be nhat mot canh duoc ve tren thanh, tinh theo phan tram.
#:
#: ⭐ Mot canh 0,4 giay trong mot video 30 phut ra 0,02% — tuc **khong mot diem
#:    anh nao**. Khach dem duoc muoi canh trong danh sach nhung chi thay chin
#:    vach, va khong co cach nao doan la vi sao. San nay lam no hien ra.
#:
#: ⚠️ No lam tong be rong vuot 100% khi co that nhieu canh vun. Do la danh doi
#:    co chu y: mot thanh dai hon khung mot chut van doc duoc, con mot canh bien
#:    mat thi khong.
SAN_BE_RONG_PT = 0.4


def dong_canh(db, kho, run) -> dict | None:
    """Cac canh cua lan chay + quyet dinh GIU/CAT, de khach XEM.

    Tra `None` khi giai doan `edit_plan` chua xong hoac khong doc duoc — man
    hinh khi do khong hien khoi nay, thay vi hien mot khoi rong.

    ## ⛔ Vi sao KHONG tra `ly_do` cho khach

    `ban_bien_tap._quyet_dinh_mot_canh` ghi `ly_do` cho **nguoi van hanh**:
    *"VLM de xuat bo (tin 0.91 >= nguong 0.85, canh co loi thoai)"*. Cau do
    mang ten mot he con, mot con so nguong va mot tu viet tat — dung ba thu ma
    `routes.py` muc 2 va `test_447` nhom D cam dua ra man khach.

    ⇒ Nhan cho khach suy tu **truong co cau truc** (`thao_tac`), khong tu chuoi.
      Doc mot chuoi tu do de doan y no la doc thu dai dien thay vi doc thu that,
      va no se vo im lang vao ngay ai do sua mot tu trong cau.

    ## ⚠️ Mot dieu ham nay KHONG noi duoc, va noi ro ra thay vi doan

    `_ap_chinh_sach_an_toan` co the **hoan mot lenh cat** de dat san giu lai —
    no lat `thao_tac` ve GIU nhung giu nguyen `do_tin` va `bang_chung`. Nen mot
    canh duoc hoan cat **khong phan biet duoc** voi mot canh duoc giu ngay tu
    dau, neu chi nhin cac truong co cau truc.

    ⛔ Va cach "sua" hien nhien — do chuoi `ly_do` xem co chua "hoan cat" khong
       — chinh la thu doan tren vua cam. Ban sua dung la them mot truong co cau
       truc vao `QuyetDinh`, va do la mot lan doi luoc do (`PHIEN_BAN_BAN`), nen
       no thuoc mot pha co chu dinh chu khong phai lam ke o day.

    ⇒ Hom nay ta noi su that o **cap ban**: `ghi_chu["da_hoan_cat"]` cho biet co
      bao nhieu canh duoc giu lai vi chinh sach, va khoi giao dien noi cau do
      mot lan cho ca danh sach.
    """
    import json

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.EDIT_PLAN)
    if gd is None or gd.status != "succeeded":
        return None
    khoa = [k for k in (((gd.outputs or {}) if gd else {}).get("khoa_asset") or [])
            if str(k).endswith(".json")]
    if not khoa:
        return None
    try:
        with kho.open(khoa[0]) as f:
            goi = json.loads(f.read().decode("utf-8"))
    except (OSError, ValueError):
        # ⛔ Nuot CO CHU DICH, va chi o day: mot artifact khong doc duoc khong
        #    duoc lam vo trang ket qua cua mot lan chay DA XONG. Khach van tai
        #    duoc video; ho chi khong thay bang ke canh.
        return None

    ban = (goi.get("ban") or {})
    chi_muc = (goi.get("chi_muc") or {})
    theo_ma = {str(q.get("ma_canh")): q for q in (ban.get("quyet_dinh") or [])}
    tong = float(chi_muc.get("thoi_luong") or ban.get("thoi_luong_nguon") or 0.0)

    canh: list[dict] = []
    giu_giay = 0.0
    for c in (chi_muc.get("canh") or []):
        bat, ket = float(c.get("bat") or 0.0), float(c.get("ket") or 0.0)
        q = theo_ma.get(str(c.get("ma")), {})
        # ⭐ Vang mat khoi ban = GIU. Cung mac dinh voi `_quyet_dinh_mot_canh`:
        #    cat la hanh dong phai co can cu, giu thi khong.
        la_giu = str(q.get("thao_tac") or "keep") != "cut"
        dai = max(0.0, ket - bat)
        if la_giu:
            giu_giay += dai
        canh.append({
            "ma": str(c.get("ma") or ""),
            "bat": round(bat, 3), "ket": round(ket, 3), "dai": round(dai, 3),
            "giu": la_giu,
            "bat_pt": round(100.0 * bat / tong, 4) if tong > 0 else 0.0,
            "rong_pt": (max(SAN_BE_RONG_PT, round(100.0 * dai / tong, 4))
                        if tong > 0 else 0.0),
        })

    ghi_chu = dict(ban.get("ghi_chu") or {})
    return {
        "thoi_luong": round(tong, 3),
        "canh": canh,
        "so_canh": len(canh),
        "so_giu": sum(1 for c in canh if c["giu"]),
        "so_cat": sum(1 for c in canh if not c["giu"]),
        "giu_giay": round(giu_giay, 3),
        # Xem docstring: day la cho DUY NHAT hom nay noi duoc ve viec hoan cat.
        "da_hoan_cat": int(ghi_chu.get("da_hoan_cat") or 0),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Bang chung chat luong — asv-final 23/09 (lan `gui`)
# ══════════════════════════════════════════════════════════════════════════════

#: Nhan cua tung BO DO trong `apps.asv_gpu.do_luong.bo_do.BO_DO`.
#:
#: ⭐ Nhan noi **cai gi duoc do**, khong noi TEN MODEL. Khach khong biet SQUIM
#:    hay MetricX la gi, va ho khong can biet: ho can biet ai da nghe lai ban
#:    doc va ai da soat lai ban dich.
NHAN_BO_DO = {
    "giong": N_("Đọc có đúng lời không"),
    "chat_luong_tieng": N_("Tiếng đọc có sạch không"),
    "dich": N_("Bản dịch có sát nghĩa không"),
}

#: Trang thai cua mot bo do -> cau cho khach.
#:
#: 🔴 `khong_kha_dung` phai NOI RA, khong duoc im lang. Luat §2 cua brief chung:
#:    *"Model thieu ⇒ danh dau QC `khong_kha_dung`; ⛔ khong lui im lang ve
#:    heuristic tu che"*. Mot bang bo mat hang "chua do duoc" doc y het mot bang
#:    da do het va deu dat — va do la dung thu bang nay ton tai de chan.
NHAN_TRANG_THAI_BO_DO = {
    "xong": N_("đã đo"),
    "khong_kha_dung": N_("chưa đo được trên máy chủ"),
    "loi": N_("đo không xong"),
}


def _outputs(db, run, ten_giai_doan: str) -> dict:
    """`outputs` cua MOT giai doan, hoac `{}` khi giai doan do chua chay.

    ⚠️ `thi_hanh` do `tom_tat` cua giai doan **phang** vao `outputs`, nen moi
       khoa duoi day la mot khoa cua chinh `tom_tat` do — khong phai mot cau
       truc long. Xem `thi_hanh.py:388`.
    """
    for s in features.cac_giai_doan(db, run):
        if s.stage == ten_giai_doan:
            return dict(s.outputs or {})
    return {}


def bang_chung_chat_luong(db, run) -> dict | None:
    """Bang chung KHACH doc duoc ve mot lan chay. `None` khi chua co gi.

    🔴 **Bon con so nay da ton tai tu truoc, va khong mot cai nao voi toi duoc
       man hinh cua nguoi tra tien.**

       `so_canh_hong`/`do_phu_bang_chung` (lan `fix-toc-do`), bao cao QC
       (`qc.tom_tat`), trang thai tung bo do (`giai_doan_qc_do_luong`) va nguon
       loi thoai THAT (`giai_doan_chep_loi` ghi `dinh_tuyen`) deu nam trong `asv_stage.outputs`
       — tuc trong CSDL, doc duoc, va chi doc duoc boi mot nguoi mo CSDL ra.

       Hau qua do duoc o luot nen v3: `smart_localize` giao mot video **khong
       cat mot canh nao** vi VLM hong 4/12 luot, va man hinh cua khach noi dung
       mot chu: *"Da xong."*

    ⇒ `do_phu_bang_chung` la con so tra loi cau ay, va no phai nam canh cau "Da
      xong" chu khong nam trong mot tep JSON o kho.

    ⛔ Khong mo kho luu tru o day. Moi thu duoi day nam san trong `outputs` —
      mot man hinh hoi lai ba giay mot lan khong duoc keo mot artifact ve.
    """
    from . import nguon_loi as nguon_loi_mod, qc as qc_mod, qc_ai as qc_ai_mod

    ra: dict = {}

    # ── Loi thoai goc lay tu dau ───────────────────────────────────────
    #
    # ⭐ Truong nay GIU sau khi o chon nguon bi RUT (Task 21, 26/09), va no doi
    #    vai: truoc kia no doi chieu voi thu KHACH EP; nay no la PROVENANCE —
    #    *"lan chay nay lay loi tu dau"* — va no phai tra loi duoc CA cho nhung
    #    lan chay 22–26/09 da di duong `ocr`/`embedded`.
    dt = dict(_outputs(db, run, pipeline.TRANSCRIBE).get("dinh_tuyen") or {})
    ma_nguon = str(dt.get("nguon_loi") or "")
    if ma_nguon:
        ra["nguon_loi"] = {
            "ma": ma_nguon,
            # ⚠️ Ma NGOAI bang (vd. `ocr` cua mot lan chay cu) in nguyen MA.
            #    ⛔ Khong bia mot nhan tieng Viet cho mot duong khong con ton
            #    tai — lam vay la noi voi khach rang duong do van chay duoc.
            "nhan": nguon_loi_mod.NHAN_NGUON_THAT.get(ma_nguon, ma_nguon),
        }

    # ── Do phu bang chung cua buoc chon canh (lan `fix-toc-do`) ─────────────
    bt = _outputs(db, run, pipeline.EDIT_PLAN)
    if bt.get("so_canh"):
        so_canh = int(bt.get("so_canh") or 0)
        ra["canh"] = {
            "so_canh": so_canh,
            "so_canh_da_doc": int(bt.get("so_canh_da_doc") or 0),
            "so_canh_hong": int(bt.get("so_canh_hong") or 0),
            # ⚠️ Phan tram, lam tron ve so nguyen: `0,8333` tren man hinh cua
            #    khach la mot con so khong ai doc duoc thanh mot cau.
            "do_phu_pt": round(100.0 * float(bt.get("do_phu_bang_chung") or 0)),
        }

    # ── Cong QC tat dinh (T1..T18) — CHI KY THUAT ───────────────────────────
    q = _outputs(db, run, pipeline.QC)
    if q.get("qc_phien_ban"):
        hong = [str(m) for m in (q.get("qc_muc_hong") or [])]
        ra["qc"] = {
            # ⚠️ `ky_thuat_dat`, khong phai "dat": co nay khong doc nghia ban dich
            #    hay chat luong giong. Xem `qc.tom_tat` va `LOI_TONG.md` N-02.
            "ky_thuat_dat": bool(q.get("qc_ky_thuat_dat")),
            "so_muc_hong": int(q.get("qc_so_muc_hong") or 0),
            # ⭐ Ma VA nhan. Ma de nguoi ho tro noi chuyen duoc voi bao cao
            #    trong kho; nhan de khach hieu phep kiem do hoi cai gi.
            "muc_hong": [{"ma": m, "nhan": qc_mod.NHAN_MUC.get(m, m)}
                         for m in hong],
        }

    # ── Bo do tren card (WER/CER · SQUIM · MetricX) ─────────────────────────
    dl = _outputs(db, run, pipeline.QC_DO_LUONG)
    if dl.get("do_luong"):
        ra["do_luong"] = {
            # ⚠️ `so_doan_do` dem doan DA CHUAN BI, ⛔ khong doan DO DUOC — xem
            #    `giai_doan_qc_do_luong.tom_tat_do_luong`. Giu lai vi cho khac doc
            #    no, nhung ⛔ KHONG dung no cho cau "da do".
            "so_doan_do": int(dl.get("so_doan_do") or 0),
            # 🔴 Con so ma man KHACH phai in. Truoc 27/09, `asv_chi_tiet.html:223`
            #    in `so_doan_do` duoi nhan *"N doan da do"*: voi bo do `giong`
            #    `khong_kha_dung` (thieu qc-venv / model / card) thi `ket_qua` rong
            #    ⇒ `so_giong_khong_dat = 0`, va khach doc duoc *"da do 95 doan,
            #    ⛔ khong doan nao sai"* trong khi ⛔ KHONG doan nao duoc do.
            #
            # ⭐ `tom_tat_do_luong` DA sinh `so_doan_da_do` de tra loi dung cau ay
            #    va CO Y ⛔ khong doi nghia khoa cu — nhung ⛔ khong ai doi NGUOI
            #    DOC sang khoa moi, nen con bo van o nguyen cho no dang o.
            "so_doan_da_do": int(dl.get("so_doan_da_do") or 0),
            "so_giong_khong_dat": int(dl.get("so_giong_khong_dat") or 0),
            "so_canh_bao_tieng": len(dl.get("canh_bao_tieng") or []),
            "bo_do": [
                {"ma": ten,
                 "nhan": NHAN_BO_DO.get(ten, ten),
                 "trang_thai": str(tt or ""),
                 "nhan_trang_thai": NHAN_TRANG_THAI_BO_DO.get(str(tt or ""),
                                                              str(tt or ""))}
                for ten, tt in (dl.get("do_luong") or {}).items()
            ],
        }

    # ── Lop NGU NGHIA, va so muc CON LAI chua sua ───────────────────────────
    #
    # 🔴 **N-03: he thong DA DO 44/95 muc dich chua sat va 85 muc con lai, luu vao
    #    `outputs` + so cai, roi KHONG hien cho khach.** Luot B 24/09 giao mot
    #    video ma he thong tu cham 46% cau la dich chua sat, va man hinh khong noi.
    #
    # ⛔ Khiem khuyet CHAT LUONG thi da khai (`so_giong_khong_dat` o duoi). Day la
    #    khiem khuyet TRUNG THUC, va no nang hon: khach khong the hoi ve mot con
    #    so khong ai cho ho thay.
    #
    # ⭐ Khong can do gi moi — du lieu co san, chi la chua ai noi. Nen day khong
    #    phai mot danh doi giua chi phi va chat luong; khong co gi de can.
    # 🔴 **...va roi 24/09 phep do noi nguoc lai: con so do KHONG khai duoc.**
    #
    #    Xac thuc bo cham tren 100 cap FLORES zh->vi (ban dich CUA NGUOI): no
    #    gan **45 %** la "dich chua sat" cho ban dich chuyen nghiep, trong khi
    #    luot that cua ta bi gan 46 %. Hai con so trung nhau nghia la no khong
    #    phan biet duoc ban dich cua ta voi mot ban hoan hao.
    #
    # ⛔ Nen khai no la mot khiem khuyet TRUNG THUC theo chieu NGUOC lai: mot
    #    nua con so la bao dong gia, va khach doc "44/95 cau dich chua sat" se
    #    hieu sai ve san pham ho vua mua. `qc_ai.khai_cho_khach()` la mot phep
    #    tinh tu ti le DA DO — ha duoc ti le thi man hinh tu bat lai.
    #
    # ⚠️ Hai con so KIA o tren (`so_giong_khong_dat`, `so_canh_bao_tieng`) VAN
    #    GIU: chung den tu thuoc khac (ASR + WER/CER, SQUIM), chua bi nghi ngo.
    na = _outputs(db, run, pipeline.QC_AI)
    if (qc_ai_mod.khai_cho_khach()
            and na.get("qc_ai_bat") and int(na.get("so_co_phan_quyet") or 0)):
        ra["ngu_nghia"] = {
            "so_muc": int(na.get("so_muc") or 0),
            "so_co_phan_quyet": int(na.get("so_co_phan_quyet") or 0),
            "so_khong_dat": int(na.get("so_khong_dat") or 0),
        }

    # So muc DANG TIN con lai sau khi het vong sua (`sua_chua_con_lai`).
    try:
        from . import su_dung as su_dung_mod
        con = [d for d in su_dung_mod.cac_dong(db, run)
               if d.nang_luc == "sua_chua_con_lai"]
        if con:
            ra["con_lai"] = {"so_muc": int(sum(float(d.so_luong or 0)
                                              for d in con))}
    except Exception as e:                   # noqa: BLE001 - so cai hong khong
        # ⛔ VAN NUOT: mot o so tren man hinh khach khong duoc lam sap ca
        #    trang. Nhung no phai de lai vet trong nhat ky worker, neu khong
        #    thi "o `con_lai` bi thieu" la mot bao loi khong the tra ra duoc.
        log.warning("quan_sat: khong dem duoc sua_chua_con_lai (run=%s): %s",
                    getattr(run, "id", "?"), type(e).__name__)

    return ra or None
