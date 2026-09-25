"""DO VUNG — tu do LOGO TINH (V4a) va DAI CHU goc (V4b) bang OpenCV thuan.

# ══════════════════════════════════════════════════════════════════════════════
#  🔴 ĐOC KHOI NAY TRUOC KHI NOI TEP NAY VAO BAT CU DAU — chot 25/09/2026
# ══════════════════════════════════════════════════════════════════════════════

## 1. Tep nay thuoc **GIAI ĐOAN 2**, ⛔ khong phai giai doan hien tai

Chu du an chot tach duong chay lam hai giai doan:

    GIAI ĐOAN 1  tieng : demucs -> ASR -> dich -> TTS -> nan -> tron -> render
                 RA   : MP4 tieng Viet khop hinh, TOAN BO do dai goc
                        (⛔ khong cat gi)
    GIAI ĐOAN 2  hinh : THAO TAC TREN MP4 ĐA XONG —
                        cat canh · logo · watermark · phu de · lat guong ·
                        dich mau · zoom

🔑 **Do vung va dien nen (`vung_che.LOAI_DIEN_NEN`) thuoc GIAI ĐOAN 2.**
⛔ Nen tep nay chay tren **MP4 da hoan thien tieng**, ⛔ khong phai tren tep
NGUON cua khach. ⛔ Đung noi no vao `media_prepare` hay bat cu chang nao cua giai
doan 1 — do la lap vao mot khung sap duoc xep lai.

## 2. 🔴 Noi dang **GOI Y**, ⛔ KHONG tu dong che

⛔ Ket qua o day ⛔ **khong bao gio** duoc ghi thang thanh vung che.

⭐ Ly do la **so do cua chinh tep nay**, nghiem thu 25/09 tren hai phim that:

| | do duoc |
|---|---|
| `phim1` (dai phu de tren nen canh) | dung khit |
| `phim2` (game co HUD) | dai **rong du ~8 % chieu cao khung** — no trum ca hang bang ten HUD |
| tang khung 18 -> 24 -> 36 -> 48 | ⛔ **KHONG** siet lai (15,4–17,7 %) |

⇒ V4b ⛔ **khong phan biet duoc** dai phu de voi bang ten HUD: **ca hai** deu la
*chu trang vien den, doi theo thoi gian* — dung tin hieu V4b di tim. Va vi tang
khung ⛔ khong giup, day la **gioi han cua PHUONG PHAP**, ⛔ khong phai mot nguong
can tinh chinh.

🔴 ⇒ Tu dong che se **boi mo HUD tren video cua khach**, sau khi ta **da thu
tien**. ⭐ **Do SAI nguy hon ⛔ KHONG do:** ⛔ khong do ⇒ khach tu khoanh, mat
cong; do sai ⇒ khach nhan ve mot video **bi hong**.

⚠️ Va chinh meo dau trang cua he tham chieu noi dung dieu do: *"nen khoanh vung
   phu de bang tay — tool khoi mat cong do, render nhanh hon, dai che can khit
   hon"*. Ho **co** bo do, va ho **van** khuyen khoanh tay.

## 3. Luong ĐUNG

    do_vung.de_xuat(mp4_da_xong_tieng)  ->  ĐE XUAT (3 trang thai)
      -> giao dien hien KHUNG ĐO
        -> khach BAM NHAN hoac KEO SUA
          -> luc do moi thanh mot `vung_che` THAT

⛔ ⛔ Khong buoc nao trong chuoi tren duoc bo qua.

## 4. ⛔ ĐO ≠ KIEM

`do_vung` la lop **ĐO**; `vung_che` la lop **KIEM**. ⛔ Đung de mot phep do tu
thang cap thanh mot quyet dinh. Đo cung la ly do tep nay ⛔ **khong bao gio** tu
dat `loai` cho mot hop (xem muc duoi).

# ══════════════════════════════════════════════════════════════════════════════

## 🔴 Mot module RIENG, va do la mot ranh gioi co y

`vung_che.py` la lop **KIEM**: mot hop toa do khach ve, kiem xong thi tu choi
hay nhan. Tep nay la lop **DO**: mot video vao, mot phan quyet *"o day co gi"*
ra. Tron hai lop la giau mot QUYET DINH DO ben trong mot phep KIEM — va lop kiem
se im lang nhan lay ket qua cua mot bo do khong ai nhin thay.

⇒ Tep nay **khong** bao gio tu dat `loai` cho hop. Che bang o mo hay bang dien
  nen la CHINH SACH, va chinh sach thuoc ve nguoi goi.

## Thuat toan chep tu `D:\\Viral` (kho cua chu du an, CHI DOC)

| | nguon | tin hieu |
|---|---|---|
| **V4a** logo tinh | `dai_watermark.py:44 _phat_hien` | PHUONG SAI THEO THOI GIAN thap (logo duc che kin nen diem anh gan nhu khong doi) **giao** cong bien Laplacian (phai co NET do hoa), **chi** o vung goc/mep |
| **V4b** dai chu | `dai_sub.py:69 phat_hien_dai` + `:188 _om_sat_vien` | nang luong bien theo HANG, manh VA bien dong theo thoi gian (= chu doi tung cau), roi bo Y ve dung net chu |

⭐ **0 model, 0 GPU, 0 VRAM** — chi `cv2` + `numpy`. Do that (Đ1,
`docs/auto_scan_video_final/L_DO_VUNG.md` §0): V4a **+0,3–0,5 %**, V4b
**+0,5–0,8 %** so voi nen 115 s cua phan viec cuc bo.

## 🔴 BAT BIEN 1 — "khong co gi o do" ≠ "khong do duoc"

Bo do cua Viral tra `[]` cho **ca hai** ca (`dai_watermark.py:50`, `:145`). Do la
mot bo do **mat kha nang phan biet**, va cai mat khong bao loi — no chi khong ton
tai. Bai hoc `hai-trang-thai-gop-thanh-mot-gia-tri` trong so cua ta.

⇒ O day:

    khong doc duoc video / qua it khung  ->  nem `DoVungLoi`   (KHONG do duoc)
    quet that, khong thay gi             ->  `KetQua(vung=(), ...)`  (KHONG co gi)

`KetQua.so_khung` noi ra da doc duoc bao nhieu khung, nen mot ket qua rong van
chung minh duoc rang chang do da chay thuc su.

## 🔴 BAT BIEN 2 — vung khach TU VE thang vung tu do

`dai_sub.py:175 _trung_vung_tay` **loai** dai tu do nao chong >= 50 % chieu cao
cua no len vung khach da ve. Ta giu dung the: `tranh` cua `do_dai_chu`.

⚠️ Va ⛔ **dung** vi co V4b ma doi nghia `vung_che.LOAI_DANH_DAU_PHU_DE` thanh
   *"che dai sub goc"*. Hai khai niem, hai truong: cai kia mang nghia AM (*dung
   ve phu de dich o day*), cai nay la mot vung se bi che.

## ⚠️ BAT BIEN 3 — ⛔ dung tiec khung, va ⛔ dung tinh chinh nguong

Đ1 §4.1 do dan hoi theo so khung: **0,179 giay CPU va 0,033 s tuong MOI KHUNG**.
Ke ca 48 khung van chi 1,7 % cua nen 115 s. ⇒ Ket qua run ray thi **tang khung**;
cac nguong duoi day la so Viral da tra gia de hoc, ⛔ dung go lai bang tay.

## ⚠️ V4c — LOGO DI CHUYEN: ⛔ KHONG ho tro, va day la hai ly do — chot ke hoach

`docs/superpowers/plans/2026-09-25-asv-hai-giai-doan.md` chot V4c la
**"C — khong lay"**, hai ly do DOC LAP (⛔ dung lat lai chi vi mot trong hai
nghe yeu hon o lan doc sau):

1. **Chi phi 5–10×** so voi V4a/V4b — bam theo mot logo doi vi tri qua tung
   khung doi hoi mot bo theo doi (tracker) rieng, ⛔ khong con la "OpenCV thuan,
   0 model" nhu hai bo tren.
2. 🔴 **No ⛔ khong phai mot bo TU DO** — thuat toan tham chieu cua Viral doi
   khach **KHOANH O TRUOC** roi moi bam THEO o do qua cac khung; ⭐ Viral **tu
   thu va tu loai** huong nay. Tuc du co lam, day van ⛔ khong phai "V4a nhung
   theo doi duoc vi tri" — no la mot tinh nang KHAC (theo doi mot vung khach da
   chi), va lop giao dien "de xuat -> khach nhan/keo/bo" cua tep nay khong co
   cho cho no.

⭐ **Da DO, ⛔ khong doan**: `do_logo_tinh` TU AN TOAN voi logo di chuyen, va do
la mot he qua TRUC TIEP cua chinh cong `NGUONG_STD` no da co — ⛔ khong phai
mot co che moi. Do tren clip tong hop (logo TRUOT ngang lien tuc qua 6 giay,
cung nen dong nhu `test_4301`):

    | clip                | `do_logo_tinh` tra ve      |
    |----------------------|----------------------------|
    | logo TINH (doi chung)| MOT hop, dung goc `tr`      |
    | logo DI CHUYEN        | **RONG** (`vung=()`)       |

Ly do bang so: `std` (phuong sai theo truc THOI GIAN, xem V4a o tren) do TAI
TUNG O LUOI CO DINH cua grid da ha (`BE_RONG_LOGO`). Logo di chuyen nghia la
mot o luoi cho no CHI che mot phan thoi gian — pixel o do doi giua "co logo"
va "nen dong phia sau" qua cac khung, nen `std` TANG VOT qua truc **cung** truc
ma logo tinh giu THAP. Cong `std < NGUONG_STD` (8,0) — vi do CHINH la dinh
nghia cua "logo", khong phai mot ngoai le rieng cho ca nay — tu loai no truoc
khi toi duoc cac cong con lai (Laplacian, vi tri, dien tich). Phep kiem:
`tests/test_4803_asv_v4c_logo_dong_khong_ho_tro.py`.

⚠️ **Ket qua tren la RONG (`khong_co` neu di qua `de_xuat()`), ⛔ khong phai
`khong_do_duoc`.** Dung lam ro: rong o day nghia la *"bo do CHAY THAT ma
khong thay gi"* — dung hanh vi BAT BIEN 1 mo ta o tren, ⛔ khong phai mot
ngoai le rieng cho logo dong. `de_xuat()` ⛔ khong can mot nhanh rieng de "chan"
V4c: no ⛔ chua bao gio hop lai duoc mot hop cho ca nay.

⛔ **Va do la MOT DIEM DO, ⛔ khong phai mot lo hong da vieng kin.** Nguong 8,0
   la hang so Viral da tra gia de hoc (BAT BIEN 3 o duoi) — mot logo di chuyen
   RAT CHAM (vai pixel/giay) van co the giu `std` duoi nguong o mot vai o luoi
   bien, va khi do V4a se bao mot hop TINH cho mot vi tri **chi dung trong mot
   phan thoi gian**. `de_xuat()` ⛔ khong phat hien duoc ca do — day chinh la
   ly do man hinh la mot ĐE XUAT khach phai nhin va nhan/bo, ⛔ khong bao gio
   tu dong che (xem muc 2 o duoi).

## ⛔ Vi sao KHONG dung lai khung `canh.rut_khung` da trich

Đ1 §9: `canh` cho ra JPEG chat luong 4 **da ha ve canh dai 512**, lay tai **giua
moi canh** (khong cach deu theo thoi gian). V4a do `std` theo truc THOI GIAN nen
doi luoi cach deu; ca V4a va V4b dat nguong tren Laplacian va tren `g>190`/
`g<70` — dung cai dai luong ma JPEG chat luong 4 them/bot. Tien tiet kiem la
duoi mot giay. ⇒ Doc khung RIENG.
"""
from __future__ import annotations

