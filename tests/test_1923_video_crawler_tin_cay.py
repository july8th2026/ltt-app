"""video_crawler — độ tin cậy yt-dlp (lane L3 tin cậy, PLAN_MVP §C, nguồn N5/N7/N8). Không chạm mạng.

(a) YouTube EJS: bật JS runtime `node` qua tuỳ chọn `js_runtimes` (yt-dlp 2026.03.17 YoutubeDL.py:538-544,
    735-736; mặc định chỉ `deno`). KHÔNG `remote_components` (:545-549 — tải mã JS từ npm/GitHub lúc chạy).
    Gói `yt-dlp-ejs` là tuỳ chọn: thiếu gói thì yt-dlp chỉ cảnh báo "n challenge solving failed" (smoke 22/09).
(b) Nhịp giữa các lượt TẢI: `sleep_interval`/`max_sleep_interval` 5–10 s ngẫu nhiên (downloader/common.py:461-475,
    donor Y:2096-2104, wiki yt-dlp) — chỉ tuỳ chọn tải, không áp khi khám phá; `sleep_interval_requests` giữ.
(c) "Cannot parse data" / "Unexpected response from webpage request" (facebook/tiktok, N8) ⇒ `trich_xuat_hong`,
    tạm thời (features.SO_LAN_THU = 2 ⇒ đúng một lượt thử lại).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yt_dlp

from apps.video_crawler.adapters._ytdlp import YtdlpAdapter
from apps.video_crawler.adapters.base import CrawlItem, YeuCauCao
from apps.video_crawler.adapters.youtube import YoutubeAdapter, tuy_chon
from apps.video_crawler.loi import phan_loai


class _Nen(YtdlpAdapter):
    nen_tang = "gia"
    allowed_extractors = ("gia",)

    def url_video(self, id):
        return f"https://gia.test/v/{id}"

    def id_hop_le(self, id):
        return isinstance(id, str) and id.isdigit()

    def url_kham_pha(self, che_do, dau_vao, n):
        return dau_vao


class _YDL:
    def __init__(self, opts, tao):
        self.params = opts
        tao.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=True):
        return {"entries": []}

    def download(self, urls):
        d = Path(self.params["outtmpl"]).parent
        (d / "123.mp4").write_bytes(b"x")
        return 0


def _chay(adapter_cls, tmp_path):
    tao: list[_YDL] = []
    a = adapter_cls(lambda o: _YDL(o, tao))
    id_ = "123" if adapter_cls is _Nen else "abcdefghijk"
    if adapter_cls is YoutubeAdapter:
        (tmp_path / f"{id_}.mp4").write_bytes(b"x")
    a.kham_pha(YeuCauCao(a.nen_tang, "link", a.url_video(id_), 1), bao_tien_do=lambda p, m: None)
    a.tai(CrawlItem(a.nen_tang, id_, a.url_video(id_)), tmp_path, bao_tien_do=lambda p, m: None)
    return tao[0].params, tao[1].params          # (khám phá, tải)


# ---------------------------------------------------------------- (a) EJS / node
def test_youtube_bat_node_ca_kham_pha_va_tai(tmp_path):
    assert tuy_chon()["js_runtimes"] == {"node": {}}
    assert tuy_chon(thu_muc=tmp_path)["js_runtimes"] == {"node": {}}


@pytest.mark.parametrize("thu_muc", [None, Path("x")])
def test_khong_bao_gio_remote_components(thu_muc):
    assert "remote_components" not in tuy_chon(thu_muc)
    assert "remote_components" not in _Nen.tuy_chon_goc(thu_muc)


def test_nen_khac_khong_dat_js_runtimes():
    """Chỉ extractor YouTube giải JS challenge; nền khác giữ mặc định của yt-dlp."""
    assert "js_runtimes" not in _Nen.tuy_chon_goc()


def test_js_runtimes_moi_lan_la_ban_sao():
    """yt-dlp sửa `js_runtimes` tại chỗ (`_clean_js_runtimes` pop runtime lạ) ⇒ không được dùng chung ClassVar."""
    a, b = tuy_chon(), tuy_chon()
    assert a["js_runtimes"] is not b["js_runtimes"]
    assert a["js_runtimes"]["node"] is not YoutubeAdapter.js_runtimes["node"]


def test_youtubedl_that_nhan_node_khong_canh_bao():
    canh_bao: list[str] = []

    class Log:
        def debug(self, m):
            pass

        info = debug

        def warning(self, m):
            canh_bao.append(m)

        def error(self, m):
            canh_bao.append(m)

    with yt_dlp.YoutubeDL({**tuy_chon(), "logger": Log()}) as y:
        assert set(y.params["js_runtimes"]) == {"node"}
        assert not y.params["remote_components"]
    assert not any("JavaScript runtime" in m for m in canh_bao)


def test_thieu_goi_yt_dlp_ejs_van_chay(monkeypatch):
    """Không import `yt_dlp_ejs` ở đâu cả: thiếu gói ⇒ dựng tuỳ chọn + YoutubeDL vẫn chạy."""
    monkeypatch.setitem(sys.modules, "yt_dlp_ejs", None)       # import yt_dlp_ejs ⇒ ImportError
    with yt_dlp.YoutubeDL(tuy_chon()) as y:
        assert "node" in y.params["js_runtimes"]


# ---------------------------------------------------------------- (b) nhịp giữa các lượt tải
# Điều phối đổi thiết kế khi gộp W1: nghỉ 5–10 s GIỮA các mục ở `jobs._tai_voi` (tests/test_1931), không dùng
# yt-dlp `sleep_interval` (nghỉ trước MỖI tệp, cả video đầu và cả luồng hình + tiếng ⇒ 7,6 s → 24 s).

# ---------------------------------------------------------------- (c) extractor hỏng
@pytest.mark.parametrize("tho", [
    "ERROR: [facebook] 647537299265662: Cannot parse data; please report this issue on "
    "https://github.com/yt-dlp/yt-dlp/issues?q= , filling out the appropriate issue template. "
    "Confirm you are on the latest version using  yt-dlp -U",
    "ERROR: [TikTok] 7123456789012345678: Unexpected response from webpage request; please report this issue on "
    "https://github.com/yt-dlp/yt-dlp/issues?q= , filling out the appropriate issue template.",
    "ERROR: [tiktok:user] private_sign_in: Unexpected response from webpage request",
])
def test_extractor_hong_la_tam_thoi_co_ma_rieng(tho):
    e = phan_loai(tho)
    assert e.ma == "trich_xuat_hong"
    assert e.tam_thoi is True
    assert "cấu trúc" in e.thong_diep and "chờ cập nhật" in e.thong_diep


def test_extractor_hong_chi_mot_luot_thu_lai():
    from apps.video_crawler.features import SO_LAN_THU
    assert SO_LAN_THU == 2
