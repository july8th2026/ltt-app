"""Pha 23 — NGHIEM THU HONG HOC: chet giua chung, huy, thu lai, mo ho.

Pha 22 chung minh duong **thanh cong**. Tep nay chung minh duong **that bai**, va
do la duong dat tien hon: mot lan chay xong dep thi khach vui; mot lan chay hong
sai cach thi khach mat tien, mat ket qua, hoac nhan mot video khong dung — va
khong ai biet cho nao da hong.

## Ba cau hoi cua ca tep

    1. Hong co TAT DINH khong?   cung mot cu ngat -> cung mot trang thai cuoi
    2. Hong co PHUC HOI duoc khong?  chay lai co di tiep tu cho da lam den
    3. Hong co TON THEM TIEN khong?  khong tinh hai lan, khong lam lai viec da dat

## Vi sao "tinh toan lai toi thieu" la mot yeu cau AN TOAN, khong phai toi uu

Mot doan tieng da sinh ra ton mot luot GPU va mot luot tra tien. Chay lai ca giai
doan de sua **mot** doan la nhan cai gia do len so doan — va te hon: mot lan sinh
lai cho ra mot ket qua KHAC, nen no doi mot khiem khuyet da biet lay mot tap
khiem khuyet chua biet.

⇒ Nen "chi lam lai phan chua xong" o day duoc kiem bang **bo dem luot goi**, chu
  khong bang mot cau khang dinh trong bao cao.

## Cai gi la THAT trong tep nay

Hang doi that, worker that, CSDL that, kho that, ffmpeg that, so cai that. Ba cua
ra ngoai (ASR, model, may sinh tieng) duoc thay bang ban gia dung chung — cung ba
cua ma `test_402` thay — vi tep nay khong kiem chat luong cua chung, no kiem
**dieu gi xay ra khi chung hong**.
"""
from __future__ import annotations

import pytest

from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests.test_402_asv_mach_doc_gia import (  # noqa: F401
    _chay_het_hang_doi, _tao_run, asr_gia, db, dich_gia, giong_gia, kho_tam)

NANG_LUC = {"api", "ffmpeg", "gpu", "voice"}


def _giai_doan(db, run, ten):
    from apps.auto_scan_video import features

    return features.giai_doan_theo_ten(db, run.id, ten)


def _trang_thai(db, run) -> dict:
    from apps.auto_scan_video import features

    return {s.stage: s.status for s in features.cac_giai_doan(db, run)}


def _chay_worker(db, *, nang_luc=None, toi_da=200) -> list[dict]:
    """Worker THAT ve mat phan loai that bai — khong phai mot ban rut gon.

    🔴 **Vi sao khong dung lai `_chay_het_hang_doi` cua `test_402`.** Ham do goi
       `jobs.fail(..., retry=False)` cho MOI ngoai le. Tien cho muc dich cua no
       (chung minh xuong song thi hanh), nhung o pha 23 no bien moi that bai
       thanh **cuoi cung** — tuc no tra loi san dung cau hoi tep nay dat ra.

    ⭐ Do la mot cai bay that: mot phep do dau tien cua pha nay ket luan "mot lan
       render hong lam ca lan chay ket thuc va khong thu lai duoc" — va do la
       phep do ve **cai harness**, khong phai ve san pham. `KetXuatError` von
       duoc `loi.py` xep vao `TAM_THOI`, tuc thu lai duoc.

    ⛔ Nen o day khong chep lai chinh sach: goi thang
       `job_runner._provider_failure_kind` va cac ham `jobs.*` ma worker that
       goi. Mot ban sao chinh sach la mot ban sao se troi.
    """
    from platform_core import jobs as jobq
    from platform_core.job_runner import JobContext, _provider_failure_kind

    nhat_ky: list[dict] = []
    for _ in range(toi_da):
        job = jobq.claim(db, worker_id="w-23", capabilities=nang_luc)
        if job is None:
            break
        db.commit()
        handler = jobq.resolve_handler(job.job_type)
        ctx = JobContext(job.id)
        ctx.job_type = job.job_type
        loi = ""
        try:
            jobq.complete(db, job, handler(dict(job.params), ctx) or {})
        except Exception as exc:            # noqa: BLE001 - worker that cung the
            loi = f"{type(exc).__name__}: {exc}"
            kind, cho = _provider_failure_kind(
                exc, provider_state=job.provider_state)
            if kind == "resource_wait":
                jobq.defer_resource(db, job, retry_after=cho,
                                    resource=job.admission_resource)
            elif kind in ("loi_nguoi_goi", "rejected"):
                jobq.fail(db, job, str(exc), retry=False)
            elif kind == "ambiguous":
                jobq.mark_ambiguous(db, job, str(exc))
            else:
                jobq.fail(db, job, str(exc))
        db.commit()
        nhat_ky.append({"job_type": job.job_type, "kind": loi})
    db.expire_all()
    return nhat_ky