import os
from typing import NamedTuple

from platform_core.i18n import _ as _t

# ── V4a — logo/watermark TINH ────────────────────────────────────────────────

#: So khung lay mau, CACH DEU theo thoi gian. `dai_watermark.py:26`.
SO_KHUNG_LOGO = 16

#: Be rong chuan hoa de tinh (giu ti le). Moi phep cua V4a chay o day, va do la
#: ly do V4a re nhat trong ca ho.
BE_RONG_LOGO = 360

#: `std` theo truc THOI GIAN duoi nguong nay = diem anh gan nhu KHONG doi = logo
#: DUC che kin nen. Watermark MO de lo nen phia sau thi bien thien -> LOAI.
NGUONG_STD = 8.0

#: Cong BIEN: `abs(Laplacian(mean, ksize=3))` tren nguong nay = co NET do hoa.
#: ⛔ Thieu cong nay thi mang phang (troi, tuong) cung `std` thap va se bi nhan
#:    la logo.
NGUONG_NET = 26

#: Kich thuoc `MORPH_CLOSE` — noi cac net gan nhau thanh mot khoi.
O_NOI_NET = (9, 9)

#: Dien tich khoi / dien tich khung. Qua nho = nhieu; qua to = mang canh.
DIEN_TICH_MIN, DIEN_TICH_MAX = 0.0009, 0.06

