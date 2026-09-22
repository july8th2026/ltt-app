"""Giai doan `edit_plan` — chot quyet dinh hinh anh truoc khi tieu tien tieng.

Giai doan nay khong tra tien khi preset la `localize_preserve_picture`: khong co
canh nao duoc cat, nen khong co gi de hoi VLM. Do la mot **duong re re tien** co
chu dinh, khong phai mot loi tat.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (ai, ban_bien_tap, canh as canh_mod, hieu_canh as hc, hop_dong_v4,
               lat_cat)
from .giai_doan_media import ThieuNguon

log = logging.getLogger(__name__)

#: Phien ban MA cua giai doan, di vao van tay.
#:
#: 🔑 **2 tu pha 27**: truoc do giai doan nay truyen `hieu = ()` cho `lap_ban`,
#:    nen moi ban bien tap la mot ban "khong co bang chung — giu het". Mot ban
#:    bien tap sinh boi ma CU va mot ban sinh boi ma NAY tra loi hai cau hoi
#:    khac nhau, va van tay phai noi duoc dieu do.
PHIEN_BAN_MA = 2


class ThieuChiMuc(ThieuNguon):
    """Chua co chi muc canh de lap ban bien tap."""


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Lap `BanBienTap` va tra ve phan de promote.

    🔑 Thu tu o day la mot phan cua hop dong: **quyet dinh hinh anh chot TRUOC**,
       roi ban chep loi moi duoc loc ve phan giu lai. Doi thu tu la quay lai dung
       `V4-R07` — dich va tra tien cho nhung cau thuoc canh se bi cat.
    """
    from . import cai_dat as cd, features

    preset = cd.doc(run).preset

    tt = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    thoi_luong = float(((tt.outputs or {}) if tt else {}).get("thoi_luong") or 0.0)

    # ── Chi muc canh ────────────────────────────────────────────────────────
    #
    # ⛔ `PRESET_GIU_HINH` khong can chi muc chi tiet: khong canh nao bi cat, nen
    #    mot chi muc mot-canh la du va dung. Chay tach canh o day la tra tien
    #    ffmpeg cho mot cau tra loi khong ai doc.
    if preset == hop_dong_v4.PRESET_GIU_HINH:
        if thoi_luong <= 0:
            raise ThieuChiMuc(_t('Chưa có bản media để phân tích cảnh.'))
        ci = canh_mod.ChiMucCanh(
            (canh_mod.Canh("canh_0001", 0.0, thoi_luong),), thoi_luong,
            ghi_chu={"bo_qua_tach_canh": "preset giu nguyen hinh"})
        hieu = ()
    else:
        # 🔑 LAT CAT: luot NOI TIEP dung lai chi muc canh cua luot dau (luu
        #    trong con tro) thay vi tach canh lai tren ca video 120 phut — vua
        #    tiet kiem mot lan ffmpeg dai, vua bao dam ma canh KHONG doi giua
        #    hai luot (diem chot khoa theo ma canh).
        lc = (lat_cat.mo(db, run, "edit_plan", du_phong_s=0.0)
              if db is not None and run is not None else None)
        cu = (lc.trang_thai.get("chi_muc")
              if lc is not None and lc.noi_tiep else None)
        if cu:
            ci = canh_mod.tu_dict(cu)
        else:
            duong = _nguon_soi_duoc(db, kho, run)
            ci = canh_mod.phan_tich(duong, thoi_luong=thoi_luong,
                                    hoi_huy=getattr(ctx, "is_cancelled", None))
        canh_mod.kiem_chi_muc(ci)

    ban_ghi = _ban_ghi(db, kho, run)
    # 🔑 **Doc canh nam SAU khi co ban chep loi, va truoc `lap_ban`.**
    #    `pipeline.CHUOI` da dat `sau=(TRANSCRIBE,)` cho dung dieu nay: nguong
    #    bo cua mot canh CO loi thoai cao hon han, nen bang chung thi giac chi co
    #    nghia khi ta da biet canh nao co thoai.
    if preset == hop_dong_v4.PRESET_GIU_HINH:
        hieu, hong = (), []
    else:
        hieu, hong = _doc_cac_canh(db, kho, run, ci, ban_ghi, ctx)
        _chot_do_phu(preset, ci, hieu, hong)
    ban = ban_bien_tap.lap_ban(preset=preset, chi_muc=ci,
                               hieu_canh=hieu, ban_ghi=ban_ghi)

    # ── Luu ban + chi muc thanh MOT artifact ───────────────────────────────
    #
    # ⭐ Mot tep chu khong hai: ban bien tap va chi muc canh khong doc duoc tach
    #    roi — mot quyet dinh "cat canh_0007" vo nghia neu khong biet canh do la
    #    khoang thoi gian nao. Luu roi la mo mot duong de hai nua lech phien ban.
    import io

    from . import assets

    vt = van_tay_ban(ban)
    goi = json.dumps({"ban": ban.sang_dict(), "chi_muc": _chi_muc_dict(ci)},
                     ensure_ascii=False, sort_keys=True).encode("utf-8")
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage="edit_plan", van_tay=vt, duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu bản biên tập'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt}],
        "ban": ban,
        "chi_muc": ci,
        "tom_tat": {
            "preset": preset,
            "so_canh": len(ci.canh),
            "so_giu": len(ban.cac_ma_giu),
            "so_cat": len(ban.cac_ma_cat),
            "van_tay_ban": ban.van_tay(),
            "so_canh_da_doc": len(hieu),
            # 🔑 **Canh doc HONG phai nhin thay duoc trong bang chung cua luot
            #    chay, khong chi trong log.** Luot nen v3 (23/09) ghi
            #    `so_canh_da_doc: 4` cho 6 canh va khong mot chu nao noi hai
            #    canh kia hong the nao — nen "smart_localize khong cat gi" doc
            #    ra giong het mot quyet dinh dung dan.
            "so_canh_hong": len(hong),
            "canh_hong": list(hong),
            "do_phu_bang_chung": (round(len(hieu) / len(ci.canh), 4)
                                  if ci.canh else 0.0),
            **dict(ban.ghi_chu),
        },
    }


