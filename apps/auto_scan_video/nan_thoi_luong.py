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

## ⚠️ Da NOI mot phan (25/09) — BAO CAO, ⛔ CHUA doi duong sinh tieng that

`giai_doan_giong.chay()` goi `gop_khe` that de tinh `so_khe_neu_gop` trong
`tom_tat`, tren DU LIEU that cua tung lan chay. Do KHONG phai mot loi goi dat
cho co: no la cau tra loi cho *"gop duoc bao nhieu"* tren chinh video khach vua
xu ly, va no chay MOI lan `voice_synthesis` chay.

🔴 Nhung no **CHUA doi** so tep tieng thuc te duoc sinh ra. Ly do la mot rang
   buoc CO THAT, khong phai ngai kho: `giai_doan_thoi_gian.py:88-89` doi
   **MOI** `ma` trong `content.json` (`CONTENT_PROCESS`, ghi TRUOC va DOC LAP
   voi `voice_synthesis`) phai co **mot** dong `giay` trong `ban_ke.json`
   (`voice_synthesis`), va nem `ThoiGianError('Doan {ma} chua co tieng.')`
   (`thoi_gian.py:182-184`) neu thieu. Gop nhieu doan lam MOT tep tieng trong
   `voice_synthesis` ma khong doi CA `giai_doan_noi_dung.py` (de `content.json`
   sinh ra da GOP san) lan `thoi_gian.lap_ke_hoach`/`_dung_ban_phoi` (de biet
   mot nhom da gop dung CHUNG mot tep am thanh) se lam **vo** pha 16/17 (ADR-003)
   tren MOI lan chay that co gop — khong phai mot rui ro, ma la mot loi CHAC CHAN.

   ⇒ Dieu kien noi THAT (doi tep tieng sinh ra): sua dong bo ca ba tep
   (`giai_doan_noi_dung.py`, `giai_doan_thoi_gian.py`, `thoi_gian.py`) VA doi
   chieu bang mot luot TTS that — dung viec `R4_TIMELINE_NOI_BO.md` §21.5 da
   ghi la dang bi CHAN ("Ca B va C deu can mot luot nang; B can TTS, dang
   chan"). Do la mot ke hoach rieng, ⛔ khong phai phan viec cua lan nay.

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

#: Toc do noi cua giong TTS ta dang dung, am tiet/giay.
#: ⭐ DO tren 18 doan TTS that (`fix_toc_do/vong_dau_moi_v*.json`:
#: `am_tiet / giay_am`), trung vi; dai [3,00 ; 3,71].
#: ⛔ Khong phai 9 ky tu/giay cua Netflix — do la toc do **DOC** cua phu de.
#: ⚠️ 25/09: `ngon_ngu.NHIP[VI]` (3,35, do lai 23/09/2026 tren chinh giong san
#:    pham) la con so **moi hon** cho CUNG dai luong. Hang nay CHUA doi chieu
#:    lai voi no — ai dung `xep_bac`/`gop_khe` cho mot quyet dinh that (⛔ khong
#:    phai bao cao) phai doi chieu TRUOC. Xem `test_2062_toc_do_noi_la_so_DO_DUOC`.
AM_TIET_MOI_GIAY = 3.284


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

    ⭐ **Re hon nan_cho_vua**: no ⛔ khong cham mot chu nao cua ban
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