def _den_han(db) -> int:
    """Keo moi job dang hen chay lai ve **bay gio**.

    ⛔ Mot bo test khong duoc `sleep`: gian cach thu lai tang dan, nen doi that
       la doi hang phut cho mot dieu da xac dinh. Day la du hanh thoi gian, va
       no chi cham `next_run_at` — khong cham so luot thu, khong cham tien.
    """
    from datetime import datetime, timezone

    from sqlalchemy import select

    from platform_core.models import Job

    n = 0
    for j in db.execute(select(Job).where(Job.status == "queued")).scalars():
        if j.next_run_at is not None:
            j.next_run_at = datetime.now(timezone.utc).replace(tzinfo=None)
            n += 1
    db.commit()
    return n


def _chay_den_yen(db, *, nang_luc=None, vong: int = 6) -> list[dict]:
    """Chay worker, keo han, chay tiep — cho toi khi hang doi thoi doi gi."""
    tat_ca: list[dict] = []
    for _ in range(vong):
        tat_ca += _chay_worker(db, nang_luc=nang_luc)
        if not _den_han(db):
            break
    return tat_ca


def _dem_job_song(db, run) -> int:
    from sqlalchemy import select

    from platform_core.models import Job

    hang = db.execute(select(Job).where(Job.plan_id == run.id)).scalars().all()
    return sum(1 for j in hang if j.status in ("queued", "running"))


# ══════════════════════════════════════════════════════════════════════════════
#  A. CHET GIUA CHUNG
# ══════════════════════════════════════════════════════════════════════════════

def test_chet_SAU_dispatch_ghi_MO_HO_va_KHONG_tinh_tien(db, kho_tam, tmp_path,
                                                        asr_gia, giong_gia,
                                                        monkeypatch):
    """🔴 Mat ket noi SAU khi da gui la truong hop dat nhat cua ca he.

    Provider **co the** da nhan, da chay, da tinh tien — ta khong biet. Coi no la
    "tu choi" roi tu dong thu lai la tra tien hai lan cho mot cau tra loi; coi no
    la "da giao" la bia ra mot ket qua khong co.

    ⇒ Ghi `mo_ho`, khong tinh tien, khong tu dong thu lai. Nguoi van hanh giai
      quyet bang `su_dung.giai_quyet_mo_ho` sau khi doi chieu voi provider.
    """
    from apps.auto_scan_video import pipeline, su_dung

    dem = {"n": 0}

    def chet(db_, *, messages, thu_tu_provider, model_theo_provider=None,
             max_tokens=None, temperature=None, on_dispatch=None,
             on_rejected=None, **kw):
        dem["n"] += 1
        if on_dispatch is not None:
            on_dispatch("ltt_llm")
        raise ConnectionResetError("mat ket noi sau khi da gui")

    monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", chet)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    tt = _trang_thai(db, run)
    assert tt[pipeline.CONTENT_PROCESS] in ("failed", "failed_terminal"), tt
    assert dem["n"] >= 1, "chua he goi toi cua model"

    mo_ho = su_dung.cac_mo_ho(db, run)
    assert mo_ho, "mot lan mat ket noi sau dispatch KHONG duoc bien mat khoi so cai"
    assert all(int(d.credit or 0) == 0 for d in mo_ho), (
        "mot luot mo ho da bi tinh tien — ta khong biet no co chay hay khong")


