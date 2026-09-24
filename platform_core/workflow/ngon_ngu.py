"""MOI NOI cua ngon ngu bieu thuc §6: may + chinh sach × bang ham.

## Van de no giai

Ngon ngu §6 duoc lam boi hai lan song song va hai nua chua bao gio gap nhau:

    `chinh_sach.py`     phuong ngu DAY DU — bang ham la mot THAM SO, mac dinh RONG
    `ham_bieu_thuc.py`  `BANG_HAM` — 49 ham, khong biet bo tinh nao

`chinh_sach.DAY_DU` la mot ngon ngu **khong co ham nao**. Goi
`tinh_ngon_ngu(bt, mt)` khong `cs=` thi moi `upper(x)` bi tu choi — im lang,
dung cach, va sai. ⇒ Mo-dun nay la **cho duy nhat** hai nua duoc lap lai, va
`test_1767` la phep kiem cua chinh cho ghep ay (khong phai cua tung nua).

## ⛔ Vi sao KHONG cam `BANG_HAM` thang vao `chinh_sach.DAY_DU`

`chinh_sach.py` la **may**; `ham_bieu_thuc.py` la **du lieu**. Cho may import
du lieu thi:

- tang may khong con test duoc bang mot bang GIA (`test_1766` dang lam dung
  the, va `test_1761` dua vao viec `NGHIEM` co bang RIENG cua no);
- `ham_bieu_thuc` nap tre `platform_core.public_api.projects` (keo SQLAlchemy)
  cho `slugify` — mot phu thuoc ma tang may khong duoc co.

⇒ Lap o mot tang thu ba. Mot chieu phu thuoc: `ngon_ngu` → (`chinh_sach`,
`ham_bieu_thuc`); hai mo-dun duoi khong biet gi ve mo-dun nay.

## Cua vao

    ngon_ngu.tinh(bieu_thuc, moi_truong)     tinh mot bieu thuc §6
    ngon_ngu.kiem(bieu_thuc)                 kiem (khong can moi truong)
    ngon_ngu.NGON_NGU                        phuong ngu da lap, cho ai can `cs=`

⚠️ Dung `chinh_sach.moi_truong_wf(...)` de dung `moi_truong` — no la cho khai
   bay namespace §6.2 va ba hang so `true/false/null`.
"""
from __future__ import annotations

import ast
from typing import Any

from platform_core.workflow import chinh_sach as _cs
from platform_core.workflow.chinh_sach import LoiNgonNgu
from platform_core.workflow.ham_bieu_thuc import BANG_HAM, LoiHam

__all__ = ["NGON_NGU", "kiem", "tinh"]

#: Phuong ngu §6 DA LAP: chinh sach day du + ca 49 ham cua §6.3.
#:
#: `loi_nguoi_dung=(LoiHam,)` noi cho may biet ngoai le nao cua bang mang cau
#: **viet cho nguoi khai doc** (dan nguyen van) va ngoai le nao la loi lap
#: trinh (nuot noi dung, chi noi ham nao nga). Xem `chinh_sach._goi_ham`.
#: ⚠️ `LoiNgonNgu` cung nam trong `loi_nguoi_dung`: mot ham co the DOC mot
#: namespace §6.2 (`keys(nodes.a.output)`), va namespace do nem `LoiNgonNgu`
#: voi mot cau viet cho nguoi khai (*"node chua chay xong"*). Nuot cau do
#: thanh "ham nga" la doi mot cau loi dung lay mot cau loi mo ho.
NGON_NGU = _cs.chinh_sach_day_du(ham=BANG_HAM,
                                 loi_nguoi_dung=(LoiHam, LoiNgonNgu))


def kiem(bieu_thuc: str, *,
         ten_cho_phep: set[str] | None = None) -> ast.Expression:
    """Kiem mot bieu thuc §6 voi bang ham THAT. Sai thi nem `LoiNgonNgu`."""
    return _cs.kiem_ngon_ngu(bieu_thuc, cs=NGON_NGU,
                             ten_cho_phep=ten_cho_phep)


def tinh(bieu_thuc: str, moi_truong: dict[str, Any]) -> Any:
    """Tinh mot bieu thuc §6 voi bang ham THAT. Tra ve gia tri JSON."""
    return _cs.tinh_ngon_ngu(bieu_thuc, moi_truong, cs=NGON_NGU)
