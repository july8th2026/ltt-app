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
PHIEN_BAN_MASTER = 2

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
#: 🔑 **CHUA doi gia tri, va day la ly do.** Ta biet 2,0 khong du cho MOT ban
#:    nguon, nhung chua biet **can bao nhieu** — vi chua biet cai gi trong tin
#:    hieu quyet dinh vot lo. Nang len mot con so doan duoc se lam phep kiem
#:    xanh va de nguyen cau hoi; ha xuong thi te hon nua. Dieu kien de doi: do
#:    vot lo tren vai ban nguon THAT khac nhau, tim ra bien nao dieu khien no,
#:    roi dat bien du theo bien do — khong theo lan hong to nhat da thay.
#:
#: ⭐ Duong do cho lan sau da san: mot luot hong nay giu lai ca ban phoi lan ban
#:    giao (`test_448._giu_tang_vat`), nen cap tep can do khong con bien mat
#:    cung thu muc tam nua.
#:
#: ── BA gia thuyet DA BI LOAI, dung thu lai ────────────────────────────────
#:
#: 1. **Bo ma hoa AAC.** Lay CHINH ban phoi that, ma hoa bang dung tham so san
#:    pham (`aac 192k`): vot lo **0,10 va 0,17 dB**. Khong phai no.
#:
#: 2. **Phep lay mau lai 44,1 -> 48 kHz.** Chay lai y het nhung GIU 44,1 kHz:
#:    vot lo khong doi (0,18 so voi 0,26 tren cung nguon). Khong phai no.
#:
#: 3. **"Limiter ep cang manh thi vot lo cang nhieu"** — chinh loi giai thich ghi
#:    o tren. Day ban phoi that len tung nac (0/3/6/9/12/18 dB) roi han cung:
#:
#:        day  0 dB -> vot lo 0,09      day  9 dB -> vot lo 0,40
#:        day  3 dB -> vot lo 0,17      day 12 dB -> vot lo 0,29
#:        day  6 dB -> vot lo 0,00      day 18 dB -> vot lo 0,30
#:
#:    Tran **0,40 dB**, khong toi mot phan sau cua 2,78. Gia thuyet nay giai
#:    thich duoc mot phan nho va khong giai thich duoc ca hien tuong.
#:
#: ⚠️ Va phep do so 3 tu phoi bay mot cai bay dang ghi lai: dinh ban phoi TROI
#:    tu -3,48 len -2,68 khi day manh, tuc `alimiter` khong giu duoc tran. Vi
#:    `alimiter` han dinh MAU con `loudnorm` do dinh THAT (giua mau) — hai dai
#:    luong khac nhau. San pham khong dinh (no dung `loudnorm=TP=`), nhung ai do
#:    lai dung `alimiter` de "cho chac" thi se tao ra dung cai lech nay.
#:
#: 🔑 ⇒ Nghi can con lai la mot thuoc tinh nao do cua **noi dung tieng noi that**
#:    ma ban model gia khong co. Khong con doan nua: luot hong lan sau giu lai
#:    ban phoi, va luc do do THANG tren no.
BIEN_CHO_CODEC_DB = 2.0


def dinh_that_phoi_db() -> float:
    """Tran dinh that cua BAN PHOI — thap hon tran giao hang mot bien du."""
    return dinh_that_db() - BIEN_CHO_CODEC_DB


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


