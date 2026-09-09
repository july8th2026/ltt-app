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
PHIEN_BAN_CHE_DO = 3

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


def _loc_lam_mo(vung, nhan_vao: str, nhan_ra: str, cua_so=None) -> list[str]:
    """Cac ve `filter_complex` lam mo tung vung tren mot luong hinh.

    `cua_so[i]` la cac khoang **CUA BAN RA** ma vung `i` duoc bat; `None` hoac
    rong = ap ca video. Doi tuong goi phai anh xa truoc — xem `loc_cat_noi`.

    Cach lam: **cat ra -> lam mo -> dan de len**. Khong dung `boxblur` thang
    tren ca khung roi ghep, vi lam the la giai ma va lam mo TOAN BO khung chi de
    lay lai mot o nho.

    ⚠️ Kich thuoc phai CHAN. `libx264` va `h264_nvenc` deu tu choi chieu le o
       mot so dinh dang pixel (`yuv420p` lay mau 2x2), va thong bao cua ffmpeg
       khi do khong nhac gi toi `crop` — no bao mot loi khoi tao encoder. Nen
       `trunc(.../2)*2` o day khong phai lam dep, no la dieu kien de lenh chay.

    ⚠️ Va `x`/`y` cung phai chan, cung ly do lay mau.
    """
    # ⛔ Khong mac dinh im lang: mot lan goi quen `cua_so` phai cho ra "ap ca
    #    video" mot cach TUONG MINH, khong phai vi mot `.get()` tra `None`.
    ds_cua_so = list(cua_so) if cua_so is not None else [None] * len(vung)
    if len(ds_cua_so) != len(vung):
        raise CheDoError(_t('Không dựng được vùng che cho lần chạy này.'))

    ve: list[str] = []
    hien = nhan_vao
    for i, v in enumerate(vung):
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
        ve.append(f"[{hien}]split[c{i}][g{i}]")
        ve.append(f"[c{i}]crop={w}:{h}:{x_crop}:{y_crop},"
                  f"boxblur=luma_radius={r}:luma_power=2[m{i}]")
        ke = f"o{i}" if i + 1 < len(vung) else nhan_ra
        ve.append(f"[g{i}][m{i}]overlay={x}:{y}{_bat_khi(ds_cua_so[i])}[{ke}]")
        hien = ke
    return ve


def loc_cat_noi(khoang: list[tuple[float, float]], vung=()) -> str:
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
    if vung:
        phan.append(f"{nhan}concat=n={len(khoang)}:v=1:a=0[noi]")
        phan.extend(_loc_lam_mo(vung, "noi", "ra", cua_so_ra(khoang, vung)))
    else:
        phan.append(f"{nhan}concat=n={len(khoang)}:v=1:a=0[ra]")
    return ";".join(phan)


def cua_so_ra(khoang: list[tuple[float, float]], vung
              ) -> list[list[tuple[float, float]] | None]:
    """Moc NGUON cua tung vung -> khoang tren BAN RA. `None` = ap ca video.

    ⛔ Nem khi mot vung CO khai gio ma khong con khoang nao de ap: doan nguon
       ay da bi cat het. Bo qua im lang la giao mot video khong che gi o cho
       khach da ve — va ho chi biet khi xem tep da nhan.

    ⚠️ Dung `BanDoThoiGian(...)` truc tiep chu khong `tu_khoang(...)`: ham lop
       kia **sap xep va gop** dau vao, con `concat` o tren noi theo dung thu tu
       da nhan. Hai cach doc mot danh sach la hai ban do khac nhau, va cho lech
       se khong ai thay cho toi khi mot vung bi che sai cho.
    """
    from .ban_do_thoi_gian import BanDoThoiGian

    ban_do = BanDoThoiGian(tuple((float(b), float(k)) for b, k in khoang),
                           float(khoang[-1][1]))
    ra: list[list[tuple[float, float]] | None] = []
    for v in vung:
        tu, den = v.get("tu_giay"), v.get("den_giay")
        if tu is None and den is None:
            ra.append(None)
            continue
        cs = ban_do.ra_khoang(float(tu or 0.0),
                              float(den) if den is not None else float(khoang[-1][1]))
        if not cs:
            raise CheDoError(_t('Một vùng che nằm trọn trong đoạn đã bị cắt bỏ, '
                                'nên không còn chỗ nào để che. Hãy sửa hoặc xoá '
                                'vùng đó.'))
        ra.append(cs)
    return ra


def van_tay_che_do(*, che_do: str, bo_ma_hoa: str,
                   khoang: list[tuple[float, float]], vung=()) -> str:
    """Van tay cua quyet dinh render.

    ⛔ Gom CA bo ma hoa: doi tu `libx264` sang `h264_nvenc` cho ra mot tep khac —
       cung noi dung, khac byte — nen dung lai tep cu tu cache la giao mot thu
       khong phai ket qua cua cau hinh hien tai.
    """
    import hashlib

    goi = json.dumps({
        "che_do": che_do,
        "bo": bo_ma_hoa,
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
        "phien_ban": PHIEN_BAN_CHE_DO,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()[:32]
