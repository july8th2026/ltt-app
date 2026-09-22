"""Nền yt-dlp dùng chung cho mọi adapter nền tảng (spec §11, §18, §21).

Lớp con chỉ cấp cấu hình nền: `nen_tang`, `allowed_extractors`, `extractor_args`, `ie_key_video`,
`impersonate`, `url_video(id)`, `id_hop_le(id)`, `url_kham_pha(che_do, dau_vao, n)`.
Mọi thứ còn lại (tuỳ chọn cốt lõi, hook tiến độ + nhịp tim, huỷ, lọc trực tiếp/quá dài/quá lớn,
tìm tệp cuối, tên hiển thị, phân loại DownloadError) nằm ở đây.

Nguồn yt-dlp 2026.03.17:
- chỉ `DownloadCancelled`/`CookieLoadError` thoát khỏi hook (YoutubeDL.py:1699, 1717-1721, 3629-3631) ⇒ huỷ đi bằng
  lớp con DownloadCancelled, và `ignoreerrors=False` tường minh.
- `match_filter(info_dict, *, incomplete) -> Optional[str]` (:453-463, gọi ở :1593); mục bị lọc bị bỏ trong im lặng
  (:3307 `process_info` return).
- `max_filesize`: HttpFD chỉ `to_screen("File is larger than max-filesize ...")` rồi `return False`
  (downloader/http.py:219-227); `to_screen` chuyển sang `logger.debug` khi có logger (:992-996).
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.
"""
from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, ClassVar, Iterator

from platform_core.i18n import N_
from platform_core.i18n import _ as _t

from apps.video_crawler.adapters.base import BaoTienDo, CrawlItem, LoiCao, TepTai, YeuCauCao
from apps.video_crawler.loi import phan_loai

# Y:1235-1249 `_CODEC_HONG` + `_CHUOI_FORMAT()` với TAI_CODEC=tot (mặc định donor).
_CODEC_HONG = ("hev", "hvc", "h265", "vvc", "bytevc")
_H264 = ("bv*[vcodec~='^(avc1|h264)']+ba[ext=m4a]/"
         "b[vcodec~='^(avc1|h264)']/"
         "bv*+ba/b[vcodec!=none]")
_LOC = "".join("[vcodec!*=%s]" % c for c in _CODEC_HONG)
CHUOI_FORMAT = "bv*%s+ba/b%s/%s" % (_LOC, _LOC, _H264)

#: Chu kỳ nhịp tim (giây) trong lúc yt-dlp trích xuất/ghép mà không gọi hook nào. Spec §18: ≥ 1 lần/60 s.
CHU_KY_NHIP = 20.0
TEN_LUONG_NHIP = "video-crawler-nhip"
MAX_FILESIZE_MAC_DINH = 4 * 1024 ** 3
THOI_LUONG_TOI_DA_MAC_DINH = 3 * 3600

#: live_status yt-dlp chưa tải được như một tệp (YoutubeDL.py:2755-2772). `was_live` là VOD bình thường ⇒ cho qua.
_TRUC_TIEP = frozenset({"is_live", "is_upcoming", "post_live"})
_TU_CHOI = {
    "khong_ho_tro_truc_tiep": N_("Video đang phát trực tiếp hoặc chưa công chiếu, chưa tải được."),
    "qua_dai": N_("Video dài quá giới hạn cho phép."),
    "qua_lon": N_("Tệp video vượt quá dung lượng cho phép."),
}
_DAU_QUA_LON = "larger than max-filesize"

_DUOI_VIDEO = (".mp4", ".mkv", ".webm", ".mov")
_KY_TU_CAM = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]+')


@lru_cache(maxsize=1)
def lop_huy() -> type:
    """Lớp con DownloadCancelled — loại duy nhất (cùng CookieLoadError) yt-dlp không nuốt."""
    from yt_dlp.utils import DownloadCancelled

    class HuyTuBaoTienDo(DownloadCancelled):
        msg = N_("Huỷ theo yêu cầu")

    return HuyTuBaoTienDo


