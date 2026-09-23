"""video_crawler — chế độ "Tìm kênh" + trang kênh trong app (làn W4-L11, THIET_KE_PHIEN_VA_KENH §3.3, §4).

Không phép nào chạm mạng: adapter được TIÊM giả (`tao_adapter=`), ảnh đại diện tiêm qua `lay=`.

Mệnh đề chốt:
- Chế độ "Tìm kênh" chỉ hiện với nền `nen_tang.co_tim_kenh(id)` True — hỏi lớp adapter, không khai tay.
- Thẻ kênh: ảnh đại diện đi qua PROXY của app (URL CDN không bao giờ vào HTML), tên, số theo dõi
  (trống ⇒ không hiện số 0), nút "Xem video của kênh".
- Trang kênh: tab (chỉ khi adapter khai), sắp xếp, khoảng ngày, thời lượng, số lượng ≤ 20, "không trùng";
  tuỳ chọn đi vào `params.tuy_chon` của job khám phá, rào an toàn cũ (URL/SSRF/tần suất/cam kết) giữ nguyên.
- Nền chưa tìm kênh được / chưa có phiên ⇒ CÂU RÕ cho khách, không phải 500.
"""
from __future__ import annotations

import re
import socket

import pytest

from apps.video_crawler import features
from apps.video_crawler.adapters.base import KenhItem, LoiCao, YeuCauTimKenh, loi_chua_ho_tro_tim_kenh

KENH_YT = "UCSJ4gkVC6NrvII8umztf0Ow"
URL_KENH_YT = f"https://www.youtube.com/channel/{KENH_YT}"
ANH_YT = "https://yt3.ggpht.com/a.jpg"


def _kenh(i: int = 0, **kw) -> KenhItem:
    d = {"nen_tang": "youtube", "id": f"UC{i:022d}", "ten": f"Kênh {i}",
         "url": f"https://www.youtube.com/channel/UC{i:022d}", "anh_dai_dien": ANH_YT,
         "so_theo_doi": 15800000, "so_video": 12, "mo_ta": "lofi"}
    d.update(kw)
    return KenhItem(**d)


class AdapterGia:
    """Adapter tối thiểu cho tầng features: KHÔNG có `tep_cookie` ⇒ `jobs._phien` đi thẳng (ẩn danh)."""
    nen_tang = "youtube"
    TAB_KENH: tuple = ()

    def __init__(self, ket_qua=None, loi=None):
        self.ket_qua = ket_qua if ket_qua is not None else [_kenh(0), _kenh(1)]
        self.loi = loi
        self.goi: list[YeuCauTimKenh] = []

    def tim_kenh(self, yeu_cau, *, bao_tien_do):
        self.goi.append(yeu_cau)
        bao_tien_do(50, "dang tim")
        if self.loi is not None:
            raise self.loi
        return list(self.ket_qua)


def _tao(adapter):
    return lambda nen_id: adapter


def _tim(adapter=None, *, owner="u-tim", nen="youtube", tu_khoa="lofi girl", n=5, db=None):
    return features.tim_kenh(db, owner_id=owner, nen_tang=nen, tu_khoa=tu_khoa, so_luong=n,
                             tao_adapter=_tao(adapter if adapter is not None else AdapterGia()))


# ============================================================ features.tim_kenh

def test_tim_kenh_tra_the_kenh_va_ton_trong_so_luong():
    ad = AdapterGia(ket_qua=[_kenh(i) for i in range(9)])
    ra = _tim(ad, owner="u1", n=3)
    assert [k.id for k in ra] == [_kenh(i).id for i in range(3)]
    assert ad.goi[0] == YeuCauTimKenh(nen_tang="youtube", tu_khoa="lofi girl", so_luong=3)


def test_tim_kenh_tu_khoa_rong_hoac_qua_dai_bi_tu_choi():
    with pytest.raises(features.LoiDauVao):
        _tim(owner="u2", tu_khoa="   ")
    with pytest.raises(features.LoiDauVao):
        _tim(owner="u2", tu_khoa="x" * (features.DAU_VAO_TOI_DA + 1))


def test_tim_kenh_so_luong_ngoai_khoang_bi_tu_choi():
    for xau in (0, -1, 999, "abc", None):
        with pytest.raises(features.LoiDauVao):
            _tim(owner="u3", n=xau)


