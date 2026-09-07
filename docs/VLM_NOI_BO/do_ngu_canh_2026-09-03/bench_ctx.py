"""bench_ctx.py - do NGU CANH DAI that su tren may B. Chay TREN may B.

    py bench_ctx.py --ra H:/LTT_LLM/bench/ketqua.json

Vi sao khong dung mot bo bench co san: cot "ngu canh" trong moi bang cong dong
la CON SO CAP PHAT, do bang prompt vai tram token. Thu ta can biet la cua so
DUOC LAP DAY co chay khong -- nen moi luot o day deu:

  * sinh prompt NGAU NHIEN (khong tai dung prompt cache cua llama.cpp; tai dung
    lam prefill nhanh gia va bien phep do thanh vo nghia);
  * dem token THAT bang /tokenize cua chinh llama-server dang nap;
  * cam mot SENTINEL o DAU va mot o CUOI prompt roi bat model doc lai ca hai --
    cat ngu canh im lang se lam mat cai dau;
  * lay mau nvidia-smi 0,5 giay/lan trong suot luot de co VRAM DINH that.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import string
import subprocess
import sys
import threading
import time
import urllib.request

SWAP = "http://127.0.0.1:8280"


def _post(url, body, timeout=1200):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def _get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def vram_mb() -> int:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20).stdout.strip().splitlines()
        return int(out[0].strip())
    except Exception:
        return -1


class LayMau:
    """Lay mau VRAM trong nen. Dinh VRAM khong hoi lai duoc sau khi luot xong."""

    def __init__(self, moi=0.5):
        self.moi = moi
        self.dinh = 0
        self._chay = False

    def __enter__(self):
        self._chay = True
        self.dinh = vram_mb()
        self._t = threading.Thread(target=self._vong, daemon=True)
        self._t.start()
        return self

    def _vong(self):
        while self._chay:
            v = vram_mb()
            if v > self.dinh:
                self.dinh = v
            time.sleep(self.moi)

    def __exit__(self, *a):
        self._chay = False
        self._t.join(timeout=5)
        return False


def cong_model(ten: str) -> str:
    """Dia chi llama-server THAT cua mot ho so dang nap (bo qua llama-swap)."""
    d = _get(SWAP + "/running")
    for m in d.get("running", []):
        if m.get("model") == ten:
            return (m.get("proxy") or "").rstrip("/")
    return ""


def nap(ten: str, timeout=900):
    """Bao llama-swap nap ho so. Tra (giay, dia chi truc tiep)."""
    t0 = time.time()
    r = _post(SWAP + "/v1/chat/completions",
              {"model": ten, "messages": [{"role": "user", "content": "hi"}],
               "max_tokens": 1, "temperature": 0}, timeout=timeout)
    r.read()
    giay = time.time() - t0
    for _ in range(30):
        c = cong_model(ten)
        if c:
            return giay, c
        time.sleep(1)
    return giay, ""


_TU = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu "
       "xi omicron pi rho sigma tau upsilon phi chi psi omega quantum vector "
       "tensor gradient kernel buffer socket thread mutex latency throughput "
       "cache token context window inference decode prefill batch attention "
       "residual").split()


def van_ban(so_tu: int, rnd: random.Random) -> str:
    return " ".join(rnd.choice(_TU) for _ in range(so_tu))


def dem_token(goc: str, s: str) -> int:
    r = _post(goc + "/tokenize", {"content": s}, timeout=600)
    return len(json.loads(r.read().decode("utf-8")).get("tokens", []))


def dung_prompt(goc: str, muc_tieu: int, rnd: random.Random):
    """Prompt ~`muc_tieu` token, ngau nhien, co sentinel dau va cuoi."""
    a = "".join(rnd.choice(string.ascii_uppercase) for _ in range(8))
    b = "".join(rnd.choice(string.ascii_uppercase) for _ in range(8))
    dau = "MOC-DAU=" + a + "\n"
    cuoi = "\nMOC-CUOI=" + b + "\n"
    so_tu = int(muc_tieu / 1.35)
    than = van_ban(so_tu, rnd)
    for _ in range(6):
        s = dau + than + cuoi
        n = dem_token(goc, s)
        if abs(n - muc_tieu) <= max(200, muc_tieu * 0.005):
            return s, a, b, n
        so_tu = max(16, int(so_tu * (muc_tieu / max(1, n))))
        than = van_ban(so_tu, rnd)
    s = dau + than + cuoi
    return s, a, b, dem_token(goc, s)


def mot_luot(goc: str, model: str, muc_tieu: int, token_ra: int,
             rnd: random.Random) -> dict:
    kq = {"model": model, "muc_tieu": muc_tieu, "token_ra_xin": token_ra}
    try:
        prompt, a, b, n_that = dung_prompt(goc, muc_tieu, rnd)
    except Exception as e:                                    # noqa: BLE001
        kq["loi"] = "dung_prompt: " + type(e).__name__ + ": " + str(e)
        return kq
    kq["token_vao_that"] = n_that
    cau = ("Doc ky van ban tren. Tra loi DUNG mot dong theo khuon:\n"
           "DAU=<gia tri MOC-DAU> CUOI=<gia tri MOC-CUOI>")
    if token_ra >= 4096:
        # ⛔ MOT NGAN SACH `max_tokens` LON KHONG PHAI MOT PHEP DO SINH DAI.
        #    Luot 160K/8192 dau tien tra dung 122 token roi `finish_reason:
        #    stop` — vi de bai chi doi mot dong. No chung minh request duoc
        #    NHAN, khong chung minh decode con khoe o cuoi cua so. Hai menh de
        #    khac nhau, va chi menh de thu hai la thu khach cam thay.
        cau += ("\n\nSau dong do, viet tiep mot danh sach danh so tu 1 den 400. "
                "Moi muc mot dong, dang: `<so>. <tu thu <so> trong van ban tren "
                "neu ban nho, neu khong thi mot tu bat ky>`. Viet du 400 muc, "
                "khong tom tat, khong dung som.")
    body = {"model": model, "temperature": 0, "max_tokens": token_ra,
            "stream": True, "stream_options": {"include_usage": True},
            # `--reasoning-format deepseek` tach khoi <think> sang truong rieng.
            # Khong ha do sau suy nghi thi mot luot ngan co the tieu het ngan
            # sach vao suy nghi va KHONG tra chu nao -- luc do sentinel do vi
            # model im, chu khong vi ngu canh bi cat. Hai nguyen nhan khac han.
            "chat_template_kwargs": {"reasoning_effort": "low"},
            "messages": [{"role": "user", "content": prompt + "\n" + cau}]}
    t0 = time.time()
    ttft = None
    chu = []
    nghi = []
    usage = None
    with LayMau() as lm:
        try:
            # 🔴 GUI QUA llama-swap, KHONG gui thang toi cong cua llama-server.
            #
            #    Lan truoc toi gui thang toi `goc` (vd 127.0.0.1:8282) vi nghi
            #    nhu the "sach hon" — bo bot mot lop proxy khoi phep do. No lam
            #    hong hai lo do lien tiep, va ca hai lan gia thuyet sai deu khop
            #    HOAN HAO voi so lieu:
            #
            #      lan 1  llama-swap DUOI model de nap ho so khac (mot request
            #             `ltt_llm` that toi giua chung)   -> trong nhu OOM 130K
            #      lan 2  llama-swap UNLOAD theo `ttl: 900` vi no khong thay
            #             hoat dong nao tren ho so nay      -> trong nhu OOM 180K
            #
            #    Ca hai lan model bien mat giua luot prefill va ta chi nhan
            #    `ConnectionReset` — dung cai xac ma mot lan OOM cung de lai.
            #
            # ⭐ Va bai hoc that: `ttl` cua llama-swap dem hoat dong **di qua
            #    no**. Do vong qua no la tu tay tat dong ho giu model song, roi
            #    quy cai chet cho model.
            r = _post(SWAP + "/v1/chat/completions", body, timeout=2400)
            for dong in r:
                dong = dong.decode("utf-8", "replace").strip()
                if not dong.startswith("data:"):
                    continue
                phan = dong[5:].strip()
                if phan == "[DONE]":
                    break
                try:
                    ev = json.loads(phan)
                except ValueError:
                    continue
                if ev.get("usage"):
                    usage = ev["usage"]
                for ch in ev.get("choices") or []:
                    delta = ch.get("delta") or {}
                    r_ = delta.get("reasoning_content") or ""
                    d = delta.get("content") or ""
                    if (d or r_) and ttft is None:
                        # TTFT tinh tu BYTE SINH DAU TIEN, ke ca byte suy nghi:
                        # do la luc prefill that su ket thuc.
                        ttft = time.time() - t0
                    if r_:
                        nghi.append(r_)
                    if d:
                        chu.append(d)
                    if ch.get("finish_reason"):
                        kq["finish_reason"] = ch["finish_reason"]
        except Exception as e:                                # noqa: BLE001
            kq["loi"] = type(e).__name__ + ": " + str(e)
        kq["vram_dinh_mb"] = lm.dinh
    tong = time.time() - t0
    ra = "".join(chu)
    kq["tong_giay"] = round(tong, 2)
    kq["ttft_giay"] = round(ttft, 2) if ttft else None
    kq["usage"] = usage
    kq["tra_loi"] = ra[:300]
    kq["token_nghi_ky_tu"] = len("".join(nghi))
    kq["sentinel_dau"] = a in ra
    kq["sentinel_cuoi"] = b in ra
    if ttft and ttft > 0:
        kq["prefill_tok_s"] = round(n_that / ttft, 1)
    n_ra = (usage or {}).get("completion_tokens")
    if n_ra and ttft and tong > ttft:
        kq["decode_tok_s"] = round(n_ra / (tong - ttft), 1)
    return kq


def _ghi(duong, bao):
    p = pathlib.Path(duong)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(bao, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", required=True)
    ap.add_argument("--model", default="qwen38-ops")
    ap.add_argument("--moc",
                    default="50000,100000,130000,150000,160000,170000,180000")
    ap.add_argument("--token-ra", type=int, default=512)
    ap.add_argument("--nang", default="",
                    help="moc:token_ra bo sung, vd 160000:8192")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    rnd = random.Random(a.seed)
    bao = {"bat_dau": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": a.model,
           "vram_truoc_nap_mb": vram_mb(), "luot": []}
    print("[.] nap " + a.model + " ...", flush=True)
    giay, goc = nap(a.model)
    bao["nap_giay"] = round(giay, 1)
    bao["dia_chi"] = goc
    bao["vram_sau_nap_mb"] = vram_mb()
    print("[+] nap xong " + str(round(giay, 1)) + "s -> " + str(goc)
          + "  VRAM=" + str(bao["vram_sau_nap_mb"]) + " MiB", flush=True)
    _ghi(a.ra, bao)
    if not goc:
        bao["loi"] = "khong tim duoc dia chi llama-server"
        _ghi(a.ra, bao)
        return 1

    viec = [(int(m), a.token_ra) for m in a.moc.split(",") if m.strip()]
    if a.nang.strip():
        for cap in a.nang.split(","):
            m, t = cap.split(":")
            viec.append((int(m), int(t)))

    for muc, tr in viec:
        # ⛔ MOT LUOT NHO QUA llama-swap TRUOC MOI PHEP DO. No lam hai viec:
        #    dat lai dong ho `ttl` (llama-swap unload theo thoi gian KHONG co
        #    hoat dong di qua no), va xac nhan model van con song truoc khi ta
        #    tinh gio. Thieu buoc nay, lo do truoc bi unload giua luot prefill
        #    180K va ket qua trong y het mot lan OOM.
        nap(a.model)
        print("[.] " + a.model + " " + str(muc) + " vao / " + str(tr) + " ra ...",
              flush=True)
        kq = mot_luot(goc, a.model, muc, tr, rnd)
        bao["luot"].append(kq)
        gon = {k: v for k, v in kq.items() if k != "tra_loi"}
        print("    " + json.dumps(gon, ensure_ascii=False), flush=True)
        _ghi(a.ra, bao)
    bao["ket_thuc"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _ghi(a.ra, bao)
    print("[+] xong", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
