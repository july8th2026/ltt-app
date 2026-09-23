"""video_crawler — registry nền tảng (một nguồn chân lý, spec §12) + nhận diện link.

Ids và luật domain port từ donor `_LINK_DOM` / `_doanTuLink`, GIỮ NGUYÊN THỨ TỰ (chỉ đọc):
  D:\\Viral\\resources\\app-src\\web\\index.html:16748-16798

Tên chế độ đổi sang tiếng Việt theo registry LTT: search→tu_khoa, detail→link, creator→kenh,
chase→bo. Hai override của donor (không phải "if platform ==" tuỳ tiện, mà đúng hành vi donor):
honggo (hg) luôn ⇒ bo (chỉ có một chế độ, khỏi đoán); bilibili_tv (bilitv) luôn ⇒ link (nền chỉ
có một đường: link công khai qua yt-dlp).

Chi tiết chế độ/login cho các nền chưa bật lấy từ `docs/migrations/video_crawler/PLATFORM_MATRIX.md`.
"""
from __future__ import annotations

import os
import re
import urllib.parse
from dataclasses import dataclass

from platform_core.i18n import N_
from platform_core.i18n import _ as _t

from apps.video_crawler.adapters.base import CHE_DO

#: Tắt mềm theo nền (vận hành, không đụng mã) — brief L4-c. Danh sách id phẩy, ví dụ "douyin,weibo".
#: Đọc MỖI LẦN GỌI (không cache): đổi env + không cần khởi động lại worker web để có hiệu lực ngay.
CO_TAT_NEN = "LTT_VIDEO_CRAWLER_TAT"


def _id_nen_da_tat() -> frozenset[str]:
    gia_tri = os.environ.get(CO_TAT_NEN, "")
    return frozenset(s.strip() for s in gia_tri.split(",") if s.strip())

#: search/detail/creator/chase (donor) → tu_khoa/link/kenh/bo (LTT).
_MODE_MAP = {
    "detail": "link",
    "chase": "bo",
    "search": "tu_khoa",
    "creator": "kenh",
    "": "",
}

#: Nền tảng có "một đường duy nhất" — donor ép chế độ, không đoán (H:16793-16795).
_EP_CHE_DO = {
    "honggo": "chase",
    "bilibili_tv": "detail",
}

# Thứ tự đoán chế độ từ link CÓ CHỦ Ý (hẹp trước, rộng sau) — port nguyên văn H:16770-16792.
_RE_DETAIL_THAM_SO = re.compile(r"[?&](?:vid|modal_id)=\d+")
_RE_CHASE = re.compile(r"/voddetail/|/collection/|/playlist/|[?&]list=")
_RE_SEARCH = re.compile(r"/search/|[?&]q=|[?&]keyword=")
#: Link rút gọn (lane W4-L12, `an_toan_url.theo_chuyen_huong` giải ra URL thật CÓ KIỂM SSRF) luôn là
#: MỘT video/bài — đoán `detail` (⇒ `link`) giống donor đã làm sẵn cho `b23\.tv`/`v\.douyin\.com` ở
#: dòng dưới; `xhslink.com`, `v.kuaishou.com`, `vm/vt.tiktok.com` LTT thêm cùng logic (không phải
#: hành vi donor — donor không có các nền này ở `_LINK_DOM`).
_RE_DETAIL = re.compile(
    r"/video/|/videos/\d|/note/|/explore/[0-9a-z]{6,}|/discovery/item/|"
    r"/short-video/|/vodplay/|/status/|/reel/|/p/|/photo/|watch/?\?v=|"
    r"fb\.watch/|/share/[vrp]/|/posts/|youtu\.be/|/shorts/|b23\.tv/|v\.douyin\.com/|"
    r"xhslink\.com/|v\.kuaishou\.com/|v[mt]\.tiktok\.com/"
)
_RE_CREATOR = re.compile(r"/user/|/space/|space\.bilibili\.com|/profile/|/channel/|/c/|/@|/(?:videos|reels)/?(?:[?#]|$)")


