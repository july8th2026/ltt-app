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

import ast
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

    Nó chỉ phải **nói rõ** rằng lượt này có thể bị nhiễu — và `da_giu` RỖNG
    chính là thứ bên gọi đọc để nói câu đó.

    ⭐ SỬA 2026-09-02: trước đây `da_giu` là `bool` và chốt này viết `is False`.
       Khi cửa sổ yên đổi sang khoá theo TÊN tài nguyên, `da_giu` thành **danh
       sách tài nguyên đang giữ**, nên "không giữ gì" nay là `[]`. Điều được
       bảo vệ không đổi một chút nào; chỉ phép so `is False` là không còn dùng
       được. `not k.da_giu` đúng với cả hai kiểu và vẫn đo đúng thứ cần đo.
    """
    _ghi_khoa(os.getpid(), tuoi_s=5)
    with cy.CuaSoYen("nguoi-sau", "gate", cho_toi_da_s=0.2) as k:
        assert not k.da_giu, "chờ quá hạn mà vẫn tưởng mình giữ được khoá"
    assert cy.TEP_KHOA.exists(), "khong duoc cuop khoa cua nguoi dang giu"


def test_bat_False_thi_khong_dung_toi_khoa():
    _ghi_khoa(os.getpid(), tuoi_s=5)
    with cy.CuaSoYen("A", "gate", bat=False) as k:
        assert not k.da_giu, "bat=False mà vẫn giữ khoá"
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
    ma = (GOC / "tools" / "cua_so_yen.py").read_text(encoding="utf-8")
    xau = [a.value for n in ast.walk(ast.parse(ma))
           if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print"
           for a in ast.walk(n)
           if isinstance(a, ast.Constant) and isinstance(a.value, str)
           and not a.value.isascii()]
    assert not xau, f"chuoi in ra khong thuan ASCII: {xau}"

# ── 4. `test_nhanh.py` phải XIN khoá — và phải BIẾT khi nào đừng xin ────────
#
# 🔴 Trước 06/09/2026 `tools/test_nhanh.py` **không có một dòng nào** xin khoá.
#    Hệ quả đo được đêm 05–06/09: `cua_so_yen trang-thai` báo `RẢNH` trong khi
#    máy đang chạy **ba** lượt gate — `test_nhanh` và `pytest` gõ tay chạy hoàn
#    toàn **vô hình** với cơ chế này.
#
# ⭐ Và nhắn tin **không** đóng được lỗ hổng ấy: hai phiên bấm cách nhau **25
#    giây**, cả hai đều đo trước khi bấm, cả hai đều thấy máy trống, cả hai đều
#    đúng lúc đo. Khe giữa *đo* và *bấm* **không có đáy**.

def _cay_test_nhanh() -> ast.Module:
    return ast.parse((GOC / "tools" / "test_nhanh.py").read_text(encoding="utf-8"))


def test_test_nhanh_CO_xin_khoa():
    """Mệnh đề: tệp ấy phải **dùng** `CuaSoYen`, không chỉ nhắc tên nó.

    ⛔ Đọc AST chứ không `grep`: một chú thích *"nên xin khoá"* cũng khớp `grep`,
       và đó đúng là trạng thái tệp này ở trước bản vá — biết mà không làm.
    """
    cay = _cay_test_nhanh()
    nhap = {a.name for n in ast.walk(cay) if isinstance(n, ast.ImportFrom)
            for a in n.names}
    assert "CuaSoYen" in nhap, "test_nhanh.py khong nhap CuaSoYen"

    goi = {getattr(n.func, "id", "") for n in ast.walk(cay)
           if isinstance(n, ast.Call)}
    assert "CuaSoYen" in goi, "co nhap ma khong goi - khoa khong duoc xin"


def test_test_nhanh_khai_CUNG_tai_nguyen_voi_gate():
    """Hai bên phải khai **cùng một chuỗi**, nếu không thì không thấy nhau.

    🔴 Hai lượt cùng ăn CPU mà khai hai tên tài nguyên khác nhau thì
       `cua_so_yen` coi chúng là hai việc **độc lập** và cho cả hai chạy. Khoá vẫn
       hoạt động đúng; nó chỉ đang bảo vệ nhầm thứ.
    """
    import test_nhanh as tn                       # noqa: PLC0415

    import ast as _ast                           # noqa: PLC0415

    # 🔴 ĐỌC AST, đừng khớp CHUỖI. Bản trước khẳng định
    #    `'tai_nguyen=("cpu_nhieu",)' in ma_gate` — nó đỏ ngay khi gate thêm một
    #    tài nguyên thứ hai, **kể cả khi hai bên vẫn khớp nhau**, và nó cũng đỏ
    #    nếu ai đó chỉ đổi khoảng trắng. Mệnh đề cần chốt không phải "gate có
    #    chứa đúng chuỗi này" mà "hai bên khai CÙNG MỘT TẬP".
    ma_gate = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    cua_gate = set()
    for n in _ast.walk(_ast.parse(ma_gate)):
        if not (isinstance(n, _ast.Call) and getattr(n.func, "id", "") == "Step"):
            continue
        ten = n.args[0].value if n.args and isinstance(n.args[0], _ast.Constant) else ""
        if not ten.startswith("bo test"):
            continue
        tn_kw = next((k.value for k in n.keywords if k.arg == "tai_nguyen"), None)
        assert tn_kw is not None, f"buoc `{ten}` cua gate khong khai tai nguyen"
        cua_gate |= {e.value for e in tn_kw.elts}

    assert cua_gate, "khong tim thay buoc `bo test` nao trong gate.py"
    assert set(tn.TAI_NGUYEN) == cua_gate, (
        f"test_nhanh khai {sorted(tn.TAI_NGUYEN)} nhung gate khai "
        f"{sorted(cua_gate)} cho buoc `bo test` - hai ben khong thay nhau")


def test_duoi_gate_thi_KHONG_xin_khoa():
    """⛔ Khoá là một tệp `O_EXCL`, **không tái nhập**.

    `gate.py` gọi `test_nhanh.py` như tiến trình con ở bốn chỗ **trong khi đang
    giữ** `cpu_nhieu`. Nếu tệp con cũng xin thì nó chờ chính tổ tiên của mình, hết
    `--cho` rồi chèn — tức bản vá làm **mọi** lượt gate chậm thêm đúng bằng thời
    gian chờ rồi quay về trạng thái cũ.

    ⭐ Hỏi **quan hệ** (`ppid`), đừng hỏi **nhãn**.
    """
    import test_nhanh as tn                       # noqa: PLC0415

    assert tn._to_tien_la_gate() is False, (
        "pytest khong chay duoi gate.py ma ham bao la co")


def test_so_loi_khai_ra_KHONG_bao_gio_la_khong():
    """⛔ Khai 0 làm cả cơ chế vô dụng một cách **im lặng**.

    Lượt khác đọc bản ghi, thấy "giữ 0 lõi", rồi kết luận máy còn trống. Ngân
    sách per-MÁY của `loi_phien_khac_dang_giu` dựa hẳn vào con số này.
    """
    import test_nhanh as tn                       # noqa: PLC0415

    assert tn._so_loi_se_dung("6") == 6
    assert tn._so_loi_se_dung("auto") >= 1
    assert tn._so_loi_se_dung("") >= 1            # rac cung phai ra >= 1


def test_bo_khoa_thi_phep_kiem_tren_PHAI_do():
    """SELF-TEST hai chiều: một phép kiểm chưa chứng minh nó **đỏ được** thì chưa
    phải phép kiểm.

    Dựng lại **hình dạng cũ** của tệp (không nhập, không gọi `CuaSoYen`) và
    khẳng định `test_test_nhanh_CO_xin_khoa` sẽ đỏ với nó.
    """
    cu = ast.parse(chr(10).join(["import argparse", "", "def main():", "    return 0"]))
    nhap = {a.name for n in ast.walk(cu) if isinstance(n, ast.ImportFrom)
            for a in n.names}
    goi = {getattr(n.func, "id", "") for n in ast.walk(cu)
           if isinstance(n, ast.Call)}
    assert "CuaSoYen" not in nhap and "CuaSoYen" not in goi, (
        "phep kiem tren KHONG phan biet duoc ban cu voi ban moi => vo dung")


def test_main_cua_test_nhanh_THUC_SU_chay_pha_1():
    """⛔ Bánh cóc HÌNH DẠNG không đủ — đã trả giá ngày 06/09.

    Các phép kiểm ở trên hỏi *"còn khối `with CuaSoYen` không"*, *"còn nhập
    không"*, *"khai đúng tài nguyên không"* — tất cả đều đọc **cấu trúc mã**.

    🔴 Hôm ấy `tools/test_nhanh.py` thoát ngay lập tức, mã 0, **không chạy một
       test nào** (một phép tách hàm cắt nhầm chỗ làm hai pha rơi vào vùng mã
       chết sau một `return`) — và **mọi** bánh cóc AST vẫn xanh, vì hình dạng
       mã không đổi. `gate.py` in `[PASS] bo test (song song) 0.1s`; dấu hiệu
       duy nhất là **con số giây**, thứ không ai đọc.

    ⭐ Câu hỏi này chỉ trả lời được **bằng cách thi hành**: gọi thẳng `main()`
       với `_chay` thay bằng một hàm ghi nhận, rồi hỏi pha 1 có được chạm tới
       không. Không subprocess, chạy tức thì.
    """
    import importlib                              # noqa: PLC0415

    tn = importlib.import_module("test_nhanh")
    goi: list[str] = []

    def _gia(argv, nhan):
        goi.append(nhan)
        return 0, 0.0

    cu_chay, cu_argv = tn._chay, sys.argv
    try:
        tn._chay = _gia
        sys.argv = ["test_nhanh.py", "--khong-khoa", "-n", "2"]
        ma = tn.main()
    finally:
        tn._chay, sys.argv = cu_chay, cu_argv

    assert any("PHA 1" in n for n in goi), (
        f"main() khong cham toi pha 1 - no goi: {goi}")
    assert ma == 0


def test_nhac_TEN_cong_cu_trong_cau_lenh_KHONG_bi_coi_la_dang_o_duoi_gate():
    """🔴 Đo 06/09: hai lệnh giống hệt nhau, khác đúng một `echo` vô hại.

    ```
    lenh KHONG chua chu do  ->  1 passed
    lenh CO   chua chu do   ->  1 failed
    ```

    Vì tổ tiên của pytest là `bash.exe -c "<cả câu lệnh>"`, nên bản cũ —
    `"gate.py" in " ".join(cmdline)` — coi **bất kỳ** câu lệnh nào nhắc tên công
    cụ là "đang chạy dưới gate", và `test_nhanh` **lặng lẽ bỏ khoá**.

    ⛔ Nó hỏng theo hướng dễ chịu: đúng những phiên hay nhắc tới công cụ nhất —
       tức những phiên đang phối hợp với nhau — là những phiên mất khoá.

    ⇒ Hỏi **tên tệp được thi hành**, đừng hỏi **văn bản của câu lệnh**.
    """
    import test_nhanh as tn                       # noqa: PLC0415

    vo_bash = ["bash.exe", "-c", "grep -n gate.py tools/*.py && python tools/test_nhanh.py"]
    assert tn._la_gate("bash.exe", vo_bash) is False, (
        "van ban cau lenh bi doc thanh 'dang chay duoi gate'")

    assert tn._la_gate("python.exe", ["python.exe", "tools/gate.py"]) is True
    assert tn._la_gate("python.exe",
                       ["python.exe", "D:" + chr(92) + "x" + chr(92) + "gate.py"]) is True
    assert tn._la_gate("python.exe", ["python.exe", "-m", "pytest"]) is False
    assert tn._la_gate("python.exe", ["python.exe"]) is False
    assert tn._la_gate("timeout.exe",
                       ["timeout.exe", "2400", "python", "tools/gate.py"]) is False, (
        "vo `timeout` khong phai gate; tien trinh python ben duoi no moi la")
