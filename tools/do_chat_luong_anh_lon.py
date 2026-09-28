"""do_chat_luong_anh_lon.py - chat luong doc o ANH LON theo do phan giai (D-7).

## Cau hoi duy nhat

Client LTTCODE cat moi anh ve <= 2048x2048 = **4.098 token**. Tai lieu Qwen khuyen
dai **256-1280** token/anh ("to balance performance and cost"), va cookbook OCR
chinh thuc dat max = 2048. Tuc ta dang o **3,2 lan** tran tai lieu.

Ha `IMAGE_BUDGET.maxPixels` cua client (hoac `--image-max-tokens`) se ha chi phi
anh lon MOT NUA. Nhung no chi dung neu chat luong KHONG giam.

⛔ Bai do D-5 chi do ANH NHO. Ha tran anh lon ma dua tren D-5 la dung lop loi da
   sua o D-5 (lay mot phep do tra loi mot cau hoi KHAC), chi doi chieu.

## Cach do

Mot anh DAY DAC: luoi ma 6 ky tu, du nhieu de do phan giai thuc su quyet dinh.
Render MOT LAN o co lon nhat roi THU NHO xuong cac co can do - dung cach client
thu nho anh that, va giu nguyen noi dung.

Cham: bao nhieu ma trong luoi doc dung. `temperature=0`.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.moi_truong_may_b import nap_env_may_b  # noqa: E402

CHU = "ACDEFGHJKMNPQRTUVWXY34679"
FONT = r"C:\Windows\Fonts\consolab.ttf"
#: (rong, cao, token) - token tinh o san 512 / tran 4096.
CO = ((640, 360, 514), (960, 540, 510), (1280, 720, 922), (1600, 900, 1450),
      (1920, 1080, 2042), (2048, 2048, 4098))


def _luoi(rng, hang: int, cot: int):
    return [["".join(rng.choice(CHU) for _ in range(6)) for _ in range(cot)]
            for _ in range(hang)]


def _anh(ma, rong, cao, goc=(3072, 3072)):
    """Render o co GOC roi thu nho ve (rong, cao) - giu nguyen noi dung.

    🔴 GOC PHAI LON HON MOI CO DUOC DO, va day la mot bai hoc dat.

       Ban dau `goc = (2048, 2048)`, nen rieng o `2048x2048` KHONG bi thu nho -
       no la anh render THANG, chu co canh cung, KHONG khu rang cua. No ra 0/9
       trong khi moi co nho hon (deu duoc thu nho) ra 9/9, va toi suyt ket luan
       "do phan giai cao hon doc TE hon".

       Doi chung tach bach: cung 2048x2048 nhung thu nho TU 3072 -> 9/9 HOAN HAO.
       ⇒ Bien that la KHU RANG CUA, khong phai so token. Mot phep do ma bo sinh
         anh doi tinh chat theo tung o thi no do chinh bo sinh, khong do model.
    """
    from PIL import Image, ImageDraw, ImageFont
    hang, cot = len(ma), len(ma[0])
    im = Image.new("RGB", goc, "white")
    d = ImageDraw.Draw(im)
    o_r, o_c = goc[0] // cot, goc[1] // hang
    px = o_c
    while px > 6:
        f = ImageFont.truetype(FONT, px)
        l, t, r, b = d.textbbox((0, 0), "WWWWWW", font=f)
        if (r - l) <= o_r * 0.86 and (b - t) <= o_c * 0.6:
            break
        px -= 1
    for i, dong in enumerate(ma):
        for j, m in enumerate(dong):
            l, t, r, b = d.textbbox((0, 0), m, font=f)
            d.text((j * o_r + (o_r - (r - l)) / 2 - l,
                    i * o_c + (o_c - (b - t)) / 2 - t), m, font=f, fill="black")
    if (rong, cao) != goc:
        im = im.resize((rong, cao), Image.LANCZOS)
    dem = io.BytesIO()
    im.save(dem, format="PNG")
    return "data:image/png;base64," + base64.b64encode(dem.getvalue()).decode()


def _doc(url, token, model, anh_url, so_ma):
    than = {"model": model, "max_tokens": 3000, "stream": False, "temperature": 0,
            "seed": 7,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": anh_url}},
                {"type": "text", "text": (
                    f"This image contains a grid of {so_ma} codes, each exactly 6 "
                    f"characters (A-Z and digits). Read them ALL, left to right, "
                    f"top to bottom. Reply with ONLY the codes separated by spaces.")}]}]}
    yc = urllib.request.Request(url + "/v1/chat/completions",
                                data=json.dumps(than).encode(),
                                headers={"content-type": "application/json",
                                         "authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(yc, timeout=900) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return [], f"http{e.code}"
    lua = (d.get("choices") or [{}])[0]
    noi = (lua.get("message") or {}).get("content") or ""
    return re.findall(r"[A-Z0-9]{6}", noi.upper()), lua.get("finish_reason")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen35-api")
    p.add_argument("--hang", type=int, default=3)
    p.add_argument("--cot", type=int, default=3)
    a = p.parse_args()

    env = dict(os.environ)
    print(nap_env_may_b(env))
    url = (env.get("LTT_LLM_BASE_URL") or "").rstrip("/")
    token = env.get("LTT_LLM_TOKEN") or ""
    if not url or not token:
        return 2

    rng = random.Random(20260928)
    ma = _luoi(rng, a.hang, a.cot)
    phang = [m for d in ma for m in d]
    print(f"\n  luoi {a.hang}x{a.cot} = {len(phang)} ma, render goc 3072x3072 roi THU NHO")
    print(f"  ma: {' '.join(phang)}")
    print(f"\n  {'co anh':<12}{'token':>7}{'doc dung':>10}{'thua/thieu':>12}   vi du sai")
    print(f"  {'-' * 62}")
    for rong, cao, tok in CO:
        co, ly_do = _doc(url, token, a.model, _anh(ma, rong, cao), len(phang))
        dung = sum(1 for m in phang if m in co)
        sai = [m for m in phang if m not in co][:2]
        print(f"  {f'{rong}x{cao}':<12}{tok:>7}{f'{dung}/{len(phang)}':>10}"
              f"{len(co) - len(phang):>12}   {', '.join(sai)}  [{ly_do}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
