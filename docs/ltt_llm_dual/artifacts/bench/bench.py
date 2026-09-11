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

  c4  -- bon luot text dong thoi; so dang ke la THONG LUONG TONG.
  anh -- mot anh mot minh, roi mot anh + ba text dong thoi (dinh VRAM ho so gop).
  whale -- mot prefill khong lo chay cung ba minnow lech gio (ep pool KV chung).
  mtp_gate -- cong DUNG/SAI cho draft-mtp voi -np 4 (Task 3.2 G2), khong do toc do.

Hinh dang cua c4/anh/whale bung tu docs/multijob/artifacts/m1/m2_bench.py de so
sanh duoc voi so do cua nhanh Multi-Job.

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


# ---------------------------------------------------------------- anh thu
def png_thu(w=1024, h=768):
    """PNG tu dung bang stdlib: nen xam, hinh TRON do ben trai, VUONG xanh ben phai.

    Bung nguyen tu m2_bench.py (nhanh Multi-Job). Giu y het de so sanh duoc voi
    so do cu: doi mau hay doi vi tri la doi ca CAU HOI lan dap an dung. Cung la
    ly do khong dung mot anh that: anh nay khong doi giua cac lan chay va khong
    keo mot tep nhi phan vao kho.
    """
    import struct
    import zlib
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            if (x - 300) ** 2 + (y - 384) ** 2 < 150 ** 2:
                raw += b"\xdc\x28\x28"
            elif 600 <= x <= 850 and 260 <= y <= 510:
                raw += b"\x28\x50\xdc"
            else:
                raw += b"\xe6\xe6\xe6"

    def khoi(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + khoi(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + khoi(b"IDAT", zlib.compress(bytes(raw), 6)) + khoi(b"IEND", b""))


def anh_data_url():
    import base64
    return "data:image/png;base64," + base64.b64encode(png_thu()).decode("ascii")


# ---------------------------------------------------------------- goi chat (mot cuc)
def chat_mot_cuc(base, model, noi_dung, max_tokens, temperature=0.7, timeout=300.0):
    """Khong stream. Tra ca `content` LAN `reasoning_content`.

    !! Phai doc CA HAI. Ho so nay chay `--reasoning-format deepseek`, tuc khoi
    <think> bi tach sang mot truong rieng. Mot luot ma model con dang nghi khi
    het `max_tokens` se tra `content` RONG nhung `reasoning_content` day chu --
    do KHONG phai loi engine. Phep do G1 dau tien (11/09 21:43) da ket luan nham
    "tra loi rong" dung vi chi doc `content` voi max_tokens=32.
    """
    body = {"model": model, "messages": [{"role": "user", "content": noi_dung}],
            "max_tokens": max_tokens, "temperature": temperature, "top_p": 0.95,
            "seed": random.randint(0, 10 ** 9), "stream": False}
    t0 = time.time()
    ma, t = http("POST", base + "/v1/chat/completions", body, timeout=timeout)
    d = json.loads(t)
    tin = ((d.get("choices") or [{}])[0].get("message") or {})
    return {"ma": ma, "wall": round(time.time() - t0, 3),
            "noi_dung": tin.get("content") or "",
            "reasoning": tin.get("reasoning_content") or "",
            "timings": d.get("timings") or {}, "usage": d.get("usage") or {}}


def so_metrics(base):
    """Doc /metrics cua llama-server (Prometheus text) thanh dict ten -> so.

    Dong co nhan duoc giu nguyen o khoa day du VA cong don vao khoa khong nhan:
    ti le chap nhan suy doan cua draft-mtp nam o
    `llamacpp:spec_decode_num_accepted_tokens_per_pos_total` co nhan pos.
    """
    ra = {}
    try:
        _, t = http("GET", base + "/metrics", timeout=10)
    except Exception:  # noqa: BLE001
        return ra
    for dong in t.splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#"):
            continue
        phan = dong.rsplit(" ", 1)
        if len(phan) != 2:
            continue
        khoa, gt = phan[0].strip(), phan[1].strip()
        try:
            so = float(gt)
        except ValueError:
            continue
        ra[khoa] = so
        ten = khoa.split("{", 1)[0]
        if ten != khoa:
            ra[ten] = ra.get(ten, 0.0) + so
    return ra


# ---------------------------------------------------------------- bai do
def bai_c4(args, ghi):
    """Cn: `--luong` luot text dong thoi. Do THONG LUONG TONG, khong phai mot luot.

    Con so dang ke la `tok_s_tong` = tong token ra / wall cua CA CUM. Toc do
    tung luot bao gio cung thap hon C1 -- do la ky vong, khong phai loi.

    !! So luong KHONG con ghim cung 4. Chot L-14 (12/09) ha ca hai model xuong
       3 slot, va mot phep do ban 4 luot vao server 3 slot thi luot thu tu nam
       trong hang doi cua llama.cpp chu khong trong slot -- van ra mot con so,
       nhung la con so cua mot thu khac. Dat `--luong` bang `-np` cua server.
    """
    cho_ranh(args.base)
    so = int(getattr(args, "luong", 0) or 4)
    kq = [None] * so
    lay = LayMau(args.uuid)
    lay.start()

    def mot(i):
        try:
            kq[i] = chat_stream(args.base, args.model,
                                PROMPT_HUONG_DAN + nonce() + sinh_prompt(1150),
                                600, ignore_eos=False, timeout=600.0)
        except Exception as e:  # noqa: BLE001
            kq[i] = {"loi": repr(e)}

    ts = [threading.Thread(target=mot, args=(i,)) for i in range(so)]
    t_bd = time.time()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    wall = round(time.time() - t_bd, 3)
    lay.dung_lai()

    ok = [x for x in kq if x and x.get("usage")]
    tong_ra = sum((x["usage"] or {}).get("completion_tokens", 0) for x in ok)
    vram_dinh, shared_dinh, power_tb = lay.ket_qua()
    rec = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "kich_ban": "c4",
        "model": args.model, "uuid": args.uuid, "sha_gguf": SHA_GGUF_QWEN38,
        "so_luong": so, "so_thanh_cong": len(ok),
        "wall_s": wall, "tong_token_ra": tong_ra,
        "tok_s_tong": round(tong_ra / wall, 3) if wall else None,
        "tung_luot": [
            None if not x or not x.get("usage") else {
                "ttft_s": round(x["moc_token"][0] - x["t0"], 3) if x.get("moc_token") else None,
                "tok_s": (x.get("timings") or {}).get("predicted_per_second"),
                "token_vao": (x["usage"] or {}).get("prompt_tokens"),
                "token_ra": (x["usage"] or {}).get("completion_tokens"),
            } for x in kq],
        "loi": [x.get("loi") for x in kq if x and x.get("loi")],
        "vram_dinh_mib": vram_dinh, "shared_dinh_mib": shared_dinh, "power_w_tb": power_tb,
    }
    ghi(rec)
    return rec


