"""
video_crawler — dùng phiên đăng nhập khi cào (đợt B1; kho phiên ở test_1908).

Mệnh đề chốt:
- adapter nhận TỆP cookie qua thuộc tính instance; yt-dlp nhận `cookiefile`; không cookie ⇒ không có khoá đó;
- nền cấm cookie khi tải (TikTok: cookie đăng nhập làm tải trả 403, donor `Y:1734-1741`) ⇒ tải không gửi cookie;
- handler mở phiên của ĐÚNG chủ job, tệp tạm bị xoá khi job xong, cookie không lọt vào result/params/sự kiện;
- chế độ cần đăng nhập mà chưa có phiên ⇒ từ chối có tên ở cửa vào (không để job chạy rồi hỏng).
"""
from __future__ import annotations

import pytest

from apps.video_crawler.adapters.base import CrawlItem, TepTai, YeuCauCao

_BI_MAT = "sessionid-bi-mat-abcdef0123456789"
_COOKIES = ("# Netscape HTTP Cookie File\n"
            f".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSAPISID\t{_BI_MAT}\n")
_A = "a" * 11
_DNS = lambda host: ["142.250.66.78"]  # noqa: E731


class _YdlGhi:
    """YoutubeDL giả ghi lại tuỳ chọn nhận được."""
    lan_goi: list = []

    def __init__(self, opts):
        _YdlGhi.lan_goi.append(dict(opts))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        return {"entries": [{"id": _A, "title": "T"}]}


def test_adapter_gui_cookiefile_khi_co_phien():
    from apps.video_crawler.adapters.youtube import YoutubeAdapter
    _YdlGhi.lan_goi = []
    ad = YoutubeAdapter(ydl_factory=_YdlGhi)
    ad.kham_pha(YeuCauCao("youtube", "tu_khoa", "meo", 1), bao_tien_do=lambda p, m: None)
    assert "cookiefile" not in _YdlGhi.lan_goi[-1]
    ad.tep_cookie = "C:/tmp/job/cookies_youtube.txt"
    ad.kham_pha(YeuCauCao("youtube", "tu_khoa", "meo", 1), bao_tien_do=lambda p, m: None)
    assert _YdlGhi.lan_goi[-1]["cookiefile"] == "C:/tmp/job/cookies_youtube.txt"


def test_nen_cam_cookie_khi_tai_thi_khong_gui():
    from apps.video_crawler.adapters._ytdlp import YtdlpAdapter
    from apps.video_crawler.adapters.youtube import YoutubeAdapter

    class _KhongCookieKhiTai(YoutubeAdapter):
        cookie_khi_tai = False

    assert YtdlpAdapter.cookie_khi_tai is True
    ad = _KhongCookieKhiTai(ydl_factory=_YdlGhi)
    ad.tep_cookie = "C:/x/cookies.txt"
    opts = ad._them_chung(ad.tuy_chon_goc(), _TrangThaiGia(), ghi_tu_choi=True)       # đường tải
    assert "cookiefile" not in opts
    opts = ad._them_chung(ad.tuy_chon_goc(), _TrangThaiGia(), ghi_tu_choi=False)      # đường khám phá
    assert opts["cookiefile"] == "C:/x/cookies.txt"


class _TrangThaiGia:
    def ghi_tu_choi(self, ma):
        pass


# ── handler + phiên ──────────────────────────────────────────────────────────

@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'b1.db').as_posix()}")
    monkeypatch.setenv("LTT_TOKEN_ENCRYPTION_KEY", "khoa-test-b1")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    from platform_core.storage import LocalStorage, set_storage
    from tests.conftest import bao_dam_user
    set_storage(LocalStorage(str(tmp_path / "store")))
    gen = dbmod.get_session(); s = next(gen)
    for uid in ("u1", "u2"):
        bao_dam_user(s, uid)
        credit.nap(s, uid, 100)
    s.commit()
    try:
        yield s
    finally:
        s.close(); set_storage(None); dbmod.reset_engine()