def test_tim_kenh_nen_chua_bat_bi_tu_choi():
    with pytest.raises(features.LoiDauVao):
        _tim(owner="u4", nen="khong-co-nen-nay")


def test_tim_kenh_nen_khong_ho_tro_cho_cau_ro_khong_phai_500():
    """Adapter THẬT của Facebook chưa tìm kênh được (không khai `ie_key_kenh`) ⇒ câu hướng dẫn dán link.

    Không tiêm adapter giả ở phép này: chính lớp adapter thật là thứ cần được hỏi.
    """
    assert not features.nen_tim_kenh_duoc("facebook")
    with pytest.raises(features.LoiDauVao) as e:
        features.tim_kenh(None, owner_id="u5", nen_tang="facebook", tu_khoa="abc", so_luong=3)
    assert "link" in str(e.value).lower()


def test_tim_kenh_loi_adapter_thanh_cau_cua_khach():
    ad = AdapterGia(loi=loi_chua_ho_tro_tim_kenh())
    with pytest.raises(features.LoiDauVao) as e:
        _tim(ad, owner="u6")
    assert str(e.value)
    ad2 = AdapterGia(loi=LoiCao("nen_chan", "Nền tạm chặn máy chủ.", tam_thoi=True))
    with pytest.raises(features.LoiDauVao) as e2:
        _tim(ad2, owner="u6b")
    assert "chặn" in str(e2.value)


def test_tim_kenh_khong_ai_khop_la_danh_sach_rong_khong_phai_loi():
    assert _tim(AdapterGia(ket_qua=[]), owner="u7") == []


def test_tim_kenh_tran_tan_suat_moi_phut():
    ad = AdapterGia()
    for _ in range(features.TIM_KENH_MOI_PHUT):
        _tim(ad, owner="u8")
    with pytest.raises(features.QuaTanSuat):
        _tim(ad, owner="u8")
    _tim(ad, owner="u8-khac")            # trần theo từng khách, không phải toàn hệ thống


def test_tim_kenh_nen_can_phien_chua_co_phien_va_chua_co_kho_cho_cau_huong_dan():
    """Bilibili cần phiên cho mọi chế độ và KHÔNG có kho tài khoản ⇒ câu "cần đăng nhập" hiện có."""
    from apps.video_crawler import kho_tai_khoan
    assert "bilibili" not in kho_tai_khoan.NEN_CO_KHO
    ad = AdapterGia()
    ad.nen_tang = "bilibili"
    with pytest.raises(features.LoiDauVao) as e:
        features.tim_kenh(None, owner_id="u9", nen_tang="bilibili", tu_khoa="lofi", so_luong=3,
                          tao_adapter=_tao(ad))
    assert "đăng nhập" in str(e.value).lower()
    assert ad.goi == []


# ============================================================ tab do ADAPTER khai

def test_tab_kenh_lay_tu_adapter_khong_khai_tay():
    class CoTab(AdapterGia):
        TAB_KENH = (("videos", "Video"), ("shorts", "Shorts"))
    assert features.tab_kenh("youtube", tao_adapter=_tao(CoTab())) == (("videos", "Video"), ("shorts", "Shorts"))
    assert features.tab_kenh("youtube", tao_adapter=_tao(AdapterGia())) == ()
    assert features.tab_kenh("khong-co-nen-nay") == ()


# ============================================================ tuỳ chọn trang kênh

def test_chuan_tuy_chon_kenh_gia_tri_hop_le():
    tc = features.chuan_tuy_chon_kenh("youtube", sap_xep="moi_nhat", tu_ngay="2026-01-01",
                                      den_ngay="2026-02-01", thoi_luong="ngan")
    assert tc == {"sap_xep": "moi_nhat", "tu_ngay": "2026-01-01", "den_ngay": "2026-02-01",
                  "thoi_luong": "ngan"}
    assert features.chuan_tuy_chon_kenh("youtube") == {}


def test_chuan_tuy_chon_kenh_tu_choi_gia_tri_la():
    for kw in ({"sap_xep": "ngau_nhien"}, {"thoi_luong": "sieu_dai"}, {"tu_ngay": "01/02/2026"},
               {"den_ngay": "2026-13-45"}, {"tu_ngay": "2026-02-01", "den_ngay": "2026-01-01"},
               {"tab": "videos"}):                     # adapter chưa khai tab nào ⇒ tab lạ bị từ chối
        with pytest.raises(features.LoiDauVao):
            features.chuan_tuy_chon_kenh("youtube", **kw)


