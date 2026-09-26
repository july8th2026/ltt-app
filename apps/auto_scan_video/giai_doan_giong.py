"""Giai doan VOICE_SYNTHESIS — doc ban dich thanh tieng, TUNG DOAN mot.

N artifact ra: mot tep WAV cho MOI doan, cong mot ban ke `voice_index.json`.

## Vi sao mot tep cho moi doan chu khong mot tep cho ca bai

TIMING dat **tung doan** vao dung khe thoi gian cua no. Mot tep lien mach thi
khong con cho de dat — va neu mot doan phai doc lai (dich sua, giong doi), ca
bai phai doc lai theo.

## Phuc hoi o muc DOAN — Prompt 12 muc 7 va cong thoat

Moi doan co van tay rieng (`giong_noi.van_tay_doan`), va khoa luu tru dan xuat
tu van tay do. Nen khi giai doan chay lai:

  * doan da co artifact **con song va con dung** -> BO QUA, khong goi lai,
    khong tra tien lan hai;
  * chi nhung doan con thieu moi duoc sinh.

⭐ Do la **hat nho nhat an toan** ma cong thoat doi. Hat nho hon (chia mot cau
   thanh hai luot) khong an toan: no doi mot doan thanh hai giong doc khac nhau
   o giua cau.

## Ban va mot dieu KHONG duoc lam o day

⛔ Prompt 12 cam ghep/canh thoi gian trong bo chuyen doi provider. Tep nay sinh
   ra cac doan tieng va **khong** ghep chung. Ghep la viec cua TIMING_ALIGN
   (pha 13), va tron vao day la giau mot quyet dinh timing ben trong mot lop
   provider — noi khong ai di tim no.
"""
from __future__ import annotations

import io
import json
import logging
import tempfile
import time
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (assets, giong_noi, lat_cat, nan_cho_vua, nan_thoi_luong,
               pipeline, su_dung, thoi_gian, van_ban)
from .giai_doan_media import ThieuNguon

log = logging.getLogger(__name__)


class ThieuBanDich(ThieuNguon):
    """Giai doan dich chua sinh ra van ban."""


