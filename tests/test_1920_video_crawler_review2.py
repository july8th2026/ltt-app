"""
video_crawler — review code lần 2 (22/09): 1 BLOCKER + 3 MAJOR + 5 MINOR. Mỗi phép kiểm tái hiện đúng một finding.
"""
from __future__ import annotations

import pytest

_NOTE = "6411cf99000000001300b6d9"
_TOK = "CBgeL8Dxd1ZWBhwqRd568gAZ_iwG-9JIf9tnApNmteU2E="
_URL_XHS = f"https://www.xiaohongshu.com/explore/{_NOTE}?xsec_token={_TOK}"
_DNS = lambda host: ["142.250.66.78"]  # noqa: E731


# ── BLOCKER: Xiaohongshu ────────────────────────────────────────────────────

def test_xhs_id_chi_la_note_token_di_theo_url():
    from apps.video_crawler.adapters.xiaohongshu import XiaohongshuAdapter
    it = XiaohongshuAdapter()._sang_item({"id": _NOTE, "title": "T", "webpage_url": _URL_XHS})
    assert it.id == _NOTE                                   # an toàn làm khoá storage (không ':' / '=')
    assert it.url == _URL_XHS


@pytest.mark.parametrize("url_goi,ok", [
    (_URL_XHS, True),
    (f"https://www.xiaohongshu.com/explore/{_NOTE}?xsec_token=CBge%3D%3Dabc_def-ghiJKLmnop", True),   # %-mã hoá
    (f"https://www.xiaohongshu.com/explore/{'f' * 24}?xsec_token={_TOK}", False),       # note khác id
    (f"https://www.xiaohongshu.com/user/profile/abc?xsec_token={_TOK}", False),        # trang người dùng
    (f"https://evil.example/explore/{_NOTE}?xsec_token={_TOK}", False),
    (f"https://www.xiaohongshu.com/explore/{_NOTE}", False),                            # thiếu token
])
def test_xhs_url_chuan_chi_nhan_dung_note_co_token(url_goi, ok):
    from apps.video_crawler.adapters.xiaohongshu import XiaohongshuAdapter
    kq = XiaohongshuAdapter().url_chuan(_NOTE, url_goi)
    assert (kq is not None) is ok
    if ok:
        assert kq.startswith(f"https://www.xiaohongshu.com/explore/{_NOTE}?xsec_token=")


def test_mac_dinh_url_chuan_bo_url_khach_gui():
    from apps.video_crawler.adapters.youtube import YoutubeAdapter
    assert YoutubeAdapter().url_chuan("a" * 11, "https://www.youtube.com/playlist?list=PL") == \
        f"https://www.youtube.com/watch?v={'a' * 11}"


def test_features_giu_url_xhs_hop_le_va_tu_choi_url_thieu_token():
    from apps.video_crawler import features
    p = features.dung_params_tai(owner_id="u1", nen_tang="xiaohongshu", muc=[{"id": _NOTE, "url": _URL_XHS}],
                                 phan_giai=_DNS)
    assert p["muc"][0]["url"] == _URL_XHS
    with pytest.raises(features.LoiDauVao):
        features.dung_params_tai(owner_id="u1", nen_tang="xiaohongshu",
                                 muc=[{"id": _NOTE, "url": f"https://www.xiaohongshu.com/explore/{_NOTE}"}],
                                 phan_giai=_DNS)


def test_cao_het_bo_muc_co_id_khong_an_toan_lam_khoa():
    """Đường "cào hết": mục đi thẳng từ adapter, không qua features ⇒ phải lọc id an toàn cho khoá storage."""
    from apps.video_crawler import jobs
    from apps.video_crawler.adapters.base import CrawlItem, YeuCauCao  # noqa: F401

    class _Ad:
        def kham_pha(self, yc, *, bao_tien_do):
            return [CrawlItem("youtube", "a:b", "u"), CrawlItem("youtube", "a" * 11, "u2")]

    muc, _ = jobs._kham_pha(_Ad(), "youtube", {"che_do": "tu_khoa", "dau_vao": "x", "so_luong": 5}, "u1",
                            lambda p, m: None)
    assert [m.id for m in muc] == ["a" * 11]


# ── MAJOR 2: loi.py tra theo mã, không theo vị trí ───────────────────────────

def test_fragment_403_dung_thong_diep_yt_403():
    from apps.video_crawler.loi import phan_loai
    e = phan_loai("ERROR: fragment 3 not found, HTTP Error 403: Forbidden")
    assert e.ma == "yt_403" and "YouTube" in e.thong_diep


