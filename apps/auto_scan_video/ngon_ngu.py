"""Hop dong NGON NGU cua Auto Scan Video — mot cho tra loi, moi giai doan hoi.

Chu du an chot 22/09/2026 (phien `asv-final`):

    nguon ∈ {zh, en, vi}      dich ∈ {vi, en}      nguon ≠ dich

## Vi sao dich chi co hai

San pham la **mot giong thuyet minh** doc ban dich. LTT Voice (VieNeu-TTS v3
Turbo) co hai LAN that — `apps/ltt_voice/lan_ngon_ngu.LAN_HOP_LE` — nen tap
dich la **chinh tap lan cua may sinh tieng**, khong phai mot lua chon rieng.
`_kiem()` o cuoi tep chot dieu do: them mot dich ma may sinh tieng khong co lan
la mot loi luc import, khong phai mot lan chay hong o giai doan GIONG.

## Vi sao nguon co `zh`

Video nghiem thu cua chu du an la Douyin tieng Trung (`Desktop\\TEST VIDEO`).
`zh` chi di vao phia NGUON: ASR doc no, OCR doc hardsub chu Han, LLM dich no.
Khong co giong `zh`, nen `zh` khong bao gio la dich.

⛔ Khong mo rong thanh "da ngon ngu tong quat". Mot ngon ngu moi o day la mot bo
   bang chung moi (ASR, dich, QC dich, giong) — khong phai mot dong cau hinh.
"""
from __future__ import annotations

from platform_core.i18n import N_, _ as _t

from apps.ltt_voice.lan_ngon_ngu import LAN_HOP_LE as _LAN_GIONG

ZH = "zh"
EN = "en"
VI = "vi"

#: Khach khong khai nguon ⇒ ASR tu doan, roi `kiem_nguon_da_doan` chot lai.
TU_DOAN = "auto"

NGUON_HOP_LE: tuple[str, ...] = (ZH, EN, VI)
DICH_HOP_LE: tuple[str, ...] = (VI, EN)
DICH_MAC_DINH = VI

#: Nhan cho KHACH doc. `N_` = danh dau de trich, dich o cho dung (cung khuon
#: `ltt_voice.lan_ngon_ngu.NHAN_LAN`).
NHAN = {ZH: N_("Tiếng Trung"), EN: N_("Tiếng Anh"), VI: N_("Tiếng Việt")}

# ══════════════════════════════════════════════════════════════════════════════
#  NHIP DOC — mot con so, DO DUOC, va moi loi nhac tinh ra tu no
# ══════════════════════════════════════════════════════════════════════════════

#: Don vi dem do dai cua mot cau, theo lan dich.
#:
#: ⭐ Tieng Viet dem **am tiet** vi chinh ta cua no la am tiet roi: moi am tiet
#:    mot tu, nen "dem tu cach nhau bang khoang trang" va "dem am tiet" la CUNG
#:    mot phep. Tieng Anh dem **tu**, va do la don vi moi bang nhip thuyet minh
#:    tieng Anh deu dung.
DON_VI_DO_DAI = {VI: "am tiet", EN: "tu"}

#: 🔑 **Nhip doc THAT cua may sinh tieng, don vi `DON_VI_DO_DAI` moi giay.**
#:
#: 🔴 `vi` = 3,35 — **DO DUOC 23/09/2026**, va con so cu (4,5) da lam hong mot
#:    lan chay that.
#:
#:    `tools/do_toc_do_giong.py --che-do tts` doc sau doan tieng Viet THAT cua
#:    luot nghiem thu nen v3 bang chinh giong cua luot ay (`Minh Duc`, LTT Voice
#:    sidecar that):
#:
#:        seg_0001 3,04 · seg_0002 3,33 · seg_0003 3,37
#:        seg_0004 3,42 · seg_0005 3,44 · seg_0006 3,51   am tiet/giay
#:        trung binh 3,35 · do lech chuan 0,16
#:
#:    Loi nhac khi ay noi "khoang 4,5 am tiet/giay". `4,5 / 3,35 = 1,34`, nen
#:    **moi cau cua luot viet dau deu dai hon khe ~34% theo dung thiet ke** —
#:    do duoc o sau doan ay: +27,8% · +31,1% · +39,7% · +44,1% · +47,4% · +50,8%.
#:
#: ⛔ Hau qua khong phai "hoi dai": no la 11 luot `rut_ngan_cho_vua` (50.144
#:    token) + 11 luot doc lai, tuc **751 trong 943 giay** cua giai doan GIONG.
#:    Mot hang so sai 34% o dau chuoi tra gia o cuoi chuoi, nhan len bang tien.
#:
#: ⚠️ `en` = 2,6 (155 tu/phut, nhip thuyet minh tieng Anh thong dung) **CHUA DO**
#:    tren may sinh tieng nay. Giu nguyen so cu va NOI RO no chua do — doi no
#:    theo cam tinh la lap lai dung cai bay vua go. Do bang cung mot cong cu khi
#:    duong `en` co mot luot chay that.
NHIP: dict[str, float] = {VI: 3.35, EN: 2.6}