#: So lan hoi VLM ve MOT canh khi phan hoi sai hinh dang. `2` = mot lan hoi +
#: mot lan hoi lai. Xem ghi chu trong `_doc_cac_canh`.
SO_LAN_DOC_CANH = 2

#: 🔴 **`smart_localize` doi bang chung cho MOI canh — khong phai "phan lon".**
#:
#:    Mot canh khong co bang chung **luon duoc GIU**
#:    (`ban_bien_tap._quyet_dinh_mot_canh`), va do la quyet dinh dung: cat mu
#:    nguy hiem hon giu thua. Nhung hau qua o cap SAN PHAM thi khong dung: khach
#:    bam "cat thong minh", tra tien cho duong cat thong minh, va nhan ve mot
#:    ban ma hoa lai cua chinh video ho — giong het `localize_preserve_picture`,
#:    khong mot loi nao noi vi sao.
#:
#:    Do that 23/09 (luot nen v3): 2/6 canh doc hong ⇒ `so_cat = 0/6` ⇒ khac
#:    biet san pham giua hai preset **bien mat**, va giai doan bao `succeeded`.
#:
#: ⭐ Vi sao 1,0 chu khong phai mot nguong hieu chinh: mot nguong 0,8 tra loi
#:    cau *"bao nhieu phan tram la du"* — mot cau khong ai do duoc va khong ai
#:    do cho. `1,0` tra loi mot cau khac han: *"co lo hong im lang nao khong"*.
#:    Do la mot bat bien, khong phai mot tham so.
#:
#: ⭐ Va cho DUNG la re: `edit_plan` chay TRUOC `content_process` va
#:    `voice_synthesis`, nen mot lan tu choi o day tra lai cho khach ca doan
#:    dat nhat cua chuoi (84 + 943 giay o luot nen v3).
#:
#: ⚠️ **Nen tang KHONG tu dong thu lai loi nay**, va do la co y.
#:    `ThieuBangChungCanh` ke thua `ThieuNguon` ⇒ `loi.phan_loai` tra
#:    `THIEU_THUONG_NGUON` ⇒ khong thu lai. Lan hoi lai da xay ra roi, ngay
#:    trong giai doan (`SO_LAN_DOC_CANH`); mot vong thu lai thu hai o tang job
#:    chi la cung mot phep goi, cung mot khung hinh, them mot hoa don. Nguoi
#:    quyet dinh chay lai la KHACH, va thong diep noi ro ho co hai lua chon.
PHU_BANG_CHUNG_TOI_THIEU = 1.0


