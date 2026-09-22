"""Adapter YouTube qua yt-dlp (spec §11, §18, §21).

Port từ donor `D:\\Viral\\resources\\app-src\\tai_ytdlp.py` (Y). Cố ý KHÔNG chép của donor:
`ignoreerrors` (nuốt huỷ, Y:2023), `nocheckcertificate` (Y:2024), cookie (Y:2042-2047),
`remote_components` (Y:2066), `download_archive` (Y:2038) và `outtmpl` theo người dùng.
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.
"""
from __future__ import annotations

import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from apps.video_crawler.adapters.base import BaoTienDo, CrawlItem, LoiCao, TepTai, YeuCauCao
from apps.video_crawler.loi import phan_loai

# Các tab hợp lệ của trang kênh YouTube (URL kết thúc bằng tab nào thì giữ nguyên) — Y:228.
_YT_TABS = ("videos", "shorts", "streams", "live", "featured", "playlists", "community", "posts")

# Y:1235-1249 `_CODEC_HONG` + `_CHUOI_FORMAT()` với TAI_CODEC=tot (mặc định donor).
_CODEC_HONG = ("hev", "hvc", "h265", "vvc", "bytevc")
_H264 = ("bv*[vcodec~='^(avc1|h264)']+ba[ext=m4a]/"
         "b[vcodec~='^(avc1|h264)']/"
         "bv*+ba/b[vcodec!=none]")
_LOC = "".join("[vcodec!*=%s]" % c for c in _CODEC_HONG)
CHUOI_FORMAT = "bv*%s+ba/b%s/%s" % (_LOC, _LOC, _H264)

#: IE_NAME (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Không generic,
#: không extractor cần đăng nhập (history/subscriptions/watchlater...), không web.archive.
EXTRACTOR_CHO_PHEP = (
    "youtube", "youtube:tab", "youtube:playlist", "youtube:search", "youtubeytbe",
    "youtube:clip", "youtube:truncated_id", "youtube:truncated_url",
)

_DUOI_VIDEO = (".mp4", ".mkv", ".webm", ".mov")
_KY_TU_CAM = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]+')


def chuan_hoa_kenh_youtube(s):
    """Kênh YouTube -> URL tab '/videos' (port nguyên Y:231-252).
    Giữ nguyên link 1 video/short hoặc tab đã chỉ định."""
    s = (s or "").strip()
    if not s:
        return s
    low = s.lower()
    if "watch?v=" in low or "youtu.be/" in low or re.search(r"/shorts/[\w-]+", low):
        return s
    if not low.startswith("http") and "/" not in s:
        h = s if s.startswith("@") else "@" + s
        return f"https://www.youtube.com/{h}/videos"
    if not low.startswith("http"):
        s = "https://" + s
    base_url = s.split("?")[0].split("#")[0].rstrip("/")
    if base_url.rsplit("/", 1)[-1].lower() in _YT_TABS:
        return base_url
    return base_url + "/videos"


def tuy_chon(thu_muc: Path | None = None, *, progress_hooks: list | None = None,
             postprocessor_hooks: list | None = None) -> dict[str, Any]:
    """Dựng tuỳ chọn yt-dlp (thuần). `thu_muc` có ⇒ tuỳ chọn tải một mục vào đó."""
    o: dict[str, Any] = {
        "format": CHUOI_FORMAT,                       # Y:2019
        "format_sort": ["res", "br"],                 # Y:2020-2021
        "merge_output_format": "mp4",                 # Y:2022
        "quiet": True, "no_warnings": True, "noprogress": True,   # Y:2025-2027
        "retries": 3,                                 # Y:2028
        "concurrent_fragment_downloads": 4,           # Y:2030
        "enable_file_urls": False,                    # Y:2031
        "extractor_args": {"youtube": {"player_client": ["web_embedded", "default"]}},  # Y:2081-2083
        "sleep_interval_requests": 1.0,               # Y:2090-2095
        "allowed_extractors": list(EXTRACTOR_CHO_PHEP),   # spec §21 (LTT thêm)
    }
    if thu_muc is not None:
        o["outtmpl"] = str(Path(thu_muc) / "%(id)s.%(ext)s")
        o["noplaylist"] = True
    if progress_hooks:
        o["progress_hooks"] = list(progress_hooks)
    if postprocessor_hooks:
        o["postprocessor_hooks"] = list(postprocessor_hooks)
    return o


@lru_cache(maxsize=1)
def _lop_huy() -> type:
    """Lớp con DownloadCancelled — loại duy nhất (cùng CookieLoadError) yt-dlp không nuốt."""
    from yt_dlp.utils import DownloadCancelled

    class HuyTuBaoTienDo(DownloadCancelled):
        msg = "Huỷ theo yêu cầu"

    return HuyTuBaoTienDo


def _ten_sach(tieu_de: str) -> str:
    """Donor `an_toan` (Y:194-198): bỏ ký tự cấm Windows + ký tự điều khiển, gộp khoảng trắng."""
    t = re.sub(r"\s+", " ", _KY_TU_CAM.sub(" ", tieu_de or "")).strip()
    return t[:80].rstrip(". ")


def _anh_bia(e: dict) -> str:
    if e.get("thumbnail"):
        return str(e["thumbnail"])
    thumbs = [t for t in (e.get("thumbnails") or []) if isinstance(t, dict) and t.get("url")]
    return str(thumbs[-1]["url"]) if thumbs else ""


