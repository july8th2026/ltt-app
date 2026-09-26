"""bench_upscale.py — bo do hieu nang cho apps/upscalevideo (V2 CORRECTION).

    python tools\\bench_upscale.py --dry-run
    python tools\\bench_upscale.py --dry-run --preset fast --target 1080 --feature normal
    python tools\\bench_upscale.py --mode matrix --preset fast --target 1080 --feature normal --video v3 --repeat 3
    python tools\\bench_upscale.py --mode warmup --preset fast --repeat 5
    python tools\\bench_upscale.py --mode tile-sweep --preset fast --video v3 --max-frames 200 --repeat 3
    python tools\\bench_upscale.py --mode thread-sweep --preset quality --tile 384 --video v3 --max-frames 200
    python tools\\bench_upscale.py --report <scratch>\\results.jsonl > 08_ket_qua.md

🔴 HIEN TRANG LUC VIET (26/09/2026): GPU DUY NHAT cua may (RTX 5060 Ti) dang
   upscale MOT VIDEO KHACH THAT qua `D:\\BOT GEMINI` (~92-98% util do khi viet
   tep nay). File nay CHI duoc DUNG, khong duoc CHAY that cho den khi GPU ranh.
   `--dry-run` khong dung GPU: no doc metadata (ffprobe/nvidia-smi/hash/git),
   IN ke hoach + lenh + provenance, KHONG goi `engine.run_upscale`, KHONG goi
   `vulkan_device.vulkan_index_for` (ham do CHINH no chay mot luot
   realesrgan-ncnn-vulkan that tren anh 16x16 de liet ke thiet bi — xem
   `vulkan_device.py:100-109` — nen no CHỈ duoc goi tren duong chay THAT).

## Nguon chan ly duoc TAI SU DUNG, khong viet lai

Bo do nay KHONG tu dung lai pipeline. No goi thang cac ham that trong
`apps/upscalevideo/{ff,engine,autotune,jobs}.py`:
  - `ff.probe_video` / `ff.stabilize_video` / `ff.extract_frames` /
    `ff.encode_full` / `ff.concat_and_mux` — dung nguyen ham san xuat.
  - `autotune.pick` — chon tile/threads that (tru mode sweep, no CHU DINH
    tile/threads de do rieng tung o).
  - `engine.run_upscale` — dung nguyen, ke ca duong fallback OOM va bien moi
    truong `LTT_UPSCALE_WARMUP`.
  - `jobs._resolve_encoder`, `jobs._output_fps`, `jobs._upscale_batched`,
    `jobs._BATCH_SIZE`, `jobs._PREVIEW_SECONDS` — cac ham/hang so noi bo cua
    `jobs.handle()` duoc goi THANG (khong qua DB/credit/storage/checkpoint,
    vi `_upscale_batched` chi ghi checkpoint khi `ctx is not None` — bo do
    nay LUON truyen `ctx=None`).

Bo do KHONG di qua `job_runner`/`gpu_lease`/`credit` (khong co job that, khong
thu tien, khong xin lease DB) — day la mot cong cu DO DOC LAP, khong phai mot
job gia. Vi vay no PHAI tu kiem GPU ranh (§ fairness guard duoi) thay vi dua
vao admission control cua nen tang.

## Ma tran

`preset {fast,quality} x target {1080,1440,2160} x feature {normal,stabilize,
smooth_motion,preview} x video {v1..v4}`. 4 video test that (chi doc, xem
`docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md`) deu ~576p ngang CFR — muc
`target_height` la thu DUY NHAT ma tran co the doi (khong co nguon 1080+,
khong co portrait/VFR/mat nguoi/nhieu nang — nhung o do la `KHONG CO MAU`,
xem `MEDIA_KHONG_CO_MAU` duoi).

`--mode warmup`: PHEP DO CHOT — warmup (`engine._warmup_model`) spawn mot
tien trinh `subprocess.run` CHO THOAT HAN truoc khi job that spawn mot
`Popen` MOI (`engine.py:87-89` vs `:127-129`) nen no KHONG the giu model
trong VRAM; loi ich (neu co) chi co the la cache tep OS / shader cache
driver. Mode nay chay CA HAI trang thai `LTT_UPSCALE_WARMUP=1|0` cho cung
mot preset/video, do time-to-first-frame + tong thoi gian, nhieu lan lap.

`--mode tile-sweep` / `--mode thread-sweep`: do RIENG tang upscale (khong
chay lai probe/tach khung/encode moi lan) tren MOT bo khung da tach san —
tile Fast {200,256,384}, Quality {256,320,384,448,512}; threads
{"1:2:2","2:2:2","4:4:4"} (dung `TuneResult` tu dung, khong qua
`autotune.pick`, de co dinh dung gia tri dang do).

## Giao thuc lenh nang (hop dong may dung chung, doc them
`docs/QUY_TAC_CHAY_LENH_NANG.md`)

Tep nay TU NO KHONG giu khoa `cpu_nhieu` — no la mot cong cu doc lap, khong
phai `gate.py`. MOI lenh CHAY THAT (khong phai `--dry-run`, khong phai
`--report`) PHAI boc qua `chay_nang.py`:

    python "C:\\Users\\Thang Tuong\\.claude\\ltt\\chay_nang.py" --phien bench-upscale -- ^
      python tools\\bench_upscale.py --mode matrix --preset fast --target 1080 ^
      --feature normal --video v3 --repeat 3

⚠️ `chay_nang.py` dung `argparse.REMAINDER` roi LOC BO moi token `"--"` DON LE
   khoi lenh con (`lenh = [x for x in a.lenh if x != "--"]` — chay_nang.py:24).
   Dùng DUY NHAT MOT `--` ngay sau `--phien <ten>` de tach; dung dat `"--"` o
   bat ky vi tri nao khac trong lenh con (vd lam gia tri cua mot co) vi no se
   BIEN MAT khoi lenh thuc thi ma khong bao loi.

⭐ Khoa CHI boc DUNG lenh o tren (mot lenh TINH). Doc `results.jsonl`, phan
   tich, sua ma, chay `--report`, `git add`/`commit`, hoi chu du an — tat ca
   lam NGOAI loi goi do, sau khi tien trinh con thoat (`chay_nang.py` tu nha
   khoa khi subprocess ket thuc — no khong giu ho ban trong luc doc ket qua).
   ⛔ Dung goi `chay_nang.py` roi NGOI CHO xong moi lam viec khac trong CUNG
   mot lenh giu khoa keo dai — vi du "chay matrix xong doc log xong chay tiep
   sweep" phai la HAI loi goi `chay_nang.py` rieng, khong phai mot script bao
   ca ba trong mot tien trinh con duy nhat neu buoc giua co doc/ghi khong-tinh.

Truoc lenh nang: `python tools\\cua_so_yen.py trang-thai` + `python
tools\\tai_may.py` (`chay_nang.py` tu lam buoc nay). Rieng CUA GPU (khac CPU):
bo do nay tu kiem `nvidia-smi` (§ fairness guard) vi khong co khoa GPU dung
chung nao trong kho nay ngoai `gpu_lease` (can DB/job that, qua nang cho mot
cong cu do doc lap).

## Dau ra

Moi lan chay ghi MOT dong JSON vao `<scratch>/results.jsonl` (JSONL, khong
ghi vao cay kho). `--report <jsonl>` doc lai va in bang Markdown — dan thang
vao `docs/UPSCALE_V2_CORRECTION/08_BENCHMARK_RESULTS.md`.

⛔ KHONG bao gio doan/uoc luong mot con so hieu nang. Chua do that thi ghi
   `"CHUA_DO"` — xem huong dan trong `docs/UPSCALE_V2_CORRECTION/06_*.md`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import psutil
except ImportError:  # pragma: no cover — moi may deu co psutil (dung khap tools/)
    psutil = None

# Console Windows mac dinh cp1252 khong ma hoa duoc ⛔/⚠️/⭐ trong docstring/--help
# (argparse tu in thang, khong qua `_in()` duoi day) — quy uoc chung cua tools/*.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

from apps.upscalevideo import autotune, engine, ff  # noqa: E402
from apps.upscalevideo import jobs as up_jobs  # noqa: E402
from apps.upscalevideo.schemas import PRESET_MODEL, Codec, Preset, TuneResult  # noqa: E402

# ── Hang so ma tran ─────────────────────────────────────────────────────────
PRESETS = ["fast", "quality"]
TARGETS = [1080, 1440, 2160]
FEATURES = ["normal", "stabilize", "smooth_motion", "preview"]
WARMUP_STATES = ["on", "off"]
TILE_SWEEP = {"fast": [200, 256, 384], "quality": [256, 320, 384, 448, 512]}
THREAD_SWEEP = ["1:2:2", "2:2:2", "4:4:4"]

#: 4 video that duy nhat, chi doc — xem docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md.
#: ⛔ KHONG sua/xoa/di chuyen; KHONG ghi output vao thu muc nay.
TEST_VIDEO_DIR = Path(r"C:\Users\Thang Tuong\Desktop\TEST VIDEO")
VIDEO_TEN_TEP = {
    "v1": "廉价的牛肠经过复杂的加工后竟然成了韩国人补充能量的救赎 "
          "#烤牛肠 #地方特色美食 #舌尖上的美食 #美食.mp4",
    "v2": "暴雨天野外露营搭建帐篷生活度过雨天享受户外露营 "
          "#暴雨露营 #帐篷露营 #户外露营.mp4",
    "v3": "深度解析丨跳伞慢了该怎么打教你用细节操作来化解危机 "
          "#和平精英夏日航海 #和平精英夏日探险.mp4",
    "v4": "真人气枪游戏红蓝双方对决.mp4",
}

#: Muc ma tran truyen thong (§20 cua brief) KHONG co mau trong bo 4 video hien
#: co — ghi ro ly do de khong ai nham "vang mat" thanh "da qua".
MEDIA_KHONG_CO_MAU = [
    ("portrait (doc)", "ca 4 video test deu NGANG (16:9/3:2/209:144); khong co nguon doc"),
    ("nguon 1080p/1440p/2160p", "ca 4 video test deu ~576p; chi do duoc o phia TARGET, khong do duoc o phia SOURCE"),
    ("VFR (variable frame rate)", "ca 4 video test deu CFR (r_frame_rate == avg_frame_rate)"),
    ("clip mat nguoi rieng (face-heavy)", "khong co clip nao trong bo 4 tap trung mat nguoi lam noi dung chinh"),
    ("clip nhieu hat/nen toi rieng (noisy)", "khong co clip quay dem/nhieu ISO cao rieng trong bo 4"),
]

_BUSY_THRESHOLD_MAC_DINH = 15
_WAIT_TIMEOUT_MAC_DINH_S = 1800


# ── Vietnamese-safe print (console Windows cp1252 khong ma hoa duoc ⛔/⭐) ──
def _in(*phan: object) -> None:
    tin = " ".join(str(x) for x in phan)
    try:
        print(tin)
    except UnicodeEncodeError:
        ma = getattr(sys.stdout, "encoding", None) or "ascii"
        print(tin.encode(ma, "replace").decode(ma, "replace"))


# ── Ho tro doc metadata (CHI DOC — an toan ke ca khi GPU dang ban) ─────────
def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for khoi in iter(lambda: f.read(1024 * 1024), b""):
            h.update(khoi)
    return h.hexdigest()


def _chay_nhanh(cmd: list[str], timeout: int = 15) -> str:
    """Chay mot lenh METADATA-ONLY (ffprobe/nvidia-smi/git/ffmpeg -version).

    ⛔ KHONG dung ham nay cho engine hay ffmpeg encode/decode video that —
       chi cho cac lenh tuc thi, chi doc.
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           errors="replace", timeout=timeout)
        return (r.stdout or "").strip() or (r.stderr or "").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return f"(khong chay duoc: {type(exc).__name__}: {exc})"


