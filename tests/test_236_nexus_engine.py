"""Nexus N3.2 — module lái engine RustDesk nguyên bản, kiểm bằng hàm thuần.

Không cần RustDesk cài: mọi thứ dựng lệnh/nội dung là hàm thuần, và phần chạy
nhận `runner` tiêm vào (cùng khuôn với `service.py`). Cái được chốt kỹ nhất là
những tính chất mà một phép đo trên máy thật đã dạy — idempotent config, mật
khẩu là argv chứ không phải chuỗi shell, và lỗi quyền admin nổi lên thành thông
điệp đọc được chứ không thành 'im lặng không đặt được'.
"""
from __future__ import annotations

import pytest

from nexus_agent import engine


def _runner(ma=0, ra=""):
    goi = []

    def chay(argv):
        goi.append(argv)
        return ma, ra

    chay.goi = goi
    return chay


# ── noi_dung_config: idempotent, đặt đúng chỗ ────────────────────────────────

def test_config_them_ba_khoa_duoi_options():
    out = engine.noi_dung_config(["[options]"], "45.76.185.75", "KEY123=")
    assert "custom-rendezvous-server = '45.76.185.75'" in out
    assert "relay-server = '45.76.185.75'" in out
    assert "key = 'KEY123='" in out


def test_config_idempotent_khong_nhan_dong():
    """Agent chạy mỗi lần khởi động; nhân dòng mỗi lần là lỗi âm thầm."""
    b1 = engine.noi_dung_config(["[options]"], "1.2.3.4", "K=")
    b2 = engine.noi_dung_config(b1.splitlines(), "1.2.3.4", "K=")
    assert b1 == b2
    assert b2.count("custom-rendezvous-server") == 1
    assert b2.count("relay-server") == 1


def test_config_giu_lai_option_khac():
    goc = ["rendezvous_server = 'rs-ny.rustdesk.com:21116'",
           "[options]", "av1-test = 'N'", "local-ip-addr = '10.0.0.5'"]
    out = engine.noi_dung_config(goc, "9.9.9.9", "K=")
    assert "av1-test = 'N'" in out
    assert "local-ip-addr = '10.0.0.5'" in out
    # doi server cu bang server moi
    assert "9.9.9.9" in out


def test_config_tao_options_neu_chua_co():
    out = engine.noi_dung_config(["some_toplevel = 1"], "1.1.1.1", "K=")
    assert "[options]" in out
    # ba khoa phai nam SAU [options]
    i_opt = out.index("[options]")
    assert out.index("custom-rendezvous-server", i_opt) > i_opt


def test_config_ba_khoa_ngay_sau_options_khong_roi_section_khac():
    goc = ["[options]", "x = '1'", "[ui_flutter]", "peer-sorting = 'Remote ID'"]
    out = engine.noi_dung_config(goc, "5.5.5.5", "K=")
    lines = out.splitlines()
    i_opt = lines.index("[options]")
    i_ui = lines.index("[ui_flutter]")
    i_key = next(i for i, l in enumerate(lines) if l.startswith("key ="))
    # key phai o GIUA [options] va [ui_flutter], khong roi vao section ui
    assert i_opt < i_key < i_ui


def test_config_thieu_server_hoac_key_thi_nem():
    with pytest.raises(engine.EngineError):
        engine.noi_dung_config(["[options]"], "", "K=")
    with pytest.raises(engine.EngineError):
        engine.noi_dung_config(["[options]"], "1.2.3.4", "")


# ── Mật khẩu: CSPRNG, đủ mạnh, argv-safe ─────────────────────────────────────

def test_mat_khau_du_dai_va_khac_nhau():
    a = engine.sinh_mat_khau_phien()
    b = engine.sinh_mat_khau_phien()
    assert len(a) == 20 and len(b) == 20
    assert a != b                       # xac suat trung ~ 0


def test_mat_khau_bo_ky_tu_de_nham():
    for _ in range(50):
        mk = engine.sinh_mat_khau_phien()
        assert not (set(mk) & set("0O1lI"))


def test_mat_khau_qua_ngan_bi_tu_choi():
    with pytest.raises(engine.EngineError):
        engine.sinh_mat_khau_phien(8)


