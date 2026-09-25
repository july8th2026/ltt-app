"""D5 — NAN THOI LUONG: ba can gat, theo dung thu tu gia tien.

⛔ Tep nay **thuan ham**: ⛔ khong doc tep, ⛔ khong goi LLM, ⛔ khong cham am
   thanh. Can gat 1 nhan mot **ham rut gon** tu ben ngoai, nen bo kiem chay
   duoc ma ⛔ khong can mot luot LLM nao.

## Thu tu ba can gat — ⭐ co CAN CU SO, ⛔ khong phai so thich

    1 RUT GON loi dich          re nhat, ⛔ khong dung tieng
    2 PHAN PHOI LAI thoi gian   dung khoang lang THAT
    3 GIAN / NEN giong          dat nhat — nghe ra ngay

Do tren ba phim (`bang_chung/d5_can_nan/`): **73,9 %** khe ⛔ khong chua noi loi
dich; trong so ay he so can nen **trung vi 1,33x, p95 1,96x**. Ma tran tang toc
cua ta la **1,15** (`thoi_gian.TRAN_TANG_TOC`) ⇒ 🔴 can gat 3 **mot minh ⛔ khong
du cho qua nua**. Do la ly do thu tu nay la **bat buoc**.

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

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

#: Toc do noi cua giong TTS ta dang dung, am tiet/giay.
#: ⭐ DO tren 18 doan TTS that (`fix_toc_do/vong_dau_moi_v*.json`:
#: `am_tiet / giay_am`), trung vi; dai [3,00 ; 3,71].
#: ⛔ Khong phai 9 ky tu/giay cua Netflix — do la toc do **DOC** cua phu de.
AM_TIET_MOI_GIAY = 3.284

#: Khe ngan nhat con nghe ra la mot cau. Netflix TTSG *General Requirements*
#: (bai 215758617): *"Minimum duration: 5/6 of a second"*.
#: ⚠️ Muon vi no la **gioi han tri giac**, ⛔ khong phai gioi han doc — nen no
#:    chuyen duoc sang long tieng. `min_subtitle_duration 2.5` cua VideoLingo
#:    thi ⛔ KHONG: do la thoi gian de **mat doc xong mot dong**.
KHE_TOI_THIEU_S = 5.0 / 6.0


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


# ── Can gat 1: RUT GON (di qua LLM — ⛔ ham o NGOAI) ─────────────────────────

def can_gat_1_rut_gon(
    khes: Sequence[Khe], *, tran_tang_toc: float,
    rut_gon: Callable[[Sequence[Khe]], dict[str, int]],
) -> list[Khe]:
    """Chi xin rut gon cho khe **that su khong vua**.

    `rut_gon` nhan danh sach khe can xu ly va tra `{ma: am_tiet_moi}`.
    ⭐ No o NGOAI vi no di qua LLM ⇒ ⛔ khong tai lap duoc; moi phep do dung no
       phai chay **>= 3 luot** va bao **trung vi + khoang**, ⛔ khong mot con so.

    ⛔ Khong bao gio de so am tiet **tang**: mot ban "rut gon" dai hon ban goc la
       mot ban dich khac, ⛔ khong phai mot phep rut gon — giu ban cu va khai ra.
    """
    can = [k for k in khes
           if xep_bac(k, tran_tang_toc=tran_tang_toc) > BacNan.BINH_THUONG]
    if not can:
        return list(khes)
    moi = rut_gon(can) or {}
    ra = []
    for k in khes:
        n = moi.get(k.ma)
        ra.append(replace(k, am_tiet=n) if n and 0 < n < k.am_tiet else k)
    return ra


# ── Can gat 2: PHAN PHOI LAI (⛔ khong dung tieng) ───────────────────────────

def can_gat_2_phan_phoi(khes: Sequence[Khe], *, tran_tang_toc: float) -> list[Khe]:
    """🔴 **CAN GAT NAY DA CHET (25/09) — ⛔ KHONG goi o duong san pham.**

    Do that (`bang_chung/d5_khoang_lang/`, VAD tren ba phim):

        muon duoc giua hai khe: **13,28 s** tren **14/185** ranh gioi,
        trung vi **0,0 s** — o ban ROSNG RAI NHAT (`pad_s=0`).

    Va phep do tat dinh (`R4 §15.3`) doc lap cho cung ket luan: no dong
    them **2 khe (1,1 %)** va con LAM TANG so khe phai dung toi giong.

    ⭐ Ly do: `cat_doan` cat tai dau cau theo moc tu ⇒ moi khoang im roi
       **VAO TRONG** mot khe. Lang co that (17,7 / 44,7 / 74,4 s) nhung
       ⛔ khong nam **giua** cac khe ⇒ can gat 2 ⛔ khong voi toi duoc.

    ⛔ Giu ham lai **kem phan quyet nay** thay vi xoa: mot lan sau doi cach
       cat doan (de lai ho that giua cac khe) thi no song lai — va luc ay
       phai **DO LAI**, ⛔ khong phai tin dong chu nay.

    Khe thieu cho **muon** khoang lang cua khe lien sau.

    ⭐ Muon cach suy cua VideoLingo (`tol_dur = duration + tolerance`) nhung
       ⛔ KHONG muon `tolerance = 1.5 s`: ta lay **dung phan dang trong**, vi
       `moc_sau` cua ta da la bien co that ke tiep (open-dubbing) chu khong phai
       mot hang so. ⇒ ⛔ Khong co so nao de chep.

    ⛔ Chi day `moc_sau` cua khe truoc VA `bat` cua khe sau di kem — hai ve cua
       CUNG mot phep muon. Khe sau chi nhuong phan no ⛔ khong dung toi, va luon
       giu lai it nhat `KHE_TOI_THIEU_S`.
    """
    ra = list(khes)
    for i in range(len(ra) - 1):
        nay, sau = ra[i], ra[i + 1]
        thieu = nay.giay_can() / tran_tang_toc - nay.ngan_sach_s
        if thieu <= 0:
            continue
        du = sau.ngan_sach_s - max(sau.giay_can() / tran_tang_toc, KHE_TOI_THIEU_S)
        nhuong = min(thieu, max(0.0, du))
        if nhuong <= 0:
            continue
        ra[i] = replace(nay, moc_sau=nay.moc_sau + nhuong)
        ra[i + 1] = replace(sau, bat=sau.bat + nhuong)
    return ra


# ── Can gat 4: GOP KHE — re nhat trong tat ca, ⛔ KHONG cham ban dich ────────

#: Tran ky tu cua MOT luot doc. Phai khop `ltt_voice.tham_so_cong_khai.
#: TRAN_MOI_LUOT_SINH` — do la tran CHAT LUONG (giong bat dau troi), ⛔ khong
#: phai tran ky thuat. ⭐ Chinh no bat duoc ban suy bien "gop tu do" (xem duoi).
TRAN_KY_TU_MOT_LUOT = 1500

#: Toi da bao nhieu khe duoc gop lam mot. ⭐ Muon CACH SUY cua VideoLingo
#: (`MAX_MERGE_COUNT = 5`, `core/_8_2_dub_chunks.py:12`) — ⛔ va o day con so
#: cung bang 5 vi **do tren du lieu cua ta** cho thay no la diem dung hop ly:
#:
#:      gop <=3  -> 33,3 % khe con phai nen > 1,15 · khe dai nhat 15,7 s
#:      gop <=5  -> 26,5 %                          · khe dai nhat 20,8 s
#:      TU DO    ->  5,1 % 🔴 NHUNG khe dai nhat 189,96 s, van ban 3.535 ky tu
#:                   => VUOT `TRAN_KY_TU_MOT_LUOT` => may doc TU CHOI
TRAN_GOP_KHE = 5


def gop_khe(khes: Sequence[Khe], *, tran_tang_toc: float,
            tran_gop: int = TRAN_GOP_KHE,
            tran_ky_tu: int = TRAN_KY_TU_MOT_LUOT) -> list[Khe]:
    """Gop khe lien ke cho toi khi khe VUA, toi da `tran_gop` khe.

    ⭐ **Re nhat trong ca bon can gat**: no ⛔ khong cham mot chu nao cua ban
       dich (⇒ **0 diem chrF++**), ⛔ khong goi LLM, va ⛔ khong gay troi giong
       (`R4 §20`: khe gop dai nhat 427 ky tu, cach tran troi 1.500 **3,5 lan**;
       va `do_bai_dai.py` cho thay ban GHEP **tot hon** ban mot luot).

    Do tren ba phim: ti le khe phai nen > 1,15 tu **55,6 % xuong 26,5 %** —
    hon MOT NUA bai toan, mien phi.

    🔴 **HAI CHOT, va chot thu hai da CUU mot lan roi:**

      1. `tran_gop` — ⛔ khong gop vo han.
      2. `tran_ky_tu` — ⛔ khong bao gio de mot khe vuot tran cua may doc.

    ⚠️ Bo `tran_gop` (gop "tu do") cho mot bang so **dep hon** (p95 1,171 so voi
       1,559) nhung no nhoi **74 khe vao MOT**, khe dai **189,96 s**, van ban
       **3.535 ky tu** — `giong_noi.doc_mot_doan` se **TU CHOI**. ⇒ Mot ban
       suy bien deo mat mot ket qua tot. Chinh `tran_ky_tu` o day bat duoc no.

    ⛔ **KHONG gop qua ranh gioi CANH?** — da do va **BAC BO**: `R4 §19`,
       **80,9 %** khe dang chay DA vat qua cat canh (co khe vat qua 4 cat), va
       san pham la **thuyet minh MOT giong** nen cat canh ⛔ khong phai cho ngat
       loi. Rang buoc ay dung cho long tieng NHAN VAT tren hinh (`N-34`).
    """
    ra: list[Khe] = []
    i = 0
    n = len(khes)
    while i < n:
        goc = khes[i]
        am_tiet, chu, moc_sau, d = goc.am_tiet, goc.chu, goc.moc_sau, 1
        while (d < tran_gop and i + d < n
               and xep_bac(replace(goc, am_tiet=am_tiet, moc_sau=moc_sau),
                           tran_tang_toc=tran_tang_toc) > BacNan.BINH_THUONG):
            ke = khes[i + d]
            chu_moi = f"{chu} {ke.chu}".strip()
            if len(chu_moi) > tran_ky_tu:
                break          # ⛔ CHOT: vuot tran may doc thi DUNG, khai ra
            am_tiet += ke.am_tiet
            chu, moc_sau = chu_moi, ke.moc_sau
            d += 1
        ra.append(replace(goc, am_tiet=am_tiet, chu=chu, moc_sau=moc_sau,
                          ket=khes[i + d - 1].ket))
        i += d
    return ra


# ── Can gat 3: GIAN / NEN (dat nhat) ────────────────────────────────────────

def can_gat_3_he_so(khe: Khe, *, tran_tang_toc: float) -> float:
    """He so toc do can, da **kep** vao tran. `1.0` = ⛔ khong dung toi giong.

    ⚠️ Gia dinh: am thanh TTS **da cat lang thua o duoi** truoc khi goi ham nay
       (open-dubbing `_convert_text_to_speech_without_end_silence`). Tinh he so
       tren mot tep con lang duoi la **nen giong de ep mot khoang im** — vo nghia
       va nghe ra ngay.
    """
    ns = khe.ngan_sach_s
    if ns <= 0:
        return tran_tang_toc
    return min(tran_tang_toc, max(1.0, khe.giay_can() / ns))


def con_khong_vua(khes: Sequence[Khe], *, tran_tang_toc: float) -> list[Khe]:
    """Khe ma **ca ba** can gat van ⛔ khong cuu duoc. ⭐ Khai ra, ⛔ khong giau."""
    return [k for k in khes
            if xep_bac(k, tran_tang_toc=tran_tang_toc) == BacNan.QUA_NHANH]
