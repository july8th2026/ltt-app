"""Adapter Xiaohongshu (`xhs`): `link` qua yt-dlp; `tu_khoa` + `kenh` qua API web (`xhs_web.py`).

`link` (spec Sec.11, Sec.18, Sec.19, Sec.21): yt-dlp `XiaoHongShuIE` trích MỘT note từ `explore/<id>` hoặc
`discovery/item/<id>`; trang chi tiết BẮT BUỘC có `xsec_token` (donor `W:4495-4513`; `PLATFORM_MATRIX.md` dòng 24).
yt-dlp KHÔNG có extractor search/user cho nền này (`_extractors.py:2489`) — donor đi trình duyệt (W:7016, W:7081).
⇒ `tu_khoa`/`kenh` gọi thẳng API web edith, ký bằng `xhshow` (thuần Python, MIT) TRONG worker, qua bộ mạng của
yt-dlp (`YoutubeDL.urlopen`, cookiejar nạp từ cookies.txt tạm của job). Không trình duyệt. Hai chế độ này đòi phiên
(`a1` + `web_session`); thiếu ⇒ `can_dang_nhap`. Chỉ giữ note loại `video` có `xsec_token` hợp lệ.

RedNote (rednote.com) không dùng adapter này: `XiaoHongShuIE._VALID_URL` chỉ khớp `www.xiaohongshu.com`
(yt-dlp/yt-dlp#16519 mở) ⇒ dòng `rednote` giữ `bat=False`.

Id = note_id (hex 24) — an toàn làm khoá storage (`base.ID_AN_TOAN`). `xsec_token` đi theo URL và được kiểm chặt ở
`url_chuan` (review lần 2); `_sang_item` gắn token lấy từ `webpage_url` (URL gốc đã khám phá) cho chế độ `link`.
"""
from __future__ import annotations

import random
import re
import time
from typing import Any, Callable

from platform_core.i18n import _ as _t

from apps.video_crawler.adapters import xhs_web
from apps.video_crawler.adapters._ytdlp import YtdlpAdapter, _anh_bia, _TrangThai
from apps.video_crawler.adapters.base import (
    BaoTienDo,
    CrawlItem,
    KenhItem,
    LoiCao,
    YeuCauCao,
    YeuCauTimKenh,
    tao_kenh,
)

__all__ = ["XiaohongshuAdapter"]

#: IE_NAME (yt-dlp so `re.fullmatch` voi `IE_NAME.lower()`, YoutubeDL.py:922-929).
EXTRACTOR_CHO_PHEP = ("xiaohongshu",)

#: note_id: hex 24 ky tu (`xiaohongshu.py` `_VALID_URL` dong 14: `[\da-f]+`; 4 id mau quan
#: sat duoc deu dai 24). xsec_token: base64 URL-safe, dai ~44-46 (3 token mau quan sat duoc).
_NOTE = r"[0-9a-f]{24}"
#: xsec_token trong query: base64 URL-safe, có thể %-mã hoá (`=` ⇒ `%3D`). Review lần 2: id KHÔNG mang token
#: (khoá storage cấm `:`), token đi theo URL và được kiểm chặt ở `url_chuan`.
_TOKEN = r"[A-Za-z0-9_=%-]{16,200}"
_ID = re.compile(_NOTE)
_TOKEN_TRONG_URL = re.compile(r"[?&]xsec_token=([^&#]+)")
_USER = r"[0-9a-f]{24}"
#: Trang hồ sơ: `https://www.xiaohongshu.com/user/profile/<user_id>[?xsec_token=…]` hoặc user_id trần.
_URL_KENH = re.compile(rf"https://(?:www\.)?xiaohongshu\.com/user/profile/({_USER})/?(?:[?#].*)?")
#: Trần số trang mỗi lượt khám phá (so_luong_toi_da = 20 ⇒ 1-2 trang là đủ; phần dư cho trang toàn ảnh).
TRANG_TOI_DA = 6
_URL_NOTE = re.compile(rf"https://(?:www\.)?xiaohongshu\.com/(?:explore|discovery/item)/({_NOTE})(?:[?&#].*)?")


def _tach_token(url: str) -> str:
    """Token trong query của URL đã dùng để khám phá ("" khi không có hoặc sai mẫu)."""
    m = _TOKEN_TRONG_URL.search(url or "")
    tok = m.group(1) if m else ""
    return tok if re.fullmatch(_TOKEN, tok) else ""


