"""
chay_baseline.py - chay bo prompt qua ComfyUI THAT va ghi lai moi so do. (H37 / G3-G4)

    E:\\AI\\ltt_render\\venv\\Scripts\\python.exe chay_baseline.py --ca baseline

** DUNG CHINH MA CLIENT CUA CONG RENDER (`render_gateway.comfy`, `.workflows`).
   Nho vay G3 vua do duoc model, vua la lan dau tien ma do noi chuyen voi ComfyUI
   THAT chu khong phai voi ban gia lap cua test.

** MOI SO DO KEM DIEU KIEN DO (luat cua bench/README.md): VRAM dinh, RAM, nhiet,
   throttle_reasons deu lay bang cach LAY MAU trong luc chay, khong phai doc mot
   lan luc xong. Doc mot lan luc xong se bo lo dung cai dinh can biet.

** VRAM doc bang nvidia-smi, KHONG bang /system_stats hay torch (D-013):
   tren Windows/WDDM hai nguon kia mu voi tien trinh khac.
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from render_gateway import ngan_sach as NS                          # noqa: E402
from render_gateway.catalog import nap_catalog                      # noqa: E402
from render_gateway.comfy import ComfyClient, prompt_id_for         # noqa: E402
from render_gateway.http import HttpxTransport                      # noqa: E402
from render_gateway.workflows import kiem_node, nap, thay           # noqa: E402


class LayMau(threading.Thread):
    """Lay mau nvidia-smi trong luc job chay. Dung mot luong rieng vi vong cho
    cua job la vong chan (blocking)."""

    def __init__(self, chu_ky: float = 1.0):
        super().__init__(daemon=True)
        self.chu_ky = chu_ky
        self.dung = False
        self.mau: list[dict] = []

    def run(self) -> None:
        truy_van = ("memory.used,temperature.gpu,power.draw,utilization.gpu,"
                    "clocks_throttle_reasons.active")
        while not self.dung:
            try:
                r = subprocess.run(
                    ["nvidia-smi", f"--query-gpu={truy_van}",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=8,
                    encoding="utf-8", errors="replace")
                dong = (r.stdout or "").strip().splitlines()
                if dong:
                    p = [x.strip() for x in dong[0].split(",")]
                    self.mau.append({
                        "t": time.time(), "vram_mb": int(float(p[0])),
                        "nhiet_c": int(float(p[1])), "power_w": float(p[2]),
                        "util_pct": int(float(p[3])),
                        "throttle": p[4] if len(p) > 4 else "",
                    })
            except Exception:                                     # noqa: BLE001
                pass
            time.sleep(self.chu_ky)

    def tom_tat(self) -> dict:
        if not self.mau:
            return {"so_mau": 0}
        vram = [m["vram_mb"] for m in self.mau]
        nhiet = [m["nhiet_c"] for m in self.mau]
        power = [m["power_w"] for m in self.mau]
        thr = sorted({m["throttle"] for m in self.mau
                      if m["throttle"] and m["throttle"] not in ("0x0000000000000000",)})
        return {
            "so_mau": len(self.mau),
            "vram_dinh_mb": max(vram), "vram_trung_vi_mb": int(statistics.median(vram)),
            "nhiet_dinh_c": max(nhiet), "nhiet_trung_vi_c": int(statistics.median(nhiet)),
            "power_dinh_w": max(power),
            "throttle_quan_sat": thr or [],
        }


def _ram_trong_gb() -> float:
    import ctypes

    class _M(ctypes.Structure):
        _fields_ = [("l", ctypes.c_ulong), ("mem", ctypes.c_ulong),
                    ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                    ("tpg", ctypes.c_ulonglong), ("apg", ctypes.c_ulonglong),
                    ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                    ("ae", ctypes.c_ulonglong)]

    m = _M()
    m.l = ctypes.sizeof(_M)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ap / 2 ** 30


def chay_mot(client: ComfyClient, wf: dict, ma_job: str, *, timeout_s: float,
             thu_muc_ra: Path) -> dict:
    """Chay mot prompt, tra ve so do. Khong nem - moi loi thanh mot truong."""
    pid = prompt_id_for(ma_job)
    lm = LayMau()
    lm.start()
    t0 = time.time()
    ket = {"prompt_id": pid, "ok": False}
    try:
        # !! Hoi TRUOC khi xep hang: prompt_id sinh tat dinh tu ma_job, nen mot lan
        #    chay truoc do co the da de lai ban ghi. Xep hang lai la dot GPU cho
        #    khong. Xem DECISIONS.md D-018.
        if client.da_xong(pid):
            ket["ok"] = True
            ket["tu_lan_truoc"] = True
        else:
            client.queue_prompt(wf, prompt_id=pid)
        het = t0 + timeout_s
        while not ket["ok"] and time.time() < het:
            # HAI dieu kien: co ban ghi `success` VA khong con trong hang doi.
            if client.da_xong(pid):
                ket["ok"] = True
                break
            muc = client.history(pid)
            if muc:
                st = muc.get("status") or {}
                if st.get("status_str") and str(st["status_str"]) != "success":
                    ket["loi"] = " | ".join(str(x) for x in (st.get("messages") or []))[:400]
                    break
            time.sleep(1.0)
        if not ket["ok"] and not ket.get("loi"):
            ket["loi"] = f"qua {timeout_s:.0f} giay"
            client.interrupt(pid)
    except Exception as e:                                        # noqa: BLE001
        ket["loi"] = f"{type(e).__name__}: {e}"[:400]
    ket["giay"] = round(time.time() - t0, 1)
    lm.dung = True
    lm.join(timeout=5)
    ket["do_duoc"] = lm.tom_tat()

    if ket["ok"]:
        anh = client.images_of(pid)
        ket["so_anh"] = len(anh)
        thu_muc_ra.mkdir(parents=True, exist_ok=True)
        ten_da_luu = []
        for i, a in enumerate(anh):
            data = client.download(a)
            duong = thu_muc_ra / f"{ma_job}_{i}.png"
            duong.write_bytes(data)
            ten_da_luu.append(duong.name)
            ket.setdefault("byte_anh", []).append(len(data))
        ket["anh"] = ten_da_luu
    return ket


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", type=Path,
                    default=Path(r"E:\AI\ltt_render\bench\prompts.json"))
    ap.add_argument("--ca", default="baseline", help="nhan cua lo do nay")
    ap.add_argument("--model", default="hidream-o1")
    ap.add_argument("--mode", default="t2i")
    ap.add_argument("--ckpt", default=None, help="ghi de ten checkpoint")
    ap.add_argument("--lam-lai", dest="lam_lai", action="store_true",
                    help="chay lai TU DAU, bo qua ket qua da co cua lo cung ten")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--cfg", type=float, default=None)
    ap.add_argument("--comfy", default="http://127.0.0.1:8188")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--ra", type=Path, default=Path(r"E:\AI\ltt_render\bench"))
    ap.add_argument("--so-prompt", type=int, default=None, help="chi chay N prompt dau")
    ap.add_argument("--ids", default=None,
                    help="chi chay dung nhung id nay, vd: p01,p13,p16")
    # Anh tham chieu cho che do edit/subject. Uu tien truong `ref1`/`ref2` cua
    # tung prompt; hai co nay chi la mac dinh khi prompt khong khai.
    ap.add_argument("--ref1", default=None, help="ten tep trong thu muc input cua ComfyUI")
    ap.add_argument("--ref2", default=None)
    # Do VRAM cho che do tham chieu phai TANG DAN (D-024). Co nay ghi de `ref_mp`
    # cua catalog cho tung bac cua thang do.
    ap.add_argument("--ref-mp", type=float, default=None,
                    help="megapixel moi anh tham chieu; ghi de mac dinh cua catalog")
    # !! CHOT NGAN SACH (D-024). May B da SAP mot lan vi mot cau hinh chua ai do
    #    duoc xep vao chuoi tu dong. Mac dinh la tran DA DO; nang no la mot hanh
    #    dong CO CHU Y, phai go ra tren dong lenh, va chi khi CO NGUOI CANH.
    ap.add_argument("--tran-token", type=int, default=NS.TOKEN_DA_DO_TOI_DA,
                    help="tran token. Nang len = tu nhan 'toi dang do, toi dang ngoi day'")
    a = ap.parse_args()

    client = ComfyClient(HttpxTransport(a.comfy))
    if not client.alive():
        print(f"ComfyUI khong tra loi o {a.comfy}")
        return 2

    spec = nap_catalog()[a.model]
    mode = spec.modes[a.mode]
    mau = nap(mode.template)
    kiem_node(mau, client.object_info_keys())          # bat thieu node TRUOC khi chay

    prompts = json.loads(a.prompts.read_text(encoding="utf-8"))["prompts"]
    if a.ids:
        chon = [x.strip() for x in a.ids.split(",") if x.strip()]
        theo_id = {p["id"]: p for p in prompts}
        thieu = [c for c in chon if c not in theo_id]
        if thieu:
            print(f"KHONG co prompt id: {', '.join(thieu)}")
            return 2
        prompts = [theo_id[c] for c in chon]      # giu dung thu tu da yeu cau
    elif a.so_prompt:
        prompts = prompts[:a.so_prompt]

    chung = dict(spec.defaults)
    for ten, gt in (("ckpt", a.ckpt), ("width", a.width), ("height", a.height),
                    ("steps", a.steps), ("cfg", a.cfg), ("ref_mp", a.ref_mp)):
        if gt is not None:
            chung[ten] = gt

    thu_muc_ra = a.ra / a.ca
    ket_qua = {
        "ca": a.ca,
        "ngay": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cau_hinh": {k: chung[k] for k in sorted(chung) if k != "prompt"},
        "model": a.model, "mode": a.mode,
        "ram_trong_truoc_gb": round(_ram_trong_gb(), 1),
        "runs": [],
    }
    print(f"== {a.ca}: {len(prompts)} prompt | {chung.get('width')}x{chung.get('height')}"
          f" | {chung.get('steps')} buoc | CFG {chung.get('cfg')} | {chung.get('ckpt')}",
          flush=True)

    # !! GHI SAU MOI ANH, KHONG DOI CUOI LO (D-025). May B tu khoi dong lai de cai
    #    cap nhat Windows (Active Hours het luc 01:00). Lo s90 dang chay bi cuon theo
    #    o anh 21/30 va MAT TOAN BO so do cua 20 anh da chay - vi tep tong ket chi
    #    duoc viet o cuoi. Anh thi con tren dia; so do thoi gian/VRAM/nhiet thi mat.
    a.ra.mkdir(parents=True, exist_ok=True)
    tep = a.ra / f"{a.ca}.json"

    def ghi_ket_qua():
        tep.write_text(json.dumps(ket_qua, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    # ⭐ TIEP TUC LO DANG DO. Ghi-sau-moi-anh (o tren) da cuu duoc SO DO khi may
    #    khoi dong lai giua chung — nhung chay lai van lam lai TU ANH 1, tuc la
    #    tra tien GPU hai lan cho phan da xong. Lo 30 anh chet o anh 21 thi 20 anh
    #    kia phai chay lai het.
    #
    #    Nay: doc lai tep ket qua, giu nhung prompt DA XONG (`ok`), va bo qua
    #    chung. Mot lan khoi dong lai gio chi mat DUNG mot anh dang chay.
    #
    #    ⛔ Chi giu `ok=True`. Anh hong phai chay lai — giu no lai la dong bang
    #       mot that bai thanh mot ket qua.
    xong_roi: set = set()
    if tep.exists() and not a.lam_lai:
        try:
            cu = json.loads(tep.read_text(encoding="utf-8"))
            # `null` va `[]` deu la JSON HOP LE nhung khong phai dict — `.get()`
            # se no va lam sap ca phien do ngay o buoc dau. Bat boi test_266.
            if not isinstance(cu, dict):
                raise ValueError("checkpoint khong phai mot doi tuong JSON")
            if cu.get("cau_hinh") == ket_qua["cau_hinh"] and cu.get("mode") == a.mode:
                giu = [r for r in (cu.get("runs") or []) if r.get("ok")]
                if giu:
                    ket_qua["runs"] = giu
                    ket_qua["tiep_tuc_tu"] = cu.get("ngay")
                    xong_roi = {r.get("id") for r in giu}
                    print(f"   tiep tuc: bo qua {len(xong_roi)} anh da xong "
                          f"(dung --lam-lai de chay lai tu dau)", flush=True)
            else:
                # ⛔ Cau hinh khac thi so do CU KHONG so duoc voi so do MOI. Ghi de
                #    la tron hai lo lam mot, va khong ai biet dong nao thuoc lo nao.
                print("   cau hinh khac lan truoc -> chay lai tu dau", flush=True)
        except (OSError, ValueError) as e:
            print(f"   khong doc duoc checkpoint cu ({e}) -> chay lai tu dau",
                  flush=True)

    ghi_ket_qua()          # ghi ngay khung rong, de biet lo nay DA BAT DAU

    for i, pr in enumerate(prompts, 1):
        if pr["id"] in xong_roi:
            continue
        gia_tri = dict(chung)
        gia_tri["prompt"] = pr["text"]
        gia_tri["negative"] = ""
        gia_tri["seed"] = pr.get("seed", 0)
        for khe, mac_dinh in (("ref1", a.ref1), ("ref2", a.ref2)):
            gt = pr.get(khe) or mac_dinh
            if gt:
                gia_tri[khe] = gt
        # ltt_h37/ chu KHONG phai ltt/ - thu muc output/ltt/ da co san ket qua
        # cua du an video (TEST1..TEST5*.mp4). Xem DECISIONS.md D-018.
        gia_tri["prefix"] = f"ltt_h37/{a.ca}/{pr['id']}"
        try:
            wf = thay(mau, gia_tri)
        except Exception as e:                                    # noqa: BLE001
            # Che do edit/subject can `ref1`/`ref2`. Thieu thi hong o DAY - truoc
            # khi cham vao GPU - chu khong hong giua chung sau khi da nap model.
            print(f"[{i}/{len(prompts)}] {pr['id']} BO QUA: {e}", flush=True)
            ket_qua["runs"].append({"id": pr["id"], "ok": False, "giay": 0.0,
                                    "loi": str(e)[:400], "do_duoc": {}})
            ghi_ket_qua()
            continue

        try:
            u = NS.kiem_workflow(wf, tran=a.tran_token)
        except NS.NgoaiVungDaDo as e:
            print(f"[{i}/{len(prompts)}] {pr['id']} BI CHAN: {e}", flush=True)
            ket_qua["runs"].append({"id": pr["id"], "ok": False, "giay": 0.0,
                                    "loi": str(e)[:400], "do_duoc": {}})
            ghi_ket_qua()
            continue

        ma = f"{a.ca}_{pr['id']}"
        print(f"[{i}/{len(prompts)}] {pr['id']} ({pr.get('cat','')}) ...", end="", flush=True)
        r = chay_mot(client, wf, ma, timeout_s=a.timeout, thu_muc_ra=thu_muc_ra)
        r.update({"id": pr["id"], "cat": pr.get("cat", ""), "seed": gia_tri["seed"],
                  "prompt": pr["text"], "token": u.as_dict()})
        ket_qua["runs"].append(r)
        ghi_ket_qua()
        d = r.get("do_duoc", {})
        print(f" {'OK ' if r['ok'] else 'HONG'} {r['giay']}s"
              f" | VRAM dinh {d.get('vram_dinh_mb','?')} MB"
              f" | {d.get('nhiet_dinh_c','?')} C"
              f"{' | ' + r.get('loi','') if not r['ok'] else ''}", flush=True)

    xong = [r for r in ket_qua["runs"] if r["ok"]]
    if xong:
        ket_qua["tom_tat"] = {
            "so_chay": len(ket_qua["runs"]),
            "so_thanh_cong": len(xong),
            "giay_trung_vi": round(statistics.median(r["giay"] for r in xong), 1),
            "giay_min": min(r["giay"] for r in xong),
            "giay_max": max(r["giay"] for r in xong),
            "vram_dinh_mb": max(r["do_duoc"].get("vram_dinh_mb", 0) for r in xong),
            "nhiet_dinh_c": max(r["do_duoc"].get("nhiet_dinh_c", 0) for r in xong),
            "throttle": sorted({t for r in xong
                                for t in r["do_duoc"].get("throttle_quan_sat", [])}),
        }
    ket_qua["ram_trong_sau_gb"] = round(_ram_trong_gb(), 1)

    ghi_ket_qua()
    print(f"\nDa ghi {tep}")
    if "tom_tat" in ket_qua:
        print(json.dumps(ket_qua["tom_tat"], ensure_ascii=False, indent=2))
    return 0 if xong else 1


if __name__ == "__main__":
    raise SystemExit(main())
