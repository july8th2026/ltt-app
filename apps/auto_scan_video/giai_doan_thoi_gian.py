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
#:    (`nan_cho_vua.co_gian_du_khong`: he_so = giay/NGAN_SACH tu 28/09 — B13-A2,
#:    truoc do la giay/khe — va chi tinh khi giay > mau so), nen chi can MOT tran
#:    tren, khong can `max()` cho bien duoi.
#: ⭐ **Bí danh từ 28/09 (B13-A4) — con số khai ở `thoi_gian.TRAN_KY_THUAT_ATEMPO`.**
#:    Từ A4 `thoi_gian.kiem()` phải cưỡng chế đúng trần này (`he_so_toc` nay là
#:    hệ số SẼ ĐƯỢC ÁP), nên nó phải sống ở module THUẦN. Tên ở đây giữ nguyên vì
#:    `giai_doan_qc_do_luong.py:169` và `test_4870` đọc nó qua tên này.
TRAN_KY_THUAT_ATEMPO = thoi_gian.TRAN_KY_THUAT_ATEMPO


def he_so_ap(h: float, *, tran_ky_thuat: float) -> float:
    """He so tang toc THAT SU se ap cho MOT doan (nac cuu (c), Task 4/8/16).

    Ham THUAN — khong doc tep, khong goi ffmpeg, khong cham kho. Chi kep ve
    `tran_ky_thuat` (tran KY THUAT cua `atempo`, qua do WSOLA ra TIENG RAC).
    ⛔ KHONG kep ve `thoi_gian.TRAN_TANG_TOC` — do la CHINH SACH SAN PHAM (chu
    du an chot 26/09: vuot tran do thoai mai, tran chi con la CANH BAO, khong
    phai mot cong). Vi `h` luon >= 1.0 (`nan_cho_vua.co_gian_du_khong` chi tinh
    khi `giay` > mau so — tu 28/09 mau so la NGAN SACH, ⛔ khong con `khe`) nen
    chi can MOT tran TREN, khong can `max()` cho bien duoi.
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
    (`giay/h_ap > khe`) — dieu kien `h_ap != h` tranh dem nham mot sai so lam
    tron dau phay dong o bien nhu mot cho LECH.

    🔴 **Tu 28/09 (B13-A2) `he_so_co_gian = giay / NGAN_SACH`, ⛔ khong con
       `giay / khe`.** Ban truoc cua chu thich nay khai mau so cu, va he qua la:
       mot doan KHONG bi kep nay cho `giay / h = ngan_sach`, tuc **> `khe`** khi
       doan ay co muon khoang lang. Dieu kien `h_ap == h -> continue` o duoi giu
       cho cac doan ay ⛔ khong bi dem, nen con so tra ve van dung.

    ⚠️ **Nhung voi doan BI KEP (`h > TRAN_KY_THUAT_ATEMPO`) thi phep so sanh o
       day bay gio CHAT HON su that**: no do `giay_sau` voi `khe` trong khi ngan
       sach thi hanh rong hon. ⇒ `so_doan_lech_cuoi` la mot cận TRÊN — no ⛔
       khong bao gio bo sot, nhung no co the dem mot doan that su van vua ngan
       sach. Giu vay CO Y: `ban_ke` ⛔ khong mang `ngan_sach` tren tung dong (chi
       `khe` — `giai_doan_giong._ke_nan`), va sai ve phia BAO NHIEU HON o mot con
       so "chap nhan lech nhung khong im" la sai ve phia an toan. Muon chinh xac
       thi phai them `ngan_sach` vao `ban_ke`, va do la mot bat bien cua
       `nan_thoi_luong` — ⛔ khong phai viec cua ham nay.

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


def he_so_da_ap_theo_ma(ban_ke: dict) -> dict[str, float]:
    """`{ma: he so `atempo` THAT SU se ap}` — MOT cho tinh, MOT cho log.

    🔴 **Vi sao ham nay ton tai (B13-A4, 28/09).** Tu A4 chinh
       `thoi_gian.lap_ke_hoach` cung phai biet he so nay (no chua cho theo
       `dai / he_so`), nen con so ay duoc DOC o hai cho. Tinh lai o cho thu hai
       la dat hai ban sao cua mot chinh sach canh nhau — va ke nay da tra gia
       dung cho do: ke hoach noi `1,15`, ban phoi ap `1,0`, va ⛔ khong ai doi
       chieu.

    🔑 **Tran la CANH BAO, ⛔ khong phai mot cong (chu du an chot 26/09).**
       Truoc day `he_so_co_gian` cua mot doan `CAN_SUA` bi KEP ve tran THIET KE
       (`thoi_gian.TRAN_TANG_TOC`) — mot doan tran qua trai bi dat SAI CHO trong
       im lang. Nay: ap DUNG he so can, chi `log.warning` khi vuot tran thiet ke.

    ⭐ Van con MOT tran, va la tran KY THUAT cua `atempo`
       (`thoi_gian.TRAN_KY_THUAT_ATEMPO` = 2,0) — qua do la TIENG RAC chu ⛔ khong
       con la "tieng nhanh". `he_so_co_gian` luon >= 1.0 nen chi can mot tran
       TREN, ⛔ khong can bien duoi.

    ⛔ **Dong DI THEO ⛔ KHONG co mot muc rieng.** 2–4 `ma` cua mot khe da gop
       tro vao CUNG mot tep, va tep ay duoc `atempo` MOT lan
       (`nan_thoi_luong.la_dong_theo_sau`). Dem no lan thu hai lam sai lech thong
       ke; TRON no lan thu hai nghe thanh tieng vang.
    """
    ra: dict[str, float] = {}
    for d in (ban_ke.get("doan") or []):
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
        if h_ap > nan_cho_vua.tran_co_gian():
            log.warning(
                "timing_align: doan %s tang toc %.3f vuot tran %.3f",
                ma, h_ap, nan_cho_vua.tran_co_gian())
        ra[ma] = h_ap
    return ra


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



#: Bon KHIEM KHUYET khac loai ma mot `giay <= 0` o ban ke tieng CO THE mang.
#:
#: 🔴 **Chung ⛔ KHONG duoc gom vao mot thong diep, va day la mot bai hoc da tra
#:    gia (27/09).** Mot tep tieng **tot** (138.284 byte, ffprobe **1,44 giay**)
#:    bi bao la *"Doan seg_0004 chua co tieng"* — vi `giai_doan_giong.
#:    _doan_con_dung` tra `0.0` khi kho ⛔ khong co `local_path` (kho production
#:    la R2, `LocalStorage` thi CO, nen moi phep kiem cuc bo do dung). Thong diep
#:    ay chi tay vao **doan tieng** trong khi loi nam o **phep DO**, va nguoi soat
#:    duoi sai ba gia thuyet lien tiep truoc khi tim ra.
#:
#: ⭐ `timing_align` co du bang chung trong tay de noi that: dong ban ke mang
#:    `khoa` cua tep tieng. `khoa` CO ma `giay = 0` thi do la **phep do hong**, ⛔
#:    khong phai *"chua co tieng"* — va hai chuyen do sua o hai noi khac nhau.
THIEU_DONG = "thieu_dong_ban_ke"
THIEU_TEP = "thieu_khoa_tep_tieng"
KHONG_DO_DUOC = "thoi_luong_khong_do_duoc"
IM_LANG_RONG = "khoang_lang_khong_duoc_sinh"


def do_dai_tieng(muc, ban_ke) -> dict[str, float]:
    """`{ma: giay}` cua ban ke tieng — va NEM dung ten khi mot so `0` vo nghia.

    ⛔ **Khong phai mot dict comprehension.** `float(d.get("giay") or 0.0)` gop
       *"⛔ khong co khoa `giay`"*, *"`giay = None`"* va *"`giay = 0.0`"* thanh MOT
       gia tri, roi `thoi_gian.lap_ke_hoach` doc gia tri ay va noi *"Doan {ma}
       chua co tieng"* cho ca bon khiem khuyet — ba trong bon la loi o cho khac.

    ⭐ Bon thong diep, bon cho sua:
         `THIEU_DONG`     ban ke va `content.json` lech nhau (thuong nguon)
         `THIEU_TEP`      dong co ma ⛔ khong co `khoa`  — that su chua co tieng
         `KHONG_DO_DUOC`  CO `khoa` ma `giay = 0`        — phep DO hong
         `IM_LANG_RONG`   co `im_lang` ma `giay = 0`     — khoang lang chua sinh

    ⚠️ `im_lang` la co cua `voice_synthesis`: mot doan CO Y im lang van co MOT
       tep khoang lang **dai dung bang khe** (`giay > 0`), nen `im_lang` + `giay
       = 0` la mot khiem khuyet **khac han** — khoang lang ⛔ khong duoc sinh.
    """
    theo_ma: dict[str, dict] = {}
    for d in ((ban_ke or {}).get("doan") or []):
        theo_ma[str(d.get("ma") or "")] = d

    for m in (muc or []):
        ma = str((m or {}).get("ma") or "")
        dong = theo_ma.get(ma)
        if dong is None:
            raise ThieuDauVao(_t(
                'Bản kê tiếng thiếu hẳn dòng cho đoạn {ma} ({ly_do}): bản kê và '
                'bản dịch lệch nhau — đoạn này chưa từng được giao cho máy sinh '
                'tiếng.').format(ma=ma, ly_do=THIEU_DONG))

        co_khoa_giay = "giay" in dong
        tho = dong.get("giay")
        giay = 0.0
        if co_khoa_giay:
            try:
                giay = float(tho or 0.0)
            except (TypeError, ValueError):
                giay = 0.0
        if giay > 0:
            continue

        mo_ta = repr(tho) if co_khoa_giay else "(thieu khoa 'giay')"
        khoa = str(dong.get("khoa") or "")
        if dong.get("im_lang"):
            raise ThieuDauVao(_t(
                'Đoạn {ma} được khai CỐ Ý im lặng nhưng bản kê ghi thời lượng '
                '{tho} ({ly_do}): khoảng lặng dài bằng khe chưa được sinh ở '
                'voice_synthesis.').format(ma=ma, tho=mo_ta,
                                           ly_do=IM_LANG_RONG))
        if khoa:
            log.error(
                "asv timing_align: doan %s CO tep tieng %s ma ban ke ghi "
                "thoi luong %s - phep DO o voice_synthesis hong (kho khong co "
                "local_path?), KHONG phai doan thieu tieng", ma, khoa, mo_ta)
            raise ThieuDauVao(_t(
                'Đoạn {ma} CÓ tệp tiếng {khoa} nhưng bản kê ghi thời lượng '
                '{tho} ({ly_do}): phép ĐO thời lượng ở voice_synthesis hỏng, '
                'đoạn tiếng không hề thiếu.').format(
                    ma=ma, khoa=khoa, tho=mo_ta, ly_do=KHONG_DO_DUOC))
        raise ThieuDauVao(_t(
            'Đoạn {ma} chưa có tệp tiếng: bản kê không có khoá nào cho nó '
            '({ly_do}).').format(ma=ma, ly_do=THIEU_TEP))

    return {str(d.get("ma") or ""): float(d.get("giay") or 0.0)
            for d in ((ban_ke or {}).get("doan") or [])}


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc ban dich + do dai tieng THAT -> ke hoach dat doan."""
    tl_vb, ban_ke, cs_vb, cs_ke = _dau_vao(db, kho, run)

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(20, _t('Đang lập kế hoạch thời gian'))

    # 🔑 Do dai THAT cua tung tep tieng, khong phai do dai uoc tinh tu so ky tu.
    #    Mot phep uoc o day se lech, va lech tich luy — dung thu ma ca mo hinh
    #    no trong ADR-003 sinh ra de kiem soat.
    #
    # 🔴 **⛔ KHONG mot dict comprehension o day (27/09).** `float(... or 0.0)`
    #    gop bon khiem khuyet khac loai thanh MOT so `0`, va thong diep ha nguon
    #    (`thoi_gian.lap_ke_hoach`: *"Doan {ma} chua co tieng"*) chi tay vao doan
    #    tieng trong khi ba trong bon loi nam o cho khac. Xem `do_dai_tieng`.
    do_dai = do_dai_tieng(tl_vb.get("muc") or [], ban_ke)

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
    # ══ B13-A4 (28/09): ke hoach chua cho theo he so SE DUOC AP ═════════
    #
    # 🔴 **Thu tu la mot phan cua ban va.** `he_so_da_ap` phai dung TRUOC
    #    `lap_ke_hoach`, vi tu A4 ke hoach doc no de biet moi doan se dai bao
    #    nhieu SAU `atempo`. Truoc A4, `lap_ke_hoach` tu tinh mot `he_so_toc`
    #    rieng ma ⛔ khong ai thi hanh ⇒ 12 doan bi chua cho hep hon tep that.
    he_so_da_ap = he_so_da_ap_theo_ma(ban_ke)
    ke_hoach = thoi_gian.lap_ke_hoach(
        tl_vb.get("muc") or [], do_dai, tong_giay=tong_giay, che_do=che_do,
        nhom_gop=nan_thoi_luong.nhom_theo_ma(ban_ke),
        he_so_da_ap=he_so_da_ap)

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
        van_tay_ke_hoach=vt, he_so_theo_ma=he_so_da_ap, ctx=ctx)
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
                   tong_giay: float, van_tay_ke_hoach: str,
                   he_so_theo_ma: dict[str, float], ctx=None):
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
    # ⭐ `he_so_theo_ma` do NGUOI GOI dung (`chay`) va truyen vao — mot cho
    #    tinh, mot cho log. Xem `he_so_da_ap_theo_ma`: tu B13-A4 chinh
    #    `thoi_gian.lap_ke_hoach` cung phai doc no, nen hai cho khong duoc
    #    tinh lai (hai ban sao cua mot chinh sach la cho se troi).
    he_so_toc_da_ap: list[float] = list(he_so_theo_ma.values())

    # ══ B13-B3/B4 (28/09): HAI máy tăng tốc, và chỉ MỘT cái được thi hành ════
    #
    # 🔴 **`ke_hoach.he_so_toc` ⛔ KHÔNG BAO GIỜ trở thành một `atempo` thứ hai.**
    #    Đọc 28/09, ba neo:
    #      · `ket_xuat.dung_lenh` (`ket_xuat.py:214-216`) chỉ nạp HAI đầu vào —
    #        `duong_video` và `duong_master` — và map `nhan_tieng = "1:a:0"`.
    #        `duong_lop` **chỉ** bị đếm để đối chiếu độ dài (`:173`), ⛔ không
    #        xuất hiện trong `cmd`;
    #      · `am_master.tron_lo` nhận `he_so` lấy TỪ `he_so_theo_ma` mà `chay`
    #        dựng bằng `he_so_da_ap_theo_ma`, tức từ `ban_ke.he_so_co_gian` —
    #        ⛔ không từ kế hoạch;
    #      · `ban_dung.py:158` vẫn chép `he_so_toc` vào từng lớp với chú thích
    #        *"Trinh render chi ap atempo khi > 1"*, và `docs/auto_scan_video/
    #        reports/13_REPORT.md:190` khai đúng thiết kế CŨ ấy (*"belongs to
    #        RENDER"*). Pha 16 dựng bản phối và trình render thôi trộn lớp ⇒ ô
    #        `he_so_toc` **mồ côi** từ đó.
    #
    # ⇒ Nên `1,15 × 1,3333 = 1,53` ⛔ KHÔNG xảy ra được, và một cái `raise` cho
    #   nó sẽ là một nhánh ⛔ không bao giờ chạy — đúng thứ `ma-phong-thu-cho-ca-
    #   khong-the-xay-ra` cấm. Cái CÓ THẬT là chiều NGƯỢC LẠI: một đoạn kế hoạch
    #   định nén 1,15 để trả nợ được trộn ở `he_so_co_gian` (thường 1,0), tức
    #   **dài hơn chỗ kế hoạch chừa cho nó**, và `thoi_gian.kiem` ⛔ không bắt
    #   được vì nó kiểm chồng lấn trên `dai_ms` ĐÃ chia cho `he_so_toc`.
    #
    # ⭐ Nên bất biến ở đây là bất biến RẺ và SỐNG: ĐẾM chỗ lệch và nói to
    #   (`log.warning`), rồi đưa CẢ HAI đại lượng vào `master` dưới hai cái tên
    #   ⛔ không đọc lẫn được. ⛔ Không `raise`: khi bộ đếm này được viết, lượt đã
    #   đo có 12 đoạn lệch, nên `raise` sẽ làm đỏ mọi lượt chạy thật.
    #
    # 🔑 **Và A4 (28/09 chiều) đã đưa con số ấy về 0.** `thoi_gian.lap_ke_hoach`
    #    nay MIRROR `he_so_da_ap`, nên kế hoạch và bản phối nói cùng một hệ số.
    #    ⇒ Bộ đếm này ⛔ KHÔNG chết đi vì thế — nó là **phép chứng minh** A4 còn
    #    ăn: một con số đếm ra `0` **sau khi từng đếm ra 12** là bằng chứng, và
    #    nó sẽ lớn lên ngay lần đầu ai đó làm hai bên lệch lại.
    # ⭐ Phép ĐO là một hàm THUẦN ở `thoi_gian` — ⛔ không viết số học ở đây.
    #    Hai lực: (i) `doi_chieu_he_so_toc` kiểm được mà ⛔ không cần một lượt trộn
    #    nào; (ii) bánh cóc `test_2018::test_he_so_toc_KHONG_bi_kep_ve_tran` đọc
    #    **cách gõ** — nó đỏ khi module này gọi cả `min` lẫn `max`, kể cả khi
    #    phép `max` ấy ⛔ không kẹp gì cả. Giữ số học ra ngoài đây là cách giữ
    #    bánh cóc ấy CÒN NGHĨA thay vì nới nó (`banh-coc-do-CACH-GO-...`).
    doi_chieu = thoi_gian.doi_chieu_he_so_toc(
        {str(d["ma"]): float(d.get("he_so_toc") or 1.0)
         for d in (ke_hoach.get("doan") or [])},
        he_so_theo_ma)
    for ma, h_ke, h_ap in doi_chieu["lech"]:
        log.warning(
            "asv timing_align: doan %s — ke hoach dat cho no theo he_so_toc="
            "%.4f nhung ban phoi ap he_so_co_gian=%.4f. Tieng se %s cho ke "
            "hoach chua; `ke_hoach.he_so_toc` KHONG duoc ap lam atempo lan hai "
            "(ket_xuat.dung_lenh chi map master)", ma, h_ke, h_ap,
            "DAI hon" if h_ap < h_ke else "NGAN hon")

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
        # 🔴 `bien_tap` (27/09): ban ma hoa THU trong `ghim_tran_phoi` phai di qua
        #    CUNG phep doi toc do voi `ket_xuat` (`atempo=toc`), neu khong no do
        #    mot tin hieu KHAC tin hieu khach nhan. Do tren `asvr_f997f794`:
        #    ban phoi -14,86 LUFS, ban giao -15,09 => `atempo` + AAC an 0,23 LU,
        #    va 0,23 LU ay la dung khoang cach con lai cua T4.
        from . import cai_dat as _cd

        bt_render = (_cd.doc(run).bien_tap or None)
        am_master.tron_cuoi(nen, cac_lo, dich, tong_giay=tong_giay_ra,
                            hoi_huy=hoi_huy, am=am, ghim=ghim,
                            bien_tap=bt_render)

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
        # ⭐ B15 (28/09): VÌ SAO khách mất câu — NỢ hay ĐUÔI (T2)? Đo 28/09 cho
        #    thấy hai cỗ máy cắt độc lập bị gộp vào MỘT số `so_doan_bi_cat`:
        #    tắt trần nợ mà số ấy VẪN là 1 ở `k = 1,15`, vì popper đuôi
        #    (`thoi_gian.py` cuối `lap_ke_hoach`) mới là thứ cưỡng chế T2.
        do_duoc["so_doan_cat_vi_no"] = int(ke_hoach.get("so_doan_cat_vi_no") or 0)
        do_duoc["so_doan_cat_vi_duoi"] = int(
            ke_hoach.get("so_doan_cat_vi_duoi") or 0)
        do_duoc["so_doan_lech_cuoi"] = int(so_doan_lech_cuoi)
        do_duoc["giay_lech_cuoi"] = round(float(giay_lech_cuoi), 3)
        # ══ B13-B4 (28/09): HAI đại lượng ⛔ KHÔNG còn đứng cạnh nhau dưới hai
        #    cái tên nghe như MỘT ══════════════════════════════════════════════
        #
        # 🔴 **Cái bẫy, đo trên `asvr_47327a869a8f4597960048f09064740`:**
        #
        #        timing_align.he_so_toc_lon_nhat   = 1,15    so_doan_tang_toc = 12
        #        timing_align.master.he_so_toc_da_ap: n=69, max = 1,3333
        #
        #    Hai dòng trong CÙNG một `outputs`, **hai tập khác nhau**, và
        #    `1,15 < 1,3333` ⇒ ai đọc báo cáo sẽ kết luận trần đã giữ.
        #
        # ⛔ **Vì sao ⛔ KHÔNG đổi tên `he_so_toc_lon_nhat`/`so_doan_tang_toc`**
        #    (hai khoá PHẲNG, do `thoi_gian.tom_tat` sinh): chúng nằm trong
        #    `asv_doi_soat.KHOA_BO_QUA_CO_Y["timing_align"]`, và `test_408` chốt
        #    HAI chiều — một khoá mới ⛔ không khai là đỏ, một khoá đã khai mà
        #    ⛔ không ai ghi cũng đỏ. Đổi tên ở đây buộc phải sửa
        #    `tools/asv_doi_soat.py`, thứ ⛔ KHÔNG thuộc làn này (B13 §7.0 giao
        #    `tools/` cho L3). ⇒ Bản vá đi đường LỒNG: `master` là MỘT khoá
        #    trong `KHOA_CAN`, nên mọi khoá con của nó thêm được tự do.
        #
        # ⭐ Bốn con số, hai vế, tên nói thẳng vế nào: `_ke_hoach` là thứ
        #    `lap_ke_hoach` ĐỊNH làm (và ⛔ không ai thi hành), `_da_ap` là thứ
        #    `am_master.tron_lo` THẬT SỰ áp. Đọc một mình `master` là đủ để trả
        #    lời *"trần có giữ không"* mà ⛔ không phải ghép hai tầng.
        for _k, _v in doi_chieu.items():
            # ⛔ `lech` là danh sách để LOG, ⛔ không phải một phép đo — nó mang
            #    `ma`, và `outputs` của giai đoạn này đã có `he_so_toc_da_ap`.
            if _k != "lech":
                do_duoc[_k] = _v
        khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                   stage=pipeline.TIMING_ALIGN, van_tay=vt,
                                   duoi="wav")
        with open(dich, "rb") as f:
            kho.put(khoa, f, content_type="audio/wav")

    return khoa, do_duoc, vt
