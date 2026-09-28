"""DIEM DONG — tin hieu "duoi canh xau" cho `ke_cat` (B13 viec E2, 28/09).

## Chu du an chot 28/09 — vi sao module nay ton tai

    "chi cat canh THAT SU xau; uu tien doan KHONG co tieng; thuong la hien
    tuong o DUOI canh (rung, chuyen canh loi, camera khong on dinh); tuyet
    doi tranh cat vao loi thoai."

`ke_cat.py` da co ba trong bon ve: `co_thoai` la luat cung, `TOI_THIEU_GIAY`
loai doan qua ngan, va `TRAN_CAT_TI_LE` chan tren. Ve con thieu la **"duoi
canh xau"** — truoc module nay, `edit_plan` khong co tin hieu nao de thay cai
chu du an thay, nen no luon ket luan `so_canh_hong = 0`.

## Tin hieu MUON tu `C:\\Cut_only ver2\\nerf_engine\\stages\\motion.py` (CHI DOC)

    diem dong = mean(cv2.absdiff(khung_xam, khung_truoc))  tren 320x180, 5 fps

Don gian, tat dinh, ⛔ khong model — dung nguyen DINH NGHIA tin hieu do (xem
`FPS_MAU`/`RONG_MAU`/`CAO_MAU` duoi day, khop dung ba con so tren).

## 🔴 GIAI MA BANG ffmpeg, ⛔ KHONG bang `cv2.VideoCapture` — va day la mot
##    QUYET DINH, khong phai so suat

Ban goc (coordinator) do rat ky `cv2.setNumThreads` tren chinh may nay va thay
no **KHONG AN** — `getNumThreads()` doc lai dung N nhung CPU dinh khong doi
(9,9-10,7 loi bat ke N). Cach dung la chan o tang HE DIEU HANH
(`psutil.Process.cpu_affinity`, dung khuon `do_vung_ocr.chan_loi()`).

Nhung `chan_loi()` dinh nghia trong `do_vung_ocr.py` — mot tep cua LAN KHAC
(L3, dang lam OCR), va bai brief cua tac vu nay noi ro: ⛔ dung tu sua
`do_vung_ocr.py`, ⛔ dung viet mot ban `chan_loi` THU HAI, va neu can NOI no de
dung chung thi BAO nguoi dieu phoi. Da THU import `chan_loi` qua module khac —
va no khong dung duoc: `tools/check_khai_tran_cpu.py` (banh coc L3 vua them)
phan tich AST **TUNG TEP RIENG**, va no chi cong nhan mot `with <ten>():` la
"da boc" khi `<ten>` la mot ham `@contextlib.contextmanager` **DINH NGHIA
TRONG CHINH TEP DANG XET** va than ham do chua mot LOI GOI THAT
(`cpu_affinity`/`setNumThreads`/`set_num_threads`) — mot `with chan_loi():` goi
qua import lien-module se KHONG duoc nhan ra, va tep nay se bi bao VI PHAM
(xem docstring `tools/check_khai_tran_cpu.py`, muc "Ba tang chung minh").
⇒ Ba lua chon con lai deu cham tep ngoai pham vi so huu cua lan nay
(`do_vung_ocr.py` hoac `check_khai_tran_cpu.py`, ca hai deu cua L3).

⇒ **Quyet dinh:** ⛔ khong dung `cv2` chut nao trong module nay. Giai ma qua
   `ffmpeg` (tien trinh con, cung khuon voi `nhap_media._chay`/`ket_xuat.py`
   da dung khap kho nay cho MOI viec doc/ghi video) roi tinh diem dong bang
   `numpy` thuan (⛔ khong nam trong danh sach thu vien nang cua banh coc CPU).

   **Cai duoc:** tranh duoc HO CPU cua `cv2`/`onnxruntime` cu the (khong con
   thu vien Python nao tu dong lay het loi vat ly trong tien trinh nay).

   🔴 **NHUNG ⛔ khong mien phi, va DO MOI THAY** — `ffmpeg` co HO CPU cua
   RIENG no, khac hinh dang nhung CUNG mot lop loi: `-vf fps=...,scale=...`
   (bo loc "don gian") tu mo mot pool luong RIENG cho loc (`-filter_threads`,
   mac dinh = so loi vat ly), va truyen mot minh `-threads N` (giai ma) KHONG
   cham toi no. Do that tren video khach that (275 s, xem `TRAN_LUONG_FFMPEG`):
   chi `-threads 2` van dinh **13,42 loi**; them `-filter_threads 2
   -filter_complex_threads 2` moi xuong **2,27 loi**. ⇒ Tranh mot ho CPU roi
   suyt mo lai chinh no duoi ten khac — bai hoc la **DO CA CHUOI LOC**, ⛔
   khong chi do lenh giai ma chinh.

   **Cai gia:** lech mot chut so voi cau chu "dung cv2 nhu ban tham chieu" —
   ghi lai day de nguoi dieu phoi doi lai neu muon, nhung dinh nghia TIN HIEU
   (mean abs diff, 320x180, 5fps) la CUNG mot dinh nghia, chi khac co che giai ma.

## 🔴 "diem dong" la DAI LUONG muon duoc, "duoi xau" la PHAN QUYET tu xay

Nguoi dieu phoi da cho V5 doc lai `D:\\Viral` (kho khac, KHONG phai
`C:\\Cut_only ver2`): `xu_ly_chon.py` cua no la tick-chon hieu ung cua khach
(mirror/speed/watermark), ⛔ khong phai ma chon/loai canh; ma do canh THAT cua
Viral (`cat_nho.py:57-90`) chi dung PySceneDetect de bam RANH GIOI clip reup —
⛔ khong co khai niem "canh xau/tot" nao. Va phia kho nay, `blackdetect`/
`freezedetect` (`giai_doan_ban_bien_tap.py`) ⛔ khong bat duoc rung/camera bat
on. ⇒ **Khong noi nao co san "tin hieu duoi xau" de muon.**

`motion.py` (`C:\\Cut_only ver2`) van la nguon DUY NHAT — nhung no cho **dai
luong** (`mean(cv2.absdiff)`), ⛔ khong cho **phan quyet**: no dung diem dong
de **CHON doan HAY** (highlight — cang dong cang tot). Viec cua module nay la
**NGUOC LAI** — LOAI duoi XAU. Hai bai toan doc CUNG mot con so theo hai
huong trai nhau, nen `duoi_xau_cua_canh` duoi day la ma **TU XAY**, ⛔ khong
phai ma muon dich sang tieng Viet.

## ⭐ Bien chuoi diem dong thanh "duoi canh xau" — TUONG DOI, ⛔ khong TUYET DOI

Day la phan chu du an giao tu thiet ke ("nen dung mot nguong tuyet doi ap cho
moi canh — no se chi bat cac canh hanh dong"). Mot canh hanh dong (video game,
the thao) co diem dong TRUNG BINH cao — ap mot nguong tuyet doi se bat NHAM ca
canh do, va bo LOT mot canh tinh (talking head) co duoi rung nhe nhung van
duoi nguong tuyet doi.

⇒ So **duoi canh voi CHINH GIUA cua no** (`duoi_xau_cua_canh`): mot canh von
   dong nhieu thi duoi dong nhieu la BINH THUONG (ti le duoi/giua ~ 1); cai
   BAT THUONG la duoi dong **hon han** giua CUA CHINH NO — bat ke muc dong
   tuyet doi cua ca canh la bao nhieu. `giua` la nua giua cua canh (25%-75%
   thoi luong), ⛔ khong phai "moi thu tru duoi": lay ca DAU canh se an ca
   nhieu on chuyen canh TU canh truoc, lam mau so bi thoi phong sai huong.
"""
from __future__ import annotations