class NenKhongHopLe(Exception):
    """Id nền không tồn tại trong registry, hoặc tồn tại nhưng chưa `bat`."""


@dataclass(frozen=True)
class NenTang:
    id: str
    ten: str
    icon: str
    bat: bool
    che_do: frozenset
    xem_truoc: bool
    can_dang_nhap: bool
    cach_dang_nhap: str  # "" | "qr" | "cookie"
    ten_mien: tuple
    so_luong_toi_da: int
    adapter: str
    gioi_han: tuple
    #: Tên cookie chứng minh ĐÃ đăng nhập (donor `COOKIE_AUTH` W:17772-17796). Rỗng ⇒ nền không nhận phiên.
    cookie_dang_nhap: tuple = ()
    #: Chế độ BẮT BUỘC có phiên (vd TikTok từ khoá — donor Y:1541-1544). Chưa có phiên ⇒ chặn ở cửa vào.
    che_do_can_dang_nhap: frozenset = frozenset()


@dataclass(frozen=True)
class DoanLink:
    nen_tang: str
    che_do: str


def _kt(*che_do: str) -> frozenset:
    het = frozenset(che_do)
    thua = het - CHE_DO
    assert not thua, _t("chế độ ngoài hợp đồng: {thua}").format(thua=thua)
    return het


