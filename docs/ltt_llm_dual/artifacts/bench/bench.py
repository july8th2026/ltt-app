"""bench.py -- Benchmark harness tong quat cho LTT LLM Dual-Model (Task 0.4).

Tong quat hoa tu docs/multijob/artifacts/m1/m1_bench.py va m2_bench.py (nhanh
Multi-Job, doc 2026-09-11). KHAC BIET CHINH: m1/m2 tu spawn mot llama-server
RIENG tren cong thu nghiem (8290, CUDA_VISIBLE_DEVICES rieng) de KHONG dung
vao production -- roi giet no o finally. bench.py nay KHONG spawn gi ca: no
do THANG vao production qua llama-swap loopback (mac dinh cong 8280), dung
chinh ho so dang phuc vu khach that. Do la muc dich Task 0.4: lay moc hoi quy
tren dung engine/ho so production, khong phai tren mot ban sao co lap.

Chi stdlib. Chay tren MAY B (Windows). Dung qua pythonw duoc (Scheduled Task,
xem khoi_dong.ps1) hoac console thuong (python bench.py ...).

Kich ban da cai:
  c1  -- mot luot chat don (khong ignore_eos), prompt thuc te ~1-2K token vao.
  nap -- giong c1 nhung KHONG cho_ranh() truoc: dung khi model dang o trang
         thai chua nap (TTL da unload) de do do tre nap lanh; TTFT khi do bao
         gom ca thoi gian nap GGUF + tao context.

Kich ban CHUA cai (bang DISPATCH khai du, khong viet code chet cho chung):
  c4, whale, anh, mtp_gate -- xem docs/multijob/artifacts/m1/m2_bench.py de
  tham khao hinh dang (4 luong dong thoi, whale+minnow lech gio, ho so gop
  vision) khi task sau can dung lai.

AN TOAN:
  * KHONG spawn/giet tien trinh nao -- chi goi HTTP toi llama-swap dang chay.
  * cho_ranh() (dung cho c1) doi /slots proxy het "is_processing" truoc khi
    ban mot rep moi, de khong chen ngang mot luot khach that (best-effort:
    neu /slots khong doc duoc thi bo qua, khong chan).
  * Moi ket qua ghi TUNG DONG JSONL (khong doi cuoi lo) qua khoa file.
  * Nhip tim moi 15s ra <ra>.nhip.txt de theo doi tu xa (Scheduled Task).
"""
import argparse
import json
import os
import random
import subprocess
import threading
import time
import traceback
import urllib.error
import urllib.request

CREATE_NO_WINDOW = 0x08000000

UUID_3090 = "GPU-26623278-4fa5-82db-4306-237651b03e78"

# SHA256 cua GGUF production, doc 2026-09-11 tren may B (Get-FileHash), ghi lai
# o docs/ltt_llm_dual/00_CURRENT_BASELINE.md Sec.5. KHONG bam lai moi lan chay
# (bam 15,3 GB ton ~60s/lan, va file khong doi giua cac lan chay bench). Neu
# doi GGUF production, sua hang so nay VA tai lieu baseline cho khop.
SHA_GGUF_QWEN38 = "322E194FF79741C7BAA497C240F677F54B201B0EFAB44CA8E50F122B39123482"

T_BAT_DAU = time.time()

PROMPT_HUONG_DAN = (
    "Ban la ky su he thong. Hay giai thich chi tiet, co vi du cu the, cach mot "
    "may chu suy luan mo hinh ngon ngu lon phuc vu nhieu nguoi dung dong thoi: "
    "hang doi, bo nho dem ngu canh, lap lich prefill va decode, va cach do do "
    "tre. Doc doan ngu canh duoi day roi viet mot ban phan tich dai, co cau "
    "truc, nhieu muc, dua vao noi dung do.\n\n")

