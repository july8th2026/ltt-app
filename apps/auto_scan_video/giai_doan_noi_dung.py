"""Giai doan CONTENT_PROCESS — viet loi long tieng cho phan DUOC GIU LAI.

Mot artifact ra:

    content.json   ban long tieng, giu nguyen ma doan   (kind=json)

⛔ Ban ghi nguon **BAT BIEN**. Tep nay chi doc `transcript.json`; no khong bao
   gio ghi de len do (Prompt 11, "explicitly forbidden"). Ly do khong phai su
   gon gang — ban ghi la bang chung ve thu may nghe duoc, ban long tieng la mot
   dien giai cua no, va ghi de dien giai len bang chung thi mat kha nang doi
   chieu khi khach khieu nai.

⛔ Prompt 14 cam: khong sinh tieng noi trong giai doan nay.

## 🔴 Pha 14 doi CAI GI o day, va vi sao

Truoc pha 14 giai doan nay **dich ca ban chep loi** — moi doan, ke ca nhung doan
thuoc canh se bi cat. Do la V4-R07, va pha 12 da dong no o phia CHUOI (dat
`EDIT_PLAN` truoc). Pha 14 dong no o phia **noi dung**: dau vao cua giai doan nay
gio la `ban_bien_tap.doan_giu_lai(...)`, tuc **chi nhung doan nam trong canh con
lai**. Mot doan thuoc canh da cat khong duoc gui di, khong duoc tra tien, va
khong duoc xuat hien trong ban ra.

## ⭐ 26/09/2026 — `edit_plan` XUONG GD2, nen o day "KHONG co ban bien tap" la HOP LE

`pipeline.CHUOI` da doi: `edit_plan` chay **sau `render`** (B1 §9a). Nen khi buoc
nay chay, ⛔ **chua co ban bien tap nao** — va do la trang thai **DUNG**, khong
phai mot thuong nguon thieu:

  * GD1 giu nguyen hinh va xuat MP4 **full do dai**; viec cat la cua GD2, tren
    **ban ra**, voi MOT dong ho duy nhat;
  * nem o day lam chet **MOI** luot chay (B1 §4a buoc 1, §7 dong "Bo `edit_plan`
    lam `content_process` nem").

⇒ `_doc_ban_bien_tap` tra `(None, None)` = **giu tat ca**, va ⛔ khong loc ban
  chep loi. Cai gia: ta tra tien tieng cho phan GD2 se bo — tran cat la 5 % nen
  phan mat <= 5 % chi phi tieng, va do la cai gia DUNG cua kien truc hai giai
  doan (B1 §9a).

## Day la giai doan DAU TIEN tieu tien that

Nen ba thu chuyen tu ly thuyet sang thuc te o day:

  * `ctx.provider_dispatched()` duoc goi **ngay truoc** khi goi ra ngoai, va no
    ghi xuong CSDL. Mot lan sap sau do doc ra duoc la "co the da goi", chu khong
    phai "chua goi" (I5).
  * `AiMoHo` KHONG BAO GIO duoc thu lai tu dong — provider co the da nhan va da
    tinh tien.
  * `su_dung.cua_chan_truoc_khi_tieu` chay truoc **moi lo**, khong phai mot lan
    o dau.

## Diem chot theo TUNG DOAN, khong phai theo giai doan

Mot lan chay lai sau khi lo thu bay hong khong duoc viet lai sau lo dau. Diem
chot ghi kem **van tay**, nen doi giong hay doi ban bien tap thi nhung doan cu
khong con duoc tinh la "da lam roi" — chung la cau tra loi cho mot cau hoi khac.
"""
from __future__ import annotations

import io
import json
import logging

from platform_core.i18n import _ as _t
from platform_core.storage import Storage

from . import (ai, assets, ban_bien_tap, ban_ghi, dich_thuat, ho_so_dich,
               lat_cat, long_tieng, ngon_ngu, pipeline, rang_giong, su_dung)
from .giai_doan_media import ThieuNguon

log = logging.getLogger(__name__)

#: Lý do đưa vào `y_canh` khi một đoạn dịch còn chữ Hán (B9-3, 28/09).
#:
#: ⛔ **Nêu ĐÍCH DANH cụm còn sót, ⛔ không nói chung chung.** Đo trên T1a: hai
#:    cụm sót đều là **từ lóng game** (`吃鸡`, `狙击`) — model dịch trọn câu rồi
#:    để nguyên đúng hai từ ấy. Một lời nhắc *"đừng để sót chữ Hán"* ⛔ không nói
#:    được nó đã sót ở đâu; một lời nhắc mang chính cụm đó thì có.
#:
#: ⛔ Và ⛔ KHÔNG kèm ví dụ dịch sẵn: *"một ví dụ trong lời nhắc là một mệnh lệnh
#:    ngầm"* — bốn ví dụ không dấu từng làm tụt một tên vốn đúng (24/09).
LY_DO_HAN_LOT = (
    "Ban dich con SOT chu Han chua dich: {cum}. Hay dich NOT phan do sang "
    "tieng Viet. Neu do la tu long hay thuat ngu, dung cach nguoi Viet thuc su "
    "noi ve no. Ban ra ⛔ KHONG duoc con mot ky tu Han nao.")


class ThieuBanGhi(ThieuNguon):
    """Giai doan chep loi chua sinh ra ban ghi."""


