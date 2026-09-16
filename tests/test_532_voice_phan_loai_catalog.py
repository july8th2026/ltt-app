"""
GUI-D001 — MỘT luật phân loại giọng cho mọi màn: `mau` · `chung` · `toi`.

🔴 VÌ SAO TỆP NÀY TỒN TẠI (đo 15–16/09/2026 trên production).

   Trước bản vá có BA luật cho cùng một câu hỏi:

     · thẻ màn Giọng (`_voice_the.html`)  : mọi VoiceProfile là "Giọng của tôi";
     · bộ chọn Studio/Dự án (`_voice_chon`): "Kho chung" theo cờ `dung_chung`;
     · cổng đọc kho chung (`tham_chieu`)   : `dung_chung` VÀ `license == "ok"`.

   Hệ quả đo được: tài khoản chủ của 25 giọng `dung_chung=True` nhưng `cho_soat`
   thấy chúng mang nhãn "Kho chung" ở Studio, trong khi KHÔNG khách nào khác thấy
   chúng; và ở màn Giọng, khách xem một giọng kho chung của người khác được mở khối
   quản lý (Tắt, Xoá vĩnh viễn, clip gốc) cùng khoá kho thô mang UUID chủ sở hữu.

⭐ Các phép kiểm dưới đây soi HTML ĐÃ RENDER qua cửa HTTP thật, với HAI tài khoản
   (người xem + một chủ giọng khác) — vì cả ba lỗi trên đều vô hình khi chỉ nhìn
   bằng tài khoản chủ, đúng như lượt kiểm 15/09 đã nhìn.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
JS = GOC / "server" / "static" / "voice.js"
MAU = GOC / "apps" / "ltt_voice" / "templates"


class _HoSo:
    def __init__(self, owner_id):
        self.owner_id = owner_id
        self.public_id = "vc_x"


def test_loai_giong_theo_CHU_SO_HUU_khong_theo_co():
    from apps.ltt_voice import tham_chieu

    assert tham_chieu.loai_giong(_HoSo("u1"), "u1") == tham_chieu.LOAI_TOI
    assert tham_chieu.loai_giong(_HoSo("u2"), "u1") == tham_chieu.LOAI_CHUNG
    # UUID đến từ hai nguồn (cột chuỗi / đối tượng) — so theo chuỗi.
    assert tham_chieu.loai_giong(_HoSo(123), "123") == tham_chieu.LOAI_TOI


@pytest.fixture()
def hai_tk(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-532.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-voice-532")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from apps.ltt_voice.tables import VoiceProfile, VoiceRef
    from platform_core.models import User
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    set_storage(LocalStorage(str(tmp_path / "store")))

    gen = dbmod.get_session()
    db = next(gen)
    try:
        for email in ("xem-532@test.com", "chu-532@test.com"):
            tao_nguoi_dung(db, email=email, password="matkhau-tot-12",
                           is_verified=True)
        db.commit()
        xem = str(db.query(User).filter_by(email="xem-532@test.com").one().id)
        chu = str(db.query(User).filter_by(email="chu-532@test.com").one().id)

        def ho_so(owner, ten, dung_chung, lic):
            h = VoiceProfile(owner_id=owner, ten_hien_thi=ten, trang_thai="active",
                             dung_chung=dung_chung, license_status=lic,
                             # 28/29 hồ sơ production mang nguồn làn này — và
                             # form khai làn chỉ dựng cho `mac_dinh_cu`/`khai_bao`.
                             ngon_ngu="vi", ngon_ngu_nguon="mac_dinh_cu")
            db.add(h)
            db.flush()
            db.add(VoiceRef(profile_id=h.id,
                            storage_key=f"voice/{owner}/{h.public_id}/source.wav",
                            sha256="0" * 64, mime="audio/wav", so_byte=10, giay=1.0))
            return h.public_id

        ma = {
            "rieng": ho_so(xem, "Rieng cua toi", False, "cho_soat"),
            # Hình dạng của 25 giọng production: cờ bật, license CHƯA duyệt.
            "chung_chua_duyet_cua_toi": ho_so(xem, "Chung chua duyet", True,
                                              "cho_soat"),
            "chung_nguoi_khac": ho_so(chu, "Chung cua nguoi khac", True, "ok"),
            "chua_duyet_nguoi_khac": ho_so(chu, "Chua duyet nguoi khac", True,
                                           "cho_soat"),
        }
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    m = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    assert m
    client.post("/login", data={"username": "xem-532@test.com",
                                "password": "matkhau-tot-12",
                                "csrf_token": m.group(1)})
    try:
        yield client, ma, chu
    finally:
        client.close()
        set_storage(None)
        dbmod.reset_engine()


def test_man_GIONG_the_mang_dung_loai_cho_nguoi_xem(hai_tk):
    client, ma, _chu = hai_tk
    r = client.get("/ltt-voice/giong")
    assert r.status_code == 200, r.text[:500]
    html = r.text

    def loai(k):
        m = re.search(rf'<article class="lv-the[^"]*"\s+data-ma="{re.escape(ma[k])}"'
                      rf'\s+data-loai="([^"]*)"', html)
        assert m, f"khong thay the {k}"
        return m.group(1)

    assert loai("rieng") == "toi"
    assert loai("chung_nguoi_khac") == "chung"
    # Cờ `dung_chung` bật nhưng CHƯA duyệt, và người xem là chủ ⇒ "của tôi".
    assert loai("chung_chua_duyet_cua_toi") == "toi"
    # Chưa duyệt của người khác thì không lọt vào trang chút nào.
    assert ma["chua_duyet_nguoi_khac"] not in html
    # Có nút lọc "Kho chung" để lọc đúng loại vừa gắn.
    assert 'data-loc="loai" data-gt="chung"' in html


def test_man_GIONG_khong_gui_clip_goc_va_UUID_cua_nguoi_khac(hai_tk):
    client, ma, chu = hai_tk
    html = client.get("/ltt-voice/giong").text
    # Khoá kho thô của giọng người khác mang UUID chủ — không được nằm trong trang.
    assert f"voice/{chu}/" not in html
    m = re.search(r"chiTiet:\s*(\{.*?\}),\s*\n", html, re.S)
    assert m, "khong doc duoc chiTiet"
    ct = json.loads(m.group(1))
    assert ct[ma["chung_nguoi_khac"]]["clip"] == []
    assert len(ct[ma["rieng"]]["clip"]) == 1


def test_man_GIONG_form_khai_lan_CHI_cho_giong_cua_toi_khong_dung_chung(hai_tk):
    client, ma, _chu = hai_tk
    html = client.get("/ltt-voice/giong").text
    assert f'/giong/{ma["rieng"]}/ngon-ngu' in html
    assert f'/giong/{ma["chung_nguoi_khac"]}/ngon-ngu' not in html
    assert f'/giong/{ma["chung_chua_duyet_cua_toi"]}/ngon-ngu' not in html
    # Giọng mẫu (preset) không bao giờ có form khai làn — lỗi 21-biểu-mẫu 65e099af.
    assert not re.search(r'/giong/[^"/]+/ngon-ngu', html.replace(ma["rieng"], ""))


def test_STUDIO_bo_chon_dung_CUNG_luat_voi_man_giong(hai_tk):
    client, ma, _chu = hai_tk
    html = client.get("/ltt-voice").text

    def loai(k):
        m = re.search(r'<label class="lv-chon-muc"\s+data-loai="([^"]*)"[^>]*>\s*'
                      rf'<input type="radio" name="giong" value="v:{re.escape(ma[k])}"',
                      html)
        assert m, f"khong thay muc {k} trong bo chon"
        return m.group(1)

    assert loai("rieng") == "toi"
    assert loai("chung_nguoi_khac") == "chung"
    # Bản trước theo `g.dung_chung` và gắn "chung" ở đây — sai.
    assert loai("chung_chua_duyet_cua_toi") == "toi"


@pytest.mark.parametrize("duong, attr", [("/ltt-voice/giong", 'data-loc="loai" data-gt'),
                                         ("/ltt-voice", "data-chon-loai")])
def test_V01_so_dem_THAT_tren_tung_loai(hai_tk, duong, attr):
    """V01: Tất cả = mẫu + chung + của tôi, số lấy từ dữ liệu — không gõ cứng."""
    from apps.ltt_voice import giong_mau
    client, _ma, _chu = hai_tk
    html = client.get(duong).text

    def dem(gt):
        m = re.search(rf'{attr}="{gt}">[^<]*<span class="lv-dem">(\d+)</span>', html)
        assert m, f"khong thay so dem cho `{gt}` o {duong}"
        return int(m.group(1))

    mau = len(giong_mau.DANH_SACH)
    assert dem("mau") == mau
    assert dem("chung") == 1                   # chỉ giọng kho chung đã duyệt của người khác
    assert dem("toi") == 2                     # riêng + dung_chung chưa duyệt của chính mình
    assert dem("") == mau + 1 + 2


def test_template_khong_con_tu_suy_loai_tu_co():
    the = (MAU / "_voice_the.html").read_text(encoding="utf-8")
    chon = (MAU / "_voice_chon.html").read_text(encoding="utf-8")
    giong = (MAU / "ltt_voice_giong.html").read_text(encoding="utf-8")
    ma_nguon = [re.sub(r"\{#.*?#\}", "", s, flags=re.S) for s in (the, chon, giong)]
    for s in ma_nguon:
        assert not re.search(r"\bla_mau\b", s)
        assert not re.search(r"data-loai=\"\{\{[^}]*dung_chung", s)
    assert "loai_giong[g.public_id]" in ma_nguon[1]
    assert "loai_giong[g.public_id]" in ma_nguon[2]


def test_D004_MOT_luat_loc_nhan_cho_ca_man_Giong_va_bo_chon():
    """GUI-D004: thẻ THIẾU nhãn giới/vùng/phong cách KHÔNG bị ẩn ở CẢ HAI màn.

    🔴 Trước 16/09 màn Giọng ẩn (rồi đếm), bộ chọn Studio giữ — cùng một giọng,
       lọc "Nam" thì mất ở màn này mà còn ở màn kia. 29/29 VoiceProfile production
       có `gioi` rỗng (đo 15/09), nên luật cũ ẩn sạch giọng nhân bản."""
    js = JS.read_text(encoding="utf-8")
    for truc in ("gioi", "vung", "phongcach"):
        assert f"(!dangLoc.{truc} || !d.{truc} || d.{truc} === dangLoc.{truc})" in js, (
            f"man Giong van AN the thieu nhan `{truc}` — lech bo chon Studio")
    assert "!locGioi || !d.gioi || d.gioi === locGioi" in js


def test_voice_js_khoi_quan_ly_chi_mo_cho_giong_cua_toi():
    js = JS.read_text(encoding="utf-8")
    assert "khoiToi.hidden = !laToi;" in js
    assert 'var laToi = d.loai === "toi";' in js
    assert "khoiToi.hidden = laMau;" not in js