def _sang_item(e: dict) -> CrawlItem:
    vid = str(e["id"])
    dur = e.get("duration")
    return CrawlItem(
        nen_tang="youtube", id=vid, url=f"https://www.youtube.com/watch?v={vid}",
        tieu_de=str(e.get("title") or ""),
        tac_gia=str(e.get("channel") or e.get("uploader") or ""),
        thoi_luong_s=int(dur) if isinstance(dur, (int, float)) else None,
        anh_bia=_anh_bia(e),
    )


class YoutubeAdapter:
    nen_tang = "youtube"

    def __init__(self, ydl_factory: Callable[[dict], Any] | None = None):
        self._ydl_factory = ydl_factory

    def _tao(self, opts: dict):
        if self._ydl_factory is None:
            import yt_dlp
            return yt_dlp.YoutubeDL(opts)
        return self._ydl_factory(opts)

    # ------------------------------------------------------------ khám phá
    def kham_pha(self, yeu_cau: YeuCauCao, *, bao_tien_do: BaoTienDo) -> list[CrawlItem]:
        from yt_dlp.utils import DownloadError

        n = int(yeu_cau.so_luong)
        opts = tuy_chon()
        opts.update(extract_flat="in_playlist", skip_download=True)
        che_do, vao = yeu_cau.che_do, yeu_cau.dau_vao.strip()
        if che_do == "tu_khoa":
            url = f"ytsearch{n}:{vao}"                # Y:2169
            opts["playlistend"] = n
        elif che_do == "kenh":
            url = chuan_hoa_kenh_youtube(vao)
            opts["playlistend"] = n
        elif che_do == "bo":
            url = vao
            opts["playlistend"] = n
        else:                                         # link: một mục
            url, n = vao, 1
            opts["noplaylist"] = True
        bao_tien_do(0, "đang tìm video")
        try:
            with self._tao(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except DownloadError as e:
            raise phan_loai(str(e)) from None
        info = info or {}
        entries = info.get("entries") if "entries" in info else [info]
        ra: list[CrawlItem] = []
        for e in entries or []:
            if len(ra) >= n:
                break
            if not isinstance(e, dict) or not e.get("id"):
                continue
            if e.get("ie_key") not in (None, "Youtube"):  # tab/playlist lồng, không phải video
                continue
            ra.append(_sang_item(e))
        bao_tien_do(100, f"tìm thấy {len(ra)} video")
        return ra

    # ------------------------------------------------------------ tải
    def tai(self, item: CrawlItem, thu_muc: Path, *, bao_tien_do: BaoTienDo) -> TepTai:
        from yt_dlp.utils import DownloadCancelled, DownloadError

        thu_muc = Path(thu_muc)
        huy = _lop_huy()
        giu: list[BaseException] = []     # ngoại lệ gốc của bao_tien_do
        tep_hook: list[str] = []
        cuoi = {"pct": None, "t": 0.0}

        def _bao(pct: int, msg: str) -> None:
            if giu:
                raise huy()
            try:
                bao_tien_do(pct, msg)
            except BaseException as e:  # noqa: BLE001 — mọi thứ bao_tien_do ném đều là huỷ
                giu.append(e)
                raise huy() from e

        def hook(d: dict) -> None:
            if giu:
                raise huy()
            st = d.get("status")
            if st == "finished" and d.get("filename"):
                tep_hook.append(d["filename"])
                return
            if st != "downloading":
                return
            tong = d.get("total_bytes") or d.get("total_bytes_estimate")
            xong = d.get("downloaded_bytes")
            if not tong or xong is None:
                return
            pct = max(0, min(98, int(xong * 100 / tong)))
            now = time.monotonic()
            if pct != cuoi["pct"] or now - cuoi["t"] >= 5:
                cuoi["pct"], cuoi["t"] = pct, now
                _bao(pct, "đang tải")

        def pp_hook(d: dict) -> None:
            if giu:
                raise huy()
            fp = (d.get("info_dict") or {}).get("filepath")
            if fp:
                tep_hook.append(fp)
            if d.get("status") == "started":
                _bao(99, "đang ghép")

        opts = tuy_chon(thu_muc, progress_hooks=[hook], postprocessor_hooks=[pp_hook])
        try:
            with self._tao(opts) as ydl:
                ydl.download([item.url])
        except DownloadCancelled:
            if giu:
                raise giu[0] from None
            raise
        except DownloadError as e:
            if giu:
                raise giu[0] from None
            raise phan_loai(str(e)) from None
        if giu:
            raise giu[0]

        path = self._tim_tep(item.id, thu_muc, tep_hook)
        if path is None:
            raise LoiCao("khong_thay_tep", "Tải xong nhưng không tìm thấy tệp video. Vui lòng thử lại.",
                         tam_thoi=True)
        ten = _ten_sach(item.tieu_de) or item.id
        return TepTai(duong_dan=path, kich_thuoc=path.stat().st_size,
                      ten_hien_thi=f"{ten} [{item.id}]{path.suffix}")

    @staticmethod
    def _tim_tep(vid: str, thu_muc: Path, tep_hook: list[str]) -> Path | None:
        for f in reversed(tep_hook):                  # hook sau cùng (MoveFiles/Merger) thắng
            p = Path(f)
            if p.is_file() and p.stem == vid and p.suffix.lower() in _DUOI_VIDEO:
                return p
        if not thu_muc.is_dir():
            return None
        for p in sorted(thu_muc.iterdir()):
            if p.is_file() and p.stem == vid and p.suffix.lower() in _DUOI_VIDEO:
                return p
        return None
