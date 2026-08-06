"""
i18n.py — chọn ngôn ngữ và dịch chuỗi (H24).

Hai ngôn ngữ: `vi` (gốc, ở đường dẫn gốc) và `en` (ở tiền tố `/en/`).

## Vì sao tiếng Việt là msgid

`_("Nạp credit")` dùng chính câu tiếng Việt làm khoá, không dùng mã kiểu
`nap.credit.title`. Đổi lại: đọc mã nguồn thấy ngay câu hiện ra, và chuỗi chưa
kịp dịch vẫn hiện tiếng Việt đọc được thay vì hiện một mã trơ như `nap.credit.title`.
Giá phải trả: sửa câu tiếng Việt là mất bản dịch của câu đó — chấp nhận được,
`pybabel update` sẽ chỉ ra chỗ cần dịch lại.

## Thứ tự chọn ngôn ngữ

Dừng ở tầng đầu tiên có kết quả:

1. **Tiền tố đường dẫn** `/en/...` — URL là sự thật cuối cùng, vì link chia sẻ
   phải mở ra đúng ngôn ngữ người gửi thấy.
2. **Người dùng tự chọn** (cookie `ltt_lang`) — lựa chọn tường minh KHÔNG BAO
   GIỜ bị máy đoán ghi đè. Đây là lỗi phổ biến nhất của web đa ngôn ngữ.
3. **Hồ sơ tài khoản** — theo người chứ không theo máy.
4. **`CF-IPCountry`** — `VN` → vi, quốc gia khác → en. Cloudflare gắn sẵn header
   này (IP Geolocation đang bật), nên không cần thư viện GeoIP nào.
5. **`Accept-Language`** — cứu lúc Cloudflare trả `XX` (Tor, VPN, mạng lạ).
6. **Mặc định `en`** — chốt của chủ sản phẩm: khách nước ngoài gặp trang tiếng
   Việt thì không đọc nổi cả nút đổi ngôn ngữ, còn người Việt gặp tiếng Anh vẫn
   bấm đổi được.
"""
from __future__ import annotations

import contextvars
import gettext as _gettext
import os
import pathlib
import re
import threading
from typing import Optional

# ── Hằng ──────────────────────────────────────────────────────────────────────
VI = "vi"
EN = "en"
NGON_NGU = (VI, EN)
MAC_DINH = EN                 # khi không suy ra được gì (xem docstring)
GOC = VI                      # ngôn ngữ của msgid, ở đường dẫn gốc
COOKIE = "ltt_lang"
COOKIE_TUOI = 365 * 24 * 3600

# Nước dùng tiếng Việt. Chỉ có một, nhưng để dạng tập hợp cho khỏi phải sửa cấu
# trúc nếu sau này thêm (vd cộng đồng người Việt ở một thị trường nào đó).
NUOC_VI = frozenset({"VN"})

# ── Đường KHÔNG BAO GIỜ mang tiền tố ngôn ngữ ────────────────────────────────
# Bên ngoài gọi vào các URL này bằng địa chỉ CỐ ĐỊNH đã đăng ký từ trước. Gắn
# tiền tố vào là họ gọi vào chỗ trống — và với webhook thanh toán thì hậu quả là
# khách trả tiền nhưng không nhận credit.
#
# Cùng loại lỗi với `return_url=PLACEHOLDER` (2026-08-06): bên ngoài luôn gọi
# đúng URL ta đưa, kể cả khi URL đó vô nghĩa.
MIEN_TRU = (
    "/webhooks/",       # PayOS gọi — đụng vào là hỏng tiền
    "/health/",         # giám sát + setup/4-nghiem-thu.ps1
    "/static/",
    "/assets/",
    "/favicon",
    "/robots.txt",
    "/sitemap",
    "/oauth/",          # Facebook/TikTok gọi ngược về
    "/api/",            # React gọi bằng đường tuyệt đối
)


def duoc_mien_tru(path: str) -> bool:
    """True nếu đường dẫn không được mang tiền tố ngôn ngữ."""
    p = path if path.startswith("/") else "/" + path
    return any(p == m.rstrip("/") or p.startswith(m) for m in MIEN_TRU)


# ── Tách / ghép tiền tố ──────────────────────────────────────────────────────
_TIEN_TO = re.compile(r"^/(" + "|".join(n for n in NGON_NGU if n != GOC) + r")(/|$)")


def tach_tien_to(path: str) -> tuple[str, Optional[str]]:
    """`/en/nap` → `("/nap", "en")`. `/nap` → `("/nap", None)`.

    Trả `None` chứ không trả `GOC`: nơi gọi cần phân biệt "URL nói rõ tiếng Việt"
    với "URL không nói gì" — cái sau mới được phép đoán tiếp.
    """
    m = _TIEN_TO.match(path or "/")
    if not m:
        return (path or "/"), None
    con_lai = path[len(m.group(1)) + 1:] or "/"
    if not con_lai.startswith("/"):
        con_lai = "/" + con_lai
    return con_lai, m.group(1)


def them_tien_to(path: str, lang: str) -> str:
    """Ghép tiền tố cho đúng ngôn ngữ. Giữ nguyên query string và đường miễn trừ."""
    duong, _ = (path.split("?", 1) + [""])[:2] if "?" in path else (path, "")
    duoi = path[len(duong):]
    duong, _cu = tach_tien_to(duong)
    if lang == GOC or duoc_mien_tru(duong) or duong.startswith(("http://", "https://")):
        return duong + duoi
    return f"/{lang}{'' if duong == '/' else duong}" + duoi


