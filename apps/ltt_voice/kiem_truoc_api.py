"""Public API pre-check cho `speech.ltt` (D007): cung cong voi Studio.

`server/api/jobs.py` goi ham `kiem` nay qua `ToolSpec.kiem_truoc` -- TRUOC khi
co gia va TRUOC khi giu tien -- de mot loi so huu giong/lech lan ngon ngu
duoc tu choi ngay tai `/quotes` va `/jobs`, thay vi giu credit, xep job, roi
moi hong o worker va phai hoan (D007).

Dung dung `features.chuan_hoa` + `features.giai_giong_kiem` ma web
(`routes.py`) va worker (`jobs.py`) dang dung qua `features.giai_giong` --
cung mot cong nghiep vu (so huu, trang thai, chot lan, chon duong lui),
khong co ban chep thu hai co the lech.

⛔ CO Y goi `giai_giong_kiem`, KHONG PHAI `giai_giong`: ham day du con nap
bieu dien tu storage (`tham_chieu.nap_ref_b64`, mot luot doc mang toi R2)
-- viec ma mot lan CHI KIEM khong can va khong duoc lam, vi (a) no bi vut
di ngay sau do (quote/job khong giu ref_b64), (b) no chay HAI LAN cho moi
yeu cau (mot o /quotes, mot o /jobs) cho cung mot cau tra loi, va (c) mot
loi storage se la `RuntimeError`/network error -- KHONG PHAI `LoiNguoiGoi`
-- nen se thoat ra thanh 500 o /quotes thay vi duoc `invocation.kiem_truoc`
bat va doi thanh 400.
"""
from __future__ import annotations

from . import features


def kiem(db, user_id: str, params: dict) -> None:
    """Nem `features.LoiGiongNoi` (ke thua `LoiNguoiGoi`) neu yeu cau se bi
    tu choi luc thi hanh -- so huu `voice_id` sai hoac van ban lech lan ngon
    ngu cua giong. Im lang tra `None` khi yeu cau hop le.

    Khong bao gio cham storage/R2 (xem docstring dau tep).
    """
    yc = features.chuan_hoa(dict(params, owner_id=user_id))
    features.giai_giong_kiem(db, yc)
