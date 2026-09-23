"""CSDL test PostgreSQL khong duoc de lai mo coi.

🔴 Su co 23/09/2026: may chu co 132 CSDL (127 tao trong thang 9). Ba cong cu gate
   tao mot CSDL test cho MOI worktree va khong bao gio xoa; `test_1010` tao mot
   CSDL ngau nhien moi luot. Sau moi lan may sap, PostgreSQL fsync tung tep
   (44.651 tep, ~4,5 phut) -> `pg_ctl runservice -w` qua han -> dich vu bao
   Stopped trong khi postgres.exe van chay -> lan tat may sau giet no. Vong lap.

Tep nay chot ba dieu:
  1. moi DROP di qua `pg_ten_cay.cau_xoa` — rao production/he thong/khong FORCE;
  2. ba cong cu XOA CSDL cua chinh cay no ke ca khi than phep do nem loi, va GIU
     khi `--giu` (kiem HANH VI bang stub, khong can PostgreSQL);
  3. moi tep trong kho TAO CSDL deu co duong XOA (quet AST), va bo quet do DO
     duoc tren mot nguon thieu duong xoa.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import warnings
from contextlib import contextmanager

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
for _p in (GOC, GOC / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pg_ten_cay  # noqa: E402

PROD = "lttplatform"


# ── 1. Rao `cau_xoa` ────────────────────────────────────────────────────────

@pytest.mark.parametrize("ten", [
    "lttplatform", "LTTPLATFORM", "postgres", "template0", "template1",
    "ltt_khach", "lttplatform_x",               # khong chua `test`
    'a_test"; DROP DATABASE lttplatform; --',   # khong phai identifier
    "a test", "",
])
def test_cau_xoa_tu_choi_moi_ten_khong_chung_minh_duoc_la_vut_di(ten):
    with pytest.raises(ValueError):
        pg_ten_cay.cau_xoa(ten, PROD)


@pytest.mark.parametrize("ten", [
    "lttplatform_multiproc_test_7ddc8630",
    "ltt_vps_v4_test_" + "a" * 32,
    "ltt_drill_src_20260923101112",
])
def test_cau_xoa_nhan_ten_vut_di_va_KHONG_FORCE(ten):
    cau = pg_ten_cay.cau_xoa(ten, PROD)
    assert cau == f'DROP DATABASE IF EXISTS "{ten}"'
    assert "FORCE" not in cau.upper()


def test_cau_xoa_csdl_test_la_ten_cua_CHINH_cay_do():
    cay = pathlib.Path(r"D:\LTTSTUDIOSAPP-mot-cay")
    for hau_to in pg_ten_cay.HAU_TO_DA_BIET:
        cau = pg_ten_cay.cau_xoa_csdl_test(PROD, hau_to, cay)
        assert pg_ten_cay.ten_csdl_test(PROD, hau_to, cay) in cau
        assert f'"{PROD}"' not in cau
    with pytest.raises(ValueError):
        pg_ten_cay.cau_xoa_csdl_test(PROD, "_hau_to_la_test", cay)


# ── 2. Hanh vi ba cong cu: xoa trong `finally`, giu khi `--giu` ─────────────

class _Ghi:
    def __init__(self):
        self.lan = []

    def __call__(self, *a, **k):
        self.lan.append((a, k))


def _chay_main(mod, argv, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["x", *argv])
    return mod.main()


@pytest.mark.parametrize("than_nem_loi", [False, True])
def test_do_migration_xoa_csdl_nhap_ca_khi_than_nem_loi(monkeypatch, than_nem_loi):
    import do_migration_tren_postgres as dm

    monkeypatch.setenv("LTT_DATABASE_URL", f"postgresql+psycopg://u:p@h:5432/{PROD}")
    monkeypatch.setattr(dm, "_url_nhap", lambda live, ten: f"postgresql+psycopg://s@h/{ten}")
    monkeypatch.setattr(dm, "_tao_neu_thieu", lambda *a: None)

    def _do(url):
        if than_nem_loi:
            raise RuntimeError("alembic no")
        return 0

    monkeypatch.setattr(dm, "_do", _do)
    xoa = _Ghi()
    monkeypatch.setattr(dm, "_xoa_csdl_nhap", xoa)
    if than_nem_loi:
        with pytest.raises(RuntimeError):
            _chay_main(dm, [], monkeypatch)
    else:
        assert _chay_main(dm, [], monkeypatch) == 0
    assert xoa.lan == [((f"postgresql+psycopg://u:p@h:5432/{PROD}", PROD), {})]


def test_do_migration_giu_thi_khong_xoa(monkeypatch):
    import do_migration_tren_postgres as dm

    monkeypatch.setenv("LTT_DATABASE_URL", f"postgresql+psycopg://u:p@h:5432/{PROD}")
    monkeypatch.setattr(dm, "_url_nhap", lambda live, ten: f"postgresql+psycopg://s@h/{ten}")
    monkeypatch.setattr(dm, "_tao_neu_thieu", lambda *a: None)
    monkeypatch.setattr(dm, "_do", lambda url: 0)
    xoa = _Ghi()
    monkeypatch.setattr(dm, "_xoa_csdl_nhap", xoa)
    assert _chay_main(dm, ["--giu"], monkeypatch) == 0
    assert xoa.lan == []


@pytest.mark.parametrize("than_nem_loi", [False, True])
def test_dien_tap_m1_xoa_csdl_nhap_ca_khi_than_nem_loi(monkeypatch, than_nem_loi):
    import dien_tap_m1_tren_postgres as dt

    class D2:
        @staticmethod
        def _live_url():
            return f"postgresql+psycopg://u:p@h:5432/{PROD}"

    monkeypatch.setattr(dt, "_nap_d2", lambda: D2)
    monkeypatch.setattr(dt, "_doc_production", lambda d2: [{"id": "w"}])
    monkeypatch.setattr(dt, "_url_nhap", lambda d2, ten: f"postgresql+psycopg://s@h/{ten}")
    monkeypatch.setattr(dt, "_tao_neu_thieu", lambda *a: None)

    def _dien_tap(url, ban_ghi):
        if than_nem_loi:
            raise RuntimeError("M-1 no")
        return 0

    monkeypatch.setattr(dt, "_dien_tap", _dien_tap)
    xoa = _Ghi()
    monkeypatch.setattr(dt, "_xoa_csdl_nhap", xoa)
    if than_nem_loi:
        with pytest.raises(RuntimeError):
            _chay_main(dt, [], monkeypatch)
    else:
        assert _chay_main(dt, [], monkeypatch) == 0
    assert xoa.lan == [((D2, PROD), {})]
    xoa.lan.clear()
    monkeypatch.setattr(dt, "_dien_tap", lambda url, ban_ghi: 0)
    assert _chay_main(dt, ["--giu"], monkeypatch) == 0
    assert xoa.lan == []


@pytest.mark.parametrize("than_nem_loi", [False, True])
def test_check_multiproc_xoa_scratch_ca_khi_than_nem_loi(monkeypatch, than_nem_loi):
    import check_multiproc as cm

    monkeypatch.setattr(cm, "_tim_url", lambda: ("postgresql+psycopg://s@h/x_test", ""))

    def _chay(url):
        if than_nem_loi:
            raise RuntimeError("pytest con no")
        return 0

    monkeypatch.setattr(cm, "_chay_test_214", _chay)
    xoa = _Ghi()
    monkeypatch.setattr(cm, "_xoa_scratch", xoa)
    if than_nem_loi:
        with pytest.raises(RuntimeError):
            cm.main()
    else:
        assert cm.main() == 0
    assert len(xoa.lan) == 1


class _EngineGia:
    """Ghi lai cau SQL; khong noi mang."""

    def __init__(self, ghi, url):
        self.ghi, self.url = ghi, url

    @contextmanager
    def connect(self):
        class C:
            def execute(_s, cau):
                self.ghi.append((self.url, str(cau)))
        yield C()

    def dispose(self):
        pass


def _engine_gia(monkeypatch, ghi):
    import sqlalchemy as sa
    monkeypatch.setattr(sa, "create_engine", lambda url, **k: _EngineGia(ghi, url))


def test_xoa_csdl_nhap_gui_DUNG_ten_cua_cay_toi_CSDL_quan_tri(monkeypatch):
    import do_migration_tren_postgres as dm
    import dien_tap_m1_tren_postgres as dt

    ghi = []
    _engine_gia(monkeypatch, ghi)
    monkeypatch.setattr(dm, "_url_nhap", lambda live, ten: f"pg://s/{ten}")
    dm._xoa_csdl_nhap(f"postgresql://u:p@h/{PROD}", PROD)
    monkeypatch.setattr(dt, "_url_nhap", lambda d2, ten: f"pg://s/{ten}")
    dt._xoa_csdl_nhap(object(), PROD)
    assert ghi == [
        ("pg://s/postgres", pg_ten_cay.cau_xoa_csdl_test(PROD, dm.HAU_TO, dm.GOC)),
        ("pg://s/postgres", pg_ten_cay.cau_xoa_csdl_test(PROD, dt.HAU_TO, dt.GOC)),
    ]


def test_check_multiproc_xoa_scratch_chi_khi_CSDL_la_cua_minh(monkeypatch):
    import check_multiproc as cm

    ghi = []
    _engine_gia(monkeypatch, ghi)
    monkeypatch.setenv("LTT_DATABASE_URL", f"postgresql+psycopg://u:p@h:5432/{PROD}")
    monkeypatch.setattr(cm, "_superuser_pw", lambda: "MK")

    # Nguoi goi tu dat CSDL test -> khong phai cua ta.
    monkeypatch.setenv("LTT_TEST_DATABASE_URL", "postgresql+psycopg://x@h/cua_ho_test")
    cm._xoa_scratch()
    assert ghi == []

    # Khong co superuser -> lan sau khong tao lai duoc -> giu.
    monkeypatch.delenv("LTT_TEST_DATABASE_URL")
    monkeypatch.setattr(cm, "_superuser_pw", lambda: "")
    cm._xoa_scratch()
    assert ghi == []

    monkeypatch.setattr(cm, "_superuser_pw", lambda: "MK")
    cm._xoa_scratch()
    assert ghi == [("postgresql+psycopg://postgres:MK@h:5432/postgres",
                    pg_ten_cay.cau_xoa_csdl_test(PROD, cm.HAU_TO, cm.ROOT))]


# ── 3. Phan loai cua `tools/don_csdl_test.py` ──────────────────────────────

VT = "7ddc8630"


@pytest.mark.parametrize("ten,ket_noi,cay_cu,nhom", [
    (PROD, 0, False, "GIU"),
    ("postgres", 0, False, "GIU"),
    ("template1", 0, False, "GIU"),
    (f"{PROD}_multiproc_test_{VT}", 0, False, "GIU"),        # cay con song
    (f"{PROD}_wf_migration_test_deadbeef", 0, False, "XOA"),  # cay da go
    (f"{PROD}_wf_migration_test_deadbeef", 1, False, "GIU"),  # dang co ket noi
    (f"{PROD}_m1_dientap_test", 0, False, "XOA"),             # ten cu, het cay dung
    (f"{PROD}_m1_dientap_test", 0, True, "GIU"),              # ten cu, con cay ma cu
    ("ltt_multiproc_test", 0, False, "XOA"),
    ("ltt_vps_v4_test_" + "0" * 32, 0, False, "XOA"),
    ("ltt_vps_v4_test_" + "0" * 32, 2, False, "GIU"),
    ("ltt_drill_dst_20260101000000", 0, False, "XOA"),
    (f"{PROD}_test", 0, False, "KHAC"),                       # ten la: khong dong toi
    ("csdl_cua_app_khac", 0, False, "KHAC"),
])
def test_phan_loai(ten, ket_noi, cay_cu, nhom):
    import don_csdl_test as dc

    assert dc.phan_loai(ten, ket_noi, PROD, {VT}, cay_cu)[0] == nhom


def test_nhom_XOA_luon_qua_duoc_rao_cau_xoa():
    """Phan loai va rao la HAI noi — moi ten phan loai cho XOA phai qua rao."""
    import don_csdl_test as dc

    for ten in (f"{PROD}_multiproc_test_deadbeef", f"{PROD}_m1_dientap_test",
                "ltt_vps_v4_test_" + "f" * 32, "ltt_drill_src_20260101000000"):
        assert dc.phan_loai(ten, 0, PROD, set(), False)[0] == "XOA"
        pg_ten_cay.cau_xoa(ten, PROD)


# ── 4. Quet kho: tep nao TAO CSDL phai co duong XOA ────────────────────────

def _ten_goi(node: ast.Call) -> str:
    f = node.func
    return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")


def _docstring_ids(cay: ast.AST) -> set[int]:
    ra = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
                ra.add(id(n.body[0].value))
    return ra


def _parse(nguon: str) -> ast.AST:
    # Tep khac trong kho co escape cu (`'\d'`...) -> SyntaxWarning khong lien quan.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(nguon)


def tao_ma_khong_xoa(nguon: str) -> bool:
    """True neu nguon TAO CSDL ma khong co duong XOA nao."""
    cay = _parse(nguon)
    doc = _docstring_ids(cay)
    tao = xoa = False
    for n in ast.walk(cay):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc:
            chu = n.value.lower()
            tao |= "create database" in chu or "createdb" in chu
            xoa |= "dropdb" in chu or "drop database" in chu
        elif isinstance(n, ast.Call):
            ten = _ten_goi(n)
            tao |= ten.endswith("_tao_neu_thieu")
            xoa |= ten in ("cau_xoa", "cau_xoa_csdl_test")
    return tao and not xoa


def test_bo_quet_DO_duoc_tren_nguon_thieu_duong_xoa():
    thieu = 'def f(c, ten):\n    c.execute(f\'CREATE DATABASE "{ten}"\')\n'
    du = thieu + "    c.execute(cau_xoa_csdl_test(a, b, c))\n"
    goi = "def g():\n    scratch._tao_neu_thieu(url, name, live)\n"
    chi_docstring = '"""chi CREATE DATABASE moi"""\n'
    assert tao_ma_khong_xoa(thieu)
    assert not tao_ma_khong_xoa(du)
    assert tao_ma_khong_xoa(goi)
    assert not tao_ma_khong_xoa(chi_docstring)
    # BAT DOI XUNG (do 23/09): bo quet nhan TAO o CA HAI tu vung
    #   (`create database` SQL va `createdb` CLI) nhung nhan XOA o CHI
    #   MOT (`dropdb`). Nen mot tep dung cap SQL day du bi bao oan:
    #   `test_2200` co 4 CREATE DATABASE va 3 DROP DATABASE ma van bi ke
    #   ten. Hai nua cua mot phep do phai dung CUNG mot tu vung.
    cap_sql = thieu + '    c.execute("DROP DATABASE IF EXISTS x")'
    assert not tao_ma_khong_xoa(cap_sql), (
        'cap CREATE/DROP DATABASE day du la DU duong xoa')


def test_moi_tep_tao_CSDL_trong_kho_deu_co_duong_xoa():
    tep = sorted((GOC / "tools").glob("*.py")) + sorted((GOC / "tests").glob("test_*.py"))
    tao_ro = [p.relative_to(GOC).as_posix() for p in tep
              if p.name != pathlib.Path(__file__).name
              and tao_ma_khong_xoa(p.read_text(encoding="utf-8", errors="replace"))]
    assert tao_ro == [], f"tao CSDL ma khong xoa (se de lai CSDL mo coi): {tao_ro}"


def test_moi_HAU_TO_khai_trong_tools_deu_nam_trong_HAU_TO_DA_BIET():
    thay = set()
    for p in (GOC / "tools").glob("*.py"):
        for n in _parse(p.read_text(encoding="utf-8", errors="replace")).body:
            if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                    and any(isinstance(t, ast.Name) and t.id == "HAU_TO" for t in n.targets)):
                thay.add(n.value.value)
    assert thay == set(pg_ten_cay.HAU_TO_DA_BIET), (
        f"khai: {sorted(thay)} | HAU_TO_DA_BIET: {sorted(pg_ten_cay.HAU_TO_DA_BIET)}")
