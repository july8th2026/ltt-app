"""Giai doan QC — BO DO va BAO CAO. ⛔ KHONG phai cong cam phat hanh.

Mot artifact ra:

    qc_report.json    bao cao muoi hai dung sai   (kind=json)

## 🔴 Doi huong 27/09/2026 (chu du an chot)

Ban truoc: QC hong ⇒ giai doan hong ⇒ ca lan chay ve `error` ⇒ khach nhan **⛔
khong gi ca**. Ly le cu — *"mot cong khong chan thi khong phai cong"* — dung ve
nguyen tac, nhung nguyen tac ay chi dung khi **con so cua cong dang tin**.

⚠️ Va do duoc rang chung ⛔ KHONG dang tin. Ba luot chay THAT (27/09) bi chan boi
   bon roi ba roi hai muc, trong do:

     T2  — SAI: chinh QC chia `toc_do` HAI LAN (`_thoi_luong_mong_doi` tra hai
           truc khac nhau tuy nhanh). Da sua.
     T18 — SAI: tham chieu 1083 khung / 30 fps vs ban giao 1351 khung / 37,5 fps
           ⇒ phep SO SANH lech, ⛔ khong phai hinh kem. Nay TAT mac dinh.
     T17 — THAT nhung vo hai voi nguoi xem: moc DTS trung, moi trinh phat bo qua.

⇒ Mot cong chan bang nhung con so nhu the ⛔ khong bao ve khach — no **giu hang
  cua khach lai**.

## Nen QC nay GHI va DI TIEP

`thi_hanh` doc `_qc_hong`, ghi mot dong `warning`, va lan chay **di tiep**. Thu
KHONG duoc mat la **phat hien**:

    ket_qua["qc_muc_hong"]      danh sach ma
    ket_qua["qc_ky_thuat_dat"]  `False` khi co muc hong
    qc_report.json              bao cao day du (promote TRUOC, nhu cu)
    mot dong log `warning`      cho nguoi van hanh

⭐ Mot bo do bi tat cong van la mot bo do; mot bo do bi **xoa so** thi ⛔ khong
   con gi. Do la khac biet duy nhat phai giu.

⛔ Va `_qc_hong` + `QcChan` GIU lai: chung la cho de chan lai MOT SO muc (vd
   T17) neu chu du an muon, ⛔ khong phai ma chet.
"""
from __future__ import annotations

import io
import json
import logging
from pathlib import Path
import tempfile

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import assets, cai_dat, nhap_media, pipeline, qc, tach_tieng
from .giai_doan_media import ThieuNguon, _duong_doc_duoc

log = logging.getLogger(__name__)


class ThieuBanRa(ThieuNguon):
    """Chua co ban render de kiem."""


