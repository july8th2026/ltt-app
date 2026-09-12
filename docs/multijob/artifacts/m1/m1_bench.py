"""m1_bench.py -- THROWAWAY (spike M-1, chuong trinh multijob LLM). KHONG phai ma san pham.

Chay tren MAY B duoi Scheduled Task bang pythonw.exe (khong console). Chi stdlib.
Muc dich: do llama.cpp b10689 nhieu slot tren RTX 3090 (va chia 2 GPU) de chot D-02 / so slot N.

An toan:
  * NHUONG PRODUCTION: thay llama-swap (:8280) nap model la dung ngay, giet server thi nghiem.
  * Tien kiem: llama-swap /running rong va ca hai GPU < 3000 MiB, neu khong thi bo.
  * Moi config trong try/finally: server thi nghiem luon bi giet.
  * Nhip tim 15 s ra nhip.txt; ket qua ghi TUNG DONG ra ketqua.jsonl (khong doi cuoi lo).
  * Han cung toan lo 50 phut.
"""
import json
import os
import random
import re
import subprocess
import threading
import time
import traceback
import urllib.error
import urllib.request

ROOT = r"E:\AI\ltt_multijob_m1"
BIN = r"H:\LTT_LLM\bin\llamacpp\llama-server.exe"
MODELS = r"H:\LTT_LLM\models"
GGUF = MODELS + r"\Qwen3.8-27B-UD-Q4_K_M.gguf"
TEMPLATE = MODELS + r"\chat_template.jinja"
PORT = 8290
BASE = "http://127.0.0.1:%d" % PORT
SWAP = "http://127.0.0.1:8280"
OUT = os.path.join(ROOT, "ketqua.jsonl")
HB = os.path.join(ROOT, "nhip.txt")
T_BAT_DAU = time.time()
DEADLINE = T_BAT_DAU + 50 * 60
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200

# Co production (llama-swap.yaml macro CHUNG + ho so qwen38-api), tru --parallel/thiet bi.
CHUNG = ["-m", GGUF, "--jinja", "--chat-template-file", TEMPLATE,
         "--reasoning-format", "deepseek", "-fa", "1", "-ngl", "999",
         "--spec-type", "draft-mtp", "--spec-draft-n-max", "2",
         "-c", "204800", "-ctk", "q4_0", "-ctv", "q4_0", "--metrics",
         "--host", "127.0.0.1", "--port", str(PORT)]

# (ten, co them, bai do, dieu kien)
CAUHINH = [
    ("p1_3090", ["-np", "1", "-dev", "CUDA0"], ["c1", "c4", "wm"], None),
    ("p2_kvu_3090", ["-np", "2", "-kvu", "-dev", "CUDA0"], ["c1", "c4", "wm"], None),
    ("p4_kvu_3090", ["-np", "4", "-kvu", "-dev", "CUDA0"], ["c1", "c4", "wm"], None),
    ("p3_kvu_3090_ub128", ["-np", "3", "-kvu", "-ub", "128", "-dev", "CUDA0"],
     ["c1", "c4", "wm"], "p4_kvu_3090_hong"),
]
# Chu du an chot 11/09: Qwen3.8-27B CHI chay tren 3090; 5060 Ti de danh cho model khac.
# => KHONG do cau hinh chia 2 GPU. Ghim bang UUID (khong phu thuoc thu tu liet ke CUDA).
UUID_3090 = "GPU-26623278-4fa5-82db-4306-237651b03e78"
ENV_SERVER = dict(os.environ, CUDA_VISIBLE_DEVICES=UUID_3090)
GPU_3090 = 0   # chi so nvidia-smi cua 3090 tren may B (do 11/09)

TRANG_THAI = {"cauhinh": "-", "buoc": "khoi dong", "dung": False}
VRAM_DINH = {}
_khoa = threading.Lock()


def ghi(ban_ghi):
    ban_ghi["t"] = round(time.time() - T_BAT_DAU, 2)
    with _khoa:
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(ban_ghi, ensure_ascii=True) + "\n")


def nhip_tim():
    while not TRANG_THAI.get("xong"):
        try:
            with open(HB, "w", encoding="utf-8") as f:
                f.write("%s | %.0fs | %s | %s\n" % (
                    time.strftime("%H:%M:%S"), time.time() - T_BAT_DAU,
                    TRANG_THAI["cauhinh"], TRANG_THAI["buoc"]))
        except OSError:
            pass
        time.sleep(15)