def ten_sach(tieu_de: str) -> str:
    """Donor `an_toan` (Y:194-198): bỏ ký tự cấm Windows + ký tự điều khiển, gộp khoảng trắng."""
    t = re.sub(r"\s+", " ", _KY_TU_CAM.sub(" ", tieu_de or "")).strip()
    return t[:80].rstrip(". ")


def _anh_bia(e: dict) -> str:
    if e.get("thumbnail"):
        return str(e["thumbnail"])
    thumbs = [t for t in (e.get("thumbnails") or []) if isinstance(t, dict) and t.get("url")]
    return str(thumbs[-1]["url"]) if thumbs else ""


def tim_tep(vid: str, thu_muc: Path, tep_hook: list[str]) -> Path | None:
    """Tệp video cuối của `vid`: hook sau cùng (MoveFiles/Merger) thắng, rồi mới quét thư mục."""
    for f in reversed(tep_hook):
        p = Path(f)
        if p.is_file() and p.stem == vid and p.suffix.lower() in _DUOI_VIDEO:
            return p
    if not thu_muc.is_dir():
        return None
    cuoi = [p for p in sorted(thu_muc.iterdir())
            if p.is_file() and p.suffix.lower() in _DUOI_VIDEO and not re.search(r"\.f\d+$", p.stem)]
    for p in cuoi:
        if p.stem == vid:
            return p
    # Tên tệp theo id khác id mục (Twitter: id media ≠ id tweet — smoke thật 22/09). Thư mục là của riêng
    # một mục ⇒ đúng MỘT tệp video cuối thì chính là nó; nhiều hơn thì không đoán.
    return cuoi[0] if len(cuoi) == 1 else None


class _TrangThai:
    """Trạng thái chung của hook tiến độ, hook ghép, nhịp tim và bộ lọc — mọi truy cập qua `khoa`
    (concurrent_fragment_downloads gọi hook từ nhiều luồng)."""

    def __init__(self, bao_tien_do: BaoTienDo):
        self._bao_tien_do = bao_tien_do
        self.khoa = threading.Lock()
        self.giu: list[BaseException] = []      # ngoại lệ GỐC của bao_tien_do (huỷ)
        self.pct = 0
        self.tep_hook: list[str] = []
        self.tu_choi: str | None = None          # mã lọc của yt-dlp (match_filter / max_filesize)

    def bao(self, pct: int | None, msg: str, *, tu_nhip: bool = False) -> None:
        """Gọi bao_tien_do. Lỗi ⇒ giữ ngoại lệ gốc; từ hook thì ném lớp huỷ, từ nhịp tim thì chỉ giữ."""
        with self.khoa:
            if self.giu:
                if tu_nhip:
                    return
                raise lop_huy()()
            if pct is not None:
                self.pct = pct
            try:
                self._bao_tien_do(self.pct, msg)
            except BaseException as e:  # noqa: BLE001 — mọi thứ bao_tien_do ném đều là huỷ
                self.giu.append(e)
                if tu_nhip:
                    return
                raise lop_huy()() from e

    def kiem_huy(self) -> None:
        with self.khoa:
            if self.giu:
                raise lop_huy()()

    def ghi_tep(self, fp: str) -> None:
        with self.khoa:
            self.tep_hook.append(fp)

    def ghi_tu_choi(self, ma: str) -> None:
        with self.khoa:
            if self.tu_choi is None:
                self.tu_choi = ma


@contextmanager
def _nhip_tim(tt: _TrangThai) -> Iterator[None]:
    """Luồng daemon báo `(pct gần nhất, "đang xử lý")` mỗi CHU_KY_NHIP giây tới khi thân `with` xong."""
    dung = threading.Event()

    def chay() -> None:
        while not dung.wait(CHU_KY_NHIP):
            tt.bao(None, _t("đang xử lý"), tu_nhip=True)
            if tt.giu:
                return

    t = threading.Thread(target=chay, name=TEN_LUONG_NHIP, daemon=True)
    t.start()
    try:
        yield
    finally:
        dung.set()
        t.join()