def bieu_thuc_tron(n: int, *, am: dict | None = None, tong_giay: float = 0.0) -> str:
    """Chuoi loc: nen (dau vao 0) + `n-1` ban lo tieng -> nhan `[tron]`.

    Tach rieng de KIEM duoc ma khong chay ffmpeg (`test_479`).

    ⭐ Ho so MAC DINH ra **dung tung ky tu** chuoi truoc pha 23: cung `volume`,
       cung mot `amix` gom het. Doi chuoi cua duong mac dinh la doi ban ra cua
       moi lan chay khong chinh gi — viec do phai di kem `PHIEN_BAN_MASTER`.
    """
    from . import am_thanh

    a = am_thanh.tu_cai_dat(am)
    muc = "volume=0" if a["nen_db"] is None else f"volume={a['nen_db']}dB"
    phan = [f"[0:a]{muc},"
            f"aformat=sample_fmts=fltp:sample_rates={TAN_SO}:"
            f"channel_layouts=stereo[nen];"]
    for i in range(1, n):
        phan.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates={TAN_SO}:"
                    f"channel_layouts=stereo[t{i}];")
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
                    f"[nen][khoa]sidechaincompress={am_thanh.THAM_SO_HA_THEO_LOI}[nend];"
                    f"[nend][gm]amix=inputs=2:normalize=0:dropout_transition=0{dich};")
    else:
        phan.append(f"[nen]{lo}amix=inputs={n}:normalize=0:dropout_transition=0{dich};")
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
              hoi_huy=None, timeout: int = 1800, am: dict | None = None) -> str:
    """Tron ban nen (da ha muc) voi cac ban lo tieng, roi chuan am luong.

    ⭐ Chuan am luong **mot lan o cuoi**, khong phai o tung lo: `loudnorm` doi
       muc cua ca dong tin hieu, nen chay no tren tung manh roi cong lai cho ra
       mot ket qua khong ai du doan duoc.
    """
    Path(dich).parent.mkdir(parents=True, exist_ok=True)
    cmd = [media.ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
           "-i", nen]
    for d in cac_lo:
        cmd += ["-i", d]

    # V6 pha 23: chuoi tron nam o `bieu_thuc_tron`, nhan ho so am thanh `am`.
    phan = [bieu_thuc_tron(1 + len(cac_lo), am=am, tong_giay=tong_giay)]
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

    cmd += ["-filter_complex", "".join(phan), "-map", "[ra]",
            "-t", f"{max(0.001, float(tong_giay)):.3f}",
            "-ac", str(SO_KENH), "-ar", str(TAN_SO), "-c:a", "pcm_s16le", dich]
    try:
        r = _chay(cmd, timeout=timeout, hoi_huy=hoi_huy)
    except subprocess.TimeoutExpired as exc:
        raise MasterError(_t('Trộn bản phối quá hạn.')) from exc
    if r.returncode != 0:
        raise MasterError(_t('Trộn bản phối thất bại: {loi}').format(
            loi=(r.stderr or b"").decode("utf-8", "replace")[-300:]))
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


def van_tay_master(*, van_tay_nen: str, van_tay_ke_hoach: str,
                   van_tay_ban_do: str, phien_ban_ffmpeg_: str,
                   am_thanh: dict | None = None) -> str:
    """Van tay cua ban phoi.

    Nam thanh phan, thieu bat cu cai nao deu lam cache noi doi: ban nen · ke
    hoach dat doan · ban do cat · phien ban cong cu · phien ban ma.
    """
    goi = json.dumps({
        "nen": van_tay_nen,
        "ke_hoach": van_tay_ke_hoach,
        "ban_do": van_tay_ban_do,
        "ffmpeg": phien_ban_ffmpeg_,
        "nen_giam_db": NEN_GIAM_DB,
        "lufs": lufs_dich(),
        "dinh": dinh_that_db(),
        "phien_ban": PHIEN_BAN_MASTER,
        # V6 pha 23: ho so am thanh DAY DU (ca mac dinh). Thieu no thi mot ban
        # phoi tron o -6 dB duoc dung lai cho mot lan chay chon -18 dB.
        "am_thanh": _am_day_du(am_thanh),
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def kiem_ban_ra(duong: str, *, mong_doi_giay: float, dung_sai_giay: float) -> dict:
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
    return {"thoi_luong": round(float(tt["thoi_luong"]), 3),
            "lech_giay": round(lech, 3), **am}
