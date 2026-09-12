"""
gpu_check.py — kiem tra moi truong GPU tren MAY B (H37 / G1).

    E:\\AI\\venv\\Scripts\\python.exe E:\\AI\\ltt_render\\scripts\\gpu_check.py

Chay bang venv CUA COMFYUI vi no can `torch`. Cong render dung venv rieng va
KHONG can torch — do la co y: cong render chi noi HTTP, no khong nap model.

** NGUYEN TAC: mot phep kiem KHONG BIET FAIL thi khong phai phep kiem.
   Moi cau hoi duoi day deu co the tra loi KHONG, va cau cuoi cung thuc su
   TINH TOAN tren GPU roi doi chieu ket qua - khong chi hoi "cuda.is_available()".

** VI SAO CAN CAU CUOI: `torch.cuda.is_available()` tra True ca khi driver va
   runtime lech phien ban den muc moi phep tinh deu ra rac. Buoc 03 cua bo build
   pack noi dung: "Chi coi buoc nay dat khi CUDA operation thuc te chay thanh cong."
"""
from __future__ import annotations

import json
import platform
import sys
from typing import Any

MB = 1024 * 1024


def _hoi_smi() -> dict:
    """VRAM/nhiet/cong suat THAT tren card, hoi nvidia-smi.

    Day la nguon DUY NHAT trong tep nay thay duoc ca card, ke ca phan tien trinh
    khac dang giu. Xem chu thich o phan cap phat VRAM de biet vi sao.
    """
    import shutil
    import subprocess
    if not shutil.which("nvidia-smi"):
        return {"vram_dung_mb": None, "ly_do": "khong co nvidia-smi tren may"}
    # 🔴 HOI THEO UUID, KHONG LAY DONG DAU TIEN (Task 6.1, sot lai).
    #    May B co HAI card tu 11/09: 3090 (model anh + LTT-3.8) va 5060 Ti
    #    (LTT-3.5). `dong[0]` la "card nao nvidia-smi liet ke truoc" - mot thu tu
    #    KHONG ai hua, va doi duoc khi cam lai khe PCIe. Doc no roi goi la "VRAM
    #    cua card ta" la mot phep do lech chieu.
    #
    # ⛔ KHONG BIET UUID => TRA `None`, KHONG roi ve `dong[0]`. Ban dau toi viet
    #    mot nhanh du phong "van doc dong dau, kem co `loc_theo_card: False`" va
    #    banh coc `test_1220` do — dung. Mot con so VRAM khong quy duoc ve mot
    #    card cu the thi khong phai mot phep do, ke ca khi co mot co noi rang no
    #    khong biet: nguoi doc bao cao chan doan se trich CON SO, khong trich cai
    #    co. Cong cu nay van in moi thu khac (python, torch, compute capability);
    #    no chi tu choi noi mot con so no khong quy duoc ve dau.
    uuid_3090 = None
    try:
        from render_gateway.danh_tinh_gpu import uuid_38
        uuid_3090 = uuid_38()
    except Exception as e:                                        # noqa: BLE001
        return {"vram_dung_mb": None, "ly_do": f"khong doc duoc danh tinh GPU: {e}"}

    truy_van = ("uuid,memory.used,memory.total,temperature.gpu,power.draw,"
                "power.limit")
    try:
        r = subprocess.run(
            ["nvidia-smi", f"--query-gpu={truy_van}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8, encoding="utf-8",
            errors="replace")
    except Exception as e:                                        # noqa: BLE001
        return {"vram_dung_mb": None, "ly_do": f"nvidia-smi loi: {e}"}
    if r.returncode != 0:
        return {"vram_dung_mb": None, "ly_do": f"nvidia-smi tra ma {r.returncode}"}
    dong = [d.strip() for d in (r.stdout or "").splitlines() if d.strip()]
    if not dong:
        return {"vram_dung_mb": None, "ly_do": "nvidia-smi khong tra dong nao"}

    if not uuid_3090:
        return {"vram_dung_mb": None,
                "ly_do": "khong biet UUID card 3090 (thieu gpu_may_b.json; "
                         "chi tay bang LTT_GPU_DANH_TINH)"}
    chon = None
    for d in dong:
        o = [x.strip() for x in d.split(",")]
        if o and o[0] == uuid_3090:
            chon = o
            break
    if chon is None:
        return {"vram_dung_mb": None,
                "ly_do": f"nvidia-smi khong thay card 3090 ({uuid_3090})"}

    try:
        return {
            "gpu_uuid": chon[0],
            "vram_dung_mb": int(float(chon[1])),
            "vram_tong_mb": int(float(chon[2])),
            "nhiet_c": int(float(chon[3])),
            "power_w": float(chon[4]),
            "power_limit_w": float(chon[5]),
        }
    except (ValueError, IndexError) as e:
        return {"vram_dung_mb": None, "ly_do": f"khong doc duoc: {e}"}


def main() -> int:
    ra: dict[str, Any] = {"ok": True, "loi": []}

    def hong(msg: str) -> None:
        ra["ok"] = False
        ra["loi"].append(msg)

    ra["python"] = sys.version.split()[0]
    ra["os"] = platform.platform()

    try:
        import torch
    except Exception as e:                                        # noqa: BLE001
        hong(f"khong import duoc torch: {e}")
        print(json.dumps(ra, ensure_ascii=False, indent=2))
        return 1

    ra["torch"] = torch.__version__
    ra["cuda_runtime"] = torch.version.cuda
    ra["cuda_available"] = bool(torch.cuda.is_available())
    if not ra["cuda_available"]:
        hong("torch.cuda.is_available() = False")
        print(json.dumps(ra, ensure_ascii=False, indent=2))
        return 1

    ra["so_gpu"] = torch.cuda.device_count()
    gpus = []
    for i in range(ra["so_gpu"]):
        p = torch.cuda.get_device_properties(i)
        gpus.append({
            "index": i,
            "ten": p.name,
            "vram_mb": p.total_memory // MB,
            "compute_capability": f"{p.major}.{p.minor}",
            "so_sm": p.multi_processor_count,
        })
    ra["gpus"] = gpus

    cc = (gpus[0]["compute_capability"] if gpus else "0.0")
    ra["bf16_ho_tro"] = bool(torch.cuda.is_bf16_supported())
    # FP8 tensor core chi co tu Ada (8.9) tro len. Tren Ampere (8.6) fp8 chi giup
    # VUA VRAM chu KHONG nhanh hon - trong so luu fp8 nhung phai giai nen ve bf16
    # luc tinh. Xem DECISIONS.md D-004.
    ra["fp8_tensor_core"] = float(cc) >= 8.9
    ra["ghi_chu_fp8"] = ("co tensor core fp8" if ra["fp8_tensor_core"] else
                         "KHONG co tensor core fp8: fp8 de VUA VRAM, khong de nhanh hon")

    # --- Phep tinh THAT tren GPU, roi doi chieu ket qua --------------------------
    try:
        a = torch.randn(2048, 2048, device="cuda", dtype=torch.bfloat16)
        b = torch.randn(2048, 2048, device="cuda", dtype=torch.bfloat16)
        c = (a @ b).float()
        # Doi chieu voi CPU. Sai so bf16 lon nen dung nguong rong, muc dich la bat
        # truong hop ket qua thanh RAC hoac NaN, khong phai do do chinh xac.
        c_cpu = (a.float().cpu() @ b.float().cpu())
        lech = (c.cpu() - c_cpu).abs().max().item()
        ra["matmul_bf16_lech_max"] = round(lech, 3)
        ra["matmul_bf16_chay_that"] = bool(torch.isfinite(c).all().item())
        if not ra["matmul_bf16_chay_that"]:
            hong("phep nhan ma tran bf16 tra ve NaN/Inf")
        if lech > 50:
            hong(f"ket qua GPU lech qua xa CPU ({lech:.1f}) - nghi driver/runtime lech")
    except Exception as e:                                        # noqa: BLE001
        hong(f"phep tinh tren GPU that bai: {e}")

    # --- Cap phat roi giai phong, kiem VRAM co TRA VE khong ----------------------
    # Ro ri VRAM la loai loi chi lo ra sau vai tram lan sinh anh (G9). Bat duoc no
    # o day thi re hon nhieu.
    #
    # !! CAC SO VRAM DUOI DAY CHI NOI VE TIEN TRINH NAY, KHONG PHAI CA CARD.
    #    Do that tren may B ngay 2026-08-21: mot tien trinh khac giu 8 GB, ba nguon
    #    tra loi "con trong bao nhieu" nhu sau —
    #        nvidia-smi              15.308 MiB   <- DUNG
    #        ComfyUI /system_stats   23.165 MiB   <- MU
    #        torch mem_get_info      23.217 MiB   <- MU
    #    Tren Windows/WDDM hai nguon sau chi thay tien trinh cua chinh minh.
    #    Muon biet CA CARD dang dung bao nhieu thi phai hoi nvidia-smi - xem
    #    truong "nvidia_smi" o duoi, va `render_gateway/busy.py`.
    try:
        torch.cuda.empty_cache()
        truoc = torch.cuda.mem_get_info()[0] // MB
        khoi = torch.empty(int(2 * 1024 * MB / 2), dtype=torch.float16, device="cuda")
        giua = torch.cuda.mem_get_info()[0] // MB
        del khoi
        torch.cuda.empty_cache()
        sau = torch.cuda.mem_get_info()[0] // MB
        ra["vram_TIEN_TRINH_NAY_trong_truoc_mb"] = truoc
        ra["vram_TIEN_TRINH_NAY_trong_khi_giu_mb"] = giua
        ra["vram_TIEN_TRINH_NAY_trong_sau_mb"] = sau
        ra["vram_tra_ve_du"] = (truoc - sau) < 128      # cho phep chenh 128 MB
        if not ra["vram_tra_ve_du"]:
            hong(f"VRAM khong tra ve du: truoc {truoc} MB, sau {sau} MB")
    except Exception as e:                                        # noqa: BLE001
        hong(f"thu cap phat VRAM that bai: {e}")

    # --- Doi chieu voi nvidia-smi: nguon DUY NHAT thay ca card -------------------
    ra["nvidia_smi"] = _hoi_smi()
    if ra["nvidia_smi"].get("vram_dung_mb") is None:
        ra["canh_bao"] = ("khong hoi duoc nvidia-smi - KHONG biet tien trinh khac "
                          "co dang giu card khong")

    print(json.dumps(ra, ensure_ascii=False, indent=2))
    return 0 if ra["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