def _gpu_snapshot() -> dict:
    """Nhiet/util/VRAM + tien trinh compute HIEN TAI — CHI DOC, tuc thi."""
    ra: dict = {}
    out = _chay_nhanh(["nvidia-smi",
                       "--query-gpu=name,driver_version,utilization.gpu,"
                       "memory.used,memory.free,memory.total,temperature.gpu",
                       "--format=csv,noheader,nounits"])
    try:
        dong = out.splitlines()[0]
        ten, driver, util, dung, trong, tong, nhiet = [p.strip() for p in dong.split(",")]
        ra = {"gpu_name": ten, "driver_version": driver, "gpu_util_pct": int(util),
              "vram_used_mb": int(dung), "vram_free_mb": int(trong),
              "vram_total_mb": int(tong), "gpu_temp_c": int(nhiet)}
    except (IndexError, ValueError):
        ra = {"loi": f"khong doc duoc nvidia-smi: {out[:200]!r}"}
    ct = _chay_nhanh(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                      "--format=csv,noheader,nounits"])
    ra["tien_trinh_compute"] = [d.strip() for d in ct.splitlines() if d.strip()]
    return ra


def _git_head() -> str:
    return _chay_nhanh(["git", "-C", str(GOC), "rev-parse", "HEAD"], timeout=10)


