"""Tao Pod A100 cho lượt đo P01.

⛔ LUẬT V3 ĐÃ TRẢ GIÁ: câu lệnh ngay sau khi có `id` phải là GHI SỔ.
   Không `print`, không gì khác chen vào — V3 từng tạo pod thành công rồi chết ở
   dòng `print` kế tiếp vì stdout cp1252, để lại một pod tính tiền không có
   trong sổ.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from tools.video_cloud import nap_env, tao_client  # noqa: E402

nap_env(Path("secrets/app.env"))
api = tao_client()

SO = Path(r"C:/Users/THANGT~1/AppData/Local/Temp/claude/D--LTTSTUDIOSAPP"
          r"/1db472be-9817-4fea-b77b-36ef2b641dac/scratchpad/b4/SO_TAI_NGUYEN.jsonl")

GPU = "NVIDIA A100-SXM4-80GB"
DC = "US-KS-2"

# ── Tiền kiểm: tồn kho và giá ngay lúc này ──
d = api._graphql(
    'query { gpuTypes { id displayName memoryInGb '
    'lowestPrice(input: {gpuCount: 1, dataCenterId: "%s"}) '
    '{ uninterruptablePrice stockStatus } } }' % DC)
co = None
for g in d.get("gpuTypes") or []:
    lp = g.get("lowestPrice") or {}
    if g.get("id") == GPU and lp.get("uninterruptablePrice"):
        co = (lp["uninterruptablePrice"], lp.get("stockStatus"))
print(f"[tien kiem] {GPU} @ {DC}: {co}")
if co is None:
    print("DUNG: khong thue duoc GPU nay o DC cua volume. Khong tu doi sang card khac.")
    raise SystemExit(2)

than = {
    "name": "lttv-wangp-p01",
    "imageName": "nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04",
    "gpuTypeIds": [GPU],
    "gpuCount": 1,
    "dataCenterIds": [DC],
    "networkVolumeId": "uizchbiet5",
    "volumeMountPath": "/data",          # KHONG /workspace — xung dot voi WanGP
    "containerDiskInGb": 20,             # mac dinh 50
    "minRAMPerGPU": 64,                  # mac dinh 8 — qua it cho profile 1/2
    "minVCPUPerGPU": 8,
    "env": {"HF_HOME": "/data/hf", "LTTV_TRAN_PHUT": "150"},
    "dockerEntrypoint": ["bash", "-lc", "bash /data/lttv/khoi_dong.sh"],
    "dockerStartCmd": [],
}
print("[tao pod] dang goi POST /pods ...")
pod = api._rest("POST", "/pods", than)
pid = pod.get("id")

# ⛔ DONG NGAY SAU — khong duoc co gi chen vao giua
with open(SO, "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"luc": time.time(), "pod_id": pid, "gpu": GPU, "dc": DC,
                         "gia_gio": co[0], "ten": than["name"]}, ensure_ascii=False) + "\n")
    fh.flush()
    os.fsync(fh.fileno())

print(f"[SO] da ghi pod_id={pid} vao {SO}")
print(json.dumps({k: pod.get(k) for k in
                  ("id", "name", "desiredStatus", "machineId", "costPerHr")},
                 ensure_ascii=False, indent=1))
