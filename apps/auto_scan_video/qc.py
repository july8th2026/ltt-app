"""QC — cong chat luong cuoi cung. Thi hanh `MVP_CONTRACT.md` §7, muoi hai dung sai.

## Vi sao QC la ma MOI, khong phai ma muon

RISK-00-14 ghi tu pha 00: *"Chinh sach QC khong co nguon o dau ca. Ca ba cay di
san deu sinh ra ket qua; khong cay nao GAT no."* Do la mot cau dang nho: mot bo
render khong co cong chat luong van chay duoc hang nam, vi cai thieu chi lo ra
khi ai do nhin ky mot ket qua — va khong ai nhin ky moi ket qua.

⇒ Tep nay khong boc mot engine nao. No do, roi so voi mot con so da dong bang.

## Con so o day KHONG duoc phat minh trong pha nay

Moi nguong den tu `MVP_CONTRACT.md` §7, dong bang o pha 02, va moi dong ghi ro
nguon. Doi mot nguong o day ma khong doi hop dong la lam hai tai lieu noi hai
dieu khac nhau — va tai lieu se thua, vi ma chay con tai lieu thi khong.

⚠️ **T8/T9/T10 khong ap dung cho MVP nay, va do la mot phat hien chu khong phai
   mot thieu sot.** Ba dung sai do do viec **CHEN khoang lang** (nguon:
   `Bot_PausePipeline/engine/insertion_planner.py`). Chung duoc viet o pha 02.
   Den pha 13, ADR-003 doi mo hinh thoi gian: ta **khong chen** khoang lang nao
   ca, ta **muon** khoang lang san co lam ngan sach. Nen ba dung sai do khong
   con chu the de do.

   ⛔ Cach xu ly SAI la lang le bo chung khoi bao cao: mot cong chat luong it
      muc hon ma khong noi gi trong y het mot cong day du. Chung duoc bao cao la
      `khong_ap_dung` **kem ly do**, va `test_420` chot rang chung khong bao gio
      duoc bao la `dat`.
"""
from __future__ import annotations

import json
import subprocess

from platform_core import media
from platform_core.i18n import _ as _t

from . import tach_tieng, thoi_gian

#: Doi khi doi bat ky nguong nao. Vao van tay (O13).
#:
#: ⭐ 1 → 2 o pha 18: QC tro thanh **biet che do render**. Neu khong nang so nay
#:    thi mot lan chay lai se dung lai bao cao QC cu tu cache — bao cao duoc lam
#:    boi mot bo luat khong biet preset cat ton tai.
PHIEN_BAN_QC = 2

#: T13 — do sang trung binh toi thieu cua ban ra (thang 0-255 tren kenh Y).
#:
#: 🔴 Mot tep hop le, dung thoi luong, dung am luong, va **toan mau den** van la
#:    mot lan giao hong. Truoc pha 18 khong chot nao bat duoc dieu do: T1 chi hoi
#:    "co luong hinh khong", con luong hinh toan den van la mot luong hinh.
#:
#: ⚠️ 2,0 la nguong RAT thap, co y: mot canh dem that co the trung binh duoi 10.
#:    Ta khong doan chat luong nghe thuat o day — ta chi bat truong hop **khong
#:    co gi ca**, va bat no bang mot con so khong the nham voi mot canh toi.
DO_SANG_TOI_THIEU = 2.0

#: T13 — so khung lay mau de do do sang. Trai deu tren ca ban ra.
SO_KHUNG_DO_SANG = 12

DAT = "dat"
HONG = "hong"
KHONG_AP_DUNG = "khong_ap_dung"

