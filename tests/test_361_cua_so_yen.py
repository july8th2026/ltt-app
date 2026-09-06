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
    #    tài nguyên thứ hai, **kể cả khi hai bên vẫn khớp nhau**, và cũng đỏ nếu
    #    ai đó chỉ đổi khoảng trắng. Đã xảy ra thật: `ff4bd527` thêm
    #    `postgres_test` vào gate và phép kiểm này đỏ, trong khi lỗi THẬT là
    #    `TAI_NGUYEN` chưa đổi theo. Mệnh đề cần chốt là "hai bên khai CÙNG MỘT
    #    TẬP", không phải "gate có chứa đúng chuỗi này".
    ma_gate = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    cua_gate = set()
    for n in _ast.walk(_ast.parse(ma_gate)):
        if not (isinstance(n, _ast.Call) and getattr(n.func, "id", "") == "Step"):
            continue
        ten = n.args[0].value if n.args and isinstance(n.args[0], _ast.Constant) else ""
        if not ten.startswith("bo test"):
            continue
        kw = next((k.value for k in n.keywords if k.arg == "tai_nguyen"), None)
        assert kw is not None, f"buoc `{ten}` cua gate khong khai tai nguyen"
        cua_gate |= {e.value for e in kw.elts}

    assert cua_gate, "khong tim thay buoc `bo test` nao trong gate.py"
    assert set(tn.TAI_NGUYEN) == cua_gate, (
        f"test_nhanh khai {sorted(tn.TAI_NGUYEN)} nhung gate khai "
        f"{sorted(cua_gate)} cho buoc `bo test` - hai ben khong thay nhau")


def test_duoi_gate_thi_KHONG_xin_khoa():
    """`_to_tien_la_gate` phai tra True khi CO to tien la gate, False khi khong.

    ⛔ Khoa la mot tep `O_EXCL`, **khong tai nhap**. `gate.py` goi
    `test_nhanh.py` nhu tien trinh con o bon cho **trong khi dang giu**
    `cpu_nhieu`. Neu tep con cung xin thi no cho chinh to tien cua minh, het
    `--cho` roi chen — tuc ban va lam **moi** luot gate cham them dung bang
    thoi gian cho roi quay ve trang thai cu.

    ⭐ Hoi **quan he** (`ppid`), dung hoi **nhan**.

    🔴 **Ban dau cua phep kiem nay SAI, va gate bat duoc.** No khang dinh
       `_to_tien_la_gate() is False` — tuc chot mot **su that moi truong** chu
       khong phai mot **tinh chat cua ma**. Chay `pytest` tay thi xanh; nhung khi
       **gate** chay bo test thi pytest THAT SU dang o duoi `gate.py`, nen no do:

           FAILED test_361::test_duoi_gate_thi_KHONG_xin_khoa

       Dung bay 'chay rieng xanh ma gate do'. Ban nay tiem to tien vao thay vi
       doc to tien that, nen no dung o CA HAI noi.
    """
    import test_nhanh as tn                       # noqa: PLC0415

    PY = ("python.exe", ["python.exe", "tools/gate.py", "--ho-so", "day-du"])
    assert tn._to_tien_la_gate([PY]) is True
    assert tn._to_tien_la_gate([]) is False
    assert tn._to_tien_la_gate([("bash.exe", ["bash.exe", "-c", "ls"]),
                                ("explorer.exe", ["explorer.exe"])]) is False

    # 🔴 Ca da tra gia 06/09: mot cau lenh chi NHAC ten cong cu.
    #
    #    To tien cua pytest la `bash.exe -c "<CA cau lenh>"`. Ban truoc khop
    #    chuoi con nen bat ky cau lenh nao co chu `gate.py` — mot `grep`, mot
    #    ghi chu — cung lam `test_nhanh` LANG LE bo khoa. Do duoc: hai lenh
    #    giong het nhau tru mot `echo` vo hai, mot ben passed mot ben failed.
    vo = ("bash.exe", ["bash.exe", "-c",
                       "grep -n gate.py tools/*.py && python tools/test_nhanh.py"])
    assert tn._to_tien_la_gate([vo]) is False, (
        "van ban cau lenh bi doc thanh 'dang chay duoi gate'")

    assert tn._la_gate("python.exe", ["python.exe", "tools/gate.py"]) is True
    assert tn._la_gate("python.exe",
                       ["python.exe", "D:" + chr(92) + "x" + chr(92) + "gate.py"]) is True
    assert tn._la_gate("python.exe", ["python.exe", "-m", "pytest"]) is False
    assert tn._la_gate("timeout.exe",
                       ["timeout.exe", "2400", "python", "tools/gate.py"]) is False, (
        "vo `timeout` khong phai gate; tien trinh python ben duoi no moi la")

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


