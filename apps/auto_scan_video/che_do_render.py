"""Chon cach render: SAO CHEP luong hinh hay CAT-NOI roi ma hoa lai.

## Hai preset, hai duong, va chung khong thay the nhau duoc

`localize_preserve_picture` khong cat canh nao, nen luong hinh di thang tu nguon
sang ban ra: `-c:v copy`. Khong giai ma, khong ma hoa, khong mat mat the he,
khong ton mot suat GPU nao. Do la duong da chung minh cua V2 (D-ASV-03).

`smart_localize` cat canh, nen ban ra la mot chuoi cac khoang duoc noi lai.

## 🔴 Vi sao preset CAT khong the dung `-c:v copy`

Nghe rat hap dan: cat-noi bang stream copy thi cung khong mat mat the he. Nhung
**cat bang stream copy chi cat duoc tai KEYFRAME**, va do la mot rang buoc cua
dinh dang chu khong phai cua ffmpeg.

⭐ **Do that 04/09 tren mot tep H.264 do chinh chuoi nay sinh ra**
   (`libx264 -preset veryfast`, mac dinh):

       keyframe o: 0, 8.33, 16.67, 25.00, 33.33, 41.67, ... giay
       GOP = **8,333 giay**, deu tam tap

   Tuc mot diem cat canh o giay 20 se bi day ve giay 16,67 hoac 25 — **lech toi
   8,3 giay**. Trong khi ban phoi am (pha 16) da duoc dung theo diem cat CHINH
   XAC. Hinh va tieng lech nhau tam giay.

⇒ Preset cat **phai ma hoa lai** luong hinh. Do khong phai mot lua chon toi uu
  hoa; do la dieu kien de hinh va tieng con khop nhau.

## Chon bo ma hoa: do, roi moi chon

⚠️ "Uu tien phan cung" la mot phan xa, khong phai mot ket luan. Do that 04/09,
   cat-noi ba khoang (160 giay hinh, 1280x720) tren may nay:

   | cau hinh | thoi gian | kich thuoc | SSIM vs nguon | CPU toan may (TB) |
   |---|---|---|---|---|
   | `libx264 veryfast crf23` | 8,31 s | 40,6 MB | 0,99578 | 61,1% |
   | `h264_nvenc p4 cq23` | 4,98 s | 80,6 MB | 0,99795 | — |
   | **`h264_nvenc p4 cq28`** | **4,95 s** | 50,8 MB | **0,99519** | **40,9%** |
   | `h264_nvenc p4 cq31` | 4,95 s | 36,7 MB | 0,99190 | — |

🔴 **Phep so dau tien cua toi sai thang do**: `cq=23` cua NVENC khong cung thang
   voi `crf=23` cua x264, nen ban dau no "lon gap doi" mot cach vo nghia. Chi khi
   can bang CHAT LUONG (SSIM ≈ 0,995) thi phep so moi doc duoc.

⭐ O cung muc chat luong, NVENC **nhanh 1,68 lan** va **lon hon 25%**. Khong ben
  nao ap dao. Cai quyet dinh la chieu thu ba: **CPU trung binh toan may 61% ->
  41%**. Tren may nay CPU la tai nguyen tranh chap — ca chuoi su co dan toi phien
  lam viec nay bat dau bang nhung lan reset vi qua tai CPU — con GPU thi ranh.

⚠️ Va mot dieu phai noi cho dung: **dinh CPU cua ca hai deu ~91%**. NVENC chi go
   phan MA HOA; giai ma H.264 va bo loc cat-noi van chay tren CPU. Noi "GPU ganh
   het" la noi sai; no ganh mot phan, va phan do do duoc.

⇒ Uu tien NVENC khi co, `libx264` la duong lui **duoc khai ro** chu khong phai
  mot cho tut xuong im lang.
"""
from __future__ import annotations

import json

from platform_core.i18n import _ as _t

#: Doi khi doi bat cu chinh sach nao o duoi. Vao van tay ban dung.
#: ⬆️ 1 -> 2 khi `van_tay_che_do` them `vung` (V5). Khong bump thi mot ban
#:    render cu va mot ban co vung che se dung chung van tay.
#: ⬆️ 2 -> 3 (V6 pha 12) khi `tu_giay`/`den_giay` **bat dau co tac dung** va vao
#:    van tay. Bat buoc bump: moi ban render dung o phien ban 2 duoc tinh khi
#:    khoang thoi gian con la mot truong CHET, nen no khong the tra loi cho mot
#:    cau hoi nay da khac.
#: ⬆️ 3 -> 4 (V6 pha 11) khi `lop_phu` chu vao chuoi loc va vao van tay.
#: ⬆️ 4 -> 5 (V6 pha 08b) khi `logo` vao chuoi loc va vao van tay — va vi thu tu
#:    chang doi: `noi -> che -> logo -> chu`.
# ⭐ 5 -> 6 o pha 14: phu de dot vao hinh la mot bien doi DIEM ANH moi trong
#    chuoi loc, nen moi ban dung cu phai duoc coi la mot quyet dinh render KHAC.
#    Thieu buoc tang nay thi mot lan chay co phu de va mot lan khong se dung
#    chung van tay — hai ket qua khac nhau, mot chuoi bam.
# ⭐ 6 -> 7 (asv-final): chang KHUNG (cat/phong/ti le) + TOC DO vao chuoi loc, va
#    ca logo + phu de KHONG co lop phu chu doi nhan (`[ra]ass..[ra]` -> `sau_logo`).
# ⭐ 7 -> 8 (asv-gui 25/09): them mot buoc DIEM ANH (`hflip` + `eq=saturation`)
#    vao chuoi loc, va doi cach noi nhan giua cac buoc (`truoc_khung` thanh mot
#    chuoi buoc thay vi mot buoc).
# ⭐ 8 -> 9 (asv-vung 25/09, V5): chang VUNG khong con mot cach lam mo duy nhat —
#    `vung_che.LOAI_DIEN_NEN` sinh mot nhanh filter KHAC HAN (`crop`+`vflip`+
#    `scale`+`alphamerge`). Toan bo chang di qua mot bo dieu phoi moi
#    (`_loc_vung`) thay vi `_loc_lam_mo` goi thang.
# ⭐ 9 -> 10 (gd2-diem-anh, chuyen chang DIEM ANH xuong GD2): `logo · lop_phu
#    (watermark) · phu de · khung (crop/zoom/doi ti le) · diem_anh (lat guong,
#    dich mau)` ROI khoi `loc_cat_noi` (GD1) va sang `loc_cat_hai_dong` (GD2,
#    `giai_doan_hinh_anh.py`) — hai ham dung CUNG cac ham thap (`_loc_khung`,
#    `_loc_diem_anh`, `_loc_logo`, `_loc_chu`) nen mot khung hinh burn ra GIONG
#    HET du di qua duong nao (xem preview `phu_de.lenh_xem_truoc`, van goi
#    `loc_cat_noi` khong doi). `loc_cat_noi` GIU NGUYEN chu ky va hanh vi —
#    GD1 chi con goi no voi `vung`/`bien_tap={"toc_do":...}`, moi tham so con
#    lai rong.
#
#    🔴 **Vi sao bump nay bat buoc du `loc_cat_noi` khong doi mot dong.** Chuoi
#       lenh THAT SU cham vao (o day la GD1) DA DOI: `ket_xuat.dung_lenh` (GD1)
#       thoi truyen `lop_phu`/`ds_logo`/`duong_ass`/khung-hinh-hoc — mot ban
#       dung CU (con logo/lop_phu trong `hinh`) qua `ket_xuat` MOI se render
#       THIEU chung, IM LANG. Va `loc_cat_hai_dong` (GD2) tu mot ham chi cat
#       thanh mot ham cat-VA-dan-diem-anh — tep GD2 cu (khong logo) va tep GD2
#       moi (co logo) phai la HAI van tay khac nhau.
#
# 🔴 **Bump nay KHONG phai thu tuc.** `_van_tay` cua giai doan RENDER bam
#    (ban_dung, PHIEN_BAN_KET_XUAT, PHIEN_BAN_CHE_DO, ffmpeg). Hai co moi nam
#    TRONG ban dung nen mot lan chay co bat co da doi van tay — nhung mot lan
#    chay KHONG bat co nao van di qua ma sinh lenh **moi**. Neu ma sinh lenh doi
#    ma so nay khong doi, mot lan chay lai se lay lai tep cu cua ma **cu**, va
#    no khong bao gio no: no hien ra nhu mot lan chay "nhanh bat thuong".
#
# ⚠️ **Tang duoi CUNG phai bump — bai hoc `a038d0a1` (PHIEN_BAN_MASTER/
#    PHIEN_BAN_TACH).** `thi_hanh.phien_ban_engine(RENDER)` KHONG doc hang so
#    nay (chi doc `ket_xuat.PHIEN_BAN_KET_XUAT`) — nen lan bump nay PHAI di
#    cung mot lan bump `ket_xuat.PHIEN_BAN_KET_XUAT`, neu khong gate cache o
#    CAP GIAI DOAN cua RENDER se khong tu lam moi du noi dung tep da khac.
#    `phien_ban_engine(IMAGE_FINISH)` thi da doc hang nay truc tiep — tang do
#    tu dong theo.
PHIEN_BAN_CHE_DO = 10

#: Sao chep luong hinh — preset giu hinh.
SAO_CHEP = "sao_chep"
#: Cat cac khoang duoc giu roi noi lai, ma hoa lai — preset cat.
CAT_MA_HOA_LAI = "cat_ma_hoa_lai"
CHE_DO = (SAO_CHEP, CAT_MA_HOA_LAI)

