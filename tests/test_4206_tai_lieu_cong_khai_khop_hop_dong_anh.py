"""test_4206 - tai lieu CONG KHAI phai khop hop dong anh DANG CUONG CHE.

## 🔴 Vi sao tep nay ton tai

Do 28/09/2026: `docs/PUBLIC_API/DEVELOPER_GUIDE.md` muc "Gioi han" ghi
**`Body JSON | 256 KiB`** trong khi tran that da qua BON lan nang
(256 KiB -> 1 MiB -> 2 MiB -> 4 MiB -> 32 MiB). Tai lieu cong khai sai **128 lan**,
va khong phep kiem nao bat.

⛔ Do khong phai mot loi go sai. Do la lop loi "hai cho khai mot dieu ma khong ai
   bat khop" - cung lop voi `max_image_bytes = 12 MiB` tung duoc CONG BO trong
   sau tuan ma khong request nao dat toi. Cai gia cua no la THAT: mot khach thiet
   ke theo `256 KiB` tu gioi han minh xuong 1/128 thu duoc phep, va khong co gi
   noi cho ho biet.

## ⛔ Vi sao KHONG doi sang bo sinh tu dong

`tools/build_public_api_docs.py` sinh phan CONG CU tu catalog, nhung bang gioi han
la van xuoi co giai thich - sinh no ra se mat phan giai thich, ma phan giai thich
chinh la thu day khach ĐOC HEADER thay vi chep con so. Nen: van xuoi viet tay,
va tep nay la nguoi canh.

## Bat bien

1. So trong tai lieu == hang dang chay (`DEFAULT_MAX_BODY_BYTES`).
2. Tai lieu phai DAY khach doc header, khong chi ghi mot con so.
3. Bon truong moi cua hop dong anh phai co ten trong tai lieu.
4. Bang doi chieu token anh trong tai lieu phai khop phep tinh THAT.
"""
from __future__ import annotations

import pathlib

import pytest

from apps.ltt_llm.ngan_sach import TOKEN_ANH_TOI_DA, TOKEN_ANH_TOI_THIEU
from platform_core.llm import anh_token as AT
from platform_core.public_api.config import DEFAULT_MAX_BODY_BYTES
from platform_core.public_api.protocol import HEADER_MAX_BODY_BYTES

HUONG_DAN = (pathlib.Path(__file__).resolve().parent.parent
             / "docs" / "PUBLIC_API" / "DEVELOPER_GUIDE.md")


@pytest.fixture(scope="module")
def van() -> str:
    return HUONG_DAN.read_text(encoding="utf-8")


def test_so_tran_than_trong_tai_lieu_khop_hang_dang_chay(van):
    """⭐ Bat bien chinh. Doi `DEFAULT_MAX_BODY_BYTES` ma quen tai lieu => DO."""
    assert str(DEFAULT_MAX_BODY_BYTES) in van, (
        f"tai lieu khong noi con so {DEFAULT_MAX_BODY_BYTES} - no da muc lai. "
        f"Lan truoc no ghi 256 KiB trong khi tran that la 32 MiB (sai 128x).")
    mib = DEFAULT_MAX_BODY_BYTES // (1024 * 1024)
    assert f"{mib} MiB" in van, f"tai lieu khong noi '{mib} MiB'"


def test_tai_lieu_DAY_khach_doc_header_chu_khong_chi_ghi_so(van):
    """Mot con so trong tai lieu se muc; mot header thi khong.

    ⛔ Thieu phep nay thi phep tren van xanh khi ai do chi cap nhat con so va
       bo mat cau huong dan - va lan nang tran ke tiep lai tao ra dung mot khach
       thiet ke theo con so cu.
    """
    assert HEADER_MAX_BODY_BYTES in van, (
        f"tai lieu khong bao khach doc header {HEADER_MAX_BODY_BYTES}")


def test_bon_truong_hop_dong_anh_co_trong_tai_lieu(van):
    for ten in ("image_pixels_per_token", "min_image_tokens",
                "max_image_tokens", "image_token_markers",
                "accepted_image_schemes"):
        assert ten in van, (
            f"`{ten}` duoc CONG BO ra /api/v1/models ma tai lieu khong noi - "
            f"khach khong hoc duoc no o dau")


def test_tai_lieu_KHONG_con_hua_tran_dem_anh(van):
    """`max_images` da go 28/09 (C4). Tai lieu hua lai la hua mot dieu khong ai cuong che."""
    assert "max_images" not in van, "tai lieu con hua `max_images`"


@pytest.mark.parametrize(("rong", "cao"), [
    (320, 240), (512, 512), (1024, 768), (1280, 720),
    (1920, 1080), (2048, 2048), (3840, 2160),
])
def test_bang_doi_chieu_trong_tai_lieu_khop_phep_tinh_THAT(van, rong, cao):
    """Bang trong tai lieu la so DO. Phai khop phep tinh, khong chi "co mat".

    🔴 BAN DAU PHEP NAY RONG, va mot phep DOT BIEN bat duoc.

       Ban dau tim `str(that)` tren BAT KY dong nao chua `{rong}×{cao}`, roi
       `any(...)`. Doi `| 3840×2160 | 4 082 |` thanh `4 098` trong bang => phep
       van XANH, vi cau van xuoi ngay duoi bang ("`3840×2160` cho **4 082**,
       khong phai 4 098") cung chua ca hai chuoi va thoa `any`.

       ⇒ Phep kiem xanh vi mot dong KHAC voi dong no tuong minh dang doc. Nay no
         ghim DUNG O BANG, tung ky tu.
    """
    that = AT.token_anh(rong, cao, toi_thieu=TOKEN_ANH_TOI_THIEU,
                        toi_da=TOKEN_ANH_TOI_DA) + AT.TOKEN_DAU_VISION
    # Tai lieu ghi dau cach nghin: 4082 -> "4 082".
    so = f"{that:,}".replace(",", " ").replace(" ", " ")
    o = f"| {rong}×{cao} | {so} |"
    assert o in van, (
        f"khong thay DUNG o bang {o!r}. Tai lieu phai ghi {that} token cho anh "
        f"{rong}x{cao} (so DO tren production 28/09, ⛔ dung sua bang cho xanh).")