def test_chuan_tuy_chon_kenh_nhan_tab_adapter_da_khai():
    class CoTab(AdapterGia):
        TAB_KENH = (("videos", "Video"),)
    assert features.chuan_tuy_chon_kenh("youtube", tab="videos",
                                        tao_adapter=_tao(CoTab())) == {"tab": "videos"}


def test_params_kham_pha_mang_tuy_chon_va_giu_rao_an_toan():
    p = features.dung_params_kham_pha(owner_id="u10", nen_tang="youtube", che_do="kenh",
                                      dau_vao=URL_KENH_YT, so_luong=5, khong_trung=True,
                                      tuy_chon={"thoi_luong": "ngan"},
                                      phan_giai=lambda h: ["142.250.66.78"])
    assert p["tuy_chon"] == {"thoi_luong": "ngan"} and p["che_do"] == "kenh"
    # Rào cũ nguyên vẹn: link ngoài tên miền của nền vẫn bị chặn dù có tuỳ chọn.
    with pytest.raises(features.LoiDauVao):
        features.dung_params_kham_pha(owner_id="u10", nen_tang="youtube", che_do="kenh",
                                      dau_vao="https://evil.example/channel/x", so_luong=5,
                                      khong_trung=False, tuy_chon={"thoi_luong": "ngan"},
                                      phan_giai=lambda h: ["142.250.66.78"])


def test_params_kham_pha_khong_tuy_chon_thi_khong_them_khoa():
    p = features.dung_params_kham_pha(owner_id="u11", nen_tang="youtube", che_do="tu_khoa",
                                      dau_vao="meo", so_luong=5, khong_trung=False)
    assert "tuy_chon" not in p


def test_loc_muc_theo_thoi_luong():
    muc = [{"id": "a", "thoi_luong_s": 30}, {"id": "b", "thoi_luong_s": 600},
           {"id": "c", "thoi_luong_s": 3600}, {"id": "d"}]
    assert [m["id"] for m in features.loc_muc(muc, {"thoi_luong": "ngan"})] == ["a"]
    assert [m["id"] for m in features.loc_muc(muc, {"thoi_luong": "vua"})] == ["b"]
    assert [m["id"] for m in features.loc_muc(muc, {"thoi_luong": "dai"})] == ["c"]
    assert features.loc_muc(muc, {}) == muc            # không lọc ⇒ nguyên danh sách (kể cả mục thiếu thời lượng)
    assert features.loc_muc(muc, None) == muc


# ============================================================ vé ảnh đại diện (ký, có hạn)

def test_ve_anh_kenh_ky_va_doc_lai(monkeypatch):
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vc-kenh")
    ve = features.ky_anh_kenh("u12", "youtube", ANH_YT)
    assert ANH_YT not in ve                             # URL CDN không lộ nguyên văn trong HTML
    assert features.doc_anh_kenh(ve, "u12") == ("youtube", ANH_YT)
    assert features.doc_anh_kenh(ve, "u-khac") is None  # vé của người khác
    assert features.doc_anh_kenh(ve + "x", "u12") is None
    assert features.doc_anh_kenh("", "u12") is None
    assert features.doc_anh_kenh(ve, "u12", max_age=-1) is None


# ============================================================ bề mặt web


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'k.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vc-kenh")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("LTT_VIDEO_CRAWLER", "1")
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.250.66.78", 443))])
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); s = next(gen)
    ua = tao_nguoi_dung(s, email="a@x.com", password="matkhau-tot", is_verified=True)
    ub = tao_nguoi_dung(s, email="b@x.com", password="matkhau-tot", is_verified=True)
    credit.nap(s, ua.id, 100); credit.nap(s, ub.id, 100)
    s.commit()
    ids = (ua.id, ub.id)
    s.close()
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    yield client, ids
    dbmod.reset_engine()


def _login(client, email):
    client.post("/logout", follow_redirects=False)
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text).group(1)
    assert client.post("/login", data={"username": email, "password": "matkhau-tot", "csrf_token": tok},
                       follow_redirects=False).status_code == 303


def _csrf(client):
    return re.search(r'name="csrf_token" value="([^"]+)"', client.get("/video-crawler").text).group(1)


