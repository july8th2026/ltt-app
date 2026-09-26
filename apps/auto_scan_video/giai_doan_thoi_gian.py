"""Giai doan TIMING_ALIGN — lap ke hoach dat tung doan tieng len truc thoi gian.

Mot artifact ra:

    timing_plan.json   ke hoach dat doan   (kind=json)

## 🔴 Pha 16 doi mot cau o day, va ly do dang ghi lai

Ban truoc noi: *"giai doan nay khong cham mot tep am thanh nao"*. Nay no ra HAI
artifact: ke hoach **truoc**, roi ban phoi am dung theo ke hoach do.

⭐ Va cau cu van dung o cho quan trong nhat: quyet dinh thoi gian **khong** bi
   giau ben trong mot phep ghep. Ke hoach duoc dung, kiem va **luu** truoc; ban
   phoi chi la mot phep thi hanh tat dinh cua no. Doc lai ke hoach van biet duoc
   moi doan nam o dau ma khong phai mo mot tep wav nao.

⛔ Cai KHONG doi: khong render hinh o day, va khong mot loi goi model nao. Pha 16
   cam ca hai bang chu.

⭐ Nho vay ke hoach doc duoc, kiem duoc va **sua duoc** ma khong phai render lai:
   mot lan chay lai chi ton vai mili-giay o phan ke hoach.

Thi hanh `ADR-003-mo-hinh-thoi-gian.md`.
"""
from __future__ import annotations

import io
import json
import logging
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (am_master, assets, hop_dong_v4, nan_cho_vua, nan_thoi_luong,
               nhap_media, pipeline, thoi_gian, van_ban)
from .giai_doan_media import ThieuNguon

log = logging.getLogger(__name__)

#: Tran KY THUAT cua `ffmpeg atempo` cho MOT lan goi tren doan tieng, ⛔ KHONG
#: phai mot chinh sach san pham (do la `thoi_gian.TRAN_TANG_TOC`, chot 26/09:
#: "vuot tran thoai mai" — khong con la cong).
#:
#: 🔑 Qua tran nay thuat toan WSOLA cua `atempo` khong con giu duoc dang song
#:    tot, cho ra TIENG RAC chu ⛔ khong phai "tieng nhanh" — khac han cai gia
#:    cua viec vuot `TRAN_TANG_TOC` (giong hoi meo nhung van nghe duoc loi).
#:    `am_master.py` da co tran cung `[0,5; 100]` cho MOT lan goi khong chain,
#:    nhung 100 chi la tran "khong crash"; 2.0 la tran "con nghe duoc" theo tai
#:    lieu bo loc `atempo` cua ffmpeg. `he_so_co_gian` o day luon >= 1.0
#:    (`nan_cho_vua.co_gian_du_khong`: he_so = giay/khe, chi tinh khi giay >
#:    khe), nen chi can MOT tran tren — khong can `max()` cho bien duoi.
TRAN_KY_THUAT_ATEMPO = 2.0


def he_so_ap(h: float, *, tran_ky_thuat: float) -> float:
    """He so tang toc THAT SU se ap cho MOT doan (nac cuu (c), Task 4/8/16).

    Ham THUAN — khong doc tep, khong goi ffmpeg, khong cham kho. Chi kep ve
    `tran_ky_thuat` (tran KY THUAT cua `atempo`, qua do WSOLA ra TIENG RAC).
    ⛔ KHONG kep ve `thoi_gian.TRAN_TANG_TOC` — do la CHINH SACH SAN PHAM (chu
    du an chot 26/09: vuot tran do thoai mai, tran chi con la CANH BAO, khong
    phai mot cong). Vi `h` luon >= 1.0 (`nan_cho_vua.co_gian_du_khong` chi tinh
    khi giay > khe) nen chi can MOT tran TREN, khong can `max()` cho bien duoi.
    """
    return min(float(tran_ky_thuat), float(h))


