"""Mọi static đính `?v={{ asset_ver }}` phải **thật sự** nằm trong sổ băm.

🔴 Lỗi thật, tự tôi gây ra ngày 07/09. Thêm `server/static/lttvideo.js`, đính
   `?v={{ asset_ver }}` vào link, và tin là đã cache-bust. Nhưng `asset_ver` băm
   một **tuple gõ tay** (`templating.TAI_SAN_CO_VERSION`) và tệp mới không có
   trong đó — nên hash **không đổi khi tệp đổi**.

⭐ Vì sao nó nguy hiểm hơn quên hẳn `?v=`: link **trông đã đúng**. Không ai soi
   lại một thứ đã có vẻ được xử lý. Sau deploy, Cloudflare phục vụ bản JS **cũ**
   cho tới khi hết TTL, trang vẫn render đẹp, và không có lỗi nào ở đâu cả.

   ⇒ Đúng sự cố `CLAUDE.md` mục 6 ghi lại (`ltt.css` cũ phục vụ 4 tiếng, chip
     hiện thành radio thô), chỉ khác là lần này **im lặng hơn**.

📌 Phép kiểm này quét NGƯỢC: đi từ template ra, tìm mọi tệp static được đính
   version, rồi đòi từng tệp phải có mặt trong sổ. Quét xuôi (đọc sổ rồi kiểm
   tệp tồn tại) **không** bắt được lỗi này — sổ thiếu thì nó không có gì để
   kiểm, và nó xanh.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
STATIC = GOC / "server" / "static"

#: `<đường-dẫn>?v={{ asset_ver }}` — chỉ bắt tệp trong `/static/`, không bắt
#: bundle của Vite (chúng cache-bust bằng chính TÊN TỆP, cơ chế khác).
_KHUON = re.compile(r'/static/([A-Za-z0-9_.\-]+)\?v=\{\{\s*asset_ver\s*\}\}')


def _template():
    for goc in (GOC / "server" / "templates", GOC / "apps"):
        yield from goc.rglob("*.html")


def _tai_san_duoc_dinh_version() -> dict[str, list[str]]:
    """`{ten_tep: [template nhac toi no]}`."""
    ra: dict[str, list[str]] = {}
    for tep in _template():
        for ten in _KHUON.findall(tep.read_text(encoding="utf-8")):
            ra.setdefault(ten, []).append(str(tep.relative_to(GOC)))
    return ra


def test_co_it_nhat_mot_tai_san_duoc_dinh_version():
    """⛔ Đối chứng cho chính khuôn regex trên. Nếu nó ngừng khớp — ai đó đổi
    cách viết link — thì mọi phép kiểm dưới đây xanh vĩnh viễn mà không canh gì.
    """
    assert _tai_san_duoc_dinh_version(), (
        "khuon regex khong con khop link nao — phep kiem nay da chet")


def test_moi_tai_san_dinh_version_deu_nam_trong_so_bam():
    """🔑 Phép kiểm trung tâm. Thiếu một tên ở đây = một tệp không bao giờ
    cache-bust, và không ai biết."""
    from server.templating import TAI_SAN_CO_VERSION

    thieu = {ten: noi for ten, noi in _tai_san_duoc_dinh_version().items()
             if ten not in TAI_SAN_CO_VERSION}
    assert not thieu, (
        "tep dinh `?v=asset_ver` nhung KHONG nam trong TAI_SAN_CO_VERSION, nen "
        f"hash cua no khong bao gio doi: {thieu}")


@pytest.mark.parametrize("ten", [
    pytest.param(t, id=t) for t in
    __import__("server.templating", fromlist=["x"]).TAI_SAN_CO_VERSION])
def test_moi_tep_trong_so_deu_CO_THAT(ten):
    """Thiếu một tệp thì `_tinh_asset_ver()` nuốt lỗi và trả hằng `"0"` — và từ
    đó **mọi** tài sản mất cache-bust, không riêng tệp thiếu."""
    assert (STATIC / ten).is_file(), f"{ten} khong ton tai trong server/static/"


def test_hash_DOI_khi_mot_tai_san_doi(tmp_path, monkeypatch):
    """⭐ Đo tính chất, không đo cách viết: sửa một byte của một tài sản thì
    `asset_ver` phải ra khác. Đây là thứ mà phép kiểm "tệp có tồn tại không"
    hoàn toàn bỏ lọt."""
    import server.templating as tp

    gia = tmp_path / "static"
    gia.mkdir()
    for ten in tp.TAI_SAN_CO_VERSION:
        (gia / ten).write_bytes(b"noi dung goc")

    monkeypatch.setattr(tp, "_STATIC_DIR", gia)
    truoc = tp._tinh_asset_ver()

    (gia / tp.TAI_SAN_CO_VERSION[-1]).write_bytes(b"noi dung DA DOI")
    sau = tp._tinh_asset_ver()

    assert truoc != sau, ("doi noi dung mot tai san ma hash khong doi — "
                          "cache-bust khong hoat dong")


def test_lttvideo_js_nam_trong_so():
    """Chốt riêng cho tệp đã gây ra lỗi này, để nó không lặng lẽ rơi ra."""
    from server.templating import TAI_SAN_CO_VERSION

    assert "lttvideo.js" in TAI_SAN_CO_VERSION