# Tu vung de dung "ngu canh" gia lap thuc te (~1-2K token). Tron ky thuat +
# van hanh de gan voi prompt that hon la lap lai mot cau.
_TU = ("he thong hang doi cong viec may chu mo hinh ngon ngu nguoi dung yeu cau "
       "bo nho dem ngu canh do tre thong luong suy luan the he ban ghi ket qua "
       "kiem tra tai khoan thanh toan tin dung loi thu lai huy bo giam sat "
       "request queue worker scheduler latency throughput cache token prompt "
       "decode prefill slot memory budget fairness priority cancel stream "
       "gpu vram context window batch continuous speculative draft metrics "
       "credit invoice job lease retry timeout backoff idempotency webhook").split()


def now_s():
    return round(time.time() - T_BAT_DAU, 3)


def sinh_prompt(so_tu):
    """Van ban gia lap ~so_tu tu (~1.3 token/tu voi BPE tieng Anh/Viet khong dau)."""
    r = random.Random(time.time_ns() ^ os.getpid())
    cau = []
    while sum(len(c.split()) for c in cau) < so_tu:
        n = r.randint(8, 20)
        c = " ".join(r.choice(_TU) for _ in range(n))
        cau.append("%s %d, %s." % (c.capitalize(), r.randint(1, 99999), r.choice(_TU)))
    return " ".join(cau)


def nonce():
    return "[%s-%d] " % ("".join(random.choice("abcdefghjkmnpqrstuvwxyz") for _ in range(10)),
                          random.randint(0, 10 ** 9))


# ---------------------------------------------------------------- HTTP
def http(method, url, body=None, timeout=60.0):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def dang_ban(base):
    """Best-effort: True neu /slots (proxy qua llama-swap) bao co slot dang xu ly."""
    try:
        _, t = http("GET", base + "/slots", timeout=5)
        mang = json.loads(t)
        return any(s.get("is_processing") for s in mang)
    except Exception:  # noqa: BLE001
        return False


def cho_ranh(base, han_s=60):
    t0 = time.time()
    while dang_ban(base) and time.time() - t0 < han_s:
        time.sleep(1)


def dang_nap(base):
    try:
        _, t = http("GET", base + "/running", timeout=5)
        return json.loads(t)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- do GPU
def vram_mib(uuid):
    try:
        o = subprocess.run(
            ["nvidia-smi", "--id=" + uuid, "--query-gpu=memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15,
            creationflags=CREATE_NO_WINDOW).stdout.strip()
        return int(o.splitlines()[0])
    except Exception:  # noqa: BLE001
        return None


def power_w(uuid):
    try:
        o = subprocess.run(
            ["nvidia-smi", "--id=" + uuid, "--query-gpu=power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15,
            creationflags=CREATE_NO_WINDOW).stdout.strip()
        return float(o.splitlines()[0])
    except Exception:  # noqa: BLE001
        return None


def pid_llama_server():
    try:
        o = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq llama-server.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=CREATE_NO_WINDOW).stdout
        for dong in o.strip().splitlines():
            phan = [p.strip('"') for p in dong.split('","')]
            if len(phan) >= 2 and phan[0].lower() == "llama-server.exe":
                return int(phan[1])
    except Exception:  # noqa: BLE001
        pass
    return None


def shared_usage_mib(pid):
    """Get-Counter '\\GPU Process Memory(pid_<pid>*)\\Shared Usage' -- nvidia-smi
    KHONG thay spill WDDM; con nay la cach duy nhat doc duoc no. Tong tat ca
    instance khop pid (mot tien trinh co the co nhieu adapter/engine)."""
    if not pid:
        return None
    lenh_ps = (
        "$s = Get-Counter '\\GPU Process Memory(pid_%d*)\\Shared Usage' "
        "-ErrorAction SilentlyContinue; "
        "if ($s) { ($s.CounterSamples | Measure-Object -Property CookedValue -Sum).Sum } "
        "else { '' }"
    ) % pid
    try:
        o = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", lenh_ps],
            capture_output=True, text=True, timeout=20,
            creationflags=CREATE_NO_WINDOW).stdout.strip()
        if o:
            return round(float(o) / (1024 * 1024), 1)
    except Exception:  # noqa: BLE001
        pass
    return None


