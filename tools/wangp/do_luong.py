"""Ma tran do WanGP tren C-CLOUD — chay khong nguoi, ghi het ra /data/ket_qua.

Goi API theo dung `docs/API.md` cua WanGP: `from shared.api import init`.
Khong tu che tham so: lay `get_default_settings()` cua chinh WanGP roi chi de len
nhung gi bat buoc de so duoc voi phep do cua V3 (1280x720, 81 khung, 20 buoc).

⛔ Khong bao gio dung ca luot vi mot phep do hong. Moi muc boc try/except,
   ghi lai, di tiep. Mot phep do thieu con hon ca luot mat trang.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

GOC = Path("/data")
KHO = GOC / "Wan2GP"
KQ = GOC / "ket_qua"
KQ.mkdir(parents=True, exist_ok=True)

TRAN_PHUT = float(os.environ.get("LTTV_TRAN_PHUT", "150"))
BAT_DAU = time.time()

# Cau hinh san xuat cua V3 — ghim de SO SANH DUOC, khong phai de toi uu.
DO_PHAN_GIAI = "1280x720"
SO_KHUNG = 81
SO_BUOC = 20

sys.path.insert(0, str(KHO))
os.chdir(KHO)


def ghi(ten: str, du_lieu) -> None:
    (KQ / ten).write_text(json.dumps(du_lieu, ensure_ascii=False, indent=1, default=str),
                          encoding="utf-8")


def nhat_ky(*phan) -> None:
    dong = f"[{time.strftime('%H:%M:%S')}] " + " ".join(str(p) for p in phan)
    print(dong, flush=True)
    with open(KQ / "do_luong.log", "a", encoding="utf-8") as fh:
        fh.write(dong + "\n")


def con_gio() -> bool:
    return (time.time() - BAT_DAU) / 60 < TRAN_PHUT


# ─────────── Lay mau VRAM/RAM lien tuc, BAT TRUOC moi thu (bay ②) ───────────
MOC = []          # (nhan, t_bat_dau, t_ket_thuc)


def _lay_mau():
    with open(KQ / "vram.csv", "w", encoding="utf-8") as fh:
        fh.write("t,vram_mb,gpu_pct,ram_kha_dung_kb\n")
        while True:
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=8)
                vram, gpu = (r.stdout.strip().splitlines() or ["0, 0"])[0].split(",")
                ram = ""
                try:
                    for ln in open("/proc/meminfo"):
                        if ln.startswith("MemAvailable"):
                            ram = ln.split()[1]
                            break
                except Exception:
                    pass
                fh.write(f"{time.time():.1f},{vram.strip()},{gpu.strip()},{ram}\n")
                fh.flush()
            except Exception:
                pass
            time.sleep(1)


threading.Thread(target=_lay_mau, daemon=True).start()
nhat_ky("bat dau lay mau VRAM/RAM 1 Hz")


class Doan:
    """Danh dau mot doan thoi gian de sau nay tinh dinh VRAM cua rieng no."""

    def __init__(self, nhan: str):
        self.nhan = nhan

    def __enter__(self):
        self.t0 = time.time()
        nhat_ky(f"--> {self.nhan}")
        return self

    def __exit__(self, *a):
        t1 = time.time()
        MOC.append({"nhan": self.nhan, "bat_dau": self.t0, "ket_thuc": t1,
                    "giay": round(t1 - self.t0, 1)})
        ghi("moc.json", MOC)
        nhat_ky(f"<-- {self.nhan}: {t1 - self.t0:.1f} giay")


KET_QUA = {"lan_chay": [], "loi": []}


def luu():
    ghi("ket_qua.json", KET_QUA)


def sinh(session, ten_do, model_type, base, seed, huy_sau=None):
    """Mot luot sinh, theo DUNG khuon trong `docs/API.md`:

        job = session.submit_task(settings)
        for event in job.events.iter(timeout=0.2): ...
        result = job.result()

    `huy_sau` > 0: mot luong phu goi `job.cancel()` sau ngan ay giay (kiem E4).
    """
    st = dict(base)
    st.update(model_type=model_type, seed=seed,
              video_length=SO_KHUNG, num_inference_steps=SO_BUOC,
              resolution=DO_PHAN_GIAI)
    ban_ghi = {"ten_do": ten_do, "model_type": model_type, "seed": seed,
               "huy_sau": huy_sau}
    try:
        with Doan(ten_do):
            job = session.submit_task(st)

            if huy_sau:
                def _huy():
                    time.sleep(huy_sau)
                    try:
                        job.cancel()
                        ban_ghi["da_goi_cancel_luc"] = round(huy_sau, 1)
                        nhat_ky("da goi job.cancel() sau", huy_sau, "giay")
                    except Exception as e:      # noqa: BLE001
                        ban_ghi["cancel_loi"] = str(e)
                threading.Thread(target=_huy, daemon=True).start()

            su_kien = {"progress": 0, "preview": 0, "stream": 0, "khac": 0}
            buoc_cuoi = None
            for ev in job.events.iter(timeout=0.5):
                kind = getattr(ev, "kind", "khac")
                su_kien[kind if kind in su_kien else "khac"] += 1
                if kind == "progress":
                    d = getattr(ev, "data", None)
                    buoc_cuoi = [getattr(d, "phase", None), getattr(d, "current_step", None),
                                 getattr(d, "total_steps", None)]

            kq = job.result()
            ban_ghi["su_kien"] = su_kien
            ban_ghi["tien_do_cuoi"] = buoc_cuoi
            ban_ghi["thanh_cong"] = bool(getattr(kq, "success", False))
            ban_ghi["tep"] = [str(x) for x in (getattr(kq, "generated_files", []) or [])]
            ban_ghi["loi"] = [str(getattr(e, "message", e))
                              for e in (getattr(kq, "errors", []) or [])]
    except Exception as e:
        ban_ghi["ngoai_le"] = f"{type(e).__name__}: {e}"
        ban_ghi["vet"] = traceback.format_exc()[-1500:]
        nhat_ky("LOI", ten_do, ban_ghi["ngoai_le"])
    KET_QUA["lan_chay"].append(ban_ghi)
    luu()
    return ban_ghi


def phien(nhan, profile, attention="sage2"):
    from shared.api import init
    with Doan(f"init_{nhan}"):
        return init(root=KHO, cli_args=["--config", "/data/config",
                                        "--profile", str(profile),
                                        "--attention", attention])


def main():
    from shared import api as _  # noqa: F401  — bao loi som neu import hong

    # ── Phien A: profile 4 (mac dinh cua WanGP) ──
    s = phien("profile4", 4)

    # E1/E2 — ban khai model va tham so mac dinh CUA CHINH WanGP
    for ten, ham in (("models.json", lambda: s.list_model_defs()),
                     ("model_metadata.json", lambda: s.list_model_metadata())):
        try:
            with Doan(ten):
                ghi(ten, ham())
        except Exception as e:
            KET_QUA["loi"].append({"muc": ten, "loi": str(e)})

    mac_dinh = {}
    for mt in ("t2v_2_2", "i2v_2_2"):
        try:
            mac_dinh[mt] = s.get_default_settings(mt)
            ghi(f"settings_{mt}.json", mac_dinh[mt])
            nhat_ky("lay duoc default settings cho", mt)
        except Exception as e:
            KET_QUA["loi"].append({"muc": f"default_{mt}", "loi": str(e)})
            mac_dinh[mt] = {}
    luu()

    base_t2v = dict(mac_dinh.get("t2v_2_2") or {})
    base_t2v.setdefault("prompt", "A calm river at dawn, mist over the water, "
                                  "slow cinematic dolly forward")

    # C1/D1/D2 — luot nguoi (gom nap model), roi luot am
    sinh(s, "R1_t2v_profile4_seed1001", "t2v_2_2", base_t2v, 1001)
    if con_gio():
        sinh(s, "R2_t2v_profile4_seed2002", "t2v_2_2", base_t2v, 2002)
    # D3 — LAP LAI seed cua R1 de PHAT HIEN CACHE (bay ①, V3 mat $1,29 vi no)
    if con_gio():
        sinh(s, "R3_t2v_profile4_seed1001_LAP", "t2v_2_2", base_t2v, 1001)

    # D4/O-008 — doi model t2v -> i2v, do thoi gian doi
    if con_gio() and mac_dinh.get("i2v_2_2"):
        base_i2v = dict(mac_dinh["i2v_2_2"])
        base_i2v.setdefault("prompt", base_t2v["prompt"])
        sinh(s, "R4_i2v_profile4_doi_model", "i2v_2_2", base_i2v, 3003)

    # E4 — kiem HUY giua chung: huy sau 45 giay, xem job tra ve gi
    if con_gio():
        sinh(s, "R7_t2v_HUY_giua_chung", "t2v_2_2", base_t2v, 6006, huy_sau=45)

    # ── Phien B: profile 3 (nap tron vao VRAM) ──
    if con_gio():
        try:
            s3 = phien("profile3", 3)
            sinh(s3, "R5_t2v_profile3", "t2v_2_2", base_t2v, 4004)
        except Exception as e:
            KET_QUA["loi"].append({"muc": "phien_profile3", "loi": str(e)})

    # ── Phien C: profile 2 (giu model khong dung o RAM) ──
    if con_gio():
        try:
            s2 = phien("profile2", 2)
            sinh(s2, "R6_t2v_profile2", "t2v_2_2", base_t2v, 5005)
        except Exception as e:
            KET_QUA["loi"].append({"muc": "phien_profile2", "loi": str(e)})

    KET_QUA["tong_phut"] = round((time.time() - BAT_DAU) / 60, 1)
    luu()
    (KQ / "_DO_XONG").write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")
    nhat_ky("XONG sau", KET_QUA["tong_phut"], "phut")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        KET_QUA["loi"].append({"muc": "main", "loi": str(e),
                               "vet": traceback.format_exc()[-3000:]})
        luu()
        nhat_ky("MAIN HONG:", e)
    finally:
        (KQ / "_KET_THUC").write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")