#: Khoi rong hon ti le nay cua be rong = vien / letterbox / dai, khong phai logo.
TRAN_BE_RONG = 0.55

#: Do DAC (`dien tich / (w*h)`). Logo la mot khoi dac, khong roi rac.
DO_DAC_MIN = 0.35

#: Ti le diem anh CO NET trong khoi. Net thua = troi / tuong / san gach.
MAT_DO_NET_MIN = 0.09

#: Dem quanh hop, theo phan so.
DEM_X_LOGO, DEM_Y_LOGO = 0.015, 0.012

#: Hop nho hon the nay (px cua khung GOC) thi bo.
CANH_PX_MIN = 8

#: Vung DUOC PHEP tim logo, theo phan so. ⛔ KHONG co phan giua.
#:
#: 🔴 Day la bo loc dat gia nhat cua V4a. Do that cua Viral: tieu de noi dung
#:    ("小时候", "刀") nam top-GIUA, dung yen nhung DOI CHU — no di qua ca hai
#:    cong std va Laplacian. Chi co VI TRI tach duoc no khoi watermark.
MEP_NGANG = 0.18      # dai mep trai + phai, full chieu cao
MEP_TREN = 0.14       # bien tren
MEP_DUOI = 0.86       # bien duoi (tu day tro xuong)
BE_GOC = 0.28         # be rong "goc" tren/duoi — ne phan giua

