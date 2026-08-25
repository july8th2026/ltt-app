"""Ranh giới công khai / riêng tư của khu API — chốt CẢ HAI chiều.

## Vì sao cần một phép kiểm chứ không phải một quy ước

Ranh giới đã được viết ra rõ ràng ở `KE_HOACH_MVP_CONG_LAP_TRINH_VIEN.md` §2.3:

    công khai: giá · công cụ có gì · cắm thế nào · gọi thử · điều khoản
    riêng tư : khoá · dự án · log · usage · webhook · ngân sách

Nhưng viết ra không giữ được nó. Dự án này đã học **cùng một bài ba lần**:

1. trang giá nằm sau `require_account` — sửa **riêng trang giá**;
2. hướng dẫn cắm nằm sau `require_account` — sửa **riêng hướng dẫn cắm**;
3. trang VPS đòi đăng nhập trong khi thẻ app hiện cho khách ẩn danh (25/08).

Mỗi lần đều sửa đúng trang đang đau, và mỗi lần bài học bay hơi cùng phiên
làm việc đó. Phép kiểm này là chỗ bài học ở lại.

## Hai chiều, và chiều thứ hai mới là chiều nguy hiểm

- **Chiều một:** trang trong `TRANG_CONG_KHAI` phải mở thật. Đóng lại một trang
  đang mở là bịt đầu phễu bán hàng, im lặng.
- **Chiều hai:** trang **không** trong danh sách đó phải vẫn đóng. Thêm một
  trang vào `TRANG_CONG_KHAI` là một dòng sửa dễ, và nếu trang đó đọc dữ liệu
  tài khoản thì đó là rò dữ liệu của khách — không có triệu chứng nào cho tới
  khi có người báo.
"""
from __future__ import annotations

import re

import pytest

from server.routes import developer as dev


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'api-ranh-gioi.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-api-ranh-gioi")
    monkeypatch.setenv("LTT_PUBLIC_API", "1")
    monkeypatch.setenv("LTT_API_KEY_PEPPER", "x" * 40)
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models   # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield dbmod
    dbmod.reset_engine()


def _client():
    from fastapi.testclient import TestClient
    from server.app import create_app
    return TestClient(create_app(), base_url="https://testserver",
                      follow_redirects=False)


def _tao_khach(dbmod):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="dev-rg@test.com",
                           password="matkhau-tot-12", is_verified=True)
        db.flush()
        credit.nap(db, u.id, 5_000)
        db.commit()
        return u.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _dang_nhap(client):
    r = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', r.text).group(1)
    client.post("/login", data={"username": "dev-rg@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": token})


# ── Chiều một: trang công khai phải MỞ ─────────────────────────────────────

def test_danh_sach_cong_khai_dung_bang_chot_cua_chu_san_pham():
    """Hôm nay danh sách này RỖNG, và đó là một chốt chứ không phải việc chưa làm.

    Chủ sản phẩm chốt 25/08: `/developers/tools` đứng sau đăng nhập là đúng, vì
    hệ thống API phải đăng nhập mới kích hoạt được — danh mục công cụ là trang
    của một tài khoản, không phải trang bán hàng. `quickstart` không nằm trong
    chốt đó nên cũng không được mở theo suy diễn.

    Phép kiểm này tồn tại vì `parametrize` trên một danh sách rỗng **không chạy
    phép kiểm nào**: không có nó, hai phép kiểm dưới đây sẽ im lặng biến mất và
    không ai biết. Đổi danh sách thì đổi cả phép kiểm này — và lúc đó người sửa
    buộc phải đọc lý do ở trên.
    """
    assert dev.TRANG_CONG_KHAI == frozenset(), (
        "danh sach trang cong khai vua doi. Doc "
        "docs/PUBLIC_API/QUY_CHUAN_TRANG_TAI_LIEU_API.md §1 truoc khi doi no, "
        "va cap nhat ca hai tai lieu quy chuan cho khop.")


@pytest.mark.parametrize("khoa", sorted(dev.TRANG_CONG_KHAI))
def test_trang_cong_khai_mo_that_cho_khach_an_danh(moi_truong, khoa):
    duong = dict((k, h) for k, h, _l in dev.SECTIONS)[khoa]
    client = _client()
    try:
        r = client.get(duong)
        assert r.status_code == 200, (
            f"{duong} tra {r.status_code} cho khach an danh — "
            "mot nguoi dang CAN NHAC khong doc duoc mot dong nao")
    finally:
        client.close()


# ── Chiều hai: mọi trang còn lại phải vẫn ĐÓNG ─────────────────────────────

@pytest.mark.parametrize(
    "khoa,duong",
    [(k, h) for k, h, _l in dev.SECTIONS if k not in dev.TRANG_CONG_KHAI])
