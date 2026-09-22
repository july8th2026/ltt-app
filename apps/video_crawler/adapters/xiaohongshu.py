"""Adapter Xiaohongshu (`xhs`) qua yt-dlp (spec Sec.11, Sec.18, Sec.19, Sec.21).

Chi ho tro CHE_DO = {"link"} (mot note/chi tiet). Day la GIAO cua donor va yt-dlp
2026.03.17 dang cai, khong phai lua chon tuy y:
- Donor: search/creator (tu_khoa/kenh) cua XHS/RedNote di **trinh duyet**, khong qua
  `main.py`/yt-dlp (`AUDIT_VIRAL_CAO_NGAY.md` Sec.0 dong 21: `_xhs_creator_browser_worker`
  `W:7016`, `_xhs_tai_links_worker` `W:7081`). Trang chi tiet BAT BUOC co `xsec_token`
  (`W:4495-4513`; `PLATFORM_MATRIX.md` dong 24, cot `link`: "bat buoc co xsec_token").
- yt-dlp: `yt_dlp/extractor/xiaohongshu.py:13-41` chi co MOT extractor `XiaoHongShuIE`,
  trich MOT note tu `explore/<id>` hoac `discovery/item/<id>` — KHONG co extractor
  search/user cho xiaohongshu (`_extractors.py:2489` chi mot dong import cho nen nay).
=> Giao = {"link"}. Dieu phoi can sua `che_do` cua dong `xiaohongshu`/`rednote` trong
`nen_tang.py` (hien khai tam `_kt("tu_khoa", "link", "kenh")`) thanh chi `_kt("link")` —
hai che do con lai khong co yt-dlp thuc dung sau.

RedNote (rednote.com, quoc te) KHONG dung duoc adapter nay, cung khong dung duoc BAT KY
adapter yt-dlp nao voi ban cai 2026.03.17:
- `XiaoHongShuIE._VALID_URL` (`xiaohongshu.py:14`) chi khop domain `www.xiaohongshu.com`;
  khong co class `Rednote*IE`/chuoi "rednote" nao trong ma yt-dlp da cai (kiem bang grep
  toan bo site-packages/yt_dlp — khong co ket qua).
- yt-dlp/yt-dlp#16519 (issue MO, tao 2026-04-19, nhan "site-bug"): nguoi dung xac nhan XHS
  da doi domain hien thi sang rednote.com o mot so khu vuc; ho phai TU sua ma nguon cuc bo
  (doi moi `xiaohongshu` -> `rednote`) va tu compile de tai duoc — tuc ban yt-dlp CHINH THUC
  chua ho tro rednote.com.
=> Hai dong registry `xhs`/`rednote` (`PLATFORM_MATRIX.md` dong 24-25) khong the dung chung
MOT adapter cho toi khi #16519 duoc vá; dong `rednote` nen giu `bat=False`.

Thiet ke id chong gia mao (rang buoc: `url_video(id)` dung lai URL tai tu id, KHONG tin URL
khach gui — xem `NenTang.mau_url` docstring trong `nen_tang.py`): donor xac nhan trang chi
tiet BAT BUOC `xsec_token` kem theo, va yt-dlp KHONG dua token nay vao info_dict tra ve
(`xiaohongshu.py` khong co truong token trong return cua `_real_extract`) — token chi song
trong CHINH url request (`YoutubeDL.py:1861` gan `webpage_url = url` goc). Vi vay id o day
mang CA HAI phan, `"<note_id>:<xsec_token>"`:
- `note_id`: hex 24 ky tu — dung voi ca 4 id mau quan sat duoc (`xiaohongshu.py` `_TESTS`
  dong 17, 30; issue #16519 va #13728 trich dan o tren) deu dai 24 ky tu hex thuong.
- `xsec_token`: base64 URL-safe (chu, so, `_`, `-`, dem `=`) — dung voi 3 token mau quan
  sat duoc (cung cac nguon tren), dai ~44-46 ky tu.
`id_hop_le` cho ca dang "note thuan" (yt-dlp tra `info["id"]` chi la note, dung o vong loc
`kham_pha` trong `_ytdlp.py` — file dung chung, KHONG duoc sua) VA dang day du "note:token"
(dung cho `CrawlItem.id` sau khi da di qua `_sang_item`, dung lai o `tai()`). `url_video`
tach theo dau `:` DAU tien; thieu token van dung lai duoc URL (khong loi), nhung note thuan
khong the tai duoc noi dung yeu cau dang nhap/token — day la gioi han cua chinh XHS, khong
phai lo hong: id khong con "note thuan" khong cho doi sang playlist/kenh nao khac, chi thieu
token cua CHINH note do.

Ghi de `_sang_item` (dinh nghia trong subclass nay, KHONG sua `_ytdlp.py`) de gan token lay
tu `webpage_url` (URL goc da dung de kham pha) vao `CrawlItem.id`/`url` — day la ky thuat duy
nhat de gan diem thiet ke tren voi hop dong `PlatformAdapter` (chi override cac hook da liet
trong brief: `url_video`, `id_hop_le`, `url_kham_pha`; `_sang_item` la mot hook noi bo cua
`YtdlpAdapter`, khong phai mot phan hop dong cong khai, nhung viec ghi de no van chi cham vao
tep cua LANE nay).
"""
from __future__ import annotations

import re
from typing import Any

from apps.video_crawler.adapters._ytdlp import YtdlpAdapter, _anh_bia
from apps.video_crawler.adapters.base import CrawlItem

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
_URL_NOTE = re.compile(rf"https://(?:www\.)?xiaohongshu\.com/(?:explore|discovery/item)/({_NOTE})(?:[?&#].*)?")


def _tach_token(url: str) -> str:
    """Token trong query của URL đã dùng để khám phá ("" khi không có hoặc sai mẫu)."""
    m = _TOKEN_TRONG_URL.search(url or "")
    tok = m.group(1) if m else ""
    return tok if re.fullmatch(_TOKEN, tok) else ""


class XiaohongshuAdapter(YtdlpAdapter):
    nen_tang = "xiaohongshu"
    allowed_extractors = EXTRACTOR_CHO_PHEP                                   # spec Sec.21
    extractor_args: dict = {}                    # khong co extractor_args nao cho nen nay
    ie_key_video = ("XiaoHongShu",)
    impersonate = False        # khong bang chung donor/yt-dlp can impersonate cho xhs

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
        """Chi "link": URL note nguoi dung dan (yt-dlp/`allowed_extractors` tu chan URL sai)."""
        return dau_vao

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