def bai_anh(args, ghi):
    """Anh mot minh, roi mot anh + ba luot text dong thoi (dinh VRAM cua ho so gop)."""
    cho_ranh(args.base)
    url = anh_data_url()
    noi = [{"type": "text",
            "text": "Hinh TRON trong anh mau gi, va no nam ben trai hay ben phai?"},
           {"type": "image_url", "image_url": {"url": url}}]

    def mot_anh():
        return chat_mot_cuc(args.base, args.model, noi, 256, temperature=0.2, timeout=300.0)

    lay = LayMau(args.uuid)
    lay.start()
    try:
        mot_minh = mot_anh()
    except Exception as e:  # noqa: BLE001
        mot_minh = {"loi": repr(e)}
    lay.dung_lai()
    v1, s1, p1 = lay.ket_qua()
    rec1 = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "kich_ban": "anh",
            "kieu": "mot_minh", "model": args.model, "uuid": args.uuid, "kq": mot_minh,
            "token_vao": (mot_minh.get("usage") or {}).get("prompt_tokens"),
            "vram_dinh_mib": v1, "shared_dinh_mib": s1, "power_w_tb": p1}
    ghi(rec1)

    cho_ranh(args.base)
    ra = {"text": [None] * 3, "anh": None}
    lay2 = LayMau(args.uuid)
    lay2.start()

    def text(i):
        try:
            ra["text"][i] = chat_mot_cuc(args.base, args.model,
                                         nonce() + sinh_prompt(400), 256, timeout=300.0)
        except Exception as e:  # noqa: BLE001
            ra["text"][i] = {"loi": repr(e)}

    def anh():
        try:
            ra["anh"] = mot_anh()
        except Exception as e:  # noqa: BLE001
            ra["anh"] = {"loi": repr(e)}

    ts = [threading.Thread(target=text, args=(i,)) for i in range(3)] + [threading.Thread(target=anh)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    lay2.dung_lai()
    v2, s2, p2 = lay2.ket_qua()
    rec2 = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "kich_ban": "anh",
            "kieu": "anh_cung_3_text", "model": args.model, "uuid": args.uuid, "kq": ra,
            "vram_dinh_mib": v2, "shared_dinh_mib": s2, "power_w_tb": p2}
    ghi(rec2)
    return rec2


