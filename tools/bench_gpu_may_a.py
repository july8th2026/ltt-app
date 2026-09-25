"""Bench CPU vs GPU cua may A cho duong chay Auto Scan Video (lan `gpu-may-a`).

    python tools\\bench_gpu_may_a.py --bench canh   --video <mp4> --lan 3
    python tools\\bench_gpu_may_a.py --bench qc-ff  --video <mp4> --lan 3
    python tools\\bench_gpu_may_a.py --bench do     --video <mp4> --lan 3

⛔ Script DO, khong phai script san pham: no khong sua gi trong `apps/` hay
   `platform_core/`. Ket qua ghi ra JSON o `--ra`.

🔑 Card xin qua `platform_core.gpu_lease.hold` — DUNG duong san pham. Khong tu
   dat `CUDA_VISIBLE_DEVICES`. Duong CPU dat `CUDA_VISIBLE_DEVICES=""` de che
   card khoi tien trinh con (do la cach DUY NHAT bat mot runner dung
   `torch.cuda.is_available()` chay CPU ma khong sua ma no).

⚠️ Moi phep chay trong TIEN TRINH CON (`qc-venv` cho bo do, ffmpeg cho video),
   nen "thoi gian" o day la thoi gian ca tien trinh — gom ca nap model. Cot
   rieng cho phan nap model doc tu `tai_nguyen` cua runner khi co.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC))

QC_PY = Path(r"C:\LTTPlatform\qc-venv\Scripts\python.exe")
DO_LUONG = GOC / "apps" / "asv_gpu" / "do_luong"


# ── Lay mau VRAM ────────────────────────────────────────────────────────────
class MauVram:
    """Lay mau `memory.used` cua card 0 moi 0,25 s trong lucrun mot phep."""

    def __init__(self, chu_ky: float = 0.25):
        self.chu_ky = chu_ky
        self.mau: list[int] = []
        self._dung = threading.Event()
        self._t: threading.Thread | None = None

    def _vong(self) -> None:
        while not self._dung.wait(self.chu_ky):
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5)
                self.mau.append(int(r.stdout.strip().splitlines()[0]))
            except (OSError, subprocess.SubprocessError,
                    ValueError, IndexError):
                pass          # mot mau hut khong duoc giet luot do

    def __enter__(self):
        self._t = threading.Thread(target=self._vong, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a):
        self._dung.set()
        if self._t:
            self._t.join(timeout=2)

    @property
    def dinh(self) -> int:
        return max(self.mau) if self.mau else 0


def nen_vram() -> int:
    r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                        "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, timeout=8)
    return int(r.stdout.strip().splitlines()[0])


def tai_may() -> str:
    """Tai may NGAY TRUOC mot phep. Mot phep so CPU↔GPU khong ghi tai luc do la
    mot phep so hai dieu kien khac nhau (dieu phoi chot 24/09)."""
    try:
        r = subprocess.run([sys.executable, str(GOC / "tools" / "tai_may.py")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
        return " | ".join(x.strip() for x in r.stdout.strip().splitlines() if x.strip())
    except Exception as exc:                                    # noqa: BLE001
        return f"khong doc duoc: {type(exc).__name__}"


_TAI: list[str] = []


def tom(xs: list[float]) -> dict:
    xs = [round(x, 3) for x in xs]
    d = {"lan": xs, "trung_vi": round(statistics.median(xs), 3),
         "min": min(xs), "max": max(xs),
         "dai": round(max(xs) - min(xs), 3)}
    if _TAI:
        d["tai_may_moi_lan"] = list(_TAI)
        _TAI.clear()
    return d


# ── Chay mot runner cua qc-venv ─────────────────────────────────────────────
def chay_runner(script: Path, dau_vao: dict, *, gpu_uuid: str,
                timeout_s: int = 3600) -> tuple[float, dict, int]:
    """(giay, JSON ra, VRAM dinh do duoc). `gpu_uuid=""` ⇒ che card hoan toan."""
    env = dict(os.environ)
    env["HF_HOME"] = env.get("LTT_QC_HF_HOME") or r"C:\LTTPlatform\hf-cache"
    env.setdefault("TORCH_HOME", str(Path(env["HF_HOME"]) / "torch"))
    env["PYTHONIOENCODING"] = "utf-8"
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    if gpu_uuid:
        from platform_core.gpu import env_for
        env = env_for(gpu_uuid, env)
    else:
        # ⛔ KHONG dat chuoi RONG. Do that 24/09: `CUDA_VISIBLE_DEVICES=""` truyen
        #    qua `subprocess` tren Windows bi **xoa han** khoi moi truong con, nen
        #    tien trinh con thay DU MOI card va runner bao `thiet_bi: "cuda"` —
        #    tuc nhanh "CPU" do ra mot con so GPU. `-1` la gia tri CUDA hieu la
        #    "khong card nao".
        env["CUDA_VISIBLE_DEVICES"] = "-1"
    with tempfile.TemporaryDirectory(prefix="bench-do-") as tam:
        vao, ra, lg = (Path(tam) / "vao.json", Path(tam) / "ra.json",
                       Path(tam) / "log.txt")
        vao.write_text(json.dumps(dau_vao, ensure_ascii=False), encoding="utf-8")
        with MauVram() as mv, open(lg, "wb") as f:
            t0 = time.perf_counter()
            p = subprocess.run([str(QC_PY), str(script), str(vao), str(ra)],
                               stdout=f, stderr=subprocess.STDOUT, env=env,
                               timeout=timeout_s)
            giay = time.perf_counter() - t0
        duoi = lg.read_text(encoding="utf-8", errors="replace")[-4000:]
        if p.returncode != 0 or not ra.is_file():
            raise RuntimeError(f"runner thoat {p.returncode}: {duoi}")
        return giay, json.loads(ra.read_text(encoding="utf-8")), mv.dinh


# ── BENCH 1: tach canh + rut khung (CPU) va tran giai ma cua card ───────────
def bench_canh(video: Path, lan: int) -> dict:
    from apps.auto_scan_video import canh as canh_mod

    ra: dict = {"video": str(video)}

    # 1a. PySceneDetect ContentDetector — duong SAN PHAM, CPU, OpenCV.
    ts, moc = [], None
    for _ in range(lan):
        _TAI.append(tai_may())
        t0 = time.perf_counter()
        m = canh_mod.tim_moc(str(video))
        ts.append(time.perf_counter() - t0)
        moc = m
    ra["pyscenedetect_cpu"] = tom(ts) | {"so_moc": len(moc or []),
                                         "moc": (moc or [])[:40]}

    # 1b. Rut khung dai dien (ffmpeg, CPU) — phan con lai cua edit_plan cuc bo.
    ci = canh_mod.phan_tich(str(video), thoi_luong=thoi_luong_video(video))
    moc_khung = [m for c in ci.canh for m in c.khung]
    ts = []
    for _ in range(lan):
        _TAI.append(tai_may())
        t0 = time.perf_counter()
        khung = canh_mod.rut_khung(str(video), moc_khung)
        ts.append(time.perf_counter() - t0)
    ra["rut_khung_cpu"] = tom(ts) | {"so_khung": len(khung), "so_canh": len(ci.canh)}

    # 1c. Tran giai ma: doc ca tep, KHONG loc, CPU vs nvdec (h264_cuvid).
    for ten, tien in (("giai_ma_cpu", []),
                      ("giai_ma_nvdec", ["-hwaccel", "cuda",
                                         "-hwaccel_output_format", "cuda"])):
        ts, dinh = [], 0
        for _ in range(lan):
            cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error",
                   *tien, "-i", str(video), "-f", "null", "-"]
            _TAI.append(tai_may())
            with MauVram() as mv:
                t0 = time.perf_counter()
                subprocess.run(cmd, capture_output=True, timeout=1800)
                ts.append(time.perf_counter() - t0)
            dinh = max(dinh, mv.dinh)
        ra[ten] = tom(ts) | {"vram_dinh_mb": dinh}

    # 1d. `scdet` cua ffmpeg (bo tach KHAC — de doi chieu ket qua, khong de thay)
    for ten, tien in (("scdet_cpu", []),
                      ("scdet_nvdec", ["-hwaccel", "cuda"])):
        ts, moc_sc = [], []
        for _ in range(lan):
            cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-v", "info",
                   *tien, "-i", str(video),
                   "-vf", "scdet=threshold=10", "-f", "null", "-"]
            _TAI.append(tai_may())
            t0 = time.perf_counter()
            p = subprocess.run(cmd, capture_output=True, text=True,
                               errors="replace", timeout=1800)
            ts.append(time.perf_counter() - t0)
            moc_sc = sorted({round(float(m), 3) for m in re.findall(
                r"lavfi\.scd\.time:\s*([0-9.]+)", p.stderr)})
        ra[ten] = tom(ts) | {"so_moc": len(moc_sc), "moc": moc_sc[:40]}
    return ra


def thoi_luong_video(video: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


# ── BENCH 2: QC hinh T17 (blackdetect + freezedetect) CPU vs nvdec ──────────
def bench_qc_ff(video: Path, lan: int) -> dict:
    from apps.auto_scan_video import qc as qc_mod

    ra: dict = {"video": str(video)}
    loc = f"{qc_mod.BLACKDETECT},{qc_mod.FREEZEDETECT}"
    for ten, tien, vf in (
            ("t17_cpu", [], loc),
            # nvdec giai ma tren card roi tai khung ve RAM: `blackdetect` va
            # `freezedetect` la bo loc CPU, khong co ban CUDA.
            ("t17_nvdec", ["-hwaccel", "cuda"], loc)):
        ts, out = [], ""
        for _ in range(lan):
            cmd = ["ffmpeg", "-hide_banner", "-nostdin", *tien, "-i", str(video),
                   "-vf", vf, "-an", "-f", "null", "-"]
            _TAI.append(tai_may())
            t0 = time.perf_counter()
            p = subprocess.run(cmd, capture_output=True, text=True,
                               errors="replace", timeout=1800)
            ts.append(time.perf_counter() - t0)
            out = p.stderr
        ra[ten] = tom(ts) | {
            "black": sorted(re.findall(r"black_start:([0-9.]+)", out)),
            "freeze": sorted(re.findall(r"freeze_start:\s*([0-9.]+)", out)),
        }
    # VMAF: duong san pham (CPU) — ghi lai thoi gian de so voi gia tri giai ma.
    return ra


# ── BENCH 3: bo do QC (SQUIM · ECAPA gioi · MetricX) CPU vs GPU ─────────────
CAP_DICH = [
    {"ma": "c1", "nguon": "他从高空跳下，伞包在最后一刻才打开。",
     "dich": "Anh ta nhảy từ trên cao, túi dù chỉ mở vào giây cuối cùng."},
    {"ma": "c2", "nguon": "如果落地太慢，敌人会先占据有利位置。",
     "dich": "Nếu hạ cánh quá chậm, địch sẽ chiếm được vị trí có lợi trước."},
    {"ma": "c3", "nguon": "这个细节操作可以帮你化解危机。",
     "dich": "Thao tác chi tiết này có thể giúp bạn hoá giải nguy hiểm."},
    {"ma": "c4", "nguon": "记住跳伞的高度和角度非常重要。",
     "dich": "Hãy nhớ rằng độ cao và góc nhảy dù là rất quan trọng."},
    {"ma": "c5", "nguon": "下一期我们讲怎么选择落点。",
     "dich": "Số sau chúng ta sẽ nói về cách chọn điểm hạ cánh."},
    {"ma": "c6", "nguon": "谢谢观看，别忘了点赞和关注。",
     "dich": "Cảm ơn đã xem, đừng quên thích và theo dõi."},
]


def cat_doan_tieng(video: Path, dich: Path, *, so: int = 6,
                   dai_s: float = 8.0) -> list[dict]:
    """Cat `so` doan `dai_s` giay tu tieng cua phim -> wav 16 kHz mono."""
    dich.mkdir(parents=True, exist_ok=True)
    tl = thoi_luong_video(video)
    buoc = max(dai_s, (tl - dai_s) / max(1, so))
    ds = []
    for i in range(so):
        bat = round(min(i * buoc, max(0.0, tl - dai_s)), 3)
        tep = dich / f"doan_{i + 1:02d}.wav"
        if not tep.is_file():
            subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y",
                            "-ss", str(bat), "-t", str(dai_s), "-i", str(video),
                            "-vn", "-ac", "1", "-ar", "16000", str(tep)],
                           check=True, timeout=300)
        ds.append({"ma": f"doan_{i + 1:02d}", "tep": str(tep)})
    return ds


def bench_do(video: Path, lan: int, tam_goc: Path, nhanh: str = "ca") -> dict:
    from apps.asv_gpu.do_luong import gioi, squim

    doan = cat_doan_tieng(video, tam_goc / "doan")
    ra: dict = {"video": str(video), "so_doan": len(doan),
                "vram_nen_mb": nen_vram()}

    phep = {
        "squim": (DO_LUONG / "squim_runner.py",
                  {"doan": doan, "url": squim.URL_WEIGHTS,
                   "sha256": squim.SHA256_WEIGHTS, "cua_so_s": squim.CUA_SO_S,
                   "buoc_s": squim.BUOC_S}),
        "gioi_ecapa": (DO_LUONG / "gioi_runner.py",
                       {"clip": doan, "cua_so_s": gioi.CUA_SO_S,
                        "buoc_s": gioi.BUOC_S, "nguong_rms": gioi.NGUONG_RMS}),
        "metricx": (DO_LUONG / "_metricx" / "chay.py",
                    {"cap": CAP_DICH, "thiet_bi": "auto", "lo": 16}),
    }
    canh_nhanh = ("gpu", "cpu") if nhanh == "ca" else (nhanh,)
    for ten, (script, dv) in phep.items():
        for nh in canh_nhanh:
            ts, dinh, kq = [], 0, None
            try:
                # ⭐ Lease chi bao DUNG cac luot GPU cua MOT bo do, roi nha ngay:
                #    giu card suot ca bench (ke ca trong luc do CPU) la giu mot
                #    tai nguyen DOC QUYEN trong luc CHO (dieu phoi chot 23-24/09).
                with _card(nh) as uuid:
                    if nh == "gpu" and not uuid:
                        ra[f"{ten}_gpu"] = {"loi": "khong xin duoc lease"}
                        continue
                    for _ in range(lan):
                        _TAI.append(tai_may())
                        giay, out, vram = chay_runner(script, dv, gpu_uuid=uuid)
                        ts.append(giay)
                        dinh = max(dinh, vram)
                        kq = out
            except Exception as exc:                            # noqa: BLE001
                ra[f"{ten}_{nh}"] = {"loi": f"{type(exc).__name__}: {exc}"[-2500:]}
                continue
            ra[f"{ten}_{nh}"] = tom(ts) | {
                "vram_dinh_mb": dinh,
                "tai_nguyen": (kq or {}).get("tai_nguyen")
                or (kq or {}).get("thong_tin"),
                "ket_qua": (kq or {}).get("ket_qua") or (kq or {}).get("diem"),
            }
    return ra


@contextlib.contextmanager
def _card(nhanh: str):
    """UUID card cho nhanh `gpu` (qua `gpu_lease.hold`), rong cho nhanh `cpu`."""
    if nhanh != "gpu":
        yield ""
        return
    # 🔑 Card xin qua `gpu_lease.acquire` — nen DUNG logic xet cho cua san pham
    #    (`free_mb`, `HEADROOM_MB`, chinh sach card cap may, cong bo `gpu_claims`
    #    ra mat phang dung chung). Chi **bang luu lease** la SQLite cuc bo, vi
    #    `LTT_DATABASE_URL` nam trong `secretspp.env` (ACL chan, co y).
    #    Cung khuon ma `tools/autosub_gpu_smoke.py:30` da dung.
    #    ⚠️ Han che phai noi ra: lease SQLite KHONG thay duoc lease cua worker
    #       production trong PostgreSQL. `gpu_claims` (tep JSON cap may) thi van
    #       thay, nen phan chong tranh card voi Voice/bot khong mat.
    import os as _os
    if not _os.environ.get("LTT_DATABASE_URL"):
        _db = Path(tempfile.gettempdir()) / "bench-gpu-may-a" / "lease.db"
        _db.parent.mkdir(parents=True, exist_ok=True)
        _os.environ["LTT_DATABASE_URL"] = f"sqlite:///{_db.as_posix()}"
        _os.environ.setdefault("LTT_DATA_DIR", str(_db.parent / "data"))
        from platform_core.db import Base, get_engine, reset_engine
        import platform_core.models  # noqa: F401
        reset_engine()
        Base.metadata.create_all(get_engine())
    from platform_core import gpu_lease
    from platform_core.db import get_session
    gen = get_session()
    db = next(gen)
    try:
        with gpu_lease.hold(db, worker_id="bench-gpu-may-a",
                            job_id="bench-gpu-may-a", need_mb=5200) as le:
            yield le.gpu_uuid if le else ""
    finally:
        try:
            next(gen)
        except StopIteration:
            pass



# ── BENCH 4: ma hoa lai libx264 vs h264_nvenc + VMAF cua CA HAI ─────────────
def bench_vmaf(video: Path, lan: int, tam_goc: Path) -> dict:
    """⭐ Cau chua ai tra loi: `qc.VMAF_TOI_THIEU = 75` chua tung do tren nhanh
    `h264_nvenc`. Day do CA HAI nhanh bang DUNG tham so san pham
    (`che_do_render.THAM_SO`) roi cham VMAF bang DUNG mo hinh + `n_subsample`
    cua `qc.py`.
    """
    from apps.auto_scan_video import che_do_render, qc as qc_mod

    tam_goc.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0",
                        str(video)], capture_output=True, text=True, check=True)
    rong, cao = (int(x) for x in r.stdout.strip().split(",")[:2])
    ra: dict = {"video": str(video), "rong": rong, "cao": cao,
                "vmaf_toi_thieu": qc_mod.VMAF_TOI_THIEU,
                "n_subsample": qc_mod.VMAF_N_SUBSAMPLE}

    for bo in ("libx264", "h264_nvenc"):
        dich = tam_goc / f"ra_{bo}.mp4"
        ts, dinh = [], 0
        for _ in range(lan):
            cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-y",
                   "-i", str(video), *che_do_render.THAM_SO[bo],
                   "-c:a", "copy", str(dich)]
            _TAI.append(tai_may())
            with MauVram() as mv:
                t0 = time.perf_counter()
                p = subprocess.run(cmd, capture_output=True, text=True,
                                   errors="replace", timeout=1800)
                ts.append(time.perf_counter() - t0)
            dinh = max(dinh, mv.dinh)
            if p.returncode != 0:
                ra[bo] = {"loi": p.stderr[-400:]}
                break
        else:
            # VMAF: ban ra vs nguon. Mo hinh + co gian + n_subsample cua `qc.py`.
            mo_hinh, co_gian = qc_mod.chon_mo_hinh_vmaf(rong, cao)
            log = tam_goc / f"vmaf_{bo}.json"
            loc = (f"[0:v]setpts=PTS-STARTPTS,{co_gian}format=yuv420p[ref];"
                   f"[1:v]setpts=PTS-STARTPTS,{co_gian}format=yuv420p[dist];"
                   f"[dist][ref]libvmaf=model=version={mo_hinh}"
                   f":n_subsample={qc_mod.VMAF_N_SUBSAMPLE}:shortest=1"
                   f":ts_sync_mode=nearest:log_fmt=json"
                   f":log_path='{qc_mod._thoat_duong_loc(str(log))}'")
            t0 = time.perf_counter()
            pv = subprocess.run(
                ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error",
                 "-i", str(video), "-i", str(dich), "-filter_complex", loc,
                 "-f", "null", "-"], capture_output=True, text=True,
                errors="replace", timeout=3600)
            giay_vmaf = time.perf_counter() - t0
            diem = ({"loi": pv.stderr[-400:]} if not log.is_file()
                    else qc_mod.doc_vmaf(json.loads(log.read_text(encoding="utf-8")),
                                         mo_hinh=mo_hinh))
            ra[bo] = tom(ts) | {
                "vram_dinh_mb": dinh,
                "co_byte": dich.stat().st_size if dich.is_file() else 0,
                "vmaf": diem, "giay_cham_vmaf": round(giay_vmaf, 2),
                "dat_nguong": bool(isinstance(diem, dict)
                                   and diem.get("trung_binh", 0)
                                   >= qc_mod.VMAF_TOI_THIEU),
            }
    return ra

# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True, choices=("canh", "qc-ff", "do", "vmaf"))
    ap.add_argument("--video", required=True)
    ap.add_argument("--lan", type=int, default=3)
    ap.add_argument("--nhanh", default="ca", choices=("ca", "gpu", "cpu"))
    ap.add_argument("--ra", default="")
    a = ap.parse_args()
    video = Path(a.video)
    if not video.is_file():
        print(f"khong thay video: {video}")
        return 2
    tam = Path(os.environ.get("LTT_BENCH_TAM")
               or (Path(tempfile.gettempdir()) / "bench-gpu-may-a"))
    tam.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    if a.bench == "canh":
        kq = bench_canh(video, a.lan)
    elif a.bench == "qc-ff":
        kq = bench_qc_ff(video, a.lan)
    elif a.bench == "vmaf":
        kq = bench_vmaf(video, a.lan, tam / "vmaf")
    else:
        kq = bench_do(video, a.lan, tam, a.nhanh)
    kq["giay_ca_bench"] = round(time.perf_counter() - t0, 1)
    van = json.dumps(kq, ensure_ascii=False, indent=2)
    print(van)
    if a.ra:
        Path(a.ra).write_text(van, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
