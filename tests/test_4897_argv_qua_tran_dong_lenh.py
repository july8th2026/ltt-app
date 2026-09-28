"""test_4897 — `[WinError 206]`: danh sách test dài phải qua tệp đối số `@tep`.

B11 kế hoạch (`docs/auto_scan_video_final/B11_PLAN_TONG_DON_NO_TRUOC_GATE.md`
§4), làn B, 28/09/2026: `gate.py --doi`/`--pham-vi` ghép TỪNG đường dẫn test
vào MỘT dòng lệnh `pytest`. Phạm vi 972-1001 tệp vượt trần **32.767 ký tự**
CreateProcess của Windows ⇒ bước `bo test` chết trong **0,0 giây** với
`[WinError 206] The filename or extension is too long` — mà 32 bước còn lại
vẫn chạy xong, nên dòng `RESULT` in ra như đã đo mà bộ test CHƯA HỀ chạy. Và
dòng `CHAY LAI DUNG PHEP DO` mà chính gate in ra cũng liệt kê ~1000 tệp, nên
chỉ dẫn nó đưa cho người đọc cũng không chạy nổi.

Chốt bằng cách DỰNG 1000 đường dẫn GIẢ và kiểm dòng lệnh sinh ra — KHÔNG chạy
1000 tệp thật, để bài kiểm tất định và nhanh (yêu cầu B11 §4).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))

import gate  # noqa: E402
import test_nhanh as tn  # noqa: E402

#: Trần CỨNG của Windows CreateProcess — KHÔNG phải trần AN TOÀN của ta
#: (`tn.TRAN_DONG_LENH_KY_TU`, cố ý thấp hơn để chừa biên). Vế đối chứng phải
#: chốt bằng con số cứng của hệ điều hành, không phải hằng số bản vá tự đặt.
TRAN_CUNG_WINDOWS = 32_767

TEP_GIA = [f"tests/test_gia_{i:04d}_khong_ton_tai.py" for i in range(1000)]


@pytest.fixture
def gate_rieng(tmp_path, monkeypatch):
    """`ghi_tep_doi_so` ghi vào `<GOC>/.gate/` — trỏ `GOC` sang `tmp_path` để
    không đụng `.gate/` thật của máy (nhiều phiên/worktree dùng chung sổ)."""
    monkeypatch.setattr(tn, "GOC", tmp_path)
    yield tmp_path


# ── 1. Danh sách ngắn: hành vi CŨ, không hề đụng tệp đối số ─────────────────

def test_danh_sach_ngan_thi_KHONG_dung_tep_doi_so(gate_rieng):
    argv, tep = tn.argv_an_toan(
        ["python", "-m", "pytest", "-q"],
        ["tests/test_1_a.py", "tests/test_2_b.py"], ten="ngan")
    assert tep is None
    assert argv == ["python", "-m", "pytest", "-q",
                    "tests/test_1_a.py", "tests/test_2_b.py"]
    assert not list(gate_rieng.glob(".gate/*"))


# ── 2. 1000 tệp GIẢ: dòng lệnh sinh ra không vượt trần ──────────────────────

def test_1000_tep_gia_sinh_dong_lenh_KHONG_vuot_tran(gate_rieng):
    dau = ["python", "-m", "pytest", "-n", "7", "-q"]
    argv, tep = tn.argv_an_toan(dau, TEP_GIA, ten="pham_vi_1000")
    assert tep is not None, "1000 tep phai vuot tran va chuyen sang @tep"
    dong_lenh = " ".join(argv)
    assert len(dong_lenh) <= TRAN_CUNG_WINDOWS, (
        f"dong lenh {len(dong_lenh)} ky tu van vuot tran cung {TRAN_CUNG_WINDOWS}")
    assert len(argv) == len(dau) + 1, "cac tuy chon phai giu nguyen dang chu"
    assert argv[-1] == f"@{tep}"
    # `-n` phai con nam TRAN VEN trong argv — `gate._ap_ngan_sach_thuc` tim no
    # bang chinh vi tri, khong duoc de no lot vao trong tep doi so.
    assert argv[argv.index("-n") + 1] == "7"
    noi_dung = tep.read_text(encoding="utf-8").splitlines()
    assert noi_dung == TEP_GIA, "tep doi so phai co DUNG 1000 duong dan, dung thu tu"


def test_doi_chung_KHONG_dung_tep_doi_so_thi_vuot_tran():
    """Vế đối chứng bắt buộc (B11 §4): thiếu tệp đối số thì nối chuỗi trực tiếp
    PHẢI vượt trần — thiếu vế này thì một bản vá vẫn nối chuỗi cũng xanh."""
    dong_lenh_tho = " ".join(["python", "-m", "pytest", "-n", "7", "-q", *TEP_GIA])
    assert len(dong_lenh_tho) > TRAN_CUNG_WINDOWS, (
        "1000 tep gia khong con du dai de chung minh WinError 206 -> tang so luong")


def test_argfile_nam_ngoai_anh_chup_cay_cua_gate(gate_rieng):
    """Tệp đối số phải nằm ngoài `THU_MUC_CHUP` (`gate._anh_chup_cay`) — nếu
    không, MỘT lượt gate sẽ tự báo "CÂY ĐÃ ĐỔI TRONG LÚC CHẠY" do chính nó ghi
    ra giữa lúc bước `bo test` đang chạy (xem `test_145`, cùng bất biến)."""
    _, tep = tn.argv_an_toan(["python", "-m", "pytest"], TEP_GIA, ten="chup_cay")
    assert tep is not None
    thu_muc_dau = tep.relative_to(gate_rieng).as_posix().split("/")[0]
    assert thu_muc_dau == ".gate"
    assert thu_muc_dau not in gate.THU_MUC_CHUP


# ── 3. `gate._steps_pham_vi` và `lenh_chay_lai` phải dùng CÙNG cơ chế ──────
#
# ⚠️ HAI phép dưới đây KHÔNG dùng `gate_rieng`: `lenh_chay_lai`/`_steps_pham_vi`
#    tính đường dẫn tệp đối số quan hệ với `gate.ROOT` thật (`.relative_to(ROOT)`),
#    nên phải giữ `test_nhanh.GOC` VÀ `gate.ROOT` khớp nhau — dùng `.gate/` THẬT
#    của worktree này (đã có sẵn trong `.gitignore`) rồi tự dọn trong `finally`.

def test_gate_steps_pham_vi_voi_1000_tep_KHONG_vuot_tran(monkeypatch):
    monkeypatch.setattr(gate, "loi_cho_bo_test", lambda **_: 7)
    tep_argfile = gate.ROOT / ".gate" / "argv_pham_vi.txt"
    try:
        [buoc] = gate._steps_pham_vi(TEP_GIA)
        dong_lenh = " ".join(buoc.argv)
        assert len(dong_lenh) <= TRAN_CUNG_WINDOWS, (
            f"argv cua buoc `bo test (pham vi)` dai {len(dong_lenh)} ky tu")
        assert buoc.argv[-1].startswith("@")
        assert "-n" in buoc.argv and buoc.argv[buoc.argv.index("-n") + 1] == "7"
    finally:
        tep_argfile.unlink(missing_ok=True)


def test_lenh_chay_lai_voi_1000_tep_do_KHONG_vuot_tran_va_noi_ro_cho():
    dau_ra = "\n".join(f"FAILED {t}::test_x - AssertionError" for t in TEP_GIA)
    s = gate.Step("bo test (song song)", [sys.executable, "tools/test_nhanh.py"],
                  gate.ROOT)
    s.ok = False
    s.tail = dau_ra
    tep_argfile = gate.ROOT / ".gate" / "argv_chay_lai.txt"
    try:
        [lenh] = gate.lenh_chay_lai([s])
        lenh_chay_duoc = lenh.split("   #", 1)[0].rstrip()
        assert len(lenh_chay_duoc) <= TRAN_CUNG_WINDOWS, (
            f"phan LENH CHAY DUOC dai {len(lenh_chay_duoc)} ky tu")
        assert lenh_chay_duoc.startswith("python -m pytest -n 7 -q @")
        assert "danh sach nam o" in lenh and ".gate" in lenh
    finally:
        tep_argfile.unlink(missing_ok=True)


# ── 4. `@tep` thật sự CHẠY ĐƯỢC với pytest (nhanh — 2 tệp có thật) ──────────

def test_tep_doi_so_pytest_doc_duoc_that():
    """Không tin lời khai pytest hỗ trợ `@tep` — chạy thật với `--collect-only`
    trên hai tệp CÓ THẬT trong kho, để bài kiểm vẫn nhanh và tất định."""
    a = "tests/test_1500_gate_l1_l2_khong_lap_khong_chen.py"
    b = "tests/test_1280_nhip_mot_l3.py"
    tep = tn.ghi_tep_doi_so(["-q", "--collect-only", a, b], "sanity_4897")
    try:
        ra = subprocess.run([sys.executable, "-m", "pytest", f"@{tep}"],
                            cwd=GOC, capture_output=True, text=True)
        assert ra.returncode == 0, ra.stdout + ra.stderr
        assert a.rsplit("/", 1)[-1] in ra.stdout
        assert b.rsplit("/", 1)[-1] in ra.stdout
    finally:
        tep.unlink(missing_ok=True)