#: Tham so ma hoa cho tung bo. Con so lay tu phep do o dau tep.
#:
#: ⛔ `cq=28` cho NVENC chu khong phai 23: xem bang do. 23 cho ra tep lon gap doi
#:    ma mat thuong khong phan biet duoc (SSIM 0,99795 vs 0,99519) — tuc tra tien
#:    bang dung luong dia va bang thong cho mot thu khong ai thay.
THAM_SO = {
    "h264_nvenc": ("-c:v", "h264_nvenc", "-preset", "p4", "-cq", "28"),
    "h264_qsv": ("-c:v", "h264_qsv", "-global_quality", "28"),
    "h264_amf": ("-c:v", "h264_amf", "-quality", "balanced", "-qp_i", "28"),
    "libx264": ("-c:v", "libx264", "-preset", "veryfast", "-crf", "23"),
}

#: Thu tu uu tien. `libx264` LUON o cuoi va luon co mat.
UU_TIEN = ("h264_nvenc", "h264_qsv", "h264_amf", "libx264")

#: Bo ma hoa duong lui. Ten no o day de khong cho nao phai go lai chuoi.
LUI_VE = "libx264"


class CheDoError(ValueError):
    """Khong chon duoc cach render."""


def che_do_cho(preset: str) -> str:
    """Preset -> cach render. Mot bang, khong phai mot chuoi `if` rai rac.

    ⛔ Khong doan tu so canh bi cat: mot ban bien tap giu **tat ca** canh van la
       preset cat, va no van phai ma hoa lai — vi cung mot ly do keyframe. Suy
       che do tu du lieu thay vi tu khai bao la mo duong cho hai lan chay cung
       mot preset di hai duong khac nhau.
    """
    from .hop_dong_v4 import PRESET, PRESET_GIU_HINH

    if preset not in PRESET:
        raise CheDoError(_t('Preset không hợp lệ: {p}').format(p=preset))
    return SAO_CHEP if preset == PRESET_GIU_HINH else CAT_MA_HOA_LAI


def chon_bo_ma_hoa(*, cho_phep_gpu: bool = True, do_duoc: str | None = None) -> str:
    """Bo ma hoa se dung. `do_duoc` de phep kiem tiem ket qua do.

    ⭐ `cho_phep_gpu=False` la mot **chinh sach duoc khai**, khong phai mot lan
       that bai: nen tang co the tu choi cap GPU vi card dang ban, va khi do CPU
       la duong dung — cham hon, va noi ra duoc vi sao.
    """
    if not cho_phep_gpu:
        return LUI_VE
    if do_duoc is None:
        from platform_core import media

        do_duoc = media.detect_gpu_encoder()
    do_duoc = str(do_duoc or "")
    return do_duoc if do_duoc in THAM_SO and do_duoc != LUI_VE else LUI_VE


def tham_so(bo: str) -> tuple[str, ...]:
    if bo not in THAM_SO:
        raise CheDoError(_t('Bộ mã hoá không được khai: {b}').format(b=bo))
    return THAM_SO[bo]


def dung_gpu(bo: str) -> bool:
    """Bo ma hoa nay co chiem mot suat GPU khong.

    🔑 Nen tang giu cho GPU theo **khai bao**, nen cau tra loi nay phai den TRUOC
       khi render bat dau, khong phai suy ra sau khi da chay.
    """
    return bo != LUI_VE


#: Ban kinh lam mo = canh ngan cua O DUOC CHE chia cho so nay.
#:
#: ⭐ Ti le, khong phai pixel. Mot ban kinh co dinh (vd 10 px) lam mo dam tren
#:    video 480p va gan nhu vo hinh tren 4K — trong khi mot logo phai bi che o
#:    MOI do phan giai.
#:
#: ⚠️ Va tinh tren o duoc che chu khong tren ca khung: mot dai phu de mong o day
#:    khung can ban kinh nho hon nhieu so voi mot o logo vuong o goc, du hai o
#:    nam tren cung mot khung hinh.
_MAU_BAN_KINH = 8


def _bat_khi(cua_so) -> str:
    """`enable=` cho mot vung chi ap trong vai khoang cua BAN RA. Rong = ca video.

    ⚠️ Dau phay phai thoat: trong cu phap filter, `,` ngan hai BO LOC. Cung cai
       bay da lam `min(iw,ih)` do o duoi, va thong bao cua ffmpeg khi do khong
       nhac gi toi dau phay.

    ⭐ Nhieu khoang thi CONG lai: `between()` tra 1 hoac 0, va `enable` chi hoi
       "khac 0 khong". Mot vung bat qua mot cho cat cho ra hai khoang, va tong
       cua chung dung bang 1 o moi thoi diem thuoc mot trong hai.
    """
    if not cua_so:
        return ""
    p = chr(92) + ","
    ve = "+".join(f"between(t{p}{b:.4f}{p}{k:.4f})" for b, k in cua_so)
    return f":enable={ve}"


#: ⛔ Đo DAY TOI DA (px) cua dai NGUON khi dien nen. `localize.py:6106` cua he
#: tham chieu, ha 8 -> 4 ngay 24/08 sau khi do that.
#:
#: 🔴 Day hon nguong nay thi dai nguon **mang theo dong chu ke ben** roi gian
#:    xuong => "chu hien HAI LAN". Do that cua ho: 25 px va 50 px deu loi, 1–8 px
#:    sach.
CHE_KEO_HS_MAX = 4

#: Ti le chieu cao dai duoc NOI ra moi dau de lay cho cho vung TAN BIEN (alpha
#: hinh thang). Chu du an cua he tham chieu xem ba muc 15/30/45 % roi chot 30 %.
#:
#: ⚠️ ⛔ Dung noi bua: bien trong suot nghia la hinh GOC lo ra o do. Khung nao
#:    chu nho cao hon thuong le se roi vao vung tan va **hien chu mo**.
CHE_KEO_FEATHER = 0.30

#: Cung the nhung theo truc X, va NHO hon han (4 % vs 30 %) vi dai rong gap ~5
#: lan chieu cao — lay cung 30 % se tan mat gan het dai.
CHE_KEO_FEATHER_X = 0.04

#: Chieu dai/rong nho nhat (px) cua mot vung dien nen. Duoi muc nay thi `crop`
#: + `scale` khong con y nghia, va cac guard chia-cho-0 ben duoi bat dau mong.
CHE_KEO_CANH_MIN = 8