import logging
import subprocess

import numpy as np

from . import ke_cat as kc

log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
#  Tin hieu — dinh nghia GIONG HET ban tham chieu, chi khac co che giai ma
# ══════════════════════════════════════════════════════════════════════════════

#: Lay mau moi giay bao nhieu khung. Khop `motion.py` (kho tham chieu).
FPS_MAU = 5.0
#: Kich thuoc downsample truoc khi so — khop `motion.py`. Nho: khong can chi
#: tiet, chi can BIEN THIEN giua hai khung lien tiep.
RONG_MAU = 320
CAO_MAU = 180

#: 🔴 **DA DO tren video khach that (275 s), ⛔ khong suy doan — va lan dau
#:    SAI.** Chi truyen `-threads N` (giai ma) la KHONG DU: bo loc don gian
#:    (`-vf fps=...,scale=...`) tu mo mot pool luong RIENG cho `-filter_threads`
#:    (mac dinh = so loi vat ly) — DUNG lop loi voi `onnxruntime`/`cv2.setNum
#:    Threads` ma nguoi dieu phoi da canh bao, chi khac ten co: mot cai chot
#:    "hien nhien" ma ⛔ khong noi vao dau ca.
#:
#:        chi `-threads 2`                              13,42 loi · 2,62 s
#:        + `-filter_threads 2 -filter_complex_threads 2` **2,27 loi** · 8,63 s
#:
#:    ⇒ **CA BA** co `-threads`/`-filter_threads`/`-filter_complex_threads`
#:    deu phai duoc truyen (xem `doc_diem_dong`), ⛔ khong chi mot. Cham hon
#:    ~3,3 lan (2,6s -> 8,6s) nhung an toan — cung cai gia da chap nhan o
#:    `do_vung_ocr.CPU_TRAN_LOI` (N=6, cham hon N=8 nhung chua tran).
TRAN_LUONG_FFMPEG = 2

