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
PHIEN_BAN_CHE_DO = 1

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


def loc_cat_noi(khoang: list[tuple[float, float]]) -> str:
    """`filter_complex` cat cac khoang duoc giu roi noi lai — **khong co tieng**.

    ⛔ Tieng khong di qua day. Ban phoi am (pha 16) da duoc dung theo dung nhung
       khoang nay va da chuan am luong mot lan; cho no di qua `concat` lan nua la
       tron hai quyet dinh am thanh o hai cho, va cai thu hai se thang mot cach
       im lang.
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
    phan.append(f"{nhan}concat=n={len(khoang)}:v=1:a=0[ra]")
    return ";".join(phan)


def van_tay_che_do(*, che_do: str, bo_ma_hoa: str,
                   khoang: list[tuple[float, float]]) -> str:
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
        "phien_ban": PHIEN_BAN_CHE_DO,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()[:32]
