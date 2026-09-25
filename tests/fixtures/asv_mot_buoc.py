"""Chay DUNG MOT giai doan ASV, tren dau vao co san (Task 4, thang cong tung buoc).

## Van de no giai

Muon do `transcribe` — mot buoc ~20 giay — hien phai di qua `media_prepare` +
`audio_prepare` truoc, tuc **3 phut de do mot buoc 20 giay**. Thang do tung buoc
chay phep do do hang chuc lan; 3 phut moi lan la ly do nguoi ta thoi do.

## ⛔ Ba thu KHONG duoc viet lai o day

    card          -> `asv_e2e.card_cho_job`       (goi CHINH `_vram_can` + `_giu_gpu`)
    trinh thong dich -> `asv_e2e.ghim_python_co_card`
    chon giai doan  -> `thi_hanh.chay_giai_doan`  (be mat CONG KHAI cua hai executor)

Go lai bang 12 nhanh o day la dung cai N-08 canh bao: **hai cho khai cung mot dieu,
khong ai bat khop**. Bang do da co mot ban trong `thi_hanh`, va no la ban THAT.

## ⚠️ Gieo theo TAP DOC THAT, khong theo cot `sau`

`BAN_DO_BUOC.md` §2: ban khai `sau=` **hep hon** thu ma that su doc o 8/12 giai doan
(bao dong bac cau thi phu, nen hom nay khong hong — N-08). Gieo theo cot `sau` cho
mot loi *"thieu dau vao"* **nghe nhu khiem khuyet san pham**, va nguoi doc se di sua
nham cho — dung chuyen da xay ra o luot A (N-06).

⇒ `can_gieo()` doc **tu ma** (AST), khong doc ban khai.

## ⚠️ Chu ky lech plan mot chut, va day la ly do

Plan viet `chay_mot_buoc(db, kho, *, ...)`. Ban nay nhan **bo canh `moi_truong`** vi
lan chay phai duoc dung qua `dich_vu_tao` — chinh cho **G-01** tung duyet `nguon_loi`
roi khong ghi vao ho so. Mot khuon tu dung `AsvRun` bang ORM se **bo qua** dung mat
xich ma Task 5 phai chung minh.
"""
from __future__ import annotations

import ast
import pathlib

from apps.auto_scan_video import pipeline as P

#: Giai doan -> module thuc thi. ⛔ Doi chieu voi `thi_hanh._chay_giai_doan`, xem
#: `test_3004::test_moi_giai_doan_deu_co_module_thuc_thi`.
TEN_MODULE = {
    P.MEDIA_PREPARE: "giai_doan_media",
    P.AUDIO_PREPARE: "giai_doan_am_thanh",
    P.TRANSCRIBE: "giai_doan_chep_loi",
    P.EDIT_PLAN: "giai_doan_ban_bien_tap",
    P.CONTENT_PROCESS: "giai_doan_noi_dung",
    P.VOICE_SYNTHESIS: "giai_doan_giong",
    P.TIMING_ALIGN: "giai_doan_thoi_gian",
    P.COMPOSE: "giai_doan_ban_dung",
    P.RENDER: "giai_doan_ket_xuat",
    P.IMAGE_FINISH: "giai_doan_hinh_anh",
    P.QC: "giai_doan_qc",
    P.QC_DO_LUONG: "giai_doan_qc_do_luong",
    P.QC_AI: "giai_doan_qc_ai",
}

GOC = pathlib.Path(P.__file__).parent
THU_TU = {g.ten: i for i, g in enumerate(P.CHUOI)}


#: Cac truong `dich_vu_tao.dung_cai_dat` BAT BUOC ma mot bench thuong khong quan
#: tam. ⛔ Nguoi goi de len duoc — xem `_dung_lan_chay`.
MAC_DINH_BENCH = {
    "che_do_giong": "AUTO_MATCH",
}