def test_lenh_password_la_LIST_khong_phai_chuoi():
    """List → subprocess không qua shell → mật khẩu chứa `&`/`^` không tiêm được."""
    lenh = engine.lenh_password("rustdesk.exe", "a&b^c'd")
    assert isinstance(lenh, list)
    assert lenh[-1] == "a&b^c'd"        # nguyen ven, mot phan tu


# ── lay_id: chạy được user thường, lọc token số ──────────────────────────────

def test_lay_id_loc_token_so_giua_log():
    # V4 cho thay stdout co the co dong log truoc ID
    r = _runner(0, "set plugin flutter unusable\n288780716\n")
    assert engine.lay_id("x", runner=r) == "288780716"


def test_lay_id_khong_co_so_thi_nem():
    with pytest.raises(engine.EngineError):
        engine.lay_id("x", runner=_runner(0, "loi gi do"))


# ── dat_mat_khau: lỗi quyền admin nổi lên, không bị nuốt ──────────────────────

def test_dat_mat_khau_thanh_cong_khi_Done():
    engine.dat_mat_khau("x", "MatKhauDai123", runner=_runner(0, "Done!"))


def test_dat_mat_khau_thieu_quyen_admin_nem_ro_rang():
    """Đây là ranh giới V8: dưới user thường RustDesk trả 'privileges required'.
    Lỗi đó phải thành thông điệp đọc được, không thành 'đặt xong mà không đặt'."""
    r = _runner(0, "Installation and administrative privileges required!")
    with pytest.raises(engine.EngineError) as ei:
        engine.dat_mat_khau("x", "MatKhauDai123", runner=r)
    assert "admin" in str(ei.value).lower()


def test_xoay_mat_khau_tra_ve_mat_khau_da_dat():
    r = _runner(0, "Done!")
    mk = engine.xoay_mat_khau("x", runner=r)
    assert len(mk) == 20
    # runner nhan dung mat khau do o vi tri cuoi argv
    assert r.goi[-1][-1] == mk


def test_xoay_mat_khau_khong_ghi_mat_khau_ra_ngoai():
    """xoay_mat_khau trả mật khẩu để tầng gọi chuyển qua đường vé; module KHÔNG
    được tự log/ghi đĩa. Chốt bằng cấu trúc: không import logging/open trong body."""
    import ast
    import inspect
    # Chi soi PHAN CODE, bo docstring (docstring co the nhac chu "log" khi giai
    # thich chinh dieu cam).
    fn = ast.parse(inspect.getsource(engine.xoay_mat_khau)).body[0]
    if (fn.body and isinstance(fn.body[0], ast.Expr)
            and isinstance(fn.body[0].value, ast.Constant)):
        fn.body = fn.body[1:]          # bo docstring
    code = ast.unparse(ast.Module(body=fn.body, type_ignores=[]))
    assert "log" not in code and "open(" not in code and "print(" not in code


# ── engine_runner: nối engine.py với RustDesk thật (W4) ──────────────────────

def test_runner_chuan_bi_phien_tra_id_va_secret(monkeypatch):
    """RustDeskEngine gọi --get-id rồi --password, trả (id, secret)."""
    from nexus_agent import engine_runner

    goi = []
    def gia(argv):
        goi.append(argv)
        if "--get-id" in argv:
            return 0, "288780716\n"
        if "--password" in argv:
            return 0, "Done!"
        return 1, "?"
    monkeypatch.setattr(engine_runner, "_runner", gia)

    eng = engine_runner.RustDeskEngine(exe="rustdesk.exe")
    engine_id, secret = eng.chuan_bi_phien()
    assert engine_id == "288780716"
    assert len(secret) == 20                    # mat khau moi, do dai chuan
    # phai da goi ca get-id lan password
    assert any("--get-id" in a for a in goi)
    assert any("--password" in a for a in goi)


def test_runner_duong_exe_doi_bang_env(monkeypatch):
    from nexus_agent import engine_runner
    monkeypatch.setenv("LTT_NEXUS_RUSTDESK_EXE", r"C:\Fork\ltt-nexus.exe")
    assert engine_runner.duong_exe() == r"C:\Fork\ltt-nexus.exe"