# ── Suy ra ngôn ngữ từ tín hiệu ──────────────────────────────────────────────
def tu_quoc_gia(ma_nuoc: str) -> Optional[str]:
    """`CF-IPCountry` → ngôn ngữ. `XX`/rỗng (không định vị được) → None."""
    ma = (ma_nuoc or "").strip().upper()
    if not ma or ma in ("XX", "T1"):        # T1 = Tor
        return None
    return VI if ma in NUOC_VI else EN


def tu_accept_language(header: str) -> Optional[str]:
    """Đọc `Accept-Language` theo trọng số q. Chỉ quan tâm có tiếng Việt hay không.

    Không dùng thư viện: chuẩn RFC 9110 phần này đủ đơn giản, và thêm phụ thuộc
    chỉ để tách một chuỗi là không đáng.
    """
    if not header:
        return None
    muc = []
    for phan in header.split(","):
        p = phan.strip()
        if not p:
            continue
        ma, _, tham_so = p.partition(";")
        q = 1.0
        for t in tham_so.split(";"):
            t = t.strip()
            if t.startswith("q="):
                try:
                    q = float(t[2:])
                except ValueError:
                    q = 0.0
        muc.append((q, ma.strip().lower()))
    if not muc:
        return None
    for _q, ma in sorted(muc, key=lambda x: -x[0]):
        goc = ma.split("-", 1)[0]
        if goc == VI:
            return VI
        if goc == EN:
            return EN
    return None


def chuan_hoa(lang: Optional[str]) -> Optional[str]:
    l = (lang or "").strip().lower()
    return l if l in NGON_NGU else None


def chon(*, tien_to: Optional[str] = None, cookie: Optional[str] = None,
         ho_so: Optional[str] = None, quoc_gia: str = "",
         accept_language: str = "") -> str:
    """Chọn ngôn ngữ theo đúng thứ tự ưu tiên ở docstring module."""
    for ung_vien in (chuan_hoa(tien_to), chuan_hoa(cookie), chuan_hoa(ho_so)):
        if ung_vien:
            return ung_vien
    return (tu_quoc_gia(quoc_gia)
            or tu_accept_language(accept_language)
            or MAC_DINH)


# ── Bộ dịch ──────────────────────────────────────────────────────────────────
THU_MUC = pathlib.Path(__file__).resolve().parent.parent / "locale"
_bo_dich: dict[str, object] = {}
_khoa = threading.Lock()

# ContextVar chu KHONG threading.local.
#
# Starlette chay endpoint dong bo trong THREADPOOL — mot luong khac han luong
# cua middleware. `threading.local` dat o middleware KHONG toi duoc template, va
# te hon: luong trong pool duoc dung lai, nen trang se hien ngon ngu con sot lai
# tu request TRUOC DO cua nguoi khac. Bug nay im lang va khong deu, rat kho lan.
#
# `contextvars` duoc anyio sao chep sang threadpool nen di dung theo request.
_hien_tai: contextvars.ContextVar[str] = contextvars.ContextVar("ltt_lang", default=MAC_DINH)


def _tai(lang: str):
    """Nạp catalog .mo. Thiếu file → bộ dịch rỗng (trả nguyên tiếng Việt).

    Cố ý KHÔNG ném lỗi: thiếu bản dịch phải làm trang hiện tiếng Việt, không được
    làm sập trang. Bánh cóc trong gate mới là chỗ bắt thiếu sót, không phải lúc chạy.
    """
    with _khoa:
        if lang not in _bo_dich:
            try:
                _bo_dich[lang] = _gettext.translation(
                    "messages", localedir=str(THU_MUC), languages=[lang])
            except FileNotFoundError:
                _bo_dich[lang] = _gettext.NullTranslations()
        return _bo_dich[lang]


def dat_ngon_ngu(lang: str) -> None:
    """Đặt ngôn ngữ cho luồng hiện tại. Middleware gọi mỗi request."""
    _hien_tai.set(chuan_hoa(lang) or MAC_DINH)


def ngon_ngu_hien_tai() -> str:
    return _hien_tai.get()


def xoa_cache() -> None:
    """Quên catalog đã nạp — dùng cho test và sau khi biên dịch lại .mo."""
    with _khoa:
        _bo_dich.clear()


def _(msg: str) -> str:
    """Dịch `msg` sang ngôn ngữ của luồng hiện tại.

    Tiếng Việt là msgid, nên ngôn ngữ gốc trả thẳng về không qua catalog — vừa
    nhanh vừa khỏi phải sinh một file .po dịch tiếng Việt sang tiếng Việt.
    """
    lang = ngon_ngu_hien_tai()
    if lang == GOC:
        return msg
    return _tai(lang).gettext(msg)


def _n(it: str, nhieu: str, n: int) -> str:
    """Dạng số ít/số nhiều. Tiếng Việt không chia số nhiều nên gốc luôn trả `it`,
    nhưng tiếng Anh thì có — nếu không có hàm này thì mọi câu đếm được sẽ sai."""
    lang = ngon_ngu_hien_tai()
    if lang == GOC:
        return it
    return _tai(lang).ngettext(it, nhieu, n)


def da_co_ban_dich(lang: str) -> bool:
    """True nếu có file .mo thật cho ngôn ngữ này. Dùng cho /health và test."""
    return (THU_MUC / lang / "LC_MESSAGES" / "messages.mo").is_file()


def bat_buoc_du_ban_dich() -> bool:
    """Production có được phép chạy khi thiếu .mo không? Mặc định: không chặn."""
    return (os.environ.get("LTT_I18N_BAT_BUOC") or "").strip() == "1"