#: Cac giai doan co NHIEU NHANH engine. Voi chung, `nhanh_mong_doi` la BAT BUOC.
#:
#: 🔴 **Vi sao bat buoc, va vi sao KHONG co mac dinh.** Ba lan trong mot phien, khuon
#:    do **chinh no** thay vi do san pham: (1) khong xin card — K-01; (2) khong ghim
#:    trinh thong dich — K-05; (3) khong nap `app.env` nen `whisperx_available()` tra
#:    False va bench do **nhanh LUI** trong khi tuong minh do nhanh mac dinh.
#:
#: ⛔ Mot mac dinh se lam nguoi viet bench sau **khong khai**, va ta quay lai dung
#:    hom nay. Bat khai la thu khien lan sau **khong im lang duoc** — cung ly do
#:    `nguon_loi.chuan_che_do(..., mac_dinh=)` bat khai duong DOC hay duong NHAN.
NHANH_THEO_GIAI_DOAN = {
    P.TRANSCRIBE: {
        "khoa_outputs": "canh_chinh",
        # gia tri `canh_chinh` -> ten nhanh nguoi doc hieu
        "anh_xa": {"aligned": "whisperx", "fallback_unaligned": "faster-whisper"},
    },
}


class _ChuaKhai:
    """Sentinel: phan biet *"khong truyen"* voi *"truyen None"*.

    ⛔ Dung `None` lam mac dinh se gop hai y do khac nhau lam mot — dung bay
       "hai trang thai gop thanh mot gia tri" ma so may nay ghi.
    """

    def __repr__(self) -> str:
        return "<chua khai>"


CHUA_KHAI = _ChuaKhai()


class NhanhSaiError(RuntimeError):
    """Do xong roi moi biet san pham chay mot nhanh KHAC nhanh dinh do.

    ⛔ Nem, ⛔ khong ghi so: mot con so cua nhanh khong dinh do **khong tra loi cau
       hoi nao cua ta**, va de no trong bang ket qua la moi nguoi sau so no voi so
       cua nhanh chinh.
    """


class ThieuDauVaoGieo(RuntimeError):
    """Goi mot buoc giua chuoi ma khong gieo dau vao cua no.

    🔴 **Vi sao co mot ngoai le RIENG, khong de `KeyError` tu nhien bay ra.**

       Mot `KeyError` trong o day la cai bay te nhat cua ca thang: nguoi do se doc
       no thanh *"san pham hong"* trong khi no la *"khuon thieu dau vao"*. Dung
       chuyen do da xay ra o luot A (N-06) — `auto_match_thieu_can_cu` mat ba vong
       moi tach duoc ra khoi ket luan *"AUTO_MATCH la duong chet"*.
    """


def _module(ten: str):
    from importlib import import_module
    return import_module(f"apps.auto_scan_video.{TEN_MODULE[ten]}")


#: Giai doan -> module da nap. Dung cho phep kiem muon thay `chay` cua tung module.
class _BangModule(dict):
    def __missing__(self, ten):
        mod = _module(ten)
        self[ten] = mod
        return mod


MODULE_GIAI_DOAN = _BangModule({})
for _t in TEN_MODULE:
    MODULE_GIAI_DOAN[_t] = _module(_t)


def doc_that_su(ten: str) -> set:
    """Cac giai doan ma module cua `ten` THAT SU doc (quet AST, khong doc ban khai).

    Phan giai `pipeline.MEDIA_PREPARE` -> `"media_prepare"` bang `getattr`, khong so
    ten hang. ⛔ Ban nhap dau cua phep quet nay so `n.attr` voi ten giai doan va tra
    **RONG cho ca 12 module** — mot phep quet rong thi moi phep kiem dua tren no deu
    xanh, mai mai (xem `test_3004::test_phep_kiem_nay_KHONG_RONG`).
    """
    cay = ast.parse((GOC / f"{TEN_MODULE[ten]}.py").read_text(encoding="utf-8"))
    ra = set()
    for n in ast.walk(cay):
        if not (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                and n.value.id == "pipeline" and n.attr.isupper()):
            continue
        gt = getattr(P, n.attr, None)
        if isinstance(gt, str) and gt in THU_TU:
            ra.add(gt)
    return ra