def _ffmpeg_version() -> str:
    out = _chay_nhanh([ff._ff(), "-version"], timeout=10)
    return out.splitlines()[0] if out else "(khong doc duoc)"


def _engine_dir_thuc(override: str | None) -> Path:
    """Thu muc vendor/engine se dung de doc provenance / chay that.

    `apps/upscalevideo/vendor/` bi gitignore (xem `.gitignore`) nen mot
    worktree MOI (nhu worktree viet tep nay) khong co no. Chay THAT phai
    dung o mot checkout co san vendor (vd `C:\\LTTPlatform\\app`) hoac
    truyen `--engine-dir`. `--dry-run` van doc duoc provenance qua fallback
    duoi de hien thi gia tri THAT ma khong can worktree co vendor.
    """
    if override:
        return Path(override)
    if engine.check_engine():
        return engine.engine_dir()
    du_phong = Path(r"C:\LTTPlatform\app\apps\upscalevideo\vendor\engine")
    return du_phong


def thu_thap_provenance(engine_dir_override: str | None = None) -> dict:
    thu_muc = _engine_dir_thuc(engine_dir_override)
    exe = thu_muc / "realesrgan-ncnn-vulkan.exe"
    models_dir = thu_muc / "models"
    ra = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": _git_head(),
        "engine_dir": str(thu_muc),
        "engine_dir_la_that_trong_worktree_nay": engine.check_engine(),
        "engine_sha256": _sha256(exe),
        "ffmpeg_version": _ffmpeg_version(),
        "ffmpeg_bin": ff._ff(),
    }
    for preset, model in PRESET_MODEL.items():
        ra[f"model_{preset.value}_ten"] = model
        ra[f"model_{preset.value}_param_sha256"] = _sha256(models_dir / f"{model}.param")
        ra[f"model_{preset.value}_bin_sha256"] = _sha256(models_dir / f"{model}.bin")
    ra["background_load_at_provenance"] = _gpu_snapshot()
    return ra


def _video_dang_ky() -> list[dict]:
    """ffprobe tuc thi ca 4 video (chi doc) — tra metadata that, khong bia."""
    ra = []
    for vid, ten_tep in VIDEO_TEN_TEP.items():
        duong = TEST_VIDEO_DIR / ten_tep
        muc = {"id": vid, "ten_tep": ten_tep, "duong": str(duong), "ton_tai": duong.is_file()}
        if muc["ton_tai"]:
            try:
                info = ff.probe_video(str(duong))
                muc.update({"w": info["w"], "h": info["h"], "fps_str": info["fps_str"],
                           "duration_s": round(info["duration"], 1), "nb_frames": info["nb_frames"],
                           "has_audio": info["has_audio"], "is_vfr": info["is_vfr"]})
            except (RuntimeError, OSError) as exc:
                muc["loi_probe"] = str(exc)
        ra.append(muc)
    return ra


# ── Fairness guard — GPU ranh truoc MOI luot do ─────────────────────────────
#: Ten tien trinh coi la "dang tranh GPU That" — desktop compositor (dwm.exe),
#: shell, AnyDesk, v.v. LUON xuat hien trong `--query-compute-apps` tren may
#: nay (WDDM dua ca compositor vao danh sach compute context) nen KHONG the
#: dung "danh sach rong" lam dieu kien — se KHONG BAO GIO ranh. Chi coi la
#: "nguoi la" khi ten khop mot workload upscale/encode that.
_TIEN_TRINH_LA_TRANH_GPU = ("realesrgan", "ffmpeg")


def _may_ranh(nguong_pct: int) -> tuple[bool, dict]:
    snap = _gpu_snapshot()
    if "loi" in snap:
        return False, snap
    la = [p for p in snap["tien_trinh_compute"]
         if any(ten in p.lower() for ten in _TIEN_TRINH_LA_TRANH_GPU)]
    snap["tien_trinh_tranh_gpu"] = la
    ranh = snap["gpu_util_pct"] < nguong_pct and not la
    return ranh, snap


def cho_gpu_ranh(nguong_pct: int, on_busy: str, wait_timeout_s: int) -> dict:
    """Kiem GPU ranh; `wait` thi cho co gioi han, `abort` thi bao loi ngay.

    Tra ve snapshot tai (background load) DU khi ranh hay ban — ket qua PHAI
    ghi lai tai nen luc bat dau du co do hay khong (yeu cau §7 cua brief).
    """
    han = time.monotonic() + wait_timeout_s
    lan = 0
    while True:
        ranh, snap = _may_ranh(nguong_pct)
        if ranh:
            return snap
        lan += 1
        if on_busy == "abort":
            raise RuntimeError(
                f"GPU dang ban (util={snap.get('gpu_util_pct')}%, "
                f"tien_trinh={snap.get('tien_trinh_compute')}) — bo qua luot do "
                f"(dung --on-busy wait de cho, hoac chay khi GPU ranh).")
        if time.monotonic() > han:
            raise RuntimeError(
                f"GPU van ban sau {wait_timeout_s}s cho — DUNG, khong do tren GPU tranh chap.")
        if lan % 4 == 1:
            _in(f"[bench_upscale] GPU ban ({snap.get('gpu_util_pct')}% util) — cho...")
        time.sleep(15)


