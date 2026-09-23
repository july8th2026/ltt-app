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

🔴 SU CO 23/09/2026. Ba cong cu tren CHI `CREATE DATABASE`, khong bao gio DROP
   (rao an toan cu: cong cu khong co DROP thi khong the xoa so credit). Moi
   worktree de lai ba CSDL; worktree bi go thi CSDL mo coi. Den 23/09: 132 CSDL,
   44.651 tep. Sau moi lan may sap, PostgreSQL fsync TUNG tep truoc khi phuc hoi
   (~4,5 phut) -> `pg_ctl runservice -w` qua han -> dich vu bao Stopped trong khi
   postgres.exe van chay -> lan tat may sau giet no -> lai phuc hoi. Vong lap.

⭐ Rao moi thay cho "khong bao gio DROP": moi DROP di qua `cau_xoa`, va cau ay
   chi sinh ra cho mot ten (a) chua `test` (hoac dung khuon dien tap khoi phuc),
   (b) KHAC ten dang chay, (c) khong phai CSDL he thong, (d) chi gom ky tu
   identifier. Khong `WITH (FORCE)`: CSDL con ket noi thi PostgreSQL tu tu choi.
   Cong cu theo cay dung `cau_xoa_csdl_test` — ten TINH LAI tu (ten dang chay,
   hau to, cay), khong nhan tu ngoai.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

GIOI_HAN_TEN = 63

#: Hau to cua moi cong cu tao CSDL test theo cay. Them cong cu moi thi them vao
#: day — `tests/test_2300` doi chieu voi moi `HAU_TO = ...` khai trong `tools/`.
HAU_TO_DA_BIET = ("_multiproc_test", "_wf_migration_test", "_m1_dientap_test")

CSDL_HE_THONG = frozenset({"postgres", "template0", "template1"})

#: CSDL tam cua `tools/restore_drill_schema.py` (khong mang chu `test`).
KHUON_DIEN_TAP = re.compile(r"ltt_drill_(src|dst)_\d{14}")

_IDENTIFIER = re.compile(r"[A-Za-z0-9_]+")


def van_tay_cay(cay: Path) -> str:
    chuan = str(cay).replace("\\", "/").rstrip("/").lower()
    return hashlib.sha256(chuan.encode("utf-8")).hexdigest()[:8]


def ten_csdl_test(ten_goc: str, hau_to: str, cay: Path) -> str:
    duoi = f"{hau_to}_{van_tay_cay(cay)}"
    goc = ten_goc[: max(1, GIOI_HAN_TEN - len(duoi))]
    return f"{goc}{duoi}"


def cau_xoa(ten: str, ten_goc: str) -> str:
    """Cau `DROP DATABASE` cho mot CSDL VUT DI, hoac `ValueError` neu khong chung minh duoc.

    `ten_goc` la ten CSDL dang chay (production). Khong co `WITH (FORCE)`.
    """
    if not _IDENTIFIER.fullmatch(ten or ""):
        raise ValueError(f"tu choi xoa {ten!r}: khong phai identifier thuan")
    thap = ten.lower()
    if thap in CSDL_HE_THONG:
        raise ValueError(f"tu choi xoa {ten!r}: CSDL he thong")
    if thap == (ten_goc or "").strip().lower():
        raise ValueError(f"tu choi xoa {ten!r}: chinh la CSDL dang chay")
    if "test" not in thap and not KHUON_DIEN_TAP.fullmatch(thap):
        raise ValueError(f"tu choi xoa {ten!r}: ten khong chua 'test'")
    return f'DROP DATABASE IF EXISTS "{ten}"'


def cau_xoa_csdl_test(ten_goc: str, hau_to: str, cay: Path) -> str:
    """`cau_xoa` cho CSDL test cua CHINH cay `cay` — ten tinh lai, khong nhan tu ngoai."""
    if hau_to not in HAU_TO_DA_BIET:
        raise ValueError(f"hau to la {hau_to!r}: khai vao HAU_TO_DA_BIET truoc")
    return cau_xoa(ten_csdl_test(ten_goc, hau_to, cay), ten_goc)
