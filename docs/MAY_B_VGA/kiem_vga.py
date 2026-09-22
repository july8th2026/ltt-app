"""Kiem trang thai mod VGA may B (chi DOC, khong ghi gi). Doc: Desktop\\Setup_VGA.md
Chay: C:\\Tools\\ModCard\\venv\\Scripts\\python.exe C:\\Tools\\ModCard\\kiem_vga.py
"""
import ctypes, subprocess, pynvml as n

# Cau hinh chot 22/09/2026 (don vi NVML = 2 x don vi Afterburner)
MONG_DOI = {
    "NVIDIA GeForce RTX 3090":    {"mem_nvml": 1500, "pl_w": 370},
    "NVIDIA GeForce RTX 5060 Ti": {"mem_nvml": 2000, "pl_w": 180},
}
ok = True
n.nvmlInit()
print("driver", n.nvmlSystemGetDriverVersion())
for i in range(n.nvmlDeviceGetCount()):
    h = n.nvmlDeviceGetHandleByIndex(i)
    ten = n.nvmlDeviceGetName(h)
    md = MONG_DOI.get(ten)
    off = {}
    for dom, t in ((n.NVML_CLOCK_MEM, "mem"), (n.NVML_CLOCK_GRAPHICS, "core")):
        info = n.c_nvmlClockOffset_t(); info.version = n.nvmlClockOffset_v1; info.type = dom; info.pstate = 2
        n.nvmlDeviceGetClockOffsets(h, ctypes.byref(info)); off[t] = info.clockOffsetMHz
    pl = n.nvmlDeviceGetEnforcedPowerLimit(h) / 1000
    nhiet = n.nvmlDeviceGetTemperature(h, n.NVML_TEMPERATURE_GPU)
    print(f"GPU{i} {ten}: offset nho={off['mem']} (NVML) nhan={off['core']} power_limit={pl:.0f}W nhiet={nhiet}C")
    if md is None:
        print("   !! card khong co trong cau hinh chot"); ok = False; continue
    if off["mem"] != md["mem_nvml"]:
        print(f"   !! offset nho {off['mem']} != mong doi {md['mem_nvml']}"); ok = False
    if off["core"] != 0:
        print("   !! offset NHAN khac 0 - cau hinh chot KHONG dung nhan"); ok = False
    if abs(pl - md["pl_w"]) > 1:
        print(f"   !! power limit {pl:.0f} != {md['pl_w']}"); ok = False

r = subprocess.run(["powershell", "-NoProfile", "-Command",
    "$t=Get-ScheduledTask LTT_ModCard_NVML_KhoiDong -EA SilentlyContinue; if ($t) { 'tac vu: ' + $t.State + ' ket_qua_lan_cuoi=' + (Get-ScheduledTaskInfo LTT_ModCard_NVML_KhoiDong).LastTaskResult } else { 'tac vu: KHONG TON TAI' }"],
    capture_output=True, text=True)
print(r.stdout.strip())
if "KHONG TON TAI" in r.stdout: ok = False
try:
    print("log dat_offset (3 dong cuoi):")
    for d in open(r"C:\Tools\ModCard\dat_offset.log", encoding="utf-8").read().splitlines()[-3:]:
        print("   " + d)
except FileNotFoundError:
    print("   !! khong co dat_offset.log"); ok = False
print("KET LUAN:", "DUNG CAU HINH CHOT" if ok else "LECH - xem Setup_VGA.md muc 6")
