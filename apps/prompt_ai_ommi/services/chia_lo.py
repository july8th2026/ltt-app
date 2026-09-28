"""Chia mot luot sinh canh thanh nhieu LO — thuan so hoc, KHONG I/O.

## 🔴 VI SAO CO TEP NAY

Do that 2 lan o `scene_count=20` (lan E, 27/09/2026): ca hai lan tra **19/20** canh,
va do dai truong `prompt` **co dan theo thu tu canh** (159->87 va 165->~90 ky tu)
trong khi chi dung **67 %/69 %** cua `_MAX_TOKENS = 8192`.

⭐ Ket luan quan trong hon con so: **chat luong suy TRUOC khi cham tran cung**, nen
   nang `_MAX_TOKENS` ⛔ KHONG phai thuoc. `apps/prompt_canh` chia lo (`LO_BUOC2=10`,
   `LO_BUOC3=5`, `LICH_SU_CANH=5`) va do duoc toi 250 canh.

## ⛔ TEP NAY KHONG IMPORT GI NANG

Khong `provider`, khong CSDL, khong `jobs`, khong `fastapi`. Do la dieu kien de cac
bat bien ve **TIEN** (`gia_phan_da_giao`) va ve **TRAN THOI GIAN** (`so_luot_goi`)
kiem duoc ma khong phai gia lap LLM — mot bat bien ve tien chi dang tin khi no re
den muc luon duoc chay. `tests/test_5570` ghim chinh dieu do bang AST.

⚠️ `manifest._cost` duoc import **BEN TRONG** `gia_phan_da_giao` chu khong o dau tep:
   `manifest.py` nhap nguoc lai tep nay (de suy `max_runtime_s`), nen mot `import` o
   dau tep se thanh vong.
"""
from __future__ import annotations

#: So canh moi lo. Lay 5 theo `prompt_canh.LO_BUOC3` — lo cang nho thi lich su cang
#: dat gia tri tuong doi, nhung so luot goi (va tran thoi gian) cang lon.
LO_CANH = 5

#: So canh gan nhat dua vao loi nhac lam lich su (`prompt_canh.LICH_SU_CANH = 5`).
#:
#: ⛔ KHONG dua CA danh sach vao: lam the thi lo cuoi lai chinh la ca van ban dai ma
#:    pha nay sinh ra de tranh.
LICH_SU = 5

#: Ngan sach thoi gian cho MOT luot goi LLM, tinh bang giay.
#:
#: ⚠️ Con so nay la mot **GIA THIET** cho toi khi ai do do lai tren may B. Dat 60 s
#:    theo `prompt_canh` (3600/76 ≈ 47 s) cong bien, vi lo cua ta LON hon lo cua no
#:    (5 canh day du so voi mot buoc chia). Ai do that thi sua o DAY — mot cho — va
#:    `manifest.max_runtime_s` tu di theo.
NGAN_SACH_MOI_LUOT_S = 60


def cac_lo(n: int) -> list[tuple[int, int]]:
    """`[(dau, cuoi)]` 1-based, `cuoi` INCLUSIVE. Phu het, khong chong nhau."""
    n = max(0, int(n))
    return [(d + 1, min(d + LO_CANH, n)) for d in range(0, n, LO_CANH)]


def so_luot_goi(n: int) -> int:
    """⭐ Dem chinh `cac_lo`, ⛔ KHONG viet lai cong thuc.

    Hai cho khai cung mot dieu la hai cho se lech, va cho lech nay di vao
    `manifest.max_runtime_s` — tuc khach tra tien roi job chet o tran.
    """
    return len(cac_lo(n))


def gia_phan_da_giao(so_canh_da_giao: int, params: dict) -> int:
    """Gia cho `so_canh_da_giao` canh, dung DUNG bang gia cua `manifest`.

    ⭐ Goi lai `manifest._cost` voi `scene_count` = so canh da giao, chu ⛔ KHONG
       nhan chia theo ti le: bang gia la mot ham BAC THANG (`2 + ceil(n/3)*2`, kep
       trong `[4, 18]`), nen mot phep nhan ti le se cho mot so **khong nam tren bang
       gia nao** — tuc mot so khach ⛔ khong the doi soat.

    ⚠️ `0` canh tra `0`, ⛔ KHONG tra san duoi `4`: san ay la gia cua mot luot CO giao
       hang. Huy truoc khi lo dau xong thi khach ⛔ khong nhan gi.
    """
    # ⛔ Import BEN TRONG ham: `manifest` nhap nguoc lai tep nay.
    from apps.prompt_ai_ommi.manifest import _cost
    if int(so_canh_da_giao) <= 0:
        return 0
    return _cost({**params, "scene_count": int(so_canh_da_giao)})


def cua_so_lich_su(canh: list[dict]) -> list[dict]:
    """`LICH_SU` canh GAN NHAT — chong troi ngu canh giua cac lo."""
    return list(canh[-LICH_SU:]) if canh else []