#: Nham THAP hon khe mot chut, va **mot con so cho ca hai pha**.
#:
#: ⭐ Vua khit la vua **du** de mot dao dong nho cua may sinh tieng lam cau tran
#:    ra lai. Voi `NHIP[vi]` = 3,35 va bien do do duoc 3,04-3,51: mot cau viet
#:    theo `3,35 x 0,92` doc cham nhat (3,04) ra dai hon khe **1,4%**, doc nhanh
#:    nhat (3,51) ra ngan hon khe 12% — ca hai deu trong dung sai cua
#:    `nan_cho_vua` (+8% / -35%). Do la ly do con so la 0,92 chu khong phai 1,0.
#:
#: 🔴 Truoc 23/09 con so nay go tay trong `nan_cho_vua.loi_nhac_nan` va pha VIET
#:    DAU khong he co no. Hai pha nham hai dich khac nhau tren cung mot khe.
HE_SO_MUC_TIEU = 0.92

#: Cum tu dien vao LOI NHAC (van ASCII khong dau nhu moi loi nhac cua ASV).
#:
#: 🔑 `nhip`/`nhip_moi_giay` **TINH RA** tu `NHIP`, khong go tay: mot con so, mot
#:    cho khai. Truoc 23/09 chung la chuoi go san va `NHIP` khong ton tai, nen
#:    khong co cach nao tinh mot ngan sach do dai tu chung.
CUM: dict[str, dict[str, str]] = {}


def _so(x: float) -> str:
    """So thap phan trong loi nhac ASCII — dau phay, kieu Viet."""
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _dung_cum() -> None:
    ten = {VI: ("tieng Viet", "nguoi Viet"), EN: ("tieng Anh", "nguoi noi tieng Anh")}
    for m in (VI, EN):
        t, ng = ten[m]
        dv = DON_VI_DO_DAI[m]
        n = _so(NHIP[m])
        CUM[m] = {"tieng": t, "nguoi": ng, "don_vi": dv,
                  "nhip": f"khoang {n} {dv}/giay",
                  "nhip_moi_giay": f"khoang {n} {dv} moi giay"}


_dung_cum()


def ngan_sach_do_dai(giay: float, dich) -> int:
    """So `DON_VI_DO_DAI[dich]` toi da cho mot cau doc vua `giay`.

    🔑 **Mot so NGUYEN, dem duoc.** Loi nhac cu dua cho model mot nhip
       ("khoang 4,5 am tiet/giay") va mot khe, roi de no tu nhan — tuc giao cho
       mot model ngon ngu mot phep tinh, cho moi doan, khong ai kiem lai.

    ⭐ Mot tran DEM DUOC thi model tu kiem duoc truoc khi tra loi, va nguoi doc
       bao cao cung kiem duoc sau do. Do la khac biet giua mot goi y va mot rang
       buoc.
    """
    d = chuan_dich(dich)
    if d not in NHIP:
        raise NgonNguError(f"dich {d!r} khong nam trong hop dong")
    return max(1, int(round(max(0.0, float(giay)) * NHIP[d] * HE_SO_MUC_TIEU)))


#: Ten NGUON trong loi nhac (ASCII).
TEN_LOI_NHAC = {ZH: "tieng Trung", EN: "tieng Anh", VI: "tieng Viet"}


