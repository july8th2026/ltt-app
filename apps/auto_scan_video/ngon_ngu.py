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

from platform_core.i18n import _ as _t

from apps.ltt_voice.lan_ngon_ngu import LAN_HOP_LE as _LAN_GIONG

ZH = "zh"
EN = "en"
VI = "vi"

#: Khach khong khai nguon ⇒ ASR tu doan, roi `kiem_nguon_da_doan` chot lai.
TU_DOAN = "auto"

NGUON_HOP_LE: tuple[str, ...] = (ZH, EN, VI)
DICH_HOP_LE: tuple[str, ...] = (VI, EN)
DICH_MAC_DINH = VI

NHAN = {ZH: "Tiếng Trung", EN: "Tiếng Anh", VI: "Tiếng Việt"}

#: Cum tu dien vao LOI NHAC (van ASCII khong dau nhu moi loi nhac cua ASV).
#:
#: 🔑 Voi `vi`, moi cum GIU DUNG TUNG KY TU cua loi nhac V4-V6 da nghiem thu —
#:    mo `en` khong duoc doi mot chu nao cua duong `vi` (khong lam troi chat
#:    luong da do). `test` chot dieu do bang chuoi cu.
#:
#: Nhip doc la goi y cho LLM uoc do dai, khong phai phep do: VieNeu doc tieng
#: Viet ~4,5 am tiet/giay (V4 pha 14); thuyet minh tieng Anh ~155 tu/phut.
CUM: dict[str, dict[str, str]] = {
    VI: {"tieng": "tieng Viet", "nguoi": "nguoi Viet",
         "nhip": "khoang 4,5 am tiet/giay",
         "nhip_moi_giay": "khoang 4,5 am tiet moi giay"},
    EN: {"tieng": "tieng Anh", "nguoi": "nguoi noi tieng Anh",
         "nhip": "khoang 2,6 tu/giay",
         "nhip_moi_giay": "khoang 2,6 tu moi giay"},
}

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


_kiem()