def test_trang_rieng_tu_van_doi_dang_nhap(moi_truong, khoa, duong):
    client = _client()
    try:
        r = client.get(duong)
        assert r.status_code == 303, (
            f"{duong} tra {r.status_code} cho khach an danh. Neu trang nay "
            "vua duoc mo cong khai thi no phai vao TRANG_CONG_KHAI *va* phai "
            "duoc doc lai xem no co cham du lieu tai khoan khong.")
    finally:
        client.close()


def test_trang_cong_khai_KHONG_doc_du_lieu_tai_khoan(moi_truong):
    """Hai trang mở phải dựng từ catalog, không từ tài khoản nào.

    Đây là điều kiện làm cho việc mở chúng an toàn. Nếu một ngày ai đó thêm
    số dư hay tên project vào một trong hai trang này, khách ẩn danh sẽ thấy
    dữ liệu của **người khác** — hoặc trang sẽ 500. Cả hai đều tệ.
    """
    _tao_khach(moi_truong)
    client = _client()
    try:
        an_danh = {k: client.get(dict((a, b) for a, b, _ in dev.SECTIONS)[k]).text
                   for k in sorted(dev.TRANG_CONG_KHAI)}
        _dang_nhap(client)
        da_vao = {k: client.get(dict((a, b) for a, b, _ in dev.SECTIONS)[k]).text
                  for k in sorted(dev.TRANG_CONG_KHAI)}
    finally:
        client.close()

    for k in an_danh:
        assert "dev-rg@test.com" not in an_danh[k], f"{k} lo email"
        # Thân trang (phần `section`) phải giống nhau: nội dung là của catalog,
        # không phải của người xem. Vỏ thì khác (thanh điều hướng, đăng nhập).
        for moc in ("<h1", "</main>"):
            assert moc in an_danh[k] and moc in da_vao[k]


def test_thanh_dieu_huong_khach_an_danh_khong_dan_toi_ngo_cut(moi_truong):
    """16 mục cho khách ẩn danh = 14 liên kết bật về `/login`."""
    client = _client()
    try:
        t = client.get("/developers/tools").text
    finally:
        client.close()
    duong_rieng = [h for k, h, _l in dev.SECTIONS
                   if k not in dev.TRANG_CONG_KHAI]
    lot = [d for d in duong_rieng if f'href="{d}"' in t]
    assert lot == [], (
        f"thanh dieu huong cho khach an danh chua {len(lot)} lien ket bat ve "
        f"/login: {lot[:5]}")


def test_trang_cong_khai_moi_khach_dang_ky(moi_truong):
    """Mở trang ra mà không nói bước tiếp theo là bỏ khách giữa đường.

    ⚠️ Phải tìm trong `<main>`, không phải cả trang. Bản đầu của phép kiểm này
    chỉ hỏi `"/register" in t` và **xanh vì header toàn cục luôn có nút "Đăng
    ký"** — tức nó xanh trong khi trang không mời gì cả. Một phép kiểm xanh vì
    lý do sai còn tệ hơn không có: nó nói rằng việc đã xong.
    """
    client = _client()
    try:
        for k in sorted(dev.TRANG_CONG_KHAI):
            duong = dict((a, b) for a, b, _ in dev.SECTIONS)[k]
            t = client.get(duong).text
            m = re.search(r"(?is)<main\b.*?</main>", t)
            assert m, f"{duong} khong co <main>"
            assert "/register" in m.group(0), (
                f"{duong} khong co loi moi dang ky TRONG than trang "
                "(lien ket o header khong tinh)")
    finally:
        client.close()

    # Va khi da dang nhap thi loi moi do phai BIEN MAT: moi mot nguoi da co tai
    # khoan di tao tai khoan la mot cau vo nghia o giua trang.
    _tao_khach(moi_truong)
    client = _client()
    try:
        _dang_nhap(client)
        for k in sorted(dev.TRANG_CONG_KHAI):
            duong = dict((a, b) for a, b, _ in dev.SECTIONS)[k]
            m = re.search(r"(?is)<main\b.*?</main>", client.get(duong).text)
            assert "/register" not in m.group(0), (
                f"{duong} van moi nguoi DA dang nhap di dang ky")
    finally:
        client.close()


def test_co_LTT_PUBLIC_API_van_dung_truoc(moi_truong, monkeypatch):
    """Công khai nghĩa là 'không đòi đăng nhập', KHÔNG phải 'bỏ qua cờ'."""
    monkeypatch.delenv("LTT_PUBLIC_API", raising=False)
    client = _client()
    try:
        for k in sorted(dev.TRANG_CONG_KHAI):
            duong = dict((a, b) for a, b, _ in dev.SECTIONS)[k]
            r = client.get(duong)
            # Trang vẫn mở (nó nói cho khách biết API đang tắt), nhưng phải
            # NÓI RA điều đó thay vì hiện một danh mục rỗng không giải thích.
            assert r.status_code == 200
            assert "LTT_PUBLIC_API" in r.text or "API" in r.text
    finally:
        client.close()