# Registry — thứ tự GIỮ NGUYÊN theo _LINK_DOM (H:16748-16753).
_NEN: tuple[NenTang, ...] = (
    NenTang(
        id="douyin", ten="Douyin", icon="douyin", bat=True,
        che_do=_kt("tu_khoa", "link", "kenh"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="qr",
        ten_mien=('douyin.com', 'iesdouyin.com'),
        so_luong_toi_da=20, adapter="douyin", gioi_han=(N_("Cần phiên Douyin cho mọi cách cào."),),
        cookie_dang_nhap=('sessionid', 'sessionid_ss', 'sid_tt'),
        che_do_can_dang_nhap=frozenset({'link', 'kenh', 'tu_khoa'}),
    ),
    NenTang(
        id="bilibili_tv", ten=N_("Bilibili quốc tế"), icon="bilibili_tv", bat=True,
        che_do=_kt("link"),
        xem_truoc=False, can_dang_nhap=False, cach_dang_nhap="",
        ten_mien=("bilibili.tv",),
        so_luong_toi_da=20, adapter="bilibili_tv", gioi_han=(N_('Chỉ link video độc lập (/video/…), chưa hỗ trợ link tập phim.'),),
    ),
    NenTang(
        id="bilibili", ten="Bilibili", icon="bilibili", bat=True,
        che_do=_kt("tu_khoa", "link", "kenh", "bo"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="qr",
        ten_mien=('bilibili.com', 'b23.tv'),
        so_luong_toi_da=20, adapter="bilibili", gioi_han=(N_('Cần phiên: Bilibili chặn truy cập ẩn danh từ máy chủ (HTTP 412).'),),
        cookie_dang_nhap=('SESSDATA', 'DedeUserID'),
        che_do_can_dang_nhap=frozenset({'link', 'tu_khoa', 'kenh', 'bo'}),
    ),
    NenTang(
        id="xiaohongshu", ten="Xiaohongshu", icon="xiaohongshu", bat=True,
        che_do=_kt("tu_khoa", "link", "kenh"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="qr",
        ten_mien=('xiaohongshu.com', 'xhslink.com'),
        so_luong_toi_da=20, adapter="xiaohongshu", gioi_han=(N_("Tìm và kênh cần phiên Xiaohongshu."), N_("Link bài phải có xsec_token (copy từ trình duyệt)."), N_("Bài chỉ có ảnh không tải được.")),
        cookie_dang_nhap=('id_token',),
        che_do_can_dang_nhap=frozenset({'kenh', 'tu_khoa'}),
    ),
    NenTang(
        id="rednote", ten="RedNote", icon="rednote", bat=False,
        che_do=_kt("tu_khoa", "link", "kenh"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="qr",
        ten_mien=("rednote.com",),
        so_luong_toi_da=10, adapter="rednote", gioi_han=(),
        cookie_dang_nhap=('id_token',),
    ),
    NenTang(
        id="weibo", ten="Weibo", icon="weibo", bat=True,
        che_do=_kt("link", "kenh"),
        xem_truoc=False, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("weibo.com", "weibo.cn"),
        so_luong_toi_da=20, adapter="weibo", gioi_han=(N_('Link video hoặc trang kênh weibo.com/u/…'),),
        cookie_dang_nhap=('SUB', 'SUBP'),
    ),
    NenTang(
        id="tiktok", ten="TikTok", icon="tiktok", bat=True,
        che_do=_kt("tu_khoa", "link", "kenh", "bo"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("tiktok.com",),
        so_luong_toi_da=20, adapter="tiktok", gioi_han=(N_('Tìm theo từ khoá cần phiên TikTok.'), N_('Bài ảnh (slideshow) không có video.')),
        cookie_dang_nhap=('sessionid', 'sessionid_ss', 'sid_tt'),
        che_do_can_dang_nhap=frozenset({'tu_khoa'}),
    ),
    NenTang(
        id="youtube", ten="YouTube", icon="youtube", bat=True,
        che_do=_kt("tu_khoa", "link", "kenh", "bo"),
        xem_truoc=True, can_dang_nhap=False, cach_dang_nhap="",
        ten_mien=("youtube.com", "youtu.be"),
        so_luong_toi_da=20, adapter="youtube", gioi_han=(),
        cookie_dang_nhap=('SAPISID', 'LOGIN_INFO'),
    ),
    NenTang(
        id="facebook", ten="Facebook", icon="facebook", bat=True,
        che_do=_kt("link"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=('facebook.com', 'fb.watch', 'fb.com'),
        so_luong_toi_da=20, adapter="facebook", gioi_han=(N_('Chỉ link video/reel đầy đủ (chưa nhận fb.watch, Page).'),),
        cookie_dang_nhap=('c_user', 'xs'),
    ),
    NenTang(
        id="instagram", ten="Instagram", icon="instagram", bat=True,
        che_do=_kt("link"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("instagram.com",),
        so_luong_toi_da=20, adapter="instagram", gioi_han=(N_('Cần phiên Instagram.'), N_('Bài chỉ có ảnh không tải được.')),
        cookie_dang_nhap=('sessionid', 'ds_user_id'),
        che_do_can_dang_nhap=frozenset({'link'}),
    ),
    NenTang(
        id="twitter", ten="Twitter (X)", icon="twitter", bat=True,
        che_do=_kt("link"),
        xem_truoc=False, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("twitter.com", "x.com"),
        so_luong_toi_da=20, adapter="twitter", gioi_han=(N_('Chỉ link một tweet.'),),
        cookie_dang_nhap=('auth_token', 'ct0'),
    ),
    NenTang(
        id="kuaishou", ten="Kuaishou", icon="kuaishou", bat=False,
        che_do=_kt("tu_khoa", "link", "kenh"),
        xem_truoc=False, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("kuaishou.com",),
        so_luong_toi_da=20, adapter="kuaishou", gioi_han=(N_("Tìm và kênh cần phiên Kuaishou."),),
        cookie_dang_nhap=('passToken', 'kuaishou.server.web_st'),
        che_do_can_dang_nhap=frozenset({'kenh', 'tu_khoa'}),
    ),
    NenTang(
        id="honggo", ten="Honggo", icon="honggo", bat=False,
        che_do=_kt("link", "bo"),
        xem_truoc=False, can_dang_nhap=False, cach_dang_nhap="",
        ten_mien=("hongguoapp.cn", "hongguoduanju.com"),
        so_luong_toi_da=10, adapter="honggo", gioi_han=(),
    ),
)

_THEO_ID = {n.id: n for n in _NEN}


def lay(id: str) -> NenTang:
    """Trả `NenTang` theo id. Ném `NenKhongHopLe` nếu id không tồn tại."""
    try:
        return _THEO_ID[id]
    except KeyError:
        raise NenKhongHopLe(_t("nền không tồn tại: {id!r}").format(id=id)) from None


def cac_nen_bat() -> list[NenTang]:
    """Danh sách nền `bat=True` VÀ chưa bị tắt mềm qua `LTT_VIDEO_CRAWLER_TAT`, giữ thứ tự registry —
    dùng để dựng lưới UI. Nền bị tắt mềm biến mất khỏi đây (khách không thấy, không chọn được)."""
    tat = _id_nen_da_tat()
    return [n for n in _NEN if n.bat and n.id not in tat]


def lay_nen_bat(id: str) -> NenTang:
    """Như `lay`, nhưng ném `NenKhongHopLe` nếu nền chưa `bat` hoặc đang bị tắt mềm (vận hành, `nen_tang.py`)."""
    n = _THEO_ID.get(id)
    if n is None or not n.bat or n.id in _id_nen_da_tat():
        raise NenKhongHopLe(_t("nền không hợp lệ hoặc chưa bật: {id!r}").format(id=id))
    return n


def nhan_dien(url: str) -> str | None:
    """Nhận nền theo domain trong `url` (port `_LINK_DOM`, giữ thứ tự). None nếu không khớp nền nào."""
    # Function parity, không bug parity: donor so chuỗi con trên CẢ URL nên `netflix.com` khớp `x.com`.
    # Ở đây so theo HOSTNAME (bằng, hoặc là subdomain của tên miền nền).
    s = (url or "").strip()
    if not s:
        return None
    if "://" not in s:
        s = "https://" + s
    try:
        host = (urllib.parse.urlparse(s).hostname or "").lower()
    except ValueError:
        return None
    for n in _NEN:
        for dom in n.ten_mien:
            dom = dom.lower()
            if host == dom or host.endswith("." + dom):
                return n.id
    return None


def co_tim_kenh(nen_id: str) -> bool:
    """Nền này tìm kênh theo TÊN được không — hỏi thẳng lớp adapter, không có cờ khai tay.

    Một cờ trong registry là nguồn chân lý thứ hai: làm `tim_kenh` cho một nền mà quên bật cờ thì giao diện
    giấu mất tính năng vừa viết (và ngược lại, bật cờ cho nền chưa có mã thì khách gõ xong mới thấy lỗi).
    """
    from apps.video_crawler.adapters import base, tao
    try:
        lop = type(tao(nen_id))
    except (NenKhongHopLe, ImportError, LookupError):   # nền lạ / chưa bật / chưa có adapter
        return False
    if lop.tim_kenh is base.PlatformAdapter.tim_kenh:
        return False
    # Họ yt-dlp: mọi lớp con KẾ THỪA `YtdlpAdapter.tim_kenh`, nhưng bản chung ấy ném "chưa hỗ trợ" khi lớp con
    # chưa khai `ie_key_kenh` ⇒ so với bản mặc định thôi là bật nhầm cho Facebook/TikTok/Twitter/Instagram/Weibo.
    from apps.video_crawler.adapters._ytdlp import YtdlpAdapter
    if lop.tim_kenh is YtdlpAdapter.tim_kenh:
        return bool(getattr(lop, "ie_key_kenh", ()))
    return True


def doan_tu_link(s: str) -> DoanLink | None:
    """Đoán (nền, chế độ) từ một link dán vào — port nguyên văn `_doanTuLink` (H:16762-16797)."""
    l = (s or "").strip()
    if not l:
        return None
    plat = nhan_dien(l)
    if not plat:
        return None
    low = l.lower()
    mode = ""
    if _RE_DETAIL_THAM_SO.search(low):
        mode = "detail"
    elif _RE_CHASE.search(low):
        mode = "chase"
    elif _RE_SEARCH.search(low):
        mode = "search"
    elif _RE_DETAIL.search(low):
        mode = "detail"
    elif _RE_CREATOR.search(low):
        mode = "creator"
    elif plat == "facebook":
        mode = "creator"
    if plat in _EP_CHE_DO:
        mode = _EP_CHE_DO[plat]
    return DoanLink(nen_tang=plat, che_do=_MODE_MAP.get(mode, ""))
