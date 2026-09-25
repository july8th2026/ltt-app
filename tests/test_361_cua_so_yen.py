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
import builtins
import sys
import tempfile
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

    🔴 HAI đòn bẩy, và bản đầu chỉ kéo một. `TEP_KHOA` là hằng số tính lúc
       **import**, và nó chỉ phủ tài nguyên `MAC_DINH`. Mọi tài nguyên **có
       tên** đi qua `_tep()` → `tempfile.gettempdir()` đọc **lúc gọi** — nên
       `test_cua_pytest_go_tay_...` (dòng ~559) lấy `_tep("postgres_test")` là
       lấy thẳng `ltt_khoa_postgres_test.json` **thật của máy**, rồi khẳng định
       nó xuất hiện và sau đó biến mất. Tức bộ kiểm này tạo và **xoá** một khoá
       thật, trong khi một lượt gate của phiên khác có thể đang giữ nó.

       Và nó **không đỏ** khi hỏng: phép kiểm chỉ nhìn khoá của chính nó.

    ⚠️ Đòn bẩy thư mục phải là `tempfile.tempdir`, KHÔNG phải biến môi trường:
       `gettempdir()` cache vào `tempfile.tempdir` sau lần gọi đầu, mà trong một
       lượt pytest thì nó đã được gọi từ lâu. Đo: đặt `os.environ["TEMP"]` →
       `gettempdir()` **không đổi**; đặt `tempfile.tempdir` → đổi.

    ⭐ `test_khoa_KHONG_nam_trong_cay_kho` vẫn đúng: `tmp_path` nằm ngoài kho.
    """
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
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


# ── 2c. THUA cuộc giành khoá treo — thua thì CHỜ, ⛔ không phải CHẾT (N-42) ──
#
# 🔴 Sự cố 25/09: ~10 phiên xếp hàng sau một khoá giữ 33 phút. Chủ khoá chết ⇒
#    **nhiều phiên cùng lao vào** giành một khoá treo. Trên Windows `unlink`
#    của phiên THUA nem `PermissionError` (WinError 5, "tiến trình khác đang mở
#    tệp") — ngoại lệ thoát thẳng ra khỏi `thu_giu`, giết `chay_nang.py`, và
#    lượt ấy ⛔ **không chạy một lệnh nào**.
#
# ⭐ Thua một cuộc đua là kết cục **bình thường**, ⛔ không phải lỗi. Đo CẢ HAI
#    chiều: thua thì xếp lại hàng, mà khoá treo THẬT thì vẫn phải giành được —
#    thiếu vế sau thì bản vá có thể làm **không ai** giành được khoá treo nữa.


def _chan_unlink_tep_khoa(monkeypatch, loi: OSError) -> None:
    """Tiêm lỗi ở ĐÚNG chỗ `unlink` của tệp khoá, không đụng tệp khác."""
    goc = Path.unlink

    def unlink(self, *a, **k):
        if self.name == cy.TEP_KHOA.name:
            raise loi
        return goc(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", unlink)


def test_THUA_cuoc_gianh_khoa_treo_thi_XEP_LAI_HANG_chu_khong_CHET(
        capsys, monkeypatch):
    con = subprocess.Popen([sys.executable, "-c", "pass"])
    con.wait()
    _ghi_khoa(con.pid)
    _chan_unlink_tep_khoa(
        monkeypatch, PermissionError(5, "Access is denied", str(cy.TEP_KHOA)))

    # ⛔ Không `pytest.raises`: thứ được chốt ở đây là ngoại lệ KHÔNG thoát ra.
    assert cy.thu_giu("thua-cuoc", "gate") is False, (
        "thua cuộc giành khoá treo phải trả False (= xếp lại hàng), "
        "không được để ngoại lệ giết cả lượt")
    ra = capsys.readouterr().out
    assert "thua cuoc gianh khoa treo" in ra, (
        "⛔ không nuốt lặng lẽ (N-19): một cuộc đua không ai thấy thì không ai "
        f"đo được nó xảy ra bao nhiêu lần. Đã in: {ra!r}")
    assert "PermissionError" in ra
    # Tệp của người kia còn nguyên: ta thua, ta không đụng được vào nó.
    assert json.loads(cy.TEP_KHOA.read_text(encoding="utf-8"))["phien"] == "da-chet"


def test_khoa_treo_THAT_thi_VAN_gianh_duoc_NHU_CU():
    """⭐ Vế ngược — thiếu nó thì bản vá có thể khoá cứng cả máy theo cách khác.

    Tệp mở được ⇒ ⛔ không có cuộc đua nào ⇒ đường giành khoá treo phải chạy
    trọn như trước bản vá, và bản ghi mới phải là của ta.
    """
    con = subprocess.Popen([sys.executable, "-c", "pass"])
    con.wait()
    _ghi_khoa(con.pid)
    assert cy.thu_giu("moi", "gate", so_loi=6) is True
    moi = json.loads(cy.TEP_KHOA.read_text(encoding="utf-8"))
    assert moi["phien"] == "moi"
    assert moi["so_loi"] == 6, (
        "bản đệ quy cũ gọi lại `thu_giu(phien, lenh, tai_nguyen)` và **đánh "
        "rơi `so_loi`** ⇒ lượt giành được khoá treo khai 0 lỗi; ngân sách của "
        "máy tính theo bản ghi đó là tính thiếu")


def test_gianh_lai_CO_TRAN_chu_khong_lap_vo_han(capsys, monkeypatch):
    """⛔ Không `retry` vô hạn: hết trần thì thoát, và NÓI RA vì sao.

    Dựng cảnh xấu nhất: tệp khoá treo **luôn** hiện ra lại ngay sau khi ta xoá
    (một phiên khác đang giữ nhịp). Bản đệ quy cũ sẽ quay vô hạn tới khi tràn
    ngăn xếp; bản mới phải dừng đúng `TRAN_GIANH_LAI` lần rồi xếp lại hàng.
    """
    con = subprocess.Popen([sys.executable, "-c", "pass"])
    con.wait()
    dem = {"n": 0}
    goc = cy.os.open

    def open_luon_bi_chiem(tep, *a, **k):
        if str(tep) == str(cy.TEP_KHOA):
            dem["n"] += 1
            _ghi_khoa(con.pid)          # người kia vừa chiếm lại
            raise FileExistsError(17, "File exists", str(tep))
        return goc(tep, *a, **k)

    monkeypatch.setattr(cy.os, "open", open_luon_bi_chiem)
    assert cy.thu_giu("kien-nhan", "gate") is False
    assert dem["n"] == cy.TRAN_GIANH_LAI, (
        f"phải dừng đúng {cy.TRAN_GIANH_LAI} lần, đã thử {dem['n']}")
    assert "xep lai hang" in capsys.readouterr().out


# ── 2b. Giữ khoá quá lâu phải LỘ RA ───────────────────────────────────────
#
# Luật 23/09 (CLAUDE.md, mục ⭐ Chạy agent): khoá bao ĐÚNG lệnh tính, nhả ngay
# khi tính xong. Nhưng một luật chỉ là giao ước cho tới khi có thứ đếm nó — nên
# một lượt giữ lâu bất thường phải tự nói ra, ở CẢ HAI phía:
#   · phía người CHỜ, để họ biết nên đợi hay đi làm việc khác;
#   · phía người GIỮ, để chính họ thấy mình vừa giữ bao lâu.
# ⛔ `TUOI_TOI_DA_S` (2 giờ) KHÔNG thay được việc này: nó là ngưỡng "coi như
#    treo, cho phép đoạt". Một lượt giữ 40 phút thì chưa treo — nó vẫn đúng
#    luật cũ mà vẫn làm cả máy đứng.


def test_nguong_giu_lau_NHO_HON_nguong_coi_nhu_treo():
    """Hai ngưỡng trả lời hai câu khác nhau, và phải xếp đúng thứ tự.

    Bằng nhau thì cảnh báo vô dụng: tới lúc in ra thì khoá đã bị đoạt rồi.
    """
    assert 0 < cy.GIU_LAU_S < cy.TUOI_TOI_DA_S


def test_giu_lau_thi_trang_thai_CANH_BAO():
    _ghi_khoa(os.getpid(), tuoi_s=cy.GIU_LAU_S + 60)
    bg = cy._doc()
    assert bg is not None
    assert cy._canh_bao_giu_lau(bg), "giu qua nguong ma khong canh bao gi"


def test_giu_NGAN_thi_KHONG_canh_bao():
    """🔑 Vế đối chứng. Thiếu nó thì một hàm luôn trả chuỗi khác rỗng cũng xanh,
    và mọi lượt đều bị gắn nhãn 'giữ lâu' — cảnh báo kêu suốt thì không ai đọc."""
    _ghi_khoa(os.getpid(), tuoi_s=5)
    bg = cy._doc()
    assert bg is not None
    assert cy._canh_bao_giu_lau(bg) == ""


def test_khoa_TAI_NGUYEN_DOC_QUYEN_co_nguong_RONG_HON():
    """Hai loại khoá trả lời hai câu khác nhau, nên không chung một ngưỡng.

    `cpu_nhieu` tuần tự hoá **sức tính**: giữ nó trong lúc chờ là phí máy.
    `postgres_test`/`may_tao_tieng` tuần tự hoá **tính đúng**: một phiên chen
    vào giữa làm HỎNG chính phép đo (số WER/LUFS mang tiếng của lượt khác, CSDL
    bị `drop_all` dưới chân). Với chúng, giữ suốt pha là ĐÚNG.

    🔴 Báo động giả là cách nhanh nhất giết một cảnh báo: kêu sai vài lần thì
       không ai đọc nữa, kể cả lúc nó kêu đúng.
    """
    assert 0 < cy.GIU_LAU_S < cy.GIU_LAU_DOC_QUYEN_S <= cy.TUOI_TOI_DA_S
    for tn in ("postgres_test", "may_tao_tieng"):
        assert tn in cy.TAI_NGUYEN_DOC_QUYEN, tn
    assert "cpu_nhieu" not in cy.TAI_NGUYEN_DOC_QUYEN


def test_khoa_doc_quyen_giu_40_phut_KHONG_bi_bao_dong_gia():
    _ghi_khoa(os.getpid(), tuoi_s=cy.GIU_LAU_S + 600)
    bg = cy._doc()
    assert bg is not None
    assert cy._canh_bao_giu_lau(bg, "postgres_test") == ""
    assert cy._canh_bao_giu_lau(bg, "cpu_nhieu"), "khoa CPU van phai canh bao"


def test_khoa_doc_quyen_giu_QUA_LAU_thi_van_canh_bao():
    """🔑 Vế đối chứng: nới ngưỡng ≠ bỏ canh. Một pha đo 3 giờ vẫn phải lộ ra."""
    _ghi_khoa(os.getpid(), tuoi_s=cy.GIU_LAU_DOC_QUYEN_S + 60)
    bg = cy._doc()
    assert bg is not None
    assert cy._canh_bao_giu_lau(bg, "postgres_test")


def test_hai_loai_khoa_noi_HAI_dieu_khac_nhau():
    """Thông điệp phải khác: một bên là 'bạn đang giữ thừa', bên kia là 'kiểm
    xem có bước CHỜ nào lọt vào khối không'. Cùng một câu cho cả hai là buộc
    tội oan đúng lúc người ta đang làm đúng."""
    _ghi_khoa(os.getpid(), tuoi_s=cy.GIU_LAU_DOC_QUYEN_S + 60)
    bg = cy._doc()
    assert cy._canh_bao_giu_lau(bg, "cpu_nhieu") !=         cy._canh_bao_giu_lau(bg, "postgres_test")


def test_thoat_khoi_with_thi_IN_RA_da_giu_bao_lau(capsys, monkeypatch):
    """Người GIỮ phải thấy con số của chính mình, không chỉ người chờ thấy."""
    monkeypatch.setattr(cy, "GIU_LAU_S", 0.01)
    with cy.CuaSoYen("toi", "lenh tinh", tai_nguyen=(cy.MAC_DINH,)):
        time.sleep(0.05)
    ra = capsys.readouterr().out
    assert "giu khoa" in ra.lower(), ra
    assert "cpu_nhieu" in ra, ra


def test_khong_giu_khoa_thi_KHONG_in_gi_ve_thoi_gian(capsys):
    """🔑 Vế đối chứng thứ hai: `bat=False` không chạm khoá nên không có gì để
    khai. In ra ở đây là in một con số không có thật."""
    with cy.CuaSoYen("toi", "lenh", bat=False):
        pass
    assert "giu khoa" not in capsys.readouterr().out.lower()


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


def test_cau_goi_y_khi_NHA_TRUOT_phai_NEU_TEN_tai_nguyen(capsys, monkeypatch):
    """Đường thứ TƯ chạm khoá thật, và nó không hiện ra ở phép quét mã.

    🔴 Ba đường kia (`nha(ep=True)`, `dang_giu()`, `_tep("<tên>")`) đọc được
       bằng AST. Đường này đi qua **một chuỗi gợi ý** mà con người gõ tay theo.

    Dòng ấy in ra **đúng lúc một phiên khác đang giữ khoá** — `that_bai` chính
    là những khoá ta vừa KHÔNG nhả được vì không phải của ta. Bản cũ gợi ý
    `nha --ep` trần, mà `--ep` không kèm `--tai-nguyen` thì gỡ **TẤT CẢ** khoá
    trên máy. Ai làm theo nguyên văn là gỡ cả khoá của một lượt gate đang sống,
    đúng ở chỗ người ta dễ tin nhất.

    ⚠️ Phép kiểm này chốt **hình dạng lời khuyên**, không chốt hành vi của `nha`
       — vì hành vi ấy đúng và có tài liệu; thứ sai là câu rủ người ta dùng nó
       ở dạng rộng nhất.
    """
    cy.thu_giu("phien-khac", "gate day du")
    ban_ghi = json.loads(cy.TEP_KHOA.read_text(encoding="utf-8"))
    ban_ghi["pid"] = os.getpid() + 1          # giả vờ của phiên khác, còn sống
    cy.TEP_KHOA.write_text(json.dumps(ban_ghi), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["cua_so_yen.py", "nha"])
    ma = cy.main()
    ra = capsys.readouterr().out

    assert ma == 1, "nha truot khoa cua phien khac phai tra ma khac 0"
    assert "--tai-nguyen" in ra, (
        "cau goi y khong neu ten tai nguyen — ai lam theo se go CA khoa cua "
        "mot luot gate dang chay")
    assert cy.TEP_KHOA.exists(), "khong duoc go khoa cua phien khac"


def test_moi_chuoi_IN_RA_deu_thuan_ASCII():
    """Console PowerShell 5.1 là CP1252.

    ⛔ Một emoji trong stdout của một công cụ đã từng làm cổng đỏ — ghi trong
       CLAUDE.md. Chú thích tiếng Việt thì thoải mái; thứ đi ra `stdout` thì không.

    🔴 LỖ ĐÃ VÁ 23/09: bản cũ chỉ quét chuỗi nằm TRỰC TIẾP trong `print(...)`.
       Một chuỗi được **trả về** rồi mới in ở chỗ khác (`_canh_bao_giu_lau`)
       lọt qua — và đã lọt thật: dấu `—` hiện ra console thành `?`. Cùng lớp
       lỗi với phạm vi quét hẹp của `test_967`: bánh cóc không phủ hết đường
       mà thứ nó canh đi qua.

    ⇒ Nay quét MỌI chuỗi chạy được của mô-đun (trừ docstring). Chú thích và
      docstring tiếng Việt vẫn thoải mái — chúng không ra `stdout`.
    """
    cay = ast.parse((GOC / "tools" / "cua_so_yen.py").read_text(encoding="utf-8"))
    docstring = set()
    for n in ast.walk(cay):
        than = getattr(n, "body", None)
        if isinstance(than, list) and than and isinstance(than[0], ast.Expr)                 and isinstance(than[0].value, ast.Constant)                 and isinstance(than[0].value.value, str):
            docstring.add(id(than[0].value))
    xau = [a.value for a in ast.walk(cay)
           if isinstance(a, ast.Constant) and isinstance(a.value, str)
           and id(a) not in docstring and not a.value.isascii()]
    assert not xau, f"chuoi CHAY DUOC khong thuan ASCII: {xau}"

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

def test_pytest_GO_TAY_luot_lon_thi_XIN_khoa(tmp_path, monkeypatch):
    """🔴 Lỗ CUỐI CÙNG của khoá, và nó là lệnh bốn phiên đều gõ.

    `gate.py` xin khoá; `tools/test_nhanh.py` xin khoá (từ 06/09). Nhưng
    `python -m pytest tests/ -n 6` gõ tay thì **không** — nên `cua_so_yen
    trang-thai` trả RẢNH trong khi máy đang chạy lệnh nặng nhất kho.

    ⛔ Xin ở `pytest_collection_modifyitems` chứ không ở `pytest_configure`:
       chỉ **sau khi thu thập** mới biết lượt này to hay nhỏ. Xin khoá cho một
       lượt 2 tệp là làm chậm mọi vòng lặp sửa-rồi-thử, và người ta sẽ học cách
       tắt nó — lúc đó ta mất cả phần bảo vệ.

    ⭐ Ba chiều, vì thiếu chiều nào cũng để lại một lỗ:
       lượt LỚN xin · lượt NHỎ không xin · `sessionfinish` **nhả**.
       Thiếu chiều ba thì mọi lượt `pytest` gõ tay để lại một khoá mồ côi, và
       phiên sau phải chờ hết `--cho` rồi CHÈN — tệ hơn trước bản vá.
    """
    import types                                 # noqa: PLC0415

    monkeypatch.setattr(cy, "_tep", lambda tn: tmp_path / f"khoa_{tn}.json")
    sys.path.insert(0, str(GOC / "tests"))
    import conftest as cf                        # noqa: PLC0415
    monkeypatch.setattr(cf, "_KHOA_PHIEN", None)

    # 🔴 Cửa ở `conftest.py:95-104` có BA điều kiện thoát sớm, và **cả ba** đều
    #    được môi trường mà phép kiểm này đang đứng tự thoả:
    #
    #      _KHOA_PHIEN is not None        phiên trước đã xin
    #      PYTEST_XDIST_WORKER            dưới gate, MỌI test ở trong một worker
    #      to_tien_da_giu_khoa()          dưới gate, tổ tiên CHÍNH LÀ `gate.py`
    #
    #    Không vô hiệu đủ cả ba thì thân hàm không bao giờ chạy tới, nên phép
    #    kiểm này **chưa từng xanh được trong gate** — nó chỉ xanh khi gõ tay.
    #
    # ⭐ Hình dạng đáng nhớ: phép kiểm canh một **cửa chặn**, mà điều kiện của
    #    cửa ấy lại chính là môi trường phép kiểm đang đứng. Nó không "khi xanh
    #    khi đỏ" — nó **luôn** đỏ ở đúng nơi duy nhất người ta đọc kết quả.
    #
    # ⛔ Và tôi đã sửa nó HAI LẦN mới đủ: lần đầu chỉ gỡ `PYTEST_XDIST_WORKER`,
    #    rồi `-n 6` cục bộ xanh 3/3 nên tôi tưởng xong — nhưng `-n 6` cục bộ
    #    **không có `gate.py` làm tổ tiên**. Một phép đo thiếu đúng cái điều
    #    kiện đang hỏi thì nó xác nhận, không kiểm chứng.
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    sys.path.insert(0, str(GOC / "tools"))
    import test_nhanh as tn                      # noqa: PLC0415
    monkeypatch.setattr(tn, "to_tien_da_giu_khoa", lambda *a, **k: False)

    lon = [types.SimpleNamespace(fspath=f"t{i}.py")
           for i in range(cf._NGUONG_TEP_NANG + 5)]
    nho = [types.SimpleNamespace(fspath=f"t{i}.py") for i in range(3)]
    cpu, pg = cy._tep("cpu_nhieu"), cy._tep("postgres_test")

    cf.pytest_collection_modifyitems(None, None, lon)
    assert cpu.exists(), "luot `pytest` go tay LON van vo hinh voi khoa"
    # 🔴 **`postgres_test` phai KHONG duoc giu — va do la mot khang dinh, ⛔ khong
    #    phai mot cho trong (25/09/2026).**
    #
    #    Bai nay tung doi `pg.exists()`. `conftest.py:143` **co y bo** khoa do tu
    #    24/09 (Task 0 / N-10): `pg_scratch.scratch_url` cap cho moi lan mot ten
    #    CSDL rieng, nen khong con mot cai ten dung chung nao de tranh. Cau `and
    #    pg.exists()` o lai lam bai nay **do tren `main`** — mot phep kiem doi
    #    bang chung cu sau khi duong da doi.
    #
    # ⭐ Viet thanh `not pg.exists()` chu ⛔ khong xoa ve: neu ai them lai khoa do
    #    ma khong noi ly do, bai nay do — va ho phai doc `conftest.py:143` truoc.
    assert not pg.exists(), (
        "`postgres_test` da bo tu 24/09 (schema rieng moi lan) — ai giu lai no "
        "phai giai trinh o `conftest.py:143`, ⛔ khong giu am tham")
    ban_ghi = json.loads(cpu.read_text(encoding="utf-8"))
    assert ban_ghi["lenh"] == "pytest go tay", (
        "phien khac phai DOC RA duoc day la mot luot go tay")

    cf.pytest_sessionfinish(None, 0)
    assert not cpu.exists() and not pg.exists(), (
        "khong nha khoa - moi luot go tay se de lai mot khoa mo coi")

    cf.pytest_collection_modifyitems(None, None, nho)
    assert not cpu.exists(), (
        "luot NHO ma van xin khoa - vong lap sua-roi-thu se bi cham va nguoi "
        "ta se tat co nay di")

    # ── Chiều thứ TƯ, và nó thiếu ở bản gốc ────────────────────────────────
    #
    # 🔴 Docstring trên kể ba chiều (lớn xin · nhỏ không xin · `sessionfinish`
    #    nhả) và nói *"thiếu chiều nào cũng để lại một lỗ"*. Có một chiều thứ tư
    #    mà nó không kể: **worker con KHÔNG được xin**. Đó là dòng ĐẦU của cửa
    #    (`conftest.py:96`), và cũng đúng là dòng đã làm phép kiểm này không bao
    #    giờ chạy tới thân hàm khi ở trong gate.
    #
    # ⭐ Nếu worker con cũng xin, thì một lượt `-n 6` sinh **sáu** người xin
    #    cùng một khoá `O_EXCL`: năm cái sau chờ hết `--cho` rồi CHÈN — tệ hơn
    #    hẳn trước bản vá, đúng câu hỏi 1 của AGENTS.md §4c.
    monkeypatch.setattr(cf, "_KHOA_PHIEN", None)
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw3")
    cf.pytest_collection_modifyitems(None, None, lon)
    assert not cpu.exists() and not pg.exists(), (
        "worker con cung xin khoa - mot luot `-n 6` se co SAU nguoi tranh mot "
        "khoa O_EXCL, va nam cai sau se CHEN sau khi het gio cho")

    # ── Chiều thứ NĂM: tổ tiên đã giữ khoá hộ thì KHÔNG xin nữa ────────────
    #
    # 🔴 Đây đúng là điều kiện đã làm phép kiểm này đỏ trong gate, và nó chưa
    #    từng được đo theo chiều của nó. `gate.py` và `test_nhanh.py` đã xin
    #    khoá trước khi gọi `pytest`; nếu `conftest` xin thêm một lần nữa thì
    #    khoá là tệp `O_EXCL` **không tái nhập** ⇒ tiến trình tự chờ chính mình
    #    tới hết `--cho` rồi CHÈN. Gate treo 15 phút ở bốn chỗ, đã xảy ra 06/09.
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    monkeypatch.setattr(cf, "_KHOA_PHIEN", None)
    monkeypatch.setattr(tn, "to_tien_da_giu_khoa", lambda *a, **k: True)
    cf.pytest_collection_modifyitems(None, None, lon)
    assert not cpu.exists() and not pg.exists(), (
        "to tien da giu khoa ho ma van xin them - khoa O_EXCL khong tai nhap, "
        "nen tien trinh se tu cho chinh minh toi het `--cho` roi CHEN")


def test_may_ban_KHONG_dem_chinh_no_va_chuoi_cha():
    """⛔ Điều kiện phải là thứ tiến trình đo **không thể tự thoả**.

    🔴 Phiên H44 đo được 06/09: một bộ lọc tiến trình khớp vào **chính công cụ
       đo**, vì vỏ `bash -c` mang cả mã nguồn được truyền cho nó. Họ dùng bộ
       lọc ấy để `kill`, và lệnh giết đi **ngược lên cây cha của chính nó** —
       script thoát mã 15 (SIGTERM).

    ⚠️ `cwd` bậc 3 **không** cứu được ca này: shell của người đang hỏi cũng có
       `cwd` đúng bằng cây ấy. Đó là lý do điều kiện phải loại `os.getpid()`
       **và toàn bộ `parents()`**, chứ không chỉ lọc theo cây.

    ⭐ `may_ban.py` chỉ ĐẾM nên hậu quả hiện tại chỉ là đếm thừa một. Nhưng một
       bộ đếm tự đếm mình là một bộ đếm **nói dối về chính câu hỏi nó trả lời**,
       và ngày nào có người thêm chế độ giết thì lỗ hổng đã nằm sẵn ở đó.
    """
    import os                                    # noqa: PLC0415
    import psutil                                # noqa: PLC0415

    sys.path.insert(0, str(GOC / "tools"))
    import may_ban                               # noqa: PLC0415

    me = psutil.Process()
    chuoi = {me.pid} | {t.pid for t in me.parents()}
    assert os.getpid() in chuoi

    # Tien trinh dang chay phep kiem nay CHINH la mot python.exe trong cay kho.
    trong_cay = bool(may_ban._ten_cay(os.getcwd()))
    if not trong_cay:
        import pytest as _pt                     # noqa: PLC0415
        _pt.skip("khong chay tu trong cay kho - phep do nay khong phan biet duoc")

    thay = []
    for p in psutil.process_iter(["pid", "name", "cwd"]):
        try:
            if p.info["pid"] in chuoi and (p.info["name"] or "").lower() == "python.exe":
                if may_ban._ten_cay(p.info["cwd"] or ""):
                    thay.append(p.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    assert thay, "phep kiem nay chi co nghia khi chinh no nam trong cay kho"

    # ⇒ Hoi HANH VI, dung grep ma nguon.
    #
    # ⛔ Ban dau cua phep kiem nay khang dinh `"parents()" in ma and "bo_qua" in ma`
    #    — tuc lai la mot banh coc HINH DANG. Tiem "bo dong loai tru" thi no VAN
    #    XANH, vi hai chu ay con nguyen trong tep. Do dung lop loi ma ca tep nay
    #    ton tai de chan.
    ten = may_ban._ten_cay(os.getcwd())
    tho = 0
    for p in psutil.process_iter(["pid", "name", "cwd"]):
        try:
            if (p.info["name"] or "").lower() != "python.exe":
                continue
            if may_ban._ten_cay(p.info["cwd"] or "") == ten:
                tho += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    tinh = may_ban.quet().get(ten, {"so": 0})["so"]
    assert tinh < tho, (
        f"quet() dem {tinh} tren tong {tho} python.exe cua cay `{ten}` - "
        "no dang dem ca chinh tien trinh dang hoi")

def test_may_ban_do_DELTA_chu_khong_do_CPU_tich_luy(tmp_path, monkeypatch):
    """🔴 Đo 06/09: công cụ báo hai cây **ĐANG LÀM** trong khi CPU toàn máy 4,6 %.

    Ngưỡng ban đầu đặt trên **CPU tích luỹ**, nên một tiến trình sống lâu tích đủ
    5 giây CPU **một lần** rồi nằm không sẽ **mãi mãi** trông như đang làm.

    ⛔ Hai cách đo đều sai, mỗi cách một chiều:
         `cpu_percent()` một nhát  -> mẫu TỨC THỜI; không phân biệt "đã chết"
                                      với "đang chờ I/O" (đo 05/09: 0,0 %)
         CPU TÍCH LUỸ              -> không phân biệt "đang làm" với "đã làm
                                      xong từ lâu"

    ⚠️ Hậu quả nếu sai: công cụ báo bận vĩnh viễn ⇒ không ai chạy gate được ⇒
       người ta thôi đọc nó. **Một cảnh báo luôn bật là một cảnh báo đã tắt.**

    ## Vì sao phép kiểm này phải TỰ DỰNG tập tiến trình của nó

    🔴 Hai bản trước đều chốt một **sự thật môi trường** và đỏ dưới gate:

         `assert cpu < NGUONG`      -> dưới gate cây chính chạy 6 worker,
                                       delta là hàng trăm phần trăm
         `assert cpu < tich_luy`    -> `cpu` là **phần trăm**, `tich_luy` là
                                       **giây**; phép so chỉ đúng nhờ tình cờ
                                       khi máy rảnh, và đỏ ngay khi có tải

    ⭐ Nên phép kiểm **thay `_ten_cay`** để chỉ đúng tiến trình con của nó rơi
       vào bảng. Khi ấy khẳng định không còn phụ thuộc vào máy đang bận hay rảnh
       — đó là khác biệt giữa *chốt một tính chất của mã* và *chốt một sự thật
       môi trường*.
    """
    import subprocess                            # noqa: PLC0415
    import time as _t                            # noqa: PLC0415

    sys.path.insert(0, str(GOC / "tools"))
    import may_ban                               # noqa: PLC0415

    thu_muc = tmp_path / "cay_gia"
    thu_muc.mkdir()
    ma = ("import time" + chr(10) +
          "t=time.time()" + chr(10) +
          "while time.time()-t < 6.0: pass" + chr(10) +
          "time.sleep(30)")
    con = subprocess.Popen([sys.executable, "-c", ma], cwd=str(thu_muc),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # CHI tien trinh con nay roi vao bang. Moi thu khac -> "" -> bi bo qua.
        goc_gia = str(thu_muc).lower()
        monkeypatch.setattr(
            may_ban, "_ten_cay",
            lambda cwd: "CAY THU" if (cwd or "").lower().startswith(goc_gia) else "")

        _t.sleep(7.0)                            # de no dot xong roi ngu
        bang = may_ban.quet()
        muc = bang.get("CAY THU")
        assert muc is not None and muc["so"] == 1, (
            f"phai thay DUNG mot tien trinh con, thay: {bang}")
        # 🔴 Phai dot LAU HON nguong o duoi, neu khong phep kiem khong phan
        #    biet duoc: ban dau dot 1,2 giay thi ca hai cach do deu < 5 va phep
        #    tiem VAN XANH. Mot phep kiem khong phan biet duoc thi khong do gi.
        assert muc["tich_luy"] >= 5.5, (
            f"tien trinh con moi tich {muc['tich_luy']:.1f}s CPU - phai VUOT "
            "nguong o duoi thi phep kiem moi phan biet duoc hai cach do")

        # ⭐ Ve DUY NHAT phan biet duoc, va no dung o MOI muc tai cua may:
        #      delta    -> ~0 %  cho mot tien trinh DANG NGU
        #      tich luy -> >= 1,2 (giay da dot truoc do)
        assert muc["cpu"] < 5.0, (
            f"delta {muc['cpu']:.1f}% cho mot tien trinh DANG NGU - bo do dang "
            f"doc CPU tich luy ({muc['tich_luy']:.1f}s) chu khong doc delta")
    finally:
        con.terminate()
        con.wait(timeout=10)


def test_may_ban_BAO_ca_KHOA_chu_khong_chi_bao_CPU(tmp_path, monkeypatch):
    """🔴 Hai phep do tra loi HAI cau khac nhau, va chung KHONG trung nhau.

       Do 06/09/2026: `may_ban` bao ca hai cay `dang cho` (3,1% va 2,1% CPU)
       trong khi mot `pytest go tay` da giu `cpu_nhieu` + `postgres_test` duoc
       3,6 phut. Toi thay `cua_so_yen trang-thai` bang `may_ban` vi tuong the
       la du, roi phong gate — no xep hang **9,5 phut**
       (`cho_khoa_giay = 555,4` trong ban ghi cua luot ay).

       Mot luot pytest o pha I/O doc ra y het mot may ranh. Nen ma thoat cua
       `may_ban` phai tinh CA HAI ve, khong chi ve CPU.

    ⭐ Phep kiem nay KHONG do CPU — no chot dung mot menh de: **co khoa thi
       phai bao**, ke ca khi khong cay nao ban. Dat CPU ra ngoai bang cach
       ep `cay_khac_dang_ban` tra ve rong.
    """
    sys.path.insert(0, str(GOC / "tools"))
    import cua_so_yen
    import may_ban

    # Khoa di noi khac: mot phep kiem KHONG duoc cham khoa that cua may.
    # Xem `AGENTS.md` — "chot khong duoc ghi vao cay".
    monkeypatch.setattr(cua_so_yen, "TEP_KHOA", tmp_path / "ltt_khoa_cpu_nhieu.json")
    monkeypatch.setattr(cua_so_yen.tempfile, "gettempdir", lambda: str(tmp_path))

    # Khong cay nao ban -> ve CPU im hoan toan.
    monkeypatch.setattr(may_ban, "cay_khac_dang_ban", lambda bang=None: [])

    assert may_ban.khoa_dang_giu() == [], "chua ai giu ma da bao co khoa"

    with cua_so_yen.CuaSoYen("PHEP-KIEM", "giu de thu", tai_nguyen=("cpu_nhieu",)):
        dong = may_ban.khoa_dang_giu()
        assert dong, (
            "CO khoa dang bi giu ma `may_ban` im — day dung la lo da lam gate "
            "xep hang 9,5 phut ma toi khong biet vi sao")
        assert "cpu_nhieu" in dong[0]
        assert "  [khoa]" in may_ban.dong_canh_bao(), (
            "`dong_canh_bao` (thu gate/test_nhanh in ra) khong nhac gi den khoa")

    assert may_ban.khoa_dang_giu() == [], "nha roi ma van bao con khoa"

# ── "Khong do duoc" phai khac "khong ai ban" (07/09/2026) ──────────────────

def test_may_ban_PHAN_BIET_khong_do_duoc_voi_khong_ai_ban(monkeypatch):
    """🔴 Do 07/09: `may_ban` bao "KHONG BIET - thieu psutil" trong khi
       `psutil 7.2.2` cai san va import duoc tu dung trinh thong dich ay.

    Nguyen nhan: `quet()` tra `{}` cho CA HAI trang thai, va `main` doc bang
    rong thanh "thieu psutil". Nen mot may THAT SU RANH bi bao la khong do
    duoc — tuc mot canh bao khi khong co gi.

    ⭐ Sai ve phia an toan VAN LA SAI. Mot thong diep bao dong khi khong co gi
       la thu day nguoi ta bo qua chinh thong diep ay — va `may_ban` la cong cu
       gac quy tac "kiem CPU truoc lenh nang", nen no bi bo qua la quy tac bi
       bo qua.

    `AGENTS.md` §4c cau 2 doi hoi dung dieu nay: **co y** phai phan biet duoc
    voi **tai nan**.
    """
    import sys as _s

    sys.path.insert(0, str(GOC / "tools"))
    import may_ban                               # noqa: PLC0415

    # 1. Do duoc, nhung khong cay nao ban -> `{}`, KHONG phai None.
    monkeypatch.setattr(may_ban, "_quet_thuc", lambda: {})
    assert may_ban._quet_thuc() == {}, "do duoc ma khong ai ban phai la {}"

    # 2. Vang psutil -> None. Ep bang cach chan chinh lan import.
    that = builtins.__import__

    def _chan(ten, *a, **k):
        if ten == "psutil":
            raise ImportError("gia lap vang psutil")
        return that(ten, *a, **k)

    monkeypatch.undo()
    monkeypatch.setattr(builtins, "__import__", _chan)
    _s.modules.pop("psutil", None)
    assert may_ban._quet_thuc() is None, (
        "vang psutil phai tra None — tra {} la gop no voi 'khong ai ban', "
        "dung cai loi ngay 07/09")

    # 3. ⛔ Va hop dong CU phai giu nguyen: `quet()` van luon tra `dict`.
    #    `test_khoa_hien_ra_o_may_ban` va cac cho khac goi `.get(...)` tren no;
    #    doi kieu tra ve o day bien mot ban sua NGHIA thanh mot ban pha hop
    #    dong o cho khong lien quan.
    assert may_ban.quet() == {}, "`quet()` phai luon tra dict, ke ca khi vang"


# ── INDEX cua cay chinh la mot khoa TAI NGUYEN DOC QUYEN (ca that 25/09/2026) ──
#
# Mot phien `git add` roi de day khoa duong `git merge` cua MOI phien khac, va
# `cua_so_yen trang-thai` truoc day bao "RANH" ngay trong luc do. Bon bai duoi
# chot ca cau tra loi (co ai giu khong) VA cai gia phai tra de hoi (khong duoc tu
# giu khoa index khi di hoi).


def _kho_git(goc: Path) -> Path:
    """Mot kho git that, roi rac, de khong phai stage vao cay `main` dung chung."""
    goc.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "."], cwd=goc, check=True,
                   capture_output=True)
    return goc


def test_index_BAN_thi_khai_ra_dung_nhung_tep_dang_giu(tmp_path, monkeypatch):
    kho = _kho_git(tmp_path)
    (kho / "a.txt").write_text("x", encoding="utf-8")
    (kho / "b.txt").write_text("y", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt", "b.txt"], cwd=kho, check=True,
                   capture_output=True)
    monkeypatch.chdir(kho)

    ix = cy.index_dung_chung()

    assert ix is not None, "index co tep staged ma ham bao khong ai giu"
    assert sorted(ix["tep"]) == ["a.txt", "b.txt"]
    assert Path(ix["cay"]).resolve() == kho.resolve()


def test_index_SACH_thi_tra_None(tmp_path, monkeypatch):
    """Doi chung. ⛔ Thieu bai nay thi mot ham LUON tra dict cung xanh o bai tren."""
    monkeypatch.chdir(_kho_git(tmp_path))
    assert cy.index_dung_chung() is None


def test_doc_tu_WORKTREE_van_lan_ra_cay_CHINH(tmp_path, monkeypatch):
    """Ca that: phien lam viec o worktree rieng, ma index bi giu o cay `main`.

    ⚠️ Neu `_cay_main()` tra ve cay DANG DUNG thi ham se bao "khong ai giu" dung
       luc duong gop bi chan — tuc im lang o dung ca no sinh ra de bat.
    """
    chinh = _kho_git(tmp_path / "chinh")
    (chinh / "a.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=chinh, check=True,
                   capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "nen"], cwd=chinh, check=True,
                   capture_output=True)
    wt = tmp_path / "wt"
    subprocess.run(["git", "worktree", "add", "-q", str(wt), "-b", "nhanh"],
                   cwd=chinh, check=True, capture_output=True)
    monkeypatch.chdir(wt)

    assert Path(cy._cay_main()).resolve() == chinh.resolve()


def test_di_HOI_ai_giu_index_thi_KHONG_duoc_tu_giu_khoa_index(tmp_path,
                                                             monkeypatch):
    """🔴 `--no-optional-locks` la BAT BUOC, ⛔ khong phai mot toi uu.

    `git diff` binh thuong duoc phep ghi lai index (stat cache) ⇒ chinh cong cu
    di hoi *"ai dang giu khoa index"* lai giu khoa index. Bo co nay la **tu tao ra
    dung cai benh minh di do**.

    ⭐ Bai nay doc ARGV THUC SU truyen cho git, ⛔ khong grep ma nguon — doi cach
       go (them khoang trang, doi thu tu co) ⛔ khong duoc lam no do oan.
    """
    kho = _kho_git(tmp_path)
    monkeypatch.chdir(kho)
    da_goi: list[list[str]] = []
    that = subprocess.run

    def ghi_lai(cmd, *a, **kw):
        if isinstance(cmd, list):
            da_goi.append(list(cmd))
        return that(cmd, *a, **kw)

    monkeypatch.setattr(cy.subprocess, "run", ghi_lai)
    cy.index_dung_chung()

    doc_index = [c for c in da_goi if "diff" in c and "--cached" in c]
    assert doc_index, "khong thay loi goi nao doc index"
    for c in doc_index:
        assert "--no-optional-locks" in c, (
            f"loi goi doc index thieu --no-optional-locks: {c}")