def _doc_ban_dich(db, kho: Storage, run) -> dict:
    """Van ban da xu ly cua run. Chi doc."""
    from . import features

    truoc = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    khoa = next((k for k in ((truoc.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".json")), "") if truoc else ""
    if not khoa:
        raise ThieuBanDich(_t('Chưa có bản dịch để đọc thành tiếng.'))
    with kho.open(khoa) as f:
        tai_lieu = json.loads(f.read().decode("utf-8"))
    van_ban.kiem(tai_lieu)
    return tai_lieu


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Doc tung doan thanh tieng. Bo qua doan da co san va con dung."""
    if not giong_noi.san_sang():
        raise giong_noi.GiongError(
            _t('Máy tạo tiếng nói chưa được thiết lập trên máy chủ này.'))

    tai_lieu = _doc_ban_dich(db, kho, run)
    from . import cai_dat as cd
    cai = cd.doc(run)
    # Tu dien ten rieng cua khach; `{}` khi khong co. Xem `tu_dien.py`.
    tu_dien = dict(cai.tu_dien)

    # 🔴 **Giong lay tu BAN LONG TIENG, khong tu `settings`.**
    #
    #    Pha 14 dong bang giong vao tai lieu vi loi thoai duoc VIET CHO mot giong
    #    — xung ho, giong dieu, do trang trong deu bam vao no. Truoc pha 15, giai
    #    doan nay van tu doc `settings["voice_id"]`, tuc mot lan chay co the viet
    #    loi cho mot giong roi **doc len bang mot giong khac**, va khong cho nao
    #    bao loi vi ca hai deu tim thay mot gia tri hop le cua rieng minh.
    #
    # ⭐ Mot cau hoi ("giong nao?") phai co MOT cho tra loi.
    #
    # 🔴 **V6 pha 19 dong duong lui `or cai.giong_id`, va no KHONG vo hai.**
    #    Voi `AUTO_MATCH`, `settings.giong_id` RONG — giong duoc chot sau, tu ho
    #    so noi dung. Nen mot ban long tieng thieu `ma_giong` se roi xuong `""`,
    #    va `giai_giong("")` tra `(None, ...)`: khong giong tham chieu, tuc
    #    **giong mac dinh cua engine**, khong ai bam nut — dung loi D-V4-04 cam.
    #
    # ⭐ Moi ban long tieng hop le deu CO `ma_giong` (`long_tieng.kiem` doi no
    #    luc ghi), nen voi moi dau vao hop le dau ra khong doi mot byte. Chi dau
    #    vao THIEU truong nay — nay tu choi to thay vi doc bang giong khac.
    ma_giong = str(tai_lieu.get("ma_giong") or "")
    if not ma_giong:
        from .rang_giong import ChuaRangError

        raise ChuaRangError(_t(
            'Bản lồng tiếng không ghi giọng đã chọn — cần chạy lại bước xử lý '
            'nội dung.'))

    # Giai giong MOT LAN cho ca lan chay — day cung la noi quyen so huu giong
    # duoc kiem (I6/I7). Lam lai cho tung doan la N luot tra CSDL cho mot cau
    # tra loi khong doi.
    # 🔴 **`preset=cai_dat.get("preset")` la mot LOI, va no da lam moi lan chay
    #    that hong o dung day (A29-01).**
    #
    #    `settings["preset"]` la preset DUNG PHIM — `localize_preserve_picture`
    #    hay `smart_localize`. Con `ltt_voice.preset` nghia la TEN MOT GIONG
    #    DUNG SAN. Hai nghia cua cung mot tu, o hai app, va khong cho nao trong
    #    ma noi rang chung khac nhau. Do:
    #        giong_mau.hop_le("localize_preserve_picture") -> False
    #
    # ⇒ Khong co "voice preset" nao trong `settings` ca. Chi co MOT ma giong, va
    #   `giong_noi.tach_ma_giong` biet no thuoc o nao.
    #
    # 🔴 **W4': chot lan tren KICH BAN THAT, mot lan, TRUOC luot sinh dau tien.**
    #
    #    `giai_giong` dua van ban + `ngon_ngu_dich` KHAI trong ban long tieng cho
    #    `ltt_voice`, noi `lan_ngon_ngu.quyet_dinh` phan xu. Lech lan ⇒
    #    `GiongKhongHopLe(voice_language_mismatch)` truoc khi ton mot giay GPU.
    #
    # ⭐ Ca kich ban, khong tung doan: ban long tieng la MOT ngon ngu (no khai
    #    vay), va mot doan le chen mot cau trich tieng Anh khong duoc lam hong ca
    #    lan chay. Chot tung doan con doi N luot doc kho giong cho mot cau tra loi.
    muc_goc = list(tai_lieu.get("muc") or [])
    # ── GOP KHE (D5) — tang RIENG, TRUOC bac thang nan cho vua ─────────────
    #
    # 🔴 **Day la cho `gop_khe` DIEU KHIEN THAT, ⛔ khong con la mot con so bao
    #    cao.** Truoc 25/09 cho nay chi tinh `so_khe_neu_gop` roi vut.
    #
    # ⭐ Vi sao gop TRUOC: `nan_cho_vua` sua MOT CAU cho vua khe cua chinh no va
    #    ⛔ khong bao gio doi ranh gioi khe. `gop_khe` doi chinh cac KHE. Gop truoc
    #    ⇒ bac thang phan quyet tren mot khe RONG HON, nen no it phai goi model.
    #    Do tren luot that `asvr_9fc9cc89`: 106 -> 59 khe, khe trung vi 1,71 ->
    #    2,24 s, so doan bi phan quyet duoi mot am tiet 100/106 -> 39/59.
    #
    # ⛔ Mot khe gop van sinh **MOT** tep tieng, va `ban_ke` van co **MOT dong cho
    #    MOI `ma` goc** (`nan_thoi_luong.no_ban_ke`) — bat bien cua
    #    `giai_doan_thoi_gian.py:88-89` ⛔ khong bi pha. Va phu de van la mot o
    #    cho MOI `ma` goc: o phu de chi chua 84 ky tu, con tran gop la 220
    #    (`nan_thoi_luong.TRAN_KY_TU_GOP`).
    khes = _khe_bao_cao_tu_muc(muc_goc)
    nhom = nan_thoi_luong.nhom_chi_so(
        khes, tran_tang_toc=nan_cho_vua.tran_co_gian())
    muc = [_gop_mot_nhom([muc_goc[k] for k in g]) for g in nhom]

    # ⭐ CÙNG các `Khe` vừa dựng cho `nhom_chi_so` — chúng đã mang `moc_sau`, tức
    #    biên có thật kế tiếp. ⛔ Không dựng lần hai: hai bản sao của cùng một mốc
    #    là chỗ sẽ trôi.
    ngan_sach_theo_ma = {
        k.ma: thoi_gian.ngan_sach_nan_s(k.khe_s, k.ngan_sach_s) for k in khes
    }

    # ══ CAU DA NAN DA LUU BEN — doc TRUOC khi tieu them mot dong ════════════
    #
    # 🔴 **Truoc 26/09 cau da nan chi song trong `m["chu"]`, tuc trong BO NHO cua
    #    MOT job.** `[A]` chi danh dau `da_tra_tien` cho doan DA DOC (`i0 <
    #    lc.vi_tri`), nen `[B]` cua MOI lat cat sau lai thay dung nhung doan tran
    #    ay, va `[E]` nan LAI ca danh sach. Do cua luot soat R2 tren video 120
    #    phut: ~1.200 doan tran ⇒ **~700 loi goi nan thay vi 60**, va `item_key`
    #    mang `luot` nen moi lan la mot dong so cai THAT — mot hoa don ×12.
    #
    # ⭐ Cho luu la `outputs` cua CHINH don vi viec cua doan (`item_key = ma`).
    #    Ba dieu kien cua no, va chi cho nay thoa ca ba:
    #      (i)   **song qua lat cat** — no la mot dong CSDL, ⛔ khong phai
    #            `lc.trang_thai`: con tro chi duoc ghi khi `TiepNoi` BAY RA, tuc
    #            mot lan SAP (`job_runner._het_gio` -> `os._exit(3)`) lam mat no;
    #      (ii)  **song qua mot lan sap** — `[E]` `commit` ngay sau MOI lo;
    #      (iii) **⛔ khong pha `ban_ke` hay van tay** — `_doc_lat` loc theo khoa
    #            `"lat"` nen no bo qua ban ghi nay, va `[F]` `danh_dau_xong` ghi
    #            DE `outputs`, tuc ban ghi tu bien mat dung luc no het viec.
    #
    # ⚠️ Ban ghi mang `chu_goc` + `lan`, va CA HAI phai khop moi duoc dung lai:
    #    `features._dat_lai_giai_doan` ⛔ KHONG cham don vi viec, nen mot ban dich
    #    MOI (`chu_goc` khac) hoac mot vong sua (`lan` khac) phai lam ban nan cu
    #    vo hieu — neu khong, khach nhan mot cau rut tu mot ban dich da bo.
    lan_lai = _lan_doc_lai(db, run)
    nan_ben = _doc_chu_da_nan(db, run)
    da_nan: set[str] = set()
    for m in muc:
        g = nan_ben.get(str(m["ma"]))
        if not g or str(g.get("chu_goc") or "") != str(m["chu"]):
            continue
        if int(g.get("lan") or 0) != int(lan_lai.get(str(m["ma"]), 0)):
            continue
        m["chu"] = str(g["chu"])
        da_nan.add(str(m["ma"]))
    # ⭐ `so_vong` cua chung la 1 — khai o DAY chu khong o `[E]`: mot doan da nan
    #    o mot lat TRUOC van la mot doan DA qua mot vong nan, va `ket_luan`,
    #    `ban_ghi_luot_doc`, `tom_tat`, `_ke_nan` deu doc dung con so ay.
    so_vong_theo_ma: dict[str, int] = {ma: 1 for ma in da_nan}

    ref_b64, preset = giong_noi.giai_giong(
        db, owner_id=run.owner_id, voice_id=ma_giong,
        van_ban="\n".join(str(m.get("chu") or "") for m in muc),
        ngon_ngu=str(tai_lieu.get("ngon_ngu_dich") or ""))

    phan: list[dict] = []
    ban_ke: list[dict] = []
    cac_nan: list[nan_cho_vua.KetQuaNan] = []
    # ⭐ Buoc 0.5 (25/09): MOI LUOT DOC mot dong — giay DO DUOC luc ay, khong phai
    #    giay cuoi cung. `cac_nan`/`tung_doan` chi giu giay sau khi da nan xong,
    #    nen truoc buoc nay khong ai tinh duoc mot ban sua nguong tiet kiem bao
    #    nhieu luot goi may B. Xem `nan_cho_vua.ban_ghi_luot_doc`.
    luot_doc: list[dict] = []
    da_sinh = 0
    # 🔑 **Hai dong ho, va thieu chung thi khong ai sua duoc giai doan nay.**
    #
    #    Luot nghiem thu nen v3 (23/09) do duoc `voice_synthesis` = 943 giay cho
    #    mot phim 107 giay va **khong tach duoc con so ay**: bao cao chi biet
    #    tong. Phai do lai ngoai duong san pham (`tools/do_toc_do_giong.py`) moi
    #    biet 751 giay la LLM viet lai chu khong phai may sinh tieng (241 giay).
    #
    # ⭐ Hai con so nay di vao `tom_tat`, tuc vao bang chung cua MOI luot chay
    #    ve sau. "Cham" khong con la mot cam giac.
    dong_ho = {"giay_tts": 0.0, "giay_llm_nan": 0.0, "so_doan_nan_oan": 0}

    # 🔑 LAT CAT (`lat_cat.py`): ~2.000 doan cua 120 phut video khong vua MOT
    #    job. Don vi te nhat = (VONG_TOI_DA + 1) luot TTS + VONG_TOI_DA lan xin
    #    viet lai, moi cai o tran timeout cua lop goi.
    #
    # ⚠️ **Tu 26/09 don vi te nhat THAT chi con MOT luot TTS** — `[E]` nan theo
    #    LO chay mot lan o dau lat, ⛔ khong nam trong don vi nua. Cong thuc
    #    `du_phong_s` GIU NGUYEN co y: `test_2050::test_du_phong_moi_giai_doan_
    #    VUA_trong_tran_manifest` chot dung cong thuc nay theo manifest, va giu
    #    THUA cho la giu ve phia an toan — lat nhuong som hon mot chut chu ⛔ khong
    #    bao gio thieu cho de ket mot don vi da bat dau.
    from . import ai as _ai
    lc = lat_cat.mo(db, run, pipeline.VOICE_SYNTHESIS,
                    du_phong_s=((nan_cho_vua.VONG_TOI_DA + 1) * _timeout_tts()
                                + nan_cho_vua.VONG_TOI_DA
                                * lat_cat.timeout_goi_ai(_ai.RUT_NGAN_CHO_VUA)
                                + lat_cat.DU_PHONG_NGOAI_GOI_S))
    da_lat = _doc_lat(db, run, lc) if lc.noi_tiep else {}

    # ══ [A] DOAN NAO DA TRA TIEN ROI — quet MOT lan, TRUOC khi tieu mot dong ══
    #
    # 🔴 **Vi sao khoi nay phai dung TRUOC `[E]`, ⛔ khong phai trong `[F]`.**
    #    Nan mot doan la doi `chu`; `_van_tay` bam `chu` ⇒ doi van tay ⇒ doi khoa
    #    luu tru ⇒ tep tieng **DA TRA TIEN** cua doan ay khong con tim thay duoc
    #    va doan bi doc lai. Bac thang cu hoi cache **truoc** khi nan, nen ban dao
    #    thu tu nay phai hoi truoc y nhu vay. Lam nguoc lai la lam hong hoa don.
    #
    # ⛔ Va moi doan chi duoc DO MOT LAN: `_doan_con_dung` cham checksum roi doc
    #    tep tieng that, nen hoi hai lan (o day roi lai o `[F]`) la nhan doi phan
    #    dat nhat cua chinh phep kiem cache. Ket qua nam trong `da_tra_tien` va
    #    `[F]` chi doc lai tu do.
    da_tra_tien: dict[int, dict] = {}
    for i0, m in enumerate(muc):
        # ⭐ NGU NGHIA CU, GIU Y NGUYEN: chi doan nam TRUOC con tro `lc.vi_tri`
        #    moi la "da sinh o mot lat truoc cua CUNG phien" (xem `_doc_lat`).
        lat = da_lat.get(str(m["ma"])) if i0 < lc.vi_tri else None
        if lat is not None:
            da_tra_tien[i0] = {"lat": lat}
            continue
        chu_dau = str(m["chu"])
        vt_dau = _van_tay(m["ma"], chu_dau, ma_giong, preset, tu_dien=tu_dien,
                          lan=lan_lai.get(m["ma"], 0))
        khoa_dau = assets.dat_khoa(owner_id=run.owner_id, run_id=run.id,
                                   stage=pipeline.VOICE_SYNTHESIS,
                                   van_tay=vt_dau, duoi="wav")
        khoa_tam_cu = assets.khoa_staging(
            owner_id=run.owner_id, run_id=run.id,
            stage=pipeline.VOICE_SYNTHESIS, van_tay=vt_dau, duoi="wav")
        cu = _doan_con_dung(db, kho, run, khoa_dau)
        tam_cu = None
        if cu is None:
            # 🔴 Mot doan con nam trong STAGING van la doan ta DA TRA TIEN — xem
            #    chu thich day du o nhanh dung lai cua `[F]`.
            cu = _doan_trong_staging(kho, khoa_tam_cu)
            if cu is not None:
                tam_cu = khoa_tam_cu
        if cu is not None:
            da_tra_tien[i0] = {"cu": float(cu), "chu": chu_dau, "vt": vt_dau,
                               "khoa": khoa_dau, "staging": tam_cu}

    # ══ [B] UOC LUONG — ⛔ KHONG chay TTS ═════════════════════════════════════
    #
    # 🔑 **Day la ca ban dao thu tu (26/09).** Hom truoc TTS **chinh la phep do**:
    #    phai doc moi biet dai bao nhieu, nen moi vong nan la `TTS -> LLM -> TTS`.
    #    Do tren luot nen v3: TTS 241 s, vong nan **751 s** trong 943 s.
    #    `nan_thoi_luong.Khe.giay_can` (nhip dong ho + nghi o dau cau) nay du tot
    #    de lam phep do **truoc**, nen TTS chi con chay MOT luot o `[F]`.
    #
    # ⚠️ `khe_gop` dung tren `muc` **DA GOP**, ⛔ khong phai `khes` (mot `Khe` cho
    #    MOI `ma` goc). Mot khe gop doc MOT luot bang van ban CUA CA NHOM, nen am
    #    tiet va dau cau phai dem tren van ban ay; `zip(muc, khes)` lech hang ngay
    #    khi co mot nhom gop. Day ⛔ khong phai "dung `Khe` lan hai cho cung mot
    #    moc" (canh bao o tren): no la cung mot phep dem tren mot DANH SACH KHAC.
    khe_gop = _khe_bao_cao_tu_muc(muc)
    doan_tran: list[dict] = []
    # ⭐ Giay UOC LUONG cua moi `ma`, tinh MOT LAN o day (`Khe.giay_can`). Loop
    #    `[F]` doc lai qua dict nay de ghi vao `ban_ghi_luot_doc` — ⛔ KHONG
    #    tinh lan hai, cung mot ly do voi `ngan_sach_theo_ma`/`so_vong_theo_ma`.
    giay_uoc_theo_ma: dict[str, float] = {}
    # ⛔ `strict=True`: `khe_gop` dung TU `muc`, nen lech do dai la mot loi lap
    #    trinh — va no se lam `[B]` bo im lang cac doan o duoi, tuc bo im lang
    #    cua tieu tien cua chung.
    for i0, (m, kg) in enumerate(zip(muc, khe_gop, strict=True)):
        if i0 in da_tra_tien:
            continue
        ngan_sach = ngan_sach_theo_ma.get(str(m["ma"]), nan_cho_vua.khe_cua(m))
        giay_doan = kg.giay_can()
        giay_uoc_theo_ma[str(m["ma"])] = giay_doan
        # 🔴 **Doan DA co cau nan luu ben thi ⛔ KHONG duoc vao `doan_tran`.**
        #    Day la cua chan cua hoa don ×12: khong co dong nay thi moi lat cat
        #    lai xin nan dung nhung doan ay mot lan nua (xem khoi `da_nan` o dau
        #    ham). ⭐ `giay_uoc_theo_ma` van duoc ghi TRUOC dong nay — no do tren
        #    van ban SE DOC (`m["chu"]` da la cau nan), va `[F]` can no cho
        #    `ban_ghi_luot_doc`; bo qua ca phep do la lam mat sai so cua bo uoc
        #    luong o dung nhung doan dat nhat.
        if str(m["ma"]) in da_nan:
            continue
        if nan_cho_vua.nen_viet_lai(giay_doan, ngan_sach):
            doan_tran.append({"ma": str(m["ma"]), "chu": str(m["chu"]),
                              "giay_doc": giay_doan, "khe": ngan_sach,
                              "truoc": _chu_ke(khe_gop, i0, -1),
                              "sau": _chu_ke(khe_gop, i0, +1)})

    # ══ [E] NAN theo LO — 1..N loi goi cho CA video (cu: hang chuc) ═══════════
    #
    # ⭐ `so_vong_theo_ma` giu NGUYEN nghia cua `so_vong` cu: *so vong NAN da chay
    #    truoc luot doc nay*. Sau ban dao thu tu no chi con nhan hai gia tri —
    #    `0` (chua nan) hoac `1` (`VONG_TOI_DA`) — va `ban_ghi_luot_doc`,
    #    `ket_luan`, `_ke_nan` van doc dung con so ay.
    theo_ma = {str(m["ma"]): m for m in muc}

    def _chot_lo(chu_lo: dict[str, str]) -> None:
        """Chot MOT lo nan: doi `chu`, LUU BEN, `commit`, dem mot don vi.

        🔴 **`commit` o day la thu chan mot lan mat tien thanh mat khong dau
           vet.** `ai.goi_tinh_tien` ghi so cai trong giao dich CUA NGUOI GOI
           (`su_dung.ghi` chi `flush`), va `db.commit()` dau tien cua giai doan
           nay von nam SAU ca `[E]`, trong `[F]`. Nen mot `TiepNoi` hay mot loi
           bat ky truoc doan tieng dau tien di qua `thi_hanh` -> `db.rollback()`
           va **ca luot nan da tieu bien mat khoi so cai**: tien mat, so trong.

        ⭐ `lc.xong_mot()`: mot lo nan LA mot don vi viec da xong va da ben, nen
           dem no la dem dung. Va no la dieu kien de `lc.nen_nhuong()` (`da_lam
           >= 1`) co the dung — thieu no thi `[E]` ⛔ khong nhuong duoc lo nao.
        """
        for ma, moi in chu_lo.items():
            m = theo_ma.get(ma)
            # ⛔ `moi == m["chu"]` (model tra ve y nguyen) ⛔ khong tinh la mot
            #    vong nan: van tay khong doi, nen doan do van dung lai duoc tep cu
            #    y nhu truoc — dung lap luan voi nhanh `moi_chu == chu` cua bac
            #    thang cu. Va ⛔ khong luu ben mot ban "nan" khong doi mot byte.
            if m is None or not moi or str(moi) == str(m["chu"]):
                continue
            _ghi_chu_da_nan(db, run, ma=ma, chu_goc=str(m["chu"]),
                            chu=str(moi), lan=int(lan_lai.get(ma, 0)))
            m["chu"] = str(moi)
            so_vong_theo_ma[ma] = 1
        db.commit()
        lc.xong_mot()

    if doan_tran:
        _t0 = time.monotonic()
        # ⭐ `truoc_lo` = `lc.kiem` TRUOC moi lo, tuc `[E]` NHUONG DUOC. `vi_tri`
        #    giu NGUYEN (`lc.vi_tri`): chua doan nao duoc doc o luot nay, nen con
        #    tro ⛔ khong duoc nhich — tien do cua `[E]` nam o `chu_da_nan` da
        #    commit, ⛔ khong o con tro.
        # ⚠️ `du_phong_s` cua lat la du phong cua mot don vi TTS (1.980 s do
        #    26/09), con mot lo nan xau nhat la `LAN_XIN_NAN_LO x
        #    timeout_goi_ai` = 360 s. Nhuong theo con so LON hon la nhuong SOM
        #    hon can — giu ve phia an toan, cung lap luan voi chu thich
        #    `du_phong_s` o `lat_cat.mo` ngay tren.
        _nan_lo(db, run, doan_tran, luot=lc.luot, ctx=ctx,
                truoc_lo=lambda: lc.kiem(vi_tri=lc.vi_tri), sau_lo=_chot_lo)
        dong_ho["giay_llm_nan"] += time.monotonic() - _t0

    with tempfile.TemporaryDirectory(prefix="asv-voice-") as tam:
        thu_muc = Path(tam)

        for i, m in enumerate(muc, start=1):
            if ctx is not None and getattr(ctx, "is_cancelled", None) and ctx.is_cancelled():
                raise giong_noi.GiongError(_t('Phiên chạy đã bị huỷ giữa chừng.'))
            if ctx is not None and getattr(ctx, "progress", None):
                ctx.progress(int(5 + 85 * i / max(1, len(muc))),
                             _t('Đang đọc thành tiếng'))
            # ⭐ Nhip tien do MANG BO DEM (log van hanh, 25/09) — khac `progress`
            #    o tren (bac thang % cho khach): day la con so THAT cho van
            #    hanh, tu nem qua `JobContext.progress_counter` neu thieu bo
            #    dem. Mac dinh 30s/5 don vi la du thua: do thuc te giai doan
            #    nay ~1.610s / ~67 doan (docs/NHAT_KY.md muc 7) — ~24s/doan —
            #    nen 5 don vi da vuot 30s, ra ~13 dong cho ca 27 phut.
            if ctx is not None and getattr(ctx, "progress_counter", None):
                ctx.progress_counter(i, len(muc), don_vi="doan")

            khe = nan_cho_vua.khe_cua(m)
            # 🔴 HAI con số, HAI câu hỏi — ⛔ đừng gộp lại:
            #    `khe`       = khe của chính đoạn (`ket - bat`) → dùng để BÁO CÁO
            #                  (`ket_luan`, `ban_ghi_luot_doc`, `tom_tat`).
            #    `ngan_sach` = khe + phần khoảng lặng mượn được → dùng cho CỬA
            #                  TIÊU TIỀN. Đây là con số mà `timing_align` thật sự
            #                  thực thi, nên nó là con số đúng để quyết có trả
            #                  tiền cho một lượt LLM hay không.
            ngan_sach = ngan_sach_theo_ma.get(str(m["ma"]), khe)
            ho_so = da_tra_tien.get(i - 1) or {}

            # ⭐ Doan DA SINH o luot truoc cua CUNG lat cat: dung lai y nguyen
            #    ban ke cua luot do (ke ca cau da nan + so vong). Di duong cache
            #    thuong se tra `tu_cu=True` va — voi doan da nan — tim theo van
            #    tay cau GOC nen khong thay, sinh lai: ban ra khac lan mot mach.
            #
            # ⛔ Dieu kien `(i - 1) < lc.vi_tri` da duoc `[A]` ap y nguyen — `[F]`
            #    ⛔ khong duoc hoi lai bang mot dieu kien thu hai: hai ban sao cua
            #    cung mot ranh gioi la cho se troi.
            lat = ho_so.get("lat")
            if lat is not None:
                kq = nan_cho_vua.ket_luan(
                    m["ma"], chu=str(lat["chu"]), giay=float(lat["giay"]),
                    khe=khe, so_vong=int(lat["so_vong"]))
                cac_nan.append(kq)
                # ⚠️ `lat["ban_ke"]` la mot DANH SACH tu 25/09 (mot khe gop tra
                #    ve nhieu dong). Ban ghi cu la mot dict — nhan ca hai, vi mot
                #    luot noi tiep co the doc diem chot cua luot truoc ban nang.
                _cu = lat["ban_ke"]
                ban_ke.extend(dict(x) for x in
                              (_cu if isinstance(_cu, list) else [_cu]))
                if lat.get("phan"):
                    phan.append(dict(lat["phan"]))
                da_sinh += int(lat.get("so_luot_doc") or 0)
                # ⭐ Lat cat truoc DA DOC that, chi khong phai trong luot nay:
                #    khong mang ban ghi sang thi bao cao cua mot video 120 phut
                #    (nhieu lat) chi noi ve lat cuoi.
                luot_doc.extend(dict(d) for d in (lat.get("luot_doc") or []))
                continue

            # ── Phuc hoi o muc DOAN — phan quyet DA lam o `[A]` ───────────
            #
            # 🔴 **Mot doan con nam trong STAGING van la doan ta DA TRA TIEN.**
            #
            #    Doan tieng chi thanh `AsvAsset` o cuoi giai doan, khi `thi_hanh`
            #    promote ca lo. Nen mot lan truot o doan thu ba lam hai doan dau
            #    **mat het dau vet co the dung lai** — trong khi tep cua chung van
            #    nam nguyen trong kho duoi khoa staging, va so cai da ghi rang
            #    chung DA GIAO.
            #
            # ⭐ Do duoc o pha 23: mot lan truot o doan ba lam luot chay lai goi
            #    may sinh tieng **6 lan cho 3 doan**. Rang buoc
            #    `UNIQUE(run_id, ma_dispatch)` che mat dieu do — no chan lan GHI
            #    thu hai, khong chan lan LAM thu hai.
            #
            # ⛔ Khoa staging mang van tay cua chinh doan (chu + giong + preset),
            #    nen mot tep tim thay o day dung la tep cua doan nay chu khong
            #    phai cua mot lan chay khac; va no da bi do lai bang
            #    `kiem_tep_tieng` o `[A]` truoc khi duoc tin.
            if "cu" in ho_so:
                chu = str(ho_so["chu"])
                khoa_ben = str(ho_so["khoa"])
                if ho_so.get("staging"):
                    phan.append({"staging_key": ho_so["staging"],
                                 "kind": "audio", "duoi": "wav",
                                 "van_tay": str(ho_so["vt"])})
                # ⭐ `so_vong` doc tu `so_vong_theo_ma`, ⛔ khong ghim `0`: tu
                #    26/09 `[A]` tham cache bang van tay cua CAU DA NAN (xem
                #    khoi `da_nan`), nen mot doan dung lai tep cu VAN co the la
                #    doan da qua mot vong nan — ghim `0` la bao cao noi doi ve
                #    so vong nan cua chinh no.
                kq = nan_cho_vua.ket_luan(
                    m["ma"], chu=chu, giay=float(ho_so["cu"]), khe=khe,
                    so_vong=int(so_vong_theo_ma.get(str(m["ma"]), 0)))
                ban_ke.extend(nan_thoi_luong.no_ban_ke(
                    {"ma": m["ma"], "khoa": khoa_ben, "chu": chu,
                     "giay": float(ho_so["cu"]), "tu_cu": True, **_ke_nan(kq)},
                    m["_thanh_vien"]))
                cac_nan.append(kq)
                continue

            # 🔑 `chu` = van ban DA CHOT o `[E]`, va `so_vong` la so vong nan da
            #    chay truoc luot doc nay. Van tay bam `chu`, nen mot doan da bi
            #    nan co van tay KHAC — thieu dieu do thi "doc lai" tra ve dung
            #    ban da bi tu choi (xem `_van_tay`).
            chu = str(m["chu"])
            so_vong = int(so_vong_theo_ma.get(str(m["ma"]), 0))
            vt = _van_tay(m["ma"], chu, ma_giong, preset, tu_dien=tu_dien,
                          lan=lan_lai.get(m["ma"], 0))

            lc.kiem(vi_tri=i - 1)
            sinh_truoc = da_sinh
            # Ban ghi rieng cua doan nay, de luot NOI TIEP dung lai duoc.
            luot_cua_doan: list[dict] = []

            # ── [F] TTS MOT luot ──────────────────────────────────────────
            #
            # ⛔ ⛔ KHONG mot vong lap nao quanh day. Bac thang cu doc -> do ->
            #    nan -> doc lai, tuc `VONG_TOI_DA + 1` luot TTS cho mot doan
            #    khong vua; phep do nay nay nam o `[B]` (`Khe.giay_can`), rẻ hon
            #    ba bac do lon va ⛔ khong ton mot giay GPU nao.
            _t0 = time.monotonic()
            wav, _headers = giong_noi.doc_mot_doan(
                chu, ref_b64=ref_b64, preset=preset,
                tu_dien_rieng=tu_dien or None)
            dong_ho["giay_tts"] += time.monotonic() - _t0
            # ⛔ Kiem TRUOC khi coi doan la xong (muc 8). Do tren TEP THAT,
            #    khong tin header cua may sinh tieng — cung ly do
            #    `apps/ltt_voice` doi chieu hai phia va ghi log khi lech.
            tep = thu_muc / f"{m['ma']}.wav"
            tep.write_bytes(wav)
            giay = giong_noi.kiem_tep_tieng(str(tep))
            da_sinh += 1
            # ⭐ Buoc 0.5: ghi NGAY sau khi do, TRUOC moi quyet dinh — mot dong
            #    so lieu them ⛔ khong duoc doi mot quyet dinh nao.
            # ⭐ `giay_doan` = uoc luong cua `[B]` (Task 12) cho CHINH `ma` nay —
            #    mang theo de `asv_doi_soat` do duoc sai so cua bo uoc luong,
            #    thay vi chi do "doc ra vuot khe bao nhieu" (`lech`).
            _bg = nan_cho_vua.ban_ghi_luot_doc(
                m["ma"], vong=so_vong, giay=giay, khe=khe,
                giay_doan=giay_uoc_theo_ma.get(str(m["ma"])))
            luot_doc.append(_bg)
            luot_cua_doan.append(_bg)

            # ⭐ Đ4: đoạn "tràn khe nhưng vừa ngân sách". TRƯỚC bản sửa mỗi đoạn
            #    như vậy là một lượt LLM tiêu OAN; nay cửa tiêu tiền ở `[B]` đọc
            #    `ngan_sach` nên ⛔ không ai bị gọi oan nữa — bộ đếm này là thứ
            #    CHỨNG MINH điều đó trên số liệu của mỗi lượt chạy, đo trên giây
            #    THẬT chứ ⛔ không trên ước lượng.
            if giay > khe and giay <= ngan_sach:
                dong_ho["so_doan_nan_oan"] += 1

            kq = nan_cho_vua.ket_luan(m["ma"], chu=chu, giay=giay, khe=khe,
                                      so_vong=so_vong)
            cac_nan.append(kq)

            khoa_ben = assets.dat_khoa(owner_id=run.owner_id, run_id=run.id,
                                       stage=pipeline.VOICE_SYNTHESIS,
                                       van_tay=vt, duoi="wav")
            khoa_tam = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                           stage=pipeline.VOICE_SYNTHESIS,
                                           van_tay=vt, duoi="wav")
            with open(tep, "rb") as f:
                kho.put(khoa_tam, f, content_type="audio/wav")

            phan_moi = {"staging_key": khoa_tam, "kind": "audio", "duoi": "wav",
                        "van_tay": vt}
            # ⭐ `chu` = cau CUOI CUNG may da doc (sau nan). `qc_do_luong` cham
            #    WER so voi chinh cau nay, khong phai cau truoc khi nan.
            # ⭐ MOT tep tieng, NHIEU dong `ban_ke` — mot dong cho MOI `ma` goc
            #    cua nhom, `giay` chia theo am tiet. Bat bien cua
            #    `giai_doan_thoi_gian.py:88-89` ⛔ khong bi pha.
            ke_moi = nan_thoi_luong.no_ban_ke(
                {"ma": m["ma"], "khoa": khoa_ben, "chu": chu, "giay": giay,
                 **_ke_nan(kq)},
                m["_thanh_vien"])
            phan.append(phan_moi)
            ban_ke.extend(ke_moi)

            # ⭐ Ghi so cai **mot lan cho moi doan da giao**, kem so giay THAT.
            #    `UNIQUE(run_id, ma_dispatch)` chan lan ghi thu hai neu giai doan
            #    chay lai — nen "dung mot lan" la mot rang buoc cua CSDL chu
            #    khong phai mot loi hua cua ma.
            _ghi_so(db, run, ma=m["ma"], van_tay=vt, giay=giay, kq=kq)
            su_dung.danh_dau_xong(db, run, stage=pipeline.VOICE_SYNTHESIS,
                                  item_key=m["ma"], fingerprint=vt,
                                  outputs={"khoa": khoa_ben, "giay": giay,
                                           "trang_thai": kq.trang_thai,
                                           "so_vong": kq.so_vong,
                                           # Du de luot noi tiep dung lai
                                           # y nguyen (xem `_doc_lat`).
                                           "lat": {"phien": lc.phien,
                                                   "chu": chu,
                                                   "giay": giay,
                                                   "so_vong": so_vong,
                                                   "so_luot_doc":
                                                       da_sinh - sinh_truoc,
                                                   # Buoc 0.5: ban ghi tung luot
                                                   # doc cua doan nay.
                                                   "luot_doc": luot_cua_doan,
                                                   "phan": phan_moi,
                                                   # ⚠️ DANH SACH tu 25/09: mot
                                                   # khe gop tra ve nhieu dong.
                                                   "ban_ke": ke_moi}})
            db.commit()
            lc.xong_mot()

        # ── Ban ke: cai TIMING doc de biet doan nao o dau ─────────────────
        goi = json.dumps({"schema": 1, "doan": ban_ke}, sort_keys=True,
                         ensure_ascii=False).encode("utf-8")
        vt_ke = assets.bam(goi)[:32]
        khoa_ke = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                      stage=pipeline.VOICE_SYNTHESIS,
                                      van_tay=vt_ke, duoi="json")
        kho.put(khoa_ke, io.BytesIO(goi), content_type="application/json")
        phan.append({"staging_key": khoa_ke, "kind": "json", "duoi": "json",
                     "van_tay": vt_ke})

        # ⭐ Dem tren dong DAU cua moi nhom: mot tep = mot luot sinh. Dong di theo
        #    ⛔ khong phai mot doan "moi sinh" hay "dung lai" nao ca.
        ke_dau = [d for d in ban_ke if not nan_thoi_luong.la_dong_theo_sau(d)]
        return {
            "phan": phan,
            "tom_tat": {
                # 🔴 **HAI con so, ⛔ khong mot.** `nan_cho_vua.tom_tat` khai
                #    `so_doan` = so KHE DOC (= so tep tieng sinh ra); khoa duoi
                #    day khai so `ma` cua `content.json`. Tu khi `gop_khe` dieu
                #    khien that chung ⛔ khong con bang nhau, va gop chung lam mot
                #    la lam bao cao noi doi ve chi phi TTS.
                # ⛔ Va ⛔ KHONG ghi de `so_doan` o day: mot khoa hai chu so huu la
                #    dung cai bay kho nay da tra gia (`test_4700` chot).
                "so_ma_noi_dung": len(muc_goc),
                "so_khe_da_gop": sum(1 for g in nhom if len(g) > 1),
                # ⚠️ **Hai con so, khong phai mot.** `so_doan_moi_sinh` dem DOAN;
                #    `so_luot_doc` dem LUOT GOI may sinh tieng — mot doan phai
                #    nan hai vong la ba luot. Gop chung lam mot se lam bao cao
                #    chi phi noi doi ngay o cho no quan trong nhat, va lam mat
                #    mot menh de ma `test_409` da chot dung.
                "so_doan_moi_sinh": len(muc) - sum(1 for d in ke_dau
                                                   if d.get("tu_cu")),
                "so_luot_doc": da_sinh,
                "so_doan_dung_lai": sum(1 for d in ke_dau if d.get("tu_cu")),
                # ⭐ `giay_tep` cua dong dau = do dai THAT ca tep; `giay` cua no
                #    chi la PHAN cua rieng no. Cong `giay` cua moi dong cung ra
                #    dung tong ay (`chia_giay` bao toan tong), nhung cong
                #    `giay_tep` la cong mot con so mot lan cho moi nhom — ro rang
                #    hon, va ⛔ khong phu thuoc vao phep chia.
                "tong_giay": round(sum(float(d.get("giay_tep") or d["giay"])
                                       for d in ke_dau), 2),
                # ⭐ Xem `dong_ho` o dau ham: hai con so nay tra loi *"giai doan
                #    nay cham vi cai gi"* ma khong phai do lai ngoai san pham.
                "giay_tts": round(dong_ho["giay_tts"], 2),
                "giay_llm_nan": round(dong_ho["giay_llm_nan"], 2),
                # ⭐ Đ4 (xem `[F]`): so doan `giay > khe` NHUNG `giay <= ngan_sach`
                #    — tung bi TINH TIEN OAN mot luot LLM truoc ban sua thu tu.
                #    ⛔ Khai `dong_ho["so_doan_nan_oan"]` ma khong XUAT o day la
                #    dung con so ⛔ khong toi duoc `asv_doi_soat` (Loi #1, 26/09).
                "so_doan_nan_oan": dong_ho["so_doan_nan_oan"],
                "preset": str(preset or ""),
                "ma_giong": ma_giong,
                **nan_cho_vua.tom_tat(cac_nan, tung_luot_doc=luot_doc),
            },
        }


def _khe_bao_cao_tu_muc(muc: list[dict]) -> list[nan_thoi_luong.Khe]:
    """`muc` (danh sach doan cua `content.json`) -> `Khe` cho `gop_khe`.

    ⭐ `moc_sau` = `bat` cua doan KE TIEP trong `muc`: moi doan trong `muc` da
       la `for_dubbing=True` (`ban_bien_tap.doan_giu_lai` loc doan bi cat truoc
       do, o CONTENT_PROCESS) — dung dinh nghia "bien co that ke tiep" cua
       open-dubbing ma `nan_thoi_luong.Khe` doi hoi, khong phai mot hang so.
       Doan CUOI khong co doan sau de muon: lay chinh `ket` cua no (ngan_sach_s
       = khe_s, khong muon).

    `am_tiet` dem theo dung dinh nghia da co san cua kho nay
    (`ngon_ngu.py:47-49`: tieng Viet — dem TU cach nhau boi khoang trang la
    dem AM TIET, "cung mot phep"), khong phai mot cach dem moi bia ra.
    """
    n = len(muc)
    ra: list[nan_thoi_luong.Khe] = []
    for i, m in enumerate(muc):
        bat = float(m.get("bat") or 0.0)
        ket = max(bat, float(m.get("ket") or 0.0))
        moc_sau = float(muc[i + 1].get("bat") or ket) if i + 1 < n else ket
        chu = str(m.get("chu") or "")
        ra.append(nan_thoi_luong.Khe(
            ma=str(m.get("ma") or ""), bat=bat, ket=ket,
            moc_sau=max(moc_sau, ket), am_tiet=len(chu.split()), chu=chu))
    return ra


def _gop_mot_nhom(thanh_vien: list[dict]) -> dict:
    """Mot NHOM muc lien ke -> mot muc "khe da gop" de DOC mot luot.

    ⭐ `ma` cua thanh vien DUNG DAU duoc dung lam `ma` cua ca nhom — ⛔ khong bia
       ra mot `ma` moi. So cai (`UNIQUE(run_id, ma_dispatch)`), diem chot
       (`su_dung.danh_dau_xong`) va van tay tep deu bam vao `ma`, nen mot `ma`
       tong hop se la mot khoa ⛔ khong doi chieu duoc voi `content.json`.

    ⭐ `_thanh_vien` mang theo CAC MUC GOC — `no_ban_ke` can `chu` va `bat`/`ket`
       cua tung `ma` de tra lai mot dong `ban_ke` cho moi cai.

    ⛔ Nhom mot thanh vien tra ve mot ban SAO co `_thanh_vien` do dai 1, ⛔ khong
       phai chinh `muc` goc: mot hinh dang duy nhat cho ca hai ca thi nguoi doc
       xuoi dong ⛔ khong phai hoi "cai nay co `_thanh_vien` khong".
    """
    dau = thanh_vien[0]
    return {**dau,
            "chu": " ".join(str(m.get("chu") or "") for m in thanh_vien).strip(),
            "goc": " ".join(str(m.get("goc") or "") for m in thanh_vien).strip(),
            "bat": float(dau.get("bat") or 0.0),
            "ket": float(thanh_vien[-1].get("ket") or 0.0),
            "_thanh_vien": [dict(m) for m in thanh_vien]}


def _timeout_tts() -> float:
    """Tran timeout cua MOT luot TTS: mac dinh cua `sidecar_client.noi`, vi
    `giong_noi.doc_mot_doan` -> `ltt_voice.features.goi_cong` khong truyen
    `timeout` (xem docstring `goi_cong`)."""
    from apps.ltt_voice import sidecar_client

    return lat_cat.mac_dinh_tham_so(sidecar_client.noi, "timeout")


def _doc_lat(db, run, lc) -> dict:
    """`{ma_doan: ban ghi lat}` cua cac doan da sinh o luot truoc CUNG phien."""
    from . import features

    ra: dict = {}
    for it in features.cac_don_vi(db, run.id, pipeline.VOICE_SYNTHESIS):
        lat = (it.outputs or {}).get("lat")
        if isinstance(lat, dict) and lat.get("phien") == lc.phien:
            ra[str(it.item_key)] = lat
    return ra


#: Khoa trong `outputs` cua don vi viec giu CAU DA NAN cua chinh doan do.
#:
#: ⛔ Mot khoa RIENG, ⛔ khong tron vao `"lat"`: `_doc_lat` chi nhan ban ghi cua
#:    doan DA DOC o CUNG phien lat cat, con ban ghi nay phai song qua ca mot
#:    phien khac (mot `attempt` moi) — hai vong doi khac nhau thi hai khoa.
KHOA_CHU_NAN = "chu_da_nan"


def _doc_chu_da_nan(db, run) -> dict[str, dict]:
    """`{ma: {"chu_goc", "chu", "lan"}}` — cau da nan DA LUU BEN cua tung doan.

    ⭐ Doc tu `outputs` cua don vi viec, tuc tu CSDL: no la thu duy nhat song
       qua ca mot lat cat (`TiepNoi` + `db.rollback()` cua `thi_hanh`) lan mot
       lan bi giet (`job_runner._het_gio` -> `os._exit(3)`).
    """
    from . import features

    ra: dict[str, dict] = {}
    for it in features.cac_don_vi(db, run.id, pipeline.VOICE_SYNTHESIS):
        g = (it.outputs or {}).get(KHOA_CHU_NAN)
        if isinstance(g, dict) and g.get("chu"):
            ra[str(it.item_key)] = dict(g)
    return ra


def _ghi_chu_da_nan(db, run, *, ma: str, chu_goc: str, chu: str,
                    lan: int) -> None:
    """Luu BEN cau da nan vao `outputs` cua don vi viec cua chinh doan `ma`.

    🔴 **`UPDATE ... WHERE revision = :r`, cung khuon voi `su_dung.danh_dau_xong`
       va `su_dung.mo_lai_don_vi`.** `tables.py` khai cot `revision` de *"bien
       mot cuoc dua thanh mot xung dot NHIN THAY DUOC thay vi mot ban ghi de"*;
       mot phep gan ORM tran o day se la duong ghi THU BA cua cung mot bang, va
       la duong duy nhat di vong qua lop bao ve do.

    ⛔ GOP vao `outputs`, ⛔ khong ghi de: `mo_lai_don_vi` cat `y_canh` (ly do
       vong sua) o cung cho, va vut no la vut dung thu giai thich vi sao doan
       nay bi lam lai.
    """
    from sqlalchemy import update

    from .tables import AsvWorkItem

    it = su_dung.mo_don_vi(db, run, stage=pipeline.VOICE_SYNTHESIS,
                           item_key=str(ma))
    rev = int(it.revision or 1)
    ra = db.execute(
        update(AsvWorkItem)
        .where(AsvWorkItem.id == it.id, AsvWorkItem.revision == rev)
        .values(revision=rev + 1,
                outputs={**(it.outputs or {}),
                         KHOA_CHU_NAN: {"chu_goc": str(chu_goc),
                                        "chu": str(chu), "lan": int(lan)}}))
    if ra.rowcount != 1:
        raise su_dung.XungDotDonVi(
            _t('Đơn vị việc đã được cập nhật ở tiến trình khác.'))
    db.flush()
    db.expire(it)


def _chu_ke(khes: list[nan_thoi_luong.Khe], k: int, buoc: int) -> str:
    """Chu cua khe lien TRUOC (`buoc=-1`) hoac lien SAU (`buoc=+1`) khe thu `k`.

    ⭐ **Vi sao ham nay ton tai.** `loi_nhac_nan_lo` gui model mot LO doan roi
       rac; rut mot cau ma ⛔ khong biet cau ke noi gi thi de rut mat chu ngu ma
       cau sau dang tro toi ("Anh ta...", "Cai do..."). Mot cau chinh xac ma cau
       ke hoa vo nghia la mot ban long tieng te hon.

    ⛔ Rong o hai dau, ⛔ khong vong lai: khe dau tien ⛔ khong co cau truoc, va
       lay cau CUOI lam "cau truoc" cua no la dung mot ngu canh sai — te hon
       khong co ngu canh nao.
    """
    j = int(k) + int(buoc)
    if j < 0 or j >= len(khes):
        return ""
    return str(khes[j].chu or "")


def _lan_doc_lai(db, run) -> dict[str, int]:
    """`{ma: so vong sua da dat lai doan nay o voice_synthesis}` — tu SO CAI.

    Doc cac dong vong sua (`jobs.NANG_LUC_VONG_SUA`) ma `_sua_chua_neu_can` ghi
    TRUOC khi dat lai: mot con so ben qua worker chet, va la ham cua du lieu
    da ghi chu khong phai cua mot bo dem trong bo nho.
    """
    from . import sua_chua
    from .jobs import DON_VI_SUA, NANG_LUC_VONG_SUA

    ke = [dict(getattr(d, "ghi_chu", None) or {})
          for d in su_dung.cac_dong(db, run, stage=pipeline.QC, item_key=DON_VI_SUA)
          if d.nang_luc == NANG_LUC_VONG_SUA]
    return sua_chua.lan_doc_lai(ke)


def _van_tay(ma: str, chu: str, ma_giong: str, preset: str, *,
             tu_dien: dict, lan: int = 0) -> str:
    """Van tay cua MOT doan tieng.

    🔑 Gom **van ban da nan** chu khong phai van ban goc: sau mot vong nan, doan
       nay la ket qua cua mot cau KHAC, va dung lai tep cu la giao mot cau ma ta
       vua quyet dinh la khong vua.
    """
    vt = giong_noi.van_tay_doan(ma_doan=ma, chu=chu, voice_id=ma_giong,
                                preset=str(preset or ""),
                                tu_dien=tu_dien or None)
    if not lan:
        # ⛔ `lan=0` giu NGUYEN van tay cu: moi doan chua tung bi sua dung lai
        #    cache y nhu truoc.
        return vt
    import hashlib
    return hashlib.sha256(f"{vt}|doc_lai:{int(lan)}".encode()).hexdigest()[:len(vt)]


def _ke_nan(kq) -> dict:
    """Phan cua ban ke ma TIMING doc de biet doan nao can co gian."""
    d = {"khe": round(kq.khe, 3), "trang_thai_nan": kq.trang_thai,
         "so_vong_nan": kq.so_vong}
    if kq.he_so_co_gian and kq.he_so_co_gian != 1.0:
        d["he_so_co_gian"] = kq.he_so_co_gian
    return d


#: Toi da bao nhieu luot XIN cho MOT lo (⛔ ke ca luot dau, ⛔ khong phai "3 lan
#: retry sau luot dau"). Mot lo con thieu ma sau ba luot thi luot thu tu cung
#: khong cuu — con moi luot la 15,6-17,7 giay tien that (do 26/09).
LAN_XIN_NAN_LO = 3


def _nan_lo(db, run, cac: list[dict], *, luot: int = 0, ctx=None,
            truoc_lo=None, sau_lo=None) -> dict[str, str]:
    """Xin model viet lai NHIEU doan trong 1..N loi goi. Tra ve `{ma: chu moi}`.

    🔑 **Ke nhiem cua `_viet_lai` (bo 26/09).** Ban cu xin MOT doan mot loi goi
       va nam TRONG vong TTS, nen mot video vai chuc doan tran la vai chuc lan
       khu hoi 16 giay — do duoc: 751 s trong 943 s cua giai doan. Nay phep do
       nam o `[B]` (`Khe.giay_can`), nen ca video chi con 1..N loi goi.

    ⛔ **Mot ma thieu ⛔ KHONG duoc lam chet ca luot chay.** Cau goc van doc duoc,
       chi la khong vua — va `nan_cho_vua.ket_luan` se xep no vao `CO_GIAN` hoac
       `CAN_SUA`, ca hai deu vao `tom_tat` va `CAN_SUA` chay thang vao vong sua.
       Nen suy giam o day la suy giam **CO GHI SO**, ⛔ khong phai mat mat am
       tham. (Cung lap luan voi `_viet_lai` cu, ma `loi.py` va `pipeline.py` van
       dan den bang ten.)

    ⭐ **Xin lai bang cach THEM MOT KHOANG TRANG vao cuoi loi nhac** — meo cua
       `VideoLingo`: mot loi nhac giong y het co the nhan lai dung phan hoi thieu
       ma tu cache cua cua LLM, nen phai doi mot byte de pha cache. ⛔ Khong doi
       NOI DUNG: doi noi dung la doi phep thu, con ta dang hoi LAI cung mot cau.

    ⚠️ `item_key` mang `luot` (so lat cat): mot lat noi tiep xin lai cho cac doan
       CHUA doc, va do la tien THAT tieu lan hai — mot `ma_dispatch` trung se bi
       `UNIQUE(run_id, ma_dispatch)` chan va lan tieu ay bien mat khoi so cai.
    """
    import dataclasses

    from . import ai, cai_dat as cd, dich_thuat

    # ⛔ `RUT_NGAN_CHO_VUA` khai `truong_bat_buoc=("doan",)` — dung cho loi nhac
    #    MOT doan. Loi nhac LO tra ve mot doi tuong PHANG, khoa la ma doan, nen
    #    ep khoa `doan` o day se tu choi dung mot phan hoi **lam dung y nguyen
    #    loi dan** — chinh cai bay `DOC_CANH` da tra gia (`ai.py`: *"Khai bao va
    #    loi dan mo ta hai luoc do khac nhau"*).
    #
    # 🔑 **Ban sao noi long chi dung o CHO DOC, ⛔ khong o cho GOI.** `goi_tinh_tien`
    #    nhan CHINH `ai.RUT_NGAN_CHO_VUA`: mot ban sao `dataclasses.replace` co
    #    cung `.ma` (nen gia, model, muc suy nghi, so cai khong doi mot byte)
    #    nhung **truot moi phep so `is`** — va hai ban gia trong `tests/
    #    test_441` va `tests/test_4600` phan nhanh bang `thao_tac is
    #    ai.RUT_NGAN_CHO_VUA`. Mot doi tuong "giong het" di qua cho goi la cach
    #    lam mot bo do im lang doi nhanh.
    doc_bang = dataclasses.replace(ai.RUT_NGAN_CHO_VUA, truong_bat_buoc=())
    ngon_ngu_dich = cd.doc(run).ngon_ngu_dich

    ra: dict[str, str] = {}
    for so_lo, lo in enumerate(
            dich_thuat.chia_lo(cac, moi_lo=dich_thuat.DOAN_MOI_LO), start=1):
        # ⭐ **Cua nhuong, va no phai o DAY — TRUOC khi tieu lo nay.** Truoc
        #    26/09 khoi `[E]` ⛔ khong co mot `lc.kiem()` nao: 200 lo xau nhat la
        #    ~10.600 s tren mot ngan sach lat 4.590 s, nen `job_runner._het_gio`
        #    ban `os._exit(3)` giua chung voi `retry=False` — lan chay hong HAN,
        #    va (truoc `sau_lo`) ca luot nan da tieu bi `rollback` theo.
        if truoc_lo is not None:
            truoc_lo()
        can = {str(d["ma"]) for d in lo}
        con = list(lo)
        for lan in range(LAN_XIN_NAN_LO):
            tin = nan_cho_vua.loi_nhac_nan_lo(con, ngon_ngu_dich=ngon_ngu_dich)
            if lan:
                tin[-1]["content"] += " " * lan
            try:
                goi = ai.doc_ket_qua(
                    ai.goi_tinh_tien(db, run, ai.RUT_NGAN_CHO_VUA, tin,
                                     stage=pipeline.VOICE_SYNTHESIS,
                                     item_key=f"nan_lo:{luot}:{so_lo}:{lan}",
                                     ctx=ctx),
                    doc_bang)
            except (ai.AiError, ai.AiMoHo, giong_noi.MayBan,
                    nan_cho_vua.NanError) as exc:
                # 🔴 **`MayBan` PHAI nam trong danh sach nay, va no tung khong.**
                #    06/09 mot ban va o `ai.goi` doi may-ban tu `AiError` sang
                #    `MayBan`; `MayBan` ke thua `RuntimeError`, ⛔ KHONG ke thua
                #    `AiError`, nen tu do no **lot qua** tay bat nay va lam
                #    `voice_synthesis failed_terminal` o luot nghiem thu 07/09
                #    16:58 — dung dieu docstring tren cam.
                log.warning("nan lo %d (luot %d, lan %d) hong: %s - giu cau goc",
                            so_lo, luot, lan, exc)
                break
            ra.update(nan_cho_vua.doc_nan_lo(goi, can=can))
            # ⚠️ `set(can) - set(ra)` la phep tru BAT BUOC: mot lo thieu MOT ma
            #    va mot lo thieu CA LO la hai tinh huong rat khac nhau, va chi
            #    phep tru nay phan biet duoc chung.
            con = [d for d in lo if str(d["ma"]) not in ra]
            if not con:
                break
        thieu = sorted(can - set(ra))
        if thieu:
            log.warning("nan lo %d: thieu %d/%d ma sau %d luot xin (%s) - GIU "
                        "CAU GOC cho chung", so_lo, len(thieu), len(can),
                        LAN_XIN_NAN_LO, thieu[:5])
        # ⭐ Chot NGAY lo nay (luu ben + `commit`), ⛔ khong doi het moi lo: mot
        #    lo da tra tien ma chua ben la mot lo se bi xin lai o lat sau.
        if sau_lo is not None:
            sau_lo({m: ra[m] for m in can if m in ra})
    return ra


def _ghi_so(db, run, *, ma: str, van_tay: str, giay: float, kq) -> None:
    """Ghi MOT dong so cai cho mot doan tieng DA GIAO.

    ⭐ Don vi la **giay**, khong phai luot: khach tra tien cho do dai tieng noi
       duoc sinh ra, va mot doan dai gap ba lan mot doan khac thi khong the tinh
       bang nhau. `su_dung.GIAY` co san cho viec do.
    """
    try:
        su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key=ma,
                    su_dung=su_dung.SuDung(
                        nang_luc="tong_hop_tieng", app_chu="ltt_voice",
                        trang_thai=su_dung.DA_GIAO, don_vi=su_dung.GIAY,
                        so_luong=float(giay), credit=0,
                        ma_dispatch=f"giong:{ma}:{van_tay[:16]}",
                        ghi_chu={"trang_thai_nan": kq.trang_thai,
                                 "so_vong": kq.so_vong}))
    except su_dung.DaGhiRoi:
        # ⭐ Rang buoc `UNIQUE(run_id, ma_dispatch)` vua chan mot lan tinh tien
        #    thu hai cho cung mot doan. Do la thanh cong, khong phai loi.
        log.info("so cai da co doan tieng %s - bo qua lan ghi trung", ma)


def _doan_trong_staging(kho: Storage, khoa_tam: str):
    """So giay cua mot doan con nam trong staging, hoac None.

    Khong doi mot ban ghi `AsvAsset` — do la thu chua kip ghi khi giai doan
    truot giua chung. Nhung van **do lai tren tep that**: mot tep dang do trong
    kho trong y het mot tep xong.
    """
    try:
        if not kho.exists(khoa_tam):
            return None
        duong = kho.local_path(khoa_tam) if hasattr(kho, "local_path") else None
        if not duong:
            return None
        return giong_noi.kiem_tep_tieng(duong)
    except Exception as loi_doc:    # noqa: BLE001 - khong doc duoc = khong dung lai
        # ⛔ Khong nuot im: mot tep staging khong doc duoc **khong** phai su co
        #    (ta chi don gian sinh lai doan do), nhung neu no xay ra o MOI doan
        #    thi phep dung lai da chet mot cach im lang va hoa don tang len ma
        #    khong ai thay. Mot dong log la thu duy nhat phan biet hai canh do.
        log.info("khong dung lai duoc doan trong staging %s (%s)",
                 khoa_tam, type(loi_doc).__name__)
        return None


def _doan_con_dung(db, kho: Storage, run, khoa: str):
    """Thoi luong cua mot doan da co san VA con dung, hoac None.

    Hai dieu kien, ca hai bat buoc (I10): ban ghi con, **va** tep con song va
    con dung checksum. "Co mot tep dung ten" khong phai la cache hop le (O13).
    """
    from .tables import ASSET_OK, AsvAsset
    from sqlalchemy import select

    row = db.execute(select(AsvAsset).where(
        AsvAsset.storage_key == khoa,
        AsvAsset.owner_id == run.owner_id)).scalars().first()
    if row is None:
        return None
    if assets.kiem_toan_ven(db, kho, row) != ASSET_OK:
        return None
    duong = kho.local_path(khoa) if hasattr(kho, "local_path") else None
    if not duong:
        return 0.0      # khong doc duoc duong dan cuc bo: tin ban ghi da kiem
    try:
        return giong_noi.kiem_tep_tieng(duong)
    except giong_noi.GiongError:
        return None