def test_mo_ho_KHONG_duoc_tu_dong_thu_lai(db, kho_tam, tmp_path, asr_gia,
                                          giong_gia, monkeypatch):
    """⛔ Tu dong thu lai mot luot mo ho la tu dong tra tien lan hai.

    Do bang **bo dem**: du hang doi chay den can, cua model chi duoc goi dung
    mot lan cho mot don vi.
    """
    from apps.auto_scan_video import su_dung

    dem = {"n": 0}

    def chet(db_, *, messages, on_dispatch=None, **kw):
        dem["n"] += 1
        if on_dispatch is not None:
            on_dispatch("ltt_llm")
        raise ConnectionResetError("mat ket noi sau khi da gui")

    monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", chet)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    lan_dau = dem["n"]
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)          # nhat lai lan nua

    assert dem["n"] == lan_dau, (
        f"cua model bi goi lai ({lan_dau} -> {dem['n']}) sau mot luot MO HO")
    assert su_dung.cac_mo_ho(db, run), "dong mo ho bien mat sau luot thu hai"


def test_chet_SAU_staging_TRUOC_checkpoint_TU_PHUC_HOI(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia, monkeypatch):
    """🔑 Cu ngat kho nhat: engine da ghi tep staging, worker chet truoc khi
    `promote` kip ghi dong `asv_asset`.

    Tep nam trong kho, CSDL khong biet gi ve no. Worker that con luot thu nen no
    chay lai giai doan do — va lan hai phai di den `succeeded` ma **khong** de
    lai hai asset cho cung mot giai doan: mot tep staging mo coi khong duoc bien
    thanh mot ket qua thu hai.
    """
    from apps.auto_scan_video import assets, pipeline

    that = assets.promote_va_ghi
    da_chet = {"roi": False}

    def chet_mot_lan(db_, kho, *, stage, **kw):
        if stage == pipeline.MEDIA_PREPARE and not da_chet["roi"]:
            da_chet["roi"] = True
            raise RuntimeError("worker chet truoc khi ghi checkpoint")
        return that(db_, kho, stage=stage, **kw)

    monkeypatch.setattr(assets, "promote_va_ghi", chet_mot_lan)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_den_yen(db, nang_luc=NANG_LUC)
    assert da_chet["roi"], "kich ban chua chay — khong co cu ngat nao"

    gd = _giai_doan(db, run, pipeline.MEDIA_PREPARE)
    assert gd.status == "succeeded", (gd.status, gd.error)
    khoa = (gd.outputs or {}).get("khoa_asset") or []
    assert khoa and len(khoa) == len(set(khoa)), f"asset trung: {khoa}"


# ══════════════════════════════════════════════════════════════════════════════
#  B. TAI SAN MAT HOAC HONG
# ══════════════════════════════════════════════════════════════════════════════

def test_TOAN_VEN_bat_duoc_mot_artifact_da_BI_XOA(db, kho_tam, tmp_path,
                                                   asr_gia, dich_gia, giong_gia):
    """⛔ Van tay khop **khong du** de dung lai (I10). Tep phai con song.

    Mot ban ghi noi "co roi" ve mot tep da bi don di se cho ra mot giai doan
    `succeeded` tro toi hu vo — va cho hong se la giai doan SAU no, duoi mot
    thong bao khong lien quan.
    """
    from platform_core.storage import get_storage

    from apps.auto_scan_video import assets, pipeline
    from apps.auto_scan_video.tables import ASSET_MISSING

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    gd = _giai_doan(db, run, pipeline.MEDIA_PREPARE)
    khoa = ((gd.outputs or {}).get("khoa_asset") or [])[0]
    kho = get_storage()
    asset = assets.asset_cua(db, khoa, "uA")
    assert assets.kiem_toan_ven(db, kho, asset) == "ok", "chua kiem duoc ban goc"

    kho.delete(khoa)
    assert assets.kiem_toan_ven(db, kho, asset) == ASSET_MISSING, (
        "mot artifact da bi xoa van duoc coi la toan ven")


def test_TOAN_VEN_bat_duoc_mot_artifact_da_BI_SUA(db, kho_tam, tmp_path,
                                                  asr_gia, dich_gia, giong_gia):
    """⛔ Mot tep bi sua trong y het mot tep dung. Chi bam moi phan biet."""
    import io

    from platform_core.storage import get_storage

    from apps.auto_scan_video import assets, pipeline
    from apps.auto_scan_video.tables import ASSET_CORRUPT

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    gd = _giai_doan(db, run, pipeline.TRANSCRIBE)
    khoa = ((gd.outputs or {}).get("khoa_asset") or [])[0]
    kho = get_storage()
    kho.put(khoa, io.BytesIO(b'{"doan": [], "da bi sua": true}'),
            content_type="application/json")

    asset = assets.asset_cua(db, khoa, "uA")
    assert assets.kiem_toan_ven(db, kho, asset) == ASSET_CORRUPT, (
        "mot artifact bi sua noi dung van duoc coi la toan ven")


