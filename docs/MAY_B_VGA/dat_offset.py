"""Dat offset xung NHO qua NVML cho tung card, ghi log. KHONG dong toi nhan/dien ap/power limit.
python dat_offset.py 1500 2000   (don vi NVML cho GPU0=3090, GPU1=5060 Ti; 0 0 = ve mac dinh)
Kiem ten card truoc khi dat: sai ten => khong dat gi (phong khi thu tu GPU doi)."""
import ctypes, sys, time, pynvml as n
MUON = {"NVIDIA GeForce RTX 3090": int(sys.argv[1]), "NVIDIA GeForce RTX 5060 Ti": int(sys.argv[2])}
# Don vi NVML = 2x don vi Afterburner (NVML 1500 = Afterburner +750 = +750 MHz tren nvidia-smi)
TRAN = {"NVIDIA GeForce RTX 3090": 2000, "NVIDIA GeForce RTX 5060 Ti": 3000}   # chan go nham
log = open(r"C:\Tools\ModCard\dat_offset.log", "a", encoding="utf-8")
def ghi(s):
    s = time.strftime("%Y-%m-%d %H:%M:%S ") + s; print(s); log.write(s + "\n"); log.flush()
n.nvmlInit()
for i in range(n.nvmlDeviceGetCount()):
    h = n.nvmlDeviceGetHandleByIndex(i); ten = n.nvmlDeviceGetName(h)
    if ten not in MUON: ghi(f"GPU{i} {ten}: khong trong danh sach, bo qua"); continue
    mhz = MUON[ten]
    if not (0 <= mhz <= TRAN[ten]): ghi(f"GPU{i} {ten}: {mhz} ngoai [0,{TRAN[ten]}], TU CHOI"); continue
    for ps in (0, 1, 2):
        info = n.c_nvmlClockOffset_t(); info.version = n.nvmlClockOffset_v1
        info.type = n.NVML_CLOCK_MEM; info.pstate = ps; info.clockOffsetMHz = mhz
        try:
            n.nvmlDeviceSetClockOffsets(h, ctypes.byref(info)); ghi(f"GPU{i} {ten}: P{ps} MEM offset={mhz} OK")
        except Exception as e:
            ghi(f"GPU{i} {ten}: P{ps} MEM LOI {type(e).__name__} {e}")
