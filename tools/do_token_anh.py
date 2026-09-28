"""do_token_anh.py - do CHI PHI TOKEN THAT cua mot anh, bang HIEU `prompt_tokens`.

## Vi sao cong cu nay ton tai

`apps/ltt_llm/ngan_sach.TOKEN_MOI_ANH = 770` la MOT diem do (anh 1024x768, 17 ->
787 token, ghi 12/09). Mot diem khop ca cong thuc dung lan mot cong thuc trung
hop. Truoc khi bat ky phep CUONG CHE nao dua tren cong thuc `f(rong, cao)`, ta
phai do it nhat ba diem tren CA HAI model va doi chieu voi du doan.

Cong thuc du doan lay tu SIEU DU LIEU CUA CHINH TEP mmproj tren may B (doc
2026-09-28, CHI DOC):

    clip.projector_type            = 'qwen3vl_merger'   (ca hai mmproj)
    clip.vision.patch_size         = 16
    clip.vision.spatial_merge_size = 2
    => mot token = (16 * 2) x (16 * 2) = 32 x 32 diem anh

    token_anh(w, h) = ceil_32(w)/32 * ceil_32(h)/32, kep trong [8, 4096]

Tran [8, 4096] la cua llama.cpp cho ho Qwen2VL/Qwen25VL/Qwen3VL:
`tools/mtmd/clip.cpp:1660` `set_limit_image_tokens(8, 4096)` tai dung commit
`91f6a6cf3` (build b10883) dang chay. Khoa GGUF `clip.vision.image_min_pixels`
/ `image_max_pixels` VANG MAT trong ca hai tep, va llama.cpp cung KHONG doc
chung cho ho Qwen - nen cac co CLI `--image-min-tokens` / `--image-max-tokens`
la can gat duy nhat.

## Vi sao goi THANG cong may B, khong qua `/api/v1` cua may A

Phep do can `usage.prompt_tokens` THAT cua llama-server, khong can so tien va
khong can lop dat cho cua may A. Di qua may A se tieu credit that va tron them
hai lop uoc luong vao mot phep do dang hoi mot cau rat hep.

Token cong may B lay qua `tools/moi_truong_may_b.nap_env_may_b` (SSH chi doc,
token chi nam trong bo nho tien trinh - KHONG in, KHONG ghi dia).

## Cach doc ket qua

Cot `hieu` la so token anh THAT (da tru phan chu, vi ca hai luot dung y het mot
chuoi). Cot `du_doan` la cong thuc tren, CONG 2 cho cap dau `<|vision_start|>` /
`<|vision_end|>` ma khuon mau chen vao dong chu.

    lech = 0   -> cong thuc dung
    lech != 0  -> DUNG viet `anh_token.py` cho toi khi hieu vi sao

Chay:

    python tools\\do_token_anh.py                     # ca hai model
    python tools\\do_token_anh.py --model qwen35-api
    python tools\\do_token_anh.py --webp              # them mot anh WebP
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.moi_truong_may_b import nap_env_may_b  # noqa: E402

#: Suy tu sieu du lieu mmproj - xem docstring. KHONG go tay o noi khac.
DIEM_ANH_MOI_TOKEN_CANH = 32
TOKEN_TOI_THIEU = 8
TOKEN_TOI_DA = 4096
#: `<|vision_start|>` + `<|vision_end|>` cua khuon mau, dem nhu token CHU.
TOKEN_DAU_VISION = 2

#: Cau hoi giong het nhau o luot co anh va luot khong anh, nen phan chu triet tieu.
CAU_HOI = "One word."

#: ⭐ Hai co cuoi nam O TREN va O DUOI tran kep 4.096 - do chinh CHO dat cho hien
#:    tai thieu 2x. Mot bang do dung lai o 1080p khong noi duoc gi ve cho ay.
CO_KICH_THUOC = ((320, 240), (512, 512), (1024, 768), (1280, 720), (1920, 1080),
                 (2048, 2048), (3840, 2160))


def _tron(x: float) -> int:
    """`std::round` cua C++: nua len, RA XA SO KHONG.

    🔴 KHONG dung `round()` cua Python - no lam tron VE SO CHAN. Do 28/09 bat
       duoc dung mot o: 1280x720 -> 720/32 = 22,5. C++ cho 23, Python cho 22,
       lech 40 token. Va 1280x720 la mot trong nhung co anh chup man hinh pho
       bien nhat - nen loi nay nam dung tren duong di nhieu nhat, lech ve chieu
       THIEU (dat cho it hon thuc), tuc chieu nguy hiem.
    """
    return math.floor(x + 0.5) if x >= 0 else -math.floor(-x + 0.5)


def du_doan(rong: int, cao: int) -> int:
    """Token anh du doan, chua cong dau vision.

    Chep `calc_size_preserved_ratio()` cua llama.cpp (`tools/mtmd/mtmd-image.cpp`),
    chinh la `smart_resize` cua transformers doi sang buoc 32.

    ⛔ Vuot tran thi KHONG kep ve `TOKEN_TOI_DA` - no THU NHO giu ti le roi
       `floor`. Do 28/09: 3840x2160 cho 4.080 chu khong phai 4.096. Kep thang
       se lam so dat cho CAO hon thuc 16 token o moi anh 4K - sai huong an toan
       nhung van la sai, va no che mat viec anh DA bi thu nho.
    """
    c = DIEM_ANH_MOI_TOKEN_CANH
    o = max(1, _tron(rong / c)) * max(1, _tron(cao / c))
    if o > TOKEN_TOI_DA:
        beta = math.sqrt(rong * cao / (TOKEN_TOI_DA * c * c))
        o = (max(1, math.floor(rong / beta / c))
             * max(1, math.floor(cao / beta / c)))
    return max(TOKEN_TOI_THIEU, o)


def _anh(rong: int, cao: int, duoi: str) -> str:
    """Anh GRADIENT tien dinh.

    ⭐ Noi dung anh KHONG anh huong so token - chi kich thuoc. Nen dung gradient
       (nen rat nho) thay vi nhieu (PNG 1920x1080 nhieu ~6 MB, base64 ~8 MB):
       mot phep do ve SO TOKEN khong duoc bien thanh mot phep do ve BYTE.
    """
    from PIL import Image

    im = Image.linear_gradient("L").resize((rong, cao)).convert("RGB")
    dem = io.BytesIO()
    im.save(dem, format={"png": "PNG", "jpg": "JPEG", "webp": "WEBP"}[duoi])
    mime = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}[duoi]
    return f"data:{mime};base64," + base64.b64encode(dem.getvalue()).decode()


def _goi(url: str, token: str, than: dict) -> dict:
    yc = urllib.request.Request(
        url, data=json.dumps(than).encode("utf-8"),
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(yc, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_loi_http": e.code, "_than": e.read().decode("utf-8", "replace")[:900]}


def _prompt_tokens(kq: dict) -> int | None:
    if "_loi_http" in kq:
        return None
    return (kq.get("usage") or {}).get("prompt_tokens")


def do_mot_model(url: str, token: str, model: str, *, webp: bool) -> int:
    print(f"\n{'=' * 78}\n{model}\n{'=' * 78}")

    nen = _goi(f"{url}/v1/chat/completions", token, {
        "model": model, "max_tokens": 1, "stream": False,
        "messages": [{"role": "user", "content": CAU_HOI}]})
    goc = _prompt_tokens(nen)
    if goc is None:
        print(f"  LOI nen: {nen.get('_loi_http')} {nen.get('_than', '')[:200]}")
        return 1
    print(f"  nen (khong anh): prompt_tokens = {goc}\n")
    print(f"  {'anh':<16}{'duoi':<6}{'hieu':>8}{'du_doan':>10}{'lech':>8}")
    print(f"  {'-' * 48}")

    xau = 0
    ca = [(r, c, "png") for r, c in CO_KICH_THUOC]
    if webp:
        ca.append((1024, 768, "webp"))
    for rong, cao, duoi in ca:
        kq = _goi(f"{url}/v1/chat/completions", token, {
            "model": model, "max_tokens": 1, "stream": False,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": _anh(rong, cao, duoi)}},
                {"type": "text", "text": CAU_HOI}]}]})
        co = _prompt_tokens(kq)
        ten = f"{rong}x{cao}"
        if co is None:
            print(f"  {ten:<16}{duoi:<6}{'LOI':>8}  http={kq.get('_loi_http')}\n"
                  f"      {kq.get('_than', '')}")
            xau += 1
            continue
        hieu = co - goc
        dd = du_doan(rong, cao) + TOKEN_DAU_VISION
        lech = hieu - dd
        print(f"  {ten:<16}{duoi:<6}{hieu:>8}{dd:>10}{lech:>8}"
              f"{'' if lech == 0 else '   <== LECH'}")
        xau += int(lech != 0)
    return xau


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", action="append", default=None)
    p.add_argument("--webp", action="store_true",
                   help="them mot anh WebP (may B chua chac giai ma duoc)")
    a = p.parse_args()

    env = dict(os.environ)
    print(nap_env_may_b(env))
    url = (env.get("LTT_LLM_BASE_URL") or "").rstrip("/")
    token = env.get("LTT_LLM_TOKEN") or ""
    if not url or not token:
        print("khong co duong vao cong may B -> khong do duoc")
        return 2

    xau = 0
    for m in (a.model or ["qwen38-api", "qwen35-api"]):
        xau += do_mot_model(url, token, m, webp=a.webp)
    print(f"\n{'KHOP HET - cong thuc dung' if xau == 0 else f'{xau} o LECH/LOI'}")
    return 0 if xau == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