class _NhatKy:
    """Logger cho yt-dlp: bắt dòng HttpFD bỏ tệp vì quá lớn (không có exception nào báo điều này)."""

    def __init__(self, tt: _TrangThai):
        self._tt = tt

    def debug(self, msg: str) -> None:
        if _DAU_QUA_LON in (msg or ""):
            self._tt.ghi_tu_choi("qua_lon")

    info = warning = debug

    def error(self, msg: str) -> None:
        pass


class YtdlpAdapter:
    """Adapter nền tảng chạy trên yt-dlp. Lớp con cấp các thuộc tính/ phương thức dưới đây."""

    nen_tang: ClassVar[str] = ""
    #: IE_NAME cho phép (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Không generic.
    allowed_extractors: ClassVar[tuple[str, ...]] = ()
    extractor_args: ClassVar[dict] = {}
    #: ie_key chấp nhận cho mục phẳng khi khám phá (None — mục đã trích đầy đủ — luôn nhận).
    ie_key_video: ClassVar[tuple[str, ...]] = ()
    #: True ⇒ `impersonate=ImpersonateTarget()` (bất kỳ đích curl_cffi có sẵn).
    impersonate: ClassVar[bool] = False
    #: Gửi cookie phiên của khách khi khám phá / khi tải. TikTok: cookie đăng nhập làm TẢI trả 403 (donor Y:1734-1741).
    cookie_khi_kham_pha: ClassVar[bool] = True
    cookie_khi_tai: ClassVar[bool] = True

    def __init__(self, ydl_factory: Callable[[dict], Any] | None = None, *,
                 max_filesize: int = MAX_FILESIZE_MAC_DINH,
                 thoi_luong_toi_da_s: int = THOI_LUONG_TOI_DA_MAC_DINH):
        self._ydl_factory = ydl_factory
        self.max_filesize = int(max_filesize)
        self.thoi_luong_toi_da_s = int(thoi_luong_toi_da_s)
        #: Đường tới cookies.txt TẠM trong thư mục job (handler đặt, `phien.tep_cookie_tam`). None ⇒ ẩn danh.
        self.tep_cookie: str | None = None

    # ------------------------------------------------------------ lớp con cài đặt
    def url_video(self, id: str) -> str:
        """URL chuẩn MỘT video — nguồn duy nhất cho CrawlItem.url và cho URL đem tải."""
        raise NotImplementedError

    def id_hop_le(self, id: Any) -> bool:
        raise NotImplementedError

    def url_chuan(self, id: str, url_goi: str = "") -> str | None:
        """URL đem tải cho `id`. Mặc định BỎ `url_goi` (khách/kết quả gửi) và dựng lại từ id — chống URL giả mạo.
        Nền cần dữ liệu ngoài id trong URL (Xiaohongshu `xsec_token`) ghi đè và kiểm chặt; None ⇒ từ chối."""
        return self.url_video(id)

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        """URL/truy vấn yt-dlp cho từng chế độ (tu_khoa/kenh/bo/link)."""
        raise NotImplementedError

    # ------------------------------------------------------------ tuỳ chọn
    @classmethod
    def tuy_chon_goc(cls, thu_muc: Path | None = None, *, progress_hooks: list | None = None,
                     postprocessor_hooks: list | None = None) -> dict[str, Any]:
        """Tuỳ chọn yt-dlp thuần (không hook trạng thái). `thu_muc` có ⇒ tuỳ chọn tải một mục vào đó."""
        o: dict[str, Any] = {
            "format": CHUOI_FORMAT,                       # Y:2019
            "format_sort": ["res", "br"],                 # Y:2020-2021
            "merge_output_format": "mp4",                 # Y:2022
            "quiet": True, "no_warnings": True, "noprogress": True,   # Y:2025-2027
            "ignoreerrors": False,                        # spec §18 — donor bật (Y:2023), cố ý không chép
            "retries": 3,                                 # Y:2028
            "concurrent_fragment_downloads": 4,           # Y:2030
            "enable_file_urls": False,                    # Y:2031
            "sleep_interval_requests": 1.0,               # Y:2090-2095
            "allowed_extractors": list(cls.allowed_extractors),   # spec §21 (LTT thêm)
        }
        if cls.extractor_args:
            o["extractor_args"] = {k: {kk: list(vv) for kk, vv in v.items()} for k, v in cls.extractor_args.items()}
        if cls.impersonate:
            from yt_dlp.networking.impersonate import ImpersonateTarget
            o["impersonate"] = ImpersonateTarget()
        if thu_muc is not None:
            o["outtmpl"] = str(Path(thu_muc) / "%(id)s.%(ext)s")
            o["noplaylist"] = True
        if progress_hooks:
            o["progress_hooks"] = list(progress_hooks)
        if postprocessor_hooks:
            o["postprocessor_hooks"] = list(postprocessor_hooks)
        return o

    # ------------------------------------------------------------ lọc
    def ly_do_tu_choi(self, info: Any) -> str | None:
        """Mã từ chối (khong_ho_tro_truc_tiep / qua_dai / qua_lon) hoặc None. Trường vắng ⇒ không xét."""
        if info.get("is_live") is True or info.get("live_status") in _TRUC_TIEP:
            return "khong_ho_tro_truc_tiep"
        dur = info.get("duration")
        if isinstance(dur, (int, float)) and dur > self.thoi_luong_toi_da_s:
            return "qua_dai"
        for k in ("filesize", "filesize_approx"):
            v = info.get(k)
            if isinstance(v, (int, float)) and v > self.max_filesize:
                return "qua_lon"
        return None

    def bo_loc(self, ghi: Callable[[str], None] | None = None) -> Callable[..., str | None]:
        """`match_filter` cho yt-dlp (chữ ký YoutubeDL.py:453-456). `ghi(ma)` nhận mã khi từ chối."""
        def match_filter(info_dict, *, incomplete=False):
            ma = self.ly_do_tu_choi(info_dict)
            if ma is None:
                return None
            if ghi is not None:
                ghi(ma)
            return f"{info_dict.get('id') or 'entry'}: {ma}"
        return match_filter

    # ------------------------------------------------------------ yt-dlp
    def _tao(self, opts: dict):
        if self._ydl_factory is None:
            import yt_dlp
            return yt_dlp.YoutubeDL(opts)
        return self._ydl_factory(opts)

    def _them_chung(self, opts: dict, tt: _TrangThai, *, ghi_tu_choi: bool) -> dict:
        opts["match_filter"] = self.bo_loc(tt.ghi_tu_choi if ghi_tu_choi else None)
        opts["max_filesize"] = self.max_filesize
        opts["logger"] = _NhatKy(tt)
        dung_cookie = self.cookie_khi_tai if ghi_tu_choi else self.cookie_khi_kham_pha   # ghi_tu_choi ⇔ đường tải
        if self.tep_cookie and dung_cookie:
            opts["cookiefile"] = str(self.tep_cookie)
        return opts

    def _sang_item(self, e: dict) -> CrawlItem:
        vid = str(e["id"])
        dur = e.get("duration")
        return CrawlItem(
            nen_tang=self.nen_tang, id=vid, url=self.url_video(vid),
            tieu_de=str(e.get("title") or ""),
            tac_gia=str(e.get("channel") or e.get("uploader") or ""),
            thoi_luong_s=int(dur) if isinstance(dur, (int, float)) else None,
            anh_bia=_anh_bia(e),
        )

    @staticmethod
    def _nem_lai(tt: _TrangThai, e: BaseException) -> None:
        from yt_dlp.utils import DownloadError

        if tt.giu:
            raise tt.giu[0] from None
        if isinstance(e, DownloadError):
            raise phan_loai(str(e)) from None
        raise e

    # ------------------------------------------------------------ khám phá
    def kham_pha(self, yeu_cau: YeuCauCao, *, bao_tien_do: BaoTienDo) -> list[CrawlItem]:
        from yt_dlp.utils import DownloadCancelled, DownloadError

        n = int(yeu_cau.so_luong)
        che_do, vao = yeu_cau.che_do, yeu_cau.dau_vao.strip()
        tt = _TrangThai(bao_tien_do)
        opts = self._them_chung(self.tuy_chon_goc(), tt, ghi_tu_choi=False)
        opts.update(extract_flat="in_playlist", skip_download=True)
        if che_do == "link":                          # một mục
            n = 1
            opts["noplaylist"] = True
        else:
            opts["playlistend"] = n
        url = self.url_kham_pha(che_do, vao, n)
        bao_tien_do(0, _t("đang tìm video"))             # ngoài yt-dlp: để ngoại lệ gốc tự thoát
        try:
            with _nhip_tim(tt), self._tao(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except (DownloadCancelled, DownloadError) as e:
            self._nem_lai(tt, e)
        if tt.giu:
            raise tt.giu[0]
        info = info or {}
        entries = info.get("entries") if "entries" in info else [info]
        ra: list[CrawlItem] = []
        for muc in entries or []:
            if len(ra) >= n:
                break
            if not isinstance(muc, dict) or not self.id_hop_le(str(muc.get("id") or "")):
                continue
            if muc.get("ie_key") is not None and muc.get("ie_key") not in self.ie_key_video:
                continue                              # tab/playlist lồng, không phải video
            if self.ly_do_tu_choi(muc) is not None:
                continue
            ra.append(self._sang_item(muc))
        bao_tien_do(100, _t("tìm thấy {n} video").format(n=len(ra)))
        return ra

    # ------------------------------------------------------------ tải
    def tai(self, item: CrawlItem, thu_muc: Path, *, bao_tien_do: BaoTienDo) -> TepTai:
        from yt_dlp.utils import DownloadCancelled, DownloadError

        if not self.id_hop_le(item.id) or item.url != self.url_chuan(item.id, item.url):
            raise LoiCao("url_khong_ho_tro", _t("Link không được hỗ trợ cho nền tảng này."), tam_thoi=False)
        thu_muc = Path(thu_muc)
        tt = _TrangThai(bao_tien_do)

        def hook(d: dict) -> None:
            tt.kiem_huy()
            st = d.get("status")
            if st == "finished" and d.get("filename"):
                tt.ghi_tep(d["filename"])
                return
            if st != "downloading":
                return
            tong = d.get("total_bytes") or d.get("total_bytes_estimate")
            xong = d.get("downloaded_bytes")
            pct = max(0, min(98, int(xong * 100 / tong))) if tong and xong is not None else None
            tt.bao(pct, _t("đang tải"))                   # mọi lần gọi; bên gọi tự bóp theo thời gian

        def pp_hook(d: dict) -> None:
            tt.kiem_huy()
            fp = (d.get("info_dict") or {}).get("filepath")
            if fp:
                tt.ghi_tep(fp)
            if d.get("status") == "started":
                tt.bao(99, _t("đang ghép"))

        opts = self._them_chung(self.tuy_chon_goc(thu_muc, progress_hooks=[hook], postprocessor_hooks=[pp_hook]),
                                tt, ghi_tu_choi=True)
        try:
            with _nhip_tim(tt), self._tao(opts) as ydl:
                ydl.download([self.url_video(item.id)])
        except (DownloadCancelled, DownloadError) as e:
            self._nem_lai(tt, e)
        if tt.giu:
            raise tt.giu[0]
        if tt.tu_choi:
            raise LoiCao(tt.tu_choi, _t(_TU_CHOI[tt.tu_choi]), tam_thoi=False)

        path = tim_tep(item.id, thu_muc, tt.tep_hook)
        if path is None:
            raise LoiCao("khong_thay_tep", _t("Tải xong nhưng không tìm thấy tệp video. Vui lòng thử lại."),
                         tam_thoi=True)
        kich_thuoc = path.stat().st_size
        if kich_thuoc > self.max_filesize:            # tải phân mảnh (DASH/HLS) không kiểm max_filesize
            path.unlink(missing_ok=True)
            ma_qua_lon = "qua_lon"
            raise LoiCao(ma_qua_lon, _t(_TU_CHOI[ma_qua_lon]), tam_thoi=False)
        ten = ten_sach(item.tieu_de) or item.id
        return TepTai(duong_dan=path, kich_thuoc=kich_thuoc, ten_hien_thi=f"{ten} [{item.id}]{path.suffix}")
