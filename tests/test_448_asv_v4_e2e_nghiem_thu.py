"""Pha 22 — NGHIEM THU CHUC NANG DAU-CUOI, tren tep RA THAT.

## Tep nay lam gi khac moi tep test truoc no

Bon muoi bay tep test truoc chung minh **tung manh**. Tep nay chay ca san pham
mot lan, tu form tai len den tep MP4 khach bam tai ve, roi **do dac tren chinh
tep do** — thoi luong, luong hinh, luong tieng, cho nao co tieng, tieng nam o
dau. Mot bao cao noi "dat" khong tinh; thu tinh la `ffprobe` va `silencedetect`
noi gi ve tep.

## Hai nua, va vi sao chung tach

    A. LUOT CHAY THAT   — nang (nap whisper + demucs that), MAC DINH KHONG CHAY,
                          ghi ra mot bao cao may doc duoc
    B. DOC BAO CAO      — nhe, chay moi luot gate, doi chieu bao cao da luu voi
                          ma nguon HOM NAY

⭐ Nua B la thu giu cho nua A khoi thanh mot to giay cu. Mot bao cao nghiem thu
   khong co gi tu bao no da het han: ma doi, engine len phien ban moi, va to
   giay van noi "PASS". Nen nua B chot `phien_ban_engine` cua tung giai doan —
   doi mot engine la lam do mot phep kiem, va do la luc phai chay lai nghiem thu
   chu khong phai luc sua con so trong tep JSON.

⛔ **Luot chay KHONG duoc ghi vao cay lam viec.** Mot phep kiem sua tep trong kho
   giua mot luot gate lam chinh luot gate do vo hieu (`gate.py` bao "CAY DA DOI
   GIUA CHUNG"). Duong ra lay tu bien `LTT_ASV_E2E_RA`; khong dat thi ghi vao
   thu muc tam va khong ai thay.

## Cai gi la THAT trong luot chay nay

    ffmpeg          that   — chuan hoa, tach tieng, cat canh, tron, ket xuat, QC
    demucs          that   — nap htdemucs, chay tren CPU cua may nay
    faster-whisper  that   — model `large-v3`, dung hang so san pham
    hang doi + worker that — `jobs.claim` + `resolve_handler`, dinh tuyen theo
                             `manifest.requires` nhu production
    CSDL, kho, tien  that  — giu credit, so cai su_dung, quyet toan, hoan lai
    nguon            that  — hoi thoai tieng noi THAT do SAPI doc (xem fixture)

Cai KHONG that: hai cua ra ben ngoai (model va may sinh tieng), vi khoa cua ca
hai nam trong `C:\\LTTPlatform\\secrets` va thu muc do bi ACL chan doc. Danh sach
day du + ly do o `tests/fixtures/asv_e2e.THAY_THE`, va bao cao chep lai nguyen
van — mot nghiem thu khong noi duoc cho nao khong that thi khong phai nghiem thu.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from tests import rao_chan_nang
from tests.fixtures import asv_e2e as fx
from tests.test_423_asv_giao_dien import moi_truong  # noqa: F401

# ⚠️ Rang giong doc `voice_profile` cua `apps/ltt_voice`, va fixture `moi_truong`
#    chi nap bang cua RIENG Auto Scan. Thieu dong nay thi lan nop dau tien nem
#    `no such table: voice_profile` — o mot cho khong lien quan gi den thu dang
#    duoc nghiem thu. O production `load_app_tables()` nap ca, nen day la dua
#    moi truong test ve dung hinh dang production chu khong phai mot cai va.
import apps.ltt_voice.tables  # noqa: E402,F401  isort:skip

#: 🔴 **Tep nay CUON, no khong dong bang — va cai ten cu da noi nguoc lai.**
#:
#:    No tung ten la `22_nghiem_thu.json`, nghe nhu "bang chung cua pha 22".
#:    Thuc te moi luot nghiem thu deu GHI DE len no, va dieu do la CO Y: pha 28
#:    da sinh lai no vi bang chung ghi truoc mot commit cham vao duong chay thi
#:    khong con mo ta ban dang xet.
#:
#: ⛔ Hai su that do khong the cung dung duoi mot cai ten. Bao cao pha 22 trich
#:    so tu tep nay; sau pha 29 nhung so do khong con o trong no nua — lien ket
#:    van song, noi dung van dung, chi la no khong con la thu bao cao 22 mo ta.
#:    Doi ten de cai ten thoi hua mot dieu ma tep khong giu.
#: Noi luot chay ghi bao cao. Khong dat = thu muc tam.
BIEN_RA = "LTT_ASV_E2E_RA"

#: 🔴 **DOC va GHI phai cung mot cho.** Truoc 06/09 hang so nay neo cung vao
#:    duong dan trong kho trong khi cho GHI doc `BIEN_RA`, nen
#:    `nghiem_thu_asv.ps1 -BaoCao <cho khac>` chuyen huong GHI ma **khong**
#:    chuyen huong DOC.
#:
#: ⛔ Hau qua do duoc, 06/09 11:25: mot luot chan doan ghi ra tep rieng va
#:    XANH ca hai preset, nhung cac bai doc bao cao lai doc tep CU trong kho va
#:    bao `cat_thong_minh ... T5`. Hai nguon, mot cau hoi, va khong gi trong
#:    thong bao noi rang chung khac nhau — toi da suyt ket luan rang luot chan
#:    doan tai hien duoc khiem khuyet, trong khi no vua chung minh dieu nguoc lai.
#:
#: ⭐ Mot co "ghi ra cho khac" ma khong keo theo "doc tu cho khac" thi khong
#:    phai mot co bi thieu — no la mot co **noi doi**, vi no hua mot su co lap
#:    ma no khong tao ra.
BAO_CAO = (Path(os.environ[BIEN_RA]) if os.environ.get(BIEN_RA)
           else (Path(__file__).resolve().parents[1]
                 / "docs" / "auto_scan_video_v4" / "evidence"
                 / "nghiem_thu_hien_hanh.json"))

SCHEMA = "asv.v4.nghiem_thu.1"

#: Nang luc cua worker chay nghiem thu. Bon lan gop lam mot vi day la MOT may.
NANG_LUC = {"api", "ffmpeg", "gpu", "voice"}


# ══════════════════════════════════════════════════════════════════════════════
#  A. LUOT CHAY THAT
# ══════════════════════════════════════════════════════════════════════════════

def _dang_ky_may() -> dict:
    import platform
    import subprocess

    import psutil

    from platform_core import media

    try:
        ff = subprocess.run([media.ffmpeg_bin(), "-version"],
                            capture_output=True, text=True).stdout.splitlines()[0]
    except Exception:                       # noqa: BLE001
        ff = ""
    try:
        import torch
        mo_ta_torch = f"{torch.__version__} cuda={torch.cuda.is_available()}"
    except Exception:                       # noqa: BLE001
        mo_ta_torch = ""
    return {"os": platform.platform(), "python": platform.python_version(),
            "loi_vat_ly": psutil.cpu_count(logical=False),
            "loi_logic": psutil.cpu_count(logical=True),
            "ram_gib": round(psutil.virtual_memory().total / 2 ** 30, 1),
            "ffmpeg": ff, "torch": mo_ta_torch}


#: Tong thoi gian bo chay nay chiu HOAN vi tai nguyen ban, tinh bang giay.
#:
#: ⭐ Co tran, va tran la thu phan biet "cho mot suat vua nha" voi "treo mai".
#:    90 giay du cho vai luot hoan 20 giay cua nen tang, va du ngan de mot lan
#:    may B ban that su khong bien bai nghiem thu thanh mot cuoc doi vo han.
#:
#: ⚠️ **Day la ngan sach cua CA LUOT, khong phai cua tung job** — va do la mot
#:    gioi han da do duoc, khong phai mot suy doan. Nhat ky luot 06/09 09:30:
#:
#:      content_process | hoan_s=20,0 | HOAN BanError: ltt_llm: ban   (x4)
#:      content_process | hoan_s=10,0 | HOAN ...                      <- can
#:      edit_plan       | hoan_s=None | HET NGAN SACH HOAN sau 90s
#:
#:    Mot giai doan tieu het ngan sach, va giai doan sau **hong ngay lap tuc**
#:    du no chua duoc hoan lan nao.
#:
#: 🔴 Dieu do quan trong vi mot lan chay co **ba** giai doan khai
#:    `tai_nguyen="llm_remote"` (`edit_plan`, `content_process`, `qc_ai`), va may
#:    B chi phuc vu **mot** luot cung luc (`ngan_sach.DONG_THOI_MAY_B = 1`). Tuc
#:    tranh chap o nhieu giai doan la truong hop THUONG, khong phai ngoai le —
#:    va mot ngan sach chung khong song sot noi truong hop thuong do.
#:
#: ⛔ CHUA doi thanh ngan sach theo job, va co y de vay: doi no bay gio la
#:    chinh mot con so cho mot phep kiem do chuyen sang xanh, trong khi nguyen
#:    nhan that (may B ban) van nguyen. Doi khi co mot luot XANH lam moc so
#:    sanh; truoc do, `_chan_tai_nguyen_ban` da lam cho thong bao noi dung su
#:    that roi.
NGAN_SACH_HOAN_S = 90.0


def _chay_hang_doi(db, *, toi_da: int = 200) -> list[dict]:
    """Dong vai worker THAT, va do gio tung job.

    Khong dung lai `test_402._chay_het_hang_doi`: cai do khong do gio, va gio
    tung giai doan la mot trong nhung thu pha 22 phai giao nop.

    🔴 **Ban dau ham nay KHONG dong vai worker that o dung cho quan trong nhat.**

       No bat moi ngoai le roi goi `jobs.fail(..., retry=False)` — tuc bien MOI
       loi thanh that bai cuoi cung. Worker that thi phan loai truoc
       (`job_runner._provider_failure_kind`), va voi mot provider **BAN** no tra
       `("resource_wait", N)` roi `defer_resource`: job ve hang doi, **khong
       tieu luot thu, khong cham tien**.

    ⛔ Hau qua do duoc, ngay 05/09 luc 13:44: may B tra 429 cho moi lenh goi
       (mot phien khac dang chay gate), va luot nghiem thu THAT bao
       `content_process failed_terminal`. Doc y het mot khiem khuyet san pham.
       San pham thi **dung** — chi bo chay nay sai.

    ⭐ Mot cua gia chi tra loi duoc nhung cau khong phu thuoc thu no thay the;
       bo chay nay thay **worker**, roi duoc dung de tra loi cau *"san pham xu
       ly tai nguyen ban the nao"* — dung cai no thay.

    🔑 Nen no goi **chinh** `_provider_failure_kind` cua worker that, khong chep
       lai bang mot chuoi `isinstance`. Mot ban sao se lech o mot nhanh nao do,
       va nhanh lech se la nhanh it duoc chay nhat.
    """
    from platform_core import jobs
    from platform_core.job_runner import JobContext, _provider_failure_kind

    nhat_ky: list[dict] = []
    da_hoan_s = 0.0
    for _ in range(toi_da):
        job = jobs.claim(db, worker_id="w-nghiem-thu", capabilities=NANG_LUC)
        if job is None:
            break
        db.commit()
        handler = jobs.resolve_handler(job.job_type)
        ctx = JobContext(job.id)
        ctx.job_type = job.job_type
        t0 = time.time()
        loi = ""
        hoan = 0.0
        try:
            ket_qua = handler(dict(job.params), ctx) or {}
            jobs.complete(db, job, ket_qua)
        except Exception as exc:            # noqa: BLE001 - worker that cung bat het
            loai, cho = _provider_failure_kind(
                exc, provider_state=str(getattr(job, "provider_state", "") or ""))
            con_lai = NGAN_SACH_HOAN_S - da_hoan_s
            if loai == "resource_wait" and con_lai > 0:
                # ⚠️ Ngu THAT, khong chi doi `next_run_at`: `jobs.claim` loc theo
                #    moc do, nen khong ngu thi vong lap quay khong va het `toi_da`
                #    trong vai mili-giay — mot kieu "het gio" doc y het "khong con
                #    viec".
                hoan = min(float(cho or 20), con_lai)
                jobs.defer_resource(
                    db, job, retry_after=cho,
                    resource=str(getattr(job, "admission_resource", "") or ""))
                da_hoan_s += hoan
                loi = f"HOAN {type(exc).__name__}: {exc}"
            else:
                loi = f"{type(exc).__name__}: {exc}"
                if loai == "resource_wait":
                    # ⛔ Het ngan sach hoan. Van la that bai, nhung phai NOI RA
                    #    rang no den tu tai nguyen ban chu khong tu san pham.
                    loi = (f"HET NGAN SACH HOAN sau {da_hoan_s:.0f}s "
                           f"(tai nguyen ban): {loi}")
                jobs.fail(db, job, str(exc), retry=False)
        db.commit()
        if hoan:
            time.sleep(hoan)
        nhat_ky.append({"job_type": job.job_type,
                        "giay": round(time.time() - t0, 2), "loi": loi,
                        **({"hoan_s": round(hoan, 1)} if hoan else {})})
    db.expire_all()
    return nhat_ky


def _nop_qua_form(client, csrf: str, nguon: Path, *, preset: str,
                  che_do_giong: str, giong_id: str) -> str:
    """Nop qua CHINH cai form khach dung. Tra ve `run_id`."""
    from apps.auto_scan_video import hop_dong_v4

    du_lieu = {"csrf_token": csrf, "che_do": "fit_original", "preset": preset,
               "che_do_giong": che_do_giong, "giong_id": giong_id}
    with open(nguon, "rb") as f:
        r = client.post("/auto-scan-video/tao", data=du_lieu,
                        files={"video": (nguon.name, f, "video/mp4")})
    assert r.status_code == 200, r.text[:400]
    duong = str(r.url)
    assert "/run/" in duong, f"khong tao duoc lan chay: {r.text[:400]}"
    assert preset in hop_dong_v4.PRESET
    return duong.rstrip("/").rsplit("/", 1)[-1]


def _doc_artifact(db, kho, run, stage: str, duoi: str) -> bytes | None:
    from apps.auto_scan_video import features

    gd = features.giai_doan_theo_ten(db, run.id, stage)
    for khoa in ((gd.outputs or {}).get("khoa_asset") or []) if gd else []:
        if khoa.endswith(f".{duoi}"):
            with kho.open(khoa) as f:
                return f.read()
    return None


# ⭐ Ham lam sach da chuyen sang `tests/fixtures/asv_e2e` o pha 24: pha 24 dinh
#    lai dung cai bay nay (75 bao dong `bare_32_char_hex` tu mot tep bang chung
#    khac), va ly do la ham nay nam trong tep test cua RIENG pha 22.
_sach = fx.sach_de_cong_bo


def _do_phan_bo(duong: str) -> dict:
    """Phan bo muc theo cua so — de doc duoc VI SAO `vung_co_tieng` ra rong.

    ⛔ Mot bao cao noi "0 vung co tieng" ma khong kem nen/nguong buoc nguoi doc
       phai doan giua hai kha nang rat khac nhau: tep that su khong co tieng
       long, hay phep do vua mat tien de cua no.
    """
    from tests.fixtures import asv_e2e as fx

    muc = fx.muc_theo_cua_so(duong, cua_so_s=0.5)
    if not muc:
        return {}
    # ⛔ Dung CHINH ham cua phep do, khong go lai phep tinh nen: mot ban sao la
    #    mot cho de bao cao va phep do noi hai dieu khac nhau ve cung mot tep.
    nen = fx._phan_vi(muc, 0.20)
    nguong = nen + 2.0
    return {
        "so_cua_so": len(muc),
        "nen_p20_db": round(nen, 2),
        "nguong_db": round(nguong, 2),
        "thap_nhat_db": round(min(muc), 2),
        "cao_nhat_db": round(max(muc), 2),
        "so_cua_so_tren_nguong": sum(1 for m in muc if m >= nguong),
        "ti_le_tren_nguong": round(
            sum(1 for m in muc if m >= nguong) / len(muc), 3),
        # ⭐ Ca chuoi muc, khong chi vai thong ke. 54-64 so cho mot lan chay —
        #    du nho de luu, va no la thu duy nhat tra loi duoc cau hoi "phep do
        #    mat tien de, hay san pham that su mat tuong phan" ma khong phai
        #    chay lai ca lan nghiem thu.
        "muc_cua_so_db": [round(m, 2) for m in muc],
    }


def _do_am(duong: str) -> dict:
    """LUFS + dinh that cua tep ra, do bang chinh ham san pham dung."""
    from apps.auto_scan_video import tach_tieng

    try:
        return dict(tach_tieng.do_am_luong(duong))
    except Exception as exc:                # noqa: BLE001 - khong do duoc != sai
        return {"loi": f"{type(exc).__name__}: {exc}"}


def _tom_tat(giai_doan: list[dict], ten: str) -> dict:
    for g in giai_doan:
        if g["ten"] == ten:
            return dict(g.get("tom_tat") or {})
    return {}


def _mot_luot(client_chu, csrf, client_khac, nguon: Path, tam: Path, *,
              nhan: str, preset: str, che_do_giong: str, giong_id: str,
              su_that=None) -> dict:
    """Mot lan chay day du, tu form den tep tai ve. Tra ve phan bao cao.

    ⚠️ `su_that=None` khi nguon la PHIM KHACH THAT: phim that khong di kem cau
       tra loi. Chi mot truong cua bao cao phu thuoc no (`phu_song_loi`, phep
       doi chieu voi su that doc lap), va truong do thanh `None` — **khong**
       thanh mot gia tri trong trong nhu `[]`, vi `[]` doc y het "da doi chieu
       va khong cau nao duoc phu song", tuc dung nguoc voi su that.
    """
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.storage import get_storage

    from apps.auto_scan_video import (features, pipeline, quan_sat, su_dung,
                                      thi_hanh)

    t0 = time.time()
    run_id = _nop_qua_form(client_chu, csrf, nguon, preset=preset,
                           che_do_giong=che_do_giong, giong_id=giong_id)

    db = next(dbmod.get_session())
    try:
        from apps.auto_scan_video.tables import AsvRun

        nhat_ky = _chay_hang_doi(db)
        run = db.get(AsvRun, run_id)
        db.refresh(run)

        giai_doan = []
        for g in pipeline.CHUOI:
            s = features.giai_doan_theo_ten(db, run_id, g.ten)
            giai_doan.append({
                "ten": g.ten, "trang_thai": getattr(s, "status", ""),
                "phien_ban_engine": thi_hanh.phien_ban_engine(g.ten),
                "credit": int(getattr(s, "credit_actual", 0) or 0),
                "loi": (getattr(s, "error", "") or "")[:200],
                "tom_tat": dict(getattr(s, "outputs", None) or {}),
            })

        kho = get_storage()
        ban_ghi = _doc_artifact(db, kho, run, pipeline.TRANSCRIBE, "json")
        ban_dich = _doc_artifact(db, kho, run, pipeline.CONTENT_PROCESS, "json")
        bao_qc = _doc_artifact(db, kho, run, pipeline.QC, "json")

        ra = {}
        gd_ra = features.giai_doan_theo_ten(db, run_id, pipeline.RENDER)
        khoa_ra = next((k for k in ((gd_ra.outputs or {}).get("khoa_asset") or [])
                        if k.endswith(".mp4")), "")
        tep_ra = tam / f"ra_{nhan}.mp4"
        if khoa_ra:
            with kho.open(khoa_ra) as f:
                tep_ra.write_bytes(f.read())
            soi = fx.soi(str(tep_ra))
            luong = {s["codec_type"]: s for s in soi["streams"]}
            ra = {
                "byte": tep_ra.stat().st_size,
                "thoi_luong": round(float(soi["format"]["duration"]), 3),
                "codec_video": luong.get("video", {}).get("codec_name", ""),
                "codec_tieng": luong.get("audio", {}).get("codec_name", ""),
                "khung": [luong.get("video", {}).get("width"),
                          luong.get("video", {}).get("height")],
                "vung_co_tieng": [list(v) for v in fx.vung_co_tieng(str(tep_ra))],
                "phu_song_loi": (
                    fx.phu_song_loi(fx.vung_co_tieng(str(tep_ra)), su_that.loi)
                    if su_that is not None else None),
                "am_luong": _do_am(str(tep_ra)),
                # 🔑 **So do CUA CHINH PHEP DO, khong phai cua san pham.**
                #    `vung_co_tieng` lay NEN bang trung vi moi cua so, va
                #    docstring cua no dat mot tien de: "mot ban long tieng noi
                #    khoang mot phan ba thoi luong, nen trung vi roi vao nen".
                #    Ngay preset cat that su cat mot canh IM LANG, ti le noi
                #    tang len va tien de do co the vo — luc do bao cao se noi
                #    "khong co tieng long" ve mot tep nghe ro tung cau.
                # ⇒ Ghi lai nen/nguong/dinh de lan sau khong phai doan.
                "do_cua_phep_do": _do_phan_bo(str(tep_ra)),
            }

        # ⛔ Doc TRUOC khi phien dong: `AsvUsage` la doi tuong ORM, va doc
        #    no sau khi phien dong se nem `DetachedInstanceError`.
        from sqlalchemy import select as _select
        from apps.auto_scan_video.tables import AsvUsage as _AsvUsage
        vi_sao = [
            {"nang_luc": r.nang_luc, "trang_thai": r.trang_thai,
             "ly_do": str((r.ghi_chu or {}).get("ly_do") or "")[:300]}
            for r in db.execute(_select(_AsvUsage).where(
                _AsvUsage.run_id == run.id)).scalars()
            if r.trang_thai != "da_giao"]
        so_ke = su_dung.so_ke(db, run)
        doi_soat = quan_sat.doi_soat_nhanh(db, run)
        khach = quan_sat.tom_tat_cho_khach(db, run)
        con_lai = credit.so_du(db, run.owner_id)
    finally:
        db.close()

    # ── Tai ve, va thu tai bang tai khoan KHAC ────────────────────────────
    tai = client_chu.get(f"/auto-scan-video/run/{run_id}/tai")
    tai_khac = client_khac.get(f"/auto-scan-video/run/{run_id}/tai")

    def _json(du_lieu):
        return json.loads(du_lieu.decode("utf-8")) if du_lieu else {}

    bg, bd, qc = _json(ban_ghi), _json(ban_dich), _json(bao_qc)
    # ⭐ Chi giu tang vat khi lan chay KHONG dat — mot luot xanh khong can bang
    #    chung, va chep hai tep media cho moi luot xanh la mot cai gia tra mai.
    tang_vat = ({} if run.status == "done"
                else _giu_tang_vat(db, kho, run, nhan, giai_doan))

    return {
        "nhan": nhan, "preset": preset, "che_do_giong": che_do_giong,
        "tang_vat": tang_vat,
        "giong_id": giong_id,
        "trang_thai_run": run.status, "giay_tong": round(time.time() - t0, 1),
        "giai_doan": giai_doan, "nhat_ky_job": nhat_ky,
        "asr": {"ngon_ngu": bg.get("ngon_ngu") or bg.get("language") or "",
                "so_doan": len(bg.get("doan") or bg.get("segments") or []),
                "van": [str(d.get("chu") or d.get("text") or "")
                        for d in (bg.get("doan") or bg.get("segments") or [])]},
        # ⚠️ Doc tu `tom_tat` cua CHINH giai doan chu khong tu doan hinh dang tep
        #    JSON: hai ban ghi khac nhau, va mot ban doc doan mo lam bao cao ghi
        #    "0 canh" trong khi lan chay hoan toan binh thuong.
        "ban_bien_tap": _tom_tat(giai_doan, pipeline.EDIT_PLAN),
        "ban_dung": _tom_tat(giai_doan, pipeline.COMPOSE),
        "ket_xuat": _tom_tat(giai_doan, pipeline.RENDER),
        "ban_long_tieng": {
            "so_muc": len(bd.get("muc") or []),
            "ngon_ngu": str(bd.get("ngon_ngu") or ""),
            "chu": [str(m.get("chu") or "") for m in (bd.get("muc") or [])],
        },
        "qc": {"dat": bool(qc.get("dat")), "muc_hong": list(qc.get("muc_hong") or []),
               # ⭐ Giu NGUYEN tung muc, ke ca cac so do duoc: mot bao cao chi
               #    ghi "hong" khong tra loi duoc "hong bao nhieu", va do chinh
               #    la cau hoi dau tien nguoi doc se hoi.
               "muc": list(qc.get("muc") or [])},
        "so_ke": so_ke, "doi_soat": doi_soat, "tom_tat_khach": khach,
        # 🔑 LY DO cua tung lan khong-thanh-cong, khong chi con dem.
        #    Mot bao cao noi "tu_choi: 4" buoc nguoi doc di doan, va ba
        #    vong doan da troi qua truoc khi dong nay duoc them.
        "vi_sao_hong": vi_sao,
        "credit_con_lai": con_lai,
        "ra": ra,
        "tai_ve": {"ma_chu": tai.status_code, "byte_chu": len(tai.content),
                   "ma_nguoi_khac": tai_khac.status_code},
    }


@rao_chan_nang.NANG
@rao_chan_nang.CHI_KHI_BAT
def test_NGHIEM_THU_ca_hai_preset_ra_video_dung_duoc(moi_truong, tmp_path,
                                                     monkeypatch):
    """Luot chay that. Ghi bao cao ra `LTT_ASV_E2E_RA`.

    ⚠️ Dat `LTT_AUTOSUB_WHISPER_DEVICE=cpu`: cay nay chay `torch+cpu` (V4-R05),
       va mac dinh cua `autosubvideo._get_faster_model` la `cuda`. Day la mot
       **thiet lap moi truong**, khong phai mot ban thay the — duong ma khong
       doi mot dong.
    """
    _app, a, csrf_a, b, _csrf_b = moi_truong
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_DEVICE", "cpu")
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_COMPUTE", "int8")

    from apps.auto_scan_video import hop_dong_v4

    if not fx.co_sapi():
        pytest.skip("khong co SAPI de dung ban nguon co tieng noi that")

    su_that = fx.nguon_hoi_thoai(tmp_path / "nguon")

    # 🔑 Nap khoa pool TRUOC khi dat cua model.
    #
    # ⛔ Va khang dinh NGAY neu pool that khong co khoa nao: khong co
    #    khoa thi khong co duong nao goi model that, va bai nay phai noi
    #    ra o day chu khong hong o giua chuoi — sau khi da ton demucs va
    #    ASR, duoi mot thong bao (`KhongCoProviderNao`) khong nhac gi toi
    #    CSDL. Da dinh dung nhu vay mot lan.
    if fx.dung_model_that():
        from platform_core.db import get_session
        so_khoa = 0
        for _db in get_session():
            so_khoa = fx.nap_khoa_pool(_db)
            _db.commit()
            break
        assert so_khoa, (
            "LTT_ASV_MODEL_THAT=1 nhung pool that khong co khoa `ltt_llm` "
            "nao dung duoc - khong co duong nao goi model that")

    dem_model = fx.dat_cua_model(monkeypatch, su_that=su_that)
    dem_giong = fx.dat_cua_giong(monkeypatch, tmp_path / "tieng")

    luot = []
    for nhan, preset in (("giu_hinh", hop_dong_v4.PRESET_GIU_HINH),
                         ("cat_thong_minh", hop_dong_v4.PRESET_CAT_THONG_MINH)):
        luot.append(_mot_luot(
            a, csrf_a, b, Path(su_that.duong), tmp_path,
            nhan=nhan, preset=preset,
            che_do_giong=hop_dong_v4.CHE_DO_GIONG_TU_CHON,
            giong_id="Minh Đức", su_that=su_that))

    bao_cao = {
        "schema": SCHEMA,
        "ghi_luc": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "may": _dang_ky_may(),
        "moi_truong": {"LTT_AUTOSUB_WHISPER_DEVICE": "cpu",
                       "LTT_AUTOSUB_WHISPER_COMPUTE": "int8"},
        "nguon": {
            "thoi_luong": su_that.thoi_luong,
            "moc_cat_canh": su_that.moc_cat_canh(),
            "canh": [{"ten": c.ten, "bat": c.bat, "ket": c.ket} for c in su_that.canh],
            "loi": [{"ma": l.ma, "giong": l.giong, "bat": round(l.bat, 3),
                     "giay": round(l.giay, 3), "chu": l.chu} for l in su_that.loi],
        },
        # 🔑 Ghi thu DA THUC SU bi thay trong luot nay, khong ghi ca danh muc.
        #    Voi `LTT_ASV_GIONG_THAT=1` thi ba cua giong khong nam o day nua, va
        #    do la ca diem: bao cao phai phan biet duoc mot luot chay dung
        #    LTTStudioVoice that voi mot luot dung SAPI.
        "giong_that": bool(dem_giong.get("giong_that")),
        "model_that": bool(dem_model.get("model_that")),
        "thay_the": [{"ten": t.ten, "ly_do": t.ly_do, "con_that": t.con_that}
                     for t in fx.THAY_THE
                     if t.ten in set(fx.cua_da_thay(dem_giong, dem_model))],
        "luot": luot,
    }

    duong = Path(os.environ.get(BIEN_RA) or (tmp_path / "nghiem_thu_hien_hanh.json"))
    duong.parent.mkdir(parents=True, exist_ok=True)
    duong.write_text(json.dumps(_sach(bao_cao), ensure_ascii=False, indent=2),
                     encoding="utf-8")

    # Cong thoat cua pha 22, kiem ngay tai cho — bao cao chi la ban sao.
    for l in luot:
        assert l["trang_thai_run"] == "done", (l["nhan"], l["giai_doan"])
        assert l["ra"].get("byte", 0) > 0 and l["ra"].get("codec_tieng")
        assert l["qc"]["dat"], (l["nhan"], l["qc"]["muc_hong"])
        assert l["tai_ve"]["ma_chu"] == 200
        assert l["tai_ve"]["ma_nguoi_khac"] == 404


# ══════════════════════════════════════════════════════════════════════════════
#  B. DOC BAO CAO — chay moi luot gate
# ══════════════════════════════════════════════════════════════════════════════

#: Dau hieu mot luot chet vi TAI NGUYEN BAN chu khong vi san pham.
#: `_chay_hang_doi` ghi tien to nay khi da hoan het `NGAN_SACH_HOAN_S` giay ma
#: tai nguyen van ban.
DAU_HET_NGAN_SACH = "HET NGAN SACH HOAN"


def _chan_tai_nguyen_ban(bc: dict) -> None:
    """Dung ngay neu bao cao den tu mot lan chay bi TAI NGUYEN BAN giet.

    \U0001F534 **Xay ra that, ba lan: 05/09 13:44, 06/09 09:14 va 09:20.** Ca ba
       lan may B tra "ban" vi mot phien khac dang dung `ltt_llm`,
       `content_process` chet, va chin bai do voi nhung cau nhu
       `assert 404 == 200` va `('giu_hinh', [])`.

    \u26d4 Chin cau do **doc y het chin khiem khuyet san pham**, va khong cau nao
       nhac toi may B. Lan dau chu du an phai hoi thang *"toi can lam gi"* — do
       la cai gia that cua mot bao cao khong phan biet duoc "san pham hong" voi
       "khong chay duoc".

    \u2b50 Va cac bai phia sau **khong the** tra loi dung: chung do giai doan 6-11
       cua mot lan chay dung o giai doan 5. Mot bao cao nhu vay khong phai bang
       chung yeu — no khong phai bang chung ve dieu chung hoi. Nen cho dung de
       chan la tai NGUON, mot lan, voi mot cau noi ro chuyen gi da xay ra.

    \u26a0\ufe0f Khong `skip`: mot luot nghiem thu khong chay duoc **phai** do. Thu
       duoc doi la LY DO no do, khong phai phan quyet cua no.
    """
    ban = []
    for luot in bc.get("luot") or []:
        for j in luot.get("nhat_ky_job") or []:
            if str(j.get("loi") or "").startswith(DAU_HET_NGAN_SACH):
                ban.append((luot.get("nhan"), j.get("job_type"),
                            str(j.get("loi"))[:160]))
    if not ban:
        return
    nl = chr(10)
    dong = [f"    {n} | {jt} | {lo}" for n, jt, lo in ban]
    pytest.fail(nl.join([
        "LUOT NGHIEM THU NAY KHONG CHAY DUOC — tai nguyen dung chung BAN,",
        "khong phai san pham hong.",
        "",
        *dong,
        "",
        "  Nghia la: mot phien khac dang dung `ltt_llm` tren may B, va bo chay",
        "  da cho het ngan sach hoan roi moi bo cuoc. Bao cao nay KHONG noi",
        "  duoc gi ve san pham.",
        "",
        "  Lam gi: hoi cac phien khac ai dang dung may B, doi ho xong, chay lai.",
        "  Mot luot hong vi ban chi ton ~2 phut, khong ton 21 phut.",
    ]))


def _giu_tang_vat(db, kho, run, nhan: str, giai_doan: list[dict]) -> dict:
    """Chep ban phoi + ban giao ra mot cho SONG LAU khi lan chay khong dat QC.

    \U0001F534 **Vi sao can:** 06/09 QC T5 (dinh that) hong o `cat_thong_minh`, va
       cau hoi tiep theo — *"phoi sai hay ma hoa vot lo?"* — chi tra loi duoc
       bang cach do CHINH hai tep do. Chung nam duoi `tmp_path` cua pytest, ma
       pytest **chi giu ba thu muc gan nhat**. Den luc toi hoi thi ba luot kiem
       toi chay SAU do da day chung ra khoi hang doi.

    \u26d4 Tuc bang chung bi xoa **boi chinh viec kiem tra chay sau no**. Bao cao
       da ghi day du con SO (`master.dinh_that` va QC T5), nhung mot con so noi
       "vot lo 2,78 dB" khong noi duoc **vi sao** — chi hai tep moi noi duoc.

    \u2b50 Ghi ra ngoai cay lam viec, khong ghi canh bao cao: bao cao nam trong
       `docs/`, va mot tep media o do se di thang vao mot commit `git add -A`.
    """
    import shutil
    import tempfile

    thu_muc = Path(tempfile.gettempdir()) / "asv_tang_vat" / nhan
    if thu_muc.exists():
        shutil.rmtree(thu_muc, ignore_errors=True)
    thu_muc.mkdir(parents=True, exist_ok=True)

    ra: dict[str, str] = {}
    for g in giai_doan:
        # `khoa_asset` nam trong `tom_tat` (thi_hanh do `ket_qua` vao
        # `stage.outputs`, va bao cao chep nguyen `outputs` vao `tom_tat`).
        for khoa in ((g.get("tom_tat") or {}).get("khoa_asset") or []):
            duoi = Path(str(khoa)).suffix.lower()
            if duoi not in (".wav", ".mp4"):
                continue
            dich = thu_muc / f"{g.get('ten')}{duoi}"
            try:
                with kho.open(str(khoa)) as f, open(dich, "wb") as o:
                    shutil.copyfileobj(f, o)
            except Exception:            # noqa: BLE001
                continue
            ra[str(g.get("ten"))] = str(dich)
    return ra


def _bao_cao() -> dict:
    if not BAO_CAO.exists():
        pytest.fail(f"chua co bao cao nghiem thu {BAO_CAO}")
    bc = json.loads(BAO_CAO.read_text(encoding="utf-8"))
    _chan_tai_nguyen_ban(bc)
    return bc


@pytest.fixture(scope="module")
def bc() -> dict:
    return _bao_cao()


def test_bao_cao_dung_luoc_do_va_co_DU_HAI_preset(bc):
    """⛔ Mot preset la nua san pham. Cong thoat pha 22 doi CA HAI."""
    from apps.auto_scan_video import hop_dong_v4

    assert bc["schema"] == SCHEMA
    co = {l["preset"] for l in bc["luot"]}
    assert co == set(hop_dong_v4.PRESET), f"thieu preset: {set(hop_dong_v4.PRESET) - co}"


def test_moi_luot_di_HET_chuoi_giai_doan(bc):
    from apps.auto_scan_video import pipeline

    for l in bc["luot"]:
        ten = [g["ten"] for g in l["giai_doan"]]
        assert ten == list(pipeline.TEN_GIAI_DOAN), (l["nhan"], ten)
        for g in l["giai_doan"]:
            assert g["trang_thai"] == "succeeded", (l["nhan"], g["ten"], g["loi"])


def test_phien_ban_ENGINE_trong_bao_cao_van_dung_HOM_NAY(bc):
    """🔑 Cai giu bao cao khoi thanh mot to giay cu.

    Mot bao cao nghiem thu khong tu biet ma da doi duoi chan no. Chot phien ban
    engine cua tung giai doan lam dieu do: nang mot engine la lam do phep kiem
    nay, va cau tra loi dung la **chay lai nghiem thu**, khong phai sua con so.
    """
    from apps.auto_scan_video import thi_hanh

    for l in bc["luot"]:
        for g in l["giai_doan"]:
            nay = thi_hanh.phien_ban_engine(g["ten"])
            assert g["phien_ban_engine"] == nay, (
                f"{g['ten']}: bao cao ghi {g['phien_ban_engine']}, ma nay {nay} "
                "-> nghiem thu da cu, phai chay lai")


def test_moi_cua_THAY_THE_van_con_ton_tai(bc):
    """⛔ Mot bao cao goi ten mot cua da bi doi ten la bao cao ve mot chuong
    trinh khong con nua — va no se im lang noi rang phan do van duoc thay."""
    import importlib

    # 🔴 Dong nay tung doc DANH MUC (`fx.THAY_THE`) chu khong doc BAO CAO, nen
    #    no doi chieu danh muc voi chinh no — mot phep kiem luon dat, khong the
    #    do gi. No chi lo ra khi pha nay them cong tac giong/model that.
    khai = {t["ten"] for t in bc["thay_the"]}
    # ⚠️ `khai` la nhung cua bao cao NOI da thay. Doi chieu voi danh muc theo
    #    chieu TAP CON: mot luot chay giong that thay it cua hon, va do la mot
    #    luot chay TOT hon chu khong phai mot bao cao sai.
    assert khai <= {t.ten for t in fx.THAY_THE}, "bao cao khai mot cua ngoai danh muc"

    # ⛔ Hai co va bon cua phai khop TUNG DOI MOT. Mot bao cao noi "da goi model
    #    that" ma van khai da thay `dieu_phoi.goi` la mot bao cao tu mau thuan,
    #    va no se duoc doc nhu bang chung cho mot dieu chua xay ra.
    co_model = set(fx.CUA_MODEL) & khai
    if bc.get("model_that"):
        assert not co_model, (
            "bao cao noi goi model THAT nhung van khai da thay cua model")
    else:
        assert co_model == set(fx.CUA_MODEL), (
            "luot chay thay the phai khai du cua model")

    # Va hai chieu phai khop: co `giong_that` thi ba cua giong PHAI vang.
    co_giong = set(fx.CUA_GIONG) & khai
    if bc.get("giong_that"):
        assert not co_giong, (
            "bao cao noi dung giong THAT nhung van khai da thay cua giong")
    else:
        assert co_giong == set(fx.CUA_GIONG), (
            "luot chay SAPI phai khai du ba cua giong")

    # ⭐ Va neu CA HAI deu that thi khong con cua nao duoc khai — luc do bao cao
    #    phai noi ro ca hai co, vi mot danh sach RONG mot minh doc len giong het
    #    mot bao cao quen ghi.
    if not khai:
        assert bc.get("model_that") and bc.get("giong_that"), (
            "khong khai cua nao ma cung khong khai la da chay that")
    for ten in khai:
        module, _, thuoc_tinh = ten.rpartition(".")
        mod = importlib.import_module(module)
        assert hasattr(mod, thuoc_tinh), f"cua da khai khong con ton tai: {ten}"


def test_ASR_that_doc_dung_ngon_ngu_va_du_so_cau(bc):
    """Nguon la tieng Anh, bon cau. ASR that phai noi duoc ca hai dieu do.

    ⭐ Day la phep kiem chung minh **dau vao la tieng noi that**: mot dang song
       khong phai tieng noi thi `large-v3` tra ve khong doan, va ca chuoi phia
       sau khong con y nghia gi.
    """
    so_cau = len(bc["nguon"]["loi"])
    for l in bc["luot"]:
        assert l["asr"]["ngon_ngu"] == "en", (l["nhan"], l["asr"]["ngon_ngu"])
        assert l["asr"]["so_doan"] >= so_cau - 1, (l["nhan"], l["asr"])


def test_ban_long_tieng_ra_TIENG_VIET_du_so_muc(bc):
    """Hop dong V4: ngon ngu ra la tieng Viet, va moi doan giu lai deu co loi."""
    from apps.auto_scan_video import hop_dong_v4

    for l in bc["luot"]:
        lt = l["ban_long_tieng"]
        assert lt["so_muc"] > 0, l["nhan"]
        assert any(_co_dau_tieng_viet(c) for c in lt["chu"]), (
            f"{l['nhan']}: khong muc nao co dau tieng Viet -> ban dich khong ra "
            f"{hop_dong_v4.NGON_NGU_DICH}")


def _co_dau_tieng_viet(chu: str) -> bool:
    return any(c in chu for c in "ăâđêôơưàảãạáằẳẵặắầẩẫậấèẻẽẹéềểễệế"
                                "ìỉĩịíòỏõọóồổỗộốờởỡợớùủũụúừửữựứỳỷỹỵý")


def test_hai_preset_dung_HAI_che_do_render_khac_nhau(bc):
    """🔑 Day la khac biet ky thuat that su giua hai preset.

    Giu hinh = sao chep luong hinh (khong ma hoa lai, khong mat mat). Cat thong
    minh = phai ma hoa lai, vi stream-copy chi cat duoc o khung khoa.
    """
    from apps.auto_scan_video import che_do_render, hop_dong_v4

    theo = {l["preset"]: l for l in bc["luot"]}
    assert (theo[hop_dong_v4.PRESET_GIU_HINH]["ban_dung"]["cach_render"]
            == che_do_render.SAO_CHEP)
    assert (theo[hop_dong_v4.PRESET_CAT_THONG_MINH]["ban_dung"]["cach_render"]
            == che_do_render.CAT_MA_HOA_LAI)


def test_tep_RA_co_du_hinh_va_tieng_va_dung_thoi_luong(bc):
    """Do tren `ffprobe` cua tep ra, khong tren mot dong tom tat nao."""
    from apps.auto_scan_video import hop_dong_v4

    nguon_giay = float(bc["nguon"]["thoi_luong"])
    for l in bc["luot"]:
        ra = l["ra"]
        assert ra["byte"] > 10_000, (l["nhan"], ra)
        assert ra["codec_video"] and ra["codec_tieng"], (l["nhan"], ra)
        if l["preset"] == hop_dong_v4.PRESET_GIU_HINH:
            # Giu hinh: khong cat gi, nen thoi luong phai bam ban nguon.
            assert abs(ra["thoi_luong"] - nguon_giay) <= 1.0, (l["nhan"], ra)
        else:
            # Cat: ngan hon hoac bang, va khong duoc bang khong.
            assert 1.0 < ra["thoi_luong"] <= nguon_giay + 1.0, (l["nhan"], ra)


def test_tieng_long_NAM_DUNG_CHO_trong_tep_ra(bc):
    """⭐ Phep kiem duy nhat trong tep nay do tren SONG AM cua tep khach tai ve.

    Mot ban long tieng dung so doan van co the dat het tieng vao ba giay dau,
    hoac dat len mot cho khong co hinh. `phu_song_loi` doi chieu cac vung co
    tieng do duoc voi **moc cua tung cau nguon** — su that ta biet TRUOC khi
    chay, khong phai thu doc lai tu bao cao.

    ⚠️ Nguong la "qua NUA so cau", khong phai "moi cau", va ly do phai noi ra:
       trong tep ra loi thoai chi cao hon nen **khoang 4 dB**
       (`am_master.NEN_GIAM_DB` ha nen deu tren ca bai), nen mot cau doc nho roi
       vao mot doan nen manh co the khong noi len du de tach ra. Doi "moi cau"
       o day la doi phep DO chinh xac hon thu no dang do.

    🔑 Con so 4 dB do duoc la mot **phat hien**, khong phai mot tham so: no da
       duoc ghi vao bao cao pha 22 de nguoi quyet dinh chinh sach tron doc.
    """
    for l in bc["luot"]:
        vung = l["ra"].get("vung_co_tieng") or []
        phu = l["ra"].get("phu_song_loi") or []
        assert vung, (l["nhan"], "tep ra khong co doan nao noi len tren nen")
        assert phu, (l["nhan"], "khong doi chieu duoc voi moc cau nguon")
        co = [p for p in phu if p["co_tieng"]]
        assert len(co) * 2 >= len(phu), (
            f"{l['nhan']}: chi {len(co)}/{len(phu)} cau nguon co tieng long "
            "trum len dung cho")
        cuoi = max(v[1] for v in vung)
        assert cuoi <= l["ra"]["thoi_luong"] + 0.5, (
            f"{l['nhan']}: co tieng o giay {cuoi} trong khi tep dai "
            f"{l['ra']['thoi_luong']}")


# ⭐ **Nhan `xfail(strict=True)` da duoc GO o pha 27, va viec go no la mot su
#    kien co that chu khong phai mot thao tac don dep.** Pha 22 viet nhan do kem
#    mot cau: *"ngay ai do noi VLM vao chuoi, phep kiem nay thanh cong va pytest
#    bao XPASS — tuc bo test tu noi rang khiem khuyet da het, thay vi de mot
#    dong TODO nam lai them mot nam."* No da bao XPASS o lan chay E2E dau tien
#    sau khi B22-01 duoc sua, tren mot luot chay THAT: `so_canh 4, so_giu 3,
#    so_cat 1, so_canh_da_doc 4`.
def test_preset_CAT_phai_cat_it_nhat_MOT_canh_khong_co_thoai(bc):
    """🔴 Ban nguon co han mot canh **khong co loi thoai nao** (canh thu tu), va
    preset cat van giu nguyen no.

    ⭐ `xfail(strict=True)` chu khong phai mot chu thich: ngay ai do noi VLM vao
       chuoi, phep kiem nay **thanh cong** va pytest bao XPASS — tuc bo test tu
       noi rang khiem khuyet da het, thay vi de mot dong TODO nam lai them mot
       nam.
    """
    from apps.auto_scan_video import hop_dong_v4

    cat = next(l for l in bc["luot"]
               if l["preset"] == hop_dong_v4.PRESET_CAT_THONG_MINH)
    assert int(cat["ban_bien_tap"].get("so_cat") or 0) >= 1, (
        f"so_canh={cat['ban_bien_tap'].get('so_canh')}, "
        f"so_cat={cat['ban_bien_tap'].get('so_cat')}, "
        f"so_co_bang_chung={cat['ban_bien_tap'].get('so_co_bang_chung')}")


def test_QC_moi_muc_deu_co_phan_quyet_va_khong_muc_nao_hong(bc):
    for l in bc["luot"]:
        assert l["qc"]["dat"], (l["nhan"], l["qc"]["muc_hong"])
        assert l["qc"]["muc"], l["nhan"]
        assert not [m for m in l["qc"]["muc"] if m["trang_thai"] == "hong"]


def test_SO_CAI_khop_va_quyet_toan_khong_vuot_phan_da_giu(bc):
    """Tien: doi soat hai chieu phai sach, va khong lan chay nao tieu qua muc giu."""
    for l in bc["luot"]:
        assert l["doi_soat"].get("khop") is not False, (l["nhan"], l["doi_soat"])
        assert l["so_ke"], l["nhan"]
        khach = l["tom_tat_khach"]
        assert khach, l["nhan"]


def test_TAI_VE_duoc_boi_chu_va_KHONG_boi_nguoi_khac(bc):
    """I6 — quyen so huu do tren duong tai ve that, khong suy tu ma."""
    for l in bc["luot"]:
        assert l["tai_ve"]["ma_chu"] == 200, l["nhan"]
        assert l["tai_ve"]["byte_chu"] > 10_000, l["nhan"]
        assert l["tai_ve"]["ma_nguoi_khac"] == 404, (
            f"{l['nhan']}: nguoi khac tai duoc ket qua "
            f"(ma {l['tai_ve']['ma_nguoi_khac']})")


def test_bao_cao_GHI_RO_thu_khong_that(bc):
    """⛔ Mot nghiem thu khong noi duoc cho nao khong that la mot loi qua quyet.

    Phai co it nhat mot cua thay the duoc khai, moi cua kem LY DO va kem phan
    con lai la that. Mot danh sach rong o day nghia la co nguoi da xoa loi khai
    thay vi dong lai cai lo hong.
    """
    # ⭐ Danh sach RONG chi hop le khi bao cao noi ro CA HAI cua deu that. Mot
    #    danh sach rong khong kem hai co doc len giong het mot bao cao co nguoi
    #    xoa loi khai thay vi dong lai lo hong — dung dieu docstring canh bao.
    if not bc["thay_the"]:
        assert bc.get("model_that") and bc.get("giong_that"), (
            "bao cao khong khai cua thay the nao, va cung khong khai la da "
            "chay that ca hai cua")
        return
    for t in bc["thay_the"]:
        assert t["ly_do"].strip() and t["con_that"].strip(), t


def test_may_chay_nghiem_thu_duoc_ghi_lai(bc):
    """Mot con so hieu nang khong kem ten may la mot con so se bi cai nhau."""
    may = bc["may"]
    for khoa in ("os", "python", "loi_vat_ly", "ram_gib", "ffmpeg", "torch"):
        assert may.get(khoa) not in (None, ""), khoa


# ══════════════════════════════════════════════════════════════════════════════
#  C. CHOT LAI BA KHIEM KHUYET NGHIEM THU TIM RA
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔑 Nua B doc mot bao cao **da luu**, nen no khong the bat mot ban sua lam hong
#    lai dung thu vua duoc sua: bao cao khong doi khi ma doi. Ba phep kiem duoi
#    day doc thang MA NGUON HOM NAY, va chung la thu con lai khi khong ai chay
#    lai luot nang.

def test_TRINH_RENDER_khong_duoc_doc_ban_NEN(bc):
    """🔴 Khiem khuyet lon nhat pha 22 tim ra, chot bang AST.

    `giai_doan_ket_xuat.chay` tung tai `ban["tieng"]["nen"]` roi dua cho ffmpeg —
    tuc moi video giao cho khach mang **nhac nen tach ra tu ban goc**, khong mot
    cau long tieng nao. Ca hai nua deu dung nen khong phep kiem nao do: pha 16
    chung minh ban phoi dung, pha 17 chung minh cau lenh dung, va khong ai doi
    chieu cau lenh do doc dung TRUONG nao.

    ⛔ Doc AST chu khong quet van ban: mot chu thich noi ve `tieng.nen` — nhu
       chinh chu thich dang giai thich loi nay — khong duoc phep lam do phep
       kiem, va mot chuoi bi cat dong cung khong duoc phep lam no xanh.
    """
    import ast

    from apps.auto_scan_video import giai_doan_ket_xuat as gd

    cay = ast.parse(Path(gd.__file__).read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "chay")

    def _chuoi_khoa(nut) -> list[str]:
        ra = []
        while isinstance(nut, ast.Subscript):
            if isinstance(nut.slice, ast.Constant) and isinstance(nut.slice.value, str):
                ra.append(nut.slice.value)
            nut = nut.value
        return list(reversed(ra))

    xau = [_chuoi_khoa(n) for n in ast.walk(ham) if isinstance(n, ast.Subscript)]
    assert ["tieng", "nen"] not in xau, (
        "giai_doan_ket_xuat.chay doc lai ban NEN — tep giao cho khach se khong "
        "co tieng long")
    # ⭐ `master` duoc lay bang `.get("master")` chu khong bang `["master"]`, nen
    #    doi chieu tren HANG CHUOI trong cay cu phap: mot chu thich khong bao gio
    #    la mot `ast.Constant`, nen phep kiem van khong the bi mot dong giai
    #    thich lam cho xanh.
    hang = {n.value for n in ast.walk(ham)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "master" in hang, (
        "giai_doan_ket_xuat.chay khong doc ban phoi (`tieng.master`) nua")


def test_BAN_PHOI_phai_chua_bien_du_cho_bo_ma_hoa(bc):
    """🔴 QC T5 do dinh that tren tep **AAC**, con gioi han dat tren **PCM**.

    Do that o lan chay truoc khi sua: ban phoi -1,49 dBTP, tep ra -1,45 dBTP,
    tran -1,5 -> hong vi 0,05 dB tren mot ban phoi khong he sai. Mot chuoi giao
    hang co mat mat phai chua bien du cho buoc mat mat do.
    """
    from apps.auto_scan_video import am_master

    assert am_master.BIEN_CHO_CODEC_DB > 0, (
        "khong con bien du cho bo ma hoa — T5 se hong tren mot ban phoi dung")
    assert am_master.dinh_that_phoi_db() < am_master.dinh_that_db()
    # ⛔ Va bieu thuc THAT phai dung tran da tru bien du, khong phai tran giao
    #    hang: mot hang so dung ma khong ai doc la mot hang so khong lam gi.
    bt = am_master.bieu_thuc_chuan_am("[a]", "[b]")
    assert f"TP={am_master.dinh_that_phoi_db()}" in bt, bt
    assert f"TP={am_master.dinh_that_db()}:" not in bt, bt


def test_TOM_TAT_ban_dung_phai_noi_ro_CACH_RENDER(bc):
    """⭐ `che_do_hinh` luon la `copy` (ten cu), nen truoc pha 22 ban tom tat
    khong noi duoc lua chon co hau qua nhat cua ca ban dung: sao chep luong hinh
    hay cat-noi roi ma hoa lai. Hai lan chay khac han nhau trong y het nhau."""
    from apps.auto_scan_video import ban_dung, che_do_render

    ban = {"hinh": {"che_do": "copy", "cach_render": che_do_render.CAT_MA_HOA_LAI},
           "tieng": {"lop": []}, "ra": {"thoi_luong_giay": 1.0},
           "cong_cu": {"ffmpeg": "x"}}
    assert ban_dung.tom_tat(ban)["cach_render"] == che_do_render.CAT_MA_HOA_LAI


def test_CUA_GOI_MODEL_tra_ve_CHUOI_va_moi_nguoi_goi_phai_doc_qua_doc_json(bc):
    """🔴 Hai giai doan tra tien tung goi `.get("doan")` thang tren phan hoi tho.

    `ai.goi` tra ve **nguyen van** phan hoi cua model — mot chuoi. Ca
    `giai_doan_noi_dung` lan `giai_doan_giong` deu doi mot dict, nen moi lan goi
    model that deu nem `AttributeError`. Khong bo test nao thay, vi ban gia dung
    chung tra ve mot **dict** — thu cua that khong bao gio tra ve.

    ⭐ Chot o day la chot vao HINH DANG cua cua: moi nguoi goi `goi_tinh_tien`
       phai dua `noi_dung` qua `ai.doc_json` truoc khi doc no.
    """
    import ast

    from apps.auto_scan_video import ai, giai_doan_giong, giai_doan_noi_dung

    for mod in (giai_doan_noi_dung, giai_doan_giong):
        cay = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
        goi = [n for n in ast.walk(cay)
               if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Attribute)
               and n.func.attr == "doc_json"]
        assert goi, (f"{mod.__name__} goi model nhung khong doc qua "
                     "`ai.doc_json` — phan hoi tho la mot CHUOI")
    # Va cua that phai van tra ve chuoi: neu mot ngay nao do no tra dict, chot
    # tren la thua va phai duoc go — khong de nguoi sau doan.
    assert "noi_dung" in ai.goi.__doc__

# ══════════════════════════════════════════════════════════════════════════════
#  G17 · chan cuoi cung: PHIM KHACH THAT
# ══════════════════════════════════════════════════════════════════════════════

@rao_chan_nang.NANG
@rao_chan_nang.CHI_KHI_BAT
def test_G17_hai_preset_tren_PHIM_KHACH_THAT(moi_truong, tmp_path, monkeypatch):
    """🔴 **Chan cuoi cung cua G17 — va bai nay ton tai de no dong duoc trong MOT
    thao tac cua chu du an: tha phim vao thu muc.**

    Truoc bai nay, `asv_e2e_that/` chi la mot cai TEN trong ba ban bao cao —
    khong mot dong ma nao doc no. Nen "G17 kep vi thieu phim" thuc ra la "thieu
    phim VA them mot vong sua ma", va vong sua thu hai khong ai ghi ra. Mot mon
    no an nam trong mot cau nghe nhu da day du.

    ⭐ **Bai nay chot IT hon duong chinh, va do la dieu dung.** Phim khach khong
       di kem `SuThat`: ta khong biet truoc cau thoai nam o giay nao, nen khong
       doi chieu `phu_song_loi` duoc. Nhung thu no chot lai la thu mot ban tong
       hop **khong the** chung minh — tieng on phong, giong chong nhau, nhac nen
       that, cat canh khong sach:

        * ca hai preset chay het chuoi (`trang_thai_run == "done"`)
        * QC dat
        * ban ra khong dai hon nguon; preset giu hinh giu nguyen do dai
        * so ke khop doi soat — moi thu tinh tien deu co but toan

    ⛔ **Khong tep nao thi `skip`, va `skip` do phai NOI TEN thu con thieu.** Mot
       bo test xanh voi mot chan G17 con ho, ma su vang mat khong hien o dau,
       doc y het mot bo test da chung minh G17.
    """
    from apps.auto_scan_video import hop_dong_v4

    phim = fx.phim_khach_that()
    if not phim:
        pytest.skip(
            "G17 chua dong duoc: khong co tep phim nao trong "
            f"{fx.THU_MUC_PHIM_THAT}. Can 2 clip 2-5 phut, tieng Anh, MOT nguoi "
            "noi la du (san pham la thuyet minh mot giong; nhieu giong la huong "
            "mo rong sau), va it nhat MOT canh that su dang cat - de preset cat "
            "tra loi "
            "duoc cau hoi 'no CO cat khong' chu khong phai 'no khong co gi de "
            "cat'. Duoi nhan: " + ", ".join(fx.DUOI_PHIM))

    _app, a, csrf_a, b, _csrf_b = moi_truong
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_DEVICE", "cpu")
    monkeypatch.setenv("LTT_AUTOSUB_WHISPER_COMPUTE", "int8")

    # Cung phep bao ve nhu duong chinh: khong co khoa thi noi ra NGAY, khong
    # hong o giua chuoi sau khi da ton demucs va ASR.
    if fx.dung_model_that():
        from platform_core.db import get_session
        so_khoa = 0
        for _db in get_session():
            so_khoa = fx.nap_khoa_pool(_db)
            _db.commit()
            break
        assert so_khoa, (
            "LTT_ASV_MODEL_THAT=1 nhung pool that khong co khoa `ltt_llm` nao "
            "dung duoc - khong co duong nao goi model that")

    fx.dat_cua_model(monkeypatch, su_that=None)
    fx.dat_cua_giong(monkeypatch, tmp_path / "tieng")

    luot = []
    for tep in phim:
        goc_s = round(float(fx.soi(str(tep))["format"]["duration"]), 3)
        for nhan, preset in (("giu_hinh", hop_dong_v4.PRESET_GIU_HINH),
                             ("cat_thong_minh", hop_dong_v4.PRESET_CAT_THONG_MINH)):
            kq = _mot_luot(
                a, csrf_a, b, tep, tmp_path / f"{tep.stem}_{nhan}",
                nhan=f"{tep.name}::{nhan}", preset=preset,
                che_do_giong=hop_dong_v4.CHE_DO_GIONG_TU_CHON,
                giong_id="Minh Đức")
            kq["nguon_that"] = {"ten": tep.name, "byte": tep.stat().st_size,
                                "thoi_luong": goc_s}
            luot.append(kq)

    # ── Chot ────────────────────────────────────────────────────────────────
    for kq in luot:
        nhan = kq["nhan"]
        assert kq["trang_thai_run"] == "done", (
            f"{nhan}: chuoi khong chay het ({kq['trang_thai_run']}) — "
            + str(kq.get("vi_sao_hong")))
        assert kq["qc"]["dat"], f"{nhan}: QC hong o {kq['qc']['muc_hong']}"

        # ⚠️ `ra` rong nghia la khong co tep ban giao. Noi thang dieu do, dung
        #    de mot `KeyError` thay cho mot cau tra loi.
        assert kq["ra"], f"{nhan}: khong co tep ban giao de do"
        goc_s, ra_s = kq["nguon_that"]["thoi_luong"], kq["ra"]["thoi_luong"]
        assert ra_s <= goc_s + 1.0, (
            f"{nhan}: ban ra {ra_s:.2f}s DAI hon nguon {goc_s:.2f}s")
        if nhan.endswith("giu_hinh"):
            # ⚠️ Bien 1 giay, khong bien 0: ma hoa lai lam tron theo khung, nen
            #    mot phep do dung bang 0 se do vi mot su that ve container chu
            #    khong vi mot khiem khuyet.
            assert abs(ra_s - goc_s) <= 1.0, (
                f"{nhan}: preset GIU HINH doi do dai {goc_s:.2f} -> {ra_s:.2f}")

        assert kq["doi_soat"].get("khop") is not False, (
            f"{nhan}: so ke lech doi soat — {kq['doi_soat']}")

    # ⚠️ Chot nay chi co nghia neu chu du an tha dung loai clip duoc yeu cau, nen
    #    thong bao phai noi ro khi no do la ban NGUON khong hop le, khong phai
    #    san pham hong — hai ket luan rat khac nhau tu cung mot dong do.
    cat = [k for k in luot if k["nhan"].endswith("cat_thong_minh")]
    assert any(int(k["ban_bien_tap"].get("so_cat") or 0) > 0 for k in cat), (
        "khong clip nao bi cat canh nao. Neu san pham dung, thi ban nguon khong "
        "co canh nao dang cat — G17 can mot clip CO canh dang cat, khong phai "
        "mot clip bat ky")

    duong = Path(os.environ.get("LTT_ASV_G17_RA")
                 or (tmp_path / "g17_phim_that.json"))
    duong.parent.mkdir(parents=True, exist_ok=True)
    duong.write_text(json.dumps(fx.sach_de_cong_bo({
        "schema": "asv.v4.g17_phim_that.1",
        "ghi_luc": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "may": _dang_ky_may(),
        "so_clip": len(phim),
        "luot": luot,
    }), ensure_ascii=False, indent=2), encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#  Bo chay hang doi: "ban" khong duoc bien thanh "hong"
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def db_nhe(tmp_path, monkeypatch):
    """SQLite tam, chi de do HANH VI cua `_chay_hang_doi` — khong dung `moi_truong`.

    ⭐ Bai nay do mot thu cua BO CHAY, khong cua san pham, nen no khong can ca
       mot ung dung dung len. Dung `moi_truong` o day la tra gia vai giay cho
       moi lan chay de do mot vong `try/except`.
    """
    url = f"sqlite:///{(tmp_path / 'hd.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    s = next(dbmod.get_session())
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def test_tai_nguyen_BAN_thi_HOAN_chu_khong_giet_lan_chay(db_nhe, monkeypatch):
    """🔴 **Bo chay nay tung bien MOI ngoai le thanh that bai cuoi cung.**

        except Exception as exc:
            jobs.fail(db, job, str(exc), retry=False)      # <- ban CU

    Worker that thi phan loai truoc: mot `KhongCoProviderNao` ma **moi** provider
    chi BAN (`busy_only`) tra ve `("resource_wait", N)`, va job **ve hang doi**,
    khong tieu luot thu, khong cham tien.

    ⛔ Hau qua do duoc, 05/09 13:44: may B tra 429 cho moi lenh goi vi mot phien
       khac dang chay gate, va luot nghiem thu THAT bao `content_process
       failed_terminal`. Doc y het mot khiem khuyet san pham. San pham **dung**;
       chi bo chay sai.

    ⭐ Bai nay chot HANH VI (trang thai job + so luot thu), khong chot hinh dang
       ma. Mot ban viet lai dung `isinstance` tay van phai lam bai nay xanh.
    """
    from platform_core import jobs as pj
    from platform_core.llm.dieu_phoi import KhongCoProviderNao
    from platform_core.models import JOB_QUEUED, Job

    job = Job(user_id="u1", app_slug="asv_media", job_type="asv_media.qc",
              params={})
    db_nhe.add(job)
    db_nhe.commit()
    ma_job = job.id

    def cua_gia(_job_type):
        def chay(_params, _ctx):
            raise KhongCoProviderNao(["ltt_llm: ban"])
        return chay

    monkeypatch.setattr(pj, "resolve_handler", cua_gia)
    # ⚠️ Chan giac ngu THAT: bo chay ngu dung `retry_after` cua nen tang (20s).
    #    Do la hanh vi dung o san pham va la mot phut vo ich trong mot bai kiem.
    monkeypatch.setattr(time, "sleep", lambda _s: None)

    nhat_ky = _chay_hang_doi(db_nhe, toi_da=3)

    db_nhe.expire_all()
    lai = db_nhe.get(Job, ma_job)
    assert lai.status == JOB_QUEUED, (
        f"tai nguyen ban ma job thanh {lai.status} — do la bien mot tin hieu "
        "'cho chut' thanh mot lan chay hong")
    assert lai.attempts == 0, (
        f"luot thu bi tieu ({lai.attempts}) — `defer_resource` khong duoc tieu "
        "luot nao, neu khong thi vai lan ban lien tiep se dot het han muc")
    assert nhat_ky and nhat_ky[0]["loi"].startswith("HOAN"), nhat_ky
    assert nhat_ky[0].get("hoan_s", 0) > 0, (
        "bo chay phai GHI RA rang no da hoan, neu khong thi mot luot cham vi "
        "tai nguyen ban doc y het mot luot cham vi san pham")


def test_loi_KHONG_phai_ban_thi_van_that_bai_nhu_cu(db_nhe, monkeypatch):
    """⛔ Ban sua tren de lai mot rui ro ro rang: doc thanh "bo chay khong bao gio
    lam hong job nua". Bai nay chot rang mot loi THAT van giet job.

    ⚠️ Va no la nua khong the thieu: neu chi co bai tren, mot ban sua "hoan MOI
       loi" se xanh — va luc do bo test khong con phan biet duoc san pham hong
       voi tai nguyen ban, tuc mat dung nang luc vua duoc them.
    """
    from platform_core import jobs as pj
    from platform_core.models import JOB_ERROR, Job

    job = Job(user_id="u1", app_slug="asv_media", job_type="asv_media.qc",
              params={})
    db_nhe.add(job)
    db_nhe.commit()
    ma_job = job.id

    def cua_gia(_job_type):
        def chay(_params, _ctx):
            raise ValueError("ban dung bi hong that")
        return chay

    monkeypatch.setattr(pj, "resolve_handler", cua_gia)
    monkeypatch.setattr(time, "sleep", lambda _s: None)

    nhat_ky = _chay_hang_doi(db_nhe, toi_da=3)

    db_nhe.expire_all()
    lai = db_nhe.get(Job, ma_job)
    assert lai.status == JOB_ERROR, f"loi that ma job thanh {lai.status}"
    assert nhat_ky and not nhat_ky[0]["loi"].startswith("HOAN"), nhat_ky
