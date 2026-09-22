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

import re
import urllib.parse
from dataclasses import dataclass

from apps.video_crawler.adapters.base import CHE_DO

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
_RE_DETAIL = re.compile(
    r"/video/|/videos/\d|/note/|/explore/[0-9a-z]{6,}|/discovery/item/|"
    r"/short-video/|/vodplay/|/status/|/reel/|/p/|/photo/|watch/?\?v=|"
    r"fb\.watch/|/share/[vrp]/|/posts/|youtu\.be/|/shorts/|b23\.tv/|v\.douyin\.com/"
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
    assert not thua, f"chế độ ngoài hợp đồng: {thua}"
    return het


# Registry — thứ tự GIỮ NGUYÊN theo _LINK_DOM (H:16748-16753).
_NEN: tuple[NenTang, ...] = (
    NenTang(
        id="douyin", ten="Douyin", icon="douyin", bat=False,
        che_do=_kt("tu_khoa", "link", "kenh", "bo"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="qr",
        ten_mien=("douyin.com", "v.douyin.com", "iesdouyin.com"),
        so_luong_toi_da=10, adapter="douyin", gioi_han=(),
        cookie_dang_nhap=('sessionid', 'sessionid_ss', 'sid_tt'),
    ),
    NenTang(
        id="bilibili_tv", ten="Bilibili quốc tế", icon="bilibili_tv", bat=False,
        che_do=_kt("link"),
        xem_truoc=False, can_dang_nhap=False, cach_dang_nhap="",
        ten_mien=("bilibili.tv",),
        so_luong_toi_da=10, adapter="bilibili_tv", gioi_han=(),
    ),
    NenTang(
        id="bilibili", ten="Bilibili", icon="bilibili", bat=False,
        che_do=_kt("tu_khoa", "link", "kenh", "bo"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="qr",
        ten_mien=("bilibili.com", "b23.tv"),
        so_luong_toi_da=10, adapter="bilibili", gioi_han=(),
        cookie_dang_nhap=('SESSDATA', 'DedeUserID'),
    ),
    NenTang(
        id="xiaohongshu", ten="Xiaohongshu", icon="xiaohongshu", bat=False,
        che_do=_kt("tu_khoa", "link", "kenh"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="qr",
        ten_mien=("xiaohongshu.com", "xhslink.com"),
        so_luong_toi_da=10, adapter="xiaohongshu", gioi_han=(),
        cookie_dang_nhap=('id_token',),
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
        id="weibo", ten="Weibo", icon="weibo", bat=False,
        che_do=_kt(),
        xem_truoc=False, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("weibo.com", "weibo.cn"),
        so_luong_toi_da=10, adapter="weibo", gioi_han=(),
        cookie_dang_nhap=('SUB', 'SUBP'),
    ),
    NenTang(
        id="tiktok", ten="TikTok", icon="tiktok", bat=False,
        che_do=_kt("tu_khoa", "link", "kenh", "bo"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("tiktok.com",),
        so_luong_toi_da=10, adapter="tiktok", gioi_han=(),
        cookie_dang_nhap=('sessionid', 'sessionid_ss', 'sid_tt'),
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
        id="facebook", ten="Facebook", icon="facebook", bat=False,
        che_do=_kt("link", "kenh"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("facebook.com", "fb.watch"),
        so_luong_toi_da=10, adapter="facebook", gioi_han=(),
        cookie_dang_nhap=('c_user', 'xs'),
    ),
    NenTang(
        id="instagram", ten="Instagram", icon="instagram", bat=False,
        che_do=_kt("link", "kenh"),
        xem_truoc=True, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("instagram.com",),
        so_luong_toi_da=10, adapter="instagram", gioi_han=(),
        cookie_dang_nhap=('sessionid', 'ds_user_id'),
    ),
    NenTang(
        id="twitter", ten="Twitter (X)", icon="twitter", bat=False,
        che_do=_kt("link", "kenh"),
        xem_truoc=False, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("twitter.com", "x.com"),
        so_luong_toi_da=10, adapter="twitter", gioi_han=(),
        cookie_dang_nhap=('auth_token', 'ct0'),
    ),
    NenTang(
        id="kuaishou", ten="Kuaishou", icon="kuaishou", bat=False,
        che_do=_kt("tu_khoa", "link", "kenh"),
        xem_truoc=False, can_dang_nhap=True, cach_dang_nhap="cookie",
        ten_mien=("kuaishou.com",),
        so_luong_toi_da=10, adapter="kuaishou", gioi_han=(),
        cookie_dang_nhap=('passToken', 'kuaishou.server.web_st'),
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
        raise NenKhongHopLe(f"nền không tồn tại: {id!r}") from None


def cac_nen_bat() -> list[NenTang]:
    """Danh sách nền `bat=True`, giữ thứ tự registry — dùng để dựng lưới UI."""
    return [n for n in _NEN if n.bat]


def lay_nen_bat(id: str) -> NenTang:
    """Như `lay`, nhưng ném `NenKhongHopLe` nếu nền chưa `bat` (chưa có adapter/test)."""
    n = _THEO_ID.get(id)
    if n is None or not n.bat:
        raise NenKhongHopLe(f"nền không hợp lệ hoặc chưa bật: {id!r}")
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
