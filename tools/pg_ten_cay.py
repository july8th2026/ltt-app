"""Ten CSDL test PostgreSQL rieng cho MOI cay lam viec.

🔴 SU CO 17/09/2026 (tests/test_1500). Ba cong cu `check_multiproc.py`,
   `do_migration_tren_postgres.py`, `dien_tap_m1_tren_postgres.py` dung MOT ten co
   dinh `<ten CSDL dang chay><hau to>` cho MOI cay va MOI phien. Khoa
   `postgres_test` la lop bao ve duy nhat — mot luot chen (qua han `--cho`, hoac
   `--khong-khoa`) la hai luot cung `drop_all`/`create_all` tren mot CSDL:
   `relation "jobs" does not exist`, do gia.

⭐ Lop phong thu thu hai: ten mang dau van tay DUONG DAN cay. Hai worktree khong the
   ghi chung mot CSDL nua, ke ca khi ai do lach khoa. Trong CUNG mot cay ten on dinh
   (hoa/thuong, `\\` hay `/`, dau `/` cuoi khong doi ten).

⚠️ PostgreSQL cat identifier o 63 byte — cat phan goc, giu nguyen hau to + van tay
   (chu `test` nam trong hau to, ma cac cong cu kia DOI chu do truoc khi ghi).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

GIOI_HAN_TEN = 63


def van_tay_cay(cay: Path) -> str:
    chuan = str(cay).replace("\\", "/").rstrip("/").lower()
    return hashlib.sha256(chuan.encode("utf-8")).hexdigest()[:8]


def ten_csdl_test(ten_goc: str, hau_to: str, cay: Path) -> str:
    duoi = f"{hau_to}_{van_tay_cay(cay)}"
    goc = ten_goc[: max(1, GIOI_HAN_TEN - len(duoi))]
    return f"{goc}{duoi}"