#: Tran thoi gian cho MOT luot giai ma diem dong (giay). Khong model, khong
#: ma hoa lai — rat re so voi `TIMEOUT_HINH_ANH` (3600 s) cua ca giai doan.
TIMEOUT_DIEM_DONG_S = 300


class DiemDongLoi(RuntimeError):
    """`ffmpeg` giai ma diem dong that bai KY THUAT. Thong bao LA cau tieng Viet."""


# ══════════════════════════════════════════════════════════════════════════════
#  Giai ma — MOT tien trinh ffmpeg cho CA video, ⛔ khong mot lan/canh
# ══════════════════════════════════════════════════════════════════════════════

def doc_diem_dong(duong_video: str, *, ffmpeg_bin: str,
                  timeout: float = TIMEOUT_DIEM_DONG_S
                  ) -> tuple[tuple[float, float], ...]:
    """`((giay, diem_dong), ...)` tren toan bo `duong_video`, 5 fps, 320x180 xam.

    `diem_dong` cua khung thu `i` (`i >= 1`) la `mean(abs(khung[i] -
    khung[i-1]))` tren thang 0..255 — dung DINH NGHIA cua `motion.py` tham
    chieu. Khung dau tien (`i=0`) khong co khung truoc nen ⛔ khong sinh diem.

    ⛔ KHONG dung `cv2.VideoCapture` — xem "GIAI MA BANG ffmpeg" o docstring
       dau tep. ⭐ MOT lan `ffmpeg` cho CA video (⛔ khong mot lan tren tung
       canh): 127 canh x 127 tien trinh con se cham hon nhieu mot lan quet va
       lam nhieu them chi phi khoi dong tien trinh.

    Nem `DiemDongLoi` khi `ffmpeg` that bai KY THUAT (nem, ⛔ khong tra rong)
    — nguoi goi (`chay()`) quyet dinh co CANH BAO roi di tiep hay khong; ham
    nay chi bao cao TRUNG THUC no co giai ma duoc hay khong.
    """
    cmd = [ffmpeg_bin, "-nostdin", "-hide_banner", "-loglevel", "error",
           "-threads", str(TRAN_LUONG_FFMPEG),
           "-i", duong_video,
           "-vf", f"fps={FPS_MAU},scale={RONG_MAU}:{CAO_MAU}",
           "-pix_fmt", "gray", "-f", "rawvideo",
           "-threads", str(TRAN_LUONG_FFMPEG),
           "-filter_threads", str(TRAN_LUONG_FFMPEG),
           "-filter_complex_threads", str(TRAN_LUONG_FFMPEG), "-"]
    try:
        kq = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiemDongLoi(
            f"khong giai ma duoc diem dong ({type(exc).__name__}: {exc})"
        ) from exc
    if kq.returncode != 0:
        raise DiemDongLoi(
            f"ffmpeg thoat ma {kq.returncode} khi doc diem dong: "
            f"{kq.stderr.decode('utf-8', 'replace')[-500:]}")

    khung_byte = RONG_MAU * CAO_MAU
    du_lieu = kq.stdout
    so_khung = len(du_lieu) // khung_byte
    if so_khung < 2:
        return ()

    mang = np.frombuffer(du_lieu, dtype=np.uint8, count=so_khung * khung_byte)
    mang = mang.reshape(so_khung, CAO_MAU, RONG_MAU).astype(np.int16)
    # ⭐ Vector hoa tren CA truc khung: hieu tuyet doi giua khung[i] va
    #    khung[i-1], trung binh tren CA khung hinh (320x180) — mot phep NumPy
    #    thuan, ⛔ khong vong lap Python tren tung diem anh.
    khac = np.abs(mang[1:] - mang[:-1])
    diem = khac.mean(axis=(1, 2))
    return tuple((round(i / FPS_MAU, 4), round(float(d), 4))
                 for i, d in enumerate(diem, start=1))