def _bat_chay(monkeypatch):
    """Thay `_chay` bang ham ghi nhan. Tra ve danh sach cac lan goi."""
    import test_nhanh as tn                       # noqa: PLC0415

    goi: list[tuple[list, str]] = []

    def gia(argv, nhan):
        goi.append((argv, nhan))
        return 0, 0.0

    monkeypatch.setattr(tn, "_chay", gia)
    return goi


def test_main_cua_test_nhanh_THUC_SU_chay_pha_1(monkeypatch):
    """🔴 Phep kiem HANH VI — va nam phep kiem AST tren KHONG thay duoc no.

    06/09/2026 mot phien khac tach ham trong chinh tep nay va cat nham cho:
    hai pha pytest roi vao **ma chet sau mot `return`**. Ket qua:

        python tools/test_nhanh.py -n 2 ...  ->  thoat 0,114s, ma 0, KHONG chay gi
        gate.py                             ->  [PASS] bo test (song song)  0.1s

    Buoc nang nhat kho, **xanh**, trong mot phan muoi giay.

    ⛔ Va **nam banh coc AST deu xanh suot** luc ay — ke ca cai vua duoc chung
       minh la *do duoc* bang self-test hai chieu. Chung hoi *"ma co con khoi
       `with CuaSoYen` khong"*, tuc hoi **hinh dang** — va hinh dang van dung
       khi cong cu da chet.

    ⭐ Bai hoc tong quat hon ca ban va: **"do duoc" va "do dung thu can do" la
       HAI cau hoi.** Tiem lai ban cu chung minh phep kiem **phan biet duoc hai
       ban**; no khong chung minh phep kiem **quan sat thu ta can**.
    """
    import test_nhanh as tn                       # noqa: PLC0415

    goi = _bat_chay(monkeypatch)
    # Bo qua duong xin khoa: phep kiem nay hoi MOT cau — main co cham toi viec
    # that khong. Duong khoa da co bon phep kiem khac canh.
    monkeypatch.setattr(tn, "_to_tien_la_gate", lambda: True)
    monkeypatch.setattr(sys, "argv", ["test_nhanh.py", "-n", "2"])

    tn.main()

    assert goi, "main() KHONG cham toi `_chay` - cong cu chet ma van tra 0"
    assert any("PHA 1" in nhan for _, nhan in goi), (
        f"khong co pha 1 trong cac lan goi: {[n for _, n in goi]}")


def test_duong_XIN_KHOA_cung_phai_cham_toi_pha_1(monkeypatch):
    """Cung menh de, nhung **di qua khoi `with CuaSoYen`**.

    ⚠️ Thieu phep kiem nay thi mot loi **chi xay ra tren nhanh co khoa** se lot:
       phep kiem tren di duong tat, nen no mu voi dung nhanh ban va them vao.

    ⛔ Khoa di vao `tmp_path` nho fixture `khoa_rieng` — **khong** dung khoa
       that. Mot luot gate cua phien khac co the dang giu no ngay luc bo test
       nay chay.
    """
    import test_nhanh as tn                       # noqa: PLC0415

    goi = _bat_chay(monkeypatch)
    monkeypatch.setattr(tn, "_to_tien_la_gate", lambda: False)
    monkeypatch.setattr(sys, "argv",
                        ["test_nhanh.py", "-n", "2", "--cho", "0.01"])

    tn.main()

    assert any("PHA 1" in nhan for _, nhan in goi), (
        "duong CO khoa khong cham toi pha 1")
    # Va khoa phai duoc NHA sau khi xong.
    assert cy._doc() is None, "khoa khong duoc nha sau khi main() xong"


