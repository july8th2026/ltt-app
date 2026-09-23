"""
video_crawler — trang vận hành KHO TÀI KHOẢN (W4-L9b; chủ dự án duyệt 23/09/2026).

Trang `/video-crawler/van-hanh/tai-khoan`: operator thêm/tạm nghỉ/bật lại/xoá tài khoản phụ trong
`kho_tai_khoan.py` (đọc, không sửa — lane L9). Ba điều bắt buộc:

- CHỈ operator dùng được (403 khách thường, 404 khi cờ `LTT_VIDEO_CRAWLER` tắt — cùng khuôn `van_hanh`).
- Giá trị cookie KHÔNG bao giờ ra khỏi CSDL/tệp tạm: không hiện trong bảng, không trong thông báo lỗi,
  không trong nhật ký thao tác — kể cả khi operator vừa dán cookie giả để thêm tài khoản.
- Lỗi nhập (sai nền ngoài đợt đầu, thiếu cookie xác thực, tệp quá lớn) phải có thông điệp rõ, không phải
  500 hay im lặng.
"""
from __future__ import annotations

import re

import pytest

_BI_MAT_GIA = "sessionid-GIA-w4l9b-khong-phai-cookie-thuc-0123456789"


def _cookies_txt(bi_mat: str = _BI_MAT_GIA, het_han: int = 1893456000, domain: str = ".douyin.com") -> str:
    return ("# Netscape HTTP Cookie File\n"
            f"{domain}\tTRUE\t/\tTRUE\t{het_han}\tsessionid\t{bi_mat}\n"
            f"{domain}\tTRUE\t/\tFALSE\t1893456000\tttwid\tcong-khai\n")


@pytest.fixture()
def van_hanh_client(tmp_path, monkeypatch):
    """Khuôn của `test_1924_video_crawler_suc_khoe.py:van_hanh_client`, thêm khoá mã hoá cho kho."""
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'tk.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vc-tk")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("LTT_VIDEO_CRAWLER", "1")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-trang-tai-khoan")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); s = next(gen)
    ops = tao_nguoi_dung(s, email="op@x.com", password="matkhau-tot", role="admin", is_verified=True)
    kh = tao_nguoi_dung(s, email="kh@x.com", password="matkhau-tot", role="user", is_verified=True)
    s.commit()
    ids = (ops.id, kh.id)
    s.close()

    from apps.video_crawler import routes_van_hanh
    from server.app import create_app
    app = create_app()
    app.include_router(routes_van_hanh.router, prefix="/video-crawler")
    client = TestClient(app, base_url="https://testserver")
    yield client, ids
    dbmod.reset_engine()


def _login(client, email):
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text).group(1)
    r = client.post("/login", data={"username": email, "password": "matkhau-tot", "csrf_token": tok},
                    follow_redirects=False)
    assert r.status_code == 303


def _csrf(html: str) -> str:
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


DUONG = "/video-crawler/van-hanh/tai-khoan"


# ═══════════════════════════════════════════════════════════════════════════
# A. Cổng: chỉ operator, cùng cờ LTT_VIDEO_CRAWLER với các trang khác
# ═══════════════════════════════════════════════════════════════════════════

def test_co_tat_thi_404_ca_khi_da_dang_nhap_operator(van_hanh_client, monkeypatch):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    monkeypatch.setenv("LTT_VIDEO_CRAWLER", "0")
    assert client.get(DUONG).status_code == 404


def test_khach_thuong_bi_chan_403(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "kh@x.com")
    assert client.get(DUONG).status_code == 403


def test_khach_thuong_khong_them_duoc_qua_post(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "kh@x.com")
    r = client.post(DUONG, data={"nen_tang": "douyin", "nhan": "x", "cookies_txt": _cookies_txt(),
                                 "csrf_token": "khong-quan-trong"})
    assert r.status_code == 403


