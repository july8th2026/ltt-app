"""test_534 — bộ tài khoản thử dùng chung (`tools/tai_khoan_thu.py`, 16/09/2026).

Ghim ba điều mà mọi phiên khác sẽ dựa vào:
  1. mật khẩu chỉ nằm trong kho `secrets\\tai_khoan_thu.json` — không in ra stdout;
  2. kho ghi UTF-8 KHÔNG BOM (luật cấu hình của dự án);
  3. không thao tác ghi nào chạm email không phải `.local`.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


def _nap():
    spec = importlib.util.spec_from_file_location("tai_khoan_thu", GOC / "tools" / "tai_khoan_thu.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_bo_chung_la_ba_email_thu_khong_trung():
    m = _nap()
    emails = [e for e, _ in m.BO_CHUNG]
    assert len(emails) == 3 and len(set(emails)) == 3
    assert all(m.la_email_thu(e) for e in emails)
    assert not m.la_email_thu("khach.that@gmail.com")


def test_kho_ghi_khong_BOM_va_doc_lai_duoc(tmp_path):
    m = _nap()
    duong = str(tmp_path / "secrets" / "tai_khoan_thu.json")
    kho = {}
    m._luu(kho, "khach1.thu@lttstudios.local", "MatKhauThu123", "Khach thu 1")
    m.ghi_kho(duong, kho)
    b = pathlib.Path(duong).read_bytes()
    assert not b.startswith(b"\xef\xbb\xbf")
    assert m.doc_kho(duong)["khach1.thu@lttstudios.local"]["mat_khau"] == "MatKhauThu123"
    assert m.doc_kho(str(tmp_path / "khong_co.json")) == {}


def test_duong_kho_nam_trong_secrets_dir(tmp_path):
    m = _nap()
    d = m.duong_kho({"LTT_SECRETS_DIR": str(tmp_path / "sec")})
    assert d == str(tmp_path / "sec" / "tai_khoan_thu.json")


def test_cookie_tu_choi_email_khong_co_trong_kho(tmp_path, monkeypatch, capsys):
    m = _nap()
    monkeypatch.setenv("LTT_SECRETS_DIR", str(tmp_path))
    assert m.main(["--cookie", "khach9.thu@lttstudios.local"]) == 2
    assert "khong co trong kho" in capsys.readouterr().err


def test_cookie_KHONG_in_mat_khau(tmp_path, monkeypatch, capsys):
    m = _nap()
    monkeypatch.setenv("LTT_SECRETS_DIR", str(tmp_path))
    kho = {}
    m._luu(kho, "khach1.thu@lttstudios.local", "BiMatKhongDuocIn42", "Khach thu 1")
    m.ghi_kho(m.duong_kho(), kho)
    goi = {}

    def gia(email, mk, goc):
        goi.update(email=email, mk=mk, goc=goc)
        return "gia-tri-phien"

    monkeypatch.setattr(m, "lay_cookie", gia)
    assert m.main(["--cookie", "KHACH1.thu@lttstudios.local", "--goc", "http://x"]) == 0
    ra = capsys.readouterr()
    assert ra.out.strip() == "session=gia-tri-phien"
    assert "BiMatKhongDuocIn42" not in ra.out + ra.err
    assert goi == {"email": "khach1.thu@lttstudios.local", "mk": "BiMatKhongDuocIn42", "goc": "http://x"}


@pytest.mark.parametrize("mk_dung", [True, False])
def test_lay_cookie_mang_phien_bang_header_va_chi_nhan_3xx(monkeypatch, mk_dung):
    """Cookie production mang `Secure` ⇒ phải tự gửi lại bằng header qua loopback;
    sai mật khẩu (form trả lại 400) không được coi là phiên đã đăng nhập."""
    import email.message
    import io
    import urllib.error
    import urllib.request
    m = _nap()
    thay = {}

    def _hd(cookie):
        h = email.message.Message()
        h["Set-Cookie"] = f"session={cookie}; path=/; httponly; samesite=lax; secure"
        return h

    class Tra(io.BytesIO):
        def __init__(self, body, status, headers):
            super().__init__(body)
            self.status, self.headers = status, headers

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class Mo:
        def open(self, req, timeout=0):
            if isinstance(req, str):
                return Tra(b'<input name="csrf_token" value="abc">', 200, _hd("an-danh"))
            thay["cookie"] = req.get_header("Cookie")
            if mk_dung:
                raise urllib.error.HTTPError(req.full_url, 303, "See Other", _hd("phien-that"), None)
            raise urllib.error.HTTPError(req.full_url, 400, "Bad", _hd("an-danh-2"), None)

    monkeypatch.setattr(urllib.request, "build_opener", lambda *h: Mo())
    if mk_dung:
        assert m.lay_cookie("khach1.thu@lttstudios.local", "x") == "phien-that"
    else:
        with pytest.raises(RuntimeError):
            m.lay_cookie("khach1.thu@lttstudios.local", "sai")
    assert thay["cookie"] == "session=an-danh"
