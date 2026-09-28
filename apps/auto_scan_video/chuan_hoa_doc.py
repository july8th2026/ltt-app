"""Chuan hoa van ban tieng Viet TRUOC KHI dua vao TTS (N7, lan L7, xem
docs/auto_scan_video_final/B14_SO_SANH_VIRAL/V4_GIONG_AM.md hang N7).

CHUA DUOC NOI VAO DUONG SAN PHAM. `giai_doan_giong.py` thuoc lan L1 dang chay
song song -- tep nay CHI la ham THUAN + test, se duoc noi sau khi L1 xong.
Khong import, khong sua bat ky tep dang co nao trong `apps/auto_scan_video/`.

## Vi sao co tep nay

`D:\\Viral\\resources\\app-src\\localize.py:44-66` dan `tts_chuan_hoa.py` (port
NghiTTS) truoc khi dua van ban vao TTS. ASV (`giai_doan_giong.py`) hien dua ban
dich vao `ltt_voice` gan nhu tho o mot vai cho -- day la phan LAP khoang trong
do, khong thay the `apps/ltt_voice/text_pipeline.py` (da co so/ngay/gio/%/tien
VND-USD + phien am Anh->Viet, xem V4_GIONG_AM.md hang "Chuan hoa so/ngay/gio...").

## Luat lay/bo (chot 28/09: LAY NGUYEN luat cua Viral, KHONG hieu chinh nguong)

Chu du an chot 28/09: moi phep muon tu `tts_chuan_hoa.py` thi lay NGUYEN ca
nguong nho (vd "so La Ma >= 2 ky tu") -- khong dung lai de do them, vi moi
nguong cua ho sinh ra tu MOT LAN TTS doc sai nghe thay duoc (bang chung ta
khong the tu tao re hon). Chi loai mot phep khi TIEN DE cua no khong dung voi
ta (vd phep cho nguon tieng Anh, trong khi nguon ASV la tieng Trung).

Toan bo phep cua `tts_chuan_hoa.py` (176 dong, doc TRON), lay/bo tung phep:

  1. Xoa dau cham ngan cach nghin (1.000.000->1000000)        -- BO
  2. Ngay/gio (dd/mm/yyyy, hh:mm, hh'h'mm)                    -- BO
  3. SO LA MA >=2 KY TU (tts_chuan_hoa.py:86-100,126-130)     -- LAY (ham nay)
  4. Tien te ($/eur/dong-VND-VNĐ)                              -- BO
  5. Phan tram (kem khoang A-B%)                                -- BO
  6. Thap phan (dau PHAY = thap phan tieng Viet)                -- BO
  7. Khoang so A-B -> "A den B"                                 -- BO
  8. SO DIEN THOAI 0 + 9-10 so (tts_chuan_hoa.py:151-152)       -- LAY (ham nay)
  9. So am (-N -> am N)                                         -- BO
  10. So nguyen con lai -> chu                                  -- BO

  Ly do BO (2,4-7,9,10) -- KHONG phai hieu chinh nguong, ma vi TIEN DE "chua
  co gi tuong duong" SAI voi ta: `apps/ltt_voice/text_pipeline.py` DA co doc
  so/ngay/gio/%/tien-VND-USD (xac nhan trong V4_GIONG_AM.md, hang "Chuan hoa
  so/ngay/gio/tien/% ... KHAC THIET KE (da co tuong duong)"). Chong them MOT
  lop doc-so THU HAI o day se (a) doc HAI LAN cung mot cum so (thu tu ap dung
  khong xac dinh giua hai ham doc lap), (b) khong co gia tri moi -- V4 doc chi
  xac nhan HAI khoang trong CU THE la so La Ma va SDT (hang "... cung hang
  muc tren -- HAI khoang trong cu the").

  Rieng vietnormalizer (`localize.py:56-66`, phien am Anh->Viet iPhone->ai-phon)
  -- BO cung ly do: `text_pipeline.py` da co truong `phien_am` (V4_GIONG_AM.md
  dong 47-48). Va tien de cua no la nguon TIENG ANH lot vao cau -- nguon ASV la
  TIENG TRUNG, hinh dang lot vao la CHU HAN chu khong phai tu Latin, nen day
  cung la mot cho TIEN DE khac (xem hang muc Han-lot ben duoi).

## Hang muc TA TU THEM (KHONG co trong tts_chuan_hoa.py -- phai khai ro)

  A. LUOI THU HAI CHO CHU HAN LOT O TANG TTS -- co that ben Viral, nhung
     KHONG nam trong `tts_chuan_hoa.py` ma trong `localize.py:293-301` (ham
     `_chuan_hoa_tts`), nguyen van:

         "NET CHONG 'TTS Viet doc chu Trung' (bug khach bao): dich Gemini fail
         giua chung -> vi fallback ve zh (chu Han) o nhieu nhanh (4272 batch /
         4332 / 4427 / 4437). Cue CHU YEU chu Han (>=35%) = CHUA DICH -> tra
         RONG -> TTS Viet BO QUA (im lang) thay vi doc chu Han bang giong Viet
         (loi). Env HAN_NET_NGUONG chinh nguong"

     `_ty_le_han` dung y het (`localize.py:69-76`): ti le ky tu trong hai dai
     Unicode CJK (U+4E00-9FFF, U+3400-4DBF) tren TONG ky tu khong-phai-khoang-
     trang. Ta LAY NGUYEN nguong 0.35 va cach tinh ti le nay (khong tu hieu
     chinh) -- day la BANG CHUNG that tu Viral, khong phai ta tu doan.

     HANH DONG thi TA DOI, va day KHONG phai hieu chinh nguong: Viral tra
     CHUOI RONG (xoa het cau) khi vuot nguong. Luat brief giu nguyen "khong
     bao gio lam MAT noi dung" dung TREN luat "lay nguyen cua Viral" -- nen
     ham o day CHI PHAT HIEN (gan co vao danh sach phep da ap), KHONG xoa mot
     ky tu nao. Quyet dinh lam gi voi cau bi gan co (bo lai dich, log canh
     bao, hay tiep tuc doc) la viec cua lop GOI (L1), khong phai cua ham thuan
     nay. Ta cung CHUA co luoi nay o tang TTS (chi co `LY_DO_HAN_LOT` +
     `ngon_ngu.ty_le_chu_han` o tang VAN BAN, trong `giai_doan_noi_dung.py` --
     truoc VOICE_SYNTHESIS) -- day la khoang trong that, khong phai viec dung.

  B. Dau cau Trung con lot (，。！？、) -- KHONG co trong `tts_chuan_hoa.py`,
     TA TU DAT vi cac dau nay khong phai dau cau tieng Viet va co the lot qua
     neu ban dich giu nguyen dau nguon; nguong/danh sach dau la TA TU CHON
     (khong phai bang chung do tu Viral), pham vi CHI 4 dau brief neu ten
     ("，。！？、") de tranh "chep ca goi".

## Luat thiet ke (bat buoc theo brief)

  - Ham THUAN: str vao, str ra + list[str] phep da ap; KHONG I/O, KHONG model,
    KHONG trang thai module-level thay doi giua cac lan goi.
  - KHONG BAO GIO xoa noi dung -- chi doi CACH VIET. Phep nao co the xoa chu
    (nhu net Han cua Viral) thi CHUYEN THANH phat hien, khong xoa.
  - Moi phep MOT ham co TEN (khong mot regex khong lo gop het).
  - Van ban da sach -> ra Y HET dau vao, tung ky tu; cau toan tieng Viet ->
    danh sach phep RONG.
"""
from __future__ import annotations