def dem_lech_cuoi(doan: list[dict], he_so_theo_ma: dict[str, float]) -> tuple[int, float]:
    """Dem so doan CON LECH khoi khe SAU KHI da ap he so toc (nac cuu (c), Task 8/16).

    Ham THUAN — khong doc tep, khong goi ffmpeg, khong cham kho. Nhan danh
    sach dong ke `doan` (moi dong co the co "ma", "giay", "khe",
    "he_so_co_gian") va `he_so_theo_ma` — map `ma -> he so THAT SU DA AP`
    (`h_ap`, gia tri tra ve tu `he_so_ap`).

    Chi dem doan THAT SU bi KEP boi tran ky thuat (tuc `h_ap != he_so_co_gian`
    cua chinh dong do) VA sau khi ap he so do, tep tieng van dai hon khe cua no
    (`giay/h_ap > khe`). Doan khong bi kep thi ve mat toan hoc `giay/h_ap`
    trung khop `khe` (vi `he_so_co_gian = giay/khe`) — dieu kien `h_ap != h`
    tranh dem nham mot sai so lam tron dau phay dong o bien nhu mot cho LECH.

    Tra `(so_doan_lech_cuoi, giay_lech_cuoi)`.
    """
    so_doan_lech_cuoi = 0
    giay_lech_cuoi = 0.0
    for d in doan:
        if nan_thoi_luong.la_dong_theo_sau(d):
            continue
        ma = str(d["ma"])
        h_ap = he_so_theo_ma.get(ma)
        if h_ap is None:
            continue
        h = float(d.get("he_so_co_gian") or 1.0)
        if h_ap == h:
            continue
        giay = float(d.get("giay") or 0.0)
        khe = float(d.get("khe") or 0.0)
        if khe > 0 and giay > 0:
            giay_sau = giay / h_ap
            if giay_sau > khe:
                so_doan_lech_cuoi += 1
                giay_lech_cuoi += giay_sau - khe
    return so_doan_lech_cuoi, giay_lech_cuoi


class ThieuDauVao(ThieuNguon):
    """Chua co ban dich hoac chua co tieng de lap ke hoach."""