# ── V4b — dai chu goc ────────────────────────────────────────────────────────

#: So khung lay mau cho V4b, trong khoang 10–90 % do dai (bo intro/outro).
SO_KHUNG_DAI = 18
BO_DAU_CUOI = (0.10, 0.90)

#: Be rong chuan hoa cho tang do dai.
BE_RONG_DAI = 480

#: Chi tim o NUA DUOI (45–100 %). Do that cua Viral: quet ca man chon nham logo
#: header, chu sub day lo ra. Sub goc o TREN la ca hiem.
VUNG_TIM_DAI = (0.45, 1.00)

#: Moc dai: `score >= max(SAN_NGUONG, peak * TI_LE_DINH)`.
SAN_NGUONG, TI_LE_DINH = 0.18, 0.45

#: Dem moi dau truoc khi kiem tin cay.
DEM_DAI = 0.015

#: Tin cay: dinh du ro VA dai hop ly. Tran 0,20 chu khong 0,30 — dai RONG hon
#: 20 % chieu cao la noi-dung-doi khuech tan (video KHONG co sub), khong phai mot
#: hang chu.
DINH_MIN = 0.22
CAO_MIN, CAO_MAX = 0.03, 0.20

#: Bu them MOI DAU **sau** khi da kiem tin cay (de khong lam lech nguong tren).
#:
#: 🔴 Vi sao can: tang OpenCV chi bat phan THAN chu co bien manh, nen dai no tra
#:    ve HEP HON dai that. Do cua Viral tren cung mot video H=1280: RapidOCR
#:    73,5–82,1 % · OpenCV 74,9–80,7 % => hut ~1,4 % moi dau = ~18 px => DINH va
#:    CHAN chu Han van lo ra ngoai vung che.
BU_MOI_DAU = 0.015

#: Dai tu do chong >= ti le nay len mot vung khach TU VE thi bi LOAI.
TRUNG_VUNG_TAY = 0.5

# ── V4b, chang hai: om sat vien chu ──────────────────────────────────────────

#: So khung cho `om_sat_vien`. Doc o be rong GOC (khong ha), nen chang nay la
#: phan dat cua V4b — Đ1 §4.2: V4b ~1,9x V4a chinh vi no.
SO_KHUNG_VIEN = 12

#: Net chu outline = TRANG co VIEN DEN ke ben. ⛔ KHAC diem-anh-sang-tho: nen
#: troi / nuoc sang KHONG co vien den nen bo qua duoc.
NGUONG_TRANG, NGUONG_DEN = 190, 70
O_NO_DEN = (1, 9)

#: Quet trong dai OCR +- chut, de khong bat chu NGOAI dai (watermark, ten kenh).
NOI_QUET_TREN, NOI_QUET_DUOI = 0.04, 0.01

#: Nguong THICH NGHI cho mat do net theo hang: `max(W*SAN, dinh*TI_LE)`.
#:
#: ⚠️ Nguong cung 0,015 mot minh bat CA nhieu ao/toc/nen nhan vat lot vao dai
#:    quet (do that: nhieu <= 19 px/hang, chu 51–189 px/hang). Lay 20 % dinh de
#:    cat dung VUC NGAN; giu san cho sub mo tren nen SACH.
SAN_MAT_DO, TI_LE_DINH_VIEN = 0.015, 0.20

#: Dem chong cat chan chu / outline, theo phan so chieu cao khung.
DEM_VIEN = 0.0075

#: Chieu cao toi thieu (px) cua dai sau khi om sat.
CAO_PX_MIN = 10


class DoVungLoi(RuntimeError):
    """⛔ KHONG DO DUOC — loi ky thuat, ⛔ khong phai "khong co gi o do".

    Xem BAT BIEN 1 o dau tep. Thong bao LA cau tieng Viet cho khach doc.
    """


class KetQua(NamedTuple):
    """Ket qua mot luot do.

    `vung` rong **cong** `so_khung > 0` = *da quet that, khong thay gi*. Ca
    *khong do duoc* ⛔ khong bao gio den bang duong nay — no nem `DoVungLoi`.
    """

    #: Hop toa do PHAN SO 0..1 (`vung_che` L1). `goc` chi co o V4a.
    vung: tuple[dict, ...]
    #: So khung doc duoc that. Bang chung rang chang do da chay.
    so_khung: int


def _cv2():
    """`cv2` + `numpy`, hay `DoVungLoi`. ⛔ KHONG tra rong khi thieu goi.

    ⚠️ Viral tra `[]` o day (`dai_watermark.py:50`) — tuc "may khong co OpenCV"
       va "video nay khong co logo" cho ra cung mot cau tra loi. Xem BAT BIEN 1.
    """
    try:
        import cv2
        import numpy
    except ImportError as e:
        raise DoVungLoi(
            _t('Máy chưa có OpenCV nên không dò được vùng cần che.')) from e
    return cv2, numpy