def bai_whale(args, ghi):
    """Whale (prefill rat dai) chay cung ba minnow lech gio.

    Do thu duy nhat dang so o mot pool KV dung chung: mot luot prefill khong lo
    co lam KV can kiet -- va o llama.cpp `-np N -kvu`, KV can kiet giet TAT CA
    slot chu khong rieng slot gay ra no (server-context.cpp:3688-3724).
    """
    cho_ranh(args.base)
    whale_txt = PROMPT_HUONG_DAN + nonce() + sinh_prompt(args.whale_tu)
    ra = {"minnow": [None] * 3, "whale": None}
    lay = LayMau(args.uuid)
    lay.start()

    def whale():
        try:
            ra["whale"] = chat_mot_cuc(args.base, args.model,
                                       whale_txt + " Tom tat doan tren trong mot cau.",
                                       64, timeout=900.0)
        except Exception as e:  # noqa: BLE001
            ra["whale"] = {"loi": repr(e)}

    def minnow(i):
        try:
            kq = chat_stream(args.base, args.model, nonce() + sinh_prompt(300), 200,
                             ignore_eos=False, timeout=600.0)
            ra["minnow"][i] = {
                "ttft_s": round(kq["moc_token"][0] - kq["t0"], 3) if kq.get("moc_token") else None,
                "tok_s": (kq.get("timings") or {}).get("predicted_per_second"),
                "token_ra": (kq.get("usage") or {}).get("completion_tokens"),
                "wall_s": round(kq["t_cuoi"] - kq["t0"], 3)}
        except Exception as e:  # noqa: BLE001
            ra["minnow"][i] = {"loi": repr(e)}

    tw = threading.Thread(target=whale)
    tw.start()
    ts = []
    for i, tre in enumerate((6, 8, 8)):
        time.sleep(tre)
        t = threading.Thread(target=minnow, args=(i,))
        t.start()
        ts.append(t)
    for t in ts:
        t.join()
    tw.join()
    lay.dung_lai()
    v, s, p = lay.ket_qua()
    rec = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "kich_ban": "whale",
           "model": args.model, "uuid": args.uuid, "whale_tu_muc_tieu": args.whale_tu,
           "kq": ra, "vram_dinh_mib": v, "shared_dinh_mib": s, "power_w_tb": p}
    ghi(rec)
    return rec


KHUON_DAU = "DAU-%d-%03d"