# ══════════════════════════════════════════════════════════════════════════════
#  Duoi canh xau — TUONG DOI voi giua CUA CHINH NO
# ══════════════════════════════════════════════════════════════════════════════

#: Canh ngan hon nay thi ⛔ khong danh gia — khong du mau de tach giua/duoi
#: co nghia. Khop san `canh.CANH_NGAN_NHAT_S`: moi canh that tu `canh.py` da
#: >= muc nay, day chi la mot rao PHONG THU cho chi muc tu nguon khac.
TOI_THIEU_CANH_S = 1.0

#: Ti le DUOI mac dinh (phan tram thoi luong canh), va hai bien.
TI_LE_DUOI = 0.20
TOI_THIEU_DUOI_S = 0.6
TRAN_DUOI_S = 3.0
#: 🔴 Tran TI LE cung — dam bao "duoi" (neo tai `ket`) ⛔ KHONG BAO GIO cham
#:    "giua" (25%-75% thoi luong canh, xem duoi). Thieu rao nay, mot canh
#:    ngan se lam hai vung CHONG LAN va phep so sanh mat nghia.
TRAN_TI_LE_DUOI = 0.25

#: Can it nhat bay nhieu diem MOI vung (giua, duoi) moi tinh trung binh — mot
#: trung binh tren 1 diem la nhieu, ⛔ khong phai tin hieu.
SO_DIEM_TOI_THIEU = 2

#: 🔑 NGUONG TUONG DOI — duoi phai dong hon giua CUA CHINH NO it nhat ngan
#:    nay lan moi bi coi la xau. Day la con so DUY NHAT quyet dinh "xau hay
#:    khong", va no ap DUNG NHU NHAU cho canh tinh lan canh dong — khac
#:    nguong TUYET DOI se chi bat canh hanh dong (xem docstring dau tep).
#:
#: 🔴 **⛔ KHONG dinh muon tu dau ca** — cung khuon tu khai voi
#:    `thoi_gian.TRAN_TROI_SO_DOAN = 3`: ⛔ khong du an tham chieu nao co tran
#:    nay. `motion.py` (`C:\\Cut_only ver2`) cho DAI LUONG (mean abs diff),
#:    ⛔ khong cho NGUONG — no dung diem dong de CHON doan HAY (highlight),
#:    ⛔ khong de LOAI duoi XAU (xem "diem dong la DAI LUONG, duoi xau la
#:    PHAN QUYET" o dau tep). Va V5 xac nhan CA `D:\\Viral` (`cat_nho.py`)
#:    LAN chinh kho nay (`blackdetect`/`freezedetect`) deu ⛔ khong co khai
#:    niem "canh xau" nao de mien. ⇒ **1,6 la ngan TA TU DAT**, ⛔ khong phai
#:    mot hang so muon.
#:
#: ⚠️ Chua co nhan tay tren du lieu that (chua co "su that" cho E2, khac ASR
#:    co the doi chieu `phu_song_loi`) — 1,6 la mot QUYET DINH KY THUAT dua
#:    tren logic (đuôi rung/chuyển cảnh lỗi thường tạo biên độ đột ngột,
#:    khong phai mot do tinh chinh tren nhan). `test_4937` chot pha DOI CHUNG
#:    bat buoc (chu du an 28/09): canh HANH DONG deu (ti le duoi/giua binh
#:    thuong) phai KHONG bi gan xau, canh TINH co duoi bat thuong PHAI bi gan
#:    xau — thieu MOT trong hai phia thi con so nay chi bat canh hanh dong
#:    (dung cai bay tuong doi da tranh) hoac khong bat gi ca. Neu do tren
#:    video khach that ma tin hieu KHONG tach duoc hai loai nay, do la mot
#:    KET QUA AM hop le (chu du an 28/09: "bao toi, dung ha nguong cho toi
#:    khi no co ve chay") — ghi vao bao cao, ⛔ dung tu ha xuong cho xanh.
HE_SO_BAT_THUONG = 1.6