import re
from typing import List, NamedTuple

# ============================================================================
# Ket qua chung: van ban sau chuan hoa + danh sach TEN phep da thuc su ap dung
# (moi lan mot phep doi duoc mot cho la MOT phan tu, de outputs dem duoc).
# ============================================================================


class KetQuaChuanHoa(NamedTuple):
    van_ban: str
    phep_da_ap: List[str]


TEN_PHEP_SO_LA_MA = "so_la_ma"
TEN_PHEP_SO_DIEN_THOAI = "so_dien_thoai"
TEN_PHEP_DAU_CAU_TRUNG = "dau_cau_trung"
TEN_PHEP_HAN_LOT_TANG_TTS = "phat_hien_han_lot_tang_tts"

# ============================================================================
# 1) SO LA MA >= 2 KY TU -- port tts_chuan_hoa.py:13-74 (doc_so) + :86-100,
#    126-130 (nhan dien + thay). Lay NGUYEN quy tac cua ho: chi doi chuoi
#    >=2 ky tu La Ma HOP LE, dung tu-bien(word-boundary) rong ca chu co dau
#    tieng Viet -- "tranh nham 'I','V','X' le trong ten/viet tat" (nguyen van
#    comment tts_chuan_hoa.py:86).
# ============================================================================

#: tts_chuan_hoa.py:13 -- 10 chu so, giu NGUYEN dau (day la NOI DUNG doc ra
#: cho TTS, khac voi cac dong # comment trong tep nay).
_CHU_SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _doc_nhom_3(n: int, day_du: bool) -> str:
    """Doc nhom 0-999. Port tts_chuan_hoa.py:17-40 (_doc_3), giu nguyen quy
    tac 'mot/tu/lam/le/muoi'. day_du=True ep 'tram'+'le' (nhom KHONG phai
    nhom cao nhat cua so nhieu chu so)."""
    tram, rem = divmod(n, 100)
    chuc, dvi = divmod(rem, 10)
    parts = []
    if tram > 0 or day_du:
        parts.append(_CHU_SO[tram] + " trăm")
    if chuc == 0:
        if dvi > 0:
            parts.append(("lẻ " + _CHU_SO[dvi]) if (tram > 0 or day_du) else _CHU_SO[dvi])
    elif chuc == 1:
        parts.append("mười" if dvi == 0 else ("mười lăm" if dvi == 5 else "mười " + _CHU_SO[dvi]))
    else:
        s = _CHU_SO[chuc] + " mươi"
        if dvi == 1:
            s += " mốt"
        elif dvi == 4:
            s += " tư"
        elif dvi == 5:
            s += " lăm"
        elif dvi > 0:
            s += " " + _CHU_SO[dvi]
        parts.append(s)
    return " ".join(parts).strip()