#: ⭐ Van tay cua "KHONG co ban bien tap" — mot gia tri TUONG MINH, ⛔ khong phai
#: chuoi rong tinh co.
#:
#: 🔴 `long_tieng.van_tay_long_tieng` tron `van_tay_ban` vao van tay cua ca giai
#:    doan. Neu "khong co ban" va "co mot ban rong" cung cho ra `""` thi hai
#:    trang thai khac nhau gop thanh MOT gia tri, va bo dem ⛔ khong phan biet
#:    duoc chung nua. Mot ten rieng giu kha nang phan biet do.
VAN_TAY_KHONG_CO_BAN = "khong-co-ban-bien-tap"


def _doc_ban_ghi(db, kho: Storage, run) -> tuple[dict, str]:
    """Ban ghi CHINH TAC cua run + checksum cua no. Chi doc, khong bao gio ghi."""
    from . import features

    truoc = features.giai_doan_theo_ten(db, run.id, pipeline.TRANSCRIBE)
    khoa = next((k for k in ((truoc.outputs or {}).get("khoa_asset") or [])
                 if k.endswith(".json")), "") if truoc else ""
    if not khoa:
        raise ThieuBanGhi(_t('Chưa có bản ghi để dịch.'))

    with kho.open(khoa) as f:
        goi = f.read()
    tai_lieu = json.loads(goi.decode("utf-8"))
    # Kiem lai sau khi doc tu kho: mot artifact hop le luc ghi van co the bi sua
    # sau do, va I8 noi DONE phai keo theo mot ket qua **con dung**.
    ban_ghi.kiem(tai_lieu)
    return tai_lieu, assets.bam(goi)


def _edit_plan_chay_sau_buoc_nay() -> bool:
    """`edit_plan` dung SAU `content_process` trong `pipeline.CHUOI` hay khong.

    🔑 Doc thu tu tu **so dang ky dung chung**, ⛔ khong go tay mot cau tra loi.
       Tu 26/09 cau tra loi la `True` (§9a), nhung viec phan quyet no o day —
       thay vi viet cung — lam hai dieu:

       1. mot ban bien tap do GD2 sinh ra ⛔ khong bao gio bi doc thanh phan
          quyet cua GD1. Mot luot **VONG SUA** cua `content_process` chay sau khi
          `edit_plan` da ghi artifact se THAY artifact do; loc theo no o day cho
          ra mot ban long tieng NGAN hon ban da render — hong ma ⛔ khong loi nao
          bao;
       2. neu chuoi doi lai (⛔ khong ai du dinh), duong loc song lai ngay, va
          ⛔ khong co cho thu hai nao khai thu tu.
    """
    ten = pipeline.TEN_GIAI_DOAN
    return ten.index(pipeline.EDIT_PLAN) > ten.index(pipeline.CONTENT_PROCESS)


def _doc_ban_bien_tap(db, kho: Storage, run) -> tuple[object, object]:
    """`BanBienTap` + `ChiMucCanh` cua run, hoac `(None, None)` = **GIU TAT CA**.

    ⭐ 26/09/2026: `edit_plan` da xuong GD2 (chay SAU `render`), nen tu day
       ⛔ KHONG bao gio co ban bien tap — va do la trang thai **DUNG**, khong
       phai loi. GD1 giu nguyen hinh va xuat MP4 full do dai; viec cat la cua
       GD2, tren ban ra, voi MOT dong ho duy nhat. ⛔ Nem o day lam chet MOI
       luot chay (B1 §4a buoc 1).
    """
    from . import canh as canh_mod, features

    if _edit_plan_chay_sau_buoc_nay():
        return None, None

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.EDIT_PLAN)
    khoa = next((k for k in (((gd.outputs or {}) if gd else {})
                             .get("khoa_asset") or []) if k.endswith(".json")), "")
    if not khoa:
        return None, None
    with kho.open(khoa) as f:
        goi = json.loads(f.read().decode("utf-8"))

    return (ban_bien_tap.BanBienTap.tu_dict(goi.get("ban") or {}),
            canh_mod.tu_dict(goi.get("chi_muc") or {}))