def can_gieo(ten: str) -> set:
    """Nhung giai doan phai duoc gieo truoc khi chay `ten`.

    = tap DOC THAT, bo chinh no, bo cac giai doan dung SAU no trong `CHUOI`.

    ⚠️ Bo phan doc NGUOC la co y: `edit_plan`/`voice_synthesis`/`qc_ai` doc phan
       quyet cua cac buoc **sau** chung — do la **duong vong sua** (`sua_chua`), co
       that va dung thiet ke, khong phai mot dau vao phai gieo truoc.
    """
    return {g for g in doc_that_su(ten) if THU_TU[g] < THU_TU[ten]}


def chay_mot_buoc(moi_truong, *, ten_giai_doan: str, cai_dat: dict,
                  duong_video=None, gieo: dict | None = None,
                  xin_card: bool = True, monkeypatch=None,
                  nhanh_mong_doi=CHUA_KHAI) -> dict:
    """Chay DUNG MOT giai doan. Tra `outputs` cua no + loi khai card/trinh thong dich.

    `gieo` = `{ten_giai_doan_truoc: khoa_asset}`. Thieu mot muc ma `can_gieo` doi
    ⇒ `ThieuDauVaoGieo` **noi ro thieu gi**.
    """
    from apps.auto_scan_video import features, thi_hanh
    from tests.fixtures import asv_e2e as fx

    thieu = can_gieo(ten_giai_doan) - set(gieo or {})
    if thieu:
        raise ThieuDauVaoGieo(
            f"buoc {ten_giai_doan!r} doc artifact cua {sorted(thieu)} nhung `gieo` "
            f"khong co muc nao cho chung. Them vao `gieo=` "
            f"({{'<giai doan>': '<khoa_asset>'}}). ⚠️ Danh sach nay lay tu TAP DOC "
            f"THAT (quet AST), khong tu cot `sau` — ban khai `sau` hep hon thuc te.")

    _kiem_nhanh_da_khai(ten_giai_doan, nhanh_mong_doi)
    _kiem_khoa_gieo(gieo or {})
    run_id, owner_id = _dung_lan_chay(moi_truong, cai_dat, duong_video)
    _gieo_cac_buoc_truoc(run_id, gieo or {})

    khai_python = (fx.ghim_python_co_card(monkeypatch)
                   if (xin_card and monkeypatch is not None) else
                   {"da_ghim": False, "vi_sao": "xin_card=False (bai nhe)"})

    import contextlib
    from platform_core.job_runner import JobContext

    job_id = f"bench-{ten_giai_doan}"
    boc = (fx.card_cho_job(P.THEO_TEN[ten_giai_doan].job_type, job_id)
           if xin_card else contextlib.nullcontext(("", False)))
    with boc as (gpu_uuid, het_gpu):
        if het_gpu:
            raise RuntimeError(
                f"buoc {ten_giai_doan!r} doi card, may CO card nhung deu dang ban. "
                f"⛔ Khong chay CPU thay the: so giay se la so cua KHUON.")
        ctx = JobContext(job_id, gpu_uuid=gpu_uuid)
        ctx.job_type = P.THEO_TEN[ten_giai_doan].job_type
        thi_hanh.chay_giai_doan(
            ten_giai_doan, {"run_id": run_id, "owner_id": owner_id}, ctx)

    import platform_core.db as dbmod
    db = next(dbmod.get_session())
    try:
        gd = features.giai_doan_theo_ten(db, run_id, ten_giai_doan)
        out = dict(getattr(gd, "outputs", None) or {})
        trang_thai = str(getattr(gd, "status", ""))
        loi = str(getattr(gd, "error", "") or "")
    finally:
        db.close()

    _kiem_nhanh_da_chay(ten_giai_doan, nhanh_mong_doi, out)

    return {
        "run_id": run_id, "giai_doan": ten_giai_doan,
        "trang_thai": trang_thai, "loi": loi, "outputs": out,
        "card": {"gpu_uuid": gpu_uuid[:20], "duoc_card": bool(gpu_uuid),
                 "can_card": bool(_vram(ten_giai_doan))},
        "trinh_thong_dich": khai_python,
    }