class _AdapterNhinCookie:
    nen_tang = "youtube"
    thay: list = []

    def __init__(self):
        self.tep_cookie = None

    def _ghi(self):
        from pathlib import Path
        noi = Path(self.tep_cookie).read_text(encoding="utf-8") if self.tep_cookie else None
        _AdapterNhinCookie.thay.append((self.tep_cookie, noi))

    def kham_pha(self, yc, *, bao_tien_do):
        self._ghi()
        return [CrawlItem("youtube", _A, f"https://www.youtube.com/watch?v={_A}", "T")]

    def tai(self, item, thu_muc, *, bao_tien_do):
        self._ghi()
        p = thu_muc / f"{item.id}.mp4"
        p.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        return TepTai(p, p.stat().st_size, "T.mp4")


def _chay_tai(db, owner, monkeypatch):
    from apps.video_crawler import features
    import apps.video_crawler.jobs as vc_jobs
    from platform_core.job_runner import _chay_mot_job
    from platform_core.models import Job
    ad = _AdapterNhinCookie()
    monkeypatch.setattr(vc_jobs, "_adapter", lambda nen: ad)
    p = features.dung_params_tai(owner_id=owner, nen_tang="youtube", muc=[{"id": _A}], phan_giai=_DNS)
    job = features.nop(db, owner_id=owner, job_type="video_crawler.tai", params=p)
    db.commit()
    assert _chay_mot_job("w-b1") is True
    db.expire_all()
    return db.get(Job, job.id)


def test_handler_dung_phien_cua_dung_chu_va_xoa_tep_sau_job(db, monkeypatch):
    from pathlib import Path

    from apps.video_crawler import phien
    from platform_core import job_events
    phien.luu(db, owner_id="u1", nen_tang="youtube", cookies_txt=_COOKIES)
    db.commit()
    _AdapterNhinCookie.thay = []
    job = _chay_tai(db, "u1", monkeypatch)
    assert job.status == "done"
    duong, noi = _AdapterNhinCookie.thay[-1]
    assert duong and _BI_MAT in noi
    assert not Path(duong).exists()                                         # tệp tạm đã xoá
    lo = str(job.result) + str(job.params) + " ".join(
        e.public_message + str(e.details) for e in job_events.timeline(db, job.id, include_internal=True))
    assert _BI_MAT not in lo and duong not in lo


def test_user_khac_khong_dung_duoc_phien(db, monkeypatch):
    from apps.video_crawler import phien
    phien.luu(db, owner_id="u1", nen_tang="youtube", cookies_txt=_COOKIES)
    db.commit()
    _AdapterNhinCookie.thay = []
    _chay_tai(db, "u2", monkeypatch)
    assert _AdapterNhinCookie.thay[-1] == (None, None)


def test_che_do_can_dang_nhap_ma_chua_co_phien_bi_tu_choi_o_cua_vao(db, monkeypatch):
    from apps.video_crawler import features, nen_tang
    yt = nen_tang.lay("youtube")
    import dataclasses
    gia = dataclasses.replace(yt, che_do_can_dang_nhap=frozenset({"kenh"}))
    monkeypatch.setattr(nen_tang, "lay_nen_bat", lambda i: gia)
    with pytest.raises(features.LoiDauVao, match="đăng nhập"):
        features.dung_params_kham_pha(owner_id="u1", nen_tang="youtube", che_do="kenh", dau_vao="@abc",
                                      so_luong=1, khong_trung=False, phan_giai=_DNS, db=db)
    from apps.video_crawler import phien
    phien.luu(db, owner_id="u1", nen_tang="youtube", cookies_txt=_COOKIES)
    db.commit()
    p = features.dung_params_kham_pha(owner_id="u1", nen_tang="youtube", che_do="kenh", dau_vao="@abc",
                                      so_luong=1, khong_trung=False, phan_giai=_DNS, db=db)
    assert p["che_do"] == "kenh"
