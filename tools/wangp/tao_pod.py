"""Tao Pod cho LTT VIDEO V2.1 — bo chinh chu WanGP (CUDA 13 / py3.11 / cu130).

    py tools/wangp/tao_pod.py [ten-anh-container]

⛔ LUAT V3 DA TRA GIA: cau lenh ngay sau khi co `id` phai la GHI SO.
   Khong `print`, khong gi khac chen vao — V3 tung tao pod thanh cong roi chet o
   dong `print` ke tiep vi stdout cp1252, de lai mot pod tinh tien khong co
   trong so.

⛔ `gpuTypeIds` la MOT DANH SACH UU TIEN, khong phai mot lua chon. Ngay 06/09
   toi truyen DUNG MOT loai, nen khi `US-KS-2` het A100 la ket cung — sau luot
   `start` deu `not enough free GPU`. Xem `TAI_NGUYEN_VA_CACH_DUNG_LAI.md` §3.

⛔ `PATCH /pods/{id}` KHONG nhan `gpuTypeIds` (tra 400). Chi dat duoc luc tao.
   Muon doi danh sach => xoa pod, tao lai. Moi truong tren volume khong mat.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from tools.wangp.may_cloud import nap_env, tao_client, tim_app_env  # noqa: E402

nap_env(tim_app_env())
api = tao_client()

SO = Path(r"C:/Users/THANGT~1/AppData/Local/Temp/claude/D--LTTSTUDIOSAPP"
          r"/1db472be-9817-4fea-b77b-36ef2b641dac/scratchpad/b4/SO_TAI_NGUYEN.jsonl")
SO.parent.mkdir(parents=True, exist_ok=True)

#: Anh nen. Bo chinh chu can CUDA 13 vi banh xe nhan GGUF cua WanGP nham toi
#: `torch210cu130py311`. Driver may chu do duoc 13.0 (do 06/09: 580.159.04).
ANH = sys.argv[1] if len(sys.argv) > 1 else "nvidia/cuda:13.0.1-cudnn-devel-ubuntu22.04"

#: Xep RE TRUOC. Duoi 5 worker, RunPod luon lay loai uu tien cao nhat CON HANG.
GPU_UU_TIEN = [
    "NVIDIA A100-SXM4-80GB",
    "NVIDIA A100 80GB PCIe",
    "NVIDIA H100 PCIe",
    "NVIDIA H100 NVL",
]
DC = "US-KS-2"          # ghim: volume nam o day, khong ghim thi khong gan duoc

# ── Tien kiem: loai nao con hang ngay luc nay ──
d = api.graphql(
    'query { gpuTypes { id displayName memoryInGb '
    'lowestPrice(input: {gpuCount: 1, dataCenterId: "%s"}) '
    '{ uninterruptablePrice stockStatus } } }' % DC)
gia = {}
for g in d.get("gpuTypes") or []:
    lp = g.get("lowestPrice") or {}
    if lp.get("uninterruptablePrice"):
        gia[g.get("id")] = (lp["uninterruptablePrice"], lp.get("stockStatus"))
print(f"[tien kiem] ton kho @ {DC}:")
for t in GPU_UU_TIEN:
    print(f"    {t:28} {gia.get(t, 'KHONG CO')}")
# ⚠️ `lowestPrice` bao co != thue duoc (§5 cua TAI_NGUYEN). Day chi la chi dau,
#    nen ta VAN gui ca danh sach de RunPod tu chon loai con hang.
if not any(t in gia for t in GPU_UU_TIEN):
    print("DUNG: khong loai nao trong danh sach con hang o DC cua volume.")
    raise SystemExit(2)

than = {
    "name": "lttv-wangp-v1",
    "imageName": ANH,
    "gpuTypeIds": GPU_UU_TIEN,
    "gpuCount": 1,
    "dataCenterIds": [DC],
    "networkVolumeId": "uizchbiet5",
    "volumeMountPath": "/data",          # KHONG /workspace — xung dot voi WanGP
    "containerDiskInGb": 20,             # mac dinh 50, va no TINH TIEN
    "minRAMPerGPU": 64,                  # mac dinh 8 — qua it cho profile 1
    "minVCPUPerGPU": 8,
    # ⛔ MANG, khong phai chuoi. RunPod tra 400:
    #    "At /pods/properties/ports/type: got string, want array"
    "ports": ["8888/http", "22/tcp"],
    "env": {"HF_HOME": "/data/hf"},
    "dockerEntrypoint": ["bash", "-lc", "bash /data/lttv/khoi_dong.sh"],
    "dockerStartCmd": [],
}
print(f"[tao pod] anh={ANH}")
print("[tao pod] dang goi POST /pods ...")
pod = api.rest("POST", "/pods", than)
pid = pod.get("id")

# ⛔ DONG NGAY SAU — khong duoc co gi chen vao giua
with open(SO, "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"luc": time.time(), "pod_id": pid, "anh": ANH,
                         "gpu_uu_tien": GPU_UU_TIEN, "dc": DC,
                         "ten": than["name"]}, ensure_ascii=False) + "\n")
    fh.flush()
    os.fsync(fh.fileno())

print(f"[SO] da ghi pod_id={pid} vao {SO}")
print(json.dumps({k: pod.get(k) for k in
                  ("id", "name", "desiredStatus", "machineId", "costPerHr",
                   "imageName", "ports")},
                 ensure_ascii=False, indent=1))
