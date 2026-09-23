"""Client web Douyin cho `tu_khoa` (tìm video) và `kenh` (video của một người dùng) — spec §11.

yt-dlp chỉ có extractor MỘT video cho Douyin (`yt-dlp/yt-dlp#2120` "Add DouyinUserIE" vẫn mở) ⇒ tìm/kênh gọi
thẳng API web của Douyin, ký `a_bogus` bằng bản port `apps/video_crawler/vendor/f2_abogus/` (Apache-2.0).
KHÔNG đọc/chép MediaCrawler (NON-COMMERCIAL).

Nguồn (giấy phép dùng được):
- Tham số gốc + kênh: `Evil0ctal/Douyin_TikTok_Download_API` (Apache-2.0) @9fa3e54
  `src/dtk/platforms/douyin/params.py` (`base_params`, `author_posts_params`: `max_cursor`, `count=20`, …);
  `endpoints.py` (`USER_POST`, `GENERAL_SEARCH`, header `Referer`/`Origin`). Chữ ký tính trên query ĐÃ mã hoá.
- Tìm kiếm: `jiji262/douyin-downloader` (MIT) @9874f41 `core/api_client.py:search_aweme`
  (`search_channel=aweme_video_web`, `offset`/`count`; phản hồi `data[].aweme_info`, `has_more`, `cursor`;
  `status_code == 2483` = cần đăng nhập; 200 thân rỗng = chống bot ⇒ thử lại với chữ ký mới; 403 = từ chối).
- Trường aweme: `Johnserf-Seed/f2` (Apache-2.0) @7dab3e2 `f2/apps/douyin/filter.py:UserPostFilter`
  (`aweme_list`, `has_more`, `max_cursor`, `images` = bài ảnh); yt-dlp 2026.03.17 `extractor/tiktok.py:
  _parse_aweme_video_app` (`video.duration` tính ms, bìa `video.cover`/`origin_cover.url_list`).
- Ký: `f2/apps/douyin/utils.py:ABogusManager.model_2_endpoint` — `<query>&a_bogus=<chữ ký>`, chữ ký nối thô.

Đường ra HTTP: qua `YoutubeDL.urlopen` của yt-dlp (cùng ngăn xếp mạng + cookiefile mà `tai` đã dùng), KHÔNG
import httpx/urllib.request ở tầng app (`tests/test_1006_rao_kien_truc.py:HTTP_CAM_O_APP`).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlencode

from platform_core.i18n import N_

from apps.video_crawler.adapters.base import LoiCao

__all__ = [
    "DUONG_KENH", "DUONG_TIM", "DUONG_TIM_KENH", "SO_TRANG_TOI_DA", "UA", "DouyinWeb", "doc_cookie",
    "dung_url", "kenh_tu_user", "ky_a_bogus", "muc_tu_aweme", "sec_uid_tu_link", "tham_so_goc",
    "tham_so_tim_kenh", "van_chuyen_ytdlp",
]

GOC = "https://www.douyin.com"
DUONG_TIM = "/aweme/v1/web/general/search/single/"
DUONG_KENH = "/aweme/v1/web/aweme/post/"
#: Tìm NGƯỜI DÙNG theo tên: `Evil0ctal/Douyin_TikTok_Download_API` (Apache-2.0) @9fa3e54
#: `src/dtk/platforms/douyin/endpoints.py:USER_SEARCH`; kênh tìm `aweme_user_web` (giá trị công khai,
#: nhiều client độc lập dùng cùng một hằng). Phản hồi: `user_list[].user_info`, `has_more`.
#: Spike 23/09: ẩn danh trả HTTP 200 THÂN RỖNG (chống bot) cả hai lượt ⇒ đường này bắt buộc có phiên.
DUONG_TIM_KENH = "/aweme/v1/web/discover/search/"
#: UA phải khớp `browser_name`/`browser_version` gửi trong query (Evil0ctal params.py: hồ sơ phải nhất quán).
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0.0.0 Safari/537.36")
CO_TRANG_TIM = 10          # jiji262 search_aweme count mặc định
CO_TRANG_KENH = 20         # Evil0ctal DEFAULT_PAGE_SIZE ("Douyin silently caps larger values")
SO_TRANG_TOI_DA = 6        # trần cứng: so_luong_toi_da=20 ⇒ 2-3 trang là đủ; chặn lặp khi trang toàn mục bị lọc
MA_CAN_DANG_NHAP = frozenset({2483})

#: (url, headers) -> (mã HTTP, thân). Lỗi mạng ⇒ ném LoiCao("mang").
VanChuyen = Callable[[str, dict], tuple[int, bytes]]
#: (query đã mã hoá, UA) -> a_bogus
KyTen = Callable[[str, str], str]

# Cùng msgid với `apps/video_crawler/loi.py` ⇒ không thêm bản dịch mới.
_CAN_DANG_NHAP = N_("Nền tảng yêu cầu đăng nhập — thêm phiên ở mục Đăng nhập nền tảng rồi thử lại.")
_NEN_CHAN = N_("Nền tảng đang chặn truy cập ẩn danh từ máy chủ — thêm phiên ở mục Đăng nhập nền tảng rồi thử lại.")
_MANG = N_("Lỗi mạng khi kết nối tới nền tảng. Vui lòng thử lại sau.")
_URL_SAI = N_("Link không được hỗ trợ cho nền tảng này.")


def loi_can_dang_nhap() -> LoiCao:
    return LoiCao("can_dang_nhap", _CAN_DANG_NHAP, tam_thoi=False)


def loi_nen_chan() -> LoiCao:
    return LoiCao("nen_chan", _NEN_CHAN, tam_thoi=False)


def loi_mang() -> LoiCao:
    return LoiCao("mang", _MANG, tam_thoi=True)


def loi_url_sai() -> LoiCao:
    return LoiCao("url_khong_ho_tro", _URL_SAI, tam_thoi=False)


# ---------------------------------------------------------------- tham số + ký
def tham_so_goc() -> dict[str, str]:
    """Evil0ctal `params.py:base_params` với DEFAULT_PROFILE (Chrome 130 / Windows 10, zh-CN)."""
    return {
        "device_platform": "webapp", "aid": "6383", "channel": "channel_pc_web", "pc_client_type": "1",
        "version_code": "290100", "version_name": "29.1.0", "cookie_enabled": "true",
        "screen_width": "1920", "screen_height": "1080", "browser_language": "zh-CN",
        "browser_platform": "Win32", "browser_name": "Chrome", "browser_version": "130.0.0.0",
        "browser_online": "true", "engine_name": "Blink", "engine_version": "130.0.0.0",
        "os_name": "Windows", "os_version": "10", "cpu_core_num": "12", "device_memory": "8",
        "platform": "PC", "downlink": "10", "effective_type": "4g", "round_trip_time": "0",
        "update_version_code": "170400",
    }


def tham_so_tim(tu_khoa: str, offset: int, count: int = CO_TRANG_TIM) -> dict[str, str]:
    return {**tham_so_goc(), "keyword": tu_khoa, "search_channel": "aweme_video_web", "sort_type": "0",
            "publish_time": "0", "search_source": "normal_search", "query_correct_type": "1",
            "is_filter_search": "0", "offset": str(offset), "count": str(count)}


def tham_so_kenh(sec_uid: str, max_cursor: str, count: int = CO_TRANG_KENH) -> dict[str, str]:
    return {**tham_so_goc(), "sec_user_id": sec_uid, "max_cursor": str(max_cursor or "0"), "count": str(count),
            "publish_video_strategy_type": "2", "from_user_page": "1", "locate_query": "false",
            "need_time_list": "1", "show_live_replay_strategy": "1", "time_list_query": "0",
            "pc_libra_divert": "Windows", "whale_cut_token": ""}


def tham_so_tim_kenh(tu_khoa: str, offset: int, count: int = CO_TRANG_TIM) -> dict[str, str]:
    return {**tham_so_goc(), "keyword": tu_khoa, "search_channel": "aweme_user_web",
            "search_source": "normal_search", "query_correct_type": "1", "is_filter_search": "0",
            "offset": str(offset), "count": str(count)}


def ky_a_bogus(query: str, ua: str) -> str:
    """Chữ ký a_bogus cho GET (ABogus mới mỗi lần — upstream tạo lại mỗi request, bảng RC4 có trạng thái)."""
    from apps.video_crawler.vendor.f2_abogus.abogus import ABogus

    return ABogus(user_agent=ua).generate_abogus(query)[1]


def dung_url(duong: str, params: dict[str, str], *, ms_token: str, ky: KyTen) -> str:
    if ms_token:
        params = {**params, "msToken": ms_token}
    q = urlencode(params, quote_via=quote)
    return f"{GOC}{duong}?{q}&a_bogus={ky(q, UA)}"


# ---------------------------------------------------------------- cookie / đầu vào
def doc_cookie(tep: str | None, ten: str) -> str:
    """Giá trị cookie `ten` trong cookies.txt (Netscape; nhận tiền tố `#HttpOnly_`). Không có ⇒ ""."""
    if not tep:
        return ""
    try:
        dong = Path(tep).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for d in dong:
        if d.startswith("#HttpOnly_"):
            d = d[len("#HttpOnly_"):]
        elif d.startswith("#"):
            continue
        cot = d.rstrip("\r").split("\t")
        if len(cot) >= 7 and cot[5] == ten:
            return cot[6]
    return ""


_SEC_UID = r"[A-Za-z0-9_-]{20,200}"
_RE_LINK_USER = re.compile(rf"^(?:https?://)?(?:www\.)?douyin\.com/user/(?P<s>{_SEC_UID})(?:[/?#]|$)")
_RE_SEC_TRAN = re.compile(rf"^{_SEC_UID}$")


def sec_uid_tu_link(s: str) -> str | None:
    """`douyin.com/user/<sec_uid>` hoặc sec_uid trần ⇒ sec_uid; còn lại (link rút gọn, /user/self…) ⇒ None."""
    s = (s or "").strip()
    m = _RE_LINK_USER.match(s)
    if m:
        return m["s"]
    return s if _RE_SEC_TRAN.match(s) else None


# ---------------------------------------------------------------- aweme -> mục
def _url_dau(d: Any) -> str:
    urls = d.get("url_list") if isinstance(d, dict) else None
    return str(urls[0]) if isinstance(urls, list) and urls and urls[0] else ""


def muc_tu_aweme(aw: Any) -> dict | None:
    """Một aweme ⇒ {id, tieu_de, tac_gia, thoi_luong_s, anh_bia}; bài ảnh (`images`) hoặc rác ⇒ None."""
    if not isinstance(aw, dict) or not aw.get("aweme_id") or aw.get("images"):
        return None
    v, a = aw.get("video"), aw.get("author")
    video: dict = v if isinstance(v, dict) else {}
    author: dict = a if isinstance(a, dict) else {}
    ms = video.get("duration")
    return {
        "id": str(aw["aweme_id"]),
        "tieu_de": str(aw.get("desc") or ""),
        "tac_gia": str(author.get("nickname") or ""),
        "thoi_luong_s": round(ms / 1000) if isinstance(ms, (int, float)) and ms > 0 else None,
        "anh_bia": _url_dau(video.get("cover")) or _url_dau(video.get("origin_cover")),
    }


def kenh_tu_user(muc: Any) -> dict | None:
    """Một mục `user_list[]` ⇒ {id (sec_uid), ten, anh_dai_dien, so_theo_doi, so_video, mo_ta}.

    `sec_uid` (không phải `uid`) là thứ `tham_so_kenh` cần để liệt kê video ⇒ dùng làm id kênh.
    Thiếu `sec_uid` hoặc mục lạ ⇒ None (không ném).
    """
    ui = muc.get("user_info") if isinstance(muc, dict) else None
    if not isinstance(ui, dict) or not ui.get("sec_uid"):
        return None
    return {
        "id": str(ui["sec_uid"]),
        "ten": ui.get("nickname"),
        "anh_dai_dien": _url_dau(ui.get("avatar_thumb")) or _url_dau(ui.get("avatar_larger")),
        "so_theo_doi": ui.get("follower_count"),
        "so_video": ui.get("aweme_count"),
        "mo_ta": ui.get("signature"),
    }


# ---------------------------------------------------------------- vận chuyển mặc định
def van_chuyen_ytdlp(tep_cookie: str | None, *, ydl_factory: Callable[[dict], Any] | None = None) -> VanChuyen:
    """Vận chuyển qua `YoutubeDL.urlopen` (cookiefile = cookies.txt tạm của khách, như đường `tai`)."""
    def lay(url: str, headers: dict) -> tuple[int, bytes]:
        from yt_dlp.networking import Request
        from yt_dlp.networking.exceptions import HTTPError, RequestError

        opts: dict[str, Any] = {"quiet": True, "no_warnings": True}
        if tep_cookie:
            opts["cookiefile"] = str(tep_cookie)
        if ydl_factory is None:
            import yt_dlp
            tao: Callable[[dict], Any] = yt_dlp.YoutubeDL
        else:
            tao = ydl_factory
        try:
            with tao(opts) as ydl:
                r = ydl.urlopen(Request(url, headers=dict(headers)))
                return int(r.status), r.read()
        except HTTPError as e:
            return int(e.status), e.response.read()
        except RequestError as e:
            raise loi_mang() from e
    return lay


# ---------------------------------------------------------------- client
class DouyinWeb:
    def __init__(self, lay: VanChuyen, *, ms_token: str = "", ky: KyTen = ky_a_bogus):
        self._lay = lay
        self._ms_token = ms_token
        self._ky = ky

    def _goi(self, duong: str, params: dict[str, str]) -> dict:
        headers = {"User-Agent": UA, "Referer": f"{GOC}/", "Origin": GOC, "Accept": "application/json, text/plain, */*"}
        for _ in range(2):                             # 200 thân rỗng ⇒ thử lại MỘT lần với chữ ký mới
            status, than = self._lay(dung_url(duong, params, ms_token=self._ms_token, ky=self._ky), headers)
            if status >= 500:
                raise loi_mang()
            if status != 200:
                raise loi_nen_chan()                   # 403 ArgusSecurityPlugin = từ chối xác định (jiji262)
            if (than or b"").strip():
                break
        else:
            raise loi_nen_chan()
        try:
            d = json.loads(than)
        except ValueError:
            raise loi_nen_chan() from None             # trang HTML xác minh thay vì JSON
        if not isinstance(d, dict):
            raise loi_nen_chan()
        ma = d.get("status_code") or 0
        if ma in MA_CAN_DANG_NHAP:
            raise loi_can_dang_nhap()
        if ma != 0:
            raise loi_nen_chan()
        return d

    def _lap(self, n: int, bao: Callable[[int], None], trang: Callable[[str], tuple[list, bool, str]],
             nhan: Callable[[dict], bool]) -> list[dict]:
        ra: list[dict] = []
        da_co: set[str] = set()
        con_tro = "0"
        for _ in range(SO_TRANG_TOI_DA):
            awemes, con, tiep = trang(con_tro)
            for aw in awemes:
                m = muc_tu_aweme(aw)
                if m is not None and m["id"] not in da_co and nhan(m):
                    da_co.add(m["id"])
                    ra.append(m)
            bao(min(95, len(ra) * 100 // max(n, 1)))
            if len(ra) >= n or not con or not tiep or tiep == con_tro:
                break
            con_tro = tiep
        return ra

    def tim_video(self, tu_khoa: str, n: int, *, bao: Callable[[int], None],
                  nhan: Callable[[dict], bool] = lambda m: True) -> list[dict]:
        """Tới `n` mục mà `nhan(mục)` chấp nhận (lọc TRƯỚC khi đếm ⇒ mục bị bỏ không làm hụt số lượng)."""
        def trang(con_tro: str) -> tuple[list, bool, str]:
            d = self._goi(DUONG_TIM, tham_so_tim(tu_khoa, int(con_tro or 0)))
            dl = d.get("data")
            data: list = dl if isinstance(dl, list) else []
            awemes = [x.get("aweme_info") for x in data if isinstance(x, dict) and isinstance(x.get("aweme_info"), dict)]
            return awemes, bool(d.get("has_more")), str(d.get("cursor") or "")
        return self._lap(n, bao, trang, nhan)

    def video_cua_nguoi_dung(self, sec_uid: str, n: int, *, bao: Callable[[int], None],
                             nhan: Callable[[dict], bool] = lambda m: True) -> list[dict]:
        def trang(con_tro: str) -> tuple[list, bool, str]:
            d = self._goi(DUONG_KENH, tham_so_kenh(sec_uid, con_tro))
            al = d.get("aweme_list")
            awemes: list = al if isinstance(al, list) else []
            return awemes, bool(d.get("has_more")), str(d.get("max_cursor") or "")
        return self._lap(n, bao, trang, nhan)

    def tim_nguoi_dung(self, tu_khoa: str, n: int, *, bao: Callable[[int], None]) -> list[dict]:
        """Tới `n` kênh khớp `tu_khoa`. Phân trang theo `offset` (như tìm video), bỏ trùng theo sec_uid."""
        ra: list[dict] = []
        da_co: set[str] = set()
        offset = 0
        for _ in range(SO_TRANG_TOI_DA):
            d = self._goi(DUONG_TIM_KENH, tham_so_tim_kenh(tu_khoa, offset))
            ul = d.get("user_list")
            for muc in (ul if isinstance(ul, list) else []):
                k = kenh_tu_user(muc)
                if k is not None and k["id"] not in da_co:
                    da_co.add(k["id"])
                    ra.append(k)
            bao(min(95, len(ra) * 100 // max(n, 1)))
            if len(ra) >= n or not d.get("has_more"):
                break
            offset += CO_TRANG_TIM
        return ra[:n]
