"""nghiem_thu.py - nghiem thu cong VLM tu dau den cuoi. CHAY TREN MAY B.

    H:\\LTT_LLM\\venv\\Scripts\\python.exe ...\\deploy\\nghiem_thu.py --token XXX

Vi sao la .py chu khong phai .ps1: quy tac 3 cua CLAUDE.md. Kiem tra nay gui JSON
long nhau qua HTTP; PowerShell nuot dau ngoac kep khi truyen cho .exe va qua ssh
thi hong chac chan.

Bay muc kiem, moi muc neo mot thu ma mat no la mat tien hoac mat dich vu.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

CONG = "http://127.0.0.1:8299"
COMFY = "http://127.0.0.1:8188"

# !! Console cua may B la CP1252. Model tra loi tieng Viet, va `print` se nem
#    UnicodeEncodeError giua bai nghiem thu - mot bai kiem TU LAM HONG CHINH NO.
#    Da dinh mot lan. `errors="replace"` de chu meo con hon la vo.
# Console cua may B la CP1252, model tra loi tieng Viet, va `print` se nem
# UnicodeEncodeError giua bai nghiem thu - mot bai kiem TU LAM HONG CHINH NO.
# Kiem thuoc tinh thay vi boc try/except (banh cong `check_silent_except`).
for _luong in (sys.stdout, sys.stderr):
    if hasattr(_luong, "reconfigure"):
        _luong.reconfigure(encoding="utf-8", errors="replace")

_dat = 0
_hong = 0


def bao(ten: str, ok: bool, chi_tiet: str = "") -> None:
    global _dat, _hong
    if ok:
        _dat += 1
        print(f"  [DAT ] {ten}" + (f" - {chi_tiet}" if chi_tiet else ""))
    else:
        _hong += 1
        print(f"  [HONG] {ten}" + (f" - {chi_tiet}" if chi_tiet else ""))


def goi(duong: str, than=None, token: str = "", timeout: float = 600.0):
    """Tra (ma, than_json_hoac_None, giay)."""
    url = CONG + duong
    du_lieu = json.dumps(than).encode("utf-8") if than is not None else None
    req = urllib.request.Request(url, data=du_lieu, method="POST" if than is not None else "GET")
    if du_lieu is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8")), time.time() - t0
    except urllib.error.HTTPError as e:
        thu = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(thu), time.time() - t0
        except ValueError:
            return e.code, {"raw": thu}, time.time() - t0
    except Exception as e:
        return 0, {"loi": f"{type(e).__name__}: {e}"}, time.time() - t0


# !! DUONG VAO GOI `llm_gateway` KHI CHAY NHU MOT SCRIPT.
#
#    Tep nay chay bang duong dan tuyet doi tren may B
#    (`...\gateway\llm_gateway\deploy\nghiem_thu.py`), nen `import llm_gateway`
#    khong tu chay - goc goi khong nam tren sys.path. Hai cap len la goc goi.
#
#    ! Kiem tra TO TIENG neu bo cuc doi. Mot `sys.path` tinh sai se lam
#      `import` that bai giua bai nghiem thu, va nguoi doc se di tim nham cho.
_GOC_GOI = pathlib.Path(__file__).resolve().parents[1]          # .../llm_gateway
if not (_GOC_GOI / "gpu_uuid.py").is_file():
    raise SystemExit(f"khong thay {_GOC_GOI}/gpu_uuid.py - bo cuc goi da doi, "
                     f"sua duong dan trong nghiem_thu.py")
if str(_GOC_GOI.parent) not in sys.path:
    sys.path.insert(0, str(_GOC_GOI.parent))
from llm_gateway import gpu_uuid as GPU                        # noqa: E402

#: Vai GPU ma bai nghiem thu nay noi ve. `--vai` doi duoc tren dong lenh.
VAI = GPU.VAI_38


def vram_mb(vai: str = ""):
    """VRAM dang dung TREN DUNG MOT CARD, MiB. `-1` = khong hoi duoc.

    !! BAN CU LAY `splitlines()[0]`. Tu 09/2026 may B co hai card, nen dong dau
       la card nao thi do driver quyet - va con so nay di thang vao KET LUAN
       nghiem thu ("ComfyUI CO giu VRAM sau khi ve"). Mot phep do lech card o day
       khong lam bai kiem do, no lam bai kiem NOI SAI.
    """
    try:
        the = GPU.doc_the(GPU.uuid_cua(vai or VAI))
    except Exception:
        return -1
    return -1 if the is None else the["vram_dung_mib"]


def comfy_ve_mot_anh() -> bool:
    """Chay mot anh 1024x1024 de LAM BAN card - cau hinh nam trong vung DA DO."""
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "hidream_o1_image_bf16.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": "a red apple"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": ""}},
        "4": {"class_type": "EmptyHiDreamO1LatentImage",
              "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                         "latent_image": ["4", 0], "seed": 99, "steps": 8, "cfg": 5.0,
                         "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage",
              "inputs": {"images": ["6", 0], "filename_prefix": "nghiem_thu/apple"}},
    }
    req = urllib.request.Request(COMFY + "/prompt",
                                 data=json.dumps({"prompt": wf}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            pid = json.loads(r.read())["prompt_id"]
    except Exception as e:
        print(f"    (khong gui duoc job ComfyUI: {e})")
        return False
    for _ in range(120):
        time.sleep(3)
        try:
            with urllib.request.urlopen(f"{COMFY}/history/{pid}", timeout=15) as r:
                if pid in json.loads(r.read()):
                    return True
        except Exception:
            pass
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default="")
    ap.add_argument("--model", default="qwen38-api")
    ap.add_argument("--bo-qua-don-dep", action="store_true")
    # Card nao dang duoc nghiem thu. `qwen38-*` chay tren 3090 (`ltt38`),
    # `qwen35-*` tren 5060 Ti (`ltt35`) - suy tu `--model` chu khong go tay.
    ap.add_argument("--vai", default="")
    a = ap.parse_args()
    tk = a.token
    # ! Suy vai tu `--model` (khong go tay o hai cho): `--vai` chi de ghi de khi
    #   nghiem thu mot ho so chua co trong bang anh xa.
    global VAI
    VAI = a.vai or GPU.vai_cua_model(a.model) or GPU.VAI_38
    print(f"  card nghiem thu: vai={VAI} uuid={GPU.uuid_cua(VAI)}")

    print("")
    print("=" * 62)
    print("  NGHIEM THU CONG VLM")
    print("=" * 62)

    # --- 1. Song va khai bao dung ---------------------------------------------
    print("\n1. Trang thai")
    ma, h, _ = goi("/health", token=tk)
    bao("/health tra 200", ma == 200, f"ma={ma}")
    if ma != 200:
        print("   Cong khong song. Dung.")
        return 1
    bao("thuong nguon song", bool(h.get("thuong_nguon", {}).get("song")),
        str(h.get("thuong_nguon")))
    bao("khong co ten model la", not h.get("models_la"), str(h.get("models_la")))

    # !! CHOT QUAN TRONG NHAT SAU SU CO 23/08, va la chot DUY NHAT nhin ra duoc no.
    #
    #    May B tat khong sach luc 13:16, CUDA hong ca may, llama.cpp LANG LE roi ve
    #    CPU. Suot hon mot gio: /live tra ok, /health tra 200, llama-swap bao
    #    "ready", moi luot goi tra 200 - va llama-server om 23 GB RAM CHU trong khi
    #    GPU o 1.153 MiB. Trieu chung la CHAM, khong phai LOI.
    #
    #    Chot nay chay TRUOC moi phep do toc do ben duoi: khong co no thi bo nghiem
    #    thu se bao "toc do < 50 tok/s" va nguoi doc di tim nham cho.
    gpu = h.get("gpu") or {}
    if gpu.get("dang_lo"):
        # Hiem: mot model tu lan truoc con nap va da o CPU. Bat ngay, dung cho toi
        # buoc 5 - moi phep do toc do ben duoi se vo nghia.
        bao("model nam TREN GPU (khong phai CPU)", False, gpu.get("ly_do", ""))
    else:
        print("   (chua nap model -> chot GPU se chay o buoc 5)")
    print(f"    models_mo = {h.get('models_mo')}")
    print(f"    trong_tai = ban={h.get('trong_tai', {}).get('ban')} "
          f"python_gpu={h.get('trong_tai', {}).get('so_python_gpu')}")

    ma, m, _ = goi("/v1/models", token=tk)
    ten_mo = [x["id"] for x in (m.get("data") or [])]
    bao("/v1/models liet ke model dang mo", a.model in ten_mo, str(ten_mo))
    if a.model not in ten_mo:
        print(f"   '{a.model}' chua mo. Dat LTT_LLM_MODELS roi chay lai.")
        return 1

    # --- 2. Xac thuc -----------------------------------------------------------
    print("\n2. Xac thuc")
    if tk:
        ma, _, _ = goi("/v1/chat/completions",
                       {"model": a.model, "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 8}, token="sai-token")
        bao("token sai -> 401", ma == 401, f"ma={ma}")
    else:
        print("    (khong co token -> bo qua)")

    # --- 3. Fail-closed --------------------------------------------------------
    print("\n3. Fail-closed")
    ma, _, _ = goi("/v1/chat/completions",
                   {"model": "khong-ton-tai", "messages": [], "max_tokens": 8}, token=tk)
    bao("model la -> 404", ma == 404, f"ma={ma}")

    # --- 4. Ngan sach chan TRUOC khi cham GPU ----------------------------------
    print("\n4. Ngan sach")
    ma, d, gy = goi("/v1/chat/completions",
                    {"model": a.model, "max_tokens": 8,
                     "messages": [{"role": "user", "content": "x" * 2_000_000}]}, token=tk)
    bao("dau vao qua dai -> 413", ma == 413, f"ma={ma} sau {gy:.1f}s")
    bao("bi chan NHANH (chua cham GPU)", gy < 10, f"{gy:.1f}s")

    ma, _, _ = goi("/v1/chat/completions",
                   {"model": a.model, "messages": [], "max_tokens": 999_999}, token=tk)
    bao("xin sinh qua nhieu -> 413", ma == 413, f"ma={ma}")

    # --- 5. Sinh that ----------------------------------------------------------
    print("\n5. Sinh that")
    v0 = vram_mb()
    ma, r, gy = goi("/v1/chat/completions",
                    {"model": a.model, "max_tokens": 300,
                     "messages": [{"role": "user",
                                   "content": "Reply in Vietnamese, one short sentence: "
                                              "what is HTTP 429 for?"}]}, token=tk)
    bao("chat -> 200", ma == 200, f"ma={ma} sau {gy:.1f}s")
    if ma == 200:
        noi = (r.get("choices") or [{}])[0].get("message", {}).get("content", "")
        u = r.get("usage") or {}
        t = r.get("timings") or {}
        bao("co noi dung", len(noi) > 10, noi[:70].replace("\n", " "))
        bao("co usage de tinh tien", "prompt_tokens" in u and "completion_tokens" in u,
            f"vao={u.get('prompt_tokens')} ra={u.get('completion_tokens')}")
        bao("co timings.cache_n", "cache_n" in t, f"cache_n={t.get('cache_n')}")
        tg = t.get("predicted_per_second") or 0
        bao("toc do >= 50 tok/s (card sach)", tg >= 50, f"{tg:.1f} tok/s")

        # !! CHOT QUAN TRONG NHAT SAU SU CO 23/08, va no phai dung O DAY chu khong
        #    phai o buoc 1: buoc 1 chay khi CHUA model nao nap, nen no luon bi bo
        #    qua. Toi da dat nham cho mot lan - chot khong bao gio chay thi khong
        #    phai chot.
        #
        #    Vi sao no dung NGAY SAU phep do toc do: neu model o CPU thi dong tren
        #    da bao "toc do < 50 tok/s" va nguoi doc se di tim nham cho - card ban,
        #    don_dep hong, mang cham. Dong nay noi thang nguyen nhan.
        ma_g, hg, _ = goi("/health", token=tk)
        g = (hg or {}).get("gpu") or {}
        bao("model nam TREN GPU (khong phai CPU)", g.get("tren_gpu") is True,
            g.get("ly_do") or f"VRAM {g.get('vram_dung_mb')} MB")
        print(f"    VRAM: {v0} -> {vram_mb()} MiB")

    # --- 6. Tool calling -------------------------------------------------------
    print("\n6. Tool calling")
    ma, r, _ = goi("/v1/chat/completions", {
        "model": a.model, "max_tokens": 300,
        "messages": [{"role": "user", "content": "What is the weather in Hanoi? Use the tool."}],
        "tools": [{"type": "function", "function": {
            "name": "get_weather", "description": "Get current weather for a city",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                           "required": ["city"]}}}]}, token=tk)
    tc = ((r.get("choices") or [{}])[0].get("message", {}) or {}).get("tool_calls") or []
    bao("model goi tool", bool(tc),
        (tc[0]["function"]["name"] + " " + tc[0]["function"]["arguments"]) if tc else "khong co")

    # --- 7. Prefix cache -------------------------------------------------------
    print("\n7. Prefix cache (tinh tien token cache)")
    than = {"model": a.model, "max_tokens": 24,
            "messages": [{"role": "user", "content": "Explain a write-ahead log. " + ("detail " * 400)}]}
    goi("/v1/chat/completions", than, token=tk)
    ma, r2, _ = goi("/v1/chat/completions", than, token=tk)
    cn = (r2.get("timings") or {}).get("cache_n", 0)
    pt = (r2.get("usage") or {}).get("prompt_tokens", 0)
    bao("goi lai y het -> cache_n > 0", cn > 0, f"cache_n={cn}/{pt}")

    # --- 8. Don dep card -------------------------------------------------------
    if not a.bo_qua_don_dep:
        print("\n8. Don dep card (P6 - cai da hong lan dau)")
        print("    Lam ban card bang mot anh ComfyUI...")
        if comfy_ve_mot_anh():
            vb = vram_mb()
            print(f"    VRAM sau khi ComfyUI ve xong: {vb} MiB")
            bao("ComfyUI CO giu VRAM sau khi ve", vb > 2500, f"{vb} MiB")
            ma, r, gy = goi("/v1/chat/completions",
                            {"model": a.model, "max_tokens": 300,
                             "messages": [{"role": "user",
                                           "content": "Write a Python function to reverse a string."}]},
                            token=tk)
            tg = (r.get("timings") or {}).get("predicted_per_second") or 0
            bao("van tra 200 sau khi card ban", ma == 200, f"ma={ma} sau {gy:.1f}s")
            # DAY la muc quan trong nhat cua ca bai nghiem thu.
            bao("toc do KHONG tut (>= 50 tok/s)", tg >= 50,
                f"{tg:.1f} tok/s - neu ~18 thi don_dep KHONG chay")
        else:
            print("    (ComfyUI khong ve duoc -> bo qua muc nay)")
    else:
        print("\n8. Don dep card - BO QUA")

    print("")
    print("=" * 62)
    print(f"  DAT {_dat} | HONG {_hong}")
    print("=" * 62)
    return 0 if _hong == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