class ThieuBangChungCanh(ThieuNguon):
    """`smart_localize` khong doc duoc het cac canh — khong lap ban cat duoc."""


def _chot_do_phu(preset: str, ci, hieu, hong) -> None:
    """Chan `smart_localize` giao mot ban "giu het" vi doc canh hong.

    ⛔ Khong ap cho `PRESET_GIU_HINH`: preset do khong doc canh nao ca, va mot
       do phu 0 o do la dung hop dong chu khong phai mot lo hong.
    """
    so_canh = len(getattr(ci, "canh", ()) or ())
    if preset != hop_dong_v4.PRESET_CAT_THONG_MINH or not so_canh:
        return
    phu = len(hieu) / so_canh
    if phu + 1e-9 >= PHU_BANG_CHUNG_TOI_THIEU:
        return
    thieu = so_canh - len(hieu)
    log.warning("edit_plan: %d/%d canh khong co bang chung (%s)",
                thieu, so_canh, [h.get("loai") for h in hong][:8])
    raise ThieuBangChungCanh(
        _t('Không đọc được hình của {thieu}/{tong} cảnh nên chưa thể cắt thông '
           'minh. Hãy chạy lại, hoặc chọn chế độ giữ nguyên hình.')
        .format(thieu=thieu, tong=so_canh))