def _tiem_adapter(monkeypatch, adapter):
    from apps.video_crawler import adapters
    monkeypatch.setattr(adapters, "tao", lambda nen_id: adapter)


def _jobs(uid):
    from platform_core.db import get_session
    from platform_core.models import Job
    gen = get_session(); s = next(gen)
    try:
        return [(j.job_type, j.params) for j in s.query(Job).filter(Job.user_id == uid).all()]
    finally:
        s.close()


def test_trang_danh_dau_nen_tim_kenh_duoc_theo_adapter(env):
    from apps.video_crawler import nen_tang
    client, _ = env
    _login(client, "a@x.com")
    r = client.get("/video-crawler")
    assert r.status_code == 200
    assert 'value="tim_kenh"' in r.text                      # chế độ mới có mặt
    for nen in nen_tang.cac_nen_bat():
        the = re.search(r'<label class="chip-opt" data-nen="%s"[^>]*>' % nen.id, r.text)
        assert the, nen.id
        co = 'data-co-tim-kenh="1"' in the.group(0)
        assert co == features.nen_tim_kenh_duoc(nen.id), nen.id
    # Đo 23/09 (spike L10): đúng bốn nền tìm kênh theo tên được.
    assert {n.id for n in nen_tang.cac_nen_bat() if features.nen_tim_kenh_duoc(n.id)} == {
        "youtube", "bilibili", "douyin", "xiaohongshu"}


def test_tim_kenh_thieu_csrf_bi_tu_choi(env):
    client, _ = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/tim-kenh", data={"nen_tang": "youtube", "tu_khoa": "lofi"})
    assert r.status_code == 400


def test_tim_kenh_tra_the_kenh_anh_qua_proxy(env, monkeypatch):
    client, _ = env
    _login(client, "a@x.com")
    _tiem_adapter(monkeypatch, AdapterGia(ket_qua=[_kenh(0), _kenh(1, so_theo_doi=None)]))
    r = client.post("/video-crawler/tim-kenh",
                    data={"nen_tang": "youtube", "tu_khoa": "lofi girl", "so_luong": "5",
                          "csrf_token": _csrf(client)})
    assert r.status_code == 200
    assert ANH_YT not in r.text                               # URL CDN KHÔNG được nhúng thẳng
    assert "/video-crawler/anh-kenh/" in r.text
    assert "Kênh 0" in r.text and "Kênh 1" in r.text
    the1 = r.text.split("Kênh 1", 1)[1]
    assert ">0<" not in the1.split("</form>")[0]              # số theo dõi trống ⇒ không hiện số 0
    assert "15" in r.text                                     # 15,8 triệu người theo dõi có hiện


def test_the_kenh_co_nut_xem_video_cua_kenh(env, monkeypatch):
    client, _ = env
    _login(client, "a@x.com")
    _tiem_adapter(monkeypatch, AdapterGia(ket_qua=[_kenh(0)]))
    r = client.post("/video-crawler/tim-kenh",
                    data={"nen_tang": "youtube", "tu_khoa": "lofi", "csrf_token": _csrf(client)})
    assert "/video-crawler/trang-kenh" in r.text
    assert _kenh(0).url in r.text


def test_anh_kenh_phuc_vu_qua_proxy_va_ve_cua_nguoi_khac_bi_tu_choi(env, monkeypatch):
    from apps.video_crawler import anh_bia
    client, (ua, _) = env
    anh_bia.xoa_dem()
    monkeypatch.setattr(anh_bia, "_lay_mac_dinh",
                        lambda url, *, toi_da: (b"\x89PNG\r\n\x1a\n" + b"0" * 10, "image/png"))
    ve = features.ky_anh_kenh(ua, "youtube", ANH_YT)
    _login(client, "a@x.com")
    r = client.get(f"/video-crawler/anh-kenh/{ve}")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/")
    assert r.headers.get("x-content-type-options") == "nosniff"
    _login(client, "b@x.com")
    assert client.get(f"/video-crawler/anh-kenh/{ve}").status_code == 404
    assert client.get("/video-crawler/anh-kenh/khong-phai-ve").status_code == 404