class LayMau(threading.Thread):
    """Lay mau VRAM dinh (dedicated) / shared dinh (WDDM spill) / power trung
    binh moi ~1s trong luc mot request dang chay."""

    def __init__(self, uuid):
        super().__init__(daemon=True)
        self.uuid = uuid
        self.dung = threading.Event()
        self.vram_dinh = None
        self.shared_dinh = None
        self.power_mau = []

    def run(self):
        pid = pid_llama_server()
        while not self.dung.is_set():
            v = vram_mib(self.uuid)
            if v is not None:
                self.vram_dinh = v if self.vram_dinh is None else max(self.vram_dinh, v)
            s = shared_usage_mib(pid)
            if s is not None:
                self.shared_dinh = s if self.shared_dinh is None else max(self.shared_dinh, s)
            p = power_w(self.uuid)
            if p is not None:
                self.power_mau.append(p)
            self.dung.wait(1.0)

    def dung_lai(self):
        self.dung.set()
        self.join(timeout=5)

    def ket_qua(self):
        tb = round(sum(self.power_mau) / len(self.power_mau), 1) if self.power_mau else None
        return self.vram_dinh, self.shared_dinh, tb


# ---------------------------------------------------------------- goi chat (stream)
def chat_stream(base, model, noi_dung, max_tokens, ignore_eos=False, timeout=300.0):
    body = {"model": model, "messages": [{"role": "user", "content": noi_dung}],
            "max_tokens": max_tokens, "temperature": 0.7, "top_p": 0.95,
            "seed": random.randint(0, 10 ** 9), "ignore_eos": ignore_eos,
            "stream": True, "stream_options": {"include_usage": True}}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base + "/v1/chat/completions", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    moc = []
    timings = None
    usage = None
    fingerprint = None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for dong in r:
            dong = dong.decode("utf-8", "replace").strip()
            if not dong.startswith("data:"):
                continue
            p = dong[5:].strip()
            if p == "[DONE]":
                break
            try:
                d = json.loads(p)
            except ValueError:
                continue
            if d.get("system_fingerprint"):
                fingerprint = d["system_fingerprint"]
            if d.get("timings"):
                timings = d["timings"]
            if d.get("usage"):
                usage = d["usage"]
            for ch in d.get("choices") or []:
                de = ch.get("delta") or {}
                if de.get("content") or de.get("reasoning_content"):
                    moc.append(time.time())
    t_cuoi = time.time()
    return {"t0": t0, "t_cuoi": t_cuoi, "moc_token": moc, "timings": timings,
            "usage": usage, "system_fingerprint": fingerprint}


def _ban_ghi_tu_stream(kich_ban, args, kq, lay, them=None):
    vram_dinh, shared_dinh, power_tb = lay.ket_qua()
    moc = kq["moc_token"]
    ttft = round(moc[0] - kq["t0"], 3) if moc else None
    usage = kq["usage"] or {}
    timings = kq["timings"] or {}
    tok_s_decode = timings.get("predicted_per_second")
    if tok_s_decode is None and len(moc) > 1:
        tok_s_decode = round((len(moc) - 1) / (moc[-1] - moc[0]), 3)
    rec = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "kich_ban": kich_ban,
        "model": args.model,
        "build": kq["system_fingerprint"],
        "sha_gguf": SHA_GGUF_QWEN38,
        "uuid": args.uuid,
        "tham_so": {"max_tokens": 600, "ignore_eos": False, "temperature": 0.7,
                     "top_p": 0.95, "prompt_tu_muc_tieu": 1150},
        "ttft_s": ttft,
        "tok_s_decode": tok_s_decode,
        "prompt_tok_s": timings.get("prompt_per_second"),
        "token_vao": usage.get("prompt_tokens"),
        "token_ra": usage.get("completion_tokens"),
        "wall_s": round(kq["t_cuoi"] - kq["t0"], 3),
        "vram_dinh_mib": vram_dinh,
        "shared_dinh_mib": shared_dinh,
        "power_w_tb": power_tb,
    }
    if them:
        rec.update(them)
    return rec