def test_nhac_TEN_gate_trong_cau_lenh_KHONG_bi_coi_la_dang_o_duoi_gate():
    """🔴 Lỗi nặng nhất của bản vá, phiên Mobile V1 tìm ra.

    Tổ tiên của `pytest` thường là một vỏ `bash.exe -c "<cả câu lệnh>"`. Bản đầu
    của `_to_tien_la_gate` làm `"gate.py" in " ".join(cmdline)`, nên **bất kỳ**
    câu lệnh nào **nhắc tên** `gate.py` — một `echo`, một `grep`, một docstring
    — cũng làm `test_nhanh` **lặng lẽ bỏ khoá**.

    ⚠️ Nó đau đúng cho ai hay nhắc tên công cụ nhất: **các phiên đang phối hợp
       với nhau**, tức đúng lúc cần khoá nhất.

    ⭐ Tôi viết luật *"hỏi quan hệ, đừng hỏi nhãn"* rồi khớp một **chuỗi con**
       trên cmdline của quan hệ ấy. Siết thêm một bậc: hỏi **tên tệp được thi
       hành**, đừng hỏi **văn bản câu lệnh**.
    """
    import test_nhanh as tn                       # noqa: PLC0415

    BS = chr(92)
    vo_bash = [
        ("bash.exe", ["C:/Program Files/Git/bin/bash.exe", "-c",
                      'echo "xem tools/gate.py roi chay test"'])]
    assert tn._to_tien_la_gate(vo_bash) is False, (
        "mot cau lenh NHAC ten gate.py bi doc thanh dang o duoi gate")

    # Va gate THAT van phai nhan ra duoc, ca hai kieu duong dan.
    assert tn._to_tien_la_gate(
        [("python.exe", ["C:/py/python.exe", "tools/gate.py", "--ho-so", "day-du"])]
    ) is True
    assert tn._to_tien_la_gate(
        [("python.exe", ["C:/py/python.exe", "D:" + BS + "t" + BS + "gate.py"])]
    ) is True

    # Mot tien trinh python KHAC thi khong.
    assert tn._to_tien_la_gate(
        [("python.exe", ["C:/py/python.exe", "tools/test_nhanh.py", "-n", "6"])]
    ) is False


def test_luot_KHONG_chay_test_nao_thi_KHONG_duoc_xanh():
    """🔴 Cổng cuối cho tai nạn 06/09, và nó hỏi HÀNH VI chứ không hỏi hình dạng.

    Hôm ấy một phép tách hàm làm hai pha pytest rơi vào **mã chết sau một
    `return`**: `tools/test_nhanh.py` thoát sau **0,114 giây**, mã **0**, và
    **không chạy một test nào**. `gate.py` in `[PASS] bo test (song song) 0.1s`.

    ⛔ **Cả năm bánh cóc AST lúc ấy đều xanh** — chúng hỏi *"còn khối `with`
       không"*, *"còn nhập không"*, *"khai đúng tài nguyên không"*. Hình dạng mã
       vẫn đúng khi công cụ đã chết. Dấu hiệu duy nhất là **con số giây**, thứ
       không ai đọc, và nó chỉ lộ ra sau ~25 phút vì tôi tình cờ đọc nó.

    ⭐ `_SO_LAN_CHAY` chỉ tăng **sau khi** một tiến trình pytest đã được phóng.
       Một khẳng định nằm **phía sau** việc thi hành thì không thể đúng khi công
       cụ bất động — đó là thứ phân biệt nó với mọi bánh cóc AST ở trên.
    """
    import test_nhanh as tn                       # noqa: PLC0415

    cu, cu_coy = tn._SO_LAN_CHAY, tn._CO_Y_KHONG_CHAY
    try:
        tn._CO_Y_KHONG_CHAY = False
        tn._SO_LAN_CHAY = 0
        assert tn._chot(0) == tn.MA_KHONG_CHAY_GI, (
            "luot RONG ma van tra 0 — cong cuoi khong hoat dong")
        tn._SO_LAN_CHAY = 1
        assert tn._chot(0) == 0, "luot CO chay bi cong cuoi chan nham"
        tn._SO_LAN_CHAY = 0
        assert tn._chot(1) == 1, "ma loi that phai di qua nguyen ven"

        # ⛔ Miễn trừ CỐ Ý phải còn nguyên, nếu không `gate --vong-lap` đỏ oan.
        #
        #    Sau một lượt xanh hết, cache `lastfailed` rỗng ⇒ `--lf` **cố ý**
        #    không chạy gì và trả 0. Trạng thái ấy nhìn từ ngoài **giống hệt**
        #    tai nạn 06/09 — cả hai đều là "không tiến trình pytest nào chạy".
        #    Nhưng một cái là QUYẾT ĐỊNH, cái kia là TAI NẠN.
        #
        # ⭐ Gộp hai trạng thái ấy làm một thì hoặc ta báo động giả mỗi lần
        #    `--vong-lap` chạy sau một lượt xanh, hoặc phải nới cổng đến mức
        #    nó bỏ lọt chính tai nạn nó sinh ra để bắt.
        tn._SO_LAN_CHAY = 0
        tn._CO_Y_KHONG_CHAY = True
        assert tn._chot(0) == 0, (
            "luot CO Y khong chay (vd `--lf` cache rong) bi chan nham - "
            "`gate --vong-lap` se do oan sau moi luot xanh")
    finally:
        tn._SO_LAN_CHAY, tn._CO_Y_KHONG_CHAY = cu, cu_coy

    assert tn.MA_KHONG_CHAY_GI not in (0, 1, 5), (
        "ma phai KHAC 0/1/5 de phan biet 'khong chay gi' voi 'co test do' "
        "va voi 'pytest thu thap 0 test'")