def test_anh_kenh_tu_choi_host_ngoai_allowlist(env, monkeypatch):
    from apps.video_crawler import anh_bia
    client, (ua, _) = env
    anh_bia.xoa_dem()
    monkeypatch.setattr(anh_bia, "_lay_mac_dinh", lambda url, *, toi_da: (b"\x89PNG\r\n\x1a\n", "image/png"))
    ve = features.ky_anh_kenh(ua, "youtube", "https://evil.example/a.jpg")
    _login(client, "a@x.com")
    assert client.get(f"/video-crawler/anh-kenh/{ve}").status_code == 404


def test_nen_khong_tim_kenh_duoc_cho_cau_ro_khong_phai_500(env):
    client, _ = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/tim-kenh",
                    data={"nen_tang": "facebook", "tu_khoa": "abc", "csrf_token": _csrf(client)},
                    headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert "link" in r.text.lower()


def test_trang_kenh_hien_tuy_chon_va_nut_mo_tren_nen_tang(env, monkeypatch):
    client, _ = env
    _login(client, "a@x.com")
    _tiem_adapter(monkeypatch, AdapterGia())
    r = client.post("/video-crawler/trang-kenh",
                    data={"nen_tang": "youtube", "dau_vao": URL_KENH_YT, "ten": "Lofi Girl",
                          "csrf_token": _csrf(client)})
    assert r.status_code == 200
    for ten_truong in ("tu_ngay", "den_ngay", "thoi_luong", "so_luong", "khong_trung", "sap_xep"):
        assert f'name="{ten_truong}"' in r.text, ten_truong
    assert 'value="kenh"' in r.text and URL_KENH_YT in r.text
    assert 'max="20"' in r.text
    assert 'rel="noopener noreferrer"' in r.text and 'target="_blank"' in r.text
    # Kiểm GUI 23/09: `outerHTML` ở đây xoá luôn `#vc-ket-qua` ⇒ lượt tìm kênh kế tiếp mất đích swap.
    assert 'hx-target="#vc-ket-qua" hx-swap="innerHTML"' in r.text
    assert 'hx-swap="outerHTML"' not in r.text


def test_trang_kenh_tu_choi_link_ngoai_nen(env, monkeypatch):
    client, _ = env
    _login(client, "a@x.com")
    _tiem_adapter(monkeypatch, AdapterGia())
    r = client.post("/video-crawler/trang-kenh",
                    data={"nen_tang": "youtube", "dau_vao": "https://evil.example/channel/x",
                          "csrf_token": _csrf(client)}, headers={"HX-Request": "true"})
    assert r.status_code == 200
    assert "evil.example" not in r.text


def test_kham_pha_tu_trang_kenh_ghi_tuy_chon_vao_params(env, monkeypatch):
    client, (ua, _) = env
    _login(client, "a@x.com")
    r = client.post("/video-crawler/kham-pha",
                    data={"nen_tang": "youtube", "che_do": "kenh", "dau_vao": URL_KENH_YT,
                          "so_luong": "5", "khong_trung": "1", "thoi_luong": "ngan",
                          "sap_xep": "moi_nhat", "tu_ngay": "2026-01-01",
                          "csrf_token": _csrf(client)})
    assert r.status_code == 200
    jobs = _jobs(ua)
    assert [t for t, _ in jobs] == ["video_crawler.kham_pha"]
    assert jobs[0][1]["tuy_chon"] == {"sap_xep": "moi_nhat", "tu_ngay": "2026-01-01",
                                      "thoi_luong": "ngan"}


def test_ket_qua_xem_truoc_loc_theo_thoi_luong_da_chon(env):
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, Job
    client, (ua, _) = env
    _login(client, "a@x.com")
    gen = get_session(); s = next(gen)
    job = Job(user_id=ua, app_slug="video_crawler", job_type=features.JOB_KHAM_PHA,
              status=JOB_DONE,
              params={"owner_id": ua, "nen_tang": "youtube", "che_do": "kenh", "dau_vao": URL_KENH_YT,
                      "so_luong": 5, "khong_trung": False, "tuy_chon": {"thoi_luong": "ngan"}},
              result={"muc": [{"id": "aaaaaaaaaaa", "tieu_de": "ngan", "thoi_luong_s": 30},
                              {"id": "bbbbbbbbbbb", "tieu_de": "dai", "thoi_luong_s": 3600}]})
    s.add(job); s.commit()
    job_id = job.id
    s.close()
    r = client.get(f"/video-crawler/kham-pha/{job_id}")
    assert r.status_code == 200
    assert "aaaaaaaaaaa" in r.text and "bbbbbbbbbbb" not in r.text