def _doc_cac_canh(db, kho, run, ci, ban_ghi: dict, ctx) -> tuple:
    """Hoi VLM ve TUNG canh. Tra ve `(tuple[HieuCanh, ...], list[dict] canh hong)`.

    🔑 **Hai ve, khong mot.** Truoc 23/09 ham nay chi tra ve cac canh DOC DUOC,
       nen mot canh hong va mot canh "VLM noi khong chac" ra ngoai giong het
       nhau — va `so_cat = 0` doc ra giong het mot quyet dinh dung dan. Ve thu
       hai la thu bien "khong cat gi" thanh mot cau noi duoc.

    🔴 **Day la nguoi goi ma pha 11 khong co.** `hieu_canh.py` da co du prompt,
       luoc do, van tay va kiem nghiem tu pha 11; `canh.lenh_rut_khung` da co tu
       cung luc; `ai.goi_tinh_tien` da co cua chan ngan sach va so cai. Bon manh
       do deu co test xanh va **khong manh nao duoc noi voi manh nao** — kiem
       toan pha 26 dem duoc nam truong hop cung hinh dang nay va goi no la mot
       thoi quen chu khong phai nam loi roi rac.

    ## Ba nguyen tac, va ca ba deu la "hong mot canh khong duoc lam hong ca lan chay"

    1. **Diem chot theo CANH.** Moi canh la mot `AsvWorkItem` voi
       `item_key = ma canh`, van tay gom prompt/luoc do/so khung/ngu canh. Chay
       lai thi canh da doc duoc **doc lai tu `outputs`**, khong hoi model lan
       hai. Do la loi hua o docstring dau `hieu_canh.py`, va truoc pha 27 khong
       co ma nao thuc hien no.

    2. **Mot canh hong thi bo canh do, khong bo lan chay.** Khung hong, phan hoi
       sai luoc do, model tu choi — tat ca deu thanh "khong co bang chung ve
       canh nay", va `ban_bien_tap._quyet_dinh_mot_canh` **giu** khi khong co
       bang chung. Cat mu nguy hiem hon giu thua.

    3. ⛔ **Nhung mot canh da doc va tra ve rac VAN da ton tien.**
       `ai.goi_tinh_tien` ghi so cai o ca ba nhanh truoc khi ta thay ket qua,
       nen viec bo qua ket qua o day khong lam bay but toan nao — yeu cau 5 cua
       pha 11.
    """
    from . import features, su_dung as sd, pipeline

    canh = list(getattr(ci, "canh", ()) or ())
    if not canh or db is None or run is None:
        return (), []

    huy = getattr(ctx, "is_cancelled", None) if ctx is not None else None
    duong = _nguon_soi_duoc(db, kho, run)
    ra: list = []
    # 🔑 **Canh doc HONG, ghi ra ngoai.** Xem `SO_LAN_DOC_CANH` va `chay`.
    hong: list = []

    # 🔑 LAT CAT (`lat_cat.py`). Don vi te nhat = rut moi khung (moi khung mot
    #    `ffmpeg` co tran `CHO_RUT_KHUNG_S`) + mot lan hoi VLM.
    so_khung_max = max((len(getattr(c, "khung", ()) or ()) for c in canh),
                       default=0)
    lc = lat_cat.mo(db, run, pipeline.EDIT_PLAN,
                    du_phong_s=(so_khung_max * CHO_RUT_KHUNG_S
                                + lat_cat.timeout_goi_ai(ai.DOC_CANH)
                                + lat_cat.DU_PHONG_NGOAI_GOI_S))
    trang_thai = {"chi_muc": _chi_muc_dict(ci)}

    for i, c in enumerate(canh):
        if huy is not None and huy():
            raise ThieuChiMuc(_t('Lần chạy đã bị hủy.'))
        lc.kiem(vi_tri=i, trang_thai=trang_thai)

        ngu_canh = hc.ngu_canh_cho_canh(ban_ghi or {}, c.bat, c.ket)
        so_khung = len(getattr(c, "khung", ()) or ())
        van_tay = hc.van_tay_canh(c.ma, ngu_canh, so_khung,
                                  ban_bien_tap.NGUONG_BO)

        # ── Diem chot: canh nay da doc voi DUNG van tay nay chua? ──────────
        cu = features.don_vi_theo_khoa(db, run.id, pipeline.EDIT_PLAN, c.ma)
        if (cu is not None and str(cu.fingerprint or "") == van_tay
                and (cu.outputs or {}).get("de_xuat")):
            ra.append(hc.tu_dict(cu.outputs))
            continue
        # ⭐ Canh nam TRUOC con tro ma khong co diem chot = canh luot truoc da
        #    hoi va bo (mo ho / hong / sai luoc do). Lan chay mot mach cung chi
        #    hoi no MOT lan roi di tiep khong bang chung — luot noi tiep phai
        #    lam dung nhu vay, khong hoi (va tra tien) lan hai.
        if lc.noi_tiep and i < lc.vi_tri:
            continue

        sd.mo_don_vi(db, run, stage=pipeline.EDIT_PLAN, item_key=c.ma,
                     fingerprint=van_tay)
        # 🔴 **`commit` NGAY o day, truoc ffmpeg va truoc mang.**
        #
        #    `mo_don_vi` GHI, nen tu day toi lan commit ke tiep phien cua handler
        #    giu mot khoa ghi. Neu de nguyen thu tu cu, khoa do bi giu xuyen qua
        #    ca `_rut_khung` (ffmpeg, vai giay) lan `goi_tinh_tien` (mang toi may
        #    B, vai giay) — va `ctx.progress` cua vong sau, chay tren mot phien
        #    THU HAI, khong chen vao duoc.
        #
        #    Do duoc: ca bon lan `doc_canh` bi ghi `tu_choi`, ly do that su la
        #    `sqlite3.OperationalError: database is locked [SQL: UPDATE jobs SET`
        #    — tuc chinh `ctx.progress`, chu **model chua tu choi lan nao**.
        #
        # ⛔ Va day khong phai mot han che cua SQLite. Giu mot giao dich GHI
        #    xuyen qua mot loi goi mang la sai tren MOI backend: PostgreSQL cung
        #    giu ket noi va khoa hang y the, chi la no chiu lau hon truoc khi keu.
        #
        # ⭐ `giai_doan_noi_dung` da viet chinh bai hoc nay ra bang chu. No khong
        #    toi duoc ham nay vi ham nay duoc viet SAU khi doc no.
        db.commit()

        # Bao tien do SAU khi da nha khoa, khong truoc.
        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(5 + int(80 * i / max(1, len(canh))),
                         _t('Đang đọc cảnh'))

        khung = _rut_khung(duong, getattr(c, "khung", ()) or ())
        messages = hc.loi_nhac_canh(
            c.ma, ngu_canh, len(khung),
            # ⭐ Tin hieu DO DUOC, khong phai y kien: model can biet canh nay dai
            #    bao nhieu va co loi thoai khong de can nhac, va ca hai deu la so
            #    ta da co san — hoi model ve chung la tra tien de biet lai.
            tin_hieu={"bat": round(float(c.bat), 3),
                      "ket": round(float(c.ket), 3),
                      "dai_giay": round(float(c.ket) - float(c.bat), 3),
                      "so_khung": len(khung),
                      "co_thoai": bool(ngu_canh.strip())},
            khung=khung)

        h = None
        loi_cuoi = None
        # 🔴 **THU LAI mot lan khi phan hoi SAI HINH DANG, va chi khi do.**
        #
        #    Do 23/09 tren 18 canh cua phim nghiem thu: 8 luot hong, va **moi
        #    luot deu la mot phan hoi HTTP thanh cong co hinh dang sai** — 5 lan
        #    `"giữ"` co dau, 2 lan tra ve mot MANG, 1 lan `content` rong sau
        #    120 giay. Khong luot nao la "model tu choi".
        #
        # ⭐ Mot phan hoi rac la mot phan hoi RIENG LE: hoi lai cung mot khung
        #    hinh thuong ra dung ngay. Va gia cua mot lan hoi lai (mot luot
        #    `doc_canh`) re hon nhieu so voi hau qua — mot canh khong bang chung
        #    la mot canh **luon duoc giu**, tuc `smart_localize` am tham tro
        #    thanh `localize_preserve_picture`.
        #
        # ⛔ `AiMoHo` KHONG nam trong nhanh nay: khong biet model da chay chua,
        #    nen thu lai la co the tra tien hai lan cho mot viec.
        for lan in range(SO_LAN_DOC_CANH):
            try:
                kq = ai.goi_tinh_tien(
                    db, run, ai.DOC_CANH, messages,
                    stage=pipeline.EDIT_PLAN,
                    # ⭐ `item_key` phai KHAC nhau giua hai lan: `ma_dispatch`
                    #    la `(thao_tac, stage, item_key)` va `UNIQUE(run_id,
                    #    ma_dispatch)` se nuot but toan cua lan thu hai — tuc
                    #    mot luot DA tra tien bien mat khoi so cai.
                    item_key=c.ma if lan == 0 else f"{c.ma}:lai{lan}",
                    ctx=ctx)
                h = hc.doc_hieu_canh(kq, c.ma)
                break
            except ai.AiMoHo:
                # ⛔ Mo ho KHONG duoc nuot: khong biet model da chay chua, nen
                #    khong duoc thu lai va khong duoc danh dau xong. So cai da
                #    ghi `mo_ho`; canh nay di tiep khong co bang chung.
                loi_cuoi = ("AiMoHo", "mat ket noi sau khi gui")
                break
            except (ai.LuocDoSai, hc.HieuCanhError) as exc:
                # 🔑 **CHI hai lop nay duoc hoi lai, va ranh gioi khong tuy y.**
                #
                #    `LuocDoSai` / `HieuCanhError` = model **da tra loi**, chi
                #    la sai hinh dang. Do la thu re-roll duoc. Con `AiError`
                #    tran (may ban, provider tu choi, mat khoa) la mot cau tra
                #    loi ve TINH TRANG, khong phai mot phan hoi rac — hoi lai
                #    ngay lap tuc chi ton tien va lam cham ca giai doan.
                #
                # 🔑 Ghi **THONG DIEP**, khong chi ten lop. Nhat ky cua luot
                #    nghiem thu nen v3 chi co `(LuocDoSai)` / `(HieuCanhError)`,
                #    nen khong ai tra loi duoc *vi sao* — phai goi lai 18 luot
                #    that moi biet. Mot dong log day du thi khong.
                loi_cuoi = (type(exc).__name__, str(exc)[:200])
                log.warning("doc canh %s sai hinh dang lan %d/%d (%s: %s)",
                            c.ma, lan + 1, SO_LAN_DOC_CANH, *loi_cuoi)
            except ai.AiError as exc:
                loi_cuoi = (type(exc).__name__, str(exc)[:200])
                log.warning("doc canh %s hong (%s: %s) — KHONG hoi lai",
                            c.ma, *loi_cuoi)
                break
        if h is None:
            log.warning("doc canh %s khong co bang chung — GIU canh nay (%s)",
                        c.ma, (loi_cuoi or ("?", ""))[0])
            hong.append({"ma_canh": c.ma, "loai": (loi_cuoi or ("?", ""))[0],
                         "ly_do": (loi_cuoi or ("", ""))[1]})
            db.commit()
            lc.xong_mot()
            continue

        sd.danh_dau_xong(db, run, stage=pipeline.EDIT_PLAN, item_key=c.ma,
                         fingerprint=van_tay, outputs=h.sang_dict())
        # 🔑 `commit` sau MOI canh, khong doi den cuoi — cung ly do da ghi dai o
        #    `giai_doan_noi_dung`: mot `flush` khong song qua mot lan worker chet.
        db.commit()
        lc.xong_mot()
        ra.append(h)

    # 🔴 **Canh bi bo o mot LUOT LAT CAT TRUOC cung la canh khong bang chung.**
    #
    #    Vong tren chi thay nhung canh cua luot NAY: canh nam truoc con tro
    #    duoc `continue` tu som (dung — khong hoi va tra tien lan hai). Nen neu
    #    chi ghi `hong` tu vong, mot lan chay nhieu luot se bao `so_canh_hong:
    #    0` trong khi `so_canh_da_doc` van thieu — tuc bang chung tu mau thuan.
    #
    # ⭐ Bat bien de doc: `so_canh_da_doc + so_canh_hong == so_canh`, luon luon.
    da_co = {getattr(h, "ma_canh", "") for h in ra} | {d["ma_canh"] for d in hong}
    for c in canh:
        if c.ma not in da_co:
            hong.append({"ma_canh": c.ma, "loai": "luot_truoc",
                         "ly_do": "da hoi va bo o mot luot lat cat truoc"})

    return tuple(ra), hong


