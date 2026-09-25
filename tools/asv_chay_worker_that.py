"""Chay MOT lan Auto Scan Video tren WORKER THAT cua may chu, va DO no.

    python tools\\asv_chay_worker_that.py tao  --video "<duong>" [--preset ...]
    python tools\\asv_chay_worker_that.py theo-doi <run_id> [--tran-phut 90]
    python tools\\asv_chay_worker_that.py worker [--giay 3600]

## Vi sao tep nay ton tai

Lan `asv-toc-do` do duoc: **0 / 19.979** luot job trong log worker production la
`auto_scan_video`/`asv_*`. Tuc moi nghiem thu cua san pham nay (12/12 giai doan,
QC dat, hai preset) chay trong KHUON TEST — chua bao gio tren tien trinh worker
that, noi PATH, quyen, bien moi truong va thu muc lam viec deu khac.

⛔ Day KHONG phai mot phep kiem: no khong khang dinh gi, no **do** va **ghi
   traceback nguyen van**. Muc tieu la TIM CHO VO, khong phai dat mau xanh.

## Ba dieu ve moi truong that ma khuon test khong tai hien duoc

1. `LTT_WORKER_POOLS = "api:6, gpu+ffmpeg:1, voice:1"` — bon app cua ASV
   (`auto_scan_video`=api, `asv_media`=ffmpeg, `asv_voice`=voice, `asv_gpu`=gpu)
   nam tren BA lan khac nhau. Mot giai doan chuyen lan la mot lan doi tien
   trinh, va do la cho thoi gian chet sinh ra.
2. Worker chay duoi `LocalSystem`: PATH khac phien nguoi dung (da tung thieu
   `ffmpeg`).
3. Co `LTT_AUTO_SCAN_VIDEO` **khong** co trong `secrets\\app.env`. No chi chan
   duong TAO (`dich_vu_tao.da_mo`) — ⛔ no KHONG chan worker thi hanh giai doan.
   Nen worker production **nhat duoc** job ASV du san pham "chua mo".

## Cach do giay CPU moi giai doan

`jobs.worker_id` la `"<host>:<pid>"` (xem `job_worker._chay_mot_worker`), nen
biet dung tien trinh nao chay giai doan nao. Lay `KernelModeTime + UserModeTime`
cua CA CAY tien trinh do luc bat dau va luc ket thuc giai doan; hieu la giay CPU.
Mot worker chay MOT job mot luc, nen nhieu tu job khac la khong dang ke.

⛔ Khong bao cao mot cot. `docs/QUY_TAC_CHAY_LENH_NANG.md` §2b: `giay CPU` tra
   loi "ton bao nhieu suc tinh", `dong ho tuong` tra loi "dieu kien do" — va
   tuong dai + CPU thap la dang CHO, khong phai dang tinh.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

APP_ENV = pathlib.Path(r"C:\LTTPlatform\secrets\app.env")

#: Cac giai doan cua chuoi, lay tu ma nguon chu khong go tay.
def _ten_giai_doan() -> tuple[str, ...]:
    from apps.auto_scan_video import pipeline
    return pipeline.TEN_GIAI_DOAN


def nap_env() -> None:
    """Nap `app.env` vao tien trinh NAY. ⛔ Khong ghi, khong in gia tri."""
    if not APP_ENV.is_file():
        raise SystemExit(f"khong thay {APP_ENV} — tep nay chi chay tren may chu")
    for dong in APP_ENV.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#") or "=" not in dong:
            continue
        ten, _, gt = dong.partition("=")
        os.environ.setdefault(ten.strip(), gt.strip())


# ══════════════════════════════════════════════════════════════════════════════
#  Giay CPU cua mot CAY tien trinh
# ══════════════════════════════════════════════════════════════════════════════

def cpu_cay(pid: int) -> tuple[float, int]:
    """`(giay CPU cong don cua CA CAY tien trinh, so tien trinh dem duoc)`.

    ⭐ `psutil`, ⛔ khong `Get-CimInstance Win32_Process`: ban dau ham nay goi
       PowerShell liet ke TOAN BO bang tien trinh moi lan, va mot lan goi mat
       **hon 40 giay** tren may nay — tuc phep do tro thanh mot nghi can, dung
       thu `QUY_TAC_CHAY_LENH_NANG.md` §3.3 cam. `psutil` hoi dung mot cay.

    ⚠️ Tien trinh CHAU (ffmpeg, demucs, whisper do worker de ra) duoc CONG VAO
       — do la ca muc dich. Mot giai doan ASV tieu phan lon suc tinh o tien
       trinh con, va mot con so chi dem tien trinh cha se noi rang `render`
       gan nhu mien phi.
    """
    import psutil

    tong = 0.0
    so = 0
    try:
        goc = psutil.Process(int(pid))
        cac = [goc] + goc.children(recursive=True)
    except Exception:                                    # noqa: BLE001
        return (0.0, 0)
    for p in cac:
        try:
            t = p.cpu_times()
            tong += float(t.user) + float(t.system)
            so += 1
        except Exception:                                # noqa: BLE001
            continue
    return (round(tong, 2), so)


def _pid_cua(worker_id: str) -> int:
    """`"<host>:<pid>"` -> pid. 0 khi khong doc duoc."""
    try:
        return int(str(worker_id or "").rsplit(":", 1)[-1])
    except ValueError:
        return 0


# ══════════════════════════════════════════════════════════════════════════════
#  tao
# ══════════════════════════════════════════════════════════════════════════════

def lenh_tao(args) -> int:
    return 0 if _tao(args) else 2


def lenh_chay(args) -> int:
    """`tao` roi `theo-doi` trong MOT luot — mot lan giu khoa may, khong hai."""
    run_id = _tao(args)
    if not run_id:
        return 2
    args.run_id = run_id
    return lenh_theo_doi(args)


def _tao(args) -> str:
    nap_env()
    # 🔑 Co chi bat trong TIEN TRINH NAY. ⛔ Khong ghi vao app.env, khong restart
    #    dich vu nao — `dich_vu_tao.da_mo()` doc `os.environ` luc goi.
    os.environ["LTT_AUTO_SCAN_VIDEO"] = "1"
    os.chdir(GOC)

    from sqlalchemy import text

    from apps.auto_scan_video import dich_vu_tao, features
    from platform_core import credit, db as dbmod

    video = pathlib.Path(args.video)
    if not video.is_file():
        print("KHONG THAY PHIM:", video)
        return ""
    print("PHIM  :", video)
    print("BYTE  :", video.stat().st_size)
    print("PRESET:", args.preset)

    tho = {
        "preset": args.preset,
        "ngon_ngu_nguon": args.nguon,
        "ngon_ngu_dich": args.dich,
        "che_do_giong": args.che_do_giong,
        "giong_id": args.giong,
    }
    for s in dbmod.get_session():
        r = s.execute(text("SELECT id FROM users WHERE email = :e"),
                      {"e": args.email}).first()
        if r is None:
            print("KHONG CO TAI KHOAN:", args.email)
            return ""
        owner = r.id
        print("CHU   :", args.email, owner, "| so_du =", credit.so_du(s, owner))
        try:
            ho_so = dich_vu_tao.dung_cai_dat(s, owner_id=owner, tho=tho)
        except Exception as exc:                          # noqa: BLE001
            s.rollback()
            print("VO O CUA DUYET DAU VAO:", type(exc).__name__, exc)
            raise
        try:
            run = features.tao_run_tu_tai_len(
                s, owner_id=owner, duong_tep=str(video),
                ten_tep=video.name, settings=ho_so)
            s.commit()
        except Exception as exc:                          # noqa: BLE001
            s.rollback()
            print("VO O TAO RUN:", type(exc).__name__, exc)
            raise
        print("RUN_ID:", run.id)
        print("CREDIT GIU:", run.credit_held)
        print("SOURCE_KEY:", run.source_key)
        print("SO_DU SAU KHI GIU:", credit.so_du(s, owner), flush=True)
        return str(run.id)
    return ""


# ══════════════════════════════════════════════════════════════════════════════
#  theo-doi
# ══════════════════════════════════════════════════════════════════════════════

def lenh_theo_doi(args) -> int:
    nap_env()
    os.chdir(GOC)

    from sqlalchemy import text

    from platform_core import db as dbmod

    run_id = args.run_id
    het = time.monotonic() + args.tran_phut * 60.0
    t0 = time.time()

    #: stage -> ho so do
    do: dict[str, dict] = {}
    #: so luot job `auto_scan_video.advance` da thay
    advance: dict[str, dict] = {}
    truoc_stage: dict[str, str] = {}
    truoc_run = ""
    nhat_ky: list[dict] = []

    def ghi(ma: str, **kw):
        muc = {"t": round(time.time() - t0, 1),
               "gio": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "ma": ma, **kw}
        nhat_ky.append(muc)
        print(f"[{muc['t']:8.1f}s] {ma} " +
              " ".join(f"{k}={v}" for k, v in kw.items()), flush=True)

    # ⛔ MOT phien cho ca vong theo doi. Mo/dong mot phien moi mot nhip (1.200
    #    nhip cho mot gio) la 1.200 lan bat tay voi CSDL PRODUCTION — dung kieu
    #    "phep do tro thanh nghi can" ma QUY_TAC_CHAY_LENH_NANG §3.3 canh bao.
    #    `rollback()` dau moi nhip mo mot giao dich moi ⇒ van doc duoc du lieu moi.
    dbmod.get_engine()
    phien = dbmod._session_factory()     # noqa: SLF001 - khong co cua cong khai
    xong = False
    try:
        while time.monotonic() < het:
            s = phien
            s.rollback()
            run = s.execute(text(
                "SELECT id, status, credit_held, credit_actual, error "
                "FROM asv_run WHERE id = :r"), {"r": run_id}).first()
            if run is None:
                print("KHONG CO RUN", run_id)
                return 2
            if run.status != truoc_run:
                ghi("run", trang_thai=run.status, credit_actual=run.credit_actual,
                    loi=(run.error or "")[:200])
                truoc_run = run.status

            stages = s.execute(text(
                "SELECT stage, status, job_id, attempt, started_at, finished_at, "
                "       error, credit_actual "
                "FROM asv_stage WHERE run_id = :r"), {"r": run_id}).all()
            for st in stages:
                cu = truoc_stage.get(st.stage)
                if cu == st.status:
                    continue
                truoc_stage[st.stage] = st.status
                job = None
                if st.job_id:
                    job = s.execute(text(
                        "SELECT id, job_type, status, worker_id, attempts, error, "
                        "       created_at, started_at, finished_at "
                        "FROM jobs WHERE id = :j"), {"j": st.job_id}).first()
                wid = getattr(job, "worker_id", "") or ""
                ho = do.setdefault(st.stage, {"stage": st.stage})
                if st.status == "running":
                    pid = _pid_cua(wid)
                    cpu, n = cpu_cay(pid) if pid else (0.0, 0)
                    ho.update(worker_id=wid, pid=pid, cpu_dau=cpu,
                              tuong_dau=time.time(), so_tien_trinh_dau=n)
                if st.status in ("succeeded", "failed_terminal",
                                 "failed_retryable", "cancelled",
                                 "invalidated"):
                    pid = int(ho.get("pid") or _pid_cua(wid))
                    cpu, n = cpu_cay(pid) if pid else (0.0, 0)
                    ho["cpu_cuoi"] = cpu
                    ho["tuong_cuoi"] = time.time()
                    if "cpu_dau" in ho:
                        ho["cpu_giay"] = round(cpu - float(ho["cpu_dau"]), 1)
                    if "tuong_dau" in ho:
                        ho["tuong_giay"] = round(
                            ho["tuong_cuoi"] - float(ho["tuong_dau"]), 1)
                    ho["trang_thai"] = st.status
                    ho["loi"] = st.error or ""
                    ho["loi_job"] = getattr(job, "error", "") or ""
                ghi("stage", ten=st.stage, trang_thai=st.status,
                    lan=st.attempt, worker=wid,
                    job=getattr(job, "status", ""),
                    cpu=ho.get("cpu_giay", ""), tuong=ho.get("tuong_giay", ""),
                    loi=(st.error or "")[:300])

            # ⭐ Dem luot `advance`: cau hoi 3 cua brief (`jobs._advance` co tu
            #    noi vo han khong). So mong doi la 12 + 1 luot mo dau.
            for j in s.execute(text(
                    "SELECT id, status, worker_id, created_at, started_at, "
                    "       finished_at, attempts, error FROM jobs "
                    "WHERE job_type = 'auto_scan_video.advance' "
                    "  AND params::text LIKE :p ORDER BY created_at"),
                    {"p": f"%{run_id}%"}).all():
                truoc = advance.get(j.id)
                if truoc and truoc.get("status") == j.status:
                    continue
                advance[j.id] = {"status": j.status, "worker": j.worker_id,
                                 "tao": str(j.created_at),
                                 "xong": str(j.finished_at),
                                 "loi": (j.error or "")[:300]}
                ghi("advance", job=j.id[:8], trang_thai=j.status,
                    worker=j.worker_id, tong=len(advance))

            xong = run.status in ("done", "error", "cancelled")
            if xong:
                break
            time.sleep(args.nhip)
    finally:
        phien.rollback()
        phien.close()
    if not xong:
        ghi("HET TRAN THOI GIAN", tran_phut=args.tran_phut)

    # ── bang ket qua ──────────────────────────────────────────────────────────
    ten = _ten_giai_doan()
    print("\n== GIAI DOAN ==")
    print(f"{'giai doan':16} {'trang thai':18} {'CPU s':>9} {'tuong s':>9} {'pid':>7} lan")
    for g in ten:
        h = do.get(g, {})
        print(f"{g:16} {str(h.get('trang_thai','(chua chay)')):18} "
              f"{h.get('cpu_giay','-')!s:>9} {h.get('tuong_giay','-')!s:>9} "
              f"{h.get('pid','-')!s:>7}")

    print("\n== THOI GIAN CHET giua cac giai doan (tuong) ==")
    moc = sorted(((float(h["tuong_dau"]), float(h.get("tuong_cuoi") or 0), g)
                  for g, h in do.items() if "tuong_dau" in h))
    chet = []
    for i in range(1, len(moc)):
        truoc_ket = moc[i - 1][1]
        sau_bat = moc[i][0]
        if truoc_ket and sau_bat > truoc_ket:
            d = round(sau_bat - truoc_ket, 1)
            chet.append((moc[i - 1][2], moc[i][2], d))
            print(f"  {moc[i-1][2]:16} -> {moc[i][2]:16} {d:8.1f} s")
    if chet:
        ds = [d for _a, _b, d in chet]
        print(f"  TONG {round(sum(ds),1)} s | trung binh {round(sum(ds)/len(ds),1)} s "
              f"| min {min(ds)} | max {max(ds)}")

    print(f"\n== LUOT `advance` ==  THAT: {len(advance)}  | CHUOI CO {len(ten)} giai doan")
    for jid, h in advance.items():
        print(f"  {jid[:8]} {h['status']:10} {h['worker']:24} {h['tao']} -> {h['xong']}"
              + (f" LOI: {h['loi']}" if h["loi"] else ""))

    ra = {"run_id": run_id, "giai_doan": do, "advance": advance,
          "thoi_gian_chet": chet, "nhat_ky": nhat_ky}
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(ra, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
        print("da ghi:", args.json)
    return 0


# ══════════════════════════════════════════════════════════════════════════════
#  worker rieng
# ══════════════════════════════════════════════════════════════════════════════

def lenh_worker(args) -> int:
    """MOT tien trinh worker RIENG. ⛔ Khong cham dich vu dang chay.

    `maintenance=False`: khong chay vong bao tri — viec nen da co dich vu
    production lam, va hai vong cung quet la hai lan cung mot viec.
    """
    import logging
    import socket

    nap_env()
    os.environ["LTT_AUTO_SCAN_VIDEO"] = "1"
    os.chdir(GOC)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from platform_core.job_runner import run_forever

    het = time.monotonic() + args.giay
    wid = f"{socket.gethostname()}:{os.getpid()}"
    print("WORKER RIENG:", wid, "| python:", sys.executable, flush=True)
    print("PATH co ffmpeg:", _tim_ffmpeg(), flush=True)
    run_forever(wid, stop=lambda: time.monotonic() > het, maintenance=False,
                capabilities=None)
    return 0


def _tim_ffmpeg() -> str:
    import shutil
    return shutil.which("ffmpeg") or "(KHONG THAY TREN PATH)"


# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="lenh", required=True)

    t = sub.add_parser("tao")
    t.add_argument("--video", required=True)
    t.add_argument("--preset", default="localize_preserve_picture")
    t.add_argument("--nguon", default="zh")
    t.add_argument("--dich", default="vi")
    t.add_argument("--che-do-giong", dest="che_do_giong", default="USER_SELECTED")
    t.add_argument("--giong", default="Minh Đức")
    t.add_argument("--email", default="khach1.thu@lttstudios.local")
    t.set_defaults(fn=lenh_tao)

    d = sub.add_parser("theo-doi")
    d.add_argument("run_id")
    d.add_argument("--tran-phut", type=float, default=90.0)
    d.add_argument("--nhip", type=float, default=3.0)
    d.add_argument("--json", default="")
    d.set_defaults(fn=lenh_theo_doi)

    c = sub.add_parser("chay", help="tao roi theo-doi trong MOT luot (mot lan khoa)")
    c.add_argument("--video", required=True)
    c.add_argument("--preset", default="localize_preserve_picture")
    c.add_argument("--nguon", default="zh")
    c.add_argument("--dich", default="vi")
    c.add_argument("--che-do-giong", dest="che_do_giong", default="USER_SELECTED")
    c.add_argument("--giong", default="Minh Đức")
    c.add_argument("--email", default="khach1.thu@lttstudios.local")
    c.add_argument("--tran-phut", type=float, default=90.0)
    c.add_argument("--nhip", type=float, default=3.0)
    c.add_argument("--json", default="")
    c.set_defaults(fn=lenh_chay)

    w = sub.add_parser("worker")
    w.add_argument("--giay", type=float, default=3600.0)
    w.set_defaults(fn=lenh_worker)

    args = ap.parse_args()
    return int(args.fn(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