# ── Lay mau tai nguyen trong luc mot luot chay ──────────────────────────────
class LayMauTaiNguyen:
    """Lay mau GPU (nvidia-smi) + CPU/RAM cay tien trinh cua tien trinh nay.

    ⚠️ `giay_cpu` la GAN DUNG: chi doc duoc `cpu_times()` trong khi tien trinh
       con SONG; sai so toi da ~mot chu ky lay mau (mac dinh 0,3s), khong dang
       ke voi cac lenh dai vai giay-vai chuc phut o day. Bao ca `giay_cpu`
       (phan quyet) LAN `dong_ho_tuong` (dieu kien do) — hai cot tra loi hai
       cau khac nhau (`docs/QUY_TAC_CHAY_LENH_NANG.md` §2b).
    """

    def __init__(self, pid_goc: int, chu_ky: float = 0.3):
        self.pid_goc = pid_goc
        self.chu_ky = chu_ky
        self.mau_gpu_util: list[int] = []
        self.mau_gpu_vram: list[int] = []
        self.mau_gpu_temp: list[int] = []
        self.mau_ram_mb: list[float] = []
        self.giay_cpu_cuoi = 0.0
        self.tien_trinh_la_ngoai: list[str] = []
        self._dung = threading.Event()
        self._t: threading.Thread | None = None

    def _vong(self) -> None:
        goc = None
        if psutil is not None:
            try:
                goc = psutil.Process(self.pid_goc)
            except psutil.Error:
                goc = None
        while not self._dung.wait(self.chu_ky):
            out = _chay_nhanh(["nvidia-smi",
                               "--query-gpu=utilization.gpu,memory.used,temperature.gpu",
                               "--format=csv,noheader,nounits"], timeout=5)
            try:
                u, v, t = [p.strip() for p in out.splitlines()[0].split(",")]
                self.mau_gpu_util.append(int(u))
                self.mau_gpu_vram.append(int(v))
                self.mau_gpu_temp.append(int(t))
            except (IndexError, ValueError):
                pass
            ct = _chay_nhanh(["nvidia-smi", "--query-compute-apps=pid,process_name",
                              "--format=csv,noheader,nounits"], timeout=5)
            for dong in ct.splitlines():
                if dong.strip() and dong.strip() not in self.tien_trinh_la_ngoai:
                    self.tien_trinh_la_ngoai.append(dong.strip())
            if goc is None:
                continue
            try:
                cay = [goc] + goc.children(recursive=True)
            except psutil.Error:
                continue
            giay = 0.0
            ram = 0.0
            for p in cay:
                try:
                    ctm = p.cpu_times()
                    giay += ctm.user + ctm.system
                    ram += p.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            self.giay_cpu_cuoi = max(self.giay_cpu_cuoi, giay)
            self.mau_ram_mb.append(ram / (1024 * 1024))

    def __enter__(self) -> "LayMauTaiNguyen":
        self._t = threading.Thread(target=self._vong, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *_a: object) -> None:
        self._dung.set()
        if self._t:
            self._t.join(timeout=3)

    def tom_tat(self) -> dict:
        def tk(xs: list) -> dict | None:
            return {"min": min(xs), "max": max(xs), "avg": round(sum(xs) / len(xs), 1)} if xs else None
        return {
            "gpu_util_pct": tk(self.mau_gpu_util),
            "gpu_vram_mb": tk(self.mau_gpu_vram),
            "gpu_temp_c": tk(self.mau_gpu_temp),
            "ram_mb_process_tree": tk(self.mau_ram_mb),
            "cpu_giay_process_tree": round(self.giay_cpu_cuoi, 2),
            "so_mau": len(self.mau_gpu_util),
            "tien_trinh_ngoai_thay_trong_luc_chay": self.tien_trinh_la_ngoai,
        }


# ── Do thoi gian theo pha (stage boundaries cua chinh app) ─────────────────
class DoPha:
    def __init__(self) -> None:
        self.pha: dict[str, float] = {}
        self._t0: dict[str, float] = {}

    def bat_dau(self, ten: str) -> None:
        self._t0[ten] = time.perf_counter()

    def ket_thuc(self, ten: str) -> None:
        if ten in self._t0:
            self.pha[ten] = round(time.perf_counter() - self._t0.pop(ten), 3)

    def __call__(self, ten: str):
        return _KhoiPha(self, ten)


class _KhoiPha:
    def __init__(self, chu: DoPha, ten: str) -> None:
        self.chu, self.ten = chu, ten

    def __enter__(self) -> None:
        self.chu.bat_dau(self.ten)

    def __exit__(self, *_a: object) -> None:
        self.chu.ket_thuc(self.ten)


# ── Lenh "demo" — CHI de hien thi trong --dry-run, KHONG bao gio duoc chay ──
def lenh_engine_demo(exe: Path, in_dir: str, out_dir: str, tune: TuneResult, gpu_index) -> list[str]:
    """Mo phong dung THU TU tham so cua `engine.run_upscale` (engine.py:119-124).

    ⚠️ Chi de IN cho nguoi doc — luot chay THAT goi thang `engine.run_upscale`,
       khong goi list nay.
    """
    args = [str(exe), "-i", in_dir, "-o", out_dir, "-n", tune.model, "-s", "4",
            "-m", "models", "-f", "png", "-t", str(tune.tile), "-j", tune.threads]
    if gpu_index is not None:
        args += ["-g", str(gpu_index)]
    return args


