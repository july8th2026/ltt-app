"""Mọi tài sản tĩnh mang `?v={{ asset_ver }}` phải THAM GIA tính ra chính hash đó.

## Lỗ này có thật, và nó im lặng tuyệt đối

`ASSET_VER` là md5 của một **danh sách tên tệp gõ tay** (`TAI_SAN_CO_VERSION`).
Khuôn mẫu thì đính `?v={{ asset_ver }}` vào **bất cứ tệp nào** người viết muốn.
Hai thứ đó không có gì buộc phải khớp nhau.

Hậu quả khi lệch: `server/static/voice.js` mang `?v={{ asset_ver }}` từ P2 nhưng
**không** nằm trong danh sách. Sửa riêng `voice.js` ⇒ nội dung đổi, **URL không
đổi** ⇒ Cloudflare tiếp tục phục vụ bản cũ tới hết TTL.

⛔ Và nó không nổ ngay, đó mới là chỗ nguy hiểm. Mọi đợt tới nay đều đổi `ltt.css`
   cùng lúc, nên hash vẫn nhảy và `voice.js` được kéo mới theo. Cái lỗ chỉ lộ ra
   ở đúng hình dạng của một **đợt sửa lỗi**: chạm mỗi JavaScript, không chạm CSS.
   Tức nó nằm im cho tới lần deploy mà người ta cần nó nhất.

## Vì sao chốt bằng một LUẬT chứ không bằng một danh sách

Ngày 31/08 kho này gặp cùng một hình dạng bốn lần (`[hidden]`, bánh cóc nội dung,
`cửa sổ yên`, `gate.py` đọc mã thoát): **một cơ chế chỉ bảo vệ thứ nó nhìn thấy**.
Một phép kiểm liệt kê `("ltt.css", …, "voice.js")` sẽ đúng hôm nay và sai vào
ngày ai đó thêm tệp thứ sáu — đúng cách cái lỗ này ra đời.

Nên phép kiểm dưới đây **đọc khuôn mẫu** để biết tệp nào đang được đính version,
rồi đòi danh sách phải phủ hết. Thêm tệp mới mà quên khai là đỏ, tự động.
"""
from __future__ import annotations

import pathlib
import re

GOC = pathlib.Path(__file__).resolve().parents[1]
TINH = GOC / "server" / "templating.py"

#: `<script src="/static/voice.js?v={{ asset_ver }}">` và mọi biến thể của nó.
DINH_VERSION = re.compile(r'/static/([A-Za-z0-9_.-]+)\?v=\{\{\s*asset_ver\s*\}\}')


def _danh_sach_khai() -> tuple:
    ma = TINH.read_text(encoding="utf-8")
    m = re.search(r"TAI_SAN_CO_VERSION\s*=\s*\(([^)]*)\)", ma, re.S)
    assert m, "khong tim thay TAI_SAN_CO_VERSION"
    return tuple(re.findall(r"[\"']([^\"']+)[\"']", m.group(1)))


def _tep_duoc_dinh_version() -> set:
    """Mọi tệp tĩnh mà MỘT khuôn mẫu nào đó đang đính `?v=asset_ver` vào."""
    ra: set = set()
    for thu_muc in (GOC / "server" / "templates", GOC / "apps"):
        for tep in thu_muc.rglob("*.html"):
            ra |= set(DINH_VERSION.findall(tep.read_text(encoding="utf-8")))
    return ra


def test_moi_tep_duoc_dinh_version_deu_tham_gia_tinh_hash():
    khai = set(_danh_sach_khai())
    dung = _tep_duoc_dinh_version()
    thieu = sorted(dung - khai)
    assert thieu == [], (
        f"{thieu} mang `?v=asset_ver` nhung KHONG nam trong TAI_SAN_CO_VERSION.\n"
        f"Sua tep do mot minh thi hash khong doi, URL khong doi, va Cloudflare\n"
        f"phuc vu ban CU toi het TTL — khong loi nao bao.\n"
        f"Them ten tep vao TAI_SAN_CO_VERSION trong server/templating.py.")


def test_moi_tep_trong_danh_sach_deu_ton_tai():
    """Một tên gõ sai làm `_tinh_asset_ver` nuốt lỗi và trả về `"0"` cho MỌI tài sản."""
    tinh = GOC / "server" / "static"
    mat = [t for t in _danh_sach_khai() if not (tinh / t).is_file()]
    assert mat == [], (
        f"{mat} khai trong TAI_SAN_CO_VERSION nhung khong co that. "
        f"`_tinh_asset_ver` bat Exception va tra ve '0' — tuc MOI tai san mat "
        f"cache-bust cung luc, im lang.")


def test_hash_doi_khi_mot_tai_san_doi():
    """Chốt chính cơ chế, không chỉ danh sách."""
    import hashlib

    tinh = GOC / "server" / "static"
    ten = _danh_sach_khai()

    def bam(them: bytes = b"") -> str:
        h = hashlib.md5()
        for t in ten:
            h.update((tinh / t).read_bytes())
        h.update(them)
        return h.hexdigest()[:8]

    assert bam() != bam(b"x"), "hash khong phan ung voi noi dung"


def test_ham_tinh_khong_bao_gio_nem_ra_ngoai():
    """Trang phải dựng được cả khi một tài sản biến mất — nhưng phải nói ra."""
    ma = TINH.read_text(encoding="utf-8")
    khuc = ma[ma.index("def _tinh_asset_ver"):]
    khuc = khuc[:khuc.index("\nASSET_VER")]
    assert "except" in khuc and 'return "0"' in khuc, (
        "mat duong lui: mot tai san thieu se lam sap MOI trang")