# ⭐ **Nhan `xfail(strict=True)` da duoc GO o pha 27 — va no da bat toi mot lan.**
#    Ban va DAU TIEN cua pha 27 chi sua tang mot (cat van tay cho khop cach
#    `dat_khoa` cat), va toi da ghi B23-01 la FIXED trong bao cao truoc khi chay
#    phep kiem nay. No van do. Ly do cu cua nhan nay ke ca HAI tang, va tang hai
#    moi la tang that: khoa mang van tay cua TUNG ARTIFACT, nen khong phep so
#    khop chuoi nao tren `storage_key` tra loi duoc cau hoi "giai doan nay da
#    chay voi van tay nay chua".
#    Ban va that bo han phep so khop chuoi va hoi `AsvStage.fingerprint`.
def test_cache_cap_GIAI_DOAN_dung_lai_duoc_mot_giai_doan_khong_doi(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    """🔴 ADR-001 D8: cung dau vao, cung cau hinh, cung phien ban engine thi
    **dung lai**, ton 0 credit. Do la loi hua cua `van_tay`.

    Do that: mot giai doan vua xong, artifact con nguyen, van tay con nguyen —
    va `cache_dung_duoc` van tra ve `None`.

    ⭐ Phep kiem nay la ly do hai phep kiem ben tren da duoc viet lai. Ban dau
       chung khang dinh "cache TU CHOI mot tep da bi xoa" va chung xanh — nhung
       chung xanh vi cache tu choi **moi thu**, ke ca mot tep hoan hao. Mot phep
       kiem chi kiem chieu PHU DINH cua mot ham luon phu dinh la mot phep kiem
       khong do gi ca, va kiem dot bien chi ra dieu do: go han phep kiem toan
       ven trong `cache_dung_duoc` khong lam do mot phep kiem nao.
    """
    from platform_core.storage import get_storage

    from apps.auto_scan_video import assets, pipeline

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    gd = _giai_doan(db, run, pipeline.MEDIA_PREPARE)
    assert gd.status == "succeeded" and gd.fingerprint
    ra = assets.cache_dung_duoc(
        db, get_storage(), owner_id="uA", run_id=run.id,
        stage=pipeline.MEDIA_PREPARE, van_tay=gd.fingerprint)
    assert ra, "cache cap giai doan khong tra ve artifact nao"


# ══════════════════════════════════════════════════════════════════════════════
#  C. HUY GIUA CHUNG — o TUNG giai doan nang
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ten_giai_doan", [
    "audio_prepare", "transcribe", "edit_plan", "content_process",
    "voice_synthesis", "render",
])
def test_HUY_giua_chung_dung_ngay_va_khong_promote_gi(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia, monkeypatch,
        ten_giai_doan):
    """🔑 I13 — huy la **hop tac**: engine hoi `ctx.is_cancelled()` va dung.

    Kiem tung giai doan nang mot, vi mot vong lap quen hoi la mot giai doan van
    chay them nhieu phut sau khi khach da bam huy — va van tinh tien.
    """
    from apps.auto_scan_video import features, thi_hanh

    run = _tao_run(db, tmp_path=tmp_path)

    class CtxHuy:
        job_type = ""

        def is_cancelled(self):
            return True

        def progress(self, *a, **kw):
            return None

    ra = thi_hanh.chay_giai_doan(
        ten_giai_doan, {"run_id": run.id, "owner_id": "uA"}, CtxHuy())
    assert ra.get("ghi_chu") == "da huy", ra

    gd = _giai_doan(db, run, ten_giai_doan)
    db.refresh(gd)
    assert gd.status != "succeeded", (
        f"{ten_giai_doan} bao xong trong khi lan chay da bi huy")
    assert not (gd.outputs or {}).get("khoa_asset"), (
        f"{ten_giai_doan} van promote artifact sau khi bi huy")
    assert features.tong_da_dung(db, run) == 0, "da tinh tien cho mot lan bi huy"