def phan_tich_dau(text, dau):
    """Doc mot tra loi cua `mtp_gate` va noi no co dau hieu lan slot khong.

    Ham THUAN (khong mang, khong trang thai) de `tests/test_1211` goi thang.

    !! DINH NGHIA HEP CO CHU DICH. Ban dau cua ham nay coi **moi** chuoi bat dau
    bang "DAU-" khac dau cua chinh minh la lan slot. Chay that 200 luot (12/09)
    thi no bao hai vu -- va ca hai deu GIA:

        luot DAU-1-040 -> thay "DAU-1-0"
        luot DAU-2-047 -> thay "DAU-2"

    Ca hai la MANH VO tien to cua chinh dau no (model xuong dong hay chen dinh
    dang giua chuoi), va ca hai luot deu doc lai dung dau minh. Khong co mot
    byte nao cua slot khac.

    Lan slot THAT phai la mot dau DUNG KHUON `DAU-<slot>-<ba chu so>` va thuoc
    ve mot **slot khac**. Do la dieu #27572 mo ta, va la dieu cong nay do.

    Manh vo van duoc TRA VE rieng chu khong bi vut: no khong lam truot cong,
    nhung no la du lieu -- thu hep mot phep kiem cho toi khi no xanh thi de,
    thu hep cho no do dung thu no tuyen bo moi la viec phai lam.
    """
    ra = {"rong": not (text or "").strip(), "co_dau_minh": dau in (text or ""),
          "dau_slot_khac": [], "manh_vo": []}
    for tho in (text or "").replace("\n", " ").split():
        x = tho.strip(".,;:!?\"'()[]{}*`<>")
        if not x.startswith("DAU-") or x == dau:
            continue
        phan = x.split("-")
        dung_khuon = (len(phan) == 3 and phan[1].isdigit()
                      and len(phan[2]) == 3 and phan[2].isdigit())
        if dung_khuon:
            ra["dau_slot_khac"].append(x)
        elif dau.startswith(x):
            ra["manh_vo"].append(x)
        else:
            # Khong dung khuon VA khong phai tien to cua dau minh: khong ket
            # luan duoc gi, nhung cung khong duoc im lang nuot di.
            ra["manh_vo"].append(x)
    ra["dau_slot_khac"] = sorted(set(ra["dau_slot_khac"]))
    ra["manh_vo"] = sorted(set(ra["manh_vo"]))
    return ra


# Dai hon mot ubatch mac dinh (512) de ep prefill chia nhieu lo -- cho ma hai
# bao cao cong dong (#27572, #26750) noi draft-mtp lan slot voi -np > 1.
_MTP_NHOI = 900