def _mo(cv2, duong: str):
    """Mo video, tra `(cap, W, H, so_khung, giay)`. Nem khi khong doc duoc."""
    cap = cv2.VideoCapture(os.path.abspath(duong))
    if not cap.isOpened():
        raise DoVungLoi(_t('Không mở được tệp video để dò vùng cần che.'))
    rong = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cao = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tong = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if rong <= 0 or cao <= 0 or tong <= 0:
        cap.release()
        raise DoVungLoi(
            _t('Tệp video không khai kích thước hoặc số khung nên không dò '
               'được vùng cần che.'))
    return cap, rong, cao, tong, (tong / fps if fps > 0 else 0.0)


def _du_khung(doc: int, can: int) -> None:
    """Đoc du khung chua. Thieu => KHONG DO DUOC, ⛔ khong phai "khong co gi"."""
    if doc < max(4, can // 3):
        raise DoVungLoi(
            _t('Chỉ đọc được {co} trên {can} khung nên chưa đủ để dò vùng cần '
               'che.').format(co=doc, can=can))


def do_logo_tinh(duong: str, *, so_khung: int = SO_KHUNG_LOGO) -> KetQua:
    """**V4a** — logo/watermark TINH o goc/mep. Chep `dai_watermark.py:44`.

    Tin hieu: logo DUC che kin nen => diem anh gan nhu khong doi qua thoi gian
    (`std` thap) **va** co net do hoa (Laplacian cao) **va** nam o goc/mep.

    ⛔ Ba dieu kien deu can. Bo `std` thi bat moi thu co net; bo Laplacian thi
       bat mang troi/tuong; bo vi tri thi bat THE TIEU DE — ca Viral da dinh.

    Nem `DoVungLoi` khi khong mo duoc video / khong doc du khung.
    """
    cv2, np = _cv2()
    cap, rong, cao, tong, _ = _mo(cv2, duong)
    try:
        gw = BE_RONG_LOGO
        gh = max(2, int(round(cao * gw / rong)))
        khung = []
        for k in range(so_khung):
            # Lay CACH DEU theo thoi gian: `std` do tren truc thoi gian nen mot
            # luoi khong deu se do mot canh dai sang mot canh ngan.
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(tong * (k + 0.5) / so_khung))
            duoc, fr = cap.read()
            if not duoc or fr is None:
                continue
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            khung.append(cv2.resize(g, (gw, gh)).astype(np.float32))
    finally:
        cap.release()
    _du_khung(len(khung), so_khung)

    chong = np.stack(khung)
    std = chong.std(axis=0)
    tb = chong.mean(axis=0).astype(np.uint8)
    co_net = np.abs(cv2.Laplacian(tb, cv2.CV_32F, ksize=3)) > NGUONG_NET
    mat_na = (std < NGUONG_STD).astype(np.uint8)
    mat_na = cv2.bitwise_and(mat_na, _vung_cho_phep(np, gw, gh))
    mat_na = cv2.morphologyEx(
        mat_na, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, O_NOI_NET))

    so_nhan, nhan, thong_ke, _ = cv2.connectedComponentsWithStats(
        mat_na, connectivity=8)
    tong_diem = float(gw * gh)
    ra: list[dict] = []
    for i in range(1, so_nhan):
        x, y, w, h, dien = thong_ke[i]
        if not DIEN_TICH_MIN <= dien / tong_diem <= DIEN_TICH_MAX:
            continue
        if w > gw * TRAN_BE_RONG:
            continue
        if dien / float(max(1, w * h)) < DO_DAC_MIN:
            continue
        if float(co_net[nhan == i].mean()) < MAT_DO_NET_MIN:
            continue
        # ⚠️ `float()` tuong minh: `stats` la mang numpy nen mot phep chia cho ra
        #    `np.float64`. No tinh dung, nhung `json.dumps` cua van tay
        #    (`che_do_render.van_tay_che_do`) **khong** tuan tu hoa duoc no —
        #    tuc mot vung tu do se lam chet chinh cai ham giu cache.
        x0 = float(max(0.0, x / gw - DEM_X_LOGO))
        y0 = float(max(0.0, y / gh - DEM_Y_LOGO))
        x1 = float(min(1.0, (x + w) / gw + DEM_X_LOGO))
        y1 = float(min(1.0, (y + h) / gh + DEM_Y_LOGO))
        if (x1 - x0) * rong < CANH_PX_MIN or (y1 - y0) * cao < CANH_PX_MIN:
            continue
        ra.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1,
                   "goc": _goc((x0 + x1) / 2, (y0 + y1) / 2)})
    return KetQua(vung=tuple(ra), so_khung=len(khung))