def nhanh_da_chay(ten_giai_doan: str, outputs: dict) -> str:
    """Nhanh engine THAT SU da chay, doc tu `outputs`. `""` neu buoc khong co nhanh."""
    khai = NHANH_THEO_GIAI_DOAN.get(ten_giai_doan)
    if not khai:
        return ""
    gt = str(outputs.get(khai["khoa_outputs"]) or "")
    return khai["anh_xa"].get(gt, gt)


def _kiem_nhanh_da_khai(ten_giai_doan: str, nhanh_mong_doi) -> None:
    """⛔ Buoc co nhieu nhanh thi nguoi goi PHAI khai y dinh. Khong mac dinh."""
    if ten_giai_doan not in NHANH_THEO_GIAI_DOAN:
        return
    if nhanh_mong_doi is CHUA_KHAI:
        co = sorted(set(NHANH_THEO_GIAI_DOAN[ten_giai_doan]["anh_xa"].values()))
        raise NhanhSaiError(
            f"buoc {ten_giai_doan!r} co NHIEU nhanh engine ({', '.join(co)}) nen "
            f"`nhanh_mong_doi=` la BAT BUOC. ⛔ Khong co mac dinh: mot mac dinh lam "
            f"nguoi viet bench sau khong khai, va ta quay lai dung 24/09 — do nhanh "
            f"LUI trong khi tuong minh do nhanh mac dinh.")


def _kiem_nhanh_da_chay(ten_giai_doan: str, nhanh_mong_doi, outputs: dict) -> None:
    """Do xong: nhanh THAT != mong doi ⇒ NEM, ⛔ khong ghi so."""
    if ten_giai_doan not in NHANH_THEO_GIAI_DOAN or nhanh_mong_doi is CHUA_KHAI:
        return
    if nhanh_mong_doi is None:
        return                      # khai TUONG MINH la "nhanh nao cung duoc"
    that = nhanh_da_chay(ten_giai_doan, outputs)
    if that != nhanh_mong_doi:
        ly_do = str(outputs.get("ly_do_roi") or "(san pham khong ghi ly do)")
        raise NhanhSaiError(
            f"bench dinh do {nhanh_mong_doi!r} nhung san pham da chay {that!r} "
            f"vi {ly_do!r}. ⛔ KHONG ghi so: mot con so cua nhanh khong dinh do "
            f"khong tra loi cau hoi nao cua ta, va de no trong bang ket qua la moi "
            f"nguoi sau so no voi so cua nhanh chinh.")


def _kiem_khoa_gieo(gieo: dict) -> None:
    """Khoa gieo phai la khoa KHO hop le — noi SOM, ⛔ khong de kho noi ho.

    🔴 **Do that 24/09.** Bench B1 gieo `"bench:<ten phim>.wav"` va chet o
       `platform_core.storage.StorageError: key khong hop le` — vi `:` bi rao chan
       path traversal tu choi. Thong diep do chi vao **kho**, trong khi nguyen nhan
       la **khoa gieo bia ra**, cach do bay buoc.

    ⇒ Cung ly do `ThieuDauVaoGieo` ton tai: mot thong diep chi dung cho SE bi doc
      thanh "san pham hong". Kiem o cua thi nguoi do biet ngay minh dua sai gi.
    """
    from platform_core import storage as kho_mod

    for ten, khoa in gieo.items():
        for k in ([khoa] if isinstance(khoa, str) else list(khoa)):
            try:
                kho_mod._safe_key(k)                    # noqa: SLF001
            except Exception as loi:                    # noqa: BLE001
                raise ThieuDauVaoGieo(
                    f"khoa gieo cho {ten!r} khong phai mot khoa kho hop le: "
                    f"{k!r} ({loi}). ⚠️ Khoa gieo phai la khoa THAT do mot giai "
                    f"doan truoc sinh ra — vi du chay `media_prepare` roi lay "
                    f"`outputs['khoa_asset']` cua no.") from loi