#: Tran thoi gian cua MOT lenh `ffmpeg` rut khung. Mot nguon cho ca lenh goi
#: lan phep tinh du phong cua lat cat.
CHO_RUT_KHUNG_S = 120


def _rut_khung(duong: str, moc) -> tuple:
    """Rut cac khung mau cua MOT canh thanh bytes JPEG.

    ⛔ Khung di thang tu dia vao bo nho roi ra `messages` — khong luu vao kho.
       Chung la **dau vao cua mot cau hoi**, khong phai san pham giao cho khach;
       luu chung la them mot vong doi phai quet (B25-01 vua day) doi lay khong gi.

    ⚠️ Mot khung hong thi bo rieng khung do. Mot canh hai khung ma mot khung
       hong van la mot cau hoi tra loi duoc; nem ca canh di thi khong.
    """
    import subprocess
    import tempfile

    ra: list = []
    with tempfile.TemporaryDirectory(prefix="asv_khung_") as tam:
        for j, m in enumerate(moc):
            tep = Path(tam) / f"k{j:02d}.jpg"
            cmd = canh_mod.lenh_rut_khung(duong, float(m), str(tep))
            try:
                subprocess.run(cmd, capture_output=True, timeout=CHO_RUT_KHUNG_S,
                               check=False)
                if tep.exists() and tep.stat().st_size > 0:
                    ra.append(tep.read_bytes())
            except (OSError, subprocess.SubprocessError) as exc:
                log.warning("khong rut duoc khung o giay %.3f (%s)",
                            float(m), type(exc).__name__)
    return tuple(ra)