#: Rao PHONG THU (⛔ khong phai tieu chi chinh): trung binh diem dong cua
#: DUOI cung phai vuot muc rat nho nay (thang 0..255). Thieu rao nay, hai
#: vung gan nhu dung yen (giua=0,05, duoi=0,15) van ra ti le 3x va bi bao
#: XAU du mat nguoi xem khong thay gi khac — nhieu cam bien, ⛔ khong phai
#: rung/chuyen canh loi.
NGUONG_DIEM_TOI_THIEU = 1.0

#: Vao bao cao van hanh (`UngVien.ly_do_cat`) — dung MOT hang so, ⛔ khong go
#: lai chuoi o nhieu cho (cung ly le voi `ke_cat.LY_DO_*`).
LY_DO_DUOI_CANH_XAU = "duoi_canh_xau"


def duoi_xau_cua_canh(diem: tuple, bat: float, ket: float
                      ) -> tuple[tuple[float, float], float] | None:
    """Duoi cua canh `[bat, ket)` co "xau" khong, so voi GIUA cua CHINH NO.

    `diem` la `((giay, diem_dong), ...)` — TOAN BO chuoi (thuong tu
    `doc_diem_dong`), ham nay tu loc phan trong `[bat, ket)`.

    Tra `((duoi_bat, ket), he_so)` neu duoi xau (he_so = trung_binh_duoi /
    trung_binh_giua, > 1 nghia la duoi dong hon giua), hoac `None` khi canh
    qua ngan/thieu mau/duoi khong bat thuong. ⛔ Ham nay THUAN — khong biet
    ve `co_thoai`/`ke_cat.chon`, nguoi goi (`ung_vien_duoi_xau`) chiu trach
    nhiem gop no lai thanh `UngVien` roi de `ke_cat.chon` loc tiep.
    """
    dai = float(ket) - float(bat)
    if dai < TOI_THIEU_CANH_S:
        return None

    duoi_s = min(max(dai * TI_LE_DUOI, TOI_THIEU_DUOI_S), TRAN_DUOI_S,
                dai * TRAN_TI_LE_DUOI)
    giua_bat, giua_ket = bat + dai * 0.25, bat + dai * 0.75
    duoi_bat = max(float(ket) - duoi_s, giua_ket)     # ⭐ khong cham `giua`

    diem_giua = [d for g, d in diem if giua_bat <= g < giua_ket]
    diem_duoi = [d for g, d in diem if duoi_bat <= g < ket]
    if len(diem_giua) < SO_DIEM_TOI_THIEU or len(diem_duoi) < SO_DIEM_TOI_THIEU:
        return None

    tb_giua = sum(diem_giua) / len(diem_giua)
    tb_duoi = sum(diem_duoi) / len(diem_duoi)
    if tb_duoi < NGUONG_DIEM_TOI_THIEU:
        return None
    he_so = tb_duoi / max(tb_giua, NGUONG_DIEM_TOI_THIEU)
    if he_so <= HE_SO_BAT_THUONG:
        return None
    return (duoi_bat, float(ket)), he_so


def ung_vien_duoi_xau(canh, diem: tuple) -> list[kc.UngVien]:
    """`ChiMucCanh.canh` (hay bat ky iterable co `.bat`/`.ket`) + diem dong ->
    danh sach `UngVien` cho cac duoi canh xau.

    ⛔ Khong tu loc `co_thoai`/tran 5% o day: `ke_cat.chon` da lam viec do, va
    lam lai o day la hai noi cung giu MOT luat — dung bay da ghi so nhieu lan
    trong kho nay ("hai cho khai cung mot dieu khong ai bat khop").
    """
    ra: list[kc.UngVien] = []
    for c in (canh or ()):
        ket_qua = duoi_xau_cua_canh(diem, float(c.bat), float(c.ket))
        if ket_qua is None:
            continue
        (duoi_bat, duoi_ket), he_so = ket_qua
        ra.append(kc.UngVien(bat=duoi_bat, ket=duoi_ket, diem_kem=he_so,
                             ly_do_cat=LY_DO_DUOI_CANH_XAU))
    return ra