def test_run_DA_HUY_khong_bao_gio_thanh_done(db, kho_tam, tmp_path, asr_gia,
                                             dich_gia, giong_gia):
    """⛔ Bat bien cung nhat cua pha nay: mot lan chay da huy **khong duoc**
    song lai vi mot job con ve muon.

    Cu ngat that: huy khi chuoi dang chay do, roi cho hang doi chay het.
    """
    from apps.auto_scan_video import features
    from apps.auto_scan_video.tables import RUN_CANCELLED

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc={"ffmpeg"})       # moi lan `media_prepare`
    features.huy_run(db, run.id, "uA")
    db.commit()

    _chay_het_hang_doi(db, nang_luc=NANG_LUC)          # cho moi job con ve
    db.expire_all()
    run = features.lay_run(db, run.id, "uA")
    assert run.status == RUN_CANCELLED, run.status
    assert _dem_job_song(db, run) == 0, "con job mo coi sau khi huy"


# ══════════════════════════════════════════════════════════════════════════════
#  D. THU LAI THUONG NGUON — va TAI DUNG phan dat tien
# ══════════════════════════════════════════════════════════════════════════════

def test_render_thu_lai_KHONG_sinh_lai_mot_doan_tieng_nao(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia, monkeypatch):
    """🔑 Menh de trung tam cua pha 23, do bang BO DEM chu khong bang loi.

    `render` truot mot lan roi duoc worker chay lai. `voice_synthesis` nam
    thuong nguon cua no nen khong duoc dong toi — bo dem luot goi may sinh tieng
    phai dung yen giua hai lan render. Neu no nhich len, moi lan sua mot loi
    render la mot hoa don TTS moi.
    """
    from apps.auto_scan_video import features, giong_noi, ket_xuat, pipeline

    dem = {"tts": 0, "render": 0}
    tts_that, render_that = giong_noi.doc_mot_doan, ket_xuat.dung_lenh

    def dem_tts(chu, **kw):
        dem["tts"] += 1
        return tts_that(chu, **kw)

    def render_hong_lan_dau(*a, **kw):
        dem["render"] += 1
        if dem["render"] == 1:
            raise ket_xuat.KetXuatError("trinh render truot mot lan")
        return render_that(*a, **kw)

    monkeypatch.setattr(giong_noi, "doc_mot_doan", dem_tts)
    monkeypatch.setattr(ket_xuat, "dung_lenh", render_hong_lan_dau)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_den_yen(db, nang_luc=NANG_LUC)

    assert dem["render"] >= 2, "worker khong he chay lai render"
    assert _trang_thai(db, run)[pipeline.RENDER] == "succeeded"
    # ⭐ Mot luot TTS cho MOT KHE DOC, va `nan_thoi_luong.gop_khe` (25/09) co the
    #    gop 2-4 doan lien ke thanh mot khe doc. ⇒ Doc so khe tu chinh bao cao cua
    #    giai doan, ⛔ dung go `3`: menh de o day la *"bo dem DUNG YEN giua hai lan
    #    render"*, ⛔ khong phai *"co dung ba doan"*.
    gd = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    so_khe = int((gd.outputs or {}).get("so_doan") or 0)
    assert 0 < so_khe <= 3, so_khe
    assert dem["tts"] == so_khe, (
        f"render chay lai da keo theo {dem['tts']} luot sinh tieng "
        f"(mong doi {so_khe} = so khe doc)")


