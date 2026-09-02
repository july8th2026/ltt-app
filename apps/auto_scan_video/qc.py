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
PHIEN_BAN_QC = 1

DAT = "dat"
HONG = "hong"
KHONG_AP_DUNG = "khong_ap_dung"

# ── Nguong, tu MVP_CONTRACT §7 ────────────────────────────────────────────────
#: T2 — thoi luong ban ra so voi nguon.
LECH_THOI_LUONG_S = 0.50
#: T4 — am luong tich hop. Cung so `tach_tieng` dung de CHUAN HOA, va do la co y:
#: chuan hoa toi mot dich roi do bang mot dich khac la tu bay minh.
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


def kiem(*, tt_ra: dict, tt_nguon: dict, am_luong: dict, ke_hoach: dict,
         ban_ke_tieng: dict, ban_dung_lop: list | None = None,
         bam_ra: str = "", bam_nguon: str = "",
         che_do_thoi_gian: str = "fit_original") -> dict:
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
    d_ra = float(tt_ra.get("thoi_luong") or 0)
    d_nguon = float(tt_nguon.get("thoi_luong") or 0)
    lech = d_ra - d_nguon
    # "khong bao gio dai hon nguon" la mot chot RIENG, khong phai he qua cua
    # `abs(lech) <= 0.5`: mot ban ra dai hon 0,3 giay van vi pham loi hua §3.
    t2 = abs(lech) <= LECH_THOI_LUONG_S and lech <= 0
    muc.append(_muc("T2", DAT if t2 else HONG,
                    "thoi luong ban ra so voi nguon",
                    thoi_luong_ra=round(d_ra, 3), thoi_luong_nguon=round(d_nguon, 3),
                    lech=round(lech, 3), nguong=LECH_THOI_LUONG_S))

    # ── T3 — luong hinh giong het nguon tung bit ────────────────────────────
    if bam_ra and bam_nguon:
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

    hong = [m["ma"] for m in muc if m["trang_thai"] == HONG]
    return {
        "phien_ban": PHIEN_BAN_QC,
        "che_do_thoi_gian": che_do_thoi_gian,
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