def _nguon_soi_duoc(db, kho, run) -> str:
    """Tep HINH de tach canh.

    🔴 **Ban dau ham nay chi tim trong artifact cua `media_prepare`, va do la mot
       cho chet.** `media_prepare` co y **khong** xuat ban hinh nao: no sinh
       `source_probe.json` va `audio_full.wav`, con ban goc thi khong bi cham
       ("Mat ban goc la mat kha nang tinh lai moi thu ha nguon").

    ⇒ Nen preset `smart_localize` hong ngay o buoc DAU TIEN cua no, voi thong
      bao "chua co ban media de phan tich canh" — mot cau dung ve chu nghia va
      sai ve nguyen nhan.

    ⭐ No khong bi phat hien vi `PRESET_MAC_DINH` la `localize_preserve_picture`,
       va nhanh do **di vong qua ham nay** (mot canh la du). Tuc ca preset cat
       chua tung chay het chuoi mot lan nao. Pha 14 la cho no chay lan dau.

    ⇒ Nguon dung la **ban goc cua run**. Van uu tien mot artifact hinh cua
      `media_prepare` neu sau nay co, nhung khong con phu thuoc vao no.
    """
    from . import assets, features

    gd = features.giai_doan_theo_ten(db, run.id, "media_prepare")
    # ⚠️ Hai ten cho hai hinh dang: mot danh sach ung vien, roi mot khoa duy
    #    nhat. Ban truoc dung chung ten `khoa` cho ca hai.
    ds_khoa = [k for k in (((gd.outputs or {}) if gd else {}).get("khoa_asset") or [])
               if str(k).endswith((".mp4", ".mkv", ".mov"))]
    khoa = str(ds_khoa[0]) if ds_khoa else str(run.source_key or "")
    if not khoa:
        raise ThieuChiMuc(_t('Chưa có bản media để phân tích cảnh.'))
    return assets.nguon_soi_duoc(kho, khoa)


def _ban_ghi(db, kho, run) -> dict:
    from . import features

    gd = features.giai_doan_theo_ten(db, run.id, "transcribe")
    khoa = [k for k in (((gd.outputs or {}) if gd else {}).get("khoa_asset") or [])
            if str(k).endswith(".json")]
    if not khoa:
        return {}
    try:
        with kho.open(khoa[0]) as f:
            return json.loads(f.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("khong doc duoc ban chep loi (%s)", type(exc).__name__)
        return {}


def _chi_muc_dict(ci) -> dict:
    """Chi muc canh dang luu tru. Cung dang voi `canh.sang_json`, dang doi tuong."""
    return json.loads(canh_mod.sang_json(ci))


def van_tay_ban(ban) -> str:
    """Van tay cua giai doan nay.

    🔑 Gom `PHIEN_BAN_MA` (ma cua giai doan) **va** van tay cua chinh ban bien
       tap. Hai thu doi doc lap: sua mot dong ma o day khong doi quyet dinh, va
       doi mot nguong chinh sach khong doi ma.
    """
    return f"{PHIEN_BAN_MA}-{ban.van_tay()}"