def bai_mtp_gate(args, ghi):
    """G2: draft-mtp co an toan voi `-np 4` khong.

    Hai bao cao cong dong tren dung dong build ho nha nay: #27572 (tra loi RONG
    khi -np > 1) va #26750 (Blackwell -32%). Ca hai la thu mot phep do "trung
    binh" KHONG thay: chung hong theo LUOT, khong theo toc do trung binh.

    Nen cong nay khong do toc do. Moi luot mang mot DAU rieng `DAU-<slot>-<n>`
    va bai kiem la:
      * luot nao cung phai co chu (content HOAC reasoning) -- 0 luot rong;
      * KHONG luot nao duoc chua dau cua luot khac (day la dau hieu lan slot);
      * tong `spec_decode_num_accepted...` phai TANG (draft-mtp that su dang
        lam viec chu khong am tham tat).

    Mot phan luot deo prompt dai hon ubatch va mot phan deo anh: hai duong ma
    bao cao cong dong noi la de kich hoat loi nhat.
    """
    cho_ranh(args.base)
    m_truoc = so_metrics(args.base)
    luong = int(getattr(args, "luong", 0) or 4)
    moi_luong = (args.lan_gate + luong - 1) // luong
    ket = []
    khoa = threading.Lock()
    url = anh_data_url() if args.gate_anh else None

    def mot_luong(slot):
        for n in range(moi_luong):
            dau = KHUON_DAU % (slot, n)
            nhoi = sinh_prompt(_MTP_NHOI) if (n % 3 == 0) else sinh_prompt(40)
            chu = ("Doc lai CHINH XAC chuoi dinh danh sau, mot minh no, khong them gi khac: "
                   "%s (ngu canh bo qua: %s)" % (dau, nhoi))
            deo_anh = bool(url) and (n % 5 == 0)
            noi = ([{"type": "text", "text": chu},
                    {"type": "image_url", "image_url": {"url": url}}] if deo_anh else chu)
            try:
                r = chat_mot_cuc(args.base, args.model, noi, 200, temperature=0.2, timeout=300.0)
                text = (r["noi_dung"] or "") + " " + (r["reasoning"] or "")
                ban_ghi = dict(phan_tich_dau(text, dau),
                               slot=slot, n=n, dau=dau, co_anh=deo_anh,
                               token_vao=(r["usage"] or {}).get("prompt_tokens"),
                               token_ra=(r["usage"] or {}).get("completion_tokens"))
            except Exception as e:  # noqa: BLE001
                ban_ghi = {"slot": slot, "n": n, "dau": dau, "loi": repr(e)}
            with khoa:
                ket.append(ban_ghi)

    ts = [threading.Thread(target=mot_luong, args=(i,)) for i in range(luong)]
    t_bd = time.time()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    wall = round(time.time() - t_bd, 3)
    m_sau = so_metrics(args.base)

    ten_spec = [k for k in m_sau if "spec_decode_num_accepted" in k and "{" not in k]
    spec_truoc = sum(m_truoc.get(k, 0.0) for k in ten_spec)
    spec_sau = sum(m_sau.get(k, 0.0) for k in ten_spec)

    rong = [r for r in ket if r.get("rong")]
    thieu_dau = [r for r in ket if not r.get("loi") and not r.get("co_dau_minh")]
    lan_slot = [r for r in ket if r.get("dau_slot_khac")]
    manh_vo = [r for r in ket if r.get("manh_vo")]
    loi = [r for r in ket if r.get("loi")]
    dat = (not rong) and (not lan_slot) and (not loi) and spec_sau > spec_truoc

    rec = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "kich_ban": "mtp_gate",
        "model": args.model, "uuid": args.uuid, "so_luot": len(ket), "so_luong": luong,
        "wall_s": wall,
        "so_rong": len(rong), "so_thieu_dau_minh": len(thieu_dau),
        "so_lan_slot": len(lan_slot), "so_manh_vo": len(manh_vo), "so_loi": len(loi),
        "spec_accepted_truoc": spec_truoc, "spec_accepted_sau": spec_sau,
        "ten_metric_spec": sorted(ten_spec),
        "DAT": dat,
        # `so_thieu_dau_minh` KHONG lam truot cong: model co quyen dien dat lai
        # thay vi doc lai nguyen van, do la hanh vi model chu khong phai loi
        # engine. Thu lam truot cong la LAN SLOT va TRA LOI RONG -- dung hai
        # dau hieu ma #27572 mo ta.
        "vi_du_lan_slot": lan_slot[:5], "vi_du_rong": rong[:5], "vi_du_loi": loi[:3],
        # Manh vo KHONG lam truot cong (xem `phan_tich_dau`), nhung van in ra:
        # mot con so bi giau di la mot con so khong ai kiem lai duoc.
        "vi_du_manh_vo": manh_vo[:5],
    }
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
    "c4": bai_c4,
    "whale": bai_whale,
    "anh": bai_anh,
    "mtp_gate": bai_mtp_gate,
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
    ap.add_argument("--whale-tu", dest="whale_tu", type=int, default=45000,
                    help="so tu cua prompt whale (~1,3 token/tu); mac dinh ~60K token")
    ap.add_argument("--lan-gate", dest="lan_gate", type=int, default=200,
                    help="tong so luot cua kich ban mtp_gate (chia deu 4 luong)")
    ap.add_argument("--gate-anh", dest="gate_anh", action="store_true",
                    help="mtp_gate deo them anh vao 1/5 so luot (can ho so co mmproj)")
    ap.add_argument("--luong", type=int, default=4,
                    help="so luong dong thoi cua mtp_gate (mac dinh 4; dat bang -np cua server)")
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
