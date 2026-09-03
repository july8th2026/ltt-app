"""Auto Scan Video V4 — architecture guards from ADR-V4-002.

Three groups:

**§1** widens two guards that `test_421` already owns. They were correct in policy and
       narrower in reach than their names suggest: `glob("*.py")` is not recursive, and
       they scan only `apps/auto_scan_video`. V4 adds eight domain modules and may add a
       `services/` package (`AGENTS.md` §8.1), and the three executor apps each run a
       `jobs.py` **inside a worker** — the exact place a stray thread pool does damage.

**§2** pins the schema half of "no second queue" (D-V4-11). `AsvWorkItem` does not exist
       yet, so this guard runs over an absence. A guard over an absence passes for the
       wrong reason, so each one is paired with a self-test proving it fires.

**§3** pins the pieces of the current runtime that ADR-V4-002 promises **not** to change.

⚠️ This file must not restate `test_421`. Where a check already exists there, §1 changes
   only its *reach*, and says so.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

GOC = Path(__file__).resolve().parent.parent
APP = GOC / "apps"

#: Bon app cua MOT san pham. `test_421` chi quet app dau tien.
APP_ASV = ("auto_scan_video", "asv_media", "asv_gpu", "asv_voice")


def _moi_tep_py(slug: str) -> list[Path]:
    """MOI tep .py cua app, ke ca trong thu muc con.

    ⭐ `rglob` chu khong `glob`: `AGENTS.md` §8.1 bat app nhieu mien dat quy tac
       nghiep vu vao `services/`, va V4 them tam module mien. Ngay ai do tao thu
       muc do la ngay mot guard dung `glob` lang le mat tam nhin — khong loi nao
       bao, va ten cua no van doc nhu the no van dang canh.
    """
    goc = APP / slug
    if not goc.is_dir():
        return []
    return sorted(p for p in goc.rglob("*.py") if "__pycache__" not in p.parts)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Mo rong tam nhin cua hai guard da co
# ══════════════════════════════════════════════════════════════════════════════

#: I1 — hang doi SSOT la `platform_core.jobs`, khong co cai thu hai.
CAM_HANG_DOI = ("ThreadPoolExecutor", "ProcessPoolExecutor", "multiprocessing",
                "APScheduler", "BackgroundScheduler")

#: Card do nen tang cap qua `gpu_lease`; mot khoa rieng se dam voi no.
CAM_KHOA_GPU = ("gpu_lock", "GPULock", "khoa_gpu", "gpu_arbiter", "current_gpu")


@pytest.mark.parametrize("slug", APP_ASV)
def test_KHONG_hang_doi_thu_hai_o_BAT_KY_tep_nao_cua_BON_app(slug):
    """`test_421` kiem dieu nay cho MOT app, khong de quy. Day la ca bon, de quy."""
    for tep in _moi_tep_py(slug):
        vp = _vi_pham(tep.read_text(encoding="utf-8"), CAM_HANG_DOI)
        assert vp == [], f"{tep.relative_to(GOC)} dung hang doi/lich rieng: {vp}"


@pytest.mark.parametrize("slug", APP_ASV)
def test_KHONG_bo_lap_lich_GPU_thu_hai_o_BAT_KY_tep_nao_cua_BON_app(slug):
    for tep in _moi_tep_py(slug):
        vp = _vi_pham(tep.read_text(encoding="utf-8"), CAM_KHOA_GPU)
        assert vp == [], f"{tep.relative_to(GOC)} cham khoa GPU rieng: {vp}"


def test_tam_nhin_mo_rong_THAT_SU_rong_hon():
    """Chung minh §1 khong phai mot ban sao khac ten cua `test_421`.

    ⛔ Neu `_moi_tep_py` tra ve dung nhung tep `glob("*.py")` da tra, thi ca §1
       la mot lan chay lai — ton thoi gian, khong them mot dong bao ve nao. Phep
       kiem nay chot rang tam nhin **that su** rong hon, theo ca hai chieu:
       them app, va (khi co) them thu muc con.
    """
    cu = set((APP / "auto_scan_video").glob("*.py"))
    moi: set[Path] = set()
    for slug in APP_ASV:
        moi |= set(_moi_tep_py(slug))

    assert cu < moi, "tam nhin moi khong bao trum tam nhin cu"
    them = {p.relative_to(APP).as_posix() for p in moi - cu}
    # Hom nay phan them la `jobs.py`/`manifest.py`/`__init__.py` cua ba executor.
    assert any(p.startswith("asv_") for p in them), (
        f"ba app executor van khong duoc quet: {sorted(them)}")


# ══════════════════════════════════════════════════════════════════════════════
#  §2  D-V4-11 — bang checkpoint KHONG duoc mang cot cua mot hang doi
# ══════════════════════════════════════════════════════════════════════════════

#: Dung nhung cot nay phan biet mot bang CHECKPOINT voi mot bang HANG DOI. Co
#: chung nghia la mot worker chon viec o day thay vi o `Job` — tuc hang doi thu hai.
COT_HANG_DOI = ("claimed_by", "worker_id", "locked_by", "lease_until",
                "visible_at", "available_at", "priority", "heartbeat_at")

TABLES = GOC / "apps" / "auto_scan_video" / "tables.py"


def _ten_cot(nguon: str) -> set[str]:
    """Ten cac cot khai trong mot module bang SQLAlchemy 2.0 (`x: Mapped[...] = ...`).

    Doc AST chu khong doc van ban: `COT_HANG_DOI` duoc nhac ngay trong docstring
    cua `ADR-V4-002` va se duoc nhac trong chinh `tables.py` khi pha 05 giai
    thich vi sao chung vang mat. Mot bo do quet van ban se bat dung loi giai
    thich do — cung cai bay da bat toi o pha 02.
    """
    try:
        cay = ast.parse(nguon)
    except SyntaxError:
        return set()
    ra: set[str] = set()
    for nut in ast.walk(cay):
        if isinstance(nut, ast.AnnAssign) and isinstance(nut.target, ast.Name):
            ra.add(nut.target.id)
        elif isinstance(nut, ast.Assign):
            for dich in nut.targets:
                if isinstance(dich, ast.Name):
                    ra.add(dich.id)
    return ra


def test_khong_bang_ASV_nao_mang_cot_cua_mot_hang_doi():
    """⚠️ Hom nay `AsvWorkItem` CHUA TON TAI, nen phep kiem nay chay tren mot tap
       gan rong va se xanh du bo do co hong. Do la ly do
       `test_bo_do_cot_hang_doi_that_su_bat_duoc` ton tai ngay ben duoi.
    """
    cot = _ten_cot(TABLES.read_text(encoding="utf-8"))
    xau = sorted(cot & set(COT_HANG_DOI))
    assert xau == [], (
        f"tables.py khai {xau} — day la cot cua mot HANG DOI, khong phai cua mot "
        f"bang checkpoint. Doc ADR-V4-002 D-V4-11 truoc khi them")


def test_bo_do_cot_hang_doi_that_su_bat_duoc():
    """Bo do chay tren mot bang gia co dung nhung cot bi cam."""
    mau = (
        "class AsvWorkItem(Base):\n"
        "    __tablename__ = 'asv_work_item'\n"
        "    id: Mapped[str] = mapped_column(String(48), primary_key=True)\n"
        "    claimed_by: Mapped[str] = mapped_column(String(36))\n"
        "    lease_until: Mapped[object] = mapped_column()\n")
    cot = _ten_cot(mau)
    assert cot & set(COT_HANG_DOI) == {"claimed_by", "lease_until"}

    # Va chieu nguoc lai: mot bang checkpoint HOP LE khong duoc bao dong gia.
    sach = (
        "class AsvWorkItem(Base):\n"
        "    __tablename__ = 'asv_work_item'\n"
        "    id: Mapped[str] = mapped_column(String(48), primary_key=True)\n"
        "    item_key: Mapped[str] = mapped_column(String(64))\n"
        "    fingerprint: Mapped[str] = mapped_column(String(64))\n"
        "    credit_actual: Mapped[int] = mapped_column(Integer)\n")
    assert _ten_cot(sach) & set(COT_HANG_DOI) == set()


def test_ADR_V4_002_ton_tai_va_khai_ro_bang_khong_phai_hang_doi():
    adr = (GOC / "docs" / "auto_scan_video_v4" / "adr"
           / "ADR-V4-002-kien-truc-rebase.md")
    assert adr.exists()
    van_ban = adr.read_text(encoding="utf-8")
    assert "AsvWorkItem" in van_ban
    for cot in ("claimed_by", "lease_until", "priority"):
        assert cot in van_ban, f"ADR khong liet ke cot bi cam {cot}"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Nhung thu ADR-V4-002 hua KHONG doi
# ══════════════════════════════════════════════════════════════════════════════

def test_chuoi_van_TU_KIEM_luc_nap_module(monkeypatch):
    """D-V4-13: mot chuoi hong phai no luc **nap app**, khong phai luc khach cho.

    ⭐ Chot bang cach GOI ham do voi mot chuoi hong, chu khong bang cach kiem no
       ton tai. Mot ham ton tai va mot ham lam viec la hai chuyen khac nhau.
    """
    from apps.auto_scan_video import pipeline

    hong = (pipeline.GiaiDoan("a", "asv_media", "asv_media.a",
                              sau=("chua_ton_tai",)),)
    monkeypatch.setattr(pipeline, "CHUOI", hong)
    with pytest.raises(ValueError, match="chua duoc khai truoc"):
        pipeline._kiem_tra_chuoi()


def test_dong_ha_nguon_van_theo_PHU_THUOC_chu_khong_theo_thu_tu(monkeypatch):
    """D-V4-13 giu `ha_nguon_cua` vi V4 them nhanh song song THAT.

    Hom nay do thi gan nhu mot duong thang, nen "ha nguon cua X" trung voi "moi
    giai doan dung sau X". `pipeline.ha_nguon_cua` co mot docstring dai giai
    thich rang hai thu do bang nhau **do hoan canh, khong do dinh nghia**.

    ⛔ V4 them nhanh canh/VLM chay song song voi nhanh tieng/ASR. Luc do chung
       tach ra, va mot phien ban `CHUOI[i+1:]` se lang le vo hieu nhung giai doan
       khong an theo — tuc bat khach tra tien lai cho mot viec khong dau vao nao
       doi. Phep kiem nay chot RANG ham do van doc phu thuoc.
    """
    from apps.auto_scan_video import pipeline

    # Hai nhanh doc lap tu `a`: `b` va `c`. `c` KHONG an theo `b`.
    monkeypatch.setattr(pipeline, "CHUOI", (
        pipeline.GiaiDoan("a", "asv_media", "asv_media.a"),
        pipeline.GiaiDoan("b", "asv_media", "asv_media.b", sau=("a",)),
        pipeline.GiaiDoan("c", "asv_media", "asv_media.c", sau=("a",)),
    ))
    assert pipeline.ha_nguon_cua("b") == [], (
        "`c` dung SAU `b` trong chuoi nhung KHONG an theo no — vo hieu no la "
        "bat khach tra lai cho mot viec khong dau vao nao doi")
    assert pipeline.ha_nguon_cua("a") == ["b", "c"]


def test_quyet_toan_van_do_chu_khong_tinh_lai():
    """ADR-001 D4, giu nguyen boi D-V4-12. Chot vao NGUON, khong vao mot lan chay.

    `features.quyet_toan` phai lay so tu `tong_da_dung` (tong `credit_actual` do
    duoc) va khong duoc goi mot ham bao gia nao. Hai ham bao gia da gay hai loi
    tien that trong du an nay (ADR-001 D4).
    """
    import inspect

    from apps.auto_scan_video import features

    nguon = inspect.getsource(features.quyet_toan)
    assert "tong_da_dung" in nguon
    for cam in ("actual_cost", "uoc_credit", "credit_cost"):
        assert cam not in nguon, (
            f"`quyet_toan` goi {cam} — do la tinh LAI gia, khong phai doc so DA DO")


def test_ban_do_rebase_ton_tai_va_phu_HET_module_hien_co():
    """Ban do rebase phai ke het, khong duoc bo sot mot module nao.

    ⛔ Mot module vang mat khoi ban do la mot module khong ai quyet dinh so phan.
       No se duoc mot pha sau "tien tay" sua ma khong co can cu nao.
    """
    ban_do = (GOC / "docs" / "auto_scan_video_v4" / "REBASE_MAP_V4.md")
    assert ban_do.exists()
    van_ban = ban_do.read_text(encoding="utf-8")

    thieu = [p.stem for p in sorted((APP / "auto_scan_video").glob("*.py"))
             if f"`{p.name}`" not in van_ban]
    assert thieu == [], f"REBASE_MAP_V4.md bo sot: {thieu}"


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Chot GIU HINH — phai song sot qua cuoc tach doi cua pha 17
# ══════════════════════════════════════════════════════════════════════════════

KET_XUAT = APP / "auto_scan_video" / "ket_xuat.py"
BAN_DUNG = APP / "auto_scan_video" / "ban_dung.py"


def test_render_van_TU_CHOI_moi_che_do_hinh_khac_copy_HOAC_da_biet_den_preset():
    """⛔ Chot nay ton tai vi mot cuoc refactor SAP DIEN RA, khong vi mot loi.

    Hom nay `ket_xuat.py:175-177` tu choi moi ban dung khai che do hinh khac
    `copy`. Do la mot chot vo dieu kien, va no dung — MVP v1 khong ma hoa lai
    hinh o dau ca.

    Pha 17 PHAI noi no ra, vi `smart_localize` ma hoa lai tai diem cat. Va cach
    noi sai la xoa han cau lenh `raise`: luc do `localize_preserve_picture` mat
    han lop bao ve, va no mat **im lang** — khong phep kiem nao do, chi la mot
    ngay nao do mot khach chon preset "giu nguyen hinh anh" va nhan ve mot ban
    da ma hoa lai.

    ⇒ Chot nay chap nhan DUNG HAI trang thai, khong chap nhan trang thai thu ba:
         (a) chot vo dieu kien con nguyen  — hom nay
         (b) chot da tro thanh CO DIEU KIEN theo preset — sau pha 17
       Xoa chot ma khong nhac toi preset nao la trang thai thu ba, va no do.

    ⭐ Doc AST chu khong doc van ban: doan giai thich ngay tren day nhac ca
       `copy` lan ten preset, va mot bo do quet van ban se tu lam minh xanh.
    """
    from apps.auto_scan_video import hop_dong_v4

    nguon = KET_XUAT.read_text(encoding="utf-8")
    cay = ast.parse(nguon)

    # (a) Chot vo dieu kien: co mot `raise` nam trong mot `if` so sanh che do hinh.
    con_chot = False
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.If):
            continue
        so_sanh = any(isinstance(n, ast.Compare) for n in ast.walk(nut.test))
        nhac_che_do = any(
            isinstance(n, ast.Attribute) and "CHE_DO_HINH" in n.attr
            or isinstance(n, ast.Constant) and n.value == "che_do"
            for n in ast.walk(nut.test))
        co_raise = any(isinstance(n, ast.Raise) for n in ast.walk(nut))
        if so_sanh and nhac_che_do and co_raise:
            con_chot = True
            break

    # (b) Da tro thanh co dieu kien: ma nguon THAM CHIEU mot ten preset.
    ten_dinh_danh = {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    ten_dinh_danh |= {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    biet_preset = any(
        p in ten_dinh_danh
        for p in ("PRESET_GIU_HINH", "PRESET_CAT_THONG_MINH", "preset"))

    assert con_chot or biet_preset, (
        "`ket_xuat.py` khong con tu choi che do hinh khac copy, VA cung khong "
        "biet den preset nao. Duong giu-nguyen-hinh dang khong duoc bao ve boi "
        "thu gi ca. Doc ADR-V4-001 he qua 1 truoc khi di tiep.")

    # Va hop dong san pham phai van noi rang preset giu hinh khong cat duoc.
    assert hop_dong_v4.THAO_TAC_CHO_PHEP[hop_dong_v4.PRESET_GIU_HINH] == ()


def test_ban_dung_van_khai_che_do_hinh_nhu_MOT_TRUONG_DU_LIEU():
    """`ban_dung` la DU LIEU, khong phai mot chuoi lenh (giu tu V2 pha 14).

    Pha 17 them duong ma hoa lai. Neu che do hinh thoi la mot truong trong ban
    dung ma thanh mot nhanh `if` trong trinh render, thi mot ban dung da luu
    khong con mo ta day du mot lan render — va `thi_hanh.van_tay` se coi hai lan
    render khac nhau la mot.
    """
    from apps.auto_scan_video import ban_dung

    assert hasattr(ban_dung, "CHE_DO_HINH")
    assert ban_dung.CHE_DO_HINH == "copy"