def _giong_da_chot(db, run, *, ban_ghi: dict, ctx=None) -> tuple[str, dict, str]:
    """Chot VoiceBinding va DONG BANG no vao ban long tieng.

    🔑 Pha 09 cho phep `AUTO_MATCH` **hoan lai** khi chua co ho so noi dung. Den
       day thi khong hoan duoc nua: loi thoai duoc viet CHO mot giong cu the —
       xung ho, giong dieu, do trang trong deu bam vao no — nen viet truoc roi
       chon giong sau la viet mu.

    ⇒ Nen day chinh la cho **dung** ho so, ngay truoc khi no het duoc hoan:
      `ho_so_noi_dung.bao_dam` doc bang chung lan chay DA tra tien (F0 cua stem
      `vocals` do o `audio_prepare`, ban chep loi cua `transcribe`) va ghi
      `dac_diem_giong` xuong `run.settings`. Ca hai nguon nam TRUOC `edit_plan`,
      nen duong nay chay y het nhau o hai preset — ke ca preset giu hinh, cai
      **khong** chay mot lan `edit_plan` nao co nghia.

    ⛔ Nen `ma_giong()` **nem** khi chua chot, thay vi rot ve giong mac dinh. Mot
       giong mac dinh o day khong hong ra loi nao: no cho ra mot ban long tieng
       nghe duoc, chi la khong phai giong khach dat. Cai doi tu 23/09 la CAU
       LOI: `vi_sao_chua_rang` noi thieu gi, thay vi mot cau chung chung ve mot
       "ho so noi dung" ma khach khong biet la thu gi.
    """
    # `tu_thiet_lap` van nhan mot dict — `rang_giong` KHONG duoc import
    # `cai_dat` (vong tron: `cai_dat` doc `CHE_DO_GIONG_MAC_DINH` cua no).
    # Nen ta chuan hoa TRUOC roi dua vao.
    from . import cai_dat as cd, ho_so_noi_dung

    yc = rang_giong.tu_thiet_lap(cd.chuan_hoa(run.settings))
    if rang_giong.can_cho_ho_so(yc):
        ho_so = ho_so_noi_dung.bao_dam(db, run, ban_ghi=ban_ghi, ctx=ctx)
        log.info("run %s: ho so noi dung %s", run.id, ho_so_noi_dung.mo_ta(ho_so))
        # Doc LAI tu thiet lap da ghi: mot duong doc duy nhat cho ca hai luot
        # (luot dau vua sinh ho so, luot chay lai doc ho so cu) — hai duong doc
        # la hai co hoi chon ra hai giong khac nhau cho cung mot lan chay.
        yc = rang_giong.tu_thiet_lap(cd.chuan_hoa(run.settings))

    kq = rang_giong.rang_noi_long(db, owner_id=run.owner_id, yeu_cau=yc)
    if not kq.da_chot:
        # ⭐ Cau + MA. Khong co ma thi cau nay dung lai o cot `error` — mot cot
        #    ma man hinh cua khach co y khong doc (`quan_sat.LOI_CO_MA`), vi chu
        #    tu do cua van hanh co the mang duong dan hay ten model.
        raise rang_giong.ChuaRangError(rang_giong.vi_sao_chua_rang(kq),
                                       ma_loi=rang_giong.ma_chua_rang(kq))
    # 🔴 **`nguon` tra ve RIENG, khong nhet vao `can_cu`.** No la mot TRUONG cua
    #    `KetQua`, con `tom_tat` cua giai doan nay lai doc `can_cu["nguon"]` —
    #    nen truoc 23/09 `nguon_giong` cua MOI lan chay deu la chuoi rong. Mot
    #    cot bao cao luon rong khong keu len bao gio; no chi tra loi sai cau hoi
    #    "vi sao giong nay".
    #
    # ⛔ Va khong nhet vao `can_cu` vi `can_cu` di THANG vao loi nhac (`dac_diem`
    #    duoi kia roi ve `can_cu` khi khong co khoa `dac_diem`). Them mot khoa o
    #    day la doi loi nhac cua duong `USER_SELECTED` da nghiem thu.
    return kq.ma_giong(), dict(kq.can_cu or {}), kq.nguon