def _khoa_theo_duoi(db, run, ten_giai_doan: str, duoi: str) -> str:
    from . import features
    s = features.giai_doan_theo_ten(db, run.id, ten_giai_doan)
    return next((k for k in ((s.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(duoi)), "") if s else ""


def _doc_json(kho: Storage, khoa: str) -> dict:
    with kho.open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def _bam_hai_ben(duong_ra: str, duong_nguon: str) -> tuple[str, str, str]:
    """`(bam_ra, bam_nguon, ly_do)` cho T3. `ly_do` rong = bam duoc.

    ⭐ Tach ra khoi `chay` de LY DO khong chay duoc tro thanh mot **gia tri tra
       ve** thay vi mot dong log: mot dong log ⛔ khong vao artifact, ⛔ khong
       vao `stage.outputs`, va ⛔ khong ai doi chieu duoc no sau khi lan chay
       ket thuc. Xem `tom_tat_kem_khong_do`.
    """
    try:
        return qc.bam_luong_hinh(duong_ra), qc.bam_luong_hinh(duong_nguon), ""
    except Exception as exc:  # noqa: BLE001 - khong do duoc != do ra sai
        log.warning("qc: khong bam duoc luong hinh (%s: %s)",
                    type(exc).__name__, exc)
        return "", "", f"{type(exc).__name__}: {exc}"


def _do_hinh_hai_ben(duong_ra: str, duong_nguon: str, *, tt_ra: dict,
                     tt_nguon: dict, bam_khop: bool
                     ) -> tuple[dict | None, dict | None, str]:
    """`(hinh_ra, hinh_nguon, ly_do)` cho T13 + T17. `ly_do` rong = do duoc.

    ⭐ Nguon chi can do khi luong hinh KHONG giong nguon tung bit: o preset giu
       hinh ma bam khop (T3), luong hinh ra CHINH LA luong hinh nguon, nen so do
       cua nguon = so do cua ban ra — giai ma lan hai la tra tien cho mot cau
       tra loi da biet.
    """
    try:
        hinh_ra = qc.do_hinh(
            duong_ra, thoi_luong=float(tt_ra.get("thoi_luong") or 0.0))
        if bam_khop:
            return hinh_ra, {"den_s": hinh_ra["den_s"],
                             "dong_s": hinh_ra["dong_s"]}, ""
        return hinh_ra, qc.do_hinh(
            duong_nguon,
            thoi_luong=float(tt_nguon.get("thoi_luong") or 0.0)), ""
    except Exception as exc:  # noqa: BLE001 - khong do duoc != do ra sai
        log.warning("qc: khong do duoc hinh (%s: %s)",
                    type(exc).__name__, exc)
        return None, None, f"{type(exc).__name__}: {exc}"


#: Bien bat T18 (VMAF). **Mac dinh TAT (chu du an chot 27/09).**
#:
#: 🔴 **Vi sao tat, va cai gia.** T18 la cong DUY NHAT canh chat luong hinh sau
#:    ma hoa lai. Tat no la mat cong do — dieu phoi da neu ro truoc khi chu du an
#:    quyet, va quyet dinh la cua chu du an.
#:
#: ⚠️ Nhung con so no cho hien **⛔ khong dang tin**, va do duoc: tren ba luot
#:    chay that lien tiep no ra `trung_binh = 53,783` **bit-identical**, kem
#:    `nho_nhat = 1,452` — mot VMAF 1,45 nghia la gan nhu ⛔ khong giong gi, va do
#:    ⛔ khong the la ton that cua bo ma hoa o `cq = 28`. Goc: ban tham chieu co
#:    **1083 khung / 30 fps** trong khi ban giao co **1351 khung / 37,5 fps** —
#:    hai ben dung HAI chinh sach nhip khac nhau, nen phep SO SANH sai, ⛔ khong
#:    phai hinh kem. Mot cong bao dong vi chinh no hong la mot cong chan moi ban
#:    giao co doi toc do.
#:
#: 🔑 Va no ton **32 giay moi job** (do: 32,07 s va 33,6 s tren hai luot that).
#:    Tra 32 giay cho mot con so ⛔ khong ai dam dung la mot khoan chi thuan.
#:
#: ⭐ Cung khuon voi `giai_doan_qc_ai.BIEN_BAT`: doi dung `"1"`, ⛔ khong nhan
#:    `"true"`/`"yes"` — mot cong tieu tien phai kho bat mot cach co chu dich.
#:    Bat lai bang `LTT_ASV_QC_T18=1` de do sau khi sua xong phep so sanh.
BIEN_T18 = "LTT_ASV_QC_T18"


def t18_bat() -> bool:
    """T18 (VMAF) co duoc bat khong. **Mac dinh TAT.** Xem `BIEN_T18`."""
    import os

    return str(os.environ.get(BIEN_T18, "")).strip() == "1"


def tom_tat_kem_khong_do(bao_cao: dict, ly_do: dict) -> dict:
    """`qc.tom_tat` + **phep do nao ⛔ KHONG chay duoc**, kem ly do.

    🔴 **Vi sao truong nay phai ton tai: `dat = not hong`, va `KHONG_AP_DUNG`
       ⛔ khong phai `hong`.**

       Mot luot ma thieu `libvmaf`, ffmpeg bam khong noi luong hinh, va luot
       giai ma ca tep het thoi gian ⇒ T3, T13, T17, T18 deu ha xuong
       `KHONG_AP_DUNG`, va bao cao in ra `dat: True`, `so_muc_hong: 0`,
       `qc_ky_thuat_dat: True`. Tuc **bao DAT sau khi ⛔ khong do gi** — dung ho
       loi cua gate o `f4c4f064`: *mot chu PASS dung mot minh tren mot phep do
       chua he chay*.

    ⭐ Va tu 27/09 (QC thoi lam cong chan) truong nay QUAN TRONG HON, ⛔ khong
       kem hon: khi ⛔ khong con gi chan thi mot chu `dat: True` la thu DUY NHAT
       nguoi doc thay, nen no phai noi duoc *"DAT tren bao nhieu phep do THAT"*.

    ⭐ `ly_do` la thu CHINH CHO NEM ra ghi lai (`_bam_hai_ben`,
       `_do_hinh_hai_ben`, `_do_vmaf`), ⛔ khong phai suy nguoc tu chuoi `mo_ta`
       cua bao cao: doc mot trang thai bang cach do chuoi la mot phep kiem se
       im lang khi ai do sua mot cau tieng Viet.

    ⛔ Va chi dem giao cua `ly_do` voi cac muc THAT SU `KHONG_AP_DUNG`: T8/T9/T10
       khong ap dung **theo thiet ke**, T3 khong ap dung o preset cat, T18 khong
       ap dung o preset giu hinh — dem ca chung thi moi lan chay deu "thieu phep
       do" va con so thanh tieng on, roi nguoi ta tat no (ho `banh coc bao dong
       gia`). Va nguoc lai: mot phep do TUNG hong nhung cuoi cung VAN co ket qua
       (vd bam ra rong ma T3 van DAT o nhanh khac) ⛔ khong duoc dem la thieu.
    """
    tt = dict(qc.tom_tat(bao_cao))
    treo = {str(m["ma"]) for m in (bao_cao.get("muc") or [])
            if m.get("trang_thai") == qc.KHONG_AP_DUNG}
    khong_do = sorted(ma for ma in ly_do if ma in treo)
    tt["qc_so_muc_khong_do"] = len(khong_do)
    tt["qc_muc_khong_do"] = khong_do
    tt["qc_ly_do_khong_do"] = {ma: str(ly_do[ma])[:300] for ma in khong_do}
    return tt


def _thoi_luong_mong_doi(ke_hoach: dict, goi_ke_cat: dict, bien_tap=None,
                         *, cua_so_khach=None) -> float:
    """Do dai (giay) ma TEP DUOC DO phai co, **tren TRUC BAN RA** (sau `toc_do`).

    🔴 **Sua 28/09 (B9-4) — ham nay tung ⛔ KHONG biet cua so `cat_dau_cuoi`.**

       `image_finish` ap HAI phep cat chong len nhau, va chi phep thu nhat nam
       trong `ke_cat`:

           ke_cat            phep cat TU DONG cua chinh sach (canh hong)
           cat_dau_cuoi      cua so KHACH tu keo, ap qua `cat_dau_cuoi.giao`

       Do T1a (28/09, production `fd565a474551`): ke cat tu dong ⛔ khong cat gi
       (`cat: []`) nen ban do cua no la phep DONG NHAT, con cua so khach
       `[0,05 ; 0,95]` cat mat 10 %:

           mong doi (cu)  220,007  = 275,008 / 1,25      ⛔ thieu cua so khach
           tep giao       198,002  = 275,008 x 0,90 / 1,25
           ⇒ `lech = -22,005 s`, va T2 **hong tren mot ban giao dung**.

    ⭐ **⛔ Khong doc `image_finish.thoi_luong_ra` cho tien**, du con so dung da
       nam san o do. Lam vay la de QC hoi CHINH giai doan vua cat *"anh cat bao
       nhieu"* — mot loi cat sai se duoc chinh no xac nhan. Thay vao do ham nay
       **tu dung lai** phep giao tu HAI ban khai doc lap (`ke_cat` la artifact,
       `cat` la cai dat cua khach), bang CHINH `cat_dau_cuoi.giao` ma GD2 dung.

    🔴 **Sua 27/09 — truoc do ham nay tra HAI TRUC KHAC NHAU tuy nhanh, va nguoi
       goi ap `moc_ban_ra` cho CA HAI:**

         co ke cat  -> `ke.ban_do().thoi_luong_ra` cua `image_finish`. Giai doan do
                       cat **ban ra cua render**, tuc con so nay DA o tren truc SAU
                       `toc_do`.  ⇒ chia them mot lan nua la ap `toc_do` HAI LAN.
         ⛔ khong    -> `tong_ms` cua ke hoach = do dai NGUON, tuc TRUOC `toc_do`.
                       ⇒ o nhanh nay phep chia la DUNG.

       Do tren lan chay that `asvr_3059dc3d` (nguon 45,121 s, `toc_do = 1,25`):
         tep giao        = 36,077 s
         compose hua     = 36,097 s   (= 45,121 / 1,25 — DUNG)
         T2 mong doi     = 28,862 s   (= 36,077 / 1,25 — SAI, chia lan hai)
         ⇒ `lech = 7,215 s`, va T2 **hong tren mot ban giao dung**.

    ⭐ Ban va 27/09: ham TU dua ca hai nhanh ve **mot truc**. B6 di xa hon va bo
       han NGUYEN NHAN: `render` thoi doi moc thoi gian, nen hai nhanh vao ham
       nay ⛔ khong con o hai truc — phep chia ra NGOAI nhanh, ap dung MOT lan.

    ⭐ MOT noi tra loi cau hoi nay, va no tra loi tu mot BAN KHAI:

        co ke cat  -> `ke_cat.KeCat.ban_do().thoi_luong_ra`
        khong      -> `tong_ms` cua ke hoach (= do dai nguon, giai doan 1 khong cat)

    ⛔ **⛔ Khong doan tu tep dang do.** Suy do dai mong doi tu chinh tep la bien
       mot phep kiem thanh mot phep tu khang dinh — no se xanh voi MOI tep.

    ⚠️ Doc lai thi kiem lai (I8): `ke_cat.kiem` chay o day nua, nen mot ke cat
       vuot tran 5 % ⛔ khong the di qua cong nay bang cach duoc ghi ra tep.
    """
    from . import cat_dau_cuoi as _cdc, ke_cat as _kc
    from .bien_tap import moc_ban_ra

    # ⭐ **Sau B6 (27/09) CA HAI nhanh o CUNG mot truc — truc NGUON.** `render` ⛔
    #    khong con doi moc thoi gian, nen `KeCat.ban_do().thoi_luong_ra` (do dai
    #    sau cat) va `tong_ms` (do dai nguon) deu la mocs TRUOC `toc_do`.
    #
    # 🔑 **Va vi the phep chia ra NGOAI nhanh.** Do chinh la ban sua tan goc cho
    #    T2: truoc B6 hai nhanh tra hai TRUC khac nhau, nen mot phep chia dat
    #    ngoai nhanh thi sai mot nhanh, dat trong nhanh thi ⛔ khong ai doc noi
    #    hop dong. Nay chi co MOT truc vao va MOT truc ra, nen `moc_ban_ra` la
    #    phep cuoi cung, ap MOT lan, cho MOI duong.
    #
    # ⚠️ `dai_vao` la do dai ban ra cua GD1 — CUNG con so ma `image_finish` dung
    #    lam `thoi_luong` khi no giao cua so. Ca hai nhanh duoi deu lay tu ban
    #    khai, ⛔ khong tu tep dang do.
    if goi_ke_cat:
        ke = _kc.KeCat.tu_dict(goi_ke_cat)
        _kc.kiem(ke)
        giu = list(ke.giu)
        dai_vao = float(goi_ke_cat.get("thoi_luong") or ke.ban_do().thoi_luong_ra)
    else:
        # ⭐ `tong_ms` = do dai NGUON (giai doan 1 ⛔ khong cat gi).
        dai_vao = float(ke_hoach.get("tong_ms") or 0) / 1000.0
        giu = [(0.0, dai_vao)]

    # 🔑 **Cung ham, cung thu tu voi `giai_doan_hinh_anh.chay`** — cua so khach
    #    la mot lop THU HEP dat len tren ke cat, ⛔ khong phai mot phep song song.
    #    Goi lai chinh `giao` thay vi nhan mot phan so la cach duy nhat de mot
    #    ngay nao do luat giao doi ma QC ⛔ khong lang le lech theo.
    cua = _cdc.chuan_hoa(cua_so_khach)
    khoang = _cdc.giao(giu, cua, dai_vao) if cua else giu
    return moc_ban_ra(sum(k - b for b, k in khoang), bien_tap)


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Do ban ra so voi muoi hai dung sai. Tra ve bao cao, KHONG nem.

    ⚠️ Ham nay khong quyet dinh so phan cua lan chay. No do va bao cao; `thi_hanh`
       doc `_qc_hong` roi nem `QcChan` **sau khi** artifact da duoc promote — thu
       tu do la thu giu lai bang chung khi mot lan chay hong.

    ⭐ Ban dau o day co mot lop `QcKhongDat` cho muc dich do, va no chua bao gio
       duoc nem tu bat cu dau. Chinh guard chot-tap-hop cua `test_418` bat duoc:
       mot lop ngoai le khong ai nem van la mot lop phai phan loai, va lan theo
       no thi thay no la ma chet. Da go.
    """
    # 🔴 **Do tep cua IMAGE_FINISH — tep KHACH NHAN (b4 hai giai doan, 25/09).**
    #    `render` giao mot ban trung gian chua qua phep cat cua giai doan 2. Do
    #    ban trung gian la chung nhan mot tep ⛔ khong ai duoc giao, tuc mot cong
    #    ⛔ khong canh giu ban giao.
    khoa_ra = _khoa_theo_duoi(db, run, pipeline.IMAGE_FINISH, ".mp4")
    if not khoa_ra:
        raise ThieuBanRa(_t('Chưa có bản kết xuất để kiểm.'))
    # ⭐ Ke cat nam trong `outputs` cua `image_finish`, ⛔ khong thanh artifact:
    #    moi artifact cua giai doan do la BAN GIAO (`han=None`), va mot bao cao
    #    van hanh ⛔ khong duoc nam trong kho cua khach mai mai.
    from . import features as _ft
    _s_if = _ft.giai_doan_theo_ten(db, run.id, pipeline.IMAGE_FINISH)
    _out_if = (_s_if.outputs or {}) if _s_if else {}
    goi_kc = _out_if.get("ke_cat") or {}
    khoang_gd2 = _out_if.get("khoang_giu") or ()
    khoa_kh = _khoa_theo_duoi(db, run, pipeline.TIMING_ALIGN, ".json")
    khoa_ke = _khoa_theo_duoi(db, run, pipeline.VOICE_SYNTHESIS, ".json")
    khoa_ban = _khoa_theo_duoi(db, run, pipeline.COMPOSE, ".json")
    if not (khoa_kh and khoa_ke and khoa_ban):
        raise ThieuBanRa(_t('Chưa đủ tài liệu thượng nguồn để kiểm chất lượng.'))

    bao = None
    if ctx is not None and getattr(ctx, "progress", None):
        bao = ctx.progress

    ke_hoach = _doc_json(kho, khoa_kh)
    ban_ke = _doc_json(kho, khoa_ke)
    ban_dung = _doc_json(kho, khoa_ban)

    if bao:
        bao(15, _t('Đang đo bản kết xuất'))

    with tempfile.TemporaryDirectory(
            prefix=f"asv-qc-{str(run.id)[:12]}-") as tam:
        thu_muc = Path(tam)
        duong_ra = _duong_doc_duoc(kho, khoa_ra, thu_muc)
        duong_nguon = _duong_doc_duoc(kho, run.source_key, thu_muc)

        tt_ra = nhap_media.soi(duong_ra)
        tt_nguon = nhap_media.soi(duong_nguon)

        if bao:
            bao(45, _t('Đang đo âm lượng'))
        am_luong = tach_tieng.do_am_luong(duong_ra)

        # ── Che do render quyet dinh QC do CAI GI ──────────────────────────
        #
        # 🔑 Doc tu BAN DUNG, khong suy lai tu `settings`: ban dung la thu da
        #    thuc su duoc render, va neu hai nguon lech nhau thi cai dung la cai
        #    da chay. Suy lai o day se cho QC do mot lan chay khac voi lan chay
        #    that.
        from . import che_do_render as cdr

        cach = str((ban_dung.get("hinh") or {}).get("cach_render") or cdr.SAO_CHEP)

        # ── Thoi luong MONG DOI (b4 hai giai doan, 25/09) ───────────────────
        #
        # 🔴 Truoc b4, dong nay doc `ke_hoach["ban_do"].thoi_luong_ra` — ngan hon
        #    nguon dung bang phan `edit_plan` da cat. Nay giai doan 1 ⛔ KHONG cat
        #    gi, nen mong doi la **do dai nguon**, cho CA HAI preset. Cat canh o
        #    giai doan 2 (`giai_doan_hinh_anh`), va cong nay do dung tep ma giai
        #    doan 2 giao.
        #
        # ⭐ asv-final: truc bien tap -> ban ra la mot phep chia cho `toc_do`.
        #
        # 🔴 Sua 27/09: phep doi truc ay nay nam TRONG `_thoi_luong_mong_doi`, vi
        #    hai nhanh cua no tra hai TRUC khac nhau va o day ⛔ khong ai biet
        #    nhanh nao da chay. Ap `moc_ban_ra` o day lam nhanh "co ke cat" bi
        #    chia `toc_do` LAN THU HAI — T2 hong tren mot ban giao dung. Xem
        #    docstring cua ham do de co so do.
        # 🔴 **Nguon cua `toc_do` doi tu ARTIFACT sang CAI DAT (B6, 27/09).**
        #    Truoc B6, GD1 ghi `toc_do` vao `ban_dung.hinh.bien_tap` va QC doc no
        #    o day. Nay GD1 ⛔ khong con thuc thi — hay ghi — phep bien tap nao;
        #    tep ma cong nay DO la ban ra cua GD2, va GD2 doc `cai_dat.doc(run)`.
        #
        # ⭐ Doc CUNG nguon va CUNG ham loc (`loc_bien_tap_gd2`) voi GD2: hai noi
        #    doc cung mot cai dat ma tu loc rieng la hai co hoi de lech, va lech
        #    o day nghia la QC do mot lan chay KHAC lan chay that.
        from . import giai_doan_hinh_anh as _gdha_bt

        # 🔴 **`cat` phai di cung (B9-4, 28/09).** Cua so `cat_dau_cuoi` la phep
        #    cat THU HAI cua `image_finish`, va no ⛔ khong nam trong `ke_cat`.
        #    Thieu no thi T2 hong tren moi lan chay khach co keo hai tay cam —
        #    do tren T1a: mong doi 220,007 vs tep giao 198,002.
        _cai = cai_dat.doc(run)
        _bt_gd2 = _gdha_bt.loc_bien_tap_gd2(_cai.bien_tap)
        mong_doi = _thoi_luong_mong_doi(ke_hoach, goi_kc, _bt_gd2,
                                        cua_so_khach=_cai.cat)

        # 🔑 Ly do KHONG do duoc cua tung phep kiem — di vao `tom_tat`, tuc vao
        #    `asv_stage.outputs`. Xem `tom_tat_kem_khong_do`.
        ly_do_khong_do: dict[str, str] = {}

        bam_ra = bam_nguon = ""
        if cach != cdr.CAT_MA_HOA_LAI:
            if bao:
                bao(70, _t('Đang đối chiếu luồng hình'))
            # T3 — bam RIENG luong hinh. Neu ffmpeg khong bam duoc thi T3 thanh
            # `khong_ap_dung` chu khong thanh `hong`: khong do duoc khac voi do
            # ra sai.
            #
            # ⭐ Chi bam o che do SAO CHEP. O che do cat, bam la mot phep tinh
            #    chac chan khong khop — ton thoi gian de tra loi mot cau hoi ta
            #    da biet cau tra loi.
            bam_ra, bam_nguon, _ly_do = _bam_hai_ben(duong_ra, duong_nguon)
            if _ly_do:
                ly_do_khong_do["T3"] = _ly_do

        if bao:
            bao(75, _t('Đang kiểm bản ra có hình'))
        # ── T13 + T17: MOT luot giai ma ban ra, mot luot giai ma nguon ────────
        #
        # ⭐ Nguon chi can do khi luong hinh KHONG giong nguon tung bit: o preset
        #    giu hinh ma bam khop (T3), luong hinh ra CHINH LA luong hinh nguon,
        #    nen so do cua nguon = so do cua ban ra — giai ma lan hai la tra
        #    tien cho mot cau tra loi da biet.
        hinh_ra, hinh_nguon, _ly_do = _do_hinh_hai_ben(
            duong_ra, duong_nguon, tt_ra=tt_ra, tt_nguon=tt_nguon,
            bam_khop=bool(bam_ra and bam_ra == bam_nguon))
        if _ly_do:
            # ⚠️ MOT luot giai ma tra loi CA HAI phep kiem, nen mot luot hong
            #    lam CA HAI khong do duoc — khai ca hai, khong khai mot.
            ly_do_khong_do["T13"] = ly_do_khong_do["T17"] = _ly_do

        # ── T18: VMAF — chi preset cat (ma hoa lai) ──────────────────────────
        vmaf = None
        if cach == cdr.CAT_MA_HOA_LAI:
            if not t18_bat():
                # ⛔ TAT co chu dich: ⛔ khong goi `_do_vmaf` (tiet kiem ~32 s), va
                #    khai RO bang mot khoa rieng. `vmaf = None` se lam `qc.kiem`
                #    in "chua do VMAF" — mot cau gop *"co y tat"* voi *"⛔ khong
                #    ro vi sao"*, dung ho loi ma phien nay sua ca ngay.
                vmaf = {"tat": BIEN_T18}
            else:
                if bao:
                    bao(85, _t('Đang đo chất lượng hình (VMAF)'))
                vmaf = _do_vmaf(kho, ban_dung.get("hinh") or {}, thu_muc, run=run,
                                duong_nguon=duong_nguon, duong_ra=duong_ra,
                                tt_ra=tt_ra, khoang_gd2=khoang_gd2)
                if vmaf.get("loi"):
                    ly_do_khong_do["T18"] = str(vmaf["loi"])

        bao_cao = qc.kiem(
            tt_ra=tt_ra, tt_nguon=tt_nguon, am_luong=am_luong,
            ke_hoach=ke_hoach, ban_ke_tieng=ban_ke,
            ban_dung_lop=(ban_dung.get("tieng") or {}).get("lop") or [],
            bam_ra=bam_ra, bam_nguon=bam_nguon,
            # 🔴 **Sua loi o pha 07, khong phai mot doi ten.**
            #
            #    Dong nay tung mac dinh `""` trong khi
            #    `giai_doan_thoi_gian` mac dinh `"fit_original"`. Tuc
            #    mot lan chay thieu khoa se CHAY o `fit_original` con
            #    **bang chung QC ghi rong** — hai cau tra loi khac nhau
            #    cho cung mot cau hoi, va khong cho nao bao loi vi ca hai
            #    deu tim thay mot gia tri hop le cua rieng minh.
            #
            # ⭐ Ban vá lay gia tri ma duong ong THUC SU dung, nen bang
            #    chung thanh dung thay vi thanh khac.
            che_do_thoi_gian=cai_dat.doc(run).timing_mode,
            che_do_render=cach, thoi_luong_mong_doi=mong_doi,
            hinh_ra=hinh_ra, hinh_nguon=hinh_nguon, vmaf=vmaf,
            # 🔴 **Ban khai cua GD2 (B9-4, 28/09).** T15 can chung de doi su kien
            #    phu de sang truc BAN GIAO. Truoc B9 no chi chia `toc_do`, nen
            #    moi su kien nam trong phan DA CAT van bi dem — T1a bao 3 dong
            #    "ngoai bien" tren mot tep ⛔ khong sai gi.
            khoang_giu=[tuple(x) for x in (_out_if.get("khoang_giu") or ())],
            thoi_luong_vao=float(_out_if.get("thoi_luong_vao") or 0.0),
            # ⭐ V6 pha 27. T14/T15 doc tu day: chinh sach render da khai va
            #    su kien phu de DA CHOT. Khong truyen thi ca hai luon tra
            #    `KHONG_AP_DUNG` — mot phep kiem ton tai ma khong ai di qua,
            #    dung hang `nang-luc-co-nhung-khong-ai-di-tren-duong`.
            # ⭐ **`bien_tap` ghep vao TU CAI DAT (B6).** T15 doi moc phu de
            #    sang truc ban giao theo `toc_do`, va tu B6 ban dung GD1 ⛔ khong
            #    con mang truong ay. Thieu no thi moi dong phu de bi so voi mot
            #    do dai NGAN hon dung he so toc do ⇒ T15 bao `hong` tren mot ban
            #    giao dung.
            ban_hinh={**(ban_dung.get("hinh") or {}),
                      **({"bien_tap": _bt_gd2} if _bt_gd2 else {})})

    goi = json.dumps(bao_cao, sort_keys=True, ensure_ascii=False).encode("utf-8")
    vt = _van_tay(kho, khoa_ra, khoa_kh)
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.QC, van_tay=vt, duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if bao:
        bao(95, _t('Đang lưu báo cáo'))

    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt, "parent_keys": [khoa_ra]}],
        # 🔑 `tom_tat` + phep do nao KHONG chay duoc: `dat = not hong` cho
        #    `KHONG_AP_DUNG` di qua lang le, nen mot cong khong do gi van in
        #    `qc_ky_thuat_dat: True`. Xem `tom_tat_kem_khong_do`.
        "tom_tat": tom_tat_kem_khong_do(bao_cao, ly_do_khong_do),
        # 🔑 Nguoi goi (`thi_hanh`) promote bao cao TRUOC roi moi doc co nay va
        #    nem. Nho vay mot lan chay hong van de lai bang chung ve VI SAO.
        "_qc_hong": bao_cao["muc_hong"],
    }


def _do_vmaf(kho: Storage, hinh: dict, thu_muc: Path, *, run, duong_nguon: str,
             duong_ra: str, tt_ra: dict, khoang_gd2=()) -> dict:
    """Dung lai DUNG dau vao ma GD2 that su dung (chu, logo, `.ass`) roi do VMAF.

    🔴 **Logo/lop_phu/khung/lat-guong/dich-mau doc tu `cai_dat.doc(run)`, ⛔
       khong tu `hinh` (gd2-diem-anh, 25/09).** `hinh` (ban dung GD1) khong con
       mang chung — chung thuc thi o GD2, dung `cai_dat` truc tiep. Doc SAI
       nguon o day se lam tham chieu VMAF thieu hoac sai cac bien doi do, va
       T18 bao mot diem cua mot chuoi loc KHONG PHAI chuoi GD2 that dung.

    ⭐ `.ass` sinh tu su kien DA DOI MOC qua `doi_moc_su_kien` — dung ham, dung
       `ban_do` voi GD2 that (`giai_doan_hinh_anh._sinh_srt` dung chung).

    ⛔ Khong do duoc => `{"loi": ...}` => T18 `khong_kha_dung`; khong lui ve
       mot uoc luong tu che.
    """
    from . import bien_tap as _bt, giai_doan_hinh_anh as _gdha
    from . import hinh_hoc as _hh, lop_phu as _lp, phu_de as _pd
    from .ban_do_thoi_gian import BanDoThoiGian
    from .giai_doan_ket_xuat import _tai_ve

    try:
        cai = cai_dat.doc(run)
        ds_logo = list(cai.logo or ())
        lop_phu_ds = list(cai.lop_phu or ())
        bt_gd2 = _gdha.loc_bien_tap_gd2(cai.bien_tap)

        tm = thu_muc / "vmaf"
        tm.mkdir(exist_ok=True)
        duong_chu = _lp.viet_tep_chu(lop_phu_ds, tm)
        duong_logo = []
        for i, lg in enumerate(ds_logo):
            khoa = str(lg["khoa"])
            duong_logo.append(_tai_ve(
                kho, khoa, tm / f"logo{i}{Path(khoa).suffix or '.png'}"))

        ho_so_pd = hinh.get("phu_de") or None
        duong_ass = ""
        if _pd.co_dot_vao_hinh(ho_so_pd):
            # ⭐ `co_dot_vao_hinh(None)` tra `False`, nen nhanh nay ⛔ khong bao
            #    gio thay `None`. `assert` de kiem kieu THAY duoc — ⛔ khong doi
            #    hanh vi.
            assert ho_so_pd is not None
            khoang_gd2_f = [(float(b), float(k)) for b, k in (khoang_gd2 or ())]
            ban_do = BanDoThoiGian.tu_khoang(
                khoang_gd2_f,
                thoi_luong_nguon=max((k for _, k in khoang_gd2_f), default=0.0))
            su_kien = _gdha.doi_moc_su_kien(ho_so_pd.get("su_kien") or [], ban_do)
            rong_nguon = int(hinh.get("rong_khung") or 0)
            cao_nguon = int(hinh.get("cao_khung") or 0)
            rong_ra, cao_ra = (
                _hh.khung_bien_tap(rong_nguon, cao_nguon, bt_gd2)["ra"]
                if bt_gd2 and set(bt_gd2) & set(_bt.TRUONG_HINH_HOC)
                else (rong_nguon, cao_nguon))
            duong_ass = _pd.viet_tep_ass(ho_so_pd, su_kien, tm,
                                         rong=rong_ra, cao=cao_ra)
        # ⭐ Tham chieu chay qua CUNG phep cat cua giai doan 2 — xem
        #    `qc.loc_tham_chieu`. Thieu no thi hai ben lech tung khung va T18
        #    bao `hong` du bo ma hoa khong lam gi sai.
        # ⭐ `toc_do` ⛔ KHONG con la tham so rieng (B6, 27/09): `bt_gd2` nay GIU
        #    `toc_do` vi GD2 la noi ap no, nen `loc_tham_chieu` doc he so tu
        #    chinh ho so ay. Mot con so di RIENG canh ho so cua no la hai cho
        #    khai mot su that — dung hinh dang da sinh ra T2.
        loc = qc.loc_tham_chieu(hinh, duong_chu=duong_chu, duong_ass=duong_ass,
                                khoang_giu=khoang_gd2, ds_logo=ds_logo,
                                lop_phu=lop_phu_ds, bien_tap=bt_gd2)
        return qc.do_vmaf(duong_nguon=duong_nguon, duong_ra=duong_ra,
                          loc_hinh=loc, duong_logo=duong_logo,
                          rong=int(tt_ra.get("rong") or 0),
                          cao=int(tt_ra.get("cao") or 0), thu_muc=str(tm))
    except Exception as exc:          # noqa: BLE001 - khong do duoc != do ra sai
        log.warning("qc: khong do duoc VMAF (%s: %s)", type(exc).__name__, exc)
        return {"loi": f"{type(exc).__name__}: {exc}"}


def _van_tay(kho: Storage, khoa_ra: str, khoa_kh: str) -> str:
    """Doi ban render, doi ke hoach, HAY doi nguong QC deu doi van tay (O13)."""
    import hashlib

    with kho.open(khoa_ra) as f:
        cs_ra = assets.bam(f.read())
    with kho.open(khoa_kh) as f:
        cs_kh = assets.bam(f.read())
    goi = json.dumps({"ra": cs_ra, "ke_hoach": cs_kh,
                      "qc": qc.PHIEN_BAN_QC}, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()