def lenh_extract_demo(ff_exe: str, src: str, out_dir: str, cfr_fps, interpolate_fps) -> list[str]:
    """Mo phong `ff.extract_frames` (ff.py:131-146) — chi de IN, khong chay."""
    cmd = [ff_exe, "-y", "-i", src]
    bo_loc = []
    if cfr_fps:
        bo_loc.append(f"fps={cfr_fps}")
    if interpolate_fps:
        bo_loc.append("minterpolate=fps=" + str(interpolate_fps) +
                      ":mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
    if bo_loc:
        cmd += ["-vf", ",".join(bo_loc)]
    cmd += [os.path.join(out_dir, "f%05d.png")]
    return cmd


# ── Ghi JSONL ────────────────────────────────────────────────────────────────
def ghi_ban_ghi(duong_jsonl: Path, ban_ghi: dict) -> None:
    duong_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with open(duong_jsonl, "a", encoding="utf-8") as f:
        f.write(json.dumps(ban_ghi, ensure_ascii=False) + "\n")


# ── Pipeline THAT — tai su dung ham cua chinh app, khong viet lai ──────────
def _cfr_cho(info: dict, preserve_fps: bool, smooth_motion: bool):
    """Sao y logic `jobs.handle` dong 338-340 — bien cuc bo, khong phai ham
    xuat cua `jobs.py` nen khong import duoc, chep nguyen bieu thuc."""
    if smooth_motion:
        return None
    if preserve_fps and info.get("is_vfr"):
        return info["fps_str"]
    return "30" if not preserve_fps else None


def chay_mot_luot_pipeline(video: dict, preset: str, target_h: int, feature: str,
                           warmup: str, scratch_dir: Path, gpu_index, env,
                           codec: str = "h264") -> dict:
    """Mot lan chay HET pipeline (khong DB/storage/credit/checkpoint).

    Tai su dung `ff.*`, `autotune.pick`, `engine.run_upscale`,
    `up_jobs._resolve_encoder/_output_fps/_upscale_batched/_BATCH_SIZE/
    _PREVIEW_SECONDS` — dung NGUYEN duong san xuat, chi thay `ctx=None` (bo
    checkpoint/progress DB) va "upload R2" bang copy-vao-scratch (khong co
    thong tin dang nhap storage trong mot cong cu do doc lap).
    """
    do = DoPha()
    t_bat_dau = time.perf_counter()
    tmp = Path(tempfile.mkdtemp(prefix="bo_", dir=str(scratch_dir)))
    trang_thai, loi = "done", None
    n_frames = ow = oh = 0
    tgian_khung_dau = None
    eff_dur = None
    tune = None
    try:
        preview = feature == "preview"
        stabilize = feature == "stabilize"
        smooth_motion = feature == "smooth_motion"

        with do("source_copy"):
            tmp_video = str(tmp / ("src" + Path(video["duong"]).suffix))
            shutil.copyfile(video["duong"], tmp_video)

        with do("probe"):
            info = ff.probe_video(tmp_video, env=env)

        eff_dur = min(info["duration"], up_jobs._PREVIEW_SECONDS) if preview else info["duration"]

        working_video = tmp_video
        if stabilize:
            with do("stabilize"):
                working_video = str(tmp / "stabilized.mp4")
                ff.stabilize_video(tmp_video, working_video,
                                   max_seconds=up_jobs._PREVIEW_SECONDS if preview else None, env=env)

        output_fps = up_jobs._output_fps(info["fps_str"], True, smooth_motion)
        cfr = _cfr_cho(info, True, smooth_motion)
        max_sec = up_jobs._PREVIEW_SECONDS if preview else None
        in_dir = str(tmp / "in")
        # ⚠️ "interpolation" (minterpolate) KHONG phai mot tien trinh rieng —
        #    no la mot bo loc noi vao CUNG lenh ffmpeg tach khung (ff.py:137-
        #    143, ISSUE K). Khong tach duoc thoi gian rieng cho no; pha
        #    "frame_extraction" duoi day GOM CA no khi smooth_motion=True.
        with do("frame_extraction"):
            n_frames = ff.extract_frames(working_video, in_dir, cfr_fps=cfr,
                                         interpolate_fps=output_fps if smooth_motion else None,
                                         max_seconds=max_sec, env=env)

        tune = autotune.pick(Preset(preset), info["w"], info["h"])
        os.environ["LTT_UPSCALE_WARMUP"] = "1" if warmup == "on" else "0"
        encoder = up_jobs._resolve_encoder(Codec(codec))

        moc = {"t0": time.perf_counter(), "khung_dau": None}

        def on_prog(done: int, _moc=moc) -> None:
            if done >= 1 and _moc["khung_dau"] is None:
                _moc["khung_dau"] = time.perf_counter() - _moc["t0"]

        up_dir = str(tmp / "up")
        out_local = str(tmp / "out.mp4")
        if n_frames <= up_jobs._BATCH_SIZE:
            with do("upscale"):
                trang = engine.run_upscale(in_dir, up_dir, tune, n_frames, progress_cb=on_prog,
                                           gpu_index=gpu_index, env=env)
            if trang != "done":
                raise RuntimeError(f"engine.run_upscale tra '{trang}' (khong phai 'done')")
            with do("encode"):
                ow, oh = ff.encode_full(up_dir, tmp_video, out_local, output_fps, target_h,
                                        info["has_audio"], encoder, env=env)
        else:
            batch_info = dict(info, fps_str=output_fps, has_audio=info["has_audio"])
            with do("upscale_encode_theo_doan"):
                segs = up_jobs._upscale_batched(str(tmp), in_dir, tune, n_frames, batch_info,
                                                target_h, encoder, None, on_prog, None,
                                                gpu_index, env)
            with do("concat"):
                ow, oh = ff.concat_and_mux(segs, tmp_video, out_local, info["has_audio"], env=env)

        tgian_khung_dau = moc["khung_dau"]

        with do("upload_local"):
            # ⚠️ KHONG co R2 that trong mot cong cu do doc lap — day la mot
            #    COPY DIA LOCAL dung vai tro "upload" de co con so tuong duong
            #    thoi gian ghi tep cuoi cung; KHONG phai thoi gian egress R2.
            dich = scratch_dir / "outputs"
            dich.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(out_local, str(dich / f"{tmp.name}.mp4"))
    except (RuntimeError, ff.ProcessingCancelled, OSError) as exc:
        trang_thai, loi = "error", f"{type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    do.pha["total"] = round(time.perf_counter() - t_bat_dau, 3)
    return {"trang_thai": trang_thai, "loi": loi, "frames": n_frames, "out_w": ow, "out_h": oh,
            "eff_duration_s": round(eff_dur, 2) if eff_dur is not None else None,
            "time_to_first_frame_s": round(tgian_khung_dau, 3) if tgian_khung_dau else None,
            "stage_timings_s": do.pha, "tune": tune.model_dump() if tune is not None else None}


def chay_upscale_chi_rieng(in_dir: str, model: str, tile: int, threads: str,
                           gpu_index, env) -> dict:
    """Chi do TANG UPSCALE (tile-sweep / thread-sweep) — khung da tach san."""
    tune = TuneResult(model=model, tile=tile, threads=threads, est_alloc_mb=0,
                      free_mb=0, budget_mb=0, fast_path=True)
    out_dir = str(Path(in_dir).parent / f"up_t{tile}_{threads.replace(':', '')}")
    n = sum(1 for f in os.scandir(in_dir) if f.name.endswith(".png"))
    moc = {"t0": time.perf_counter(), "khung_dau": None}

    def on_prog(done: int, _moc=moc) -> None:
        if done >= 1 and _moc["khung_dau"] is None:
            _moc["khung_dau"] = time.perf_counter() - _moc["t0"]

    t0 = time.perf_counter()
    trang = engine.run_upscale(in_dir, out_dir, tune, n, progress_cb=on_prog,
                               gpu_index=gpu_index, env=env, _allow_fallback=False)
    tong = time.perf_counter() - t0
    shutil.rmtree(out_dir, ignore_errors=True)
    return {"trang_thai": trang, "frames": n, "tile": tile, "threads": threads,
            "total_s": round(tong, 3),
            "time_to_first_frame_s": round(moc["khung_dau"], 3) if moc["khung_dau"] else None}


def _chuan_bi_khung(video: dict, scratch_dir: Path, gpu_index, env, max_frames: int | None) -> str:
    """Tach khung MOT LAN de sweep tai su dung — tra thu muc `in_dir`."""
    tmp = Path(tempfile.mkdtemp(prefix="sweep_khung_", dir=str(scratch_dir)))
    tmp_video = str(tmp / ("src" + Path(video["duong"]).suffix))
    shutil.copyfile(video["duong"], tmp_video)
    in_dir = str(tmp / "in")
    max_sec = None
    if max_frames:
        fps = video.get("fps_str", "30/1")
        try:
            num, den = fps.split("/")
            fps_f = float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            fps_f = 30.0
        max_sec = max_frames / max(fps_f, 1.0)
    ff.extract_frames(tmp_video, in_dir, max_seconds=max_sec, env=env)
    return in_dir


# ── Bang Markdown tu JSONL ───────────────────────────────────────────────────
def render_report(duong_jsonl: Path) -> str:
    if not duong_jsonl.is_file():
        return f"(khong thay {duong_jsonl} — chua co ket qua nao)"
    ban_ghi = []
    with open(duong_jsonl, encoding="utf-8") as f:
        for dong in f:
            dong = dong.strip()
            if dong:
                ban_ghi.append(json.loads(dong))
    if not ban_ghi:
        return "(tep JSONL rong)"
    theo_loai: dict[str, list[dict]] = {}
    for b in ban_ghi:
        theo_loai.setdefault(b.get("kind", "khong_ro"), []).append(b)

    dong_ra = [f"<!-- render tu {duong_jsonl} — {len(ban_ghi)} ban ghi -->", ""]
    for loai, xs in theo_loai.items():
        dong_ra.append(f"## {loai} ({len(xs)} luot)")
        dong_ra.append("")
        theo_o: dict[tuple, list[dict]] = {}
        for x in xs:
            khoa = tuple(sorted((k, v) for k, v in x.get("matrix", {}).items() if k != "repeat_index"))
            theo_o.setdefault(khoa, []).append(x)
        cot = ["o", "n", "total_s (median)", "min", "max", "cpu_giay (median)", "trang_thai"]
        dong_ra.append("| " + " | ".join(cot) + " |")
        dong_ra.append("|" + "---|" * len(cot))
        for khoa, luot in theo_o.items():
            tong = [l["ket_qua"]["stage_timings_s"].get("total")
                   for l in luot if l.get("ket_qua", {}).get("stage_timings_s", {}).get("total") is not None]
            cpu = [l.get("tai_nguyen", {}).get("cpu_giay_process_tree")
                  for l in luot if l.get("tai_nguyen", {}).get("cpu_giay_process_tree") is not None]
            ten_o = ", ".join(f"{k}={v}" for k, v in khoa) or "(mac dinh)"
            trang_thai_list = {l.get("ket_qua", {}).get("trang_thai", "?") for l in luot}
            dong_ra.append("| " + " | ".join([
                ten_o, str(len(luot)),
                f"{statistics.median(tong):.2f}" if tong else "CHUA_DO",
                f"{min(tong):.2f}" if tong else "CHUA_DO",
                f"{max(tong):.2f}" if tong else "CHUA_DO",
                f"{statistics.median(cpu):.2f}" if cpu else "CHUA_DO",
                ", ".join(trang_thai_list),
            ]) + " |")
        dong_ra.append("")
    return "\n".join(dong_ra)


# ── Dry-run: in ke hoach + lenh + provenance, KHONG dung GPU ────────────────
def in_dry_run(args: argparse.Namespace) -> None:
    _in("=" * 78)
    _in("bench_upscale.py --dry-run — KHONG chay GPU, KHONG goi engine that.")
    _in("=" * 78)

    _in("\n[1] Provenance (doc that, chi doc):")
    prov = thu_thap_provenance(args.engine_dir)
    for k, v in prov.items():
        _in(f"    {k}: {v}")

    _in("\n[2] 4 video test that (ffprobe truc tiep, chi doc):")
    videos = _video_dang_ky()
    for v in videos:
        if v["ton_tai"]:
            _in(f"    {v['id']}: {v['w']}x{v['h']} {v['fps_str']} {v['duration_s']}s "
                f"{v['nb_frames']} khung audio={v['has_audio']} vfr={v['is_vfr']}")
        else:
            _in(f"    {v['id']}: ⛔ KHONG THAY TEP tai {v['duong']}")

    _in("\n[3] Muc ma tran KHONG CO MAU (bo 4 video hien co khong phu duoc):")
    for ten, ly_do in MEDIA_KHONG_CO_MAU:
        _in(f"    KHONG CO MAU — {ten}: {ly_do}")

    presets = args.preset or PRESETS
    targets = args.target or TARGETS
    features = args.feature or FEATURES
    vids = args.video or list(VIDEO_TEN_TEP)
    o_list = [(p, t, feat, v) for p in presets for t in targets for feat in features for v in vids]
    _in(f"\n[4] Ma tran (mode={args.mode}) — {len(o_list)} o, --repeat {args.repeat}:")
    for p, t, feat, v in o_list[:25]:
        _in(f"    preset={p} target={t} feature={feat} video={v} warmup={args.warmup or 'on'}")
    if len(o_list) > 25:
        _in(f"    ... con {len(o_list) - 25} o nua (dung --preset/--target/--feature/--video de thu hep)")

    _in("\n[5] Lenh 'demo' cho o dau tien (mo phong dung thu tu tham so that,"
        " KHONG duoc chay o day):")
    if o_list:
        p, t, feat, v = o_list[0]
        vid = next((x for x in videos if x["id"] == v), None)
        tune_demo = autotune.pick(Preset(p), vid.get("w", 1024) if vid else 1024,
                                  vid.get("h", 576) if vid else 576)
        exe = _engine_dir_thuc(args.engine_dir) / "realesrgan-ncnn-vulkan.exe"
        if tune_demo is not None:
            cmd_engine = lenh_engine_demo(exe, r"<in_dir>", r"<out_dir>", tune_demo, "<gpu_index>")
            _in("    engine: " + " ".join(cmd_engine))
        cmd_extract = lenh_extract_demo(ff._ff(), r"<src.mp4>", r"<out_dir>",
                                        cfr_fps=None, interpolate_fps=("60/1" if feat == "smooth_motion" else None))
        _in("    extract: " + " ".join(cmd_extract))

    _in("\n[6] Giao thuc lenh nang cho lenh CHAY THAT (khong ap dung --dry-run):")
    _in('    python "C:\\Users\\Thang Tuong\\.claude\\ltt\\chay_nang.py" --phien bench-upscale -- ^')
    _in("      python tools\\bench_upscale.py --mode matrix --preset fast --target 1080 ^")
    _in("      --feature normal --video v3 --repeat 3")
    _in('    ⚠️ chay_nang.py loc bo moi token "--" don le khoi lenh con — chi dung MOT "--"')
    _in('       ngay sau "--phien <ten>".')

    _in("\n[7] Tinh trang GPU ngay bay gio (nvidia-smi, chi doc):")
    ranh, snap = _may_ranh(args.busy_threshold_pct)
    _in(f"    {snap}")
    _in(f"    => {'RANH' if ranh else 'BAN — KHONG duoc do that luc nay'}")

    _in("\n[8] Thoi gian tuong uoc luong: CHUA_DO.")
    _in("    Chua co MOT phep do that nao tren may nay cho pipeline nay (GPU dang")
    _in("    ban boi job khach that — xem muc [7]). Bia mot con so o day vi pham")
    _in("    luat 'khong doan/khong uoc luong hieu nang' cua brief; --dry-run chi")
    _in("    xac nhan ke hoach + lenh dung, khong du doan toc do.")

    _in("\n[9] Cai bo do KHONG the do duoc (ke ca sau khi GPU ranh):")
    _in("    - 'interpolation' (minterpolate) khong tach duoc rieng khoi")
    _in("      frame_extraction — no la MOT bo loc trong CUNG lenh ffmpeg (ISSUE K).")
    _in("    - CPU-giay chia THEO PHA chua lam — sampler chay cho CA luot, khong")
    _in("      reset giua cac pha (them sampler moi quanh moi pha se tang overhead")
    _in("      lay mau; de lai cho ban sau neu can).")
    _in("    - Egress R2 that: bo do dung COPY DIA LOCAL thay 'upload' vi day la")
    _in("      cong cu do doc lap, khong co thong tin dang nhap storage.")
    _in("    - vulkan_index (gpu_index that) CHUA duoc xac dinh trong --dry-run vi")
    _in("      vulkan_device.vulkan_index_for() TU CHAY mot luot realesrgan that tren")
    _in("      anh 16x16 (vulkan_device.py:100-109) — bi cam trong nhiem vu nay.")


# ── main ─────────────────────────────────────────────────────────────────────
def _tao_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bench_upscale.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["matrix", "warmup", "tile-sweep", "thread-sweep"],
                   default="matrix")
    p.add_argument("--dry-run", action="store_true",
                   help="Chi in ke hoach/lenh/provenance. KHONG dung GPU.")
    p.add_argument("--preset", choices=PRESETS, action="append")
    p.add_argument("--target", type=int, choices=TARGETS, action="append")
    p.add_argument("--feature", choices=FEATURES, action="append")
    p.add_argument("--video", choices=list(VIDEO_TEN_TEP), action="append",
                   help="v1..v4 — mac dinh ca 4")
    p.add_argument("--warmup", choices=WARMUP_STATES, default=None,
                   help="matrix/tile-sweep/thread-sweep: mot trang thai co dinh "
                        "(mac dinh 'on', khop mac dinh cua app). mode=warmup LUON chay CA HAI.")
    p.add_argument("--repeat", type=int, default=1, help="so lan lap moi o (median/min/max/N)")
    p.add_argument("--tile", type=int, help="thread-sweep: tile co dinh")
    p.add_argument("--max-frames", type=int, default=None,
                   help="tile/thread-sweep: gioi han so khung tach de sweep nhanh hon")
    p.add_argument("--on-busy", choices=["wait", "abort"], default="abort")
    p.add_argument("--busy-threshold-pct", type=int, default=_BUSY_THRESHOLD_MAC_DINH)
    p.add_argument("--wait-timeout-s", type=int, default=_WAIT_TIMEOUT_MAC_DINH_S)
    p.add_argument("--out", default=None,
                   help="thu muc scratch (mac dinh %%TEMP%%/ltt_bench_upscale — KHONG duoc "
                        "nam trong cay kho)")
    p.add_argument("--engine-dir", default=None,
                   help="ghi de thu muc vendor/engine (mac dinh: engine.engine_dir() cua "
                        "checkout nay, du phong C:\\LTTPlatform\\app\\...)")
    p.add_argument("--codec", choices=["h264", "hevc"], default="h264")
    p.add_argument("--report", metavar="JSONL",
                   help="Doc mot tep JSONL da co, in bang Markdown, KHONG chay gi.")
    return p


