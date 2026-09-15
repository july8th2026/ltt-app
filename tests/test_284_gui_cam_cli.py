"""GUI của `cam_cli` — vỏ phải **mỏng**, và bản sao CSS phải **không trôi**.

Hai thứ được chốt ở đây, và cả hai đều hỏng **lặng lẽ** nếu không chốt.

🔴 ① MẶT TIẾP XÚC CỦA CẦU NỐI.

   pywebview đưa **mọi phương thức công khai** của đối tượng `js_api` ra cho
   JavaScript gọi. Không có khai báo nào, không có allowlist — cứ là phương thức
   không bắt đầu bằng `_` thì `window.pywebview.api.<tên>()` gọi được.

   Nên một hàm tiện tay thêm vào `Cau` (`doc_tep`, `chay_lenh`, `mo_thu_muc`…)
   **là một hàm mã trong cửa sổ gọi được**, ngay lập tức, mà không ai phải sửa
   thêm dòng nào. Và cửa sổ đó render HTML — hôm nay là HTML của ta, nhưng
   "hôm nay" không phải một bảo đảm.

   ⇒ Danh sách `HAM_CHO_PHEP` là **hợp đồng**, và test này là thứ bắt nó phải đúng.

🔴 ② BẢN SAO `ltt.css`.

   GUI không phục vụ từ `server/static/` — khi đã đóng gói thành installer thì
   không có máy chủ nào cả. Nên phải có một bản sao nằm cạnh GUI.

   Và một bản sao **không có gì nhắc nó cập nhật thì nó sẽ không cập nhật**. Lần
   đầu ai đó đổi màu thương hiệu, GUI vẫn dùng bản cũ — không ai báo lỗi, công cụ
   chỉ trông **gần giống** nền tảng, kiểu sai khó chịu nhất.

   Cùng lớp với bài học cache-bust ở quy tắc 6 của `CLAUDE.md`.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(
        f"{ten}_test", GOC / "tools" / f"{ten}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── ① Cầu nối: đúng bốn hàm ────────────────────────────────────────────────

def test_cau_noi_lo_ra_DUNG_bon_ham():
    gui = _nap("cam_cli_gui")
    that = {t for t in dir(gui.Cau) if not t.startswith("_")}
    assert that == set(gui.HAM_CHO_PHEP), (
        f"Cau lo ra {sorted(that)} nhung HAM_CHO_PHEP khai {sorted(gui.HAM_CHO_PHEP)}. "
        f"pywebview dua MOI phuong thuc cong khai ra cho JavaScript goi - mot ham "
        f"them vao day la mot ham ma trong cua so goi duoc ngay, khong ai phai sua "
        f"them dong nao.")


def test_bon_ham_do_dung_la_bon_ham_da_thiet_ke():
    gui = _nap("cam_cli_gui")
    assert set(gui.HAM_CHO_PHEP) == {"xem", "cam", "go", "kiem"}


def test_cau_noi_KHONG_lo_ham_chay_lenh_hay_doc_tep():
    """Chốt riêng cho ba cái tên nguy hiểm nhất, gọi thẳng tên ra.

    `test_cau_noi_lo_ra_DUNG_bon_ham` đã phủ, nhưng test này **đọc được** khi ai
    đó đang cân nhắc thêm đúng những hàm này — nó nói *không* bằng tên cụ thể.
    """
    gui = _nap("cam_cli_gui")
    cam = {"doc_tep", "ghi_tep", "chay_lenh", "mo_thu_muc", "eval",
           "exec", "he_thong", "shell"}
    assert not (cam & set(dir(gui.Cau)))


def test_ngoai_le_trong_loi_KHONG_lam_trang_cua_so():
    """Một ngoại lệ chưa nghĩ tới phải thành **một dòng đọc được**, không phải
    một cửa sổ trắng."""
    gui = _nap("cam_cli_gui")

    class LoiGia:
        GOC_MAC_DINH = "https://vi-du"

        @staticmethod
        def lenh_xem(a):
            raise RuntimeError("hong mot cach bat ngo")

    kq = gui.Cau(LoiGia()).xem()
    assert kq["ma"] == 1
    assert any("hong mot cach bat ngo" in d for d in kq["dong"]), (
        "khach phai thay CHUYEN GI da xay ra, ke ca khi do la loi ta chua nghi toi")


# ── ② Bản sao ltt.css không được trôi ──────────────────────────────────────

def test_ltt_css_ban_sao_khop_ban_goc():
    nguon = GOC / "server" / "static" / "ltt.css"
    ban_sao = GOC / "tools" / "gui" / "ltt.css"
    assert ban_sao.exists(), "chua chay: python tools\\dong_goi_gui.py"
    assert ban_sao.read_bytes() == nguon.read_bytes(), (
        "tools/gui/ltt.css da TROI khoi server/static/ltt.css. "
        "Chay: python tools\\dong_goi_gui.py")


def test_kiem_bat_duoc_khi_ban_sao_troi(tmp_path, monkeypatch):
    """Chứng minh chốt **thật sự đỏ** khi bản sao lệch, không xanh vì lý do sai."""
    dg = _nap("dong_goi_gui")
    goc_gia = tmp_path
    (goc_gia / "server" / "static").mkdir(parents=True)
    (goc_gia / "tools" / "gui").mkdir(parents=True)
    (goc_gia / "server" / "static" / "ltt.css").write_text("a{color:red}", encoding="utf-8")
    (goc_gia / "tools" / "gui" / "ltt.css").write_text("a{color:blue}", encoding="utf-8")
    monkeypatch.setattr(dg, "GOC", goc_gia)

    assert dg.dong_bo(kiem_thoi=True) == 1, "ban sao lech ma chot van xanh"
    assert dg.dong_bo(kiem_thoi=False) == 0
    assert dg.dong_bo(kiem_thoi=True) == 0, "dong bo xong roi ma van bao lech"


# ── Giao diện: không màu nào viết cứng ─────────────────────────────────────

def test_index_html_khong_viet_cung_ma_mau():
    """Mọi màu phải lấy từ token của `ltt.css`.

    Viết cứng một mã màu ở đây là tạo một chỗ mà lần đổi thương hiệu sau sẽ **bỏ
    sót** — và bỏ sót đúng cái cửa sổ khách nhìn thấy đầu tiên.
    """
    html = (GOC / "tools" / "gui" / "index.html").read_text(encoding="utf-8")
    khoi_style = "\n".join(re.findall(r"<style>(.*?)</style>", html, re.S))
    mau = [m for m in re.findall(r"#[0-9a-fA-F]{3,8}\b", khoi_style)
           if m.lower() != "#fff"]          # #fff tren nen thuong hieu: chap nhan
    assert not mau, (
        f"ma mau viet cung trong <style>: {mau}. Dung bien token cua ltt.css "
        f"(vd var(--brand-primary)) de doi thuong hieu la doi mot cho.")


def test_index_html_co_canh_bao_toan_cuc():
    """Ô "áp cho mọi phiên" **phải** có cảnh báo ngay cạnh nó.

    `ANTHROPIC_BASE_URL` trong `settings.json` chuyen huong ca goi Anthropic that
    cua khach. Mot o tich lang le o do la mot cai bay.
    """
    html = (GOC / "tools" / "gui" / "index.html").read_text(encoding="utf-8")
    assert 'id="toancuc"' in html
    assert "Anthropic" in html and "⚠" in html


def test_index_html_lien_ket_toi_ltt_css_ban_sao():
    html = (GOC / "tools" / "gui" / "index.html").read_text(encoding="utf-8")
    assert 'href="ltt.css"' in html, (
        "phai tro toi ban sao canh no, khong phai mot duong dan may chu - khi da "
        "dong goi thanh installer thi khong co may chu nao ca")


@pytest.mark.parametrize("ten", ["cam_cli.py", "cam_cli_gui.py", "dong_goi_gui.py"])
def test_tep_python_khong_co_BOM(ten):
    b = (GOC / "tools" / ten).read_bytes()
    assert b[:3] != b"\xef\xbb\xbf"


def test_bat_thuan_ascii_khong_BOM():
    """`.bat` đọc theo bảng mã ANSI; một dấu tiếng Việt làm hỏng cả câu lệnh."""
    b = (GOC / "tools" / "cam_cli.bat").read_bytes()
    assert b[:3] != b"\xef\xbb\xbf"
    xau = [(i, hex(c)) for i, c in enumerate(b) if c > 127]
    assert not xau, f"ky tu ngoai ASCII trong .bat: {xau[:3]}"


def test_launcher_ps1_thuan_ascii_khong_BOM_va_khong_lo_khoa():
    p = GOC / "tools" / "cam_cli_launcher.ps1"
    b = p.read_bytes()
    assert b[:3] != b"\xef\xbb\xbf"
    assert not [c for c in b if c > 127]
    van = b.decode("ascii")
    assert "Read-Host 'Paste API key (input is hidden)' -AsSecureString" in van
    assert "LTT_API_KEY" in van
    assert "LTT_CAM_CLI_OUTPUT" in van
    assert "Start-Process" in van and "-Wait" in van


@pytest.mark.parametrize("ten", ["cam_cli_admin.bat", "cam_cli_admin.ps1"])
def test_goi_bat_admin_thuan_ascii_khong_BOM(ten):
    b = (GOC / "tools" / ten).read_bytes()
    assert b[:3] != b"\xef\xbb\xbf"
    assert not [c for c in b if c > 127]


def test_goi_zip_thuc_su_yeu_cau_administrator():
    ps = (GOC / "tools" / "cam_cli_admin.ps1").read_text(encoding="ascii")
    bat = (GOC / "tools" / "cam_cli_admin.bat").read_text(encoding="ascii")
    assert "WindowsBuiltInRole]::Administrator" in ps
    assert "-Verb RunAs" in ps
    assert "LTTStudios-CamCLI-Console.exe" in bat


def test_dong_goi_co_the_dat_output_tren_o_con_trong(monkeypatch, tmp_path):
    output = tmp_path / "cam-cli-release"
    monkeypatch.setenv("LTT_CAM_CLI_BUILD_DIR", str(output))
    dong_goi = _nap("dong_goi_exe")
    assert dong_goi.RA == output.resolve()


def test_gui_cho_chon_tung_be_mat_va_hien_loi_bridge():
    html = (GOC / "tools" / "gui" / "index.html").read_text(encoding="utf-8")
    for ten in ("codex", "claude_cli", "claude_vscode", "claude_desktop"):
        assert ten in html
    # Nút "Cắm" đi QUA cầu-nối-guard `coCau()` rồi mới gọi `.cam(k, luaChon)`:
    # nếu window.pywebview.api trống (bản 1.1.0 thiếu webview/js) thì báo lỗi rõ
    # thay vì "Cannot read properties of null".
    assert "coCau()" in html
    assert "a.cam(k, luaChon)" in html
    assert "catch (e)" in html
    assert "Hoàn tất sau" in html


def test_cau_cam_chuyen_lua_chon_thanh_dung_hang_muc(monkeypatch):
    gui = _nap("cam_cli_gui")

    class LoiGia:
        GOC_MAC_DINH = "https://x"
        MUC_CODEX_CLI = "codex-cli"
        MUC_CODEX_VSCODE = "codex-vscode"
        MUC_CLAUDE_CLI = "claude-cli"
        MUC_CLAUDE_VSCODE = "claude-vscode"
        MUC_CLAUDE_DESKTOP = "claude-desktop"

        @staticmethod
        def lenh_cam(a):
            assert a.muc == ["codex-vscode", "claude-vscode"]
            return 0

    kq = gui.Cau(LoiGia()).cam("ltt_sk_x", {
        "codex": "vscode", "claude_cli": False,
        "claude_vscode": True, "claude_desktop": False,
    })
    assert kq["ma"] == 0
