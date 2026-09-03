"""giam_sat_may.py — hop den cua may. Ghi lien tuc, doc lai sau mot lan treo.

    python tools/giam_sat_may.py --chay          # chay nen, ghi moi 15s
    python tools/giam_sat_may.py --kham          # KHAM NGHIEM sau mot lan reset
    python tools/giam_sat_may.py --kham 2        # kham hai lan dut gan nhat
    python tools/giam_sat_may.py --trang-thai    # dang chay khong

## Khac gi `nhat_ky_chay.py`

    nhat_ky_chay   ghi MOT luot chay, boc quanh mot lenh
    giam_sat_may   ghi LIEN TUC, khong phu thuoc ai chay gi

Ngay 03/09 may reset **hai lan**. Ca hai lan `nhat_ky_chay` deu chua ton tai
hoac chua duoc dung, va quan trong hon: **cai lam treo may co the khong phai
lenh ta boc**. Do duoc luc do: cay gate co 13 tien trinh, toan may co 58. Bon
muoi lam cai con lai — bot, phien Claude khac, dich vu production, deploy — khong
di qua bat cu thu gi ta boc duoc.

⇒ Hop den phai ghi **may**, khong phai **lenh cua ta**.

## 🔑 `--kham` la ly do tep nay ton tai

Ghi log thi de. Cai kho la sau mot lan reset, doc mot nghin dong JSON de tra loi
"cai gi lam treo". `--kham` lam viec do:

  1. tim cho log **DUT** (khoang trong > 3 nhip = may chet hoac ngu)
  2. lay 6 mau cuoi truoc khi dut
  3. xep hang tien trinh theo CPU va RAM o dung nhung mau do
  4. so voi nen binh thuong cua chinh may (trung vi 24h) de biet cai gi BAT THUONG

⛔ No khong doan nguyen nhan. No dua ra ai dang chiem cho luc do va cai gi lech
   khoi thuong le — phan ket luan la cua nguoi doc. Mot cong cu tu ket luan se
   dan nguoi doc vao gia thuyet dau tien, va do dung la kieu sai da xay ra chin
   lan trong mot ngay o du an nay.

## Ba rang buoc thiet ke

### 1. Chinh no khong duoc thanh nghi can

Bai hoc dat nhat 03/09: phep do cua toi la mot trong ba ung vien lam treo may —
`process_iter` qua 58 tien trinh, `cpu_percent` tung cai, moi 2 giay.

⇒ Nhip **15 giay**, va moi vong chi lay **top 5** tien trinh theo CPU. Do bang
  `oneshot()` de mot lan doc lay het truong, thay vi goi lai tung truong.

### 2. `flush` + `fsync` moi dong

Mot lan treo khong cho tien trinh dong tep. Thu nam trong buffer la thu khong
bao gio doc lai duoc, dung luc no dang gia nhat.

### 3. ASCII thuan o dau ra

`print` mot emoji vo voi `UnicodeEncodeError` tren stdout cp1252 — va no vo o
dung nhanh "bi cat", tuc dung luc can doc nhat. Da xay ra that voi
`nhat_ky_chay.py`.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

#: Noi ghi. Mac dinh `%TEMP%`, nhung **ban dat o `Desktop\HOP DEN` tu ghi canh
#: chinh no** — vi mot hop den nam trong `%TEMP%` la mot hop den co the bi don
#: dep, va nam trong mot worktree la mot hop den bien mat khi worktree bi go.
#:
#: Thu tu uu tien:
#:   1. bien moi truong `LTT_HOP_DEN`
#:   2. thu muc `du_lieu` canh script, NEU thu muc cha ten co "HOP DEN"
#:   3. `%TEMP%/ltt_hop_den`
def _thu_muc_ghi() -> Path:
    tu_env = os.environ.get("LTT_HOP_DEN", "").strip()
    if tu_env:
        return Path(tu_env)
    canh = Path(__file__).resolve().parent
    if "HOP DEN" in canh.name.upper():
        return canh / "du_lieu"
    return Path(tempfile.gettempdir()) / "ltt_hop_den"


THU_MUC = _thu_muc_ghi()

#: Nhip ghi luc BINH THUONG. Thua co y — xem rang buoc 1 dau tep.
NHIP_S = 15.0

#: Nhip ghi khi may dang CANG. Xem `_dang_cang`.
#:
#: ⭐ Y tuong nay lay tu `gpu_recorder.py` cua `D:\FULL AUTO VIDEO` (0,5s binh
#:    thuong / 0,2s khi cang): khoanh khac truoc khi mot may chet co the chi dai
#:    vai tram mili-giay, va do dung la doan can do phan giai cao nhat.
#:
#: ⚠️ Nhung o day 15s/1s chu khong 0,5s/0,2s. Ban kia ghi 34 MB moi ngay cho
#:    RIENG GPU; hop den nay con ghi ca bang tien trinh, nen cung nhip do se
#:    thanh vai tram MB/ngay va tu bien minh thanh mot nghi can.
NHIP_NONG_S = 1.0

#: Bao lau thi thoi coi la cang, sau khi cac dieu kien da het (giay).
#:
#: 🔑 Co do tre nay vi doan HA TAI cung dang doc: neu tai tut ma may van chet
#:    thi do la mot chuyen; neu tai tut roi may song lai thi la chuyen khac.
#:    Cat nhip nhanh ngay khi het cang se lam mat dung doan phan biet hai cai.
NGUI_S = 60.0

#: Nguong coi la "dang cang".
#:
#: 🔴 Ba nguong dau (CPU, RAM, swap) la phan `gpu_recorder.py` KHONG co, va do
#:    la ly do co che tang nhip cua no chua tung kich hoat dung luc: `_is_hot`
#:    cua no chi nhin nhiet do, dien nang va VRAM. Ca ba lan may dut ngay 03/09,
#:    GPU deu lanh (8,7 W, 48 C) trong khi CPU chay 100% va RAM dang tut —
#:    tuc no ghi 0,5s/mau suot mot ngay ma van o nhip THUONG dung luc quan
#:    trong nhat.
CANG_CPU = 85.0          # %
CANG_RAM_GIB = 4.0       # RAM trong con lai
CANG_SWAP_GIB = 2.0      # swap dang dung
CANG_NHIET_C = 75.0      # nhiet GPU
CANG_DIEN_TI_LE = 0.85   # power.draw / power.limit
CANG_VRAM_TRONG_MB = 2048

#: Truong lay tu nvidia-smi. Lay NGUYEN bo cua `gpu_recorder.py`: bo do da qua
#: mot thang van hanh that va tung truong deu co ly do o do.
#:
#: 🔑 `clocks_event_reasons.active` la truong dat gia nhat va la thu ban dau toi
#:    KHONG lay. No phan biet ba kieu chet ma moi so lieu khac deu tron lan:
#:    qua nhiet (HwThermalSlowdown), thieu nguon (HwPowerBrakeSlowdown), va cham
#:    xung theo phan mem (SwPowerCap). Khong co no thi "GPU 50 C, 20 W" va "GPU
#:    dang bi ha xung vi nguon" trong y het nhau.
SMI_TRUONG = ("index,memory.used,memory.free,utilization.gpu,utilization.memory,"
              "temperature.gpu,power.draw,power.limit,clocks.sm,fan.speed,pstate,"
              "clocks_event_reasons.active")

#: Giai ma bitmask `clocks_event_reasons.active`.
#:
#: ⛔ Bit 0 (`GpuIdle`) BAT gan nhu lien tuc tren mot may de ban — no khong phai
#:    van de. Gop no vao "co chan xung" se cho ra bao dong o 100% so mau, va mot
#:    canh bao luon bat thi khong con la canh bao.
SMI_CO = {
    0x0001: "nhan roi",
    0x0002: "xung theo ung dung",
    0x0004: "tran dien (phan mem)",
    0x0008: "ha xung phan cung",
    0x0010: "dong bo boost",
    0x0020: "qua nhiet (phan mem)",
    0x0040: "QUA NHIET (phan cung)",
    0x0080: "THIEU NGUON (power brake)",
    0x0100: "xung theo man hinh",
}

#: Nhung co THUC SU dang lo — dung cho canh bao, khac voi `SMI_CO` dung de in.
SMI_CO_LO = 0x0004 | 0x0008 | 0x0020 | 0x0040 | 0x0080

#: Bao nhieu tien trinh nang nhat duoc ghi moi vong.
#:
#: ⚠️ 10 chu khong 5: chu du an muon thay "moi tac vu dang chay". Ghi het 330
#:    tien trinh moi 15 giay la 8 MB/gio va bien hop den thanh mot nghi can —
#:    nen lay 10 nang nhat, du de thay ai chiem cho ma khong phinh.
TOP_N = 10

#: Cach nhau it nhat bao nhieu giay thi doc GPU mot lan. `nvidia-smi` la mot
#: TIEN TRINH CON (~80ms), nen no khong duoc di theo nhip 1 giay cua che do cang.
#:
#: ⭐ Tinh theo THOI GIAN chu khong theo so vong: o che do cang nhip la 1s, neu
#:    dem vong thi "moi 2 vong" thanh 2 giay va ta tu them 1800 tien trinh con
#:    moi gio — dung kieu tu-bien-thanh-nghi-can ma ca tep nay dung de tranh.
GPU_CACH_S = 30.0        # binh thuong
GPU_CACH_NONG_S = 3.0    # khi dang cang

#: Bang tien trinh giu GPU it doi. Ghi lai ca danh sach moi mau la lang phi —
#: chi ghi khi TAP PID doi, con lai ghi mot con so.
GPU_APP_GHI_LAI_S = 300.0

#: Khoang trong bao nhieu NHIP thi coi la log DUT (may chet / ngu / reset).
NHIP_COI_LA_DUT = 3

#: Giu bao nhieu ngay. Moi ngay mot tep.
GIU_NGAY = 7


#: Da dat moc `cpu_percent` cho tung tien trinh chua. Xem `mot_vong`.
_da_dat_moc = False

#: Lan cuoi doc GPU (monotonic). Xem `GPU_CACH_S`.
_gpu_lan_cuoi = 0.0

#: Tap PID cham GPU o lan ghi day du gan nhat, va thoi diem ghi day du do.
_gpu_app_pid: frozenset = frozenset()
_gpu_app_luc = 0.0

#: Lan cuoi thay may CANG (monotonic). Xem `NGUI_S`.
_cang_luc = -1e9


def _tep_hom_nay() -> Path:
    THU_MUC.mkdir(parents=True, exist_ok=True)
    return THU_MUC / f"{datetime.now():%Y%m%d}.jsonl"


def _don_tep_cu() -> None:
    """Xoa tep qua han. Mot hop den phinh mai se bi ai do xoa ca thu muc."""
    gioi_han = time.time() - GIU_NGAY * 86400
    for t in THU_MUC.glob("*.jsonl"):
        try:
            if t.stat().st_mtime < gioi_han:
                t.unlink()
        except OSError:
            pass


def _giai_ma_co(hex_str: str) -> list[str]:
    """Bitmask `clocks_event_reasons.active` -> ten doc duoc."""
    try:
        v = int(hex_str, 16)
    except (ValueError, TypeError):
        return []
    return [ten for bit, ten in SMI_CO.items() if v & bit]


def _so(x: str, mac_dinh=None):
    """`nvidia-smi` tra `[N/A]` cho nhieu truong. Mot truong vang KHONG duoc lam
    hong ca dong.

    🔴 Ban dau doan doc `used_memory` dung `int()` tran trong mot `try` bao ca
       vong lap. Mot dong `[N/A]` nem ValueError va **vut ca danh sach 15 PID**,
       roi ket qua ve None — trong y het "khong co tien trinh nao cham GPU".
       Cung lop loi voi nhung loi im lang khac cua ngay 03/09: mot phep do hong
       trong giong het mot may ranh.
    """
    try:
        return float(x)
    except (ValueError, TypeError):
        return mac_dinh


def _gpu(day_du_app: bool = True) -> dict:
    """Trang thai day du tung card, va tien trinh nao dang cham GPU.

    🔑 **Tien trinh cham GPU la nua quan trong hon.** "VRAM 15/16 GiB" khong noi
       ai giu; may nay co bot dungvideo, LTT Voice, whisper, Ollama, va hai phien
       Claude cung co the cham GPU. Mot lan treo do VRAM ma khong biet ai giu thi
       cung vo dung nhu "python.exe an 77%".

    ⚠️ `pynvml` khong co tren may nay (da kiem), nen dung `nvidia-smi`. Neu no
       vang mat hoac qua han thi tra rong — mot phep do hong khong duoc lam hong
       ca vong ghi.
    """
    ra: dict = {}
    co_cua_so = 0x08000000 if os.name == "nt" else 0
    try:
        r = subprocess.run(
            ["nvidia-smi", f"--query-gpu={SMI_TRUONG}",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
            creationflags=co_cua_so)
        card = []
        for d in r.stdout.strip().splitlines():
            c = [x.strip() for x in d.split(",")]
            if len(c) < 12:
                continue
            m = {"id": int(_so(c[0], 0)),
                 "vram_mb": _so(c[1]),
                 "vram_trong_mb": _so(c[2]),
                 "util": _so(c[3]),
                 "util_bonho": _so(c[4]),
                 "nhiet_c": _so(c[5]),
                 "dien_w": _so(c[6]),
                 "dien_tran_w": _so(c[7]),
                 "xung_mhz": _so(c[8]),
                 "quat": _so(c[9]),
                 "pstate": c[10],
                 "co": c[11]}
            card.append({k: v for k, v in m.items() if v is not None})
        if card:
            ra["gpu"] = card
            ra["dien_tong_w"] = round(sum(x.get("dien_w", 0) for x in card), 1)
    except (OSError, subprocess.SubprocessError, ValueError):
        return ra

    if not day_du_app:
        return ra
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
            creationflags=co_cua_so)
        app = []
        for d in r.stdout.strip().splitlines():
            c = [x.strip() for x in d.split(",")]
            if len(c) < 2 or not c[0].isdigit():
                continue
            # ⚠️ `used_memory` tra `[N/A]` tren may NAY, va do khong phai loi
            #    lenh: o che do WDDM (GPU tieu dung tren Windows) driver KHONG
            #    bao VRAM theo tung tien trinh, chi bao tong cua card. Van ghi
            #    PID — biet ai dang giu context GPU la du de doi chieu.
            app.append({"pid": int(c[0]), "vram_mb": _so(c[1])})
        if app:
            ra["gpu_app"] = app
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return ra


def _nhan(p) -> str:
    """Nhan ngan doc duoc cho mot tien trinh. `python.exe` khong noi len gi ca."""
    import psutil
    try:
        cl = p.cmdline()
    except (psutil.Error, OSError):
        return ""
    if len(cl) < 2:
        return ""
    for i, x in enumerate(cl[1:], 1):
        x = str(x)
        # ⛔ `-c` di kem ca mot doan MA NGUON. Lay no lam nhan cho ra mot chuoi
        #    nhieu dong, dai, va khong noi len gi — do that o ban dau: nhan cua
        #    mot `python -c` ra nguyen mot doan import co ca xuong dong trong do.
        #
        # ⚠️ Va chinh doan comment nay tung lam VO tep: ban dau toi dan nguyen
        #    chuoi nhan xau vao day, trong do co mot dau nhay don, va no dong
        #    chuoi Python cua lenh dang ghi tep. Mo ta mot chuoi xau bang cach
        #    CHEP no vao la cach de nhat de lam hong thu dang sua.
        if x in ("-c", "-m"):
            ke = str(cl[i + 1]) if i + 1 < len(cl) else ""
            return f"{x} {ke.splitlines()[0][:24]}" if x == "-m" else "-c inline"
        if x.startswith("-"):
            continue
        return Path(x).name[:32] if ("/" in x or "\\" in x) else x[:32]
    return str(cl[1])[:32]


def mot_vong() -> dict:
    """Mot anh chup. Nhe: top-N tien trinh, doc bang `oneshot`."""
    try:
        import psutil
    except ImportError:
        return {"loi": "khong co psutil"}

    m = psutil.virtual_memory()
    ra = {"cpu": psutil.cpu_percent(interval=0.2),
          "ram_trong_gib": round(m.available / 2**30, 2),
          "so_tien_trinh": len(psutil.pids())}

    # SWAP: dau hieu SOM hon "RAM trong thap". Khi may bat dau swap manh thi no
    # da tren duong treo, con "RAM trong 2 GiB" thi co the chi la cache.
    try:
        sw = psutil.swap_memory()
        ra["swap_dung_gib"] = round(sw.used / 2**30, 2)
    except (psutil.Error, OSError):
        pass

    # DISK I/O tich luy. `--kham` lay HIEU giua hai mau de ra toc do — ghi so
    # tich luy thay vi toc do vi mot lan doc khong tinh duoc toc do, va hai mau
    # thi tinh duoc ca hai.
    #
    # 🔴 Kho nay da co mot su co I/O that: 282 tien trinh mo coi khoa **85 GB
    #    temp**. Mot hop den khong ghi I/O se khong thay lai duoc canh do.
    try:
        io = psutil.disk_io_counters()
        if io:
            ra["doc_mb"] = round(io.read_bytes / 2**20)
            ra["ghi_mb"] = round(io.write_bytes / 2**20)
    except (psutil.Error, OSError):
        pass

    # 🔴 `p.cpu_percent(None)` lan goi DAU cua MOI tien trinh tra 0.0 — no do
    #    chenh lech voi lan truoc, va lan dau khong co lan truoc. Voi bo loc
    #    `if c <= 0: continue` ben duoi, ket qua la `top: []` — mot may dang
    #    chay 100% trong y het mot may khong co tien trinh nao.
    #
    # ⇒ Dat moc cho MOI tien trinh, doi mot nhip ngan, roi moi doc that. Trong
    #   `chay()` moc da co tu vong truoc nen buoc nay gan nhu mien phi; o lan
    #   goi don le (vd `--trang-thai`) thi no la thu cuu ket qua khoi rong.
    if not _da_dat_moc:
        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)
            except (psutil.Error, OSError):
                pass
        time.sleep(0.3)
        globals()["_da_dat_moc"] = True

    nang = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            # ⛔ `System Idle Process` la tien trinh NHAN ROI cua Windows: CPU%
            #    cua no la tong so loi dang RANH, nen no luon dung dau bang va
            #    day moi thu that xuong. Mot bao cao kham nghiem mo dau bang
            #    "System Idle Process 1786%" la mot bao cao khong ai doc tiep.
            if p.pid in (0, 4):
                continue
            with p.oneshot():
                c = p.cpu_percent(None)
                if c <= 0:
                    continue
                # 🔴 `name` KHONG DU. Tren may nay co hang chuc `python.exe`:
                #    gate, worker pytest, bot dungvideo, bot gemini, phien
                #    Claude, sidecar giong noi. Mot hop den bao "python.exe an
                #    77%" thi sau mot lan reset ta van khong biet gi hon truoc.
                #
                # ⇒ Ghi them mot NHAN doc duoc tu `cmdline`, cat ngan. Do la
                #   khac biet giua mot ban ghi va mot ban ghi DUNG DUOC.
                nang.append({"pid": p.pid, "ten": (p.info["name"] or "")[:22],
                             "nhan": _nhan(p),
                             "cpu": round(c, 1),
                             "ram_mb": round(p.memory_info().rss / 2**20)})
        except (psutil.Error, OSError):
            continue
    nang.sort(key=lambda x: -x["cpu"])
    ra["top"] = nang[:TOP_N]

    # GPU: thua hon nhip chinh, va tinh theo THOI GIAN. Xem `GPU_CACH_S`.
    bay_gio = time.monotonic()
    cach = GPU_CACH_NONG_S if (bay_gio - _cang_luc) < NGUI_S else GPU_CACH_S
    if bay_gio - _gpu_lan_cuoi >= cach:
        globals()["_gpu_lan_cuoi"] = bay_gio
        # Bang PID cham GPU it doi — chi doc no khi da qua lau, hoac khi dang
        # cang (luc do mot mo hinh vua duoc nap la thong tin dat gia).
        day_du = (bay_gio - _gpu_app_luc >= GPU_APP_GHI_LAI_S
                  or (bay_gio - _cang_luc) < NGUI_S)
        g = _gpu(day_du_app=day_du)
        if g:
            # Gan ten cho tien trinh giu VRAM — cung ly do nhu `nhan` o tren.
            # ⛔ KHONG tra ten trong `nang` (top 10 theo CPU). Tien trinh giu
            #    GPU thuong dung im — mot mo hinh da nap xong VRAM an gan 0% CPU
            #    — nen tra trong top se ra ten rong cho dung thu ta can biet.
            for a in g.get("gpu_app", []):
                try:
                    pr = psutil.Process(a["pid"])
                    # ⚠️ Ca `ten` LAN `nhan`. Voi `python.exe` thi ten vo dung va
                    #    nhan la tat ca; voi `dwm.exe`, `chrome.exe`, `AnyDesk`
                    #    thi nguoc lai — chung khong co doi so nao dang ke va
                    #    `_nhan` tra chuoi rong. Do la 5/8 dong o lan thu dau.
                    a["ten"] = pr.name()
                    a["nhan"] = _nhan(pr)
                except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                    a["ten"] = a["nhan"] = ""
            # ⭐ Ghi ca danh sach CHI KHI tap PID doi. Tren may nay co 16 tien
            #    trinh cham GPU luc de ban (dwm, explorer, chrome, Claude... — o
            #    che do WDDM moi thu co cua so deu cham GPU), va chung khong doi
            #    hang gio. Ghi lai 16 dong do moi 30 giay la ~1 MB/ngay cho mot
            #    thong tin khong doi; ghi khi DOI thi vua giu duoc dung khoanh
            #    khac "co ke moi vao GPU" vua khong phinh tep.
            pid_moi = frozenset(a["pid"] for a in g.get("gpu_app", []))
            if "gpu_app" in g:
                if pid_moi == _gpu_app_pid:
                    g["gpu_app_nhu_cu"] = len(pid_moi)
                    del g["gpu_app"]
                else:
                    globals()["_gpu_app_pid"] = pid_moi
                    globals()["_gpu_app_luc"] = bay_gio
            ra.update(g)

    # Danh dau CANG de vong chay biet co doi nhip khong. Tinh o day, tren dung
    # so lieu vua do, thay vi bat vong chay do lai lan nua.
    if _dang_cang(ra):
        globals()["_cang_luc"] = time.monotonic()
        ra["cang"] = True
    return ra


def _dang_cang(mau: dict) -> bool:
    """May co dang o vung nguy hiem khong? Quyet dinh nhip lay mau.

    🔴 Ba dieu kien dau (CPU, RAM, swap) la thu `gpu_recorder.py` KHONG co, va
       do la ly do co che tang nhip cua no chua tung kich hoat dung luc: no chi
       nhin GPU. Ngay 03/09 may dut ba lan, ca ba lan GPU deu lanh.

    ⚠️ `or` chu khong `and`. Mot may co the chet vi CPU ma GPU van 8 W, hoac vi
       VRAM ma CPU van 3%. Bat ky duong nao cung dang tang do phan giai.
    """
    if mau.get("cpu", 0) >= CANG_CPU:
        return True
    if mau.get("ram_trong_gib", 999) <= CANG_RAM_GIB:
        return True
    if mau.get("swap_dung_gib", 0) >= CANG_SWAP_GIB:
        return True
    for c in mau.get("gpu", []):
        if c.get("nhiet_c", 0) >= CANG_NHIET_C:
            return True
        tran = c.get("dien_tran_w", 0)
        if tran and c.get("dien_w", 0) / tran >= CANG_DIEN_TI_LE:
            return True
        if c.get("vram_trong_mb", 1e9) <= CANG_VRAM_TRONG_MB:
            return True
        try:
            if int(c.get("co", "0x0"), 16) & SMI_CO_LO:
                return True
        except (ValueError, TypeError):
            pass
    return False


def _ghi(f, dong: dict) -> None:
    """Mot dong, xuong dia NGAY.

    ⛔ Ca `flush` LAN `fsync`. `flush` day khoi buffer cua Python; `fsync` day
       khoi buffer cua HE DIEU HANH. Mot lan mat dien khong ton trong cai nao,
       va thu con nam trong buffer la thu khong bao gio doc lai duoc — dung luc
       no dang gia nhat.
    """
    f.write(json.dumps(dong, ensure_ascii=False) + "\n")
    f.flush()
    try:
        os.fsync(f.fileno())
    except OSError:
        pass


def _ban_ghi_phien() -> dict:
    """Ban ghi mo dau moi lan hop den bat dau ghi vao mot tep.

    🔑 **`khoi_dong_luc` la truong quan trong nhat o day**, va la thu ca hai hop
       den truoc deu thieu. No cho phep `--kham` tra loi dut khoat mot cau hoi
       ma truoc do chi doan duoc:

         khoang dut + moc khoi dong DOI  => MAY da khoi dong lai
         khoang dut + moc khoi dong Y NGUYEN => chi HOP DEN dung, may van song

    🔴 Toi da doc sai dung cho nay: mot khoang im lang 79 giay trong nhat ky
       duoc ket luan la "may chet", trong khi telemetry cua mot cong cu khac cho
       thay may van ghi binh thuong suot khoang do — that ra chi la ban hop den
       cua toi bi khoi dong lai. Mot truong nay xoa han lop suy doan do.
    """
    ra = {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
          "loai": "phien", "pid": os.getpid()}
    try:
        import psutil
        ra["khoi_dong_luc"] = int(psutil.boot_time())
        ra["loi_vat_ly"] = psutil.cpu_count(logical=False)
        ra["loi_logic"] = psutil.cpu_count()
        ra["ram_tong_gib"] = round(psutil.virtual_memory().total / 2**30, 1)
    except (ImportError, OSError):
        pass
    try:
        r = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,memory.total,power.limit,power.max_limit",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8,
            creationflags=0x08000000 if os.name == "nt" else 0)
        card = []
        for d in r.stdout.strip().splitlines():
            c = [x.strip() for x in d.split(",")]
            if len(c) >= 5:
                card.append({"id": c[0], "ten": c[1], "vram_tong_mb": _so(c[2]),
                             "dien_tran_w": _so(c[3]), "dien_max_w": _so(c[4])})
        if card:
            ra["gpu_co_san"] = card
            # ⚠️ Tong tran dien cua CAC card la con so dang ghi mot lan: hai card
            #    180 W la 360 W chi rieng GPU. Khi doc lai mot lan may chet, biet
            #    tran nay giup doi chieu voi `dien_tong_w` cua tung mau.
            ra["dien_tran_tong_w"] = sum(x.get("dien_tran_w") or 0 for x in card)
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return ra


def chay() -> int:
    """Vong lap ghi. Chay nen, khong in gi tru khi hong."""
    try:
        import psutil
        psutil.cpu_percent(interval=None)          # dat moc cho lan do dau
        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)
            except psutil.Error:
                pass
    except ImportError:
        print("[hop den] khong co psutil - khong ghi duoc")
        return 1

    # ⛔ Mot ban dang chay roi thi DUNG, dung ghi chen.
    #
    # 🔴 Tu 03/09 co BA duong khoi dong hop den: `BAT.bat` (bam tay), muc
    #    Startup (tu chay khi dang nhap), va lenh tay cua toi. Hai ban cung ghi
    #    vao MOT tep `.jsonl` se cho ra hai day mau tron vao nhau — nhip nhin
    #    nhu 7 giay thay vi 15, va `_tim_cho_dut` doc nhip do la co so de goi
    #    mot khoang la "dut". Tuc chinh cai chong-trung nay bao ve phep do
    #    trung tam cua ca cong cu.
    #
    # ⚠️ Loc theo `cmdline[1]`, KHONG quet chuoi ca dong lenh — xem ghi chu dai
    #    o `trang_thai()`: quet chuoi bat nham thu NHAC DEN no, va loi do da
    #    xay ra muoi mot lan trong mot ngay.
    try:
        import psutil as _ps
        for _pr in _ps.process_iter(["pid", "cmdline"]):
            _cl = _pr.info["cmdline"] or []
            if (len(_cl) > 1 and str(_cl[1]).endswith("giam_sat_may.py")
                    and _pr.pid != os.getpid()):
                print(f"[hop den] da co ban dang chay (pid {_pr.pid}) - thoat.")
                return 0
    except Exception as exc:  # noqa: BLE001
        # Fail-OPEN co y: chinh phep kiem hong thi VAN ghi. Mot hop den khong
        # chay la thiet hai chac chan; hai ban cung ghi chi la nhieu.
        print(f"[hop den] khong kiem duoc ban trung ({type(exc).__name__}) - chay tiep")

    print(f"[hop den] ghi vao {THU_MUC}, nhip {NHIP_S:.0f}s "
          f"(xuong {NHIP_NONG_S:.0f}s khi cang). Ctrl-C de dung.")
    _don_tep_cu()
    ngay = None
    f = None
    try:
        while True:
            t = _tep_hom_nay()
            if t != ngay:
                if f:
                    f.close()
                f = open(t, "a", encoding="utf-8", newline="\n")
                ngay = t
                _don_tep_cu()
                _ghi(f, _ban_ghi_phien())
            mau = mot_vong()
            _ghi(f, {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     **mau})
            # ⭐ Nhip thich nghi. Xem `NHIP_NONG_S` va `_dang_cang`.
            nong = (time.monotonic() - _cang_luc) < NGUI_S
            time.sleep(NHIP_NONG_S if nong else NHIP_S)
    except KeyboardInterrupt:
        print("\n[hop den] dung.")
        return 0
    finally:
        if f:
            f.close()


# ══════════════════════════════════════════════════════════════════════════════
#  KHAM NGHIEM — phan quan trong nhat
# ══════════════════════════════════════════════════════════════════════════════

def _doc_het(ke_ca_phien: bool = False) -> list[dict]:
    """Doc het nhat ky.

    ⚠️ Mac dinh BO ban ghi `loai="phien"`. Chung khong co `cpu`/`ram_trong_gib`
       nen se lam lech moi thong ke, va — quan trong hon — chung nam DUNG sau
       moi khoang dut, nen de chung trong day mau se lam `_tim_cho_dut` do
       khoang tu ban ghi phien thay vi tu mau that.
    """
    ra = []
    for t in sorted(THU_MUC.glob("*.jsonl")):
        for l in t.read_text(encoding="utf-8", errors="replace").splitlines():
            l = l.strip()
            if not l:
                continue
            try:
                o = json.loads(l)
            except ValueError:
                continue          # dong ghi do dang luc may chet - bo qua
            if o.get("loai") == "phien" and not ke_ca_phien:
                continue
            ra.append(o)
    return ra


def _phien_theo_thoi_gian() -> list[dict]:
    """Cac ban ghi `phien`, de tra moc khoi dong quanh mot khoang dut."""
    return [d for d in _doc_het(ke_ca_phien=True) if d.get("loai") == "phien"]


def _giay(d: dict) -> float:
    return datetime.fromisoformat(d["t"]).timestamp()


def _tim_cho_dut(dong: list[dict]) -> list[int]:
    """Chi so cua nhung mau NGAY TRUOC mot khoang trong bat thuong."""
    # ⚠️ Bam theo nhip THUONG (15s), khong theo nhip dang chay. O che do cang
    #    nhip la 1s, va mot nguong 3s se goi moi lan may binh tinh tro lai la
    #    mot "cho dut" — tuc chinh co che tang do phan giai se sinh ra bao dong
    #    gia hang loat neu nguong di theo no.
    nguong = NHIP_S * NHIP_COI_LA_DUT
    return [i for i in range(len(dong) - 1)
            if _giay(dong[i + 1]) - _giay(dong[i]) > nguong]


def _phan_loai_dut(truoc: dict, sau: dict) -> str:
    """MAY khoi dong lai, hay chi HOP DEN dung? Tra loi bang moc khoi dong.

    🔴 Day la cau hoi toi da tra loi SAI mot lan hom nay: mot khoang im lang 79
       giay bi ket luan la "may chet", trong khi mot cong cu khac cho thay may
       van ghi binh thuong suot khoang do. Chenh lech giua hai ket luan nay la
       chenh lech giua "di tim nguyen nhan treo may" va "di tim vi sao mot tien
       trinh bi dung" — hai cuoc dieu tra hoan toan khac nhau.

    ⛔ Neu khong co ban ghi phien nao bao quanh, noi thang la KHONG BIET. Mot
       cau tra loi "co le" o day dat hon mot cau "khong ro".
    """
    ph = _phien_theo_thoi_gian()
    t0, t1 = _giay(truoc), _giay(sau)
    truoc_moc = [d.get("khoi_dong_luc") for d in ph if _giay(d) <= t0]
    sau_moc = [d.get("khoi_dong_luc") for d in ph if _giay(d) >= t1]
    a = next((x for x in reversed(truoc_moc) if x), None)
    b = next((x for x in sau_moc if x), None)
    if a is None or b is None:
        return "(khong biet may co khoi dong lai khong - thieu ban ghi phien)"
    if a != b:
        from datetime import datetime as _dt
        return (f"=> MAY DA KHOI DONG LAI (moc khoi dong doi, moc moi "
                f"{_dt.fromtimestamp(b):%H:%M:%S})")
    return "=> May KHONG khoi dong lai - chi hop den dung. Tim ly do o tien trinh."


def kham(so_lan: int = 1) -> int:
    if not THU_MUC.is_dir():
        print(f"[kham] chua co hop den nao o {THU_MUC}")
        print("       bat bang: python tools/giam_sat_may.py --chay")
        return 1
    dong = _doc_het()
    if len(dong) < 4:
        print(f"[kham] moi co {len(dong)} mau - chua du de kham")
        return 1

    cpu_all = [d["cpu"] for d in dong if "cpu" in d]
    ram_all = [d["ram_trong_gib"] for d in dong if "ram_trong_gib" in d]
    nen_cpu = statistics.median(cpu_all) if cpu_all else 0
    nen_ram = statistics.median(ram_all) if ram_all else 0
    print(f"[kham] {len(dong)} mau tu {dong[0]['t']} den {dong[-1]['t']}")
    print(f"       NEN cua may nay: CPU trung vi {nen_cpu:.0f}%, "
          f"RAM trong trung vi {nen_ram:.1f} GiB")

    dut = _tim_cho_dut(dong)
    if not dut:
        print("\n[kham] KHONG co cho dut nao - may chua tat/treo trong ky nay.")
        return 0

    for chi_so in dut[-max(1, so_lan):]:
        truoc, sau = dong[chi_so], dong[chi_so + 1]
        khoang = (_giay(sau) - _giay(truoc)) / 60
        print(f"\n{'='*66}")
        print(f"DUT luc {truoc['t']} -> chay lai {sau['t']}  (im lang {khoang:.0f} phut)")
        # 🔑 Phan quyet DUT KHOAT, khong phai suy doan. Xem `_ban_ghi_phien`.
        print(f"    {_phan_loai_dut(truoc, sau)}")
        print(f"{'='*66}")

        mau = dong[max(0, chi_so - 5):chi_so + 1]
        print(f"\n  6 mau cuoi truoc khi dut:")
        for d in mau:
            co = "  <-- BAT THUONG" if d.get("cpu", 0) > nen_cpu * 2 + 20 else ""
            print(f"    {d['t'][11:19]}  CPU {d.get('cpu', 0):5.1f}%  "
                  f"RAM trong {d.get('ram_trong_gib', 0):5.1f} GiB  "
                  f"{d.get('so_tien_trinh', 0):4d} tien trinh{co}")

        gom: dict[str, dict] = {}
        for d in mau:
            for p in d.get("top", []):
                k = p["ten"]
                g = gom.setdefault(k, {"cpu": 0.0, "ram_mb": 0, "lan": 0,
                                       "nhan": p.get("nhan", "")})
                g["cpu"] += p["cpu"]
                g["ram_mb"] = max(g["ram_mb"], p["ram_mb"])
                g["lan"] += 1
        if gom:
            print(f"\n  Ai chiem cho trong 6 mau do (tong CPU, RAM dinh):")
            for ten, g in sorted(gom.items(), key=lambda x: -x[1]["cpu"])[:8]:
                nhan = f"  [{g['nhan']}]" if g.get("nhan") else ""
                print(f"    {ten:20} CPU {g['cpu']:7.1f}  "
                      f"RAM {g['ram_mb']:6d} MB  ({g['lan']} mau){nhan}")

        # GPU: chi cac mau CO doc GPU (xem `GPU_CACH_S`).
        mau_gpu = [d for d in mau if d.get("gpu")]
        if mau_gpu:
            print(f"{chr(10)}  GPU o {len(mau_gpu)} mau co doc:")
            for d in mau_gpu[-3:]:
                cot = "  ".join(
                    f"#{c['id']} u{c.get('util', 0):3.0f}% "
                    f"{c.get('vram_mb', 0):6.0f}MB "
                    f"{c.get('nhiet_c', 0):3.0f}C "
                    f"{c.get('dien_w', 0):5.1f}/{c.get('dien_tran_w', 0):.0f}W "
                    f"{c.get('xung_mhz', 0):4.0f}MHz {c.get('pstate', '')}"
                    for c in d["gpu"])
                print(f"    {d['t'][11:19]}  tong {d.get('dien_tong_w', 0):5.1f}W  {cot}")
            for c in mau_gpu[-1]["gpu"]:
                # ⚠️ Nguong 90% VRAM, khong phai 100%: het VRAM khong bao loi
                #    sach — driver day sang bo nho he thong va may cham den muc
                #    trong nhu treo. Do la mot duong VE treo khac han duong het
                #    RAM, va no khong hien ra o bat cu con so RAM/CPU nao o tren.
                # ⚠️ `vram_trong_mb` phai CO THAT. Dong ghi truoc ban nay khong
                #    co truong do; mac dinh 0 se lam `tong == vram_mb` va moi
                #    dong cu deu bao "VRAM gan day". Mot hop den bao dong sai
                #    tren chinh du lieu lich su cua no la mot hop den khong ai
                #    tin nua — va lich su la thu duy nhat no co.
                if "vram_trong_mb" not in c:
                    continue
                tong = c.get("vram_mb", 0) + c["vram_trong_mb"]
                if tong and c.get("vram_mb", 0) > tong * 0.9:
                    print(f"    [!] GPU #{c['id']} VRAM gan day "
                          f"({c['vram_mb']:.0f}/{tong:.0f} MB)")
                if c.get("nhiet_c", 0) >= CANG_NHIET_C:
                    print(f"    [!] GPU #{c['id']} NONG {c['nhiet_c']:.0f}C")
            # 🔑 Co chan xung: thu duy nhat phan biet ba kieu chet. Xem `SMI_CO`.
            for d in mau_gpu:
                for c in d.get("gpu", []):
                    try:
                        v = int(c.get("co", "0x0"), 16)
                    except (ValueError, TypeError):
                        continue
                    # ⛔ Loc bang `SMI_CO_LO`, khong in moi co. Bit `nhan roi`
                    #    bat gan nhu lien tuc tren may de ban; in no ra la tao
                    #    mot canh bao luon bat, tuc mot canh bao vo nghia.
                    if v & SMI_CO_LO:
                        ten = ", ".join(_giai_ma_co(c["co"]))
                        print(f"    [!!] {d['t'][11:19]} GPU #{c['id']} BI CHAN "
                              f"XUNG: {ten}")
            giu = None
            for d in reversed(mau_gpu):
                if d.get("gpu_app"):
                    giu = d["gpu_app"]
                    break
            if giu:
                dem: dict = {}
                for a in giu:
                    k = a.get("nhan") or a.get("ten") or str(a["pid"])
                    dem[k] = dem.get(k, 0) + 1
                print(f"    {len(giu)} tien trinh cham GPU: "
                      + ", ".join(f"{k}x{v}" if v > 1 else k
                                  for k, v in list(dem.items())[:10]))

        cuoi = mau[-1]
        print(f"\n  So voi nen:")
        d_cpu = cuoi.get("cpu", 0) - nen_cpu
        d_ram = cuoi.get("ram_trong_gib", 0) - nen_ram
        print(f"    CPU      {cuoi.get('cpu', 0):.0f}%  "
              f"({'+' if d_cpu >= 0 else ''}{d_cpu:.0f} diem so voi nen)")
        print(f"    RAM trong {cuoi.get('ram_trong_gib', 0):.1f} GiB  "
              f"({'+' if d_ram >= 0 else ''}{d_ram:.1f} GiB)")
        if cuoi.get("ram_trong_gib", 99) < 3:
            print("    [!] RAM trong RAT THAP - het bo nho la nguyen nhan hang dau")
        if cuoi.get("cpu", 0) > 90:
            print("    [!] CPU bao hoa o mau cuoi")
        if cuoi.get("swap_dung_gib", 0) > 2:
            print(f"    [!] SWAP {cuoi['swap_dung_gib']:.1f} GiB - may dang trao "
                  f"bo nho ra dia, dau hieu SOM cua mot lan treo")
        if len(mau) >= 2 and "ghi_mb" in mau[-1] and "ghi_mb" in mau[0]:
            dt = max(1.0, _giay(mau[-1]) - _giay(mau[0]))
            toc_ghi = (mau[-1]["ghi_mb"] - mau[0]["ghi_mb"]) / dt
            toc_doc = (mau[-1].get("doc_mb", 0) - mau[0].get("doc_mb", 0)) / dt
            print(f"    Dia: doc {toc_doc:.0f} MB/s, ghi {toc_ghi:.0f} MB/s "
                  f"(trung binh {dt:.0f}s cuoi)")

    print("\n[kham] Day la SO LIEU, khong phai ket luan. Doi chieu voi:")
    print("       - nhat ky lenh:  python tools/nhat_ky_chay.py --xem 3")
    print("       - log bot:       D:/FULL AUTO VIDEO/*/logs/")
    print("       - phien khac:    ListAgents")
    return 0


def trang_thai() -> int:
    try:
        import psutil
    except ImportError:
        print("khong co psutil")
        return 1
    # ⛔ Loc theo `cmdline[1]`, KHONG quet chuoi trong ca dong lenh.
    #
    # 🔴 Lan thu MUOI MOT cua cung mot loi trong ngay 03/09: ban dau dong nay
    #    la `any("giam_sat_may" in str(c) for c in cmdline)`, va no bat ba
    #    **shell wrapper** cua chinh cau lenh vua go — cmdline cua chung chua
    #    chuoi do vi no la cau lenh. Bao "DANG CHAY pid [3 cai]" cho mot thu
    #    khong chay.
    #
    #    Cung lop loi da bat "7 tien trinh gate.py" (that ra 1) va "5 tien trinh
    #    test_nhanh" (that ra 1). **Quet chuoi bat nham thu NHAC DEN no.**
    dang = []
    for pr in psutil.process_iter(["pid", "cmdline"]):
        cl = pr.info["cmdline"] or []
        if len(cl) > 1 and str(cl[1]).endswith("giam_sat_may.py")                 and pr.pid != os.getpid():
            dang.append(pr.pid)
    print(f"hop den: {'DANG CHAY pid ' + str(dang) if dang else 'KHONG chay'}")
    if THU_MUC.is_dir():
        tep = sorted(THU_MUC.glob("*.jsonl"))
        print(f"tep: {len(tep)} ngay, moi nhat: {tep[-1].name if tep else '(khong)'}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Hop den cua may.")
    p.add_argument("--chay", action="store_true", help="vong lap ghi (chay nen)")
    p.add_argument("--kham", nargs="?", type=int, const=1, default=None,
                   help="kham nghiem N lan dut gan nhat")
    p.add_argument("--trang-thai", action="store_true")
    a = p.parse_args()
    if a.chay:
        return chay()
    if a.kham is not None:
        return kham(a.kham)
    if a.trang_thai:
        return trang_thai()
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
