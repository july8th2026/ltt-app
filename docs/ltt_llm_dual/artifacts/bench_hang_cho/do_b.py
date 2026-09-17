"""do_b.py - lo do may B trong CUA SO BAO TRI (17/09/2026). Thuan ASCII, chi stdlib.

Chay TREN MAY B bang Scheduled Task SYSTEM + pythonw (khoi_dong_b.ps1). Moi phep do
dung MOT llama-server RIENG tren cong thu (8290/8292/8294) - KHONG di qua llama-swap,
KHONG cham 8280/8281/8282, KHONG sua cau hinh nao. Tham so = DUNG dong lenh
production (chep tu /running cua llama-swap 17/09, gom `--no-cache-idle-slots` ma
llm_gateway/deploy/llama-swap.yaml tren main CHUA co), chi doi DUNG tham so dang do.

Phep do (--do, ghep bang dau phay, chay theo thu tu dua vao):
  m1     LTT-3.5 -np 3/4/6 (-kvu, MTP): VRAM dedicated+shared, tok/s tung luong va
         tong o 1..6 luong, prompt tron 1k/8k/32k, kiem tra tra loi rong, cap slot
         {0,2} (llama.cpp #25840).
  m3_35  LTT-3.5: toc do cac luong decode dang chay trong luc prefill 32k va 163k,
         -b 2048 vs 512.
  m5     tran KV co y (3.5, -c 16384 -np 3 -kvu): lieu b10883 giet het cac slot?
  m6     ty le trung prompt cache (/metrics prompt_tokens_cached_total) duoi tai tron,
         --cache-ram mac dinh (8192) vs --cache-ram 0.
  m3_38  nhu m3_35 cho LTT-3.8 (32k va 128k).
  m2     LTT-3.8 -np 4/5 voi -c ha cho vua (449 MiB/slot), doi chung np3 truoc;
         kiem tran truoc, cong decode don >= 60 tok/s roi moi do dong thoi.

PREFLIGHT (truoc MOI cau hinh, khong qua duoc => HUY ca lo, ghi ly do):
  * llama-swap 127.0.0.1:8280/running doc duoc; moi model dang nap: /slots khong
    slot nao is_processing, /metrics requests_processing == 0 va deferred == 0.
  * utilization.gpu cua MOI card (10 mau / 5 s) trung binh <= 10 %.
  * VRAM da dung cua card dich <= nguong (tuc model production cua card do da nha).
NGAN SACH: --han-phut la tran CUNG cho ca lo; moi phep co tran rieng (HAN_PHEP).
  Mot luong gac: qua han + 120 s => giet server thu va os._exit(3).
DON DEP: finally + luong gac giet MOI llama-server co `--port 829x` (chi cong thu).
KET QUA: <ra>\\<do>.jsonl tung dong ngay khi co; nhip tim <ra>\\trang_thai.json.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import random
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

BIN = r"H:\LTT_LLM\bin\llamacpp\llama-server.exe"
M = "H:/LTT_LLM/models"
UUID38 = "GPU-26623278-4fa5-82db-4306-237651b03e78"
UUID35 = "GPU-ebecd0a4-a8a7-14a5-dad1-21565f6dc1df"
SWAP = "http://127.0.0.1:8280"
CONG_THU = (8290, 8292, 8294)
P38, P35, PTRAN = 8290, 8292, 8294

# Dong lenh production, chep tu /running 17/09/2026 15:0x (khong phai tu kho).
CHUNG = ["--jinja", "--reasoning-format", "deepseek", "-fa", "1", "-ngl", "999", "-kvu",
         "--top-p", "0.95", "--top-k", "20", "--min-p", "0", "--metrics",
         "--no-cache-idle-slots"]


def args35(port, np_=3, c=262144, them=()):
    return (["-m", M + "/Qwen3.5-9B-Q6_K-unsloth.gguf",
             "--mmproj", M + "/mmproj-9B-F16-unsloth.gguf",
             "--chat-template-file", M + "/chat_template_v22.5.jinja"] + CHUNG +
            ["--reasoning", "on", "--reasoning-budget", "2048", "--temp", "1.0",
             "-c", str(c), "-np", str(np_),
             "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
             "--spec-type", "draft-mtp", "--spec-draft-n-max", "2",
             "--host", "127.0.0.1", "--port", str(port)] + list(them))


def args38(port, np_=3, c=221184, them=()):
    return (["-m", M + "/Qwen3.8-27B-UD-Q4_K_M.gguf",
             "--mmproj", M + "/mmproj-F16.gguf",
             "--chat-template-file", M + "/chat_template_v22.5.jinja"] + CHUNG +
            ["--reasoning-effort", "xhigh", "--reasoning-budget", "4096", "--temp", "1.0",
             "-c", str(c), "-np", str(np_),
             "--cache-type-k", "q4_0", "--cache-type-v", "q4_0",
             "--spec-type", "draft-mtp", "--spec-draft-n-max", "2",
             "--host", "127.0.0.1", "--port", str(port)] + list(them))


# Tran rieng tung phep (phut) - uoc luong x ~1,4.
HAN_PHEP = {"m1": 45, "m3_35": 26, "m5": 10, "m6": 12, "m3_38": 32, "m2": 35}
# VRAM toi da cua card dich de coi la "production da nha" (MiB; desktop giu ~0,3-0,9 GB).
VRAM_SACH = {UUID35: 1500, UUID38: 1200}

RA = "."
HAN = 0.0
DANG_CHAY: list = []          # Popen server thu dang song
_khoa = threading.Lock()


class HuyLo(Exception):
    pass


class HetGio(Exception):
    pass


# ---------------------------------------------------------------- ghi chep
def ghi(do: str, d: dict) -> None:
    d = dict(d)
    d.setdefault("luc", time.strftime("%Y-%m-%dT%H:%M:%S"))
    with _khoa, open(os.path.join(RA, do + ".jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(d, ensure_ascii=True) + "\n")
        f.flush()


def nhip(do: str, buoc: str) -> None:
    try:
        with open(os.path.join(RA, "trang_thai.json"), "w", encoding="ascii") as f:
            json.dump({"do": do, "buoc": buoc, "luc": time.strftime("%H:%M:%S"),
                       "con_giay": round(HAN - time.time()), "pid": os.getpid()}, f)
    except OSError:
        pass
    with _khoa, open(os.path.join(RA, "nhat_ky.txt"), "a", encoding="ascii", errors="replace") as f:
        f.write(time.strftime("%H:%M:%S") + "  " + do + "  " + buoc + "\n")


def con(giay: float) -> bool:
    return time.time() + giay < HAN


# ---------------------------------------------------------------- HTTP
def hj(method, url, body=None, timeout=10.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        try:
            return r.status, json.loads(raw or b"null")
        except ValueError:
            return r.status, raw.decode("utf-8", "replace")


def metrics(port) -> dict:
    req = urllib.request.Request("http://127.0.0.1:%d/metrics" % port)
    with urllib.request.urlopen(req, timeout=10) as r:
        txt = r.read().decode("utf-8", "replace")
    ra = {}
    for dong in txt.splitlines():
        if dong.startswith("#") or " " not in dong:
            continue
        k, v = dong.rsplit(" ", 1)
        try:
            ra[k] = float(v)
        except ValueError:
            pass
    return ra


def luong(port, body, kq: dict, huy: threading.Event | None = None, timeout=1800.0):
    """Mot luot SSE. Ghi moc thoi gian tung khoi (de tinh toc do trong cua so)."""
    body = dict(body)
    body.setdefault("stream", True)
    body["stream"] = True
    body.setdefault("stream_options", {"include_usage": True})
    kq.update({"t_gui": time.time(), "t_dau": None, "t_cuoi": None, "moc": [],
               "noi_dung_ky_tu": 0, "suy_nghi_ky_tu": 0, "ket_thuc": None,
               "usage": None, "timings": None, "loi": None, "bi_huy": False})
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("POST", "/v1/chat/completions", json.dumps(body),
                     {"Content-Type": "application/json"})
        r = conn.getresponse()
        if r.status != 200:
            kq["loi"] = "http %d: %s" % (r.status, r.read()[:300].decode("utf-8", "replace"))
            return kq
        while True:
            if huy is not None and huy.is_set():
                kq["bi_huy"] = True
                break
            dong = r.readline()
            if not dong:
                break
            dong = dong.strip()
            if not dong.startswith(b"data:"):
                continue
            p = dong[5:].strip()
            if p == b"[DONE]":
                break
            try:
                d = json.loads(p)
            except ValueError:
                continue
            if d.get("error"):
                kq["loi"] = json.dumps(d["error"])[:300]
                break
            if d.get("timings"):
                kq["timings"] = d["timings"]
            if d.get("usage"):
                kq["usage"] = d["usage"]
            for ch in d.get("choices") or []:
                de = ch.get("delta") or {}
                c1 = de.get("content") or ""
                c2 = de.get("reasoning_content") or ""
                if c1 or c2:
                    t = time.time()
                    if kq["t_dau"] is None:
                        kq["t_dau"] = t
                    kq["moc"].append(t)
                    kq["noi_dung_ky_tu"] += len(c1)
                    kq["suy_nghi_ky_tu"] += len(c2)
                if ch.get("finish_reason"):
                    kq["ket_thuc"] = ch["finish_reason"]
    except Exception as e:                                   # noqa: BLE001
        kq["loi"] = "%s: %s" % (type(e).__name__, e)
    finally:
        kq["t_cuoi"] = time.time()
        try:
            conn.close()
        except Exception:                                    # noqa: BLE001
            pass
    return kq


def token_ra(kq) -> int:
    u = kq.get("usage") or {}
    if u.get("completion_tokens"):
        return int(u["completion_tokens"])
    t = kq.get("timings") or {}
    return int(t.get("predicted_n") or len(kq.get("moc") or []))


def gon(kq) -> dict:
    """Ban rut gon cua mot luot de ghi (bo danh sach moc)."""
    t = kq.get("timings") or {}
    n = token_ra(kq)
    dec = None
    if kq.get("t_dau") and kq.get("t_cuoi") and kq["t_cuoi"] > kq["t_dau"] and n > 1:
        dec = round(n / (kq["t_cuoi"] - kq["t_dau"]), 2)
    return {"ttft_s": round(kq["t_dau"] - kq["t_gui"], 3) if kq.get("t_dau") else None,
            "token_ra": n, "decode_tps_khach": dec,
            "decode_tps_server": t.get("predicted_per_second"),
            "prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n"),
            "prefill_tps": t.get("prompt_per_second"),
            "ket_thuc": kq.get("ket_thuc"), "loi": kq.get("loi"), "bi_huy": kq.get("bi_huy"),
            "noi_dung_ky_tu": kq.get("noi_dung_ky_tu"), "suy_nghi_ky_tu": kq.get("suy_nghi_ky_tu"),
            "rong": (kq.get("noi_dung_ky_tu") or 0) == 0}


def toc_do_cua_so(kqs, t0, t1) -> float | None:
    """Tong token/s cua cac luong trong [t0, t1], quy doi khoi -> token bang ty le cuoi."""
    if t1 - t0 < 0.5:
        return None
    tong = 0.0
    for k in kqs:
        moc = k.get("moc") or []
        if not moc:
            continue
        he_so = token_ra(k) / max(1, len(moc))
        tong += sum(1 for t in moc if t0 <= t <= t1) * he_so
    return round(tong / (t1 - t0), 2)


def gap_max(kq, t0, t1) -> float | None:
    moc = [t for t in (kq.get("moc") or []) if t0 - 5 <= t <= t1]
    if len(moc) < 2:
        return None
    return round(max(b - a for a, b in zip(moc, moc[1:], strict=False)), 2)


# ---------------------------------------------------------------- prompt
_TU = ("thi truong nguoi dung he thong mo hinh du lieu phan tich ket qua quy trinh "
       "san pham khach hang dich vu chat luong toc do bao cao tai lieu huong dan "
       "network latency cache memory throughput request response server client "
       "kiem thu trien khai van hanh ngan sach chi phi rui ro ke hoach tien do").split()
_TI_LE: dict = {}


def ti_le_ky_tu(port) -> float:
    if port in _TI_LE:
        return _TI_LE[port]
    rng = random.Random(7)
    mau = " ".join(rng.choice(_TU) for _ in range(3000))
    try:
        _, d = hj("POST", "http://127.0.0.1:%d/tokenize" % port, {"content": mau}, 60)
        r = len(mau) / max(1, len(d.get("tokens") or []))
    except Exception:                                        # noqa: BLE001
        r = 4.0
    _TI_LE[port] = r
    return r


def prompt(port, n_token: int, nonce: str, seed: int = 0, cuoi="Tom tat doan tren trong 3 cau.") -> str:
    rng = random.Random(seed or hash(nonce) & 0xFFFFFFFF)
    so_ky_tu = int(n_token * ti_le_ky_tu(port))
    phan = []
    dai = 0
    while dai < so_ky_tu:
        w = rng.choice(_TU)
        phan.append(w)
        dai += len(w) + 1
    return "[" + nonce + "] " + " ".join(phan) + "\n\n" + cuoi


def nonce() -> str:
    return "%08x" % random.getrandbits(32)


# ---------------------------------------------------------------- GPU
def nvsmi() -> dict:
    out = subprocess.run(["nvidia-smi", "--query-gpu=uuid,memory.used,memory.total,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True,
                         timeout=20, creationflags=0x08000000).stdout
    ra = {}
    for dong in out.splitlines():
        c = [x.strip() for x in dong.split(",")]
        if len(c) == 4:
            ra[c[0]] = {"used": int(c[1]), "total": int(c[2]), "util": int(c[3])}
    return ra


def bo_nho_tien_trinh(pid: int) -> dict:
    ps = ("$d=0;$s=0;foreach($c in (Get-Counter '\\GPU Process Memory(pid_%d_*)\\Dedicated Usage',"
          "'\\GPU Process Memory(pid_%d_*)\\Shared Usage' -ErrorAction Stop).CounterSamples)"
          "{ if($c.Path -like '*dedicated*'){$d+=$c.CookedValue}else{$s+=$c.CookedValue} };"
          "[math]::Round($d/1MB,1).ToString()+' '+[math]::Round($s/1MB,1).ToString()") % (pid, pid)
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                             text=True, timeout=60, creationflags=0x08000000).stdout.split()
        return {"dedicated_mib": float(out[0]), "shared_mib": float(out[1])}
    except Exception:                                        # noqa: BLE001
        return {"dedicated_mib": None, "shared_mib": None}


def anh_vram(uuid, pid) -> dict:
    g = nvsmi().get(uuid, {})
    d = {"vram_used_mib": g.get("used"), "vram_total_mib": g.get("total"),
         "bien_mib": (g["total"] - g["used"]) if g else None}
    d.update(bo_nho_tien_trinh(pid))
    return d


# ---------------------------------------------------------------- preflight
def preflight(do: str, uuid_dich: str) -> None:
    nhip(do, "preflight")
    ly_do = []
    try:
        _, run = hj("GET", SWAP + "/running", timeout=10)
        for m in (run or {}).get("running") or []:
            proxy = m.get("proxy") or ""
            if m.get("state") != "ready" or not proxy:
                ly_do.append("model %s o trang thai %s" % (m.get("model"), m.get("state")))
                continue
            port = int(proxy.rsplit(":", 1)[1])
            _, slots = hj("GET", "http://127.0.0.1:%d/slots" % port, timeout=10)
            ban = [s.get("id") for s in slots or [] if s.get("is_processing")]
            mt = metrics(port)
            if ban or mt.get("llamacpp:requests_processing", 0) > 0 or mt.get("llamacpp:requests_deferred", 0) > 0:
                ly_do.append("llama-swap %s con luot: slots %s processing %s deferred %s" % (
                    m.get("model"), ban, mt.get("llamacpp:requests_processing"),
                    mt.get("llamacpp:requests_deferred")))
    except Exception as e:                                   # noqa: BLE001
        ly_do.append("khong doc duoc llama-swap (khong biet != ranh): %s" % e)
    mau: dict = {}
    for _ in range(10):
        for u, g in nvsmi().items():
            mau.setdefault(u, []).append(g["util"])
        time.sleep(0.5)
    for u, ds in mau.items():
        if statistics.mean(ds) > 10:
            ly_do.append("GPU %s util trung binh %.1f%% > 10%%" % (u[-6:], statistics.mean(ds)))
    g = nvsmi().get(uuid_dich)
    if g is None:
        ly_do.append("khong thay card dich " + uuid_dich)
    elif g["used"] > VRAM_SACH[uuid_dich]:
        ly_do.append("card dich %s da dung %d MiB > %d (model production cua card nay chua nha? "
                     "xem cua_so_b.ps1 -Buoc nha35/nha38/dung_comfy)" % (uuid_dich[-6:], g["used"],
                                                                          VRAM_SACH[uuid_dich]))
    ghi(do, {"su_kien": "preflight", "dat": not ly_do, "ly_do": ly_do,
             "util_tb": {u[-6:]: round(statistics.mean(v), 1) for u, v in mau.items()}})
    if ly_do:
        raise HuyLo("; ".join(ly_do))


# ---------------------------------------------------------------- server thu
def quet_cong_thu() -> None:
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='llama-server.exe'\" | Where-Object { "
          "$_.CommandLine -match '--port (8290|8292|8294)(\\s|$)' } | ForEach-Object { "
          "Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                   timeout=60, creationflags=0x08000000)


def bat_server(do, nhan, args, uuid, port, han_nap=600):
    quet_cong_thu()
    time.sleep(3)
    nen = nvsmi().get(uuid, {})
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = uuid
    out = open(os.path.join(RA, "%s_%s.log" % (do, nhan)), "wb")
    t0 = time.time()
    p = subprocess.Popen([BIN] + args, stdout=out, stderr=subprocess.STDOUT, env=env,
                         creationflags=0x08000000)
    DANG_CHAY.append(p)
    xanh = False
    while time.time() - t0 < han_nap and con(30):
        if p.poll() is not None:
            break
        try:
            if hj("GET", "http://127.0.0.1:%d/health" % port, timeout=3)[1].get("status") == "ok":
                xanh = True
                break
        except Exception:                                    # noqa: BLE001
            pass
        time.sleep(1)
    d = {"su_kien": "nap", "nhan": nhan, "xanh": xanh, "giay_nap": round(time.time() - t0, 1),
         "bin": BIN, "args": " ".join(args), "cuda_visible_devices": uuid,
         "vram_nen_truoc_nap_mib": nen.get("used"), "util_truoc_nap": nen.get("util")}
    if xanh:
        try:
            pr = hj("GET", "http://127.0.0.1:%d/props" % port, timeout=10)[1]
            d["build_info"] = pr.get("build_info")
            d["n_ctx"] = (pr.get("default_generation_settings") or {}).get("n_ctx")
            d["total_slots"] = pr.get("total_slots")
        except Exception as e:                               # noqa: BLE001
            d["build_info"] = "loi %s" % e
        time.sleep(2)
        d.update(anh_vram(uuid, p.pid))
    else:
        d["exit"] = p.poll()
    ghi(do, d)
    return p, xanh, d


def tat_server(p) -> None:
    try:
        p.kill()
        p.wait(30)
    except Exception:                                        # noqa: BLE001
        pass
    if p in DANG_CHAY:
        DANG_CHAY.remove(p)
    quet_cong_thu()
    time.sleep(4)


def chay_song_song(port, bodies, timeout=1800.0, huy=None):
    kqs = [dict() for _ in bodies]
    ts = [threading.Thread(target=luong, args=(port, b, k, huy, timeout), daemon=True)
          for b, k in zip(bodies, kqs, strict=True)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return kqs


def body_tp(port, n_vao, max_tok, **them):
    b = {"model": "x", "messages": [{"role": "user", "content": prompt(port, n_vao, nonce())}],
         "max_tokens": max_tok, "ignore_eos": True, "seed": random.randint(0, 10 ** 9)}
    b.update(them)
    return b


def dot_dong_thoi(do, port, nhan, k, kich_thuoc, max_tok=400):
    """k luong cung luc; toc do tong trong cua so ma CA k luong deu dang decode."""
    bodies = [body_tp(port, kich_thuoc[i % len(kich_thuoc)], max_tok) for i in range(k)]
    t0 = time.time()
    kqs = chay_song_song(port, bodies)
    dau = [x["t_dau"] for x in kqs if x.get("t_dau")]
    cuoi = [x["t_cuoi"] for x in kqs if x.get("t_dau")]
    chong = toc_do_cua_so(kqs, max(dau), min(cuoi)) if len(dau) == k else None
    ghi(do, {"su_kien": "dong_thoi", "nhan": nhan, "k": k,
             "prompt_token": [kich_thuoc[i % len(kich_thuoc)] for i in range(k)],
             "wall_s": round(time.time() - t0, 1),
             "tok_s_tong_khi_ca_k_decode": chong,
             "cua_so_chong_s": round(min(cuoi) - max(dau), 1) if len(dau) == k else None,
             "tok_s_tong_ca_dot": round(sum(token_ra(x) for x in kqs) / (time.time() - t0), 2),
             "tung_luong": [gon(x) for x in kqs]})


def kiem_rong(do, port, nhan, k, lan=2):
    cau = ["Giai thich ngan gon vi sao bau troi co mau xanh.",
           "Viet ham Python dao nguoc mot chuoi, kem mot vi du.",
           "So sanh TCP va UDP trong 4 gach dau dong.",
           "Tinh 37 * 43 va trinh bay cach tinh.",
           "Dich sang tieng Anh: Chung toi se bao tri he thong trong 30 phut.",
           "Liet ke 5 loi ich cua viec ngu du giac."]
    for l in range(lan):
        bodies = [{"model": "x", "max_tokens": 4096,
                   "messages": [{"role": "user", "content": "[%s] %s" % (nonce(), cau[(i + l) % len(cau)])}]}
                  for i in range(k)]
        kqs = chay_song_song(port, bodies, timeout=900)
        ghi(do, {"su_kien": "kiem_rong", "nhan": nhan, "k": k, "lan": l,
                 "so_rong": sum(1 for x in kqs if (x.get("noi_dung_ky_tu") or 0) == 0),
                 "tung_luong": [gon(x) for x in kqs]})


def cap_slot(do, port, nhan, cap_list):
    for cap in cap_list:
        bodies = [body_tp(port, 1000, 512, id_slot=s) for s in cap]
        kqs = chay_song_song(port, bodies, timeout=600)
        ghi(do, {"su_kien": "cap_slot", "nhan": nhan, "slots": list(cap),
                 "decode_tps_server": [(x.get("timings") or {}).get("predicted_per_second") for x in kqs],
                 "tung_luong": [gon(x) for x in kqs]})


def hai_job(do, port, nhan, max1=8000):
    """Cau hoi chu san pham: job 1 dang decode on dinh MOT MINH, job 2 vao (a) prompt
    ngan, (b) prompt 32k. Ghi moc tung khoi cua job 1 (tuong doi, ms) va toc do job 1
    trong tung pha: truoc | job 2 prefill | job 2 decode | sau; va toc do job 2."""
    for loai, n2 in (("a_ngan_1k", 1000), ("b_dai_32k", 32000)):
        if not con(4 * 60):
            raise HetGio()
        nhip(do, "%s hai_job %s" % (nhan, loai))
        huy = threading.Event()
        j1: dict = {}
        t1 = threading.Thread(target=luong, args=(port, body_tp(port, 1000, max1), j1, huy, 1800), daemon=True)
        t1.start()
        t_bd = time.time()
        while time.time() - t_bd < 120 and not j1.get("t_dau"):
            time.sleep(0.1)
        time.sleep(15)
        t2_gui = time.time()
        j2 = luong(port, body_tp(port, n2, 500), {}, None, 900)
        t2_dau = j2.get("t_dau") or j2.get("t_cuoi")
        t2_cuoi = j2.get("t_cuoi")
        time.sleep(10)
        t_het = time.time()
        huy.set()
        t1.join(60)
        g = t2_gui
        moc1 = [round((t - g) * 1000) for t in (j1.get("moc") or []) if g - 15 <= t <= t_het]
        he_so = round(token_ra(j1) / max(1, len(j1.get("moc") or [])), 3)
        ghi(do, {"su_kien": "hai_job", "nhan": nhan, "loai": loai, "prompt_job2": n2,
                 "job1_tok_s_truoc": toc_do_cua_so([j1], g - 12, g),
                 "job1_tok_s_trong_prefill_job2": toc_do_cua_so([j1], g + 0.3, t2_dau),
                 "job1_tok_s_trong_decode_job2": toc_do_cua_so([j1], t2_dau + 0.3, t2_cuoi),
                 "job1_tok_s_sau_job2": toc_do_cua_so([j1], t2_cuoi + 0.5, t_het),
                 "job1_khoang_lang_max_trong_prefill_s": gap_max(j1, g, t2_dau),
                 "job2_ttft_s": round(t2_dau - g, 3), "job2": gon(j2),
                 "job2_tok_s_decode": toc_do_cua_so([j2], t2_dau + 0.3, t2_cuoi),
                 "moc_job1_ms_tuong_doi_luc_gui_job2": moc1, "token_moi_khoi_job1": he_so,
                 "moc_job2_ms": {"dau": round((t2_dau - g) * 1000), "cuoi": round((t2_cuoi - g) * 1000)},
                 "job1": gon(j1)})
        time.sleep(3)


# ================================================================ PHEP DO
def m1():
    do = "m1"
    for np_ in (3, 4, 6):
        if not con(8 * 60):
            ghi(do, {"su_kien": "bo_qua_het_gio", "np": np_})
            break
        preflight(do, UUID35)
        nhan = "np%d" % np_
        nhip(do, "nap " + nhan)
        p, xanh, _ = bat_server(do, nhan, args35(P35, np_=np_), UUID35, P35)
        try:
            if not xanh:
                continue
            if np_ == 3:
                hai_job(do, P35, nhan)
            nhip(do, nhan + " cap slot")
            cap = [(0,), (2,), (0, 1), (1, 2), (0, 2)] + ([(1, 3), (0, 3)] if np_ >= 4 else [])
            cap_slot(do, P35, nhan, cap)
            for k, kt in [(1, [1000]), (1, [8000]), (1, [32000]), (2, [1000, 8000]),
                          (3, [1000, 8000, 32000]), (4, [1000, 8000, 32000]),
                          (5, [1000, 8000, 32000]), (6, [1000, 8000, 32000])]:
                if not con(90):
                    raise HetGio()
                nhip(do, "%s k=%d" % (nhan, k))
                dot_dong_thoi(do, P35, nhan, k, kt)
            nhip(do, nhan + " kiem rong")
            kiem_rong(do, P35, nhan, np_)
            ghi(do, dict({"su_kien": "vram_sau_tai", "nhan": nhan}, **anh_vram(UUID35, p.pid)))
        finally:
            tat_server(p)


def _m3(do, uuid, port, mk_args, dai):
    for b in (2048, 512):
        if not con(6 * 60):
            ghi(do, {"su_kien": "bo_qua_het_gio", "b": b})
            break
        preflight(do, uuid)
        nhan = "b%d" % b
        nhip(do, "nap " + nhan)
        p, xanh, _ = bat_server(do, nhan, mk_args(port, them=["-b", str(b), "-ub", "512"]), uuid, port)
        try:
            if not xanh:
                continue
            hai_job(do, port, nhan)
            for n_dai in (32000, dai):
                if not con(4 * 60):
                    raise HetGio()
                nhip(do, "%s prefill %d" % (nhan, n_dai))
                huy = threading.Event()
                dec = [dict(), dict()]
                ts = [threading.Thread(target=luong, args=(port, body_tp(port, 1000, 30000), k, huy, 3600),
                                       daemon=True) for k in dec]
                for t in ts:
                    t.start()
                t_bd = time.time()
                while time.time() - t_bd < 180 and not all(k.get("t_dau") for k in dec):
                    time.sleep(0.2)
                time.sleep(10)
                t_gui = time.time()
                dl = luong(port, {"model": "x", "max_tokens": 8, "ignore_eos": True,
                                  "messages": [{"role": "user", "content": prompt(port, n_dai, nonce())}]},
                           {}, None, 1800)
                t_xong_prefill = dl.get("t_dau") or dl.get("t_cuoi")
                time.sleep(10)
                t_het = time.time()
                huy.set()
                for t in ts:
                    t.join(60)
                ghi(do, {"su_kien": "prefill_chen", "nhan": nhan, "b": b, "prompt_token": n_dai,
                         "tok_s_decode_2_luong_truoc": toc_do_cua_so(dec, t_gui - 10, t_gui),
                         "tok_s_decode_2_luong_trong_prefill": toc_do_cua_so(dec, t_gui + 0.5, t_xong_prefill),
                         "tok_s_decode_2_luong_sau": toc_do_cua_so(dec, t_xong_prefill + 1, t_het),
                         "khoang_lang_max_s": [gap_max(k, t_gui, t_xong_prefill) for k in dec],
                         "giay_prefill": round(t_xong_prefill - t_gui, 1),
                         "luot_dai": gon(dl), "luong_decode": [gon(k) for k in dec]})
                time.sleep(3)
        finally:
            tat_server(p)


def m3_35():
    _m3("m3_35", UUID35, P35, args35, 163000)


def m3_38():
    _m3("m3_38", UUID38, P38, args38, 128000)


def m5():
    do = "m5"
    preflight(do, UUID35)
    nhip(do, "nap c16384")
    p, xanh, _ = bat_server(do, "c16384_np3", args35(PTRAN, np_=3, c=16384), UUID35, PTRAN)
    try:
        if not xanh:
            return
        for nhan, vao, ra in (("doi_chung_vua", 1000, 1500), ("tran_co_y", 3000, 4000)):
            if not con(3 * 60):
                raise HetGio()
            nhip(do, nhan)
            bodies = [body_tp(PTRAN, vao, ra) for _ in range(3)]
            kqs = chay_song_song(PTRAN, bodies, timeout=900)
            song = None
            try:
                song = hj("GET", "http://127.0.0.1:%d/health" % PTRAN, timeout=5)[1]
            except Exception as e:                           # noqa: BLE001
                song = "chet: %s" % e
            ghi(do, {"su_kien": "tran_kv", "nhan": nhan, "tong_can_token": 3 * (vao + ra),
                     "pool": 16384, "server_sau": song, "exit": p.poll(),
                     "tung_luong": [gon(x) for x in kqs]})
            sau = luong(PTRAN, body_tp(PTRAN, 500, 200), {}, None, 300)
            ghi(do, {"su_kien": "luot_moi_sau_" + nhan, "luot": gon(sau)})
        with open(os.path.join(RA, "m5_c16384_np3.log"), "rb") as f:
            dong = [x.decode("utf-8", "replace").strip() for x in f.read().splitlines()]
        tu = ("kv cache", "failed", "free space", "context", "shift", "truncat", "error", "abort")
        ghi(do, {"su_kien": "log_server", "dong": [x for x in dong if any(t in x.lower() for t in tu)][-60:]})
    finally:
        tat_server(p)


def _m6_tai():
    """Tai tron: 6 hoi thoai (chung system ~3k + tai lieu rieng ~2k, 5 luot) va 5
    luot la ~4k, 3 tho => 6 hoi thoai tranh 3 slot (buoc cache-ram phai cuu)."""
    he_thong = prompt(P35, 3000, "he-thong-chung", seed=11, cuoi="Ban la tro ly. Tra loi ngan.")
    lich_su = [[{"role": "system", "content": he_thong + "\n\nTai lieu rieng: " +
                 prompt(P35, 2000, "tai-lieu-%d" % i, seed=100 + i, cuoi="")}] for i in range(6)]
    hang: list = []
    for luot_ in range(5):
        hang.extend(("hoi", i, luot_) for i in range(6))
        hang.append(("la", -1, luot_))
    kq_all: list = []
    khoa = threading.Lock()

    def lam(v):
        loai, i, l = v
        msgs = None
        if loai == "la":
            b = body_tp(P35, 4000, 64)
        else:
            with khoa:
                msgs = list(lich_su[i]) + [{"role": "user", "content": "Cau hoi %d: y chinh cua doan %d la gi?" % (l, l)}]
            b = {"model": "x", "messages": msgs, "max_tokens": 150}
        k = luong(P35, b, {}, None, 600)
        with khoa:
            if msgs is not None:
                # Tra loi co dinh: lich su GIONG HET giua hai bien the cache.
                lich_su[i] = msgs + [{"role": "assistant", "content": "Da ghi nhan doan %d." % l}]
            kq_all.append(dict(gon(k), loai=loai, hoi_thoai=i, luot=l))

    def tho():
        while con(60):
            with khoa:
                if not hang:
                    return
                v = hang.pop(0)
            lam(v)

    ts = [threading.Thread(target=tho, daemon=True) for _ in range(3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return kq_all


def m6():
    do = "m6"
    for nhan, them in (("cache_ram_mac_dinh", []), ("cache_ram_0", ["--cache-ram", "0"])):
        if not con(5 * 60):
            ghi(do, {"su_kien": "bo_qua_het_gio", "nhan": nhan})
            break
        preflight(do, UUID35)
        nhip(do, "nap " + nhan)
        p, xanh, _ = bat_server(do, nhan, args35(P35, them=them), UUID35, P35)
        try:
            if not xanh:
                continue
            m0 = metrics(P35)
            kq_all = _m6_tai()
            m1_ = metrics(P35)
            dp = m1_.get("llamacpp:prompt_tokens_total", 0) - m0.get("llamacpp:prompt_tokens_total", 0)
            dc = m1_.get("llamacpp:prompt_tokens_cached_total", 0) - m0.get("llamacpp:prompt_tokens_cached_total", 0)
            hoi_kq = [x for x in kq_all if x["loai"] == "hoi"]
            ttft = [x["ttft_s"] for x in hoi_kq if x["ttft_s"]]
            ghi(do, {"su_kien": "cache", "nhan": nhan, "so_luot": len(kq_all),
                     "metrics_prompt_tokens": dp, "metrics_prompt_tokens_cached": dc,
                     "ty_le_trung_metrics": round(dc / (dp + dc), 4) if (dp + dc) else None,
                     "ghi_chu": "prompt_tokens_total co the chi dem token DA XU LY; ty le = cached/(processed+cached)",
                     "ttft_hoi_p50": statistics.median(ttft) if ttft else None,
                     "cache_n_tong": sum(x["cache_n"] or 0 for x in hoi_kq),
                     "prompt_n_tong": sum(x["prompt_n"] or 0 for x in hoi_kq),
                     "tung_luot": kq_all})
        finally:
            tat_server(p)


def m2():
    do = "m2"
    # KV 3.8 q4_0 do tu G1 (g1_matrix_luot2): 212992 -> 229376 = +448 MiB / 16384 token
    # => ~224 MiB / 8192. Mot slot them ton 449 MiB => bot 16384 token moi slot.
    MIB_MOI_8192 = 224.0
    ds = [(3, 221184)]
    for np_ in (4, 5):
        bot = int((np_ - 3) * 449 / MIB_MOI_8192 * 8192)
        c = 221184 - ((bot + 4095) // 4096) * 4096
        ds.append((np_, c))
    ghi(do, {"su_kien": "ke_hoach", "cau_hinh": ds, "cong_thuc": "c = 221184 - ceil((np-3)*449/224*8192 /4096)*4096"})
    shared_goc = None
    for np_, c in ds:
        if not con(7 * 60):
            ghi(do, {"su_kien": "bo_qua_het_gio", "np": np_})
            break
        preflight(do, UUID38)
        nhan = "np%d_c%d" % (np_, c)
        nhip(do, "nap " + nhan)
        p, xanh, d = bat_server(do, nhan, args38(P38, np_=np_, c=c), UUID38, P38)
        try:
            if not xanh:
                continue
            sh = d.get("shared_mib")
            if np_ == 3:
                shared_goc = sh
            tran = (d.get("bien_mib") is None or d["bien_mib"] < 300 or sh is None or
                    (shared_goc is not None and sh > shared_goc + 64))
            ghi(do, {"su_kien": "kiem_tran", "nhan": nhan, "tran": tran, "shared_mib": sh,
                     "shared_goc_np3": shared_goc, "bien_mib": d.get("bien_mib")})
            if tran and np_ != 3:
                continue
            don = []
            for _ in range(3):
                k = luong(P38, body_tp(P38, 1000, 512), {}, None, 600)
                don.append(gon(k))
            tps = [x["decode_tps_server"] or x["decode_tps_khach"] or 0 for x in don]
            dat = statistics.median(tps) >= 60
            ghi(do, {"su_kien": "cong_decode_don", "nhan": nhan, "tps": tps, "trung_vi": statistics.median(tps),
                     "dat_60": dat})
            if not dat and np_ != 3:
                continue
            for k in range(1, np_ + 1):
                if not con(2 * 60):
                    raise HetGio()
                nhip(do, "%s k=%d" % (nhan, k))
                dot_dong_thoi(do, P38, nhan, k, [1000, 8000, 32000])
            kiem_rong(do, P38, nhan, np_, lan=1)
            ghi(do, dict({"su_kien": "vram_sau_tai", "nhan": nhan}, **anh_vram(UUID38, p.pid)))
        finally:
            tat_server(p)


PHEP = {"m1": m1, "m3_35": m3_35, "m5": m5, "m6": m6, "m3_38": m3_38, "m2": m2}


def gac(han_cung):
    while True:
        time.sleep(5)
        if time.time() > han_cung:
            for p in list(DANG_CHAY):
                try:
                    p.kill()
                except Exception:                            # noqa: BLE001
                    pass
            quet_cong_thu()
            nhip("gac", "QUA HAN CUNG - da giet server thu, thoat 3")
            os._exit(3)


def main() -> int:
    global RA, HAN
    ap = argparse.ArgumentParser()
    ap.add_argument("--do", required=True)
    ap.add_argument("--ra", default=r"E:\AI\ltt_dual\bench_hang_cho\ket_qua")
    ap.add_argument("--han-phut", type=float, required=True)
    a = ap.parse_args()
    RA = a.ra
    os.makedirs(RA, exist_ok=True)
    t_lo = time.time()
    han_lo = t_lo + a.han_phut * 60
    threading.Thread(target=gac, args=(han_lo + 120,), daemon=True).start()
    ma = 0
    try:
        quet_cong_thu()
        for ten in [x.strip() for x in a.do.split(",") if x.strip()]:
            if ten not in PHEP:
                raise SystemExit("phep do la: " + ten)
            HAN = min(han_lo, time.time() + HAN_PHEP[ten] * 60)
            nhip(ten, "bat dau")
            ghi(ten, {"su_kien": "bat_dau", "han_phut": round((HAN - time.time()) / 60, 1)})
            try:
                PHEP[ten]()
                ghi(ten, {"su_kien": "xong"})
            except HetGio:
                ghi(ten, {"su_kien": "het_ngan_sach"})
            except HuyLo as e:
                ghi(ten, {"su_kien": "HUY_LO_PREFLIGHT", "ly_do": str(e)})
                nhip(ten, "HUY: " + str(e)[:300])
                ma = 2
                break
            except Exception as e:                           # noqa: BLE001
                ghi(ten, {"su_kien": "loi", "loi": "%s: %s" % (type(e).__name__, e)})
                ma = 1
    finally:
        for p in list(DANG_CHAY):
            tat_server(p)
        quet_cong_thu()
        nhip("lo", "KET THUC ma=%d sau %.1f phut" % (ma, (time.time() - t_lo) / 60))
    return ma


if __name__ == "__main__":
    sys.exit(main())