class XiaohongshuAdapter(YtdlpAdapter):
    nen_tang = "xiaohongshu"
    allowed_extractors = EXTRACTOR_CHO_PHEP                                   # spec Sec.21
    extractor_args = {}                    # khong co extractor_args nao cho nen nay
    ie_key_video = ("XiaoHongShu",)
    impersonate = False        # khong bang chung donor/yt-dlp can impersonate cho xhs

    def __init__(self, ydl_factory: Callable[[dict], Any] | None = None, *, ky: xhs_web.Ky | None = None,
                 ngu: Callable[[float], None] | None = None, **kw: Any):
        super().__init__(ydl_factory, **kw)
        self._ky = ky
        #: Nhịp giữa các trang API (1-2 s, như `sleep_interval_requests` của đường yt-dlp).
        self._ngu = ngu if ngu is not None else (lambda s: time.sleep(s))

    def url_video(self, id: str) -> str:
        return f"https://www.xiaohongshu.com/explore/{id}"

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_chuan(self, id: str, url_goi: str = "") -> str | None:
        """Chỉ nhận URL của ĐÚNG note `id` trên xiaohongshu.com, có xsec_token hợp lệ (bắt buộc — W:4495-4513)."""
        m = _URL_NOTE.fullmatch(str(url_goi or ""))
        tok = _tach_token(url_goi)
        if not self.id_hop_le(id) or m is None or m.group(1) != id or not tok:
            return None
        return f"{self.url_video(id)}?xsec_token={tok}"

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        """"link": URL note khách dán (yt-dlp/`allowed_extractors` tự chặn URL sai). Các chế độ khác: `kham_pha`."""
        return dau_vao

    @staticmethod
    def tach_kenh(dau_vao: str) -> tuple[str, str]:
        """(user_id, xsec_token của trang hồ sơ hoặc "") — sai mẫu ⇒ LoiCao url_khong_ho_tro."""
        vao = (dau_vao or "").strip()
        if re.fullmatch(_USER, vao):
            return vao, ""
        m = _URL_KENH.fullmatch(vao)
        if m is None:
            raise LoiCao("url_khong_ho_tro", _t("Link không được hỗ trợ cho nền tảng này."), tam_thoi=False)
        return m.group(1), _tach_token(vao)

    def url_kenh(self, id: str) -> str:
        """Trang hồ sơ dựng lại từ `user_id` — đúng dạng `tach_kenh` nhận lại khi khách bấm cào.
        Không có `xsec_token` ở đây: token của trang hồ sơ chỉ có khi khách dán link thật, và
        `params_kenh` chấp nhận thiếu token."""
        return f"https://www.xiaohongshu.com/user/profile/{id}"

    # ------------------------------------------------------------ tìm kênh theo TÊN (cần phiên)
    def tim_kenh(self, yeu_cau: YeuCauTimKenh, *, bao_tien_do: BaoTienDo) -> list[KenhItem]:
        """`usersearch` đòi phiên như mọi đường tìm/kênh của nền (spike 23/09: không có đường ẩn danh)."""
        n = max(1, int(yeu_cau.so_luong))
        bao_tien_do(0, _t("đang tìm kênh"))
        opts = self._them_chung(self.tuy_chon_goc(), _TrangThai(bao_tien_do), ghi_tu_choi=False)
        ra: list[KenhItem] = []
        with self._tao(opts) as ydl:
            cookies = xhs_web.cookie_phien(ydl.cookiejar) if self.tep_cookie else {}
            xhs_web.kiem_phien(cookies)
            ky = self._ky if self._ky is not None else xhs_web.KyXhshow()
            search_id = ky.search_id()
            for trang in range(1, TRANG_TOI_DA + 1):
                if trang > 1:
                    self._ngu(random.uniform(1.0, 2.0))
                d = xhs_web.goi(ydl, ky, cookies, "POST", xhs_web.URI_TIM_KENH,
                                payload=xhs_web.payload_tim_kenh(yeu_cau.tu_khoa.strip(), trang, search_id))
                self._them_kenh(ra, d.get("users") or [], n)
                bao_tien_do(min(90, 100 * len(ra) // n), _t("đang tìm kênh"))
                if len(ra) >= n or d.get("has_more") is not True:
                    break
        bao_tien_do(100, _t("tìm thấy {n} kênh").format(n=len(ra)))
        return ra

    def _them_kenh(self, ra: list[KenhItem], users: list, n: int) -> None:
        """Chỉ user_id đúng mẫu hex-24 (khác mẫu ⇒ không dựng được URL hồ sơ), không trùng."""
        for muc in users:
            if len(ra) >= n:
                return
            k = xhs_web.user_tim(muc)
            if k is None or re.fullmatch(_USER, k["id"]) is None or any(k["id"] == x.id for x in ra):
                continue
            it = tao_kenh(self.nen_tang, k["id"], self.url_kenh(k["id"]), ten=k["ten"],
                          anh_dai_dien=k["anh_dai_dien"], so_video=k["so_video"], mo_ta=k["mo_ta"])
            if it is not None:
                ra.append(it)

    def kham_pha(self, yeu_cau: YeuCauCao, *, bao_tien_do: BaoTienDo) -> list[CrawlItem]:
        if yeu_cau.che_do == "link":
            return super().kham_pha(yeu_cau, bao_tien_do=bao_tien_do)
        user = self.tach_kenh(yeu_cau.dau_vao) if yeu_cau.che_do == "kenh" else ("", "")
        n = max(1, int(yeu_cau.so_luong))
        bao_tien_do(0, _t("đang tìm video"))
        opts = self._them_chung(self.tuy_chon_goc(), _TrangThai(bao_tien_do), ghi_tu_choi=False)
        ra: list[CrawlItem] = []
        with self._tao(opts) as ydl:
            cookies = xhs_web.cookie_phien(ydl.cookiejar) if self.tep_cookie else {}
            xhs_web.kiem_phien(cookies)
            ky = self._ky if self._ky is not None else xhs_web.KyXhshow()
            cursor, search_id = "", ky.search_id()
            for trang in range(1, TRANG_TOI_DA + 1):
                if trang > 1:
                    self._ngu(random.uniform(1.0, 2.0))
                    bao_tien_do(min(90, 100 * len(ra) // n), _t("đang tìm video"))
                if yeu_cau.che_do == "kenh":
                    d = xhs_web.goi(ydl, ky, cookies, "GET", xhs_web.URI_KENH,
                                    params=xhs_web.params_kenh(user[0], cursor, user[1]))
                    notes = [xhs_web.note_kenh(m) for m in d.get("notes") or []]
                    cursor = str(d.get("cursor") or "")
                else:
                    d = xhs_web.goi(ydl, ky, cookies, "POST", xhs_web.URI_TIM,
                                    payload=xhs_web.payload_tim(yeu_cau.dau_vao.strip(), trang, search_id))
                    notes = [xhs_web.note_tim(m) for m in d.get("items") or []]
                self._them(ra, notes, n)
                if len(ra) >= n or d.get("has_more") is not True or (yeu_cau.che_do == "kenh" and not cursor):
                    break
        bao_tien_do(100, _t("tìm thấy {n} video").format(n=len(ra)))
        return ra

    def _them(self, ra: list[CrawlItem], notes: list[dict | None], n: int) -> None:
        """Chỉ note VIDEO, id hợp lệ, có xsec_token đúng mẫu (thiếu ⇒ không tải được), không trùng."""
        co = {m.id for m in ra}
        for x in notes:
            if len(ra) >= n:
                return
            if not x or x["loai"] != "video" or not self.id_hop_le(x["id"]) or x["id"] in co:
                continue
            url = self.url_chuan(x["id"], f"{self.url_video(x['id'])}?xsec_token={x['token']}")
            if url is None:
                continue
            co.add(x["id"])
            ra.append(CrawlItem(nen_tang=self.nen_tang, id=x["id"], url=url, tieu_de=x["tieu_de"],
                                tac_gia=x["tac_gia"], anh_bia=x["anh_bia"]))

    def _sang_item(self, e: dict) -> CrawlItem:
        note = str(e.get("id") or "")
        url = self.url_chuan(note, str(e.get("webpage_url") or "")) or self.url_video(note)
        dur = e.get("duration")
        return CrawlItem(
            nen_tang=self.nen_tang, id=note, url=url,
            tieu_de=str(e.get("title") or ""),
            tac_gia=str(e.get("uploader_id") or e.get("uploader") or e.get("channel") or ""),
            thoi_luong_s=int(dur) if isinstance(dur, (int, float)) else None,
            anh_bia=_anh_bia(e),
        )
