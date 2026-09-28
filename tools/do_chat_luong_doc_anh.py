"""do_chat_luong_doc_anh.py - do CHAT LUONG doc anh nho (phep do D-5).

## Cau hoi duy nhat tep nay tra loi

`tools/mtmd/clip.cpp:1662-1667` o dung build dang chay in canh bao rang Qwen-VL
can **>= 1.024 token anh** de lam dung tac vu dinh vi (dan issue #16842). Ta dang
chay san **8** (`--image-min-tokens 8`). Nang san len la mot DANH DOI SAN PHAM:
do chinh xac doi lay KV + credit khach tra.

⛔ KHONG duoc suy tu canh bao cua thuong nguon. Canh bao cho biet CO mot can gat;
   no khong cho biet can gat ay dang gia bao nhieu O TA.

## Cach do

Sinh anh chua mot MA NGAU NHIEN TIEN DINH (chu + so, khong co tu tieng Anh nao
de model doan), o cac co anh NAM DUOI 1.024 token - tuc dung vung ma `--image-min-
tokens` se can thiep. Hoi model doc lai. Cham bang:

  * `khop` - dung tung ky tu;
  * `CER`  - ti le ky tu sai (Levenshtein / do dai that), thap hon la tot hon.

⭐ `temperature=0` + `seed` co dinh: phep do nay hoi ve KHA NANG DOC, khong hoi ve
   do bien thien cua lay mau. Engine chay `--temp 1.0` nen phai ghi de o than.

⛔ CHAY BAN NAY TRUOC KHI DOI CO. Mot bang "sau" ma khong co "truoc" tren CUNG
   bo anh khong tra loi duoc cau hoi nao - do dung bai hoc 25/09 (mot phep kiem
   viet theo niem tin ve ma se xac nhan niem tin do).
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import random
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.moi_truong_may_b import nap_env_may_b  # noqa: E402

#: Chu + so KHONG gay nhap nhang hinh dang (bo O/0, I/1/l, S/5, Z/2, B/8).
CHU = "ACDEFGHJKMNPQRTUVWXY34679"
FONT = [r"C:\Windows\Fonts\consolab.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
#: Co anh NAM DUOI 1.024 token (o 32 px/token): 8, 12, 24, 48 token.
CO = ((128, 48), (192, 64), (256, 96), (384, 128))


def _ma(rng, n=6) -> str:
    return "".join(rng.choice(CHU) for _ in range(n))


def _anh(ma: str, rong: int, cao: int) -> str:
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (rong, cao), "white")
    d = ImageDraw.Draw(im)
    f = None
    for duong in FONT:
        if os.path.exists(duong):
            # Co chu chiem ~70 % chieu cao: to nhat co the ma con le hai ben.
            for px in range(cao, 6, -1):
                thu = ImageFont.truetype(duong, px)
                l, t, r, b = d.textbbox((0, 0), ma, font=thu)
                if (r - l) <= rong * 0.92 and (b - t) <= cao * 0.8:
                    f = thu
                    break
            break
    if f is None:
        raise SystemExit("khong tim thay font TrueType - phep do nay can mot font that")
    l, t, r, b = d.textbbox((0, 0), ma, font=f)
    d.text(((rong - (r - l)) / 2 - l, (cao - (b - t)) / 2 - t), ma, font=f, fill="black")
    dem = io.BytesIO()
    im.save(dem, format="PNG")
    return "data:image/png;base64," + base64.b64encode(dem.getvalue()).decode()


def _cer(mong: str, co: str) -> float:
    """Levenshtein / do dai that."""
    a, b = mong, co
    truoc = list(range(len(b) + 1))
    for i, ka in enumerate(a, 1):
        nay = [i]
        for j, kb in enumerate(b, 1):
            nay.append(min(truoc[j] + 1, nay[j - 1] + 1, truoc[j - 1] + (ka != kb)))
        truoc = nay
    return truoc[-1] / max(1, len(a))


def _doc(url, token, model, anh_url) -> tuple:
    # 🔴 `max_tokens` PHAI LON HON `--reasoning-budget` cua ho so.
    #    Lan do dau tien toi dat 24 va nhan 0/20 voi content RONG - khong phai
    #    model doc sai, ma la SUY NGHI an het ngan sach roi bi cat, tra rong voi
    #    `finish_reason=length`. Chinh `DEVELOPER_GUIDE.md` toi vua viet canh bao
    #    dung dieu nay, va toi van mac. Nen ham nay tra CA `finish_reason` -
    #    mot phep do khong phan biet duoc "doc sai" voi "bi cat" thi khong do gi.
    than = {"model": model, "max_tokens": 3000, "stream": False, "temperature": 0,
            "seed": 7,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": anh_url}},
                {"type": "text", "text": ("Transcribe the characters in this image "
                                          "EXACTLY. Reply with only those characters, "
                                          "no words, no punctuation.")}]}]}
    yc = urllib.request.Request(url + "/v1/chat/completions",
                                data=json.dumps(than).encode(),
                                headers={"content-type": "application/json",
                                         "authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(yc, timeout=900) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return None, f"http{e.code}"
    lua = (d.get("choices") or [{}])[0]
    noi = (lua.get("message") or {}).get("content") or ""
    return "".join(c for c in noi.upper() if c.isalnum()), lua.get("finish_reason")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen35-api")
    p.add_argument("--so-ma", type=int, default=5)
    p.add_argument("--nhan", default="TRUOC", help="nhan cua lan do nay, vd TRUOC/SAU")
    a = p.parse_args()

    env = dict(os.environ)
    print(nap_env_may_b(env))
    url = (env.get("LTT_LLM_BASE_URL") or "").rstrip("/")
    token = env.get("LTT_LLM_TOKEN") or ""
    if not url or not token:
        return 2

    rng = random.Random(20260928)          # TIEN DINH: hai lan do dung y het bo anh
    ma = [_ma(rng) for _ in range(a.so_ma)]
    print(f"\n  [{a.nhan}] model {a.model}, {a.so_ma} ma, temperature 0, seed 7")
    print(f"  ma: {' '.join(ma)}")
    print(f"\n  {'co anh':<12}{'token':>7}{'khop':>8}{'CER':>8}{'bi cat':>6}   vi du sai")
    print(f"  {'-' * 58}")
    tong = {}
    for rong, cao in CO:
        dung = 0
        cers = []
        sai = []
        cat = 0
        for m in ma:
            co, ly_do = _doc(url, token, a.model, _anh(m, rong, cao))
            if co is None:
                sai.append(f"LOI {ly_do}")
                cers.append(1.0)
                continue
            cat += int(ly_do == "length")
            dung += int(co == m)
            cers.append(_cer(m, co))
            if co != m and len(sai) < 2:
                sai.append(f"{m}->{co or '(rong)'}[{ly_do}]")
        tok = max(8, round(rong / 32 + 0.5) * round(cao / 32 + 0.5)) if False else None
        tok = max(8, (rong // 32) * (cao // 32))
        cer = sum(cers) / len(cers)
        tong[(rong, cao)] = (dung, len(ma), cer)
        print(f"  {f'{rong}x{cao}':<12}{tok:>7}{f'{dung}/{len(ma)}':>8}{cer:>8.2f}"
              f"{cat:>6}   {', '.join(sai)}")
    tong_dung = sum(v[0] for v in tong.values())
    tong_ma = sum(v[1] for v in tong.values())
    tong_cer = sum(v[2] for v in tong.values()) / len(tong)
    print(f"\n  [{a.nhan}] TONG: khop {tong_dung}/{tong_ma}  ·  CER trung binh {tong_cer:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
