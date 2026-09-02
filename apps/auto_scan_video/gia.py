"""Uoc gia mot lan chay, va lua chon san pham cho giao dien.

## Vi sao uoc theo THOI LUONG chu khong theo so ky tu

Luc khach bam "Bat dau", ta chua co ban chep loi. Chua co ban chep loi thi chua
biet so ky tu TTS lan so token LLM — hai thu chiem gan het chi phi. Nen uoc luon
phai dua tren thu **duy nhat** da biet: do dai video.

⚠️ Uoc thua la binh thuong va co chu dinh. `features.quyet_toan` tra lai phan du,
   nen mot uoc rong rai chi lam khach thay so giu cho lon hon so thu — no khong
   lam ho mat tien. Uoc THIEU thi nguoc lai: `features.kiem_tran_chi` se **danh
   hong mot lan chay dang giua chung**, va do la trai nghiem te nhat trong ca
   san pham (RISK-12-03).

⇒ Khi phan van, uoc cao hon.

## Ba con so nay CHUA DUOC DO

⛔ Chung duoc chon de an toan, khong de dung. Chung se duoc thay bang so do that
   o pha 21 (nghiem thu dau-cuoi). Ghi ro o day de khong ai doc chung nhu mot
   bang gia da chot.
"""
from __future__ import annotations

import logging

from platform_core.i18n import N_

log = logging.getLogger(__name__)

#: Credit moi PHUT video, cho phan **may** (tach nguon, chep loi, render).
#: ⚠️ CHUA DO. Chon theo thoi gian may chay chu khong theo gia von.
GIA_MOI_PHUT_MAY = 2

#: Credit moi PHUT video, cho phan **model** (dich + sinh tieng).
#: ⚠️ CHUA DO. Day la phan lon chi phi that, va no ti le voi **luong noi** chu
#:    khong voi do dai video — mot video 10 phut im lang gan nhu khong ton gi.
#:    Uoc theo do dai la mot xap xi rong rai co chu y.
GIA_MOI_PHUT_MODEL = 6

#: San toi thieu. Mot video 20 giay van ton mot lan khoi dong model.
GIA_TOI_THIEU = 5


def uoc_credit(thoi_luong_giay: float) -> int:
    """Uoc chi phi mot lan chay tu do dai video. Luon >= `GIA_TOI_THIEU`."""
    phut = max(0.0, float(thoi_luong_giay or 0)) / 60.0
    return max(GIA_TOI_THIEU,
               int(round(phut * (GIA_MOI_PHUT_MAY + GIA_MOI_PHUT_MODEL))))


#: Che do thoi gian, dong bang o `MVP_CONTRACT.md` §6 va sua boi ADR-003.
#:
#: ⭐ Nhan viet cho NGUOI DUNG, khong phai cho ky su: khach khong can biet
#:    "fit_original" nghia la gi, ho can biet ban long tieng se nghe ra sao.
CHE_DO_THOI_GIAN = (
    ("fit_original", N_('Bám sát câu gốc'),
     N_('Mỗi câu bắt đầu đúng lúc người nói bắt đầu. Phù hợp khi hình có khẩu '
        'hình hoặc chữ chạy theo lời.')),
    ("natural", N_('Nghe tự nhiên'),
     N_('Ưu tiên nhịp đọc dễ nghe, chấp nhận lệch nhẹ so với câu gốc. Phù hợp '
        'với video kể chuyện hoặc thuyết minh.')),
)

CHE_DO_MAC_DINH = "fit_original"


def che_do_hop_le(ma: str) -> bool:
    return any(ma == x[0] for x in CHE_DO_THOI_GIAN)


def giong_cua_toi(db, owner_id: str) -> list[dict]:
    """Giong ma CHINH chu so huu duoc dung.

    🔑 Danh sach nay do `ltt_voice` so huu, va ta hoi no thay vi tu truy van
       bang cua no — `test_421` chot dieu do. Mot phep loc `WHERE owner_id` viet
       tay o day la mot cho de quen menh de do, va quen no la mo duong dung
       giong nhan ban cua nguoi khac.
    """
    try:
        from apps.ltt_voice.doc_man_api import ma_giong_cua_toi
    except Exception as exc:      # noqa: BLE001 - app kia co the chua nap
        log.warning("khong nap duoc danh sach giong cua ltt_voice (%s: %s)",
                    type(exc).__name__, exc)
        return []

    # ⭐ `ma_giong_cua_toi` da loc `owner_id`, da xu ly kho giong dung chung, va
    #    da bo giong `active=False`. Ba viec do deu de lam sai neu tu viet lai,
    #    va cai thu nhat lam sai thi hau qua la khach dung giong cua nguoi khac.
    ra = []
    for g in ma_giong_cua_toi(db, owner_id) or []:
        # ⛔ Chi lay HAI truong. Chep nguyen doi tuong cua app kia sang day la de
        #    mot truong noi bo cua ho lot ra giao dien cua ta o lan doi sau.
        ma = str((g or {}).get("ma") or "")
        if ma:
            ra.append({"ma": ma, "ten": str(g.get("ten") or "") or "—"})
    return ra