def _doc_so_toi_3999(n: int) -> str:
    """So nguyen 0..3999 -> chu tieng Viet. GIOI HAN 3999 co chu dich: day la
    NHANH DUY NHAT dung ham nay (doc gia tri so La Ma), va so La Ma lon nhat
    hop le la MMMCMXCIX = 3999 -- khong mo rong len nghin/trieu/ty vi khong
    co duong goi nao dua gia tri lon hon toi day (ma phong thu cho ca khong
    the xay ra, xem MEMORY.md muc "ma phong thu cho ca khong the xay ra")."""
    if n == 0:
        return "không"
    nghin, con_lai = divmod(n, 1000)
    if nghin == 0:
        return _doc_nhom_3(con_lai, False)
    phan_nghin = _doc_nhom_3(nghin, False) + " nghìn"
    if con_lai == 0:
        return phan_nghin
    return (phan_nghin + " " + _doc_nhom_3(con_lai, True)).strip()


#: tts_chuan_hoa.py:87 -- gia tri chu La Ma.
_GIA_TRI_LA_MA = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

#: tts_chuan_hoa.py:92 -- regex kiem chuoi La Ma HOP LE (tu choi "IIII", "VV"...).
_MAU_LA_MA_HOP_LE = re.compile(
    r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})"
)

#: tts_chuan_hoa.py:130 -- chi doi chuoi >=2 ky tu, KHONG dung sat chu/so
#: khac (ASCII \\w) LAN chu co dau tieng Viet (dai À-ỹ) -- giu dung bien Viral
#: da dung de "tranh nham 'I','V','X' le trong ten/viet tat".
_MAU_TIM_LA_MA = re.compile(r"(?<![\wÀ-ỹ])([IVXLCDM]{2,})(?![\wÀ-ỹ])")


def _gia_tri_la_ma(chuoi: str):
    """Port tts_chuan_hoa.py:90-100 (_roman_to_int). None = khong phai so La
    Ma hop le (vd 'IIII', 'VV') -> GIU NGUYEN chu, khong doi."""
    s = chuoi.upper()
    if not s or not _MAU_LA_MA_HOP_LE.fullmatch(s):
        return None
    tong = 0
    truoc = 0
    for c in reversed(s):
        v = _GIA_TRI_LA_MA[c]
        tong += -v if v < truoc else v
        truoc = max(truoc, v)
    return tong


