"""
video_crawler — proxy ảnh bìa xem trước (SO_LOI L10).

Kiểm GUI 22/09: CSP nền tảng (`img-src 'self' …`) chặn ảnh bìa `i.ytimg.com` — và chặn là ĐÚNG (không lộ IP khách cho
bên thứ ba). Donor hiện ảnh bìa trong "Xem trước & chọn" (`H:9336`), nên app phục vụ ảnh qua route của chính nó:
- chỉ host thuộc CDN ảnh của các nền (allowlist) + chặn IP nội bộ (an_toan_url);
- không theo redirect, timeout ngắn, tối đa 2 MB, chỉ `image/*`;
- chỉ ảnh của mục trong kết quả xem trước CỦA CHÍNH người dùng (route kiểm chủ).
Tải ảnh được TIÊM để test không đọc mạng.
"""
from __future__ import annotations

import pytest

from apps.video_crawler import anh_bia

_DNS = lambda host: ["142.250.66.78"]  # noqa: E731


def _lay_gia(noi_dung=b"\x89PNG\r\n\x1a\n...", loai="image/jpeg"):
    goi = []

    def lay(url, *, toi_da):
        goi.append(url)
        return noi_dung, loai
    lay.goi = goi
    return lay


def test_anh_cdn_hop_le_duoc_tra_ve():
    lay = _lay_gia()
    du_lieu, loai = anh_bia.tai("https://i.ytimg.com/vi/abc/hq720.jpg", phan_giai=_DNS, lay=lay)
    assert loai == "image/jpeg" and du_lieu.startswith(b"\x89PNG")
    assert lay.goi == ["https://i.ytimg.com/vi/abc/hq720.jpg"]


@pytest.mark.parametrize("url", [
    "https://evil.example/a.jpg",
    "http://127.0.0.1/a.jpg",
    "https://i.ytimg.com.evil.io/a.jpg",
    "file:///C:/Windows/win.ini",
    "",
])
def test_host_ngoai_allowlist_bi_tu_choi_khong_goi_mang(url):
    lay = _lay_gia()
    with pytest.raises(anh_bia.AnhKhongHopLe):
        anh_bia.tai(url, phan_giai=_DNS, lay=lay)
    assert lay.goi == []


def test_noi_dung_khong_phai_anh_bi_tu_choi():
    with pytest.raises(anh_bia.AnhKhongHopLe):
        anh_bia.tai("https://i.ytimg.com/vi/abc/x.jpg", phan_giai=_DNS, lay=_lay_gia(b"<html>", "text/html"))


def test_moi_nen_bat_co_cdn_anh():
    """Nền mới bật mà quên khai CDN ảnh ⇒ xem trước của nền đó mất ảnh không ai hay."""
    from apps.video_crawler import nen_tang
    for n in nen_tang.cac_nen_bat():
        assert anh_bia.CDN_ANH.get(n.id), n.id


def test_anh_bia_cua_chi_lay_tu_xem_truoc_cua_chu(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'a.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.models import JOB_DONE, Job
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    try:
        j = Job(user_id="u1", app_slug="video_crawler", job_type="video_crawler.kham_pha",
                params={"nen_tang": "youtube"}, status=JOB_DONE,
                result={"muc": [{"id": "a" * 11, "anh_bia": "https://i.ytimg.com/vi/a/hq.jpg"}]})
        db.add(j); db.commit()
        assert anh_bia.url_cua(db, owner_id="u1", job_id=j.id, chi_so=0) == ("youtube", "https://i.ytimg.com/vi/a/hq.jpg")
        assert anh_bia.url_cua(db, owner_id="u2", job_id=j.id, chi_so=0) is None
        assert anh_bia.url_cua(db, owner_id="u1", job_id=j.id, chi_so=5) is None
    finally:
        db.close(); dbmod.reset_engine()


def test_host_phai_thuoc_cdn_cua_dung_nen():
    lay = _lay_gia()
    with pytest.raises(anh_bia.AnhKhongHopLe):
        anh_bia.tai("https://i.ytimg.com/vi/abc/hq720.jpg", nen_tang="tiktok", phan_giai=_DNS, lay=lay)
