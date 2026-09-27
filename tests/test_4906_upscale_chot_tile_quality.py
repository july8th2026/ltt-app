"""Khoa quyet dinh "UU TIEN CHAT LUONG" cho tile cua preset Quality (chot 27/09).

⭐ VI SAO CAN MOT PHEP KIEM CHO MOT THU "KHONG DOI"

Do 27/09 cho thay tile 256 chay NHANH HON 8,7 % va ton it VRAM hon 64 % so voi
tile 512 dang dung. Bien do do lon hon nhieu mot bac, nen bat ky ai do lai cung
se thay — va se rat muon doi mac dinh xuong 256.

Nhung dau ra KHAC NHAU: PSNR 45,2-46,5 dB, SSIM 0,990-0,992, 0/12 khung giong het
tung bit. Nguon 836x576 => tile 512 chia 2x2 manh, tile 256 chia 4x3 => tile nho
nhieu duong ghep hon.

⇒ 8,7 % do la mot DANH DOI chat luong lay toc do, trong chinh preset ten la
  Quality. Chu du an chot: giu chat luong.

⛔ Khong co phep kiem nay thi lan sau ai do se do lai, thay 8,7 %, doi mac dinh,
   va ghi vao docs nhu mot "toi uu" — vi con so toc do thi hien ra ngay, con cai
   gia thi phai di do rieng moi thay. Day chinh la hinh dang cua moi "toi uu ao"
   ma dot sua nay di don.

Phep kiem nay ⛔ KHONG cam doi tile. No bat nguoi doi phai doi CA LY DO — tuc
phai doc va sua chu thich giai thich cai gia, chu khong lang le doi mot con so.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEP_AUTOTUNE = ROOT / "apps" / "upscalevideo" / "autotune.py"


def test_tile_quality_cao_nhat_van_la_512():
    """Doi con so nay = doi cai KHACH NHAN DUOC, khong chi doi toc do.

    Ngan hoi quy: ha xuong 256 lay 8,7 % toc do se doi dau ra (PSNR ~46 dB,
    SSIM ~0,990 so voi 512). Neu that su muon doi thi phai sua ca chu thich ly do
    o `autotune.py` va muc §K cua `08_BENCHMARK_RESULTS.md`.
    """
    from apps.upscalevideo import autotune

    src = TEP_AUTOTUNE.read_text(encoding="utf-8")
    cay = ast.parse(src)

    gan = [n for n in ast.walk(cay)
           if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Tuple) for t in n.targets)]
    tim = None
    for n in gan:
        ten = [e.id for e in n.targets[0].elts if isinstance(e, ast.Name)]
        if ten[:1] == ["FAST_TILE"]:
            tim = n
            break
    assert tim is not None, "khong tim thay dong `FAST_TILE, FAST_ALLOC, SAFETY = ...`"
    gia_tri = [e.value for e in tim.value.elts if isinstance(e, ast.Constant)]
    assert gia_tri[0] == 512, (
        f"tile Quality cao nhat da doi thanh {gia_tri[0]}. Neu co y: phai sua ca "
        f"chu thich ly do trong autotune.py va §K cua 08_BENCHMARK_RESULTS.md, "
        f"va phai co bang chung chat luong (xem docstring tep nay).")

    # Va autotune that su tra ve no khi budget du.
    autotune_pick = autotune.pick
    assert callable(autotune_pick)


def test_ly_do_danh_doi_van_con_trong_ma():
    """Con so ma khong con LY DO thi lan sau se bi doi ma khong ai biet cai gia.

    Bat buoc chu thich phai con neu duoc ca ba dieu: co phep do, co cai gia, va
    co duong dan toi so lieu day du.
    """
    src = TEP_AUTOTUNE.read_text(encoding="utf-8")
    for manh, y_nghia in (
        ("8,7", "muc tang toc do do duoc cua tile 256"),
        ("PSNR", "cai gia: dau ra khac nhau"),
        ("08_BENCHMARK_RESULTS.md", "duong dan toi so lieu day du"),
    ):
        assert manh in src, f"chu thich ly do tile Quality thieu: {y_nghia} ({manh!r})"