def http(method, url, body=None, timeout=60.0):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def vram():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.used,memory.total",
                            "--format=csv,noheader,nounits"], capture_output=True,
                           text=True, timeout=15, creationflags=CREATE_NO_WINDOW).stdout
        kq = {}
        for dong in o.strip().splitlines():
            i, u, t = [x.strip() for x in dong.split(",")]
            kq[int(i)] = {"dung": int(u), "tong": int(t)}
        return kq
    except Exception:  # noqa: BLE001
        return {}


def lay_mau_vram(dung_lai):
    while not dung_lai.is_set():
        for i, v in vram().items():
            VRAM_DINH[i] = max(VRAM_DINH.get(i, 0), v["dung"])
        dung_lai.wait(1.0)


def production_dang_chay():
    try:
        _, t = http("GET", SWAP + "/running", timeout=5)
        return bool(json.loads(t).get("running"))
    except Exception:  # noqa: BLE001
        return False   # llama-swap khong tra loi => khong co ai nap qua no


def kiem_nhuong():
    if production_dang_chay():
        TRANG_THAI["dung"] = True
        raise RuntimeError("NHUONG: llama-swap dang nap model production")
    if time.time() > DEADLINE:
        TRANG_THAI["dung"] = True
        raise RuntimeError("HET HAN 50 phut")


# ---------------------------------------------------------------- van ban thu
_TU = ("he thong hang doi cong viec may chu mo hinh ngon ngu nguoi dung yeu cau "
       "bo nho dem ngu canh do tre thong luong suy luan the he ban ghi ket qua "
       "kiem tra tai khoan thanh toan tin dung loi thu lai huy bo giam sat "
       "request queue worker scheduler latency throughput cache token prompt "
       "decode prefill slot memory budget fairness priority cancel stream").split()


def van_ban(so_tu, hat):
    r = random.Random(hat)
    cau = []
    while sum(len(c.split()) for c in cau) < so_tu:
        n = r.randint(8, 20)
        c = " ".join(r.choice(_TU) for _ in range(n))
        cau.append("%s %d, %s." % (c.capitalize(), r.randint(1, 99999), r.choice(_TU)))
    return " ".join(cau)


def dem_token(noi_dung):
    _, t = http("POST", BASE + "/tokenize", {"content": noi_dung}, timeout=120)
    return len(json.loads(t).get("tokens", []))


def dung_whale(muc_tieu):
    """Van ban ~muc_tieu token (do bang /tokenize cua chinh server)."""
    so_tu = int(muc_tieu / 1.6)
    t = van_ban(so_tu, 7)
    n = dem_token(t)
    if n > 0:
        t = van_ban(int(so_tu * muc_tieu / n), 7)
        n = dem_token(t)
    return t, n


PROMPT_NGAN = ("Ban la ky su he thong. Hay giai thich chi tiet, co vi du cu the, cach mot "
               "may chu suy luan mo hinh ngon ngu lon phuc vu nhieu nguoi dung dong thoi: "
               "hang doi, bo nho dem ngu canh, lap lich prefill va decode, va cach do do tre. "
               "Viet dai, co cau truc, nhieu muc. ")


def nonce():
    return "[%s-%d] " % ("".join(random.choice("abcdefghjkmnpqrstuvwxyz") for _ in range(10)),
                         random.randint(0, 10 ** 9))


def chat(noi_dung, max_tokens, timeout=600.0):
    body = {"messages": [{"role": "user", "content": noi_dung}], "max_tokens": max_tokens,
            "temperature": 0.7, "top_p": 0.95, "seed": 42, "ignore_eos": True, "stream": False}
    t0 = time.time()
    ma, t = http("POST", BASE + "/v1/chat/completions", body, timeout=timeout)
    t1 = time.time()
    d = json.loads(t)
    return {"ma": ma, "bat_dau": round(t0 - T_BAT_DAU, 3), "ket_thuc": round(t1 - T_BAT_DAU, 3),
            "wall": round(t1 - t0, 3), "timings": d.get("timings"), "usage": d.get("usage")}


def chat_stream(noi_dung, max_tokens, timeout=600.0):
    body = {"messages": [{"role": "user", "content": noi_dung}], "max_tokens": max_tokens,
            "temperature": 0.7, "top_p": 0.95, "seed": 43, "ignore_eos": True, "stream": True,
            "stream_options": {"include_usage": True}}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    moc = []
    timings = None
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
            if d.get("timings"):
                timings = d["timings"]
            for ch in d.get("choices") or []:
                de = ch.get("delta") or {}
                if de.get("content") or de.get("reasoning_content"):
                    moc.append(round(time.time() - T_BAT_DAU, 3))
    return {"bat_dau": round(t0 - T_BAT_DAU, 3), "ket_thuc": round(time.time() - T_BAT_DAU, 3),
            "moc_token": moc, "timings": timings}


