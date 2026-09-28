"""`chia_lo.py` — so hoc chia lo, thuan, KHONG I/O.

⭐ Tep nay kiem duoc ma ⛔ khong can LLM, khong can CSDL, khong can job. Do la dieu
   kien de cac bat bien ve TIEN va ve TRAN THOI GIAN re den muc luon duoc chay —
   mot bat bien ve tien chi dang tin khi no re.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.project_schema import MAX_SCENES
from apps.prompt_ai_ommi.services import chia_lo


def test_cac_lo_phu_HET_va_KHONG_chong_nhau():
    """Bat bien manh nhat cua tep nay: moi canh thuoc DUNG MOT lo."""
    for n in range(1, MAX_SCENES + 1):
        lo = chia_lo.cac_lo(n)
        phu = [i for dau, cuoi in lo for i in range(dau, cuoi + 1)]
        assert phu == list(range(1, n + 1)), f"n={n}: {lo}"


def test_so_luot_goi_KHOP_so_lo_thuc_te():
    """⛔ Khong go lai cong thuc: dem chinh cai `cac_lo` tra ve.

    Hai cho khai cung mot dieu la hai cho se lech, va cho lech nay di vao
    `max_runtime_s` — tuc khach tra tien roi job chet o tran.
    """
    for n in range(1, MAX_SCENES + 1):
        assert chia_lo.so_luot_goi(n) == len(chia_lo.cac_lo(n)), f"n={n}"


def test_gia_phan_da_giao_KHONG_BAO_GIO_vuot_gia_day_du():
    """Khach huy phai tra <= so da giu. ⛔ Khong duoc thu vuot."""
    from apps.prompt_ai_ommi.manifest import _cost
    p = {"operation": "director", "scene_count": MAX_SCENES}
    day_du = _cost(p)
    for da_giao in range(0, MAX_SCENES + 1):
        gia = chia_lo.gia_phan_da_giao(da_giao, p)
        assert 0 <= gia <= day_du, f"da_giao={da_giao}: {gia} > {day_du}"
    assert chia_lo.gia_phan_da_giao(0, p) == 0, "chua giao canh nao thi KHONG thu"
    assert chia_lo.gia_phan_da_giao(MAX_SCENES, p) == day_du, (
        "giao du thi phai bang gia day du — neu khong, mot luot XONG binh thuong "
        "va mot luot huy o canh cuoi se thu hai so khac nhau cho cung mot hang")


def test_gia_phan_da_giao_KHONG_GIAM_khi_giao_them():
    """Don dieu. ⛔ Khong duoc co khe nao giao THEM mot canh lai thu IT hon."""
    p = {"operation": "director", "scene_count": MAX_SCENES}
    day = [chia_lo.gia_phan_da_giao(k, p) for k in range(MAX_SCENES + 1)]
    assert day == sorted(day), day


def test_gia_phan_da_giao_dung_DUNG_bang_gia_cua_manifest():
    """⛔ KHONG nhan chia theo ti le: bang gia la mot ham BAC THANG.

    `_director_cost = max(4, min(18, 2 + ceil(n/3)*2))`. Mot phep nhan ti le se cho
    mot so **khong nam tren bang gia nao** — tuc mot so khach khong the doi soat.
    """
    from apps.prompt_ai_ommi.manifest import _cost
    p = {"operation": "director", "scene_count": MAX_SCENES}
    for k in range(1, MAX_SCENES + 1):
        assert chia_lo.gia_phan_da_giao(k, p) == _cost({**p, "scene_count": k}), k


def test_cua_so_lich_su_lay_DUOI_cung_va_khong_qua_LICH_SU():
    canh = [{"position": i} for i in range(1, 13)]
    ra = chia_lo.cua_so_lich_su(canh)
    assert len(ra) == chia_lo.LICH_SU
    assert [c["position"] for c in ra] == list(range(13 - chia_lo.LICH_SU, 13))
    assert chia_lo.cua_so_lich_su([]) == []


def test_chia_lo_KHONG_import_provider_csdl_hay_jobs():
    """Bat bien kien truc: tep nay phai THUAN.

    ⛔ Mot `import` nang o day lam moi phep kiem tien/tran o tren phai keo theo ca
       mot the gioi — va luc do chung se bi tat khi ai do voi.
    """
    import ast
    import pathlib
    from apps.prompt_ai_ommi.services import chia_lo as m
    cay = ast.parse(pathlib.Path(m.__file__).read_text(encoding="utf-8"))
    cam = ("provider", "platform_core.db", "jobs", "sqlalchemy", "fastapi")
    o_dau_tep = [n for n in cay.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    ten = [getattr(n, "module", "") or "" for n in o_dau_tep]
    ten += [a.name for n in o_dau_tep if isinstance(n, ast.Import) for a in n.names]
    xau = [t for t in ten if any(c in t for c in cam)]
    assert not xau, f"import nang o DAU TEP: {xau}"