def test_thu_lai_THUONG_NGUON_khi_run_CON_SONG_thi_ha_nguon_chay_lai(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    """⭐ Chieu nguoc lai: thu lai mot giai doan THUONG NGUON phai keo ha nguon
    chay lai — va tong tien khong duoc nhan doi.

    ⚠️ **Phai lam khi lan chay CON SONG.** `thu_lai_giai_doan` tu choi moi run da
       ket thuc (`done`/`error`/`cancelled`), va do la co y: mot run ket thuc da
       **quyet toan**, khong con cho giu, nen tieu them la tieu vao khong khi.

    🔴 He qua cua rang buoc do phai duoc noi thang, vi no la mot gioi han THAT
       cua san pham: sau khi mot lan chay hong han, khach khong "sua tiep" duoc —
       ho nop mot lan chay MOI, va lan chay moi tinh lai tu dau moi giai doan,
       ke ca demucs va ASR, vi cache artifact khoa theo `run_id`.
    """
    from apps.auto_scan_video import features, pipeline

    run = _tao_run(db, tmp_path=tmp_path, giu=100)
    # Dung truoc `voice_synthesis`: worker nay khong co nang luc `voice`.
    _chay_den_yen(db, nang_luc={"api", "ffmpeg", "gpu"})
    assert _trang_thai(db, run)[pipeline.CONTENT_PROCESS] == "succeeded"
    truoc = features.tong_da_dung(db, run)

    features.thu_lai_giai_doan(db, run.id, "uA", pipeline.EDIT_PLAN)
    db.commit()
    _chay_den_yen(db, nang_luc=NANG_LUC)

    tt = _trang_thai(db, run)
    assert all(tt[g] == "succeeded" for g in pipeline.TEN_GIAI_DOAN), tt
    sau = features.tong_da_dung(db, run)
    assert sau <= truoc * 2, (
        f"chi phi nhan len sau mot lan thu lai: {truoc} -> {sau}")


# ══════════════════════════════════════════════════════════════════════════════
#  E. HONG MOT DON VI — cac don vi da xong phai song sot
# ══════════════════════════════════════════════════════════════════════════════

def test_mot_doan_tieng_hong_KHONG_lam_sinh_lai_cac_doan_DA_XONG(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia, monkeypatch):
    """🔑 Diem chot o muc DOAN, do bang bo dem.

    Doan thu ba truot o luot dau. Worker chay lai ca giai doan — nhung hai doan
    dau da co diem chot ben vung, nen chung **khong duoc sinh lai**. Bo dem phai
    dung `3 + 1` chu khong phai `3 + 3`.

    🔴 **TAT phep gop khe o day, co y (25/09).** `nan_thoi_luong.gop_khe` gop ba
       doan cua `asr_gia` thanh MOT luot doc, va khi do loi duoc tiem o luot thu
       ba **khong bao gio xay ra** ⇒ phep kiem van XANH ma ⛔ khong do gi ca — dung
       kieu "cong thoa man duoc ma khong lam viec no sinh ra de canh" (`N-29`).
       Menh de can chot la DIEM CHOT o muc DON VI, nen phep kiem phai co **nhieu
       hon mot** don vi; gop khe co phep kiem rieng (`test_4700`).
    """
    from apps.auto_scan_video import (giong_noi, nan_thoi_luong, pipeline,
                                      su_dung)

    monkeypatch.setattr(nan_thoi_luong, "nhom_chi_so",
                        lambda khes, **kw: [[i] for i in range(len(khes))])

    that = giong_noi.doc_mot_doan
    dem = {"n": 0}

    def hong_doan_ba_lan_dau(chu, **kw):
        dem["n"] += 1
        if dem["n"] == 3:
            raise giong_noi.GiongError("may sinh tieng truot o doan nay")
        return that(chu, **kw)

    monkeypatch.setattr(giong_noi, "doc_mot_doan", hong_doan_ba_lan_dau)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_den_yen(db, nang_luc=NANG_LUC)

    assert _trang_thai(db, run)[pipeline.VOICE_SYNTHESIS] == "succeeded"
    assert dem["n"] == 4, (
        f"{dem['n']} luot sinh tieng cho 3 doan + 1 lan truot: hai doan dau da "
        "bi sinh lai du chung co diem chot")
    xong = su_dung.da_xong(db, run, stage=pipeline.VOICE_SYNTHESIS,
                           fingerprint="")
    assert len(xong) >= 3, xong


# ══════════════════════════════════════════════════════════════════════════════
#  F. MODEL TRA VE THU KHONG DUNG LUOC DO / QUA HAN
# ══════════════════════════════════════════════════════════════════════════════

def test_phan_hoi_SAI_LUOC_DO_hong_SACH_SE_chu_khong_di_tiep(db, kho_tam,
                                                             tmp_path, asr_gia,
                                                             giong_gia,
                                                             monkeypatch):
    """⛔ Mot truong thieu **phai** thanh loi ngay, khong duoc thanh `None` di
    tiep: mot `None` di tiep se lo ra o mot giai doan khac, duoi mot thong bao
    khong lien quan gi den nguyen nhan."""
    from platform_core.llm import cong_vlm

    from apps.auto_scan_video import pipeline

    def rac(db_, *, messages, on_dispatch=None, **kw):
        return cong_vlm.KetQuaChat(
            noi_dung='{"khong_phai_doan": 1}', model="x",
            su_dung=cong_vlm.SuDung(token_vao=1, token_ra=1, dang_tin=True))

    monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", rac)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    tt = _trang_thai(db, run)
    assert tt[pipeline.CONTENT_PROCESS] in ("failed", "failed_terminal"), tt
    assert tt[pipeline.VOICE_SYNTHESIS] == "pending", (
        "giai doan sau van chay tren mot ban dich khong ton tai")


def test_qua_han_TRUOC_dispatch_la_TU_CHOI_chu_khong_phai_MO_HO(
        db, kho_tam, tmp_path, asr_gia, giong_gia, monkeypatch):
    """🔑 Hai kieu hong nhin giong nhau tu ben ngoai va **khac han** ve tien.

    Chua gui di thi khong ai tinh tien -> `tu_choi`, thu lai duoc.
    Da gui roi thi khong biet -> `mo_ho`, khong tu dong thu lai.
    """
    from apps.auto_scan_video import su_dung

    def tu_choi(db_, *, messages, on_dispatch=None, on_rejected=None, **kw):
        # KHONG goi `on_dispatch`: chua he gui di.
        raise TimeoutError("provider khong bat may")

    monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", tu_choi)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    dong = list(su_dung.cac_dong(db, run))
    trang_thai = {d.trang_thai for d in dong}
    assert su_dung.TU_CHOI in trang_thai, [d.trang_thai for d in dong]
    assert not su_dung.cac_mo_ho(db, run), (
        "mot lan chua gui di bi ghi la MO HO — se bi giu lai cho nguoi doi soat "
        "mot cach vo ich")


# ══════════════════════════════════════════════════════════════════════════════
#  G. RENDER HONG / QC CHAN
# ══════════════════════════════════════════════════════════════════════════════

def test_render_hong_HET_LUOT_thi_run_ket_thuc_nhung_artifact_van_con(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia, monkeypatch):
    """⭐ Khi mot giai doan hong het ca cac luot thu, lan chay ket thuc — nhung
    nhung thu dat tien da lam xong **phai con nguyen** trong kho.

    Do la dieu kien de mot nguoi ho tro con truy duoc chuyen gi da xay ra.
    """
    from apps.auto_scan_video import features, ket_xuat, pipeline

    dem = {"n": 0}

    def luon_hong(*a, **kw):
        dem["n"] += 1
        raise ket_xuat.KetXuatError("trinh render hong")

    monkeypatch.setattr(ket_xuat, "dung_lenh", luon_hong)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_den_yen(db, nang_luc=NANG_LUC)

    assert dem["n"] >= 2, f"render chi duoc thu {dem['n']} lan"
    tt = _trang_thai(db, run)
    assert tt[pipeline.RENDER] != "succeeded"
    for g in (pipeline.TIMING_ALIGN, pipeline.COMPOSE, pipeline.VOICE_SYNTHESIS):
        assert tt[g] == "succeeded", (g, tt[g])
        assert (_giai_doan(db, run, g).outputs or {}).get("khoa_asset"), (
            f"{g} mat artifact vi mot lan render hong")
    assert _dem_job_song(db, run) == 0, "con job mo coi sau khi het luot thu"
    db.expire_all()
    assert features.lay_run(db, run.id, "uA").status == "error"


def test_QC_hong_KHONG_chan_nhung_bao_cao_QC_van_con(db, kho_tam, tmp_path,
                                                     asr_gia, dich_gia,
                                                     giong_gia, monkeypatch):
    """🔴 **DAO CHIEU 27/09/2026 — chu du an chot: QC la BO DO, ⛔ khong phai cong.**

    Ban truoc chot `gd.status in ("failed", "failed_terminal")` va
    `run.status == RUN_ERROR`. Ly le cu (*"mot cong phai chan duoc"*) dung ve
    nguyen tac nhung chi dung khi con so cua cong **dang tin** — va ba luot chay
    THAT 27/09 cho thay chung ⛔ khong (T2 SAI do chinh QC tinh nham, T18 SAI do
    phep so sanh lech nhip, T17 THAT nhung vo hai voi nguoi xem).

    ⭐ Ve thu hai cua bai cu — *"no phai de lai bang chung ve vi sao"* — VAN
       DUNG va van duoc chot o day. Do la thu duy nhat phai giu: mot bo do bi tat
       cong van la mot bo do; mot bo do bi **xoa so** thi ⛔ khong con gi.
    """
    from apps.auto_scan_video import pipeline, qc
    from apps.auto_scan_video.tables import RUN_ERROR

    that = qc.kiem

    def luon_hong(**kw):
        bao = that(**kw)
        bao["dat"] = False
        bao["muc_hong"] = ["T99"]
        bao["so_muc_hong"] = 1
        return bao

    monkeypatch.setattr(qc, "kiem", luon_hong)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    gd = _giai_doan(db, run, pipeline.QC)
    # ── Ve 1: giai doan VA lan chay ⛔ KHONG bi lam hong ──────────────────────
    assert gd.status not in ("failed", "failed_terminal"), (
        f"QC hong ma giai doan ve {gd.status!r} — QC ⛔ khong phai cong nua")
    db.expire_all()
    from apps.auto_scan_video import features
    assert features.lay_run(db, run.id, "uA").status != RUN_ERROR, (
        "QC hong ma ca lan chay ve error — khach ⛔ khong nhan duoc hang")

    # ── Ve 2: bang chung VAN con, ca artifact LAN con so ────────────────────
    out = dict(gd.outputs or {})
    assert out.get("khoa_asset"), (
        "bao cao QC ⛔ khong duoc luu — tat cong roi vut luon phat hien thi "
        "⛔ khong con bo do nao")
    assert out.get("qc_muc_hong") == ["T99"], (
        f"ma muc hong bien mat khoi outputs: {out}")
    assert out.get("qc_ky_thuat_dat") is False, out


# ══════════════════════════════════════════════════════════════════════════════
#  H. BAT BIEN TOAN CUC — chay lai nhieu lan van khong sinh them tien/job
# ══════════════════════════════════════════════════════════════════════════════

def test_chay_lai_hang_doi_BA_LAN_khong_tao_them_job_hay_tien(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    """⛔ Mot vong dieu phoi chay lai tren mot lan chay DA XONG phai la mot
    phep khong: khong job moi, khong but toan moi."""
    from sqlalchemy import select

    from platform_core.models import Job

    from apps.auto_scan_video import features

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    def _so_job():
        return len(db.execute(
            select(Job).where(Job.plan_id == run.id)).scalars().all())

    job_1, tien_1 = _so_job(), features.tong_da_dung(db, run)
    for _ in range(3):
        _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    assert (_so_job(), features.tong_da_dung(db, run)) == (job_1, tien_1)
    assert _dem_job_song(db, run) == 0


def test_giai_doan_KHONG_BAO_GIO_xong_van_dung_lai_sau_TRAN_luot_thu(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia, monkeypatch):
    """🔴 **Lo hong nay do chinh ban va cua pha 23 mo ra, va no la loai nguy
    hiem nhat: mot vong lap vo han tren mot may dang phuc vu khach.**

    `chay_giai_doan` hoi `con_luot_thu` truoc khi danh dau mot giai doan la
    `failed_retryable`. Nhung do khong phai duong duy nhat dan toi trang thai
    do: `_thu_ket_qua_job_con` cung dat no khi "job xong ma giai doan chua xong"
    — handler chet giua chung — va duong do khong hoi tran nao ca.

    ⇒ Neu cho NOP khong tu cuong che tran, moi vong dieu phoi lai sinh mot job
      moi cho cung mot giai doan, mai mai.

    ⭐ Bai hoc chung: mot bat bien phai duoc cuong che o cho **cuoi cung truoc
      khi hanh dong**, khong phai o mot trong nhung cho co the dan toi no.
    """
    from apps.auto_scan_video import features, pipeline
    from sqlalchemy import select

    from platform_core.models import Job

    that = features.danh_dau_xong

    def khong_bao_gio_xong(db_, stage, **kw):
        if stage.stage == pipeline.MEDIA_PREPARE:
            return stage          # handler tra ve nhung khong ai ghi ket qua
        return that(db_, stage, **kw)

    monkeypatch.setattr(features, "danh_dau_xong", khong_bao_gio_xong)

    run = _tao_run(db, tmp_path=tmp_path)
    _chay_den_yen(db, nang_luc=NANG_LUC, vong=12)

    job_media = db.execute(select(Job).where(
        Job.plan_id == run.id,
        Job.step_id == pipeline.MEDIA_PREPARE)).scalars().all()
    assert len(job_media) <= features.LAN_THU_GIAI_DOAN_TOI_DA, (
        f"{len(job_media)} job cho mot giai doan — tran thu lai khong duoc "
        "cuong che o cho nop")
    gd = _giai_doan(db, run, pipeline.MEDIA_PREPARE)
    assert gd.status == "failed_terminal", gd.status
    assert _dem_job_song(db, run) == 0, "con job dang cho sau khi het luot thu"