def metrics():
    try:
        _, t = http("GET", BASE + "/metrics", timeout=10)
    except Exception as e:  # noqa: BLE001
        return {"loi": str(e)}
    kq = {}
    for dong in t.splitlines():
        if dong.startswith("llamacpp:"):
            k, _, v = dong.partition(" ")
            try:
                kq[k[9:]] = float(v)
            except ValueError:
                pass
    return kq


# ---------------------------------------------------------------- bai do
def bai_c1(ten):
    kiem_nhuong()
    TRANG_THAI["buoc"] = "c1"
    r = chat(nonce() + PROMPT_NGAN, 512)
    ghi({"loai": "c1", "cauhinh": ten, "kq": r, "metrics": metrics()})


def bai_c4(ten):
    kiem_nhuong()
    TRANG_THAI["buoc"] = "c4"
    kq = [None] * 4

    def mot(i):
        try:
            kq[i] = chat(nonce() + PROMPT_NGAN, 512)
        except Exception as e:  # noqa: BLE001
            kq[i] = {"loi": repr(e)}

    ts = [threading.Thread(target=mot, args=(i,)) for i in range(4)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    ok = [x for x in kq if x and "timings" in x and x["timings"]]
    tong_tok = sum(x["timings"].get("predicted_n", 0) for x in ok)
    wall = (max(x["ket_thuc"] for x in ok) - min(x["bat_dau"] for x in ok)) if ok else None
    ghi({"loai": "c4", "cauhinh": ten, "kq": kq, "tong_token_ra": tong_tok, "wall": wall,
         "tok_s_tong": round(tong_tok / wall, 2) if wall else None, "metrics": metrics()})


def bai_wm(ten, whale_txt, whale_n):
    """Whale ~60K token prefill; minnow stream bat dau sau 6 s."""
    kiem_nhuong()
    TRANG_THAI["buoc"] = "wm"
    kq = {}

    def whale():
        try:
            kq["whale"] = chat(nonce() + whale_txt + "\n\nTom tat doan tren trong mot cau.", 16)
        except Exception as e:  # noqa: BLE001
            kq["whale"] = {"loi": repr(e)}

    def minnow():
        try:
            kq["minnow"] = chat_stream(nonce() + PROMPT_NGAN, 200)
        except Exception as e:  # noqa: BLE001
            kq["minnow"] = {"loi": repr(e)}

    tw = threading.Thread(target=whale)
    tw.start()
    time.sleep(6)
    tm = threading.Thread(target=minnow)
    tm.start()
    tw.join()
    tm.join()
    tom = {}
    w, m = kq.get("whale", {}), kq.get("minnow", {})
    if "ket_thuc" in w and m.get("moc_token"):
        moc = m["moc_token"]
        tom["minnow_ttft"] = round(moc[0] - m["bat_dau"], 3)
        trong = [x for x in moc if x <= w["ket_thuc"]]
        sau = [x for x in moc if x > w["ket_thuc"]]
        tom["minnow_token_trong_luc_whale"] = len(trong)
        if len(trong) > 1:
            tom["minnow_tok_s_trong_luc_whale"] = round((len(trong) - 1) / (trong[-1] - trong[0]), 3)
        if len(sau) > 1:
            tom["minnow_tok_s_sau_whale"] = round((len(sau) - 1) / (sau[-1] - sau[0]), 3)
        tom["whale_wall"] = w.get("wall")
        m = dict(m)
        m["so_token"] = len(moc)
        m.pop("moc_token", None)
        kq["minnow"] = m
    ghi({"loai": "wm", "cauhinh": ten, "whale_token": whale_n, "kq": kq, "tom": tom,
         "metrics": metrics()})


# ---------------------------------------------------------------- vong doi server
def trich_log(duong):
    try:
        with open(duong, encoding="utf-8", errors="replace") as f:
            L = f.read().splitlines()
    except OSError:
        return {}
    mau = re.compile(r"model buffer size|KV buffer size|compute buffer size|"
                     r"llama_memory_recurrent|n_ctx_seq|n_seq_max|kv_unified|"
                     r"using device|failed|error|out of memory|n_slots|"
                     r"offloaded|n_ctx_slot|draft", re.I)
    return {"khop": [x[:220] for x in L if mau.search(x)][:80], "duoi": [x[:220] for x in L[-25:]]}


def chay_cauhinh(ten, them, bai, whale_cache):
    TRANG_THAI["cauhinh"] = ten
    TRANG_THAI["buoc"] = "nap"
    kiem_nhuong()
    VRAM_DINH.clear()
    log = os.path.join(ROOT, "server_%s.log" % ten)
    f = open(log, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen([BIN] + CHUNG + them, stdout=f, stderr=subprocess.STDOUT, env=ENV_SERVER,
                            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP)
    dung_mau = threading.Event()
    tm = threading.Thread(target=lay_mau_vram, args=(dung_mau,), daemon=True)
    tm.start()
    t0 = time.time()
    nap_ok = False
    try:
        while time.time() - t0 < 300:
            if proc.poll() is not None:
                break
            try:
                ma, _ = http("GET", BASE + "/health", timeout=3)
                if ma == 200:
                    nap_ok = True
                    break
            except Exception:  # noqa: BLE001
                pass
            if production_dang_chay():
                TRANG_THAI["dung"] = True
                raise RuntimeError("NHUONG luc nap")
            time.sleep(1)
        nap_s = round(time.time() - t0, 1)
        time.sleep(2)
        rec = {"loai": "nap", "cauhinh": ten, "co": them, "ok": nap_ok, "nap_s": nap_s,
               "vram_sau_nap": vram(), "exit": proc.poll()}
        if nap_ok:
            try:
                _, s = http("GET", BASE + "/slots", timeout=10)
                rec["slots"] = [{"id": x.get("id"), "n_ctx": x.get("n_ctx")} for x in json.loads(s)]
            except Exception as e:  # noqa: BLE001
                rec["slots_loi"] = repr(e)
            try:
                _, p = http("GET", BASE + "/props", timeout=10)
                pj = json.loads(p)
                rec["props"] = {k: pj.get(k) for k in ("total_slots", "build_info", "n_ctx")}
            except Exception:  # noqa: BLE001
                pass
        f.flush()
        rec["log"] = trich_log(log)
        ghi(rec)
        if not nap_ok:
            return False
        for b in bai:
            try:
                if b == "c1":
                    bai_c1(ten)
                elif b == "c4":
                    bai_c4(ten)
                elif b == "wm":
                    if "txt" not in whale_cache:
                        TRANG_THAI["buoc"] = "dung whale"
                        whale_cache["txt"], whale_cache["n"] = dung_whale(60000)
                    bai_wm(ten, whale_cache["txt"], whale_cache["n"])
            except Exception as e:  # noqa: BLE001
                ghi({"loai": "loi_bai", "cauhinh": ten, "bai": b, "loi": repr(e),
                     "tb": traceback.format_exc()[-1500:]})
                if TRANG_THAI["dung"]:
                    raise
        return True
    finally:
        dung_mau.set()
        try:
            proc.terminate()
            proc.wait(30)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
        f.close()
        ghi({"loai": "tat", "cauhinh": ten, "vram_dinh": dict(VRAM_DINH), "exit": proc.poll(),
             "log_duoi": trich_log(log).get("duoi", [])[-8:]})
        for _ in range(30):             # cho VRAM ve
            v = vram()
            if v and v.get(GPU_3090, {}).get("dung", 99999) < 3000:
                break
            time.sleep(1)


def main():
    os.makedirs(ROOT, exist_ok=True)
    threading.Thread(target=nhip_tim, daemon=True).start()
    v = vram()
    ghi({"loai": "bat_dau", "vram": v, "production_dang_chay": production_dang_chay(), "pid": os.getpid()})
    if production_dang_chay() or not v or v.get(GPU_3090, {}).get("dung", 99999) >= 3000:
        ghi({"loai": "bo", "ly_do": "tien kiem khong dat (production dang nap hoac GPU dang bi giu)"})
        TRANG_THAI["xong"] = True
        return
    whale_cache = {}
    co = set()
    for ten, them, bai, dieu_kien in CAUHINH:
        if TRANG_THAI["dung"]:
            break
        if dieu_kien and dieu_kien not in co:
            ghi({"loai": "bo_qua", "cauhinh": ten, "vi": "dieu kien %s khong xay ra" % dieu_kien})
            continue
        try:
            ok = chay_cauhinh(ten, them, bai, whale_cache)
            if not ok:
                co.add(ten + "_hong")
        except Exception as e:  # noqa: BLE001
            ghi({"loai": "loi_cauhinh", "cauhinh": ten, "loi": repr(e),
                 "tb": traceback.format_exc()[-1500:]})
            co.add(ten + "_hong")
    ghi({"loai": "xong", "dung_giua_chung": TRANG_THAI["dung"], "vram": vram()})
    TRANG_THAI["xong"] = True
    TRANG_THAI["buoc"] = "XONG"
    try:
        with open(HB, "w", encoding="utf-8") as f:
            f.write("%s | XONG | dung=%s\n" % (time.strftime("%H:%M:%S"), TRANG_THAI["dung"]))
    except OSError:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        ghi({"loai": "loi_main", "tb": traceback.format_exc()[-2000:]})
        TRANG_THAI["xong"] = True