def chay(db, kho: Storage, *, run, ctx=None) -> dict:
    """Loc theo ban bien tap -> chot giong -> viet loi theo lo -> rap -> kiem."""
    goc, checksum = _doc_ban_ghi(db, kho, run)
    ban, chi_muc = _doc_ban_bien_tap(db, kho, run)

    # ⛔ Ban ghi nguon khong bi cham. `doan_giu_lai` tra ve mot BAN SAO da loc.
    #
    # ⭐ `(None, None)` = **GIU TAT CA** (26/09, `edit_plan` xuong GD2): ⛔ khong
    #    loc ban chep loi, va ⛔ khong goi `doan_giu_lai` — mot "ban giu het" gia
    #    de cho qua ham loc la mot nguoi noi thu hai ve cung mot dieu.
    if ban is None or chi_muc is None:
        giu, van_tay_ban = dict(goc), VAN_TAY_KHONG_CO_BAN
    else:
        giu, van_tay_ban = ban_bien_tap.doan_giu_lai(goc, ban, chi_muc), ban.van_tay()
    doan_giu = list(giu.get("doan") or [])
    if not doan_giu:
        # ⭐ Hai nguyen nhan KHAC nhau, nen hai cau KHAC nhau — nhung ca hai
        #    msgid deu DA CO trong catalog, ⛔ khong them msgid moi cho mot ca
        #    chi doi nguyen nhan.
        raise long_tieng.LongTiengError(
            _t('Bản biên tập không giữ lại đoạn thoại nào.') if ban is not None
            else _t('Không có đoạn nào được giữ lại để lồng tiếng.'))

    ma_giong, can_cu, nguon_giong = _giong_da_chot(db, run, ban_ghi=goc, ctx=ctx)
    from . import cai_dat as cd
    dich = cd.doc(run).ngon_ngu_dich
    provider = ai.THU_TU_PROVIDER[0]
    model = ai.model_cho(ai.CHUYEN_LOI_THOAI, provider=provider)

    # 🔑 Task 11 — MOT lan cho CA video, truoc khi buoc vao vong lo dich tung
    #    lo. `dich_mot_lo`/`long_tieng` la VO TRANG THAI (moi lo chi thay
    #    `{ma: chu}` cua chinh no) nen quan he nhan vat phai duoc quyet MOT
    #    LAN o day, ⛔ khong phai moi lo mot lan.
    #
    # ⭐ Ho so DA duoc noi vao loi nhac: `ho_so=ho_so` di vao `long_tieng.loi_nhac`
    #    o vong lo duoi, va `loi_nhac` THAT SU dung `bang_dai_tu` /
    #    `bang_ten_rieng` cua no (`test_408::test_loi_nhac_mang_BANG_DAI_TU...`).
    #    Ngoai ra ho so con vao `tom_tat["ho_so_dich"]` de co bang chung no da
    #    chay. (Chu thich truoc day khai *"CHUA duoc noi vao loi nhac"* — cau ay
    #    dung cho buoc dau cua Task 11 va ⛔ da sai tu khi Task 7b noi xong.)
    #
    # ⚠️ `dung()` nem khi CUA CHAN ngan sach (`features.AsvError`) va tra ho so
    #    RONG khi model tra rac — hai ca khac loai, xem docstring cua no.
    ho_so = ho_so_dich.dung(db, run, goc, ctx=ctx)
    # 🔴 **`commit` NGAY sau loi goi tra tien dau tien cua giai doan nay.**
    #
    #    `ai.goi_tinh_tien` ghi so cai trong giao dich CUA NGUOI GOI
    #    (`su_dung.ghi` chi `db.add` + `db.flush`), va `db.commit()` dau tien cua
    #    ham nay nam o CUOI lo thu nhat, cach day bay buoc. Bat cu thu nao nem
    #    trong khoang do di qua `thi_hanh` -> `db.rollback()` va **dong so cai
    #    cua loi goi DA TRA TIEN nay bien mat**: tien mat, so trong. Cung lap
    #    luan — va cung cau chu — voi `giai_doan_giong._chot_lo`.
    #
    # ⚠️ Va khoang do ⛔ khong phai ly thuyet: `lc.kiem(vi_tri=0)` ngay duoi nem
    #    `TiepNoi` khi lat cat het cho, tuc mot duong DIEU KHIEN THUONG cua moi
    #    video dai — ⛔ khong phai mot su co.
    #
    # ⚠️ **⛔ KHONG CO PHEP KIEM DO cho dong nay, va do la mot su that ve BO
    #    TEST, ⛔ khong ve menh de.** Do 27/09: `pysqlite` phat `SAVEPOINT` o che
    #    do autocommit, nen `su_dung.ghi` (dung `begin_nested`) BEN NGAY tren
    #    SQLite va `db.rollback()` ⛔ khong xoa duoc dong so. Tren PostgreSQL —
    #    kho cua production — no la SAVEPOINT that va rollback XOA. Bang chung +
    #    duong di lai: `test_440::test_DO_KHA_NANG_BO_TEST_flush_so_cai_co_MAT_
    #    qua_rollback_khong`. Dong nay theo cung luat voi `_chot_lo` va
    #    `ho_so_noi_dung.bao_dam`, ca hai cung ⛔ khong do duoc o cuc bo.
    db.commit()

    vt = long_tieng.van_tay_long_tieng(
        checksum_ban_ghi=checksum, van_tay_ban=van_tay_ban,
        ma_giong=ma_giong, provider=provider, model=model, ngon_ngu_dich=dich)

    # ⭐ Diem chot mang van tay nay. Doi giong hay doi ban bien tap => van tay
    #    doi => khong doan nao duoc tinh la da lam roi.
    xong = su_dung.da_xong(db, run, stage=pipeline.CONTENT_PROCESS, fingerprint=vt)

    dac_diem = dict(can_cu.get("dac_diem") or {}) or can_cu
    con_lai = [d for d in doan_giu if str(d.get("ma") or "") not in xong]
    chuyen: dict[str, dict] = _lay_lai_doan_da_xong(db, run, xong)
    # ⭐ Ly do bi che cua nhung don vi VONG SUA vua mo lai. Rong o lan chay dau
    #    — tuc duong THUONG ⛔ khong bi cham (`su_dung.y_canh_dang_cho`).
    y_canh_cho_lo = su_dung.y_canh_dang_cho(db, run,
                                            stage=pipeline.CONTENT_PROCESS)

    lo_lo = long_tieng.chia_lo(con_lai)

    # 🔑 LAT CAT (`lat_cat.py`): 120 phut video ~ 150 lo x ~142 s — gap ~6 lan
    #    tran job. Truoc MOI lo hoi co con du cho cho mot lo te nhat khong; het
    #    thi nhuong, job ke tiep doc diem chot va di tiep. Lo la nguyen tu (thieu
    #    mot doan thi `doc_chuyen` nem), nen luot sau chia lai `con_lai` ra
    #    DUNG cac lo con lai cua lan chay mot mach.
    lc = lat_cat.mo(db, run, pipeline.CONTENT_PROCESS, van_tay=vt,
                    du_phong_s=(lat_cat.timeout_goi_ai(ai.CHUYEN_LOI_THOAI)
                                + lat_cat.DU_PHONG_NGOAI_GOI_S))
    # `so_lo` cua tom tat = so lo DA GUI cua ca giai doan, cong qua cac luot.
    so_lo_truoc = int(lc.trang_thai.get("so_lo") or 0) if lc.noi_tiep else 0
    # ⭐ Khoa so cai cua lo theo vi tri TRONG `doan_giu`, khong theo vi tri
    #    trong `con_lai`: luot noi tiep bat dau lai `i` tu 0, va `lo_000` thu
    #    hai se dung `UNIQUE(run_id, ma_dispatch)` — `DaGhiRoi` bi nuot va mot
    #    lan goi DA GIAO bien mat khoi so cai.
    vi_tri_cua = {str(d.get("ma") or ""): k for k, d in enumerate(doan_giu)}
    co_lo = max(1, int(long_tieng.DOAN_MOI_LO))

    # B14/V3 — bon cua PHAT HIEN muon tu D:\Viral (`dich_thuat.py`, chi doc,
    # khong sua ban dich). Ba tap nay CHI cong don nhung doan duoc DICH MOI
    # trong luot chay nay (`lo_lo`/`con_lai`) — mot doan da xong o luot TRUOC
    # (`_lay_lai_doan_da_xong`) giu nguyen outputs cu, dung tinh than "diem chot
    # theo TUNG DOAN" o dau tep: no la cau tra loi cho mot cau hoi khac.
    phinh_bia_ma: set[str] = set()
    vuot_tran_nguon_ma: set[str] = set()
    gop_cau_ma: set[str] = set()

    for i, lo in enumerate(lo_lo):
        lc.kiem(vi_tri=i, trang_thai={"so_lo": so_lo_truoc + i})
        dau = vi_tri_cua.get(str(lo[0].get("ma") or ""), 0)
        if ctx is not None and getattr(ctx, "progress", None):
            ctx.progress(5 + int(85 * dau / max(1, len(doan_giu))),
                         _t('Đang viết lời thoại'))
        # ⭐ Nhip tien do MANG BO DEM (log van hanh, 25/09) — xem giai thich o
        #    `giai_doan_giong.py`. Giai doan nay ngan hon (~5 phut do duoc,
        #    docs/NHAT_KY.md muc 8), va moi lo nhay `DOAN_MOI_LO=12` don vi
        #    mot luc nen mac dinh 30s/5 don vi da du thua — khong can chinh.
        if ctx is not None and getattr(ctx, "progress_counter", None):
            ctx.progress_counter(dau, len(doan_giu), don_vi="doan")

        ma_da_gui = {str(d.get("ma") or "") for d in lo}
        messages = long_tieng.loi_nhac(
            lo, tat_ca=doan_giu, ngon_ngu_goc=str(goc.get("ngon_ngu") or ""),
            dac_diem_giong=dac_diem, ngon_ngu_dich=dich,
            # ⭐ **LY DO bi che di vao luot dich lai.** `y_canh` loc theo dung
            #    cac ma cua LO nay, nen mot lo ⛔ khong co doan bi che se cho ra
            #    loi nhac **y het ban nen** (`long_tieng.loi_nhac` chi chen luat
            #    `y_canh` khi lo that su co doan mang no).
            y_canh={m: y for m, y in y_canh_cho_lo.items() if m in ma_da_gui},
            # 🔑 Task 7b — `chuyen` la dict DANG TICH LUY (`chuyen.update(moi)`
            #    sau moi lo o duoi), nen tai lo `i` no giu ban dich cua MOI lo
            #    truoc. `ho_so` la ket qua MOT lan goi cua Task 11 (dong 182),
            #    ⛔ khong goi lai o day.
            da_dich=chuyen, ho_so=ho_so)

        kq = ai.goi_tinh_tien(
            db, run, ai.CHUYEN_LOI_THOAI, messages,
            stage=pipeline.CONTENT_PROCESS,
            # ⭐ N-23: ep luoc do o tang GIAI MA. 2/21 lo hong -> 0/20,
            #    gia +0 luot goi (`long_tieng.luoc_do_phan_hoi`).
            luoc_do=long_tieng.luoc_do_phan_hoi(lo),
            # 🔑 Khoa cua so cai la LO (mot lan goi = mot dong so cai), con diem
            #    chot la DOAN. Hai truc khac nhau va gop chung lai se hong: mot
            #    lo chua 12 doan nhung chi mot lan tinh tien.
            item_key=f"lo_{dau // co_lo:03d}",
            ctx=ctx)

        # 🔴 **`noi_dung` la MOT CHUOI, khong phai mot dict.** `ai.goi` tra ve
        #    nguyen van phan hoi cua model (`ai.py:270`), va viec doc no thanh
        #    JSON la viec cua `ai.doc_json` — ham ton tai dung de lam dieu do va
        #    de kiem cac truong bat buoc cua tung thao tac.
        #
        #    Truoc pha 22 dong nay truyen thang chuoi vao `doc_chuyen`, va
        #    `doc_chuyen` goi `.get("doan")` tren no: **moi lan goi model that
        #    deu nem `AttributeError`**, tuc giai doan tra tien nay chua bao gio
        #    chay noi mot lan voi mot model that.
        #
        # ⭐ Vi sao khong bo test nao bat duoc: `tests/fixtures/asv_media.cua_ai_gia`
        #    thay `goi_tinh_tien` va tra ve mot **dict** o `noi_dung` — thu ma cua
        #    that khong bao gio tra ve. Mot ban gia tra ve dung thu ma ma nguon
        #    muon nhan, thay vi thu cua that tra ve, se lam ca bo test xanh
        #    quanh mot loi khong the khong xay ra.
        moi = long_tieng.doc_chuyen(
            ai.doc_ket_qua(kq, ai.CHUYEN_LOI_THOAI),
            ma_da_gui)
        chuyen.update(moi)

        # N6 (B14/V3) — GOP CAU: do dai bat thuong TRONG CUNG LO nay, truoc khi
        # dem theo doan. Phai tinh o CAP LO (khong phai ca video): mot cau dai
        # bat thuong trong mot lo thoai it khac han mot lo thoai nhieu — xem
        # `dich_thuat.danh_dau_gop_cau`.
        gop_cau_lo = dich_thuat.danh_dau_gop_cau(
            {ma: len(str(v.get("chu") or "")) for ma, v in moi.items()})
        if gop_cau_lo:
            log.warning("run %s lo %d: %d/%d ma nghi GOP CAU (do dai bat "
                        "thuong trong lo, chua sua)",
                        run.id, i, len(gop_cau_lo), len(moi))
            gop_cau_ma.update(gop_cau_lo)

        # Nguon (tieng goc) cua tung ma TRONG LO NAY — de N4/N5 doi chieu.
        # `lo` la danh sach doan cua chinh CON_LAI/doan_giu (co "ma","chu",
        # "bat","ket"), khong phai ban dich — xem `long_tieng.chia_lo(con_lai)`.
        nguon_theo_ma = {str(d.get("ma") or ""): d for d in lo}

        # ⛔ Ghi diem chot NGAY sau moi lo, khong doi den cuoi: mot lan sap o lo
        #    thu bay khong duoc lam mat sau lo dau.
        for ma, v in moi.items():
            # ⭐ **BAT BIEN O BIEN: ban ghi tieng Viet ⛔ khong chua chu Han.**
            #    ⛔ **DANH DAU, ⛔ KHONG HUY.** 0,3 % la hiem, nhung de khach
            #    mat CA LUOT vi mot ky tu thi te hon han mot doan bi gan co.
            #    ⇒ ghi vao `outputs` kem DOAN TRICH; ⛔ khong nem, ⛔ khong chan.
            # ⚠️ Chi cho dich `vi`: mot ban dich sang tieng Anh ⛔ cung khong nen
            #    co chu Han, nhung bat bien nay do tren du lieu `vi` va ⛔ chua
            #    do tren `en` — ⛔ dung khai rong hon thu da do.
            han = (long_tieng.chu_han_lot(v["chu"])
                   if dich == ngon_ngu.VI else [])
            if han:
                log.warning("run %s doan %s: chu Han lot ban ghi %r",
                            run.id, ma, han[:3])

            # N4 + N5 (B14/V3) — doi chieu voi NGUON cua chinh doan nay. Ca hai
            # la CUA PHAT HIEN thuan tuy: `dich_thuat.cau_dich_phinh_bia` /
            # `dich_thuat.vuot_tran_theo_nguon` chi TRA VE co/dem, khong sua gi.
            d_nguon = nguon_theo_ma.get(ma) or {}
            nguon_chu = str(d_nguon.get("chu") or "")
            try:
                giay_nguon = max(0.0, float(d_nguon.get("ket") or 0.0)
                                 - float(d_nguon.get("bat") or 0.0))
            except (TypeError, ValueError):
                giay_nguon = 0.0
            phinh_bia = dich_thuat.cau_dich_phinh_bia(nguon_chu, v["chu"])
            vuot_nguon, do_dai_dich, tran_nguon = dich_thuat.vuot_tran_theo_nguon(
                giay=giay_nguon, nguon=nguon_chu, dich_ra=v["chu"], dich=dich)
            if phinh_bia:
                log.warning("run %s doan %s: nghi PHINH/BIA so voi nguon "
                            "(chua sua)", run.id, ma)
                phinh_bia_ma.add(ma)
            if vuot_nguon:
                log.warning("run %s doan %s: vuot TRAN THEO MAT DO NGUON "
                            "(%d > %d, chua sua)", run.id, ma, do_dai_dich,
                            tran_nguon)
                vuot_tran_nguon_ma.add(ma)

            su_dung.danh_dau_xong(db, run, stage=pipeline.CONTENT_PROCESS,
                                  item_key=ma, fingerprint=vt,
                                  outputs={"chu": v["chu"],
                                           "cam_xuc": v["cam_xuc"],
                                           "kieu_noi": v["kieu_noi"],
                                           # ⭐ DUONG B — chi THU vao so, ⛔
                                           #    khong hien cho khach, ⛔ khong
                                           #    lai vong sua, ⛔ khong chan gi.
                                           #    `long_tieng.QUY_TAC_TU_KHAI`.
                                           "khong_chac": v["khong_chac"],
                                           # ⛔ Rong = sach. Xem tren: danh
                                           #    dau, ⛔ khong huy lan chay.
                                           "han_lot": han,
                                           # B14/V3 — ba cua PHAT HIEN, xem tren.
                                           "phinh_bia": phinh_bia,
                                           "vuot_tran_nguon": vuot_nguon,
                                           "gop_cau_nghi_ngo": ma in gop_cau_lo})
        # 🔴 **`commit`, khong phai `flush`** — va no khong phai mot chi tiet ky
        #    thuat, no la dinh nghia cua "diem chot".
        #
        #    Mot `flush` chi day cau lenh xuong giao dich dang mo. Worker chet
        #    ngay sau do thi ca giao dich bi cuon lai, va "diem chot" cua ta
        #    khong ton tai. Chot ma khong ben thi khong chot gi ca.
        #
        # ⭐ Va no con sua mot loi DO DUOC: `su_dung.ghi` + `danh_dau_xong` giu
        #    khoa ghi tren phien cua handler, trong khi `ctx.progress` mo mot
        #    phien THU HAI de cap nhat bang `jobs`. Tren SQLite hai cai do gap
        #    nhau thanh `database is locked`, va lo thu hai cua giai doan nay la
        #    lan dau tien trong ca kho hai duong do chay canh nhau — pha 11 co
        #    `goi_tinh_tien` nhung chua duoc noi vao chuoi.
        db.commit()
        lc.xong_mot()

    # ── Vong SUA chu Han lot — chu du an chot 28/09 (B9-3) ──────────────────
    #
    # 🔴 Do tren T1a: **5/78 doan (6,4 %)** con chu Han sau khi dich — `吃鸡`
    #    (an ga = thang tran) va `狙击` (ban tia), hai TU LONG GAME. Khach nhin
    #    thay chung tren phu de da dot vao hinh.
    #
    # ⭐ **⛔ Khong viet duong dich lai thu hai.** Kho nay da co `y_canh`: *"LY
    #    DO bi che di vao luot dich lai"*, va `long_tieng.loi_nhac` chi chen
    #    `QUY_TAC_Y_CANH` khi lo that su mang no — nen mot lo sach cho ra loi
    #    nhac **y het ban nen**. Dung lai co san, ⛔ khong tu viet.
    #
    # ⛔ **DUNG mot vong.** Mot vong lap "tra ve cho toi khi sach" se tra tien
    #    khong tran cho mot dieu model co the ⛔ khong bao gio lam duoc. Con sot
    #    thi `tom_tat` phia duoi NOI RA, va ban giao van di tiep — chinh sach
    #    *"DANH DAU, ⛔ KHONG HUY"* o vong lo tren giu nguyen.
    if dich == ngon_ngu.VI:
        ban = {m: long_tieng.chu_han_lot(str(v.get("chu") or ""))
               for m, v in chuyen.items()}
        ban = {m: t for m, t in ban.items() if t}
        lo_ban = [d for d in doan_giu if str(d.get("ma") or "") in ban]
        if lo_ban:
            log.warning("run %s: %d/%d doan con chu Han, dich lai mot vong",
                        run.id, len(lo_ban), len(doan_giu))
            for j, lo in enumerate(long_tieng.chia_lo(lo_ban)):
                ma_lo = {str(d.get("ma") or "") for d in lo}
                try:
                    kq = ai.goi_tinh_tien(
                        db, run, ai.CHUYEN_LOI_THOAI,
                        long_tieng.loi_nhac(
                            lo, tat_ca=doan_giu,
                            ngon_ngu_goc=str(goc.get("ngon_ngu") or ""),
                            dac_diem_giong=dac_diem, ngon_ngu_dich=dich,
                            y_canh={m: LY_DO_HAN_LOT.format(
                                cum=", ".join(ban[m][:3])) for m in ma_lo},
                            da_dich=chuyen, ho_so=ho_so),
                        stage=pipeline.CONTENT_PROCESS,
                        luoc_do=long_tieng.luoc_do_phan_hoi(lo),
                        # ⭐ Khoa RIENG: mot lan goi = mot dong so cai, va vong
                        #    sua ⛔ khong duoc dung lai khoa cua vong thuong —
                        #    `UNIQUE(run_id, ma_dispatch)` se nuot no im lang.
                        item_key=f"han_{j:03d}", ctx=ctx)
                    sua = long_tieng.doc_chuyen(
                        ai.doc_ket_qua(kq, ai.CHUYEN_LOI_THOAI), ma_lo)
                except Exception as exc:  # noqa: BLE001
                    # ⛔ Mot vong SUA hong ⛔ khong duoc lam hong ban giao: ta
                    #    van co ban dich cu, chi la no con chu Han. Ghi lai roi
                    #    di tiep — `tom_tat` phia duoi van noi ra con so that.
                    log.warning("run %s: vong sua chu Han hong: %s", run.id, exc)
                    break
                # ⛔ Chi nhan ban sua NEU no THAT SU sach hon: mot model tra ve
                #    y nguyen (hoac te hon) thi giu ban cu. Thieu ve nay thi mot
                #    luot sua vo ich van ghi de, va so do "truoc/sau" mat nghia.
                for m, v in sua.items():
                    if len(long_tieng.chu_han_lot(str(v.get("chu") or ""))) \
                            < len(ban.get(m) or []):
                        chuyen[m] = v
                db.commit()

    tai_lieu = long_tieng.dung(giu, chuyen, ma_giong=ma_giong,
                               van_tay_ban=van_tay_ban,
                               provider=provider, model=model,
                               ngon_ngu_dich=dich)
    long_tieng.kiem(tai_lieu, giu)

    goi = json.dumps(tai_lieu, sort_keys=True, ensure_ascii=False).encode("utf-8")
    khoa = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                               stage=pipeline.CONTENT_PROCESS, van_tay=vt,
                               duoi="json")
    kho.put(khoa, io.BytesIO(goi), content_type="application/json")

    if ctx is not None and getattr(ctx, "progress", None):
        ctx.progress(95, _t('Đang lưu kết quả'))

    # 🔴 **Chu Han lot: con so DA DUOC DO tu lau, ⛔ nhung chet trong so.**
    #
    #    `chu_han_lot` chay tung doan o vong lo tren va ghi ket qua vao
    #    `AsvWorkItem.outputs["han_lot"]` — dung, day du, kem doan trich. Do
    #    tren T1a (28/09): **78/78** dong mang khoa, **5** dong khac rong,
    #    khop chinh xac 5 doan that su con chu Han.
    #
    #    ⛔ Nhung `tom_tat` cua giai doan ⛔ KHONG mang mot khoa nao ve chu Han.
    #    Con so nam lai trong `asv_work_item` va ⛔ khong len bao cao, ⛔ khong
    #    toi QC, ⛔ khong toi khach. Dung hinh dang *"cho noi hai module vut
    #    truong im lang"* — phep do DUNG, duong bao cao thi KHONG CO.
    #
    # ⚠️ **Va no lam mot gia dinh chinh sach het han.** Chu thich o vong lo
    #    tren chon *"DANH DAU, ⛔ KHONG HUY"* voi ly do *"0,3 % la hiem"*. T1a
    #    do **6,4 %** (5/78) tren mot video game — gap **21 lan** tien de ay.
    #    Con so len bao cao thi lan sau chinh sach duoc chon tren SO DO, ⛔
    #    khong tren mot tien de ⛔ khong ai kiem lai.
    #
    # ⭐ Dung lai tu `tai_lieu` — ban DA GIAO — chu ⛔ khong doc lai diem chot:
    #    day hoi *"thu vua giao con chu Han khong"*, va thu vua giao la
    #    `tai_lieu`.
    #
    # 🔴 **BUG DA SUA (B14/V3, 28/09) — khoa dung la `"muc"`, khong phai
    #    `"doan"`.** `long_tieng.dung()` tra ve `{"muc": ra, ...}` (xem
    #    `long_tieng.py:595`; `van_ban.py`/`long_tieng.kiem`/`tom_tat` deu doc
    #    `tai_lieu.get("muc")`) — tai lieu nay KHONG co khoa `"doan"` bao gio.
    #    Truoc ban sua nay `tai_lieu.get("doan")` luon tra `None` -> `[]`, nen
    #    `han_lot` khoi tao tu vong lap RONG mai mai (LUON `{}`), `so_doan`
    #    LUON `max(1, 0) = 1`, va ca hai khoa `so_doan_han_lot`/`ti_le_han_lot`
    #    trong `tom_tat` chet lang du danh dau per-doan (o vong lo tren) van
    #    dung — dung hinh dang "so dung nhung gan cho SAI KHOA". Khong bo test
    #    nao bat duoc vi `test_4894` chi kiem `long_tieng.chu_han_lot()` doc
    #    lap, chua tung kiem duong bao cao nay dau-cuoi (xem `test_4950`).
    muc = list(tai_lieu.get("muc") or [])
    han_lot = {str(d.get("ma") or ""): long_tieng.chu_han_lot(str(d.get("chu") or ""))
               for d in muc} if dich == ngon_ngu.VI else {}
    han_lot = {k: v for k, v in han_lot.items() if v}
    so_doan = max(1, len(muc))
    return {
        "phan": [{"staging_key": khoa, "kind": "json", "duoi": "json",
                  "van_tay": vt}],
        "tom_tat": {**long_tieng.tom_tat(tai_lieu),
                    "so_doan_goc": len(goc.get("doan") or []),
                    "so_lo": so_lo_truoc + len(lo_lo),
                    "nguon_giong": nguon_giong,
                    "ho_so_dich": ho_so,
                    # ⛔ `0` o day la *"da do, ⛔ khong co"*, ⛔ khong phai
                    #    *"⛔ khong do"* — nhanh ⛔ khong do la `ngon_ngu_dich`
                    #    khac `vi`, va khi do `ti_le_han_lot` la `None`.
                    "so_doan_han_lot": len(han_lot),
                    "ti_le_han_lot": (round(len(han_lot) / so_doan, 4)
                                      if dich == ngon_ngu.VI else None),
                    # ⭐ Ma doan, ⛔ khong phai doan trich: tom tat di vao
                    #    `asv_stage.outputs` va bi doc boi nguoi van hanh; doan
                    #    trich da nam san o tung `AsvWorkItem`.
                    "doan_han_lot": sorted(han_lot)[:20] or None,
                    # B14/V3 — ba cua PHAT HIEN muon tu Viral (xem vong lo
                    # tren + `dich_thuat.py`). Chi cong don doan DICH MOI
                    # trong luot nay — xem chu thich o `phinh_bia_ma` dau vong.
                    "so_doan_phinh_bia": len(phinh_bia_ma),
                    "doan_phinh_bia": sorted(phinh_bia_ma)[:20] or None,
                    "so_doan_vuot_tran_nguon": len(vuot_tran_nguon_ma),
                    "doan_vuot_tran_nguon": sorted(vuot_tran_nguon_ma)[:20] or None,
                    "so_doan_gop_cau_nghi_ngo": len(gop_cau_ma),
                    "doan_gop_cau_nghi_ngo": sorted(gop_cau_ma)[:20] or None},
    }


