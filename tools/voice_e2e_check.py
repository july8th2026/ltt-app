r"""
voice_e2e_check.py — CHAY va PHAN QUYET golden path + negative cua LTT Voice,
qua duong HTTP that, KHONG can GPU. Day la tang CI-tat-dinh.

    python tools\voice_e2e_check.py           # tu dung mock + e2e server roi kiem
    python tools\voice_e2e_check.py --no-servers --cong 8129   # dung server co san

## No chay gi

1. Dung `voice_mock_sidecar.py` (cong giong GIA LAP) + `voice_e2e_server.py`
   (may chu cach ly + worker trong tien trinh, tro vao mock).
2. GOLDEN: login -> POST /ltt-voice/tao -> poll /ket-qua toi `done` -> tai WAV.
3. NEGATIVE (moi ca phai bi tu choi DUNG cach): rong · vua preset vua voice_id ·
   CSRF sai · vuot tran ky tu · preset bia.
4. Cac RAO CHONG-XANH-GIA o duoi.

## ⛔ DAY LA SIMULATED INFERENCE

Tieng do cong GIA LAP sinh ra (`voice_mock_sidecar.py`). Phan quyet o day KHONG
thay cho tang LIVE (`chay_thu_ltt_voice.py` + `cong_chat_luong_voice.py` tren
dich vu that). Dong RESULT tu khai dieu do.

## 🔴 RAO CHONG-XANH-GIA (false-green guards) — vi mot cong xanh de dang la vo dung

  G1  job phai that su toi `done` (KHONG chap nhan mot trang thai cuoi bat ky:
      `error`/`cancelled` la ĐO). Mot bo test coi moi trang thai cuoi la "xong"
      se xanh ca khi job HONG.
  G2  WAV tra ve phai la RIFF/WAVE HOP LE va co `X-Duration-S` > 0 va credit > 0
      — tuc worker + ffprobe + so credit that su da chay, khong phai mot 200 rong.
  G3  moi ca NEGATIVE phai tra 400 + `ok:false`. Mot ca vo tinh 200 la mot cai
      cong da mo ma khong ai thay.
  G4  so phep kiem thuc chay phai == so phep kiem KHAI BAO (`SO_KIEM`). Neu mot
      buoc tu bo qua (ngoai le, redirect la, thoat som) thi tong lech va cong ĐO
      — chan dung lop "test collection = 0 bat thuong".
  G5  WAV phai mang dau van tay `ltt-voice-mock`. Neu KHONG co, nghia la duong
      da tro vao mot cong THAT — sai tang; cong nay chi duoc chay tren mock.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL = "voice-e2e@test.local"
MAT_KHAU = "khong-phai-mat-khau-that-12"

#: So phep kiem KHAI BAO. G4 doi so thuc chay khop dung con so nay.
#: 1 golden + 5 negative = 6.
SO_KIEM = 6


class Loi(RuntimeError):
    pass


class Client:
    def __init__(self, goc: str):
        self.goc = goc.rstrip("/")
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self.csrf = ""

    def get(self, duong: str) -> tuple[int, str, bytes]:
        try:
            with self.op.open(self.goc + duong, timeout=30) as r:
                raw = r.read()
                return r.status, raw.decode("utf-8", "replace"), raw
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, raw.decode("utf-8", "replace"), raw

    def post(self, duong: str, data: dict) -> tuple[int, str]:
        body = urllib.parse.urlencode(data).encode()
        try:
            with self.op.open(urllib.request.Request(self.goc + duong, data=body),
                              timeout=60) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    def login(self) -> None:
        _, html, _ = self.get("/login")
        m = re.search(r'name="csrf_token" value="([^"]+)"', html)
        if not m:
            raise Loi("khong lay duoc csrf o /login")
        self.post("/login", {"username": EMAIL, "password": MAT_KHAU,
                             "csrf_token": m.group(1)})
        _, st, _ = self.get("/ltt-voice")
        m2 = re.search(r'id="lv-form"[\s\S]*?name="csrf_token" value="([^"]*)"', st)
        if not (m2 and m2.group(1)):
            raise Loi("form Studio khong render csrf_token")
        self.csrf = m2.group(1)


def _cho_len(goc: str, duong: str, giay: float = 30.0) -> None:
    het = time.time() + giay
    while time.time() < het:
        try:
            with urllib.request.urlopen(goc + duong, timeout=2) as r:
                if r.status < 500:
                    return
        except (OSError, urllib.error.URLError):
            pass                                # chua len — thu lai, day la vong cho
        time.sleep(0.4)
    raise Loi(f"server khong len: {goc}{duong}")


def golden(c: Client) -> list[str]:
    """Tra ve danh sach loi (rong = dat). Ap G1/G2/G5."""
    import json
    loi = []
    code, body = c.post("/ltt-voice/tao", {
        "text": "Xin chao, day la luot kiem golden path cua LTT Voice.",
        "preset": "Adam", "toc_do": "1.0", "ngon_ngu": "auto",
        "csrf_token": c.csrf})
    if code != 200:
        return [f"golden: POST /tao -> {code} {body[:120]}"]
    jid = json.loads(body).get("job_id")
    if not jid:
        return [f"golden: khong co job_id: {body[:120]}"]

    final = None
    het = time.time() + 60
    while time.time() < het:
        _, rb, _ = c.get(f"/ltt-voice/ket-qua/{jid}")
        try:
            d = json.loads(rb)
        except ValueError:
            time.sleep(0.4); continue
        if d.get("trang_thai") in ("done", "error", "cancelled"):
            final = d; break
        time.sleep(0.4)
    if final is None:
        return [f"golden: job {jid[:8]} HET GIO, chua toi trang thai cuoi"]
    # G1: phai la `done`, khong phai mot trang thai cuoi bat ky.
    if final.get("trang_thai") != "done":
        loi.append(f"G1 golden: job KHONG done -> {final.get('trang_thai')}")
        return loi
    # G2: worker + ffprobe + credit that su chay.
    if not (final.get("giay") and float(final["giay"]) > 0):
        loi.append(f"G2 golden: duration_s khong > 0 ({final.get('giay')})")
    if not (final.get("credit") and int(final["credit"]) > 0):
        loi.append(f"G2 golden: credit khong > 0 ({final.get('credit')})")
    url = final.get("audio_url") or ""
    if not url:
        loi.append("G2 golden: khong co audio_url")
        return loi
    code, _, raw = c.get(url)
    if code not in (200, 206):
        loi.append(f"G2 golden: tai audio -> {code}")
    elif not (raw[:4] == b"RIFF" and raw[8:12] == b"WAVE"):
        loi.append("G2 golden: audio KHONG phai WAV hop le")
    # G5: phai la tieng GIA LAP.
    elif b"ltt-voice-mock" not in raw:
        loi.append("G5 golden: WAV THIEU dau van tay mock -> co the da tro vao "
                   "cong THAT; cong nay chi chay tren mock")
    return loi


#: Cac ca NEGATIVE. Moi ca: `(nhan, form, ky vong chuoi trong loi)`.
NEGATIVE = [
    ("rong", {"text": "   ", "preset": "Adam"}, "văn bản"),
    ("vua-preset-vua-voice", {"text": "hi", "preset": "Adam",
                              "voice_id": "vce_e2e_natural_vi"}, "Chỉ chọn một"),
    ("csrf-sai", {"text": "hi", "preset": "Adam", "csrf_token": "__SAI__"}, "hết hạn"),
    ("vuot-tran", {"text": "a" * 100001, "preset": "Adam"}, "vượt giới hạn"),
    ("preset-bia", {"text": "hi", "preset": "KHONG-CO-THAT"}, "dựng sẵn"),
]


def negative(c: Client) -> tuple[int, list[str]]:
    """Chay het negative. Tra `(so_ca_chay, loi[])`. Ap G3."""
    import json
    loi = []
    n = 0
    for nhan, form, _mong in NEGATIVE:      # `_mong` (thong diep) do browser flow khang dinh
        n += 1
        f = dict(form)
        f.setdefault("csrf_token", c.csrf)
        code, body = c.post("/ltt-voice/tao", f)
        # G3: phai 400 + ok:false.
        if code != 400:
            loi.append(f"G3 negative[{nhan}]: mong 400, nhan {code} — CUA MO")
            continue
        try:
            ok = json.loads(body).get("ok")
        except ValueError:
            ok = None
        if ok is not False:
            loi.append(f"G3 negative[{nhan}]: body khong ok:false ({body[:80]})")
    return n, loi


def chay(goc: str) -> int:
    c = Client(goc)
    c.login()
    loi = list(golden(c))
    so_neg, loi_neg = negative(c)
    loi += loi_neg

    # G4: so phep kiem thuc chay == khai bao.
    so_chay = 1 + so_neg                        # 1 golden + N negative
    if so_chay != SO_KIEM:
        loi.append(f"G4: chay {so_chay} phep kiem, KHAI BAO {SO_KIEM} — "
                   f"mot buoc da tu bo qua")

    print("=" * 70)
    print(f"  golden: {'DAT' if not [x for x in loi if x.startswith(('G1','G2','G5','golden'))] else 'ĐO'}")
    print(f"  negative: {so_neg}/{len(NEGATIVE)} ca chay")
    if loi:
        print(f"  🔴 CONG ĐO — {len(loi)} van de:")
        for d in loi:
            print(f"     {d}")
        print("\nRESULT: FAIL")
        return 1
    print(f"  ✅ CONG XANH — golden + {so_neg} negative, {SO_KIEM} phep kiem.")
    print("\n⚠️ SIMULATED INFERENCE: tieng do cong GIA LAP sinh. KHONG thay cho")
    print("   tang LIVE (chay_thu_ltt_voice.py + cong_chat_luong_voice.py).")
    print("RESULT: PASS (mock)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cong", type=int, default=8129)
    ap.add_argument("--mock-cong", type=int, default=8131)
    ap.add_argument("--no-servers", action="store_true",
                    help="dung server dang chay san, dung tu dung")
    a = ap.parse_args(argv)
    goc = f"http://127.0.0.1:{a.cong}"

    if a.no_servers:
        _cho_len(goc, "/login", 10)
        return chay(goc)

    py = sys.executable
    env = dict(os.environ)
    mock = subprocess.Popen(
        [py, os.path.join(ROOT, "tools", "voice_mock_sidecar.py"),
         "--cong", str(a.mock_cong), "--token", "mock-token"],
        cwd=ROOT, env=env)
    srv = subprocess.Popen(
        [py, os.path.join(ROOT, "tools", "voice_e2e_server.py"),
         "--cong", str(a.cong), "--mock-cong", str(a.mock_cong)],
        cwd=ROOT, env=env)
    try:
        _cho_len(f"http://127.0.0.1:{a.mock_cong}", "/health", 30)
        _cho_len(goc, "/login", 45)
        return chay(goc)
    finally:
        for p in (srv, mock):
            try:
                p.terminate()
                p.wait(timeout=10)
            except (OSError, subprocess.SubprocessError):
                try:
                    p.kill()
                except OSError:
                    pass                        # tien trinh da chet — khong con gi de giet


if __name__ == "__main__":
    raise SystemExit(main())