def _scratch_dir(out_arg: str | None) -> Path:
    d = Path(out_arg) if out_arg else Path(tempfile.gettempdir()) / "ltt_bench_upscale"
    try:
        d.resolve().relative_to(GOC.resolve())
        raise SystemExit(f"⛔ --out {d} nam TRONG cay kho ({GOC}) — ket qua KHONG duoc ghi vao cay.")
    except ValueError:
        pass  # tot: nam ngoai cay kho
    d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> int:
    args = _tao_parser().parse_args()

    if args.report:
        _in(render_report(Path(args.report)))
        return 0

    if args.dry_run:
        in_dry_run(args)
        return 0

    # ── Duong CHAY THAT — moi luot phai qua fairness guard + chay_nang.py ──
    scratch = _scratch_dir(args.out)
    jsonl = scratch / "results.jsonl"
    prov = thu_thap_provenance(args.engine_dir)
    if not prov["engine_dir_la_that_trong_worktree_nay"] and not args.engine_dir:
        _in(f"⚠️ vendor/engine khong co trong worktree nay — dang doc provenance tu "
            f"{prov['engine_dir']} nhung se KHONG chay duoc engine that tu day. "
            f"Dung --engine-dir hoac chay tu mot checkout co vendor (vd C:\\LTTPlatform\\app).")
        return 2
    videos = {v["id"]: v for v in _video_dang_ky() if v["ton_tai"]}
    if not videos:
        _in(f"⛔ Khong doc duoc video nao tu {TEST_VIDEO_DIR}")
        return 2

    from apps.upscalevideo import vulkan_device
    from platform_core import gpu as gpu_mod
    danh_sach_gpu = gpu_mod.list_gpus()
    if not danh_sach_gpu:
        _in("⛔ Khong thay GPU nao qua platform_core.gpu.list_gpus()")
        return 2
    gpu_that = danh_sach_gpu[0]
    gpu_index = vulkan_device.vulkan_index_for(gpu_that.name)
    env = None  # ke thua moi truong tien trinh nay; day la cong cu do doc lap, khong da-thue

    presets = args.preset or PRESETS
    targets = args.target or TARGETS
    features = args.feature or FEATURES
    vids = args.video or list(videos)

    if args.mode == "matrix":
        warmup = args.warmup or "on"
        for p in presets:
            for t in targets:
                for feat in features:
                    for vid in vids:
                        if vid not in videos:
                            continue
                        for i in range(1, args.repeat + 1):
                            nen = cho_gpu_ranh(args.busy_threshold_pct, args.on_busy, args.wait_timeout_s)
                            with LayMauTaiNguyen(os.getpid()) as mau:
                                kq = chay_mot_luot_pipeline(videos[vid], p, t, feat, warmup,
                                                            scratch, gpu_index, env, args.codec)
                            ban_ghi = {"kind": "matrix",
                                      "matrix": {"preset": p, "target": t, "feature": feat,
                                                "video": vid, "warmup": warmup,
                                                "repeat_index": i, "repeat_total": args.repeat},
                                      "provenance": dict(prov, background_load_start=nen,
                                                         gpu_index=gpu_index, tile=kq.get("tune", {}).get("tile") if kq.get("tune") else None,
                                                         threads=kq.get("tune", {}).get("threads") if kq.get("tune") else None,
                                                         codec_requested=args.codec),
                                      "ket_qua": kq, "tai_nguyen": mau.tom_tat()}
                            ghi_ban_ghi(jsonl, ban_ghi)
                            _in(f"[{p}/{t}/{feat}/{vid} #{i}] {kq['trang_thai']} "
                               f"total={kq['stage_timings_s'].get('total')}s")
    elif args.mode == "warmup":
        for p in presets:
            vid = vids[0]
            for warmup in WARMUP_STATES:
                for i in range(1, args.repeat + 1):
                    nen = cho_gpu_ranh(args.busy_threshold_pct, args.on_busy, args.wait_timeout_s)
                    with LayMauTaiNguyen(os.getpid()) as mau:
                        kq = chay_mot_luot_pipeline(videos[vid], p, 1080, "normal", warmup,
                                                    scratch, gpu_index, env, args.codec)
                    ban_ghi = {"kind": "warmup",
                              "matrix": {"preset": p, "video": vid, "warmup": warmup,
                                        "repeat_index": i, "repeat_total": args.repeat},
                              "provenance": dict(prov, background_load_start=nen, gpu_index=gpu_index),
                              "ket_qua": kq, "tai_nguyen": mau.tom_tat()}
                    ghi_ban_ghi(jsonl, ban_ghi)
                    _in(f"[warmup={warmup} {p} #{i}] ttff={kq['time_to_first_frame_s']}s "
                       f"total={kq['stage_timings_s'].get('total')}s")
    elif args.mode == "tile-sweep":
        for p in presets:
            vid = vids[0]
            nen = cho_gpu_ranh(args.busy_threshold_pct, args.on_busy, args.wait_timeout_s)
            in_dir = _chuan_bi_khung(videos[vid], scratch, gpu_index, env, args.max_frames)
            for tile in TILE_SWEEP[p]:
                for i in range(1, args.repeat + 1):
                    with LayMauTaiNguyen(os.getpid()) as mau:
                        kq = chay_upscale_chi_rieng(in_dir, PRESET_MODEL[Preset(p)], tile,
                                                    "4:4:4" if p == "fast" else "1:2:2",
                                                    gpu_index, env)
                    ghi_ban_ghi(jsonl, {"kind": "tile_sweep",
                                       "matrix": {"preset": p, "tile": tile, "video": vid,
                                                 "repeat_index": i, "repeat_total": args.repeat},
                                       "provenance": dict(prov, background_load_start=nen, gpu_index=gpu_index),
                                       "ket_qua": kq, "tai_nguyen": mau.tom_tat()})
                    _in(f"[tile-sweep {p} tile={tile} #{i}] {kq['trang_thai']} {kq['total_s']}s")
            shutil.rmtree(Path(in_dir).parent, ignore_errors=True)
    elif args.mode == "thread-sweep":
        if not args.tile:
            _in("⛔ --mode thread-sweep can --tile <so>")
            return 2
        for p in presets:
            vid = vids[0]
            nen = cho_gpu_ranh(args.busy_threshold_pct, args.on_busy, args.wait_timeout_s)
            in_dir = _chuan_bi_khung(videos[vid], scratch, gpu_index, env, args.max_frames)
            for threads in THREAD_SWEEP:
                for i in range(1, args.repeat + 1):
                    with LayMauTaiNguyen(os.getpid()) as mau:
                        kq = chay_upscale_chi_rieng(in_dir, PRESET_MODEL[Preset(p)],
                                                    args.tile, threads, gpu_index, env)
                    ghi_ban_ghi(jsonl, {"kind": "thread_sweep",
                                       "matrix": {"preset": p, "tile": args.tile, "threads": threads,
                                                 "video": vid, "repeat_index": i, "repeat_total": args.repeat},
                                       "provenance": dict(prov, background_load_start=nen, gpu_index=gpu_index),
                                       "ket_qua": kq, "tai_nguyen": mau.tom_tat()})
                    _in(f"[thread-sweep {p} threads={threads} #{i}] {kq['trang_thai']} {kq['total_s']}s")
            shutil.rmtree(Path(in_dir).parent, ignore_errors=True)

    _in(f"\nKet qua: {jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
