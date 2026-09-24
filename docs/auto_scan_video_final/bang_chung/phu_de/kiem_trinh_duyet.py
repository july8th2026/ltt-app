"""Kiem GUI that (Playwright, Chromium headless) — lan phu-de asv-final.

Chay tren ban co lap `tools/asv_browser_server.py` (CSDL `asv-browser-test`):
    python kiem_trinh_duyet.py <url_goc> <cookie_session> <clip.mp4> <thu_muc_ra>

Lam dung luong khach: chon tep -> video hien -> tua toi giay 3 -> chon preset
cat -> danh dau dai phu de goc -> doi TUNG che do -> bam "Xem truoc" -> doc PNG
may chu tra ve. Ghi `kiem_trinh_duyet.json` canh tep nay: bam PNG moi che do,
loi console, request hong, va trang thai cac o (goi y, nguon chu, kieu).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

GOC_URL, COOKIE, CLIP, RA = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
RA.mkdir(parents=True, exist_ok=True)
DAI = [{"loai": "danh_dau_phu_de", "x0": 0.1, "x1": 0.9, "y0": 0.904, "y1": 0.976}]

ket: dict = {"che_do": {}, "console_loi": [], "request_hong": []}
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")  # Chrome that: co H.264
    ctx = b.new_context(viewport={"width": 1280, "height": 1800},
                          bypass_csp=True)  # CSP cam eval chuoi cua wait_for_function
    ctx.add_cookies([{"name": "session", "value": COOKIE, "url": GOC_URL}])
    pg = ctx.new_page()
    pg.on("console", lambda m: m.type == "error" and ket["console_loi"].append(m.text))
    pg.on("requestfailed", lambda r: ket["request_hong"].append(r.url))
    pg.on("response", lambda r: r.status >= 400 and ket["request_hong"].append(
        f"{r.status} {r.url}"))
    pg.goto(GOC_URL + "/auto-scan-video")
    pg.set_input_files("#asv-video", CLIP)
    pg.wait_for_function("document.getElementById('asv-xem').readyState >= 2")
    pg.evaluate("v => { const e=document.getElementById('asv-xem'); e.currentTime=3; }", None)
    pg.wait_for_function("Math.abs(document.getElementById('asv-xem').currentTime-3)<0.05")
    pg.check("input[name=preset][value=smart_localize]")
    pg.click("details.asv-nang-cao > summary")   # khoi "nang cao" dong san
    ket["nut_xem_bat"] = pg.is_enabled("#asv-phu-de-xem-nut")

    # Goi y khi CHUA danh dau dai (che do tu dong)
    pg.select_option("#asv-phu-de-che-do", "tu_dong")
    pg.click("#asv-phu-de-che-do")
    ket["goi_y_khi_chua_danh_dau"] = pg.is_visible("#asv-phu-de-goi-y")
    # Danh dau dai phu de goc (vung.js ghi o an nay y het)
    pg.evaluate("d => { document.getElementById('asv-vung').value = JSON.stringify(d); }", DAI)
    pg.click("#asv-phu-de-che-do")
    ket["goi_y_sau_khi_danh_dau"] = pg.is_visible("#asv-phu-de-goi-y")

    for che_do in ("tat", "tu_dong", "nguon", "dich", "tu_chon"):
        pg.select_option("#asv-phu-de-che-do", che_do)
        if che_do == "tu_chon":
            pg.select_option("#asv-phu-de-kieu", "tiktok_bold")
            pg.select_option("#asv-phu-de-chu", "nguon")
        truoc = pg.get_attribute("#asv-phu-de-xem-anh", "src") or ""
        with pg.expect_response(lambda r: "/phu-de/xem-truoc" in r.url) as rr:
            pg.click("#asv-phu-de-xem-nut")
        r = rr.value
        pg.wait_for_timeout(1500)   # moi yeu cau (ke ca hen gio 400 ms) da ve
        pg.wait_for_function("!document.getElementById('asv-phu-de-xem-anh').hidden")
        pg.wait_for_function("t => { const i = document.getElementById('asv-phu-de-xem-anh'); return i.src !== t && i.complete; }", arg=truoc)
        # Doc DUNG anh dang hien tren trang (blob cua phan hoi may chu).
        import base64
        png = base64.b64decode(pg.evaluate("""async () => {
            const b = await (await fetch(document.getElementById('asv-phu-de-xem-anh').src)).blob();
            return await new Promise(ok => { const f = new FileReader();
              f.onload = () => ok(f.result.split(',')[1]); f.readAsDataURL(b); });
        }"""))
        (RA / f"{che_do}.png").write_bytes(png)
        pg.locator("#asv-nhom-phu-de").screenshot(path=str(RA / f"o_{che_do}.png"))
        ket["che_do"][che_do] = {
            "http": r.status, "sha256": hashlib.sha256(png).hexdigest()[:16],
            "phu_de_gui": pg.input_value("#asv-phu-de"),
            "o_kieu_hien": pg.is_visible("#asv-phu-de-kieu"),
            "o_nguon_chu_hien": pg.is_visible("#asv-phu-de-chu"),
        }
    ket["so_png_khac_nhau"] = len({v["sha256"] for v in ket["che_do"].values()})
    b.close()

Path(__file__).with_name("kiem_trinh_duyet.json").write_text(
    json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(ket, ensure_ascii=False, indent=1))