def _lay_lai_doan_da_xong(db, run, xong: set[str]) -> dict[str, dict]:
    """Doc lai ket qua cua nhung doan da xong tu diem chot.

    ⭐ Doc tu `AsvWorkItem.outputs` chu khong goi lai model: do la ca ly do ton
       tai cua diem chot. Mot lan chay lai sau khi lo thu bay hong phai tra tien
       cho **sau lo**, khong phai bay.
    """
    from . import features

    ra: dict[str, dict] = {}
    if not xong:
        return ra
    for it in features.cac_don_vi(db, run.id, pipeline.CONTENT_PROCESS):
        if it.item_key in xong and (it.outputs or {}).get("chu"):
            o = dict(it.outputs)
            ra[it.item_key] = {
                "chu": str(o.get("chu") or ""),
                "cam_xuc": o.get("cam_xuc") or long_tieng.CAM_XUC[0],
                "kieu_noi": o.get("kieu_noi") or long_tieng.KIEU_NOI[0],
                "nhan_manh": list(o.get("nhan_manh") or []),
                # ⛔ Doan da xong TRUOC khi co truong nay se khong co no —
                #    `[]` la cau tra loi dung, ⛔ khong phai mot thieu sot.
                "khong_chac": list(o.get("khong_chac") or []),
            }
    return ra
