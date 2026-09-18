"""L1 (`gate.py --doi`) và L2 (`gate.py --pham-vi`) — sự cố 17/09/2026.

Bốn nguyên nhân gốc móc xích, đo trên máy chủ đêm 16→17/09:

1. `test_nhanh.py` pha 2 chạy `chung + co` với `chung` ĐÃ chứa danh sách tệp mà
   L1/L2 truyền vào ⇒ mọi L1/L2 chạy lại TOÀN BỘ test lần hai, nối tiếp 1 lõi
   (pytest pid 6020: 222 tệp, không `-n`). Hồi quy do ghép `777eaa11` (pha 2, khi
   chỉ chạy cả kho) với `65aef31d` (L2 truyền danh sách tệp).
2. `_steps_pham_vi` không truyền `-n` ⇒ `auto` (10), bỏ ngân sách 7 và phép co
   theo tải của `_ap_ngan_sach_thuc`.
3. Chờ khoá quá `--cho` (15 phút) thì gate CHEN — kể cả vào `postgres_test`;
   `--khong-khoa` cũng bỏ khoá `postgres_test`.
4. Các bước PostgreSQL dùng MỘT CSDL test cố định cho mọi cây ⇒ khoá là lớp bảo vệ
   duy nhất; một lượt chen = `relation "jobs" does not exist` (đỏ giả).

Và L1 gần như không bao giờ thu hẹp được: mọi tệp tài liệu/bản dịch/`.gitignore`
"không ai sở hữu" ⇒ tự nâng lên đầy đủ ⇒ bị từ chối giữa phiên ⇒ người dùng phải
dùng L2 (chậm hơn, và L2 thì dính lỗi 1–2).
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))

import cua_so_yen as cy  # noqa: E402
import test_nhanh as tn  # noqa: E402
import thanh_phan as tp  # noqa: E402


@pytest.fixture(autouse=True)
def khoa_rieng(tmp_path, monkeypatch):
    """Khoá vào `tmp_path` — không bao giờ đụng khoá thật của máy (xem test_361)."""
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(cy, "TEP_KHOA", tmp_path / "khoa.json")
    yield


# ── 1. Pha 2 KHÔNG BAO GIỜ lặp lại danh sách tệp ─────────────────────────────

def _tep_trong(argv: list[str]) -> list[str]:
    return [a for a in argv if a.startswith("tests/")]


def _ke_hoach(con_lai: list[str], n: str = "7"):
    return tn.ke_hoach_pha(con_lai, n)


def test_ca_kho_pha_2_chi_chay_ba_tep_ghi_cay():
    pha1, pha2 = _ke_hoach([])
    assert "-n" in pha1 and pha1[pha1.index("-n") + 1] == "7"
    assert _tep_trong(pha1) == []
    assert _tep_trong(pha2) == list(tn.TEP_NOI_TIEP)


def test_danh_sach_tep_pha_2_chi_lay_tep_ghi_cay_CO_trong_danh_sach():
    """🔴 Sự cố: 222 tệp chạy lại nối tiếp ở pha 2."""
    a = "tests/test_1300_lttcode_phat_hanh.py"
    b = "tests/test_209_versioning_status.py"
    pha1, pha2 = _ke_hoach([a, b])
    assert _tep_trong(pha1) == [a, b]
    assert f"--deselect={b}" in pha1
    assert _tep_trong(pha2) == [b], f"pha 2 lap lai danh sach: {pha2}"


def test_danh_sach_khong_co_tep_ghi_cay_thi_KHONG_co_pha_2():
    pha1, pha2 = _ke_hoach(["tests/test_1300_lttcode_phat_hanh.py", "tests/test_394_nen_da_phien.py"])
    assert pha2 is None
    assert len(_tep_trong(pha1)) == 2


def test_tuy_chon_pytest_duoc_giu_o_ca_hai_pha_va_khong_bi_coi_la_tep():
    b = "tests/test_306_banh_coc_bo_qua_va_dich.py"
    pha1, pha2 = _ke_hoach(["-x", "-p", "no:cacheprovider", b])
    for pha in (pha1, pha2):
        assert "-x" in pha and "no:cacheprovider" in pha
    assert _tep_trong(pha2) == [b]


def test_node_id_cua_tep_ghi_cay_di_vao_pha_2():
    nid = "tests/test_210_sdk_ecosystem.py::test_x"
    pha1, pha2 = _ke_hoach(["tests/test_1300_lttcode_phat_hanh.py", nid])
    assert nid not in pha1
    assert _tep_trong(pha2) == [nid]


def test_than_DUNG_ke_hoach_pha_khi_chay_that(monkeypatch):
    """Phép kiểm HÀNH VI: `_than` phải thật sự đi qua `ke_hoach_pha` (bài học test_361)."""
    goi: list[list[str]] = []
    monkeypatch.setattr(tn, "_chay", lambda argv, nhan: (goi.append(list(argv)), (0, 0.0))[1])
    a = "tests/test_1300_lttcode_phat_hanh.py"

    class A:
        n = "3"; lf = False; lf_rong_thi_khong_chay = False; k = ""; noi_tiep = False  # noqa: E702

    tn._than(A(), [a])
    assert len(goi) == 1, f"danh sach khong co tep ghi cay ma van co pha 2: {goi}"
    assert _tep_trong(goi[0]) == [a] and goi[0][goi[0].index("-n") + 1] == "3"


# ── 2. L1/L2 dùng cùng ngân sách worker với gate đầy đủ ──────────────────────

def test_buoc_test_pham_vi_mang_n_va_duoc_ap_ngan_sach(monkeypatch):
    import gate
    monkeypatch.setattr(gate, "loi_cho_bo_test", lambda **_: 5)
    [buoc] = gate._steps_pham_vi(["tests/test_1300_lttcode_phat_hanh.py"])
    assert "-n" in buoc.argv and buoc.argv[buoc.argv.index("-n") + 1] == "5"
    assert buoc.so_loi == 5
    monkeypatch.setattr(gate, "loi_cho_bo_test", lambda **_: 3)
    gate._ap_ngan_sach_thuc([buoc], "phien-test")
    assert buoc.argv[buoc.argv.index("-n") + 1] == "3", "ngan sach thuc khong ap duoc len L1/L2"


# ── 3. Không bao giờ chen vào postgres_test ──────────────────────────────────

def test_cho_qua_han_voi_postgres_test_thi_CHO_TIEP_khong_chen():
    assert cy.thu_giu("nguoi-truoc", "gate", "postgres_test")

    def nha_sau():
        time.sleep(1.5)
        cy.nha("nguoi-truoc", tai_nguyen="postgres_test")

    threading.Thread(target=nha_sau, daemon=True).start()
    with cy.CuaSoYen("nguoi-sau", "gate", cho_toi_da_s=0.2, tai_nguyen=("postgres_test",)) as k:
        assert k.da_giu == ["postgres_test"], "da chen vao postgres_test khi khoa con bi giu"
        assert k.da_cho_s >= 1.0


def test_cho_qua_han_voi_cpu_nhieu_van_chen_nhu_cu():
    """Chính sách cũ giữ nguyên cho tài nguyên chỉ là CPU: chen thì chạy nhỏ, không sai kết quả."""
    assert cy.thu_giu("nguoi-truoc", "gate", "cpu_nhieu")
    with cy.CuaSoYen("nguoi-sau", "gate", cho_toi_da_s=0.2, tai_nguyen=("cpu_nhieu",)) as k:
        assert not k.da_giu
    cy.nha("nguoi-truoc", tai_nguyen="cpu_nhieu")


def test_khong_khoa_van_giu_postgres_test():
    import gate
    assert gate.khoa_can_giu({"cpu_nhieu", "postgres_test"}, khong_khoa=True) == ("postgres_test",)
    assert gate.khoa_can_giu({"cpu_nhieu"}, khong_khoa=True) == ()
    assert gate.khoa_can_giu({"cpu_nhieu", "postgres_test"}, khong_khoa=False) == ("cpu_nhieu", "postgres_test")


# ── 4. CSDL test PostgreSQL tách theo cây làm việc ───────────────────────────

def test_ten_csdl_test_khac_nhau_giua_hai_cay_va_on_dinh_trong_mot_cay():
    import pg_ten_cay
    a = pg_ten_cay.ten_csdl_test("lttplatform", "_multiproc_test", Path(r"D:\LTTSTUDIOSAPP"))
    b = pg_ten_cay.ten_csdl_test("lttplatform", "_multiproc_test", Path(r"D:\LTTSTUDIOSAPP-lttcode-updater"))
    a2 = pg_ten_cay.ten_csdl_test("lttplatform", "_multiproc_test", Path("d:/lttstudiosapp/"))
    assert a != b and a == a2
    assert "test" in a and len(a) <= 63, "PostgreSQL cat ten > 63 byte"
    assert a.startswith("lttplatform_multiproc_test")


# ── 5. L1 thu hẹp được khi thay đổi kèm tài liệu / công cụ gate ─────────────

def test_tai_lieu_khong_ai_nhac_toi_thi_khong_keo_ca_kho():
    phan = tp.bi_anh_huong({"docs/LTTCODE/README.md"}, GOC)
    assert phan == set()


def test_tai_lieu_ma_test_DOC_thi_chay_dung_test_do():
    tests = tp.test_nhac_toi({"CLAUDE.md"}, GOC)
    assert "tests/test_61_setup_scripts.py" in tests
    assert tp.bi_anh_huong({"CLAUDE.md"}, GOC) is not None


def test_cong_cu_gate_khong_con_keo_ca_kho_nhung_chay_test_cua_no():
    phan = tp.bi_anh_huong({"tools/test_nhanh.py"}, GOC)
    assert phan is not None and "cong_cu" in phan
    tests = tp.test_nhac_toi({"tools/test_nhanh.py"}, GOC)
    assert "tests/test_361_cua_so_yen.py" in tests and "tests/test_309_toc_do_bo_test.py" in tests


@pytest.mark.parametrize("tep", ["tests/conftest.py", "requirements.txt", "requirements-server.txt"])
def test_tep_anh_huong_MOI_test_van_chay_tat_ca(tep):
    assert tp.bi_anh_huong({tep}, GOC) is None


def test_ma_khong_ai_so_huu_van_fail_open():
    assert tp.bi_anh_huong({"mot/duong/khong/ton/tai.py"}, GOC) is None


# ── 6. L2 NHIỀU thành phần một lượt (Task 11b, 18/09) ───────────────────────
#
# Đợt 2 (18/09) phải chạy 5 lượt L2 nối nhau (~75 phút) vì L1 từ chối khi chạm
# tệp dùng chung: mỗi lượt lặp lại toàn bộ bước kiểm tĩnh và bỏ sót giao nhau.
# Một lượt `--pham-vi a,b` (hoặc lặp cờ) = HỢP tệp test, bước chung chạy MỘT lần,
# bản ghi liệt kê MỌI thành phần.

HAI_TP = ("gateway:llm", "app:ltt_llm")

_NHO: dict = {}


@pytest.fixture
def do_thi_nho(monkeypatch):
    """Đồ thị kho đọc AST mất vài giây mỗi lần; các phép dưới đây hỏi CÙNG một
    kho nhiều lần ⇒ nhớ theo khoá, chỉ trong tệp này (không đổi hành vi)."""
    for ten in ("do_thi_phu_thuoc", "test_cua_thanh_phan", "cac_thanh_phan"):
        goc = getattr(tp, ten)

        def boc(root=tp.ROOT, *a, _goc=goc, _ten=ten, **kw):
            khoa = (_ten, str(root))
            if khoa not in _NHO:
                _NHO[khoa] = _goc(root, *a, **kw)
            return _NHO[khoa]
        monkeypatch.setattr(tp, ten, boc)


def test_tach_danh_sach_pham_vi_phay_va_lap_co():
    assert tp.tach_danh_sach("app:vps") == ["app:vps"]
    assert tp.tach_danh_sach("") == []
    assert tp.tach_danh_sach(["a,b", " c ", "b", ""]) == ["a", "b", "c"]
    assert tp.tach_danh_sach("a, b ,,a") == ["a", "b"]


def test_mo_rong_pham_vi_la_HOP_cua_tung_thanh_phan(do_thi_nho):
    a, b = HAI_TP
    ca = tp.mo_rong_pham_vi({a, b}, GOC)
    assert ca == tp.mo_rong_pham_vi({a}, GOC) | tp.mo_rong_pham_vi({b}, GOC)
    assert {a, b} <= ca
    assert (tp.test_can_chay(ca, GOC)
            == tp.test_can_chay(tp.mo_rong_pham_vi({a}, GOC), GOC)
            | tp.test_can_chay(tp.mo_rong_pham_vi({b}, GOC), GOC))


def test_gate_nhan_pham_vi_lap_co_va_phay():
    import gate
    p = gate._parser()
    assert tp.tach_danh_sach(p.parse_args(["--pham-vi", "a,b", "--pham-vi", "c"]).pham_vi) \
        == ["a", "b", "c"]
    assert tp.tach_danh_sach(p.parse_args(["--pham-vi", "app:vps"]).pham_vi) == ["app:vps"]
    assert not p.parse_args([]).pham_vi


def _thu_hep_voi(monkeypatch, pham_vi):
    import argparse

    import gate
    monkeypatch.setattr(gate, "loi_cho_bo_test", lambda **_: 4)
    args = argparse.Namespace(pham_vi=pham_vi, tu="")
    return gate._thu_hep(gate._steps(False), args, "pham-vi")


def test_gate_pham_vi_nhieu_HOP_test_va_buoc_chung_MOT_lan(monkeypatch, do_thi_nho):
    a, b = HAI_TP
    ra, ghi_chu = _thu_hep_voi(monkeypatch, [f"{a},{b}"])
    assert ra is not None, ghi_chu
    ten = [s.name for s in ra]
    assert len(ten) == len(set(ten)), f"buoc lap lai: {ten}"
    [buoc] = [s for s in ra if s.name == "bo test (pham vi)"]
    tep = {x for x in buoc.argv if x.startswith("tests/")}
    mong = tp.test_can_chay(tp.mo_rong_pham_vi({a, b}, GOC), GOC)
    assert tep == mong
    ra_a, _ = _thu_hep_voi(monkeypatch, [a])
    ra_b, _ = _thu_hep_voi(monkeypatch, [b])
    tep_a = {x for s in ra_a if s.name == "bo test (pham vi)" for x in s.argv if x.startswith("tests/")}
    tep_b = {x for s in ra_b if s.name == "bo test (pham vi)" for x in s.argv if x.startswith("tests/")}
    assert tep == tep_a | tep_b
    assert a in ghi_chu and b in ghi_chu


def test_gate_pham_vi_mot_thanh_phan_GIU_NGUYEN(monkeypatch, do_thi_nho):
    """Một thành phần: dạng chuỗi cũ và dạng danh sách mới cho cùng kết quả."""
    ra_moi, gc_moi = _thu_hep_voi(monkeypatch, ["app:ltt_llm"])
    ra_cu, gc_cu = _thu_hep_voi(monkeypatch, "app:ltt_llm")
    assert [(s.name, s.argv) for s in ra_moi] == [(s.name, s.argv) for s in ra_cu]
    assert gc_moi == gc_cu


def test_gate_pham_vi_co_thanh_phan_la_thi_KHONG_thu_hep(monkeypatch, do_thi_nho):
    ra, ghi_chu = _thu_hep_voi(monkeypatch, ["app:ltt_llm", "khong:ton_tai"])
    assert ra is None and "khong:ton_tai" in ghi_chu


def test_ban_ghi_gate_liet_ke_MOI_thanh_phan(tmp_path, monkeypatch):
    import json

    import gate
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    gate._ghi_ket_qua("pham-vi", [], "PASS", 1.0, None, False, sha="abc",
                      thanh_phan=["gateway:llm", "app:ltt_llm"])
    [tep] = (tmp_path / "test-results" / "gates").glob("*.json")
    ban_ghi = json.loads(tep.read_text(encoding="utf-8"))
    assert ban_ghi["thanh_phan"] == ["gateway:llm", "app:ltt_llm"]
