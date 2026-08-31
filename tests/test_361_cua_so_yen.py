"""test_361 — khoá "cửa sổ yên": xếp hàng cho các lượt đo đắt tiền.

Kho này thường có **ba phiên Claude cùng ghi một cây**, và ngày 31/08 cả hai
lượt `gate.py` chạy gần nhau đều cho **đỏ giả**: mỗi lượt thấy tệp của phiên kia
đổi giữa chừng. Sáu phút mỗi lượt, và kết quả không dùng được.

⛔ Thứ được chốt ở đây **không phải** "chạy nhanh hơn". Pha `bo test` đã lấy
   `-n auto` = mọi lõi, nên hai lượt song song chỉ chia đôi cùng một chiếc bánh.
   Cái khoá mua được là **một cửa sổ yên** và một hàng đợi nhìn thấy được.

🔴 Đường nguy hiểm nhất của một cái khoá không phải lúc nó khoá — mà lúc **người
   giữ chết**. Khoá treo vĩnh viễn biến cổng chất lượng thành thứ không ai chạy
   được, và cách sửa duy nhất là xoá một tệp mà không ai nhớ tên. Nên phần lớn
   tệp này đo đúng đường đó.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))

import cua_so_yen as cy  # noqa: E402


@pytest.fixture(autouse=True)
def khoa_rieng(tmp_path, monkeypatch):
    """Mỗi test một tệp khoá riêng.

    ⛔ Không được đụng vào khoá THẬT: một lượt gate của phiên khác có thể đang
       giữ nó ngay lúc bộ test này chạy, và cướp mất là làm hỏng đúng thứ tệp
       này sinh ra để bảo vệ.
    """
    monkeypatch.setattr(cy, "TEP_KHOA", tmp_path / "khoa.json")
    yield


# ── 1. Loại trừ lẫn nhau ────────────────────────────────────────────────────

def test_nguoi_thu_hai_bi_tu_choi():
    assert cy.thu_giu("A", "gate") is True
    assert cy.thu_giu("B", "gate") is False, (
        "hai luot gate cung luc chia doi 20 loi va nhan doi kha nang do sai")


def test_nha_roi_thi_nguoi_sau_vao_duoc():
    cy.thu_giu("A", "gate")
    assert cy.nha("A") is True
    assert cy.thu_giu("B", "gate") is True


def test_khong_nha_duoc_khoa_CUA_NGUOI_KHAC():
    cy.thu_giu("A", "gate")
    ban_ghi = json.loads(cy.TEP_KHOA.read_text(encoding="utf-8"))
    ban_ghi["pid"] = os.getpid() + 1          # giả vờ của phiên khác
    cy.TEP_KHOA.write_text(json.dumps(ban_ghi), encoding="utf-8")
    assert cy.nha("A") is False, "nha nham khoa cua phien khac la cuop cua so yen"
    assert cy.nha("A", ep=True) is True, "`--ep` phai van go duoc khoa treo"


# ── 2. Khoá treo — đường nguy hiểm nhất ─────────────────────────────────────

def _ghi_khoa(pid: int, tuoi_s: float = 0.0) -> None:
    cy.TEP_KHOA.write_text(json.dumps({
        "phien": "da-chet", "pid": pid, "lenh": "gate",
        "bat_dau_epoch": time.time() - tuoi_s}), encoding="utf-8")


def test_tien_trinh_giu_khoa_da_chet_thi_luot_sau_TU_DOAT():
    """Nếu không có nhánh này, một lần Ctrl-C khoá cổng lại vĩnh viễn."""
    con = subprocess.Popen([sys.executable, "-c", "pass"])
    con.wait()
    _ghi_khoa(con.pid)
    assert cy.thu_giu("moi", "gate") is True
    assert json.loads(cy.TEP_KHOA.read_text(encoding="utf-8"))["phien"] == "moi"


def test_khoa_qua_gia_thi_bi_doat_DU_tien_trinh_con_song():
    """PID có thể bị dùng lại, và một lượt gate không bao giờ chạy 2 giờ."""
    _ghi_khoa(os.getpid(), tuoi_s=cy.TUOI_TOI_DA_S + 60)
    assert cy.thu_giu("moi", "gate") is True


def test_tep_khoa_HONG_thi_don_di_chu_khong_ket():
    """Ngắt giữa chừng để lại tệp rỗng. Đọc không ra ≠ có người đang giữ."""
    cy.TEP_KHOA.write_text("{khong phai json", encoding="utf-8")
    assert cy.thu_giu("moi", "gate") is True


def test_khoa_CON_HIEU_LUC_thi_KHONG_bi_doat():
    """Chiều ngược lại phải đúng, nếu không cái khoá chẳng khoá gì cả."""
    _ghi_khoa(os.getpid(), tuoi_s=5)
    assert cy.thu_giu("ke-cuop", "gate") is False


# ── 3. `_con_song` không được giết thứ nó đang hỏi ─────────────────────────

def test_do_tien_trinh_con_song_KHONG_giet_no():
    """🔴 Trên Windows `os.kill(pid, 0)` gọi `TerminateProcess`.

    Tức phép "xem còn sống không" viết theo lối Unix sẽ **giết** đúng lượt gate
    của phiên khác. Phép kiểm này canh rằng ta không quay lại lối đó.
    """
    con = subprocess.Popen([sys.executable, "-c",
                            "import time; time.sleep(30)"])
    try:
        assert cy._con_song(con.pid) is True
        assert con.poll() is None, (
            "phep do 'con song khong' vua GIET tien trinh no dang hoi")
    finally:
        con.kill()
        con.wait()


def test_pid_khong_ton_tai_la_khong_song():
    con = subprocess.Popen([sys.executable, "-c", "pass"])
    con.wait()
    assert cy._con_song(con.pid) is False
    assert cy._con_song(0) is False
    assert cy._con_song(-1) is False


# ── 4. Xếp hàng thật: người sau vào được ngay khi người trước nhả ──────────

def test_xep_hang_roi_vao_duoc_khi_nguoi_truoc_nha():
    _ghi_khoa(os.getpid(), tuoi_s=5)

    import threading
    def nha_sau_mot_giay():
        time.sleep(1.0)
        cy.nha(ep=True)

    threading.Thread(target=nha_sau_mot_giay, daemon=True).start()
    t0 = time.monotonic()
    with cy.CuaSoYen("nguoi-sau", "gate", cho_toi_da_s=20) as k:
        assert k.da_giu, "phai vao duoc sau khi nguoi truoc nha"
    assert 0.5 < time.monotonic() - t0 < 15


def test_cho_qua_han_thi_VAN_CHAY_chu_khong_bo_cuoc():
    """Một cổng chất lượng từ chối chạy vì bận là một cổng không ai dùng.

    Nó chỉ phải **nói rõ** rằng lượt này có thể bị nhiễu — và `da_giu=False`
    chính là thứ bên gọi đọc để nói câu đó.
    """
    _ghi_khoa(os.getpid(), tuoi_s=5)
    with cy.CuaSoYen("nguoi-sau", "gate", cho_toi_da_s=0.2) as k:
        assert k.da_giu is False
    assert cy.TEP_KHOA.exists(), "khong duoc cuop khoa cua nguoi dang giu"


def test_bat_False_thi_khong_dung_toi_khoa():
    _ghi_khoa(os.getpid(), tuoi_s=5)
    with cy.CuaSoYen("A", "gate", bat=False) as k:
        assert k.da_giu is False
    assert json.loads(cy.TEP_KHOA.read_text(encoding="utf-8"))["phien"] == "da-chet"


# ── 5. Hai bất biến về chỗ đặt và về đầu ra ───────────────────────────────

def test_tep_khoa_KHONG_nam_trong_cay_kho():
    """🔴 `gate._anh_chup_cay()` quét `tools/`.

    Một tệp khoá trong đó sẽ tự làm bẩn phép đo của chính nó: ghi lúc bắt đầu,
    thấy `tools/...` đổi lúc kết thúc, rồi báo "cây đã đổi". Đúng lớp lỗi
    "gate tự nhiễu vào phép đo" đã ghi trong CLAUDE.md.
    """
    import cua_so_yen
    that = Path(cua_so_yen.TEP_KHOA).resolve()
    assert GOC.resolve() not in that.parents, f"{that} nam trong cay kho"


def test_moi_chuoi_IN_RA_deu_thuan_ASCII():
    """Console PowerShell 5.1 là CP1252.

    ⛔ Một emoji trong stdout của một công cụ đã từng làm cổng đỏ — ghi trong
       CLAUDE.md. Chú thích tiếng Việt thì thoải mái; thứ đi ra `stdout` thì không.
    """
    import ast

    ma = (GOC / "tools" / "cua_so_yen.py").read_text(encoding="utf-8")
    xau = [a.value for n in ast.walk(ast.parse(ma))
           if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print"
           for a in ast.walk(n)
           if isinstance(a, ast.Constant) and isinstance(a.value, str)
           and not a.value.isascii()]
    assert not xau, f"chuoi in ra khong thuan ASCII: {xau}"