def _doc_json(kho: Storage, khoa: str) -> dict:
    with kho.open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def _dau_vao(db, kho: Storage, run) -> tuple[dict, dict, str, str]:
    """`(van_ban_da_xu_ly, ban_ke_tieng, checksum_van_ban, checksum_ban_ke)`."""
    from . import features

    s_vb = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    khoa_vb = next((k for k in ((s_vb.outputs or {}).get("khoa_asset") or [])
                    if k.endswith(".json")), "") if s_vb else ""
    if not khoa_vb:
        raise ThieuDauVao(_t('Chưa có bản dịch để lập kế hoạch thời gian.'))

    s_g = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    khoa_ke = next((k for k in ((s_g.outputs or {}).get("khoa_asset") or [])
                    if k.endswith(".json")), "") if s_g else ""
    if not khoa_ke:
        raise ThieuDauVao(_t('Chưa có bản kê tiếng để lập kế hoạch thời gian.'))

    tl_vb = _doc_json(kho, khoa_vb)
    van_ban.kiem(tl_vb)
    ban_ke = _doc_json(kho, khoa_ke)

    with kho.open(khoa_vb) as f:
        cs_vb = assets.bam(f.read())
    with kho.open(khoa_ke) as f:
        cs_ke = assets.bam(f.read())
    return tl_vb, ban_ke, cs_vb, cs_ke


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc ban dich + do dai tieng THAT -> ke hoach dat doan."""
    tl_vb, ban_ke, cs_vb, cs_ke = _dau_vao(db, kho, run)

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(20, _t('Đang lập kế hoạch thời gian'))

    # 🔑 Do dai THAT cua tung tep tieng, khong phai do dai uoc tinh tu so ky tu.
    #    Mot phep uoc o day se lech, va lech tich luy — dung thu ma ca mo hinh
    #    no trong ADR-003 sinh ra de kiem soat.
    do_dai = {str(d["ma"]): float(d.get("giay") or 0.0)
              for d in (ban_ke.get("doan") or [])}

    # Thoi luong nguon lay tu ho so soi cua MEDIA_PREPARE.
    from . import features
    s_media = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
    tong_giay = float((s_media.outputs or {}).get("thoi_luong") or 0.0) if s_media else 0.0
    if tong_giay <= 0:
        raise ThieuDauVao(_t('Không biết thời lượng video nguồn.'))

    # ⛔ Truoc pha 07 dong nay chep CUNG chuoi `"fit_original"` — ban thu
    #    BA cua `gia.CHE_DO_MAC_DINH`, va mot trong ba ban do da lech.
    from . import cai_dat as cd
    che_do = cd.doc(run).timing_mode
    # ⭐ Khe da GOP (`nan_thoi_luong.gop_khe`): MOT tep tieng, NHIEU `ma`. Cac
    #    `ma` di theo phai duoc dat LIEN NHAU thay vi o moc goc cua chung —
    #    `thoi_gian.lap_ke_hoach` doi hoi `nhom_gop` de biet dieu do. Rong khi
    #    lan chay khong gop gi, va khi do ke hoach khong doi mot mili-giay.
    # 🔴 **KHONG mot tham so nao doc preset o day (b4 hai giai doan, 25/09).**
    #    Giai doan 1 giao MP4 tieng Viet **toan bo do dai goc**, nen hai preset
    #    di y het mot duong voice. Cat canh nam o giai doan 2 (`ke_cat.py`), sau
    #    render, tren mot tep da xong. `test_4801` ghim menh de nay bang may.
    ke_hoach = thoi_gian.lap_ke_hoach(
        tl_vb.get("muc") or [], do_dai, tong_giay=tong_giay, che_do=che_do,
        nhom_gop=nan_thoi_luong.nhom_theo_ma(ban_ke))

    goi = json.dumps(ke_hoach, sort_keys=True, ensure_ascii=False).encode("utf-8")
    vt = thoi_gian.van_tay_ke_hoach(checksum_van_ban=cs_vb, ban_ke_tieng=cs_ke,
                                    che_do=che_do)

    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.TIMING_ALIGN, van_tay=vt,
                               duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")
    phan = [{"staging_key": khoa, "kind": "json", "duoi": "json", "van_tay": vt}]

    # ── Ban phoi am, SAU khi ke hoach da ben ───────────────────────────────
    #
    # 🔑 Thu tu la mot phan cua hop dong (pha 16 muc 4): ke hoach truoc, ban phoi
    #    sau. Neu ban phoi hong thi ke hoach van con — va lan chay lai khong phai
    #    tinh lai gi ca, chi tron lai.
    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(50, _t('Đang trộn bản phối'))

    khoa_master, do_duoc, vt_master = _dung_ban_phoi(
        db, kho, run, ke_hoach=ke_hoach, ban_ke=ban_ke, tong_giay=tong_giay,
        van_tay_ke_hoach=vt, ctx=ctx)
    phan.append({"staging_key": khoa_master, "kind": "audio", "duoi": "wav",
                 "van_tay": vt_master})

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu kết quả'))

    # ⛔ `ban_do` / `so_cho_noi` DA ROI KHOI bao cao nay: o giai doan 1 khong co
    #    cho noi nao — luong hinh di nguyen ven. Hai khoa luon bang `0`/dong nhat
    #    se lam moi bao cao van hanh noi rang "da kiem cho noi" trong khi khong
    #    cho noi nao ton tai. Giai doan 2 khai chung (`ke_cat.tom_tat`).
    tom_tat = {**thoi_gian.tom_tat(ke_hoach), "master": do_duoc}
    return {"phan": phan, "tom_tat": tom_tat}


def _dung_ban_phoi(db, kho: Storage, run, *, ke_hoach: dict, ban_ke: dict,
                   tong_giay: float, van_tay_ke_hoach: str, ctx=None):
    """Tron nen + cac doan tieng theo ke hoach.

    Tra `(khoa, do_duoc, van_tay)` — `do_duoc["he_so_toc_da_ap"]` liet ke moi
    he so tang toc THAT SU da ap cho tung doan (task 4, chot 26/09)."""
    import tempfile

    from . import features
    from .giai_doan_media import _duong_doc_duoc

    s_am = features.giai_doan_theo_ten(db, run.id, pipeline.AUDIO_PREPARE)
    khoa_nen = next((k for k in (((s_am.outputs or {}) if s_am else {})
                                 .get("khoa_asset") or []) if k.endswith(".wav")), "")
    if not khoa_nen:
        raise ThieuDauVao(_t('Chưa có bản nền để trộn bản phối.'))

    # 🔴 **`tep_theo_ma`, ⛔ KHONG mot dict comprehension o day.** Voi khe da gop
    #    thi 2-4 `ma` tro vao CUNG mot tep tieng; dat theo tung `ma` se tron tep
    #    ay 2-4 lan — nghe thanh tieng vang, ⛔ khong nem, ⛔ khong log. Ham ay chi
    #    tra ve nhung dong SO HUU mot tep (`nan_thoi_luong.la_dong_theo_sau`).
    khoa_theo_ma = nan_thoi_luong.tep_theo_ma(ban_ke)
    # 🔑 **Tran la CANH BAO, ⛔ khong phai mot cong (chu du an chot 26/09).**
    #    Truoc day `he_so_co_gian` cua mot doan `CAN_SUA` (vuot
    #    `thoi_gian.TRAN_TANG_TOC`, thuong vi `LTT_ASV_QC_AI` tat theo mac
    #    dinh nen khong lan chay nao qua vong sua truoc khi toi day) bi KEP ve
    #    tran THIET KE — mot doan tran qua trai bi dat SAI CHO trong im lang.
    #    Nay: ap DUNG he so can, chi GHI CANH BAO (log.warning) khi vuot tran
    #    thiet ke, va DEM moi he so THAT SU da ap vao `he_so_toc_da_ap` (danh
    #    sach float, ra trong `do_duoc` — giai doan nay tra ve trong outputs)
    #    de ai doc bao cao van hanh thay duoc: cai gia (giong hoi meo) khach
    #    nghe duoc va ⛔ khong giau.
    #
    # ⭐ Van con MOT tran, nhung la tran KY THUAT cua `atempo`
    #    (`TRAN_KY_THUAT_ATEMPO` = 2.0, dinh nghia o dau tep nay) — qua tran do
    #    la TIENG RAC chu khong con la "tieng nhanh". `he_so_co_gian` luon
    #    >= 1.0 o day nen chi can mot tran TREN, ⛔ khong can `max()`.
    he_so_theo_ma: dict[str, float] = {}
    he_so_toc_da_ap: list[float] = []
    for d in (ban_ke.get("doan") or []):
        # ⛔ Dong DI THEO mang cung `he_so_co_gian` voi dong dau (mot tep, mot
        #    lan `atempo`) — dem no lan thu hai chi lam sai lech thong ke.
        if nan_thoi_luong.la_dong_theo_sau(d):
            continue
        ma = str(d["ma"])
        h = float(d.get("he_so_co_gian") or 1.0)
        h_ap = he_so_ap(h, tran_ky_thuat=TRAN_KY_THUAT_ATEMPO)
        if h_ap != h:
            log.warning(
                "asv timing_align: doan %s co he_so_co_gian=%.4f vuot tran KY "
                "THUAT cua atempo %.2f - ap %.4f de tranh tieng rac",
                ma, h, TRAN_KY_THUAT_ATEMPO, h_ap)
        he_so_toc_da_ap.append(float(h_ap))
        if h_ap > nan_cho_vua.tran_co_gian():
            log.warning(
                "timing_align: doan %s tang toc %.3f vuot tran %.3f",
                ma, h_ap, nan_cho_vua.tran_co_gian())
        he_so_theo_ma[ma] = h_ap

    # ⭐ Nấc cứu cuối (Task 8, chốt 26/09): chủ dự án chốt thứ tự cứu là
    #    (b) nới biên lần hai (`thoi_gian.lap_ke_hoach` đã mượn
    #    `TY_LE_MUON_KHOANG_LANG` — xong ở đó) → (c) CHẤP NHẬN phần còn lệch,
    #    nhưng ⛔ không được IM. `dem_lech_cuoi` (hàm THUẦN, Task 16) đếm lại
    #    trên đúng `he_so_theo_ma` (h_ap) vừa dựng ở vòng lặp trên.
    so_doan_lech_cuoi, giay_lech_cuoi = dem_lech_cuoi(
        ban_ke.get("doan") or [], he_so_theo_ma)

    # ⛔ Loai cac `ma` DI THEO bang mot truong TUONG MINH (`nhom_theo_ma`), ⛔ KHONG
    #    bang "vang mat khoi `khoa_theo_ma`": hai chuyen khac han nhau va chi mot
    #    trong hai duoc phep im lang.
    #      di theo    -> tep cua nhom da co mot lop, bo qua  (binh thuong)
    #      thieu khoa -> NEM `Doan {ma} chua co tep tieng`   (khiem khuyet)
    #    Loc bang `in khoa_theo_ma` se bien ca hai thanh mot, va ca thu hai bien
    #    thanh mot doan tieng bi vut AM THAM.
    di_theo = nan_thoi_luong.nhom_theo_ma(ban_ke)
    dat = [d for d in (ke_hoach.get("doan") or [])
           if int(d.get("dai_ms") or 0) > 0 and str(d["ma"]) not in di_theo]
    if not dat:
        raise ThieuDauVao(_t('Kế hoạch thời gian không còn đoạn nào có tiếng.'))

    # 🔑 `tong_giay` la do dai NGUON, va o giai doan 1 do cung la do dai ban
    #    phoi: khong canh nao bi cat. Truoc b4 dong nay doc `ban_do.thoi_luong_ra`
    #    — mot con so NHO hon khi preset cat — va do la dung SU GHEP NOI ma thu
    #    tu moi xoa bo.
    tong_giay_ra = float(tong_giay)
    # V6 pha 23: ho so am thanh cua khach — vao van tay VA vao chuoi tron.
    from . import am_thanh, cai_dat as cd
    am = am_thanh.tu_cai_dat(cd.doc(run).am_thanh)
    vt = am_master.van_tay_master(
        van_tay_nen=khoa_nen.rsplit("/", 1)[-1][:32],
        van_tay_ke_hoach=van_tay_ke_hoach,
        phien_ban_ffmpeg_=nhap_media.phien_ban_ffmpeg(),
        am_thanh=am)

    hoi_huy = getattr(ctx, "is_cancelled", None) if ctx is not None else None

    with tempfile.TemporaryDirectory(prefix="asv-master-") as tam:
        thu_muc = Path(tam)
        nen = _duong_doc_duoc(kho, khoa_nen, thu_muc)

        cac_lo = []
        for n_lo, (i, j) in enumerate(am_master.chia_lo(len(dat))):
            duong, moc, he_so = [], [], []
            for d in dat[i:j]:
                ma = str(d["ma"])
                k = khoa_theo_ma.get(ma)
                if not k:
                    raise ThieuDauVao(
                        _t('Đoạn {ma} chưa có tệp tiếng.').format(ma=ma))
                duong.append(_duong_doc_duoc(kho, k, thu_muc / f"t{n_lo}_{ma}"))
                moc.append(int(d["dat_tai_ms"]))
                he_so.append(he_so_theo_ma.get(ma, 1.0))
            cac_lo.append(am_master.tron_lo(
                duong, moc, he_so, str(thu_muc / f"lo_{n_lo}.wav"),
                tong_giay=tong_giay_ra, hoi_huy=hoi_huy))

        dich = str(thu_muc / "master.wav")
        # ⭐ asv-final R-03: `ghim` hung bao cao ghim tran (dinh that cua BAN
        #    GIAO, da do bang chinh tham so ma hoa cua `ket_xuat`) va di thang
        #    sang `kiem_ban_ra` — do mot lan, ghi vao ho so giai doan.
        ghim: dict = {}
        am_master.tron_cuoi(nen, cac_lo, dich, tong_giay=tong_giay_ra,
                            hoi_huy=hoi_huy, am=am, ghim=ghim)

        do_duoc = am_master.kiem_ban_ra(
            dich, mong_doi_giay=tong_giay_ra,
            dung_sai_giay=hop_dong_v4.DUNG_SAI_DO_DAI_S, ghim=ghim)
        # ⭐ Ghi thu DA AP, khong chi thu khach chon: fade bi cat theo do dai ban
        #    phoi (`fade_ap_dung`), va mot lan cat khong ghi lai la mot lan lang le.
        fv, fr = am_master.fade_ap_dung(am, tong_giay_ra)
        do_duoc["am_thanh"] = {**am, "fade_vao": fv, "fade_ra": fr}
        # 🔑 Task 4 (chot 26/09): moi he so tang toc THAT SU da ap, ⛔ khong
        #    con bi kep im lang — xem chu thich o vong lap phia tren.
        do_duoc["he_so_toc_da_ap"] = he_so_toc_da_ap
        # ⭐ Nấc (c) của chủ dự án: chấp nhận lệch, nhưng ⛔ KHÔNG im. Hai con số
        #    này đi vào hồ sơ giai đoạn, nên "chấp nhận" là một quyết định NHÌN
        #    THẤY ĐƯỢC chứ không phải một sự vắng mặt.
        do_duoc["so_doan_lech_cuoi"] = int(so_doan_lech_cuoi)
        do_duoc["giay_lech_cuoi"] = round(float(giay_lech_cuoi), 3)

        khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                   stage=pipeline.TIMING_ALIGN, van_tay=vt,
                                   duoi="wav")
        with open(dich, "rb") as f:
            kho.put(khoa, f, content_type="audio/wav")

    return khoa, do_duoc, vt