# ── Nguong, tu MVP_CONTRACT §7 ────────────────────────────────────────────────
#: T2 — thoi luong ban ra so voi nguon.
LECH_THOI_LUONG_S = 0.50
#: T4 — am luong tich hop. Cung so `tach_tieng` dung de CHUAN HOA, va do la co y:
#: chuan hoa toi mot dich roi do bang mot dich khac la tu bay minh.
#:
#: 🔴 **A26-04 (P3, pha 26) — va no duoc GIU nguyen mot cach co y, khong phai bo
#:    qua.** Chia se hang so voi ben SAN XUAT co nghia la T4/T5 chi hoi duoc
#:    *"co trung dich da nham khong"*. No bat duoc mot loi thi hanh va **khong
#:    the** bat duoc mot dich SAI.
#:
#: ⭐ Bang chung rang hinh dang nay co that chu khong ly thuyet: pha 24 nham dung
#:    tran (-1,5 dBTP) va giao -1,45 dBTP. Khoang lech do tim ra duoc chi vi
#:    duong DO khac duong SAN XUAT (AAC dau ra so voi PCM master) — khong phai
#:    vi phep kiem chat van cai dich.
#:
#: ⇒ Voi MVP, chia se hang so la DUNG: cau hoi dang hoi la "duong ong co lam
#:   dung thu no duoc bao khong". Mot **quy cach ban giao** la mot tai lieu
#:   khac, va no chua ton tai.
#:
#: ⛔ DIEU KIEN DE DOI: ngay co mot quy cach ban giao (mot muc am luong hua voi
#:    khach, mot chuan nen tang phat, mot yeu cau cua doi tac), T4/T5 phai doc
#:    **tai lieu do** chu khong doc `tach_tieng`. Khong duoc dan xep bang cach
#:    chep so sang day — hai ban sao cua mot dich la hai dich se lech nhau.
LUFS_DICH = tach_tieng.LUFS_DICH
LUFS_DUNG_SAI = 1.0
#: T5 — dinh that.
DINH_THAT_TOI_DA_DB = tach_tieng.DINH_THAT_DB
#: T7 — troi cua mot doan so voi vi tri DA HOACH DINH cua no.
#: ⚠️ So voi vi tri hoach dinh, KHONG so voi vi tri goc: ADR-003 lam viec doan
#:    tran qua vi tri goc thanh **thiet ke**, va T11 moi la thu do phan do.
TROI_MOI_DOAN_S = 0.30
#: T11 — troi tich luy, tinh bang so doan. `thoi_gian` cuong che no khi lap ke
#: hoach; o day ta do lai ban ra, vi mot chot chi dung khi no duoc kiem hai dau.
TRAN_TROI_SO_DOAN = thoi_gian.TRAN_TROI_SO_DOAN


class QcError(RuntimeError):
    """QC khong chay duoc. KHAC voi "QC chay xong va ket qua hong"."""


def _muc(ma: str, trang_thai: str, mo_ta: str, **so) -> dict:
    return {"ma": ma, "trang_thai": trang_thai, "mo_ta": mo_ta, **so}