def _chan2(n: int) -> int:
    """Kep ve SO CHAN, san 0. Dung cho MOI do day cua nhanh dien nen.

    🔴 VI SAO BAT BUOC (`localize.py:6110`, bug 12/08/2026 tai hien 100 %): chuoi
       nay chay sau `format=yuv420p`, ma yuv420p lay mau chroma **2:1 theo chieu
       DOC** => dai nguon cao **1 px** cho ra **0 hang** chroma:

           [Parsed_crop] Invalid too big or non positive size ... height '0'

       ffmpeg chet `-22` o **ca** `h264_nvenc` **lan** `libx264`. Do that ma tran
       5 to hop: `hs=1` LOI · `hs=2` OK · `hs=8` OK.

    ⭐ San la 0 chu **khong phai 1**: `0` = *"het cho o ben nay"*, mot tin hieu
       ma cho goi doc duoc. San 1 bien "het cho" thanh "con 1 px" => dung crop
       1 px => chet.
    """
    return max(0, int(n) // 2 * 2)


def _noi_cho_tan(v0: int, dai: int, f: int, san: int, tran: int
                 ) -> tuple[int, int, int, int]:
    """NOI `[v0, v0+dai)` ra hai phia toi da `f` px lay cho cho vung TAN BIEN,
    kep trong `[san, tran]`. Tra `(v0_moi, dai_moi, tan_dau, tan_cuoi)`.

    Chep `localize.py:6142`. Hai tinh chat SONG CON, ca hai deu la bug da bat:

    ① **Do dai LUON CHAN.** Ban dau cua ho viet `min(<da lam chan>, tran - v0)` —
       ve thu hai co the LE va `min` chon dung no (do that: dai sat day ra cao
       **71**). Xem `_chan2`. Le thi keo dai THEM VE PHIA DAU (van phu tron), het
       cho moi cat.

    ② **Tan bien suy NGUOC tu hinh hoc cuoi**, khong phai tu `f` mong muon: lam
       tron / kep co the doi mep, ma **loi duc phai trum khit doan goc** — hut
       1 px la ho chu.
    """
    v1 = v0 + dai
    a = max(san, v0 - max(0, int(f)))
    b = min(tran, v1 + max(0, int(f)))
    n = b - a
    if n % 2:
        if a - 1 >= san:
            a -= 1
            n += 1
        else:
            n -= 1
    return a, n, max(0, min(v0 - a, v1 - a - 1)), max(0, (a + n) - v1)


def _min_long(xs: list[str]) -> str:
    """Long `min()` HAI tham so cho N bieu thuc.

    ⛔ ffmpeg **khong co** `min` ba tham so: viet `min(a,b,c)` thi filter chet ma
       thong bao chi noi *"Error initializing filters"*, ⛔ khong neu bieu thuc
       nao. (`xu_ly_video.py:1349`.)
    """
    e = xs[0]
    for x in xs[1:]:
        # `\,` chu khong `,`: trong cu phap filter, `,` ngan hai BO LOC — cung
        # cai bay ma ban kinh `min(w\,h)` cua `_ve_lam_mo` da ghi.
        e = "min(%s%s,%s)" % (e, chr(92), x)
    return e


def _alpha_hinh_thang(rong: int, cao: int, trai: int, phai: int,
                      tren: int, duoi: int) -> str:
    """Chuoi loc sinh anh ALPHA hinh thang: trong suot sat mep, duc han sau `f`
    px moi canh. `""` khi ⛔ khong canh nao can tan (cho goi khoi `alphamerge`).

    🔴 CANH KHONG NOI DUOC (`f = 0`) PHAI DE DUC HAN, ⛔ KHONG duoc ramp. Ban dau
       cua he tham chieu viet `max(1, f)` "cho chac khoi chia 0" => canh `f=0`
       hoa ra ramp tren DUNG 1 pixel => hang/cot ngoai cung alpha = 0 => **HO
       1 px hinh goc ngay tai mep**. Luoi cua ho bat 4/15 ca, toan o SAT MEP
       KHUNG. (`xu_ly_video.py:1358`.)
    """
    xs: list[str] = []
    if tren > 0:
        xs.append(f"Y/{tren}")
    if duoi > 0:
        xs.append(f"({cao - 1}-Y)/{duoi}")
    if trai > 0:
        xs.append(f"X/{trai}")
    if phai > 0:
        xs.append(f"({rong - 1}-X)/{phai}")
    if not xs:
        return ""
    return (f"color=c=black:s={rong}x{cao}:d=1,format=gray,"
            f"geq=lum='255*min(1{chr(92)},{_min_long(xs)})',format=gray")


def _mo_ngang(rong: int, cao: int) -> str:
    """Lam mo NGANG dai vua keo — lam diu vet doc do dai mong bi gian cao.

    ⚠️ Mo CHI THEO CHIEU NGANG. Vet sinh ra do gian DOC nen bien thien nam theo
       COT => mo ngang la du tri. Mo theo chieu DOC thi tron hang => hang tren
       cung cua ban-thay lech khoi hang goc ngay tren => **LO VACH** o ranh gioi
       (do that hoi con boxblur hai chieu: ban kinh 13 -> vach 12,05, te hon ca
       blur thuong 10,21).

    ⭐ THU NHO ROI PHONG LAI thay cho `gblur` (`xu_ly_video.py:1393`, do that
       12/08/2026 tren 6 video x 3 do phan giai): `gblur` chiem **44–63 %** toan
       bo chuoi loc keo mep, con thu-nho-roi-phong bang **dung gia cua viec BO
       blur han** — `swscale` chay SIMD, `gblur` thi khong. PSNR trong dai so voi
       `gblur`: 39,0–52,1 dB (bo han chi 26,0–42,5 dB).

    ⚠️ `flags=area` khi thu nho THUA `bilinear` o **ca 6/6** video — ⛔ dung doi.
    """
    manh = max(2, cao // 24)
    hep = max(2, (rong // (manh + 1)) // 2 * 2)
    if hep >= rong:
        # Dai hep hon ca he so thu nho — khong thu duoc, thi thoi. ⛔ Khong lui
        # sang `gblur`: no la duong dat ma ta vua bo, va o day dai nho toi muc
        # vet doc khong con dang ke.
        return ""
    return (f",scale={hep}:{cao}:flags=bilinear"
            f",scale={rong}:{cao}:flags=bilinear")


def hinh_hoc_dien_nen(v, rong_nguon: int, cao_nguon: int) -> dict:
    """Hinh hoc PIXEL cua mot vung `dien_nen`, hay `CheDoError` neu ⛔ khong dung
    duoc. Mot NOI duy nhat tra loi cau *"vung nay dien nen duoc khong"*.

    🔴 ⛔ **KHONG CO DUONG LUI IM LANG.** He tham chieu lui ve LAM MO khi ffmpeg
       chet (`localize.py:6588`) — *"khach chon Keo mep nhan ve Lam mo, ton 2
       luot ffmpeg vo ich, va KHONG co gi bao cho khach"*. O ta: hinh hoc khong
       dung duoc thi **nem**, va nem **truoc khi** goi ffmpeg (`ban_dung.kiem`
       goi ham nay, nen no nem ngay luc dung ban dung).

    ⚠️ Ham nay lam viec tren khung **NGUON**: chang `vung` dat TRUOC chang KHUNG
       trong `loc_cat_noi`, nen toa do cua vung la toa do nguon.
    """
    if rong_nguon <= 0 or cao_nguon <= 0:
        raise CheDoError(_t(
            'Vùng điền nền cần biết kích thước khung hình nguồn, nhưng bản '
            'dựng không khai nó.'))
    x0f, y0f = float(v["x0"]), float(v["y0"])
    x0 = max(0, int(round(x0f * rong_nguon)))
    y0 = max(0, int(round(y0f * cao_nguon)))
    rong = max(2, min(int(round((float(v["x1"]) - x0f) * rong_nguon)),
                      rong_nguon - x0))
    cao = max(2, min(int(round((float(v["y1"]) - y0f) * cao_nguon)),
                     cao_nguon - y0))
    if rong < CHE_KEO_CANH_MIN or cao < CHE_KEO_CANH_MIN:
        raise CheDoError(_t(
            'Vùng điền nền quá nhỏ trên khung hình này. Hãy vẽ vùng lớn hơn, '
            'hoặc chọn kiểu làm mờ.'))
    # Dai nguon lay NGAY BEN NGOAI vung. `>= 2` chu khong `>= 1` — xem `_chan2`.
    tren = _chan2(min(CHE_KEO_HS_MAX, y0))
    duoi = _chan2(min(CHE_KEO_HS_MAX, cao_nguon - (y0 + cao)))
    if tren < 2 and duoi < 2:
        # ⛔ Vung trum gan het chieu cao khung: ⛔ khong con hinh nao de lay lam
        #    nen. Noi that ra, ⛔ dung lang le doi sang lam mo.
        raise CheDoError(_t(
            'Vùng điền nền chạm cả mép trên lẫn mép dưới khung hình nên không '
            'còn dải hình nào để lấy làm nền. Hãy thu nhỏ vùng, hoặc chọn kiểu '
            'làm mờ.'))

    # ── NOI cho vung tan bien ───────────────────────────────────────────────
    #
    # ⚠️ CHI chua cho dai nguon o BEN THAT SU LAY NGUON. Chua ca hai ben vo dieu
    #    kien la sai: dai sat day ⛔ khong co nguon duoi (`duoi = 0`) ma van bi tru
    #    4 px => dai noi NGAN hon ca dai goc => **loi duc HUT 3 px o day — dung
    #    cho chu nam**. (`localize.py:7852`.)
    x1g, y1g = x0 + rong, y0 + cao
    y0n, caon, ft, fd = _noi_cho_tan(
        y0, cao, round(cao * CHE_KEO_FEATHER),
        CHE_KEO_HS_MAX if tren >= 2 else 0,
        cao_nguon - (CHE_KEO_HS_MAX if duoi >= 2 else 0))
    x0n, rongn, fl, fr = _noi_cho_tan(
        x0, rong, round(rong * CHE_KEO_FEATHER_X), 0, rong_nguon)
    # ⛔ Đieu kien dung la PHU TRON dai goc, ⛔ KHONG phai "cao hon dai goc": mot
    #    dai bi day LEN roi cat cut o day van "cao hon" ma day lai ho.
    if ((y0n + caon) >= y1g and (x0n + rongn) >= x1g
            and caon >= CHE_KEO_CANH_MIN and rongn >= CHE_KEO_CANH_MIN):
        x0, y0, rong, cao = x0n, y0n, rongn, caon
    else:
        fl = fr = ft = fd = 0    # ⛔ Khong du cho -> mep cung, dung hanh vi cu.

    # Ben lay nguon: uu tien TREN (Đ1 §4.4 — mot ben re hon hai ben ~20 % giay
    # CPU va ~43 % dong ho tuong, ma chat luong do tren render THAT gan nhu bang
    # nhau: giat-hang 0,84 vs 0,73 · vach duoi 6,96 vs 6,99).
    day = tren if tren >= 2 else duoi
    return {"x": x0, "y": y0, "rong": rong, "cao": cao, "day_nguon": day,
            "nguon_y": (y0 - day) if tren >= 2 else (y0 + cao),
            "tan": (fl, fr, ft, fd)}


def _ve_dien_nen(i: int, hien: str, ke: str, v, cs,
                 rong_nguon: int, cao_nguon: int) -> list[str]:
    """Cac ve `filter_complex` DIEN NEN cho mot vung. Chep `localize.py:7830`.

    Lay mot dai MONG ngay ben ngoai vung, **lat doc**, gian phu tron vung, lam
    diu vet doc, roi dan de len qua mot alpha hinh thang.

    🐛 `vflip` la **BAT BUOC**, ⛔ dung go. Dai nguon TREN gom cac hang
       `[y0-day .. y0-1]`; `scale` giu nguyen thu tu nen hang XA bien nhat roi
       vao DINH dai — dung cho phai noi lien voi hang goc `y0-1` => lech `day`
       hang => **LO VACH** o ranh gioi NGOAI. Lat doc thi hang SAT bien nam o
       bien (= mirror padding). Do thang bang anh "hang y co do sang = y": truoc
       khi lat, dinh lay nham hang 91 thay vi 99, buoc nhay tai bien 7,0 (lien
       mach = 1,0).

    🐛 `alphamerge` lay **LUMA** cua anh mat na lam alpha, ⛔ KHONG lay kenh
       alpha. Dung mat na bang anh trang + ramp o kenh alpha la mat na **VO
       HIEU** (luma = 255 khap noi) => mat han phan hoa dan ma ⛔ khong he bao
       loi. Nen `_alpha_hinh_thang` dung LUMA (den -> trang).
    """
    hh = hinh_hoc_dien_nen(v, rong_nguon, cao_nguon)
    x, y = hh["x"], hh["y"]
    rong, cao = hh["rong"], hh["cao"]
    ve = [f"[{hien}]split[dg{i}][dk{i}]",
          f"[dk{i}]crop={rong}:{hh['day_nguon']}:{x}:{hh['nguon_y']},vflip,"
          f"scale={rong}:{cao},setsar=1{_mo_ngang(rong, cao)}[dm{i}]"]
    nhan = f"dm{i}"
    tan = _alpha_hinh_thang(rong, cao, *hh["tan"])
    if tan:
        ve.append(f"{tan}[dt{i}]")
        ve.append(f"[dm{i}][dt{i}]alphamerge[da{i}]")
        nhan = f"da{i}"
    ve.append(f"[dg{i}][{nhan}]overlay={x}:{y}{_bat_khi(cs)}[{ke}]")
    return ve


def _loc_vung(vung, nhan_vao: str, nhan_ra: str, cua_so=None, *,
              rong_nguon: int = 0, cao_nguon: int = 0) -> list[str]:
    """Chang VUNG cua chuoi loc — dieu phoi theo `loai` cua TUNG vung.

    🔑 Hai loai, hai nhanh filter khac han, va chung dung chung mot chuoi nhan:
    vung `i` doc nhan cua vung `i-1`, nen thu tu khach ve duoc giu nguyen.

    ⚠️ `vung_che.LOAI_DANH_DAU_PHU_DE` mang nghia AM (*dung ve phu de dich o
       day*) nhung van di qua nhanh LAM MO — do la hanh vi co tu V5 va
       `phu_de.py:280` ghi ro. ⛔ Dung "sua" no o day.
    """
    from .vung_che import LOAI_DIEN_NEN

    # ⛔ Khong mac dinh im lang: mot lan goi quen `cua_so` phai cho ra "ap ca
    #    video" mot cach TUONG MINH, khong phai vi mot `.get()` tra `None`.
    ds_cua_so = list(cua_so) if cua_so is not None else [None] * len(vung)
    if len(ds_cua_so) != len(vung):
        raise CheDoError(_t('Không dựng được vùng che cho lần chạy này.'))

    ve: list[str] = []
    hien = nhan_vao
    for i, v in enumerate(vung):
        tiep = f"o{i}" if i + 1 < len(vung) else nhan_ra
        if str(v.get("loai") or "") == LOAI_DIEN_NEN:
            ve.extend(_ve_dien_nen(i, hien, tiep, v, ds_cua_so[i],
                                   rong_nguon, cao_nguon))
        else:
            ve.extend(_ve_lam_mo(i, hien, tiep, v, ds_cua_so[i]))
        hien = tiep
    return ve


def _loc_lam_mo(vung, nhan_vao: str, nhan_ra: str, cua_so=None) -> list[str]:
    """Chang VUNG khi ⛔ khong vung nao dien nen. Giu lai vi ba tep test va hai
    tai lieu goi ten no; `_loc_vung` moi la duong that.
    """
    return _loc_vung(vung, nhan_vao, nhan_ra, cua_so)


def _ve_lam_mo(i: int, hien: str, ke: str, v, cs) -> list[str]:
    """Cac ve `filter_complex` lam mo MOT vung tren mot luong hinh.

    `cs` la cac khoang **CUA BAN RA** ma vung nay duoc bat; `None` hoac rong =
    ap ca video. Doi tuong goi phai anh xa truoc — xem `loc_cat_noi`.

    Cach lam: **cat ra -> lam mo -> dan de len**. Khong dung `boxblur` thang
    tren ca khung roi ghep, vi lam the la giai ma va lam mo TOAN BO khung chi de
    lay lai mot o nho.

    ⚠️ Kich thuoc phai CHAN. `libx264` va `h264_nvenc` deu tu choi chieu le o
       mot so dinh dang pixel (`yuv420p` lay mau 2x2), va thong bao cua ffmpeg
       khi do khong nhac gi toi `crop` — no bao mot loi khoi tao encoder. Nen
       `trunc(.../2)*2` o day khong phai lam dep, no la dieu kien de lenh chay.

    ⚠️ Va `x`/`y` cung phai chan, cung ly do lay mau.
    """
    x0, y0 = float(v["x0"]), float(v["y0"])
    rong, cao = float(v["x1"]) - x0, float(v["y1"]) - y0
    # 🔴 **`crop` dung `iw`/`ih`; `overlay` KHONG CO hai bien do** — no dung
    #    `W`/`H` cho khung CHINH va `w`/`h` cho lop dan len.
    #
    #    Do that tren may nay: mot `overlay=trunc(iw*0.1/2)*2` lam ffmpeg nem
    #    *"Error when evaluating the expression ... for x"*, trong khi dung
    #    y het bieu thuc do trong `crop` thi chay. Hai bo loc, hai bo bien —
    #    va tai lieu khong dat chung canh nhau de ai do nhin ra.
    w = f"trunc(iw*{rong:.6f}/2)*2"
    h = f"trunc(ih*{cao:.6f}/2)*2"
    x_crop = f"trunc(iw*{x0:.6f}/2)*2"
    y_crop = f"trunc(ih*{y0:.6f}/2)*2"
    x = f"trunc(W*{x0:.6f}/2)*2"
    y = f"trunc(H*{y0:.6f}/2)*2"
    # 🔴 Ban kinh tinh tren kich thuoc cua CHINH luong da cat (`w`/`h`), khong
    #    tren khung goc.
    #
    #    Ban dau toi viet `min(iw,ih)*0.025` va **ffmpeg tu choi ca chuoi**:
    #    trong cu phap filter, `,` ngan hai BO LOC va `:` ngan hai THAM SO,
    #    nen dau phay trong `min(iw,ih)` bi doc la het bo loc. Thong bao khi
    #    do — *"No option name near '2'"* — khong nhac gi toi dau phay.
    #
    # ⇒ Thoat dau phay bang `\,`. Va dung `w`/`h` thi ban kinh ti le voi
    #   chinh o duoc che, tuc mot o nho khong bi lam mo qua tay.
    r = f"min(w{chr(92)},h)/{_MAU_BAN_KINH}"
    return [f"[{hien}]split[c{i}][g{i}]",
            f"[c{i}]crop={w}:{h}:{x_crop}:{y_crop},"
            f"boxblur=luma_radius={r}:luma_power=2[m{i}]",
            f"[g{i}][m{i}]overlay={x}:{y}{_bat_khi(cs)}[{ke}]"]


def _loc_chu(lop_phu, duong_chu, nhan_vao: str, nhan_ra: str, *,
             cao_khung: int, cua_so=None) -> list[str]:
    """Cac ve `filter_complex` ve tung dong chu len mot luong hinh.

    `duong_chu[i]` la tep UTF-8 chua chu cua lop `i` — xem `lop_phu.viet_tep_chu`
    va doan "`textfile=` chu khong `text=`" o dau tep do. `cua_so[i]` la cac
    khoang **CUA BAN RA** ma lop `i` duoc hien; `None` = suot ca video.

    ⚠️ `drawtext` dat len TREN cung, tuc SAU vung che trong chuoi loc. Nguoc lai
       thi mot dong chu roi trung o che se bi chinh o do lam mo — khach ve chu
       de nguoi ta doc duoc no.
    """
    from . import lop_phu as lp

    ds_cua_so = list(cua_so) if cua_so is not None else [None] * len(lop_phu)
    if len(ds_cua_so) != len(lop_phu) or len(duong_chu) != len(lop_phu):
        raise CheDoError(_t('Không dựng được lớp phủ chữ cho lần chạy này.'))

    font = lp.thoat_duong(lp.duong_font())
    ve: list[str] = []
    hien = nhan_vao
    for i, l in enumerate(lop_phu):
        mau = lp.MAU_FFMPEG[str(l["mau"])]
        do_mo = float(l["do_mo"])
        cai = [
            # ⛔ `expansion=none`: khong co no thi `%` va `{...}` trong chu cua
            #    khach duoc `drawtext` doc nhu ma dinh dang. Mot cau
            #    *"Giam 50%"* van chay, nhung *"%{pts}"* thi in ra dong ho.
            "expansion=none",
            f"fontfile='{font}'",
            f"textfile='{lp.thoat_duong(duong_chu[i])}'",
            f"fontsize=H*{float(l['co_chu']):.6f}",
            f"fontcolor={mau}@{do_mo:.6f}",
            # 🔴 L3: neo o dung cho khach dat, KHONG kep ve bien. Be rong mot
            #    dong chu chi biet duoc khi ffmpeg do font, nen "co tran ra
            #    ngoai khung khong" khong tra loi duoc o cong vao — va kep ve
            #    bien la dung sai lam `localize.py:675` da ghi.
            #
            # 🔴 **`x` la TAM chu, ⛔ khong phai mep trai (B9-2, 28/09).**
            #
            #    `drawtext` neo `x` o **mep trai** hop chu. Khach keo con truot
            #    toi `0,5` nghi *"giua"* va nhan duoc mep trai o giua, tuc duoi
            #    chu tran ra ngoai. Do tren T1a: *"LTT STUDIOS"* dat `x = 0,5`
            #    hien ra **"LTT STUD"** tren MOI frame.
            #
            # ⭐ `text_w` la bien cua chinh `drawtext` — ffmpeg do font roi moi
            #    thay vao, nen day la cho DUY NHAT be rong chu duoc biet. Dung
            #    no ⛔ KHONG pha luat L3: ta van ⛔ khong `max`/`min` gi ca, nen
            #    `x = 0` van cho chu tran sang TRAI dung nhu truoc.
            f"x=(W*{float(l['x']):.6f})-text_w/2",
            f"y=H*{float(l['y']):.6f}",
        ]
        if l.get("vien"):
            # Chu den thi vien trang; con lai vien den. Vien cung mau chu la
            # khong co vien.
            mau_vien = "white" if mau == "black" else "black"
            cai.append(f"borderw={lp.vien_px(l, cao_khung)}")
            cai.append(f"bordercolor={mau_vien}@{do_mo:.6f}")
        ke = f"t{i}" if i + 1 < len(lop_phu) else nhan_ra
        ve.append(f"[{hien}]drawtext={':'.join(cai)}"
                  f"{_bat_khi(ds_cua_so[i])}[{ke}]")
        hien = ke
    return ve


def cua_so_ra_logo(khoang: list[tuple[float, float]], ds_logo
                   ) -> list[list[tuple[float, float]] | None]:
    """`_anh_xa_cua_so` cho LOGO. `None` = hien suot ca video."""
    ra = _anh_xa_cua_so(khoang, ds_logo)
    for cs in ra:
        if cs is not None and not cs:
            raise CheDoError(_t('Một logo được đặt giờ nằm trọn trong đoạn đã '
                                'bị cắt bỏ, nên nó sẽ không bao giờ hiện ra. '
                                'Hãy sửa giờ hoặc xoá logo đó.'))
    return ra


def _loc_logo(ds_logo, nhan_vao: str, nhan_ra: str, *,
              rong_khung: int, chi_so_dau: int, cua_so=None) -> list[str]:
    """Cac ve `filter_complex` dan tung logo len mot luong hinh.

    `chi_so_dau` la so thu tu dau vao ffmpeg cua logo dau tien — trinh render
    truyen video la `0`, ban phoi am la `1`, nen logo bat dau tu `2`.

    ⛔ **So nay phai den TU NGUOI GOI.** Neu module nay tu doan `2`, thi ngay ai
       do them mot dau vao thu ba, moi logo se lay diem anh cua **ban phoi am** —
       va ffmpeg khong bao gi ca, no chi dan mot thu khac len.

    ⚠️ `format=rgba` TRUOC `colorchannelmixer`: mot PNG khong co kenh alpha se
       vao `colorchannelmixer` o `yuv`/`rgb`, va `aa=` khi do khong tro toi kenh
       nao — do mo bi bo qua trong im lang.
    """
    from . import logo as lg

    ds_cua_so = list(cua_so) if cua_so is not None else [None] * len(ds_logo)
    if len(ds_cua_so) != len(ds_logo):
        raise CheDoError(_t('Không dựng được logo cho lần chạy này.'))

    ve: list[str] = []
    hien = nhan_vao
    for i, l in enumerate(ds_logo):
        vao = chi_so_dau + i
        px = lg.rong_px(l, rong_khung)
        do_mo = float(l["do_mo"])
        ve.append(f"[{vao}:v]scale=w={px}:h=-2,format=rgba,"
                  f"colorchannelmixer=aa={do_mo:.6f}[lg{i}]")
        # 🔴 `overlay` KHONG CO `iw`/`ih` — no dung `W`/`H` cho khung chinh va
        #    `w`/`h` cho lop dan len. Cung cai bay `_loc_lam_mo` da ghi.
        x = f"trunc(W*{float(l['x']):.6f}/2)*2"
        y = f"trunc(H*{float(l['y']):.6f}/2)*2"
        ke = f"lo{i}" if i + 1 < len(ds_logo) else nhan_ra
        ve.append(f"[{hien}][lg{i}]overlay={x}:{y}"
                  f"{_bat_khi(ds_cua_so[i])}[{ke}]")
        hien = ke
    return ve


def loc_cat_noi(khoang: list[tuple[float, float]], vung=(), *,
                lop_phu=(), duong_chu=(), cao_khung: int = 0,
                ds_logo=(), rong_khung: int = 0,
                chi_so_logo_dau: int = 2, duong_ass: str = "",
                nhan_ra: str = "ra",
                bien_tap=None, rong_nguon: int = 0, cao_nguon: int = 0) -> str:
    """`filter_complex` cat cac khoang duoc giu roi noi lai — **khong co tieng**.

    ⛔ Tieng khong di qua day. Ban phoi am (pha 16) da duoc dung theo dung nhung
       khoang nay va da chuan am luong mot lan; cho no di qua `concat` lan nua la
       tron hai quyet dinh am thanh o hai cho, va cai thu hai se thang mot cach
       im lang.

    ## `vung` chi co nghia o duong NAY, va do la mot rang buoc VAT LY

    🔴 Lam mo mot vung doi hoi mot BO LOC, va mot bo loc doi hoi **giai ma roi ma
       hoa lai**. Duong `SAO_CHEP` di bang `-c:v copy` — o do khong co cho nao
       dat mot bo loc vao, va D-ASV-03 cam ma hoa lai.

    ⇒ Vung che chi phuc vu duoc o preset **cat**. Do khong phai mot lua chon
      thiet ke ma la mot he qua: khong the vua "sao chep nguyen ven tung diem
      anh" vua "sua mot vung diem anh". `ban_dung.kiem` cuong che dieu nay, va
      giao dien noi ro cho khach truoc khi ho ve.

    ## 🔴 `tu_giay`/`den_giay` la moc NGUON, con bo loc chay tren ban RA

    `vung_che` nhan, kiem va luu hai truong nay tu V5. Cho toi V6 **khong dong
    ma nao doc chung** — mot vung ke gio van bi lam mo suot ca video, va
    `van_tay_che_do` cung khong bam chung, nen hai cau hinh khac nhau dung chung
    mot van tay. Cai thu hai bi cai thu nhat CHE: khi gio khong co tac dung thi
    hai ket qua trung nhau that.

    ⇒ Sua rieng cai thu nhat se **kich hoat** cai thu hai. Hai viec phai di cung
      mot luot, va `PHIEN_BAN_CHE_DO` phai len mot bac.

    ⭐ Va phep anh xa khong duoc viet lai o day: `BanDoThoiGian.ra_khoang` da la
       chu so huu cua "moc nguon -> moc ra". Mot ban thu hai la mot ban se lech,
       va no se lech dung vao ngay ai do doi cach cat.
    """
    if not khoang:
        raise CheDoError(_t('Không có khoảng nào để cắt nối.'))
    phan = []
    for i, (b, k) in enumerate(khoang):
        if k <= b:
            raise CheDoError(_t('Khoảng cắt nối rỗng hoặc ngược.'))
        phan.append(f"[0:v]trim=start={float(b):.6f}:end={float(k):.6f},"
                    f"setpts=PTS-STARTPTS[v{i}]")
    nhan = "".join(f"[v{i}]" for i in range(len(khoang)))
    # ⭐ Lam mo SAU khi noi, khong phai tren tung manh: mot vung ap cho ca video
    #    thi mo tren ban da noi la MOT chuoi bo loc, con mo tung manh la N chuoi.
    #
    # ⚠️ Thu tu BON chang la mot phan cua hop dong:
    #
    #        noi -> che -> logo -> chu
    #
    #    · che truoc logo/chu: nguoc lai thi mot logo roi trung o che se bi
    #      chinh o do lam mo — khach dan logo de nguoi ta NHIN THAY no;
    #    · chu SAU CUNG: chu la thu khach doc, nen no nam tren het.
    #    · phu de SAU CUNG, tren ca chu: no la thu khach doc de HIEU, con lop
    #      phu chu la thu khach dan de TRANG TRI. Mot phu de bi logo hay lop phu
    #      de len la mot phu de khong doc duoc, tuc mot tinh nang khong ton tai.
    #
    # ── Bien tap khung + toc do (asv-final 22/09) ───────────────────────────
    #
    # 🔑 Thu tu day du: noi -> che (toa do NGUON) -> KHUNG (cat/phong/ti le) ->
    #    logo -> chu -> phu de (toa do BAN RA) -> TOC DO (cuoi cung).
    #    · che TRUOC khung: vung che bam theo noi dung nguon; mot vung nam ngoai
    #      cua so cat thi khong con trong khung — L3 cua `vung_che` (loai, khong
    #      kep) dung ma khong can anh xa toa do;
    #    · logo/chu/phu de SAU khung: chung bam theo man hinh ban ra;
    #    · toc do SAU phu de: `.ass` va loi long cung dat tren truc BIEN TAP, va
    #      `setpts` + `atempo` nen ca hai cung mot he so.
    #
    # ⭐ Khong bien tap thi chuoi giu NGUYEN tung ky tu nhu truoc.
    from . import bien_tap as _bt

    # 🔴 **`toc_do` ⛔ KHONG con nhan o day (B6, 27/09).** Toc do la mot phep
    #    **DOI TRUC** thoi gian, va hop dong GD1/GD2 buoc moi phep doi truc xep
    #    SAU moi buoc doc moc — tuc o cuoi GD2 (`loc_cat_hai_dong`).
    #
    # ⚠️ Ap no o day bat ke cat, khe thoai, phu de va QC tu doi truc bang tay o
    #    BA cho, va ba cho ay da sinh ra T2 (QC chia `toc_do` HAI lan), T17 (moc
    #    DTS trung) va mot ca cat vao GIUA cau thoai. Xem
    #    `docs/auto_scan_video_final/B6_PLAN_MOT_TRUC_THOI_GIAN.md`.
    #
    # ⛔ NEM chu ⛔ khong bo qua im lang: mot `toc_do` toi day nghia la noi goi
    #    dang tin rang GD1 con ap toc do, va mot ban giao ⛔ KHONG doi toc do la
    #    thu khach phat hien ra truoc ta.
    if _bt.toc_do(bien_tap) != 1.0:
        raise CheDoError(
            _t('Tốc độ áp ở giai đoạn 2 (hoàn thiện hình), không phải ở render.'))
    # ⚠️ CHI hinh hoc moi keo `_loc_khung` vao: no goi `hinh_hoc.khung_bien_tap`,
    #    mot ham NEM khi chua biet kich thuoc nguon. Mot lan chay chi bat lat
    #    guong khong can biet kich thuoc nao ca, nen `set(bien_tap) - {"toc_do"}`
    #    cua ban cu se bat no phai biet — va bat no hong khi khong biet.
    buoc_khung = (_loc_khung(bien_tap, rong_nguon, cao_nguon)
                  if bien_tap and set(bien_tap) & set(_bt.TRUONG_HINH_HOC)
                  else None)
    # ⭐ **Ten nhan ra la tham so, ⛔ khong hang so go cung (B6).** Ban tham
    #    chieu VMAF (`qc.loc_tham_chieu`) can noi `setpts` VAO SAU chuoi nay de
    #    khop ban giao — ma muon noi vao sau thi phai biet dat ten cho dau ra
    #    trung gian. Go cung `"ra"` bat noi goi phai SUA CHUOI bang tay.
    dich = nhan_ra
    sau_che = dich
    if ds_logo or lop_phu or duong_ass:
        sau_che = "sau_che"

    # ── Cac buoc HINH giua `noi` va `sau_che`, theo thu tu ──────────────────
    #
    # 🔑 **Thu tu la mot quyet dinh, khong phai mot chi tiet.**
    #
    #    · `vung` (lam mo) di TRUOC moi thu: toa do cua no thuoc khung NGUON;
    #    · hinh hoc (cat/phong/ti le) tiep theo;
    #    · DIEM ANH (`hflip`, `eq`) **sau** hinh hoc va **truoc** logo/chu/phu
    #      de. Ca hai ranh gioi deu co ly do:
    #        - sau hinh hoc, vi lat truoc thi moi toa do `crop` phai duoc anh xa
    #          guong — mot phep anh xa khong ai yeu cau va chac chan se lech;
    #        - truoc lop phu, vi lat SAU se lat CA logo va chu cua khach. Mot
    #          dong chu bi lat guong la mot dong chu khong doc duoc, va no se
    #          di thang ra tep giao cho khach.
    giua: list[tuple[str, object]] = []
    if buoc_khung:
        giua.append(("khung", buoc_khung))
    loc_dp = _loc_diem_anh(bien_tap)
    if loc_dp:
        giua.append(("diem_anh",
                     lambda vao, ra, _f=loc_dp: [f"[{vao}]{_f}[{ra}]"]))

    # ⭐ Khong buoc nao thi chuoi giu NGUYEN tung ky tu nhu truoc asv-gui.
    sau_noi = f"truoc_{giua[0][0]}" if giua else sau_che
    if vung:
        phan.append(f"{nhan}concat=n={len(khoang)}:v=1:a=0[noi]")
        phan.extend(_loc_vung(vung, "noi", sau_noi, cua_so_ra(khoang, vung),
                              rong_nguon=rong_nguon, cao_nguon=cao_nguon))
    else:
        phan.append(f"{nhan}concat=n={len(khoang)}:v=1:a=0[{sau_noi}]")
    for i, (ten, dung) in enumerate(giua):
        ke = f"truoc_{giua[i + 1][0]}" if i + 1 < len(giua) else sau_che
        phan.extend(dung(f"truoc_{ten}", ke))

    hien = sau_che
    if ds_logo:
        # ⚠️ Truoc asv-final: `"sau_logo" if lop_phu else "ra"` — logo + phu de
        #    ma KHONG co lop phu chu thi chuoi thanh `[ra]ass=...[ra]`.
        ke = "sau_logo" if (lop_phu or duong_ass) else dich
        phan.extend(_loc_logo(ds_logo, hien, ke, rong_khung=rong_khung,
                              chi_so_dau=chi_so_logo_dau,
                              cua_so=cua_so_ra_logo(khoang, ds_logo)))
        hien = ke
    if lop_phu:
        ke = "sau_chu" if duong_ass else dich
        phan.extend(_loc_chu(lop_phu, duong_chu, hien, ke,
                             cao_khung=cao_khung,
                             cua_so=cua_so_ra_lop_phu(khoang, lop_phu)))
        hien = ke
    if duong_ass:
        # 🔑 **Khong can dieu nhay `cwd` cua `autosubvideo/burn.py`.**
        #
        #    `burn._ass_filter_arg` chay ffmpeg voi `cwd` = thu muc chua `.ass`
        #    roi truyen ten tep tran, *"khoi phai escape duong dan Windows"*.
        #    Nhung ASV da co loi giai tot hon va da dung no cho `textfile=`:
        #    `lop_phu.thoat_duong` doi `\` -> `/` va `:` -> `\:`.
        #
        # ⭐ Escape tot hon `cwd` o mot cho cu the: `cwd` la trang thai TOAN
        #    TIEN TRINH, nen no rang buoc ca lenh ffmpeg vao mot thu muc — trong
        #    khi lenh nay con doc video nguon, anh logo va tep chu o cac thu muc
        #    KHAC. Mot lenh mot cwd thi khong the phuc vu bon duong dan.
        from . import lop_phu as _lp

        phan.append(f"[{hien}]ass='{_lp.thoat_duong(duong_ass)}'[{dich}]")
    return ";".join(phan)


#: Nhan ra cua `loc_cat_hai_dong`. Hang so co ten vi hai noi doc chung: ham dung
#: chuoi loc, va ham dung argv (`-map`).
NHAN_HINH_RA = "vr"
NHAN_TIENG_RA = "ar"


def loc_cat_hai_dong(khoang: list[tuple[float, float]], *,
                     bien_tap=None, rong_nguon: int = 0, cao_nguon: int = 0,
                     ds_logo=(), rong_khung: int = 0, chi_so_logo_dau: int = 1,
                     lop_phu=(), duong_chu=(), cao_khung: int = 0,
                     duong_ass: str = "") -> str:
    """`filter_complex` cat cac khoang duoc giu roi noi lai — **CA HINH VA TIENG**
    — RA sau do di qua chang DIEM ANH (khung, diem_anh, logo, lop_phu, phu de).

    🔴 **Day la cho khac han `loc_cat_noi`, va khac biet ay LA ca giai doan 2.**

        `loc_cat_noi`      chi HINH. Tieng ⛔ khong di qua: ban phoi cua pha 16 da
                           duoc dung theo dung nhung khoang do va chuan am mot
                           lan roi, nen cho no qua `concat` lan nua la tron hai
                           quyet dinh am thanh o hai cho. GD1 (`ket_xuat.py`) chi
                           con goi no voi `vung`/`bien_tap={"toc_do": ...}`.
        `loc_cat_hai_dong` CA HAI, trong MOT `concat`. Dau vao la MP4 **da xong**
                           cua giai doan 1: hinh va tieng cua no la hai dong cua
                           MOT tep, tren MOT truc thoi gian.

    ⭐ Va do la ly do thu tu moi xoa duoc mot lop loi thay vi quan ly no: cat
       `[10;20)` tren mot tep da xong thi giay hinh thu 15 va giay tieng thu 15
       **bien mat cung nhau**, vi chung la cung mot `trim`. ⛔ Khong mot phep anh
       xa nao o giua de ma lech, nen mot doan tieng bi cut ⛔ khong the sinh ra.

    ⚠️ `asetpts=PTS-STARTPTS` la bat buoc, cung ly do voi `setpts` cua hinh: sau
       `atrim`, moc cua manh thu hai van la moc GOC, va `concat` noi khong ke ho
       ⇒ manh do se nam sai cho. Thieu mot trong hai dong thi HINH va TIENG lech
       nhau dung bang do dai phan bi cat — hong theo kieu nghe thay duoc.

    ## Chang DIEM ANH — logo/watermark/phu de/lat guong/dich mau/zoom (25/09)

    🔑 **Chuyen tu `loc_cat_noi` (GD1) xuong day (GD2), va day la CA LY DO cua
       lan tai cau truc nay: mot lan chay co phep doi diem anh nay ⛔ khong con
       ma hoa lai HAI lan (render cua GD1, roi cat o GD2) — no ma hoa lai MOT
       lan, o day, cung mot luot voi phep cat.**

    ⚠️ **Thu tu SAU concat GIONG HET duoi cua `loc_cat_noi`** — dung CUNG cac
       ham thap `_loc_khung`/`_loc_diem_anh`/`_loc_logo`/`_loc_chu`, nen mot
       khung hinh burn ra Y HET du di qua ham nao (preview `phu_de.lenh_xem_truoc`
       van goi `loc_cat_noi`, khong doi):

           concat(hinh+tieng) -> khung (cat/phong/doi ti le) -> diem_anh
           (lat guong/dich mau) -> logo -> lop_phu (chu) -> phu de (`.ass`)

       · khung TRUOC diem_anh: lat truoc thi moi toa do `crop` phai anh xa
         guong — mot phep anh xa khong ai yeu cau;
       · diem_anh TRUOC logo/chu: lat SAU se lat ca logo va chu cua khach;
       · phu de SAU CUNG: no la thu khach doc de HIEU, logo/chu la de trang tri.

    ⛔ **`vung` (lam mo/dien nen) KHONG nhan o day, va do la co y.** `vung` van
       o GD1: no dat truoc `concat` tren toa do NGUON, tren TUNG khoang truoc
       khi noi — trong khi `khoang` o day la khoang CAT cua GD2, tren MP4 GD1
       da xong (GD1 da ap vung xong roi).

    ⭐ **`toc_do` NHAN o day, va no la buoc CUOI CUNG cua ca chuoi (B6, 27/09).**
       Truoc 27/09 no o GD1 va ly le cu la *"chuyen xuong day se lam ke cat va
       toc do tranh nhau tren HAI truc"*. Do thi thay NGUOC: HAI truc la tinh
       trang cua chinh cach cu — GD1 doi truc TRUOC, nen ban do cua phep cat
       (GD2) lam viec tren mot truc ⛔ khong mot ke quyet dinh nao noi, va kho
       phai tu doi truc bang tay o BA cho. Ba cho ay sinh ra T2 · T17 · mot ca
       cat vao giua cau thoai.

    🔑 Dat o **duoi** thi moi buoc tren — cat, hinh hoc, diem anh, logo, chu,
       phu de — da doc moc thoi gian XONG, nen ⛔ khong ai phai doi truc theo.
       Viral lam dung hinh dang nay (`xu_ly_video.py:1140`: `setpts` ngay sau
       zoom/hflip trong CUNG chuoi). Hop dong:
       `docs/auto_scan_video_final/B6_PLAN_MOT_TRUC_THOI_GIAN.md`.

    `chi_so_logo_dau` mac dinh `1` (khac `2` cua `loc_cat_noi`): dau vao `0` o
    day la MOT tep MP4 da co san CA hinh lan tieng (khong co dau vao "ban phoi
    am" rieng nhu GD1), nen logo dau tien la dau vao `1`.
    """
    if not khoang:
        raise CheDoError(_t('Không có khoảng nào để cắt nối.'))
    phan = []
    for i, (b, k) in enumerate(khoang):
        if k <= b:
            raise CheDoError(_t('Khoảng cắt nối rỗng hoặc ngược.'))
        b, k = float(b), float(k)
        phan.append(f"[0:v]trim=start={b:.6f}:end={k:.6f},"
                    f"setpts=PTS-STARTPTS[v{i}]")
        phan.append(f"[0:a]atrim=start={b:.6f}:end={k:.6f},"
                    f"asetpts=PTS-STARTPTS[a{i}]")
    nhan = "".join(f"[v{i}][a{i}]" for i in range(len(khoang)))

    # ── Chang DIEM ANH, y het `giua`/logo/chu/ass cua `loc_cat_noi` ─────────
    from . import bien_tap as _bt

    buoc_khung = (_loc_khung(bien_tap, rong_nguon, cao_nguon)
                  if bien_tap and set(bien_tap) & set(_bt.TRUONG_HINH_HOC)
                  else None)
    loc_dp = _loc_diem_anh(bien_tap)

    # ⭐ **Toc do: buoc CUOI CUNG, tren CA hai dong.** Hai `ve_*` duoi day doc he
    #    so tu CUNG `bien_tap.toc_do`, nen `setpts` va `atempo` ⛔ khong the lech.
    #    Khong doi toc do thi ca hai rong va chuoi giu NGUYEN tung ky tu nhu
    #    truoc B6 — duong `toc_do = 1` ⛔ khong doi mot byte nao.
    ve_hinh = loc_toc_do_hinh(bien_tap, nhan_vao="truoc_toc",
                              nhan_ra=NHAN_HINH_RA)
    ve_tieng = loc_toc_do_tieng(bien_tap, nhan_vao="truoc_toc_a",
                                nhan_ra=NHAN_TIENG_RA)
    hinh_cuoi = "truoc_toc" if ve_hinh else NHAN_HINH_RA
    tieng_cuoi = "truoc_toc_a" if ve_tieng else NHAN_TIENG_RA

    giua: list[tuple[str, object]] = []
    if buoc_khung:
        giua.append(("khung", buoc_khung))
    if loc_dp:
        giua.append(("diem_anh",
                     lambda vao, ra, _f=loc_dp: [f"[{vao}]{_f}[{ra}]"]))

    # ⭐ Khong buoc diem anh nao thi chuoi giu NGUYEN nhu truoc lan tai cau
    #    truc nay: concat ra thang `[vr][ar]`.
    sau_gh = "sau_gh" if (ds_logo or lop_phu or duong_ass) else hinh_cuoi
    video_dau = f"truoc_{giua[0][0]}" if giua else sau_gh
    phan.append(f"{nhan}concat=n={len(khoang)}:v=1:a=1"
                f"[{video_dau}][{tieng_cuoi}]")

    for i, (ten, dung) in enumerate(giua):
        ke = f"truoc_{giua[i + 1][0]}" if i + 1 < len(giua) else sau_gh
        phan.extend(dung(f"truoc_{ten}", ke))

    hien = sau_gh
    if ds_logo:
        ke = "sau_logo" if (lop_phu or duong_ass) else hinh_cuoi
        phan.extend(_loc_logo(ds_logo, hien, ke, rong_khung=rong_khung,
                              chi_so_dau=chi_so_logo_dau,
                              cua_so=cua_so_ra_logo(khoang, ds_logo)))
        hien = ke
    if lop_phu:
        ke = "sau_chu" if duong_ass else hinh_cuoi
        phan.extend(_loc_chu(lop_phu, duong_chu, hien, ke,
                             cao_khung=cao_khung,
                             cua_so=cua_so_ra_lop_phu(khoang, lop_phu)))
        hien = ke
    if duong_ass:
        from . import lop_phu as _lp

        phan.append(f"[{hien}]ass='{_lp.thoat_duong(duong_ass)}'"
                    f"[{hinh_cuoi}]")
    # ⭐ SAU CUNG TUYET DOI — sau ca phu de. Xem docstring.
    if ve_hinh:
        phan.append(ve_hinh)
    if ve_tieng:
        phan.append(ve_tieng)
    return ";".join(phan)


def loc_toc_do_hinh(bien_tap, nhan_vao: str = "truoc_toc",
                    nhan_ra: str = "ra") -> str:
    """Ve HINH cua toc do: `setpts`. Rong khi ⛔ khong doi toc do.

    ⭐ Sinh doi cua `loc_toc_do_tieng`, va hai ham doc he so tu CUNG mot
       `bien_tap.toc_do` — nen `setpts` va `atempo` ⛔ khong the lech he so.
    """
    from . import bien_tap as _bt

    toc = _bt.toc_do(bien_tap)
    if toc == 1.0:
        return ""
    return f"[{nhan_vao}]setpts=PTS/{toc:.4f}[{nhan_ra}]"


def loc_toc_do_tieng(bien_tap, nhan_vao: str = "1:a", nhan_ra: str = "a_ra") -> str:
    """Ve TIENG cua toc do: `atempo` tren BAN PHOI. Rong khi khong doi toc do.

    ⭐ `atempo` giu cao do, va dung MOT he so voi `setpts` cua hinh — nen T16
       (hinh/tieng dai bang nhau) dung theo cau truc, khong theo may man.
    """
    from . import bien_tap as _bt

    toc = _bt.toc_do(bien_tap)
    if toc == 1.0:
        return ""
    return f"[{nhan_vao}]atempo={toc:.4f}[{nhan_ra}]"


def _loc_diem_anh(bien_tap) -> str:
    """Chuoi loc cua hai phep DIEM ANH, hoac rong.

    ⭐ Tra ve mot chuoi loc chu khong mot ham dung nhan nhu `_loc_khung`: ca hai
       phep deu la mot bo loc mot-vao-mot-ra, khong tach luong, khong can nhan
       trung gian nao.

    ⛔ `hflip` TRUOC `eq`, va thu tu nay co y nghia o mot cho duy nhat — no phai
       **on dinh**. Hai bo loc nay giao hoan (lat roi doi bao hoa = doi bao hoa
       roi lat), nen ket qua khong doi; nhung chuoi loc thi doi, va chuoi loc di
       vao van tay qua `PHIEN_BAN_CHE_DO`. Mot thu tu "tuy luc" se lam hai lan
       chay y het nhau cho hai van tay.

    ⚠️ `:.4f` chu khong `str(float)`: `repr` cua float doi theo phien ban Python
       o mot so gia tri, va mot chuoi lenh doi theo phien ban thong dich la mot
       chuoi lenh khong tai lap duoc.
    """
    from . import bien_tap as _bt

    ho = bien_tap or {}
    ve = []
    if ho.get("lat_guong"):
        ve.append("hflip")
    if ho.get("dich_mau"):
        ve.append(f"eq=saturation={_bt.DICH_MAU_BAO_HOA:.4f}")
    return ",".join(ve)


def _loc_khung(bien_tap, rong: int, cao: int):
    """`hinh_hoc.khung_bien_tap` -> ham `(nhan_vao, nhan_ra) -> [ve filter]`.

    ⛔ So pixel tinh o Python (so nguyen, chan), khong de ffmpeg tinh bang bieu
       thuc: `ban_dung` ghi `khung_ra` tu CHINH ham hinh hoc do, va logo / vien
       chu / `PlayRes` phu de dat theo con so ay. Hai noi tinh la hai con so.
    """
    from . import hinh_hoc as _hh

    try:
        hh = _hh.khung_bien_tap(rong, cao, bien_tap)
    except ValueError as exc:
        raise CheDoError(_t('Chưa biết kích thước khung hình nguồn nên không '
                            'biên tập khung được.')) from exc

    def dung(vao: str, ra: str) -> list[str]:
        chuoi: list[str] = []
        if hh["cat"]:
            w, h, x, y = hh["cat"]
            chuoi.append(f"crop={w}:{h}:{x}:{y}")
        if hh["phong"]:
            chuoi.append(f"scale={hh['phong'][0]}:{hh['phong'][1]}:flags=lanczos")
        kh = hh["khung"]
        if kh and kh["cach"] == "cat":
            w, h, x, y = kh["cat"]
            chuoi.append(f"crop={w}:{h}:{x}:{y}")
        if not (kh and kh["cach"] == "nen_mo"):
            chuoi.append("setsar=1")
            return [f"[{vao}]{','.join(chuoi)}[{ra}]"]
        # Nen mo: ban PHU day khung + lam mo lam nen, ban VUA khung dat giua.
        (nw, nh), (fw, fh), (px, py) = kh["nen"], kh["hinh"], kh["vi_tri"]
        dau = ",".join(chuoi + ["split"]) if chuoi else "split"
        p = chr(92) + ","
        return [f"[{vao}]{dau}[kn][kt]",
                f"[kn]scale={nw}:{nh}:force_original_aspect_ratio=increase,"
                f"crop={nw}:{nh},boxblur=luma_radius=min(w{p}h)/20:luma_power=2[kn2]",
                f"[kt]scale={fw}:{fh}[kt2]",
                f"[kn2][kt2]overlay={px}:{py},setsar=1[{ra}]"]

    return dung


def _anh_xa_cua_so(khoang: list[tuple[float, float]], muc
                   ) -> list[list[tuple[float, float]] | None]:
    """Moc NGUON cua tung muc -> khoang tren BAN RA.

    Ba gia tri tra ve cho moi muc, va ca ba deu khac nhau:

        `None`      muc khong khai gio  -> ap ca video
        `[...]`     khai gio, con cho   -> cac khoang tren ban ra
        `[]`        khai gio, HET cho   -> nguoi goi phai NEM, kem cau cua no

    ⛔ Ham nay khong nem, va do la co y: `vung_che` va `lop_phu` can HAI cau
       tieng Viet khac nhau cho cung mot tinh huong. Mot cau chung chung
       (*"một vùng…"*) hien ra khi khach dat gio cho mot dong CHU la mot cau noi
       ve thu ho khong lam. Cung bai hoc `cat_dau_cuoi.giao` da ghi.

    ⚠️ Dung `BanDoThoiGian(...)` truc tiep chu khong `tu_khoang(...)`: ham lop
       kia **sap xep va gop** dau vao, con `concat` noi theo dung thu tu da
       nhan. Hai cach doc mot danh sach la hai ban do khac nhau, va cho lech se
       khong ai thay cho toi khi mot vung bi che sai cho.
    """
    from .ban_do_thoi_gian import BanDoThoiGian

    ban_do = BanDoThoiGian(tuple((float(b), float(k)) for b, k in khoang),
                           float(khoang[-1][1]))
    ra: list[list[tuple[float, float]] | None] = []
    for v in muc:
        tu, den = v.get("tu_giay"), v.get("den_giay")
        if tu is None and den is None:
            ra.append(None)
            continue
        ra.append(ban_do.ra_khoang(
            float(tu or 0.0),
            float(den) if den is not None else float(khoang[-1][1])))
    return ra


def cua_so_ra(khoang: list[tuple[float, float]], vung
              ) -> list[list[tuple[float, float]] | None]:
    """`_anh_xa_cua_so` cho VUNG CHE. `None` = ap ca video.

    ⛔ Nem khi mot vung CO khai gio ma khong con khoang nao de ap: doan nguon
       ay da bi cat het. Bo qua im lang la giao mot video khong che gi o cho
       khach da ve — va ho chi biet khi xem tep da nhan.
    """
    ra = _anh_xa_cua_so(khoang, vung)
    for cs in ra:
        if cs is not None and not cs:
            raise CheDoError(_t('Một vùng che nằm trọn trong đoạn đã bị cắt bỏ, '
                                'nên không còn chỗ nào để che. Hãy sửa hoặc xoá '
                                'vùng đó.'))
    return ra


def cua_so_ra_lop_phu(khoang: list[tuple[float, float]], lop_phu
                      ) -> list[list[tuple[float, float]] | None]:
    """`_anh_xa_cua_so` cho LOP PHU CHU. `None` = hien suot ca video."""
    ra = _anh_xa_cua_so(khoang, lop_phu)
    for cs in ra:
        if cs is not None and not cs:
            raise CheDoError(_t('Một lớp phủ chữ được đặt giờ nằm trọn trong '
                                'đoạn đã bị cắt bỏ, nên nó sẽ không bao giờ '
                                'hiện ra. Hãy sửa giờ hoặc xoá lớp đó.'))
    return ra


def van_tay_che_do(*, che_do: str, bo_ma_hoa: str,
                   khoang: list[tuple[float, float]], vung=(),
                   lop_phu=(), ds_logo=(), phu_de=None) -> str:
    """Van tay cua quyet dinh render.

    ⛔ Gom CA bo ma hoa: doi tu `libx264` sang `h264_nvenc` cho ra mot tep khac —
       cung noi dung, khac byte — nen dung lai tep cu tu cache la giao mot thu
       khong phai ket qua cua cau hinh hien tai.
    """
    import hashlib

    goi = json.dumps({
        "che_do": che_do,
        "bo": bo_ma_hoa,
        # ⭐ Ho so phu de vao van tay, khong phai duong dan `.ass`. Duong dan la
        #    mot tep tam doi ten moi lan chay; ho so moi la thu quyet dinh KET
        #    QUA. Bam duong dan se lam moi lan chay ra mot van tay khac du cau
        #    hinh y het — tuc pha huy chinh cai cache ma van tay ton tai de mo.
        "phu_de": phu_de or None,
        "tham_so": list(THAM_SO.get(bo_ma_hoa, ())),
        "khoang": [[round(float(b), 4), round(float(k), 4)] for b, k in khoang],
        # 🔴 L4 cua `vung_che`: doi vung ma van tay khong doi la **phuc vu lai
        #    ket qua cu**. Day dung la cai bay ma `cache_artifact.py` cua he
        #    tham chieu goi ten: *"sot tham so = serve nham"*.
        #
        # ⛔ **Va V5 da sot dung mot chieu cua chinh no**: `tu_giay`/`den_giay`
        #    duoc `vung_che` nhan, kiem, luu — roi khong vao day. Hai lan chay
        #    chi khac khoang thoi gian dung chung mot van tay.
        #
        #    ⚠️ No khong bao gio no, vi mot loi THU HAI che no: khoang thoi gian
        #       cung khong duoc `_loc_lam_mo` doc, nen hai ket qua trung nhau
        #       THAT. Sua rieng cai kia se kich hoat cai nay — hai viec mot luot,
        #       va `PHIEN_BAN_CHE_DO` len mot bac.
        #
        # 🔑 Bam moc NGUON chu khong bam khoang da anh xa: khoang ra la HAM cua
        #    (`vung`, `khoang`), va `khoang` da nam ngay tren. Bam ca hai la bam
        #    mot thu hai lan, va lan thu hai se lech khi phep anh xa doi.
        "vung": [[v.get("loai"), round(float(v["y0"]), 4), round(float(v["y1"]), 4),
                  round(float(v["x0"]), 4), round(float(v["x1"]), 4),
                  None if v.get("tu_giay") is None else round(float(v["tu_giay"]), 3),
                  None if v.get("den_giay") is None else round(float(v["den_giay"]), 3)]
                 for v in (vung or ())],
        # 🔴 Cung mot L4, va lan nay khai TU DAU thay vi vá sau.
        #
        #    ⛔ Bam CA `chu`. Doi mot dong chu ma van tay khong doi la giao lai
        #       ban render cu — tuc khach sua chinh ta xong van thay loi chinh
        #       ta cu, va khong co gi noi vi sao.
        #
        #    ⚠️ `duong_chu` (tep tam) **khong** vao day: no la ham cua `chu`, va
        #       duong dan doi theo tung lan chay. Bam no lam moi lan chay ra mot
        #       van tay khac — tuc pha huy cache ma khong ai co y do.
        #
        #    ⚠️ `cao_khung` cung khong: no la thuoc tinh cua NGUON, va nguon da
        #       nam trong van tay ban dung o mot tang khac.
        "lop_phu": [[l.get("chu"), l.get("mau"),
                     round(float(l["x"]), 4), round(float(l["y"]), 4),
                     round(float(l["co_chu"]), 4), round(float(l["do_mo"]), 3),
                     bool(l.get("vien")),
                     None if l.get("tu_giay") is None else round(float(l["tu_giay"]), 3),
                     None if l.get("den_giay") is None else round(float(l["den_giay"]), 3)]
                    for l in (lop_phu or ())],
        # 🔑 Bam `khoa` cua logo, khong bam noi dung anh. Khoa duoc dan xuat tu
        #    van tay cua chinh tep (`assets`), nen hai anh khac nhau khong the
        #    dung chung mot khoa — bam khoa la bam anh, qua mot tang gian tiep
        #    da co bao dam.
        #
        # ⚠️ `rong_khung` KHONG vao day: no la thuoc tinh cua NGUON, va nguon da
        #    nam trong van tay ban dung o mot tang khac. Cung ly do voi
        #    `cao_khung`.
        "logo": [[l.get("khoa"),
                  round(float(l["x"]), 4), round(float(l["y"]), 4),
                  round(float(l["rong"]), 4), round(float(l["do_mo"]), 3),
                  None if l.get("tu_giay") is None else round(float(l["tu_giay"]), 3),
                  None if l.get("den_giay") is None else round(float(l["den_giay"]), 3)]
                 for l in (ds_logo or ())],
        "phien_ban": PHIEN_BAN_CHE_DO,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()[:32]
