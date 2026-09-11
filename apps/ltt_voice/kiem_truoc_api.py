"""Public API pre-check cho `speech.ltt` (D007): cung cong voi Studio.

`server/api/jobs.py` goi ham `kiem` nay qua `ToolSpec.kiem_truoc` -- TRUOC khi
co gia va TRUOC khi giu tien -- de mot loi so huu giong/lech lan ngon ngu
duoc tu choi ngay tai `/quotes` va `/jobs`, thay vi giu credit, xep job, roi
moi hong o worker va phai hoan (D007).

Dung dung `features.chuan_hoa` + `features.giai_giong` ma web (`routes.py`)
va worker (`jobs.py`) dang dung -- cung mot cong nghiep vu, khong co ban chep
thu hai co the lech (dung dau tep `features.py` da noi).
"""
from __future__ import annotations

from . import features


def kiem(db, user_id: str, params: dict) -> None:
    """Nem `features.LoiGiongNoi` (ke thua `LoiNguoiGoi`) neu yeu cau se bi
    tu choi luc thi hanh -- so huu `voice_id` sai hoac van ban lech lan ngon
    ngu cua giong. Im lang tra `None` khi yeu cau hop le.
    """
    yc = features.chuan_hoa(dict(params, owner_id=user_id))
    features.giai_giong(db, yc)