def _goc(xt: float, yt: float) -> str:
    """Ten goc chua tam hop: `tl` `tr` `bl` `br`. Chi de doc log / dat ten anh."""
    return ("b" if yt >= 0.5 else "t") + ("r" if xt >= 0.5 else "l")


def _vung_cho_phep(np, gw: int, gh: int):
    """Mat na 0/1 cua vung DUOC PHEP tim logo. Xem `MEP_NGANG` o tren."""
    z = np.zeros((gh, gw), np.uint8)
    mx = int(gw * MEP_NGANG)
    tren = int(gh * MEP_TREN)
    duoi = int(gh * MEP_DUOI)
    goc = int(gw * BE_GOC)
    z[:, :mx] = 1
    z[:, gw - mx:] = 1
    z[:tren, :goc] = 1
    z[:tren, gw - goc:] = 1
    z[duoi:, :goc] = 1
    z[duoi:, gw - goc:] = 1
    return z


def do_dai_chu(duong: str, *, so_khung: int = SO_KHUNG_DAI,
               tranh=()) -> KetQua:
    """**V4b** — dai chu goc (hardsub). Chep `dai_sub.py:69` + `:188`.

    Tin hieu: nang luong bien theo HANG **manh** (co chu) **va bien dong theo
    thoi gian** (chu DOI tung cau). Watermark tinh manh nhung khong bien dong =>
    tu bi loai boi ve `std`. Do la doi xung cua V4a, va la ly do hai bo do nay
    ⛔ khong the gop thanh mot.

    `tranh` = cac cap `(y0, y1)` phan so cua vung khach TU VE. Dai tu do chong
    >= `TRUNG_VUNG_TAY` len mot trong do thi bi LOAI — xem BAT BIEN 2.

    Tra `KetQua(vung=(), ...)` khi da quet that ma khong chac co dai chu nao.
    Nem `DoVungLoi` khi khong mo duoc video / khong doc du khung.
    """
    cv2, np = _cv2()
    cap, rong, cao, tong, giay = _mo(cv2, duong)
    try:
        if giay <= 0:
            raise DoVungLoi(
                _t('Tệp video không khai độ dài nên không dò được dải chữ gốc.'))
        t0, t1 = giay * BO_DAU_CUOI[0], giay * BO_DAU_CUOI[1]
        hang = []
        for i in range(so_khung):
            cap.set(cv2.CAP_PROP_POS_MSEC,
                    (t0 + (t1 - t0) * i / max(1, so_khung - 1)) * 1000.0)
            duoc, fr = cap.read()
            if not duoc or fr is None:
                continue
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            gh = max(2, int(round(g.shape[0] * float(BE_RONG_DAI)
                                  / max(1, g.shape[1]))))
            g = cv2.resize(g, (BE_RONG_DAI, gh))
            hang.append(np.abs(cv2.Laplacian(g, cv2.CV_32F, ksize=3)
                               ).sum(axis=1))
    finally:
        cap.release()
    _du_khung(len(hang), so_khung)

    # Chieu cao co the lech 1 px giua cac khung — cat ve cai ngan nhat.
    thap = min(len(r) for r in hang)
    M = np.array([r[:thap] for r in hang])
    h = M.shape[1]

    def chuan(a):
        a = a - a.min()
        return a / (a.max() + 1e-6)

    # 🔑 `mean` MOT MINH bat ca watermark tinh; `std` MOT MINH bat ca canh dong.
    #    NHAN hai cai lai = "manh VA doi" = chu chay.
    diem = chuan(M.mean(axis=0)) * chuan(M.std(axis=0))
    dinh, y0, y1 = _dai_manh_nhat(np, diem, h)
    dem = int(h * DEM_DAI)
    y0f = max(0.0, (y0 - dem) / h)
    y1f = min(1.0, (y1 + dem) / h)
    # ⚠️ Kiem tin cay TREN chieu cao CHUA bu — `BU_MOI_DAU` ap sau, de khong lam
    #    lech nguong `CAO_MIN..CAO_MAX` von duoc do o ban khong bu.
    if dinh < DINH_MIN or not CAO_MIN <= (y1f - y0f) <= CAO_MAX:
        return KetQua(vung=(), so_khung=len(hang))
    y0f = max(0.0, y0f - BU_MOI_DAU)
    y1f = min(1.0, y1f + BU_MOI_DAU)
    y0f, y1f = _om_sat_vien(cv2, np, duong, y0f, y1f)
    if _trung_vung_tay(y0f, y1f, tranh):
        return KetQua(vung=(), so_khung=len(hang))
    # `float()` tuong minh — cung ly do voi `do_logo_tinh`: `numpy` ro ri vao van
    # tay se lam chet `json.dumps`.
    return KetQua(vung=({"x0": 0.0, "y0": float(y0f),
                         "x1": 1.0, "y1": float(y1f)},),
                  so_khung=len(hang))


