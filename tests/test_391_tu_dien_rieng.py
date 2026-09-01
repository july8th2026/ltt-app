"""Từ điển phát âm RIÊNG của khách — module mà chuỗi tham số đã chờ từ lâu.

## Vì sao nó là một module thật, không phải trang trí

Ảnh 01 vẽ mục ⑤ `PRONUNCIATION`. Nhưng điều đáng nói hơn: `chuan_bi_van_ban(
tu_dien_rieng=...)` → `text_pipeline.chuan_hoa` → `tu_dien.ap_dung(them=...)`
đã nhận tham số này qua BA TẦNG, và **không ai truyền** — cả đường ống dựng
xong rồi để không cho tới 01/09/2026.

⛔ Không có nó thì khách phải **gõ sai chính tả trong kịch bản** để ép engine
   đọc đúng tên riêng (upstream #168, `ch` -> `tr`) — và bản chép sai ấy đi vào
   tài liệu của họ, vào phụ đề, vào mọi chỗ khác.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def khach(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'td.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-tu-dien")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.ltt_voice.tables  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "kho")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="td@test.com", password="matkhau-tot-12",
                           is_verified=True)
        db.commit()
        uid = str(u.id)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver",
                   follow_redirects=False)
    m = re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").text)
    assert m
    c.post("/login", data={"username": "td@test.com",
                           "password": "matkhau-tot-12",
                           "csrf_token": m.group(1)})
    try:
        yield c, uid
    finally:
        c.close()
        set_storage(None)
        dbmod.reset_engine()


def _csrf(client) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"',
                  client.get("/ltt-voice").text)
    assert m
    return m.group(1)


def test_them_roi_ap_vao_chuan_hoa(khach):
    """🔴 Phép kiểm QUAN TRỌNG NHẤT: mục thêm vào có THẬT SỰ đổi cách đọc không.

    Một bảng + một route + một ô nhập mà không nối tới `chuan_hoa` thì vẫn
    "chạy" ở mọi phép kiểm CRUD — và không làm gì cả.
    """
    import platform_core.db as dbmod

    from apps.ltt_voice import features, tu_dien_rieng

    client, uid = khach
    r = client.post("/ltt-voice/tu-dien/them",
                    data={"tu": "Chuong", "thay": "Chuwowng",
                          "csrf_token": _csrf(client)})
    assert r.status_code == 200 and r.json()["ok"], r.text

    gen = dbmod.get_session()
    db = next(gen)
    try:
        rieng = tu_dien_rieng.nhu_dict(db, uid)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    assert rieng == {"Chuong": "Chuwowng"}
    yc = features.chuan_hoa({"text": "Chuong mot bat dau", "preset": "Adam"})
    kq = features.chuan_bi_van_ban(yc, tran_moi_doan=1500,
                                   tu_dien_rieng=rieng)
    assert "Chuwowng" in kq.da_chuan_hoa, (
        f"muc tu dien KHONG duoc ap vao chuan hoa: {kq.da_chuan_hoa!r}")


def test_go_lai_cung_mot_tu_la_SUA_khong_phai_loi_trung(khach):
    client, _uid = khach
    for thay in ("mot", "hai"):
        r = client.post("/ltt-voice/tu-dien/them",
                        data={"tu": "abc", "thay": thay,
                              "csrf_token": _csrf(client)})
        assert r.json()["ok"], r.text
    ds = client.get("/ltt-voice/tu-dien").json()["muc"]
    assert len(ds) == 1 and ds[0]["thay"] == "hai", ds


def test_TU_CHOI_ky_tu_dac_biet(khach):
    """⛔ `tu_dien._mau` đã `re.escape`, nên không có đường tiêm regex.

    Nhưng vẫn từ chối ở cửa vào: một chuỗi trông như regex trong danh sách của
    khách là một thứ họ sẽ TƯỞNG là chạy.
    """
    client, _uid = khach
    for xau in (".*", "a|b", "(x)", "a\b", "<script>"):
        r = client.post("/ltt-voice/tu-dien/them",
                        data={"tu": xau, "thay": "gi do",
                              "csrf_token": _csrf(client)})
        assert r.status_code == 400, f"{xau!r} lot qua: {r.text[:120]}"


def test_TU_CHOI_muc_thay_chinh_no(khach):
    client, _uid = khach
    r = client.post("/ltt-voice/tu-dien/them",
                    data={"tu": "Abc", "thay": "abc",
                          "csrf_token": _csrf(client)})
    assert r.status_code == 400, "muc thay chinh no chiem mot suat ma khong lam gi"


def test_TRAN_so_muc_duoc_ap(khach):
    """Mỗi phép thay là một lượt quét toàn văn bản. Không trần = một cách để
    một tài khoản làm chậm worker cho mọi người."""
    from apps.ltt_voice import tu_dien_rieng

    client, _uid = khach
    csrf = _csrf(client)
    for i in range(tu_dien_rieng.TRAN_SO_MUC):
        r = client.post("/ltt-voice/tu-dien/them",
                        data={"tu": f"tu{i}", "thay": f"thay{i}",
                              "csrf_token": csrf})
        assert r.json()["ok"], (i, r.text[:120])
    r = client.post("/ltt-voice/tu-dien/them",
                    data={"tu": "qua-tran", "thay": "gi do", "csrf_token": csrf})
    assert r.status_code == 400, "vuot tran ma van nhan"


def test_xoa_muc_cua_NGUOI_KHAC_la_404(khach):
    import platform_core.db as dbmod

    from apps.ltt_voice.tables import VoiceTuDien

    client, _uid = khach
    gen = dbmod.get_session()
    db = next(gen)
    try:
        m = VoiceTuDien(owner_id="mot-nguoi-khac", tu="bimat", thay="bi mat")
        db.add(m)
        db.commit()
        mid = m.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = client.post(f"/ltt-voice/tu-dien/{mid}/xoa",
                    data={"csrf_token": _csrf(client)})
    assert r.status_code == 404, r.text


def test_o_TU_DIEN_hien_tren_man_studio(khach):
    client, _uid = khach
    html = client.get("/ltt-voice").text
    assert 'id="lv-td-hop"' in html, "thieu hop tu dien tren man Studio"
    assert 'id="lv-td-luu"' in html


def test_XEM_TRUOC_va_LUC_SINH_phai_ap_CUNG_mot_tu_dien(khach):
    """🔴 Bảng "Máy sẽ đọc thành" mà lệch với lúc sinh là một lời nói dối.

    Bảng ấy tồn tại để khách thấy trước máy đọc ra sao **trước khi trả tiền**.
    Nếu worker áp từ điển mà xem trước thì không, hai bên cho hai kết quả khác
    nhau — và bên khách nhìn thấy là bên SAI.

    ⚠️ Tôi mắc đúng lỗi này ngay trong lượt thêm chính tính năng: nối vào
       `jobs.py` rồi quên `xem_truoc`. Cùng lớp "một cửa có, cửa kia không" mà
       `features.py` đã cảnh báo — và cảnh báo ấy không cứu được tôi.
    """
    import platform_core.db as dbmod

    from apps.ltt_voice import features, tu_dien_rieng

    client, uid = khach
    csrf = _csrf(client)
    r = client.post("/ltt-voice/tu-dien/them",
                    data={"tu": "Chuong", "thay": "Chuwowng", "csrf_token": csrf})
    assert r.json()["ok"], r.text

    xt = client.post("/ltt-voice/xem-truoc",
                     data={"text": "Chuong mot", "csrf_token": csrf})
    assert xt.status_code == 200, xt.text
    thay_o_xem_truoc = xt.json()["da_chuan_hoa"]

    gen = dbmod.get_session()
    db = next(gen)
    try:
        rieng = tu_dien_rieng.nhu_dict(db, uid)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    yc = features.chuan_hoa({"text": "Chuong mot", "preset": "Adam"})
    thay_luc_sinh = features.chuan_bi_van_ban(
        yc, tran_moi_doan=1500, tu_dien_rieng=rieng).da_chuan_hoa

    assert thay_o_xem_truoc == thay_luc_sinh, (
        f"xem truoc va luc sinh KHAC NHAU:\n"
        f"  xem truoc: {thay_o_xem_truoc!r}\n"
        f"  luc sinh : {thay_luc_sinh!r}")
    assert "Chuwowng" in thay_o_xem_truoc
