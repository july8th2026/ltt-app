r"""
golden_ui_anh_mau.py — screenshot regression cho các màn critical (Golden UI).

    python tools\golden_ui_dev.py --cong 8140            # máy chủ soi, seed mới
    python tools\golden_ui_anh_mau.py --cong 8140          # so với ảnh mẫu
    python tools\golden_ui_anh_mau.py --cong 8140 --cap-nhat   # ghi lại ảnh mẫu

Ảnh mẫu: `tests/visual/golden_ui/<màn>@<rộng>.png` (chỉ khung nhìn, không cả
trang — nhỏ và ổn định). Ảnh lệch: `tmp/golden_ui/anh_lech/`.

## Vì sao không dùng `expect(page).toHaveScreenshot()`

Kho không có `@playwright/test` (không có cấu hình Playwright Test nào), và thêm
một test runner chỉ cho việc này là thêm dependency. Thứ đã có: thư viện
`playwright` (Python) + Pillow (đã là dependency máy chủ). Cùng hai cơ chế cốt
lõi của `toHaveScreenshot`: che vùng dữ liệu động (`mask`) và ngưỡng pixel.

## Dữ liệu động phải che, không phải chấp nhận lệch

Seed dựng lại mỗi lần chạy ⇒ id job, giờ tạo, mã tra cứu đổi. Chúng được che
bằng `mask` theo bộ chọn (`time`, `.tnum`, `.mono`, `code`…) — che ĐÚNG vùng đổi,
không nới ngưỡng cho cả trang. Ngưỡng chỉ để hấp thụ khác biệt khử răng cưa.

⛔ Đây là công cụ ĐO trên máy chủ soi cục bộ, không phải bước của gate: nó cần
   một trình duyệt và một máy chủ đang chạy.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "tools"))

MAU = GOC / "tests" / "visual" / "golden_ui"
LECH = GOC / "tmp" / "golden_ui" / "anh_lech"
KHUNG = (390, 1440)
#: Tỉ lệ điểm ảnh được phép lệch (khử răng cưa chữ). 0,2% của 1440×900 ≈ 2.600 px.
NGUONG = 0.002
#: Một điểm ảnh tính là lệch khi kênh bất kỳ khác quá mức này (0–255).
DUNG_SAI_KENH = 24

CHE_CHUNG = ["time", ".tnum", ".mono", "code", ".ui-state-id", ".job-correlation"]


def man_hinh(ids: dict) -> list[dict]:
    o, j = ids["orders"], ids["jobs"]
    return [
        dict(ten="loi-404", duong="/khong-ton-tai-golden", vai="khach"),
        dict(ten="login", duong="/login", vai=None),
        dict(ten="register", duong="/register", vai=None),
        dict(ten="home-an-danh", duong="/", vai=None),
        dict(ten="home-khach", duong="/", vai="khach",
             che=[".market-rail", "#market-count"]),
        dict(ten="nap", duong="/nap", vai="khach"),
        dict(ten="don-pending", duong=f"/nap/don/{o['pending']}", vai="khach", cho=800),
        dict(ten="don-paid", duong=f"/nap/don/{o['paid']}", vai="khach", cho=800),
        dict(ten="don-expired", duong=f"/nap/don/{o['expired']}", vai="khach", cho=800),
        dict(ten="jobs", duong="/jobs", vai="khach"),
        dict(ten="job-running", duong=f"/jobs/{j['running']}", vai="khach", cho=600,
             che=[".page-sub"]),
        dict(ten="job-error", duong=f"/jobs/{j['error']}", vai="khach", cho=600,
             che=[".page-sub", ".job-lineage .btn"]),
        dict(ten="status", duong="/status", vai="admin"),
        dict(ten="admin-user-list", duong="/admin/user/list", vai="admin",
             che=["tbody td:nth-last-child(-n+2)"]),
    ]


def so_anh(a: pathlib.Path, b: pathlib.Path, ra: pathlib.Path) -> float:
    from PIL import Image, ImageChops

    ia = Image.open(a).convert("RGB")
    ib = Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return 1.0
    diff = ImageChops.difference(ia, ib)
    mask = diff.point(lambda v: 255 if v > DUNG_SAI_KENH else 0).convert("L")
    # "L" gộp ba kênh: một điểm lệch ở bất kỳ kênh nào vẫn > 0 sau convert.
    lech = sum(mask.histogram()[1:])
    ti_le = lech / (ia.size[0] * ia.size[1])
    if lech:
        ra.parent.mkdir(parents=True, exist_ok=True)
        nen = ia.copy()
        do = Image.new("RGB", ia.size, (255, 0, 64))
        nen.paste(do, mask=mask)
        nen.save(ra)
    return ti_le


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cong", type=int, default=8140)
    ap.add_argument("--cap-nhat", action="store_true", help="ghi lai anh mau")
    ap.add_argument("--chi", default="", help="chi man co ten chua chuoi nay")
    a = ap.parse_args(argv)

    import golden_ui_dev
    from playwright.sync_api import sync_playwright

    ids = json.loads((GOC / "tmp" / "golden_ui" / "ids.json").read_text(encoding="utf-8"))
    cookies = {v: golden_ui_dev.lay_cookie(a.cong, v) for v in ("khach", "admin")}
    goc = f"http://127.0.0.1:{a.cong}"
    MAU.mkdir(parents=True, exist_ok=True)
    hong = []
    with sync_playwright() as pw:
        trinh = pw.chromium.launch()
        for m in man_hinh(ids):
            if a.chi and a.chi not in m["ten"]:
                continue
            for w in KHUNG:
                ctx = trinh.new_context(viewport={"width": w, "height": 900 if w > 500 else 844},
                                        device_scale_factor=1, locale="vi-VN",
                                        is_mobile=w < 768, has_touch=w < 768,
                                        reduced_motion="reduce")
                if m["vai"]:
                    ten_ck, gia = cookies[m["vai"]].split("=", 1)
                    ctx.add_cookies([{"name": ten_ck, "value": gia, "domain": "127.0.0.1", "path": "/"}])
                p = ctx.new_page()
                p.goto(goc + m["duong"], wait_until="networkidle")
                if m.get("cho"):
                    p.wait_for_timeout(m["cho"])
                p.evaluate("document.fonts && document.fonts.ready")
                che = [p.locator(s) for s in CHE_CHUNG + m.get("che", [])]
                ten = f"{m['ten']}@{w}.png"
                dich = MAU / ten if a.cap_nhat else LECH / ("moi-" + ten)
                dich.parent.mkdir(parents=True, exist_ok=True)
                p.screenshot(path=str(dich), mask=che, mask_color="#ff00ff", animations="disabled", caret="hide")
                ctx.close()
                if a.cap_nhat:
                    print(f"  [GHI] {ten}")
                    continue
                mau = MAU / ten
                if not mau.exists():
                    hong.append(f"{ten}: CHUA CO anh mau (--cap-nhat)")
                    continue
                tl = so_anh(mau, dich, LECH / ("lech-" + ten))
                trang = "OK " if tl <= NGUONG else "LECH"
                print(f"  [{trang}] {ten:28} {tl * 100:.3f}%")
                if tl > NGUONG:
                    hong.append(f"{ten}: {tl * 100:.3f}% > {NGUONG * 100:.2f}%")
        trinh.close()
    if a.cap_nhat:
        print(f"RESULT: GHI anh mau -> {MAU}")
        return 0
    print("RESULT:", "PASS" if not hong else "FAIL")
    for h in hong:
        print("  -", h)
    return 0 if not hong else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