def chuan_hoa_so_la_ma(van_ban: str) -> KetQuaChuanHoa:
    """Doi so La Ma (>=2 ky tu HOP LE, dung tu-bien) sang chu tieng Viet.

    Doi chung AM (theo dung yeu cau brief):
      - "I" dung MOT MINH (dai tu tieng Anh? mot muc danh sach?) -- KHONG
        doi, vi mau chi khop chuoi >=2 ky tu.
      - Chuoi La Ma KHONG hop le (vd "IIII") -- GIU NGUYEN, khong doi (tra
        None tu _gia_tri_la_ma).
    """
    phep_da_ap: List[str] = []

    def _thay(m: "re.Match") -> str:
        gia_tri = _gia_tri_la_ma(m.group(1))
        if gia_tri is None:
            return m.group(0)
        phep_da_ap.append(TEN_PHEP_SO_LA_MA)
        return _doc_so_toi_3999(gia_tri)

    ket_qua = _MAU_TIM_LA_MA.sub(_thay, van_ban)
    return KetQuaChuanHoa(ket_qua, phep_da_ap)


# ============================================================================
# 2) SO DIEN THOAI -- port tts_chuan_hoa.py:82-83 (_doc_tung_so) + :151-152.
#    "0 + 9-10 so -> doc TUNG SO, khong doc thanh mot so nguyen khong lo"
#    (nguyen van y comment tts_chuan_hoa.py:151).
# ============================================================================

#: tts_chuan_hoa.py:152 -- 0 roi 9-10 chu so, dung tu-bien (\\b hai dau, y het
#: nguon: khong bi dinh vao chu/so khac).
_MAU_SO_DIEN_THOAI = re.compile(r"\b0\d{9,10}\b")


def _doc_tung_chu_so(chuoi_so: str) -> str:
    """Port tts_chuan_hoa.py:82-83 (_doc_tung_so)."""
    return " ".join(_CHU_SO[int(c)] for c in chuoi_so if c.isdigit())


def chuan_hoa_so_dien_thoai(van_ban: str) -> KetQuaChuanHoa:
    """Doi so dien thoai (0 + 9-10 chu so) sang doc tung so."""
    phep_da_ap: List[str] = []

    def _thay(m: "re.Match") -> str:
        phep_da_ap.append(TEN_PHEP_SO_DIEN_THOAI)
        return _doc_tung_chu_so(m.group(0))

    ket_qua = _MAU_SO_DIEN_THOAI.sub(_thay, van_ban)
    return KetQuaChuanHoa(ket_qua, phep_da_ap)


# ============================================================================
# 3) DAU CAU TRUNG CON LOT -- TA TU THEM (KHONG co trong tts_chuan_hoa.py).
#    Doi 1-doi-1 sang dau Latin/Viet tuong duong -- day la DOI CACH VIET,
#    KHONG mat ky tu nao (moi dau van con, chi doi hinh dang).
# ============================================================================

#: Pham vi CHI 4 dau brief neu ten, tranh "chep ca mot bang dau cau CJK".
_DAU_CAU_TRUNG = {
    "，": ",",
    "。": ".",
    "！": "!",
    "？": "?",
    "、": ",",
}
_MAU_DAU_CAU_TRUNG = re.compile("|".join(re.escape(k) for k in _DAU_CAU_TRUNG))


def chuan_hoa_dau_cau_trung(van_ban: str) -> KetQuaChuanHoa:
    """Doi dau cau Trung con lot (，。！？、) sang dau Latin/Viet tuong duong.

    Doi chung AM: cau toan tieng Viet (khong co dau nao trong bang) -> khong
    doi gi, danh sach phep rong.
    """
    phep_da_ap: List[str] = []

    def _thay(m: "re.Match") -> str:
        phep_da_ap.append(TEN_PHEP_DAU_CAU_TRUNG)
        return _DAU_CAU_TRUNG[m.group(0)]

    ket_qua = _MAU_DAU_CAU_TRUNG.sub(_thay, van_ban)
    return KetQuaChuanHoa(ket_qua, phep_da_ap)