# ---------------------------------------------------------------- bai do
def bai_c1(args, ghi):
    cho_ranh(args.base)
    prompt = PROMPT_HUONG_DAN + nonce() + sinh_prompt(1150)
    lay = LayMau(args.uuid)
    lay.start()
    try:
        kq = chat_stream(args.base, args.model, prompt, 600, ignore_eos=False, timeout=300.0)
    finally:
        lay.dung_lai()
    rec = _ban_ghi_tu_stream("c1", args, kq, lay)
    ghi(rec)
    return rec


def bai_nap(args, ghi):
    """Khong cho_ranh(): dung dung luc model dang KHONG duoc nap (TTL da unload)
    de do do tre nap lanh. TTFT bao gom ca thoi gian nap GGUF."""
    truoc = dang_nap(args.base)
    prompt = PROMPT_HUONG_DAN + nonce() + sinh_prompt(1150)
    lay = LayMau(args.uuid)
    lay.start()
    try:
        # healthCheckTimeout cua llama-swap la 600s (nap GGUF 15,33 GiB) -- de bien.
        kq = chat_stream(args.base, args.model, prompt, 600, ignore_eos=False, timeout=650.0)
    finally:
        lay.dung_lai()
    rec = _ban_ghi_tu_stream("nap", args, kq, lay, them={"dang_nap_truoc_khi_goi": truoc})
    ghi(rec)
    return rec


def _chua_cai(ten):
    def _f(args, ghi):
        raise SystemExit(
            "kich_ban '%s' chua duoc cai o Task 0.4 (bench.py chi lam c1/nap). "
            "Xem docs/multijob/artifacts/m1/m2_bench.py (bai_c4/bai_wm3/bai_anh) "
            "de tham khao hinh dang khi mot task sau can dung lai." % ten)
    return _f


DISPATCH = {
    "c1": bai_c1,
    "nap": bai_nap,
    "c4": _chua_cai("c4"),
    "whale": _chua_cai("whale"),
    "anh": _chua_cai("anh"),
    "mtp_gate": _chua_cai("mtp_gate"),
}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Benchmark production qua llama-swap loopback (Task 0.4)")
    ap.add_argument("--cong", type=int, default=8280, help="cong llama-swap (mac dinh 8280)")
    ap.add_argument("--model", default="qwen38-api", help="id model noi bo goi trong body (khoa llama-swap.yaml)")
    ap.add_argument("--uuid", default=UUID_3090, help="UUID GPU can do (nvidia-smi --id=)")
    ap.add_argument("--kich-ban", dest="kich_ban", required=True,
                     choices=sorted(DISPATCH.keys()))
    ap.add_argument("--lan", type=int, default=1, help="so lan lap lai")
    ap.add_argument("--ra", required=True, help="duong dan JSONL ghi ket qua (append)")
    args = ap.parse_args()
    args.base = "http://127.0.0.1:%d" % args.cong

    thu_muc_ra = os.path.dirname(os.path.abspath(args.ra))
    if thu_muc_ra:
        os.makedirs(thu_muc_ra, exist_ok=True)
    khoa = threading.Lock()

    def ghi(rec):
        with khoa:
            with open(args.ra, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=True) + "\n")

    hb_path = os.path.splitext(args.ra)[0] + ".nhip.txt"
    dung_hb = threading.Event()

    def nhip_tim():
        while not dung_hb.is_set():
            try:
                with open(hb_path, "w", encoding="utf-8") as f:
                    f.write("%s | %s | lan=%d | %.0fs\n" % (
                        time.strftime("%H:%M:%S"), args.kich_ban, args.lan, now_s()))
            except OSError:
                pass
            dung_hb.wait(15)

    threading.Thread(target=nhip_tim, daemon=True).start()

    ham = DISPATCH[args.kich_ban]
    for i in range(args.lan):
        try:
            rec = ham(args, ghi)
            print(json.dumps(rec, ensure_ascii=True))
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001
            loi = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "kich_ban": args.kich_ban,
                   "lan_thu": i, "loi": repr(e), "tb": traceback.format_exc()[-1500:]}
            ghi(loi)
            print(json.dumps(loi, ensure_ascii=True))
    dung_hb.set()


if __name__ == "__main__":
    main()
