"""D5 — NAN THOI LUONG: `gop_khe`, tang RIENG TRUOC bac thang cua `nan_cho_vua`.

⛔ Tep nay **thuan ham**: ⛔ khong doc tep, ⛔ khong goi LLM, ⛔ khong cham am
   thanh.

## 🔴 25/09: ba trong bon "can gat" ban dau da XOA — TRUNG voi `nan_cho_vua.py`

Tep nay tung khai **bon can gat** (RUT GON, PHAN PHOI LAI, GIAN/NEN, GOP KHE),
nhung ca bon deu **KHONG co nguoi goi** trong ma san pham (`tests/test_453`).
Doi chieu voi `nan_cho_vua.py` — bac thang **bon nac** dang CHAY THAT trong
`giai_doan_giong.py` — cho ket qua:

    1 RUT GON loi dich (LLM)     🔴 TRUNG nac 2 cua `nan_cho_vua`  (da chay)
    2 PHAN PHOI LAI thoi gian    ⛔ CHET: khong con khoang lang THAT giua hai
                                    khe de muon (xem docstring cu, git history)
    3 GIAN / NEN giong           🔴 TRUNG nac 3 cua `nan_cho_vua`  (da chay)
    4 GOP KHE                    ✅ MOI THAT — khong co trong `nan_cho_vua`

⇒ Ba can gat dau + `con_khong_vua` (ham bao cao di kem) **da XOA** (25/09) —
  canh cho trong o `tests/test_2062_asv_nan_thoi_luong.py`. ⛔ Dung them lai
  ma khong doi chieu lai voi `nan_cho_vua.py`: hai cho khai cung mot chinh
  sach la dung thu kho nay da tra gia (`docs/.../hai-cho-khai-cung-mot-dieu...`).

## `gop_khe` di TRUOC ca bac thang, ⛔ khong phai mot nac trong no

`nan_cho_vua.khe_cua(m)` doc `bat`/`ket` **CO DINH** cua tung doan — no sua
**mot cau cho vua khe cua chinh no**, ⛔ khong bao gio doi RANH GIOI khe. `gop_khe`
thi nguoc lai: no doi **chinh cac khe** (gop nhieu khe hep thanh mot khe rong hon)
TRUOC KHI bac thang do tren tep that bat dau. Hai tang khac nhau, nen ⛔ khong
gap `gop_khe` vao `nan_cho_vua` — do la giau mot quyet dinh THOI GIAN (doi ranh
gioi khe) o trong mot ham sua CAU, dung thu `thoi_gian.py` cam ngay tu dau file.

## ✅ DA NOI THAT (25/09, lan `b2-gop-khe`) — `gop_khe` DIEU KHIEN duong sinh tieng

`giai_doan_giong.chay()` goi `nhom_chi_so()` NGAY sau khi doc `content.json`, roi
doc **mot luot cho ca nhom** (`_gop_mot_nhom`). Truoc do no chi tinh
`so_khe_neu_gop` roi vut — mot con so bao cao, khong dieu khien gi.

### Bat bien phai giu, va ta giu duoc no ⛔ KHONG can sua `giai_doan_noi_dung.py`

`giai_doan_thoi_gian.py:88-89` doi **MOI** `ma` trong `content.json`
(`CONTENT_PROCESS`, ghi TRUOC va DOC LAP voi `voice_synthesis`) phai co **mot**
dong `giay` trong `ban_ke.json`, va `thoi_gian.py:182-184` nem
`ThoiGianError('Doan {ma} chua co tieng.')` neu thieu.

⭐ **Giai: mot khe gop sinh MOT tep tieng, nhung `no_ban_ke()` tra lai MOT dong
   cho MOI `ma` goc** — cung `khoa`, `giay` chia theo am tiet (`chia_giay`). Dong
   dau mang `gop` + `giay_tep`; cac dong sau mang `gop_vao`. Nen `content.json`
   ⛔ khong bi cham, va `van_ban.kiem`/`long_tieng.kiem` (phu kin chinh xac) ⛔ khong
   bi noi long mot ly.

⛔ **Va co y ⛔ KHONG gop o `giai_doan_noi_dung.py`**, du duong do it ma hon: gop
   trong `content.json` la gop CA O PHU DE, va o phu de cua ta chua toi da
   `phu_de.SO_DONG_TOI_DA x KY_TU_MOI_DONG` = **84** ky tu. Do 25/09 tren 188 o
   that: gop ca o day ti le o vuot tran bo cuc tu **15,4 % len 42,9 %**
   (`bang_chung/b2_gop_khe/ket_qua.json`). Tran gop 220 cua Viral la tran cua
   mot LUOT DOC, ⛔ khong phai cua mot o chu — xem `TRAN_KY_TU_GOP`.

### Bon cho ha nguon, va mot cho khai

Mot khe gop lam 2-4 `ma` tro vao CUNG mot tep. Bon cho anh xa `ma -> khoa` de DAT
tep len truc thoi gian, va cho nao bo sot se dat cung mot tep 2-4 lan — nghe
thanh **tieng vang**, ⛔ khong nem, ⛔ khong log. ⇒ Ca bon di qua `tep_theo_ma()` /
`la_dong_theo_sau()` o cuoi tep nay: `giai_doan_thoi_gian._dung_ban_phoi`,
`ban_dung.py`, `giai_doan_qc_do_luong.chay`, va `qc.py` (T6 dung `khoa`, nen no
tu dung). `tests/test_4700` co mot banh coc chan cho thu nam.

`thoi_gian.lap_ke_hoach` nhan `nhom_gop` de dat cac `ma` di theo **lien nhau**
(tieng cua chung nam trong cung mot khoi) va de ca nhom dung **MOT** `he_so_toc`.

### Lo i cua no, do tren 3 phim that (188 khe, bang chung da commit)

    khe                              188 -> 126   (33 % khe bi hap thu)
    khe bi phan quyet duoi 1 am tiet 119 (63,3 %) -> 44 (34,9 %)
    SO luot goi model                135 -> 85    (-37 %)
    TI LE khe khong vua              71,8 % -> 67,5 %   ⚠️ gan nhu khong doi

⚠️ **Cai giam that la SO luot goi, ⛔ khong phai TI LE khong vua** — va do la hai
   menh de khac nhau. Ti le khong doi vi phep gop chi gop trong khi khe CHUA vua,
   nen khe ra thuong van chua vua; cai no mua la **it khe hon** de phan quyet.

## Nguon — ⛔ MUON CACH SUY, ⛔ KHONG MUON SO

⭐ **VideoLingo** (`core/_8_2_dub_chunks.py`, `config.yaml`) — thang **4 bac**:

    est_dur / accept > tol_dur       ->  2   ⛔ tran toc do cung khong cuu duoc
    est_dur > tol_dur                ->  1   nen trong tam chap nhan
    est_dur < duration - tolerance   -> -1   noi qua cham
    con lai                          ->  0   binh thuong

  va **7 hang so**: `speed_factor.min 1` · `accept 1.2` · `max 1.4` ·
  `tolerance 1.5` · `min_subtitle_duration 2.5` · `min_trim_duration 3.5` ·
  `MAX_MERGE_COUNT 5`.

⭐ **open-dubbing** (`open_dubbing/text_to_speech.py`, Apache-2.0) lam **tot hon
   hai diem**, va ta lay ca hai:

  1. `get_start_time_of_next_speech_utterance` — khe keo toi **bien co THAT ke
     tiep** (bo qua cau `for_dubbing=False`), lui ve **het tep** neu khong con
     cau nao; ⛔ khong phai mot hang so. `_calculate_target_utterance_speed`
     dung dung no: `reference_length = end - start`.
  2. `_convert_text_to_speech_without_end_silence` — chu thich nguyen van:
     *"TTS add silence at the end that we want to remove to prevent increasing
     the speech of next segments if is not necessary"* ⇒ **cat lang thua TRUOC**
     khi tinh he so.

🔴 **So cua ho ⛔ KHONG chep sang.** `tolerance 1.5 s` va `accept 1.2` do tren
   **cap ngon ngu khac** va **giong khac**. So cua ta do tren chinh du lieu ta:

       0,737  am tiet Viet / ky tu Han   (n=188, [0,562 ; 1,000])
       3,284  am tiet/giay cua giong TTS (n=18,  [3,00 ; 3,71])

   ⛔ Va ⛔ **dung dung `3,5-4,5x`**: con so ay **dung** nhung o don vi **KY TU**
      (do duoc 3,22x) — lech don vi **4,4 lan** (`N-34`).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from apps.auto_scan_video import ngon_ngu as _ngon_ngu

#: Toc do noi cua giong TTS ta dang dung, am tiet/giay.
#:
#: 🔑 **MOT CHO KHAI**: doc thang `ngon_ngu.NHIP[VI]`. ⛔ Dung go lai so.
#:
#: ⭐ Doi chieu 25/09 — hai phep do DOC LAP, CUNG dai luong, va chung DONG Y:
#:
#:      3,284   dai [3,00 ; 3,71]   18 doan TTS that (`fix_toc_do/vong_dau_moi_v*.json`)
#:      3,35    dai [3,04 ; 3,51]   giong san pham, do lai 23/09/2026
#:
#:    Hai dai chong nhau gan het, hai trung vi lech 2% ⇒ **trong nhieu**. Giu ban
#:    **moi hon** va **da noi vao san pham** (`nan_cho_vua.loi_nhac_nan` qua
#:    `ngon_ngu.HE_SO_MUC_TIEU`). Con so `3,284` nghi huu — lich su giu o day.
#:
#: ⛔ Khong phai 9 ky tu/giay cua Netflix — do la toc do **DOC** cua phu de.
#: ⛔ Va khong phai `4,5` — con so cu do da **lam hong mot lan chay that**
#:    (xem `ngon_ngu.NHIP`).
#:
#: 🔴 **MOT MAU THUAN CON MO, 25/09 — doc truoc khi tin bat ky ket luan nen nao:**
#:    lan `D5` do trung vi **4,228** (dai [3,13 ; 4,72]) tren WAV da sinh, tuc
#:    **NGOAI ca hai dai tren**. Ba phep do khong the cung dung.
#:    ⇒ Nghi phan: `D5` do WAV **da bi tang toc**, hoac dem am tiet khac cach.
#:    ⚠️ Moi ket luan dua tren `4,228` — nhat la *"bai toan nen nho hon 3,4 lan"* —
#:       **CHUA duoc coi la da chot** cho toi khi doi chieu xong.
AM_TIET_MOI_GIAY = _ngon_ngu.NHIP[_ngon_ngu.VI]


class BacNan:
    """Thang 4 bac cua VideoLingo, giu nguyen ngu nghia."""

    BINH_THUONG = 0
    NEN_TRONG_TAM = 1
    QUA_NHANH = 2          # ⛔ tran toc do cung khong cuu
    QUA_CHAM = -1


@dataclass(frozen=True)
class Khe:
    """Mot khe thoai. `bat`/`ket` la moc NGUON; `moc_sau` la bien co that ke tiep."""

    ma: str
    bat: float
    ket: float
    moc_sau: float          # ⭐ open-dubbing: bien co THAT ke tiep, ⛔ khong hang so
    am_tiet: int
    chu: str = ""

    @property
    def khe_s(self) -> float:
        return self.ket - self.bat

    @property
    def ngan_sach_s(self) -> float:
        """Toi luc khe sau bat dau — `thoi_gian.py:26-31` (muon Subdub).

        ⛔ Lay `ket - bat` la vut het khoang lang, tuc vut phan lon ngan sach.
        """
        return max(0.0, self.moc_sau - self.bat)

    def giay_can(self, *, am_tiet: int | None = None) -> float:
        n = self.am_tiet if am_tiet is None else am_tiet
        return n / AM_TIET_MOI_GIAY


def xep_bac(khe: Khe, *, tran_tang_toc: float, am_tiet: int | None = None) -> int:
    """Thang 4 bac, tinh tren **ngan sach** (da gom khoang lang muon duoc)."""
    can = khe.giay_can(am_tiet=am_tiet)
    ns = khe.ngan_sach_s
    if ns <= 0:
        return BacNan.QUA_NHANH
    if can / tran_tang_toc > ns:
        return BacNan.QUA_NHANH
    if can > ns:
        return BacNan.NEN_TRONG_TAM
    if can < khe.khe_s:
        return BacNan.QUA_CHAM
    return BacNan.BINH_THUONG


# ── GOP KHE — tang RIENG truoc bac thang, ⛔ KHONG cham ban dich ────────────

#: Tran ky tu cua MOT luot doc. Phai khop `ltt_voice.tham_so_cong_khai.
#: TRAN_MOI_LUOT_SINH` — do la tran CHAT LUONG (giong bat dau troi), ⛔ khong
#: phai tran ky thuat.
#:
#: 🔴 **Tu 25/09 no ⛔ KHONG con la tran cua `gop_khe`** — `TRAN_KY_TU_GOP` (220)
#:    la tran that su rang buoc, va no nho hon cai nay **6,8 lan**. Giu hang so
#:    nay lai vi no khai mot su that ve MAY DOC (khong phai ve phep gop), va
#:    `_kiem_chinh_sach()` o duoi bien quan he giua hai so thanh mot BAT BIEN
#:    chay luc nap module — ⛔ thay vi mot nhanh `if` khong bao gio chay.
TRAN_KY_TU_MOT_LUOT = 1500

#: Toi da bao nhieu khe duoc gop lam mot.
#:
#: ⭐ **MUON tu bot Viral** — `localize._nhom_gop_capcut()` (`localize.py:12648`,
#:    *"NGUON SU THAT DUY NHAT"*), hang `DUB_GOP_MAX = 4`; luat ay da chay THAT
#:    tren video 55 phut va gop **708/1755 cue = 40 %** (do 26/08).
#: ⭐ Nguon thu hai, DOC LAP: VideoLingo `MAX_MERGE_COUNT = 5`
#:    (`core/_8_2_dub_chunks.py:12`).
#:
#: 🔑 Lay **4** (so nho hon trong hai nguon) vi do cua ta noi hai nguong gan
#:    nhu bang nhau: `gop <=3` -> 33,3 % khe con phai nen > 1,15 · `gop <=5` ->
#:    26,5 %. Chenh 7 diem giua 3 va 5 ⇒ diem dung khong nhay cam, nen chon so
#:    da CHAY THAT tren mot he san pham.
#: ⛔ Va ⛔ dung bo tran: `TU DO` cho 5,1 % nhung khe dai nhat **189,96 s**, van
#:    ban **3.535 ky tu** — mot ban suy bien deo mat mot ket qua tot.
TRAN_GOP_KHE = 4

#: Khe (khoang LANG giua hai doan lien ke) toi da con cho phep gop, tinh GIAY.
#:
#: ⭐ **MUON tu bot Viral**: `DUB_GOP_KHE = 0,6 s` (`localize.py:12648`).
#: 🔑 Vi sao phai co: gop hai doan cach nhau 3 s la dan mot khoang lang 3 s vao
#:    GIUA mot luot doc lien mach — giong se doc lien, con hinh thi im 3 s. Tran
#:    nay la thu phan biet "hai cau trong cung mot hoi" voi "hai canh khac nhau".
#:
#: 🔴 **DO 25/09 tren du lieu cua ta: no chan 0/185 cap — tuc NO CHUA BAO GIO
#:    RANG BUOC o day.** Ly do la mot khac biet ve MO HINH KHE, khong phai mot
#:    tran dat sai: `cat_doan` cua ta cho `ket[i] == bat[i+1]` (khe = 0,000 s o
#:    moi cap), trong khi cue cua CapCut co khoang lang THAT giua chung.
#:    ⇒ Giu lai, va khai ra: du lieu co hinh dang khac (ban chep loi co khoang
#:    lang that, mot cau hinh `cat_doan` khac) thi no rang buoc ngay. ⛔ Nhung
#:    ⛔ dung "chinh" con so nay de doi ket qua — no ⛔ khong dong mot cua nao.
#:    Bang chung: `bang_chung/b2_gop_khe/ket_qua_vi_sao.json`.
TRAN_KHE_GIUA_S = 0.6

#: Tran KY TU cua mot khe da gop.
#:
#: ⭐ **MUON tu bot Viral**: `DUB_GOP_KYTU = 220` (`localize.py:12648`).
#:
#: ⚠️ **Day la tran cua MOT LUOT DOC, ⛔ KHONG phai tran cua mot o phu de.** Do
#:    duoc 25/09: o phu de cua ta chi chua `phu_de.SO_DONG_TOI_DA (2) x
#:    phu_de.KY_TU_MOI_DONG (42)` = **84** ky tu — 220 la **2,6 lan** cai do.
#:    ⇒ Chinh vi the `gop_khe` ⛔ **khong duoc gop O PHU DE**: no gop cai DOC
#:    (mot tep tieng cho ca nhom), con moi `ma` goc giu o phu de RIENG cua no
#:    (xem `no_ban_ke` + `giai_doan_giong`). Gop ca o phu de se cho `wrap_lines`
#:    do het phan du vao **dong thu hai** ("the last allowed line takes whatever
#:    remains") ⇒ mot dong 180 ky tu chay khoi man hinh, va no ⛔ khong nem.
#:
#: 🔴 **DO 25/09: no cung chan 0/185 cap** — `TRAN_GOP_KHE` (4) va `con_tiep`
#:    dong cua truoc. Giu lai vi du lieu dai hon (doan 60+ ky tu, gop 4) se dung
#:    toi no. ⛔ Dung "chinh" no de doi ket qua: hai dieu kien kia moi rang buoc.
TRAN_KY_TU_GOP = 220

#: Dau cau ket thuc MOT cau. Doan ket thuc bang mot trong nhung ky tu nay thi
#: ⛔ khong duoc gop voi doan sau — ⭐ MUON `_con_tiep(...)` cua bot Viral.
#: 🔑 Co ca dau Trung/Nhat: nguon cua ta la `zh`, va `goc` di cung `chu`.
DAU_KET_CAU = ".!?…:;。！？；："

#: Ky tu dong goi nam SAU dau cau ma khong doi y nghia "cau da het".
_DONG_GOI_CUOI = "\"'”’)]}》』、"


def _kiem_chinh_sach() -> None:
    """No luc NAP MODULE neu hai tran ky tu quay nguoc nhau.

    ⛔ Dat o cap module theo dung khuon `nan_cho_vua._kiem_chinh_sach`: mot chinh
       sach tu mau thuan phai chan viec NAP app, ⛔ khong phai doi mot phep kiem
       chay den.

    🔑 Va no bien mot **nhanh chet** thanh mot **bat bien song**: vi
       `TRAN_KY_TU_GOP < TRAN_KY_TU_MOT_LUOT`, mot phep kiem `len(chu) >
       TRAN_KY_TU_MOT_LUOT` trong `gop_khe` se ⛔ KHONG BAO GIO chay — va ma
       phong thu cho mot ca khong the xay ra chi mua su yen tam bang tin dung
       gia. Khang dinh nay tra loi cung cau hoi, mot lan, o cho doc duoc.
    """
    if not 0 < TRAN_KY_TU_GOP < TRAN_KY_TU_MOT_LUOT:
        raise AssertionError(
            "TRAN_KY_TU_GOP (%d) phai nam trong (0; TRAN_KY_TU_MOT_LUOT=%d): "
            "mot khe da gop ⛔ khong bao gio duoc vuot tran cua may doc"
            % (TRAN_KY_TU_GOP, TRAN_KY_TU_MOT_LUOT))


_kiem_chinh_sach()


def con_tiep(chu: str) -> bool:
    """Cau NAY con tiep sang doan sau khong? ⭐ MUON `_con_tiep` cua bot Viral.

    ⛔ Khong gop qua mot dau ket cau: hai cau tron thanh mot luot doc lien mach
       thi may doc mat cho nghi, va nguoi nghe mat ranh gioi y.

    ⚠️ Doan RONG tra `False` — ⛔ khong phai `True`. "Khong biet" va "con tiep"
       la hai chuyen khac nhau, va ben an toan o day la ⛔ khong gop.
    """
    s = str(chu or "").strip().rstrip(_DONG_GOI_CUOI).strip()
    if not s:
        return False
    return s[-1] not in DAU_KET_CAU


def _khe_giua(truoc: Khe, sau: Khe) -> float:
    """Khoang LANG giua hai doan lien ke, tinh giay. Am (chong lan) -> 0."""
    return max(0.0, float(sau.bat) - float(truoc.ket))


def gop_khe(khes: Sequence[Khe], *, tran_tang_toc: float,
            tran_gop: int = TRAN_GOP_KHE,
            tran_khe_giua_s: float = TRAN_KHE_GIUA_S,
            tran_ky_tu: int = TRAN_KY_TU_GOP) -> list[Khe]:
    """Gop khe lien ke cho toi khi khe VUA, theo LUAT DA CHAY THAT cua Viral.

    ⭐ **Re hon nan_cho_vua**: no ⛔ khong cham mot chu nao cua ban
       dich (⇒ **0 diem chrF++**), ⛔ khong goi LLM, va ⛔ khong gay troi giong
       (`R4 §20`: khe gop dai nhat 427 ky tu, cach tran troi 1.500 **3,5 lan**;
       va `do_bai_dai.py` cho thay ban GHEP **tot hon** ban mot luot).

    Do tren ba phim: ti le khe phai nen > 1,15 tu **55,6 % xuong 26,5 %** —
    hon MOT NUA bai toan, mien phi.

    🔴 **NAM DIEU KIEN, bon trong so do MUON tu `localize._nhom_gop_capcut()`
       (`localize.py:12648`, da chay that, gop 708/1755 cue):**

      1. chi so LIEN nhau                          (`_i == _p + 1` cua Viral)
      2. `tran_gop`   <= 4 doan                    (`DUB_GOP_MAX`)
      3. `tran_khe_giua_s` <= 0,6 s                (`DUB_GOP_KHE`)
      4. `tran_ky_tu` <= 220 ky tu                 (`DUB_GOP_KYTU`)
      5. `con_tiep(...)` — cau CHUA ket thuc       (`_con_tiep`)

    ⭐ **Va MOT dieu kien la CUA TA, giu lai co y:** khe da VUA thi ⛔ khong bi
       dong vao (`xep_bac(...) > BINH_THUONG`). Viral ⛔ khong co dieu kien nay vi
       ho gop de **TONG HOP** cho prosody chay suot cau; ta gop de **noi rong
       KHE** cho mot phan quyet dung sai co nghia. Hai muc dich khac nhau ⇒ giu
       dieu kien nay lam phep gop hep hon CA HAI he, ⛔ khong rong hon.

    🔴 **⛔ KHONG gop O PHU DE — va do la mot phep do, khong phai mot y thich.**
       O phu de cua ta chua toi da `phu_de.SO_DONG_TOI_DA x KY_TU_MOI_DONG` = 84
       ky tu, tuc `tran_ky_tu` 220 cua Viral rong hon **2,6 lan**: 220 la tran
       cua MOT LUOT DOC, ⛔ khong phai cua mot o chu. Nen `giai_doan_giong` gop
       cai DOC (mot tep tieng cho ca nhom) va `no_ban_ke` tra lai MOT dong cho
       MOI `ma` goc ⇒ phu de giu nguyen tung o cua no. Xem `TRAN_KY_TU_GOP`.

    ⭐ **Va day la ly do `gop_khe` duoc phep SONG o ta trong khi no phai CHET o
       Viral.** Viral tat `DUB_CAPCUT_GOP` tu 01/09 — ⛔ khong phai vi gop sai, ma
       vi ho **CAT TRA VE** tung cue theo moc tu cua server: `end_time` danh dau
       het NGUYEN AM nen phan buong phu am bi xen o **100 % cau gop**, can toi
       >250 ms voi giong `lacphi` (`localize.py:11258-11268`); lan gop truoc do
       (`_gop_cue_cung_cau`) troi **5,80 s**. Ca hai ca hong deu o phep CAT TRA
       VE. `gop_khe` giu **mot khoi trong mot khe**, ⛔ khong cat tra ve ⇒ **mien
       nhiem ve mat cau truc** voi ca hai.

    ⛔ **KHONG gop qua ranh gioi CANH?** — da do va **BAC BO**: `R4 §19`,
       **80,9 %** khe dang chay DA vat qua cat canh (co khe vat qua 4 cat), va
       san pham la **thuyet minh MOT giong** nen cat canh ⛔ khong phai cho ngat
       loi. Rang buoc ay dung cho long tieng NHAN VAT tren hinh (`N-34`).
    """
    ra: list[Khe] = []
    for nhom in nhom_chi_so(khes, tran_tang_toc=tran_tang_toc,
                            tran_gop=tran_gop,
                            tran_khe_giua_s=tran_khe_giua_s,
                            tran_ky_tu=tran_ky_tu):
        goc = khes[nhom[0]]
        cuoi = khes[nhom[-1]]
        ra.append(replace(
            goc,
            am_tiet=sum(khes[k].am_tiet for k in nhom),
            chu=" ".join(khes[k].chu for k in nhom).strip(),
            moc_sau=cuoi.moc_sau, ket=cuoi.ket))
    return ra


def nhom_chi_so(khes: Sequence[Khe], *, tran_tang_toc: float,
                tran_gop: int = TRAN_GOP_KHE,
                tran_khe_giua_s: float = TRAN_KHE_GIUA_S,
                tran_ky_tu: int = TRAN_KY_TU_GOP) -> list[list[int]]:
    """Phan hoach `khes` thanh cac NHOM chi so lien nhau — luat o `gop_khe`.

    ⭐ **Day la lop LOI**, `gop_khe` chi la mot cach doc no. Nguoi goi that
       (`giai_doan_giong`) can biet nhom gom nhung `ma` NAO, ⛔ khong chi can biet
       khe gop ra dai bao nhieu — mot khe gop phai tra lai mot dong `ban_ke` cho
       MOI `ma` goc, neu khong `giai_doan_thoi_gian.py:88-89` nem
       `ThoiGianError('Doan {ma} chua co tieng.')` tren MOI lan chay co gop.

    ⭐ Nhom mot phan tu van la mot nhom (luon co mat). ⛔ Khong dung `None`/danh
       sach rong cho "khong gop": *"co gop hay khong"* va *"gop voi ai"* la cung
       mot cau hoi, va tra loi no bang hai hinh dang la dung lai cai bay "hai
       trang thai gop thanh mot gia tri".
    """
    ra: list[list[int]] = []
    i, n = 0, len(khes)
    while i < n:
        goc = khes[i]
        am_tiet, chu, moc_sau, d = goc.am_tiet, goc.chu, goc.moc_sau, 1
        while (d < tran_gop and i + d < n
               # ⭐ dieu kien CUA TA: khe da vua thi dung lai
               and xep_bac(replace(goc, am_tiet=am_tiet, moc_sau=moc_sau),
                           tran_tang_toc=tran_tang_toc) > BacNan.BINH_THUONG
               # 5 — cau chua ket thuc (Viral `_con_tiep`)
               and con_tiep(chu)):
            ke = khes[i + d]
            # 3 — khe giua hai doan (Viral `DUB_GOP_KHE`)
            if _khe_giua(khes[i + d - 1], ke) > tran_khe_giua_s:
                break
            chu_moi = f"{chu} {ke.chu}".strip()
            # 4 — tran ky tu cua mot luot doc (Viral `DUB_GOP_KYTU`)
            if len(chu_moi) > tran_ky_tu:
                break
            am_tiet += ke.am_tiet
            chu, moc_sau = chu_moi, ke.moc_sau
            d += 1
        ra.append(list(range(i, i + d)))
        i += d
    return ra


def chia_giay(giay_tep: float, am_tiet: Sequence[int]) -> list[float]:
    """Chia do dai THAT cua mot tep tieng gop cho tung thanh vien cua nhom.

    🔑 **Chia theo AM TIET, ⛔ khong chia deu.** Mot nhom `["Vang.", "Nhung neu
       hoi ai da lam viec do thi khong ai tra loi duoc."]` chia deu se cho o phu
       de dau 50 % thoi luong cho 1 am tiet — phu de lech han voi tieng.

    ⚠️ ⛔ **Day KHONG phai mot phep cat tep tieng.** Tep van la MOT khoi, phat
       MOT lan (`giai_doan_thoi_gian._dung_ban_phoi` dat no dung mot lan). Cac
       con so nay chi noi cho `thoi_gian.lap_ke_hoach` va phu de biet **phan noi
       cua tung `ma` nam o dau BEN TRONG khoi ay**. Dung cai nay de CAT tep la
       lap lai dung loi da lam Viral phai tat phep gop (xem `gop_khe`).

    ⛔ Tong cac phan **bang** `giay_tep` (phan du don vao phan cuoi), de
       `lap_ke_hoach` ⛔ khong bao gio dat mot nhom dai hon tep that cua no.
    """
    g = max(0.0, float(giay_tep))
    n = len(am_tiet)
    if n == 0:
        return []
    if n == 1:
        return [g]
    tong = sum(max(0, int(a)) for a in am_tiet)
    if tong <= 0:                       # ⛔ khong chia cho 0: roi ve chia deu
        phan = [g / n] * n
    else:
        phan = [g * max(0, int(a)) / tong for a in am_tiet]
    # 🔑 **SAN 1 ms cho moi thanh vien khi tep co do dai.** ⛔ Day ⛔ khong phai ma
    #    phong thu cho mot ca khong the xay ra: `thoi_gian.lap_ke_hoach` doi don
    #    vi MILI GIAY (`_ms`) va **nem** `ThoiGianError('Doan {ma} chua co
    #    tieng.')` khi `dai <= 0`. Mot thanh vien 1 am tiet trong mot nhom rat dai
    #    co the lam tron xuong 0 ms ⇒ ca lan chay chet vi mot phep chia. Day la
    #    mot ranh gioi giua HAI HE DON VI, ⛔ khong phai mot nhanh "cho chac".
    san = 0.001 if g > 0 else 0.0
    phan = [max(san, x) for x in phan]
    # Phan du lam tron don vao phan CUOI — tong phai bang giay_tep tung mili giay.
    phan[-1] = max(san, g - sum(phan[:-1]))
    return [round(x, 6) for x in phan]


# ── BAN KE: mot tep tieng, NHIEU dong ───────────────────────────────────────
#
# 🔴 **Bat bien phai giu, va no da chan lan truoc:**
#    `giai_doan_thoi_gian.py:88-89` doi **MOI** `ma` cua `content.json` co MOT
#    dong `giay` trong `ban_ke.json`, va `thoi_gian.py:182-184` nem
#    `ThoiGianError('Doan {ma} chua co tieng.')` neu thieu. `content.json` duoc
#    ghi TRUOC va DOC LAP voi `voice_synthesis`, nen gop o day ⛔ khong duoc lam
#    bien mat mot `ma` nao.
#
# ⭐ **Giai bang cach ⛔ KHONG pha bat bien ay:** mot khe gop sinh MOT tep tieng,
#    va `no_ban_ke` tra lai MOT dong cho MOI `ma` goc — cung `khoa`, `giay` chia
#    theo am tiet (`chia_giay`). Dong dau mang `gop` (danh sach `ma` no phu);
#    cac dong sau mang `gop_vao` (ma cua dong dau).
#
# 🔑 **`gop_vao` la mot truong O BIEN, ⛔ khong phai mot chi tiet ben trong.** Bon
#    cho ha nguon anh xa `ma -> khoa` de DAT tep len truc thoi gian:
#    `giai_doan_thoi_gian._dung_ban_phoi`, `ban_dung.py`, `giai_doan_qc_do_luong`
#    va `qc.py`. Ba cho dau ma bo sot `gop_vao` se dat CUNG mot tep 2-4 lan —
#    nghe thanh tieng vang, ⛔ khong nem, ⛔ khong log. ⇒ Ca bon di qua
#    `tep_theo_ma()` o duoi, mot cho khai, ⛔ khong bon dict comprehension.

#: Dong DAU cua mot nhom: danh sach `ma` (ke ca chinh no) ma tep nay doc.
KHOA_GOP = "gop"

#: Dong THEO SAU: `ma` cua dong dau. Co mat = dong nay ⛔ KHONG so huu tep.
KHOA_GOP_VAO = "gop_vao"

#: Dong dau: do dai THAT cua ca tep (⛔ khong phai `giay` phan cua rieng no).
KHOA_GIAY_TEP = "giay_tep"


def la_dong_theo_sau(dong) -> bool:
    """Dong `ban_ke` nay co phai mot `ma` DI THEO mot tep cua `ma` khac khong?

    ⭐ Mot ham thay cho `d.get("gop_vao")` rai rac: bon cho ha nguon hoi cung cau
       hoi nay, va mot cho trong bon go sai ten khoa se im lang.
    """
    return bool((dong or {}).get(KHOA_GOP_VAO))


def am_tiet_cua(chu: str) -> int:
    """Dem am tiet tieng Viet = token cach nhau boi khoang trang.

    ⭐ Dung dinh nghia da co san cua kho (`ngon_ngu.py:47-49`: voi tieng Viet
       "dem TU la dem AM TIET, cung mot phep"), ⛔ khong bia ra mot don vi moi
       roi so voi so cua nguoi khac (`N-34`).
    """
    return len(str(chu or "").split())


def no_ban_ke(dong_dau: dict, thanh_vien: Sequence[dict]) -> list[dict]:
    """MOT dong ban ke cua mot khe da gop -> MOT dong cho MOI `ma` goc.

    `dong_dau`   dong `ban_ke` vua sinh ra (mang `ma` cua thanh vien dau, `khoa`
                 cua tep tieng, `giay` = do dai THAT cua ca tep, `chu` = van ban
                 GOP that su da doc).
    `thanh_vien` cac muc `content.json` cua nhom, DUNG thu tu.

    ⭐ Nhom mot thanh vien tra ve dung mot dong — va dong ay mang `gop` do dai 1.
       ⛔ Khong co hinh dang thu hai cho ca "khong gop": mot nguoi doc `ban_ke`
       hoi *"dong nay phu nhung ma nao"* luon nhan cung mot loai cau tra loi.
    """
    ma = [str(m.get("ma") or "") for m in thanh_vien]
    if not ma:
        raise ValueError("no_ban_ke: nhom rong")
    giay_tep = float(dong_dau.get("giay") or 0.0)
    phan = chia_giay(giay_tep, [am_tiet_cua(m.get("chu")) for m in thanh_vien])

    dau = {**dong_dau, "giay": phan[0], KHOA_GIAY_TEP: giay_tep, KHOA_GOP: ma}
    if len(ma) == 1:
        return [dau]

    ra = [dau]
    for k in range(1, len(ma)):
        # ⛔ CHINH XAC nhung truong ha nguon doc, ⛔ khong `{**dong_dau}`: sao ca
        #    dong dau se chep `gop`/`giay_tep`/`tu_cu` sang dong theo sau va lam
        #    hai loai dong khong phan biet duoc nua.
        theo = {"ma": ma[k], "khoa": str(dong_dau.get("khoa") or ""),
                "chu": str(thanh_vien[k].get("chu") or ""),
                "giay": phan[k], KHOA_GOP_VAO: ma[0],
                "khe": round(max(0.0, float(thanh_vien[k].get("ket") or 0.0)
                                 - float(thanh_vien[k].get("bat") or 0.0)), 3),
                "trang_thai_nan": str(dong_dau.get("trang_thai_nan") or ""),
                "so_vong_nan": int(dong_dau.get("so_vong_nan") or 0)}
        # ⭐ He so co gian la cua CA TEP, nen moi thanh vien phai mang CUNG mot
        #    so: `thoi_gian.lap_ke_hoach` doc no cho tung `ma`, va hai so khac
        #    nhau tren cung mot tep se cho hai moc khong the cung dung.
        if dong_dau.get("he_so_co_gian"):
            theo["he_so_co_gian"] = dong_dau["he_so_co_gian"]
        if dong_dau.get("tu_cu"):
            theo["tu_cu"] = True
        ra.append(theo)
    return ra


def tep_theo_ma(ban_ke) -> dict[str, str]:
    """`{ma: khoa tep tieng}` — ⭐ CHI nhung dong SO HUU mot tep.

    🔴 **Mot cho khai cho bon nguoi goi.** Truoc 25/09 bon cho tu viet
       `{d["ma"]: d.get("khoa") for d in ban_ke["doan"]}`; voi khe gop thi dict
       ay co 2-4 `ma` tro vao CUNG mot tep, va ai dung no de DAT tep len truc
       thoi gian se dat tep ay 2-4 lan. Khong nem, khong log — chi nghe thanh
       tieng vang.

    ⛔ Nguoi goi can `{ma: giay}` (vd `giai_doan_thoi_gian` de lap ke hoach) thi
       ⛔ KHONG dung ham nay: ho can CA cac dong theo sau. Hai cau hoi khac nhau.
    """
    return {str(d.get("ma") or ""): str(d.get("khoa") or "")
            for d in ((ban_ke or {}).get("doan") or [])
            if not la_dong_theo_sau(d)}


def nhom_theo_ma(ban_ke) -> dict[str, str]:
    """`{ma dong theo sau: ma dong dau}` — rong khi lan chay ⛔ khong gop gi."""
    return {str(d.get("ma") or ""): str(d.get(KHOA_GOP_VAO) or "")
            for d in ((ban_ke or {}).get("doan") or [])
            if la_dong_theo_sau(d)}