def _vram(ten: str) -> int:
    from platform_core.job_runner import _vram_can
    return _vram_can(P.THEO_TEN[ten].job_type)


def _dung_lan_chay(moi_truong, cai_dat: dict, duong_video=None):
    """Dung mot `AsvRun` QUA `dich_vu_tao` — khong tu ghi ORM.

    🔑 **G-01 la ly do.** `dung_cai_dat` tung DUYET `nguon_loi` roi **khong dat vao
       ho so tra ve**, nen khach ep `embedded`/`ocr`/`asr` van chay `auto`, im lang.
       Mot khuon tu dung `AsvRun` bang ORM se bo qua dung mat xich do — va Task 5
       phai chung minh chinh no.
    """
    import platform_core.db as dbmod

    from apps.auto_scan_video import dich_vu_tao, features

    _app, a, csrf, _b, _csrf = moi_truong
    db = next(dbmod.get_session())
    try:
        ma = a.get("/auto-scan-video").status_code
        assert ma == 200, f"khong mo duoc trang ASV: {ma}"
        chu = _chu(db)
        # ⭐ Mac dinh cho MOI truong bat buoc ma bench khong quan tam. Nguoi goi
        #    chi phai khai dung thu ho dang DO — con lai khuon dien.
        # ⛔ Va `cai_dat` cua nguoi goi DE LEN mac dinh, khong nguoc lai: neu
        #    nguoc, mot bench ep `nguon_loi=asr` se im lang chay `auto` — dung
        #    hinh dang G-01.
        tho = dict(MAC_DINH_BENCH)
        tho.update(cai_dat or {})
        ho_so = dich_vu_tao.dung_cai_dat(db, owner_id=chu, tho=tho)
        # ⭐ Hai loi vao THAT, tuy co phim hay khong:
        #
        #    co `duong_video`  -> `tao_run_tu_tai_len`: tep di vao KHO that, co
        #                         `source_key` that ⇒ `media_prepare` chay duoc.
        #    khong             -> `tao_run` voi mot `source_key` gia, du cho cac
        #                         bai NHE thay het 12 giai doan bang monkeypatch.
        #
        # 🔴 **Do that 24/09:** ban dau khuon LUON dung `source_key="bench:..."`, va
        #    bench B1 chet o `StorageError: key khong hop le` — vi `:` va khoang
        #    trang bi `storage._chuan_key` tu choi (chan path traversal). Trieu chung
        #    chi vao KHO, trong khi nguyen nhan la **khuon chua bao gio tai phim len**.
        if duong_video:
            run = features.tao_run_tu_tai_len(
                db, owner_id=chu, duong_tep=str(duong_video),
                ten_tep=pathlib.Path(duong_video).name, settings=dict(ho_so))
        else:
            run = features.tao_run(db, owner_id=chu,
                                   source_key="bench/nguon.mp4",
                                   settings=dict(ho_so), uoc_luong_credit=0)
        db.commit()
        db.refresh(run)
        return run.id, run.owner_id
    finally:
        db.close()


def _chu(db) -> str:
    from platform_core.models import User
    u = db.query(User).order_by(User.id).first()
    assert u is not None, "bo canh `moi_truong` chua tao nguoi dung nao"
    return u.id


def _gieo_cac_buoc_truoc(run_id: str, gieo: dict) -> None:
    import platform_core.db as dbmod

    from apps.auto_scan_video import tables as T

    db = next(dbmod.get_session())
    try:
        for ten, khoa in gieo.items():
            s = (db.query(T.AsvStage)
                 .filter(T.AsvStage.run_id == run_id, T.AsvStage.stage == ten)
                 .one())
            out = dict(s.outputs or {})
            out["khoa_asset"] = [khoa] if isinstance(khoa, str) else list(khoa)
            s.outputs = out
            s.status = "succeeded"
        db.commit()
    finally:
        db.close()
