"""Ban phoi am cuoi: nen (da bo giong goc) + cac doan tieng Viet da nan.

⛔ **Khong mot loi goi model nao trong tep nay.** Pha 16 cam ro. Tat ca o day la
   so hoc va ffmpeg — tat dinh, chay lai cho ket qua giong het.

## Vi sao khong phai mot lenh ffmpeg duy nhat

Cach "sach" nhat la mot `filter_complex` voi N+1 dau vao: nen, cong tung doan
tieng, moi doan mot `adelay`. Voi mot phim co 400 doan thoai thi:

  * dong lenh dai hang chuc nghin ky tu — Windows cat o **32.767** ky tu, va no
    cat **im lang**: ffmpeg nhan mot bieu thuc loc bi cut cut, roi bao mot loi
    cu phap khong lien quan gi toi nguyen nhan;
  * do thi loc co 400 nhanh, va bo nho ffmpeg tang theo so nhanh chu khong theo
    do dai tieng.

⭐ Nen ta gom theo **lo**: moi lo `DOAN_MOI_LO` doan thanh mot ban tieng dai bang
   ca bai, roi tron cac ban lo lai. Cung mot ket qua, so nhanh moi lan chay bi
   chan, va do dai dong lenh khong con phu thuoc do dai phim.

## Vi sao `amix` chu khong phai `overlay`/`concat`

Cac doan tieng **khong** noi duoi nhau: chung nam o nhung moc rieng, co the co
khoang lang giua, va (trong tran cho phep) co the cham nhau. `concat` gia dinh
noi duoi nhau; `amix` cong tin hieu tai moi thoi diem — dung mo hinh cua bai
toan.

⛔ `amix` mac dinh **chia trung binh** theo so dau vao (`normalize=1`), tuc them
   mot doan tieng lam nho ca ban nen. Luon `normalize=0` roi chuan am luong mot
   lan o cuoi.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from pathlib import Path

from platform_core import media
from platform_core.i18n import _ as _t

from .nhap_media import MediaError, _chay

log = logging.getLogger(__name__)

#: Doi khi doi cach dung ban phoi. Vao van tay.
#: ⬆️ 1 -> 2 (V6): `loudnorm` doi tu MOT luot sang HAI luot. Ban ra doi byte —
#:    khong bump thi mot ban phoi tinh o thoi mot luot duoc dung lai cho mot
#:    cau hoi nay da khac.
#: ⬆️ 2 -> 3 (asv-final, R-03): ban phoi ket thuc bang mot bo HAN DINH THAT o
#:    tran DO DUOC (`ghim_tran_phoi`) thay vi tin mot bien du doan truoc. Ban
#:    phoi doi byte ⇒ bat buoc bump.
#: ⬆️ 4 -> 5 (B2, 25/09): `van_tay_master` nhan them `lop_nen` — ho so BA LOP
#:    demucs (`tach_tieng.LOP_MAC_DINH`: giong/nhac/vfx, bat/tat + gain). Ghi
#:    THANG ho so nay vao goi hash — cung khuon voi `am_thanh` ben duoi — thay
#:    vi tin no da "di theo" qua `van_tay_nen`: mot tham so chi mot NOI GOI
#:    dung con nhung noi khac quen truyen se lam hai lan chay khac gain lop
#:    tra ve CUNG mot van tay ma khong ai phat hien (O13).
#: ⬆️ 5 -> 6 (asv-nhac V3, 25/09): `bieu_thuc_tron`/`tron_cuoi` nhan them mot
#:    NGUON am thanh THU HAI — nhac nen KHACH TU TAI LEN (`am_thanh.nhac_nen`:
#:    khoa + am_luong_nen + lap). ⛔ Day KHONG phai lop "nhac" cua `tach_tieng`
#:    (do la mot phan cua CHINH `nen`, dau vao 0, da tron xong tu truoc) — xem
#:    canh bao o dau `am_thanh.py`. Ho so `am_thanh` day du (da nhan them khoa
#:    `nhac_nen`, `am_thanh.MAC_DINH`) da tu di vao goi hash qua `_am_day_du`
#:    ben duoi, nen ban chi cung KHONG mot dong code moi o `van_tay_master` —
#:    nhung PHAI bump o day: mot json THEM MOT KHOA (`nhac_nen: None`) ngay ca
#:    o ho so mac dinh la mot HINH DANG hash khac, va bump la tai lieu tuong
#:    minh cho dieu do (cung quy uoc voi lan bump 4->5 vua roi).
#: ⬆️ 6 -> 7 (T4, 28/09): `ghim_tran_phoi` nay sua CA DO TO, ⛔ khong chi dinh —
#:    `loc_han_dinh` co them mot khau `aformat` + `volume` truoc bo han, va mot ban
#:    phoi lech do to nay ra byte KHAC. Thieu buoc tang nay thi mot ban phoi CHUA
#:    duoc sua do to duoc dung lai tu cache va T4 do lai lech y nguyen.
PHIEN_BAN_MASTER = 7

#: So doan tieng moi lo. Xem ghi chu dau tep ve vi sao khong lam mot lan.
#:
#: ⚠️ 24 la con so an toan cho dong lenh, CHUA DO ve toc do. Moi doan them vao
#:    mot lo lam do thi loc rong ra mot nhanh; moi lo them vao lam them mot lan
#:    giai ma/ma hoa. Diem toi uu nam o dau thi phai do, va pha 21 do.
DOAN_MOI_LO = 24

#: Dang cua ban phoi. Trung voi `tach_tieng` de khong phai doi tan so o giua.
TAN_SO = 44100
SO_KENH = 2

#: Am luong dich cua ban ra. Muon tu `tach_tieng` — mot con so, mot cho khai.
def lufs_dich() -> float:
    from .tach_tieng import LUFS_DICH

    return float(LUFS_DICH)


def dinh_that_db() -> float:
    from .tach_tieng import DINH_THAT_DB

    return float(DINH_THAT_DB)


#: Bien du cho BO MA HOA CO MAT MAT, tinh bang dB.
#:
#: 🔴 **Do duoc o pha 22, va no la mot chot chan that.** Ban phoi duoc gioi han
#:    dung bang tran QC (-1,5 dBTP), roi `RENDER` ma hoa no sang AAC — va AAC
#:    **luon** vuot len mot chut vi dinh giua-mau (inter-sample peak). Do that
#:    tren mot lan chay day du: ban phoi -1,49 dBTP, tep giao cho khach
#:    **-1,45 dBTP**, tuc QC T5 hong vi 0,05 dB tren mot ban phoi khong he sai.
#:
#: ⭐ Sai lam o day khong phai con so, ma la **do luong o hai cho khac nhau**:
#:    gioi han dat tren PCM, con phep kiem do tren AAC. Mot chuoi giao hang co
#:    mat mat phai chua bien du cho buoc mat mat do — day la thuc hanh chuan cua
#:    nganh, khong phai mot cai va cho lan chay nay.
#:
#: ⛔ Va cach sua SAI la noi tran cua QC ra: khi do phep kiem thoi noi ve thu
#:    khach that su nhan duoc.
#:
#: 🔴 **1,0 tung DU, va no du vi no duoc do tren MOT preset (A29-07).**
#:
#:    Con so 1,0 den tu "mot lan chay day du" o pha 22 — nhung lan chay do co
#:    `so_cat: 0`: preset cat chua noi duoc VLM nen no chay ra mot ban giong het
#:    preset giu hinh. Tuc bien du duoc do tren mot hinh dang tin hieu, roi ap
#:    cho ca hai.
#:
#:    Do duoc o luot chay THAT dau tien (pha 29, ca hai cua deu that), cung mot
#:    ban phoi -2,49 dBTP cho ca hai preset:
#:
#:        giu hinh   -2,49 -> ban giao -2,30   vot lo **0,19 dB**
#:        cat        -2,49 -> ban giao -0,78   vot lo **1,71 dB**   <- vuot bien du
#:
#: 🔴 **Va lan chay xac nhan da BAC mot nua loi giai thich dau tien cua toi.**
#:
#:    Toi doan preset cat vot lo manh hon vi tin hieu DAC hon (da bo doan im
#:    lang). Do lai sau khi ha tran phoi xuong -3,5:
#:
#:        giu hinh   -3,42 -> -3,27   vot lo 0,15 dB
#:        cat        -3,48 -> -3,28   vot lo **0,20 dB**   (truoc: 1,71)
#:
#:    Cung mot duong ma, cung mot preset, vot lo tut tu 1,71 xuong 0,20. Nen no
#:    khong phai thuoc tinh cua tin hieu — no phu thuoc **limiter dang phai ep
#:    manh toi dau**. O -2,5 limiter kep nhieu mau vao tran, va moi mau bi kep
#:    la mot cho dinh giua-mau co the vuot len; o -3,5 no gan nhu khong ep.
#:
#: ⛔ Ghi ro dieu nay vi mot ly do cu the: neu ai do doc du bao cu cua toi ("con
#:    0,29 dB du"), ho se ket luan bien du dang qua chat va co the ha no xuong.
#:    So that la con **~1,8 dB** du. Ha bien du xuong lai lam limiter ep manh
#:    hon, tuc lam vot lo TANG tro lai — mot vong phan hoi de doc nham.
#:
#: ⚠️ Va van la mot con so do tu MOT ban nguon. No can do lai tren vai nguon
#:    khac nhau truoc khi ai do tin no la du.
#:
#: ⛔ Va no KHONG lam ban giao nho di ve cam giac: LUFS tich hop van la -14, chi
#:    co bien dinh la ha xuong. Am luong nghe duoc khong doi.
#:
#: ══════════════════════════════════════════════════════════════════════════
#: 🔴 **06/09: nguon thu HAI da do, va 2,0 KHONG DU. Vot lo phu thuoc NOI DUNG.**
#:
#:    Cau canh bao ngay tren ("van la mot con so do tu MOT ban nguon") da den
#:    han. Bon phep do, cung tran phoi -3,5, cung duong ma:
#:
#:        noi dung              phoi     giao    vot lo   T5
#:        ─────────────────────────────────────────────────────
#:        model GIA, giu hinh   -3,45   -3,27     0,18    dat
#:        model GIA, cat        -3,45   -3,32     0,13    dat
#:        model THAT, giu hinh  -3,43   -2,10     1,33    dat
#:        model THAT, cat       -3,46   -0,68     2,78    HONG
#:
#: ⭐ **Cung mot muc phoi, vot lo tu 0,13 den 2,78 dB.** Nen bien du can bao
#:    nhieu **khong phai mot thuoc tinh cua duong ong** — no la mot thuoc tinh
#:    cua TIN HIEU di qua duong ong. Model that sinh ban dich khac, ban dich
#:    khac sinh tieng doc khac, va tieng doc khac vot lo khac.
#:
#: ⛔ **Va no BAC loi giai thich ngay ben tren.** Doan tren quy bien thien cho
#:    "limiter dang phai ep manh toi dau", do o -2,5 so voi -3,5. Nhung bon dong
#:    tren **cung o -3,45**, tuc limiter ep nhu nhau, ma vot lo van lech 20 lan.
#:    Loi giai thich do dung cho THI NGHIEM cua no va khong dung cho truong hop
#:    chung.
#:
#: ⚠️ **Bo ma hoa da duoc DOI CHUNG va no vo can.** Lay chinh ban phoi that roi
#:    ma hoa bang dung tham so san pham (`aac 192k`, 44,1->48 kHz): vot lo
#:    **0,10 va 0,17 dB**. Chay lai khong doi tan so: y het. Nen khong phai AAC,
#:    khong phai phep lay mau lai, va khong phai `render` doc nham dau vao
#:    (input 1 dung la ban phoi — loi pha 22 khong tai phat).
#:
#: ══════════════════════════════════════════════════════════════════════════
#: 🔴 **23/09 (asv-final R-03): con so nay thoi lam TRAN, no chi con lam DIEM
#:    XUAT PHAT.** Vi dung cau hoi ma bon dong tren dat ra — *"can bao nhieu"* —
#:    khong co cau tra loi bang mot hang so.
#:
#:    Bang chung cuoi cung: luot nghiem thu phim khach that (NEN_V3, 23/09) voi
#:    BIEN = 2,0 van HONG T5 — ban giao **-0,33 dBTP** o preset cat va -1,69 o
#:    preset giu hinh. Va bon phim that do lai qua CHINH duong san pham
#:    (`docs/auto_scan_video_final/L_FIX_QC_AM.md` §2, 16 to hop) cho vot lo tu
#:    **0,00 den 0,85 dB** — cung khoang bien thien, cung ket luan: vot lo cua
#:    bo ma hoa co mat mat la thuoc tinh cua TIN HIEU, khong phai cua duong ong.
#:
#: ⇒ Ta khong doan nua, ta **do**: `ghim_tran_phoi` ma hoa THU ban phoi bang
#:   dung tham so giao hang, do dinh that cua ban thu, roi ha tran ban phoi cho
#:   toi khi ban THU dat tran T5. Bien du o day chi de vong dau thuong trung
#:   ngay — sai thi vong hai sua, va so do duoc GHI vao tom tat giai doan.
#:
#: ⚠️ Van con la mot con so co ich: dat qua thap thi ban phoi bi han nhieu hon
#:    can (LUFS tut, T4 hep dan); dat qua cao thi hau het lan chay ton them mot
#:    vong ghim. 2,0 la muc da do tren bon phim that: khong lan nao can vong hai.
#:
#: 🔴 **2,0 -> 0,5 (27/09). Chinh canh bao "LUFS tut, T4 hep dan" o dong tren da
#:    thanh su that tren mot lan chay THAT.**
#:
#:    Lan chay `asvr_3059dc3d77f0456bb3a3ab3705b6fae` (27/09, phim khach that,
#:    preset cat + `toc_do = 1,25`) lam **T4 HONG**: ban phoi ra `-15,24 LUFS`
#:    (`loudnorm`) / `-15,0` (doi chung bang `ebur128`), trong khi dich la
#:    `-14,0 ± 1,0`, tuc ngoai khoang cho phep.
#:
#: ⭐ **Do tren CHINH ba luot cua san pham, voi du lieu THAT cua lan chay do**
#:    (nen + hai lop tieng tai tu kho, `am_master.tron_lo` + `tron_cuoi`):
#:
#:      BIEN   tran phoi   LUFS ra   dinh giao   so vong ghim
#:       2,0      -3,5      -15,0      -3,35          1        <- HONG T4
#:       1,0      -2,5      -14,8      -2,38          1
#:       0,5      -2,0      -14,6      -1,92          1
#:      0,25     -1,75      -14,5      -1,64          1        <- CHON
#:       0,0      -1,5      -14,5      -1,78          2
#:
#:    ⇒ Tran DANG rang buoc: no lam `loudnorm ... linear=true` mat tinh tuyen
#:      tinh (tai lieu: gain tuyen tinh nao lam vuot `TP` thi no LUI ve che do
#:      dong, va che do dong sai ~1 LU).
#:
#: 🔴 **0,5 -> 0,25 (lan chay thu HAI, 27/09).** BIEN = 0,5 da len production va
#:    do duoc tren `asvr_f997f794`: T4 di tu `-15,46` len `-15,09` — cai thien
#:    **0,37 LU**, dung nhu bang tren du doan — nhung **VAN HONG**, vi khoang cho
#:    phep dung o `-15,0`. Thieu **0,09 LU**.
#:
#:    Cho thieu ay CO TEN, va no ⛔ khong nam o hang so nay: bang tren do LUFS cua
#:    **ban phoi PCM**, con T4 do **ban giao**. Hai tin hieu cach nhau mot
#:    `atempo=toc` + mot lan ma hoa AAC. Do 27/09 bang chinh `do_ban_giao`:
#:        ban phoi (PCM)   -14,86 LUFS
#:        ban giao (khach) -15,09 LUFS      => `atempo` + AAC an **0,21..0,23 LU**
#:
#: ⭐ Nen chon `0,25`: ban phoi `-14,5`, tru `0,21` cua `atempo` ⇒ ban giao
#:    **~-14,7**, nam trong khoang voi du **~0,3 LU** — va dinh giao `-1,64` van
#:    du duoi tran T5 (`-1,5`), van **1 vong ghim**.
#:
#: ⚠️ Day ⛔ **khong** phai ban sua ben vung. Ben vung la mot vong do-va-sua cho
#:    DO TO, doi xung voi `ghim_tran_phoi` cua DINH: `do_ban_giao` nay DA tra
#:    `lufs` cua ban giao that (sau khi vá `bien_tap` 27/09), nen con so de sua
#:    da co san — chi thieu vong ap no. ⛔ Chua lam vi hai vong ay TRANH nhau
#:    (tang gain de len -14,0 thi day dinh len, vong ghim lai ha xuong), va mot
#:    vong hoi tu chung can thiet ke chu ⛔ khong can mot hang so.
#:
#: ══════════════════════════════════════════════════════════════════════════
#: 🔴 **28/09 (T4, lan B11-A): vong do-to DA LAM — va cau "hai vong ay TRANH
#:    nhau" o ngay tren la mot TIEN DE SAI. No duoc do, va no sai gan hai bac.**
#:
#:    Cau tren suy luan: `volume=+g` thi dinh cung len `g`. Nhung `volume` nam
#:    TRUOC bo han dinh (`alimiter` o `tran`), nen bo han hung gan het phan
#:    tang. Do tren BON ban `tho` THAT (nen = tieng mot clip phim that, doan =
#:    giong Viet that o `tmp/giong_cu`), moi ban sau bay muc gain, ma hoa THU
#:    bang dung tham so giao hang roi do lai BAN GIAO:
#:
#:        gain   Δ do to ban giao (LU)      Δ dinh ban giao (dB)
#:        ────────────────────────────────────────────────────────
#:        +0,5      +0,47 .. +0,50            -0,10 .. +0,10
#:        +1,0      +0,92 .. +0,98            -0,10 .. +0,15
#:        +2,0      +1,79 .. +1,94            -0,05 .. +0,21
#:        +4,0      +3,31 .. +3,56            -0,05 .. +0,25
#:        +8,0      +5,09 .. +5,54            +0,09 .. +0,39
#:        -1,0      -1,00 .. -1,00            -0,96 .. -1,21
#:        -3,0      -2,99 .. -3,00            -2,99 .. -3,08
#:
#: ⭐ **Hai cot ay la ca thiet ke.** Can gat DO TO co he so ~0,95 len do to va
#:    ⛔ **≤ 0,05** len dinh (8 dB gain day dinh len 0,39 dB — mot phan hai muoi).
#:    Can gat DINH (`tran`) thi nguoc lai: ~1:1 len dinh. Tuc he nay **cheo troi**
#:    — hai vong gan nhu VUONG GOC, khong tranh nhau. Sua ca hai trong CUNG mot
#:    vong hoi tu duoc, va no hoi tu vi moi can gat chi thuc su keo mot dai luong.
#:
#: ⚠️ Chieu AM thi 1:1 tren CA HAI cot (bo han nha tay ra) — nen mot ban QUA TO
#:    duoc keo xuong khong bao gio lam hong T5.
#:
#: ⛔ **Va tien de "loi nam o chinh phep chuan hoa master" van CHUA duoc tai
#:    hien.** Bay ca chay qua DUNG duong san pham (`tron_lo` + `tron_cuoi`, LRA
#:    dau vao 1,6 -> 13,3, toc do 1,0 va 1,25) deu cho ban phoi **-13,84 ..
#:    -14,14 LUFS** — tuc `loudnorm` hai luot TRUNG dich tren moi ca thu duoc.
#:    Con so `-15,0` cua lan chay that ⛔ khong tai hien duoc o day, va gia thuyet
#:    con lai manh nhat la `_do_am_luong` LUI VE MOT LUOT (no chi `log.warning`,
#:    va mot luot `loudnorm` do duoc ~-15,0 o pha 10/09 — dung con so ay). ⭐ Vong
#:    do-to duoi day sua CA truong hop do ma ⛔ khong can biet nguyen nhan: no do
#:    ban giao roi bu, tu bat ky nguyen nhan nao.
#:
#: 🔑 Nen hang so nay tu nay chi con la **diem xuat phat cua CA HAI vong**, ⛔
#:    khong con la thu quyet dinh do to. Doi no chi doi so vong, ⛔ khong doi ket
#:    qua — va do la dung y nghia ta muon mot hang so hieu chinh co.
#:
#: ⛔ Va no ⛔ KHONG lam hong T5: o BIEN = 0,5 ban giao do duoc **-1,92 dBTP**,
#:    du 0,42 dB duoi tran T5 (-1,5), va `ghim_tran_phoi` chi can **1 vong** —
#:    tuc ban sua nay ⛔ khong tra them mot luot ma hoa nao.
#:
#: 🔑 **Vi sao dam ha: luoi an toan la mot PHEP DO, ⛔ khong phai mot loi khai.**
#:    Do 27/09: o tran -1,5 vong ghim do ban giao **-1,47** (vuot T5 0,03), tu ha
#:    tran xuong -1,83, do lai **-1,78** ⇒ **hoi tu va an toan**. Tuc ngay ca khi
#:    vot lo lon hon bien, vong ghim bat duoc va sua — no ma hoa THU bang dung
#:    tham so giao hang. Bien du chi con la mot phep toi uu **so vong**, ⛔ khong
#:    con la mot lan doan ve an toan.
#:
#: ⚠️ Cai gia neu sai: vot lo cua mot phim khac lon hon 0,5 dB (nghien cuu cu do
#:    `0,00-2,78 dB` o mot cho va `0,00-0,85` o cho khac) ⇒ vong ghim chay 2-3
#:    vong, tuc ton them 1-2 luot ma hoa THU (giay), ⛔ khong phai mot ban giao
#:    vuot dinh: `SO_VONG_GHIM = 3` va T5 la trong tai cuoi.
BIEN_CHO_CODEC_DB = 0.25


def dinh_that_phoi_db() -> float:
    """Tran dinh that KHOI DIEM cua ban phoi — `ghim_tran_phoi` ha tiep neu can."""
    return dinh_that_db() - BIEN_CHO_CODEC_DB


# ══════════════════════════════════════════════════════════════════════════════
#  GHIM BAN GIAO — hai can gat, MOT vong hoi tu (asv-final R-03; T4 28/09)
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔑 **Mot vong, hai can gat, va chung gan nhu VUONG GOC.** Bang do o cuoi khoi
#    `BIEN_CHO_CODEC_DB` la ly le: `tran` keo DINH ~1:1 va `gain` keo DO TO ~0,95
#    trong khi chi lam DINH nhich ≤ 0,05 dB moi dB. Nen ta ⛔ khong can hai vong
#    long nhau (se khong hoi tu) va ⛔ khong can mot hang so hieu chinh: moi vong
#    do BAN GIAO mot lan roi sua CA HAI can gat theo dung phan lech vua do.
#
# ⚠️ Bat doi xung CO Y giua hai can gat, vi hai rang buoc khong cung loai:
#      * DINH la rang buoc CUNG (T5 chan phat hanh) ⇒ `tran` chi bao gio GIAM,
#        va vong CUOI CUNG **chi duoc sua dinh** (xem `_duoc_sua_do_to`), de tep
#        cuoi con lai tren dia khong bao gio te hon tep cua mot vong truoc do.
#      * DO TO la mot KHOANG (`qc.LUFS_DUNG_SAI = 1,0`) ⇒ no co VUNG CHET, va
#        khi het cho de sua no BAO CAO chu ⛔ khong keo them.

#: So vong toi da. Moi vong = MOT lan han dinh + MOT lan ma hoa thu (vai giay).
#:
#: 🔑 **Con so nay duoc DO, ⛔ khong chon.** 32 lan chay: 8 ca tiem loi x 4 ban
#:    phoi THAT (nen = tieng mot clip phim that, doan = giong Viet that o
#:    `tmp/giong_cu`; LRA dau vao 1,6 .. 13,3). Chay voi tran vong RONG (8) de
#:    xem vong nao la vong THAT SU cuoi, ⛔ khong phai de xem no co chay het tran:
#:
#:        ca tiem                       tho LUFS/dinh      so vong (4 ban)
#:        ──────────────────────────────────────────────────────────────────
#:        lanh (khong tiem)             -13,8..-14,1 / -1,8      1 1 1 1
#:        nho 1 LU                      -14,8..-15,1 / -2,8      2 2 2 2
#:        nho 3 LU                      -16,8..-17,1 / -4,8      2 2 2 2
#:        nho 6 LU                      -19,8..-20,1 / -7,8      2 2 2 2
#:        TO 2 LU (dinh +1,25 dBFS)     -10,8..-11,1 / +1,2      3 2 3 3
#:        hinh dang T1a-bis (PLR 7,8)   -14,8..-15,1 / -7,2      2 2 2 2
#:        nho 1 LU + dinh VUOT tran     -14,8..-15,1 / -2,8      3 2 3 2
#:        nho 12 LU (vuot tran gain)    -25,8..-26,1 / -13,8     2 2 2 2  <- thoat co ghi
#:
#: ⇒ **Lon nhat DO DUOC = 3.** Lay 4 = 3 + mot vong du: mot ca 3 vong la mot ca
#:   **vua du**, va bang tren do tren BON ban phoi — ⛔ khong phai tren moi phim.
#:
#: ⭐ Ket qua cua 32 lan: T5 dat **32/32** (ke ca ca tiem dinh len +1,25 dBFS), T4
#:    dat **28/32** — bon ca hong dung la bon ca `nho 12 LU`, tuc ca CO Y vuot
#:    `GHIM_GAIN_TRAN_DB`, va ca bon thoat o `ket_do_to="kep_boi_tran_gain"` chu
#:    ⛔ khong treo va ⛔ khong am tham.
#:
#: ⚠️ Cai gia mot vong: mot `han_dinh` + mot `do_ban_giao` tren ca ban phoi. Do
#:    tren ban phoi 60 giay: **2,1 .. 6,7 giay/vong** (~0,035 .. 0,11 giay moi
#:    giay ban phoi; chenh la do lan quet chay canh cac lan khac tren may dung
#:    chung). Mot phim 90 phut ⇒ ~3 .. 10 phut mot vong THEM.
#:
#: ⛔ Va cai gia do **chi ca DO LECH phai tra**: duong lanh dung o 1 vong y nhu
#:    truoc ban nay (4/4 ban phoi), tuc ban nay ⛔ KHONG them mot luot ma hoa nao
#:    cho mot lan chay khong co gi sai.
SO_VONG_GHIM = 4

#: Do to cua ban giao duoc coi la DAT khi cach dich khong qua bay nhieu LU.
#:
#: 🔑 **Vung chet nay la thu lam vong DUNG, va no duoc DO.** `qc.LUFS_DUNG_SAI`
#:    cho phep ±1,0; neu vung chet la 0 thi moi lan chay deu ton mot vong sua cho
#:    mot phan muoi LU va chang bao gio "dat" (`loudnorm` + AAC ⛔ khong tat dinh
#:    toi muc do).
#:
#: ⭐ 0,3 la con so NHO NHAT tron con phu het dai do duoc cua duong LANH: bay lan
#:    chay that o 28/09 (LRA 1,6 -> 13,3; toc do 1,0 va 1,25) cho ban giao
#:    -14,02 .. -14,28 LUFS, tuc lech toi **0,28 LU** khi ⛔ khong co gi sai. Dat
#:    0,1 hay 0,2 la buoc CA BAY lan chay ay tra them mot luot ma hoa cho mot loi
#:    khong ton tai; dat 0,5 la bo mat mot nua bien an toan ma ⛔ khong mua gi.
#:
#: ⛔ Va no PHAI nho han `qc.LUFS_DUNG_SAI` mot khoang thay duoc: 0,3 de lai 0,7 LU
#:    cho phan `atempo` + AAC cua chinh lan render THAT (do duoc 0,18 .. 0,23 LU).
#:    `test_4896` chot bat dang thuc nay bang may.
GHIM_LUFS_VUNG_CHET_DB = 0.3

#: Tran BIEN DO cua phan bu do to, hai chieu.
#:
#: 🔑 Do duoc (bang o cuoi khoi `BIEN_CHO_CODEC_DB`): he so truyen cua can gat do
#:    to la ~0,95 toi +2 dB, 0,83..0,89 o +4 dB, roi tut con 0,64..0,69 o +8 dB —
#:    tuc tu khoang +6 dB tro len ta ⛔ khong con "sua do to" ma dang **ep bo han**,
#:    va cai gia la am thanh bi bom (pumping) chu ⛔ khong phai mot con so.
#:
#: ⛔ Nen mot ban phoi lech hon 6 dB la mot ban phoi HONG o thuong nguon (`loudnorm`
#:    lui ve mot luot, ho so nhac nen sai, ban nen im lang) — vong nay ghi lai
#:    `ket_do_to="kep_boi_tran_gain"` de nguoi doc bao cao di tim cho hong that,
#:    chu ⛔ khong che no bang 16 dB gain.
GHIM_GAIN_TRAN_DB = 6.0

#: Buoc sua do to nho hon bay nhieu thi ⛔ khong dang mot vong nua.
#:
#: 🔑 Khong trung `GHIM_LUFS_VUNG_CHET_DB`: vung chet noi ve **ket qua** (da dat
#:    dich chua), con so nay noi ve **buoc** (con cho de tien khong). Chung khac
#:    nhau o dung mot cho — khi `GHIM_GAIN_TRAN_DB` kep buoc lai: luc do ket qua
#:    con lech 3 LU ma buoc chi con 0,02 dB, va vong phai THOAT chu ⛔ khong quay
#:    them hai vong de tien 0,04 LU.
GHIM_LUFS_BUOC_TOI_THIEU_DB = 0.05

#: Lui THEM bao nhieu dB moi vong, ngoai phan vuot da do.
#:
#: 🔑 Khong phai mot bien du doan: ha tran doi tin hieu (limiter ep khac di), nen
#:    vot lo do o vong truoc khong con dung y nguyen o vong sau. 0,3 dB de vong
#:    ke tiep khong dung ngay tren bien va phai chay vong thu ba.
GHIM_LUI_THEM_DB = 0.3

#: He so lay mau cua bo han dinh. **4x la he so cua chinh phep do** — BS.1770 /
#: `loudnorm` / `ebur128 peak=true` deu uoc luong dinh giua-mau bang cach lay
#: mau len 4 lan. Han o 4x tuc han DUNG dai luong ma T5 do.
#:
#: ⚠️ Bay da ghi o pha 22 va ban nay vá no: `alimiter` mot minh han dinh MAU,
#:    khong phai dinh THAT — dinh that van troi len tren (do duoc: tran -3,48 ma
#:    dinh that len -2,68). Boc no giua hai `aresample` thi sai so tut hang bac:
#:    tren ban phoi that, dinh that roi DUNG tran (-3,50 / -4,50 / -5,99 cho
#:    tran -3,5 / -4,5 / -6,0); tren mot am don 14 kHz — truong hop xau nhat cua
#:    dinh giua-mau — sai so 0,41 dB, so voi 1,81 dB neu khong lay mau len
#:    (`test_2015`).
#:
#: 🔑 Va phan du do KHONG phai mot lo: bo han la CO CHE, con BAO DAM la vong
#:    `ghim_tran_phoi` — no do tren ban MA HOA THU, tuc do ca phan du nay.
GHIM_BOI_LAY_MAU = 4


def loc_han_dinh(tran_db: float, gain_db: float = 0.0) -> str:
    """Bo loc: bu do to `gain_db` roi han DINH THAT o `tran_db`.

    Tach rieng de kiem ma khong chay ffmpeg.

    ⛔ `level=0` bat buoc: mac dinh `alimiter` TU NANG muc ra len cham tran, tuc
       mot ban phoi yen tinh se bi keo to len — no se pha ca T4 lan y nghia cua
       `loudnorm` vua chay xong. Phan bu do to o day la mot con so DA DO, ⛔ khong
       phai mot phep tu nang.

    ⭐ **Thu tu la ca ly le cua thiet ke** (T4, 28/09): `volume` nam TRUOC bo han,
       nen bo han van la nguoi giu tran cuoi cung. Do la vi sao can gat do to chi
       lam dinh nhich ≤ 0,05 dB moi dB gain, va vi sao hai vong sua khong tranh
       nhau — bang do o cuoi khoi `BIEN_CHO_CODEC_DB`.

    ⛔ `aformat=sample_fmts=fltp` BAT BUOC va phai dung TRUOC `volume`: dau vao la
       WAV `pcm_s16le`, va `aresample` giu nguyen dinh dang mau. `volume` voi gain
       DUONG tren mau s16 **cat ngon ngay tai do**, truoc khi bo han kip lam gi —
       tuc phan bu do to se sinh meo thay vi sinh do to.

    ⚠️ `volume` duoc phat **ca khi gain = 0** (mot khau vo hai). MOT hinh dang
       chuoi cho moi duong chay: hai hinh dang la hai thu phai kiem, va la cho
       mot phep kiem xanh tren duong nay ⛔ khong noi gi ve duong kia.
    """
    lin = 10.0 ** (float(tran_db) / 20.0)
    return (f"aresample={TAN_SO * GHIM_BOI_LAY_MAU},"
            f"aformat=sample_fmts=fltp,"
            f"volume={float(gain_db):.6f}dB,"
            f"alimiter=limit={lin:.6f}:level=0:attack=5:release=50,"
            f"aresample={TAN_SO}")


def han_dinh(vao: str, ra: str, *, tran_db: float, gain_db: float = 0.0,
             hoi_huy=None, timeout: int = 1800) -> str:
    """Ghi mot ban sao cua `vao` da bu `gain_db` roi han dinh that o `tran_db`."""
    Path(ra).parent.mkdir(parents=True, exist_ok=True)
    cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(vao), "-af", loc_han_dinh(tran_db, gain_db),
           "-ac", str(SO_KENH), "-ar", str(TAN_SO), "-c:a", "pcm_s16le", str(ra)]
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MasterError(_t('Hạn đỉnh bản phối quá hạn.')) from exc
    if r.returncode != 0:
        raise MasterError(_t('Hạn đỉnh bản phối thất bại: {loi}').format(
            loi=(r.stderr or b"").decode("utf-8", "replace")[-300:]))
    return ra


def do_ban_giao(duong: str, *, bien_tap=None, hoi_huy=None,
                timeout: int = 1800) -> dict:
    """Ma hoa THU ban phoi bang DUNG tham so giao hang roi do lai am luong.

    🔑 Day la thu tra loi duoc cau hoi ma mot phep do tren ban phoi PCM khong
       tra loi duoc: *khach se nhan dinh bao nhieu*. Tham so lay tu `ban_dung`,
       cung cho `ket_xuat.dung_lenh` lay — mot nguon, khong phai mot ban chep.

    ⭐ Do tren bon phim that: ban ma hoa thu nay va luong tieng cua tep render
       THAT do ra **cung mot con so** (ca hai preset khi khong doi toc do), nen
       no la mot ban dai dien dung chu khong phai mot uoc luong.

    🔴 **`bien_tap` (27/09): chinh cau "khi khong doi toc do" o dong tren la mot
       PHAM VI, va ngoai pham vi do ham nay do SAI.**

       Duong ong ap `atempo=toc` cho ve tieng khi `toc_do != 1`
       (`che_do_render.loc_toc_do_tieng`). Ban ma hoa thu o day thi ⛔ khong ap,
       nen voi `toc_do = 1,25` no do mot tin hieu **khac** tin hieu khach nhan.

       ⚠️ **Tu B6 (27/09) phep `atempo` ay o GD2** (`loc_cat_hai_dong`, duoi
       chuoi), ⛔ khong con o `ket_xuat.dung_lenh`. Ly le tren ⛔ KHONG doi — khach
       VAN nhan tin hieu da qua `atempo`, nen ban thu VAN phai ap no. Nhung HINH
       DANG chuoi thi doi: truoc B6 la `atempo` + MOT lan AAC; nay la AAC (GD1,
       ⛔ khong atempo) roi `atempo` + AAC (GD2).

       ⛔ **Con so 0,23 LU duoi day do tren chuoi TRUOC B6** — no ⛔ chua duoc do
       lai tren chuoi hai lan AAC. Giu lai vi no van chung minh dieu can chung
       minh (*ban thu phai ap `atempo`*), nhung ⛔ dung tri no nhu do chinh xac
       cua chuoi hien tai.

       Do tren lan chay that `asvr_f997f794` (27/09):
           ban phoi (PCM)        -14,86 LUFS
           ban giao (khach nhan) -15,09 LUFS
           => `atempo` + AAC an **0,23 LU** ma ⛔ khong ai tinh.

       Va 0,23 LU ay la dung khoang cach con lai cua T4: dich `-14,0 ± 1,0` cho
       phep toi `-15,0`, ban giao ra `-15,09` — **thieu 0,09 LU**.

    ⭐ Nen ham nay nay ap CUNG phep doi toc do voi render. Mot ban dai dien phai
       di qua **moi** phep bien doi ma ban that di qua, ⛔ khong phai gan het.
    """
    import tempfile

    from . import ban_dung, tach_tieng

    with tempfile.TemporaryDirectory(prefix="asv-thu-giao-") as tam:
        thu = str(Path(tam) / f"thu.{ban_dung.CODEC_TIENG}")
        cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
               "-i", str(duong)]
        # ⭐ CUNG ham ma duong ong dung (`loc_cat_hai_dong` o GD2 tu B6), ⛔ khong
        #    go lai mot chuoi `atempo` thu hai: hai ban sao cua mot phep bien doi
        #    la thu kho nay da tra gia nhieu lan.
        from . import che_do_render as _cdr

        ve = _cdr.loc_toc_do_tieng(bien_tap, nhan_vao="0:a", nhan_ra="a_thu")
        if ve:
            cmd += ["-filter_complex", ve, "-map", "[a_thu]"]
        cmd += ["-c:a", ban_dung.CODEC_TIENG,
                "-b:a", ban_dung.BITRATE_TIENG, "-ar", str(ban_dung.TAN_SO_RA),
                "-ac", str(ban_dung.SO_KENH_RA), "-f", "adts", thu]
        try:
            r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
        except subprocess.TimeoutExpired as exc:
            raise MasterError(_t('Mã hoá thử bản giao quá hạn.')) from exc
        if r.returncode != 0:
            raise MasterError(_t('Mã hoá thử bản giao thất bại: {loi}').format(
                loi=(r.stderr or b"").decode("utf-8", "replace")[-300:]))
        return tach_tieng.do_am_luong(thu)


def _buoc_do_to(thieu: float, gain: float) -> tuple[float, str]:
    """Buoc sua do to cua MOT vong, va ten cua thu da kep no.

    `thieu` = `lufs_dich - lufs_giao` (duong = ban giao con NHO). Tach thanh ham
    thuan de con so nay kiem duoc ma ⛔ khong chay mot lan ffmpeg nao.

    ⭐ **Buoc Newton he so 1**, ⛔ khong phai mot buoc ham: ham truyen do duoc la
       0,92..1,00 trong khoang ±1 LU (bang o cuoi khoi `BIEN_CHO_CODEC_DB`), nen
       buoc day du la buoc dung. Ham hoac chia doi chi lam ton vong.

    ⚠️ He so tut con 0,83..0,89 o 4 LU va 0,64..0,69 o 8 LU, tuc mot buoc lon se
       **thieu** — do la ly do phai co vong thu hai chu ⛔ khong phai ly do de
       nhan buoc len: nhan len la doan, con vong thu hai thi DO.
    """
    if abs(thieu) <= GHIM_LUFS_VUNG_CHET_DB:
        return 0.0, "dat"
    moi = max(-GHIM_GAIN_TRAN_DB, min(GHIM_GAIN_TRAN_DB, gain + thieu))
    buoc = moi - gain
    if abs(buoc) < GHIM_LUFS_BUOC_TOI_THIEU_DB:
        return 0.0, "kep_boi_tran_gain"
    return buoc, "dang_sua"


def ghim_tran_phoi(goc: str, dich: str, *, tran_giao: float | None = None,
                   tran_bat_dau: float | None = None,
                   lufs_muc_tieu: float | None = None,
                   so_vong: int = SO_VONG_GHIM, bien_tap=None, hoi_huy=None,
                   timeout: int = 1800) -> dict:
    """Sua BAN GIAO ve dung DINH va dung DO TO. Ghi ban phoi ra `dich`.

    Moi vong: bu do to + han dinh that tren `goc` (khong phai tren ban da han
    cua vong truoc — de ket qua khong phu thuoc so vong da chay), ma hoa thu, do
    lai CA HAI dai luong, roi sua CA HAI can gat.

    ⭐ **Vi sao MOT vong sua duoc hai thu ma van hoi tu** (T4, 28/09). He nay cheo
       troi: `tran` keo dinh ~1:1 va hau nhu khong keo do to; `gain` keo do to
       ~0,95 va chi lam dinh nhich ≤ 0,05 dB moi dB. Tuc moi can gat gan nhu chi
       dieu khien mot dai luong, va mot buoc Newton dong thoi khong dao qua lai.
       Bang do: cuoi khoi `BIEN_CHO_CODEC_DB`.

    ⭐ **Bat doi xung CO Y, vi hai rang buoc khong cung loai.** DINH la rang buoc
       CUNG (T5 chan phat hanh) nen `tran` chi GIAM va **vong cuoi chi duoc sua
       dinh**; DO TO la mot KHOANG nen no co vung chet va khi het cho thi BAO CAO.

    ⛔ **Vong cuoi ⛔ khong duoc doi `gain`** — day la thu bao dam tep con lai
       tren dia khong te hon mot tep da tot. Doi `gain` o vong cuoi thi phan tang
       ay ⛔ khong bao gio duoc DO, va ta se giao mot tep chua ai kiem.

    ⛔ Khong nem khi het vong ma van vuot: QC T5 la trong tai, va mot ban phoi
       tot nhat co the kem mot dong log co ich hon la mot lan chay chet sau khi
       da ton ca gio tao tieng. Bao cao tra ve `dat` / `dat_do_to` de nguoi goi
       ghi lai.
    """
    tran_giao = dinh_that_db() if tran_giao is None else float(tran_giao)
    tran = dinh_that_phoi_db() if tran_bat_dau is None else float(tran_bat_dau)
    muc_tieu = lufs_dich() if lufs_muc_tieu is None else float(lufs_muc_tieu)
    tong_vong = max(1, int(so_vong))
    vet: list[dict] = []
    gain = 0.0
    giao = 0.0
    lufs_giao: float | None = None
    ket_do_to = "chua_do"
    for vong in range(tong_vong):
        han_dinh(goc, dich, tran_db=tran, gain_db=gain, hoi_huy=hoi_huy,
                 timeout=timeout)
        # ⭐ `do_ban_giao` do CA `dinh_that` LAN `lufs` cua ban ma hoa thu. Truoc
        #    27/09 chi `dinh_that` duoc doc; `lufs` bi VUT — mot con so da tra
        #    tien de do ma ⛔ khong ai dung, trong khi no la dung dai luong T4 do.
        do_giao = do_ban_giao(dich, bien_tap=bien_tap, hoi_huy=hoi_huy,
                              timeout=timeout)
        giao = float(do_giao["dinh_that"])
        tho = do_giao.get("lufs")
        lufs_giao = None if tho is None else float(tho)
        vet.append({"tran_phoi": round(tran, 2), "gain": round(gain, 2),
                    "dinh_giao": round(giao, 2),
                    "lufs_giao": (None if lufs_giao is None
                                  else round(lufs_giao, 2))})

        # ── Can gat DINH (rang buoc cung) ────────────────────────────────────
        dinh_dat = giao <= tran_giao

        # ── Can gat DO TO (mot khoang) ───────────────────────────────────────
        # ⛔ `lufs_giao is None` khong phai "dat": `do_am_luong` khong tra `None`
        #    o duong binh thuong, nen do la mot phep do VANG MAT — goi no la dat
        #    se bien mot lo hong do luong thanh mot dau xanh.
        if lufs_giao is None:
            buoc, ket_do_to = 0.0, "khong_do_duoc"
        else:
            buoc, ket_do_to = _buoc_do_to(muc_tieu - lufs_giao, gain)

        # ⛔ Dieu kien dung la `buoc == 0`, ⛔ KHONG `ket_do_to == "dat"`: ca
        #    `"kep_boi_tran_gain"` cung cho buoc 0, va do CUNG la mot ly do dung
        #    hop le (het cho de sua). Doc `ket_do_to` o day de quyet dinh dung hay
        #    khong se lam vong quay het tran de tien 0 dB moi vong.
        if dinh_dat and buoc == 0.0:
            break
        # ⛔ Vong cuoi: chi sua dinh. Xem docstring.
        duoc_sua_do_to = vong < tong_vong - 1
        if not dinh_dat:
            tran -= (giao - tran_giao) + GHIM_LUI_THEM_DB
        if buoc and duoc_sua_do_to:
            gain += buoc
        elif buoc:
            ket_do_to = "het_vong"
    if not (giao <= tran_giao):
        log.warning("ghim tran phoi: het %d vong ma ban giao van %.2f dBTP "
                    "(tran %.2f) — QC T5 se chan", tong_vong, giao, tran_giao)
    if ket_do_to != "dat":
        # ⚠️ Mot canh bao, ⛔ khong mot ngoai le: QC T4 la trong tai, va bao cao
        #    nay di vao tom tat giai doan nen con so ⛔ khong bien mat.
        log.warning("ghim do to: ban giao %s LUFS (dich %.2f, vung chet %.2f, "
                    "gain %.2f dB) — ket %s", lufs_giao, muc_tieu,
                    GHIM_LUFS_VUNG_CHET_DB, gain, ket_do_to)
    # 🔑 `lufs_giao` la do to ma KHACH thuc su nhan — do tren ban ma hoa thu da
    #    qua CUNG phep doi toc do voi render. T4 do dung dai luong nay, nen ghi
    #    no ra de cong ay ⛔ khong con la mot cau hoi mo cho tan luc render.
    #
    # ⛔ `tran_phoi`/`gain_do_to` lay tu `vet[-1]`, ⛔ KHONG tu bien vong: khi het
    #    vong, hai bien ay da duoc sua cho vong ke tiep **chua bao gio chay**, nen
    #    bao cao chung se ta mot tep ⛔ khong ton tai tren dia. Bao cao phai noi ve
    #    tep DA DO.
    cuoi = vet[-1] if vet else {"tran_phoi": round(tran, 2), "gain": 0.0}
    return {"tran_phoi": cuoi["tran_phoi"], "dinh_giao": round(giao, 2),
            "tran_giao": round(tran_giao, 2), "so_vong": len(vet),
            "lufs_giao": (None if lufs_giao is None else round(lufs_giao, 2)),
            "lufs_muc_tieu": round(muc_tieu, 2),
            "gain_do_to": cuoi["gain"],
            "dat_do_to": ket_do_to == "dat", "ket_do_to": ket_do_to,
            "dat": giao <= tran_giao, "vet": vet}


#: He so am luong cua NEN khi co tieng noi de len.
#:
#: 🔴 Khong phai mot lua chon tham my: neu nen giu nguyen muc thi giong Viet phai
#:    to hon nen moi nghe ro, va lam giong to hon la dua no toi tran cat ngon.
#:    Ha nen xuong la cach cac ban long tieng that lam ("ducking"), va -6 dB la
#:    muc thuong dung: nghe van con nhac, nhung loi thoai noi len tren.
#:
#: ⚠️ CHUA DO tren ban that. Chon theo huong an toan cho de nghe ro loi. Pha 21
#:    do lai bang mot phep do tach biet giong/nen.
NEN_GIAM_DB = -6.0


class MasterError(MediaError):
    """Khong dung duoc ban phoi."""


def _delay_ms(t: float) -> int:
    return max(0, int(round(float(t) * 1000.0)))


def bieu_thuc_lo(so_dau_vao: int, moc_ms: list[int], he_so: list[float]) -> str:
    """Bieu thuc `filter_complex` cho MOT lo doan tieng.

    Moi dau vao: `atempo` (neu can co gian) -> `adelay` -> gom lai bang `amix`.

    ⛔ `atempo` chi nhan he so trong `[0,5; 100]` mot lan goi. Tran co gian cua ta
       la 1,15 nen mot lan la du — nhung viec do phai duoc NOI RA, khong de nguoi
       sau nang tran roi gap mot loi ffmpeg kho hieu.
    """
    if so_dau_vao <= 0:
        raise MasterError(_t('Lô trộn không có đoạn nào.'))
    phan = []
    for i in range(so_dau_vao):
        chuoi = f"[{i}:a]"
        h = float(he_so[i]) if i < len(he_so) else 1.0
        if abs(h - 1.0) > 1e-6:
            if not (0.5 <= h <= 2.0):
                raise MasterError(
                    _t('Hệ số co giãn {h} ngoài khoảng một lần `atempo`.')
                    .format(h=round(h, 3)))
            chuoi += f"atempo={h:.6f},"
        # ⚠️ `all=1` — bai hoc thu hai mang tu trinh render cu sang. Thieu no
        #    thi `adelay` **chi tre kenh dau**, va tieng lech hai ben tai: hong
        #    theo kieu nghe thay duoc nhung rat kho goi ten.
        #
        # ⭐ `aformat` tren TUNG dau vao, TRUOC khi tron: tieng do may TTS sinh
        #    ra va nhac nen do demucs tach ra khong cung tan so/so kenh, va de
        #    `amix` tu xu ly la de no chon gium — no chon theo dau vao dau tien.
        chuoi += (f"adelay={moc_ms[i]}:all=1,"
                  f"aformat=sample_fmts=fltp:sample_rates={TAN_SO}:"
                  f"channel_layouts=stereo[v{i}];")
        phan.append(chuoi)
    nhan = "".join(f"[v{i}]" for i in range(so_dau_vao))
    # ⛔ `normalize=0`: xem ghi chu dau tep.
    phan.append(f"{nhan}amix=inputs={so_dau_vao}:normalize=0:"
                f"dropout_transition=0[ra]")
    return "".join(phan)


def tron_lo(duong_vao: list[str], moc_ms: list[int], he_so: list[float],
            dich: str, *, tong_giay: float, hoi_huy=None,
            timeout: int = 1800) -> str:
    """Tron MOT lo doan tieng thanh mot ban dai bang ca bai."""
    if len(duong_vao) != len(moc_ms):
        raise MasterError(_t('Số đoạn và số mốc không khớp.'))
    Path(dich).parent.mkdir(parents=True, exist_ok=True)

    cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error"]
    for d in duong_vao:
        cmd += ["-i", d]
    cmd += ["-filter_complex", bieu_thuc_lo(len(duong_vao), moc_ms, he_so),
            "-map", "[ra]",
            # ⭐ `-t` chan ban lo dung bang ca bai: mot doan dat gan cuoi va dai
            #    hon phan con lai se keo ban ra dai them, va cai do tich luy qua
            #    tung lo thanh mot ban phoi dai hon video.
            "-t", f"{max(0.001, float(tong_giay)):.3f}",
            "-ac", str(SO_KENH), "-ar", str(TAN_SO), "-c:a", "pcm_s16le", dich]
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MasterError(_t('Trộn lô tiếng quá hạn.')) from exc
    if r.returncode != 0:
        raise MasterError(_t('Trộn lô tiếng thất bại: {loi}').format(
            loi=(r.stderr or b"").decode("utf-8", "replace")[-300:]))
    return dich


def bieu_thuc_chuan_am(vao: str, ra: str, *, tong_giay: float = 0.0,
                       do_duoc: dict | None = None,
                       in_json: bool = False) -> str:
    """Bo loc chuan am luong cuoi cung. Tach rieng de KIEM duoc ma khong chay.

    `do_duoc` — ket qua luot DO (`print_format=json` cua `loudnorm`). Rong =
    phat ban MOT LUOT, tuc chinh luot do. Xem khoi giai thich o duoi.

    ⭐ Truoc pha 22 chuoi nay nam thang trong `tron_cuoi`, va cach duy nhat de
       kiem no la chay ca mot lan tron that. Mot tham so quan trong nhu tran dinh
       that thi phai co mot phep kiem re tien canh no.
    """
    # 🔴 **`apad` khong phai mot chi tiet — no giu loi hua cua preset giu hinh.**
    #
    #    `amix` ket thuc khi dau vao dai nhat het, va dieu do co the som hon ban
    #    nguon vai chuc mili giay. Trinh render map mot luong hinh + mot luong
    #    tieng voi `-shortest`, nen mot ban phoi NGAN HON keo theo **luong hinh
    #    bi cat**. Do that o pha 22: ban phoi 2,919 s tren mot nguon 3,000 s, va
    #    QC T3 ("luong hinh giong het nguon tung bit") hong — dung cai T3 sinh ra
    #    de bao ve.
    #
    # ⭐ Khiem khuyet nay bi CHE cho toi pha 22: truoc do trinh render doc nham
    #    ban NEN, ma ban nen thi luon dai bang ban nguon. Mot loi che mot loi.
    # ⚠️ **`asetpts` moi la thu sua duoc, khong phai `apad`.** Do tung buoc tren
    #    mot ban nguon 3,019 giay, cat bang `-t 3.000`:
    #
    #        anull                              -> 3,000
    #        loudnorm                           -> 2,919   <- mat 0,1 giay
    #        loudnorm,apad                      -> 2,919
    #        loudnorm,apad=pad_dur=0.5          -> 2,919
    #        loudnorm,asetpts=N/SR/TB,apad      -> 3,000
    #
    # 🔑 `loudnorm` **doi moc thoi gian**: ban ra bat dau tre 0,1 giay, nen `-t`
    #    cat o PTS 3,000 khi moi co 2,919 giay am thanh. `apad` khong cuu duoc vi
    #    van de khong phai thieu mau ma la moc bi day. `asetpts=N/SR/TB` dat lai
    #    moc ve 0, roi `apad` lo phan thieu neu ban tron that su ngan hon.
    dem = ",asetpts=N/SR/TB,apad" if tong_giay > 0 else ""

    # 🔴 **MOT luot `loudnorm` KHONG trung dich, va do la mot phep do chu khong
    #    phai mot y kien.**
    #
    #    Luot nghiem thu 10/09 tren PostgreSQL, cung mot ban master, hai preset:
    #
    #        giu_hinh        LUFS = -14,98   DAT   (con 0,02 dB toi bien)
    #        cat_thong_minh  LUFS = -15,02   HONG  (vuot 0,02 dB)
    #
    #    Dich la -14,0 ± 1,0. **Ca hai deu roi vao ~-15,0**, tuc lech ~1 dB va
    #    nam DUNG tren bien. Preset nay dat, preset kia hong, cach nhau 0,04 dB —
    #    do la tung dong xu, khong phai mot phep kiem.
    #
    # ⛔ Nen ban sua KHONG phai noi `LUFS_DUNG_SAI`. Noi mot dung sai de mot phep
    #    kiem xanh la bo chinh cau hoi no dang hoi, va `giu_hinh` "dat" truoc do
    #    la MAY chu khong phai dung.
    #
    # ⭐ `loudnorm` mot luot la mot bo chuan **dong**: no doan muc khi dang chay
    #    va bam theo, nen sai so ~1 dB la hanh vi da biet cua no. Hai luot —
    #    do truoc, roi ap bang `measured_*` kem `linear=true` — moi la duong
    #    trung dich.
    #
    # ⚠️ Ham nay van phat duoc ban MOT LUOT khi `do_duoc` rong: luot do chinh la
    #    luot DO. Hai luot dung chung mot chuoi loc, nen thu duoc do va thu duoc
    #    ap khong the la hai tin hieu khac nhau.
    lo = f"{vao}loudnorm=I={lufs_dich()}:TP={dinh_that_phoi_db()}:LRA=11:dual_mono=true"
    if do_duoc:
        lo += (f":measured_I={do_duoc['input_i']}"
               f":measured_TP={do_duoc['input_tp']}"
               f":measured_LRA={do_duoc['input_lra']}"
               f":measured_thresh={do_duoc['input_thresh']}"
               f":offset={do_duoc['target_offset']}:linear=true")
    # ⛔ `print_format` la THAM SO cua `loudnorm`, phai nam TRONG cum tham so
    #    cua no. Noi no sau nhan ra (`[ra]:print_format=...`) la cu phap
    #    khong hop le, va ffmpeg tu choi CA chuoi — luot do khi do lang le
    #    tra `None` va he tu lui ve mot luot. Da dinh dung the mot lan.
    if in_json:
        lo += ":print_format=json"
    return f"{lo}{dem}{ra}"


def fade_ap_dung(am: dict | None, tong_giay: float) -> tuple[float, float]:
    """`(vao, ra)` giay THAT SU ap — moi dau toi da mot phan ba ban phoi.

    ⚠️ Ho so duoc duyet o cua, khi chua biet video dai bao nhieu, nen mot fade
       5 giay co the gap mot ban 6 giay. Cat o day chu khong tu choi — va con
       so da cat duoc GHI vao tom tat giai doan (`giai_doan_thoi_gian`), khong
       lang le.
    """
    from . import am_thanh

    a = am_thanh.tu_cai_dat(am)
    tran = max(0.0, float(tong_giay)) / 3.0
    return round(min(a["fade_vao"], tran), 3), round(min(a["fade_ra"], tran), 3)


def bieu_thuc_tron(n: int, *, am: dict | None = None, tong_giay: float = 0.0,
                   nhac_nen_idx: int | None = None) -> str:
    """Chuoi loc: nen (dau vao 0) + `n-1` ban lo tieng -> nhan `[tron]`.

    Tach rieng de KIEM duoc ma khong chay ffmpeg (`test_479`).

    ⭐ Ho so MAC DINH ra **dung tung ky tu** chuoi truoc pha 23: cung `volume`,
       cung mot `amix` gom het. Doi chuoi cua duong mac dinh la doi ban ra cua
       moi lan chay khong chinh gi — viec do phai di kem `PHIEN_BAN_MASTER`.

    `nhac_nen_idx` — V3 (25/09), chi so dau vao ffmpeg (`-i`) cua nhac nen
    KHACH TU TAI LEN, hoac `None` khi khong co. ⛔ Ham nay KHONG tu suy chi so
    tu `am["nhac_nen"]`: day la BO DUNG CHUOI thuan tuy (xem docstring "Tach
    rieng" o tren), no khong biet `nen` va cac lo da chiem bao nhieu dau vao
    `-i` — chi `tron_cuoi` (noi xay CA lenh) biet, va phai TRUYEN THANG chi so
    xuong day. Ho so va chi so nay phai cung co hoac cung vang; `tron_cuoi` da
    doi chieu truoc khi goi.
    """
    from . import am_thanh

    a = am_thanh.tu_cai_dat(am)
    nhac_nen = a.get("nhac_nen")
    co_nhac = nhac_nen_idx is not None
    if co_nhac != bool(nhac_nen):
        raise MasterError(_t(
            'Hồ sơ nhạc nền và tệp nhạc nền phải cùng có hoặc cùng vắng mặt.'))

    muc = "volume=0" if a["nen_db"] is None else f"volume={a['nen_db']}dB"
    phan = [f"[0:a]{muc},"
            f"aformat=sample_fmts=fltp:sample_rates={TAN_SO}:"
            f"channel_layouts=stereo[nen];"]
    for i in range(1, n):
        phan.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates={TAN_SO}:"
                    f"channel_layouts=stereo[t{i}];")

    # V3 (25/09): nhac nen KHACH TAI LEN la MOT nguon am thanh rieng — ⛔
    # KHONG phai lop "nhac" cua `tach_tieng` (do da nam TRONG `nen`, dau vao
    # 0, tu truoc). Gap no lam MOT voi `nen` NGAY O DAY, truoc ca ducking: hai
    # thu cung la mot "nen bed" nen tu nhien duoc ha THEO LOI cung nhau khi
    # `giam_theo_loi` bat, khong can them mot nhanh rieng cho no.
    #
    # 🔴 `apad` BAT BUOC tren chinh dau vao nay (bai hoc Viral
    #    `xu_ly_video.py:1197-1212`, dan lai o dau `am_thanh.py`): nhac ngan
    #    hon video ma khach TAT lap (`tron_cuoi` khong gan `-stream_loop`) se
    #    lam dau vao nay tu ket thuc SOM. `amix` o day khong khai `duration=`
    #    (mac dinh `longest`) nen ban than no da an toan vi `nen` luon du
    #    `tong_giay` — nhung `apad` la mot lop bao hiem re, dut khoat, khong
    #    phu thuoc mot gia dinh ve `nen` co the sai trong tuong lai.
    nen_nhan = "[nen]"
    if co_nhac:
        vol = nhac_nen["am_luong_nen"]
        phan.append(f"[{nhac_nen_idx}:a]volume={vol},apad,"
                    f"aformat=sample_fmts=fltp:sample_rates={TAN_SO}:"
                    f"channel_layouts=stereo[nhacnen];")
        phan.append("[nen][nhacnen]amix=inputs=2:normalize=0:"
                    "dropout_transition=0[nenx];")
        nen_nhan = "[nenx]"

    fade_vao, fade_ra = fade_ap_dung(a, tong_giay)
    dich = "[tron0]" if (fade_vao or fade_ra) else "[tron]"
    lo = "".join(f"[t{i}]" for i in range(1, n))
    if a["giam_theo_loi"]:
        # 🔑 Khoa cua bo nen = CHINH loi thoai, da **chuan hoa** (khuech dai roi han
        #    bien): moi cau noi dua khoa len cung mot muc, nen do ha gan nhu khong
        #    phu thuoc giong to hay nho. Do o `PHA23_AUDIO_STUDIO.md` §2.
        gop = (f"{lo}amix=inputs={n - 1}:normalize=0:dropout_transition=0[giong];"
               if n > 2 else f"{lo}anull[giong];")
        phan.append(gop + "[giong]asplit=2[gk][gm];"
                    "[gk]volume=40dB,alimiter=limit=0.5:level=0[khoa];"
                    f"{nen_nhan}[khoa]sidechaincompress={am_thanh.THAM_SO_HA_THEO_LOI}[nend];"
                    f"[nend][gm]amix=inputs=2:normalize=0:dropout_transition=0{dich};")
    else:
        phan.append(f"{nen_nhan}{lo}amix=inputs={n}:normalize=0:dropout_transition=0{dich};")
    if dich != "[tron]":
        # Fade TRUOC `loudnorm`: chuan am luong do ca doan fade, nen ban ra van
        # dung -14 LUFS. Fade sau no se lam ban ra nho hon muc tieu.
        loc = []
        if fade_vao:
            loc.append(f"afade=t=in:st=0:d={fade_vao}")
        if fade_ra:
            loc.append(f"afade=t=out:st={max(0.0, tong_giay - fade_ra):.3f}:d={fade_ra}")
        phan.append(f"[tron0]{','.join(loc)}[tron];")
    return "".join(phan)


def tron_cuoi(nen: str, cac_lo: list[str], dich: str, *, tong_giay: float,
              hoi_huy=None, timeout: int = 1800, am: dict | None = None,
              ghim: dict | None = None, nhac_nen_duong: str | None = None,
              bien_tap=None) -> str:
    """Tron ban nen (da ha muc) voi cac ban lo tieng, roi chuan am luong.

    ⭐ Chuan am luong **mot lan o cuoi**, khong phai o tung lo: `loudnorm` doi
       muc cua ca dong tin hieu, nen chay no tren tung manh roi cong lai cho ra
       mot ket qua khong ai du doan duoc.

    `ghim` — dict de HUNG bao cao cua `ghim_tran_phoi` (dinh that ban giao da
    do). Dua no cho `kiem_ban_ra` de khoi ma hoa thu lan hai: hai lan chay cung
    mot lenh tren cung mot tep khong the cho hai cau tra loi, no chi ton them
    mot luot `loudnorm` 192 kHz tren ca ban phoi.

    `nhac_nen_duong` — V3 (25/09), DUONG DIA PHUONG da giai quyet san cua nhac
    nen KHACH TU TAI LEN (khuon `nen`/`cac_lo`: ham nay khong biet Storage hay
    quyen so huu, no chi nhan mot tep tren dia — nguoi goi phai tu `assets.py`
    xac minh chu so huu roi tai tep ve TRUOC khi goi ham nay, dung cach
    `giai_doan_thoi_gian._duong_doc_duoc` da lam cho `nen`/`cac_lo`). `None` =
    khong co nhac nen; PHAI khop voi `am["nhac_nen"]` (ca hai cung co hoac
    cung vang), neu khong ham nay nem `MasterError` — mot ben noi "co nhac",
    ben kia khong biet phai tron gi la mot loi cau hinh, khong phai mot ca
    hop le de lang le bo qua.

    ⛔ **KHONG them mot `-i` thu ba o `ket_xuat.dung_lenh`** (xem plan §3.2):
       `ket_xuat` chi ghep video + BAN PHOI (2 dau vao). Nhac nen phai vao TRUOC
       `loudnorm`, tuc o DAY — sau `loudnorm` thi mot thanh am luong nhac nen se
       la "mot thanh keo khong lam gi" (`loudnorm` da dua ca ban ve -14 LUFS).
    """
    from . import am_thanh

    a = am_thanh.tu_cai_dat(am)
    nhac_nen = a.get("nhac_nen")
    if bool(nhac_nen) != (nhac_nen_duong is not None):
        raise MasterError(_t(
            'Hồ sơ nhạc nền và tệp nhạc nền phải cùng có hoặc cùng vắng mặt.'))

    Path(dich).parent.mkdir(parents=True, exist_ok=True)
    cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
           "-i", nen]
    for d in cac_lo:
        cmd += ["-i", d]

    nhac_nen_idx = None
    if nhac_nen_duong is not None:
        # ⭐ Bat bien o tren (`bool(nhac_nen) != (nhac_nen_duong is not None)` ->
        #    NEM) da dam bao `nhac_nen` co that o nhanh nay. `assert` de kiem
        #    kieu THAY duoc dieu do — ⛔ khong doi hanh vi, chi noi ra mot dieu
        #    da dung. Neu bat bien kia bi go sau nay thi cho nay do NGAY, thay vi
        #    nem `AttributeError` o `nhac_nen.get`.
        assert nhac_nen is not None
        nhac_nen_idx = 1 + len(cac_lo)
        # 🔴 `-stream_loop -1` PHAI dat TRUOC `-i` cua CHINH no (khop Viral
        #    `xu_ly_video.py:1091-1093`) — dat sau se ap cho dau vao KE TIEP,
        #    khong phai dau vao nay, va ffmpeg khong bao loi ve dieu do.
        if nhac_nen.get("lap", True):
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", nhac_nen_duong]

    # V6 pha 23: chuoi tron nam o `bieu_thuc_tron`, nhan ho so am thanh `am`.
    phan = [bieu_thuc_tron(1 + len(cac_lo), am=am, tong_giay=tong_giay,
                           nhac_nen_idx=nhac_nen_idx)]
    # ⚠️ `dual_mono=true` — mot bai hoc DA TRA GIA o pha 18 cua ban truoc, mang
    #    sang day nguyen ven: mot doan tieng MONO da qua `aformat` thanh stereo
    #    se bi `loudnorm` **do to hon thuc te 3 dB** neu thieu co nay. May sinh
    #    tieng tra ve mono, nen truong hop do khong phai gia dinh — no la duong
    #    chay binh thuong.
    #
    # ⭐ Va no la loai khiem khuyet khong bao gio duoc bao cao: khach khong nghe
    #    ra "sai 3 dB", ho chi thay ban long tieng "hoi to".
    # ── Luot 1: DO ────────────────────────────────────────────────────────
    #
    # ⭐ Cung mot chuoi loc, chi khac duoi `loudnorm` va dich ra `NUL`. Dung
    #    chung chuoi la dieu kien de phep do noi ve dung tin hieu se duoc ap.
    do_duoc = _do_am_luong(cmd, "".join(phan), tong_giay=tong_giay,
                           hoi_huy=hoi_huy, timeout=timeout)

    # ── Luot 2: AP ────────────────────────────────────────────────────────
    phan.append(bieu_thuc_chuan_am("[tron]", "[ra]", tong_giay=tong_giay,
                                   do_duoc=do_duoc))

    # ⭐ Luot 2 ghi ra ban THO; `ghim_tran_phoi` moi ghi ra `dich`. Hai tep chu
    #    khong mot: vong ghim han dinh tu ban THO moi vong, nen ket qua khong
    #    phu thuoc no da chay may vong.
    tho = str(Path(dich).with_name(Path(dich).stem + ".tho.wav"))
    cmd += ["-filter_complex", "".join(phan), "-map", "[ra]",
            "-t", f"{max(0.001, float(tong_giay)):.3f}",
            "-ac", str(SO_KENH), "-ar", str(TAN_SO), "-c:a", "pcm_s16le", tho]
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MasterError(_t('Trộn bản phối quá hạn.')) from exc
    if r.returncode != 0:
        raise MasterError(_t('Trộn bản phối thất bại: {loi}').format(
            loi=(r.stderr or b"").decode("utf-8", "replace")[-300:]))

    # ── Luot 3: GHIM tran theo BAN GIAO da do (asv-final R-03) ────────────
    #
    # 🔴 `loudnorm=TP=` dat tran tren ban PCM, con T5 do tep AAC khach tai ve —
    #    va bo ma hoa co mat mat vot len bao nhieu la thuoc tinh cua TIN HIEU
    #    (do duoc: 0,00-2,78 dB). Nen buoc nay ma hoa THU roi ha tran cho toi
    #    khi ban thu dat tran; xem khoi `BIEN_CHO_CODEC_DB`.
    # ⭐ `bien_tap` xuong tan `do_ban_giao`: ban ma hoa THU phai di qua CUNG
    #    phep doi toc do voi render, neu khong no do mot tin hieu KHAC.
    kq = ghim_tran_phoi(tho, dich, bien_tap=bien_tap, hoi_huy=hoi_huy,
                        timeout=timeout)
    if ghim is not None:
        ghim.update(kq)
    return dich


#: Nam khoa `loudnorm` in ra o `print_format=json`. Thieu mot khoa la phep do
#: khong dung duoc — va **thieu im lang** thi luot hai lai roi ve mot luot ma
#: khong ai biet.
KHOA_DO = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")


def _do_am_luong(cmd_goc: list[str], loc_tron: str, *, tong_giay: float,
                 hoi_huy=None, timeout: int = 1800) -> dict | None:
    """Luot DO cua `loudnorm` hai luot. `None` khi khong doc duoc.

    ⛔ Tra `None` thay vi nem: khong do duoc thi ta ve ban MOT LUOT — ban van
       chay tu truoc toi nay. Mot ban phoi lech 1 dB xau hon mot ban phoi dung,
       nhung tot hon **khong co ban phoi nao**.

    ⚠️ Va no phai ghi log khi lui: mot duong lui im lang la mot duong lui se
       thanh mac dinh ma khong ai phat hien.
    """
    cmd = list(cmd_goc)
    # ⛔ KHONG noi them bo loc nao sau `bieu_thuc_chuan_am`: chuoi do ket
    #    thuc bang mot NHAN ra (`[ra]`), va noi tiep sau mot nhan la cu phap
    #    khong hop le. Ban dau toi them `,aformat=...` vao day va ffmpeg tu
    #    choi ca chuoi — luot do lang le tra `None`, tuc tu lui ve mot luot.
    cmd += ["-filter_complex",
            loc_tron + bieu_thuc_chuan_am("[tron]", "[ra]",
                                          tong_giay=tong_giay, in_json=True),
            "-map", "[ra]",
            # ⛔ `-t` BAT BUOC o luot do, khong phai tuy chon. `apad` chen im
            #    lang **vo han**, nen mot lenh khong co `-t` se chay mai —
            #    va no treo IM LANG: ffmpeg khong bao gi, tien trinh cha doi
            #    toi khi het gio. Da dinh dung the mot lan.
            "-t", f"{max(0.001, float(tong_giay)):.3f}",
            "-f", "null", "-"]
    # `loudnorm` in JSON o loglevel `info`, con ca chuoi nay chay `-loglevel
    # error`. Nang rieng cho luot do.
    try:
        i = cmd.index("error")
        cmd[i] = "info"
    except ValueError:
        pass
    cmd = [c for c in cmd if c != "-hide_banner"]
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired:
        log.warning("do am luong qua han — lui ve loudnorm mot luot")
        return None
    if r.returncode != 0:
        log.warning("do am luong that bai — lui ve loudnorm mot luot")
        return None

    van = (r.stderr or b"").decode("utf-8", "replace")
    m = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", van, re.S)
    if not m:
        log.warning("khong thay JSON cua loudnorm — lui ve mot luot")
        return None
    try:
        goi = json.loads(m[-1])
    except ValueError:
        log.warning("JSON cua loudnorm khong doc duoc — lui ve mot luot")
        return None

    thieu = [k for k in KHOA_DO if k not in goi]
    if thieu:
        log.warning("do am luong thieu khoa %s — lui ve mot luot", thieu)
        return None
    # ⛔ `-inf` xuat hien khi doan vao im lang hoan toan. `linear=true` voi mot
    #    gia tri vo cuc cho ra mot bo loc khong hop le, va ffmpeg tu choi CA
    #    chuoi — tuc mot ban phoi im lang se lam hong ca lan chay.
    if any(str(goi[k]).lstrip("-").lower().startswith("inf") for k in KHOA_DO):
        log.warning("do am luong tra vo cuc (ban tron im lang?) — lui ve mot luot")
        return None
    # 🔴 V3 (25/09) — do DUOC that, tu mot ca nhac nen o gain cao + nguon gan
    #    full-scale (`test_4855::test_GAIN_CAO_khong_vuot_DINH_THAT`): `amix
    #    normalize=0` CONG nhieu nguon gan 0 dBFS co the day `measured_I` VUOT
    #    mien hop le cua chinh `loudnorm` (`[-99, 0]` — thong bao ffmpeg khi vi
    #    pham: "Value X for parameter 'measured_I' out of range [-99 - 0]").
    #    Luot DO (`-f null -`) van THANH CONG o day: no chi DO, khong AP dung.
    #    Luot AP moi NEM khi nhan gia tri do lam tham so `measured_I=` — tuc
    #    mot ho so hop le (am_luong_nen trong dung mien) van co the lam CA LAN
    #    CHAY CHET neu khong bat truoc o day. Cung mot duong lui voi `-inf`
    #    ngay tren: canh bao, tra `None`, `tron_cuoi` tu lui ve mot luot.
    try:
        if not (-99.0 <= float(goi["input_i"]) <= 0.0):
            log.warning("do am luong: input_i=%s ngoai mien hop le cua loudnorm "
                        "([-99, 0]) — lui ve mot luot", goi["input_i"])
            return None
    except (TypeError, ValueError):
        log.warning("do am luong: input_i khong doc duoc thanh so — lui ve mot luot")
        return None
    return {k: goi[k] for k in KHOA_DO}


def chia_lo(n: int, *, moi_lo: int | None = None) -> list[tuple[int, int]]:
    """Chia `n` doan thanh cac lo `[bat, ket)`.

    ⛔ `moi_lo=None` chu khong phai `moi_lo=DOAN_MOI_LO`: mot gia tri mac dinh
       duoc gan LUC DINH NGHIA HAM, nen doi hang so sau do khong doi duoc gi.
       Bai hoc nay tra gia o pha 14 (`long_tieng.chia_lo`).
    """
    k = max(1, int(moi_lo if moi_lo is not None else DOAN_MOI_LO))
    return [(i, min(n, i + k)) for i in range(0, max(0, n), k)]


def _am_day_du(am: dict | None) -> dict:
    from . import am_thanh

    return am_thanh.tu_cai_dat(am)


def _lop_nen_day_du(lop_nen: dict | None) -> dict:
    from . import tach_tieng

    return tach_tieng.tu_cai_dat_lop(lop_nen)


def van_tay_master(*, van_tay_nen: str, van_tay_ke_hoach: str,
                   phien_ban_ffmpeg_: str,
                   am_thanh: dict | None = None,
                   lop_nen: dict | None = None) -> str:
    """Van tay cua ban phoi.

    Nam thanh phan, thieu bat cu cai nao deu lam cache noi doi: ban nen · ke
    hoach dat doan · phien ban cong cu · phien ban ma (+ ho so am thanh + ho so
    ba lop nen).

    🔴 **`van_tay_ban_do` DA ROI KHOI day (b4 hai giai doan, 25/09).** Ban phoi
       cua giai doan 1 phu am cho **toan bo** do dai goc, nen khong con mot ban
       do cat nao de bam. Giu mot tham so luon nhan cung mot gia tri se lam
       nguoi doc sau tuong ban phoi con phu thuoc cach cat — va ho se di tim
       phep cat o giai doan sai.

    ⚠️ `PHIEN_BAN_MASTER` 3 -> 4 vi the: mot ban phoi cua thu tu CU (do dai =
       phan con lai sau cat) ⛔ khong duoc dung lai cho lan chay moi (do dai =
       nguon).
    """
    goi = json.dumps({
        "nen": van_tay_nen,
        "ke_hoach": van_tay_ke_hoach,
        "ffmpeg": phien_ban_ffmpeg_,
        "nen_giam_db": NEN_GIAM_DB,
        "lufs": lufs_dich(),
        "dinh": dinh_that_db(),
        "phien_ban": PHIEN_BAN_MASTER,
        # V6 pha 23: ho so am thanh DAY DU (ca mac dinh). Thieu no thi mot ban
        # phoi tron o -6 dB duoc dung lai cho mot lan chay chon -18 dB.
        "am_thanh": _am_day_du(am_thanh),
        # B2 (25/09): ho so BA LOP demucs DAY DU (ca mac dinh) — xem chu thich
        # bump PHIEN_BAN_MASTER 4 -> 5 o tren ve vi sao ghi THANG chu khong
        # tin no "di theo" qua `van_tay_nen`.
        "lop_nen": _lop_nen_day_du(lop_nen),
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def kiem_ban_ra(duong: str, *, mong_doi_giay: float, dung_sai_giay: float,
                ghim: dict | None = None) -> dict:
    """Do ban phoi THAT va doi chieu voi thoi luong mong doi.

    ⛔ Do tren TEP, khong tin bat cu con so nao ta tu tinh: ca pha nay la mot
       chuoi phep tinh, va mot phep tinh sai se cho ra mot ke hoach dep va mot
       tep sai. Chi phep do tren tep moi phan biet duoc hai thu do.
    """
    from . import nhap_media, tach_tieng

    tt = nhap_media.soi(duong)
    if tt["tan_so"] != TAN_SO:
        raise MasterError(_t('Bản phối sai tần số lấy mẫu.'))
    if tt["so_kenh"] != SO_KENH:
        raise MasterError(_t('Bản phối sai số kênh.'))
    lech = float(tt["thoi_luong"]) - float(mong_doi_giay)
    if abs(lech) > float(dung_sai_giay):
        raise MasterError(
            _t('Bản phối lệch thời lượng {lech} giây so với dự kiến.')
            .format(lech=round(lech, 3)))
    am = tach_tieng.do_am_luong(duong)
    # ⭐ **Dinh that cua BAN GIAO vao ho so giai doan.** Do la con so T5 se hoi,
    #    va truoc ban nay khong giai doan nao biet no truoc khi render xong.
    #
    # 🔑 `ghim` = bao cao `tron_cuoi` vua tra ve; no da do DUNG tep nay bang
    #    DUNG lenh nay o vong cuoi. Do lai la mot luot `loudnorm` 192 kHz tren
    #    ca ban phoi de nhan cung mot con so.
    dinh_giao = (ghim or {}).get("dinh_giao")
    if dinh_giao is None:
        dinh_giao = float(do_ban_giao(duong)["dinh_that"])
    return {"thoi_luong": round(float(tt["thoi_luong"]), 3),
            "lech_giay": round(lech, 3), **am,
            "dinh_that_giao": round(float(dinh_giao), 2),
            "tran_phoi_da_ghim": (ghim or {}).get("tran_phoi"),
            "so_vong_ghim": (ghim or {}).get("so_vong"),
            # ⭐ T4 (28/09): do to cua BAN GIAO va phan bu da ap. `lufs` ngay tren
            #    la do to cua ban phoi PCM — no KHAC do to khach nhan (atempo +
            #    AAC an 0,18..0,23 LU), va T4 hoi dai luong duoi day. Ghi CA HAI
            #    de khong ai phai doan chung la mot.
            "lufs_giao": (ghim or {}).get("lufs_giao"),
            "gain_do_to": (ghim or {}).get("gain_do_to"),
            "dat_do_to": (ghim or {}).get("dat_do_to"),
            "ket_do_to": (ghim or {}).get("ket_do_to"),
            "vot_lo_codec": round(float(dinh_giao) - float(am["dinh_that"]), 2)}
