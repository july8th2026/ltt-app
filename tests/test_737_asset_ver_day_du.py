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


# ══════════════════════════════════════════════════════════════════════════
#  Xem truoc tep dinh kem phai KHOP CSP
#
#  🔴 Loi that 07/09. Ban dau dung `URL.createObjectURL` (=> `blob:`) cho CA
#     anh lan video. CSP o `server/app.py` cho phep:
#
#         img-src   'self' data:  https://*.r2...      (KHONG co blob:)
#         media-src 'self' blob:  https://*.r2...      (CO blob:)
#
#     ⇒ Trinh duyet CHAN anh. DOM van co the <img> voi `src` dung, nen mot phep
#       kiem cau truc van XANH — that bai chi hien o console, va chi khi mo
#       trinh duyet that.
#
#  ⭐ Nen phep kiem duoi day do CO CHE (dung ham nao cho loai nao), chu khong do
#     su ton tai cua the.
# ══════════════════════════════════════════════════════════════════════════

def _js_khong_chu_thich() -> str:
    """JS đã **bỏ chú thích**.

    🔴 Đây là lần thứ ba trong một ngày một bộ dò quét văn bản ở kho này báo
       động trên chính đoạn giải thích nó. Hai lần trước: một chú thích nhắc
       `t2v_2_2` làm đỏ phép kiểm "route không chứa quy tắc giá", và một chú
       thích nhắc `nhan_vien` suýt làm đỏ phép kiểm từ vựng.

    ⇒ Quét **mã**, đừng quét **lời**. Ở Python thì đọc AST; ở JS không có AST
      sẵn nên bỏ chú thích trước đã — rẻ và đủ cho việc này.
    """
    import re as _re

    js = (STATIC / "lttvideo.js").read_text(encoding="utf-8")
    js = _re.sub(r"/\*.*?\*/", "", js, flags=_re.S)      # /* ... */
    js = _re.sub(r"(?m)//.*$", "", js)                    # // ...
    return js


def _khoi_xem_truoc() -> str:
    js = _js_khong_chu_thich()
    return js.split("input[type=file][name=media]", 1)[1].split(
        "oDoDai", 1)[0]


def test_anh_dung_FileReader_chu_KHONG_dung_blob():
    """`img-src` không cho `blob:`. Dùng `createObjectURL` cho ảnh là dựng một
    ô xem trước không bao giờ hiện — và DOM vẫn trông đúng."""
    khoi = _khoi_xem_truoc()
    nhanh_anh = khoi.split("} else {", 1)[1].split("var ten", 1)[0]
    assert "FileReader" in nhanh_anh
    assert "createObjectURL" not in nhanh_anh, (
        "nhanh anh dung blob: — CSP `img-src` se chan no")


def test_video_dung_createObjectURL_vi_media_src_CHO_PHEP_blob():
    khoi = _khoi_xem_truoc()
    nhanh_video = khoi.split("if (la_video) {", 1)[1].split("} else {", 1)[0]
    assert "createObjectURL" in nhanh_video


def _chi_thi_csp(ten: str) -> str:
    """Chỉ thị CSP thật, lấy từ **hằng chuỗi**, không lấy từ chú thích.

    ⚠️ `server/app.py` có một chú thích nhắc "media-src/connect-src" NGAY TRƯỚC
       khối chính sách. Tách thô trên tên chỉ thị sẽ bắt vào chú thích đó.
    """
    import re as _re

    ma = (GOC / "server" / "app.py").read_text(encoding="utf-8")
    m = _re.search(r'"' + _re.escape(ten) + r'\s+([^"]*)"', ma)
    assert m, f"khong tim thay chi thi {ten} trong hang chuoi"
    return m.group(1)


def test_CSP_van_dung_nhu_gia_dinh_o_tren():
    """⭐ Sự thật độc lập. Nếu ai đó thêm `blob:` vào `img-src` — hoặc bỏ nó
    khỏi `media-src` — thì giả định của tệp này sai, và phép kiểm phải đỏ để
    người sửa biết đường xem lại, thay vì để mã trôi khỏi chính sách."""
    img = _chi_thi_csp("img-src")
    media = _chi_thi_csp("media-src")
    assert "data:" in img, "img-src khong con cho data: — xem truoc anh se vo"
    assert "blob:" not in img, (
        "img-src nay CHO blob: — co the don gian hoa xem truoc anh")
    assert "blob:" in media, "media-src khong con cho blob: — xem truoc video vo"


def test_tu_kiem_bo_tach_chi_thi_CSP():
    """⛔ Đối chứng cho chính bộ tách trên: nó phải lấy được chỉ thị thật, và
    chỉ thị ấy phải bắt đầu bằng `'self'` như mọi chỉ thị trong tệp."""
    assert _chi_thi_csp("img-src").startswith("'self'")
    assert _chi_thi_csp("media-src").startswith("'self'")


def test_giai_phong_blob_khi_roi_trang():
    """Một `createObjectURL` không `revoke` giữ nguyên tệp trong RAM tới khi
    đóng tab."""
    khoi = _khoi_xem_truoc()
    assert "revokeObjectURL" in khoi
    assert "beforeunload" in khoi