# ── MAJOR 3: proxy ảnh không được vắt kiệt threadpool ────────────────────────

def test_anh_bia_co_bo_nho_dem_khong_tai_lai():
    from apps.video_crawler import anh_bia
    anh_bia.xoa_dem()
    goi = []

    def lay(url, *, toi_da):
        goi.append(url)
        return b"\xff\xd8\xff", "image/jpeg"
    for _ in range(3):
        anh_bia.tai("https://i.ytimg.com/vi/a/hq.jpg", nen_tang="youtube", phan_giai=_DNS, lay=lay)
    assert len(goi) == 1


def test_anh_bia_qua_tai_thi_tu_choi_ngay(monkeypatch):
    from apps.video_crawler import anh_bia
    anh_bia.xoa_dem()
    monkeypatch.setattr(anh_bia, "_SO_LUONG_DONG_THOI", anh_bia.threading.BoundedSemaphore(1))
    anh_bia._SO_LUONG_DONG_THOI.acquire()
    try:
        with pytest.raises(anh_bia.AnhKhongHopLe):
            anh_bia.tai("https://i.ytimg.com/vi/b/hq.jpg", nen_tang="youtube", phan_giai=_DNS,
                        lay=lambda url, *, toi_da: (b"x", "image/jpeg"), cho_s=0.01)
    finally:
        anh_bia._SO_LUONG_DONG_THOI.release()


# ── MAJOR 4 + MINOR 5/6/8: phiên ────────────────────────────────────────────

@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'r2.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-1")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _ck(*dong):
    return "# Netscape HTTP Cookie File\n" + "\n".join(dong) + "\n"


def test_phien_giai_ma_hong_thi_bao_ro_khong_coi_la_co_phien(db, monkeypatch):
    from apps.video_crawler import features, phien
    phien.luu(db, owner_id="u1", nen_tang="youtube",
              cookies_txt=_ck(".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\tx1"))
    db.commit()
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-2")              # xoay khoá
    (row,) = phien.danh_sach(db, "u1")
    assert phien.hop_le(row) is False
    import dataclasses

    from apps.video_crawler import nen_tang
    gia = dataclasses.replace(nen_tang.lay("youtube"), che_do_can_dang_nhap=frozenset({"kenh"}))
    monkeypatch.setattr(nen_tang, "lay_nen_bat", lambda i: gia)
    with pytest.raises(features.LoiDauVao, match="hỏng"):
        features.dung_params_kham_pha(owner_id="u1", nen_tang="youtube", che_do="kenh", dau_vao="@a",
                                      so_luong=1, khong_trung=False, phan_giai=_DNS, db=db)


def test_han_phien_theo_cookie_xac_thuc_va_khong_vo_khi_so_qua_lon(db):
    from apps.video_crawler import phien
    row = phien.luu(db, owner_id="u1", nen_tang="youtube", cookies_txt=_ck(
        ".youtube.com\tTRUE\t/\tTRUE\t1600000000\tVISITOR\tv",            # cookie phụ hết hạn sớm
        ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\tx",
        ".youtube.com\tTRUE\t/\tTRUE\t99999999999999999999\tLOGIN_INFO\ty"))
    assert row.het_han_luc is not None and row.het_han_luc.year == 2030   # theo SAPISID, không theo VISITOR


def test_tep_co_bom_khong_mat_dong_dau(db):
    from apps.video_crawler import phien
    row = phien.luu(db, owner_id="u1", nen_tang="youtube",
                    cookies_txt="﻿.youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\tx")
    assert row.so_cookie == 1


def test_don_thu_muc_cookie_tam_cu(tmp_path):
    """MINOR 7: `_het_gio` giết tiến trình ⇒ thư mục cookie tạm còn lại. Dọn những thư mục cũ khi mở phiên mới."""
    import os
    import time

    from apps.video_crawler import phien
    cu = tmp_path / "vc_phien_cu"
    cu.mkdir()
    (cu / "cookies_youtube.txt").write_text("bi mat", encoding="utf-8")
    moc = time.time() - 4 * 3600
    os.utime(cu, (moc, moc))
    moi = tmp_path / "vc_phien_moi"
    moi.mkdir()
    phien.don_tam_cu(tmp_path, tuoi_s=3 * 3600)
    assert not cu.exists() and moi.exists()