def bam_luong_hinh(duong: str, *, timeout: int = 600) -> str:
    """MD5 cua RIENG luong hinh, khong ke container.

    🔑 T3 doi "luong hinh giong het nguon tung bit". Bam ca tep thi khong tra
       loi duoc: tep ra co container khac, co luong tieng khac, co moov atom o
       cho khac. Chi `-map 0:v -c copy -f md5` moi so dung thu can so.
    """
    cmd = [media.ffmpeg_bin(), "-v", "error", "-i", duong,
           "-map", "0:v:0", "-c", "copy", "-f", "md5", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise QcError(_t('Không băm được luồng hình.'))
    ra = (r.stdout or b"").decode("utf-8", "replace").strip()
    return ra.split("=", 1)[1] if "=" in ra else ra


def do_sang_trung_binh(duong: str, *, so_khung: int = 0,
                       thoi_luong: float = 0.0, timeout: int = 600) -> float:
    """Do sang trung binh cua ban ra, lay mau trai deu. -1 neu khong do duoc.

    🔑 Lay mau chu khong duyet het: mot video 2 gio co 216.000 khung, va cau hoi
       "ban ra co phai toan mau den khong" khong can 216.000 phep do. Muoi hai
       diem trai deu tra loi no, va tra loi trong mot phan giay.

    ⛔ Do tren kenh Y (do choi) chu khong tren mau: mot ban ra hong theo kieu
       "toan den" thi Y ~ 0 bat ke khong gian mau.
    """
    so_khung = so_khung or SO_KHUNG_DO_SANG
    dai = float(thoi_luong or 0.0)
    if dai <= 0 or so_khung <= 0:
        return -1.0

    tong, dem = 0.0, 0
    for i in range(so_khung):
        # Trai deu, tranh dung sat hai dau (khung dau/cuoi hay la mau den THAT).
        t = dai * (i + 0.5) / so_khung
        cmd = [media.ffmpeg_bin(), "-v", "error", "-ss", f"{t:.3f}",
               "-i", duong, "-frames:v", "1",
               "-vf", "scale=64:36,format=gray,signalstats",
               "-f", "null", "-"]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            continue
        van = (r.stderr or b"").decode("utf-8", "replace")
        for khoa in ("lavfi.signalstats.YAVG=", "YAVG:"):
            if khoa in van:
                try:
                    tong += float(van.split(khoa, 1)[1].split()[0])
                    dem += 1
                except (IndexError, ValueError):
                    pass
                break
    return round(tong / dem, 3) if dem else -1.0


def kiem(*, tt_ra: dict, tt_nguon: dict, am_luong: dict, ke_hoach: dict,
         ban_ke_tieng: dict, ban_dung_lop: list | None = None,
         bam_ra: str = "", bam_nguon: str = "",
         che_do_thoi_gian: str = "fit_original",
         che_do_render: str = "", thoi_luong_mong_doi: float = 0.0,
         do_sang: float | None = None) -> dict:
    """Do het muoi hai dung sai. Tra ve bao cao; KHONG nem khi co muc hong.

    ⭐ Khong nem la mot quyet dinh, khong phai mot thieu sot: mot bao cao QC liet
       ke **moi** muc hong co ich hon mot ngoai le noi ve muc dau tien. Nguoi
       goi (`giai_doan_qc`) doc `dat` roi quyet dinh so phan cua lan chay.
    """
    muc: list[dict] = []

    # ── T1 — tep ra hop le, mot luong hinh + mot luong tieng ────────────────
    t1 = bool(tt_ra.get("co_video")) and bool(tt_ra.get("co_tieng"))
    muc.append(_muc("T1", DAT if t1 else HONG,
                    "tep ra co du luong hinh va luong tieng",
                    co_video=bool(tt_ra.get("co_video")),
                    co_tieng=bool(tt_ra.get("co_tieng"))))

    # ── T2 — thoi luong ────────────────────────────────────────────────────
    #
    # 🔴 **So voi cai gi, moi la cau hoi that.**
    #
    #    Truoc pha 18 T2 luon so voi NGUON. Dung cho preset giu hinh, noi luong
    #    hinh duoc sao chep. Voi preset CAT thi sai han: ban ra ngan hon nguon
    #    dung bang phan da cat — va do la **muc dich cua san pham**, khong phai
    #    mot khiem khuyet. So voi nguon o do se lam T2 hong o MOI lan chay preset
    #    cat, tuc QC chan dung cai no phai cho qua.
    #
    # ⭐ `thoi_luong_mong_doi` do nguoi goi tinh tu ban do thoi gian. Khong co no
    #    thi lui ve thoi luong nguon — dung hanh vi cu, cho preset cu.
    d_ra = float(tt_ra.get("thoi_luong") or 0)
    d_nguon = float(tt_nguon.get("thoi_luong") or 0)
    mong_doi = float(thoi_luong_mong_doi or 0.0) or d_nguon
    lech = d_ra - mong_doi
    # "khong bao gio dai hon MONG DOI" la mot chot RIENG, khong phai he qua cua
    # `abs(lech) <= 0.5`: mot ban ra dai hon 0,3 giay van vi pham loi hua §3.
    t2 = abs(lech) <= LECH_THOI_LUONG_S and lech <= 0
    muc.append(_muc("T2", DAT if t2 else HONG,
                    "thoi luong ban ra so voi MONG DOI cua che do",
                    thoi_luong_ra=round(d_ra, 3), thoi_luong_nguon=round(d_nguon, 3),
                    mong_doi=round(mong_doi, 3),
                    lech=round(lech, 3), nguong=LECH_THOI_LUONG_S))

    # ── T3 — luong hinh giong het nguon tung bit ────────────────────────────
    #
    # 🔴 **Chi co nghia o preset GIU HINH.**
    #
    #    Preset cat **ma hoa lai** luong hinh (bat buoc — xem `che_do_render`:
    #    cat bang stream copy chi cat duoc tai keyframe, va GOP do duoc la 8,333
    #    giay). Nen bam KHONG BAO GIO khop, va so no o do la chot mot dieu ta vua
    #    co y khong lam.
    #
    # ⛔ Cong thoat pha 18 goi dich danh dieu nay: QC "khong duoc gia dinh bam
    #    luong hinh bang nguon o che do cat".
    #
    # ⭐ Chi phi bam **da duoc do** truoc khi giu lai: MD5 ca luong hinh cua mot
    #    tep 154 MB / 10 phut het **0,27 giay** (stream copy, khong giai ma). O
    #    tran 2 gio uoc ~3,5 giay — canh mot luot render tinh bang phut. Pha 18
    #    doi "profile roi thay bang cach re hon **neu bang chung ung ho**"; bang
    #    chung noi khong can thay, va moi cach re hon deu la bang chung YEU HON.
    from .che_do_render import CAT_MA_HOA_LAI

    if str(che_do_render) == CAT_MA_HOA_LAI:
        muc.append(_muc("T3", KHONG_AP_DUNG,
                        "che do CAT ma hoa lai luong hinh — bam khong the bang "
                        "nguon, va so no la chot mot dieu ta co y khong lam",
                        che_do_render=str(che_do_render)))
    elif bam_ra and bam_nguon:
        t3 = bam_ra == bam_nguon
        muc.append(_muc("T3", DAT if t3 else HONG,
                        "luong hinh giong het nguon tung bit",
                        bam_ra=bam_ra, bam_nguon=bam_nguon))
    else:
        muc.append(_muc("T3", KHONG_AP_DUNG,
                        "chua bam duoc luong hinh de doi chieu"))

    # ── T4/T5 — am luong tich hop va dinh that ──────────────────────────────
    lufs = float(am_luong.get("lufs", 0) or 0)
    dinh = float(am_luong.get("dinh_that", 0) or 0)
    t4 = abs(lufs - LUFS_DICH) <= LUFS_DUNG_SAI
    muc.append(_muc("T4", DAT if t4 else HONG, "am luong tich hop",
                    lufs=round(lufs, 2), dich=LUFS_DICH, dung_sai=LUFS_DUNG_SAI))
    t5 = dinh <= DINH_THAT_TOI_DA_DB
    muc.append(_muc("T5", DAT if t5 else HONG, "dinh that",
                    dinh_that=round(dinh, 2), toi_da=DINH_THAT_TOI_DA_DB))

    # ── T6 — moi doan trong ke hoach co tep tieng ───────────────────────────
    doan = list(ke_hoach.get("doan") or [])
    co_tieng = {str(d.get("ma")) for d in (ban_ke_tieng.get("doan") or [])
                if d.get("khoa")}
    # Doan bi cat o TIMING (dai_ms <= 0) khong con la doan can tieng — chinh T12
    # dem chung, va dem chung hai lan la bao cao mot loi thanh hai.
    can = [str(d["ma"]) for d in doan if int(d.get("dai_ms") or 0) > 0]
    thieu = [m for m in can if m not in co_tieng]
    muc.append(_muc("T6", DAT if not thieu else HONG,
                    "moi doan con lai deu co tep tieng",
                    so_can=len(can), so_thieu=len(thieu), thieu=thieu[:10]))

    # ── T7 — moi doan nam DUNG cho ke hoach da dinh ────────────────────────
    #
    # 🔑 "So voi vi tri DA HOACH DINH", khong phai so voi vi tri goc: ADR-003 lam
    #    viec mot doan tran qua vi tri goc thanh **thiet ke**, va T11 moi do phan
    #    do. Vay do cai gi? Do **ke hoach so voi ban dung**: COMPOSE chep
    #    `dat_tai_ms` tu ke hoach sang ban dung, nen T7 chot rang no khong lam
    #    lech mot doan nao.
    #
    # ⚠️ Ban dau cho nay doc mot khoa `bat_hoach_dinh_ms` **khong ton tai** trong
    #    ke hoach, nen phep tru luon ra 0 va T7 luon DAT. Mot chot luon xanh la
    #    mot chot khong canh gi ca — te hon khong co, vi no trong nhu co.
    kh_theo_ma = {str(d["ma"]): int(d["dat_tai_ms"]) for d in doan
                  if int(d.get("dai_ms") or 0) > 0}
    troi_max, ma_troi = 0.0, ""
    for lop in (ban_dung_lop or []):
        ma = str(lop.get("ma"))
        if ma not in kh_theo_ma:
            continue
        t = abs(int(lop.get("dat_tai_ms", 0)) - kh_theo_ma[ma]) / 1000.0
        if t > troi_max:
            troi_max, ma_troi = t, ma
    if not ban_dung_lop:
        muc.append(_muc("T7", KHONG_AP_DUNG,
                        "chua co ban dung de doi chieu vi tri tung doan"))
    else:
        muc.append(_muc("T7", DAT if troi_max <= TROI_MOI_DOAN_S else HONG,
                        "moi doan nam dung cho ke hoach da dinh",
                        troi_lon_nhat_s=round(troi_max, 3), doan=ma_troi,
                        nguong=TROI_MOI_DOAN_S))

    # ── T8/T9/T10 — KHONG AP DUNG (xem docstring dau tep) ───────────────────
    ly_do = ("MVP khong CHEN khoang lang nao — ADR-003 doi mo hinh thoi gian "
             "sang MUON khoang lang san co lam ngan sach, nen ba dung sai nay "
             "khong con chu the de do")
    for ma in ("T8", "T9", "T10"):
        muc.append(_muc(ma, KHONG_AP_DUNG, ly_do))

    # ── T11 — troi tich luy khong vuot ngan sach cua 3 doan ke tiep ─────────
    #
    # `thoi_gian` da cuong che dieu nay khi LAP ke hoach. Do lai o day vi mot
    # chot chi dung khi no duoc kiem o ca hai dau: neu mot ngay nao do phep lap
    # ke hoach sai, khong gi khac trong chuoi phat hien duoc.
    #
    # Tran cua doan `i` = tong `ngan_sach_ms` cua ba doan `i..i+2`, dung cong
    # thuc cua `lap_ke_hoach` (ADR-003 D5).
    ns = [int(d.get("ngan_sach_ms") or 0) for d in doan]
    vuot: list[str] = []
    for i, d in enumerate(doan):
        tran = sum(ns[i:i + TRAN_TROI_SO_DOAN])
        if int(d.get("troi_sau_ms") or 0) > tran:
            vuot.append(str(d.get("ma")))
    muc.append(_muc("T11", DAT if not vuot else HONG,
                    "troi tich luy trong tran ngan sach cua 3 doan ke tiep",
                    tran_so_doan=TRAN_TROI_SO_DOAN, so_doan_vuot=len(vuot),
                    doan_vuot=vuot[:10],
                    troi_toi_da_ms=int(ke_hoach.get("troi_toi_da_ms") or 0)))

    # ── T12 — moi doan bi cat deu duoc BAO CAO ─────────────────────────────
    #
    # ⭐ T12 khong phai mot nguong: mat loi thoai **luon** la mot khiem khuyet
    #    chat luong. No `dat` khi so bi cat duoc bao cao ra, va con so do di kem
    #    de nguoi doc thay — mot lan chay cat 12 doan van "dat T12" nhung khong
    #    ai doc bao cao do ma nghi la on.
    bi_cat = int(ke_hoach.get("so_doan_bi_cat") or 0)
    muc.append(_muc("T12", DAT, "so doan bi cat da duoc bao cao",
                    so_doan_bi_cat=bi_cat))

    # ── T13 — ban ra khong RONG, khong TOAN DEN ────────────────────────────
    #
    # 🔴 Mot tep hop le, dung thoi luong, dung am luong, va **toan mau den** van
    #    la mot lan giao hong — va truoc pha 18 khong chot nao bat duoc: T1 chi
    #    hoi "co luong hinh khong", ma mot luong hinh toan den van la mot luong
    #    hinh.
    #
    # ⚠️ Nguong RAT thap (2,0/255) co y: mot canh dem that co the trung binh
    #    duoi 10. Ta khong doan chat luong nghe thuat — ta bat truong hop **khong
    #    co gi ca**, bang mot con so khong the nham voi mot canh toi.
    if do_sang is None:
        muc.append(_muc("T13", KHONG_AP_DUNG,
                        "chua do duoc do sang cua ban ra"))
    elif float(do_sang) < 0:
        muc.append(_muc("T13", KHONG_AP_DUNG,
                        "khong lay duoc khung nao de do do sang"))
    else:
        t13 = float(do_sang) >= DO_SANG_TOI_THIEU
        muc.append(_muc("T13", DAT if t13 else HONG,
                        "ban ra khong rong, khong toan den",
                        do_sang=round(float(do_sang), 3),
                        toi_thieu=DO_SANG_TOI_THIEU,
                        so_khung=SO_KHUNG_DO_SANG))

    hong = [m["ma"] for m in muc if m["trang_thai"] == HONG]
    return {
        "phien_ban": PHIEN_BAN_QC,
        "che_do_thoi_gian": che_do_thoi_gian,
        # 🔑 Bao cao QC phai noi no da do theo LUAT NAO. Mot bao cao khong ghi
        #    che do la mot bao cao khong doc lai duoc: "T3 khong ap dung" co
        #    nghia hoan toan khac giua hai preset.
        "che_do_render": str(che_do_render or ""),
        "thoi_luong_mong_doi": round(float(thoi_luong_mong_doi or 0.0), 3),
        "dat": not hong,
        "so_muc_hong": len(hong),
        "muc_hong": hong,
        "muc": muc,
    }


def tom_tat(bao_cao: dict) -> dict:
    """Con so cho tien do va giao dien. Khong duong dan, khong bi mat."""
    return {
        "qc_dat": bool(bao_cao.get("dat")),
        "qc_so_muc_hong": int(bao_cao.get("so_muc_hong") or 0),
        "qc_muc_hong": list(bao_cao.get("muc_hong") or []),
        "qc_phien_ban": int(bao_cao.get("phien_ban") or 0),
    }