def test_trang_rong_hien_thong_diep(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    r = client.get(DUONG)
    assert r.status_code == 200
    assert "Chưa có tài khoản" in r.text


# ═══════════════════════════════════════════════════════════════════════════
# B. Thêm tài khoản — CSRF, lỗi nhập rõ ràng, cookie KHÔNG BAO GIỜ hiện lại
# ═══════════════════════════════════════════════════════════════════════════

def test_them_thanh_cong_hien_trong_bang_khong_lo_cookie(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    tok = _csrf(client.get(DUONG).text)
    r = client.post(DUONG, data={"nen_tang": "douyin", "nhan": "phu-1",
                                 "cookies_txt": _cookies_txt(), "csrf_token": tok},
                    follow_redirects=False)
    assert r.status_code == 303
    r2 = client.get(DUONG)
    assert "phu-1" in r2.text
    assert "douyin" in r2.text
    assert _BI_MAT_GIA not in r2.text          # ⛔ giá trị cookie không bao giờ hiện lại


def test_thieu_csrf_khong_them(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    r = client.post(DUONG, data={"nen_tang": "douyin", "nhan": "phu-csrf",
                                 "cookies_txt": _cookies_txt(), "csrf_token": "sai"})
    assert r.status_code == 400
    assert "phu-csrf" not in client.get(DUONG).text


def test_nen_ngoai_dot_dau_bi_tu_choi_ro_rang_khong_lo_cookie(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    tok = _csrf(client.get(DUONG).text)
    r = client.post(DUONG, data={"nen_tang": "facebook", "nhan": "phu-fb",
                                 "cookies_txt": _cookies_txt(domain=".facebook.com"), "csrf_token": tok})
    assert r.status_code == 400
    assert _BI_MAT_GIA not in r.text
    assert "phu-fb" not in client.get(DUONG).text


def test_thieu_cookie_xac_thuc_bi_tu_choi(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    tok = _csrf(client.get(DUONG).text)
    # Có cookie thuộc domain douyin nhưng không phải cookie đăng nhập (sessionid/sessionid_ss/sid_tt).
    noi_dung = "# Netscape HTTP Cookie File\n.douyin.com\tTRUE\t/\tFALSE\t1893456000\tttwid\tcong-khai\n"
    r = client.post(DUONG, data={"nen_tang": "douyin", "nhan": "phu-thieu",
                                 "cookies_txt": noi_dung, "csrf_token": tok})
    assert r.status_code == 400
    assert "phu-thieu" not in client.get(DUONG).text


def test_cookie_qua_lon_bi_tu_choi(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    tok = _csrf(client.get(DUONG).text)
    r = client.post(DUONG, data={"nen_tang": "douyin", "nhan": "phu-to",
                                 "cookies_txt": "x" * (300 * 1024), "csrf_token": tok})
    assert r.status_code == 400
    assert "phu-to" not in client.get(DUONG).text


# ═══════════════════════════════════════════════════════════════════════════
# C. Bảng hiển thị — trạng thái, điểm, hạn cookie, mã lỗi (không phải văn bản thô)
# ═══════════════════════════════════════════════════════════════════════════

def _tao_hang(db, **kw):
    from apps.video_crawler import kho_tai_khoan
    from apps.video_crawler.tables import VcTaiKhoan
    mac_dinh = dict(nen_tang="tiktok", nhan="hang-test", cookie_ma_hoa="", trang_thai=kho_tai_khoan.SONG,
                    diem=kho_tai_khoan.DIEM_BAN_DAU)
    mac_dinh.update(kw)
    row = VcTaiKhoan(**mac_dinh)
    db.add(row)
    db.commit()
    return row


def test_ma_loi_hien_khong_phai_van_ban_tho(van_hanh_client):
    client, _ = van_hanh_client
    from platform_core.db import get_session
    gen = get_session(); s = next(gen)
    _tao_hang(s, nhan="loi-ma", loi_gan_nhat="yt_bot")
    s.close()

    _login(client, "op@x.com")
    r = client.get(DUONG)
    assert "yt_bot" in r.text
    assert "Traceback" not in r.text


def test_tam_nghi_va_bat_lai(van_hanh_client):
    client, (op_id, _) = van_hanh_client
    from platform_core.db import get_session
    gen = get_session(); s = next(gen)
    row = _tao_hang(s, nhan="bat-tat")
    tk_id = row.id
    s.close()

    _login(client, "op@x.com")
    tok = _csrf(client.get(DUONG).text)
    r = client.post(f"{DUONG}/{tk_id}/trang-thai", data={"trang_thai": "tam_nghi", "csrf_token": tok},
                    follow_redirects=False)
    assert r.status_code == 303

    gen2 = get_session(); s2 = next(gen2)
    from apps.video_crawler.tables import VcTaiKhoan
    from apps.video_crawler import kho_tai_khoan
    assert s2.get(VcTaiKhoan, tk_id).trang_thai == kho_tai_khoan.TAM_NGHI
    s2.close()

    tok2 = _csrf(client.get(DUONG).text)
    r2 = client.post(f"{DUONG}/{tk_id}/trang-thai", data={"trang_thai": "song", "csrf_token": tok2},
                     follow_redirects=False)
    assert r2.status_code == 303
    gen3 = get_session(); s3 = next(gen3)
    assert s3.get(VcTaiKhoan, tk_id).trang_thai == kho_tai_khoan.SONG
    s3.close()


def test_doi_trang_thai_thieu_csrf_bi_tu_choi(van_hanh_client):
    client, _ = van_hanh_client
    from platform_core.db import get_session
    gen = get_session(); s = next(gen)
    row = _tao_hang(s, nhan="bat-tat-csrf")
    tk_id = row.id
    s.close()

    _login(client, "op@x.com")
    r = client.post(f"{DUONG}/{tk_id}/trang-thai", data={"trang_thai": "tam_nghi", "csrf_token": "sai"})
    assert r.status_code == 400
    gen2 = get_session(); s2 = next(gen2)
    from apps.video_crawler.tables import VcTaiKhoan
    from apps.video_crawler import kho_tai_khoan
    assert s2.get(VcTaiKhoan, tk_id).trang_thai == kho_tai_khoan.SONG
    s2.close()


def test_xoa_co_xac_nhan_tren_giao_dien_va_xoa_that_qua_post(van_hanh_client):
    client, _ = van_hanh_client
    from platform_core.db import get_session
    gen = get_session(); s = next(gen)
    row = _tao_hang(s, nhan="xoa-toi")
    tk_id = row.id
    s.close()

    _login(client, "op@x.com")
    trang = client.get(DUONG)
    assert f"{DUONG}/{tk_id}/xoa" in trang.text
    assert "confirm(" in trang.text            # xác nhận phía giao diện trước khi gửi POST xoá

    tok = _csrf(trang.text)
    r = client.post(f"{DUONG}/{tk_id}/xoa", data={"csrf_token": tok}, follow_redirects=False)
    assert r.status_code == 303
    from apps.video_crawler.tables import VcTaiKhoan
    gen2 = get_session(); s2 = next(gen2)
    assert s2.get(VcTaiKhoan, tk_id) is None
    s2.close()


def test_xoa_thieu_csrf_khong_xoa(van_hanh_client):
    client, _ = van_hanh_client
    from platform_core.db import get_session
    gen = get_session(); s = next(gen)
    row = _tao_hang(s, nhan="giu-lai")
    tk_id = row.id
    s.close()

    _login(client, "op@x.com")
    r = client.post(f"{DUONG}/{tk_id}/xoa", data={"csrf_token": "sai"})
    assert r.status_code == 400
    from apps.video_crawler.tables import VcTaiKhoan
    gen2 = get_session(); s2 = next(gen2)
    assert s2.get(VcTaiKhoan, tk_id) is not None
    s2.close()


def test_chi_hien_nen_dot_dau_trong_o_chon(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    r = client.get(DUONG)
    assert 'value="douyin"' in r.text
    assert 'value="xiaohongshu"' in r.text
    assert 'value="tiktok"' in r.text
    assert 'value="facebook"' not in r.text
    assert 'value="youtube"' not in r.text


# ── Hướng dẫn THEO TỪNG NỀN (rà soát 23/09: trang chỉ có hướng dẫn chung) ────

def test_huong_dan_tung_nen_lay_tu_REGISTRY_khong_khai_tay():
    """Trang phải nói rõ: đứng ở tên miền nào khi xuất, cookie nào chứng minh đã đăng nhập. Dữ liệu lấy từ
    `nen_tang` — khai tay sẽ lệch ngay lần đầu registry đổi (thêm tên miền, đổi tên cookie)."""
    from apps.video_crawler import kho_tai_khoan, nen_tang, routes_van_hanh
    hd = {h["nen"]: h for h in routes_van_hanh._huong_dan_nen()}
    assert set(hd) == set(kho_tai_khoan.NEN_CO_KHO)
    for nen_id, h in hd.items():
        nen = nen_tang.lay(nen_id)
        assert h["ten_mien"] == list(nen.ten_mien)
        assert h["cookie"] == list(nen.cookie_dang_nhap)
        assert h["ten"] == nen.ten


def test_trang_hien_huong_dan_tung_nen(van_hanh_client):
    client, _ = van_hanh_client
    _login(client, "op@x.com")
    r = client.get(DUONG)
    assert r.status_code == 200
    for dau in ("douyin.com", "sessionid", "xiaohongshu.com", "id_token", "tiktok.com"):
        assert dau in r.text, dau