def _dai_manh_nhat(np, diem, h: int) -> tuple[float, int, int]:
    """Moc dai chu manh nhat trong `VUNG_TIM_DAI` -> `(dinh, y0, y1)` theo hang."""
    lo = int(h * VUNG_TIM_DAI[0])
    hi = min(h, int(round(h * VUNG_TIM_DAI[1])))
    vung = diem.copy()
    vung[:lo] = 0
    if hi < h:
        vung[hi:] = 0
    dinh = float(vung.max())
    pk = int(vung.argmax())
    bat = vung >= max(SAN_NGUONG, dinh * TI_LE_DINH)
    y0 = pk
    while y0 > lo and bat[y0 - 1]:
        y0 -= 1
    y1 = pk
    while y1 < min(h - 1, hi - 1) and bat[y1 + 1]:
        y1 += 1
    return dinh, y0, y1


def _trung_vung_tay(y0: float, y1: float, tranh) -> bool:
    """Dai tu do co chong nhieu len mot vung khach TU VE khong. BAT BIEN 2."""
    cao = max(1e-6, y1 - y0)
    for ay0, ay1 in (tranh or ()):
        chong = max(0.0, min(y1, float(ay1)) - max(y0, float(ay0)))
        if chong / cao >= TRUNG_VUNG_TAY:
            return True
    return False


def _om_sat_vien(cv2, np, duong: str, y0f: float, y1f: float
                 ) -> tuple[float, float]:
    """Bo Y ve dung NET CHU (trang co vien den ke). Chep `dai_sub.py:188`.

    ⭐ Vi sao can: dai o chang truoc la mot HOP, va mot hop dung cho sub 2 dong
       thi qua cao cho sub 1 dong (do that cua Viral: hop 154 px cho chu 73 px).
       Om sat lam chinh xac ca hai chieu — tu CO khi hop qua to, tu NOI khi hut.

    ⚠️ Chang nay doc o be rong GOC (khong ha 480): `g>190` va `g<70` la nguong
       DIEM ANH TUYET DOI, va mot lan `resize` doi chinh cai dai luong do.

    ⛔ Khong tim thay net-vien thi GIU dai cu — day ⛔ khong phai mot duong lui
       im lang: dai cu da qua cong tin cay, va bai nay chi SIET no lai.
    """
    cap, rong, cao, tong, _ = _mo(cv2, duong)
    try:
        z0 = max(0, int((y0f - NOI_QUET_TREN) * cao))
        z1 = min(cao, int((y1f + NOI_QUET_DUOI) * cao))
        if z1 - z0 < CANH_PX_MIN:
            return y0f, y1f
        mat_do = np.zeros(cao, np.float32)
        doc = 0
        for k in range(SO_KHUNG_VIEN):
            cap.set(cv2.CAP_PROP_POS_FRAMES,
                    int(tong * (k + 0.5) / SO_KHUNG_VIEN))
            duoc, fr = cap.read()
            if not duoc or fr is None:
                continue
            doc += 1
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            trang = g > NGUONG_TRANG
            den = cv2.dilate((g < NGUONG_DEN).astype(np.uint8),
                             np.ones(O_NO_DEN, np.uint8)) > 0
            # HOP qua cac khung: chu o dau cung phu, vi moi cau nam mot cho.
            mat_do = np.maximum(
                mat_do, (trang & den).sum(axis=1).astype(np.float32))
    finally:
        cap.release()
    if doc < 3:
        return y0f, y1f
    dinh = float(mat_do[z0:z1].max()) if z1 > z0 else 0.0
    hang = np.where(mat_do[z0:z1]
                    >= max(rong * SAN_MAT_DO, dinh * TI_LE_DINH_VIEN))[0]
    if len(hang) == 0:
        return y0f, y1f
    dem = int(cao * DEM_VIEN)
    n0 = max(0, z0 + int(hang[0]) - dem)
    n1 = min(cao, z0 + int(hang[-1]) + dem)
    if n1 - n0 < CAO_PX_MIN:
        return y0f, y1f
    return n0 / cao, n1 / cao


# ══════════════════════════════════════════════════════════════════════════════
#  ĐE XUAT — be mat DUY NHAT ma GIAI ĐOAN 2 duoc goi
# ══════════════════════════════════════════════════════════════════════════════

#: Ba trang thai cua mot de xuat. ⛔ KHONG duoc gop lai thanh hai.
#:
#: 🔴 `khong_do_duoc` ≠ `khong_co`. Gop chung lai thi mot may hong codec se bao
#:    cao *"video nay sach"* — va ⛔ khong ai biet. Xem BAT BIEN 1 o dau tep.
TRANG_THAI_CO = "co"
TRANG_THAI_KHONG_CO = "khong_co"
TRANG_THAI_KHONG_DO_DUOC = "khong_do_duoc"