def cum(dich) -> dict[str, str]:
    """Cum loi nhac cho mot dich. Dich ngoai hop dong ⇒ `NgonNguError`."""
    d = chuan_dich(dich)
    if d not in CUM:
        raise NgonNguError(f"dich {d!r} khong nam trong hop dong")
    return CUM[d]


#: Whisper tra ma rieng cho tieng Quang Dong. Van la chu Han, van dich duoc
#: bang cung loi nhac `zh`.
_BI_DANH_NGUON = {"yue": ZH, "zh-cn": ZH, "zh-tw": ZH, "cmn": ZH}


class NgonNguError(ValueError):
    """Cap ngon ngu khong nam trong hop dong. Thong diep cho khach doc."""


def chuan_nguon(ma) -> str:
    """Ma nguon chuan, hoac `TU_DOAN` khi rong/"auto". Khong kiem hop le."""
    m = str(ma or "").strip().lower()
    if not m or m == TU_DOAN:
        return TU_DOAN
    return _BI_DANH_NGUON.get(m, m)


def chuan_dich(ma) -> str:
    """Ma dich chuan; rong ⇒ mac dinh. Khong kiem hop le."""
    m = str(ma or "").strip().lower()
    return m or DICH_MAC_DINH


def kiem_cap(nguon, dich) -> tuple[str, str]:
    """Kiem cap khach KHAI luc nop. Tra ve cap da chuan hoa.

    `nguon` duoc la `TU_DOAN` — khi do chi kiem duoc dich, con nguon that thi
    `kiem_nguon_da_doan` chot sau ASR.
    """
    n, d = chuan_nguon(nguon), chuan_dich(dich)
    if d not in DICH_HOP_LE:
        raise NgonNguError(_t('Ngôn ngữ đích chỉ được là tiếng Việt hoặc tiếng Anh.'))
    if n != TU_DOAN and n not in NGUON_HOP_LE:
        raise NgonNguError(_t('Ngôn ngữ nguồn chỉ được là tiếng Trung, tiếng Anh hoặc tiếng Việt.'))
    if n == d:
        raise NgonNguError(_t('Ngôn ngữ nguồn và đích trùng nhau — không có gì để dịch.'))
    return n, d


def kiem_nguon_da_doan(ma_asr, dich) -> str:
    """Chot ngon ngu ASR DOAN ra. Goi o TRANSCRIBE, truoc moi giai doan tra tien.

    ⛔ Khong im lang cho qua: mot video tieng Nhat chay tiep se ra mot ban dich
       tu mot ban chep loi rac, va khach tra tien cho LLM + giong truoc khi thay.
    """
    n = chuan_nguon(ma_asr)
    if n not in NGUON_HOP_LE:
        raise NgonNguError(
            _t('Video này nói {ma} — Auto Scan chỉ nhận tiếng Trung, tiếng Anh '
               'hoặc tiếng Việt.').format(ma=str(ma_asr or '?')))
    if n == chuan_dich(dich):
        raise NgonNguError(
            _t('Video đã nói đúng ngôn ngữ đích — hãy chọn ngôn ngữ đích khác.'))
    return n


def ten_nguon(ma) -> str:
    """Ten nguon cho loi nhac; `auto`/la ⇒ chuoi rong (model tu doc)."""
    return TEN_LOI_NHAC.get(chuan_nguon(ma), "")


def _kiem() -> None:
    # 🔑 Moi dich phai la mot LAN giong that. Xem docstring dau tep.
    thieu = set(DICH_HOP_LE) - set(_LAN_GIONG)
    if thieu:
        raise ValueError(f"dich {sorted(thieu)} khong co lan giong trong ltt_voice")
    if DICH_MAC_DINH not in DICH_HOP_LE:
        raise ValueError("DICH_MAC_DINH ngoai DICH_HOP_LE")
    for m in DICH_HOP_LE:
        if m not in CUM or m not in NHAN:
            raise ValueError(f"dich {m!r} thieu CUM/NHAN")
        # ⛔ Mot lan dich khong co nhip la mot lan dich khong tinh duoc ngan
        #    sach do dai — tuc pha VIET DAU lai quay ve doan mo, va do dung la
        #    khiem khuyet 23/09. Chan luc nap module.
        if m not in NHIP or m not in DON_VI_DO_DAI:
            raise ValueError(f"dich {m!r} thieu NHIP/DON_VI_DO_DAI")


_kiem()