# ============================================================================
# 4) LUOI THU HAI CHO CHU HAN LOT O TANG TTS -- PHAT HIEN, KHONG XOA.
#    Nguong 0.35 va cach tinh ti le LAY NGUYEN tu localize.py:69-76,293-301
#    (_ty_le_han + _chuan_hoa_tts) -- xem trich dan day du o docstring dau
#    tep. HANH DONG (phat hien thay vi xoa) la cho TA DOI, da khai ro o tren.
# ============================================================================

#: localize.py:74 -- hai dai CJK dung de tinh _ty_le_han (KHONG gom kana/
#: hangul -- do la dai rieng cua _co_kana, ham khac, ho khong dung no o luoi
#: TTS nay).
_KHOANG_HAN = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF))

#: localize.py:295 -- nguong mac dinh cua HAN_NET_NGUONG, LAY NGUYEN.
NGUONG_HAN_LOT_TANG_TTS = 0.35


def _la_ky_tu_han(k: str) -> bool:
    n = ord(k)
    return any(a <= n <= b for a, b in _KHOANG_HAN)


def _ty_le_han(van_ban: str) -> float:
    """Port y het localize.py:69-76 (_ty_le_han): so ky tu Han tren TONG ky
    tu khong-phai-khoang-trang (KHONG loai dau cau nhu ngon_ngu.ty_le_chu_han
    -- day la ban port dung cua Viral, giu nguyen mau so de nguong 0.35 con
    dung y nghia da do)."""
    s = (van_ban or "").strip()
    if not s:
        return 0.0
    han = sum(1 for c in s if _la_ky_tu_han(c))
    tong = sum(1 for c in s if not c.isspace())
    return (han / tong) if tong else 0.0


def phat_hien_han_lot_tang_tts(van_ban: str) -> KetQuaChuanHoa:
    """Co ban dich con >= NGUONG_HAN_LOT_TANG_TTS (0.35, lay nguyen tu Viral)
    ty le chu Han khong? CHI PHAT HIEN -- van ban tra ve LUON GIONG HET dau
    vao, ke ca khi phat hien (khac Viral: ho xoa trang cau, ta khong duoc
    lam mat noi dung). Neu phat hien, TEN_PHEP_HAN_LOT_TANG_TTS xuat hien
    trong danh sach phep -- lop GOI (L1) tu quyet dinh lam gi tiep (vd bo
    lai dich, ghi log, hay van doc).
    """
    if _ty_le_han(van_ban) >= NGUONG_HAN_LOT_TANG_TTS:
        return KetQuaChuanHoa(van_ban, [TEN_PHEP_HAN_LOT_TANG_TTS])
    return KetQuaChuanHoa(van_ban, [])


# ============================================================================
# HAM TONG: chay ca 4 phep theo thu tu co dinh, gop danh sach phep da ap.
# ============================================================================


def chuan_hoa_truoc_tts(van_ban: str) -> KetQuaChuanHoa:
    """Chay tron bo phep chuan hoa (dau cau Trung -> so La Ma -> SDT -> phat
    hien Han lot) va gop danh sach phep da ap. Thu tu: doi dau cau truoc (doc
    lap voi hai phep so), roi so La Ma va SDT (doc lap voi nhau -- La Ma dung
    chu cai IVXLCDM, SDT dung chu so, khong giao nhau), phat hien Han lot
    CUOI CUNG vi no doc van ban KET QUA sau cac buoc doi cach viet o tren.

    KHONG BAO GIO lam mat noi dung: van ban dau vao da sach (khong co ca 4
    hinh dang tren) -> ra Y HET dau vao, tung ky tu; danh sach phep RONG.
    """
    van_ban_hien_tai = van_ban
    phep_da_ap: List[str] = []

    for ham in (
        chuan_hoa_dau_cau_trung,
        chuan_hoa_so_la_ma,
        chuan_hoa_so_dien_thoai,
    ):
        ket_qua = ham(van_ban_hien_tai)
        van_ban_hien_tai = ket_qua.van_ban
        phep_da_ap.extend(ket_qua.phep_da_ap)

    ket_qua_han = phat_hien_han_lot_tang_tts(van_ban_hien_tai)
    phep_da_ap.extend(ket_qua_han.phep_da_ap)

    return KetQuaChuanHoa(van_ban_hien_tai, phep_da_ap)