#: Chang nao de xuat ra hop nay. Khach phai biet: mot logo goc va mot dai chu
#: duoc xu ly KHAC nhau (che kin vs dien nen), va ⛔ khong ai doan giup ho.
NGUON_LOGO = "logo_tinh"
NGUON_DAI = "dai_chu"


def de_xuat(duong: str, *, tranh=()) -> dict:
    """Mot **ĐE XUAT** cho khach xac nhan. ⛔ KHONG bao gio nem.

    ## 🔴 Vi sao la ĐE XUAT chu ⛔ khong phai tu dong che — chu du an chot 25/09

    Nghiem thu 25/09 tren hai phim that: V4b ⛔ **khong phan biet duoc** dai phu
    de voi bang ten HUD cua game — ca hai deu la *chu trang vien den, doi theo
    thoi gian*, va tren `phim2` dai do ra **rong hon ~8 % chieu cao khung** vi
    trum ca hang HUD. Tang khung 18 -> 24 -> 36 -> 48 ⛔ **khong** siet lai, tuc
    do la **gioi han cua phuong phap**, ⛔ khong phai chuyen tinh chinh nguong.

    ⭐ **Do SAI nguy hon ⛔ KHONG do.** ⛔ Khong do ⇒ khach tu khoanh, mat cong.
       Do sai ⇒ khach nhan ve mot video **bi hong** ma ta **da thu tien**.

    ⚠️ Va chinh meo dau trang cua he tham chieu noi dung dieu do: *"nen khoanh
       vung phu de bang tay — tool khoi mat cong do, render nhanh hon, dai che
       can khit hon"*. Ho **co** bo do, va ho **van** khuyen khoanh tay.

    ⇒ Ham nay tra ve mot de xuat. Giao dien hien khung do; khach **bam nhan hoac
      keo sua** thi no moi thanh mot `vung_che` THAT. ⛔ Ket qua o day ⛔ khong
      bao gio duoc ghi thang vao `vung`.

    ⚠️ `duong` la **MP4 ĐA HOAN THIEN TIENG** (dau ra cua Giai doan 1), ⛔ khong
       phai tep nguon cua khach — xem khoi dau tep.

    ## Hinh dang tra ve

        {"trang_thai": "co" | "khong_co" | "khong_do_duoc",
         "vung": [{"x0","y0","x1","y1", "nguon": "logo_tinh"|"dai_chu",
                   "goc"?}, ...],
         "so_khung": {"logo_tinh": N, "dai_chu": N},
         "ly_do": "<cau tieng Viet, CHI khi khong_do_duoc>"}

    ⭐ `so_khung` la **bang chung** rang chang do da chay: mot `vung` rong kem
       `so_khung > 0` la *"da quet that, ⛔ khong thay gi"*, khac han mot loi.

    ## ⛔ Vi sao bat `DoVungLoi` o day ⛔ KHONG phai nuot loi lang le

    Ngoai le duoc bien thanh mot **gia tri nhin thay duoc**
    (`trang_thai="khong_do_duoc"` + `ly_do`), va gia tri do di ra toi giao dien.
    Đo la **xu ly** loi, ⛔ khong phai giau no — dung phan biet ma
    `tools/check_silent_except.py` dat ra o dieu kien thu ba cua no.

    ⚠️ Mot de xuat hong ⛔ **khong duoc** giet lan chay: khach van con duong tu
       khoanh vung, va do la duong chinh chu ⛔ khong phai duong lui.

    `tranh` = cac cap `(y0, y1)` vung khach ĐA VE. Xem BAT BIEN 2.
    """
    so_khung: dict[str, int] = {}
    try:
        # ⛔ Hai loi goi viet THANG, ⛔ khong gom vao mot vong lap: hai ham nay co
        #    hai chu ky khac nhau (`tranh` chi co nghia voi dai chu — mot logo
        #    goc ⛔ khong nam tren truc Y ma `tranh` noi toi), va mot vong lap se
        #    che dieu do sau mot `if ten == ...`.
        logo = do_logo_tinh(duong)
        so_khung[NGUON_LOGO] = logo.so_khung
        dai = do_dai_chu(duong, tranh=tranh)
        so_khung[NGUON_DAI] = dai.so_khung
    except DoVungLoi as loi:
        # ⛔ Mot chang hong = CA de xuat khong do duoc. ⛔ Khong tra ve nua ket
        #    qua kem mot trang thai noi rang moi thu on: mot de xuat THIEU trong
        #    y het mot de xuat DAY DU tren man hinh khach.
        return {"trang_thai": TRANG_THAI_KHONG_DO_DUOC, "vung": [],
                "so_khung": so_khung, "ly_do": str(loi)}
    ra = ([{**h, "nguon": NGUON_LOGO} for h in logo.vung]
          + [{**h, "nguon": NGUON_DAI} for h in dai.vung])
    return {"trang_thai": TRANG_THAI_CO if ra else TRANG_THAI_KHONG_CO,
            "vung": ra, "so_khung": so_khung, "ly_do": ""}
